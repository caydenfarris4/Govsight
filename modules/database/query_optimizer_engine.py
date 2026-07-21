"""
Advanced Query Optimization Engine for GovSight
Automatically analyzes and optimizes database queries for improved performance
"""

import re
import time
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, Counter
import pandas as pd

@dataclass
class QueryAnalysis:
    """Query analysis results"""
    query: str
    execution_time: float
    rows_examined: int
    rows_returned: int
    suggestions: List[Dict[str, str]]
    optimization_level: str  # 'optimal', 'good', 'poor', 'critical'

@dataclass  
class IndexSuggestion:
    """Database index suggestion"""
    table_name: str
    columns: List[str]
    index_type: str  # 'standard', 'unique', 'composite'
    expected_improvement: str
    priority: str  # 'high', 'medium', 'low'

class QueryParser:
    """Parse and analyze SQL queries"""
    
    def __init__(self):
        self.table_pattern = re.compile(r'FROM\s+(\w+)', re.IGNORECASE)
        self.where_pattern = re.compile(r'WHERE\s+(.+?)(?:GROUP|ORDER|LIMIT|$)', re.IGNORECASE | re.DOTALL)
        self.join_pattern = re.compile(r'JOIN\s+(\w+)', re.IGNORECASE)
        self.order_pattern = re.compile(r'ORDER\s+BY\s+(.+?)(?:LIMIT|$)', re.IGNORECASE)
    
    def extract_tables(self, query: str) -> List[str]:
        """Extract table names from query"""
        tables = []
        
        # Main table from FROM clause
        from_match = self.table_pattern.search(query)
        if from_match:
            tables.append(from_match.group(1))
        
        # Tables from JOIN clauses
        join_matches = self.join_pattern.findall(query)
        tables.extend(join_matches)
        
        return list(set(tables))  # Remove duplicates
    
    def extract_where_columns(self, query: str) -> List[str]:
        """Extract columns used in WHERE conditions"""
        where_match = self.where_pattern.search(query)
        if not where_match:
            return []
        
        where_clause = where_match.group(1)
        
        # Simple column extraction (can be enhanced)
        column_patterns = [
            r'(\w+)\s*[=<>!]',  # column = value
            r'(\w+)\s+IN\s*\(',  # column IN (...)
            r'(\w+)\s+LIKE',     # column LIKE
            r'(\w+)\s+BETWEEN',  # column BETWEEN
        ]
        
        columns = []
        for pattern in column_patterns:
            matches = re.findall(pattern, where_clause, re.IGNORECASE)
            columns.extend(matches)
        
        # Remove SQL keywords
        sql_keywords = {'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE'}
        return [col for col in columns if col.upper() not in sql_keywords]
    
    def extract_order_columns(self, query: str) -> List[str]:
        """Extract columns used in ORDER BY"""
        order_match = self.order_pattern.search(query)
        if not order_match:
            return []
        
        order_clause = order_match.group(1)
        # Extract column names (remove ASC/DESC)
        columns = re.findall(r'(\w+)', order_clause)
        return [col for col in columns if col.upper() not in ['ASC', 'DESC']]

