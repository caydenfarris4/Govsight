"""
Audit Logging System for Report Generation
Tracks all report generation activities for compliance and monitoring
"""

import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
import json
from pathlib import Path
import streamlit as st


class ReportAuditLogger:
    """Audit logger for tracking report generation and access"""
    
    def __init__(self, db_path: str = None):
        """Initialize audit logger with database connection"""
        if db_path is None:
            db_path = Path("databases") / "audit.db"
            db_path.parent.mkdir(exist_ok=True)
        
        self.db_path = str(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Create audit tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Report generation audit table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                user_role TEXT,
                report_type TEXT,
                module TEXT,
                format TEXT,
                parameters TEXT,
                status TEXT,
                error_message TEXT,
                file_size INTEGER,
                generation_time_ms INTEGER,
                ip_address TEXT
            )
        """)
        
        # Report access log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                report_id INTEGER,
                action TEXT,
                ip_address TEXT,
                FOREIGN KEY (report_id) REFERENCES report_audit (id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_report_audit_timestamp 
            ON report_audit(timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_report_audit_user 
            ON report_audit(user_id)
        """)
        
        conn.commit()
        conn.close()
    
    def log_report_generation(self,
                             user_id: str,
                             user_role: str,
                             report_type: str,
                             module: str,
                             format: str,
                             parameters: Dict[str, Any],
                             status: str = "success",
                             error_message: str = None,
                             file_size: int = None,
                             generation_time_ms: int = None) -> int:
        """
        Log report generation activity
        
        Args:
            user_id: User identifier
            user_role: User role (viewer, analyst, admin)
            report_type: Type of report generated
            module: Module that generated the report
            format: Export format (PDF, CSV, etc.)
            parameters: Report parameters as dictionary
            status: Generation status (success, failure)
            error_message: Error message if failed
            file_size: Size of generated file in bytes
            generation_time_ms: Time taken to generate report
            
        Returns:
            Report audit ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get IP address from session if available
        ip_address = st.session_state.get('client_ip', 'unknown')
        
        cursor.execute("""
            INSERT INTO report_audit (
                user_id, user_role, report_type, module, format,
                parameters, status, error_message, file_size,
                generation_time_ms, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            user_role,
            report_type,
            module,
            format,
            json.dumps(parameters),
            status,
            error_message,
            file_size,
            generation_time_ms,
            ip_address
        ))
        
        report_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return report_id
    
    def log_report_access(self,
                         user_id: str,
                         report_id: int,
                         action: str = "download"):
        """
        Log report access/download
        
        Args:
            user_id: User identifier
            report_id: Report audit ID
            action: Action performed (download, view, email)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ip_address = st.session_state.get('client_ip', 'unknown')
        
        cursor.execute("""
            INSERT INTO report_access_log (user_id, report_id, action, ip_address)
            VALUES (?, ?, ?, ?)
        """, (user_id, report_id, action, ip_address))
        
        conn.commit()
        conn.close()
    
    def get_user_report_history(self,
                                user_id: str,
                                limit: int = 50) -> list:
        """Get report generation history for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, timestamp, report_type, module, format, status,
                file_size, generation_time_ms
            FROM report_audit
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def get_report_statistics(self,
                              days: int = 30) -> Dict[str, Any]:
        """Get report generation statistics for the specified period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total reports generated
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   COUNT(DISTINCT user_id) as unique_users,
                   AVG(generation_time_ms) as avg_time_ms
            FROM report_audit
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """, (days,))
        
        row = cursor.fetchone()
        stats['total_reports'] = row[0]
        stats['unique_users'] = row[1]
        stats['avg_generation_time_ms'] = row[2]
        
        # Reports by format
        cursor.execute("""
            SELECT format, COUNT(*) as count
            FROM report_audit
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY format
            ORDER BY count DESC
        """, (days,))
        
        stats['by_format'] = {}
        for row in cursor.fetchall():
            stats['by_format'][row[0]] = row[1]
        
        # Reports by module
        cursor.execute("""
            SELECT module, COUNT(*) as count
            FROM report_audit
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY module
            ORDER BY count DESC
        """, (days,))
        
        stats['by_module'] = {}
        for row in cursor.fetchall():
            stats['by_module'][row[0]] = row[1]
        
        # Success rate
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'failure' THEN 1 ELSE 0 END) as failure
            FROM report_audit
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        """, (days,))
        
        row = cursor.fetchone()
        total = (row[0] or 0) + (row[1] or 0)
        stats['success_rate'] = (row[0] / total * 100) if total > 0 else 0
        
        conn.close()
        return stats
    
    def cleanup_old_records(self, days_to_keep: int = 365):
        """Clean up audit records older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete old report access logs first (foreign key constraint)
        cursor.execute("""
            DELETE FROM report_access_log
            WHERE report_id IN (
                SELECT id FROM report_audit
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            )
        """, (days_to_keep,))
        
        # Delete old report audits
        cursor.execute("""
            DELETE FROM report_audit
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        """, (days_to_keep,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count