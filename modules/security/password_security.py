"""
Password Security Module for GovSight Financial Analyzer

This module implements secure password hashing and validation to replace
plain text password storage identified in the security audit.
"""

import hashlib
import secrets
import os
from typing import Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_salt() -> str:
    """
    Generate a cryptographically secure random salt
    
    Returns:
        str: Random salt as hex string
    """
    return secrets.token_hex(16)

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash a password using PBKDF2 with SHA-256
    
    Args:
        password (str): Plain text password to hash
        salt (str, optional): Salt to use. If None, generates new salt.
        
    Returns:
        Tuple[str, str]: (hashed_password, salt)
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    if salt is None:
        salt = generate_salt()
    
    # Use PBKDF2 with 100,000 iterations for security
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    
    return password_hash.hex(), salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """
    Verify a password against its stored hash
    
    Args:
        password (str): Plain text password to verify
        stored_hash (str): Stored password hash
        salt (str): Salt used for hashing
        
    Returns:
        bool: True if password matches, False otherwise
    """
    if not password or not stored_hash or not salt:
        return False
    
    try:
        # Hash the provided password with the same salt
        computed_hash, _ = hash_password(password, salt)
        
        # Compare hashes securely (constant time comparison)
        return secrets.compare_digest(computed_hash, stored_hash)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password
    
    Args:
        length (int): Length of password to generate
        
    Returns:
        str: Generated password
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")
    
    # Use a mix of letters, digits, and special characters
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return password

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength according to security requirements
    
    Args:
        password (str): Password to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not has_upper:
        return False, "Password must contain at least one uppercase letter"
    
    if not has_lower:
        return False, "Password must contain at least one lowercase letter"
    
    if not has_digit:
        return False, "Password must contain at least one digit"
    
    if not has_special:
        return False, "Password must contain at least one special character"
    
    # Check for common weak passwords
    weak_passwords = {
        "password", "123456", "password123", "admin", "govsight123",
        "administrator", "root", "guest", "user", "test"
    }
    
    if password.lower() in weak_passwords:
        return False, "Password is too common or weak"
    
    return True, "Password strength is acceptable"

def create_session_token() -> str:
    """
    Create a secure session token for user authentication
    
    Returns:
        str: Secure session token
    """
    return secrets.token_urlsafe(32)

def migrate_plain_text_passwords(users_data: list) -> list:
    """
    Migrate existing plain text passwords to hashed passwords
    
    Args:
        users_data (list): List of user dictionaries with plain text passwords
        
    Returns:
        list: Updated user data with hashed passwords
    """
    migrated_users = []
    
    for user in users_data:
        if "password" in user and not user.get("password_hashed", False):
            # Hash the plain text password
            password_hash, salt = hash_password(user["password"])
            
            # Update user record
            updated_user = user.copy()
            updated_user["password_hash"] = password_hash
            updated_user["password_salt"] = salt
            updated_user["password_hashed"] = True
            
            # Remove plain text password
            if "password" in updated_user:
                del updated_user["password"]
            
            migrated_users.append(updated_user)
            logger.info(f"Migrated password for user: {user.get('username', 'unknown')}")
        else:
            migrated_users.append(user)
    
    return migrated_users

def secure_compare(a: str, b: str) -> bool:
    """
    Perform constant-time string comparison to prevent timing attacks
    
    Args:
        a (str): First string
        b (str): Second string
        
    Returns:
        bool: True if strings are equal
    """
    return secrets.compare_digest(a.encode('utf-8'), b.encode('utf-8'))