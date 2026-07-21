"""
Transaction Analyzer Module

This module provides tools for analyzing transaction-level data from the Caselle GL database.
It shows transaction breakdowns by department, fund, and account with proper handling of 
credit transactions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from dateutil.relativedelta import relativedelta

from db_connection_central import (
    load_transaction_data, 
    get_department_list,
    get_gl_account_balances,
    get_department_monthly_trend,
    format_currency
)

def run_transaction_analyzer():
    """Main function to run the transaction analyzer dashboard"""
    st.title("🧾 GL Transaction Analyzer")
    
    # Introduction
    st.markdown("""
    This dashboard allows you to analyze transaction-level data across your general ledger.
    Select different filters and visualization options to gain insights into transaction patterns.
    """)
    
    # Load transaction data
    with st.spinner("Loading transaction data..."):
        try:
            # Get transaction data
            transactions_df = load_transaction_data()
            
            if transactions_df.empty:
                st.error("No transaction data found. Please check your database connection.")
                st.stop()
                
            # Display basic statistics
            st.success(f"Loaded {len(transactions_df):,} transactions successfully!")
        except Exception as e:
            st.error(f"Error loading transaction data: {e}")
            st.stop()
    
    # Create a date filter
    col1, col2 = st.columns(2)
    with col1:
        min_date = transactions_df['TransactionDate'].min().date()
        max_date = transactions_df['TransactionDate'].max().date()
        start_date = st.date_input("Start Date", min_date)
    
    with col2:
        end_date = st.date_input("End Date", max_date)
    
    if start_date > end_date:
        st.error("End date must be after start date")
        st.stop()
    
    # Filter data by date
    filtered_df = transactions_df[
        (transactions_df['TransactionDate'].dt.date >= start_date) &
        (transactions_df['TransactionDate'].dt.date <= end_date)
    ].copy()
    
    # Check if we have filtered data
    if filtered_df.empty:
        st.warning("No transactions found for the selected date range.")
        st.stop()
    
    # Department filter
    departments = ["All Departments"] + get_department_list()
    selected_dept = st.selectbox("Select Department", departments)
    
    if selected_dept != "All Departments":
        # Filter by department
        dept_filter = filtered_df['Department'] == selected_dept
        filtered_df = filtered_df[dept_filter]
        
        if filtered_df.empty:
            st.warning(f"No transactions found for {selected_dept} in the selected date range.")
            st.stop()
    
    # Display transaction type filter (show Credits or not)
    transaction_types = st.multiselect(
        "Transaction Types", 
        ["Debits", "Credits"],
        default=["Debits", "Credits"]
    )
    
    if transaction_types:
        if "Debits" in transaction_types and "Credits" in transaction_types:
            # Keep all transactions
            pass
        elif "Debits" in transaction_types:
            # Only show debits (positive Amount)
            filtered_df = filtered_df[filtered_df['Amount'] > 0]
        elif "Credits" in transaction_types:
            # Only show credits (Type is 'Credit' or DepositAmount > 0)
            filtered_df = filtered_df[
                (filtered_df['Type'] == 'Credit') | 
                (filtered_df['DepositAmount'] > 0)
            ]
    
    # Check if we have filtered data again
    if filtered_df.empty:
        st.warning("No transactions found with the current filters.")
        st.stop()
    
    # Tabs for different analysis views
    tab1, tab2, tab3, tab4 = st.tabs([
        " Overview", 
        " Trend Analysis", 
        " Transaction Details",
        "🧮 Account Breakdown"
    ])
    
    # Overview Tab
    with tab1:
        st.header("Transaction Overview")
        
        # Summary metrics
        total_transactions = len(filtered_df)
        total_amount = filtered_df['TransactionAmount'].sum() if 'TransactionAmount' in filtered_df.columns else filtered_df['Amount'].sum()
        avg_transaction = filtered_df['TransactionAmount'].mean() if 'TransactionAmount' in filtered_df.columns else filtered_df['Amount'].mean()
        
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("Total Transactions", f"{total_transactions:,}")
        with metrics_col2:
            st.metric("Total Amount", format_currency(total_amount))
        with metrics_col3:
            st.metric("Average Transaction", format_currency(avg_transaction))
        
        # Transaction type distribution
        st.subheader("Transaction Distribution")
        
        # Prepare data for visualization
        credits_df = filtered_df[(filtered_df['Type'] == 'Credit') | (filtered_df['DepositAmount'] > 0)]
        debits_df = filtered_df[(filtered_df['Type'] != 'Credit') & ((filtered_df['DepositAmount'] <= 0) | pd.isna(filtered_df['DepositAmount']))]
        
        credits_amount = credits_df['TransactionAmount'].sum() if 'TransactionAmount' in credits_df.columns else credits_df['Amount'].sum()
        debits_amount = debits_df['TransactionAmount'].sum() if 'TransactionAmount' in debits_df.columns else debits_df['Amount'].sum()
        
        # Create a distribution chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Debits", "Credits"],
            y=[debits_amount, credits_amount],
            marker_color=['#2E86C1', '#E74C3C']
        ))
        fig.update_layout(
            title="Debit vs Credit Distribution",
            yaxis_title="Amount",
            xaxis_title="Transaction Type"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Top accounts by volume
        st.subheader("Top Accounts by Transaction Volume")
        
        # Group by account
        account_volume = filtered_df.groupby('GLAccount').size().reset_index(name='Count')
        account_volume = account_volume.sort_values('Count', ascending=False).head(10)
        
        # Create bar chart of top accounts
        fig = px.bar(
            account_volume, 
            x='GLAccount', 
            y='Count',
            title="Top 10 Accounts by Transaction Count",
            labels={"GLAccount": "GL Account", "Count": "Number of Transactions"},
            color='Count',
            color_continuous_scale=px.colors.sequential.Blues
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Top accounts by amount
        st.subheader("Top Accounts by Transaction Amount")
        
        # Group by account
        amount_col = 'TransactionAmount' if 'TransactionAmount' in filtered_df.columns else 'Amount'
        account_amount = filtered_df.groupby('GLAccount')[amount_col].sum().reset_index()
        account_amount = account_amount.sort_values(amount_col, ascending=False).head(10)
        
        # Create bar chart of top accounts by amount
        fig = px.bar(
            account_amount, 
            x='GLAccount', 
            y=amount_col,
            title="Top 10 Accounts by Transaction Amount",
            labels={"GLAccount": "GL Account", amount_col: "Total Amount"},
            color=amount_col,
            color_continuous_scale=px.colors.sequential.Greens
        )
        fig.update_layout(yaxis_tickformat='$,.2f')
        st.plotly_chart(fig, use_container_width=True)
        
        # Department distribution
        if selected_dept == "All Departments":
            st.subheader("Department Distribution")
            
            # Group by department
            dept_amount = filtered_df.groupby('Department')[amount_col].sum().reset_index()
            dept_amount = dept_amount.sort_values(amount_col, ascending=False)
            
            # Create pie chart of department distribution
            fig = px.pie(
                dept_amount,
                values=amount_col,
                names='Department',
                title="Transaction Amount by Department",
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    # Trend Analysis Tab
    with tab2:
        st.header("Transaction Trend Analysis")
        
        # Time period selection
        period_options = ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]
        selected_period = st.selectbox("Select Time Period", period_options)
        
        # Group by selected time period
        if selected_period == "Daily":
            filtered_df['Period'] = filtered_df['TransactionDate'].dt.date
        elif selected_period == "Weekly":
            filtered_df['Period'] = filtered_df['TransactionDate'].dt.to_period('W').astype(str)
        elif selected_period == "Monthly":
            filtered_df['Period'] = filtered_df['TransactionDate'].dt.to_period('M').astype(str)
        elif selected_period == "Quarterly":
            filtered_df['Period'] = filtered_df['TransactionDate'].dt.to_period('Q').astype(str)
        else:  # Yearly
            filtered_df['Period'] = filtered_df['TransactionDate'].dt.year
        
        # Group by period
        amount_col = 'TransactionAmount' if 'TransactionAmount' in filtered_df.columns else 'Amount'
        period_data = filtered_df.groupby('Period').agg({
            amount_col: ['sum', 'mean', 'count']
        }).reset_index()
        
        # Flatten the column names
        period_data.columns = ['Period', 'Total_Amount', 'Average_Amount', 'Transaction_Count']
        
        # Ensure period is sorted correctly
        period_data = period_data.sort_values('Period')
        
        # Create line chart for trends
        st.subheader(f"{selected_period} Transaction Trends")
        
        # Create tabs for different trend views
        trend_tab1, trend_tab2, trend_tab3 = st.tabs([
            "Transaction Count", "Total Amount", "Average Amount"
        ])
        
        with trend_tab1:
            fig = px.line(
                period_data, 
                x='Period', 
                y='Transaction_Count',
                title=f"{selected_period} Transaction Count",
                markers=True,
                labels={"Period": selected_period, "Transaction_Count": "Number of Transactions"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with trend_tab2:
            fig = px.line(
                period_data, 
                x='Period', 
                y='Total_Amount',
                title=f"{selected_period} Total Transaction Amount",
                markers=True,
                labels={"Period": selected_period, "Total_Amount": "Total Amount"}
            )
            fig.update_layout(yaxis_tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        
        with trend_tab3:
            fig = px.line(
                period_data, 
                x='Period', 
                y='Average_Amount',
                title=f"{selected_period} Average Transaction Amount",
                markers=True,
                labels={"Period": selected_period, "Average_Amount": "Average Amount"}
            )
            fig.update_layout(yaxis_tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        
        # Transaction volume heatmap
        st.subheader("Transaction Volume Heatmap")
        
        # Add month and day of week columns
        filtered_df['Month'] = filtered_df['TransactionDate'].dt.month_name()
        filtered_df['DayOfWeek'] = filtered_df['TransactionDate'].dt.day_name()
        
        # Create a pivot table for the heatmap
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        heatmap_data = pd.pivot_table(
            filtered_df,
            values=amount_col,
            index='Month',
            columns='DayOfWeek',
            aggfunc='count',
            fill_value=0
        )
        
        # Reorder the index and columns
        heatmap_data = heatmap_data.reindex(month_order, axis=0)
        heatmap_data = heatmap_data.reindex(day_order, axis=1)
        
        # Create heatmap
        fig = px.imshow(
            heatmap_data,
            labels=dict(x="Day of Week", y="Month", color="Transaction Count"),
            x=heatmap_data.columns,
            y=heatmap_data.index,
            color_continuous_scale="Viridis"
        )
        fig.update_layout(title="Transaction Volume by Day of Week and Month")
        st.plotly_chart(fig, use_container_width=True)
    
    # Transaction Details Tab
    with tab3:
        st.header("Transaction Details")
        
        # Add filters
        st.subheader("Filter Transactions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Get unique accounts
            accounts = sorted(filtered_df['GLAccount'].unique())
            selected_accounts = st.multiselect("Select GL Accounts", accounts)
        
        with col2:
            # Amount range
            amount_col = 'TransactionAmount' if 'TransactionAmount' in filtered_df.columns else 'Amount'
            min_amount = float(filtered_df[amount_col].min())
            max_amount = float(filtered_df[amount_col].max())
            amount_range = st.slider(
                "Amount Range",
                min_value=min_amount,
                max_value=max_amount,
                value=(min_amount, max_amount)
            )
        
        # Apply filters
        detail_df = filtered_df.copy()
        
        if selected_accounts:
            detail_df = detail_df[detail_df['GLAccount'].isin(selected_accounts)]
        
        amount_col = 'TransactionAmount' if 'TransactionAmount' in detail_df.columns else 'Amount'
        detail_df = detail_df[
            (detail_df[amount_col] >= amount_range[0]) &
            (detail_df[amount_col] <= amount_range[1])
        ]
        
        # Sort options
        sort_options = {
            "Date (Newest First)": ("TransactionDate", False),
            "Date (Oldest First)": ("TransactionDate", True),
            "Amount (Highest First)": (amount_col, False),
            "Amount (Lowest First)": (amount_col, True)
        }
        
        sort_by = st.selectbox("Sort by", list(sort_options.keys()))
        sort_col, sort_asc = sort_options[sort_by]
        
        detail_df = detail_df.sort_values(sort_col, ascending=sort_asc)
        
        # Display transaction details
        st.subheader("Transaction List")
        st.write(f"Showing {len(detail_df)} transactions")
        
        # Format the amount as currency
        detail_df['FormattedAmount'] = detail_df[amount_col].apply(lambda x: format_currency(x))
        
        # Select columns to display
        display_cols = [
            'TransactionDate', 'GLAccount', 'Department', 'FormattedAmount', 
            'Type', 'ReferenceNumber'
        ]
        
        # Add Fund, Dept, Object columns if available
        account_segments = [col for col in detail_df.columns if col in ['Fund', 'DeptCode', 'Object']]
        if account_segments:
            display_cols = ['TransactionDate', 'GLAccount', 'Department'] + account_segments + ['FormattedAmount', 'Type', 'ReferenceNumber']
        
        # Display the data
        st.dataframe(
            detail_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "TransactionDate": st.column_config.DateColumn("Date"),
                "GLAccount": st.column_config.TextColumn("GL Account"),
                "Department": st.column_config.TextColumn("Department"),
                "FormattedAmount": st.column_config.TextColumn("Amount"),
                "Type": st.column_config.TextColumn("Type"),
                "ReferenceNumber": st.column_config.TextColumn("Reference")
            }
        )
        
        # Download option
        csv = detail_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Filtered Transactions",
            csv,
            "transaction_data.csv",
            "text/csv",
            key='download-csv'
        )
    
    # Account Breakdown Tab
    with tab4:
        st.header("Account Breakdown Analysis")
        
        # Get GL account balances
        gl_balances = get_gl_account_balances(filtered_df)
        
        if not gl_balances.empty:
            # Create visualization of account balances
            st.subheader("GL Account Balances")
            
            # Display top accounts
            st.dataframe(
                gl_balances[['GLAccount', 'FormattedBalance', 'TransactionCount']].head(20),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "GLAccount": st.column_config.TextColumn("GL Account"),
                    "FormattedBalance": st.column_config.TextColumn("Balance"),
                    "TransactionCount": st.column_config.NumberColumn("Transaction Count")
                }
            )
            
            # Create charts
            top_accounts = gl_balances.head(10)
            
            # Bar chart for top accounts by balance
            fig = px.bar(
                top_accounts,
                x='GLAccount',
                y='Balance',
                title="Top 10 GL Accounts by Balance",
                labels={"GLAccount": "GL Account", "Balance": "Balance Amount"},
                color='Balance',
                color_continuous_scale=px.colors.diverging.RdBu_r
            )
            fig.update_layout(yaxis_tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
            
            # Fund analysis 
            if 'Fund' in filtered_df.columns:
                st.subheader("Fund Analysis")
                
                # Group by fund
                fund_data = filtered_df.groupby('Fund').agg({
                    amount_col: 'sum',
                    'pk_Transaction': 'count'
                }).reset_index()
                
                fund_data.columns = ['Fund', 'Total_Amount', 'Transaction_Count']
                fund_data['Formatted_Amount'] = fund_data['Total_Amount'].apply(format_currency)
                
                # Display fund data
                st.dataframe(
                    fund_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Fund": st.column_config.TextColumn("Fund"),
                        "Formatted_Amount": st.column_config.TextColumn("Total Amount"),
                        "Transaction_Count": st.column_config.NumberColumn("Transaction Count")
                    }
                )
                
                # Create pie chart for fund distribution
                fig = px.pie(
                    fund_data,
                    values='Total_Amount',
                    names='Fund',
                    title="Transaction Amount by Fund",
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
                
            # Department analysis (if all departments are selected)
            if selected_dept == "All Departments" and 'Department' in filtered_df.columns:
                st.subheader("Department Analysis")
                
                # Group by department
                dept_data = filtered_df.groupby('Department').agg({
                    amount_col: 'sum',
                    'pk_Transaction': 'count'
                }).reset_index()
                
                dept_data.columns = ['Department', 'Total_Amount', 'Transaction_Count']
                dept_data['Formatted_Amount'] = dept_data['Total_Amount'].apply(format_currency)
                
                # Display department data
                st.dataframe(
                    dept_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Department": st.column_config.TextColumn("Department"),
                        "Formatted_Amount": st.column_config.TextColumn("Total Amount"),
                        "Transaction_Count": st.column_config.NumberColumn("Transaction Count")
                    }
                )
                
                # Create bar chart for department comparison
                fig = px.bar(
                    dept_data,
                    x='Department',
                    y='Total_Amount',
                    title="Transaction Amount by Department",
                    labels={"Department": "Department", "Total_Amount": "Total Amount"},
                    color='Total_Amount',
                    color_continuous_scale=px.colors.sequential.Viridis
                )
                fig.update_layout(yaxis_tickformat='$,.2f')
                st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_transaction_analyzer()