"""
Ingestion pipeline: source -> AI-mapped canonical records -> platform store.

This is the funnel the Admin panel drives. A registered source (Caselle
ERP API, any other REST API, or a file drop) is fetched, massaged through
its approved mapping (see ai_data_mapper), validated, and written into
the canonical store the rest of the platform reads:

    databases/core/govsight_all_in_one_data.db
        gl_accounts             <- 'gl_accounts' entity (Budget Playground,
                                   scenario planner, PBB all read this)
        canonical_transactions  <- 'transactions' entity
        canonical_vendors       <- 'vendors' entity
        canonical_departments   <- 'departments' entity

Writes are idempotent upserts on each entity's natural key, so re-running
a sync never duplicates rows.
"""

import csv
import io
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

import requests

from modules.data_adapter.ai_data_mapper import (
    MappingEngine,
    MappingStore,
    TransformExecutor,
)

logger = logging.getLogger(__name__)

CANONICAL_DB_PATH = os.path.join("databases", "core", "govsight_all_in_one_data.db")

_ENTITY_TABLES = {
    "gl_accounts": {
        "table": "gl_accounts",
        "columns": {
            # canonical field -> table column
            "account_number": "account_number",
            "account_name": "account_name",
            "account_type": "account_type",
            "department": "department",
            "fund": "fund",
            "budget_amount": "budget_amount",
            "ytd_actual": "ytd_actual",
        },
        "key": ["account_number"],
        "create": """
            CREATE TABLE IF NOT EXISTS gl_accounts (
                account_number TEXT PRIMARY KEY,
                account_name   TEXT NOT NULL,
                account_type   TEXT NOT NULL,
                department     TEXT NOT NULL DEFAULT '',
                fund           TEXT NOT NULL DEFAULT '10',
                budget_amount  REAL NOT NULL DEFAULT 0,
                ytd_actual     REAL NOT NULL DEFAULT 0
            )
        """,
    },
    "transactions": {
        "table": "canonical_transactions",
        "columns": {
            "source_transaction_id": "source_transaction_id",
            "transaction_date": "transaction_date",
            "account_number": "account_number",
            "amount": "amount",
            "direction": "direction",
            "vendor_name": "vendor_name",
            "description": "description",
            "department": "department",
            "fund": "fund",
        },
        "key": ["source_transaction_id"],
        "create": """
            CREATE TABLE IF NOT EXISTS canonical_transactions (
                source_transaction_id TEXT PRIMARY KEY,
                transaction_date TEXT NOT NULL,
                account_number   TEXT NOT NULL,
                amount           REAL NOT NULL,
                direction        TEXT,
                vendor_name      TEXT,
                description      TEXT,
                department       TEXT,
                fund             TEXT
            )
        """,
    },
    "vendors": {
        "table": "canonical_vendors",
        "columns": {
            "source_vendor_id": "source_vendor_id",
            "vendor_name": "vendor_name",
            "tax_id": "tax_id",
            "is_1099": "is_1099",
        },
        "key": ["source_vendor_id"],
        "create": """
            CREATE TABLE IF NOT EXISTS canonical_vendors (
                source_vendor_id TEXT PRIMARY KEY,
                vendor_name      TEXT NOT NULL,
                tax_id           TEXT,
                is_1099          INTEGER
            )
        """,
    },
    "departments": {
        "table": "canonical_departments",
        "columns": {
            "source_department_id": "source_department_id",
            "department_name": "department_name",
            "fund": "fund",
        },
        "key": ["source_department_id"],
        "create": """
            CREATE TABLE IF NOT EXISTS canonical_departments (
                source_department_id TEXT PRIMARY KEY,
                department_name      TEXT NOT NULL,
                fund                 TEXT
            )
        """,
    },
}


