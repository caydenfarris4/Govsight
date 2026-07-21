"""
Credential Management System for Multi-Organization Deployment
Handles secure storage and retrieval of API credentials in organized folder structure

ARCHITECTURAL DECISION: Separate file-based credential storage
WHY: Each organization needs isolated credential storage for security and scalability.
File-based approach allows easy backup, migration, and organization-specific access control.
"""

import os
import json
import streamlit as st
from typing import Optional, Dict, Any, List
from datetime import datetime
try:
    from modules.external_data.api_config import api_config
except ImportError:
    api_config = None

class CredentialsManager:
    """Manages API credentials for multiple organizations with secure file storage"""
    
    def __init__(self):
        self.base_path = "credentials"
        self.google_sheets_path = os.path.join(self.base_path, "google_sheets")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create credential directory structure if it doesn't exist"""
        os.makedirs(self.google_sheets_path, exist_ok=True)
    
    def get_organization_folder(self, org_name: str = None) -> str:
        """Get the organization-specific folder path"""
        if not org_name:
            org_name = st.session_state.get('selected_org', 'default_org')
        
        org_folder = os.path.join(self.google_sheets_path, org_name)
        os.makedirs(org_folder, exist_ok=True)
        return org_folder
    
    def save_google_sheets_credentials(self, credentials_json: str, org_name: str = None) -> Dict[str, Any]:
        """
        Save Google Sheets credentials to environment (session only)
        Note: For production, use environment variables in deployment settings
        
        Args:
            credentials_json: JSON string of service account credentials
            org_name: Organization name (not used, kept for compatibility)
            
        Returns:
            Dict with success status
        """
        try:
            # Validate JSON format first
            creds_data = json.loads(credentials_json)
            
            # Validate required fields
            required_fields = ["type", "project_id", "private_key", "client_email"]
            missing = [f for f in required_fields if f not in creds_data]
            
            if missing:
                return {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing)}"
                }
            
            if creds_data.get('type') != 'service_account':
                return {
                    "success": False,
                    "error": "File must be a service account JSON file"
                }
            
            # Set environment variable for current session
            os.environ["GOOGLE_SHEETS_CREDENTIALS"] = credentials_json
            
            st.warning(
                "⚠️ Credentials set for current session only. \n"
                "For permanent configuration:\n"
                "1. Set GOOGLE_SHEETS_CREDENTIALS environment variable in your deployment settings\n"
                "2. Copy the JSON content (excluding any formatting)\n"
                "3. Restart the application after setting the environment variable"
            )
            
            return {
                "success": True,
                "project_id": creds_data.get('project_id'),
                "client_email": creds_data.get('client_email'),
                "note": "Credentials set for current session only"
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON file: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error setting credentials: {str(e)}"
            }
    
    def load_google_sheets_credentials(self, org_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Load Google Sheets credentials from environment variable
        
        Args:
            org_name: Organization name (not used, kept for compatibility)
            
        Returns:
            Credentials data or None if not found
        """
        # First try centralized API config
        if api_config:
            try:
                return api_config.get_google_sheets_credentials()
            except ValueError:
                pass
        
        # Try direct environment variable
        try:
            env_creds = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
            if env_creds:
                return json.loads(env_creds)
        except json.JSONDecodeError:
            pass
        
        # Legacy: Check file system (for backward compatibility only)
        try:
            org_folder = self.get_organization_folder(org_name)
            file_path = os.path.join(org_folder, "service_account.json")
            
            if os.path.exists(file_path):
                st.warning(
                    "⚠️ Using credentials from file system (deprecated). "
                    "Please migrate to GOOGLE_SHEETS_CREDENTIALS environment variable."
                )
                with open(file_path, 'r') as f:
                    data = json.load(f)
                return data.get('credentials')
        except Exception:
            pass
        
        return None
    
    def get_credentials_status(self, org_name: str = None) -> Dict[str, Any]:
        """
        Get status of Google Sheets credentials for organization
        
        Returns:
            Status information including file existence, metadata
        """
        try:
            org_folder = self.get_organization_folder(org_name)
            file_path = os.path.join(org_folder, "service_account.json")
            
            if not os.path.exists(file_path):
                return {
                    "configured": False,
                    "file_path": file_path,
                    "organization": org_name or st.session_state.get('selected_org', 'default_org')
                }
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            
            return {
                "configured": True,
                "file_path": file_path,
                "uploaded_date": metadata.get('uploaded_date'),
                "project_id": metadata.get('project_id'),
                "client_email": metadata.get('client_email'),
                "organization": metadata.get('organization')
            }
            
        except Exception as e:
            return {
                "configured": False,
                "error": str(e),
                "file_path": file_path if 'file_path' in locals() else None
            }
    
    def delete_google_sheets_credentials(self, org_name: str = None) -> bool:
        """Delete Google Sheets credentials for organization"""
        try:
            org_folder = self.get_organization_folder(org_name)
            file_path = os.path.join(org_folder, "service_account.json")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
            
        except Exception as e:
            st.error(f"Error deleting credentials: {str(e)}")
            return False
    
    def list_configured_organizations(self) -> List[str]:
        """List all organizations that have configured Google Sheets credentials"""
        try:
            if not os.path.exists(self.google_sheets_path):
                return []
            
            configured_orgs = []
            for item in os.listdir(self.google_sheets_path):
                org_path = os.path.join(self.google_sheets_path, item)
                if os.path.isdir(org_path):
                    credentials_file = os.path.join(org_path, "service_account.json")
                    if os.path.exists(credentials_file):
                        configured_orgs.append(item)
            
            return configured_orgs
            
        except Exception as e:
            st.error(f"Error listing organizations: {str(e)}")
            return []