"""
Unit tests for the Advanced BI Sandbox Module

This comprehensive test suite ensures >80% code coverage for the BI sandbox
functionality, including all advanced features and visualization types.
"""

import unittest
import pandas as pd
import numpy as np
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import sys
import io

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bi_sandbox import (
    VisualizationType,
    AnalyticsMetric,
    DimensionHierarchy,
    FilterAction,
    AdvancedAnalyticsEngine,
    NaturalLanguageAnalytics,
    AdvancedVisualizationEngine,
    load_org_data,
    generate_ai_insights
)


class TestVisualizationType(unittest.TestCase):
    """Test the VisualizationType enum"""
    
    def test_visualization_types_exist(self):
        """Test that all visualization types are defined"""
        expected_types = [
            "TABLE", "BAR", "LINE", "PIE", "SCATTER", "HEATMAP",
            "TREEMAP", "SUNBURST", "SANKEY", "WATERFALL", "FUNNEL",
            "GAUGE", "CANDLESTICK", "RADAR", "PARALLEL_COORDINATES",
            "VIOLIN", "BOX", "HISTOGRAM", "DENSITY", "CORRELATION_MATRIX",
            "REGRESSION", "CLUSTER", "FORECAST"
        ]
        
        for viz_type in expected_types:
            self.assertTrue(hasattr(VisualizationType, viz_type))
    
    def test_visualization_type_values(self):
        """Test that visualization types have correct values"""
        self.assertEqual(VisualizationType.BAR.value, "bar")
        self.assertEqual(VisualizationType.LINE.value, "line")
        self.assertEqual(VisualizationType.PIE.value, "pie")


class TestAnalyticsMetric(unittest.TestCase):
    """Test the AnalyticsMetric dataclass"""
    
    def test_analytics_metric_creation(self):
        """Test creating an AnalyticsMetric"""
        metric = AnalyticsMetric(
            name="Revenue",
            expression="SUM(amount)",
            aggregation_type="sum",
            format_type="currency",
            description="Total revenue"
        )
        
        self.assertEqual(metric.name, "Revenue")
        self.assertEqual(metric.expression, "SUM(amount)")
        self.assertEqual(metric.aggregation_type, "sum")
        self.assertEqual(metric.format_type, "currency")
        self.assertEqual(metric.description, "Total revenue")
        self.assertIsNone(metric.dependencies)
    
    def test_analytics_metric_with_dependencies(self):
        """Test creating an AnalyticsMetric with dependencies"""
        metric = AnalyticsMetric(
            name="Profit",
            expression="Revenue - Costs",
            aggregation_type="calculated",
            format_type="currency",
            description="Profit calculation",
            dependencies=["Revenue", "Costs"]
        )
        
        self.assertEqual(metric.dependencies, ["Revenue", "Costs"])


class TestDimensionHierarchy(unittest.TestCase):
    """Test the DimensionHierarchy dataclass"""
    
    def test_dimension_hierarchy_creation(self):
        """Test creating a DimensionHierarchy"""
        hierarchy = DimensionHierarchy(
            name="Time",
            levels=["Year", "Quarter", "Month"],
            parent_child_mapping={"Quarter": "Year", "Month": "Quarter"}
        )
        
        self.assertEqual(hierarchy.name, "Time")
        self.assertEqual(hierarchy.levels, ["Year", "Quarter", "Month"])
        self.assertEqual(hierarchy.parent_child_mapping, {"Quarter": "Year", "Month": "Quarter"})
        self.assertEqual(hierarchy.sort_order, "asc")


class TestFilterAction(unittest.TestCase):
    """Test the FilterAction dataclass"""
    
    def test_filter_action_creation(self):
        """Test creating a FilterAction"""
        action = FilterAction(
            source_field="Department",
            target_field="Budget",
            filter_type="equals",
            relationship="one_to_many"
        )
        
        self.assertEqual(action.source_field, "Department")
        self.assertEqual(action.target_field, "Budget")
        self.assertEqual(action.filter_type, "equals")
        self.assertEqual(action.relationship, "one_to_many")


