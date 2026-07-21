"""
Database Connection and Security Module

This module handles all database connections, security features, and authentication.
It provides a consistent interface for connecting to the database and executing queries.
"""

import os
import json
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union, Tuple
from urllib.parse import quote_plus
from sqlalchemy import create_engine

# Try to import database connection libraries
try:
    import psycopg2  # PostgreSQL
except ImportError:
    pass

try:
    import mysql.connector  # MySQL
except ImportError:
    pass

# Default database paths
DEFAULT_DB_PATH = 'databases/core/caselle_gl0_mock.db'  # Transaction database with GL accounts
DASHBOARD_DB_PATH = 'org_dashboard_data.db'  # Dashboard metrics
CONFIG_DB_PATH = 'cityA_with_gl_accounts.db'  # GL account configurations

# The currently selected database (can be changed in admin panel)
CURRENT_DB_PATH = DEFAULT_DB_PATH

def get_selected_database():
    """
    Get the currently selected database from session state or settings file
    
    Returns:
        str: Path to the currently selected database
    """
    # First check session state (set by admin panel)
    if 'db_path' in st.session_state:
        return st.session_state['db_path']
    
    # If not in session state, try to get from settings file
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                if "current_database" in settings:
                    return settings["current_database"]
                elif "SQLite_File" in settings and settings.get("DB_Type", "") == "SQLite":
                    return settings["SQLite_File"]
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    # Default fallback
    return DEFAULT_DB_PATH

# Settings file for database configuration
SETTINGS_FILE = "system_settings.json"

# Account code mask parsing functions
def get_mask_from_settings(account_type: str) -> str:
    """
    Returns the appropriate mask from system settings based on account type
    
    Args:
        account_type (str): Type of account mask to retrieve (Expense, Revenue, Balance)
        
    Returns:
        str: Mask string in format like 'FF-DD-OOOO'
    """
    if not os.path.exists(SETTINGS_FILE):
        # Default masks if settings file doesn't exist
        defaults = {
            "Expense": "FF-DD-CC-AAAA",
            "Revenue": "F-D-OOO",
            "Balance": "FF-DD-OOOO"
        }
        return defaults.get(account_type, "")
        
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
    return settings.get(f"Mask_{account_type}", "")

def parse_account(account_str: str, mask: str) -> dict:
    """
    Parses an account string based on a given mask like 'FF-DD-OOOO'
    
    Args:
        account_str (str): The GL account string to parse
        mask (str): The mask format to apply (e.g., 'FF-DD-OOOO')
        
    Returns:
        dict: Dictionary with parsed segments (Fund, Dept, Object, etc.)
    """
    # Handle empty or invalid inputs
    if not account_str or not mask:
        return {}
        
    # Clean the mask for processing
    clean_mask = mask.replace("-", "")
    segment_map = {}
    mask_parts = mask.split("-")
    account_parts = account_str.split("-")
    
    # Map account segments based on mask parts
    index = 0
    for i, part in enumerate(mask_parts):
        # Get label based on first character of mask segment
        label = {
            'F': 'Fund',
            'D': 'Dept',
            'O': 'Object',
            'C': 'Category',
            'A': 'Account',
            'B': 'SubFund'
        }.get(part[0], f"Part{index}")
        
        # If we have corresponding account part, set the value
        if i < len(account_parts):
            segment_map[label] = account_parts[i]
        else:
            segment_map[label] = ""
            
        index += 1
    
    return segment_map

# Load configuration
def load_config() -> Dict[str, Any]:
    """Load the configuration from config.json"""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return minimal default config if file doesn't exist or is invalid
        return {
            "cityA": {
                "org_name": "City A",
                "dashboard_db": DASHBOARD_DB_PATH,
                "login_password": "cityA2024",
                "theme_color": "#0066cc"
            }
        }

# Save configuration
def save_config(config: Dict[str, Any]) -> None:
    """Save the configuration to config.json"""
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

