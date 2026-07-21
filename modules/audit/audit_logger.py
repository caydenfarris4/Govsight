"""
Comprehensive Audit Logging System
Tracks security events, data access, user actions, and system operations
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import os
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Audit event types"""
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILED = "auth_failed"
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_MODIFY = "data_modify"
    API_CALL = "api_call"
    QUERY_EXECUTE = "query_execute"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    ADMIN_ACTION = "admin_action"
    CONFIG_CHANGE = "config_change"
    ERROR_OCCURRED = "error_occurred"
    SECURITY_ALERT = "security_alert"


class Severity(Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event"""
    event_type: EventType
    severity: Severity
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    resource: Optional[str]
    outcome: str  # 'success', 'failure', 'partial'
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    timestamp: str
    correlation_id: Optional[str]  # Link related events
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'event_type': self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            'severity': self.severity.value if isinstance(self.severity, Severity) else self.severity,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'action': self.action,
            'resource': self.resource,
            'outcome': self.outcome,
            'details': json.dumps(self.details) if self.details else None,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp,
            'correlation_id': self.correlation_id
        }


class AuditLogger:
    """Production-ready audit logging system"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize audit logger
        
        Args:
            db_path: Path to audit database
        """
        self.db_path = db_path or "databases/core/audit.db"
        self._init_database()
        
        # Configuration
        self.retention_days = 365  # Keep logs for 1 year
        self.max_detail_length = 10000  # Max length of details JSON
        
    def _init_database(self):
        """Initialize audit database schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                outcome TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp DATETIME NOT NULL,
                correlation_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indices for audit_log
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_correlation_id ON audit_log(correlation_id)")
        
        # Security alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                details TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_by TEXT,
                resolved_at DATETIME,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Data access log (for compliance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                database_name TEXT NOT NULL,
                table_name TEXT,
                operation TEXT NOT NULL,
                row_count INTEGER,
                query_hash TEXT,
                accessed_at DATETIME NOT NULL
            )
        """)
        
        # Create indices for data_access_log
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_access_user_id ON data_access_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_access_accessed_at ON data_access_log(accessed_at)")
        
        # Admin actions log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_user TEXT,
                before_state TEXT,
                after_state TEXT,
                reason TEXT,
                timestamp DATETIME NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Audit database initialized at {self.db_path}")
    
    def log_event(self, event: AuditEvent) -> bool:
        """
        Log an audit event
        
        Args:
            event: AuditEvent to log
            
        Returns:
            Success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            event_dict = event.to_dict()
            
            # Truncate details if too long
            if event_dict['details'] and len(event_dict['details']) > self.max_detail_length:
                event_dict['details'] = event_dict['details'][:self.max_detail_length] + '...[truncated]'
            
            cursor.execute("""
                INSERT INTO audit_log
                (event_type, severity, user_id, session_id, action, resource,
                 outcome, details, ip_address, timestamp, correlation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_dict['event_type'],
                event_dict['severity'],
                event_dict['user_id'],
                event_dict['session_id'],
                event_dict['action'],
                event_dict['resource'],
                event_dict['outcome'],
                event_dict['details'],
                event_dict['ip_address'],
                event_dict['timestamp'],
                event_dict['correlation_id']
            ))
            
            conn.commit()
            conn.close()
            
            # Check for security alerts
            if event.severity == Severity.CRITICAL or event.event_type == EventType.SECURITY_ALERT:
                self._create_security_alert(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False
    
    def log_auth_attempt(self, username: str, success: bool, ip_address: str = None,
                        session_id: str = None) -> bool:
        """Log authentication attempt"""
        event = AuditEvent(
            event_type=EventType.AUTH_LOGIN if success else EventType.AUTH_FAILED,
            severity=Severity.INFO if success else Severity.WARNING,
            user_id=username if success else None,
            session_id=session_id,
            action="login_attempt",
            resource="authentication_system",
            outcome="success" if success else "failure",
            details={"username": username},
            ip_address=ip_address,
            timestamp=datetime.now().isoformat(),
            correlation_id=self._generate_correlation_id(username)
        )
        
        return self.log_event(event)
    
    def log_data_access(self, user_id: str, database: str, table: str = None,
                       operation: str = "SELECT", row_count: int = None,
                       query_hash: str = None) -> bool:
        """Log data access for compliance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO data_access_log
                (user_id, database_name, table_name, operation, row_count,
                 query_hash, accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                database,
                table,
                operation,
                row_count,
                query_hash,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            # Also log as audit event
            event = AuditEvent(
                event_type=EventType.DATA_ACCESS,
                severity=Severity.INFO,
                user_id=user_id,
                session_id=None,
                action=f"data_access_{operation.lower()}",
                resource=f"{database}.{table}" if table else database,
                outcome="success",
                details={"operation": operation, "row_count": row_count},
                ip_address=None,
                timestamp=datetime.now().isoformat(),
                correlation_id=None
            )
            
            return self.log_event(event)
            
        except Exception as e:
            logger.error(f"Failed to log data access: {e}")
            return False
    
    def log_admin_action(self, admin_user: str, action_type: str, target_user: str = None,
                        before_state: Dict = None, after_state: Dict = None,
                        reason: str = None) -> bool:
        """Log administrative actions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO admin_actions
                (admin_user, action_type, target_user, before_state,
                 after_state, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                admin_user,
                action_type,
                target_user,
                json.dumps(before_state) if before_state else None,
                json.dumps(after_state) if after_state else None,
                reason,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            # Also log as audit event
            event = AuditEvent(
                event_type=EventType.ADMIN_ACTION,
                severity=Severity.WARNING,  # Admin actions are always significant
                user_id=admin_user,
                session_id=None,
                action=action_type,
                resource=f"admin_target:{target_user}" if target_user else "system",
                outcome="success",
                details={"reason": reason, "target": target_user},
                ip_address=None,
                timestamp=datetime.now().isoformat(),
                correlation_id=self._generate_correlation_id(admin_user)
            )
            
            return self.log_event(event)
            
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            return False
    
    def _create_security_alert(self, event: AuditEvent):
        """Create security alert from critical event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_alerts
                (alert_type, severity, description, user_id, ip_address,
                 details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
                event.severity.value if isinstance(event.severity, Severity) else event.severity,
                f"{event.action} on {event.resource}",
                event.user_id,
                event.ip_address,
                json.dumps(event.details) if event.details else None,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to create security alert: {e}")
    
    def get_events(self, user_id: str = None, event_type: EventType = None,
                   start_date: datetime = None, end_date: datetime = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """Query audit events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value if isinstance(event_type, EventType) else event_type)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            columns = [desc[0] for desc in cursor.description]
            events = []
            
            for row in cursor.fetchall():
                event_dict = dict(zip(columns, row))
                if event_dict.get('details'):
                    try:
                        event_dict['details'] = json.loads(event_dict['details'])
                    except:
                        pass
                events.append(event_dict)
            
            conn.close()
            return events
            
        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            return []
    
    def get_security_alerts(self, resolved: bool = False) -> List[Dict[str, Any]]:
        """Get security alerts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM security_alerts
                WHERE resolved = ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (1 if resolved else 0,))
            
            columns = [desc[0] for desc in cursor.description]
            alerts = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get security alerts: {e}")
            return []
    
    def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            # Archive to separate table before deletion (optional)
            cursor.execute("""
                DELETE FROM audit_log
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted} old audit logs")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0
    
    def _generate_correlation_id(self, seed: str) -> str:
        """Generate correlation ID for related events"""
        return hashlib.md5(f"{seed}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]


# Global singleton instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
