"""
Visualization Engine for BI Sandbox

This module provides advanced chart creation and visualization capabilities
with support for multiple chart types and interactive features.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from .data_structures import VisualizationType, create_visualization_engine_config

def create_visualization_engine():
    """Create custom visualization engine for interactive charts and dashboards"""
    return create_visualization_engine_config()

class AdvancedVisualizationEngine:
    """Advanced visualization engine with multiple chart types"""
    
    def __init__(self):
        self.config = create_visualization_engine_config()
        self.color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
    
    def create_bar_chart(self, data: pd.DataFrame, x_col: str, y_col: str, **kwargs) -> go.Figure:
        """Create interactive bar chart"""
        if data.empty or x_col not in data.columns or y_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'{y_col} by {x_col}')
        color_col = kwargs.get('color', None)
        
        if color_col and color_col in data.columns:
            fig = px.bar(data, x=x_col, y=y_col, color=color_col, title=title)
        else:
            fig = px.bar(data, x=x_col, y=y_col, title=title)
        
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
            showlegend=True if color_col else False
        )
        
        return fig
    
    def create_line_chart(self, data: pd.DataFrame, x_col: str, y_col: str, **kwargs) -> go.Figure:
        """Create interactive line chart"""
        if data.empty or x_col not in data.columns or y_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'{y_col} over {x_col}')
        color_col = kwargs.get('color', None)
        
        if color_col and color_col in data.columns:
            fig = px.line(data, x=x_col, y=y_col, color=color_col, title=title)
        else:
            fig = px.line(data, x=x_col, y=y_col, title=title)
        
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        
        return fig
    
    def create_scatter_plot(self, data: pd.DataFrame, x_col: str, y_col: str, **kwargs) -> go.Figure:
        """Create interactive scatter plot"""
        if data.empty or x_col not in data.columns or y_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'{y_col} vs {x_col}')
        color_col = kwargs.get('color', None)
        size_col = kwargs.get('size', None)
        
        if color_col and color_col in data.columns:
            if size_col and size_col in data.columns:
                fig = px.scatter(data, x=x_col, y=y_col, color=color_col, size=size_col, title=title)
            else:
                fig = px.scatter(data, x=x_col, y=y_col, color=color_col, title=title)
        else:
            fig = px.scatter(data, x=x_col, y=y_col, title=title)
        
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        
        return fig
    
    def create_pie_chart(self, data: pd.DataFrame, values_col: str, names_col: str, **kwargs) -> go.Figure:
        """Create interactive pie chart"""
        if data.empty or values_col not in data.columns or names_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Distribution of {values_col}')
        
        fig = px.pie(data, values=values_col, names=names_col, title=title)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        return fig
    
    def create_heatmap(self, data: pd.DataFrame, x_col: str, y_col: str, z_col: str, **kwargs) -> go.Figure:
        """Create interactive heatmap"""
        if data.empty:
            return go.Figure()
        
        title = kwargs.get('title', f'Heatmap of {z_col}')
        
        # Pivot data for heatmap
        try:
            pivot_data = data.pivot_table(values=z_col, index=y_col, columns=x_col, aggfunc='mean')
            
            fig = px.imshow(
                pivot_data,
                title=title,
                aspect="auto",
                color_continuous_scale="RdYlBu_r"
            )
            
        except Exception:
            # Fallback to correlation heatmap if pivot fails
            numeric_data = data.select_dtypes(include=[np.number])
            if not numeric_data.empty:
                corr_matrix = numeric_data.corr()
                fig = px.imshow(
                    corr_matrix,
                    title="Correlation Heatmap",
                    color_continuous_scale="RdYlBu_r"
                )
            else:
                fig = go.Figure()
        
        return fig
    
    def create_box_plot(self, data: pd.DataFrame, y_col: str, x_col: str = None, **kwargs) -> go.Figure:
        """Create interactive box plot"""
        if data.empty or y_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Box Plot of {y_col}')
        
        if x_col and x_col in data.columns:
            fig = px.box(data, x=x_col, y=y_col, title=title)
        else:
            fig = px.box(data, y=y_col, title=title)
        
        return fig
    
    def create_violin_plot(self, data: pd.DataFrame, y_col: str, x_col: str = None, **kwargs) -> go.Figure:
        """Create interactive violin plot"""
        if data.empty or y_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Violin Plot of {y_col}')
        
        if x_col and x_col in data.columns:
            fig = px.violin(data, x=x_col, y=y_col, title=title)
        else:
            fig = px.violin(data, y=y_col, title=title)
        
        return fig
    
    def create_histogram(self, data: pd.DataFrame, x_col: str, **kwargs) -> go.Figure:
        """Create interactive histogram"""
        if data.empty or x_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Distribution of {x_col}')
        bins = kwargs.get('bins', 30)
        
        fig = px.histogram(data, x=x_col, nbins=bins, title=title)
        fig.update_layout(yaxis_title='Count')
        
        return fig
    
    def create_treemap(self, data: pd.DataFrame, path_cols: List[str], values_col: str, **kwargs) -> go.Figure:
        """Create interactive treemap"""
        if data.empty or not all(col in data.columns for col in path_cols + [values_col]):
            return go.Figure()
        
        title = kwargs.get('title', f'Treemap of {values_col}')
        
        fig = px.treemap(
            data,
            path=path_cols,
            values=values_col,
            title=title
        )
        
        return fig
    
    def create_sunburst(self, data: pd.DataFrame, path_cols: List[str], values_col: str, **kwargs) -> go.Figure:
        """Create interactive sunburst chart"""
        if data.empty or not all(col in data.columns for col in path_cols + [values_col]):
            return go.Figure()
        
        title = kwargs.get('title', f'Sunburst of {values_col}')
        
        fig = px.sunburst(
            data,
            path=path_cols,
            values=values_col,
            title=title
        )
        
        return fig
    
    def create_waterfall_chart(self, data: pd.DataFrame, x_col: str, y_col: str, **kwargs) -> go.Figure:
        """Create waterfall chart"""
        if data.empty or x_col not in data.columns or y_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Waterfall Chart of {y_col}')
        
        # Calculate cumulative values
        cumulative = data[y_col].cumsum()
        
        fig = go.Figure()
        
        # Add bars for each category
        for i, (x_val, y_val) in enumerate(zip(data[x_col], data[y_col])):
            color = 'green' if y_val >= 0 else 'red'
            fig.add_trace(go.Bar(
                x=[x_val],
                y=[y_val],
                name=str(x_val),
                marker_color=color,
                showlegend=False
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        
        return fig
    
    def create_gauge_chart(self, value: float, max_value: float = 100, title: str = "Gauge", **kwargs) -> go.Figure:
        """Create gauge chart for KPIs"""
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            delta={'reference': max_value * 0.8},  # Target at 80%
            gauge={
                'axis': {'range': [None, max_value]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, max_value * 0.5], 'color': "lightgray"},
                    {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': max_value * 0.9
                }
            }
        ))
        
        return fig
    
    def create_funnel_chart(self, data: pd.DataFrame, stage_col: str, values_col: str, **kwargs) -> go.Figure:
        """Create funnel chart"""
        if data.empty or stage_col not in data.columns or values_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Funnel Chart of {values_col}')
        
        fig = go.Figure(go.Funnel(
            y=data[stage_col],
            x=data[values_col],
            textinfo="value+percent initial"
        ))
        
        fig.update_layout(title=title)
        
        return fig
    
    def create_chart_by_type(self, chart_type: str, data: pd.DataFrame, **kwargs) -> go.Figure:
        """Create chart based on type string"""
        chart_creators = {
            'bar': self.create_bar_chart,
            'line': self.create_line_chart,
            'scatter': self.create_scatter_plot,
            'pie': self.create_pie_chart,
            'heatmap': self.create_heatmap,
            'box': self.create_box_plot,
            'violin': self.create_violin_plot,
            'histogram': self.create_histogram,
            'treemap': self.create_treemap,
            'sunburst': self.create_sunburst,
            'waterfall': self.create_waterfall_chart,
            'funnel': self.create_funnel_chart
        }
        
        creator = chart_creators.get(chart_type.lower())
        if creator:
            return creator(data, **kwargs)
        else:
            return go.Figure()
    
    def add_chart_interactivity(self, fig: go.Figure, enable_zoom: bool = True, enable_pan: bool = True) -> go.Figure:
        """Add interactive features to charts"""
        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': []
        }
        
        if not enable_zoom:
            config['modeBarButtonsToRemove'].extend(['zoomIn2d', 'zoomOut2d', 'autoScale2d'])
        
        if not enable_pan:
            config['modeBarButtonsToRemove'].append('pan2d')
        
        fig.update_layout(
            hovermode='closest',
            dragmode='zoom' if enable_zoom else 'pan' if enable_pan else False
        )
        
        return fig
    
    def apply_theme(self, fig: go.Figure, theme: str = 'plotly') -> go.Figure:
        """Apply visual theme to chart"""
        themes = {
            'plotly': 'plotly',
            'dark': 'plotly_dark',
            'white': 'plotly_white',
            'simple': 'simple_white'
        }
        
        template = themes.get(theme, 'plotly')
        fig.update_layout(template=template)
        
        return fig