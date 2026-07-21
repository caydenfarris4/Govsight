"""
GovSight Financial Analyzer

A comprehensive municipal funding scenario optimization platform that enables intelligent, 
interactive financial analysis with enhanced database connectivity and 
standardized advanced analytical capabilities.

This simplified version focuses on core functionality with role-based security.
"""

import streamlit as st
import os
import json
from urllib.parse import parse_qs

# Import custom modules
from modules.admin.admin_panel import login, authorized_tabs, get_user_role, get_user_departments, is_admin, is_finance_director, is_department_manager, run_admin_panel
from db_connection import get_org_display_info, check_password, get_selected_database 
from scenario_planner import render_scenario_planner
from historical_analysis import render_historical_analysis
from department_insights import render_department_insights
from ai_assistant import render_ai_assistant
from bi_sandbox import render_bi_sandbox
from balance_sheet_position import render_balance_sheet_position
from transaction_analyzer import run_transaction_analyzer
from accessibility_helper import add_accessibility_features, add_accessibility_css, announce_to_screen_reader

# Set page config
st.set_page_config(
    page_title="GovSight Financial Analyzer",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"  # Start with sidebar collapsed
)

# Set the default organization
DEFAULT_ORG = "cityA"

# Enhanced CSS for modern appearance and ADA compliance
st.markdown("""
<style>
    /* Import modern fonts with accessibility considerations */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styling with ADA compliance and smooth transitions */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        font-size: 16px; /* Minimum font size for accessibility */
        line-height: 1.5; /* Improved readability */
    }
    
    /* Fix Streamlit header and viewport issues */
    .main .block-container {
        padding-top: 5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: none !important;
    }
    
    /* Remove default Streamlit header spacing that causes cutoff */
    header[data-testid="stHeader"] {
        height: 0px !important;
        display: none !important;
    }
    
    /* Ensure proper spacing for all content */
    .stApp > header {
        display: none !important;
    }
    
    /* Fix chart spacing */
    .stPlotlyChart {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Simplified chart containers */
    .js-plotly-plot, .plotly {
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #e5e7eb !important;
        background: white !important;
        margin: 16px 0 !important;
    }
    
    .js-plotly-plot:hover, .plotly:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    
    /* Enhanced dataframe styling */
    .stDataFrame > div {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #e5e7eb !important;
        background: white !important;
    }
    
    /* Remove problematic container styling that creates empty boxes */
    .element-container {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Apply styling only to specific content containers */
    .stDataFrame, .stMetric {
        background: white !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        border: 1px solid #f1f3f4 !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    .stDataFrame:hover, .stMetric:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Simplified chart styling - single container */
    .stPlotlyChart {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 16px 0 !important;
        box-shadow: none !important;
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        .main-header, .org-header, .ai-response, .insight-section {
            background: #000000 !important;
            color: #ffffff !important;
            border: 2px solid #ffffff !important;
        }
    }
    
    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Header styling with ADA compliant contrast ratios */
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        color: #003080; /* High contrast color for accessibility */
        padding: 1rem 0;
        text-align: center;
        outline: none;
    }
    
    .main-header:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    .org-header {
        background: #003080; /* Solid color with WCAG AA compliance */
        padding: 1.5rem 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        margin-bottom: 2rem;
        border: 2px solid #ffffff;
    }
    
    .org-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 600;
        color: #ffffff;
        outline: none;
    }
    
    .org-header h1:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    .org-header h3 {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        font-weight: 400;
        color: #ffffff;
        outline: none;
    }
    
    /* Card-based layouts */
    .dashboard-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .dashboard-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
    }
    
    .info-card {
        background: linear-gradient(135deg, #4169E1 0%, #87CEEB 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(65, 105, 225, 0.3);
        margin-bottom: 1.5rem;
    }
    
    .stats-card {
        background: linear-gradient(135deg, #87CEEB 0%, #4169E1 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(135, 206, 235, 0.3);
        text-align: center;
    }
    
    /* ADA compliant button styling */
    .stButton > button {
        background: #003080; /* High contrast background */
        color: white;
        border: 2px solid #003080;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        font-size: 16px; /* Minimum touch target size */
        min-height: 44px; /* WCAG AA touch target minimum */
        min-width: 44px;
        transition: all 0.2s ease;
        cursor: pointer;
        outline: none;
    }
    
    .stButton > button:hover {
        background: #0056CC;
        border-color: #0056CC;
        transform: none; /* Remove transform for accessibility */
    }
    
    .stButton > button:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
        background: #0056CC;
    }
    
    .stButton > button:active {
        background: #002060;
        border-color: #002060;
    }
    
    /* Disabled button state */
    .stButton > button:disabled {
        background: #cccccc;
        color: #666666;
        border-color: #cccccc;
        cursor: not-allowed;
    }
    
    /* ADA compliant quick link buttons */
    .quick-link-btn {
        background: white;
        border: 2px solid #003080;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.2s ease;
        cursor: pointer;
        min-height: 100px;
        min-width: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: #003080;
        font-weight: 500;
        outline: none;
    }
    
    .quick-link-btn:hover {
        border-color: #0056CC;
        background: #f0f8ff;
        color: #003080;
        transform: none; /* Remove transform for accessibility */
    }
    
    .quick-link-btn:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
        background: #f0f8ff;
    }
    
    .quick-link-btn:active {
        background: #e6f3ff;
        border-color: #002060;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    /* ADA compliant tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f8f9fa;
        border-radius: 12px;
        padding: 0.5rem;
        border: 2px solid #dee2e6;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #003080;
        font-weight: 500;
        min-height: 44px;
        padding: 0.75rem 1rem;
        border: 2px solid transparent;
        outline: none;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #e9ecef;
        border-color: #003080;
    }
    
    .stTabs [data-baseweb="tab"]:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    .stTabs [aria-selected="true"] {
        background: #003080;
        color: white;
        border-color: #003080;
    }
    
    .stTabs [aria-selected="true"]:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    /* Enhanced metrics */
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border-left: 4px solid #004AAD;
        margin-bottom: 1rem;
    }
    
    /* ADA compliant AI response styling */
    .ai-response {
        background: #003080;
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #ffffff;
        margin: 1rem 0;
        font-size: 16px;
        line-height: 1.6;
    }
    
    .insight-section {
        background: #003080;
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #ffffff;
        margin-bottom: 1.5rem;
        font-size: 16px;
        line-height: 1.6;
    }
    
    /* Focus states for interactive sections */
    .ai-response:focus-within,
    .insight-section:focus-within {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    /* ADA compliant Success/Info styling */
    .stSuccess {
        background: #d4edda;
        color: #155724;
        border: 2px solid #c3e6cb;
        border-radius: 8px;
        font-weight: 500;
    }
    
    .stInfo {
        background: #d1ecf1;
        color: #0c5460;
        border: 2px solid #bee5eb;
        border-radius: 8px;
        font-weight: 500;
    }
    
    .stWarning {
        background: #fff3cd;
        color: #856404;
        border: 2px solid #ffeaa7;
        border-radius: 8px;
        font-weight: 500;
    }
    
    .stError {
        background: #f8d7da;
        color: #721c24;
        border: 2px solid #f5c6cb;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Footer styling */
    .footer {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-top: 3rem;
    }
    
    /* Radio button styling */
    .stRadio > div {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
    
    /* ADA compliant form and input styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
        font-size: 16px;
        min-height: 44px;
        border: 2px solid #003080;
        border-radius: 4px;
        padding: 8px 12px;
        outline: none;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus,
    .stTextArea > div > div > textarea:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
        border-color: #0056CC;
    }
    
    /* Data editor styling with accessibility */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 2px solid #dee2e6;
        font-size: 16px;
    }
    
    /* Ensure table headers are clearly defined */
    .stDataFrame table th {
        background: #f8f9fa;
        color: #003080;
        font-weight: 600;
        border: 1px solid #dee2e6;
        padding: 12px 8px;
        text-align: left;
    }
    
    .stDataFrame table td {
        border: 1px solid #dee2e6;
        padding: 8px;
        font-size: 15px;
    }
    
    /* Skip navigation link for screen readers */
    .skip-nav {
        position: absolute;
        top: -40px;
        left: 6px;
        background: #003080;
        color: white;
        padding: 8px;
        text-decoration: none;
        border-radius: 4px;
        z-index: 1000;
    }
    
    .skip-nav:focus {
        top: 6px;
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    /* Improved radio button and checkbox styling */
    .stRadio > div {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        border: 2px solid #dee2e6;
    }
    
    .stCheckbox > label {
        font-size: 16px;
        min-height: 44px;
        display: flex;
        align-items: center;
    }
    
    /* Ensure sufficient color contrast for all text */
    .stMarkdown, .stText {
        color: #212529;
        line-height: 1.6;
    }
    
    /* High contrast for links */
    a {
        color: #0056CC;
        text-decoration: underline;
    }
    
    a:hover, a:focus {
        color: #003080;
        outline: 2px solid #FFD700;
        outline-offset: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Add accessibility features
add_accessibility_features()
add_accessibility_css()

# We'll let Streamlit handle the sidebar state natively
# and just use initial_sidebar_state in set_page_config

# --- Login Management ---
if "user" not in st.session_state:
    # Login screen in main content
    login()
    st.stop()

# Parse query parameters
def get_query_params():
    """Get query parameters from the URL"""
    query_params = st.query_params
    return query_params

def get_icon_for_module(module_name):
    """Get an appropriate icon for each module"""
    icons = {
        "Scenario Planner": "⚖️",
        "Department Insights": "",
        "AI Assistant": "",
        "Historical Analysis": "",
        "BI Sandbox": "",
        "Balance Sheet": "💼",
        "Dashboard": "🏠",
        "Reports": "",
        "Transaction Analyzer": "",
        "Admin Panel": "⚙️"
    }
    return icons.get(module_name, "")

# Load organization information
query_params = get_query_params()
org = query_params.get("org", DEFAULT_ORG)

# We're handling the sidebar collapse directly in the security_manager now

# Get organization display info
org_info = get_org_display_info(org)
org_display_name = org_info["name"]
org_theme_color = org_info["theme_color"]

# --- Tabs setup based on user role ---
allowed_tabs = authorized_tabs()

# Add skip navigation and accessibility landmarks
st.markdown("""
<a href="#main-content" class="skip-nav">Skip to main content</a>
<div id="main-content" role="main" aria-label="Main application content">
""", unsafe_allow_html=True)

# Main application interface - Enhanced header with logo
col1, col2 = st.columns([1, 3])

with col1:
    # Display the GovSight logo
    try:
        st.image("govsight_logo.png", width=200)
    except:
        # Fallback if logo file is not found
        st.markdown("### GovSight")

with col2:
    st.markdown(f"""
    <div class="org-header" role="banner" aria-label="Organization header">
        <div>
            <h1 tabindex="0" aria-label="Financial Analyzer main heading">Financial Analyzer</h1>
            <h3 tabindex="0" aria-label="Organization: {org_display_name}">Organization: {org_display_name}</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Initialize all required session state variables
def initialize_session_state():
    """Initialize all required session state variables with safe defaults"""
    if "selected_tab" not in st.session_state:
        st.session_state.selected_tab = "Dashboard"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "sidebar_collapsed" not in st.session_state:
        st.session_state.sidebar_collapsed = False
    if "login_attempted" not in st.session_state:
        st.session_state.login_attempted = False
    if "data_cache" not in st.session_state:
        st.session_state.data_cache = {}

# Initialize session state
initialize_session_state()

# Always put content in the sidebar and let Streamlit handle collapsing it
with st.sidebar:
    # Simple divider at the top of sidebar
    st.markdown("---")
    
    # Add the logout information
    st.success(f"Logged in as: {st.session_state.user['username']} ({st.session_state.user['role']})")
    
    # Add a logout button
    if st.button("Logout", use_container_width=True):
        del st.session_state["user"]
        st.rerun()
    
    st.markdown("---")
    
    # When a radio button is selected, update the session state
    selected_sidebar_tab = st.radio(
        "📂 Navigation", 
        allowed_tabs, 
        index=allowed_tabs.index(st.session_state.selected_tab) if st.session_state.selected_tab in allowed_tabs else 0,
        help="Use arrow keys to navigate between sections",
        key="main_navigation"
    )
    if selected_sidebar_tab != st.session_state.selected_tab:
        st.session_state.selected_tab = selected_sidebar_tab
        st.rerun()

# Always use the tab from session state
selected_tab = st.session_state.selected_tab

# Display the selected module based on tab selection
if selected_tab == "Dashboard":
    # Enhanced dashboard with modern card layout
    st.markdown('<div class="main-header">Welcome to GovSight Dashboard</div>', unsafe_allow_html=True)
    
    user_role = get_user_role()
    user_depts = get_user_departments()
    
    # User info card at the top
    st.markdown(f"""
    <div class="info-card">
        <h3 style="margin: 0 0 1rem 0; font-size: 1.4rem;">👤 User Information</h3>
        <div style="display: flex; gap: 2rem; align-items: center;">
            <div>
                <strong>Role:</strong> {user_role.title()}
            </div>
            <div>
                <strong>Departments:</strong> {', '.join(user_depts) if isinstance(user_depts, list) else 'All'}
            </div>
        </div>
        <p style="margin: 1rem 0 0 0; opacity: 0.9;">Use the sidebar navigation or quick links below to access different modules.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick access section
    st.markdown("""
    <div class="dashboard-card">
        <h3 style="margin: 0 0 1.5rem 0; color: #1a202c; font-size: 1.5rem;"> Quick Access</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Create enhanced grid of module buttons
    num_cols = 3
    module_buttons = []
    
    for tab in allowed_tabs:
        if tab != "Dashboard":
            module_buttons.append({"name": tab, "icon": get_icon_for_module(tab)})
    
    # Display buttons in rows with enhanced styling
    rows = [module_buttons[i:i+num_cols] for i in range(0, len(module_buttons), num_cols)]
    
    for row in rows:
        cols = st.columns(num_cols)
        for i, module in enumerate(row):
            if i < len(cols):
                with cols[i]:
                    # Create custom styled button using HTML/CSS
                    button_key = f"quicklink_{module['name'].replace(' ', '_')}"
                    st.markdown(f"""
                    <div style="margin-bottom: 1rem;">
                        <div class="quick-link-btn" onclick="alert('Use sidebar navigation')">
                            <div style="font-size: 2rem; margin-bottom: 0.5rem;">{module['icon']}</div>
                            <div style="font-weight: 500;">{module['name']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Keep functional button but make it invisible
                    if st.button(f"Go to {module['name']}", key=button_key, use_container_width=True):
                        st.session_state.selected_tab = module['name']
                        st.rerun()
    
    # Add feature highlights
    st.markdown("""
    <div class="dashboard-card">
        <h3 style="margin: 0 0 1.5rem 0; color: #1a202c; font-size: 1.5rem;">✨ Platform Features</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
            <div class="stats-card">
                <h4 style="margin: 0 0 0.5rem 0;">AI-Powered Analysis</h4>
                <p style="margin: 0; opacity: 0.9;">Advanced financial insights and recommendations</p>
            </div>
            <div class="stats-card">
                <h4 style="margin: 0 0 0.5rem 0;">Real-time Scenarios</h4>
                <p style="margin: 0; opacity: 0.9;">Dynamic funding scenario modeling</p>
            </div>
            <div class="stats-card">
                <h4 style="margin: 0 0 0.5rem 0;">Comprehensive Reports</h4>
                <p style="margin: 0; opacity: 0.9;">Detailed analytics and visualizations</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif selected_tab == "Scenario Planner":
    # Use the updated scenario planner with security features
    from scenario_planner import run_scenario_planner
    run_scenario_planner()

elif selected_tab == "Historical Analysis":
    # First try to use the secured version with role-based access
    try:
        from historical_analysis import run_historical_analysis
        run_historical_analysis()
    except (ImportError, AttributeError):
        # Fallback to the original version if the secured version is not available
        render_historical_analysis(org, org_display_name)

elif selected_tab == "Department Insights":
    departments = get_user_departments()
    render_department_insights(org, org_display_name, departments)

elif selected_tab == "BI Sandbox":
    # First try to use the secured version with role-based access
    try:
        from bi_sandbox import run_bi_sandbox
        run_bi_sandbox()
    except (ImportError, AttributeError):
        # Fallback to the original version if the secured version is not available
        render_bi_sandbox(org, org_display_name)

elif selected_tab == "Balance Sheet":
    render_balance_sheet_position(org, org_display_name)

elif selected_tab == "AI Assistant":
    render_ai_assistant(org, org_display_name)


elif selected_tab == "Reports":
    try:
        from summary_report_generator import run_report_generator
        run_report_generator()
    except ImportError as e:
        st.error(f"Report generator module is not available: {e}")
        st.info("Please ensure summary_report_generator.py exists.")


elif selected_tab == "Transaction Analyzer":
    try:
        run_transaction_analyzer()
    except Exception as e:
        st.error(f"Transaction Analyzer module encountered an error: {e}")
        st.info("Please ensure the transaction data is available in the database.")

elif selected_tab == "Admin Panel":
    try:
        from modules.admin.admin_panel import run_admin_panel
        run_admin_panel()
    except ImportError as e:
        st.error(f"Admin panel module is not available: {e}")
        st.info("Please ensure admin_panel.py exists.")

# Enhanced Footer
st.markdown(f"""
<div class="footer">
    <h4 style="margin: 0 0 1rem 0;">GovSight Financial Analyzer</h4>
    <p style="margin: 0 0 0.5rem 0; opacity: 0.9;">Organization: {org_display_name}</p>
    <p style="margin: 0; opacity: 0.7;">© 2024 GovSight Analytics - Empowering Municipal Financial Excellence</p>
</div>
""", unsafe_allow_html=True)