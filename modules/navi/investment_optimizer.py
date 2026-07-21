"""
Municipal Investment Optimizer
Helps cities optimize cash reserves through safe, accredited investment opportunities
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.financial_data.investment_aggregator import get_investment_aggregator

def render_investment_optimizer():
    """
    Main Investment Optimizer interface for municipal cash management
    """
    st.title("Municipal Investment Optimizer")
    st.markdown("""
    Optimize your city's cash reserves through **safe, accredited investment opportunities**.
    Compare Treasury securities, FDIC-insured CDs, money market funds, and government investment pools.
    """)
    
    # Initialize aggregator and fetch opportunities once per render
    aggregator = get_investment_aggregator()
    
    # Fetch fresh opportunities on each render, but cache for consistency within this render
    # This ensures users see current data and can recover from transient API failures
    opportunities_result = aggregator.get_all_opportunities()
    
    # Display global data quality status
    if opportunities_result['errors'] or opportunities_result['warnings']:
        with st.expander("⚠️ Data Quality Status - Click to View", expanded=False):
            if opportunities_result['errors']:
                for error in opportunities_result['errors']:
                    st.error(f"🚨 {error}")
            if opportunities_result['warnings']:
                for warning in opportunities_result['warnings']:
                    st.warning(f"⚠️ {warning}")
            st.info("💡 Always verify current rates with providers before making investment decisions.")
    
    # Create tabs for different features
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Investment Opportunities",
        "Cash Optimization",
        "Yield Comparison",
        "Grant + Investment",
        "Educational Resources"
    ])
    
    with tab1:
        render_opportunities_tab(aggregator, opportunities_result)
    
    with tab2:
        render_optimization_tab(aggregator, opportunities_result)
    
    with tab3:
        render_comparison_tab(aggregator, opportunities_result)
    
    with tab4:
        render_grant_integration_tab()
    
    with tab5:
        render_education_tab()


def render_grant_integration_tab():
    """Grant + Investment integration tab"""
    try:
        from .grant_investment_integration import render_grant_investment_integration
        render_grant_investment_integration()
    except Exception as e:
        st.error(f"Error loading grant integration: {e}")
        st.info("Grant + Investment integration combines grant discovery with cash optimization")


def render_opportunities_tab(aggregator, opportunities_result):
    """Display all available investment opportunities"""
    st.header("Available Investment Opportunities")
    
    # Prominent error display in main content
    if opportunities_result['errors']:
        for error in opportunities_result['errors']:
            st.error(f"🚨 **API ERROR:** {error}")
    
    # Prominent warning display in main content
    if opportunities_result['warnings']:
        for warning in opportunities_result['warnings']:
            st.warning(f"⚠️ **DATA NOTICE:** {warning}")
    
    opportunities = opportunities_result['opportunities']
    
    # Display data quality metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Opportunities", opportunities_result['total_count'])
    with col2:
        st.metric("Live Data Sources", opportunities_result['live_data_count'], 
                  delta="✓ Current" if opportunities_result['live_data_count'] > 0 else None)
    with col3:
        st.metric("Estimated Data", opportunities_result['estimated_data_count'],
                  delta="⚠️ Verify" if opportunities_result['estimated_data_count'] > 0 else None)
    
    if not opportunities:
        st.error("🚫 **No investment opportunities available.** API services may be temporarily unavailable. Please try again later or contact support.")
        return
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        investment_type = st.multiselect(
            "Investment Type",
            options=list(set([opp['type'] for opp in opportunities])),
            default=list(set([opp['type'] for opp in opportunities]))
        )
    
    with col2:
        liquidity = st.selectbox(
            "Liquidity Requirement",
            options=["All", "High", "Medium", "Low"]
        )
    
    with col3:
        min_rate = st.slider(
            "Minimum Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.1
        )
    
    # Filter opportunities
    filtered_opps = [
        opp for opp in opportunities
        if opp['type'] in investment_type
        and (liquidity == "All" or opp['liquidity'] == liquidity)
        and opp['rate'] >= min_rate
    ]
    
    # Display count
    st.info(f"**{len(filtered_opps)}** investment opportunities match your criteria")
    
    # Display opportunities as cards
    for opp in filtered_opps:
        # Add visual indicator for estimated data
        is_live = opp.get('is_live_data', True)
        title_prefix = "" if is_live else "⚠️ ESTIMATED: "
        title_suffix = "" if is_live else " (VERIFY RATE)"
        
        with st.expander(f"{title_prefix}**{opp['name']}** - {opp['rate']}% APY{title_suffix}", expanded=False):
            # Prominent warning for estimated data
            if not is_live:
                st.warning("⚠️ **ESTIMATED RATE** - This rate is not from live API data. Contact provider to verify current rates before investing.")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Provider:** {opp['provider']}")
                st.markdown(f"**Type:** {opp['type']}")
                st.markdown(f"**Term:** {opp['term_display']}")
                st.markdown(f"**Minimum Investment:** ${opp['minimum']:,}")
                
                # Safety indicators
                safety_badges = []
                if opp['fdic_insured']:
                    safety_badges.append("🛡️ FDIC Insured")
                if opp['government_backed']:
                    safety_badges.append("🏛️ Government Backed")
                
                if safety_badges:
                    st.markdown(f"**Safety:** {' | '.join(safety_badges)}")
                
                st.markdown(f"**Safety Rating:** {opp['safety_rating']}")
                st.markdown(f"**Liquidity:** {opp['liquidity']}")
                
                if 'notes' in opp:
                    st.caption(f"ℹ️ {opp['notes']}")
            
            with col2:
                # Calculate example return
                example_principal = max(opp['minimum'], 100000)
                calc = aggregator.calculate_investment_return(opp, example_principal)
                
                st.metric(
                    label=f"Return on ${example_principal:,}",
                    value=f"${calc['interest_earned']:,.2f}",
                    delta=f"{calc['effective_yield']:.2f}% effective yield"
                )
            
            st.caption(f"*Data source: {opp['source']}*")


def render_optimization_tab(aggregator, opportunities_result):
    """Cash optimization calculator"""
    st.header("Cash Optimization Calculator")
    
    # Prominent error/warning display
    if opportunities_result['errors']:
        for error in opportunities_result['errors']:
            st.error(f"🚨 **API ERROR:** {error}")
        st.error("🚫 **Calculator unavailable** - Critical data sources are offline. Please try again later.")
        return
    
    if opportunities_result['warnings']:
        for warning in opportunities_result['warnings']:
            st.warning(f"⚠️ **DATA NOTICE:** {warning}")
        st.info("💡 Calculations below use available data. Verify all rates with providers before investing.")
    
    st.markdown("""
    Enter your available cash and investment criteria to get personalized recommendations.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        principal = st.number_input(
            "Available Cash to Invest",
            min_value=100,
            max_value=100000000,
            value=500000,
            step=10000,
            format="%d"
        )
        
        liquidity_req = st.selectbox(
            "Liquidity Requirement",
            options=["Any", "High (daily access)", "Low (can lock for term)"],
            index=0
        )
    
    with col2:
        investment_term = st.selectbox(
            "Maximum Investment Term",
            options=["Any", "1 month", "3 months", "6 months", "1 year"],
            index=0
        )
        
        safety_pref = st.selectbox(
            "Safety Preference",
            options=["FDIC Insured Only", "Government Backed Only", "Any Accredited Source"],
            index=2
        )
    
    if st.button("Find Best Investment", type="primary"):
        # Map liquidity requirement
        liq_map = {
            "Any": "any",
            "High (daily access)": "high",
            "Low (can lock for term)": "low"
        }
        liquidity = liq_map.get(liquidity_req, "any")
        
        # Get best opportunity using cached result for consistency
        best_opp = aggregator.get_best_opportunity(
            principal=principal,
            liquidity_requirement=liquidity,
            opportunities_result=opportunities_result
        )
        
        if best_opp:
            # Warning if best option is estimated data
            if not best_opp.get('is_live_data', True):
                st.warning("⚠️ **ESTIMATED RATE WARNING:** The recommended investment uses an estimated rate. Verify current rates with the provider before proceeding.")
            
            st.success("**Recommended Investment Found!**")
            
            calc = aggregator.calculate_investment_return(best_opp, principal)
            
            # Display recommendation
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Investment", best_opp['name'])
                st.metric("Rate", f"{best_opp['rate']}%")
            
            with col2:
                st.metric("Expected Interest", f"${calc['interest_earned']:,.2f}")
                st.metric("Total Return", f"${calc['total_return']:,.2f}")
            
            with col3:
                st.metric("Term", best_opp['term_display'])
                st.metric("Effective Yield", f"{calc['effective_yield']:.2f}%")
            
            # Investment details
            with st.expander("Investment Details", expanded=True):
                st.markdown(f"**Provider:** {best_opp['provider']}")
                st.markdown(f"**Type:** {best_opp['type']}")
                st.markdown(f"**Safety Rating:** {best_opp['safety_rating']}")
                st.markdown(f"**FDIC Insured:** {'Yes ✓' if best_opp['fdic_insured'] else 'No'}")
                st.markdown(f"**Government Backed:** {'Yes ✓' if best_opp['government_backed'] else 'No'}")
                st.markdown(f"**Liquidity:** {best_opp['liquidity']}")
                st.markdown(f"**Minimum Investment:** ${best_opp['minimum']:,}")
        else:
            st.error("No suitable investment found matching your criteria. Try adjusting your requirements.")


