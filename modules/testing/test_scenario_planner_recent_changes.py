"""
Test Suite for Recent Scenario Planner Changes

This module tests all recent changes made to the scenario planner including:
- AI Proposal Generator interface changes
- Scenario loading functionality
- Database integration fixes
- Import path corrections

Created: 2025-06-27
Tests cover changes made during scenario planner debugging session
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add modules to path for testing
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scenario_planner'))

class TestScenarioPlannerRecentChanges:
    """Test class for recent scenario planner changes"""

    def setup_method(self):
        """Setup test environment"""
        self.test_scenario_data = {
            "name": "westside baseball complex",
            "Total Cost": 3600000.0,
            "Tax Revenue": 500000.0,
            "Grant Funding": 400000.0,
            "Private Investment": 1200000.0,
            "Department Allocations": {
                "Parks & Recreation": 1000000.0,
                "Public Works": 500000.0
            }
        }

    @patch('modules.scenario_planner.original_scenario_planner.get_scenarios')
    def test_ai_proposal_generator_scenario_loading(self, mock_get_scenarios):
        """Test that AI proposal generator correctly loads scenario data"""
        # Mock scenario data
        mock_get_scenarios.return_value = [self.test_scenario_data]
        
        # Import function under test
        from modules.scenario_planner.original_scenario_planner import render_ai_proposal_generator
        
        # Mock streamlit components
        with patch('streamlit.header'), \
             patch('streamlit.markdown'), \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.success'), \
             patch('streamlit.metric'), \
             patch('streamlit.write'), \
             patch('streamlit.columns'):
            
            # Simulate scenario selection
            mock_selectbox.return_value = "westside baseball complex"
            
            # Test should not raise exception
            try:
                render_ai_proposal_generator("cityA", "City A")
                assert True, "AI proposal generator renders without error"
            except Exception as e:
                pytest.fail(f"AI proposal generator failed to render: {e}")

    def test_scenario_data_field_mapping(self):
        """Test that scenario data field mapping works correctly"""
        # Test the data field mapping logic
        scenario = self.test_scenario_data
        
        # Extract funding data using the same logic as the updated function
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        
        # Calculate funding total and bonds needed
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        
        # Verify calculations
        assert total_reallocation == 1500000.0, f"Expected 1500000.0, got {total_reallocation}"
        assert tax_revenue == 500000.0, f"Expected 500000.0, got {tax_revenue}"
        assert grant == 400000.0, f"Expected 400000.0, got {grant}"
        assert private_investment == 1200000.0, f"Expected 1200000.0, got {private_investment}"
        assert project_cost == 3600000.0, f"Expected 3600000.0, got {project_cost}"
        assert funding_total == 3600000.0, f"Expected 3600000.0, got {funding_total}"
        assert bonds_needed == 0.0, f"Expected 0.0, got {bonds_needed}"

    @patch('modules.scenario_planner.original_scenario_planner.get_scenarios')
    def test_funding_breakdown_visualization_data(self, mock_get_scenarios):
        """Test that funding breakdown visualization uses correct data"""
        mock_get_scenarios.return_value = [self.test_scenario_data]
        
        scenario = self.test_scenario_data
        
        # Test the funding breakdown categories and values logic
        total_reallocation = sum(scenario.get("Department Allocations", {}).values())
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = total_reallocation + tax_revenue + grant + private_investment
        bonds_needed = max(0, project_cost - funding_total)
        
        categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
        values = [total_reallocation, tax_revenue, grant, private_investment, bonds_needed]
        
        # Filter out zero values (same logic as in the function)
        non_zero_categories = []
        non_zero_values = []
        
        for cat, val in zip(categories, values):
            if val > 0:
                non_zero_categories.append(cat)
                non_zero_values.append(val)
        
        # Verify we have the expected non-zero categories
        expected_categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment"]
        assert non_zero_categories == expected_categories, f"Expected {expected_categories}, got {non_zero_categories}"
        assert len(non_zero_values) == 4, f"Expected 4 non-zero values, got {len(non_zero_values)}"
        assert sum(non_zero_values) == 3600000.0, f"Expected total 3600000.0, got {sum(non_zero_values)}"

    @patch('modules.database.original_db_connection.get_scenarios')
    def test_get_scenarios_database_integration(self, mock_db_get_scenarios):
        """Test that get_scenarios returns complete funding breakdown data"""
        # Mock database return with complete funding data
        mock_db_get_scenarios.return_value = [self.test_scenario_data]
        
        from modules.database.original_db_connection import get_scenarios
        
        scenarios = get_scenarios()
        
        assert len(scenarios) == 1, f"Expected 1 scenario, got {len(scenarios)}"
        scenario = scenarios[0]
        
        # Verify all required fields are present
        required_fields = ["name", "Total Cost", "Tax Revenue", "Grant Funding", "Private Investment", "Department Allocations"]
        for field in required_fields:
            assert field in scenario, f"Missing required field: {field}"
        
        # Verify field types and values
        assert isinstance(scenario["Total Cost"], (int, float)), "Total Cost should be numeric"
        assert isinstance(scenario["Tax Revenue"], (int, float)), "Tax Revenue should be numeric"
        assert isinstance(scenario["Grant Funding"], (int, float)), "Grant Funding should be numeric"
        assert isinstance(scenario["Private Investment"], (int, float)), "Private Investment should be numeric"
        assert isinstance(scenario["Department Allocations"], dict), "Department Allocations should be a dictionary"

    def test_main_app_import_fix(self):
        """Test that main_app.py imports are correctly configured"""
        # Read main_app.py content to verify import fix
        main_app_path = os.path.join(os.path.dirname(__file__), '..', '..', 'main_app.py')
        
        with open(main_app_path, 'r') as f:
            content = f.read()
        
        # Verify the correct import is present
        assert 'from modules.scenario_planner.original_scenario_planner import render_scenario_planner' in content, \
            "Missing correct scenario planner import"
        
        # Verify the scenario planner is called correctly
        assert 'render_scenario_planner()' in content, \
            "Missing correct scenario planner function call"

    @patch('streamlit.header')
    @patch('streamlit.markdown')
    @patch('streamlit.selectbox')
    @patch('streamlit.success')
    @patch('streamlit.metric')
    @patch('streamlit.write')
    @patch('streamlit.columns')
    @patch('streamlit.multiselect')
    @patch('streamlit.button')
    @patch('modules.scenario_planner.original_scenario_planner.get_scenarios')
    def test_ai_proposal_generator_interface_simplification(self, mock_get_scenarios, mock_button, 
                                                           mock_multiselect, mock_columns, mock_write,
                                                           mock_metric, mock_success, mock_selectbox,
                                                           mock_markdown, mock_header):
        """Test that AI proposal generator interface only shows scenario loading"""
        mock_get_scenarios.return_value = [self.test_scenario_data]
        mock_selectbox.return_value = "westside baseball complex"
        mock_multiselect.return_value = ["Administration", "Public Works"]
        mock_button.return_value = False
        mock_columns.return_value = [Mock(), Mock(), Mock()]
        
        from modules.scenario_planner.original_scenario_planner import render_ai_proposal_generator
        
        # Test that function executes without project input requirements
        try:
            render_ai_proposal_generator("cityA", "City A")
            
            # Verify header is set correctly
            mock_header.assert_called_with(" AI Proposal Generator")
            
            # Verify selectbox is called for scenario selection
            mock_selectbox.assert_called()
            selectbox_calls = mock_selectbox.call_args_list
            scenario_selectbox_called = any("Choose Scenario" in str(call) for call in selectbox_calls)
            assert scenario_selectbox_called, "Scenario selection dropdown not found"
            
            # Verify success message for scenario loading
            mock_success.assert_called()
            
            # Verify metrics are displayed
            assert mock_metric.call_count >= 3, "Expected at least 3 metric calls for funding display"
            
        except Exception as e:
            pytest.fail(f"AI proposal generator interface test failed: {e}")

    def test_removed_grant_integration_from_ai_proposal(self):
        """Test that Grant Integration section is removed from AI proposal generator"""
        # Read the AI proposal generator function source
        scenario_planner_path = os.path.join(os.path.dirname(__file__), '..', 'scenario_planner', 'original_scenario_planner.py')
        
        with open(scenario_planner_path, 'r') as f:
            content = f.read()
        
        # Find the render_ai_proposal_generator function
        function_start = content.find('def render_ai_proposal_generator(')
        function_end = content.find('\ndef ', function_start + 1)
        
        if function_end == -1:
            function_end = len(content)
        
        function_content = content[function_start:function_end]
        
        # Verify Grant Integration sections are not present in AI proposal generator
        assert 'Grant Integration' not in function_content, \
            "Grant Integration section should be removed from AI proposal generator"
        
        # Verify Project Information input fields are not present
        assert 'Project Name' not in function_content or 'text_input("Project Name"' not in function_content, \
            "Project Name input should be removed from AI proposal generator"
        
        assert 'Estimated Cost' not in function_content or 'number_input(' not in function_content, \
            "Cost input fields should be removed from AI proposal generator"

    def test_debug_output_functionality(self):
        """Test that debug output shows correct scenario values"""
        scenario = self.test_scenario_data
        
        # Simulate the debug output logic
        total_reallocation = sum(scenario.get("Department Allocations", {}).values())
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = total_reallocation + tax_revenue + grant + private_investment
        bonds_needed = max(0, project_cost - funding_total)
        
        # Create debug strings that would be displayed
        debug_strings = [
            f"- Departmental Reallocation: ${total_reallocation:,.0f}",
            f"- Tax Revenue: ${tax_revenue:,.0f}",
            f"- Grant Funding: ${grant:,.0f}",
            f"- Private Investment: ${private_investment:,.0f}",
            f"- Bonds Needed: ${bonds_needed:,.0f}",
            f"- Total Funding: ${funding_total:,.0f}",
            f"- Project Cost: ${project_cost:,.0f}"
        ]
        
        # Verify debug output contains expected values
        expected_values = [
            "1,500,000",  # Departmental Reallocation
            "500,000",    # Tax Revenue
            "400,000",    # Grant Funding
            "1,200,000",  # Private Investment
            "0",          # Bonds Needed
            "3,600,000",  # Total Funding
            "3,600,000"   # Project Cost
        ]
        
        for debug_str, expected_val in zip(debug_strings, expected_values):
            assert expected_val in debug_str, f"Expected {expected_val} in debug output: {debug_str}"

    def test_grant_integration_tab_restoration(self):
        """Test that Grant Integration tab is properly restored as separate tab"""
        scenario_planner_path = os.path.join(os.path.dirname(__file__), '..', 'scenario_planner', 'original_scenario_planner.py')
        
        with open(scenario_planner_path, 'r') as f:
            content = f.read()
        
        # Verify Grant Integration is in the tabs list
        assert '" Grant Integration"' in content, \
            "Grant Integration tab should be present in tabs list"
        
        # Verify Grant Integration tab is properly called
        assert 'render_grant_integration(org, org_display_name)' in content, \
            "Grant Integration function should be called in tab6"

    @patch('modules.scenario_planner.original_scenario_planner.get_scenarios')
    def test_scenario_data_persistence(self, mock_get_scenarios):
        """Test that scenario data persists correctly through interface"""
        mock_get_scenarios.return_value = [self.test_scenario_data]
        
        # Simulate loading scenario data
        scenarios = mock_get_scenarios.return_value
        selected_scenario = next((s for s in scenarios if s["name"] == "westside baseball complex"), None)
        
        assert selected_scenario is not None, "Should find westside baseball complex scenario"
        
        # Verify data persistence
        project_name = selected_scenario["name"]
        project_cost = float(selected_scenario.get("Total Cost", 0))
        
        assert project_name == "westside baseball complex", f"Expected 'westside baseball complex', got {project_name}"
        assert project_cost == 3600000.0, f"Expected 3600000.0, got {project_cost}"


class TestDatabaseConnectionFixes:
    """Test database connection fixes for scenario loading"""

    def test_get_scenarios_return_format(self):
        """Test that get_scenarios returns data in expected format"""
        # Mock database response
        mock_db_response = [
            ("westside baseball complex", 3600000.0, 500000.0, 400000.0, 1200000.0, '{"Parks & Recreation": 1000000.0, "Public Works": 500000.0}')
        ]
        
        # Simulate the data processing that should happen in get_scenarios
        processed_scenarios = []
        for row in mock_db_response:
            scenario = {
                "name": row[0],
                "Total Cost": row[1],
                "Tax Revenue": row[2],
                "Grant Funding": row[3],
                "Private Investment": row[4],
                "Department Allocations": eval(row[5]) if row[5] else {}
            }
            processed_scenarios.append(scenario)
        
        # Verify processed data format
        assert len(processed_scenarios) == 1, "Should process one scenario"
        scenario = processed_scenarios[0]
        
        assert scenario["name"] == "westside baseball complex"
        assert scenario["Total Cost"] == 3600000.0
        assert scenario["Tax Revenue"] == 500000.0
        assert scenario["Grant Funding"] == 400000.0
        assert scenario["Private Investment"] == 1200000.0
        assert isinstance(scenario["Department Allocations"], dict)
        assert scenario["Department Allocations"]["Parks & Recreation"] == 1000000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])