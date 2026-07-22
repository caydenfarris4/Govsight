"""
GovSight Financial Analyzer

A comprehensive municipal funding scenario optimization platform that enables intelligent, 
interactive financial analysis with enhanced database connectivity and 
standardized advanced analytical capabilities.

ARCHITECTURAL DECISION: This simplified version focuses on core functionality with role-based security.
WHY: Prioritizing security and maintainability over complex features to ensure municipal data protection
and user-friendly operation for non-technical government staff.

DESIGN PHILOSOPHY:
- Modular architecture: Each major function (AI, scenarios, analytics) is separated into distinct modules
  to enable independent development, testing, and maintenance
- Security-first approach: All user interactions are authenticated and role-based to protect sensitive
  municipal financial data
- Accessibility compliance: ADA-compliant design ensures equal access for all government employees
- Multi-organization support: Built to scale across multiple municipalities with shared infrastructure
"""

import streamlit as st

# Configure Streamlit page settings FIRST - before any other imports or commands
# Note: initial_sidebar_state will be managed dynamically based on user interaction
st.set_page_config(
    page_title="GovSight Financial Analyzer",
    page_icon=None,                              # Clean professional appearance without icons
    layout="wide",                               # Wide layout to accommodate complex financial data tables
    initial_sidebar_state="collapsed"           # Start collapsed for clean interface
)
import os
import json
import base64
from urllib.parse import parse_qs
from typing import Optional

# Add root directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Bootstrap enterprise services (database-backed config, migrations, etc.)
from modules.services.bootstrap import bootstrap_services
bootstrap_services()

# Import enterprise-grade infrastructure
from modules.core.config_manager import get_config, get_config_manager
from modules.core.error_handler import get_error_handler, handle_errors, ErrorCategory
from modules.core.enhanced_logger import get_logger
from modules.core.performance_optimizer import smart_data_sampling, optimize_dataframe_memory

# Import custom modules
# WHY MODULAR IMPORTS: Each module handles a specific domain of functionality
# This separation allows for independent development, testing, and maintenance

# Security and authentication module
# Import authentication functions from the correct authentication module
from modules.admin.authentication import login, is_admin, is_finance_director, is_department_manager
from modules.admin.user_database import get_user_role, get_user_departments, init_users_db
from modules.admin.admin_panel import authorized_tabs, render_admin_panel
# WHY: Centralized authentication ensures consistent security across all features

# Database connectivity and organization management
from modules.database.connection_manager import get_org_display_info, check_password, get_selected_database
# WHY: Abstracted database layer allows switching between different municipal databases without code changes

# New 3-module consolidated structure
from modules.navi.navi_main import render_navi_module                   # Navigation & Planning Hub (Scenario Planner + BI Sandbox)
from modules.mantis.mantis_main import render_mantis_module               # Intelligence & Reporting Hub (AI Assistant + Reports)
from modules.vatica.vatica_main import render_vatica_module               # Analysis & Insights Cathedral (Historical + Department + Transaction + Balance Sheet)
from modules.utils.module_icons import get_compass_icon, get_mantis_icon, get_cathedral_icon
from modules.agent.agent_dashboard import render_agent_dashboard          # Claude Code background agent dashboard

# Accessibility and compliance module
from modules.utils.accessibility_helper import add_accessibility_features, add_accessibility_css, announce_to_screen_reader
# WHY: ADA compliance is mandatory for government applications

# Anti-scraping protection module
from modules.security.anti_scraping import protect_page, protect_sensitive_content, get_security_events
from modules.security.content_protection import display_protected_content, obfuscate_financial_data
# WHY: Municipal financial data requires protection from unauthorized automated extraction

# Code protection modules
from modules.security.code_protection import protect_function, obfuscate_string, code_obfuscator
from modules.security.runtime_protection import protected_function, start_runtime_protection, validate_environment
# WHY: Source code contains proprietary municipal financial algorithms that require protection

# Install the /bp-api/* reverse proxy into Streamlit's Tornado server at startup.
# This allows browser-side JS inside the Budget Playground iframe to reach the
# PBB API Backend (port 8000) via same-origin requests on port 5000.
try:
    from modules.navi.bp_proxy import install_proxy as _install_bp_proxy
    _install_bp_proxy()
