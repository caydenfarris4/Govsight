"""
OAuth 2.0 / OpenID Connect Handler
Provides unified OAuth framework for SSO with multiple identity providers
"""
import secrets
import hashlib
import base64
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc7636 import create_s256_code_challenge
import requests


class OAuthProvider:
    """Base class for OAuth 2.0 / OIDC providers"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str = "openid profile email"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        
        # Override these in subclasses
        self.authorization_endpoint = ""
        self.token_endpoint = ""
        self.userinfo_endpoint = ""
        self.issuer = ""
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')  # Remove padding
        
        code_challenge = create_s256_code_challenge(code_verifier)
        
        return code_verifier, code_challenge
    
    def generate_state(self) -> str:
        """Generate random state parameter for CSRF protection"""
        return secrets.token_urlsafe(32)
    
    def get_authorization_url(
        self,
        state: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: str = "S256"
    ) -> str:
        """Build authorization URL for redirect"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': state,
        }
        
        # Add PKCE parameters if provided
        if code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = code_challenge_method
        
        return f"{self.authorization_endpoint}?{urlencode(params)}"
    
    def exchange_code_for_token(
        self,
        code: str,
        code_verifier: Optional[str] = None
    ) -> Dict:
        """Exchange authorization code for access token"""
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        # Add PKCE verifier if provided
        if code_verifier:
            token_data['code_verifier'] = code_verifier
        
        response = requests.post(
            self.token_endpoint,
            data=token_data,
            headers={'Accept': 'application/json'}
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_user_info(self, access_token: str) -> Dict:
        """Get user information from provider"""
        response = requests.get(
            self.userinfo_endpoint,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        response.raise_for_status()
        return response.json()
    
    def validate_token(self, token_response: Dict) -> bool:
        """Validate token response (override in subclasses for ID token validation)"""
        return 'access_token' in token_response


class GoogleOAuthProvider(OAuthProvider):
    """Google Workspace OAuth 2.0 / OIDC Provider"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="openid profile email"
        )
        
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
        self.issuer = "https://accounts.google.com"
    
    def get_user_info(self, access_token: str) -> Dict:
        """Get user information from Google"""
        user_info = super().get_user_info(access_token)
        
        # Normalize to standard format
        return {
            'sub': user_info.get('sub'),
            'email': user_info.get('email'),
            'email_verified': user_info.get('email_verified', False),
            'name': user_info.get('name'),
            'given_name': user_info.get('given_name'),
            'family_name': user_info.get('family_name'),
            'picture': user_info.get('picture'),
            'hd': user_info.get('hd'),  # Hosted domain for G Suite
        }


class MicrosoftOAuthProvider(OAuthProvider):
    """Microsoft Azure AD / Office 365 OAuth 2.0 / OIDC Provider"""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        tenant: str = "common"
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="openid profile email User.Read"
        )
        
        self.tenant = tenant
        base_url = f"https://login.microsoftonline.com/{tenant}"
        
        self.authorization_endpoint = f"{base_url}/oauth2/v2.0/authorize"
        self.token_endpoint = f"{base_url}/oauth2/v2.0/token"
        self.userinfo_endpoint = "https://graph.microsoft.com/v1.0/me"
        self.issuer = f"https://login.microsoftonline.com/{tenant}/v2.0"
    
    def get_user_info(self, access_token: str) -> Dict:
        """Get user information from Microsoft Graph"""
        response = requests.get(
            self.userinfo_endpoint,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        response.raise_for_status()
        user_info = response.json()
        
        # Normalize to standard format
        return {
            'sub': user_info.get('id'),
            'email': user_info.get('mail') or user_info.get('userPrincipalName'),
            'email_verified': True,  # Microsoft verifies emails
            'name': user_info.get('displayName'),
            'given_name': user_info.get('givenName'),
            'family_name': user_info.get('surname'),
            'job_title': user_info.get('jobTitle'),
            'office_location': user_info.get('officeLocation'),
        }


class OAuthHandler:
    """Main OAuth handler for managing multiple providers"""
    
    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {}
        self.pending_auth: Dict[str, Dict] = {}  # Store state/verifier pairs
    
    def register_provider(self, name: str, provider: OAuthProvider):
        """Register an OAuth provider"""
        self.providers[name] = provider
    
    def get_provider(self, name: str) -> Optional[OAuthProvider]:
        """Get provider by name"""
        return self.providers.get(name)
    
    def initiate_auth(self, provider_name: str, use_pkce: bool = True) -> Tuple[str, str]:
        """
        Initiate OAuth flow
        Returns: (authorization_url, state)
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        state = provider.generate_state()
        
        if use_pkce:
            code_verifier, code_challenge = provider.generate_pkce_pair()
            auth_url = provider.get_authorization_url(state, code_challenge)
            
            # Store PKCE verifier for later
            self.pending_auth[state] = {
                'provider': provider_name,
                'code_verifier': code_verifier,
            }
        else:
            auth_url = provider.get_authorization_url(state)
            self.pending_auth[state] = {
                'provider': provider_name,
            }
        
        return auth_url, state
    
    def handle_callback(
        self,
        provider_name: str,
        code: str,
        state: str
    ) -> Dict:
        """
        Handle OAuth callback
        Returns: token response and user info
        """
        # Validate state
        if state not in self.pending_auth:
            raise ValueError("Invalid state parameter - possible CSRF attack")
        
        auth_data = self.pending_auth.pop(state)
        if auth_data['provider'] != provider_name:
            raise ValueError("Provider mismatch")
        
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        # Exchange code for token
        code_verifier = auth_data.get('code_verifier')
        token_response = provider.exchange_code_for_token(code, code_verifier)
        
        # Get user info
        access_token = token_response.get('access_token')
        user_info = provider.get_user_info(access_token)
        
        return {
            'provider': provider_name,
            'token_response': token_response,
            'user_info': user_info,
        }


# Global OAuth handler instance
oauth_handler = OAuthHandler()
