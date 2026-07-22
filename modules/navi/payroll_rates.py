"""
Canonical payroll tax and benefit rate defaults for Position-Based Budgeting.

Single source of truth shared by the Streamlit PBB engine (pbb_core.py) and
the PBB FastAPI backend (modules/api/pbb_api.py). These previously diverged
between the two engines (retirement 10% vs 12%, unemployment base $15,000 vs
$7,000), which made the same budget compute differently depending on which
surface ran the calculation.

Values are defaults for a demonstration configuration; production deployments
should override them per fiscal year through the admin settings, since FICA
wage bases and SUTA rates change annually.
"""

DEFAULT_PAYROLL_RATES = {
    'pay_periods': 26,
    'fica_pct': 0.062,
    'fica_wage_base': 176100,      # 2025 Social Security wage base
    'medicare_pct': 0.0145,
    'retirement_pct': 0.10,
    'unemployment_pct': 0.006,
    'unemployment_base': 15000,
    'workers_comp_pct': 0.012,
    'std_benefits_pct': 0.18,
}
