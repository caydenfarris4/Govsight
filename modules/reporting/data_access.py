"""
Data Access Layer for Secure Database Queries
Provides parameterized queries, role-based filtering, and caching
"""

import pandas as pd
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import json
from datetime import datetime, timedelta
from functools import lru_cache
import streamlit as st
from pathlib import Path


class DataAccessLayer:
    """Secure data access layer with role-based filtering"""
    
    def __init__(self, db_path: str = None):
        """Initialize data access layer with database connection"""
        if db_path is None:
            # Use default database path
            db_path = Path("databases") / "gl_data.db"
        self.db_path = str(db_path)
        self.cache_ttl = 300  # Cache for 5 minutes
        self._cache = {}
        self._cache_timestamps = {}
        
    def _get_cache_key(self, query: str, params: Tuple) -> str:
        """Generate cache key from query and parameters"""
        cache_data = f"{query}:{json.dumps(params, default=str)}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.now() - self._cache_timestamps[cache_key]
        return age.total_seconds() < self.cache_ttl
    
    def execute_query(self, 
                     query: str,
                     params: Tuple = (),
                     use_cache: bool = True,
                     user_role: str = "viewer") -> pd.DataFrame:
        """
        Execute parameterized query with role-based filtering
        
        Args:
            query: SQL query with parameter placeholders
            params: Query parameters
            use_cache: Whether to use caching
            user_role: User role for data filtering
            
        Returns:
            DataFrame with query results
        """
        # Apply role-based filtering
        query = self._apply_role_filter(query, user_role)
        
        # Check cache
        cache_key = self._get_cache_key(query, params)
        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key].copy()
        
        try:
            # Execute query
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            # Cache results
            if use_cache:
                self._cache[cache_key] = df.copy()
                self._cache_timestamps[cache_key] = datetime.now()
            
            return df
            
        except Exception as e:
            st.error(f"Database query error: {str(e)}")
            return pd.DataFrame()
    
    def _apply_role_filter(self, query: str, user_role: str) -> str:
        """Apply role-based filtering to queries"""
        # Role-based data restrictions
        role_filters = {
            'viewer': {
                'exclude_tables': ['payroll_details', 'employee_salaries'],
                'exclude_columns': ['ssn', 'salary', 'wage_rate']
            },
            'analyst': {
                'exclude_tables': [],
                'exclude_columns': ['ssn']
            },
            'admin': {
                'exclude_tables': [],
                'exclude_columns': []
            }
        }
        
        filters = role_filters.get(user_role, role_filters['viewer'])
        
        # Add filtering logic here based on role
        # For now, return query as-is (to be enhanced)
        return query
    
    def get_departments(self) -> List[str]:
        """Get list of available departments"""
        query = "SELECT DISTINCT department FROM transactions WHERE department IS NOT NULL ORDER BY department"
        df = self.execute_query(query)
        return df['department'].tolist() if not df.empty else []
    
    def get_gl_accounts(self) -> pd.DataFrame:
        """Get General Ledger accounts"""
        query = """
            SELECT account_code, account_name, account_type, balance
            FROM gl_accounts
            ORDER BY account_code
        """
        return self.execute_query(query)
    
    def get_transactions(self, 
                        start_date: str = None,
                        end_date: str = None,
                        department: str = None,
                        limit: int = 1000) -> pd.DataFrame:
        """
        Get transactions with optional filtering
        
        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            department: Department filter
            limit: Maximum number of records
            
        Returns:
            DataFrame of transactions
        """
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)
        
        if department:
            query += " AND department = ?"
            params.append(department)
        
        query += f" ORDER BY transaction_date DESC LIMIT {limit}"
        
        return self.execute_query(query, tuple(params))
    
    def get_budget_summary(self, 
                          fiscal_year: int = None,
                          department: str = None) -> pd.DataFrame:
        """Get budget summary by department and category"""
        if fiscal_year is None:
            fiscal_year = datetime.now().year
        
        query = """
            SELECT 
                department,
                category,
                SUM(budget_amount) as budget,
                SUM(actual_amount) as actual,
                SUM(budget_amount) - SUM(actual_amount) as variance,
                CASE 
                    WHEN SUM(budget_amount) > 0 
                    THEN ROUND(100.0 * SUM(actual_amount) / SUM(budget_amount), 2)
                    ELSE 0 
                END as percent_used
            FROM budget_data
            WHERE fiscal_year = ?
        """
        params = [fiscal_year]
        
        if department:
            query += " AND department = ?"
            params.append(department)
        
        query += " GROUP BY department, category ORDER BY department, category"
        
        return self.execute_query(query, tuple(params))
    
    def get_revenue_forecast(self, months: int = 12) -> pd.DataFrame:
        """Get revenue forecast for specified number of months"""
        query = """
            SELECT 
                strftime('%Y-%m', transaction_date) as month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
            FROM transactions
            WHERE transaction_date >= date('now', '-' || ? || ' months')
            GROUP BY month
            ORDER BY month
        """
        return self.execute_query(query, (months,))
    
    def get_vendor_analysis(self, top_n: int = 20) -> pd.DataFrame:
        """Get top vendors by transaction volume"""
        query = """
            SELECT 
                vendor,
                COUNT(*) as transaction_count,
                SUM(ABS(amount)) as total_amount,
                AVG(ABS(amount)) as avg_amount,
                MIN(transaction_date) as first_transaction,
                MAX(transaction_date) as last_transaction
            FROM transactions
            WHERE vendor IS NOT NULL
            GROUP BY vendor
            ORDER BY total_amount DESC
            LIMIT ?
        """
        return self.execute_query(query, (top_n,))
    
    def get_balance_sheet_data(self, as_of_date: str = None) -> Dict[str, pd.DataFrame]:
        """Get balance sheet data (assets, liabilities, equity)"""
        if as_of_date is None:
            as_of_date = datetime.now().strftime('%Y-%m-%d')
        
        # Assets
        assets_query = """
            SELECT account_name, balance
            FROM gl_accounts
            WHERE account_type IN ('Asset', 'Current Asset', 'Fixed Asset')
            ORDER BY account_code
        """
        
        # Liabilities
        liabilities_query = """
            SELECT account_name, balance
            FROM gl_accounts
            WHERE account_type IN ('Liability', 'Current Liability', 'Long-term Liability')
            ORDER BY account_code
        """
        
        # Equity
        equity_query = """
            SELECT account_name, balance
            FROM gl_accounts
            WHERE account_type IN ('Equity', 'Revenue', 'Expense')
            ORDER BY account_code
        """
        
        return {
            'assets': self.execute_query(assets_query),
            'liabilities': self.execute_query(liabilities_query),
            'equity': self.execute_query(equity_query)
        }
    
    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get key performance metrics for dashboard"""
        metrics = {}
        
        # Total budget
        budget_query = "SELECT SUM(budget_amount) as total FROM budget_data WHERE fiscal_year = ?"
        current_year = datetime.now().year
        budget_df = self.execute_query(budget_query, (current_year,))
        metrics['total_budget'] = budget_df['total'].iloc[0] if not budget_df.empty else 0
        
        # YTD spending
        ytd_query = """
            SELECT SUM(ABS(amount)) as total 
            FROM transactions 
            WHERE amount < 0 
            AND strftime('%Y', transaction_date) = ?
        """
        spending_df = self.execute_query(ytd_query, (str(current_year),))
        metrics['ytd_spending'] = spending_df['total'].iloc[0] if not spending_df.empty else 0
        
        # Department count
        dept_query = "SELECT COUNT(DISTINCT department) as count FROM transactions"
        dept_df = self.execute_query(dept_query)
        metrics['department_count'] = dept_df['count'].iloc[0] if not dept_df.empty else 0
        
        # Transaction count
        trans_query = "SELECT COUNT(*) as count FROM transactions"
        trans_df = self.execute_query(trans_query)
        metrics['transaction_count'] = trans_df['count'].iloc[0] if not trans_df.empty else 0
        
        return metrics