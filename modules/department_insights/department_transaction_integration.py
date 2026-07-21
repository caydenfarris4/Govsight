"""
Department Transaction Integration Module

This module integrates transaction data with department insights, providing:
- GL account balances by department
- Transaction breakdowns for each account
- Historical transaction analysis by department
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from modules.database.db_connection import (
    load_transaction_data, 
    load_department_transactions, 
    format_currency, 
    get_connection, 
    get_gl_account_balances,
    get_department_monthly_trend, 
    get_selected_database
)

def get_department_transactions(department=None):
    """
    Load transaction data filtered by department using the consolidated database connection
    
    Args:
        department (str, optional): Department to filter by. If None, returns all transactions.
        
    Returns:
        DataFrame: Pandas DataFrame with transaction data for the specified department
    """
    # Use the centralized database connection to load department transactions
    # This ensures we're using the database selected in the admin panel
    return load_department_transactions(department)

# Use the centralized get_gl_account_balances function from db_connection.py
# No need to duplicate the function here as we're using the one from the main module
    
    # Sort by absolute balance (largest amounts first)
    gl_balances = gl_balances.sort_values(by='Balance', key=abs, ascending=False)
    
    return gl_balances

def get_department_monthly_trend(transactions_df):
    """
    Calculate monthly transaction trends for a department
    
    Args:
        transactions_df (DataFrame): Pandas DataFrame with transaction data
        
    Returns:
        DataFrame: Pandas DataFrame with monthly transaction totals
    """
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Extract year and month from the transaction date
    transactions_df['Year'] = transactions_df['TransactionDate'].dt.year
    transactions_df['Month'] = transactions_df['TransactionDate'].dt.month
    transactions_df['YearMonth'] = transactions_df['TransactionDate'].dt.strftime('%Y-%m')
    
    # Group by year-month and calculate total amounts
    monthly_trend = transactions_df.groupby('YearMonth').agg({
        'Amount': 'sum',
        'pk_Transaction': 'count'
    }).reset_index()
    
    # Sort by year-month
    monthly_trend = monthly_trend.sort_values(by='YearMonth')
    
    # Add formatted amount column
    monthly_trend['FormattedAmount'] = monthly_trend['Amount'].apply(format_currency)
    
    return monthly_trend

def display_department_transaction_analysis(department=None):
    """
    Display transaction analysis for a department
    
    Args:
        department (str, optional): Department to analyze. If None, analyzes all transactions.
    """
    # Load transaction data for the department
    transactions_df = get_department_transactions(department)
    
    if transactions_df.empty:
        st.warning("No transaction data found for this department.")
        return
    
    # Display basic transaction metrics
    total_transactions = len(transactions_df)
    total_amount = transactions_df['Amount'].sum()
    avg_transaction = transactions_df['Amount'].mean()
    date_range = f"{transactions_df['TransactionDate'].min().date()} to {transactions_df['TransactionDate'].max().date()}"
    
    # Summary metrics
    st.subheader("Transaction Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Transactions", f"{total_transactions:,}")
    
    with col2:
        st.metric("Total Amount", format_currency(total_amount))
    
    with col3:
        st.metric("Average Transaction", format_currency(avg_transaction))
    
    st.caption(f"Transaction date range: {date_range}")
    
    # GL Account Balances
    st.subheader("GL Account Balances")
    gl_balances = get_gl_account_balances(transactions_df)
    
    if not gl_balances.empty:
        # Add formatted amount column
        gl_balances['FormattedBalance'] = gl_balances['Balance'].apply(format_currency)
        
        # Show table of GL account balances
        st.dataframe(
            gl_balances[['GLAccount', 'FormattedBalance', 'TransactionCount']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "GLAccount": st.column_config.TextColumn("GL Account"),
                "FormattedBalance": st.column_config.TextColumn("Balance"),
                "TransactionCount": st.column_config.NumberColumn("Transaction Count")
            }
        )
        
        # Top 10 GL accounts by balance visualization
        top_gl_accounts = gl_balances.head(10)
        fig = px.bar(
            top_gl_accounts,
            x='GLAccount',
            y='Balance',
            title="Top 10 GL Accounts by Balance",
            labels={"GLAccount": "GL Account", "Balance": "Balance Amount"},
            color='Balance',
            color_continuous_scale=px.colors.diverging.RdBu_r
        )
        fig.update_layout(yaxis_tickformat='$,.2f')
        st.plotly_chart(fig, use_container_width=True)
    
    # Monthly Transaction Trend
    st.subheader("Monthly Transaction Trend")
    monthly_trend = get_department_monthly_trend(transactions_df)
    
    if not monthly_trend.empty:
        fig = px.line(
            monthly_trend,
            x='YearMonth',
            y='Amount',
            title="Monthly Transaction Amounts",
            labels={"YearMonth": "Month", "Amount": "Total Amount"},
            markers=True
        )
        fig.update_layout(yaxis_tickformat='$,.2f')
        st.plotly_chart(fig, use_container_width=True)
        
        # Monthly transaction count trend
        fig = px.line(
            monthly_trend,
            x='YearMonth',
            y='pk_Transaction',
            title="Monthly Transaction Count",
            labels={"YearMonth": "Month", "pk_Transaction": "Transaction Count"},
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Transaction Details
    st.subheader("Transaction Details")
    
    # Date range filter
    date_min = transactions_df['TransactionDate'].min().date()
    date_max = transactions_df['TransactionDate'].max().date()
    
    # Create date filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", date_min)
    with col2:
        end_date = st.date_input("End Date", date_max)
    
    # Filter by date range
    date_filtered_df = transactions_df[
        (transactions_df['TransactionDate'].dt.date >= start_date) &
        (transactions_df['TransactionDate'].dt.date <= end_date)
    ]
    
    # Amount filter
    min_amount = float(transactions_df['Amount'].min())
    max_amount = float(transactions_df['Amount'].max())
    amount_range = st.slider(
        "Amount Range",
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount)
    )
    
    # Filter by amount range
    filtered_df = date_filtered_df[
        (date_filtered_df['Amount'] >= amount_range[0]) &
        (date_filtered_df['Amount'] <= amount_range[1])
    ]
    
    # GL Account filter
    gl_accounts = sorted(filtered_df['GLAccount'].unique())
    selected_accounts = st.multiselect("GL Accounts", gl_accounts)
    
    if selected_accounts:
        filtered_df = filtered_df[filtered_df['GLAccount'].isin(selected_accounts)]
    
    # Sort options
    sort_options = {
        "Date (Newest First)": ("TransactionDate", False),
        "Date (Oldest First)": ("TransactionDate", True),
        "Amount (Highest First)": ("Amount", False),
        "Amount (Lowest First)": ("Amount", True)
    }
    
    sort_by = st.selectbox("Sort by", list(sort_options.keys()))
    sort_col, sort_asc = sort_options[sort_by]
    
    filtered_df = filtered_df.sort_values(sort_col, ascending=sort_asc)
    
    # Show filtered transactions
    if len(filtered_df) > 0:
        st.write(f"Showing {len(filtered_df)} transactions")
        
        # Format the amount column
        filtered_df['FormattedAmount'] = filtered_df['Amount'].apply(format_currency)
        
        # Select columns to display
        display_cols = [
            'TransactionDate', 'GLAccount', 'FormattedAmount', 
            'Type', 'ReferenceNumber'
        ]
        
        # Add Fund, Dept, Object columns if available
        account_segments = [col for col in filtered_df.columns if col in ['Fund', 'Dept', 'Object']]
        if account_segments:
            display_cols = ['TransactionDate', 'GLAccount'] + account_segments + ['FormattedAmount', 'Type', 'ReferenceNumber']
        
        # Display the transactions
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "TransactionDate": st.column_config.DateColumn("Date"),
                "GLAccount": st.column_config.TextColumn("GL Account"),
                "FormattedAmount": st.column_config.TextColumn("Amount"),
                "Type": st.column_config.TextColumn("Type"),
                "ReferenceNumber": st.column_config.TextColumn("Reference")
            }
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Filtered Transactions",
            csv,
            "department_transactions.csv",
            "text/csv",
            key='download-dept-csv'
        )
    else:
        st.info("No transactions match the current filters.")