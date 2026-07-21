"""
BI Sandbox Core - Main interface and data loading
"""

import streamlit as st
import pandas as pd
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.database.db_connection import load_org_data, format_currency, format_percentage
from modules.admin.admin_panel import get_user_departments, is_admin, is_finance_director
from .chart_builder import create_chart
from .data_processor import process_sandbox_data, apply_filters
from .export_manager import export_to_csv, generate_pdf_report

def render_bi_sandbox(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Self-Service BI Sandbox tab
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.subheader(" Self-Service BI Sandbox")
    
    st.markdown("""
    Create custom visualizations and analyze your budget data with this interactive sandbox.
    Select dimensions, apply filters, and generate charts on demand.
    """)
    
    # Load and secure data
    df = load_sandbox_data(org)
    
    if df.empty:
        st.warning(f"No data found for {org_display_name}")
        return
    
    # Apply security filters
    df = apply_security_filters(df)
    
    # Field selection interface
    render_field_selection(df)
    
    # Data filtering
    filtered_df = render_data_filters(df)
    
    # Chart creation
    render_chart_builder(filtered_df)
    
    # Saved charts management
    render_saved_charts()
    
    # Export options
    render_export_options(filtered_df)

def load_sandbox_data(org: str) -> pd.DataFrame:
    """Load data for the BI sandbox"""
    try:
        df = load_org_data(org)
        
        if df.empty:
            st.warning("No data available for analysis")
            return pd.DataFrame()
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def apply_security_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply security-based department filtering"""
    
    # Get user's allowed departments
    allowed_depts = get_user_departments()
    
    if not allowed_depts or is_admin() or is_finance_director():
        # Admin and finance directors see all data
        return df
    
    # Find department column
    dept_col = None
    for col in ['Department', 'DepartmentName', 'Dept']:
        if col in df.columns:
            dept_col = col
            break
    
    if dept_col:
        # Filter to allowed departments only
        df = df[df[dept_col].isin(allowed_depts)]
        
        if df.empty:
            st.warning("No data available for your assigned departments.")
    else:
        st.warning("Department column not found. Security filtering disabled.")
    
    return df

def render_field_selection(df: pd.DataFrame):
    """Render field selection interface"""
    st.markdown("#### Field Selection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Dimension selection (X-axis)
        dimensions = st.multiselect(
            "Select dimensions (X-axis)",
            options=df.columns.tolist(),
            default=[df.columns[0]] if not df.empty else [],
            key="sandbox_dimensions",
            help="Choose categorical fields for grouping data"
        )
    
    with col2:
        # Measure selection (Y-axis)
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        
        # Add calculated measures if both Budget and Actual exist
        measure_options = numeric_columns.copy()
        if 'Budget' in df.columns and 'Actual' in df.columns:
            measure_options.extend(['Budget - Actual', 'Actual/Budget Ratio'])
        
        value = st.selectbox(
            "Select value to measure (Y-axis)",
            options=measure_options,
            index=measure_options.index('Actual') if 'Actual' in measure_options else 0,
            key="sandbox_measure",
            help="Choose numeric field to analyze"
        )
    
    # Store selections in session state
    st.session_state.sandbox_dimensions = dimensions
    st.session_state.sandbox_measure = value

def render_data_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render data filtering interface and return filtered data"""
    st.markdown("#### Data Filters")
    
    # Create filter interface
    filter_cols = st.columns(min(3, len(df.columns)))
    
    filters = {}
    
    # Add filters for categorical columns
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    for i, col in enumerate(categorical_cols[:3]):  # Limit to 3 filters for UI space
        with filter_cols[i % len(filter_cols)]:
            unique_values = df[col].dropna().unique().tolist()
            
            selected_values = st.multiselect(
                f"Filter by {col}",
                options=unique_values,
                default=unique_values,
                key=f"filter_{col}"
            )
            
            filters[col] = selected_values
    
    # Apply filters
    filtered_df = apply_filters(df, filters)
    
    # Show filter results
    if len(filtered_df) != len(df):
        st.info(f"Showing {len(filtered_df):,} of {len(df):,} records after filtering")
    
    return filtered_df

def render_chart_builder(df: pd.DataFrame):
    """Render chart building interface"""
    st.markdown("#### Chart Builder")
    
    if df.empty:
        st.warning("No data available for charting")
        return
    
    # Get selections from session state
    dimensions = st.session_state.get('sandbox_dimensions', [])
    measure = st.session_state.get('sandbox_measure', '')
    
    if not dimensions or not measure:
        st.info("Please select dimensions and a measure above to create charts")
        return
    
    # Chart type selection
    chart_type = st.selectbox(
        "Chart Type",
        options=['Bar Chart', 'Line Chart', 'Pie Chart', 'Scatter Plot', 'Table'],
        key="chart_type"
    )
    
    # Aggregation method
    agg_method = st.selectbox(
        "Aggregation Method",
        options=['Sum', 'Average', 'Count', 'Min', 'Max'],
        key="agg_method"
    )
    
    # Create chart button
    if st.button("Create Chart", type="primary"):
        chart_config = {
            'dimensions': dimensions,
            'measure': measure,
            'chart_type': chart_type,
            'aggregation': agg_method,
            'created_at': datetime.now().isoformat()
        }
        
        chart_fig = create_chart(df, chart_config)
        
        if chart_fig:
            st.plotly_chart(chart_fig, use_container_width=True)
            
            # Save chart option
            if st.button("Save This Chart"):
                save_chart_to_session(chart_config, chart_fig)

def render_saved_charts():
    """Render saved charts management"""
    st.markdown("#### Saved Charts")
    
    if 'saved_charts' not in st.session_state:
        st.session_state.saved_charts = []
    
    if not st.session_state.saved_charts:
        st.info("No saved charts yet. Create and save charts above.")
        return
    
    # Display saved charts
    for i, chart_data in enumerate(st.session_state.saved_charts):
        with st.expander(f"Chart {i+1}: {chart_data['config']['chart_type']} - {chart_data['config']['measure']}"):
            
            # Display chart
            if 'figure' in chart_data:
                st.plotly_chart(chart_data['figure'], use_container_width=True)
            
            # Chart actions
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"Regenerate Chart {i+1}", key=f"regen_{i}"):
                    # Regenerate chart with current data
                    df = load_sandbox_data(st.session_state.get('selected_org', 'cityA'))
                    updated_fig = create_chart(df, chart_data['config'])
                    if updated_fig:
                        st.session_state.saved_charts[i]['figure'] = updated_fig
                        st.rerun()
            
            with col2:
                if st.button(f"Remove Chart {i+1}", key=f"remove_{i}"):
                    st.session_state.saved_charts.pop(i)
                    st.rerun()

