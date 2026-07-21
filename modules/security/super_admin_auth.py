"""
Super Admin Authentication System
Provides exclusive control over database configuration to system owner
"""

import streamlit as st
import hashlib
import hmac
from datetime import datetime, timedelta
import json
import os
from typing import Optional, Tuple
import sqlite3
from pathlib import Path


class SuperAdminAuth:
    """Super Admin authentication and authorization system"""
    
    # Super Admin access levels
    SUPER_ADMIN = "super_admin"
    CITY_ADMIN = "city_admin"
    USER = "user"
    
    def __init__(self):
        self.session_timeout = 30  # minutes
        self._init_auth_storage()
    
    def _init_auth_storage(self):
        """Initialize authentication storage"""
        db_path = Path("databases/core")
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.auth_db = db_path / "super_admin_auth.db"
        
        with sqlite3.connect(self.auth_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS super_admin_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP,
                    ip_address TEXT,
                    expires_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_attempts (
                    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    success BOOLEAN,
                    reason TEXT
                )
            """)
            
            conn.commit()
    
    def _get_expected_master_key_hash(self) -> Optional[str]:
        """Get expected master key hash from ADMIN_PASSWORD secret"""
        # Use the ADMIN_PASSWORD secret for super admin authentication
        try:
            from modules.security.secret_manager import get_secret
            admin_password = get_secret("ADMIN_PASSWORD")
            
            if admin_password:
                # Return the hash of the ADMIN_PASSWORD for comparison
                return hashlib.sha256(admin_password.encode()).hexdigest()
            
        except ImportError:
            # Fallback if secret_manager not available
            pass
        
        # Fallback to environment variable if secret not available
        if os.environ.get('ADMIN_PASSWORD'):
            key = os.environ.get('ADMIN_PASSWORD')
            return hashlib.sha256(key.encode()).hexdigest()
        
        # Development-only default
        # Check if we're in development mode
        dev_mode = os.environ.get('GOVSIGHT_DEV_MODE', 'true').lower() == 'true'
        
        if dev_mode:
            st.warning("ADMIN_PASSWORD secret not configured. Super admin functions require this secret.")
            # No default for super admin - must have the secret configured
            return None
        
        # No valid configuration found
        return None
    
    def verify_super_admin(self, master_key: str) -> Tuple[bool, str]:
        """Verify super admin credentials"""
        # Get expected hash from configured sources
        expected_hash = self._get_expected_master_key_hash()
        
        if not expected_hash:
            st.error("Super Admin authentication not configured. Please set up authentication.")
            self._log_access_attempt(False, "No authentication configured")
            return False, "Super Admin authentication not configured"
        
        # Hash the provided key
        provided_hash = hashlib.sha256(master_key.encode()).hexdigest()
        
        # Secure comparison
        if hmac.compare_digest(provided_hash, expected_hash):
            # Create session
            session_id = self._create_super_session()
            return True, session_id
        else:
            # Log failed attempt
            self._log_access_attempt(False, "Invalid master key")
            return False, "Invalid Super Admin credentials"
    
    def _create_super_session(self) -> str:
        """Create a new super admin session"""
        session_id = hashlib.md5(f"{datetime.now()}_{os.urandom(16)}".encode()).hexdigest()
        expires_at = datetime.now() + timedelta(minutes=self.session_timeout)
        
        # Store in session state
        st.session_state['super_admin_session'] = {
            'id': session_id,
            'created': datetime.now(),
            'expires': expires_at,
            'level': self.SUPER_ADMIN
        }
        
        # Store in database
        with sqlite3.connect(self.auth_db) as conn:
            conn.execute("""
                INSERT INTO super_admin_sessions 
                (session_id, last_activity, expires_at)
                VALUES (?, ?, ?)
            """, (session_id, datetime.now(), expires_at))
            conn.commit()
        
        # Log successful access
        self._log_access_attempt(True, "Super Admin authenticated")
        
        return session_id
    
    def is_super_admin(self) -> bool:
        """Check if current session is super admin"""
        if 'super_admin_session' not in st.session_state:
            return False
        
        session = st.session_state['super_admin_session']
        
        # Check expiration
        if datetime.now() > session['expires']:
            self.logout_super_admin()
            return False
        
        # Update last activity
        self._update_session_activity(session['id'])
        
        return session['level'] == self.SUPER_ADMIN
    
    def require_super_admin(self) -> bool:
        """Decorator/check that requires super admin access"""
        if not self.is_super_admin():
            st.error("🔒 This operation requires Super Admin access")
            st.stop()
            return False
        return True
    
    def _update_session_activity(self, session_id: str):
        """Update session last activity time"""
        new_expiry = datetime.now() + timedelta(minutes=self.session_timeout)
        
        # Update session state
        if 'super_admin_session' in st.session_state:
            st.session_state['super_admin_session']['expires'] = new_expiry
        
        # Update database
        with sqlite3.connect(self.auth_db) as conn:
            conn.execute("""
                UPDATE super_admin_sessions 
                SET last_activity = ?, expires_at = ?
                WHERE session_id = ?
            """, (datetime.now(), new_expiry, session_id))
            conn.commit()
    
    def logout_super_admin(self):
        """Logout super admin"""
        if 'super_admin_session' in st.session_state:
            session_id = st.session_state['super_admin_session']['id']
            
            # Remove from database
            with sqlite3.connect(self.auth_db) as conn:
                conn.execute("DELETE FROM super_admin_sessions WHERE session_id = ?", (session_id,))
                conn.commit()
            
            # Clear session
            del st.session_state['super_admin_session']
            
            self._log_access_attempt(True, "Super Admin logged out")
    
    def _log_access_attempt(self, success: bool, reason: str):
        """Log access attempt"""
        with sqlite3.connect(self.auth_db) as conn:
            conn.execute("""
                INSERT INTO access_attempts (success, reason)
                VALUES (?, ?)
            """, (success, reason))
            conn.commit()
    
    def get_user_level(self) -> str:
        """Get current user's access level"""
        if self.is_super_admin():
            return self.SUPER_ADMIN
        elif st.session_state.get('is_admin', False):
            return self.CITY_ADMIN
        else:
            return self.USER
    
    def can_modify_databases(self) -> bool:
        """Check if user can modify database configurations"""
        return self.is_super_admin()
    
    def can_select_live_databases(self) -> bool:
        """Check if user can select which databases are live"""
        level = self.get_user_level()
        return level in [self.SUPER_ADMIN, self.CITY_ADMIN]
    
    def can_view_connections(self) -> bool:
        """Check if user can view connection information"""
        level = self.get_user_level()
        return level in [self.SUPER_ADMIN, self.CITY_ADMIN]


# Global instance
_super_auth = None

def get_super_auth() -> SuperAdminAuth:
    """Get the global super admin auth instance"""
    global _super_auth
    if _super_auth is None:
        _super_auth = SuperAdminAuth()
    return _super_auth


def render_super_admin_login():
    """Render super admin login interface"""
    st.markdown("### 🔐 Super Admin Authentication")
    st.info("This area requires the ADMIN_PASSWORD secret to manage critical system configurations.")
    
    with st.form("super_admin_login"):
        master_key = st.text_input("Admin Password", type="password", 
                                   help="Enter the ADMIN_PASSWORD secret (not your regular login password)")
        
        submitted = st.form_submit_button("Authenticate", type="primary")
        
        if submitted:
            if master_key:
                auth = get_super_auth()
                success, result = auth.verify_super_admin(master_key)
                
                if success:
                    st.success("✅ Super Admin authenticated successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Authentication failed: {result}")
            else:
                st.error("Please enter the admin password")
    
    st.markdown("---")
    st.caption("Super Admin access is restricted to system administrators with the ADMIN_PASSWORD secret.")
    st.caption("All access attempts are logged for security purposes.")