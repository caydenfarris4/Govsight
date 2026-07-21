"""
OFR Money Market Fund Monitor API Connector
Fetches government money market fund yields and portfolio data

Official API: https://www.financialresearch.gov/short-term-funding-monitor/api/
Free, no API key required
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from functools import lru_cache

class MoneyMarketAPI:
    """
    Connector for OFR (Office of Financial Research) Money Market Fund Monitor API
    Provides government money market fund yields and holdings data
    """
    
    BASE_URL = "https://data.financialresearch.gov/v1/series"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GovSight-Municipal-Investment-Platform',
            'Accept': 'application/json'
        })
    
    @lru_cache(maxsize=10)
    def get_government_mmf_yields(self, days_back: int = 30) -> pd.DataFrame:
        """
        Get Government Money Market Fund 7-day yields
        
        Args:
            days_back: Number of days of historical data
            
        Returns:
            DataFrame with MMF yield data
        """
        # OFR API endpoint for money market fund data
        endpoint = f"{self.BASE_URL}/dataset"
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "dataset": "mmf",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                df = pd.DataFrame(data)
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error fetching MMF data from OFR: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame()
    
    def get_latest_government_mmf_yield(self) -> Optional[float]:
        """
        Get most recent government MMF 7-day yield
        
        Returns:
            Latest 7-day yield as float, or None if unavailable
        """
        df = self.get_government_mmf_yields(days_back=7)
        
        if df.empty:
            return None
        
        # Try to extract latest yield
        # Note: Actual field names may vary based on OFR API response
        if 'yield_7day' in df.columns:
            return float(df['yield_7day'].iloc[-1])
        elif 'seven_day_yield' in df.columns:
            return float(df['seven_day_yield'].iloc[-1])
        
        return None
    
    def get_investment_opportunities(self) -> Dict[str, Any]:
        """
        Get government money market fund opportunities formatted for dashboard
        
        Returns:
            Dict with opportunities list and status information
        """
        latest_yield = self.get_latest_government_mmf_yield()
        
        opportunities = []
        status = "success"
        message = None
        is_live = False
        
        # Add government MMF opportunity if data available
        if latest_yield is not None:
            opportunities.append({
                "name": "Government Money Market Fund",
                "provider": "Various (Vanguard, Fidelity, etc.)",
                "type": "Money Market Fund",
                "rate": latest_yield,
                "term_days": 1,  # Daily liquidity
                "term_display": "Daily liquidity",
                "minimum": 1000,  # Typical minimum
                "safety_rating": "AAA",
                "fdic_insured": False,
                "government_backed": True,  # Invests in government securities
                "liquidity": "Daily",
                "source": "OFR Money Market Fund Monitor (Live Data)",
                "last_updated": datetime.now().isoformat(),
                "is_live_data": True
            })
            is_live = True
        else:
            # Use estimated data with clear warning
            status = "estimated_data"
            message = "Live MMF data unavailable. Showing estimated rates - verify current rates with fund providers."
            
            estimated_mmfs = [
                {
                    "name": "Vanguard Treasury Money Market Fund (VUSXX)",
                    "provider": "Vanguard",
                    "type": "Treasury Money Market Fund",
                    "rate": 4.85,  # Approximate current rate
                    "term_days": 1,
                    "term_display": "Daily liquidity",
                    "minimum": 3000,
                    "safety_rating": "AAAm",
                    "fdic_insured": False,
                    "government_backed": True,
                    "liquidity": "Daily",
                    "source": "⚠️ ESTIMATED RATE - Verify with Vanguard",
                    "last_updated": datetime.now().isoformat(),
                    "is_live_data": False
                },
                {
                    "name": "Fidelity Government Money Market Fund (SPAXX)",
                    "provider": "Fidelity",
                    "type": "Government Money Market Fund",
                    "rate": 4.82,  # Approximate current rate
                    "term_days": 1,
                    "term_display": "Daily liquidity",
                    "minimum": 0,
                    "safety_rating": "AAAm",
                    "fdic_insured": False,
                    "government_backed": True,
                    "liquidity": "Daily",
                    "source": "⚠️ ESTIMATED RATE - Verify with Fidelity",
                    "last_updated": datetime.now().isoformat(),
                    "is_live_data": False
                }
            ]
            
            opportunities.extend(estimated_mmfs)
        
        return {
            "status": status,
            "message": message,
            "opportunities": opportunities,
            "data_source": "OFR Money Market Fund Monitor",
            "is_live": is_live
        }
    
    def calculate_mmf_return(self, principal: float, rate: float, days: int) -> Dict[str, float]:
        """
        Calculate expected return from money market fund investment
        
        Args:
            principal: Investment amount
            rate: 7-day yield (as percentage)
            days: Holding period in days
            
        Returns:
            Dict with investment calculations
        """
        annual_rate = rate / 100
        daily_rate = annual_rate / 365
        
        # Compound daily for MMF
        total_return = principal * ((1 + daily_rate) ** days)
        interest = total_return - principal
        
        return {
            "principal": principal,
            "rate": rate,
            "term_days": days,
            "interest_earned": round(interest, 2),
            "total_return": round(total_return, 2),
            "effective_yield": round((interest / principal) * (365 / days) * 100, 3)
        }


# Singleton instance
_mmf_api = None

def get_money_market_api() -> MoneyMarketAPI:
    """Get singleton MoneyMarketAPI instance"""
    global _mmf_api
    if _mmf_api is None:
        _mmf_api = MoneyMarketAPI()
    return _mmf_api
