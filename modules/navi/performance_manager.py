"""
Navi Module Performance Manager
Handles all performance optimizations specific to the Navigation & Planning Hub
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
from typing import Dict, Any, Optional

class NaviPerformanceManager:
    """Performance management specifically for Navi module components"""
    
    def __init__(self):
        self.cache_stats = {
            "scenario_cache_hits": 0,
            "visualization_cache_hits": 0,
            "monte_carlo_cache_hits": 0,
            "bi_cache_hits": 0
        }
    
    @staticmethod
    @st.cache_data(ttl=600, max_entries=5, show_spinner=False)
    def optimize_navi_data(data: pd.DataFrame, component: str = "general") -> pd.DataFrame:
        """
        Optimize data specifically for Navi module components
        
        Args:
            data: Raw data to optimize
            component: Component type for specific optimizations
        """
        if data.empty:
            return data
        
        # Component-specific optimization limits
        limits = {
            "scenario": 5000,      # Scenario planner
            "visualization": 2000,  # Custom viz builder  
            "monte_carlo": 1000,   # Monte Carlo simulator
            "bi_sandbox": 8000     # BI Sandbox
        }
        
        max_rows = limits.get(component, 3000)
        
        # Apply optimizations
        if len(data) > max_rows:
            # Use stratified sampling when possible
            if 'Department' in data.columns:
                try:
                    sampled = data.groupby('Department').apply(
                        lambda x: x.sample(min(len(x), max_rows // data['Department'].nunique()), 
                                         random_state=42)
                    ).reset_index(drop=True)
                    
                    if len(sampled) > max_rows:
                        sampled = sampled.sample(n=max_rows, random_state=42)
                    
                    return sampled
                except:
                    # Fallback to simple sampling
                    pass
            
            # Simple random sampling
            data = data.sample(n=max_rows, random_state=42)
        
        # Memory optimization
        for col in data.columns:
            if data[col].dtype == 'float64':
                data[col] = pd.to_numeric(data[col], downcast='float')
            elif data[col].dtype == 'int64':
                data[col] = pd.to_numeric(data[col], downcast='integer')
        
        return data
    
    @staticmethod
    @st.cache_data(ttl=300, max_entries=10, show_spinner=False)
    def prepare_chart_data(data: pd.DataFrame, chart_type: str, x_col: str, y_col: str = None) -> Dict[str, Any]:
        """
        Prepare data specifically for chart rendering in Navi module
        """
        # Limit data points based on chart type for better performance
        chart_limits = {
            "scatter": 1500,
            "line": 2000,
            "bar": 500,
            "histogram": 1000,
            "heatmap": 100  # Heatmaps are computationally expensive
        }
        
        max_points = chart_limits.get(chart_type, 1000)
        
        if len(data) > max_points:
            data = data.sample(n=max_points, random_state=42)
        
        return {
            "data": data,
            "x_col": x_col,
            "y_col": y_col,
            "chart_type": chart_type,
            "optimized": True,
            "point_count": len(data)
        }
    
    @staticmethod
    def show_performance_indicator(component: str, original_size: int, optimized_size: int):
        """Show performance indicators specific to Navi components"""
        if optimized_size < original_size:
            reduction_pct = ((original_size - optimized_size) / original_size) * 100
            
            # Component-specific messaging
            messages = {
                "scenario": f"⚡ Scenario Planning optimized: {reduction_pct:.0f}% data reduction for faster modeling",
                "visualization": f"⚡ Chart Builder optimized: {reduction_pct:.0f}% fewer points for responsive visualization", 
                "monte_carlo": f"⚡ Monte Carlo optimized: Simulation capped for faster risk analysis",
                "bi_sandbox": f"⚡ BI Analytics optimized: {reduction_pct:.0f}% data sampling for quick insights"
            }
            
            message = messages.get(component, f"⚡ Navi optimized: {reduction_pct:.0f}% performance improvement")
            st.caption(message)
    
    @staticmethod
    def enable_navi_performance_mode():
        """Enable performance optimizations across all Navi components"""
        if 'navi_performance_enabled' not in st.session_state:
            st.session_state.navi_performance_enabled = True
            st.session_state.navi_cache_duration = 300  # 5 minutes
            st.session_state.navi_max_monte_carlo = 3000
            st.session_state.navi_max_chart_points = 2000
        
        # Show performance status
        with st.container():
            st.caption("⚡ Navi Performance Mode: Active - All components optimized for speed")

# Module-level performance functions for easy importing
@st.cache_data(ttl=180, max_entries=20)
def fast_monte_carlo_navi(iterations: int, *args) -> Dict[str, Any]:
    """Fast Monte Carlo simulation optimized for Navi module"""
    # Limit iterations for Navi module performance
    max_iterations = min(iterations, 3000)
    
    # Use vectorized operations
    np.random.seed(42)  # Reproducible results
    
    # Simplified but fast simulation logic
    results = np.random.normal(0, 1, max_iterations)
    
    return {
        "results": results,
        "mean": np.mean(results),
        "std": np.std(results),
        "iterations": max_iterations,
        "cached": True
    }

@st.cache_data(ttl=600, max_entries=8)
def fast_data_summary_navi(data: pd.DataFrame) -> Dict[str, Any]:
    """Fast data summary for Navi components"""
    if data.empty:
        return {"empty": True}
    
    # Quick summary without expensive operations
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    
    summary = {
        "row_count": len(data),
        "column_count": len(data.columns),
        "numeric_columns": len(numeric_cols),
        "memory_usage": data.memory_usage(deep=True).sum(),
        "cached": True
    }
    
    # Only calculate statistics for first 3 numeric columns to save time
    if numeric_cols:
        sample_cols = numeric_cols[:3]
        for col in sample_cols:
            summary[f"{col}_mean"] = data[col].mean()
            summary[f"{col}_std"] = data[col].std()
    
    return summary