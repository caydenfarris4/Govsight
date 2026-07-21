"""
Advanced Security Audit Logger

This module provides comprehensive security audit logging, session management,
and real-time threat detection for the GovSight Financial Analyzer.
"""

import logging
import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import sqlite3

class SecurityEventType(Enum):
    """Security event types for classification"""
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    SQL_INJECTION_ATTEMPT = "SQL_INJECTION_ATTEMPT"
    XSS_ATTEMPT = "XSS_ATTEMPT"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    DATA_EXPORT = "DATA_EXPORT"
    ADMIN_ACTION = "ADMIN_ACTION"
    SESSION_CREATION = "SESSION_CREATION"
    SESSION_EXPIRY = "SESSION_EXPIRY"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    FAILED_AUTHORIZATION = "FAILED_AUTHORIZATION"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"

class ThreatLevel(Enum):
    """Threat level classification"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class SecurityEvent:
    """Security event data structure"""
    timestamp: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    event_details: Dict[str, Any]
    source_module: str
    action_taken: str

class SecurityAuditLogger:
    """Advanced security audit logger with threat detection"""
    
    def __init__(self, log_file: str = "security_audit.log", db_file: str = "security_events.db"):
        """
        Initialize security audit logger
        
        Args:
            log_file (str): Path to log file
            db_file (str): Path to SQLite database for events
        """
        self.log_file = log_file
        self.db_file = db_file
        self.threat_counters = {}
        self.session_cache = {}
        self.lock = threading.Lock()
        
        # Set up logging
        self.logger = logging.getLogger('security_audit')
        self.logger.setLevel(logging.INFO)
        
        # File handler for persistent logging
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler for immediate alerts
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for security events"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    threat_level TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    event_details TEXT,
                    source_module TEXT,
                    action_taken TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON security_events(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type ON security_events(event_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON security_events(user_id)
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize security database: {e}")
    
    def log_security_event(
        self,
        event_type: SecurityEventType,
        threat_level: ThreatLevel,
        user_id: str = "unknown",
        session_id: str = "",
        ip_address: str = "unknown",
        user_agent: str = "",
        event_details: Dict[str, Any] = None,
        source_module: str = "",
        action_taken: str = ""
    ) -> bool:
        """
        Log a security event with comprehensive details
        
        Args:
            event_type: Type of security event
            threat_level: Severity level
            user_id: User identifier
            session_id: Session identifier
            ip_address: Source IP address
            user_agent: User agent string
            event_details: Additional event details
            source_module: Module that generated the event
            action_taken: Action taken in response
            
        Returns:
            bool: True if logged successfully
        """
        try:
            with self.lock:
                # Create security event
                event = SecurityEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type=event_type,
                    threat_level=threat_level,
                    user_id=user_id,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    event_details=event_details or {},
                    source_module=source_module,
                    action_taken=action_taken
                )
                
                # Log to file
                log_message = (
                    f"SECURITY_EVENT - Type: {event_type.value}, "
                    f"Level: {threat_level.value}, "
                    f"User: {user_id}, "
                    f"Module: {source_module}, "
                    f"Details: {json.dumps(event_details or {})}"
                )
                
                if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                    self.logger.critical(log_message)
                elif threat_level == ThreatLevel.MEDIUM:
                    self.logger.warning(log_message)
                else:
                    self.logger.info(log_message)
                
                # Store in database
                self._store_event_to_db(event)
                
                # Update threat counters
                self._update_threat_counters(user_id, event_type, threat_level)
                
                # Check for suspicious patterns
                self._detect_suspicious_patterns(user_id, event_type)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to log security event: {e}")
            return False
    
    def _store_event_to_db(self, event: SecurityEvent):
        """Store security event in database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_events 
                (timestamp, event_type, threat_level, user_id, session_id, 
                 ip_address, user_agent, event_details, source_module, action_taken)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp,
                event.event_type.value,
                event.threat_level.value,
                event.user_id,
                event.session_id,
                event.ip_address,
                event.user_agent,
                json.dumps(event.event_details),
                event.source_module,
                event.action_taken
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store event to database: {e}")
    
    def _update_threat_counters(self, user_id: str, event_type: SecurityEventType, threat_level: ThreatLevel):
        """Update threat counters for pattern detection"""
        key = f"{user_id}_{event_type.value}"
        current_time = time.time()
        
        if key not in self.threat_counters:
            self.threat_counters[key] = []
        
        # Add current event
        self.threat_counters[key].append({
            'timestamp': current_time,
            'threat_level': threat_level
        })
        
        # Remove events older than 1 hour
        one_hour_ago = current_time - 3600
        self.threat_counters[key] = [
            event for event in self.threat_counters[key]
            if event['timestamp'] > one_hour_ago
        ]
    
    def _detect_suspicious_patterns(self, user_id: str, event_type: SecurityEventType):
        """Detect suspicious activity patterns"""
        # Check for rapid failed login attempts
        if event_type == SecurityEventType.LOGIN_FAILURE:
            failure_key = f"{user_id}_{SecurityEventType.LOGIN_FAILURE.value}"
            if failure_key in self.threat_counters:
                recent_failures = len(self.threat_counters[failure_key])
                if recent_failures >= 5:
                    self.log_security_event(
                        SecurityEventType.SUSPICIOUS_ACTIVITY,
                        ThreatLevel.HIGH,
                        user_id=user_id,
                        event_details={
                            "pattern": "rapid_login_failures",
                            "count": recent_failures,
                            "timeframe": "1_hour"
                        },
                        source_module="audit_logger",
                        action_taken="account_lockout_recommended"
                    )
        
        # Check for repeated SQL injection attempts
        if event_type == SecurityEventType.SQL_INJECTION_ATTEMPT:
            injection_key = f"{user_id}_{SecurityEventType.SQL_INJECTION_ATTEMPT.value}"
            if injection_key in self.threat_counters:
                recent_attempts = len(self.threat_counters[injection_key])
                if recent_attempts >= 3:
                    self.log_security_event(
                        SecurityEventType.SUSPICIOUS_ACTIVITY,
                        ThreatLevel.CRITICAL,
                        user_id=user_id,
                        event_details={
                            "pattern": "repeated_sql_injection",
                            "count": recent_attempts,
                            "timeframe": "1_hour"
                        },
                        source_module="audit_logger",
                        action_taken="ip_blocking_recommended"
                    )
    
    def get_security_events(
        self, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[SecurityEventType] = None,
        user_id: Optional[str] = None,
        threat_level: Optional[ThreatLevel] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve security events with filtering
        
        Args:
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            event_type: Filter by event type
            user_id: Filter by user ID
            threat_level: Filter by threat level
            limit: Maximum number of events to return
            
        Returns:
            List of security events
        """
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM security_events WHERE 1=1"
            params = []
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if threat_level:
                query += " AND threat_level = ?"
                params.append(threat_level.value)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                event_dict = dict(row)
                # Parse JSON event_details
                if event_dict['event_details']:
                    event_dict['event_details'] = json.loads(event_dict['event_details'])
                events.append(event_dict)
            
            conn.close()
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve security events: {e}")
            return []
    
    def generate_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate security report for the specified time period
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Dictionary containing security statistics
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Get events in time range
            events = self.get_security_events(
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                limit=10000
            )
            
            # Generate statistics
            report = {
                "report_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_hours": hours
                },
                "total_events": len(events),
                "events_by_type": {},
                "events_by_threat_level": {},
                "events_by_user": {},
                "top_threats": [],
                "suspicious_patterns": []
            }
            
            # Count events by type
            for event in events:
                event_type = event['event_type']
                threat_level = event['threat_level']
                user_id = event['user_id']
                
                # Count by type
                if event_type not in report["events_by_type"]:
                    report["events_by_type"][event_type] = 0
                report["events_by_type"][event_type] += 1
                
                # Count by threat level
                if threat_level not in report["events_by_threat_level"]:
                    report["events_by_threat_level"][threat_level] = 0
                report["events_by_threat_level"][threat_level] += 1
                
                # Count by user
                if user_id not in report["events_by_user"]:
                    report["events_by_user"][user_id] = 0
                report["events_by_user"][user_id] += 1
            
            # Identify top threats
            critical_events = [e for e in events if e['threat_level'] == 'CRITICAL']
            high_events = [e for e in events if e['threat_level'] == 'HIGH']
            
            report["top_threats"] = critical_events[:10] + high_events[:10]
            
            # Identify suspicious patterns
            suspicious_events = [
                e for e in events 
                if e['event_type'] == 'SUSPICIOUS_ACTIVITY'
            ]
            report["suspicious_patterns"] = suspicious_events
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate security report: {e}")
            return {}

# Global security logger instance
_security_logger = None

def get_security_logger() -> SecurityAuditLogger:
    """Get the global security logger instance"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityAuditLogger()
    return _security_logger

def log_security_event(
    event_type: SecurityEventType,
    threat_level: ThreatLevel,
    user_id: str = "unknown",
    session_id: str = "",
    ip_address: str = "unknown",
    user_agent: str = "",
    event_details: Dict[str, Any] = None,
    source_module: str = "",
    action_taken: str = ""
) -> bool:
    """Convenience function to log security events"""
    logger = get_security_logger()
    return logger.log_security_event(
        event_type, threat_level, user_id, session_id,
        ip_address, user_agent, event_details, source_module, action_taken
    )