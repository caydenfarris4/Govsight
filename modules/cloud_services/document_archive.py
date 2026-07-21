"""
Document Archive System
Provides enterprise document archiving using Google Cloud Storage
Integrates with Vatica reports, CSV exports, and database backups
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from .gcs_connector import GCSConnector

logger = logging.getLogger(__name__)


class DocumentArchive:
    """
    Enterprise document archiving system with:
    - Automatic classification (reports, exports, backups)
    - Versioning and retention policies
    - Search and retrieval
    - Integration with existing GovSight modules
    """
    
    # Standard bucket configuration
    ARCHIVE_BUCKETS = {
        "reports": {
            "name": "govsight-reports",
            "retention_days": 2555,  # 7 years for financial reports
            "archive_days": 365,  # Move to cold storage after 1 year
            "versioning": True
        },
        "exports": {
            "name": "govsight-exports",
            "retention_days": 1095,  # 3 years for CSV exports
            "archive_days": 180,  # Move to cold storage after 6 months
            "versioning": True
        },
        "backups": {
            "name": "govsight-backups",
            "retention_days": 90,  # 90 days for database backups
            "archive_days": 30,  # Move to cold storage after 30 days
            "versioning": True
        },
        "documents": {
            "name": "govsight-documents",
            "retention_days": 2555,  # 7 years for general documents
            "archive_days": 365,
            "versioning": True
        }
    }
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize document archive with GCS connector
        
        Args:
            project_id: Optional GCP project ID
        """
        self.connector = GCSConnector(project_id=project_id)
        self._ensure_buckets_exist()
    
    def _ensure_buckets_exist(self):
        """
        Ensure all standard archive buckets exist with proper configuration.
        Short-circuits if GCP is not configured to support graceful degradation.
        """
        # Skip bucket creation if GCP not configured - graceful degradation
        if not self.connector.is_configured():
            logger.info("GCP not configured - skipping bucket initialization")
            return
        
        for archive_type, config in self.ARCHIVE_BUCKETS.items():
            try:
                bucket = self.connector.get_bucket(config["name"])
                
                if not bucket:
                    # Create bucket with lifecycle rules
                    lifecycle_rules = []
                    
                    # Add archive rule
                    if config.get("archive_days"):
                        lifecycle_rules.append({
                            "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
                            "condition": {"age": config["archive_days"]}
                        })
                    
                    # Add deletion rule
                    if config.get("retention_days"):
                        lifecycle_rules.append({
                            "action": {"type": "Delete"},
                            "condition": {"age": config["retention_days"]}
                        })
                    
                    bucket = self.connector.create_bucket(
                        config["name"],
                        versioning_enabled=config.get("versioning", True),
                        lifecycle_rules=lifecycle_rules
                    )
                    
                    if bucket:
                        logger.info(f"Created archive bucket: {config['name']}")
                
            except Exception as e:
                logger.error(f"Failed to ensure bucket {config['name']}: {e}")
    
    def archive_report(self, report_path: str, 
                      report_type: str,
                      metadata: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Archive financial report to GCS
        
        Args:
            report_path: Local path to report file (PDF, XLSX, etc.)
            report_type: Type of report (budget, balance_sheet, gl_analysis, etc.)
            metadata: Optional custom metadata
            
        Returns:
            GCS URI or None if failed
        """
        # Check if GCP is configured - graceful degradation
        if not self.connector.is_configured():
            logger.warning(f"Cannot archive report - GCP not configured: {self.connector.get_config_error()}")
            return None
        
        try:
            if not os.path.exists(report_path):
                logger.error(f"Report file not found: {report_path}")
                return None
            
            bucket_name = self.ARCHIVE_BUCKETS["reports"]["name"]
            
            # Create organized path: YYYY/MM/type/filename
            timestamp = datetime.now()
            filename = os.path.basename(report_path)
            destination = f"{timestamp.year}/{timestamp.month:02d}/{report_type}/{filename}"
            
            # Prepare metadata
            archive_metadata = {
                "archive_time": timestamp.isoformat(),
                "report_type": report_type,
                "source_system": "govsight-vatica",
                "file_extension": Path(report_path).suffix
            }
            
            if metadata:
                archive_metadata.update(metadata)
            
            # Upload to GCS
            blob = self.connector.upload_file(
                bucket_name,
                report_path,
                destination,
                metadata=archive_metadata
            )
            
            if blob:
                uri = f"gs://{bucket_name}/{destination}"
                logger.info(f"Archived report: {uri}")
                return uri
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to archive report: {e}")
            return None
    
    def archive_csv_export(self, csv_path: str,
                          export_type: str,
                          metadata: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Archive CSV export to GCS
        
        Args:
            csv_path: Local path to CSV file
            export_type: Type of export (gl_accounts, transactions, departments, etc.)
            metadata: Optional custom metadata
            
        Returns:
            GCS URI or None if failed
        """
        # Check if GCP is configured - graceful degradation
        if not self.connector.is_configured():
            logger.warning(f"Cannot archive CSV export - GCP not configured: {self.connector.get_config_error()}")
            return None
        
        try:
            if not os.path.exists(csv_path):
                logger.error(f"CSV file not found: {csv_path}")
                return None
            
            bucket_name = self.ARCHIVE_BUCKETS["exports"]["name"]
            
            # Create organized path: YYYY/MM/type/filename
            timestamp = datetime.now()
            filename = os.path.basename(csv_path)
            destination = f"{timestamp.year}/{timestamp.month:02d}/{export_type}/{filename}"
            
            # Prepare metadata
            archive_metadata = {
                "archive_time": timestamp.isoformat(),
                "export_type": export_type,
                "source_system": "govsight-vatica",
                "format": "csv"
            }
            
            if metadata:
                archive_metadata.update(metadata)
            
            # Upload to GCS
            blob = self.connector.upload_file(
                bucket_name,
                csv_path,
                destination,
                metadata=archive_metadata,
                content_type="text/csv"
            )
            
            if blob:
                uri = f"gs://{bucket_name}/{destination}"
                logger.info(f"Archived CSV export: {uri}")
                return uri
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to archive CSV: {e}")
            return None
    
    def archive_database_backup(self, backup_path: str,
                               database_name: str,
                               metadata: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Archive database backup to GCS
        
        Args:
            backup_path: Local path to backup file
            database_name: Name of database (caselle_gl0, payroll, etc.)
            metadata: Optional custom metadata
            
        Returns:
            GCS URI or None if failed
        """
        # Check if GCP is configured - graceful degradation
        if not self.connector.is_configured():
            logger.warning(f"Cannot archive database backup - GCP not configured: {self.connector.get_config_error()}")
            return None
        
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return None
            
            bucket_name = self.ARCHIVE_BUCKETS["backups"]["name"]
            
            # Create organized path: YYYY/MM/DD/database/filename
            timestamp = datetime.now()
            filename = os.path.basename(backup_path)
            destination = f"{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/{database_name}/{filename}"
            
            # Prepare metadata
            archive_metadata = {
                "archive_time": timestamp.isoformat(),
                "database_name": database_name,
                "backup_type": "full",  # Can be extended for incremental
                "source_system": "govsight-backup-manager"
            }
            
            if metadata:
                archive_metadata.update(metadata)
            
            # Upload to GCS
            blob = self.connector.upload_file(
                bucket_name,
                backup_path,
                destination,
                metadata=archive_metadata,
                content_type="application/x-sqlite3"
            )
            
            if blob:
                uri = f"gs://{bucket_name}/{destination}"
                logger.info(f"Archived database backup: {uri}")
                return uri
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to archive backup: {e}")
            return None
    
    def search_archives(self, archive_type: str,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       filter_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search archived documents
        
        Args:
            archive_type: Type (reports, exports, backups, documents)
            start_date: Optional start date filter
            end_date: Optional end date filter
            filter_prefix: Optional path prefix filter
            
        Returns:
            List of matching documents with metadata
        """
        # Check if GCP is configured - graceful degradation
        if not self.connector.is_configured():
            logger.warning(f"Cannot search archives - GCP not configured: {self.connector.get_config_error()}")
            return []
        
        try:
            if archive_type not in self.ARCHIVE_BUCKETS:
                logger.error(f"Invalid archive type: {archive_type}")
                return []
            
            bucket_name = self.ARCHIVE_BUCKETS[archive_type]["name"]
            
            # Build prefix for date-based filtering
            prefix = filter_prefix
            if start_date and not prefix:
                prefix = f"{start_date.year}/"
            
            # List blobs
            blobs = self.connector.list_blobs(bucket_name, prefix=prefix)
            
            # Filter and collect metadata
            results = []
            for blob in blobs:
                # Get blob metadata
                metadata = self.connector.get_blob_metadata(bucket_name, blob.name)
                
                if metadata:
                    # Date filtering
                    if start_date or end_date:
                        created = datetime.fromisoformat(metadata["created"])
                        
                        if start_date and created < start_date:
                            continue
                        if end_date and created > end_date:
                            continue
                    
                    results.append(metadata)
            
            logger.info(f"Found {len(results)} documents in {archive_type}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search archives: {e}")
            return []
    
    def retrieve_document(self, archive_type: str, blob_name: str,
                         local_path: Optional[str] = None) -> Optional[str]:
        """
        Retrieve archived document
        
        Args:
            archive_type: Type (reports, exports, backups, documents)
            blob_name: Name of blob in bucket
            local_path: Optional local path to save (temp file if not specified)
            
        Returns:
            Local file path or None if failed
        """
        # Check if GCP is configured - graceful degradation
        if not self.connector.is_configured():
            logger.warning(f"Cannot retrieve document - GCP not configured: {self.connector.get_config_error()}")
            return None
        
        try:
            if archive_type not in self.ARCHIVE_BUCKETS:
                logger.error(f"Invalid archive type: {archive_type}")
                return None
            
            bucket_name = self.ARCHIVE_BUCKETS[archive_type]["name"]
            
            # Determine local path
            if not local_path:
                # Create temp file
                temp_dir = "temp_downloads"
                os.makedirs(temp_dir, exist_ok=True)
                local_path = os.path.join(temp_dir, os.path.basename(blob_name))
            
            # Download from GCS
            success = self.connector.download_file(bucket_name, blob_name, local_path)
            
            if success:
                logger.info(f"Retrieved document to {local_path}")
                return local_path
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            return None
    
    def get_archive_statistics(self) -> Dict[str, Any]:
        """Get statistics for all archive buckets"""
        # Check if GCP is configured - graceful degradation
        if not self.connector.is_configured():
            logger.warning(f"Cannot get archive statistics - GCP not configured: {self.connector.get_config_error()}")
            # Return empty statistics with default values
            return {
                archive_type: {
                    "bucket": config["name"],
                    "document_count": 0,
                    "total_size_mb": 0.0,
                    "retention_days": config["retention_days"],
                    "archive_days": config.get("archive_days", 0)
                }
                for archive_type, config in self.ARCHIVE_BUCKETS.items()
            }
        
        stats = {}
        
        for archive_type, config in self.ARCHIVE_BUCKETS.items():
            try:
                bucket_name = config["name"]
                blobs = self.connector.list_blobs(bucket_name)
                
                total_size = sum(blob.size for blob in blobs if blob.size)
                
                stats[archive_type] = {
                    "bucket": bucket_name,
                    "document_count": len(blobs),
                    "total_size_mb": total_size / (1024 * 1024) if total_size else 0,
                    "retention_days": config["retention_days"],
                    "archive_days": config.get("archive_days", 0)
                }
                
            except Exception as e:
                logger.error(f"Failed to get stats for {archive_type}: {e}")
                stats[archive_type] = {"error": str(e)}
        
        return stats
    
    def generate_access_url(self, archive_type: str, blob_name: str,
                           expiration_minutes: int = 60) -> Optional[str]:
        """
        Generate temporary signed URL for document access
        
        Args:
            archive_type: Type (reports, exports, backups, documents)
            blob_name: Name of blob in bucket
            expiration_minutes: URL validity duration
            
        Returns:
            Signed URL or None if failed
        """
        # Check if GCP is configured - graceful degradation
        if not self.connector.is_configured():
            logger.warning(f"Cannot generate access URL - GCP not configured: {self.connector.get_config_error()}")
            return None
        
        try:
            if archive_type not in self.ARCHIVE_BUCKETS:
                return None
            
            bucket_name = self.ARCHIVE_BUCKETS[archive_type]["name"]
            
            url = self.connector.generate_signed_url(
                bucket_name,
                blob_name,
                expiration_minutes=expiration_minutes
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate access URL: {e}")
            return None


if __name__ == "__main__":
    # Example usage
    archive = DocumentArchive()
    stats = archive.get_archive_statistics()
    
    print("Archive Statistics:")
    for archive_type, stat in stats.items():
        print(f"\n{archive_type.upper()}:")
        print(f"  Documents: {stat.get('document_count', 'N/A')}")
        print(f"  Total Size: {stat.get('total_size_mb', 0):.2f} MB")
