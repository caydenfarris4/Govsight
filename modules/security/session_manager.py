"""
Advanced Session Management with Security Controls

This module provides secure session management with automatic expiry,
concurrent session limits, and suspicious activity detection.
"""

import os
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import sqlite3
import threading
from .audit_logger import SecurityEventType, ThreatLevel, log_security_event

@dataclass
class UserSession:
    """User session data structure"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    is_active: bool
    permissions: List[str]
    session_data: Dict[str, Any]

class SessionManager:
    """Advanced session manager with security controls"""
    
    def __init__(self, db_file: str = "user_sessions.db", max_session_age: int = 3600):
        """
        Initialize session manager
        
        Args:
            db_file (str): Path to session database
            max_session_age (int): Maximum session age in seconds (default: 1 hour)
        """
        self.db_file = db_file
        self.max_session_age = max_session_age
        self.active_sessions = {}
        self.failed_attempts = {}
        self.lock = threading.Lock()
        
        # Session security settings
        self.max_concurrent_sessions = 3
        self.session_timeout_minutes = 30
        self.failed_attempt_lockout = 5
        self.lockout_duration_minutes = 15
        
        # Initialize database
        self._init_database()
        
        # Clean up expired sessions on startup
        self._cleanup_expired_sessions()
    
    def _init_database(self):
        """Initialize SQLite database for session storage"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active INTEGER DEFAULT 1,
                    permissions TEXT,
                    session_data TEXT,
                    expires_at TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at)
            """)
            
            # Table for tracking failed authentication attempts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failed_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    ip_address TEXT,
                    attempt_time TEXT NOT NULL,
                    reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_failed_attempts_user ON failed_attempts(user_id)
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            raise Exception(f"Failed to initialize session database: {e}")
    
    def create_session(
        self,
        user_id: str,
        ip_address: str = "unknown",
        user_agent: str = "",
        permissions: List[str] = None,
        session_data: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Create a new user session with security validations
        
        Args:
            user_id (str): User identifier
            ip_address (str): User's IP address
            user_agent (str): User's browser user agent
            permissions (List[str]): User permissions
            session_data (Dict): Additional session data
            
        Returns:
            str: Session ID if successful, None if failed
        """
        try:
            with self.lock:
                # Check if user is locked out
                if self._is_user_locked_out(user_id, ip_address):
                    log_security_event(
                        SecurityEventType.FAILED_AUTHORIZATION,
                        ThreatLevel.MEDIUM,
                        user_id=user_id,
                        ip_address=ip_address,
                        event_details={"reason": "user_locked_out"},
                        source_module="session_manager",
                        action_taken="session_creation_denied"
                    )
                    return None
                
                # Check concurrent session limit
                active_sessions = self._get_active_sessions_for_user(user_id)
                if len(active_sessions) >= self.max_concurrent_sessions:
                    # Terminate oldest session
                    oldest_session = min(active_sessions, key=lambda x: x['last_activity'])
                    self.terminate_session(oldest_session['session_id'], "max_sessions_exceeded")
                
                # Generate secure session ID
                session_id = self._generate_session_id()
                
                # Calculate expiry time
                created_at = datetime.now()
                expires_at = created_at + timedelta(minutes=self.session_timeout_minutes)
                
                # Create session object
                session = UserSession(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=created_at,
                    last_activity=created_at,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    is_active=True,
                    permissions=permissions or [],
                    session_data=session_data or {}
                )
                
                # Store session in database
                self._store_session(session, expires_at)
                
                # Add to active sessions cache
                self.active_sessions[session_id] = session
                
                # Log session creation
                log_security_event(
                    SecurityEventType.SESSION_CREATION,
                    ThreatLevel.LOW,
                    user_id=user_id,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    event_details={
                        "session_timeout_minutes": self.session_timeout_minutes,
                        "permissions": permissions or []
                    },
                    source_module="session_manager",
                    action_taken="session_created"
                )
                
                return session_id
                
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.MEDIUM,
                user_id=user_id,
                event_details={"error": str(e), "operation": "create_session"},
                source_module="session_manager",
                action_taken="session_creation_failed"
            )
            return None
    
    def validate_session(
        self,
        session_id: str,
        ip_address: str = "unknown",
        user_agent: str = ""
    ) -> Optional[UserSession]:
        """
        Validate and refresh a user session
        
        Args:
            session_id (str): Session identifier
            ip_address (str): Current IP address
            user_agent (str): Current user agent
            
        Returns:
            UserSession: Session object if valid, None if invalid
        """
        try:
            with self.lock:
                # Check cache first
                if session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                else:
                    # Load from database
                    session = self._load_session(session_id)
                    if not session:
                        return None
                
                # Validate session
                if not session.is_active:
                    return None
                
                # Check expiry
                if self._is_session_expired(session):
                    self.terminate_session(session_id, "session_expired")
                    return None
                
                # Security checks
                if not self._validate_session_security(session, ip_address, user_agent):
                    self.terminate_session(session_id, "security_violation")
                    return None
                
                # Update last activity
                session.last_activity = datetime.now()
                session.ip_address = ip_address  # Update current IP
                
                # Update in database and cache
                self._update_session_activity(session)
                self.active_sessions[session_id] = session
                
                return session
                
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.MEDIUM,
                session_id=session_id,
                ip_address=ip_address,
                event_details={"error": str(e), "operation": "validate_session"},
                source_module="session_manager",
                action_taken="session_validation_failed"
            )
            return None
    
    def terminate_session(self, session_id: str, reason: str = "user_logout") -> bool:
        """
        Terminate a user session
        
        Args:
            session_id (str): Session identifier
            reason (str): Reason for termination
            
        Returns:
            bool: True if successful
        """
        try:
            with self.lock:
                # Get session info for logging
                session = self.active_sessions.get(session_id) or self._load_session(session_id)
                
                # Remove from cache
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                
                # Mark inactive in database
                self._deactivate_session(session_id)
                
                # Log session termination
                if session:
                    log_security_event(
                        SecurityEventType.SESSION_EXPIRY,
                        ThreatLevel.LOW,
                        user_id=session.user_id,
                        session_id=session_id,
                        ip_address=session.ip_address,
                        event_details={"reason": reason},
                        source_module="session_manager",
                        action_taken="session_terminated"
                    )
                
                return True
                
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.LOW,
                session_id=session_id,
                event_details={"error": str(e), "operation": "terminate_session"},
                source_module="session_manager",
                action_taken="session_termination_failed"
            )
            return False
    
    def record_failed_attempt(
        self,
        user_id: str,
        ip_address: str = "unknown",
        reason: str = "invalid_credentials"
    ):
        """Record a failed authentication attempt"""
        try:
            with self.lock:
                # Store in database
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO failed_attempts (user_id, ip_address, attempt_time, reason)
                    VALUES (?, ?, ?, ?)
                """, (user_id, ip_address, datetime.now().isoformat(), reason))
                
                conn.commit()
                conn.close()
                
                # Update in-memory tracking
                key = f"{user_id}_{ip_address}"
                if key not in self.failed_attempts:
                    self.failed_attempts[key] = []
                
                self.failed_attempts[key].append(time.time())
                
                # Clean old attempts (older than lockout duration)
                cutoff_time = time.time() - (self.lockout_duration_minutes * 60)
                self.failed_attempts[key] = [
                    t for t in self.failed_attempts[key] if t > cutoff_time
                ]
                
                # Log failed attempt
                log_security_event(
                    SecurityEventType.LOGIN_FAILURE,
                    ThreatLevel.MEDIUM,
                    user_id=user_id,
                    ip_address=ip_address,
                    event_details={"reason": reason, "attempt_count": len(self.failed_attempts[key])},
                    source_module="session_manager",
                    action_taken="failed_attempt_recorded"
                )
                
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.LOW,
                user_id=user_id,
                ip_address=ip_address,
                event_details={"error": str(e), "operation": "record_failed_attempt"},
                source_module="session_manager",
                action_taken="failed_attempt_recording_failed"
            )
    
    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        # Combine random bytes with timestamp for uniqueness
        random_bytes = secrets.token_bytes(32)
        timestamp = str(time.time()).encode()
        
        # Create hash of combined data
        session_hash = hashlib.sha256(random_bytes + timestamp).hexdigest()
        
        return session_hash
    
    def _is_user_locked_out(self, user_id: str, ip_address: str) -> bool:
        """Check if user is currently locked out"""
        key = f"{user_id}_{ip_address}"
        
        if key not in self.failed_attempts:
            return False
        
        recent_attempts = len(self.failed_attempts[key])
        return recent_attempts >= self.failed_attempt_lockout
    
    def _get_active_sessions_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_sessions 
                WHERE user_id = ? AND is_active = 1 AND expires_at > ?
            """, (user_id, datetime.now().isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception:
            return []
    
    def _store_session(self, session: UserSession, expires_at: datetime):
        """Store session in database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_sessions 
            (session_id, user_id, created_at, last_activity, ip_address, 
             user_agent, is_active, permissions, session_data, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.user_id,
            session.created_at.isoformat(),
            session.last_activity.isoformat(),
            session.ip_address,
            session.user_agent,
            1 if session.is_active else 0,
            json.dumps(session.permissions),
            json.dumps(session.session_data),
            expires_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _load_session(self, session_id: str) -> Optional[UserSession]:
        """Load session from database"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return UserSession(
                session_id=row['session_id'],
                user_id=row['user_id'],
                created_at=datetime.fromisoformat(row['created_at']),
                last_activity=datetime.fromisoformat(row['last_activity']),
                ip_address=row['ip_address'],
                user_agent=row['user_agent'],
                is_active=bool(row['is_active']),
                permissions=json.loads(row['permissions'] or '[]'),
                session_data=json.loads(row['session_data'] or '{}')
            )
            
        except Exception:
            return None
    
    def _is_session_expired(self, session: UserSession) -> bool:
        """Check if session has expired"""
        session_age = datetime.now() - session.last_activity
        return session_age.total_seconds() > (self.session_timeout_minutes * 60)
    
    def _validate_session_security(
        self, 
        session: UserSession, 
        current_ip: str, 
        current_user_agent: str
    ) -> bool:
        """Validate session security constraints"""
        # Check for IP address changes (flag but don't block for now)
        if session.ip_address != current_ip and session.ip_address != "unknown":
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.MEDIUM,
                user_id=session.user_id,
                session_id=session.session_id,
                ip_address=current_ip,
                event_details={
                    "original_ip": session.ip_address,
                    "current_ip": current_ip,
                    "pattern": "ip_address_change"
                },
                source_module="session_manager",
                action_taken="ip_change_detected"
            )
        
        # Check for user agent changes (basic fingerprinting)
        if (session.user_agent and current_user_agent and 
            session.user_agent != current_user_agent):
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.LOW,
                user_id=session.user_id,
                session_id=session.session_id,
                event_details={
                    "pattern": "user_agent_change",
                    "original_agent": session.user_agent[:100],
                    "current_agent": current_user_agent[:100]
                },
                source_module="session_manager",
                action_taken="user_agent_change_detected"
            )
        
        return True  # Don't block for now, just log
    
    def _update_session_activity(self, session: UserSession):
        """Update session last activity in database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions 
                SET last_activity = ?, ip_address = ?
                WHERE session_id = ?
            """, (
                session.last_activity.isoformat(),
                session.ip_address,
                session.session_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            pass  # Non-critical operation
    
    def _deactivate_session(self, session_id: str):
        """Mark session as inactive in database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions SET is_active = 0 WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
            conn.close()
            
        except Exception:
            pass  # Non-critical operation
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions from database and cache"""
        try:
            current_time = datetime.now()
            
            # Clean up database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE expires_at < ? AND is_active = 1
            """, (current_time.isoformat(),))
            
            conn.commit()
            conn.close()
            
            # Clean up cache
            expired_sessions = []
            for session_id, session in self.active_sessions.items():
                if self._is_session_expired(session):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self.terminate_session(session_id, "cleanup_expired")
                
        except Exception as e:
            log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                ThreatLevel.LOW,
                event_details={"error": str(e), "operation": "cleanup_expired_sessions"},
                source_module="session_manager",
                action_taken="cleanup_failed"
            )

# Global session manager instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager