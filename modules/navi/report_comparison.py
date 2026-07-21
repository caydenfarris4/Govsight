"""
Report Comparison Module for Navi

This module was moved from Mantis to Navi as it better fits with scenario planning
and navigation workflows. It provides comprehensive scenario comparison and
report generation capabilities.
"""

import streamlit as st
import pandas as pd
import openai
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
from io import BytesIO
import plotly.express as px
import matplotlib.pyplot as plt
import tempfile
import os
from datetime import datetime

# AI API Key Setup - Use from environment or secrets
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

# Import required modules
import sys
import os
# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    import modules.security.security_manager as sec
    import modules.admin.admin_archive_manager as archive
except ImportError as e:
    st.error(f"Import error in report comparison: {e}")

def generate_fallback_comparison(df_compare):
    """
    Generate a fallback comparison analysis when AI is unavailable
    
    Args:
        df_compare (DataFrame): The comparison data
        
    Returns:
        str: Formatted comparison analysis
    """
    if df_compare.empty:
        return "No scenarios available for comparison."
    
    analysis = "## Scenario Comparison Analysis\n\n"
    
    # Find the scenario with highest and lowest amounts
    if "Total Amount" in df_compare.columns:
        highest_idx = df_compare["Total Amount"].idxmax()
        lowest_idx = df_compare["Total Amount"].idxmin()
        
        highest_scenario = df_compare.loc[highest_idx]
        lowest_scenario = df_compare.loc[lowest_idx]
        
        analysis += f"**Budget Range Analysis:**\n"
        analysis += f"- Highest Budget: {highest_scenario['Name']} (${highest_scenario['Total Amount']:,.2f})\n"
        analysis += f"- Lowest Budget: {lowest_scenario['Name']} (${lowest_scenario['Total Amount']:,.2f})\n"
        
        budget_difference = highest_scenario['Total Amount'] - lowest_scenario['Total Amount']
        analysis += f"- Budget Difference: ${budget_difference:,.2f}\n\n"
        
        # Calculate average
        avg_budget = df_compare["Total Amount"].mean()
        analysis += f"**Average Budget:** ${avg_budget:,.2f}\n\n"
        
        # Recommendations based on budget analysis
        analysis += "**Preliminary Recommendations:**\n"
        for _, row in df_compare.iterrows():
            budget = row["Total Amount"]
            if budget == df_compare["Total Amount"].max():
                analysis += f"- {row['Name']}: Highest investment option - consider if budget allows and ROI justifies cost\n"
            elif budget == df_compare["Total Amount"].min():
                analysis += f"- {row['Name']}: Most cost-effective option - good for budget-conscious implementations\n"
            elif abs(budget - avg_budget) < (avg_budget * 0.1):
                analysis += f"- {row['Name']}: Balanced middle-ground option - moderate cost and scope\n"
        
        analysis += "\n*This is a basic comparison. For detailed AI-powered analysis, please configure your OpenAI API key.*"
    
    return analysis