except Exception as _bp_exc:
    pass  # Non-fatal: Budget Playground will show a connectivity error in the UI

# Initialize enterprise infrastructure
logger = get_logger("main_app")
error_handler = get_error_handler()

# Set correlation ID for request tracking
correlation_id = logger.set_correlation_id()
logger.info("Application startup", action="app_start", outcome="success")

# Initialize user database on startup (only creates default users if database is empty)
# WHY: Ensures database exists and has admin user for first-time setup
# NOTE: This only runs once on app startup and won't reset existing passwords
try:
    init_users_db()
    logger.info("User database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing user database: {e}", error_category="database")

# Get UI configuration
ui_config = get_config("ui", default={})

# Page config will be set at the very beginning of the file

# Get database configuration
db_config = get_config("database", default={})

# Set the default organization
DEFAULT_ORG = db_config.get("default_org", "cityA")  # Internal ID, display name comes from database config
# WHY DEFAULT ORG: Provides fallback when URL parameters don't specify organization
# This ensures the application always loads with valid data rather than failing
# cityA serves as the primary demo/development organization

# Image loading functions for 3D icons
def get_image_base64(image_path):
    """Convert image to base64 for embedding in HTML"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

# Load 3D icons
navi_icon_b64 = get_image_base64("logos/navi_3d.png")
mantis_icon_b64 = get_image_base64("logos/mantis_3d.png")
vatica_icon_b64 = get_image_base64("logos/vatica_3d.png")

# Enhanced CSS for modern appearance and ADA compliance
st.markdown("""
<style>
    /* Import modern fonts that match the GovSight logo aesthetic */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styling with ADA compliance and GovSight branding */
    html, body, [class*="css"] {
        font-family: 'Poppins', 'Inter', sans-serif;
        font-size: 16px; /* Minimum font size for accessibility */
        line-height: 1.6; /* Improved readability */
        color: #1a202c; /* Professional dark color */
    }
    
    /* Fix Streamlit header and viewport issues */
    .main .block-container {
        padding-top: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px !important;
        margin: 0 auto !important;
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
    
    /* Clean form styling - no background boxes */
    .stForm {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 1rem 0 !important;
    }
    
    /* Professional text input styling */
    .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 2px solid #e9ecef !important;
        padding: 12px 16px !important;
        font-size: 16px !important;
        background-color: #ffffff !important;
        transition: border-color 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }
    
    
    .stTextInput > div > div > input:focus {
        border-color: #2563eb !important;
        outline: none !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }
    
    /* Clean submit button with GovSight branding */
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-family: 'Poppins', sans-serif !important;
        font-size: 16px !important;
        font-weight: 500 !important;
        width: 100% !important;
        margin-top: 1rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
        letter-spacing: 0.01em !important;
    }
    
    .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.3) !important;
    }
    
    /* Fix alignment for all modules throughout the app */
    .stSelectbox > div > div {
        border-radius: 8px !important;
        border: 2px solid #e9ecef !important;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }
    
    /* Fix table alignment */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #e5e7eb !important;
    }
    
    /* Fix metric alignment */
    .stMetric {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }
    
    /* Enhanced tab styling with GovSight branding */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px !important;
        background: transparent !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        background: rgba(248, 250, 252, 0.8) !important;
        border: 1px solid #e2e8f0 !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.01em !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(37, 99, 235, 0.1) !important;
        border-color: #2563eb !important;
        transform: translateY(-1px) !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        border-color: #2563eb !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
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
    
    /* Header styling with GovSight branding */
    .main-header {
        font-family: 'Poppins', sans-serif;
        font-size: 2.8rem;
        font-weight: 600;
        color: #1a202c;
        padding: 1rem 0;
        text-align: center;
        outline: none;
        letter-spacing: -0.02em;
    }
    
    .main-header:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    .org-header {
        background: #4169E1;
        padding: 1.5rem 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(65, 105, 225, 0.3);
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .org-header h1 {
        margin: 0;
        font-family: 'Poppins', sans-serif;
        font-size: 2.2rem;
        font-weight: 600;
        color: #ffffff;
        outline: none;
        letter-spacing: -0.01em;
    }
    
    .org-header h1:focus {
        outline: 3px solid #FFD700;
        outline-offset: 2px;
    }
    
    .org-header h3 {
        margin: 0.5rem 0 0 0;
        font-family: 'Poppins', sans-serif;
        font-size: 1.1rem;
        font-weight: 400;
        color: rgba(255, 255, 255, 0.9);
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
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(37, 99, 235, 0.25);
        margin-bottom: 1.5rem;
        font-family: 'Poppins', sans-serif;
    }
    
    .stats-card {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.25);
        text-align: center;
        font-family: 'Poppins', sans-serif;
    }
    
    /* Enhanced global button styling with GovSight branding */
    .stButton > button {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.01em !important;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.3) !important;
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

