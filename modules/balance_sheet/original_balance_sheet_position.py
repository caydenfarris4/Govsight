"""
Balance Sheet Position Module

This module handles all functionality related to the Balance Sheet Position tab, including:
- Display of all balance sheet accounts 
- Balance sheet analysis and position tracking
- Historical trends on balance sheet accounts
- Visualization of assets, liabilities, and net position
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List

from db_connection import (
    get_db_path_for_org, 
    execute_query,
    format_currency, 
    format_percentage
)

# Import the mask parser for account parsing
from mask_parser import get_mask_from_settings, parse_account

def render_balance_sheet_position(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Balance Sheet Position tab
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    # Header
    st.markdown(f"<h2>Balance Sheet Position - {org_display_name}</h2>", unsafe_allow_html=True)
    st.markdown("Monitor your organization's financial position with balance sheet accounts and analysis.")
    
    # Get the database path for the organization
    db_path = get_db_path_for_org(org)
    
    # Load balance sheet data
    balance_data = load_balance_sheet_data(db_path)
    
    if balance_data.empty:
        st.warning("No balance sheet data available. Please check your database connection.")
        return
    
    # Classify accounts based on their names and account numbers using mask parsing
    balance_data['Category'] = 'Unknown'
    
    # Get the balance sheet mask from settings
    balance_sheet_mask = get_mask_from_settings("BalanceSheet")
    
    # Parse account numbers if mask is available
    if balance_sheet_mask:
        # Add account segment columns
        try:
            # Apply mask parser to extract meaningful segments from account numbers
            for index, row in balance_data.iterrows():
                if 'AccountNumber' in row:
                    account_number = str(row['AccountNumber'])
                    segments = parse_account(account_number, balance_sheet_mask)
                    
                    # Add segments as new columns
                    for segment_name, segment_value in segments.items():
                        if segment_name not in balance_data.columns:
                            balance_data[segment_name] = ""
                        balance_data.at[index, segment_name] = segment_value
        except Exception as e:
            st.warning(f"Could not parse account numbers with mask: {e}")
    
    # Perform classification based on account name patterns
    for index, row in balance_data.iterrows():
        account_name = row['AccountName'].lower()
        if 'cash' in account_name or 'receivable' in account_name or 'asset' in account_name:
            balance_data.at[index, 'Category'] = 'Asset'
        elif 'payable' in account_name or 'liability' in account_name or 'debt' in account_name:
            balance_data.at[index, 'Category'] = 'Liability'
        elif 'fund balance' in account_name or 'net position' in account_name or 'equity' in account_name:
            balance_data.at[index, 'Category'] = 'Fund Balance'
    
    # Create dashboard layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Balance Sheet Overview
        st.subheader("Balance Sheet Overview")
        
        # Get summary by category
        summary_by_type = balance_data.groupby('Category')['Actual'].sum().reset_index()
        
        # Calculate totals
        total_assets = summary_by_type[summary_by_type['Category'] == 'Asset']['Actual'].sum() if 'Asset' in summary_by_type['Category'].values else 0
        total_liabilities = summary_by_type[summary_by_type['Category'] == 'Liability']['Actual'].sum() if 'Liability' in summary_by_type['Category'].values else 0
        total_fund_balance = summary_by_type[summary_by_type['Category'] == 'Fund Balance']['Actual'].sum() if 'Fund Balance' in summary_by_type['Category'].values else 0
        
        # Add Net Position row if Fund Balance is not present
        if 'Fund Balance' not in summary_by_type['Category'].values:
            net_position = total_assets - total_liabilities
            net_position_row = pd.DataFrame({'Category': ['Fund Balance'], 'Actual': [net_position]})
            summary_by_type = pd.concat([summary_by_type, net_position_row], ignore_index=True)
        
        # Create summary bar chart
        fig = px.bar(
            summary_by_type,
            x='Category',
            y='Actual',
            title='Balance Sheet Summary',
            color='Category',
            text_auto=True,
            color_discrete_map={
                'Asset': '#0066cc',
                'Liability': '#cc0000',
                'Fund Balance': '#009900',
                'Unknown': '#999999'
            }
        )
        
        # Format y-axis as currency
        fig.update_layout(
            yaxis=dict(tickprefix="$", tickformat=","),
        )
        
        # Format hover text
        fig.update_traces(
            hovertemplate='%{x}<br>%{y:$,.2f}<extra></extra>',
            texttemplate='%{y:$,.2f}', 
            textposition='outside'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Balance Sheet Detail by Fund
        st.subheader("Balance Sheet by Fund")
        
        # Group by Fund and Category
        fund_summary = balance_data.groupby(['Fund', 'Category'])['Actual'].sum().reset_index()
        
        # Create stacked bar chart by fund
        fig2 = px.bar(
            fund_summary,
            x='Fund',
            y='Actual',
            color='Category',
            barmode='group',
            title='Balance Sheet by Fund',
            color_discrete_map={
                'Asset': '#0066cc',
                'Liability': '#cc0000',
                'Fund Balance': '#009900',
                'Unknown': '#999999'
            }
        )
        
        # Format y-axis as currency
        fig2.update_layout(
            yaxis=dict(tickprefix="$", tickformat=","),
        )
        
        # Format hover text
        fig2.update_traces(
            hovertemplate='%{x}<br>%{y:$,.2f}<extra></extra>'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        # Financial Position Metrics
        st.subheader("Financial Position Metrics")
        
        # Calculate net position and metrics
        net_position = total_assets - total_liabilities
        current_ratio = total_assets / total_liabilities if total_liabilities > 0 else float('inf')
        net_position_ratio = net_position / total_assets if total_assets > 0 else 0
        
        # Display metrics
        st.metric("Total Assets", format_currency(total_assets))
        st.metric("Total Liabilities", format_currency(total_liabilities))
        st.metric("Fund Balance / Net Position", format_currency(total_fund_balance if total_fund_balance > 0 else net_position))
        st.metric("Current Ratio", f"{current_ratio:.2f}")
        st.metric("Net Position Ratio", format_percentage(net_position_ratio * 100))
        
    # Detailed Balance Sheet Table
    st.subheader("Detailed Balance Sheet")
    
    # Add filters
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        selected_fund = st.selectbox(
            "Select Fund",
            options=["All Funds"] + sorted(balance_data['Fund'].unique().tolist())
        )
    
    with filter_col2:
        selected_category = st.selectbox(
            "Select Account Category",
            options=["All Categories"] + sorted(balance_data['Category'].unique().tolist())
        )
    
    # Apply filters
    filtered_data = balance_data.copy()
    
    if selected_fund != "All Funds":
        filtered_data = filtered_data[filtered_data['Fund'] == selected_fund]
    
    if selected_category != "All Categories":
        filtered_data = filtered_data[filtered_data['Category'] == selected_category]
    
    # Group by account
    account_data = filtered_data.groupby(['AccountCode', 'AccountName', 'Category'])['Actual'].sum().reset_index()
    
    # Sort by Category then AccountCode
    account_data = account_data.sort_values(['Category', 'AccountCode'])
    
    # Format currency values
    account_data['Actual'] = account_data['Actual'].apply(format_currency)
    
    # Create asset, liability, and fund balance sections
    assets = account_data[account_data['Category'] == 'Asset']
    liabilities = account_data[account_data['Category'] == 'Liability']
    fund_balance = account_data[account_data['Category'] == 'Fund Balance']
    unknown = account_data[account_data['Category'] == 'Unknown']
    
    # Display account tables
    if not assets.empty:
        st.subheader("Assets")
        st.dataframe(
            assets[['AccountCode', 'AccountName', 'Actual']],
            hide_index=True,
            use_container_width=True
        )
    
    if not liabilities.empty:
        st.subheader("Liabilities")
        st.dataframe(
            liabilities[['AccountCode', 'AccountName', 'Actual']],
            hide_index=True,
            use_container_width=True
        )
        
    if not fund_balance.empty:
        st.subheader("Fund Balance")
        st.dataframe(
            fund_balance[['AccountCode', 'AccountName', 'Actual']],
            hide_index=True,
            use_container_width=True
        )
    
    if not unknown.empty and selected_category == "All Categories":
        st.subheader("Uncategorized Accounts")
        st.info("These accounts couldn't be automatically classified as Assets, Liabilities, or Fund Balance")
        st.dataframe(
            unknown[['AccountCode', 'AccountName', 'Actual']],
            hide_index=True,
            use_container_width=True
        )

def load_balance_sheet_data(db_path):
    """
    Load balance sheet data from the database
    
    Args:
        db_path (str): Path to the database
        
    Returns:
        DataFrame: Pandas DataFrame with balance sheet data
    """
    try:
        # Query to get balance sheet accounts
        query = """
        SELECT 
            AccountCode, 
            AccountName, 
            AccountType,
            FundCode,
            FundName,
            SUM(Actual) as Actual
        FROM 
            DepartmentPerformance
        WHERE 
            AccountType = 'Balance'
        GROUP BY
            AccountCode, AccountName, AccountType, FundCode, FundName
        """
        
        # Use the database connection module to execute the query
        import sqlite3
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            st.warning("No balance sheet data found in the database.")
            return pd.DataFrame()
            
        # Rename FundName column to Fund for consistency with the rest of the app
        df = df.rename(columns={'FundName': 'Fund'})
        
        return df
    
    except Exception as e:
        st.error(f"Error loading balance sheet data: {e}")
        return pd.DataFrame()