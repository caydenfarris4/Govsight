"""
Unit tests for secure database operations
Tests the SecureDatabase class and related functions
"""

import pytest
import sqlite3
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.security.secure_db_operations import (
    SecureDatabase,
    secure_bulk_insert,
    secure_data_export
)

class TestSecureDatabase:
    """Test SecureDatabase class"""
    
    def setup_method(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        
        # Initialize database with test data
        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE DepartmentPerformance (
                Department TEXT,
                Budget REAL,
                Actual REAL,
                Organization TEXT
            )
        """)
        
        cursor.execute("""
            INSERT INTO DepartmentPerformance 
            VALUES ('Police', 1000000, 950000, 'CityA')
        """)
        
        cursor.execute("""
            INSERT INTO DepartmentPerformance 
            VALUES ('Fire', 800000, 750000, 'CityA')
        """)
        
        conn.commit()
        conn.close()
    
    def teardown_method(self):
        """Clean up test database"""
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)
    
    def test_secure_database_context_manager(self):
        """Test SecureDatabase as context manager"""
        with SecureDatabase(self.test_db.name) as db:
            assert db.conn is not None
            assert isinstance(db.conn, sqlite3.Connection)
    
    def test_execute_secure_query_select(self):
        """Test secure query execution for SELECT"""
        with SecureDatabase(self.test_db.name) as db:
            query = "SELECT Department, Budget FROM DepartmentPerformance WHERE Organization = ?"
            result = db.execute_secure_query(query, ('CityA',), fetchall=True)
            
            assert result is not None
            assert len(result) == 2
            assert result[0]['Department'] in ['Police', 'Fire']
    
    def test_execute_secure_query_single_result(self):
        """Test secure query execution for single result"""
        with SecureDatabase(self.test_db.name) as db:
            query = "SELECT Department, Budget FROM DepartmentPerformance WHERE Department = ?"
            result = db.execute_secure_query(query, ('Police',), fetchall=False)
            
            assert result is not None
            assert result['Department'] == 'Police'
            assert result['Budget'] == 1000000
    
    def test_get_department_data(self):
        """Test getting department data securely"""
        with SecureDatabase(self.test_db.name) as db:
            result = db.get_department_data('CityA')
            
            assert result is not None
            assert len(result) == 2
            # Should be ordered by Budget DESC
            assert result[0]['Budget'] >= result[1]['Budget']
    
    def test_check_table_exists(self):
        """Test table existence checking"""
        with SecureDatabase(self.test_db.name) as db:
            assert db.check_table_exists('DepartmentPerformance') is True
            assert db.check_table_exists('NonExistentTable') is False
    
    def test_check_table_exists_invalid_name(self):
        """Test table existence check with invalid name"""
        with SecureDatabase(self.test_db.name) as db:
            # Should return False for invalid table names
            assert db.check_table_exists("'; DROP TABLE users; --") is False
    
    def test_get_table_columns(self):
        """Test getting table columns"""
        with SecureDatabase(self.test_db.name) as db:
            columns = db.get_table_columns('DepartmentPerformance')
            
            expected_columns = ['Department', 'Budget', 'Actual', 'Organization']
            assert set(columns) == set(expected_columns)
    
    def test_get_table_columns_invalid_table(self):
        """Test getting columns for invalid table"""
        with SecureDatabase(self.test_db.name) as db:
            columns = db.get_table_columns('NonExistentTable')
            assert columns == []
    
    def test_execute_secure_query_sql_error(self):
        """Test handling of SQL errors"""
        with SecureDatabase(self.test_db.name) as db:
            # Invalid SQL should return None
            result = db.execute_secure_query("SELECT * FROM NonExistentTable", ())
            assert result is None


class TestSecureBulkInsert:
    """Test secure bulk insert operations"""
    
    def setup_method(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        
        # Create empty table
        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE TestTable (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def teardown_method(self):
        """Clean up test database"""
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)
    
    def test_secure_bulk_insert_success(self):
        """Test successful bulk insert"""
        data = [
            {'id': 1, 'name': 'Item1', 'value': 100.0},
            {'id': 2, 'name': 'Item2', 'value': 200.0}
        ]
        
        result = secure_bulk_insert(self.test_db.name, 'TestTable', data)
        assert result is True
        
        # Verify data was inserted
        with SecureDatabase(self.test_db.name) as db:
            query_result = db.execute_secure_query("SELECT COUNT(*) as count FROM TestTable", ())
            assert query_result[0]['count'] == 2
    
    def test_secure_bulk_insert_invalid_table(self):
        """Test bulk insert with invalid table name"""
        data = [{'id': 1, 'name': 'Item1', 'value': 100.0}]
        
        result = secure_bulk_insert(self.test_db.name, "'; DROP TABLE users; --", data)
        assert result is False
    
    def test_secure_bulk_insert_empty_data(self):
        """Test bulk insert with empty data"""
        result = secure_bulk_insert(self.test_db.name, 'TestTable', [])
        assert result is True  # Empty insert should succeed


class TestSecureDataExport:
    """Test secure data export functionality"""
    
    def setup_method(self):
        """Set up test database"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        
        # Create test table with data
        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE ExportTable (
                id INTEGER,
                department TEXT,
                budget REAL,
                organization TEXT
            )
        """)
        
        test_data = [
            (1, 'Police', 1000000, 'CityA'),
            (2, 'Fire', 800000, 'CityA'),
            (3, 'Parks', 500000, 'CityB')
        ]
        
        cursor.executemany("INSERT INTO ExportTable VALUES (?, ?, ?, ?)", test_data)
        conn.commit()
        conn.close()
    
    def teardown_method(self):
        """Clean up test database"""
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)
    
    def test_secure_data_export_all(self):
        """Test exporting all data"""
        df = secure_data_export(self.test_db.name, 'ExportTable')
        
        assert df is not None
        assert len(df) == 3
        assert set(df.columns) == {'id', 'department', 'budget', 'organization'}
    
    def test_secure_data_export_with_filters(self):
        """Test exporting data with filters"""
        filters = {'organization': 'CityA'}
        df = secure_data_export(self.test_db.name, 'ExportTable', filters=filters)
        
        assert df is not None
        assert len(df) == 2
        assert all(df['organization'] == 'CityA')
    
    def test_secure_data_export_specific_columns(self):
        """Test exporting specific columns"""
        columns = ['department', 'budget']
        df = secure_data_export(self.test_db.name, 'ExportTable', columns=columns)
        
        assert df is not None
        assert set(df.columns) == {'department', 'budget'}
        assert len(df) == 3
    
    def test_secure_data_export_invalid_table(self):
        """Test export with invalid table name"""
        df = secure_data_export(self.test_db.name, "'; DROP TABLE users; --")
        assert df is None
    
    def test_secure_data_export_nonexistent_table(self):
        """Test export with non-existent table"""
        df = secure_data_export(self.test_db.name, 'NonExistentTable')
        assert df is None


if __name__ == "__main__":
    # Run the tests
    pytest.main(["-v", __file__])