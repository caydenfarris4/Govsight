"""
Scenario Planner Module

This module handles all functionality related to the Scenario Planner tab, including:
- Project selection and configuration
- Department budget reallocation
- Funding source allocation
- Visualization and analysis of funding scenarios
- Saving and loading scenarios
- Report generation
"""

from .scenario_builder import render_scenario_builder
from .legislative_analyzer import render_legislative_analyzer
from .whatif_simulator import process_whatif_question, ConversationalWhatIfSimulator
from .grant_finder import render_grant_finder
from .scenario_utils import (
    load_scenario_data,
    save_scenario_data,
    calculate_budget_variance,
    generate_scenario_summary
)

__all__ = [
    'render_scenario_builder',
    'render_legislative_analyzer', 
    'process_whatif_question',
    'ConversationalWhatIfSimulator',
    'render_grant_finder',
    'load_scenario_data',
    'save_scenario_data',
    'calculate_budget_variance',
    'generate_scenario_summary'
]