"""
User Database Management - Admin Module
Handles user data storage and retrieval using SQLite

Focused on user database operations only (~200 lines)
"""

import sqlite3
import os
from typing import Dict, List, Optional, Any
import hashlib
import hmac
from modules.security.secret_manager import get_secret

# Production database path - unified for dev and production
from modules.admin.database_config import PRODUCTION_USERS_DB
USERS_DB_PATH = PRODUCTION_USERS_DB

# Default users for initial setup
# NOTE: admin_user now uses standard password like other users
# Super admin functions will separately require ADMIN_PASSWORD secret
DEFAULT_USERS = [
    {"username": "admin_user", "role": "admin", "departments": "all", "password": "govsight123"},
    {"username": "finance_director", "role": "finance", "departments": "all", "password": "govsight123"},
    {"username": "pw_manager", "role": "manager", "departments": "Public Works", "password": "govsight123"},
    {"username": "police_manager", "role": "manager", "departments": "Police", "password": "govsight123"},
    {"username": "parks_manager", "role": "manager", "departments": "Parks & Rec", "password": "govsight123"},
]

def init_users_db():
    """Initialize the users database with default users"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(USERS_DB_PATH), exist_ok=True)
    
    # Remove file if it exists but is not a valid database
    if os.path.exists(USERS_DB_PATH):
        try:
            # Test if file is a valid SQLite database
            test_conn = sqlite3.connect(USERS_DB_PATH)
            test_conn.execute("SELECT 1")
            test_conn.close()
        except sqlite3.DatabaseError:
            # File exists but is not a valid database, remove it
            os.remove(USERS_DB_PATH)
    
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            departments TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            active BOOLEAN DEFAULT 1
        )
    """)
    
    # Check if users already exist
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    # If no users exist, create default users
    if user_count == 0:
        for user in DEFAULT_USERS:
            hashed_password = hash_password(user["password"])
            cursor.execute("""
                INSERT INTO users (username, password, role, departments)
                VALUES (?, ?, ?, ?)
            """, (user["username"], hashed_password, user["role"], user["departments"]))
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (simple hashing for demo purposes)"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username: str, password: str) -> bool:
    """
    Verify user credentials against database.
    
    For all users including admin_user: Checks against database with hashed passwords
    Super admin functions will separately require ADMIN_PASSWORD secret
    
    This allows admin users to login normally while keeping super admin functions protected.
    """
    if not username or not password:
        return False
    
    # Regular authentication for all users including admin_user
    # Check against database - no special handling for admin_user anymore
    
    # Check database with hashed password for all users
    # Note: Database should already be initialized by main_app.py on startup
    # We don't call init_users_db() here to avoid resetting passwords
    
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        hashed_password = hash_password(password)
        cursor.execute("""
            SELECT id FROM users 
            WHERE LOWER(username) = LOWER(?) AND password = ? AND active = 1
        """, (username, hashed_password))
        
        result = cursor.fetchone()
        
        # Update last login if authentication successful
        if result:
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP 
                WHERE LOWER(username) = LOWER(?)
            """, (username,))
            conn.commit()
        
        return result is not None
        
    except Exception as e:
        print(f"Authentication error: {e}")
        return False
    finally:
        conn.close()

def get_user_info(username: str) -> Optional[Dict[str, Any]]:
    """Get user information from database"""
    if not username:
        return None
    
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT username, role, departments, created_at, last_login, active
            FROM users WHERE LOWER(username) = LOWER(?) AND active = 1
        """, (username,))
        
        row = cursor.fetchone()
        if row:
            return {
                "username": row[0],
                "role": row[1], 
                "departments": row[2],
                "created_at": row[3],
                "last_login": row[4],
                "active": bool(row[5])
            }
        return None
        
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None
    finally:
        conn.close()

def get_user_role(username: str) -> str:
    """Get user role"""
    user_info = get_user_info(username)
    return user_info.get("role", "viewer") if user_info else "viewer"

def get_user_departments(username: str):
    """Get user departments"""
    user_info = get_user_info(username)
    if not user_info:
        return []
    
    departments = user_info.get("departments", "")
    if departments == "all":
        return "all"
    return departments.split(",") if departments else []

def create_user(username: str, password: str, role: str, departments: str) -> bool:
    """Create a new user"""
    if not username or not password:
        return False
    
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        hashed_password = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password, role, departments)
            VALUES (?, ?, ?, ?)
        """, (username, hashed_password, role, departments))
        conn.commit()
        return True
        
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    except Exception as e:
        print(f"Error creating user: {e}")
        return False
    finally:
        conn.close()

def update_user(username: str, role: str = None, departments: str = None, password: str = None) -> bool:
    """Update user information"""
    if not username:
        return False
    
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        updates = []
        params = []
        
        if role:
            updates.append("role = ?")
            params.append(role)
        if departments:
            updates.append("departments = ?") 
            params.append(departments)
        if password:
            updates.append("password = ?")
            params.append(hash_password(password))
        
        if not updates:
            return False
        
        params.append(username)
        query = f"UPDATE users SET {', '.join(updates)} WHERE LOWER(username) = LOWER(?)"
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error updating user: {e}")
        return False
    finally:
        conn.close()

def delete_user(username: str) -> bool:
    """Deactivate user (soft delete)"""
    if not username:
        return False
    
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE users SET active = 0 WHERE LOWER(username) = LOWER(?)", (username,))
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        conn.close()

def list_all_users() -> List[Dict[str, Any]]:
    """Get all active users"""
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT username, role, departments, created_at, last_login
            FROM users WHERE active = 1 ORDER BY username
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "username": row[0],
                "role": row[1],
                "departments": row[2],
                "created_at": row[3],
                "last_login": row[4]
            })
        return users
        
    except Exception as e:
        print(f"Error listing users: {e}")
        return []
    finally:
        conn.close()

# NOTE: Database initialization is handled by main_app.py on startup
# We do NOT auto-initialize here to prevent unexpected password resets
# If you need to manually initialize, run: python -c "from modules.admin.user_database import init_users_db; init_users_db()"