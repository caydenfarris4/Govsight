"""
Unit tests for the treasury stack: cash flow engine, portfolio manager,
TreasuryDirect auction parsing, investment aggregator freshness, and the
monthly close assistant. All external calls are mocked; database-backed
tests run against temporary SQLite files.
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from modules.financial_data.treasury_api import TreasuryAPI  # noqa: E402
from modules.financial_data.portfolio_manager import PortfolioManager  # noqa: E402
from modules.treasury.cash_flow_engine import CashFlowEngine  # noqa: E402
from modules.vatica.monthly_close_assistant import MonthlyCloseAssistant  # noqa: E402


def build_gl_db(path, monthly=True):
    """Minimal canonical GL store with a November-lumpy revenue account."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE gl_accounts (
            account_number TEXT PRIMARY KEY, account_name TEXT NOT NULL,
            account_type TEXT NOT NULL, department TEXT DEFAULT '',
            fund TEXT DEFAULT '10', budget_amount REAL NOT NULL,
            ytd_actual REAL NOT NULL);
        CREATE TABLE monthly_actuals (
            account_number TEXT, fiscal_year INTEGER, month INTEGER,
            actual REAL, PRIMARY KEY (account_number, fiscal_year, month));
    """)
    conn.execute("INSERT INTO gl_accounts VALUES "
                 "('10-00-4100','Property Tax','Revenue','Rev','10',1200000,300000)")
    conn.execute("INSERT INTO gl_accounts VALUES "
                 "('10-20-5300','Police Services','Expense','Police','10',1180000,590000)")
    if monthly:
        for fy in (2023, 2024):
            for m in range(1, 13):
                rev = 700000 if m == 11 else 45000     # November lump
                exp = 100000                            # level spending
                conn.execute("INSERT INTO monthly_actuals VALUES (?,?,?,?)",
                             ("10-00-4100", fy, m, rev))
                conn.execute("INSERT INTO monthly_actuals VALUES (?,?,?,?)",
                             ("10-20-5300", fy, m, exp))
    conn.commit()
    conn.close()


class TestTreasuryAuctionParsing(unittest.TestCase):
    def test_latest_auction_wins_and_terms_map(self):
        payload = [
            {"securityTerm": "4-Week", "highInvestmentRate": "4.5",
             "auctionDate": "2026-07-14"},
            {"securityTerm": "4-Week", "highInvestmentRate": "4.4",
             "auctionDate": "2026-07-07"},
            {"securityTerm": "CMB", "highInvestmentRate": "4.6",
             "auctionDate": "2026-07-10"},
        ]
        api = TreasuryAPI()
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status = lambda: None
        with patch.object(api.session, "get", return_value=resp):
            api.get_auction_bill_rates.cache_clear()
            result = api.get_investment_opportunities()
        self.assertTrue(result["is_live"])
        self.assertEqual(len(result["opportunities"]), 1)  # CMB excluded
        opp = result["opportunities"][0]
        self.assertEqual(opp["rate"], 4.5)                 # latest auction
        self.assertEqual(opp["as_of"], "2026-07-14")

    def test_api_failure_reports_error_without_fabricating(self):
        api = TreasuryAPI()
        with patch.object(api.session, "get", side_effect=Exception("down")):
            api.get_auction_bill_rates.cache_clear()
            result = api.get_investment_opportunities()
        self.assertFalse(result["is_live"])
        self.assertEqual(result["opportunities"], [])


class TestPortfolioManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pm = PortfolioManager(db_path=os.path.join(self.tmp, "inv.db"))

    def test_weighted_yield_ladder_and_opportunity_cost(self):
        future = (date.today() + timedelta(days=60)).isoformat()
        self.pm.add_holding({"instrument_type": "t-bill", "description": "T-Bill",
                             "principal": 1_000_000, "rate": 4.0,
                             "purchase_date": "2026-01-01",
                             "maturity_date": future})
        self.pm.add_holding({"instrument_type": "lgip", "description": "LGIP",
                             "principal": 3_000_000, "rate": 5.0,
                             "purchase_date": "2026-01-01"})
        a = self.pm.analytics(idle_cash=2_000_000, benchmark_rate=4.5)
        self.assertAlmostEqual(a["weighted_avg_yield"], 4.75, places=2)
        liquid = next(b for b in a["ladder"] if b["bucket"] == "Liquid (no maturity)")
        self.assertEqual(liquid["principal"], 3_000_000)
        self.assertEqual(a["opportunity_cost"]["annual_cost"], 90_000.0)
        # A 60-day maturity is an upcoming reinvestment decision
        self.assertEqual(len(a["upcoming_maturities"]), 1)

    def test_crud_roundtrip(self):
        hid = self.pm.add_holding({"instrument_type": "cd", "description": "CD",
                                   "principal": 500000, "rate": 4.1,
                                   "purchase_date": "2026-01-01"})
        self.pm.update_holding(hid, {"rate": 4.2})
        self.assertEqual(self.pm.list_holdings()[0]["rate"], 4.2)
        self.pm.delete_holding(hid)
        self.assertEqual(self.pm.list_holdings(), [])


class TestCashFlowEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "gl.db")

    def test_seasonal_projection_and_investable_buckets(self):
        build_gl_db(self.db)
        eng = CashFlowEngine(db_path=self.db)
        proj = eng.project(starting_balance=1_000_000, policy_floor=200_000,
                           start=date(2026, 8, 1))
        self.assertEqual(proj.method, "seasonal")
        nov = proj.months.index("2026-11")
        self.assertEqual(proj.receipts[nov], max(proj.receipts),
                         "November must be the receipts peak")
        # Balance conservation: ending = start + sum(net flows)
        # (per-month rounding to cents can drift by pennies over a year)
        self.assertAlmostEqual(
            proj.ending_balance[-1],
            proj.starting_balance + sum(proj.net_flow), delta=1.0)
        # Investable never exceeds the minimum surplus over the window
        min_surplus_3m = min(b - 200_000 for b in proj.ending_balance[:3])
        self.assertAlmostEqual(proj.investable["term_90d"],
                               max(0, min_surplus_3m), places=2)

    def test_uniform_fallback_without_history(self):
        build_gl_db(self.db, monthly=False)
        proj = CashFlowEngine(db_path=self.db).project(
            starting_balance=1_000_000, start=date(2026, 8, 1))
        self.assertEqual(proj.method, "uniform")
        # Uniform: all receipt months equal
        self.assertAlmostEqual(min(proj.receipts), max(proj.receipts), places=2)

    def test_weekly_view_thirteen_weeks(self):
        build_gl_db(self.db)
        eng = CashFlowEngine(db_path=self.db)
        proj = eng.project(starting_balance=500_000, start=date(2026, 8, 1))
        wk = eng.weekly_view(proj)
        self.assertEqual(len(wk["labels"]), 13)
        self.assertEqual(len(wk["ending_balance"]), 13)


class TestMonthlyCloseAssistant(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "gl.db")
        conn = sqlite3.connect(self.db)
        conn.execute("""CREATE TABLE canonical_transactions (
            source_transaction_id TEXT PRIMARY KEY, transaction_date TEXT,
            account_number TEXT, amount REAL, direction TEXT,
            vendor_name TEXT, description TEXT, department TEXT, fund TEXT)""")
        rows = []
        for m in range(1, 7):                      # history baseline ~ $450
            for i in range(10):
                rows.append((f"H{m}-{i}", f"2026-{m:02d}-10", "10-15-5350",
                             430 + i * 5, "DR", "Staples", "", "Finance", "10"))
        rows += [
            ("C-1", "2026-07-05", "10-15-5350", 460, "DR", "Staples", "", "Finance", "10"),
            ("C-OUT", "2026-07-15", "10-15-5350", 9800, "DR", "Staples", "", "Finance", "10"),
            ("C-D1", "2026-07-10", "10-30-5450", 12500, "DR", "Acme", "", "PW", "10"),
            ("C-D2", "2026-07-12", "10-30-5450", 12500, "DR", "Acme", "", "PW", "10"),
            ("C-T1", "2026-07-08", "10-40-5300", 4950, "DR", "QuickFix", "", "CD", "10"),
            ("C-T2", "2026-07-21", "10-40-5300", 4899, "DR", "QuickFix", "", "CD", "10"),
        ]
        conn.executemany(
            "INSERT INTO canonical_transactions VALUES (?,?,?,?,?,?,?,?,?)", rows)
        conn.commit()
        conn.close()

    def test_planted_exceptions_are_caught(self):
        report = MonthlyCloseAssistant(db_path=self.db).run(2026, 7)
        checks = {f.check for f in report.findings}
        self.assertIn("unusual_amount", checks)
        self.assertIn("possible_duplicate", checks)
        self.assertIn("threshold_hugging", checks)

    def test_clean_month_produces_no_findings(self):
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM canonical_transactions WHERE "
                     "source_transaction_id LIKE 'C-%' AND "
                     "source_transaction_id != 'C-1'")
        conn.commit()
        conn.close()
        report = MonthlyCloseAssistant(db_path=self.db).run(2026, 7)
        self.assertEqual(report.findings, [])
        self.assertEqual(report.transaction_count, 1)

    def test_empty_month_says_so(self):
        report = MonthlyCloseAssistant(db_path=self.db).run(2030, 1)
        self.assertIn("all", report.checks_skipped)
        self.assertEqual(report.transaction_count, 0)


if __name__ == "__main__":
    unittest.main()
