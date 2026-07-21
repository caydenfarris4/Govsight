"""
File Watcher Service
Monitors a configured folder for new ERP export files and auto-imports them
"""
import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

WATCHER_CONFIG_PATH = "configs/file_watcher_config.json"
WATCHER_STATUS_PATH = "configs/file_watcher_status.json"

DEFAULT_WATCHER_CONFIG = {
    "enabled": False,
    "watch_folder": "imports/incoming",
    "check_interval_hours": 1,
    "auto_archive": True,
    "archive_folder": "imports/processed",
    "file_types": [".csv", ".pdf"],
    "default_fiscal_year": None,
    "last_modified": None
}

class FileWatcherService:
    """Service to watch a folder and auto-import new files"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = self._load_config()
        self.status = self._load_status()
        self._running = False
        self._thread = None
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Load watcher configuration"""
        if os.path.exists(WATCHER_CONFIG_PATH):
            try:
                with open(WATCHER_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    for key, value in DEFAULT_WATCHER_CONFIG.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f"Error loading watcher config: {e}")
        return DEFAULT_WATCHER_CONFIG.copy()
    
    def _save_config(self) -> bool:
        """Save watcher configuration"""
        try:
            os.makedirs(os.path.dirname(WATCHER_CONFIG_PATH), exist_ok=True)
            self.config["last_modified"] = datetime.now().isoformat()
            with open(WATCHER_CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving watcher config: {e}")
            return False
    
    def _load_status(self) -> Dict[str, Any]:
        """Load watcher status"""
        default_status = {
            "last_check": None,
            "next_check": None,
            "files_processed_today": 0,
            "total_files_processed": 0,
            "last_import_results": [],
            "errors": []
        }
        if os.path.exists(WATCHER_STATUS_PATH):
            try:
                with open(WATCHER_STATUS_PATH, 'r') as f:
                    status = json.load(f)
                    for key, value in default_status.items():
                        if key not in status:
                            status[key] = value
                    return status
            except Exception:
                pass
        return default_status
    
    def _save_status(self) -> bool:
        """Save watcher status"""
        try:
            os.makedirs(os.path.dirname(WATCHER_STATUS_PATH), exist_ok=True)
            with open(WATCHER_STATUS_PATH, 'w') as f:
                json.dump(self.status, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving watcher status: {e}")
            return False
    
    def configure(
        self,
        watch_folder: str = None,
        check_interval_hours: float = None,
        auto_archive: bool = None,
        archive_folder: str = None,
        file_types: List[str] = None,
        default_fiscal_year: int = None,
        enabled: bool = None
    ) -> Dict[str, Any]:
        """Update watcher configuration"""
        if watch_folder is not None:
            self.config["watch_folder"] = watch_folder
        if check_interval_hours is not None:
            self.config["check_interval_hours"] = max(0.25, check_interval_hours)
        if auto_archive is not None:
            self.config["auto_archive"] = auto_archive
        if archive_folder is not None:
            self.config["archive_folder"] = archive_folder
        if file_types is not None:
            self.config["file_types"] = file_types
        if default_fiscal_year is not None:
            self.config["default_fiscal_year"] = default_fiscal_year
        if enabled is not None:
            self.config["enabled"] = enabled
        
        os.makedirs(self.config["watch_folder"], exist_ok=True)
        if self.config["auto_archive"]:
            os.makedirs(self.config["archive_folder"], exist_ok=True)
        
        self._save_config()
        
        return {"success": True, "config": self.config}
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        status = self.status.copy()
        status["is_running"] = self._running
        status["config"] = self.config.copy()
        
        watch_folder = self.config["watch_folder"]
        if os.path.exists(watch_folder):
            pending = [f for f in os.listdir(watch_folder) 
                      if any(f.lower().endswith(ext) for ext in self.config["file_types"])]
            status["pending_files"] = pending
            status["pending_count"] = len(pending)
        else:
            status["pending_files"] = []
            status["pending_count"] = 0
        
        return status
    
    def check_and_process(self, force: bool = False) -> Dict[str, Any]:
        """Check for new files and process them"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "files_found": 0,
            "files_processed": 0,
            "files_failed": 0,
            "details": []
        }
        
        watch_folder = self.config["watch_folder"]
        
        if not os.path.exists(watch_folder):
            os.makedirs(watch_folder, exist_ok=True)
            results["message"] = f"Created watch folder: {watch_folder}"
            return results
        
        file_types = self.config["file_types"]
        files = [f for f in os.listdir(watch_folder) 
                if any(f.lower().endswith(ext) for ext in file_types)]
        
        results["files_found"] = len(files)
        
        if not files:
            results["message"] = "No new files to process"
            self.status["last_check"] = datetime.now().isoformat()
            self._update_next_check()
            self._save_status()
            return results
        
        try:
            from modules.data_adapter.unified_adapter import UnifiedDataAdapter
            adapter = UnifiedDataAdapter()
        except Exception as e:
            results["error"] = f"Failed to initialize adapter: {e}"
            return results
        
        for filename in files:
            file_path = os.path.join(watch_folder, filename)
            file_result = {
                "filename": filename,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                import_result = adapter.import_file(
                    file_path=file_path,
                    fiscal_year=self.config.get("default_fiscal_year"),
                    auto_archive=True
                )
                
                if import_result.get("success"):
                    file_result["status"] = "success"
                    file_result["records"] = import_result.get("result", {}).get("record_count", 0)
                    file_result["report_type"] = import_result.get("result", {}).get("report_type", "unknown")
                    results["files_processed"] += 1
                    
                    if self.config["auto_archive"]:
                        archive_path = os.path.join(
                            self.config["archive_folder"],
                            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        )
                        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                        os.rename(file_path, archive_path)
                        file_result["archived_to"] = archive_path
                else:
                    file_result["status"] = "failed"
                    file_result["error"] = import_result.get("result", {}).get("error", "Unknown error")
                    results["files_failed"] += 1
                    
            except Exception as e:
                file_result["status"] = "error"
                file_result["error"] = str(e)
                results["files_failed"] += 1
            
            results["details"].append(file_result)
        
        self.status["last_check"] = datetime.now().isoformat()
        self.status["total_files_processed"] += results["files_processed"]
        self.status["files_processed_today"] += results["files_processed"]
        self.status["last_import_results"] = results["details"][-10:]
        self._update_next_check()
        self._save_status()
        
        results["message"] = f"Processed {results['files_processed']} of {results['files_found']} files"
        return results
    
    def _update_next_check(self):
        """Update the next scheduled check time"""
        interval_hours = self.config.get("check_interval_hours", 1)
        next_check = datetime.now() + timedelta(hours=interval_hours)
        self.status["next_check"] = next_check.isoformat()
    
    def start_background_watcher(self):
        """Start the background watcher thread"""
        if self._running:
            return {"success": False, "message": "Watcher already running"}
        
        if not self.config.get("enabled"):
            return {"success": False, "message": "Watcher not enabled in config"}
        
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        
        return {"success": True, "message": "Background watcher started"}
    
    def stop_background_watcher(self):
        """Stop the background watcher thread"""
        self._running = False
        return {"success": True, "message": "Watcher stopped"}
    
    def _watch_loop(self):
        """Main watch loop for background processing"""
        logger.info("File watcher started")
        
        while self._running:
            try:
                if self.config.get("enabled"):
                    self.check_and_process()
                
                interval_seconds = self.config.get("check_interval_hours", 1) * 3600
                sleep_interval = min(60, interval_seconds)
                
                elapsed = 0
                while elapsed < interval_seconds and self._running:
                    time.sleep(sleep_interval)
                    elapsed += sleep_interval
                    
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
                self.status["errors"].append({
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })
                self.status["errors"] = self.status["errors"][-10:]
                self._save_status()
                time.sleep(60)
        
        logger.info("File watcher stopped")


def get_file_watcher() -> FileWatcherService:
    """Get the singleton file watcher instance"""
    return FileWatcherService()
