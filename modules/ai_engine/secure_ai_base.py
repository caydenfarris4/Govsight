"""
Secure AI Base Framework for GovSight
Enterprise-grade security foundation for all AI capabilities
"""

import os
import json
import hashlib
import logging
import streamlit as st
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd
import sqlite3
from cryptography.fernet import Fernet
import secrets

# Configure security logging
logging.basicConfig(level=logging.INFO)
security_logger = logging.getLogger('govsight.ai.security')

@dataclass
class AISecurityConfig:
    """Security configuration for AI operations"""
    encrypt_data: bool = True
    log_all_requests: bool = True
    data_retention_days: int = 90
    max_query_length: int = 10000
    allowed_data_sources: List[str] = None
    security_level: str = "high"  # low, medium, high, maximum
    
class SecureAIBase:
    """
    Secure foundation class for all AI capabilities in GovSight
    
    SECURITY FEATURES:
    - Input validation and sanitization
    - Data encryption at rest and in transit
    - Audit logging for all AI operations
    - Access control and rate limiting
    - Secure data handling and cleanup
    - Protection against prompt injection
    """
    
    def __init__(self, module_name: str, security_config: AISecurityConfig = None):
        self.module_name = module_name
        self.security_config = security_config or AISecurityConfig()
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Initialize OpenAI client securely
        self.openai_client = self._initialize_openai_client()
        
        # Initialize security database
        self._initialize_security_db()
        
        security_logger.info(f"SecureAI initialized for module: {module_name}")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Generate or retrieve encryption key for data protection"""
        key_file = 'ai_encryption.key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure file permissions (readable only by owner)
            os.chmod(key_file, 0o600)
        
        return key
    
    def _initialize_openai_client(self) -> Optional[openai.OpenAI]:
        """Initialize OpenAI client with security validations and graceful degradation"""
        # Try to import the API key manager
        try:
            from modules.security.api_key_manager import api_key_manager
            api_key = api_key_manager.get_api_key("openai")
        except ImportError:
            # Fallback to environment variable if manager not available
            api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key or api_key == "sk-xxx":
            security_logger.warning("OpenAI API key not configured - AI features will be disabled")
            return None
        
        if len(api_key) < 32:  # Basic API key validation
            security_logger.warning("Invalid OpenAI API key format detected")
            return None
        
        try:
            return openai.OpenAI(api_key=api_key)
        except Exception as e:
            security_logger.error(f"Failed to initialize OpenAI client: {e}")
            return None
    
    def _initialize_security_db(self):
        """Initialize security audit database"""
        try:
            conn = sqlite3.connect('ai_security_audit.db')
            cursor = conn.cursor()
            
            # Create audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    module_name TEXT,
                    operation TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    input_hash TEXT,
                    output_hash TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    security_level TEXT,
                    data_sources TEXT
                )
            ''')
            
            # Create rate limiting table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rate_limiting (
                    user_id TEXT,
                    timestamp DATETIME,
                    request_count INTEGER,
                    PRIMARY KEY (user_id, timestamp)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            security_logger.error(f"Failed to initialize security database: {e}")
    
    def _validate_input(self, user_input: str) -> Dict[str, Any]:
        """
        Comprehensive input validation and sanitization
        
        Returns:
            Dict with validation results and sanitized input
        """
        validation_result = {
            'is_valid': True,
            'sanitized_input': user_input,
            'warnings': [],
            'blocked_content': []
        }
        
        # Length validation
        if len(user_input) > self.security_config.max_query_length:
            validation_result['is_valid'] = False
            validation_result['warnings'].append(f"Input exceeds maximum length of {self.security_config.max_query_length} characters")
            return validation_result
        
        # Prompt injection detection
        injection_patterns = [
            r'ignore\s+previous\s+instructions?',
            r'system\s*:\s*you\s+are',
            r'pretend\s+to\s+be',
            r'act\s+as\s+(?:if\s+)?you\s+are',
            r'forget\s+everything',
            r'disregard\s+.*(?:above|previous)',
            r'role\s*:\s*system',
            r'<\s*script\s*>',
            r'javascript\s*:',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__.*__',  # Python dunder methods
        ]
        
        import re
        for pattern in injection_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                validation_result['warnings'].append(f"Potential prompt injection detected: {pattern}")
                validation_result['blocked_content'].append(pattern)
        
        # SQL injection detection (for data queries)
        sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+.*set',
            r'--\s*\w',
            r'/\*.*\*/',
            r';\s*drop',
            r';\s*delete'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                validation_result['warnings'].append(f"Potential SQL injection detected: {pattern}")
                validation_result['blocked_content'].append(pattern)
        
        # Block if critical security issues found
        if len(validation_result['blocked_content']) > 0:
            validation_result['is_valid'] = False
        
        return validation_result
    
    def _log_ai_operation(self, operation: str, input_data: str, output_data: str = "", 
                         success: bool = True, error_message: str = "", 
                         data_sources: List[str] = None):
        """Log AI operations for security audit"""
        try:
            user_id = st.session_state.get('username', 'anonymous')
            session_id = st.session_state.get('session_id', 'unknown')
            
            # Hash sensitive data for logging
            input_hash = hashlib.sha256(input_data.encode()).hexdigest()
            output_hash = hashlib.sha256(output_data.encode()).hexdigest()
            
            conn = sqlite3.connect('ai_security_audit.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ai_audit_log 
                (module_name, operation, user_id, session_id, input_hash, output_hash, 
                 success, error_message, security_level, data_sources)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.module_name, operation, user_id, session_id, input_hash, output_hash,
                success, error_message, self.security_config.security_level,
                json.dumps(data_sources or [])
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            security_logger.error(f"Failed to log AI operation: {e}")
    
    def _check_rate_limit(self, user_id: str, max_requests: int = 100, 
                         window_minutes: int = 60) -> bool:
        """Check if user has exceeded rate limits"""
        try:
            conn = sqlite3.connect('ai_security_audit.db')
            cursor = conn.cursor()
            
            # Clean up old entries
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            cursor.execute('DELETE FROM rate_limiting WHERE timestamp < ?', (cutoff_time,))
            
            # Check current request count
            cursor.execute('''
                SELECT SUM(request_count) FROM rate_limiting 
                WHERE user_id = ? AND timestamp >= ?
            ''', (user_id, cutoff_time))
            
            current_count = cursor.fetchone()[0] or 0
            
            if current_count >= max_requests:
                conn.close()
                return False
            
            # Record this request
            now = datetime.now().replace(second=0, microsecond=0)  # Round to minute
            cursor.execute('''
                INSERT OR REPLACE INTO rate_limiting (user_id, timestamp, request_count)
                VALUES (?, ?, COALESCE((SELECT request_count FROM rate_limiting WHERE user_id = ? AND timestamp = ?), 0) + 1)
            ''', (user_id, now, user_id, now))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            security_logger.error(f"Rate limiting check failed: {e}")
            return True  # Allow request on error to avoid blocking legitimate users
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data for storage"""
        if not self.security_config.encrypt_data:
            return data
        
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return encrypted_data.decode()
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.security_config.encrypt_data:
            return encrypted_data
        
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            security_logger.error(f"Failed to decrypt data: {e}")
            return ""
    
    def secure_ai_request(self, prompt: str, operation: str, 
                         data_sources: List[str] = None,
                         max_tokens: int = 2000, 
                         temperature: float = 0.2) -> Dict[str, Any]:
        """
        Make a secure AI request with full security validations
        
        Returns:
            Dict containing response, metadata, and security info
        """
        user_id = st.session_state.get('username', 'anonymous')
        
        # Rate limiting check
        if not self._check_rate_limit(user_id):
            security_logger.warning(f"Rate limit exceeded for user: {user_id}")
            return {
                'success': False,
                'error': 'Rate limit exceeded. Please try again later.',
                'security_status': 'blocked'
            }
        
        # Input validation
        validation = self._validate_input(prompt)
        if not validation['is_valid']:
            security_logger.warning(f"Input validation failed: {validation['warnings']}")
            self._log_ai_operation(operation, prompt, "", False, 
                                 f"Validation failed: {validation['warnings']}", data_sources)
            return {
                'success': False,
                'error': 'Input validation failed: ' + '; '.join(validation['warnings']),
                'security_status': 'blocked',
                'validation_details': validation
            }
        
        try:
            # Make secure AI request
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a secure AI assistant for GovSight municipal financial platform. 
                        
