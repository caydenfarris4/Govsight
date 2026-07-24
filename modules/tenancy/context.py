"""
Per-request tenant context and database path resolution.

Isolation model: database-per-city. The default (founding) tenant keeps
the legacy databases/ layout untouched; every other tenant gets its own
directory under databases/tenants/<tenant_id>/ with the same relative
file names. A query executed through tenant_db_path() physically cannot
touch another city's rows because it never opens their files.
"""

import os
import re
from contextvars import ContextVar

DEFAULT_TENANT = "spanish-fork"

_current_tenant: ContextVar[str] = ContextVar("govsight_tenant", default=DEFAULT_TENANT)

_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


def valid_tenant_id(tenant_id: str) -> bool:
    return bool(_TENANT_ID_RE.match(tenant_id or ""))


def current_tenant() -> str:
    return _current_tenant.get()


def set_current_tenant(tenant_id: str):
    """Bind the request's tenant; returns a token for reset()."""
    if not valid_tenant_id(tenant_id):
        raise ValueError(f"invalid tenant id: {tenant_id!r}")
    return _current_tenant.set(tenant_id)


def reset_current_tenant(token) -> None:
    _current_tenant.reset(token)


def tenant_db_path(rel_path: str, tenant_id: str = None) -> str:
    """Absolute-ish path of a tenant's database file.

    rel_path is the file's location within the legacy databases/ layout
    (e.g. 'core/govsight_all_in_one_data.db', 'budget_playground.db').
    The default tenant maps to that legacy location; other tenants map
    to databases/tenants/<id>/<rel_path> (directories created on use).
    """
    tenant = tenant_id or current_tenant()
    if not valid_tenant_id(tenant):
        raise ValueError(f"invalid tenant id: {tenant!r}")
    rel_path = rel_path.lstrip("/")
    if ".." in rel_path.split("/"):
        raise ValueError("invalid database path")
    if tenant == DEFAULT_TENANT:
        return os.path.join("databases", rel_path)
    path = os.path.join("databases", "tenants", tenant, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path
