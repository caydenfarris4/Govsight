"""
Transaction Data Connection Module

This module handles loading and processing transaction data from the database.
It provides functions for account mask parsing and transaction analysis.
"""

import pandas as pd
import json
import os
import sqlite3
from typing import Dict, Any, Optional

def load_settings():
    """
    Load settings from ConfigService (database-backed).
    Falls back to system_settings.json if ConfigService unavailable.
    
    Returns:
        Dict: Settings as a dictionary
    """
    try:
        from modules.services.config_service import get_config_service
        svc = get_config_service()
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

def parse_account(account_code, mask):
    """
    Parse account code according to mask pattern
    
    Args:
        account_code (str): Account code to parse
        mask (str): Mask pattern to apply (e.g., "FF-DD-CC-AAAA")
        
    Returns:
        dict: Dictionary of parsed segments (Fund, Dept, Object, Category)
    """
    segments = {
        "Fund": "",
        "Dept": "",
        "Object": "",
        "Category": ""
    }
    
    # Check if account code exists
    if not account_code or pd.isna(account_code):
        return segments
            
    # Convert to string if not already
    account_code = str(account_code).strip()
    
    # Initialize pointers to track position in account code and mask
    code_pos = 0
    mask_pos = 0
    current_segment = ""
    current_segment_type = ""
    
    # Parse account code according to mask
    try:
        while mask_pos < len(mask) and code_pos < len(account_code):
            if mask[mask_pos] == "-":
                # If we reach a separator in the mask, save the current segment
                if current_segment_type:
                    if current_segment_type == "F":
                        segments["Fund"] = current_segment
                    elif current_segment_type == "D":
                        segments["Dept"] = current_segment
                    elif current_segment_type == "C":
                        segments["Category"] = current_segment
                    elif current_segment_type == "O" or current_segment_type == "A":
                        segments["Object"] = current_segment
                            
                # Reset for next segment
                current_segment = ""
                current_segment_type = ""
                
                # Skip separator in account code if it exists
                if code_pos < len(account_code) and account_code[code_pos] == "-":
                    code_pos += 1
                    
                mask_pos += 1
            else:
                # Get the segment type from the mask
                current_segment_type = mask[mask_pos]
                
                # Collect segments of the same type
                while (mask_pos < len(mask) and 
                      mask[mask_pos] == current_segment_type and 
                      code_pos < len(account_code)):
                    # Skip separators in account code
                    if code_pos < len(account_code) and account_code[code_pos] == "-":
                        code_pos += 1
                        continue
                        
                    if code_pos < len(account_code):
                        current_segment += account_code[code_pos]
                        code_pos += 1
                    mask_pos += 1
        
        # Save the last segment
        if current_segment_type:
            if current_segment_type == "F":
                segments["Fund"] = current_segment
            elif current_segment_type == "D":
                segments["Dept"] = current_segment
            elif current_segment_type == "C":
                segments["Category"] = current_segment
            elif current_segment_type == "O" or current_segment_type == "A":
                segments["Object"] = current_segment
    except Exception as e:
        print(f"Error parsing account: {e}")
        # If there's an error parsing, reset segments
        segments = {
            "Fund": "",
            "Dept": "",
            "Object": "",
            "Category": ""
        }
        
    return segments

def load_transaction_data(account_type: str = "Expense") -> pd.DataFrame:
    """
    Load transaction data from the database with account mask parsing
    
    Args:
        account_type (str): The type of account mask to apply (Expense, Revenue, Balance)
        
    Returns:
        DataFrame: Pandas DataFrame with transaction data and parsed account segments
    """
    try:
        # Connect to the transaction database
        conn = get_connection('govdata.db')
        
        # Query to get all transactions
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
            SequenceNumber
        FROM tblTransaction
        """
        
        # Load data into DataFrame
        df = pd.read_sql_query(query, conn)
        
        # Close connection
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        # Get mask settings from system_settings.json
        settings = load_settings()
        expense_mask = settings.get("ExpenseAccountMask", "FF-DD-CC-AAAA")
        revenue_mask = settings.get("RevenueAccountMask", "F-D-OOO")
        balance_mask = settings.get("BalanceSheetAccountMask", "FF-DD-OOOO")
        
        # Choose the appropriate mask based on account_type
        if account_type == "Expense":
            mask = expense_mask
        elif account_type == "Revenue":
            mask = revenue_mask
        else:  # Balance Sheet
            mask = balance_mask
        
        # Apply the parsing function to each account code
        if not df.empty:
            account_segments = df['GLAccount'].apply(lambda x: pd.Series(parse_account(x, mask)))
            
            # Combine with original DataFrame
            result_df = pd.concat([df, account_segments], axis=1)
            return result_df
        
        return df
        
    except Exception as e:
        print(f"Error loading transaction data: {e}")
        return pd.DataFrame()