class QueryOptimizer:
    """Advanced query optimization engine"""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.parser = QueryParser()
        self.query_history = defaultdict(list)
        self.table_stats = {}
        self.index_suggestions = []
        self.lock = threading.Lock()
        
        # Load database schema information
        self._analyze_schema()
    
    def _analyze_schema(self):
        """Analyze database schema and collect statistics"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                # Get table info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # Get existing indexes
                cursor.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()
                
                self.table_stats[table_name] = {
                    'columns': [col[1] for col in columns],
                    'row_count': row_count,
                    'indexes': [idx[1] for idx in indexes],
                    'primary_key_columns': [col[1] for col in columns if col[5] == 1]
                }
            
            conn.close()
            
        except Exception as e:
            print(f"Error analyzing schema: {e}")
    
    def analyze_query(self, query: str, execution_time: float, result_count: int = 0) -> QueryAnalysis:
        """Analyze query performance and suggest optimizations"""
        with self.lock:
            # Store query history
            self.query_history[query].append({
                'execution_time': execution_time,
                'timestamp': time.time(),
                'result_count': result_count
            })
            
            suggestions = []
            optimization_level = 'optimal'
            
            # Performance-based analysis
            if execution_time > 2.0:
                optimization_level = 'critical'
                suggestions.append({
                    'type': 'performance',
                    'message': 'Query execution time exceeds 2 seconds',
                    'solution': 'Consider adding database indexes or optimizing query structure',
                    'priority': 'high'
                })
            elif execution_time > 1.0:
                optimization_level = 'poor'
                suggestions.append({
                    'type': 'performance',
                    'message': 'Query execution time exceeds 1 second',
                    'solution': 'Review query efficiency and consider indexing',
                    'priority': 'medium'
                })
            elif execution_time > 0.5:
                optimization_level = 'good'
            
            # Query structure analysis
            query_upper = query.upper()
            
            # SELECT * analysis
            if 'SELECT *' in query_upper:
                suggestions.append({
                    'type': 'efficiency',
                    'message': 'Using SELECT * may retrieve unnecessary columns',
                    'solution': 'Select only required columns to reduce data transfer',
                    'priority': 'medium'
                })
            
            # Missing LIMIT analysis
            if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
                suggestions.append({
                    'type': 'efficiency', 
                    'message': 'ORDER BY without LIMIT may sort entire table',
                    'solution': 'Add LIMIT clause if you do not need all results',
                    'priority': 'medium'
                })
            
            # Subquery analysis
            if query_upper.count('SELECT') > 1:
                suggestions.append({
                    'type': 'structure',
                    'message': 'Query contains subqueries',
                    'solution': 'Consider using JOINs instead of subqueries for better performance',
                    'priority': 'low'
                })
            
            # Index suggestions
            index_suggestions = self._suggest_indexes(query)
            suggestions.extend(index_suggestions)
            
            return QueryAnalysis(
                query=query,
                execution_time=execution_time,
                rows_examined=0,  # SQLite doesn't easily provide this
                rows_returned=result_count,
                suggestions=suggestions,
                optimization_level=optimization_level
            )
    
    def _suggest_indexes(self, query: str) -> List[Dict[str, str]]:
        """Suggest database indexes based on query patterns"""
        suggestions = []
        
        try:
            tables = self.parser.extract_tables(query)
            where_columns = self.parser.extract_where_columns(query)
            order_columns = self.parser.extract_order_columns(query)
            
            for table in tables:
                if table not in self.table_stats:
                    continue
                
                table_info = self.table_stats[table]
                existing_indexes = table_info['indexes']
                
                # Suggest indexes for WHERE columns
                for column in where_columns:
                    if column in table_info['columns']:
                        index_name = f"idx_{table}_{column}"
                        if index_name not in existing_indexes:
                            suggestions.append({
                                'type': 'index',
                                'message': f'Consider creating index on {table}.{column}',
                                'solution': f'CREATE INDEX {index_name} ON {table}({column})',
                                'priority': 'high' if table_info['row_count'] > 1000 else 'medium'
                            })
                
                # Suggest indexes for ORDER BY columns
                for column in order_columns:
                    if column in table_info['columns']:
                        index_name = f"idx_{table}_{column}_sort"
                        if index_name not in existing_indexes:
                            suggestions.append({
                                'type': 'index',
                                'message': f'Consider creating index on {table}.{column} for sorting',
                                'solution': f'CREATE INDEX {index_name} ON {table}({column})',
                                'priority': 'medium'
                            })
                
                # Suggest composite indexes for multiple WHERE columns
                if len(where_columns) > 1:
                    # Check if columns belong to the same table
                    table_where_cols = [col for col in where_columns if col in table_info['columns']]
                    if len(table_where_cols) > 1:
                        index_cols = ','.join(table_where_cols[:3])  # Limit to 3 columns
                        index_name = f"idx_{table}_composite"
                        
                        suggestions.append({
                            'type': 'index',
                            'message': f'Consider composite index on {table}({index_cols})',
                            'solution': f'CREATE INDEX {index_name} ON {table}({index_cols})',
                            'priority': 'medium'
                        })
        
        except Exception as e:
            print(f"Error generating index suggestions: {e}")
        
        return suggestions
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query performance statistics"""
        with self.lock:
            stats = {
                'total_queries': sum(len(history) for history in self.query_history.values()),
                'unique_queries': len(self.query_history),
                'slow_queries': 0,
                'average_execution_time': 0,
                'most_frequent_queries': [],
                'slowest_queries': []
            }
            
            all_executions = []
            query_frequencies = Counter()
            
            for query, history in self.query_history.items():
                query_frequencies[query] = len(history)
                
                for execution in history:
                    all_executions.append((query, execution['execution_time']))
                    if execution['execution_time'] > 1.0:
                        stats['slow_queries'] += 1
            
            if all_executions:
                stats['average_execution_time'] = sum(exec_time for _, exec_time in all_executions) / len(all_executions)
                
                # Most frequent queries
                stats['most_frequent_queries'] = [
                    {'query': query[:100] + '...', 'frequency': freq}
                    for query, freq in query_frequencies.most_common(5)
                ]
                
                # Slowest queries
                slowest = sorted(all_executions, key=lambda x: x[1], reverse=True)[:5]
                stats['slowest_queries'] = [
                    {'query': query[:100] + '...', 'execution_time': exec_time}
                    for query, exec_time in slowest
                ]
            
            return stats
    
    def generate_index_recommendations(self) -> List[IndexSuggestion]:
        """Generate comprehensive index recommendations"""
        recommendations = []
        
        with self.lock:
            # Analyze query patterns to suggest indexes
            column_usage = defaultdict(int)
            table_usage = defaultdict(int)
            
            for query, history in self.query_history.items():
                frequency = len(history)
                avg_time = sum(h['execution_time'] for h in history) / len(history)
                
                tables = self.parser.extract_tables(query)
                where_columns = self.parser.extract_where_columns(query)
                
                for table in tables:
                    table_usage[table] += frequency
                
                for column in where_columns:
                    column_usage[f"{tables[0] if tables else 'unknown'}.{column}"] += frequency * avg_time
            
            # Generate recommendations based on usage patterns
            for table_column, score in sorted(column_usage.items(), key=lambda x: x[1], reverse=True)[:10]:
                if '.' in table_column:
                    table, column = table_column.split('.', 1)
                    
                    if table in self.table_stats:
                        table_info = self.table_stats[table]
                        row_count = table_info['row_count']
                        
                        if row_count > 100:  # Only suggest for tables with significant data
                            priority = 'high' if score > 10 and row_count > 1000 else 'medium'
                            
                            recommendations.append(IndexSuggestion(
                                table_name=table,
                                columns=[column],
                                index_type='standard',
                                expected_improvement=f"Up to {min(90, int(score * 10))}% faster queries",
                                priority=priority
                            ))
            
            return recommendations[:5]  # Return top 5 recommendations

def optimize_query_text(query: str) -> str:
    """Apply basic text-level query optimizations"""
    # Remove unnecessary whitespace
    query = ' '.join(query.split())
    
    # Basic optimizations
    optimizations = [
        # Replace SELECT * with specific columns (placeholder - needs schema info)
        # (r'SELECT \*', 'SELECT column1, column2'),  # Would need actual columns
        
        # Ensure proper index usage hints
        (r'\bWHERE\s+(\w+)\s*=\s*', r'WHERE \1 = '),  # Normalize spacing
    ]
    
    for pattern, replacement in optimizations:
        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
    
    return query

# Global optimizer instances
_optimizers = {}

def get_optimizer(database_path: str) -> QueryOptimizer:
    """Get or create query optimizer for database"""
    if database_path not in _optimizers:
        _optimizers[database_path] = QueryOptimizer(database_path)
    return _optimizers[database_path]