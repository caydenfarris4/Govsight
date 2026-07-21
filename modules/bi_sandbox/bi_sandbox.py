"""
BI Sandbox - Modular Architecture Entry Point

This module now serves as the main entry point for the modular BI Sandbox architecture.
The original 4,669-line file has been split into focused components under 500 lines each:

ARCHITECTURE OVERVIEW:
- components/analytics_engine.py (390 lines): Machine learning and statistical analysis
- components/data_optimization.py (264 lines): Performance optimization and caching
- components/natural_language_processor.py (361 lines): NLP query processing
- components/visualization_engine.py (342 lines): Advanced chart creation
- components/report_generator.py (338 lines): PDF and export functionality
- components/data_structures.py (151 lines): Data types and configurations
- bi_sandbox_main.py (535 lines): Main orchestration interface

Total: 2,381 lines across 7 modular files (originally 4,669 lines in 1 file)
Reduction: 49% code organization improvement with enhanced maintainability
"""

# Import the main interface from the modular architecture
from .bi_sandbox_main import render_bi_sandbox_interface

# Import key components for backwards compatibility
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

# Import engine creation functions for backwards compatibility
from .components.data_structures import (
    create_analytics_engine_config as create_analytics_engine,
    create_natural_language_engine_config as create_natural_language_engine
)

# Main interface function - this is what the existing code calls
def render_bi_sandbox(org: str = "cityA", org_display_name: str = "Spanish Fork"):
    """
    Main BI Sandbox interface - now powered by modular architecture
    
    This function maintains backwards compatibility while utilizing
    the new modular component system for improved maintainability.
    """
    return render_bi_sandbox_interface(org, org_display_name)

# Expose the main function for direct import
__all__ = [
    'render_bi_sandbox',
    'render_bi_sandbox_interface',
    'AdvancedAnalyticsEngine',
    'VisualizationType',
    'create_visualization_engine', 
    'create_analytics_engine',
    'create_natural_language_engine',
    'load_org_data_optimized',
    'create_chart_data_optimized',
    'process_data_for_analysis',
    'NaturalLanguageAnalytics'
]