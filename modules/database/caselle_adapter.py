"""
Caselle SQL Server Adapter
Handles connections to Caselle ERP systems with automatic database discovery
"""

import pyodbc
import pymssql
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.pool import QueuePool
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import streamlit as st
from datetime import datetime
import hashlib
import json
import os

class CaselleServerAdapter:
    """Adapter for connecting to Caselle SQL Server instances"""
    
    # Database function patterns for automatic detection
    DB_PATTERNS = {
        'GL': ['GLTRAN', 'GLACCT', 'GLBUDGET', 'GLJRNL'],
        'AP': ['APINV', 'APVEND', 'APPMT', 'APDIST'],
        'PAYROLL': ['PAYEMP', 'PAYCHK', 'PAYDED', 'PAYTAX'],
        'UTILITY': ['UMBILL', 'UMCUST', 'UMMETER', 'UMREAD'],
        'AR': ['ARCUST', 'ARINV', 'ARPMT', 'ARAGING'],
        'BUDGET': ['BUDGETMASTER', 'BUDGETDETAIL', 'BUDGETREV'],
        'PURCHASING': ['POREQ', 'POORDER', 'POVENDOR', 'POINV'],
        'ASSETS': ['FASSET', 'FDEPRE', 'FLOCATION', 'FMAINT']
    }
    
    def __init__(self, server: str, port: int = 1433, instance: str = None):
        """Initialize Caselle server connection"""
        self.server = server
        self.port = port
        self.instance = instance
        self.connection_string = self._build_connection_string()
        self.engines = {}  # Cache of database engines
        self.metadata_cache = {}
        
    def _build_connection_string(self, database: str = 'master') -> str:
        """Build SQL Server connection string"""
        server_str = f"{self.server},{self.port}" if self.port else self.server
        if self.instance:
            server_str = f"{self.server}\\{self.instance}"
            
        # Using Windows Authentication by default
        # For production, credentials will come from secure storage
        driver = '{ODBC Driver 17 for SQL Server}'
        
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server_str};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
        )
        return conn_str
    
    def test_connection(self, username: str = None, password: str = None) -> Tuple[bool, str]:
        """Test connection to SQL Server"""
        try:
            if username and password:
                # SQL Authentication
                conn_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.server},{self.port};"
                    f"UID={username};"
                    f"PWD={password};"
                )
            else:
                conn_str = self.connection_string
                
            with pyodbc.connect(conn_str, timeout=5) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                return True, f"Connected successfully. SQL Server version: {version[:50]}..."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def discover_databases(self, username: str = None, password: str = None) -> List[Dict[str, Any]]:
        """Discover all databases on the server"""
        databases = []
        try:
            conn_str = self._get_auth_connection_string('master', username, password)
            
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                
                # Get all databases
                cursor.execute("""
                    SELECT 
                        name,
                        database_id,
                        create_date,
                        state_desc,
                        recovery_model_desc,
                        compatibility_level
                    FROM sys.databases
                    WHERE state = 0  -- Online databases only
                    ORDER BY name
                """)
                
                for row in cursor.fetchall():
                    db_info = {
                        'name': row[0],
                        'id': row[1],
                        'created': row[2].isoformat() if row[2] else None,
                        'state': row[3],
                        'recovery_model': row[4],
                        'compatibility': row[5],
                        'detected_function': None,
                        'tables': []
                    }
                    
                    # Try to detect function based on database name or contents
                    db_info['detected_function'] = self._detect_database_function(
                        db_info['name'], conn_str
                    )
                    
                    databases.append(db_info)
                    
        except Exception as e:
            st.error(f"Failed to discover databases: {str(e)}")
            
        return databases
    
    def _detect_database_function(self, db_name: str, base_conn_str: str) -> Optional[str]:
        """Detect the function of a database based on its tables"""
        try:
            # Build connection string for specific database
            conn_str = base_conn_str.replace('DATABASE=master', f'DATABASE={db_name}')
            
            with pyodbc.connect(conn_str, timeout=5) as conn:
                cursor = conn.cursor()
                
                # Get table names
                cursor.execute("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE'
                """)
                
                tables = [row[0].upper() for row in cursor.fetchall()]
                
                # Check against patterns
                for function, patterns in self.DB_PATTERNS.items():
                    matches = sum(1 for pattern in patterns if pattern in tables)
                    if matches >= 2:  # At least 2 matching tables
                        return function
                        
        except:
            pass  # Silently fail for inaccessible databases
            
        # Try to infer from database name
        db_upper = db_name.upper()
        if 'GL' in db_upper or 'GENERAL' in db_upper:
            return 'GL'
        elif 'AP' in db_upper or 'PAYABLE' in db_upper:
            return 'AP'
        elif 'PAY' in db_upper or 'PAYROLL' in db_upper:
            return 'PAYROLL'
        elif 'UTIL' in db_upper or 'BILLING' in db_upper:
            return 'UTILITY'
        elif 'AR' in db_upper or 'RECEIVABLE' in db_upper:
            return 'AR'
            
        return None
    
    def _get_auth_connection_string(self, database: str, username: str = None, password: str = None) -> str:
        """Get connection string with proper authentication"""
        if username and password:
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server},{self.port};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
            )
        else:
            return self._build_connection_string(database)
    
    def get_database_schema(self, database: str, username: str = None, password: str = None) -> Dict:
        """Get detailed schema information for a database"""
        schema_info = {
            'tables': [],
            'views': [],
            'stored_procedures': [],
            'row_counts': {}
        }
        
        try:
            conn_str = self._get_auth_connection_string(database, username, password)
            
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                
                # Get tables with row counts
                cursor.execute("""
                    SELECT 
                        t.TABLE_NAME,
                        p.rows
                    FROM INFORMATION_SCHEMA.TABLES t
                    LEFT JOIN sys.partitions p ON p.object_id = OBJECT_ID(t.TABLE_NAME)
                    WHERE t.TABLE_TYPE = 'BASE TABLE'
                    AND p.index_id IN (0, 1)
                    ORDER BY t.TABLE_NAME
                """)
                
                for row in cursor.fetchall():
                    schema_info['tables'].append(row[0])
                    schema_info['row_counts'][row[0]] = row[1] or 0
                
                # Get views
                cursor.execute("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.VIEWS
                    ORDER BY TABLE_NAME
                """)
                
                schema_info['views'] = [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            st.error(f"Failed to get schema for {database}: {str(e)}")
            
        return schema_info
    
    def create_engine(self, database: str, username: str = None, password: str = None) -> Any:
        """Create SQLAlchemy engine for a specific database"""
        cache_key = f"{self.server}:{self.port}:{database}"
        
        if cache_key not in self.engines:
            # Build connection URL for SQLAlchemy
            if username and password:
                conn_url = f"mssql+pymssql://{username}:{password}@{self.server}:{self.port}/{database}"
            else:
                # For Windows Authentication with SQLAlchemy
                conn_url = f"mssql+pyodbc://@{self.server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
            
            # Create engine with connection pooling
            engine = create_engine(
                conn_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                echo=False
            )
            
            self.engines[cache_key] = engine
            
        return self.engines[cache_key]
    
    def execute_query(self, database: str, query: str, username: str = None, password: str = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        engine = self.create_engine(database, username, password)
        
        try:
            df = pd.read_sql_query(query, engine)
            return df
        except Exception as e:
            st.error(f"Query execution failed: {str(e)}")
            return pd.DataFrame()
    
    def get_sample_data(self, database: str, table: str, limit: int = 10, 
                       username: str = None, password: str = None) -> pd.DataFrame:
        """Get sample data from a table"""
        query = f"SELECT TOP {limit} * FROM {table}"
        return self.execute_query(database, query, username, password)
    
    def dispose_all_engines(self):
        """Dispose all cached engines"""
        for engine in self.engines.values():
            engine.dispose()
        self.engines.clear()


class CaselleDatabaseSet:
    """Represents a set of related databases for a city/organization"""
    
    def __init__(self, name: str, server_adapter: CaselleServerAdapter):
        self.name = name
        self.server = server_adapter
        self.databases = {
            'GL': None,
            'AP': None,
            'PAYROLL': None,
            'UTILITY': None,
            'AR': None,
            'BUDGET': None,
            'PURCHASING': None,
            'ASSETS': None
        }
        self.is_live = False
        self.created_at = datetime.now()
        self.last_accessed = None
    
    def assign_database(self, function: str, database_name: str):
        """Assign a database to a function"""
        if function in self.databases:
            self.databases[function] = database_name
            
    def get_connection(self, function: str, username: str = None, password: str = None):
        """Get connection for a specific function"""
        db_name = self.databases.get(function)
        if db_name:
            return self.server.create_engine(db_name, username, password)
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'server': self.server.server,
            'port': self.server.port,
            'instance': self.server.instance,
            'databases': self.databases,
            'is_live': self.is_live,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }