"""
PBB Data Store - Persistent storage for multi-sheet budget workbooks
Uses SQLite for reliable data persistence across Streamlit reruns
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class PBBDataStore:
    """Persistent storage for PBB sheets and configurations"""
    
    def __init__(self, db_path: str = "production_data/pbb_workbooks.db"):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sheets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pbb_sheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workbook_id TEXT NOT NULL,
                sheet_name TEXT NOT NULL,
                sheet_order INTEGER DEFAULT 0,
                is_production BOOLEAN DEFAULT 0,
                is_locked BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workbook_id, sheet_name)
            )
        """)
        
        # Grid data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pbb_grid_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id INTEGER NOT NULL,
                row_data TEXT NOT NULL,
                row_order INTEGER DEFAULT 0,
                data_source TEXT DEFAULT 'Manual Entry',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sheet_id) REFERENCES pbb_sheets(id) ON DELETE CASCADE
            )
        """)
        
        # Change history table for audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pbb_change_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id INTEGER NOT NULL,
                row_id INTEGER,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sheet_id) REFERENCES pbb_sheets(id) ON DELETE CASCADE
            )
        """)
        
        # GL mappings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pbb_gl_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department TEXT NOT NULL,
                gl_account TEXT NOT NULL,
                description TEXT,
                UNIQUE(department, gl_account)
            )
        """)
        
        # Benefit packages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pbb_benefit_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT UNIQUE NOT NULL,
                benefits_rate REAL,
                health_cost REAL,
                pension_rate REAL,
                dental_cost REAL,
                package_config TEXT
            )
        """)
        
        # Step/Grade matrix table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pbb_step_grade_matrix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grade TEXT NOT NULL,
                step INTEGER NOT NULL,
                salary REAL NOT NULL,
                UNIQUE(grade, step)
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize default data
        self._init_default_data()
    
    def _init_default_data(self):
        """Initialize default GL mappings, benefit packages, and step/grade matrix"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if we need to initialize
        cursor.execute("SELECT COUNT(*) FROM pbb_gl_mappings")
        if cursor.fetchone()[0] == 0:
            # Default GL mappings
            gl_mappings = [
                ("Finance", "101-1000-5100", "Finance Salaries & Wages"),
                ("Police", "101-2000-5100", "Police Salaries"),
                ("Fire", "101-3000-5100", "Fire Salaries"),
                ("Public Works", "101-4000-5100", "Public Works Salaries")
            ]
            cursor.executemany(
                "INSERT INTO pbb_gl_mappings (department, gl_account, description) VALUES (?, ?, ?)",
                gl_mappings
            )
        
        # Check benefit packages
        cursor.execute("SELECT COUNT(*) FROM pbb_benefit_packages")
        if cursor.fetchone()[0] == 0:
            packages = [
                ("Full-Time Union", 35.0, 18000, 0.28, 1200, 
                 json.dumps({"type": "union", "fica": True})),
                ("Full-Time Non-Union", 30.0, 15000, 0.20, 1000,
                 json.dumps({"type": "non_union", "fica": True})),
                ("Part-Time", 12.0, 0, 0.12, 0,
                 json.dumps({"type": "part_time", "fica": True}))
            ]
            cursor.executemany(
                """INSERT INTO pbb_benefit_packages 
                   (package_name, benefits_rate, health_cost, pension_rate, dental_cost, package_config) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                packages
            )
        
        # Check step/grade matrix
        cursor.execute("SELECT COUNT(*) FROM pbb_step_grade_matrix")
        if cursor.fetchone()[0] == 0:
            matrix = []
            grades = {
                'PO-1': [45000, 47000, 49000, 51000, 53000],
                'PO-2': [50000, 52500, 55000, 57500, 60000],
                'PO-3': [60000, 63000, 66000, 69000, 72000],
                'FF-1': [48000, 50000, 52000, 54000, 56000],
                'FF-2': [55000, 57500, 60000, 62500, 65000],
                'ADM-1': [55000, 58000, 61000, 64000, 67000],
                'ADM-2': [70000, 74000, 78000, 82000, 86000]
            }
            for grade, salaries in grades.items():
                for step, salary in enumerate(salaries, 1):
                    matrix.append((grade, step, salary))
            
            cursor.executemany(
                "INSERT INTO pbb_step_grade_matrix (grade, step, salary) VALUES (?, ?, ?)",
                matrix
            )
        
        conn.commit()
        conn.close()
    
    def create_workbook(self, workbook_id: str = "default") -> int:
        """Create a new workbook with default Production sheet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create default production sheet
        cursor.execute("""
            INSERT OR IGNORE INTO pbb_sheets (workbook_id, sheet_name, sheet_order, is_production)
            VALUES (?, ?, ?, ?)
        """, (workbook_id, "Sheet 1 (Production)", 0, 1))
        
        sheet_id = cursor.lastrowid or 0
        conn.commit()
        conn.close()
        
        return sheet_id
    
    def get_or_create_workbook(self, workbook_id: str = "default") -> List[Dict]:
        """Get workbook sheets or create if doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, sheet_name, sheet_order, is_production, is_locked
            FROM pbb_sheets
            WHERE workbook_id = ?
            ORDER BY sheet_order, id
        """, (workbook_id,))
        
        sheets = cursor.fetchall()
        
        if not sheets:
            # Create default workbook
            self.create_workbook(workbook_id)
            cursor.execute("""
                SELECT id, sheet_name, sheet_order, is_production, is_locked
                FROM pbb_sheets
                WHERE workbook_id = ?
                ORDER BY sheet_order, id
            """, (workbook_id,))
            sheets = cursor.fetchall()
        
        conn.close()
        
        return [
            {
                "id": s[0],
                "name": s[1],
                "order": s[2],
                "is_production": bool(s[3]),
                "is_locked": bool(s[4])
            }
            for s in sheets
        ]
    
    def add_sheet(self, workbook_id: str, sheet_name: str) -> int:
        """Add a new sheet to workbook"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get max order
        cursor.execute("""
            SELECT COALESCE(MAX(sheet_order), -1) + 1
            FROM pbb_sheets
            WHERE workbook_id = ?
        """, (workbook_id,))
        
        next_order = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            INSERT INTO pbb_sheets (workbook_id, sheet_name, sheet_order)
            VALUES (?, ?, ?)
        """, (workbook_id, sheet_name, next_order))
        
        sheet_id = cursor.lastrowid or 0
        conn.commit()
        conn.close()
        
        return sheet_id
    
    def delete_sheet(self, sheet_id: int):
        """Delete a sheet and all its data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete grid data (cascade will handle it, but explicit is clear)
        cursor.execute("DELETE FROM pbb_grid_data WHERE sheet_id = ?", (sheet_id,))
        cursor.execute("DELETE FROM pbb_change_history WHERE sheet_id = ?", (sheet_id,))
        cursor.execute("DELETE FROM pbb_sheets WHERE id = ?", (sheet_id,))
        
        conn.commit()
        conn.close()
    
    def save_sheet_data(self, sheet_id: int, grid_data: List[Dict], user: str = "system"):
        """Save all grid data for a sheet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete existing data for this sheet
        cursor.execute("DELETE FROM pbb_grid_data WHERE sheet_id = ?", (sheet_id,))
        
        # Insert new data
        for order, row in enumerate(grid_data):
            cursor.execute("""
                INSERT INTO pbb_grid_data (sheet_id, row_data, row_order, data_source)
                VALUES (?, ?, ?, ?)
            """, (sheet_id, json.dumps(row), order, row.get('data_source', 'Manual Entry')))
        
        # Update sheet timestamp
        cursor.execute("""
            UPDATE pbb_sheets
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (sheet_id,))
        
        conn.commit()
        conn.close()
    
    def load_sheet_data(self, sheet_id: int) -> List[Dict]:
        """Load all grid data for a sheet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT row_data
            FROM pbb_grid_data
            WHERE sheet_id = ?
            ORDER BY row_order
        """, (sheet_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [json.loads(row[0]) for row in rows]
    
    def get_gl_accounts(self) -> List[str]:
        """Get list of GL accounts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT gl_account FROM pbb_gl_mappings ORDER BY gl_account")
        accounts = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return accounts
    
    def get_benefit_packages(self) -> Dict[str, Dict]:
        """Get benefit package configurations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT package_name, benefits_rate, health_cost, pension_rate, dental_cost
            FROM pbb_benefit_packages
        """)
        
        packages = {}
        for row in cursor.fetchall():
            packages[row[0]] = {
                "benefits_rate": row[1],
                "health_cost": row[2],
                "pension_rate": row[3],
                "dental_cost": row[4]
            }
        
        conn.close()
        return packages
    
    def get_step_grade_salary(self, grade: str, step: int) -> Optional[float]:
        """Get salary for grade/step combination"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT salary FROM pbb_step_grade_matrix
            WHERE grade = ? AND step = ?
        """, (grade, step))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def log_change(self, sheet_id: int, row_id: Optional[int], field_name: str, 
                   old_value: Any, new_value: Any, user: str = "system"):
        """Log a change for audit trail"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pbb_change_history 
            (sheet_id, row_id, field_name, old_value, new_value, changed_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sheet_id, row_id, field_name, str(old_value), str(new_value), user))
        
        conn.commit()
        conn.close()
    
    def get_change_history(self, sheet_id: int, limit: int = 100) -> List[Dict]:
        """Get change history for a sheet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT field_name, old_value, new_value, changed_by, changed_at
            FROM pbb_change_history
            WHERE sheet_id = ?
            ORDER BY changed_at DESC
            LIMIT ?
        """, (sheet_id, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "field": row[0],
                "old_value": row[1],
                "new_value": row[2],
                "user": row[3],
                "timestamp": row[4]
            })
        
        conn.close()
        return history
