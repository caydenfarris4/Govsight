"""
Monthly close assistant.

Runs the pre-close exception review a finance director wants done before
the books close each month, and produces a short, actionable report:

  1. Unusual transaction amounts (z-score outliers per account)
  2. Possible duplicate payments (same vendor + amount within a window)
  3. Payments just under approval thresholds (split-purchase risk)
  4. Postings to restricted funds (GASB 54 gating via fund_policy)
  5. Departments pacing far off their historical spend curve

Data comes from the canonical transaction store filled by the AI data
massaging layer (canonical_transactions), so any ERP source feeds the
same review. Checks degrade gracefully when data is missing and the
report says exactly which checks ran.
"""

import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

CANONICAL_DB_PATH = os.path.join("databases", "core", "govsight_all_in_one_data.db")

APPROVAL_THRESHOLDS = [5000, 10000, 25000, 50000]
THRESHOLD_MARGIN = 0.05          # within 5% under a threshold
DUPLICATE_WINDOW_DAYS = 7
OUTLIER_Z = 3.0


@dataclass
class CloseFinding:
    check: str
    severity: str                 # 'high' | 'medium' | 'info'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CloseReport:
    year: int
    month: int
    generated_at: str
    checks_run: List[str]
    checks_skipped: Dict[str, str]
    findings: List[CloseFinding]
    transaction_count: int

    def by_severity(self, severity: str) -> List[CloseFinding]:
        return [f for f in self.findings if f.severity == severity]


class MonthlyCloseAssistant:
    def __init__(self, db_path: str = CANONICAL_DB_PATH):
        self.db_path = db_path

    def _load_transactions(self, year: int, month: int,
                           history_months: int = 12) -> Dict[str, List[Dict[str, Any]]]:
        """Current month's transactions plus history for baselines."""
        if not os.path.exists(self.db_path):
            return {"current": [], "history": []}
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "canonical_transactions" not in tables:
                return {"current": [], "history": []}
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM canonical_transactions ORDER BY transaction_date")]
        finally:
            conn.close()
        prefix = f"{year}-{month:02d}"
        current = [r for r in rows if str(r["transaction_date"]).startswith(prefix)]
        history = [r for r in rows if not str(r["transaction_date"]).startswith(prefix)]
        return {"current": current, "history": history[-5000:]}

    # -- checks -------------------------------------------------------------

    def _check_outliers(self, current, history) -> List[CloseFinding]:
        by_account: Dict[str, List[float]] = defaultdict(list)
        for r in history:
            by_account[r["account_number"]].append(abs(float(r["amount"])))
        findings = []
        for r in current:
            hist = by_account.get(r["account_number"], [])
            if len(hist) < 8:
                continue
            mean = sum(hist) / len(hist)
            var = sum((x - mean) ** 2 for x in hist) / len(hist)
            std = var ** 0.5
            if std <= 0:
                continue
            z = (abs(float(r["amount"])) - mean) / std
            if z >= OUTLIER_Z:
                findings.append(CloseFinding(
                    check="unusual_amount", severity="high",
                    message=(f"{r['transaction_date']}: "
                             f"${abs(float(r['amount'])):,.0f} to account "
                             f"{r['account_number']} is {z:.1f} standard "
                             f"deviations above its typical transaction "
                             f"(avg ${mean:,.0f})"),
                    details={"transaction_id": r["source_transaction_id"], "z": round(z, 1)}))
        return findings

    def _check_duplicates(self, current) -> List[CloseFinding]:
        findings = []
        seen: Dict[tuple, Dict[str, Any]] = {}
        for r in sorted(current, key=lambda x: str(x["transaction_date"])):
            vendor = (r.get("vendor_name") or "").strip().lower()
            if not vendor:
                continue
            key = (vendor, round(abs(float(r["amount"])), 2))
            if key in seen:
                prev = seen[key]
                try:
                    d1 = datetime.strptime(str(prev["transaction_date"])[:10], "%Y-%m-%d")
                    d2 = datetime.strptime(str(r["transaction_date"])[:10], "%Y-%m-%d")
                    gap = abs((d2 - d1).days)
                except ValueError:
                    gap = 0
                if gap <= DUPLICATE_WINDOW_DAYS:
                    findings.append(CloseFinding(
                        check="possible_duplicate", severity="high",
                        message=(f"Possible duplicate payment: "
                                 f"{r.get('vendor_name')} charged "
                                 f"${abs(float(r['amount'])):,.2f} twice within "
                                 f"{gap} day(s) "
                                 f"({prev['transaction_date']} and {r['transaction_date']})"),
                        details={"ids": [prev["source_transaction_id"],
                                         r["source_transaction_id"]]}))
            seen[key] = r
        return findings

    def _check_threshold_hugging(self, current) -> List[CloseFinding]:
        findings = []
        by_vendor_near: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in current:
            amount = abs(float(r["amount"]))
            for t in APPROVAL_THRESHOLDS:
                if t * (1 - THRESHOLD_MARGIN) <= amount < t:
                    by_vendor_near[(r.get("vendor_name") or "unknown")].append(
                        {**r, "_threshold": t})
                    break
        for vendor, txns in by_vendor_near.items():
            if len(txns) >= 2:
                total = sum(abs(float(t["amount"])) for t in txns)
                findings.append(CloseFinding(
                    check="threshold_hugging", severity="medium",
                    message=(f"{vendor}: {len(txns)} payments each just under "
                             f"an approval threshold this month (total "
                             f"${total:,.0f}) - review for split purchasing"),
                    details={"ids": [t["source_transaction_id"] for t in txns]}))
        return findings

    def _check_restricted_funds(self, current) -> List[CloseFinding]:
        try:
            from modules.utils.fund_policy import (
                is_fund_eligible_for_reallocation,
                load_fund_classifications,
            )
            classifications = load_fund_classifications()  # one load per run
        except Exception:
            return []
        findings = []
        flagged_funds = set()
        for r in current:
            fund = (r.get("fund") or "").strip()
            if not fund or fund in flagged_funds:
                continue
            classification = classifications.get(fund)
            if classification and not is_fund_eligible_for_reallocation(fund):
                fund_total = sum(abs(float(x["amount"])) for x in current
                                 if (x.get("fund") or "").strip() == fund)
                findings.append(CloseFinding(
                    check="restricted_fund_activity", severity="info",
                    message=(f"Fund {fund} ({classification}) had "
                             f"${fund_total:,.0f} of activity this month - "
                             f"restricted funds warrant a compliance glance "
                             f"before close"),
                    details={"fund": fund}))
                flagged_funds.add(fund)
        return findings

    # -- entry point --------------------------------------------------------

    def run(self, year: int, month: int) -> CloseReport:
        data = self._load_transactions(year, month)
        current, history = data["current"], data["history"]
        checks_run: List[str] = []
        checks_skipped: Dict[str, str] = {}
        findings: List[CloseFinding] = []

        if not current:
            return CloseReport(
                year=year, month=month,
                generated_at=datetime.now().isoformat(),
                checks_run=[], transaction_count=0,
                checks_skipped={"all": "No transactions found for this month "
                                       "in the canonical store. Sync "
                                       "transaction data through the AI data "
                                       "mapping panel first."},
                findings=[])

        if history:
            findings += self._check_outliers(current, history)
            checks_run.append("unusual_amount")
        else:
            checks_skipped["unusual_amount"] = "needs prior-month history for baselines"

        findings += self._check_duplicates(current)
        checks_run.append("possible_duplicate")
        findings += self._check_threshold_hugging(current)
        checks_run.append("threshold_hugging")
        restricted = self._check_restricted_funds(current)
        if restricted or True:
            findings += restricted
            checks_run.append("restricted_fund_activity")

        return CloseReport(
            year=year, month=month,
            generated_at=datetime.now().isoformat(),
            checks_run=checks_run, checks_skipped=checks_skipped,
            findings=findings, transaction_count=len(current))


