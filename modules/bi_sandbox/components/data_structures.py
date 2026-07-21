"""
Data Structures and Types for BI Sandbox Components

This module contains all the data classes, enums, and type definitions
used across the BI Sandbox components for consistent data handling.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

class VisualizationType(Enum):
    """Extended visualization types beyond basic charts"""
    TABLE = "table"
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    SANKEY = "sankey"
    WATERFALL = "waterfall"
    FUNNEL = "funnel"
    GAUGE = "gauge"
    CANDLESTICK = "candlestick"
    RADAR = "radar"
    PARALLEL_COORDINATES = "parallel_coordinates"
    VIOLIN = "violin"
    BOX = "box"
    HISTOGRAM = "histogram"
    DENSITY = "density"
    CORRELATION_MATRIX = "correlation_matrix"
    REGRESSION = "regression"
    CLUSTER = "cluster"
    FORECAST = "forecast"

@dataclass
class AnalyticsMetric:
    """Advanced analytics metric definition"""
    name: str
    expression: str
    aggregation_type: str
    format_type: str
    description: str
    dependencies: List[str] = None

@dataclass
class DimensionHierarchy:
    """Hierarchical dimension structure"""
    name: str
    levels: List[str]
    parent_child_mapping: Dict[str, str]
    sort_order: str = "asc"

@dataclass
class FilterAction:
    """Advanced filter action definition"""
    source_field: str
    target_field: str
    filter_type: str
    relationship: str

@dataclass
class ChartConfig:
    """Chart configuration data structure"""
    chart_type: str
    title: str
    dimensions: List[str]
    measures: List[str]
    filters: List[FilterAction] = None
    styling: Dict = None
    interactive_features: List[str] = None

@dataclass
class ChartConfiguration:
    """Extended chart configuration for Phase 4 testing"""
    chart_type: str
    title: str = ""
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    color_by: Optional[str] = None
    values: Optional[str] = None
    labels: Optional[str] = None
    category: Optional[str] = None
    filters: List[FilterAction] = None
    styling: Dict = None

@dataclass 
class FilterConfiguration:
    """Filter configuration for advanced filtering"""
    field: str
    operator: str
    value: str
    logic_operator: str = "AND"

@dataclass
class AnalyticsResult:
    """Result container for analytics operations"""
    success: bool
    data: Dict
    message: str = ""
    timestamp: str = ""
    execution_time: float = 0.0

class AggregationType(Enum):
    """Supported aggregation types"""
    SUM = "sum"
    AVERAGE = "mean"
    COUNT = "count"
    MAX = "max"
    MIN = "min"
    MEDIAN = "median"
    STD = "std"
    VAR = "var"

class FilterType(Enum):
    """Supported filter types"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    CONTAINS = "contains"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"

def create_analytics_engine_config():
    """Create default analytics engine configuration"""
    return {
        'name': 'Advanced Analytics Engine',
        'capabilities': [
            'statistical_analysis', 'predictive_modeling', 'trend_analysis',
            'anomaly_detection', 'correlation_analysis', 'regression_modeling'
        ],
        'algorithms': ['linear_regression', 'clustering', 'time_series', 'classification'],
        'status': 'ready'
    }

def create_visualization_engine_config():
    """Create default visualization engine configuration"""
    return {
        'name': 'Custom Visualization Engine',
        'chart_types': [
            'bar', 'line', 'scatter', 'heatmap', 'sankey', 'treemap', 'waterfall',
            'funnel', 'gauge', 'radar', 'box_plot', 'violin_plot', 'candlestick',
            'geographic_map', 'network_graph', 'parallel_coordinates'
        ],
        'interactive_features': [
            'zoom', 'filter', 'drill_down', 'cross_filter', 'brush_select',
            'hover_details', 'click_actions', 'dynamic_updates'
        ],
        'export_formats': ['png', 'svg', 'pdf', 'html', 'json'],
        'status': 'ready'
    }

def create_natural_language_engine_config():
    """Create default natural language engine configuration"""
    return {
        'name': 'Natural Language Query Engine',
        'supported_queries': [
            'summary_statistics', 'data_comparison', 'trend_analysis', 
            'anomaly_detection', 'correlation_discovery', 'what_if_scenarios',
            'budget_variance', 'performance_metrics', 'forecasting'
        ],
        'query_types': [
            'descriptive', 'diagnostic', 'predictive', 'prescriptive'
        ],
        'ai_powered': True,
        'languages': ['english', 'natural_language_sql'],
        'status': 'ready'
    }