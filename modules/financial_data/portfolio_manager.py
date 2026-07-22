"""
Municipal investment portfolio tracking.

Tracks what the city actually holds — not just what it could buy — and
computes the treasurer's working numbers: the maturity ladder, weighted
average yield, upcoming reinvestment decisions, and the opportunity cost
of idle cash versus a benchmark rate.

Persistence is SQLite (databases/core/investments.db) so holdings survive
restarts and are shared across sessions.
"""

import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

PORTFOLIO_DB_PATH = os.path.join("databases", "core", "investments.db")

LADDER_BUCKETS = [
    ("0-30 days", 0, 30),
    ("31-90 days", 31, 90),
    ("91-180 days", 91, 180),
    ("181-365 days", 181, 365),
    ("1+ years", 366, 100000),
]


class PortfolioManager:
    def __init__(self, db_path: str = PORTFOLIO_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_type TEXT NOT NULL,   -- t-bill | cd | lgip | mmf | agency | other
                    description     TEXT NOT NULL,
                    principal       REAL NOT NULL,
                    rate            REAL NOT NULL,   -- annual %, as purchased
                    purchase_date   TEXT NOT NULL,   -- YYYY-MM-DD
                    maturity_date   TEXT,            -- NULL = open-ended (LGIP/MMF)
                    fund            TEXT DEFAULT '',
                    notes           TEXT DEFAULT '',
                    status          TEXT NOT NULL DEFAULT 'active',  -- active | matured | sold
                    created_at      TEXT NOT NULL,
                    updated_at      TEXT NOT NULL
                )
            """)

    # -- CRUD ---------------------------------------------------------------

    def add_holding(self, data: Dict[str, Any]) -> int:
        now = datetime.now().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO holdings (instrument_type, description, principal, rate, "
                "purchase_date, maturity_date, fund, notes, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
                (data["instrument_type"], data["description"], float(data["principal"]),
                 float(data["rate"]), data["purchase_date"], data.get("maturity_date"),
                 data.get("fund", ""), data.get("notes", ""), now, now))
            return cur.lastrowid

    def update_holding(self, holding_id: int, data: Dict[str, Any]) -> None:
        allowed = {"instrument_type", "description", "principal", "rate",
                   "purchase_date", "maturity_date", "fund", "notes", "status"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE holdings SET {sets}, updated_at=? WHERE id=?",
                (*fields.values(), datetime.now().isoformat(), holding_id))

    def delete_holding(self, holding_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM holdings WHERE id=?", (holding_id,))

    def list_holdings(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        query = "SELECT * FROM holdings"
        if not include_inactive:
            query += " WHERE status='active'"
        query += " ORDER BY maturity_date IS NULL, maturity_date"
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(query).fetchall()]

    # -- analytics ----------------------------------------------------------

    def analytics(self, idle_cash: float = 0.0,
                  benchmark_rate: Optional[float] = None) -> Dict[str, Any]:
        holdings = self.list_holdings()
        today = date.today()
        total = sum(h["principal"] for h in holdings)

        weighted_yield = (
            sum(h["principal"] * h["rate"] for h in holdings) / total
            if total else 0.0)

        ladder = []
        for label, lo, hi in LADDER_BUCKETS:
            bucket_total = 0.0
            for h in holdings:
                days = self._days_to_maturity(h, today)
                if days is not None and lo <= days <= hi:
                    bucket_total += h["principal"]
            ladder.append({"bucket": label, "principal": bucket_total})
        open_ended = sum(h["principal"] for h in holdings
                        if not h.get("maturity_date"))
        ladder.insert(0, {"bucket": "Liquid (no maturity)", "principal": open_ended})

        upcoming = []
        for h in holdings:
            days = self._days_to_maturity(h, today)
            if days is not None and days <= 60:
                upcoming.append({
                    "id": h["id"], "description": h["description"],
                    "principal": h["principal"], "rate": h["rate"],
                    "maturity_date": h["maturity_date"], "days_to_maturity": days,
                    "overdue": days < 0,
                })
        upcoming.sort(key=lambda u: u["days_to_maturity"])

        concentration = {}
        for h in holdings:
            concentration[h["instrument_type"]] = (
                concentration.get(h["instrument_type"], 0.0) + h["principal"])
        max_share = max(concentration.values()) / total * 100 if total else 0.0

        opportunity_cost = None
        if benchmark_rate is not None and idle_cash > 0:
            # Annual dollars left on the table by not investing idle cash at
            # the benchmark (assumes idle cash currently earns nothing; pass
            # the checking-account rate difference for a tighter figure)
            opportunity_cost = {
                "idle_cash": idle_cash,
                "benchmark_rate": benchmark_rate,
                "annual_cost": round(idle_cash * benchmark_rate / 100.0, 2),
                "monthly_cost": round(idle_cash * benchmark_rate / 100.0 / 12, 2),
            }

        return {
            "as_of": today.isoformat(),
            "holdings_count": len(holdings),
            "total_principal": total,
            "weighted_avg_yield": round(weighted_yield, 3),
            "ladder": ladder,
            "upcoming_maturities": upcoming,
            "concentration_by_type": [
                {"instrument_type": k, "principal": v,
                 "share_pct": round(v / total * 100, 1) if total else 0}
                for k, v in sorted(concentration.items(), key=lambda kv: -kv[1])],
            "max_type_concentration_pct": round(max_share, 1),
            "opportunity_cost": opportunity_cost,
        }

    @staticmethod
    def _days_to_maturity(holding: Dict[str, Any], today: date) -> Optional[int]:
        md = holding.get("maturity_date")
        if not md:
            return None
        try:
            return (datetime.strptime(md[:10], "%Y-%m-%d").date() - today).days
        except ValueError:
            return None


_manager: Optional[PortfolioManager] = None


def get_portfolio_manager() -> PortfolioManager:
    global _manager
    if _manager is None:
        _manager = PortfolioManager()
    return _manager
