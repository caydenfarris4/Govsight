import streamlit as st
import pandas as pd
import sqlite3
import json
import os

# Load config
try:
    with open("config.json") as f:
        CONFIG = json.load(f)
except Exception as e:
    st.error(f"Error loading configuration: {e}")
    CONFIG = {}

def get_connection(db_name='budget.db'):
    """Create a connection to the SQLite database"""
    import os
    
    # Check if database file exists
    if not os.path.exists(db_name):
        st.error(f"Database file '{db_name}' not found. Please verify the database exists.")
        return None
    
    try:
        conn = sqlite3.connect(db_name, timeout=30.0)
        # Test the connection
        conn.execute("SELECT 1")
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected database error: {e}")
        return None

def execute_query(query, params=(), fetchall=True, db_name='budget.db'):
    """Execute a query and return results"""
    conn = get_connection(db_name)
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
            if fetchall:
                return cursor.fetchall()
            else:
                return cursor.fetchone()
        else:
            conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        st.error(f"Query execution error: {e}")
        return None
    finally:
        conn.close()

def run_dashboard_query(query, org_filter=None):
    """Execute a query against the dashboard database"""
    try:
        # Check for unsafe SQL operations
        banned = ["drop", "delete", "update", "insert", "alter"]
        if any(word in query.lower() for word in banned):
            return " Unsafe query blocked."
            
        # Get the appropriate database path for this organization
        dashboard_db = get_db_path_for_org(org_filter)
        
        conn = get_connection(dashboard_db)
        if not conn:
            return f"Database connection error for {dashboard_db}"
        
        cursor = conn.cursor()
        
        # Add organization filter if provided
        if org_filter:
            # If the query has a WHERE clause, add an AND condition
            if "WHERE" in query.upper():
                query = query.replace("WHERE", f"WHERE Organization = '{org_filter}' AND")
            # If no WHERE clause, add one
            elif "GROUP BY" in query.upper():
                query = query.replace("GROUP BY", f"WHERE Organization = '{org_filter}' GROUP BY")
            else:
                # Add WHERE before any ORDER BY, LIMIT, etc.
                for clause in ["ORDER BY", "LIMIT", "HAVING"]:
                    if clause in query.upper():
                        parts = query.split(clause, 1)
                        query = f"{parts[0]} WHERE Organization = '{org_filter}' {clause}{parts[1]}"
                        break
                else:
                    query += f" WHERE Organization = '{org_filter}'"
        
        # Print query for debugging
        print(f"Executing query on {dashboard_db}: {query}")
        
        # Execute the query
        cursor.execute(query)
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=columns)
        conn.close()
        return df
    except Exception as e:
        error_msg = f"Error executing query on {dashboard_db}: {str(e)}"
        print(error_msg)
        return error_msg

def get_departments(org=None):
    """
    Get all departments from the database, with improved organization-specific handling
    
    This function first tries to get department data from the organization-specific dashboard database.
    If that fails, it falls back to the legacy departments table.
    
    Args:
        org (str, optional): Organization identifier for org-specific data. Defaults to None.
        
    Returns:
        dict: Dictionary of departments with budget and underspent data
    """
    departments = {}
    
    # First try to get department data from the dashboard database if org is specified
    if org:
        try:
            # Get the correct database path for this organization
            db_path = get_db_path_for_org(org)
            
            # Direct query to the organization's specific database
            conn = get_connection(db_path)
            if conn:
                # Use ROUND function in SQL to ensure all values are properly rounded to 2 decimal places
                query = f"""
                SELECT 
                    Department, 
                    ROUND(SUM(Budget), 2) as Budget, 
                    ROUND(SUM(Budget - Actual), 2) as Underspent 
                FROM DepartmentPerformance 
                WHERE Organization = '{org}' AND FiscalYear = 'FY 2024' 
                GROUP BY Department
                """
                dept_data = pd.read_sql_query(query, conn)
                conn.close()
                
                if not dept_data.empty:
                    # Convert DataFrame to the expected format
                    for _, row in dept_data.iterrows():
                        # Round values to ensure exactly 2 decimal places
                        budget_value = round(float(row['Budget']), 2)
                        underspent_value = round(float(row['Underspent']), 2) if row['Underspent'] > 0 else 0.00
                        
                        departments[row['Department']] = {
                            "id": 0,  # Use placeholder ID since we don't have real IDs in the dashboard data
                            "budget": budget_value,
                            "underspent": underspent_value
                        }
                    return departments
        except Exception as e:
            print(f"Could not load department data from dashboard DB for {org}: {str(e)}")
    
    # Fall back to legacy departments table
    query = "SELECT id, name, ROUND(total_budget, 2) as total_budget, ROUND(underspent, 2) as underspent FROM departments"
    departments_data = execute_query(query)
    
    if not departments_data:
        return {}
    
    # Convert to dictionary with department name as key
    for dept in departments_data:
        departments[dept[1]] = {
            "id": dept[0],
            "budget": round(float(dept[2]), 2),
            "underspent": round(float(dept[3]), 2)
        }
    
    return departments

