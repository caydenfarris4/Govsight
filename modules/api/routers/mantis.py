"""
Mantis chat API: the SPA's chat page over the existing AI orchestrator.

The orchestrator (GPT function-calling over ~20 municipal-data tools,
dual-model routing, GASB gating) stays exactly where it is; this router
exposes it. Without an AI key configured, the endpoint degrades
honestly instead of failing.
"""

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from modules.api.routers.auth import require_user

router = APIRouter(prefix="/api/mantis", tags=["mantis"],
                   dependencies=[Depends(require_user)])

_orchestrator = None
_orchestrator_error: Optional[str] = None


def _get_orchestrator():
    global _orchestrator, _orchestrator_error
    if _orchestrator is not None or _orchestrator_error is not None:
        return _orchestrator
    try:
        from modules.mantis.mantis_ai_orchestrator import MantisAIOrchestrator
        _orchestrator = MantisAIOrchestrator()
    except Exception as exc:
        _orchestrator_error = str(exc)
    return _orchestrator


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


def _serialize_result(result: Any) -> Dict[str, Any]:
    out = {
        "type": getattr(result, "type", "text"),
        "title": getattr(result, "title", ""),
        "message": getattr(result, "message", ""),
        "tool_used": getattr(result, "tool_used", None),
        "metadata": getattr(result, "metadata", None) or {},
    }
    data = getattr(result, "data", None)
    if data is not None:
        try:
            out["data"] = {
                "columns": list(data.columns),
                "rows": data.astype(object).where(data.notna(), None)
                            .values.tolist(),
            }
        except Exception:
            out["data"] = None
    chart = getattr(result, "chart", None)
    if chart is not None:
        try:
            out["chart"] = chart.to_json()
        except Exception:
            pass
    return out


@router.get("/status")
def status():
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    return {
        "ai_available": has_openai or has_anthropic,
        "openai_configured": has_openai,
        "anthropic_configured": has_anthropic,
        "degraded_reason": None if (has_openai or has_anthropic) else
            "No AI key configured. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY "
            "on the platform to enable conversational analysis.",
    }


@router.post("/chat")
async def chat(body: ChatRequest):
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        return {
            "degraded": True,
            "result": {
                "type": "text",
                "title": "AI not configured",
                "message": "Conversational analysis needs an AI key on the "
                           "platform (OPENAI_API_KEY or ANTHROPIC_API_KEY). "
                           "The Ledger Insights tab works without one.",
            },
        }
    orchestrator = _get_orchestrator()
    if orchestrator is None:
        return {
            "degraded": True,
            "result": {"type": "error", "title": "Assistant unavailable",
                       "message": _orchestrator_error or "initialization failed"},
        }
    try:
        result = await orchestrator.process_message(
            body.message, context={}, session_id=body.session_id)
        return {"degraded": False, "result": _serialize_result(result)}
    except Exception as exc:
        return {"degraded": True,
                "result": {"type": "error", "title": "Assistant error",
                           "message": str(exc)}}
