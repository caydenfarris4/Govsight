"""
Build the rich demo dataset that powers the static (Cloudflare) GovSight
app's data views: public/demo/demo_data.json.

Contents (all clearly demo, internally consistent, and cross-linked):
  - 10 departments, 4 funds, 60 GL accounts (10 revenue / 50 expense)
  - 3 fiscal years of monthly actuals with municipal seasonality
    (property tax Nov/Dec lumps, holiday sales tax, summer field work)
  - ~5,000 vendor transactions over the last 18 months, joined to real
    accounts, with planted exceptions (duplicate payment, threshold
    hugging, outlier) for the Monthly Close view to find
  - Balance sheet accounts by fund and reserve policy inputs
  - 28 budgeted positions for the PBB view with rates and benefits
  - 3 saved planning scenarios for Report Comparison
  - 36 months of demo economic indicator series

Deterministic (seeded) so rebuilds are stable diffs.
"""

import json
import math
import os
import random

OUT_PATH = os.path.join("public", "demo", "demo_data.json")

FY_YEARS = [2024, 2025, 2026]      # fiscal years (Jan-Dec for simplicity here)
CURRENT_YEAR = 2026
CURRENT_MONTH = 7                   # July: 6 full months of the current year

DEPARTMENTS = [
    ("10", "Administration"), ("15", "Finance"), ("20", "Police"),
    ("25", "Fire"), ("30", "Public Works"), ("35", "Parks and Recreation"),
    ("40", "Community Development"), ("45", "Utilities"), ("50", "Library"),
    ("55", "Information Technology"),
]

FUNDS = [
    ("10", "General Fund", "Unrestricted"),
    ("20", "Special Revenue", "Restricted"),
    ("30", "Capital Projects", "Capital"),
    ("40", "Enterprise (Water/Sewer)", "Unrestricted"),
]

# Revenue budgets sum to ~$35.8M against ~$34.9M of expense budgets -
# a realistic adopted budget with a modest surplus
REVENUE_ACCOUNTS = [
    ("4100", "Property Tax Revenue", 11200),
    ("4150", "Sales Tax Revenue", 9200),
    ("4200", "Franchise Fees", 1900),
    ("4250", "Licenses and Permits", 1600),
    ("4300", "Intergovernmental Revenue", 3000),
    ("4350", "Charges for Services", 4500),
    ("4400", "Fines and Forfeitures", 550),
    ("4450", "Investment Earnings", 1000),
    ("4500", "Impact Fees", 2350),
    ("4550", "Miscellaneous Revenue", 500),
]  # amounts in $k

EXPENSE_OBJECTS = [
    ("5100", "Salaries and Wages", 0.44),
    ("5200", "Employee Benefits", 0.16),
    ("5300", "Professional Services", 0.10),
    ("5350", "Supplies and Materials", 0.08),
    ("5400", "Utilities and Communications", 0.07),
    ("5450", "Repairs and Maintenance", 0.08),
    ("5500", "Capital Outlay", 0.07),
]

DEPT_BUDGET_K = {  # annual expense budget per department, $k
    "Administration": 2400, "Finance": 1900, "Police": 8600, "Fire": 5900,
    "Public Works": 5200, "Parks and Recreation": 2300,
    "Community Development": 1500, "Utilities": 4800, "Library": 900,
    "Information Technology": 1400,
}

VENDORS = [
    "Rocky Mountain Power", "Dominion Energy", "Staples Inc", "Office Depot",
    "Acme Paving LLC", "Wasatch Fleet Service", "QuickFix Consulting",
    "Beehive Uniforms", "Great Basin Water Works", "Summit IT Solutions",
    "Canyon Landscaping", "Frontier Communications", "ProShield Insurance",
    "Mountain West Fuel", "Cache Valley Concrete", "Pioneer Legal Group",
    "Redrock Software", "Alpine Janitorial", "Silver State Labs",
    "Timp Auto Parts", "Jordan River Nursery", "Bonneville Printing",
    "Deseret Safety Supply", "Oquirrh Engineering", "Golden Spike Tools",
]

