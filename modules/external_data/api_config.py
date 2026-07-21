"""
Centralized API Configuration Module
Manages all external API keys and credentials using environment variables

SECURITY: All API keys are loaded from environment variables
Never hardcode API keys or credentials in the source code
"""

import os
import json
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class APIConfig:
    """Centralized API configuration and key management"""
    
    def __init__(self):
        """Initialize API configuration from environment variables"""
        self.fred_api_key = os.environ.get('FRED_API_KEY', '')
        self.bea_api_key = os.environ.get('BEA_API_KEY', '')
        self.google_sheets_credentials = os.environ.get('GOOGLE_SHEETS_CREDENTIALS', '')
        
        # API endpoints
        self.fred_base_url = "https://api.stlouisfed.org/fred"
        self.bea_base_url = "https://apps.bea.gov/api/data"
        
        # Request configuration
        self.timeout = 30  # 30 seconds timeout for all API calls
        self.max_retries = 3
        self.backoff_factor = 1  # Exponential backoff: 1, 2, 4 seconds
        
    def get_fred_key(self) -> str:
        """Get FRED API key with validation"""
        if not self.fred_api_key:
            raise ValueError(
                "FRED API key not configured. Please set the FRED_API_KEY environment variable. "
                "You can get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html"
            )
        return self.fred_api_key
    
    def get_bea_key(self) -> str:
        """Get BEA API key with validation"""
        if not self.bea_api_key:
            raise ValueError(
                "BEA API key not configured. Please set the BEA_API_KEY environment variable. "
                "You can get a free API key at: https://apps.bea.gov/api/signup"
            )
        return self.bea_api_key
    
    def get_google_sheets_credentials(self) -> Optional[Dict[str, Any]]:
        """Get Google Sheets credentials from environment variable"""
        if not self.google_sheets_credentials:
            return None
        
        try:
            # Parse JSON credentials from environment variable
            creds = json.loads(self.google_sheets_credentials)
            
            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in creds]
            
            if missing:
                # Return None instead of raising error for graceful degradation
                return None
            
            if creds.get('type') != 'service_account':
                # Return None instead of raising error for graceful degradation
                return None
            
            return creds
            
        except json.JSONDecodeError:
            # Return None instead of raising error for graceful degradation
            return None
        except Exception:
            # Return None instead of raising error for graceful degradation
            return None
    
    def create_session_with_retries(self) -> requests.Session:
        """Create a requests session with retry logic and timeout"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["GET", "POST"]  # Only retry safe methods
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def make_api_request(self, url: str, params: Dict[str, Any] = None, 
                         method: str = "GET", timeout: int = None) -> Dict[str, Any]:
        """
        Make an API request with retry logic and timeout
        
        Args:
            url: API endpoint URL
            params: Request parameters
            method: HTTP method (GET or POST)
            timeout: Request timeout in seconds (defaults to self.timeout)
        
        Returns:
            JSON response data
        
        Raises:
            requests.exceptions.RequestException: If request fails after all retries
        """
        session = self.create_session_with_retries()
        timeout = timeout or self.timeout
        
        try:
            if method.upper() == "GET":
                response = session.get(url, params=params, timeout=timeout)
            elif method.upper() == "POST":
                response = session.post(url, json=params, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise requests.exceptions.RequestException(
                f"Request timed out after {timeout} seconds. The external API may be slow or unavailable."
            )
        except requests.exceptions.ConnectionError:
            raise requests.exceptions.RequestException(
                "Could not connect to the external API. Please check your internet connection."
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise requests.exceptions.RequestException(
                    "Invalid API key. Please check your API key configuration."
                )
            elif e.response.status_code == 403:
                raise requests.exceptions.RequestException(
                    "Access forbidden. Your API key may not have the required permissions."
                )
            elif e.response.status_code == 429:
                raise requests.exceptions.RequestException(
                    "Rate limit exceeded. Please try again later."
                )
            else:
                raise requests.exceptions.RequestException(
                    f"HTTP error {e.response.status_code}: {str(e)}"
                )
        except Exception as e:
            raise requests.exceptions.RequestException(
                f"Unexpected error during API request: {str(e)}"
            )
    
    def check_api_keys_status(self) -> Dict[str, bool]:
        """Check which API keys are configured"""
        return {
            'fred': bool(self.fred_api_key),
            'bea': bool(self.bea_api_key),
            'google_sheets': bool(self.google_sheets_credentials)
        }
    
    def get_missing_keys_instructions(self) -> str:
        """Get instructions for configuring missing API keys"""
        status = self.check_api_keys_status()
        missing = [key for key, configured in status.items() if not configured]
        
        if not missing:
            return "All API keys are configured!"
        
        instructions = ["The following API keys are not configured:"]
        
        if 'fred' in missing:
            instructions.append(
                "\n**FRED API Key:**\n"
                "1. Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html\n"
                "2. Set environment variable: FRED_API_KEY=your_key_here"
            )
        
        if 'bea' in missing:
            instructions.append(
                "\n**BEA API Key:**\n"
                "1. Get a free key at: https://apps.bea.gov/api/signup\n"
                "2. Set environment variable: BEA_API_KEY=your_key_here"
            )
        
        if 'google_sheets' in missing:
            instructions.append(
                "\n**Google Sheets Credentials:**\n"
                "1. Create a service account in Google Cloud Console\n"
                "2. Download the JSON credentials file\n"
                "3. Set environment variable: GOOGLE_SHEETS_CREDENTIALS='<json_content>'"
            )
        
        return "\n".join(instructions)


# Global instance for easy access
api_config = APIConfig()