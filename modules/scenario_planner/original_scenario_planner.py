"""
Scenario Planner Module

This module handles all functionality related to the Scenario Planner tab, including:
- Project selection and configuration
- Department budget reallocation
- Funding source allocation
- Visualization and analysis of funding scenarios
- Saving and loading scenarios
- Report generation
- Legislative impact analysis
- What-if scenario simulation

The module now uses a tabbed interface to organize functionality:
- Scenario Builder: Main funding scenario creation and analysis
- Legislative Impact Analyzer: Assess regulatory impact on scenarios
- What-If Scenario Simulator: Test hypothetical budget adjustments
"""

from ai_hub import ask_ai, simulate_adjustment
from mask_parser import get_mask_from_settings, parse_account
from anomaly_detection_module import render_anomaly_analysis
from accessibility_helper import create_accessible_chart

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Additional imports for simulations and modeling
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import plotly.express as px

# Import database functions from db_connection.py
from db_connection import (
    get_departments, 
    get_projects, 
    save_scenario, 
    get_scenarios,
    format_currency,
    format_percentage,
    load_org_data,
    get_connection,
    get_db_path_for_org
)
import os
import json
import sqlite3
import plotly.express as px

# Import security functions and report generator
from modules.admin.admin_panel import get_user_departments, is_admin, is_finance_director
from summary_report_generator import generate_full_scenario_report, add_scenario_to_comparison, remove_scenario_from_comparison

# Import report generator module
import summary_report_generator as report_gen

def render_restricted_fund_guidance():
    """
    Render the Restricted Fund Guidance tab
    
    This tab provides guidance on compliant usage of restricted funds
    based on fund classifications from the admin panel.
    """
    st.header("Restricted Fund Guidance")
    st.markdown("Review your restricted funds and get guidance on compliant usage.")

    # Load classifications from the fund_classifications.json file
    if os.path.exists("fund_classifications.json"):
        with open("fund_classifications.json") as f:
            classifications = json.load(f)
    else:
        classifications = {}
        st.warning("No fund classifications found. Please use the Fund Classification Manager in the Admin Panel to classify your funds.")

    # Load fund balances from the database using the correct table structure
    conn = get_database_connection()
    try:
        fund_data = pd.read_sql("""
            SELECT DISTINCT 
                Fund as FundCode, 
                Fund as FundName, 
                SUM(Budget) as EndingBalance
            FROM DepartmentPerformance 
            GROUP BY Fund
        """, conn)
    except Exception as e:
        st.error(f"Could not load fund data: {e}")
        # Create empty data structure if query fails
        fund_data = pd.DataFrame(columns=["FundCode", "FundName", "EndingBalance"])
        st.warning("Unable to load fund data from the database. Please check your database connection.")

    if not fund_data.empty:
        # Add fund type classification to the dataframe
        fund_data["Type"] = fund_data["FundCode"].astype(str).apply(lambda x: classifications.get(str(x), "Unclassified"))
        
        # Filter for restricted funds
        restricted_funds = fund_data[fund_data["Type"] == "Restricted"]

        st.subheader("Restricted Funds Overview")
        
        if not restricted_funds.empty:
            # Format the ending balance as currency
            restricted_funds["EndingBalance"] = restricted_funds["EndingBalance"].apply(
                lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A"
            )
            
            # Display the restricted funds table
            st.dataframe(restricted_funds, use_container_width=True)

            # Create a pie chart of fund balances
            if len(restricted_funds) > 1:
                try:
                    # Prepare data for visualization
                    fig = px.pie(
                        restricted_funds, 
                        values="EndingBalance", 
                        names="FundName",
                        title="Restricted Funds Distribution",
                        hole=0.4
                    )
                    create_accessible_chart(fig, "Restricted Funds Distribution", "Pie chart showing the distribution of restricted fund balances across different fund categories.")
                except Exception as e:
                    st.warning(f"Could not create visualization: {e}")
            
            # Fund selection for detailed guidance
            selected_fund = st.selectbox(
                "Select a Restricted Fund for Compliance Guidance", 
                options=restricted_funds["FundCode"].tolist(),
                format_func=lambda x: f"{x} - {restricted_funds.loc[restricted_funds['FundCode'] == x, 'FundName'].values[0]}"
            )
            
            if selected_fund:
                fund_name = restricted_funds.loc[restricted_funds["FundCode"] == selected_fund, "FundName"].values[0]
                fund_type = classifications.get(str(selected_fund), "Restricted")
                
                # Display fund details
                st.subheader(f"Fund Details: {fund_name}")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fund Code", selected_fund)
                with col2:
                    st.metric("Classification", fund_type)
                
                # Generate AI guidance for fund usage
                st.subheader("AI Compliance Guidance")
                
                with st.spinner("Generating compliance guidance..."):
                    prompt = f"What are the GASB-compliant uses for a {fund_type} fund like '{fund_name}'? Include specific GASB statements and compliance requirements."
                    
                    try:
                        guidance = ask_ai(prompt, sources=["gasb", "irs"])
                        st.markdown(guidance)
                        
                        # Add a checklist for compliance verification
                        st.subheader("Compliance Checklist")
                        st.markdown("Use this checklist to verify compliance with restricted fund requirements:")
                        
                        st.checkbox("☑️ Fund use aligns with specific restricted purpose", value=False)
                        st.checkbox("☑️ Proper documentation of fund source and restrictions", value=False)
                        st.checkbox("☑️ Required reporting and disclosure procedures in place", value=False)
                        st.checkbox("☑️ Separate accounting maintained for restricted funds", value=False)
                        st.checkbox("☑️ Compliance with applicable GASB statements", value=False)
                        st.checkbox("☑️ Regular review of fund compliance by finance team", value=False)
                        
                    except Exception as e:
                        st.error(f"Error generating guidance: {e}")
                        st.info("""
                        ### General Guidance for Restricted Funds
                        
                        Restricted funds must be used only for their designated purpose. Key considerations include:
                        
                        - Maintain separate accounting for each restricted fund
                        - Document the source and purpose of all restrictions
                        - Ensure expenditures align with the fund's designated purpose
                        - Follow GASB Statement No. 54 for fund balance reporting
                        - Consult with your auditor for specific compliance requirements
                        """)
        else:
            st.info("No restricted funds have been classified yet. Use the Fund Classification Manager in the Admin Panel to classify your funds.")
            
            # Show guidance on fund classification
            with st.expander("How to Classify Funds", expanded=True):
                st.markdown("""
                ### Fund Classification Guide
                
                To properly classify your funds:
                
                1. Navigate to the **Admin Panel**
                2. Select the **Fund Classifications** tab
                3. Assign each fund to the appropriate category:
                   - **Unrestricted**: General purpose funds with no external restrictions
                   - **Restricted**: Funds limited to specific purposes by external parties
                   - **Capital**: Funds designated for capital projects
                   - **Debt Service**: Funds for payment of debt principal and interest
                   - **Grant**: Funds provided by grantors for specific purposes
                   - **Other**: Special purpose funds not fitting other categories
                
                After classification, return to this tab to see guidance specific to your restricted funds.
                """)
    else:
        st.info("No fund data available. Please check your database connection or add funds to your system.")

# Monte Carlo functionality has been moved to modules/navi/monte_carlo_simulator.py

# Monte Carlo plotting functions have been moved to modules/navi/monte_carlo_simulator.py

# Monte Carlo simulation UI has been moved to modules/navi/monte_carlo_simulator.py

# --- AI PROPOSAL GENERATOR MODULE ---
def generate_ai_base_scenario(project_name, cost, department_names=None, scenario_data=None):
    """Generate AI-powered scenario plan with optional scenario funding data"""
    phases = [
        {"name": "Planning", "duration_months": 2, "cost_pct": 10},
        {"name": "Construction", "duration_months": 10, "cost_pct": 75},
        {"name": "Closeout", "duration_months": 2, "cost_pct": 15}
    ]
    
    # Enhanced summary with scenario funding details if available
    if scenario_data:
        funding_details = []
        if scenario_data.get("tax_revenue"):
            funding_details.append(f"Tax Revenue: ${float(scenario_data['tax_revenue']):,.0f}")
        if scenario_data.get("grant_funding"):
            funding_details.append(f"Grant Funding: ${float(scenario_data['grant_funding']):,.0f}")
        if scenario_data.get("private_investment"):
            funding_details.append(f"Private Investment: ${float(scenario_data['private_investment']):,.0f}")
        if scenario_data.get("bonds_required"):
            funding_details.append(f"Bond Financing: ${float(scenario_data['bonds_required']):,.0f}")
        
        funding_text = " | ".join(funding_details) if funding_details else "Funding sources to be determined"
        summary = f"The {project_name} is a strategic capital investment with total estimated cost of ${cost:,.0f}. Funding strategy: {funding_text}. The project includes comprehensive planning, construction, and closeout phases with risk mitigation strategies."
    else:
        summary = f"The {project_name} is a strategic capital investment aimed at addressing long-term community needs. Estimated total cost is ${cost:,.0f}. The project includes planning, construction, and closeout phases."

    return {
        "phases": phases,
        "total_duration": sum(p["duration_months"] for p in phases),
        "risks": ["Delays in permitting", "Cost overruns", "Grant disbursement timing", "Revenue shortfalls"],
        "summary": summary,
        "project_name": project_name,
        "project_cost": cost,
        "scenario_data": scenario_data,
        "funding_sources": scenario_data if scenario_data else None
    }

def render_scenario_plan_editor(plan_dict):
    """Render the AI-generated scenario plan"""
    st.subheader("AI-Generated Scenario Plan")
    st.markdown(plan_dict["summary"])
    st.markdown(f"**Estimated Project Duration:** {plan_dict['total_duration']} months")
    st.markdown("### Phase Breakdown")
    for phase in plan_dict["phases"]:
        st.markdown(f"- **{phase['name']}**: {phase['duration_months']} months, {phase['cost_pct']}% of total cost")

    st.markdown("### Key Risks")
    for risk in plan_dict["risks"]:
        st.markdown(f"- {risk}")

