"""
Scenario Manager for Admin Panel

This module provides administrative functions for managing scenarios,
integrating with the scenario planner database and AI proposal generator.
"""

import streamlit as st
import pandas as pd
import json
import sqlite3
from datetime import datetime
import sys
import os

# Add modules to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.database.scenarios_db import (
    get_all_scenarios,
    get_scenario,
    delete_scenario,
    get_scenario_proposals,
    init_scenarios_database
)

def render_scenario_manager():
    """Render the scenario management interface in admin panel"""
    
    st.markdown("### 📊 Scenario Manager")
    st.markdown("Manage and review all saved budget scenarios from the Scenario Planner")
    
    # Initialize database if needed
    init_scenarios_database()
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["📋 All Scenarios", "🤖 AI Proposals", "📈 Analytics"])
    
    with tab1:
        render_scenarios_list()
    
    with tab2:
        render_ai_proposals()
    
    with tab3:
        render_scenario_analytics()

def render_scenarios_list():
    """Display list of all scenarios with management options"""
    
    # Get all scenarios from database
    scenarios = get_all_scenarios()
    
    if not scenarios:
        st.info("No scenarios found. Create scenarios using the Scenario Planner in the Navi module.")
        return
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Scenarios", len(scenarios))
    with col2:
        draft_count = len([s for s in scenarios if s.get('status') == 'draft'])
        st.metric("Draft", draft_count)
    with col3:
        approved_count = len([s for s in scenarios if s.get('status') == 'approved'])
        st.metric("Approved", approved_count)
    with col4:
        total_value = sum([sum(s.get('costs', [])) for s in scenarios])
        st.metric("Total Value", f"${total_value:,.0f}")
    
    st.markdown("---")
    
    # Display scenarios in a table format
    for idx, scenario in enumerate(scenarios):
        with st.expander(f"📄 {scenario.get('name', 'Untitled')} - {scenario.get('status', 'draft').upper()}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**ID:** `{scenario.get('id')}`")
                st.markdown(f"**Description:** {scenario.get('description', 'No description')}")
                st.markdown(f"**Years:** {scenario.get('years', 3)}")
                st.markdown(f"**Created:** {scenario.get('created_at', 'Unknown')}")
                st.markdown(f"**Modified:** {scenario.get('modified_at', 'Unknown')}")
                
                # Display costs
                costs = scenario.get('costs', [])
                if costs:
                    st.markdown("**Annual Costs:**")
                    for i, cost in enumerate(costs):
                        st.write(f"  Year {i+1}: ${cost:,.0f}")
                
                # Display funding sources
                funding_sources = scenario.get('funding_sources', [])
                if funding_sources:
                    st.markdown("**Funding Sources:**")
                    for source in funding_sources:
                        st.write(f"  - {source.get('name', 'Unknown')}: ${source.get('amount', 0):,.0f} ({source.get('type', 'Unknown')})")
                
                # Display departments
                departments = scenario.get('departments', [])
                if departments:
                    st.markdown("**Department Allocations:**")
                    for dept in departments:
                        st.write(f"  - {dept.get('name', 'Unknown')}: ${dept.get('allocation', 0):,.0f}")
            
            with col2:
                st.markdown("**Actions:**")
                
                # View in Scenario Planner button
                if st.button(f"View Details", key=f"view_{scenario['id']}"):
                    st.session_state['selected_scenario_id'] = scenario['id']
                    st.info(f"Selected scenario: {scenario['name']}")
                
                # Change status
                new_status = st.selectbox(
                    "Status", 
                    ["draft", "review", "approved", "rejected"],
                    index=["draft", "review", "approved", "rejected"].index(scenario.get('status', 'draft')),
                    key=f"status_{scenario['id']}"
                )
                if new_status != scenario.get('status'):
                    if st.button(f"Update Status", key=f"update_status_{scenario['id']}"):
                        update_scenario_status(scenario['id'], new_status)
                        st.success(f"Status updated to {new_status}")
                        st.rerun()
                
                # Delete button
                if st.button(f"🗑️ Delete", key=f"delete_{scenario['id']}"):
                    if delete_scenario(scenario['id']):
                        st.success(f"Scenario '{scenario['name']}' deleted")
                        st.rerun()
                    else:
                        st.error("Failed to delete scenario")

