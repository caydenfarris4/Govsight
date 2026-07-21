"""
Enterprise Configuration Service - SQLite-backed key/value store

Replaces all JSON config file reads/writes with a single persistent database table.
Provides namespaced configuration with in-memory caching, atomic writes,
audit trail, and thread-safe access.

ARCHITECTURAL DECISIONS:
1. SQLite-backed instead of JSON files
   WHY: Atomic writes, no race conditions, works with concurrent Streamlit sessions
2. Namespace/key/value schema with JSON serialization for complex values
   WHY: Flexible enough for any config shape without schema migrations per config change
3. In-memory cache with write-through invalidation
   WHY: Performance - most config reads happen on every page load; cache avoids disk I/O
4. Backward-compatible JSON migration on first run
   WHY: Existing JSON configs must be preserved during transition
"""

import os
import json
import sqlite3
import threading
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("govsight.services.config")

CONFIG_DB_PATH = "databases/govsight_config.db"

_instance = None
_lock = threading.Lock()


class ConfigService:
    def __init__(self, db_path: str = CONFIG_DB_PATH):
        self._db_path = db_path
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._write_lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS app_config (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    value_type TEXT NOT NULL DEFAULT 'string',
                    updated_at TEXT NOT NULL,
                    updated_by TEXT DEFAULT 'system',
                    PRIMARY KEY (namespace, key)
                );
                CREATE TABLE IF NOT EXISTS config_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_at TEXT NOT NULL,
                    changed_by TEXT DEFAULT 'system'
                );
                CREATE INDEX IF NOT EXISTS idx_config_namespace ON app_config(namespace);
                CREATE INDEX IF NOT EXISTS idx_audit_namespace ON config_audit(namespace, changed_at);
            """)
            conn.commit()
        finally:
            conn.close()

    def _serialize(self, value: Any) -> Tuple[str, str]:
        if isinstance(value, bool):
            return json.dumps(value), "bool"
        elif isinstance(value, int):
            return str(value), "int"
        elif isinstance(value, float):
            return str(value), "float"
        elif isinstance(value, str):
            return value, "string"
        elif isinstance(value, (dict, list)):
            return json.dumps(value, default=str), "json"
        else:
            return json.dumps(value, default=str), "json"

    def _deserialize(self, raw: str, value_type: str) -> Any:
        if value_type == "bool":
            return json.loads(raw)
        elif value_type == "int":
            return int(raw)
        elif value_type == "float":
            return float(raw)
        elif value_type == "string":
            return raw
        elif value_type == "json":
            return json.loads(raw)
        return raw

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        if namespace in self._cache and key in self._cache[namespace]:
            return self._cache[namespace][key]

        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT value, value_type FROM app_config WHERE namespace = ? AND key = ?",
                (namespace, key)
            ).fetchone()
            if row is None:
                return default
            val = self._deserialize(row[0], row[1])
            self._cache.setdefault(namespace, {})[key] = val
            return val
        finally:
            conn.close()

    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        if namespace in self._cache:
            return dict(self._cache[namespace])

        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT key, value, value_type FROM app_config WHERE namespace = ?",
                (namespace,)
            ).fetchall()
            result = {}
            for key, raw, vtype in rows:
                result[key] = self._deserialize(raw, vtype)
            self._cache[namespace] = dict(result)
            return result
        finally:
            conn.close()

    def set(self, namespace: str, key: str, value: Any, updated_by: str = "system") -> bool:
        raw, vtype = self._serialize(value)
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            conn = self._get_conn()
            try:
                old_row = conn.execute(
                    "SELECT value FROM app_config WHERE namespace = ? AND key = ?",
                    (namespace, key)
                ).fetchone()
                old_value = old_row[0] if old_row else None

                conn.execute("""
                    INSERT INTO app_config (namespace, key, value, value_type, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(namespace, key) DO UPDATE SET
                        value = excluded.value,
                        value_type = excluded.value_type,
                        updated_at = excluded.updated_at,
                        updated_by = excluded.updated_by
                """, (namespace, key, raw, vtype, now, updated_by))

                conn.execute("""
                    INSERT INTO config_audit (namespace, key, old_value, new_value, changed_at, changed_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (namespace, key, old_value, raw, now, updated_by))

                conn.commit()

                if namespace in self._cache:
                    self._cache[namespace][key] = value
                else:
                    self._cache[namespace] = {key: value}

                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"ConfigService.set failed [{namespace}.{key}]: {e}")
                return False
            finally:
                conn.close()

    def set_namespace(self, namespace: str, data: Dict[str, Any], updated_by: str = "system") -> bool:
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            conn = self._get_conn()
            try:
                for key, value in data.items():
                    raw, vtype = self._serialize(value)

                    old_row = conn.execute(
                        "SELECT value FROM app_config WHERE namespace = ? AND key = ?",
                        (namespace, key)
                    ).fetchone()
                    old_value = old_row[0] if old_row else None

                    conn.execute("""
                        INSERT INTO app_config (namespace, key, value, value_type, updated_at, updated_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(namespace, key) DO UPDATE SET
                            value = excluded.value,
                            value_type = excluded.value_type,
                            updated_at = excluded.updated_at,
                            updated_by = excluded.updated_by
                    """, (namespace, key, raw, vtype, now, updated_by))

                    conn.execute("""
                        INSERT INTO config_audit (namespace, key, old_value, new_value, changed_at, changed_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (namespace, key, old_value, raw, now, updated_by))

                conn.commit()
                self._cache[namespace] = dict(data)
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"ConfigService.set_namespace failed [{namespace}]: {e}")
                return False
            finally:
                conn.close()

    def delete(self, namespace: str, key: str, deleted_by: str = "system") -> bool:
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            conn = self._get_conn()
            try:
                old_row = conn.execute(
                    "SELECT value FROM app_config WHERE namespace = ? AND key = ?",
                    (namespace, key)
                ).fetchone()

                if old_row:
                    conn.execute(
                        "DELETE FROM app_config WHERE namespace = ? AND key = ?",
                        (namespace, key)
                    )
                    conn.execute("""
                        INSERT INTO config_audit (namespace, key, old_value, new_value, changed_at, changed_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (namespace, key, old_row[0], None, now, deleted_by))
                    conn.commit()

                if namespace in self._cache and key in self._cache[namespace]:
                    del self._cache[namespace][key]

                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"ConfigService.delete failed [{namespace}.{key}]: {e}")
                return False
            finally:
                conn.close()

    def delete_namespace(self, namespace: str, deleted_by: str = "system") -> bool:
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT key, value FROM app_config WHERE namespace = ?",
                    (namespace,)
                ).fetchall()

                for key, old_value in rows:
                    conn.execute("""
                        INSERT INTO config_audit (namespace, key, old_value, new_value, changed_at, changed_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (namespace, key, old_value, None, now, deleted_by))

                conn.execute("DELETE FROM app_config WHERE namespace = ?", (namespace,))
                conn.commit()

                self._cache.pop(namespace, None)
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"ConfigService.delete_namespace failed [{namespace}]: {e}")
                return False
            finally:
                conn.close()

    def get_audit_log(self, namespace: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            if namespace:
                rows = conn.execute(
                    "SELECT namespace, key, old_value, new_value, changed_at, changed_by "
                    "FROM config_audit WHERE namespace = ? ORDER BY changed_at DESC LIMIT ?",
                    (namespace, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT namespace, key, old_value, new_value, changed_at, changed_by "
                    "FROM config_audit ORDER BY changed_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [
                {
                    "namespace": r[0], "key": r[1], "old_value": r[2],
                    "new_value": r[3], "changed_at": r[4], "changed_by": r[5]
                }
                for r in rows
            ]
        finally:
            conn.close()

    def invalidate_cache(self, namespace: Optional[str] = None):
        if namespace:
            self._cache.pop(namespace, None)
        else:
            self._cache.clear()

    def list_namespaces(self) -> List[str]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT DISTINCT namespace FROM app_config ORDER BY namespace").fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()


def get_config_service() -> ConfigService:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ConfigService()
    return _instance
