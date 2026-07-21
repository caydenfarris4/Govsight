"""
SSO Database Schema and Management
Handles SSO identity providers, user SSO identities, and configuration
"""
import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
from modules.admin.database_config import PRODUCTION_USERS_DB


def init_sso_tables():
    """Initialize SSO-related tables in the production database"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    cursor = conn.cursor()
    
    # SSO Providers Configuration Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sso_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            provider_type TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            config JSON NOT NULL,
            municipality TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # SSO User Identities Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sso_identities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            provider_user_id TEXT NOT NULL,
            email TEXT,
            display_name TEXT,
            attributes JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (provider_id) REFERENCES sso_providers(id) ON DELETE CASCADE,
            UNIQUE(provider_id, provider_user_id)
        )
    """)
    
    # SSO Sessions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sso_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            id_token TEXT,
            access_token TEXT,
            refresh_token TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (provider_id) REFERENCES sso_providers(id) ON DELETE CASCADE
        )
    """)
    
    # Check if users table needs sso_enabled column
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'sso_enabled' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN sso_enabled BOOLEAN DEFAULT 0")
    
    if 'sso_required' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN sso_required BOOLEAN DEFAULT 0")
    
    if 'mfa_enabled' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0")
    
    if 'mfa_secret' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN mfa_secret TEXT")
    
    # SECURITY: Backfill sso_required for existing SSO users
    # This ensures legacy SSO users created before this security fix are protected
    try:
        cursor.execute("""
            UPDATE users 
            SET sso_enabled = 1, sso_required = 1
            WHERE id IN (
                SELECT DISTINCT user_id FROM sso_identities
            ) AND (sso_required IS NULL OR sso_required = 0)
        """)
        
        backfilled_count = cursor.rowcount
        if backfilled_count > 0:
            print(f"Security: Backfilled {backfilled_count} legacy SSO users with sso_required flag")
    except sqlite3.OperationalError:
        # Table might not exist yet on first run
        pass
    
    conn.commit()
    conn.close()
    
    print("SSO database tables initialized successfully")


def add_sso_provider(
    name: str,
    provider_type: str,
    config: Dict,
    municipality: Optional[str] = None,
    enabled: bool = True
) -> int:
    """Add a new SSO provider configuration"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sso_providers (name, provider_type, enabled, config, municipality)
        VALUES (?, ?, ?, ?, ?)
    """, (name, provider_type, enabled, json.dumps(config), municipality))
    
    provider_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return provider_id


def get_sso_provider(provider_id: Optional[int] = None, name: Optional[str] = None) -> Optional[Dict]:
    """Get SSO provider by ID or name"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if provider_id:
        cursor.execute("SELECT * FROM sso_providers WHERE id = ?", (provider_id,))
    elif name:
        cursor.execute("SELECT * FROM sso_providers WHERE name = ?", (name,))
    else:
        conn.close()
        return None
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        provider = dict(row)
        provider['config'] = json.loads(provider['config']) if provider['config'] else {}
        return provider
    
    return None


def list_sso_providers(enabled_only: bool = False, municipality: Optional[str] = None) -> List[Dict]:
    """List all SSO providers"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM sso_providers WHERE 1=1"
    params = []
    
    if enabled_only:
        query += " AND enabled = 1"
    
    if municipality:
        query += " AND (municipality = ? OR municipality IS NULL)"
        params.append(municipality)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    providers = []
    for row in rows:
        provider = dict(row)
        provider['config'] = json.loads(provider['config']) if provider['config'] else {}
        providers.append(provider)
    
    return providers


def link_sso_identity(
    user_id: int,
    provider_id: int,
    provider_user_id: str,
    email: str,
    display_name: str,
    attributes: Optional[Dict] = None
) -> int:
    """Link an SSO identity to a user account"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO sso_identities 
        (user_id, provider_id, provider_user_id, email, display_name, attributes, last_login)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, provider_id, provider_user_id, email, display_name, 
          json.dumps(attributes) if attributes else None, datetime.now().isoformat()))
    
    identity_id = cursor.lastrowid
    
    # Update user's sso_enabled flag
    cursor.execute("UPDATE users SET sso_enabled = 1 WHERE id = ?", (user_id,))
    
    conn.commit()
    conn.close()
    
    return identity_id


def get_sso_identity(
    provider_id: int,
    provider_user_id: str
) -> Optional[Dict]:
    """Get SSO identity by provider and provider user ID"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sso_identities 
        WHERE provider_id = ? AND provider_user_id = ?
    """, (provider_id, provider_user_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        identity = dict(row)
        identity['attributes'] = json.loads(identity['attributes']) if identity['attributes'] else {}
        return identity
    
    return None


def get_user_sso_identities(user_id: int) -> List[Dict]:
    """Get all SSO identities for a user"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT si.*, sp.name as provider_name, sp.provider_type
        FROM sso_identities si
        JOIN sso_providers sp ON si.provider_id = sp.id
        WHERE si.user_id = ?
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    identities = []
    for row in rows:
        identity = dict(row)
        identity['attributes'] = json.loads(identity['attributes']) if identity['attributes'] else {}
        identities.append(identity)
    
    return identities


def create_sso_session(
    user_id: int,
    provider_id: int,
    session_token: str,
    id_token: Optional[str] = None,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    expires_at: Optional[datetime] = None
) -> int:
    """Create a new SSO session"""
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sso_sessions 
        (user_id, provider_id, session_token, id_token, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, provider_id, session_token, id_token, access_token, refresh_token,
          expires_at.isoformat() if expires_at else None))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return session_id


if __name__ == "__main__":
    # Initialize SSO tables
    init_sso_tables()
    print("SSO database schema created successfully!")
