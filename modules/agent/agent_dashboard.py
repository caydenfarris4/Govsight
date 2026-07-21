"""
Claude Agent Dashboard

Streamlit component for the GovSight Claude Code background agent.
Embedded as a tab in main_app.py so administrators can trigger automated
tasks and review results without leaving the platform.

WHY STREAMLIT: Reuses existing authentication and session context instead of
building a separate web UI, keeping the agent accessible but gated behind
the existing role-based access controls.
"""

import time
import requests
import streamlit as st

AGENT_API = "http://localhost:5001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api_get(path: str, timeout: int = 5):
    """GET request to the agent API; returns (data, error_str)."""
    try:
        r = requests.get(f"{AGENT_API}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Agent service is not running. Start the 'Claude Agent' workflow."
    except Exception as exc:
        return None, str(exc)


def _api_post(path: str, payload: dict, timeout: int = 10):
    """POST request to the agent API; returns (data, error_str)."""
    try:
        r = requests.post(f"{AGENT_API}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Agent service is not running. Start the 'Claude Agent' workflow."
    except Exception as exc:
        return None, str(exc)


def _status_badge(status: str) -> str:
    """Return a plain-text status label (no emojis per platform rules)."""
    labels = {
        "queued":  "[QUEUED]",
        "running": "[RUNNING]",
        "success": "[SUCCESS]",
        "failed":  "[FAILED]",
    }
    return labels.get(status, f"[{status.upper()}]")


def _format_duration(started: str, finished: str) -> str:
    """Return a human-readable duration string."""
    if not started or not finished:
        return "-"
    try:
        from datetime import datetime, timezone
        fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
        # Try with microseconds first, then without
        for f in ["%Y-%m-%dT%H:%M:%S.%f+00:00", "%Y-%m-%dT%H:%M:%S+00:00",
                  "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
            try:
                s = datetime.strptime(started, f)
                e = datetime.strptime(finished, f)
                secs = int((e - s).total_seconds())
                return f"{secs}s"
            except ValueError:
                continue
        return "-"
    except Exception:
        return "-"


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_agent_dashboard():
    """Render the full Claude Agent dashboard within the GovSight app."""

    st.markdown("## Claude Agent")
    st.markdown(
        "Run automated tasks powered by Claude Code — test execution, code review, "
        "security scans, and more. Tasks run in the background and results are stored "
        "for review."
    )

    # ------------------------------------------------------------------
    # Service health check
    # ------------------------------------------------------------------
    health, err = _api_get("/agent/health")
    if err:
        st.error(f"Agent service unavailable: {err}")
        st.info(
            "To start the agent service, go to the Replit workflow panel and start "
            "the 'Claude Agent' workflow."
        )
        return

    if not health.get("claude_available"):
        st.warning(
            f"Claude Code binary not found at `{health.get('claude_bin')}`. "
            "The service is running but cannot execute tasks until Claude Code is installed."
        )
    else:
        st.success(f"Agent service online  |  Claude Code ready at `{health.get('claude_bin')}`")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Layout: two columns — task launcher on left, history on right
    # ------------------------------------------------------------------
    left, right = st.columns([1, 2], gap="large")

    with left:
        # Fetch task list
        tasks_data, tasks_err = _api_get("/agent/tasks")
        task_list = tasks_data.get("tasks", []) if tasks_data else []

        st.markdown("### Run a Task")

        if tasks_err:
            st.error(tasks_err)
        else:
            # Task picker
            task_labels = [t["label"] for t in task_list] + ["Custom Prompt"]
            selected_label = st.selectbox(
                "Select task",
                task_labels,
                key="agent_task_select",
                help="Pre-defined tasks run a specific analysis. Custom Prompt lets you write your own instruction.",
            )

            # Find the selected task definition (None for custom)
            selected_task = next(
                (t for t in task_list if t["label"] == selected_label), None
            )

            if selected_task:
                st.caption(selected_task["description"])

            # Budget slider
            budget = st.slider(
                "Max spend per run (USD)",
                min_value=0.10,
                max_value=5.00,
                value=1.00,
                step=0.10,
                key="agent_budget_slider",
                help="Claude Code will stop if this cost cap is reached.",
            )

            # Custom prompt box (only shown when Custom Prompt is selected)
            custom_prompt = None
            if selected_label == "Custom Prompt":
                custom_prompt = st.text_area(
                    "Your instruction for Claude Code",
                    height=180,
                    key="agent_custom_prompt",
                    placeholder=(
                        "Example: Review the scenario_planner module for unused imports "
                        "and remove them, then run the tests to confirm nothing broke."
                    ),
                )

            # Run button
            if st.button("Run Task", key="agent_run_btn", use_container_width=True, type="primary"):
                if selected_label == "Custom Prompt":
                    payload = {
                        "task_name": "custom",
                        "custom_prompt": custom_prompt or "",
                        "budget_usd": budget,
                    }
                else:
                    payload = {
                        "task_name": selected_task["name"],
                        "budget_usd": budget,
                    }

                result, post_err = _api_post("/agent/run", payload)
                if post_err:
                    st.error(post_err)
                elif result:
                    st.success(f"Task queued — Run ID: `{result['run_id'][:8]}...`")
                    # Store the new run ID in session state to auto-expand it
                    st.session_state["agent_focus_run"] = result["run_id"]
                    time.sleep(0.5)
                    st.rerun()

    with right:
        st.markdown("### Run History")

        # Auto-refresh toggle
        auto_refresh = st.toggle(
            "Auto-refresh (every 15 s)",
            value=False,
            key="agent_auto_refresh",
        )

        if st.button("Refresh Now", key="agent_refresh_btn"):
            st.rerun()

        runs_data, runs_err = _api_get("/agent/runs?limit=20")
        if runs_err:
            st.error(runs_err)
        elif not runs_data or not runs_data.get("runs"):
            st.info("No tasks have been run yet. Use the panel on the left to start one.")
        else:
            runs = runs_data["runs"]

            # Highlight any running tasks
            running = [r for r in runs if r["status"] == "running"]
            if running:
                st.info(f"{len(running)} task(s) currently running...")

            for run in runs:
                badge = _status_badge(run["status"])
                duration = _format_duration(run.get("started_at"), run.get("finished_at"))
                cost_str = f"${run['cost_usd']:.4f}" if run.get("cost_usd") else "-"
                created = (run.get("created_at") or "")[:16].replace("T", " ")

                # Use an expander for each run; auto-expand the most recently triggered one
                default_open = (
                    st.session_state.get("agent_focus_run") == run["id"]
                    or run["status"] == "running"
                )
                header = f"{badge}  {run['task_name']}  |  {created}  |  {duration}  |  {cost_str}"

                with st.expander(header, expanded=default_open):
                    col_a, col_b = st.columns(2)
                    col_a.caption(f"Run ID: `{run['id'][:8]}...`")
                    col_b.caption(f"Status: {run['status']}")

                    if run.get("summary"):
                        st.markdown("**Summary**")
                        st.text(run["summary"])

                    if run.get("error_text"):
                        st.markdown("**Error**")
                        st.error(run["error_text"])

                    # Full output available via "View full output" button
                    if st.button("View full output", key=f"view_{run['id']}"):
                        full_run, full_err = _api_get(f"/agent/runs/{run['id']}")
                        if full_err:
                            st.error(full_err)
                        elif full_run and full_run.get("output_text"):
                            st.text_area(
                                "Full Claude Code Output",
                                value=full_run["output_text"],
                                height=400,
                                key=f"output_{run['id']}",
                            )
                        else:
                            st.info("No output available yet.")

        # Auto-refresh: rerun every 15 seconds if toggled on
        if auto_refresh:
            time.sleep(15)
            st.rerun()
