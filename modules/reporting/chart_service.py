"""
Chart Generation Service
Creates data visualizations using Plotly for interactive charts and static image export
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional, Union
import base64
import io
from datetime import datetime


class ChartService:
    """Service for generating charts and visualizations"""
    
    def __init__(self):
        """Initialize chart service with default settings"""
        self.default_colors = [
            '#3b82f6',  # Blue
            '#10b981',  # Green 
            '#f59e0b',  # Amber
            '#ef4444',  # Red
            '#8b5cf6',  # Purple
            '#ec4899',  # Pink
            '#06b6d4',  # Cyan
            '#84cc16',  # Lime
        ]
        
        self.layout_template = {
            'font': {'family': 'Segoe UI, Arial, sans-serif'},
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            'margin': {'t': 50, 'b': 50, 'l': 60, 'r': 30},
            'showlegend': True,
            'hovermode': 'x unified'
        }
    
    def create_bar_chart(self,
                        data: pd.DataFrame,
                        x_col: str,
                        y_col: str,
                        title: str = "Bar Chart",
                        color_col: str = None,
                        orientation: str = 'v') -> go.Figure:
        """Create a bar chart"""
        fig = px.bar(
            data,
            x=x_col if orientation == 'v' else y_col,
            y=y_col if orientation == 'v' else x_col,
            color=color_col,
            title=title,
            orientation=orientation,
            color_discrete_sequence=self.default_colors
        )
        
        fig.update_layout(**self.layout_template)
        return fig
    
    def create_line_chart(self,
                         data: pd.DataFrame,
                         x_col: str,
                         y_cols: Union[str, List[str]],
                         title: str = "Line Chart",
                         show_markers: bool = True) -> go.Figure:
        """Create a line chart with one or multiple series"""
        if isinstance(y_cols, str):
            y_cols = [y_cols]
        
        fig = go.Figure()
        
        for idx, y_col in enumerate(y_cols):
            fig.add_trace(go.Scatter(
                x=data[x_col],
                y=data[y_col],
                mode='lines+markers' if show_markers else 'lines',
                name=y_col,
                line=dict(color=self.default_colors[idx % len(self.default_colors)], width=2),
                marker=dict(size=6) if show_markers else None
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title='Value',
            **self.layout_template
        )
        
        return fig
    
    def create_pie_chart(self,
                        data: pd.DataFrame,
                        values_col: str,
                        names_col: str,
                        title: str = "Pie Chart",
                        show_percentages: bool = True) -> go.Figure:
        """Create a pie chart"""
        fig = px.pie(
            data,
            values=values_col,
            names=names_col,
            title=title,
            color_discrete_sequence=self.default_colors
        )
        
        if show_percentages:
            fig.update_traces(textposition='inside', textinfo='percent+label')
        
        fig.update_layout(**self.layout_template)
        return fig
    
    def create_area_chart(self,
                         data: pd.DataFrame,
                         x_col: str,
                         y_cols: Union[str, List[str]],
                         title: str = "Area Chart",
                         stacked: bool = True) -> go.Figure:
        """Create an area chart"""
        if isinstance(y_cols, str):
            y_cols = [y_cols]
        
        fig = go.Figure()
        
        for idx, y_col in enumerate(y_cols):
            fig.add_trace(go.Scatter(
                x=data[x_col],
                y=data[y_col],
                mode='lines',
                name=y_col,
                fill='tonexty' if idx > 0 and stacked else 'tozeroy',
                line=dict(color=self.default_colors[idx % len(self.default_colors)]),
                stackgroup='one' if stacked else None
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title='Value',
            **self.layout_template
        )
        
        return fig
    
    def create_heatmap(self,
                      data: pd.DataFrame,
                      title: str = "Heatmap",
                      show_values: bool = True) -> go.Figure:
        """Create a heatmap from DataFrame"""
        fig = go.Figure(data=go.Heatmap(
            z=data.values,
            x=data.columns,
            y=data.index,
            colorscale='Blues',
            text=data.values if show_values else None,
            texttemplate='%{text}' if show_values else None,
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title=title,
            **self.layout_template
        )
        
        return fig
    
    def create_waterfall_chart(self,
                              data: pd.DataFrame,
                              x_col: str,
                              y_col: str,
                              title: str = "Waterfall Chart") -> go.Figure:
        """Create a waterfall chart for showing cumulative effect"""
        fig = go.Figure(go.Waterfall(
            x=data[x_col],
            y=data[y_col],
            text=[f"{v:,.0f}" for v in data[y_col]],
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": self.default_colors[1]}},  # Green
            decreasing={"marker": {"color": self.default_colors[3]}},  # Red
            totals={"marker": {"color": self.default_colors[0]}}  # Blue
        ))
        
        fig.update_layout(
            title=title,
            showlegend=False,
            **self.layout_template
        )
        
        return fig
    
    def create_treemap(self,
                      data: pd.DataFrame,
                      values_col: str,
                      labels_col: str,
                      parents_col: str = None,
                      title: str = "Treemap") -> go.Figure:
        """Create a treemap for hierarchical data"""
        fig = px.treemap(
            data,
            values=values_col,
            names=labels_col,
            parents=parents_col,
            title=title,
            color=values_col,
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(**self.layout_template)
        return fig
    
    def create_scatter_plot(self,
                           data: pd.DataFrame,
                           x_col: str,
                           y_col: str,
                           title: str = "Scatter Plot",
                           size_col: str = None,
                           color_col: str = None,
                           trendline: bool = False) -> go.Figure:
        """Create a scatter plot"""
        fig = px.scatter(
            data,
            x=x_col,
            y=y_col,
            size=size_col,
            color=color_col,
            title=title,
            trendline="ols" if trendline else None,
            color_discrete_sequence=self.default_colors
        )
        
        fig.update_layout(**self.layout_template)
        return fig
    
    def create_multi_chart_dashboard(self,
                                     charts: List[Dict[str, Any]],
                                     title: str = "Dashboard",
                                     rows: int = 2,
                                     cols: int = 2) -> go.Figure:
        """Create a dashboard with multiple charts"""
        fig = make_subplots(
            rows=rows,
            cols=cols,
            subplot_titles=[chart.get('title', '') for chart in charts[:rows*cols]],
            specs=[[{'type': chart.get('type', 'xy')} for _ in range(cols)] for _ in range(rows)]
        )
        
        for idx, chart_config in enumerate(charts[:rows*cols]):
            row = (idx // cols) + 1
            col = (idx % cols) + 1
            
            if 'figure' in chart_config:
                for trace in chart_config['figure'].data:
                    fig.add_trace(trace, row=row, col=col)
        
        fig.update_layout(
            title_text=title,
            height=400 * rows,
            showlegend=True,
            **self.layout_template
        )
        
        return fig
    
    def export_chart_as_image(self, 
                             fig: go.Figure,
                             format: str = 'png',
                             width: int = 800,
                             height: int = 600) -> bytes:
        """Export chart as image bytes"""
        try:
            # Export to bytes
            img_bytes = fig.to_image(format=format, width=width, height=height)
            return img_bytes
        except Exception as e:
            # Fallback to base64 encoded HTML if image export fails
            html = fig.to_html(include_plotlyjs='cdn')
            return html.encode('utf-8')
    
    def get_chart_html(self, fig: go.Figure, include_plotlyjs: str = 'cdn') -> str:
        """Get chart as HTML string"""
        return fig.to_html(include_plotlyjs=include_plotlyjs)
    
    def create_budget_variance_chart(self,
                                     budget_data: pd.DataFrame,
                                     title: str = "Budget vs Actual") -> go.Figure:
        """Create a specialized budget variance chart"""
        fig = go.Figure()
        
        # Budget bars
        fig.add_trace(go.Bar(
            name='Budget',
            x=budget_data.index,
            y=budget_data['budget'],
            marker_color=self.default_colors[0]
        ))
        
        # Actual bars
        fig.add_trace(go.Bar(
            name='Actual',
            x=budget_data.index,
            y=budget_data['actual'],
            marker_color=self.default_colors[1]
        ))
        
        # Variance line
        if 'variance' in budget_data.columns:
            fig.add_trace(go.Scatter(
                name='Variance',
                x=budget_data.index,
                y=budget_data['variance'],
                mode='lines+markers',
                marker_color=self.default_colors[3],
                yaxis='y2'
            ))
        
        fig.update_layout(
            title=title,
            barmode='group',
            yaxis=dict(title='Amount ($)'),
            yaxis2=dict(title='Variance ($)', overlaying='y', side='right'),
            **self.layout_template
        )
        
        return fig
    
    def create_trend_analysis_chart(self,
                                   data: pd.DataFrame,
                                   date_col: str,
                                   value_cols: List[str],
                                   title: str = "Trend Analysis",
                                   show_forecast: bool = False) -> go.Figure:
        """Create a trend analysis chart with optional forecast"""
        fig = go.Figure()
        
        for idx, col in enumerate(value_cols):
            fig.add_trace(go.Scatter(
                x=data[date_col],
                y=data[col],
                mode='lines+markers',
                name=col,
                line=dict(color=self.default_colors[idx % len(self.default_colors)], width=2)
            ))
        
        if show_forecast and 'forecast' in data.columns:
            fig.add_trace(go.Scatter(
                x=data[date_col],
                y=data['forecast'],
                mode='lines',
                name='Forecast',
                line=dict(dash='dash', color='gray'),
                opacity=0.7
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='Value',
            **self.layout_template
        )
        
        return fig