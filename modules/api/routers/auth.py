"""
Session authentication for the unified API.

HMAC-signed session cookies (same scheme as the edge worker) over the
existing user database with hashed passwords. The SPA calls
/api/auth/login, /api/auth/me, and /api/auth/logout; every other
router depends on `require_user`.
"""

import hashlib
import hmac
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from modules.admin.user_database import authenticate_user, get_user_info

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "gs_platform_session"
SESSION_SECONDS = 8 * 3600


def _secret() -> bytes:
    return os.getenv("SESSION_SECRET", "govsight-dev-session-secret-change-me").encode()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def make_session(username: str) -> str:
    payload = f"{username}|{int(time.time()) + SESSION_SECONDS}"
    return payload + "|" + _sign(payload)


def read_session(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    parts = token.rsplit("|", 1)
    if len(parts) != 2:
        return None
    payload, sig = parts
    if not hmac.compare_digest(_sign(payload), sig):
        return None
    try:
        username, expires = payload.rsplit("|", 1)
        if int(expires) < time.time():
            return None
    except ValueError:
        return None
    return username


def require_user(request: Request) -> dict:
    username = read_session(request.cookies.get(COOKIE_NAME))
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    info = get_user_info(username) or {"username": username, "role": "viewer"}
    info["username"] = username
    return info


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response):
    if not authenticate_user(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    info = get_user_info(body.username) or {}
    response.set_cookie(
        COOKIE_NAME, make_session(body.username),
        max_age=SESSION_SECONDS, httponly=True, samesite="lax",
        secure=os.getenv("GOVSIGHT_INSECURE_COOKIES") != "1",
    )
    return {"ok": True, "username": body.username,
            "role": info.get("role", "viewer")}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {"username": user["username"], "role": user.get("role", "viewer"),
            "departments": user.get("departments", "all")}
