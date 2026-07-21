"""
Content Protection Module

Advanced protection for sensitive financial data display
including watermarking, obfuscation, and access logging.
"""

import streamlit as st
import hashlib
import base64
from datetime import datetime
import json
from typing import Dict, List, Optional

class ContentProtector:
    """Protects sensitive financial content from unauthorized extraction"""
    
    def __init__(self):
        self.access_log = []
        self.watermark_enabled = True
    
    def create_watermarked_content(self, content: str, user_id: str) -> str:
        """
        Add invisible watermark to content for tracking
        
        Args:
            content: Original content
            user_id: User identifier
            
        Returns:
            str: Watermarked content
        """
        timestamp = datetime.now().isoformat()
        watermark_data = {
            'user': user_id,
            'timestamp': timestamp,
            'session': st.session_state.get('session_id', 'unknown')
        }
        
        # Create invisible watermark
        watermark_json = json.dumps(watermark_data)
        watermark_encoded = base64.b64encode(watermark_json.encode()).decode()
        
        watermarked_content = f"""
        <div data-watermark="{watermark_encoded}" class="protected-content">
            {content}
            <div style="position: absolute; top: 0; left: 0; width: 1px; height: 1px; opacity: 0.01; pointer-events: none;">
                <!-- Watermark: {user_id} @ {timestamp} -->
            </div>
        </div>
        """
        
        return watermarked_content
    
    def obfuscate_sensitive_data(self, data: str, field_type: str = 'general') -> str:
        """
        Obfuscate sensitive data for display
        
        Args:
            data: Original data
            field_type: Type of sensitive field (ssn, account, etc.)
            
        Returns:
            str: Obfuscated data
        """
        if field_type == 'account':
            # Show only last 4 digits of account numbers
            if len(data) > 4:
                return '*' * (len(data) - 4) + data[-4:]
        elif field_type == 'ssn':
            # Show only last 4 digits of SSN
            if len(data) >= 4:
                return 'XXX-XX-' + data[-4:]
        elif field_type == 'amount':
            # Optionally mask large amounts
            try:
                amount = float(data.replace('$', '').replace(',', ''))
                if amount > 1000000:  # Mask amounts over $1M
                    return '$XX,XXX,XXX+'
            except:
                pass
        
        return data
    
    def log_content_access(self, content_type: str, user_id: str, action: str = 'view'):
        """
        Log access to sensitive content
        
        Args:
            content_type: Type of content accessed
            user_id: User accessing content
            action: Action performed (view, download, etc.)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'content_type': content_type,
            'action': action,
            'session_id': st.session_state.get('session_id', 'unknown'),
            'ip_hash': hashlib.md5(str(st.session_state.get('client_ip', 'unknown')).encode()).hexdigest()[:8]
        }
        
        self.access_log.append(log_entry)
        
        # Store in session for admin review
        if 'content_access_log' not in st.session_state:
            st.session_state.content_access_log = []
        
        st.session_state.content_access_log.append(log_entry)
    
    def create_secure_display(self, content: str, title: str, user_id: str, 
                            sensitive_level: str = 'medium') -> str:
        """
        Create secure display wrapper for content
        
        Args:
            content: Content to display
            title: Content title
            user_id: Current user
            sensitive_level: Sensitivity level (low, medium, high)
            
        Returns:
            str: Secure display HTML
        """
        # Log access
        self.log_content_access(title, user_id, 'view')
        
        # Apply protection based on sensitivity
        if sensitive_level == 'high':
            protection_css = """
            <style>
            .high-security {
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
                -webkit-touch-callout: none;
                -webkit-tap-highlight-color: transparent;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                background: linear-gradient(45deg, transparent 40%, rgba(255,0,0,0.1) 50%, transparent 60%);
                background-size: 20px 20px;
                position: relative;
            }
            .high-security::before {
                content: "CONFIDENTIAL - " attr(data-user);
                position: absolute;
                top: 10px;
                right: 10px;
                font-size: 8px;
                opacity: 0.3;
                color: red;
                font-weight: bold;
                z-index: 1000;
            }
            @media print {
                .high-security::after {
                    content: "CONFIDENTIAL - Accessed by " attr(data-user) " on " attr(data-timestamp);
                    position: fixed;
                    bottom: 10px;
                    left: 10px;
                    font-size: 8px;
                    color: red;
                }
            }
            </style>
            """
            
            protected_content = f"""
            {protection_css}
            <div class="high-security protected-content" data-user="{user_id}" data-timestamp="{datetime.now().strftime('%Y-%m-%d %H:%M')}">
                {content}
            </div>
            """
        else:
            protected_content = f"""
            <div class="protected-content" style="user-select: none;">
                {content}
            </div>
            """
        
        # Add watermark if enabled
        if self.watermark_enabled:
            protected_content = self.create_watermarked_content(protected_content, user_id)
        
        return protected_content
    
    def get_access_log(self) -> List[Dict]:
        """Get content access log for admin review"""
        return st.session_state.get('content_access_log', [])
    
    def clear_access_log(self):
        """Clear content access log"""
        if 'content_access_log' in st.session_state:
            del st.session_state.content_access_log
        self.access_log = []

# Global instance
content_protector = ContentProtector()

def display_protected_content(content: str, title: str, sensitive_level: str = 'medium'):
    """
    Display content with protection measures
    
    Args:
        content: Content to display
        title: Content title
        sensitive_level: Protection level
    """
    user_id = st.session_state.get('user', {}).get('username', 'anonymous')
    
    protected_html = content_protector.create_secure_display(
        content, title, user_id, sensitive_level
    )
    
    st.markdown(protected_html, unsafe_allow_html=True)

def obfuscate_financial_data(data: str, data_type: str = 'amount') -> str:
    """
    Obfuscate sensitive financial data
    
    Args:
        data: Original data
        data_type: Type of financial data
        
    Returns:
        str: Obfuscated data
    """
    return content_protector.obfuscate_sensitive_data(data, data_type)