"""
Unit tests for input validation module
Ensures comprehensive validation coverage for all input types
"""

import pytest
import sys
import os
import tempfile
from unittest.mock import Mock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.security import (
    validate_file_upload,
    sanitize_html_input,
    validate_numeric_input,
    validate_email_address,
    validate_phone_number,
    validate_date_input,
    sanitize_search_query,
    validate_url
)

class TestFileUploadValidation:
    """Test file upload validation"""
    
    def create_mock_file(self, name: str, size: int):
        """Create mock uploaded file"""
        mock_file = Mock()
        mock_file.name = name
        mock_file.size = size
        return mock_file
    
    def test_validate_file_upload_valid(self):
        """Test valid file uploads"""
        valid_files = [
            ("document.pdf", 1024 * 1024),  # 1MB PDF
            ("report.txt", 500 * 1024),     # 500KB text
            ("budget.xlsx", 2 * 1024 * 1024), # 2MB Excel
            ("data.csv", 1024 * 512)        # 512KB CSV
        ]
        
        for name, size in valid_files:
            mock_file = self.create_mock_file(name, size)
            assert validate_file_upload(mock_file) is True
    
    def test_validate_file_upload_invalid_extension(self):
        """Test invalid file extensions"""
        invalid_files = [
            ("malware.exe", 1024),
            ("script.bat", 1024),
            ("code.js", 1024),
            ("image.png", 1024)  # Not in default allowed list
        ]
        
        for name, size in invalid_files:
            mock_file = self.create_mock_file(name, size)
            with pytest.raises(ValueError, match="not allowed"):
                validate_file_upload(mock_file)
    
    def test_validate_file_upload_too_large(self):
        """Test file size validation"""
        large_file = self.create_mock_file("document.pdf", 15 * 1024 * 1024)  # 15MB
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_file_upload(large_file, max_size_mb=10)
    
    def test_validate_file_upload_suspicious_name(self):
        """Test suspicious file name detection"""
        suspicious_files = [
            ("../../../etc/passwd.txt", 1024),
            ("<script>alert.txt", 1024),
            ("javascript:void.pdf", 1024),
            ("<?php echo.txt", 1024)
        ]
        
        for name, size in suspicious_files:
            mock_file = self.create_mock_file(name, size)
            with pytest.raises(ValueError, match="suspicious patterns"):
                validate_file_upload(mock_file)


class TestHTMLSanitization:
    """Test HTML input sanitization"""
    
    def test_sanitize_html_input_safe(self):
        """Test sanitizing safe HTML input"""
        safe_inputs = [
            ("Normal text input", "Normal text input"),
            ("Budget Report 2024", "Budget Report 2024"),
            ("Department: Police & Fire", "Department: Police &amp; Fire")  # & gets escaped
        ]
        
        for input_str, expected in safe_inputs:
            result = sanitize_html_input(input_str)
            assert result == expected
    
    def test_sanitize_html_input_dangerous(self):
        """Test sanitizing dangerous HTML input"""
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "<iframe src='malicious.com'></iframe>",
            "<img src='x' onerror='alert(1)'>",
            "javascript:alert('xss')",
            "<link rel='stylesheet' href='malicious.css'>"
        ]
        
        for input_str in dangerous_inputs:
            result = sanitize_html_input(input_str)
            # Should not contain dangerous patterns
            assert "<script" not in result.lower()
            assert "javascript:" not in result.lower()
            assert "onerror=" not in result.lower()


class TestNumericValidation:
    """Test numeric input validation"""
    
    def test_validate_numeric_input_valid(self):
        """Test valid numeric inputs"""
        valid_inputs = [
            (100, 100.0),
            ("250.50", 250.5),
            ("$1,234.56", 1234.56),
            (" 500 ", 500.0)
        ]
        
        for input_val, expected in valid_inputs:
            result = validate_numeric_input(input_val)
            assert result == expected
    
    def test_validate_numeric_input_with_bounds(self):
        """Test numeric validation with bounds"""
        # Valid within bounds
        assert validate_numeric_input(50, min_value=0, max_value=100) == 50.0
        
        # Below minimum
        with pytest.raises(ValueError, match="below minimum"):
            validate_numeric_input(-10, min_value=0)
        
        # Above maximum
        with pytest.raises(ValueError, match="above maximum"):
            validate_numeric_input(150, min_value=0, max_value=100)
    
    def test_validate_numeric_input_invalid(self):
        """Test invalid numeric inputs"""
        invalid_inputs = [
            "not a number",
            "abc123",
            "",
            None
        ]
        
        for input_val in invalid_inputs:
            with pytest.raises(ValueError, match="Invalid numeric value"):
                validate_numeric_input(input_val)


