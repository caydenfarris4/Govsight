"""
Central Database Connection Module

This module provides a centralized connection point for all database access across the application.
It handles database selection from the admin panel and ensures consistent access patterns.
"""

import sqlite3
import pandas as pd
import json
import os
from typing import Dict, Any, Optional, List, Union

# Default database paths
DEFAULT_DB = "databases/core/caselle_gl0_mock.db"
DEFAULT_ORG = "cityA"

def _get_config_service():
    try:
        from modules.services.config_service import get_config_service
        return get_config_service()
    except Exception:
        return None

def load_settings():
    """
    Load settings from ConfigService (database-backed).
    Falls back to system_settings.json if ConfigService unavailable.
    
    Returns:
        Dict: Settings as a dictionary
    """
    svc = _get_config_service()
    if svc:
        try:
            data = svc.get_namespace("system_settings")
            if data:
                return data
        except Exception:
            pass

    try:
        for path in ["configs/system/system_settings.json", "system_settings.json"]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}

def save_settings(settings):
    """
    Save settings to ConfigService (database-backed).
    Falls back to system_settings.json if ConfigService unavailable.
    
    Args:
        settings (Dict): Settings dictionary to save
    """
    svc = _get_config_service()
    if svc:
        try:
            safe_settings = {k: v for k, v in settings.items()
                            if k not in ("GoogleSheets_Credentials", "OpenAI_Key", "DefaultPassword")}
            svc.set_namespace("system_settings", safe_settings, updated_by="db_connection_central")
            return
        except Exception:
            pass

    try:
        with open("system_settings.json", "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

def get_selected_org():
    """
    Get the currently selected organization from the session state
    
    Returns:
        str: Organization identifier (e.g., 'cityA')
    """
    import streamlit as st
    
    # Get from session state if available
    if 'selected_org' in st.session_state:
        return st.session_state.selected_org
    
    # Default to cityA
    return DEFAULT_ORG

def get_selected_database():
    """
    Get the currently selected database path based on admin settings
    
    Returns:
        str: Database path
    """
    import streamlit as st
    
    # Check if a database path is explicitly set in session state
    if 'db_path' in st.session_state:
        return st.session_state.db_path
    
    # Load settings to see if there's a custom database path
    settings = load_settings()
    if 'current_database' in settings:
        return settings['current_database']
    
    # Default to the transaction database
    return DEFAULT_DB

def get_connection(db_path: Optional[str] = None):
    """
    Create a connection to the SQLite database
    
    Args:
        db_path (str, optional): Path to the database. If None, uses the selected database.
        
    Returns:
        Connection: Database connection
    """
    try:
        # If no specific path is provided, use the selected database
        if db_path is None:
            db_path = get_selected_database()
            
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

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

def load_transaction_data() -> pd.DataFrame:
    """
    Load all transaction data from the database with proper parsing
    of GL accounts and department codes
    
    Returns:
        DataFrame: Pandas DataFrame with transaction data
    """
    try:
        # Connect to the selected database
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
                WHEN DepositAmount > 0 THEN DepositAmount
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
        
        # Add transaction direction (Debit/Credit)
        df['Direction'] = df.apply(
            lambda x: 'Credit' if x['DepositAmount'] > 0 else 'Debit', 
            axis=1
        )
        
        # Add formatted amount for display
        df['FormattedAmount'] = df['TransactionAmount'].apply(format_currency)
        
        return df
        
    except Exception as e:
        print(f"Error loading transaction data: {e}")
        return pd.DataFrame()

def get_department_list() -> List[str]:
    """
    Get the list of department names from the transaction database
    
    Returns:
        List[str]: List of department names
    """
    # Get all transactions with department mapping
    df = load_transaction_data()
    
    if df.empty:
        return []
    
    # Get unique department names, sorted alphabetically
    return sorted(df['Department'].unique().tolist())

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
    
    # If department is specified, filter the data
    if department and department != "All Departments":
        # Filter by department name
        return df[df['Department'] == department]
    
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