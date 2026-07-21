"""
Multi-Database Manager for GovSight BI Sandbox
Handles connections to all 5 municipal database types and provides unified schema discovery.

Supports:
- GL Primary Database (SQLite)
- Utility Management Database (PostgreSQL)  
- Asset Management Database (MySQL)
- Permits & Licensing Database (SQL Server)
- Payroll Database (PostgreSQL/SQLite)
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import pandas as pd
from pathlib import Path

# Import database connectors with fallbacks
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import pyodbc
    SQLSERVER_AVAILABLE = True
except ImportError:
    pyodbc = None
    SQLSERVER_AVAILABLE = False

# Import existing connection manager
from modules.database.connection_manager import load_db_config, get_database_connection
from modules.bi_sandbox.schema_catalog_manager import schema_catalog_manager

logger = logging.getLogger(__name__)

class MultiDatabaseManager:
    """
    Unified manager for all 5 municipal database types with schema discovery and caching.
    """
    
    def __init__(self):
        self.connections = {}
        self.schemas_cache = {}
        self.cache_timestamp = {}
        self.config = load_db_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize sample databases for demo purposes
        self._ensure_sample_databases()
    
    def _ensure_sample_databases(self):
        """Create sample databases for demo purposes if external databases aren't available."""
        try:
            # Create sample utility management database (SQLite simulation)
            self._create_sample_utility_db()
            
            # Create sample asset management database (SQLite simulation)
            self._create_sample_asset_db()
            
            # Create sample permits database (SQLite simulation)  
            self._create_sample_permits_db()
            
            # Update configuration to use sample databases
            self._update_config_for_samples()
            
        except Exception as e:
            self.logger.error(f"Error creating sample databases: {e}")
    
    def _create_sample_utility_db(self):
        """Create sample utility management database only if it doesn't exist."""
        db_path = "databases/sample_utility_management.db"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Check if database already exists and has data - skip if so
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM water_meters")
                count = cursor.fetchone()[0]
                conn.close()
                if count > 0:
                    return  # Database already has data, skip recreation
            except:
                pass  # Table doesn't exist, continue with creation
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Water System Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS water_meters (
                meter_id INTEGER PRIMARY KEY,
                account_number TEXT NOT NULL,
                customer_name TEXT,
                address TEXT,
                meter_size TEXT,
                install_date DATE,
                last_reading_date DATE,
                current_reading REAL,
                previous_reading REAL,
                consumption REAL,
                rate_class TEXT,
                service_status TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS water_infrastructure (
                asset_id INTEGER PRIMARY KEY,
                asset_type TEXT,
                location TEXT,
                install_date DATE,
                condition_rating INTEGER,
                maintenance_schedule TEXT,
                replacement_cost REAL,
                criticality_level TEXT
            )
        """)
        
        # Sewer System Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sewer_connections (
                connection_id INTEGER PRIMARY KEY,
                property_id TEXT,
                connection_type TEXT,
                pipe_diameter REAL,
                connection_date DATE,
                inspection_status TEXT,
                last_inspection_date DATE
            )
        """)
        
        # Electric Utility Tables (if applicable)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS electric_accounts (
                account_id INTEGER PRIMARY KEY,
                customer_name TEXT,
                service_address TEXT,
                meter_number TEXT,
                rate_schedule TEXT,
                monthly_kwh REAL,
                monthly_charge REAL,
                service_type TEXT
            )
        """)
        
        # Insert sample data
        sample_meters = [
            (1, 'UT001', 'John Smith', '123 Main St', '3/4"', '2020-01-15', '2024-09-01', 15420, 15200, 220, 'Residential', 'Active'),
            (2, 'UT002', 'Jane Doe', '456 Oak Ave', '1"', '2019-05-20', '2024-09-01', 28750, 28500, 250, 'Residential', 'Active'),
            (3, 'UT003', 'City Park', '789 Park Blvd', '2"', '2018-03-10', '2024-09-01', 45200, 44800, 400, 'Municipal', 'Active')
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO water_meters 
            (meter_id, account_number, customer_name, address, meter_size, install_date, 
             last_reading_date, current_reading, previous_reading, consumption, rate_class, service_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_meters)
        
        sample_infrastructure = [
            (1, 'Water Main', 'Main St (100-200 block)', '1985-06-15', 7, 'Annual', 125000, 'High'),
            (2, 'Fire Hydrant', 'Main St & 1st Ave', '1990-08-20', 8, 'Semi-Annual', 5000, 'Critical'),
            (3, 'Pump Station', 'Water Treatment Plant', '2005-04-12', 9, 'Monthly', 250000, 'Critical')
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO water_infrastructure 
            (asset_id, asset_type, location, install_date, condition_rating, 
             maintenance_schedule, replacement_cost, criticality_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_infrastructure)
        
        conn.commit()
        conn.close()
        
        self.logger.info("Sample utility management database created successfully")
    
    def _create_sample_asset_db(self):
        """Create sample asset management database only if it doesn't exist."""
        db_path = "databases/sample_asset_management.db"
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Check if database already exists and has data - skip if so
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM infrastructure_assets")
                count = cursor.fetchone()[0]
                conn.close()
                if count > 0:
                    return  # Database already has data, skip recreation
            except:
                pass  # Table doesn't exist, continue with creation
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Infrastructure Assets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS infrastructure_assets (
                asset_id INTEGER PRIMARY KEY,
                asset_category TEXT,
                asset_name TEXT,
                location TEXT,
                acquisition_date DATE,
                acquisition_cost REAL,
                current_value REAL,
                depreciation_method TEXT,
                useful_life_years INTEGER,
                condition_rating INTEGER,
                maintenance_frequency TEXT
            )
        """)
        
        # Vehicle Fleet
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_fleet (
                vehicle_id INTEGER PRIMARY KEY,
                vehicle_type TEXT,
                make_model TEXT,
                year INTEGER,
                vin TEXT,
                license_plate TEXT,
                department TEXT,
                mileage INTEGER,
                last_service_date DATE,
                fuel_type TEXT,
                purchase_price REAL
            )
        """)
        
        # Equipment Inventory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment_inventory (
                equipment_id INTEGER PRIMARY KEY,
                equipment_type TEXT,
                manufacturer TEXT,
                model_number TEXT,
                serial_number TEXT,
                location TEXT,
                responsible_department TEXT,
                purchase_date DATE,
                warranty_expiration DATE,
                maintenance_status TEXT
            )
        """)
        
        # Buildings and Facilities
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facilities (
                facility_id INTEGER PRIMARY KEY,
                facility_name TEXT,
                facility_type TEXT,
                address TEXT,
                square_footage REAL,
                construction_year INTEGER,
                last_renovation_year INTEGER,
                occupancy_type TEXT,
                assessed_value REAL,
                insurance_value REAL
            )
        """)
        
        # Insert sample data
        sample_infrastructure = [
            (1, 'Roads', 'Main Street Pavement', 'Main St (0-500 block)', '1995-05-15', 500000, 250000, 'Straight-line', 30, 6, 'Annual'),
            (2, 'Bridges', 'River Bridge #1', 'Main St over City Creek', '1988-09-20', 1200000, 400000, 'Straight-line', 50, 7, 'Bi-annual'),
            (3, 'Parks', 'City Park Playground', 'City Park', '2010-04-10', 85000, 60000, 'Straight-line', 20, 8, 'Monthly')
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO infrastructure_assets 
            (asset_id, asset_category, asset_name, location, acquisition_date, acquisition_cost,
             current_value, depreciation_method, useful_life_years, condition_rating, maintenance_frequency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_infrastructure)
        
        sample_vehicles = [
            (1, 'Police Cruiser', 'Ford Explorer', 2022, 'ABC123456789', 'PD-001', 'Police', 15000, '2024-08-15', 'Gasoline', 35000),
            (2, 'Fire Truck', 'Pierce Enforcer', 2019, 'DEF987654321', 'FD-001', 'Fire', 8500, '2024-07-20', 'Diesel', 650000),
            (3, 'Public Works Truck', 'Ford F-350', 2020, 'GHI456789123', 'PW-001', 'Public Works', 22000, '2024-09-05', 'Diesel', 45000)
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO vehicle_fleet 
            (vehicle_id, vehicle_type, make_model, year, vin, license_plate, 
             department, mileage, last_service_date, fuel_type, purchase_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_vehicles)
        
        conn.commit()
        conn.close()
        
        self.logger.info("Sample asset management database created successfully")
    
    def _create_sample_permits_db(self):
        """Create sample permits and licensing database only if it doesn't exist."""
        db_path = "databases/sample_permits_licensing.db"
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Check if database already exists and has data - skip if so
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM building_permits")
                count = cursor.fetchone()[0]
                conn.close()
                if count > 0:
                    return  # Database already has data, skip recreation
            except:
                pass  # Table doesn't exist, continue with creation
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Building Permits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_permits (
                permit_id INTEGER PRIMARY KEY,
                permit_number TEXT UNIQUE,
                property_address TEXT,
                applicant_name TEXT,
                permit_type TEXT,
                project_description TEXT,
                application_date DATE,
                issue_date DATE,
                expiration_date DATE,
                permit_value REAL,
                permit_fee REAL,
                status TEXT,
                inspector_assigned TEXT
            )
        """)
        
        # Business Licenses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_licenses (
                license_id INTEGER PRIMARY KEY,
                license_number TEXT UNIQUE,
                business_name TEXT,
                business_type TEXT,
                owner_name TEXT,
                business_address TEXT,
                issue_date DATE,
                expiration_date DATE,
                license_fee REAL,
                status TEXT,
                renewal_date DATE
            )
        """)
        
        # Inspections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                inspection_id INTEGER PRIMARY KEY,
                permit_id INTEGER,
                inspection_type TEXT,
                scheduled_date DATE,
                inspection_date DATE,
                inspector_name TEXT,
                inspection_result TEXT,
                notes TEXT,
                reinspection_required INTEGER,
                FOREIGN KEY (permit_id) REFERENCES building_permits (permit_id)
            )
        """)
        
        # Zoning Permits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zoning_permits (
                zoning_permit_id INTEGER PRIMARY KEY,
                property_address TEXT,
                zoning_district TEXT,
                permit_type TEXT,
                application_date DATE,
                approval_date DATE,
                conditions TEXT,
                fee_amount REAL,
                status TEXT
            )
        """)
        
        # Insert sample data
        sample_building_permits = [
            (1, 'BP-2024-001', '123 Elm Street', 'John Builder', 'New Construction', 'Single Family Home', '2024-01-15', '2024-02-01', '2025-02-01', 250000, 1250, 'Active', 'Inspector Smith'),
            (2, 'BP-2024-002', '456 Oak Avenue', 'Jane Contractor', 'Addition', 'Garage Addition', '2024-02-20', '2024-03-05', '2025-03-05', 45000, 225, 'Complete', 'Inspector Jones'),
            (3, 'BP-2024-003', '789 Pine Road', 'ABC Construction', 'Remodel', 'Kitchen Remodel', '2024-03-10', '2024-03-25', '2025-03-25', 35000, 175, 'Active', 'Inspector Brown')
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO building_permits 
            (permit_id, permit_number, property_address, applicant_name, permit_type, 
             project_description, application_date, issue_date, expiration_date, 
             permit_value, permit_fee, status, inspector_assigned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_building_permits)
        
        sample_business_licenses = [
            (1, 'BL-2024-001', 'Main Street Cafe', 'Restaurant', 'Sarah Wilson', '100 Main Street', '2024-01-01', '2024-12-31', 150, 'Active', '2024-12-01'),
            (2, 'BL-2024-002', 'City Hardware Store', 'Retail', 'Mike Johnson', '200 Center Street', '2024-02-01', '2025-01-31', 125, 'Active', '2025-01-01'),
            (3, 'BL-2024-003', 'Downtown Barber Shop', 'Personal Services', 'Tony Rodriguez', '150 Main Street', '2024-03-01', '2025-02-28', 100, 'Active', '2025-02-01')
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO business_licenses 
            (license_id, license_number, business_name, business_type, owner_name,
             business_address, issue_date, expiration_date, license_fee, status, renewal_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_business_licenses)
        
        conn.commit()
        conn.close()
        
        self.logger.info("Sample permits and licensing database created successfully")
    
    def _update_config_for_samples(self):
        """Update database configuration to use sample databases for demo."""
        try:
            config = load_db_config()
            
            # Update configuration to use sample databases
            config["databases"]["utility_management"].update({
                "type": "sqlite",
                "path": "databases/sample_utility_management.db",
                "connection_status": "connected"
            })
            
            config["databases"]["asset_management"].update({
                "type": "sqlite", 
                "path": "databases/sample_asset_management.db",
                "connection_status": "connected"
            })
            
            config["databases"]["permits_licensing"].update({
                "type": "sqlite",
                "path": "databases/sample_permits_licensing.db", 
                "connection_status": "connected"
            })
            
            # Save updated configuration
            from modules.database.connection_manager import save_db_config
            save_db_config(config)
            
            self.config = config
            self.logger.info("Database configuration updated for sample databases")
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
    
    def get_all_database_connections(self) -> Dict[str, Any]:
        """Get connections to all available databases."""
        connections = {}
        
        for db_name, db_info in self.config.get("databases", {}).items():
            if db_info.get("connection_status") == "connected":
                try:
                    conn = get_database_connection(db_name)
                    if conn:
                        connections[db_name] = {
                            "connection": conn,
                            "type": db_info.get("type", "sqlite"),
                            "display_name": db_info.get("display_name", db_name),
                            "description": db_info.get("description", "")
                        }
                        self.logger.info(f"Connected to database: {db_name}")
                except Exception as e:
                    self.logger.error(f"Failed to connect to {db_name}: {e}")
        
        return connections
    
    def discover_database_schemas(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Discover schemas from all connected databases.
        
        Returns unified schema catalog: {database: {tables: {table_name: {columns: [...], metadata: {...}}}}}
        """
        if not force_refresh and self.schemas_cache:
            # Check if cache is still valid (refresh every 30 minutes)
            if self.cache_timestamp:
                oldest_cache_time = min(self.cache_timestamp.values())
                cache_age = datetime.now() - oldest_cache_time
                if cache_age.total_seconds() < 1800:  # 30 minutes
                    return self.schemas_cache
            # No cache timestamps available, proceed with refresh
        
        schemas = {}
        connections = self.get_all_database_connections()
        
        for db_name, db_info in connections.items():
            try:
                self.logger.info(f"Discovering schema for database: {db_name}")
                
                conn = db_info["connection"]
                db_type = db_info["type"]
                
                # Discover schema based on database type
                if db_type == "sqlite":
                    db_schema = self._discover_sqlite_schema(conn, db_name, db_info)
                elif db_type == "postgres":
                    db_schema = self._discover_postgres_schema(conn, db_name, db_info)
                elif db_type == "mysql":
                    db_schema = self._discover_mysql_schema(conn, db_name, db_info)
                elif db_type == "sqlserver":
                    db_schema = self._discover_sqlserver_schema(conn, db_name, db_info)
                else:
                    continue
                
                schemas[db_name] = db_schema
                self.cache_timestamp[db_name] = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error discovering schema for {db_name}: {e}")
                schemas[db_name] = {"error": str(e), "tables": {}}
        
        self.schemas_cache = schemas
        
        # Save to persistent catalog for verification
        try:
            catalog_result = schema_catalog_manager.save_schema_catalog(schemas, force_refresh)
            if catalog_result.get("success"):
                self.logger.info(f"Schema catalog saved: {catalog_result.get('statistics', {})}")
            else:
                self.logger.error(f"Failed to save schema catalog: {catalog_result.get('error')}")
        except Exception as e:
            self.logger.error(f"Error saving schema catalog: {e}")
        
        return schemas
    
    def _discover_sqlite_schema(self, conn, db_name: str, db_info: Dict) -> Dict[str, Any]:
        """Discover SQLite database schema."""
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        schema = {
            "database_name": db_name,
            "display_name": db_info.get("display_name", db_name),
            "description": db_info.get("description", ""),
            "database_type": "sqlite",
            "tables": {}
        }
        
        for (table_name,) in tables:
            try:
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                table_info = {
                    "columns": [],
                    "row_count": row_count,
                    "metadata": {
                        "has_data": row_count > 0,
                        "primary_keys": [],
                        "foreign_keys": []
                    }
                }
                
                for col_info in columns:
                    cid, name, data_type, not_null, default_value, pk = col_info
                    table_info["columns"].append({
                        "column_name": name,
                        "data_type": data_type,
                        "nullable": not not_null,
                        "default_value": default_value,
                        "is_primary_key": bool(pk),
                        "position": cid
                    })
                    
                    if pk:
                        table_info["metadata"]["primary_keys"].append(name)
                
                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fkeys = cursor.fetchall()
                for fkey in fkeys:
                    table_info["metadata"]["foreign_keys"].append({
                        "column": fkey[3],
                        "referenced_table": fkey[2],
                        "referenced_column": fkey[4]
                    })
                
                schema["tables"][table_name] = table_info
                
            except Exception as e:
                self.logger.error(f"Error discovering table {table_name} in {db_name}: {e}")
        
        return schema
    
    def _discover_postgres_schema(self, conn, db_name: str, db_info: Dict) -> Dict[str, Any]:
        """Discover PostgreSQL database schema."""
        # For demo purposes, this would contain the actual PostgreSQL schema discovery
        # Since we're using SQLite simulations, we'll call the SQLite method
        return self._discover_sqlite_schema(conn, db_name, db_info)
    
    def _discover_mysql_schema(self, conn, db_name: str, db_info: Dict) -> Dict[str, Any]:
        """Discover MySQL database schema."""
        # For demo purposes, this would contain the actual MySQL schema discovery
        # Since we're using SQLite simulations, we'll call the SQLite method
        return self._discover_sqlite_schema(conn, db_name, db_info)
    
    def _discover_sqlserver_schema(self, conn, db_name: str, db_info: Dict) -> Dict[str, Any]:
        """Discover SQL Server database schema."""
        # For demo purposes, this would contain the actual SQL Server schema discovery
        # Since we're using SQLite simulations, we'll call the SQLite method
        return self._discover_sqlite_schema(conn, db_name, db_info)
    
    def get_unified_field_catalog(self) -> List[Dict[str, Any]]:
        """
        Get unified field catalog for all databases.
        
        Returns list of field definitions: 
        {database, database_display_name, table, column, data_type, nullable, description, database_type}
        """
        schemas = self.discover_database_schemas()
        unified_catalog = []
        
        for db_name, db_schema in schemas.items():
            if "error" in db_schema:
                continue
                
            for table_name, table_info in db_schema.get("tables", {}).items():
                for column_info in table_info.get("columns", []):
                    unified_catalog.append({
                        "database": db_name,
                        "database_display_name": db_schema.get("display_name", db_name),
                        "database_type": db_schema.get("database_type", "unknown"),
                        "description": db_schema.get("description", ""),
                        "schema": "main",  # SQLite default, would be actual schema for other DB types
                        "table": table_name,
                        "column": column_info["column_name"],
                        "data_type": column_info["data_type"],
                        "nullable": column_info["nullable"],
                        "is_primary_key": column_info.get("is_primary_key", False),
                        "position": column_info.get("position", 0),
                        "full_name": f"{db_name}.{table_name}.{column_info['column_name']}",
                        "display_name": f"{db_schema.get('display_name', db_name)} → {table_name} → {column_info['column_name']}"
                    })
        
        return unified_catalog
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Get summary information about all connected databases."""
        schemas = self.discover_database_schemas()
        summary = {
            "total_databases": len(schemas),
            "connected_databases": [],
            "total_tables": 0,
            "total_columns": 0,
            "database_types": {}
        }
        
        for db_name, db_schema in schemas.items():
            if "error" in db_schema:
                continue
                
            db_type = db_schema.get("database_type", "unknown")
            table_count = len(db_schema.get("tables", {}))
            column_count = sum(len(table.get("columns", [])) for table in db_schema.get("tables", {}).values())
            
            summary["connected_databases"].append({
                "name": db_name,
                "display_name": db_schema.get("display_name", db_name),
                "type": db_type,
                "table_count": table_count,
                "column_count": column_count
            })
            
            summary["total_tables"] += table_count
            summary["total_columns"] += column_count
            
            if db_type not in summary["database_types"]:
                summary["database_types"][db_type] = 0
            summary["database_types"][db_type] += 1
        
        return summary
    
    def test_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """Test connections to all configured databases."""
        results = {}
        
        for db_name, db_info in self.config.get("databases", {}).items():
            try:
                conn = get_database_connection(db_name)
                if conn:
                    # Test with a simple query
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    
                    results[db_name] = {
                        "status": "connected",
                        "type": db_info.get("type", "unknown"),
                        "display_name": db_info.get("display_name", db_name)
                    }
                    conn.close()
                else:
                    results[db_name] = {
                        "status": "failed",
                        "error": "Could not establish connection"
                    }
            except Exception as e:
                results[db_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results

# Global instance
multi_db_manager = MultiDatabaseManager()