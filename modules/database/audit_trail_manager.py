"""
Database Audit Trail Manager
Tracks all delete operations on General Ledger databases with comprehensive logging

ARCHITECTURAL DECISION: Implement audit trails for financial data compliance
WHY: Municipal financial systems require complete audit trails for regulatory compliance,
forensic investigation, and data recovery. Every delete operation must be logged with
full context including user, timestamp, and original data.

DESIGN PATTERN: Immutable audit log with before-image capture
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import os
import hashlib
from modules.database.connection_manager import get_database_connection, load_db_config

class AuditTrailManager:
    """Manages audit trails for database delete operations"""
    
    def __init__(self):
        self.audit_db_path = "databases/audit/audit_trail.db"
        self._ensure_audit_database()
    
    def _ensure_audit_database(self):
        """Create audit database and tables if they don't exist"""
        # Ensure audit directory exists
        audit_dir = os.path.dirname(self.audit_db_path)
        if not os.path.exists(audit_dir):
            os.makedirs(audit_dir, exist_ok=True)
        
        # Create audit database
        conn = sqlite3.connect(self.audit_db_path)
        try:
            cursor = conn.cursor()
            
            # Create audit trail table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_timestamp TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                database_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id TEXT,
                user_id TEXT,
                session_id TEXT,
                original_data TEXT,
                affected_rows INTEGER,
                query_hash TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT DEFAULT (datetime('now', 'utc'))
            )
            ''')
            
            # Create delete operations specific table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS gl_delete_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                delete_timestamp TEXT NOT NULL,
                gl_database TEXT NOT NULL,
                table_name TEXT NOT NULL,
                deleted_record_count INTEGER,
                deleted_data_json TEXT,
                delete_criteria TEXT,
                user_id TEXT,
                user_role TEXT,
                session_id TEXT,
                operation_reason TEXT,
                approval_required BOOLEAN DEFAULT 0,
                approved_by TEXT,
                approval_timestamp TEXT,
                recovery_data TEXT,
                checksum TEXT,
                created_at TEXT DEFAULT (datetime('now', 'utc'))
            )
            ''')
            
            # Create recovery staging table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_staging (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER,
                table_name TEXT NOT NULL,
                recovery_data TEXT,
                recovery_status TEXT DEFAULT 'staged',
                recovery_requested_by TEXT,
                recovery_approved_by TEXT,
                recovery_timestamp TEXT,
                created_at TEXT DEFAULT (datetime('now', 'utc')),
                FOREIGN KEY (audit_id) REFERENCES gl_delete_audit(id)
            )
            ''')
            
            # Create audit summary view
            cursor.execute('''
            CREATE VIEW IF NOT EXISTS audit_summary AS
            SELECT 
                date(delete_timestamp) as delete_date,
                gl_database,
                table_name,
                COUNT(*) as delete_operations,
                SUM(deleted_record_count) as total_records_deleted,
                GROUP_CONCAT(DISTINCT user_id) as users_involved
            FROM gl_delete_audit
            GROUP BY date(delete_timestamp), gl_database, table_name
            ORDER BY delete_timestamp DESC
            ''')
            
            conn.commit()
            
        finally:
            conn.close()
    
    def log_delete_operation(self, 
                           database_name: str,
                           table_name: str, 
                           delete_criteria: str,
                           deleted_data: Union[List[Dict], pd.DataFrame],
                           user_id: Optional[str] = None,
                           user_role: Optional[str] = None,
                           session_id: Optional[str] = None,
                           operation_reason: Optional[str] = None) -> int:
        """
        Log a delete operation with full audit trail
        
        Args:
            database_name: Name of the GL database
            table_name: Table where deletion occurred
            delete_criteria: SQL WHERE clause or description of delete criteria
            deleted_data: The actual data that was deleted (before deletion)
            user_id: User who performed the deletion
            user_role: Role of the user
            session_id: Session identifier
            operation_reason: Reason for the deletion
            
        Returns:
            audit_id: ID of the audit record created
        """
        
        conn = sqlite3.connect(self.audit_db_path)
        try:
            cursor = conn.cursor()
            
            # Convert data to JSON for storage
            if isinstance(deleted_data, pd.DataFrame):
                data_json = deleted_data.to_json(orient='records', date_format='iso')
                record_count = len(deleted_data)
            elif isinstance(deleted_data, list):
                data_json = json.dumps(deleted_data)
                record_count = len(deleted_data)
            else:
                data_json = json.dumps(str(deleted_data))
                record_count = 1
            
            # Create checksum for data integrity
            checksum = hashlib.sha256(data_json.encode('utf-8')).hexdigest()
            
            # Insert audit record
            cursor.execute('''
            INSERT INTO gl_delete_audit (
                delete_timestamp, gl_database, table_name, deleted_record_count,
                deleted_data_json, delete_criteria, user_id, user_role, session_id,
                operation_reason, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(),
                database_name,
                table_name,
                record_count,
                data_json,
                delete_criteria,
                user_id if user_id is not None else 'unknown',
                user_role if user_role is not None else 'unknown', 
                session_id if session_id is not None else 'unknown',
                operation_reason if operation_reason is not None else 'Not specified',
                checksum
            ))
            
            audit_id = cursor.lastrowid
            conn.commit()
            
            # Also log to general audit trail
            self._log_to_general_audit(
                'DELETE', database_name, table_name, 
                str(audit_id), user_id if user_id is not None else 'unknown', 
                session_id if session_id is not None else 'unknown', data_json, record_count
            )
            
            return audit_id
            
        finally:
            conn.close()
    
    def _log_to_general_audit(self, operation_type: str, database_name: str, 
                            table_name: str, record_id: str, user_id: str, 
                            session_id: str, original_data: str, affected_rows: int):
        """Log to general audit trail table"""
        conn = sqlite3.connect(self.audit_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO audit_trail (
                audit_timestamp, operation_type, database_name, table_name,
                record_id, user_id, session_id, original_data, affected_rows,
                query_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(),
                operation_type,
                database_name,
                table_name,
                record_id,
                user_id,
                session_id,
                original_data,
                affected_rows,
                hashlib.md5(f"{operation_type}{table_name}{record_id}".encode()).hexdigest()
            ))
            conn.commit()
        finally:
            conn.close()
    
    def get_audit_trail(self, 
                       database_name: str = None,
                       table_name: str = None,
                       user_id: str = None,
                       start_date: str = None,
                       end_date: str = None,
                       limit: int = 100) -> pd.DataFrame:
        """
        Retrieve audit trail records with filtering options
        
        Args:
            database_name: Filter by database name
            table_name: Filter by table name
            user_id: Filter by user ID
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            limit: Maximum number of records to return
            
        Returns:
            DataFrame with audit trail records
        """
        
        conn = sqlite3.connect(self.audit_db_path)
        try:
            # Build dynamic query
            where_clauses = []
            params = []
            
            if database_name:
                where_clauses.append("gl_database = ?")
                params.append(database_name)
            
            if table_name:
                where_clauses.append("table_name = ?")
                params.append(table_name)
            
            if user_id:
                where_clauses.append("user_id = ?")
                params.append(user_id)
            
            if start_date:
                where_clauses.append("date(delete_timestamp) >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("date(delete_timestamp) <= ?")
                params.append(end_date)
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            query = f'''
            SELECT 
                id,
                delete_timestamp,
                gl_database,
                table_name,
                deleted_record_count,
                user_id,
                user_role,
                session_id,
                operation_reason,
                checksum,
                created_at
            FROM gl_delete_audit
            {where_clause}
            ORDER BY delete_timestamp DESC
            LIMIT ?
            '''
            
            params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
            
        finally:
            conn.close()
    
    def get_deleted_data(self, audit_id: int) -> Dict[str, Any]:
        """
        Retrieve the original data that was deleted
        
        Args:
            audit_id: ID of the audit record
            
        Returns:
            Dictionary containing the deleted data and metadata
        """
        
        conn = sqlite3.connect(self.audit_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT deleted_data_json, checksum, table_name, gl_database,
                   delete_timestamp, user_id, operation_reason
            FROM gl_delete_audit
            WHERE id = ?
            ''', (audit_id,))
            
            result = cursor.fetchone()
            if not result:
                return {"error": "Audit record not found"}
            
            data_json, checksum, table_name, gl_database, timestamp, user_id, reason = result
            
            # Verify data integrity
            current_checksum = hashlib.sha256(data_json.encode()).hexdigest()
            if current_checksum != checksum:
                return {"error": "Data integrity check failed - possible corruption"}
            
            # Parse the JSON data
            try:
                deleted_data = json.loads(data_json)
                if isinstance(deleted_data, str):
                    # Try to parse again if it was double-encoded
                    deleted_data = json.loads(deleted_data)
            except json.JSONDecodeError:
                return {"error": "Could not parse deleted data"}
            
            return {
                "audit_id": audit_id,
                "deleted_data": deleted_data,
                "table_name": table_name,
                "database_name": gl_database,
                "delete_timestamp": timestamp,
                "user_id": user_id,
                "operation_reason": reason,
                "integrity_verified": True
            }
            
        finally:
            conn.close()
    
    def get_audit_summary(self, days: int = 30) -> pd.DataFrame:
        """Get summary of audit activities over specified days"""
        conn = sqlite3.connect(self.audit_db_path)
        try:
            query = '''
            SELECT * FROM audit_summary
            WHERE delete_date >= date('now', '-{} days')
            ORDER BY delete_date DESC
            '''.format(days)
            
            return pd.read_sql_query(query, conn)
        finally:
            conn.close()
    
    def prepare_recovery(self, audit_id: int, requested_by: str) -> int:
        """
        Prepare deleted data for recovery
        
        Args:
            audit_id: ID of the audit record to recover
            requested_by: User requesting the recovery
            
        Returns:
            recovery_id: ID of the recovery staging record
        """
        
        # Get the deleted data
        deleted_info = self.get_deleted_data(audit_id)
        if "error" in deleted_info:
            raise ValueError(f"Cannot prepare recovery: {deleted_info['error']}")
        
        conn = sqlite3.connect(self.audit_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO recovery_staging (
                audit_id, table_name, recovery_data, recovery_requested_by
            ) VALUES (?, ?, ?, ?)
            ''', (
                audit_id,
                deleted_info['table_name'],
                json.dumps(deleted_info['deleted_data']),
                requested_by
            ))
            
            recovery_id = cursor.lastrowid
            conn.commit()
            return recovery_id
            
        finally:
            conn.close()

# Global instance
audit_manager = AuditTrailManager()

def safe_delete_with_audit(database_name: str, table_name: str, 
                          delete_query: str, user_context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Perform a delete operation with full audit trail
    
    Args:
        database_name: Name of the database
        table_name: Table to delete from
        delete_query: DELETE SQL query
        user_context: Dictionary with user_id, user_role, session_id, reason
        
    Returns:
        Dictionary with operation results and audit information
    """
    
    user_context = user_context or {}
    
    # First, capture the data that will be deleted
    select_query = delete_query.replace('DELETE FROM', 'SELECT * FROM')
    
    try:
        # Get connection to the target database
        conn = get_database_connection(database_name)
        
        # Capture data before deletion
        deleted_data = pd.read_sql_query(select_query, conn)
        
        if deleted_data.empty:
            return {
                "success": True,
                "message": "No records matched delete criteria",
                "audit_id": None,
                "records_deleted": 0
            }
        
        # Log to audit trail BEFORE deletion
        audit_id = audit_manager.log_delete_operation(
            database_name=database_name,
            table_name=table_name,
            delete_criteria=delete_query,
            deleted_data=deleted_data,
            user_id=user_context.get('user_id'),
            user_role=user_context.get('user_role'),
            session_id=user_context.get('session_id'),
            operation_reason=user_context.get('reason')
        )
        
        # Perform the actual deletion
        cursor = conn.cursor()
        cursor.execute(delete_query)
        records_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"Successfully deleted {records_deleted} records",
            "audit_id": audit_id,
            "records_deleted": records_deleted,
            "audit_trail_created": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Delete operation failed: {str(e)}",
            "audit_id": None,
            "records_deleted": 0,
            "error": str(e)
        }