class IngestionPipeline:
    """Drives fetch -> massage -> validate -> upsert for registered sources."""

    def __init__(self, store: Optional[MappingStore] = None,
                 canonical_db_path: str = CANONICAL_DB_PATH):
        self.store = store or MappingStore()
        self.engine = MappingEngine()
        self.executor = TransformExecutor()
        self.canonical_db_path = canonical_db_path

    # -- fetching -----------------------------------------------------------

    def fetch_sample(self, source: Dict[str, Any], limit: int = 25) -> List[Dict[str, Any]]:
        return self.fetch_records(source, limit=limit)

    def fetch_records(self, source: Dict[str, Any],
                      limit: Optional[int] = None) -> List[Dict[str, Any]]:
        stype = source["source_type"]
        config = source.get("config") or {}
        if stype == "rest_api":
            records = self._fetch_rest(config)
        elif stype == "csv":
            records = self._fetch_csv(config)
        elif stype == "caselle":
            records = self._fetch_caselle(config)
        else:
            raise ValueError(f"Unsupported source type: {stype}")
        return records[:limit] if limit else records

    def _fetch_rest(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = config.get("url")
        if not url:
            raise ValueError("REST source has no url configured")
        headers = dict(config.get("headers") or {})
        token = config.get("bearer_token") or os.getenv(config.get("token_env", ""), "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(url, headers=headers,
                            params=config.get("params") or {}, timeout=45)
        resp.raise_for_status()
        payload = resp.json()
        # Accept either a bare list or an object with a configurable list key
        if isinstance(payload, list):
            return payload
        for key in (config.get("records_key"), "data", "results", "items", "records"):
            if key and isinstance(payload.get(key), list):
                return payload[key]
        raise ValueError("Could not locate a record list in the API response; "
                         "set records_key in the source config")

    @staticmethod
    def _fetch_csv(config: Dict[str, Any]) -> List[Dict[str, Any]]:
        path = config.get("path")
        content = config.get("content")  # inline upload from the admin UI
        if content is None:
            if not path or not os.path.exists(path):
                raise ValueError(f"CSV source file not found: {path}")
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                content = fh.read()
        reader = csv.DictReader(io.StringIO(content))
        return [dict(row) for row in reader]

    @staticmethod
    def _fetch_caselle(config: Dict[str, Any]) -> List[Dict[str, Any]]:
        from modules.data_adapter.unified_adapter import get_adapter
        adapter = get_adapter(config.get("municipality_id", "default"))
        dataset = config.get("dataset", "general_ledger")
        fetchers = {
            "general_ledger": adapter.get_general_ledger,
            "budget": adapter.get_budget_data,
            "payroll": adapter.get_payroll_data,
            "accounts_payable": adapter.get_accounts_payable,
            "vendors": adapter.get_vendors,
            "departments": adapter.get_departments,
        }
        if dataset not in fetchers:
            raise ValueError(f"Unknown Caselle dataset: {dataset}")
        records = fetchers[dataset]()
        return records if isinstance(records, list) else []

    # -- mapping ------------------------------------------------------------

    def propose_mapping(self, source_name: str, source_type: str,
                        entity: str, config: Optional[Dict[str, Any]] = None,
                        sample_records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        source_id = self.store.register_source(source_name, source_type, config)
        source = {"source_type": source_type, "config": config or {}}
        sample = sample_records if sample_records is not None else self.fetch_sample(source)
        proposal = self.engine.propose(entity, sample, source_name=source_name)
        mapping_id = self.store.save_proposal(source_id, proposal)
        proposal["mapping_id"] = mapping_id
        proposal["source_id"] = source_id
        return proposal

    # -- sync ---------------------------------------------------------------

    def run_sync(self, source_name: str, entity: str) -> Dict[str, Any]:
        sources = {s["name"]: s for s in self.store.list_sources()}
        if source_name not in sources:
            raise ValueError(f"Source not registered: {source_name}")
        source = sources[source_name]
        approved = self.store.get_approved_mapping(source["id"], entity)
        if approved is None:
            raise ValueError(
                f"No approved mapping for source '{source_name}' entity '{entity}'. "
                "Propose and approve a mapping in the Admin panel first.")

        sync_id = self.store.start_sync(source["id"], entity, approved["id"])
        try:
            records = self.fetch_records(source)
            result = self.executor.apply(
                entity, approved["mapping_json"]["mappings"], records)
            written = self._upsert_canonical(entity, result["records"])
            result["written"] = written
            status = "ok" if result["failed"] == 0 else "ok"
            detail = json.dumps({
                "written": written,
                "row_errors": [e["errors"] for e in result["errors"][:20]],
            })
            self.store.finish_sync(sync_id, result, status=status, detail=detail)
            return result
        except Exception as exc:
            self.store.finish_sync(sync_id, {}, status="error", detail=str(exc))
            raise

    def _upsert_canonical(self, entity: str, records: List[Dict[str, Any]]) -> int:
        spec = _ENTITY_TABLES.get(entity)
        if spec is None:
            raise ValueError(f"No canonical table registered for entity {entity}")
        os.makedirs(os.path.dirname(self.canonical_db_path), exist_ok=True)
        conn = sqlite3.connect(self.canonical_db_path)
        try:
            conn.execute(spec["create"])
            cols = list(spec["columns"].values())
            keys = spec["key"]
            non_keys = [c for c in cols if c not in keys]
            placeholders = ", ".join("?" for _ in cols)
            update_clause = ", ".join(f"{c}=excluded.{c}" for c in non_keys)
            sql = (f"INSERT INTO {spec['table']} ({', '.join(cols)}) "
                   f"VALUES ({placeholders}) "
                   f"ON CONFLICT({', '.join(keys)}) DO UPDATE SET {update_clause}")
            count = 0
            for rec in records:
                values = []
                for canonical_field, _col in spec["columns"].items():
                    v = rec.get(canonical_field)
                    if isinstance(v, bool):
                        v = int(v)
                    values.append(v if v is not None else "")
                conn.execute(sql, values)
                count += 1
            conn.commit()
            return count
        finally:
            conn.close()


def get_pipeline() -> IngestionPipeline:
    return IngestionPipeline()
