"""
HTML/TypeScript Investment Optimizer Server
Serves the modern HTML/TypeScript investment optimizer interface
"""

import streamlit as st
import streamlit.components.v1 as components
import os

def render_investment_optimizer_html():
    """
    Render the HTML/TypeScript Investment Optimizer
    """
    # Get the path to the HTML file
    html_path = os.path.join(os.path.dirname(__file__), 'investment_optimizer_html.html')

    # Read the HTML file
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Inject live aggregated rates and the platform API URL so the page shows
    # real, dated rates instead of its static fallback snapshot. Failures are
    # non-fatal: the page then labels itself as a static snapshot.
    injection = ""
    try:
        import json
        from modules.financial_data.investment_aggregator import get_investment_aggregator
        rates = get_investment_aggregator().get_all_opportunities()
        injection = (
            "<script>\n"
            f"window.GOVSIGHT_RATES = {json.dumps(rates)};\n"
            f"window.GOVSIGHT_API_URL = {json.dumps(os.getenv('PBB_API_URL', 'http://localhost:8000'))};\n"
            "</script>\n"
        )
    except Exception:
        pass
    if injection:
        html_content = html_content.replace("<script>", injection + "<script>", 1)

    # Render the HTML component
    components.html(html_content, height=1200, scrolling=True)
