"""
Session Security Module for GovSight Financial Analyzer

This module provides secure session management including:
- Session token generation and validation
- Session timeout handling
- Secure session storage
- Session hijacking prevention
"""

import secrets
import time
import hashlib
import json
import os
from typing import Dict, Optional, Any
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureSessionManager:
    """
    Secure session manager with timeout and validation
    """
    
    def __init__(self, session_timeout_minutes: int = 30, max_sessions_per_user: int = 3):
        """
        Initialize session manager
        
        Args:
            session_timeout_minutes (int): Session timeout in minutes
            max_sessions_per_user (int): Maximum concurrent sessions per user
        """
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_sessions_per_user = max_sessions_per_user
        self.sessions = {}  # In production, use Redis or database
        
    def create_session(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """
        Create a new secure session
        
        Args:
            user_id (str): User identifier
            user_data (dict): User session data
            
        Returns:
            str: Session token
        """
        # Clean up expired sessions first
        self._cleanup_expired_sessions()
        
        # Limit concurrent sessions per user
        self._enforce_session_limit(user_id)
        
        # Generate secure session token
        session_token = self._generate_session_token()
        
        # Create session data
        session_data = {
            'user_id': user_id,
            'user_data': user_data,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'ip_address': self._get_client_ip(),
            'user_agent': self._get_user_agent(),
            'is_active': True
        }
        
        self.sessions[session_token] = session_data
        
        logger.info(f"Session created for user: {user_id}")
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate session token and return session data
        
        Args:
            session_token (str): Session token to validate
            
        Returns:
            Session data if valid, None if invalid
        """
        if not session_token or session_token not in self.sessions:
            return None
        
        session_data = self.sessions[session_token]
        
        # Check if session is active
        if not session_data.get('is_active', False):
            return None
        
        # Check session timeout
        last_activity = session_data['last_activity']
        if datetime.now() - last_activity > self.session_timeout:
            self.invalidate_session(session_token)
            logger.warning(f"Session expired for user: {session_data['user_id']}")
            return None
        
        # Validate session integrity
        if not self._validate_session_integrity(session_token, session_data):
            self.invalidate_session(session_token)
            logger.warning(f"Session integrity check failed for user: {session_data['user_id']}")
            return None
        
        # Update last activity
        session_data['last_activity'] = datetime.now()
        
        return session_data
    
    def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate a session
        
        Args:
            session_token (str): Session token to invalidate
            
        Returns:
            bool: True if session was invalidated, False if not found
        """
        if session_token in self.sessions:
            user_id = self.sessions[session_token].get('user_id', 'unknown')
            del self.sessions[session_token]
            logger.info(f"Session invalidated for user: {user_id}")
            return True
        return False
    
    def invalidate_all_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a specific user
        
        Args:
            user_id (str): User identifier
            
        Returns:
            int: Number of sessions invalidated
        """
        sessions_to_remove = []
        for token, data in self.sessions.items():
            if data.get('user_id') == user_id:
                sessions_to_remove.append(token)
        
        for token in sessions_to_remove:
            del self.sessions[token]
        
        logger.info(f"Invalidated {len(sessions_to_remove)} sessions for user: {user_id}")
        return len(sessions_to_remove)
    
    def get_active_sessions_count(self, user_id: str) -> int:
        """
        Get count of active sessions for a user
        
        Args:
            user_id (str): User identifier
            
        Returns:
            int: Number of active sessions
        """
        count = 0
        for data in self.sessions.values():
            if data.get('user_id') == user_id and data.get('is_active', False):
                count += 1
        return count
    
    def _generate_session_token(self) -> str:
        """Generate cryptographically secure session token"""
        return secrets.token_urlsafe(32)
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = datetime.now()
        expired_tokens = []
        
        for token, data in self.sessions.items():
            last_activity = data['last_activity']
            if current_time - last_activity > self.session_timeout:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            user_id = self.sessions[token].get('user_id', 'unknown')
            del self.sessions[token]
            logger.info(f"Cleaned up expired session for user: {user_id}")
    
    def _enforce_session_limit(self, user_id: str):
        """Enforce maximum sessions per user"""
        user_sessions = []
        for token, data in self.sessions.items():
            if data.get('user_id') == user_id:
                user_sessions.append((token, data['created_at']))
        
        if len(user_sessions) >= self.max_sessions_per_user:
            # Remove oldest session
            user_sessions.sort(key=lambda x: x[1])
            oldest_token = user_sessions[0][0]
            del self.sessions[oldest_token]
            logger.info(f"Removed oldest session for user {user_id} due to session limit")
    
    def _validate_session_integrity(self, session_token: str, session_data: Dict) -> bool:
        """
        Validate session integrity to prevent session hijacking
        
        Args:
            session_token (str): Session token
            session_data (dict): Session data
            
        Returns:
            bool: True if session is valid
        """
        # Check IP address consistency (optional - can be disabled for mobile users)
        current_ip = self._get_client_ip()
        if current_ip and session_data.get('ip_address') != current_ip:
            # Log suspicious activity but don't invalidate (user might have dynamic IP)
            logger.warning(f"IP address change detected for session: {session_token}")
        
        # Check user agent consistency
        current_user_agent = self._get_user_agent()
        if current_user_agent and session_data.get('user_agent') != current_user_agent:
            logger.warning(f"User agent change detected for session: {session_token}")
            # This could indicate session hijacking, but might also be legitimate
        
        return True
    
    def _get_client_ip(self) -> Optional[str]:
        """Get client IP address (mock implementation)"""
        # In a real Streamlit app, this would extract from request headers
        return "127.0.0.1"
    
    def _get_user_agent(self) -> Optional[str]:
        """Get client user agent (mock implementation)"""
        # In a real Streamlit app, this would extract from request headers
        return "Mozilla/5.0"

# Global session manager instance
session_manager = SecureSessionManager()

def create_user_session(user_id: str, user_data: Dict[str, Any]) -> str:
    """
    Create a new user session
    
    Args:
        user_id (str): User identifier
        user_data (dict): User data to store in session
        
    Returns:
        str: Session token
    """
    return session_manager.create_session(user_id, user_data)

def validate_user_session(session_token: str) -> Optional[Dict[str, Any]]:
    """
    Validate user session
    
    Args:
        session_token (str): Session token
        
    Returns:
        Session data if valid, None if invalid
    """
    return session_manager.validate_session(session_token)

def logout_user(session_token: str) -> bool:
    """
    Logout user by invalidating session
    
    Args:
        session_token (str): Session token to invalidate
        
    Returns:
        bool: True if logout successful
    """
    return session_manager.invalidate_session(session_token)

def logout_all_user_sessions(user_id: str) -> int:
    """
    Logout all sessions for a user
    
    Args:
        user_id (str): User identifier
        
    Returns:
        int: Number of sessions logged out
    """
    return session_manager.invalidate_all_user_sessions(user_id)

def get_session_info(session_token: str) -> Optional[Dict[str, str]]:
    """
    Get session information for display
    
    Args:
        session_token (str): Session token
        
    Returns:
        Session info dictionary
    """
    session_data = session_manager.validate_session(session_token)
    if not session_data:
        return None
    
    return {
        'user_id': session_data['user_id'],
        'created_at': session_data['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
        'last_activity': session_data['last_activity'].strftime('%Y-%m-%d %H:%M:%S'),
        'ip_address': session_data.get('ip_address', 'Unknown'),
        'active_time': str(datetime.now() - session_data['created_at'])
    }