def render_ai_proposals():
    """Display AI-generated proposals for scenarios"""
    
    scenarios = get_all_scenarios()
    
    if not scenarios:
        st.info("No scenarios found. Create scenarios first to generate AI proposals.")
        return
    
    # Select a scenario
    scenario_names = [s.get('name', 'Untitled') + f" ({s.get('id')[:8]}...)" for s in scenarios]
    selected_idx = st.selectbox("Select Scenario", range(len(scenarios)), format_func=lambda x: scenario_names[x])
    
    if selected_idx is not None:
        selected_scenario = scenarios[selected_idx]
        
        st.markdown(f"### Proposals for: {selected_scenario.get('name')}")
        
        # Get AI proposals for this scenario
        proposals = get_scenario_proposals(selected_scenario['id'])
        
        if not proposals:
            st.info("No AI proposals generated for this scenario yet.")
            st.markdown("Use the AI features in the Scenario Planner to generate:")
            st.markdown("- Legislative impact analysis")
            st.markdown("- What-if simulations")
            st.markdown("- Optimization recommendations")
        else:
            for proposal in proposals:
                with st.expander(f"🤖 {proposal.get('proposal_type', 'Unknown').title()} - {proposal.get('created_at', 'Unknown')[:10]}"):
                    st.markdown(f"**Type:** {proposal.get('proposal_type')}")
                    st.markdown(f"**Confidence Score:** {proposal.get('confidence_score', 0):.2%}")
                    st.markdown(f"**Created:** {proposal.get('created_at')}")
                    
                    st.markdown("**Input Parameters:**")
                    st.json(proposal.get('input_params', {}))
                    
                    st.markdown("**Output Result:**")
                    st.json(proposal.get('output_result', {}))

def render_scenario_analytics():
    """Display analytics and insights for scenarios"""
    
    scenarios = get_all_scenarios()
    
    if not scenarios:
        st.info("No scenarios found for analytics.")
        return
    
    # Prepare data for analytics
    df_data = []
    for s in scenarios:
        total_cost = sum(s.get('costs', []))
        num_funding_sources = len(s.get('funding_sources', []))
        num_departments = len(s.get('departments', []))
        
        df_data.append({
            'Name': s.get('name', 'Untitled'),
            'Status': s.get('status', 'draft'),
            'Years': s.get('years', 3),
            'Total Cost': total_cost,
            'Funding Sources': num_funding_sources,
            'Departments': num_departments,
            'Created': s.get('created_at', '')[:10],
            'Modified': s.get('modified_at', '')[:10]
        })
    
    df = pd.DataFrame(df_data)
    
    if not df.empty:
        st.markdown("### Scenario Overview")
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Scenario Cost", f"${df['Total Cost'].mean():,.0f}")
        with col2:
            st.metric("Max Scenario Cost", f"${df['Total Cost'].max():,.0f}")
        with col3:
            st.metric("Min Scenario Cost", f"${df['Total Cost'].min():,.0f}")
        
        # Display table
        st.markdown("### All Scenarios Table")
        st.dataframe(df, use_container_width=True)
        
        # Charts
        st.markdown("### Scenario Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Status distribution
            status_counts = df['Status'].value_counts()
            st.bar_chart(status_counts)
            st.caption("Scenarios by Status")
        
        with col2:
            # Cost distribution
            st.bar_chart(df.set_index('Name')['Total Cost'])
            st.caption("Total Cost by Scenario")
        
        # Export functionality
        st.markdown("### Export Data")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Scenarios as CSV",
            data=csv,
            file_name=f"scenarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv'
        )

def update_scenario_status(scenario_id: str, new_status: str):
    """Update the status of a scenario in the database"""
    try:
        conn = sqlite3.connect("databases/core/scenarios.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE scenarios 
            SET status = ?, modified_at = ?
            WHERE id = ?
        """, (new_status, datetime.now().isoformat(), scenario_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating scenario status: {e}")
        return False