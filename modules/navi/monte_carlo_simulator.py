"""
Monte Carlo Risk Simulation Module

This module provides advanced Monte Carlo risk analysis capabilities for
municipal financial planning and project risk assessment.

DESIGN DECISIONS:
1. Standalone module for focused risk simulation functionality
2. Optimized performance with vectorized NumPy operations
3. Professional visualization with full-width charts
4. Real-time progress feedback for better user experience
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
from typing import Dict, Any

# Add the root directory to the path to import helpers
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.utils.ui_helpers import (
    apply_custom_styling,
    show_spinner,
    show_error_with_guidance,
    validate_numeric_input,
    validate_triangular_distribution,
    show_validation_error,
    show_validation_success,
    create_responsive_columns,
    create_scrollable_dataframe,
    create_metric_cards,
    MultiStepProgress,
    show_info_banner
)

# Try to import accessibility helper, fall back if not available
try:
    from modules.utils.accessibility_helper import create_accessible_chart
except ImportError:
    def create_accessible_chart(fig, title, description):
        st.plotly_chart(fig, use_container_width=True)
        return fig

# Performance optimization for Monte Carlo simulations
@st.cache_data(ttl=300, max_entries=10)  # Cache for 5 minutes
def run_optimized_monte_carlo(
    base_amount: float, 
    volatility: float, 
    time_periods: int = 12, 
    num_simulations: int = 1000
) -> Dict[str, Any]:
    """
    Optimized Monte Carlo simulation with caching and performance improvements
    """
    # Limit simulations for better performance
    max_simulations = min(num_simulations, 2000)  # Cap at 2000 for UI responsiveness
    
    # Pre-allocate arrays for better performance
    results = np.zeros((max_simulations, time_periods))
    
    # Set seed for reproducible results
    np.random.seed(42)
    
    # Vectorized random number generation
    random_factors = np.random.normal(1.0, volatility, (max_simulations, time_periods))
    
    # Calculate cumulative returns efficiently
    for sim in range(max_simulations):
        results[sim, 0] = base_amount
        for period in range(1, time_periods):
            results[sim, period] = results[sim, period - 1] * random_factors[sim, period]
    
    # Calculate summary statistics
    final_values = results[:, -1]
    mean_final = np.mean(final_values)
    std_final = np.std(final_values)
    percentiles = np.percentile(final_values, [5, 25, 50, 75, 95])
    
    return {
        "simulation_results": results,
        "final_values": final_values,
        "mean_final": mean_final,
        "std_final": std_final,
        "percentiles": {
            "p5": percentiles[0],
            "p25": percentiles[1], 
            "p50": percentiles[2],
            "p75": percentiles[3],
            "p95": percentiles[4]
        },
        "num_simulations": max_simulations,
        "time_periods": time_periods,
        "base_amount": base_amount,
        "volatility": volatility
    }

@st.cache_data(ttl=180, max_entries=15)  # Cache Monte Carlo results within module
def run_monte_carlo(project_cost: float, revenue_min: float, revenue_mode: float, revenue_max: float, cost_std_dev: float, inflation_rate: float, years: int, iterations: int = 1000):
    '''
    Optimized Monte Carlo simulation using triangular distribution for revenue and cost volatility
    Cached within the Navi module for faster performance
    '''
    # Limit iterations for better performance in the module
    max_iterations = min(iterations, 3000)  # Cap at 3000 for module performance
    
    # Set seed for reproducible results
    np.random.seed(42)
    
    # Vectorized calculations for better performance
    revenues = np.random.triangular(revenue_min, revenue_mode, revenue_max, size=max_iterations)
    adj_revenues = revenues * ((1 + inflation_rate) ** years)
    costs = np.random.normal(loc=project_cost, scale=cost_std_dev, size=max_iterations)
    funding_gaps = costs - adj_revenues
    
    # Vectorized outcome calculation
    outcomes = np.where(funding_gaps <= 0, "Surplus", "Deficit")
    
    # Create DataFrame with proper data types to avoid PyArrow conversion issues
    df = pd.DataFrame({
        "Simulated Revenue": adj_revenues.astype(np.float64),
        "Simulated Cost": costs.astype(np.float64), 
        "Funding Gap": funding_gaps.astype(np.float64),
        "Outcome": outcomes
    })

    # Calculate summary statistics efficiently
    deficit_risk = (funding_gaps > 0).mean() * 100
    summary = {
        "deficit_risk": round(deficit_risk, 2),
        "avg_gap": round(funding_gaps.mean(), 2),
        "min_gap": round(funding_gaps.min(), 2),
        "max_gap": round(funding_gaps.max(), 2),
        "percentile_5": round(np.percentile(funding_gaps, 5), 2),
        "percentile_95": round(np.percentile(funding_gaps, 95), 2),
        "actual_iterations": max_iterations
    }

    return df, summary

def plot_histogram(df):
    # Ensure data types are compatible with plotting
    df_clean = df.copy()
    df_clean["Funding Gap"] = pd.to_numeric(df_clean["Funding Gap"], errors='coerce')
    
    fig = px.histogram(
        df_clean, 
        x="Funding Gap", 
        color="Outcome", 
        nbins=30, 
        title="Risk Distribution Histogram",
        color_discrete_map={"Surplus": "#28a745", "Deficit": "#dc3545"}
    )
    fig.update_layout(
        height=650,
        showlegend=True,
        xaxis_title="Funding Gap ($)",
        yaxis_title="Frequency",
        font=dict(size=12)
    )
    return fig

def plot_cdf(df):
    # Ensure data types are compatible with plotting
    df_clean = df.copy()
    df_clean["Funding Gap"] = pd.to_numeric(df_clean["Funding Gap"], errors='coerce')
    
    fig = px.ecdf(
        df_clean, 
        x="Funding Gap", 
        title="Cumulative Probability Distribution",
        color_discrete_sequence=["#0056CC"]
    )
    fig.update_layout(
        height=650,
        showlegend=False,
        xaxis_title="Funding Gap ($)",
        yaxis_title="Probability",
        font=dict(size=12)
    )
    return fig

def render_monte_carlo_simulator():
    """
    Render the Monte Carlo Risk Simulation interface with enhanced UI/UX
    """
    # Apply consistent styling
    apply_custom_styling()
    
    st.markdown("### Additional Options")
    st.markdown("#### Enhanced Monte Carlo Risk Simulation")
    
    # Info banner for guidance
    show_info_banner(
        "Monte Carlo Simulation",
        "This tool uses statistical simulation to analyze project risk by running thousands of scenarios with varying inputs. The triangular distribution helps model realistic revenue ranges.",
        "📊"
    )

    # Default values
    project_cost = 1000000.0
    mean_revenue = 800000.0

    # Advanced simulation parameters with responsive columns
    col1, col2 = create_responsive_columns(2)
    
    with col1:
        st.markdown("### Scenario Configuration")
        scenario_type = st.selectbox("Scenario Type", ["Baseline", "Optimistic", "Pessimistic"], key="mc_scenario_type")
        inflation_check = st.checkbox("Adjust for Inflation", value=True, key="mc_inflation_check")
        inflation_rate = st.number_input("Annual Inflation Rate (%)", value=2.5, min_value=0.0, max_value=10.0, key="mc_inflation_rate") / 100 if inflation_check else 0.0
        years = st.number_input("Years to Project", value=1, min_value=1, max_value=10, key="mc_years")
    
    with col2:
        st.markdown("### Revenue Range (Triangular Distribution)")
        revenue_min = st.number_input("Minimum Revenue ($)", value=max(0, mean_revenue * 0.8), step=10000.0, key="mc_revenue_min")
        revenue_mode = st.number_input("Most Likely Revenue ($)", value=mean_revenue, step=10000.0, key="mc_revenue_mode")
        revenue_max = st.number_input("Maximum Revenue ($)", value=mean_revenue * 1.2, step=10000.0, key="mc_revenue_max")

    # Cost volatility and simulation parameters with responsive columns
    col3, col4 = create_responsive_columns(2)
    
    with col3:
        st.markdown("### Cost Volatility")
        cost_std_dev = st.number_input("Standard Deviation of Project Cost ($)", value=project_cost * 0.05, step=1000.0, key="mc_cost_std_dev")
        
    with col4:
        st.markdown("### Simulation Parameters")
        iterations = st.slider("Number of Simulations", min_value=500, max_value=3000, value=1000, step=250, key="mc_iterations")
        threshold_value = st.number_input("Test Threshold Revenue ($)", value=float(project_cost), step=10000.0, key="mc_threshold_value")

    # Validation container
    validation_container = st.container()
    
    # Performance notification specific to module
    st.info("⚡ Navi Module Performance Mode: Simulations optimized for speed with up to 3,000 iterations and caching enabled")
    
    # Run simulation button with validation
    if st.button("🎲 Run Monte Carlo Simulation", type="primary", use_container_width=True, key="mc_run_button"):
        # Validate inputs first
        all_valid = True
        validation_errors = []
        
        # Validate triangular distribution
        is_valid, error_msg = validate_triangular_distribution(
            revenue_min, revenue_mode, revenue_max, "Revenue Distribution"
        )
        if not is_valid:
            validation_errors.append(error_msg)
            all_valid = False
        
        # Validate cost standard deviation
        is_valid, error_msg = validate_numeric_input(
            cost_std_dev, min_value=0, field_name="Cost Standard Deviation"
        )
        if not is_valid:
            validation_errors.append(error_msg)
            all_valid = False
        
        # Validate iterations
        is_valid, error_msg = validate_numeric_input(
            iterations, min_value=100, max_value=10000, field_name="Number of Iterations"
        )
        if not is_valid:
            validation_errors.append(error_msg)
            all_valid = False
        
        # Show validation results
        with validation_container:
            if not all_valid:
                for error in validation_errors:
                    show_validation_error("Input Validation", error)
                st.stop()
            else:
                show_validation_success()
        
        # Run the enhanced Monte Carlo simulation with progress tracking
        progress = MultiStepProgress(
            steps=["Initializing simulation", "Running scenarios", "Calculating statistics", "Generating visualizations"],
            title="Monte Carlo Simulation"
        )
        
        try:
            progress.next_step()  # Initializing
            
            # Run simulation with error handling
            progress.next_step()  # Running scenarios
            df, summary = run_monte_carlo(project_cost, revenue_min, revenue_mode, revenue_max, cost_std_dev, inflation_rate, years, iterations)
            
            progress.next_step()  # Calculating statistics
            
            # Generate visualizations
            progress.next_step()  # Generating visualizations
            
            progress.complete("Simulation completed successfully!")
            
        except Exception as e:
            progress.error(f"Simulation failed: {str(e)}")
            show_error_with_guidance(
                f"Failed to run Monte Carlo simulation: {str(e)}",
                recovery_steps=[
                    "Check that all input values are valid numbers",
                    "Ensure revenue minimum ≤ most likely ≤ maximum",
                    "Try reducing the number of iterations",
                    "Refresh the page and try again"
                ]
            )
            st.stop()
        
        # Display charts in full width for better visibility
        st.markdown("### Monte Carlo Simulation Results")
        
        # First chart - Risk Distribution Histogram (full width)
        create_accessible_chart(
            plot_histogram(df), 
            "Risk Distribution Histogram", 
            "Histogram showing the distribution of potential net present value outcomes from Monte Carlo simulation."
        )
        
        st.markdown("---")
        
        # Second chart - Cumulative Probability (full width)
        create_accessible_chart(
            plot_cdf(df), 
            "Cumulative Probability Distribution", 
            "Cumulative distribution function showing the probability of achieving various net present value outcomes."
        )
        
        # Enhanced metrics display with responsive metric cards
        st.markdown("### Comprehensive Risk Analysis")
        
        # Create metrics dictionary for card display
        metrics = {
            "Deficit Risk": {
                "value": f"{summary['deficit_risk']}%",
                "delta": f"{summary['deficit_risk'] - 50:.1f}%" if summary['deficit_risk'] != 50 else None,
                "delta_color": "inverse"
            },
            "Average Gap": {
                "value": f"${summary['avg_gap']:,.0f}"
            },
            "Worst 5% (Risk)": {
                "value": f"${summary['percentile_5']:,.0f}"
            },
            "Best 5% (Opportunity)": {
                "value": f"${summary['percentile_95']:,.0f}"
            }
        }
        
        create_metric_cards(metrics, columns_per_row=4)
        
        # Legacy metric display code for fallback
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.markdown(f"""
            <div style="background-color: #ffebee; padding: 15px; border-radius: 10px; text-align: center;">
                <h4 style="color: #d32f2f; margin: 0;">Deficit Risk</h4>
                <h2 style="color: #d32f2f; margin: 5px 0;">{summary['deficit_risk']}%</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col2:
            st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 10px; text-align: center;">
                <h4 style="color: #1976d2; margin: 0;">Average Gap</h4>
                <h2 style="color: #1976d2; margin: 5px 0;">${summary['avg_gap']:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col3:
            st.markdown(f"""
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 10px; text-align: center;">
                <h4 style="color: #f57c00; margin: 0;">Worst 5%</h4>
                <h2 style="color: #f57c00; margin: 5px 0;">${summary['percentile_5']:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_col4:
            st.markdown(f"""
            <div style="background-color: #e8f5e8; padding: 15px; border-radius: 10px; text-align: center;">
                <h4 style="color: #388e3c; margin: 0;">Best 5%</h4>
                <h2 style="color: #388e3c; margin: 5px 0;">${summary['percentile_95']:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Additional insights with responsive columns
        st.markdown("---")
        prob_above = (df["Simulated Revenue"] > threshold_value).mean() * 100
        
        col_insight1, col_insight2 = create_responsive_columns(2)
        
        with col_insight1:
            st.info(f"**Probability Revenue > ${threshold_value:,.0f}:** {prob_above:.1f}%")
        
        with col_insight2:
            if inflation_check:
                adj_factor = ((1 + inflation_rate) ** years - 1) * 100
                st.info(f"**Inflation Impact:** {adj_factor:.1f}% over {years} year(s)")
        
        # Data Table with scrollable container
        with st.expander("📊 View Detailed Simulation Data", expanded=False):
            st.info(f"Showing {len(df):,} simulation results")
            create_scrollable_dataframe(df, height=400, key="mc_results_table")
        
        # Executive summary
        st.markdown("---")
        st.markdown("### Executive Summary")
        
        risk_level = "HIGH" if summary['deficit_risk'] > 30 else "MEDIUM" if summary['deficit_risk'] > 15 else "LOW"
        risk_color = "#d32f2f" if risk_level == "HIGH" else "#f57c00" if risk_level == "MEDIUM" else "#388e3c"
        
        st.markdown(f"""
        <div style="background-color: #f5f5f5; padding: 20px; border-radius: 10px; border-left: 5px solid {risk_color};">
            <h4 style="color: {risk_color};">Risk Level: {risk_level}</h4>
            <p>Based on {iterations:,} simulations over {years} year(s), there's a <strong>{summary['deficit_risk']}%</strong> chance the project will face a funding shortfall.</p>
            <p>The average funding gap is <strong>${summary['avg_gap']:,.0f}</strong>, with worst-case scenarios (5th percentile) showing gaps of <strong>${abs(summary['percentile_5']):,.0f}</strong> or more.</p>
            <p>There is a <strong>{prob_above:.1f}%</strong> probability that revenue will exceed the ${threshold_value:,.0f} threshold after accounting for inflation adjustments.</p>
        </div>
        """, unsafe_allow_html=True)

    # Information section
    with st.expander("📖 How Monte Carlo Simulation Works", expanded=False):
        st.markdown("""
        ### Monte Carlo Risk Analysis
        
        This advanced simulation technique uses probabilistic modeling to assess financial risk:
        
        **Key Features:**
        - **Triangular Distribution**: Models revenue using minimum, most likely, and maximum values
        - **Cost Volatility**: Accounts for uncertainty in project costs using normal distribution
        - **Inflation Adjustment**: Projects future values accounting for inflation over time
        - **Risk Metrics**: Provides comprehensive risk assessment with percentile analysis
        
        **Interpretation:**
        - **Deficit Risk**: Percentage chance of funding shortfall
        - **Average Gap**: Expected funding gap across all scenarios
        - **Percentile Analysis**: Shows worst-case (5th) and best-case (95th) outcomes
        - **Probability Thresholds**: Likelihood of achieving specific revenue targets
        
        **Best Practices:**
        - Use realistic minimum and maximum revenue estimates
        - Consider historical cost variance for standard deviation
        - Run multiple iterations (1000+) for reliable results
        - Review both charts and summary metrics for complete picture
        """)