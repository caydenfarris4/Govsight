# GovSight SSO Implementation Guide

## Overview
Enterprise-grade Single Sign-On (SSO) authentication system for GovSight Financial Intelligence Platform supporting OAuth 2.0/OIDC (Google Workspace, Microsoft Azure AD) and SAML 2.0 for municipal government deployments.

## Architecture

### Database Schema
Located in: `data/production/users.db`

**sso_providers** - SSO identity provider configurations
```sql
id INTEGER PRIMARY KEY
name TEXT UNIQUE                    -- e.g., 'google', 'microsoft', 'okta'
provider_type TEXT                  -- 'oauth' or 'saml'
config JSON                         -- Provider-specific configuration
municipality TEXT                   -- NULL for global, or specific city
enabled INTEGER (boolean)
created_at TIMESTAMP
```

**sso_identities** - Links users to SSO providers
```sql
id INTEGER PRIMARY KEY
user_id INTEGER → users.id
provider_id INTEGER → sso_providers.id
external_id TEXT                    -- User ID from provider (e.g., Google sub)
email TEXT
display_name TEXT
attributes JSON                     -- Additional claims from provider
last_login TIMESTAMP
created_at TIMESTAMP
UNIQUE(provider_id, external_id)
```

**sso_sessions** - Tracks SSO login sessions
```sql
id INTEGER PRIMARY KEY
user_id INTEGER → users.id
provider_id INTEGER → sso_providers.id
session_token TEXT UNIQUE
id_token TEXT                       -- OIDC ID token
access_token TEXT                   -- OAuth access token
refresh_token TEXT                  -- OAuth refresh token
expires_at TIMESTAMP
created_at TIMESTAMP
```

### Backend Components

#### 1. OAuth Handler (`modules/api/oauth_handler.py`)
Core OAuth 2.0/OIDC framework with:
- PKCE (Proof Key for Code Exchange) for enhanced security
- State parameter validation for CSRF protection
- Provider abstraction (Google, Microsoft)
- Token exchange and user info retrieval
- Automatic user info normalization

**Supported Providers:**
- **Google Workspace**: Uses OpenID Connect with hosted domain restriction
- **Microsoft Azure AD**: Uses Microsoft Graph API with tenant support

#### 2. SSO Endpoints (`modules/api/sso_endpoints.py`)
FastAPI routes mounted at `/api/auth/sso/`:

**GET /api/auth/sso/initiate**
- Query params: `provider` (google|microsoft)
- Generates authorization URL with PKCE
- Returns: redirect URL to provider

**GET /api/auth/sso/callback**
- OAuth callback endpoint
- Validates state and code verifier
- Exchanges authorization code for tokens
- Performs JIT user provisioning
- Creates SSO session
- Returns: redirect to React frontend with JWT token

**GET /api/auth/sso/providers**
- Lists enabled SSO providers
- Returns: provider configurations (without secrets)

**POST /api/auth/sso/logout** (planned)
- Implements Single Logout (SLO)

#### 3. SSO Database Layer (`modules/api/sso_database.py`)
Database operations for:
- Provider management (add, list, get, update, enable/disable)
- SSO identity creation and lookup
- Session management
- User-provider linking

#### 4. FastAPI Integration (`modules/api/pbb_api.py`)
SSO router included in main API:
```python
from modules.api.sso_endpoints import router as sso_router
app.include_router(sso_router)
```

### Frontend Components

#### 1. Login Page (`frontend/src/pages/Login.tsx`)
Enhanced with SSO buttons:
- "Sign in with Google" button with Google branding
- "Sign in with Microsoft" button with Microsoft branding
- Redirects to backend SSO initiation endpoint

#### 2. Callback Handler (`frontend/src/pages/AuthCallback.tsx`)
Handles OAuth redirect:
- Extracts token from URL query parameters
- Verifies token with backend `/api/auth/verify`
- Stores token and user in authStore
- Redirects to Dashboard on success
- Error handling and redirect to login on failure

#### 3. Auth Store (`frontend/src/stores/authStore.ts`)
Enhanced with:
- `setAuth(user, token)` method for SSO login
- Token persistence in localStorage
- Axios header configuration for API calls

#### 4. Routing (`frontend/src/App.tsx`)
New route: `/auth/callback` → `<AuthCallback />`

## OAuth 2.0 Flow

