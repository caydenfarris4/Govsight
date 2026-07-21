"""
Authentication API endpoints for GovSight
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
import jwt
from modules.admin.database_config import PRODUCTION_USERS_DB

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: str
    username: str
    email: str
    role: str
    department: Optional[str] = None
    permissions: list[str] = []

def get_db_connection():
    """Get connection to users database"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def init_users_db():
    """Initialize users database with default admin user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user',
            department TEXT,
            permissions TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            sso_enabled BOOLEAN DEFAULT 0,
            sso_required BOOLEAN DEFAULT 0
        )
    """)
    
    # Add SSO columns if they don't exist (for existing databases)
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'sso_enabled' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN sso_enabled BOOLEAN DEFAULT 0")
    
    if 'sso_required' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN sso_required BOOLEAN DEFAULT 0")
    
    # Create default admin user if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    
    if count == 0:
        admin_password_hash = hash_password("admin123")  # Default password
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, role, permissions)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "admin",
            admin_password_hash,
            "admin@govsight.gov",
            "admin",
            json.dumps(["all"])
        ))
        
        # Add sample users
        users = [
            ("jdoe", "password123", "jdoe@govsight.gov", "Finance Director", "Finance", ["finance", "reports"]),
            ("asmith", "password123", "asmith@govsight.gov", "Analyst", "Budget", ["view", "analyze"]),
            ("bwilson", "password123", "bwilson@govsight.gov", "Department Head", "Police", ["department", "budget"])
        ]
        
        for username, password, email, role, department, permissions in users:
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, role, department, permissions)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                username,
                hash_password(password),
                email,
                role,
                department,
                json.dumps(permissions)
            ))
    
    conn.commit()
    conn.close()

@router.post("/login")
async def login(request: LoginRequest):
    """Authenticate user and return token"""
    # Only initialize if database doesn't exist or is empty
    # This prevents recreation of sample users on every login
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        if count == 0:
            init_users_db()  # Only initialize if empty
    except:
        init_users_db()  # Table doesn't exist, initialize
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find user by username
    cursor.execute("""
        SELECT id, username, password_hash, email, role, department, permissions, sso_required
        FROM users WHERE username = ?
    """, (request.username,))
    
    user_row = cursor.fetchone()
    
    if not user_row:
        return {"success": False, "message": "Invalid username or password"}
    
    # SECURITY: Check if user is SSO-required (defense-in-depth)
    # Check both the flag AND the existence of sso_identities to prevent bypass
    sso_required = user_row['sso_required'] if 'sso_required' in user_row.keys() else False
    
    # Defensive check: Also verify if SSO identity exists (even if flag not set)
    cursor.execute("""
        SELECT COUNT(*) FROM sso_identities WHERE user_id = ?
    """, (user_row['id'],))
    has_sso_identity = cursor.fetchone()[0] > 0
    
    if sso_required or has_sso_identity:
        return {
            "success": False, 
            "message": "This account requires SSO authentication. Please use 'Sign in with Google' or 'Sign in with Microsoft'.",
            "sso_required": True
        }
    
    # Verify password for non-SSO users
    if not verify_password(request.password, user_row['password_hash']):
        return {"success": False, "message": "Invalid username or password"}
    
    # Update last login
    cursor.execute("""
        UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
    """, (user_row['id'],))
    conn.commit()
    
    # Parse permissions
    try:
        permissions = json.loads(user_row['permissions'])
    except:
        permissions = []
    
    # Create user object
    user = User(
        id=str(user_row['id']),
        username=user_row['username'],
        email=user_row['email'],
        role=user_row['role'],
        department=user_row['department'],
        permissions=permissions
    )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    conn.close()
    
    return {
        "success": True,
        "user": user.dict(),
        "token": access_token
    }

@router.get("/verify")
async def verify(payload: Dict[str, Any] = Depends(verify_token)):
    """Verify token and return user info"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    username = payload.get("sub")
    cursor.execute("""
        SELECT id, username, email, role, department, permissions
        FROM users WHERE username = ?
    """, (username,))
    
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row:
        return {"valid": False}
    
    try:
        permissions = json.loads(user_row['permissions'])
    except:
        permissions = []
    
    user = User(
        id=str(user_row['id']),
        username=user_row['username'],
        email=user_row['email'],
        role=user_row['role'],
        department=user_row['department'],
        permissions=permissions
    )
    
    return {"valid": True, "user": user.dict()}

@router.get("/users")
async def list_users(payload: Dict[str, Any] = Depends(verify_token)):
    """List all users (admin only)"""
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, email, role, department, permissions, created_at, last_login
        FROM users
    """)
    
    users = []
    for row in cursor.fetchall():
        try:
            permissions = json.loads(row['permissions'])
        except:
            permissions = []
        
        users.append({
            "id": row['id'],
            "username": row['username'],
            "email": row['email'],
            "role": row['role'],
            "department": row['department'],
            "permissions": permissions,
            "created_at": row['created_at'],
            "last_login": row['last_login']
        })
    
    conn.close()
    return users