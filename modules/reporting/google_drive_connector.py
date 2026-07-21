"""
Google Drive Connector using Replit Integration
Phase 3: Uses the native Replit Google Drive connection

ARCHITECTURAL DECISIONS:
1. Leverages Replit's OAuth integration for secure authentication
2. No manual credential management needed
3. Automatic token refresh handled by Replit
4. Python wrapper for the JavaScript integration
"""

import os
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class GoogleDriveConnector:
    """Google Drive connector using Replit's native integration"""
    
    def __init__(self):
        self.connected = False
        self.check_connection()
    
    def check_connection(self) -> bool:
        """Check if Google Drive is connected via Replit"""
        try:
            # Check for Replit environment variables
            if os.environ.get('REPLIT_CONNECTORS_HOSTNAME'):
                self.connected = True
                return True
        except Exception as e:
            print(f"Google Drive connection check failed: {e}")
        
        self.connected = False
        return False
    
    def upload_file(self, 
                   file_path: str,
                   folder_name: str = "GovSight Reports",
                   custom_name: Optional[str] = None) -> Dict[str, str]:
        """
        Upload a file to Google Drive using Replit connection
        
        Args:
            file_path: Local file path to upload
            folder_name: Google Drive folder name
            custom_name: Optional custom name for the file
        
        Returns:
            Dict with file_id and status
        """
        if not self.connected:
            return {"status": "error", "message": "Google Drive not connected"}
        
        try:
            # Create a Node.js script to handle the upload
            script_content = f"""
const {{ google }} = require('googleapis');
const fs = require('fs');
const path = require('path');

async function getAccessToken() {{
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  const xReplitToken = process.env.REPL_IDENTITY 
    ? 'repl ' + process.env.REPL_IDENTITY 
    : process.env.WEB_REPL_RENEWAL 
    ? 'depl ' + process.env.WEB_REPL_RENEWAL 
    : null;

  if (!xReplitToken) {{
    throw new Error('X_REPLIT_TOKEN not found');
  }}

  const response = await fetch(
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=google-drive',
    {{
      headers: {{
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }}
    }}
  );
  
  const data = await response.json();
  const connectionSettings = data.items?.[0];
  const accessToken = connectionSettings?.settings?.access_token || 
                      connectionSettings?.settings?.oauth?.credentials?.access_token;

  if (!accessToken) {{
    throw new Error('Google Drive not connected');
  }}
  
  return accessToken;
}}

async function uploadFile() {{
  const accessToken = await getAccessToken();
  
  const oauth2Client = new google.auth.OAuth2();
  oauth2Client.setCredentials({{
    access_token: accessToken
  }});
  
  const drive = google.drive({{ version: 'v3', auth: oauth2Client }});
  
  // Create folder if it doesn't exist
  const folderName = '{folder_name}';
  let folderId = 'root';
  
  try {{
    const folderResponse = await drive.files.list({{
      q: `name='${{folderName}}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
      fields: 'files(id, name)'
    }});
    
    if (folderResponse.data.files.length > 0) {{
      folderId = folderResponse.data.files[0].id;
    }} else {{
      const createResponse = await drive.files.create({{
        requestBody: {{
          name: folderName,
          mimeType: 'application/vnd.google-apps.folder'
        }},
        fields: 'id'
      }});
      folderId = createResponse.data.id;
    }}
  }} catch (err) {{
    console.error('Folder creation error:', err);
  }}
  
  // Upload file
  const filePath = '{file_path}';
  const fileName = '{custom_name or os.path.basename(file_path)}';
  
  const fileMetadata = {{
    name: fileName,
    parents: [folderId]
  }};
  
  const media = {{
    mimeType: 'application/octet-stream',
    body: fs.createReadStream(filePath)
  }};
  
  const response = await drive.files.create({{
    requestBody: fileMetadata,
    media: media,
    fields: 'id, name, webViewLink'
  }});
  
  console.log(JSON.stringify({{
    status: 'success',
    fileId: response.data.id,
    fileName: response.data.name,
    webLink: response.data.webViewLink
  }}));
}}

uploadFile().catch(err => {{
  console.log(JSON.stringify({{
    status: 'error',
    message: err.message
  }}));
}});
"""
            
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            # Execute the Node.js script
            result = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up temporary file
            os.unlink(script_path)
            
            # Parse result
            if result.stdout:
                return json.loads(result.stdout)
            else:
                return {"status": "error", "message": result.stderr or "Upload failed"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def list_files(self, folder_name: str = "GovSight Reports") -> List[Dict]:
        """
        List files in a Google Drive folder
        
        Args:
            folder_name: Name of the folder to list
        
        Returns:
            List of file dictionaries
        """
        if not self.connected:
            return []
        
        try:
            # Create a Node.js script to list files
            script_content = f"""
const {{ google }} = require('googleapis');

async function getAccessToken() {{
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  const xReplitToken = process.env.REPL_IDENTITY 
    ? 'repl ' + process.env.REPL_IDENTITY 
    : process.env.WEB_REPL_RENEWAL 
    ? 'depl ' + process.env.WEB_REPL_RENEWAL 
    : null;

  if (!xReplitToken) {{
    throw new Error('X_REPLIT_TOKEN not found');
  }}

  const response = await fetch(
    'https://' + hostname + '/api/v2/connection?include_secrets=true&connector_names=google-drive',
    {{
      headers: {{
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': xReplitToken
      }}
    }}
  );
  
  const data = await response.json();
  const connectionSettings = data.items?.[0];
  const accessToken = connectionSettings?.settings?.access_token || 
                      connectionSettings?.settings?.oauth?.credentials?.access_token;

  if (!accessToken) {{
    throw new Error('Google Drive not connected');
  }}
  
  return accessToken;
}}

async function listFiles() {{
  const accessToken = await getAccessToken();
  
  const oauth2Client = new google.auth.OAuth2();
  oauth2Client.setCredentials({{
    access_token: accessToken
  }});
  
  const drive = google.drive({{ version: 'v3', auth: oauth2Client }});
  
  // Find folder
  const folderName = '{folder_name}';
  const folderResponse = await drive.files.list({{
    q: `name='${{folderName}}' and mimeType='application/vnd.google-apps.folder' and trashed=false`,
    fields: 'files(id, name)'
  }});
  
  if (folderResponse.data.files.length === 0) {{
    console.log(JSON.stringify([]));
    return;
  }}
  
  const folderId = folderResponse.data.files[0].id;
  
  // List files in folder
  const response = await drive.files.list({{
    q: `'${{folderId}}' in parents and trashed=false`,
    fields: 'files(id, name, mimeType, modifiedTime, size, webViewLink)',
    orderBy: 'modifiedTime desc'
  }});
  
  const files = response.data.files.map(file => ({{
    id: file.id,
    name: file.name,
    type: file.mimeType,
    modified: file.modifiedTime,
    size: file.size || 0,
    link: file.webViewLink
  }}));
  
  console.log(JSON.stringify(files));
}}

listFiles().catch(err => {{
  console.log(JSON.stringify([]));
}});
"""
            
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            # Execute the Node.js script
            result = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up temporary file
            os.unlink(script_path)
            
            # Parse result
            if result.stdout:
                return json.loads(result.stdout)
            else:
                return []
                
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def create_folder_structure(self, base_folder: str = "GovSight Reports") -> bool:
        """
        Create the standard folder structure for reports
        
        Args:
            base_folder: Base folder name
        
        Returns:
            True if successful
        """
        folders = [
            f"{base_folder}/Vatica",
            f"{base_folder}/Navi", 
            f"{base_folder}/Mantis",
            f"{base_folder}/Scheduled",
            f"{base_folder}/Archive"
        ]
        
        # For now, folders will be created automatically when uploading files
        # This is a placeholder for future enhancement
        return True
    
    def is_available(self) -> bool:
        """Check if Google Drive service is available"""
        return self.connected


# Singleton instance
_google_drive_connector = None

def get_google_drive_connector() -> GoogleDriveConnector:
    """Get or create the Google Drive connector instance"""
    global _google_drive_connector
    if _google_drive_connector is None:
        _google_drive_connector = GoogleDriveConnector()
    return _google_drive_connector