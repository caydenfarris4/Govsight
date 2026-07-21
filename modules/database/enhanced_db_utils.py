"""
Enhanced Database Utilities for GovSight Financial Analyzer

This module provides enhanced database utilities that support multiple SQL database types
and integrates with the existing common_utils functions.

It supports:
- SQLite (default, file-based)
- PostgreSQL
- MySQL/MariaDB
- Microsoft SQL Server

Usage example:
    from enhanced_db_utils import get_connection, execute_query, get_departments
    
    # Get departments for a specific organization
    departments = get_departments("cityA")
    
    # Run a custom query
    results = execute_query("SELECT * FROM projects")
"""

import os
import json
import logging
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional, Union, Any, Tuple
from sql_connection import SQLDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('enhanced_db_utils')

try:
    from modules.services.config_service import get_config_service
    _config_svc = get_config_service()
    CONFIG = _config_svc.get_namespace("city_config")
    if not CONFIG:
        raise ValueError("Empty config")
except Exception:
    try:
        with open("config.json") as f:
            CONFIG = json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        CONFIG = {}

# Connection cache to avoid redundant connections
_connection_cache = {}

def get_connection_config(org=None):
    """
    Get the database connection configuration for an organization.
    
    Args:
        org (str, optional): Organization identifier. Defaults to None.
        
    Returns:
        dict: Configuration dictionary for database connection
    """
    if not org:
        # Default to SQLite with budget.db
        return {"dbtype": "sqlite", "database_path": "budget.db"}
    
    # Check if there's organization config in the new format
    if 'organizations' in CONFIG and org in CONFIG['organizations']:
        org_config = CONFIG['organizations'][org]
        if 'database' in org_config:
            return org_config['database']
    
    # For backwards compatibility, check legacy format
    db_path = get_db_path_for_org(org)
    return {"dbtype": "sqlite", "database_path": db_path}

def get_connection(org=None):
    """
    Get a database connection for the specified organization.
    
    Args:
        org (str, optional): Organization identifier. Defaults to None.
        
    Returns:
        SQLDatabase: A database connection
    """
    global _connection_cache
    
    # Return cached connection if available
    cache_key = str(org)
    if cache_key in _connection_cache:
        try:
            # Test connection to make sure it's still valid
            if _connection_cache[cache_key].check_connection():
                return _connection_cache[cache_key]
            # If connection test fails, remove from cache and get a new one
            del _connection_cache[cache_key]
        except Exception:
            # If there's an error, remove from cache and get a new one
            del _connection_cache[cache_key]
    
    # Get connection configuration
    db_config = get_connection_config(org)
    
    try:
        # Create the database connection
        db = SQLDatabase(**db_config)
        
        # Cache the connection
        _connection_cache[cache_key] = db
        
        return db
    except Exception as e:
        logger.error(f"Error connecting to database for {org}: {e}")
        if st:  # Only show error if streamlit is available
            st.error(f"Database connection error: {e}")
        return None

def execute_query(
    query: str,
    params: Optional[Union[Dict[str, Any], List[Any], Tuple[Any, ...]]] = None,
    fetchall: bool = True,
    org: Optional[str] = None
) -> Union[List[Dict[str, Any]], None]:
    """
    Execute a query and return results.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        fetchall: Whether to fetch all results
        org: Organization identifier
        
    Returns:
        Query results or None if error
    """
    db = get_connection(org)
    if not db:
        return None
    
    try:
        return db.execute_query(query, params, fetchall)
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        if st:  # Only show error if streamlit is available
            st.error(f"Query execution error: {e}")
        return None

