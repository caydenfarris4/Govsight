"""
Claude Agent Task Library

Pre-defined task prompts for the GovSight Claude Code background agent.
Each task is a dict with:
  - name: short identifier used in API calls
  - label: human-readable display name for the UI
  - description: one-line description shown in the UI
  - prompt: the full instruction sent to Claude Code via -p flag

WHY PRE-DEFINED TASKS: Gives the operations team a curated, safe set of
agent actions that are known to be useful and appropriately scoped.
Custom prompts are also supported for advanced users.
"""

from typing import Dict, List

# Root directory context injected into every prompt so Claude Code
# knows exactly what project it is working inside.
_PROJECT_CONTEXT = """
You are operating inside the GovSight Financial Intelligence Platform — a
Streamlit + Python application for municipal financial analysis.  The project
root is /home/runner/workspace.  Key directories:
  modules/          Python module tree (navi, mantis, vatica, core, services, etc.)
  agent/            Claude Code agent service (you are called from here)
  modules/testing/  Comprehensive pytest test suite
  tests/            Additional integration tests
  databases/        SQLite databases (govsight_config.db, agent_runs.db, etc.)
  pytest.ini        Test configuration (testpaths=., coverage threshold 80%)

IMPORTANT: This is a government financial system.  When editing code, preserve
all existing security controls, role-based access checks, and audit logging.
Never remove authentication guards or expose sensitive data.
"""

TASKS: List[Dict[str, str]] = [
    {
        "name": "run_tests",
        "label": "Run Test Suite",
        "description": "Execute the full pytest suite and report pass/fail counts with details on any failures.",
        "prompt": f"""{_PROJECT_CONTEXT}

TASK: Run the full test suite and report results.

Steps:
1. Run: cd /home/runner/workspace && python -m pytest modules/testing/ tests/ -v --tb=short --no-header -q 2>&1 | head -200
2. Parse the output and provide a structured summary:
   - Total tests run
   - Passed / Failed / Errors / Skipped counts
   - List each failing test with the error message (truncated to 3 lines each)
   - Overall health assessment: Healthy / Degraded / Critical
3. If there are failures, briefly identify the likely root cause for each.

Output your findings in plain text — no markdown code blocks needed.
""",
    },
    {
        "name": "review_recent_changes",
        "label": "Review Recent Changes",
        "description": "Review the last git commit for bugs, security issues, and code quality.",
        "prompt": f"""{_PROJECT_CONTEXT}

TASK: Review the most recent code changes for quality, bugs, and security issues.

Steps:
1. Run: cd /home/runner/workspace && git log --oneline -5
2. Run: cd /home/runner/workspace && git diff HEAD~1 --stat
3. Run: cd /home/runner/workspace && git diff HEAD~1 -- '*.py' | head -400
4. Analyse the diff and report:
   - Summary of what changed
   - Any potential bugs introduced
   - Any security concerns (especially around authentication, SQL queries, or secret handling)
   - Code quality observations (style, missing error handling, etc.)
   - Overall risk level: Low / Medium / High

Be specific — reference file names and line numbers from the diff.
""",
    },
    {
        "name": "fix_failing_tests",
        "label": "Fix Failing Tests",
        "description": "Run the test suite, identify failures, and attempt to fix them by editing source files.",
        "prompt": f"""{_PROJECT_CONTEXT}

TASK: Run the test suite, identify failures, and fix them.

Steps:
1. Run: cd /home/runner/workspace && python -m pytest modules/testing/ tests/ --tb=short -q 2>&1 | head -300
2. For each failing test:
   a. Read the relevant source file(s)
   b. Identify the root cause
   c. Apply the minimal fix required — do NOT refactor unrelated code
   d. Preserve all security controls and authentication checks
3. After fixing, run the test suite again to verify the fixes work.
4. Report: which tests were fixed, what changes were made, and final pass/fail counts.

If a test failure requires information you cannot determine (e.g. missing environment
variable, external service unavailable), skip that test and explain why.
""",
    },
    {
        "name": "security_scan",
        "label": "Security Scan",
        "description": "Scan security-sensitive modules for vulnerabilities, hardcoded secrets, and weak patterns.",
        "prompt": f"""{_PROJECT_CONTEXT}

TASK: Perform a security review of the GovSight codebase.

Focus areas:
1. modules/security/ — review all files for logic gaps
2. modules/admin/authentication.py — check for auth bypass risks
3. modules/core/main_app.py — verify session handling and role checks
4. modules/services/config_service.py — confirm secrets are not stored in config DB

For each file, check:
- Hardcoded credentials or API keys (should be in env vars only)
- SQL injection risks (look for string-formatted queries)
- Authentication bypass possibilities
- Sensitive data logged to console or files
- Missing input validation

Report findings as: File → Issue → Severity (Low/Medium/High/Critical) → Recommendation.
If no issues found in a file, say "Clean".
""",
    },
    {
        "name": "dependency_audit",
        "label": "Dependency Audit",
        "description": "Check pyproject.toml for outdated packages and known vulnerability patterns.",
        "prompt": f"""{_PROJECT_CONTEXT}

TASK: Audit Python dependencies for outdated versions and security concerns.

Steps:
1. Read /home/runner/workspace/pyproject.toml — list all dependencies with versions
2. Run: cd /home/runner/workspace && pip list --outdated 2>&1 | head -50
3. Cross-reference the outdated packages with the project's dependencies
4. Flag any packages with known vulnerability history (e.g. requests, pillow, cryptography, werkzeug)
5. Report:
   - Packages that are outdated AND used by this project
   - Risk level for each outdated package
   - Recommended update action

Keep the report concise — focus on actionable items only.
""",
    },
    {
        "name": "check_lsp_errors",
        "label": "Check Code Errors",
        "description": "Review Python files for import errors, undefined variables, and type issues.",
        "prompt": f"""{_PROJECT_CONTEXT}

TASK: Check the codebase for static analysis errors and fix any critical ones.

Steps:
1. Run: cd /home/runner/workspace && python -m py_compile modules/core/main_app.py 2>&1
2. Run: cd /home/runner/workspace && python -m py_compile modules/services/config_service.py modules/services/database_service.py modules/services/bootstrap.py 2>&1
3. Run: cd /home/runner/workspace && python -c "import modules.core.main_app" 2>&1 | head -30
4. Check the following files for obvious import errors by reading them:
   - modules/database/db_connection.py
   - modules/database/connection_manager.py
   - modules/bi_sandbox/database_status_ui.py
5. Report all syntax errors, import failures, and undefined names found.
6. Fix any critical errors (syntax errors, missing imports) that would prevent startup.

Report format: File → Error → Fix Applied (or "Manual review needed").
""",
    },
]

TASK_MAP: Dict[str, Dict[str, str]] = {t["name"]: t for t in TASKS}


def get_task(name: str) -> Dict[str, str]:
    """Return a task definition by name. Raises KeyError if not found."""
    return TASK_MAP[name]


def get_all_tasks() -> List[Dict[str, str]]:
    """Return the full task library."""
    return TASKS
