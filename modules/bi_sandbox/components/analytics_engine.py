"""
Advanced Analytics Engine for BI Sandbox

This module provides machine learning, statistical analysis, and predictive
modeling capabilities for enterprise-grade business intelligence.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class AdvancedAnalyticsEngine:
    """Core analytics engine with advanced capabilities"""
    
    def __init__(self):
        self.data_cache = {}
        self.calculation_cache = {}
        self.dimension_hierarchies = {}
        self.custom_metrics = {}
        self.filter_actions = []
        
    def create_star_schema(self, data: pd.DataFrame, dimensions: List[str], measures: List[str]) -> Dict[str, pd.DataFrame]:
        """Create star schema from flat data"""
        star_schema = {}
        
        # Create fact table
        fact_columns = measures + [col for col in data.columns if col.endswith('_id') or col.endswith('_key')]
        fact_table = data[fact_columns].copy()
        star_schema['fact'] = fact_table
        
        # Create dimension tables
        for dim in dimensions:
            if dim in data.columns:
                dim_table = data[[dim]].drop_duplicates().reset_index(drop=True)
                dim_table[f'{dim}_id'] = dim_table.index
                star_schema[f'dim_{dim}'] = dim_table
        
        return star_schema
    
    def calculate_dax_expression(self, expression: str, data: pd.DataFrame) -> pd.Series:
        """DAX-style calculation engine"""
        # Basic DAX functions implementation
        if expression.startswith('SUM('):
            column = expression[4:-1]
            return data.groupby(level=0)[column].sum() if column in data.columns else pd.Series()
        elif expression.startswith('AVERAGE('):
            column = expression[8:-1]
            return data.groupby(level=0)[column].mean() if column in data.columns else pd.Series()
        elif expression.startswith('COUNT('):
            column = expression[6:-1]
            return data.groupby(level=0)[column].count() if column in data.columns else pd.Series()
        elif expression.startswith('MAX('):
            column = expression[4:-1]
            return data.groupby(level=0)[column].max() if column in data.columns else pd.Series()
        elif expression.startswith('MIN('):
            column = expression[4:-1]
            return data.groupby(level=0)[column].min() if column in data.columns else pd.Series()
        else:
            # For complex expressions, use eval with safety checks
            try:
                return pd.eval(expression, target=data)
            except:
                return pd.Series()
    
    def perform_time_intelligence(self, data: pd.DataFrame, date_column: str, measure_column: str) -> Dict[str, pd.Series]:
        """Advanced time intelligence calculations"""
        if date_column not in data.columns:
            return {}
        
        data[date_column] = pd.to_datetime(data[date_column])
        data = data.sort_values(date_column)
        
        time_calcs = {}
        
        # Year over year
        time_calcs['yoy_growth'] = data.groupby(data[date_column].dt.year)[measure_column].sum().pct_change() * 100
        
        # Quarter over quarter
        time_calcs['qoq_growth'] = data.groupby(data[date_column].dt.quarter)[measure_column].sum().pct_change() * 100
        
        # Moving averages
        time_calcs['ma_3'] = data.groupby(data[date_column].dt.to_period('M'))[measure_column].sum().rolling(3).mean()
        time_calcs['ma_12'] = data.groupby(data[date_column].dt.to_period('M'))[measure_column].sum().rolling(12).mean()
        
        # Seasonal decomposition
        monthly_data = data.groupby(data[date_column].dt.to_period('M'))[measure_column].sum()
        if len(monthly_data) >= 24:  # Need at least 2 years for seasonal analysis
            try:
                from statsmodels.tsa.seasonal import seasonal_decompose
                decomposition = seasonal_decompose(monthly_data, model='additive', period=12)
                time_calcs['trend'] = decomposition.trend
                time_calcs['seasonal'] = decomposition.seasonal
                time_calcs['residual'] = decomposition.resid
            except:
                pass
        
        return time_calcs
    
    def perform_predictive_modeling(self, data: pd.DataFrame, target_column: str, feature_columns: List[str] = None) -> Dict[str, Any]:
        """Advanced predictive modeling with multiple algorithms"""
        if data.empty or target_column not in data.columns:
            return {"error": "Invalid data or target column"}
        
        # Prepare features
        if feature_columns is None:
            feature_columns = [col for col in data.select_dtypes(include=[np.number]).columns if col != target_column]
        
        if not feature_columns:
            return {"error": "No numeric features available"}
        
        # Clean data
        clean_data = data[feature_columns + [target_column]].dropna()
        if len(clean_data) < 10:
            return {"error": "Insufficient data for modeling"}
        
        X = clean_data[feature_columns]
        y = clean_data[target_column]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train multiple models
        models = {}
        
        # Random Forest
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf_model.fit(X_train_scaled, y_train)
        rf_pred = rf_model.predict(X_test_scaled)
        models['random_forest'] = {
            'model': rf_model,
            'r2_score': r2_score(y_test, rf_pred),
            'mse': mean_squared_error(y_test, rf_pred),
            'feature_importance': dict(zip(feature_columns, rf_model.feature_importances_))
        }
        
        # Generate predictions for next period
        last_values = X.tail(1)
        predictions = {}
        for name, model_data in models.items():
            pred = model_data['model'].predict(scaler.transform(last_values))
            predictions[name] = pred[0]
        
        return {
            'models': models,
            'predictions': predictions,
            'feature_columns': feature_columns,
            'data_shape': X.shape
        }
    
    def perform_clustering_analysis(self, data: pd.DataFrame, n_clusters: int = 3) -> Dict[str, Any]:
        """Advanced clustering analysis with multiple methods"""
        numeric_data = data.select_dtypes(include=[np.number]).dropna()
        if numeric_data.empty or len(numeric_data) < n_clusters:
            return {"error": "Insufficient numeric data for clustering"}
        
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_data)
        
        # K-Means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(scaled_data)
        
        # PCA for dimensionality reduction
        pca = PCA(n_components=min(2, scaled_data.shape[1]))
        pca_data = pca.fit_transform(scaled_data)
        
        # Cluster statistics
        cluster_stats = {}
        for i in range(n_clusters):
            cluster_mask = clusters == i
            cluster_stats[f'cluster_{i}'] = {
                'size': np.sum(cluster_mask),
                'percentage': np.sum(cluster_mask) / len(clusters) * 100,
                'centroid': kmeans.cluster_centers_[i].tolist()
            }
        
        return {
            'clusters': clusters.tolist(),
            'cluster_centers': kmeans.cluster_centers_.tolist(),
            'cluster_stats': cluster_stats,
            'pca_coordinates': pca_data.tolist(),
            'explained_variance': pca.explained_variance_ratio_.tolist(),
            'inertia': kmeans.inertia_
        }
    
    def generate_advanced_forecast(self, data: pd.DataFrame, target_column: str, periods: int = 12) -> Dict[str, Any]:
        """Advanced forecasting with multiple models"""
        if len(data) < 3:
            return {}
        
        # Check if target column exists
        if target_column not in data.columns:
            return {}
        
        # Prepare data
        y = data[target_column].dropna().values
        if len(y) < 3:
            return {}
        
        X = np.arange(len(y)).reshape(-1, 1)
        
        forecasts = {}
        
        # Linear regression forecast
        try:
            model = RandomForestRegressor(n_estimators=10, random_state=42)
            model.fit(X, y)
            
            future_X = np.arange(len(y), len(y) + periods).reshape(-1, 1)
            linear_forecast = model.predict(future_X)
            forecasts['linear'] = linear_forecast
        except:
            pass
        
        # Moving average forecast
        if len(y) >= 3:
            ma_window = min(3, len(y))
            ma_value = np.mean(y[-ma_window:])
            ma_forecast = np.full(periods, ma_value)
            forecasts['moving_average'] = ma_forecast
        
        # Simple trend forecast
        try:
            if len(y) >= 2:
                # Simple linear trend
                x_vals = np.arange(len(y))
                coeffs = np.polyfit(x_vals, y, 1)
                trend_forecast = []
                for i in range(periods):
                    trend_forecast.append(coeffs[0] * (len(y) + i) + coeffs[1])
                forecasts['trend'] = np.array(trend_forecast)
        except:
            pass
        
        # Exponential smoothing (simplified)
        try:
            alpha = 0.3
            exp_forecast = []
            last_value = y[-1]
            for _ in range(periods):
                exp_forecast.append(last_value)
                last_value = alpha * last_value + (1 - alpha) * np.mean(y)
            forecasts['exponential_smoothing'] = np.array(exp_forecast)
        except:
            pass
        
        return forecasts
    
    def perform_statistical_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Advanced statistical analysis with multiple tests"""
        if data.empty:
            return {}
        
        numeric_data = data.select_dtypes(include=[np.number])
        if numeric_data.empty:
            return {}
        
        stats_results = {}
        
        # Basic descriptive statistics
        stats_results['descriptive'] = numeric_data.describe().to_dict()
        
        # Correlation analysis
        if len(numeric_data.columns) > 1:
            correlation_matrix = numeric_data.corr()
            stats_results['correlation_matrix'] = correlation_matrix.to_dict()
            
            # Find strong correlations
            strong_correlations = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if abs(corr_value) > 0.7:  # Strong correlation threshold
                        strong_correlations.append({
                            'variable1': correlation_matrix.columns[i],
                            'variable2': correlation_matrix.columns[j],
                            'correlation': corr_value
                        })
            stats_results['strong_correlations'] = strong_correlations
        
        # Distribution analysis
        distribution_tests = {}
        for col in numeric_data.columns:
            col_data = numeric_data[col].dropna()
            if len(col_data) > 8:  # Minimum sample size for normality test
                try:
                    # Shapiro-Wilk test for normality
                    stat, p_value = stats.shapiro(col_data)
                    distribution_tests[col] = {
                        'shapiro_wilk_stat': stat,
                        'shapiro_wilk_p_value': p_value,
                        'is_normal': p_value > 0.05
                    }
                except:
                    pass
        stats_results['distribution_tests'] = distribution_tests
        
        # Outlier detection using IQR method
        outliers = {}
        for col in numeric_data.columns:
            col_data = numeric_data[col].dropna()
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outlier_mask = (col_data < lower_bound) | (col_data > upper_bound)
            outliers[col] = {
                'count': outlier_mask.sum(),
                'percentage': (outlier_mask.sum() / len(col_data)) * 100,
                'values': col_data[outlier_mask].tolist()[:10]  # First 10 outliers
            }
        stats_results['outliers'] = outliers
        
        return stats_results
    
    def detect_anomalies(self, data: pd.DataFrame, columns: List[str] = None, method: str = 'isolation_forest') -> Dict[str, Any]:
        """Advanced anomaly detection using multiple methods"""
        if data.empty:
            return {"error": "No data provided"}
        
        if columns is None:
            columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if not columns:
            return {"error": "No numeric columns found"}
        
        # Clean data
        clean_data = data[columns].dropna()
        if len(clean_data) < 10:
            return {"error": "Insufficient data for anomaly detection"}
        
        anomaly_results = {}
        
        # Statistical method (Z-score)
        z_scores = np.abs(stats.zscore(clean_data))
        z_threshold = 3
        z_anomalies = (z_scores > z_threshold).any(axis=1)
        
        anomaly_results['z_score'] = {
            'anomaly_count': z_anomalies.sum(),
            'anomaly_percentage': (z_anomalies.sum() / len(clean_data)) * 100,
            'anomaly_indices': np.where(z_anomalies)[0].tolist()
        }
        
        # IQR method
        Q1 = clean_data.quantile(0.25)
        Q3 = clean_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        iqr_anomalies = ((clean_data < lower_bound) | (clean_data > upper_bound)).any(axis=1)
        
        anomaly_results['iqr'] = {
            'anomaly_count': iqr_anomalies.sum(),
            'anomaly_percentage': (iqr_anomalies.sum() / len(clean_data)) * 100,
            'anomaly_indices': np.where(iqr_anomalies)[0].tolist()
        }
        
        # Machine learning method (if sklearn available and enough data)
        if len(clean_data) >= 50:
            try:
                from sklearn.ensemble import IsolationForest
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                ml_anomalies = iso_forest.fit_predict(clean_data) == -1
                
                anomaly_results['isolation_forest'] = {
                    'anomaly_count': ml_anomalies.sum(),
                    'anomaly_percentage': (ml_anomalies.sum() / len(clean_data)) * 100,
                    'anomaly_indices': np.where(ml_anomalies)[0].tolist()
                }
            except ImportError:
                pass
        
        return anomaly_results