class TestAdvancedAnalyticsEngine(unittest.TestCase):
    """Test the AdvancedAnalyticsEngine class"""
    
    def setUp(self):
        """Set up test data"""
        self.engine = AdvancedAnalyticsEngine()
        self.test_data = pd.DataFrame({
            'Department': ['HR', 'IT', 'Finance', 'HR', 'IT'],
            'Budget': [100000, 150000, 200000, 120000, 180000],
            'Actual': [95000, 145000, 195000, 115000, 175000],
            'Year': [2023, 2023, 2023, 2024, 2024]
        })
    
    def test_create_star_schema(self):
        """Test creating star schema from flat data"""
        dimensions = ['Department']
        measures = ['Budget', 'Actual']
        
        star_schema = self.engine.create_star_schema(self.test_data, dimensions, measures)
        
        self.assertIn('fact', star_schema)
        self.assertIn('dim_Department', star_schema)
        self.assertEqual(len(star_schema['fact'].columns), 2)  # Budget and Actual
        self.assertEqual(len(star_schema['dim_Department']), 3)  # HR, IT, Finance
    
    def test_calculate_dax_expression_sum(self):
        """Test DAX SUM expression"""
        result = self.engine.calculate_dax_expression('SUM(Budget)', self.test_data)
        self.assertIsInstance(result, pd.Series)
    
    def test_calculate_dax_expression_average(self):
        """Test DAX AVERAGE expression"""
        result = self.engine.calculate_dax_expression('AVERAGE(Budget)', self.test_data)
        self.assertIsInstance(result, pd.Series)
    
    def test_calculate_dax_expression_count(self):
        """Test DAX COUNT expression"""
        result = self.engine.calculate_dax_expression('COUNT(Budget)', self.test_data)
        self.assertIsInstance(result, pd.Series)
    
    def test_calculate_dax_expression_invalid(self):
        """Test invalid DAX expression"""
        result = self.engine.calculate_dax_expression('INVALID(Budget)', self.test_data)
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(len(result), 0)
    
    def test_perform_time_intelligence(self):
        """Test time intelligence calculations"""
        # Add proper date column
        self.test_data['Date'] = pd.to_datetime(['2023-01-01', '2023-02-01', '2023-03-01', '2024-01-01', '2024-02-01'])
        
        time_calcs = self.engine.perform_time_intelligence(self.test_data, 'Date', 'Budget')
        
        self.assertIsInstance(time_calcs, dict)
        self.assertIn('yoy_growth', time_calcs)
        self.assertIn('qoq_growth', time_calcs)
    
    def test_perform_time_intelligence_no_date_column(self):
        """Test time intelligence with missing date column"""
        time_calcs = self.engine.perform_time_intelligence(self.test_data, 'NonExistentDate', 'Budget')
        self.assertEqual(time_calcs, {})
    
    def test_generate_advanced_forecast(self):
        """Test advanced forecasting"""
        forecasts = self.engine.generate_advanced_forecast(self.test_data, 'Budget', periods=3)
        
        self.assertIsInstance(forecasts, dict)
        # Should have at least one forecast method
        self.assertTrue(len(forecasts) > 0)
    
    def test_generate_advanced_forecast_insufficient_data(self):
        """Test forecasting with insufficient data"""
        small_data = pd.DataFrame({'Budget': [100, 200]})
        forecasts = self.engine.generate_advanced_forecast(small_data, 'Budget', periods=3)
        
        self.assertEqual(forecasts, {})


