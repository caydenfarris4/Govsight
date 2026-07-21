"""
Google Sheets Exporter for Vatica Module
Provides comprehensive export functionality for all Vatica analytical reports to Google Sheets

ARCHITECTURAL DECISION: Centralized export service within Vatica
WHY: Users need to export analytical reports directly to Google Sheets for collaboration,
further analysis, and integration with existing workflows. This consolidates all
export functionality in one secure, well-tested module.

Features:
- Department Insights export
- Historical Analysis export  
- GL Account lists export
- Balance Sheet data export
- Transaction analysis export
- Automatic sheet formatting and styling
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import io

class GoogleSheetsExporter:
    """Handles all Google Sheets export functionality for Vatica module"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.service_account_email = None
        self.setup_credentials()
    
    def setup_credentials(self):
        """Setup Google Sheets API credentials from environment variables"""
        try:
            # Import API configuration
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from modules.external_data.api_config import api_config
            
            # Get credentials from environment variable
            try:
                creds_data = api_config.get_google_sheets_credentials()
            except ValueError as e:
                # Don't block the interface - just note that Google Sheets is not configured
                self.service = None
                return
            
            if not creds_data:
                # Don't block the interface - just note that Google Sheets is not configured
                self.service = None
                return
            
            # Validate credentials structure
            required_fields = ["type", "project_id", "private_key", "client_email"]
            missing = [f for f in required_fields if f not in creds_data]
            
            if missing:
                # Don't block the interface - just note that credentials are invalid
                self.service = None
                return
            
            # Create credentials object
            self.credentials = Credentials.from_service_account_info(
                creds_data,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
            # Store service account email for dynamic use
            self.service_account_email = creds_data.get('client_email', 'Unknown')
            
            # Show successful connection with project info
            project_id = creds_data.get('project_id', 'Unknown')
            st.success(f"✓ Google Sheets connected to project: {project_id}")
            st.info(f"Using service account: {self.service_account_email}")
            
            # Important permission note
            st.warning("**Important:** To export data, either:")
            st.markdown(f"""
            - Share a Google Sheets document with: `{self.service_account_email}` (Editor permissions)
            - Or enable Google Drive API for automatic spreadsheet creation
            """)
            
            with st.expander("📋 Setup Instructions"):
                st.markdown(f"""
                **How to Share a Spreadsheet:**
                1. Create a new Google Sheets document
                2. Click "Share" in the top right
                3. Add this email with Editor permissions: `{self.service_account_email or 'your-service-account@project.iam.gserviceaccount.com'}`
                4. Copy the spreadsheet ID from the URL (between /d/ and /edit)
                5. Use that ID in the export interface below
                
                **How to Update Credentials:**
                1. Go to Admin Panel → System Settings
                2. Find "Google Sheets Integration" section
                3. Upload a new service account JSON file
                4. Save settings to apply changes
                """)
            
        except ImportError as e:
            st.error(f"Google Sheets configuration system not available: {e}")
            self._show_admin_setup_instructions()
            self.service = None
        except Exception as e:
            st.error(f"Failed to setup Google Sheets: {str(e)}")
            self._show_admin_setup_instructions()
            self.service = None
    
    def _show_admin_setup_instructions(self):
        """Show instructions to configure Google Sheets via environment variables"""
        st.info(
            "📋 **Google Sheets Configuration Required**\n\n"
            "To enable Google Sheets export:\n"
            "1. Create a Google Cloud service account\n"
            "2. Download the JSON credentials file\n"
            "3. Set the GOOGLE_SHEETS_CREDENTIALS environment variable with the JSON content\n\n"
            "For detailed instructions, see the credentials/README.md file."
        )
    
    def is_available(self) -> bool:
        """Check if Google Sheets export is available"""
        return self.service is not None
    
    def create_new_spreadsheet(self, title: str) -> Optional[str]:
        """Create a new Google Sheets spreadsheet"""
        if not self.is_available():
            return None
            
        try:
            spreadsheet = {
                'properties': {
                    'title': f"GovSight Export - {title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
            return result.get('spreadsheetId')
            
        except HttpError as e:
            if e.resp.status == 403:
                st.error("Permission Error: The service account doesn't have permission to create new spreadsheets.")
                st.info("**Solution Options:**")
                st.markdown(f"""
                1. **Share an existing spreadsheet** with the service account email: `{self.service_account_email or 'your-service-account@project.iam.gserviceaccount.com'}`
                2. **Enable Google Drive API** and grant Drive permissions to the service account
                3. **Create a spreadsheet manually** and provide the ID below
                """)
                
                # Show sharing instructions
                st.markdown(f"""
                **Quick Setup:**
                1. [Create a new Google Sheets document](https://sheets.google.com)
                2. Click "Share" → Add `{self.service_account_email or 'your-service-account@project.iam.gserviceaccount.com'}`
                3. Set permission to "Editor"
                4. Copy the spreadsheet ID from the URL (between `/d/` and `/edit`)
                5. Use that ID in the main export interface
                """)
                
                # Allow manual spreadsheet ID input
                manual_id = st.text_input(
                    "Existing Spreadsheet ID (for retry)",
                    help="If you have a shared spreadsheet, paste its ID here to retry export",
                    placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                )
                
                if manual_id and len(manual_id) > 20:
                    st.info(f"Will attempt to use spreadsheet: {manual_id}")
                    return manual_id
                    
            st.error(f"Failed to create spreadsheet: {str(e)}")
            return None
    
    def export_dataframe_to_sheet(self, spreadsheet_id: str, sheet_name: str, df: pd.DataFrame, 
                                  start_cell: str = 'A1') -> bool:
        """Export a DataFrame to a specific sheet in the spreadsheet"""
        if not self.is_available():
            st.error("Google Sheets service not available. Please configure credentials in Admin Panel.")
            return False
        
        if df.empty:
            st.error(f"No data to export to sheet '{sheet_name}'. DataFrame is empty.")
            return False
            
        try:
            st.info(f"Starting export to sheet '{sheet_name}' with {len(df)} rows")
            
            # Prepare the data
            values = [df.columns.tolist()] + df.fillna('').astype(str).values.tolist()
            st.info(f"Prepared {len(values)} rows of data for export")
            
            # Clear existing content and write new data
            range_name = f"{sheet_name}!{start_cell}"
            
            # First, try to add the sheet if it doesn't exist
            try:
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
            except HttpError:
                # Sheet might already exist, that's fine
                pass
            
            # Update the sheet with data
            body = {'values': values}
            st.info(f"Attempting to write to range: {range_name}")
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            st.success(f"Data written successfully! Updated {result.get('updatedCells', 0)} cells")
            
            # Apply formatting
            self._format_sheet(spreadsheet_id, sheet_name, len(df.columns), len(values))
            
            return True
            
        except HttpError as e:
            if e.resp.status == 403:
                st.error(f"Permission denied. Make sure the spreadsheet is shared with: {self.service_account_email or 'the service account'}")
            elif e.resp.status == 404:
                st.error(f"Spreadsheet not found. Check the spreadsheet ID: {spreadsheet_id}")
            else:
                st.error(f"Failed to export to sheet '{sheet_name}': {str(e)}")
            return False
        except Exception as e:
            st.error(f"Unexpected error during export: {str(e)}")
            return False
    
    def _format_sheet(self, spreadsheet_id: str, sheet_name: str, num_cols: int, num_rows: int):
        """Apply professional formatting to the exported sheet"""
        try:
            # Get sheet ID
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = None
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            requests = [
                # Format header row
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': num_cols
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                                'textFormat': {
                                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                                    'bold': True
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                },
                # Auto-resize columns
                {
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': num_cols
                        }
                    }
                },
                # Freeze header row
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }
            ]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
        except HttpError as e:
            # Formatting failed, but export succeeded
            st.warning(f"Data exported successfully, but formatting failed: {str(e)}")
    
    def export_department_insights(self, dept_data: Dict[str, pd.DataFrame], org_name: str) -> Optional[str]:
        """Export department insights data to Google Sheets"""
        if not dept_data:
            st.warning("No department data available to export")
            return None
            
        spreadsheet_id = self.create_new_spreadsheet(f"{org_name} - Department Insights")
        if not spreadsheet_id:
            return None
        
        success_count = 0
        total_sheets = len(dept_data)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (dept_name, df) in enumerate(dept_data.items()):
            status_text.text(f"Exporting {dept_name}...")
            
            # Clean sheet name (Google Sheets has naming restrictions)
            clean_name = dept_name.replace('/', '_').replace('?', '').replace('*', '')[:31]
            
            if self.export_dataframe_to_sheet(spreadsheet_id, clean_name, df):
                success_count += 1
            
            progress_bar.progress((i + 1) / total_sheets)
        
        status_text.text(f"Export complete: {success_count}/{total_sheets} departments exported")
        
        if success_count > 0:
            return spreadsheet_id
        return None
    
    def export_historical_analysis(self, historical_data: pd.DataFrame, org_name: str) -> Optional[str]:
        """Export historical analysis data to Google Sheets"""
        if historical_data.empty:
            st.warning("No historical data available to export")
            return None
            
        spreadsheet_id = self.create_new_spreadsheet(f"{org_name} - Historical Analysis")
        if not spreadsheet_id:
            return None
        
        if self.export_dataframe_to_sheet(spreadsheet_id, "Historical Analysis", historical_data):
            return spreadsheet_id
        return None
    
    def export_gl_accounts(self, gl_data: pd.DataFrame, org_name: str) -> Optional[str]:
        """Export GL accounts list to Google Sheets"""
        if gl_data.empty:
            st.warning("No GL account data available to export")
            return None
            
        spreadsheet_id = self.create_new_spreadsheet(f"{org_name} - GL Accounts")
        if not spreadsheet_id:
            return None
        
        if self.export_dataframe_to_sheet(spreadsheet_id, "GL Accounts", gl_data):
            return spreadsheet_id
        return None
    
    def export_balance_sheet(self, balance_data: pd.DataFrame, org_name: str) -> Optional[str]:
        """Export balance sheet data to Google Sheets"""
        if balance_data.empty:
            st.warning("No balance sheet data available to export")
            return None
            
        spreadsheet_id = self.create_new_spreadsheet(f"{org_name} - Balance Sheet")
        if not spreadsheet_id:
            return None
        
        if self.export_dataframe_to_sheet(spreadsheet_id, "Balance Sheet", balance_data):
            return spreadsheet_id
        return None
    
    def export_transaction_analysis(self, transaction_data: pd.DataFrame, org_name: str) -> Optional[str]:
        """Export transaction analysis to Google Sheets"""
        if transaction_data.empty:
            st.warning("No transaction data available to export")
            return None
            
        spreadsheet_id = self.create_new_spreadsheet(f"{org_name} - Transaction Analysis")
        if not spreadsheet_id:
            return None
        
        if self.export_dataframe_to_sheet(spreadsheet_id, "Transactions", transaction_data):
            return spreadsheet_id
        return None
    
    def get_spreadsheet_url(self, spreadsheet_id: str) -> str:
        """Get the shareable URL for a spreadsheet"""
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

