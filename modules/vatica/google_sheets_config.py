"""
Google Sheets Configuration Manager

Centralized management for Google Sheets credentials and configuration
Used by admin panel and all Google Sheets export functionality

ARCHITECTURAL DECISION: Centralized configuration management
WHY: Provides single source of truth for Google Sheets credentials,
reduces duplication, and makes credential management easier for administrators.
"""

import json
import os
import streamlit as st
from typing import Optional, Dict, Any
from modules.external_data.api_config import api_config

SETTINGS_FILE = "system_settings.json"

def load_google_sheets_credentials() -> Optional[str]:
    """
    Load Google Sheets credentials from environment variable
    
    Returns:
        str: JSON credential string if available, None otherwise
    """
    # Use centralized API configuration
    try:
        creds_dict = api_config.get_google_sheets_credentials()
        if creds_dict:
            # Convert dict back to JSON string for compatibility
            return json.dumps(creds_dict)
    except ValueError as e:
        print(f"Google Sheets credentials error: {e}")
    
    # Fallback to direct environment variable check
    env_creds = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if env_creds and len(env_creds) > 100:
        return env_creds
    
    return None

def validate_google_sheets_credentials(creds_json: str) -> Dict[str, Any]:
    """
    Validate Google Sheets credentials JSON
    
    Args:
        creds_json (str): JSON credential string
        
    Returns:
        dict: Validation result with 'valid', 'error', and 'data' keys
    """
    if not creds_json or len(creds_json) < 100:
        return {
            'valid': False,
            'error': 'Credentials too short (expected 2000+ characters)',
            'data': None
        }
    
    try:
        creds_data = json.loads(creds_json)
        
        # Check required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds_data]
        
        if missing_fields:
            return {
                'valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'data': None
            }
        
        # Check if it's a service account
        if creds_data.get('type') != 'service_account':
            return {
                'valid': False,
                'error': 'Credentials must be for a service account',
                'data': None
            }
        
        return {
            'valid': True,
            'error': None,
            'data': creds_data
        }
        
    except json.JSONDecodeError as e:
        return {
            'valid': False,
            'error': f'Invalid JSON format: {str(e)}',
            'data': None
        }

def get_google_sheets_status() -> Dict[str, Any]:
    """
    Get current Google Sheets configuration status
    
    Returns:
        dict: Status information including availability, project details, etc.
    """
    creds = load_google_sheets_credentials()
    
    if not creds:
        return {
            'available': False,
            'configured': False,
            'error': 'No credentials found',
            'project_id': None,
            'service_account': None
        }
    
    validation = validate_google_sheets_credentials(creds)
    
    if not validation['valid']:
        return {
            'available': False,
            'configured': True,
            'error': validation['error'],
            'project_id': None,
            'service_account': None
        }
    
    data = validation['data']
    return {
        'available': True,
        'configured': True,
        'error': None,
        'project_id': data.get('project_id'),
        'service_account': data.get('client_email')
    }

def save_google_sheets_credentials(creds_json: str) -> bool:
    """
    Note: Google Sheets credentials should be set via environment variable
    
    Args:
        creds_json (str): JSON credential string
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    # Validate first
    validation = validate_google_sheets_credentials(creds_json)
    if not validation['valid']:
        return False
    
    # Note: In production, credentials should be set via environment variables
    # This function temporarily sets the environment variable for the current session
    try:
        # Apply to environment for current session only
        os.environ["GOOGLE_SHEETS_CREDENTIALS"] = creds_json
        
        st.warning(
            "⚠️ Credentials set for current session only. "
            "For permanent configuration, set the GOOGLE_SHEETS_CREDENTIALS "
            "environment variable in your deployment settings."
        )
        
        return True
        
    except Exception:
        return False