# Load settings from system_settings.json
def load_settings():
    """
    Load settings from system_settings.json
    
    Returns:
        pd.Series: Settings as a pandas Series
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            settings = pd.read_json(SETTINGS_FILE, typ="series")
            return settings
        except Exception as e:
            st.error(f"Error loading settings: {e}")
    
    # Return default settings
    return pd.Series({
        "OrganizationName": "City A",
        "DefaultPassword": "changeme123",
        "OpenAI_Key": "",
        "AutoBackupEnabled": False,
        "DB_Type": "SQLite",
        "SQLite_File": DEFAULT_DB_PATH,
        "DB_Server": "",
        "DB_Port": "",
        "DB_Name": "",
        "DB_User": "",
        "DB_Password": ""
    })

# Connect to the database based on settings
def connect_db():
    """
    Connect to the database based on settings
    
    Returns:
        Connection: Database connection
    """
    settings = load_settings()
    db_type = settings.get("DB_Type", "SQLite")

    if db_type == "SQLite":
        db_file = settings.get("SQLite_File", DEFAULT_DB_PATH)
        
        # Check for extracted files first
        is_extracted_file = hasattr(st.session_state, 'extracted_db_files') and db_file in st.session_state.extracted_db_files
        
        # If either it's an extracted file or it exists on disk
        if db_file and (is_extracted_file or os.path.exists(db_file)):
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            return conn
        else:
            st.error(f"SQLite database file {db_file} not found.")
            return None

    elif db_type == "PostgreSQL":
        try:
            conn = psycopg2.connect(
                host=settings.get("DB_Server", ""),
                port=settings.get("DB_Port", ""),
                dbname=settings.get("DB_Name", ""),
                user=settings.get("DB_User", ""),
                password=settings.get("DB_Password", "")
            )
            return conn
        except Exception as e:
            st.error(f"PostgreSQL connection failed: {e}")
            return None

    elif db_type == "MySQL":
        try:
            conn = mysql.connector.connect(
                host=settings.get("DB_Server", ""),
                port=int(settings.get("DB_Port", 3306)),
                database=settings.get("DB_Name", ""),
                user=settings.get("DB_User", ""),
                password=settings.get("DB_Password", "")
            )
            return conn
        except Exception as e:
            st.error(f"MySQL connection failed: {e}")
            return None

    else:
        st.error(f"Unknown database type: {db_type}")
        return None

# Load data using dynamic connection
def load_data():
    """
    Load data from dynamic database connection
    
    Returns:
        DataFrame: Pandas DataFrame with department performance data
    """
    conn = connect_db()
    if conn is None:
        return pd.DataFrame()

    try:
        query = "SELECT * FROM DepartmentPerformance"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

# Get the appropriate database path
def get_db_path_for_org(org: str = None) -> str:
    """
    Get the appropriate database path for an organization
    
    Args:
        org (str, optional): Organization identifier
        
    Returns:
        str: Database path for the organization
    """
    # First check if we have a database selected in admin panel via session state
    selected_db = get_selected_database()
    if selected_db:
        return selected_db
    
    # If no selected database, fall back to standard logic
    # Check if we should use a different database system
    settings = load_settings()
    if settings.get("DB_Type", "SQLite") != "SQLite":
        # For non-SQLite databases, we'll use the connect_db function
        # But for compatibility, we still return a default path
        return DEFAULT_DB_PATH
    
    # Otherwise continue with normal SQLite path logic
    if not org:
        return settings.get("SQLite_File", DEFAULT_DB_PATH)
    
    config = load_config()
    if org in config and "dashboard_db" in config[org]:
        return config[org]["dashboard_db"]
    
    # Fallback to standard format if not in config, but ensure we prioritize unified database for cityA
    if org.lower() == "citya":
        return DASHBOARD_DB_PATH
    
    return f"{org}_dashboard_data.db"

# Create a database connection
def get_connection(db_path: str = None):
    """
    Create a connection to the SQLite database or other database types
    
    Args:
        db_path (str, optional): Path to the database. If None, uses the default path.
        
    Returns:
        Connection: Database connection
    """
    # Check if db_path is a configuration string for SQL Server
    if db_path and not db_path.endswith(".db"):
        quoted = quote_plus(db_path)
        try:
            return create_engine(f"mssql+pyodbc:///?odbc_connect={quoted}").connect()
        except Exception as e:
            st.error(f"SQL Server connection error: {e}")
            return None
    
    # Check if we should use a different database system
    settings = load_settings()
    if settings.get("DB_Type", "SQLite") != "SQLite":
        return connect_db()
    
    # Otherwise use SQLite connection
    if db_path is None:
        db_path = settings.get("SQLite_File", DEFAULT_DB_PATH)
    
    try:
        # Check if there are any extracted database files that match the requested path
        if hasattr(st.session_state, 'extracted_db_files') and db_path in st.session_state.extracted_db_files:
            # Use the temporary path directly
            conn = sqlite3.connect(db_path)
        else:
            # Regular file path handling
            conn = sqlite3.connect(db_path)
            
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        return None

# Execute a database query
def execute_query(query: str, params: tuple = (), fetchall: bool = True, db_path: str = None):
    """
    Execute a query and return results
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Query parameters
        fetchall (bool, optional): Whether to fetch all results. Defaults to True.
        db_path (str, optional): Path to the database. If None, uses the default.
        
    Returns:
        list or dict: Query results or None if error
    """
    conn = get_connection(db_path)
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetchall:
            results = cursor.fetchall()
        else:
            results = cursor.fetchone()
            
        # Convert results to list of dictionaries for better handling
        if results and fetchall:
            return [dict(row) for row in results]
        elif results:
            return dict(results)
        else:
            return []
    except sqlite3.Error as e:
        st.error(f"Query execution error: {e}")
        return None
    finally:
        conn.close()

# Run a query against the dashboard database
def run_dashboard_query(query, params=(), fetchall=True, org=None):
    """
    Execute a query against the dashboard database
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Query parameters
        fetchall (bool, optional): Whether to fetch all results
        org (str, optional): Organization identifier
        
    Returns:
        list or dict: Query results
    """
    db_path = get_db_path_for_org(org)
    return execute_query(query, params, fetchall, db_path)

# Load data for an organization
def load_org_data(org=None, table: str = "DepartmentPerformance"):
    """
    Load department performance data for an organization
    
    Args:
        org (str, optional): Organization identifier. Defaults to None.
        table (str, optional): Table to load data from. Defaults to "DepartmentPerformance".
        
    Returns:
        DataFrame: Pandas DataFrame with department performance data
    """
    # Always use the transaction database for all operations
    transaction_db_path = "databases/core/caselle_gl0_mock.db"
    
    try:
        # Connect to the database
        conn = sqlite3.connect(transaction_db_path)
        
        # Check if DepartmentPerformance table exists
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            st.info(f"Creating {table} table in the database")
            # Create the DepartmentPerformance table based on transaction data
            # First get the transaction data to derive departments and funds
            try:
                # Create the DepartmentPerformance table
                cursor.execute(f"""
                CREATE TABLE {table} (
                    Department TEXT,
                    Fund TEXT,
                    FiscalYear TEXT,
                    AccountCode TEXT,
                    AccountName TEXT,
                    Budget REAL,
                    Actual REAL,
                    PercentUsed REAL,
                    Organization TEXT
                )
                """)
                
                # Extract department codes from transactions
                cursor.execute("""
                SELECT DISTINCT 
                    SUBSTR(GLAccount, INSTR(GLAccount, '-') + 1, 2) as dept_code,
                    Type as AccountType,
                    GLAccount
                FROM tblTransaction
                """)
                
                dept_codes = cursor.fetchall()
                
                # Define department mapping
                dept_mapping = {
                    '01': 'Administration',
                    '02': 'Finance',  
                    '03': 'Police',
                    '04': 'Fire'
                }
                
                # Define fund types
                fund_types = ['General Fund', 'Capital Projects', 'Enterprise Fund', 'Special Revenue']
                
                # Create sample data for each department
                for dept_row in dept_codes:
                    dept_code = dept_row[0]
                    account_type = dept_row[1]
                    account_code = dept_row[2]
                    
                    # Skip if department code not in our mapping
                    if dept_code not in dept_mapping:
                        continue
                        
                    dept_name = dept_mapping[dept_code]
                    
                    # Get sum of transactions for this department
                    cursor.execute("""
                    SELECT SUM(ABS(Amount)) 
                    FROM tblTransaction 
                    WHERE SUBSTR(GLAccount, INSTR(GLAccount, '-') + 1, 2) = ?
                    """, (dept_code,))
                    
                    dept_total = cursor.fetchone()[0] or 10000  # Default to 10000 if no data
                    
                    # Create entries for each fund and fiscal year
                    for fund in fund_types:
                        # Scale the budget based on fund type
                        fund_factor = 1.0
                        if fund == 'Capital Projects':
                            fund_factor = 0.8
                        elif fund == 'Enterprise Fund':
                            fund_factor = 0.6
                        elif fund == 'Special Revenue':
                            fund_factor = 0.4
                        
                        # Create records for current and past fiscal years
                        for year_offset in range(3):  # 0 = current year, 1 = last year, 2 = two years ago
                            fiscal_year = f"FY{2023 - year_offset}"
                            
                            # Calculate budget and actual values based on dept total and offset
                            base_budget = dept_total * fund_factor * (0.9 ** year_offset)
                            base_actual = base_budget * (0.75 + year_offset * 0.05)  # Higher completion rate in past years
                            
                            # Create different account categories
                            accounts = [
                                (f"{dept_code}-01", "Personnel", 0.6),  # 60% for personnel
                                (f"{dept_code}-02", "Operations", 0.3),  # 30% for operations
                                (f"{dept_code}-03", "Capital", 0.1)      # 10% for capital
                            ]
                            
                            for acct_code, acct_name, pct in accounts:
                                budget = base_budget * pct
                                actual = base_actual * pct
                                percent_used = (actual / budget) * 100 if budget > 0 else 0
                                
                                # Insert into DepartmentPerformance
                                cursor.execute(f"""
                                INSERT INTO {table} 
                                (Department, Fund, FiscalYear, AccountCode, AccountName, Budget, Actual, PercentUsed, Organization)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    dept_name, fund, fiscal_year, acct_code, acct_name, 
                                    budget, actual, percent_used, "City A"
                                ))
                
                # Commit the changes
                conn.commit()
                st.success(f"Successfully created {table} with data derived from transaction records")
                
            except Exception as e:
                st.error(f"Error creating {table}: {e}")
                return pd.DataFrame()
        
        # Now get column names to determine database schema
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Handle different tables (GL vs DepartmentPerformance)
        if table != "DepartmentPerformance":
            # For GL tables or other tables
            query = f"SELECT * FROM {table}"
            df = pd.read_sql_query(query, conn)
        else:
            # Check if we're using the new database schema
            is_new_schema = 'DepartmentCode' in columns and 'DepartmentName' in columns
            
            if is_new_schema:
                # New database schema with account segments
                query = """
                    SELECT 
                        DepartmentName as Department,
                        FundName as Fund,
                        FiscalYear,
                        Budget,
                        Actual,
                        Month,
                        'City A' as Organization,
                        AccountCode,
                        AccountName,
                        AccountType,
                        DepartmentCode,
                        FundCode,
                        Mask
                    FROM DepartmentPerformance
                """
                df = pd.read_sql_query(query, conn)
            else:
                # Check if the Organization column exists in old schema
                has_org_column = 'Organization' in columns
                
                if has_org_column:
                    query = "SELECT * FROM DepartmentPerformance"
                    df = pd.read_sql_query(query, conn)
                else:
                    # For databases without Organization column (like the original cityA)
                    query = "SELECT *, 'City A' as Organization FROM DepartmentPerformance"
                    df = pd.read_sql_query(query, conn)
        
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading data from {transaction_db_path}: {e}")
        # Return empty DataFrame with expected columns reflecting new schema
        if table == "DepartmentPerformance":
            return pd.DataFrame(columns=[
                'Department', 'Fund', 'FiscalYear', 'Budget', 'Actual', 'Month', 
                'Organization', 'AccountCode', 'AccountName', 'AccountType',
                'DepartmentCode', 'FundCode', 'Mask'
            ])
        else:
            return pd.DataFrame()