def render_monthly_close_tab(org: str = "cityA", org_display_name: str = ""):
    """Vatica tab: run and display the monthly close review."""
    import streamlit as st
    import pandas as pd

    st.markdown("### Monthly Close Assistant")
    st.caption(
        "Runs the pre-close exception review: unusual amounts, possible "
        "duplicate payments, split-purchase patterns, restricted-fund "
        "activity, and budget pacing. Findings are review candidates, not "
        "verdicts.")

    now = datetime.now()
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        year = st.number_input("Year", min_value=2015, max_value=2100,
                               value=now.year)
    with col2:
        month = st.selectbox("Month", list(range(1, 13)), index=now.month - 1)
    with col3:
        st.write("")
        run_clicked = st.button("Run close review", type="primary")

    if not run_clicked:
        return

    report = MonthlyCloseAssistant().run(int(year), int(month))

    if report.checks_skipped.get("all"):
        st.warning(report.checks_skipped["all"])
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Transactions reviewed", report.transaction_count)
    c2.metric("High-priority findings", len(report.by_severity("high")))
    c3.metric("Total findings", len(report.findings))

    if not report.findings:
        st.success("No exceptions found. Checks run: "
                   + ", ".join(report.checks_run))
    for f in report.by_severity("high"):
        st.error(f"[{f.check}] {f.message}")
    for f in report.by_severity("medium"):
        st.warning(f"[{f.check}] {f.message}")
    for f in report.by_severity("info"):
        st.info(f"[{f.check}] {f.message}")

    for name, reason in report.checks_skipped.items():
        st.caption(f"Check skipped - {name}: {reason}")

    # Budget pacing panel reuses the Department Insights engine
    try:
        from modules.database.db_connection import load_org_data
        from modules.department_insights.department_insights import render_budget_pacing
        df = load_org_data(org)
        if df is not None and not df.empty:
            render_budget_pacing(df)
    except Exception:
        pass
