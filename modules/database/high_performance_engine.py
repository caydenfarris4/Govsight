"""
High-Performance Database Engine
Advanced connection pooling, caching, and query optimization for GovSight
"""

import sqlite3
import threading
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from functools import wraps, lru_cache
from collections import defaultdict
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

class ConnectionPool:
    """Thread-safe database connection pool for improved performance"""
    
    def __init__(self, database_path: str, max_connections: int = 20):
        self.database_path = database_path
        self.max_connections = max_connections
        self.connections = []
        self.in_use = set()
        self.lock = threading.Lock()
        self.created_count = 0
        
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection from the pool"""
        with self.lock:
            # Return existing connection if available
            if self.connections:
                conn = self.connections.pop()
                self.in_use.add(conn)
                return conn
            
            # Create new connection if under limit
            if self.created_count < self.max_connections:
                conn = sqlite3.connect(self.database_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                self.created_count += 1
                self.in_use.add(conn)
                return conn
            
            # If at limit, create temporary connection
            conn = sqlite3.connect(self.database_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool"""
        with self.lock:
            if conn in self.in_use:
                self.in_use.remove(conn)
                self.connections.append(conn)

class QueryCache:
    """Intelligent query result caching system"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = threading.Lock()
    
    def _get_cache_key(self, query: str, params: tuple = ()) -> str:
        """Generate cache key from query and parameters"""
        query_normalized = ' '.join(query.split()).upper()
        cache_input = f"{query_normalized}|{params}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get(self, query: str, params: tuple = ()) -> Optional[pd.DataFrame]:
        """Get cached query result if available and fresh"""
        cache_key = self._get_cache_key(query, params)
        
        with self.lock:
            if cache_key not in self.cache:
                return None
            
            cached_data, timestamp = self.cache[cache_key]
            
            # Check if cache entry is expired
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[cache_key]
                if cache_key in self.access_times:
                    del self.access_times[cache_key]
                return None
            
            # Update access time
            self.access_times[cache_key] = time.time()
            return cached_data.copy()
    
    def put(self, query: str, params: tuple, data: pd.DataFrame):
        """Cache query result"""
        cache_key = self._get_cache_key(query, params)
        
        with self.lock:
            # Clean cache if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
            
            self.cache[cache_key] = (data.copy(), time.time())
            self.access_times[cache_key] = time.time()
    
    def _evict_oldest(self):
        """Remove least recently used cache entry"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    def clear(self):
        """Clear all cached data"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()

class QueryOptimizer:
    """Analyze and optimize SQL queries automatically"""
    
    def __init__(self):
        self.query_stats = defaultdict(list)
        self.optimization_rules = {
            'missing_index': self._suggest_index,
            'inefficient_joins': self._optimize_joins,
            'unnecessary_columns': self._remove_unused_columns
        }
    
    def analyze_query(self, query: str, execution_time: float) -> Dict[str, Any]:
        """Analyze query performance and suggest optimizations"""
        query_normalized = ' '.join(query.split()).upper()
        self.query_stats[query_normalized].append(execution_time)
        
        suggestions = []
        
        # Check for common performance issues
        if 'SELECT *' in query_normalized:
            suggestions.append({
                'type': 'efficiency',
                'message': 'Consider selecting specific columns instead of SELECT *',
                'impact': 'medium'
            })
        
        if 'ORDER BY' in query_normalized and 'LIMIT' not in query_normalized:
            suggestions.append({
                'type': 'performance',
                'message': 'Consider adding LIMIT to ORDER BY queries',
                'impact': 'high'
            })
        
        if execution_time > 1.0:  # Slow query
            suggestions.append({
                'type': 'performance',
                'message': 'Query execution time exceeds 1 second - consider indexing',
                'impact': 'high'
            })
        
        return {
            'execution_time': execution_time,
            'suggestions': suggestions,
            'query_hash': hashlib.md5(query_normalized.encode()).hexdigest()
        }
    
    def _suggest_index(self, query: str) -> List[str]:
        """Suggest database indexes based on query patterns"""
        # Simple heuristic-based index suggestions
        suggestions = []
        
        if 'WHERE' in query.upper():
            # Extract potential index candidates from WHERE clauses
            # This is a simplified implementation
            suggestions.append("Consider creating indexes on frequently filtered columns")
        
        return suggestions
    
    def _optimize_joins(self, query: str) -> str:
        """Optimize JOIN operations"""
        # Simple optimization - could be expanded
        return query
    
    def _remove_unused_columns(self, query: str) -> str:
        """Remove unnecessary columns from SELECT"""
        # Simple optimization - could be expanded
        return query

class HighPerformanceEngine:
    """Main high-performance database engine"""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.pool = ConnectionPool(database_path)
        self.cache = QueryCache()
        self.optimizer = QueryOptimizer()
        self.performance_stats = {
            'queries_executed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_query_time': 0
        }
    
    def execute_query(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """Execute query with caching and optimization"""
        start_time = time.time()
        
        # Check cache first
        cached_result = self.cache.get(query, params)
        if cached_result is not None:
            self.performance_stats['cache_hits'] += 1
            return cached_result
        
        self.performance_stats['cache_misses'] += 1
        
        # Execute query
        conn = self.pool.get_connection()
        try:
            result = pd.read_sql_query(query, conn, params=params)
            
            # Cache result for SELECT queries
            if query.strip().upper().startswith('SELECT'):
                self.cache.put(query, params, result)
            
            execution_time = time.time() - start_time
            self.performance_stats['queries_executed'] += 1
            self.performance_stats['total_query_time'] += execution_time
            
            # Analyze query performance
            if execution_time > 0.5:  # Log slow queries
                analysis = self.optimizer.analyze_query(query, execution_time)
                if analysis['suggestions']:
                    print(f"Query optimization suggestions: {analysis['suggestions']}")
            
            return result
            
        finally:
            self.pool.return_connection(conn)
    
    def execute_non_query(self, query: str, params: tuple = ()) -> int:
        """Execute non-SELECT queries (INSERT, UPDATE, DELETE)"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            affected_rows = cursor.rowcount
            
            # Clear cache for data modification queries
            if any(keyword in query.upper() for keyword in ['INSERT', 'UPDATE', 'DELETE']):
                self.cache.clear()
            
            return affected_rows
            
        finally:
            self.pool.return_connection(conn)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = self.performance_stats.copy()
        if stats['queries_executed'] > 0:
            stats['average_query_time'] = stats['total_query_time'] / stats['queries_executed']
            stats['cache_hit_rate'] = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])
        else:
            stats['average_query_time'] = 0
            stats['cache_hit_rate'] = 0
        
        return stats

