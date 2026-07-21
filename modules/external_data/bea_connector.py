"""
BEA API Connector
Bureau of Economic Analysis data integration for regional economic data

Note: Requires BEA API key to be set in environment variables or secrets
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


class BEAConnector:
    """Connector for Bureau of Economic Analysis (BEA) API"""
    
    def __init__(self, api_key: str = None, cache_manager=None):
        """
        Initialize BEA connector
        
        Args:
            api_key: BEA API key (or set BEA_API_KEY env variable)
            cache_manager: Optional cache manager for data caching
        """
        # Use centralized API configuration
        try:
            self.api_key = api_key or api_config.get_bea_key()
        except ValueError:
            # Fall back to empty string if not configured
            self.api_key = api_key or os.getenv('BEA_API_KEY', '')
            
        self.base_url = api_config.bea_base_url
        self.cache_manager = cache_manager
        self.cache_ttl = 86400  # 24 hours in seconds
        
        # Common BEA datasets
        self.datasets = {
            'REGIONAL_GDP': {
                'dataset': 'Regional',
                'table': 'CAGDP2',
                'name': 'Regional GDP',
                'description': 'Gross Domestic Product by County and Metropolitan Area'
            },
            'PERSONAL_INCOME': {
                'dataset': 'Regional',
                'table': 'CAINC1',
                'name': 'Personal Income',
                'description': 'Personal Income Summary by County'
            },
            'EMPLOYMENT': {
                'dataset': 'Regional',
                'table': 'CAEMP25N',
                'name': 'Employment by Industry',
                'description': 'Total Full-Time and Part-Time Employment by NAICS Industry'
            },
            'POPULATION': {
                'dataset': 'Regional',
                'table': 'CAINC4',
                'name': 'Population Statistics',
                'description': 'Population and Personal Income'
            },
            'GOVERNMENT_SPENDING': {
                'dataset': 'Regional',
                'table': 'CAGOV',
                'name': 'Government Expenditures',
                'description': 'State and Local Government Current Receipts and Expenditures'
            }
        }
        
        # Utah County FIPS code (Spanish Fork is in Utah County)
        self.utah_county_fips = '49049'
        self.utah_state_fips = '49'
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to BEA with timeout and retry logic"""
        # Add API key to params
        params['UserID'] = self.api_key
        params['method'] = 'GetData'
        params['ResultFormat'] = 'JSON'
        
        # Check if API key is configured
        if not self.api_key:
            print("BEA API key not configured. Using mock data.")
            print("To use real data, set the BEA_API_KEY environment variable.")
            print("Get a free key at: https://apps.bea.gov/api/signup")
            return self._get_mock_data(params)
        
        try:
            # Use centralized API request method with timeout and retry logic
            return api_config.make_api_request(self.base_url, params, method="GET")
        except requests.exceptions.RequestException as e:
            print(f"BEA API request failed: {e}")
            return self._get_mock_data(params)
    
    def _get_mock_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock data for testing when API is unavailable"""
        # Generate mock regional economic data
        years = list(range(2018, 2024))
        
        mock_data = {
            'BEAAPI': {
                'Results': {
                    'Data': []
                }
            }
        }
        
        # Generate data based on table type
        table_name = params.get('TableName', '')
        
        if 'GDP' in table_name.upper():
            # Mock GDP data
            for year in years:
                value = np.random.uniform(5000000, 10000000) * (1.03 ** (year - 2018))
                mock_data['BEAAPI']['Results']['Data'].append({
                    'GeoName': 'Utah County, UT',
                    'TimePeriod': str(year),
                    'DataValue': str(int(value)),
                    'UNIT_MULT': '1',
                    'CL_UNIT': 'Thousands of dollars'
                })
        
        elif 'INCOME' in table_name.upper():
            # Mock personal income data
            for year in years:
                value = np.random.uniform(45000, 65000) * (1.025 ** (year - 2018))
                mock_data['BEAAPI']['Results']['Data'].append({
                    'GeoName': 'Utah County, UT',
                    'TimePeriod': str(year),
                    'DataValue': str(int(value)),
                    'UNIT_MULT': '1',
                    'CL_UNIT': 'Dollars'
                })
        
        elif 'EMP' in table_name.upper():
            # Mock employment data
            for year in years:
                value = np.random.uniform(250000, 350000) * (1.02 ** (year - 2018))
                mock_data['BEAAPI']['Results']['Data'].append({
                    'GeoName': 'Utah County, UT',
                    'TimePeriod': str(year),
                    'DataValue': str(int(value)),
                    'UNIT_MULT': '1',
                    'CL_UNIT': 'Number of jobs'
                })
        
        else:
            # Generic economic data
            for year in years:
                value = np.random.uniform(100, 200) * (1.03 ** (year - 2018))
                mock_data['BEAAPI']['Results']['Data'].append({
                    'GeoName': 'Utah County, UT',
                    'TimePeriod': str(year),
                    'DataValue': str(value),
                    'UNIT_MULT': '1',
                    'CL_UNIT': 'Index'
                })
        
        return mock_data
    
    def get_regional_data(self, dataset_name: str, geofips: str = None,
                         year_start: int = None, year_end: int = None,
                         use_cache: bool = True) -> pd.DataFrame:
        """
        Get regional economic data from BEA
        
        Args:
            dataset_name: Name of dataset from self.datasets
            geofips: Geographic FIPS code (defaults to Utah County)
            year_start: Start year
            year_end: End year
            use_cache: Whether to use cached data
        
        Returns:
            DataFrame with economic data
        """
        if dataset_name not in self.datasets:
            raise ValueError(f"Unknown dataset: {dataset_name}")
        
        dataset_info = self.datasets[dataset_name]
        geofips = geofips or self.utah_county_fips
        
        # Default to last 5 years if not specified
        if year_end is None:
            year_end = datetime.now().year - 1
        if year_start is None:
            year_start = year_end - 5
        
        # Check cache
        cache_key = f"bea_{dataset_name}_{geofips}_{year_start}_{year_end}"
        
        if use_cache and self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return pd.DataFrame(cached_data)
        
        # Prepare API parameters
        params = {
            'datasetname': dataset_info['dataset'],
            'TableName': dataset_info['table'],
            'LineCode': '1',  # All industries/categories
            'Year': ','.join(str(y) for y in range(year_start, year_end + 1)),
            'GeoFips': geofips
        }
        
        # Make API request
        response = self._make_request(params)
        
        # Process response
        if 'BEAAPI' in response and 'Results' in response['BEAAPI']:
            data = response['BEAAPI']['Results'].get('Data', [])
            
            if data:
                df = pd.DataFrame(data)
                
                # Clean and format data
                if 'DataValue' in df.columns:
                    df['value'] = pd.to_numeric(df['DataValue'].replace(['(NA)', '(D)'], np.nan), errors='coerce')
                if 'TimePeriod' in df.columns:
                    df['year'] = pd.to_numeric(df['TimePeriod'], errors='coerce')
                if 'GeoName' in df.columns:
                    df['location'] = df['GeoName']
                
                # Select relevant columns
                result_df = df[['year', 'value', 'location']].dropna()
                
                # Cache the data
                if self.cache_manager:
                    self.cache_manager.set(cache_key, result_df.to_dict('records'), self.cache_ttl)
                
                return result_df
        
        return pd.DataFrame()
    
    def get_all_regional_indicators(self, geofips: str = None) -> Dict[str, pd.DataFrame]:
        """Get all available regional indicators"""
        geofips = geofips or self.utah_county_fips
        all_data = {}
        
        for name, info in self.datasets.items():
            try:
                df = self.get_regional_data(name, geofips)
                if not df.empty:
                    all_data[name] = df
            except Exception as e:
                print(f"Failed to get {name}: {e}")
        
        return all_data
    
    def get_industry_breakdown(self, geofips: str = None, year: int = None) -> pd.DataFrame:
        """Get employment or GDP breakdown by industry"""
        geofips = geofips or self.utah_county_fips
        year = year or datetime.now().year - 1
        
        # This would normally query detailed industry data
        # For now, return mock industry breakdown
        industries = [
            'Manufacturing', 'Retail Trade', 'Health Care', 'Construction',
            'Professional Services', 'Government', 'Education', 'Finance',
            'Information Technology', 'Transportation'
        ]
        
        # Generate mock data
        values = np.random.uniform(1000, 50000, len(industries))
        values = values / values.sum() * 100  # Convert to percentages
        
        df = pd.DataFrame({
            'industry': industries,
            'employment_share': values,
            'year': year
        })
        
        return df.sort_values('employment_share', ascending=False)
    
    def calculate_economic_trends(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Calculate economic trends and growth rates"""
        trends = {
            'gdp_growth': None,
            'income_growth': None,
            'employment_growth': None,
            'population_growth': None,
            'economic_health': 'stable',
            'trend_analysis': []
        }
        
        # Calculate GDP growth
        if 'REGIONAL_GDP' in data and not data['REGIONAL_GDP'].empty:
            gdp_df = data['REGIONAL_GDP'].sort_values('year')
            if len(gdp_df) >= 2:
                recent_gdp = gdp_df.iloc[-1]['value']
                previous_gdp = gdp_df.iloc[-2]['value']
                growth = (recent_gdp - previous_gdp) / previous_gdp
                trends['gdp_growth'] = growth
                
                if growth > 0.03:
                    trends['trend_analysis'].append("Strong GDP growth indicates expanding economy")
                elif growth < 0:
                    trends['trend_analysis'].append("Negative GDP growth suggests economic contraction")
        
        # Calculate income growth
        if 'PERSONAL_INCOME' in data and not data['PERSONAL_INCOME'].empty:
            income_df = data['PERSONAL_INCOME'].sort_values('year')
            if len(income_df) >= 2:
                recent_income = income_df.iloc[-1]['value']
                previous_income = income_df.iloc[-2]['value']
                growth = (recent_income - previous_income) / previous_income
                trends['income_growth'] = growth
                
                if growth > 0.025:
                    trends['trend_analysis'].append("Rising personal income supports consumer spending")
        
        # Calculate employment growth
        if 'EMPLOYMENT' in data and not data['EMPLOYMENT'].empty:
            emp_df = data['EMPLOYMENT'].sort_values('year')
            if len(emp_df) >= 2:
                recent_emp = emp_df.iloc[-1]['value']
                previous_emp = emp_df.iloc[-2]['value']
                growth = (recent_emp - previous_emp) / previous_emp
                trends['employment_growth'] = growth
                
                if growth > 0.02:
                    trends['trend_analysis'].append("Strong employment growth indicates labor market strength")
        
        # Determine overall economic health
        growth_rates = [v for v in [trends['gdp_growth'], trends['income_growth'], 
                                   trends['employment_growth']] if v is not None]
        
        if growth_rates:
            avg_growth = np.mean(growth_rates)
            if avg_growth > 0.03:
                trends['economic_health'] = 'strong'
            elif avg_growth > 0.01:
                trends['economic_health'] = 'moderate'
            elif avg_growth < 0:
                trends['economic_health'] = 'weak'
        
        return trends
    
    def create_regional_dashboard(self, data: Dict[str, pd.DataFrame]) -> Dict[str, go.Figure]:
        """Create visualizations for regional economic data"""
        charts = {}
        
        # 1. Multi-metric trend chart
        if data:
            fig_trends = go.Figure()
            
            colors = {
                'REGIONAL_GDP': 'blue',
                'PERSONAL_INCOME': 'green',
                'EMPLOYMENT': 'orange'
            }
            
            for metric_name, df in data.items():
                if metric_name in colors and not df.empty:
                    df_sorted = df.sort_values('year')
                    
                    # Normalize to index (100 = first year)
                    if len(df_sorted) > 0:
                        base_value = df_sorted.iloc[0]['value']
                        df_sorted['index'] = (df_sorted['value'] / base_value) * 100
                        
                        fig_trends.add_trace(go.Scatter(
                            x=df_sorted['year'],
                            y=df_sorted['index'],
                            name=self.datasets[metric_name]['name'],
                            mode='lines+markers',
                            line=dict(color=colors[metric_name])
                        ))
            
            fig_trends.update_layout(
                title='Regional Economic Indicators (Indexed)',
                xaxis_title='Year',
                yaxis_title='Index (Base Year = 100)',
                hovermode='x unified'
            )
            
            charts['trends'] = fig_trends
        
        # 2. Industry breakdown pie chart
        industry_df = self.get_industry_breakdown()
        if not industry_df.empty:
            fig_industry = px.pie(
                industry_df,
                values='employment_share',
                names='industry',
                title='Employment by Industry'
            )
            
            charts['industry'] = fig_industry
        
        # 3. Growth rates comparison
        trends = self.calculate_economic_trends(data)
        growth_metrics = ['gdp_growth', 'income_growth', 'employment_growth']
        growth_values = []
        growth_labels = []
        
        for metric in growth_metrics:
            if trends[metric] is not None:
                growth_values.append(trends[metric] * 100)
                growth_labels.append(metric.replace('_', ' ').title())
        
        if growth_values:
            fig_growth = go.Figure(data=[
                go.Bar(
                    x=growth_labels,
                    y=growth_values,
                    marker_color=['green' if v > 0 else 'red' for v in growth_values]
                )
            ])
            
            fig_growth.update_layout(
                title='Annual Growth Rates',
                xaxis_title='Metric',
                yaxis_title='Growth Rate (%)',
                showlegend=False
            )
            
            charts['growth'] = fig_growth
        
        return charts
    
    def get_budget_recommendations(self, geofips: str = None) -> Dict[str, Any]:
        """Generate budget recommendations based on regional economic data"""
        geofips = geofips or self.utah_county_fips
        
        # Get all regional data
        data = self.get_all_regional_indicators(geofips)
        
        # Calculate trends
        trends = self.calculate_economic_trends(data)
        
        # Generate recommendations
        recommendations = {
            'economic_outlook': trends['economic_health'],
            'revenue_projections': {},
            'expenditure_considerations': [],
            'opportunities': [],
            'risks': []
        }
        
        # Revenue projections based on economic growth
        if trends['gdp_growth'] is not None:
            revenue_growth = trends['gdp_growth'] * 0.8  # Conservative estimate
            recommendations['revenue_projections']['sales_tax'] = f"{revenue_growth:.1%} growth expected"
            
            if trends['gdp_growth'] > 0.03:
                recommendations['opportunities'].append(
                    "Strong economic growth supports revenue increases"
                )
        
        if trends['income_growth'] is not None:
            if trends['income_growth'] > 0.025:
                recommendations['opportunities'].append(
                    "Rising incomes may increase property values and tax revenues"
                )
            elif trends['income_growth'] < 0:
                recommendations['risks'].append(
                    "Declining personal income may impact revenue collections"
                )
        
        if trends['employment_growth'] is not None:
            if trends['employment_growth'] > 0.02:
                recommendations['expenditure_considerations'].append(
                    "Growing employment may require infrastructure expansion"
                )
                recommendations['opportunities'].append(
                    "Job growth supports economic development initiatives"
                )
            elif trends['employment_growth'] < 0:
                recommendations['risks'].append(
                    "Job losses may increase demand for social services"
                )
        
        # Industry-specific considerations
        industry_df = self.get_industry_breakdown(geofips)
        if not industry_df.empty:
            top_industry = industry_df.iloc[0]['industry']
            recommendations['expenditure_considerations'].append(
                f"Consider infrastructure needs for {top_industry} sector"
            )
        
        return recommendations