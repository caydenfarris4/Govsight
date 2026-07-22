"""
Navi Module - Navigation and Planning Hub

This module consolidates:
- Scenario Planner: Budget scenario planning and what-if analysis
- BI Sandbox: Self-service business intelligence and data visualization

ARCHITECTURAL DECISION: Consolidating scenario planning and BI tools
WHY: These tools work together in the planning workflow - users create scenarios 
and then visualize them through BI tools for decision-making.

DESIGN PATTERN: Tabbed interface within the module for clean organization
"""

import streamlit as st
import sys
import os

# Add the root directory to the path so we can import the original modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import HTML scenario planner instead of Python version
from modules.scenario_planner.scenario_planner_html_server import render_scenario_planner_tab as render_scenario_planner_html

# BI Sandbox moved to Vatica module
from modules.utils.accessibility_helper import add_accessibility_features
from .monte_carlo_simulator import render_monte_carlo_simulator
# Legacy PBB (pbb_spreadsheet) is dormant - enhanced multisheet only
from .pbb_enhanced_multisheet import render_enhanced_pbb
from .budget_playground_server import render_budget_playground_tab

def render_navi_module(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Navi module with scenario planning and BI sandbox
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    # Add navigation back button at the very top
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back to Dashboard", key="navi_back_to_dashboard", use_container_width=True):
            st.session_state.selected_tab = "Dashboard"
            st.rerun()
    
    # Add accessibility features
    add_accessibility_features()
    
    # Module header with GovSight branding
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 8px 25px rgba(37, 99, 235, 0.25);">
        <h1 style="color: white; margin: 0; font-size: 2.5em; font-family: 'Poppins', sans-serif; font-weight: 600; letter-spacing: -0.02em;">Navi</h1>
        <p style="color: rgba(255, 255, 255, 0.9); margin: 10px 0 0 0; font-size: 1.2em; font-family: 'Poppins', sans-serif;">Navigation & Planning Hub</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Navi tab structure ────────────────────────────────────────────────
    # Focused four-tab layout: Scenario Planner stays first and prominent
    # (the market differentiator), then the three core money workflows.
    # Phase-2 tabs are hidden, not removed - flip SHOW_PHASE2_TABS to True
    # to restore them. Their capabilities remain reachable today:
    #   - Report Comparison and Risk Analysis live inside the Scenario
    #     Planner (Scenario Comparison and Monte Carlo tabs)
    #   - Predictive Analytics forecasting is covered by Budget Playground
    #     reforecasting and the Treasury cash flow projection
    #   - Economic Indicators & Demographics returns as its own tab when
    #     re-enabled
    SHOW_PHASE2_TABS = False

    tab_labels = ["Scenario Planner", "Budget", "Personnel", "Treasury"]
    if SHOW_PHASE2_TABS:
        tab_labels += ["Economic Indicators", "Report Comparison",
                       "Risk Analysis", "Predictive Analytics"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_scenario_planner_html()

    with tabs[1]:
        render_budget_playground_tab()

    with tabs[2]:
        st.markdown("### Position-Based Budgeting Workbook")
        st.markdown("Multi-sheet personnel budgeting with GL mapping, split allocations, and ERP export")

        # The enhanced multi-sheet PBB is the supported implementation; the
        # legacy spreadsheet (pbb_spreadsheet.py) is dormant and no longer
        # reachable from the UI
        try:
            render_enhanced_pbb()
        except Exception as e:
            st.error(f"Error loading Position-Based Budgeting: {str(e)}")
            st.info("Please ensure payroll database connection is configured in Admin Panel.")

    with tabs[3]:
        # Treasury: one workflow in two steps - how much cash can be
        # invested and for how long (Cash Flow), then in what instruments
        # (Investment Optimizer)
        treasury_flow, treasury_invest = st.tabs(["Cash Flow", "Investment Optimizer"])
        with treasury_flow:
            try:
                from modules.treasury.cash_flow_ui import render_cash_flow_forecast
                render_cash_flow_forecast(org, org_display_name)
            except Exception as cash_exc:
                st.error(f"Cash Flow Forecast unavailable: {cash_exc}")
        with treasury_invest:
            st.markdown("### Municipal Investment Optimizer")
            try:
                from .investment_optimizer_html_server import render_investment_optimizer_html
                render_investment_optimizer_html()
            except Exception as e:
                st.error(f"Error loading Investment Optimizer: {e}")

    if SHOW_PHASE2_TABS:
        with tabs[4]:
            st.markdown("### Economic Indicators & Demographics Dashboard")
            econ_tab1, econ_tab2 = st.tabs(["Economic Indicators", "Demographics & Climate"])
            with econ_tab1:
                try:
                    from modules.bi_sandbox.ml_integration import render_economic_indicators_tab
                    render_economic_indicators_tab()
                except ImportError as e:
                    st.error(f"Economic indicators module not available: {e}")
            with econ_tab2:
                try:
                    from modules.navi.demographics_integration import DemographicsIntegration
                    DemographicsIntegration().render_demographics_dashboard()
                except Exception as e:
                    st.error(f"Error loading demographics: {e}")

        with tabs[5]:
            st.markdown("### Scenario Report Comparison")
            try:
                from .report_comparison import render_report_comparison_interface
                render_report_comparison_interface()
            except ImportError as e:
                st.error(f"Report comparison module not available: {e}")

        with tabs[6]:
            st.markdown("### Advanced Risk Analysis")
            render_monte_carlo_simulator()

        with tabs[7]:
            st.markdown("### Predictive Analytics Engine")
            try:
                from modules.admin.predictive_analytics_engine import get_predictive_analytics_engine
                get_predictive_analytics_engine().render_predictive_analytics_dashboard()
            except Exception as e:
                st.error(f"Error loading Predictive Analytics Engine: {e}")
