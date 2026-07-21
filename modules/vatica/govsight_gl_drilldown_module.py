"""
GL Drilldown Module

This module offers detailed GL account-level analysis including:
- Department-level filtering with security
- Fund-level summary visualizations
- GL Account detail tables and charts
- PDF report generation with AI-powered analysis
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import modules.database.db_connection as db_connection
from modules.database.db_connection import get_db_path_for_org
import modules.security.security_manager as sec
import modules.reports.summary_report_generator as report_gen

def run_gl_drilldown(org: str = "cityA", org_display_name: str = "City A"):
    """
    Run the GL Account Drilldown module with security features
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.title(" Department & GL Account Drilldown")
    st.markdown(f"Detailed GL account analysis for {org_display_name}")
    
    # Get database path for the organization
    DB_PATH = "cityA_with_gl_accounts.db"  # Default path
    
    @st.cache_data
    def load_data(db_path):
        """Load data from the database with GL account information"""
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query("SELECT * FROM DepartmentPerformance", conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading GL account data: {e}")
            return pd.DataFrame()
    
    # Load the data
    df = load_data(DB_PATH)
    
    if df.empty:
        st.warning("No GL account data available.")
        return
    
    # Apply department security filter for non-admin users
    allowed_depts = sec.get_user_departments()
    if allowed_depts:
        column_name = "Department" if "Department" in df.columns else "DepartmentName"
        if column_name in df.columns:
            df = df[df[column_name].isin(allowed_depts)]
            st.info(f"Showing data for your authorized departments: {', '.join(allowed_depts)}")
    
    # Determine department column name
    dept_column = "Department" if "Department" in df.columns else "DepartmentName"
    
    # Department filter
    departments = sorted(df[dept_column].unique())
    selected_dept = st.selectbox("Select Department", departments)
    
    # Filter data for selected department
    df_dept = df[df[dept_column] == selected_dept]
    
    # Determine fund column name
    fund_column = "Fund" if "Fund" in df.columns else "FundName"
    
    # Fund-level summary
    st.subheader(f" Fund Summary – {selected_dept}")
    fund_summary = df_dept.groupby(fund_column)[["Budget", "Actual"]].sum().reset_index()
    fig_fund = px.bar(fund_summary, x=fund_column, y=["Budget", "Actual"], barmode="group")
    st.plotly_chart(fig_fund, use_container_width=True, key=f"fund_summary_{selected_dept}")
    
    # Check if AccountCode/AccountName columns exist
    has_gl_detail = "AccountCode" in df.columns and "AccountName" in df.columns
    
    if has_gl_detail:
        # GL Account-level drilldown
        st.subheader("📘 GL Account Detail")
        df_gl = df_dept.groupby(["AccountCode", "AccountName"])[["Budget", "Actual"]].sum().reset_index()
        
        # Create bar chart with GL accounts
        fig_gl = px.bar(
            df_gl, 
            x="AccountName", 
            y=["Budget", "Actual"], 
            barmode="group", 
            title="GL Account Spending",
            labels={"value": "Amount ($)", "variable": "Category"}
        )
        
        # Update layout for better display
        fig_gl.update_layout(
            xaxis_title="GL Account",
            yaxis_title="Amount ($)",
            legend_title="Category"
        )
        
        st.plotly_chart(fig_gl, use_container_width=True, key=f"gl_detail_{selected_dept}")
        
        # Show detailed table with sorting and filtering
        st.subheader("Detailed GL Account Data")
        
        # Add variance calculation
        df_gl["Variance"] = df_gl["Budget"] - df_gl["Actual"]
        df_gl["Variance %"] = (df_gl["Variance"] / df_gl["Budget"]) * 100
        
        # Format for display
        formatted_df = df_gl.copy()
        formatted_df["Budget"] = formatted_df["Budget"].apply(lambda x: f"${x:,.2f}")
        formatted_df["Actual"] = formatted_df["Actual"].apply(lambda x: f"${x:,.2f}")
        formatted_df["Variance"] = formatted_df["Variance"].apply(lambda x: f"${x:,.2f}")
        formatted_df["Variance %"] = formatted_df["Variance %"].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(formatted_df, use_container_width=True)
        
        # Add download option
        csv = df_gl.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download GL Account Data as CSV",
            csv,
            f"{selected_dept}_gl_accounts.csv",
            "text/csv",
            key="download-gl-csv"
        )
        
        st.divider()
        
        st.subheader(" Auto-Generate GL Account Report")
        if st.button(" Generate GL Drilldown Report PDF"):
            report_gen.generate_full_report(df_gl, report_title=f"GovSight GL Drilldown Report – {selected_dept}")
    else:
        st.warning("GL Account detail is not available in this database. Please use a database with AccountCode and AccountName columns.")

# This section allows the module to be run directly
if __name__ == "__main__":
    run_gl_drilldown()