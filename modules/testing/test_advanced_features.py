import streamlit as st
from ai_hub import ask_ai, simulate_adjustment
import pandas as pd
from modules.database.connection_manager import load_org_data

def test_advanced_features():
    st.title("Advanced Analysis Tools Demo")
    
    # Sample project data for the Legislative Impact Analyzer
    org = "cityA"
    selected_project_data = {"name": "Sample Project", "description": "Sample description"}
    project_cost = 2000000
    tax_revenue = 500000
    grant = 300000
    
    # === Legislative Impact Analyzer Tab ===
    st.subheader(" Legislative Impact Analyzer")
    st.markdown("Analyze how proposed or recent legislation could impact your funding scenario.")
    bill_topic = st.text_input("Enter Bill Title or Topic", placeholder="e.g., Utah SB110 - Gas Tax Adjustment")
    selected_sources = st.multiselect("Regulatory Sources", ["gasb", "irs", "congress", "utah"], default=["utah", "congress"])

    if st.button("Analyze Legislation"):
        if bill_topic:
            # Use a DataFrame with basic project info for context
            scenario_df = pd.DataFrame({
                "Item": ["Project", "Total Cost", "Tax Revenue", "Grant Funding"],
                "Value": [selected_project_data["name"], project_cost, tax_revenue, grant]
            })
            summary = ask_ai(f"What are the financial impacts of the legislation or policy related to: {bill_topic}", df=scenario_df, sources=selected_sources)
            st.markdown("### AI Legislative Summary")
            st.markdown(summary)
        else:
            st.warning("Please enter a bill or policy topic.")

    # === What-If Scenario Simulator ===
    st.subheader(" What-If Scenario Simulator")
    st.markdown("Simulate how hypothetical changes could affect your departmental budgets.")
    scenario_input = st.text_area("Describe your hypothetical change", placeholder="E.g., Increase Public Works overtime by 15% for FY25")
    if st.button("Simulate Adjustment"):
        df = load_org_data(org)
        modified = simulate_adjustment(scenario_input, df)
        if not modified.empty:
            st.success("Simulation completed")
            st.dataframe(modified)
            st.markdown("### AI Summary")
            st.markdown(ask_ai(f"What is the budget implication of this scenario: {scenario_input}", modified))
        else:
            st.warning("AI could not simulate changes for this request.")

if __name__ == "__main__":
    test_advanced_features()