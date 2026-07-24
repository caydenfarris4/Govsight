"""
Department-level access control.

A user's `departments` is either "*" (citywide visibility) or a list of
department names. Filtering happens server-side on every response that
carries department-dimensioned data; fund-level views (balance sheet,
cash flow) are citywide by nature and stay visible to every role.
"""

from typing import Any, Dict, List, Optional, Set


def allowed_departments(user: Dict[str, Any]) -> Optional[Set[str]]:
    """None means unrestricted; otherwise the set of visible departments."""
    deps = user.get("departments", "*")
    if deps == "*" or deps is None:
        return None
    return set(deps)


def filter_bundle(bundle: Dict[str, Any], allowed: Optional[Set[str]]) -> Dict[str, Any]:
    """Restrict a data bundle to the departments a user may see.

    Department-dimensioned sections (accounts, monthly actuals,
    transactions, positions) are filtered; fund-level sections pass
    through. The result notes its scope in meta.department_scope.
    """
    if allowed is None:
        return bundle
    out = dict(bundle)

    accounts = [a for a in bundle.get("accounts", [])
                if a.get("department") in allowed]
    visible_accounts = {a["account_number"] for a in accounts}
    out["accounts"] = accounts
    out["monthly_actuals"] = [m for m in bundle.get("monthly_actuals", [])
                              if m.get("account_number") in visible_accounts]
    out["transactions"] = [t for t in bundle.get("transactions", [])
                           if t.get("department") in allowed]
    out["positions"] = [p for p in bundle.get("positions", [])
                        if p.get("department") in allowed]
    out["departments"] = [d for d in bundle.get("departments", []) if d in allowed]

    meta = dict(bundle.get("meta", {}))
    meta["department_scope"] = sorted(allowed)
    out["meta"] = meta
    return out


def filter_pacing_rows(rows: List[Dict[str, Any]],
                       allowed: Optional[Set[str]]) -> List[Dict[str, Any]]:
    if allowed is None:
        return rows
    return [r for r in rows if r.get("Department") in allowed]