def run_dashboard_query(query, org_filter=None):
    """
    Execute a query against the dashboard database with organization filtering.
    
    Args:
        query: SQL query to execute
        org_filter: Organization identifier to filter results
        
    Returns:
        DataFrame with query results
    """
    try:
        # Check for unsafe SQL operations
        banned = ["drop", "delete", "update", "insert", "alter"]
        if any(word in query.lower() for word in banned):
            return " Unsafe query blocked."
            
        # Get the database connection for this organization
        db = get_connection(org_filter)
        if not db:
            return f"Database connection error for {org_filter}"
        
        # Add organization filter if provided and the table has an Organization column
        if org_filter:
            try:
                # Check if the DepartmentPerformance table exists and has an Organization column
                tables = db.get_tables()
                if "DepartmentPerformance" in tables:
                    columns = db.get_columns("DepartmentPerformance")
                    column_names = [col.get('name') for col in columns]
                    
                    if "Organization" in column_names:
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
            except Exception as e:
                logger.warning(f"Error checking schema for organization filtering: {e}")
        
        # Debug output
        logger.info(f"Executing query for {org_filter}: {query}")
        
        # Execute the query
        result = db.execute_query(query)
        
        # Check if the result is an error message
        if isinstance(result, str):
            return result
            
        # Convert the result to a DataFrame
        if result:
            df = pd.DataFrame(result)
            
            # Round all numeric columns to two decimal places
            numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
            for col in numeric_columns:
                df[col] = df[col].round(2)
                
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        error_msg = f"Error executing query for {org_filter}: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_departments(org=None):
    """
    Get all departments from the database, with improved organization-specific handling.
    
    This function first tries to get department data from the organization-specific database.
    If that fails, it falls back to the legacy departments table.
    
    Args:
        org (str, optional): Organization identifier for org-specific data. Defaults to None.
        
    Returns:
        dict: Dictionary of departments with budget and underspent data
    """
    departments = {}
    
    # First try to get department data from the organization's database
    if org:
        try:
            # Get the database connection for this organization
            db = get_connection(org)
            if db:
                # Use ROUND function in SQL to ensure all values are properly rounded to 2 decimal places
                # Check if the table has an Organization column
                try:
                    schema_query = "PRAGMA table_info(DepartmentPerformance)"
                    columns = db.execute_query(schema_query)
                    has_org_column = any(col.get('name') == 'Organization' for col in columns) if columns else False
                    
                    if has_org_column:
                        query = f"""
                        SELECT 
                            Department, 
                            ROUND(SUM(Budget), 2) as Budget, 
                            ROUND(SUM(Budget - Actual), 2) as Underspent 
                        FROM DepartmentPerformance 
                        WHERE Organization = '{org}' AND FiscalYear = 'FY 2024' 
                        GROUP BY Department
                        """
                    else:
                        # No Organization column, don't filter by it
                        query = f"""
                        SELECT 
                            Department, 
                            ROUND(SUM(Budget), 2) as Budget, 
                            ROUND(SUM(Budget - Actual), 2) as Underspent 
                        FROM DepartmentPerformance 
                        WHERE FiscalYear = 'FY 2024' 
                        GROUP BY Department
                        """
                except Exception as e:
                    # If schema check fails, use a query without Organization filter
                    logger.warning(f"Error checking schema, using query without Organization filter: {e}")
                    query = f"""
                    SELECT 
                        Department, 
                        ROUND(SUM(Budget), 2) as Budget, 
                        ROUND(SUM(Budget - Actual), 2) as Underspent 
                    FROM DepartmentPerformance 
                    WHERE FiscalYear = 'FY 2024' 
                    GROUP BY Department
                    """
                
                # Execute the query
                result = db.execute_query(query)
                
                if result:
                    # Convert the result to the expected format
                    for row in result:
                        # Round values to ensure exactly 2 decimal places
                        budget_value = round(float(row['Budget']), 2)
                        underspent_value = round(float(row['Underspent']), 2) if row.get('Underspent', 0) > 0 else 0.00
                        
                        departments[row['Department']] = {
                            "id": 0,  # Use placeholder ID since we don't have real IDs in the dashboard data
                            "budget": budget_value,
                            "underspent": underspent_value
                        }
                    return departments
        except Exception as e:
            logger.error(f"Could not load department data from database for {org}: {str(e)}")
    
    # Fall back to legacy departments table in the default database
    db = get_database_connection()
    if db:
        query = "SELECT id, name, ROUND(total_budget, 2) as total_budget, ROUND(underspent, 2) as underspent FROM departments"
        result = db.execute_query(query)
        
        if result:
            # Convert to dictionary with department name as key
            for dept in result:
                departments[dept['name']] = {
                    "id": dept['id'],
                    "budget": round(float(dept['total_budget']), 2),
                    "underspent": round(float(dept['underspent']), 2)
                }
    
    return departments

def get_projects():
    """Get all projects from the database"""
    db = get_database_connection()
    if not db:
        return []
        
    query = "SELECT * FROM projects"
    return db.execute_query(query)

