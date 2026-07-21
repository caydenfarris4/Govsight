"""
Migrate Existing SSO Users - Security Fix
Backfills SSO users with random passwords and sets sso_required flag
"""
import sys
import os
import sqlite3
import hashlib
import secrets

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.admin.database_config import PRODUCTION_USERS_DB


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def migrate_sso_users():
    """
    Migrate existing SSO users to use random passwords and sso_required flag
    """
    conn = sqlite3.connect(PRODUCTION_USERS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("  SSO User Security Migration")
    print("=" * 60)
    print()
    
    # Ensure SSO columns exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'sso_enabled' not in columns:
        print("Adding sso_enabled column...")
        cursor.execute("ALTER TABLE users ADD COLUMN sso_enabled BOOLEAN DEFAULT 0")
    
    if 'sso_required' not in columns:
        print("Adding sso_required column...")
        cursor.execute("ALTER TABLE users ADD COLUMN sso_required BOOLEAN DEFAULT 0")
    
    conn.commit()
    
    # Check if sso_identities table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='sso_identities'
    """)
    
    if not cursor.fetchone():
        print("No sso_identities table found. No SSO users to migrate.")
        conn.close()
        return
    
    # Determine password column name (password or password_hash)
    cursor.execute("PRAGMA table_info(users)")
    columns = {col[1]: col[2] for col in cursor.fetchall()}
    password_column = 'password' if 'password' in columns else 'password_hash'
    
    # Find all users with SSO identities
    cursor.execute(f"""
        SELECT DISTINCT u.id, u.username, u.{password_column}, u.sso_required
        FROM users u
        INNER JOIN sso_identities si ON u.id = si.user_id
    """)
    
    sso_users = cursor.fetchall()
    
    if not sso_users:
        print("No SSO users found. Migration not needed.")
        conn.close()
        return
    
    print(f"Found {len(sso_users)} SSO users")
    print()
    
    # Known vulnerable password hash
    vulnerable_hash = hash_password("sso-user-no-password")
    
    migrated_count = 0
    already_secure_count = 0
    
    for user in sso_users:
        user_id = user['id']
        username = user['username']
        current_hash = user[password_column]
        sso_required = user['sso_required']
        
        # Check if user has vulnerable password or missing sso_required flag
        needs_migration = (
            current_hash == vulnerable_hash or 
            not sso_required
        )
        
        if needs_migration:
            # Generate new random password
            random_password = secrets.token_urlsafe(32)  # 256-bit random secret
            new_hash = hash_password(random_password)
            
            # Update user with secure password and sso_required flag
            cursor.execute(f"""
                UPDATE users 
                SET {password_column} = ?, sso_enabled = 1, sso_required = 1
                WHERE id = ?
            """, (new_hash, user_id))
            
            print(f"✓ Migrated: {username:20} | Random password set, SSO required")
            migrated_count += 1
        else:
            print(f"  Skipped:  {username:20} | Already secure")
            already_secure_count += 1
    
    conn.commit()
    conn.close()
    
    print()
    print("-" * 60)
    print(f"Migration Summary:")
    print(f"  Total SSO users:        {len(sso_users)}")
    print(f"  Migrated (secured):     {migrated_count}")
    print(f"  Already secure:         {already_secure_count}")
    print("-" * 60)
    print()
    
    if migrated_count > 0:
        print("✓ Migration completed successfully!")
        print()
        print("⚠️  IMPORTANT:")
        print("   Migrated users can now ONLY login via SSO.")
        print("   Password login attempts will be rejected.")
        print()
    else:
        print("✓ All SSO users are already secure!")
        print()


if __name__ == "__main__":
    try:
        migrate_sso_users()
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
