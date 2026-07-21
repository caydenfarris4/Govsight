"""
Enterprise Configuration Management System
Provides centralized, validated configuration management with environment support
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union, TypeVar, Generic
from dataclasses import dataclass, field
from pathlib import Path
import streamlit as st

# Type definitions
T = TypeVar('T')

@dataclass
class ConfigSchema:
    """Configuration schema definition for validation"""
    required_fields: list = field(default_factory=list)
    optional_fields: dict = field(default_factory=dict)
    validators: dict = field(default_factory=dict)

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class ConfigManager:
    """
    Enterprise-grade configuration manager with validation and environment support
    
    Features:
    - Environment-specific configurations (dev, staging, prod)
    - Schema validation with type checking
    - Secure default fallbacks
    - Centralized configuration access
    - Auto-reload capability
    - Audit logging of configuration changes
    """
    
    def __init__(self, config_dir: str = "config", env: Optional[str] = None):
        self.config_dir = Path(config_dir)
        self.env = env or os.getenv("GOVSIGHT_ENV", "development")
        self.config_cache: Dict[str, Any] = {}
        self.schemas: Dict[str, ConfigSchema] = {}
        self.logger = self._setup_logger()
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize default configurations
        self._initialize_default_configs()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated configuration logger"""
        logger = logging.getLogger(f"govsight.config.{self.env}")
        logger.setLevel(logging.INFO)
        
        # Create handler if it doesn't exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def register_schema(self, config_name: str, schema: ConfigSchema) -> None:
        """Register a configuration schema for validation"""
        self.schemas[config_name] = schema
        self.logger.info(f"Registered schema for {config_name}")
    
    def get_config(self, config_name: str, reload: bool = False) -> Dict[str, Any]:
        """
        Get configuration with caching and validation
        
        Args:
            config_name: Name of the configuration file (without .json)
            reload: Force reload from disk
            
        Returns:
            Dict containing the configuration
            
        Raises:
            ConfigurationError: If configuration is invalid or missing
        """
        cache_key = f"{config_name}_{self.env}"
        
        # Return cached config if available and not forcing reload
        if not reload and cache_key in self.config_cache:
            return self.config_cache[cache_key]
        
        try:
            # Load configuration from file
            config = self._load_config_file(config_name)
            
            # Validate against schema if available
            if config_name in self.schemas:
                config = self._validate_config(config_name, config)
            
            # Cache the configuration
            self.config_cache[cache_key] = config
            
            self.logger.info(f"Loaded configuration: {config_name} for environment: {self.env}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration {config_name}: {e}")
            raise ConfigurationError(f"Configuration error for {config_name}: {e}")
    
    def _load_config_file(self, config_name: str) -> Dict[str, Any]:
        """Load configuration file with environment override support"""
        # Try environment-specific config first
        env_config_path = self.config_dir / f"{config_name}.{self.env}.json"
        base_config_path = self.config_dir / f"{config_name}.json"
        
        base_config = {}
        if base_config_path.exists():
            with open(base_config_path, 'r') as f:
                base_config = json.load(f)
        
        # Override with environment-specific settings
        if env_config_path.exists():
            with open(env_config_path, 'r') as f:
                env_config = json.load(f)
            base_config.update(env_config)
        
        return base_config
    
    def _validate_config(self, config_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration against registered schema"""
        schema = self.schemas[config_name]
        
        # Check required fields
        for field in schema.required_fields:
            if field not in config:
                raise ConfigurationError(f"Required field '{field}' missing in {config_name}")
        
        # Apply defaults for optional fields
        for field, default_value in schema.optional_fields.items():
            if field not in config:
                config[field] = default_value
        
        # Run custom validators
        for field, validator in schema.validators.items():
            if field in config:
                try:
                    config[field] = validator(config[field])
                except Exception as e:
                    raise ConfigurationError(f"Validation failed for {field} in {config_name}: {e}")
        
        return config
    
    def set_config_value(self, config_name: str, key: str, value: Any) -> None:
        """Set a configuration value and persist to file"""
        config = self.get_config(config_name)
        config[key] = value
        
        # Persist to environment-specific file
        env_config_path = self.config_dir / f"{config_name}.{self.env}.json"
        with open(env_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Update cache
        cache_key = f"{config_name}_{self.env}"
        self.config_cache[cache_key] = config
        
        self.logger.info(f"Updated {config_name}.{key} = {value}")
    
    def _initialize_default_configs(self) -> None:
        """Initialize default configuration files if they don't exist"""
        default_configs = {
            "database": {
                "type": "SQLite",
                "sqlite_file": "databases/core/caselle_gl0_mock.db",
                "connection_timeout": 30,
                "pool_size": 5,
                "max_overflow": 10
            },
            "security": {
                "session_timeout": 3600,
                "max_file_size_mb": 50,
                "allowed_file_types": [".pdf", ".csv"],
                "enable_audit_logging": True,
                "bcrypt_rounds": 12
            },
            "performance": {
                "cache_enabled": True,
                "cache_ttl": 300,
                "max_cache_size": 100,
                "lazy_loading": True,
                "compression_enabled": True
            },
            "ui": {
                "page_title": "GovSight Financial Analyzer",
                "layout": "wide",
                "theme": "municipal",
                "accessibility_enabled": True
            }
        }
        
        for config_name, default_values in default_configs.items():
            config_path = self.config_dir / f"{config_name}.json"
            if not config_path.exists():
                with open(config_path, 'w') as f:
                    json.dump(default_values, f, indent=2)
                self.logger.info(f"Created default configuration: {config_name}")

# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config(config_name: str, key: Optional[str] = None, default: Any = None) -> Any:
    """
    Convenience function to get configuration values
    
    Args:
        config_name: Configuration file name
        key: Specific key to retrieve (optional)
        default: Default value if key not found
        
    Returns:
        Configuration value or entire config dict
    """
    try:
        manager = get_config_manager()
        config = manager.get_config(config_name)
        
        if key is None:
            return config
        
        return config.get(key, default)
        
    except ConfigurationError:
        if key is None:
            return {}
        return default

# Register common configuration schemas
def register_default_schemas():
    """Register default configuration schemas"""
    manager = get_config_manager()
    
    # Database configuration schema
    db_schema = ConfigSchema(
        required_fields=["type"],
        optional_fields={
            "sqlite_file": "databases/core/caselle_gl0_mock.db",
            "connection_timeout": 30,
            "pool_size": 5
        },
        validators={
            "type": lambda x: x if x in ["SQLite", "PostgreSQL", "MySQL"] else "SQLite",
            "connection_timeout": lambda x: max(1, int(x)),
            "pool_size": lambda x: max(1, min(20, int(x)))
        }
    )
    manager.register_schema("database", db_schema)
    
    # Security configuration schema
    security_schema = ConfigSchema(
        required_fields=["session_timeout"],
        optional_fields={
            "max_file_size_mb": 50,
            "allowed_file_types": [".pdf", ".csv"],
            "enable_audit_logging": True
        },
        validators={
            "session_timeout": lambda x: max(300, int(x)),  # Minimum 5 minutes
            "max_file_size_mb": lambda x: max(1, min(500, int(x)))  # 1MB to 500MB
        }
    )
    manager.register_schema("security", security_schema)

# Initialize schemas on module import
register_default_schemas()