# Get departments from the database
def get_departments(org=None):
    """
    Get all departments from the transaction database (databases/core/caselle_gl0_mock.db)
    
    This function extracts department information directly from the transaction
    database, ensuring consistent departments across the application.
    
    Args:
        org (str, optional): Organization identifier - not used but kept for API compatibility.
        
    Returns:
        dict: Dictionary of departments with budget and underspent data
    """
    # Always use the transaction database (databases/core/caselle_gl0_mock.db) to get departments
    transaction_db_path = "databases/core/caselle_gl0_mock.db"
    
    # Department mapping from the transaction database
    dept_mapping = {
        '01': 'Administration',
        '02': 'Finance',  
        '03': 'Police',
        '04': 'Fire'
    }
    
    try:
        # Connect to the transaction database
        conn = get_connection(transaction_db_path)
        if not conn:
            raise Exception("Could not connect to transaction database")
        
        # Get transactions to extract department info
        cursor = conn.cursor()
        
        # First attempt to get transaction counts by department
        try:
            # Construct query to count transactions and sum amounts by department code
            query = """
            WITH dept_transactions AS (
                SELECT 
                    SUBSTR(GLAccount, INSTR(GLAccount, '-') + 1, 2) as dept_code,
                    COUNT(*) as transaction_count,
                    SUM(Amount) as total_amount
                FROM tblTransaction
                GROUP BY SUBSTR(GLAccount, INSTR(GLAccount, '-') + 1, 2)
            )
            SELECT dept_code, transaction_count, total_amount FROM dept_transactions
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Process results
            departments = {}
            for row in results:
                dept_code = row[0]
                if dept_code in dept_mapping:
                    dept_name = dept_mapping[dept_code]
                    departments[dept_name] = {
                        "budget": abs(row[2]) * 1.1,  # Use absolute transaction amount + 10% as "budget"
                        "underspent": abs(row[2]) * 0.1  # Set underspent to 10% of "budget"
                    }
            
            # If we found departments, return them
            if departments:
                conn.close()
                return departments
                
        except Exception as e:
            print(f"Error analyzing transactions by department: {e}")
            # Fall through to use the basic department list
            
        # Fallback method: just return the department list with estimated budgets
        departments = {}
        for code, name in dept_mapping.items():
            # Assign reasonable budget values
            if name == 'Administration':
                budget = 1000000
                underspent = 50000
            elif name == 'Finance':
                budget = 750000
                underspent = 25000
            elif name == 'Police':
                budget = 2000000
                underspent = 100000
            elif name == 'Fire':
                budget = 1500000
                underspent = 75000
            else:
                budget = 500000
                underspent = 25000
                
            departments[name] = {
                "budget": budget,
                "underspent": underspent
            }
            
        conn.close()
        return departments
        
    except Exception as e:
        print(f"Could not get departments from transaction database: {e}")
        
        # Return the standard department list as a last resort
        sample_departments = {
            "Administration": {"budget": 1000000, "underspent": 50000},
            "Finance": {"budget": 750000, "underspent": 25000},
            "Police": {"budget": 2000000, "underspent": 100000},
            "Fire": {"budget": 1500000, "underspent": 75000}
        }
        
        st.warning(" No departments found in the database. Using standard department list.")
        return sample_departments

# Get projects from the database
def get_projects():
    """
    Get all projects from the database. If the projects table doesn't exist in the transaction database,
    it will be created with sample data based on the departments.
    """
    # Always use the transaction database for all operations
    transaction_db_path = "databases/core/caselle_gl0_mock.db"
    conn = get_connection(transaction_db_path)
    
    if not conn:
        st.error("Failed to connect to the transaction database.")
        return []
    
    try:
        cursor = conn.cursor()
        
        # Check if projects table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            # Create projects table and populate with default data
            cursor.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                total_cost REAL NOT NULL
            )
            """)
            
            # Insert sample projects matched to the departments in the transaction database
            sample_projects = [
                (1, "Administrative Services Review", "Comprehensive review of administrative services and processes", 250000.00),
                (2, "City Hall Renovation", "Renovation of city hall facilities including public areas", 750000.00),
                (3, "Budget Management System", "Implementation of advanced budget tracking and reporting system", 180000.00),
                (4, "Revenue Optimization", "Analysis and implementation of revenue enhancement strategies", 425000.00),
                (5, "Police Equipment Upgrade", "Modernization of police department equipment and technology", 150000.00),
                (6, "Community Safety Program", "Comprehensive community safety initiative including outreach", 100000.00),
                (7, "Fire Equipment Modernization", "Upgrades to firefighting equipment and emergency response tools", 200000.00),
                (8, "Emergency Response Training", "Advanced training program for emergency response situations", 65000.00)
            ]
            
            cursor.executemany(
                "INSERT INTO projects (id, name, description, total_cost) VALUES (?, ?, ?, ?)",
                sample_projects
            )
            conn.commit()
            print("Created projects table with sample data in transaction database")
        
        # Fetch the projects
        cursor.execute("SELECT id, name, description, total_cost FROM projects")
        
        # Build list of projects
        projects = []
        for row in cursor.fetchall():
            projects.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "total_cost": row[3]
            })
        
        return projects
    except sqlite3.Error as e:
        st.error(f"Error managing projects: {e}")
        
        # Return sample data as a fallback if there's an error
        sample_projects = [
            {"id": 1, "name": "Administrative Services Review", "description": "Comprehensive review of administrative services", "total_cost": 250000.00},
            {"id": 2, "name": "City Hall Renovation", "description": "Renovation of city hall facilities", "total_cost": 750000.00},
            {"id": 3, "name": "Budget Management System", "description": "Implementation of budget tracking system", "total_cost": 180000.00},
            {"id": 4, "name": "Revenue Optimization", "description": "Analysis of revenue enhancement strategies", "total_cost": 425000.00}
        ]
        return sample_projects
    finally:
        conn.close()

# Save a funding scenario to the database
def save_scenario(scenario_data, department_allocations):
    """Save a funding scenario to the database"""
    # Always use the transaction database for all operations
    transaction_db_path = "databases/core/caselle_gl0_mock.db"
    conn = get_connection(transaction_db_path)
    
    if not conn:
        st.error("Failed to connect to the transaction database.")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if the scenarios table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'")
        table_exists = cursor.fetchone()
        
        # Create tables if they don't exist
        if not table_exists:
            # Create scenarios table
            cursor.execute("""
            CREATE TABLE scenarios (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                project_id INTEGER NOT NULL,
                tax_revenue REAL,
                grant_funding REAL,
                private_investment REAL,
                bonds_needed REAL,
                total_cost REAL,
                creation_date TEXT
            )
            """)
            
            # Create departments table if it doesn't exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='departments'")
            if not cursor.fetchone():
                cursor.execute("""
                CREATE TABLE departments (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    budget REAL,
                    underspent REAL
                )
                """)
                
                # Insert departments based on our mapping
                dept_mapping = {
                    '01': 'Administration',
                    '02': 'Finance',  
                    '03': 'Police',
                    '04': 'Fire'
                }
                
                for dept_code, dept_name in dept_mapping.items():
                    # Assign reasonable budget values
                    if dept_name == 'Administration':
                        budget = 1000000
                        underspent = 50000
                    elif dept_name == 'Finance':
                        budget = 750000
                        underspent = 25000
                    elif dept_name == 'Police':
                        budget = 2000000
                        underspent = 100000
                    elif dept_name == 'Fire':
                        budget = 1500000
                        underspent = 75000
                    else:
                        budget = 500000
                        underspent = 25000
                    
                    cursor.execute(
                        "INSERT INTO departments (name, budget, underspent) VALUES (?, ?, ?)",
                        (dept_name, budget, underspent)
                    )
            
            # Create scenario_department_allocations table
            cursor.execute("""
            CREATE TABLE scenario_department_allocations (
                id INTEGER PRIMARY KEY,
                scenario_id INTEGER,
                department_id INTEGER,
                allocation_amount REAL,
                FOREIGN KEY (scenario_id) REFERENCES scenarios(id),
                FOREIGN KEY (department_id) REFERENCES departments(id)
            )
            """)
        
        # Insert scenario
        cursor.execute(
            "INSERT INTO scenarios (name, project_id, tax_revenue, grant_funding, "
            "private_investment, bonds_needed, total_cost, creation_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                scenario_data["name"],
                scenario_data["project_id"],
                scenario_data["tax_revenue"],
                scenario_data["grant"],
                scenario_data["private_investment"],
                scenario_data["bonds_needed"],
                scenario_data["total_amount"]
            )
        )
        
        # Get the inserted scenario ID
        scenario_id = cursor.lastrowid
        
        # Insert department allocations
        for dept_name, amount in department_allocations.items():
            # Need to get the department ID first
            dept_cursor = conn.cursor()
            dept_cursor.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
            dept_row = dept_cursor.fetchone()
            
            if dept_row:
                dept_id = dept_row[0]
                cursor.execute(
                    "INSERT INTO scenario_department_allocations (scenario_id, department_id, allocation_amount) "
                    "VALUES (?, ?, ?)",
                    (scenario_id, dept_id, amount)
                )
            else:
                # If department not found, create a log but continue processing
                st.warning(f"Department '{dept_name}' not found in database, allocation not saved.")
        
        conn.commit()
        
        # Auto-add this scenario to the comparison list in session state
        if "st" in globals() and hasattr(st, "session_state"):
            # Initialize the session state's saved_scenarios if it doesn't exist
            if not hasattr(st.session_state, "saved_scenarios"):
                st.session_state.saved_scenarios = []
                
            # Add this scenario to the comparison list
            st.session_state.saved_scenarios.append({
                "id": scenario_id,
                "name": scenario_data["name"],
                "total_amount": scenario_data["total_amount"],
                "project_id": scenario_data["project_id"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if 'datetime' in globals() else "Now"
            })
        
        return True
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"Error saving scenario: {e}")
        return False
    finally:
        conn.close()

