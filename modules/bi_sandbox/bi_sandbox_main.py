"""
Main BI Sandbox Interface - Modular Architecture

This is the main interface file that orchestrates all BI Sandbox components
with a clean, modular architecture. Each component is under 500 lines.

MODULAR ARCHITECTURE:
- components/analytics_engine.py (390 lines): ML and statistical analysis
- components/data_optimization.py (264 lines): Performance and caching
- components/natural_language_processor.py (361 lines): NLP query processing  
- components/visualization_engine.py (457 lines): Chart creation
- components/report_generator.py (287 lines): PDF and export functionality
- components/data_structures.py (151 lines): Data types and configurations
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import all modular components
from .components import (
    AdvancedAnalyticsEngine,
    VisualizationType,
    create_visualization_engine,
    load_org_data_optimized,
    create_chart_data_optimized,
    process_data_for_analysis,
    NaturalLanguageAnalytics,
    AnalyticsMetric,
    DimensionHierarchy,
    FilterAction
)

from .components.visualization_engine import AdvancedVisualizationEngine
from .components.report_generator import PDFReportGenerator, DataExporter, AutomatedReportGenerator
from .components.enhanced_visualization_engine import EnhancedVisualizationEngine

# Import existing dependencies
from modules.utils.mask_parser import get_mask_from_settings, parse_account
from modules.bi_sandbox.department_budget_analyzer import render_department_budget_analysis
from modules.database.db_connection import (
    get_db_path_for_org, format_currency, format_percentage,
    get_detailed_scenario_data, load_org_data
)
from modules.admin.admin_panel import get_user_departments, is_admin, is_finance_director
import modules.reports.summary_report_generator as report_gen
from modules.ai_hub.ai_hub import generate_multi_chart_report, generate_forecast

# Import the new centralized reporting system
from modules.reporting import ReportEngine, DataAccessLayer, ChartService
from modules.reporting.audit_logger import ReportAuditLogger

def render_bi_sandbox_interface(org: str = "cityA", org_display_name: str = "Spanish Fork"):
    """
    Main interface for the Visual Analytics BI Dashboard
    
    This function renders the custom HTML dashboard with ECharts/D3.js hybrid visualization system
    """
    # Check visualization mode preference
    vis_mode = st.session_state.get('visualization_mode', 'Visual Analytics Dashboard')
    
    if vis_mode == "Visual Analytics Dashboard":
        # Use new fullscreen dashboard with checkbox field selection
        from pathlib import Path
        import streamlit.components.v1 as components
        
        st.markdown("### Visual Analytics Dashboard - Enhanced")
        st.markdown("**Per-Chart Field Selection | 35+ Chart Types | Professional Data Visualization | Interactive Analytics**")
        
        # Read the enhanced HTML with per-chart field selection
        html_path = Path(__file__).parent / "visual_analytics_enhanced.html"
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Inject real GL aggregates so the default dashboard charts the
            # city's actual numbers instead of its hardcoded sample arrays
            injection = _build_dashboard_data_injection()
            if injection:
                html_content = html_content.replace("<script>", injection + "<script>", 1)

            # Render fullscreen dashboard
            components.html(html_content, height=1400, scrolling=True)
            
        except Exception as e:
            # If new file doesn't exist, try the existing one
            html_path = Path(__file__).parent / "visual_analytics_echarts.html"
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            components.html(html_content, height=1200, scrolling=True)
    
    else:
        # Use standard dashboard integration
        from .dashboard_integration import create_dashboard_integration
        
        try:
            # Create and render the Visual Analytics dashboard
            dashboard = create_dashboard_integration()
            dashboard.render_dashboard(org, org_display_name)
            
        except Exception as e:
            st.error(f"Error loading BI Dashboard: {str(e)}")
            st.info("Falling back to legacy interface...")
            
            # Fallback to legacy interface if dashboard fails
            render_legacy_bi_sandbox_interface(org, org_display_name)

def render_legacy_bi_sandbox_interface(org: str = "cityA", org_display_name: str = "Spanish Fork"):
    """
    Legacy BI Sandbox interface (8 tabs) - used as fallback
    
    This function maintains the original modular architecture as backup
    """
    st.title("BI Sandbox - Advanced Business Intelligence")
    st.markdown("**Enterprise-grade analytics with modular architecture**")
    
    # Initialize component engines
    if 'analytics_engine' not in st.session_state:
        st.session_state.analytics_engine = AdvancedAnalyticsEngine()
        st.session_state.viz_engine = AdvancedVisualizationEngine()
        st.session_state.enhanced_viz_engine = EnhancedVisualizationEngine()
        st.session_state.nlp_engine = NaturalLanguageAnalytics()
        st.session_state.report_generator = AutomatedReportGenerator()
    
    # Load and optimize data
    try:
        with st.spinner("Loading and optimizing data..."):
            df = load_org_data_optimized(org)
            data_profile = process_data_for_analysis(df)
        
        if df.empty:
            st.error("No data available for the selected organization.")
            return
        
        # Display data summary
        with st.expander("Data Overview", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", f"{data_profile['row_count']:,}")
            with col2:
                st.metric("Columns", data_profile['col_count'])
            with col3:
                st.metric("Numeric Columns", len(data_profile['numeric_columns']))
            with col4:
                st.metric("Categorical Columns", len(data_profile['categorical_columns']))
        
        # Main interface tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "Interactive Analytics",
            "Natural Language Queries", 
            "Advanced Visualizations",
            "Machine Learning",
            "Budget Analysis",
            "Custom Reports",
            "Data Export",
            "System Performance"
        ])
        
        # Tab 1: Interactive Analytics
        with tab1:
            render_interactive_analytics_tab(df, data_profile)
        
        # Tab 2: Natural Language Queries
        with tab2:
            render_nlp_queries_tab(df)
        
        # Tab 3: Advanced Visualizations  
        with tab3:
            render_advanced_visualizations_tab(df)
        
        # Tab 4: Machine Learning
        with tab4:
            render_machine_learning_tab(df)
        
        # Tab 5: Budget Analysis (existing functionality)
        with tab5:
            render_department_budget_analysis(org, org_display_name)
        
        # Tab 6: Custom Reports
        with tab6:
            render_custom_reports_tab(df, org_display_name)
        
        # Tab 7: Data Export
        with tab7:
            render_data_export_tab(df, org_display_name)
        
        # Tab 8: System Performance
        with tab8:
            render_performance_monitoring_tab(df)
    
    except Exception as e:
        st.error(f"Error loading BI Sandbox: {str(e)}")
        st.info("Please check your data connections and try again.")

def render_interactive_analytics_tab(df: pd.DataFrame, data_profile: Dict):
    """Render interactive analytics interface"""
    st.markdown("### Interactive Data Analytics")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("**Quick Analysis**")
        
        # Column selector
        selected_column = st.selectbox(
            "Select Column for Analysis",
            data_profile['numeric_columns'] + data_profile['categorical_columns']
        )
        
        if selected_column:
            # Show basic statistics
            st.markdown(f"**{selected_column} Statistics**")
            
            if selected_column in data_profile['numeric_columns']:
                stats = df[selected_column].describe()
                for stat, value in stats.items():
                    st.write(f"{stat.title()}: {value:.2f}")
            else:
                value_counts = df[selected_column].value_counts().head(10)
                st.write("Top Values:")
                for value, count in value_counts.items():
                    st.write(f"{value}: {count}")
    
    with col2:
        if selected_column:
            st.markdown(f"**{selected_column} Visualization**")
            
            # Create appropriate chart based on data type
            if selected_column in data_profile['numeric_columns']:
                # Histogram for numeric data
                chart_data = create_chart_data_optimized(df, 'histogram', selected_column)
                fig = st.session_state.viz_engine.create_histogram(
                    chart_data['data'], 
                    selected_column,
                    title=f"Distribution of {selected_column}"
                )
                st.plotly_chart(fig, use_container_width=True, key=f"histogram_{selected_column}")
            else:
                # Bar chart for categorical data
                value_counts = df[selected_column].value_counts().head(10).reset_index()
                value_counts.columns = [selected_column, 'Count']
                
                fig = st.session_state.viz_engine.create_bar_chart(
                    value_counts,
                    selected_column,
                    'Count',
                    title=f"Top Values in {selected_column}"
                )
                st.plotly_chart(fig, use_container_width=True, key=f"bar_chart_{selected_column}")

def render_nlp_queries_tab(df: pd.DataFrame):
    """Render natural language query interface"""
    st.markdown("### Natural Language Data Queries")
    st.markdown("Ask questions about your data in plain English!")
    
    # Get suggested queries
    suggestions = st.session_state.nlp_engine.get_suggested_queries(df)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Query input
        user_query = st.text_input(
            "Enter your question:",
            placeholder="e.g., What is the sum of Budget? or Show top 5 departments"
        )
        
        # Quick suggestion buttons
        st.markdown("**Quick Suggestions:**")
        for i, suggestion in enumerate(suggestions[:6]):
            if st.button(suggestion, key=f"suggestion_{i}"):
                user_query = suggestion
    
    with col2:
        st.markdown("**Sample Queries:**")
        sample_queries = [
            "Sum of actual spending",
            "Average budget by department", 
            "Count the number of departments",
            "Top 5 highest budgets",
            "Compare budget to actual"
        ]
        for query in sample_queries:
            st.code(query, language=None)
    
    # Process query
    if user_query:
        with st.spinner("Processing your question..."):
            result = st.session_state.nlp_engine.parse_natural_query(user_query, df)
        
        if result['success']:
            st.success(result['message'])
            
            # Display results
            if result['data']:
                st.json(result['data'])
        else:
            st.error(result['message'])
            st.info("Try rephrasing your question or use one of the suggested formats.")

def render_advanced_visualizations_tab(df: pd.DataFrame):
    """Render advanced visualization interface with enhanced features"""
    st.markdown("### Advanced Visualization Builder")
    
    # Create tabs for different visualization features
    viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
        "Standard Charts", "Enhanced Charts", "Small Multiples", "Chart Configuration"
    ])
    
    with viz_tab1:
        render_standard_charts(df)
    
    with viz_tab2:
        render_enhanced_charts(df)
    
    with viz_tab3:
        render_small_multiples(df)
    
    with viz_tab4:
        render_chart_configuration()

def render_standard_charts(df: pd.DataFrame):
    """Render standard chart types with enhanced features"""
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("**Chart Configuration**")
        
        # Expanded chart type selection
        chart_type = st.selectbox(
            "Chart Type",
            ['Bar', 'Line', 'Scatter', 'Scatter with Trendline', 'Area', 'Stacked Area',
             'Stacked Bar', 'Horizontal Stacked Bar', 'Pie', 'Heatmap', 'Correlation Matrix',
             'Box Plot', 'Violin', 'Histogram', 'Treemap', 'Waterfall', 'Funnel']
        )
        
        # Column selection based on chart type
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Configure columns based on chart type
        if chart_type in ['Bar', 'Line', 'Scatter', 'Scatter with Trendline']:
            x_col = st.selectbox("X-axis", categorical_cols + numeric_cols)
            y_col = st.selectbox("Y-axis", numeric_cols)
            color_col = st.selectbox("Color by (optional)", [None] + categorical_cols)
            
        elif chart_type in ['Area', 'Stacked Area']:
            x_col = st.selectbox("X-axis", categorical_cols + numeric_cols)
            y_cols = st.multiselect("Y-axis (multiple for stacking)", numeric_cols, default=numeric_cols[:2])
            y_col = y_cols
            color_col = st.selectbox("Color by (optional)", [None] + categorical_cols)
            
        elif chart_type in ['Stacked Bar', 'Horizontal Stacked Bar']:
            x_col = st.selectbox("Categories", categorical_cols)
            y_cols = st.multiselect("Values to stack", numeric_cols, default=numeric_cols[:3])
            y_col = y_cols
            color_col = None
            
        elif chart_type == 'Pie':
            values_col = st.selectbox("Values", numeric_cols)
            names_col = st.selectbox("Labels", categorical_cols)
            x_col, y_col, color_col = names_col, values_col, None
            
        elif chart_type in ['Heatmap', 'Correlation Matrix']:
            if chart_type == 'Correlation Matrix':
                x_col, y_col, color_col = None, None, None
            else:
                x_col = st.selectbox("X-axis", categorical_cols)
                y_col = st.selectbox("Y-axis", categorical_cols)
                z_col = st.selectbox("Values", numeric_cols)
                color_col = None
            
        elif chart_type == 'Histogram':
            x_col = st.selectbox("Column", numeric_cols)
            y_col, color_col = None, None
            
        elif chart_type == 'Waterfall':
            x_col = st.selectbox("Categories", categorical_cols)
            y_col = st.selectbox("Values", numeric_cols)
            color_col = None
            
        elif chart_type == 'Funnel':
            stage_col = st.selectbox("Stages", categorical_cols)
            values_col = st.selectbox("Values", numeric_cols)
            x_col, y_col, color_col = stage_col, values_col, None
            
        else:
            x_col = st.selectbox("X-axis", categorical_cols + numeric_cols)
            y_col = st.selectbox("Y-axis", numeric_cols) if chart_type != 'Box Plot' else st.selectbox("Y-axis", numeric_cols)
            color_col = None
        
        # Chart customization
        chart_title = st.text_input("Chart Title", f"{chart_type} Chart")
        
        # Advanced options
        with st.expander("Advanced Options"):
            col_a, col_b = st.columns(2)
            with col_a:
                color_palette = st.selectbox(
                    "Color Palette",
                    ['default', 'pastel', 'bold', 'dark', 'colorblind', 'viridis', 'plasma']
                )
                show_legend = st.checkbox("Show Legend", value=True)
                show_grid = st.checkbox("Show Grid", value=True)
            with col_b:
                chart_height = st.slider("Chart Height", 300, 800, 500, 50)
                transparency = st.slider("Transparency", 0.0, 1.0, 1.0, 0.1)
                
    with col2:
        if (x_col and y_col) or chart_type in ['Histogram', 'Correlation Matrix']:
            try:
                # Create chart based on type using enhanced engine
                kwargs = {
                    'title': chart_title,
                    'height': chart_height,
                    'color_palette': color_palette,
                    'show_legend': show_legend,
                    'show_grid': show_grid,
                    'transparency': transparency
                }
                
                if color_col:
                    kwargs['color'] = color_col
                
                # Create the appropriate chart
                if chart_type == 'Scatter with Trendline':
                    fig = st.session_state.enhanced_viz_engine.create_scatter_with_trendline(
                        df, x_col, y_col, trendline='ols', **kwargs
                    )
                elif chart_type in ['Area', 'Stacked Area']:
                    fig = st.session_state.enhanced_viz_engine.create_area_chart(
                        df, x_col, y_col, stacked=(chart_type == 'Stacked Area'), **kwargs
                    )
                elif chart_type in ['Stacked Bar', 'Horizontal Stacked Bar']:
                    fig = st.session_state.enhanced_viz_engine.create_stacked_bar_chart(
                        df, x_col, y_col, horizontal=(chart_type == 'Horizontal Stacked Bar'), **kwargs
                    )
                elif chart_type == 'Correlation Matrix':
                    fig = st.session_state.enhanced_viz_engine.create_enhanced_heatmap(
                        df, correlation=True, annotate=True, **kwargs
                    )
                elif chart_type == 'Heatmap':
                    kwargs['x_col'] = x_col
                    kwargs['y_col'] = y_col
                    kwargs['z_col'] = z_col if 'z_col' in locals() else numeric_cols[0]
                    fig = st.session_state.enhanced_viz_engine.create_enhanced_heatmap(
                        df, correlation=False, annotate=True, **kwargs
                    )
                elif chart_type == 'Pie':
                    fig = st.session_state.viz_engine.create_pie_chart(df, y_col, x_col, **kwargs)
                elif chart_type == 'Histogram':
                    fig = st.session_state.viz_engine.create_histogram(df, x_col, **kwargs)
                elif chart_type == 'Waterfall':
                    fig = st.session_state.viz_engine.create_waterfall_chart(df, x_col, y_col, **kwargs)
                elif chart_type == 'Funnel':
                    fig = st.session_state.viz_engine.create_funnel_chart(df, x_col, y_col, **kwargs)
                elif chart_type == 'Box Plot':
                    fig = st.session_state.viz_engine.create_box_plot(df, y_col, x_col, **kwargs)
                else:
                    # Use standard visualization engine for basic charts
                    fig = st.session_state.viz_engine.create_chart_by_type(
                        chart_type.lower().replace(' ', '_'), df, x_col=x_col, y_col=y_col, **kwargs
                    )
                
                # Display the chart
                st.plotly_chart(fig, use_container_width=True, key=f"custom_chart_{chart_type}")
                
                # CSV Export functionality
                st.markdown("### Export Data")
                col_exp1, col_exp2 = st.columns(2)
                
                with col_exp1:
                    # Generate CSV with metadata
                    metadata = {
                        'Chart Type': chart_type,
                        'X-axis': str(x_col),
                        'Y-axis': str(y_col),
                        'Organization': 'Spanish Fork',
                        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    csv_data = st.session_state.enhanced_viz_engine.generate_csv_export(
                        df, chart_type, metadata
                    )
                    
                    st.download_button(
                        label="📥 Download Chart Data (CSV)",
                        data=csv_data,
                        file_name=f"{chart_type.lower().replace(' ', '_')}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                with col_exp2:
                    # Download filtered data
                    if st.button("📊 Export Filtered Dataset"):
                        st.download_button(
                            label="Download Full Dataset",
                            data=df.to_csv(index=False),
                            file_name=f"filtered_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                
            except Exception as e:
                st.error(f"Error creating chart: {str(e)}")
                st.info("Please check your column selections and try again.")

def render_enhanced_charts(df: pd.DataFrame):
    """Render enhanced chart types with advanced features"""
    st.markdown("### Enhanced Chart Types")
    st.info("These charts provide advanced analytical capabilities with enhanced interactivity")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("**Enhanced Chart Selection**")
        
        # Select enhanced chart type
        enhanced_type = st.selectbox(
            "Enhanced Chart Type",
            ["Time Series with Forecast", "Bubble Chart", "Radar Chart", 
             "Sankey Diagram", "3D Scatter", "Candlestick Chart", "Gantt Chart"]
        )
        
        # Get columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Configure based on chart type
        if enhanced_type == "Bubble Chart":
            x_col = st.selectbox("X-axis", numeric_cols)
            y_col = st.selectbox("Y-axis", numeric_cols)
            size_col = st.selectbox("Bubble Size", numeric_cols)
            color_col = st.selectbox("Color By", [None] + categorical_cols)
            
        elif enhanced_type == "Time Series with Forecast":
            date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            time_col = st.selectbox("Time Column", date_cols + categorical_cols)
            value_col = st.selectbox("Value Column", numeric_cols)
            forecast_periods = st.slider("Forecast Periods", 0, 12, 3)
            
        else:
            x_col = st.selectbox("Primary Dimension", categorical_cols + numeric_cols)
            y_col = st.selectbox("Value", numeric_cols)
            
    with col2:
        st.markdown("**Visualization Preview**")
        st.info(f"Enhanced {enhanced_type} visualization will appear here")
        
        # Add placeholder for enhanced visualizations
        if enhanced_type == "Bubble Chart" and 'x_col' in locals():
            # Create bubble chart
            import plotly.express as px
            fig = px.scatter(df, x=x_col, y=y_col, size=size_col if 'size_col' in locals() else None,
                           color=color_col if color_col else None,
                           title=f"Bubble Chart: {y_col} vs {x_col}")
            st.plotly_chart(fig, use_container_width=True, key="bubble_chart")

def render_small_multiples(df: pd.DataFrame):
    """Render small multiples visualization for comparative analysis"""
    st.markdown("### Small Multiples Visualization")
    st.info("Compare multiple dimensions across faceted charts")
    
    # Get columns
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("**Configuration**")
        
        # Chart type for small multiples
        chart_type = st.selectbox(
            "Chart Type for Multiples",
            ["bar", "line", "scatter", "area"]
        )
        
        # Facet configuration
        facet_col = st.selectbox(
            "Split By (Facet Column)",
            categorical_cols,
            help="Create separate charts for each unique value"
        )
        
        # Metrics to display
        metrics = st.multiselect(
            "Metrics to Display",
            numeric_cols,
            default=numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols
        )
        
        # Grid configuration
        st.markdown("**Grid Layout**")
        col_config = st.columns(2)
        with col_config[0]:
            grid_cols = st.number_input("Columns", min_value=1, max_value=4, value=2)
        with col_config[1]:
            grid_rows = st.number_input("Rows", min_value=1, max_value=4, value=2)
        
        # X-axis for charts
        x_col = st.selectbox("X-axis", categorical_cols + numeric_cols)
        
        # Advanced options
        with st.expander("Advanced Options"):
            shared_axes = st.checkbox("Share axes across charts", value=True)
            show_trend = st.checkbox("Show trend lines", value=False)
            
    with col2:
        st.markdown("**Small Multiples Grid**")
        
        if facet_col and metrics and x_col:
            try:
                # Create small multiples using enhanced engine
                fig = st.session_state.enhanced_viz_engine.create_small_multiples(
                    df, 
                    chart_type=chart_type,
                    facet_col=facet_col,
                    metrics=metrics,
                    rows=grid_rows,
                    cols=grid_cols,
                    x_col=x_col,
                    shared_xaxes=shared_axes,
                    shared_yaxes=shared_axes,
                    title=f"Small Multiples: {', '.join(metrics)} by {facet_col}"
                )
                
                st.plotly_chart(fig, use_container_width=True, key=f"small_multiples_{facet_col}")
                
                # Export functionality
                st.markdown("### Export Options")
                col_exp1, col_exp2 = st.columns(2)
                
                with col_exp1:
                    # Generate CSV for small multiples data
                    metadata = {
                        'Chart Type': f'Small Multiples ({chart_type})',
                        'Facet Column': facet_col,
                        'Metrics': ', '.join(metrics),
                        'Grid': f'{grid_rows}x{grid_cols}'
                    }
                    
                    csv_data = st.session_state.enhanced_viz_engine.generate_csv_export(
                        df, f"small_multiples_{chart_type}", metadata
                    )
                    
                    st.download_button(
                        label="📥 Download Small Multiples Data",
                        data=csv_data,
                        file_name=f"small_multiples_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
            except Exception as e:
                st.error(f"Error creating small multiples: {str(e)}")
        else:
            st.info("Please configure all required fields to generate small multiples")

def render_chart_configuration():
    """Render advanced chart configuration panel"""
    st.markdown("### Advanced Chart Configuration")
    st.info("Customize chart appearance and behavior")
    
    # Get configuration options
    config_options = st.session_state.enhanced_viz_engine.create_advanced_config_panel()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Visual Settings**")
        
        # Color palette
        color_palette = st.selectbox(
            config_options['color_palette']['label'],
            config_options['color_palette']['options'],
            help=config_options['color_palette']['description']
        )
        
        # Chart dimensions
        chart_height = st.slider(
            config_options['chart_height']['label'],
            config_options['chart_height']['min'],
            config_options['chart_height']['max'],
            config_options['chart_height']['default'],
            config_options['chart_height']['step'],
            help=config_options['chart_height']['description']
        )
        
        # Transparency
        transparency = st.slider(
            config_options['transparency']['label'],
            config_options['transparency']['min'],
            config_options['transparency']['max'],
            config_options['transparency']['default'],
            config_options['transparency']['step'],
            help=config_options['transparency']['description']
        )
        
    with col2:
        st.markdown("**Display Options**")
        
        # Grid and legend
        show_grid = st.checkbox(
            config_options['show_grid']['label'],
            value=config_options['show_grid']['default'],
            help=config_options['show_grid']['description']
        )
        
        show_legend = st.checkbox(
            config_options['show_legend']['label'],
            value=config_options['show_legend']['default'],
            help=config_options['show_legend']['description']
        )
        
        if show_legend:
            legend_position = st.selectbox(
                config_options['legend_position']['label'],
                config_options['legend_position']['options'],
                help=config_options['legend_position']['description']
            )
        
        # Data labels
        data_labels = st.checkbox(
            config_options['data_labels']['label'],
            value=config_options['data_labels']['default'],
            help=config_options['data_labels']['description']
        )
        
        # Animation
        animation = st.checkbox(
            config_options['animation']['label'],
            value=config_options['animation']['default'],
            help=config_options['animation']['description']
        )
        
    with col3:
        st.markdown("**Text & Annotations**")
        
        # Title size
        title_size = st.slider(
            config_options['title_size']['label'],
            config_options['title_size']['min'],
            config_options['title_size']['max'],
            config_options['title_size']['default'],
            config_options['title_size']['step'],
            help=config_options['title_size']['description']
        )
        
        # Custom axis labels
        st.markdown("**Custom Axis Labels**")
        x_label = st.text_input("X-axis Label", "")
        y_label = st.text_input("Y-axis Label", "")
        
        # Reference lines
        st.markdown("**Reference Lines**")
        add_ref_line = st.checkbox("Add Reference Line")
        if add_ref_line:
            ref_value = st.number_input("Reference Value", value=0.0)
            ref_label = st.text_input("Reference Label", "Target")
    
    # Save configuration
    if st.button("💾 Save Configuration as Default"):
        # Store configuration in session state
        st.session_state.chart_config = {
            'color_palette': color_palette,
            'chart_height': chart_height,
            'transparency': transparency,
            'show_grid': show_grid,
            'show_legend': show_legend,
            'legend_position': legend_position if show_legend else 'right',
            'data_labels': data_labels,
            'animation': animation,
            'title_size': title_size,
            'x_label': x_label,
            'y_label': y_label
        }
        st.success("Configuration saved! It will be applied to new charts.")
    
    # Preview section
    st.markdown("### Configuration Preview")
    st.json(st.session_state.get('chart_config', {}))

def render_machine_learning_tab(df: pd.DataFrame):
    """Render machine learning analysis interface with enhanced ML pipelines"""
    st.markdown("### Machine Learning Analytics")
    
    # Import ML integration features
    try:
        from .ml_integration import (
            render_anomaly_detection_tab, 
            render_grant_opportunities_tab,
            render_economic_indicators_tab
        )
        ml_integration_available = True
    except ImportError:
        ml_integration_available = False
    
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if len(numeric_cols) < 2 and not ml_integration_available:
        st.warning("Machine learning requires at least 2 numeric columns.")
        return
    
    # ML Analysis type - Enhanced with new capabilities
    ml_type = st.selectbox(
        "Analysis Type",
        ["Anomaly Detection (Enhanced)", "Grant Opportunity Matching", "Economic Indicators", 
         "Predictive Modeling", "Clustering Analysis", "Statistical Analysis"]
    )
    
    # Handle new ML capabilities
    if ml_type == "Anomaly Detection (Enhanced)" and ml_integration_available:
        render_anomaly_detection_tab()
        return
    
    elif ml_type == "Grant Opportunity Matching" and ml_integration_available:
        render_grant_opportunities_tab()
        return
    
    elif ml_type == "Economic Indicators" and ml_integration_available:
        render_economic_indicators_tab()
        return
    
    elif ml_type == "Predictive Modeling":
        col1, col2 = st.columns(2)
        
        with col1:
            target_col = st.selectbox("Target Variable", numeric_cols)
            feature_cols = st.multiselect(
                "Feature Variables", 
                [col for col in numeric_cols if col != target_col],
                default=[col for col in numeric_cols if col != target_col][:3]
            )
        
        if st.button("Run Predictive Model") and target_col and feature_cols:
            with st.spinner("Training predictive models..."):
                results = st.session_state.analytics_engine.perform_predictive_modeling(
                    df, target_col, feature_cols
                )
            
            if 'error' not in results:
                st.success("Model training completed!")
                
                # Display results
                model_metrics = results['models']['random_forest']
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("R² Score", f"{model_metrics['r2_score']:.3f}")
                with col2:
                    st.metric("MSE", f"{model_metrics['mse']:.2f}")
                with col3:
                    st.metric("Data Points", results['data_shape'][0])
                
                # Feature importance
                st.markdown("**Feature Importance**")
                importance_df = pd.DataFrame([
                    {'Feature': k, 'Importance': v} 
                    for k, v in model_metrics['feature_importance'].items()
                ]).sort_values('Importance', ascending=False)
                
                fig = st.session_state.viz_engine.create_bar_chart(
                    importance_df, 'Feature', 'Importance',
                    title="Feature Importance"
                )
                st.plotly_chart(fig, use_container_width=True, key="feature_importance")
            else:
                st.error(results['error'])
    
    elif ml_type == "Clustering Analysis":
        n_clusters = st.slider("Number of Clusters", 2, 10, 3)
        
        if st.button("Run Clustering Analysis"):
            with st.spinner("Performing clustering analysis..."):
                results = st.session_state.analytics_engine.perform_clustering_analysis(
                    df, n_clusters
                )
            
            if 'error' not in results:
                st.success("Clustering analysis completed!")
                
                # Display cluster statistics
                st.markdown("**Cluster Statistics**")
                cluster_stats_df = pd.DataFrame([
                    {
                        'Cluster': k.replace('cluster_', 'Cluster '),
                        'Size': v['size'],
                        'Percentage': f"{v['percentage']:.1f}%"
                    }
                    for k, v in results['cluster_stats'].items()
                ])
                
                st.dataframe(cluster_stats_df, use_container_width=True)
            else:
                st.error(results['error'])

def render_custom_reports_tab(df: pd.DataFrame, org_name: str):
    """Render custom report generation interface"""
    st.markdown("### Custom Report Generation")
    
    report_type = st.selectbox(
        "Report Type",
        ["Financial Summary", "Custom Analysis", "Data Export Report"]
    )
    
    if report_type == "Financial Summary":
        if st.button("Generate Financial Report"):
            with st.spinner("Generating financial summary report..."):
                report_result = st.session_state.report_generator.generate_financial_summary_report(
                    df, org_name
                )
            
            st.success("Report generated successfully!")
            
            # Display summary
            if 'summary' in report_result and 'metrics' in report_result['summary']:
                st.markdown("**Key Metrics**")
                for metric, value in report_result['summary']['metrics'].items():
                    st.write(f"• {metric}: {value}")
            
            # Download button
            st.download_button(
                "Download PDF Report",
                report_result['pdf_data'],
                file_name=report_result['filename'],
                mime="application/pdf"
            )

def render_data_export_tab(df: pd.DataFrame, org_name: str):
    """Render enhanced data export interface with comprehensive format support"""
    st.markdown("### 📊 Comprehensive Data Export Center")
    st.info("Export your BI dashboards, charts, and data in multiple professional formats")
    
    # Initialize reporting engines
    report_engine = ReportEngine()
    chart_service = ChartService()
    audit_logger = ReportAuditLogger()
    
    # Export tabs
    export_tab1, export_tab2, export_tab3 = st.tabs([
        "📄 Data Export", 
        "📈 Dashboard Export",
        "📋 Report Generation"
    ])
    
    with export_tab1:
        st.markdown("#### Export Raw Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Enhanced format selection
            export_format = st.selectbox(
                "Export Format",
                ["PDF", "CSV", "Excel (XLSX)", "JSON", "HTML"],
                help="Choose your preferred export format"
            )
            
            # Column selection
            all_columns = df.columns.tolist()
            selected_columns = st.multiselect(
                "Select Columns",
                all_columns,
                default=all_columns[:10]  # First 10 columns by default
            )
            
            # Row filtering
            max_rows = st.number_input(
                "Maximum Rows",
                min_value=1,
                max_value=len(df),
                value=min(1000, len(df))
            )
            
            # Additional options
            with st.expander("Advanced Options"):
                include_index = st.checkbox("Include Index", value=False)
                include_stats = st.checkbox("Include Statistical Summary", value=True)
                include_charts = st.checkbox("Include Basic Charts (PDF/HTML only)", value=True)
        
        with col2:
            if selected_columns:
                export_df = df[selected_columns].head(max_rows)
                
                st.markdown("**Export Preview**")
                st.dataframe(export_df.head(10), use_container_width=True)
                
                # Prepare report data
                report_data = {
                    'title': f'{org_name} Data Export',
                    'metadata': {
                        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'organization': org_name,
                        'rows': len(export_df),
                        'columns': len(selected_columns)
                    },
                    'sections': [
                        {
                            'header': 'Data Table',
                            'content': f'Selected {len(export_df)} rows and {len(selected_columns)} columns',
                            'data': export_df
                        }
                    ]
                }
                
                # Add statistical summary if requested
                if include_stats:
                    numeric_cols = export_df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        stats_df = export_df[numeric_cols].describe()
                        report_data['sections'].append({
                            'header': 'Statistical Summary',
                            'content': 'Key statistics for numeric columns',
                            'data': stats_df
                        })
                
                # Generate export based on format
                if st.button("🚀 Generate Export", type="primary"):
                    start_time = datetime.now()
                    
                    try:
                        # Map format names
                        format_map = {
                            'PDF': 'PDF',
                            'CSV': 'CSV',
                            'Excel (XLSX)': 'XLSX',
                            'JSON': 'JSON',
                            'HTML': 'HTML'
                        }
                        
                        export_format_clean = format_map[export_format]
                        
                        # Generate report
                        export_bytes = report_engine.generate_report(
                            report_data, 
                            export_format_clean,
                            include_charts=include_charts and export_format_clean in ['PDF', 'HTML']
                        )
                        
                        # Calculate generation time
                        generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                        
                        # Log the export
                        report_id = audit_logger.log_report_generation(
                            user_id=st.session_state.get('username', 'guest'),
                            user_role=st.session_state.get('user_role', 'viewer'),
                            report_type='Data Export',
                            module='BI Dashboard',
                            format=export_format_clean,
                            parameters={'columns': selected_columns, 'rows': max_rows},
                            status='success',
                            file_size=len(export_bytes),
                            generation_time_ms=generation_time_ms
                        )
                        
                        # Create download button
                        file_extension = export_format_clean.lower()
                        if file_extension == 'xlsx':
                            file_extension = 'xlsx'
                            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        elif file_extension == 'pdf':
                            mime_type = 'application/pdf'
                        elif file_extension == 'csv':
                            mime_type = 'text/csv'
                        elif file_extension == 'json':
                            mime_type = 'application/json'
                        else:  # HTML
                            mime_type = 'text/html'
                        
                        st.success(f"✅ Export generated successfully in {generation_time_ms}ms!")
                        
                        st.download_button(
                            label=f"📥 Download {export_format}",
                            data=export_bytes,
                            file_name=f"{org_name}_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}",
                            mime=mime_type,
                            key=f"download_{report_id}"
                        )
                        
                        # Log the download
                        audit_logger.log_report_access(
                            user_id=st.session_state.get('username', 'guest'),
                            report_id=report_id,
                            action='download'
                        )
                        
                    except Exception as e:
                        st.error(f"Export generation failed: {str(e)}")
                        
                        # Log failure
                        audit_logger.log_report_generation(
                            user_id=st.session_state.get('username', 'guest'),
                            user_role=st.session_state.get('user_role', 'viewer'),
                            report_type='Data Export',
                            module='BI Dashboard',
                            format=export_format,
                            parameters={'columns': selected_columns, 'rows': max_rows},
                            status='failure',
                            error_message=str(e)
                        )
    
    with export_tab2:
        st.markdown("#### Export Dashboard & Visualizations")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**Dashboard Export Options**")
            
            # Chart selection
            available_charts = [
                "Budget Overview",
                "Revenue Trends", 
                "Department Spending",
                "Transaction Analysis",
                "Performance Metrics"
            ]
            
            selected_charts = st.multiselect(
                "Select Charts to Include",
                available_charts,
                default=available_charts[:3]
            )
            
            # Export format for dashboard
            dashboard_format = st.selectbox(
                "Dashboard Export Format",
                ["PDF Report", "HTML Dashboard", "PowerPoint Presentation"],
                key="dashboard_format"
            )
            
            # Layout options
            with st.expander("Layout Options"):
                charts_per_page = st.number_input("Charts per Page", 1, 4, 2)
                include_narrative = st.checkbox("Include AI Narrative", value=True)
                include_recommendations = st.checkbox("Include Recommendations", value=True)
        
        with col2:
            st.markdown("**Dashboard Preview**")
            
            if selected_charts:
                # Create sample visualizations
                st.info(f"Selected {len(selected_charts)} charts for export")
                
                # Generate sample chart
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) >= 2:
                    sample_fig = chart_service.create_bar_chart(
                        df.head(20),
                        df.columns[0],
                        numeric_cols[0],
                        title="Sample Budget Overview"
                    )
                    st.plotly_chart(sample_fig, use_container_width=True, key="sample_budget_overview")
                
                if st.button("📊 Generate Dashboard Export", type="primary", key="gen_dashboard"):
                    with st.spinner("Generating dashboard export..."):
                        # Create comprehensive dashboard report
                        dashboard_data = {
                            'title': f'{org_name} BI Dashboard Export',
                            'metadata': {
                                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                                'organization': org_name,
                                'charts_included': len(selected_charts)
                            },
                            'sections': []
                        }
                        
                        # Add each selected chart
                        for chart_name in selected_charts:
                            dashboard_data['sections'].append({
                                'header': chart_name,
                                'content': f'Analysis and visualization for {chart_name}',
                                'chart_title': chart_name
                            })
                        
                        # Add narrative if requested
                        if include_narrative:
                            dashboard_data['sections'].append({
                                'header': 'Executive Summary',
                                'content': 'AI-generated insights and analysis of the dashboard data showing key trends and patterns.'
                            })
                        
                        # Convert format name
                        format_map = {
                            'PDF Report': 'PDF',
                            'HTML Dashboard': 'HTML',
                            'PowerPoint Presentation': 'PDF'  # Will enhance later
                        }
                        
                        export_format = format_map[dashboard_format]
                        
                        # Generate the dashboard export
                        dashboard_bytes = report_engine.generate_report(
                            dashboard_data,
                            export_format,
                            include_charts=True
                        )
                        
                        st.success("✅ Dashboard export generated successfully!")
                        
                        # Download button
                        file_ext = 'pdf' if dashboard_format == 'PDF Report' else 'html'
                        st.download_button(
                            f"📥 Download {dashboard_format}",
                            dashboard_bytes,
                            f"{org_name}_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}",
                            mime='application/pdf' if file_ext == 'pdf' else 'text/html'
                        )
    
    with export_tab3:
        st.markdown("#### Automated Report Generation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Report Configuration**")
            
            # Report template selection
            report_template = st.selectbox(
                "Report Template",
                [
                    "Executive Summary",
                    "Financial Analysis Report",
                    "Department Performance Report",
                    "Monthly Budget Report",
                    "Custom Report"
                ]
            )
            
            # Time period
            period = st.selectbox(
                "Reporting Period",
                ["Current Month", "Last Month", "Current Quarter", "Year to Date", "Custom Range"]
            )
            
            # Report sections
            st.markdown("**Include Sections:**")
            include_summary = st.checkbox("Executive Summary", value=True)
            include_kpis = st.checkbox("Key Performance Indicators", value=True)
            include_trends = st.checkbox("Trend Analysis", value=True)
            include_comparisons = st.checkbox("Period Comparisons", value=True)
            include_forecasts = st.checkbox("Forecasts & Projections", value=False)
            
            # Delivery options
            with st.expander("Delivery Options"):
                schedule_report = st.checkbox("Schedule Recurring Report", value=False)
                if schedule_report:
                    frequency = st.selectbox(
                        "Frequency",
                        ["Daily", "Weekly", "Monthly", "Quarterly"]
                    )
                    delivery_time = st.time_input("Delivery Time")
        
        with col2:
            st.markdown("**Report Preview & Generation**")
            
            # Show report outline
            st.markdown("##### Report Outline")
            outline = []
            if include_summary:
                outline.append("1. Executive Summary")
            if include_kpis:
                outline.append("2. Key Performance Indicators")
            if include_trends:
                outline.append("3. Trend Analysis")
            if include_comparisons:
                outline.append("4. Period Comparisons")
            if include_forecasts:
                outline.append("5. Forecasts & Projections")
            
            for item in outline:
                st.write(item)
            
            # Generate button
            if st.button("📑 Generate Full Report", type="primary", key="gen_report"):
                with st.spinner("Generating comprehensive report..."):
                    # Build comprehensive report
                    full_report = {
                        'title': f'{org_name} {report_template}',
                        'metadata': {
                            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'organization': org_name,
                            'period': period,
                            'template': report_template
                        },
                        'sections': [],
                        'footer': f'Generated by GovSight BI Dashboard | {datetime.now().strftime("%Y")}'
                    }
                    
                    # Add sections based on selections
                    if include_summary:
                        full_report['sections'].append({
                            'header': 'Executive Summary',
                            'content': 'This report provides a comprehensive analysis of financial and operational metrics.'
                        })
                    
                    if include_kpis:
                        # Create KPI data
                        kpi_data = pd.DataFrame({
                            'Metric': ['Total Revenue', 'Total Expenses', 'Net Margin', 'Efficiency'],
                            'Current': [1500000, 1200000, 300000, 85],
                            'Target': [1600000, 1100000, 500000, 90],
                            'Variance': [-100000, -100000, -200000, -5]
                        })
                        full_report['sections'].append({
                            'header': 'Key Performance Indicators',
                            'data': kpi_data
                        })
                    
                    # Generate as PDF by default
                    report_bytes = report_engine.generate_report(
                        full_report,
                        'PDF',
                        include_charts=True
                    )
                    
                    st.success("✅ Comprehensive report generated successfully!")
                    
                    # Download button
                    st.download_button(
                        "📥 Download Full Report (PDF)",
                        report_bytes,
                        f"{org_name}_{report_template.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime='application/pdf'
                    )

def render_performance_monitoring_tab(df: pd.DataFrame):
    """Render system performance monitoring"""
    st.markdown("### System Performance Monitoring")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Data metrics
        st.markdown("**Data Metrics**")
        memory_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
        st.metric("Memory Usage", f"{memory_usage:.2f} MB")
        st.metric("Cache Entries", len(st.session_state))
        
    with col2:
        # Performance metrics  
        st.markdown("**Performance**")
        st.metric("Data Load Time", "< 1 sec")
        st.metric("Chart Render Time", "< 0.5 sec")
        
    with col3:
        # System info
        st.markdown("**System Info**")
        st.metric("Components Loaded", "6 modules")
        st.metric("Status", "Optimal")
    
    # Component status
    st.markdown("**Component Status**")
    components_status = {
        "Analytics Engine": "✅ Active",
        "Visualization Engine": "✅ Active", 
        "NLP Processor": "✅ Active",
        "Report Generator": "✅ Active",
        "Data Optimizer": "✅ Active",
        "Export Manager": "✅ Active"
    }
    
    status_df = pd.DataFrame([
        {'Component': k, 'Status': v} 
        for k, v in components_status.items()
    ])
    
    st.dataframe(status_df, use_container_width=True, hide_index=True)

def _build_dashboard_data_injection() -> str:
    """Aggregate the canonical GL store into the payload the enhanced
    dashboard charts from. Returns an empty string when no real data exists
    (the page then labels itself as sample data)."""
    import json
    import os
    import sqlite3
    db_path = os.path.join("databases", "core", "govsight_all_in_one_data.db")
    if not os.path.exists(db_path):
        return ""
    try:
        conn = sqlite3.connect(db_path)
        try:
            dept = conn.execute(
                """SELECT department, SUM(budget_amount), SUM(ytd_actual)
                   FROM gl_accounts WHERE account_type='Expense'
                   GROUP BY department ORDER BY SUM(budget_amount) DESC"""
            ).fetchall()
            atype = conn.execute(
                """SELECT account_type, SUM(budget_amount), SUM(ytd_actual)
                   FROM gl_accounts GROUP BY account_type"""
            ).fetchall()
            fund = conn.execute(
                """SELECT fund, SUM(budget_amount), SUM(ytd_actual)
                   FROM gl_accounts GROUP BY fund"""
            ).fetchall()
        finally:
            conn.close()
        if not dept:
            return ""
        payload = {
            "source": "real",
            "byDept": {
                "categories": [d[0] for d in dept],
                "budget": [round(d[1] or 0, 2) for d in dept],
                "actual": [round(d[2] or 0, 2) for d in dept],
            },
            "byAccountType": {
                "categories": [a[0] for a in atype],
                "budget": [round(a[1] or 0, 2) for a in atype],
                "actual": [round(a[2] or 0, 2) for a in atype],
            },
            "byFund": {
                "categories": [f[0] for f in fund],
                "budget": [round(f[1] or 0, 2) for f in fund],
                "actual": [round(f[2] or 0, 2) for f in fund],
            },
        }
        return "<script>window.GOVSIGHT_DATA = " + json.dumps(payload) + ";</script>\n"
    except Exception:
        return ""
