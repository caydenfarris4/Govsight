"""
GovSight SQL Database Connection Module

This module provides a flexible way to connect to various SQL database systems:
- SQLite (default, file-based)
- PostgreSQL
- MySQL/MariaDB
- Microsoft SQL Server

The module handles connection pooling, error handling, and provides utility functions
for common database operations.

Usage example:
    from sql_connection import SQLDatabase
    
    # Connect to SQLite
    db = SQLDatabase(dbtype='sqlite', database_path='my_database.db')
    
    # Connect to PostgreSQL
    db = SQLDatabase(
        dbtype='postgresql',
        host='localhost',
        port=5432,
        user='username',
        password='password',
        database='mydatabase'
    )
    
    # Execute a query
    results = db.execute_query("SELECT * FROM departments")
"""

import os
import json
import logging
from typing import Optional, Dict, List, Union, Any, Tuple
import sqlite3
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sql_connection')

# Load environment variables
load_dotenv()

class SQLDatabase:
    """
    A flexible SQL database connection class that supports multiple database types.
    """
    
    def __init__(
        self,
        dbtype: str = 'sqlite',
        database_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        connection_string: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        config_file: Optional[str] = None,
        config_section: Optional[str] = None,
        env_prefix: Optional[str] = None,
    ):
        """
        Initialize a database connection.
        
        Args:
            dbtype: Database type ('sqlite', 'postgresql', 'mysql', 'mssql')
            database_path: Path to SQLite database file (for sqlite only)
            host: Database server hostname or IP
            port: Database server port
            user: Database username
            password: Database password
            database: Database name
            connection_string: Direct connection string (overrides other connection parameters)
            pool_size: Connection pool size
            max_overflow: Maximum number of connections to overflow
            pool_timeout: Timeout for getting a connection from the pool
            pool_recycle: Number of seconds after which a connection is recycled
            config_file: Path to a JSON config file with connection details
            config_section: Section in config file to use
            env_prefix: Prefix for environment variables
        """
        self.dbtype = dbtype.lower()
        self.database_path = database_path
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.engine = None
        self.inspector = None
        
        # Load connection details from config file if provided
        if config_file and config_section:
            self._load_from_config(config_file, config_section)
        
        # Load connection details from environment variables if prefix provided
        if env_prefix:
            self._load_from_env(env_prefix)
            
        # Create the database engine
        self._create_engine()
        
    def _load_from_config(self, config_file: str, section: str) -> None:
        """Load database connection details from a JSON config file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            if section in config:
                conn_config = config[section]
                self.dbtype = conn_config.get('dbtype', self.dbtype)
                self.database_path = conn_config.get('database_path', self.database_path)
                self.host = conn_config.get('host', self.host)
                self.port = conn_config.get('port', self.port)
                self.user = conn_config.get('user', self.user)
                self.password = conn_config.get('password', self.password)
                self.database = conn_config.get('database', self.database)
                self.connection_string = conn_config.get('connection_string', self.connection_string)
            else:
                logger.warning(f"Section {section} not found in config file {config_file}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading config file: {e}")
            
    def _load_from_env(self, prefix: str) -> None:
        """Load database connection details from environment variables."""
        prefix = prefix.upper() + '_'
        self.dbtype = os.environ.get(f"{prefix}DBTYPE", self.dbtype)
        self.database_path = os.environ.get(f"{prefix}DATABASE_PATH", self.database_path)
        self.host = os.environ.get(f"{prefix}HOST", self.host)
        self.port = os.environ.get(f"{prefix}PORT", self.port)
        if self.port and isinstance(self.port, str):
            try:
                self.port = int(self.port)
            except ValueError:
                logger.warning(f"Invalid port number: {self.port}")
                self.port = None
        self.user = os.environ.get(f"{prefix}USER", self.user)
        self.password = os.environ.get(f"{prefix}PASSWORD", self.password)
        self.database = os.environ.get(f"{prefix}DATABASE", self.database)
        self.connection_string = os.environ.get(f"{prefix}CONNECTION_STRING", self.connection_string)
            
    def _create_engine(self) -> None:
        """Create a SQLAlchemy engine based on the database type and connection parameters."""
        try:
            if self.connection_string:
                # Use direct connection string if provided
                conn_url = self.connection_string
            else:
                # Build connection URL based on database type
                if self.dbtype == 'sqlite':
                    # Default to in-memory database if no path provided
                    db_path = self.database_path or 'budget.db'
                    conn_url = f"sqlite:///{db_path}"
                    
                elif self.dbtype == 'postgresql':
                    port = self.port or 5432
                    conn_url = f"postgresql://{self.user}:{self.password}@{self.host}:{port}/{self.database}"
                    
                elif self.dbtype == 'mysql':
                    port = self.port or 3306
                    conn_url = f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{port}/{self.database}"
                    
                elif self.dbtype == 'mssql':
                    port = self.port or 1433
                    conn_url = f"mssql+pymssql://{self.user}:{self.password}@{self.host}:{port}/{self.database}"
                    
                else:
                    raise ValueError(f"Unsupported database type: {self.dbtype}")
            
            # Create the engine with connection pooling
            self.engine = create_engine(
                conn_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle
            )
            
            # Create an inspector for schema introspection
            self.inspector = inspect(self.engine)
            
            logger.info(f"Successfully created database engine for {self.dbtype}")
            
        except Exception as e:
            logger.error(f"Error creating database engine: {e}")
            raise
            
    def execute_query(
        self, 
        query: str, 
        params: Union[Dict[str, Any], List[Any], Tuple[Any, ...], None] = None,
        fetchall: bool = True
    ) -> Union[List[Dict[str, Any]], None]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetchall: Whether to fetch all results or not
            
        Returns:
            List of dictionaries containing query results if fetchall=True,
            otherwise None
        """
        try:
            with self.engine.connect() as connection:
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))
                    
                if fetchall:
                    # Convert to list of dictionaries
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in result.fetchall()]
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error executing query: {e}")
            return f"Error: {str(e)}"
            
    def execute_file(self, file_path: str) -> None:
        """
        Execute SQL statements from a file.
        
        Args:
            file_path: Path to the SQL file
        """
        try:
            with open(file_path, 'r') as f:
                sql = f.read()
                
            # Split on semicolons but ignore those in quotes
            import re
            statements = re.split(r';(?=(?:[^\'"]|\'[^\']*\'|"[^"]*")*$)', sql)
            
            with self.engine.begin() as connection:
                for statement in statements:
                    if statement.strip():
                        connection.execute(text(statement))
                        
            logger.info(f"Successfully executed SQL file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error executing SQL file: {e}")
            raise
            
    def get_tables(self) -> List[str]:
        """Get a list of all tables in the database."""
        try:
            return self.inspector.get_table_names()
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
            
    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of dictionaries with column information
        """
        try:
            return self.inspector.get_columns(table_name)
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
            return []
            
    def check_connection(self) -> bool:
        """Check if the database connection is working."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
            
    def close(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

# Convenience functions for working with the default database
_default_db = None

def get_db(
    dbtype: str = 'sqlite', 
    database_path: Optional[str] = None,
    **kwargs
) -> SQLDatabase:
    """
    Get a database connection. Creates a new one if none exists.
    
    Args:
        dbtype: Database type
        database_path: Path to SQLite database file
        **kwargs: Additional connection parameters
        
    Returns:
        SQLDatabase instance
    """
    global _default_db
    if _default_db is None:
        _default_db = SQLDatabase(dbtype=dbtype, database_path=database_path, **kwargs)
    return _default_db

def execute_query(
    query: str, 
    params: Union[Dict[str, Any], List[Any], Tuple[Any, ...], None] = None,
    fetchall: bool = True,
    dbtype: str = 'sqlite',
    database_path: Optional[str] = None,
    **kwargs
) -> Union[List[Dict[str, Any]], None]:
    """
    Execute a SQL query using the default database.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        fetchall: Whether to fetch all results
        dbtype: Database type
        database_path: Path to SQLite database file
        **kwargs: Additional connection parameters
        
    Returns:
        Query results
    """
    db = get_db(dbtype=dbtype, database_path=database_path, **kwargs)
    return db.execute_query(query, params, fetchall)

def close_db() -> None:
    """Close the default database connection."""
    global _default_db
    if _default_db:
        _default_db.close()
        _default_db = None

# Example usage
if __name__ == "__main__":
    # Example: SQLite connection
    db_sqlite = SQLDatabase(dbtype='sqlite', database_path='example.db')
    
    # Create a test table
    db_sqlite.execute_query("""
    CREATE TABLE IF NOT EXISTS test (
        id INTEGER PRIMARY KEY,
        name TEXT,
        value REAL
    )
    """)
    
    # Insert data
    db_sqlite.execute_query(
        "INSERT INTO test (name, value) VALUES (:name, :value)",
        {"name": "Test Item", "value": 123.45}
    )
    
    # Query data
    results = db_sqlite.execute_query("SELECT * FROM test")
    print("SQLite results:", results)
    
    # Example: PostgreSQL connection (commented out)
    """
    db_pg = SQLDatabase(
        dbtype='postgresql',
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='testdb'
    )
    
    results = db_pg.execute_query("SELECT * FROM departments")
    print("PostgreSQL results:", results)
    """
    
    # Close connections
    db_sqlite.close()