def save_scenario(scenario_data, department_allocations):
    """Save a funding scenario to the database"""
    db = get_database_connection()
    if not db:
        return False
        
    try:
        # Insert scenario data
        scenario_query = """
        INSERT INTO scenarios (
            name, total_amount, description, created_at
        ) VALUES (
            :name, :total_amount, :description, datetime('now')
        )
        """
        
        db.execute_query(scenario_query, scenario_data, fetchall=False)
        
        # Get the scenario ID
        scenario_id_query = "SELECT last_insert_rowid() as id"
        scenario_id_result = db.execute_query(scenario_id_query)
        scenario_id = scenario_id_result[0]['id'] if scenario_id_result else None
        
        if not scenario_id:
            return False
            
        # Insert department allocations
        for dept_id, amount in department_allocations.items():
            allocation_query = """
            INSERT INTO scenario_departments (
                scenario_id, department_id, amount
            ) VALUES (
                :scenario_id, :department_id, :amount
            )
            """
            
            allocation_data = {
                "scenario_id": scenario_id,
                "department_id": int(dept_id),
                "amount": float(amount)
            }
            
            db.execute_query(allocation_query, allocation_data, fetchall=False)
            
        return True
    except Exception as e:
        logger.error(f"Error saving scenario: {e}")
        if st:  # Only show error if streamlit is available
            st.error(f"Error saving scenario: {e}")
        return False

def get_scenarios(limit=10):
    """Get the most recent scenarios from the database"""
    db = get_database_connection()
    if not db:
        return []
        
    query = f"""
    SELECT
        s.id,
        s.name,
        s.description,
        s.total_amount,
        s.created_at,
        COUNT(sd.department_id) as department_count
    FROM
        scenarios s
    LEFT JOIN
        scenario_departments sd ON s.id = sd.scenario_id
    GROUP BY
        s.id
    ORDER BY
        s.created_at DESC
    LIMIT {limit}
    """
    
    return db.execute_query(query)

def get_scenario_data_as_df(scenario_id):
    """Get scenario data as pandas DataFrame for CSV export"""
    db = get_database_connection()
    if not db:
        return pd.DataFrame()
        
    query = """
    SELECT
        d.name as Department,
        sd.amount as Amount,
        s.name as Scenario,
        s.created_at as Created
    FROM
        scenario_departments sd
    JOIN
        departments d ON sd.department_id = d.id
    JOIN
        scenarios s ON sd.scenario_id = s.id
    WHERE
        sd.scenario_id = :scenario_id
    ORDER BY
        d.name
    """
    
    result = db.execute_query(query, {"scenario_id": scenario_id})
    
    if not result:
        return pd.DataFrame()
        
    # Convert to DataFrame
    df = pd.DataFrame(result)
    
    # Round all numeric columns to two decimal places
    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_columns:
        df[col] = df[col].round(2)
        
    return df

def get_db_path_for_org(org):
    """
    Get the appropriate database path for an organization.
    Legacy function for backwards compatibility.
    
    Args:
        org (str): Organization identifier
        
    Returns:
        str: Database path for the organization
    """
    # Default database path
    db_path = "org_dashboard_data.db"
    
    # Legacy format in config.json
    if org and org in CONFIG and 'dashboard_db' in CONFIG[org]:
        db_path = CONFIG[org]['dashboard_db']
    # New format in config.json
    elif org and 'organizations' in CONFIG and org in CONFIG['organizations']:
        org_config = CONFIG['organizations'][org]
        if 'database' in org_config and 'database_path' in org_config['database']:
            db_path = org_config['database']['database_path']
    # Default to organization-specific database file
    elif org:
        db_path = f"{org}_dashboard_data.db"
        
    return db_path

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
        num_value = float(value)
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
        num_value = float(value)
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
        # Get the database connection for this organization
        db = get_connection(org_filter)
        if not db:
            return pd.DataFrame()
        
        # Build the query
        query = "SELECT * FROM DepartmentPerformance"
        
        # Check if Organization column exists before filtering by it
        try:
            if org_filter:
                schema_query = "PRAGMA table_info(DepartmentPerformance)"
                columns = db.execute_query(schema_query)
                has_org_column = any(col.get('name') == 'Organization' for col in columns) if columns else False
                
                if has_org_column:
                    query += f" WHERE Organization = '{org_filter}'"
                # If no Organization column, don't filter (return all rows)
        except Exception as e:
            logger.warning(f"Error checking DepartmentPerformance schema: {e}")
            
        # Execute the query
        result = db.execute_query(query)
        
        if not result:
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(result)
        
        # Round all numeric columns to two decimal places
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            df[col] = df[col].round(2)
            
        return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame()

def close_connections():
    """Close all database connections"""
    global _connection_cache
    for cache_key, db in _connection_cache.items():
        try:
            db.close()
        except:
            pass
    _connection_cache = {}