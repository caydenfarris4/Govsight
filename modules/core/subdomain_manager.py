import os
import json
import streamlit as st
from typing import Optional, Dict, Any
from pathlib import Path


class SubdomainManager:
    """
    Manages multi-tenant subdomain detection and city-specific configuration.
    
    Supports deployment scenarios:
    - Production: citya.govsight.net, cityb.govsight.net (Cloud Run)
    - Development: localhost with manual override
    
    Usage:
        manager = SubdomainManager()
        city_config = manager.get_city_config()
        
        if city_config:
            st.title(f"Welcome to {city_config['display_name']}")
    """
    
    def __init__(self, config_path: str = "configs/cities.json"):
        self.config_path = config_path
        self._cities_config = None
        self._current_subdomain = None
        
    def get_subdomain(self) -> Optional[str]:
        """
        Detect the current subdomain from various sources.
        
        Priority:
        1. Session state override (for development)
        2. X-Forwarded-Host header (Cloud Run)
        3. HTTP headers from Streamlit
        4. Environment variable
        
        Returns:
            Subdomain string (e.g., 'citya') or None
        """
        if self._current_subdomain:
            return self._current_subdomain
            
        # Check session state override (dev mode)
        if 'override_subdomain' in st.session_state:
            self._current_subdomain = st.session_state.override_subdomain
            return self._current_subdomain
        
        # Try to get from headers (Cloud Run)
        try:
            # Check X-Forwarded-Host header (set by Cloud Load Balancer)
            headers = st.context.headers if hasattr(st, 'context') else {}
            
            if 'x-forwarded-host' in headers:
                host = headers['x-forwarded-host']
                subdomain = self._extract_subdomain(host)
                if subdomain:
                    self._current_subdomain = subdomain
                    return subdomain
            
            # Fallback to Host header
            if 'host' in headers:
                host = headers['host']
                subdomain = self._extract_subdomain(host)
                if subdomain:
                    self._current_subdomain = subdomain
                    return subdomain
                    
        except Exception as e:
            # Headers not available (local dev or old Streamlit version)
            pass
        
        # Check environment variable
        env_subdomain = os.getenv('GOVSIGHT_SUBDOMAIN')
        if env_subdomain:
            self._current_subdomain = env_subdomain
            return env_subdomain
        
        # Default to None (no subdomain detected)
        return None
    
    def _extract_subdomain(self, host: str) -> Optional[str]:
        """
        Extract subdomain from host string.
        
        Examples:
            citya.govsight.net -> citya
            cityb.govsight.net -> cityb
            localhost:5000 -> None
        """
        if not host:
            return None
            
        # Remove port if present
        host = host.split(':')[0]
        
        # Check if it's a govsight.net domain
        if '.govsight.net' in host:
            parts = host.split('.')
            if len(parts) >= 3:
                # First part is the subdomain
                return parts[0]
        
        return None
    
    def get_cities_config(self) -> Dict[str, Any]:
        """
        Load city configuration from JSON file.
        
        Returns:
            Dictionary of city configurations
        """
        if self._cities_config is not None:
            return self._cities_config
            
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # Return default config if file doesn't exist
            return {}
        
        try:
            with open(config_file, 'r') as f:
                self._cities_config = json.load(f)
                return self._cities_config
        except Exception as e:
            st.error(f"Error loading city configuration: {e}")
            return {}
    
    def get_city_config(self, subdomain: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific city.
        
        Args:
            subdomain: City subdomain (optional, auto-detected if not provided)
            
        Returns:
            City configuration dictionary or None
        """
        if subdomain is None:
            subdomain = self.get_subdomain()
        
        if not subdomain:
            return None
        
        cities = self.get_cities_config()
        return cities.get(subdomain)
    
    def get_database_name(self, base_name: str = "govsight") -> str:
        """
        Get city-specific database name.
        
        Args:
            base_name: Base database name
            
        Returns:
            City-specific database name (e.g., 'citya_govsight')
        """
        subdomain = self.get_subdomain()
        
        if subdomain:
            city_config = self.get_city_config(subdomain)
            if city_config and 'database_prefix' in city_config:
                return f"{city_config['database_prefix']}_{base_name}"
        
        # Default database name
        return base_name
    
    def is_multi_tenant(self) -> bool:
        """Check if running in multi-tenant mode."""
        return self.get_subdomain() is not None
    
    def set_override_subdomain(self, subdomain: str):
        """
        Set subdomain override for development/testing.
        
        Args:
            subdomain: Subdomain to use (e.g., 'citya')
        """
        st.session_state.override_subdomain = subdomain
        self._current_subdomain = subdomain
    
    def clear_override(self):
        """Clear subdomain override."""
        if 'override_subdomain' in st.session_state:
            del st.session_state.override_subdomain
        self._current_subdomain = None
    
    def render_city_selector(self):
        """
        Render a city selector dropdown for development.
        Only shows if no subdomain is auto-detected.
        """
        if self.get_subdomain():
            # Already have a subdomain, don't show selector
            return
        
        cities = self.get_cities_config()
        
        if not cities:
            st.warning("No city configurations found. Add cities in configs/cities.json")
            return
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Development Mode")
        
        city_options = ["None"] + list(cities.keys())
        current = st.session_state.get('override_subdomain', "None")
        
        selected = st.sidebar.selectbox(
            "Select City",
            city_options,
            index=city_options.index(current) if current in city_options else 0,
            key="city_selector_dropdown"
        )
        
        if selected != "None" and selected != current:
            self.set_override_subdomain(selected)
            st.rerun()
        elif selected == "None" and current != "None":
            self.clear_override()
            st.rerun()


def get_current_city() -> Optional[Dict[str, Any]]:
    """
    Convenience function to get current city configuration.
    
    Returns:
        City configuration dictionary or None
    """
    manager = SubdomainManager()
    return manager.get_city_config()


def get_city_display_name(default: str = "GovSight") -> str:
    """
    Get the display name for the current city.
    
    Args:
        default: Default name if no city detected
        
    Returns:
        City display name
    """
    city_config = get_current_city()
    
    if city_config and 'display_name' in city_config:
        return city_config['display_name']
    
    return default
