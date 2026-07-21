"""
Automated Database Backup System
Provides point-in-time recovery, incremental backups, and disaster recovery
"""

import os
import shutil
import sqlite3
import json
import hashlib
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Production-ready database backup system with:
    - Full and incremental backups
    - Point-in-time recovery
    - Compression
    - Integrity verification
    - Retention policies
    - Backup rotation
    """
    
    def __init__(self, backup_root: str = None, retention_days: int = 30):
        """
        Initialize backup manager
        
        Args:
            backup_root: Root directory for backups
            retention_days: Days to retain backups
        """
        self.backup_root = backup_root or "backups"
        self.retention_days = retention_days
        self.manifest_file = os.path.join(self.backup_root, "backup_manifest.json")
        
        # Ensure backup directory exists
        os.makedirs(self.backup_root, exist_ok=True)
        
        # Load or initialize manifest
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load backup manifest tracking all backups"""
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load manifest: {e}")
                return {"backups": [], "metadata": {}}
        
        return {"backups": [], "metadata": {}}
    
    def _save_manifest(self):
        """Save backup manifest"""
        try:
            with open(self.manifest_file, 'w') as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
    
    def create_backup(self, database_path: str, backup_type: str = "full",
                     compress: bool = True, verify: bool = True) -> Dict[str, Any]:
        """
        Create a database backup
        
        Args:
            database_path: Path to database to backup
            backup_type: 'full' or 'incremental'
            compress: Whether to compress the backup
            verify: Whether to verify backup integrity
            
        Returns:
            Dictionary with backup metadata
        """
        if not os.path.exists(database_path):
            raise FileNotFoundError(f"Database not found: {database_path}")
        
        # Generate backup metadata
        db_name = os.path.basename(database_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_id = hashlib.md5(f"{db_name}_{timestamp}".encode()).hexdigest()[:12]
        
        backup_dir = os.path.join(self.backup_root, db_name.replace('.db', ''))
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_filename = f"{db_name.replace('.db', '')}_{backup_type}_{timestamp}.db"
        if compress:
            backup_filename += ".gz"
        
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            # Create backup using SQLite backup API (safe for active databases)
            if backup_type == "full":
                self._create_full_backup(database_path, backup_path, compress)
            else:
                self._create_incremental_backup(database_path, backup_path, compress)
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            
            # Verify if requested
            if verify:
                is_valid = self._verify_backup(backup_path, compress)
                if not is_valid:
                    raise ValueError("Backup verification failed")
            
            # Get file size
            file_size = os.path.getsize(backup_path)
            
            # Record in manifest
            backup_record = {
                "backup_id": backup_id,
                "database_name": db_name,
                "database_path": database_path,
                "backup_path": backup_path,
                "backup_type": backup_type,
                "timestamp": datetime.now().isoformat(),
                "compressed": compress,
                "file_size": file_size,
                "checksum": checksum,
                "verified": verify
            }
            
            self.manifest["backups"].append(backup_record)
            self._save_manifest()
            
            logger.info(f"Created {backup_type} backup: {backup_filename} ({file_size:,} bytes)")
            
            return backup_record
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            # Clean up partial backup
            if os.path.exists(backup_path):
                os.remove(backup_path)
            raise
    
    def _create_full_backup(self, source_db: str, dest_path: str, compress: bool):
        """Create full database backup using SQLite backup API"""
        # Use SQLite's backup API for safe online backup
        source_conn = sqlite3.connect(source_db)
        
        # Create temporary uncompressed backup
        temp_backup = dest_path.replace('.gz', '') if compress else dest_path
        
        dest_conn = sqlite3.connect(temp_backup)
        
        # Perform backup (can run while database is in use)
        source_conn.backup(dest_conn)
        
        dest_conn.close()
        source_conn.close()
        
        # Compress if requested
        if compress:
            with open(temp_backup, 'rb') as f_in:
                with gzip.open(dest_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(temp_backup)
    
    def _create_incremental_backup(self, source_db: str, dest_path: str, compress: bool):
        """
        Create incremental backup (for now, implements differential from last full)
        
        Note: True incremental backups would require WAL mode and tracking changes.
        This is a simplified implementation.
        """
        # Find last full backup
        db_name = os.path.basename(source_db)
        full_backups = [b for b in self.manifest["backups"] 
                       if b["database_name"] == db_name and b["backup_type"] == "full"]
        
        if not full_backups:
            logger.warning("No full backup found, creating full backup instead")
            return self._create_full_backup(source_db, dest_path, compress)
        
        # For simplicity, create full backup (proper incremental needs WAL)
        # In production, implement WAL-based incremental backups
        self._create_full_backup(source_db, dest_path, compress)
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of backup file"""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _verify_backup(self, backup_path: str, compressed: bool) -> bool:
        """Verify backup integrity"""
        try:
            if compressed:
                # Decompress to temp file and verify
                temp_db = backup_path.replace('.gz', '.temp')
                
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_db, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Verify SQLite database
                is_valid = self._verify_sqlite_db(temp_db)
                os.remove(temp_db)
                
                return is_valid
            else:
                return self._verify_sqlite_db(backup_path)
        
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
    
    def _verify_sqlite_db(self, db_path: str) -> bool:
        """Verify SQLite database integrity"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] == "ok"
        
        except Exception as e:
            logger.error(f"SQLite verification failed: {e}")
            return False
    
    def restore_backup(self, backup_id: str, restore_path: str = None,
                      verify_before_restore: bool = True) -> bool:
        """
        Restore a database from backup
        
        Args:
            backup_id: ID of backup to restore
            restore_path: Path to restore to (defaults to original location)
            verify_before_restore: Verify backup before restoring
            
        Returns:
            Success status
        """
        # Find backup
        backup = None
        for b in self.manifest["backups"]:
            if b["backup_id"] == backup_id:
                backup = b
                break
        
        if not backup:
            raise ValueError(f"Backup not found: {backup_id}")
        
        if not os.path.exists(backup["backup_path"]):
            raise FileNotFoundError(f"Backup file not found: {backup['backup_path']}")
        
        # Verify if requested
        if verify_before_restore:
            logger.info("Verifying backup before restore...")
            if not self._verify_backup(backup["backup_path"], backup["compressed"]):
                raise ValueError("Backup verification failed, restore aborted")
        
        # Determine restore path
        target_path = restore_path or backup["database_path"]
        
        # Create backup of existing database before restore
        if os.path.exists(target_path):
            pre_restore_backup = f"{target_path}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target_path, pre_restore_backup)
            logger.info(f"Created pre-restore backup: {pre_restore_backup}")
        
        try:
            # Restore based on compression
            if backup["compressed"]:
                with gzip.open(backup["backup_path"], 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup["backup_path"], target_path)
            
            # Verify restored database
            if not self._verify_sqlite_db(target_path):
                raise ValueError("Restored database failed integrity check")
            
            logger.info(f"Successfully restored backup {backup_id} to {target_path}")
            return True
        
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            # Attempt to restore pre-restore backup
            if 'pre_restore_backup' in locals() and os.path.exists(pre_restore_backup):
                shutil.copy2(pre_restore_backup, target_path)
                logger.info("Restored pre-restore backup after failure")
            raise
    
    def list_backups(self, database_name: str = None, 
                    backup_type: str = None) -> List[Dict[str, Any]]:
        """List available backups with optional filtering"""
        backups = self.manifest["backups"]
        
        if database_name:
            backups = [b for b in backups if b["database_name"] == database_name]
        
        if backup_type:
            backups = [b for b in backups if b["backup_type"] == backup_type]
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return backups
    
    def get_point_in_time_backup(self, database_name: str, 
                                target_time: datetime) -> Optional[Dict[str, Any]]:
        """Find the best backup for point-in-time recovery"""
        backups = self.list_backups(database_name=database_name)
        
        # Find latest backup before target time
        for backup in backups:
            backup_time = datetime.fromisoformat(backup["timestamp"])
            if backup_time <= target_time:
                return backup
        
        return None
    
    def cleanup_old_backups(self) -> int:
        """Remove backups older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        backups_to_keep = []
        
        for backup in self.manifest["backups"]:
            backup_time = datetime.fromisoformat(backup["timestamp"])
            
            if backup_time < cutoff_date:
                # Remove backup file
                try:
                    if os.path.exists(backup["backup_path"]):
                        os.remove(backup["backup_path"])
                    removed_count += 1
                    logger.info(f"Removed old backup: {backup['backup_id']}")
                except Exception as e:
                    logger.error(f"Failed to remove backup {backup['backup_id']}: {e}")
                    backups_to_keep.append(backup)  # Keep in manifest if removal failed
            else:
                backups_to_keep.append(backup)
        
        self.manifest["backups"] = backups_to_keep
        self._save_manifest()
        
        return removed_count
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics"""
        backups = self.manifest["backups"]
        
        if not backups:
            return {"total_backups": 0}
        
        total_size = sum(b["file_size"] for b in backups)
        
        by_database = {}
        for backup in backups:
            db_name = backup["database_name"]
            if db_name not in by_database:
                by_database[db_name] = {"count": 0, "size": 0, "latest": None}
            
            by_database[db_name]["count"] += 1
            by_database[db_name]["size"] += backup["file_size"]
            
            if not by_database[db_name]["latest"]:
                by_database[db_name]["latest"] = backup["timestamp"]
        
        return {
            "total_backups": len(backups),
            "total_size": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "by_database": by_database,
            "oldest_backup": min(b["timestamp"] for b in backups),
            "newest_backup": max(b["timestamp"] for b in backups),
            "retention_days": self.retention_days
        }
    
    def create_scheduled_backup(self, database_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Create backups for multiple databases (for scheduled jobs)
        
        Args:
            database_paths: List of database paths to backup
            
        Returns:
            List of backup records
        """
        results = []
        
        for db_path in database_paths:
            try:
                backup_record = self.create_backup(
                    database_path=db_path,
                    backup_type="full",
                    compress=True,
                    verify=True
                )
                results.append(backup_record)
            except Exception as e:
                logger.error(f"Scheduled backup failed for {db_path}: {e}")
                results.append({
                    "database_path": db_path,
                    "error": str(e),
                    "success": False
                })
        
        return results


def create_backup_schedule():
    """
    Create automated backup schedule configuration
    This can be called by a cron job or task scheduler
    """
    backup_manager = BackupManager()
    
    # Define databases to backup
    databases = [
        "databases/cityA/caselle_gl0_mock.db",
        "databases/cityA/caselle_payroll_mock.db",
        "databases/core/cache.db",
        "databases/core/audit.db"
    ]
    
    # Filter to existing databases
    existing_dbs = [db for db in databases if os.path.exists(db)]
    
    if existing_dbs:
        logger.info(f"Starting scheduled backup for {len(existing_dbs)} databases")
        results = backup_manager.create_scheduled_backup(existing_dbs)
        
        success_count = sum(1 for r in results if r.get("success", True))
        logger.info(f"Backup completed: {success_count}/{len(existing_dbs)} successful")
        
        # Cleanup old backups
        removed = backup_manager.cleanup_old_backups()
        if removed > 0:
            logger.info(f"Cleaned up {removed} old backups")
    else:
        logger.warning("No databases found for backup")


if __name__ == "__main__":
    # Run backup schedule when executed directly
    create_backup_schedule()
