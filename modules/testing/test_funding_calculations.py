"""
Test Suite for Funding Calculation Logic

This module tests the core funding calculation logic used in the AI proposal generator
without requiring full module imports.

Created: 2025-06-27
Tests the exact calculation logic implemented in render_ai_proposal_generator
"""

import pytest


class TestFundingCalculations:
    """Test funding calculation logic used in AI proposal generator"""

    def setup_method(self):
        """Setup test data matching westside baseball complex scenario"""
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

    def test_departmental_reallocation_calculation(self):
        """Test departmental reallocation sum calculation"""
        scenario = self.test_scenario
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        
        expected = 1000000.0 + 500000.0  # Parks & Recreation + Public Works
        assert total_reallocation == expected, f"Expected {expected}, got {total_reallocation}"
        assert total_reallocation == 1500000.0, f"Expected 1500000.0, got {total_reallocation}"

    def test_individual_funding_sources(self):
        """Test individual funding source extraction"""
        scenario = self.test_scenario
        
        # Logic from render_ai_proposal_generator
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        
        assert tax_revenue == 500000.0, f"Expected 500000.0, got {tax_revenue}"
        assert grant == 400000.0, f"Expected 400000.0, got {grant}"
        assert private_investment == 1200000.0, f"Expected 1200000.0, got {private_investment}"
        assert project_cost == 3600000.0, f"Expected 3600000.0, got {project_cost}"

    def test_funding_total_calculation(self):
        """Test total funding calculation logic"""
        scenario = self.test_scenario
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        
        expected_total = 1500000.0 + 500000.0 + 400000.0 + 1200000.0
        assert funding_total == expected_total, f"Expected {expected_total}, got {funding_total}"
        assert funding_total == 3600000.0, f"Expected 3600000.0, got {funding_total}"

    def test_bonds_needed_calculation(self):
        """Test bonds needed calculation logic"""
        scenario = self.test_scenario
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        
        # For westside baseball complex, funding covers full cost, so no bonds needed
        assert bonds_needed == 0.0, f"Expected 0.0, got {bonds_needed}"

    def test_chart_categories_and_values(self):
        """Test chart data preparation logic"""
        scenario = self.test_scenario
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        
        categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
        values = [total_reallocation, tax_revenue, grant, private_investment, bonds_needed]
        
        expected_values = [1500000.0, 500000.0, 400000.0, 1200000.0, 0.0]
        
        assert len(categories) == 5, f"Expected 5 categories, got {len(categories)}"
        assert len(values) == 5, f"Expected 5 values, got {len(values)}"
        assert values == expected_values, f"Expected {expected_values}, got {values}"

    def test_non_zero_filtering_logic(self):
        """Test filtering logic for chart display"""
        scenario = self.test_scenario
        
        # Complete calculation
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        
        categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
        values = [total_reallocation, tax_revenue, grant, private_investment, bonds_needed]
        
        # Filter out zero values (logic from render_ai_proposal_generator)
        non_zero_categories = []
        non_zero_values = []
        
        for cat, val in zip(categories, values):
            if val > 0:
                non_zero_categories.append(cat)
                non_zero_values.append(val)
        
        # For westside baseball complex, bonds needed is 0, so should be filtered out
        expected_categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment"]
        expected_values = [1500000.0, 500000.0, 400000.0, 1200000.0]
        
        assert non_zero_categories == expected_categories, f"Expected {expected_categories}, got {non_zero_categories}"
        assert non_zero_values == expected_values, f"Expected {expected_values}, got {non_zero_values}"
        assert len(non_zero_categories) == 4, f"Expected 4 non-zero categories, got {len(non_zero_categories)}"

    def test_funding_percentage_calculation(self):
        """Test funding percentage calculation for metrics"""
        scenario = self.test_scenario
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        
        funding_percentage = round((funding_total / project_cost) * 100, 2) if project_cost > 0 else 0
        
        # For westside baseball complex, funding exactly covers cost
        assert funding_percentage == 100.0, f"Expected 100.0%, got {funding_percentage}%"

    def test_edge_case_zero_department_allocations(self):
        """Test calculation when no department allocations exist"""
        scenario_no_depts = {
            "name": "test project",
            "Total Cost": 1000000.0,
            "Tax Revenue": 500000.0,
            "Grant Funding": 300000.0,
            "Private Investment": 0.0,
            "Department Allocations": {}
        }
        
        # Logic from render_ai_proposal_generator
        total_reallocation = sum(scenario_no_depts.get("Department Allocations", {}).values()) if scenario_no_depts.get("Department Allocations") else 0
        tax_revenue = float(scenario_no_depts.get("Tax Revenue", 0))
        grant = float(scenario_no_depts.get("Grant Funding", 0))
        private_investment = float(scenario_no_depts.get("Private Investment", 0))
        project_cost = float(scenario_no_depts.get("Total Cost", 0))
        
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        
        assert total_reallocation == 0.0, f"Expected 0.0, got {total_reallocation}"
        assert funding_total == 800000.0, f"Expected 800000.0, got {funding_total}"
        assert bonds_needed == 200000.0, f"Expected 200000.0, got {bonds_needed}"

    def test_edge_case_missing_fields(self):
        """Test calculation when some fields are missing"""
        scenario_minimal = {
            "name": "minimal project",
            "Total Cost": 500000.0
        }
        
        # Logic from render_ai_proposal_generator with default values
        total_reallocation = sum(scenario_minimal.get("Department Allocations", {}).values()) if scenario_minimal.get("Department Allocations") else 0
        tax_revenue = float(scenario_minimal.get("Tax Revenue", 0))
        grant = float(scenario_minimal.get("Grant Funding", 0))
        private_investment = float(scenario_minimal.get("Private Investment", 0))
        project_cost = float(scenario_minimal.get("Total Cost", 0))
        
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        
        assert total_reallocation == 0.0, f"Expected 0.0, got {total_reallocation}"
        assert tax_revenue == 0.0, f"Expected 0.0, got {tax_revenue}"
        assert grant == 0.0, f"Expected 0.0, got {grant}"
        assert private_investment == 0.0, f"Expected 0.0, got {private_investment}"
        assert funding_total == 0.0, f"Expected 0.0, got {funding_total}"
        assert bonds_needed == 500000.0, f"Expected 500000.0, got {bonds_needed}"

    def test_debug_output_formatting(self):
        """Test debug output string formatting logic"""
        scenario = self.test_scenario
        
        # Calculate values
        total_reallocation = sum(scenario.get("Department Allocations", {}).values()) if scenario.get("Department Allocations") else 0
        tax_revenue = float(scenario.get("Tax Revenue", 0))
        grant = float(scenario.get("Grant Funding", 0))
        private_investment = float(scenario.get("Private Investment", 0))
        project_cost = float(scenario.get("Total Cost", 0))
        funding_total = round(total_reallocation + tax_revenue + grant + private_investment, 2)
        bonds_needed = round(max(0, project_cost - funding_total), 2)
        
        # Debug formatting logic from render_ai_proposal_generator
        debug_strings = [
            f"- Departmental Reallocation: ${total_reallocation:,.0f}",
            f"- Tax Revenue: ${tax_revenue:,.0f}",
            f"- Grant Funding: ${grant:,.0f}",
            f"- Private Investment: ${private_investment:,.0f}",
            f"- Bonds Needed: ${bonds_needed:,.0f}",
            f"- Total Funding: ${funding_total:,.0f}",
            f"- Project Cost: ${project_cost:,.0f}"
        ]
        
        expected_strings = [
            "- Departmental Reallocation: $1,500,000",
            "- Tax Revenue: $500,000",
            "- Grant Funding: $400,000",
            "- Private Investment: $1,200,000",
            "- Bonds Needed: $0",
            "- Total Funding: $3,600,000",
            "- Project Cost: $3,600,000"
        ]
        
        assert debug_strings == expected_strings, f"Expected {expected_strings}, got {debug_strings}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])