def get_db_path_for_org(org):
    """
    Get the appropriate database path for an organization
    
    Args:
        org (str): Organization identifier
        
    Returns:
        str: Database path for the organization
    """
    # For cityA, use the caselle database which has the actual data
    if org and org.lower() == "citya":
        return "databases/core/caselle_gl0_mock.db"
    
    # Check if there's a custom database path for this organization
    if org and org in CONFIG and 'dashboard_db' in CONFIG[org]:
        db_path = CONFIG[org]['dashboard_db']
        # Verify the database exists and has data
        import os
        if os.path.exists(db_path):
            return db_path
    
    # Default database path - but check if caselle exists as fallback
    if os.path.exists("databases/core/caselle_gl0_mock.db"):
        return "databases/core/caselle_gl0_mock.db"
    
    return "org_dashboard_data.db"

def format_currency(value):
    """
    Format a numeric value as currency with exactly two decimal places
    
    Args:
        value (float or int): The numeric value to format
        
    Returns:
        str: Formatted string with commas and exactly two decimal places
    """
    # Ensure we have a numeric value
    try:
        # Convert to float and round to 2 decimal places
        num_value = round(float(value), 2)
        # Format with commas and exactly two decimal places
        return f"${num_value:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def format_percentage(value):
    """
    Format a numeric value as percentage with exactly two decimal places
    
    Args:
        value (float or int): The numeric value to format
        
    Returns:
        str: Formatted string with exactly two decimal places and % symbol
    """
    try:
        # Round to 2 decimal places for consistent display
        num_value = round(float(value), 2)
        return f"{num_value:.2f}%"
    except (ValueError, TypeError):
        return "0.00%"

def load_org_data(org_filter=None):
    """
    Load department performance data for an organization
    
    Args:
        org_filter (str, optional): Organization identifier. Defaults to None.
        
    Returns:
        DataFrame: Pandas DataFrame with department performance data
    """
    try:
        # Get the appropriate database path
        db_path = get_db_path_for_org(org_filter) if org_filter else "org_dashboard_data.db"
        
        # Connect to the database
        conn = get_connection(db_path)
        if not conn:
            return pd.DataFrame()
        
        # Build the query
        query = "SELECT * FROM DepartmentPerformance"
        if org_filter:
            query += f" WHERE Organization = '{org_filter}'"
            
        # Execute the query
        df = pd.read_sql_query(query, conn)
        
        # Round all numeric columns to two decimal places
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            df[col] = df[col].round(2)
            
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()
def validate_numeric_input(value):
    """Validate numeric input and convert to float/int"""
    if isinstance(value, (int, float)):
        return value
    
    if isinstance(value, str):
        try:
            # Try int first
            if '.' not in value:
                return int(value)
            else:
                return float(value)
        except ValueError:
            raise ValueError(f"'{value}' is not a valid number")
    
    raise ValueError(f"Cannot convert {type(value)} to number")
