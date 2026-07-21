"""
Report Archive
Persistent storage for imported reports enabling multi-year historical analysis
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)

class ReportArchive:
    """
    SQLite-based archive for storing imported financial reports
    
    Features:
    - Store all imported data with full metadata
    - Query historical data across years
    - Support trend analysis over time
    - Maintain data integrity with source tracking
    """
    
    def __init__(
        self,
        database_path: str = "databases/report_archive.db",
        municipality_id: str = "default"
    ):
        self.database_path = Path(database_path)
        self.municipality_id = municipality_id
        
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.database_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize archive database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                municipality_id TEXT NOT NULL,
                import_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source_file TEXT,
                report_type TEXT,
                fiscal_year INTEGER,
                fiscal_period TEXT,
                record_count INTEGER,
                status TEXT DEFAULT 'completed',
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS general_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                fiscal_year INTEGER,
                fiscal_period TEXT,
                transaction_date DATE,
                account_number TEXT,
                account_description TEXT,
                fund TEXT,
                department TEXT,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                description TEXT,
                reference TEXT,
                vendor TEXT,
                check_number TEXT,
                source_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                fiscal_year INTEGER,
                account_number TEXT,
                account_description TEXT,
                fund TEXT,
                department TEXT,
                original_budget REAL DEFAULT 0,
                revised_budget REAL DEFAULT 0,
                actual_ytd REAL DEFAULT 0,
                encumbered REAL DEFAULT 0,
                available REAL DEFAULT 0,
                source_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payroll_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                fiscal_year INTEGER,
                pay_period TEXT,
                pay_date DATE,
                employee_id TEXT,
                employee_name TEXT,
                department TEXT,
                position TEXT,
                hours_regular REAL DEFAULT 0,
                hours_overtime REAL DEFAULT 0,
                gross_pay REAL DEFAULT 0,
                deductions REAL DEFAULT 0,
                net_pay REAL DEFAULT 0,
                benefits_cost REAL DEFAULT 0,
                source_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts_payable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                fiscal_year INTEGER,
                invoice_date DATE,
                invoice_number TEXT,
                vendor_id TEXT,
                vendor_name TEXT,
                amount REAL DEFAULT 0,
                account_number TEXT,
                fund TEXT,
                department TEXT,
                status TEXT,
                paid_date DATE,
                check_number TEXT,
                source_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts_receivable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                fiscal_year INTEGER,
                invoice_date DATE,
                invoice_number TEXT,
                customer_id TEXT,
                customer_name TEXT,
                amount REAL DEFAULT 0,
                account_number TEXT,
                fund TEXT,
                status TEXT,
                received_date DATE,
                source_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS utility_billing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                fiscal_year INTEGER,
                billing_period TEXT,
                service_type TEXT,
                account_number TEXT,
                customer_name TEXT,
                address TEXT,
                usage_amount REAL DEFAULT 0,
                usage_unit TEXT,
                billed_amount REAL DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                source_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixed_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                fiscal_year INTEGER,
                asset_id TEXT,
                asset_description TEXT,
                asset_type TEXT,
                department TEXT,
                location TEXT,
                acquisition_date DATE,
                acquisition_cost REAL DEFAULT 0,
                accumulated_depreciation REAL DEFAULT 0,
                book_value REAL DEFAULT 0,
                useful_life_years INTEGER,
                source_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                municipality_id TEXT NOT NULL,
                report_type TEXT,
                fiscal_year INTEGER,
                data_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES import_sessions(session_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gl_municipality_year ON general_ledger(municipality_id, fiscal_year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gl_account ON general_ledger(account_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gl_date ON general_ledger(transaction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_budget_municipality_year ON budget_data(municipality_id, fiscal_year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payroll_municipality_year ON payroll_data(municipality_id, fiscal_year)")
        
        conn.commit()
        conn.close()
        logger.info(f"Report archive initialized at {self.database_path}")
    
    def create_import_session(
        self,
        source_file: str,
        report_type: str,
        fiscal_year: int,
        fiscal_period: Optional[str] = None,
        record_count: int = 0,
        metadata: Optional[Dict] = None
    ) -> int:
        """Create a new import session and return session_id"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO import_sessions 
            (municipality_id, source_file, report_type, fiscal_year, fiscal_period, record_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self.municipality_id,
            source_file,
            report_type,
            fiscal_year,
            fiscal_period,
            record_count,
            json.dumps(metadata) if metadata else None
        ))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def archive_import(
        self,
        import_result: Dict[str, Any]
    ) -> int:
        """Archive an import result from FileImportService"""
        session_id = self.create_import_session(
            source_file=import_result.get('filename', ''),
            report_type=import_result.get('report_type', 'unknown'),
            fiscal_year=import_result.get('fiscal_year', datetime.now().year),
            fiscal_period=import_result.get('fiscal_period'),
            record_count=import_result.get('record_count', 0),
            metadata={"processed_at": import_result.get('processed_at')}
        )
        
        report_type = import_result.get('report_type', 'unknown')
        data = import_result.get('data', [])
        
        if report_type in ['general_ledger', 'journal']:
            self._store_general_ledger(session_id, data, import_result.get('fiscal_year'))
        elif report_type == 'budget':
            self._store_budget_data(session_id, data, import_result.get('fiscal_year'))
        elif report_type == 'payroll':
            self._store_payroll_data(session_id, data, import_result.get('fiscal_year'))
        else:
            self._store_raw_import(session_id, report_type, data, import_result.get('fiscal_year'))
        
        return session_id
    
    def _store_general_ledger(self, session_id: int, data: List[Dict], fiscal_year: int):
        """Store general ledger records"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for record in data:
            cursor.execute("""
                INSERT INTO general_ledger
                (session_id, municipality_id, fiscal_year, transaction_date, account_number,
                 account_description, fund, department, debit, credit, description,
                 reference, vendor, check_number, source_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                self.municipality_id,
                fiscal_year,
                record.get('date') or record.get('transaction_date'),
                record.get('account_number') or record.get('account'),
                record.get('account_description') or record.get('description'),
                record.get('fund'),
                record.get('department'),
                self._parse_amount(record.get('debit', 0)),
                self._parse_amount(record.get('credit', 0)),
                record.get('description') or record.get('memo'),
                record.get('reference'),
                record.get('vendor'),
                record.get('check_number'),
                json.dumps(record)
            ))
        
        conn.commit()
        conn.close()
    
    def _store_budget_data(self, session_id: int, data: List[Dict], fiscal_year: int):
        """Store budget data records"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for record in data:
            cursor.execute("""
                INSERT INTO budget_data
                (session_id, municipality_id, fiscal_year, account_number, account_description,
                 fund, department, original_budget, revised_budget, actual_ytd, encumbered, available, source_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                self.municipality_id,
                fiscal_year,
                record.get('account_number') or record.get('account'),
                record.get('account_description') or record.get('description'),
                record.get('fund'),
                record.get('department'),
                self._parse_amount(record.get('original_budget') or record.get('budget_amount', 0)),
                self._parse_amount(record.get('revised_budget', 0)),
                self._parse_amount(record.get('actual_ytd') or record.get('actual', 0)),
                self._parse_amount(record.get('encumbered', 0)),
                self._parse_amount(record.get('available', 0)),
                json.dumps(record)
            ))
        
        conn.commit()
        conn.close()
    
    def _store_payroll_data(self, session_id: int, data: List[Dict], fiscal_year: int):
        """Store payroll data records"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for record in data:
            cursor.execute("""
                INSERT INTO payroll_data
                (session_id, municipality_id, fiscal_year, pay_period, pay_date,
                 employee_id, employee_name, department, position,
                 hours_regular, hours_overtime, gross_pay, deductions, net_pay, benefits_cost, source_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                self.municipality_id,
                fiscal_year,
                record.get('pay_period'),
                record.get('pay_date'),
                record.get('employee_id'),
                record.get('employee_name') or record.get('name'),
                record.get('department'),
                record.get('position') or record.get('title'),
                self._parse_amount(record.get('hours_regular') or record.get('regular_hours', 0)),
                self._parse_amount(record.get('hours_overtime') or record.get('overtime_hours', 0)),
                self._parse_amount(record.get('gross_pay', 0)),
                self._parse_amount(record.get('deductions', 0)),
                self._parse_amount(record.get('net_pay', 0)),
                self._parse_amount(record.get('benefits_cost') or record.get('benefits', 0)),
                json.dumps(record)
            ))
        
        conn.commit()
        conn.close()
    
    def _store_raw_import(self, session_id: int, report_type: str, data: List[Dict], fiscal_year: int):
        """Store raw import data for unknown report types"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO raw_imports (session_id, municipality_id, report_type, fiscal_year, data_json)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, self.municipality_id, report_type, fiscal_year, json.dumps(data)))
        
        conn.commit()
        conn.close()
    
    def _parse_amount(self, value) -> float:
        """Parse amount from various formats"""
        if value is None or value == '':
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace(',', '').replace('$', '').replace('(', '-').replace(')', '').strip()
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def get_general_ledger(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        fund: Optional[str] = None,
        department: Optional[str] = None,
        account: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query general ledger data from archive"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM general_ledger WHERE municipality_id = ?"
        params = [self.municipality_id]
        
        if fiscal_year:
            query += " AND fiscal_year = ?"
            params.append(fiscal_year)
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)
        if fund:
            query += " AND fund = ?"
            params.append(fund)
        if department:
            query += " AND department = ?"
            params.append(department)
        if account:
            query += " AND account_number LIKE ?"
            params.append(f"%{account}%")
        
        query += " ORDER BY transaction_date DESC, id DESC"
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_budget_data(
        self,
        fiscal_year: int,
        fund: Optional[str] = None,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query budget data from archive"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM budget_data WHERE municipality_id = ? AND fiscal_year = ?"
        params = [self.municipality_id, fiscal_year]
        
        if fund:
            query += " AND fund = ?"
            params.append(fund)
        if department:
            query += " AND department = ?"
            params.append(department)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_payroll_data(
        self,
        fiscal_year: Optional[int] = None,
        department: Optional[str] = None,
        employee_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query payroll data from archive"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM payroll_data WHERE municipality_id = ?"
        params = [self.municipality_id]
        
        if fiscal_year:
            query += " AND fiscal_year = ?"
            params.append(fiscal_year)
        if department:
            query += " AND department = ?"
            params.append(department)
        if employee_id:
            query += " AND employee_id = ?"
            params.append(employee_id)
        
        query += " ORDER BY pay_date DESC"
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_available_years(self) -> List[int]:
        """Get list of years with data in archive"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT fiscal_year FROM import_sessions 
            WHERE municipality_id = ? AND fiscal_year IS NOT NULL
            ORDER BY fiscal_year DESC
        """, (self.municipality_id,))
        
        years = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return years
    
    def get_import_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent import history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM import_sessions 
            WHERE municipality_id = ?
            ORDER BY import_timestamp DESC
            LIMIT ?
        """, (self.municipality_id, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """Check archive status"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM import_sessions WHERE municipality_id = ?", (self.municipality_id,))
        session_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM general_ledger WHERE municipality_id = ?", (self.municipality_id,))
        gl_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "active",
            "database_path": str(self.database_path),
            "municipality": self.municipality_id,
            "import_sessions": session_count,
            "gl_records": gl_count,
            "available_years": self.get_available_years(),
            "timestamp": datetime.now().isoformat()
        }
