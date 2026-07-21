"""
Claude Code Background Agent Service

A FastAPI service that wraps the Claude Code CLI (`claude -p ...`) and runs it
as a managed, non-interactive subprocess.  Results are persisted to SQLite so
the Streamlit dashboard can poll for status without keeping an open connection.

Port: 5001 (separate from the main app on 5000 and PBB API on 8000)

WHY FASTAPI: Lightweight async framework that lets us launch Claude Code
subprocesses without blocking the HTTP server, which is critical because some
Claude Code tasks can take 30–120 seconds to complete.
"""

import asyncio
import json
import os
import sys
import shutil
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure the workspace root is in PYTHONPATH so agent_db and tasks import cleanly
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.agent_db import create_run, update_run_status, get_runs, get_run
from agent.tasks import get_all_tasks, get_task

app = FastAPI(
    title="GovSight Claude Agent",
    description="Background agent service that runs Claude Code tasks and stores results.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Locate the claude binary; fall back to PATH lookup
CLAUDE_BIN = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")

# Maximum USD to spend per task unless overridden by the caller
DEFAULT_BUDGET_USD = 1.0


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    task_name: str = "run_tests"
    custom_prompt: Optional[str] = None
    budget_usd: float = DEFAULT_BUDGET_USD


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Core execution logic
# ---------------------------------------------------------------------------

async def _execute_claude(run_id: str, prompt: str, budget_usd: float) -> None:
    """
    Spawn Claude Code as a subprocess in non-interactive (-p) mode.

    WHY --dangerously-skip-permissions: The agent runs in a sandboxed Replit
    environment and needs to read/write files without interactive confirmation.
    This flag is appropriate here because:
      1. The container has no outbound internet access beyond approved APIs.
      2. All tasks are pre-defined or explicitly entered by an authenticated admin.
      3. The budget cap limits runaway spending.
    """
    update_run_status(run_id, "running")

    if not os.path.isfile(CLAUDE_BIN):
        update_run_status(
            run_id,
            "failed",
            error_text=f"Claude Code binary not found at {CLAUDE_BIN}. "
                       "Run: curl -fsSL https://claude.ai/install.sh | bash",
        )
        return

    cmd = [
        CLAUDE_BIN,
        "--print",
        "--dangerously-skip-permissions",
        "--output-format", "json",
        "--max-budget-usd", str(budget_usd),
        prompt,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=ROOT,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # Claude Code --output-format json returns a JSON object.
        # We extract the assistant's final text message as the summary.
        cost_usd: Optional[float] = None
        summary = ""
        output_text = stdout

        try:
            data = json.loads(stdout)
            # The JSON schema: {"type":"result","subtype":"success","result":"...","cost_usd":...}
            result_text = data.get("result", "") or ""
            cost_usd = data.get("cost_usd")
            # Build a plain-text summary (first 600 chars of the result)
            summary = result_text[:600].strip()
            output_text = result_text
        except (json.JSONDecodeError, AttributeError):
            # If JSON parsing fails, use raw stdout as the output
            summary = stdout[:600].strip() if stdout else stderr[:300].strip()
            output_text = stdout or stderr

        if proc.returncode == 0:
            update_run_status(
                run_id,
                "success",
                output_text=output_text,
                summary=summary or "Task completed.",
                cost_usd=cost_usd,
            )
        else:
            update_run_status(
                run_id,
                "failed",
                output_text=output_text,
                summary=summary,
                cost_usd=cost_usd,
                error_text=stderr[:1000] if stderr else f"Exit code {proc.returncode}",
            )

    except Exception as exc:
        update_run_status(run_id, "failed", error_text=str(exc))


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.get("/agent/health")
async def health():
    """Health check — confirms the service is running."""
    claude_available = os.path.isfile(CLAUDE_BIN)
    return {
        "status": "ok",
        "claude_bin": CLAUDE_BIN,
        "claude_available": claude_available,
    }


@app.get("/agent/tasks")
async def list_tasks():
    """Return the full pre-defined task library."""
    return {"tasks": get_all_tasks()}


@app.post("/agent/run", response_model=RunResponse)
async def trigger_run(request: RunRequest):
    """
    Enqueue and start a Claude Code task.

    - If task_name is 'custom', the custom_prompt field is used directly.
    - Otherwise, task_name must match a key in the task library.
    - The task is launched as a background asyncio task so the HTTP response
      returns immediately with the run_id for polling.
    """
    if request.task_name == "custom":
        if not request.custom_prompt or not request.custom_prompt.strip():
            raise HTTPException(status_code=400, detail="custom_prompt is required for custom tasks.")
        prompt = request.custom_prompt.strip()
        task_label = "Custom Prompt"
    else:
        try:
            task = get_task(request.task_name)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown task '{request.task_name}'. "
                       f"Valid tasks: {[t['name'] for t in get_all_tasks()]}",
            )
        prompt = task["prompt"]
        task_label = task["label"]

    budget = max(0.05, min(request.budget_usd, 10.0))  # clamp to $0.05–$10.00

    run_id = create_run(task_label, prompt)
    asyncio.create_task(_execute_claude(run_id, prompt, budget))

    return RunResponse(
        run_id=run_id,
        status="queued",
        message=f"Task '{task_label}' queued. Poll /agent/runs/{run_id} for status.",
    )


@app.get("/agent/runs")
async def list_runs(limit: int = 50):
    """Return the most recent task runs (newest first)."""
    return {"runs": get_runs(limit=limit)}


@app.get("/agent/runs/{run_id}")
async def get_run_detail(run_id: str):
    """Return full details including the complete Claude Code output."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
    return run


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent.agent_service:app", host="0.0.0.0", port=5001, reload=False)
