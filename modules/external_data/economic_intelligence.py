"""
Economic Intelligence Module
Integrates FRED and BEA data for revenue forecasting and economic context
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from .fred_connector import FREDConnector
from .bea_connector import BEAConnector
from .cache_manager import CacheManager


class EconomicIntelligence:
    """Provides economic context and forecasting for municipal planning"""
    
    def __init__(self):
        """Initialize economic intelligence with data connectors"""
        self.cache_manager = CacheManager()
        self.fred = FREDConnector(cache_manager=self.cache_manager)
        self.bea = BEAConnector(cache_manager=self.cache_manager)
        
        # Default forecast periods
        self.forecast_months = 12
        
    def get_economic_context(self, include_forecasts: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive economic context for decision-making
        
        Args:
            include_forecasts: Whether to include predictive forecasts
            
        Returns:
            Dictionary with economic indicators and analysis
        """
        # Get recent data (last 2 years)
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        
        # Fetch key indicators
        indicators = self.fred.get_all_indicators(start_date)
        regional_data = self.bea.get_all_regional_indicators()
        
        # Calculate current economic health
        economic_health = self._assess_economic_health(indicators, regional_data)
        
        # Generate forecasts if requested
        forecasts = None
        if include_forecasts:
            forecasts = self._generate_forecasts(indicators)
        
        # Calculate revenue impact
        revenue_impact = self._calculate_revenue_impact(indicators, regional_data)
        
        return {
            'indicators': self._format_indicators(indicators),
            'regional_data': self._format_regional_data(regional_data),
            'economic_health': economic_health,
            'forecasts': forecasts,
            'revenue_impact': revenue_impact,
            'updated_at': datetime.now().isoformat()
        }
    
    def forecast_revenue(self, historical_revenue: pd.DataFrame,
                        economic_indicators: List[str] = None) -> Dict[str, Any]:
        """
        Forecast municipal revenue using economic indicators
        
        Args:
            historical_revenue: DataFrame with date and revenue columns
            economic_indicators: List of indicators to use (default: key indicators)
            
        Returns:
            Dictionary with forecasts and confidence intervals
        """
        if economic_indicators is None:
            economic_indicators = ['UNEMPLOYMENT', 'CPI', 'GDP']
        
        # Get economic data aligned with revenue data
        start_date = historical_revenue['date'].min().strftime('%Y-%m-%d')
        end_date = historical_revenue['date'].max().strftime('%Y-%m-%d')
        
        # Prepare features
        features = []
        feature_names = []
        
        for indicator in economic_indicators:
            try:
                data = self.fred.get_indicator(indicator, start_date, end_date)
                if not data.empty:
                    # Resample to match revenue frequency
                    resampled = self._align_data(data, historical_revenue)
                    features.append(resampled['value'].values)
                    feature_names.append(indicator)
            except Exception as e:
                print(f"Could not fetch {indicator}: {e}")
        
        if not features:
            return self._simple_forecast(historical_revenue)
        
        # Build feature matrix
        X = np.column_stack(features)
        y = historical_revenue['revenue'].values
        
        # Handle missing values
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[mask]
        y = y[mask]
        
        if len(X) < 10:
            return self._simple_forecast(historical_revenue)
        
        # Train model
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = LinearRegression()
        model.fit(X_scaled, y)
        
        # Generate future forecasts
        future_dates = pd.date_range(
            start=historical_revenue['date'].max() + timedelta(days=30),
            periods=self.forecast_months,
            freq='M'
        )
        
        # Get future economic indicators
        future_X = self._get_future_indicators(economic_indicators, future_dates)
        
        if future_X is not None:
            future_X_scaled = scaler.transform(future_X)
            forecasts = model.predict(future_X_scaled)
            
            # Calculate confidence intervals (simple approach)
            residuals = y - model.predict(X_scaled)
            std_error = np.std(residuals)
            
            lower_bound = forecasts - 1.96 * std_error
            upper_bound = forecasts + 1.96 * std_error
        else:
            # Fallback to trend-based forecast
            return self._simple_forecast(historical_revenue)
        
        return {
            'dates': future_dates.strftime('%Y-%m-%d').tolist(),
            'forecasts': forecasts.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_score': model.score(X_scaled, y),
            'features_used': feature_names,
            'method': 'economic_regression'
        }
    
    def analyze_economic_scenarios(self, base_revenue: float) -> Dict[str, Any]:
        """
        Analyze economic scenarios and their revenue impact
        
        Args:
            base_revenue: Current annual revenue
            
        Returns:
            Dictionary with scenario analysis
        """
        scenarios = {
            'optimistic': {
                'name': 'Strong Economic Growth',
                'gdp_growth': 0.04,
                'unemployment_change': -0.5,
                'inflation': 0.02,
                'revenue_impact': 1.08
            },
            'base': {
                'name': 'Moderate Growth',
                'gdp_growth': 0.02,
                'unemployment_change': 0,
                'inflation': 0.025,
                'revenue_impact': 1.03
            },
            'pessimistic': {
                'name': 'Economic Slowdown',
                'gdp_growth': -0.01,
                'unemployment_change': 1.5,
                'inflation': 0.04,
                'revenue_impact': 0.97
            }
        }
        
        # Get current economic indicators to contextualize
        indicators = self.fred.get_all_indicators(
            (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        )
        
        current_context = self._get_current_conditions(indicators)
        
        # Calculate scenario outcomes
        for scenario_name, scenario in scenarios.items():
            projected_revenue = base_revenue * scenario['revenue_impact']
            scenarios[scenario_name]['projected_revenue'] = projected_revenue
            scenarios[scenario_name]['revenue_change'] = projected_revenue - base_revenue
            scenarios[scenario_name]['probability'] = self._estimate_probability(
                scenario, current_context
            )
        
        return {
            'scenarios': scenarios,
            'current_conditions': current_context,
            'recommendation': self._recommend_scenario(scenarios, current_context)
        }
    
    def _assess_economic_health(self, indicators: Dict[str, pd.DataFrame],
                                regional_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Assess overall economic health"""
        health_score = 50  # Neutral starting point
        factors = []
        
        # Analyze unemployment
        if 'UNEMPLOYMENT' in indicators and not indicators['UNEMPLOYMENT'].empty:
            unemployment = indicators['UNEMPLOYMENT']['value'].iloc[-1]
            if unemployment < 4:
                health_score += 15
                factors.append(f"Low unemployment ({unemployment:.1f}%) is positive")
            elif unemployment > 6:
                health_score -= 15
                factors.append(f"High unemployment ({unemployment:.1f}%) is concerning")
        
        # Analyze GDP growth
        if 'GDP' in indicators and len(indicators['GDP']) >= 4:
            gdp_data = indicators['GDP']['value']
            gdp_growth = (gdp_data.iloc[-1] - gdp_data.iloc[-4]) / gdp_data.iloc[-4]
            if gdp_growth > 0.02:
                health_score += 10
                factors.append(f"GDP growing at {gdp_growth:.1%}")
            elif gdp_growth < 0:
                health_score -= 10
                factors.append(f"GDP declining at {gdp_growth:.1%}")
        
        # Analyze inflation
        if 'CPI' in indicators and len(indicators['CPI']) >= 12:
            cpi_data = indicators['CPI']['value']
            inflation = (cpi_data.iloc[-1] - cpi_data.iloc[-12]) / cpi_data.iloc[-12]
            if inflation > 0.04:
                health_score -= 10
                factors.append(f"High inflation ({inflation:.1%}) increases costs")
            elif inflation < 0.01:
                health_score -= 5
                factors.append("Low inflation may indicate weak demand")
        
        # Regional analysis
        if 'REGIONAL_GDP' in regional_data:
            trends = self.bea.calculate_economic_trends(regional_data)
            if trends['economic_health'] == 'strong':
                health_score += 10
                factors.append("Regional economy is strong")
            elif trends['economic_health'] == 'weak':
                health_score -= 10
                factors.append("Regional economy is weak")
        
        # Determine rating
        if health_score >= 70:
            rating = "Strong"
        elif health_score >= 55:
            rating = "Moderate"
        elif health_score >= 40:
            rating = "Fair"
        else:
            rating = "Weak"
        
        return {
            'rating': rating,
            'score': health_score,
            'factors': factors,
            'trend': self._determine_trend(indicators)
        }
    
    def _generate_forecasts(self, indicators: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Generate economic forecasts"""
        forecasts = {}
        
        for name, data in indicators.items():
            if data.empty or len(data) < 12:
                continue
            
            try:
                # Simple trend-based forecast
                recent_data = data['value'].iloc[-12:].values
                X = np.arange(len(recent_data)).reshape(-1, 1)
                y = recent_data
                
                model = LinearRegression()
                model.fit(X, y)
                
                # Forecast next 6 months
                future_X = np.arange(len(recent_data), len(recent_data) + 6).reshape(-1, 1)
                forecast_values = model.predict(future_X)
                
                forecasts[name] = {
                    'values': forecast_values.tolist(),
                    'trend': 'increasing' if model.coef_[0] > 0 else 'decreasing',
                    'confidence': 'moderate'
                }
            except Exception:
                continue
        
        return forecasts
    
    def _calculate_revenue_impact(self, indicators: Dict[str, pd.DataFrame],
                                  regional_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Calculate potential revenue impact from economic conditions"""
        impact = {
            'sales_tax': 1.0,
            'property_tax': 1.0,
            'fees': 1.0,
            'total_adjustment': 1.0,
            'recommendations': []
        }
        
        # Sales tax correlates with unemployment and retail sales
        if 'UNEMPLOYMENT' in indicators and not indicators['UNEMPLOYMENT'].empty:
            unemployment = indicators['UNEMPLOYMENT']['value'].iloc[-1]
            if unemployment < 4:
                impact['sales_tax'] *= 1.03
                impact['recommendations'].append("Low unemployment supports sales tax revenue")
            elif unemployment > 6:
                impact['sales_tax'] *= 0.97
                impact['recommendations'].append("High unemployment may reduce sales tax collections")
        
        # Property tax affected by home prices and regional GDP
        if 'REGIONAL_GDP' in regional_data:
            regional_trends = self.bea.calculate_economic_trends(regional_data)
            if regional_trends['economic_health'] == 'strong':
                impact['property_tax'] *= 1.02
                impact['recommendations'].append("Strong regional economy supports property values")
        
        # Calculate total impact
        impact['total_adjustment'] = np.mean([
            impact['sales_tax'],
            impact['property_tax'],
            impact['fees']
        ])
        
        return impact
    
    def _simple_forecast(self, historical_revenue: pd.DataFrame) -> Dict[str, Any]:
        """Simple trend-based forecast when economic data unavailable"""
        recent_revenue = historical_revenue['revenue'].iloc[-12:].values
        
        X = np.arange(len(recent_revenue)).reshape(-1, 1)
        y = recent_revenue
        
        model = LinearRegression()
        model.fit(X, y)
        
        future_X = np.arange(len(recent_revenue), len(recent_revenue) + self.forecast_months).reshape(-1, 1)
        forecasts = model.predict(future_X)
        
        std_error = np.std(y - model.predict(X))
        
        return {
            'dates': [(historical_revenue['date'].max() + timedelta(days=30*i)).strftime('%Y-%m-%d') 
                     for i in range(1, self.forecast_months + 1)],
            'forecasts': forecasts.tolist(),
            'lower_bound': (forecasts - 1.96 * std_error).tolist(),
            'upper_bound': (forecasts + 1.96 * std_error).tolist(),
            'model_score': model.score(X, y),
            'features_used': ['historical_trend'],
            'method': 'simple_regression'
        }
    
    def _align_data(self, economic_data: pd.DataFrame, revenue_data: pd.DataFrame) -> pd.DataFrame:
        """Align economic data frequency with revenue data"""
        # Resample to monthly frequency
        economic_monthly = economic_data.resample('M').mean()
        return economic_monthly
    
    def _get_future_indicators(self, indicator_names: List[str], future_dates: pd.DatetimeIndex) -> Optional[np.ndarray]:
        """Get or forecast future economic indicators"""
        # For simplicity, use trend-based forecast
        future_values = []
        
        for indicator in indicator_names:
            try:
                data = self.fred.get_indicator(indicator)
                if not data.empty and len(data) >= 12:
                    recent = data['value'].iloc[-12:].values
                    trend = np.polyfit(range(len(recent)), recent, 1)
                    future = np.polyval(trend, range(len(recent), len(recent) + len(future_dates)))
                    future_values.append(future)
                else:
                    return None
            except Exception:
                return None
        
        if future_values:
            return np.column_stack(future_values)
        return None
    
    def _get_current_conditions(self, indicators: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Get current economic conditions"""
        conditions = {}
        
        for name, data in indicators.items():
            if not data.empty:
                conditions[name] = {
                    'current': float(data['value'].iloc[-1]),
                    'trend': 'up' if len(data) > 1 and data['value'].iloc[-1] > data['value'].iloc[-2] else 'down'
                }
        
        return conditions
    
    def _estimate_probability(self, scenario: Dict[str, Any], 
                             current_conditions: Dict[str, Any]) -> float:
        """Estimate probability of scenario based on current conditions"""
        # Simple heuristic based on current trends
        if scenario['name'] == 'Moderate Growth':
            return 0.50  # Base case most likely
        elif scenario['name'] == 'Strong Economic Growth':
            # More likely if current conditions are strong
            if current_conditions.get('UNEMPLOYMENT', {}).get('trend') == 'down':
                return 0.30
            return 0.20
        else:  # Pessimistic
            if current_conditions.get('UNEMPLOYMENT', {}).get('trend') == 'up':
                return 0.35
            return 0.20
    
    def _recommend_scenario(self, scenarios: Dict[str, Dict], 
                           current_conditions: Dict[str, Any]) -> str:
        """Recommend which scenario to plan for"""
        # Use highest probability scenario
        max_prob = 0
        recommended = 'base'
        
        for name, scenario in scenarios.items():
            if scenario.get('probability', 0) > max_prob:
                max_prob = scenario['probability']
                recommended = name
        
        return f"Plan for '{scenarios[recommended]['name']}' scenario (probability: {scenarios[recommended]['probability']:.0%})"
    
    def _determine_trend(self, indicators: Dict[str, pd.DataFrame]) -> str:
        """Determine overall economic trend"""
        if not indicators:
            return "unknown"
        
        trends = []
        for data in indicators.values():
            if not data.empty and len(data) >= 2:
                if data['value'].iloc[-1] > data['value'].iloc[-2]:
                    trends.append(1)
                else:
                    trends.append(-1)
        
        if not trends:
            return "stable"
        
        avg_trend = np.mean(trends)
        if avg_trend > 0.2:
            return "improving"
        elif avg_trend < -0.2:
            return "declining"
        else:
            return "stable"
    
    def _format_indicators(self, indicators: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Format indicators for API response"""
        formatted = {}
        
        for name, data in indicators.items():
            if not data.empty:
                formatted[name] = {
                    'current_value': float(data['value'].iloc[-1]),
                    'previous_value': float(data['value'].iloc[-2]) if len(data) > 1 else None,
                    'change': float(data['value'].iloc[-1] - data['value'].iloc[-2]) if len(data) > 1 else None,
                    'unit': self.fred.indicators.get(name, {}).get('units', ''),
                    'last_updated': data.index[-1].strftime('%Y-%m-%d')
                }
        
        return formatted
    
    def _format_regional_data(self, regional_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Format regional data for API response"""
        formatted = {}
        
        for name, data in regional_data.items():
            if not data.empty:
                formatted[name] = {
                    'latest_year': int(data['year'].max()),
                    'latest_value': float(data['value'].iloc[-1]),
                    'location': data['location'].iloc[-1] if 'location' in data.columns else 'Utah County'
                }
        
        return formatted
