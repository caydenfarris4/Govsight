"""
Unit tests for password security module
Ensures secure password hashing and validation
"""

import pytest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.security import (
    generate_salt,
    hash_password,
    verify_password,
    generate_secure_password,
    validate_password_strength,
    create_session_token,
    migrate_plain_text_passwords,
    secure_compare
)

class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_generate_salt(self):
        """Test salt generation"""
        salt1 = generate_salt()
        salt2 = generate_salt()
        
        assert isinstance(salt1, str)
        assert isinstance(salt2, str)
        assert len(salt1) == 32  # 16 bytes as hex = 32 chars
        assert len(salt2) == 32
        assert salt1 != salt2  # Should be unique
    
    def test_hash_password_with_salt(self):
        """Test password hashing with provided salt"""
        password = "TestPassword123!"
        salt = "abcd1234efgh5678"
        
        hash1, returned_salt = hash_password(password, salt)
        hash2, _ = hash_password(password, salt)
        
        assert isinstance(hash1, str)
        assert returned_salt == salt
        assert hash1 == hash2  # Same password + salt = same hash
        assert len(hash1) == 64  # SHA-256 hash as hex = 64 chars
    
    def test_hash_password_auto_salt(self):
        """Test password hashing with automatic salt generation"""
        password = "TestPassword123!"
        
        hash1, salt1 = hash_password(password)
        hash2, salt2 = hash_password(password)
        
        assert isinstance(hash1, str)
        assert isinstance(salt1, str)
        assert hash1 != hash2  # Different salts = different hashes
        assert salt1 != salt2  # Different salts
    
    def test_hash_password_empty(self):
        """Test hashing empty password raises error"""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            hash_password("")
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        password_hash, salt = hash_password(password)
        
        assert verify_password(password, password_hash, salt) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        password_hash, salt = hash_password(password)
        
        assert verify_password(wrong_password, password_hash, salt) is False
    
    def test_verify_password_empty_inputs(self):
        """Test password verification with empty inputs"""
        assert verify_password("", "hash", "salt") is False
        assert verify_password("password", "", "salt") is False
        assert verify_password("password", "hash", "") is False


class TestPasswordGeneration:
    """Test password generation functionality"""
    
    def test_generate_secure_password_default(self):
        """Test generating secure password with default length"""
        password = generate_secure_password()
        
        assert isinstance(password, str)
        assert len(password) == 16
        
        # Check for character variety
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        # Should have at least some variety (not guaranteed every time but likely)
        assert has_upper or has_lower or has_digit
    
    def test_generate_secure_password_custom_length(self):
        """Test generating secure password with custom length"""
        password = generate_secure_password(12)
        
        assert len(password) == 12
    
    def test_generate_secure_password_minimum_length(self):
        """Test password generation with minimum length requirement"""
        with pytest.raises(ValueError, match="Password length must be at least 8"):
            generate_secure_password(7)
    
    def test_generate_secure_password_uniqueness(self):
        """Test that generated passwords are unique"""
        password1 = generate_secure_password()
        password2 = generate_secure_password()
        
        assert password1 != password2


class TestPasswordStrengthValidation:
    """Test password strength validation"""
    
    def test_validate_strong_password(self):
        """Test validation of strong passwords"""
        strong_passwords = [
            "StrongPass123!",
            "MySecure#Password1",
            "Complex$Password99"
        ]
        
        for password in strong_passwords:
            is_valid, message = validate_password_strength(password)
            assert is_valid is True
            assert message == "Password strength is acceptable"
    
    def test_validate_weak_passwords(self):
        """Test validation rejects weak passwords"""
        weak_cases = [
            ("short", "Password must be at least 8 characters long"),
            ("nouppercase123!", "Password must contain at least one uppercase letter"),
            ("NOLOWERCASE123!", "Password must contain at least one lowercase letter"),
            ("NoDigitsInThis!", "Password must contain at least one digit"),
            ("NoSpecialChars123", "Password must contain at least one special character"),
            ("Password123!", "Password is too common or weak"),
            ("123456", "Password is too common or weak"),
            ("Govsight123!", "Password is too common or weak")
        ]
        
        for password, expected_message in weak_cases:
            is_valid, message = validate_password_strength(password)
            assert is_valid is False
            assert expected_message in message
    
    def test_validate_password_too_long(self):
        """Test validation rejects overly long passwords"""
        long_password = "A" * 129 + "1!"
        is_valid, message = validate_password_strength(long_password)
        
        assert is_valid is False
        assert "less than 128 characters" in message


class TestSessionSecurity:
    """Test session token generation"""
    
    def test_create_session_token(self):
        """Test session token creation"""
        token1 = create_session_token()
        token2 = create_session_token()
        
        assert isinstance(token1, str)
        assert isinstance(token2, str)
        assert len(token1) > 20  # Should be reasonably long
        assert token1 != token2  # Should be unique


class TestPasswordMigration:
    """Test password migration from plain text to hashed"""
    
    def test_migrate_plain_text_passwords(self):
        """Test migrating plain text passwords to hashed passwords"""
        users_data = [
            {
                "username": "admin",
                "password": "govsight123",
                "role": "admin"
            },
            {
                "username": "user1",
                "password": "password123",
                "role": "user"
            },
            {
                "username": "user2",
                "password_hash": "existing_hash",
                "password_salt": "existing_salt",
                "password_hashed": True,
                "role": "user"
            }
        ]
        
        migrated = migrate_plain_text_passwords(users_data)
        
        assert len(migrated) == 3
        
        # Check first user (admin)
        admin_user = migrated[0]
        assert "password" not in admin_user
        assert "password_hash" in admin_user
        assert "password_salt" in admin_user
        assert admin_user["password_hashed"] is True
        
        # Check second user (user1)
        user1 = migrated[1]
        assert "password" not in user1
        assert "password_hash" in user1
        assert "password_salt" in user1
        assert user1["password_hashed"] is True
        
        # Check third user (already hashed)
        user2 = migrated[2]
        assert user2["password_hash"] == "existing_hash"
        assert user2["password_salt"] == "existing_salt"
        assert user2["password_hashed"] is True
    
    def test_migrate_empty_list(self):
        """Test migrating empty user list"""
        migrated = migrate_plain_text_passwords([])
        assert migrated == []


class TestSecureComparison:
    """Test secure string comparison"""
    
    def test_secure_compare_equal(self):
        """Test secure comparison with equal strings"""
        assert secure_compare("test", "test") is True
        assert secure_compare("password123", "password123") is True
    
    def test_secure_compare_different(self):
        """Test secure comparison with different strings"""
        assert secure_compare("test", "different") is False
        assert secure_compare("password123", "password124") is False
    
    def test_secure_compare_empty(self):
        """Test secure comparison with empty strings"""
        assert secure_compare("", "") is True
        assert secure_compare("test", "") is False
        assert secure_compare("", "test") is False


if __name__ == "__main__":
    # Run the tests
    pytest.main(["-v", __file__])