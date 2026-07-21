"""
BI Sandbox Chart Builder - Chart creation and configuration
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional, Tuple, List

def create_chart(df: pd.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Create a chart based on configuration
    
    Args:
        df: DataFrame with data
        config: Chart configuration dictionary
        
    Returns:
        Plotly figure or None if error
    """
    
    if df.empty:
        st.warning("No data available for charting")
        return None
    
    try:
        # Process data based on configuration
        processed_df = process_chart_data(df, config)
        
        if processed_df.empty:
            st.warning("No data after processing")
            return None
        
        # Create chart based on type
        chart_type = config.get('chart_type', 'Bar Chart')
        
        if chart_type == 'Bar Chart':
            return create_bar_chart(processed_df, config)
        elif chart_type == 'Line Chart':
            return create_line_chart(processed_df, config)
        elif chart_type == 'Pie Chart':
            return create_pie_chart(processed_df, config)
        elif chart_type == 'Scatter Plot':
            return create_scatter_plot(processed_df, config)
        elif chart_type == 'Table':
            return create_table_display(processed_df, config)
        else:
            st.error(f"Unsupported chart type: {chart_type}")
            return None
            
    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")
        return None

def process_chart_data(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Process data for charting based on configuration"""
    
    dimensions = config.get('dimensions', [])
    measure = config.get('measure', '')
    aggregation = config.get('aggregation', 'Sum')
    
    if not dimensions or not measure:
        return df
    
    # Handle calculated measures
    if measure == 'Budget - Actual':
        if 'Budget' in df.columns and 'Actual' in df.columns:
            df = df.copy()
            df['Budget - Actual'] = df['Budget'] - df['Actual']
        else:
            st.warning("Budget and Actual columns required for variance calculation")
            return pd.DataFrame()
    
    elif measure == 'Actual/Budget Ratio':
        if 'Budget' in df.columns and 'Actual' in df.columns:
            df = df.copy()
            df['Actual/Budget Ratio'] = df['Actual'] / df['Budget'].replace(0, 1)
        else:
            st.warning("Budget and Actual columns required for ratio calculation")
            return pd.DataFrame()
    
    # Group by dimensions and aggregate
    if measure in df.columns:
        agg_func = get_aggregation_function(aggregation)
        
        try:
            grouped_df = df.groupby(dimensions)[measure].agg(agg_func).reset_index()
            return grouped_df
        except Exception as e:
            st.warning(f"Error in aggregation: {str(e)}")
            return df
    else:
        st.warning(f"Measure column '{measure}' not found in data")
        return df

def get_aggregation_function(aggregation: str):
    """Get pandas aggregation function"""
    agg_map = {
        'Sum': 'sum',
        'Average': 'mean',
        'Count': 'count',
        'Min': 'min',
        'Max': 'max'
    }
    return agg_map.get(aggregation, 'sum')

def create_bar_chart(df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
    """Create a bar chart"""
    
    dimensions = config.get('dimensions', [])
    measure = config.get('measure', '')
    
    if len(dimensions) == 1:
        # Simple bar chart
        fig = px.bar(
            df, 
            x=dimensions[0], 
            y=measure,
            title=f"{measure} by {dimensions[0]}",
            labels={measure: measure, dimensions[0]: dimensions[0]}
        )
    else:
        # Grouped bar chart
        fig = px.bar(
            df,
            x=dimensions[0],
            y=measure,
            color=dimensions[1] if len(dimensions) > 1 else None,
            title=f"{measure} by {' and '.join(dimensions)}",
            labels={measure: measure}
        )
    
    # Update layout for better appearance
    fig.update_layout(
        template='plotly_white',
        height=500,
        showlegend=len(dimensions) > 1
    )
    
    return fig

def create_line_chart(df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
    """Create a line chart"""
    
    dimensions = config.get('dimensions', [])
    measure = config.get('measure', '')
    
    fig = px.line(
        df,
        x=dimensions[0],
        y=measure,
        color=dimensions[1] if len(dimensions) > 1 else None,
        title=f"{measure} Trend by {dimensions[0]}",
        markers=True
    )
    
    fig.update_layout(
        template='plotly_white',
        height=500,
        showlegend=len(dimensions) > 1
    )
    
    return fig

def create_pie_chart(df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
    """Create a pie chart"""
    
    dimensions = config.get('dimensions', [])
    measure = config.get('measure', '')
    
    # Pie charts work best with single dimension
    dimension = dimensions[0] if dimensions else None
    
    if not dimension:
        st.warning("Pie charts require at least one dimension")
        return go.Figure()
    
    fig = px.pie(
        df,
        names=dimension,
        values=measure,
        title=f"{measure} Distribution by {dimension}"
    )
    
    fig.update_layout(
        template='plotly_white',
        height=500
    )
    
    return fig

def create_scatter_plot(df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
    """Create a scatter plot"""
    
    dimensions = config.get('dimensions', [])
    measure = config.get('measure', '')
    
    # For scatter plot, we need at least 2 numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if len(numeric_cols) < 2:
        st.warning("Scatter plots require at least 2 numeric columns")
        return go.Figure()
    
    x_col = numeric_cols[0]
    y_col = measure if measure in numeric_cols else numeric_cols[1]
    
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=dimensions[0] if dimensions else None,
        title=f"{y_col} vs {x_col}",
        labels={x_col: x_col, y_col: y_col}
    )
    
    fig.update_layout(
        template='plotly_white',
        height=500
    )
    
    return fig

def create_table_display(df: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
    """Create a table visualization"""
    
    # Limit rows for display performance
    display_df = df.head(100)
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(display_df.columns),
            fill_color='lightblue',
            align='left',
            font=dict(size=12)
        ),
        cells=dict(
            values=[display_df[col] for col in display_df.columns],
            fill_color='white',
            align='left',
            font=dict(size=10)
        )
    )])
    
    fig.update_layout(
        title="Data Table View",
        height=500
    )
    
    if len(df) > 100:
        st.info(f"Showing first 100 rows of {len(df)} total rows")
    
    return fig

def save_chart_config(config: Dict[str, Any]) -> bool:
    """Save chart configuration to session state"""
    
    try:
        if 'chart_configs' not in st.session_state:
            st.session_state.chart_configs = []
        
        st.session_state.chart_configs.append(config)
        return True
        
    except Exception as e:
        st.error(f"Error saving chart configuration: {str(e)}")
        return False

def get_chart_preview_data(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Get preview data for chart configuration"""
    
    processed_df = process_chart_data(df, config)
    
    preview = {
        'row_count': len(processed_df),
        'columns': list(processed_df.columns),
        'sample_data': processed_df.head(5).to_dict('records') if not processed_df.empty else []
    }
    
    return preview

def validate_chart_config(config: Dict[str, Any], df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate chart configuration against available data"""
    
    errors = []
    
    # Check required fields
    if not config.get('dimensions'):
        errors.append("At least one dimension is required")
    
    if not config.get('measure'):
        errors.append("A measure field is required")
    
    # Check if columns exist in data
    dimensions = config.get('dimensions', [])
    measure = config.get('measure', '')
    
    for dim in dimensions:
        if dim not in df.columns:
            errors.append(f"Dimension '{dim}' not found in data")
    
    if measure not in df.columns and measure not in ['Budget - Actual', 'Actual/Budget Ratio']:
        errors.append(f"Measure '{measure}' not found in data")
    
    # Check chart type compatibility
    chart_type = config.get('chart_type', '')
    if chart_type == 'Pie Chart' and len(dimensions) > 1:
        errors.append("Pie charts work best with a single dimension")
    
    return len(errors) == 0, errors