def generate_proposal_pdf(plan_dict):
    """Generate PDF proposal from plan data"""
    from fpdf import FPDF
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Project Proposal: {plan_dict['project_name']}", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d')}", ln=True)

    pdf.ln(10)
    # Clean text for PDF compatibility
    summary_clean = plan_dict["summary"].encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 10, summary_clean)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Phase Breakdown", ln=True)
    pdf.set_font("Arial", size=12)
    for phase in plan_dict["phases"]:
        pdf.cell(0, 10, f"{phase['name']}: {phase['duration_months']} months, {phase['cost_pct']}% of cost", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Key Risks", ln=True)
    pdf.set_font("Arial", size=12)
    for risk in plan_dict["risks"]:
        risk_clean = risk.encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 10, f"- {risk_clean}", ln=True)

    # Output as bytes
    return pdf.output(dest='S')

def render_ai_proposal_generator(org: str = "cityA", org_display_name: str = "City A"):
    """Render the AI Proposal Generator tab - ONLY scenario loading, no project inputs"""
    st.header("AI Proposal Generator")
    st.markdown("""
    Generate comprehensive project proposals from saved scenarios using AI analysis. 
    Select a saved scenario below to load its funding data and generate AI proposals.
    """)
    
    # Load from saved scenarios only - NO PROJECT INPUTS
    scenarios = get_scenarios()
    scenario_data = None
    project_name = ""
    project_cost = 0
    
    if scenarios:
        st.markdown("### Load Saved Scenario")
        scenario_names = ["Select a scenario..."] + [s["name"] for s in scenarios]
        selected_scenario_name = st.selectbox("Choose Scenario", scenario_names, key="ai_scenario_selector")
        
        if selected_scenario_name != "Select a scenario...":
            selected_scenario = next((s for s in scenarios if s["name"] == selected_scenario_name), None)
            if selected_scenario:
                # Update project details with scenario data
                project_name = selected_scenario["name"]
                project_cost = float(selected_scenario.get("Total Cost", 0))
                scenario_data = selected_scenario
                
                # Display scenario details
                st.success(f"Loaded scenario: {project_name}")
                
                # Show key scenario metrics
                col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
                with col_metrics1:
                    st.metric("Total Project Cost", f"${project_cost:,.0f}")
                with col_metrics2:
                    st.metric("Tax Revenue", f"${selected_scenario.get('Tax Revenue', 0):,.0f}")
                with col_metrics3:
                    st.metric("Grant Funding", f"${selected_scenario.get('Grant Funding', 0):,.0f}")
                
                # Create funding breakdown visualization (exact same as scenario builder)
                st.markdown("#### Funding Breakdown Visualization")
                
                # Extract funding data using exact same variable names as scenario builder
                # Map scenario database fields to scenario builder variable names
                total_reallocation = sum(selected_scenario.get("Department Allocations", {}).values()) if selected_scenario.get("Department Allocations") else 0
                tax_revenue = float(selected_scenario.get("Tax Revenue", 0))
                grant = float(selected_scenario.get("Grant Funding", 0))  # Database returns "Grant Funding"
                private_investment = float(selected_scenario.get("Private Investment", 0))
                
                # Calculate funding total and bonds needed (exact same logic as scenario builder)
                funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
                bonds_needed = round(max(0, project_cost - funding_total), 2)
                
                # Debug output to verify values
                st.write(f"**Debug - Loaded values:**")
                st.write(f"- Departmental Reallocation: ${total_reallocation:,.0f}")
                st.write(f"- Tax Revenue: ${tax_revenue:,.0f}")
                st.write(f"- Grant Funding: ${grant:,.0f}")
                st.write(f"- Private Investment: ${private_investment:,.0f}")
                st.write(f"- Bonds Needed: ${bonds_needed:,.0f}")
                st.write(f"- Total Funding: ${funding_total:,.0f}")
                st.write(f"- Project Cost: ${project_cost:,.0f}")
                
                # Create funding breakdown chart (EXACT same code as scenario builder)
                categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
                values = [total_reallocation, tax_revenue, grant, private_investment, bonds_needed]
                colors = ["#6c5ce7", "#00b894", "#fdcb6e", "#e84393", "#d63031"]
                
                # Filter out zero values
                non_zero_categories = []
                non_zero_values = []
                non_zero_colors = []
                
                for cat, val, col in zip(categories, values, colors):
                    if val > 0:
                        non_zero_categories.append(cat)
                        non_zero_values.append(val)
                        non_zero_colors.append(col)
                
                if non_zero_categories:
                    # Create the stacked bar chart using accessible chart function (exact same as scenario builder)
                    from accessibility_helper import create_accessible_chart
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    for i, (cat, val, col) in enumerate(zip(non_zero_categories, non_zero_values, non_zero_colors)):
                        fig.add_trace(
                            go.Bar(
                                name=cat, 
                                x=["Funding Breakdown"], 
                                y=[val], 
                                marker_color=col,
                                text=[f"${val:,.2f}"],
                                textposition="auto"
                            )
                        )
                    
                    fig.update_layout(
                        barmode="stack",
                        template="plotly_white",
                        showlegend=True,
                        legend_title="Funding Source",
                        title=None,
                        title_text=None
                    )
                    
                    create_accessible_chart(
                        fig, 
                        "Project Funding Breakdown",
                        "Breakdown of project funding sources including departmental reallocations, tax revenue, grants, private investment, and any bonds needed to cover remaining costs."
                    )
                    
                    # Add funding summary metrics (exact same as scenario builder)
                    st.markdown("##### Funding Summary")
                    funding_percentage = round((funding_total / project_cost) * 100, 2) if project_cost > 0 else 0
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    
                    with col_m1:
                        st.metric("Total Project Cost", f"${project_cost:,.2f}")
                    
                    with col_m2:
                        st.metric("Total Secured Funding", f"${funding_total:,.2f}", delta=f"{funding_percentage:.1f}% Funded")
                    
                    with col_m3:
                        st.metric("Bonds Required", f"${bonds_needed:,.2f}", delta=f"-${funding_total:,.2f} from other sources" if funding_total > 0 else None)
                
                # AI Generation section
                st.markdown("---")
                st.markdown("### AI Proposal Generation")
                
                # Department selection
                departments = get_departments(org)
                if departments:
                    dept_names = list(departments.keys())
                    selected_depts = st.multiselect("Involved Departments", dept_names, 
                                                  default=dept_names[:2] if len(dept_names) >= 2 else dept_names,
                                                  key="ai_dept_selector")
                else:
                    selected_depts = ["Administration", "Public Works"]
                
                if st.button("Generate AI Plan", use_container_width=True):
                    with st.spinner("Creating AI scenario plan..."):
                        try:
                            plan = generate_ai_base_scenario(project_name, project_cost, selected_depts, scenario_data)
                            if plan:
                                st.session_state["ai_plan"] = plan
                                st.success(" AI Plan created successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to generate AI plan. Please try again.")
                        except Exception as e:
                            st.error(f"Error generating AI plan: {str(e)}")
                            st.info("Please check your data and try again.")

    else:
        st.warning("No saved scenarios found. Please create a scenario in the Scenario Builder tab first.")

    # Display generated plan if available
    if "ai_plan" in st.session_state:
        st.markdown("---")
        plan = st.session_state["ai_plan"]
        render_scenario_plan_editor(plan)

        # PDF download
        st.markdown("---")
        col_download1, col_download2 = st.columns(2)
        
        with col_download1:
            try:
                pdf_bytes = generate_proposal_pdf(plan)
                st.download_button(
                    label="Download Proposal as PDF",
                    data=pdf_bytes,
                    file_name=f"{plan['project_name'].replace(' ', '_').lower()}_proposal.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF generation error: {e}")
        
        with col_download2:
            if st.button("Clear Plan", use_container_width=True):
                if "ai_plan" in st.session_state:
                    del st.session_state["ai_plan"]
                st.rerun()

def run_simple_scenario_planner():
    """
    Run a simplified version of the Scenario Planner (based on secured_final)
    """
    st.title("Scenario Planner (Simplified Version)")

    df = load_org_data()
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

    st.subheader("Department Budget Overview")
    df_dept = df[df["Department"] == selected_dept]
    st.dataframe(df_dept[["Fund", "FiscalYear", "Budget", "Actual"]])

    st.divider()

    st.subheader("Auto-Generate Executive Scenario Report")
    if st.button("Generate Executive Scenario Report PDF"):
        generate_full_scenario_report(
            project_name,
            selected_dept,
            project_cost,
            tax_increase,
            grant_amount,
            project_notes
        )

def run_scenario_planner():
    """
    Run the Scenario Planner with security features and enhanced visualization
    This is a wrapper function that calls render_scenario_planner
    """
    render_scenario_planner()

def render_scenario_planner(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Scenario Planner tab with tabbed interface for advanced analysis
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.title("Scenario Planner")
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Scenario Builder", 
        "Legislative Impact Analyzer", 
        "What-If Scenario Simulator",
        "Restricted Fund Guidance",
        "AI Proposal Generator",
        "Grant Integration"
    ])
    
    with tab1:
        render_scenario_builder(org, org_display_name)
    
    with tab2:
        render_legislative_impact_analyzer()
    
    with tab3:
        render_whatif_simulator()
        
    with tab4:
        render_restricted_fund_guidance()
    
    with tab5:
        render_ai_proposal_generator(org, org_display_name)
    
    with tab6:
        render_grant_integration(org, org_display_name)
        