# Global engine instances for each database
_engines = {}

def get_engine(database_path: str) -> HighPerformanceEngine:
    """Get or create high-performance engine for database"""
    if database_path not in _engines:
        _engines[database_path] = HighPerformanceEngine(database_path)
    return _engines[database_path]

def performance_query(database_path: str = None):
    """Decorator for high-performance database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if database_path is None:
                # Use default database
                from modules.database.connection_manager import get_database_connection
                db_path = "databases/core/caselle_gl0_mock.db"  # Default path
            else:
                db_path = database_path
            
            engine = get_engine(db_path)
            
            # Replace database connection with high-performance engine
            kwargs['engine'] = engine
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

@lru_cache(maxsize=100)
def get_table_columns(database_path: str, table_name: str) -> List[str]:
    """Get table columns with caching"""
    engine = get_engine(database_path)
    query = f"PRAGMA table_info({table_name})"
    result = engine.execute_query(query)
    return result['name'].tolist() if not result.empty else []

def batch_insert(database_path: str, table_name: str, data: List[Dict[str, Any]]) -> int:
    """High-performance batch insert"""
    if not data:
        return 0
    
    engine = get_engine(database_path)
    
    # Generate bulk insert query
    columns = list(data[0].keys())
    placeholders = ', '.join(['?' for _ in columns])
    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    
    # Prepare batch data
    batch_params = []
    for row in data:
        batch_params.append(tuple(row[col] for col in columns))
    
    # Execute batch insert
    conn = engine.pool.get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(query, batch_params)
        conn.commit()
        return cursor.rowcount
    finally:
        engine.pool.return_connection(conn)