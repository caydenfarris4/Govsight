"""
Budget Playground API — Python port of budget_playground_api/server.js.

Same behavior, same databases, one process. Namespaced under /api/bp so
it can live beside the scenario-planner endpoints in the unified API.
The Node server is retired from startup once this router is live.
"""

import csv
import io
import os
import re
import sqlite3
import uuid as uuidlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from modules.api.routers.auth import require_user

router = APIRouter(prefix="/api/bp", tags=["budget-playground"],
                   dependencies=[Depends(require_user)])

GL_DB_PATH = os.path.join("databases", "core", "govsight_all_in_one_data.db")
PLAY_DB_PATH = os.path.join("databases", "budget_playground.db")

_PAYROLL_RE = re.compile(r"-(5100|5200)$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuidlib.uuid4())


def _gl() -> sqlite3.Connection:
    if not os.path.exists(GL_DB_PATH):
        raise HTTPException(status_code=503,
                            detail="GL database not found - seed or sync data first")
    conn = sqlite3.connect(GL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _play() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(PLAY_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(PLAY_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            description TEXT DEFAULT '', fiscal_year INTEGER NOT NULL DEFAULT 2026,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            is_locked INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS scenario_lines (
            id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL,
            account_number TEXT NOT NULL, revised_budget REAL,
            forecast_yr2 REAL, forecast_yr3 REAL, note TEXT DEFAULT '',
            updated_at TEXT NOT NULL, UNIQUE(scenario_id, account_number));
        CREATE TABLE IF NOT EXISTS supplementals (
            id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL,
            account_number TEXT, department TEXT,
            category TEXT NOT NULL DEFAULT 'Supplemental',
            amount REAL NOT NULL DEFAULT 0, justification TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            submitted_at TEXT NOT NULL, reviewed_at TEXT);
    """)
    return conn


def non_payroll_accounts() -> List[Dict[str, Any]]:
    with _gl() as gl:
        rows = gl.execute("""
            SELECT account_number, account_name, account_type, department,
                   fund, budget_amount, ytd_actual
            FROM gl_accounts
            ORDER BY account_type DESC, department, account_number
        """).fetchall()
    return [dict(r) for r in rows if not _PAYROLL_RE.search(r["account_number"] or "")]


def _seed_default(play: sqlite3.Connection) -> None:
    if play.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0]:
        return
    sid, now = _uuid(), _now()
    play.execute(
        "INSERT INTO scenarios (id, name, description, fiscal_year, created_at, "
        "updated_at, is_locked) VALUES (?, ?, ?, 2026, ?, ?, 0)",
        (sid, "Adopted Budget FY 2026",
         "Original adopted budget - do not delete", now, now))
    for a in non_payroll_accounts():
        play.execute(
            "INSERT INTO scenario_lines (id, scenario_id, account_number, "
            "revised_budget, forecast_yr2, forecast_yr3, note, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, '', ?)",
            (_uuid(), sid, a["account_number"], a["budget_amount"],
             a["budget_amount"], a["budget_amount"], now))
    play.commit()


def _merged_lines(play: sqlite3.Connection, scenario_id: str) -> List[Dict[str, Any]]:
    accounts = non_payroll_accounts()
    lines = {r["account_number"]: dict(r) for r in play.execute(
        "SELECT * FROM scenario_lines WHERE scenario_id = ?", (scenario_id,))}
    merged = []
    for a in accounts:
        line = lines.get(a["account_number"])
        merged.append({
            **a,
            "revised_budget": line["revised_budget"] if line and line["revised_budget"] is not None else a["budget_amount"],
            "forecast_yr2": line["forecast_yr2"] if line and line["forecast_yr2"] is not None else a["budget_amount"],
            "forecast_yr3": line["forecast_yr3"] if line and line["forecast_yr3"] is not None else a["budget_amount"],
            "note": (line or {}).get("note") or "",
            "has_override": bool(line),
        })
    return merged


# ── accounts ───────────────────────────────────────────────────────────────

@router.get("/accounts")
def get_accounts():
    return non_payroll_accounts()


# ── scenarios ──────────────────────────────────────────────────────────────

class ScenarioCreate(BaseModel):
    name: str
    description: str = ""
    fiscal_year: int = 2026
    copy_from_id: Optional[str] = None


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fiscal_year: Optional[int] = None
    is_locked: Optional[int] = None


@router.get("/scenarios")
def list_scenarios():
    with _play() as play:
        _seed_default(play)
        return [dict(r) for r in play.execute(
            "SELECT * FROM scenarios ORDER BY created_at ASC")]


@router.post("/scenarios", status_code=201)
def create_scenario(body: ScenarioCreate):
    if not body.name:
        raise HTTPException(status_code=400, detail="name is required")
    with _play() as play:
        sid, now = _uuid(), _now()
        play.execute(
            "INSERT INTO scenarios (id, name, description, fiscal_year, "
            "created_at, updated_at, is_locked) VALUES (?, ?, ?, ?, ?, ?, 0)",
            (sid, body.name, body.description, body.fiscal_year, now, now))
        if body.copy_from_id:
            for r in play.execute("SELECT * FROM scenario_lines WHERE scenario_id = ?",
                                  (body.copy_from_id,)).fetchall():
                play.execute(
                    "INSERT INTO scenario_lines (id, scenario_id, account_number, "
                    "revised_budget, forecast_yr2, forecast_yr3, note, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (_uuid(), sid, r["account_number"], r["revised_budget"],
                     r["forecast_yr2"], r["forecast_yr3"], r["note"], now))
        else:
            for a in non_payroll_accounts():
                play.execute(
                    "INSERT INTO scenario_lines (id, scenario_id, account_number, "
                    "revised_budget, forecast_yr2, forecast_yr3, note, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, '', ?)",
                    (_uuid(), sid, a["account_number"], a["budget_amount"],
                     a["budget_amount"], a["budget_amount"], now))
        play.commit()
        return dict(play.execute("SELECT * FROM scenarios WHERE id = ?", (sid,)).fetchone())


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    with _play() as play:
        _seed_default(play)
        s = play.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return {**dict(s), "lines": _merged_lines(play, scenario_id)}


@router.put("/scenarios/{scenario_id}")
def update_scenario(scenario_id: str, body: ScenarioUpdate):
    with _play() as play:
        s = play.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Scenario not found")
        fields = {k: v for k, v in body.dict().items() if v is not None}
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            play.execute(f"UPDATE scenarios SET {sets}, updated_at = ? WHERE id = ?",
                         (*fields.values(), _now(), scenario_id))
            play.commit()
        return dict(play.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone())


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str):
    with _play() as play:
        s = play.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Scenario not found")
        if s["is_locked"]:
            raise HTTPException(status_code=403, detail="Scenario is locked")
        play.execute("DELETE FROM scenario_lines WHERE scenario_id = ?", (scenario_id,))
        play.execute("DELETE FROM supplementals WHERE scenario_id = ?", (scenario_id,))
        play.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
        play.commit()
        return {"ok": True}


class LineUpdate(BaseModel):
    account_number: str
    revised_budget: Optional[float] = None
    forecast_yr2: Optional[float] = None
    forecast_yr3: Optional[float] = None
    note: str = ""


@router.put("/scenarios/{scenario_id}/lines")
def put_lines(scenario_id: str, lines: List[LineUpdate]):
    with _play() as play:
        s = play.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Scenario not found")
        if s["is_locked"]:
            raise HTTPException(status_code=403, detail="Scenario is locked")
        now = _now()
        for line in lines:
            play.execute(
                "INSERT INTO scenario_lines (id, scenario_id, account_number, "
                "revised_budget, forecast_yr2, forecast_yr3, note, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(scenario_id, account_number) DO UPDATE SET "
                "revised_budget=excluded.revised_budget, "
                "forecast_yr2=excluded.forecast_yr2, "
                "forecast_yr3=excluded.forecast_yr3, "
                "note=excluded.note, updated_at=excluded.updated_at",
                (_uuid(), scenario_id, line.account_number, line.revised_budget,
                 line.forecast_yr2, line.forecast_yr3, line.note, now))
        play.execute("UPDATE scenarios SET updated_at = ? WHERE id = ?",
                     (now, scenario_id))
        play.commit()
        return {"ok": True, "updated": len(lines)}


@router.get("/scenarios/{scenario_id}/export.csv")
def export_csv(scenario_id: str):
    with _play() as play:
        s = play.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Scenario not found")
        lines = _merged_lines(play, scenario_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["account_number", "account_name", "account_type", "department",
                     "adopted_budget", "ytd_actual", "revised_budget",
                     "forecast_yr2", "forecast_yr3", "note"])
    for l in lines:
        writer.writerow([l["account_number"], l["account_name"], l["account_type"],
                         l["department"], l["budget_amount"], l["ytd_actual"],
                         l["revised_budget"], l["forecast_yr2"], l["forecast_yr3"],
                         l["note"]])
    name = re.sub(r"[^A-Za-z0-9]+", "_", s["name"]) or "scenario"
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})


# ── supplementals ──────────────────────────────────────────────────────────

class SupplementalCreate(BaseModel):
    scenario_id: str
    account_number: Optional[str] = None
    department: Optional[str] = None
    category: str = "Supplemental"
    amount: float = 0
    justification: str = ""


class SupplementalUpdate(BaseModel):
    status: Optional[str] = None
    amount: Optional[float] = None
    justification: Optional[str] = None


@router.get("/supplementals")
def list_supplementals(scenario_id: Optional[str] = None):
    with _play() as play:
        if scenario_id:
            rows = play.execute("SELECT * FROM supplementals WHERE scenario_id = ? "
                                "ORDER BY submitted_at", (scenario_id,))
        else:
            rows = play.execute("SELECT * FROM supplementals ORDER BY submitted_at")
        return [dict(r) for r in rows]


@router.post("/supplementals", status_code=201)
def create_supplemental(body: SupplementalCreate):
    with _play() as play:
        sid = _uuid()
        play.execute(
            "INSERT INTO supplementals (id, scenario_id, account_number, department, "
            "category, amount, justification, status, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (sid, body.scenario_id, body.account_number, body.department,
             body.category, body.amount, body.justification, _now()))
        play.commit()
        return dict(play.execute("SELECT * FROM supplementals WHERE id = ?", (sid,)).fetchone())


@router.put("/supplementals/{supp_id}")
def update_supplemental(supp_id: str, body: SupplementalUpdate):
    with _play() as play:
        s = play.execute("SELECT * FROM supplementals WHERE id = ?", (supp_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Supplemental not found")
        fields = {k: v for k, v in body.dict().items() if v is not None}
        if fields:
            sets = ", ".join(f"{k} = ?" for k in fields)
            extra = ", reviewed_at = ?" if "status" in fields else ""
            args = list(fields.values()) + ([_now()] if "status" in fields else []) + [supp_id]
            play.execute(f"UPDATE supplementals SET {sets}{extra} WHERE id = ?", args)
            play.commit()
        return dict(play.execute("SELECT * FROM supplementals WHERE id = ?", (supp_id,)).fetchone())


@router.delete("/supplementals/{supp_id}")
def delete_supplemental(supp_id: str):
    with _play() as play:
        play.execute("DELETE FROM supplementals WHERE id = ?", (supp_id,))
        play.commit()
        return {"ok": True}


@router.post("/scenarios/{scenario_id}/apply-supplementals")
def apply_supplementals(scenario_id: str):
    with _play() as play:
        s = play.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not s:
            raise HTTPException(status_code=404, detail="Scenario not found")
        approved = play.execute(
            "SELECT * FROM supplementals WHERE scenario_id = ? AND status = 'approved' "
            "AND account_number IS NOT NULL", (scenario_id,)).fetchall()
        budgets = {a["account_number"]: a["budget_amount"]
                   for a in non_payroll_accounts()}
        now, count = _now(), 0
        for supp in approved:
            acct = supp["account_number"]
            line = play.execute(
                "SELECT * FROM scenario_lines WHERE scenario_id = ? AND account_number = ?",
                (scenario_id, acct)).fetchone()
            base = (line["revised_budget"] if line and line["revised_budget"] is not None
                    else budgets.get(acct, 0))
            note = ((line["note"] if line else "") + " [Supplemental applied]").strip()
            play.execute(
                "INSERT INTO scenario_lines (id, scenario_id, account_number, "
                "revised_budget, forecast_yr2, forecast_yr3, note, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(scenario_id, account_number) DO UPDATE SET "
                "revised_budget=excluded.revised_budget, note=excluded.note, "
                "updated_at=excluded.updated_at",
                (_uuid(), scenario_id, acct, base + supp["amount"],
                 (line["forecast_yr2"] if line else budgets.get(acct, 0)),
                 (line["forecast_yr3"] if line else budgets.get(acct, 0)),
                 note, now))
            # Mark as applied so re-running doesn't double-apply
            play.execute("UPDATE supplementals SET status = 'applied', reviewed_at = ? "
                         "WHERE id = ?", (now, supp["id"]))
            count += 1
        play.commit()
        return {"applied": count}


# ── seasonality (port of the Node endpoint) ────────────────────────────────

@router.get("/seasonality")
def seasonality(fyStart: str = "July"):
    start_month = 1 if fyStart == "January" else 7
    with _gl() as gl:
        tables = {r[0] for r in gl.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "monthly_actuals" not in tables:
            return {"available": False, "byAccount": {}, "byType": {},
                    "reason": "no monthly history"}
        rows = gl.execute(
            "SELECT account_number, fiscal_year, month, actual FROM monthly_actuals"
        ).fetchall()
        types = {a["account_number"]: a["account_type"]
                 for a in gl.execute("SELECT account_number, account_type FROM gl_accounts")}
    if not rows:
        return {"available": False, "byAccount": {}, "byType": {},
                "reason": "no monthly history"}

    per_acct: Dict[str, Dict[int, List[float]]] = {}
    for r in rows:
        fiscal_idx = (r["month"] - start_month + 12) % 12
        per_acct.setdefault(r["account_number"], {}).setdefault(
            r["fiscal_year"], [0.0] * 12)[fiscal_idx] += r["actual"]

    by_account: Dict[str, List[float]] = {}
    type_accum: Dict[str, Dict[str, Any]] = {}
    for acct, years in per_acct.items():
        shares = [0.0] * 12
        usable = 0
        for months in years.values():
            total = sum(abs(v) for v in months)
            if total <= 0:
                continue
            usable += 1
            cum = 0.0
            for i in range(12):
                cum += abs(months[i])
                shares[i] += cum / total
        if not usable:
            continue
        curve = [s / usable for s in shares]
        by_account[acct] = curve
        t = types.get(acct, "Expense")
        acc = type_accum.setdefault(t, {"sum": [0.0] * 12, "n": 0})
        for i in range(12):
            acc["sum"][i] += curve[i]
        acc["n"] += 1

    by_type = {t: [v / acc["n"] for v in acc["sum"]]
               for t, acc in type_accum.items()}
    return {"available": bool(by_account), "byAccount": by_account, "byType": by_type}
