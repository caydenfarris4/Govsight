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
_orchestrator_key_state: Optional[tuple] = None


def _hydrate_keys() -> None:
    """Pull admin-configured keys from the encrypted store into os.environ.

    Cheap (one small file read), and it means keys saved through the
    management console take effect here without a platform restart.
    """
    try:
        from modules.security.api_key_manager import api_key_manager
        api_key_manager.hydrate_environment()
    except Exception:
        pass


def _key_state() -> tuple:
    return (bool(os.getenv("OPENAI_API_KEY")), bool(os.getenv("ANTHROPIC_API_KEY")))


def _get_orchestrator():
    global _orchestrator, _orchestrator_error, _orchestrator_key_state
    _hydrate_keys()
    state = _key_state()
    # Rebuild when keys appear or change - a cached keyless orchestrator
    # would otherwise stay degraded forever.
    if _orchestrator is not None and state == _orchestrator_key_state:
        return _orchestrator
    if _orchestrator_error is not None and state == _orchestrator_key_state:
        return None
    try:
        from modules.mantis.mantis_ai_orchestrator import MantisAIOrchestrator
        _orchestrator = MantisAIOrchestrator()
        _orchestrator_error = None
    except Exception as exc:
        _orchestrator = None
        _orchestrator_error = str(exc)
    _orchestrator_key_state = state
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
    _hydrate_keys()
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


def _insight_metrics() -> Dict[str, Any]:
    """Deterministic metrics for the insight narrative: department pacing
    from the pacing engine plus the latest close review summary. The AI
    writes about these numbers; it does not invent any."""
    metrics: Dict[str, Any] = {}
    try:
        from modules.api.routers.data import pacing
        metrics["pacing"] = pacing()
    except Exception as exc:
        metrics["pacing"] = {"available": False, "reason": str(exc)}
    try:
        import sqlite3
        conn = sqlite3.connect("databases/core/govsight_all_in_one_data.db")
        latest = conn.execute(
            "SELECT MAX(transaction_date) FROM canonical_transactions").fetchone()[0]
        conn.close()
        if latest:
            from modules.vatica.monthly_close_assistant import MonthlyCloseAssistant
            year, month = int(latest[:4]), int(latest[5:7])
            report = MonthlyCloseAssistant().run(year, month)
            metrics["close_review"] = {
                "period": f"{year}-{month:02d}",
                "transaction_count": report.transaction_count,
                "findings": [{"check": f.check, "severity": f.severity,
                              "message": f.message} for f in report.findings[:10]],
            }
    except Exception as exc:
        metrics["close_review"] = {"error": str(exc)}
    return metrics


@router.get("/insights")
def insights():
    """AI-written insight cards for the Ledger Insights tab. Metrics come
    from the platform engines; Claude turns them into finance-director
    narrative. Honest degraded response without an Anthropic key."""
    _hydrate_keys()
    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"ai": False,
                "reason": "ANTHROPIC_API_KEY not configured - the tab shows "
                          "engine-computed insights instead."}
    metrics = _insight_metrics()
    try:
        import anthropic
        import json as _json
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = (
            "You are a municipal finance analyst writing for a finance director. "
            "Given these platform metrics (department budget pacing and the latest "
            "monthly close review), write 3 to 5 short insight cards. Each card: a "
            "title under 10 words and a body of 2-3 sentences that cites the actual "
            "numbers, names the department or vendor involved, and says what action "
            "to consider. Only reference facts present in the data. Respond with "
            "JSON only: {\"insights\": [{\"title\": ..., \"body\": ...}]}\n\n"
            + _json.dumps(metrics, default=str)[:12000]
        )
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        # The model may emit thinking blocks before the text block
        text = "".join(b.text for b in response.content
                       if getattr(b, "type", "") == "text").strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.index("{"):text.rindex("}") + 1]
        parsed = _json.loads(text)
        cards = [c for c in parsed.get("insights", [])
                 if c.get("title") and c.get("body")][:5]
        if not cards:
            raise ValueError("model returned no insight cards")
        return {"ai": True, "model": response.model, "insights": cards}
    except Exception as exc:
        return {"ai": False, "reason": f"AI insight generation failed: {exc}"}


@router.post("/chat")
async def chat(body: ChatRequest):
    _hydrate_keys()
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
