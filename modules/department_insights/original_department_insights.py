"""
Department Insights Module

This module handles all functionality related to the Department Insights tab, including:
- Department performance metrics
- Fund allocation analysis
- Comparative department analysis
- Monthly spending patterns
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
from typing import Dict, Any, List, Optional, Union

# Import database functions from centralized db_connection.py
from db_connection import (
    load_org_data, 
    format_percentage, 
    format_currency, 
    get_db_path_for_org,
    load_transaction_data, 
    load_department_transactions,
    get_gl_account_balances,
    get_department_monthly_trend,
    get_selected_database
)
import security_manager as sec
import summary_report_generator as report_gen

# Account mask parsing is now integrated in db_connection.py
from db_connection import get_mask_from_settings, parse_account

# Import transaction integration for GL account data
from department_transaction_integration import display_department_transaction_analysis

# Import GL drilldown functionality if available
try:
    # First try the attached_assets folder
    import sys
    from pathlib import Path
    
    # Add attached_assets to path if it exists
    assets_path = Path("./attached_assets")
    if assets_path.exists() and assets_path.is_dir():
        if str(assets_path) not in sys.path:
            sys.path.append(str(assets_path))
    
    from govsight_gl_drilldown_module import load_data as load_gl_data
except ImportError:
    # If the module is not available, define a placeholder function
    def load_gl_data(db_path, department=None):
        """Placeholder function if the GL drilldown module is not available"""
        return None

# Import centralized AI Hub
try:
    from ai_hub import ask_ai, generate_dept_insights, generate_forecast
    AI_MODULE_AVAILABLE = True
except ImportError:
    AI_MODULE_AVAILABLE = False

def generate_ai_commentary(df, prompt=None):
    """
    Generate AI commentary on department data
    
    Args:
        df (DataFrame): pandas DataFrame with department data
        prompt (str, optional): User prompt for specific analysis. Defaults to None.
        
    Returns:
        str: AI commentary on the data
    """
    # Create a fallback response in case AI is not available
    fallback_response = """
    Based on the department financial data analysis:
    
    1. Look for consistent patterns in budget allocation across funds
    2. Compare actual vs. budgeted amounts to identify areas of concern
    3. Identify key spending categories that drive department costs
    4. Consider seasonal or periodic spending patterns that may affect projections
    """
    
    # Try using the centralized AI Hub first
    if AI_MODULE_AVAILABLE:
        try:
            # Get current department for context
            department = ""
            if 'selected_dept' in st.session_state:
                department = st.session_state.selected_dept
                
            # Use the department-specific AI insights function from the centralized hub
            return generate_dept_insights(df, department, prompt)
        except Exception as e:
            # If centralized AI fails, fall back to basic response
            if st.session_state.get("debug_mode", False):
                st.warning(f"Enhanced AI features unavailable. Using fallback response. Error: {str(e)}")
            return fallback_response
    
    # If AI Hub is not available, return fallback response
    return fallback_response

def render_department_insights(org: str = "cityA", org_display_name: str = "City A", restricted_departments: Optional[List[str]] = None, enable_debug: bool = False):
    """
    Render the Department Insights tab
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
        restricted_departments (Optional[List[str]]): If provided, only show these departments (for department managers)
        enable_debug (bool): If True, show debug information
    """
    # Set debug mode in session state
    if enable_debug and 'debug_mode' not in st.session_state:
        st.session_state['debug_mode'] = True
    st.markdown('<div class="sub-header">Department Performance Insights</div>', unsafe_allow_html=True)
    
    # Load department data
    try:
        df = load_org_data(org)
        
        # Ensure we have the organization column
        if 'Organization' not in df.columns:
            df['Organization'] = org
        
        has_real_data = not df.empty
    except Exception as e:
        st.error(f"Error loading department data: {e}")
        has_real_data = False
    
    if has_real_data:
        # Basic overview
        st.subheader("Department Overview")
        
        # Create summary metrics
        dept_count = df["Department"].nunique()
        fund_count = df["Fund"].nunique()
        total_budget = df["Budget"].sum()
        total_actual = df["Actual"].sum()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Departments", f"{dept_count}")
        col2.metric("Total Funds", f"{fund_count}")
        col3.metric("Total Budget", format_currency(total_budget))
        col4.metric("Total Actual", format_currency(total_actual))
        
        # Fiscal Year Filter
        fiscal_years = sorted(df["FiscalYear"].unique())
        selected_years = st.multiselect("Select Fiscal Years", fiscal_years, default=fiscal_years)
        
        if not selected_years:
            st.warning("Please select at least one fiscal year.")
            st.stop()
        
        # Filter data based on selected years
        filtered_df = df[df["FiscalYear"].isin(selected_years)]
        
        # Department Filter - filtered by user role if applicable
        available_depts = sorted(filtered_df["Department"].unique())
        
        # Get departments from GL database to ensure exact matches
        try:
            gl_db_path = "cityA_with_gl_accounts.db"
            if os.path.exists(gl_db_path):
                conn = sqlite3.connect(gl_db_path)
                gl_depts_query = "SELECT DISTINCT Department FROM DepartmentPerformance"
                gl_depts_df = pd.read_sql_query(gl_depts_query, conn)
                gl_depts = gl_depts_df['Department'].tolist()
                conn.close()
                
                # Create a mapping from overview departments to GL departments
                dept_mapping = {}
                for dept in available_depts:
                    exact_match = dept in gl_depts
                    if exact_match:
                        dept_mapping[dept] = dept
                    else:
                        # Find closest match
                        for gl_dept in gl_depts:
                            if dept in gl_dept or gl_dept in dept:
                                dept_mapping[dept] = gl_dept
                                break
                        # If no match found, keep original
                        if dept not in dept_mapping:
                            dept_mapping[dept] = dept
                
                # Add a note about department name mapping (only in debug mode)
                if st.session_state.get("debug_mode", False):
                    st.info("Department names have been synchronized with GL database for consistent analysis")
                
                # Store the mapping for later use
                if 'dept_mapping' not in st.session_state:
                    st.session_state['dept_mapping'] = dept_mapping
            else:
                # No GL database, use original departments
                dept_mapping = {dept: dept for dept in available_depts}
                st.session_state['dept_mapping'] = dept_mapping
        except Exception as e:
            st.warning(f"Could not synchronize departments with GL database: {e}")
            # Use original departments on error
            dept_mapping = {dept: dept for dept in available_depts} 
            st.session_state['dept_mapping'] = dept_mapping
        
        if restricted_departments:
            # Filter departments based on user access
            available_depts = [d for d in available_depts if d in restricted_departments]
            
            if not available_depts:
                st.error("You don't have access to any departments in the current selection.")
                st.stop()
                
            # For department managers, default to their department
            if len(available_depts) == 1:
                selected_dept = available_depts[0]
                st.info(f"Showing data for your department: {selected_dept}")
            else:
                selected_dept = st.selectbox("Select Department", available_depts)
        else:
            # For admin/finance users who can see all departments
            all_depts = ["All Departments"] + available_depts
            selected_dept = st.selectbox("Select Department", all_depts)
        
        # Store selected department in session state for AI access
        st.session_state['selected_dept'] = selected_dept
        
        if selected_dept != "All Departments":
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
            dept_title = selected_dept
        else:
            dept_title = "All Departments"
        
        # Calculate aggregated metrics
        dept_summary = filtered_df.groupby("Department").agg({
            "Budget": "sum",
            "Actual": "sum"
        }).reset_index()
        
        dept_summary["Variance"] = dept_summary["Budget"] - dept_summary["Actual"]
        dept_summary["Variance%"] = (dept_summary["Variance"] / dept_summary["Budget"]) * 100
        
        # Sort departments by budget
        dept_summary = dept_summary.sort_values(by="Budget", ascending=False)
        
        # Apply account mask parsing if applicable
        if "Account" in filtered_df.columns or "AccountNumber" in filtered_df.columns:
            # Get the expense account mask from settings
            expense_mask = get_mask_from_settings("Expense")
            
            if expense_mask:
                st.info(f"Using expense account mask: {expense_mask}")
                
                # Create expandable section for account details
                with st.expander("View Account Structure Details", expanded=False):
                    st.write("Account parsing is enabled. The system will interpret account codes according to the mask format.")
                    
                    account_col = "Account" if "Account" in filtered_df.columns else "AccountNumber"
                    
                    # Sample mask parsing for demonstration
                    if not filtered_df.empty:
                        try:
                            sample_account = str(filtered_df[account_col].iloc[0])
                            segments = parse_account(sample_account, expense_mask)
                            
                            st.write("Sample account parsing:")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"Account: {sample_account}")
                            with col2:
                                for segment, value in segments.items():
                                    st.write(f"{segment}: {value}")
                        except Exception as e:
                            st.warning(f"Error parsing account: {e}")
        
        # Create the budget allocation chart
        st.subheader(f"Budget Allocation - {dept_title}")
        
        try:
            if selected_dept == "All Departments":
                # Show all departments in a pie chart
                fig = px.pie(
                    dept_summary,
                    values="Budget",
                    names="Department",
                    title=f"{org_display_name} Budget Allocation by Department",
                    hole=0.3
                )
                
                fig.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)
                
                # Also create a bar chart for better comparison
                fig2 = px.bar(
                    dept_summary.head(10),  # Top 10 departments by budget
                    x="Department",
                    y=["Budget", "Actual"],
                    barmode="group",
                    title="Top 10 Departments - Budget vs. Actual",
                    labels={"value": "Amount ($)", "variable": "Type"}
                )
                
                st.plotly_chart(fig2, use_container_width=True)
                
                # Add AI analysis of department performance trends for all departments
                with st.expander("AI Department Comparison Analysis", expanded=False):
                    st.info("Get AI-powered comparison of all departments' performance")
                    if st.button("Generate Department Comparison Analysis"):
                        with st.spinner("Analyzing department performance data..."):
                            all_dept_prompt = f"Compare the budget performance across all departments in {org_display_name}. Identify the top performing and underperforming departments, key trends, and provide recommendations for resource allocation optimization."
                            ai_insights = generate_ai_commentary(dept_summary, all_dept_prompt)
                            st.markdown(ai_insights)
                
                # Add AI Q&A for organization-wide questions
                st.subheader("💬 Ask AI About All Departments")
                org_question = st.text_input("Ask a question about department performance across the organization:", key="org_question")
                if org_question:
                    with st.spinner("Analyzing your question..."):
                        qa_prompt = f"Based on the municipal financial performance data for all departments, answer this question: '{org_question}'\nOrganization: {org_display_name}\nFiscal Years: {', '.join(map(str, selected_years))}\nBe specific and use the data context if relevant."
                        ai_answer = generate_ai_commentary(filtered_df, qa_prompt)
                        st.markdown(ai_answer)
            else:
                # For a single department, show fund allocation
                fund_summary = filtered_df.groupby("Fund").agg({
                    "Budget": "sum",
                    "Actual": "sum"
                }).reset_index()
                
                fund_summary["Variance"] = fund_summary["Budget"] - fund_summary["Actual"]
                fund_summary["Variance%"] = (fund_summary["Variance"] / fund_summary["Budget"]) * 100
                
                # Sort funds by budget
                fund_summary = fund_summary.sort_values(by="Budget", ascending=False)
                
                # Show fund allocation as a pie chart
                fig = px.pie(
                    fund_summary,
                    values="Budget",
                    names="Fund",
                    title=f"{selected_dept} Budget Allocation by Fund",
                    hole=0.3
                )
                
                fig.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)
                
                # Also create a bar chart for funds
                fig2 = px.bar(
                    fund_summary,
                    x="Fund",
                    y=["Budget", "Actual"],
                    barmode="group",
                    title=f"{selected_dept} - Budget vs. Actual by Fund",
                    labels={"value": "Amount ($)", "variable": "Type"}
                )
                
                st.plotly_chart(fig2, use_container_width=True)
                
                # Add transaction analysis section
                st.markdown("---")
                st.subheader("GL Account Transactions Analysis")
                
                # Display transaction analysis for the selected department
                with st.expander("View Transaction Details and GL Account Balances", expanded=True):
                    st.markdown(f"""
                    This section shows detailed transaction data for {selected_dept}, including:
                    - GL account balances and transaction counts
                    - Monthly transaction trends
                    - Detailed transaction list with filtering options
                    """)
                    
                    # Use the selected department code for transaction analysis
                    display_department_transaction_analysis(selected_dept)
                
                # Add AI insights for department or fund allocation
                with st.expander("AI Budget Allocation Insights", expanded=False):
                    st.info("Get AI-powered insights about budget allocation patterns")
                    if st.button("Generate Budget Allocation Insights"):
                        with st.spinner("Analyzing budget allocation data..."):
                            if selected_dept == "All Departments":
                                dept_prompt = f"Analyze the budget allocation across departments for {org_display_name}. Identify which departments have the highest budget allocation and provide insights on potential resource distribution optimization."
                                ai_insights = generate_ai_commentary(dept_summary, dept_prompt)
                            else:
                                fund_prompt = f"Analyze the fund allocation for the {selected_dept} department. Identify key patterns in how funds are distributed and provide 3-4 specific insights or recommendations."
                                ai_insights = generate_ai_commentary(fund_summary, fund_prompt)
                            st.markdown(ai_insights)
        except Exception as e:
            st.error(f"Error creating charts: {e}")
        
        # Budget vs. Actual Comparison
        st.subheader("Budget vs. Actual Comparison")
        
        try:
            # Performance metrics comparison
            if selected_dept == "All Departments":
                # Calculate overall variance
                total_variance = dept_summary["Variance"].sum()
                total_variance_pct = (total_variance / dept_summary["Budget"].sum()) * 100
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total Variance", format_currency(total_variance))
                
                with col2:
                    st.metric("Variance Percentage", format_percentage(total_variance_pct))
                
                # Top 5 departments with highest variance
                top_variance = dept_summary.sort_values(by="Variance", ascending=False).head(5)
                
                st.subheader("Top 5 Departments by Underspending")
                
                for _, row in top_variance.iterrows():
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                        <h4>{row['Department']}</h4>
                        <p><strong>Budget:</strong> {format_currency(row['Budget'])}</p>
                        <p><strong>Actual:</strong> {format_currency(row['Actual'])}</p>
                        <p><strong>Variance:</strong> {format_currency(row['Variance'])} ({format_percentage(row['Variance%'])})</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Bottom 5 departments with lowest variance
                bottom_variance = dept_summary.sort_values(by="Variance", ascending=True).head(5)
                
                st.subheader("Top 5 Departments by Overspending")
                
                for _, row in bottom_variance.iterrows():
                    variance_color = "red" if row['Variance'] < 0 else "green"
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                        <h4>{row['Department']}</h4>
                        <p><strong>Budget:</strong> {format_currency(row['Budget'])}</p>
                        <p><strong>Actual:</strong> {format_currency(row['Actual'])}</p>
                        <p><strong>Variance:</strong> <span style="color: {variance_color};">{format_currency(row['Variance'])} ({format_percentage(row['Variance%'])})</span></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # For a single department
                # Get fiscal year data
                year_data = filtered_df.groupby("FiscalYear").agg({
                    "Budget": "sum",
                    "Actual": "sum"
                }).reset_index()
                
                year_data["Variance"] = year_data["Budget"] - year_data["Actual"]
                year_data["Variance%"] = (year_data["Variance"] / year_data["Budget"]) * 100
                
                # Create a line chart for trends over years
                fig3 = go.Figure()
                
                fig3.add_trace(go.Scatter(
                    x=year_data["FiscalYear"],
                    y=year_data["Budget"],
                    mode="lines+markers",
                    name="Budget"
                ))
                
                fig3.add_trace(go.Scatter(
                    x=year_data["FiscalYear"],
                    y=year_data["Actual"],
                    mode="lines+markers",
                    name="Actual"
                ))
                
                fig3.update_layout(
                    title=f"{selected_dept} - Budget and Actual Trends",
                    xaxis_title="Fiscal Year",
                    yaxis_title="Amount ($)"
                )
                
                st.plotly_chart(fig3, use_container_width=True)
                
                # Add AI analysis for department performance trends
                with st.expander("AI Department Performance Analysis", expanded=False):
                    st.info("Get AI-powered analysis of this department's performance trends across fiscal years")
                    if st.button("Generate Performance Trends Analysis"):
                        with st.spinner("Analyzing performance data..."):
                            perf_prompt = f"Analyze the performance trends for the {selected_dept} department across fiscal years. Identify patterns in budget vs actual spending, evaluate consistency in performance, and provide 3-4 specific insights or recommendations for budget planning."
                            ai_insights = generate_ai_commentary(year_data, perf_prompt)
                            st.markdown(ai_insights)
                
                # Add AI Q&A for department-specific questions
                st.subheader("💬 Ask AI About This Department")
                user_question = st.text_input("Ask a question about this department's budget data:", key="dept_question")
                if user_question:
                    with st.spinner("Analyzing your question..."):
                        qa_prompt = f"Based on this municipal department's financial performance data, answer this question: '{user_question}'\nDepartment: {selected_dept}\nFiscal Years: {', '.join(map(str, selected_years))}\nBe specific and use the data context if relevant."
                        ai_answer = generate_ai_commentary(filtered_df, qa_prompt)
                        st.markdown(ai_answer)
                
                # Show monthly data if available
                if "Month" in filtered_df.columns:
                    # Group by month
                    month_data = filtered_df.groupby("Month").agg({
                        "Budget": "sum",
                        "Actual": "sum"
                    }).reset_index()
                    
                    # Sort by month
                    month_order = ["January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"]
                    month_map = {month: i for i, month in enumerate(month_order)}
                    
                    month_data["MonthNum"] = month_data["Month"].map(month_map)
                    month_data = month_data.sort_values(by="MonthNum")
                    
                    # Create a bar chart for monthly spending
                    fig4 = px.bar(
                        month_data,
                        x="Month",
                        y=["Budget", "Actual"],
                        barmode="group",
                        title=f"{selected_dept} - Monthly Budget and Spending",
                        labels={"value": "Amount ($)", "variable": "Type"}
                    )
                    
                    # Set the x-axis category order
                    fig4.update_layout(xaxis={"categoryorder": "array", "categoryarray": month_order})
                    
                    st.plotly_chart(fig4, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating comparative visualizations: {e}")
        
        # Enhanced GL Account Drilldown (only for specific departments)
        if selected_dept != "All Departments":
            st.subheader("GL Account Drilldown")
            st.markdown("Detailed GL account analysis allows you to explore spending patterns at the account level.")
            
            try:
                # Get database path for the organization
                DB_PATH = "cityA_with_gl_accounts.db"  # Default path
                
                if os.path.exists(DB_PATH):
                    db_path = DB_PATH
                else:
                    db_path = get_db_path_for_org(org)
                
                # Only show debug information in debug mode
                if st.session_state.get('debug_mode', False):
                    st.write(f"Using database: {db_path}")
                    
                    # Print available departments for debugging
                    try:
                        conn = sqlite3.connect(db_path)
                        depts_query = "SELECT DISTINCT Department FROM DepartmentPerformance"
                        depts_df = pd.read_sql_query(depts_query, conn)
                        st.write("Available departments in GL database:", depts_df['Department'].tolist())
                        conn.close()
                    except Exception as e:
                        st.error(f"Error checking departments: {e}")
                
                # First try direct database query for GL accounts
                try:
                    # Connect to the database directly first
                    conn = sqlite3.connect(db_path)
                    
                    # Use the department mapping previously created
                    if 'dept_mapping' in st.session_state and selected_dept in st.session_state['dept_mapping']:
                        dept_name_to_query = st.session_state['dept_mapping'][selected_dept]
                        
                        # Add an info message only if the mapping is different from the selected department (in debug mode)
                        if dept_name_to_query != selected_dept and st.session_state.get("debug_mode", False):
                            st.info(f"Using database department name: '{dept_name_to_query}'")
                    else:
                        # Fallback to direct database check
                        depts_df = pd.read_sql_query("SELECT DISTINCT Department FROM DepartmentPerformance", conn)
                        dept_list = depts_df['Department'].tolist()
                        
                        # Check if the selected department is in database as-is or if it's a partial match
                        if selected_dept in dept_list:
                            # Exact match found
                            dept_name_to_query = selected_dept
                        else:
                            # Check for partial matches (e.g., "Police" in "Police Department")
                            partial_matches = [dept for dept in dept_list if selected_dept in dept or dept in selected_dept]
                            if partial_matches:
                                dept_name_to_query = partial_matches[0]
                                # Only show in debug mode
                                if st.session_state.get('debug_mode', False):
                                    st.info(f"Using similar department name: '{dept_name_to_query}' instead of '{selected_dept}'")
                            else:
                                dept_name_to_query = selected_dept
                    
                    # Use explicit column selection and single quotes for the department name
                    gl_query = f"""
                        SELECT 
                            Department, Fund, FiscalYear, Month, 
                            Budget, Actual, AccountCode, AccountName 
                        FROM DepartmentPerformance 
                        WHERE Department = '{dept_name_to_query}'
                    """
                    gl_data = pd.read_sql_query(gl_query, conn)
                    conn.close()
                    
                    # Debug info (only show in debug mode)
                    if st.session_state.get("debug_mode", False):
                        st.write(f"Query: {gl_query}")
                        st.write(f"Found {len(gl_data)} GL records")
                    
                    # If we have data with AccountCode and AccountName, use it
                    if not gl_data.empty and 'AccountCode' in gl_data.columns and 'AccountName' in gl_data.columns:
                        if st.session_state.get("debug_mode", False):
                            st.success(f"Found {len(gl_data)} GL account records for {selected_dept}")
                    else:
                        # If direct query didn't work, try the module (debug mode only)
                        if st.session_state.get("debug_mode", False):
                            st.warning("No GL data found with direct query, trying module...")
                        gl_data = load_gl_data(db_path, selected_dept)
                except Exception as e:
                    # Only show warning in debug mode
                    if st.session_state.get("debug_mode", False):
                        st.warning(f"Direct database query failed: {e}. Trying module...")
                    # If direct query failed, try the module
                    gl_data = load_gl_data(db_path, selected_dept)
                
                if gl_data is not None and not gl_data.empty:
                    # Use the GL drilldown module's data
                    st.subheader(f"GL Account Analysis for {selected_dept}")
                    
                    # Check if AccountType column exists
                    if 'AccountType' in gl_data.columns:
                        # Group by account type
                        account_types = gl_data["AccountType"].unique()
                        
                        if len(account_types) > 0:
                            # Show GL data by account type
                            account_type = st.selectbox("Select Account Type", 
                                                      ["All"] + sorted(account_types.tolist()))
                            
                            # Filter by account type if selected
                            if account_type != "All":
                                filtered_gl_data = gl_data[gl_data["AccountType"] == account_type]
                            else:
                                filtered_gl_data = gl_data
                        else:
                            filtered_gl_data = gl_data
                    else:
                        # Create derived account types based on account code
                        # This is a fallback when AccountType isn't in the table
                        st.info("No account type information available, deriving from account codes using masks.")
                        
                        # Get account masks from settings
                        balance_sheet_mask = get_mask_from_settings("BalanceSheet")
                        revenue_mask = get_mask_from_settings("Revenue")
                        expense_mask = get_mask_from_settings("Expense")
                        
                        # Initialize derived type column with default
                        gl_data['DerivedType'] = 'Other'
                        
                        # Function to determine account type based on first digit and masks
                        def determine_account_type(account_code):
                            account_str = str(account_code)
                            # Basic classification by first digit as fallback
                            if account_str.startswith('4') or account_str.startswith('3'):
                                return 'Revenue'
                            elif account_str.startswith('5') or account_str.startswith('6'):
                                return 'Expense'
                            elif account_str.startswith('1') or account_str.startswith('2'):
                                return 'Balance Sheet'
                            else:
                                return 'Other'
                        
                        # Apply basic classification first
                        gl_data['DerivedType'] = gl_data['AccountCode'].apply(determine_account_type)
                        
                        # Apply full account structure parsing if masks are available
                        account_col = 'AccountCode'
                        
                        # Process different types of accounts using appropriate masks
                        try:
                            # Apply balance sheet mask to balance sheet accounts
                            if balance_sheet_mask:
                                balance_accounts = gl_data[gl_data['DerivedType'] == 'Balance Sheet']
                                if not balance_accounts.empty:
                                    try:
                                        # Parse balance sheet accounts
                                        balance_segments = balance_accounts[account_col].astype(str).apply(
                                            lambda x: pd.Series(parse_account(x, balance_sheet_mask))
                                        )
                                        # Add parsed segments to the original dataframe
                                        for col in balance_segments.columns:
                                            gl_data.loc[gl_data['DerivedType'] == 'Balance Sheet', col] = balance_segments[col].values
                                    except Exception as e:
                                        st.warning(f"Error parsing balance sheet accounts: {e}")
                            
                            # Apply revenue mask to revenue accounts
                            if revenue_mask:
                                revenue_accounts = gl_data[gl_data['DerivedType'] == 'Revenue']
                                if not revenue_accounts.empty:
                                    try:
                                        # Parse revenue accounts
                                        revenue_segments = revenue_accounts[account_col].astype(str).apply(
                                            lambda x: pd.Series(parse_account(x, revenue_mask))
                                        )
                                        # Add parsed segments to the original dataframe
                                        for col in revenue_segments.columns:
                                            gl_data.loc[gl_data['DerivedType'] == 'Revenue', col] = revenue_segments[col].values
                                    except Exception as e:
                                        st.warning(f"Error parsing revenue accounts: {e}")
                            
                            # Apply expense mask to expense accounts
                            if expense_mask:
                                expense_accounts = gl_data[gl_data['DerivedType'] == 'Expense']
                                if not expense_accounts.empty:
                                    try:
                                        # Parse expense accounts
                                        expense_segments = expense_accounts[account_col].astype(str).apply(
                                            lambda x: pd.Series(parse_account(x, expense_mask))
                                        )
                                        # Add parsed segments to the original dataframe
                                        for col in expense_segments.columns:
                                            gl_data.loc[gl_data['DerivedType'] == 'Expense', col] = expense_segments[col].values
                                    except Exception as e:
                                        st.warning(f"Error parsing expense accounts: {e}")
                        except Exception as e:
                            st.warning(f"Error during account parsing: {e}")
                            # Fallback to basic classification
                        
                        # Use the derived types
                        derived_types = gl_data["DerivedType"].unique()
                        account_type = st.selectbox("Select Account Type", 
                                                  ["All"] + sorted(derived_types.tolist()))
                        
                        # Add segment-based filtering options for parsed account codes
                        if 'Fund' in gl_data.columns:
                            fund_values = gl_data['Fund'].dropna().unique()
                            if len(fund_values) > 0:
                                st.subheader("Filter by Account Segments")
                                selected_fund = st.selectbox("Select Fund", ["All"] + sorted(fund_values.tolist()))
                                if selected_fund != "All":
                                    gl_data = gl_data[gl_data['Fund'] == selected_fund]
                        
                        # Add Department filter if available from account parsing
                        if 'Dept' in gl_data.columns:
                            dept_values = gl_data['Dept'].dropna().unique()
                            if len(dept_values) > 0:
                                selected_dept_code = st.selectbox("Select Department Code", ["All"] + sorted(dept_values.tolist()))
                                if selected_dept_code != "All":
                                    gl_data = gl_data[gl_data['Dept'] == selected_dept_code]
                        
                        # Add Object filter if available from account parsing
                        if 'Object' in gl_data.columns:
                            object_values = gl_data['Object'].dropna().unique()
                            if len(object_values) > 0:
                                selected_object = st.selectbox("Select Object Code", ["All"] + sorted(object_values.tolist()))
                                if selected_object != "All":
                                    gl_data = gl_data[gl_data['Object'] == selected_object]
                        
                        # Filter by account type if selected
                        if account_type != "All":
                            filtered_gl_data = gl_data[gl_data["DerivedType"] == account_type]
                        else:
                            filtered_gl_data = gl_data
                        
                        # Group by account for visualization
                        account_summary = filtered_gl_data.groupby(["AccountCode", "AccountName"]).agg({
                            "Budget": "sum",
                            "Actual": "sum"
                        }).reset_index()
                        
                        account_summary["Variance"] = account_summary["Budget"] - account_summary["Actual"]
                        account_summary["Variance%"] = (account_summary["Variance"] / account_summary["Budget"]) * 100
                        
                        # Sort by budget amount
                        account_summary = account_summary.sort_values(by="Budget", ascending=False)
                        
                        # Show top accounts visualization
                        st.subheader(f"Top GL Accounts - {account_type if account_type != 'All' else 'All Types'}")
                        
                        # Create visualization of GL accounts
                        fig_gl = px.bar(
                            account_summary.head(10),  # Show top 10 accounts by budget
                            x="AccountName",
                            y=["Budget", "Actual"],
                            barmode="group",
                            title=f"Top GL Accounts for {selected_dept}",
                            labels={"value": "Amount ($)", "variable": "Type"}
                        )
                        
                        fig_gl.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig_gl, use_container_width=True)
                        
                        # Format and display the GL account data table
                        st.subheader("GL Account Details")
                        
                        # Add variance color formatting
                        def highlight_variance(val):
                            if isinstance(val, float):
                                if val < 0:
                                    return 'color: red'
                                elif val > 0:
                                    return 'color: green'
                            return ''
                        
                        # Format the table data
                        display_df = account_summary.copy()
                        display_df["Budget"] = display_df["Budget"].apply(lambda x: format_currency(x))
                        display_df["Actual"] = display_df["Actual"].apply(lambda x: format_currency(x))
                        display_df["Variance"] = display_df["Variance"].apply(lambda x: format_currency(x))
                        display_df["Variance%"] = display_df["Variance%"].apply(lambda x: format_percentage(x))
                        
                        # GL Account Data with Advanced Filtering
                        st.subheader("GL Account Data with Filters")
                        
                        # Import advanced filtering components
                        from advanced_filters import create_advanced_filter_component, display_filtered_dataframe, create_summary_metrics
                        
                        # Apply advanced filtering to the GL account data
                        filtered_gl_data = create_advanced_filter_component(
                            df=account_summary,
                            key_prefix=f"dept_gl_{selected_dept}",
                            default_sort_column="Budget",
                            items_per_page=20
                        )
                        
                        # Display summary metrics
                        create_summary_metrics(filtered_gl_data, account_summary)
                        
                        # Display the filtered data
                        display_filtered_dataframe(
                            filtered_gl_data,
                            key_prefix=f"dept_gl_display_{selected_dept}",
                            height=400
                        )
                        
                        with filter_columns[1]:
                            # Budget range filter
                            budget_min = float(filterable_data["Budget"].min())
                            budget_max = float(filterable_data["Budget"].max())
                            if budget_min != budget_max:
                                budget_range = st.slider(
                                    "Budget Range",
                                    min_value=budget_min,
                                    max_value=budget_max,
                                    value=(budget_min, budget_max),
                                    key=f"gl_budget_filter_{selected_dept}"
                                )
                                filterable_data = filterable_data[
                                    (filterable_data["Budget"] >= budget_range[0]) & 
                                    (filterable_data["Budget"] <= budget_range[1])
                                ]
                        
                        with filter_columns[2]:
                            # Variance filter
                            variance_min = float(filterable_data["Variance"].min())
                            variance_max = float(filterable_data["Variance"].max())
                            if variance_min != variance_max:
                                variance_range = st.slider(
                                    "Variance Range",
                                    min_value=variance_min,
                                    max_value=variance_max,
                                    value=(variance_min, variance_max),
                                    key=f"gl_variance_filter_{selected_dept}"
                                )
                                filterable_data = filterable_data[
                                    (filterable_data["Variance"] >= variance_range[0]) & 
                                    (filterable_data["Variance"] <= variance_range[1])
                                ]
                        
                        with filter_columns[3]:
                            # Variance percentage filter
                            var_pct_min = float(filterable_data["Variance%"].min())
                            var_pct_max = float(filterable_data["Variance%"].max())
                            if var_pct_min != var_pct_max:
                                var_pct_range = st.slider(
                                    "Variance % Range",
                                    min_value=var_pct_min,
                                    max_value=var_pct_max,
                                    value=(var_pct_min, var_pct_max),
                                    key=f"gl_var_pct_filter_{selected_dept}"
                                )
                                filterable_data = filterable_data[
                                    (filterable_data["Variance%"] >= var_pct_range[0]) & 
                                    (filterable_data["Variance%"] <= var_pct_range[1])
                                ]
                        
                        # Format the filtered data
                        display_df = filterable_data.copy()
                        display_df["Budget"] = display_df["Budget"].apply(lambda x: format_currency(x))
                        display_df["Actual"] = display_df["Actual"].apply(lambda x: format_currency(x))
                        display_df["Variance"] = display_df["Variance"].apply(lambda x: format_currency(x))
                        display_df["Variance%"] = display_df["Variance%"].apply(lambda x: format_percentage(x))
                        
                        # Show the data with Excel-style filtering
                        st.data_editor(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                            disabled=True,
                            height=400,
                            column_config={
                                "Budget": st.column_config.NumberColumn(format="$%.2f"),
                                "Actual": st.column_config.NumberColumn(format="$%.2f"),
                                "Variance": st.column_config.NumberColumn(format="$%.2f"),
                                "Variance%": st.column_config.NumberColumn(format="%.1f%%")
                            }
                        )
                        
                        # Add download button for GL account data
                        csv = account_summary.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Download GL Account Data",
                            csv,
                            file_name=f"{selected_dept}_gl_accounts.csv",
                            mime="text/csv"
                        )
                        
                        # === AI-Powered Forecasting Section ===
                        with st.expander("AI Forecasting Tool"):
                            st.markdown("Use this tool to project future values based on historical trends.")

                            # Check if we have AccountName in the data
                            if 'AccountName' in filtered_gl_data.columns:
                                account_options = filtered_gl_data["AccountName"].unique().tolist()
                                selected_account = st.selectbox("Select Account", account_options)

                                forecast_years = st.slider("Years to Forecast", 1, 5, 3)
                                
                                # Filter data for the selected account
                                forecast_df = filtered_gl_data[filtered_gl_data["AccountName"] == selected_account]
                                
                                # Add a fiscal year column if it doesn't exist
                                if 'FiscalYear' not in forecast_df.columns and 'Date' in forecast_df.columns:
                                    forecast_df['FiscalYear'] = pd.to_datetime(forecast_df['Date']).dt.year
                                
                                # Generate forecast using the AI Hub function
                                if 'FiscalYear' in forecast_df.columns and len(forecast_df) > 0:
                                    forecast_data = generate_forecast(forecast_df, year_col="FiscalYear", value_col="Amount", forecast_years=forecast_years)

                                    if not forecast_data.empty:
                                        st.subheader("Forecast Results")
                                        st.dataframe(forecast_data)

                                        # Create a line chart showing actual and forecast data
                                        fig = px.line(forecast_data, x="FiscalYear", y="Amount", color="Source", markers=True,
                                                      title=f"{selected_account} - Forecast vs. Actual")
                                        st.plotly_chart(fig, use_container_width=True)

                                        # Generate AI analysis of the forecast
                                        forecast_prompt = (
                                            f"Forecast the next {forecast_years} years for account '{selected_account}' based on the historical trends "
                                            f"from the department '{selected_dept}'. Provide explanation and risks."
                                        )
                                        st.markdown("### Forecast Analysis")
                                        st.markdown(ask_ai(forecast_prompt, forecast_df))
                                    else:
                                        st.warning("Not enough data to generate a forecast.")
                                else:
                                    st.warning("Account data doesn't contain fiscal year information required for forecasting.")
                            else:
                                st.warning("Account data is not available for forecasting.")
                else:
                    # Fallback to the basic GL account data from the database
                    try:
                        # Connect to the database
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        
                        # Check for the database schema using column names
                        cursor.execute("PRAGMA table_info(DepartmentPerformance)")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        # Check if we're dealing with the new or old schema
                        has_gl_detail = 'AccountCode' in columns and 'AccountName' in columns
                        is_new_schema = 'DepartmentCode' in columns and 'DepartmentName' in columns
                        
                        if has_gl_detail:
                            if is_new_schema:
                                # Use the department mapping previously created or find similar match
                                if 'dept_mapping' in st.session_state and selected_dept in st.session_state['dept_mapping']:
                                    dept_name_to_query = st.session_state['dept_mapping'][selected_dept]
                                else:
                                    # Get the available departments
                                    depts_query = "SELECT DISTINCT DepartmentName FROM DepartmentPerformance"
                                    depts_df = pd.read_sql_query(depts_query, conn)
                                    dept_list = depts_df['DepartmentName'].tolist()
                                    
                                    # Check for matches
                                    if selected_dept in dept_list:
                                        dept_name_to_query = selected_dept
                                    else:
                                        # Find the closest match
                                        partial_matches = [dept for dept in dept_list if selected_dept in dept or dept in selected_dept]
                                        if partial_matches:
                                            dept_name_to_query = partial_matches[0]
                                            # Only show in debug mode
                                            if st.session_state.get('debug_mode', False):
                                                st.info(f"Using similar department name: '{dept_name_to_query}' instead of '{selected_dept}'")
                                        else:
                                            dept_name_to_query = selected_dept
                                
                                # For the new schema, we need to use DepartmentName
                                gl_query = f"""
                                    SELECT 
                                        DepartmentName as Department, 
                                        FundName as Fund, 
                                        FiscalYear, 
                                        AccountCode, 
                                        AccountName,
                                        AccountType,
                                        Mask,
                                        SUM(Budget) as Budget, 
                                        SUM(Actual) as Actual
                                    FROM DepartmentPerformance
                                    WHERE DepartmentName = '{dept_name_to_query}'
                                    GROUP BY DepartmentName, FundName, FiscalYear, AccountCode, AccountName, AccountType, Mask
                                """
                                gl_df = pd.read_sql_query(gl_query, conn)
                                
                                # Check if we got data
                                if not gl_df.empty:
                                    # Filter out Revenue and Expense accounts only
                                    operating_df = gl_df[gl_df["AccountType"] != "Balance"].copy() if "AccountType" in gl_df.columns else gl_df.copy()
                                    
                                    # Handle Revenue and Expense accounts
                                    if not operating_df.empty:
                                        st.subheader("Revenue and Expense Accounts")
                                        
                                        # Group data by account with account type information
                                        operating_summary = operating_df.groupby(["AccountCode", "AccountName"]).agg({
                                            "Budget": "sum",
                                            "Actual": "sum"
                                        }).reset_index()
                                        
                                        operating_summary["Variance"] = operating_summary["Budget"] - operating_summary["Actual"]
                                        operating_summary["Variance%"] = (operating_summary["Variance"] / operating_summary["Budget"]) * 100
                                        
                                        # Sort by budget amount
                                        operating_summary = operating_summary.sort_values(by="Budget", ascending=False)
                                        
                                        # Create visualization of GL accounts
                                        fig_gl = px.bar(
                                            operating_summary.head(15),  # Show top 15 accounts by budget
                                            x="AccountName",
                                            y=["Budget", "Actual"],
                                            barmode="group",
                                            title=f"Top GL Accounts for {selected_dept}",
                                            labels={"value": "Amount ($)", "variable": "Type"}
                                        )
                                        
                                        fig_gl.update_layout(xaxis_tickangle=-45)
                                        st.plotly_chart(fig_gl, use_container_width=True)
                                        
                                        # Add variance color formatting
                                        def highlight_variance(val):
                                            if isinstance(val, float):
                                                if val < 0:
                                                    return 'color: red'
                                                elif val > 0:
                                                    return 'color: green'
                                            return ''
                                        
                                        # Format the table data
                                        display_df = operating_summary.copy()
                                        display_df["Budget"] = display_df["Budget"].apply(lambda x: format_currency(x))
                                        display_df["Actual"] = display_df["Actual"].apply(lambda x: format_currency(x))
                                        display_df["Variance"] = display_df["Variance"].apply(lambda x: format_currency(x))
                                        display_df["Variance%"] = display_df["Variance%"].apply(lambda x: format_percentage(x))
                                        
                                        # Show the data with sorting and filtering
                                        st.dataframe(display_df.style.applymap(highlight_variance, subset=["Variance%"]))
                                        
                                        # Add download button for GL account data
                                        csv = operating_summary.to_csv(index=False).encode("utf-8")
                                        st.download_button(
                                            "Download GL Account Data",
                                            csv,
                                            file_name=f"{selected_dept}_gl_accounts.csv",
                                            mime="text/csv"
                                        )
                                    else:
                                        st.info("No GL account data available for the selected department.")
                                else:
                                    st.info("No GL account data available for the selected department.")
                            else:
                                # For old schema
                                has_gl_accounts = "AccountCode" in columns and "AccountName" in columns
                                
                                if has_gl_accounts:
                                    # Get the available departments
                                    depts_query = "SELECT DISTINCT Department FROM DepartmentPerformance"
                                    depts_df = pd.read_sql_query(depts_query, conn)
                                    dept_list = depts_df['Department'].tolist()
                                    
                                    # Check if the selected department is in database as-is or if it's a partial match
                                    if selected_dept in dept_list:
                                        # Exact match found
                                        dept_name_to_query = selected_dept
                                    else:
                                        # Check for partial matches (e.g., "Police" in "Police Department")
                                        partial_matches = [dept for dept in dept_list if selected_dept in dept or dept in selected_dept]
                                        if partial_matches:
                                            dept_name_to_query = partial_matches[0]
                                            # Only show in debug mode
                                            if st.session_state.get('debug_mode', False):
                                                st.info(f"Using similar department name: '{dept_name_to_query}' instead of '{selected_dept}'")
                                        else:
                                            dept_name_to_query = selected_dept
                                    
                                    # Use the existing query for old schema
                                    gl_query = f"""
                                        SELECT Department, Fund, FiscalYear, AccountCode, AccountName, 
                                               SUM(Budget) as Budget, SUM(Actual) as Actual
                                        FROM DepartmentPerformance
                                        WHERE Department = '{dept_name_to_query}'
                                        GROUP BY Department, Fund, FiscalYear, AccountCode, AccountName
                                    """
                                    gl_df = pd.read_sql_query(gl_query, conn)
                                    
                                    # Continue with existing functionality
                                    if not gl_df.empty:
                                        # Group data by account
                                        gl_summary = gl_df.groupby(["AccountCode", "AccountName"]).agg({
                                            "Budget": "sum",
                                            "Actual": "sum"
                                        }).reset_index()
                                        
                                        gl_summary["Variance"] = gl_summary["Budget"] - gl_summary["Actual"]
                                        gl_summary["Variance%"] = (gl_summary["Variance"] / gl_summary["Budget"]) * 100
                                        
                                        # Sort by budget amount
                                        gl_summary = gl_summary.sort_values(by="Budget", ascending=False)
                                        
                                        # Create visualization of GL accounts
                                        fig_gl = px.bar(
                                            gl_summary.head(15),  # Show top 15 accounts by budget
                                            x="AccountName",
                                            y=["Budget", "Actual"],
                                            barmode="group",
                                            title=f"Top GL Accounts for {selected_dept}",
                                            labels={"value": "Amount ($)", "variable": "Type"}
                                        )
                                        
                                        fig_gl.update_layout(xaxis_tickangle=-45)
                                        st.plotly_chart(fig_gl, use_container_width=True)
                                        
                                        # Show data table with GL account details
                                        st.markdown("### GL Account Details")
                                        
                                        # Add variance color formatting
                                        def highlight_variance(val):
                                            if isinstance(val, float):
                                                if val < 0:
                                                    return 'color: red'
                                                elif val > 0:
                                                    return 'color: green'
                                            return ''
                                        
                                        # Format the table data
                                        display_df = gl_summary.copy()
                                        display_df["Budget"] = display_df["Budget"].apply(lambda x: format_currency(x))
                                        display_df["Actual"] = display_df["Actual"].apply(lambda x: format_currency(x))
                                        display_df["Variance"] = display_df["Variance"].apply(lambda x: format_currency(x))
                                        display_df["Variance%"] = display_df["Variance%"].apply(lambda x: format_percentage(x))
                                        
                                        # Show the data with sorting and filtering
                                        st.dataframe(display_df.style.applymap(highlight_variance, subset=["Variance%"]))
                                        
                                        # Add download button for GL account data
                                        csv = gl_summary.to_csv(index=False).encode("utf-8")
                                        st.download_button(
                                            "Download GL Account Data",
                                            csv,
                                            file_name=f"{selected_dept}_gl_accounts.csv",
                                            mime="text/csv"
                                        )
                                    else:
                                        st.info("No GL account data available for the selected department.")
                                else:
                                    st.info("GL account data is not available in the current database schema.")
                        else:
                            st.info("GL account data is not available in the current database schema.")
                    except Exception as e:
                        st.error(f"Error loading GL account data: {e}")
            except Exception as e:
                st.error(f"Error in GL account analysis: {e}")
        
        # Monthly Spending Patterns (if date information is available)
        if "Month" in filtered_df.columns and selected_dept != "All Departments":
            st.subheader("Monthly Spending Patterns")
            
            try:
                # Create a monthly spending breakdown
                monthly_data = filtered_df.groupby(["Month", "Fund"]).agg({
                    "Budget": "sum",
                    "Actual": "sum"
                }).reset_index()
                
                # Check how many unique months we have
                unique_months = monthly_data["Month"].nunique()
                
                # Sort months chronologically
                month_order = ["January", "February", "March", "April", "May", "June",
                              "July", "August", "September", "October", "November", "December"]
                month_map = {month: i for i, month in enumerate(month_order)}
                
                monthly_data["MonthNum"] = monthly_data["Month"].map(month_map)
                monthly_data = monthly_data.sort_values(by="MonthNum")
                
                # Create a heatmap for monthly spending by fund
                pivot_data = monthly_data.pivot_table(
                    values="Actual",
                    index="Fund",
                    columns="Month",
                    aggfunc="sum"
                ).fillna(0)
                
                # Reorder columns to be chronological
                ordered_months = [m for m in month_order if m in pivot_data.columns]
                pivot_data = pivot_data[ordered_months]
                
                # Create a heatmap
                fig5 = go.Figure(data=go.Heatmap(
                    z=pivot_data.values,
                    x=pivot_data.columns,
                    y=pivot_data.index,
                    colorscale="Blues",
                    hoverongaps=False
                ))
                
                fig5.update_layout(
                    title=f"{selected_dept} - Monthly Spending by Fund",
                    xaxis_title="Month",
                    yaxis_title="Fund"
                )
                
                st.plotly_chart(fig5, use_container_width=True)
                
                # Show data table
                st.subheader("Monthly Spending Data")
                
                display_data = monthly_data.pivot_table(
                    values="Actual",
                    index="Fund",
                    columns="Month",
                    aggfunc="sum"
                ).fillna(0)
                
                # Format the data as currency
                for col in display_data.columns:
                    display_data[col] = display_data[col].apply(lambda x: format_currency(x))
                
                st.dataframe(display_data)
                
                # Add download button for monthly data
                csv = monthly_data.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📅 Download Monthly Data",
                    csv,
                    file_name=f"{selected_dept}_monthly_data.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"Error analyzing monthly data: {e}")