"""
Central Performance Management System for GovSight
Coordinates all performance optimizations across the platform
"""

import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import streamlit as st

# Import our performance modules
try:
    from ..database.high_performance_engine import get_engine, HighPerformanceEngine
    from ..database.query_optimizer_engine import get_optimizer, QueryOptimizer  
    from ..database.performance_integration import get_performance_db, PerformanceIntegratedDB
    from .intelligent_cache import get_cache, get_cache_performance_report, invalidate_cache_by_operation
    PERFORMANCE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some performance modules not available: {e}")
    PERFORMANCE_MODULES_AVAILABLE = False
    # Provide stub classes/functions
    class PerformanceIntegratedDB:
        def __init__(self, path): pass
        def execute_financial_query(self, query, params): 
            import pandas as pd
            return pd.DataFrame()
        def get_performance_report(self): return {}
    
    def get_performance_db(path): return PerformanceIntegratedDB(path)
    def get_cache_performance_report(): return {}
    def invalidate_cache_by_operation(op_type): pass

class PerformanceManager:
    """Central manager for all performance optimizations"""
    
    def __init__(self):
        self.start_time = time.time()
        self.enabled_optimizations = {
            'database_pooling': True,
            'intelligent_caching': True,
            'query_optimization': True,
            'memory_optimization': True,
            'performance_monitoring': True
        }
        
        # Performance metrics
        self.metrics = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'slow_queries': 0,
            'optimization_suggestions': 0
        }
        
        # Database instances for different purposes
        self.db_instances = {}
        
        self.lock = threading.Lock()
    
    def get_optimized_database(self, database_type: str = 'primary') -> Optional['PerformanceIntegratedDB']:
        """Get performance-optimized database instance"""
        if not self.enabled_optimizations['database_pooling'] or not PERFORMANCE_MODULES_AVAILABLE:
            return None
        
        try:
            database_paths = {
                'primary': 'databases/core/caselle_gl0_mock.db',
                'payroll': 'databases/payroll_city_payroll_demo.db',
                'dashboard': 'org_dashboard_data.db'
            }
            
            db_path = database_paths.get(database_type, database_paths['primary'])
            
            if database_type not in self.db_instances:
                self.db_instances[database_type] = get_performance_db(db_path)
            
            return self.db_instances[database_type]
            
        except Exception as e:
            print(f"Error getting optimized database: {e}")
            return None
    
    def execute_optimized_query(self, query: str, params: tuple = (), database_type: str = 'primary'):
        """Execute query with all performance optimizations"""
        with self.lock:
            self.metrics['total_queries'] += 1
        
        db = self.get_optimized_database(database_type)
        if db is None:
            # Fallback to standard database connection
            from ..database.connection_manager import get_database_connection
            import pandas as pd
            
            conn = get_database_connection()
            try:
                return pd.read_sql_query(query, conn, params=list(params))
            finally:
                conn.close()
        
        return db.execute_financial_query(query, params)
    
    def clear_caches(self, cache_type: str = 'all'):
        """Clear performance caches"""
        if not self.enabled_optimizations['intelligent_caching']:
            return
        
        try:
            if cache_type == 'all':
                invalidate_cache_by_operation('all')
            else:
                invalidate_cache_by_operation(cache_type)
            
            st.success("Performance caches cleared successfully")
            
        except Exception as e:
            st.error(f"Error clearing caches: {e}")
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive performance data for dashboard"""
        dashboard_data = {
            'uptime_hours': (time.time() - self.start_time) / 3600,
            'enabled_optimizations': self.enabled_optimizations,
            'metrics': self.metrics.copy(),
            'cache_performance': {},
            'database_performance': {},
            'optimization_suggestions': []
        }
        
        try:
            # Get cache performance
            if self.enabled_optimizations['intelligent_caching'] and PERFORMANCE_MODULES_AVAILABLE:
                dashboard_data['cache_performance'] = get_cache_performance_report()
            
            # Get database performance for each instance
            for db_type, db_instance in self.db_instances.items():
                if db_instance:
                    dashboard_data['database_performance'][db_type] = db_instance.get_performance_report()
            
            # Generate optimization suggestions
            dashboard_data['optimization_suggestions'] = self._generate_optimization_suggestions()
            
        except Exception as e:
            print(f"Error getting performance dashboard data: {e}")
        
        return dashboard_data
    
    def _generate_optimization_suggestions(self) -> List[Dict[str, str]]:
        """Generate performance optimization suggestions"""
        suggestions = []
        
        try:
            # Analyze cache performance
            if PERFORMANCE_MODULES_AVAILABLE:
                cache_report = get_cache_performance_report()
            else:
                cache_report = None
            if cache_report and 'summary' in cache_report:
                hit_rate = cache_report['summary'].get('overall_hit_rate', 0)
                
                if hit_rate < 0.7:  # Less than 70% hit rate
                    suggestions.append({
                        'type': 'caching',
                        'priority': 'medium',
                        'message': 'Cache hit rate is below optimal (70%)',
                        'solution': 'Consider increasing cache TTL or reviewing cache invalidation strategy'
                    })
                
                memory_usage = cache_report['summary'].get('total_memory_mb', 0)
                if memory_usage > 200:  # More than 200MB
                    suggestions.append({
                        'type': 'memory',
                        'priority': 'high', 
                        'message': 'Cache memory usage is high',
                        'solution': 'Consider reducing cache size or TTL values'
                    })
            
            # Analyze query performance from database instances
            for db_type, db_instance in self.db_instances.items():
                if db_instance:
                    perf_report = db_instance.get_performance_report()
                    engine_stats = perf_report.get('engine_performance', {})
                    
                    avg_query_time = engine_stats.get('average_query_time', 0)
                    if avg_query_time > 1.0:
                        suggestions.append({
                            'type': 'query_performance',
                            'priority': 'high',
                            'message': f'{db_type} database queries averaging >1 second',
                            'solution': 'Review slow queries and consider adding database indexes'
                        })
                    
                    cache_hit_rate = engine_stats.get('cache_hit_rate', 0)
                    if cache_hit_rate < 0.5:
                        suggestions.append({
                            'type': 'database_caching',
                            'priority': 'medium',
                            'message': f'{db_type} database cache hit rate is low',
                            'solution': 'Increase query cache TTL or review query patterns'
                        })
        
        except Exception as e:
            print(f"Error generating optimization suggestions: {e}")
        
        return suggestions
    
    def toggle_optimization(self, optimization_name: str, enabled: bool):
        """Enable or disable specific optimization"""
        if optimization_name in self.enabled_optimizations:
            self.enabled_optimizations[optimization_name] = enabled
            
            if optimization_name == 'intelligent_caching' and not enabled:
                # Clear caches if caching is disabled
                self.clear_caches()
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick performance statistics for display"""
        return {
            'total_queries': self.metrics['total_queries'],
            'optimizations_active': sum(1 for enabled in self.enabled_optimizations.values() if enabled),
            'uptime_hours': round((time.time() - self.start_time) / 3600, 1)
        }

# Global performance manager instance
_performance_manager = None

def get_performance_manager() -> PerformanceManager:
    """Get global performance manager instance"""
    global _performance_manager
    if _performance_manager is None:
        _performance_manager = PerformanceManager()
    return _performance_manager

# Streamlit session state integration
def init_performance_session():
    """Initialize performance manager in Streamlit session"""
    if 'performance_manager' not in st.session_state:
        st.session_state.performance_manager = get_performance_manager()

# Convenience functions for easy integration
def optimized_query(query: str, params: tuple = (), database_type: str = 'primary'):
    """Execute query with performance optimizations"""
    manager = get_performance_manager()
    return manager.execute_optimized_query(query, params, database_type)

def clear_performance_caches(cache_type: str = 'all'):
    """Clear performance caches"""
    manager = get_performance_manager()
    manager.clear_caches(cache_type)

def get_performance_stats():
    """Get performance statistics"""
    manager = get_performance_manager()
    return manager.get_performance_dashboard_data()