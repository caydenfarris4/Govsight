"""
Unit tests for session manager
Tests secure session management and authentication controls
"""

import pytest
import sys
import os
import tempfile
import sqlite3
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.security.session_manager import (
    SessionManager,
    UserSession,
    get_session_manager
)

class TestSessionManager:
    """Test SessionManager class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.session_manager = SessionManager(
            db_file=self.temp_db.name,
            max_session_age=3600
        )
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test that session database is properly initialized"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check that user_sessions table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_sessions'
        """)
        assert cursor.fetchone() is not None
        
        # Check that failed_attempts table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='failed_attempts'
        """)
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_create_session_success(self):
        """Test successful session creation"""
        session_id = self.session_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            permissions=["read", "write"],
            session_data={"role": "admin"}
        )
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) == 64  # SHA256 hash length
        
        # Verify session is stored
        assert session_id in self.session_manager.active_sessions
        
        session = self.session_manager.active_sessions[session_id]
        assert session.user_id == "test_user"
        assert session.ip_address == "192.168.1.100"
        assert session.permissions == ["read", "write"]
        assert session.session_data == {"role": "admin"}
        assert session.is_active is True
    
    def test_create_session_concurrent_limit(self):
        """Test concurrent session limit enforcement"""
        user_id = "test_user"
        session_ids = []
        
        # Create sessions up to the limit
        for i in range(self.session_manager.max_concurrent_sessions + 1):
            session_id = self.session_manager.create_session(
                user_id=user_id,
                ip_address=f"192.168.1.{100 + i}"
            )
            assert session_id is not None
            session_ids.append(session_id)
        
        # Verify only max_concurrent_sessions are active
        active_sessions = self.session_manager._get_active_sessions_for_user(user_id)
        assert len(active_sessions) == self.session_manager.max_concurrent_sessions
        
        # First session should have been terminated
        assert session_ids[0] not in self.session_manager.active_sessions
    
    def test_validate_session_success(self):
        """Test successful session validation"""
        # Create session
        session_id = self.session_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0"
        )
        
        # Validate session
        session = self.session_manager.validate_session(
            session_id=session_id,
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0"
        )
        
        assert session is not None
        assert isinstance(session, UserSession)
        assert session.user_id == "test_user"
        assert session.is_active is True
    
    def test_validate_session_invalid_id(self):
        """Test validation with invalid session ID"""
        session = self.session_manager.validate_session(
            session_id="invalid_session_id",
            ip_address="192.168.1.100"
        )
        
        assert session is None
    
    def test_validate_session_expired(self):
        """Test validation of expired session"""
        # Create session with short timeout
        self.session_manager.session_timeout_minutes = 0.01  # 0.6 seconds
        
        session_id = self.session_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100"
        )
        
        # Wait for session to expire
        time.sleep(1)
        
        # Validate expired session
        session = self.session_manager.validate_session(
            session_id=session_id,
            ip_address="192.168.1.100"
        )
        
        assert session is None
        assert session_id not in self.session_manager.active_sessions
    
    def test_terminate_session_success(self):
        """Test successful session termination"""
        # Create session
        session_id = self.session_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100"
        )
        
        # Terminate session
        result = self.session_manager.terminate_session(
            session_id=session_id,
            reason="user_logout"
        )
        
        assert result is True
        assert session_id not in self.session_manager.active_sessions
        
        # Verify session is marked inactive in database
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT is_active FROM user_sessions WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 0  # is_active = False
        conn.close()
    
    def test_record_failed_attempt(self):
        """Test recording failed authentication attempts"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        
        # Record failed attempt
        self.session_manager.record_failed_attempt(
            user_id=user_id,
            ip_address=ip_address,
            reason="invalid_password"
        )
        
        # Verify attempt is recorded in database
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM failed_attempts 
            WHERE user_id = ? AND ip_address = ?
        """, (user_id, ip_address))
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()
        
        # Verify in-memory tracking
        key = f"{user_id}_{ip_address}"
        assert key in self.session_manager.failed_attempts
        assert len(self.session_manager.failed_attempts[key]) == 1
    
    def test_user_lockout_mechanism(self):
        """Test user lockout after multiple failed attempts"""
        user_id = "test_user"
        ip_address = "192.168.1.100"
        
        # Record multiple failed attempts
        for i in range(self.session_manager.failed_attempt_lockout):
            self.session_manager.record_failed_attempt(
                user_id=user_id,
                ip_address=ip_address,
                reason=f"attempt_{i}"
            )
        
        # Verify user is locked out
        assert self.session_manager._is_user_locked_out(user_id, ip_address) is True
        
        # Attempt to create session should fail
        session_id = self.session_manager.create_session(
            user_id=user_id,
            ip_address=ip_address
        )
        assert session_id is None
    
    def test_session_id_generation_uniqueness(self):
        """Test that session IDs are unique"""
        session_ids = set()
        
        for i in range(100):
            session_id = self.session_manager._generate_session_id()
            assert session_id not in session_ids
            session_ids.add(session_id)
            assert len(session_id) == 64  # SHA256 hash
    
    def test_session_security_validation_ip_change(self):
        """Test security validation with IP address change"""
        # Create session
        session_id = self.session_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100"
        )
        
        # Validate with different IP (should still work but log warning)
        with patch('modules.security.session_manager.log_security_event') as mock_log:
            session = self.session_manager.validate_session(
                session_id=session_id,
                ip_address="192.168.1.200"  # Different IP
            )
            
            assert session is not None  # Should still validate
            mock_log.assert_called()  # Should log suspicious activity
    
    def test_session_activity_update(self):
        """Test that session activity is updated on validation"""
        # Create session
        session_id = self.session_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100"
        )
        
        original_session = self.session_manager.active_sessions[session_id]
        original_activity = original_session.last_activity
        
        # Wait a moment and validate
        time.sleep(0.1)
        session = self.session_manager.validate_session(
            session_id=session_id,
            ip_address="192.168.1.100"
        )
        
        assert session is not None
        assert session.last_activity > original_activity
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        # Create session with very short timeout
        original_timeout = self.session_manager.session_timeout_minutes
        self.session_manager.session_timeout_minutes = 0.01  # 0.6 seconds
        
        session_id = self.session_manager.create_session(
            user_id="test_user",
            ip_address="192.168.1.100"
        )
        
        # Wait for expiry
        time.sleep(1)
        
        # Run cleanup
        self.session_manager._cleanup_expired_sessions()
        
        # Verify session is cleaned up
        assert session_id not in self.session_manager.active_sessions
        
        # Restore timeout
        self.session_manager.session_timeout_minutes = original_timeout
    
    def test_get_active_sessions_for_user(self):
        """Test retrieving active sessions for a user"""
        user_id = "test_user"
        
        # Create multiple sessions
        session_ids = []
        for i in range(2):
            session_id = self.session_manager.create_session(
                user_id=user_id,
                ip_address=f"192.168.1.{100 + i}"
            )
            session_ids.append(session_id)
        
        # Get active sessions
        active_sessions = self.session_manager._get_active_sessions_for_user(user_id)
        
        assert len(active_sessions) == 2
        active_session_ids = [s['session_id'] for s in active_sessions]
        for session_id in session_ids:
            assert session_id in active_session_ids


class TestUserSessionDataClass:
    """Test UserSession data class"""
    
    def test_user_session_creation(self):
        """Test creating UserSession instance"""
        created_at = datetime.now()
        
        session = UserSession(
            session_id="test_session_id",
            user_id="test_user",
            created_at=created_at,
            last_activity=created_at,
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            is_active=True,
            permissions=["read", "write"],
            session_data={"role": "admin"}
        )
        
        assert session.session_id == "test_session_id"
        assert session.user_id == "test_user"
        assert session.created_at == created_at
        assert session.is_active is True
        assert session.permissions == ["read", "write"]
        assert session.session_data == {"role": "admin"}


class TestGlobalSessionManager:
    """Test global session manager function"""
    
    def test_get_session_manager_singleton(self):
        """Test that get_session_manager returns singleton"""
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, SessionManager)


if __name__ == "__main__":
    pytest.main(["-v", __file__])