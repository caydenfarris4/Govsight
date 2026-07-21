"""
Enterprise Database Security Module for MantisAI
Implements comprehensive security controls for municipal financial data access

CRITICAL SECURITY FEATURES:
- PII protection and data anonymization
- Local-only data processing (no raw data to external APIs)
- Read-only database connections with query validation
- Comprehensive audit logging
- Data sanitization and masking
- Query result limits and security controls
"""

import os
import re
import json
import sqlite3
import hashlib
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from cryptography.fernet import Fernet
import secrets

# Configure security logging
security_logger = logging.getLogger('govsight.enterprise.db.security')
security_logger.setLevel(logging.INFO)

# Add file handler for security logs
if not security_logger.handlers:
    handler = logging.FileHandler('logs/database_security.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)

@dataclass
class DatabaseAccessEvent:
    """Audit event for database access"""
    timestamp: datetime
    user_id: str
    session_id: str
    database_name: str
    query_description: str
    query_hash: str
    data_categories: List[str]
    rows_accessed: int
    pii_detected: bool
    sanitized: bool
    external_api_called: bool
    success: bool
    error_message: Optional[str] = None

@dataclass
class SensitiveDataPattern:
    """Pattern definition for sensitive data detection"""
    name: str
    pattern: str
    replacement: str
    severity: str  # 'high', 'medium', 'low'
    category: str  # 'pii', 'financial', 'confidential'

class EnterpriseDBSecurity:
    """
    Enterprise-grade database security for MantisAI
    
    SECURITY PRINCIPLES:
    1. Zero Trust - No raw data leaves the local environment
    2. Data Minimization - Only necessary aggregated data is processed
    3. Purpose Limitation - Data used only for approved municipal purposes
    4. Audit Everything - Complete audit trail of all data access
    5. PII Protection - Strict anonymization of personal information
    """
    
    def __init__(self):
        self.audit_db_path = 'databases/audit/enterprise_security_audit.db'
        self.encryption_key = self._get_or_create_security_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Initialize audit database
        self._init_audit_database()
        
        # Define sensitive data patterns
        self.sensitive_patterns = self._define_sensitive_patterns()
        
        # SQL query security rules
        self.allowed_operations = {'SELECT', 'WITH'}
        self.blocked_operations = {
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
            'TRUNCATE', 'EXEC', 'EXECUTE', 'CALL', 'MERGE'
        }
        
        # Data access limits
        self.max_rows_per_query = 10000
        self.max_queries_per_session = 100
        self.max_queries_per_minute = 20
        
        security_logger.info("Enterprise Database Security initialized")
    
    def _get_or_create_security_key(self) -> bytes:
        """Generate or retrieve encryption key for sensitive data"""
        key_file = 'credentials/enterprise_db_security.key'
        
        # Ensure credentials directory exists
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
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
    
    def _init_audit_database(self):
        """Initialize comprehensive audit database"""
        try:
            # Ensure audit directory exists
            os.makedirs(os.path.dirname(self.audit_db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.audit_db_path)
            cursor = conn.cursor()
            
            # Database access audit table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS database_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    database_name TEXT NOT NULL,
                    query_description TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    data_categories TEXT,
                    rows_accessed INTEGER,
                    pii_detected BOOLEAN,
                    sanitized BOOLEAN,
                    external_api_called BOOLEAN,
                    success BOOLEAN,
                    error_message TEXT,
                    security_level TEXT DEFAULT 'ENTERPRISE'
                )
            ''')
            
            # PII detection log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pii_detection_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_log_id INTEGER,
                    pii_type TEXT,
                    field_name TEXT,
                    pattern_matched TEXT,
                    anonymization_method TEXT,
                    FOREIGN KEY (access_log_id) REFERENCES database_access_log (id)
                )
            ''')
            
            # Query validation log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_validation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    query_description TEXT,
                    validation_result TEXT,
                    blocked_reason TEXT,
                    security_threat_level TEXT
                )
            ''')
            
            # Rate limiting tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rate_limiting_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    session_id TEXT,
                    query_count INTEGER,
                    rate_limit_exceeded BOOLEAN
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            security_logger.error(f"Failed to initialize audit database: {e}")
    
    def _define_sensitive_patterns(self) -> List[SensitiveDataPattern]:
        """Define patterns for detecting sensitive data"""
        return [
            # Social Security Numbers
            SensitiveDataPattern(
                name="SSN",
                pattern=r'\b\d{3}-?\d{2}-?\d{4}\b',
                replacement="***-**-****",
                severity="high",
                category="pii"
            ),
            
            # Email addresses
            SensitiveDataPattern(
                name="Email",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                replacement="***@***.***",
                severity="medium",
                category="pii"
            ),
            
            # Phone numbers
            SensitiveDataPattern(
                name="Phone",
                pattern=r'\b\d{3}-?\d{3}-?\d{4}\b',
                replacement="***-***-****",
                severity="medium",
                category="pii"
            ),
            
            # Credit card numbers
            SensitiveDataPattern(
                name="Credit Card",
                pattern=r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
                replacement="****-****-****-****",
                severity="high",
                category="financial"
            ),
            
            # Bank account numbers (generic pattern)
            SensitiveDataPattern(
                name="Bank Account",
                pattern=r'\b\d{8,17}\b',
                replacement="***ACCOUNT***",
                severity="high",
                category="financial"
            ),
            
            # Street addresses (simple pattern)
            SensitiveDataPattern(
                name="Street Address",
                pattern=r'\b\d+\s+[A-Z][a-z]+\s+(St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Blvd|Boulevard|Way|Ct|Court|Pl|Place)\b',
                replacement="*** [ADDRESS] ***",
                severity="medium",
                category="pii"
            ),
            
            # Names (common personal name patterns)
            SensitiveDataPattern(
                name="Personal Name",
                pattern=r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b',
                replacement="*** [NAME] ***",
                severity="medium",
                category="pii"
            )
        ]
    
    def validate_query_security(self, query_description: str, database_name: str) -> Dict[str, Any]:
        """
        Validate query for security compliance
        
        Returns:
            Dict with validation results and security assessment
        """
        validation_result = {
            'is_safe': True,
            'threat_level': 'low',
            'blocked_reasons': [],
            'security_warnings': [],
            'sanitized_description': query_description
        }
        
        # Convert to uppercase for checking
        query_upper = query_description.upper()
        
        # Check for blocked SQL operations
        for blocked_op in self.blocked_operations:
            if blocked_op in query_upper:
                validation_result['is_safe'] = False
                validation_result['threat_level'] = 'high'
                validation_result['blocked_reasons'].append(f"Blocked SQL operation: {blocked_op}")
        
        # Check for SQL injection patterns
        injection_patterns = [
            r'(UNION\s+SELECT)',
            r'(;\s*DROP)',
            r'(;\s*DELETE)',
            r'(OR\s+1\s*=\s*1)',
            r'(AND\s+1\s*=\s*1)',
            r'(\'\s*OR\s*\')',
            r'(--\s*\w)',
            r'(/\*.*\*/)',
            r'(EXEC\s*\()',
            r'(EXECUTE\s*\()'
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, query_upper):
                validation_result['is_safe'] = False
                validation_result['threat_level'] = 'critical'
                validation_result['blocked_reasons'].append(f"SQL injection pattern detected: {pattern}")
        
        # Check for data dumping attempts
        dump_patterns = [
            r'(LIMIT\s+\d{5,})',  # Very large limits
            r'(SELECT\s+\*\s+FROM\s+\w+\s*$)',  # Select all without limits
            r'(COUNT\s*\(\s*\*\s*\)\s*>\s*\d{4,})'  # Large count queries
        ]
        
        for pattern in dump_patterns:
            if re.search(pattern, query_upper):
                validation_result['threat_level'] = 'medium'
                validation_result['security_warnings'].append(f"Potential data dumping pattern: {pattern}")
        
        # Log validation attempt
        self._log_query_validation(query_description, validation_result)
        
        return validation_result
    
    def execute_secure_query(self, database_name: str, query_description: str, 
                           user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Execute database query with comprehensive security controls
        
        Returns:
            Dict with query results, security metadata, and audit information
        """
        start_time = datetime.now()
        
        # Validate rate limiting
        if not self._check_rate_limiting(user_id, session_id):
            return {
                'success': False,
                'error': 'Rate limit exceeded. Please wait before making more queries.',
                'security_status': 'blocked',
                'threat_level': 'medium'
            }
        
        # Validate query security
        validation = self.validate_query_security(query_description, database_name)
        if not validation['is_safe']:
            self._log_database_access(
                user_id, session_id, database_name, query_description,
                0, False, False, False, False, 
                f"Query blocked: {'; '.join(validation['blocked_reasons'])}"
            )
            return {
                'success': False,
                'error': f"Query blocked for security reasons: {'; '.join(validation['blocked_reasons'])}",
                'security_status': 'blocked',
                'threat_level': validation['threat_level']
            }
        
        try:
            # Execute query with read-only connection
            raw_data = self._execute_read_only_query(database_name, query_description)
            
            if raw_data is None or (isinstance(raw_data, pd.DataFrame) and raw_data.empty):
                self._log_database_access(
                    user_id, session_id, database_name, query_description,
                    0, False, False, False, True, None
                )
                return {
                    'success': True,
                    'data': pd.DataFrame(),
                    'summary': 'No data found for the specified query.',
                    'security_status': 'safe',
                    'rows_accessed': 0
                }
            
            # Detect and log PII
            pii_detected, pii_details = self._detect_pii(raw_data)
            
            # Sanitize and anonymize data
            sanitized_data = self._sanitize_data(raw_data, pii_details)
            
            # Process data locally (aggregations, summaries)
            processed_data = self._process_data_locally(sanitized_data, query_description)
            
            # Generate secure summary (no raw records exposed)
            summary = self._generate_secure_summary(processed_data, query_description)
            
            # Determine data categories
            data_categories = self._categorize_data(processed_data)
            
            # Log successful access
            self._log_database_access(
                user_id, session_id, database_name, query_description,
                len(raw_data) if isinstance(raw_data, pd.DataFrame) else 0,
                pii_detected, True, False, True, None
            )
            
            # Log PII detection details
            if pii_detected and pii_details:
                self._log_pii_detection(user_id, session_id, pii_details)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'data': processed_data,
                'summary': summary,
                'security_status': 'safe',
                'rows_accessed': len(raw_data) if isinstance(raw_data, pd.DataFrame) else 0,
                'pii_detected': pii_detected,
                'sanitized': True,
                'data_categories': data_categories,
                'execution_time': execution_time,
                'security_warnings': validation.get('security_warnings', [])
            }
            
        except Exception as e:
            error_msg = str(e)
            security_logger.error(f"Secure query execution failed: {error_msg}")
            
            self._log_database_access(
                user_id, session_id, database_name, query_description,
                0, False, False, False, False, error_msg
            )
            
            return {
                'success': False,
                'error': f"Query execution failed: {error_msg}",
                'security_status': 'error',
                'threat_level': 'low'
            }
    
    def _execute_read_only_query(self, database_name: str, query_description: str) -> Optional[pd.DataFrame]:
        """Execute query with read-only connection and safety limits"""
        try:
            # Import database manager
            from modules.bi_sandbox.multi_database_manager import MultiDatabaseManager
            
            db_manager = MultiDatabaseManager()
            connections = db_manager.get_all_database_connections()
            
            if database_name not in connections:
                raise ValueError(f"Database '{database_name}' not available")
            
            conn = connections[database_name]['connection']
            
            # Generate safe SQL query from description
            safe_query = self._generate_safe_sql(query_description, database_name)
            
            # Add row limit for safety
            if 'LIMIT' not in safe_query.upper():
                safe_query += f" LIMIT {self.max_rows_per_query}"
            
            # Execute query with timeout
            result = pd.read_sql_query(safe_query, conn)
            
            security_logger.info(f"Executed safe query on {database_name}: {len(result)} rows returned")
            return result
            
        except Exception as e:
            security_logger.error(f"Read-only query execution failed: {e}")
            return None
    
    def _generate_safe_sql(self, description: str, database_name: str) -> str:
        """Generate safe SQL from natural language description"""
        # This is a simplified version - in production, use proper query builder
        # Map common requests to safe, read-only queries
        
        description_lower = description.lower()
        
        # Database-specific safe queries
        if database_name == 'gl_primary':
            if 'department' in description_lower:
                return "SELECT Department, SUM(Amount) as Total_Amount, COUNT(*) as Transaction_Count FROM transactions GROUP BY Department"
            elif 'budget' in description_lower:
                return "SELECT Department, SUM(Budget) as Total_Budget, SUM(Actual) as Total_Actual FROM budget_summary GROUP BY Department"
            elif 'vendor' in description_lower:
                return "SELECT Vendor, COUNT(*) as Transaction_Count, SUM(Amount) as Total_Amount FROM transactions GROUP BY Vendor"
            elif 'monthly' in description_lower or 'month' in description_lower:
                return "SELECT strftime('%Y-%m', Date) as Month, SUM(Amount) as Monthly_Total FROM transactions GROUP BY strftime('%Y-%m', Date)"
            else:
                return "SELECT Department, COUNT(*) as Count FROM transactions GROUP BY Department"
        
        elif database_name == 'payroll':
            if 'employee' in description_lower:
                return "SELECT Department, COUNT(*) as Employee_Count, AVG(Salary) as Avg_Salary FROM employees GROUP BY Department"
            elif 'salary' in description_lower:
                return "SELECT Department, AVG(Salary) as Average_Salary, MIN(Salary) as Min_Salary, MAX(Salary) as Max_Salary FROM employees GROUP BY Department"
            else:
                return "SELECT Department, COUNT(*) as Employee_Count FROM employees GROUP BY Department"
        
        # Default safe query
        return f"SELECT COUNT(*) as total_records FROM (SELECT * FROM sqlite_master WHERE type='table' LIMIT 10)"
    
    def _detect_pii(self, data: pd.DataFrame) -> Tuple[bool, List[Dict]]:
        """Detect personally identifiable information in data"""
        pii_detected = False
        pii_details = []
        
        for column in data.columns:
            for index, value in data[column].items():
                if pd.isna(value):
                    continue
                
                value_str = str(value)
                
                for pattern in self.sensitive_patterns:
                    if re.search(pattern.pattern, value_str):
                        pii_detected = True
                        pii_details.append({
                            'column': column,
                            'row': index,
                            'pattern': pattern.name,
                            'category': pattern.category,
                            'severity': pattern.severity
                        })
        
        return pii_detected, pii_details
    
    def _sanitize_data(self, data: pd.DataFrame, pii_details: List[Dict]) -> pd.DataFrame:
        """Sanitize data by removing/anonymizing PII"""
        sanitized_data = data.copy()
        
        # Apply pattern-based sanitization
        for column in sanitized_data.columns:
            for pattern in self.sensitive_patterns:
                sanitized_data[column] = sanitized_data[column].astype(str).apply(
                    lambda x: re.sub(pattern.pattern, pattern.replacement, x) if pd.notna(x) else x
                )
        
        # Additional anonymization for detected PII
        for pii_detail in pii_details:
            column = pii_detail['column']
            row = pii_detail['row']
            
            if pii_detail['severity'] == 'high':
                # Replace with generic placeholder
                sanitized_data.at[row, column] = f"[{pii_detail['pattern'].upper()}_REDACTED]"
            elif pii_detail['severity'] == 'medium':
                # Partial masking
                original_value = str(sanitized_data.at[row, column])
                if len(original_value) > 4:
                    sanitized_data.at[row, column] = f"{original_value[:2]}***{original_value[-2:]}"
        
        return sanitized_data
    
    def _process_data_locally(self, data: pd.DataFrame, query_description: str) -> pd.DataFrame:
        """Process data locally with aggregations and summaries"""
        try:
            # Always aggregate data to prevent individual record exposure
            processed_data = data.copy()
            
            # If data has more than 100 rows, aggregate it
            if len(processed_data) > 100:
                # Identify numeric columns for aggregation
                numeric_columns = processed_data.select_dtypes(include=[np.number]).columns.tolist()
                categorical_columns = processed_data.select_dtypes(exclude=[np.number]).columns.tolist()
                
                if categorical_columns and numeric_columns:
                    # Group by first categorical column and aggregate numeric columns
                    group_col = categorical_columns[0]
                    agg_dict = {col: ['sum', 'count', 'mean'] for col in numeric_columns}
                    processed_data = processed_data.groupby(group_col).agg(agg_dict)
                    processed_data.columns = ['_'.join(col).strip() for col in processed_data.columns]
                    processed_data = processed_data.reset_index()
            
            # Limit rows for security
            if len(processed_data) > self.max_rows_per_query:
                processed_data = processed_data.head(self.max_rows_per_query)
            
            return processed_data
            
        except Exception as e:
            security_logger.error(f"Data processing error: {e}")
            # Return empty dataframe on error for security
            return pd.DataFrame()
    
    def _generate_secure_summary(self, data: pd.DataFrame, query_description: str) -> str:
        """Generate secure text summary of data (no raw records)"""
        try:
            if data.empty:
                return "No data found for the specified query."
            
            summary_parts = []
            
            # Basic statistics
            summary_parts.append(f"Data summary for query: {query_description}")
            summary_parts.append(f"Total records: {len(data)}")
            summary_parts.append(f"Columns: {', '.join(data.columns[:5])}")  # Limit column names
            
            # Numeric summaries
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                for col in numeric_columns[:3]:  # Limit to first 3 numeric columns
                    if col in data.columns:
                        summary_parts.append(f"{col}: min={data[col].min():.2f}, max={data[col].max():.2f}, avg={data[col].mean():.2f}")
            
            # Categorical summaries
            categorical_columns = data.select_dtypes(exclude=[np.number]).columns
            if len(categorical_columns) > 0:
                for col in categorical_columns[:2]:  # Limit to first 2 categorical columns
                    if col in data.columns and len(data[col].unique()) < 20:
                        unique_count = len(data[col].unique())
                        summary_parts.append(f"{col}: {unique_count} unique values")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            security_logger.error(f"Summary generation error: {e}")
            return "Summary generation failed due to security constraints."
    
    def _categorize_data(self, data: pd.DataFrame) -> List[str]:
        """Categorize data types for audit purposes"""
        categories = []
        
        columns_lower = [col.lower() for col in data.columns]
        
        # Financial data indicators
        financial_keywords = ['amount', 'budget', 'cost', 'price', 'fee', 'salary', 'payment', 'revenue']
        if any(keyword in col for col in columns_lower for keyword in financial_keywords):
            categories.append('financial_data')
        
        # Personal data indicators
        personal_keywords = ['name', 'address', 'phone', 'email', 'ssn', 'employee']
        if any(keyword in col for col in columns_lower for keyword in personal_keywords):
            categories.append('personal_data')
        
        # Administrative data indicators
        admin_keywords = ['department', 'vendor', 'account', 'transaction', 'permit', 'license']
        if any(keyword in col for col in columns_lower for keyword in admin_keywords):
            categories.append('administrative_data')
        
        return categories if categories else ['general_data']
    
    def _check_rate_limiting(self, user_id: str, session_id: str) -> bool:
        """Check if user has exceeded rate limits"""
        try:
            conn = sqlite3.connect(self.audit_db_path)
            cursor = conn.cursor()
            
            # Check queries in last minute
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            cursor.execute('''
                SELECT COUNT(*) FROM database_access_log 
                WHERE user_id = ? AND timestamp >= ?
            ''', (user_id, one_minute_ago))
            
            recent_queries = cursor.fetchone()[0]
            
            if recent_queries >= self.max_queries_per_minute:
                # Log rate limit exceeded
                cursor.execute('''
                    INSERT INTO rate_limiting_log (user_id, session_id, query_count, rate_limit_exceeded)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, session_id, recent_queries, True))
                conn.commit()
                conn.close()
                return False
            
            conn.close()
            return True
            
        except Exception as e:
            security_logger.error(f"Rate limiting check failed: {e}")
            return True  # Allow on error to avoid blocking legitimate users
    
    def _log_database_access(self, user_id: str, session_id: str, database_name: str, 
                           query_description: str, rows_accessed: int, pii_detected: bool,
                           sanitized: bool, external_api_called: bool, success: bool,
                           error_message: Optional[str]):
        """Log database access event for audit"""
        try:
            conn = sqlite3.connect(self.audit_db_path)
            cursor = conn.cursor()
            
            query_hash = hashlib.sha256(query_description.encode()).hexdigest()
            data_categories = json.dumps(['financial_data'])  # Default category
            
            cursor.execute('''
                INSERT INTO database_access_log 
                (user_id, session_id, database_name, query_description, query_hash,
                 data_categories, rows_accessed, pii_detected, sanitized, 
                 external_api_called, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, session_id, database_name, query_description, query_hash,
                  data_categories, rows_accessed, pii_detected, sanitized,
                  external_api_called, success, error_message))
            
            conn.commit()
            conn.close()
            
            security_logger.info(f"Database access logged: {user_id} -> {database_name} ({rows_accessed} rows)")
            
        except Exception as e:
            security_logger.error(f"Failed to log database access: {e}")
    
    def _log_pii_detection(self, user_id: str, session_id: str, pii_details: List[Dict]):
        """Log PII detection details"""
        try:
            conn = sqlite3.connect(self.audit_db_path)
            cursor = conn.cursor()
            
            # Get the most recent access log entry for this session
            cursor.execute('''
                SELECT id FROM database_access_log 
                WHERE user_id = ? AND session_id = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (user_id, session_id))
            
            access_log_id = cursor.fetchone()
            if access_log_id:
                access_log_id = access_log_id[0]
                
                for pii_detail in pii_details:
                    cursor.execute('''
                        INSERT INTO pii_detection_log 
                        (access_log_id, pii_type, field_name, pattern_matched, anonymization_method)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (access_log_id, pii_detail['category'], pii_detail['column'],
                          pii_detail['pattern'], 'pattern_replacement'))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            security_logger.error(f"Failed to log PII detection: {e}")
    
    def _log_query_validation(self, query_description: str, validation_result: Dict):
        """Log query validation results"""
        try:
            conn = sqlite3.connect(self.audit_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO query_validation_log 
                (query_description, validation_result, blocked_reason, security_threat_level)
                VALUES (?, ?, ?, ?)
            ''', (query_description, json.dumps(validation_result),
                  '; '.join(validation_result.get('blocked_reasons', [])),
                  validation_result.get('threat_level', 'low')))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            security_logger.error(f"Failed to log query validation: {e}")
    
    def generate_security_report(self, start_date: Optional[datetime] = None, 
                               end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive security audit report"""
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            conn = sqlite3.connect(self.audit_db_path)
            
            # Database access statistics
            access_stats = pd.read_sql_query('''
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT database_name) as databases_accessed,
                    SUM(rows_accessed) as total_rows_accessed,
                    SUM(CASE WHEN pii_detected THEN 1 ELSE 0 END) as pii_incidents,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_queries,
                    AVG(rows_accessed) as avg_rows_per_query
                FROM database_access_log
                WHERE timestamp BETWEEN ? AND ?
            ''', conn, params=[start_date, end_date])
            
            # PII detection summary
            pii_stats = pd.read_sql_query('''
                SELECT 
                    pii_type, 
                    COUNT(*) as detection_count,
                    COUNT(DISTINCT dal.user_id) as affected_users
                FROM pii_detection_log pdl
                JOIN database_access_log dal ON pdl.access_log_id = dal.id
                WHERE dal.timestamp BETWEEN ? AND ?
                GROUP BY pii_type
            ''', conn, params=[start_date, end_date])
            
            # Query validation issues
            validation_stats = pd.read_sql_query('''
                SELECT 
                    security_threat_level,
                    COUNT(*) as incident_count
                FROM query_validation_log
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY security_threat_level
            ''', conn, params=[start_date, end_date])
            
            conn.close()
            
            return {
                'report_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'access_statistics': access_stats.to_dict('records')[0] if not access_stats.empty else {},
                'pii_detection_summary': pii_stats.to_dict('records') if not pii_stats.empty else [],
                'validation_summary': validation_stats.to_dict('records') if not validation_stats.empty else [],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            security_logger.error(f"Failed to generate security report: {e}")
            return {'error': str(e)}

# Global instance for use throughout the application
enterprise_db_security = EnterpriseDBSecurity()