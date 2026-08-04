"""
Tenant-aware session authentication for the unified API.

Sessions are HMAC-signed cookies carrying `username|tenant|expiry`.
Credentials live in the central tenant directory (salted PBKDF2);
accounts from the legacy single-tenant user database migrate
automatically on their first successful login. Every request is bound
to the session's city - a user cannot reach another tenant's data
because the tenant in their signed cookie decides which database files
open (see modules/tenancy/context.py).
"""

import hashlib
import hmac
import os
import time
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from modules.tenancy.directory import directory

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "gs_platform_session"
SESSION_SECONDS = 8 * 3600


def _secret() -> bytes:
    return os.getenv("SESSION_SECRET", "govsight-dev-session-secret-change-me").encode()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_session(username: str, tenant_id: str) -> str:
    payload = f"{username}|{tenant_id}|{int(time.time()) + SESSION_SECONDS}"
    return payload + "|" + _sign(payload)


def read_session(token: Optional[str]) -> Optional[Tuple[str, str]]:
    """Validate a session cookie; returns (username, tenant_id) or None."""
    if not token:
        return None
    parts = token.rsplit("|", 1)
    if len(parts) != 2:
        return None
    payload, sig = parts
    if not hmac.compare_digest(_sign(payload), sig):
        return None
    fields = payload.split("|")
    if len(fields) != 3:
        return None
    username, tenant_id, expires = fields
    try:
        if int(expires) < time.time():
            return None
    except ValueError:
        return None
    return username, tenant_id


def require_user(request: Request) -> dict:
    session = read_session(request.cookies.get(COOKIE_NAME))
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username, tenant_id = session
    user = directory.get_user(username)
    if not user or not user["active"] or user["tenant_id"] != tenant_id:
        raise HTTPException(status_code=401, detail="Session no longer valid")
    tenant = directory.get_tenant(tenant_id) or {}
    if not tenant.get("active", 1):
        raise HTTPException(status_code=403, detail="This city's account is suspended")
    user["tenant_name"] = tenant.get("name", tenant_id)
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response, request: Request):
    user = directory.authenticate(body.username, body.password)
    ip = request.client.host if request.client else ""
    if not user:
        # A failed attempt may not map to a tenant; log it against the
        # attempted user's city when we can resolve one.
        try:
            from modules.tenancy import audit as admin_audit
            known = directory.get_user(body.username)
            if known:
                admin_audit.record(body.username, "auth.login_failed", "",
                                   {}, ip, tenant_id=known["tenant_id"])
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid username or password")
    try:
        from modules.tenancy import audit as admin_audit
        admin_audit.record(user["username"], "auth.login", "", {}, ip,
                           tenant_id=user["tenant_id"])
    except Exception:
        pass
    tenant = directory.get_tenant(user["tenant_id"]) or {}
    if not tenant.get("active", 1):
        raise HTTPException(status_code=403, detail="This city's account is suspended")
    response.set_cookie(
        COOKIE_NAME, make_session(user["username"], user["tenant_id"]),
        max_age=SESSION_SECONDS, httponly=True, samesite="lax",
        secure=os.getenv("GOVSIGHT_INSECURE_COOKIES") != "1",
    )
    return {"ok": True, "username": user["username"], "role": user["role"],
            "tenant_id": user["tenant_id"],
            "tenant_name": tenant.get("name", user["tenant_id"]),
            "departments": user["departments"],
            "is_platform_admin": user["is_platform_admin"]}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {"username": user["username"], "role": user["role"],
            "tenant_id": user["tenant_id"], "tenant_name": user["tenant_name"],
            "departments": user["departments"],
            "is_platform_admin": user["is_platform_admin"]}
