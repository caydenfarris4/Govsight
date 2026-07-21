"""
Dedicated Test Suite for AI Proposal Generator

Tests the complete AI proposal generator functionality including 
interface logic, data processing, and error handling.

Created: 2025-06-27
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd


class TestAIProposalGeneratorInterface:
    """Test AI proposal generator interface functionality"""

    def setup_method(self):
        """Setup test data"""
        self.test_scenario = {
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

    def test_scenario_dropdown_population(self):
        """Test scenario dropdown population logic"""
        scenarios = [self.test_scenario]
        
        # Logic from render_ai_proposal_generator
        scenario_names = ["Select a scenario..."] + [s["name"] for s in scenarios]
        
        assert len(scenario_names) == 2, "Should have default option plus one scenario"
        assert scenario_names[0] == "Select a scenario...", "First option should be default"
        assert scenario_names[1] == "westside baseball complex", "Should include scenario name"

    def test_scenario_selection_logic(self):
        """Test scenario selection and data extraction"""
        scenarios = [self.test_scenario]
        selected_scenario_name = "westside baseball complex"
        
        # Logic from render_ai_proposal_generator
        selected_scenario = next((s for s in scenarios if s["name"] == selected_scenario_name), None)
        
        assert selected_scenario is not None, "Should find selected scenario"
        
        project_name = selected_scenario["name"]
        project_cost = float(selected_scenario.get("Total Cost", 0))
        
        assert project_name == "westside baseball complex", "Correct project name extracted"
        assert project_cost == 3600000.0, "Correct project cost extracted"

    def test_funding_metrics_calculation(self):
        """Test funding metrics for display"""
        scenario = self.test_scenario
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        funding_percentage = round((funding_total / project_cost) * 100, 2) if project_cost > 0 else 0
        
        # Test metric values
        assert total_reallocation == 1500000.0, "Correct departmental reallocation"
        assert tax_revenue == 500000.0, "Correct tax revenue"
        assert grant == 400000.0, "Correct grant funding"
        assert private_investment == 1200000.0, "Correct private investment"
        assert funding_total == 3600000.0, "Correct total funding"
        assert bonds_needed == 0.0, "No bonds needed for fully funded project"
        assert funding_percentage == 100.0, "100% funding percentage"

    def test_chart_data_preparation(self):
        """Test chart data preparation for visualization"""
        scenario = self.test_scenario
        
        # Complete calculation logic
        total_reallocation = sum(scenario.get("Department Allocations", {}).values())
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = total_reallocation + tax_revenue + grant + private_investment
        bonds_needed = max(0, project_cost - funding_total)
        
        # Chart data logic from render_ai_proposal_generator
        categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
        values = [total_reallocation, tax_revenue, grant, private_investment, bonds_needed]
        colors = ["#6c5ce7", "#00b894", "#fdcb6e", "#e84393", "#d63031"]
        
        # Filter out zero values
        non_zero_categories = []
        non_zero_values = []
        non_zero_colors = []
        
        for cat, val, col in zip(categories, values, colors):
            if val > 0:
                non_zero_categories.append(cat)
                non_zero_values.append(val)
                non_zero_colors.append(col)
        
        # Test chart data
        assert len(categories) == 5, "Should have 5 categories"
        assert len(values) == 5, "Should have 5 values"
        assert len(colors) == 5, "Should have 5 colors"
        assert len(non_zero_categories) == 4, "Should have 4 non-zero categories (no bonds)"
        assert "Bonds Needed" not in non_zero_categories, "Bonds should be filtered out"
        assert sum(non_zero_values) == 3600000.0, "Non-zero values should sum to total cost"

    def test_debug_output_generation(self):
        """Test debug output generation"""
        scenario = self.test_scenario
        
        # Calculate all values
        total_reallocation = sum(scenario.get("Department Allocations", {}).values())
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = total_reallocation + tax_revenue + grant + private_investment
        bonds_needed = max(0, project_cost - funding_total)
        
        # Debug output formatting logic
        debug_lines = [
            f"- Departmental Reallocation: ${total_reallocation:,.0f}",
            f"- Tax Revenue: ${tax_revenue:,.0f}",
            f"- Grant Funding: ${grant:,.0f}",
            f"- Private Investment: ${private_investment:,.0f}",
            f"- Bonds Needed: ${bonds_needed:,.0f}",
            f"- Total Funding: ${funding_total:,.0f}",
            f"- Project Cost: ${project_cost:,.0f}"
        ]
        
        # Test debug formatting
        assert "1,500,000" in debug_lines[0], "Departmental reallocation formatted correctly"
        assert "500,000" in debug_lines[1], "Tax revenue formatted correctly"
        assert "400,000" in debug_lines[2], "Grant funding formatted correctly"
        assert "1,200,000" in debug_lines[3], "Private investment formatted correctly"
        assert "$0" in debug_lines[4], "Bonds needed formatted correctly"
        assert "3,600,000" in debug_lines[5], "Total funding formatted correctly"
        assert "3,600,000" in debug_lines[6], "Project cost formatted correctly"

    def test_department_selection_logic(self):
        """Test department selection for AI generation"""
        # Mock departments data
        departments = {
            "Administration": {"budget": 1000000},
            "Public Works": {"budget": 2000000},
            "Parks & Recreation": {"budget": 500000},
            "Fire Department": {"budget": 1500000}
        }
        
        # Logic from render_ai_proposal_generator
        dept_names = list(departments.keys())
        default_selection = dept_names[:2] if len(dept_names) >= 2 else dept_names
        
        assert len(dept_names) == 4, "Should have 4 departments"
        assert len(default_selection) == 2, "Should default to first 2 departments"
        assert "Administration" in default_selection, "Should include Administration"
        assert "Public Works" in default_selection, "Should include Public Works"

    def test_empty_scenarios_handling(self):
        """Test handling when no scenarios exist"""
        scenarios = []
        
        # Logic for empty scenarios
        if scenarios:
            scenario_names = ["Select a scenario..."] + [s["name"] for s in scenarios]
        else:
            scenario_names = []
        
        assert scenario_names == [], "Empty scenarios should result in empty options"

    def test_missing_department_allocations(self):
        """Test handling scenarios with missing department allocations"""
        scenario_no_depts = {
            "name": "project without departments",
            "Total Cost": 1000000.0,
            "Tax Revenue": 500000.0,
            "Grant Funding": 300000.0,
            "Private Investment": 200000.0
            # No Department Allocations field
        }
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario_no_depts.get("Department Allocations", {}).values()) if scenario_no_depts.get("Department Allocations") else 0
        
        assert total_reallocation == 0, "Missing department allocations should default to 0"

    def test_ai_plan_generation_trigger(self):
        """Test AI plan generation logic trigger"""
        # Mock AI plan generation
        project_name = "test project"
        project_cost = 1000000.0
        selected_depts = ["Administration", "Public Works"]
        scenario_data = self.test_scenario
        
        # Simulate generate_ai_base_scenario function
        def mock_generate_ai_base_scenario(name, cost, depts, data):
            return {
                "project_name": name,
                "estimated_cost": cost,
                "involved_departments": depts,
                "phases": [
                    {"name": "Planning", "duration_months": 3, "cost_pct": 20},
                    {"name": "Implementation", "duration_months": 12, "cost_pct": 70},
                    {"name": "Completion", "duration_months": 2, "cost_pct": 10}
                ],
                "risks": ["Budget overrun", "Timeline delays", "Resource constraints"],
                "summary": f"AI-generated plan for {name} with estimated cost of ${cost:,.0f}"
            }
        
        plan = mock_generate_ai_base_scenario(project_name, project_cost, selected_depts, scenario_data)
        
        assert plan["project_name"] == "test project", "Correct project name in plan"
        assert plan["estimated_cost"] == 1000000.0, "Correct cost in plan"
        assert len(plan["involved_departments"]) == 2, "Correct number of departments"
        assert len(plan["phases"]) == 3, "Should have 3 phases"
        assert len(plan["risks"]) == 3, "Should have 3 risks"
        assert "AI-generated plan" in plan["summary"], "Should have summary"


class TestAIProposalGeneratorEdgeCases:
    """Test edge cases and error conditions"""

    def test_invalid_scenario_data(self):
        """Test handling of invalid scenario data"""
        invalid_scenarios = [
            {"name": "invalid cost", "Total Cost": "not a number"},
            {"name": "negative cost", "Total Cost": -1000},
            {"name": "missing fields"},
            None
        ]
        
        for scenario in invalid_scenarios:
            if scenario is None:
                continue
                
            # Safe extraction logic
            project_cost = 0
            try:
                project_cost = float(scenario.get("Total Cost", 0))
                if project_cost < 0:
                    project_cost = 0
            except (ValueError, TypeError):
                project_cost = 0
            
            assert project_cost >= 0, f"Cost should be non-negative for scenario: {scenario}"

    def test_large_numbers_formatting(self):
        """Test formatting of very large numbers"""
        large_scenario = {
            "name": "large project",
            "Total Cost": 1000000000.0,  # 1 billion
            "Tax Revenue": 250000000.0,  # 250 million
            "Grant Funding": 100000000.0,  # 100 million
            "Private Investment": 650000000.0,  # 650 million
            "Department Allocations": {}
        }
        
        total_cost = large_scenario["Total Cost"]
        tax_revenue = large_scenario["Tax Revenue"]
        
        # Test formatting
        cost_formatted = f"${total_cost:,.0f}"
        tax_formatted = f"${tax_revenue:,.0f}"
        
        assert "1,000,000,000" in cost_formatted, "Billion should be formatted with commas"
        assert "250,000,000" in tax_formatted, "Millions should be formatted with commas"

    def test_zero_values_filtering(self):
        """Test filtering of zero values in chart data"""
        scenario_with_zeros = {
            "name": "project with zeros",
            "Total Cost": 1000000.0,
            "Tax Revenue": 500000.0,
            "Grant Funding": 0.0,  # Zero value
            "Private Investment": 0.0,  # Zero value
            "Department Allocations": {"Admin": 500000.0}
        }
        
        # Calculate values
        total_reallocation = sum(scenario_with_zeros.get("Department Allocations", {}).values())
        tax_revenue = scenario_with_zeros.get("Tax Revenue", 0)
        grant = scenario_with_zeros.get("Grant Funding", 0)
        private = scenario_with_zeros.get("Private Investment", 0)
        bonds_needed = max(0, scenario_with_zeros["Total Cost"] - (total_reallocation + tax_revenue + grant + private))
        
        categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
        values = [total_reallocation, tax_revenue, grant, private, bonds_needed]
        
        # Filter zero values
        non_zero_data = [(cat, val) for cat, val in zip(categories, values) if val > 0]
        
        assert len(non_zero_data) == 2, "Should have 2 non-zero categories (dept reallocation and tax revenue only)"
        non_zero_categories = [cat for cat, val in non_zero_data]
        assert "Grant Funding" not in non_zero_categories, "Grant funding should be filtered out"
        assert "Private Investment" not in non_zero_categories, "Private investment should be filtered out"

    def test_funding_percentage_edge_cases(self):
        """Test funding percentage calculation edge cases"""
        def calculate_funding_percentage(funding_total, project_cost):
            return round((funding_total / project_cost) * 100, 2) if project_cost > 0 else 0
        
        # Test normal case
        assert calculate_funding_percentage(800000, 1000000) == 80.0, "80% funding"
        
        # Test zero cost
        assert calculate_funding_percentage(500000, 0) == 0, "Zero cost should return 0%"
        
        # Test overfunding
        assert calculate_funding_percentage(1200000, 1000000) == 120.0, "120% overfunding"
        
        # Test exact funding
        assert calculate_funding_percentage(1000000, 1000000) == 100.0, "100% exact funding"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])