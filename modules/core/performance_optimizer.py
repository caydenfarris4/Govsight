"""
Performance Optimizer for GovSight
Centralizes performance improvements across all modules
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import time
from functools import wraps

class PerformanceMonitor:
    """Monitor and optimize performance across GovSight modules"""
    
    def __init__(self):
        self.start_times = {}
        self.performance_log = []
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing and return duration"""
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            self.performance_log.append({
                "operation": operation,
                "duration": duration,
                "timestamp": time.time()
            })
            return duration
        return 0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_log:
            return {"message": "No performance data available"}
        
        recent_operations = self.performance_log[-10:]  # Last 10 operations
        avg_duration = sum(op["duration"] for op in recent_operations) / len(recent_operations)
        
        return {
            "average_duration": avg_duration,
            "total_operations": len(self.performance_log),
            "recent_operations": recent_operations
        }

# Global performance monitor
if 'perf_monitor' not in st.session_state:
    st.session_state.perf_monitor = PerformanceMonitor()

def performance_timer(operation_name: str):
    """Decorator to time function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = st.session_state.perf_monitor
            monitor.start_timer(operation_name)
            result = func(*args, **kwargs)
            duration = monitor.end_timer(operation_name)
            
            # Show performance info if operation takes more than 2 seconds
            if duration > 2.0:
                st.info(f"Performance: {operation_name} completed in {duration:.1f}s")
            
            return result
        return wrapper
    return decorator

@st.cache_data(ttl=900, max_entries=5)  # Cache for 15 minutes
def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize DataFrame memory usage"""
    if df.empty:
        return df
    
    original_memory = df.memory_usage(deep=True).sum()
    
    # Optimize numeric columns
    for col in df.columns:
        if df[col].dtype in ['int64', 'float64']:
            try:
                # Try to downcast to smaller types
                if df[col].dtype == 'int64':
                    df[col] = pd.to_numeric(df[col], downcast='integer')
                elif df[col].dtype == 'float64':
                    df[col] = pd.to_numeric(df[col], downcast='float')
            except:
                pass
        elif df[col].dtype == 'object':
            # Convert to category if suitable
            if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique values
                df[col] = df[col].astype('category')
    
    new_memory = df.memory_usage(deep=True).sum()
    memory_reduction = (original_memory - new_memory) / original_memory * 100
    
    if memory_reduction > 10:  # Only show if significant reduction
        st.caption(f"Memory optimized: {memory_reduction:.1f}% reduction")
    
    return df

@performance_timer("Data Sampling")
def smart_data_sampling(df: pd.DataFrame, max_rows: int = 5000) -> pd.DataFrame:
    """Intelligently sample data for better performance"""
    if len(df) <= max_rows:
        return df
    
    # Use stratified sampling if there are categorical columns
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    
    if len(categorical_cols) > 0 and categorical_cols[0] in df.columns:
        try:
            # Stratified sampling by first categorical column
            sampled = df.groupby(categorical_cols[0]).apply(
                lambda x: x.sample(min(len(x), max_rows // df[categorical_cols[0]].nunique()), 
                                 random_state=42)
            ).reset_index(drop=True)
            
            if len(sampled) > max_rows:
                sampled = sampled.sample(n=max_rows, random_state=42)
                
            return sampled
        except:
            # Fall back to simple random sampling
            pass
    
    # Simple random sampling
    return df.sample(n=max_rows, random_state=42)

@st.cache_data(ttl=300)
def create_performance_optimized_chart(df: pd.DataFrame, chart_type: str, x_col: str, y_col: str = None) -> Dict[str, Any]:
    """Create chart with performance optimizations"""
    
    # Sample data for large datasets
    if len(df) > 2000:
        df_chart = smart_data_sampling(df, 2000)
        sampled = True
    else:
        df_chart = df
        sampled = False
    
    return {
        "data": df_chart,
        "x_col": x_col,
        "y_col": y_col,
        "chart_type": chart_type,
        "sampled": sampled,
        "original_rows": len(df),
        "chart_rows": len(df_chart)
    }

def display_performance_metrics():
    """Display performance metrics in sidebar"""
    monitor = st.session_state.perf_monitor
    summary = monitor.get_performance_summary()
    
    if "average_duration" in summary:
        with st.sidebar:
            with st.expander("Performance Metrics", expanded=False):
                st.metric("Avg Operation Time", f"{summary['average_duration']:.2f}s")
                st.metric("Total Operations", summary['total_operations'])
                
                if summary['recent_operations']:
                    st.caption("Recent Operations:")
                    for op in summary['recent_operations'][-3:]:
                        st.caption(f"• {op['operation']}: {op['duration']:.1f}s")

def enable_performance_mode():
    """Enable performance optimizations across the application"""
    
    # Set performance flags in session state
    if 'performance_mode' not in st.session_state:
        st.session_state.performance_mode = True
        st.session_state.max_chart_points = 2000
        st.session_state.max_table_rows = 1000
        st.session_state.cache_duration = 300  # 5 minutes
    
    # Display performance status
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.caption("⚡ Performance Mode: Enabled")
        with col2:
            if st.button("Clear Cache", help="Clear all cached data"):
                st.cache_data.clear()
                st.success("Cache cleared!")
                st.rerun()
        with col3:
            if st.button("Performance", help="View performance metrics"):
                display_performance_metrics()

# Export main functions
__all__ = [
    'PerformanceMonitor',
    'performance_timer', 
    'optimize_dataframe_memory',
    'smart_data_sampling',
    'create_performance_optimized_chart',
    'enable_performance_mode',
    'display_performance_metrics'
]