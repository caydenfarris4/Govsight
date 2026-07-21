"""
Transaction Data Connection Module

This module handles loading and processing transaction data from the Caselle GL database.
It provides functions for transaction analysis with proper handling of department codes
and credit transactions.
"""

import pandas as pd
import json
import os
import sqlite3
from typing import Dict, Any, Optional, List

def load_settings():
    """
    Load settings from system_settings.json
    
    Returns:
        Dict: Settings as a dictionary
    """
    try:
        if os.path.exists("system_settings.json"):
            with open("system_settings.json", "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}

def format_currency(value):
    """
    Format a numeric value as currency with exactly two decimal places
    
    Args:
        value (float or int): The numeric value to format
        
    Returns:
        str: Formatted string with commas and exactly two decimal places
    """
    if pd.isna(value):
        return "$0.00"
    return "${:,.2f}".format(float(value))

def get_connection(db_path: str = "databases/core/caselle_gl0_mock.db"):
    """
    Create a connection to the SQLite database
    
    Args:
        db_path (str, optional): Path to the database. If None, uses the default path.
        
    Returns:
        Connection: Database connection
    """
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_department_list() -> List[str]:
    """
    Get the list of department names from the transaction database
    
    Returns:
        List[str]: List of department names
    """
    dept_mapping = {
        '01': 'Administration',
        '02': 'Finance',  
        '03': 'Police',
        '04': 'Fire'
    }
    
    return list(dept_mapping.values())

def load_transaction_data() -> pd.DataFrame:
    """
    Load all transaction data from the database with proper parsing
    of GL accounts and department codes
    
    Returns:
        DataFrame: Pandas DataFrame with transaction data
    """
    try:
        # Connect to the Caselle database
        conn = get_database_connection()
        
        # Query to get all transactions including credits (deposits)
        query = """
        SELECT 
            pk_Transaction, 
            GLAccount, 
            TransactionDate, 
            Type, 
            Amount,
            DepositAmount, 
            CheckAmount, 
            ReferenceNumber, 
            SequenceNumber,
            CASE
                WHEN Type = 'Credit' OR DepositAmount > 0 THEN DepositAmount
                ELSE Amount
            END as TransactionAmount
        FROM tblTransaction
        """
        
        # Load data into DataFrame
        df = pd.read_sql_query(query, conn)
        
        # Close connection
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        # Convert date column to datetime
        df['TransactionDate'] = pd.to_datetime(df['TransactionDate'])
        
        # Extract GL account segments directly from the account code
        # In Caselle GL, the format is typically FF-DD-OOOO where:
        # FF = Fund code (positions 0-1)
        # DD = Department code (positions 3-4)
        # OOOO = Object code (positions 6+)
        
        df['Fund'] = df['GLAccount'].apply(lambda x: x.split('-')[0] if isinstance(x, str) and '-' in x else '')
        df['DeptCode'] = df['GLAccount'].apply(lambda x: x.split('-')[1] if isinstance(x, str) and '-' in x and len(x.split('-')) > 1 else '')
        df['Object'] = df['GLAccount'].apply(lambda x: x.split('-')[2] if isinstance(x, str) and '-' in x and len(x.split('-')) > 2 else '')
        
        # Map department codes to department names
        dept_mapping = {
            '01': 'Administration',
            '02': 'Finance',  
            '03': 'Police',
            '04': 'Fire'
        }
        
        # Add department name
        df['Department'] = df['DeptCode'].map(lambda x: dept_mapping.get(x, "Other"))
        
        return df
        
    except Exception as e:
        print(f"Error loading transaction data: {e}")
        return pd.DataFrame()

def load_department_transactions(department: str = None) -> pd.DataFrame:
    """
    Load transaction data for a specific department
    
    Args:
        department (str, optional): Department name to filter by. If None, returns all transactions.
        
    Returns:
        DataFrame: Pandas DataFrame with transaction data for the specified department
    """
    # Load all transaction data
    df = load_transaction_data()
    
    if df.empty:
        return pd.DataFrame()
    
    # Map department names to codes
    dept_code_mapping = {
        'Administration': '01',
        'Finance': '02',
        'Police': '03',
        'Fire': '04'
    }
    
    # If department is specified, filter the data
    if department and department != "All Departments":
        # Try to match by department name first
        if department in dept_code_mapping:
            dept_code = dept_code_mapping[department]
            return df[df['DeptCode'] == dept_code]
        
        # Try partial matching of department names
        matching_depts = [code for name, code in dept_code_mapping.items() 
                         if department.lower() in name.lower()]
        
        if matching_depts:
            return df[df['DeptCode'].isin(matching_depts)]
            
        # As a fallback, try to filter by the Department column
        filtered_df = df[df['Department'] == department]
        if not filtered_df.empty:
            return filtered_df
            
        # Last resort: check if it's in any part of the GLAccount
        return df[df['GLAccount'].str.contains(department, case=False, na=False)]
    
    return df

def get_gl_account_balances(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate GL account balances from transaction data
    
    Args:
        transactions_df (DataFrame): Pandas DataFrame with transaction data
        
    Returns:
        DataFrame: Pandas DataFrame with GL account balances
    """
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Group by GL Account and calculate total amounts
    gl_balances = transactions_df.groupby('GLAccount').agg({
        'TransactionAmount': 'sum',
        'pk_Transaction': 'count'
    }).reset_index()
    
    # Rename columns for clarity
    gl_balances.columns = ['GLAccount', 'Balance', 'TransactionCount']
    
    # Sort by absolute balance (largest amounts first)
    gl_balances = gl_balances.sort_values(by='Balance', key=abs, ascending=False)
    
    # Add formatted balance
    gl_balances['FormattedBalance'] = gl_balances['Balance'].apply(format_currency)
    
    return gl_balances

def get_department_monthly_trend(transactions_df: pd.DataFrame) -> pd.DataFrame:
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
        'TransactionAmount': 'sum',
        'pk_Transaction': 'count'
    }).reset_index()
    
    # Sort by year-month
    monthly_trend = monthly_trend.sort_values(by='YearMonth')
    
    # Add formatted amount column
    monthly_trend['FormattedAmount'] = monthly_trend['TransactionAmount'].apply(format_currency)
    
    return monthly_trend