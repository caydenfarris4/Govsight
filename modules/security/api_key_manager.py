"""
Secure API Key Management Module for GovSight
Handles secure storage and retrieval of API keys with encryption and graceful degradation
"""

import os
import json
import streamlit as st
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
import base64
import hashlib

class APIKeyManager:
    """
    Centralized API key management with security best practices
    
    SECURITY FEATURES:
    - Never stores keys in plain text
    - Uses environment variables for runtime storage
    - Supports encrypted storage for persistence
    - Provides key validation without exposing the key
    - Graceful degradation when keys are missing
    """
    
    # Supported providers: environment variable + expected key prefix
    ENV_KEYS = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    KEY_PREFIXES = {
        "openai": "sk-",
        "anthropic": "sk-ant-",
    }

    def __init__(self):
        self.env_key = "OPENAI_API_KEY"  # legacy alias, kept for callers
        self.config_file = Path("configs/security/api_keys.json")
        self.encryption_key_file = Path("configs/security/.encryption_key")
        self.cipher_suite = self._get_cipher_suite()

    def _env_var(self, key_type: str) -> Optional[str]:
        return self.ENV_KEYS.get(key_type)
        
    def _get_cipher_suite(self) -> Optional[Fernet]:
        """Get or create encryption cipher for secure storage"""
        try:
            # Check if encryption key exists
            if self.encryption_key_file.exists():
                with open(self.encryption_key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new encryption key
                key = Fernet.generate_key()
                # Ensure directory exists
                self.encryption_key_file.parent.mkdir(parents=True, exist_ok=True)
                # Save key with restricted permissions
                with open(self.encryption_key_file, 'wb') as f:
                    f.write(key)
                # Set file permissions to owner-only on Unix systems
                try:
                    os.chmod(self.encryption_key_file, 0o600)
                except:
                    pass
            
            return Fernet(key)
        except Exception as e:
            st.warning(f"Encryption not available: {e}")
            return None
    
    def set_api_key(self, api_key: str, key_type: str = "openai") -> Dict[str, Any]:
        """
        Securely store API key
        
        Args:
            api_key: The API key to store
            key_type: Type of API key (openai, anthropic, etc.)
            
        Returns:
            Status dictionary with success and message
        """
        if not api_key or not api_key.strip():
            return {"success": False, "message": "API key cannot be empty"}
        
        # Validate key format (basic check)
        prefix = self.KEY_PREFIXES.get(key_type)
        if prefix and not api_key.startswith(prefix):
            return {"success": False,
                    "message": f"Invalid {key_type} API key format (should start with '{prefix}')"}

        try:
            # Set in environment variable for immediate use
            env_var = self._env_var(key_type)
            if env_var:
                os.environ[env_var] = api_key
            
            # Store encrypted version for persistence
            if self.cipher_suite:
                encrypted_key = self.cipher_suite.encrypt(api_key.encode())
                
                # Load existing config or create new
                config = {}
                if self.config_file.exists():
                    try:
                        with open(self.config_file, 'r') as f:
                            config = json.load(f)
                    except:
                        config = {}
                
                # Store encrypted key
                config[key_type] = {
                    "encrypted": base64.b64encode(encrypted_key).decode(),
                    "configured": True,
                    "hash": hashlib.sha256(api_key.encode()).hexdigest()[:8]  # Store partial hash for verification
                }
                
                # Save config
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                # Set file permissions
                try:
                    os.chmod(self.config_file, 0o600)
                except:
                    pass
            
            # Also set in Streamlit secrets if available
            if hasattr(st, 'secrets'):
                try:
                    st.secrets[self.env_key] = api_key
                except:
                    pass
            
            return {"success": True, "message": "API key configured successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Failed to store API key: {str(e)}"}
    
    def get_api_key(self, key_type: str = "openai") -> Optional[str]:
        """
        Retrieve API key securely
        
        Args:
            key_type: Type of API key to retrieve
            
        Returns:
            API key if available, None otherwise
        """
        # Check environment variable first (runtime storage)
        env_var = self._env_var(key_type)
        if env_var:
            key = os.environ.get(env_var)
            if key and key != "sk-xxx":  # Ignore placeholder
                return key
        
        # Check Streamlit secrets
        if hasattr(st, 'secrets'):
            try:
                key = st.secrets.get(self.env_key)
                if key and key != "sk-xxx":
                    # Set in environment for other modules
                    os.environ[self.env_key] = key
                    return key
            except:
                pass
        
        # Check encrypted storage
        if self.cipher_suite and self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                if key_type in config and "encrypted" in config[key_type]:
                    encrypted_key = base64.b64decode(config[key_type]["encrypted"])
                    api_key = self.cipher_suite.decrypt(encrypted_key).decode()

                    # Set in environment for immediate use
                    if env_var:
                        os.environ[env_var] = api_key

                    return api_key
            except Exception:
                pass
        
        return None
    
    def is_configured(self, key_type: str = "openai") -> bool:
        """Check if API key is configured"""
        return self.get_api_key(key_type) is not None
    
    def get_status(self, key_type: str = "openai") -> Dict[str, Any]:
        """
        Get API key configuration status without exposing the key
        
        Returns:
            Status dictionary with configuration details
        """
        status = {
            "configured": False,
            "source": None,
            "partial_hash": None,
            "key_type": key_type
        }
        
        # Check if key exists
        key = self.get_api_key(key_type)
        if key:
            status["configured"] = True

            # Determine source
            env_var = self._env_var(key_type)
            if env_var and os.environ.get(env_var):
                status["source"] = "environment"
            elif hasattr(st, 'secrets') and env_var and env_var in st.secrets:
                status["source"] = "secrets"
            elif self.config_file.exists():
                status["source"] = "encrypted_storage"
            
            # Add partial hash for verification (first and last 4 chars)
            if len(key) > 8:
                status["partial_hash"] = f"{key[:4]}...{key[-4:]}"
            else:
                status["partial_hash"] = "****"
        
        return status
    
    def validate_api_key(self, api_key: str = None, key_type: str = "openai") -> Dict[str, Any]:
        """
        Validate API key by making a test request
        
        Args:
            api_key: Key to validate (if None, uses stored key)
            key_type: Type of API key
            
        Returns:
            Validation result dictionary
        """
        if not api_key:
            api_key = self.get_api_key(key_type)
        
        if not api_key:
            return {"valid": False, "message": "No API key configured"}
        
        if key_type == "openai":
            try:
                import openai
                # Test the key with a minimal request
                client = openai.OpenAI(api_key=api_key)
                # Use the models endpoint which has minimal cost
                models = client.models.list()
                return {"valid": True, "message": "API key is valid"}
            except openai.AuthenticationError:
                return {"valid": False, "message": "Invalid API key"}
            except openai.APIConnectionError:
                return {"valid": False, "message": "Connection error - check network"}
            except Exception as e:
                return {"valid": False, "message": f"Validation error: {str(e)}"}

        if key_type == "anthropic":
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                # Minimal request to confirm the key authenticates
                client.models.list(limit=1)
                return {"valid": True, "message": "API key is valid"}
            except anthropic.AuthenticationError:
                return {"valid": False, "message": "Invalid API key"}
            except anthropic.APIConnectionError:
                return {"valid": False, "message": "Connection error - check network"}
            except Exception as e:
                return {"valid": False, "message": f"Validation error: {str(e)}"}

        return {"valid": False, "message": f"Unknown key type: {key_type}"}
    
    def remove_api_key(self, key_type: str = "openai") -> Dict[str, Any]:
        """
        Remove stored API key
        
        Args:
            key_type: Type of API key to remove
            
        Returns:
            Status dictionary
        """
        try:
            # Remove from environment
            env_var = self._env_var(key_type)
            if env_var and env_var in os.environ:
                del os.environ[env_var]
            
            # Remove from encrypted storage
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                if key_type in config:
                    del config[key_type]
                    
                    with open(self.config_file, 'w') as f:
                        json.dump(config, f, indent=2)
            
            return {"success": True, "message": "API key removed"}
            
        except Exception as e:
            return {"success": False, "message": f"Failed to remove key: {str(e)}"}

    def hydrate_environment(self) -> Dict[str, bool]:
        """Load every stored key into its environment variable.

        Call at process startup (and cheaply before AI feature checks) so
        keys configured through the admin console reach services that read
        os.environ - the FastAPI platform, the Mantis orchestrator, and
        the AI data mapper all become live without a restart.
        """
        loaded = {}
        for key_type in self.ENV_KEYS:
            loaded[key_type] = self.get_api_key(key_type) is not None
        return loaded

# Global instance for easy access
api_key_manager = APIKeyManager()

def check_openai_availability() -> bool:
    """Quick check if OpenAI is available"""
    return api_key_manager.is_configured("openai")

def get_openai_client():
    """
    Get OpenAI client with proper error handling
    
    Returns:
        OpenAI client if configured, None otherwise
    """
    api_key = api_key_manager.get_api_key("openai")
    if api_key:
        try:
            import openai
            return openai.OpenAI(api_key=api_key)
        except ImportError:
            st.error("OpenAI library not installed. Please install with: pip install openai")
            return None
        except Exception as e:
            st.error(f"Failed to initialize OpenAI client: {e}")
            return None
    return None