# Keep sidebar expanded for easy navigation
# Removed auto-close functionality to improve user navigation experience
st.markdown("""
<script>
// Ensure sidebar remains visible for navigation
document.addEventListener('DOMContentLoaded', function() {
    // Function to expand sidebar if collapsed
    function expandSidebar() {
        const expandButton = document.querySelector('[data-testid="collapsedControl"]');
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        
        // If sidebar is collapsed and expand button exists, click it
        if (sidebar && sidebar.classList.contains('collapsed') && expandButton) {
            expandButton.click();
        }
    }
    
    // Check sidebar state periodically
    setInterval(expandSidebar, 1000);
    
    // Initial expansion
    setTimeout(expandSidebar, 500);
});
</script>
""", unsafe_allow_html=True)

# Add accessibility features
add_accessibility_features()
add_accessibility_css()

# Initialize runtime protection
start_runtime_protection()

# Validate execution environment
if not validate_environment():
    st.error("Application environment validation failed")
    st.stop()

# We'll let Streamlit handle the sidebar state natively
# and just use initial_sidebar_state in set_page_config

# --- Login Management ---
if not st.session_state.get('authenticated') or 'user' not in st.session_state:
    # Apply anti-scraping protection even for login page
    protect_page("login", sensitive=True)
    # Login screen in main content
    try:
        login()
        st.stop()  # Prevent fall-through during authentication
    except Exception as e:
        st.error(f"Login system error: {e}")
        st.info("Please contact support if this error persists")
        st.info("Try: admin_user / govsight123")
    st.stop()

# Parse query parameters
def get_query_params():
    """Get query parameters from the URL"""
    query_params = st.query_params
    return query_params

def get_icon_for_module(module_name):
    """Get clean text labels for each module"""
    # No icons - clean professional appearance
    return ""

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
        st.session_state.sidebar_collapsed = False  # Keep sidebar visible by default
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
    user = st.session_state.get('user', {})
    username = user.get('username', 'Unknown')
    user_role = user.get('role', 'viewer')
    st.success(f"Logged in as: {username} ({user_role})")

    # Demo data: when the admin signs in, make sure a complete linked demo
    # dataset exists so every module is exercisable immediately. Idempotent;
    # runs once per session.
    if username == 'admin_user' and not st.session_state.get('demo_data_checked'):
        try:
            from modules.services.demo_data import ensure_demo_data
            demo_status = ensure_demo_data()
            st.session_state['demo_data_checked'] = True
            st.caption(
                f"Demo data ready: {demo_status['gl_accounts']} GL accounts, "
                f"{demo_status['monthly_actuals']} monthly actuals, "
                f"{demo_status['canonical_transactions']} transactions")
        except Exception as demo_exc:
            st.session_state['demo_data_checked'] = True
            st.caption(f"Demo data check failed: {demo_exc}")
    
    # Add a logout button
    if st.button("Logout", use_container_width=True):
        for key in ['authenticated', 'username', 'user_role', 'user_departments', 'user']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    
    # Apply navigation requested by dashboard buttons BEFORE the radio is
    # instantiated: setting the widget's state here (legal pre-instantiation)
    # keeps the sidebar radio and selected_tab authoritative and in sync.
    # The previous approach (deleting the widget key) left the frontend
    # holding the stale value, which reverted navigation on the next
    # interaction anywhere in the app.
    if 'pending_nav' in st.session_state:
        pending = st.session_state.pop('pending_nav')
        if pending in allowed_tabs:
            st.session_state.selected_tab = pending
            st.session_state.main_navigation = pending

    # When a radio button is selected, update the session state
    selected_sidebar_tab = st.radio(
        "Navigation", 
        allowed_tabs, 
        index=allowed_tabs.index(st.session_state.selected_tab) if st.session_state.selected_tab in allowed_tabs else 0,
        help="Use arrow keys to navigate between sections",
        key="main_navigation"
    )
    if selected_sidebar_tab != st.session_state.selected_tab:
        st.session_state.selected_tab = selected_sidebar_tab
        # Keep sidebar open for easy navigation
        # Removed auto-close to improve navigation experience
        st.rerun()

