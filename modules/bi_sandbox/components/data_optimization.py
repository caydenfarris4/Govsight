"""
Data Optimization and Performance Enhancement Module

This module provides optimized data loading, caching, and preprocessing
functions to ensure maximum performance for large datasets.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from modules.database.db_connection import load_org_data

@st.cache_data(ttl=600, max_entries=10)  # Cache for 10 minutes, max 10 orgs
def load_org_data_optimized(org: str) -> pd.DataFrame:
    """Optimized data loading with aggressive caching and memory optimization"""
    try:
        data = load_org_data(org)
        if data.empty:
            return pd.DataFrame()
        
        # Optimize data types to reduce memory usage by up to 75%
        for col in data.columns:
            if data[col].dtype == 'object':
                try:
                    # Try to convert to numeric if possible
                    numeric_data = pd.to_numeric(data[col], errors='coerce')
                    if not numeric_data.isna().all():
                        data[col] = numeric_data
                    else:
                        # Convert object columns to category for memory efficiency
                        unique_vals = data[col].nunique()
                        if unique_vals < len(data) * 0.5:  # If less than 50% unique values
                            data[col] = data[col].astype('category')
                except Exception:
                    continue
        
        return data
    except Exception as e:
        st.error(f"Data loading error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300, max_entries=20)  # Cache processed data for 5 minutes
def process_data_for_analysis(data: pd.DataFrame) -> Dict[str, Any]:
    """Pre-process data for analysis with caching"""
    if data.empty:
        return {"numeric_columns": [], "categorical_columns": [], "summary": {}}
    
    numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
    
    # Pre-compute summary statistics only for first 5 numeric columns for speed
    summary = {}
    if numeric_columns:
        sample_cols = numeric_columns[:5]  # Limit to 5 columns for performance
        summary = data[sample_cols].describe().to_dict()
    
    return {
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns, 
        "summary": summary,
        "row_count": len(data),
        "col_count": len(data.columns)
    }

@st.cache_data(ttl=600)  # Cache chart data
def create_chart_data_optimized(data: pd.DataFrame, chart_type: str, x_col: str, y_col: str = None) -> Dict[str, Any]:
    """Optimized chart data preparation with intelligent sampling"""
    if data.empty:
        return {"error": "No data available"}
    
    # Dynamic sampling based on chart type and data complexity
    if chart_type in ['scatter', 'line']:
        sample_size = min(len(data), 10000)  # More points for scatter/line charts
    elif chart_type in ['heatmap', 'treemap']:
        sample_size = min(len(data), 2500)   # Fewer points for complex visualizations
    else:
        sample_size = min(len(data), 5000)   # Standard sampling
    
    # Use stratified sampling to preserve data distribution
    sampled_data = data
    if len(data) > sample_size:
        if x_col in data.columns and data[x_col].dtype in ['object', 'category']:
            # Stratified sampling based on categorical column
            try:
                sampled_data = data.groupby(x_col, group_keys=False).apply(
                    lambda x: x.sample(min(len(x), max(1, sample_size // data[x_col].nunique())), 
                                      random_state=42)
                ).reset_index(drop=True)
            except Exception:
                sampled_data = data.sample(n=sample_size, random_state=42)
        else:
            sampled_data = data.sample(n=sample_size, random_state=42)
        
    chart_data = {
        "data": sampled_data,
        "x_col": x_col,
        "y_col": y_col,
        "chart_type": chart_type,
        "sampled": len(sampled_data) < len(data),
        "original_size": len(data),
        "sample_size": len(sampled_data)
    }
    
    return chart_data

def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize DataFrame memory usage"""
    if df.empty:
        return df
    
    optimized_df = df.copy()
    
    # Optimize numeric columns
    for col in optimized_df.select_dtypes(include=[np.number]):
        col_data = optimized_df[col]
        
        # Check if integer
        if col_data.dtype in ['int64', 'int32']:
            if col_data.min() >= np.iinfo(np.int8).min and col_data.max() <= np.iinfo(np.int8).max:
                optimized_df[col] = col_data.astype(np.int8)
            elif col_data.min() >= np.iinfo(np.int16).min and col_data.max() <= np.iinfo(np.int16).max:
                optimized_df[col] = col_data.astype(np.int16)
            elif col_data.min() >= np.iinfo(np.int32).min and col_data.max() <= np.iinfo(np.int32).max:
                optimized_df[col] = col_data.astype(np.int32)
        
        # Check if float can be downcast
        elif col_data.dtype in ['float64']:
            if col_data.min() >= np.finfo(np.float32).min and col_data.max() <= np.finfo(np.float32).max:
                optimized_df[col] = col_data.astype(np.float32)
    
    # Optimize object columns to category where appropriate
    for col in optimized_df.select_dtypes(include=['object']):
        num_unique_values = optimized_df[col].nunique()
        num_total_values = len(optimized_df[col])
        
        # If less than 50% unique values, convert to category
        if num_unique_values / num_total_values < 0.5:
            optimized_df[col] = optimized_df[col].astype('category')
    
    return optimized_df

