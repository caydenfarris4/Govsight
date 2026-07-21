"""
Summary Report Generator Module

This module handles the generation of PDF reports with AI-powered analysis including:
- Budget narrative generation using OpenAI
- PDF report creation with data summaries
- Visualization embedding in reports
- Scenario comparisons with detailed analysis
- Enhanced scenario reports with funding breakdowns
"""

import streamlit as st
import pandas as pd
import openai
from fpdf import FPDF
from io import BytesIO
import plotly.express as px
import matplotlib.pyplot as plt
import security_manager as sec
from db_connection import check_password
import tempfile
import admin_archive_manager as archive
from datetime import datetime

# AI API Key Setup - Use from environment or secrets
import os
# Check first in environment variables, then try st.secrets if available
try:
    # Get the API key from environment or secrets
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key and hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    
    # For initialization only - used to check if key is present in the functions
    openai.api_key = api_key
except Exception:
    # Set a placeholder key for initialization (will show a warning later)
    openai.api_key = "sk-placeholder"

# --- AI Narrative Helper ---
def generate_ai_narrative(dataframe, prompt_extra=""):
    """
    Generate an AI-powered narrative based on financial data
    
    Args:
        dataframe (DataFrame): The financial data to analyze
        prompt_extra (str): Additional context for the prompt
        
    Returns:
        str: The generated narrative
    """
    try:
        # Check if a valid OpenAI API key is available
        if not openai.api_key or openai.api_key == "sk-placeholder":
            st.warning("OpenAI API key not configured. Using default analysis instead.")
            return generate_fallback_narrative(dataframe)
        
        # Create a client instance
        client = openai.OpenAI(api_key=openai.api_key)
        
        sample = dataframe.head(10).to_csv(index=False)
        prompt = f"Based on the following financial data, write a professional budget analysis summary. Focus on trends, over/underspending, and notable changes. {prompt_extra}\n\n{sample}"
        
        try:
            # Use the new API format
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # Use gpt-3.5-turbo which has higher quotas
                messages=[
                    {"role": "system", "content": "You are a government finance officer assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as api_error:
            # If the API call fails (e.g., quota exceeded), use fallback
            st.warning(f"OpenAI API Error: {str(api_error)}")
            return generate_fallback_narrative(dataframe)
            
    except Exception as e:
        st.error(f"AI summary generation failed: {e}")
        return generate_fallback_narrative(dataframe)

def generate_fallback_narrative(df):
    """
    Generate a simple narrative based on financial data without using AI
    
    Args:
        df (DataFrame): The financial data to analyze
        
    Returns:
        str: A simple narrative
    """
    # Basic stats
    narrative = "## Financial Data Analysis\n\n"
    
    try:
        # Check if this is budget data
        if "Budget" in df.columns and "Actual" in df.columns:
            total_budget = df["Budget"].sum()
            total_actual = df["Actual"].sum()
            
            # Basic variance calculation
            variance = total_actual - total_budget
            variance_pct = (variance / total_budget) * 100 if total_budget else 0
            
            narrative += f"**Budget Summary:**\n\n"
            narrative += f"- Total Budget: ${total_budget:,.2f}\n"
            narrative += f"- Total Actual Spending: ${total_actual:,.2f}\n"
            
            if variance < 0:
                narrative += f"- Under Budget by: ${abs(variance):,.2f} ({abs(variance_pct):.1f}%)\n\n"
            else:
                narrative += f"- Over Budget by: ${variance:,.2f} ({variance_pct:.1f}%)\n\n"
                
            # Check if there's fiscal year data for trend analysis
            if "FiscalYear" in df.columns:
                narrative += "**Yearly Trends:**\n\n"
                years_summary = df.groupby("FiscalYear").agg({
                    "Budget": "sum", 
                    "Actual": "sum"
                }).reset_index()
                
                for _, row in years_summary.iterrows():
                    year = row["FiscalYear"]
                    budget = row["Budget"]
                    actual = row["Actual"]
                    yr_var = actual - budget
                    yr_var_pct = (yr_var / budget) * 100 if budget else 0
                    
                    if yr_var < 0:
                        narrative += f"- {year}: Budget ${budget:,.2f}, Spent ${actual:,.2f} (Under by {abs(yr_var_pct):.1f}%)\n"
                    else:
                        narrative += f"- {year}: Budget ${budget:,.2f}, Spent ${actual:,.2f} (Over by {yr_var_pct:.1f}%)\n"
            
            narrative += "\n**Recommendation:**\n\n"
            narrative += "- Consider adjusting budget allocations based on historical spending patterns."
            narrative += "\n- For detailed AI-powered insights, please ensure your OpenAI API key has sufficient quota."
                
        else:
            # Generic fallback for other data types
            num_rows = len(df)
            num_cols = len(df.columns)
            
            narrative += f"Analyzed dataset with {num_rows} records and {num_cols} attributes.\n\n"
            narrative += "For detailed AI-powered insights, please ensure your OpenAI API key has sufficient quota."
            
    except Exception as e:
        narrative += f"Error generating basic analysis: {e}\n"
        narrative += "For detailed AI-powered insights, please ensure your OpenAI API key has sufficient quota."
    
    return narrative

# --- PDF Report Builder ---
def generate_pdf_report(title, narrative, df_summary, output_chart=None):
    """
    Generate a PDF report with narrative, data summary, and optional chart
    
    Args:
        title (str): Report title
        narrative (str): AI-generated narrative
        df_summary (DataFrame): Summary data
        output_chart: Optional chart to include
        
    Returns:
        bytes: PDF report as bytes
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(10)

    # Narrative section
    pdf.set_font("Helvetica", "", 12)
    for line in narrative.split("\n"):
        pdf.multi_cell(0, 8, line)
    pdf.ln(5)

    # Data summary
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Key Financial Data:", ln=True)
    pdf.set_font("Helvetica", "", 12)
    for i, row in df_summary.iterrows():
        row_text = " - ".join(str(x) for x in row)
        pdf.multi_cell(0, 8, row_text)

    # Chart image if provided
    if output_chart is not None:
        try:
            # Create a temporary file path that works on all platforms
            import tempfile
            chart_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            plt.figure(figsize=(6, 3))
            output_chart.savefig(chart_path)
            pdf.ln(10)
            pdf.image(chart_path, w=170)
            
            # Clean up temporary file
            import os
            os.unlink(chart_path)
        except Exception as e:
            # If chart rendering fails, just add a text note
            pdf.ln(5)
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 10, "Chart rendering unavailable", ln=True)

    # Output as bytes
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return pdf_bytes

# --- Master Report Generator ---
def generate_full_report(df, report_title="GovSight Auto-Generated Report", scenario_context=None):
    """
    Generate a full report from financial data
    
    Args:
        df (DataFrame): Financial data
        report_title (str): Report title
        scenario_context (str): Optional scenario context
        
    Returns:
        None: Creates a download button for the report
    """
    st.info("Generating your report...")

    # 1. AI narrative
    if scenario_context:
        prompt_extra = f" The user is working on the scenario: {scenario_context}."
    else:
        prompt_extra = ""
    narrative = generate_ai_narrative(df, prompt_extra=prompt_extra)

    # 2. Mini data summary
    if "Budget" in df.columns and "Actual" in df.columns:
        df_summary = df.groupby("FiscalYear").agg({"Budget": "sum", "Actual": "sum"}).reset_index()
    else:
        df_summary = df.head(10)

    # 3. Optional chart
    fig = None
    try:
        if "FiscalYear" in df_summary.columns and "Budget" in df_summary.columns and "Actual" in df_summary.columns:
            fig = plt.figure(figsize=(10, 5))
            ax = fig.add_subplot(111)
            df_summary.plot(x="FiscalYear", y=["Budget", "Actual"], ax=ax, marker='o')
            plt.title("Budget vs. Actual Over Time")
            plt.grid(True, linestyle='--', alpha=0.7)
    except Exception as e:
        st.warning(f"Chart generation error: {e}")
        fig = None

    # 4. Assemble PDF
    pdf_bytes = generate_pdf_report(report_title, narrative, df_summary, output_chart=fig)

    # 5. Download link
    st.success(" Report ready!")
    st.download_button(" Download Full Report", data=pdf_bytes, file_name="govsight_budget_report.pdf", mime="application/pdf")

# Utilities for scenario comparison
def add_scenario_to_comparison(scenario_data):
    """
    Add a scenario to the comparison list in session state
    
    Args:
        scenario_data (dict or int): The scenario data to add to comparison or just the scenario ID
    """
    # Initialize session state for saved scenarios if it doesn't exist
    if "saved_scenarios" not in st.session_state:
        st.session_state.saved_scenarios = []
    
    # Check if this scenario is already in the list to avoid duplicates
    scenario_ids = [s.get('id') for s in st.session_state.saved_scenarios]
    
    # Handle both dictionary and direct ID inputs
    if isinstance(scenario_data, dict) and 'id' in scenario_data:
        scenario_id = scenario_data['id']
        if scenario_id not in scenario_ids:
            # Add this scenario to the list for comparison
            st.session_state.saved_scenarios.append(scenario_data)
            return True
    elif isinstance(scenario_data, int):
        # If just an ID is provided, create a minimal scenario dict
        scenario_id = scenario_data
        if scenario_id not in scenario_ids:
            # Create a minimal scenario dict with just the ID
            # The full data will be loaded when needed for comparison
            from db_connection import get_scenarios  # Import here to avoid circular imports
            # Get the scenario data from the database
            all_scenarios = get_scenarios()
            for s in all_scenarios:
                if s['id'] == scenario_id:
                    st.session_state.saved_scenarios.append(s)
                    return True
            # If scenario not found but we still want to track the ID
            st.session_state.saved_scenarios.append({'id': scenario_id, 'name': f'Scenario {scenario_id}'})
            return True
    
    return False

def remove_scenario_from_comparison(scenario_id):
    """
    Remove a scenario from the comparison list
    
    Args:
        scenario_id (int): The ID of the scenario to remove
    """
    if "saved_scenarios" in st.session_state and st.session_state.saved_scenarios:
        st.session_state.saved_scenarios = [
            s for s in st.session_state.saved_scenarios if s.get('id') != scenario_id
        ]
        return True
    return False

# --- Scenario Comparison Generator ---
def compare_scenarios_and_generate_report():
    """
    Compare multiple scenarios and generate a comparison report
    """
    st.subheader(" Compare Multiple Scenarios")

    # Load all recent scenarios to make them accessible for adding to comparison
    from db_connection import get_scenarios  # Import here to avoid circular imports
    recent_scenarios = get_scenarios(limit=10)
    
    if "saved_scenarios" not in st.session_state or not st.session_state.saved_scenarios:
        st.info("No saved scenarios to compare yet. Build and save some in the Scenario Planner!")
        
        # If we have recent scenarios, let's offer a way to add them directly
        if recent_scenarios:
            st.markdown("### Recent Scenarios")
            
            scenario_data = []
            for s in recent_scenarios:
                scenario_data.append({
                    "Name": s["name"],
                    "Total Cost": f"${s.get('total_amount', 0):,.2f}",
                    "Date Created": s["created_at"]
                })
            
            scenario_df = pd.DataFrame(scenario_data)
            st.dataframe(scenario_df, hide_index=True)
            
            # Add option to add all recent scenarios to comparison
            if st.button(" Add All Recent Scenarios to Comparison", type="primary"):
                added_count = 0
                for s in recent_scenarios:
                    # Format for comparison list
                    scenario_to_add = {
                        "id": s['id'],
                        "name": s['name'],
                        "total_amount": s.get('total_amount', 0),
                        "department_count": s.get('department_count', 0),
                        "created_at": s.get('created_at', '')
                    }
                    if add_scenario_to_comparison(scenario_to_add):
                        added_count += 1
                
                if added_count > 0:
                    st.success(f"Added {added_count} scenarios to comparison list!")
                    st.rerun()
                else:
                    st.info("No new scenarios added.")
        
        # Standard help message
        st.markdown("""
        ### How to Add Scenarios for Comparison
        1. Go to the **Scenario Planner** tab
        2. Create and save a scenario or select an existing one
        3. Use the **Add to Comparison List** button or **Add All Recent Scenarios** button
        4. Come back to this tab to compare multiple scenarios
        """)
        
        # Add button to go to Scenario Planner
        if st.button("Go to Scenario Planner"):
            st.session_state.selected_tab = "Scenario Planner"
            st.rerun()
        return

    # Display the current scenarios in the comparison list
    st.markdown("### Current Scenarios in Comparison List")
    
    # Get detailed scenario data from the database
    from db_connection import get_detailed_scenario_data, execute_query  # Import here to avoid circular imports
    
    # Enhance the data with more information from the database
    enhanced_scenarios = []
    for s in st.session_state.saved_scenarios:
        scenario_id = s.get('id')
        enhanced_scenario = s.copy()
        
        # Try to get more details from the database
        try:
            # Get the full scenario details
            detailed = get_detailed_scenario_data(scenario_id)
            if detailed:
                # Add additional fields from the detailed data
                enhanced_scenario.update({
                    "project_name": detailed.get("project_name", "Unknown"),
                    "department_allocations": detailed.get("department_allocations", {}),
                    "funding_sources": detailed.get("funding_sources", {})
                })
        except Exception as e:
            # Just continue with the basic data if we can't get details
            pass
            
        enhanced_scenarios.append(enhanced_scenario)
    
    # Update the session state with enhanced data
    st.session_state.saved_scenarios = enhanced_scenarios
    
    # Display the current scenarios in the comparison list
    current_scenarios_df = pd.DataFrame([
        {
            "Name": s["name"], 
            "Total Amount": f"${s.get('total_amount', 0):,.2f}", 
            "Date Created": s.get('created_at', ''),
            "Project": s.get("project_name", "Unknown")
        } 
        for s in st.session_state.saved_scenarios
    ])
    st.dataframe(current_scenarios_df, hide_index=True)
    
    # Add button to clear the comparison list
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Comparison List"):
            # Clear the saved scenarios list
            st.session_state.saved_scenarios = []
            st.success("Comparison list cleared!")
            st.rerun()
    
    with col2:
        if st.button("↻ Refresh Scenario Data"):
            st.success("Refreshing scenario data...")
            st.rerun()
    
    scenario_names = [s["name"] for s in st.session_state.saved_scenarios]
    selected = st.multiselect("Select Scenarios to Compare", scenario_names, default=scenario_names[:2] if len(scenario_names) >= 2 else scenario_names)

    if len(selected) < 2:
        st.warning("Please select at least two scenarios to compare.")
        return

    selected_scenarios = [s for s in st.session_state.saved_scenarios if s["name"] in selected]

    st.subheader(" Scenario Comparison Details")
    
    # Format the DataFrame for better display
    comparison_data = []
    for s in selected_scenarios:
        comparison_data.append({
            "Name": s["name"],
            "Total Amount": s.get("total_amount", 0),
            "Department Count": s.get("department_count", 0),
            "Date Created": s.get("created_at", "")
        })
    
    df_compare = pd.DataFrame(comparison_data)
    
    # Add formatting for currency
    df_display = df_compare.copy()
    df_display["Total Amount"] = df_display["Total Amount"].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(df_display, hide_index=True)

    if st.button("💬 Generate AI Comparison Summary"):
        scenario_summary = df_compare.to_csv(index=False)
        prompt = f"Compare these government budget scenarios and recommend the best option:\n{scenario_summary}"
        try:
            # Check if a valid OpenAI API key is available
            if not openai.api_key or openai.api_key == "sk-placeholder":
                st.warning("OpenAI API key not configured. Using fallback analysis instead.")
                st.markdown(generate_fallback_comparison(df_compare))
                return
            
            # Create a client instance
            client = openai.OpenAI(api_key=openai.api_key)
            
            try:
                # Try with gpt-3.5-turbo model instead of gpt-4o to avoid quota issues
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo", # Use gpt-3.5-turbo which has higher quotas
                    messages=[
                        {"role": "system", "content": "You are a financial strategist."},
                        {"role": "user", "content": prompt}
                    ]
                )
                st.success("AI Recommendation:")
                st.markdown(response.choices[0].message.content)
            except Exception as api_error:
                # If we get an API error (like quota exceeded), use a fallback
                st.warning(f"OpenAI API Error: {str(api_error)}")
                st.markdown(generate_fallback_comparison(df_compare))
                
        except Exception as e:
            st.error(f"Error generating comparison: {e}")
            st.markdown(generate_fallback_comparison(df_compare))

    if st.button(" Download Scenario Comparison PDF"):
        # Create a more professional PDF report
        pdf = FPDF()
        pdf.add_page()
        
        # Add header
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "GovSight Scenario Comparison Report", ln=True, align="C")
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 10, f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align="C")
        pdf.ln(5)
        
        # Add comparison summary
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Comparison Summary", ln=True)
        
        # Get summary statistics
        num_scenarios = len(df_compare)
        if 'Total Amount' in df_compare.columns:
            max_idx = df_compare['Total Amount'].idxmax()
            min_idx = df_compare['Total Amount'].idxmin()
            max_scenario = df_compare.iloc[max_idx]
            min_scenario = df_compare.iloc[min_idx]
            avg_amount = df_compare['Total Amount'].mean()
            
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(0, 8, f"Number of Scenarios Compared: {num_scenarios}", ln=True)
            pdf.cell(0, 8, f"Highest Amount Scenario: {max_scenario['Name']} (${max_scenario['Total Amount']:,.2f})", ln=True)
            pdf.cell(0, 8, f"Lowest Amount Scenario: {min_scenario['Name']} (${min_scenario['Total Amount']:,.2f})", ln=True)
            pdf.cell(0, 8, f"Average Amount: ${avg_amount:,.2f}", ln=True)
        else:
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(0, 8, f"Number of Scenarios Compared: {num_scenarios}", ln=True)
        
        pdf.ln(10)
        
        # Add scenario comparison table
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Detailed Scenario Comparison", ln=True)
        
        # Create a table-like structure for scenarios
        pdf.set_font("Helvetica", "B", 10)
        
        # Table header
        col_width = 45
        pdf.cell(col_width, 10, "Scenario Name", border=1)
        pdf.cell(col_width, 10, "Total Amount", border=1) 
        pdf.cell(col_width, 10, "Department Count", border=1)
        pdf.cell(col_width, 10, "Date Created", border=1)
        pdf.ln()
        
        # Table content
        pdf.set_font("Helvetica", "", 10)
        for idx, row in df_compare.iterrows():
            pdf.cell(col_width, 10, str(row["Name"]), border=1)
            pdf.cell(col_width, 10, f"${row['Total Amount']:,.2f}", border=1)
            pdf.cell(col_width, 10, str(row["Department Count"]), border=1)
            pdf.cell(col_width, 10, str(row["Date Created"]), border=1)
            pdf.ln()
        
        pdf.ln(10)
        
        # Add recommendations
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Recommendations", ln=True)
        
        pdf.set_font("Helvetica", "", 12)
        if 'Total Amount' in df_compare.columns:
            pdf.multi_cell(0, 8, f"Based on financial analysis, the scenario '{max_scenario['Name']}' provides the highest funding amount at ${max_scenario['Total Amount']:,.2f}.")
            pdf.multi_cell(0, 8, f"The scenario '{min_scenario['Name']}' offers the most cost-effective approach at ${min_scenario['Total Amount']:,.2f}.")
            pdf.multi_cell(0, 8, "For a more comprehensive analysis, we recommend reviewing each scenario in detail considering factors beyond just financial amounts.")
        else:
            pdf.multi_cell(0, 8, "For detailed scenario analysis, we recommend reviewing each scenario individually in the Scenario Planner.")
        
        # Add footer with GovSight branding
        pdf.ln(10)
        pdf.set_y(-30)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 10, "Generated by GovSight Financial Analyzer Platform", ln=True, align="C")
        pdf.cell(0, 10, "© Municipal Funding Optimization System", ln=True, align="C")
        
        # Convert PDF to bytes
        pdf_bytes = pdf.output(dest='S').encode('latin-1')  
        
        # Create download button
        st.success(" Comparison Report Generated!")
        st.download_button(
            " Download Comparison PDF", 
            data=pdf_bytes, 
            file_name=f"govsight_scenario_comparison_{datetime.now().strftime('%Y%m%d')}.pdf", 
            mime="application/pdf"
        )

# --- Fallback Comparison Generator ---
def generate_fallback_comparison(df_compare):
    """
    Generate a basic comparison of scenarios without using AI
    
    Args:
        df_compare (DataFrame): DataFrame with scenario comparison data
        
    Returns:
        str: Formatted markdown with basic comparison information
    """
    # Basic analysis of the data
    num_scenarios = len(df_compare)
    
    # Find the scenario with highest total amount
    if 'Total Amount' in df_compare.columns:
        max_amount_scenario = df_compare.loc[df_compare['Total Amount'].idxmax()]
        min_amount_scenario = df_compare.loc[df_compare['Total Amount'].idxmin()]
        avg_amount = df_compare['Total Amount'].mean()
        
        # Prepare the comparison text
        comparison = f"""
        ## Scenario Comparison Summary
        
        **Overview:** Analyzed {num_scenarios} different funding scenarios.
        
        **Financial Analysis:**
        - Highest funding: "{max_amount_scenario['Name']}" at ${max_amount_scenario['Total Amount']:,.2f}
        - Lowest funding: "{min_amount_scenario['Name']}" at ${min_amount_scenario['Total Amount']:,.2f}
        - Average funding: ${avg_amount:,.2f}
        
        **Recommendation:**
        Without an AI-based analysis, we recommend reviewing the "{max_amount_scenario['Name']}" scenario for maximum funding impact, or the "{min_amount_scenario['Name']}" scenario for cost efficiency.
        
        For a more detailed AI-powered comparison, please ensure your OpenAI API key has sufficient quota.
        """
    else:
        # Fallback if total_amount is not available
        comparison = f"""
        ## Basic Scenario Comparison
        
        Compared {num_scenarios} funding scenarios.
        
        For detailed scenario analysis, we recommend reviewing each scenario individually in the Scenario Planner.
        
        For AI-powered recommendations, please ensure your OpenAI API key has sufficient quota.
        """
    
    return comparison

# --- Executive AI Summary for Scenario ---
def generate_scenario_exec_summary(project_name, department, cost, tax_increase, grant_amount):
    """
    Generate an executive summary for the project scenario using AI
    
    Args:
        project_name (str): Name of the project
        department (str): Department responsible for the project
        cost (float): Total project cost
        tax_increase (float): Projected tax revenue increase
        grant_amount (float): Available grant funding
        
    Returns:
        str: AI-generated executive summary
    """
    try:
        # Check if a valid OpenAI API key is available
        if not openai.api_key or openai.api_key == "sk-placeholder":
            st.warning("OpenAI API key not configured. Using default analysis instead.")
            return generate_fallback_exec_summary(project_name, department, cost, tax_increase, grant_amount)
        
        # Create a client instance
        client = openai.OpenAI(api_key=openai.api_key)
        
        prompt = f"Write a 1-paragraph executive summary for a city project called '{project_name}' managed by the {department} department. The total project cost is ${cost:,.0f}. They expect a tax revenue increase of ${tax_increase:,.0f} and grant funding of ${grant_amount:,.0f}. Summarize the project benefits, risks, and funding situation."
        
        try:
            # Use the new API format with gpt-3.5-turbo to avoid quota issues
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a city finance officer drafting an executive summary for city leadership."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as api_error:
            # If the API call fails, use fallback
            st.warning(f"OpenAI API Error: {str(api_error)}")
            return generate_fallback_exec_summary(project_name, department, cost, tax_increase, grant_amount)
    except Exception as e:
        st.error(f"Executive Summary generation failed: {e}")
        return generate_fallback_exec_summary(project_name, department, cost, tax_increase, grant_amount)

def generate_fallback_exec_summary(project_name, department, cost, tax_increase, grant_amount):
    """
    Generate a fallback executive summary without using AI
    
    Args:
        project_name (str): Name of the project
        department (str): Department responsible for the project
        cost (float): Total project cost
        tax_increase (float): Projected tax revenue increase
        grant_amount (float): Available grant funding
        
    Returns:
        str: Generated executive summary
    """
    remaining_need = cost - (grant_amount + tax_increase)
    funding_ratio = ((grant_amount + tax_increase) / cost) * 100 if cost > 0 else 0
    
    summary = f"Executive Summary: The {project_name} project, managed by the {department} department, "
    summary += f"has a total estimated cost of ${cost:,.0f}. "
    
    if funding_ratio >= 90:
        summary += f"The project is well-funded with secured grants (${grant_amount:,.0f}) and projected tax increases "
        summary += f"(${tax_increase:,.0f}), covering {funding_ratio:.1f}% of costs with minimal remaining funding needs "
        summary += f"of ${remaining_need:,.0f}."
    elif funding_ratio >= 70:
        summary += f"The project has significant funding through grants (${grant_amount:,.0f}) and projected tax increases "
        summary += f"(${tax_increase:,.0f}), but requires additional funding of ${remaining_need:,.0f} to be fully financed."
    else:
        summary += f"The project faces funding challenges with a significant gap of ${remaining_need:,.0f} despite "
        summary += f"secured grants (${grant_amount:,.0f}) and projected tax increases (${tax_increase:,.0f}). Additional "
        summary += f"funding sources should be identified before proceeding."
    
    return summary

# --- Enhanced Scenario Report ---
def generate_full_scenario_report(project_name, department, cost, tax_increase, grant_amount, notes=""):
    """
    Generate a comprehensive PDF report for the funding scenario
    
    Args:
        project_name (str): Name of the project
        department (str): Department responsible for the project
        cost (float): Total project cost
        tax_increase (float): Projected tax revenue increase
        grant_amount (float): Available grant funding
        notes (str, optional): Additional notes for the report
        
    Returns:
        None: Creates a download button for the report
    """
    st.info("Generating your scenario report...")

    # Generate AI executive summary
    exec_summary = generate_scenario_exec_summary(project_name, department, cost, tax_increase, grant_amount)

    # Calculate remaining funding need
    remaining_need = cost - (grant_amount + tax_increase)

    # Generate chart
    fig, ax = plt.subplots()
    labels = ['Grant Funding', 'Tax Increase', 'Remaining Need']
    values = [grant_amount, tax_increase, remaining_need]
    colors = ['#4CAF50', '#2196F3', '#FF5722']
    
    # Handle negative values in pie chart
    if min(values) < 0:
        st.warning("Cannot generate pie chart with negative values. Using bar chart instead.")
        ax.bar(labels, values, color=colors)
        ax.set_ylabel('Amount ($)')
        ax.set_title('Project Funding Breakdown')
    else:
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        ax.axis('equal')
    
    # Create a temporary file path that works on all platforms
    chart_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    plt.savefig(chart_path)

    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "GovSight Scenario Report", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 12)
    for line in exec_summary.split("\n"):
        pdf.multi_cell(0, 8, line)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Scenario Details", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Project Name: {project_name}", ln=True)
    pdf.cell(0, 8, f"Department: {department}", ln=True)
    pdf.cell(0, 8, f"Total Project Cost: ${cost:,.0f}", ln=True)
    pdf.cell(0, 8, f"Expected Tax Increase: ${tax_increase:,.0f}", ln=True)
    pdf.cell(0, 8, f"Projected Grant Funding: ${grant_amount:,.0f}", ln=True)
    pdf.cell(0, 8, f"Remaining Need: ${remaining_need:,.0f}", ln=True)

    # Funding status assessment
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Funding Assessment", ln=True)
    pdf.set_font("Helvetica", "", 12)
    
    funding_ratio = ((grant_amount + tax_increase) / cost) * 100 if cost > 0 else 0
    pdf.cell(0, 8, f"Funding Coverage: {funding_ratio:.1f}%", ln=True)
    
    if funding_ratio >= 90:
        status = "Well Funded"
    elif funding_ratio >= 70:
        status = "Adequately Funded"
    elif funding_ratio >= 50:
        status = "Partially Funded"
    else:
        status = "Funding Deficient"
        
    pdf.cell(0, 8, f"Status: {status}", ln=True)

    if notes:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Notes", ln=True)
        pdf.set_font("Helvetica", "", 12)
        for line in notes.split("\n"):
            pdf.multi_cell(0, 8, line)

    # Add the chart
    pdf.ln(10)
    pdf.image(chart_path, w=170)
    
    # Clean up temporary file
    try:
        os.unlink(chart_path)
    except:
        pass

    # Convert PDF to bytes with proper encoding handling
    try:
        # Try UTF-8 first for better character support
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            pdf_bytes = pdf_output.encode('utf-8', errors='replace')
        else:
            pdf_bytes = pdf_output
    except UnicodeEncodeError:
        # Fall back to latin-1 if UTF-8 fails
        try:
            pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='replace')
        except:
            # Final fallback - output as bytes directly
            pdf_bytes = pdf.output(dest='S')
            if isinstance(pdf_bytes, str):
                pdf_bytes = pdf_bytes.encode('utf-8', errors='ignore')
    
    # Save to archive
    username = st.session_state.user['username'] if 'user' in st.session_state else "admin"
    archive_filename = archive.save_scenario_report_to_archive(pdf_bytes, project_name, department, username)
    
    st.success(f" Report ready! Saved to archive as {archive_filename}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(" Download Scenario Full Report", data=pdf_bytes, file_name="govsight_scenario_full_report.pdf", mime="application/pdf")
    with col2:
        if st.button(" View Archive"):
            st.session_state.selected_tab = "Reports"
            st.session_state.show_archive = True
            st.rerun()

# --- (Removed run_enhanced_scenario_report as it's now integrated directly) ---

def run_report_generator():
    """
    Run the report generator module with role-based access control
    """
    st.title(" Summary Report Generator")
    
    # Check user permissions with more detailed feedback
    try:
        if not sec.is_admin() and not sec.is_finance_director():
            st.warning("You don't have permissions to generate financial reports.")
            st.info("Financial report generation requires Administrator or Finance Director privileges.")
            st.info("Current user access level allows viewing existing reports but not generating new ones.")
            st.info("Please contact your system administrator to request appropriate access.")
            return
    except Exception as e:
        st.error(f"Permission check failed: {str(e)}")
        st.info("Unable to verify user permissions. Please contact your administrator.")
        return
    
    # Add tabs for different report types
    report_tab, comparison_tab, archive_tab = st.tabs(["Single Report", "Scenario Comparison", "Report Archive"])
    
    # Initialize show_archive flag if not exists
    if "show_archive" not in st.session_state:
        st.session_state.show_archive = False
    
    # Auto-select the Archive tab if directed from elsewhere
    if st.session_state.show_archive:
        st.session_state.show_archive = False  # Reset flag
        # Must be done via JavaScript - Streamlit doesn't support direct tab switching
        st.markdown("""
        <script>
            document.querySelector('[data-baseweb="tab"][aria-selected="true"]').setAttribute('aria-selected', 'false');
            document.querySelectorAll('[data-baseweb="tab"]')[2].setAttribute('aria-selected', 'true');
        </script>
        """, unsafe_allow_html=True)
    
    with report_tab:
        st.markdown("""
        This tool allows you to generate comprehensive financial reports with AI-powered analysis.
        Select a data source and customize your report options below.
        """)
        
        # First section for data source-based reports
        st.subheader("Standard Financial Reports")
        
        # Load data from a module
        data_source = st.selectbox(
            "Select Data Source",
            ["Historical Budget Data", "Department Performance", "Current Scenario"]
        )
        
        # Load appropriate data based on selection
        if data_source == "Historical Budget Data":
            from db_connection import load_org_data
            df = load_org_data()
            report_title = "Historical Budget Analysis Report"
        elif data_source == "Department Performance":
            from db_connection import load_org_data
            df = load_org_data()
            
            # Filter by department for department managers
            allowed_depts = sec.get_user_departments()
            if allowed_depts:
                df = df[df["DepartmentName"].isin(allowed_depts)]
                
            report_title = "Department Performance Report"
        else:
            # For scenario data, we'd need to load from the session state
            if "scenario_data" in st.session_state:
                df = st.session_state.scenario_data
                report_title = f"Funding Scenario Report - {st.session_state.scenario_name}"
            else:
                st.warning("No active scenario found. Please create or open a scenario first.")
                st.markdown("""
                To export a scenario from the Scenario Planner to this module:
                1. Go to the **Scenario Planner** tab
                2. Create and save your scenario
                3. Click on the **Export to Enhanced Reports** button
                """)
                df = pd.DataFrame()
                report_title = "Current Scenario Report"
        
        if not df.empty:
            # Allow the user to customize the report title
            custom_title = st.text_input("Report Title", value=report_title)
            
            # Additional context for the AI narrative
            context = st.text_area("Additional Context for Analysis", 
                                help="Add any specific questions or information you want the AI to address in the analysis")
            
            # Generate the report
            if st.button("Generate Standard Report"):
                generate_full_report(df, report_title=custom_title, scenario_context=context)
        else:
            st.error("No data available for the selected source. Please choose a different data source.")
        
        # Second section for enhanced scenario reports
        st.markdown("---")
        st.subheader("Enhanced Scenario Report")
        st.markdown("""
        Create a detailed funding scenario report with AI-powered executive summary and
        visualizations for funding breakdowns. This report provides more detailed analysis
        of project funding scenarios.
        """)
        
        # Form for enhanced scenario details
        with st.form("enhanced_scenario_form"):
            project_name = st.text_input("Project Name", "New Community Center")
            department = st.selectbox("Department", [
                "Parks & Recreation", "Public Works", "Public Safety", 
                "Community Development", "Administration", "Finance",
                "Information Technology", "Human Resources"
            ])
            
            col1, col2 = st.columns(2)
            with col1:
                cost = st.number_input("Total Project Cost ($)", min_value=0, value=1000000, step=10000)
                tax_increase = st.number_input("Expected Tax Revenue Increase ($)", min_value=0, value=200000, step=10000)
            with col2:
                grant_amount = st.number_input("Projected Grant Funding ($)", min_value=0, value=500000, step=10000)
                notes = st.text_area("Additional Notes", "")
            
            submit = st.form_submit_button("Generate Enhanced Report")
        
        # Display preview and generate report
        if submit:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("Funding Breakdown")
                remaining_need = cost - (tax_increase + grant_amount)
                
                # Create simple chart for preview
                fig, ax = plt.subplots(figsize=(6, 4))
                labels = ['Grant Funding', 'Tax Increase', 'Remaining Need']
                values = [grant_amount, tax_increase, remaining_need]
                colors = ['#4CAF50', '#2196F3', '#FF5722']
                
                if min(values) < 0:
                    ax.bar(labels, values, color=colors)
                    ax.set_ylabel('Amount ($)')
                    ax.set_title('Project Funding Breakdown')
                else:
                    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
                    ax.axis('equal')
                    
                st.pyplot(fig)
            
            with col2:
                st.subheader("Summary")
                st.markdown(f"**Project:** {project_name}")
                st.markdown(f"**Department:** {department}")
                st.markdown(f"**Total Cost:** ${cost:,.0f}")
                st.markdown(f"**Tax Revenue:** ${tax_increase:,.0f}")
                st.markdown(f"**Grant Funding:** ${grant_amount:,.0f}")
                st.markdown(f"**Remaining Need:** ${remaining_need:,.0f}")
            
            # Generate full report with PDF
            st.markdown("---")
            generate_full_scenario_report(project_name, department, cost, tax_increase, grant_amount, notes)
    
    with comparison_tab:
        compare_scenarios_and_generate_report()
    
    with archive_tab:
        st.subheader(" Archived Reports")
        st.markdown("""
        View and download previously generated reports that have been automatically archived.
        This archive contains all reports generated across the application.
        """)
        
        # Load archive metadata
        archive_df = archive.load_archive_metadata()
        
        if archive_df.empty:
            st.info("No reports have been archived yet. Generate a report to see it here.")
        else:
            # Add timestamp column in readable format
            archive_df["Created"] = pd.to_datetime(archive_df["Timestamp"], format="%Y%m%d_%H%M%S").dt.strftime("%b %d, %Y %I:%M %p")
            
            # Add filters
            col1, col2 = st.columns(2)
            with col1:
                dept_filter = st.multiselect("Filter by Department", 
                                            options=["All"] + sorted(archive_df["Department"].unique().tolist()),
                                            default=["All"])
            with col2:
                user_filter = st.multiselect("Filter by Creator", 
                                            options=["All"] + sorted(archive_df["CreatedBy"].unique().tolist()),
                                            default=["All"])
            
            # Apply filters
            filtered_df = archive_df.copy()
            if dept_filter and "All" not in dept_filter:
                filtered_df = filtered_df[filtered_df["Department"].isin(dept_filter)]
            if user_filter and "All" not in user_filter:
                filtered_df = filtered_df[filtered_df["CreatedBy"].isin(user_filter)]
            
            # Display filtered archive
            if filtered_df.empty:
                st.warning("No reports match the selected filters.")
            else:
                # Sort by timestamp (newest first)
                filtered_df = filtered_df.sort_values("Timestamp", ascending=False)
                
                # Create display table (hide technical fields)
                display_df = filtered_df[["ProjectName", "Department", "CreatedBy", "Created"]].copy()
                display_df.columns = ["Project Name", "Department", "Created By", "Date & Time"]
                
                # Show the table
                st.dataframe(display_df)
                
                # View selected report
                st.subheader("View Report")
                selected_index = st.selectbox("Select a report to view:", 
                                            options=range(len(filtered_df)),
                                            format_func=lambda x: f"{filtered_df.iloc[x]['ProjectName']} - {filtered_df.iloc[x]['Department']} ({filtered_df.iloc[x]['Created']})")
                
                selected_file = filtered_df.iloc[selected_index]["Filename"]
                file_path = os.path.join(archive.ARCHIVE_FOLDER, selected_file)
                
                # Display PDF download button
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        pdf_bytes = f.read()
                        st.download_button(" Download Selected Report", 
                                        data=pdf_bytes, 
                                        file_name=selected_file,
                                        mime="application/pdf")
                    
                    # If using a PDF viewer component, could show preview here
                    st.info("PDF preview is not available. Please download to view the full report.")
                else:
                    st.error(f"File not found: {selected_file}")
    
if __name__ == "__main__":
    run_report_generator()