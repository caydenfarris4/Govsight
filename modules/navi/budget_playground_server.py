"""
Budget Playground Server — renders the HTML tool into a Streamlit iframe.

API connectivity strategy
--------------------------
Replit only exposes port 5000 (Streamlit) to the browser. The Budget Playground
Node.js API runs internally on port 5002, unreachable from browser JS. To solve
this, we inject a lightweight reverse-proxy into Streamlit's Tornado server
(bp_proxy.py) that forwards /bp-api/* requests server-side to localhost:5002.
The HTML then calls /bp-api/* (same origin = port 5000), which works from any
browser.
"""

import os
import logging
import streamlit as st
import streamlit.components.v1 as components

log = logging.getLogger(__name__)

_HTML_PATH = os.path.join(os.path.dirname(__file__), 'budget_playground.html')

# Module-level flag so we only attempt proxy installation once per process
_proxy_attempted = False


def _ensure_proxy() -> None:
    """Install the /bp-api/* reverse proxy into Streamlit's Tornado server."""
    global _proxy_attempted
    if _proxy_attempted:
        return
    _proxy_attempted = True
    try:
        from .bp_proxy import install_proxy
        ok = install_proxy()
        if ok:
            log.info("Budget Playground proxy installed at /bp-api/*")
        else:
            log.warning("Budget Playground proxy could not be installed; API calls may fail")
    except Exception as exc:
        log.warning("Budget Playground proxy installation failed: %s", exc)


def render_budget_playground() -> None:
    """Read the Budget Playground HTML, inject the API URL, and render in iframe."""
    _ensure_proxy()

    try:
        with open(_HTML_PATH, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        st.error(f"Budget Playground HTML not found at: {_HTML_PATH}")
        return

    # Use /bp-api as the API base — same origin (port 5000), proxied server-side
    # to localhost:5002/*.  Relative path works regardless of the public
    # hostname so this is correct for both dev and deployed.
    injection = (
        '<script>\n'
        'window.BUDGET_PLAYGROUND_API_URL = "/bp-api";\n'
        '</script>\n'
    )

    html_content = html_content.replace(
        '<script type="text/babel">',
        injection + '<script type="text/babel">',
        1
    )

    components.html(html_content, height=900, scrolling=True)


def render_budget_playground_tab() -> None:
    """
    Public entry point called from navi_main.py.
    Wraps render_budget_playground() with a clear error message if anything fails.
    """
    try:
        render_budget_playground()
    except Exception as e:
        st.error(f"Budget Playground could not be loaded: {e}")
        st.info(
            "If the API backend is not running, restart the **Budget Playground API** "
            "workflow from the Replit workflow panel."
        )


__all__ = ['render_budget_playground_tab']
