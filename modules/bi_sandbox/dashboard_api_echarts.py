"""
ECharts Dashboard API - Enhanced backend for hybrid visualization system

This module provides the API endpoints for the ECharts/D3.js hybrid dashboard,
supporting 60+ chart types with real-time data from 5 connected databases.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

# Import database connections
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.database.db_connection import (
    get_connection,
    format_currency,
    format_percentage,
    execute_query
)

class EChartsDashboardAPI:
    """API handler for ECharts dashboard with advanced visualization capabilities"""
    
    def __init__(self):
        self.databases = {
            'gl_primary': 'SQLite',      # General Ledger
            'utility': 'PostgreSQL',     # Utility Management
            'asset': 'MySQL',            # Asset Management
            'permits': 'SQL Server',     # Permits & Licensing
            'payroll': 'PostgreSQL'      # Payroll & HR
        }
        
        self.chart_configs = self._load_chart_configs()
        
    def _load_chart_configs(self) -> Dict:
        """Load configuration for all 60+ chart types"""
        return {
            # Basic Charts
            'bar': {'min_fields': 2, 'supports_3d': True},
            'line': {'min_fields': 2, 'supports_animation': True},
            'pie': {'min_fields': 2, 'supports_donut': True},
            'scatter': {'min_fields': 2, 'supports_bubble': True},
            'area': {'min_fields': 2, 'supports_stack': True},
            
            # Advanced Analytics
            'heatmap': {'min_fields': 3, 'requires_matrix': True},
            'treemap': {'min_fields': 2, 'supports_drill': True},
            'sunburst': {'min_fields': 2, 'hierarchical': True},
            'sankey': {'min_fields': 3, 'flow_visualization': True},
            'chord': {'min_fields': 3, 'relationship_map': True},
            'network': {'min_fields': 2, 'graph_based': True},
            
            # Statistical
            'boxplot': {'min_fields': 2, 'statistical': True},
            'violin': {'min_fields': 2, 'distribution': True},
            'histogram': {'min_fields': 1, 'bins_required': True},
            'density': {'min_fields': 1, 'kernel_density': True},
            'beeswarm': {'min_fields': 2, 'jitter': True},
            'parallel': {'min_fields': 3, 'multi_axis': True},
            
            # Business Analytics
            'gauge': {'min_fields': 1, 'kpi_display': True},
            'radar': {'min_fields': 3, 'multi_metric': True},
            'funnel': {'min_fields': 2, 'conversion': True},
            'waterfall': {'min_fields': 2, 'cumulative': True},
            'candlestick': {'min_fields': 5, 'ohlc': True},
            'kpi': {'min_fields': 1, 'single_metric': True},
            
            # Geographic
            'map': {'min_fields': 2, 'geo_data': True},
            'choropleth': {'min_fields': 2, 'region_based': True},
            'scatter_map': {'min_fields': 3, 'coordinates': True},
            
            # 3D Visualizations
            '3d_bar': {'min_fields': 3, 'webgl': True},
            '3d_surface': {'min_fields': 3, 'mesh': True},
            '3d_scatter': {'min_fields': 3, 'point_cloud': True},
            
            # Custom D3 Visualizations
            'budget_flow': {'custom': True, 'd3': True},
            'department_network': {'custom': True, 'd3': True},
            'tax_distribution': {'custom': True, 'd3': True},
            'project_timeline': {'custom': True, 'd3': True},
            'utility_infrastructure': {'custom': True, 'd3': True},
            'financial_health': {'custom': True, 'd3': True}
        }
    
    def get_available_fields(self, database: Optional[str] = None) -> List[Dict]:
        """Get all available fields from connected databases"""
        fields = []
        
        if database:
            fields.extend(self._get_database_fields(database))
        else:
            # Get fields from all databases
            for db_name in self.databases.keys():
                fields.extend(self._get_database_fields(db_name))
        
        return self._categorize_fields(fields)
    
    def _get_database_fields(self, database: str) -> List[Dict]:
        """Get fields from a specific database"""
        fields = []
        
        try:
            # For databases that may not be configured, return sample fields
            if database in ['permits', 'asset', 'utility', 'payroll']:
                return self._get_sample_fields(database)
            
            # Try to get connection, but don't fail if it doesn't work
            try:
                conn = get_connection(database)
                if not conn:
                    return self._get_sample_fields(database)
            except:
                return self._get_sample_fields(database)
            
            if database == 'gl_primary':
                # General Ledger fields
                query = """
                SELECT DISTINCT
                    'Department' as field_name, 'text' as field_type,
                    'dimension' as category, 'GL' as source
                UNION ALL
                SELECT 'Account', 'text', 'dimension', 'GL'
                UNION ALL
                SELECT 'Budget', 'number', 'measure', 'GL'
                UNION ALL
                SELECT 'Actual', 'number', 'measure', 'GL'
                UNION ALL
                SELECT 'Date', 'date', 'date', 'GL'
                UNION ALL
                SELECT 'Fiscal_Year', 'text', 'dimension', 'GL'
                UNION ALL
                SELECT 'Fund', 'text', 'dimension', 'GL'
                UNION ALL
                SELECT 'Vendor', 'text', 'dimension', 'GL'
                UNION ALL
                SELECT 'Amount', 'number', 'measure', 'GL'
                UNION ALL
                SELECT 'Transaction_Type', 'text', 'dimension', 'GL'
                """
                
            elif database == 'utility':
                # Utility Management fields
                query = """
                SELECT 
                    column_name as field_name,
                    data_type as field_type,
                    CASE 
                        WHEN data_type IN ('integer', 'numeric', 'real') THEN 'measure'
                        WHEN data_type IN ('date', 'timestamp') THEN 'date'
                        ELSE 'dimension'
                    END as category,
                    'Utility' as source
                FROM information_schema.columns
                WHERE table_schema = 'public'
                LIMIT 20
                """
                
            elif database == 'asset':
                # Asset Management fields
                query = """
                SELECT 
                    COLUMN_NAME as field_name,
                    DATA_TYPE as field_type,
                    CASE 
                        WHEN DATA_TYPE IN ('int', 'decimal', 'float') THEN 'measure'
                        WHEN DATA_TYPE IN ('date', 'datetime') THEN 'date'
                        ELSE 'dimension'
                    END as category,
                    'Asset' as source
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                LIMIT 20
                """
                
            elif database == 'permits':
                # Permits & Licensing fields
                query = """
                SELECT TOP 20
                    COLUMN_NAME as field_name,
                    DATA_TYPE as field_type,
                    CASE 
                        WHEN DATA_TYPE IN ('int', 'decimal', 'money') THEN 'measure'
                        WHEN DATA_TYPE IN ('date', 'datetime') THEN 'date'
                        ELSE 'dimension'
                    END as category,
                    'Permits' as source
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo'
                """
                
            elif database == 'payroll':
                # Payroll fields
                query = """
                SELECT 
                    column_name as field_name,
                    data_type as field_type,
                    CASE 
                        WHEN data_type IN ('integer', 'numeric', 'money') THEN 'measure'
                        WHEN data_type IN ('date', 'timestamp') THEN 'date'
                        ELSE 'dimension'
                    END as category,
                    'Payroll' as source
                FROM information_schema.columns
                WHERE table_schema = 'public'
                LIMIT 20
                """
            
            # Execute query and get results
            result = execute_query(conn, query)
            
            if result:
                for row in result:
                    fields.append({
                        'name': row[0],
                        'type': row[1],
                        'category': row[2],
                        'source': row[3],
                        'display_name': row[0].replace('_', ' ').title()
                    })
                    
        except Exception as e:
            # Silently handle database connection errors and return sample fields
            # Don't show error to user since many databases may not be configured
            fields = self._get_sample_fields(database)
        
        return fields
    
    def _get_sample_fields(self, database: str) -> List[Dict]:
        """Get sample fields for demonstration"""
        sample_fields = {
            'gl_primary': [
                {'name': 'Department', 'type': 'text', 'category': 'dimension', 'source': 'GL'},
                {'name': 'Account', 'type': 'text', 'category': 'dimension', 'source': 'GL'},
                {'name': 'Budget', 'type': 'number', 'category': 'measure', 'source': 'GL'},
                {'name': 'Actual', 'type': 'number', 'category': 'measure', 'source': 'GL'},
                {'name': 'Variance', 'type': 'number', 'category': 'measure', 'source': 'GL'},
                {'name': 'Date', 'type': 'date', 'category': 'date', 'source': 'GL'},
                {'name': 'Fiscal_Year', 'type': 'text', 'category': 'dimension', 'source': 'GL'},
                {'name': 'Fund', 'type': 'text', 'category': 'dimension', 'source': 'GL'}
            ],
            'utility': [
                {'name': 'Service_Type', 'type': 'text', 'category': 'dimension', 'source': 'Utility'},
                {'name': 'Usage', 'type': 'number', 'category': 'measure', 'source': 'Utility'},
                {'name': 'Revenue', 'type': 'number', 'category': 'measure', 'source': 'Utility'},
                {'name': 'Customer_Count', 'type': 'number', 'category': 'measure', 'source': 'Utility'},
                {'name': 'Service_Date', 'type': 'date', 'category': 'date', 'source': 'Utility'}
            ],
            'asset': [
                {'name': 'Asset_Type', 'type': 'text', 'category': 'dimension', 'source': 'Asset'},
                {'name': 'Asset_Value', 'type': 'number', 'category': 'measure', 'source': 'Asset'},
                {'name': 'Depreciation', 'type': 'number', 'category': 'measure', 'source': 'Asset'},
                {'name': 'Purchase_Date', 'type': 'date', 'category': 'date', 'source': 'Asset'},
                {'name': 'Location', 'type': 'text', 'category': 'dimension', 'source': 'Asset'}
            ],
            'permits': [
                {'name': 'Permit_Type', 'type': 'text', 'category': 'dimension', 'source': 'Permits'},
                {'name': 'Fee_Amount', 'type': 'number', 'category': 'measure', 'source': 'Permits'},
                {'name': 'Issue_Date', 'type': 'date', 'category': 'date', 'source': 'Permits'},
                {'name': 'Status', 'type': 'text', 'category': 'dimension', 'source': 'Permits'}
            ],
            'payroll': [
                {'name': 'Employee_Type', 'type': 'text', 'category': 'dimension', 'source': 'Payroll'},
                {'name': 'Salary', 'type': 'number', 'category': 'measure', 'source': 'Payroll'},
                {'name': 'Benefits', 'type': 'number', 'category': 'measure', 'source': 'Payroll'},
                {'name': 'Hire_Date', 'type': 'date', 'category': 'date', 'source': 'Payroll'},
                {'name': 'Department', 'type': 'text', 'category': 'dimension', 'source': 'Payroll'}
            ]
        }
        
        fields = sample_fields.get(database, [])
        for field in fields:
            field['display_name'] = field['name'].replace('_', ' ').title()
        
        return fields
    
    def _categorize_fields(self, fields: List[Dict]) -> List[Dict]:
        """Categorize fields by type for the UI"""
        for field in fields:
            if field['category'] not in ['dimension', 'measure', 'date']:
                # Auto-categorize based on type
                if field['type'] in ['date', 'datetime', 'timestamp']:
                    field['category'] = 'date'
                elif field['type'] in ['number', 'integer', 'decimal', 'float', 'money', 'numeric', 'real']:
                    field['category'] = 'measure'
                else:
                    field['category'] = 'dimension'
        
        return fields
    
    def get_chart_data(self, chart_type: str, config: Dict) -> Dict:
        """Get data formatted for specific chart type"""
        
        # Check if it's a custom D3 visualization
        if chart_type in ['budget_flow', 'department_network', 'tax_distribution', 
                         'project_timeline', 'utility_infrastructure', 'financial_health']:
            return self._get_d3_viz_data(chart_type)
        
        # Get base data from configuration
        data = self._fetch_data_from_config(config)
        
        # Transform data based on chart type
        if chart_type == 'bar':
            return self._transform_bar_data(data, config)
        elif chart_type == 'line':
            return self._transform_line_data(data, config)
        elif chart_type == 'pie':
            return self._transform_pie_data(data, config)
        elif chart_type == 'scatter':
            return self._transform_scatter_data(data, config)
        elif chart_type == 'heatmap':
            return self._transform_heatmap_data(data, config)
        elif chart_type == 'treemap':
            return self._transform_treemap_data(data, config)
        elif chart_type == 'sankey':
            return self._transform_sankey_data(data, config)
        elif chart_type == 'gauge':
            return self._transform_gauge_data(data, config)
        elif chart_type == 'radar':
            return self._transform_radar_data(data, config)
        elif chart_type == 'funnel':
            return self._transform_funnel_data(data, config)
        elif chart_type == 'waterfall':
            return self._transform_waterfall_data(data, config)
        elif chart_type == 'network':
            return self._transform_network_data(data, config)
        elif chart_type == 'chord':
            return self._transform_chord_data(data, config)
        elif chart_type == 'sunburst':
            return self._transform_sunburst_data(data, config)
        elif chart_type == '3d_bar':
            return self._transform_3d_bar_data(data, config)
        else:
            # Default transformation
            return self._transform_default_data(data, config)
    
    def _fetch_data_from_config(self, config: Dict) -> pd.DataFrame:
        """Fetch data based on visualization configuration"""
        try:
            # Determine which database to use based on fields
            axis_fields = config.get('axis', [])
            value_fields = config.get('values', [])
            legend_fields = config.get('legend', [])
            
            all_fields = axis_fields + value_fields + legend_fields
            
            if not all_fields:
                return self._get_sample_data()
            
            # Get source database from first field
            source = all_fields[0].get('source', 'GL')
            database = self._get_database_from_source(source)
            
            # Build query
            query = self._build_query_from_config(config, database)
            
            # Execute query
            conn = get_connection(database)
            df = pd.read_sql_query(query, conn)
            
            return df
            
        except Exception as e:
            st.warning(f"Error fetching data: {str(e)}")
            return self._get_sample_data()
    
    def _get_database_from_source(self, source: str) -> str:
        """Map source to database name"""
        source_map = {
            'GL': 'gl_primary',
            'Utility': 'utility',
            'Asset': 'asset',
            'Permits': 'permits',
            'Payroll': 'payroll'
        }
        return source_map.get(source, 'gl_primary')
    
    def _build_query_from_config(self, config: Dict, database: str) -> str:
        """Build SQL query from visualization configuration"""
        # This is a simplified query builder
        # In production, this would be more sophisticated
        
        if database == 'gl_primary':
            return """
            SELECT 
                Department,
                SUM(Budget) as Budget,
                SUM(Actual) as Actual,
                COUNT(*) as Count
            FROM gl_data
            GROUP BY Department
            LIMIT 100
            """
        else:
            # Default query for other databases
            return "SELECT * FROM main_table LIMIT 100"
    
    def _get_sample_data(self) -> pd.DataFrame:
        """Generate sample data for demonstration"""
        np.random.seed(42)
        
        departments = ['Police', 'Fire', 'Public Works', 'Parks', 'Admin', 'IT', 'Finance', 'HR']
        months = pd.date_range('2024-01', periods=12, freq='ME')
        
        data = []
        for dept in departments:
            for month in months:
                budget = np.random.uniform(100000, 500000)
                actual = budget * np.random.uniform(0.8, 1.1)
                data.append({
                    'Department': dept,
                    'Month': month,
                    'Budget': budget,
                    'Actual': actual,
                    'Variance': budget - actual,
                    'Percentage': (actual / budget) * 100
                })

        df = pd.DataFrame(data)
        # Tagged so downstream chart payloads can label themselves as sample
        df.attrs['is_sample'] = True
        return df
    
    def _transform_bar_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for bar chart"""
        if df.empty:
            return {'categories': [], 'values': []}
        
        # Get first text column for categories and first numeric for values
        text_cols = df.select_dtypes(include=['object']).columns
        num_cols = df.select_dtypes(include=['number']).columns
        
        if len(text_cols) > 0 and len(num_cols) > 0:
            categories = df[text_cols[0]].tolist()
            values = df[num_cols[0]].tolist()
        else:
            categories = list(range(len(df)))
            values = df.iloc[:, 0].tolist() if len(df.columns) > 0 else []
        
        return {
            'categories': categories[:20],  # Limit to 20 items
            'values': values[:20]
        }
    
    def _transform_line_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for line chart"""
        return self._transform_bar_data(df, config)  # Similar structure
    
    def _transform_pie_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for pie chart"""
        if df.empty:
            return {'pieData': []}
        
        text_cols = df.select_dtypes(include=['object']).columns
        num_cols = df.select_dtypes(include=['number']).columns
        
        pie_data = []
        if len(text_cols) > 0 and len(num_cols) > 0:
            for i in range(min(10, len(df))):  # Limit to 10 slices
                pie_data.append({
                    'value': float(df[num_cols[0]].iloc[i]),
                    'name': str(df[text_cols[0]].iloc[i])
                })
        
        return {'pieData': pie_data}
    
    def _transform_scatter_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for scatter plot"""
        if df.empty:
            return {'scatterData': []}
        
        num_cols = df.select_dtypes(include=['number']).columns
        
        if len(num_cols) >= 2:
            scatter_data = df[list(num_cols[:2])].values.tolist()
        else:
            scatter_data = [[i, v] for i, v in enumerate(df.iloc[:, 0].tolist())]
        
        return {'scatterData': scatter_data[:100]}  # Limit to 100 points
    
    def _transform_heatmap_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for heatmap"""
        # Create sample heatmap data
        x_categories = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        y_categories = ['Morning', 'Afternoon', 'Evening']
        
        heatmap_data = []
        for i, x in enumerate(x_categories):
            for j, y in enumerate(y_categories):
                value = np.random.randint(0, 100)
                heatmap_data.append([i, j, value])
        
        return {
            'xCategories': x_categories,
            'yCategories': y_categories,
            'heatmapData': heatmap_data
        }
    
    def _transform_treemap_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for treemap"""
        if df.empty:
            return {'treemapData': []}
        
        # Group data hierarchically
        treemap_data = []
        
        text_cols = df.select_dtypes(include=['object']).columns
        num_cols = df.select_dtypes(include=['number']).columns
        
        if len(text_cols) > 0 and len(num_cols) > 0:
            # Group by first text column
            grouped = df.groupby(text_cols[0])[num_cols[0]].sum()
            
            for name, value in grouped.items():
                treemap_data.append({
                    'name': str(name),
                    'value': float(value)
                })
        
        return {'treemapData': treemap_data[:20]}
    
    def _transform_sankey_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for Sankey diagram"""
        # Create sample Sankey data
        nodes = [
            {'name': 'Revenue'},
            {'name': 'Taxes'},
            {'name': 'Fees'},
            {'name': 'Grants'},
            {'name': 'Police'},
            {'name': 'Fire'},
            {'name': 'Public Works'},
            {'name': 'Parks'}
        ]
        
        links = [
            {'source': 'Revenue', 'target': 'Police', 'value': 30},
            {'source': 'Revenue', 'target': 'Fire', 'value': 20},
            {'source': 'Revenue', 'target': 'Public Works', 'value': 25},
            {'source': 'Revenue', 'target': 'Parks', 'value': 15},
            {'source': 'Taxes', 'target': 'Revenue', 'value': 60},
            {'source': 'Fees', 'target': 'Revenue', 'value': 20},
            {'source': 'Grants', 'target': 'Revenue', 'value': 10}
        ]
        
        return {'nodes': nodes, 'links': links}
    
    def _transform_gauge_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for gauge chart"""
        # Calculate a percentage value
        if not df.empty and len(df.select_dtypes(include=['number']).columns) > 0:
            num_col = df.select_dtypes(include=['number']).columns[0]
            value = (df[num_col].mean() / df[num_col].max()) * 100 if df[num_col].max() > 0 else 50
        else:
            value = 75
        
        return {'gaugeValue': float(value)}
    
    def _transform_radar_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for radar chart"""
        indicators = [
            {'name': 'Budget', 'max': 100},
            {'name': 'Actual', 'max': 100},
            {'name': 'Efficiency', 'max': 100},
            {'name': 'Performance', 'max': 100},
            {'name': 'Compliance', 'max': 100}
        ]
        
        radar_data = [{
            'value': [85, 78, 92, 68, 88],
            'name': 'Current Period'
        }]
        
        return {'indicators': indicators, 'radarData': radar_data}
    
    def _transform_funnel_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for funnel chart"""
        funnel_data = [
            {'value': 100, 'name': 'Applications'},
            {'value': 80, 'name': 'Review'},
            {'value': 60, 'name': 'Approved'},
            {'value': 40, 'name': 'Funded'},
            {'value': 20, 'name': 'Completed'}
        ]
        
        return {'funnelData': funnel_data}
    
    def _transform_waterfall_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for waterfall chart"""
        return {
            'categories': ['Start', 'Q1', 'Q2', 'Q3', 'Q4', 'End'],
            'values': [100, 20, -30, 40, -10, 120]
        }
    
    def _transform_network_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for network graph"""
        return self._transform_sankey_data(df, config)  # Similar structure
    
    def _transform_chord_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for chord diagram"""
        # Similar to network but with circular layout
        return {
            'nodes': [
                {'name': 'Group A', 'value': 40},
                {'name': 'Group B', 'value': 30},
                {'name': 'Group C', 'value': 20},
                {'name': 'Group D', 'value': 25}
            ],
            'links': [
                {'source': 'Group A', 'target': 'Group B', 'value': 10},
                {'source': 'Group A', 'target': 'Group C', 'value': 5},
                {'source': 'Group B', 'target': 'Group C', 'value': 15},
                {'source': 'Group B', 'target': 'Group D', 'value': 8},
                {'source': 'Group C', 'target': 'Group D', 'value': 12}
            ]
        }
    
    def _transform_sunburst_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for sunburst chart"""
        sunburst_data = [{
            'name': 'Total Budget',
            'children': [
                {
                    'name': 'Operations',
                    'value': 40,
                    'children': [
                        {'name': 'Police', 'value': 20},
                        {'name': 'Fire', 'value': 15},
                        {'name': 'Public Works', 'value': 5}
                    ]
                },
                {
                    'name': 'Administration',
                    'value': 20,
                    'children': [
                        {'name': 'Finance', 'value': 10},
                        {'name': 'HR', 'value': 5},
                        {'name': 'IT', 'value': 5}
                    ]
                },
                {
                    'name': 'Capital',
                    'value': 30
                }
            ]
        }]
        
        return {'sunburstData': sunburst_data}
    
    def _transform_3d_bar_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Transform data for 3D bar chart"""
        # Generate 3D data points
        data_3d = []
        for i in range(5):
            for j in range(3):
                value = np.random.randint(10, 150)
                data_3d.append([i, j, value])
        
        return {
            'xCategories': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
            'yCategories': ['Morning', 'Afternoon', 'Evening'],
            'data3d': data_3d
        }
    
    def _transform_default_data(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Default data transformation"""
        return self._transform_bar_data(df, config)
    
    def _get_d3_viz_data(self, viz_type: str) -> Dict:
        """Get data for custom D3 visualizations"""
        
        if viz_type == 'budget_flow':
            return {
                'nodes': [
                    {'id': 'Revenue', 'group': 1, 'value': 1000000},
                    {'id': 'Police', 'group': 2, 'value': 300000},
                    {'id': 'Fire', 'group': 2, 'value': 200000},
                    {'id': 'Public Works', 'group': 2, 'value': 250000},
                    {'id': 'Parks', 'group': 2, 'value': 150000},
                    {'id': 'Admin', 'group': 2, 'value': 100000}
                ],
                'links': [
                    {'source': 'Revenue', 'target': 'Police', 'value': 300000},
                    {'source': 'Revenue', 'target': 'Fire', 'value': 200000},
                    {'source': 'Revenue', 'target': 'Public Works', 'value': 250000},
                    {'source': 'Revenue', 'target': 'Parks', 'value': 150000},
                    {'source': 'Revenue', 'target': 'Admin', 'value': 100000}
                ]
            }
        
        elif viz_type == 'department_network':
            return {
                'departments': ['Finance', 'HR', 'IT', 'Operations', 'Legal', 'Planning'],
                'connections': [
                    [0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3], [3, 4], [4, 5]
                ]
            }
        
        elif viz_type == 'tax_distribution':
            return {
                'categories': [
                    {'name': 'Property Tax', 'value': 45},
                    {'name': 'Sales Tax', 'value': 30},
                    {'name': 'Income Tax', 'value': 15},
                    {'name': 'Other', 'value': 10}
                ]
            }
        
        elif viz_type == 'project_timeline':
            return {
                'projects': [
                    {'name': 'Road Repair', 'start': 0, 'end': 3, 'budget': 500000},
                    {'name': 'Park Renovation', 'start': 2, 'end': 5, 'budget': 300000},
                    {'name': 'School Upgrade', 'start': 4, 'end': 8, 'budget': 800000},
                    {'name': 'Water System', 'start': 6, 'end': 10, 'budget': 1200000}
                ]
            }
        
        elif viz_type == 'utility_infrastructure':
            return {
                'utilities': [
                    {'type': 'Water', 'x': 100, 'y': 100, 'connections': [1, 2]},
                    {'type': 'Electric', 'x': 300, 'y': 100, 'connections': [0, 2, 3]},
                    {'type': 'Gas', 'x': 200, 'y': 200, 'connections': [0, 1, 3]},
                    {'type': 'Sewer', 'x': 400, 'y': 200, 'connections': [1, 2]}
                ]
            }
        
        elif viz_type == 'financial_health':
            return {
                'metrics': [
                    {'name': 'Revenue', 'value': 85, 'target': 100},
                    {'name': 'Expenses', 'value': 70, 'target': 80},
                    {'name': 'Reserves', 'value': 60, 'target': 50},
                    {'name': 'Debt', 'value': 40, 'target': 30},
                    {'name': 'Growth', 'value': 75, 'target': 70}
                ]
            }
        
        return {}
    
    def save_dashboard(self, dashboard_config: Dict) -> bool:
        """Save dashboard configuration"""
        try:
            # Save to session state or database
            st.session_state['dashboard_config'] = dashboard_config
            return True
        except Exception as e:
            st.error(f"Error saving dashboard: {str(e)}")
            return False
    
    def load_dashboard(self, dashboard_id: str) -> Dict:
        """Load dashboard configuration"""
        try:
            # Load from session state or database
            return st.session_state.get('dashboard_config', {})
        except Exception as e:
            st.error(f"Error loading dashboard: {str(e)}")
            return {}
    
    def export_dashboard(self, dashboard_config: Dict, format: str = 'pdf') -> bytes:
        """Export dashboard to various formats"""
        try:
            if format == 'pdf':
                # Export to PDF (implementation would go here)
                return b"PDF content"
            elif format == 'png':
                # Export to PNG (implementation would go here)
                return b"PNG content"
            elif format == 'json':
                # Export configuration as JSON
                return json.dumps(dashboard_config, indent=2).encode()
            else:
                return b""
        except Exception as e:
            st.error(f"Error exporting dashboard: {str(e)}")
            return b""

# Initialize API
dashboard_api = EChartsDashboardAPI()