"""
Anti-Scraping Protection Module for GovSight Financial Analyzer

This module provides protection against automated scraping, bot attacks,
and unauthorized data extraction from the municipal financial system.

SECURITY DECISIONS:
1. Rate limiting by IP and session to prevent automated requests
2. Request pattern analysis to detect scraping behavior
3. Security headers to prevent content extraction
4. Bot detection through behavioral analysis
"""

import streamlit as st
import time
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AntiScrapingManager:
    """Manages anti-scraping protection for the application"""
    
    def __init__(self):
        self.rate_limits = {}
        self.request_patterns = {}
        self.blocked_ips = set()
        self.suspicious_activity = {}
    
    def add_security_headers(self):
        """Add security headers to prevent content extraction"""
        st.markdown("""
        <script>
        // Disable right-click context menu
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
        });
        
        // Disable text selection for sensitive areas
        document.addEventListener('selectstart', function(e) {
            if (e.target.closest('.sensitive-data')) {
                e.preventDefault();
            }
        });
        
        // Disable F12 and inspect shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.key === 'F12' || 
                (e.ctrlKey && e.shiftKey && e.key === 'I') ||
                (e.ctrlKey && e.shiftKey && e.key === 'C') ||
                (e.ctrlKey && e.key === 'u')) {
                e.preventDefault();
            }
        });
        
        // Add anti-scraping metadata
        document.querySelector('meta[name="robots"]') || 
        document.head.appendChild(Object.assign(document.createElement('meta'), {
            name: 'robots',
            content: 'noindex, nofollow, noarchive, nosnippet, notranslate'
        }));
        </script>
        """, unsafe_allow_html=True)
    
    def check_rate_limit(self, identifier: str, max_requests: int = 60, time_window: int = 60) -> bool:
        """
        Check if request is within rate limits
        
        Args:
            identifier: Unique identifier (IP, session, etc.)
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
            
        Returns:
            bool: True if within limits, False if exceeded
        """
        current_time = time.time()
        
        # Initialize or clean old entries
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Remove old requests outside time window
        self.rate_limits[identifier] = [
            req_time for req_time in self.rate_limits[identifier]
            if current_time - req_time < time_window
        ]
        
        # Check if limit exceeded
        if len(self.rate_limits[identifier]) >= max_requests:
            self.log_security_event(
                "RATE_LIMIT_EXCEEDED",
                f"Rate limit exceeded for {identifier}: {len(self.rate_limits[identifier])} requests in {time_window}s"
            )
            return False
        
        # Add current request
        self.rate_limits[identifier].append(current_time)
        return True
    
    def detect_scraping_behavior(self, user_session: Dict) -> bool:
        """
        Detect potential scraping behavior patterns
        
        Args:
            user_session: Session data including page views, timing, etc.
            
        Returns:
            bool: True if suspicious behavior detected
        """
        session_id = user_session.get('session_id', 'unknown')
        
        # Track request patterns
        if session_id not in self.request_patterns:
            self.request_patterns[session_id] = {
                'requests': [],
                'pages_visited': set(),
                'user_agent': user_session.get('user_agent', ''),
                'first_seen': datetime.now()
            }
        
        pattern = self.request_patterns[session_id]
        pattern['requests'].append(datetime.now())
        pattern['pages_visited'].add(user_session.get('current_page', ''))
        
        # Analyze for suspicious patterns
        recent_requests = [
            req for req in pattern['requests']
            if datetime.now() - req < timedelta(minutes=5)
        ]
        
        # Too many requests in short time - increased limit for simulation activities
        # Check if user is authenticated (less strict for logged-in users)
        is_authenticated = hasattr(st.session_state, 'user') and st.session_state.user is not None
        
        # Higher limits for authenticated users doing legitimate work
        rate_limit = 100 if is_authenticated else 30  # 100 requests for auth users, 30 for anonymous
        
        if len(recent_requests) > rate_limit:
            self.log_security_event(
                "SUSPICIOUS_RAPID_REQUESTS",
                f"Session {session_id}: {len(recent_requests)} requests in 5 minutes (limit: {rate_limit})"
            )
            return True
        
        # Too many different pages visited quickly - more lenient for authenticated users
        page_limit = 25 if is_authenticated else 10
        request_limit = 60 if is_authenticated else 20
        
        if len(pattern['pages_visited']) > page_limit and len(recent_requests) > request_limit:
            self.log_security_event(
                "SUSPICIOUS_PAGE_CRAWLING",
                f"Session {session_id}: {len(pattern['pages_visited'])} pages visited with {len(recent_requests)} recent requests"
            )
            return True
        
        # Suspicious user agent patterns
        suspicious_agents = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python',
            'requests', 'scrapy', 'selenium', 'headless'
        ]
        
        user_agent = pattern['user_agent'].lower()
        if any(agent in user_agent for agent in suspicious_agents):
            self.log_security_event(
                "SUSPICIOUS_USER_AGENT",
                f"Session {session_id}: Suspicious user agent: {user_agent}"
            )
            return True
        
        return False
    
    def apply_content_protection(self, content: str, sensitive: bool = False) -> str:
        """
        Apply content protection measures
        
        Args:
            content: HTML content to protect
            sensitive: Whether content contains sensitive data
            
        Returns:
            str: Protected content
        """
        if sensitive:
            # Add obfuscation for sensitive data
            protected_content = f"""
            <div class="sensitive-data" style="
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
                -webkit-touch-callout: none;
                -webkit-tap-highlight-color: transparent;
            ">
                {content}
            </div>
            """
            return protected_content
        
        return content
    
    def log_security_event(self, event_type: str, description: str):
        """Log security events for monitoring"""
        timestamp = datetime.now().isoformat()
        logger.warning(f"SECURITY_EVENT: {event_type} - {description} at {timestamp}")
        
        # Store in session for admin review
        if 'security_events' not in st.session_state:
            st.session_state.security_events = []
        
        st.session_state.security_events.append({
            'timestamp': timestamp,
            'event_type': event_type,
            'description': description
        })
    
    def get_client_fingerprint(self) -> str:
        """Generate client fingerprint for tracking"""
        # Use available Streamlit session info
        fingerprint_data = {
            'session_id': st.session_state.get('session_id', ''),
            'user_agent': st.session_state.get('user_agent', ''),
            'timestamp': str(int(time.time() / 3600))  # Hour-based to prevent exact tracking
        }
        
        fingerprint_string = str(fingerprint_data)
        return hashlib.md5(fingerprint_string.encode()).hexdigest()[:16]