class TestEmailValidation:
    """Test email address validation"""
    
    def test_validate_email_valid(self):
        """Test valid email addresses"""
        valid_emails = [
            "user@example.com",
            "admin@city.gov",
            "finance.director@municipality.org",
            "test123+tag@domain.co.uk"
        ]
        
        for email in valid_emails:
            result = validate_email_address(email)
            assert result == email.lower().strip()
    
    def test_validate_email_invalid(self):
        """Test invalid email addresses"""
        invalid_emails = [
            "not.an.email",
            "@domain.com",
            "user@",
            "user..double@domain.com",
            ".leading@domain.com",
            "trailing.@domain.com",
            "",
            None
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email"):
                validate_email_address(email)


class TestPhoneValidation:
    """Test phone number validation"""
    
    def test_validate_phone_valid(self):
        """Test valid phone numbers"""
        valid_phones = [
            ("1234567890", "(123) 456-7890"),
            ("11234567890", "+1 (123) 456-7890"),
            ("(123) 456-7890", "(123) 456-7890"),
            ("123-456-7890", "(123) 456-7890")
        ]
        
        for input_phone, expected in valid_phones:
            result = validate_phone_number(input_phone)
            assert result == expected
    
    def test_validate_phone_invalid(self):
        """Test invalid phone numbers"""
        invalid_phones = [
            "123456789",      # Too short
            "123456789012",   # Too long
            "abc1234567",     # Contains letters
            "",               # Empty
            None              # None
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValueError, match="Invalid phone number"):
                validate_phone_number(phone)


class TestDateValidation:
    """Test date input validation"""
    
    def test_validate_date_valid(self):
        """Test valid date inputs"""
        valid_dates = [
            "2024-01-15",
            "2023-12-31",
            "2025-06-23"
        ]
        
        for date_str in valid_dates:
            result = validate_date_input(date_str)
            assert result == date_str
    
    def test_validate_date_invalid_format(self):
        """Test invalid date formats"""
        invalid_dates = [
            "2024/01/15",     # Wrong separator
            "01-15-2024",     # Wrong order
            "2024-13-01",     # Invalid month
            "2024-01-32",     # Invalid day
            "not-a-date",     # Not a date
            ""                # Empty
        ]
        
        for date_str in invalid_dates:
            with pytest.raises(ValueError, match="Invalid date format"):
                validate_date_input(date_str)
    
    def test_validate_date_out_of_range(self):
        """Test dates outside reasonable range"""
        out_of_range_dates = [
            "1800-01-01",     # Too old
            "2150-01-01"      # Too far in future
        ]
        
        for date_str in out_of_range_dates:
            with pytest.raises(ValueError, match="Date must be between"):
                validate_date_input(date_str)


class TestSearchQuerySanitization:
    """Test search query sanitization"""
    
    def test_sanitize_search_query_valid(self):
        """Test valid search queries"""
        valid_queries = [
            "budget analysis",
            "department performance 2024",
            "police fire department",
            "fiscal year report"
        ]
        
        for query in valid_queries:
            result = sanitize_search_query(query)
            assert result == query
    
    def test_sanitize_search_query_dangerous(self):
        """Test sanitizing dangerous search queries"""
        dangerous_queries = [
            "budget<script>",
            'department"malicious',
            "search;DROP TABLE",
            "query\\injection"
        ]
        
        for query in dangerous_queries:
            result = sanitize_search_query(query)
            # Should not contain dangerous characters
            assert "<" not in result
            assert "'" not in result
            assert '"' not in result
            assert ";" not in result
    
    def test_sanitize_search_query_too_long(self):
        """Test search query length validation"""
        long_query = "a" * 201
        
        with pytest.raises(ValueError, match="too long"):
            sanitize_search_query(long_query, max_length=200)
    
    def test_sanitize_search_query_empty(self):
        """Test empty search query handling"""
        empty_queries = ["", "   ", None]
        
        for query in empty_queries:
            with pytest.raises(ValueError, match="cannot be empty"):
                sanitize_search_query(query)


class TestURLValidation:
    """Test URL validation"""
    
    def test_validate_url_valid(self):
        """Test valid URLs"""
        valid_urls = [
            "https://example.com",
            "http://city.gov/budget",
            "https://municipality.org/reports/annual.pdf"
        ]
        
        for url in valid_urls:
            result = validate_url(url)
            assert result == url
    
    def test_validate_url_invalid_format(self):
        """Test invalid URL formats"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",      # Wrong protocol
            "https://",               # Incomplete
            "https://local host",     # Space in hostname
            ""                        # Empty
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError, match="Invalid URL"):
                validate_url(url)
    
    def test_validate_url_private_addresses(self):
        """Test blocking private/local addresses"""
        private_urls = [
            "http://127.0.0.1",
            "https://10.0.0.1",
            "http://192.168.1.1",
            "https://172.16.0.1",
            "http://169.254.1.1"
        ]
        
        for url in private_urls:
            with pytest.raises(ValueError, match="private/local addresses"):
                validate_url(url)


if __name__ == "__main__":
    # Run the tests
    pytest.main(["-v", __file__])