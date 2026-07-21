"""
Core Module

Enterprise infrastructure components for GovSight Financial Analyzer
"""

# Core infrastructure imports
try:
    from .config_manager import get_config, get_config_manager
    from .error_handler import get_error_handler, handle_errors
    from .enhanced_logger import get_logger
    from .performance_optimizer import get_performance_monitor
except ImportError:
    # Graceful fallback if modules aren't available
    pass

__all__ = [
    'get_config',
    'get_config_manager', 
    'get_error_handler',
    'handle_errors',
    'get_logger',
    'get_performance_monitor'
]