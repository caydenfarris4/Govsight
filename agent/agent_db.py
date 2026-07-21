"""
Agent Database Layer

SQLite persistence for Claude Code agent task runs.
Stores the full lifecycle of every agent task: queued → running → success/failed.

WHY SQLITE: Consistent with the rest of the GovSight platform's approach to
local persistence. No extra infrastructure required and the table is small.
"""

import sqlite3
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "databases", "agent_runs.db")


def _get_connection() -> sqlite3.Connection:
    """Return a connection with row_factory set for dict-like access."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the task_runs table if it does not already exist."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_runs (
                id          TEXT PRIMARY KEY,
                task_name   TEXT NOT NULL,
                prompt_used TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'queued',
                started_at  TEXT,
                finished_at TEXT,
                output_text TEXT,
                summary     TEXT,
                cost_usd    REAL,
                error_text  TEXT,
                created_at  TEXT NOT NULL
            )
        """)
        conn.commit()


def create_run(task_name: str, prompt_used: str) -> str:
    """Insert a new run record in 'queued' status and return its UUID."""
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO task_runs (id, task_name, prompt_used, status, created_at)
            VALUES (?, ?, ?, 'queued', ?)
            """,
            (run_id, task_name, prompt_used, now),
        )
        conn.commit()
    return run_id


def update_run_status(
    run_id: str,
    status: str,
    output_text: Optional[str] = None,
    summary: Optional[str] = None,
    cost_usd: Optional[float] = None,
    error_text: Optional[str] = None,
) -> None:
    """Update a run record after execution completes or fails."""
    now = datetime.now(timezone.utc).isoformat()
    fields = ["status = ?", "finished_at = ?"]
    values: list = [status, now]

    if status == "running":
        fields = ["status = ?", "started_at = ?"]
        values = [status, now]
    else:
        if output_text is not None:
            fields.append("output_text = ?")
            values.append(output_text)
        if summary is not None:
            fields.append("summary = ?")
            values.append(summary)
        if cost_usd is not None:
            fields.append("cost_usd = ?")
            values.append(cost_usd)
        if error_text is not None:
            fields.append("error_text = ?")
            values.append(error_text)

    values.append(run_id)
    with _get_connection() as conn:
        conn.execute(
            f"UPDATE task_runs SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()


def get_runs(limit: int = 50) -> List[Dict[str, Any]]:
    """Return the most recent `limit` runs, newest first."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, task_name, status, started_at, finished_at,
                   summary, cost_usd, error_text, created_at
            FROM task_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Return all fields for a single run."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM task_runs WHERE id = ?", (run_id,)
        ).fetchone()
    return dict(row) if row else None


# Initialise the schema on import so callers never need to call init_db() manually
init_db()
