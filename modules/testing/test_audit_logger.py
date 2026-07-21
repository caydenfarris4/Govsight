"""
Unit tests for security audit logger
Tests comprehensive security event logging and threat detection
"""

import pytest
import sys
import os
import tempfile
import sqlite3
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.security.audit_logger import (
    SecurityAuditLogger,
    SecurityEventType,
    ThreatLevel,
    SecurityEvent,
    get_security_logger,
    log_security_event
)

class TestSecurityAuditLogger:
    """Test SecurityAuditLogger class"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_log = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
        self.temp_log.close()
        
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.logger = SecurityAuditLogger(
            log_file=self.temp_log.name,
            db_file=self.temp_db.name
        )
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_log.name):
            os.unlink(self.temp_log.name)
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test that database is properly initialized"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check that security_events table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='security_events'
        """)
        assert cursor.fetchone() is not None
        
        # Check table structure
        cursor.execute("PRAGMA table_info(security_events)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = [
            'id', 'timestamp', 'event_type', 'threat_level', 
            'user_id', 'session_id', 'ip_address', 'user_agent',
            'event_details', 'source_module', 'action_taken', 'created_at'
        ]
        
        for col in expected_columns:
            assert col in columns
        
        conn.close()
    
    def test_log_security_event_success(self):
        """Test successful security event logging"""
        result = self.logger.log_security_event(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            threat_level=ThreatLevel.LOW,
            user_id="test_user",
            session_id="test_session",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            event_details={"login_method": "password"},
            source_module="auth_module",
            action_taken="user_authenticated"
        )
        
        assert result is True
        
        # Verify event was stored in database
        events = self.logger.get_security_events(limit=1)
        assert len(events) == 1
        
        event = events[0]
        assert event['event_type'] == SecurityEventType.LOGIN_SUCCESS.value
        assert event['threat_level'] == ThreatLevel.LOW.value
        assert event['user_id'] == "test_user"
        assert event['session_id'] == "test_session"
        assert event['ip_address'] == "192.168.1.100"
        assert event['event_details']['login_method'] == "password"
    
    def test_log_critical_event(self):
        """Test logging critical security events"""
        with patch.object(self.logger.logger, 'critical') as mock_critical:
            self.logger.log_security_event(
                event_type=SecurityEventType.SQL_INJECTION_ATTEMPT,
                threat_level=ThreatLevel.CRITICAL,
                user_id="attacker",
                event_details={"query": "'; DROP TABLE users; --"},
                source_module="database_module",
                action_taken="query_blocked"
            )
            
            mock_critical.assert_called_once()
    
    def test_threat_counter_updates(self):
        """Test threat counter tracking"""
        user_id = "test_user"
        
        # Log multiple failed login attempts
        for i in range(6):
            self.logger.log_security_event(
                event_type=SecurityEventType.LOGIN_FAILURE,
                threat_level=ThreatLevel.MEDIUM,
                user_id=user_id,
                event_details={"attempt_number": i + 1}
            )
        
        # Check that threat counters are updated
        key = f"{user_id}_{SecurityEventType.LOGIN_FAILURE.value}"
        assert key in self.logger.threat_counters
        assert len(self.logger.threat_counters[key]) == 6
    
    def test_suspicious_pattern_detection(self):
        """Test detection of suspicious activity patterns"""
        user_id = "suspicious_user"
        
        # Simulate rapid failed login attempts
        for i in range(5):
            self.logger.log_security_event(
                event_type=SecurityEventType.LOGIN_FAILURE,
                threat_level=ThreatLevel.MEDIUM,
                user_id=user_id,
                event_details={"attempt": i + 1}
            )
        
        # Check that suspicious activity was logged
        events = self.logger.get_security_events(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY
        )
        
        assert len(events) >= 1
        suspicious_event = events[0]
        assert suspicious_event['event_details']['pattern'] == 'rapid_login_failures'
        assert suspicious_event['event_details']['count'] == 5
    
    def test_sql_injection_pattern_detection(self):
        """Test detection of SQL injection patterns"""
        user_id = "attacker"
        
        # Simulate multiple SQL injection attempts
        for i in range(3):
            self.logger.log_security_event(
                event_type=SecurityEventType.SQL_INJECTION_ATTEMPT,
                threat_level=ThreatLevel.HIGH,
                user_id=user_id,
                event_details={"query": f"malicious_query_{i}"}
            )
        
        # Check that critical suspicious activity was logged
        events = self.logger.get_security_events(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            threat_level=ThreatLevel.CRITICAL
        )
        
        assert len(events) >= 1
        critical_event = events[0]
        assert critical_event['event_details']['pattern'] == 'repeated_sql_injection'
    
    def test_get_security_events_filtering(self):
        """Test filtering of security events"""
        # Log events with different parameters
        test_events = [
            (SecurityEventType.LOGIN_SUCCESS, ThreatLevel.LOW, "user1"),
            (SecurityEventType.LOGIN_FAILURE, ThreatLevel.MEDIUM, "user2"),
            (SecurityEventType.SQL_INJECTION_ATTEMPT, ThreatLevel.HIGH, "user3"),
            (SecurityEventType.UNAUTHORIZED_ACCESS, ThreatLevel.CRITICAL, "user1")
        ]
        
        for event_type, threat_level, user_id in test_events:
            self.logger.log_security_event(
                event_type=event_type,
                threat_level=threat_level,
                user_id=user_id
            )
        
        # Test filtering by event type
        login_events = self.logger.get_security_events(
            event_type=SecurityEventType.LOGIN_SUCCESS
        )
        assert len(login_events) == 1
        assert login_events[0]['event_type'] == SecurityEventType.LOGIN_SUCCESS.value
        
        # Test filtering by user
        user1_events = self.logger.get_security_events(user_id="user1")
        assert len(user1_events) == 2
        
        # Test filtering by threat level
        critical_events = self.logger.get_security_events(
            threat_level=ThreatLevel.CRITICAL
        )
        assert len(critical_events) >= 1
    
    def test_generate_security_report(self):
        """Test security report generation"""
        # Log various events
        test_events = [
            (SecurityEventType.LOGIN_SUCCESS, ThreatLevel.LOW, "user1"),
            (SecurityEventType.LOGIN_FAILURE, ThreatLevel.MEDIUM, "user2"),
            (SecurityEventType.SQL_INJECTION_ATTEMPT, ThreatLevel.HIGH, "attacker"),
            (SecurityEventType.UNAUTHORIZED_ACCESS, ThreatLevel.CRITICAL, "user3")
        ]
        
        for event_type, threat_level, user_id in test_events:
            self.logger.log_security_event(
                event_type=event_type,
                threat_level=threat_level,
                user_id=user_id,
                event_details={"test": True}
            )
        
        # Generate report
        report = self.logger.generate_security_report(hours=24)
        
        # Verify report structure
        assert 'report_period' in report
        assert 'total_events' in report
        assert 'events_by_type' in report
        assert 'events_by_threat_level' in report
        assert 'events_by_user' in report
        assert 'top_threats' in report
        
        # Verify report content
        assert report['total_events'] >= 4
        assert SecurityEventType.LOGIN_SUCCESS.value in report['events_by_type']
        assert ThreatLevel.CRITICAL.value in report['events_by_threat_level']
        assert 'user1' in report['events_by_user']