# Get recent scenarios from the database
def get_scenarios(limit=10):
    """Get the most recent scenarios from the database"""
    # Always use the transaction database for all operations
    transaction_db_path = "databases/core/caselle_gl0_mock.db"
    conn = get_connection(transaction_db_path)
    
    if not conn:
        st.error("Failed to connect to the transaction database.")
        return []
    
    try:
        cursor = conn.cursor()
        
        # Check if creation_date column exists in scenarios table
        cursor.execute("PRAGMA table_info(scenarios)")
        columns = [column[1] for column in cursor.fetchall()]
        has_creation_date = 'creation_date' in columns
        
        if has_creation_date:
            # Use creation_date column if it exists
            cursor.execute(
                "SELECT s.id, s.name, '' as description, s.total_cost as total_amount, s.creation_date as created_at, "
                "COUNT(sd.department_id) as dept_count "
                "FROM scenarios s "
                "LEFT JOIN scenario_department_allocations sd ON s.id = sd.scenario_id "
                "GROUP BY s.id "
                "ORDER BY s.creation_date DESC "
                "LIMIT ?",
                (limit,)
            )
        else:
            # Fallback without creation_date column
            cursor.execute(
                "SELECT s.id, s.name, '' as description, s.total_cost as total_amount, 'N/A' as created_at, "
                "COUNT(sd.department_id) as dept_count "
                "FROM scenarios s "
                "LEFT JOIN scenario_department_allocations sd ON s.id = sd.scenario_id "
                "GROUP BY s.id "
                "ORDER BY s.id DESC "
                "LIMIT ?",
                (limit,)
            )
        
        scenarios = []
        for row in cursor.fetchall():
            scenarios.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "total_amount": row[3],
                "created_at": row[4],
                "department_count": row[5]
            })
        
        return scenarios
    except sqlite3.Error as e:
        st.error(f"Error fetching scenarios: {e}")
        return []
    finally:
        conn.close()

