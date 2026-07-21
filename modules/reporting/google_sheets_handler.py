"""
Google Sheets Export Handler for Reporting System
Provides seamless Google Sheets integration with proper error handling

ARCHITECTURAL DECISION: Graceful degradation approach
WHY: Google Sheets export is optional - the system should work without it
and provide clear instructions when credentials are missing
"""

import os
import json
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


class GoogleSheetsHandler:
    """Handler for Google Sheets export with graceful degradation"""
    
    def __init__(self):
        """Initialize Google Sheets handler"""
        self.service = None
        self.credentials = None
        self.service_account_email = None
        self.is_configured = False
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Sheets service if credentials are available"""
        if not GOOGLE_API_AVAILABLE:
            return
        
        # Try to load credentials from environment
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS', '')
        
        if not creds_json:
            return
        
        try:
            # Parse credentials
            creds_data = json.loads(creds_json)
            
            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in creds_data]
            
            if missing:
                print(f"Google Sheets credentials missing fields: {missing}")
                return
            
            # Create credentials
            self.credentials = Credentials.from_service_account_info(
                creds_data,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Build service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            self.service_account_email = creds_data.get('client_email')
            self.is_configured = True
            
        except json.JSONDecodeError:
            print("Invalid JSON in GOOGLE_SHEETS_CREDENTIALS")
        except Exception as e:
            print(f"Error initializing Google Sheets: {e}")
    
    def export_to_sheets(self,
                        data: pd.DataFrame,
                        spreadsheet_id: str = None,
                        sheet_name: str = "Export",
                        create_new: bool = False) -> Dict[str, Any]:
        """
        Export DataFrame to Google Sheets
        
        Args:
            data: DataFrame to export
            spreadsheet_id: ID of existing spreadsheet (optional)
            sheet_name: Name of sheet to create/update
            create_new: Whether to create new spreadsheet
            
        Returns:
            Dict with export status and details
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'Google Sheets not configured',
                'instructions': self._get_setup_instructions()
            }
        
        try:
            # Create new spreadsheet if requested
            if create_new or not spreadsheet_id:
                spreadsheet_id = self._create_spreadsheet(
                    f"GovSight Export - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                if not spreadsheet_id:
                    return {
                        'success': False,
                        'error': 'Failed to create new spreadsheet',
                        'instructions': self._get_permission_instructions()
                    }
            
            # Convert DataFrame to values list
            values = [data.columns.tolist()] + data.values.tolist()
            
            # Update the sheet
            body = {'values': values}
            
            # Clear existing content and write new data
            range_name = f"{sheet_name}!A1"
            
            # Clear the sheet first
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:Z"
            ).execute()
            
            # Write the data
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return {
                'success': True,
                'spreadsheet_id': spreadsheet_id,
                'updated_cells': result.get('updatedCells', 0),
                'url': f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            }
            
        except HttpError as e:
            if e.resp.status == 403:
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'instructions': self._get_permission_instructions()
                }
            else:
                return {
                    'success': False,
                    'error': f'Google Sheets API error: {str(e)}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Export failed: {str(e)}'
            }
    
    def _create_spreadsheet(self, title: str) -> Optional[str]:
        """Create a new Google Sheets spreadsheet"""
        try:
            spreadsheet = {
                'properties': {'title': title}
            }
            
            result = self.service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            
            return result.get('spreadsheetId')
            
        except Exception:
            return None
    
    def _get_setup_instructions(self) -> str:
        """Get setup instructions for Google Sheets"""
        return """
        To enable Google Sheets export:
        1. Create a Google Cloud service account
        2. Download the JSON credentials file
        3. Ask your admin to configure the GOOGLE_SHEETS_CREDENTIALS secret
        4. The admin can set this in the Replit Secrets tab
        """
    
    def _get_permission_instructions(self) -> str:
        """Get permission instructions for Google Sheets"""
        if self.service_account_email:
            return f"""
            To grant access:
            1. Open or create a Google Sheets document
            2. Click 'Share' in the top right
            3. Add this email: {self.service_account_email}
            4. Set permission to 'Editor'
            5. Use the spreadsheet ID from the URL
            """
        else:
            return """
            Google Sheets permissions need to be configured.
            Please contact your administrator.
            """
    
    def show_export_interface(self, data: pd.DataFrame) -> None:
        """Show Streamlit interface for Google Sheets export"""
        if not self.is_configured:
            st.warning("📊 Google Sheets export is not configured")
            with st.expander("Setup Instructions"):
                st.markdown(self._get_setup_instructions())
            return
        
        st.markdown("### 📊 Export to Google Sheets")
        
        col1, col2 = st.columns(2)
        
        with col1:
            export_option = st.radio(
                "Export Option",
                ["Create New Spreadsheet", "Use Existing Spreadsheet"]
            )
            
            spreadsheet_id = None
            if export_option == "Use Existing Spreadsheet":
                spreadsheet_id = st.text_input(
                    "Spreadsheet ID",
                    placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    help="Find this in the spreadsheet URL between /d/ and /edit"
                )
                
                if self.service_account_email:
                    st.info(f"Make sure the spreadsheet is shared with: {self.service_account_email}")
            
            sheet_name = st.text_input(
                "Sheet Name",
                value=f"Export_{datetime.now().strftime('%Y%m%d')}",
                help="Name of the sheet tab to create/update"
            )
        
        with col2:
            st.markdown("**Export Preview**")
            st.dataframe(data.head(), use_container_width=True)
            st.caption(f"Total rows: {len(data)}, Total columns: {len(data.columns)}")
        
        if st.button("📤 Export to Google Sheets", type="primary"):
            with st.spinner("Exporting to Google Sheets..."):
                result = self.export_to_sheets(
                    data,
                    spreadsheet_id=spreadsheet_id if export_option == "Use Existing Spreadsheet" else None,
                    sheet_name=sheet_name,
                    create_new=(export_option == "Create New Spreadsheet")
                )
                
                if result['success']:
                    st.success(f"✅ Successfully exported {result.get('updated_cells', 0)} cells!")
                    st.markdown(f"[📊 Open in Google Sheets]({result['url']})")
                else:
                    st.error(f"❌ Export failed: {result['error']}")
                    if 'instructions' in result:
                        with st.expander("How to fix this"):
                            st.markdown(result['instructions'])


# Global instance for easy import
google_sheets_handler = GoogleSheetsHandler()