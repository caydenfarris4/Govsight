"""
Vatica Module - Analysis and Insights Cathedral

This module consolidates:
- Historical Analysis: Multi-year budget trend analysis and forecasting
- Department Insights: Department-specific financial analysis and AI insights
- Transaction Analyzer: Detailed transaction-level analysis and anomaly detection
- Balance Sheet: Financial position and balance sheet analysis

ARCHITECTURAL DECISION: Consolidating all analytical tools
WHY: These tools represent different layers of financial analysis - from high-level 
historical trends to detailed transaction analysis. Users need seamless access 
to all analytical capabilities in one unified interface.

DESIGN PATTERN: Multi-tab interface with analytical workflow progression
"""

import streamlit as st
import sys
import os

# Add the root directory to the path so we can import the original modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.historical_analysis.historical_analysis import render_historical_analysis
from modules.department_insights.department_insights import render_department_insights
from modules.transaction_analyzer.transaction_analyzer import run_transaction_analyzer
from modules.balance_sheet.balance_sheet_position import render_balance_sheet_position
# Import accessibility features with lazy loading to avoid circular imports
def get_accessibility_features():
    from modules.utils.accessibility_helper import add_accessibility_features
    return add_accessibility_features

def render_vatica_module(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Vatica module with comprehensive analytical tools
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    # Add navigation back button at the very top
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back to Dashboard", key="vatica_back_to_dashboard", use_container_width=True):
            st.session_state.selected_tab = "Dashboard"
            st.rerun()
    
    # Add accessibility features (lazy loaded)
    try:
        add_accessibility_features = get_accessibility_features()
        add_accessibility_features()
    except Exception:
        pass  # Continue without accessibility features if import fails
    
    # Module header with GovSight branding
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 8px 25px rgba(6, 182, 212, 0.25);">
        <h1 style="color: white; margin: 0; font-size: 2.5em; font-family: 'Poppins', sans-serif; font-weight: 600; letter-spacing: -0.02em;">Vatica</h1>
        <p style="color: rgba(255, 255, 255, 0.9); margin: 10px 0 0 0; font-size: 1.2em; font-family: 'Poppins', sans-serif;">Analysis & Insights Cathedral</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for the main functions with BI Sandbox in tab 1
    tab1, tab2, tab3, tab4, tab5, tab_close, tab6 = st.tabs(["BI Sandbox", "Historical Analysis", "Department Insights", "Transaction Analyzer", "Balance Sheet", "Monthly Close", "Google Sheets Export"])

    with tab_close:
        try:
            from modules.vatica.monthly_close_assistant import render_monthly_close_tab
            render_monthly_close_tab(org, org_display_name)
        except Exception as close_exc:
            st.error(f"Monthly Close Assistant unavailable: {close_exc}")
    
    with tab1:
        st.markdown("### Enhanced BI Sandbox")
        st.markdown("Business intelligence dashboard with advanced analytics and visualization")
        
        try:
            from modules.bi_sandbox.bi_sandbox_main import render_bi_sandbox_interface
            render_bi_sandbox_interface(org, org_display_name)
        except ImportError:
            st.error("BI Sandbox module not available - module loading")
            st.info("Enhanced BI features require all dependencies to be loaded")
        except Exception as e:
            st.error(f"Error loading BI Sandbox: {e}")
            st.info("BI Sandbox includes custom visualization builder, drag-and-drop interface, and export functionality")
    
    with tab2:
        st.markdown("### Historical Budget Analysis")
        st.markdown("Analyze multi-year trends and generate forecasts")
        render_historical_analysis(org, org_display_name)
    
    with tab3:
        st.markdown("### Department Financial Insights")
        st.markdown("Department-specific analysis with AI-powered insights")
        # Get user departments for role-based access
        from modules.admin.admin_panel import get_user_departments
        departments = get_user_departments()
        render_department_insights(org, org_display_name, departments)
    
    with tab4:
        st.markdown("### Transaction-Level Analysis")
        st.markdown("Detailed transaction analysis and anomaly detection")
        run_transaction_analyzer()
    
    with tab5:
        st.markdown("### Balance Sheet Analysis")
        st.markdown("Financial position and balance sheet insights")
        render_balance_sheet_position(org, org_display_name)
    
    with tab6:
        st.markdown("### 📊 Advanced Google Sheets Export")
        st.markdown("Professional templates, batch exports, and automated reporting")
        
        # Import and render the enhanced export interface
        try:
            from .google_sheets_exporter import GoogleSheetsExporter, render_export_interface
            from .sheets_templates import render_template_selector, apply_template_to_spreadsheet
            from .enhanced_sheets_export import render_enhanced_export_interface
            from .automated_reports import render_automated_reports_interface
            
            # Set organization context for export
            st.session_state['selected_org'] = org
            st.session_state['org_display_name'] = org_display_name
            
            # Initialize exporter
            exporter = GoogleSheetsExporter()
            
            # Create sub-tabs for different export features
            export_tab1, export_tab2, export_tab3, export_tab4, export_tab5 = st.tabs([
                "Templates", "Enhanced Export", "Automated Reports", 
                "ML Export", "Basic Export"
            ])
            
            with export_tab1:
                st.markdown("#### Professional Report Templates")
                st.markdown("Select from pre-defined templates with professional formatting, formulas, and charts")
                
                # Render template selector
                selected_template = render_template_selector(exporter)
                
                if selected_template:
                    st.markdown("---")
                    st.markdown("#### Apply Template to Spreadsheet")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        spreadsheet_id = st.text_input(
                            "Enter Google Sheets ID",
                            placeholder="1abc...xyz",
                            help="The ID from the Google Sheets URL",
                            key="template_spreadsheet_id"
                        )
                    
                    with col2:
                        if st.button("Apply Template", type="primary", key="apply_template_btn"):
                            if spreadsheet_id:
                                # Load sample data based on template type
                                import pandas as pd
                                sample_data = pd.DataFrame({
                                    'Department': ['IT', 'HR', 'Finance'],
                                    'Budget': [100000, 80000, 90000],
                                    'Actual': [95000, 82000, 88000],
                                    'Variance': [5000, -2000, 2000]
                                })
                                
                                success = apply_template_to_spreadsheet(
                                    exporter, spreadsheet_id, selected_template, sample_data
                                )
                                
                                if success:
                                    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
                                    st.markdown(f"**[Open in Google Sheets]({url})**")
                            else:
                                st.error("Please enter a spreadsheet ID")
            
            with export_tab2:
                st.markdown("#### Enhanced Export Options")
                st.markdown("Batch exports, multi-sheet workbooks, and smart formatting")
                
                # Render enhanced export interface
                render_enhanced_export_interface(exporter)
            
            with export_tab3:
                st.markdown("#### Automated Report Scheduling")
                st.markdown("Schedule regular reports with automatic export to Google Sheets")
                
                # Render automated reports interface
                render_automated_reports_interface(exporter)
            
            with export_tab4:
                st.markdown("#### ML & AI Results Export")
                st.markdown("Export machine learning results with specialized formatting")
                
                # ML Export Options
                ml_export_type = st.selectbox(
                    "Select ML Export Type",
                    ["Anomaly Detection Results", "Grant Matching Results", 
                     "Economic Indicators", "RAG Statistics", "Scenario Planning"]
                )
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    ml_spreadsheet_id = st.text_input(
                        "Enter Google Sheets ID",
                        placeholder="1abc...xyz",
                        help="The ID for ML results export",
                        key="ml_spreadsheet_id"
                    )
                
                with col2:
                    if st.button("Export ML Results", type="primary", key="export_ml_btn"):
                        if ml_spreadsheet_id and exporter.service:
                            from .enhanced_sheets_export import EnhancedSheetsExporter
                            enhanced_exporter = EnhancedSheetsExporter(exporter.service)
                            
                            # Mock ML data for demonstration
                            import pandas as pd
                            import numpy as np
                            
                            if ml_export_type == "Anomaly Detection Results":
                                ml_data = pd.DataFrame({
                                    'Transaction_ID': ['T001', 'T002', 'T003'],
                                    'Amount': [10000, 25000, 50000],
                                    'anomaly_score': [0.2, 0.7, 0.9],
                                    'confidence': [0.8, 0.9, 0.95],
                                    'risk_level': ['low', 'medium', 'high'],
                                    'department': ['IT', 'Finance', 'Operations']
                                })
                                result = enhanced_exporter.export_ml_results(
                                    ml_spreadsheet_id, "anomaly_detection", ml_data
                                )
                            
                            elif ml_export_type == "Grant Matching Results":
                                ml_data = pd.DataFrame({
                                    'grant_name': ['Federal Infrastructure', 'State Education'],
                                    'match_score': [95, 88],
                                    'amount': [1000000, 500000],
                                    'deadline': pd.date_range(start='2024-03-01', periods=2, freq='M')
                                })
                                result = enhanced_exporter.export_ml_results(
                                    ml_spreadsheet_id, "grant_matching", ml_data
                                )
                            
                            elif ml_export_type == "Economic Indicators":
                                ml_data = pd.DataFrame({
                                    'indicator': ['GDP Growth', 'Inflation', 'Unemployment'],
                                    'value': [2.5, 3.2, 4.1],
                                    'benchmark': [2.0, 2.0, 4.0],
                                    'date': pd.date_range(start='2024-01-01', periods=3, freq='M')
                                })
                                result = enhanced_exporter.export_ml_results(
                                    ml_spreadsheet_id, "economic_indicators", ml_data
                                )
                            
                            elif ml_export_type == "RAG Statistics":
                                ml_data = pd.DataFrame({
                                    'document': ['Policy Doc', 'Budget Doc', 'Procedure Doc'],
                                    'content_length': [5000, 8000, 3000],
                                    'relevance_score': [0.9, 0.8, 0.7],
                                    'query_count': [10, 15, 5]
                                })
                                result = enhanced_exporter.export_ml_results(
                                    ml_spreadsheet_id, "rag_statistics", ml_data
                                )
                            
                            else:  # Scenario Planning
                                ml_data = pd.DataFrame({
                                    'scenario': ['baseline', 'optimistic', 'pessimistic'],
                                    'metric': ['Revenue', 'Revenue', 'Revenue'],
                                    'value': [1000000, 1200000, 800000]
                                })
                                result = enhanced_exporter.export_ml_results(
                                    ml_spreadsheet_id, "scenario_planning", ml_data
                                )
                            
                            if result.get('success'):
                                st.success(result.get('message', 'Export successful!'))
                                url = f"https://docs.google.com/spreadsheets/d/{ml_spreadsheet_id}"
                                st.markdown(f"**[Open in Google Sheets]({url})**")
                            else:
                                st.error(f"Export failed: {result.get('error', 'Unknown error')}")
                        else:
                            st.error("Please enter a spreadsheet ID and ensure Google Sheets is configured")
            
            with export_tab5:
                st.markdown("#### Basic Export")
                st.markdown("Standard export functionality for quick data exports")
                
                # Render original export interface
                render_export_interface()
            
        except ImportError as e:
            st.error(f"Google Sheets export modules not available: {e}")
            st.info("Please ensure all export modules are installed and configured")
            
            # Fallback to basic export if enhanced modules not available
            try:
                from .google_sheets_exporter import render_export_interface
                st.session_state['selected_org'] = org
                st.session_state['org_display_name'] = org_display_name
                render_export_interface()
            except:
                st.error("Google Sheets export functionality is not available")
                
        except Exception as e:
            st.error(f"Error loading export interface: {e}")
            import traceback
            st.text(traceback.format_exc())