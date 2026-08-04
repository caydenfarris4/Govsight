"""
Per-city administrative audit log.

One clean ledger per tenant (replacing the five overlapping legacy audit
databases): who did what, to what, when, from where. Written by the
auth router (sign-ins) and every admin mutation (users, city profile,
fund policy, data sources, schedules, AI keys).
"""

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional

from modules.tenancy.context import tenant_db_path


def _conn(tenant_id: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(tenant_db_path("admin_audit.db", tenant_id))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT DEFAULT '',
            details TEXT DEFAULT '',
            ip TEXT DEFAULT ''
        )""")
    return conn


def record(actor: str, action: str, target: str = "",
           details: Optional[Dict[str, Any]] = None, ip: str = "",
           tenant_id: Optional[str] = None) -> None:
    """Append an audit event for the current (or given) tenant.

    Never raises - an audit failure must not break the action it records.
    """
    try:
        with _conn(tenant_id) as conn:
            conn.execute(
                "INSERT INTO admin_audit (ts, actor, action, target, details, ip) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (int(time.time()), actor, action, target,
                 json.dumps(details or {}, default=str)[:4000], ip))
            conn.commit()
    except Exception:
        pass


def query(limit: int = 100, action: str = "", actor: str = "",
          tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM admin_audit WHERE 1=1"
    args: list = []
    if action:
        sql += " AND action = ?"; args.append(action)
    if actor:
        sql += " AND actor = ?"; args.append(actor)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(int(limit), 1000)))
    with _conn(tenant_id) as conn:
        rows = conn.execute(sql, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["details"] = json.loads(d["details"]) if d["details"] else {}
        except Exception:
            pass
        out.append(d)
    return out


def distinct_actions(tenant_id: Optional[str] = None) -> List[str]:
    with _conn(tenant_id) as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT action FROM admin_audit ORDER BY action")]