def add_scenario_to_comparison(scenario_data):
    """
    Add a scenario to the comparison list in session state
    
    Args:
        scenario_data (dict or int): The scenario data to add to comparison or just the scenario ID
        
    Returns:
        bool: True if scenario was added, False if it was already in the list
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
            try:
                from modules.database.connection_manager import get_scenarios
                # Get the scenario data from the database
                all_scenarios = get_scenarios()
                for s in all_scenarios:
                    if s['id'] == scenario_id:
                        st.session_state.saved_scenarios.append(s)
                        return True
                # If scenario not found but we still want to track the ID
                st.session_state.saved_scenarios.append({'id': scenario_id, 'name': f'Scenario {scenario_id}'})
                return True
            except ImportError:
                st.session_state.saved_scenarios.append({'id': scenario_id, 'name': f'Scenario {scenario_id}'})
                return True
    
    return False

def remove_scenario_from_comparison(scenario_id):
    """
    Remove a scenario from the comparison list
    
    Args:
        scenario_id (int): The ID of the scenario to remove
        
    Returns:
        bool: True if scenario was removed, False if not found
    """
    if "saved_scenarios" in st.session_state and st.session_state.saved_scenarios:
        original_count = len(st.session_state.saved_scenarios)
        st.session_state.saved_scenarios = [
            s for s in st.session_state.saved_scenarios if s.get('id') != scenario_id
        ]
        return len(st.session_state.saved_scenarios) < original_count
    return False

def compare_scenarios_and_generate_report():
    """
    Compare multiple scenarios and generate a comparison report
    """
    st.subheader("Compare Multiple Scenarios")

    # Load all recent scenarios to make them accessible for adding to comparison
    try:
        from modules.database.connection_manager import get_scenarios
        recent_scenarios = get_scenarios(limit=10)
    except TypeError as e:
        # Handle case where limit parameter is not supported
        try:
            from modules.database.connection_manager import get_scenarios
            all_scenarios = get_scenarios()
            recent_scenarios = all_scenarios[:10] if all_scenarios else []
        except Exception as e2:
            st.error(f"Database connection error: {str(e2)}")
            st.info("Unable to load scenarios. Please check the database connection.")
            recent_scenarios = []
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        st.info("Unable to load scenarios. Please check the database connection.")
        recent_scenarios = []
    
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
            if st.button("Add All Recent Scenarios to Comparison", type="primary"):
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
            # Navigate to the Scenario Planner tab within Navi
            st.info("Please click on the Scenario Planner tab above to create scenarios.")
        return

    # Display the current scenarios in the comparison list
    st.markdown("### Current Scenarios in Comparison List")
    
    # Get detailed scenario data from the database
    try:
        from modules.database.connection_manager import get_detailed_scenario_data
        
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
        
    except ImportError:
        # If we can't import the database functions, continue with existing data
        pass
    
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
        if st.button("Clear Comparison List"):
            # Clear the saved scenarios list
            st.session_state.saved_scenarios = []
            st.success("Comparison list cleared!")
            st.rerun()
    
    with col2:
        if st.button("Refresh Scenario Data"):
            st.success("Refreshing scenario data...")
            st.rerun()
    
    scenario_names = [s["name"] for s in st.session_state.saved_scenarios]
    selected = st.multiselect("Select Scenarios to Compare", scenario_names, default=scenario_names[:2] if len(scenario_names) >= 2 else scenario_names)

    if len(selected) < 2:
        st.warning("Please select at least two scenarios to compare.")
        return

    selected_scenarios = [s for s in st.session_state.saved_scenarios if s["name"] in selected]

    st.subheader("Scenario Comparison Details")
    
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

    if st.button("Generate AI Comparison Summary"):
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
                    model="gpt-3.5-turbo",
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

    if st.button("Download Scenario Comparison PDF"):
        # Create a more professional PDF report
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "GovSight Scenario Comparison Report", ln=True, align="C")
        pdf.ln(10)

        # Add generation timestamp
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align="C")
        pdf.ln(10)

        # Add scenario comparison table
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Scenario Details:", ln=True)
        pdf.ln(5)

        pdf.set_font("Arial", "", 10)
        for idx, row in df_compare.iterrows():
            pdf.cell(0, 6, f"Scenario {idx + 1}: {row['Name']}", ln=True)
            pdf.cell(0, 6, f"  Total Amount: ${row['Total Amount']:,.2f}", ln=True)
            pdf.cell(0, 6, f"  Department Count: {row['Department Count']}", ln=True)
            pdf.cell(0, 6, f"  Date Created: {row['Date Created']}", ln=True)
            pdf.ln(3)

        # Add basic analysis
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Analysis Summary:", ln=True)
        pdf.ln(3)

        pdf.set_font("Arial", "", 10)
        
        # Calculate some basic statistics
        total_amounts = df_compare["Total Amount"].tolist()
        highest_amount = max(total_amounts)
        lowest_amount = min(total_amounts)
        avg_amount = sum(total_amounts) / len(total_amounts)
        
        highest_scenario = df_compare[df_compare["Total Amount"] == highest_amount]["Name"].iloc[0]
        lowest_scenario = df_compare[df_compare["Total Amount"] == lowest_amount]["Name"].iloc[0]

        analysis_lines = [
            f"Highest Budget: {highest_scenario} (${highest_amount:,.2f})",
            f"Lowest Budget: {lowest_scenario} (${lowest_amount:,.2f})",
            f"Average Budget: ${avg_amount:,.2f}",
            f"Budget Range: ${highest_amount - lowest_amount:,.2f}"
        ]

        for line in analysis_lines:
            pdf.cell(0, 6, line, ln=True)

        # Convert PDF to bytes with UTF-8 encoding (fixed from latin-1)
        pdf_bytes = pdf.output(dest='S').encode('utf-8', errors='replace')  
        
        # Save to archive if available
        try:
            username = st.session_state.user['username'] if 'user' in st.session_state else "admin"
            archive_filename = archive.save_scenario_report_to_archive(pdf_bytes, "Scenario Comparison", "Multiple", username)
            st.success(f"Report saved to archive as {archive_filename}")
        except:
            # If archive is not available, just offer download
            pass
        
        # Create download button
        st.success("Comparison Report Generated!")
        st.download_button(
            "Download Comparison PDF", 
            data=pdf_bytes, 
            file_name=f"govsight_scenario_comparison_{datetime.now().strftime('%Y%m%d')}.pdf", 
            mime="application/pdf"
        )

def render_report_comparison_interface():
    """
    Main function to render the report comparison interface
    """
    # Check user permissions
    try:
        if not sec.is_admin() and not sec.is_finance_director():
            st.warning("You don't have permissions to compare financial scenarios.")
            st.info("Scenario comparison requires Administrator or Finance Director privileges.")
            st.info("Please contact your system administrator to request appropriate access.")
            return
    except Exception as e:
        st.error(f"Permission check failed: {str(e)}")
        st.info("Unable to verify user permissions. Please contact your administrator.")
        return
    
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 30px;">
        <h2 style="color: white; margin: 0;">Scenario Comparison</h2>
        <p style="color: white; margin: 10px 0 0 0; opacity: 0.9;">Compare multiple budget scenarios and generate comprehensive reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main comparison interface
    compare_scenarios_and_generate_report()

# Export the main functions for use in other modules
__all__ = [
    'render_report_comparison_interface',
    'compare_scenarios_and_generate_report',
    'add_scenario_to_comparison',
    'remove_scenario_from_comparison'
]