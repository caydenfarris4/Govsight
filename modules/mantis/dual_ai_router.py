"""
Dual AI Router for MantisAI

Routes user prompts between Claude (Anthropic) and GPT-4o (OpenAI) based on
the nature of the question, and enables a cross-check mode where both models
review each other's answers before a final response is returned.

ROUTING PHILOSOPHY:
- Claude (claude-3-5-sonnet): Excels at code, debugging, technical explanations,
  SQL generation, step-by-step problem solving, and platform configuration help.
- GPT-4o: Excels at financial reasoning, grants knowledge, structured tool use
  (the existing function-calling tools stay on GPT), GASB compliance, and
  natural language data queries that drive chart/table outputs.
- Cross-check: Neither model is infallible. On validation requests or high-stakes
  financial questions, both models run and the secondary reviews the primary's
  answer — catching errors before they reach municipal staff.

WHY THIS SPLIT:
The GovSight orchestrator's function-calling tools (query_database, search_grants,
detect_anomalies, etc.) are built for OpenAI's function-calling spec. Those stay
entirely on GPT-4o. Claude is brought in as the technical advisor: when users
ask about code, debugging, SQL syntax, API setup, or platform configuration, they
get Claude's superior reasoning. The cross-check layer lets both models act as
sanity-checkers on each other for any question type.
"""

import os
import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routing categories
# ---------------------------------------------------------------------------

ROUTE_GPT = "gpt"          # OpenAI GPT-4o — uses full function-calling pipeline
ROUTE_CLAUDE = "claude"    # Anthropic Claude — conversational, no tool calls
ROUTE_CROSSCHECK = "crosscheck"  # Both models; secondary reviews primary


# ---------------------------------------------------------------------------
# Keyword scoring tables
# ---------------------------------------------------------------------------

# Signals that the question is primarily technical / coding-oriented
_TECHNICAL_SIGNALS = [
    # Programming / code
    "python", "code", "script", "function", "class", "method", "import",
    "module", "package", "library", "syntax", "error", "traceback", "exception",
    "debug", "bug", "fix", "broken", "doesn't work", "not working", "fails",
    "crash", "stacktrace", "stack trace",
    # SQL / database structure
    "sql", "query", "join", "select", "insert", "update", "delete", "schema",
    "migration", "table", "column", "index", "foreign key", "constraint",
    # Config / integration / deployment
    "api key", "endpoint", "config", "configure", "setup", "install",
    "deploy", "docker", "server", "port", "host", "environment variable",
    "secret", "credential", "connection string", "oauth", "auth token",
    # Platform / technical support
    "streamlit", "fastapi", "uvicorn", "replit", "workflow", "process",
    "log", "logging", "how to implement", "how do i", "how to set up",
    "import error", "module not found", "cannot import", "attribute error",
    "type error", "name error", "key error", "index error",
]

# Signals that the question is primarily financial / data / compliance
_FINANCIAL_SIGNALS = [
    "budget", "grant", "fund", "gasb", "gaap", "compliance", "revenue",
    "expenditure", "expense", "spend", "fiscal", "municipal", "city",
    "department", "appropriation", "encumbrance", "reconcil", "audit",
    "vendor", "payroll", "invoice", "purchase order", "gl", "general ledger",
    "balance sheet", "cash flow", "forecast", "projection", "scenario",
    "anomaly", "anomalies", "outlier", "trend", "variance", "performance",
    "investment", "portfolio", "bond", "treasury", "lgip", "interest",
    "tax", "levy", "assessment", "fee", "reserve", "surplus", "deficit",
    "transfer", "reallocation", "interfund", "restricted", "unrestricted",
    "debt service", "capital project", "enterprise fund", "special revenue",
    "report", "statement", "chart", "graph", "visualization", "dashboard",
]

# Signals that the user wants both models to check each other
_CROSSCHECK_SIGNALS = [
    "verify", "confirm", "double.check", "double check", "second opinion",
    "are you sure", "validate this", "check this", "cross.check", "cross check",
    "is this right", "is this correct", "make sure", "sanity check",
    "both models", "ask both", "get both", "compare", "review this answer",
    "review my", "check my", "does this look right",
]


def classify_prompt(message: str) -> Tuple[str, str, int, int]:
    """
    Score a user message and return the recommended route.

    Returns:
        (route, reason, technical_score, financial_score)

    Route is one of: ROUTE_GPT, ROUTE_CLAUDE, ROUTE_CROSSCHECK
    """
    lower = message.lower()

    # Check for cross-check intent first — it overrides the other routes
    for sig in _CROSSCHECK_SIGNALS:
        if re.search(sig, lower):
            return (
                ROUTE_CROSSCHECK,
                f"Cross-check requested (detected: '{sig}')",
                0, 0,
            )

    # Score each category
    tech_score = sum(1 for sig in _TECHNICAL_SIGNALS if sig in lower)
    fin_score = sum(1 for sig in _FINANCIAL_SIGNALS if sig in lower)

    # Claude wins if it outscores financial by a clear margin
    # (margin of 2 avoids flipping on ambiguous messages like "how do I query budget data")
    if tech_score > fin_score + 1 and tech_score >= 2:
        reason = f"Technical question (tech={tech_score}, fin={fin_score})"
        return ROUTE_CLAUDE, reason, tech_score, fin_score

    # GPT wins if financial signals are dominant or scores are close
    reason = f"Financial/data question (tech={tech_score}, fin={fin_score})"
    return ROUTE_GPT, reason, tech_score, fin_score


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

