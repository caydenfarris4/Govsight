"""
AI data massaging layer.

Takes raw records from any external system — the Caselle ERP API, another
ERP's REST API, a payroll system, a CSV export — and maps them into
GovSight's canonical schema (modules/data_adapter/canonical_schema.py).

How it works
------------
1. A source is registered with a sample of its records.
2. The mapping engine proposes a field mapping: AI-assisted when an
   OpenAI or Anthropic key is configured (the model sees field names,
   inferred types, and a few sample values, and returns a strict JSON
   mapping), falling back to a deterministic alias/fuzzy-name heuristic
   when no AI is available. Every proposal is labeled with its method
   and per-field confidence.
3. A human approves (optionally edits) the mapping in the Admin panel.
4. The TransformExecutor applies the approved mapping deterministically
   on every sync. The AI runs once per source schema — never per row —
   so sync results are reproducible and auditable.

Transforms are drawn from a safe whitelist; there is no eval() and no
AI-generated code execution. Mappings, proposals, and sync history are
persisted in SQLite (databases/core/integration_mappings.db).
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from modules.data_adapter.canonical_schema import (
    CanonicalEntity,
    entity_prompt_description,
    get_entity,
)

logger = logging.getLogger(__name__)

MAPPING_DB_PATH = os.path.join("databases", "core", "integration_mappings.db")

# Transform whitelist. Each entry: name -> (description, params)
SUPPORTED_TRANSFORMS = {
    "direct":     "Copy the source field value as-is",
    "to_number":  "Parse a number: strips $ , spaces; (1,234.56) and trailing '-' become negative",
    "to_integer": "Parse an integer (e.g. fiscal year from '2025' or 'FY2025')",
    "to_date":    "Parse a date into ISO YYYY-MM-DD (accepts common US formats)",
    "to_boolean": "Parse truthy strings (Y/Yes/True/1) into booleans",
    "constant":   "Ignore the source; always emit the configured 'value'",
    "concat":     "Join multiple source fields with the configured 'separator'",
    "map_values": "Translate source values through the configured 'values' dictionary (unmatched pass through)",
    "signed_amount": "Combine an amount field with a debit/credit field: credits become negative",
}

_NUMBER_JUNK = re.compile(r"[$,\s]")
_DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d",
    "%d-%b-%Y", "%b %d, %Y", "%Y%m%d", "%m-%d-%Y",
)


# ---------------------------------------------------------------------------
# Sample profiling
# ---------------------------------------------------------------------------

def profile_sample(records: List[Dict[str, Any]], max_values: int = 4) -> List[Dict[str, Any]]:
    """Summarize a record sample per field: inferred type + example values.

    This profile — not the raw data — is what the AI sees, keeping the
    prompt small and limiting data exposure to a handful of example values.
    """
    if not records:
        return []
    fields: Dict[str, Dict[str, Any]] = {}
    for rec in records[:50]:
        for key, val in rec.items():
            entry = fields.setdefault(key, {"name": key, "examples": [], "types": set()})
            if val is not None and val != "" and len(entry["examples"]) < max_values:
                sval = str(val)
                if sval not in entry["examples"]:
                    entry["examples"].append(sval[:60])
            entry["types"].add(_infer_type(val))
    out = []
    for entry in fields.values():
        types = entry["types"] - {"empty"}
        entry["inferred_type"] = sorted(types)[0] if len(types) == 1 else (
            "number" if types == {"integer", "number"} else "mixed" if types else "empty")
        del entry["types"]
        out.append(entry)
    return out


def _infer_type(val: Any) -> str:
    if val is None or val == "":
        return "empty"
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, int):
        return "integer"
    if isinstance(val, float):
        return "number"
    s = str(val).strip()
    if re.fullmatch(r"-?\$?[\d,]+", s):
        return "integer"
    if re.fullmatch(r"-?\$?[\d,]*\.\d+", s) or re.fullmatch(r"\(\$?[\d,.]+\)", s):
        return "number"
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(s, fmt)
            # Reject implausible years: account numbers like 10-20-5300
            # would otherwise parse as dates (year 5300)
            if 1990 <= parsed.year <= 2100:
                return "date"
        except ValueError:
            continue
    return "string"


# ---------------------------------------------------------------------------
# Mapping proposal — AI first, deterministic heuristic as fallback
# ---------------------------------------------------------------------------

class MappingEngine:
    """Proposes source-to-canonical field mappings."""

    def propose(self, entity_name: str, sample_records: List[Dict[str, Any]],
                source_name: str = "") -> Dict[str, Any]:
        entity = get_entity(entity_name)
        if entity is None:
            raise ValueError(f"Unknown canonical entity: {entity_name}")
        profile = profile_sample(sample_records)
        if not profile:
            raise ValueError("Sample contains no records to profile")

        proposal = self._propose_with_ai(entity, profile, source_name)
        if proposal is None:
            proposal = self._propose_heuristic(entity, profile)
            proposal["method"] = "heuristic"
        else:
            proposal["method"] = proposal.get("method", "ai")

        proposal["entity"] = entity.name
        proposal["profiled_fields"] = profile
        proposal["proposed_at"] = datetime.now(timezone.utc).isoformat()
        self._annotate_gaps(entity, proposal)
        return proposal

    # -- AI path ------------------------------------------------------------

    def _propose_with_ai(self, entity: CanonicalEntity,
                         profile: List[Dict[str, Any]],
                         source_name: str) -> Optional[Dict[str, Any]]:
        prompt = self._build_prompt(entity, profile, source_name)
        raw = self._call_openai(prompt) or self._call_anthropic(prompt)
        if raw is None:
            return None
        try:
            parsed = _extract_json(raw)
            mappings = self._sanitize_ai_mappings(entity, profile, parsed)
            if not mappings:
                return None
            return {"mappings": mappings, "method": "ai"}
        except Exception as exc:
            logger.warning("AI mapping response could not be parsed (%s); "
                           "falling back to heuristic", exc)
            return None

    def _build_prompt(self, entity: CanonicalEntity, profile: List[Dict[str, Any]],
                      source_name: str) -> str:
        source_desc = "\n".join(
            f"- {f['name']} (looks like: {f['inferred_type']}; examples: {f['examples']})"
            for f in profile
        )
        transforms = "\n".join(f"- {k}: {v}" for k, v in SUPPORTED_TRANSFORMS.items())
        return f"""You are a municipal-finance data integration engineer. Map fields from an
