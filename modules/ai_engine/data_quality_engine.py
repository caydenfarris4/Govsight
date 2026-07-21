"""
Data Quality & Validation Engine for GovSight
AI-powered data quality assessment, cleaning, and validation for municipal financial data
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import re
from dataclasses import dataclass, field
import sqlite3
import json

from modules.ai_engine.secure_ai_base import SecureAIBase, GOVSIGHT_AI_SECURITY

@dataclass
class DataQualityIssue:
    """Data quality issue structure"""
    issue_type: str
    severity: str  # High, Medium, Low
    field_name: str
    description: str
    affected_rows: int
    sample_values: List[str] = field(default_factory=list)
    suggested_fix: str = ""
    auto_fixable: bool = False

@dataclass
class DataValidationRule:
    """Data validation rule structure"""
    rule_name: str
    field_name: str
    rule_type: str  # format, range, lookup, consistency
    parameters: Dict[str, Any]
    error_message: str
    severity: str = "Medium"

class DataQualityEngine(SecureAIBase):
    """
    Advanced data quality assessment and improvement system
    
    CAPABILITIES:
    - Automated data profiling and quality assessment
    - AI-powered data cleaning recommendations
    - Data validation rule engine
    - Missing data imputation using ML models
    - Data consistency checking across systems
    - Automated data quality reporting
    """
    
    def __init__(self):
        super().__init__("DataQualityEngine", GOVSIGHT_AI_SECURITY)
        
        # Municipal finance data validation rules
        self.municipal_validation_rules = [
            DataValidationRule(
                rule_name="account_code_format",
                field_name="AccountCode",
                rule_type="format",
                parameters={"pattern": r"^\d{2}-\d{2}-\d{2}-\d{4}$"},
                error_message="Account code must follow FF-DD-CC-AAAA format",
                severity="High"
            ),
            DataValidationRule(
                rule_name="transaction_amount_range",
                field_name="Amount",
                rule_type="range",
                parameters={"min": 0.01, "max": 10000000},
                error_message="Transaction amount must be positive and under $10M",
                severity="High"
            ),
            DataValidationRule(
                rule_name="vendor_name_format",
                field_name="Vendor",
                rule_type="format",
                parameters={"min_length": 2, "max_length": 100},
                error_message="Vendor name must be 2-100 characters",
                severity="Medium"
            ),
            DataValidationRule(
                rule_name="date_validity",
                field_name="Date",
                rule_type="range",
                parameters={"min_date": "2000-01-01", "max_date": "2030-12-31"},
                error_message="Transaction date must be between 2000 and 2030",
                severity="High"
            )
        ]
        
        # Data quality patterns
        self.quality_patterns = {
            'suspicious_patterns': {
                'all_caps_text': r'^[A-Z\s\d]+$',
                'multiple_spaces': r'\s{2,}',
                'special_chars_only': r'^[^\w\s]+$',
                'mixed_case_inconsistent': r'[a-z][A-Z]',
            },
            'common_errors': {
                'leading_trailing_spaces': r'^\s+|\s+$',
                'inconsistent_abbreviations': ['ST', 'STREET', 'St.', 'str'],
                'duplicate_words': r'\b(\w+)\s+\1\b',
                'invalid_characters': r'[^\x00-\x7F]'  # Non-ASCII characters
            },
            'municipal_specific': {
                'department_codes': ['01', '02', '03', '04', '05', '06', '10', '11', '12'],
                'fund_codes': ['01', '02', '10', '11', '20', '21', '30', '31'],
                'account_types': ['ASSETS', 'LIABILITIES', 'REVENUE', 'EXPENSE', 'FUND BALANCE']
            }
        }
        
        # Initialize quality tracking database
        self._initialize_quality_db()
    
    def _initialize_quality_db(self):
        """Initialize data quality tracking database"""
        try:
            conn = sqlite3.connect('data_quality_tracking.db')
            cursor = conn.cursor()
            
            # Data quality assessments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    dataset_name TEXT,
                    total_records INTEGER,
                    total_issues INTEGER,
                    high_severity_issues INTEGER,
                    quality_score REAL,
                    assessment_details TEXT,
                    user_id TEXT
                )
            ''')
            
            # Data cleaning actions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cleaning_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    dataset_name TEXT,
                    action_type TEXT,
                    field_name TEXT,
                    records_affected INTEGER,
                    action_details TEXT,
                    user_id TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Failed to initialize quality tracking database: {e}")
    
    def comprehensive_quality_assessment(self, data: pd.DataFrame, 
                                       dataset_name: str = "unknown",
                                       validation_rules: List[DataValidationRule] = None) -> Dict[str, Any]:
        """
        Perform comprehensive data quality assessment
        
        Args:
            data: DataFrame to assess
            dataset_name: Name of the dataset for tracking
            validation_rules: Custom validation rules (optional)
            
        Returns:
            Comprehensive quality assessment results
        """
        if data.empty:
            return {'error': 'No data provided for quality assessment'}
        
        assessment_results = {
            'assessment_timestamp': datetime.now().isoformat(),
            'dataset_name': dataset_name,
            'total_records': len(data),
            'total_fields': len(data.columns),
            'quality_issues': [],
            'field_profiles': {},
            'overall_quality_score': 0,
            'recommendations': []
        }
        
        # Use provided rules or defaults
        rules_to_apply = validation_rules or self.municipal_validation_rules
        
        # 1. Basic Data Profiling
        assessment_results['field_profiles'] = self._profile_dataset(data)
        
        # 2. Missing Data Analysis
        missing_analysis = self._analyze_missing_data(data)
        assessment_results['missing_data_analysis'] = missing_analysis
        
        # 3. Data Type Validation
        type_issues = self._validate_data_types(data)
        assessment_results['quality_issues'].extend(type_issues)
        
        # 4. Format Validation
        format_issues = self._validate_data_formats(data, rules_to_apply)
        assessment_results['quality_issues'].extend(format_issues)
        
        # 5. Range and Constraint Validation
        range_issues = self._validate_ranges_constraints(data, rules_to_apply)
        assessment_results['quality_issues'].extend(range_issues)
        
        # 6. Consistency Validation
        consistency_issues = self._validate_consistency(data)
        assessment_results['quality_issues'].extend(consistency_issues)
        
        # 7. Duplicate Detection
        duplicate_issues = self._detect_duplicates(data)
        assessment_results['quality_issues'].extend(duplicate_issues)
        
        # 8. Municipal-Specific Validation
        municipal_issues = self._validate_municipal_patterns(data)
        assessment_results['quality_issues'].extend(municipal_issues)
        
        # 9. Calculate Overall Quality Score
        assessment_results['overall_quality_score'] = self._calculate_quality_score(assessment_results['quality_issues'], len(data))
        
        # 10. Generate AI-Powered Recommendations
        assessment_results['ai_recommendations'] = self._generate_quality_recommendations(assessment_results)
        
        # 11. Save assessment to tracking database
        self._save_quality_assessment(assessment_results)
        
        return assessment_results
    
    def _profile_dataset(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Create comprehensive data profile for each field"""
        profiles = {}
        
        for column in data.columns:
            column_data = data[column]
            
            profile = {
                'data_type': str(column_data.dtype),
                'total_values': len(column_data),
                'missing_count': column_data.isnull().sum(),
                'missing_percentage': (column_data.isnull().sum() / len(column_data)) * 100,
                'unique_count': column_data.nunique(),
                'unique_percentage': (column_data.nunique() / len(column_data)) * 100
            }
            
            # Numeric field profiling
            if pd.api.types.is_numeric_dtype(column_data):
                non_null_data = column_data.dropna()
                if len(non_null_data) > 0:
                    profile.update({
                        'min_value': float(non_null_data.min()),
                        'max_value': float(non_null_data.max()),
                        'mean_value': float(non_null_data.mean()),
                        'median_value': float(non_null_data.median()),
                        'std_deviation': float(non_null_data.std()) if len(non_null_data) > 1 else 0,
                        'zero_count': (non_null_data == 0).sum(),
                        'negative_count': (non_null_data < 0).sum()
                    })
            
            # Text field profiling
            elif pd.api.types.is_string_dtype(column_data):
                non_null_data = column_data.dropna().astype(str)
                if len(non_null_data) > 0:
                    lengths = non_null_data.str.len()
                    profile.update({
                        'min_length': int(lengths.min()),
                        'max_length': int(lengths.max()),
                        'avg_length': float(lengths.mean()),
                        'empty_strings': (non_null_data == '').sum(),
                        'whitespace_only': non_null_data.str.strip().eq('').sum(),
                        'contains_numbers': non_null_data.str.contains(r'\d').sum(),
                        'all_caps_count': non_null_data.str.isupper().sum(),
                        'all_lower_count': non_null_data.str.islower().sum()
                    })
            
            # Date field profiling
            elif pd.api.types.is_datetime64_any_dtype(column_data):
                non_null_data = column_data.dropna()
                if len(non_null_data) > 0:
                    profile.update({
                        'earliest_date': non_null_data.min().isoformat(),
                        'latest_date': non_null_data.max().isoformat(),
                        'date_range_days': (non_null_data.max() - non_null_data.min()).days
                    })
            
            # Top values analysis
            if column_data.nunique() < 100:  # Only for fields with reasonable number of unique values
                value_counts = column_data.value_counts().head(10)
                profile['top_values'] = [
                    {'value': str(val), 'count': int(count)} 
                    for val, count in value_counts.items()
                ]
            
            profiles[column] = profile
        
        return profiles
    
    def _analyze_missing_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze missing data patterns and suggest imputation strategies"""
        missing_analysis = {
            'total_missing_values': data.isnull().sum().sum(),
            'missing_percentage': (data.isnull().sum().sum() / data.size) * 100,
            'fields_with_missing_data': {},
            'missing_patterns': {},
            'imputation_recommendations': {}
        }
        
        # Analyze missing data by field
        for column in data.columns:
            missing_count = data[column].isnull().sum()
            if missing_count > 0:
                missing_percentage = (missing_count / len(data)) * 100
                
                missing_analysis['fields_with_missing_data'][column] = {
                    'count': int(missing_count),
                    'percentage': float(missing_percentage),
                    'severity': 'High' if missing_percentage > 20 else 'Medium' if missing_percentage > 5 else 'Low'
                }
                
                # Recommend imputation strategy
                imputation_strategy = self._recommend_imputation_strategy(data[column], column)
                missing_analysis['imputation_recommendations'][column] = imputation_strategy
        
        # Analyze missing data patterns across rows
        rows_with_missing = data.isnull().any(axis=1).sum()
        missing_analysis['rows_with_missing_data'] = {
            'count': int(rows_with_missing),
            'percentage': float((rows_with_missing / len(data)) * 100)
        }
        
        return missing_analysis
    
    def _recommend_imputation_strategy(self, column_data: pd.Series, column_name: str) -> Dict[str, Any]:
        """Recommend appropriate imputation strategy for missing data"""
        column_lower = column_name.lower()
        data_type = column_data.dtype
        missing_percentage = (column_data.isnull().sum() / len(column_data)) * 100
        
        recommendation = {
            'strategy': 'manual_review',
            'confidence': 'low',
            'rationale': 'Default - requires manual review'
        }
        
        if missing_percentage > 50:
            recommendation = {
                'strategy': 'consider_dropping',
                'confidence': 'high',
                'rationale': f'Over 50% missing data ({missing_percentage:.1f}%) - consider dropping column'
            }
        
        elif pd.api.types.is_numeric_dtype(data_type):
            if 'amount' in column_lower or 'balance' in column_lower:
                recommendation = {
                    'strategy': 'zero_fill',
                    'confidence': 'high',
                    'rationale': 'Financial amounts - missing likely means zero'
                }
            else:
                recommendation = {
                    'strategy': 'median_imputation',
                    'confidence': 'medium',
                    'rationale': 'Numeric field - median imputation reduces outlier impact'
                }
        
        elif pd.api.types.is_string_dtype(data_type):
            unique_ratio = column_data.nunique() / len(column_data.dropna())
            
            if unique_ratio < 0.1:  # Low cardinality - likely categorical
                recommendation = {
                    'strategy': 'mode_imputation',
                    'confidence': 'medium',
                    'rationale': 'Categorical field - use most frequent value'
                }
            elif 'description' in column_lower or 'note' in column_lower:
                recommendation = {
                    'strategy': 'default_text',
                    'confidence': 'medium',
                    'rationale': 'Description field - use default placeholder text'
                }
            else:
                recommendation = {
                    'strategy': 'manual_review',
                    'confidence': 'low',
                    'rationale': 'Text field with high cardinality - manual review recommended'
                }
        
        elif pd.api.types.is_datetime64_any_dtype(data_type):
            recommendation = {
                'strategy': 'interpolation',
                'confidence': 'medium',
                'rationale': 'Date field - time-based interpolation may be appropriate'
            }
        
        return recommendation
    
    def _validate_data_types(self, data: pd.DataFrame) -> List[DataQualityIssue]:
        """Validate data types and identify type conversion issues"""
        issues = []
        
        for column in data.columns:
            column_data = data[column]
            
            # Check for numeric fields stored as text
            if pd.api.types.is_string_dtype(column_data):
                # Check if column contains numeric values
                non_null_data = column_data.dropna().astype(str)
                numeric_pattern_count = non_null_data.str.match(r'^-?\d+\.?\d*$').sum()
                
                if numeric_pattern_count > len(non_null_data) * 0.8:  # 80% look numeric
                    issues.append(DataQualityIssue(
                        issue_type="data_type_mismatch",
                        severity="Medium",
                        field_name=column,
                        description=f"Field appears to contain numeric data but stored as text",
                        affected_rows=int(numeric_pattern_count),
                        suggested_fix=f"Convert {column} to numeric data type",
                        auto_fixable=True
                    ))
            
            # Check for date fields stored as text
            elif pd.api.types.is_string_dtype(column_data):
                if 'date' in column.lower() or 'time' in column.lower():
                    try:
                        pd.to_datetime(column_data.dropna().head(10))
                        issues.append(DataQualityIssue(
                            issue_type="data_type_mismatch",
                            severity="Medium",
                            field_name=column,
                            description=f"Date field stored as text",
                            affected_rows=len(column_data.dropna()),
                            suggested_fix=f"Convert {column} to datetime data type",
                            auto_fixable=True
                        ))
                    except:
                        pass
        
        return issues
    
    def _validate_data_formats(self, data: pd.DataFrame, 
                             validation_rules: List[DataValidationRule]) -> List[DataQualityIssue]:
        """Validate data formats against specified rules"""
        issues = []
        
        for rule in validation_rules:
            if rule.rule_type == "format" and rule.field_name in data.columns:
                column_data = data[rule.field_name].dropna()
                
                if rule.parameters.get('pattern'):
                    pattern = rule.parameters['pattern']
                    non_matching = column_data[~column_data.astype(str).str.match(pattern)]
                    
                    if len(non_matching) > 0:
                        issues.append(DataQualityIssue(
                            issue_type="format_violation",
                            severity=rule.severity,
                            field_name=rule.field_name,
                            description=f"{rule.error_message}",
                            affected_rows=len(non_matching),
                            sample_values=non_matching.astype(str).head(5).tolist(),
                            suggested_fix=f"Fix format to match pattern: {pattern}"
                        ))
                
                # Length validation
                if rule.parameters.get('min_length') or rule.parameters.get('max_length'):
                    min_len = rule.parameters.get('min_length', 0)
                    max_len = rule.parameters.get('max_length', float('inf'))
                    
                    lengths = column_data.astype(str).str.len()
                    invalid_lengths = column_data[(lengths < min_len) | (lengths > max_len)]
                    
                    if len(invalid_lengths) > 0:
                        issues.append(DataQualityIssue(
                            issue_type="length_violation",
                            severity=rule.severity,
                            field_name=rule.field_name,
                            description=f"Field length outside valid range ({min_len}-{max_len} characters)",
                            affected_rows=len(invalid_lengths),
                            sample_values=invalid_lengths.astype(str).head(5).tolist()
                        ))
        
        return issues
    
    def _validate_ranges_constraints(self, data: pd.DataFrame, 
                                   validation_rules: List[DataValidationRule]) -> List[DataQualityIssue]:
        """Validate numeric ranges and constraints"""
        issues = []
        
        for rule in validation_rules:
            if rule.rule_type == "range" and rule.field_name in data.columns:
                column_data = data[rule.field_name].dropna()
                
                if pd.api.types.is_numeric_dtype(column_data):
                    min_val = rule.parameters.get('min', float('-inf'))
                    max_val = rule.parameters.get('max', float('inf'))
                    
                    out_of_range = column_data[(column_data < min_val) | (column_data > max_val)]
                    
                    if len(out_of_range) > 0:
                        issues.append(DataQualityIssue(
                            issue_type="range_violation",
                            severity=rule.severity,
                            field_name=rule.field_name,
                            description=f"{rule.error_message}",
                            affected_rows=len(out_of_range),
                            sample_values=[str(x) for x in out_of_range.head(5).tolist()]
                        ))
                
                elif pd.api.types.is_datetime64_any_dtype(column_data):
                    min_date = pd.to_datetime(rule.parameters.get('min_date', '1900-01-01'))
                    max_date = pd.to_datetime(rule.parameters.get('max_date', '2100-12-31'))
                    
                    out_of_range = column_data[(column_data < min_date) | (column_data > max_date)]
                    
                    if len(out_of_range) > 0:
                        issues.append(DataQualityIssue(
                            issue_type="date_range_violation",
                            severity=rule.severity,
                            field_name=rule.field_name,
                            description=f"{rule.error_message}",
                            affected_rows=len(out_of_range),
                            sample_values=[x.strftime('%Y-%m-%d') for x in out_of_range.head(5)]
                        ))
        
        return issues
    
    def _validate_consistency(self, data: pd.DataFrame) -> List[DataQualityIssue]:
        """Validate data consistency across fields and records"""
        issues = []
        
        # Cross-field consistency checks
        if 'Budget' in data.columns and 'Actual' in data.columns:
            # Check for negative variances that are suspiciously large
            variance = data['Actual'] - data['Budget']
            large_negative_variance = variance[variance < -data['Budget'] * 0.5]  # More than 50% under budget
            
            if len(large_negative_variance) > 0:
                issues.append(DataQualityIssue(
                    issue_type="consistency_violation",
                    severity="Medium",
                    field_name="Budget vs Actual",
                    description="Actual spending significantly under budget (>50% variance)",
                    affected_rows=len(large_negative_variance),
                    suggested_fix="Review budget vs actual calculations for accuracy"
                ))
        
        # Check for logical inconsistencies in account codes
        if 'AccountCode' in data.columns:
            account_codes = data['AccountCode'].dropna().astype(str)
            
            # Pattern consistency check
            patterns = account_codes.str.extract(r'(\d+)-(\d+)-(\d+)-(\d+)', expand=False)
            if not patterns.dropna().empty:
                # Check for inconsistent department codes within same fund
                # This would require more domain knowledge to implement properly
                pass
        
        return issues
    
    def _detect_duplicates(self, data: pd.DataFrame) -> List[DataQualityIssue]:
        """Detect duplicate records and potential data entry errors"""
        issues = []
        
        # Exact duplicates
        exact_duplicates = data.duplicated()
        duplicate_count = exact_duplicates.sum()
        
        if duplicate_count > 0:
            issues.append(DataQualityIssue(
                issue_type="exact_duplicates",
                severity="High",
                field_name="All fields",
                description=f"Found {duplicate_count} exact duplicate records",
                affected_rows=duplicate_count,
                suggested_fix="Review and remove duplicate records",
                auto_fixable=True
            ))
        
        # Near duplicates (same amount, vendor, date within 1 day)
        if all(col in data.columns for col in ['Amount', 'Vendor', 'Date']):
            # Group by amount and vendor, check for same-day transactions
            grouped = data.groupby(['Amount', 'Vendor'])
            
            near_duplicates = 0
            for name, group in grouped:
                if len(group) > 1:
                    # Check if transactions are within 1 day of each other
                    dates = pd.to_datetime(group['Date'])
                    date_diffs = dates.diff().dt.days.abs()
                    
                    if (date_diffs <= 1).any():
                        near_duplicates += len(group) - 1
            
            if near_duplicates > 0:
                issues.append(DataQualityIssue(
                    issue_type="potential_duplicates",
                    severity="Medium",
                    field_name="Amount, Vendor, Date",
                    description=f"Found {near_duplicates} potential duplicate transactions (same amount, vendor, within 1 day)",
                    affected_rows=near_duplicates,
                    suggested_fix="Review potential duplicate transactions for legitimacy"
                ))
        
        return issues
    
    def _validate_municipal_patterns(self, data: pd.DataFrame) -> List[DataQualityIssue]:
        """Validate against municipal-specific data patterns"""
        issues = []
        
        # Validate department codes
        if 'Department' in data.columns or 'DepartmentCode' in data.columns:
            dept_column = 'Department' if 'Department' in data.columns else 'DepartmentCode'
            dept_data = data[dept_column].dropna().astype(str)
            
            valid_dept_codes = self.quality_patterns['municipal_specific']['department_codes']
            invalid_depts = dept_data[~dept_data.isin(valid_dept_codes)]
            
            if len(invalid_depts) > 0:
                issues.append(DataQualityIssue(
                    issue_type="invalid_department_code",
                    severity="Medium",
                    field_name=dept_column,
                    description=f"Invalid department codes found",
                    affected_rows=len(invalid_depts),
                    sample_values=invalid_depts.unique().tolist()[:5],
                    suggested_fix=f"Use valid department codes: {', '.join(valid_dept_codes)}"
                ))
        
        # Validate account type patterns
        if 'AccountType' in data.columns:
            account_types = data['AccountType'].dropna().astype(str).str.upper()
            valid_types = self.quality_patterns['municipal_specific']['account_types']
            
            invalid_types = account_types[~account_types.isin(valid_types)]
            
            if len(invalid_types) > 0:
                issues.append(DataQualityIssue(
                    issue_type="invalid_account_type",
                    severity="Medium",
                    field_name="AccountType",
                    description=f"Invalid account types found",
                    affected_rows=len(invalid_types),
                    sample_values=invalid_types.unique().tolist()[:5],
                    suggested_fix=f"Use valid account types: {', '.join(valid_types)}"
                ))
        
        return issues
    
    def _calculate_quality_score(self, issues: List[DataQualityIssue], total_records: int) -> float:
        """Calculate overall data quality score (0-100)"""
        if not issues:
            return 100.0
        
        # Weight issues by severity
        severity_weights = {'High': 10, 'Medium': 5, 'Low': 2}
        total_penalty = 0
        
        for issue in issues:
            weight = severity_weights.get(issue.severity, 2)
            affected_percentage = (issue.affected_rows / total_records) * 100
            penalty = weight * (affected_percentage / 100)  # Normalize by percentage of affected records
            total_penalty += penalty
        
        # Convert penalty to quality score (higher penalty = lower quality)
        quality_score = max(0, 100 - total_penalty)
        return round(quality_score, 1)
    
    def _generate_quality_recommendations(self, assessment_results: Dict[str, Any]) -> str:
        """Generate AI-powered data quality improvement recommendations"""
        issues = assessment_results.get('quality_issues', [])
        if not issues:
            return "Data quality is excellent. No significant issues detected."
        
        # Prepare issue summary for AI analysis
        issue_summary = []
        for issue in issues[:15]:  # Top 15 issues
            summary = f"- {issue.issue_type}: {issue.field_name} ({issue.affected_rows} records, {issue.severity} severity)"
            if issue.description:
                summary += f" - {issue.description}"
            issue_summary.append(summary)
        
        recommendations_prompt = f"""
        Analyze these data quality issues in municipal financial data and provide actionable recommendations:
        
        DATASET INFO:
        - Total Records: {assessment_results['total_records']:,}
        - Overall Quality Score: {assessment_results['overall_quality_score']}/100
        
        DETECTED ISSUES:
        {chr(10).join(issue_summary)}
        
        Provide professional recommendations including:
        
        1. IMMEDIATE ACTIONS: Critical issues that need immediate attention
        
        2. DATA CLEANING PLAN: Step-by-step plan to address quality issues
        
        3. PREVENTION STRATEGIES: How to prevent these issues in the future
        
        4. AUTOMATION OPPORTUNITIES: Which fixes can be automated vs require manual review
        
        5. IMPACT ASSESSMENT: How these quality issues affect financial reporting and decision-making
        
        Format as actionable guidance for municipal finance teams.
        """
        
        ai_response = self.secure_ai_request(
            recommendations_prompt,
            "data_quality_recommendations",
            data_sources=["data_quality_assessment"],
            max_tokens=2000
        )
        
        return ai_response.get('response', 'AI recommendations generation failed')
    
    def _save_quality_assessment(self, assessment_results: Dict[str, Any]):
        """Save quality assessment results to tracking database"""
        try:
            user_id = st.session_state.get('username', 'anonymous')
            
            conn = sqlite3.connect('data_quality_tracking.db')
            cursor = conn.cursor()
            
            high_severity_count = len([
                issue for issue in assessment_results['quality_issues'] 
                if issue.severity == 'High'
            ])
            
            cursor.execute('''
                INSERT INTO quality_assessments 
                (dataset_name, total_records, total_issues, high_severity_issues, 
                 quality_score, assessment_details, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                assessment_results['dataset_name'],
                assessment_results['total_records'],
                len(assessment_results['quality_issues']),
                high_severity_count,
                assessment_results['overall_quality_score'],
                json.dumps(assessment_results, default=str),
                user_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Failed to save quality assessment: {e}")
    
    def automated_data_cleaning(self, data: pd.DataFrame, 
                              quality_issues: List[DataQualityIssue],
                              user_approval: bool = False) -> Dict[str, Any]:
        """
        Perform automated data cleaning for auto-fixable issues
        
        Args:
            data: DataFrame to clean
            quality_issues: List of identified quality issues
            user_approval: Whether user has approved automated fixes
            
        Returns:
            Cleaned data and cleaning report
        """
        if not user_approval:
            return {
                'error': 'User approval required for automated data cleaning',
                'auto_fixable_issues': [issue for issue in quality_issues if issue.auto_fixable]
            }
        
        cleaned_data = data.copy()
        cleaning_actions = []
        
        for issue in quality_issues:
            if issue.auto_fixable:
                if issue.issue_type == "exact_duplicates":
                    # Remove exact duplicates
                    original_count = len(cleaned_data)
                    cleaned_data = cleaned_data.drop_duplicates()
                    removed_count = original_count - len(cleaned_data)
                    
                    cleaning_actions.append({
                        'action': 'remove_exact_duplicates',
                        'field': 'all_fields',
                        'records_affected': removed_count,
                        'description': f'Removed {removed_count} exact duplicate records'
                    })
                
                elif issue.issue_type == "data_type_mismatch" and "numeric" in issue.suggested_fix:
                    # Convert text fields to numeric
                    try:
                        cleaned_data[issue.field_name] = pd.to_numeric(
                            cleaned_data[issue.field_name], errors='coerce'
                        )
                        
                        cleaning_actions.append({
                            'action': 'convert_data_type',
                            'field': issue.field_name,
                            'records_affected': issue.affected_rows,
                            'description': f'Converted {issue.field_name} to numeric type'
                        })
                    except Exception as e:
                        cleaning_actions.append({
                            'action': 'convert_data_type_failed',
                            'field': issue.field_name,
                            'error': str(e)
                        })
        
        # Save cleaning actions to database
        self._save_cleaning_actions(cleaning_actions)
        
        return {
            'cleaned_data': cleaned_data,
            'cleaning_actions': cleaning_actions,
            'original_records': len(data),
            'cleaned_records': len(cleaned_data),
            'records_modified': len(data) - len(cleaned_data)
        }
    
    def _save_cleaning_actions(self, cleaning_actions: List[Dict[str, Any]]):
        """Save data cleaning actions to tracking database"""
        try:
            user_id = st.session_state.get('username', 'anonymous')
            
            conn = sqlite3.connect('data_quality_tracking.db')
            cursor = conn.cursor()
            
            for action in cleaning_actions:
                cursor.execute('''
                    INSERT INTO cleaning_actions 
                    (dataset_name, action_type, field_name, records_affected, action_details, user_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'unknown',  # Would need to track dataset name
                    action.get('action', 'unknown'),
                    action.get('field', ''),
                    action.get('records_affected', 0),
                    json.dumps(action),
                    user_id
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Failed to save cleaning actions: {e}")