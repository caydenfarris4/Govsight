"""
US Treasury Fiscal Data API Connector
Fetches real-time Treasury rates, securities data, and yield curves

Official API: https://fiscaldata.treasury.gov/api-documentation/
Free, no restrictions, no API key required
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from functools import lru_cache

class TreasuryAPI:
    """
    Connector for US Treasury Fiscal Data API
    Provides Treasury Bills, Notes, Bonds rates and yield curve data
    """
    
    BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GovSight-Municipal-Investment-Platform',
            'Accept': 'application/json'
        })
    
    @lru_cache(maxsize=10)
    def get_treasury_rates(self, days_back: int = 30) -> pd.DataFrame:
        """
        Get recent Treasury Bill rates (4-week, 8-week, 13-week, 26-week, 52-week)
        
        Args:
            days_back: Number of days of historical data to fetch
            
        Returns:
            DataFrame with Treasury Bill rates
        """
        endpoint = f"{self.BASE_URL}/v2/accounting/od/avg_interest_rates"
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "fields": "record_date,security_desc,avg_interest_rate_amt,security_type_desc",
            "filter": f"record_date:gte:{start_date},security_type_desc:eq:Treasury Bills",
            "sort": "-record_date",
            "page[size]": 1000
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['avg_interest_rate_amt'] = pd.to_numeric(df['avg_interest_rate_amt'])
                df['record_date'] = pd.to_datetime(df['record_date'])
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error fetching Treasury rates: {e}")
            return pd.DataFrame()
    
    @lru_cache(maxsize=5)
    def get_latest_treasury_rates(self) -> Dict[str, float]:
        """
        Get most recent Treasury Bill rates as a dictionary
        
        Returns:
            Dict with Treasury instruments and their latest rates
        """
        df = self.get_treasury_rates(days_back=7)
        
        if df.empty:
            return {}
        
        # Get most recent date
        latest_date = df['record_date'].max()
        latest_data = df[df['record_date'] == latest_date]
        
        rates = {}
        for _, row in latest_data.iterrows():
            security = row['security_desc']
            rate = row['avg_interest_rate_amt']
            rates[security] = rate
        
        return rates
    
    @lru_cache(maxsize=10)
    def get_treasury_yield_curve(self, days_back: int = 7) -> pd.DataFrame:
        """
        Get Treasury Constant Maturity Rates (Yield Curve)
        
        Args:
            days_back: Number of days of historical data
            
        Returns:
            DataFrame with yield curve data
        """
        endpoint = f"{self.BASE_URL}/v2/accounting/od/avg_interest_rates"
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "fields": "record_date,security_desc,avg_interest_rate_amt",
            "filter": f"record_date:gte:{start_date},security_type_desc:in:(Treasury Notes,Treasury Bonds)",
            "sort": "-record_date",
            "page[size]": 1000
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['avg_interest_rate_amt'] = pd.to_numeric(df['avg_interest_rate_amt'])
                df['record_date'] = pd.to_datetime(df['record_date'])
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error fetching yield curve: {e}")
            return pd.DataFrame()
    
    def get_investment_opportunities(self) -> Dict[str, Any]:
        """
        Get current Treasury investment opportunities formatted for dashboard
        
        Returns:
            Dict with opportunities list and status information
        """
        rates = self.get_latest_treasury_rates()
        
        opportunities = []
        status = "success"
        message = None
        
        if not rates:
            status = "api_error"
            message = "Unable to fetch live Treasury rates from US Treasury API. Please try again later."
            return {
                "status": status,
                "message": message,
                "opportunities": opportunities,
                "data_source": "US Treasury Fiscal Data API",
                "is_live": False
            }
        
        # Map Treasury securities to investment opportunities
        security_mapping = {
            "Treasury Bills - 4 Week": {"term": "4 weeks", "term_days": 28, "type": "T-Bill"},
            "Treasury Bills - 8 Week": {"term": "8 weeks", "term_days": 56, "type": "T-Bill"},
            "Treasury Bills - 13 Week": {"term": "13 weeks", "term_days": 91, "type": "T-Bill"},
            "Treasury Bills - 26 Week": {"term": "26 weeks", "term_days": 182, "type": "T-Bill"},
            "Treasury Bills - 52 Week": {"term": "52 weeks", "term_days": 365, "type": "T-Bill"},
        }
        
        for security, rate in rates.items():
            if security in security_mapping:
                info = security_mapping[security]
                opportunities.append({
                    "name": f"US Treasury {info['type']} - {info['term']}",
                    "provider": "US Treasury",
                    "type": "Government Security",
                    "rate": rate,
                    "term_days": info['term_days'],
                    "term_display": info['term'],
                    "minimum": 100,  # Treasury bills start at $100
                    "safety_rating": "AAA",
                    "fdic_insured": False,
                    "government_backed": True,
                    "liquidity": "High",
                    "source": "US Treasury Fiscal Data API",
                    "last_updated": datetime.now().isoformat(),
                    "is_live_data": True
                })
        
        return {
            "status": status,
            "message": message,
            "opportunities": opportunities,
            "data_source": "US Treasury Fiscal Data API",
            "is_live": True
        }
    
    def calculate_treasury_return(self, principal: float, rate: float, days: int) -> Dict[str, float]:
        """
        Calculate expected return from Treasury investment
        
        Args:
            principal: Investment amount
            rate: Annual interest rate (as percentage)
            days: Term in days
            
        Returns:
            Dict with investment calculations
        """
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
            "effective_yield": round((interest / principal) * (365 / days) * 100, 3)
        }


# Singleton instance
_treasury_api = None

def get_treasury_api() -> TreasuryAPI:
    """Get singleton TreasuryAPI instance"""
    global _treasury_api
    if _treasury_api is None:
        _treasury_api = TreasuryAPI()
    return _treasury_api
