"""
Google Drive Manager for Report Distribution
Phase 3: Automated report uploads and folder management

ARCHITECTURAL DECISIONS:
1. Uses Google Drive API v3 for file operations
2. Implements folder hierarchy management
3. Supports batch uploads and sharing
4. Provides graceful fallback when credentials not available
"""

import os
import json
import io
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleDriveManager:
    """Manages Google Drive integration for report distribution"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.root_folder_id = None
        self.folder_cache = {}
        self.initialize()
    
    def initialize(self):
        """Initialize Google Drive connection"""
        if not GOOGLE_AVAILABLE:
            print("Google Drive API not available. Install google-api-python-client")
            return False
        
        # Try to load credentials from environment or file
        creds_json = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
        if not creds_json:
            creds_file = "configs/google_drive_credentials.json"
            if os.path.exists(creds_file):
                with open(creds_file, 'r') as f:
                    creds_json = f.read()
        
        if creds_json:
            try:
                creds_dict = json.loads(creds_json)
                self.credentials = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                self.service = build('drive', 'v3', credentials=self.credentials)
                return True
            except Exception as e:
                print(f"Error initializing Google Drive: {e}")
                return False
        
        return False
    
    def is_available(self) -> bool:
        """Check if Google Drive service is available"""
        return self.service is not None
    
    def create_folder_hierarchy(self, folder_path: str, parent_id: Optional[str] = None) -> str:
        """
        Create folder hierarchy in Google Drive
        
        Args:
            folder_path: Path like "GovSight Reports/Vatica/2024"
            parent_id: Parent folder ID (None for root)
        
        Returns:
            Folder ID of the deepest folder
        """
        if not self.is_available():
            raise Exception("Google Drive not initialized")
        
        # Split path into components
        parts = folder_path.split('/')
        current_parent = parent_id or 'root'
        
        for part in parts:
            if not part:
                continue
            
            # Check cache first
            cache_key = f"{current_parent}/{part}"
            if cache_key in self.folder_cache:
                current_parent = self.folder_cache[cache_key]
                continue
            
            # Search for existing folder
            try:
                query = f"name='{part}' and '{current_parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name)"
                ).execute()
                
                if results.get('files'):
                    # Folder exists
                    folder_id = results['files'][0]['id']
                else:
                    # Create new folder
                    file_metadata = {
                        'name': part,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [current_parent]
                    }
                    folder = self.service.files().create(
                        body=file_metadata,
                        fields='id'
                    ).execute()
                    folder_id = folder['id']
                
                # Cache the folder ID
                self.folder_cache[cache_key] = folder_id
                current_parent = folder_id
                
            except HttpError as e:
                raise Exception(f"Error creating folder {part}: {e}")
        
        return current_parent
    
    def upload_file(self, 
                   file_path: str,
                   folder_path: str,
                   custom_name: Optional[str] = None,
                   share_with: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Local file path to upload
            folder_path: Google Drive folder path
            custom_name: Optional custom name for the file
            share_with: List of emails to share with
        
        Returns:
            Dict with file_id and web_link
        """
        if not self.is_available():
            raise Exception("Google Drive not initialized")
        
        # Create folder hierarchy
        folder_id = self.create_folder_hierarchy(folder_path)
        
        # Prepare file metadata
        file_name = custom_name or os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Determine MIME type
        mime_type = self.get_mime_type(file_path)
        
        # Upload file
        try:
            media = MediaFileUpload(file_path, mimetype=mime_type)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink')
            
            # Share file if requested
            if share_with:
                self.share_file(file_id, share_with)
            
            return {
                'file_id': file_id,
                'web_link': web_link,
                'folder_path': folder_path,
                'file_name': file_name
            }
            
        except HttpError as e:
            raise Exception(f"Error uploading file: {e}")
    
    def upload_bytes(self,
                    file_bytes: bytes,
                    file_name: str,
                    folder_path: str,
                    mime_type: str = 'application/octet-stream',
                    share_with: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Upload bytes directly to Google Drive
        
        Args:
            file_bytes: File content as bytes
            file_name: Name for the file
            folder_path: Google Drive folder path
            mime_type: MIME type of the file
            share_with: List of emails to share with
        
        Returns:
            Dict with file_id and web_link
        """
        if not self.is_available():
            raise Exception("Google Drive not initialized")
        
        # Create folder hierarchy
        folder_id = self.create_folder_hierarchy(folder_path)
        
        # Prepare file metadata
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Upload file
        try:
            media = MediaIoBaseUpload(
                io.BytesIO(file_bytes),
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            web_link = file.get('webViewLink')
            
            # Share file if requested
            if share_with:
                self.share_file(file_id, share_with)
            
            return {
                'file_id': file_id,
                'web_link': web_link,
                'folder_path': folder_path,
                'file_name': file_name
            }
            
        except HttpError as e:
            raise Exception(f"Error uploading bytes: {e}")
    
    def share_file(self, file_id: str, emails: List[str], role: str = 'reader'):
        """
        Share a file with specified emails
        
        Args:
            file_id: Google Drive file ID
            emails: List of email addresses
            role: Permission role (reader, writer, commenter)
        """
        if not self.is_available():
            return
        
        for email in emails:
            if not email or '@' not in email:
                continue
            
            try:
                permission = {
                    'type': 'user',
                    'role': role,
                    'emailAddress': email
                }
                
                self.service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    sendNotificationEmail=True
                ).execute()
                
            except HttpError as e:
                print(f"Error sharing with {email}: {e}")
    
    def list_files(self, folder_path: str, file_type: Optional[str] = None) -> List[Dict]:
        """
        List files in a folder
        
        Args:
            folder_path: Google Drive folder path
            file_type: Optional filter by MIME type
        
        Returns:
            List of file dictionaries
        """
        if not self.is_available():
            return []
        
        try:
            # Get folder ID
            folder_id = self.create_folder_hierarchy(folder_path)
            
            # Build query
            query = f"'{folder_id}' in parents and trashed=false"
            if file_type:
                query += f" and mimeType='{file_type}'"
            
            # List files
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            # Format response
            return [{
                'id': f['id'],
                'name': f['name'],
                'type': f.get('mimeType', 'unknown'),
                'modified': f.get('modifiedTime'),
                'size': f.get('size', 0),
                'link': f.get('webViewLink')
            } for f in files]
            
        except HttpError as e:
            print(f"Error listing files: {e}")
            return []
    
    def delete_file(self, file_id: str):
        """Delete a file from Google Drive"""
        if not self.is_available():
            return False
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except HttpError as e:
            print(f"Error deleting file: {e}")
            return False
    
    def get_mime_type(self, file_path: str) -> str:
        """Get MIME type for a file"""
        ext = Path(file_path).suffix.lower()
        
        mime_map = {
            '.pdf': 'application/pdf',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.html': 'text/html',
            '.txt': 'text/plain',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        
        return mime_map.get(ext, 'application/octet-stream')
    
    def create_folder_structure(self, base_folder: str, structure: str) -> Dict[str, str]:
        """
        Create a complete folder structure for reports
        
        Args:
            base_folder: Base folder name (e.g., "GovSight Reports")
            structure: Structure type ("By Module", "By Date", "By Module and Date")
        
        Returns:
            Dict mapping folder paths to folder IDs
        """
        folders = {}
        
        if structure == "By Module":
            modules = ["Vatica", "Navi", "Mantis", "Archive"]
            for module in modules:
                path = f"{base_folder}/{module}"
                folders[path] = self.create_folder_hierarchy(path)
                
        elif structure == "By Date":
            year = datetime.now().year
            months = ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"]
            for month in months:
                path = f"{base_folder}/{year}/{month}"
                folders[path] = self.create_folder_hierarchy(path)
                
        elif structure == "By Module and Date":
            modules = ["Vatica", "Navi", "Mantis"]
            year = datetime.now().year
            month = datetime.now().strftime("%B")
            
            for module in modules:
                path = f"{base_folder}/{module}/{year}/{month}"
                folders[path] = self.create_folder_hierarchy(path)
        
        return folders


# Singleton instance
_google_drive_manager = None

def get_google_drive_manager() -> GoogleDriveManager:
    """Get or create the Google Drive manager instance"""
    global _google_drive_manager
    if _google_drive_manager is None:
        _google_drive_manager = GoogleDriveManager()
    return _google_drive_manager