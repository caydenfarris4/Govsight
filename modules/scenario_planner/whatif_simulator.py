"""
Conversational What-If Scenario Simulator - AI-powered budget scenario analysis
Integrated with Mantis for natural language scenario testing
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
import re
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.ai_hub.ai_hub import ask_ai, simulate_adjustment
from modules.database.db_connection import load_org_data, format_currency, format_percentage, connect_db
from modules.utils.ui_helpers import (
    apply_custom_styling,
    show_spinner,
    show_error_with_guidance,
    show_validation_success,
    MultiStepProgress,
    show_info_banner,
    create_responsive_columns,
    handle_database_error
)

# Try to import accessibility helper, fall back if not available
try:
    from modules.utils.accessibility_helper import enhance_chart_accessibility
except ImportError:
    def enhance_chart_accessibility(fig, title, description):
        return fig

import sqlite3

class ConversationalWhatIfSimulator:
    """
    Conversational AI-powered What-If Scenario Simulator
    Processes natural language scenario questions and returns relevant graphs
    """
    
    def __init__(self):
        self.scenario_patterns = {
            'increase_decrease': r'(?i)(increase|decrease|reduce|cut|boost|raise|lower)\s+(.+?)\s+by\s+(\d+\.?\d*)\s*(%|percent|million|thousand|dollars|\$)',
            'reallocate': r'(?i)(reallocate|move|transfer)\s+(.+?)\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+(\d+\.?\d*))?',
            'compare_scenarios': r'(?i)(compare|what if)\s+(.+?)\s+(vs|versus|compared to)\s+(.+)',
            'target_budget': r'(?i)(target|set)\s+(.+?)\s+(budget|total)\s+(?:to\s+)?(\d+\.?\d*)\s*(million|thousand|dollars|\$)?',
            'percentage_change': r'(?i)(all|every)\s+(.+?)\s+(increase|decrease|reduce|cut)\s+by\s+(\d+\.?\d*)\s*(%|percent)',
            'department_focus': r'(?i)(what would happen if|show me|analyze)\s+(.+?)\s+(department|budget)',
            'impact_analysis': r'(?i)(impact|effect|result)\s+of\s+(.+)',
            'visualization_request': r'(?i)(show|display|chart|graph|visualize)\s+(.+)',
            'salary_adjustment': r'(?i)(increase|decrease|raise|reduce|cut)\s+(?:all\s+)?salaries?\s+(?:by\s+)?(\d+\.?\d*)\s*(%|percent)?',
            'fte_change': r'(?i)(add|remove|hire|eliminate)\s+(\d+)\s+(?:new\s+)?(?:fte|positions?|employees?)(?:\s+(?:in|for)\s+(.+?))?',
            'cola_adjustment': r'(?i)(?:apply|add|implement)\s+(?:a\s+)?(\d+\.?\d*)\s*(%|percent)?\s+cola'
        }
        
        # Initialize database connection
        self.db_conn = None
        self.connect_to_database()
        
        # Average salary data for position calculations
        self.avg_salaries = {
            'police': 65000,
            'fire': 62000,
            'public works': 55000,
            'parks': 48000,
            'administration': 58000,
            'finance': 60000,
            'utilities': 57000,
            'planning': 62000,
            'library': 45000,
            'recreation': 47000,
            'public safety': 63000,
            'community development': 59000,
            'default': 55000
        }
        
        # Benefits multiplier (typically 30-40% on top of salary)
        self.benefits_multiplier = 1.35
    
    def process_scenario_query(self, query: str, org_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Process natural language scenario query and return visualization data
        """
        try:
            # Parse the what-if query
            parsed_query = self.parse_whatif_query(query)
            
            # Analyze the query to determine scenario type
            scenario_type = self._identify_scenario_type(query)
            
            # Extract parameters from the query
            parameters = self._extract_parameters(query, scenario_type)
            parameters.update(parsed_query)  # Merge parsed query data
            
            # Generate scenario based on type
            if scenario_type == 'salary_adjustment':
                result = self._handle_salary_adjustment(query, parameters, org_data)
            elif scenario_type == 'fte_change':
                result = self._handle_fte_change(query, parameters, org_data)
            elif scenario_type == 'cola_adjustment':
                result = self._handle_cola_adjustment(query, parameters, org_data)
            elif scenario_type == 'increase_decrease':
                result = self._handle_increase_decrease(query, parameters, org_data)
            elif scenario_type == 'reallocate':
                result = self._handle_reallocation(query, parameters, org_data)
            elif scenario_type == 'compare_scenarios':
                result = self._handle_comparison(query, parameters, org_data)
            elif scenario_type == 'target_budget':
                result = self._handle_target_budget(query, parameters, org_data)
            elif scenario_type == 'percentage_change':
                result = self._handle_percentage_change(query, parameters, org_data)
            elif scenario_type == 'impact_analysis':
                result = self._handle_impact_analysis(query, parameters, org_data)
            else:
                result = self._handle_general_scenario(query, org_data)
            
            return {
                'success': True,
                'scenario_type': scenario_type,
                'query': query,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
    
    def _identify_scenario_type(self, query: str) -> str:
        """Identify the type of scenario from natural language"""
        for scenario_type, pattern in self.scenario_patterns.items():
            if re.search(pattern, query):
                return scenario_type
        return 'general'
    
    def _extract_parameters(self, query: str, scenario_type: str) -> Dict[str, Any]:
        """Extract parameters from natural language query"""
        parameters = {}
        
        if scenario_type in self.scenario_patterns:
            pattern = self.scenario_patterns[scenario_type]
            match = re.search(pattern, query)
            if match:
                parameters['match_groups'] = match.groups()
                parameters['full_match'] = match.group(0)
        
        # Extract common parameters
        parameters['departments'] = self._extract_departments(query)
        parameters['amounts'] = self._extract_amounts(query)
        parameters['percentages'] = self._extract_percentages(query)
        
        return parameters
    
    def connect_to_database(self):
        """Connect to the GL database"""
        try:
            # Try multiple database paths
            db_paths = [
                'databases/core/caselle_gl0_mock.db',
                'caselle_gl0_mock.db',
                'govsight_all_in_one_data.db',
                'databases/core/govsight_all_in_one_data.db'
            ]
            
            for path in db_paths:
                if os.path.exists(path):
                    self.db_conn = sqlite3.connect(path)
                    break
        except Exception as e:
            print(f"Database connection error: {e}")
    
    def _extract_departments(self, query: str) -> List[str]:
        """Extract department names from query"""
        # Get actual departments from database if available
        actual_departments = self._get_departments_from_db()
        if not actual_departments:
            # Fallback to common department names
            actual_departments = ['police', 'fire', 'public works', 'parks', 'administration', 
                                 'finance', 'utilities', 'planning', 'library', 'recreation',
                                 'public safety', 'community development']
        
        found_departments = []
        query_lower = query.lower()
        
        for dept in actual_departments:
            dept_lower = dept.lower()
            # Check for exact match or partial match
            if dept_lower in query_lower or dept_lower.replace(' ', '') in query_lower:
                found_departments.append(dept)
        
        return found_departments
    
    def _get_departments_from_db(self) -> List[str]:
        """Get department list from database"""
        if not self.db_conn:
            return []
        
        try:
            cursor = self.db_conn.cursor()
            # Try different table/column combinations
            queries = [
                "SELECT DISTINCT Department FROM tblGLAccount WHERE Department IS NOT NULL",
                "SELECT DISTINCT name FROM departments",
                "SELECT DISTINCT Department FROM Budget WHERE Department IS NOT NULL"
            ]
            
            for query in queries:
                try:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    if results:
                        return [row[0] for row in results if row[0]]
                except:
                    continue
        except:
            pass
        
        return []
    
    def _extract_amounts(self, query: str) -> List[float]:
        """Extract monetary amounts from query"""
        # Pattern for amounts with units
        amount_pattern = r'(\d+\.?\d*)\s*(million|thousand|dollars|\$|k|m)'
        matches = re.findall(amount_pattern, query.lower())
        
        amounts = []
        for value, unit in matches:
            val = float(value)
            if unit in ['million', 'm']:
                val *= 1000000
            elif unit in ['thousand', 'k']:
                val *= 1000
            amounts.append(val)
        
        return amounts
    
    def _extract_percentages(self, query: str) -> List[float]:
        """Extract percentages from query"""
        percentage_pattern = r'(\d+\.?\d*)\s*(?:%|percent)'
        matches = re.findall(percentage_pattern, query.lower())
        return [float(match) for match in matches]
    
    def _handle_increase_decrease(self, query: str, parameters: Dict[str, Any], org_data: pd.DataFrame) -> Dict[str, Any]:
        """Handle increase/decrease scenarios"""
        try:
            match_groups = parameters.get('match_groups', [])
            if not match_groups:
                return self._handle_general_scenario(query, org_data)
            
            action = match_groups[0].lower()  # increase/decrease
            target = match_groups[1]  # what to change
            amount = float(match_groups[2])  # by how much
            unit = match_groups[3].lower()  # unit (%, dollar, etc.)
            
            # Create simulated data
            simulated_df = org_data.copy()
            
            # Find matching departments
            departments = parameters.get('departments', [])
            if not departments:
                # Try to find department from target
                departments = [dept for dept in org_data['Department'].unique() if dept.lower() in target.lower()]
            
            if departments:
                for dept in departments:
                    dept_mask = simulated_df['Department'].str.lower().str.contains(dept.lower(), na=False)
                    
                    if unit in ['%', 'percent']:
                        multiplier = 1 + (amount / 100) if action in ['increase', 'boost', 'raise'] else 1 - (amount / 100)
                        simulated_df.loc[dept_mask, 'Budget'] *= multiplier
                    else:
                        # Dollar amount
                        change = amount if action in ['increase', 'boost', 'raise'] else -amount
                        simulated_df.loc[dept_mask, 'Budget'] += change
            
            # Generate visualization
            chart = self._create_comparison_chart(org_data, simulated_df)
            
            # Create summary
            original_total = org_data['Budget'].sum()
            new_total = simulated_df['Budget'].sum()
            change = new_total - original_total
            
            summary = f"""
            **Scenario Analysis: {action.title()} {target} by {amount}{unit}**
            
            **Budget Impact:**
            - Original Total: {format_currency(original_total)}
            - New Total: {format_currency(new_total)}
            - Net Change: {format_currency(change)} ({(change/original_total)*100:+.1f}%)
            """
            
            return {
                'summary': summary,
                'chart': chart,
                'original_data': org_data,
                'simulated_data': simulated_df,
                'change_amount': change
            }
            
        except Exception as e:
            return {'error': f"Could not process scenario: {str(e)}"}
    
    def _handle_general_scenario(self, query: str, org_data: pd.DataFrame) -> Dict[str, Any]:
        """Handle general scenario queries using AI"""
        try:
            # Use AI to understand and simulate the scenario
            simulated_df = simulate_adjustment(query, org_data)
            
            if simulated_df is not None and not simulated_df.empty:
                chart = self._create_comparison_chart(org_data, simulated_df)
                
                original_total = org_data['Budget'].sum()
                new_total = simulated_df['Budget'].sum()
                change = new_total - original_total
                
                summary = f"""
                **AI-Powered Scenario Analysis**
                
                Query: "{query}"
                
                **Budget Impact:**
                - Original Total: {format_currency(original_total)}
                - New Total: {format_currency(new_total)}
                - Net Change: {format_currency(change)} ({(change/original_total)*100:+.1f}%)
                """
                
                return {
                    'summary': summary,
                    'chart': chart,
                    'original_data': org_data,
                    'simulated_data': simulated_df,
                    'change_amount': change
                }
            else:
                return {'error': "Could not generate scenario simulation. Please provide more specific details."}
                
        except Exception as e:
            return {'error': f"AI scenario processing failed: {str(e)}"}
    
    def parse_whatif_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language what-if query to extract parameters"""
        parsed = {
            'scenario_type': None,
            'departments': [],
            'amount': None,
            'percentage': None,
            'fte_count': None,
            'salary_change': None,
            'cola_rate': None,
            'is_ongoing': True,  # Default to ongoing expenses
            'funding_source': None,
            'time_period': 'annual'
        }
        
        query_lower = query.lower()
        
        # Check for one-time vs ongoing
        if any(phrase in query_lower for phrase in ['one time', 'one-time', 'once', 'single year']):
            parsed['is_ongoing'] = False
        
        # Extract salary adjustment
        salary_match = re.search(self.scenario_patterns['salary_adjustment'], query)
        if salary_match:
            parsed['scenario_type'] = 'salary_adjustment'
            parsed['salary_change'] = float(salary_match.group(2))  # Group 2 is the number
            if salary_match.group(3) and '%' in str(salary_match.group(3)):
                parsed['percentage'] = parsed['salary_change']
        
        # Extract FTE changes
        fte_match = re.search(self.scenario_patterns['fte_change'], query)
        if fte_match:
            parsed['scenario_type'] = 'fte_change'
            parsed['fte_count'] = int(fte_match.group(2))
            if fte_match.group(3):
                parsed['departments'] = [fte_match.group(3)]
        
        # Extract COLA
        cola_match = re.search(self.scenario_patterns['cola_adjustment'], query)
        if cola_match:
            parsed['scenario_type'] = 'cola_adjustment'
            parsed['cola_rate'] = float(cola_match.group(1))
        
        # Extract departments
        if not parsed['departments']:
            parsed['departments'] = self._extract_departments(query)
        
        # Extract amounts and percentages
        parsed['amounts'] = self._extract_amounts(query)
        if parsed['amounts'] and not parsed['amount']:
            parsed['amount'] = parsed['amounts'][0]
        
        percentages = self._extract_percentages(query)
        if percentages and not parsed['percentage']:
            parsed['percentage'] = percentages[0]
        
        return parsed
    
    def calculate_salary_impact(self, departments: List[str], percentage_change: float, 
                               is_ongoing: bool = True) -> Dict[str, Any]:
        """Calculate the impact of salary changes on department budgets"""
        impact = {
            'total_cost': 0,
            'annual_cost': 0,
            'department_impacts': {},
            'affected_employees': 0,
            'recommendations': []
        }
        
        try:
            if self.db_conn:
                cursor = self.db_conn.cursor()
                
                for dept in departments:
                    # Get current salary expenses for department
                    queries = [
                        f"SELECT SUM(Budget) FROM tblGLAccount WHERE Department LIKE '%{dept}%' AND (AccountName LIKE '%salary%' OR AccountName LIKE '%wage%' OR AccountName LIKE '%personnel%')",
                        f"SELECT COUNT(*) FROM Employees e JOIN Positions p ON e.PositionID = p.PositionID WHERE p.Department LIKE '%{dept}%'"
                    ]
                    
                    dept_salary_total = 0
                    employee_count = 0
                    
                    try:
                        # Get salary budget
                        cursor.execute(queries[0])
                        result = cursor.fetchone()
                        if result and result[0]:
                            dept_salary_total = result[0]
                        else:
                            # Estimate based on department size
                            dept_salary_total = self.avg_salaries.get(dept.lower(), self.avg_salaries['default']) * 50
                        
                        # Get employee count if possible
                        try:
                            cursor.execute(queries[1])
                            result = cursor.fetchone()
                            if result and result[0]:
                                employee_count = result[0]
                            else:
                                employee_count = int(dept_salary_total / self.avg_salaries.get(dept.lower(), self.avg_salaries['default']))
                        except:
                            employee_count = int(dept_salary_total / self.avg_salaries.get(dept.lower(), self.avg_salaries['default']))
                        
                    except Exception as e:
                        # Fallback estimation
                        dept_salary_total = self.avg_salaries.get(dept.lower(), self.avg_salaries['default']) * 50
                        employee_count = 50
                    
                    # Calculate impact
                    dept_impact = dept_salary_total * (percentage_change / 100)
                    
                    impact['department_impacts'][dept] = {
                        'current_salary_budget': dept_salary_total,
                        'change_amount': dept_impact,
                        'new_salary_budget': dept_salary_total + dept_impact,
                        'affected_employees': employee_count
                    }
                    
                    impact['total_cost'] += dept_impact
                    impact['affected_employees'] += employee_count
            else:
                # Fallback calculation without database
                for dept in departments:
                    avg_salary = self.avg_salaries.get(dept.lower(), self.avg_salaries['default'])
                    estimated_employees = 50  # Default estimate
                    dept_salary_total = avg_salary * estimated_employees
                    dept_impact = dept_salary_total * (percentage_change / 100)
                    
                    impact['department_impacts'][dept] = {
                        'current_salary_budget': dept_salary_total,
                        'change_amount': dept_impact,
                        'new_salary_budget': dept_salary_total + dept_impact,
                        'affected_employees': estimated_employees
                    }
                    
                    impact['total_cost'] += dept_impact
                    impact['affected_employees'] += estimated_employees
            
            # Set annual cost
            impact['annual_cost'] = impact['total_cost'] if is_ongoing else 0
            
            # Generate recommendations
            if percentage_change > 0:
                impact['recommendations'].append(f"Consider phased implementation over 2-3 years to minimize budget impact")
                impact['recommendations'].append(f"Review comparable jurisdictions to ensure competitive compensation")
                if impact['total_cost'] > 1000000:
                    impact['recommendations'].append(f"Identify revenue sources or cost reductions to offset {format_currency(impact['total_cost'])}")
            else:
                impact['recommendations'].append(f"Monitor employee retention and morale during salary reductions")
                impact['recommendations'].append(f"Consider alternative cost-saving measures")
        
        except Exception as e:
            print(f"Error calculating salary impact: {e}")
        
        return impact
    
    def calculate_fte_impact(self, fte_count: int, departments: List[str], 
                           action: str = 'add') -> Dict[str, Any]:
        """Calculate the cost impact of adding or removing FTE positions"""
        impact = {
            'total_cost': 0,
            'annual_cost': 0,
            'positions': [],
            'breakdown': {
                'salary_cost': 0,
                'benefits_cost': 0,
                'equipment_cost': 0,
                'training_cost': 0
            },
            'recommendations': []
        }
        
        try:
            for dept in departments:
                avg_salary = self.avg_salaries.get(dept.lower(), self.avg_salaries['default'])
                
                # Calculate costs per position
                salary_per_fte = avg_salary
                benefits_per_fte = avg_salary * (self.benefits_multiplier - 1)
                equipment_per_fte = 5000 if action == 'add' else 0  # One-time equipment cost
                training_per_fte = 3000 if action == 'add' else 0   # One-time training cost
                
                # Total per FTE
                total_per_fte = salary_per_fte + benefits_per_fte
                one_time_per_fte = equipment_per_fte + training_per_fte
                
                # Calculate for all FTEs
                total_salary = salary_per_fte * fte_count
                total_benefits = benefits_per_fte * fte_count
                total_equipment = equipment_per_fte * fte_count
                total_training = training_per_fte * fte_count
                
                if action == 'add':
                    impact['total_cost'] = (total_salary + total_benefits) + (total_equipment + total_training)
                    impact['annual_cost'] = total_salary + total_benefits
                else:  # remove
                    impact['total_cost'] = -(total_salary + total_benefits)
                    impact['annual_cost'] = -(total_salary + total_benefits)
                
                impact['breakdown']['salary_cost'] = total_salary if action == 'add' else -total_salary
                impact['breakdown']['benefits_cost'] = total_benefits if action == 'add' else -total_benefits
                impact['breakdown']['equipment_cost'] = total_equipment
                impact['breakdown']['training_cost'] = total_training
                
                # Add position details
                for i in range(fte_count):
                    impact['positions'].append({
                        'department': dept,
                        'salary': salary_per_fte,
                        'benefits': benefits_per_fte,
                        'total_cost': total_per_fte + (one_time_per_fte if action == 'add' else 0)
                    })
            
            # Generate recommendations
            if action == 'add':
                impact['recommendations'].append(f"Budget {format_currency(impact['annual_cost'])} annually for ongoing costs")
                impact['recommendations'].append(f"Allocate {format_currency(total_equipment + total_training)} for one-time setup costs")
                if fte_count > 5:
                    impact['recommendations'].append("Consider phased hiring to spread costs and ensure proper onboarding")
            else:
                impact['recommendations'].append(f"Expect {format_currency(abs(impact['annual_cost']))} in annual savings")
                impact['recommendations'].append("Plan for knowledge transfer and workload redistribution")
                impact['recommendations'].append("Consider attrition-based reductions to minimize disruption")
        
        except Exception as e:
            print(f"Error calculating FTE impact: {e}")
        
        return impact
    
    def calculate_cola_impact(self, cola_rate: float, org_data: pd.DataFrame = None) -> Dict[str, Any]:
        """Calculate the impact of Cost of Living Adjustment across all salaries"""
        impact = {
            'total_cost': 0,
            'annual_cost': 0,
            'department_breakdown': {},
            'affected_employees': 0,
            'recommendations': []
        }
        
        try:
            total_salary_budget = 0
            
            if self.db_conn:
                cursor = self.db_conn.cursor()
                
                # Get total salary budget
                cursor.execute("""
                    SELECT Department, SUM(Budget) as SalaryBudget
                    FROM tblGLAccount 
                    WHERE AccountName LIKE '%salary%' 
                       OR AccountName LIKE '%wage%' 
                       OR AccountName LIKE '%personnel%'
                       OR AccountName LIKE '%compensation%'
                    GROUP BY Department
                """)
                
                results = cursor.fetchall()
                if results:
                    for dept, salary_budget in results:
                        if salary_budget:
                            cola_amount = salary_budget * (cola_rate / 100)
                            impact['department_breakdown'][dept] = {
                                'current_salary': salary_budget,
                                'cola_amount': cola_amount,
                                'new_salary': salary_budget + cola_amount
                            }
                            total_salary_budget += salary_budget
                            impact['total_cost'] += cola_amount
                
                # Estimate employee count
                cursor.execute("SELECT COUNT(*) FROM Employees WHERE TerminationDate IS NULL OR TerminationDate = ''")
                result = cursor.fetchone()
                impact['affected_employees'] = result[0] if result and result[0] else int(total_salary_budget / 55000)
            
            elif org_data is not None and not org_data.empty:
                # Use org_data if available
                # Estimate salary portion as 60% of total budget for personnel-heavy departments
                personnel_depts = ['police', 'fire', 'administration']
                
                for dept in org_data['Department'].unique():
                    dept_budget = org_data[org_data['Department'] == dept]['Budget'].sum()
                    
                    # Estimate salary portion
                    if any(p in dept.lower() for p in personnel_depts):
                        salary_portion = dept_budget * 0.6
                    else:
                        salary_portion = dept_budget * 0.4
                    
                    cola_amount = salary_portion * (cola_rate / 100)
                    
                    impact['department_breakdown'][dept] = {
                        'current_salary': salary_portion,
                        'cola_amount': cola_amount,
                        'new_salary': salary_portion + cola_amount
                    }
                    
                    impact['total_cost'] += cola_amount
                    total_salary_budget += salary_portion
                
                impact['affected_employees'] = int(total_salary_budget / 55000)
            
            else:
                # Fallback estimation
                estimated_total_salary = 10000000  # $10M default
                impact['total_cost'] = estimated_total_salary * (cola_rate / 100)
                impact['affected_employees'] = 200
            
            impact['annual_cost'] = impact['total_cost']
            
            # Generate recommendations
            impact['recommendations'].append(f"COLA of {cola_rate}% will cost {format_currency(impact['total_cost'])} annually")
            if cola_rate > 3:
                impact['recommendations'].append("Consider tying COLA to regional CPI or wage growth indices")
            impact['recommendations'].append("Review compensation structure to ensure internal equity")
            if impact['total_cost'] > 500000:
                impact['recommendations'].append(f"Identify sustainable revenue sources for ongoing {format_currency(impact['annual_cost'])} cost")
        
        except Exception as e:
            print(f"Error calculating COLA impact: {e}")
        
        return impact
    
    def calculate_funding_offsets(self, source_depts: List[str], target_depts: List[str], 
                                 amount: float, org_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate funding reallocation between departments"""
        offsets = {
            'source_reductions': {},
            'target_increases': {},
            'net_impact': 0,
            'feasibility': True,
            'recommendations': []
        }
        
        try:
            # Calculate reductions from source departments
            if source_depts:
                amount_per_source = amount / len(source_depts)
                
                for dept in source_depts:
                    dept_budget = org_data[org_data['Department'].str.lower() == dept.lower()]['Budget'].sum() if not org_data.empty else 1000000
                    reduction_pct = (amount_per_source / dept_budget) * 100 if dept_budget > 0 else 0
                    
                    offsets['source_reductions'][dept] = {
                        'current_budget': dept_budget,
                        'reduction_amount': amount_per_source,
                        'new_budget': dept_budget - amount_per_source,
                        'reduction_percentage': reduction_pct
                    }
                    
                    if reduction_pct > 10:
                        offsets['feasibility'] = False
                        offsets['recommendations'].append(f"Warning: {dept} reduction of {reduction_pct:.1f}% may impact service delivery")
            
            # Calculate increases to target departments
            if target_depts:
                amount_per_target = amount / len(target_depts)
                
                for dept in target_depts:
                    dept_budget = org_data[org_data['Department'].str.lower() == dept.lower()]['Budget'].sum() if not org_data.empty else 1000000
                    increase_pct = (amount_per_target / dept_budget) * 100 if dept_budget > 0 else 0
                    
                    offsets['target_increases'][dept] = {
                        'current_budget': dept_budget,
                        'increase_amount': amount_per_target,
                        'new_budget': dept_budget + amount_per_target,
                        'increase_percentage': increase_pct
                    }
            
            # Generate recommendations
            if offsets['feasibility']:
                offsets['recommendations'].append("Reallocation appears feasible without major service impacts")
            else:
                offsets['recommendations'].append("Consider phased reallocation over multiple years")
                offsets['recommendations'].append("Review service level agreements before implementing")
            
            offsets['recommendations'].append("Engage department heads in reallocation planning")
            offsets['recommendations'].append("Monitor performance metrics after implementation")
        
        except Exception as e:
            print(f"Error calculating funding offsets: {e}")
        
        return offsets
    
    def generate_whatif_results(self, scenario_type: str, calculations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate formatted results for what-if scenarios"""
        results = {
            'summary': '',
            'financial_impact': {},
            'visualizations': [],
            'recommendations': [],
            'key_metrics': {}
        }
        
        try:
            if scenario_type == 'salary_adjustment' and 'salary_impact' in calculations:
                impact = calculations['salary_impact']
                results['summary'] = f"Salary adjustment will impact {impact['affected_employees']} employees with a total cost of {format_currency(impact['total_cost'])}"
                results['financial_impact'] = {
                    'One-Time Cost': format_currency(impact['total_cost'] if not impact.get('is_ongoing') else 0),
                    'Annual Cost': format_currency(impact['annual_cost']),
                    'Affected Employees': impact['affected_employees']
                }
                results['recommendations'] = impact['recommendations']
                
            elif scenario_type == 'fte_change' and 'fte_impact' in calculations:
                impact = calculations['fte_impact']
                action_word = 'Adding' if impact['total_cost'] > 0 else 'Removing'
                results['summary'] = f"{action_word} {len(impact['positions'])} FTE positions with total impact of {format_currency(abs(impact['total_cost']))}"
                results['financial_impact'] = {
                    'First Year Cost': format_currency(impact['total_cost']),
                    'Annual Cost': format_currency(impact['annual_cost']),
                    'Salary Component': format_currency(impact['breakdown']['salary_cost']),
                    'Benefits Component': format_currency(impact['breakdown']['benefits_cost'])
                }
                if impact['breakdown']['equipment_cost'] > 0:
                    results['financial_impact']['Equipment Cost'] = format_currency(impact['breakdown']['equipment_cost'])
                if impact['breakdown']['training_cost'] > 0:
                    results['financial_impact']['Training Cost'] = format_currency(impact['breakdown']['training_cost'])
                results['recommendations'] = impact['recommendations']
                
            elif scenario_type == 'cola_adjustment' and 'cola_impact' in calculations:
                impact = calculations['cola_impact']
                results['summary'] = f"COLA adjustment affecting {impact['affected_employees']} employees with annual cost of {format_currency(impact['annual_cost'])}"
                results['financial_impact'] = {
                    'Annual COLA Cost': format_currency(impact['annual_cost']),
                    'Affected Employees': impact['affected_employees']
                }
                # Add department breakdown
                for dept, details in impact['department_breakdown'].items():
                    results['financial_impact'][f"{dept} Impact"] = format_currency(details['cola_amount'])
                results['recommendations'] = impact['recommendations']
            
            # Add key metrics
            if 'total_cost' in results.get('financial_impact', {}):
                results['key_metrics']['Budget Impact'] = results['financial_impact'].get('Annual Cost', results['financial_impact'].get('Total Cost'))
            
        except Exception as e:
            print(f"Error generating results: {e}")
            results['summary'] = "Error generating scenario results"
        
        return results
    
    def _handle_salary_adjustment(self, query: str, parameters: Dict[str, Any], org_data: pd.DataFrame) -> Dict[str, Any]:
        """Handle salary adjustment scenarios"""
        try:
            # Get parameters
            percentage = parameters.get('percentage') or parameters.get('salary_change', 0)
            departments = parameters.get('departments', [])
            
            if not departments:
                # Apply to all departments
                departments = list(org_data['Department'].unique())
            
            # Calculate impact
            salary_impact = self.calculate_salary_impact(departments, percentage, parameters.get('is_ongoing', True))
            
            # Generate results
            results = self.generate_whatif_results('salary_adjustment', {'salary_impact': salary_impact})
            
            # Create visualization if we have data
            if not org_data.empty:
                simulated_df = org_data.copy()
                
                # Apply salary changes to budget
                for dept, impact_data in salary_impact['department_impacts'].items():
                    dept_mask = simulated_df['Department'].str.lower() == dept.lower()
                    if dept_mask.any():
                        change_ratio = impact_data['change_amount'] / impact_data['current_salary_budget'] if impact_data['current_salary_budget'] > 0 else 0
                        simulated_df.loc[dept_mask, 'Budget'] *= (1 + change_ratio)
                
                results['chart'] = self._create_comparison_chart(org_data, simulated_df)
            
            results['summary'] = f"""**Salary Adjustment Scenario**
            
{results['summary']}

**Financial Impact:**
- Total Cost: {format_currency(salary_impact['total_cost'])}
- Annual Cost: {format_currency(salary_impact['annual_cost'])}
- Affected Employees: {salary_impact['affected_employees']}
            """
            
            return results
            
        except Exception as e:
            return {'error': f"Could not process salary adjustment: {str(e)}"}
    
    def _handle_fte_change(self, query: str, parameters: Dict[str, Any], org_data: pd.DataFrame) -> Dict[str, Any]:
        """Handle FTE change scenarios"""
        try:
            # Get parameters
            fte_count = parameters.get('fte_count', 1)
            departments = parameters.get('departments', [])
            action = 'add' if any(word in query.lower() for word in ['add', 'hire']) else 'remove'
            
            if not departments:
                # Default to general administration if no department specified
                departments = ['administration']
            
            # Calculate impact
            fte_impact = self.calculate_fte_impact(fte_count, departments, action)
            
            # Generate results
            results = self.generate_whatif_results('fte_change', {'fte_impact': fte_impact})
            
            # Create visualization if we have data
            if not org_data.empty:
                simulated_df = org_data.copy()
                
                # Apply FTE changes to budget
                for dept in departments:
                    dept_mask = simulated_df['Department'].str.lower() == dept.lower()
                    if dept_mask.any():
                        dept_budget = simulated_df.loc[dept_mask, 'Budget'].sum()
                        change_amount = fte_impact['annual_cost']
                        if dept_budget > 0:
                            simulated_df.loc[dept_mask, 'Budget'] += (change_amount / len(departments))
                
                results['chart'] = self._create_comparison_chart(org_data, simulated_df)
            
            action_word = 'Adding' if action == 'add' else 'Removing'
            results['summary'] = f"""**FTE Change Scenario: {action_word} {fte_count} Positions**
            
{results['summary']}

**Cost Breakdown:**
- Salary Cost: {format_currency(fte_impact['breakdown']['salary_cost'])}
- Benefits Cost: {format_currency(fte_impact['breakdown']['benefits_cost'])}
- Equipment Cost: {format_currency(fte_impact['breakdown']['equipment_cost'])}
- Training Cost: {format_currency(fte_impact['breakdown']['training_cost'])}
            """
            
            return results
            
        except Exception as e:
            return {'error': f"Could not process FTE change: {str(e)}"}
    
    def _handle_cola_adjustment(self, query: str, parameters: Dict[str, Any], org_data: pd.DataFrame) -> Dict[str, Any]:
        """Handle COLA adjustment scenarios"""
        try:
            # Get COLA rate
            cola_rate = parameters.get('cola_rate', 0)
            
            # Calculate impact
            cola_impact = self.calculate_cola_impact(cola_rate, org_data)
            
            # Generate results  
            results = self.generate_whatif_results('cola_adjustment', {'cola_impact': cola_impact})
            
            # Create visualization if we have data
            if not org_data.empty:
                simulated_df = org_data.copy()
                
                # Apply COLA to all departments
                for dept, impact_data in cola_impact['department_breakdown'].items():
                    dept_mask = simulated_df['Department'] == dept
                    if dept_mask.any():
                        current_budget = simulated_df.loc[dept_mask, 'Budget'].sum()
                        if current_budget > 0:
                            cola_ratio = impact_data['cola_amount'] / impact_data['current_salary']
                            # Apply proportionally to budget
                            simulated_df.loc[dept_mask, 'Budget'] *= (1 + cola_ratio * 0.6)  # Assume 60% is salary
                
                results['chart'] = self._create_comparison_chart(org_data, simulated_df)
            
            results['summary'] = f"""**COLA Adjustment Scenario: {cola_rate}% Increase**
            
{results['summary']}

**Department Impact:**
{chr(10).join([f"- {dept}: {format_currency(data['cola_amount'])}" for dept, data in list(cola_impact['department_breakdown'].items())[:5]])}            
            """
            
            return results
            
        except Exception as e:
            return {'error': f"Could not process COLA adjustment: {str(e)}"}
    
    def _handle_reallocation(self, query: str, parameters: Dict[str, Any], org_data: pd.DataFrame) -> Dict[str, Any]:
        """Handle budget reallocation scenarios"""
        try:
            match_groups = parameters.get('match_groups', [])
            if not match_groups or len(match_groups) < 3:
                return self._handle_general_scenario(query, org_data)
            
            # Extract from and to departments
            from_text = match_groups[2]
            to_text = match_groups[3]
            amount = parameters.get('amount', 500000)  # Default amount if not specified
            
            # Find departments
            from_depts = [d for d in self._extract_departments(from_text)]
            to_depts = [d for d in self._extract_departments(to_text)]
            
            if not from_depts:
                from_depts = [from_text]  # Use as-is if no match found
            if not to_depts:
                to_depts = [to_text]
            
            # Calculate funding offsets
            offsets = self.calculate_funding_offsets(from_depts, to_depts, amount, org_data)
            
            # Create simulated data
            simulated_df = org_data.copy()
            
            # Apply reductions
            for dept, reduction in offsets['source_reductions'].items():
                dept_mask = simulated_df['Department'].str.lower() == dept.lower()
                if dept_mask.any():
                    simulated_df.loc[dept_mask, 'Budget'] = reduction['new_budget']
            
            # Apply increases
            for dept, increase in offsets['target_increases'].items():
                dept_mask = simulated_df['Department'].str.lower() == dept.lower()
                if dept_mask.any():
                    simulated_df.loc[dept_mask, 'Budget'] = increase['new_budget']
            
            # Generate visualization
            chart = self._create_comparison_chart(org_data, simulated_df)
            
            summary = f"""**Budget Reallocation Scenario**
            
Reallocating {format_currency(amount)} from {', '.join(from_depts)} to {', '.join(to_depts)}

**Source Department Reductions:**
{chr(10).join([f"- {dept}: -{format_currency(data['reduction_amount'])} ({data['reduction_percentage']:.1f}% reduction)" for dept, data in offsets['source_reductions'].items()])}

**Target Department Increases:**
{chr(10).join([f"- {dept}: +{format_currency(data['increase_amount'])} ({data['increase_percentage']:.1f}% increase)" for dept, data in offsets['target_increases'].items()])}

**Feasibility:** {'✓ Feasible' if offsets['feasibility'] else '⚠ May impact service delivery'}
            """
            
            return {
                'summary': summary,
                'chart': chart,
                'original_data': org_data,
                'simulated_data': simulated_df,
                'offsets': offsets,
                'recommendations': offsets['recommendations']
            }
            
        except Exception as e:
            return {'error': f"Could not process reallocation: {str(e)}"}
    
    def _create_comparison_chart(self, original_df: pd.DataFrame, simulated_df: pd.DataFrame) -> go.Figure:
        """Create a comparison chart for scenario results"""
        # Group data by department
        original_dept = original_df.groupby('Department')['Budget'].sum().reset_index()
        simulated_dept = simulated_df.groupby('Department')['Budget'].sum().reset_index()
        
        # Create comparison chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Current Budget',
            x=original_dept['Department'],
            y=original_dept['Budget'],
            marker_color='#3498db',
            text=original_dept['Budget'].apply(lambda x: format_currency(x)),
            textposition='auto'
        ))
        
        fig.add_trace(go.Bar(
            name='Scenario Budget',
            x=simulated_dept['Department'],
            y=simulated_dept['Budget'],
            marker_color='#e74c3c',
            text=simulated_dept['Budget'].apply(lambda x: format_currency(x)),
            textposition='auto'
        ))
        
        fig.update_layout(
            title='Budget Scenario Comparison',
            xaxis_title='Department',
            yaxis_title='Budget Amount',
            barmode='group',
            height=500,
            template='plotly_white',
            showlegend=True
        )
        
        return enhance_chart_accessibility(fig, "Budget Scenario Comparison")

# Function to integrate with Mantis chat
def process_whatif_question(question: str, org_id: str = None) -> Dict[str, Any]:
    """
    Process a what-if question from Mantis chat and return results
    This is the main entry point for conversational what-if analysis
    """
    try:
        # Get organization data
        org = org_id or st.session_state.get('selected_org', 'cityA')
        org_data = load_org_data(org)
        
        if org_data.empty:
            return {
                'success': False,
                'error': "No budget data available for analysis",
                'message': "I need access to budget data to run scenario simulations. Please ensure your organization data is properly loaded."
            }
        
        # Create simulator and process query
        simulator = ConversationalWhatIfSimulator()
        result = simulator.process_scenario_query(question, org_data)
        
        if result['success']:
            return {
                'success': True,
                'chart': result['result'].get('chart'),
                'summary': result['result'].get('summary', ''),
                'message': "Here's your scenario analysis with visual comparison:",
                'scenario_type': result['scenario_type']
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'message': "I couldn't process that scenario request. Could you try rephrasing with more specific details?"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': "Something went wrong with the scenario analysis. Please try again with a different question."
        }

def display_current_budget_overview(df: pd.DataFrame):
    """Display current budget overview"""
    st.markdown("#### Current Budget Overview")
    
    total_budget = df['Budget'].sum()
    total_actual = df['Actual'].sum() if 'Actual' in df.columns else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Budget", format_currency(total_budget))
    
    with col2:
        if 'Actual' in df.columns:
            st.metric("Total Actual", format_currency(total_actual))
    
    with col3:
        dept_count = df['Department'].nunique()
        st.metric("Departments", dept_count)
    
    # Department breakdown
    dept_summary = df.groupby('Department')['Budget'].sum().sort_values(ascending=False)
    
    with st.expander("View Department Breakdown"):
        for dept, budget in dept_summary.items():
            pct = (budget / total_budget) * 100
            st.markdown(f"**{dept}**: {format_currency(budget)} ({pct:.1f}%)")

def render_natural_language_simulation(df: pd.DataFrame):
    """Natural language simulation interface"""
    st.markdown("#### Natural Language Simulation")
    
    st.markdown("""
    Describe your what-if scenario in plain English. For example:
    - "Increase police budget by 15% and reduce administration by 10%"
    - "Cut all department budgets by 5% except public safety"
    - "Reallocate $500,000 from administration to infrastructure"
    """)
    
    natural_prompt = st.text_area(
        "Describe your budget adjustment scenario:",
        height=100,
        placeholder="Enter your scenario description here...",
        key="natural_whatif_prompt"
    )
    
    if st.button("Simulate Scenario", type="primary") and natural_prompt:
        with st.spinner("Generating simulation..."):
            try:
                # Use AI to simulate the adjustment
                simulated_df = simulate_adjustment(natural_prompt, df)
                
                if simulated_df is not None and not simulated_df.empty:
                    display_simulation_results(df, simulated_df, "Natural Language Simulation")
                else:
                    st.error("Could not generate simulation from the description. Please try a more specific description.")
                    
            except Exception as e:
                st.error(f"Simulation error: {str(e)}")

def render_manual_adjustments_simulation(df: pd.DataFrame):
    """Manual adjustments simulation interface"""
    st.markdown("#### Manual Department Adjustments")
    
    departments = df['Department'].unique()
    adjustments = {}
    
    # Create adjustment inputs for each department
    cols = st.columns(2)
    
    for i, dept in enumerate(departments):
        with cols[i % 2]:
            current_budget = df[df['Department'] == dept]['Budget'].sum()
            
            new_budget = st.number_input(
                f"{dept} Budget",
                min_value=0.0,
                value=float(current_budget),
                step=1000.0,
                key=f"manual_adj_{dept}",
                format="%.0f",
                help=f"Current: {format_currency(current_budget)}"
            )
            
            adjustments[dept] = new_budget
    
    if st.button("Apply Manual Adjustments", type="primary"):
        simulated_df = apply_manual_adjustments(df, adjustments)
        display_simulation_results(df, simulated_df, "Manual Adjustments")

def render_percentage_based_simulation(df: pd.DataFrame):
    """Percentage-based simulation interface"""
    st.markdown("#### Percentage-Based Changes")
    
    # Global adjustment
    st.markdown("**Global Adjustment**")
    global_adjustment = st.slider(
        "Apply percentage change to all departments",
        min_value=-50.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        key="global_pct_adj"
    )
    
    # Department-specific adjustments
    st.markdown("**Department-Specific Adjustments**")
    
    departments = df['Department'].unique()
    dept_adjustments = {}
    
    cols = st.columns(2)
    
    for i, dept in enumerate(departments):
        with cols[i % 2]:
            adj_pct = st.slider(
                f"{dept} Additional Adjustment (%)",
                min_value=-50.0,
                max_value=100.0,
                value=0.0,
                step=1.0,
                key=f"pct_adj_{dept}"
            )
            dept_adjustments[dept] = adj_pct
    
    if st.button("Apply Percentage Changes", type="primary"):
        simulated_df = apply_percentage_adjustments(df, global_adjustment, dept_adjustments)
        display_simulation_results(df, simulated_df, "Percentage-Based Changes")

def render_target_based_simulation(df: pd.DataFrame):
    """Target-based simulation interface"""
    st.markdown("#### Target-Based Planning")
    
    st.markdown("Set target total budget and department priorities:")
    
    current_total = df['Budget'].sum()
    
    # Target total budget
    target_total = st.number_input(
        "Target Total Budget",
        min_value=0.0,
        value=float(current_total),
        step=10000.0,
        key="target_total_budget",
        format="%.0f"
    )
    
    # Department priorities
    st.markdown("**Department Priority Weights**")
    st.markdown("Higher weights = larger budget allocation")
    
    departments = df['Department'].unique()
    priorities = {}
    
    cols = st.columns(2)
    
    for i, dept in enumerate(departments):
        with cols[i % 2]:
            priority = st.slider(
                f"{dept} Priority Weight",
                min_value=0.1,
                max_value=5.0,
                value=1.0,
                step=0.1,
                key=f"priority_{dept}"
            )
            priorities[dept] = priority
    
    if st.button("Calculate Target-Based Budget", type="primary"):
        simulated_df = apply_target_based_allocation(df, target_total, priorities)
        display_simulation_results(df, simulated_df, "Target-Based Planning")

def apply_manual_adjustments(df: pd.DataFrame, adjustments: Dict[str, float]) -> pd.DataFrame:
    """Apply manual budget adjustments"""
    simulated_df = df.copy()
    
    for dept, new_budget in adjustments.items():
        dept_mask = simulated_df['Department'] == dept
        if dept_mask.any():
            # Proportionally adjust all accounts in the department
            current_dept_total = simulated_df.loc[dept_mask, 'Budget'].sum()
            if current_dept_total > 0:
                adjustment_factor = new_budget / current_dept_total
                simulated_df.loc[dept_mask, 'Budget'] *= adjustment_factor
    
    return simulated_df

def apply_percentage_adjustments(df: pd.DataFrame, global_adj: float, dept_adjustments: Dict[str, float]) -> pd.DataFrame:
    """Apply percentage-based adjustments"""
    simulated_df = df.copy()
    
    # Apply global adjustment first
    simulated_df['Budget'] *= (1 + global_adj / 100)
    
    # Apply department-specific adjustments
    for dept, adj_pct in dept_adjustments.items():
        if adj_pct != 0:
            dept_mask = simulated_df['Department'] == dept
            simulated_df.loc[dept_mask, 'Budget'] *= (1 + adj_pct / 100)
    
    return simulated_df

def apply_target_based_allocation(df: pd.DataFrame, target_total: float, priorities: Dict[str, float]) -> pd.DataFrame:
    """Apply target-based budget allocation"""
    simulated_df = df.copy()
    
    # Calculate total priority weight
    total_weight = sum(priorities.values())
    
    # Calculate target budget for each department
    for dept, priority in priorities.items():
        dept_target = target_total * (priority / total_weight)
        dept_mask = simulated_df['Department'] == dept
        
        if dept_mask.any():
            current_dept_total = simulated_df.loc[dept_mask, 'Budget'].sum()
            if current_dept_total > 0:
                adjustment_factor = dept_target / current_dept_total
                simulated_df.loc[dept_mask, 'Budget'] *= adjustment_factor
    
    return simulated_df

def display_simulation_results(original_df: pd.DataFrame, simulated_df: pd.DataFrame, simulation_type: str):
    """Display simulation results"""
    st.markdown(f"### {simulation_type} Results")
    
    # Summary comparison
    original_total = original_df['Budget'].sum()
    simulated_total = simulated_df['Budget'].sum()
    total_change = simulated_total - original_total
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Original Total", format_currency(original_total))
    
    with col2:
        st.metric("Simulated Total", format_currency(simulated_total))
    
    with col3:
        st.metric(
            "Total Change",
            format_currency(total_change),
            delta=format_percentage(total_change / original_total)
        )
    
    # Department comparison
    create_simulation_comparison_table(original_df, simulated_df)
    
    # Visualization
    create_simulation_visualizations(original_df, simulated_df)
    
    # Save simulation option
    if st.button("Save This Simulation"):
        save_simulation_results(original_df, simulated_df, simulation_type)

def create_simulation_comparison_table(original_df: pd.DataFrame, simulated_df: pd.DataFrame):
    """Create department comparison table"""
    st.markdown("#### Department-by-Department Comparison")
    
    # Group by department for comparison
    original_dept = original_df.groupby('Department')['Budget'].sum()
    simulated_dept = simulated_df.groupby('Department')['Budget'].sum()
    
    comparison_data = []
    for dept in original_dept.index:
        original_budget = original_dept[dept]
        simulated_budget = simulated_dept.get(dept, 0)
        change = simulated_budget - original_budget
        change_pct = (change / original_budget * 100) if original_budget > 0 else 0
        
        comparison_data.append({
            'Department': dept,
            'Original Budget': format_currency(original_budget),
            'Simulated Budget': format_currency(simulated_budget),
            'Change ($)': format_currency(change),
            'Change (%)': f"{change_pct:+.1f}%"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True)

def create_simulation_visualizations(original_df: pd.DataFrame, simulated_df: pd.DataFrame):
    """Create visualizations for simulation results"""
    st.markdown("#### Visualization")
    
    # Group data by department
    original_dept = original_df.groupby('Department')['Budget'].sum().reset_index()
    simulated_dept = simulated_df.groupby('Department')['Budget'].sum().reset_index()
    
    # Create comparison chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Original Budget',
        x=original_dept['Department'],
        y=original_dept['Budget'],
        marker_color='lightcoral'
    ))
    
    fig.add_trace(go.Bar(
        name='Simulated Budget',
        x=simulated_dept['Department'],
        y=simulated_dept['Budget'],
        marker_color='lightblue'
    ))
    
    fig.update_layout(
        title='Budget Simulation Comparison',
        xaxis_title='Department',
        yaxis_title='Budget Amount',
        barmode='group',
        height=500
    )
    
    accessible_fig = create_accessible_chart(
        fig,
        "Budget Simulation Comparison",
        "Bar chart comparing original and simulated budgets by department"
    )
    
    st.plotly_chart(accessible_fig, use_container_width=True)

def save_simulation_results(original_df: pd.DataFrame, simulated_df: pd.DataFrame, simulation_type: str):
    """Save simulation results to session state"""
    simulation_data = {
        'type': simulation_type,
        'original_data': original_df.to_dict('records'),
        'simulated_data': simulated_df.to_dict('records'),
        'created_at': datetime.now().isoformat(),
        'created_by': st.session_state.get('user', {}).get('username', 'unknown')
    }
    
    # Initialize saved simulations if not exists
    if 'saved_simulations' not in st.session_state:
        st.session_state.saved_simulations = []
    
    st.session_state.saved_simulations.append(simulation_data)
    st.success(f"Simulation saved! You now have {len(st.session_state.saved_simulations)} saved simulations.")