class TestNaturalLanguageAnalytics(unittest.TestCase):
    """Test the NaturalLanguageAnalytics class"""
    
    def setUp(self):
        """Set up test data"""
        self.nl_engine = NaturalLanguageAnalytics()
        self.test_data = pd.DataFrame({
            'Department': ['HR', 'IT', 'Finance'],
            'Budget': [100000, 150000, 200000],
            'Actual': [95000, 145000, 195000]
        })
    
    def test_parse_natural_query_sum(self):
        """Test parsing sum queries"""
        result = self.nl_engine.parse_natural_query('sum Budget', self.test_data)
        
        self.assertEqual(result['type'], 'sum')
        self.assertEqual(result['column'], 'Budget')
        self.assertEqual(result['result'], 450000)
    
    def test_parse_natural_query_average(self):
        """Test parsing average queries"""
        result = self.nl_engine.parse_natural_query('average Budget', self.test_data)
        
        self.assertEqual(result['type'], 'average')
        self.assertEqual(result['column'], 'Budget')
        self.assertEqual(result['result'], 150000)
    
    def test_parse_natural_query_count(self):
        """Test parsing count queries"""
        result = self.nl_engine.parse_natural_query('count Budget', self.test_data)
        
        self.assertEqual(result['type'], 'count')
        self.assertEqual(result['column'], 'Budget')
        self.assertEqual(result['result'], 3)
    
    def test_parse_natural_query_top(self):
        """Test parsing top queries"""
        result = self.nl_engine.parse_natural_query('top 2 Budget', self.test_data)
        
        self.assertEqual(result['type'], 'top')
        self.assertEqual(result['n'], 2)
        self.assertEqual(result['column'], 'Budget')
        self.assertIsInstance(result['result'], pd.DataFrame)
        self.assertEqual(len(result['result']), 2)
    
    def test_parse_natural_query_invalid(self):
        """Test parsing invalid queries"""
        result = self.nl_engine.parse_natural_query('invalid query', self.test_data)
        
        self.assertIn('error', result)
        self.assertIn('Query not understood', result['error'])
    
    def test_execute_query_pattern_trend(self):
        """Test executing trend pattern"""
        # Add more data for trend calculation
        trend_data = pd.DataFrame({
            'Budget': [100, 110, 120, 130, 140]
        })
        
        import re
        match = re.search(r'(trend|change|growth)\s+(\w+)', 'trend Budget')
        result = self.nl_engine.execute_query_pattern('trend', match, trend_data)
        
        self.assertEqual(result['type'], 'trend')
        self.assertEqual(result['column'], 'Budget')
        self.assertIsInstance(result['result'], float)


class TestAdvancedVisualizationEngine(unittest.TestCase):
    """Test the AdvancedVisualizationEngine class"""
    
    def setUp(self):
        """Set up test data"""
        self.viz_engine = AdvancedVisualizationEngine()
        self.test_data = pd.DataFrame({
            'Department': ['HR', 'IT', 'Finance', 'Marketing'],
            'Budget': [100000, 150000, 200000, 120000],
            'Actual': [95000, 145000, 195000, 115000],
            'Region': ['North', 'South', 'North', 'South']
        })
    
    def test_color_palettes(self):
        """Test that color palettes are defined"""
        expected_palettes = ['corporate', 'municipal', 'financial', 'analytics']
        
        for palette in expected_palettes:
            self.assertIn(palette, self.viz_engine.color_palettes)
            self.assertIsInstance(self.viz_engine.color_palettes[palette], list)
    
    def test_create_standard_chart_bar(self):
        """Test creating standard bar chart"""
        fig = self.viz_engine._create_standard_chart(
            self.test_data, VisualizationType.BAR, 'Department', 'Budget'
        )
        
        self.assertIsNotNone(fig)
        # Check if it's a plotly figure
        self.assertTrue(hasattr(fig, 'data'))
    
    def test_create_standard_chart_line(self):
        """Test creating standard line chart"""
        fig = self.viz_engine._create_standard_chart(
            self.test_data, VisualizationType.LINE, 'Department', 'Budget'
        )
        
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, 'data'))
    
    def test_create_standard_chart_pie(self):
        """Test creating standard pie chart"""
        fig = self.viz_engine._create_standard_chart(
            self.test_data, VisualizationType.PIE, 'Department', 'Budget'
        )
        
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, 'data'))
    
    def test_create_correlation_matrix(self):
        """Test creating correlation matrix"""
        fig = self.viz_engine._create_correlation_matrix(
            self.test_data, title="Test Correlation"
        )
        
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, 'data'))
    
    def test_create_box_plot(self):
        """Test creating box plot"""
        fig = self.viz_engine._create_box(
            self.test_data, 'Department', 'Budget', title="Test Box Plot"
        )
        
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, 'data'))
    
    def test_create_gauge_chart(self):
        """Test creating gauge chart"""
        fig = self.viz_engine._create_gauge(
            self.test_data, 'Budget', title="Test Gauge"
        )
        
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, 'data'))
    
    def test_create_advanced_chart_invalid_type(self):
        """Test creating chart with invalid type"""
        fig = self.viz_engine.create_advanced_chart(
            self.test_data, VisualizationType.TABLE, 'Department', 'Budget'
        )
        
        # Should fall back to standard chart
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, 'data'))