# Global instance
anti_scraping_manager = AntiScrapingManager()

def protect_page(page_name: str, sensitive: bool = False):
    """
    Decorator/function to protect a page from scraping
    
    Args:
        page_name: Name of the page being protected
        sensitive: Whether page contains sensitive financial data
    """
    # Allow authenticated users to navigate freely between modules
    module_pages = ['navi', 'mantis', 'vatica', 'dashboard', 'scenario', 'simulation', 'chart', 'graph', 'admin']
    is_authenticated = hasattr(st.session_state, 'user') and st.session_state.user is not None
    
    # For authenticated users navigating between legitimate modules, use relaxed rate limiting
    if is_authenticated and any(module in page_name.lower() for module in module_pages):
        # Apply very relaxed rate limiting (300 requests per minute for authenticated module navigation)
        client_id = anti_scraping_manager.get_client_fingerprint()
        if not anti_scraping_manager.check_rate_limit(client_id, max_requests=300, time_window=60):
            # For authenticated users, just show a brief warning without stopping
            st.warning("Please slow down navigation slightly.")
            time.sleep(1)
            return
    else:
        # Full protection for unauthenticated users and non-module pages
        client_id = anti_scraping_manager.get_client_fingerprint()
        
        # Check rate limits
        if not anti_scraping_manager.check_rate_limit(client_id):
            st.error("Too many requests. Please wait before continuing.")
            st.stop()
    
    # Check for suspicious behavior (but don't block authenticated simulation users)
    user_session = {
        'session_id': client_id if 'client_id' in locals() else anti_scraping_manager.get_client_fingerprint(),
        'current_page': page_name,
        'user_agent': st.session_state.get('user_agent', ''),
        'timestamp': datetime.now()
    }
    
    if anti_scraping_manager.detect_scraping_behavior(user_session):
        st.error("Suspicious activity detected. Access temporarily restricted.")
        st.stop()
    
    # Apply security headers
    anti_scraping_manager.add_security_headers()
    
    # Add content protection CSS
    if sensitive:
        st.markdown("""
        <style>
        .sensitive-data {
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
            -webkit-touch-callout: none;
            -webkit-tap-highlight-color: transparent;
        }
        </style>
        """, unsafe_allow_html=True)

def protect_sensitive_content(content: str) -> str:
    """
    Protect sensitive content from extraction
    
    Args:
        content: Content to protect
        
    Returns:
        str: Protected content
    """
    return anti_scraping_manager.apply_content_protection(content, sensitive=True)

def get_security_events() -> List[Dict]:
    """Get recent security events for admin review"""
    return st.session_state.get('security_events', [])