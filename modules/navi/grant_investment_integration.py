"""
Grant + Investment Integration
Optimizes combined grant funding and city cash for maximum returns
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.financial_data.investment_aggregator import get_investment_aggregator

class GrantInvestmentOptimizer:
    """
    Combines grant discovery with investment optimization
    Helps cities maximize returns on both operating cash and grant funds
    """
    
    def __init__(self):
        self.aggregator = get_investment_aggregator()
    
    def optimize_grant_investment(
        self, 
        grant_amount: float,
        grant_receipt_date: datetime,
        expenditure_date: datetime,
        liquidity_requirement: str = "medium"
    ) -> Dict[str, Any]:
        """
        Optimize investment strategy for grant funds between receipt and expenditure
        
        Args:
            grant_amount: Grant amount received
            grant_receipt_date: When grant is received
            expenditure_date: When grant must be spent
            liquidity_requirement: Required liquidity level
            
        Returns:
            Optimized investment strategy
        """
        # Calculate days until expenditure
        days_available = (expenditure_date - grant_receipt_date).days
        
        # Get suitable opportunities
        opportunities = self.aggregator.get_all_opportunities()
        
        # Filter by term
        suitable_opps = [
            opp for opp in opportunities
            if opp['term_days'] <= days_available
            and opp['minimum'] <= grant_amount
        ]
        
        if not suitable_opps:
            return {
                "status": "no_suitable_options",
                "message": f"No suitable investments for {days_available} day term",
                "recommendation": "Keep in operating account"
            }
        
        # Find best opportunity
        best_opp = max(suitable_opps, key=lambda x: x['rate'])
        calc = self.aggregator.calculate_investment_return(best_opp, grant_amount)
        
        return {
            "status": "optimized",
            "grant_amount": grant_amount,
            "days_available": days_available,
            "recommended_investment": best_opp['name'],
            "rate": best_opp['rate'],
            "interest_earned": calc['interest_earned'],
            "total_return": calc['total_return'],
            "safety_rating": best_opp['safety_rating'],
            "fdic_insured": best_opp['fdic_insured'],
            "details": best_opp
        }
    
    def create_combined_strategy(
        self,
        operating_cash: float,
        grant_funds: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create combined investment strategy for operating cash + grants
        
        Args:
            operating_cash: Available operating cash
            grant_funds: List of grant fund details
            
        Returns:
            Combined optimization strategy
        """
        strategies = []
        total_interest = 0
        
        # Optimize operating cash (keep liquid)
        if operating_cash > 0:
            op_best = self.aggregator.get_best_opportunity(
                principal=operating_cash,
                liquidity_requirement="high"
            )
            
            if op_best:
                op_calc = self.aggregator.calculate_investment_return(op_best, operating_cash)
                strategies.append({
                    "type": "Operating Cash",
                    "amount": operating_cash,
                    "investment": op_best['name'],
                    "rate": op_best['rate'],
                    "interest": op_calc['interest_earned'],
                    "liquidity": "High"
                })
                total_interest += op_calc['interest_earned']
        
        # Optimize each grant
        for grant in grant_funds:
            if 'amount' in grant and 'expenditure_date' in grant:
                grant_opt = self.optimize_grant_investment(
                    grant_amount=grant['amount'],
                    grant_receipt_date=grant.get('receipt_date', datetime.now()),
                    expenditure_date=grant['expenditure_date']
                )
                
                if grant_opt['status'] == 'optimized':
                    strategies.append({
                        "type": f"Grant: {grant.get('name', 'Unnamed')}",
                        "amount": grant['amount'],
                        "investment": grant_opt['recommended_investment'],
                        "rate": grant_opt['rate'],
                        "interest": grant_opt['interest_earned'],
                        "term": f"{grant_opt['days_available']} days"
                    })
                    total_interest += grant_opt['interest_earned']
        
        return {
            "strategies": strategies,
            "total_principal": operating_cash + sum(g.get('amount', 0) for g in grant_funds),
            "total_interest": round(total_interest, 2),
            "total_return": round(operating_cash + sum(g.get('amount', 0) for g in grant_funds) + total_interest, 2)
        }


