"""
City administration API - the unified admin surface.

Grouped by responsibility, one owner per concern (no legacy overlap):
  users            - accounts, roles, department access (city admin)
  city-profile     - who this city is; feeds the bundle's `city` block,
                     Economic Indicators localization, and AI context
  datasource       - the ERP connection: register sources, AI field
                     mapping (propose -> approve), sync into this
                     city's canonical database
  funds            - GASB 54 fund classifications (reallocation policy)
  reports          - report schedules and execution history
  archive          - archived report files
  audit            - this city's administrative audit ledger
  ai-keys          - platform AI provider keys (platform admin)
  tenants          - create cities (platform admin)
"""

import csv
import io
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from modules.api.routers.auth import require_admin, require_user
from modules.tenancy import audit as admin_audit
from modules.tenancy.city_profile import PROFILE_FIELDS, load_profile, save_profile
from modules.tenancy.context import DEFAULT_TENANT, current_tenant, tenant_db_path
from modules.tenancy.directory import directory

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


# ── departments (for the permission checklist UI) ───────────────────────


@router.get("/departments")
def departments(user: dict = Depends(require_user)):
    """Distinct departments in this city's ledger (demo fallback for the
    founding city)."""
    db = tenant_db_path(os.path.join("core", "govsight_all_in_one_data.db"))
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        try:
            rows = conn.execute(
                "SELECT DISTINCT department FROM gl_accounts "
                "WHERE department IS NOT NULL AND department != '' "
                "ORDER BY department").fetchall()
            if rows:
                return {"departments": [r[0] for r in rows]}
        finally:
            conn.close()
    if current_tenant() == DEFAULT_TENANT:
        try:
            with open(os.path.join("public", "demo", "demo_data.json")) as fh:
                return {"departments": json.load(fh).get("departments", [])}
        except Exception:
            pass
    return {"departments": []}


# ── user management (own city only) ─────────────────────────────────────


