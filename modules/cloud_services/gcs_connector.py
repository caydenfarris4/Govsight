"""
Google Cloud Storage Connector
Provides document archiving, report storage, and backup capabilities using GCS
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, BinaryIO
from pathlib import Path
import logging

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound
from google.api_core import retry

from modules.security.secret_manager import UnifiedSecretManager

logger = logging.getLogger(__name__)


class GCSConnector:
    """
    Production-ready Google Cloud Storage connector with:
    - Automatic authentication via UnifiedSecretManager
    - Bucket management and file operations
    - Versioning and lifecycle management
    - Secure file upload/download
    - Metadata tracking
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize GCS connector with deferred client creation for graceful degradation.
        The client is only created on first use, allowing the application to start
        without GCP configuration.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
        """
        secret_manager = UnifiedSecretManager()
        
        # Store project ID without raising error - allows graceful degradation
        self.project_id = project_id or secret_manager.get_secret("GOOGLE_CLOUD_PROJECT")
        
        # Defer client creation until first use
        self._client = None
        self._client_error = None
    
    def is_configured(self) -> bool:
        """Check if GCP is properly configured"""
        return self.project_id is not None
    
    def _get_client(self) -> Optional[storage.Client]:
        """
        Lazily initialize GCS client on first use.
        Returns None if GCP is not configured, allowing graceful degradation.
        """
        # Return cached client if available
        if self._client is not None:
            return self._client
        
        # Return None if previous initialization failed
        if self._client_error is not None:
            return None
        
        # Check if project ID is configured
        if not self.project_id:
            self._client_error = "GCP project ID not configured. Set GOOGLE_CLOUD_PROJECT environment variable."
            logger.warning(self._client_error)
            return None
        
        # Initialize GCS client with Application Default Credentials
        try:
            self._client = storage.Client(project=self.project_id)
            logger.info(f"GCS connector initialized for project: {self.project_id}")
            return self._client
        except Exception as e:
            self._client_error = f"Failed to initialize GCS client: {e}"
            logger.error(self._client_error)
            return None
    
    def get_config_error(self) -> Optional[str]:
        """Get configuration error message if GCP is not properly configured"""
        if not self.project_id:
            return "GCP not configured. Set GOOGLE_CLOUD_PROJECT environment variable."
        return self._client_error
    
    def create_bucket(self, bucket_name: str, location: str = "US",
                     storage_class: str = "STANDARD",
                     versioning_enabled: bool = True,
                     lifecycle_rules: Optional[List[Dict]] = None) -> Optional[storage.Bucket]:
        """
        Create a new GCS bucket with versioning and lifecycle policies
        
        Args:
            bucket_name: Unique bucket name
            location: Bucket location (US, EU, asia-east1, etc.)
            storage_class: STANDARD, NEARLINE, COLDLINE, or ARCHIVE
            versioning_enabled: Enable object versioning
            lifecycle_rules: Optional lifecycle management rules
            
        Returns:
            Created bucket object, or None if GCP not configured
        """
        client = self._get_client()
        if not client:
            logger.warning(f"Cannot create bucket {bucket_name}: {self.get_config_error()}")
            return None
        
        try:
            bucket = client.bucket(bucket_name)
            
            # Check if bucket already exists
            if bucket.exists():
                logger.info(f"Bucket {bucket_name} already exists")
                return bucket
            
            # Create bucket with specified configuration
            bucket = client.create_bucket(
                bucket_name,
                location=location
            )
            
            # Set storage class
            bucket.storage_class = storage_class
            
            # Enable versioning if requested
            if versioning_enabled:
                bucket.versioning_enabled = True
            
            # Apply lifecycle rules if provided
            if lifecycle_rules:
                bucket.lifecycle_rules = lifecycle_rules
            
            bucket.patch()
            
            logger.info(f"Created bucket: {bucket_name} in {location}")
            return bucket
            
        except GoogleCloudError as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            raise
    
    def get_bucket(self, bucket_name: str) -> Optional[storage.Bucket]:
        """Get bucket by name, returns None if GCP not configured"""
        client = self._get_client()
        if not client:
            return None
        
        try:
            bucket = client.bucket(bucket_name)
            if bucket.exists():
                return bucket
            return None
        except Exception as e:
            logger.error(f"Failed to get bucket {bucket_name}: {e}")
            return None
    
    def list_buckets(self) -> List[storage.Bucket]:
        """List all buckets in the project, returns empty list if GCP not configured"""
        client = self._get_client()
        if not client:
            return []
        
        try:
            buckets = list(client.list_buckets())
            logger.info(f"Found {len(buckets)} buckets")
            return buckets
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            return []
    
    def upload_file(self, bucket_name: str, source_file_path: str,
                   destination_blob_name: Optional[str] = None,
                   metadata: Optional[Dict[str, str]] = None,
                   content_type: Optional[str] = None) -> Optional[storage.Blob]:
        """
        Upload file to GCS bucket
        
        Args:
            bucket_name: Target bucket name
            source_file_path: Local file path to upload
            destination_blob_name: Destination path in bucket (defaults to filename)
            metadata: Optional custom metadata
            content_type: Optional content type (auto-detected if not provided)
            
        Returns:
            Uploaded blob object or None if failed
        """
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                raise ValueError(f"Bucket {bucket_name} not found")
            
            # Use filename as destination if not specified
            if not destination_blob_name:
                destination_blob_name = os.path.basename(source_file_path)
            
            blob = bucket.blob(destination_blob_name)
            
            # Set metadata if provided
            if metadata:
                blob.metadata = metadata
            
            # Upload file with retry logic
            blob.upload_from_filename(
                source_file_path,
                content_type=content_type,
                retry=retry.Retry(deadline=300)
            )
            
            logger.info(f"Uploaded {source_file_path} to gs://{bucket_name}/{destination_blob_name}")
            return blob
            
        except Exception as e:
            logger.error(f"Failed to upload file to {bucket_name}: {e}")
            return None
    
    def upload_from_string(self, bucket_name: str, content: str,
                          destination_blob_name: str,
                          metadata: Optional[Dict[str, str]] = None,
                          content_type: str = "text/plain") -> Optional[storage.Blob]:
        """
        Upload string content to GCS
        
        Args:
            bucket_name: Target bucket name
            content: String content to upload
            destination_blob_name: Destination path in bucket
            metadata: Optional custom metadata
            content_type: Content type (default: text/plain)
            
        Returns:
            Uploaded blob object or None if failed
        """
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                raise ValueError(f"Bucket {bucket_name} not found")
            
            blob = bucket.blob(destination_blob_name)
            
            if metadata:
                blob.metadata = metadata
            
            blob.upload_from_string(
                content,
                content_type=content_type,
                retry=retry.Retry(deadline=300)
            )
            
            logger.info(f"Uploaded string content to gs://{bucket_name}/{destination_blob_name}")
            return blob
            
        except Exception as e:
            logger.error(f"Failed to upload string to {bucket_name}: {e}")
            return None
    
    def download_file(self, bucket_name: str, source_blob_name: str,
                     destination_file_path: str) -> bool:
        """
        Download file from GCS bucket
        
        Args:
            bucket_name: Source bucket name
            source_blob_name: Blob name in bucket
            destination_file_path: Local path to save file
            
        Returns:
            Success status
        """
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                raise ValueError(f"Bucket {bucket_name} not found")
            
            blob = bucket.blob(source_blob_name)
            
            # Create parent directories if needed
            os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
            
            blob.download_to_filename(
                destination_file_path,
                retry=retry.Retry(deadline=300)
            )
            
            logger.info(f"Downloaded gs://{bucket_name}/{source_blob_name} to {destination_file_path}")
            return True
            
        except NotFound:
            logger.error(f"Blob {source_blob_name} not found in bucket {bucket_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to download file from {bucket_name}: {e}")
            return False
    
    def download_as_string(self, bucket_name: str, blob_name: str) -> Optional[str]:
        """Download blob content as string"""
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                return None
            
            blob = bucket.blob(blob_name)
            content = blob.download_as_text(retry=retry.Retry(deadline=300))
            
            logger.info(f"Downloaded gs://{bucket_name}/{blob_name} as string")
            return content
            
        except Exception as e:
            logger.error(f"Failed to download string from {bucket_name}: {e}")
            return None
    
    def list_blobs(self, bucket_name: str, prefix: Optional[str] = None,
                  delimiter: Optional[str] = None) -> List[storage.Blob]:
        """
        List blobs in bucket
        
        Args:
            bucket_name: Bucket name
            prefix: Optional prefix filter
            delimiter: Optional delimiter for directory-like listing
            
        Returns:
            List of blob objects
        """
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                return []
            
            blobs = list(bucket.list_blobs(prefix=prefix, delimiter=delimiter))
            logger.info(f"Found {len(blobs)} blobs in {bucket_name}")
            return blobs
            
        except Exception as e:
            logger.error(f"Failed to list blobs in {bucket_name}: {e}")
            return []
    
    def delete_blob(self, bucket_name: str, blob_name: str) -> bool:
        """Delete blob from bucket"""
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                return False
            
            blob = bucket.blob(blob_name)
            blob.delete()
            
            logger.info(f"Deleted gs://{bucket_name}/{blob_name}")
            return True
            
        except NotFound:
            logger.warning(f"Blob {blob_name} not found in bucket {bucket_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}")
            return False
    
    def get_blob_metadata(self, bucket_name: str, blob_name: str) -> Optional[Dict[str, Any]]:
        """Get blob metadata and properties"""
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                return None
            
            blob = bucket.blob(blob_name)
            blob.reload()
            
            metadata = {
                "name": blob.name,
                "bucket": blob.bucket.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "generation": blob.generation,
                "metageneration": blob.metageneration,
                "etag": blob.etag,
                "md5_hash": blob.md5_hash,
                "crc32c": blob.crc32c,
                "custom_metadata": blob.metadata or {}
            }
            
            return metadata
            
        except NotFound:
            logger.error(f"Blob {blob_name} not found in bucket {bucket_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get metadata for {blob_name}: {e}")
            return None
    
    def generate_signed_url(self, bucket_name: str, blob_name: str,
                           expiration_minutes: int = 60,
                           method: str = "GET") -> Optional[str]:
        """
        Generate signed URL for temporary access to blob
        
        Args:
            bucket_name: Bucket name
            blob_name: Blob name
            expiration_minutes: URL validity duration
            method: HTTP method (GET, PUT, etc.)
            
        Returns:
            Signed URL or None if failed
        """
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                return None
            
            blob = bucket.blob(blob_name)
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method=method
            )
            
            logger.info(f"Generated signed URL for gs://{bucket_name}/{blob_name}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None
    
    def copy_blob(self, source_bucket: str, source_blob: str,
                 dest_bucket: str, dest_blob: str) -> bool:
        """Copy blob between buckets"""
        try:
            src_bucket = self.get_bucket(source_bucket)
            dst_bucket = self.get_bucket(dest_bucket)
            
            if not src_bucket or not dst_bucket:
                return False
            
            source_blob_obj = src_bucket.blob(source_blob)
            src_bucket.copy_blob(source_blob_obj, dst_bucket, dest_blob)
            
            logger.info(f"Copied gs://{source_bucket}/{source_blob} to gs://{dest_bucket}/{dest_blob}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy blob: {e}")
            return False
    
    def setup_lifecycle_policy(self, bucket_name: str, 
                              delete_after_days: Optional[int] = None,
                              archive_after_days: Optional[int] = None) -> bool:
        """
        Configure lifecycle management for bucket
        
        Args:
            bucket_name: Bucket name
            delete_after_days: Delete objects after N days
            archive_after_days: Move to ARCHIVE storage after N days
            
        Returns:
            Success status
        """
        try:
            bucket = self.get_bucket(bucket_name)
            if not bucket:
                return False
            
            rules = []
            
            if delete_after_days:
                rules.append({
                    "action": {"type": "Delete"},
                    "condition": {"age": delete_after_days}
                })
            
            if archive_after_days:
                rules.append({
                    "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
                    "condition": {"age": archive_after_days}
                })
            
            bucket.lifecycle_rules = rules
            bucket.patch()
            
            logger.info(f"Updated lifecycle policy for {bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update lifecycle policy: {e}")
            return False


# Convenience functions for document archiving
def archive_document(file_path: str, archive_type: str = "reports",
                    project_id: Optional[str] = None) -> Optional[str]:
    """
    Archive document to GCS with standard naming convention
    
    Args:
        file_path: Local file path
        archive_type: Category (reports, exports, backups, etc.)
        project_id: Optional GCP project ID
        
    Returns:
        GCS URI (gs://bucket/path) or None if failed
    """
    try:
        connector = GCSConnector(project_id=project_id)
        
        # Standard bucket naming: govsight-{archive_type}
        bucket_name = f"govsight-{archive_type}"
        
        # Ensure bucket exists
        bucket = connector.get_bucket(bucket_name)
        if not bucket:
            bucket = connector.create_bucket(
                bucket_name,
                versioning_enabled=True,
                lifecycle_rules=[
                    {"action": {"type": "Delete"}, "condition": {"age": 365}}  # 1 year retention
                ]
            )
        
        # Upload with timestamp in path
        timestamp = datetime.now().strftime("%Y/%m/%d")
        filename = os.path.basename(file_path)
        destination = f"{timestamp}/{filename}"
        
        metadata = {
            "upload_time": datetime.now().isoformat(),
            "source_system": "govsight",
            "archive_type": archive_type
        }
        
        blob = connector.upload_file(bucket_name, file_path, destination, metadata=metadata)
        
        if blob:
            return f"gs://{bucket_name}/{destination}"
        return None
        
    except Exception as e:
        logger.error(f"Failed to archive document: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    connector = GCSConnector()
    print(f"GCS Connector initialized for project: {connector.project_id}")
    
    # List buckets
    buckets = connector.list_buckets()
    print(f"Found {len(buckets)} buckets")
