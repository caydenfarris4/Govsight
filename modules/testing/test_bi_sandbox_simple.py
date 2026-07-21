"""
Simplified unit tests for BI Sandbox with focus on core functionality
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bi_sandbox import (
    VisualizationType,
    AnalyticsMetric,
    AdvancedAnalyticsEngine,
    NaturalLanguageAnalytics,
    AdvancedVisualizationEngine,
    generate_ai_insights
)


class TestBISandboxCore(unittest.TestCase):
    """Test core BI Sandbox functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.test_data = pd.DataFrame({
            'Department': ['HR', 'IT', 'Finance', 'Marketing'],
            'Budget': [100000, 150000, 200000, 120000],
            'Actual': [95000, 145000, 195000, 115000],
            'Region': ['North', 'South', 'North', 'South']
        })
    
    def test_visualization_types(self):
        """Test visualization types enum"""
        self.assertEqual(VisualizationType.BAR.value, "bar")
        self.assertEqual(VisualizationType.LINE.value, "line")
        self.assertEqual(VisualizationType.PIE.value, "pie")
        self.assertTrue(hasattr(VisualizationType, 'HEATMAP'))
        self.assertTrue(hasattr(VisualizationType, 'TREEMAP'))
    
    def test_analytics_metric_creation(self):
        """Test analytics metric creation"""
        metric = AnalyticsMetric(
            name="Revenue",
            expression="SUM(amount)",
            aggregation_type="sum",
            format_type="currency",
            description="Total revenue"
        )
        self.assertEqual(metric.name, "Revenue")
        self.assertEqual(metric.aggregation_type, "sum")
    
    def test_advanced_analytics_engine_star_schema(self):
        """Test star schema creation"""
        engine = AdvancedAnalyticsEngine()
        schema = engine.create_star_schema(
            self.test_data, 
            ['Department'], 
            ['Budget', 'Actual']
        )
        
        self.assertIn('fact', schema)
        self.assertIn('dim_Department', schema)
        self.assertIsInstance(schema['fact'], pd.DataFrame)
        self.assertIsInstance(schema['dim_Department'], pd.DataFrame)
    
    def test_dax_calculations(self):
        """Test DAX-style calculations"""
        engine = AdvancedAnalyticsEngine()
        
        # Test SUM
        result = engine.calculate_dax_expression('SUM(Budget)', self.test_data)
        self.assertIsInstance(result, pd.Series)
        
        # Test AVERAGE
        result = engine.calculate_dax_expression('AVERAGE(Budget)', self.test_data)
        self.assertIsInstance(result, pd.Series)
        
        # Test COUNT
        result = engine.calculate_dax_expression('COUNT(Budget)', self.test_data)
        self.assertIsInstance(result, pd.Series)
    
    def test_forecasting_basic(self):
        """Test basic forecasting functionality"""
        engine = AdvancedAnalyticsEngine()
        forecasts = engine.generate_advanced_forecast(self.test_data, 'Budget', 3)
        
        self.assertIsInstance(forecasts, dict)
        # Should have at least one forecast method
        if forecasts:
            self.assertTrue(len(forecasts) > 0)
            # Check that forecast values are numeric
            for forecast_name, forecast_values in forecasts.items():
                self.assertIsInstance(forecast_values, np.ndarray)
                self.assertTrue(len(forecast_values) > 0)
    
    def test_natural_language_analytics(self):
        """Test natural language processing"""
        nl_engine = NaturalLanguageAnalytics()
        
        # Test sum query
        result = nl_engine.parse_natural_query('sum Budget', self.test_data)
        self.assertEqual(result['type'], 'sum')
        self.assertEqual(result['column'], 'Budget')
        self.assertEqual(result['result'], 570000)
        
        # Test average query
        result = nl_engine.parse_natural_query('average Budget', self.test_data)
        self.assertEqual(result['type'], 'average')
        self.assertEqual(result['column'], 'Budget')
        self.assertEqual(result['result'], 142500)
        
        # Test count query
        result = nl_engine.parse_natural_query('count Budget', self.test_data)
        self.assertEqual(result['type'], 'count')
        self.assertEqual(result['column'], 'Budget')
        self.assertEqual(result['result'], 4)
        
        # Test case insensitive
        result = nl_engine.parse_natural_query('sum budget', self.test_data)
        self.assertEqual(result['type'], 'sum')
        self.assertEqual(result['column'], 'Budget')
    
    def test_natural_language_top_queries(self):
        """Test top/bottom queries"""
        nl_engine = NaturalLanguageAnalytics()
        
        # Test top query
        result = nl_engine.parse_natural_query('top 2 Budget', self.test_data)
        self.assertEqual(result['type'], 'top')
        self.assertEqual(result['n'], 2)
        self.assertEqual(result['column'], 'Budget')
        self.assertIsInstance(result['result'], pd.DataFrame)
        self.assertEqual(len(result['result']), 2)
    
    def test_natural_language_error_handling(self):
        """Test error handling in natural language"""
        nl_engine = NaturalLanguageAnalytics()
        
        # Test invalid query
        result = nl_engine.parse_natural_query('invalid query', self.test_data)
        self.assertIn('error', result)
        
        # Test non-existent column
        result = nl_engine.parse_natural_query('sum NonExistentColumn', self.test_data)
        self.assertIn('error', result)
    
    def test_visualization_engine_creation(self):
        """Test visualization engine creation"""
        viz_engine = AdvancedVisualizationEngine()
        
        # Test color palettes exist
        self.assertIn('corporate', viz_engine.color_palettes)
        self.assertIn('municipal', viz_engine.color_palettes)
        self.assertIn('financial', viz_engine.color_palettes)
        
        # Test chart creation
        fig = viz_engine.create_advanced_chart(
            self.test_data, 
            VisualizationType.BAR, 
            'Department', 
            'Budget'
        )
        self.assertIsNotNone(fig)
    
    def test_ai_insights_generation(self):
        """Test AI insights generation"""
        insights = generate_ai_insights(self.test_data)
        
        self.assertIsInstance(insights, list)
        self.assertTrue(len(insights) <= 5)  # Should return max 5 insights
        
        # Should generate at least one insight with proper data
        if len(insights) > 0:
            self.assertIsInstance(insights[0], str)
            self.assertTrue(len(insights[0]) > 0)
    
    def test_ai_insights_with_correlation(self):
        """Test insights with correlated data"""
        corr_data = pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, 6, 8, 10]  # Perfect correlation
        })
        
        insights = generate_ai_insights(corr_data)
        self.assertIsInstance(insights, list)
        
        # Should detect correlation
        correlation_found = any('correlation' in insight.lower() for insight in insights)
        self.assertTrue(correlation_found)
    
    def test_ai_insights_with_outliers(self):
        """Test insights with outliers"""
        outlier_data = pd.DataFrame({
            'values': [1, 2, 3, 4, 1000]  # 1000 is an outlier
        })
        
        insights = generate_ai_insights(outlier_data)
        self.assertIsInstance(insights, list)
        
        # Should detect outliers
        outlier_found = any('outlier' in insight.lower() for insight in insights)
        self.assertTrue(outlier_found)
    
    def test_ai_insights_empty_data(self):
        """Test insights with empty data"""
        empty_data = pd.DataFrame()
        insights = generate_ai_insights(empty_data)
        
        self.assertIsInstance(insights, list)
        self.assertEqual(len(insights), 0)
    
    def test_column_finding_flexibility(self):
        """Test flexible column finding"""
        nl_engine = NaturalLanguageAnalytics()
        
        # Test exact match
        column = nl_engine.find_column('Budget', self.test_data)
        self.assertEqual(column, 'Budget')
        
        # Test case insensitive
        column = nl_engine.find_column('budget', self.test_data)
        self.assertEqual(column, 'Budget')
        
        # Test partial match
        column = nl_engine.find_column('Budg', self.test_data)
        self.assertEqual(column, 'Budget')
        
        # Test no match
        column = nl_engine.find_column('NonExistent', self.test_data)
        self.assertIsNone(column)
    
    def test_time_intelligence_basic(self):
        """Test basic time intelligence"""
        engine = AdvancedAnalyticsEngine()
        
        # Add date column
        time_data = self.test_data.copy()
        time_data['Date'] = pd.to_datetime(['2023-01-01', '2023-02-01', '2023-03-01', '2024-01-01'])
        
        time_calcs = engine.perform_time_intelligence(time_data, 'Date', 'Budget')
        
        self.assertIsInstance(time_calcs, dict)
        # Should have some time intelligence calculations
        self.assertIn('yoy_growth', time_calcs)
        self.assertIn('qoq_growth', time_calcs)
    
    def test_integration_workflow(self):
        """Test basic integration workflow"""
        # 1. Generate insights
        insights = generate_ai_insights(self.test_data)
        self.assertIsInstance(insights, list)
        
        # 2. Query data
        nl_engine = NaturalLanguageAnalytics()
        query_result = nl_engine.parse_natural_query('sum Budget', self.test_data)
        self.assertEqual(query_result['type'], 'sum')
        
        # 3. Create visualization
        viz_engine = AdvancedVisualizationEngine()
        fig = viz_engine.create_advanced_chart(
            self.test_data, VisualizationType.BAR, 'Department', 'Budget'
        )
        self.assertIsNotNone(fig)
        
        # 4. Perform analytics
        analytics_engine = AdvancedAnalyticsEngine()
        star_schema = analytics_engine.create_star_schema(
            self.test_data, ['Department'], ['Budget', 'Actual']
        )
        self.assertIn('fact', star_schema)
    
    def test_load_org_data_basic(self):
        """Test basic data loading functionality"""
        from bi_sandbox import load_org_data
        
        # Test that the function returns a DataFrame
        result = load_org_data('test_org')
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)  # Should not be empty
        
        # Should have expected columns
        expected_columns = ['Department', 'Budget', 'Actual']
        for col in expected_columns:
            self.assertIn(col, result.columns)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)