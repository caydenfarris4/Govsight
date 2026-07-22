"""
Demo data provisioning.

Ensures a complete, linked demo dataset exists so every module has data
to exercise: the canonical GL store with 80 accounts, two years of
seasonally-realistic monthly actual history (property-tax November lump,
holiday sales tax, summer-heavy public works), and six months of
canonical transactions with a few planted exceptions so the Monthly
Close Assistant has something to find.

Idempotent: provisioning is skipped when data already exists unless
force=True. Automatically invoked when admin_user signs in, so a fresh
deployment is fully testable immediately.
"""

import importlib.util
import logging
import os
import random
import sqlite3
from typing import Dict

logger = logging.getLogger("govsight.services.demo_data")

CANONICAL_DB_PATH = os.path.join("databases", "core", "govsight_all_in_one_data.db")
SEEDER_PATH = os.path.join("scripts", "seed_sample_gl.py")


def demo_data_status() -> Dict[str, int]:
    """Row counts of the demo-relevant tables (0 when absent)."""
    counts = {"gl_accounts": 0, "monthly_actuals": 0, "canonical_transactions": 0}
    if not os.path.exists(CANONICAL_DB_PATH):
        return counts
    conn = sqlite3.connect(CANONICAL_DB_PATH)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for table in counts:
            if table in tables:
                counts[table] = conn.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()
    return counts


def ensure_demo_data(force: bool = False) -> Dict[str, int]:
    """Provision the linked demo dataset if it is not already present."""
    status = demo_data_status()

    if force or status["gl_accounts"] == 0 or status["monthly_actuals"] == 0:
        _run_gl_seeder()

    status = demo_data_status()
    if force or status["canonical_transactions"] == 0:
        _seed_demo_transactions()

    final = demo_data_status()
    logger.info("Demo data ready: %s", final)
    return final


def _run_gl_seeder() -> None:
    """Load and run scripts/seed_sample_gl.py (the canonical GL seeder)."""
    spec = importlib.util.spec_from_file_location("seed_sample_gl", SEEDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The script seeds relative to its own directory; call main() with the
    # working directory unchanged since its DB_PATH is script-relative
    module.main()


def _seed_demo_transactions() -> None:
    """Six months of vendor transactions tied to real seeded GL accounts,
    with planted exceptions the Monthly Close Assistant should catch."""
    conn = sqlite3.connect(CANONICAL_DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS canonical_transactions (
                source_transaction_id TEXT PRIMARY KEY,
                transaction_date TEXT NOT NULL,
                account_number   TEXT NOT NULL,
                amount           REAL NOT NULL,
                direction        TEXT,
                vendor_name      TEXT,
                description      TEXT,
                department       TEXT,
                fund             TEXT
            )
        """)
        conn.execute("DELETE FROM canonical_transactions")

        accounts = conn.execute(
            "SELECT account_number, department, fund FROM gl_accounts "
            "WHERE account_type='Expense' LIMIT 12").fetchall()
        if not accounts:
            return

        vendors = ["Staples Inc", "Rocky Mountain Power", "Acme Paving",
                   "QuickFix LLC", "Wasatch Fleet Service", "Office Depot"]
        rng = random.Random(11)
        rows = []
        seq = 0
        # History: Feb-Jul 2026, ~8 transactions per account per month
        for month in range(2, 8):
            for acct, dept, fund in accounts:
                for _ in range(8):
                    seq += 1
                    rows.append((
                        f"DEMO-{seq:05d}",
                        f"2026-{month:02d}-{rng.randint(1, 28):02d}",
                        acct, round(rng.gauss(1200, 300), 2), "DR",
                        rng.choice(vendors), "demo transaction", dept, fund))

        # Planted exceptions in July (current close month)
        a0, d0, f0 = accounts[0]
        a1, d1, f1 = accounts[1]
        a2, d2, f2 = accounts[2]
        rows += [
            ("DEMO-OUTLIER", "2026-07-15", a0, 24800.00, "DR",
             "Staples Inc", "unusually large order", d0, f0),
            ("DEMO-DUP-1", "2026-07-10", a1, 12500.00, "DR",
             "Acme Paving", "invoice 884", d1, f1),
            ("DEMO-DUP-2", "2026-07-13", a1, 12500.00, "DR",
             "Acme Paving", "invoice 884 (again)", d1, f1),
            ("DEMO-TH-1", "2026-07-08", a2, 4950.00, "DR",
             "QuickFix LLC", "consulting phase 1", d2, f2),
            ("DEMO-TH-2", "2026-07-21", a2, 4899.00, "DR",
             "QuickFix LLC", "consulting phase 2", d2, f2),
        ]
        conn.executemany(
            "INSERT INTO canonical_transactions VALUES (?,?,?,?,?,?,?,?,?)",
            rows)
        conn.commit()
    finally:
        conn.close()
