"""
Scenario Builder - Main funding scenario creation and analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List, Tuple
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.ai_hub.ai_hub import ask_ai, simulate_adjustment
from modules.utils.mask_parser import get_mask_from_settings, parse_account
from modules.utils.anomaly_detection_module import render_anomaly_analysis
from modules.utils.accessibility_helper import create_accessible_chart

from modules.database.db_connection import (
    get_departments, 
    get_projects, 
    save_scenario, 
    get_scenarios,
    format_currency,
    format_percentage,
    load_org_data,
    get_connection,
    get_db_path_for_org
)

# Try to import enhanced scenario builder
try:
    from modules.scenario_planner.enhanced_scenario_builder import render_enhanced_scenario_builder
    HAS_ENHANCED_BUILDER = True
except ImportError:
    HAS_ENHANCED_BUILDER = False

def render_scenario_builder():
    """Main scenario builder interface"""
    # Check if enhanced mode is enabled
    if HAS_ENHANCED_BUILDER:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader("Scenario Builder")
        with col2:
            enhanced_mode = st.checkbox("Enhanced Mode", value=True, help="Enable advanced features like multi-year forecasting, Monte Carlo analysis, and report generation")
        
        if enhanced_mode:
            render_enhanced_scenario_builder()
            return
    else:
        st.subheader("Scenario Builder")
    
    # Get organization data
    org = st.session_state.get('selected_org', 'cityA')
    org_display_name = st.session_state.get('org_display_name', 'City A')
    
    # Load data
    df = load_org_data(org)
    
    if df.empty:
        st.warning(f"No budget data found for {org_display_name}")
        return
    
    # Project selection
    st.markdown("#### Step 1: Project Selection")
    projects = get_projects(org)
    
    if projects:
        selected_project = st.selectbox(
            "Select a project to analyze",
            options=projects,
            key="scenario_project_select"
        )
    else:
        st.info("No projects found. Creating a general scenario.")
        selected_project = "General Budget Analysis"
    
    # Department budget reallocation
    st.markdown("#### Step 2: Department Budget Adjustments")
    
    # Get departments from data
    departments = df['Department'].unique().tolist()
    
    # Create adjustment inputs
    adjustments = {}
    cols = st.columns(2)
    
    for i, dept in enumerate(departments):
        with cols[i % 2]:
            current_budget = df[df['Department'] == dept]['Budget'].sum()
            
            adjustment = st.number_input(
                f"{dept} Budget Adjustment (%)",
                min_value=-50.0,
                max_value=200.0,
                value=0.0,
                step=5.0,
                key=f"adj_{dept}",
                help=f"Current budget: {format_currency(current_budget)}"
            )
            adjustments[dept] = adjustment
    
    # Funding source allocation
    st.markdown("#### Step 3: Funding Source Configuration")
    
    funding_cols = st.columns(3)
    with funding_cols[0]:
        federal_pct = st.slider("Federal Funding %", 0, 100, 30, key="federal_funding")
    with funding_cols[1]:
        state_pct = st.slider("State Funding %", 0, 100, 25, key="state_funding")
    with funding_cols[2]:
        local_pct = st.slider("Local Funding %", 0, 100, 45, key="local_funding")
    
    total_funding = federal_pct + state_pct + local_pct
    if total_funding != 100:
        st.warning(f"Funding percentages total {total_funding}%. Please adjust to equal 100%.")
    
    # Calculate scenario
    if st.button("Generate Scenario Analysis", type="primary"):
        scenario_results = calculate_scenario_impact(df, adjustments, {
            'federal': federal_pct,
            'state': state_pct,
            'local': local_pct
        })
        
        # Display results
        display_scenario_results(scenario_results, df, adjustments)
        
        # Save scenario option
        if st.button("Save This Scenario"):
            save_scenario_to_db(selected_project, adjustments, scenario_results)

def calculate_scenario_impact(df: pd.DataFrame, adjustments: Dict[str, float], funding_sources: Dict[str, float]) -> Dict[str, Any]:
    """Calculate the impact of scenario adjustments"""
    results = {
        'original_data': df.copy(),
        'adjusted_data': df.copy(),
        'adjustments': adjustments,
        'funding_sources': funding_sources,
        'total_impact': 0,
        'department_impacts': {}
    }
    
    # Apply adjustments
    for dept, adj_pct in adjustments.items():
        if adj_pct != 0:
            mask = results['adjusted_data']['Department'] == dept
            original_budget = results['adjusted_data'].loc[mask, 'Budget'].sum()
            adjustment_amount = original_budget * (adj_pct / 100)
            
            results['adjusted_data'].loc[mask, 'Budget'] *= (1 + adj_pct / 100)
            results['department_impacts'][dept] = {
                'original_budget': original_budget,
                'adjustment_pct': adj_pct,
                'adjustment_amount': adjustment_amount,
                'new_budget': original_budget + adjustment_amount
            }
            results['total_impact'] += adjustment_amount
    
    return results

def display_scenario_results(results: Dict[str, Any], original_df: pd.DataFrame, adjustments: Dict[str, float]):
    """Display scenario analysis results"""
    st.markdown("### Scenario Analysis Results")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    original_total = original_df['Budget'].sum()
    adjusted_total = results['adjusted_data']['Budget'].sum()
    total_variance = adjusted_total - original_total
    
    with col1:
        st.metric("Original Budget", format_currency(original_total))
    with col2:
        st.metric("Adjusted Budget", format_currency(adjusted_total))
    with col3:
        st.metric("Total Variance", format_currency(total_variance), 
                 delta=format_percentage(total_variance / original_total))
    
    # Department impact table
    if results['department_impacts']:
        st.markdown("#### Department Impact Analysis")
        
        impact_data = []
        for dept, impact in results['department_impacts'].items():
            impact_data.append({
                'Department': dept,
                'Original Budget': format_currency(impact['original_budget']),
                'Adjustment %': f"{impact['adjustment_pct']:.1f}%",
                'Adjustment Amount': format_currency(impact['adjustment_amount']),
                'New Budget': format_currency(impact['new_budget'])
            })
        
        impact_df = pd.DataFrame(impact_data)
        st.dataframe(impact_df, use_container_width=True)
    
    # Visualization
    create_scenario_visualizations(results)

def create_scenario_visualizations(results: Dict[str, Any]):
    """Create visualizations for scenario analysis"""
    st.markdown("#### Budget Comparison Visualization")
    
    # Prepare data for visualization
    original_data = results['original_data'].groupby('Department')['Budget'].sum().reset_index()
    adjusted_data = results['adjusted_data'].groupby('Department')['Budget'].sum().reset_index()
    
    # Create comparison chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Original Budget',
        x=original_data['Department'],
        y=original_data['Budget'],
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Adjusted Budget',
        x=adjusted_data['Department'],
        y=adjusted_data['Budget'],
        marker_color='darkblue'
    ))
    
    fig.update_layout(
        title='Budget Comparison: Original vs Adjusted',
        xaxis_title='Department',
        yaxis_title='Budget Amount',
        barmode='group',
        height=500
    )
    
    # Use accessibility helper
    accessible_fig = create_accessible_chart(
        fig, 
        "Budget Comparison Chart",
        "Comparison of original and adjusted budgets by department"
    )
    
    st.plotly_chart(accessible_fig, use_container_width=True)
    
    # Funding source pie chart
    if results['funding_sources']:
        st.markdown("#### Funding Source Distribution")
        
        funding_fig = go.Figure(data=[go.Pie(
            labels=list(results['funding_sources'].keys()),
            values=list(results['funding_sources'].values()),
            hole=0.3
        )])
        
        funding_fig.update_layout(
            title='Funding Source Distribution',
            height=400
        )
        
        accessible_funding_fig = create_accessible_chart(
            funding_fig,
            "Funding Source Distribution",
            "Pie chart showing the distribution of funding sources"
        )
        
        st.plotly_chart(accessible_funding_fig, use_container_width=True)

def save_scenario_to_db(project_name: str, adjustments: Dict[str, float], results: Dict[str, Any]):
    """Save scenario to database"""
    try:
        scenario_data = {
            'project_name': project_name,
            'adjustments': adjustments,
            'funding_sources': results['funding_sources'],
            'total_impact': results['total_impact'],
            'department_impacts': results['department_impacts'],
            'created_by': st.session_state.get('user', {}).get('username', 'unknown'),
            'created_date': datetime.now().isoformat()
        }
        
        scenario_id = save_scenario(scenario_data)
        
        if scenario_id:
            st.success(f"Scenario saved successfully! ID: {scenario_id}")
        else:
            st.error("Failed to save scenario")
            
    except Exception as e:
        st.error(f"Error saving scenario: {str(e)}")