def render_grant_investment_integration():
    """
    UI for combined grant + investment optimization
    """
    st.header("Grant + Investment Integration")
    
    st.markdown("""
    Maximize returns on **grant funds** between receipt and expenditure dates.
    Combine with operating cash optimization for complete financial strategy.
    """)
    
    optimizer = GrantInvestmentOptimizer()
    
    # Tabs for different scenarios
    tab1, tab2 = st.tabs(["Single Grant Optimization", "Combined Strategy"])
    
    with tab1:
        st.subheader("Optimize Single Grant Investment")
        
        col1, col2 = st.columns(2)
        
        with col1:
            grant_amount = st.number_input(
                "Grant Amount",
                min_value=1000,
                max_value=100000000,
                value=500000,
                step=10000
            )
            
            receipt_date = st.date_input(
                "Grant Receipt Date",
                value=datetime.now()
            )
        
        with col2:
            expenditure_date = st.date_input(
                "Expenditure Deadline",
                value=datetime.now()
            )
            
            liquidity = st.selectbox(
                "Liquidity Requirement",
                ["High", "Medium", "Low"]
            )
        
        if st.button("Optimize Grant Investment", type="primary"):
            result = optimizer.optimize_grant_investment(
                grant_amount=grant_amount,
                grant_receipt_date=datetime.combine(receipt_date, datetime.min.time()),
                expenditure_date=datetime.combine(expenditure_date, datetime.min.time()),
                liquidity_requirement=liquidity.lower()
            )
            
            if result['status'] == 'optimized':
                st.success("**Grant Investment Optimized!**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Grant Amount", f"${result['grant_amount']:,.0f}")
                    st.metric("Days Available", result['days_available'])
                
                with col2:
                    st.metric("Recommended Investment", result['recommended_investment'])
                    st.metric("Interest Rate", f"{result['rate']}%")
                
                with col3:
                    st.metric("Interest Earned", f"${result['interest_earned']:,.2f}")
                    st.metric("Total Return", f"${result['total_return']:,.2f}")
                
                # Details
                with st.expander("Investment Details", expanded=True):
                    details = result['details']
                    st.markdown(f"**Provider:** {details['provider']}")
                    st.markdown(f"**Type:** {details['type']}")
                    st.markdown(f"**Term:** {details['term_display']}")
                    st.markdown(f"**Safety Rating:** {details['safety_rating']}")
                    st.markdown(f"**FDIC Insured:** {'Yes ✓' if details['fdic_insured'] else 'No'}")
                    st.markdown(f"**Liquidity:** {details['liquidity']}")
                
                st.info(f"""
                💡 **Strategy:** Invest your grant funds in **{result['recommended_investment']}** 
                for {result['days_available']} days to earn **${result['interest_earned']:,.2f}** 
                in additional revenue while maintaining safety and meeting expenditure deadline.
                """)
            else:
                st.warning(result['message'])
                st.info(result['recommendation'])
    
    with tab2:
        st.subheader("Combined Cash + Grants Strategy")
        
        operating_cash = st.number_input(
            "Operating Cash Available",
            min_value=0,
            max_value=100000000,
            value=1000000,
            step=50000
        )
        
        st.markdown("### Grant Funds")
        
        num_grants = st.number_input(
            "Number of Grants",
            min_value=1,
            max_value=10,
            value=2
        )
        
        grant_funds = []
        for i in range(num_grants):
            with st.expander(f"Grant #{i+1}", expanded=i==0):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    grant_name = st.text_input(
                        "Grant Name",
                        value=f"Infrastructure Grant {i+1}",
                        key=f"grant_name_{i}"
                    )
                
                with col2:
                    grant_amt = st.number_input(
                        "Amount",
                        min_value=1000,
                        max_value=50000000,
                        value=250000,
                        step=10000,
                        key=f"grant_amt_{i}"
                    )
                
                with col3:
                    exp_date = st.date_input(
                        "Expenditure Date",
                        value=datetime.now(),
                        key=f"exp_date_{i}"
                    )
                
                grant_funds.append({
                    "name": grant_name,
                    "amount": grant_amt,
                    "receipt_date": datetime.now(),
                    "expenditure_date": datetime.combine(exp_date, datetime.min.time())
                })
        
        if st.button("Create Combined Strategy", type="primary"):
            strategy = optimizer.create_combined_strategy(
                operating_cash=operating_cash,
                grant_funds=grant_funds
            )
            
            st.success("**Combined Strategy Created!**")
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Principal", f"${strategy['total_principal']:,.0f}")
            
            with col2:
                st.metric("Total Interest Earned", f"${strategy['total_interest']:,.2f}")
            
            with col3:
                st.metric("Total Return", f"${strategy['total_return']:,.2f}")
            
            # Strategy details
            st.subheader("Investment Allocation")
            
            strategy_df = pd.DataFrame(strategy['strategies'])
            
            if not strategy_df.empty:
                # Format currency columns
                for col in ['amount', 'interest']:
                    if col in strategy_df.columns:
                        strategy_df[col] = strategy_df[col].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(strategy_df, use_container_width=True, hide_index=True)
            
            # Visual breakdown
            st.subheader("Revenue Optimization Impact")
            
            baseline_revenue = strategy['total_principal']
            optimized_revenue = strategy['total_return']
            additional_revenue = strategy['total_interest']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Baseline (No Investment)",
                    f"${baseline_revenue:,.0f}",
                    delta=None
                )
            
            with col2:
                st.metric(
                    "Optimized Revenue",
                    f"${optimized_revenue:,.0f}",
                    delta=f"+${additional_revenue:,.2f}"
                )
            
            st.success(f"""
            🎯 **Optimization Result:** By strategically investing operating cash and grant funds, 
            your city can generate an additional **${additional_revenue:,.2f}** in revenue 
            while maintaining safety and meeting all expenditure deadlines.
            """)
