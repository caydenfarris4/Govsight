"""
City administration API.

A city admin manages only their own city's users: create accounts,
assign roles, and control which departments each user can see. Platform
administrators (GovSight staff) additionally create cities.
"""

import json
import os
import sqlite3
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from modules.api.routers.auth import require_admin, require_user
from modules.tenancy.context import DEFAULT_TENANT, current_tenant, tenant_db_path
from modules.tenancy.directory import directory

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
def create_user(body: CreateUser, admin: dict = Depends(require_admin)):
    try:
        return directory.create_user(
            body.username, body.password, admin["tenant_id"],
            role=body.role, departments=body.departments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/users/{username}")
def update_user(username: str, body: UpdateUser,
                admin: dict = Depends(require_admin)):
    if username == admin["username"] and body.active is False:
        raise HTTPException(status_code=400,
                            detail="You cannot deactivate your own account")
    if username == admin["username"] and body.role and body.role != "admin":
        raise HTTPException(status_code=400,
                            detail="You cannot remove your own admin role")
    try:
        return directory.update_user(
            username, admin["tenant_id"], role=body.role,
            departments=body.departments, active=body.active,
            password=body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
def create_tenant(body: CreateTenant, user: dict = Depends(require_platform_admin)):
    try:
        return directory.create_tenant(
            body.tenant_id, body.name, body.state,
            admin_username=body.admin_username,
            admin_password=body.admin_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