def get_data_quality_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Get comprehensive data quality metrics"""
    if df.empty:
        return {}
    
    metrics = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
        'missing_values': df.isnull().sum().to_dict(),
        'duplicate_rows': df.duplicated().sum(),
        'numeric_columns': len(df.select_dtypes(include=[np.number]).columns),
        'categorical_columns': len(df.select_dtypes(include=['object', 'category']).columns),
        'datetime_columns': len(df.select_dtypes(include=['datetime64']).columns)
    }
    
    # Calculate missing value percentage
    metrics['missing_percentage'] = {
        col: (missing / len(df)) * 100 
        for col, missing in metrics['missing_values'].items()
        if missing > 0
    }
    
    return metrics

def create_data_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Create comprehensive data profile for analysis"""
    if df.empty:
        return {}
    
    profile = {
        'shape': df.shape,
        'dtypes': df.dtypes.to_dict(),
        'quality_metrics': get_data_quality_metrics(df),
        'summary_stats': {},
        'categorical_info': {}
    }
    
    # Numeric column statistics
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        profile['summary_stats'] = df[numeric_cols].describe().to_dict()
    
    # Categorical column information
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        profile['categorical_info'][col] = {
            'unique_values': df[col].nunique(),
            'top_values': df[col].value_counts().head(10).to_dict()
        }
    
    return profile

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def precompute_aggregations(df: pd.DataFrame, group_cols: List[str], agg_cols: List[str]) -> Dict[str, pd.DataFrame]:
    """Precompute common aggregations for faster dashboard performance"""
    if df.empty or not group_cols or not agg_cols:
        return {}
    
    aggregations = {}
    
    try:
        # Basic aggregations
        for agg_func in ['sum', 'mean', 'count', 'max', 'min']:
            key = f"{'-'.join(group_cols)}_{agg_func}"
            aggregations[key] = df.groupby(group_cols)[agg_cols].agg(agg_func).reset_index()
        
        # Time-based aggregations if date column exists
        date_cols = df.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0 and len(group_cols) == 1 and group_cols[0] in date_cols:
            date_col = group_cols[0]
            # Monthly aggregations
            df_monthly = df.copy()
            df_monthly['year_month'] = df[date_col].dt.to_period('M')
            aggregations['monthly_sum'] = df_monthly.groupby('year_month')[agg_cols].sum().reset_index()
            aggregations['monthly_avg'] = df_monthly.groupby('year_month')[agg_cols].mean().reset_index()
            
    except Exception as e:
        st.warning(f"Error precomputing aggregations: {e}")
    
    return aggregations

def validate_data_for_visualization(df: pd.DataFrame, chart_type: str, required_cols: List[str]) -> Dict[str, Any]:
    """Validate data suitability for specific visualization types"""
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'recommendations': []
    }
    
    # Check if required columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Missing required columns: {missing_cols}")
        return validation_result
    
    # Chart-specific validations
    if chart_type in ['bar', 'line', 'scatter']:
        numeric_cols = df[required_cols].select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            validation_result['errors'].append("No numeric columns found for chart")
            validation_result['valid'] = False
    
    elif chart_type == 'pie':
        if len(required_cols) < 2:
            validation_result['errors'].append("Pie chart requires at least 2 columns")
            validation_result['valid'] = False
    
    elif chart_type == 'heatmap':
        if len(df) > 1000:
            validation_result['warnings'].append("Large dataset may impact heatmap performance")
            validation_result['recommendations'].append("Consider filtering or sampling data")
    
    # General data quality checks
    for col in required_cols:
        if col in df.columns:
            null_percentage = df[col].isnull().mean() * 100
            if null_percentage > 50:
                validation_result['warnings'].append(f"Column '{col}' has {null_percentage:.1f}% missing values")
    
    return validation_result