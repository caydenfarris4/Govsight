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
from .pbb_spreadsheet import render_pbb_spreadsheet
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
    
    # Create tabs for different functions within Navi module
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Scenario Planner",
        "Economic Indicators",
        "Investment Optimizer",
        "Report Comparison",
        "Risk Analysis",
        "Position-Based Budgeting",
        "Budget Playground",
        "Predictive Analytics"
    ])
    
    with tab1:
        render_scenario_planner_html()
    
    with tab2:
        st.markdown("### Economic Indicators & Demographics Dashboard")
        st.markdown("Real-time economic data from FRED and BEA, plus demographic insights for informed budget planning")
        
        # Create sub-tabs for Economic Indicators and Demographics
        econ_tab1, econ_tab2 = st.tabs(["Economic Indicators", "Demographics & Climate"])
        
        with econ_tab1:
            try:
                # Import ML integration for economic indicators
                from modules.bi_sandbox.ml_integration import render_economic_indicators_tab
                render_economic_indicators_tab()
            except ImportError as e:
                st.error(f"Economic indicators module not available: {e}")
                st.info("External data connectors are being initialized...")
        
        with econ_tab2:
            try:
                # Import demographics integration
                from modules.navi.demographics_integration import DemographicsIntegration
                demo_engine = DemographicsIntegration()
                demo_engine.render_demographics_dashboard()
            except ImportError as e:
                st.error(f"Demographics module not available: {e}")
                st.info("Demographics integration is being initialized...")
            except Exception as e:
                st.error(f"Error loading demographics: {e}")
                st.info("Demographics includes population, zoning, and climate data analysis")
    
    with tab3:
        st.markdown("### Municipal Investment Optimizer")
        st.markdown("Optimize cash reserves through safe, accredited investment opportunities")
        
        try:
            # Use HTML/TypeScript version for enhanced functionality
            from .investment_optimizer_html_server import render_investment_optimizer_html
            render_investment_optimizer_html()
        except ImportError as e:
            st.error(f"Investment Optimizer module not available: {e}")
            st.info("Treasury and investment data APIs are being initialized...")
        except Exception as e:
            st.error(f"Error loading Investment Optimizer: {e}")
            st.info("Investment optimizer provides Treasury rates, CDARS/ICS options, and yield comparisons")
    
    with tab4:
        st.markdown("### Scenario Report Comparison")
        st.markdown("Compare multiple scenarios and generate comprehensive comparison reports")
        
        try:
            from .report_comparison import render_report_comparison_interface
            render_report_comparison_interface()
        except ImportError as e:
            st.error(f"Report comparison module not available: {e}")
            st.info("Please ensure all dependencies are installed")
    
    with tab5:
        st.markdown("### Advanced Risk Analysis")
        st.markdown("Monte Carlo simulation for comprehensive project risk assessment")
        render_monte_carlo_simulator()
    
    with tab6:
        st.markdown("### Position-Based Budgeting Workbook")
        st.markdown("Multi-sheet budgeting system with GL mapping, split allocations, and ERP export")
        
        # Version selector
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("*Enterprise-grade PBB with multi-year planning and payroll integration*")
        with col2:
            use_enhanced = st.toggle("Enhanced Version", value=True, help="Use multi-sheet enhanced PBB")
        
        try:
            if use_enhanced:
                render_enhanced_pbb()
            else:
                render_pbb_spreadsheet()
        except Exception as e:
            st.error(f"Error loading Position-Based Budgeting: {str(e)}")
            st.info("Please ensure payroll database connection is configured in Admin Panel.")
            st.markdown("""
            **Enhanced PBB Features:**
            - Multi-sheet workbook (Production + Sandbox sheets)
            - GL account mapping for ERP integration
            - Split allocations across funds/cost centers
            - Multi-year budgeting (FY 2024-2026)
            - Vacancy management and savings tracking
            - Grant-funded position tracking with expiration alerts
            - Step/grade progression with auto-calculation
            - Benefit package configuration
            - Smart payroll sync with manual override
            - CSV export by GL account for ERP import
            - Quick actions for COLA, merit increases, bulk edits
            - Position history audit trail
            """)
    
    with tab7:
        render_budget_playground_tab()

    with tab8:
        st.markdown("### Predictive Analytics Engine")
        st.markdown("Advanced ML-powered forecasting and budget optimization")
        
        try:
            # Import predictive analytics from admin module
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from modules.admin.predictive_analytics_engine import get_predictive_analytics_engine
            analytics_engine = get_predictive_analytics_engine()
            analytics_engine.render_predictive_analytics_dashboard()
        except ImportError:
            st.error("Predictive Analytics Engine not available - module loading")
            st.info("Advanced ML analytics requires all dependencies to be loaded")
        except Exception as e:
            st.error(f"Error loading Predictive Analytics Engine: {e}")
            st.info("Predictive analytics includes forecasting, budget optimization, and ML-driven insights")