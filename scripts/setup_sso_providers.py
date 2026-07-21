"""
Setup SSO Providers
Initializes Google and Microsoft OAuth providers in the database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.api.sso_database import init_sso_tables, add_sso_provider, list_sso_providers


def setup_google_provider():
    """Add Google Workspace OAuth provider"""
    config = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET"),
        "allowed_domains": ["*.gov", "*.state.*.us", "*.city.*.us"],  # Government email domains
        "hd_restriction": True,  # Restrict to specific hosted domains
    }
    
    try:
        provider_id = add_sso_provider(
            name="google",
            provider_type="oauth",
            config=config,
            municipality=None,  # Available to all municipalities
            enabled=False  # Disabled until configured
        )
        print(f"✓ Added Google OAuth provider (ID: {provider_id})")
        print("  Configure by setting GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET secrets")
    except Exception as e:
        print(f"✗ Google provider already exists or error: {e}")


def setup_microsoft_provider():
    """Add Microsoft Azure AD / Office 365 OAuth provider"""
    config = {
        "client_id": os.getenv("MICROSOFT_CLIENT_ID", "YOUR_MICROSOFT_CLIENT_ID"),
        "client_secret": os.getenv("MICROSOFT_CLIENT_SECRET", "YOUR_MICROSOFT_CLIENT_SECRET"),
        "tenant": "common",  # Can be changed to specific tenant ID
        "allowed_domains": ["*.gov", "*.state.*.us", "*.city.*.us"],
    }
    
    try:
        provider_id = add_sso_provider(
            name="microsoft",
            provider_type="oauth",
            config=config,
            municipality=None,  # Available to all municipalities
            enabled=False  # Disabled until configured
        )
        print(f"✓ Added Microsoft OAuth provider (ID: {provider_id})")
        print("  Configure by setting MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET secrets")
    except Exception as e:
        print(f"✗ Microsoft provider already exists or error: {e}")


def list_configured_providers():
    """List all SSO providers"""
    providers = list_sso_providers()
    
    if providers:
        print("\n📋 Configured SSO Providers:")
        print("-" * 60)
        for p in providers:
            status = "✓ Enabled" if p['enabled'] else "✗ Disabled"
            print(f"{p['name']:15} | {p['provider_type']:8} | {status}")
        print("-" * 60)
    else:
        print("\nNo SSO providers configured")


if __name__ == "__main__":
    print("=" * 60)
    print("  GovSight SSO Provider Setup")
    print("=" * 60)
    print()
    
    # Initialize SSO tables
    init_sso_tables()
    
    # Setup providers
    setup_google_provider()
    setup_microsoft_provider()
    
    # List all providers
    list_configured_providers()
    
    print()
    print("📝 Next Steps:")
    print("1. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to Replit Secrets")
    print("2. Add MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET to Replit Secrets")
    print("3. Enable providers through the Admin Panel")
    print("4. Test SSO login from the React frontend")
    print()
