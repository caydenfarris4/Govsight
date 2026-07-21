#!/usr/bin/env python3
"""
Test script to verify Google Sheets credentials and API connection
"""
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def test_credentials():
    print("Testing Google Sheets API credentials...")
    
    # Check if environment variable exists
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        print("❌ GOOGLE_SHEETS_CREDENTIALS environment variable not found")
        return False
    
    print("✓ GOOGLE_SHEETS_CREDENTIALS environment variable found")
    
    # Try to parse JSON
    try:
        credentials_info = json.loads(creds_json)
        print("✓ JSON credentials parsed successfully")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    
    # Check required fields
    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
    missing_fields = [field for field in required_fields if field not in credentials_info]
    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        return False
    
    print("✓ All required credential fields present")
    
    # Try to create credentials object
    try:
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        print("✓ Credentials object created successfully")
    except Exception as e:
        print(f"❌ Failed to create credentials: {e}")
        return False
    
    # Try to build the service
    try:
        service = build('sheets', 'v4', credentials=credentials)
        print("✓ Google Sheets API service built successfully")
    except Exception as e:
        print(f"❌ Failed to build API service: {e}")
        return False
    
    # Try to create a test spreadsheet
    try:
        spreadsheet = {
            'properties': {
                'title': 'GovSight Test - Connection Verification'
            }
        }
        result = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = result.get('spreadsheetId')
        print(f"✓ Test spreadsheet created successfully: {spreadsheet_id}")
        print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
        
        # Clean up - delete the test spreadsheet
        try:
            # Note: Can't delete via API, but this confirms write access works
            print("✓ API has write permissions (test spreadsheet remains for manual cleanup)")
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test spreadsheet: {e}")
        print("This might be a permissions issue or network connectivity problem")
        return False

if __name__ == "__main__":
    success = test_credentials()
    if success:
        print("\n🎉 Google Sheets integration is working correctly!")
    else:
        print("\n❌ Google Sheets integration needs attention")