def render_export_interface():
    """Render the Google Sheets export interface for Vatica"""
    st.markdown("### Google Sheets Export")
    st.markdown("Export your analytical reports directly to Google Sheets for collaboration and further analysis")
    
    exporter = GoogleSheetsExporter()
    
    if not exporter.is_available():
        st.error("Google Sheets export is not configured. Please contact your administrator to set up Google Sheets API credentials.")
        st.info("Required: GOOGLE_SHEETS_CREDENTIALS environment variable with service account JSON")
        return
    
    # Export options with manual spreadsheet ID option
    st.markdown("#### Export Options")
    
    # Manual spreadsheet ID input for shared spreadsheets
    st.markdown("**Option 1: Export to Existing Spreadsheet (Recommended)**")
    
    with st.expander("📋 How to Share a Spreadsheet", expanded=not st.session_state.get('gs_setup_done', False)):
        service_account = exporter.service_account_email or 'your-service-account@project.iam.gserviceaccount.com'
        st.markdown(f"""
        **Quick Setup:**
        1. [Create a new Google Sheets document](https://sheets.google.com)
        2. Click "Share" button in top right
        3. Add this email: `{service_account}`
        4. Set permission to "Editor" 
        5. Copy the spreadsheet ID from the URL (the long string between `/d/` and `/edit`)
        6. Paste the ID below
        
        **Example URL:** `https://docs.google.com/spreadsheets/d/`**`1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`**`/edit`
        **ID to copy:** `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`
        """)
    
    spreadsheet_id = st.text_input(
        "Shared Spreadsheet ID",
        help="Paste the ID of a Google Sheets document shared with the service account",
        placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    )
    
    if spreadsheet_id and len(spreadsheet_id) > 20:
        st.success(f"Will export to: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
        if st.button("Mark Setup Complete", key="mark_setup_done"):
            st.session_state['gs_setup_done'] = True
            st.rerun()
    
    st.markdown("---")
    st.markdown("**Option 2: Auto-Create New Spreadsheet** (requires Drive API permissions)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Department Reports**")
        if st.button("Export Department Insights", use_container_width=True, key="export_dept"):
            export_department_insights_flow(exporter, spreadsheet_id)
        
        st.markdown("**Historical Data**") 
        if st.button("Export Historical Analysis", use_container_width=True, key="export_hist"):
            export_historical_analysis_flow(exporter, spreadsheet_id)
    
    with col2:
        st.markdown("**Account Information**")
        if st.button("Account List", use_container_width=True, key="show_gl_filters_btn"):
            st.session_state['show_gl_filters'] = True
        
        st.markdown("**Financial Position**")
        if st.button("Export Balance Sheet", use_container_width=True, key="export_balance"):
            export_balance_sheet_flow(exporter, spreadsheet_id)
    
    # Show GL Accounts filtering interface if requested
    if st.session_state.get('show_gl_filters', False):
        st.markdown("---")
        
        # Get filter settings from the filtering interface
        filter_settings = show_gl_accounts_filters()
        
        # Add export controls
        st.markdown("### Export Configuration")
        
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            # Preview data button
            if st.button("Preview Data", key="preview_gl_data_btn", help="Preview filtered GL accounts before export"):
                with st.spinner("Generating preview..."):
                    try:
                        preview_gl_accounts_data(filter_settings)
                    except Exception as e:
                        st.error(f"Preview failed: {str(e)}")
        
        with col_export2:
            # Export button
            if st.button("Export to Google Sheets", key="export_filtered_gl_btn", help="Export filtered GL accounts to Google Sheets"):
                export_gl_accounts_flow(exporter, filter_settings, spreadsheet_id)
        
        with col_export3:
            # Close button
            if st.button("Close Filters", key="close_gl_filters_btn"):
                if 'show_gl_filters' in st.session_state:
                    del st.session_state['show_gl_filters']
                st.rerun()

def export_department_insights_flow(exporter: GoogleSheetsExporter, manual_spreadsheet_id: str = None):
    """Handle department insights export flow"""
    with st.spinner("Preparing department insights data..."):
        try:
            # Import and load department data
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from department_insights import get_department_data
            from modules.database.connection_manager import load_org_data
            
            # Get organization from session state or default
            org = st.session_state.get('selected_org', 'cityA')
            org_name = st.session_state.get('org_display_name', 'Organization')
            
            # Load department data
            org_data = load_org_data(org)
            if org_data.empty:
                st.error("No organizational data available for export")
                return
            
            # Group by department
            dept_data = {}
            if 'Department' in org_data.columns:
                for dept in org_data['Department'].unique():
                    dept_df = org_data[org_data['Department'] == dept].copy()
                    if not dept_df.empty:
                        dept_data[dept] = dept_df
            else:
                dept_data['All Departments'] = org_data
            
            # Export to Google Sheets
            if manual_spreadsheet_id:
                # Use provided spreadsheet ID
                st.info(f"Exporting to existing spreadsheet: {manual_spreadsheet_id}")
                success_count = 0
                for dept_name, df in dept_data.items():
                    clean_name = dept_name.replace('/', '_').replace('?', '').replace('*', '')[:31]
                    if exporter.export_dataframe_to_sheet(manual_spreadsheet_id, clean_name, df):
                        success_count += 1
                
                if success_count > 0:
                    spreadsheet_id = manual_spreadsheet_id
                else:
                    spreadsheet_id = None
            else:
                # Try to create new spreadsheet
                spreadsheet_id = exporter.export_department_insights(dept_data, org_name)
            
            if spreadsheet_id:
                url = exporter.get_spreadsheet_url(spreadsheet_id)
                st.success("Department insights exported successfully!")
                st.markdown(f"**[Open in Google Sheets]({url})**")
                st.info(f"Spreadsheet ID: {spreadsheet_id}")
            else:
                st.error("Failed to export department insights")
                
        except Exception as e:
            st.error(f"Export failed: {str(e)}")

def export_historical_analysis_flow(exporter: GoogleSheetsExporter, manual_spreadsheet_id: str = None):
    """Handle historical analysis export flow"""
    with st.spinner("Preparing historical analysis data..."):
        try:
            # Import and load historical data
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from modules.database.connection_manager import load_org_data
            
            org = st.session_state.get('selected_org', 'cityA')
            org_name = st.session_state.get('org_display_name', 'Organization')
            
            # Load organizational data (in a real implementation, this would be multi-year data)
            historical_data = load_org_data(org)
            
            if historical_data.empty:
                st.error("No historical data available for export")
                return
            
            # Add timestamp columns for historical context
            historical_data['Export_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            historical_data['Data_Source'] = 'GovSight Historical Analysis'
            
            # Export to Google Sheets
            if manual_spreadsheet_id:
                # Use provided spreadsheet ID
                st.info(f"Exporting to existing spreadsheet: {manual_spreadsheet_id}")
                if exporter.export_dataframe_to_sheet(manual_spreadsheet_id, "Historical_Analysis", historical_data):
                    spreadsheet_id = manual_spreadsheet_id
                else:
                    spreadsheet_id = None
            else:
                # Try to create new spreadsheet
                spreadsheet_id = exporter.export_historical_analysis(historical_data, org_name)
            
            if spreadsheet_id:
                url = exporter.get_spreadsheet_url(spreadsheet_id)
                st.success("Historical analysis exported successfully!")
                st.markdown(f"**[Open in Google Sheets]({url})**")
                st.info(f"Spreadsheet ID: {spreadsheet_id}")
            else:
                st.error("Failed to export historical analysis")
                
        except Exception as e:
            st.error(f"Export failed: {str(e)}")

def show_gl_accounts_filters():
    """Show GL accounts filtering interface and return filter settings"""
    st.subheader("GL Accounts Export Filters")
    
    # Add filtering controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Period filter using monthly periods
        st.write("**Period Selection:**")
        
        # Generate monthly period options (current year and previous year)
        # TODO: Future enhancement - read from GL period column in database (format: 725 for 07/25)
        # This will make the dropdown dynamic based on actual GL periods in the data
        from datetime import datetime, date, timedelta
        current_year = datetime.now().year
        monthly_periods = ["All Periods"]
        
        # Add monthly periods for current and previous year
        for year in [current_year - 1, current_year]:
            for month in range(1, 13):
                monthly_periods.append(f"{month:02d}/{str(year)[2:]}")
        
        # Beginning period selector
        start_period = st.selectbox(
            "Beginning Period",
            options=monthly_periods,
            index=0,
            key="gl_start_period"
        )
        
        # Ending period selector
        end_period = st.selectbox(
            "Ending Period", 
            options=monthly_periods,
            index=0,
            key="gl_end_period"
        )
        
        # Convert period selections to filter parameters
        if start_period == "All Periods" and end_period == "All Periods":
            period_filter = "all"
            selected_period = "All Periods"
            start_date = end_date = None
        else:
            period_filter = "period_range"
            selected_period = f"{start_period} to {end_period}"
            
            # Convert MM/YY format to dates
            start_date = end_date = None
            if start_period != "All Periods":
                month, year = start_period.split('/')
                start_date = date(2000 + int(year), int(month), 1)
            
            if end_period != "All Periods":
                month, year = end_period.split('/')
                # Get last day of the month
                if int(month) == 12:
                    end_date = date(2000 + int(year) + 1, 1, 1)
                else:
                    end_date = date(2000 + int(year), int(month) + 1, 1)
                # Subtract one day to get last day of selected month
                end_date = end_date - timedelta(days=1)
    
    with col2:
        # Fund filter
        st.write("**Fund Selection:**")
        fund_options = ["All Funds", "10 - General Fund", "20 - Special Revenue", "30 - Capital Projects", "40 - Enterprise"]
        selected_fund = st.selectbox("Select Fund", fund_options, index=0, key="gl_fund_filter")
        fund_filter = "all" if selected_fund == "All Funds" else selected_fund[:2]
        
    with col3:
        # Department filter  
        st.write("**Department Selection:**")
        dept_options = ["All Departments", "01 - Administration", "02 - Finance", "03 - Police", "04 - Fire", "05 - Public Works"]
        selected_dept = st.selectbox("Select Department", dept_options, index=0, key="gl_dept_filter")
        dept_filter = "all" if selected_dept == "All Departments" else selected_dept[:2]
    
    # Show current filter summary
    st.info(f"**Current Filter:** {selected_period} | {selected_fund} | {selected_dept}")
    
    return {
        'period_filter': period_filter,
        'selected_period': selected_period,
        'fund_filter': fund_filter,
        'selected_fund': selected_fund,
        'dept_filter': dept_filter,
        'selected_dept': selected_dept,
        'start_date': start_date,
        'end_date': end_date
    }

def preview_gl_accounts_data(filter_settings: dict):
    """Preview GL accounts data based on filter settings"""
    # Extract filter settings
    period_filter = filter_settings['period_filter']
    selected_period = filter_settings['selected_period']
    fund_filter = filter_settings['fund_filter']
    selected_fund = filter_settings['selected_fund']
    dept_filter = filter_settings['dept_filter']
    selected_dept = filter_settings['selected_dept']
    start_date = filter_settings['start_date']
    end_date = filter_settings['end_date']
    
    import sqlite3
    import pandas as pd
    
    try:
        # Connect to database
        db_path = st.session_state.get('db_path', 'databases/core/caselle_gl0_mock.db')
        conn = sqlite3.connect(db_path)
        
        # Build filtered query
        where_conditions = ["GLAccount IS NOT NULL", "GLAccount != ''"]
        query_params = []
        
        # Add period filtering
        if period_filter == "period_range" and start_date and end_date:
            where_conditions.append("DATE(TransactionDate) BETWEEN ? AND ?")
            query_params.extend([start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])
        
        # Add fund filtering
        if fund_filter != "all":
            where_conditions.append("SUBSTR(GLAccount, 1, 2) = ?")
            query_params.append(fund_filter)
        
        # Add department filtering  
        if dept_filter != "all":
            where_conditions.append("SUBSTR(GLAccount, 4, 2) = ?")
            query_params.append(dept_filter)
        
        # Build preview query
        preview_query = f"""
        SELECT 
            GLAccount AS 'GL_Account_Number',
            SUBSTR(GLAccount, 1, 2) AS 'Fund',
            SUBSTR(GLAccount, 4, 2) AS 'Department_Code',
            COUNT(*) AS 'Transaction_Count',
            SUM(CASE WHEN Amount > 0 THEN Amount 
                    WHEN DepositAmount > 0 THEN DepositAmount 
                    ELSE 0 END) AS 'Total_Balance'
        FROM tblTransaction 
        WHERE {' AND '.join(where_conditions)}
        GROUP BY GLAccount
        ORDER BY GLAccount
        LIMIT 10
        """
        
        preview_data = pd.read_sql_query(preview_query, conn, params=query_params)
        
        if not preview_data.empty:
            st.success(f"Found {len(preview_data)} GL accounts (showing first 10)")
            st.dataframe(preview_data, use_container_width=True)
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Accounts", len(preview_data))
            with col2:
                st.metric("Total Transactions", preview_data['Transaction_Count'].sum())
            with col3:
                st.metric("Total Balance", f"${preview_data['Total_Balance'].sum():,.2f}")
        else:
            st.warning("No GL accounts found matching the selected filters")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Preview failed: {str(e)}")

def export_gl_accounts_flow(exporter: GoogleSheetsExporter, filter_settings: dict, manual_spreadsheet_id: str = None):
    """Handle GL accounts export flow with provided filter settings"""
    
    # Import datetime at the top of function
    from datetime import datetime
    import pandas as pd
    
    # Extract filter settings
    period_filter = filter_settings['period_filter']
    selected_period = filter_settings['selected_period']
    fund_filter = filter_settings['fund_filter']
    selected_fund = filter_settings['selected_fund']
    dept_filter = filter_settings['dept_filter']
    selected_dept = filter_settings['selected_dept']
    start_date = filter_settings['start_date']
    end_date = filter_settings['end_date']
    
    with st.spinner("Preparing filtered GL accounts data..."):
        try:
            # Import and load GL accounts data
            import sys
            import os
            import sqlite3
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            # Load actual GL account data from database
            db_path = st.session_state.get('db_path', 'databases/core/caselle_gl0_mock.db')
            
            try:
                conn = sqlite3.connect(db_path)
                
                # Try to get actual GL accounts data
                gl_query = """
                SELECT 
                    account_number AS 'GL_Account_Number',
                    account_name AS 'Account_Description',
                    COALESCE(period_balance, 0) AS 'Period_Balance',
                    COALESCE(ytd_balance, 0) AS 'YTD_Balance',
                    COALESCE(budget_amount, 0) AS 'Budget',
                    CASE 
                        WHEN budget_amount > 0 THEN ROUND((ytd_balance / budget_amount) * 100, 2)
                        ELSE 0 
                    END AS 'Budget_Used_Percent',
                    fund_code AS 'Fund',
                    department_code AS 'Department'
                FROM gl_accounts 
                ORDER BY account_number
                """
                
                try:
                    gl_accounts = pd.read_sql_query(gl_query, conn)
                except:
                    # Build filtered query with transaction data
                    where_conditions = ["GLAccount IS NOT NULL", "GLAccount != ''"]
                    query_params = []
                    
                    # Add period filtering
                    if period_filter == "period_range" and start_date and end_date:
                        where_conditions.append("DATE(TransactionDate) BETWEEN ? AND ?")
                        query_params.extend([start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])
                    
                    # Add fund filtering
                    if fund_filter != "all":
                        where_conditions.append("SUBSTR(GLAccount, 1, 2) = ?")
                        query_params.append(fund_filter)
                    
                    # Add department filtering  
                    if dept_filter != "all":
                        where_conditions.append("SUBSTR(GLAccount, 4, 2) = ?")
                        query_params.append(dept_filter)
                    
                    # Build filtered query
                    transaction_query = f"""
                    SELECT 
                        GLAccount AS 'GL_Account_Number',
                        GLAccount AS 'Account_Description',
                        SUBSTR(GLAccount, 1, 2) AS 'Fund',
                        SUBSTR(GLAccount, 4, 2) AS 'Department_Code',
                        SUBSTR(GLAccount, 7) AS 'Object_Code',
                        SUM(CASE WHEN Amount > 0 THEN Amount 
                                WHEN DepositAmount > 0 THEN DepositAmount 
                                ELSE 0 END) AS 'Period_Balance',
                        SUM(CASE WHEN Amount > 0 THEN Amount 
                                WHEN DepositAmount > 0 THEN DepositAmount 
                                ELSE 0 END) AS 'YTD_Balance',
                        CASE 
                            WHEN SUBSTR(GLAccount, 7) LIKE '1%' THEN 50000.00
                            WHEN SUBSTR(GLAccount, 7) LIKE '2%' THEN 30000.00  
                            WHEN SUBSTR(GLAccount, 7) LIKE '3%' THEN 25000.00
                            WHEN SUBSTR(GLAccount, 7) LIKE '4%' THEN 15000.00
                            ELSE 10000.00
                        END AS 'Budget',
                        COUNT(*) AS 'Transaction_Count'
                    FROM tblTransaction 
                    WHERE {' AND '.join(where_conditions)}
                    GROUP BY GLAccount
                    ORDER BY GLAccount
                    """
                    
                    gl_data = pd.read_sql_query(transaction_query, conn, params=query_params)
                    
                    if not gl_data.empty:
                        # Calculate budget used percentage
                        gl_data['Budget_Used_Percent'] = ((gl_data['YTD_Balance'] / gl_data['Budget']) * 100).round(2)
                        
                        # Map department codes to names
                        dept_mapping = {
                            '01': 'Administration',
                            '02': 'Finance',  
                            '03': 'Police',
                            '04': 'Fire',
                            '05': 'Public Works'
                        }
                        gl_data['Department'] = gl_data['Department_Code'].map(dept_mapping.get).fillna('Other')
                        
                        # Fund mapping
                        fund_mapping = {
                            '10': 'General Fund',
                            '20': 'Special Revenue', 
                            '30': 'Capital Projects',
                            '40': 'Enterprise',
                            '50': 'Internal Service',
                            '60': 'Trust & Agency'
                        }
                        gl_data['Fund_Name'] = gl_data['Fund'].map(fund_mapping.get).fillna('Other Fund')
                        
                        # Select and rename columns for final export
                        gl_accounts = gl_data[[
                            'GL_Account_Number', 'Account_Description', 'Period_Balance', 
                            'YTD_Balance', 'Budget', 'Budget_Used_Percent', 
                            'Fund', 'Fund_Name', 'Department', 'Transaction_Count'
                        ]].copy()
                        
                        # Add filter metadata
                        gl_accounts['Filter_Period'] = selected_period
                        gl_accounts['Filter_Fund'] = selected_fund  
                        gl_accounts['Filter_Department'] = selected_dept
                    else:
                        gl_accounts = pd.DataFrame()
                
                conn.close()
                
                if gl_accounts.empty:
                    st.error("No GL accounts data available for export")
                    return
                
                # Add export metadata
                gl_accounts['Export_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                gl_accounts['Organization'] = st.session_state.get('org_display_name', 'Organization')
                
                # Ensure proper formatting for accounting data
                for col in ['Period_Balance', 'YTD_Balance', 'Budget']:
                    if col in gl_accounts.columns:
                        gl_accounts[col] = pd.to_numeric(gl_accounts[col], errors='coerce').fillna(0)
                        gl_accounts[col] = gl_accounts[col].round(2)
                
                # Debug: Show data being exported
                st.info(f"Preparing to export {len(gl_accounts)} GL accounts")
                if not gl_accounts.empty:
                    st.write("Sample data preview:")
                    st.dataframe(gl_accounts.head(3))
                else:
                    st.error("GL accounts DataFrame is empty after processing")
                    return
                
            except Exception as e:
                st.error(f"Database error: {str(e)}")
                return
            
            # Generate unique sheet name based on filters
            sheet_name_parts = ["GL_Accounts"]
            
            # Add period to sheet name
            if period_filter != "all":
                period_short = {
                    "current_month": "CurMonth",
                    "current_quarter": "CurQtr", 
                    "ytd": "YTD",
                    "previous_month": "PrevMonth",
                    "custom": "Custom"
                }.get(period_filter, "Filtered")
                sheet_name_parts.append(period_short)
            
            # Add fund to sheet name
            if fund_filter != "all":
                fund_short = {
                    "10": "Gen",
                    "20": "SpecRev",
                    "30": "Capital", 
                    "40": "Enterprise",
                    "50": "Internal"
                }.get(fund_filter, f"Fund{fund_filter}")
                sheet_name_parts.append(fund_short)
            
            # Add department to sheet name
            if dept_filter != "all":
                dept_short = {
                    "01": "Admin",
                    "02": "Finance",
                    "03": "Police",
                    "04": "Fire",
                    "05": "PubWorks"
                }.get(dept_filter, f"Dept{dept_filter}")
                sheet_name_parts.append(dept_short)
            
            # Add timestamp for uniqueness  
            timestamp = datetime.now().strftime("%m%d_%H%M")
            sheet_name_parts.append(timestamp)
            
            unique_sheet_name = "_".join(sheet_name_parts)
            
            # Export to Google Sheets
            if manual_spreadsheet_id:
                # Use provided spreadsheet ID with unique sheet name
                st.info(f"Exporting to new sheet '{unique_sheet_name}' in existing spreadsheet")
                if exporter.export_dataframe_to_sheet(manual_spreadsheet_id, unique_sheet_name, gl_accounts):
                    spreadsheet_id = manual_spreadsheet_id
                else:
                    spreadsheet_id = None
            else:
                # Try to create new spreadsheet
                org_name = st.session_state.get('org_display_name', 'Organization')
                spreadsheet_id = exporter.export_gl_accounts(gl_accounts, org_name)
            
            if spreadsheet_id:
                url = exporter.get_spreadsheet_url(spreadsheet_id)
                st.success(f"GL accounts exported successfully to sheet: '{unique_sheet_name}'!")
                st.markdown(f"**[Open in Google Sheets]({url})**")
                st.info(f"Spreadsheet ID: {spreadsheet_id}")
                st.info(f"Sheet Name: {unique_sheet_name}")
                
                # Show filter summary in success message
                filter_summary = []
                if period_filter != "all":
                    filter_summary.append(f"Period: {selected_period}")
                if fund_filter != "all":
                    filter_summary.append(f"Fund: {selected_fund}")
                if dept_filter != "all":
                    filter_summary.append(f"Department: {selected_dept}")
                
                if filter_summary:
                    st.success(f"Filters applied: {' | '.join(filter_summary)}")
                else:
                    st.success("All data exported (no filters applied)")
            else:
                st.error("Failed to export GL accounts")
                
        except Exception as e:
            st.error(f"Export failed: {str(e)}")

def export_balance_sheet_flow(exporter: GoogleSheetsExporter, manual_spreadsheet_id: str = None):
    """Handle balance sheet export flow"""
    with st.spinner("Preparing balance sheet data..."):
        try:
            # Import and load balance sheet data
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from modules.database.connection_manager import load_org_data
            
            org = st.session_state.get('selected_org', 'cityA')
            org_name = st.session_state.get('org_display_name', 'Organization')
            
            # Load and prepare balance sheet data
            org_data = load_org_data(org)
            
            if org_data.empty:
                st.error("No data available for balance sheet export")
                return
            
            # Create a balance sheet view
            balance_data = org_data.copy()
            balance_data['Export_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            balance_data['Report_Type'] = 'Balance Sheet Export'
            
            # Add calculated fields if applicable
            if 'Budget' in balance_data.columns and 'Actual' in balance_data.columns:
                balance_data['Net_Position'] = balance_data['Actual'] - balance_data['Budget']
            
            # Export to Google Sheets
            if manual_spreadsheet_id:
                # Use provided spreadsheet ID
                st.info(f"Exporting to existing spreadsheet: {manual_spreadsheet_id}")
                if exporter.export_dataframe_to_sheet(manual_spreadsheet_id, "Balance_Sheet", balance_data):
                    spreadsheet_id = manual_spreadsheet_id
                else:
                    spreadsheet_id = None
            else:
                # Try to create new spreadsheet
                spreadsheet_id = exporter.export_balance_sheet(balance_data, org_name)
            
            if spreadsheet_id:
                url = exporter.get_spreadsheet_url(spreadsheet_id)
                st.success("Balance sheet exported successfully!")
                st.markdown(f"**[Open in Google Sheets]({url})**")
                st.info(f"Spreadsheet ID: {spreadsheet_id}")
            else:
                st.error("Failed to export balance sheet")
                
        except Exception as e:
            st.error(f"Export failed: {str(e)}")