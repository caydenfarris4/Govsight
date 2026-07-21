"""
Schema Migration Service - Versioned database schema management

Replaces scattered CREATE TABLE IF NOT EXISTS patterns with a proper
versioned migration system. Tracks which migrations have been applied
and applies them in order.

ARCHITECTURAL DECISIONS:
1. Migration table tracks applied versions in the config database
   WHY: Single source of truth for schema state; no guessing if a table exists
2. Migrations are Python functions, not SQL files
   WHY: Can include data transformations, conditional logic, and error handling
3. Forward-only migrations (no rollback)
   WHY: Rollbacks in production databases are dangerous; use backups instead
4. Runs automatically on application startup
   WHY: Ensures schema is always current without manual intervention
"""

import sqlite3
import os
import json
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional, Any

logger = logging.getLogger("govsight.services.migration")

_instance = None
_lock = None

try:
    import threading
    _lock = threading.Lock()
except Exception:
    pass


class MigrationService:
    def __init__(self, db_path: str = "databases/govsight_config.db"):
        self._db_path = db_path
        self._migrations: List[Dict[str, Any]] = []
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_migration_table()
        self._register_core_migrations()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_migration_table(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    checksum TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def register(self, version: str, description: str, fn: Callable[[sqlite3.Connection], None]):
        self._migrations.append({
            "version": version,
            "description": description,
            "fn": fn,
        })
        self._migrations.sort(key=lambda m: m["version"])

    def get_applied_versions(self) -> List[str]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def get_pending(self) -> List[Dict[str, Any]]:
        applied = set(self.get_applied_versions())
        return [m for m in self._migrations if m["version"] not in applied]

    def apply_all(self) -> List[str]:
        pending = self.get_pending()
        if not pending:
            logger.info("No pending migrations")
            return []

        applied = []
        conn = self._get_conn()
        try:
            for migration in pending:
                version = migration["version"]
                desc = migration["description"]
                logger.info(f"Applying migration {version}: {desc}")
                try:
                    migration["fn"](conn)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
                        (version, desc, datetime.utcnow().isoformat())
                    )
                    conn.commit()
                    applied.append(version)
                    logger.info(f"Migration {version} applied successfully")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Migration {version} failed: {e}")
                    raise
        finally:
            conn.close()

        return applied

    def _register_core_migrations(self):
        self.register("001", "Create app_config table", _migration_001_app_config)
        self.register("002", "Create config_audit table", _migration_002_config_audit)
        self.register("003", "Migrate JSON configs to database", _migration_003_json_to_db)


def _migration_001_app_config(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_config (
            namespace TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            value_type TEXT NOT NULL DEFAULT 'string',
            updated_at TEXT NOT NULL,
            updated_by TEXT DEFAULT 'system',
            PRIMARY KEY (namespace, key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_config_namespace ON app_config(namespace)")


def _migration_002_config_audit(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            namespace TEXT NOT NULL,
            key TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_at TEXT NOT NULL,
            changed_by TEXT DEFAULT 'system'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_namespace ON config_audit(namespace, changed_at)")


def _migration_003_json_to_db(conn: sqlite3.Connection):
    now = datetime.utcnow().isoformat()

    json_sources = [
        ("system_settings", "configs/system/system_settings.json", None),
        ("system_settings", "system_settings.json", None),
        ("fund_classifications", "configs/application/fund_classifications.json", None),
        ("fund_classifications", "fund_classifications.json", None),
        ("city_config", "configs/application/config.json", None),
        ("city_config", "config.json", None),
        ("data_adapter", "configs/data_adapter_config.json", None),
        ("super_admin", "configs/super_admin_config.json", None),
    ]

    for namespace, filepath, _ in json_sources:
        if not os.path.exists(filepath):
            continue

        existing = conn.execute(
            "SELECT COUNT(*) FROM app_config WHERE namespace = ?", (namespace,)
        ).fetchone()[0]
        if existing > 0:
            continue

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Could not read {filepath} for migration: {e}")
            continue

        if isinstance(data, dict):
            for key, value in data.items():
                if key in ("GoogleSheets_Credentials", "OpenAI_Key", "DefaultPassword"):
                    continue

                if isinstance(value, (dict, list)):
                    raw = json.dumps(value, default=str)
                    vtype = "json"
                elif isinstance(value, bool):
                    raw = json.dumps(value)
                    vtype = "bool"
                elif isinstance(value, int):
                    raw = str(value)
                    vtype = "int"
                elif isinstance(value, float):
                    raw = str(value)
                    vtype = "float"
                else:
                    raw = str(value)
                    vtype = "string"

                conn.execute("""
                    INSERT OR IGNORE INTO app_config (namespace, key, value, value_type, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (namespace, key, raw, vtype, now, "migration_003"))

        logger.info(f"Migrated {filepath} -> namespace '{namespace}'")


def get_migration_service() -> MigrationService:
    global _instance
    if _instance is None:
        if _lock:
            with _lock:
                if _instance is None:
                    _instance = MigrationService()
        else:
            _instance = MigrationService()
    return _instance