class CreateUser(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    departments: Union[str, List[str]] = "*"


class UpdateUser(BaseModel):
    role: Optional[str] = None
    departments: Optional[Union[str, List[str]]] = None
    active: Optional[bool] = None
    password: Optional[str] = None


@router.get("/users")
def list_users(admin: dict = Depends(require_admin)):
    return {"users": directory.list_users(admin["tenant_id"])}


@router.post("/users", status_code=201)
def create_user(body: CreateUser, request: Request,
                admin: dict = Depends(require_admin)):
    try:
        user = directory.create_user(
            body.username, body.password, admin["tenant_id"],
            role=body.role, departments=body.departments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    admin_audit.record(admin["username"], "user.create", body.username,
                       {"role": body.role, "departments": body.departments},
                       _client_ip(request))
    return user


@router.put("/users/{username}")
def update_user(username: str, body: UpdateUser, request: Request,
                admin: dict = Depends(require_admin)):
    if username == admin["username"] and body.active is False:
        raise HTTPException(status_code=400,
                            detail="You cannot deactivate your own account")
    if username == admin["username"] and body.role and body.role != "admin":
        raise HTTPException(status_code=400,
                            detail="You cannot remove your own admin role")
    try:
        user = directory.update_user(
            username, admin["tenant_id"], role=body.role,
            departments=body.departments, active=body.active,
            password=body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    changes = {k: v for k, v in (("role", body.role),
               ("departments", body.departments), ("active", body.active),
               ("password", "changed" if body.password else None)) if v is not None}
    admin_audit.record(admin["username"], "user.update", username,
                       changes, _client_ip(request))
    return user


# ── city profile ────────────────────────────────────────────────────────
# The single source of "which city is this" - flows into the data
# bundle's city block, Economic Indicators, branding, and AI context.


@router.get("/city-profile")
def get_city_profile(admin: dict = Depends(require_admin)):
    return {
        "fields": [{"key": k, "label": l, "kind": kind}
                   for k, l, kind in PROFILE_FIELDS],
        "profile": load_profile(),
        "effective": load_profile(
            include_demo_fallback=current_tenant() == DEFAULT_TENANT),
    }


@router.put("/city-profile")
def put_city_profile(body: Dict[str, Any], request: Request,
                     admin: dict = Depends(require_admin)):
    try:
        saved = save_profile(body)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    admin_audit.record(admin["username"], "city_profile.update", "",
                       saved, _client_ip(request))
    return {"ok": True, "profile": saved}


# ── data source (the ERP connection) ────────────────────────────────────
# Registered sources feed this city's canonical database through the
# AI mapping pipeline; the canonical database is what every module and
# the data bundle read. One path, no duplicate connection managers.


def _pipeline():
    from modules.data_adapter.ai_data_mapper import MappingStore
    from modules.data_adapter.ingestion_pipeline import IngestionPipeline
    store = MappingStore(db_path=tenant_db_path(
        os.path.join("core", "integration_mappings.db")))
    canonical = tenant_db_path(os.path.join("core", "govsight_all_in_one_data.db"))
    return IngestionPipeline(store=store, canonical_db_path=canonical)


class CreateSource(BaseModel):
    name: str
    source_type: str          # rest_api | caselle
    config: Dict[str, Any] = {}


@router.get("/datasource/sources")
def list_sources(admin: dict = Depends(require_admin)):
    pipe = _pipeline()
    sources = pipe.store.list_sources()
    mappings = pipe.store.list_mappings()
    approved = {}
    for m in mappings:
        if m.get("status") == "approved":
            approved.setdefault((m["source_id"], m["entity"]), m["version"])
    for s in sources:
        s["approved_entities"] = sorted(
            e for (sid, e) in approved if sid == s["id"])
    from modules.data_adapter.canonical_schema import CANONICAL_ENTITIES
    return {"sources": sources,
            "entities": sorted(CANONICAL_ENTITIES.keys())}


@router.post("/datasource/sources", status_code=201)
def create_source(body: CreateSource, request: Request,
                  admin: dict = Depends(require_admin)):
    if body.source_type not in ("rest_api", "caselle"):
        raise HTTPException(status_code=400,
                            detail="source_type must be rest_api or caselle "
                                   "(use the CSV upload for files)")
    pipe = _pipeline()
    source_id = pipe.store.register_source(body.name, body.source_type, body.config)
    admin_audit.record(admin["username"], "datasource.register", body.name,
                       {"type": body.source_type}, _client_ip(request))
    return {"ok": True, "source_id": source_id}


@router.post("/datasource/upload-csv", status_code=201)
async def upload_csv_source(request: Request,
                            name: str = Form(...),
                            file: UploadFile = File(...),
                            admin: dict = Depends(require_admin)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CSV larger than 25 MB")
    safe = "".join(c for c in os.path.basename(file.filename)
                   if c.isalnum() or c in "._-") or "upload.csv"
    dest = tenant_db_path(os.path.join("uploads", f"{int(time.time())}_{safe}"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(content)
    pipe = _pipeline()
    source_id = pipe.store.register_source(name, "csv", {"path": dest})
    admin_audit.record(admin["username"], "datasource.upload_csv", name,
                       {"file": safe, "bytes": len(content)}, _client_ip(request))
    return {"ok": True, "source_id": source_id, "stored_as": os.path.basename(dest)}


class ProposeBody(BaseModel):
    source_id: int
    entity: str


@router.post("/datasource/propose")
def propose_mapping(body: ProposeBody, admin: dict = Depends(require_admin)):
    from modules.data_adapter.canonical_schema import CANONICAL_ENTITIES
    if body.entity not in CANONICAL_ENTITIES:
        raise HTTPException(status_code=400,
                            detail=f"Unknown entity; choose from "
                                   f"{sorted(CANONICAL_ENTITIES)}")
    pipe = _pipeline()
    source = next((s for s in pipe.store.list_sources()
                   if s["id"] == body.source_id), None)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    try:
        sample = pipe.fetch_sample(source)
    except Exception as exc:
        raise HTTPException(status_code=400,
                            detail=f"Could not read from source: {exc}")
    if not sample:
        raise HTTPException(status_code=400, detail="Source returned no records")
    proposal = pipe.engine.propose(body.entity, sample)
    mapping_id = pipe.store.save_proposal(body.source_id, proposal)
    return {"ok": True, "mapping_id": mapping_id,
            "proposal": proposal, "sample_size": len(sample)}


class ApproveBody(BaseModel):
    mapping_id: int
    mappings: List[Dict[str, Any]]


@router.post("/datasource/approve")
def approve_mapping(body: ApproveBody, request: Request,
                    admin: dict = Depends(require_admin)):
    pipe = _pipeline()
    pipe.store.approve_mapping(body.mapping_id, admin["username"], body.mappings)
    admin_audit.record(admin["username"], "datasource.approve_mapping",
                       str(body.mapping_id),
                       {"fields": len(body.mappings)}, _client_ip(request))
    return {"ok": True}


class SyncBody(BaseModel):
    source_name: str
    entity: str


@router.post("/datasource/sync")
def run_sync(body: SyncBody, request: Request,
             admin: dict = Depends(require_admin)):
    pipe = _pipeline()
    try:
        result = pipe.run_sync(body.source_name, body.entity)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    admin_audit.record(admin["username"], "datasource.sync", body.source_name,
                       {"entity": body.entity, **{k: result.get(k) for k in
                        ("total", "succeeded", "failed")}}, _client_ip(request))
    return {"ok": True, "result": result}


@router.get("/datasource/history")
def sync_history(admin: dict = Depends(require_admin)):
    return {"runs": _pipeline().store.recent_syncs(50)}


# ── fund classifications (GASB 54) ──────────────────────────────────────
# Drives reallocation eligibility platform-wide: the scenario planner,
# Mantis, and the monthly close assistant all enforce this policy.


@router.get("/funds")
def get_funds(admin: dict = Depends(require_admin)):
    from modules.utils.fund_policy import GASB_54_CATEGORIES, load_fund_classifications
    funds = set()
    db = tenant_db_path(os.path.join("core", "govsight_all_in_one_data.db"))
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        try:
            funds |= {r[0] for r in conn.execute(
                "SELECT DISTINCT fund FROM gl_accounts "
                "WHERE fund IS NOT NULL AND fund != ''")}
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    fund_names = {}
    if current_tenant() == DEFAULT_TENANT and not funds:
        try:
            with open(os.path.join("public", "demo", "demo_data.json")) as fh:
                for f in json.load(fh).get("funds", []):
                    funds.add(f["code"])
                    fund_names[f["code"]] = f["name"]
        except Exception:
            pass
    return {
        "funds": sorted(funds),
        "fund_names": fund_names,
        "classifications": load_fund_classifications(),
        "categories": {k: {"eligible": v.get("reallocation_eligible", False),
                           "requires_approval": v.get("requires_approval", False),
                           "reference": v.get("gasb_reference", ""),
                           "description": v.get("description", "")}
                       for k, v in GASB_54_CATEGORIES.items()},
    }


@router.put("/funds")
def put_funds(body: Dict[str, str], request: Request,
              admin: dict = Depends(require_admin)):
    from modules.utils.fund_policy import GASB_54_CATEGORIES, save_fund_classifications
    bad = [c for c in body.values() if c not in GASB_54_CATEGORIES]
    if bad:
        raise HTTPException(status_code=400,
                            detail=f"Unknown GASB 54 categories: {sorted(set(bad))}")
    if not save_fund_classifications(dict(body), updated_by=admin["username"]):
        raise HTTPException(status_code=500, detail="Could not save classifications")
    admin_audit.record(admin["username"], "funds.classify", "",
                       dict(body), _client_ip(request))
    return {"ok": True}


# ── reports & archive ───────────────────────────────────────────────────


def _schedules_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(tenant_db_path("report_schedules.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS report_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT, report_name TEXT, report_type TEXT,
            frequency TEXT, schedule_time TEXT,
            day_of_week INTEGER, day_of_month INTEGER,
            timezone TEXT DEFAULT 'US/Eastern', enabled INTEGER DEFAULT 1,
            last_run TEXT, next_run TEXT,
            distribution_channels TEXT DEFAULT '[]', recipients TEXT DEFAULT '[]',
            google_drive_folder TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS schedule_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER, execution_time TEXT,
            status TEXT, file_path TEXT, error_message TEXT
        );
    """)
    return conn


class CreateSchedule(BaseModel):
    module: str
    report_name: str
    frequency: str            # daily | weekly | monthly | quarterly
    schedule_time: str = "06:00"
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    recipients: List[str] = []


@router.get("/reports/schedules")
def list_schedules(admin: dict = Depends(require_admin)):
    with _schedules_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM report_schedules ORDER BY module, report_name")]
    return {"schedules": rows}


@router.post("/reports/schedules", status_code=201)
def create_schedule(body: CreateSchedule, request: Request,
                    admin: dict = Depends(require_admin)):
    if body.frequency not in ("daily", "weekly", "monthly", "quarterly"):
        raise HTTPException(status_code=400, detail="Invalid frequency")
    with _schedules_conn() as conn:
        conn.execute(
            "INSERT INTO report_schedules (module, report_name, report_type, "
            "frequency, schedule_time, day_of_week, day_of_month, recipients) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (body.module, body.report_name, body.report_name.lower().replace(" ", "_"),
             body.frequency, body.schedule_time, body.day_of_week,
             body.day_of_month, json.dumps(body.recipients)))
        conn.commit()
    admin_audit.record(admin["username"], "reports.schedule_create",
                       body.report_name, {"frequency": body.frequency},
                       _client_ip(request))
    return {"ok": True}


@router.put("/reports/schedules/{schedule_id}")
def toggle_schedule(schedule_id: int, body: Dict[str, Any], request: Request,
                    admin: dict = Depends(require_admin)):
    with _schedules_conn() as conn:
        row = conn.execute("SELECT id FROM report_schedules WHERE id = ?",
                           (schedule_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if "enabled" in body:
            conn.execute("UPDATE report_schedules SET enabled = ? WHERE id = ?",
                         (int(bool(body["enabled"])), schedule_id))
            conn.commit()
    admin_audit.record(admin["username"], "reports.schedule_update",
                       str(schedule_id), body, _client_ip(request))
    return {"ok": True}


@router.delete("/reports/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, request: Request,
                    admin: dict = Depends(require_admin)):
    with _schedules_conn() as conn:
        conn.execute("DELETE FROM report_schedules WHERE id = ?", (schedule_id,))
        conn.commit()
    admin_audit.record(admin["username"], "reports.schedule_delete",
                       str(schedule_id), {}, _client_ip(request))
    return {"ok": True}


@router.get("/reports/history")
def report_history(admin: dict = Depends(require_admin)):
    with _schedules_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT h.*, s.module, s.report_name FROM schedule_history h "
            "LEFT JOIN report_schedules s ON s.id = h.schedule_id "
            "ORDER BY h.id DESC LIMIT 100")]
    return {"history": rows}


def _archive_dir() -> str:
    if current_tenant() == DEFAULT_TENANT:
        return "admin_archive"
    return os.path.dirname(tenant_db_path(os.path.join("archive", ".keep")))


@router.get("/archive")
def list_archive(admin: dict = Depends(require_admin)):
    folder = _archive_dir()
    files = []
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder), reverse=True):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and not name.startswith("."):
                files.append({"name": name, "size": os.path.getsize(path),
                              "modified": int(os.path.getmtime(path))})
    return {"files": files[:200]}


@router.get("/archive/download")
def download_archive(name: str, admin: dict = Depends(require_admin)):
    folder = os.path.abspath(_archive_dir())
    path = os.path.abspath(os.path.join(folder, os.path.basename(name)))
    if not path.startswith(folder) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    from fastapi.responses import FileResponse
    return FileResponse(path, filename=os.path.basename(path))


# ── audit ledger ────────────────────────────────────────────────────────


@router.get("/audit")
def get_audit(limit: int = 100, action: str = "", actor: str = "",
              admin: dict = Depends(require_admin)):
    return {"events": admin_audit.query(limit=limit, action=action, actor=actor),
            "actions": admin_audit.distinct_actions()}


@router.get("/audit/export.csv")
def export_audit(admin: dict = Depends(require_admin)):
    events = admin_audit.query(limit=1000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestamp", "actor", "action", "target", "details", "ip"])
    for e in events:
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(e["ts"])),
                         e["actor"], e["action"], e["target"],
                         json.dumps(e["details"]), e["ip"]])
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=admin_audit.csv"})


# ── AI provider keys (platform-wide, platform admin only) ───────────────


class AIKeyBody(BaseModel):
    provider: str             # openai | anthropic
    key: Optional[str] = None


# ── platform administration (GovSight staff) ────────────────────────────


def require_platform_admin(user: dict = Depends(require_user)) -> dict:
    if not user.get("is_platform_admin"):
        raise HTTPException(status_code=403,
                            detail="Platform administrator access required")
    return user


class CreateTenant(BaseModel):
    tenant_id: str
    name: str
    state: str = ""
    admin_username: str
    admin_password: str


@router.get("/tenants")
def list_tenants(user: dict = Depends(require_platform_admin)):
    return {"tenants": directory.list_tenants()}


@router.post("/tenants", status_code=201)
def create_tenant(body: CreateTenant, request: Request,
                  user: dict = Depends(require_platform_admin)):
    try:
        tenant = directory.create_tenant(
            body.tenant_id, body.name, body.state,
            admin_username=body.admin_username,
            admin_password=body.admin_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    admin_audit.record(user["username"], "tenant.create", body.tenant_id,
                       {"name": body.name, "admin": body.admin_username},
                       _client_ip(request))
    return tenant


@router.get("/ai-keys")
def ai_key_status(user: dict = Depends(require_platform_admin)):
    from modules.security.api_key_manager import api_key_manager
    return {p: api_key_manager.get_status(p) for p in ("openai", "anthropic")}


@router.put("/ai-keys")
def save_ai_key(body: AIKeyBody, request: Request,
                user: dict = Depends(require_platform_admin)):
    if body.provider not in ("openai", "anthropic"):
        raise HTTPException(status_code=400, detail="Unknown provider")
    from modules.security.api_key_manager import api_key_manager
    if not body.key:
        raise HTTPException(status_code=400, detail="Key required")
    result = api_key_manager.set_api_key(body.key, body.provider)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    admin_audit.record(user["username"], "ai_keys.save", body.provider, {},
                       _client_ip(request))
    return {"ok": True, "status": api_key_manager.get_status(body.provider)}


@router.post("/ai-keys/test")
def test_ai_key(body: AIKeyBody, user: dict = Depends(require_platform_admin)):
    from modules.security.api_key_manager import api_key_manager
    return api_key_manager.validate_api_key(body.key, body.provider)


@router.delete("/ai-keys/{provider}")
def remove_ai_key(provider: str, request: Request,
                  user: dict = Depends(require_platform_admin)):
    from modules.security.api_key_manager import api_key_manager
    result = api_key_manager.remove_api_key(provider)
    admin_audit.record(user["username"], "ai_keys.remove", provider, {},
                       _client_ip(request))
    return result
