"""
Live data bundle and insight endpoints for the SPA.

/api/data/bundle returns the exact shape the frontend views were built
against (the demo_data.json contract), assembled from the live
canonical stores. This is the strangler seam: every Vatica/Navi data
view runs unchanged on live data the moment this endpoint feeds it.

Sections without a live source yet (economic series, balance sheet when
no balance data is synced) fall back to bundled defaults and say so in
meta.sources, so the UI can badge live vs sample per section.
"""

import json
import os
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from modules.api.routers.auth import require_user

router = APIRouter(prefix="/api/data", tags=["data"],
                   dependencies=[Depends(require_user)])

from modules.tenancy.context import tenant_db_path

def CANONICAL_DB() -> str:
    return tenant_db_path(os.path.join("core", "govsight_all_in_one_data.db"))

def PAYROLL_DB() -> str:
    return tenant_db_path("payroll_city_payroll_demo (1).db")
DEMO_JSON = os.path.join("public", "demo", "demo_data.json")


def _conn() -> Optional[sqlite3.Connection]:
    if not os.path.exists(CANONICAL_DB()):
        return None
    conn = sqlite3.connect(CANONICAL_DB())
    conn.row_factory = sqlite3.Row
    return conn


def _demo_defaults() -> Dict[str, Any]:
    try:
        with open(DEMO_JSON) as fh:
            return json.load(fh)
    except Exception:
        return {}