external system export into a canonical schema.

Source system: {source_name or 'unknown'}
Source fields:
{source_desc}

{entity_prompt_description(entity)}

Allowed transforms:
{transforms}

Respond with ONLY a JSON object of this exact shape (no prose):
{{"mappings": [
  {{"target": "<canonical field>", "source": "<source field or list of fields for concat/signed_amount>",
    "transform": "<one of the allowed transforms>",
    "params": {{}},
    "confidence": <0.0-1.0>,
    "note": "<short reasoning>"}}
]}}

Rules:
- Map every REQUIRED target field you possibly can; omit targets with no plausible source.
- Use to_number for currency-looking strings, to_date for dates, to_integer for fiscal years.
- Use signed_amount (source = [amount_field, direction_field]) when debits/credits are split.
- Use constant with params.value only when the value is truly implied by the source
  (e.g. account_type = "Expense" for an expenses-only export).
- Confidence below 0.5 means a human must review that line."""

    def _call_openai(self, prompt: str) -> Optional[str]:
        if not os.getenv("OPENAI_API_KEY"):
            return None
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=os.getenv("GOVSIGHT_MAPPING_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content
        except Exception as exc:
            logger.warning("OpenAI mapping call failed: %s", exc)
            return None

    def _call_anthropic(self, prompt: str) -> Optional[str]:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return None
        try:
            import anthropic
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=os.getenv("GOVSIGHT_MAPPING_MODEL_ANTHROPIC", "claude-sonnet-5"),
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text')
        except Exception as exc:
            logger.warning("Anthropic mapping call failed: %s", exc)
            return None

    def _sanitize_ai_mappings(self, entity: CanonicalEntity,
                              profile: List[Dict[str, Any]],
                              parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Keep only mappings that reference real fields and allowed transforms."""
        source_fields = {f["name"] for f in profile}
        valid_targets = set(entity.field_map())
        clean = []
        for m in parsed.get("mappings", []):
            target = m.get("target")
            transform = m.get("transform", "direct")
            source = m.get("source")
            if target not in valid_targets or transform not in SUPPORTED_TRANSFORMS:
                continue
            sources = source if isinstance(source, list) else [source]
            if transform != "constant" and not all(s in source_fields for s in sources):
                continue
            # Enforce dtype consistency: identifiers and codes declared as
            # strings must stay strings - an AI-proposed to_number would
            # corrupt fund/account codes ("10" -> 10.0, "010" -> 10).
            target_dtype = entity.field_map()[target].dtype
            if target_dtype == "string" and transform in ("to_number", "to_integer"):
                transform = "direct"
            elif target_dtype == "number" and transform == "direct":
                transform = "to_number"
            elif target_dtype == "integer" and transform == "direct":
                transform = "to_integer"
            elif target_dtype == "date" and transform == "direct":
                transform = "to_date"
            clean.append({
                "target": target,
                "source": source,
                "transform": transform,
                "params": m.get("params") or {},
                "confidence": float(m.get("confidence", 0.5)),
                "note": str(m.get("note", ""))[:300],
            })
        return clean

    # -- Deterministic fallback ---------------------------------------------

    def _propose_heuristic(self, entity: CanonicalEntity,
                           profile: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Score every (target, source) pair, then assign globally best-first.
        # Greedy per-target assignment mis-pairs similar names (e.g. taking
        # "Acct Description" for account_number before account_name gets a
        # chance); global assignment lets the strongest pairing win.
        pairs: List[Tuple[float, str, str]] = []
        for cf in entity.fields:
            for f in profile:
                score = self._name_similarity(cf.name, cf.aliases, f["name"])
                if f["inferred_type"] == cf.dtype:
                    score += 0.1
                if score >= 0.55:
                    pairs.append((score, cf.name, f["name"]))
        pairs.sort(reverse=True)

        field_map = entity.field_map()
        mappings, used_targets, used_sources = [], set(), set()
        for score, target, source in pairs:
            if target in used_targets or source in used_sources:
                continue
            used_targets.add(target)
            used_sources.add(source)
            transform = {
                "number": "to_number", "integer": "to_integer",
                "date": "to_date", "boolean": "to_boolean",
            }.get(field_map[target].dtype, "direct")
            mappings.append({
                "target": target,
                "source": source,
                "transform": transform,
                "params": {},
                "confidence": round(min(score, 0.95), 2),
                "note": "heuristic name match",
            })
        mappings.sort(key=lambda m: [f.name for f in entity.fields].index(m["target"]))
        return {"mappings": mappings}

    @staticmethod
    def _name_similarity(target: str, aliases: List[str], candidate: str) -> float:
        def norm(s: str) -> str:
            return re.sub(r"[^a-z0-9]", "", s.lower())
        cand = norm(candidate)
        names = [norm(target)] + [norm(a) for a in aliases]
        best = 0.0
        for n in names:
            if not n:
                continue
            if cand == n:
                return 1.0
            if n in cand or cand in n:
                # Containment scaled by how much of the longer string the
                # shorter one covers, so a short alias buried in a long
                # candidate ("acct" in "acctdescription") scores lower than
                # a near-complete containment ("fundno" in "fund_no")
                shorter, longer = sorted((cand, n), key=len)
                best = max(best, 0.55 + 0.35 * (len(shorter) / len(longer)))
            best = max(best, SequenceMatcher(None, cand, n).ratio())
        return best

    # -- Shared -------------------------------------------------------------

    @staticmethod
    def _annotate_gaps(entity: CanonicalEntity, proposal: Dict[str, Any]) -> None:
        mapped = {m["target"] for m in proposal["mappings"]}
        proposal["unmapped_required"] = [
            f for f in entity.required_fields() if f not in mapped
        ]
        proposal["needs_review"] = [
            m["target"] for m in proposal["mappings"] if m["confidence"] < 0.5
        ]


def _extract_json(text: str) -> Dict[str, Any]:
    """Parse a JSON object out of a model response, tolerating code fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------------------
# Deterministic transform execution
# ---------------------------------------------------------------------------

class TransformExecutor:
    """Applies an approved mapping to raw records. No AI involved."""

    def apply(self, entity_name: str, mappings: List[Dict[str, Any]],
              records: List[Dict[str, Any]]) -> Dict[str, Any]:
        entity = get_entity(entity_name)
        if entity is None:
            raise ValueError(f"Unknown canonical entity: {entity_name}")
        good: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        for idx, rec in enumerate(records):
            row: Dict[str, Any] = {}
            row_errors: List[str] = []
            for m in mappings:
                try:
                    row[m["target"]] = self._apply_one(m, rec)
                except Exception as exc:
                    row_errors.append(f"{m['target']}: {exc}")
            for req in entity.required_fields():
                if row.get(req) in (None, ""):
                    row_errors.append(f"{req}: required field missing/empty")
            if row_errors:
                errors.append({"row": idx, "errors": row_errors, "raw": rec})
            else:
                good.append(row)
        return {
            "entity": entity_name,
            "records": good,
            "errors": errors,
            "total": len(records),
            "succeeded": len(good),
            "failed": len(errors),
        }

    def _apply_one(self, m: Dict[str, Any], rec: Dict[str, Any]) -> Any:
        transform = m["transform"]
        params = m.get("params") or {}
        source = m.get("source")

        if transform == "constant":
            return params.get("value")
        if transform == "concat":
            sep = params.get("separator", " ")
            parts = source if isinstance(source, list) else [source]
            return sep.join(str(rec.get(s, "") or "") for s in parts).strip()
        if transform == "signed_amount":
            parts = source if isinstance(source, list) else [source]
            amount = self._to_number(rec.get(parts[0]))
            direction = str(rec.get(parts[1], "") if len(parts) > 1 else "").strip().lower()
            if direction.startswith(("c", "cr")):
                return -abs(amount)
            return abs(amount)

        raw = rec.get(source if isinstance(source, str) else source[0])
        if transform == "direct":
            return raw if raw is None else str(raw).strip()
        if transform == "to_number":
            return self._to_number(raw)
        if transform == "to_integer":
            return self._to_integer(raw)
        if transform == "to_date":
            return self._to_date(raw)
        if transform == "to_boolean":
            return str(raw).strip().lower() in ("y", "yes", "true", "1", "t")
        if transform == "map_values":
            values = params.get("values", {})
            key = str(raw).strip()
            return values.get(key, raw)
        raise ValueError(f"unsupported transform {transform}")

    @staticmethod
    def _to_number(raw: Any) -> float:
        if raw is None or raw == "":
            raise ValueError("empty number")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return float(raw)
        s = _NUMBER_JUNK.sub("", str(raw))
        negative = False
        if s.startswith("(") and s.endswith(")"):
            s, negative = s[1:-1], True
        if s.endswith("-"):
            s, negative = s[:-1], True
        value = float(s)
        return -value if negative else value

    @classmethod
    def _to_integer(cls, raw: Any) -> int:
        s = re.sub(r"(?i)^fy", "", str(raw).strip())
        return int(cls._to_number(s))

    @staticmethod
    def _to_date(raw: Any) -> str:
        s = str(raw).strip()
        for fmt in _DATE_FORMATS:
            try:
                parsed = datetime.strptime(s, fmt)
                if 1990 <= parsed.year <= 2100:
                    return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"unparseable date: {s!r}")


# ---------------------------------------------------------------------------
# Persistence: sources, mappings, sync log
# ---------------------------------------------------------------------------

class MappingStore:
    """SQLite persistence for registered sources and their mappings."""

    def __init__(self, db_path: str = MAPPING_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    source_type TEXT NOT NULL,          -- rest_api | csv | caselle | custom
                    config TEXT NOT NULL DEFAULT '{}',  -- JSON: url, auth mode, etc.
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES sources(id),
                    entity TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'proposed',  -- proposed | approved | retired
                    method TEXT NOT NULL,                     -- ai | heuristic | manual
                    mapping_json TEXT NOT NULL,
                    proposed_at TEXT NOT NULL,
                    approved_at TEXT,
                    approved_by TEXT,
                    UNIQUE(source_id, entity, version)
                );
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES sources(id),
                    entity TEXT NOT NULL,
                    mapping_id INTEGER REFERENCES mappings(id),
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    total INTEGER DEFAULT 0,
                    succeeded INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'running', -- running | ok | error
                    detail TEXT
                );
            """)

    # -- sources ------------------------------------------------------------

    def register_source(self, name: str, source_type: str,
                        config: Optional[Dict[str, Any]] = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO sources (name, source_type, config, created_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET source_type=excluded.source_type, "
                "config=excluded.config",
                (name, source_type, json.dumps(config or {}),
                 datetime.now(timezone.utc).isoformat()))
            if cur.lastrowid:
                return cur.lastrowid
            row = conn.execute("SELECT id FROM sources WHERE name=?", (name,)).fetchone()
            return row["id"]

    def list_sources(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY name").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["config"] = json.loads(d["config"])
            out.append(d)
        return out

    # -- mappings -----------------------------------------------------------

    def save_proposal(self, source_id: int, proposal: Dict[str, Any]) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS v FROM mappings "
                "WHERE source_id=? AND entity=?",
                (source_id, proposal["entity"])).fetchone()
            version = row["v"] + 1
            cur = conn.execute(
                "INSERT INTO mappings (source_id, entity, version, status, method, "
                "mapping_json, proposed_at) VALUES (?, ?, ?, 'proposed', ?, ?, ?)",
                (source_id, proposal["entity"], version, proposal["method"],
                 json.dumps(proposal), proposal["proposed_at"]))
            return cur.lastrowid

    def approve_mapping(self, mapping_id: int, approved_by: str,
                        edited_mappings: Optional[List[Dict[str, Any]]] = None) -> None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM mappings WHERE id=?",
                               (mapping_id,)).fetchone()
            if row is None:
                raise ValueError(f"mapping {mapping_id} not found")
            payload = json.loads(row["mapping_json"])
            if edited_mappings is not None:
                payload["mappings"] = edited_mappings
                payload["method"] = "manual"
            # Retire any previously approved mapping for the same source/entity
            conn.execute(
                "UPDATE mappings SET status='retired' "
                "WHERE source_id=? AND entity=? AND status='approved'",
                (row["source_id"], row["entity"]))
            conn.execute(
                "UPDATE mappings SET status='approved', approved_at=?, approved_by=?, "
                "mapping_json=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), approved_by,
                 json.dumps(payload), mapping_id))

    def get_approved_mapping(self, source_id: int, entity: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM mappings WHERE source_id=? AND entity=? AND "
                "status='approved' ORDER BY version DESC LIMIT 1",
                (source_id, entity)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["mapping_json"] = json.loads(d["mapping_json"])
        return d

    def list_mappings(self, source_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM mappings"
        args: tuple = ()
        if source_id is not None:
            query += " WHERE source_id=?"
            args = (source_id,)
        query += " ORDER BY entity, version DESC"
        with self._conn() as conn:
            rows = conn.execute(query, args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["mapping_json"] = json.loads(d["mapping_json"])
            out.append(d)
        return out

    # -- sync log -----------------------------------------------------------

    def start_sync(self, source_id: int, entity: str, mapping_id: int) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO sync_log (source_id, entity, mapping_id, started_at) "
                "VALUES (?, ?, ?, ?)",
                (source_id, entity, mapping_id,
                 datetime.now(timezone.utc).isoformat()))
            return cur.lastrowid

    def finish_sync(self, sync_id: int, result: Dict[str, Any],
                    status: str = "ok", detail: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sync_log SET finished_at=?, total=?, succeeded=?, failed=?, "
                "status=?, detail=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), result.get("total", 0),
                 result.get("succeeded", 0), result.get("failed", 0),
                 status, detail[:2000], sync_id))

    def recent_syncs(self, limit: int = 25) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT sync_log.*, sources.name AS source_name FROM sync_log "
                "JOIN sources ON sources.id = sync_log.source_id "
                "ORDER BY sync_log.id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
