"""
Custom Visualization Builder - Interactive Chart Creation Tool
Enables users to build custom visualizations with drag-and-drop interface
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Any, Optional

class CustomVisualizationBuilder:
    """Builder class for creating custom interactive visualizations"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        self.date_columns = data.select_dtypes(include=['datetime64']).columns.tolist()
    
    def render_chart_builder(self, key_prefix: str = "custom_viz") -> Optional[go.Figure]:
        """Render the custom chart builder interface"""
        
        st.subheader("Custom Visualization Builder")
        
        # Chart type selection
        chart_types = {
            'Bar Chart': 'bar',
            'Line Chart': 'line', 
            'Scatter Plot': 'scatter',
            'Area Chart': 'area',
            'Histogram': 'histogram',
            'Box Plot': 'box',
            'Violin Plot': 'violin',
            'Heatmap': 'heatmap',
            'Treemap': 'treemap',
            'Sunburst': 'sunburst',
            'Waterfall': 'waterfall',
            'Funnel': 'funnel',
            'Gauge': 'gauge',
            'Radar Chart': 'radar'
        }
        
        selected_chart_type = st.selectbox(
            "Select Chart Type",
            options=list(chart_types.keys()),
            key=f"{key_prefix}_chart_type"
        )
        
        chart_type = chart_types[selected_chart_type]
        
        # Dynamic column selection based on chart type
        col1, col2, col3 = st.columns(3)
        
        with col1:
            x_axis = self._get_x_axis_selection(chart_type, key_prefix)
        
        with col2:
            y_axis = self._get_y_axis_selection(chart_type, key_prefix)
        
        with col3:
            color_by = self._get_color_selection(chart_type, key_prefix)
        
        # Advanced options
        with st.expander("Advanced Chart Options"):
            size_by, facet_col, facet_row = self._get_advanced_options(chart_type, key_prefix)
        
        # Chart customization
        with st.expander("Chart Styling"):
            title, color_scheme, height = self._get_styling_options(key_prefix)
        
        # Generate chart button
        if st.button("Generate Custom Chart", key=f"{key_prefix}_generate"):
            try:
                chart = self._create_chart(
                    chart_type=chart_type,
                    x_axis=x_axis,
                    y_axis=y_axis,
                    color_by=color_by,
                    size_by=size_by,
                    facet_col=facet_col,
                    facet_row=facet_row,
                    title=title,
                    color_scheme=color_scheme,
                    height=height
                )
                
                if chart:
                    st.plotly_chart(chart, use_container_width=True)
                    
                    # Chart export options
                    self._render_export_options(chart, key_prefix)
                    
                    return chart
                    
            except Exception as e:
                st.error(f"Error creating chart: {e}")
                st.info("Try adjusting your column selections or chart type.")
        
        return None
    
    def _get_x_axis_selection(self, chart_type: str, key_prefix: str) -> Optional[str]:
        """Get X-axis column selection based on chart type"""
        if chart_type in ['histogram', 'box', 'violin']:
            # These charts typically use single column
            return st.selectbox(
                "Select Data Column",
                options=self.numeric_columns + self.categorical_columns,
                key=f"{key_prefix}_x_axis"
            )
        else:
            return st.selectbox(
                "X-Axis",
                options=self.categorical_columns + self.date_columns + self.numeric_columns,
                key=f"{key_prefix}_x_axis"
            )
    
    def _get_y_axis_selection(self, chart_type: str, key_prefix: str) -> Optional[str]:
        """Get Y-axis column selection based on chart type"""
        if chart_type in ['histogram', 'treemap', 'sunburst']:
            return None  # These don't need Y-axis
        elif chart_type in ['heatmap']:
            return st.selectbox(
                "Y-Axis",
                options=self.categorical_columns + self.numeric_columns,
                key=f"{key_prefix}_y_axis"
            )
        else:
            return st.selectbox(
                "Y-Axis", 
                options=self.numeric_columns,
                key=f"{key_prefix}_y_axis"
            )
    
    def _get_color_selection(self, chart_type: str, key_prefix: str) -> Optional[str]:
        """Get color-by column selection"""
        return st.selectbox(
            "Color By (Optional)",
            options=[None] + self.categorical_columns + self.numeric_columns,
            key=f"{key_prefix}_color_by"
        )
    
    def _get_advanced_options(self, chart_type: str, key_prefix: str) -> tuple:
        """Get advanced visualization options"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            size_by = None
            if chart_type in ['scatter', 'bubble']:
                size_by = st.selectbox(
                    "Size By (Optional)",
                    options=[None] + self.numeric_columns,
                    key=f"{key_prefix}_size_by"
                )
        
        with col2:
            facet_col = st.selectbox(
                "Facet Columns (Optional)",
                options=[None] + self.categorical_columns,
                key=f"{key_prefix}_facet_col"
            )
        
        with col3:
            facet_row = st.selectbox(
                "Facet Rows (Optional)",
                options=[None] + self.categorical_columns,
                key=f"{key_prefix}_facet_row"
            )
        
        return size_by, facet_col, facet_row
    
    def _get_styling_options(self, key_prefix: str) -> tuple:
        """Get chart styling options"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            title = st.text_input(
                "Chart Title",
                value="Custom Visualization",
                key=f"{key_prefix}_title"
            )
        
        with col2:
            color_schemes = [
                'plotly', 'viridis', 'plasma', 'inferno', 'magma',
                'blues', 'reds', 'greens', 'purples', 'oranges'
            ]
            color_scheme = st.selectbox(
                "Color Scheme",
                options=color_schemes,
                key=f"{key_prefix}_color_scheme"
            )
        
        with col3:
            height = st.slider(
                "Chart Height",
                min_value=300,
                max_value=800,
                value=500,
                step=50,
                key=f"{key_prefix}_height"
            )
        
        return title, color_scheme, height
    
    def _create_chart(self, **kwargs) -> Optional[go.Figure]:
        """Create the chart based on specifications"""
        chart_type = kwargs.get('chart_type')
        x_axis = kwargs.get('x_axis')
        y_axis = kwargs.get('y_axis')
        color_by = kwargs.get('color_by')
        size_by = kwargs.get('size_by')
        facet_col = kwargs.get('facet_col')
        facet_row = kwargs.get('facet_row')
        title = kwargs.get('title')
        color_scheme = kwargs.get('color_scheme')
        height = kwargs.get('height', 500)
        
        # Create chart based on type
        if chart_type == 'bar':
            fig = px.bar(
                self.data, x=x_axis, y=y_axis, color=color_by,
                facet_col=facet_col, facet_row=facet_row,
                title=title, color_continuous_scale=color_scheme,
                height=height
            )
            
        elif chart_type == 'line':
            fig = px.line(
                self.data, x=x_axis, y=y_axis, color=color_by,
                facet_col=facet_col, facet_row=facet_row,
                title=title, height=height
            )
            
        elif chart_type == 'scatter':
            fig = px.scatter(
                self.data, x=x_axis, y=y_axis, color=color_by, size=size_by,
                facet_col=facet_col, facet_row=facet_row,
                title=title, color_continuous_scale=color_scheme,
                height=height
            )
            
        elif chart_type == 'area':
            fig = px.area(
                self.data, x=x_axis, y=y_axis, color=color_by,
                facet_col=facet_col, facet_row=facet_row,
                title=title, height=height
            )
            
        elif chart_type == 'histogram':
            fig = px.histogram(
                self.data, x=x_axis, color=color_by,
                facet_col=facet_col, facet_row=facet_row,
                title=title, color_discrete_sequence=px.colors.qualitative.Set3,
                height=height
            )
            
        elif chart_type == 'box':
            fig = px.box(
                self.data, x=x_axis, y=y_axis, color=color_by,
                facet_col=facet_col, facet_row=facet_row,
                title=title, height=height
            )
            
        elif chart_type == 'violin':
            fig = px.violin(
                self.data, x=x_axis, y=y_axis, color=color_by,
                facet_col=facet_col, facet_row=facet_row,
                title=title, height=height
            )
            
        elif chart_type == 'heatmap':
            # Create correlation matrix for heatmap
            numeric_data = self.data.select_dtypes(include=[np.number])
            if len(numeric_data.columns) > 1:
                corr_matrix = numeric_data.corr()
                fig = px.imshow(
                    corr_matrix, 
                    title=title,
                    color_continuous_scale=color_scheme,
                    height=height
                )
            else:
                st.warning("Heatmap requires at least 2 numeric columns")
                return None
                
        elif chart_type == 'treemap':
            if color_by and x_axis:
                fig = px.treemap(
                    self.data, path=[x_axis], values=y_axis or color_by,
                    color=color_by, title=title,
                    color_continuous_scale=color_scheme,
                    height=height
                )
            else:
                st.warning("Treemap requires path and values columns")
                return None
                
        elif chart_type == 'waterfall':
            # Create waterfall chart
            if y_axis and x_axis:
                fig = go.Figure(go.Waterfall(
                    name="Waterfall",
                    orientation="v",
                    measure=["relative"] * len(self.data),
                    x=self.data[x_axis],
                    textposition="outside",
                    y=self.data[y_axis],
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                ))
                fig.update_layout(title=title, height=height)
            else:
                st.warning("Waterfall chart requires X and Y axes")
                return None
                
        else:
            st.warning(f"Chart type '{chart_type}' not yet implemented")
            return None
        
        # Apply common styling
        fig.update_layout(
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        
        return fig
    
    def _render_export_options(self, chart: go.Figure, key_prefix: str):
        """Render chart export options"""
        st.markdown("### Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Download as PNG", key=f"{key_prefix}_png"):
                img_bytes = chart.to_image(format="png", width=1200, height=800)
                st.download_button(
                    label="Download PNG",
                    data=img_bytes,
                    file_name=f"custom_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png"
                )
        
        with col2:
            if st.button("Download as HTML", key=f"{key_prefix}_html"):
                html_string = chart.to_html(include_plotlyjs='cdn')
                st.download_button(
                    label="Download HTML",
                    data=html_string,
                    file_name=f"custom_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html"
                )
        
        with col3:
            if st.button("Copy Chart Config", key=f"{key_prefix}_config"):
                config = {
                    'data': chart.data[0].to_plotly_json() if chart.data else {},
                    'layout': chart.layout.to_plotly_json()
                }
                st.code(str(config), language='json')

def render_custom_visualization_tab(data: pd.DataFrame, org: str):
    """Render the custom visualization tab"""
    
    st.markdown("## Custom Visualization Builder")
    st.markdown("Build interactive charts and dashboards with drag-and-drop simplicity")
    
    if data.empty:
        st.warning("No data available for visualization. Please load data first.")
        return
    
    # Initialize the builder
    viz_builder = CustomVisualizationBuilder(data)
    
    # Render the chart builder interface
    chart = viz_builder.render_chart_builder(key_prefix=f"custom_viz_{org}")
    
    # Quick preset charts section
    st.markdown("---")
    st.markdown("### Quick Preset Charts")
    
    preset_col1, preset_col2, preset_col3 = st.columns(3)
    
    with preset_col1:
        if st.button("Department Budget Overview"):
            if 'Department' in data.columns and 'Budget' in data.columns:
                fig = px.bar(data, x='Department', y='Budget', 
                           title='Department Budget Overview',
                           color='Budget', color_continuous_scale='viridis')
                st.plotly_chart(fig, use_container_width=True)
    
    with preset_col2:
        if st.button("Budget vs Actual Analysis"):
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 2:
                fig = px.scatter(data, x=numeric_cols[0], y=numeric_cols[1],
                               title='Budget vs Actual Analysis',
                               trendline="ols")
                st.plotly_chart(fig, use_container_width=True)
    
    with preset_col3:
        if st.button("Performance Heatmap"):
            numeric_data = data.select_dtypes(include=[np.number])
            if len(numeric_data.columns) > 1:
                corr_matrix = numeric_data.corr()
                fig = px.imshow(corr_matrix, title='Performance Correlation Heatmap',
                              color_continuous_scale='RdBu_r')
                st.plotly_chart(fig, use_container_width=True)