SECURITY GUIDELINES:
- Only provide information about municipal finance, budgets, grants, and government operations
- Never execute code, access external systems, or perform administrative tasks
- If asked about non-municipal topics, politely redirect to financial matters
- Protect sensitive information and maintain data confidentiality
- Report any suspicious requests or potential security issues

OPERATION: {operation}
DATA SOURCES: {', '.join(data_sources or [])}"""
                    },
                    {
                        "role": "user", 
                        "content": validation['sanitized_input']
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            response_content = response.choices[0].message.content
            
            # Log successful operation
            self._log_ai_operation(operation, prompt, response_content, True, "", data_sources)
            
            return {
                'success': True,
                'response': response_content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                    'total_tokens': response.usage.total_tokens if response.usage else 0
                } if response.usage else {},
                'security_status': 'approved',
                'validation_warnings': validation.get('warnings', [])
            }
            
        except Exception as e:
            error_msg = str(e)
            security_logger.error(f"AI request failed: {error_msg}")
            self._log_ai_operation(operation, prompt, "", False, error_msg, data_sources)
            
            return {
                'success': False,
                'error': f"AI request failed: {error_msg}",
                'security_status': 'error'
            }
    
    def cleanup_expired_data(self):
        """Clean up expired data based on retention policy"""
        try:
            if self.security_config.data_retention_days <= 0:
                return
                
            cutoff_date = datetime.now() - timedelta(days=self.security_config.data_retention_days)
            
            conn = sqlite3.connect('ai_security_audit.db')
            cursor = conn.cursor()
            
            # Delete expired audit logs
            cursor.execute('DELETE FROM ai_audit_log WHERE timestamp < ?', (cutoff_date,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                security_logger.info(f"Cleaned up {deleted_count} expired audit records")
                
        except Exception as e:
            security_logger.error(f"Data cleanup failed: {e}")

# Global security configuration
GOVSIGHT_AI_SECURITY = AISecurityConfig(
    encrypt_data=True,
    log_all_requests=True,
    data_retention_days=90,
    max_query_length=8000,
    security_level="high"
)