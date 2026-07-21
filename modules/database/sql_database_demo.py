"""
GovSight SQL Database Connection Demo

This script demonstrates how to use the SQL database connection tools to:
1. Connect to different types of SQL databases
2. Configure multiple cities/organizations
3. Query and manipulate data across different databases

Usage:
    python sql_database_demo.py
"""

import os
import json
import pandas as pd
from sql_connection import SQLDatabase
from enhanced_db_utils import (
    get_connection, 
    execute_query, 
    format_currency, 
    format_percentage
)

def demo_sqlite_connection():
    """Demonstrate SQLite connection and queries."""
    print("\n=== SQLite Connection Demo ===")
    
    # Connect to SQLite
    db = SQLDatabase(dbtype='sqlite', database_path='org_dashboard_data.db')
    
    # Check connection
    if db.check_connection():
        print("✓ Successfully connected to SQLite database")
    else:
        print("✗ Failed to connect to SQLite database")
        return
    
    # List tables
    tables = db.get_tables()
    print(f"\nAvailable tables in database ({len(tables)}):")
    for table in tables:
        print(f"- {table}")
    
    # If there's a DepartmentPerformance table, show sample data
    if 'DepartmentPerformance' in tables:
        # Get column information
        columns = db.get_columns('DepartmentPerformance')
        print("\nDepartmentPerformance columns:")
        for col in columns:
            print(f"- {col['name']} ({col['type']})")
        
        # Sample query
        print("\nSample data from DepartmentPerformance:")
        results = db.execute_query("SELECT * FROM DepartmentPerformance LIMIT 5")
        
        if results:
            # Show formatted data
            for i, row in enumerate(results):
                print(f"\nRow {i+1}:")
                for col, val in row.items():
                    # Format currency fields
                    if col in ['Budget', 'Actual']:
                        print(f"  {col}: {format_currency(val)}")
                    # Format percentage fields
                    elif col in ['PercentUnderspent']:
                        print(f"  {col}: {format_percentage(val)}")
                    else:
                        print(f"  {col}: {val}")
    
    # Close connection
    db.close()

def demo_postgres_connection():
    """Demonstrate PostgreSQL connection (commented out for demo)."""
    print("\n=== PostgreSQL Connection Demo ===")
    print("To connect to PostgreSQL, uncomment the code in this function and provide your credentials.")
    
    """
    # Connect to PostgreSQL
    db = SQLDatabase(
        dbtype='postgresql',
        host='localhost',
        port=5432,
        user='username',
        password='password',
        database='budget_db'
    )
    
    # Check connection
    if db.check_connection():
        print("✓ Successfully connected to PostgreSQL database")
        
        # List tables
        tables = db.get_tables()
        print(f"\nAvailable tables in PostgreSQL database ({len(tables)}):")
        for table in tables:
            print(f"- {table}")
            
        # Execute sample query
        results = db.execute_query("SELECT 'PostgreSQL is working!' as message")
        print(f"\nQuery result: {results[0]['message']}")
    else:
        print("✗ Failed to connect to PostgreSQL database")
    
    # Close connection
    db.close()
    """

def demo_multiple_organizations():
    """Demonstrate multiple organization setup and queries."""
    print("\n=== Multiple Organizations Demo ===")
    
    # Create a sample configuration
    config = {
        "organizations": {
            "cityA": {
                "display_name": "City of Springfield",
                "database": {
                    "dbtype": "sqlite",
                    "database_path": "cityA_dashboard_data.db"
                }
            },
            "cityB": {
                "display_name": "Shelbyville Metro",
                "database": {
                    "dbtype": "sqlite",
                    "database_path": "cityB_dashboard_data.db"
                }
            }
        }
    }
    
    # Save the configuration (for demonstration)
    with open("demo_config.json", "w") as f:
        json.dump(config, f, indent=4)
    
    print("Created sample configuration with two organizations")
    print("- cityA: City of Springfield (SQLite)")
    print("- cityB: Shelbyville Metro (SQLite)")
    
    # Check if the database files exist
    cityA_exists = os.path.exists("cityA_dashboard_data.db")
    cityB_exists = os.path.exists("cityB_dashboard_data.db")
    
    print(f"\nDatabase status:")
    print(f"- cityA_dashboard_data.db: {'✓ Exists' if cityA_exists else '✗ Not found'}")
    print(f"- cityB_dashboard_data.db: {'✓ Exists' if cityB_exists else '✗ Not found'}")
    
    # Demonstrate using enhanced_db_utils with multiple organizations
    print("\nUsing enhanced_db_utils to query multiple organizations:")
    
    # The enhanced_db_utils would normally use the real config.json
    # For this demo, we're just showing the concept
    if cityA_exists:
        print("\n== City A Departments ==")
        db = get_connection("cityA")  # This would normally read from config.json
        if db:
            query = """
            SELECT 
                Department, 
                ROUND(SUM(Budget), 2) as Budget, 
                ROUND(SUM(Budget - Actual), 2) as Underspent 
            FROM DepartmentPerformance 
            WHERE Organization = 'cityA'
            GROUP BY Department
            LIMIT 5
            """
            results = db.execute_query(query)
            if results:
                for row in results:
                    dept = row.get('Department', 'Unknown')
                    budget = format_currency(row.get('Budget', 0))
                    underspent = format_currency(row.get('Underspent', 0))
                    print(f"- {dept}: Budget {budget}, Underspent {underspent}")
    
    if cityB_exists:
        print("\n== City B Departments ==")
        db = get_connection("cityB")  # This would normally read from config.json
        if db:
            query = """
            SELECT 
                Department, 
                ROUND(SUM(Budget), 2) as Budget, 
                ROUND(SUM(Budget - Actual), 2) as Underspent 
            FROM DepartmentPerformance 
            WHERE Organization = 'cityB'
            GROUP BY Department
            LIMIT 5
            """
            results = db.execute_query(query)
            if results:
                for row in results:
                    dept = row.get('Department', 'Unknown')
                    budget = format_currency(row.get('Budget', 0))
                    underspent = format_currency(row.get('Underspent', 0))
                    print(f"- {dept}: Budget {budget}, Underspent {underspent}")

def demo_connection_pool():
    """Demonstrate connection pooling and efficiency."""
    print("\n=== Connection Pooling Demo ===")
    
    print("Creating 10 database connections with the same parameters...")
    
    # Create 10 connections with the same parameters
    for i in range(10):
        db = get_connection("cityA")  # Should reuse the same connection after the first one
        if db:
            print(f"Connection {i+1}: Connected to database")
    
    print("\nEven though we created 10 'connections', they all reuse the same pool.")
    print("This improves performance and prevents connection leaks.")

def main():
    print("=== GovSight SQL Database Connection Demo ===")
    print("This demo shows how to use the SQL connection tools to work with multiple databases")
    
    # Run the SQLite demo
    demo_sqlite_connection()
    
    # Run the PostgreSQL demo (commented out code)
    demo_postgres_connection()
    
    # Run the multiple organizations demo
    demo_multiple_organizations()
    
    # Run the connection pool demo
    demo_connection_pool()
    
    print("\n=== Demo Complete ===")
    print("You can now:")
    print("1. Use `python city_config_tool.py add-city` to add a new city/organization")
    print("2. Modify app.py to use the enhanced_db_utils module")
    print("3. Connect to any type of SQL database in your GovSight application")

if __name__ == "__main__":
    main()