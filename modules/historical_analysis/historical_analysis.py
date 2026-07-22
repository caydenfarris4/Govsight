"""
Historical Analysis Module

This module handles all functionality related to the Historical Analysis tab, including:
- Budget vs. actual spending analysis
- Trend visualization and forecasting
- Custom SQL query execution
- Data export functionality
- Role-based department access
- Enhanced reporting with comprehensive Plotly visualizations

ENHANCED REPORTING FEATURES:
- Executive summaries with AI-generated insights
- Multi-year trend analysis with forecasting
- Year-over-year comparison charts
- Historical performance metrics
- Comprehensive PDF reports with embedded charts
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import openai

# Import mask parser for account code interpretation
from modules.utils.mask_parser import get_mask_from_settings, parse_account

# Import database functions from db_connection.py
from modules.database.db_connection import (
    load_org_data, 
    run_dashboard_query,
    format_currency, 
    format_percentage
)

# Import security functions from admin_panel
from modules.admin.admin_panel import get_user_departments, is_admin, is_finance_director

# Import report generator
import modules.reports.summary_report_generator as report_gen

# Import new centralized reporting integration
try:
    from modules.vatica.reports_integration import vatica_reports
    REPORTS_INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import reports integration: {e}")
    REPORTS_INTEGRATION_AVAILABLE = False
    vatica_reports = None

def generate_ai_commentary(df, prompt=None):
    """
    Generate AI commentary on budget data
    
    Args:
        df (DataFrame): pandas DataFrame with budget data
        prompt (str, optional): User prompt for specific analysis. Defaults to None.
        
    Returns:
        str: AI commentary on the data
    """
    # Create a fallback response in case AI is not available
    fallback_response = """
    Based on the financial data analysis:
    
    1. Look for departments with consistent underspending that may have budget adjustment opportunities
    2. Compare actual vs. budgeted amounts to identify areas needing better forecasting
    3. Track year-over-year trends to identify seasonal patterns
    4. Consider areas with highest variance for potential budget reallocation
    """
    
    # Check if OpenAI integration is available
    try:
        import os
        import openai
        OPENAI_AVAILABLE = True
    except ImportError:
        OPENAI_AVAILABLE = False
    
    if not OPENAI_AVAILABLE:
        return fallback_response
    
    try:
        # Get the API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = st.secrets.get("OPENAI_API_KEY", None)
            
        if not api_key:
            return "AI commentary not available (API key missing)."
        
        # Check if API key is having quota issues
        if "insufficient_quota" in st.session_state.get('api_errors', ""):
            return fallback_response
            
        try:
            # Create a client instance with the API key
            client = openai.OpenAI(api_key=api_key)
            
            # Convert DataFrame to CSV for the prompt
            data_preview = df.head(10).to_csv(index=False)
            
            if prompt:
                user_prompt = f"Based on the following financial data, answer this question: {prompt}\n\nData:\n{data_preview}"
            else:
                user_prompt = f"Based on the following financial data, provide brief insights or recommendations:\n{data_preview}"
            
            # Use the client to create a chat completion
            response = client.chat.completions.create(
                model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {"role": "system", "content": "You analyze financial tables and suggest insights for government financial data."},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Access the response content
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            # Store error message to avoid repeated API calls with insufficient quota
            if "insufficient_quota" in error_str:
                if 'api_errors' not in st.session_state:
                    st.session_state['api_errors'] = error_str
            return f"Could not generate insights: {error_str}"
    except Exception as e:
        return f"Could not generate insights: {str(e)}"

def run_historical_analysis():
    """
    Run the Historical Analysis module with role-based security
    """
    st.title("Historical Budget Analysis")

    df = load_org_data()
    if df.empty:
        st.warning("No data found.")
        st.stop()

    # Apply department security filter
    allowed_depts = get_user_departments()
    if allowed_depts:
        df = df[df["DepartmentName"].isin(allowed_depts)]

    st.subheader("Budget vs. Actual Trends (Multi-Year)")
    df_grouped = df.groupby(["FiscalYear"]).agg({"Budget": "sum", "Actual": "sum"}).reset_index()
    fig = px.line(df_grouped, x="FiscalYear", y=["Budget", "Actual"], markers=True)
    st.plotly_chart(fig, use_container_width=True, key="multi_year_trends")

    st.subheader("Drilldown by Department")
    # Handle department fields consistently (could be Department or DepartmentName)
    dept_field = "Department"
    if "DepartmentName" in df.columns:
        dept_field = "DepartmentName"
        
    departments = sorted(df[dept_field].unique())
    selected_dept = st.selectbox("Choose a Department", departments)

    df_dept = df[df[dept_field] == selected_dept]
    fig2 = px.bar(df_dept, x="FiscalYear", y=["Budget", "Actual"], barmode="group", title=f"{selected_dept} Budget vs. Actual by Year")
    st.plotly_chart(fig2, use_container_width=True, key=f"dept_drilldown_{selected_dept}")

    st.subheader("Cumulative Variance History")
    df["Variance"] = df["Budget"] - df["Actual"]
    # Handle department fields consistently (could be Department or DepartmentName)
    dept_field = "Department"
    if "DepartmentName" in df.columns:
        dept_field = "DepartmentName"
    df_var = df.groupby(dept_field).agg({"Variance": "sum"}).reset_index()
    st.dataframe(df_var.sort_values(by="Variance", ascending=False), use_container_width=True)
    
    # Add account structure analysis if applicable and if account fields are available
    account_col = None
    if "Account" in df.columns:
        account_col = "Account"
    elif "AccountNumber" in df.columns:
        account_col = "AccountNumber"
        
    if account_col and not df.empty:
        with st.expander("🧾 Account Structure Analysis", expanded=False):
            # Get masks from settings
            balance_sheet_mask = get_mask_from_settings("BalanceSheet")
            expense_mask = get_mask_from_settings("Expense")
            revenue_mask = get_mask_from_settings("Revenue")
            
            st.markdown("### Account Structure Insights")
            st.write("This analysis helps you understand spending patterns based on your chart of accounts structure.")
            
            # Apply full account parsing to all rows
            st.subheader("Full Dataset Account Parsing")
            
            # Create a working copy of dataframe
            df_with_segments = df.copy()
            
            # Determine account types based on account number patterns
            df_with_segments['AccountType'] = df_with_segments[account_col].astype(str).apply(
                lambda x: 'Revenue' if str(x).startswith('4') or str(x).startswith('3') else
                         ('Expense' if str(x).startswith('5') or str(x).startswith('6') else
                          ('Balance Sheet' if str(x).startswith('1') or str(x).startswith('2') else 'Other'))
            )
            
            # Apply appropriate mask to each account type
            try:
                # Process balance sheet accounts
                if balance_sheet_mask:
                    balance_accounts = df_with_segments[df_with_segments['AccountType'] == 'Balance Sheet']
                    if not balance_accounts.empty:
                        try:
                            # Parse with balance sheet mask
                            segments_df = balance_accounts[account_col].astype(str).apply(
                                lambda x: pd.Series(parse_account(x, balance_sheet_mask))
                            )
                            # Add segment columns to original dataframe where account type is Balance Sheet
                            for col in segments_df.columns:
                                df_with_segments.loc[df_with_segments['AccountType'] == 'Balance Sheet', col] = segments_df[col].values
                        except Exception as e:
                            st.warning(f"Error parsing balance sheet accounts: {e}")
                
                # Process revenue accounts
                if revenue_mask:
                    revenue_accounts = df_with_segments[df_with_segments['AccountType'] == 'Revenue']
                    if not revenue_accounts.empty:
                        try:
                            # Parse with revenue mask
                            segments_df = revenue_accounts[account_col].astype(str).apply(
                                lambda x: pd.Series(parse_account(x, revenue_mask))
                            )
                            # Add segment columns to original dataframe where account type is Revenue
                            for col in segments_df.columns:
                                df_with_segments.loc[df_with_segments['AccountType'] == 'Revenue', col] = segments_df[col].values
                        except Exception as e:
                            st.warning(f"Error parsing revenue accounts: {e}")
                
                # Process expense accounts
                if expense_mask:
                    expense_accounts = df_with_segments[df_with_segments['AccountType'] == 'Expense']
                    if not expense_accounts.empty:
                        try:
                            # Parse with expense mask
                            segments_df = expense_accounts[account_col].astype(str).apply(
                                lambda x: pd.Series(parse_account(x, expense_mask))
                            )
                            # Add segment columns to original dataframe where account type is Expense
                            for col in segments_df.columns:
                                df_with_segments.loc[df_with_segments['AccountType'] == 'Expense', col] = segments_df[col].values
                        except Exception as e:
                            st.warning(f"Error parsing expense accounts: {e}")
                
                # Add Fund filtering if Fund segments were parsed
                if 'Fund' in df_with_segments.columns:
                    fund_values = df_with_segments['Fund'].dropna().unique()
                    if len(fund_values) > 0:
                        st.subheader("Filter by Account Segments")
                        selected_fund = st.selectbox("Filter by Fund", ["All Funds"] + sorted(fund_values.tolist()))
                        if selected_fund != "All Funds":
                            df_with_segments = df_with_segments[df_with_segments['Fund'] == selected_fund]
                            
                            # Show summary by Fund
                            st.write(f"### Fund: {selected_fund}")
                            fund_summary = df_with_segments.groupby('AccountType').agg({
                                'Budget': 'sum',
                                'Actual': 'sum'
                            }).reset_index()
                            fund_summary['Variance'] = fund_summary['Budget'] - fund_summary['Actual']
                            fund_summary['Percent'] = (fund_summary['Variance'] / fund_summary['Budget'] * 100).fillna(0)
                            
                            st.dataframe(fund_summary.style.format({
                                'Budget': "${:,.2f}",
                                'Actual': "${:,.2f}",
                                'Variance': "${:,.2f}",
                                'Percent': "{:.1f}%"
                            }))
                
                # Add Department filtering if Dept segments were parsed
                if 'Dept' in df_with_segments.columns:
                    dept_values = df_with_segments['Dept'].dropna().unique()
                    if len(dept_values) > 0:
                        selected_dept = st.selectbox("Filter by Department Code", ["All Departments"] + sorted(dept_values.tolist()))
                        if selected_dept != "All Departments":
                            df_with_segments = df_with_segments[df_with_segments['Dept'] == selected_dept]
                
                # Add Object filtering if Object segments were parsed
                if 'Object' in df_with_segments.columns:
                    object_values = df_with_segments['Object'].dropna().unique()
                    if len(object_values) > 0:
                        selected_object = st.selectbox("Filter by Object Code", ["All Objects"] + sorted(object_values.tolist()))
                        if selected_object != "All Objects":
                            df_with_segments = df_with_segments[df_with_segments['Object'] == selected_object]
                
                # Visualization of data with account segments
                if not df_with_segments.empty:
                    st.subheader("Account Segment Analysis")
                    
                    # Group by different segments for analysis
                    available_segments = [col for col in ['Fund', 'Dept', 'Object', 'Category', 'Account'] if col in df_with_segments.columns]
                    
                    if available_segments:
                        segment_for_analysis = st.selectbox("Analyze by Segment", available_segments)
                        
                        # Create summary grouped by selected segment
                        segment_summary = df_with_segments.groupby(segment_for_analysis).agg({
                            'Budget': 'sum',
                            'Actual': 'sum'
                        }).reset_index()
                        
                        segment_summary['Variance'] = segment_summary['Budget'] - segment_summary['Actual']
                        segment_summary = segment_summary.sort_values('Budget', ascending=False)
                        
                        # Create visualization
                        fig = px.bar(segment_summary.head(10), 
                                     x=segment_for_analysis, 
                                     y=['Budget', 'Actual'],
                                     barmode='group',
                                     title=f'Top 10 {segment_for_analysis} by Budget Amount')
                        st.plotly_chart(fig, use_container_width=True, key=f"segment_analysis_{segment_for_analysis}")
                        
                        # Show data table
                        st.write(f"### {segment_for_analysis} Summary")
                        st.dataframe(segment_summary.style.format({
                            'Budget': "${:,.2f}",
                            'Actual': "${:,.2f}",
                            'Variance': "${:,.2f}"
                        }))
                    
            except Exception as e:
                st.error(f"Error during account segment analysis: {e}")
                
            # Show sample account parsing as reference
            st.subheader("Account Structure Reference")
            
            # Get a sample account for each type
            balance_sample = "10304000"  # Common balance sheet account format
            revenue_sample = "4100"      # Common revenue account format  
            expense_sample = "10225406"  # Common expense account format
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### Balance Sheet Accounts")
                if balance_sheet_mask:
                    try:
                        segments = parse_account(balance_sample, balance_sheet_mask)
                        st.write(f"Sample Account: {balance_sample}")
                        for segment, value in segments.items():
                            st.write(f"{segment}: {value}")
                    except Exception as e:
                        st.warning(f"Error parsing balance sheet account: {e}")
                else:
                    st.info("No balance sheet mask configured in Admin Settings.")
            
            with col2:
                st.markdown("#### Revenue Accounts")
                if revenue_mask:
                    try:
                        segments = parse_account(revenue_sample, revenue_mask)
                        st.write(f"Sample Account: {revenue_sample}")
                        for segment, value in segments.items():
                            st.write(f"{segment}: {value}")
                    except Exception as e:
                        st.warning(f"Error parsing revenue account: {e}")
                else:
                    st.info("No revenue mask configured in Admin Settings.")
                    
            with col3:
                st.markdown("#### Expense Accounts")
                if expense_mask:
                    try:
                        segments = parse_account(expense_sample, expense_mask)
                        st.write(f"Sample Account: {expense_sample}")
                        for segment, value in segments.items():
                            st.write(f"{segment}: {value}")
                    except Exception as e:
                        st.warning(f"Error parsing expense account: {e}")
                else:
                    st.info("No expense mask configured in Admin Settings.")

    st.subheader("AI Narrative Summary")
    if st.button("Generate AI Summary"):
        with st.spinner("Generating AI insights..."):
            prompt = "Analyze this multi-year department performance data and provide key insights and budget recommendations"
            ai_insights = generate_ai_commentary(df, prompt)
            st.markdown(ai_insights)
            
    st.divider()
    
    st.subheader("Auto-Generate Full Report")
    if st.button("Generate Full Budget Report PDF"):
        report_gen.generate_full_report(df, report_title="GovSight Historical Budget Analysis Report")

def render_historical_analysis(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Historical Analysis tab
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.markdown('<div class="sub-header">Historical Budget Analysis</div>', unsafe_allow_html=True)
    
    # Load historical data
    try:
        df = load_org_data(org)
        
        # Ensure we have the organization column
        if 'Organization' not in df.columns:
            df['Organization'] = org
        
        has_real_data = not df.empty
    except Exception as e:
        st.error(f"Error loading historical data: {e}")
        has_real_data = False
    
    if has_real_data:
        st.success("Loaded historical budget data from database")
        
        # Dashboard KPIs at the top
        st.subheader("Budget Overview Metrics")
        total_budget = df["Budget"].sum()
        total_actual = df["Actual"].sum()
        total_underspent = total_budget - total_actual
        underspent_pct = (total_underspent / total_budget) * 100 if total_budget > 0 else 0
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Budget", format_currency(total_budget))
        kpi2.metric("Total Actual Spent", format_currency(total_actual))
        kpi3.metric("Total Underspent", format_currency(total_underspent))
        kpi4.metric("Underspent %", format_percentage(underspent_pct))
        
        # Add overall AI insight option
        with st.expander("AI Budget Analysis", expanded=False):
            st.info("Get AI-powered insights for your overall budget performance")
            if st.button("Generate Organization-Wide Insights"):
                with st.spinner("Analyzing organizational budget data..."):
                    org_prompt = f"Analyze the overall budget performance for {org_display_name}. Identify key trends, risks, and opportunities based on this data. Provide 3-5 actionable recommendations for financial planning."
                    ai_insights = generate_ai_commentary(df, org_prompt)
                    st.markdown(ai_insights)
        
        # Add a fiscal year filter
        fiscal_years = sorted(df["FiscalYear"].unique())
        selected_years = st.multiselect("Select Fiscal Years for Analysis", fiscal_years, default=fiscal_years)
        
        if not selected_years:
            st.warning("Please select at least one fiscal year.")
        else:
            filtered_df = df[df["FiscalYear"].isin(selected_years)]
            
            # Budget vs Actual by Fiscal Year
            st.subheader("Budget vs. Actual by Fiscal Year")
            year_totals = filtered_df.groupby("FiscalYear").agg({"Budget": "sum", "Actual": "sum"}).reset_index()
            
            # Create a bar chart showing budget vs actual by year
            try:
                # Create a bar chart showing budget vs actual by year
                fig1 = px.bar(year_totals, x="FiscalYear", y=["Budget", "Actual"], 
                             barmode="group", 
                             title=f"{org_display_name} Budget vs. Actual by Fiscal Year",
                             labels={"value": "Amount ($)", "variable": "Category"})
                st.plotly_chart(fig1, use_container_width=True, key="budget_vs_actual_by_year")
                
                # Add forecasting option
                with st.expander("Generate Future Forecasts", expanded=False):
                    st.markdown("""
                    This tool uses machine learning to forecast future budget trends. It analyzes historical patterns
                    to predict how budgets and actual spending might change in the coming years if current patterns continue.
                    """)
                    
                    # Option for number of years to forecast
                    future_years = st.slider("Number of years to forecast", min_value=1, max_value=5, value=3)
                    
                    if st.button("Generate Forecast"):
                        # Prepare data for modeling
                        try:
                            # First, ensure Budget and Actual are numeric
                            try:
                                year_totals['Budget'] = pd.to_numeric(year_totals['Budget'], errors='coerce')
                                year_totals['Actual'] = pd.to_numeric(year_totals['Actual'], errors='coerce')
                                
                                # Drop any rows with NaN values after conversion
                                year_totals = year_totals.dropna(subset=['Budget', 'Actual'])
                                
                                if year_totals.empty:
                                    st.error("No valid numeric data found for forecasting after data cleaning.")
                                    st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                                    raise ValueError("No valid numeric data for forecasting")
                            except Exception as data_err:
                                st.error(f"Error preparing data for forecasting: {data_err}")
                                st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                                raise ValueError(f"Data preparation error: {data_err}")
                                
                            year_totals["Year_Num"] = range(len(year_totals))
                            
                            # Create and train linear regression models for both Budget and Actual
                            budget_model = LinearRegression()
                            actual_model = LinearRegression()
                            
                            X = year_totals[["Year_Num"]]
                            y_budget = year_totals["Budget"]
                            y_actual = year_totals["Actual"]
                            
                            # Train models
                            budget_model.fit(X, y_budget)
                            actual_model.fit(X, y_actual)
                            
                            # Generate future years
                            last_year_num = len(X) - 1
                            future_year_nums = list(range(last_year_num + 1, last_year_num + 1 + future_years))
                            future_X = np.array(future_year_nums).reshape(-1, 1)
                            
                            # Get the last fiscal year and predict future fiscal years
                            try:
                                last_year = year_totals["FiscalYear"].iloc[-1]
                                
                                # Convert to string for consistent handling
                                last_year_str = str(last_year)
                                
                                # Extract year number if format is like "FY 2024"
                                if "FY" in last_year_str:
                                    try:
                                        # Find any number in the string
                                        import re
                                        year_match = re.search(r'\d+', last_year_str)
                                        if year_match:
                                            year_num = int(year_match.group())
                                            future_fiscal_years = [f"FY {year_num + i}" for i in range(1, future_years + 1)]
                                        else:
                                            future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                                    except:
                                        # If can't parse, just use generic labels
                                        future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                                else:
                                    # Try to convert to number and increment
                                    try:
                                        year_num = int(float(last_year_str))
                                        future_fiscal_years = [str(year_num + i) for i in range(1, future_years + 1)]
                                    except (ValueError, TypeError):
                                        future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                            except (IndexError, TypeError, KeyError) as e:
                                # Something went wrong, use generic labels
                                st.warning(f"Using generic year labels for forecast due to data format issue: {str(e)}")
                                future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                            
                            # Predict future values
                            future_budget = budget_model.predict(future_X)
                            future_actual = actual_model.predict(future_X)
                            
                            # Create forecast dataframe
                            forecast_df = pd.DataFrame({
                                "FiscalYear": future_fiscal_years,
                                "Budget": future_budget,
                                "Actual": future_actual,
                                "Forecast": True
                            })
                            
                            # Add indicator column to original data
                            year_totals["Forecast"] = False
                            
                            # Combine historical and forecast data
                            combined = pd.concat([year_totals, forecast_df])
                            
                            # Visualize the forecast with a line chart
                            fig_forecast = px.line(
                                combined, 
                                x="FiscalYear", 
                                y=["Budget", "Actual"],
                                markers=True,
                                title=f"{org_display_name} - Budget and Actual Forecast",
                                labels={"value": "Amount ($)", "variable": "Type"}
                            )
                            
                            # Add vertical line at forecast boundary
                            historical_years = len(year_totals)
                            forecast_start = combined["FiscalYear"].iloc[historical_years-1]
                            
                            fig_forecast.add_vline(
                                x=forecast_start, 
                                line_dash="dash", 
                                line_color="gray", 
                                annotation_text="Forecast Start",
                                annotation_position="top right"
                            )
                            
                            # Update layout for better visualization
                            fig_forecast.update_layout(
                                xaxis_title="Fiscal Year",
                                yaxis_title="Amount ($)",
                                legend_title="Type",
                                hovermode="x unified"
                            )
                            
                            # Show the forecast visualization
                            st.plotly_chart(fig_forecast, use_container_width=True, key="forecast_chart")
                            
                            # Show the forecast data
                            st.subheader("Forecast Data")
                            # Create a copy to apply formatting
                            forecast_display = forecast_df.copy()
                            forecast_display["Budget"] = forecast_display["Budget"].apply(lambda x: format_currency(x))
                            forecast_display["Actual"] = forecast_display["Actual"].apply(lambda x: format_currency(x))
                            st.dataframe(forecast_display, use_container_width=True)
                            
                            # Calculate budget variance in forecast
                            forecast_df["Variance"] = forecast_df["Budget"] - forecast_df["Actual"]
                            forecast_df["Variance%"] = (forecast_df["Variance"] / forecast_df["Budget"]) * 100
                            
                            avg_variance = forecast_df["Variance"].mean()
                            avg_variance_pct = forecast_df["Variance%"].mean()
                            
                            # Show forecast insights
                            st.subheader("Forecast Insights")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Average Forecast Variance", format_currency(avg_variance))
                            with col2:
                                st.metric("Average Variance Percentage", format_percentage(avg_variance_pct))
                            
                            # Recommendation based on forecast
                            if avg_variance_pct > 10:
                                st.success("The budget is projected to significantly underspend. Consider reallocating budget to other priorities.")
                            elif avg_variance_pct < -10:
                                st.error("The budget is projected to significantly overspend. Consider increasing the budget allocation.")
                            else:
                                st.info("The budget spending is projected to closely align with budgeted amounts.")
                        except Exception as e:
                            st.error(f"Error generating forecast: {e}")
                            st.info("Make sure you have enough historical data points for a meaningful forecast.")
            except ImportError:
                # Fallback to regular plotly
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(x=year_totals["FiscalYear"], y=year_totals["Budget"], name="Budget"))
                fig1.add_trace(go.Bar(x=year_totals["FiscalYear"], y=year_totals["Actual"], name="Actual"))
                fig1.update_layout(barmode="group", title=f"{org_display_name} Budget vs. Actual by Fiscal Year")
                st.plotly_chart(fig1, use_container_width=True, key="budget_vs_actual_fallback")
            
            # Department breakdown
            st.subheader("🏢 Department Budget Analysis")
            departments = sorted(filtered_df["Department"].unique())
            
            # Allow selecting specific departments
            selected_dept = st.selectbox("Select Department for Detailed Analysis", departments)
            
            # Create filtered data for the selected department
            dept_df = filtered_df[filtered_df["Department"] == selected_dept]
            dept_by_year = dept_df.groupby("FiscalYear").agg({"Budget": "sum", "Actual": "sum"}).reset_index()
            
            # Show department metrics
            dept_total_budget = dept_df["Budget"].sum()
            dept_total_actual = dept_df["Actual"].sum()
            dept_underspent = dept_total_budget - dept_total_actual
            dept_underspent_pct = (dept_underspent / dept_total_budget) * 100 if dept_total_budget > 0 else 0
            
            dept_kpi1, dept_kpi2, dept_kpi3 = st.columns(3)
            dept_kpi1.metric(f"{selected_dept} Total Budget", format_currency(dept_total_budget))
            dept_kpi2.metric(f"Total Actual", format_currency(dept_total_actual))
            dept_kpi3.metric(f"Underspent ({format_percentage(dept_underspent_pct)})", format_currency(dept_underspent))
            
            # Create department trend chart
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=dept_by_year["FiscalYear"], 
                y=dept_by_year["Budget"],
                mode="lines+markers",
                name="Budget"
            ))
            fig2.add_trace(go.Scatter(
                x=dept_by_year["FiscalYear"], 
                y=dept_by_year["Actual"],
                mode="lines+markers",
                name="Actual"
            ))
            
            fig2.update_layout(
                title=f"{selected_dept} Budget Trends",
                xaxis_title="Fiscal Year",
                yaxis_title="Amount ($)",
                height=400
            )
            
            st.plotly_chart(fig2, use_container_width=True, key=f"dept_trends_{selected_dept}")
            
            # Add AI insights for the department
            with st.expander("AI Department Insights", expanded=False):
                st.info("Get AI-powered insights for this department's budget performance")
                if st.button("Generate AI Insights for Department"):
                    with st.spinner("Analyzing department data..."):
                        dept_prompt = f"Analyze the budget performance for the {selected_dept} department across fiscal years. Identify trends, underspending/overspending patterns, and provide 3-4 specific actionable recommendations."
                        ai_insights = generate_ai_commentary(dept_df, dept_prompt)
                        st.markdown(ai_insights)
            
            # Department-level forecasting
            with st.expander("Forecast Department Budget", expanded=False):
                st.markdown(f"""
                Forecast future budgets and spending for **{selected_dept}** based on historical trends.
                This will help plan for future budget allocations more effectively.
                """)
                
                # Option for number of years to forecast
                dept_future_years = st.slider("Number of years to forecast", min_value=1, max_value=5, value=3, key="dept_forecast_years")
                
                # Show advanced options
                advanced_options = st.checkbox("Show Advanced Options")
                if advanced_options:
                    growth_adj = st.slider("Growth adjustment (%)", min_value=-10, max_value=10, value=0, 
                                          help="Adjust the growth rate for forecasting. Positive values will increase the growth rate; negative values will decrease it.")
                else:
                    growth_adj = 0
                
                if st.button("Generate Department Forecast"):
                    try:
                        # First, ensure Budget and Actual are numeric
                        try:
                            dept_by_year['Budget'] = pd.to_numeric(dept_by_year['Budget'], errors='coerce')
                            dept_by_year['Actual'] = pd.to_numeric(dept_by_year['Actual'], errors='coerce')
                            
                            # Drop any rows with NaN values after conversion
                            dept_by_year = dept_by_year.dropna(subset=['Budget', 'Actual'])
                            
                            if dept_by_year.empty:
                                st.error("No valid numeric data found for forecasting after data cleaning.")
                                st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                                raise ValueError("No valid numeric data for forecasting")
                        except Exception as data_err:
                            st.error(f"Error preparing data for forecasting: {data_err}")
                            st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                            raise ValueError(f"Data preparation error: {data_err}")
                        
                        # Prepare data for modeling
                        dept_by_year["Year_Num"] = range(len(dept_by_year))
                        
                        # Create and train linear regression models for both Budget and Actual
                        dept_budget_model = LinearRegression()
                        dept_actual_model = LinearRegression()
                        
                        X = dept_by_year[["Year_Num"]]
                        y_budget = dept_by_year["Budget"]
                        y_actual = dept_by_year["Actual"]
                        
                        # Train models
                        dept_budget_model.fit(X, y_budget)
                        dept_actual_model.fit(X, y_actual)
                        
                        # Generate future years
                        last_year_num = len(X) - 1
                        future_year_nums = list(range(last_year_num + 1, last_year_num + 1 + dept_future_years))
                        future_X = np.array(future_year_nums).reshape(-1, 1)
                        
                        # Get the last fiscal year and predict future fiscal years
                        try:
                            last_year = dept_by_year["FiscalYear"].iloc[-1]
                            
                            # Convert to string for consistent handling
                            last_year_str = str(last_year)
                            
                            # Extract year number if format is like "FY 2024"
                            if "FY" in last_year_str:
                                try:
                                    # Find any number in the string
                                    import re
                                    year_match = re.search(r'\d+', last_year_str)
                                    if year_match:
                                        year_num = int(year_match.group())
                                        future_fiscal_years = [f"FY {year_num + i}" for i in range(1, dept_future_years + 1)]
                                    else:
                                        future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                                except:
                                    # If can't parse, just use generic labels
                                    future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                            else:
                                # Try to convert to number and increment
                                try:
                                    year_num = int(float(last_year_str))
                                    future_fiscal_years = [str(year_num + i) for i in range(1, dept_future_years + 1)]
                                except (ValueError, TypeError):
                                    future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                        except (IndexError, TypeError, KeyError) as e:
                            # Something went wrong, use generic labels
                            st.warning(f"Using generic year labels for forecast due to data format issue: {str(e)}")
                            future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                        
                        # Predict future values and ensure they are numeric
                        try:
                            future_budget = dept_budget_model.predict(future_X)
                            future_actual = dept_actual_model.predict(future_X)
                            
                            # Ensure predictions are float arrays for calculations
                            future_budget = np.array(future_budget, dtype=float)
                            future_actual = np.array(future_actual, dtype=float)
                        except Exception as e:
                            st.error(f"Error generating forecasts: {str(e)}")
                            st.info("Please ensure the department has sufficient historical data for forecasting.")
                            return  # Exit the function gracefully instead of continue
                        
                        # Apply growth adjustment if specified
                        if growth_adj != 0:
                            try:
                                # Ensure growth_adj is a numeric value
                                growth_adj = float(growth_adj)
                                
                                # Apply adjustment factor to the growth
                                adj_factor = 1 + (growth_adj / 100)
                                
                                # Ensure future predictions are numeric arrays
                                future_budget = np.array(future_budget, dtype=float)
                                future_actual = np.array(future_actual, dtype=float)
                                
                                # Calculate the average growth rate per year
                                if len(future_budget) > 1:
                                    budget_growth_per_year = (future_budget[-1] - future_budget[0]) / (len(future_budget) - 1)
                                    actual_growth_per_year = (future_actual[-1] - future_actual[0]) / (len(future_actual) - 1)
                                    
                                    # Apply the adjustment to the growth rate
                                    adjusted_budget_growth = float(budget_growth_per_year) * adj_factor
                                    adjusted_actual_growth = float(actual_growth_per_year) * adj_factor
                                    
                                    # Recalculate the forecasted values with the adjusted growth
                                    for i in range(1, len(future_budget)):
                                        future_budget[i] = float(future_budget[0]) + (adjusted_budget_growth * i)
                                        future_actual[i] = float(future_actual[0]) + (adjusted_actual_growth * i)
                                else:
                                    # If only one forecasted year, apply the adjustment directly
                                    future_budget[0] = float(future_budget[0]) * adj_factor
                                    future_actual[0] = float(future_actual[0]) * adj_factor
                            except (TypeError, ValueError) as e:
                                st.warning(f"Growth adjustment failed due to data type issue: {str(e)}. Using original forecast.")
                                # Continue with original forecast without adjustment
                        
                        # Create forecast dataframe with proper data type handling
                        try:
                            dept_forecast_df = pd.DataFrame({
                                "FiscalYear": future_fiscal_years,
                                "Budget": [float(x) for x in future_budget],
                                "Actual": [float(x) for x in future_actual],
                                "Forecast": True
                            })
                        except (TypeError, ValueError) as e:
                            st.error(f"Error creating forecast data: {str(e)}")
                            return  # Exit the function gracefully instead of continue
                        
                        # Add indicator column to original data
                        dept_by_year["Forecast"] = False
                        
                        # Combine historical and forecast data
                        dept_combined = pd.concat([dept_by_year, dept_forecast_df])
                        
                        # Visualize the forecast with a line chart
                        fig_dept_forecast = px.line(
                            dept_combined, 
                            x="FiscalYear", 
                            y=["Budget", "Actual"],
                            markers=True,
                            title=f"{selected_dept} - Budget and Actual Forecast",
                            labels={"value": "Amount ($)", "variable": "Type"}
                        )
                        
                        # Add vertical line at forecast boundary
                        historical_years = len(dept_by_year)
                        forecast_start = dept_combined["FiscalYear"].iloc[historical_years-1]
                        
                        fig_dept_forecast.add_vline(
                            x=forecast_start, 
                            line_dash="dash", 
                            line_color="gray", 
                            annotation_text="Forecast Start",
                            annotation_position="top right"
                        )
                        
                        # Update layout for better visualization
                        fig_dept_forecast.update_layout(
                            xaxis_title="Fiscal Year",
                            yaxis_title="Amount ($)",
                            legend_title="Type",
                            hovermode="x unified"
                        )
                        
                        # Show the forecast visualization
                        st.plotly_chart(fig_dept_forecast, use_container_width=True, key=f"dept_forecast_{selected_dept}")
                        
                        # Show the forecast data
                        st.subheader(f"Forecast Data for {selected_dept}")
                        # Create a copy to apply formatting
                        dept_forecast_display = dept_forecast_df.copy()
                        dept_forecast_display["Budget"] = dept_forecast_display["Budget"].apply(lambda x: format_currency(x))
                        dept_forecast_display["Actual"] = dept_forecast_display["Actual"].apply(lambda x: format_currency(x))
                        st.dataframe(dept_forecast_display, use_container_width=True)
                        
                        # Calculate budget variance in forecast
                        dept_forecast_df["Variance"] = dept_forecast_df["Budget"] - dept_forecast_df["Actual"]
                        dept_forecast_df["Variance%"] = (dept_forecast_df["Variance"] / dept_forecast_df["Budget"]) * 100
                        
                        avg_variance = dept_forecast_df["Variance"].mean()
                        avg_variance_pct = dept_forecast_df["Variance%"].mean()
                        
                        # Show forecast insights
                        st.subheader(f"Forecast Insights for {selected_dept}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Average Forecast Variance", format_currency(avg_variance))
                        with col2:
                            st.metric("Average Variance Percentage", format_percentage(avg_variance_pct))
                        
                        # Recommendation based on forecast
                        if growth_adj != 0:
                            st.info(f"This forecast includes a {growth_adj}% adjustment to the growth rate.")
                            
                        if avg_variance_pct > 10:
                            st.success(f"is projected to significantly underspend. Consider reallocating budget to other departments.")
                        elif avg_variance_pct < -10:
                            st.error(f"is projected to significantly overspend. Consider increasing their budget allocation.")
                        else:
                            st.info(f"{selected_dept}'s spending is projected to closely align with budgeted amounts.")
                            
                        # Final year forecast summary
                        final_year = dept_forecast_df.iloc[-1]
                        st.markdown(f"""
                        ### FY {final_year['FiscalYear']} Projected Budget
                        By fiscal year {final_year['FiscalYear']}, {selected_dept} is projected to have:
                        - Budget: **{format_currency(final_year['Budget'])}**
                        - Expenditure: **{format_currency(final_year['Actual'])}**
                        - Variance: **{format_currency(final_year['Variance'])}** ({format_percentage(final_year['Variance%'])})
                        """)
                        
                    except Exception as e:
                        st.error(f"Error generating department forecast: {e}")
                        st.info("Make sure you have enough historical data points for a meaningful forecast.")
        
        # Enhanced Historical Report Generation
        st.markdown("---")
        st.subheader("Enhanced Historical Analysis Report")
        st.markdown("Generate comprehensive historical analysis with trend forecasting, executive summary, and detailed visualizations.")
        
        if st.button("Generate Enhanced Historical Report", use_container_width=True):
            with st.spinner("Generating comprehensive historical analysis report..."):
                try:
                    from modules.reports.enhanced_report_generator import generate_enhanced_report
                    
                    # Use filtered data based on current selections
                    report_data = filtered_df.copy()
                    
                    # Add time-based analysis columns
                    if 'FiscalYear' in report_data.columns:
                        report_data = report_data.sort_values('FiscalYear')
                        
                        # Calculate year-over-year changes
                        if 'Budget' in report_data.columns:
                            budget_by_year = report_data.groupby('FiscalYear')['Budget'].sum().reset_index()
                            budget_by_year['YoY_Budget_Change'] = budget_by_year['Budget'].pct_change() * 100
                            
                        if 'Actual' in report_data.columns:
                            actual_by_year = report_data.groupby('FiscalYear')['Actual'].sum().reset_index()
                            actual_by_year['YoY_Actual_Change'] = actual_by_year['Actual'].pct_change() * 100
                    
                    # Generate enhanced report
                    hist_title = f"Historical Financial Analysis: {selected_dept}" if selected_dept != "All Departments" else "Historical Financial Analysis - All Departments"
                    enhanced_report = generate_enhanced_report(
                        report_data, 
                        "historical", 
                        hist_title,
                        org_display_name,
                        {
                            'fiscal_years': selected_years, 
                            'department': selected_dept,
                            'forecast_enabled': forecast_years > 0 if 'forecast_years' in locals() else False
                        }
                    )
                    
                    # Display executive summary
                    st.markdown("### Executive Summary")
                    st.markdown(enhanced_report['executive_summary'])
                    
                    # Display key metrics
                    if enhanced_report['key_metrics']:
                        st.markdown("### Key Historical Metrics")
                        metrics_cols = st.columns(4)
                        for i, (metric, value) in enumerate(enhanced_report['key_metrics'].items()):
                            with metrics_cols[i % 4]:
                                if isinstance(value, (int, float)):
                                    if 'percent' in metric.lower() or 'growth' in metric.lower():
                                        st.metric(metric.replace('_', ' ').title(), f"{value:.1f}%")
                                    elif 'amount' in metric.lower() or 'total' in metric.lower():
                                        st.metric(metric.replace('_', ' ').title(), f"${value:,.0f}")
                                    else:
                                        st.metric(metric.replace('_', ' ').title(), f"{value:,.0f}")
                    
                    # Display comprehensive visualizations with tabs
                    if enhanced_report['charts']:
                        st.markdown("### Historical Analysis Visualizations")
                        
                        # Organize charts by category
                        trend_charts = [c for c in enhanced_report['charts'] if 'trend' in c.get('title', '').lower() or 'time' in c.get('title', '').lower()]
                        comparison_charts = [c for c in enhanced_report['charts'] if 'comparison' in c.get('title', '').lower() or 'year' in c.get('title', '').lower()]
                        forecast_charts = [c for c in enhanced_report['charts'] if 'forecast' in c.get('title', '').lower()]
                        other_charts = [c for c in enhanced_report['charts'] if c not in trend_charts + comparison_charts + forecast_charts]
                        
                        chart_tabs = st.tabs(["Trend Analysis", "Comparative Analysis", "Forecasting", "Additional Insights"])
                        
                        with chart_tabs[0]:
                            if trend_charts:
                                for i, chart in enumerate(trend_charts):
                                    st.plotly_chart(chart['figure'], use_container_width=True, key=f"trend_chart_{i}")
                                    if 'description' in chart:
                                        st.caption(chart['description'])
                            else:
                                st.info("No trend-specific charts available for this dataset.")
                        
                        with chart_tabs[1]:
                            if comparison_charts:
                                for i, chart in enumerate(comparison_charts):
                                    st.plotly_chart(chart['figure'], use_container_width=True, key=f"comparison_chart_{i}")
                                    if 'description' in chart:
                                        st.caption(chart['description'])
                            else:
                                st.info("No comparison charts available for this dataset.")
                        
                        with chart_tabs[2]:
                            if forecast_charts:
                                for i, chart in enumerate(forecast_charts):
                                    st.plotly_chart(chart['figure'], use_container_width=True, key=f"forecast_chart_tab_{i}")
                                    if 'description' in chart:
                                        st.caption(chart['description'])
                            else:
                                st.info("Enable forecasting in the main analysis to see forecast charts here.")
                        
                        with chart_tabs[3]:
                            if other_charts:
                                for i, chart in enumerate(other_charts):
                                    st.plotly_chart(chart['figure'], use_container_width=True, key=f"other_chart_{i}")
                                    if 'description' in chart:
                                        st.caption(chart['description'])
                            else:
                                st.info("No additional charts available.")
                    
                    # Professional PDF download
                    if enhanced_report['pdf_bytes']:
                        st.download_button(
                            "Download Complete Historical Analysis Report (PDF)",
                            data=enhanced_report['pdf_bytes'],
                            file_name=f"historical_analysis_{selected_dept.replace(' ', '_').lower()}_{min(selected_years)}-{max(selected_years)}.pdf",
                            mime="application/pdf"
                        )
                    
                    # Report summary
                    st.markdown("### Report Summary")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Report Features:**")
                        st.markdown("- AI-generated executive summary")
                        st.markdown("- Multi-year trend analysis")
                        st.markdown("- Year-over-year comparisons")
                    with col2:
                        st.markdown("**Analysis Coverage:**")
                        st.markdown("- Historical performance patterns")
                        st.markdown("- Forecasting insights")
                        st.markdown("- Professional PDF with charts")
                        
                except ImportError:
                    st.error("Enhanced reporting module not available.")
                except Exception as e:
                    st.error(f"Error generating enhanced report: {str(e)}")
            
        # Variance Analysis
        st.subheader("Variance Analysis")
        
        # Calculate variance for each department and fiscal year
        variance_df = filtered_df.copy()
        variance_df["Variance"] = variance_df["Budget"] - variance_df["Actual"]
        variance_df["Variance%"] = (variance_df["Variance"] / variance_df["Budget"]) * 100
        
        # Group by department to get overall variance
        dept_variance = variance_df.groupby("Department").agg({
            "Budget": "sum",
            "Actual": "sum",
            "Variance": "sum"
        }).reset_index()
        
        # Calculate percentage variance
        dept_variance["Variance%"] = (dept_variance["Variance"] / dept_variance["Budget"]) * 100
        
        # Sort by absolute variance percentage
        dept_variance = dept_variance.sort_values(by="Variance%", ascending=False)
        
        # Create a bar chart for variance by department
        try:
            fig3 = px.bar(
                dept_variance,
                y="Department",
                x="Variance%",
                orientation="h",
                title="Budget Variance by Department (%)",
                color="Variance%",
                color_continuous_scale=["red", "white", "green"],
                range_color=[-20, 20],
                text="Variance%"
            )
            
            fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig3.update_layout(height=500)
            
            st.plotly_chart(fig3, use_container_width=True, key="dept_variance_chart")
        except Exception:
            st.error("Could not create variance chart. Please check your data.")
        
        # Display detailed variance table
        st.subheader("Detailed Variance Analysis")
        
        # Format the table for display
        display_variance = dept_variance.copy()
        display_variance["Budget"] = display_variance["Budget"].apply(lambda x: format_currency(x))
        display_variance["Actual"] = display_variance["Actual"].apply(lambda x: format_currency(x))
        display_variance["Variance"] = display_variance["Variance"].apply(lambda x: format_currency(x))
        display_variance["Variance%"] = display_variance["Variance%"].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(display_variance, use_container_width=True)
        
        # Export data option
        st.download_button(
            label="Download Variance Data as CSV",
            data=dept_variance.to_csv(index=False),
            file_name=f"{org_display_name}_variance_analysis.csv",
            mime="text/csv"
        )
        
        # Add Phase 2 Reporting Integration
        st.markdown("---")
        
        # Prepare analysis results for reporting
        analysis_results = {
            'period': f"{min(selected_years)} - {max(selected_years)}" if selected_years else "All Years",
            'summary': f"Analysis of {org_display_name} budget data showing {format_percentage(underspent_pct)} underspent",
            'executive_summary': f"{org_display_name} has a total budget of {format_currency(total_budget)} with actual spending of {format_currency(total_actual)}",
            'recommendations': "Continue monitoring budget utilization and identify opportunities for reallocation.",
            'key_findings': f"Overall underspending of {format_currency(total_underspent)} ({format_percentage(underspent_pct)})"
        }
        
        # Add export options using centralized Phase 2 reporting
        if REPORTS_INTEGRATION_AVAILABLE and vatica_reports:
            vatica_reports.add_historical_analysis_export(filtered_df, analysis_results)
        else:
            # If integration not available, show direct message
            st.warning("Phase 2 reporting integration is initializing. Please refresh the page if export options don't appear.")
            # Provide basic CSV fallback
            st.download_button(
                label="📥 Download CSV (Basic)",
                data=filtered_df.to_csv(index=False),
                file_name=f"historical_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        # Custom SQL Query Section
        st.subheader("Custom Data Analysis")
        
        with st.expander("Run Custom SQL Query", expanded=False):
            st.markdown("""
            Write your own SQL query to analyze budget data. Use the table `DepartmentPerformance` with columns:
            - Department
            - Fund
            - FiscalYear
            - Budget
            - Actual
            - Month
            - Organization
            """)
            
            # Sample queries
            sample_queries = {
                "Department Totals": "SELECT Department, SUM(Budget) as TotalBudget, SUM(Actual) as TotalSpent, SUM(Budget - Actual) as Variance FROM DepartmentPerformance GROUP BY Department ORDER BY TotalBudget DESC",
                "Year over Year": "SELECT FiscalYear, SUM(Budget) as YearlyBudget, SUM(Actual) as YearlySpent FROM DepartmentPerformance GROUP BY FiscalYear",
                "Fund Analysis": "SELECT Fund, SUM(Budget) as TotalBudget, SUM(Actual) as TotalSpent FROM DepartmentPerformance GROUP BY Fund ORDER BY TotalBudget DESC",
                "Top Underspent": "SELECT Department, SUM(Budget) as TotalBudget, SUM(Actual) as TotalSpent, SUM(Budget - Actual) as Underspent FROM DepartmentPerformance GROUP BY Department ORDER BY Underspent DESC LIMIT 5"
            }
            
            selected_sample = st.selectbox("Sample Queries", list(sample_queries.keys()))
            custom_query = st.text_area("SQL Query", value=sample_queries[selected_sample], height=100)
            
            if st.button("Run Query"):
                if custom_query:
                    try:
                        # Execute the query
                        results = run_dashboard_query(custom_query, org=org)
                        
                        if results:
                            # Convert to DataFrame
                            results_df = pd.DataFrame(results)
                            
                            # Display the results
                            st.subheader("Query Results")
                            st.dataframe(results_df, use_container_width=True)
                            
                            # Option to download results
                            st.download_button(
                                label="Download Results as CSV",
                                data=results_df.to_csv(index=False),
                                file_name="custom_query_results.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("The query returned no results.")
                    except Exception as e:
                        st.error(f"Error executing query: {e}")
    else:
        st.error("No historical data available. Please check the database connection settings.")
        st.markdown("""
        Please check the following:
        1. The database file exists at the expected location
        2. The database contains the required tables
        3. The database has proper permissions
        """)