def _live_positions() -> Optional[List[Dict[str, Any]]]:
    """Positions from the connected payroll system, in the bundle's shape.
    The loaded-benefits rate comes from the canonical payroll rates so the
    Personnel workbook matches the PBB calculation engine."""
    if not os.path.exists(PAYROLL_DB()):
        return None
    try:
        from modules.navi.payroll_rates import DEFAULT_PAYROLL_RATES as rates
        benefits_pct = round(
            rates["std_benefits_pct"] + rates["retirement_pct"]
            + rates["fica_pct"] + rates["medicare_pct"]
            + rates["unemployment_pct"] + rates["workers_comp_pct"], 4)
        conn = sqlite3.connect(PAYROLL_DB())
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT e.EmployeeID AS id, e.Position AS title,
                      e.Department AS department, e.FTE AS fte,
                      COALESCE(AVG(ph.GrossPay) * :periods, 0) AS annual
               FROM Employees e
               LEFT JOIN PaycheckHeaders ph ON ph.EmployeeID = e.EmployeeID
               WHERE e.Position IS NOT NULL
               GROUP BY e.EmployeeID, e.Position, e.Department, e.FTE""",
            {"periods": rates["pay_periods"]}).fetchall()
        conn.close()
        out = [{
            "position_id": str(r["id"]), "title": r["title"],
            "department": r["department"] or "Unassigned",
            "fte": float(r["fte"] or 1.0),
            "annual_salary": round(float(r["annual"]), 2),
            "benefits_pct": benefits_pct, "status": "Filled",
        } for r in rows if float(r["annual"] or 0) > 0]
        return out or None
    except Exception:
        return None


@router.get("/bundle")
def data_bundle(user: dict = Depends(require_user)):
    from modules.tenancy.acl import allowed_departments, filter_bundle
    from modules.tenancy.context import DEFAULT_TENANT, current_tenant

    # Sample-data fallbacks belong to the founding demo city only; a new
    # city starts empty until its ERP data is ingested.
    if current_tenant() == DEFAULT_TENANT:
        demo = _demo_defaults()
    else:
        demo = {"city": {"name": user.get("tenant_name", "")},
                "departments": []}
    sources: Dict[str, str] = {}
    bundle: Dict[str, Any] = {}

    conn = _conn()
    tables = set()
    if conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}

    # accounts + monthly + transactions from the canonical store
    if conn and "gl_accounts" in tables:
        bundle["accounts"] = [dict(r) for r in conn.execute(
            "SELECT account_number, account_name, account_type, department, "
            "fund, budget_amount, ytd_actual FROM gl_accounts")]
        sources["accounts"] = "live"
    else:
        bundle["accounts"] = demo.get("accounts", [])
        sources["accounts"] = "sample"

    if conn and "monthly_actuals" in tables:
        bundle["monthly_actuals"] = [dict(r) for r in conn.execute(
            "SELECT account_number, fiscal_year, month, actual FROM monthly_actuals")]
        sources["monthly_actuals"] = "live"
    else:
        bundle["monthly_actuals"] = demo.get("monthly_actuals", [])
        sources["monthly_actuals"] = "sample"

    if conn and "canonical_transactions" in tables:
        rows = conn.execute(
            "SELECT source_transaction_id, transaction_date, account_number, "
            "amount, vendor_name, description, department, fund "
            "FROM canonical_transactions").fetchall()
        names = {a["account_number"]: a["account_name"]
                 for a in bundle["accounts"]}
        bundle["transactions"] = [{
            "id": r["source_transaction_id"], "date": r["transaction_date"],
            "account_number": r["account_number"],
            "account_name": names.get(r["account_number"], ""),
            "department": r["department"] or "", "fund": r["fund"] or "",
            "vendor": r["vendor_name"] or "", "amount": abs(float(r["amount"])),
            "description": r["description"] or "",
        } for r in rows]
        sources["transactions"] = "live"
    else:
        bundle["transactions"] = demo.get("transactions", [])
        sources["transactions"] = "sample"

    # Positions come from the payroll system when one is connected
    live_positions = _live_positions()
    if live_positions:
        bundle["positions"] = live_positions
        sources["positions"] = "live"
    else:
        bundle["positions"] = demo.get("positions", [])
        sources["positions"] = "sample"

    # Sections with no live pipeline yet ship bundled defaults, labeled
    for key in ("balance_sheet", "scenarios", "economic",
                "funds", "departments"):
        bundle[key] = demo.get(key, [])
        sources[key] = "sample"

    # City block comes from the admin-managed City Profile - it drives
    # Economic Indicators localization (Census FIPS, weather lat/lon),
    # branding, and AI context
    from modules.tenancy.city_profile import bundle_city
    bundle["city"] = bundle_city(current_tenant(), user.get("tenant_name", ""),
                                 current_tenant() == DEFAULT_TENANT)
    sources["city"] = "profile" if bundle["city"].get("name") else "sample"

    # Live GL can supply the fund and department lists directly
    if bundle.get("accounts"):
        live_funds = sorted({a.get("fund") for a in bundle["accounts"] if a.get("fund")})
        live_depts = sorted({a.get("department") for a in bundle["accounts"]
                             if a.get("department")})
        if not bundle.get("departments") and live_depts:
            bundle["departments"] = live_depts
        if not bundle.get("funds") and live_funds:
            bundle["funds"] = [{"code": f, "name": f"Fund {f}",
                                "classification": "Unclassified"} for f in live_funds]
    if conn:
        conn.close()

    today = date.today()
    bundle["reserve_policy_months"] = demo.get("reserve_policy_months", 2.0)
    bundle["meta"] = {
        "label": "GovSight data bundle",
        "organization": (bundle.get("city") or {}).get("name", "")
                        or user.get("tenant_name", ""),
        "tenant": current_tenant(),
        "current_fiscal_year": max(
            [m["fiscal_year"] for m in bundle["monthly_actuals"]] or [today.year]),
        "months_elapsed": max(
            [m["month"] for m in bundle["monthly_actuals"]
             if m["fiscal_year"] == max(
                 [x["fiscal_year"] for x in bundle["monthly_actuals"]] or [today.year])]
            or [today.month]),
        "sources": sources,
        "live_sections": sorted(k for k, v in sources.items() if v == "live"),
    }
    return filter_bundle(bundle, allowed_departments(user))


@router.get("/close-review")
def close_review(year: int, month: int, user: dict = Depends(require_user)):
    from fastapi import HTTPException
    from modules.tenancy.acl import allowed_departments
    # The close review reads the entire ledger (all departments' vendors
    # and amounts); it is a citywide-visibility function.
    if allowed_departments(user) is not None:
        raise HTTPException(
            status_code=403,
            detail="Monthly close review requires citywide department access. "
                   "Ask your city administrator to grant all-departments visibility.")
    from modules.vatica.monthly_close_assistant import MonthlyCloseAssistant
    report = MonthlyCloseAssistant(db_path=CANONICAL_DB()).run(year, month)
    return {
        "year": report.year, "month": report.month,
        "generated_at": report.generated_at,
        "transaction_count": report.transaction_count,
        "checks_run": report.checks_run,
        "checks_skipped": report.checks_skipped,
        "findings": [{"check": f.check, "severity": f.severity,
                      "message": f.message, "details": f.details}
                     for f in report.findings],
    }


@router.get("/cash-flow")
def cash_flow(starting_balance: float, policy_floor: float = 0.0,
              revenue_scale: float = 1.0, expense_scale: float = 1.0):
    from modules.treasury.cash_flow_engine import CashFlowEngine
    proj = CashFlowEngine(db_path=CANONICAL_DB()).project(
        starting_balance=starting_balance, policy_floor=policy_floor,
        revenue_scale=revenue_scale, expense_scale=expense_scale)
    return {
        "months": proj.months, "receipts": proj.receipts,
        "disbursements": proj.disbursements, "net_flow": proj.net_flow,
        "ending_balance": proj.ending_balance, "method": proj.method,
        "min_balance": proj.min_balance,
        "min_balance_month": proj.min_balance_month,
        "months_below_floor": proj.months_below_floor,
        "investable": proj.investable,
        "summary": proj.summary(),
    }


class _PacingUnavailable(Exception):
    pass


def compute_pacing() -> Dict[str, Any]:
    """Department pacing from the current tenant's monthly history.
    Internal (unfiltered); the HTTP endpoint applies the caller's ACL."""
    import pandas as pd
    conn = _conn()
    if not conn:
        return {"available": False, "reason": "no canonical database"}
    try:
        df = pd.read_sql_query(
            """SELECT g.department AS Department, m.fiscal_year AS FiscalYear,
                      m.month AS Month, g.budget_amount / 12.0 AS Budget,
                      m.actual AS Actual
               FROM monthly_actuals m
               JOIN gl_accounts g ON g.account_number = m.account_number
               WHERE g.account_type = 'Expense'""", conn)
    finally:
        conn.close()
    from modules.department_insights.department_insights import compute_budget_pacing
    out, year, month = compute_budget_pacing(df)
    if out is None:
        return {"available": False, "reason": "insufficient monthly history"}
    return {"available": True, "fiscal_year": int(year), "through_month": int(month),
            "rows": out.to_dict(orient="records")}


@router.get("/pacing")
def pacing(user: dict = Depends(require_user)):
    from modules.tenancy.acl import allowed_departments, filter_pacing_rows
    result = compute_pacing()
    if result.get("available"):
        result["rows"] = filter_pacing_rows(result["rows"], allowed_departments(user))
    return result