def _claude_system_prompt() -> str:
    return """You are MantisAI's technical advisor for the GovSight Financial Intelligence Platform.

GovSight is a Streamlit + Python + FastAPI application for municipal financial management.
It has three modules: Navi (planning & scenario analysis), Mantis (AI intelligence hub —
that's you), and Vatica (document management & GL analysis).

TECHNOLOGY STACK:
- Frontend: Streamlit (Python) — located in modules/core/main_app.py
- APIs: FastAPI services (modules/api/) running on ports 8000 and 5001
- Databases: SQLite (config, GL, PBB), PostgreSQL (utility, payroll), MySQL (assets)
- AI: OpenAI GPT-4o (financial reasoning), Anthropic Claude (technical support — that's you)
- Key modules: modules/services/ (ConfigService, DatabaseService, Bootstrap),
  modules/mantis/ (AI orchestration), modules/navi/ (planning tools)

YOUR ROLE:
- Answer technical questions: Python code, SQL, debugging, API integration, configuration,
  platform setup, import errors, workflow issues, and GovSight-specific technical help.
- Provide working code examples when relevant. Be specific and actionable.
- If you spot a security concern (hardcoded secrets, SQL injection, etc.), flag it clearly.
- Keep responses professional and focused. Municipal IT staff appreciate directness.
- Never use emojis. Avoid vague answers — give specific steps or code.

IMPORTANT:
- You do not have access to the municipality's live financial data in this role.
- For data queries, budget analysis, grants, or compliance questions, the user should
  ask the financial AI (GPT-4o side of MantisAI) which has those tools available.
- You CAN help write SQL queries, Python code to process data, or explain how to use
  GovSight tools — but the actual data retrieval goes through the GPT side."""


def _crosscheck_review_prompt(original_question: str, primary_model: str, primary_answer: str) -> str:
    return f"""You are acting as a second reviewer in MantisAI's cross-check system.

A user asked the following question:
"{original_question}"

The {primary_model} model provided this answer:
--- BEGIN PRIMARY ANSWER ---
{primary_answer}
--- END PRIMARY ANSWER ---

Your job:
1. Review the primary answer for accuracy, completeness, and potential errors.
2. Identify anything that is incorrect, misleading, or missing.
3. Add any important perspective the primary answer overlooked.
4. If the primary answer is fully correct, confirm it and briefly explain why you agree.

Format your response as:
REVIEW: [1-3 sentences assessing the primary answer — be direct and honest]
ADDITIONS: [Any important information the primary answer missed, or "None." if complete]
VERDICT: [Correct / Mostly correct with caveats / Needs correction]

Be concise. Municipal staff need clear, actionable information."""


# ---------------------------------------------------------------------------
# Claude caller
# ---------------------------------------------------------------------------

class ClaudeAdvisor:
    """
    Thin wrapper around the Anthropic API for technical MantisAI queries.

    WHY A SEPARATE CLASS: Keeps Claude-specific API details isolated from the
    main GPT orchestrator. The orchestrator calls ask_claude() and gets back a
    plain string — it doesn't need to know about Anthropic's SDK internals.
    """

    def __init__(self):
        self.client = None
        self.model = "claude-3-5-sonnet-20241022"
        self._init_client()

    def _init_client(self):
        """Initialize Anthropic client from environment variable."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — Claude routing unavailable")
            return
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info("Anthropic client initialised (claude-3-5-sonnet-20241022)")
        except ImportError:
            logger.error("anthropic package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")

    @property
    def available(self) -> bool:
        return self.client is not None

    def ask(self, user_message: str, system_prompt: Optional[str] = None,
            max_tokens: int = 2000) -> str:
        """
        Send a message to Claude and return the text response.
        Raises if the client is unavailable.
        """
        if not self.client:
            raise RuntimeError(
                "Anthropic client not available. "
                "Ensure ANTHROPIC_API_KEY is set in Replit Secrets."
            )

        system = system_prompt or _claude_system_prompt()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def review(self, original_question: str, primary_model: str,
               primary_answer: str, max_tokens: int = 1000) -> str:
        """
        Ask Claude to review another model's answer (cross-check role).
        """
        if not self.client:
            raise RuntimeError("Anthropic client not available for cross-check.")

        prompt = _crosscheck_review_prompt(original_question, primary_model, primary_answer)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system="You are a precise, critical reviewer. Be direct and honest.",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


# ---------------------------------------------------------------------------
# Convenience function used by the orchestrator
# ---------------------------------------------------------------------------

def get_claude_advisor() -> ClaudeAdvisor:
    """Return a shared ClaudeAdvisor instance."""
    return ClaudeAdvisor()
