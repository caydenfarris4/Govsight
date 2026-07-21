"""
Test Suite for Main App Import Fixes

This module tests the import path corrections made to main_app.py
to ensure the correct scenario planner is being loaded.

Created: 2025-06-27
Tests cover the critical import fix that was preventing AI proposal generator changes from showing
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

# Add root directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class TestMainAppImports:
    """Test main app import configurations"""

    def test_main_app_scenario_planner_import(self):
        """Test that main_app.py has correct scenario planner import"""
        main_app_path = os.path.join(os.path.dirname(__file__), '..', '..', 'main_app.py')
        
        with open(main_app_path, 'r') as f:
            content = f.read()
        
        # Verify correct import is present
        assert 'from modules.scenario_planner.original_scenario_planner import render_scenario_planner' in content, \
            "Missing correct scenario planner import from modules directory"
        
        # Verify incorrect import is not present
        assert 'from scenario_planner import run_scenario_planner' not in content or \
               content.count('from scenario_planner import run_scenario_planner') == 0, \
            "Old incorrect import should be removed or commented out"

    def test_main_app_scenario_planner_function_call(self):
        """Test that main_app.py calls the correct scenario planner function"""
        main_app_path = os.path.join(os.path.dirname(__file__), '..', '..', 'main_app.py')
        
        with open(main_app_path, 'r') as f:
            content = f.read()
        
        # Find the scenario planner section
        scenario_section_start = content.find('elif selected_tab == "Scenario Planner":')
        scenario_section_end = content.find('elif selected_tab ==', scenario_section_start + 1)
        
        if scenario_section_end == -1:
            scenario_section_end = content.find('if __name__', scenario_section_start)
        
        scenario_section = content[scenario_section_start:scenario_section_end]
        
        # Verify correct function call
        assert 'render_scenario_planner()' in scenario_section, \
            "Should call render_scenario_planner() function"
        
        # Verify incorrect function call is not present
        assert 'run_scenario_planner()' not in scenario_section, \
            "Should not call old run_scenario_planner() function"

    def test_import_path_accessibility(self):
        """Test that the imported modules are accessible"""
        try:
            from modules.scenario_planner.original_scenario_planner import render_scenario_planner
            assert callable(render_scenario_planner), "render_scenario_planner should be callable"
            
            # Test function signature
            import inspect
            sig = inspect.signature(render_scenario_planner)
            params = list(sig.parameters.keys())
            
            assert 'org' in params, "Function should accept 'org' parameter"
            assert 'org_display_name' in params, "Function should accept 'org_display_name' parameter"
            
        except ImportError as e:
            pytest.fail(f"Failed to import render_scenario_planner: {e}")

    def test_modules_directory_structure(self):
        """Test that modules directory structure is correct"""
        modules_path = os.path.join(os.path.dirname(__file__), '..', '..')
        scenario_planner_path = os.path.join(modules_path, 'modules', 'scenario_planner')
        original_scenario_planner_path = os.path.join(scenario_planner_path, 'original_scenario_planner.py')
        
        assert os.path.exists(scenario_planner_path), \
            f"Scenario planner module directory should exist: {scenario_planner_path}"
        
        assert os.path.exists(original_scenario_planner_path), \
            f"Original scenario planner file should exist: {original_scenario_planner_path}"

    @patch('streamlit.title')
    def test_render_scenario_planner_basic_functionality(self, mock_title):
        """Test that render_scenario_planner function works without errors"""
        try:
            from modules.scenario_planner.original_scenario_planner import render_scenario_planner
            
            # Mock streamlit components to prevent actual rendering
            with patch('streamlit.tabs') as mock_tabs, \
                 patch('modules.scenario_planner.original_scenario_planner.render_scenario_builder'), \
                 patch('modules.scenario_planner.original_scenario_planner.render_legislative_impact_analyzer'), \
                 patch('modules.scenario_planner.original_scenario_planner.render_whatif_simulator'), \
                 patch('modules.scenario_planner.original_scenario_planner.render_restricted_fund_guidance'), \
                 patch('modules.scenario_planner.original_scenario_planner.render_ai_proposal_generator'), \
                 patch('modules.scenario_planner.original_scenario_planner.render_grant_integration'):
                
                # Mock tabs context managers
                tab_mocks = [Mock() for _ in range(6)]
                mock_tabs.return_value = tab_mocks
                
                for tab_mock in tab_mocks:
                    tab_mock.__enter__ = Mock(return_value=tab_mock)
                    tab_mock.__exit__ = Mock(return_value=None)
                
                # Should execute without error
                render_scenario_planner("cityA", "City A")
                
                # Verify title is set
                mock_title.assert_called_with(" Scenario Planner")
                
                # Verify tabs are created
                mock_tabs.assert_called_once()
                
        except Exception as e:
            pytest.fail(f"render_scenario_planner failed to execute: {e}")


class TestImportPathConsistency:
    """Test import path consistency across the application"""

    def test_no_conflicting_imports(self):
        """Test that there are no conflicting import patterns"""
        main_app_path = os.path.join(os.path.dirname(__file__), '..', '..', 'main_app.py')
        
        with open(main_app_path, 'r') as f:
            content = f.read()
        
        # Count import patterns
        modules_imports = content.count('from modules.')
        root_imports = content.count('from scenario_planner import')
        
        # Verify we're primarily using modules imports for scenario planner
        assert 'from modules.scenario_planner.original_scenario_planner import render_scenario_planner' in content, \
            "Should have correct modules import"
        
        # Check that old pattern is not actively used in scenario planner section
        scenario_section_start = content.find('elif selected_tab == "Scenario Planner":')
        scenario_section_end = content.find('elif selected_tab ==', scenario_section_start + 1)
        
        if scenario_section_end == -1:
            scenario_section_end = content.find('if __name__', scenario_section_start)
        
        scenario_section = content[scenario_section_start:scenario_section_end]
        
        assert 'from scenario_planner import' not in scenario_section, \
            "Scenario planner section should not use old import pattern"

    def test_ai_proposal_generator_accessibility(self):
        """Test that AI proposal generator is accessible through correct import path"""
        try:
            from modules.scenario_planner.original_scenario_planner import render_ai_proposal_generator
            
            assert callable(render_ai_proposal_generator), \
                "AI proposal generator should be callable"
            
            # Test function signature
            import inspect
            sig = inspect.signature(render_ai_proposal_generator)
            params = list(sig.parameters.keys())
            
            assert len(params) >= 2, "Function should accept at least 2 parameters"
            assert 'org' in params, "Function should accept 'org' parameter"
            assert 'org_display_name' in params, "Function should accept 'org_display_name' parameter"
            
        except ImportError as e:
            pytest.fail(f"Failed to import render_ai_proposal_generator: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])