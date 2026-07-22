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
from modules.financial_data.ttl_cache import ttl_cache

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
    
    @ttl_cache(ttl_seconds=3600)
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
    
    @ttl_cache(ttl_seconds=3600)
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
    
    @ttl_cache(ttl_seconds=3600)
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
    
    @ttl_cache(ttl_seconds=3600)
    def get_auction_bill_rates(self) -> Dict[str, Dict[str, Any]]:
        """
        Latest T-Bill auction results from TreasuryDirect (keyless, official).

        Unlike the avg_interest_rates series (average rate on ALL outstanding
        federal debt), auction results are the yields a purchaser actually
        locks in, which is what a municipal treasurer compares against.

        Returns:
            Dict keyed by term ("4-Week", "13-Week", ...) with the most
            recent auction's investment rate (coupon-equivalent yield) and
            auction date.
        """
        url = "https://www.treasurydirect.gov/TA_WS/securities/auctioned"
        try:
            resp = self.session.get(
                url, params={"type": "Bill", "days": 60, "format": "json"},
                timeout=10)
            resp.raise_for_status()
            securities = resp.json()
        except Exception as e:
            print(f"Error fetching TreasuryDirect auction rates: {e}")
            return {}

        latest: Dict[str, Dict[str, Any]] = {}
        for sec in securities if isinstance(securities, list) else []:
            term = sec.get("securityTerm", "")
            rate_raw = sec.get("highInvestmentRate") or sec.get("averageMedianInvestmentRate")
            auction_date = (sec.get("auctionDate") or "")[:10]
            if not term or not rate_raw:
                continue
            try:
                rate = float(rate_raw)
            except (TypeError, ValueError):
                continue
            existing = latest.get(term)
            if existing is None or auction_date > existing["auction_date"]:
                latest[term] = {
                    "rate": rate,
                    "auction_date": auction_date,
                    "cusip": sec.get("cusip", ""),
                    "issue_date": (sec.get("issueDate") or "")[:10],
                }
        return latest

    def get_investment_opportunities(self) -> Dict[str, Any]:
        """
        Get current Treasury investment opportunities formatted for dashboard
        
        Returns:
            Dict with opportunities list and status information
        """
        term_days_map = {
            "4-Week": 28, "8-Week": 56, "13-Week": 91,
            "17-Week": 119, "26-Week": 182, "52-Week": 364,
        }

        opportunities = []

        # Primary source: actual auction results (purchasable yields)
        auction_rates = self.get_auction_bill_rates()
        for term, info in sorted(auction_rates.items(),
                                 key=lambda kv: term_days_map.get(kv[0], 999)):
            if term not in term_days_map:
                continue
            opportunities.append({
                "name": f"US Treasury T-Bill - {term.replace('-', ' ').lower()}",
                "provider": "US Treasury",
                "type": "Government Security",
                "rate": info["rate"],
                "term_days": term_days_map[term],
                "term_display": term.replace("-", " ").lower(),
                "minimum": 100,
                "safety_rating": "AAA",
                "fdic_insured": False,
                "government_backed": True,
                "liquidity": "High",
                "source": "TreasuryDirect auction results",
                "as_of": info["auction_date"],
                "last_updated": datetime.now().isoformat(),
                "is_live_data": True
            })

        if opportunities:
            return {
                "status": "success",
                "message": None,
                "opportunities": opportunities,
                "data_source": "TreasuryDirect auction results",
                "is_live": True
            }

        # No fabricated fallback: report the failure honestly
        return {
            "status": "api_error",
            "message": "Unable to fetch live Treasury auction rates. No estimated rates are substituted.",
            "opportunities": [],
            "data_source": "TreasuryDirect",
            "is_live": False
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
