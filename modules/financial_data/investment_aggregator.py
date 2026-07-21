"""
Investment Opportunities Aggregator
Combines data from all financial data sources to provide comprehensive investment options
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from .treasury_api import get_treasury_api
from .money_market_api import get_money_market_api

class InvestmentAggregator:
    """
    Aggregates investment opportunities from multiple sources:
    - US Treasury securities
    - Government money market funds
    - CDARS/ICS (manual input for now)
    - Local Government Investment Pools (manual input)
    """
    
    def __init__(self):
        self.treasury_api = get_treasury_api()
        self.mmf_api = get_money_market_api()
    
    def get_all_opportunities(self) -> Dict[str, Any]:
        """
        Get all available investment opportunities from all sources
        
        Returns:
            Dict with opportunities list and aggregated status information
        """
        opportunities = []
        warnings = []
        errors = []
        
        # Get Treasury securities
        try:
            treasury_result = self.treasury_api.get_investment_opportunities()
            if treasury_result['status'] == 'success':
                opportunities.extend(treasury_result['opportunities'])
            elif treasury_result['status'] == 'api_error':
                errors.append(treasury_result['message'])
        except Exception as e:
            errors.append(f"Error fetching Treasury data: {str(e)}")
        
        # Get Money Market Funds
        try:
            mmf_result = self.mmf_api.get_investment_opportunities()
            if mmf_result['status'] == 'success':
                opportunities.extend(mmf_result['opportunities'])
            elif mmf_result['status'] == 'estimated_data':
                opportunities.extend(mmf_result['opportunities'])
                warnings.append(mmf_result['message'])
        except Exception as e:
            errors.append(f"Error fetching MMF data: {str(e)}")
        
        # Add CDARS/ICS opportunities (manual - always add warning)
        cdars_opps = self._get_cdars_ics_opportunities()
        opportunities.extend(cdars_opps)
        warnings.append("CDARS/ICS rates are illustrative examples. Contact your bank partner for current rates and availability.")
        
        # Add LGIP opportunities (manual - always add warning)
        lgip_opps = self._get_lgip_opportunities()
        opportunities.extend(lgip_opps)
        warnings.append("State LGIP rates are illustrative examples. Contact your state treasury for current rates.")
        
        # Sort by rate (highest first)
        opportunities.sort(key=lambda x: x.get('rate', 0), reverse=True)
        
        # Determine overall status
        status = "success"
        if errors:
            status = "partial_error" if opportunities else "error"
        elif warnings:
            status = "warning"
        
        return {
            "status": status,
            "opportunities": opportunities,
            "warnings": warnings,
            "errors": errors,
            "total_count": len(opportunities),
            "live_data_count": sum(1 for opp in opportunities if opp.get('is_live_data', False)),
            "estimated_data_count": sum(1 for opp in opportunities if not opp.get('is_live_data', True))
        }
    
    def _get_cdars_ics_opportunities(self) -> List[Dict[str, Any]]:
        """
        Get CDARS/ICS investment opportunities
        Note: Rates are illustrative - would come from bank partner API in production
        """
        return [
            {
                "name": "CDARS CD - 3 Month",
                "provider": "IntraFi Network (CDARS)",
                "type": "Certificate of Deposit",
                "rate": 5.25,  # Example rate
                "term_days": 90,
                "term_display": "3 months",
                "minimum": 250000,
                "safety_rating": "FDIC Insured",
                "fdic_insured": True,
                "government_backed": False,
                "liquidity": "Low (penalty for early withdrawal)",
                "source": "⚠️ ESTIMATED - CDARS Network - Contact your bank for current rates",
                "last_updated": datetime.now().isoformat(),
                "notes": "Multi-million FDIC insurance through network of 3,000+ banks",
                "is_live_data": False
            },
            {
                "name": "CDARS CD - 6 Month",
                "provider": "IntraFi Network (CDARS)",
                "type": "Certificate of Deposit",
                "rate": 5.35,  # Example rate
                "term_days": 182,
                "term_display": "6 months",
                "minimum": 250000,
                "safety_rating": "FDIC Insured",
                "fdic_insured": True,
                "government_backed": False,
                "liquidity": "Low (penalty for early withdrawal)",
                "source": "⚠️ ESTIMATED - CDARS Network - Contact your bank for current rates",
                "last_updated": datetime.now().isoformat(),
                "notes": "Multi-million FDIC insurance through network of 3,000+ banks",
                "is_live_data": False
            },
            {
                "name": "CDARS CD - 12 Month",
                "provider": "IntraFi Network (CDARS)",
                "type": "Certificate of Deposit",
                "rate": 5.45,  # Example rate
                "term_days": 365,
                "term_display": "12 months",
                "minimum": 250000,
                "safety_rating": "FDIC Insured",
                "fdic_insured": True,
                "government_backed": False,
                "liquidity": "Low (penalty for early withdrawal)",
                "source": "⚠️ ESTIMATED - CDARS Network - Contact your bank for current rates",
                "last_updated": datetime.now().isoformat(),
                "notes": "Multi-million FDIC insurance through network of 3,000+ banks",
                "is_live_data": False
            },
            {
                "name": "ICS Money Market",
                "provider": "IntraFi Network (ICS)",
                "type": "Money Market Account",
                "rate": 5.05,  # Example rate
                "term_days": 1,
                "term_display": "Daily liquidity",
                "minimum": 250000,
                "safety_rating": "FDIC Insured",
                "fdic_insured": True,
                "government_backed": False,
                "liquidity": "High (daily access)",
                "source": "⚠️ ESTIMATED - ICS Network - Contact your bank for current rates",
                "last_updated": datetime.now().isoformat(),
                "notes": "Multi-million FDIC insurance with daily liquidity",
                "is_live_data": False
            }
        ]
    
    def _get_lgip_opportunities(self) -> List[Dict[str, Any]]:
        """
        Get Local Government Investment Pool opportunities
        Note: Rates are illustrative - would vary by state
        """
        return [
            {
                "name": "State LGIP - Liquid Pool",
                "provider": "State Investment Pool",
                "type": "Local Government Investment Pool",
                "rate": 5.15,  # Example rate
                "term_days": 1,
                "term_display": "Daily liquidity",
                "minimum": 100000,
                "safety_rating": "AAA/AAAm",
                "fdic_insured": False,
                "government_backed": False,
                "liquidity": "Daily",
                "source": "⚠️ ESTIMATED - State Treasury - Contact for current rates",
                "last_updated": datetime.now().isoformat(),
                "notes": "State-regulated investment pool for local governments",
                "is_live_data": False
            },
            {
                "name": "State LGIP - Term Pool",
                "provider": "State Investment Pool",
                "type": "Local Government Investment Pool",
                "rate": 5.30,  # Example rate
                "term_days": 180,
                "term_display": "6 months",
                "minimum": 250000,
                "safety_rating": "AAA",
                "fdic_insured": False,
                "government_backed": False,
                "liquidity": "Low (term commitment)",
                "source": "⚠️ ESTIMATED - State Treasury - Contact for current rates",
                "last_updated": datetime.now().isoformat(),
                "notes": "Higher rates for term commitment",
                "is_live_data": False
            }
        ]
    
    def calculate_investment_return(
        self, 
        opportunity: Dict[str, Any], 
        principal: float
    ) -> Dict[str, float]:
        """
        Calculate expected return for an investment opportunity
        
        Args:
            opportunity: Investment opportunity dict
            principal: Amount to invest
            
        Returns:
            Dict with calculation results
        """
        rate = opportunity['rate']
        days = opportunity['term_days']
        
        # Simple interest calculation
        annual_rate = rate / 100
        daily_rate = annual_rate / 365
        interest = principal * daily_rate * days
        total_return = principal + interest
        
        return {
            "principal": principal,
            "rate": rate,
            "term_days": days,
            "interest_earned": round(interest, 2),
            "total_return": round(total_return, 2),
            "effective_yield": round((interest / principal) * (365 / days) * 100, 3),
            "opportunity_name": opportunity['name']
        }
    
    def compare_opportunities(
        self, 
        principal: float, 
        max_term_days: Optional[int] = None,
        opportunities_result: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Compare all investment opportunities for a given principal
        
        Args:
            principal: Amount to invest
            max_term_days: Filter to opportunities with term <= this value
            opportunities_result: Pre-fetched opportunities result (for consistency)
            
        Returns:
            DataFrame with comparison data
        """
        if opportunities_result is None:
            opportunities_result = self.get_all_opportunities()
        
        opportunities = opportunities_result['opportunities']
        
        # Filter by term if specified
        if max_term_days:
            opportunities = [
                opp for opp in opportunities 
                if opp['term_days'] <= max_term_days
            ]
        
        comparisons = []
        for opp in opportunities:
            calc = self.calculate_investment_return(opp, principal)
            comparisons.append({
                "Investment": opp['name'],
                "Type": opp['type'],
                "Rate (%)": opp['rate'],
                "Term": opp['term_display'],
                "Interest Earned": f"${calc['interest_earned']:,.2f}",
                "Total Return": f"${calc['total_return']:,.2f}",
                "Effective Yield (%)": calc['effective_yield'],
                "Safety Rating": opp['safety_rating'],
                "FDIC Insured": "✓" if opp['fdic_insured'] else "✗",
                "Liquidity": opp['liquidity'],
                "Minimum": f"${opp['minimum']:,}"
            })
        
        return pd.DataFrame(comparisons)
    
    def get_best_opportunity(
        self, 
        principal: float, 
        liquidity_requirement: str = "any",
        min_safety: str = "any",
        opportunities_result: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best investment opportunity based on criteria
        
        Args:
            principal: Amount to invest
            liquidity_requirement: "high", "medium", "low", or "any"
            min_safety: Minimum safety rating required
            opportunities_result: Pre-fetched opportunities result (for consistency)
            
        Returns:
            Best opportunity dict or None
        """
        if opportunities_result is None:
            opportunities_result = self.get_all_opportunities()
        
        opportunities = opportunities_result['opportunities']
        
        # Filter by liquidity if specified
        if liquidity_requirement != "any":
            liquidity_map = {
                "high": ["High", "Daily"],
                "medium": ["Medium"],
                "low": ["Low"]
            }
            allowed_liquidity = liquidity_map.get(liquidity_requirement.lower(), [])
            opportunities = [
                opp for opp in opportunities 
                if opp['liquidity'] in allowed_liquidity
            ]
        
        # Filter by minimum investment
        opportunities = [
            opp for opp in opportunities 
            if opp['minimum'] <= principal
        ]
        
        if not opportunities:
            return None
        
        # Return highest rate
        return max(opportunities, key=lambda x: x['rate'])


# Singleton instance
_investment_aggregator = None

def get_investment_aggregator() -> InvestmentAggregator:
    """Get singleton InvestmentAggregator instance"""
    global _investment_aggregator
    if _investment_aggregator is None:
        _investment_aggregator = InvestmentAggregator()
    return _investment_aggregator
