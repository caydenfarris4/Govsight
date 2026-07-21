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

ARCHITECTURAL DECISIONS:
1. Tabbed interface design: Separates complex functionality into digestible sections
   WHY: Municipal users need focused workflows without overwhelming complexity

2. Real-time visualization: Updates charts as users modify budget allocations
   WHY: Immediate visual feedback helps users understand impact of changes

3. Scenario persistence: Save/load functionality for iterative planning
   WHY: Budget planning is an iterative process requiring multiple sessions

4. AI integration: Provides intelligent recommendations and impact analysis
   WHY: Municipal staff need expert guidance for complex financial decisions

5. Regulatory compliance: Built-in legislative impact analysis
   WHY: Municipal budgets must comply with various regulations and restrictions

The module uses a tabbed interface to organize functionality:
- Scenario Builder: Main funding scenario creation and analysis
- Legislative Impact Analyzer: Assess regulatory impact on scenarios  
- What-If Scenario Simulator: Test hypothetical budget adjustments
"""

# Add root directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import AI and analysis modules
from modules.ai_hub.ai_hub import ask_ai, simulate_adjustment
# WHY AI INTEGRATION: Provides intelligent budget recommendations and scenario analysis

from modules.utils.mask_parser import get_mask_from_settings, parse_account
# WHY MASK PARSER: Standardizes GL account formatting across different municipal systems

from modules.utils.anomaly_detection_module import render_anomaly_analysis
# WHY ANOMALY DETECTION: Identifies unusual budget patterns that need attention

from modules.utils.accessibility_helper import create_accessible_chart
# WHY ACCESSIBILITY: Government applications must be ADA compliant

# Core framework imports
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Additional imports for simulations and modeling
# WHY SCIENTIFIC COMPUTING: Municipal budget scenarios require statistical analysis
import numpy as np
from sklearn.ensemble import IsolationForest    # For anomaly detection in budget data
from sklearn.linear_model import LinearRegression  # For trend forecasting
from sklearn.model_selection import train_test_split  # For model validation
import plotly.express as px  # For additional visualization options

# Import conversational what-if simulator
try:
    from modules.scenario_planner.whatif_simulator import process_whatif_question
except ImportError:
    process_whatif_question = None

# Performance optimization for Monte Carlo simulations
@st.cache_data(ttl=300, max_entries=5)  # Cache Monte Carlo results for 5 minutes
def run_monte_carlo_optimized(base_amount: float, volatility: float, num_simulations: int = 1000) -> Dict[str, Any]:
    """Optimized Monte Carlo simulation with caching and performance improvements"""
    # Limit simulations for better performance
    max_simulations = min(num_simulations, 5000)  # Cap at 5000 for performance
    
    # Generate random samples efficiently
    np.random.seed(42)  # For reproducible results
    random_factors = np.random.normal(1.0, volatility, max_simulations)
    
    # Vectorized calculation
    simulated_values = base_amount * random_factors
    
    # Calculate statistics
    mean_value = np.mean(simulated_values)
    std_value = np.std(simulated_values)
    percentiles = np.percentile(simulated_values, [5, 25, 50, 75, 95])
    
    return {
        "simulated_values": simulated_values,
        "mean": mean_value,
        "std": std_value,
        "percentiles": {
            "p5": percentiles[0],
            "p25": percentiles[1],
            "p50": percentiles[2],
            "p75": percentiles[3],
            "p95": percentiles[4]
        },
        "num_simulations": max_simulations
    }

@st.cache_data(ttl=600)  # Cache data loading for 10 minutes
def load_scenario_data_optimized(org: str) -> pd.DataFrame:
    """Optimized scenario data loading with caching"""
    try:
        data = load_org_data(org)
        if data.empty:
            return pd.DataFrame()
        
        # Optimize data types for memory efficiency
        for col in data.columns:
            if data[col].dtype == 'object':
                try:
                    data[col] = pd.to_numeric(data[col], errors='ignore')
                except:
                    pass
        
        return data
    except Exception as e:
        st.error(f"Data loading error: {e}")
        return pd.DataFrame()

# Import database functions from db_connection.py
from modules.database.db_connection import (
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
from modules.reports.summary_report_generator import generate_full_scenario_report, add_scenario_to_comparison, remove_scenario_from_comparison

# Import report generator module
import modules.reports.summary_report_generator as report_gen

def render_restricted_fund_guidance():
    """
    Render the Restricted Fund Guidance tab
    
    This tab provides guidance on compliant usage of restricted funds
    based on fund classifications from the admin panel.
    """
    st.header("Restricted Fund Guidance")
    st.markdown("Review your restricted funds and get guidance on compliant usage.")

    from modules.utils.fund_policy import load_fund_classifications
    classifications = load_fund_classifications()
    if not classifications:
        st.warning("No fund classifications found. Please use the Fund Classification Manager in the Admin Panel to classify your funds.")

    # Load fund balances from the database using the correct table structure
    try:
        conn = get_database_connection()
        fund_data = pd.read_sql("""
            SELECT DISTINCT 
                Fund as FundCode, 
                Fund as FundName, 
                SUM(Budget) as EndingBalance
            FROM DepartmentPerformance 
            GROUP BY Fund
        """, conn)
        conn.close()
    except Exception as e:
        st.error(f"Database error while loading fund data: {str(e)}")
        # Create empty data structure if query fails
        fund_data = pd.DataFrame(columns=["FundCode", "FundName", "EndingBalance"])
        st.warning("Unable to load fund data from the database. This may be due to:")
        st.info("• Database connection issues\n• Missing DepartmentPerformance table\n• Insufficient permissions")
        st.info("Please contact your system administrator or check your network connection.")
    
    # Display fund information
    if fund_data.empty:
        st.info("No fund data available - using default general fund structure")
        fund_data = pd.DataFrame({
            "FundCode": ["001"],
            "FundName": ["General Fund"],
            "EndingBalance": [0]
        })

    if not fund_data.empty:
        # Add fund type classification to the dataframe
        fund_data["Type"] = fund_data["FundCode"].astype(str).apply(lambda x: classifications.get(str(x), "Unclassified"))
        
        # Filter for restricted funds
        restricted_funds = fund_data[fund_data["Type"] == "Restricted"]

        st.subheader("🔒 Restricted Funds Overview")
        
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
            with st.expander("How to Classify Funds"):
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

# Monte Carlo plotting and UI functions have been moved to modules/navi/monte_carlo_simulator.py

# --- AI PROPOSAL GENERATOR MODULE ---
def generate_ai_base_scenario(project_name, cost, department_names=None, scenario_data=None, enhanced_context=None):
    """
    Generate AI-powered scenario plan with enhanced grant and funding context
    
    ARCHITECTURAL DECISION: Enhanced context integration
    WHY: AI can provide more accurate and comprehensive recommendations when given
    complete funding context including grants and scenario data
    """
    phases = [
        {"name": "Planning", "duration_months": 2, "cost_pct": 10},
        {"name": "Construction", "duration_months": 10, "cost_pct": 75},
        {"name": "Closeout", "duration_months": 2, "cost_pct": 15}
    ]
    
    # Enhanced summary with comprehensive funding details
    funding_details = []
    grant_details = []
    
    # Add scenario funding details if available
    if scenario_data:
        if scenario_data.get("tax_revenue"):
            funding_details.append(f"Tax Revenue: ${float(scenario_data['tax_revenue']):,.0f}")
        if scenario_data.get("grant_funding"):
            funding_details.append(f"Baseline Grant Funding: ${float(scenario_data['grant_funding']):,.0f}")
        if scenario_data.get("private_investment"):
            funding_details.append(f"Private Investment: ${float(scenario_data['private_investment']):,.0f}")
        if scenario_data.get("bonds_required"):
            funding_details.append(f"Bond Financing: ${float(scenario_data['bonds_required']):,.0f}")
    
    # Add enhanced grant context if available
    if enhanced_context and enhanced_context.get('grants'):
        for grant in enhanced_context['grants']:
            grant_details.append(f"{grant['name']} ({grant['agency']}): ${grant['amount']:,.0f}")
        
        if enhanced_context.get('total_grant_funding', 0) > 0:
            funding_details.append(f"Additional Grant Opportunities: ${enhanced_context['total_grant_funding']:,.0f}")
    
    # Create comprehensive summary
    if funding_details or grant_details:
        funding_text = " | ".join(funding_details) if funding_details else "Funding strategy under development"
        grant_text = "; ".join(grant_details) if grant_details else "No specific grants identified"
        
        summary = f"""The {project_name} is a strategic capital investment with total estimated cost of ${cost:,.0f}. 
        
