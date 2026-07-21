"""
Data Adapter Configuration
Defines data source settings per municipality.

Reads/writes through enterprise ConfigService (database-backed).
Falls back to JSON file if ConfigService is unavailable.

ARCHITECTURAL DECISIONS:
1. ConfigService namespace 'data_adapter' stores all settings
   WHY: Eliminates configs/data_adapter_config.json file dependency
2. Preserves same public API (load_config, save_config, etc.)
   WHY: Existing callers in unified_adapter.py and file_watcher.py don't need changes
3. Secrets (API keys) stay in environment variables, never in config
   WHY: Enterprise security - credentials must not be persisted in any storage
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger("govsight.data_adapter.config")

class DataSourceType(Enum):
    CASELLE_API = "caselle_api"
    FILE_IMPORT = "file_import"
    LEGACY_DATABASE = "legacy_database"

DEFAULT_CONFIG = {
    "default_source": DataSourceType.FILE_IMPORT.value,
    "municipalities": {
        "default": {
            "name": "Default Municipality",
            "source_type": DataSourceType.FILE_IMPORT.value,
            "caselle_api": {
                "enabled": False,
                "base_url": "",
                "client_id": "",
                "timeout": 30,
                "retry_count": 3
            },
            "file_import": {
                "enabled": True,
                "incoming_folder": "imports/incoming",
                "processed_folder": "imports/processed",
                "archive_folder": "imports/archive",
                "supported_formats": ["csv", "pdf"],
                "auto_process": True,
                "watch_interval_seconds": 60
            },
            "report_archive": {
                "enabled": True,
                "database_path": "databases/report_archive.db",
                "retention_years": 10
            }
        }
    }
}

CONFIG_FILE_PATH = "configs/data_adapter_config.json"


def _get_config_service():
    try:
        from modules.services.config_service import get_config_service
        return get_config_service()
    except Exception:
        return None


def load_config() -> Dict[str, Any]:
    svc = _get_config_service()
    if svc:
        try:
            data = svc.get_namespace("data_adapter")
            if data:
                if "municipalities" in data and isinstance(data["municipalities"], str):
                    data["municipalities"] = json.loads(data["municipalities"])
                logger.info("Loaded data adapter config from ConfigService")
                return data
        except Exception as e:
            logger.warning(f"ConfigService read failed, falling back to JSON: {e}")

    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> bool:
    svc = _get_config_service()
    if svc:
        try:
            result = svc.set_namespace("data_adapter", config, updated_by="data_adapter")
            if result:
                logger.info("Saved data adapter config to ConfigService")
                return True
        except Exception as e:
            logger.error(f"ConfigService write failed: {e}")

    try:
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False

def get_municipality_config(municipality_id: str = "default") -> Dict[str, Any]:
    config = load_config()
    municipalities = config.get("municipalities", {})
    return municipalities.get(municipality_id, municipalities.get("default", {}))

def set_data_source(municipality_id: str, source_type: DataSourceType) -> bool:
    config = load_config()
    if municipality_id not in config.get("municipalities", {}):
        config["municipalities"][municipality_id] = DEFAULT_CONFIG["municipalities"]["default"].copy()
    config["municipalities"][municipality_id]["source_type"] = source_type.value
    return save_config(config)

def configure_caselle_api(
    municipality_id: str,
    base_url: str,
    client_id: str = "",
    timeout: int = 30,
    retry_count: int = 3
) -> bool:
    config = load_config()
    if municipality_id not in config.get("municipalities", {}):
        config["municipalities"][municipality_id] = DEFAULT_CONFIG["municipalities"]["default"].copy()

    api_key_configured = bool(os.getenv("CASELLE_API_KEY"))

    config["municipalities"][municipality_id]["caselle_api"] = {
        "enabled": api_key_configured and bool(base_url),
        "base_url": base_url,
        "client_id": client_id,
        "timeout": timeout,
        "retry_count": retry_count
    }
    if api_key_configured and base_url:
        config["municipalities"][municipality_id]["source_type"] = DataSourceType.CASELLE_API.value
    return save_config(config)

def configure_file_import(
    municipality_id: str,
    incoming_folder: str = "imports/incoming",
    supported_formats: list = None
) -> bool:
    if supported_formats is None:
        supported_formats = ["csv", "pdf"]

    config = load_config()
    if municipality_id not in config.get("municipalities", {}):
        config["municipalities"][municipality_id] = DEFAULT_CONFIG["municipalities"]["default"].copy()

    config["municipalities"][municipality_id]["file_import"]["incoming_folder"] = incoming_folder
    config["municipalities"][municipality_id]["file_import"]["supported_formats"] = supported_formats
    config["municipalities"][municipality_id]["file_import"]["enabled"] = True
    config["municipalities"][municipality_id]["source_type"] = DataSourceType.FILE_IMPORT.value
    return save_config(config)
