"""
Scenario Planner HTML Server Module

This module serves the HTML/TypeScript scenario planner interface.
It replaces the Python-based implementation with a modern React-based frontend
that communicates with the FastAPI backend.
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import json
import sqlite3
import requests
import time
from typing import Dict, Any

def render_scenario_planner():
    """
    Render the HTML/TypeScript scenario planner interface.
    This function serves the React-based scenario planner with 4 tabs:
    1. Scenario & Grants
    2. Legislative Impact
    3. What-If Simulator
    4. Monte Carlo
    """
    
    # Strip all Streamlit padding/chrome so the iframe sits flush in the tab.
    # The tab-content and vertical-block selectors remove the gap that Streamlit
    # injects between the tab bar and the iframe, eliminating the "boxed" look.
    st.markdown("""
    <style>
        .main > div {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            max-width: none !important;
        }
        [data-testid="stTabsContent"] > div,
        [data-testid="stTabsContent"] > div > div,
        [data-testid="stVerticalBlock"] {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            gap: 0 !important;
        }
        iframe {
            display: block;
            border: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if API is running
    api_status = check_api_status()
    if not api_status:
        st.error("⚠️ The PBB API Backend is not running. Please wait while it starts...")
        with st.spinner("Connecting to PBB API..."):
            # Retry connection a few times
            for i in range(5):
                time.sleep(2)
                if check_api_status():
                    st.success("✅ Connected to PBB API!")
                    st.rerun()
                    return
        
        st.error("❌ Could not connect to PBB API. Please refresh the page.")
        if st.button("Retry Connection"):
            st.rerun()
        return
    
    # Get the path to the HTML file
    html_file_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "scenario_planner_html",
        "scenario_planner.html"
    )
    
    # Check if HTML file exists
    if not os.path.exists(html_file_path):
        st.error("Scenario Planner HTML file not found. Please ensure the file exists at: " + html_file_path)
        return
    
    # Read the HTML content
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Inject server-resolved values so the browser JS never has to guess them.
    # Both the API URL and the current user identity are injected this way because
    # window.location inside the iframe reflects the Streamlit host, not port 8000,
    # and st.session_state is only available server-side.
    api_url = get_api_base_url()

    # Derive a clean display name from the username (e.g. "admin_user" → "Admin User")
    user = st.session_state.get('user', {})
    raw_username = user.get('username', '') or ''
    user_role = user.get('role', '') or ''
    display_name = ' '.join(w.capitalize() for w in raw_username.replace('_', ' ').split()) if raw_username else 'Anonymous'

    # Load real GL account data from the database and inject it into the page.
    # This gives the What-If Simulator access to actual revenue/expense accounts
    # for keyword matching, without requiring any API call from within the iframe.
    gl_accounts_json = json.dumps(load_gl_accounts())

    injection = (
        f'<script>\n'
        f'window.GOVSIGHT_API_URL = "{api_url}";\n'
        f'window.GOVSIGHT_USER = {{ name: "{display_name}", role: "{user_role}", username: "{raw_username}" }};\n'
        f'window.GOVSIGHT_GL_ACCOUNTS = {gl_accounts_json};\n'
        f'</script>\n'
    )
    html_content = html_content.replace(
        '<script type="text/babel">',
        injection + '<script type="text/babel">',
        1
    )

    # height=950 with scrolling=True gives a usable viewport without making the
    # Streamlit page excessively tall. The iframe handles its own internal scroll.
    components.html(
        html_content,
        height=950,
        scrolling=True
    )

