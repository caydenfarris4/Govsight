"""
FRED API Connector
Federal Reserve Economic Data integration for economic indicators

Note: Requires FRED API key to be set in environment variables or secrets
"""

import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go
import plotly.express as px
from modules.external_data.api_config import api_config


class FREDConnector:
    """Connector for Federal Reserve Economic Data (FRED) API"""
    
    def __init__(self, api_key: str = None, cache_manager=None):
        """
        Initialize FRED connector
        
        Args:
            api_key: FRED API key (or set FRED_API_KEY env variable)
            cache_manager: Optional cache manager for data caching
        """
        # Use centralized API configuration
        try:
            self.api_key = api_key or api_config.get_fred_key()
        except ValueError:
            # Fall back to empty string if not configured
            self.api_key = api_key or os.getenv('FRED_API_KEY', '')
            
        self.base_url = api_config.fred_base_url
        self.cache_manager = cache_manager
        self.cache_ttl = 86400  # 24 hours in seconds
        
        # Common economic indicators
        self.indicators = {
            'CPI': {
                'series_id': 'CPIAUCSL',
                'name': 'Consumer Price Index',
                'description': 'Consumer Price Index for All Urban Consumers: All Items',
                'units': 'Index 1982-1984=100',
                'frequency': 'Monthly'
            },
            'UNEMPLOYMENT': {
                'series_id': 'UNRATE',
                'name': 'Unemployment Rate',
                'description': 'Civilian Unemployment Rate',
                'units': 'Percent',
                'frequency': 'Monthly'
            },
            'FED_RATE': {
                'series_id': 'FEDFUNDS',
                'name': 'Federal Funds Rate',
                'description': 'Effective Federal Funds Rate',
                'units': 'Percent',
                'frequency': 'Monthly'
            },
            'GDP': {
                'series_id': 'GDP',
                'name': 'Gross Domestic Product',
                'description': 'Gross Domestic Product',
                'units': 'Billions of Dollars',
                'frequency': 'Quarterly'
            },
            'INFLATION': {
                'series_id': 'T10YIE',
                'name': '10-Year Inflation Expectations',
                'description': '10-Year Breakeven Inflation Rate',
                'units': 'Percent',
                'frequency': 'Daily'
            },
            'HOUSING_STARTS': {
                'series_id': 'HOUST',
                'name': 'Housing Starts',
                'description': 'Housing Starts: Total: New Privately Owned Housing Units Started',
                'units': 'Thousands of Units',
                'frequency': 'Monthly'
            },
            'RETAIL_SALES': {
                'series_id': 'RSXFS',
                'name': 'Retail Sales',
                'description': 'Advance Retail Sales: Retail Trade and Food Services',
                'units': 'Millions of Dollars',
                'frequency': 'Monthly'
            },
            'INDUSTRIAL_PRODUCTION': {
                'series_id': 'INDPRO',
                'name': 'Industrial Production Index',
                'description': 'Industrial Production Index',
                'units': 'Index 2017=100',
                'frequency': 'Monthly'
            }
        }
        
        # Regional indicators for Utah/Spanish Fork area
        self.regional_indicators = {
            'UTAH_UNEMPLOYMENT': {
                'series_id': 'UTUR',
                'name': 'Utah Unemployment Rate',
                'description': 'Unemployment Rate in Utah',
                'units': 'Percent',
                'frequency': 'Monthly'
            },
            'UTAH_EMPLOYMENT': {
                'series_id': 'UTNAN',
                'name': 'Utah Employment',
                'description': 'All Employees: Total Nonfarm in Utah',
                'units': 'Thousands of Persons',
                'frequency': 'Monthly'
            },
            'UTAH_HOME_PRICES': {
                'series_id': 'UTSTHPI',
                'name': 'Utah Home Price Index',
                'description': 'All-Transactions House Price Index for Utah',
                'units': 'Index 1980 Q1=100',
                'frequency': 'Quarterly'
            }
        }
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to FRED with timeout and retry logic"""
        # Add API key to params
        params['api_key'] = self.api_key
        params['file_type'] = 'json'
        
        # Check if API key is configured
        if not self.api_key:
            print("FRED API key not configured. Using mock data.")
            print("To use real data, set the FRED_API_KEY environment variable.")
            print("Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
            return self._get_mock_data(endpoint, params)
        
        try:
            # Use centralized API request method with timeout and retry logic
            url = f"{self.base_url}/{endpoint}"
            return api_config.make_api_request(url, params, method="GET")
        except requests.exceptions.RequestException as e:
            print(f"FRED API request failed: {e}")
            return self._get_mock_data(endpoint, params)
    
    def _get_mock_data(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock data for testing when API is unavailable"""
        # Generate mock economic data for testing
        if 'series/observations' in endpoint:
            series_id = params.get('series_id', 'UNKNOWN')
            
            # Generate time series data
            dates = pd.date_range(end=datetime.now(), periods=100, freq='M')
            
            # Different patterns for different indicators
            if 'UNRATE' in series_id or 'UNEMPLOYMENT' in series_id:
                values = np.random.uniform(3.5, 7.5, 100)  # Unemployment typically 3.5-7.5%
            elif 'CPI' in series_id:
                values = np.linspace(250, 300, 100) + np.random.normal(0, 2, 100)  # Increasing CPI
            elif 'GDP' in series_id:
                values = np.linspace(20000, 25000, 100) + np.random.normal(0, 100, 100)  # Growing GDP
            elif 'FEDFUNDS' in series_id:
                values = np.random.uniform(0.25, 5.5, 100)  # Fed rate typically 0.25-5.5%
            else:
                values = np.random.uniform(90, 110, 100)  # Generic index
            
            observations = []
            for date, value in zip(dates, values):
                observations.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'value': str(value)
                })
            
            return {'observations': observations}
        
        return {}
    
    def get_series(self, series_id: str, start_date: str = None, 
                  end_date: str = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Get time series data from FRED
        
        Args:
            series_id: FRED series ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            use_cache: Whether to use cached data
        
        Returns:
            DataFrame with date and value columns
        """
        # Check cache first
        cache_key = f"fred_{series_id}_{start_date}_{end_date}"
        
        if use_cache and self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return pd.DataFrame(cached_data)
        
        # Prepare parameters
        params = {'series_id': series_id}
        if start_date:
            params['observation_start'] = start_date
        if end_date:
            params['observation_end'] = end_date
        
        # Make API request
        data = self._make_request('series/observations', params)
        
        # Process response
        if 'observations' in data:
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna()
            df = df.set_index('date')
            
            # Cache the data
            if self.cache_manager:
                self.cache_manager.set(cache_key, df.reset_index().to_dict('records'), self.cache_ttl)
            
            return df
        
        return pd.DataFrame()
    
    def get_indicator(self, indicator_name: str, start_date: str = None,
                     end_date: str = None) -> pd.DataFrame:
        """Get a specific economic indicator by name"""
        if indicator_name in self.indicators:
            series_id = self.indicators[indicator_name]['series_id']
        elif indicator_name in self.regional_indicators:
            series_id = self.regional_indicators[indicator_name]['series_id']
        else:
            raise ValueError(f"Unknown indicator: {indicator_name}")
        
        return self.get_series(series_id, start_date, end_date)
    
    def get_all_indicators(self, start_date: str = None, 
                          end_date: str = None) -> Dict[str, pd.DataFrame]:
        """Get all available indicators"""
        all_data = {}
        
        # Get national indicators
        for name, info in self.indicators.items():
            try:
                df = self.get_series(info['series_id'], start_date, end_date)
                if not df.empty:
                    all_data[name] = df
            except Exception as e:
                print(f"Failed to get {name}: {e}")
        
        # Get regional indicators
        for name, info in self.regional_indicators.items():
            try:
                df = self.get_series(info['series_id'], start_date, end_date)
                if not df.empty:
                    all_data[name] = df
            except Exception as e:
                print(f"Failed to get {name}: {e}")
        
        return all_data
    
    def calculate_economic_impact(self, indicators: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Calculate economic impact metrics for budget planning"""
        impact = {
            'inflation_adjustment': 1.0,
            'revenue_impact': 1.0,
            'cost_pressures': {},
            'economic_outlook': 'neutral',
            'recommendations': []
        }
        
        # Calculate inflation impact
        if 'CPI' in indicators and not indicators['CPI'].empty:
            cpi_data = indicators['CPI']['value']
            # Calculate year-over-year inflation
            if len(cpi_data) >= 12:
                current_cpi = cpi_data.iloc[-1]
                year_ago_cpi = cpi_data.iloc[-12]
                inflation_rate = (current_cpi - year_ago_cpi) / year_ago_cpi
                impact['inflation_adjustment'] = 1 + inflation_rate
                impact['cost_pressures']['inflation'] = f"{inflation_rate:.1%}"
                
                if inflation_rate > 0.03:
                    impact['recommendations'].append(
                        f"Consider {inflation_rate:.1%} inflation adjustment in budget projections"
                    )
        
        # Analyze unemployment impact on revenues
        if 'UNEMPLOYMENT' in indicators and not indicators['UNEMPLOYMENT'].empty:
            unemployment = indicators['UNEMPLOYMENT']['value'].iloc[-1]
            # Lower unemployment = stronger economy = higher revenues
            if unemployment < 4:
                impact['revenue_impact'] *= 1.05
                impact['economic_outlook'] = 'strong'
                impact['recommendations'].append(
                    "Low unemployment suggests strong revenue potential"
                )
            elif unemployment > 6:
                impact['revenue_impact'] *= 0.95
                impact['economic_outlook'] = 'weak'
                impact['recommendations'].append(
                    "High unemployment may impact revenue collections"
                )
        
        # Analyze interest rates impact
        if 'FED_RATE' in indicators and not indicators['FED_RATE'].empty:
            fed_rate = indicators['FED_RATE']['value'].iloc[-1]
            impact['cost_pressures']['borrowing_cost'] = f"{fed_rate:.1f}%"
            
            if fed_rate > 4:
                impact['recommendations'].append(
                    "High interest rates increase borrowing costs - consider timing of bond issues"
                )
        
        # Regional analysis
        if 'UTAH_UNEMPLOYMENT' in indicators and not indicators['UTAH_UNEMPLOYMENT'].empty:
            ut_unemployment = indicators['UTAH_UNEMPLOYMENT']['value'].iloc[-1]
            national_unemployment = indicators.get('UNEMPLOYMENT', pd.DataFrame())
            
            if not national_unemployment.empty:
                nat_unemployment = national_unemployment['value'].iloc[-1]
                if ut_unemployment < nat_unemployment:
                    impact['recommendations'].append(
                        "Utah unemployment below national average - positive for local economy"
                    )
        
        return impact
    
    def create_economic_dashboard(self, indicators: Dict[str, pd.DataFrame]) -> Dict[str, go.Figure]:
        """Create visualizations for economic indicators"""
        charts = {}
        
        # 1. Key Indicators Overview
        if indicators:
            fig_overview = go.Figure()
            
            # Add traces for key indicators
            for name in ['CPI', 'UNEMPLOYMENT', 'FED_RATE']:
                if name in indicators and not indicators[name].empty:
                    df = indicators[name]
                    fig_overview.add_trace(go.Scatter(
                        x=df.index,
                        y=df['value'],
                        name=self.indicators[name]['name'],
                        mode='lines',
                        yaxis='y' if name == 'CPI' else 'y2'
                    ))
            
            fig_overview.update_layout(
                title='Key Economic Indicators',
                xaxis_title='Date',
                yaxis=dict(title='CPI Index', side='left'),
                yaxis2=dict(title='Rate (%)', overlaying='y', side='right'),
                hovermode='x unified'
            )
            
            charts['overview'] = fig_overview
        
        # 2. Regional vs National Comparison
        if 'UTAH_UNEMPLOYMENT' in indicators and 'UNEMPLOYMENT' in indicators:
            fig_regional = go.Figure()
            
            fig_regional.add_trace(go.Scatter(
                x=indicators['UNEMPLOYMENT'].index,
                y=indicators['UNEMPLOYMENT']['value'],
                name='National',
                mode='lines',
                line=dict(color='blue')
            ))
            
            fig_regional.add_trace(go.Scatter(
                x=indicators['UTAH_UNEMPLOYMENT'].index,
                y=indicators['UTAH_UNEMPLOYMENT']['value'],
                name='Utah',
                mode='lines',
                line=dict(color='green')
            ))
            
            fig_regional.update_layout(
                title='Unemployment Rate: Utah vs National',
                xaxis_title='Date',
                yaxis_title='Unemployment Rate (%)',
                hovermode='x unified'
            )
            
            charts['regional'] = fig_regional
        
        # 3. Economic Growth Indicators
        growth_indicators = ['GDP', 'RETAIL_SALES', 'INDUSTRIAL_PRODUCTION']
        available_growth = [ind for ind in growth_indicators if ind in indicators]
        
        if available_growth:
            fig_growth = go.Figure()
            
            for ind in available_growth:
                df = indicators[ind]
                # Calculate year-over-year change
                if len(df) >= 4:
                    yoy_change = df['value'].pct_change(4) * 100  # Quarterly data
                    
                    fig_growth.add_trace(go.Scatter(
                        x=df.index,
                        y=yoy_change,
                        name=self.indicators[ind]['name'],
                        mode='lines'
                    ))
            
            fig_growth.update_layout(
                title='Economic Growth Indicators (YoY % Change)',
                xaxis_title='Date',
                yaxis_title='Year-over-Year Change (%)',
                hovermode='x unified'
            )
            
            charts['growth'] = fig_growth
        
        return charts
    
    def get_budget_impact_report(self, start_date: str = None) -> Dict[str, Any]:
        """Generate comprehensive economic impact report for budget planning"""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
        
        # Get all indicators
        indicators = self.get_all_indicators(start_date)
        
        # Calculate impacts
        impact = self.calculate_economic_impact(indicators)
        
        # Create visualizations
        charts = self.create_economic_dashboard(indicators)
        
        # Generate report
        report = {
            'generated_date': datetime.now().strftime('%Y-%m-%d'),
            'indicators_analyzed': list(indicators.keys()),
            'economic_impact': impact,
            'visualizations': charts,
            'data_sources': 'Federal Reserve Economic Data (FRED)',
            'update_frequency': 'Daily/Monthly depending on indicator'
        }
        
        return report