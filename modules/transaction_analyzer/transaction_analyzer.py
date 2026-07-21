"""
Transaction Analyzer Module

This module handles visualization and analysis of transaction-level data from the financial system.
It provides insights into transaction patterns, department spending, and account balances.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
from typing import Dict, List, Optional, Tuple

# Import from centralized database connection module
from modules.database.db_connection import (
    load_transaction_data,
    get_department_list,
    load_department_transactions,
    get_gl_account_balances,
    get_department_monthly_trend,
    format_currency
)

# Import new centralized reporting integration
try:
    from modules.vatica.reports_integration import vatica_reports
    REPORTS_INTEGRATION_AVAILABLE = True
except ImportError:
    REPORTS_INTEGRATION_AVAILABLE = False

def run_transaction_analyzer():
    """
    Main function to render the Transaction Analyzer tab
    """
    st.title("Transaction Analyzer")
    
    st.markdown("""
    This module provides detailed analysis of transaction data with filtering by department,
    date range, and transaction type. Visualize transaction patterns and account balances.
    """)
    
    # Get all departments
    departments = get_department_list()
    if not departments:
        st.error("No department data found. Please check database connection.")
        return
        
    # Add 'All Departments' option at the beginning
    all_depts = ["All Departments"] + departments
    
    # Sidebar for filters
    with st.sidebar:
        st.header("Transaction Filters")
        
        # Department filter
        selected_dept = st.selectbox("Department", all_depts, index=0)
        
        # Date range filter
        try:
            # Get all transaction data to determine date range
            all_data = load_transaction_data()
            if not all_data.empty:
                min_date = all_data['TransactionDate'].min().date()
                max_date = all_data['TransactionDate'].max().date()
                
                # Create date range slider
                date_range = st.date_input(
                    "Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
            else:
                st.warning("No transaction data available.")
                date_range = None
        except Exception as e:
            st.error(f"Error loading transaction dates: {e}")
            date_range = None
            
        # Transaction type filter
        trans_type = st.multiselect(
            "Transaction Direction",
            ["Debit", "Credit"],
            default=["Debit", "Credit"]
        )
        
        # Amount range filter
        st.subheader("Amount Range")
        try:
            if not all_data.empty:
                min_amount = float(all_data['TransactionAmount'].min())
                max_amount = float(all_data['TransactionAmount'].max())
                
                # Create amount range slider
                amount_range = st.slider(
                    "Amount",
                    min_value=min_amount,
                    max_value=max_amount,
                    value=(min_amount, max_amount),
                    format="$%f"
                )
            else:
                amount_range = None
        except Exception as e:
            st.error(f"Error setting amount range: {e}")
            amount_range = None
            
    # Load transaction data based on department selection
    transactions_df = load_department_transactions(selected_dept if selected_dept != "All Departments" else None)
    
    if transactions_df.empty:
        st.warning(f"No transaction data found for {selected_dept}.")
        return
        
    # Apply filters
    filtered_df = filter_transactions(
        transactions_df,
        date_range=date_range, 
        trans_type=trans_type,
        amount_range=amount_range
    )
    
    if filtered_df.empty:
        st.warning("No transactions match the selected filters.")
        return
    
    # Display transaction summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Transactions", f"{len(filtered_df):,}")
    with col2:
        total_amount = filtered_df['TransactionAmount'].sum()
        st.metric("Total Amount", format_currency(total_amount))
    with col3:
        credits = filtered_df[filtered_df['Direction'] == 'Credit']['TransactionAmount'].sum()
        st.metric("Total Credits", format_currency(credits))
    with col4:
        debits = filtered_df[filtered_df['Direction'] == 'Debit']['TransactionAmount'].sum()
        st.metric("Total Debits", format_currency(debits))
        
    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs([
        "Monthly Trends", 
        "GL Account Balances", 
        "Transaction Details",
        "Department Comparison"
    ])
    
    with tab1:
        display_monthly_trends(filtered_df, selected_dept)
        
    with tab2:
        display_gl_account_balances(filtered_df)
        
    with tab3:
        display_transaction_details(filtered_df)
        
    with tab4:
        if selected_dept == "All Departments":
            display_department_comparison(transactions_df)
        else:
            st.info("Select 'All Departments' to view department comparison.")

def filter_transactions(df, date_range=None, trans_type=None, amount_range=None):
    """
    Filter transactions based on selected criteria
    
    Args:
        df (DataFrame): Transaction data
        date_range (tuple): Start and end date
        trans_type (list): Transaction types to include
        amount_range (tuple): Min and max amount
        
    Returns:
        DataFrame: Filtered transaction data
    """
    filtered_df = df.copy()
    
    # Apply date filter
    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['TransactionDate'].dt.date >= start_date) &
            (filtered_df['TransactionDate'].dt.date <= end_date)
        ]
    
    # Apply transaction type filter
    if trans_type and len(trans_type) > 0:
        filtered_df = filtered_df[filtered_df['Direction'].isin(trans_type)]
    
    # Apply amount filter
    if amount_range and len(amount_range) == 2:
        min_amount, max_amount = amount_range
        filtered_df = filtered_df[
            (filtered_df['TransactionAmount'] >= min_amount) &
            (filtered_df['TransactionAmount'] <= max_amount)
        ]
    
    return filtered_df

def display_monthly_trends(df, department):
    """
    Display monthly transaction trends
    
    Args:
        df (DataFrame): Filtered transaction data
        department (str): Selected department
    """
    st.subheader(f"Monthly Transaction Trends - {department}")
    
    # Get monthly trend data
    monthly_df = get_department_monthly_trend(df)
    
    if monthly_df.empty:
        st.warning("No monthly trend data available.")
        return
    
    # Create line chart for monthly trends
    fig = px.line(
        monthly_df,
        x='YearMonth',
        y='TransactionAmount',
        title=f"Monthly Transaction Amounts - {department}",
        markers=True,
        labels={"YearMonth": "Month", "TransactionAmount": "Amount"}
    )
    
    # Add labels
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Transaction Amount",
        yaxis_tickformat='$,.2f',
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"monthly_trend_{department}")
    
    # Show transaction counts by month
    fig_count = px.bar(
        monthly_df,
        x='YearMonth',
        y='pk_Transaction',
        title=f"Monthly Transaction Counts - {department}",
        labels={"YearMonth": "Month", "pk_Transaction": "Transaction Count"}
    )
    
    fig_count.update_layout(
        xaxis_title="Month",
        yaxis_title="Transaction Count",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig_count, use_container_width=True, key=f"monthly_count_{department}")
    
    # Show monthly data table
    st.subheader("Monthly Data")
    st.dataframe(monthly_df[['YearMonth', 'TransactionAmount', 'pk_Transaction', 'FormattedAmount']])

def display_gl_account_balances(df):
    """
    Display GL account balances
    
    Args:
        df (DataFrame): Filtered transaction data
    """
    st.subheader("GL Account Balances")
    
    # Get GL account balances
    balances_df = get_gl_account_balances(df)
    
    if balances_df.empty:
        st.warning("No GL account balance data available.")
        return
    
    # Show top accounts by balance
    top_n = st.slider("Number of top accounts to display", 5, 20, 10)
    top_balances = balances_df.head(top_n)
    
    # Create bar chart for top GL accounts with proper number formatting
    fig = px.bar(
        top_balances,
        x='GLAccount',
        y='Balance',
        title=f"Top {top_n} GL Accounts by Balance",
        color='Balance',
        color_continuous_scale=px.colors.sequential.Blues,
        text=[f'${val:,.0f}' for val in top_balances['Balance']]  # Prevent truncation
    )
    
    # Add labels
    fig.update_layout(
        xaxis_title="GL Account",
        yaxis_title="Balance",
        yaxis_tickformat='$,.2f',
        xaxis_tickangle=-45
    )
    
    # Show actual values on bars
    fig.update_traces(textposition='outside')
    
    st.plotly_chart(fig, use_container_width=True, key=f"gl_account_balances_top{top_n}")
    
    # Show GL account balance table
    st.subheader("GL Account Details")
    st.dataframe(balances_df)

def display_transaction_details(df):
    """
    Display transaction details in a table
    
    Args:
        df (DataFrame): Filtered transaction data
    """
    st.subheader("Transaction Details")
    
    # Show number of records
    st.info(f"Showing {len(df):,} transaction records")
    
    # Add pagination
    page_size = st.slider("Rows per page", 10, 100, 25)
    total_pages = (len(df) - 1) // page_size + 1
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    
    # Create paginated view
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, len(df))
    
    # Show paginated data
    paginated_df = df.iloc[start_idx:end_idx].copy()
    
    # Format date for display
    paginated_df['DisplayDate'] = paginated_df['TransactionDate'].dt.strftime('%Y-%m-%d')
    
    # Select columns to display
    display_columns = [
        'DisplayDate', 
        'GLAccount', 
        'Direction',
        'FormattedAmount', 
        'Fund', 
        'Department',
        'ReferenceNumber', 
        'SequenceNumber'
    ]
    
    # Filter to only columns that exist
    valid_columns = [col for col in display_columns if col in paginated_df.columns]
    
    # Display the dataframe
    st.dataframe(paginated_df[valid_columns], use_container_width=True)
    
    # Export options
    if st.button("Export to CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def display_department_comparison(df):
    """
    Display department comparison
    
    Args:
        df (DataFrame): Transaction data for all departments
    """
    st.subheader("Department Comparison")
    
    if 'Department' not in df.columns:
        st.warning("Department information missing in transaction data.")
        return
    
    # Aggregate by department
    dept_summary = df.groupby('Department').agg({
        'TransactionAmount': 'sum',
        'pk_Transaction': 'count'
    }).reset_index()
    
    # Sort by total amount
    dept_summary = dept_summary.sort_values('TransactionAmount', ascending=False)
    
    # Add formatted amount
    dept_summary['FormattedAmount'] = dept_summary['TransactionAmount'].apply(format_currency)
    
    # Create bar chart for department comparison with proper formatting
    fig = px.bar(
        dept_summary,
        x='Department',
        y='TransactionAmount',
        title="Total Transaction Amount by Department",
        color='Department',
        text=[f'${val:,.0f}' for val in dept_summary['TransactionAmount']]  # Prevent truncation
    )
    
    # Add labels
    fig.update_layout(
        xaxis_title="Department",
        yaxis_title="Total Amount",
        yaxis_tickformat='$,.2f'
    )
    
    # Show actual values on bars
    fig.update_traces(textposition='outside')
    
    st.plotly_chart(fig, use_container_width=True, key="dept_comparison_amount")
    
    # Transaction count by department
    fig_count = px.pie(
        dept_summary,
        values='pk_Transaction',
        names='Department',
        title="Transaction Count by Department"
    )
    
    # Improve pie chart layout
    fig_count.update_traces(textposition='inside', textinfo='percent+label')
    
    st.plotly_chart(fig_count, use_container_width=True, key="dept_comparison_count")
    
    # Show department summary table
    st.subheader("Department Summary")
    st.dataframe(dept_summary)

if __name__ == "__main__":
    run_transaction_analyzer()