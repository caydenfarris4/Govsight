"""
SSO Authentication Endpoints for FastAPI
Handles OAuth 2.0 / OIDC flows for Google, Microsoft, and SAML
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import json
from datetime import datetime, timedelta
import jwt

from modules.api.oauth_handler import oauth_handler, GoogleOAuthProvider, MicrosoftOAuthProvider
from modules.api.sso_database import (
    get_sso_provider, link_sso_identity, get_sso_identity,
    create_sso_session, list_sso_providers, get_user_sso_identities
)
from modules.api.auth_api import create_access_token, get_db_connection, hash_password

router = APIRouter(prefix="/api/auth/sso", tags=["sso"])

# SSO Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class SSOInitiateRequest(BaseModel):
    provider: str  # "google", "microsoft", "saml"
    redirect_uri: Optional[str] = None


class SSOCallbackRequest(BaseModel):
    code: str
    state: str
    provider: str


def find_or_create_user_from_sso(email: str, name: str, sso_data: Dict) -> int:
    """
    Find existing user by email or create new user (JIT provisioning)
    Returns user_id
    """
    import secrets
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Try to find user by email
    cursor.execute("SELECT id, username FROM users WHERE email = ?", (email,))
    user_row = cursor.fetchone()
    
    if user_row:
        user_id = user_row['id']
    else:
        # JIT provisioning - create new user
        username = email.split('@')[0]  # Use email prefix as username
        
        # Make sure username is unique
        cursor.execute("SELECT COUNT(*) FROM users WHERE username LIKE ?", (f"{username}%",))
        count = cursor.fetchone()[0]
        if count > 0:
            username = f"{username}{count + 1}"
        
        # Create user with SSO
        # Generate cryptographically secure random password
        # SSO users should NEVER use password login - this is a secure placeholder
        random_password = secrets.token_urlsafe(32)  # 256-bit random secret, never exposed
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, role, department, permissions, sso_enabled, sso_required)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            hash_password(random_password),  # Secure random password, never disclosed
            email,
            "user",  # Default role, can be customized based on SSO claims
            sso_data.get('department', ''),
            json.dumps(["view"]),  # Default permissions
            1,  # sso_enabled = True
            1   # sso_required = True - MUST use SSO to login
        ))
        
        user_id = cursor.lastrowid
    
    # Update last login
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return user_id


@router.get("/providers")
async def get_available_providers():
    """List all available and enabled SSO providers"""
    providers = list_sso_providers(enabled_only=True)
    
    return {
        "providers": [
            {
                "id": p['id'],
                "name": p['name'],
                "type": p['provider_type'],
                "municipality": p['municipality']
            }
            for p in providers
        ]
    }


@router.post("/initiate")
async def initiate_sso(request: SSOInitiateRequest):
    """
    Initiate SSO login flow
    Returns authorization URL for redirect
    """
    provider_name = request.provider.lower()
    
    # Get provider configuration from database
    provider_config = get_sso_provider(name=provider_name)
    
    if not provider_config or not provider_config.get('enabled'):
        raise HTTPException(status_code=404, detail=f"SSO provider '{provider_name}' not found or disabled")
    
    config = provider_config.get('config', {})
    redirect_uri = request.redirect_uri or f"{BASE_URL}/api/auth/sso/callback/{provider_name}"
    
    # Initialize OAuth provider
    if provider_name == "google":
        provider = GoogleOAuthProvider(
            client_id=config.get('client_id'),
            client_secret=config.get('client_secret'),
            redirect_uri=redirect_uri
        )
    elif provider_name == "microsoft":
        provider = MicrosoftOAuthProvider(
            client_id=config.get('client_id'),
            client_secret=config.get('client_secret'),
            redirect_uri=redirect_uri,
            tenant=config.get('tenant', 'common')
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider_name}'")
    
    # Register provider with handler
    oauth_handler.register_provider(provider_name, provider)
    
    # Generate authorization URL with PKCE
    auth_url, state = oauth_handler.initiate_auth(provider_name, use_pkce=True)
    
    return {
        "authorization_url": auth_url,
        "state": state,
        "provider": provider_name
    }


@router.get("/callback/{provider}")
async def sso_callback(
    provider: str,
    code: str,
    state: str,
    request: Request
):
    """
    OAuth callback endpoint
    Exchanges code for token and creates user session
    """
    try:
        # Handle OAuth callback
        result = oauth_handler.handle_callback(provider, code, state)
        
        user_info = result['user_info']
        token_response = result['token_response']
        
        # Extract user data
        email = user_info.get('email')
        name = user_info.get('name', '')
        provider_user_id = user_info.get('sub')
        
        if not email or not provider_user_id:
            raise HTTPException(status_code=400, detail="Invalid user info from provider")
        
        # Get provider config
        provider_config = get_sso_provider(name=provider)
        if not provider_config:
            raise HTTPException(status_code=500, detail="Provider configuration not found")
        
        # Check if SSO identity already exists
        existing_identity = get_sso_identity(provider_config['id'], provider_user_id)
        
        if existing_identity:
            user_id = existing_identity['user_id']
        else:
            # Find or create user (JIT provisioning)
            user_id = find_or_create_user_from_sso(email, name, user_info)
            
            # Link SSO identity to user
            link_sso_identity(
                user_id=user_id,
                provider_id=provider_config['id'],
                provider_user_id=provider_user_id,
                email=email,
                display_name=name,
                attributes=user_info
            )
        
        # Get user details for token
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, role, email, department, permissions
            FROM users WHERE id = ?
        """, (user_id,))
        user_row = cursor.fetchone()
        conn.close()
        
        if not user_row:
            raise HTTPException(status_code=500, detail="User not found after SSO")
        
        # Create JWT access token
        access_token = create_access_token(
            data={
                "sub": user_row['username'],
                "role": user_row['role'],
                "email": user_row['email'],
                "sso": True,
                "provider": provider
            }
        )
        
        # Create SSO session
        expires_at = datetime.utcnow() + timedelta(seconds=token_response.get('expires_in', 3600))
        create_sso_session(
            user_id=user_id,
            provider_id=provider_config['id'],
            session_token=access_token,
            id_token=token_response.get('id_token'),
            access_token=token_response.get('access_token'),
            refresh_token=token_response.get('refresh_token'),
            expires_at=expires_at
        )
        
        # Redirect to frontend with token
        frontend_callback_url = f"{FRONTEND_URL}/auth/callback?token={access_token}&provider={provider}"
        return RedirectResponse(url=frontend_callback_url)
        
    except Exception as e:
        print(f"SSO callback error: {str(e)}")
        # Redirect to frontend with error
        error_url = f"{FRONTEND_URL}/login?error=sso_failed&message={str(e)}"
        return RedirectResponse(url=error_url)


@router.get("/user/identities")
async def get_user_identities(request: Request):
    """Get all SSO identities linked to current user"""
    # TODO: Extract user_id from JWT token in Authorization header
    # For now, returning example response
    return {
        "identities": []
    }


@router.post("/link")
async def link_sso_to_account(request: Request):
    """Link an additional SSO provider to existing account"""
    # TODO: Implement SSO account linking
    return {
        "success": True,
        "message": "SSO provider linked successfully"
    }


@router.post("/unlink")
async def unlink_sso_from_account(request: Request):
    """Unlink an SSO provider from account"""
    # TODO: Implement SSO account unlinking
    return {
        "success": True,
        "message": "SSO provider unlinked successfully"
    }


@router.post("/logout")
async def sso_logout(request: Request):
    """Handle SSO logout (Single Logout - SLO)"""
    # TODO: Implement SLO with identity providers
    return {
        "success": True,
        "message": "Logged out successfully"
    }
