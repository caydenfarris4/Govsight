"""
Central tenant directory: cities, their users, roles, and department
access lists.

This is the control plane. Data lives per-tenant (see context.py); the
directory only knows who exists, which city they belong to, what role
they hold there, and which departments they may see.

Passwords are PBKDF2-HMAC-SHA256 with a per-user salt. Users from the
legacy (single-tenant) user database are migrated automatically on
their first successful login, so existing credentials keep working.
"""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from modules.tenancy.context import DEFAULT_TENANT, valid_tenant_id

DIRECTORY_DB = os.path.join("databases", "directory.db")
_PBKDF2_ITERATIONS = 200_000

ROLES = ("admin", "editor", "viewer")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS).hex()


class TenantDirectory:
    def __init__(self, db_path: str = DIRECTORY_DB):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    state TEXT DEFAULT '',
                    active INTEGER DEFAULT 1,
                    created_at INTEGER
                );
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY COLLATE NOCASE,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id),
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    departments TEXT NOT NULL DEFAULT '*',
                    active INTEGER DEFAULT 1,
                    is_platform_admin INTEGER DEFAULT 0,
                    created_at INTEGER
                );
            """)
            conn.execute(
                "INSERT OR IGNORE INTO tenants (id, name, state, created_at) "
                "VALUES (?, ?, ?, ?)",
                (DEFAULT_TENANT, "Spanish Fork", "UT", int(time.time())))
            conn.commit()

    # ── authentication ──────────────────────────────────────────────────

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify credentials; returns the user record on success.

        Falls back to the legacy single-tenant user database and migrates
        the account (fresh salted hash, default tenant) on first success.
        """
        username = (username or "").strip()
        if not username or "|" in username:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND active = 1",
                (username,)).fetchone()
        if row:
            expected = _hash_password(password, row["salt"])
            if hmac.compare_digest(expected, row["password_hash"]):
                return self._user_dict(row)
            return None
        return self._legacy_migrate(username, password)

    def _legacy_migrate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        try:
            from modules.admin.user_database import authenticate_user, get_user_info
            if not authenticate_user(username, password):
                return None
            info = get_user_info(username) or {}
        except Exception:
            return None
        role = "admin" if info.get("role") == "admin" else \
               ("editor" if info.get("role") in ("editor", "user") else "viewer")
        # The founding city's first migrated admin also administers the
        # platform (creates new cities) until dedicated staff users exist.
        is_platform_admin = 1 if role == "admin" and not self._any_platform_admin() else 0
        self.create_user(username, password, DEFAULT_TENANT, role=role,
                         departments="*", is_platform_admin=bool(is_platform_admin))
        return self.get_user(username)

    def _any_platform_admin(self) -> bool:
        with self._conn() as conn:
            return conn.execute(
                "SELECT 1 FROM users WHERE is_platform_admin = 1 LIMIT 1"
            ).fetchone() is not None

    # ── users ───────────────────────────────────────────────────────────

    @staticmethod
    def _user_dict(row: sqlite3.Row) -> Dict[str, Any]:
        deps = row["departments"]
        return {
            "username": row["username"],
            "tenant_id": row["tenant_id"],
            "role": row["role"],
            "departments": "*" if deps == "*" else json.loads(deps),
            "active": bool(row["active"]),
            "is_platform_admin": bool(row["is_platform_admin"]),
        }

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?",
                               (username,)).fetchone()
        return self._user_dict(row) if row else None

    def list_users(self, tenant_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE tenant_id = ? ORDER BY username",
                (tenant_id,)).fetchall()
        return [self._user_dict(r) for r in rows]

    def create_user(self, username: str, password: str, tenant_id: str,
                    role: str = "viewer", departments="*",
                    is_platform_admin: bool = False) -> Dict[str, Any]:
        username = (username or "").strip()
        if not username or "|" in username or len(username) > 64:
            raise ValueError("Invalid username (no '|', max 64 characters)")
        if len(password or "") < 8:
            raise ValueError("Password must be at least 8 characters")
        if role not in ROLES:
            raise ValueError(f"Role must be one of {ROLES}")
        if not self.get_tenant(tenant_id):
            raise ValueError(f"Unknown tenant: {tenant_id}")
        deps = "*" if departments == "*" else json.dumps(sorted(set(departments)))
        salt = secrets.token_hex(16)
        with self._lock, self._conn() as conn:
            existing = conn.execute("SELECT 1 FROM users WHERE username = ?",
                                    (username,)).fetchone()
            if existing:
                raise ValueError("Username already exists")
            conn.execute(
                "INSERT INTO users (username, tenant_id, password_hash, salt, role, "
                "departments, active, is_platform_admin, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
                (username, tenant_id, _hash_password(password, salt), salt,
                 role, deps, int(is_platform_admin), int(time.time())))
            conn.commit()
        return self.get_user(username)

    def update_user(self, username: str, tenant_id: str, *,
                    role: Optional[str] = None, departments=None,
                    active: Optional[bool] = None,
                    password: Optional[str] = None) -> Dict[str, Any]:
        """Update a user; tenant_id must match (admins manage only their city)."""
        user = self.get_user(username)
        if not user or user["tenant_id"] != tenant_id:
            raise ValueError("User not found in this city")
        sets, args = [], []
        if role is not None:
            if role not in ROLES:
                raise ValueError(f"Role must be one of {ROLES}")
            sets.append("role = ?"); args.append(role)
        if departments is not None:
            deps = "*" if departments == "*" else json.dumps(sorted(set(departments)))
            sets.append("departments = ?"); args.append(deps)
        if active is not None:
            sets.append("active = ?"); args.append(int(active))
        if password is not None:
            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters")
            salt = secrets.token_hex(16)
            sets.append("password_hash = ?"); args.append(_hash_password(password, salt))
            sets.append("salt = ?"); args.append(salt)
        if sets:
            with self._lock, self._conn() as conn:
                conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE username = ?",
                             (*args, username))
                conn.commit()
        return self.get_user(username)

    # ── tenants ─────────────────────────────────────────────────────────

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE id = ?",
                               (tenant_id,)).fetchone()
        return dict(row) if row else None

    def list_tenants(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM tenants ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def create_tenant(self, tenant_id: str, name: str, state: str = "",
                      admin_username: str = "", admin_password: str = "") -> Dict[str, Any]:
        if not valid_tenant_id(tenant_id):
            raise ValueError("Tenant id must be lowercase letters, digits, hyphens")
        if not (name or "").strip():
            raise ValueError("City name is required")
        with self._lock, self._conn() as conn:
            if conn.execute("SELECT 1 FROM tenants WHERE id = ?",
                            (tenant_id,)).fetchone():
                raise ValueError("Tenant id already exists")
            conn.execute(
                "INSERT INTO tenants (id, name, state, created_at) VALUES (?, ?, ?, ?)",
                (tenant_id, name.strip(), state.strip(), int(time.time())))
            conn.commit()
        if admin_username:
            self.create_user(admin_username, admin_password, tenant_id,
                             role="admin", departments="*")
        return self.get_tenant(tenant_id)


# Shared instance
directory = TenantDirectory()