def render_export_options(df: pd.DataFrame):
    """Render export and download options"""
    st.markdown("#### Export Options")
    
    if df.empty:
        st.warning("No data to export")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # CSV export
        csv_data = export_to_csv(df)
        st.download_button(
            "Download as CSV",
            data=csv_data,
            file_name=f"bi_sandbox_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # PDF report export
        if st.button("Generate PDF Report"):
            generate_sandbox_pdf_report(df)

def save_chart_to_session(config: dict, figure):
    """Save chart configuration and figure to session state"""
    if 'saved_charts' not in st.session_state:
        st.session_state.saved_charts = []
    
    chart_data = {
        'config': config,
        'figure': figure,
        'saved_at': datetime.now().isoformat()
    }
    
    st.session_state.saved_charts.append(chart_data)
    st.success(f"Chart saved! You now have {len(st.session_state.saved_charts)} saved charts.")

def generate_sandbox_pdf_report(df: pd.DataFrame):
    """Generate and offer PDF report download"""
    try:
        with st.spinner("Generating PDF report..."):
            # Get saved charts for inclusion
            charts = st.session_state.get('saved_charts', [])
            
            pdf_bytes = generate_pdf_report(df, charts)
            
            st.download_button(
                "Download PDF Report",
                data=pdf_bytes,
                file_name=f"bi_sandbox_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            
    except Exception as e:
        st.error(f"Error generating PDF report: {str(e)}")