class TestGlobalSecurityLogger:
    """Test global security logger functions"""
    
    def test_get_security_logger_singleton(self):
        """Test that get_security_logger returns singleton"""
        logger1 = get_security_logger()
        logger2 = get_security_logger()
        
        assert logger1 is logger2
        assert isinstance(logger1, SecurityAuditLogger)
    
    @patch('modules.security.audit_logger.get_security_logger')
    def test_log_security_event_convenience_function(self, mock_get_logger):
        """Test convenience function for logging events"""
        mock_logger = Mock()
        mock_logger.log_security_event.return_value = True
        mock_get_logger.return_value = mock_logger
        
        result = log_security_event(
            SecurityEventType.LOGIN_SUCCESS,
            ThreatLevel.LOW,
            user_id="test_user"
        )
        
        assert result is True
        mock_logger.log_security_event.assert_called_once_with(
            SecurityEventType.LOGIN_SUCCESS,
            ThreatLevel.LOW,
            "test_user",
            "",
            "unknown",
            "",
            None,
            "",
            ""
        )


class TestSecurityEventTypes:
    """Test security event type enumeration"""
    
    def test_security_event_types_exist(self):
        """Test that all required security event types exist"""
        required_types = [
            'LOGIN_SUCCESS', 'LOGIN_FAILURE', 'SQL_INJECTION_ATTEMPT',
            'XSS_ATTEMPT', 'UNAUTHORIZED_ACCESS', 'DATA_EXPORT',
            'ADMIN_ACTION', 'SESSION_CREATION', 'SESSION_EXPIRY',
            'PASSWORD_CHANGE', 'FAILED_AUTHORIZATION', 'SUSPICIOUS_ACTIVITY'
        ]
        
        for event_type in required_types:
            assert hasattr(SecurityEventType, event_type)
            assert isinstance(getattr(SecurityEventType, event_type), SecurityEventType)
    
    def test_threat_levels_exist(self):
        """Test that all threat levels exist"""
        required_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        for level in required_levels:
            assert hasattr(ThreatLevel, level)
            assert isinstance(getattr(ThreatLevel, level), ThreatLevel)


class TestSecurityEventDataClass:
    """Test SecurityEvent data class"""
    
    def test_security_event_creation(self):
        """Test creating SecurityEvent instance"""
        event = SecurityEvent(
            timestamp="2024-01-01T12:00:00",
            event_type=SecurityEventType.LOGIN_SUCCESS,
            threat_level=ThreatLevel.LOW,
            user_id="test_user",
            session_id="test_session",
            ip_address="192.168.1.1",
            user_agent="TestAgent",
            event_details={"test": True},
            source_module="test_module",
            action_taken="test_action"
        )
        
        assert event.timestamp == "2024-01-01T12:00:00"
        assert event.event_type == SecurityEventType.LOGIN_SUCCESS
        assert event.threat_level == ThreatLevel.LOW
        assert event.user_id == "test_user"
        assert event.event_details == {"test": True}
    
    def test_security_event_to_dict(self):
        """Test converting SecurityEvent to dictionary"""
        event = SecurityEvent(
            timestamp="2024-01-01T12:00:00",
            event_type=SecurityEventType.LOGIN_SUCCESS,
            threat_level=ThreatLevel.LOW,
            user_id="test_user",
            session_id="test_session",
            ip_address="192.168.1.1",
            user_agent="TestAgent",
            event_details={"test": True},
            source_module="test_module",
            action_taken="test_action"
        )
        
        event_dict = asdict(event)
        assert isinstance(event_dict, dict)
        assert event_dict['timestamp'] == "2024-01-01T12:00:00"
        assert event_dict['user_id'] == "test_user"


if __name__ == "__main__":
    pytest.main(["-v", __file__])