# Get scenario data as a pandas DataFrame
def get_scenario_data_as_df(scenario_id):
    """Get scenario data as pandas DataFrame for CSV export"""
    # Use budget.db explicitly since that's where the scenarios data is stored
    conn = get_connection("budget.db")
    if not conn:
        return None
    
    try:
        # Get scenario details
        scenario_query = "SELECT * FROM scenarios WHERE id = ?"
        scenario_df = pd.read_sql_query(scenario_query, conn, params=(scenario_id,))
        
        # Get department allocations with proper mapping
        dept_query = """
            SELECT 
                sda.scenario_id, 
                sda.department_id, 
                d.name as department_name, 
                sda.allocation_amount 
            FROM scenario_department_allocations sda 
            JOIN departments d ON sda.department_id = d.id 
            WHERE sda.scenario_id = ?
        """
        dept_df = pd.read_sql_query(dept_query, conn, params=(scenario_id,))
        
        # Combine into a single DataFrame
        result = pd.concat([
            scenario_df,
            pd.DataFrame({
                'department_allocations': [dept_df.to_dict('records')]
            })
        ], axis=1)
        
        return result
    except Exception as e:
        st.error(f"Error exporting scenario: {e}")
        return None
    finally:
        conn.close()

# Transaction data functions
def load_transaction_data(filters=None):
    """
    Load transaction data with optional filters
    
    Args:
        filters (dict, optional): Dictionary of filter criteria
        
    Returns:
        DataFrame: Pandas DataFrame with transaction data
    """
    # Transaction data is always in the databases/core/caselle_gl0_mock.db
    db_path = "databases/core/caselle_gl0_mock.db"  # Always use transaction database for transaction data
    conn = get_connection(db_path)
    
    if not conn:
        return pd.DataFrame()
    
    try:
        query = """
        SELECT 
            t.pk_Transaction,
            t.TransactionDate,
            t.GLAccount,
            t.Amount,
            t.Description,
            t.TransactionType,
            t.Reference
        FROM Transactions t
        """
        
        where_clauses = []
        params = []
        
        # Apply filters if provided
        if filters:
            if 'date_range' in filters and filters['date_range']:
                start_date, end_date = filters['date_range']
                where_clauses.append("t.TransactionDate BETWEEN ? AND ?")
                params.extend([start_date, end_date])
                
            if 'trans_type' in filters and filters['trans_type']:
                types = filters['trans_type']
                placeholders = ','.join(['?' for _ in types])
                where_clauses.append(f"t.TransactionType IN ({placeholders})")
                params.extend(types)
                
            if 'amount_range' in filters and filters['amount_range']:
                min_amount, max_amount = filters['amount_range']
                where_clauses.append("t.Amount BETWEEN ? AND ?")
                params.extend([min_amount, max_amount])
                
            if 'department' in filters and filters['department']:
                # For department filtering, we need to extract department code from GLAccount
                # using the account mask parser
                dept = filters['department']
                where_clauses.append("t.GLAccount LIKE ?")
                params.append(f"%-{dept}-%")
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        print(f"Error loading transaction data: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def load_department_transactions(department=None):
    """
    Load transaction data filtered by department
    
    Args:
        department (str, optional): Department to filter by. If None, returns all transactions.
        
    Returns:
        DataFrame: Pandas DataFrame with transaction data for the specified department
    """
    filters = {'department': department} if department else None
    return load_transaction_data(filters)

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
    
    # Convert TransactionDate to datetime if not already
    transactions_df['TransactionDate'] = pd.to_datetime(transactions_df['TransactionDate'])
    
    # Extract year and month
    transactions_df['Year'] = transactions_df['TransactionDate'].dt.year
    transactions_df['Month'] = transactions_df['TransactionDate'].dt.month
    
    # Group by year and month
    monthly_totals = transactions_df.groupby(['Year', 'Month']).agg({
        'Amount': 'sum',
        'pk_Transaction': 'count'
    }).reset_index()
    
    # Create Month-Year column for display
    monthly_totals['Period'] = monthly_totals.apply(
        lambda x: f"{x['Year']}-{x['Month']:02d}", axis=1
    )
    
    # Sort by date
    monthly_totals = monthly_totals.sort_values(by=['Year', 'Month'])
    
    return monthly_totals

def get_gl_account_balances(transactions_df):
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
        'Amount': 'sum',
        'pk_Transaction': 'count'
    }).reset_index()
    
    # Rename columns for clarity
    gl_balances.columns = ['GLAccount', 'Balance', 'TransactionCount']
    
    # Sort by absolute balance (largest amounts first)
    gl_balances = gl_balances.sort_values(by='Balance', key=abs, ascending=False)
    
    return gl_balances

def get_department_list() -> List[str]:
    """
    Get the list of department names from the transaction database
    
    Returns:
        List[str]: List of department names
    """
    # Department mapping based on department codes in transaction data
    # These are the 4 unique departments in the transaction database
    dept_mapping = {
        '01': 'Administration',
        '02': 'Finance',  
        '03': 'Police',
        '04': 'Fire'
    }
    
    # Get transactions to extract department codes from GLAccount field
    try:
        # Transaction data is always in databases/core/caselle_gl0_mock.db
        db_path = "databases/core/caselle_gl0_mock.db"
        conn = get_connection(db_path)
        
        if not conn:
            return list(dept_mapping.values())
        
        # Get unique GL Account patterns to extract department codes
        query = "SELECT DISTINCT GLAccount FROM Transactions"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            return list(dept_mapping.values())
            
        # Extract department codes from GLAccount field using mask parser
        departments = set()
        for account in df['GLAccount']:
            # Account format is typically like "01-02-0000" where the second segment is department
            parts = account.split('-')
            if len(parts) >= 2:
                dept_code = parts[1]
                if dept_code in dept_mapping:
                    departments.add(dept_mapping[dept_code])
        
        # If we found departments, return them sorted
        if departments:
            return sorted(list(departments))
        
        # Fallback to known departments if we couldn't extract from data
        return list(dept_mapping.values())
        
    except Exception as e:
        print(f"Error getting department list: {e}")
        # Fallback to known departments if there's an error
        return list(dept_mapping.values())

# Formatting utility functions
def format_currency(value):
    """
    Format a numeric value as currency with exactly two decimal places
    
    Args:
        value (float or int): The numeric value to format
        
    Returns:
        str: Formatted string with commas and exactly two decimal places
    """
    try:
        # Convert to float first in case it's a string or other type
        value = float(value)
        return f"${value:,.2f}"
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
        # Convert to float first in case it's a string or other type
        value = float(value)
        return f"{value:.2f}%"
    except (ValueError, TypeError):
        return "0.00%"