POSITIONS = [
    ("City Manager", "Administration", 165000), ("Assistant City Manager", "Administration", 128000),
    ("Finance Director", "Finance", 142000), ("Senior Accountant", "Finance", 88000),
    ("Accountant", "Finance", 72000), ("Payroll Specialist", "Finance", 61000),
    ("Police Chief", "Police", 148000), ("Police Captain", "Police", 118000),
    ("Police Sergeant", "Police", 96000), ("Police Officer II", "Police", 78000),
    ("Police Officer I", "Police", 66000), ("Dispatcher", "Police", 52000),
    ("Fire Chief", "Fire", 141000), ("Fire Captain", "Fire", 108000),
    ("Firefighter/Paramedic", "Fire", 74000), ("Firefighter", "Fire", 62000),
    ("Public Works Director", "Public Works", 132000), ("Streets Supervisor", "Public Works", 87000),
    ("Equipment Operator", "Public Works", 58000), ("Maintenance Worker II", "Public Works", 49000),
    ("Parks Director", "Parks and Recreation", 112000), ("Recreation Coordinator", "Parks and Recreation", 56000),
    ("Parks Maintenance Lead", "Parks and Recreation", 54000),
    ("Planning Director", "Community Development", 121000), ("City Planner", "Community Development", 82000),
    ("Building Inspector", "Community Development", 71000),
    ("IT Director", "Information Technology", 126000), ("Systems Administrator", "Information Technology", 84000),
]


def month_weights(kind, dept=None):
    w = {m: 1.0 for m in range(1, 13)}
    if kind == "property_tax":
        w = {m: 0.22 for m in range(1, 13)}
        w[11], w[12], w[1] = 6.5, 2.2, 0.7
    elif kind == "sales_tax":
        w[12], w[1], w[6], w[7], w[8] = 1.5, 1.35, 1.15, 1.2, 1.1
    elif kind == "impact_fees":
        for m in (4, 5, 6, 7, 8, 9):
            w[m] = 1.7
    elif kind == "field_dept":
        for m in (5, 6, 7, 8, 9):
            w[m] = 1.5
    total = sum(w.values())
    return {m: v / total for m, v in w.items()}


def revenue_kind(name):
    if "Property Tax" in name:
        return "property_tax"
    if "Sales Tax" in name:
        return "sales_tax"
    if "Impact" in name:
        return "impact_fees"
    return "flat"


