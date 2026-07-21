"""
Unified Secret Management Module
Supports both Replit environment variables and Google Cloud Secret Manager
Provides transparent fallback between platforms for seamless deployment
"""

import os
import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

class UnifiedSecretManager:
    """
    Unified secret management that works across Replit and Google Cloud Platform.
    
    Order of precedence:
    - Development mode (default): Environment variables → GCP Secret Manager
    - Production mode (PREFER_GCP_SECRETS=true): GCP Secret Manager → Environment variables
    
    This ensures the application works identically in both environments
    without code changes, while allowing GCP to take precedence in production.
    """
    
    def __init__(self):
        self.gcp_client = None
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        # Production mode: prefer GCP Secret Manager over environment variables
        self.prefer_gcp = os.environ.get('PREFER_GCP_SECRETS', 'false').lower() == 'true'
        self._init_gcp_client()
    
    def _init_gcp_client(self):
        """
        Initialize Google Cloud Secret Manager client if available.
        Silently fails if not in GCP environment.
        """
        if not self.project_id:
            logger.info("No GOOGLE_CLOUD_PROJECT found - using environment variables only")
            return
        
        try:
            from google.cloud import secretmanager
            self.gcp_client = secretmanager.SecretManagerServiceClient()
            logger.info(f"Google Cloud Secret Manager initialized for project: {self.project_id}")
        except ImportError:
            logger.info("google-cloud-secret-manager not installed - using environment variables only")
        except Exception as e:
            logger.warning(f"Could not initialize GCP Secret Manager: {e}")
    
    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str, version: str = "latest") -> Optional[str]:
        """
        Get secret value with configurable precedence.
        
        Args:
            secret_name: Name of the secret (e.g., 'ADMIN_PASSWORD')
            version: Version number for GCP (default: "latest" for dev, use explicit version in prod)
        
        Returns:
            Secret value or None if not found
        
        Note: Results are cached for performance (5 min TTL recommended).
              Call clear_cache() after rotating secrets.
        """
        # Production mode: Try GCP first, then environment
        if self.prefer_gcp:
            # Priority 1: Google Cloud Secret Manager
            if self.gcp_client and self.project_id:
                try:
                    secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
                    response = self.gcp_client.access_secret_version(request={"name": secret_path})
                    secret_value = response.payload.data.decode('utf-8')
                    logger.debug(f"Secret '{secret_name}' retrieved from GCP Secret Manager (production mode)")
                    return secret_value
                except Exception as e:
                    logger.warning(f"Could not retrieve '{secret_name}' from GCP: {e}")
            
            # Priority 2: Fallback to environment variables
            env_value = os.environ.get(secret_name)
            if env_value:
                logger.debug(f"Secret '{secret_name}' retrieved from environment (fallback)")
                return env_value
        
        # Development mode (default): Try environment first, then GCP
        else:
            # Priority 1: Check environment variables (Replit Secrets or local .env)
            env_value = os.environ.get(secret_name)
            if env_value:
                logger.debug(f"Secret '{secret_name}' retrieved from environment")
                return env_value
            
            # Priority 2: Try Google Cloud Secret Manager
            if self.gcp_client and self.project_id:
                try:
                    secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
                    response = self.gcp_client.access_secret_version(request={"name": secret_path})
                    secret_value = response.payload.data.decode('utf-8')
                    logger.debug(f"Secret '{secret_name}' retrieved from GCP Secret Manager")
                    return secret_value
                except Exception as e:
                    logger.warning(f"Could not retrieve '{secret_name}' from GCP: {e}")
        
        logger.error(f"Secret '{secret_name}' not found in any source")
        return None
    
    def clear_cache(self):
        """Clear the secret cache to force fresh retrieval"""
        self.get_secret.cache_clear()
        logger.info("Secret cache cleared")
    
    def has_secret(self, secret_name: str) -> bool:
        """Check if a secret exists without retrieving its value"""
        return self.get_secret(secret_name) is not None


# Global singleton instance
_secret_manager = None

def get_secret_manager() -> UnifiedSecretManager:
    """Get or create the global secret manager instance"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = UnifiedSecretManager()
    return _secret_manager


def get_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get a secret value.
    
    Args:
        secret_name: Name of the secret
        default: Default value if secret not found
    
    Returns:
        Secret value or default
    """
    manager = get_secret_manager()
    value = manager.get_secret(secret_name)
    return value if value is not None else default
