"""
Seed a sample general-ledger database for local development and demos.

The production deployment loads GL data from the Caselle ERP adapter into
databases/core/govsight_all_in_one_data.db. That database is not committed
to the repository, so this script generates a representative sample:
10 revenue accounts and 50 expense accounts across 10 departments, plus
payroll accounts (5100/5200) which the Budget Playground excludes.

Usage: python3 scripts/seed_sample_gl.py
"""

import os
import random
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "databases", "core",
                       "govsight_all_in_one_data.db")

DEPARTMENTS = [
    ("10", "Administration"),
    ("15", "Finance"),
    ("20", "Police"),
    ("25", "Fire"),
    ("30", "Public Works"),
    ("35", "Parks and Recreation"),
    ("40", "Community Development"),
    ("45", "Utilities"),
    ("50", "Library"),
    ("55", "Information Technology"),
]

REVENUE_ACCOUNTS = [
    ("4100", "Property Tax Revenue"),
    ("4150", "Sales Tax Revenue"),
    ("4200", "Franchise Fees"),
    ("4250", "Licenses and Permits"),
    ("4300", "Intergovernmental Revenue"),
    ("4350", "Charges for Services"),
    ("4400", "Fines and Forfeitures"),
    ("4450", "Investment Earnings"),
    ("4500", "Impact Fees"),
    ("4550", "Miscellaneous Revenue"),
]

EXPENSE_OBJECTS = [
    ("5300", "Professional Services"),
    ("5350", "Supplies and Materials"),
    ("5400", "Utilities and Communications"),
    ("5450", "Repairs and Maintenance"),
    ("5500", "Capital Outlay"),
]

PAYROLL_OBJECTS = [
    ("5100", "Salaries and Wages"),
    ("5200", "Employee Benefits"),
]


def main():
    random.seed(42)  # deterministic sample data
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gl_accounts (
            account_number TEXT PRIMARY KEY,
            account_name   TEXT NOT NULL,
            account_type   TEXT NOT NULL,
            department     TEXT NOT NULL,
            fund           TEXT NOT NULL DEFAULT '10',
            budget_amount  REAL NOT NULL,
            ytd_actual     REAL NOT NULL
        )
    """)
    cur.execute("DELETE FROM gl_accounts")

    rows = []
    for obj, name in REVENUE_ACCOUNTS:
        budget = random.randrange(200, 4000) * 1000
        ytd = round(budget * random.uniform(0.35, 0.65), 2)
        rows.append((f"10-00-{obj}", name, "Revenue", "General Revenue",
                     "10", budget, ytd))

    for dept_code, dept_name in DEPARTMENTS:
        for obj, obj_name in EXPENSE_OBJECTS:
            budget = random.randrange(50, 900) * 1000
            ytd = round(budget * random.uniform(0.30, 0.70), 2)
            rows.append((f"10-{dept_code}-{obj}", f"{dept_name} {obj_name}",
                         "Expense", dept_name, "10", budget, ytd))
        for obj, obj_name in PAYROLL_OBJECTS:
            budget = random.randrange(300, 2500) * 1000
            ytd = round(budget * random.uniform(0.40, 0.60), 2)
            rows.append((f"10-{dept_code}-{obj}", f"{dept_name} {obj_name}",
                         "Expense", dept_name, "10", budget, ytd))

    cur.executemany(
        "INSERT INTO gl_accounts VALUES (?, ?, ?, ?, ?, ?, ?)", rows)

    # Monthly actual history (two prior fiscal years) with realistic
    # municipal seasonality so the reforecast engine has curves to learn:
    # property tax arrives in Nov/Dec lumps, sales tax has a holiday bump,
    # most expenses run level with a summer lift for field departments.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_actuals (
            account_number TEXT NOT NULL,
            fiscal_year    INTEGER NOT NULL,
            month          INTEGER NOT NULL,   -- calendar month 1-12
            actual         REAL NOT NULL,
            PRIMARY KEY (account_number, fiscal_year, month)
        )
    """)
    cur.execute("DELETE FROM monthly_actuals")

    def monthly_weights(account_number, account_name):
        months = {m: 1.0 for m in range(1, 13)}
        name = account_name.lower()
        if "property tax" in name:
            # Utah property tax due Nov 30: the year concentrates in Nov/Dec
            months = {m: 0.25 for m in range(1, 13)}
            months[11], months[12], months[1] = 6.0, 2.5, 0.8
        elif "sales tax" in name:
            months[12], months[1], months[6], months[7] = 1.5, 1.3, 1.15, 1.15
        elif "investment earnings" in name:
            pass  # level
        elif any(dept in account_number for dept in ("-30-", "-35-")):
            # Public Works / Parks: summer-heavy spending
            for m in (5, 6, 7, 8, 9):
                months[m] = 1.5
        total = sum(months.values())
        return {m: w / total for m, w in months.items()}

    monthly_rows = []
    for (acct, name, _atype, _dept, _fund, budget, _ytd) in rows:
        weights = monthly_weights(acct, name)
        for fy_offset, scale in ((2, 0.94), (1, 0.97)):  # two prior years
            fiscal_year = 2025 - fy_offset
            annual = budget * scale * random.uniform(0.96, 1.04)
            for month, w in weights.items():
                monthly_rows.append((
                    acct, fiscal_year, month,
                    round(annual * w * random.uniform(0.92, 1.08), 2)))
    cur.executemany(
        "INSERT INTO monthly_actuals VALUES (?, ?, ?, ?)", monthly_rows)

    conn.commit()
    conn.close()
    print(f"Seeded {len(rows)} GL accounts and {len(monthly_rows)} monthly "
          f"actuals into {os.path.normpath(DB_PATH)}")


if __name__ == "__main__":
    main()
