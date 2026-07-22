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

CANONICAL_DB = os.path.join("databases", "core", "govsight_all_in_one_data.db")
DEMO_JSON = os.path.join("public", "demo", "demo_data.json")


def _conn() -> Optional[sqlite3.Connection]:
    if not os.path.exists(CANONICAL_DB):
        return None
    conn = sqlite3.connect(CANONICAL_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _demo_defaults() -> Dict[str, Any]:
    try:
        with open(DEMO_JSON) as fh:
            return json.load(fh)
    except Exception:
        return {}


@router.get("/bundle")
def data_bundle():
    demo = _demo_defaults()
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

    # Sections with no live pipeline yet ship bundled defaults, labeled
    for key in ("balance_sheet", "positions", "scenarios", "economic",
                "funds", "departments", "city"):
        bundle[key] = demo.get(key, [] if key != "city" else {})
        sources[key] = "sample"
    if conn:
        conn.close()

    today = date.today()
    bundle["reserve_policy_months"] = demo.get("reserve_policy_months", 2.0)
    bundle["meta"] = {
        "label": "GovSight data bundle",
        "organization": (demo.get("city") or {}).get("name", ""),
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
    return bundle


@router.get("/close-review")
def close_review(year: int, month: int):
    from modules.vatica.monthly_close_assistant import MonthlyCloseAssistant
    report = MonthlyCloseAssistant().run(year, month)
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
    proj = CashFlowEngine().project(
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


@router.get("/pacing")
def pacing():
    """Department pacing from the canonical monthly history."""
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
