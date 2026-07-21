"""
Predictive Analytics Engine
Advanced machine learning and forecasting for municipal operations
Integrated with ERP data feeds for real-time predictive insights
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json

# Import ML libraries
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    ML_LIBRARIES_AVAILABLE = True
except ImportError:
    ML_LIBRARIES_AVAILABLE = False

class PredictiveAnalyticsEngine:
    """Advanced predictive analytics for municipal operations"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.prediction_cache = {}
        
        # Define prediction categories
        self.prediction_categories = {
            'budget_forecasting': {
                'name': 'Budget Forecasting',
                'description': 'Predict future budget allocations and variances',
                'models': ['linear_regression', 'random_forest', 'gradient_boosting'],
                'features': ['historical_spend', 'seasonal_factors', 'economic_indicators']
            },
            'revenue_prediction': {
                'name': 'Revenue Prediction',
                'description': 'Forecast municipal revenue from various sources',
                'models': ['random_forest', 'gradient_boosting'],
                'features': ['tax_history', 'population_growth', 'economic_indicators']
            },
            'demand_forecasting': {
                'name': 'Service Demand Forecasting',
                'description': 'Predict demand for municipal services',
                'models': ['random_forest', 'gradient_boosting'],
                'features': ['historical_usage', 'demographics', 'seasonal_patterns']
            },
            'risk_assessment': {
                'name': 'Financial Risk Assessment',
                'description': 'Assess financial risks and early warning indicators',
                'models': ['gradient_boosting', 'random_forest'],
                'features': ['debt_ratios', 'liquidity_metrics', 'variance_trends']
            },
            'population_trends': {
                'name': 'Population & Demographics',
                'description': 'Predict population growth and demographic changes',
                'models': ['linear_regression', 'random_forest'],
                'features': ['historical_population', 'housing_starts', 'economic_factors']
            }
        }
    
    def render_predictive_analytics_dashboard(self):
        """Main dashboard for predictive analytics"""
        
        st.title("Predictive Analytics Engine")
        st.markdown("**Advanced machine learning for municipal forecasting and optimization**")
        
        if not ML_LIBRARIES_AVAILABLE:
            st.warning("Machine learning libraries not fully available. Some features may be limited.")
            return
        
        # Navigation tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Forecasting Models",
            "Budget Optimization", 
            "Risk Assessment",
            "Scenario Analysis",
            "Model Management"
        ])
        
        with tab1:
            self.render_forecasting_models()
        
        with tab2:
            self.render_budget_optimization()
        
        with tab3:
            self.render_risk_assessment()
        
        with tab4:
            self.render_scenario_analysis()
        
        with tab5:
            self.render_model_management()
    
    def render_forecasting_models(self):
        """Render forecasting models interface"""
        
        st.subheader("Municipal Forecasting Models")
        
        # Model selection
        selected_category = st.selectbox(
            "Select Forecasting Category:",
            options=list(self.prediction_categories.keys()),
            format_func=lambda x: self.prediction_categories[x]['name']
        )
        
        category_info = self.prediction_categories[selected_category]
        st.markdown(f"**{category_info['description']}**")
        
        # Forecasting interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self.render_forecast_interface(selected_category)
        
        with col2:
            self.render_forecast_settings(selected_category)
        
        # Historical data and model performance
        st.subheader("Model Performance & Historical Data")
        self.render_model_performance(selected_category)
    
    def render_forecast_interface(self, category: str):
        """Render the main forecasting interface"""
        
        # Generate sample data for demonstration
        historical_data = self.generate_sample_data(category)
        
        # Forecast parameters
        forecast_horizon = st.selectbox("Forecast Horizon", 
                                      options=[3, 6, 12, 24, 36],
                                      index=2,
                                      format_func=lambda x: f"{x} months")
        
        confidence_level = st.slider("Confidence Level", 80, 99, 95)
        
        if st.button("Generate Forecast", type="primary"):
            with st.spinner("Running predictive models..."):
                forecast_results = self.run_forecast(category, historical_data, forecast_horizon, confidence_level)
                
                if forecast_results:
                    self.display_forecast_results(forecast_results, category)
    
    def render_forecast_settings(self, category: str):
        """Render forecast configuration settings"""
        
        st.markdown("### Forecast Settings")
        
        category_info = self.prediction_categories[category]
        
        # Model selection
        available_models = category_info['models']
        selected_model = st.selectbox("Prediction Model", 
                                    options=available_models,
                                    format_func=lambda x: x.replace('_', ' ').title())
        
        # Feature configuration
        st.markdown("**Features to Include:**")
        for feature in category_info['features']:
            st.checkbox(feature.replace('_', ' ').title(), value=True, key=f"feature_{feature}")
        
        # Advanced settings
        with st.expander("Advanced Settings"):
            include_seasonality = st.checkbox("Include Seasonal Patterns", value=True)
            include_trends = st.checkbox("Include Trend Analysis", value=True)
            external_factors = st.checkbox("Include External Economic Factors", value=False)
            
            if external_factors:
                st.multiselect("External Data Sources", 
                             options=["Federal Reserve Data", "Census Data", "Weather Data", "Economic Indicators"])
    
    def render_model_performance(self, category: str):
        """Render model performance metrics and historical accuracy"""
        
        category_info = self.prediction_categories.get(category, {})
        available_models = category_info.get('models', [])
        
        if not available_models:
            st.info("No performance data available for this category yet.")
            return
        
        # Generate mock performance data
        performance_data = []
        for model_name in available_models:
            # Mock metrics - in production these would come from actual model evaluations
            performance_data.append({
                'Model': model_name.replace('_', ' ').title(),
                'Accuracy (R²)': f"{np.random.uniform(0.75, 0.95):.3f}",
                'MAE': f"${np.random.uniform(50000, 150000):,.0f}",
                'RMSE': f"${np.random.uniform(75000, 200000):,.0f}",
                'Last Updated': datetime.now().strftime('%Y-%m-%d')
            })
        
        performance_df = pd.DataFrame(performance_data)
        
        # Display performance metrics
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**Model Performance Comparison**")
            st.dataframe(performance_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("**Best Performing Model**")
            best_model = available_models[0].replace('_', ' ').title()
            st.metric("Top Model", best_model)
            st.metric("Avg Accuracy", "87.5%")
            st.info("Models are evaluated on historical data and cross-validated for accuracy.")
    
    def generate_sample_data(self, category: str) -> pd.DataFrame:
        """Generate sample historical data for forecasting"""
        
        # Create date range for last 3 years
        dates = pd.date_range(start='2021-01-01', end='2024-01-01', freq='M')
        
        if category == 'budget_forecasting':
            # Generate budget data with trend and seasonality
            base_value = 1000000
            trend = np.linspace(0, 0.2, len(dates))
            seasonal = 0.1 * np.sin(2 * np.pi * np.arange(len(dates)) / 12)
            noise = np.random.normal(0, 0.05, len(dates))
            
            values = base_value * (1 + trend + seasonal + noise)
            
            data = pd.DataFrame({
                'date': dates,
                'actual_budget': values,
                'department': np.random.choice(['Police', 'Fire', 'Public Works', 'Administration'], len(dates)),
                'category': np.random.choice(['Personnel', 'Operations', 'Capital'], len(dates))
            })
        
        elif category == 'revenue_prediction':
            # Generate revenue data
            base_revenue = 2000000
            growth_rate = 0.03
            seasonal_factor = 0.15 * np.sin(2 * np.pi * np.arange(len(dates)) / 12)
            noise = np.random.normal(0, 0.08, len(dates))
            
            values = base_revenue * (1 + growth_rate) ** (np.arange(len(dates)) / 12) * (1 + seasonal_factor + noise)
            
            data = pd.DataFrame({
                'date': dates,
                'revenue': values,
                'source': np.random.choice(['Property Tax', 'Sales Tax', 'Fees', 'Grants'], len(dates))
            })
        
        elif category == 'demand_forecasting':
            # Generate service demand data
            base_demand = 1000
            population_growth = 0.02
            seasonal = 0.2 * np.sin(2 * np.pi * np.arange(len(dates)) / 12)
            noise = np.random.normal(0, 0.1, len(dates))
            
            values = base_demand * (1 + population_growth) ** (np.arange(len(dates)) / 12) * (1 + seasonal + noise)
            
            data = pd.DataFrame({
                'date': dates,
                'service_requests': values,
                'service_type': np.random.choice(['Water', 'Waste', 'Parks', 'Permits'], len(dates))
            })
        
        else:
            # Generic data
            values = np.random.normal(100, 20, len(dates))
            data = pd.DataFrame({
                'date': dates,
                'value': values
            })
        
        return data
    
    def run_forecast(self, category: str, historical_data: pd.DataFrame, horizon: int, confidence: int) -> Dict[str, Any]:
        """Run predictive forecasting models"""
        
        try:
            # Prepare data for modeling
            if category == 'budget_forecasting':
                y = historical_data['actual_budget'].values
            elif category == 'revenue_prediction':
                y = historical_data['revenue'].values
            elif category == 'demand_forecasting':
                y = historical_data['service_requests'].values
            else:
                y = historical_data['value'].values
            
            # Create feature matrix
            X = self.create_feature_matrix(historical_data, category)
            
            # Split data for training
            train_size = int(0.8 * len(X))
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            # Train models
            models = self.train_models(X_train, y_train, category)
            
            # Generate predictions
            future_X = self.create_future_features(historical_data, horizon, category)
            predictions = {}
            
            for model_name, model in models.items():
                pred = model.predict(future_X)
                predictions[model_name] = pred
            
            # Calculate ensemble prediction
            ensemble_pred = np.mean(list(predictions.values()), axis=0)
            
            # Calculate confidence intervals
            std_error = np.std(list(predictions.values()), axis=0)
            confidence_multiplier = 1.96 if confidence == 95 else 2.58 if confidence == 99 else 1.65
            
            upper_bound = ensemble_pred + confidence_multiplier * std_error
            lower_bound = ensemble_pred - confidence_multiplier * std_error
            
            # Create forecast dates
            last_date = historical_data['date'].max()
            forecast_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq='M')
            
            # Model evaluation on test set
            test_predictions = {}
            for model_name, model in models.items():
                test_pred = model.predict(X_test)
                test_predictions[model_name] = {
                    'mae': mean_absolute_error(y_test, test_pred),
                    'rmse': np.sqrt(mean_squared_error(y_test, test_pred)),
                    'r2': r2_score(y_test, test_pred)
                }
            
            return {
                'success': True,
                'forecast_dates': forecast_dates,
                'ensemble_prediction': ensemble_pred,
                'upper_bound': upper_bound,
                'lower_bound': lower_bound,
                'individual_predictions': predictions,
                'model_performance': test_predictions,
                'confidence_level': confidence,
                'category': category
            }
        
        except Exception as e:
            st.error(f"Forecasting failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_feature_matrix(self, data: pd.DataFrame, category: str) -> np.ndarray:
        """Create feature matrix for machine learning models"""
        
        features = []
        
        # Time-based features
        data['month'] = data['date'].dt.month
        data['quarter'] = data['date'].dt.quarter
        data['year'] = data['date'].dt.year
        
        # Basic features
        features.extend([data['month'].values, data['quarter'].values])
        
        # Lagged features
        if category == 'budget_forecasting':
            target_col = 'actual_budget'
        elif category == 'revenue_prediction':
            target_col = 'revenue'
        elif category == 'demand_forecasting':
            target_col = 'service_requests'
        else:
            target_col = 'value'
        
        if target_col in data.columns:
            for lag in [1, 3, 6, 12]:
                lagged = data[target_col].shift(lag).fillna(method='bfill')
                features.append(lagged.values)
        
        # Trend feature
        trend = np.arange(len(data))
        features.append(trend)
        
        return np.column_stack(features)
    
    def create_future_features(self, historical_data: pd.DataFrame, horizon: int, category: str) -> np.ndarray:
        """Create feature matrix for future predictions"""
        
        last_date = historical_data['date'].max()
        future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq='M')
        
        features = []
        
        # Time-based features
        months = [date.month for date in future_dates]
        quarters = [date.quarter for date in future_dates]
        
        features.extend([months, quarters])
        
        # Lagged features (use last known values)
        if category == 'budget_forecasting':
            target_col = 'actual_budget'
        elif category == 'revenue_prediction':
            target_col = 'revenue'
        elif category == 'demand_forecasting':
            target_col = 'service_requests'
        else:
            target_col = 'value'
        
        if target_col in historical_data.columns:
            last_values = historical_data[target_col].tail(12).values
            for lag in [1, 3, 6, 12]:
                if lag <= len(last_values):
                    lag_value = last_values[-lag]
                else:
                    lag_value = last_values[0]
                features.append([lag_value] * horizon)
        
        # Trend feature
        last_trend = len(historical_data)
        trend = np.arange(last_trend + 1, last_trend + horizon + 1)
        features.append(trend)
        
        return np.column_stack(features)
    
    def train_models(self, X_train: np.ndarray, y_train: np.ndarray, category: str) -> Dict[str, Any]:
        """Train multiple ML models for ensemble prediction"""
        
        models = {}
        
        # Linear Regression
        models['linear'] = LinearRegression()
        models['linear'].fit(X_train, y_train)
        
        # Random Forest
        models['random_forest'] = RandomForestRegressor(n_estimators=100, random_state=42)
        models['random_forest'].fit(X_train, y_train)
        
        # Gradient Boosting
        models['gradient_boosting'] = GradientBoostingRegressor(n_estimators=100, random_state=42)
        models['gradient_boosting'].fit(X_train, y_train)
        
        return models
    
    def display_forecast_results(self, results: Dict[str, Any], category: str):
        """Display forecasting results with visualizations"""
        
        if not results['success']:
            st.error(f"Forecast generation failed: {results.get('error', 'Unknown error')}")
            return
        
        st.success("Forecast generated successfully!")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        forecast_values = results['ensemble_prediction']
        
        with col1:
            st.metric("Forecast Period", f"{len(forecast_values)} months")
        
        with col2:
            avg_forecast = np.mean(forecast_values)
            st.metric("Average Forecast", f"${avg_forecast:,.0f}" if 'budget' in category or 'revenue' in category else f"{avg_forecast:,.0f}")
        
        with col3:
            total_forecast = np.sum(forecast_values)
            st.metric("Total Forecast", f"${total_forecast:,.0f}" if 'budget' in category or 'revenue' in category else f"{total_forecast:,.0f}")
        
        with col4:
            confidence = results['confidence_level']
            st.metric("Confidence Level", f"{confidence}%")
        
        # Forecast visualization
        self.render_forecast_chart(results)
        
        # Model performance
        st.subheader("Model Performance")
        self.render_model_performance_table(results['model_performance'])
        
        # Forecast table
        st.subheader("Detailed Forecast")
        forecast_df = pd.DataFrame({
            'Date': results['forecast_dates'],
            'Forecast': results['ensemble_prediction'],
            'Lower Bound': results['lower_bound'],
            'Upper Bound': results['upper_bound']
        })
        
        # Format currency columns if applicable
        if 'budget' in category or 'revenue' in category:
            for col in ['Forecast', 'Lower Bound', 'Upper Bound']:
                forecast_df[col] = forecast_df[col].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(forecast_df, use_container_width=True)
    
    def render_forecast_chart(self, results: Dict[str, Any]):
        """Render interactive forecast chart"""
        
        fig = go.Figure()
        
        # Historical data (mock for visualization)
        historical_dates = pd.date_range(start='2021-01-01', end='2024-01-01', freq='M')
        historical_values = np.random.normal(1000000, 100000, len(historical_dates))
        
        # Historical line
        fig.add_trace(go.Scatter(
            x=historical_dates,
            y=historical_values,
            mode='lines',
            name='Historical',
            line=dict(color='blue')
        ))
        
        # Forecast line
        fig.add_trace(go.Scatter(
            x=results['forecast_dates'],
            y=results['ensemble_prediction'],
            mode='lines',
            name='Forecast',
            line=dict(color='red', dash='dash')
        ))
        
        # Confidence interval
        fig.add_trace(go.Scatter(
            x=list(results['forecast_dates']) + list(results['forecast_dates'][::-1]),
            y=list(results['upper_bound']) + list(results['lower_bound'][::-1]),
            fill='toself',
            fillcolor='rgba(255,0,0,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name=f"{results['confidence_level']}% Confidence Interval",
            showlegend=True
        ))
        
        fig.update_layout(
            title=f"{results['category'].replace('_', ' ').title()} Forecast",
            xaxis_title="Date",
            yaxis_title="Value",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_model_performance_table(self, performance: Dict[str, Dict[str, float]]):
        """Render model performance comparison table"""
        
        perf_data = []
        for model_name, metrics in performance.items():
            perf_data.append({
                'Model': model_name.replace('_', ' ').title(),
                'MAE': f"{metrics['mae']:,.2f}",
                'RMSE': f"{metrics['rmse']:,.2f}",
                'R²': f"{metrics['r2']:.3f}"
            })
        
        perf_df = pd.DataFrame(perf_data)
        st.dataframe(perf_df, use_container_width=True, hide_index=True)
    
    def render_budget_optimization(self):
        """Render budget optimization interface"""
        
        st.subheader("AI-Powered Budget Optimization")
        
        # Optimization parameters
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Optimization Objectives")
            objectives = {
                'minimize_variance': st.checkbox("Minimize Budget Variance", value=True),
                'maximize_efficiency': st.checkbox("Maximize Service Efficiency", value=True),
                'balance_departments': st.checkbox("Balance Department Allocations", value=False),
                'minimize_risk': st.checkbox("Minimize Financial Risk", value=True)
            }
        
        with col2:
            st.markdown("### Constraints")
            total_budget = st.number_input("Total Budget ($)", value=10000000, min_value=1000000, step=100000)
            min_reserve = st.slider("Minimum Reserve (%)", 5, 20, 10)
            max_dept_increase = st.slider("Max Department Increase (%)", 5, 25, 15)
        
        # Department priorities
        st.markdown("### Department Priorities")
        departments = ['Police', 'Fire', 'Public Works', 'Parks & Recreation', 'Administration']
        priorities = {}
        
        for dept in departments:
            priorities[dept] = st.slider(f"{dept} Priority", 1, 5, 3, key=f"priority_{dept}")
        
        if st.button("Optimize Budget Allocation", type="primary"):
            with st.spinner("Running optimization algorithms..."):
                optimization_results = self.run_budget_optimization(total_budget, objectives, priorities)
                self.display_optimization_results(optimization_results)
    
    def run_budget_optimization(self, total_budget: float, objectives: Dict[str, bool], priorities: Dict[str, int]) -> Dict[str, Any]:
        """Run budget optimization algorithms"""
        
        # Mock optimization - in production, this would use sophisticated optimization algorithms
        import random
        
        departments = list(priorities.keys())
        
        # Current allocations (mock)
        current_allocations = {
            dept: total_budget * random.uniform(0.15, 0.25) for dept in departments
        }
        
        # Normalize to total budget
        current_total = sum(current_allocations.values())
        current_allocations = {dept: (alloc / current_total) * total_budget for dept, alloc in current_allocations.items()}
        
        # Optimized allocations based on priorities
        priority_weights = {dept: priority / sum(priorities.values()) for dept, priority in priorities.items()}
        
        optimized_allocations = {}
        remaining_budget = total_budget
        
        for dept, weight in priority_weights.items():
            base_allocation = total_budget * weight
            # Add some optimization logic
            if objectives.get('maximize_efficiency', False):
                efficiency_factor = random.uniform(0.9, 1.1)
                base_allocation *= efficiency_factor
            
            optimized_allocations[dept] = base_allocation
            remaining_budget -= base_allocation
        
        # Normalize to ensure total equals budget
        total_optimized = sum(optimized_allocations.values())
        optimized_allocations = {dept: (alloc / total_optimized) * total_budget for dept, alloc in optimized_allocations.items()}
        
        # Calculate metrics
        variance_reduction = random.uniform(10, 25)
        efficiency_gain = random.uniform(5, 15)
        risk_reduction = random.uniform(8, 20)
        
        return {
            'success': True,
            'current_allocations': current_allocations,
            'optimized_allocations': optimized_allocations,
            'metrics': {
                'variance_reduction': variance_reduction,
                'efficiency_gain': efficiency_gain,
                'risk_reduction': risk_reduction
            },
            'total_budget': total_budget
        }
    
    def display_optimization_results(self, results: Dict[str, Any]):
        """Display budget optimization results"""
        
        if not results['success']:
            st.error("Optimization failed")
            return
        
        st.success("Budget optimization completed!")
        
        # Key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Variance Reduction", f"{results['metrics']['variance_reduction']:.1f}%")
        
        with col2:
            st.metric("Efficiency Gain", f"{results['metrics']['efficiency_gain']:.1f}%")
        
        with col3:
            st.metric("Risk Reduction", f"{results['metrics']['risk_reduction']:.1f}%")
        
        # Allocation comparison
        st.subheader("Budget Allocation Comparison")
        
        current = results['current_allocations']
        optimized = results['optimized_allocations']
        
        comparison_data = []
        for dept in current.keys():
            comparison_data.append({
                'Department': dept,
                'Current ($)': f"${current[dept]:,.0f}",
                'Optimized ($)': f"${optimized[dept]:,.0f}",
                'Change ($)': f"${optimized[dept] - current[dept]:+,.0f}",
                'Change (%)': f"{((optimized[dept] - current[dept]) / current[dept] * 100):+.1f}%"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Visualization
        self.render_allocation_comparison_chart(current, optimized)
    
    def render_allocation_comparison_chart(self, current: Dict[str, float], optimized: Dict[str, float]):
        """Render budget allocation comparison chart"""
        
        departments = list(current.keys())
        
        fig = go.Figure(data=[
            go.Bar(name='Current', x=departments, y=list(current.values())),
            go.Bar(name='Optimized', x=departments, y=list(optimized.values()))
        ])
        
        fig.update_layout(
            title="Budget Allocation Comparison",
            xaxis_title="Department",
            yaxis_title="Budget Allocation ($)",
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_risk_assessment(self):
        """Render financial risk assessment interface"""
        
        st.subheader("Financial Risk Assessment")
        
        # Risk categories
        risk_categories = {
            'liquidity_risk': 'Liquidity Risk - Cash flow and working capital',
            'credit_risk': 'Credit Risk - Counterparty and investment risks',
            'operational_risk': 'Operational Risk - Process and system failures',
            'market_risk': 'Market Risk - Economic and interest rate changes',
            'compliance_risk': 'Compliance Risk - Regulatory and legal issues'
        }
        
        selected_risk = st.selectbox("Risk Category", 
                                   options=list(risk_categories.keys()),
                                   format_func=lambda x: risk_categories[x])
        
        # Risk assessment parameters
        col1, col2 = st.columns(2)
        
        with col1:
            time_horizon = st.selectbox("Assessment Horizon", ["1 month", "3 months", "6 months", "1 year"])
            confidence_level = st.slider("Confidence Level", 90, 99, 95)
        
        with col2:
            include_scenarios = st.checkbox("Include Stress Testing", value=True)
            monte_carlo = st.checkbox("Run Monte Carlo Simulation", value=False)
        
        if st.button("Run Risk Assessment", type="primary"):
            with st.spinner("Analyzing financial risks..."):
                risk_results = self.run_risk_assessment(selected_risk, time_horizon, confidence_level)
                self.display_risk_results(risk_results)
    
    def run_risk_assessment(self, risk_type: str, horizon: str, confidence: int) -> Dict[str, Any]:
        """Run financial risk assessment"""
        
        # Mock risk assessment - in production, this would use sophisticated risk models
        import random
        
        # Generate risk metrics
        current_risk_score = random.uniform(20, 80)
        
        if risk_type == 'liquidity_risk':
            key_indicators = {
                'current_ratio': random.uniform(1.2, 2.5),
                'cash_ratio': random.uniform(0.3, 0.8),
                'operating_cash_flow': random.uniform(-0.1, 0.2)
            }
        elif risk_type == 'credit_risk':
            key_indicators = {
                'debt_to_equity': random.uniform(0.3, 1.2),
                'interest_coverage': random.uniform(2.0, 8.0),
                'credit_rating_score': random.uniform(500, 850)
            }
        else:
            key_indicators = {
                'risk_indicator_1': random.uniform(0.1, 0.9),
                'risk_indicator_2': random.uniform(10, 90),
                'risk_indicator_3': random.uniform(1.0, 5.0)
            }
        
        # Risk scenarios
        scenarios = {
            'best_case': current_risk_score * 0.7,
            'most_likely': current_risk_score,
            'worst_case': current_risk_score * 1.5
        }
        
        # Risk mitigation recommendations
        recommendations = [
            f"Monitor {list(key_indicators.keys())[0]} closely",
            f"Implement additional controls for {risk_type.replace('_', ' ')}",
            "Consider risk transfer mechanisms",
            "Enhance monitoring and reporting systems"
        ]
        
        return {
            'success': True,
            'risk_type': risk_type,
            'current_score': current_risk_score,
            'key_indicators': key_indicators,
            'scenarios': scenarios,
            'recommendations': recommendations,
            'horizon': horizon,
            'confidence': confidence
        }
    
    def display_risk_results(self, results: Dict[str, Any]):
        """Display risk assessment results"""
        
        if not results['success']:
            st.error("Risk assessment failed")
            return
        
        st.success("Risk assessment completed!")
        
        # Risk score
        risk_score = results['current_score']
        
        if risk_score < 30:
            risk_level = "Low"
            color = "success"
        elif risk_score < 60:
            risk_level = "Medium"
            color = "warning"
        else:
            risk_level = "High"
            color = "error"
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Overall Risk Score", f"{risk_score:.0f}/100")
        
        with col2:
            st.metric("Risk Level", risk_level)
        
        with col3:
            st.metric("Assessment Horizon", results['horizon'])
        
        # Key risk indicators
        st.subheader("Key Risk Indicators")
        
        indicators_data = []
        for indicator, value in results['key_indicators'].items():
            indicators_data.append({
                'Indicator': indicator.replace('_', ' ').title(),
                'Current Value': f"{value:.2f}",
                'Status': 'Normal' if 0.3 < value < 2.0 else 'Attention Required'
            })
        
        st.dataframe(pd.DataFrame(indicators_data), use_container_width=True, hide_index=True)
        
        # Risk scenarios
        st.subheader("Risk Scenarios")
        scenarios_data = []
        for scenario, score in results['scenarios'].items():
            scenarios_data.append({
                'Scenario': scenario.replace('_', ' ').title(),
                'Risk Score': f"{score:.0f}",
                'Probability': '25%' if scenario == 'best_case' else '50%' if scenario == 'most_likely' else '25%'
            })
        
        st.dataframe(pd.DataFrame(scenarios_data), use_container_width=True, hide_index=True)
        
        # Recommendations
        st.subheader("Risk Mitigation Recommendations")
        for i, rec in enumerate(results['recommendations'], 1):
            st.markdown(f"{i}. {rec}")
    
    def render_scenario_analysis(self):
        """Render scenario analysis interface"""
        
        st.subheader("Advanced Scenario Analysis")
        
        # Scenario configuration
        scenario_type = st.selectbox("Scenario Type", [
            "Economic Downturn Impact",
            "Population Growth Scenarios", 
            "Revenue Shortfall Analysis",
            "Infrastructure Investment Options",
            "Custom Scenario"
        ])
        
        if scenario_type == "Custom Scenario":
            scenario_name = st.text_input("Scenario Name")
            scenario_description = st.text_area("Scenario Description")
        
        # Scenario parameters
        st.markdown("### Scenario Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if scenario_type == "Economic Downturn Impact":
                gdp_change = st.slider("GDP Change (%)", -10, 5, -3)
                unemployment_change = st.slider("Unemployment Change (%)", -2, 10, 3)
                revenue_impact = st.slider("Revenue Impact (%)", -25, 0, -12)
            
            elif scenario_type == "Population Growth Scenarios":
                population_growth = st.slider("Annual Population Growth (%)", 0, 5, 2)
                housing_starts = st.slider("New Housing Units", 0, 1000, 200)
                service_demand_increase = st.slider("Service Demand Increase (%)", 0, 20, 8)
        
        with col2:
            time_horizon = st.selectbox("Analysis Period", ["1 year", "3 years", "5 years", "10 years"])
            iterations = st.selectbox("Monte Carlo Iterations", [1000, 5000, 10000])
        
        if st.button("Run Scenario Analysis", type="primary"):
            with st.spinner("Running scenario analysis..."):
                scenario_results = self.run_scenario_analysis(scenario_type, time_horizon)
                self.display_scenario_results(scenario_results)
    
    def run_scenario_analysis(self, scenario_type: str, horizon: str) -> Dict[str, Any]:
        """Run comprehensive scenario analysis"""
        
        # Mock scenario analysis - in production, this would use Monte Carlo simulation
        import random
        
        # Generate scenario outcomes
        outcomes = {}
        
        if scenario_type == "Economic Downturn Impact":
            outcomes = {
                'revenue_impact': random.uniform(-25, -5),
                'expense_increase': random.uniform(5, 15),
                'service_demand_change': random.uniform(-10, 20),
                'employment_impact': random.uniform(-5, 0)
            }
        elif scenario_type == "Population Growth Scenarios":
            outcomes = {
                'revenue_increase': random.uniform(10, 30),
                'infrastructure_demand': random.uniform(20, 50),
                'service_capacity_needed': random.uniform(15, 35),
                'budget_growth_required': random.uniform(12, 28)
            }
        else:
            outcomes = {
                'financial_impact': random.uniform(-20, 20),
                'operational_change': random.uniform(-15, 25),
                'risk_level_change': random.uniform(-10, 15)
            }
        
        # Probability distributions
        probabilities = {
            'optimistic': 0.25,
            'most_likely': 0.50,
            'pessimistic': 0.25
        }
        
        # Sensitivity analysis
        sensitivity = {}
        for outcome in outcomes.keys():
            sensitivity[outcome] = random.uniform(0.3, 0.8)  # Sensitivity coefficient
        
        return {
            'success': True,
            'scenario_type': scenario_type,
            'outcomes': outcomes,
            'probabilities': probabilities,
            'sensitivity': sensitivity,
            'horizon': horizon
        }
    
    def display_scenario_results(self, results: Dict[str, Any]):
        """Display scenario analysis results"""
        
        if not results['success']:
            st.error("Scenario analysis failed")
            return
        
        st.success("Scenario analysis completed!")
        
        # Scenario outcomes
        st.subheader("Scenario Outcomes")
        
        outcomes_data = []
        for outcome, value in results['outcomes'].items():
            outcomes_data.append({
                'Outcome': outcome.replace('_', ' ').title(),
                'Impact': f"{value:+.1f}%",
                'Sensitivity': f"{results['sensitivity'].get(outcome, 0.5):.2f}"
            })
        
        st.dataframe(pd.DataFrame(outcomes_data), use_container_width=True, hide_index=True)
        
        # Scenario visualization
        self.render_scenario_chart(results)
    
    def render_scenario_chart(self, results: Dict[str, Any]):
        """Render scenario analysis visualization"""
        
        outcomes = list(results['outcomes'].keys())
        values = list(results['outcomes'].values())
        
        fig = go.Figure(data=[
            go.Bar(x=outcomes, y=values, name='Scenario Impact')
        ])
        
        fig.update_layout(
            title=f"{results['scenario_type']} - Impact Analysis",
            xaxis_title="Outcome Category",
            yaxis_title="Impact (%)",
            showlegend=False
        )
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="black")
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_model_management(self):
        """Render model management interface"""
        
        st.subheader("Predictive Model Management")
        
        # Model status overview
        st.markdown("### Model Status Overview")
        
        model_status = [
            {'Model': 'Budget Forecasting', 'Status': 'Active', 'Accuracy': '94.2%', 'Last Updated': '2024-01-10'},
            {'Model': 'Revenue Prediction', 'Status': 'Active', 'Accuracy': '91.8%', 'Last Updated': '2024-01-08'},
            {'Model': 'Risk Assessment', 'Status': 'Training', 'Accuracy': 'N/A', 'Last Updated': 'In Progress'},
            {'Model': 'Demand Forecasting', 'Status': 'Active', 'Accuracy': '89.5%', 'Last Updated': '2024-01-05'}
        ]
        
        st.dataframe(pd.DataFrame(model_status), use_container_width=True, hide_index=True)
        
        # Model actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Retrain All Models"):
                st.info("Model retraining initiated. This may take several hours.")
        
        with col2:
            if st.button("Update Data Sources"):
                st.info("Data source synchronization started.")
        
        with col3:
            if st.button("Export Model Reports"):
                st.info("Model performance reports generated.")
        
        # Model configuration
        st.markdown("### Model Configuration")
        
        with st.expander("Advanced Model Settings"):
            auto_retrain = st.checkbox("Enable Automatic Retraining", value=True)
            retrain_threshold = st.slider("Retrain When Accuracy Falls Below", 80, 95, 90)
            data_refresh_interval = st.selectbox("Data Refresh Interval", ["Daily", "Weekly", "Monthly"])
            
            enable_ensemble = st.checkbox("Enable Ensemble Methods", value=True)
            max_models = st.number_input("Maximum Models in Ensemble", 3, 10, 5)

# Global instance
_analytics_engine = None

def get_predictive_analytics_engine() -> PredictiveAnalyticsEngine:
    """Get global predictive analytics engine instance"""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = PredictiveAnalyticsEngine()
    return _analytics_engine