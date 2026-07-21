"""
Legislative Impact Analyzer - Assess regulatory impact on scenarios
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from io import BytesIO
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

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.ai_hub.ai_hub import ask_ai
from modules.database.db_connection import load_org_data
from modules.utils.organization_service import get_current_org_config, get_current_state_config

def render_legislative_analyzer():
    """Legislative impact analysis interface"""
    st.subheader("Legislative Impact Analyzer")
    
    # Get current organization configuration
    org_config = get_current_org_config()
    state_config = get_current_state_config()
    
    st.markdown(f"""
    Analyze how current and proposed legislation might impact your budget scenarios for **{org_config.name}, {org_config.state}**.
    This tool uses AI to assess regulatory compliance and financial implications specific to {state_config.get('legislative_session', 'current legislative session')}.
    """)
    
    # Get organization data
    org = st.session_state.get('selected_org', 'cityA')
    df = load_org_data(org)
    
    if df.empty:
        st.warning("No budget data available for analysis")
        return
    
    # Regulation category selection
    st.markdown("#### Step 1: Select Regulation Category")
    
    regulation_categories = [
        "Environmental Regulations",
        "Public Safety Requirements", 
        "Healthcare Mandates",
        "Education Standards",
        "Infrastructure Requirements",
        "Labor and Employment Laws",
        "Financial Reporting Standards",
        "Data Privacy and Security",
        "Accessibility Compliance",
        "Custom/Other"
    ]
    
    regulation_category = st.selectbox(
        "Choose the type of regulation to analyze",
        options=regulation_categories,
        key="reg_category"
    )
    
    if regulation_category == "Custom/Other":
        custom_category = st.text_input(
            "Specify the regulation category",
            key="custom_reg_category"
        )
        if custom_category:
            regulation_category = custom_category
    
    # Department focus
    st.markdown("#### Step 2: Department Focus")
    
    departments = df['Department'].unique().tolist()
    selected_departments = st.multiselect(
        "Select departments to analyze (leave empty for all)",
        options=departments,
        key="leg_departments"
    )
    
    if not selected_departments:
        selected_departments = departments
    
    # Analysis parameters
    st.markdown("#### Step 3: Analysis Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        time_horizon = st.selectbox(
            "Analysis Time Horizon",
            options=["Current Year", "1-2 Years", "3-5 Years", "5+ Years"],
            key="time_horizon"
        )
    
    with col2:
        impact_severity = st.selectbox(
            "Expected Impact Severity",
            options=["Low", "Moderate", "High", "Critical"],
            key="impact_severity"
        )
    
    # Custom legislative text input
    st.markdown("#### Step 4: Legislative Context")
    
    legislative_text = st.text_area(
        "Paste relevant legislative text or describe the regulation (optional)",
        height=150,
        placeholder="Enter bill text, regulation summary, or compliance requirements...",
        key="legislative_text"
    )
    
    # Analysis execution
    if st.button("Analyze Legislative Impact", type="primary"):
        with st.spinner("Analyzing legislative impact..."):
            analysis_results = perform_legislative_analysis(
                df, 
                selected_departments,
                regulation_category,
                time_horizon,
                impact_severity,
                legislative_text
            )
            
            display_legislative_analysis(analysis_results)

def perform_legislative_analysis(
    df: pd.DataFrame,
    departments: List[str],
    regulation_category: str,
    time_horizon: str,
    impact_severity: str,
    legislative_text: str = ""
) -> Dict[str, Any]:
    """Perform AI-powered legislative impact analysis"""
    
    # Filter data for selected departments
    dept_data = df[df['Department'].isin(departments)]
    
    # Calculate department budget totals
    dept_budgets = dept_data.groupby('Department')['Budget'].sum().to_dict()
    total_affected_budget = sum(dept_budgets.values())
    
    # Build analysis prompt
    prompt = f"""
    As a government budget analyst, analyze the potential impact of {regulation_category} 
    on the following municipal budget data:
    
    Affected Departments and Budgets:
    {chr(10).join([f"- {dept}: ${budget:,.2f}" for dept, budget in dept_budgets.items()])}
    
    Total Affected Budget: ${total_affected_budget:,.2f}
    
    Analysis Parameters:
    - Time Horizon: {time_horizon}
    - Expected Impact Severity: {impact_severity}
    
    {f"Legislative Context: {legislative_text}" if legislative_text else ""}
    
    Please provide:
    1. Compliance cost estimates for each department
    2. Implementation timeline and milestones
    3. Risk assessment and mitigation strategies
    4. Recommended budget adjustments
    5. Long-term financial implications
    
    Focus on actionable insights for municipal budget planning.
    """
    
    # Get AI analysis
    try:
        analysis = ask_ai(
            prompt,
            df=dept_data,
            sources=[f"{regulation_category} regulations", "Municipal budget compliance"],
            max_tokens=1000
        )
    except Exception as e:
        analysis = f"Analysis unavailable: {str(e)}"
    
    return {
        'regulation_category': regulation_category,
        'departments': departments,
        'dept_budgets': dept_budgets,
        'total_affected_budget': total_affected_budget,
        'time_horizon': time_horizon,
        'impact_severity': impact_severity,
        'legislative_text': legislative_text,
        'analysis': analysis,
        'generated_at': datetime.now()
    }

def display_legislative_analysis(results: Dict[str, Any]):
    """Display legislative analysis results"""
    st.markdown("### Legislative Impact Analysis Results")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Regulation Category",
            results['regulation_category']
        )
    
    with col2:
        st.metric(
            "Departments Affected",
            len(results['departments'])
        )
    
    with col3:
        st.metric(
            "Total Budget at Risk",
            f"${results['total_affected_budget']:,.0f}"
        )
    
    # Department breakdown
    st.markdown("#### Affected Department Budgets")
    
    dept_breakdown = pd.DataFrame([
        {
            'Department': dept,
            'Current Budget': f"${budget:,.2f}",
            'Risk Level': results['impact_severity']
        }
        for dept, budget in results['dept_budgets'].items()
    ])
    
    st.dataframe(dept_breakdown, use_container_width=True)
    
    # AI Analysis
    st.markdown("#### Legislative Impact Analysis")
    st.markdown(results['analysis'])
    
    # Recommendations
    create_legislative_recommendations(results)
    
    # Export option
    create_legislative_report_download(results)

def create_legislative_recommendations(results: Dict[str, Any]):
    """Create actionable recommendations"""
    st.markdown("#### Recommended Actions")
    
    # Basic recommendations based on impact severity
    recommendations = []
    
    if results['impact_severity'] == "Critical":
        recommendations.extend([
            "Immediate budget reallocation required",
            "Establish compliance task force",
            "Seek emergency funding sources",
            "Accelerate implementation timeline"
        ])
    elif results['impact_severity'] == "High":
        recommendations.extend([
            "Conduct detailed cost-benefit analysis",
            "Engage with regulatory agencies",
            "Consider phased implementation",
            "Monitor for funding opportunities"
        ])
    elif results['impact_severity'] == "Moderate":
        recommendations.extend([
            "Include in next budget cycle",
            "Monitor regulatory developments",
            "Update compliance procedures",
            "Explore efficiency improvements"
        ])
    else:  # Low
        recommendations.extend([
            "Plan for future budget cycles",
            "Stay informed on regulatory changes",
            "Review periodically",
            "Consider as contingency"
        ])
    
    for rec in recommendations:
        st.markdown(f"- {rec}")

def create_legislative_report_download(results: Dict[str, Any]):
    """Create downloadable legislative impact report"""
    st.markdown("#### Download Report")
    
    if st.button("Generate PDF Report"):
        pdf_bytes = generate_legislative_pdf_report(results)
        
        st.download_button(
            label="Download Legislative Impact Report",
            data=pdf_bytes,
            file_name=f"legislative_impact_{results['regulation_category'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )

def generate_legislative_pdf_report(results: Dict[str, Any]) -> bytes:
    """Generate PDF report for legislative analysis"""
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Legislative Impact Analysis Report", ln=True, align="C")
    
    # Metadata
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Generated: {results['generated_at'].strftime('%m/%d/%Y %H:%M')}", ln=True)
    pdf.cell(200, 10, f"Regulation Category: {results['regulation_category']}", ln=True)
    pdf.cell(200, 10, f"Impact Severity: {results['impact_severity']}", ln=True)
    pdf.ln(5)
    
    # Department budgets
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Affected Departments:", ln=True)
    pdf.set_font("Arial", size=10)
    
    for dept, budget in results['dept_budgets'].items():
        pdf.cell(200, 6, f"• {dept}: ${budget:,.2f}", ln=True)
    
    pdf.ln(5)
    
    # Analysis
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Analysis:", ln=True)
    pdf.set_font("Arial", size=10)
    
    # Clean analysis text for PDF
    analysis_clean = results['analysis'].encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 5, analysis_clean)
    
    return pdf.output(dest='S').encode('utf-8', errors='replace')