```
1. User clicks "Sign in with Google" on Login page
   ↓
2. React → GET /api/auth/sso/initiate?provider=google
   ↓
3. Backend generates:
   - state: random CSRF token (stored in session)
   - code_verifier: random string (stored in session)
   - code_challenge: SHA256(code_verifier)
   ↓
4. Backend → Redirect to Google OAuth URL with:
   - client_id, redirect_uri, scope
   - state, code_challenge, response_type=code
   ↓
5. User authenticates with Google
   ↓
6. Google → Redirect to /api/auth/sso/callback?code=XXX&state=YYY
   ↓
7. Backend validates state, exchanges code for tokens using:
   - client_id, client_secret, code
   - redirect_uri, code_verifier (PKCE)
   ↓
8. Backend retrieves user info from Google
   ↓
9. Backend performs JIT provisioning:
   - Check if SSO identity exists
   - If not, create user and link to provider
   - If exists, update last login
   ↓
10. Backend creates SSO session, generates JWT
    ↓
11. Backend → Redirect to React /auth/callback?token=JWT
    ↓
12. React stores token, verifies, redirects to Dashboard
```

## JIT User Provisioning

**Automatic User Creation:**
When a user authenticates via SSO for the first time:

1. Extract user info from provider (email, name, etc.)
2. Check if user exists with matching email
3. If not, create new user:
   - Username: generated from email
   - Password: cryptographically secure random 256-bit secret (never exposed)
   - `sso_enabled`: set to `1` (True)
   - `sso_required`: set to `1` (True) - enforces SSO-only login
   - Role: `viewer` (default, can be customized)
   - Municipality: extracted from email domain or default
   - Department: from IdP claims (if available)
4. Create SSO identity linking user to provider
5. Log authentication event

**SSO-Only Enforcement:**
Users created via JIT provisioning are marked with `sso_required=1` flag, which:
- Prevents password-based login attempts
- Returns clear error message: "This account requires SSO authentication"
- Ensures SSO users can ONLY authenticate via their identity provider
- Random password is stored (for schema compliance) but is unguessable and never disclosed

**Attribute Mapping:**
```python
{
  "email": "john.smith@cityname.gov",
  "name": "John Smith",
  "given_name": "John",
  "family_name": "Smith",
  "picture": "https://...",
  "hd": "cityname.gov",  # Google hosted domain
  "groups": ["Finance", "Admin"]  # From Azure AD
}
```

## Security Features

### 1. PKCE (Proof Key for Code Exchange)
Prevents authorization code interception attacks:
- Generate `code_verifier`: 43-128 random characters
- Compute `code_challenge`: BASE64URL(SHA256(code_verifier))
- Send challenge in authorization request
- Send verifier in token exchange
- Provider validates: SHA256(verifier) == challenge

### 2. State Parameter Validation
Prevents CSRF attacks:
- Generate random state token
- Store in server-side session
- Include in authorization URL
- Validate on callback: session state == callback state

### 3. Token Security
- JWT tokens signed with HS256
- Short expiry times (configurable)
- Refresh tokens for long-lived sessions
- Secure storage in database with encryption (planned)

### 4. SSO-Only Account Protection
- SSO-provisioned users created with `sso_required=1` flag
- Password login blocked for SSO accounts with clear error message
- Random unguessable 256-bit password stored (schema compliance, never exposed)
- Prevents credential stuffing and password-based attacks on SSO accounts

### 5. Domain Restrictions
- Google: `hd` (hosted domain) parameter restricts to government domains
- Microsoft: Tenant ID restricts to specific Azure AD tenant
- Configurable allowed domains per provider

## Configuration

### Setting Up Google Workspace OAuth

1. **Create OAuth 2.0 Client in Google Cloud Console:**
   - Navigate to APIs & Credentials
   - Create OAuth 2.0 Client ID (Web application)
   - Authorized redirect URIs: `https://your-domain.com/api/auth/sso/callback`
   - Note Client ID and Client Secret

2. **Add Secrets to Replit:**
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

3. **Enable Provider:**
   ```bash
   python scripts/setup_sso_providers.py
   # Then enable via Admin Panel or database update
   ```

### Setting Up Microsoft Azure AD OAuth

1. **Register Application in Azure Portal:**
   - Navigate to Azure Active Directory → App registrations
   - Create new registration
   - Redirect URI: `https://your-domain.com/api/auth/sso/callback`
   - API permissions: `User.Read`, `email`, `openid`, `profile`
   - Note Application (client) ID and create Client Secret

2. **Add Secrets to Replit:**
   ```
   MICROSOFT_CLIENT_ID=your-application-id
   MICROSOFT_CLIENT_SECRET=your-client-secret
   ```

3. **Enable Provider:**
   ```bash
   python scripts/setup_sso_providers.py
   # Then enable via Admin Panel
   ```

## Testing

### Manual Testing Flow
1. Start all workflows (Streamlit, FastAPI, React)
2. Navigate to React login page: `http://localhost:3000/login`
3. Click "Sign in with Google" or "Sign in with Microsoft"
4. Authenticate with provider
5. Verify redirect to Dashboard
6. Check `data/production/users.db` for new records:
   - `sso_identities` table
   - `sso_sessions` table
   - `users` table (if new user)