# Get detailed scenario data for BI Sandbox
def get_detailed_scenario_data(scenario_id):
    """
    Get detailed scenario data for visualization in BI Sandbox
    
    Args:
        scenario_id (int): ID of the scenario to retrieve
        
    Returns:
        dict: Dictionary with scenario details and formatted data for charts
    """
    # Use budget.db explicitly since that's where the scenarios data is stored
    conn = get_connection("budget.db")
    if not conn:
        return None
    
    try:
        # Get scenario details
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, project_id, tax_revenue, grant_funding, "
            "private_investment, bonds_needed, total_cost, creation_date "
            "FROM scenarios WHERE id = ?",
            (scenario_id,)
        )
        
        scenario_row = cursor.fetchone()
        if not scenario_row:
            return None
        
        # Get project details
        project_id = scenario_row[2]
        project_name = "Unknown Project"
        
        if project_id:
            cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
            project_row = cursor.fetchone()
            if project_row:
                project_name = project_row[0]
        
        # Get department allocations
        cursor.execute("""
            SELECT 
                d.name as department_name, 
                sda.allocation_amount
            FROM 
                scenario_department_allocations sda
            JOIN 
                departments d ON sda.department_id = d.id
            WHERE 
                sda.scenario_id = ?
        """, (scenario_id,))
        
        departments = {}
        for dept_row in cursor.fetchall():
            departments[dept_row[0]] = dept_row[1]
        
        # Create formatted data for visualization
        funding_data = {
            "id": scenario_row[0],
            "name": scenario_row[1],
            "project_id": project_id,
            "project_name": project_name,
            "tax_revenue": scenario_row[3],
            "grant_funding": scenario_row[4],
            "private_investment": scenario_row[5],
            "bonds_needed": scenario_row[6],
            "total_cost": scenario_row[7],
            "creation_date": scenario_row[8],
            "department_allocations": departments,
            "formatted_data": []
        }
        
        # Add data for Funding Source visualization
        sources = []
        values = []
        
        # Department reallocation total
        dept_total = sum(departments.values())
        if dept_total > 0:
            sources.append("Department Reallocation")
            values.append(dept_total)
        
        # Other funding sources
        if funding_data["tax_revenue"] > 0:
            sources.append("Tax Revenue")
            values.append(funding_data["tax_revenue"])
            
        if funding_data["grant_funding"] > 0:
            sources.append("Grant Funding")
            values.append(funding_data["grant_funding"])
            
        if funding_data["private_investment"] > 0:
            sources.append("Private Investment")
            values.append(funding_data["private_investment"])
            
        if funding_data["bonds_needed"] > 0:
            sources.append("Bonds Needed")
            values.append(funding_data["bonds_needed"])
        
        # Add funding source data
        for source, value in zip(sources, values):
            funding_data["formatted_data"].append({
                "FundingSource": source,
                "Amount": value,
                "Category": "Funding",
                "Percentage": (value / funding_data["total_cost"]) * 100 if funding_data["total_cost"] > 0 else 0
            })
        
        # Add department allocation data if any departments contributed
        if dept_total > 0:
            for dept, amount in departments.items():
                if amount > 0:
                    funding_data["formatted_data"].append({
                        "FundingSource": dept,
                        "Amount": amount,
                        "Category": "Department",
                        "Percentage": (amount / dept_total) * 100
                    })
        
        return funding_data
    except Exception as e:
        st.error(f"Error fetching detailed scenario data: {e}")
        return None
    finally:
        conn.close()

# Authentication functions
def check_password(org_id: str, entered_password: str) -> bool:
    """
    Check if the entered password matches the organization password
    
    Args:
        org_id (str): Organization identifier
        entered_password (str): Password entered by the user
        
    Returns:
        bool: True if password matches, False otherwise
    """
    config = load_config()
    
    if org_id in config and "login_password" in config[org_id]:
        return entered_password == config[org_id]["login_password"]
    
    return False

def get_org_display_info(org_id: str = None) -> Dict[str, str]:
    """
    Get display information for an organization
    
    Args:
        org_id (str, optional): Organization identifier. Defaults to None.
        
    Returns:
        Dict[str, str]: Dictionary with display information
    """
    if not org_id:
        return {"name": "GovSight", "theme_color": "#0066cc"}
    
    config = load_config()
    
    if org_id in config:
        return {
            "name": config[org_id].get("org_name", org_id),
            "theme_color": config[org_id].get("theme_color", "#0066cc")
        }
    
    return {"name": org_id, "theme_color": "#0066cc"}

# Transaction data access functions
# -------------------------------------------------------------------------

def get_selected_database():
    """
    Get the currently selected database path based on admin settings
    
    Returns:
        str: Database path
    """
    # Check if a database path is explicitly set in session state
    if hasattr(st, 'session_state') and 'db_path' in st.session_state:
        return st.session_state.db_path
    
    # Load settings to see if there's a custom database path
    settings = load_settings()
    if 'current_database' in settings:
        return settings['current_database']
    
    # Default to the transaction database
    return DEFAULT_DB_PATH

def load_transaction_data() -> pd.DataFrame:
    """
    Load all transaction data from the database with proper GL account parsing
    
    Returns:
        DataFrame: Pandas DataFrame with transaction data
    """
    try:
        # Connect to the Caselle database
        conn = get_connection(get_selected_database())
        
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