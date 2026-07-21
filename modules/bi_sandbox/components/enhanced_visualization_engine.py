"""
Enhanced Visualization Engine for BI Sandbox
Extended functionality for advanced chart types, CSV export, and small multiples

This module extends the base visualization engine with:
- Area charts (regular and stacked)
- Stacked bar charts (horizontal and vertical)
- Enhanced scatter plots with trend lines
- Small multiples visualization
- CSV export functionality
- Advanced configuration options
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Optional, Any, Union
import io
import base64
from datetime import datetime

class EnhancedVisualizationEngine:
    """Enhanced visualization engine with expanded chart types and features"""
    
    def __init__(self):
        self.color_palettes = {
            'default': px.colors.qualitative.Plotly,
            'pastel': px.colors.qualitative.Pastel,
            'bold': px.colors.qualitative.Bold,
            'dark': px.colors.qualitative.Dark24,
            'colorblind': px.colors.qualitative.Safe,
            'viridis': px.colors.sequential.Viridis,
            'plasma': px.colors.sequential.Plasma,
            'blues': px.colors.sequential.Blues,
            'reds': px.colors.sequential.Reds,
            'greens': px.colors.sequential.Greens
        }
        self.current_palette = 'default'
        
    def create_area_chart(self, data: pd.DataFrame, x_col: str, y_col: str, 
                         stacked: bool = False, **kwargs) -> go.Figure:
        """
        Create area chart (regular or stacked)
        
        Args:
            data: DataFrame with data
            x_col: Column name for x-axis
            y_col: Column name for y-axis (or list for multiple series)
            stacked: Whether to create stacked area chart
            **kwargs: Additional chart configuration
        """
        if data.empty or x_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Area Chart: {y_col}')
        color_col = kwargs.get('color', None)
        
        # Handle multiple y columns for stacked area
        if isinstance(y_col, list):
            fig = go.Figure()
            colors = self.color_palettes[self.current_palette]
            
            for i, col in enumerate(y_col):
                if col in data.columns:
                    fig.add_trace(go.Scatter(
                        x=data[x_col],
                        y=data[col],
                        mode='lines',
                        fill='tonexty' if i > 0 and stacked else 'tozeroy',
                        name=col,
                        line=dict(color=colors[i % len(colors)]),
                        stackgroup='one' if stacked else None
                    ))
        else:
            if y_col not in data.columns:
                return go.Figure()
            
            if color_col and color_col in data.columns:
                # Group by color column for multiple areas
                fig = go.Figure()
                colors = self.color_palettes[self.current_palette]
                
                for i, (name, group) in enumerate(data.groupby(color_col)):
                    fig.add_trace(go.Scatter(
                        x=group[x_col],
                        y=group[y_col],
                        mode='lines',
                        fill='tonexty' if i > 0 and stacked else 'tozeroy',
                        name=str(name),
                        line=dict(color=colors[i % len(colors)]),
                        stackgroup='one' if stacked else None
                    ))
            else:
                fig = px.area(data, x=x_col, y=y_col, title=title)
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title=y_col if isinstance(y_col, str) else 'Value',
            hovermode='x unified',
            showlegend=True
        )
        
        return self._apply_custom_config(fig, **kwargs)
    
    def create_stacked_bar_chart(self, data: pd.DataFrame, x_col: str, y_cols: Union[str, List[str]], 
                                horizontal: bool = False, **kwargs) -> go.Figure:
        """
        Create stacked bar chart (horizontal or vertical)
        
        Args:
            data: DataFrame with data
            x_col: Column name for categories
            y_cols: Column name(s) for values (list for stacking)
            horizontal: Whether to create horizontal bar chart
            **kwargs: Additional chart configuration
        """
        if data.empty or x_col not in data.columns:
            return go.Figure()
        
        title = kwargs.get('title', f'Stacked Bar Chart: {x_col}')
        
        # Convert single column to list for consistency
        if isinstance(y_cols, str):
            y_cols = [y_cols]
        
        # Filter valid columns
        y_cols = [col for col in y_cols if col in data.columns]
        if not y_cols:
            return go.Figure()
        
        fig = go.Figure()
        colors = self.color_palettes[self.current_palette]
        
        for i, col in enumerate(y_cols):
            if horizontal:
                fig.add_trace(go.Bar(
                    y=data[x_col],
                    x=data[col],
                    name=col,
                    orientation='h',
                    marker_color=colors[i % len(colors)]
                ))
            else:
                fig.add_trace(go.Bar(
                    x=data[x_col],
                    y=data[col],
                    name=col,
                    marker_color=colors[i % len(colors)]
                ))
        
        fig.update_layout(
            title=title,
            barmode='stack',
            xaxis_title=x_col if not horizontal else 'Value',
            yaxis_title='Value' if not horizontal else x_col,
            hovermode='closest',
            showlegend=True
        )
        
        return self._apply_custom_config(fig, **kwargs)
    
    def create_scatter_with_trendline(self, data: pd.DataFrame, x_col: str, y_col: str, 
                                     trendline: str = 'ols', **kwargs) -> go.Figure:
        """
        Create scatter plot with trend line and correlation analysis
        
        Args:
            data: DataFrame with data
            x_col: Column name for x-axis
            y_col: Column name for y-axis
            trendline: Type of trendline ('ols', 'lowess', 'polynomial')
            **kwargs: Additional chart configuration
        """
        if data.empty or x_col not in data.columns or y_col not in data.columns:
            return go.Figure()
        
        # Remove NaN values for correlation calculation
        clean_data = data[[x_col, y_col]].dropna()
        
        # Calculate correlation
        if len(clean_data) > 1:
            correlation = clean_data[x_col].corr(clean_data[y_col])
            r_squared = correlation ** 2
        else:
            correlation = 0
            r_squared = 0
        
        title = kwargs.get('title', f'{y_col} vs {x_col} (R²={r_squared:.3f})')
        color_col = kwargs.get('color', None)
        size_col = kwargs.get('size', None)
        
        # Create scatter plot with trendline
        fig_kwargs = {
            'data_frame': data,
            'x': x_col,
            'y': y_col,
            'title': title,
            'trendline': trendline if trendline != 'none' else None
        }
        
        if color_col and color_col in data.columns:
            fig_kwargs['color'] = color_col
        
        if size_col and size_col in data.columns:
            fig_kwargs['size'] = size_col
        
        fig = px.scatter(**fig_kwargs)
        
        # Add correlation info to layout
        fig.update_layout(
            annotations=[
                dict(
                    x=0.05, y=0.95,
                    xref='paper', yref='paper',
                    text=f'Correlation: {correlation:.3f}<br>R²: {r_squared:.3f}',
                    showarrow=False,
                    font=dict(size=12),
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='black',
                    borderwidth=1
                )
            ]
        )
        
        return self._apply_custom_config(fig, **kwargs)
    
    def create_enhanced_heatmap(self, data: pd.DataFrame, correlation: bool = False, 
                               annotate: bool = True, **kwargs) -> go.Figure:
        """
        Create enhanced heatmap with correlation matrix option
        
        Args:
            data: DataFrame with data
            correlation: Whether to create correlation matrix
            annotate: Whether to show values in cells
            **kwargs: Additional chart configuration
        """
        if data.empty:
            return go.Figure()
        
        if correlation:
            # Create correlation matrix
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) < 2:
                return go.Figure()
            
            corr_matrix = data[numeric_cols].corr()
            title = kwargs.get('title', 'Correlation Matrix')
            
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdBu',
                zmid=0,
                text=corr_matrix.values.round(2) if annotate else None,
                texttemplate='%{text}' if annotate else None,
                textfont={"size": 10},
                colorbar=dict(title="Correlation")
            ))
        else:
            # Regular heatmap with specified columns
            x_col = kwargs.get('x_col')
            y_col = kwargs.get('y_col')
            z_col = kwargs.get('z_col')
            
            if not all([x_col, y_col, z_col]):
                return go.Figure()
            
            # Pivot data for heatmap
            pivot_data = data.pivot_table(
                values=z_col, 
                index=y_col, 
                columns=x_col, 
                aggfunc='mean'
            )
            
            title = kwargs.get('title', f'Heatmap: {z_col}')
            
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale=kwargs.get('colorscale', 'Viridis'),
                text=pivot_data.values.round(2) if annotate else None,
                texttemplate='%{text}' if annotate else None,
                textfont={"size": 10},
                colorbar=dict(title=z_col)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=kwargs.get('x_label', ''),
            yaxis_title=kwargs.get('y_label', '')
        )
        
        return self._apply_custom_config(fig, **kwargs)
    
    def create_small_multiples(self, data: pd.DataFrame, chart_type: str, 
                             facet_col: str, metrics: List[str], 
                             rows: int = None, cols: int = None, **kwargs) -> go.Figure:
        """
        Create small multiples visualization
        
        Args:
            data: DataFrame with data
            chart_type: Type of chart for each facet ('bar', 'line', 'scatter', 'area')
            facet_col: Column to facet by
            metrics: List of metric columns to plot
            rows: Number of subplot rows (auto-calculated if None)
            cols: Number of subplot columns (auto-calculated if None)
            **kwargs: Additional chart configuration
        """
        if data.empty or facet_col not in data.columns:
            return go.Figure()
        
        # Get unique facet values
        facet_values = data[facet_col].unique()
        n_facets = len(facet_values)
        
        # Auto-calculate grid dimensions if not provided
        if rows is None or cols is None:
            cols = min(3, n_facets)  # Max 3 columns
            rows = (n_facets + cols - 1) // cols
        
        # Create subplots
        subplot_titles = [f"{facet_col}: {val}" for val in facet_values]
        fig = make_subplots(
            rows=rows, 
            cols=cols,
            subplot_titles=subplot_titles[:n_facets],
            shared_xaxes=kwargs.get('shared_xaxes', False),
            shared_yaxes=kwargs.get('shared_yaxes', False),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        colors = self.color_palettes[self.current_palette]
        
        # Create each subplot
        for idx, facet_value in enumerate(facet_values):
            if idx >= rows * cols:
                break
                
            row = idx // cols + 1
            col = idx % cols + 1
            
            # Filter data for this facet
            facet_data = data[data[facet_col] == facet_value]
            
            # Add traces based on chart type
            for metric_idx, metric in enumerate(metrics):
                if metric not in facet_data.columns:
                    continue
                
                x_col = kwargs.get('x_col', facet_data.columns[0])
                
                if chart_type == 'bar':
                    fig.add_trace(
                        go.Bar(
                            x=facet_data[x_col],
                            y=facet_data[metric],
                            name=metric,
                            marker_color=colors[metric_idx % len(colors)],
                            showlegend=(idx == 0)  # Only show legend for first subplot
                        ),
                        row=row, col=col
                    )
                elif chart_type == 'line':
                    fig.add_trace(
                        go.Scatter(
                            x=facet_data[x_col],
                            y=facet_data[metric],
                            mode='lines',
                            name=metric,
                            line=dict(color=colors[metric_idx % len(colors)]),
                            showlegend=(idx == 0)
                        ),
                        row=row, col=col
                    )
                elif chart_type == 'scatter':
                    fig.add_trace(
                        go.Scatter(
                            x=facet_data[x_col],
                            y=facet_data[metric],
                            mode='markers',
                            name=metric,
                            marker=dict(color=colors[metric_idx % len(colors)]),
                            showlegend=(idx == 0)
                        ),
                        row=row, col=col
                    )
                elif chart_type == 'area':
                    fig.add_trace(
                        go.Scatter(
                            x=facet_data[x_col],
                            y=facet_data[metric],
                            mode='lines',
                            fill='tozeroy',
                            name=metric,
                            line=dict(color=colors[metric_idx % len(colors)]),
                            showlegend=(idx == 0)
                        ),
                        row=row, col=col
                    )
        
        # Update layout
        title = kwargs.get('title', f'Small Multiples: {", ".join(metrics)} by {facet_col}')
        fig.update_layout(
            title=title,
            height=300 * rows,
            showlegend=True,
            hovermode='closest'
        )
        
        return self._apply_custom_config(fig, **kwargs)
    
    def generate_csv_export(self, data: pd.DataFrame, chart_type: str, 
                          metadata: Dict[str, Any] = None) -> str:
        """
        Generate CSV export with metadata for chart data
        
        Args:
            data: DataFrame to export
            chart_type: Type of chart the data represents
            metadata: Additional metadata to include
        
        Returns:
            CSV string with metadata headers
        """
        output = io.StringIO()
        
        # Add metadata headers
        output.write(f"# GovSight BI Sandbox Export\n")
        output.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write(f"# Chart Type: {chart_type}\n")
        
        if metadata:
            for key, value in metadata.items():
                output.write(f"# {key}: {value}\n")
        
        output.write(f"# Total Records: {len(data)}\n")
        output.write(f"# Columns: {', '.join(data.columns)}\n")
        output.write("#\n")
        
        # Add summary statistics for numeric columns
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            output.write("# Summary Statistics:\n")
            for col in numeric_cols:
                output.write(f"#   {col}: Mean={data[col].mean():.2f}, ")
                output.write(f"Std={data[col].std():.2f}, ")
                output.write(f"Min={data[col].min():.2f}, ")
                output.write(f"Max={data[col].max():.2f}\n")
            output.write("#\n")
        
        # Write the actual data
        data.to_csv(output, index=False)
        
        return output.getvalue()
    
    def create_advanced_config_panel(self) -> Dict[str, Any]:
        """
        Create configuration options for advanced chart customization
        
        Returns:
            Dictionary of configuration options
        """
        return {
            'color_palette': {
                'label': 'Color Palette',
                'type': 'select',
                'options': list(self.color_palettes.keys()),
                'default': 'default',
                'description': 'Choose color scheme for charts'
            },
            'chart_height': {
                'label': 'Chart Height',
                'type': 'slider',
                'min': 300,
                'max': 1000,
                'default': 500,
                'step': 50,
                'description': 'Adjust chart height in pixels'
            },
            'show_grid': {
                'label': 'Show Grid',
                'type': 'checkbox',
                'default': True,
                'description': 'Show gridlines on chart'
            },
            'show_legend': {
                'label': 'Show Legend',
                'type': 'checkbox',
                'default': True,
                'description': 'Display chart legend'
            },
            'legend_position': {
                'label': 'Legend Position',
                'type': 'select',
                'options': ['right', 'top', 'bottom', 'left'],
                'default': 'right',
                'description': 'Position of legend'
            },
            'axis_range': {
                'label': 'Custom Axis Range',
                'type': 'range',
                'description': 'Set custom min/max for axes'
            },
            'annotations': {
                'label': 'Annotations',
                'type': 'text_list',
                'description': 'Add text annotations to chart'
            },
            'reference_lines': {
                'label': 'Reference Lines',
                'type': 'number_list',
                'description': 'Add horizontal/vertical reference lines'
            },
            'title_size': {
                'label': 'Title Size',
                'type': 'slider',
                'min': 12,
                'max': 32,
                'default': 20,
                'step': 2,
                'description': 'Font size for chart title'
            },
            'axis_labels': {
                'label': 'Custom Axis Labels',
                'type': 'text',
                'description': 'Override default axis labels'
            },
            'data_labels': {
                'label': 'Show Data Labels',
                'type': 'checkbox',
                'default': False,
                'description': 'Display values on data points'
            },
            'transparency': {
                'label': 'Transparency',
                'type': 'slider',
                'min': 0,
                'max': 1,
                'default': 1,
                'step': 0.1,
                'description': 'Adjust chart transparency'
            },
            'animation': {
                'label': 'Enable Animation',
                'type': 'checkbox',
                'default': True,
                'description': 'Animate chart transitions'
            }
        }
    
    def _apply_custom_config(self, fig: go.Figure, **kwargs) -> go.Figure:
        """
        Apply custom configuration options to a figure
        
        Args:
            fig: Plotly figure to customize
            **kwargs: Configuration options
        
        Returns:
            Customized figure
        """
        # Apply height
        if 'height' in kwargs:
            fig.update_layout(height=kwargs['height'])
        
        # Apply color palette
        if 'color_palette' in kwargs and kwargs['color_palette'] in self.color_palettes:
            self.current_palette = kwargs['color_palette']
        
        # Apply grid
        if 'show_grid' in kwargs:
            fig.update_xaxes(showgrid=kwargs['show_grid'])
            fig.update_yaxes(showgrid=kwargs['show_grid'])
        
        # Apply legend settings
        if 'show_legend' in kwargs:
            fig.update_layout(showlegend=kwargs['show_legend'])
        
        if 'legend_position' in kwargs:
            positions = {
                'right': dict(yanchor="top", y=1, xanchor="left", x=1.02),
                'top': dict(yanchor="bottom", y=1.02, xanchor="center", x=0.5, orientation="h"),
                'bottom': dict(yanchor="top", y=-0.15, xanchor="center", x=0.5, orientation="h"),
                'left': dict(yanchor="top", y=1, xanchor="right", x=-0.02)
            }
            if kwargs['legend_position'] in positions:
                fig.update_layout(legend=positions[kwargs['legend_position']])
        
        # Apply custom axis ranges
        if 'x_range' in kwargs:
            fig.update_xaxes(range=kwargs['x_range'])
        if 'y_range' in kwargs:
            fig.update_yaxes(range=kwargs['y_range'])
        
        # Apply reference lines
        if 'reference_lines' in kwargs:
            for line in kwargs['reference_lines']:
                if 'y' in line:
                    fig.add_hline(y=line['y'], line_dash="dash", 
                                line_color="gray", opacity=0.7,
                                annotation_text=line.get('label', ''))
                if 'x' in line:
                    fig.add_vline(x=line['x'], line_dash="dash",
                                line_color="gray", opacity=0.7,
                                annotation_text=line.get('label', ''))
        
        # Apply annotations
        if 'annotations' in kwargs:
            annotations = []
            for ann in kwargs['annotations']:
                annotations.append(dict(
                    x=ann.get('x', 0.5),
                    y=ann.get('y', 0.5),
                    xref=ann.get('xref', 'paper'),
                    yref=ann.get('yref', 'paper'),
                    text=ann.get('text', ''),
                    showarrow=ann.get('showarrow', True),
                    font=dict(size=ann.get('size', 12))
                ))
            fig.update_layout(annotations=annotations)
        
        # Apply title customization
        if 'title_size' in kwargs:
            fig.update_layout(title_font_size=kwargs['title_size'])
        
        # Apply axis labels
        if 'x_label' in kwargs:
            fig.update_xaxes(title_text=kwargs['x_label'])
        if 'y_label' in kwargs:
            fig.update_yaxes(title_text=kwargs['y_label'])
        
        # Apply transparency
        if 'transparency' in kwargs:
            opacity = kwargs['transparency']
            for trace in fig.data:
                trace.opacity = opacity
        
        return fig

# Convenience function for integration
def create_enhanced_visualization_engine() -> EnhancedVisualizationEngine:
    """Create and return an instance of the enhanced visualization engine"""
    return EnhancedVisualizationEngine()