### Using Test Accounts
For development, create test accounts in:
- Google Workspace (with @yourcompany.gov domain)
- Azure AD tenant

### Monitoring
Check logs for SSO events:
```bash
# Backend logs
tail -f /tmp/logs/PBB_API_Backend_*.log

# Look for:
# - "Initiating SSO with provider: google"
# - "User info retrieved from Google"
# - "JIT provisioning: Creating new user"
# - "SSO callback successful"
```

## Migration from Password-Based Authentication

### Option 1: Gradual Migration
- Keep password authentication enabled
- Users can link SSO to existing accounts
- Eventually require SSO for new users

### Option 2: Bulk Migration
```python
# Link existing users to SSO providers by email
from modules.api.sso_database import create_sso_identity

for user in get_all_users():
    if user.email.endswith('@cityname.gov'):
        create_sso_identity(
            user_id=user.id,
            provider_id=google_provider_id,
            external_id=None,  # Will be set on first login
            email=user.email
        )
```

## Future Enhancements

### SAML 2.0 Support (Planned)
For enterprise IdPs (Okta, OneLogin, etc.):
- SP metadata generation
- IdP metadata parsing
- Assertion validation
- Attribute mapping

### Multi-Factor Authentication (Planned)
- TOTP implementation for password users
- Honor MFA from SSO providers
- Backup codes

### Advanced Features (Planned)
- Single Logout (SLO)
- Role mapping from IdP groups
- Per-municipality provider configuration
- SSO admin panel in React
- Audit logging for SSO events
- Session management UI

## Troubleshooting

### Common Issues

**1. "Invalid state parameter"**
- Cause: State mismatch between request and callback
- Solution: Ensure cookies are enabled, check session storage

**2. "Provider not enabled"**
- Cause: Provider not activated in database
- Solution: Run `scripts/setup_sso_providers.py` and enable provider

**3. "Failed to exchange authorization code"**
- Cause: Invalid client credentials or redirect URI
- Solution: Verify GOOGLE_CLIENT_ID/SECRET in Replit Secrets
- Check redirect URI matches exactly in Google Console

**4. "Email domain not allowed"**
- Cause: User email doesn't match allowed domains
- Solution: Update provider config `allowed_domains` in database

**5. Token verification failed**
- Cause: Token expired or invalid
- Solution: Check JWT secret consistency, verify token format

## API Reference

### SSO Initiation
```http
GET /api/auth/sso/initiate?provider=google
```
**Response:** Redirect to provider authorization URL

### SSO Callback
```http
GET /api/auth/sso/callback?code={code}&state={state}
```
**Response:** Redirect to frontend with token
```
{FRONTEND_URL}/auth/callback?token={jwt_token}&provider={provider_name}
```

### List Providers
```http
GET /api/auth/sso/providers
```
**Response:**
```json
[
  {
    "id": 1,
    "name": "google",
    "provider_type": "oauth",
    "enabled": true
  },
  {
    "id": 2,
    "name": "microsoft",
    "provider_type": "oauth",
    "enabled": true
  }
]
```

## Security Considerations for Production

1. **HTTPS Required:** All OAuth flows must use HTTPS in production
2. **Secure Secrets:** Use Google Cloud Secret Manager for production secrets
3. **Token Rotation:** Implement refresh token rotation
4. **Rate Limiting:** Add rate limits to SSO endpoints
5. **Audit Logging:** Log all SSO authentication attempts
6. **Session Management:** Implement session timeout and renewal
7. **Domain Validation:** Strictly validate email domains for government use

## SOC-2 Compliance Notes

SSO implementation supports SOC-2 compliance requirements:

- **Access Control (CC6.1):** Centralized authentication via trusted IdP
- **Authentication (CC6.6):** Strong authentication with MFA support (via IdP)
- **User Provisioning (CC6.2):** JIT provisioning with audit trail
- **Session Management (CC6.7):** Tracked sessions with expiry
- **Audit Logging (CC7.2):** All authentication events logged (when implemented)
- **Encryption (CC6.7):** Tokens encrypted in transit (HTTPS) and at rest (planned)

## Support

For issues or questions:
1. Check logs in `/tmp/logs/`
2. Verify provider configuration in `data/production/users.db`
3. Test with curl to isolate frontend vs backend issues
4. Review this documentation for common troubleshooting steps

## Version History

- **v1.0 (October 2025):** Initial OAuth 2.0 implementation with Google and Microsoft
- **v1.1 (Planned):** SAML 2.0 support
- **v1.2 (Planned):** MFA and advanced session management
- **v2.0 (Planned):** Full SOC-2 compliance with audit logging