def main():
    rng = random.Random(2026)
    accounts = []
    monthly = []          # {account, fy, month, actual}
    dept_names = [d[1] for d in DEPARTMENTS]

    # --- Revenue accounts -------------------------------------------------
    for obj, name, base_k in REVENUE_ACCOUNTS:
        acct = f"10-00-{obj}"
        weights = month_weights(revenue_kind(name))
        budget = base_k * 1000
        accounts.append({
            "account_number": acct, "account_name": name,
            "account_type": "Revenue", "department": "General Revenue",
            "fund": "10", "budget_amount": budget,
        })
        for fy in FY_YEARS:
            growth = 1.0 + 0.032 * (fy - FY_YEARS[0])
            annual = budget * growth * rng.uniform(0.97, 1.03)
            months = range(1, 13) if fy < CURRENT_YEAR else range(1, CURRENT_MONTH)
            for m in months:
                monthly.append({
                    "account_number": acct, "fiscal_year": fy, "month": m,
                    "actual": round(annual * weights[m] * rng.uniform(0.93, 1.07), 2),
                })

    # --- Expense accounts -------------------------------------------------
    for dept_code, dept_name in DEPARTMENTS:
        dept_annual = DEPT_BUDGET_K[dept_name] * 1000
        kind = "field_dept" if dept_name in ("Public Works", "Parks and Recreation") else "flat"
        weights = month_weights(kind)
        for obj, obj_name, share in EXPENSE_OBJECTS:
            acct = f"10-{dept_code}-{obj}"
            budget = round(dept_annual * share, 2)
            accounts.append({
                "account_number": acct, "account_name": f"{dept_name} {obj_name}",
                "account_type": "Expense", "department": dept_name,
                "fund": "10", "budget_amount": budget,
            })
            # Community Development runs hot in 2026 (a pacing story);
            # Library runs under
            hot = 1.18 if dept_name == "Community Development" else \
                  0.86 if dept_name == "Library" else 1.0
            for fy in FY_YEARS:
                annual = budget * rng.uniform(0.94, 1.0)
                if fy == CURRENT_YEAR:
                    annual *= hot
                months = range(1, 13) if fy < CURRENT_YEAR else range(1, CURRENT_MONTH)
                for m in months:
                    monthly.append({
                        "account_number": acct, "fiscal_year": fy, "month": m,
                        "actual": round(annual * weights[m] * rng.uniform(0.9, 1.1), 2),
                    })

    # ytd_actual for the current year
    ytd = {}
    for row in monthly:
        if row["fiscal_year"] == CURRENT_YEAR:
            ytd[row["account_number"]] = ytd.get(row["account_number"], 0) + row["actual"]
    for acct in accounts:
        acct["ytd_actual"] = round(ytd.get(acct["account_number"], 0), 2)

    # --- Transactions (last 18 months, joined to expense accounts) --------
    transactions = []
    seq = 0
    expense_accounts = [a for a in accounts if a["account_type"] == "Expense"
                        and not a["account_number"].endswith(("5100", "5200"))]
    vendor_for_object = {
        "5300": ["QuickFix Consulting", "Pioneer Legal Group", "Oquirrh Engineering", "Silver State Labs"],
        "5350": ["Staples Inc", "Office Depot", "Deseret Safety Supply", "Golden Spike Tools", "Bonneville Printing"],
        "5400": ["Rocky Mountain Power", "Dominion Energy", "Frontier Communications"],
        "5450": ["Acme Paving LLC", "Wasatch Fleet Service", "Alpine Janitorial", "Timp Auto Parts", "Canyon Landscaping"],
        "5500": ["Cache Valley Concrete", "Summit IT Solutions", "Redrock Software", "Great Basin Water Works"],
    }
    periods = ([(2025, m) for m in range(1, 13)] +
               [(2026, m) for m in range(1, CURRENT_MONTH)])
    for year, m in periods:
        for a in expense_accounts:
            obj = a["account_number"][-4:]
            vendors = vendor_for_object.get(obj, VENDORS)
            monthly_spend = a["budget_amount"] / 12
            n = rng.randint(2, 5)
            for _ in range(n):
                seq += 1
                amount = round(max(35.0, rng.gauss(monthly_spend / n, monthly_spend / (n * 3))), 2)
                transactions.append({
                    "id": f"TX-{seq:06d}",
                    "date": f"{year}-{m:02d}-{rng.randint(1, 28):02d}",
                    "account_number": a["account_number"],
                    "account_name": a["account_name"],
                    "department": a["department"],
                    "fund": a["fund"],
                    "vendor": rng.choice(vendors),
                    "amount": amount,
                    "description": f"{a['account_name']} - invoice {rng.randint(1000, 9999)}",
                })

    # Planted close exceptions (June 2026, the latest complete month)
    transactions += [
        {"id": "TX-DUP-A", "date": "2026-06-09", "account_number": "10-30-5450",
         "account_name": "Public Works Repairs and Maintenance", "department": "Public Works",
         "fund": "10", "vendor": "Acme Paving LLC", "amount": 18750.00,
         "description": "Chip seal project - invoice 4471"},
        {"id": "TX-DUP-B", "date": "2026-06-12", "account_number": "10-30-5450",
         "account_name": "Public Works Repairs and Maintenance", "department": "Public Works",
         "fund": "10", "vendor": "Acme Paving LLC", "amount": 18750.00,
         "description": "Chip seal project - invoice 4471 (resubmitted)"},
        {"id": "TX-TH-A", "date": "2026-06-05", "account_number": "10-40-5300",
         "account_name": "Community Development Professional Services", "department": "Community Development",
         "fund": "10", "vendor": "QuickFix Consulting", "amount": 4950.00,
         "description": "Zoning study phase 1"},
        {"id": "TX-TH-B", "date": "2026-06-19", "account_number": "10-40-5300",
         "account_name": "Community Development Professional Services", "department": "Community Development",
         "fund": "10", "vendor": "QuickFix Consulting", "amount": 4890.00,
         "description": "Zoning study phase 2"},
        {"id": "TX-OUTLIER", "date": "2026-06-24", "account_number": "10-15-5350",
         "account_name": "Finance Supplies and Materials", "department": "Finance",
         "fund": "10", "vendor": "Staples Inc", "amount": 14200.00,
         "description": "Bulk order - review"},
    ]

    # --- Balance sheet ----------------------------------------------------
    balance_sheet = [
        {"account": "10-1010", "name": "Cash and Cash Equivalents", "fund": "10", "category": "Asset", "amount": 8200000},
        {"account": "10-1020", "name": "Investments (LGIP/Treasuries)", "fund": "10", "category": "Asset", "amount": 6400000},
        {"account": "10-1200", "name": "Accounts Receivable", "fund": "10", "category": "Asset", "amount": 1150000},
        {"account": "10-1300", "name": "Property Taxes Receivable", "fund": "10", "category": "Asset", "amount": 940000},
        {"account": "10-2010", "name": "Accounts Payable", "fund": "10", "category": "Liability", "amount": 1320000},
        {"account": "10-2100", "name": "Accrued Payroll Liabilities", "fund": "10", "category": "Liability", "amount": 610000},
        {"account": "10-3000", "name": "Unassigned Fund Balance", "fund": "10", "category": "Fund Balance", "amount": 9800000},
        {"account": "20-1010", "name": "Cash - Special Revenue", "fund": "20", "category": "Asset", "amount": 2100000},
        {"account": "20-3000", "name": "Restricted Fund Balance", "fund": "20", "category": "Fund Balance", "amount": 1980000},
        {"account": "30-1010", "name": "Cash - Capital Projects", "fund": "30", "category": "Asset", "amount": 5400000},
        {"account": "30-3000", "name": "Committed Fund Balance", "fund": "30", "category": "Fund Balance", "amount": 5150000},
        {"account": "40-1010", "name": "Cash - Enterprise", "fund": "40", "category": "Asset", "amount": 3300000},
        {"account": "40-1500", "name": "Utility Plant (net)", "fund": "40", "category": "Asset", "amount": 21400000},
        {"account": "40-2500", "name": "Revenue Bonds Payable", "fund": "40", "category": "Liability", "amount": 12800000},
        {"account": "40-3000", "name": "Net Position - Enterprise", "fund": "40", "category": "Fund Balance", "amount": 11900000},
    ]

    # --- Positions (PBB) --------------------------------------------------
    positions = []
    for i, (title, dept, salary) in enumerate(POSITIONS, 1):
        fte = 1.0
        vacant = title in ("Police Officer I", "Maintenance Worker II")
        positions.append({
            "position_id": f"P{i:03d}", "title": title, "department": dept,
            "fte": fte, "annual_salary": salary,
            "benefits_pct": 0.34 if salary < 100000 else 0.30,
            "status": "Vacant" if vacant else "Filled",
        })

    # --- Saved scenarios (Report Comparison) ------------------------------
    scenarios = [
        {"name": "Adopted Budget FY2026", "created": "2025-06-17",
         "total_cost": 34900000, "tax_revenue": 20200000, "grant_funding": 2100000,
         "bonds": 0, "reallocation": 0, "note": "Council-adopted baseline"},
        {"name": "Bridge Replacement Program", "created": "2026-02-04",
         "total_cost": 41200000, "tax_revenue": 20200000, "grant_funding": 6800000,
         "bonds": 5200000, "reallocation": 900000, "note": "Adds 3-year bridge capital program"},
        {"name": "Recession Stress Case", "created": "2026-05-22",
         "total_cost": 33600000, "tax_revenue": 17900000, "grant_funding": 2100000,
         "bonds": 0, "reallocation": 1400000, "note": "Sales tax -12%, hiring freeze"},
    ]

    # --- Economic indicators (demo series, labeled) -----------------------
    econ = {"months": [], "cpi_yoy": [], "unemployment": [], "fed_funds": [],
            "local_permits": []}
    for i in range(36):
        year = 2023 + (6 + i) // 12
        month = (6 + i) % 12 + 1
        econ["months"].append(f"{year}-{month:02d}")
        econ["cpi_yoy"].append(round(3.6 - 1.2 * (i / 35) + 0.25 * math.sin(i / 4), 2))
        econ["unemployment"].append(round(3.1 + 0.7 * (i / 35) + 0.2 * math.sin(i / 5.5), 2))
        econ["fed_funds"].append(round(5.35 - 1.1 * (i / 35), 2))
        econ["local_permits"].append(int(52 + 14 * math.sin((i % 12) / 12 * 2 * math.pi - 1.2) + rng.randint(-6, 6)))

    dataset = {
        "meta": {
            "label": "GovSight demo dataset",
            "generated_for": "demonstration and testing - not real municipal data",
            "current_fiscal_year": CURRENT_YEAR,
            "months_elapsed": CURRENT_MONTH - 1,
            "organization": "Spanish Fork (demo)",
        },
        "funds": [{"code": c, "name": n, "classification": cl} for c, n, cl in FUNDS],
        "departments": dept_names,
        "accounts": accounts,
        "monthly_actuals": monthly,
        "transactions": transactions,
        "balance_sheet": balance_sheet,
        "positions": positions,
        "scenarios": scenarios,
        "economic": econ,
        "reserve_policy_months": 2.0,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        json.dump(dataset, fh, separators=(",", ":"))
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"Wrote {OUT_PATH}: {len(accounts)} accounts, {len(monthly)} monthly rows, "
          f"{len(transactions)} transactions, {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