FUNDING STRATEGY: {funding_text}

GRANT OPPORTUNITIES: {grant_text}

The project includes comprehensive planning, construction, and closeout phases with integrated risk mitigation and grant management strategies."""
    else:
        summary = f"The {project_name} is a strategic capital investment aimed at addressing long-term community needs. Estimated total cost is ${cost:,.0f}. The project includes planning, construction, and closeout phases."

    return {
        "phases": phases,
        "total_duration": sum(p["duration_months"] for p in phases),
        "risks": ["Delays in permitting", "Cost overruns", "Grant disbursement timing", "Revenue shortfalls", "Grant application deadlines"],
        "summary": summary,
        "project_name": project_name,
        "project_cost": cost,
        "scenario_data": scenario_data,
        "funding_sources": scenario_data if scenario_data else None,
        "enhanced_context": enhanced_context,
        "grant_opportunities": enhanced_context.get('grants', []) if enhanced_context else []
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
    # PDF generation capability (optional)
    try:
        from fpdf2 import FPDF
        PDF_AVAILABLE = True
    except ImportError:
        try:
            from fpdf import FPDF
            PDF_AVAILABLE = True
        except ImportError:
            # PDF functionality will be disabled if fpdf2 is not available
            class FPDF:
                def __init__(self, *args, **kwargs):
                    raise ImportError("PDF functionality requires fpdf2 package")
            PDF_AVAILABLE = False
    
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
    """
    Enhanced AI Proposal Generator with funding breakdown visualization and grant integration
    
    ARCHITECTURAL DECISIONS:
    1. Funding visualization integration: Uses same chart code as scenario builder
       WHY: Provides consistent visual representation of funding sources
    
    2. Grant data integration: Automatically includes grants from grant finder
       WHY: Streamlines workflow from grant discovery to proposal generation
    
    3. AI-enhanced proposal content: Leverages funding details for better proposals
       WHY: AI can provide more accurate recommendations with complete funding context
    """
    st.header("AI Proposal Generator")
    st.markdown("""
    Generate comprehensive project proposals with funding breakdown visualizations and integrated grant opportunities.
    Create detailed project plans with phases, timelines, risk assessments, and complete funding strategies.
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Project Information")
        
        # Project name input (open text field)
        project_name = st.text_input("Project Name", value="New Infrastructure Project", 
                                    help="Enter any project name or select from saved scenarios below")
        project_cost = st.number_input("Estimated Cost ($)", value=1000000.0, step=10000.0)
        
        # Grant Integration Section
        st.markdown("### Grant Integration")
        available_grants = []
        total_grant_funding = 0.0
        
        # Check for grants from grant finder
        if 'selected_grants' in st.session_state and st.session_state.selected_grants:
            st.success(f"Found {len(st.session_state.selected_grants)} grants from Grant Finder!")
            
            for grant in st.session_state.selected_grants:
                # Calculate estimated grant amount (use midpoint of range)
                grant_amount = (grant['min_amount'] + grant['max_amount']) / 2
                total_grant_funding += grant_amount
                available_grants.append({
                    'name': grant['name'],
                    'agency': grant['agency'],
                    'amount': grant_amount,
                    'department': grant['department']
                })
                
                # Display grant info
                with st.expander(f"{grant['name']}", expanded=False):
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.write(f"**Agency:** {grant['agency']}")
                        st.write(f"**Department:** {grant['department']}")
                    with col_g2:
                        st.metric("Estimated Amount", f"${grant_amount:,.0f}")
                        st.write(f"Range: ${grant['min_amount']:,.0f} - ${grant['max_amount']:,.0f}")
        else:
            st.info("No grants selected. Visit Grant Integration tab to find relevant grants for your project.")
        
        # Optional: Load from saved scenarios
        scenarios = get_scenarios()
        scenario_data = None
        
        if scenarios:
            st.markdown("### Scenario Data")
            scenario_names = ["None"] + [s["name"] for s in scenarios]
            selected_scenario_name = st.selectbox("Load Scenario Data", scenario_names)
            
            if selected_scenario_name != "None":
                selected_scenario = next((s for s in scenarios if s["name"] == selected_scenario_name), None)
                if selected_scenario:
                    # Update project details with scenario data
                    project_name = selected_scenario["name"]
                    project_cost = float(selected_scenario.get("total_cost", project_cost))
                    scenario_data = selected_scenario
                    
                    # Display scenario details
                    st.success(f"Loaded scenario: {project_name}")
                    
                    # Create funding breakdown visualization (exact same as scenario builder)
                    st.markdown("#### Funding Breakdown Visualization")
                    
                    # Extract funding data using exact same variable names as scenario builder
                    # Map scenario database fields to scenario builder variable names
                    total_reallocation = sum(selected_scenario.get("department_allocations", {}).values()) if selected_scenario.get("department_allocations") else 0
                    tax_revenue = float(selected_scenario.get("tax_revenue", 0))
                    grant = float(selected_scenario.get("grant", 0)) + total_grant_funding  # Use 'grant' not 'grant_funding' to match scenario builder
                    private_investment = float(selected_scenario.get("private_investment", 0))
                    
                    # Calculate funding total and bonds needed (exact same logic as scenario builder)
                    funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
                    bonds_needed = round(max(0, project_cost - funding_total), 2)
                    
                    # Create funding breakdown chart (EXACT same code as scenario builder lines 1118-1164)
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
                        from modules.utils.accessibility_helper import create_accessible_chart
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
                        
                        # Add funding summary metrics (exact same as scenario builder lines 1186-1201)
                        st.markdown("##### Funding Summary")
                        funding_percentage = round((funding_total / project_cost) * 100, 2) if project_cost > 0 else 0
                        
                        col_m1, col_m2, col_m3 = st.columns(3)
                        
                        with col_m1:
                            st.metric("Total Project Cost", f"${project_cost:,.2f}")
                        
                        with col_m2:
                            st.metric("Total Secured Funding", f"${funding_total:,.2f}", delta=f"{funding_percentage:.1f}% Funded")
                        
                        with col_m3:
                            st.metric("Bonds Required", f"${bonds_needed:,.2f}", delta=f"-${funding_total:,.2f} from other sources" if funding_total > 0 else None)

        
        # Department selection
        departments = get_departments(org)
        if departments:
            dept_names = list(departments.keys())
            selected_depts = st.multiselect("Involved Departments", dept_names, default=dept_names[:2] if len(dept_names) >= 2 else dept_names)
        else:
            selected_depts = ["Administration", "Public Works"]
    
    with col2:
        st.subheader("AI Generation")
        
        # Enhanced AI generation with grant and funding context
        if st.button("Generate Enhanced AI Plan", use_container_width=True, type="primary"):
            with st.spinner("Creating comprehensive AI proposal with funding analysis..."):
                # Prepare enhanced context for AI
                enhanced_context = {
                    'grants': available_grants,
                    'total_grant_funding': total_grant_funding,
                    'funding_secured': total_grant_funding > 0
                }
                
                plan = generate_ai_base_scenario(project_name, project_cost, selected_depts, scenario_data, enhanced_context)
                st.session_state["ai_plan"] = plan
                st.success("Enhanced plan created with funding analysis!")
                st.rerun()
        
        # Quick stats
        if available_grants:
            st.markdown("---")
            st.markdown("**Grant Summary:**")
            st.metric("Total Grants", len(available_grants))
            st.metric("Estimated Funding", f"${total_grant_funding:,.0f}")
            if project_cost > 0:
                grant_coverage = (total_grant_funding / project_cost) * 100
                st.metric("Coverage", f"{grant_coverage:.1f}%")

    # Display generated plan if available
    if "ai_plan" in st.session_state:
        st.markdown("---")
        plan = st.session_state["ai_plan"]
        
        # Enhanced plan display with funding information
        render_scenario_plan_editor(plan)

        # Enhanced PDF download with funding charts
        st.markdown("---")
        col_download1, col_download2 = st.columns(2)
        
        with col_download1:
            try:
                pdf_bytes = generate_proposal_pdf(plan)
                st.download_button(
                    label="Download Enhanced Proposal PDF",
                    data=pdf_bytes,
                    file_name=f"{plan['project_name'].replace(' ', '_').lower()}_enhanced_proposal.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF generation error: {e}")
                # Fallback to basic PDF
                try:
                    pdf_bytes = generate_proposal_pdf(plan)
                    st.download_button(
                        label="Download Basic Proposal PDF",
                        data=pdf_bytes,
                        file_name=f"{plan['project_name'].replace(' ', '_').lower()}_proposal.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e2:
                    st.error(f"Basic PDF generation also failed: {e2}")
        
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

    try:
        df = load_scenario_data_optimized()
        if df.empty:
            st.warning("No data found in the selected organization database.")
            st.info("Please ensure your organization data has been properly loaded, or contact your administrator.")
            st.stop()
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        st.info("Unable to connect to the organization database. Please check your network connection and try again.")
        st.stop()

    # Department restrictions
    allowed_depts = get_user_departments()
    if allowed_depts:
        df = df[df["Department"].isin(allowed_depts)]

    departments = sorted(df["Department"].unique())
    selected_dept = st.selectbox("Select Department for Scenario", departments)

    # Project inputs with enhanced security validation
    try:
        from modules.utils.security_utils import validate_project_name, validate_text_input, handle_error_safely
    except ImportError:
        st.error("Security validation module not available. Please contact your administrator.")
        return
    
    project_name = st.text_input("Enter Project Name", help="Enter a valid project name (alphanumeric characters, spaces, and common punctuation only)")
    
    # Validate project name with security checks
    name_validation = {'valid': True, 'message': ''}
    if project_name:
        name_validation = validate_project_name(project_name)
        if not name_validation['valid']:
            st.error(name_validation['message'])
            project_name = ""
    
    project_cost = st.number_input("Projected Project Cost", min_value=0, value=1000000, max_value=1000000000)
    tax_increase = st.number_input("Projected Tax Revenue Increase", min_value=0, value=250000, max_value=1000000000)
    grant_amount = st.number_input("Projected Grant Aid", min_value=0, value=300000, max_value=1000000000)
    project_notes = st.text_area("Optional Project Notes", height=100, help="Enter project details (plain text only)", max_chars=1000)
    
    # Validate project notes with security checks
    notes_validation = {'valid': True, 'message': ''}
    if project_notes:
        notes_validation = validate_text_input(project_notes, "Project notes", max_length=1000)
        if not notes_validation['valid']:
            st.error(notes_validation['message'])
            project_notes = ""

    if st.button("Save Scenario"):
        # Validate inputs before saving
        if not project_name or not project_name.strip():
            st.error("Please enter a valid project name.")
        elif project_cost <= 0:
            st.error("Project cost must be greater than 0.")
        else:
            # Sanitize inputs before saving
            sanitized_name = project_name.strip()
            sanitized_notes = project_notes.strip() if project_notes else ""
            
            if "saved_scenarios" not in st.session_state:
                st.session_state.saved_scenarios = []
            
            # Save to session state with sanitized data
            st.session_state.saved_scenarios.append({
                "name": sanitized_name,
                "department": selected_dept,
                "cost": project_cost,
                "tax_increase": tax_increase,
                "grant_amount": grant_amount,
                "notes": sanitized_notes
            })
            
            # Try to save to database with parameterized queries and secure error handling
            try:
                from modules.database.connection_manager import get_database_connection
                from modules.utils.security_utils import sanitize_for_database, handle_error_safely, log_security_event
                
                # Additional sanitization for database
                db_safe_name = sanitize_for_database(sanitized_name)
                db_safe_notes = sanitize_for_database(sanitized_notes)
                
                conn = get_database_connection()
                if conn:
                    cursor = conn.cursor()
                    # Use parameterized query to prevent SQL injection
                    cursor.execute("""
                        INSERT INTO scenarios (name, project_name, total_cost, tax_revenue, grant_funding, private_investment, bonds_needed)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (db_safe_name, db_safe_name, project_cost, tax_increase, grant_amount, 0, max(0, project_cost - tax_increase - grant_amount)))
                    conn.commit()
                    conn.close()
                    
                    # Log successful scenario creation
                    user_id = st.session_state.get('user', {}).get('username', 'unknown')
                    log_security_event("scenario_created", f"Scenario '{db_safe_name}' created", user_id)
                    
                    st.success(f"Scenario '{sanitized_name}' saved successfully to database!")
                else:
                    st.success(f"Scenario '{sanitized_name}' saved to session (database unavailable)!")
            except Exception as e:
                # Use secure error handling
                safe_message = handle_error_safely(e, "Unable to save scenario to database. Please try again.")
                st.warning(safe_message)
                st.success(f"Scenario '{sanitized_name}' saved to session!")

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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Scenario Builder", 
        "Legislative Impact Analyzer", 
        "What-If Scenario Simulator",
        "Restricted Fund Guidance",
        "AI Proposal Generator",
        "Grant Integration",
        "Demographics & Environment"
    ])
    
    with tab1:
        render_scenario_builder(org, org_display_name)
    
    with tab2:
        render_legislative_impact_analyzer()
    
    with tab3:
        render_conversational_whatif_simulator(org, org_display_name)
        
    with tab4:
        render_restricted_fund_guidance()
    
    with tab5:
        render_ai_proposal_generator(org, org_display_name)
    
    with tab6:
        render_grant_integration(org, org_display_name)
    
    with tab7:
        st.header("Demographics & Environmental Intelligence")
        st.markdown("Comprehensive demographic, zoning, and climate analysis for informed scenario planning")
        
        try:
            from modules.navi.demographics_integration import get_demographics_integration
            demographics = get_demographics_integration()
            demographics.render_demographics_dashboard()
        except ImportError:
            st.error("Demographics integration module is loading...")
            st.info("Phase 3 demographics analysis requires all dependencies to be loaded")
            
            # Fallback demo content
            st.markdown("**Demographics Analysis Features:**")
            st.markdown("- Population trends and projections")
            st.markdown("- Zoning capacity and development impact analysis") 
            st.markdown("- Climate risk assessment and adaptation planning")
            st.markdown("- Economic indicators and service demand forecasting")
            st.markdown("- Integrated scenario planning with environmental factors")
        except Exception as e:
            st.error(f"Error loading Demographics Intelligence: {e}")
            st.info("Please refresh the page to retry loading the demographics module")

def render_conversational_whatif_simulator(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render embedded conversational what-if simulator with chat interface
    """
    st.markdown("### Conversational What-If Simulator")
    st.markdown("Ask natural language questions about budget scenarios and get instant visual analysis.")
    
    # Example questions
    with st.expander("Example Questions"):
        st.markdown("""
        - "What if we increase the police budget by 15%?"
        - "Show me what happens if we cut administration by $50,000"
        - "Simulate reallocating money from parks to infrastructure"
        - "Compare increasing fire budget by 10% vs 20%"
        - "What would happen if we reduce all departments by 5%?"
        """)
    
    # Initialize session state for quick questions
    if 'quick_question' not in st.session_state:
        st.session_state.quick_question = ""
    
    # Use the quick question if it was set
    default_value = st.session_state.quick_question if st.session_state.quick_question else ""
    if st.session_state.quick_question:
        st.session_state.quick_question = ""  # Clear it after using
    
    # Chat input
    user_question = st.text_input(
        "Ask a what-if question:",
        placeholder="What if we increase the police budget by 15%?",
        value=default_value,
        key="whatif_question"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        ask_button = st.button("Analyze Scenario", type="primary", use_container_width=True)
    
    # Process the question when button is clicked or Enter is pressed
    if (ask_button or user_question) and user_question.strip():
        with st.spinner("Analyzing scenario..."):
            if process_whatif_question:
                try:
                    # Process the what-if question
                    result = process_whatif_question(user_question, org)
                    
                    if result and result.get('success'):
                        # Display the analysis
                        if result.get('summary'):
                            st.markdown("#### Analysis Results")
                            st.markdown(result['summary'])
                        
                        # Display the chart
                        if result.get('chart'):
                            st.plotly_chart(result['chart'], use_container_width=True, key="whatif_scenario_chart")
                        
                        # Add insights
                        st.markdown("#### Key Insights")
                        scenario_type = result.get('scenario_type', 'general')
                        
                        if 'increase' in user_question.lower():
                            st.info("This scenario shows the impact of budget increases on department allocations and total municipal spending.")
                        elif 'decrease' in user_question.lower() or 'cut' in user_question.lower():
                            st.info("This scenario demonstrates potential cost savings and their effects on service delivery capabilities.")
                        elif 'reallocate' in user_question.lower() or 'move' in user_question.lower():
                            st.info("This reallocation scenario helps visualize shifting priorities between departments while maintaining fiscal balance.")
                        else:
                            st.info("This scenario analysis provides insights into your proposed budget modifications and their municipal impact.")
                            
                    elif result:
                        # Show error message
                        st.error(result.get('message', 'Could not process that scenario question.'))
                        st.markdown("**Try rephrasing your question with more specific details, such as:**")
                        st.markdown("- Specific department names")
                        st.markdown("- Exact amounts or percentages") 
                        st.markdown("- Clear action words (increase, decrease, reallocate)")
                    else:
                        st.error("Scenario analysis is temporarily unavailable. Please try again later.")
                        
                except Exception as e:
                    st.error(f"An error occurred while processing your scenario: {str(e)}")
                    st.info("Please try rephrasing your question or contact support if the issue persists.")
            else:
                st.error("What-if simulator is not available. Please check the system configuration.")
    
    # Quick action buttons for common scenarios
    st.markdown("#### Quick Scenarios")
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    
    with quick_col1:
        if st.button("Increase Police 10%", use_container_width=True):
            st.session_state.quick_question = "What if we increase the police budget by 10%?"
            st.rerun()
    
    with quick_col2:
        if st.button("Cut Admin 15%", use_container_width=True):
            st.session_state.quick_question = "What if we cut the administration budget by 15%?"
            st.rerun()
    
    with quick_col3:
        if st.button("5% Budget Reduction", use_container_width=True):
            st.session_state.quick_question = "What if we reduce all department budgets by 5%?"
            st.rerun()
        
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
                with st.expander("Imported Grants"):
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
        st.subheader("Department Budget Reallocation")
        st.markdown(
            "Departments can contribute unspent budget allocations to help fund the project. "
            "Only funds classified as Unrestricted in the Admin Panel are eligible for "
            "reallocation per GASB Statement No. 54."
        )

        from modules.utils.fund_policy import (
            load_fund_classifications, is_fund_restricted,
            get_eligible_funds_for_reallocation, GASB_54_CATEGORIES
        )

        fund_classifications = load_fund_classifications()

        departments = get_departments()

        if not departments:
            st.warning("No departments found in the database. Using sample data.")
            departments = {
                "Public Works": {"budget": 1200000, "underspent": 300000},
                "Administration": {"budget": 800000, "underspent": 150000}
            }

        excluded_funds_summary = []
        if fund_classifications:
            all_funds = list(fund_classifications.keys())
            _, excluded_info = get_eligible_funds_for_reallocation(all_funds)
            if excluded_info:
                excluded_funds_summary = excluded_info
                with st.expander("Restricted Funds (Excluded from Reallocation)"):
                    for ef in excluded_info:
                        st.markdown(
                            f"**{ef['fund_code']}** - {ef['classification']}: "
                            f"{ef['reason']} ({ef['gasb_reference']})"
                        )

        dept_fund_budgets = {}
        try:
            from modules.database.connection_manager import get_database_connection
            _conn = get_database_connection()
            import pandas as _pd
            dept_fund_df = _pd.read_sql("""
                SELECT Department, Fund,
                       SUM(Budget) as TotalBudget,
                       SUM(Budget) - SUM(Actual) as Underspent
                FROM DepartmentPerformance
                GROUP BY Department, Fund
            """, _conn)
            for _, row in dept_fund_df.iterrows():
                dept = row["Department"]
                fund = row["Fund"]
                if dept not in dept_fund_budgets:
                    dept_fund_budgets[dept] = {}
                dept_fund_budgets[dept][fund] = {
                    "budget": float(row["TotalBudget"]),
                    "underspent": float(row["Underspent"]),
                }
        except Exception:
            pass

        total_reallocation = 0
        reallocated_amounts = {}

        with st.expander("Department Allocations"):
            for dept, data in departments.items():
                eligible_budget = 0.0
                eligible_underspent = 0.0
                restricted_amount = 0.0

                if dept in dept_fund_budgets:
                    for fund_name, fund_data in dept_fund_budgets[dept].items():
                        if not is_fund_restricted(fund_name):
                            eligible_budget += fund_data["budget"]
                            eligible_underspent += max(0, fund_data["underspent"])
                        else:
                            restricted_amount += fund_data["budget"]
                else:
                    eligible_budget = data.get("budget", 0)
                    eligible_underspent = data.get("underspent", 0)

                if eligible_budget <= 0:
                    st.markdown(
                        f"**{dept}** - All funds are restricted. "
                        f"Not eligible for reallocation."
                    )
                    continue

                is_default = dept in list(departments.keys())[:2]
                include = st.checkbox(f"{dept}", value=is_default, key=f"check_{dept}")

                if include:
                    max_allowable = min(eligible_budget * 0.10, eligible_underspent)
                    max_allowable = max(1000, max_allowable)
                    max_allowable = round(max_allowable, 2)

                    saved_key = f"dept_allocation_{dept}"
                    if saved_key not in st.session_state:
                        st.session_state[saved_key] = float(max_allowable / 2)

                    st.markdown("""
                    <style>
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

                    reallocation = st.number_input(
                        f"{dept} Reallocation - Exact Amount ($)",
                        min_value=0.0,
                        max_value=float(max_allowable),
                        value=st.session_state[saved_key],
                        step=0.01,
                        format="%.2f",
                        key=f"number_{dept}",
                        help=f"Enter amount between $0 and ${max_allowable:,.2f} (unrestricted funds only)"
                    )

                    st.session_state[saved_key] = reallocation

                    total_reallocation += round(reallocation, 2)
                    reallocated_amounts[dept] = round(reallocation, 2)

                    if restricted_amount > 0:
                        st.markdown(
                            f'<div class="department-data">'
                            f'Eligible Budget: ${eligible_budget:,.2f} | '
                            f'Underspent: ${eligible_underspent:,.2f} | '
                            f'Max: ${max_allowable:,.2f} | '
                            f'Restricted (excluded): ${restricted_amount:,.2f}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="department-data">'
                            f'Budget: ${eligible_budget:,.2f} | '
                            f'Underspent: ${eligible_underspent:,.2f} | '
                            f'Max: ${max_allowable:,.2f}'
                            f'</div>',
                            unsafe_allow_html=True
                        )

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
        from modules.utils.accessibility_helper import create_accessible_chart
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
        
        # Redirect to Monte Carlo Simulator tab
        st.markdown("---")
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
                    # Prepare data structure for save_scenario function
                    scenario_data = {
                        "name": scenario_name,
                        "project_id": project_id,
                        "total_amount": project_cost,
                        "tax_revenue": tax_revenue,
                        "grant": grant,
                        "private_investment": private_investment,
                        "bonds_needed": bonds_needed
                    }
                    
                    # Prepare department allocations dictionary
                    department_allocations = reallocated_amounts if reallocated_amounts else {}
                    
                    scenario_id = save_scenario(scenario_data, department_allocations)
                    
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
    Render the Legislative Impact Analyzer tab with bill lookup capability.
    Connects to Congress.gov API for federal bills and scrapes state legislature
    websites for state bills. Uses AI to project financial impact on municipal budgets.
    """
    st.header("Legislative Impact Analyzer")
    st.markdown("""
    Look up specific bills from federal and state legislatures by bill number.
    The system fetches bill details and uses AI to analyze projected financial impact on your municipality.
    """)
    
    leg_tab1, leg_tab2, leg_tab3 = st.tabs([
        "Bill Lookup & Impact Analysis",
        "Keyword Search",
        "Analysis History"
    ])
    
    with leg_tab1:
        _render_bill_lookup_tab()
    
    with leg_tab2:
        _render_keyword_search_tab()
    
    with leg_tab3:
        _render_analysis_history_tab()


def _render_bill_lookup_tab():
    """Bill number lookup and financial impact analysis"""
    
    st.subheader("Look Up a Bill")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        bill_level = st.radio(
            "Legislative Level",
            options=["Federal", "State"],
            horizontal=True,
            key="bill_level_radio"
        )
    
    with col2:
        if bill_level == "State":
            from modules.scenario_planner.bill_lookup_service import US_STATES
            state_names = sorted(US_STATES.keys())
            selected_state = st.selectbox(
                "Select State",
                options=state_names,
                key="state_select_leg"
            )
    
    st.markdown("---")
    
    col_input1, col_input2 = st.columns([2, 1])
    
    with col_input1:
        if bill_level == "Federal":
            bill_input = st.text_input(
                "Enter Bill Number",
                placeholder="e.g., HR 1234, S 567, HJRES 100",
                help="Enter a federal bill number. Examples: HR 1234 (House), S 567 (Senate), HJRES 100 (Joint Resolution)",
                key="fed_bill_input"
            )
        else:
            bill_input = st.text_input(
                "Enter State Bill Number",
                placeholder="e.g., HB 100, SB 200",
                help="Enter a state bill number. Use HB for House Bills, SB for Senate Bills.",
                key="state_bill_input"
            )
    
    with col_input2:
        if bill_level == "Federal":
            congress_options = {
                "Current (119th)": 119,
                "118th (2023-2024)": 118,
                "117th (2021-2022)": 117,
                "116th (2019-2020)": 116
            }
            congress_label = st.selectbox(
                "Congress",
                options=list(congress_options.keys()),
                key="congress_select"
            )
            selected_congress = congress_options[congress_label]
    
    annual_budget = st.number_input(
        "Your Municipality's Annual Budget (for impact projection)",
        min_value=100000,
        max_value=10000000000,
        value=5000000,
        step=100000,
        format="%d",
        key="muni_budget_input"
    )
    
    if st.button("Look Up Bill & Analyze Impact", type="primary", use_container_width=True, key="lookup_bill_btn"):
        if not bill_input or not bill_input.strip():
            st.warning("Please enter a bill number to look up.")
            return
        
        with st.spinner("Looking up bill details..."):
            from modules.scenario_planner.bill_lookup_service import (
                parse_bill_number, lookup_federal_bill, lookup_state_bill,
                get_bill_financial_keywords, US_STATES
            )
            
            bill_type, bill_number, bill_congress = parse_bill_number(bill_input)
            
            if bill_level == "Federal":
                congress = bill_congress if bill_congress else selected_congress
                bill_data = lookup_federal_bill(bill_type, bill_number, congress)
            else:
                state_code = US_STATES.get(selected_state, "")
                bill_data = lookup_state_bill(state_code, bill_type, bill_number)
            
            st.session_state['last_bill_lookup'] = bill_data
        
        if bill_data.get("found"):
            _display_bill_details(bill_data)
            
            with st.spinner("Analyzing financial impact on your municipality..."):
                financial_keywords = get_bill_financial_keywords(bill_data)
                impact_analysis = _analyze_bill_financial_impact(
                    bill_data, annual_budget, financial_keywords
                )
                st.session_state['last_impact_analysis'] = impact_analysis
            
            _display_impact_analysis(impact_analysis, annual_budget)
            
            if 'legislation_history' not in st.session_state:
                st.session_state['legislation_history'] = []
            st.session_state['legislation_history'].append({
                "bill": f"{bill_data.get('bill_type', '').upper()} {bill_data.get('bill_number', '')}",
                "title": bill_data.get("title", "")[:100],
                "level": bill_level,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "impact_areas": financial_keywords[:3]
            })
            
        else:
            st.error(bill_data.get("error", "Bill not found"))
            if bill_data.get("suggestion"):
                st.info(bill_data["suggestion"])
            if bill_data.get("congress_url") or bill_data.get("legislature_url"):
                url = bill_data.get("congress_url") or bill_data.get("legislature_url")
                st.markdown(f"[Search directly on the legislature website]({url})")


def _display_bill_details(bill_data: Dict[str, Any]):
    """Display fetched bill details in a structured format"""
    
    st.markdown("---")
    st.subheader("Bill Details")
    
    source_label = "Federal" if bill_data.get("source") == "federal" else bill_data.get("state_name", "State")
    bill_id = f"{bill_data.get('bill_type', '').upper()} {bill_data.get('bill_number', '')}"
    
    if bill_data.get("source") == "federal":
        congress = bill_data.get("congress", "")
        st.markdown(f"**{bill_id}** - {congress}th Congress ({source_label})")
    else:
        st.markdown(f"**{bill_id}** - {source_label}")
    
    if bill_data.get("title"):
        st.markdown(f"### {bill_data['title']}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if bill_data.get("introduced_date"):
            st.metric("Introduced", bill_data["introduced_date"])
        if bill_data.get("policy_area"):
            st.metric("Policy Area", bill_data["policy_area"])
    
    with col2:
        if bill_data.get("status"):
            st.metric("Latest Action", bill_data["status"][:60])
        if bill_data.get("status_date"):
            st.metric("Action Date", bill_data["status_date"])
    
    with col3:
        if bill_data.get("cosponsors_count"):
            st.metric("Cosponsors", bill_data["cosponsors_count"])
        if bill_data.get("committees"):
            st.metric("Committees", bill_data["committees"])
    
    if bill_data.get("sponsors"):
        sponsors_text = ", ".join([
            f"{s.get('name', '')} ({s.get('party', '')}-{s.get('state', '')})"
            for s in bill_data["sponsors"]
        ])
        st.markdown(f"**Sponsors:** {sponsors_text}")
    
    if bill_data.get("cbo_estimates"):
        with st.expander("CBO Cost Estimates"):
            for est in bill_data["cbo_estimates"]:
                desc = est.get("description", "").strip()
                url_cbo = est.get("url", "")
                if desc:
                    st.markdown(f"- {desc}")
                if url_cbo:
                    st.markdown(f"  [View CBO Report]({url_cbo})")
    
    if bill_data.get("summary"):
        with st.expander("Bill Summary", expanded=True):
            st.markdown(bill_data["summary"][:2000])
    
    url = bill_data.get("congress_url") or bill_data.get("legislature_url")
    if url:
        st.markdown(f"[View Full Bill Text]({url})")


def _analyze_bill_financial_impact(
    bill_data: Dict[str, Any],
    annual_budget: int,
    financial_keywords: list
) -> Dict[str, Any]:
    """Use AI to analyze the financial impact of a bill on the municipality"""
    
    bill_id = f"{bill_data.get('bill_type', '').upper()} {bill_data.get('bill_number', '')}"
    title = bill_data.get("title", "Unknown")
    summary = bill_data.get("summary", bill_data.get("raw_text", "No summary available"))[:2500]
    status = bill_data.get("status", "Unknown")
    policy_area = bill_data.get("policy_area", "General")
    source = "Federal" if bill_data.get("source") == "federal" else bill_data.get("state_name", "State")
    
    prompt = f"""You are a municipal financial analyst. Analyze the following {source} legislation 
and project its financial impact on a municipality with an annual budget of ${annual_budget:,.0f}.

BILL: {bill_id}
TITLE: {title}
STATUS: {status}
POLICY AREA: {policy_area}
IDENTIFIED IMPACT AREAS: {', '.join(financial_keywords)}

BILL SUMMARY/TEXT:
{summary}

Provide a structured analysis with the following sections:

1. EXECUTIVE SUMMARY (2-3 sentences on what this bill does and why it matters to municipalities)

2. FINANCIAL IMPACT PROJECTION
   - Estimated annual cost or savings to the municipality (provide dollar ranges)
   - One-time implementation costs if applicable
   - Revenue impact (positive or negative)
   - Percentage of annual budget affected

3. AFFECTED DEPARTMENTS
   - List specific municipal departments that would be impacted
   - For each department, estimate the budget impact (increase/decrease percentage)

4. IMPLEMENTATION TIMELINE
   - When would costs/changes take effect
   - Phased implementation considerations

5. COMPLIANCE REQUIREMENTS
   - New reporting or documentation requirements
   - Staffing needs
   - Technology or infrastructure changes needed

6. RISK ASSESSMENT
   - Probability of passage (based on current status)
   - Financial risk level (Low/Medium/High/Critical)
   - Unfunded mandate concerns

7. RECOMMENDED ACTIONS
   - Immediate steps the municipality should take
   - Budget planning recommendations
   - Advocacy or coalition opportunities

Be specific with dollar estimates relative to the ${annual_budget:,.0f} budget. 
Use percentage ranges when exact figures are uncertain.
Focus on practical, actionable insights for municipal budget planners."""

    try:
        analysis = ask_ai(
            prompt=prompt,
            sources=[
                f"Legislative analysis: {bill_id}",
                "Municipal budget impact assessment",
                "Government finance best practices",
                f"Policy area: {policy_area}"
            ],
            max_tokens=1500
        )
    except Exception as e:
        analysis = f"AI analysis temporarily unavailable: {str(e)}\n\nPlease review the bill details above and consult with your finance team for impact assessment."
    
    return {
        "bill_id": bill_id,
        "title": title,
        "source": source,
        "annual_budget": annual_budget,
        "financial_keywords": financial_keywords,
        "analysis": analysis,
        "generated_at": datetime.now().isoformat()
    }


def _display_impact_analysis(impact: Dict[str, Any], annual_budget: int):
    """Display the AI-generated financial impact analysis"""
    
    st.markdown("---")
    st.subheader("Financial Impact Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Bill", impact["bill_id"])
    with col2:
        st.metric("Your Annual Budget", f"${annual_budget:,.0f}")
    with col3:
        areas = impact.get("financial_keywords", [])
        st.metric("Impact Areas Identified", len(areas))
    
    if impact.get("financial_keywords"):
        st.markdown("**Key Financial Impact Areas:**")
        keyword_cols = st.columns(min(len(impact["financial_keywords"]), 4))
        for i, kw in enumerate(impact["financial_keywords"][:4]):
            with keyword_cols[i]:
                st.info(kw)
    
    st.markdown("### Detailed Analysis")
    st.markdown(impact.get("analysis", "Analysis not available"))
    
    st.markdown("---")
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        report_text = f"""Legislative Impact Analysis Report
Generated: {impact.get('generated_at', '')}
Bill: {impact.get('bill_id', '')}
Title: {impact.get('title', '')}
Level: {impact.get('source', '')}
Municipality Annual Budget: ${annual_budget:,.0f}
Impact Areas: {', '.join(impact.get('financial_keywords', []))}

{'='*60}

{impact.get('analysis', '')}
"""
        st.download_button(
            "Download Analysis Report",
            data=report_text,
            file_name=f"legislative_impact_{impact.get('bill_id', 'report').replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="download_impact_txt"
        )
    
    with col_dl2:
        try:
            from fpdf import FPDF
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, "Legislative Impact Analysis", ln=True, align="C")
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 6, f"Generated: {impact.get('generated_at', '')[:16]}", ln=True)
            pdf.cell(200, 6, f"Bill: {impact.get('bill_id', '')}", ln=True)
            pdf.cell(200, 6, f"Title: {impact.get('title', '')[:80]}", ln=True)
            pdf.cell(200, 6, f"Budget: ${annual_budget:,.0f}", ln=True)
            pdf.ln(5)
            
            analysis_clean = impact.get('analysis', '').encode('ascii', 'ignore').decode('ascii')
            pdf.set_font("Arial", size=9)
            pdf.multi_cell(0, 4, analysis_clean)
            
            pdf_bytes = pdf.output(dest='S')
            st.download_button(
                "Download as PDF",
                data=pdf_bytes,
                file_name=f"legislative_impact_{impact.get('bill_id', 'report').replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="download_impact_pdf"
            )
        except ImportError:
            st.caption("PDF export requires fpdf2 package")


def _render_keyword_search_tab():
    """Search for bills by keyword"""
    st.subheader("Search Bills by Keyword")
    st.markdown("Find bills related to specific topics that may affect your municipality.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_keyword = st.text_input(
            "Search Keywords",
            placeholder="e.g., infrastructure funding, minimum wage, water quality",
            key="bill_search_keyword"
        )
    
    with col2:
        search_level = st.radio(
            "Search Level",
            options=["Federal", "State"],
            horizontal=True,
            key="search_level_radio"
        )
        
        if search_level == "State":
            from modules.scenario_planner.bill_lookup_service import US_STATES
            state_names = sorted(US_STATES.keys())
            search_state = st.selectbox(
                "State",
                options=state_names,
                key="search_state_select"
            )
    
    if st.button("Search Bills", type="primary", key="search_bills_btn"):
        if not search_keyword or not search_keyword.strip():
            st.warning("Enter a keyword to search.")
            return
        
        with st.spinner("Searching legislative databases..."):
            from modules.scenario_planner.bill_lookup_service import search_bills_by_keyword, US_STATES
            
            state_code = None
            if search_level == "State":
                state_code = US_STATES.get(search_state, "")
            
            results = search_bills_by_keyword(
                keyword=search_keyword,
                level=search_level.lower(),
                state_code=state_code
            )
        
        if results.get("found"):
            if results.get("bills"):
                st.success(f"Found {len(results['bills'])} bills matching '{search_keyword}'")
                
                for bill in results["bills"]:
                    with st.expander(f"{bill.get('bill_type', '').upper()} {bill.get('bill_number', '')} - {bill.get('title', '')[:80]}"):
                        st.write(f"**Congress:** {bill.get('congress', '')}")
                        st.write(f"**Introduced:** {bill.get('introduced', '')}")
                        st.write(f"**Status:** {bill.get('status', '')}")
                        st.caption("Use the Bill Lookup tab to get full details and financial impact analysis")
            
            elif results.get("search_results_text"):
                st.success(f"Search results for '{search_keyword}'")
                st.markdown(results["search_results_text"][:3000])
                if results.get("search_url"):
                    st.markdown(f"[View full results]({results['search_url']})")
        else:
            st.info(f"No bills found matching '{search_keyword}'. Try different keywords.")
            if results.get("error"):
                st.caption(f"Note: {results['error']}")


def _render_analysis_history_tab():
    """Show history of bill lookups and analyses"""
    st.subheader("Analysis History")
    
    history = st.session_state.get('legislation_history', [])
    
    if history:
        st.markdown(f"**{len(history)} bills analyzed this session**")
        
        history_data = []
        for entry in reversed(history):
            history_data.append({
                "Bill": entry.get("bill", ""),
                "Title": entry.get("title", ""),
                "Level": entry.get("level", ""),
                "Analyzed": entry.get("timestamp", ""),
                "Impact Areas": ", ".join(entry.get("impact_areas", []))
            })
        
        st.dataframe(pd.DataFrame(history_data), use_container_width=True, key="history_df")
        
        if st.button("Clear History", key="clear_leg_history"):
            st.session_state['legislation_history'] = []
            st.rerun()
    else:
        st.info("No bills analyzed yet. Use the Bill Lookup tab to analyze legislation.")

def render_whatif_simulator():
    """
    Render a simplified What-If Scenario Simulator with enhanced UI/UX
    """
    # Import UI helpers
    from modules.utils.ui_helpers import (
        apply_custom_styling,
        show_spinner,
        show_error_with_guidance,
        show_info_banner,
        create_responsive_columns,
        handle_database_error,
        create_scrollable_dataframe
    )
    
    # Apply consistent styling
    apply_custom_styling()
    
    st.header("What-If Budget Simulator")
    
    # Info banner for guidance
    show_info_banner(
        "Budget Impact Testing",
        "Test different budget scenarios and see their immediate financial impact. This tool helps you understand the consequences of budget decisions before implementation.",
        "🔮"
    )
    
    # Load data for simulation with better error handling
    with show_spinner("Loading budget data...", show_progress=True) as progress:
        try:
            if progress:
                progress.update(0.3)
            
            db_path = get_db_path_for_org("cityA")
            conn = sqlite3.connect(db_path)
            
            if progress:
                progress.update(0.6)
            
            df = pd.read_sql_query("""
                SELECT Department, 
                       SUM(Budget) as Budget, 
                       SUM(Actual) as Actual
                FROM DepartmentPerformance
                WHERE Budget > 0
                GROUP BY Department
            """, conn)
            conn.close()
            
            if progress:
                progress.update(0.9)
            
            # Calculate derived fields
            df['Remaining'] = df['Budget'] - df['Actual']
            df['PercentSpent'] = ((df['Actual'] / df['Budget']) * 100).round(1)
            
            if progress:
                progress.update(1.0)
            
        except sqlite3.DatabaseError as e:
            handle_database_error(e)
            return
        except Exception as e:
            show_error_with_guidance(
                f"Cannot load budget data: {str(e)}",
                recovery_steps=[
                    "Check your network connection",
                    "Verify database server is running",
                    "Ensure you have permission to access budget data",
                    "Try refreshing the page"
                ]
            )
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
    with st.expander("Step 1: Select Data"):
        st.subheader("Select Department Data")
        
        # Load financial data for departments with loading indicator
        with st.spinner("Loading department data..."):
            df = load_scenario_data_optimized()
            
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
        temp_df = load_scenario_data_optimized()
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
    Enhanced with real API integration for federal and state grants
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.header("Grant Integration")
    st.markdown(f"""
    ## 🌐 Live Grant Search for {org_display_name}
    
    Search real-time federal and state grant databases to find opportunities for your {org_display_name} funding scenarios.
    Connect to live APIs including Grants.gov, USASpending.gov, and state grant portals.
    """)
    
    # Use the real grant finder with API integration
    try:
        from .grant_finder import render_grant_finder
        st.info("🔍 Searching live grant databases including Grants.gov, USASpending.gov, and state portals")
        render_grant_finder()
    except ImportError as e:
        st.error(f"Grant finder module not available: {e}")
        
        # NO FALLBACK DATA - Meeting user's strict requirement for only real grants
        st.error("⚠️ **Grant search functionality is temporarily unavailable**")
        st.info("💡 **Alternative Grant Resources:**")
        st.markdown("""
        - **Federal Grants**: Visit [Grants.gov](https://www.grants.gov) to search current opportunities
        - **Municipal Funding**: Contact your state's municipal finance office
        - **Federal Agencies**: Check department websites for direct funding programs
        - **Grant Consultants**: Consider professional grant writing services
        """)
        
        st.warning("**Note**: We only provide verified, current grant opportunities with working URLs. "
                  "Static or placeholder grant information is not displayed to ensure authenticity.")
    
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
                    # Removed st.rerun() to prevent navigation reset
        
        # Clear all button
        if st.button("Clear All Selected Grants"):
            st.session_state.selected_grants = []
            # Removed st.rerun() to prevent navigation reset
        
        st.info("Tip: Go to the 'Scenario Builder' tab to incorporate these grants into your funding scenarios.")


def create_scenario(name: str, total_cost: float, funding_sources: dict) -> dict:
    """Create a new scenario"""
    return {
        'name': name,
        'total_cost': total_cost,
        **funding_sources
    }

def validate_scenario(scenario: dict) -> bool:
    """Validate scenario data"""
    required_fields = ['name', 'total_cost']
    
    for field in required_fields:
        if field not in scenario:
            return False
    
    # Validate positive costs
    if scenario.get('total_cost', 0) <= 0:
        return False
    
    return True

def load_scenarios() -> list:
    """Load all scenarios from database"""
    import sqlite3
    import json
    
    try:
        conn = sqlite3.connect('databases/scenarios.db')
        cursor = conn.cursor()
        
        # Ensure table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                project_type TEXT,
                total_cost REAL,
                funding_sources TEXT,
                revenue_assumptions TEXT,
                cost_assumptions TEXT,
                monte_carlo_results TEXT,
                created_by TEXT,
                created_date TIMESTAMP,
                last_modified TIMESTAMP,
                status TEXT,
                description TEXT,
                metadata TEXT
            )
        ''')
        
        # Load all scenarios
        cursor.execute('''
            SELECT id, name, project_type, total_cost, funding_sources,
                   revenue_assumptions, cost_assumptions, monte_carlo_results,
                   created_by, created_date, last_modified, status,
                   description, metadata
            FROM scenarios
            ORDER BY last_modified DESC
        ''')
        
        rows = cursor.fetchall()
        scenarios = []
        
        for row in rows:
            scenario = {
                'id': row[0],
                'name': row[1],
                'project_type': row[2],
                'total_cost': row[3],
                'funding_sources': json.loads(row[4]) if row[4] else {},
                'revenue_assumptions': json.loads(row[5]) if row[5] else {},
                'cost_assumptions': json.loads(row[6]) if row[6] else {},
                'monte_carlo_results': json.loads(row[7]) if row[7] else {},
                'created_by': row[8],
                'created_date': row[9],
                'last_modified': row[10],
                'status': row[11],
                'description': row[12],
                'metadata': json.loads(row[13]) if row[13] else {}
            }
            scenarios.append(scenario)
        
        conn.close()
        return scenarios
        
    except Exception as e:
        print(f"Error loading scenarios from database: {e}")
        return []

def save_scenario(scenario: dict) -> bool:
    """Save scenario to database with proper persistence"""
    import sqlite3
    import json
    from datetime import datetime
    
    if not validate_scenario(scenario):
        return False
    
    try:
        # Connect to the scenarios database
        conn = sqlite3.connect('databases/scenarios.db')
        cursor = conn.cursor()
        
        # Create scenarios table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                project_type TEXT,
                total_cost REAL,
                funding_sources TEXT,
                revenue_assumptions TEXT,
                cost_assumptions TEXT,
                monte_carlo_results TEXT,
                created_by TEXT,
                created_date TIMESTAMP,
                last_modified TIMESTAMP,
                status TEXT,
                description TEXT,
                metadata TEXT
            )
        ''')
        
        # Prepare data for insertion
        scenario_data = {
            'name': scenario.get('name', f"Scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            'project_type': scenario.get('project_type', 'General'),
            'total_cost': scenario.get('total_cost', 0),
            'funding_sources': json.dumps(scenario.get('funding_sources', {})),
            'revenue_assumptions': json.dumps(scenario.get('revenue_assumptions', {})),
            'cost_assumptions': json.dumps(scenario.get('cost_assumptions', {})),
            'monte_carlo_results': json.dumps(scenario.get('monte_carlo_results', {})),
            'created_by': scenario.get('created_by', 'System'),
            'created_date': datetime.now(),
            'last_modified': datetime.now(),
            'status': scenario.get('status', 'Draft'),
            'description': scenario.get('description', ''),
            'metadata': json.dumps(scenario.get('metadata', {}))
        }
        
        # Insert scenario into database
        cursor.execute('''
            INSERT INTO scenarios (
                name, project_type, total_cost, funding_sources,
                revenue_assumptions, cost_assumptions, monte_carlo_results,
                created_by, created_date, last_modified, status,
                description, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scenario_data['name'],
            scenario_data['project_type'],
            scenario_data['total_cost'],
            scenario_data['funding_sources'],
            scenario_data['revenue_assumptions'],
            scenario_data['cost_assumptions'],
            scenario_data['monte_carlo_results'],
            scenario_data['created_by'],
            scenario_data['created_date'],
            scenario_data['last_modified'],
            scenario_data['status'],
            scenario_data['description'],
            scenario_data['metadata']
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error saving scenario to database: {e}")
        return False