def render_scenario_builder(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the main Scenario Builder tab
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.header("Funding Scenario Builder")
    st.markdown("""
    Build and analyze funding scenarios for capital projects and initiatives.
    Allocate funds from various sources and visualize the funding breakdown.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Project details
        st.subheader("Project Details")
        
        # Project name as open text input
        project_name = st.text_input("Project Name", value="New Infrastructure Project", 
                                    help="Enter any project name or select from existing projects below")
        
        # Allow cost adjustment
        project_cost = st.number_input(
            "Total Project Cost ($)", 
            min_value=100000, 
            max_value=50000000,
            value=2000000, 
            step=50000,
            format="%d"
        )
        
        # TODO: Load from existing projects - commented out for sandbox-style interface
        # projects = get_projects()
        # if projects:
        #     st.markdown("**Or load from existing project:**")
        #     project_options = ["None"] + [p["name"] for p in projects]
        #     selected_existing = st.selectbox("Load Project Data", project_options)
        #     
        #     if selected_existing != "None":
        #         selected_project = next((p for p in projects if p["name"] == selected_existing), None)
        #         if selected_project:
        #             project_name = selected_project["name"]
        #             project_cost = int(selected_project["total_cost"])
        #             project_id = selected_project["id"]
        #             st.success(f"Loaded project: {project_name}")
        #             st.markdown(f"**Description:** {selected_project.get('description', 'No description available')}")
        #         else:
        #             project_id = 0
        #     else:
        #         project_id = 0
        # else:
        #     project_id = 0
        project_id = 0  # Always use 0 for sandbox-style projects
        
        # Primary funding sources
        st.subheader("Primary Funding Sources")
        
        # Check if we have saved grants from the AI assistant or Grant Integration tab
        has_saved_grants = st.session_state.get('saved_grants', [])
        has_selected_grants = st.session_state.get('selected_grants', [])
        import_flag = st.session_state.get('import_grants_to_scenario', False)
        
        # Combine grants from both sources
        all_available_grants = has_saved_grants + has_selected_grants
        
        # Display a notification if grants are available to import
        if all_available_grants:
            st.markdown("""
            <div style="background-color: #e6f7ff; border: 1px solid #1890ff; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
                <h3 style="color: #1890ff; margin-top: 0;">Grants Ready to Import!</h3>
                <p>You have grants selected that can be imported into your scenario.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Add an import button - make it more prominent
            if st.button("Import Available Grants", type="primary", use_container_width=True):
                # Clear the import flag to prevent repeated notices
                st.session_state.import_grants_to_scenario = False
                
                # Create an expander to show grant details
                with st.expander("Imported Grants", expanded=True):
                    # Calculate the total potential grant funding (using the average of min and max for each grant)
                    total_grant_funding = 0
                    
                    for i, grant_data in enumerate(all_available_grants):
                        # Calculate the average of min and max as the default value
                        avg_amount = (grant_data['min_amount'] + grant_data['max_amount']) / 2
                        total_grant_funding += avg_amount
                        
                        st.markdown(f"**{i+1}. {grant_data['name']}**")
                        
                        # Handle different grant data structures
                        if 'agency' in grant_data:
                            st.markdown(f"- Agency: {grant_data['agency']}")
                        elif 'source' in grant_data:
                            st.markdown(f"- Source: {grant_data['source']}")
                            
                        st.markdown(f"- Amount Range: ${grant_data['min_amount']:,} to ${grant_data['max_amount']:,}")
                        
                        # Optional fields that may not exist in all grant structures
                        if 'deadline' in grant_data:
                            st.markdown(f"- Deadline: {grant_data['deadline']}")
                        if 'complexity' in grant_data:
                            st.markdown(f"- Complexity: {grant_data['complexity']}")
                        if 'department' in grant_data:
                            st.markdown(f"- Department: {grant_data['department']}")
                    
                    st.info(f"Total potential grant funding: ${total_grant_funding:,.2f}")
                    
                    # Set the grant amount field to the total potential funding
                    st.session_state.grant_amount = int(total_grant_funding)
                
                st.success("Grants imported successfully! The grant funding amount has been updated.")
                st.rerun()  # Rerun to update the UI with the new grant amount
        
        tax_revenue = st.number_input("Projected Tax Revenue Increase ($)", 
                                   min_value=0.0, 
                                   value=500000.0, 
                                   step=50000.0,
                                   format="%.2f")
        
        # Get the grant amount from session state if available, otherwise use default
        default_grant_amount = st.session_state.get('grant_amount', 300000)
        grant = st.number_input("Grant Funding ($)", 
                              min_value=0.0, 
                              value=float(default_grant_amount), 
                              step=50000.0,
                              format="%.2f")
        
        # Display grant sources if grants were imported
        if all_available_grants and not st.session_state.get('import_grants_to_scenario', False):
            with st.expander("Grant Sources", expanded=False):
                for i, grant_data in enumerate(all_available_grants):
                    st.markdown(f"**{i+1}. {grant_data['name']}**")
                    
                    # Handle different grant data structures
                    if 'agency' in grant_data:
                        st.markdown(f"- Agency: {grant_data['agency']}")
                    elif 'source' in grant_data:
                        st.markdown(f"- Source: {grant_data['source']}")
                        
                    st.markdown(f"- Amount Range: ${grant_data['min_amount']:,} to ${grant_data['max_amount']:,}")
        
        private_investment = st.number_input("Private Investment ($)", 
                                          min_value=0.0, 
                                          value=0.0, 
                                          step=50000.0,
                                          format="%.2f")
                                          
        # Add a note about finding more grants
        st.info("Need more grant funding? Visit the Grant Finder in the AI Assistant tab to find and save additional grants.")

    with col2:
        # Department-level reallocation
        st.subheader("Department Budget Reallocation")
        st.markdown("""
        Departments can contribute unspent budget allocations to help fund the project.
        Select which departments to include and adjust the reallocation amounts.
        """)
        
        # Get departments
        departments = get_departments()
        
        # Use fallback data if needed
        if not departments:
            st.warning(f"No departments found in the database. Using sample data.")
            departments = {
                "Public Works": {"budget": 1200000, "underspent": 300000},
                "Administration": {"budget": 800000, "underspent": 150000}
            }
        
        # Calculate department reallocation
        total_reallocation = 0
        reallocated_amounts = {}
        
        # Create an expander for department allocations to save space
        with st.expander("Department Allocations", expanded=True):
            for dept, data in departments.items():
                # Default checked for first two departments
                is_default = dept in list(departments.keys())[:2]
                include = st.checkbox(f"{dept}", value=is_default, key=f"check_{dept}")
                
                if include:
                    # Calculate maximum allowed reallocation (10% of budget or underspent amount, whichever is less)
                    max_allowable = min(data["budget"] * 0.10, data.get("underspent", 0))
                    
                    # Ensure max_allowable is at least $1,000 for UI purposes
                    max_allowable = max(1000, max_allowable)
                    
                    # Round max_allowable to cents for better usability
                    max_allowable = round(max_allowable, 2)
                    
                    # Get saved value from session state if it exists
                    saved_key = f"dept_allocation_{dept}"
                    if saved_key not in st.session_state:
                        st.session_state[saved_key] = float(max_allowable / 2)
                    
                    # Add CSS to hide spinner arrows for number inputs
                    st.markdown("""
                    <style>
                    /* Hide spinner arrows */
                    input::-webkit-outer-spin-button,
                    input::-webkit-inner-spin-button {
                        -webkit-appearance: none;
                        margin: 0;
                    }
                    input[type=number] {
                        -moz-appearance: textfield;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Simple number input for exact amount entry
                    reallocation = st.number_input(
                        f"{dept} Reallocation - Exact Amount ($)",
                        min_value=0.0,
                        max_value=float(max_allowable),
                        value=st.session_state[saved_key],
                        step=0.01,
                        format="%.2f",
                        key=f"number_{dept}",
                        help=f"Enter amount between $0 and ${max_allowable:,.2f}"
                    )
                    
                    # Update session state
                    st.session_state[saved_key] = reallocation
                    
                    # Ensure we're adding rounded values
                    total_reallocation += round(reallocation, 2)
                    reallocated_amounts[dept] = round(reallocation, 2)
                    st.markdown(f'<div class="department-data">Budget: ${data["budget"]:,.2f} | Underspent: ${data.get("underspent", 0):,.2f} | Max: ${max_allowable:,.2f}</div>', unsafe_allow_html=True)

    # Calculate funding breakdown
    st.subheader("Funding Analysis")
    
    # Get expense account mask for funding allocation insights
    # expense_mask = get_mask_from_settings("Expense")
    
    # TODO: Account structure analysis - commented out for now
    # Show account structure information if masks are configured
    # if expense_mask:
    #     with st.expander("Account Structure Analysis", expanded=False):
    #         st.write("The system will categorize project expenses according to your chart of accounts structure:")
    #         
    #         # Create a sample expense account for demonstration
    #         sample_account = "10225406"  # This would typically come from your project data
    #         
    #         try:
    #             # Parse the account based on the mask
    #             account_segments = parse_account(sample_account, expense_mask)
    #             
    #             # Display the account structure
    #             st.write(f"Sample Project Expense Account: {sample_account}")
    #             
    #             # Create columns for better visualization
    #             cols = st.columns(len(account_segments))
    #             for i, (segment_name, segment_value) in enumerate(account_segments.items()):
    #                 with cols[i]:
    #                     st.metric(segment_name, segment_value)
    #                     
    #             # Show how funding sources map to account segments
    #             st.markdown("### Funding Source to Account Mapping")
    #             st.info(f"Projects funded through departmental reallocations will use department code from the source department.")
    #             if "Fund" in account_segments:
    #                 st.info(f"Bond-funded expenses typically use fund code {account_segments.get('Fund', '10')}1.")
    #                 st.info(f"Grant-funded expenses typically use fund code {account_segments.get('Fund', '10')}5.")
    #         except Exception as e:
    #             st.warning(f"Unable to parse account structure: {e}")
    
    col_analysis1, col_analysis2 = st.columns([2, 1])
    
    with col_analysis1:
        # Calculate total funding and bond need with explicit rounding to cents
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        funding_percentage = round((funding_total / project_cost) * 100, 2) if project_cost > 0 else 0
        
        # Create funding breakdown chart
        categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
        values = [total_reallocation, tax_revenue, grant, private_investment, bonds_needed]
        colors = ["#6c5ce7", "#00b894", "#fdcb6e", "#e84393", "#d63031"]
        
        # Filter out zero values
        non_zero_categories = []
        non_zero_values = []
        non_zero_colors = []
        
        for cat, val, col in zip(categories, values, colors):
            if val > 0:
                non_zero_categories.append(cat)
                non_zero_values.append(val)
                non_zero_colors.append(col)
        
        # Create the stacked bar chart using accessible chart function
        from accessibility_helper import create_accessible_chart
        import plotly.graph_objects as go
        
        fig = go.Figure()
        for i, (cat, val, col) in enumerate(zip(non_zero_categories, non_zero_values, non_zero_colors)):
            fig.add_trace(
                go.Bar(
                    name=cat, 
                    x=["Funding Breakdown"], 
                    y=[val], 
                    marker_color=col,
                    text=[f"${val:,.2f}"],
                    textposition="auto"
                )
            )
        
        fig.update_layout(
            barmode="stack",
            template="plotly_white",
            showlegend=True,
            legend_title="Funding Source",
            title=None,
            title_text=None
        )
        
        create_accessible_chart(
            fig, 
            "Project Funding Breakdown",
            "Breakdown of project funding sources including departmental reallocations, tax revenue, grants, private investment, and any bonds needed to cover remaining costs."
        )

        # Department reallocation breakdown if there are reallocations
        if reallocated_amounts:
            # Create pie chart for department reallocation using accessible chart function
            dept_fig = go.Figure(data=[
                go.Pie(
                    labels=list(reallocated_amounts.keys()),
                    values=list(reallocated_amounts.values()),
                    hole=.4,
                    textinfo="label+percent",
                    marker=dict(colors=["#a29bfe", "#74b9ff", "#55efc4", "#81ecec", "#ffeaa7", "#fab1a0", "#ff7675"])
                )
            ])
            
            create_accessible_chart(
                dept_fig, 
                "Department Reallocation Breakdown",
                "Pie chart showing the proportion of budget reallocations from each department to fund the project."
            )

    with col_analysis2:
        # Summary statistics
        st.subheader("Funding Summary")
        
        # Create a metrics display
        st.metric("Total Project Cost", 
                 f"${project_cost:,.2f}",
                 delta=None)
        
        st.metric("Total Secured Funding", 
                 f"${funding_total:,.2f}", 
                 delta=f"{funding_percentage:.1f}% Funded")
        
        st.metric("Bonds Required", 
                 f"${bonds_needed:,.2f}", 
                 delta=f"-${funding_total:,.2f} from other sources", 
                 delta_color="inverse")
        
        # Project savings / cost reduction potential
        st.markdown("### Additional Options")
        
        # Risk Analysis Note
        st.info("For advanced Monte Carlo risk simulation, please use the dedicated Monte Carlo Simulator tab in the Navi module.")
        
        # Display option to save the scenario
        with st.form("save_scenario_form"):
            st.subheader("Save This Scenario")
            scenario_name = st.text_input("Scenario Name", value=f"Scenario {datetime.now().strftime('%m/%d/%Y')}")
            scenario_notes = st.text_area("Notes", height=80, placeholder="Enter any additional notes for this scenario...")
            
            col_save1, col_save2 = st.columns(2)
            with col_save1:
                save_submitted = st.form_submit_button("Save Scenario", use_container_width=True)
            
            with col_save2:
                save_and_report = st.form_submit_button("Save & Generate Report", use_container_width=True)
            
            if save_submitted or save_and_report:
                if not scenario_name:
                    st.error("Please enter a scenario name.")
                else:
                    # Save the scenario to the database
                    scenario_id = save_scenario(
                        name=scenario_name,
                        project_id=project_id,
                        total_cost=project_cost,
                        tax_revenue=tax_revenue,
                        grant_funding=grant,
                        private_investment=private_investment,
                        dept_reallocation=total_reallocation,
                        bonds_required=bonds_needed,
                        notes=scenario_notes,
                        dept_breakdown=str(reallocated_amounts)
                    )
                    
                    # Display success message
                    st.success(f"Scenario '{scenario_name}' saved successfully!")
                    
                    # Generate report if requested
                    if save_and_report:
                        # Generate and offer the report for download
                        file_bytes = generate_full_scenario_report(
                            project_name=selected_project_data["name"],
                            department="Multiple Departments",
                            project_cost=project_cost,
                            tax_revenue=tax_revenue,
                            grant_amount=grant,
                            project_notes=scenario_notes,
                            scenario_id=scenario_id,
                            return_file=True
                        )
                        
                        if file_bytes:
                            st.download_button(
                                label="Download Scenario Report",
                                data=file_bytes,
                                file_name=f"scenario_report_{scenario_name.replace(' ', '_')}.pdf",
                                mime="application/pdf",
                            )

        # Comparison tool link
        st.markdown("---")
        st.markdown("### Scenario Comparison")
        
        # Load existing scenarios to select for comparison
        all_scenarios = get_scenarios()
        if all_scenarios:
            # Get selected scenarios for comparison
            comparison_list = st.session_state.get('comparison_list', [])
            
            # Display currently selected scenarios
            if comparison_list:
                st.markdown("#### Currently selected for comparison:")
                for scenario_id in comparison_list:
                    # Find the scenario in the all_scenarios list
                    scenario = next((s for s in all_scenarios if s["id"] == scenario_id), None)
                    if scenario:
                        col_scenario, col_remove = st.columns([3, 1])
                        with col_scenario:
                            st.markdown(f"**{scenario['name']}** (${float(scenario['total_cost']):,.2f})")
                        with col_remove:
                            if st.button("Remove", key=f"remove_{scenario_id}"):
                                remove_scenario_from_comparison(scenario_id)
                                st.rerun()
            
            # Select additional scenarios
            scenario_options = {s["name"]: s["id"] for s in all_scenarios if s["id"] not in comparison_list}
            if scenario_options:
                selected_scenario = st.selectbox("Add scenario to comparison", options=list(scenario_options.keys()))
                if st.button("Add to Comparison"):
                    add_scenario_to_comparison(scenario_options[selected_scenario])
                    st.success(f"Added '{selected_scenario}' to comparison list!")
                    st.rerun()
            
            # Button to view comparison if we have at least 2 scenarios
            if len(comparison_list) >= 2:
                if st.button("View Comparison", type="primary"):
                    # Set the tab selection in session state to trigger the comparison view
                    st.session_state['show_scenario_comparison'] = True
                    st.rerun()
        else:
            st.info("No saved scenarios found. Save this scenario first to enable comparisons.")

def render_legislative_impact_analyzer(project_cost: int = 1000000, tax_revenue: int = 500000, grant: int = 300000):
    """
    Render the Legislative Impact Analyzer tab
    
    Args:
        project_cost (int): Default project cost for analysis
        tax_revenue (int): Default tax revenue value for analysis
        grant (int): Default grant amount for analysis
    """
    st.header("Legislative Impact Analyzer")
    st.markdown("""
    Analyze how legislation and regulations might impact your funding scenario.
    This tool uses AI to assess potential regulatory impacts and compliance requirements.
    """)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("Regulatory Analysis")
        
        regulation_category = st.selectbox(
            "Select Regulation Category", 
            options=[
                "Municipal Bond Regulations",
                "Federal Grant Requirements",
                "Environmental Compliance",
                "Zoning and Land Use",
                "Procurement Regulations",
                "Tax Increment Financing"
            ]
        )
        
        # Custom prompt option
        use_custom_prompt = st.checkbox("Use Custom Regulatory Prompt")
        
        if use_custom_prompt:
            prompt = st.text_area(
                "Enter your regulatory compliance question",
                height=100,
                value="What regulatory considerations should we be aware of for using tax increment financing in this project?"
            )
        else:
            # Set default prompts based on selected category
            if regulation_category == "Municipal Bond Regulations":
                prompt = f"Explain the key municipal bond regulations and requirements for a ${project_cost:,} project. Include any recent changes and compliance considerations."
            elif regulation_category == "Federal Grant Requirements":
                prompt = f"What are the federal grant compliance requirements for a ${grant:,} grant? Include reporting requirements and restrictions on fund usage."
            elif regulation_category == "Environmental Compliance":
                prompt = "What environmental impact assessments and compliance requirements would be needed for a municipal infrastructure project? Include timeline considerations."
            elif regulation_category == "Zoning and Land Use":
                prompt = "Explain the zoning and land use approval process for municipal projects. What are common challenges and timeline considerations?"
            elif regulation_category == "Procurement Regulations":
                prompt = "What procurement regulations apply to municipal projects? Include bidding requirements, local vendor preferences, and compliance documentation."
            else:  # Tax Increment Financing
                prompt = f"Explain how Tax Increment Financing (TIF) works for municipal projects. What are the requirements, restrictions, and approval process for a ${project_cost:,} project?"
        
        st.markdown("### Analysis Query")
        st.markdown(f"**{prompt}**")
        
        # Display analysis button
        if st.button("Run Regulatory Analysis", use_container_width=True):
            with st.spinner("Analyzing regulatory implications..."):
                # Use AI Hub to generate insights
                reg_sources = [
                    "Municipal Securities Rulemaking Board (MSRB) Rule G-17",
                    "2 CFR Part 200 (Uniform Administrative Requirements for Federal Grants)",
                    "National Environmental Policy Act (NEPA)",
                    "Municipal Procurement Standards"
                ]
                
                # Get AI analysis
                analysis = ask_ai(
                    prompt=prompt,
                    sources=reg_sources,
                    max_tokens=750
                )
                
                # Store in session state
                st.session_state['regulatory_analysis'] = analysis
                st.session_state['regulatory_prompt'] = prompt
                
                # Display the analysis
                st.markdown("### Regulatory Analysis Results")
                st.markdown(analysis)
                
                # Add a download button for the analysis
                from io import BytesIO
                from fpdf import FPDF
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(200, 10, "Regulatory Impact Analysis", ln=True, align="C")
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, f"Analysis Date: {datetime.now().strftime('%m/%d/%Y')}", ln=True)
                pdf.cell(200, 10, f"Regulation Category: {regulation_category}", ln=True)
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(200, 10, "Query:", ln=True)
                pdf.set_font("Arial", size=10)
                
                # Split prompt into multiple lines if needed - clean for PDF
                prompt_clean = prompt.encode('ascii', 'ignore').decode('ascii')
                pdf.multi_cell(0, 5, prompt_clean)
                pdf.ln(5)
                
                pdf.set_font("Arial", "B", 12)
                pdf.cell(200, 10, "Analysis:", ln=True)
                pdf.set_font("Arial", size=10)
                
                # Split analysis into multiple lines - remove Unicode characters for PDF compatibility
                analysis_clean = analysis.encode('ascii', 'ignore').decode('ascii')
                pdf.multi_cell(0, 5, analysis_clean)
                
                # Add sources
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(200, 10, "Regulatory Sources:", ln=True)
                pdf.set_font("Arial", "I", 10)
                for source in reg_sources:
                    pdf.cell(200, 6, f"• {source}", ln=True)
                    
                # Get PDF as bytes for download
                pdf_bytes = pdf.output(dest='S')
                
                st.download_button(
                    "Download Analysis as PDF",
                    data=pdf_bytes,
                    file_name=f"regulatory_analysis_{regulation_category.replace(' ', '_').lower()}.pdf",
                    mime="application/pdf"
                )
    
    with col2:
        st.subheader("Compliance Checklist")
        
        # Compliance checklist based on regulation category
        if regulation_category == "Municipal Bond Regulations":
            checklist_items = [
                "Review bond counsel requirements",
                "Check debt capacity limits",
                "Confirm public hearing requirements",
                "Review financial disclosure requirements",
                "Ensure interest rate compliance",
                "Verify arbitrage rules compliance"
            ]
        elif regulation_category == "Federal Grant Requirements":
            checklist_items = [
                "Verify eligibility criteria",
                "Prepare required documentation",
                "Understand matching requirements",
                "Review reporting obligations",
                "Check spending timelines",
                "Confirm compliance with 2 CFR 200"
            ]
        elif regulation_category == "Environmental Compliance":
            checklist_items = [
                "Complete environmental impact assessment",
                "Check for required permits",
                "Plan for public comment period",
                "Review stormwater management requirements",
                "Verify endangered species impact",
                "Prepare mitigation plans if needed"
            ]
        elif regulation_category == "Zoning and Land Use":
            checklist_items = [
                "Review zoning requirements",
                "Check for variance needs",
                "Schedule public hearings",
                "Prepare site plans",
                "Verify compliance with comprehensive plan",
                "Address parking/traffic requirements"
            ]
        elif regulation_category == "Procurement Regulations":
            checklist_items = [
                "Prepare RFP/RFQ documents",
                "Plan for competitive bidding",
                "Check local vendor preference requirements",
                "Verify prevailing wage compliance",
                "Prepare contract documents",
                "Document bid evaluation process"
            ]
        else:  # Tax Increment Financing
            checklist_items = [
                "Document blight/development need",
                "Calculate tax increment projections",
                "Schedule public hearings",
                "Verify project eligibility",
                "Prepare financial impact analysis",
                "Document job creation potential"
            ]
        
        # Display checklist with progress tracking
        if checklist_items:
            # Initialize session state for checklist progress
            if 'checklist_progress' not in st.session_state:
                st.session_state.checklist_progress = {}
            
            completed_items = 0
            total_items = len(checklist_items)
            
            for i, item in enumerate(checklist_items):
                key = f"compliance_{regulation_category}_{i}"
                is_checked = st.checkbox(item, key=key)
                
                # Track completion
                if is_checked:
                    completed_items += 1
                    st.session_state.checklist_progress[key] = True
                else:
                    st.session_state.checklist_progress[key] = False
            
            # Show progress
            progress = completed_items / total_items if total_items > 0 else 0
            st.progress(progress)
            st.write(f"Progress: {completed_items}/{total_items} items completed ({progress:.0%})")
            
            # Show completion message
            if completed_items == total_items:
                st.success("All compliance items completed! You're ready to proceed with this regulation category.")
            elif completed_items > 0:
                st.info(f"{total_items - completed_items} items remaining to complete compliance review.")
            
            # Add action buttons based on progress
            if completed_items == total_items:
                if st.button("Generate Compliance Summary", key=f"summary_{regulation_category}"):
                    summary_text = f"""
                    ## Compliance Summary for {regulation_category}
                    
                    **Status:** All requirements reviewed
                    **Completion Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
                    
                    **Completed Items:**
                    """
                    for item in checklist_items:
                        summary_text += f"\n• {item}"
                    
                    st.markdown(summary_text)
                    
                    # Option to download compliance report
                    st.download_button(
                        "Download Compliance Report",
                        data=summary_text,
                        file_name=f"compliance_report_{regulation_category.replace(' ', '_').lower()}.txt",
                        mime="text/plain"
                    )
        
        # Display reference materials
        st.markdown("### Key Reference Materials")
        
        # Based on category, show different reference materials
        if regulation_category == "Municipal Bond Regulations":
            st.markdown("""
            - [MSRB Rules and Guidance](https://www.msrb.org/rules-and-interpretations)
            - [SEC Municipal Securities](https://www.sec.gov/municipal-securities)
            - [IRS Tax-Exempt Bonds](https://www.irs.gov/tax-exempt-bonds)
            """)
        elif regulation_category == "Federal Grant Requirements":
            st.markdown("""
            - [2 CFR 200 - Uniform Administrative Requirements](https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200)
            - [Grants.gov Learning Center](https://www.grants.gov/web/grants/learn-grants.html)
            - [COSO Internal Controls Framework](https://www.coso.org/guidance-on-internal-control)
            """)
        elif regulation_category == "Environmental Compliance":
            st.markdown("""
            - [EPA NEPA Compliance](https://www.epa.gov/nepa)
            - [Clean Water Act Section 404](https://www.epa.gov/cwa-404)
            - [Environmental Review Process](https://www.hudexchange.info/programs/environmental-review/)
            """)
        elif regulation_category == "Zoning and Land Use":
            st.markdown("""
            - [American Planning Association](https://www.planning.org/resources/)
            - [HUD Community Development](https://www.hudexchange.info/programs/cdbg/)
            - [Zoning Practice Guidelines](https://www.planning.org/publications/document/9026899/)
            """)
        elif regulation_category == "Procurement Regulations":
            st.markdown("""
            - [Federal Acquisition Regulation](https://www.acquisition.gov/far/)
            - [GSA Schedules Program](https://www.gsa.gov/buying-selling/purchasing-programs/gsa-schedules)
            - [National Institute of Governmental Purchasing](https://www.nigp.org/home)
            """)
        else:  # Tax Increment Financing
            st.markdown("""
            - [CDFA TIF Resources](https://www.cdfa.net/cdfa/cdfaweb.nsf/pages/tif-resources.html)
            - [Lincoln Institute TIF Policy Focus](https://www.lincolninst.edu/publications/policy-focus-reports/tax-increment-financing)
            - [IEDC Economic Development Resources](https://www.iedconline.org/web-pages/resources-publications/)
            """)

def render_whatif_simulator():
    """
    Render a simplified What-If Scenario Simulator for city council members
    """
    st.header("What-If Budget Simulator")
    st.markdown("""
    **Budget Impact Testing Tool**  
    Test different budget scenarios and see their immediate financial impact on your city.
    """)
    
    # Load data for simulation - aggregate by department
    try:
        db_path = get_db_path_for_org("cityA")
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("""
            SELECT Department, 
                   SUM(Budget) as Budget, 
                   SUM(Actual) as Actual
            FROM DepartmentPerformance
            WHERE Budget > 0
            GROUP BY Department
        """, conn)
        conn.close()
        
        # Calculate derived fields
        df['Remaining'] = df['Budget'] - df['Actual']
        df['PercentSpent'] = ((df['Actual'] / df['Budget']) * 100).round(1)
        
    except Exception as e:
        st.error(f"Cannot load budget data: {str(e)}")
        return
    
    if df.empty:
        st.warning("No budget data available.")
        return
    
    # Simple scenario selection
    st.subheader("Choose Your Scenario")
    
    scenario_type = st.selectbox(
        "What do you want to test?",
        [
            "Adjust a department's budget", 
            "Move money between departments",
            "Apply across-the-board changes",
            "Emergency budget reduction"
        ]
    )
    
    # Show current budget overview first
    st.subheader("Current Budget Overview")
    
    # Create simple budget overview
    overview_df = df[['Department', 'Budget', 'Actual', 'Remaining', 'PercentSpent']].copy()
    overview_df['Budget'] = overview_df['Budget'].apply(lambda x: f"${x:,.0f}")
    overview_df['Actual'] = overview_df['Actual'].apply(lambda x: f"${x:,.0f}")
    overview_df['Remaining'] = overview_df['Remaining'].apply(lambda x: f"${x:,.0f}")
    overview_df['PercentSpent'] = overview_df['PercentSpent'].apply(lambda x: f"{x}%")
    
    st.dataframe(overview_df, use_container_width=True, hide_index=True)
    
    # Simplified input based on scenario type
    st.subheader("Set Up Your Test")
    
    if scenario_type == "Adjust a department's budget":
        col1, col2 = st.columns(2)
        with col1:
            dept = st.selectbox("Which department?", df['Department'].tolist())
        with col2:
            adjustment_percent = st.number_input(
                "Adjust budget by what percentage?", 
                min_value=-50, 
                max_value=100, 
                value=0,
                step=1,
                help="Negative values = cuts, Positive values = increases",
                key="dept_budget_number"
            )
        
        if st.button("Test This Scenario", type="primary"):
            show_budget_adjustment_results(df, dept, adjustment_percent)
    
    elif scenario_type == "Move money between departments":
        col1, col2, col3 = st.columns(3)
        with col1:
            from_dept = st.selectbox("Take money from:", df['Department'].tolist())
        with col2:
            to_dept = st.selectbox("Give money to:", df['Department'].tolist())
        with col3:
            amount = st.number_input("Amount to move:", min_value=1000, value=50000, step=1000)
        
        if st.button("Test This Scenario", type="primary"):
            show_budget_transfer_results(df, from_dept, to_dept, amount)
    
    elif scenario_type == "Apply across-the-board changes":
        adjustment_percent = st.number_input(
            "Adjust all departments by what percentage?", 
            min_value=-25, 
            max_value=50, 
            value=0,
            step=1,
            help="Negative values = cuts, Positive values = increases",
            key="across_board_number"
        )
        
        if st.button("Test This Scenario", type="primary"):
            show_across_board_adjustment_results(df, adjustment_percent)
    
    elif scenario_type == "Emergency budget reduction":
        target_savings = st.number_input(
            "How much do you need to save?", 
            min_value=10000, 
            value=100000, 
            step=10000,
            help="Enter the total amount you need to cut from the budget"
        )
        
        if st.button("Test This Scenario", type="primary"):
            show_emergency_reduction_results(df, target_savings)

def show_budget_adjustment_results(df, dept, adjustment_percent):
    """Show results of adjusting a department's budget (positive or negative)"""
    st.subheader("What This Means")
    
    # Calculate impacts
    original_budget = df[df['Department'] == dept]['Budget'].iloc[0]
    adjustment_amount = original_budget * (adjustment_percent / 100)
    new_budget = original_budget + adjustment_amount
    
    # Show impact in plain language
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            f"{dept} Current Budget", 
            f"${original_budget:,.0f}"
        )
        
    with col2:
        delta_text = f"{adjustment_amount:+,.0f}" if adjustment_amount >= 0 else f"{adjustment_amount:,.0f}"
        st.metric(
            f"{dept} New Budget", 
            f"${new_budget:,.0f}",
            delta=f"${delta_text}"
        )
    
    # Show appropriate message based on adjustment type
    if adjustment_percent > 0:
        st.info(f"This would cost the city an additional ${adjustment_amount:,.0f}")
        st.info(f"Where will this ${adjustment_amount:,.0f} come from? You'll need to find savings elsewhere or raise revenue.")
    elif adjustment_percent < 0:
        st.success(f"This would save the city ${abs(adjustment_amount):,.0f}")
        
        # Show warnings if needed
        current_spending = df[df['Department'] == dept]['Actual'].iloc[0]
        if new_budget < current_spending:
            shortfall = current_spending - new_budget
            st.warning(f"Warning: {dept} is currently spending ${current_spending:,.0f}. "
                      f"This cut would create a ${shortfall:,.0f} shortfall.")
    else:
        st.info("No change to budget")
    
    # Show updated budget table
    st.subheader("Updated Budget")
    updated_df = df.copy()
    updated_df.loc[updated_df['Department'] == dept, 'Budget'] = new_budget
    updated_df.loc[updated_df['Department'] == dept, 'Remaining'] = new_budget - updated_df.loc[updated_df['Department'] == dept, 'Actual']
    
    display_df = updated_df[['Department', 'Budget', 'Actual', 'Remaining']].copy()
    display_df['Budget'] = display_df['Budget'].apply(lambda x: f"${x:,.0f}")
    display_df['Actual'] = display_df['Actual'].apply(lambda x: f"${x:,.0f}")
    display_df['Remaining'] = display_df['Remaining'].apply(lambda x: f"${x:,.0f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

def show_budget_transfer_results(df, from_dept, to_dept, amount):
    """Show results of transferring money between departments"""
    st.subheader("What This Means")
    
    if from_dept == to_dept:
        st.error("Cannot transfer money from a department to itself!")
        return
    
    from_budget = df[df['Department'] == from_dept]['Budget'].iloc[0]
    to_budget = df[df['Department'] == to_dept]['Budget'].iloc[0]
    
    if amount > from_budget:
        st.error(f"{from_dept} doesn't have ${amount:,.0f} to transfer!")
        return
    
    # Show the transfer
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            f"{from_dept} Budget", 
            f"${from_budget - amount:,.0f}",
            delta=f"-${amount:,.0f}"
        )
        
    with col2:
        st.metric(
            f"{to_dept} Budget", 
            f"${to_budget + amount:,.0f}",
            delta=f"+${amount:,.0f}"
        )
    
    st.success(f"Total city budget stays the same - just moved ${amount:,.0f} between departments")

def show_across_board_adjustment_results(df, adjustment_percent):
    """Show results of across-the-board budget adjustments (positive or negative)"""
    st.subheader("What This Means")
    
    total_current_budget = df['Budget'].sum()
    total_change = total_current_budget * (adjustment_percent / 100)
    
    # Show appropriate metric based on adjustment type
    if adjustment_percent > 0:
        st.metric(
            "Total Additional Cost", 
            f"${total_change:,.0f}",
            delta=f"+{adjustment_percent}% across all departments"
        )
        st.info(f"This would cost the city an additional ${total_change:,.0f} total")
        st.info(f"Where will this ${total_change:,.0f} come from? You'll need to find savings elsewhere or raise revenue.")
    elif adjustment_percent < 0:
        st.metric(
            "Total Savings", 
            f"${abs(total_change):,.0f}",
            delta=f"{adjustment_percent}% across all departments"
        )
        st.success(f"This would save the city ${abs(total_change):,.0f} total")
    else:
        st.info("No change to budgets")
        return
    
    # Show department-by-department impact
    st.subheader("Impact on Each Department")
    
    impact_df = df.copy()
    impact_df['Adjustment_Amount'] = impact_df['Budget'] * (adjustment_percent / 100)
    impact_df['New_Budget'] = impact_df['Budget'] + impact_df['Adjustment_Amount']
    
    display_df = impact_df[['Department', 'Budget', 'Adjustment_Amount', 'New_Budget']].copy()
    
    if adjustment_percent > 0:
        display_df.columns = ['Department', 'Current Budget', 'Amount Added', 'New Budget']
    else:
        display_df.columns = ['Department', 'Current Budget', 'Amount Cut', 'New Budget']
    
    for col in ['Current Budget', 'Amount Added' if adjustment_percent > 0 else 'Amount Cut', 'New Budget']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"${abs(x):,.0f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Show warnings for cuts that create shortfalls
    if adjustment_percent < 0:
        problem_depts = impact_df[impact_df['New_Budget'] < impact_df['Actual']]['Department'].tolist()
        if problem_depts:
            st.warning(f"These departments are already spending more than their new budget would allow: {', '.join(problem_depts)}")
            st.info("You may need to make targeted cuts instead of across-the-board cuts.")

def show_emergency_reduction_results(df, target_savings):
    """Show results of emergency budget reduction"""
    st.subheader("Emergency Budget Plan")
    
    total_budget = df['Budget'].sum()
    required_cut_percent = (target_savings / total_budget) * 100
    
    if required_cut_percent > 30:
        st.error(f"This would require cutting {required_cut_percent:.1f}% from all budgets - this may be too severe!")
    
    st.metric(
        "Required Cut Per Department", 
        f"{required_cut_percent:.1f}%",
        delta=f"To save ${target_savings:,.0f}"
    )
    
    # Show what this means for each department
    emergency_df = df.copy()
    emergency_df['Cut_Amount'] = (emergency_df['Budget'] * required_cut_percent / 100)
    emergency_df['New_Budget'] = emergency_df['Budget'] - emergency_df['Cut_Amount']
    emergency_df['Potential_Problem'] = emergency_df['New_Budget'] < emergency_df['Actual']
    
    st.subheader("Emergency Cuts by Department")
    
    display_df = emergency_df[['Department', 'Budget', 'Cut_Amount', 'New_Budget']].copy()
    display_df.columns = ['Department', 'Current Budget', 'Emergency Cut', 'New Budget']
    
    for col in ['Current Budget', 'Emergency Cut', 'New Budget']:
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Warn about problems
    problem_depts = emergency_df[emergency_df['Potential_Problem']]['Department'].tolist()
    if problem_depts:
        st.warning(f"These departments are already spending more than their new budget would allow: {', '.join(problem_depts)}")
        st.info("You may need to make targeted cuts instead of across-the-board cuts.")


# Keep the rest of the original function but skip the complex parts
def render_whatif_simulator_old():
    """
    Original complex version - kept for reference
    """
    # Data loading section
    with st.expander("Step 1: Select Data", expanded=True):
        st.subheader("Select Department Data")
        
        # Load financial data for departments with loading indicator
        with st.spinner("Loading department data..."):
            df = load_org_data()
            
        # Validate data quality
        if df is None or df.empty:
            st.error("No department data available. Please check database connection and data sources.")
            st.info("Contact your administrator to verify database setup and data import.")
            return
            
        # Check for required columns
        required_columns = ["Department"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            st.info("Data structure may be incomplete. Contact your administrator.")
            return
        
        # Select department
        departments = sorted(df["Department"].unique())
        selected_dept = st.selectbox(
            "Select Department", 
            options=departments,
            index=0,
            key="whatif_dept_select"
        )
        
        # Filter data for selected department
        dept_data = df[df["Department"] == selected_dept].copy()
        
        # Allow user to select which columns to display
        available_columns = dept_data.columns.tolist()
        default_columns = ["Fund", "FiscalYear", "Budget", "Actual", "PercentUsed"]
        displayed_columns = [col for col in default_columns if col in available_columns]
        
        selected_columns = st.multiselect(
            "Select Columns to Display",
            options=available_columns,
            default=displayed_columns,
            key="whatif_columns"
        )
        
        # Show a section for account structure but without nesting in another expander
        st.markdown("---")
        st.subheader("Chart of Accounts Analysis")
        
        # Get account masks from settings
        balance_sheet_mask = get_mask_from_settings("BalanceSheet")
        revenue_mask = get_mask_from_settings("Revenue") 
        expense_mask = get_mask_from_settings("Expense")
        
        # Identify account column
        account_col = None
        if "AccountCode" in dept_data.columns:
            account_col = "AccountCode"
        elif "Account" in dept_data.columns:
            account_col = "Account"
            
            if account_col and not dept_data.empty:
                # Apply account structure parsing
                st.write("Using account structure masks to parse account codes into segments:")
                
                # Create a working copy for segment parsing
                dept_data_parsed = dept_data.copy()
                
                # Determine account types based on account number patterns
                dept_data_parsed['AccountType'] = dept_data_parsed[account_col].astype(str).apply(
                    lambda x: 'Revenue' if str(x).startswith('4') or str(x).startswith('3') else
                             ('Expense' if str(x).startswith('5') or str(x).startswith('6') else
                              ('Balance Sheet' if str(x).startswith('1') or str(x).startswith('2') else 'Other'))
                )
                
                # Parse accounts using appropriate masks
                try:
                    # Process expense accounts
                    if expense_mask:
                        expense_accounts = dept_data_parsed[dept_data_parsed['AccountType'] == 'Expense']
                        if not expense_accounts.empty:
                            segments_df = expense_accounts[account_col].astype(str).apply(
                                lambda x: pd.Series(parse_account(x, expense_mask))
                            )
                            for col in segments_df.columns:
                                dept_data_parsed.loc[dept_data_parsed['AccountType'] == 'Expense', col] = segments_df[col].values
                    
                    # Process revenue accounts
                    if revenue_mask:
                        revenue_accounts = dept_data_parsed[dept_data_parsed['AccountType'] == 'Revenue']
                        if not revenue_accounts.empty:
                            segments_df = revenue_accounts[account_col].astype(str).apply(
                                lambda x: pd.Series(parse_account(x, revenue_mask))
                            )
                            for col in segments_df.columns:
                                dept_data_parsed.loc[dept_data_parsed['AccountType'] == 'Revenue', col] = segments_df[col].values
                    
                    # Process balance sheet accounts
                    if balance_sheet_mask:
                        balance_accounts = dept_data_parsed[dept_data_parsed['AccountType'] == 'Balance Sheet']
                        if not balance_accounts.empty:
                            segments_df = balance_accounts[account_col].astype(str).apply(
                                lambda x: pd.Series(parse_account(x, balance_sheet_mask))
                            )
                            for col in segments_df.columns:
                                dept_data_parsed.loc[dept_data_parsed['AccountType'] == 'Balance Sheet', col] = segments_df[col].values
                    
                    # Create segment-based filters
                    available_segments = []
                    if 'Fund' in dept_data_parsed.columns:
                        fund_values = dept_data_parsed['Fund'].dropna().unique()
                        if len(fund_values) > 0:
                            selected_fund = st.selectbox("Filter by Fund", ["All Funds"] + sorted(fund_values.tolist()))
                            if selected_fund != "All Funds":
                                dept_data_parsed = dept_data_parsed[dept_data_parsed['Fund'] == selected_fund]
                                available_segments.append('Fund')
                    
                    if 'Dept' in dept_data_parsed.columns:
                        dept_values = dept_data_parsed['Dept'].dropna().unique()
                        if len(dept_values) > 0:
                            selected_dept_code = st.selectbox("Filter by Department Code", ["All Dept Codes"] + sorted(dept_values.tolist()))
                            if selected_dept_code != "All Dept Codes":
                                dept_data_parsed = dept_data_parsed[dept_data_parsed['Dept'] == selected_dept_code]
                                available_segments.append('Dept')
                    
                    if 'Object' in dept_data_parsed.columns:
                        object_values = dept_data_parsed['Object'].dropna().unique()
                        if len(object_values) > 0:
                            selected_object = st.selectbox("Filter by Object Code", ["All Objects"] + sorted(object_values.tolist()))
                            if selected_object != "All Objects":
                                dept_data_parsed = dept_data_parsed[dept_data_parsed['Object'] == selected_object]
                                available_segments.append('Object')
                    
                    # Use the parsed data with segments for visualization
                    if available_segments:
                        st.subheader("Segment-Based Analysis")
                        
                        # Allow selection of segment for visualization if multiple are available
                        if len(available_segments) > 1:
                            selected_segment = st.selectbox("Group By Segment", available_segments)
                        else:
                            selected_segment = available_segments[0]
                        
                        # Create summary by segment
                        segment_summary = dept_data_parsed.groupby(selected_segment).agg({
                            'Budget': 'sum',
                            'Actual': 'sum'
                        }).reset_index().sort_values('Budget', ascending=False)
                        
                        # Visualize data
                        st.write(f"#### Budget by {selected_segment}")
                        fig = px.bar(
                            segment_summary,
                            x=selected_segment,
                            y=['Budget', 'Actual'],
                            barmode='group',
                            title=f"{selected_dept} Budget and Actual by {selected_segment}"
                        )
                        create_accessible_chart(fig, f"{selected_dept} Budget vs Actual", f"Comparison of budgeted versus actual amounts for {selected_dept} department broken down by {selected_segment}.")
                    
                    # Update main dataframe with filtered/parsed version
                    dept_data = dept_data_parsed
                
                except Exception as e:
                    st.warning(f"Error during account parsing: {e}")
                    st.info("Using original data without account parsing.")
            else:
                st.info("No account column found for structure analysis.")
        
        # Display the selected data with Excel-style filtering
        if selected_columns:
            st.subheader("Department Data")
            
            # Show data summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Department", selected_dept)
            with col2:
                st.metric("Records", len(dept_data))
            with col3:
                st.metric("Columns Selected", len(selected_columns))
            
            # Use advanced filtering component
            from advanced_filters_clean import create_advanced_filter_component, display_filtered_dataframe, create_summary_metrics
            
            # Store original data for comparison
            original_data = dept_data[selected_columns].copy()
            
            # Apply advanced filtering (non-expander version for nested contexts)
            filtered_data = create_advanced_filter_component(
                df=dept_data[selected_columns],
                key_prefix=f"whatif_{selected_dept}",
                default_sort_column="FiscalYear" if "FiscalYear" in selected_columns else None,
                items_per_page=25,
                use_expander=False
            )
            
            # Display summary metrics
            create_summary_metrics(filtered_data, original_data)
            
            # Display the filtered data
            display_filtered_dataframe(
                filtered_data,
                key_prefix=f"whatif_display_{selected_dept}",
                height=400
            )
            
            # Data ready indicator
            st.success(f"✓ Data ready for simulation: {len(dept_data)} records with {len(selected_columns)} columns")
            
            # Add export option
            csv_data = dept_data[selected_columns].to_csv(index=False)
            st.download_button(
                label="Download Data as CSV",
                data=csv_data,
                file_name=f"{selected_dept}_data.csv",
                mime="text/csv"
            )
        else:
            st.info("Please select at least one column to display.")
    
    # What-if query section
    with st.expander("Step 2: Define What-If Scenario", expanded=True):
        st.subheader("Define Your What-If Scenario")
        
        # Check if data is available from Step 1 using session state
        if "whatif_dept_select" not in st.session_state or "whatif_columns" not in st.session_state:
            st.warning("Please complete Step 1 first: Select a department and choose columns to display.")
            st.stop()
        
        # Reload the data to ensure consistency
        temp_df = load_org_data()
        if temp_df is None or temp_df.empty:
            st.error("Data is no longer available. Please refresh and try again.")
            st.stop()
            
        selected_dept = st.session_state.get("whatif_dept_select")
        selected_columns = st.session_state.get("whatif_columns", [])
        dept_data = temp_df[temp_df["Department"] == selected_dept].copy()
        
        if selected_columns and not dept_data.empty:
            # Validate selected columns still exist
            available_cols = [col for col in selected_columns if col in dept_data.columns]
            if not available_cols:
                st.error("Selected columns are no longer available in the dataset.")
                st.stop()
            selected_columns = available_cols
        
        scenario_options = [
            "Budget adjustment across funds",
            "Cut specific category by percentage",
            "Increase specific category by percentage",
            "Shift funding between categories",
            "Emergency budget reduction",
            "Multi-year budget projection"
        ]
        
        selected_scenario = st.selectbox(
            "Select Scenario Type",
            options=scenario_options,
            key="whatif_scenario_type"
        )
        
        # Dynamic prompt based on scenario type
        default_prompts = {
            "Budget adjustment across funds": f"Adjust {selected_dept} budget by cutting 5% from all funds",
            "Cut specific category by percentage": f"Cut {selected_dept} capital expenses by 10%",
            "Increase specific category by percentage": f"Increase {selected_dept} training budget by 15%",
            "Shift funding between categories": f"Move 10% of {selected_dept} equipment budget to personnel",
            "Emergency budget reduction": f"Implement emergency 8% reduction across all {selected_dept} budget categories",
            "Multi-year budget projection": f"Project {selected_dept} budget with 3% annual growth for next 3 years"
        }
        
        # Allow custom prompt
        use_custom_prompt = st.checkbox("Use Custom Prompt", key="whatif_custom_prompt_check")
        
        if use_custom_prompt:
            whatif_prompt = st.text_area(
                "What would you like to simulate?", 
                height=80,
                key="whatif_custom_prompt",
                help="Describe your what-if scenario in natural language"
            )
        else:
            whatif_prompt = st.text_area(
                "What would you like to simulate?", 
                value=default_prompts.get(selected_scenario, ""),
                height=80,
                key="whatif_default_prompt"
            )
    
    # Run simulation
    if st.button("Run What-If Simulation", type="primary", use_container_width=True):
        if whatif_prompt and not dept_data.empty:
            with st.spinner("Running simulation..."):
                # Use AI Hub's simulate_adjustment function
                try:
                    # Use the filtered data with selected columns if available
                    data_for_simulation = dept_data[selected_columns] if selected_columns else dept_data
                    
                    # Create a copy of the data for simulation
                    simulation_data = simulate_adjustment(
                        prompt=whatif_prompt,
                        df=data_for_simulation.copy()
                    )
                    
                    # Store results in session state
                    st.session_state['original_data'] = dept_data.copy()
                    st.session_state['simulation_data'] = simulation_data
                    st.session_state['whatif_prompt'] = whatif_prompt
                    
                    # Show comparison
                    st.subheader("Simulation Results")
                    
                    # Side-by-side comparison (original vs. simulated)
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Original Data")
                        if selected_columns:
                            st.dataframe(dept_data[selected_columns], use_container_width=True)
                        else:
                            st.dataframe(dept_data, use_container_width=True)
                    
                    with col2:
                        st.markdown("#### Simulated Data")
                        if selected_columns:
                            st.dataframe(simulation_data[selected_columns], use_container_width=True)
                        else:
                            st.dataframe(simulation_data, use_container_width=True)
                    
                    # Calculate diffs for numerical columns
                    numeric_cols = simulation_data.select_dtypes(include=['number']).columns.tolist()
                    if numeric_cols:
                        st.subheader("Budget Impact Analysis")
                        
                        # Calculate total impact
                        if 'Budget' in numeric_cols:
                            original_total = dept_data['Budget'].sum()
                            simulated_total = simulation_data['Budget'].sum()
                            total_diff = simulated_total - original_total
                            percent_diff = (total_diff / original_total) * 100 if original_total != 0 else 0
                            
                            # Display impact metrics
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "Original Total Budget", 
                                    f"${original_total:,.2f}"
                                )
                            
                            with col2:
                                st.metric(
                                    "Simulated Total Budget", 
                                    f"${simulated_total:,.2f}",
                                    delta=f"${total_diff:,.2f}"
                                )
                            
                            with col3:
                                st.metric(
                                    "Percentage Change", 
                                    f"{percent_diff:.2f}%"
                                )
                        
                        # Create comparison chart for visualizing differences
                        # This assumes 'Budget' and 'FiscalYear' columns exist
                        if 'Budget' in numeric_cols and 'FiscalYear' in simulation_data.columns:
                            # Prepare data for chart
                            chart_data = pd.DataFrame({
                                'Year': dept_data['FiscalYear'],
                                'Original Budget': dept_data['Budget'],
                                'Simulated Budget': simulation_data['Budget']
                            })
                            
                            # Create bar chart comparing original vs simulated
                            fig = go.Figure()
                            
                            fig.add_trace(go.Bar(
                                x=chart_data['Year'],
                                y=chart_data['Original Budget'],
                                name='Original Budget',
                                marker_color='#2a9d8f'
                            ))
                            
                            fig.add_trace(go.Bar(
                                x=chart_data['Year'],
                                y=chart_data['Simulated Budget'],
                                name='Simulated Budget',
                                marker_color='#e76f51'
                            ))
                            
                            fig.update_layout(
                                title='Budget Comparison by Year',
                                xaxis_title='Year',
                                yaxis_title='Budget Amount ($)',
                                barmode='group',
                                height=400
                            )
                            
                            create_accessible_chart(fig, "Budget Comparison by Year", "Multi-year comparison showing the impact of simulated adjustments on department budgets over time.")
                    
                    # Get AI insights
                    st.subheader("AI Analysis of Simulation")
                    
                    with st.spinner("Generating insights..."):
                        # Get AI analysis of the simulation impact
                        # Craft a specific prompt for analysis
                        analysis_prompt = f"""
                        Analyze the impact of the following budget scenario for {selected_dept}:
                        "{whatif_prompt}"
                        
                        Provide insights on:
                        1. The overall financial impact
                        2. Potential operational implications
                        3. Long-term sustainability considerations
                        4. Alternative approaches to consider
                        5. Implementation recommendations
                        """
                        
                        # Use AI Hub to get insights
                        analysis = ask_ai(
                            prompt=analysis_prompt,
                            df=simulation_data,
                            max_tokens=750
                        )
                        
                        # Display the analysis
                        st.markdown(analysis)
                    
                    # Offer option to download results with robust error handling
                    try:
                        from io import BytesIO
                        import xlsxwriter
                        
                        # Validate data before export
                        if dept_data.empty or simulation_data.empty:
                            st.warning("Cannot create Excel export: simulation data is empty")
                        else:
                            # Create Excel file with multiple sheets
                            buffer = BytesIO()
                            
                            # Get safe filename
                            safe_dept_name = str(selected_dept).replace(' ', '_').replace('/', '_') if selected_dept else "department"
                            
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                # Export original data
                                if isinstance(dept_data, pd.DataFrame) and not dept_data.empty:
                                    dept_data.to_excel(writer, sheet_name='Original Data', index=False)
                                
                                # Export simulation data
                                if isinstance(simulation_data, pd.DataFrame) and not simulation_data.empty:
                                    simulation_data.to_excel(writer, sheet_name='Simulated Data', index=False)
                                
                                # Create comparison sheet for numeric columns
                                numeric_cols = dept_data.select_dtypes(include=['int64', 'float64']).columns.tolist()
                                if numeric_cols and len(dept_data) == len(simulation_data):
                                    try:
                                        comparison_data = pd.DataFrame()
                                        for col in numeric_cols:
                                            if col in dept_data.columns and col in simulation_data.columns:
                                                comparison_data[f'{col}_Original'] = dept_data[col].values
                                                comparison_data[f'{col}_Simulated'] = simulation_data[col].values
                                                diff = simulation_data[col].values - dept_data[col].values
                                                comparison_data[f'{col}_Difference'] = diff
                                                
                                                # Calculate percentage change with zero division protection
                                                pct_change = []
                                                for orig, sim in zip(dept_data[col].values, simulation_data[col].values):
                                                    if orig != 0:
                                                        pct_change.append(((sim - orig) / orig) * 100)
                                                    else:
                                                        pct_change.append(0)
                                                comparison_data[f'{col}_Pct_Change'] = pct_change
                                        
                                        if not comparison_data.empty:
                                            comparison_data.to_excel(writer, sheet_name='Impact Analysis', index=False)
                                    except Exception as e:
                                        st.warning(f"Could not create impact analysis sheet: {str(e)}")
                            
                            # Offer download with validated filename
                            filename = f"whatif_simulation_{safe_dept_name}.xlsx"
                            st.download_button(
                                label="Download Simulation Results (Excel)",
                                data=buffer.getvalue(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                    except ImportError:
                        st.error("Excel export requires xlsxwriter package. Using CSV export instead.")
                        # Fallback to CSV export
                        csv_data = simulation_data.to_csv(index=False)
                        st.download_button(
                            label="Download Simulation Results (CSV)",
                            data=csv_data,
                            file_name=f"whatif_simulation_{safe_dept_name}.csv",
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.error(f"Export error: {str(e)}. Please try CSV export instead.")
                        # Emergency CSV fallback
                        try:
                            csv_data = simulation_data.to_csv(index=False)
                            st.download_button(
                                label="Download Simulation Results (CSV)",
                                data=csv_data,
                                file_name=f"whatif_simulation_backup.csv",
                                mime="text/csv"
                            )
                        except:
                            st.error("Unable to export data in any format.")
                    
                except Exception as e:
                    st.error(f"Error running simulation: {str(e)}")
        else:
            st.error("Please select a department and enter a what-if prompt to run the simulation.")
    
    # Add divider before anomaly detection section
    st.divider()
    
    # Anomaly Detection Section
    if not dept_data.empty:
        render_anomaly_analysis(dept_data)
    else:
        st.info("Select a department above to enable anomaly detection analysis.")

def render_grant_integration(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Grant Integration tab for finding and incorporating grant funding into scenarios
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.header("Grant Integration")
    st.markdown(f"""
    Find and integrate grant opportunities into your {org_display_name} funding scenarios.
    Search for relevant grants and add them directly to your scenario planning.
    """)
    
    # Standard Grant Opportunities Section
    st.subheader("Federal Grant Opportunities")
    st.info("These federal grant opportunities are commonly available for municipal projects.")
    
    # List of standard grants with their details
    standard_grants = [
        {
                "name": "Community Development Block Grant (CDBG)",
                "agency": "Department of Housing and Urban Development",
                "amount": "$200,000 - $800,000",
                "details": "Flexible program that provides communities with resources to address community development needs.",
                "department": "Administration",
                "link": "https://www.hud.gov/program_offices/comm_planning/cdbg"
            },
            {
                "name": "COPS Hiring Program (CHP)",
                "agency": "Department of Justice",
                "amount": "$250,000 - $750,000",
                "details": "Funding to hire additional law enforcement officers for community policing initiatives.",
                "department": "Police",
                "link": "https://cops.usdoj.gov/chp"
            },
            {
                "name": "Assistance to Firefighters Grant (AFG)",
                "agency": "FEMA",
                "amount": "$200,000 - $600,000",
                "details": "Helps fire departments obtain equipment, protective gear, emergency vehicles, and training.",
                "department": "Fire",
                "link": "https://www.fema.gov/grants/preparedness/firefighters/assistance-grants"
            },
            {
                "name": "Clean Water State Revolving Fund (CWSRF)",
                "agency": "EPA",
                "amount": "$300,000 - $900,000",
                "details": "Low-cost financing for water quality infrastructure and improvements.",
                "department": "Water",
                "link": "https://www.epa.gov/cwsrf"
            },
            {
                "name": "Water Infrastructure Improvements for the Nation (WIIN)",
                "agency": "EPA",
                "amount": "$250,000 - $800,000",
                "details": "Grants for drinking water infrastructure and water quality improvements.",
                "department": "Sewer",
                "link": "https://www.epa.gov/ground-water-and-drinking-water/drinking-water-grants"
            },
            {
                "name": "Land and Water Conservation Fund (LWCF)",
                "agency": "National Park Service",
                "amount": "$150,000 - $450,000",
                "details": "Funding for outdoor recreation areas and facilities.",
                "department": "Parks",
                "link": "https://www.nps.gov/subjects/lwcf/index.htm"
            }
    ]
    
    # Create columns for each grant
    for i, grant in enumerate(standard_grants):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {i+1}. {grant['name']}")
            st.markdown(f"**Agency**: {grant['agency']}")
            st.markdown(f"**Amount**: {grant['amount']}")
            st.markdown(f"**Details**: {grant['details']}")
            st.markdown(f"**Relevant Department**: {grant['department']}")
            st.markdown(f"**Link**: [{grant['link']}]({grant['link']})")
        
        with col2:
            # Add button to add this grant to current scenario
            if st.button(f"Add to Scenario", key=f"grant_{i}"):
                # Parse the amount range for scenario planning
                amount_str = grant['amount'].replace('$', '').replace(',', '')
                min_amount, max_amount = 100000, 500000  # Default values
                
                try:
                    # Try to extract min and max from the amount string
                    import re
                    amounts = re.findall(r'\d+', amount_str)
                    if len(amounts) >= 2:
                        min_amount = float(amounts[0]) * (1000 if len(amounts[0]) <= 3 else 1)
                        max_amount = float(amounts[1]) * (1000 if len(amounts[1]) <= 3 else 1)
                except:
                    pass  # Use default values if parsing fails
                
                # Store grant in session state for use in scenario builder
                if 'selected_grants' not in st.session_state:
                    st.session_state.selected_grants = []
                
                grant_data = {
                    'name': grant['name'],
                    'agency': grant['agency'],
                    'min_amount': min_amount,
                    'max_amount': max_amount,
                    'department': grant['department']
                }
                
                st.session_state.selected_grants.append(grant_data)
                
                # Set flag to indicate grants are ready for import
                st.session_state.import_grants_to_scenario = True
                
                st.success(f"Added '{grant['name']}' to your scenario planning! Go to Scenario Builder to import.")
        
        st.markdown("---")
    
    # Custom Grant Search Section
    st.subheader("Custom Grant Search")
    
    col1, col2 = st.columns(2)
    with col1:
        search_department = st.selectbox(
            "Filter by Department:",
            options=["All Departments", "Administration", "Police", "Fire", "Water", "Sewer", "Parks", "Streets", "Other"],
            index=0
        )
    
    with col2:
        search_keywords = st.text_input(
            "Search Keywords:",
            placeholder="e.g., infrastructure, technology, community development"
        )
    
    if st.button("Search for Grants"):
        if search_keywords:
            st.info(f"Searching for grants related to '{search_keywords}' for {search_department}...")
            
            # This would typically connect to a grant database API
            # For now, show a message about connecting to external sources
            st.markdown("""
            **Grant Search Results:**
            
            To access real-time grant opportunities, this feature would connect to:
            - Grants.gov database
            - State-specific grant databases  
            - Foundation grant directories
            
            For live grant data integration, please provide API credentials for grant databases.
            """)
        else:
            st.warning("Please enter search keywords to find grants.")
    
    # Selected Grants Summary
    if 'selected_grants' in st.session_state and st.session_state.selected_grants:
        st.subheader("Selected Grants for Scenario Planning")
        
        total_min = sum(grant['min_amount'] for grant in st.session_state.selected_grants)
        total_max = sum(grant['max_amount'] for grant in st.session_state.selected_grants)
        
        st.info(f"**Total Grant Funding Range**: ${total_min:,.0f} - ${total_max:,.0f}")
        
        # Display selected grants
        for i, grant in enumerate(st.session_state.selected_grants):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{grant['name']}** - {grant['agency']}")
                st.write(f"Amount: ${grant['min_amount']:,.0f} - ${grant['max_amount']:,.0f}")
            with col2:
                if st.button("Remove", key=f"remove_grant_{i}"):
                    st.session_state.selected_grants.pop(i)
                    st.rerun()
        
        # Clear all button
        if st.button("Clear All Selected Grants"):
            st.session_state.selected_grants = []
            st.rerun()
        
        st.info("Tip: Go to the 'Scenario Builder' tab to incorporate these grants into your funding scenarios.")