def load_gl_accounts() -> dict:
    """
    Load GL account data from the local database and return it grouped by type.
    This is injected server-side into the HTML page so the What-If Simulator can
    perform keyword matching against real account names without any API call.
    Falls back to a representative dataset if the database is unavailable.
    """
    db_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'databases', 'core', 'govsight_all_in_one_data.db'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'attached_assets', 'govsight_all_in_one_data.db'),
    ]

    accounts = {'revenue': [], 'expense': [], 'asset': []}

    for db_path in db_paths:
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path, timeout=3)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT account_number, account_name, account_type, department, budget_amount, ytd_actual "
                "FROM gl_accounts ORDER BY account_type, budget_amount DESC"
            )
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                number, name, acct_type, dept, budget, actual = row
                entry = {
                    'number': number or '',
                    'name': name or '',
                    'type': acct_type or '',
                    'department': dept or '',
                    'budget': budget or 0,
                    'actual': actual or 0,
                }
                t = (acct_type or '').lower()
                if t == 'revenue':
                    accounts['revenue'].append(entry)
                elif t == 'expense':
                    accounts['expense'].append(entry)
                else:
                    accounts['asset'].append(entry)
            if accounts['revenue'] or accounts['expense']:
                return accounts
        except Exception:
            pass

    # Fallback dataset that includes utility/IT accounts matching the data center scenario
    accounts['revenue'] = [
        {'number': '1000-4000', 'name': 'Police - Tax Revenue',              'type': 'Revenue', 'department': 'Police',               'budget': 5000000, 'actual': 4375000},
        {'number': '1100-4000', 'name': 'Fire - Tax Revenue',                'type': 'Revenue', 'department': 'Fire',                 'budget': 3920000, 'actual': 3430000},
        {'number': '1200-4000', 'name': 'Public Works - Tax Revenue',        'type': 'Revenue', 'department': 'Public Works',         'budget': 3400000, 'actual': 2975000},
        {'number': '1300-4000', 'name': 'Parks & Recreation - Tax Revenue',  'type': 'Revenue', 'department': 'Parks & Recreation',   'budget': 2080000, 'actual': 1820000},
        {'number': '1400-4000', 'name': 'Administration - Tax Revenue',      'type': 'Revenue', 'department': 'Administration',       'budget': 1400000, 'actual': 1225000},
        {'number': '1600-4000', 'name': 'IT Services - Utility Revenue',     'type': 'Revenue', 'department': 'IT Services',          'budget': 1280000, 'actual': 1120000},
        {'number': '1601-4000', 'name': 'Data Center Hosting Revenue',       'type': 'Revenue', 'department': 'IT Services',          'budget': 1024000, 'actual': 896000},
        {'number': '1500-4000', 'name': 'Finance - Tax Revenue',             'type': 'Revenue', 'department': 'Finance',              'budget': 1120000, 'actual': 980000},
        {'number': '1800-4000', 'name': 'Planning & Development - Revenue',  'type': 'Revenue', 'department': 'Planning & Development','budget': 960000, 'actual': 840000},
        {'number': '4100-4500', 'name': 'Utility Enterprise Fund Revenue',   'type': 'Revenue', 'department': 'Utilities',            'budget': 8500000, 'actual': 7650000},
        {'number': '4200-4500', 'name': 'Parking Revenue',                   'type': 'Revenue', 'department': 'Parking',              'budget': 720000,  'actual': 648000},
        {'number': '4300-4500', 'name': 'Permit & License Fees',             'type': 'Revenue', 'department': 'Planning',             'budget': 540000,  'actual': 486000},
        {'number': '4400-4500', 'name': 'Sales Tax Revenue',                 'type': 'Revenue', 'department': 'Finance',              'budget': 12000000,'actual': 10800000},
    ]
    accounts['expense'] = [
        {'number': '1000-5100', 'name': 'Police - Salaries & Wages',         'type': 'Expense', 'department': 'Police',               'budget': 6562500, 'actual': 4921875},
        {'number': '1100-5100', 'name': 'Fire - Salaries & Wages',           'type': 'Expense', 'department': 'Fire',                 'budget': 5488000, 'actual': 4116000},
        {'number': '1200-5100', 'name': 'Public Works - Labor',              'type': 'Expense', 'department': 'Public Works',         'budget': 2800000, 'actual': 2450000},
        {'number': '1600-5200', 'name': 'IT Services - Operations',          'type': 'Expense', 'department': 'IT Services',          'budget': 980000,  'actual': 882000},
        {'number': '1601-5200', 'name': 'Data Center - Maintenance',         'type': 'Expense', 'department': 'IT Services',          'budget': 250000,  'actual': 200000},
        {'number': '1601-5300', 'name': 'Data Center - Server Costs',        'type': 'Expense', 'department': 'IT Services',          'budget': 120000,  'actual': 100000},
        {'number': '1601-5400', 'name': 'Data Center - Utilities',           'type': 'Expense', 'department': 'IT Services',          'budget': 85000,   'actual': 72000},
        {'number': '4100-5100', 'name': 'Utility Operations - Labor',        'type': 'Expense', 'department': 'Utilities',            'budget': 3200000, 'actual': 2880000},
        {'number': '4100-5200', 'name': 'Utility Operations - Maintenance',  'type': 'Expense', 'department': 'Utilities',            'budget': 1400000, 'actual': 1260000},
        {'number': '9000-5900', 'name': 'Contingency / Emergency Reserve',   'type': 'Expense', 'department': 'Finance',              'budget': 500000,  'actual': 0},
    ]
    return accounts


def get_api_base_url() -> str:
    """
    Get the correct API base URL based on the environment.
    
    Returns:
        str: API base URL
    """
    # Check if running in Replit deployment
    import os
    
    # Check for deployment-specific environment variable
    repl_deployment = os.getenv('REPL_DEPLOYMENT')
    repl_slug = os.getenv('REPL_SLUG', 'govsight')
    
    if repl_deployment == '1':
        # Production deployment - use the .replit.app domain with port 8000
        return f"https://{repl_slug}.replit.app:8000"
    
    # Check if running in Replit dev environment
    repl_id = os.getenv('REPL_ID')
    if repl_id:
        # Development environment - use localhost
        return "http://localhost:8000"
    
    # Default to localhost for local development
    return "http://localhost:8000"

def check_api_status() -> bool:
    """
    Check if the PBB API is running and accessible.
    
    Returns:
        bool: True if API is running, False otherwise
    """
    try:
        api_url = get_api_base_url()
        response = requests.get(f"{api_url}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def render_scenario_planner_tab():
    """
    Main entry point for the Scenario Planner tab in the Streamlit app.
    All wrapper chrome (header, divider, expander) is intentionally omitted so
    the HTML app fills the tab seamlessly without a double-scroll box effect.
    """
    render_scenario_planner()

# Export the main rendering function
__all__ = ['render_scenario_planner_tab']