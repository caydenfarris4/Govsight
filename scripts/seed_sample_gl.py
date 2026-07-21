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
    conn.commit()
    conn.close()
    print(f"Seeded {len(rows)} GL accounts into {os.path.normpath(DB_PATH)}")


if __name__ == "__main__":
    main()