# Always use the tab from session state
selected_tab = st.session_state.selected_tab

# Display the selected module based on tab selection
if selected_tab == "Dashboard":
    # New 3-module dashboard with large icons
    st.markdown('<div class="main-header">Welcome to GovSight Financial Analyzer</div>', unsafe_allow_html=True)
    
    user = st.session_state.get('user', {})
    user_role = user.get('role', 'viewer')
    user_depts = user.get('departments', [])
    
    # User info card at the top
    st.markdown(f"""
    <div class="info-card">
        <h3 style="margin: 0 0 1rem 0; font-size: 1.4rem;">User Information</h3>
        <div style="display: flex; gap: 2rem; align-items: center;">
            <div>
                <strong>Role:</strong> {user_role.title()}
            </div>
            <div>
                <strong>Departments:</strong> {', '.join(user_depts) if isinstance(user_depts, list) else 'All'}
            </div>
        </div>
        <p style="margin: 1rem 0 0 0; opacity: 0.9;">Select a module below to access different analytical tools.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Three-module layout with large icons
    st.markdown("""
    <style>
    /* Dashboard card button styling */
    div[data-testid="column"]:nth-child(1) .stButton > button,
    div[data-testid="column"]:nth-child(2) .stButton > button,
    div[data-testid="column"]:nth-child(3) .stButton > button {
        background-color: white !important;
        color: #4169E1 !important;
        border: none !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="column"]:nth-child(1) .stButton > button:hover,
    div[data-testid="column"]:nth-child(2) .stButton > button:hover,
    div[data-testid="column"]:nth-child(3) .stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.95) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    </style>
    <div style="text-align: center; padding: 2rem 0;">
        <h2 style="color: #1a202c; margin-bottom: 2rem; font-family: 'Poppins', sans-serif; font-weight: 600; letter-spacing: -0.01em;">Choose Your Module</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Create three perfectly centered columns for the modules
    col1, col2, col3 = st.columns([1, 1, 1], gap="large")
    
    with col1:
        # Module card for Navi
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: #4169E1; border-radius: 15px; 
                    box-shadow: 0 8px 24px rgba(65, 105, 225, 0.35); 
                    transition: all 0.3s ease; margin: 0;">
            <div style="margin-bottom: 1rem;">
                <img src="data:image/png;base64,{navi_icon_b64}" width="120" height="120" style="max-width: 120px; height: auto;" alt="Navi 3D Icon" />
            </div>
            <h3 style="color: white; margin: 0 0 0.5rem 0; font-family: 'Poppins', sans-serif; font-weight: 600;">GOVSIGHT NAVI</h3>
            <p style="color: white; margin: 0; font-family: 'Poppins', sans-serif; font-size: 0.9rem; opacity: 0.95;">Project Planner</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Enter Navi", key="navi_card", use_container_width=True, help="Access scenario planning and business intelligence tools"):
            st.session_state['pending_nav'] = "Navi"
            st.rerun()
    
    with col2:
        # Module card for Mantis
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: #4169E1; border-radius: 15px; 
                    box-shadow: 0 8px 24px rgba(65, 105, 225, 0.35); 
                    transition: all 0.3s ease; margin: 0;">
            <div style="margin-bottom: 1rem;">
                <img src="data:image/png;base64,{mantis_icon_b64}" width="120" height="120" style="max-width: 120px; height: auto;" alt="Mantis 3D Icon" />
            </div>
            <h3 style="color: white; margin: 0 0 0.5rem 0; font-family: 'Poppins', sans-serif; font-weight: 600;">GOVSIGHT MANTIS</h3>
            <p style="color: white; margin: 0; font-family: 'Poppins', sans-serif; font-size: 0.9rem; opacity: 0.95;">AI Assistant</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Enter Mantis", key="mantis_card_btn", use_container_width=True, help="Access AI assistant and intelligence reporting"):
            st.session_state['pending_nav'] = "Mantis"
            st.rerun()
    
    with col3:
        # Module card for Vatica
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: #4169E1; border-radius: 15px; 
                    box-shadow: 0 8px 24px rgba(65, 105, 225, 0.35); 
                    transition: all 0.3s ease; margin: 0;">
            <div style="margin-bottom: 1rem;">
                <img src="data:image/png;base64,{vatica_icon_b64}" width="120" height="120" style="max-width: 120px; height: auto;" alt="Vatica 3D Icon" />
            </div>
            <h3 style="color: white; margin: 0 0 0.5rem 0; font-family: 'Poppins', sans-serif; font-weight: 600;">GOVSIGHT VATICA</h3>
            <p style="color: white; margin: 0; font-family: 'Poppins', sans-serif; font-size: 0.9rem; opacity: 0.95;">Departmental Insights</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Enter Vatica", key="vatica_card", use_container_width=True, help="Access comprehensive financial analysis and insights"):
            st.session_state['pending_nav'] = "Vatica"
            st.rerun()

    # Direct admin access from the main page for administrators
    if user_role == "admin":
        st.markdown("---")
        admin_col1, admin_col2, admin_col3 = st.columns([1, 2, 1])
        with admin_col2:
            st.markdown("""
            <div style="text-align: center; padding: 1.25rem; background: #1d3a56; border-radius: 12px;
                        box-shadow: 0 6px 18px rgba(18, 38, 58, 0.25); margin-bottom: 0.5rem;">
                <h3 style="color: white; margin: 0; font-family: 'Poppins', sans-serif; font-weight: 600;">Administration</h3>
                <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0 0; font-size: 0.9rem;">User management, ERP connections, AI data mapping, and system settings</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Admin Settings", key="admin_card", use_container_width=True,
                         help="Manage users, data sources, and system configuration"):
                st.session_state['pending_nav'] = "Admin Panel"
                st.rerun()


elif selected_tab == "Navi":
    # Apply anti-scraping protection for navigation and planning data
    protect_page("navi", sensitive=True)
    render_navi_module(org, org_display_name)

elif selected_tab == "Mantis":
    # Apply anti-scraping protection for intelligence and reporting data
    protect_page("mantis", sensitive=True)
    render_mantis_module(org, org_display_name)

elif selected_tab == "Vatica":
    # Apply anti-scraping protection for analysis and insights data
    protect_page("vatica", sensitive=True)
    render_vatica_module(org, org_display_name)

elif selected_tab == "Claude Agent":
    # Claude Code background agent dashboard — restricted to admin and finance roles
    protect_page("claude_agent", sensitive=True)
    render_agent_dashboard()

elif selected_tab == "Admin Panel":
    # Apply anti-scraping protection for admin functions
    protect_page("admin_panel", sensitive=True)
    render_admin_panel()

# Enhanced Footer
st.markdown(f"""
<div class="footer">
    <h4 style="margin: 0 0 1rem 0;">GovSight Financial Analyzer</h4>
    <p style="margin: 0 0 0.5rem 0; opacity: 0.9;">Organization: {org_display_name}</p>
    <p style="margin: 0; opacity: 0.7;">© 2024 GovSight Analytics - Empowering Municipal Financial Excellence</p>
</div>
""", unsafe_allow_html=True)