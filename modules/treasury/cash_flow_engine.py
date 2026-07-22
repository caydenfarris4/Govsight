"""
Cash flow forecasting engine.

Answers the treasurer's two standing questions:
  1. What will the cash balance be each month for the next year?
  2. How much cash can be invested, and for how long, without risking
     the operating floor?

Method: receipts (Revenue accounts) and disbursements (Expense accounts)
follow each fund's historical monthly seasonality, learned from the
monthly_actuals history in the canonical GL store — the same curves the
Budget Playground reforecast uses. Projected annual totals default to the
current budget and can be scaled. The projection then walks the balance
forward from a starting cash position.

The engine is deliberately free of Streamlit so it can be unit-tested
and reused by the API layer.
"""

import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

CANONICAL_DB_PATH = os.path.join("databases", "core", "govsight_all_in_one_data.db")


@dataclass
class CashFlowProjection:
    months: List[str]                       # "2026-08" style labels
    receipts: List[float]
    disbursements: List[float]
    net_flow: List[float]
    ending_balance: List[float]
    starting_balance: float
    policy_floor: float
    method: str                             # 'seasonal' | 'uniform'
    min_balance: float = 0.0
    min_balance_month: str = ""
    months_below_floor: List[str] = field(default_factory=list)
    investable: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> Dict[str, object]:
        return {
            "starting_balance": self.starting_balance,
            "min_balance": self.min_balance,
            "min_balance_month": self.min_balance_month,
            "months_below_floor": self.months_below_floor,
            "investable": self.investable,
            "method": self.method,
        }


class CashFlowEngine:
    def __init__(self, db_path: str = CANONICAL_DB_PATH):
        self.db_path = db_path

    # -- data ---------------------------------------------------------------

    def _load_history(self) -> Dict[str, Dict[int, List[float]]]:
        """{'Revenue'|'Expense': {fiscal_year: [12 calendar months of actuals]}}"""
        if not os.path.exists(self.db_path):
            return {}
        conn = sqlite3.connect(self.db_path)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "monthly_actuals" not in tables or "gl_accounts" not in tables:
                return {}
            rows = conn.execute("""
                SELECT g.account_type, m.fiscal_year, m.month, SUM(m.actual)
                FROM monthly_actuals m
                JOIN gl_accounts g ON g.account_number = m.account_number
                WHERE g.account_type IN ('Revenue', 'Expense')
                GROUP BY g.account_type, m.fiscal_year, m.month
            """).fetchall()
        finally:
            conn.close()
        out: Dict[str, Dict[int, List[float]]] = {}
        for atype, fy, month, total in rows:
            out.setdefault(atype, {}).setdefault(fy, [0.0] * 12)[month - 1] = float(total or 0)
        return out

    def _load_budget_totals(self) -> Dict[str, float]:
        if not os.path.exists(self.db_path):
            return {}
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute("""
                SELECT account_type, SUM(budget_amount) FROM gl_accounts
                WHERE account_type IN ('Revenue', 'Expense')
                GROUP BY account_type
            """).fetchall()
        finally:
            conn.close()
        return {atype: float(total or 0) for atype, total in rows}

    @staticmethod
    def _monthly_shares(history: Dict[int, List[float]]) -> Optional[List[float]]:
        """Average share of the annual total falling in each calendar month."""
        shares = [0.0] * 12
        years = 0
        for months in history.values():
            total = sum(abs(m) for m in months)
            if total <= 0:
                continue
            years += 1
            for i in range(12):
                shares[i] += abs(months[i]) / total
        if not years:
            return None
        return [s / years for s in shares]

    # -- projection ---------------------------------------------------------

    def project(self, starting_balance: float, policy_floor: float = 0.0,
                horizon_months: int = 12, start: Optional[date] = None,
                revenue_scale: float = 1.0, expense_scale: float = 1.0) -> CashFlowProjection:
        start = start or date.today()
        history = self._load_history()
        budgets = self._load_budget_totals()

        rev_shares = self._monthly_shares(history.get("Revenue", {}))
        exp_shares = self._monthly_shares(history.get("Expense", {}))
        method = "seasonal" if (rev_shares and exp_shares) else "uniform"
        if rev_shares is None:
            rev_shares = [1 / 12] * 12
        if exp_shares is None:
            exp_shares = [1 / 12] * 12

        annual_rev = budgets.get("Revenue", 0.0) * revenue_scale
        annual_exp = budgets.get("Expense", 0.0) * expense_scale

        months, receipts, disbursements, net_flow, balances = [], [], [], [], []
        balance = starting_balance
        year, month = start.year, start.month
        for _ in range(horizon_months):
            label = f"{year}-{month:02d}"
            r = annual_rev * rev_shares[month - 1]
            d = annual_exp * exp_shares[month - 1]
            balance += r - d
            months.append(label)
            receipts.append(round(r, 2))
            disbursements.append(round(d, 2))
            net_flow.append(round(r - d, 2))
            balances.append(round(balance, 2))
            month += 1
            if month > 12:
                month, year = 1, year + 1

        proj = CashFlowProjection(
            months=months, receipts=receipts, disbursements=disbursements,
            net_flow=net_flow, ending_balance=balances,
            starting_balance=starting_balance, policy_floor=policy_floor,
            method=method)

        min_idx = min(range(len(balances)), key=lambda i: balances[i])
        proj.min_balance = balances[min_idx]
        proj.min_balance_month = months[min_idx]
        proj.months_below_floor = [m for m, b in zip(months, balances)
                                   if b < policy_floor]
        proj.investable = self._investable_buckets(balances, policy_floor)
        return proj

    @staticmethod
    def _investable_buckets(balances: List[float], floor: float) -> Dict[str, float]:
        """How much can be locked up for each horizon without breaching the
        floor: the investable amount for N months is the minimum projected
        surplus over the next N months."""
        def surplus_through(n: int) -> float:
            window = balances[:n]
            return max(0.0, min(b - floor for b in window)) if window else 0.0
        return {
            "liquid_30d": round(surplus_through(1), 2),
            "term_90d": round(surplus_through(3), 2),
            "term_180d": round(surplus_through(6), 2),
            "term_365d": round(surplus_through(12), 2),
        }

    # -- 13-week view -------------------------------------------------------

    def weekly_view(self, projection: CashFlowProjection,
                    weeks: int = 13) -> Dict[str, List]:
        """13-week cash view interpolated from the monthly projection.

        Weekly figures are the month's flow spread across its weeks — an
        approximation, honestly labeled by the caller, until
        transaction-level history is connected.
        """
        labels, flows, balances = [], [], []
        balance = projection.starting_balance
        week = 0
        for i, month in enumerate(projection.months):
            if week >= weeks:
                break
            weeks_in_month = 4 if i % 3 != 2 else 5   # 4-4-5 approximation
            for w in range(weeks_in_month):
                if week >= weeks:
                    break
                flow = projection.net_flow[i] / weeks_in_month
                balance += flow
                labels.append(f"Wk {week + 1} ({month})")
                flows.append(round(flow, 2))
                balances.append(round(balance, 2))
                week += 1
        return {"labels": labels, "net_flow": flows, "ending_balance": balances}
