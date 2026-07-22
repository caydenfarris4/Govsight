"""
Investment Opportunities Aggregator
Combines data from all financial data sources to provide comprehensive investment options
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import pandas as pd
from .treasury_api import get_treasury_api
from .money_market_api import get_money_market_api

# Finance staff maintain current LGIP/CDARS/ICS/MMF rates here (these products
# have no public APIs). Each entry carries as_of so staleness is visible.
MANUAL_RATES_PATH = os.path.join("configs", "application", "investment_rates.json")
STALE_AFTER_DAYS_MANUAL = 35   # LGIP rates publish monthly
STALE_AFTER_DAYS_LIVE = 7


def _load_manual_rates() -> Dict[str, Any]:
    try:
        with open(MANUAL_RATES_PATH, "r") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _days_old(as_of: Optional[str]) -> Optional[int]:
    if not as_of:
        return None
    try:
        return (date.today() - datetime.strptime(as_of[:10], "%Y-%m-%d").date()).days
    except ValueError:
        return None

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
        if any(not o.get("as_of") for o in cdars_opps):
            warnings.append("Some CDARS/ICS rates are template values that staff have not entered yet - update them in configs/application/investment_rates.json.")
        
        # Add LGIP opportunities (manual - always add warning)
        lgip_opps = self._get_lgip_opportunities()
        opportunities.extend(lgip_opps)
        if any(not o.get("as_of") for o in lgip_opps):
            warnings.append("Some LGIP rates are template values that staff have not entered yet - update them in configs/application/investment_rates.json.")
        
        # Stamp freshness on every opportunity so the UI can badge staleness
        for opp in opportunities:
            age = _days_old(opp.get('as_of'))
            limit = STALE_AFTER_DAYS_LIVE if opp.get('is_live_data') else STALE_AFTER_DAYS_MANUAL
            opp['age_days'] = age
            opp['stale'] = age is None or age > limit

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
            "estimated_data_count": sum(1 for opp in opportunities if not opp.get('is_live_data', True)),
            "stale_count": sum(1 for opp in opportunities if opp.get('stale')),
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_cdars_ics_opportunities(self) -> List[Dict[str, Any]]:
        """CDARS/ICS opportunities from the staff-maintained rate config.

        These products have no public rate API; a treasurer gets rates from
        their bank partner. Staff record them (with the date) in
        configs/application/investment_rates.json and the UI shows exactly
        how old each figure is.
        """
        return self._opportunities_from_config("cdars_ics")

    def _get_lgip_opportunities(self) -> List[Dict[str, Any]]:
        """State LGIP opportunities from the staff-maintained rate config."""
        return self._opportunities_from_config("lgip")

    def _opportunities_from_config(self, section: str) -> List[Dict[str, Any]]:
        config = _load_manual_rates()
        entries = config.get(section, [])
        opportunities = []
        for entry in entries:
            as_of = entry.get("as_of")
            entered_by = entry.get("entered_by", "")
            if as_of:
                source = f"Entered by staff {as_of}" + (f" ({entered_by})" if entered_by else "")
            else:
                source = "TEMPLATE VALUE - not yet entered by staff; do not rely on this rate"
            opportunities.append({
                "name": entry.get("name", "Unnamed"),
                "provider": entry.get("provider", ""),
                "type": entry.get("type", ""),
                "rate": float(entry.get("rate", 0)),
                "term_days": int(entry.get("term_days", 1)),
                "term_display": entry.get("term_display", ""),
                "minimum": entry.get("minimum", 0),
                "safety_rating": entry.get("safety_rating", ""),
                "fdic_insured": bool(entry.get("fdic_insured", False)),
                "government_backed": bool(entry.get("government_backed", False)),
                "liquidity": entry.get("liquidity", ""),
                "source": source,
                "as_of": as_of,
                "last_updated": datetime.now().isoformat(),
                "notes": entry.get("notes", ""),
                "is_live_data": False,
                "is_manual_entry": True,
            })
        return opportunities

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
