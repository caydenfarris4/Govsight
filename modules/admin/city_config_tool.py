"""
GovSight City Configuration Tool

This tool allows administrators to add new cities/organizations to the GovSight
platform with their own database connections and custom settings.

Usage:
    python city_config_tool.py add-city
    python city_config_tool.py list-cities
    python city_config_tool.py test-connection cityA
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional
import getpass
from sql_connection import SQLDatabase

# Default configuration file path
CONFIG_FILE = 'config.json'

def load_config() -> Dict[str, Any]:
    """Load the current configuration from config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {CONFIG_FILE} is not valid JSON")
            return {"organizations": {}}
    else:
        return {"organizations": {}}

def save_config(config: Dict[str, Any]) -> None:
    """Save the configuration to config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"Configuration saved to {CONFIG_FILE}")

def add_city() -> None:
    """
    Interactive tool to add a new city/organization to the configuration.
    Guides the user through specifying database connection details and other settings.
    """
    config = load_config()
    
    print("=== Add New City/Organization to GovSight ===")
    
    # Basic organization information
    org_id = input("Organization ID (e.g., cityA, countyB): ").strip()
    if not org_id:
        print("Error: Organization ID is required")
        return
    
    if org_id in config.get('organizations', {}):
        overwrite = input(f"Organization '{org_id}' already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Operation cancelled")
            return
    
    # Organization details
    org_name = input("Organization Display Name (e.g., City of Springfield): ").strip()
    password = getpass.getpass("Access Password (leave empty for no password): ")
    
    # Database configuration
    print("\n=== Database Connection Configuration ===")
    print("Supported database types: sqlite, postgresql, mysql, mssql")
    
    db_type = input("Database Type [sqlite]: ").strip().lower() or "sqlite"
    
    db_config = {
        "dbtype": db_type
    }
    
    if db_type == "sqlite":
        db_path = input("Database Path [org_dashboard_data.db]: ").strip() or f"{org_id}_dashboard_data.db"
        db_config["database_path"] = db_path
    else:
        db_config["host"] = input("Database Host [localhost]: ").strip() or "localhost"
        db_config["port"] = input(f"Database Port [{get_default_port(db_type)}]: ").strip() or get_default_port(db_type)
        db_config["user"] = input("Database Username: ").strip()
        db_config["password"] = getpass.getpass("Database Password: ")
        db_config["database"] = input("Database Name: ").strip()
    
    # Visual customization
    print("\n=== Visual Customization ===")
    primary_color = input("Primary Color [#3498db]: ").strip() or "#3498db"
    logo_url = input("Logo URL (optional): ").strip()
    
    # Create organization config
    org_config = {
        "display_name": org_name,
        "database": db_config,
        "theme": {
            "primary_color": primary_color
        }
    }
    
    if password:
        org_config["password"] = password
    
    if logo_url:
        org_config["theme"]["logo_url"] = logo_url
    
    # Add to configuration
    if 'organizations' not in config:
        config['organizations'] = {}
    
    config['organizations'][org_id] = org_config
    
    # Test database connection
    print("\nTesting database connection...")
    connection_successful = test_db_connection(db_config)
    
    if connection_successful:
        print("Database connection successful!")
    else:
        print("Warning: Could not connect to the database with the provided settings.")
        proceed = input("Save configuration anyway? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Operation cancelled")
            return
    
    # Save configuration
    save_config(config)
    print(f"Organization '{org_id}' ({org_name}) has been added to the configuration")
    print(f"You can now access it at: /?org={org_id}")

def list_cities() -> None:
    """List all configured cities/organizations."""
    config = load_config()
    orgs = config.get('organizations', {})
    
    if not orgs:
        print("No organizations configured")
        return
    
    print("=== Configured Organizations ===")
    for org_id, org_config in orgs.items():
        db_type = org_config.get('database', {}).get('dbtype', 'unknown')
        db_path = org_config.get('database', {}).get('database_path', '')
        db_name = org_config.get('database', {}).get('database', '')
        db_info = db_path if db_type == 'sqlite' else db_name
        
        print(f"- {org_id}: {org_config.get('display_name', 'Unknown')}")
        print(f"  Database: {db_type} ({db_info})")
        print(f"  Password Protected: {'Yes' if 'password' in org_config else 'No'}")
        print()

def test_connection(org_id: str) -> None:
    """Test database connection for a specific organization."""
    config = load_config()
    orgs = config.get('organizations', {})
    
    if org_id not in orgs:
        print(f"Error: Organization '{org_id}' not found")
        return
    
    org_config = orgs[org_id]
    db_config = org_config.get('database', {})
    
    print(f"Testing database connection for '{org_id}'...")
    connection_successful = test_db_connection(db_config)
    
    if connection_successful:
        print("Connection successful!")
        print("\nAvailable tables:")
        list_tables(db_config)
    else:
        print("Connection failed.")

def test_db_connection(db_config: Dict[str, Any]) -> bool:
    """Test a database connection using the given configuration."""
    try:
        db = SQLDatabase(**db_config)
        return db.check_connection()
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def list_tables(db_config: Dict[str, Any]) -> None:
    """List tables in the database."""
    try:
        db = SQLDatabase(**db_config)
        tables = db.get_tables()
        
        if not tables:
            print("No tables found")
            return
        
        for table in tables:
            print(f"- {table}")
            
            # Get column information
            columns = db.get_columns(table)
            if columns:
                print("  Columns:")
                for col in columns:
                    col_type = str(col.get('type', 'unknown'))
                    print(f"  - {col.get('name', 'unknown')} ({col_type})")
        
    except Exception as e:
        print(f"Error listing tables: {str(e)}")

def get_default_port(db_type: str) -> str:
    """Get the default port for a database type."""
    ports = {
        'postgresql': '5432',
        'mysql': '3306',
        'mssql': '1433'
    }
    return ports.get(db_type, '5432')

def main() -> None:
    parser = argparse.ArgumentParser(description="GovSight City Configuration Tool")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Add city command
    add_parser = subparsers.add_parser('add-city', help='Add a new city/organization')
    
    # List cities command
    list_parser = subparsers.add_parser('list-cities', help='List all configured cities/organizations')
    
    # Test connection command
    test_parser = subparsers.add_parser('test-connection', help='Test database connection for an organization')
    test_parser.add_argument('org_id', help='Organization ID to test')
    
    args = parser.parse_args()
    
    if args.command == 'add-city':
        add_city()
    elif args.command == 'list-cities':
        list_cities()
    elif args.command == 'test-connection':
        test_connection(args.org_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()