"""
Performance Integration Module
Integrates high-performance engine with existing GovSight database operations
"""

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps

from .high_performance_engine import get_engine, performance_query
from .query_optimizer_engine import get_optimizer
from ..core.intelligent_cache import cache_result, cached_dataframe, get_cache
from .connection_manager import get_database_connection

class PerformanceIntegratedDB:
    """High-performance wrapper for existing database operations"""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.engine = get_engine(database_path)
        self.optimizer = get_optimizer(database_path)
        self.cache = get_cache(f'db_{hash(database_path)}', ttl=600, max_memory_mb=100)
    
    @cached_dataframe(ttl=300, cache_name='financial_queries')
    def execute_financial_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute financial data queries with caching and optimization"""
        import time
        start_time = time.time()
        
        result = self.engine.execute_query(query, params)
        execution_time = time.time() - start_time
        
        # Analyze query performance
        analysis = self.optimizer.analyze_query(query, execution_time, len(result))
        
        # Log slow queries with suggestions
        if analysis.optimization_level in ['poor', 'critical']:
            print(f"Query performance: {analysis.optimization_level}")
            for suggestion in analysis.suggestions[:3]:  # Show top 3 suggestions
                print(f"  - {suggestion['message']}: {suggestion['solution']}")
        
        return result
    
    @cache_result(ttl=900, cache_name='metadata')  # 15 minute cache for metadata
    def get_gl_accounts(self, account_type: str = None) -> pd.DataFrame:
        """Get GL accounts with performance optimization"""
        query = "SELECT * FROM GLAccounts"
        params = ()
        
        if account_type:
            query += " WHERE AccountType = ?"
            params = (account_type,)
        
        return self.execute_financial_query(query, params)
    
    @cached_dataframe(ttl=180, cache_name='transactions')  # 3 minute cache for transactions
    def get_transactions(self, start_date: str = None, end_date: str = None, 
                        account_codes: List[str] = None, limit: int = None) -> pd.DataFrame:
        """Get transactions with intelligent caching and optimization"""
        query = """
        SELECT t.*, g.AccountName, g.AccountType 
        FROM Transactions t
        LEFT JOIN GLAccounts g ON t.AccountCode = g.AccountCode
        WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND t.TransactionDate >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND t.TransactionDate <= ?"
            params.append(end_date)
        
        if account_codes:
            placeholders = ','.join(['?' for _ in account_codes])
            query += f" AND t.AccountCode IN ({placeholders})"
            params.extend(account_codes)
        
        query += " ORDER BY t.TransactionDate DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return self.execute_financial_query(query, tuple(params))
    
    @cache_result(ttl=1800, cache_name='aggregates')  # 30 minute cache for aggregates
    def get_account_balances(self, as_of_date: str = None) -> pd.DataFrame:
        """Get account balances with advanced caching"""
        query = """
        SELECT 
            g.AccountCode,
            g.AccountName,
            g.AccountType,
            COALESCE(SUM(t.Amount), 0) as Balance
        FROM GLAccounts g
        LEFT JOIN Transactions t ON g.AccountCode = t.AccountCode
        """
        params = []
        
        if as_of_date:
            query += " AND t.TransactionDate <= ?"
            params.append(as_of_date)
        
        query += " GROUP BY g.AccountCode, g.AccountName, g.AccountType ORDER BY g.AccountCode"
        
        return self.execute_financial_query(query, tuple(params))
    
    @cached_dataframe(ttl=120, cache_name='payroll')  # 2 minute cache for payroll
    def get_employee_data(self, department: str = None, position: str = None) -> pd.DataFrame:
        """Get employee data with performance optimization"""
        query = """
        SELECT e.*, ph.GrossPay, ph.PayPeriodEnd
        FROM Employees e
        LEFT JOIN PaycheckHeaders ph ON e.EmployeeID = ph.EmployeeID
        WHERE 1=1
        """
        params = []
        
        if department:
            query += " AND e.Department = ?"
            params.append(department)
        
        if position:
            query += " AND e.Position = ?"
            params.append(position)
        
        query += " ORDER BY e.LastName, e.FirstName"
        
        return self.execute_financial_query(query, tuple(params))
    
    def bulk_insert_transactions(self, transactions: List[Dict[str, Any]]) -> int:
        """High-performance bulk insert for transactions"""
        from .high_performance_engine import batch_insert
        
        # Clear transaction-related caches
        get_cache('transactions').invalidate()
        get_cache('aggregates').invalidate()
        
        return batch_insert(self.database_path, 'Transactions', transactions)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        engine_stats = self.engine.get_performance_stats()
        optimizer_stats = self.optimizer.get_query_statistics()
        cache_stats = self.cache.get_stats()
        
        return {
            'database_path': self.database_path,
            'engine_performance': engine_stats,
            'query_optimization': optimizer_stats,
            'cache_performance': cache_stats,
            'recommendations': self.optimizer.generate_index_recommendations()
        }

# Performance-enhanced database functions for backward compatibility
@performance_query()
def enhanced_read_sql(query: str, params: tuple = (), engine=None, **kwargs) -> pd.DataFrame:
    """Enhanced version of pd.read_sql with performance optimizations"""
    if engine is not None:
        return engine.execute_query(query, params)
    else:
        # Fallback to standard connection
        conn = get_database_connection()
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

def get_performance_db(database_path: str = None) -> PerformanceIntegratedDB:
    """Get performance-integrated database instance"""
    if database_path is None:
        database_path = "databases/core/caselle_gl0_mock.db"
    
    # Cache instances to reuse connections
    if not hasattr(get_performance_db, '_instances'):
        get_performance_db._instances = {}
    
    if database_path not in get_performance_db._instances:
        get_performance_db._instances[database_path] = PerformanceIntegratedDB(database_path)
    
    return get_performance_db._instances[database_path]

# Decorator for easy migration of existing functions
def use_performance_db(database_path: str = None):
    """Decorator to migrate existing database functions to high-performance versions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Inject performance database
            perf_db = get_performance_db(database_path)
            kwargs['perf_db'] = perf_db
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Example usage for migrating existing code:
"""
# Old code:
def get_transactions_old():
    conn = get_database_connection()
    query = "SELECT * FROM Transactions"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# New performance-enhanced code:
@use_performance_db()
def get_transactions_new(perf_db=None):
    return perf_db.get_transactions()
"""