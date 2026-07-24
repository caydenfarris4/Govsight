"""Multi-tenant support: central directory, per-tenant data resolution,
and department-level access control."""

from modules.tenancy.context import (  # noqa: F401
    DEFAULT_TENANT, current_tenant, set_current_tenant, tenant_db_path,
)
from modules.tenancy.directory import directory  # noqa: F401
