"""
Scenario Planner Utilities - Shared functions and data operations
"""

import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import json

from modules.database.db_connection import (
    load_org_data,
    save_scenario,
    get_scenarios,
    format_currency,
    format_percentage
)

def load_scenario_data(org: str = "cityA") -> pd.DataFrame:
    """Load scenario data for the organization"""
    try:
        df = load_org_data(org)
        return df
    except Exception as e:
        st.error(f"Error loading scenario data: {str(e)}")
        return pd.DataFrame()

def save_scenario_data(scenario_data: Dict[str, Any]) -> Optional[int]:
    """Save scenario data to database"""
    try:
        scenario_id = save_scenario(scenario_data)
        return scenario_id
    except Exception as e:
        st.error(f"Error saving scenario: {str(e)}")
        return None

def calculate_budget_variance(original_df: pd.DataFrame, modified_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate variance between original and modified budget data"""
    
    # Total variance
    original_total = original_df['Budget'].sum()
    modified_total = modified_df['Budget'].sum()
    total_variance = modified_total - original_total
    total_variance_pct = (total_variance / original_total * 100) if original_total > 0 else 0
    
    # Department-level variance
    original_dept = original_df.groupby('Department')['Budget'].sum()
    modified_dept = modified_df.groupby('Department')['Budget'].sum()
    
    dept_variances = {}
    for dept in original_dept.index:
        original_amt = original_dept[dept]
        modified_amt = modified_dept.get(dept, 0)
        variance = modified_amt - original_amt
        variance_pct = (variance / original_amt * 100) if original_amt > 0 else 0
        
        dept_variances[dept] = {
            'original': original_amt,
            'modified': modified_amt,
            'variance': variance,
            'variance_pct': variance_pct
        }
    
    return {
        'total_original': original_total,
        'total_modified': modified_total,
        'total_variance': total_variance,
        'total_variance_pct': total_variance_pct,
        'department_variances': dept_variances
    }

def generate_scenario_summary(scenario_data: Dict[str, Any], variance_data: Dict[str, Any]) -> str:
    """Generate a summary of the scenario"""
    
    summary_parts = []
    
    # Basic scenario info
    summary_parts.append(f"**Scenario:** {scenario_data.get('name', 'Unnamed Scenario')}")
    summary_parts.append(f"**Created:** {scenario_data.get('created_date', 'Unknown')}")
    summary_parts.append(f"**Created By:** {scenario_data.get('created_by', 'Unknown')}")
    
    # Budget impact
    total_variance = variance_data['total_variance']
    total_variance_pct = variance_data['total_variance_pct']
    
    if total_variance > 0:
        impact_desc = f"increases total budget by {format_currency(total_variance)} ({total_variance_pct:+.1f}%)"
    elif total_variance < 0:
        impact_desc = f"decreases total budget by {format_currency(abs(total_variance))} ({total_variance_pct:+.1f}%)"
    else:
        impact_desc = "maintains current budget levels"
    
    summary_parts.append(f"**Budget Impact:** This scenario {impact_desc}")
    
    # Department impacts
    dept_impacts = []
    for dept, data in variance_data['department_variances'].items():
        if abs(data['variance']) > 1000:  # Only show significant changes
            change_desc = f"{dept}: {format_currency(data['variance'])} ({data['variance_pct']:+.1f}%)"
            dept_impacts.append(change_desc)
    
    if dept_impacts:
        summary_parts.append("**Key Department Changes:**")
        for impact in dept_impacts[:5]:  # Show top 5 changes
            summary_parts.append(f"  • {impact}")
    
    return "\n".join(summary_parts)

def validate_scenario_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate scenario data for consistency and completeness"""
    errors = []
    
    # Check required columns
    required_columns = ['Department', 'Budget']
    for col in required_columns:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    # Check for negative budgets
    if 'Budget' in df.columns:
        negative_budgets = df[df['Budget'] < 0]
        if not negative_budgets.empty:
            errors.append(f"Found {len(negative_budgets)} records with negative budgets")
    
    # Check for missing department names
    if 'Department' in df.columns:
        missing_depts = df[df['Department'].isna() | (df['Department'] == '')]
        if not missing_depts.empty:
            errors.append(f"Found {len(missing_depts)} records with missing department names")
    
    # Check for duplicate department entries (if not expected)
    if 'Department' in df.columns and len(df) > 0:
        dept_counts = df['Department'].value_counts()
        if dept_counts.max() > 10:  # Arbitrary threshold
            errors.append("Some departments have unusually high number of budget lines")
    
    return len(errors) == 0, errors

def export_scenario_comparison(scenarios: List[Dict[str, Any]], format_type: str = "csv") -> bytes:
    """Export scenario comparison data"""
    
    if not scenarios:
        return b""
    
    # Prepare comparison data
    comparison_data = []
    
    for scenario in scenarios:
        scenario_info = {
            'Scenario_Name': scenario.get('name', 'Unnamed'),
            'Created_Date': scenario.get('created_date', ''),
            'Created_By': scenario.get('created_by', ''),
            'Total_Budget': scenario.get('total_budget', 0),
            'Total_Variance': scenario.get('total_variance', 0),
            'Variance_Percentage': scenario.get('variance_percentage', 0)
        }
        
        # Add department data if available
        if 'department_data' in scenario:
            for dept, data in scenario['department_data'].items():
                scenario_info[f'{dept}_Budget'] = data.get('budget', 0)
                scenario_info[f'{dept}_Variance'] = data.get('variance', 0)
        
        comparison_data.append(scenario_info)
    
    df = pd.DataFrame(comparison_data)
    
    if format_type.lower() == "csv":
        return df.to_csv(index=False).encode('utf-8')
    elif format_type.lower() == "json":
        return df.to_json(orient='records', indent=2).encode('utf-8')
    else:
        return df.to_csv(index=False).encode('utf-8')

def get_scenario_templates() -> List[Dict[str, Any]]:
    """Get predefined scenario templates"""
    
    templates = [
        {
            'name': 'Budget Reduction (5%)',
            'description': 'Reduce all department budgets by 5%',
            'adjustments': {'global_reduction': 5.0},
            'category': 'Cost Reduction'
        },
        {
            'name': 'Public Safety Focus',
            'description': 'Increase Police and Fire budgets by 10%, reduce others by 3%',
            'adjustments': {
                'Police': 10.0,
                'Fire': 10.0,
                'other_departments': -3.0
            },
            'category': 'Reallocation'
        },
        {
            'name': 'Infrastructure Investment',
            'description': 'Increase Public Works by 15%, maintain others',
            'adjustments': {'Public Works': 15.0},
            'category': 'Investment'
        },
        {
            'name': 'Balanced Growth',
            'description': 'Increase all departments by 3%',
            'adjustments': {'global_increase': 3.0},
            'category': 'Growth'
        },
        {
            'name': 'Emergency Response',
            'description': 'Major increase in emergency services funding',
            'adjustments': {
                'Police': 20.0,
                'Fire': 25.0,
                'Emergency Management': 30.0
            },
            'category': 'Emergency'
        }
    ]
    
    return templates

def apply_scenario_template(df: pd.DataFrame, template: Dict[str, Any]) -> pd.DataFrame:
    """Apply a scenario template to budget data"""
    
    modified_df = df.copy()
    adjustments = template.get('adjustments', {})
    
    for key, adjustment in adjustments.items():
        if key == 'global_reduction':
            # Apply reduction to all departments
            modified_df['Budget'] *= (1 - adjustment / 100)
        elif key == 'global_increase':
            # Apply increase to all departments
            modified_df['Budget'] *= (1 + adjustment / 100)
        elif key == 'other_departments':
            # Apply to departments not specifically mentioned
            specific_depts = [k for k in adjustments.keys() if k not in ['global_reduction', 'global_increase', 'other_departments']]
            other_mask = ~modified_df['Department'].isin(specific_depts)
            modified_df.loc[other_mask, 'Budget'] *= (1 + adjustment / 100)
        else:
            # Apply to specific department
            dept_mask = modified_df['Department'] == key
            if dept_mask.any():
                modified_df.loc[dept_mask, 'Budget'] *= (1 + adjustment / 100)
    
    return modified_df

def get_scenario_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate key metrics for a scenario"""
    
    metrics = {}
    
    if not df.empty and 'Budget' in df.columns:
        metrics['total_budget'] = df['Budget'].sum()
        metrics['department_count'] = df['Department'].nunique()
        metrics['average_department_budget'] = df.groupby('Department')['Budget'].sum().mean()
        metrics['largest_department'] = df.groupby('Department')['Budget'].sum().idxmax()
        metrics['largest_department_amount'] = df.groupby('Department')['Budget'].sum().max()
        metrics['smallest_department'] = df.groupby('Department')['Budget'].sum().idxmin()
        metrics['smallest_department_amount'] = df.groupby('Department')['Budget'].sum().min()
        
        # Budget distribution
        dept_budgets = df.groupby('Department')['Budget'].sum().sort_values(ascending=False)
        top_3_pct = (dept_budgets.head(3).sum() / dept_budgets.sum() * 100)
        metrics['top_3_departments_percentage'] = top_3_pct
    
    return metrics

def create_scenario_snapshot(df: pd.DataFrame, name: str, description: str = "") -> Dict[str, Any]:
    """Create a snapshot of current scenario state"""
    
    snapshot = {
        'name': name,
        'description': description,
        'created_date': datetime.now().isoformat(),
        'created_by': st.session_state.get('user', {}).get('username', 'unknown'),
        'data': df.to_dict('records'),
        'metrics': get_scenario_metrics(df),
        'department_summary': df.groupby('Department')['Budget'].sum().to_dict()
    }
    
    return snapshot