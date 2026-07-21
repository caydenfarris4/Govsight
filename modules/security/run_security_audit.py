"""
Comprehensive Security Audit Script
Scans entire GovSight application for security vulnerabilities
"""

import os
import re
import subprocess
import json
from typing import List, Dict, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityAuditor:
    """Comprehensive security auditing for GovSight application"""
    
    def __init__(self, project_path: str = "."):
        self.project_path = project_path
        self.vulnerabilities = []
        self.fixes_applied = []
        
    def scan_sql_injection_vulnerabilities(self) -> List[Dict]:
        """Scan for SQL injection vulnerabilities"""
        logger.info("Scanning for SQL injection vulnerabilities...")
        
        vulnerabilities = []
        
        # Patterns that indicate potential SQL injection
        dangerous_patterns = [
            r'f".*SELECT.*{.*}"',  # f-string with SELECT
            r'f\'.*SELECT.*{.*}\'',  # f-string with SELECT (single quotes)
            r'\.format\(.*\).*SELECT',  # .format() with SELECT
            r'\+.*SELECT',  # String concatenation with SELECT
            r'%.*SELECT',  # % formatting with SELECT
        ]
        
        python_files = []
        for root, dirs, files in os.walk(self.project_path):
            # Skip cache and library directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    python_files.append(os.path.join(root, file))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in dangerous_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                vulnerabilities.append({
                                    'file': file_path,
                                    'line': line_num,
                                    'code': line.strip(),
                                    'type': 'SQL_INJECTION',
                                    'severity': 'HIGH',
                                    'description': 'Potential SQL injection vulnerability'
                                })
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        return vulnerabilities
    
    def scan_input_validation_issues(self) -> List[Dict]:
        """Scan for input validation issues"""
        logger.info("Scanning for input validation issues...")
        
        vulnerabilities = []
        
        # Patterns indicating missing input validation
        validation_patterns = [
            r'request\.args\.get\([^,]+\)(?!\s*or\s)',  # Flask request args without validation
            r'st\.text_input\([^,]+\)(?!\s*if\s)',  # Streamlit input without validation
            r'st\.selectbox\([^,]+\)(?!\s*if\s)',  # Streamlit selectbox without validation
            r'input\(\)(?!\s*if\s)',  # Raw input() without validation
        ]
        
        python_files = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in validation_patterns:
                            if re.search(pattern, line):
                                vulnerabilities.append({
                                    'file': file_path,
                                    'line': line_num,
                                    'code': line.strip(),
                                    'type': 'INPUT_VALIDATION',
                                    'severity': 'MEDIUM',
                                    'description': 'User input may lack proper validation'
                                })
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        return vulnerabilities
    
    def scan_hardcoded_secrets(self) -> List[Dict]:
        """Scan for hardcoded secrets and credentials"""
        logger.info("Scanning for hardcoded secrets...")
        
        vulnerabilities = []
        
        # Patterns for potential secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']{3,}["\']',
            r'api_key\s*=\s*["\'][^"\']{10,}["\']',
            r'secret\s*=\s*["\'][^"\']{10,}["\']',
            r'token\s*=\s*["\'][^"\']{10,}["\']',
        ]
        
        python_files = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith(('.py', '.json', '.yaml', '.yml')):
                    python_files.append(os.path.join(root, file))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in secret_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                vulnerabilities.append({
                                    'file': file_path,
                                    'line': line_num,
                                    'code': line.strip()[:50] + '...',
                                    'type': 'HARDCODED_SECRET',
                                    'severity': 'HIGH',
                                    'description': 'Potential hardcoded credential'
                                })
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        return vulnerabilities
    
    def verify_security_fixes(self) -> Dict:
        """Verify that security fixes have been properly implemented"""
        logger.info("Verifying security fixes...")
        
        verification_results = {
            'sql_injection_prevention': False,
            'input_validation': False,
            'parameterized_queries': False,
            'security_module': False
        }
        
        # Check for security module
        security_files = [
            'security_sql_injection_fixes.py',
            'modules/security/__init__.py'
        ]
        
        for security_file in security_files:
            if os.path.exists(security_file):
                verification_results['security_module'] = True
                break
        
        # Check for parameterized query usage
        try:
            with open('db_connection.py', 'r') as f:
                content = f.read()
                if 'execute_safe_query' in content or 'cursor.execute(query, params)' in content:
                    verification_results['parameterized_queries'] = True
        except FileNotFoundError:
            pass
        
        # Check for SQL injection prevention
        try:
            with open('security_sql_injection_fixes.py', 'r') as f:
                content = f.read()
                if 'SQLSecurityValidator' in content:
                    verification_results['sql_injection_prevention'] = True
        except FileNotFoundError:
            pass
        
        return verification_results
    
    def run_comprehensive_audit(self) -> Dict:
        """Run comprehensive security audit"""
        logger.info("Starting comprehensive security audit...")
        
        audit_results = {
            'sql_injection_vulnerabilities': self.scan_sql_injection_vulnerabilities(),
            'input_validation_issues': self.scan_input_validation_issues(),
            'hardcoded_secrets': self.scan_hardcoded_secrets(),
            'security_fixes_verification': self.verify_security_fixes(),
            'summary': {}
        }
        
        # Generate summary
        total_vulnerabilities = (
            len(audit_results['sql_injection_vulnerabilities']) +
            len(audit_results['input_validation_issues']) +
            len(audit_results['hardcoded_secrets'])
        )
        
        audit_results['summary'] = {
            'total_vulnerabilities': total_vulnerabilities,
            'sql_injection_count': len(audit_results['sql_injection_vulnerabilities']),
            'input_validation_count': len(audit_results['input_validation_issues']),
            'hardcoded_secrets_count': len(audit_results['hardcoded_secrets']),
            'security_score': self.calculate_security_score(audit_results)
        }
        
        return audit_results
    
    def calculate_security_score(self, audit_results: Dict) -> int:
        """Calculate security score (0-100)"""
        base_score = 100
        
        # Deduct points for vulnerabilities
        high_severity_count = (
            len(audit_results['sql_injection_vulnerabilities']) +
            len(audit_results['hardcoded_secrets'])
        )
        medium_severity_count = len(audit_results['input_validation_issues'])
        
        # High severity: -10 points each
        # Medium severity: -5 points each
        deductions = (high_severity_count * 10) + (medium_severity_count * 5)
        
        # Add points for security fixes
        fixes = audit_results['security_fixes_verification']
        points_added = sum([
            15 if fixes['sql_injection_prevention'] else 0,
            10 if fixes['parameterized_queries'] else 0,
            10 if fixes['input_validation'] else 0,
            5 if fixes['security_module'] else 0
        ])
        
        final_score = max(0, min(100, base_score - deductions + points_added))
        return final_score
    
    def generate_security_report(self, audit_results: Dict) -> str:
        """Generate comprehensive security report"""
        report = []
        report.append("=" * 60)
        report.append("GOVSIGHT SECURITY AUDIT REPORT")
        report.append("=" * 60)
        report.append("")
        
        summary = audit_results['summary']
        report.append(f"Security Score: {summary['security_score']}/100")
        report.append(f"Total Vulnerabilities Found: {summary['total_vulnerabilities']}")
        report.append("")
        
        # SQL Injection Vulnerabilities
        if audit_results['sql_injection_vulnerabilities']:
            report.append("SQL INJECTION VULNERABILITIES (HIGH SEVERITY)")
            report.append("-" * 50)
            for vuln in audit_results['sql_injection_vulnerabilities']:
                report.append(f"File: {vuln['file']}:{vuln['line']}")
                report.append(f"Code: {vuln['code']}")
                report.append(f"Description: {vuln['description']}")
                report.append("")
        
        # Input Validation Issues
        if audit_results['input_validation_issues']:
            report.append("INPUT VALIDATION ISSUES (MEDIUM SEVERITY)")
            report.append("-" * 50)
            for vuln in audit_results['input_validation_issues']:
                report.append(f"File: {vuln['file']}:{vuln['line']}")
                report.append(f"Code: {vuln['code']}")
                report.append("")
        
        # Security Fixes Verification
        report.append("SECURITY FIXES VERIFICATION")
        report.append("-" * 30)
        fixes = audit_results['security_fixes_verification']
        for fix_name, implemented in fixes.items():
            status = "✓ IMPLEMENTED" if implemented else "✗ MISSING"
            report.append(f"{fix_name}: {status}")
        
        report.append("")
        report.append("RECOMMENDATIONS:")
        report.append("-" * 20)
        
        if summary['sql_injection_count'] > 0:
            report.append("1. Implement parameterized queries for all database operations")
        if summary['input_validation_count'] > 0:
            report.append("2. Add comprehensive input validation for all user inputs")
        if summary['hardcoded_secrets_count'] > 0:
            report.append("3. Move hardcoded secrets to environment variables")
        
        if summary['security_score'] >= 85:
            report.append("\n✓ SECURITY AUDIT PASSED - Score >= 85")
        else:
            report.append(f"\n✗ SECURITY AUDIT FAILED - Score {summary['security_score']} < 85")
        
        return "\n".join(report)

def main():
    """Run security audit"""
    auditor = SecurityAuditor()
    results = auditor.run_comprehensive_audit()
    
    # Generate and save report
    report = auditor.generate_security_report(results)
    
    with open('security_audit_report.txt', 'w') as f:
        f.write(report)
    
    # Save detailed results as JSON
    with open('security_audit_details.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(report)
    
    return results['summary']['security_score'] >= 85

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)