def render_comparison_tab(aggregator, opportunities_result):
    """Yield comparison and visualization"""
    st.header("Investment Yield Comparison")
    
    # Prominent error/warning display
    if opportunities_result['errors']:
        for error in opportunities_result['errors']:
            st.error(f"🚨 **API ERROR:** {error}")
        st.error("🚫 **Comparison unavailable** - Critical data sources are offline. Please try again later.")
        return
    
    if opportunities_result['warnings']:
        for warning in opportunities_result['warnings']:
            st.warning(f"⚠️ **DATA NOTICE:** {warning}")
        st.info("💡 Comparisons below include estimated data. Verify all rates with providers before making decisions.")
    
    # Input amount to compare
    compare_amount = st.number_input(
        "Amount to Compare",
        min_value=1000,
        max_value=100000000,
        value=1000000,
        step=100000,
        format="%d"
    )
    
    # Max term filter
    term_options = {
        "All Terms": None,
        "Up to 1 month": 30,
        "Up to 3 months": 90,
        "Up to 6 months": 180,
        "Up to 1 year": 365
    }
    
    term_filter = st.selectbox(
        "Filter by Term",
        options=list(term_options.keys()),
        index=0
    )
    
    max_term = term_options[term_filter]
    
    # Get comparison data using cached result for consistency
    comparison_df = aggregator.compare_opportunities(
        compare_amount, 
        max_term,
        opportunities_result=opportunities_result
    )
    
    if not comparison_df.empty:
        # Display table
        st.dataframe(
            comparison_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Create visualization
        st.subheader("Interest Earned Comparison")
        
        # Extract numeric values for plotting
        comparison_df['Interest_Numeric'] = comparison_df['Interest Earned'].str.replace('$', '').str.replace(',', '').astype(float)
        comparison_df['Rate_Numeric'] = comparison_df['Rate (%)']
        
        # Create bar chart
        fig = px.bar(
            comparison_df,
            x='Investment',
            y='Interest_Numeric',
            color='Rate_Numeric',
            title=f'Interest Earned on ${compare_amount:,} Investment',
            labels={'Interest_Numeric': 'Interest Earned ($)', 'Rate_Numeric': 'Rate (%)'},
            color_continuous_scale='viridis'
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Opportunity cost analysis
        st.subheader("Opportunity Cost Analysis")
        
        max_interest = comparison_df['Interest_Numeric'].max()
        min_interest = comparison_df['Interest_Numeric'].min()
        opportunity_cost = max_interest - min_interest
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Best Return", f"${max_interest:,.2f}")
            st.caption(f"Investment: {comparison_df.loc[comparison_df['Interest_Numeric'].idxmax(), 'Investment']}")
        
        with col2:
            st.metric("Opportunity Cost", f"${opportunity_cost:,.2f}")
            st.caption("Difference between best and worst options")


def render_education_tab():
    """Educational resources about municipal investments"""
    st.header("Municipal Investment Education")
    
    st.markdown("""
    ### Understanding Safe Investment Options for Municipalities
    
    Cities and municipalities have several **accredited and regulated** investment options for managing cash reserves:
    """)
    
    # Investment types
    with st.expander("🏛️ US Treasury Securities", expanded=True):
        st.markdown("""
        **What:** Direct obligations of the US Government
        
        **Types:**
        - **Treasury Bills (T-Bills):** Short-term (4 weeks to 1 year)
        - **Treasury Notes:** Medium-term (2 to 10 years)
        - **Treasury Bonds:** Long-term (20 to 30 years)
        
        **Safety:** Backed by full faith and credit of US Government (AAA rated)
        
        **Minimum:** $100
        
        **Best for:** Risk-free investment, benchmark for other rates
        """)
    
    with st.expander("🛡️ CDARS / ICS (IntraFi Network)"):
        st.markdown("""
        **What:** Certificate of Deposit Account Registry Service / IntraFi Cash Service
        
        **How it works:** 
        - Your deposit is split into increments under $250,000
        - Each portion placed at different FDIC-insured banks
        - Full FDIC insurance on multi-million dollar deposits
        
        **Network:** 3,000+ participating banks nationwide
        
        **Safety:** FDIC insured (up to millions through network)
        
        **Minimum:** Typically $250,000
        
        **Best for:** Large cash balances requiring FDIC insurance
        """)
    
    with st.expander("💰 Government Money Market Funds"):
        st.markdown("""
        **What:** Mutual funds investing in government securities
        
        **Types:**
        - **Treasury MMF:** 99.5%+ in Treasury securities
        - **Government MMF:** 99.5%+ in government securities
        
        **Safety:** AAA rated, highly stable $1.00 NAV
        
        **Liquidity:** Daily access to funds
        
        **Minimum:** Varies by fund ($0 - $3,000)
        
        **Best for:** Operating cash needing daily liquidity
        """)
    
    with st.expander("🏦 Local Government Investment Pools (LGIPs)"):
        st.markdown("""
        **What:** State-sponsored investment pools for local governments
        
        **Structure:**
        - Managed by state treasury or financial institution
        - Invests in high-quality short-term securities
        - Rated by agencies like S&P and Moody's
        
        **Safety:** State-regulated, typically AAA/AAAm rated
        
        **Minimum:** Varies by state ($25,000 - $250,000)
        
        **Best for:** Local government entities, competitive rates with safety
        """)
    
    # Key considerations
    st.subheader("Key Investment Principles for Municipalities")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Safety First**
        - Preservation of capital is priority #1
        - Only invest in accredited sources
        - Understand FDIC limits and coverage
        - Diversify across multiple instruments
        """)
    
    with col2:
        st.markdown("""
        **Liquidity Management**
        - Match investments to cash flow needs
        - Keep operating funds liquid
        - Use term investments for reserves
        - Ladder CD maturities for flexibility
        """)
    
    # Resources
    st.subheader("Additional Resources")
    
    st.markdown("""
    - **GFOA (Government Finance Officers Association):** Investment policy guidance
    - **MSRB EMMA:** Municipal securities transparency
    - **US Treasury Direct:** Direct purchase of Treasury securities
    - **IntraFi Network:** Find CDARS/ICS participating banks
    - **State Treasury:** LGIP information for your state
    """)
    
    # Compliance note
    st.info("""
    **Compliance Note:** Always consult with your city's financial advisor and ensure 
    investments comply with your municipality's investment policy and state regulations.
    """)
