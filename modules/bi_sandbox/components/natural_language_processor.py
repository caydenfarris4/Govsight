"""
Natural Language Processing for Analytics Queries

This module provides AI-powered natural language interface for intuitive
data queries and analysis commands.
"""

import re
import pandas as pd
from typing import Dict, List, Optional, Any
from .data_structures import create_natural_language_engine_config

class NaturalLanguageAnalytics:
    """AI-powered natural language interface for analytics"""
    
    def __init__(self):
        self.config = create_natural_language_engine_config()
        self.query_patterns = {
            'sum': r'(sum|total|add up)\s+(\w+)',
            'average': r'(average|mean|avg)\s+(\w+)',
            'count': r'(count|number of)\s+(\w+)',
            'max': r'(maximum|max|highest)\s+(\w+)',
            'min': r'(minimum|min|lowest)\s+(\w+)',
            'trend': r'(trend|change|growth)\s+(\w+)',
            'compare': r'(compare|vs|versus)\s+(\w+)\s+(to|with)\s+(\w+)',
            'filter': r'(show|display|filter)\s+(\w+)\s+(where|with)\s+(\w+)',
            'top': r'(top|best|highest)\s+(\d+)\s+(\w+)',
            'bottom': r'(bottom|worst|lowest)\s+(\d+)\s+(\w+)'
        }
    
    def parse_natural_query(self, query: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Parse natural language query into analytical operations"""
        query = query.lower().strip()
        
        # Initialize result structure
        result = {
            'query_type': 'unknown',
            'operation': None,
            'columns': [],
            'filters': [],
            'aggregation': None,
            'limit': None,
            'success': False,
            'data': None,
            'message': 'Unable to parse query'
        }
        
        # Try to match query patterns
        for query_type, pattern in self.query_patterns.items():
            match = re.search(pattern, query)
            if match:
                result['query_type'] = query_type
                result['success'] = True
                
                # Execute based on query type
                if query_type in ['sum', 'average', 'count', 'max', 'min']:
                    column = match.group(2)
                    result = self._execute_aggregation_query(data, column, query_type, result)
                
                elif query_type == 'trend':
                    column = match.group(2)
                    result = self._execute_trend_query(data, column, result)
                
                elif query_type == 'compare':
                    col1, col2 = match.group(2), match.group(4)
                    result = self._execute_comparison_query(data, col1, col2, result)
                
                elif query_type in ['top', 'bottom']:
                    limit = int(match.group(2))
                    column = match.group(3)
                    result = self._execute_ranking_query(data, column, limit, query_type, result)
                
                elif query_type == 'filter':
                    column = match.group(2)
                    filter_value = match.group(4)
                    result = self._execute_filter_query(data, column, filter_value, result)
                
                break
        
        return result
    
    def _execute_aggregation_query(self, data: pd.DataFrame, column: str, agg_type: str, result: Dict) -> Dict:
        """Execute aggregation queries (sum, average, count, max, min)"""
        # Find the best matching column
        matching_col = self._find_best_column_match(data, column)
        if not matching_col:
            result['success'] = False
            result['message'] = f"Column '{column}' not found in data"
            return result
        
        result['columns'] = [matching_col]
        result['aggregation'] = agg_type
        
        try:
            if agg_type == 'sum':
                if data[matching_col].dtype in ['object', 'category']:
                    result['success'] = False
                    result['message'] = f"Cannot sum non-numeric column '{matching_col}'"
                    return result
                value = data[matching_col].sum()
                result['data'] = {'sum': value}
                result['message'] = f"Sum of {matching_col}: {value:,.2f}"
            
            elif agg_type == 'average':
                if data[matching_col].dtype in ['object', 'category']:
                    result['success'] = False
                    result['message'] = f"Cannot average non-numeric column '{matching_col}'"
                    return result
                value = data[matching_col].mean()
                result['data'] = {'average': value}
                result['message'] = f"Average of {matching_col}: {value:,.2f}"
            
            elif agg_type == 'count':
                value = data[matching_col].count()
                result['data'] = {'count': value}
                result['message'] = f"Count of {matching_col}: {value:,}"
            
            elif agg_type == 'max':
                if data[matching_col].dtype in ['object', 'category']:
                    value = data[matching_col].value_counts().index[0]
                    result['data'] = {'max': value}
                    result['message'] = f"Most frequent value in {matching_col}: {value}"
                else:
                    value = data[matching_col].max()
                    result['data'] = {'max': value}
                    result['message'] = f"Maximum of {matching_col}: {value:,.2f}"
            
            elif agg_type == 'min':
                if data[matching_col].dtype in ['object', 'category']:
                    value = data[matching_col].value_counts().index[-1]
                    result['data'] = {'min': value}
                    result['message'] = f"Least frequent value in {matching_col}: {value}"
                else:
                    value = data[matching_col].min()
                    result['data'] = {'min': value}
                    result['message'] = f"Minimum of {matching_col}: {value:,.2f}"
            
        except Exception as e:
            result['success'] = False
            result['message'] = f"Error executing aggregation: {str(e)}"
        
        return result
    
    def _execute_trend_query(self, data: pd.DataFrame, column: str, result: Dict) -> Dict:
        """Execute trend analysis queries"""
        matching_col = self._find_best_column_match(data, column)
        if not matching_col:
            result['success'] = False
            result['message'] = f"Column '{column}' not found in data"
            return result
        
        result['columns'] = [matching_col]
        
        try:
            if data[matching_col].dtype in ['object', 'category']:
                # For categorical data, show value counts trend
                trend_data = data[matching_col].value_counts().head(10)
                result['data'] = {'trend': trend_data.to_dict()}
                result['message'] = f"Top values in {matching_col}: {', '.join(trend_data.index[:5])}"
            else:
                # For numeric data, calculate basic trend statistics
                values = data[matching_col].dropna()
                if len(values) > 1:
                    # Simple trend using first and last values
                    trend_direction = "increasing" if values.iloc[-1] > values.iloc[0] else "decreasing"
                    change_percent = ((values.iloc[-1] - values.iloc[0]) / values.iloc[0]) * 100 if values.iloc[0] != 0 else 0
                    
                    result['data'] = {
                        'trend_direction': trend_direction,
                        'change_percent': change_percent,
                        'first_value': values.iloc[0],
                        'last_value': values.iloc[-1]
                    }
                    result['message'] = f"{matching_col} is {trend_direction} by {abs(change_percent):.1f}%"
                else:
                    result['message'] = f"Insufficient data for trend analysis of {matching_col}"
        
        except Exception as e:
            result['success'] = False
            result['message'] = f"Error executing trend analysis: {str(e)}"
        
        return result
    
    def _execute_comparison_query(self, data: pd.DataFrame, col1: str, col2: str, result: Dict) -> Dict:
        """Execute comparison queries"""
        matching_col1 = self._find_best_column_match(data, col1)
        matching_col2 = self._find_best_column_match(data, col2)
        
        if not matching_col1 or not matching_col2:
            result['success'] = False
            result['message'] = f"One or both columns not found: '{col1}', '{col2}'"
            return result
        
        result['columns'] = [matching_col1, matching_col2]
        
        try:
            if data[matching_col1].dtype in ['int64', 'float64'] and data[matching_col2].dtype in ['int64', 'float64']:
                # Numeric comparison
                corr = data[[matching_col1, matching_col2]].corr().iloc[0, 1]
                avg1 = data[matching_col1].mean()
                avg2 = data[matching_col2].mean()
                
                result['data'] = {
                    'correlation': corr,
                    'average_col1': avg1,
                    'average_col2': avg2,
                    'difference': avg1 - avg2
                }
                result['message'] = f"Correlation between {matching_col1} and {matching_col2}: {corr:.3f}"
            else:
                # Categorical or mixed comparison
                result['data'] = {
                    'unique_values_col1': data[matching_col1].nunique(),
                    'unique_values_col2': data[matching_col2].nunique()
                }
                result['message'] = f"{matching_col1} has {data[matching_col1].nunique()} unique values, {matching_col2} has {data[matching_col2].nunique()}"
        
        except Exception as e:
            result['success'] = False
            result['message'] = f"Error executing comparison: {str(e)}"
        
        return result
    
    def _execute_ranking_query(self, data: pd.DataFrame, column: str, limit: int, direction: str, result: Dict) -> Dict:
        """Execute top/bottom ranking queries"""
        matching_col = self._find_best_column_match(data, column)
        if not matching_col:
            result['success'] = False
            result['message'] = f"Column '{column}' not found in data"
            return result
        
        result['columns'] = [matching_col]
        result['limit'] = limit
        
        try:
            if data[matching_col].dtype in ['object', 'category']:
                # For categorical data, show most/least frequent values
                value_counts = data[matching_col].value_counts()
                if direction == 'top':
                    top_values = value_counts.head(limit)
                else:
                    top_values = value_counts.tail(limit)
                
                result['data'] = {'ranking': top_values.to_dict()}
                result['message'] = f"{direction.title()} {limit} values in {matching_col}: {', '.join(map(str, top_values.index))}"
            else:
                # For numeric data, show highest/lowest values
                if direction == 'top':
                    top_values = data.nlargest(limit, matching_col)[matching_col]
                else:
                    top_values = data.nsmallest(limit, matching_col)[matching_col]
                
                result['data'] = {'ranking': top_values.tolist()}
                result['message'] = f"{direction.title()} {limit} values in {matching_col}: {top_values.min():.2f} to {top_values.max():.2f}"
        
        except Exception as e:
            result['success'] = False
            result['message'] = f"Error executing ranking query: {str(e)}"
        
        return result
    
    def _execute_filter_query(self, data: pd.DataFrame, column: str, filter_value: str, result: Dict) -> Dict:
        """Execute filter queries"""
        matching_col = self._find_best_column_match(data, column)
        if not matching_col:
            result['success'] = False
            result['message'] = f"Column '{column}' not found in data"
            return result
        
        result['columns'] = [matching_col]
        result['filters'] = [{'column': matching_col, 'value': filter_value}]
        
        try:
            # Try different filter approaches
            filtered_data = None
            
            if data[matching_col].dtype in ['object', 'category']:
                # String matching for categorical data
                filtered_data = data[data[matching_col].str.contains(filter_value, case=False, na=False)]
            else:
                # Try to convert filter_value to numeric and filter
                try:
                    numeric_filter = float(filter_value)
                    filtered_data = data[data[matching_col] == numeric_filter]
                except ValueError:
                    result['success'] = False
                    result['message'] = f"Cannot filter numeric column {matching_col} with non-numeric value '{filter_value}'"
                    return result
            
            if filtered_data is not None and not filtered_data.empty:
                result['data'] = {
                    'filtered_count': len(filtered_data),
                    'total_count': len(data),
                    'percentage': (len(filtered_data) / len(data)) * 100
                }
                result['message'] = f"Found {len(filtered_data)} records where {matching_col} matches '{filter_value}' ({(len(filtered_data)/len(data)*100):.1f}%)"
            else:
                result['message'] = f"No records found where {matching_col} matches '{filter_value}'"
        
        except Exception as e:
            result['success'] = False
            result['message'] = f"Error executing filter query: {str(e)}"
        
        return result
    
    def _find_best_column_match(self, data: pd.DataFrame, column_query: str) -> Optional[str]:
        """Find the best matching column name in the DataFrame"""
        if column_query in data.columns:
            return column_query
        
        # Try case-insensitive match
        for col in data.columns:
            if col.lower() == column_query.lower():
                return col
        
        # Try partial matches
        for col in data.columns:
            if column_query.lower() in col.lower():
                return col
        
        # Try fuzzy matching (simple version)
        for col in data.columns:
            if any(part in col.lower() for part in column_query.lower().split()):
                return col
        
        return None
    
    def get_suggested_queries(self, data: pd.DataFrame) -> List[str]:
        """Generate suggested natural language queries based on data"""
        suggestions = []
        
        if data.empty:
            return suggestions
        
        numeric_columns = data.select_dtypes(include=['int64', 'float64']).columns
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns
        
        # Aggregation suggestions
        for col in numeric_columns[:3]:  # Limit to first 3 columns
            suggestions.extend([
                f"What is the sum of {col}?",
                f"What is the average {col}?",
                f"What is the maximum {col}?"
            ])
        
        # Categorical analysis suggestions
        for col in categorical_columns[:2]:  # Limit to first 2 columns
            suggestions.extend([
                f"Count the number of {col}",
                f"Show top 5 {col}"
            ])
        
        # Comparison suggestions
        if len(numeric_columns) >= 2:
            suggestions.append(f"Compare {numeric_columns[0]} to {numeric_columns[1]}")
        
        # Trend suggestions
        if len(data) > 10:
            for col in numeric_columns[:2]:
                suggestions.append(f"Show trend for {col}")
        
        return suggestions[:10]  # Return top 10 suggestions