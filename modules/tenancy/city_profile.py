"""
Per-city profile: the single source of truth for "which city is this".

Whatever is saved here flows into the data bundle's `city` block and
`meta.organization`, which drive the Economic Indicators localization
(Census ACS via state/place FIPS, weather via lat/lon), report
branding, and the AI chat context. The founding demo city falls back
to the bundled demo profile for anything unset.
"""

import json
import os
from typing import Any, Dict, Optional

from modules.tenancy.context import tenant_db_path

# Editable fields, in display order: (key, label, kind)
PROFILE_FIELDS = [
    ("name", "City name", "text"),
    ("state", "State", "text"),
    ("state_abbr", "State abbreviation", "text"),
    ("county", "County", "text"),
    ("state_fips", "State FIPS code", "text"),
    ("place_fips", "Place FIPS code", "text"),
    ("latitude", "Latitude", "number"),
    ("longitude", "Longitude", "number"),
    ("fiscal_year_start_month", "Fiscal year start month (1-12)", "number"),
    ("budget_year", "Current budget year", "number"),
]


def _path(tenant_id: Optional[str] = None) -> str:
    return tenant_db_path("city_profile.json", tenant_id)


def _demo_city() -> Dict[str, Any]:
    try:
        with open(os.path.join("public", "demo", "demo_data.json")) as fh:
            return json.load(fh).get("city", {})
    except Exception:
        return {}


def load_profile(tenant_id: Optional[str] = None,
                 include_demo_fallback: bool = False) -> Dict[str, Any]:
    stored: Dict[str, Any] = {}
    try:
        with open(_path(tenant_id)) as fh:
            stored = json.load(fh)
    except Exception:
        pass
    if include_demo_fallback:
        base = _demo_city()
        base.update({k: v for k, v in stored.items() if v not in (None, "")})
        return base
    return stored


def save_profile(profile: Dict[str, Any], tenant_id: Optional[str] = None) -> Dict[str, Any]:
    allowed = {k for k, _, _ in PROFILE_FIELDS}
    clean = {k: v for k, v in profile.items() if k in allowed and v not in (None, "")}
    for key in ("latitude", "longitude"):
        if key in clean:
            clean[key] = float(clean[key])
    for key in ("fiscal_year_start_month", "budget_year"):
        if key in clean:
            clean[key] = int(clean[key])
    if "fiscal_year_start_month" in clean and not 1 <= clean["fiscal_year_start_month"] <= 12:
        raise ValueError("Fiscal year start month must be 1-12")
    for key in ("state_fips", "place_fips"):
        if key in clean and not str(clean[key]).isdigit():
            raise ValueError(f"{key} must be numeric (Census FIPS code)")
    path = _path(tenant_id)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(clean, fh, indent=1)
    return clean


def bundle_city(tenant_id: Optional[str], tenant_name: str,
                is_default_tenant: bool) -> Dict[str, Any]:
    """The `city` block for the data bundle: stored profile, with the
    demo profile as fallback for the founding city only."""
    if is_default_tenant:
        return load_profile(tenant_id, include_demo_fallback=True)
    profile = load_profile(tenant_id)
    profile.setdefault("name", tenant_name)
    return profile
