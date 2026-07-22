"""
Unit tests for the budget pacing engine
(modules/department_insights/department_insights.compute_budget_pacing).
"""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from modules.department_insights.department_insights import compute_budget_pacing  # noqa: E402


def build_frame(current_months=6, police_monthly_actual=850000):
    rows = []
    for fy in (2023, 2024):
        for m in range(1, 13):
            rows.append({"Department": "Parks", "FiscalYear": fy, "Month": m,
                         "Budget": 220000,
                         "Actual": 360000 if 5 <= m <= 9 else 120000})
            rows.append({"Department": "Police", "FiscalYear": fy, "Month": m,
                         "Budget": 700000, "Actual": 690000})
    for m in range(1, current_months + 1):
        rows.append({"Department": "Parks", "FiscalYear": 2025, "Month": m,
                     "Budget": 220000,
                     "Actual": 360000 if 5 <= m <= 9 else 120000})
        rows.append({"Department": "Police", "FiscalYear": 2025, "Month": m,
                     "Budget": 700000, "Actual": police_monthly_actual})
    return pd.DataFrame(rows)


class TestBudgetPacing(unittest.TestCase):
    def test_overspend_flagged_seasonal_not(self):
        out, year, month = compute_budget_pacing(build_frame())
        self.assertEqual((year, month), (2025, 6))
        police = out[out.Department == "Police"].iloc[0]
        parks = out[out.Department == "Parks"].iloc[0]
        self.assertEqual(police["Flag"], "OVER PACE")
        self.assertEqual(parks["Flag"], "")
        self.assertAlmostEqual(parks["Deviation (pp)"], 0.0, places=1)

    def test_underspend_flagged(self):
        out, _, _ = compute_budget_pacing(build_frame(police_monthly_actual=350000))
        police = out[out.Department == "Police"].iloc[0]
        self.assertEqual(police["Flag"], "UNDER PACE")

    def test_partial_year_budget_annualized(self):
        # % spent must use the ANNUAL budget even when only 6 months of
        # budget rows are loaded (the original bug doubled the pace)
        out, _, _ = compute_budget_pacing(build_frame(police_monthly_actual=690000))
        police = out[out.Department == "Police"].iloc[0]
        # 6 months x 690k / (700k x 12) = 49.3%
        self.assertAlmostEqual(police["% Spent"], 49.3, places=1)

    def test_graceful_without_month_column(self):
        df = pd.DataFrame([{"Department": "A", "FiscalYear": 2025,
                            "Budget": 100, "Actual": 50}])
        out, year, month = compute_budget_pacing(df)
        self.assertIsNone(out)

    def test_graceful_without_history(self):
        df = build_frame()
        df = df[df.FiscalYear == 2025]
        out, _, _ = compute_budget_pacing(df)
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
