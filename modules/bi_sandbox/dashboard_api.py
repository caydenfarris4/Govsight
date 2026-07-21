"""
Dashboard API - Backend endpoints for the Visual Analytics dashboard
Provides data endpoints and Mantis AI integration for the dashboard
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import time
from functools import lru_cache
import asyncio

# Import existing modules
from modules.database.db_connection import (
    load_org_data, get_departments, format_currency, 
    format_percentage, get_connection
)
# Import multi-database manager for schema discovery
from .multi_database_manager import MultiDatabaseManager
# Import will be handled dynamically to avoid import errors
# Organization service import handled dynamically

logger = logging.getLogger(__name__)

class DashboardAPI:
    """API class for dashboard data and AI integration"""
    
    def __init__(self):
        self.current_org = None
        self.cached_data = {}
        self.cache_timestamp = None
        self.schema_cache = None
        self.schema_cache_time = 0
        self.cache_duration = 300  # 5 minutes cache
        # Initialize multi-database manager for schema discovery
        self.db_manager = MultiDatabaseManager()
    
    def get_dashboard_data(self, org: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for the specified organization
        
        Args:
            org: Organization identifier
            
        Returns:
            Dictionary containing all dashboard data
        """
        try:
            if not org:
                org = "cityA"  # Default organization
            
            self.current_org = org
            
            # Load organization data with graceful fallback
            try:
                df = load_org_data(org)
            except Exception as e:
                logger.warning(f"Failed to load data for org '{org}': {e}")
                # Fallback to default organization
                if org != "cityA":
                    logger.info("Falling back to default organization 'cityA'")
                    df = load_org_data("cityA")
                    org = "cityA"
                else:
                    return self._get_empty_dashboard_data(org)
            
            if df.empty:
                return self._get_empty_dashboard_data(org)
            
            # Calculate KPIs
            kpis = self._calculate_kpis(df)
            
            # Get filter options
            filters = self._get_filter_options(df)
            
            # Prepare chart data
            chart_data = self._prepare_chart_data(df)
            
            # Generate AI insights
            insights = self._generate_insights(df, kpis)
            
            # Get database schema information
            database_schema = self._get_database_schema()
            
            dashboard_data = {
                'organization': self._get_organization_display_name(org),
                'timestamp': datetime.now().isoformat(),
                'kpis': kpis,
                'filters': filters,
                'chartData': chart_data,
                'insights': insights,
                'tableData': self._prepare_table_data(df),
                'databaseSchema': database_schema,
                'connectionStatus': self._get_connection_status()
            }
            
            # Cache the data
            self.cached_data = dashboard_data
            self.cache_timestamp = datetime.now()
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return self._get_error_dashboard_data(str(e))
    
    def _calculate_kpis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate KPI values from the data"""
        try:
            # Total budget
            total_budget = df['Budget'].sum() if 'Budget' in df.columns else 0
            total_actual = df['Actual'].sum() if 'Actual' in df.columns else 0
            
            # Department count
            dept_count = df['Department'].nunique() if 'Department' in df.columns else 0
            
            # Budget variance
            variance = total_actual - total_budget
            variance_percent = (variance / total_budget * 100) if total_budget > 0 else 0
            
            # Fund utilization (actual vs budget)
            utilization = (total_actual / total_budget * 100) if total_budget > 0 else 0
            
            # Calculate year-over-year changes (mock for now)
            budget_change = 12.3  # This would be calculated from historical data
            dept_change = 3       # This would be calculated from historical data
            utilization_change = 2.1  # This would be calculated from historical data
            
            return {
                'totalBudget': total_budget,
                'budgetChange': budget_change,
                'departmentCount': dept_count,
                'departmentChange': dept_change,
                'variance': variance,
                'variancePercent': variance_percent,
                'utilization': min(utilization, 100),  # Cap at 100%
                'utilizationChange': utilization_change
            }
            
        except Exception as e:
            logger.error(f"Error calculating KPIs: {e}")
            return self._get_default_kpis()
    
    def _get_filter_options(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Get comprehensive filter options from the data"""
        try:
            filters = {
                'departments': [],
                'years': [],
                'funds': [],
                'accounts': [],
                'quarters': [],
                'budget_types': [],
                'vendors': [],
                'amounts': []
            }
            
            # Department filter
            if 'Department' in df.columns:
                dept_list = sorted(df['Department'].dropna().unique().tolist())
                filters['departments'] = [{'value': dept, 'label': dept, 'count': len(df[df['Department'] == dept])} for dept in dept_list]
            
            # Year filter with intelligent extraction
            years = set()
            for col in ['Year', 'Period', 'FiscalYear', 'TransactionDate']:
                if col in df.columns:
                    if col == 'Year':
                        years.update(df[col].dropna().astype(str).tolist())
                    elif col == 'Period':
                        # Extract years from period format (e.g., "725" -> "2025")
                        period_years = df[col].dropna().apply(lambda x: f"20{str(x)[-2:]}" if len(str(x)) >= 2 else "2024")
                        years.update(period_years.tolist())
                    elif col == 'TransactionDate':
                        # Extract years from date columns
                        try:
                            date_years = pd.to_datetime(df[col], errors='coerce').dt.year.dropna().astype(str)
                            years.update(date_years.tolist())
                        except:
                            pass
            
            if years:
                year_list = sorted(list(years))
                filters['years'] = [{'value': year, 'label': year, 'count': 0} for year in year_list]
            
            # Fund filter
            if 'Fund' in df.columns:
                fund_list = sorted(df['Fund'].dropna().unique().tolist())
                filters['funds'] = [{'value': fund, 'label': fund, 'count': len(df[df['Fund'] == fund])} for fund in fund_list]
            
            # Account filter (GL Accounts)
            for col in ['GLAccount', 'Account', 'AccountCode', 'GLAccountCode']:
                if col in df.columns:
                    account_list = sorted(df[col].dropna().unique().tolist())
                    filters['accounts'] = [{'value': acc, 'label': str(acc), 'count': len(df[df[col] == acc])} for acc in account_list[:50]]  # Limit to top 50
                    break
            
            # Quarter filter
            if 'Quarter' in df.columns:
                quarter_list = sorted(df['Quarter'].dropna().unique().tolist())
                filters['quarters'] = [{'value': q, 'label': f"Q{q}", 'count': len(df[df['Quarter'] == q])} for q in quarter_list]
            
            # Budget type filter
            for col in ['BudgetType', 'Type', 'Category']:
                if col in df.columns:
                    type_list = sorted(df[col].dropna().unique().tolist())
                    filters['budget_types'] = [{'value': bt, 'label': bt, 'count': len(df[df[col] == bt])} for bt in type_list]
                    break
            
            # Vendor filter (if available)
            if 'Vendor' in df.columns:
                vendor_list = sorted(df['Vendor'].dropna().unique().tolist())
                filters['vendors'] = [{'value': vendor, 'label': vendor, 'count': len(df[df['Vendor'] == vendor])} for vendor in vendor_list[:20]]  # Top 20 vendors
            
            # Amount ranges for filtering
            amount_cols = ['Amount', 'Budget', 'Actual', 'Total']
            for col in amount_cols:
                if col in df.columns and df[col].dtype in ['int64', 'float64']:
                    amounts = df[col].dropna()
                    if len(amounts) > 0:
                        min_amt, max_amt = amounts.min(), amounts.max()
                        # Create amount ranges
                        ranges = [
                            {'value': 'under_1k', 'label': 'Under $1K', 'min': 0, 'max': 1000},
                            {'value': '1k_10k', 'label': '$1K - $10K', 'min': 1000, 'max': 10000},
                            {'value': '10k_50k', 'label': '$10K - $50K', 'min': 10000, 'max': 50000},
                            {'value': '50k_100k', 'label': '$50K - $100K', 'min': 50000, 'max': 100000},
                            {'value': 'over_100k', 'label': 'Over $100K', 'min': 100000, 'max': float('inf')}
                        ]
                        for r in ranges:
                            count = len(amounts[(amounts >= r['min']) & (amounts < r['max'])])
                            r['count'] = count
                        filters['amounts'] = ranges
                    break
            
            return filters
            
        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
            return {
                'departments': [], 'years': [], 'funds': [], 'accounts': [],
                'quarters': [], 'budget_types': [], 'vendors': [], 'amounts': []
            }
    
    def _prepare_chart_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Prepare data for charts"""
        try:
            chart_data = {}
            
            # Department budget analysis
            if 'Department' in df.columns:
                dept_summary = df.groupby('Department').agg({
                    'Budget': 'sum',
                    'Actual': 'sum'
                }).reset_index()
                
                chart_data['departmentBudgets'] = [
                    {
                        'department': row['Department'],
                        'budget': row['Budget'],
                        'actual': row['Actual']
                    }
                    for _, row in dept_summary.iterrows()
                ]
            
            # Monthly trends (mock data for now)
            chart_data['monthlyTrends'] = [
                {'month': 'Jan', 'budget': 180000, 'actual': 175000},
                {'month': 'Feb', 'budget': 180000, 'actual': 185000},
                {'month': 'Mar', 'budget': 180000, 'actual': 172000},
                {'month': 'Apr', 'budget': 180000, 'actual': 188000},
                {'month': 'May', 'budget': 180000, 'actual': 179000},
                {'month': 'Jun', 'budget': 180000, 'actual': 182000}
            ]
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error preparing chart data: {e}")
            return {}
    
    def _prepare_table_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare data for the data table"""
        try:
            if df.empty:
                return []
            
            # Group by department for table display
            if 'Department' in df.columns:
                table_data = df.groupby('Department').agg({
                    'Budget': 'sum',
                    'Actual': 'sum'
                }).reset_index()
                
                return [
                    {
                        'department': row['Department'],
                        'budget': row['Budget'],
                        'actual': row['Actual'],
                        'variance': row['Actual'] - row['Budget'],
                        'variancePercent': ((row['Actual'] - row['Budget']) / row['Budget'] * 100) if row['Budget'] > 0 else 0
                    }
                    for _, row in table_data.iterrows()
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error preparing table data: {e}")
            return []
    
    def _generate_insights(self, df: pd.DataFrame, kpis: Dict[str, Any]) -> List[str]:
        """Generate AI insights based on the data"""
        try:
            insights = []
            
            # Budget variance insights
            if kpis.get('variancePercent', 0) > 5:
                insights.append("Several departments are significantly over budget. Consider implementing stricter budget controls and regular monitoring.")
            elif kpis.get('variancePercent', 0) < -5:
                insights.append("Departments are consistently under budget. This may indicate conservative budgeting or potential for increased service delivery.")
            
            # Department-specific insights
            if 'Department' in df.columns and 'Budget' in df.columns and 'Actual' in df.columns:
                dept_analysis = df.groupby('Department').agg({
                    'Budget': 'sum',
                    'Actual': 'sum'
                }).reset_index()
                
                dept_analysis['variance_pct'] = ((dept_analysis['Actual'] - dept_analysis['Budget']) / dept_analysis['Budget'] * 100)
                
                # Find departments with highest variance
                over_budget = dept_analysis[dept_analysis['variance_pct'] > 10]
                if not over_budget.empty:
                    dept_name = over_budget.iloc[0]['Department']
                    variance = over_budget.iloc[0]['variance_pct']
                    insights.append(f"{dept_name} department is {variance:.1f}% over budget. Recommend immediate review of spending patterns and budget adjustments.")
                
                # Find efficient departments
                efficient = dept_analysis[(dept_analysis['variance_pct'] >= -5) & (dept_analysis['variance_pct'] <= 5)]
                if not efficient.empty:
                    dept_name = efficient.iloc[0]['Department']
                    insights.append(f"{dept_name} department is demonstrating excellent budget management with minimal variance. Consider sharing their best practices.")
            
            # Utilization insights
            if kpis.get('utilization', 0) > 95:
                insights.append("High budget utilization indicates active spending. Monitor cash flow and ensure reserves are adequate.")
            elif kpis.get('utilization', 0) < 75:
                insights.append("Low budget utilization may indicate opportunity for additional projects or services, or conservative budget estimates.")
            
            # Default insights if none generated
            if not insights:
                insights = [
                    "Budget performance is within normal parameters. Continue regular monitoring for optimal financial management.",
                    "Consider implementing quarterly budget reviews to identify trends early and make timely adjustments.",
                    "Current financial health appears stable. Focus on strategic initiatives and long-term planning."
                ]
            
            return insights[:3]  # Limit to 3 insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return ["Error generating insights. Please check data quality and try again."]
    
    def process_ai_chat(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process AI chat message with dashboard context
        
        Args:
            message: User's chat message
            context: Current dashboard context
            
        Returns:
            AI response with optional dashboard updates
        """
        try:
            # Enhance context with current data
            enhanced_context = {
                **context,
                'dashboardData': self.cached_data,
                'organization': self.current_org,
                'dataAvailable': bool(self.cached_data)
            }
            
            # Process with simple AI response for now (can be enhanced later)
            ai_response = self._generate_dashboard_ai_response(message, enhanced_context)
            
            # Determine if dashboard updates are needed
            dashboard_updates = self._analyze_for_dashboard_updates(message, ai_response)
            
            return {
                'message': ai_response,
                'dashboard_updates': dashboard_updates,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing AI chat: {e}")
            return {
                'message': "I apologize, but I'm having trouble processing your request right now. Please try rephrasing your question or contact support if the issue persists.",
                'dashboard_updates': None,
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_dashboard_ai_response(self, message: str, context: Dict[str, Any]) -> str:
        """Generate AI response for dashboard queries"""
        message_lower = message.lower()
        
        # Check if we have dashboard data to work with
        dashboard_data = context.get('dashboardData', {})
        kpis = dashboard_data.get('kpis', {})
        
        # Department-specific responses
        if 'police' in message_lower:
            if kpis.get('variancePercent', 0) > 5:
                return "The Police department appears to be over budget. This is typically due to increased overtime costs from community events and staff shortages. I recommend reviewing patrol schedules and considering additional officer hiring to reduce overtime dependency."
            else:
                return "The Police department is performing within budget parameters. Current spending patterns appear sustainable."
        
        elif 'parks' in message_lower or 'recreation' in message_lower:
            return "Parks & Recreation is demonstrating efficient budget management. Citizen satisfaction surveys typically show high approval for park services. Consider allocating additional funds for community-requested improvements."
        
        elif 'fire' in message_lower:
            return "The Fire department typically maintains excellent budget discipline. Their emergency response capabilities remain strong while managing costs effectively."
        
        # Budget analysis responses
        elif any(word in message_lower for word in ['budget', 'variance', 'spending']):
            total_budget = kpis.get('totalBudget', 0)
            variance_pct = kpis.get('variancePercent', 0)
            
            if variance_pct > 5:
                return f"Current budget shows a variance of {variance_pct:.1f}%, indicating some departments are over budget. The total budget is {format_currency(total_budget)}. Focus on departments with highest variances for immediate attention."
            elif variance_pct < -5:
                return f"Budget is running {abs(variance_pct):.1f}% under projections, which may indicate conservative estimates or opportunities for additional services. Total budget: {format_currency(total_budget)}."
            else:
                return f"Budget performance is within normal parameters with {variance_pct:.1f}% variance. Total budget of {format_currency(total_budget)} is being managed effectively."
        
        # Department attention requests
        elif 'attention' in message_lower or 'focus' in message_lower:
            return "Based on current data, I recommend focusing on: 1) Departments with highest budget variances, 2) Areas with declining performance metrics, 3) Opportunities for efficiency improvements. Check the variance column in the data table for specific departments needing attention."
        
        # Trend analysis
        elif 'trend' in message_lower:
            utilization = kpis.get('utilization', 0)
            return f"Current fund utilization is at {utilization}%. Revenue trends are generally stable. Monitor quarterly patterns and seasonal variations for better forecasting."
        
        # Revenue questions
        elif 'revenue' in message_lower or 'income' in message_lower:
            budget_change = kpis.get('budgetChange', 0)
            if budget_change > 0:
                return f"Revenue is trending {budget_change}% above last year, primarily from property tax increases and grant funding. This provides opportunities for strategic investments or reserve building."
            else:
                return "Revenue streams are stable. Monitor economic indicators and consider diversification strategies for long-term sustainability."
        
        # Default helpful response
        else:
            org_name = context.get('organization', 'your organization')
            return f"I can help you analyze {org_name}'s financial data. Try asking me about:\n• Department budget performance\n• Budget variances and trends\n• Revenue analysis\n• Which departments need attention\n• Spending patterns and utilization\n\nWhat specific area would you like to explore?"
    
    def _analyze_for_dashboard_updates(self, message: str, ai_response: str) -> Optional[Dict[str, Any]]:
        """Analyze if the AI response suggests dashboard updates"""
        updates = {}
        
        # Check for department focus requests
        message_lower = message.lower()
        if 'show' in message_lower and any(dept in message_lower for dept in ['police', 'fire', 'parks', 'public works']):
            for dept in ['police', 'fire', 'parks', 'public works']:
                if dept in message_lower:
                    updates['highlightDepartment'] = dept.title()
                    break
        
        # Check for filter suggestions
        if 'filter' in message_lower or 'focus on' in message_lower:
            updates['suggestFilter'] = True
        
        return updates if updates else None
    
    def _get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information from MultiDatabaseManager"""
        try:
            # Get all database connections
            connections = self.db_manager.get_all_database_connections()
            
            # Discover schemas for all connected databases
            schemas = self.db_manager.discover_database_schemas(force_refresh=False)
            
            # Format schema data for frontend
            schema_data = {
                'databases': {},
                'field_tree': {},
                'unified_catalog': [],
                'summary': {
                    'total_databases': len(connections),
                    'connected_databases': len([db for db in connections.values() if db]),
                    'total_tables': 0,
                    'total_fields': 0
                }
            }
            
            # Process each database schema
            for db_name, schema in schemas.items():
                if 'error' not in schema:
                    # Count tables and fields
                    table_count = len(schema.get('tables', {}))
                    field_count = sum(len(table.get('columns', [])) for table in schema.get('tables', {}).values())
                    
                    schema_data['summary']['total_tables'] += table_count
                    schema_data['summary']['total_fields'] += field_count
                    
                    # Add to databases collection
                    schema_data['databases'][db_name] = {
                        'display_name': schema.get('display_name', db_name),
                        'database_type': schema.get('database_type', 'unknown'),
                        'description': schema.get('description', ''),
                        'table_count': table_count,
                        'field_count': field_count,
                        'tables': schema.get('tables', {})
                    }
                    
                    # Build field tree structure for frontend
                    schema_data['field_tree'][db_name] = {
                        'name': schema.get('display_name', db_name),
                        'type': 'database',
                        'children': []
                    }
                    
                    for table_name, table_info in schema.get('tables', {}).items():
                        table_node = {
                            'name': table_name,
                            'type': 'table',
                            'children': []
                        }
                        
                        for column in table_info.get('columns', []):
                            field_node = {
                                'name': column.get('name', ''),
                                'type': 'field',
                                'data_type': column.get('type', 'unknown'),
                                'nullable': column.get('nullable', True),
                                'primary_key': column.get('primary_key', False)
                            }
                            table_node['children'].append(field_node)
                            
                            # Add to unified catalog
                            schema_data['unified_catalog'].append({
                                'database': db_name,
                                'table': table_name,
                                'field': column.get('name', ''),
                                'type': column.get('type', 'unknown'),
                                'full_path': f"{db_name}.{table_name}.{column.get('name', '')}"
                            })
                        
                        schema_data['field_tree'][db_name]['children'].append(table_node)
            
            return schema_data
            
        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            return {
                'databases': {},
                'field_tree': {},
                'unified_catalog': [],
                'summary': {'total_databases': 0, 'connected_databases': 0, 'total_tables': 0, 'total_fields': 0},
                'error': str(e)
            }
    
    def _get_connection_status(self) -> Dict[str, Any]:
        """Get database connection status"""
        try:
            connections = self.db_manager.get_all_database_connections()
            
            status = {
                'overall_status': 'connected' if connections else 'disconnected',
                'databases': {},
                'summary': {
                    'total': len(self.db_manager.config.get('databases', {})),
                    'connected': len(connections),
                    'failed': len(self.db_manager.config.get('databases', {})) - len(connections)
                }
            }
            
            # Check status of each configured database
            for db_name, db_config in self.db_manager.config.get('databases', {}).items():
                is_connected = db_name in connections
                status['databases'][db_name] = {
                    'name': db_config.get('display_name', db_name),
                    'type': db_config.get('type', 'unknown'),
                    'status': 'connected' if is_connected else 'disconnected',
                    'last_checked': datetime.now().isoformat()
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return {
                'overall_status': 'error',
                'databases': {},
                'summary': {'total': 0, 'connected': 0, 'failed': 0},
                'error': str(e)
            }
    
    def _get_organization_display_name(self, org: Optional[str]) -> str:
        """Get display name for organization"""
        org_names = {
            'cityA': 'Spanish Fork',
            'cityB': 'Municipal Demo',
            'spanish_fork': 'Spanish Fork'
        }
        if org is not None:
            return org_names.get(org, org.replace('_', ' ').title())
        else:
            return 'Unknown Organization'
    
    def _get_empty_dashboard_data(self, org: str) -> Dict[str, Any]:
        """Return empty dashboard data structure"""
        return {
            'organization': self._get_organization_display_name(org),
            'timestamp': datetime.now().isoformat(),
            'kpis': self._get_default_kpis(),
            'filters': {'departments': [], 'years': [], 'funds': []},
            'chartData': {},
            'insights': ["No data available for analysis. Please check data connections and try again."],
            'tableData': []
        }
    
    def get_fast_schema(self) -> Dict[str, Any]:
        """
        Get database schema optimized for Visual Analytics interface
        Uses caching and progressive loading for sub-5 second performance
        """
        try:
            # Check cache first
            current_time = time.time()
            if (self.schema_cache and 
                current_time - self.schema_cache_time < self.cache_duration):
                logger.info("Returning cached schema data")
                return self.schema_cache
            
            logger.info("Loading fresh schema data...")
            start_time = time.time()
            
            # Get schema from database manager using correct method
            # Use get_unified_field_catalog for field information
            field_catalog = self.db_manager.get_unified_field_catalog()
            
            # Transform catalog to schema format
            schema = self._catalog_to_schema(field_catalog)
            
            # Transform schema for Visual Analytics interface
            transformed_schema = {
                'databases': {},
                'field_types': {
                    'measures': [],
                    'dimensions': [], 
                    'dates': [],
                    'calculations': []
                },
                'quick_fields': [],
                'statistics': {
                    'total_tables': 0,
                    'total_columns': 0,
                    'total_databases': 0
                }
            }
            
            all_fields = []
            
            for db_name, db_info in schema.items():
                if isinstance(db_info, dict) and 'tables' in db_info:
                    db_data = {
                        'name': db_name,
                        'display_name': db_name.replace('_', ' ').title(),
                        'tables': [],
                        'field_count': 0
                    }
                    
                    for table_name, table_info in db_info['tables'].items():
                        table_data = {
                            'name': table_name,
                            'display_name': table_name.replace('_', ' ').title(),
                            'database': db_name,
                            'columns': []
                        }
                        
                        if isinstance(table_info, dict) and 'columns' in table_info:
                            for col_name, col_info in table_info['columns'].items():
                                col_type = col_info.get('type', 'text').lower()
                                
                                # Categorize field for visual analytics
                                field_category = self._categorize_field_analytics_style(col_type, col_name)
                                
                                field_data = {
                                    'name': col_name,
                                    'display_name': col_name.replace('_', ' ').title(),
                                    'type': col_type,
                                    'category': field_category,
                                    'table': table_name,
                                    'database': db_name,
                                    'full_name': f"{db_name}.{table_name}.{col_name}",
                                    'draggable': True,
                                    'icon': self._get_field_icon(field_category),
                                    'nullable': col_info.get('nullable', True)
                                }
                                
                                table_data['columns'].append(field_data)
                                all_fields.append(field_data)
                                
                                # Add to field type categories
                                transformed_schema['field_types'][field_category].append(field_data)
                                
                                transformed_schema['statistics']['total_columns'] += 1
                                db_data['field_count'] += 1
                        
                        if table_data['columns']:  # Only add tables with columns
                            db_data['tables'].append(table_data)
                            transformed_schema['statistics']['total_tables'] += 1
                    
                    if db_data['tables']:  # Only add databases with tables
                        transformed_schema['databases'][db_name] = db_data
                        transformed_schema['statistics']['total_databases'] += 1
            
            # Create quick fields list (most useful fields)
            transformed_schema['quick_fields'] = self._get_quick_fields(all_fields)
            
            load_time = time.time() - start_time
            
            result = {
                'success': True,
                'data': transformed_schema,
                'load_time': round(load_time, 2),
                'cached': False,
                'message': f"Schema loaded: {transformed_schema['statistics']['total_databases']} databases, {transformed_schema['statistics']['total_tables']} tables, {transformed_schema['statistics']['total_columns']} fields"
            }
            
            # Cache the result
            self.schema_cache = result
            self.schema_cache_time = current_time
            
            logger.info(f"Schema loaded in {load_time:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error getting fast schema: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to load database schema'
            }
    
    def _catalog_to_schema(self, catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert field catalog to schema format"""
        schema = {}
        
        for field in catalog:
            db_name = field.get('database', 'default')
            table_name = field.get('table', 'unknown')
            
            if db_name not in schema:
                schema[db_name] = {'tables': {}}
            if table_name not in schema[db_name]['tables']:
                schema[db_name]['tables'][table_name] = {'columns': {}}
            
            col_name = field.get('column_name', field.get('field_name', 'unknown'))
            schema[db_name]['tables'][table_name]['columns'][col_name] = {
                'type': field.get('data_type', 'text'),
                'nullable': field.get('nullable', True)
            }
        
        return schema
    
    def _categorize_field_analytics_style(self, col_type: str, col_name: str) -> str:
        """Categorize fields for better analytics UX"""
        col_type = col_type.lower()
        col_name = col_name.lower()
        
        # Date/time types
        if any(t in col_type for t in ['date', 'time', 'timestamp']):
            return 'dates'
        
        # Numeric types - check if it's a measure or dimension
        elif any(t in col_type for t in ['int', 'float', 'decimal', 'numeric', 'money']):
            # Measure indicators
            measure_keywords = ['amount', 'total', 'sum', 'cost', 'price', 'budget', 'actual', 'balance', 'salary', 'wage']
            if any(keyword in col_name for keyword in measure_keywords):
                return 'measures'
            # ID/Key fields are dimensions even if numeric
            elif any(keyword in col_name for keyword in ['id', 'key', 'code', 'number']):
                return 'dimensions'
            else:
                return 'measures'  # Default numeric to measures
        
        # Text/categorical types - dimensions
        else:
            return 'dimensions'
    
    def _get_field_icon(self, field_category: str) -> str:
        """Get icon for field category for visual analytics"""
        icons = {
            'measures': '∑',      # Sum symbol for measures
            'dimensions': '📦',   # Box symbol for dimensions  
            'dates': '📅',       # Calendar for dates
            'calculations': '🧮'  # Calculator for calculated fields
        }
        return icons.get(field_category, '📊')
    
    def _get_quick_fields(self, all_fields: List[Dict]) -> List[Dict]:
        """Get the most commonly used fields for quick access"""
        # Priority patterns (higher priority = lower number)
        priority_patterns = {
            'amount': 1, 'total': 2, 'sum': 3, 'budget': 4, 'actual': 5,
            'department': 10, 'fund': 11, 'account': 12, 'year': 13, 'month': 14,
            'date': 15, 'name': 16, 'description': 17, 'type': 18, 'category': 19
        }
        
        # Score and sort fields
        scored_fields = []
        for field in all_fields:
            score = 100  # Default low priority
            field_name = field['name'].lower()
            
            for pattern, priority in priority_patterns.items():
                if pattern in field_name:
                    score = min(score, priority)  # Take highest priority (lowest number)
            
            scored_fields.append((score, field))
        
        # Sort by score and return top 15
        scored_fields.sort(key=lambda x: x[0])
        return [field for score, field in scored_fields[:15]]
    
    def _get_default_kpis(self) -> Dict[str, Any]:
        """Return default KPI values"""
        return {
            'totalBudget': 0,
            'budgetChange': 0,
            'departmentCount': 0,
            'departmentChange': 0,
            'variance': 0,
            'variancePercent': 0,
            'utilization': 0,
            'utilizationChange': 0
        }
    
    def _get_error_dashboard_data(self, error_message: str) -> Dict[str, Any]:
        """Return error dashboard data"""
        return {
            'organization': 'Error',
            'timestamp': datetime.now().isoformat(),
            'error': error_message,
            'kpis': self._get_default_kpis(),
            'filters': {'departments': [], 'years': [], 'funds': []},
            'chartData': {},
            'insights': [f"Error loading dashboard: {error_message}"],
            'tableData': []
        }

# Global instance
_dashboard_api = None

def get_dashboard_api() -> DashboardAPI:
    """Get global dashboard API instance"""
    global _dashboard_api
    if _dashboard_api is None:
        _dashboard_api = DashboardAPI()
    return _dashboard_api

# Streamlit API endpoints (for integration with Streamlit's session)
def handle_dashboard_data_request(org: Optional[str] = None) -> str:
    """Handle dashboard data request and return JSON"""
    api = get_dashboard_api()
    data = api.get_dashboard_data(org)
    return json.dumps(data, default=str)

def handle_ai_chat_request(message: str, context: Dict[str, Any]) -> str:
    """Handle AI chat request and return JSON"""
    api = get_dashboard_api()
    response = api.process_ai_chat(message, context)
    return json.dumps(response, default=str)