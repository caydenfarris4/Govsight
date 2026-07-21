"""
Enhanced Scenario Builder - Advanced funding scenario creation with multi-year forecasting,
dynamic funding sources, Monte Carlo risk analysis, and comprehensive reporting
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import json
import sqlite3
from io import BytesIO
import base64

# Import system modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import existing modules
from modules.ai_hub.ai_hub import ask_ai, simulate_adjustment
from modules.utils.mask_parser import get_mask_from_settings, parse_account
from modules.utils.anomaly_detection_module import render_anomaly_analysis
from modules.utils.accessibility_helper import create_accessible_chart
from modules.navi.monte_carlo_simulator import run_optimized_monte_carlo
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

# Import report generation libraries
try:
    from fpdf2 import FPDF
    HAS_FPDF = True
except ImportError:
    try:
        from fpdf import FPDF
        HAS_FPDF = True
    except ImportError:
        HAS_FPDF = False
        # Don't show warning at import time - only when PDF generation is actually used

class EnhancedScenarioBuilder:
    """Enhanced scenario builder with advanced features"""
    
    def __init__(self):
        # Initialize session state for dynamic funding sources
        if 'funding_sources' not in st.session_state:
            st.session_state.funding_sources = []
        if 'scenarios_for_comparison' not in st.session_state:
            st.session_state.scenarios_for_comparison = []
        if 'multi_year_data' not in st.session_state:
            st.session_state.multi_year_data = {}
    
    def render(self):
        """Main render method for enhanced scenario builder"""
        st.subheader("🎯 Enhanced Scenario Builder")
        
        # Create tabs for different features
        tabs = st.tabs([
            "📊 Multi-Year Forecast",
            "💰 Dynamic Funding",
            "📈 Risk Analysis",
            "📄 Report Generation",
            "🔄 Scenario Comparison"
        ])
        
        with tabs[0]:
            self.render_multi_year_forecast()
        
        with tabs[1]:
            self.render_dynamic_funding()
        
        with tabs[2]:
            self.render_risk_analysis()
        
        with tabs[3]:
            self.render_report_generation()
        
        with tabs[4]:
            self.render_scenario_comparison()
    
    def render_multi_year_forecast(self):
        """Render multi-year forecasting interface"""
        st.markdown("### Multi-Year Budget Forecasting")
        
        # Get organization data
        org = st.session_state.get('selected_org', 'cityA')
        org_display_name = st.session_state.get('org_display_name', 'City A')
        
        # Load base data
        df = load_org_data(org)
        if df.empty:
            st.warning(f"No budget data found for {org_display_name}")
            return
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Year selector
            forecast_years = st.slider(
                "Forecast Horizon (Years)",
                min_value=1,
                max_value=5,
                value=3,
                help="Select the number of years to forecast"
            )
        
        with col2:
            # Base year selection
            current_year = datetime.now().year
            base_year = st.number_input(
                "Base Year",
                min_value=current_year - 5,
                max_value=current_year,
                value=current_year,
                help="Starting year for the forecast"
            )
        
        with col3:
            # Inflation rate
            inflation_rate = st.number_input(
                "Annual Inflation Rate (%)",
                min_value=0.0,
                max_value=10.0,
                value=2.5,
                step=0.1,
                help="Expected annual inflation rate"
            )
        
        st.markdown("#### Department Growth Rates")
        
        # Create growth rate inputs for each department
        departments = df['Department'].unique().tolist()
        growth_rates = {}
        
        # Create a more compact layout with expander
        with st.expander("Configure Department Growth Rates", expanded=True):
            cols = st.columns(3)
            for i, dept in enumerate(departments):
                with cols[i % 3]:
                    growth_rates[dept] = st.number_input(
                        f"{dept} (%/year)",
                        min_value=-10.0,
                        max_value=20.0,
                        value=3.0,
                        step=0.5,
                        key=f"growth_{dept}"
                    )
        
        # Additional forecast parameters
        st.markdown("#### Forecast Parameters")
        col1, col2 = st.columns(2)
        
        with col1:
            revenue_growth = st.number_input(
                "Revenue Growth Rate (%/year)",
                min_value=-10.0,
                max_value=20.0,
                value=2.0,
                step=0.5,
                help="Expected annual revenue growth"
            )
        
        with col2:
            cost_escalation = st.number_input(
                "Cost Escalation Rate (%/year)",
                min_value=0.0,
                max_value=15.0,
                value=3.0,
                step=0.5,
                help="Expected annual cost increases"
            )
        
        # Generate forecast button
        if st.button("Generate Multi-Year Forecast", type="primary"):
            with st.spinner("Generating forecast..."):
                forecast_data = self.generate_multi_year_forecast(
                    df, forecast_years, base_year, inflation_rate,
                    growth_rates, revenue_growth, cost_escalation
                )
                
                # Store in session state
                st.session_state.multi_year_data = forecast_data
                
                # Display results
                self.display_multi_year_results(forecast_data)
    
    def generate_multi_year_forecast(self, df, years, base_year, inflation, 
                                    growth_rates, revenue_growth, cost_escalation):
        """Generate multi-year forecast data"""
        forecast = {
            'years': [],
            'departments': {},
            'totals': {
                'budget': [],
                'revenue': [],
                'costs': [],
                'surplus_deficit': []
            },
            'cumulative_impact': 0,
            'year_over_year': []
        }
        
        # Initialize base values
        base_budget = df['Budget'].sum()
        base_revenue = base_budget * 0.95  # Assume 95% revenue coverage initially
        base_costs = base_budget
        
        for year in range(years):
            current_year = base_year + year
            forecast['years'].append(current_year)
            
            # Calculate year-specific values
            year_multiplier = (1 + inflation/100) ** year
            revenue_multiplier = (1 + revenue_growth/100) ** year
            cost_multiplier = (1 + cost_escalation/100) ** year
            
            # Calculate department budgets
            year_total = 0
            for dept in growth_rates:
                dept_base = df[df['Department'] == dept]['Budget'].sum()
                dept_growth_multiplier = (1 + growth_rates[dept]/100) ** year
                dept_budget = dept_base * dept_growth_multiplier * year_multiplier
                
                if dept not in forecast['departments']:
                    forecast['departments'][dept] = []
                forecast['departments'][dept].append(dept_budget)
                year_total += dept_budget
            
            # Calculate totals
            year_revenue = base_revenue * revenue_multiplier
            year_costs = base_costs * cost_multiplier
            year_surplus = year_revenue - year_costs
            
            forecast['totals']['budget'].append(year_total)
            forecast['totals']['revenue'].append(year_revenue)
            forecast['totals']['costs'].append(year_costs)
            forecast['totals']['surplus_deficit'].append(year_surplus)
            
            # Calculate year-over-year change
            if year > 0:
                yoy_change = ((year_total - forecast['totals']['budget'][year-1]) / 
                             forecast['totals']['budget'][year-1]) * 100
                forecast['year_over_year'].append(yoy_change)
            else:
                forecast['year_over_year'].append(0)
        
        # Calculate cumulative impact
        forecast['cumulative_impact'] = sum(forecast['totals']['budget']) - (base_budget * years)
        
        return forecast
    
    def display_multi_year_results(self, forecast_data):
        """Display multi-year forecast results"""
        st.markdown("### 📊 Multi-Year Forecast Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Budget Growth",
                format_currency(forecast_data['totals']['budget'][-1] - forecast_data['totals']['budget'][0]),
                delta=f"{((forecast_data['totals']['budget'][-1] / forecast_data['totals']['budget'][0]) - 1) * 100:.1f}%"
            )
        
        with col2:
            st.metric(
                "Cumulative Impact",
                format_currency(forecast_data['cumulative_impact'])
            )
        
        with col3:
            avg_yoy = np.mean(forecast_data['year_over_year'][1:]) if len(forecast_data['year_over_year']) > 1 else 0
            st.metric(
                "Avg Annual Growth",
                f"{avg_yoy:.1f}%"
            )
        
        with col4:
            final_surplus = forecast_data['totals']['surplus_deficit'][-1]
            st.metric(
                "Final Year Balance",
                format_currency(abs(final_surplus)),
                delta="Surplus" if final_surplus > 0 else "Deficit"
            )
        
        # Timeline visualization
        st.markdown("#### Budget Timeline")
        fig_timeline = go.Figure()
        
        # Add budget line
        fig_timeline.add_trace(go.Scatter(
            x=forecast_data['years'],
            y=forecast_data['totals']['budget'],
            mode='lines+markers',
            name='Total Budget',
            line=dict(color='blue', width=3),
            marker=dict(size=8)
        ))
        
        # Add revenue line
        fig_timeline.add_trace(go.Scatter(
            x=forecast_data['years'],
            y=forecast_data['totals']['revenue'],
            mode='lines+markers',
            name='Revenue',
            line=dict(color='green', width=2),
            marker=dict(size=6)
        ))
        
        # Add costs line
        fig_timeline.add_trace(go.Scatter(
            x=forecast_data['years'],
            y=forecast_data['totals']['costs'],
            mode='lines+markers',
            name='Costs',
            line=dict(color='red', width=2),
            marker=dict(size=6)
        ))
        
        fig_timeline.update_layout(
            title="Multi-Year Financial Projection",
            xaxis_title="Year",
            yaxis_title="Amount ($)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Department breakdown
        st.markdown("#### Department Budget Projections")
        
        # Create department projection chart
        fig_dept = go.Figure()
        
        for dept, values in forecast_data['departments'].items():
            fig_dept.add_trace(go.Scatter(
                x=forecast_data['years'],
                y=values,
                mode='lines+markers',
                name=dept,
                stackgroup='one'
            ))
        
        fig_dept.update_layout(
            title="Department Budget Projections (Stacked)",
            xaxis_title="Year",
            yaxis_title="Budget ($)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_dept, use_container_width=True)
        
        # Tabular view
        with st.expander("View Detailed Data Table"):
            # Create DataFrame for display
            table_data = {
                'Year': forecast_data['years'],
                'Total Budget': [format_currency(x) for x in forecast_data['totals']['budget']],
                'Revenue': [format_currency(x) for x in forecast_data['totals']['revenue']],
                'Costs': [format_currency(x) for x in forecast_data['totals']['costs']],
                'Balance': [format_currency(x) for x in forecast_data['totals']['surplus_deficit']],
                'YoY Change': [f"{x:.1f}%" for x in forecast_data['year_over_year']]
            }
            
            df_table = pd.DataFrame(table_data)
            st.dataframe(df_table, use_container_width=True, hide_index=True)
    
    def render_dynamic_funding(self):
        """Render dynamic funding sources interface"""
        st.markdown("### 💰 Dynamic Funding Sources")
        
        # Add funding source button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Add Funding Source", type="primary"):
                st.session_state.funding_sources.append({
                    'id': len(st.session_state.funding_sources),
                    'name': f"Source {len(st.session_state.funding_sources) + 1}",
                    'amount': 0,
                    'type': 'grant',
                    'certainty': 50,
                    'dependencies': [],
                    'notes': ''
                })
        
        # Display existing funding sources
        if st.session_state.funding_sources:
            total_funding = 0
            weighted_certainty = 0
            
            for i, source in enumerate(st.session_state.funding_sources):
                with st.expander(f"💵 {source['name']}", expanded=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        source['name'] = st.text_input(
                            "Source Name",
                            value=source['name'],
                            key=f"source_name_{i}"
                        )
                    
                    with col2:
                        source['amount'] = st.number_input(
                            "Amount ($)",
                            min_value=0,
                            value=source['amount'],
                            step=10000,
                            key=f"source_amount_{i}"
                        )
                    
                    with col3:
                        source['type'] = st.selectbox(
                            "Type",
                            options=['grant', 'tax', 'bond', 'donation', 'loan', 'other'],
                            index=['grant', 'tax', 'bond', 'donation', 'loan', 'other'].index(source['type']),
                            key=f"source_type_{i}"
                        )
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        source['certainty'] = st.slider(
                            "Certainty (%)",
                            min_value=0,
                            max_value=100,
                            value=source['certainty'],
                            key=f"source_certainty_{i}"
                        )
                    
                    with col2:
                        # Dependencies selector
                        other_sources = [s['name'] for j, s in enumerate(st.session_state.funding_sources) if j != i]
                        source['dependencies'] = st.multiselect(
                            "Dependencies (requires these sources)",
                            options=other_sources,
                            default=source.get('dependencies', []),
                            key=f"source_deps_{i}"
                        )
                    
                    with col3:
                        if st.button("🗑️ Remove", key=f"remove_{i}"):
                            st.session_state.funding_sources.pop(i)
                            st.rerun()
                    
                    # Notes field
                    source['notes'] = st.text_area(
                        "Notes",
                        value=source.get('notes', ''),
                        key=f"source_notes_{i}",
                        height=60
                    )
                    
                    # Update totals
                    total_funding += source['amount']
                    weighted_certainty += source['amount'] * source['certainty']
            
            # Calculate total funding probability
            st.markdown("---")
            st.markdown("### Funding Summary")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Funding", format_currency(total_funding))
            
            with col2:
                avg_certainty = weighted_certainty / total_funding if total_funding > 0 else 0
                st.metric("Weighted Certainty", f"{avg_certainty:.1f}%")
            
            with col3:
                # Calculate expected value
                expected_value = sum(s['amount'] * s['certainty'] / 100 for s in st.session_state.funding_sources)
                st.metric("Expected Value", format_currency(expected_value))
            
            # Dependency analysis
            if any(s['dependencies'] for s in st.session_state.funding_sources):
                st.markdown("#### Dependency Analysis")
                
                # Check for circular dependencies
                circular = self.check_circular_dependencies()
                if circular:
                    st.error(f"⚠️ Circular dependency detected: {' → '.join(circular)}")
                else:
                    st.success("✅ No circular dependencies detected")
                
                # Calculate cascading probability
                cascading_prob = self.calculate_cascading_probability()
                st.info(f"Cascading Success Probability: {cascading_prob:.1f}%")
            
            # Funding visualization
            if st.session_state.funding_sources:
                fig = self.create_funding_visualization()
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No funding sources added yet. Click 'Add Funding Source' to begin.")
    
    def check_circular_dependencies(self):
        """Check for circular dependencies in funding sources"""
        def has_cycle_util(node, visited, rec_stack, adj_list):
            visited[node] = True
            rec_stack[node] = True
            
            for neighbor in adj_list.get(node, []):
                if not visited.get(neighbor, False):
                    if has_cycle_util(neighbor, visited, rec_stack, adj_list):
                        return True
                elif rec_stack.get(neighbor, False):
                    return True
            
            rec_stack[node] = False
            return False
        
        # Build adjacency list
        adj_list = {}
        for source in st.session_state.funding_sources:
            adj_list[source['name']] = source['dependencies']
        
        visited = {}
        rec_stack = {}
        
        for source in st.session_state.funding_sources:
            if not visited.get(source['name'], False):
                if has_cycle_util(source['name'], visited, rec_stack, adj_list):
                    return [source['name']]  # Simplified return for now
        
        return None
    
    def calculate_cascading_probability(self):
        """Calculate probability considering dependencies"""
        # Simplified calculation - can be enhanced with more sophisticated algorithms
        total_prob = 1.0
        
        for source in st.session_state.funding_sources:
            source_prob = source['certainty'] / 100
            
            # Reduce probability based on dependencies
            if source['dependencies']:
                dep_prob = 1.0
                for dep_name in source['dependencies']:
                    dep_source = next((s for s in st.session_state.funding_sources if s['name'] == dep_name), None)
                    if dep_source:
                        dep_prob *= dep_source['certainty'] / 100
                source_prob *= dep_prob
            
            total_prob *= source_prob
        
        return total_prob * 100
    
    def create_funding_visualization(self):
        """Create funding sources visualization"""
        # Prepare data
        names = [s['name'] for s in st.session_state.funding_sources]
        amounts = [s['amount'] for s in st.session_state.funding_sources]
        certainties = [s['certainty'] for s in st.session_state.funding_sources]
        types = [s['type'] for s in st.session_state.funding_sources]
        
        # Create bubble chart
        fig = go.Figure()
        
        # Define color map for funding types
        color_map = {
            'grant': '#28a745',
            'tax': '#17a2b8',
            'bond': '#ffc107',
            'donation': '#e83e8c',
            'loan': '#fd7e14',
            'other': '#6c757d'
        }
        
        for i, source in enumerate(st.session_state.funding_sources):
            fig.add_trace(go.Scatter(
                x=[certainties[i]],
                y=[amounts[i]],
                mode='markers+text',
                name=names[i],
                text=[names[i]],
                textposition='top center',
                marker=dict(
                    size=amounts[i]/10000,  # Scale bubble size
                    color=color_map.get(types[i], '#6c757d'),
                    opacity=0.7,
                    line=dict(width=2, color='white')
                ),
                hovertemplate=f"<b>{names[i]}</b><br>" +
                            f"Amount: ${amounts[i]:,.0f}<br>" +
                            f"Certainty: {certainties[i]}%<br>" +
                            f"Type: {types[i]}<br>" +
                            "<extra></extra>"
            ))
        
        fig.update_layout(
            title="Funding Sources Risk-Amount Analysis",
            xaxis_title="Certainty (%)",
            yaxis_title="Amount ($)",
            showlegend=True,
            height=500,
            xaxis=dict(range=[0, 105]),
            yaxis=dict(rangemode='tozero')
        )
        
        return fig
    
    def render_risk_analysis(self):
        """Render Monte Carlo risk analysis interface"""
        st.markdown("### 📈 Monte Carlo Risk Analysis")
        
        # Check if we have funding sources
        if not st.session_state.funding_sources:
            st.warning("Please add funding sources in the 'Dynamic Funding' tab first.")
            return
        
        st.markdown("Configure risk parameters for Monte Carlo simulation:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            num_simulations = st.number_input(
                "Number of Simulations",
                min_value=100,
                max_value=5000,
                value=1000,
                step=100,
                help="More simulations provide better accuracy but take longer"
            )
        
        with col2:
            volatility = st.slider(
                "Volatility (%)",
                min_value=5,
                max_value=50,
                value=20,
                help="Expected variation in funding amounts"
            )
        
        with col3:
            confidence_level = st.selectbox(
                "Confidence Level",
                options=[90, 95, 99],
                index=1,
                help="Statistical confidence level for analysis"
            )
        
        # Cost uncertainty parameters
        st.markdown("#### Cost Uncertainty")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cost_overrun_prob = st.slider(
                "Cost Overrun Probability (%)",
                min_value=0,
                max_value=50,
                value=20,
                help="Likelihood of costs exceeding estimates"
            )
        
        with col2:
            max_cost_overrun = st.slider(
                "Maximum Cost Overrun (%)",
                min_value=0,
                max_value=100,
                value=30,
                help="Maximum possible cost overrun"
            )
        
        # Run simulation button
        if st.button("🎲 Run Risk Analysis", type="primary"):
            with st.spinner(f"Running {num_simulations} simulations..."):
                # Calculate total funding
                total_funding = sum(s['amount'] for s in st.session_state.funding_sources)
                
                # Run Monte Carlo simulation
                results = run_optimized_monte_carlo(
                    base_amount=total_funding,
                    volatility=volatility/100,
                    time_periods=1,
                    num_simulations=num_simulations
                )
                
                # Display results
                self.display_risk_analysis_results(results, confidence_level)
    
    def display_risk_analysis_results(self, results, confidence_level):
        """Display Monte Carlo risk analysis results"""
        st.markdown("### Risk Analysis Results")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Mean Outcome",
                format_currency(results['mean_final'])
            )
        
        with col2:
            st.metric(
                "Standard Deviation",
                format_currency(results['std_final'])
            )
        
        with col3:
            # Calculate success probability (meeting base amount)
            success_prob = (results['final_values'] >= results['base_amount']).mean() * 100
            st.metric(
                "Success Probability",
                f"{success_prob:.1f}%"
            )
        
        with col4:
            # Value at Risk (VaR)
            var_percentile = (100 - confidence_level) / 2
            var_value = np.percentile(results['final_values'], var_percentile)
            st.metric(
                f"VaR ({confidence_level}%)",
                format_currency(results['base_amount'] - var_value)
            )
        
        # Distribution histogram
        st.markdown("#### Outcome Distribution")
        
        fig_hist = go.Figure()
        
        fig_hist.add_trace(go.Histogram(
            x=results['final_values'],
            nbinsx=50,
            name='Simulated Outcomes',
            marker_color='lightblue',
            opacity=0.7
        ))
        
        # Add mean line
        fig_hist.add_vline(
            x=results['mean_final'],
            line_dash="dash",
            line_color="red",
            annotation_text=f"Mean: {format_currency(results['mean_final'])}"
        )
        
        # Add percentile lines
        for p_name, p_value in results['percentiles'].items():
            fig_hist.add_vline(
                x=p_value,
                line_dash="dot",
                line_color="gray",
                annotation_text=f"{p_name}: {format_currency(p_value)}"
            )
        
        fig_hist.update_layout(
            title=f"Monte Carlo Simulation Results ({results['num_simulations']} simulations)",
            xaxis_title="Funding Amount ($)",
            yaxis_title="Frequency",
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Percentile table
        with st.expander("View Percentile Analysis"):
            percentile_data = {
                'Percentile': ['5th', '25th', '50th (Median)', '75th', '95th'],
                'Value': [
                    format_currency(results['percentiles']['p5']),
                    format_currency(results['percentiles']['p25']),
                    format_currency(results['percentiles']['p50']),
                    format_currency(results['percentiles']['p75']),
                    format_currency(results['percentiles']['p95'])
                ],
                'Probability of Exceeding': ['95%', '75%', '50%', '25%', '5%']
            }
            
            df_percentiles = pd.DataFrame(percentile_data)
            st.dataframe(df_percentiles, use_container_width=True, hide_index=True)
        
        # Risk recommendations
        st.markdown("#### Risk Mitigation Recommendations")
        
        recommendations = self.generate_risk_recommendations(results, success_prob)
        for rec in recommendations:
            st.info(f"💡 {rec}")
    
    def generate_risk_recommendations(self, results, success_prob):
        """Generate risk mitigation recommendations based on analysis"""
        recommendations = []
        
        if success_prob < 70:
            recommendations.append("Consider diversifying funding sources to improve success probability")
        
        if results['std_final'] / results['mean_final'] > 0.3:
            recommendations.append("High volatility detected - consider more stable funding sources")
        
        if results['percentiles']['p5'] < results['base_amount'] * 0.7:
            recommendations.append("Significant downside risk - develop contingency plans for worst-case scenarios")
        
        if not recommendations:
            recommendations.append("Risk profile appears acceptable - continue monitoring funding certainty")
        
        return recommendations
    
    def render_report_generation(self):
        """Render report generation interface"""
        st.markdown("### 📄 Report Generation")
        
        # Check if we have data to report
        if not st.session_state.get('multi_year_data') and not st.session_state.funding_sources:
            st.warning("Please generate a forecast or add funding sources before creating a report.")
            return
        
        st.markdown("Configure your report settings:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_format = st.selectbox(
                "Report Format",
                options=['PDF', 'HTML', 'CSV'],
                help="Select the output format for your report"
            )
        
        with col2:
            report_name = st.text_input(
                "Report Title",
                value=f"Scenario Analysis Report - {datetime.now().strftime('%Y-%m-%d')}",
                help="Enter a title for your report"
            )
        
        # Report sections to include
        st.markdown("#### Select Report Sections")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            include_summary = st.checkbox("Executive Summary", value=True)
            include_forecast = st.checkbox("Multi-Year Forecast", value=True)
            include_funding = st.checkbox("Funding Analysis", value=True)
        
        with col2:
            include_risk = st.checkbox("Risk Analysis", value=True)
            include_charts = st.checkbox("Visualizations", value=True)
            include_recommendations = st.checkbox("Recommendations", value=True)
        
        with col3:
            include_assumptions = st.checkbox("Assumptions", value=True)
            include_methodology = st.checkbox("Methodology", value=True)
            include_appendix = st.checkbox("Data Appendix", value=True)
        
        # Additional notes
        report_notes = st.text_area(
            "Additional Notes (optional)",
            placeholder="Add any additional notes or comments for the report...",
            height=100
        )
        
        # Generate report button
        if st.button("📥 Generate Report", type="primary"):
            with st.spinner(f"Generating {report_format} report..."):
                report_data = self.compile_report_data(
                    include_summary, include_forecast, include_funding,
                    include_risk, include_charts, include_recommendations,
                    include_assumptions, include_methodology, include_appendix,
                    report_notes
                )
                
                if report_format == 'PDF':
                    pdf_file = self.generate_pdf_report(report_name, report_data)
                    if pdf_file:
                        st.download_button(
                            label="📥 Download PDF Report",
                            data=pdf_file,
                            file_name=f"{report_name.replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )
                elif report_format == 'HTML':
                    html_content = self.generate_html_report(report_name, report_data)
                    st.download_button(
                        label="📥 Download HTML Report",
                        data=html_content,
                        file_name=f"{report_name.replace(' ', '_')}.html",
                        mime="text/html"
                    )
                elif report_format == 'CSV':
                    csv_data = self.generate_csv_report(report_data)
                    st.download_button(
                        label="📥 Download CSV Data",
                        data=csv_data,
                        file_name=f"{report_name.replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
                
                st.success(f"✅ {report_format} report generated successfully!")
    
    def compile_report_data(self, *args):
        """Compile all data for report generation"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'multi_year_data': st.session_state.get('multi_year_data', {}),
            'funding_sources': st.session_state.funding_sources,
            'scenarios': st.session_state.get('scenarios_for_comparison', []),
            'sections': {
                'summary': args[0],
                'forecast': args[1],
                'funding': args[2],
                'risk': args[3],
                'charts': args[4],
                'recommendations': args[5],
                'assumptions': args[6],
                'methodology': args[7],
                'appendix': args[8]
            },
            'notes': args[9] if len(args) > 9 else ''
        }
        
        return report_data
    
    def generate_pdf_report(self, title, data):
        """Generate PDF report"""
        if not HAS_FPDF:
            st.error("PDF generation is not available. Please install fpdf2.")
            return None
        
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Title
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, title, ln=True, align='C')
            pdf.ln(10)
            
            # Executive Summary
            if data['sections']['summary']:
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Executive Summary", ln=True)
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 5, self.generate_executive_summary(data))
                pdf.ln(5)
            
            # Multi-Year Forecast
            if data['sections']['forecast'] and data['multi_year_data']:
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Multi-Year Forecast", ln=True)
                pdf.set_font("Arial", size=11)
                
                forecast = data['multi_year_data']
                if forecast:
                    pdf.multi_cell(0, 5, f"Forecast Period: {forecast.get('years', [])[0]} - {forecast.get('years', [])[-1]}")
                    pdf.multi_cell(0, 5, f"Cumulative Impact: ${forecast.get('cumulative_impact', 0):,.0f}")
                pdf.ln(5)
            
            # Funding Analysis
            if data['sections']['funding'] and data['funding_sources']:
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Funding Sources", ln=True)
                pdf.set_font("Arial", size=11)
                
                for source in data['funding_sources']:
                    pdf.multi_cell(0, 5, f"• {source['name']}: ${source['amount']:,.0f} ({source['certainty']}% certainty)")
                pdf.ln(5)
            
            # Return PDF as bytes
            return pdf.output(dest='S').encode('latin-1')
            
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return None
    
    def generate_html_report(self, title, data):
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 30px; }}
                .metric {{ display: inline-block; margin: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                .metric-label {{ font-size: 14px; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #007bff; color: white; }}
                .section {{ margin: 30px 0; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        # Executive Summary
        if data['sections']['summary']:
            html += f"""
            <div class="section">
                <h2>Executive Summary</h2>
                <p>{self.generate_executive_summary(data)}</p>
            </div>
            """
        
        # Multi-Year Forecast
        if data['sections']['forecast'] and data['multi_year_data']:
            forecast = data['multi_year_data']
            html += """
            <div class="section">
                <h2>Multi-Year Forecast</h2>
                <div class="metric">
                    <div class="metric-label">Forecast Period</div>
                    <div class="metric-value">""" + f"{forecast.get('years', [])[0]} - {forecast.get('years', [])[-1]}" + """</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Cumulative Impact</div>
                    <div class="metric-value">""" + f"${forecast.get('cumulative_impact', 0):,.0f}" + """</div>
                </div>
            </div>
            """
        
        # Funding Sources
        if data['sections']['funding'] and data['funding_sources']:
            html += """
            <div class="section">
                <h2>Funding Sources</h2>
                <table>
                    <tr>
                        <th>Source</th>
                        <th>Amount</th>
                        <th>Type</th>
                        <th>Certainty</th>
                    </tr>
            """
            for source in data['funding_sources']:
                html += f"""
                    <tr>
                        <td>{source['name']}</td>
                        <td>${source['amount']:,.0f}</td>
                        <td>{source['type']}</td>
                        <td>{source['certainty']}%</td>
                    </tr>
                """
            html += "</table></div>"
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def generate_csv_report(self, data):
        """Generate CSV report data"""
        output = BytesIO()
        
        # Create DataFrame from funding sources
        if data['funding_sources']:
            df = pd.DataFrame(data['funding_sources'])
            df.to_csv(output, index=False)
        
        # Add multi-year data if available
        if data['multi_year_data'] and 'years' in data['multi_year_data']:
            forecast = data['multi_year_data']
            df_forecast = pd.DataFrame({
                'Year': forecast['years'],
                'Total Budget': forecast['totals']['budget'],
                'Revenue': forecast['totals']['revenue'],
                'Costs': forecast['totals']['costs'],
                'Balance': forecast['totals']['surplus_deficit']
            })
            df_forecast.to_csv(output, index=False, mode='a')
        
        return output.getvalue()
    
    def generate_executive_summary(self, data):
        """Generate executive summary text"""
        summary = "This scenario analysis report provides comprehensive financial projections and risk assessments. "
        
        if data['funding_sources']:
            total_funding = sum(s['amount'] for s in data['funding_sources'])
            summary += f"Total funding identified: ${total_funding:,.0f} from {len(data['funding_sources'])} sources. "
        
        if data['multi_year_data']:
            forecast = data['multi_year_data']
            if 'cumulative_impact' in forecast:
                summary += f"Multi-year cumulative impact: ${forecast['cumulative_impact']:,.0f}. "
        
        if data['notes']:
            summary += f"Additional notes: {data['notes']}"
        
        return summary
    
    def render_scenario_comparison(self):
        """Render scenario comparison interface"""
        st.markdown("### 🔄 Scenario Comparison")
        
        # Load saved scenarios
        scenarios = get_scenarios(limit=10)
        
        if not scenarios:
            st.info("No saved scenarios available for comparison. Create and save scenarios first.")
            return
        
        # Scenario selection
        st.markdown("Select up to 3 scenarios to compare:")
        
        col1, col2, col3 = st.columns(3)
        
        selected_scenarios = []
        
        with col1:
            scenario1 = st.selectbox(
                "Scenario 1",
                options=['None'] + [s['name'] for s in scenarios],
                key="compare_scenario_1"
            )
            if scenario1 != 'None':
                selected_scenarios.append(next(s for s in scenarios if s['name'] == scenario1))
        
        with col2:
            scenario2 = st.selectbox(
                "Scenario 2",
                options=['None'] + [s['name'] for s in scenarios],
                key="compare_scenario_2"
            )
            if scenario2 != 'None':
                selected_scenarios.append(next(s for s in scenarios if s['name'] == scenario2))
        
        with col3:
            scenario3 = st.selectbox(
                "Scenario 3",
                options=['None'] + [s['name'] for s in scenarios],
                key="compare_scenario_3"
            )
            if scenario3 != 'None':
                selected_scenarios.append(next(s for s in scenarios if s['name'] == scenario3))
        
        if len(selected_scenarios) < 2:
            st.warning("Please select at least 2 scenarios to compare.")
            return
        
        # Display comparison
        st.markdown("#### Side-by-Side Comparison")
        
        # Create comparison table
        comparison_data = []
        metrics = ['Total Cost', 'Tax Revenue', 'Grant Funding', 'Private Investment', 'Bonds Needed']
        
        for metric in metrics:
            row = {'Metric': metric}
            for i, scenario in enumerate(selected_scenarios):
                row[f"Scenario {i+1}"] = format_currency(scenario.get(metric, 0))
            comparison_data.append(row)
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
        
        # Radar chart comparison
        st.markdown("#### Radar Chart Comparison")
        
        fig_radar = go.Figure()
        
        for i, scenario in enumerate(selected_scenarios):
            values = [scenario.get(m, 0) for m in metrics]
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=metrics,
                fill='toself',
                name=f"Scenario {i+1}"
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(max(s.get(m, 0) for s in selected_scenarios) for m in metrics)]
                )),
            showlegend=True,
            height=500,
            title="Scenario Comparison Radar Chart"
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # Difference analysis
        if len(selected_scenarios) == 2:
            st.markdown("#### Difference Analysis")
            
            diff_data = []
            for metric in metrics:
                val1 = selected_scenarios[0].get(metric, 0)
                val2 = selected_scenarios[1].get(metric, 0)
                diff = val2 - val1
                pct_diff = (diff / val1 * 100) if val1 != 0 else 0
                
                diff_data.append({
                    'Metric': metric,
                    'Scenario 1': format_currency(val1),
                    'Scenario 2': format_currency(val2),
                    'Difference': format_currency(diff),
                    'Change %': f"{pct_diff:+.1f}%"
                })
            
            df_diff = pd.DataFrame(diff_data)
            st.dataframe(df_diff, use_container_width=True, hide_index=True)
        
        # Export comparison
        if st.button("📥 Export Comparison"):
            comparison_csv = df_comparison.to_csv(index=False)
            st.download_button(
                label="Download Comparison CSV",
                data=comparison_csv,
                file_name=f"scenario_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# Initialize and render the enhanced scenario builder
def render_enhanced_scenario_builder():
    """Main entry point for enhanced scenario builder"""
    builder = EnhancedScenarioBuilder()
    builder.render()