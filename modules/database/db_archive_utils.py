"""
Database Archive Utilities

This module provides utility functions for working with database archive formats:
- .zip archives containing .db files
- .bak SQL Server backup files

These utilities enable importing and extracting database files from various formats
for use in the GovSight Financial Analyzer.
"""

import os
import zipfile
import tempfile
import shutil
import sqlite3
import streamlit as st
from typing import List, Tuple, Optional, Union

# Define temporary directory for extraction
TEMP_DIR = "temp_extracts"

def ensure_temp_dir():
    """Ensure the temporary directory exists"""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

def extract_sqlite_from_zip(zip_file_path: str) -> List[str]:
    """
    Extract SQLite database files (.db) from a zip archive
    
    Args:
        zip_file_path (str): Path to the .zip file
        
    Returns:
        List[str]: List of extracted .db file paths
    """
    ensure_temp_dir()
    extracted_files = []
    
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Get list of .db files in the archive
            db_files = [f for f in zip_ref.namelist() if f.lower().endswith('.db')]
            
            if not db_files:
                st.warning(f"No SQLite database (.db) files found in {zip_file_path}")
                return []
            
            # Extract the .db files
            for db_file in db_files:
                # Get just the filename without any path
                db_filename = os.path.basename(db_file)
                # Create a path in our temporary directory
                output_path = os.path.join(TEMP_DIR, db_filename)
                
                # Extract the file
                with zip_ref.open(db_file) as source, open(output_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                
                # Verify it's a valid SQLite database
                if is_valid_sqlite_db(output_path):
                    extracted_files.append(output_path)
                else:
                    os.remove(output_path)  # Remove invalid file
                    st.warning(f"{db_filename} is not a valid SQLite database")
        
        return extracted_files
    
    except Exception as e:
        st.error(f"Error extracting from zip file: {e}")
        return []

def convert_bak_to_sqlite(bak_file_path: str) -> Optional[str]:
    """
    Convert a SQL Server .bak file to SQLite database
    Note: This requires additional setup with SQL Server tools
    
    Args:
        bak_file_path (str): Path to the .bak file
        
    Returns:
        Optional[str]: Path to the converted SQLite database or None if conversion failed
    """
    # SQL Server .bak handling needs external tools that may not be available in all environments
    # This is a placeholder - full implementation would require SQL Server utilities
    st.warning("SQL Server .bak file conversion is not fully implemented yet.")
    st.info("Support for .bak files requires SQL Server tools. Please extract the data first and provide as .db file.")
    return None

def is_valid_sqlite_db(file_path: str) -> bool:
    """
    Check if a file is a valid SQLite database
    
    Args:
        file_path (str): Path to the file to check
        
    Returns:
        bool: True if valid SQLite database, False otherwise
    """
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return len(tables) > 0  # Valid SQLite DB should have at least one table
    except sqlite3.Error:
        return False
    except Exception:
        return False

def get_tables_from_db(db_path: str) -> List[str]:
    """
    Get a list of tables in a SQLite database
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        List[str]: List of table names in the database
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        st.error(f"Error getting tables from database: {e}")
        return []

def cleanup_temp_files():
    """Remove temporary extracted files"""
    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR)  # Recreate empty directory
        except Exception as e:
            st.error(f"Error cleaning up temporary files: {e}")