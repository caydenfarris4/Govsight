"""
Performance-Enhanced Position Based Budgeting
Integrates Phase 1 performance optimizations with PBB functionality
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
import time

# Import performance modules
try:
    from ..core.performance_manager import get_performance_manager, optimized_query
    from ..core.intelligent_cache import cached_dataframe, cache_result
    from ..database.performance_integration import get_performance_db
except ImportError as e:
    print(f"Performance modules not available: {e}")
    # Fallback functions
    def optimized_query(query, params=(), database_type='primary'):
        from ..database.connection_manager import get_database_connection
        import pandas as pd
        conn = get_database_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
    
    def cached_dataframe(ttl=300, cache_name='default'):
        def decorator(func):
            return func
        return decorator

class PerformanceEnhancedPBB:
    """High-performance Position Based Budgeting with Phase 1 optimizations"""
    
    def __init__(self):
        self.performance_manager = get_performance_manager()
        self.payroll_db = get_performance_db('databases/payroll_city_payroll_demo.db')
    
    @cached_dataframe(ttl=600, cache_name='departments')  # 10 minute cache for departments
    def get_departments_optimized(self) -> List[str]:
        """Get all departments with performance caching"""
        query = """
        SELECT DISTINCT Department 
        FROM Employees 
        WHERE Department IS NOT NULL AND Department != ''
        ORDER BY Department
        """
        
        try:
            df = optimized_query(query, database_type='payroll')
            return df['Department'].tolist()
        except Exception as e:
            st.error(f"Error loading departments: {e}")
            return ['Finance', 'Police', 'Fire', 'Public Works', 'Administration']  # Fallback
    
    @cached_dataframe(ttl=300, cache_name='employee_positions')  # 5 minute cache
    def get_employees_for_departments_optimized(self, departments: List[str]) -> pd.DataFrame:
        """Get employees for selected departments with high-performance query"""
        if not departments:
            return pd.DataFrame()
        
        # Use optimized IN query with parameters
        placeholders = ','.join(['?' for _ in departments])
        query = f"""
        SELECT 
            e.EmployeeID,
            e.FirstName,
            e.LastName, 
            e.Department,
            e.Position,
            COALESCE(pc.HoursPerPay, 80.0) as HoursPerPay,
            COALESCE(pc.OTHours, 0.0) as OTHours,
            COALESCE(pc.OTRate, 1.5) as OTRate,
            COALESCE(bp.BenefitsPercentage, 0.25) as BenefitsPercentage,
            COALESCE(ph.GrossPay / NULLIF(pc.HoursPerPay, 0), 15.0) as HourlyRate
        FROM Employees e
        LEFT JOIN PayCodes pc ON e.Position = pc.Position 
        LEFT JOIN BenefitPlans bp ON e.BenefitPlan = bp.PlanName
        LEFT JOIN (
            SELECT EmployeeID, GrossPay, 
                   ROW_NUMBER() OVER (PARTITION BY EmployeeID ORDER BY PayPeriodEnd DESC) as rn
            FROM PaycheckHeaders 
        ) ph ON e.EmployeeID = ph.EmployeeID AND ph.rn = 1
        WHERE e.Department IN ({placeholders})
        ORDER BY e.Department, e.LastName, e.FirstName
        """
        
        try:
            start_time = time.time()
            df = optimized_query(query, tuple(departments), database_type='payroll')
            execution_time = time.time() - start_time
            
            # Show performance improvement
            if execution_time < 1.0:
                st.success(f"Performance Enhancement: Department mapping completed in {execution_time:.2f} seconds")
            
            return df
            
        except Exception as e:
            st.error(f"Performance-optimized query failed: {e}")
            # Fallback to basic query
            return self._fallback_employee_query(departments)
    
    def _fallback_employee_query(self, departments: List[str]) -> pd.DataFrame:
        """Fallback employee query without performance optimizations"""
        try:
            placeholders = ','.join(['?' for _ in departments])
            query = f"""
            SELECT 
                EmployeeID, FirstName, LastName, Department, Position,
                80.0 as HoursPerPay, 0.0 as OTHours, 1.5 as OTRate,
                0.25 as BenefitsPercentage, 15.0 as HourlyRate
            FROM Employees 
            WHERE Department IN ({placeholders})
            ORDER BY Department, LastName, FirstName
            """
            
            return optimized_query(query, tuple(departments), database_type='payroll')
            
        except Exception as e:
            st.error(f"Fallback query also failed: {e}")
            return pd.DataFrame()
    
    @cache_result(ttl=1800, cache_name='budget_calculations')  # 30 minute cache for calculations
    def calculate_employee_costs_optimized(self, employee_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate employee costs with performance optimization"""
        if employee_data.empty:
            return pd.DataFrame()
        
        # Vectorized calculations for better performance
        df = employee_data.copy()
        
        # Calculate regular wages
        df['RegularWages'] = df['HoursPerPay'] * df['HourlyRate']
        
        # Calculate overtime wages  
        df['OvertimeWages'] = df['OTHours'] * df['HourlyRate'] * df['OTRate']
        
        # Total wages
        df['TotalWages'] = df['RegularWages'] + df['OvertimeWages']
        
        # Benefits calculation
        df['Benefits'] = df['TotalWages'] * df['BenefitsPercentage']
        
        # Taxes (simplified calculation)
        df['Taxes'] = df['TotalWages'] * 0.077  # 7.7% for FICA
        
        # Total cost
        df['TotalCost'] = df['TotalWages'] + df['Benefits'] + df['Taxes']
        
        # Annual costs (assuming bi-weekly pay periods)
        df['AnnualCost'] = df['TotalCost'] * 26
        
        return df
    
    def get_department_summary_optimized(self, employee_costs: pd.DataFrame) -> pd.DataFrame:
        """Get department cost summary with performance optimization"""
        if employee_costs.empty:
            return pd.DataFrame()
        
        # High-performance aggregation using pandas groupby
        summary = employee_costs.groupby('Department').agg({
            'EmployeeID': 'count',
            'TotalWages': 'sum',
            'Benefits': 'sum', 
            'Taxes': 'sum',
            'TotalCost': 'sum',
            'AnnualCost': 'sum'
        }).reset_index()
        
        summary.rename(columns={'EmployeeID': 'EmployeeCount'}, inplace=True)
        
        # Add percentage of total budget
        total_annual = summary['AnnualCost'].sum()
        summary['PercentOfTotal'] = (summary['AnnualCost'] / total_annual * 100) if total_annual > 0 else 0
        
        return summary
    
    @cached_dataframe(ttl=120, cache_name='performance_metrics')  # 2 minute cache for metrics
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get PBB performance metrics"""
        try:
            perf_data = self.performance_manager.get_performance_dashboard_data()
            
            metrics = {
                'total_database_queries': perf_data['metrics']['total_queries'],
                'cache_hit_rate': 0,
                'average_query_time': 0,
                'active_optimizations': sum(1 for enabled in perf_data['enabled_optimizations'].values() if enabled),
                'uptime_hours': perf_data['uptime_hours']
            }
            
            # Calculate cache performance
            if 'cache_performance' in perf_data and 'summary' in perf_data['cache_performance']:
                cache_summary = perf_data['cache_performance']['summary']
                metrics['cache_hit_rate'] = cache_summary.get('overall_hit_rate', 0)
            
            # Calculate database performance
            if 'database_performance' in perf_data:
                total_query_time = 0
                query_count = 0
                
                for db_name, db_perf in perf_data['database_performance'].items():
                    engine_stats = db_perf.get('engine_performance', {})
                    avg_time = engine_stats.get('average_query_time', 0)
                    queries = engine_stats.get('queries_executed', 0)
                    
                    total_query_time += avg_time * queries
                    query_count += queries
                
                if query_count > 0:
                    metrics['average_query_time'] = total_query_time / query_count
            
            return metrics
            
        except Exception as e:
            print(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def clear_pbb_caches(self):
        """Clear PBB-specific caches for fresh data"""
        try:
            from ..core.intelligent_cache import invalidate_cache_by_operation
            invalidate_cache_by_operation('employee_data')
            st.success("PBB caches cleared successfully")
        except Exception as e:
            st.error(f"Error clearing caches: {e}")
    
    def render_performance_dashboard(self):
        """Render performance metrics dashboard for PBB"""
        st.subheader("Performance Analytics")
        
        metrics = self.get_performance_metrics()
        
        if 'error' in metrics:
            st.error(f"Error loading performance metrics: {metrics['error']}")
            return
        
        # Performance metrics display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Cache Hit Rate", f"{metrics['cache_hit_rate']:.1%}")
        
        with col2:
            st.metric("Avg Query Time", f"{metrics['average_query_time']:.3f}s")
        
        with col3:
            st.metric("Active Optimizations", metrics['active_optimizations'])
        
        with col4:
            st.metric("System Uptime", f"{metrics['uptime_hours']:.1f}h")
        
        # Performance controls
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Clear PBB Caches", help="Clear cached data to refresh with latest information"):
                self.clear_pbb_caches()
        
        with col2:
            if st.button("View Detailed Performance Report"):
                detailed_metrics = self.performance_manager.get_performance_dashboard_data()
                st.json(detailed_metrics)

# Global instance for easy access
_enhanced_pbb = None

def get_enhanced_pbb() -> PerformanceEnhancedPBB:
    """Get global performance-enhanced PBB instance"""
    global _enhanced_pbb
    if _enhanced_pbb is None:
        _enhanced_pbb = PerformanceEnhancedPBB()
    return _enhanced_pbb