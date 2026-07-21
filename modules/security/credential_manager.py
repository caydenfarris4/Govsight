"""
Secure Credential Manager
Handles secure storage and retrieval of database credentials using environment variables.
Provides credential redaction and secure management for Phase 3 Multi-Database Integration.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class SecureCredentialManager:
    """
    Manages database credentials securely using environment variables.
    Replaces plaintext credential storage with secure environment-based management.
    """
    
    def __init__(self):
        self.env_prefix = "GOVSIGHT_DB_"
        self.credential_mapping = {
            "gl_primary": "GL_PRIMARY",
            "utility_management": "UTILITY_MGMT", 
            "asset_management": "ASSET_MGMT",
            "permits_licensing": "PERMITS_LIC",
            "payroll": "PAYROLL"
        }
    
    def store_credentials(self, db_name: str, credentials: Dict[str, str]) -> bool:
        """
        Store database credentials in environment variables.
        
        Args:
            db_name: Database identifier
            credentials: Dictionary containing host, port, database, username, password
            
        Returns:
            True if credentials stored successfully
        """
        try:
            if db_name not in self.credential_mapping:
                logger.error(f"Unknown database: {db_name}")
                return False
            
            db_prefix = f"{self.env_prefix}{self.credential_mapping[db_name]}_"
            
            # Store each credential component
            for key, value in credentials.items():
                if key in ["host", "port", "database", "username", "password"]:
                    env_var = f"{db_prefix}{key.upper()}"
                    os.environ[env_var] = str(value) if value else ""
                    logger.info(f"Stored credential {env_var} for {db_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing credentials for {db_name}: {e}")
            return False
    
    def get_credentials(self, db_name: str) -> Dict[str, str]:
        """
        Retrieve database credentials from environment variables.
        
        Args:
            db_name: Database identifier
            
        Returns:
            Dictionary containing database connection parameters
        """
        try:
            if db_name not in self.credential_mapping:
                logger.warning(f"Unknown database: {db_name}")
                return {}
            
            db_prefix = f"{self.env_prefix}{self.credential_mapping[db_name]}_"
            
            credentials = {}
            for key in ["host", "port", "database", "username", "password"]:
                env_var = f"{db_prefix}{key.upper()}"
                credentials[key] = os.environ.get(env_var, "")
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error retrieving credentials for {db_name}: {e}")
            return {}
    
    def remove_credentials(self, db_name: str) -> bool:
        """Remove stored credentials for a database."""
        try:
            if db_name not in self.credential_mapping:
                return False
            
            db_prefix = f"{self.env_prefix}{self.credential_mapping[db_name]}_"
            
            for key in ["host", "port", "database", "username", "password"]:
                env_var = f"{db_prefix}{key.upper()}"
                if env_var in os.environ:
                    del os.environ[env_var]
                    logger.info(f"Removed credential {env_var}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing credentials for {db_name}: {e}")
            return False
    
    def migrate_plaintext_credentials(self, config_file: str = "system_settings.json") -> Dict[str, Any]:
        """
        Migrate plaintext credentials from configuration file to environment variables.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Migration report with results
        """
        migration_report = {
            "success": False,
            "databases_migrated": [],
            "databases_failed": [],
            "credentials_removed": [],
            "errors": []
        }
        
        try:
            if not os.path.exists(config_file):
                migration_report["errors"].append(f"Configuration file not found: {config_file}")
                return migration_report
            
            # Load existing configuration
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            database_config = config.get("database", {})
            databases = database_config.get("databases", {})
            
            # Migrate each database's credentials
            for db_name, db_info in databases.items():
                try:
                    # Extract credentials
                    credentials = {
                        "host": db_info.get("host", ""),
                        "port": db_info.get("port", ""),
                        "database": db_info.get("database", ""),
                        "username": db_info.get("username", ""),
                        "password": db_info.get("password", "")
                    }
                    
                    # Only migrate if there are actual credentials
                    if any(credentials.values()):
                        if self.store_credentials(db_name, credentials):
                            migration_report["databases_migrated"].append(db_name)
                            
                            # Clear credentials from config
                            for key in ["host", "port", "database", "username", "password"]:
                                if key in db_info:
                                    db_info[key] = ""
                                    migration_report["credentials_removed"].append(f"{db_name}.{key}")
                        else:
                            migration_report["databases_failed"].append(db_name)
                    
                except Exception as e:
                    migration_report["databases_failed"].append(db_name)
                    migration_report["errors"].append(f"Error migrating {db_name}: {str(e)}")
            
            # Save cleaned configuration
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            migration_report["success"] = len(migration_report["databases_failed"]) == 0
            
            logger.info(f"Credential migration completed: {migration_report}")
            
        except Exception as e:
            migration_report["errors"].append(f"Migration failed: {str(e)}")
            logger.error(f"Credential migration error: {e}")
        
        return migration_report
    
    def get_redacted_credentials(self, db_name: str) -> Dict[str, str]:
        """Get credentials with password redacted for logging/display."""
        credentials = self.get_credentials(db_name)
        redacted = credentials.copy()
        if redacted.get("password"):
            redacted["password"] = "*" * len(redacted["password"])
        return redacted
    
    def verify_credentials_security(self) -> Dict[str, Any]:
        """Verify that credentials are properly secured."""
        verification = {
            "secure": True,
            "issues": [],
            "databases_checked": [],
            "environment_variables_found": [],
            "plaintext_found": []
        }
        
        try:
            # Check environment variables
            for db_name in self.credential_mapping.keys():
                verification["databases_checked"].append(db_name)
                db_prefix = f"{self.env_prefix}{self.credential_mapping[db_name]}_"
                
                env_vars_found = []
                for key in ["host", "port", "database", "username", "password"]:
                    env_var = f"{db_prefix}{key.upper()}"
                    if env_var in os.environ:
                        env_vars_found.append(env_var)
                
                if env_vars_found:
                    verification["environment_variables_found"].extend(env_vars_found)
            
            # Check for plaintext credentials in configuration
            try:
                if os.path.exists("system_settings.json"):
                    with open("system_settings.json", 'r') as f:
                        config = json.load(f)
                    
                    databases = config.get("database", {}).get("databases", {})
                    for db_name, db_info in databases.items():
                        for key in ["host", "port", "database", "username", "password"]:
                            if db_info.get(key) and key != "port":  # Port numbers are OK
                                verification["plaintext_found"].append(f"{db_name}.{key}")
                
                if verification["plaintext_found"]:
                    verification["secure"] = False
                    verification["issues"].append("Plaintext credentials found in configuration file")
                
            except Exception as e:
                verification["issues"].append(f"Error checking configuration file: {e}")
        
        except Exception as e:
            verification["secure"] = False
            verification["issues"].append(f"Verification failed: {e}")
        
        return verification
    
    def create_env_template(self) -> str:
        """Create a template .env file for database credentials."""
        template_lines = [
            "# GovSight Database Credentials",
            "# Set these environment variables for secure database access",
            ""
        ]
        
        for db_name, db_code in self.credential_mapping.items():
            db_prefix = f"{self.env_prefix}{db_code}_"
            template_lines.extend([
                f"# {db_name.replace('_', ' ').title()} Database",
                f"{db_prefix}HOST=localhost",
                f"{db_prefix}PORT=5432",
                f"{db_prefix}DATABASE=database_name",
                f"{db_prefix}USERNAME=username",
                f"{db_prefix}PASSWORD=password",
                ""
            ])
        
        return "\n".join(template_lines)

# Global instance
credential_manager = SecureCredentialManager()