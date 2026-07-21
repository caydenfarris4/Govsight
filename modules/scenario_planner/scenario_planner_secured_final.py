import streamlit as st
import db_connection
from modules.admin.admin_panel import get_user_departments, is_admin, is_finance_director
import pandas as pd
from summary_report_generator import generate_full_scenario_report

def run_scenario_planner():
    st.title("️ Scenario Planner (Final Version)")

    df = db_connection.load_org_data()
    if df.empty:
        st.warning("No data found.")
        st.stop()

    # Department restrictions
    allowed_depts = get_user_departments()
    if allowed_depts:
        df = df[df["Department"].isin(allowed_depts)]

    departments = sorted(df["Department"].unique())
    selected_dept = st.selectbox("Select Department for Scenario", departments)

    # Project inputs
    project_name = st.text_input("Enter Project Name")
    project_cost = st.number_input("Projected Project Cost", min_value=0, value=1000000)
    tax_increase = st.number_input("Projected Tax Revenue Increase", min_value=0, value=250000)
    grant_amount = st.number_input("Projected Grant Aid", min_value=0, value=300000)
    project_notes = st.text_area("Optional Project Notes", height=100)

    if st.button("Save Scenario"):
        if "saved_scenarios" not in st.session_state:
            st.session_state.saved_scenarios = []
        st.session_state.saved_scenarios.append({
            "name": project_name,
            "department": selected_dept,
            "cost": project_cost,
            "tax_increase": tax_increase,
            "grant_amount": grant_amount,
            "notes": project_notes
        })
        st.success(f"Scenario '{project_name}' saved successfully!")

    st.subheader("🔎 Department Budget Overview")
    df_dept = df[df["Department"] == selected_dept]
    st.dataframe(df_dept[["Fund", "FiscalYear", "Budget", "Actual"]])

    st.divider()

    st.subheader(" Auto-Generate Executive Scenario Report")
    if st.button(" Generate Executive Scenario Report PDF"):
        generate_full_scenario_report(
            project_name,
            selected_dept,
            project_cost,
            tax_increase,
            grant_amount,
            project_notes
        )