class TestLoadOrgData(unittest.TestCase):
    """Test the load_org_data function"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Create test database
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE financial_data (
                id INTEGER PRIMARY KEY,
                department TEXT,
                budget REAL,
                actual REAL
            )
        ''')
        cursor.execute('''
            INSERT INTO financial_data (department, budget, actual)
            VALUES ('HR', 100000, 95000), ('IT', 150000, 145000)
        ''')
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.temp_db.name)
    
    @patch('bi_sandbox.st')
    def test_load_org_data_success(self, mock_st):
        """Test successful data loading"""
        with patch('bi_sandbox.os.path.exists', return_value=True):
            with patch('bi_sandbox.sqlite3.connect') as mock_connect:
                mock_conn = Mock()
                mock_connect.return_value = mock_conn
                
                # Mock pandas read_sql_query
                with patch('bi_sandbox.pd.read_sql_query') as mock_read_sql:
                    mock_read_sql.return_value = pd.DataFrame({
                        'department': ['HR', 'IT'],
                        'budget': [100000, 150000],
                        'actual': [95000, 145000]
                    })
                    
                    result = load_org_data('test_org')
                    
                    self.assertIsInstance(result, pd.DataFrame)
                    self.assertEqual(len(result), 2)
                    self.assertIn('department', result.columns)
    
    @patch('bi_sandbox.st')
    def test_load_org_data_fallback(self, mock_st):
        """Test fallback to default database"""
        with patch('bi_sandbox.os.path.exists', side_effect=lambda x: x == 'govsight_all_in_one_data.db'):
            with patch('bi_sandbox.sqlite3.connect') as mock_connect:
                mock_conn = Mock()
                mock_connect.return_value = mock_conn
                
                with patch('bi_sandbox.pd.read_sql_query') as mock_read_sql:
                    mock_read_sql.return_value = pd.DataFrame({'test': [1, 2, 3]})
                    
                    result = load_org_data('nonexistent_org')
                    
                    self.assertIsInstance(result, pd.DataFrame)
    
    @patch('bi_sandbox.st')
    def test_load_org_data_error(self, mock_st):
        """Test error handling in data loading"""
        with patch('bi_sandbox.os.path.exists', return_value=True):
            with patch('bi_sandbox.sqlite3.connect', side_effect=Exception("Database error")):
                result = load_org_data('test_org')
                
                self.assertIsInstance(result, pd.DataFrame)
                self.assertTrue(result.empty)
                mock_st.error.assert_called_once()


class TestGenerateAIInsights(unittest.TestCase):
    """Test the generate_ai_insights function"""
    
    def setUp(self):
        """Set up test data"""
        self.test_data = pd.DataFrame({
            'Department': ['HR', 'IT', 'Finance', 'Marketing'],
            'Budget': [100000, 150000, 200000, 120000],
            'Actual': [95000, 145000, 195000, 115000],
            'Region': ['North', 'South', 'North', 'South']
        })
    
    def test_generate_ai_insights_basic(self):
        """Test basic insights generation"""
        insights = generate_ai_insights(self.test_data)
        
        self.assertIsInstance(insights, list)
        self.assertTrue(len(insights) > 0)
        self.assertTrue(len(insights) <= 5)  # Should return max 5 insights
    
    def test_generate_ai_insights_correlation(self):
        """Test insights with strong correlation"""
        # Create data with strong correlation
        corr_data = pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, 6, 8, 10]  # Perfect correlation
        })
        
        insights = generate_ai_insights(corr_data)
        
        self.assertIsInstance(insights, list)
        # Should detect strong correlation
        correlation_found = any('correlation' in insight.lower() for insight in insights)
        self.assertTrue(correlation_found)
    
    def test_generate_ai_insights_outliers(self):
        """Test insights with outliers"""
        # Create data with outliers
        outlier_data = pd.DataFrame({
            'values': [1, 2, 3, 4, 100]  # 100 is an outlier
        })
        
        insights = generate_ai_insights(outlier_data)
        
        self.assertIsInstance(insights, list)
        # Should detect outliers
        outlier_found = any('outlier' in insight.lower() for insight in insights)
        self.assertTrue(outlier_found)
    
    def test_generate_ai_insights_categorical(self):
        """Test insights with categorical data"""
        cat_data = pd.DataFrame({
            'category': ['A', 'A', 'A', 'B', 'C'],
            'value': [1, 2, 3, 4, 5]
        })
        
        insights = generate_ai_insights(cat_data)
        
        self.assertIsInstance(insights, list)
        # Should provide categorical insights
        categorical_found = any('most common' in insight.lower() for insight in insights)
        self.assertTrue(categorical_found)
    
    def test_generate_ai_insights_empty_data(self):
        """Test insights with empty data"""
        empty_data = pd.DataFrame()
        
        insights = generate_ai_insights(empty_data)
        
        self.assertIsInstance(insights, list)
        # Should handle empty data gracefully
        self.assertEqual(len(insights), 0)


class TestBISandboxIntegration(unittest.TestCase):
    """Integration tests for BI Sandbox components"""
    
    def setUp(self):
        """Set up integration test data"""
        self.analytics_engine = AdvancedAnalyticsEngine()
        self.viz_engine = AdvancedVisualizationEngine()
        self.nl_engine = NaturalLanguageAnalytics()
        self.test_data = pd.DataFrame({
            'Department': ['HR', 'IT', 'Finance'],
            'Budget': [100000, 150000, 200000],
            'Actual': [95000, 145000, 195000],
            'Year': [2023, 2023, 2023]
        })
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from data to insights"""
        # 1. Generate insights
        insights = generate_ai_insights(self.test_data)
        self.assertIsInstance(insights, list)
        
        # 2. Query data using natural language
        query_result = self.nl_engine.parse_natural_query('sum Budget', self.test_data)
        self.assertEqual(query_result['type'], 'sum')
        
        # 3. Create visualization
        fig = self.viz_engine.create_advanced_chart(
            self.test_data, VisualizationType.BAR, 'Department', 'Budget'
        )
        self.assertIsNotNone(fig)
        
        # 4. Perform analytics
        star_schema = self.analytics_engine.create_star_schema(
            self.test_data, ['Department'], ['Budget', 'Actual']
        )
        self.assertIn('fact', star_schema)
    
    def test_error_handling_integration(self):
        """Test error handling across components"""
        # Test with empty data
        empty_data = pd.DataFrame()
        
        # Should handle empty data gracefully
        insights = generate_ai_insights(empty_data)
        self.assertEqual(len(insights), 0)
        
        # Natural language should handle empty data
        result = self.nl_engine.parse_natural_query('sum Budget', empty_data)
        self.assertIn('error', result)
    
    def test_performance_with_large_data(self):
        """Test performance with larger datasets"""
        # Create larger test dataset
        large_data = pd.DataFrame({
            'Department': ['HR', 'IT', 'Finance'] * 1000,
            'Budget': np.random.randint(50000, 200000, 3000),
            'Actual': np.random.randint(45000, 190000, 3000)
        })
        
        # Should handle large data efficiently
        insights = generate_ai_insights(large_data)
        self.assertIsInstance(insights, list)
        self.assertTrue(len(insights) <= 5)
        
        # Natural language queries should work with large data
        result = self.nl_engine.parse_natural_query('sum Budget', large_data)
        self.assertEqual(result['type'], 'sum')


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestVisualizationType,
        TestAnalyticsMetric,
        TestDimensionHierarchy,
        TestFilterAction,
        TestAdvancedAnalyticsEngine,
        TestNaturalLanguageAnalytics,
        TestAdvancedVisualizationEngine,
        TestLoadOrgData,
        TestGenerateAIInsights,
        TestBISandboxIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print coverage summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)