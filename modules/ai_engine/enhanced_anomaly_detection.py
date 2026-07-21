"""
Enhanced Anomaly Detection System for GovSight
Advanced AI-powered transaction anomaly detection with municipal finance context
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

from modules.ai_engine.secure_ai_base import SecureAIBase, GOVSIGHT_AI_SECURITY

class EnhancedAnomalyDetection(SecureAIBase):
    """
    Advanced anomaly detection system for municipal financial transactions
    
    CAPABILITIES:
    - Multi-layer anomaly detection (statistical, ML, AI)
    - Transaction pattern analysis with municipal context
    - Vendor behavior monitoring
    - Budget variance anomaly detection
    - Fraud risk assessment
    - Automated investigation guidance
    """
    
    def __init__(self):
        super().__init__("EnhancedAnomalyDetection", GOVSIGHT_AI_SECURITY)
        
        # Anomaly detection models
        self.isolation_forest = IsolationForest(
            contamination=0.05,
            n_estimators=200,
            random_state=42
        )
        
        self.dbscan = DBSCAN(eps=0.5, min_samples=5)
        self.scaler = StandardScaler()
        
        # Municipal finance patterns
        self.municipal_patterns = {
            'seasonal_spending': {
                'snow_removal': [11, 12, 1, 2, 3],  # November through March
                'construction': [4, 5, 6, 7, 8, 9],  # April through September
                'budget_year_end': [11, 12],  # November, December
                'summer_programs': [6, 7, 8]  # June, July, August
            },
            'normal_vendor_patterns': {
                'utility_payments': {'frequency': 'monthly', 'variance': 0.15},
                'payroll': {'frequency': 'bi-weekly', 'variance': 0.05},
                'fuel': {'frequency': 'weekly', 'variance': 0.25},
                'maintenance': {'frequency': 'irregular', 'variance': 0.40}
            },
            'suspicious_patterns': {
                'round_numbers': [1000, 2500, 5000, 10000, 25000],
                'split_transactions': 'just_under_approval_limits',
                'weekend_transactions': 'non_emergency_only',
                'duplicate_vendors': 'similar_names_addresses'
            }
        }
    
    def comprehensive_anomaly_analysis(self, transaction_data: pd.DataFrame, 
                                     budget_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Perform comprehensive anomaly analysis on municipal transaction data
        
        Args:
            transaction_data: DataFrame with transaction records
            budget_data: Optional budget data for variance analysis
            
        Returns:
            Comprehensive anomaly analysis results
        """
        if transaction_data.empty:
            return {'error': 'No transaction data provided for analysis'}
        
        # Prepare data
        processed_data = self._prepare_transaction_data(transaction_data)
        
        results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_transactions': len(transaction_data),
            'anomaly_layers': {}
        }
        
        # Layer 1: Statistical Anomaly Detection
        results['anomaly_layers']['statistical'] = self._statistical_anomaly_detection(processed_data)
        
        # Layer 2: Machine Learning Anomaly Detection
        results['anomaly_layers']['machine_learning'] = self._ml_anomaly_detection(processed_data)
        
        # Layer 3: Municipal Pattern Analysis
        results['anomaly_layers']['municipal_patterns'] = self._municipal_pattern_analysis(processed_data)
        
        # Layer 4: Vendor Behavior Analysis
        results['anomaly_layers']['vendor_behavior'] = self._vendor_behavior_analysis(processed_data)
        
        # Layer 5: Budget Variance Analysis (if budget data provided)
        if budget_data is not None and not budget_data.empty:
            results['anomaly_layers']['budget_variance'] = self._budget_variance_analysis(
                processed_data, budget_data
            )
        
        # Consolidate anomalies and generate AI insights
        results['consolidated_anomalies'] = self._consolidate_anomalies(results['anomaly_layers'])
        results['ai_insights'] = self._generate_ai_insights(results['consolidated_anomalies'])
        
        # Risk scoring
        results['risk_assessment'] = self._calculate_risk_scores(results['consolidated_anomalies'])
        
        return results
    
    def _prepare_transaction_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare and enhance transaction data for anomaly detection"""
        data = df.copy()
        
        # Standardize column names
        column_mapping = {
            'amount': 'Amount',
            'vendor': 'Vendor',
            'date': 'Date',
            'description': 'Description',
            'department': 'Department',
            'account_code': 'AccountCode'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in data.columns and new_col not in data.columns:
                data[new_col] = data[old_col]
        
        # Ensure required columns exist
        required_columns = ['Amount', 'Date']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            st.error(f"Missing required columns: {missing_columns}")
            return pd.DataFrame()
        
        # Convert data types
        data['Amount'] = pd.to_numeric(data['Amount'], errors='coerce')
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        
        # Remove rows with invalid data
        data = data.dropna(subset=['Amount', 'Date'])
        
        # Add derived features
        data['Month'] = data['Date'].dt.month
        data['DayOfWeek'] = data['Date'].dt.dayofweek  # 0=Monday, 6=Sunday
        data['Hour'] = data['Date'].dt.hour
        data['IsWeekend'] = data['DayOfWeek'].isin([5, 6])
        data['IsRoundNumber'] = data['Amount'].apply(
            lambda x: x in self.municipal_patterns['suspicious_patterns']['round_numbers'] or x % 1000 == 0
        )
        
        # Vendor analysis
        if 'Vendor' in data.columns:
            data['VendorFrequency'] = data.groupby('Vendor')['Amount'].transform('count')
            data['VendorTotalSpend'] = data.groupby('Vendor')['Amount'].transform('sum')
            data['VendorAvgTransaction'] = data.groupby('Vendor')['Amount'].transform('mean')
        
        # Department analysis
        if 'Department' in data.columns:
            data['DeptTransactionCount'] = data.groupby('Department')['Amount'].transform('count')
            data['DeptTotalSpend'] = data.groupby('Department')['Amount'].transform('sum')
        
        return data
    
    def _statistical_anomaly_detection(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies using statistical methods"""
        anomalies = {
            'method': 'Statistical Analysis',
            'total_anomalies': 0,
            'anomaly_types': {}
        }
        
        # Z-score based outliers
        if len(data) > 10:  # Need sufficient data for statistical analysis
            z_scores = np.abs((data['Amount'] - data['Amount'].mean()) / data['Amount'].std())
            z_anomalies = data[z_scores > 3]  # 3 standard deviations
            
            anomalies['anomaly_types']['z_score_outliers'] = {
                'count': len(z_anomalies),
                'transactions': z_anomalies.to_dict('records') if len(z_anomalies) < 100 else [],
                'description': 'Transactions with amounts more than 3 standard deviations from mean'
            }
        
        # IQR based outliers
        Q1 = data['Amount'].quantile(0.25)
        Q3 = data['Amount'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        iqr_anomalies = data[(data['Amount'] < lower_bound) | (data['Amount'] > upper_bound)]
        
        anomalies['anomaly_types']['iqr_outliers'] = {
            'count': len(iqr_anomalies),
            'transactions': iqr_anomalies.to_dict('records') if len(iqr_anomalies) < 100 else [],
            'description': 'Transactions outside interquartile range boundaries'
        }
        
        # Time-based anomalies
        weekend_transactions = data[data['IsWeekend'] & (data['Amount'] > 1000)]  # Large weekend transactions
        after_hours = data[data['Hour'].isin([22, 23, 0, 1, 2, 3, 4, 5])]  # Late night/early morning
        
        anomalies['anomaly_types']['temporal_anomalies'] = {
            'weekend_large_transactions': {
                'count': len(weekend_transactions),
                'description': 'Large transactions (>$1000) on weekends'
            },
            'after_hours_transactions': {
                'count': len(after_hours),
                'description': 'Transactions processed outside normal business hours'
            }
        }
        
        anomalies['total_anomalies'] = sum(
            item['count'] if isinstance(item, dict) and 'count' in item 
            else sum(subitem['count'] for subitem in item.values() if isinstance(subitem, dict) and 'count' in subitem)
            for item in anomalies['anomaly_types'].values()
        )
        
        return anomalies
    
    def _ml_anomaly_detection(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies using machine learning algorithms"""
        if len(data) < 50:  # Need sufficient data for ML
            return {
                'method': 'Machine Learning',
                'error': 'Insufficient data for ML anomaly detection (minimum 50 transactions required)'
            }
        
        # Prepare features for ML
        feature_columns = ['Amount', 'Month', 'DayOfWeek', 'Hour']
        if 'VendorFrequency' in data.columns:
            feature_columns.extend(['VendorFrequency', 'VendorAvgTransaction'])
        if 'DeptTransactionCount' in data.columns:
            feature_columns.extend(['DeptTransactionCount'])
        
        # Filter data to only include rows with all required features
        ml_data = data[feature_columns].dropna()
        
        if len(ml_data) < 50:
            return {
                'method': 'Machine Learning',
                'error': 'Insufficient clean data for ML analysis'
            }
        
        # Scale features
        scaled_features = self.scaler.fit_transform(ml_data)
        
        # Isolation Forest
        iso_predictions = self.isolation_forest.fit_predict(scaled_features)
        iso_scores = self.isolation_forest.decision_function(scaled_features)
        
        # Mark anomalies
        ml_data['anomaly_score'] = iso_scores
        ml_data['is_anomaly'] = iso_predictions == -1
        
        anomalies_df = ml_data[ml_data['is_anomaly']]
        
        # DBSCAN for cluster-based anomalies
        cluster_labels = self.dbscan.fit_predict(scaled_features)
        outlier_mask = cluster_labels == -1
        cluster_anomalies = ml_data.iloc[outlier_mask]
        
        return {
            'method': 'Machine Learning',
            'isolation_forest': {
                'total_anomalies': len(anomalies_df),
                'anomaly_percentage': len(anomalies_df) / len(ml_data) * 100,
                'top_anomalies': anomalies_df.nlargest(10, 'Amount').to_dict('records')
            },
            'dbscan_clustering': {
                'total_outliers': len(cluster_anomalies),
                'outlier_percentage': len(cluster_anomalies) / len(ml_data) * 100,
                'clusters_found': len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
            }
        }
    
    def _municipal_pattern_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze transactions for municipal-specific suspicious patterns"""
        patterns = {
            'method': 'Municipal Pattern Analysis',
            'pattern_violations': {}
        }
        
        # Round number analysis
        round_number_transactions = data[data['IsRoundNumber']]
        if len(round_number_transactions) > len(data) * 0.2:  # More than 20% are round numbers
            patterns['pattern_violations']['excessive_round_numbers'] = {
                'count': len(round_number_transactions),
                'percentage': len(round_number_transactions) / len(data) * 100,
                'concern_level': 'Medium',
                'description': 'Unusually high percentage of round-number transactions'
            }
        
        # Seasonal spending pattern analysis
        current_month = datetime.now().month
        seasonal_categories = self.municipal_patterns['seasonal_spending']
        
        for category, expected_months in seasonal_categories.items():
            if current_month not in expected_months:
                # Check if there's unusual spending in this category during off-season
                category_keywords = {
                    'snow_removal': ['snow', 'salt', 'plow', 'ice'],
                    'construction': ['construction', 'paving', 'concrete'],
                    'summer_programs': ['camp', 'pool', 'recreation']
                }
                
                if category in category_keywords and 'Description' in data.columns:
                    category_transactions = data[
                        data['Description'].str.contains(
                            '|'.join(category_keywords[category]), 
                            case=False, na=False
                        )
                    ]
                    
                    if len(category_transactions) > 0:
                        patterns['pattern_violations'][f'off_season_{category}'] = {
                            'count': len(category_transactions),
                            'total_amount': category_transactions['Amount'].sum(),
                            'concern_level': 'Low',
                            'description': f'Off-season spending on {category}'
                        }
        
        # Duplicate vendor detection (similar names)
        if 'Vendor' in data.columns:
            vendors = data['Vendor'].dropna().unique()
            potential_duplicates = []
            
            for i, vendor1 in enumerate(vendors):
                for vendor2 in vendors[i+1:]:
                    # Simple similarity check (Levenshtein distance would be better)
                    if (len(vendor1) > 5 and len(vendor2) > 5 and 
                        vendor1.lower()[:5] == vendor2.lower()[:5]):
                        potential_duplicates.append((vendor1, vendor2))
            
            if potential_duplicates:
                patterns['pattern_violations']['potential_duplicate_vendors'] = {
                    'pairs': potential_duplicates[:10],  # Top 10 pairs
                    'count': len(potential_duplicates),
                    'concern_level': 'Medium',
                    'description': 'Vendors with similar names that may be duplicates'
                }
        
        return patterns
    
    def _vendor_behavior_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze vendor behavior patterns for anomalies"""
        if 'Vendor' not in data.columns:
            return {'method': 'Vendor Behavior Analysis', 'error': 'No vendor information available'}
        
        vendor_analysis = {
            'method': 'Vendor Behavior Analysis',
            'vendor_anomalies': {}
        }
        
        # Vendor statistics
        vendor_stats = data.groupby('Vendor').agg({
            'Amount': ['count', 'sum', 'mean', 'std'],
            'Date': ['min', 'max']
        }).round(2)
        
        vendor_stats.columns = ['TransactionCount', 'TotalSpend', 'AvgTransaction', 'StdTransaction', 'FirstTransaction', 'LastTransaction']
        vendor_stats = vendor_stats.reset_index()
        
        # Flag suspicious vendor patterns
        suspicious_vendors = []
        
        for _, vendor_row in vendor_stats.iterrows():
            vendor_name = vendor_row['Vendor']
            flags = []
            
            # High-value, low-frequency vendors
            if (vendor_row['TransactionCount'] <= 2 and 
                vendor_row['TotalSpend'] > data['Amount'].quantile(0.95)):
                flags.append('High value, low frequency')
            
            # Vendors with very regular amounts (potential duplicate/fraudulent)
            if (vendor_row['TransactionCount'] > 5 and 
                vendor_row['StdTransaction'] < vendor_row['AvgTransaction'] * 0.1):
                flags.append('Suspiciously regular transaction amounts')
            
            # New vendors with large transactions
            days_active = (pd.Timestamp.now() - vendor_row['FirstTransaction']).days
            if (days_active < 30 and 
                vendor_row['TotalSpend'] > data['Amount'].quantile(0.9)):
                flags.append('New vendor with large spending')
            
            if flags:
                vendor_data = data[data['Vendor'] == vendor_name]
                suspicious_vendors.append({
                    'vendor': vendor_name,
                    'flags': flags,
                    'transaction_count': int(vendor_row['TransactionCount']),
                    'total_spend': float(vendor_row['TotalSpend']),
                    'avg_transaction': float(vendor_row['AvgTransaction']),
                    'transactions': vendor_data.to_dict('records')
                })
        
        vendor_analysis['vendor_anomalies']['suspicious_vendors'] = suspicious_vendors
        vendor_analysis['vendor_anomalies']['total_flagged'] = len(suspicious_vendors)
        
        return vendor_analysis
    
    def _budget_variance_analysis(self, transaction_data: pd.DataFrame, 
                                budget_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze budget vs actual spending for anomalies"""
        variance_analysis = {
            'method': 'Budget Variance Analysis',
            'variances': {}
        }
        
        # Match transactions to budget categories
        if 'Department' in transaction_data.columns and 'Department' in budget_data.columns:
            dept_spending = transaction_data.groupby('Department')['Amount'].sum()
            
            for dept in dept_spending.index:
                if dept in budget_data['Department'].values:
                    budget_row = budget_data[budget_data['Department'] == dept].iloc[0]
                    budgeted = budget_row.get('Budget', 0)
                    actual = dept_spending[dept]
                    variance = ((actual - budgeted) / budgeted * 100) if budgeted > 0 else 0
                    
                    if abs(variance) > 20:  # More than 20% variance
                        variance_analysis['variances'][dept] = {
                            'budgeted': float(budgeted),
                            'actual': float(actual),
                            'variance_percent': float(variance),
                            'variance_amount': float(actual - budgeted),
                            'concern_level': 'High' if abs(variance) > 50 else 'Medium'
                        }
        
        return variance_analysis
    
    def _consolidate_anomalies(self, anomaly_layers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Consolidate anomalies from all detection layers"""
        consolidated = []
        
        # Process each layer
        for layer_name, layer_data in anomaly_layers.items():
            if 'error' in layer_data:
                continue
                
            if layer_name == 'statistical':
                for anomaly_type, details in layer_data.get('anomaly_types', {}).items():
                    if isinstance(details, dict) and details.get('count', 0) > 0:
                        consolidated.append({
                            'layer': 'Statistical',
                            'type': anomaly_type,
                            'count': details['count'],
                            'severity': self._calculate_severity(details['count'], anomaly_type),
                            'description': details.get('description', ''),
                            'transactions': details.get('transactions', [])
                        })
            
            elif layer_name == 'machine_learning':
                for ml_method, details in layer_data.items():
                    if ml_method != 'method' and isinstance(details, dict):
                        anomaly_count = details.get('total_anomalies', details.get('total_outliers', 0))
                        if anomaly_count > 0:
                            consolidated.append({
                                'layer': 'Machine Learning',
                                'type': ml_method,
                                'count': anomaly_count,
                                'severity': self._calculate_severity(anomaly_count, ml_method),
                                'percentage': details.get('anomaly_percentage', details.get('outlier_percentage', 0)),
                                'transactions': details.get('top_anomalies', [])
                            })
            
            elif layer_name == 'municipal_patterns':
                for pattern_type, details in layer_data.get('pattern_violations', {}).items():
                    consolidated.append({
                        'layer': 'Municipal Patterns',
                        'type': pattern_type,
                        'count': details.get('count', 0),
                        'severity': details.get('concern_level', 'Medium'),
                        'description': details.get('description', ''),
                        'amount': details.get('total_amount', 0)
                    })
            
            # Similar processing for other layers...
        
        # Sort by severity and count
        severity_order = {'High': 3, 'Medium': 2, 'Low': 1}
        consolidated.sort(key=lambda x: (severity_order.get(x.get('severity', 'Low'), 1), x.get('count', 0)), reverse=True)
        
        return consolidated
    
    def _calculate_severity(self, count: int, anomaly_type: str) -> str:
        """Calculate severity level based on anomaly count and type"""
        high_risk_types = ['z_score_outliers', 'isolation_forest', 'suspicious_vendors']
        
        if anomaly_type in high_risk_types:
            if count > 20:
                return 'High'
            elif count > 5:
                return 'Medium'
            else:
                return 'Low'
        else:
            if count > 50:
                return 'High'
            elif count > 10:
                return 'Medium'
            else:
                return 'Low'
    
    def _generate_ai_insights(self, consolidated_anomalies: List[Dict[str, Any]]) -> str:
        """Generate AI-powered insights and recommendations"""
        if not consolidated_anomalies:
            return "No significant anomalies detected. Financial transactions appear to follow normal patterns."
        
        # Prepare anomaly summary for AI analysis
        anomaly_summary = []
        for anomaly in consolidated_anomalies[:10]:  # Top 10 anomalies
            summary = f"- {anomaly['layer']}: {anomaly['type']} ({anomaly['count']} instances, {anomaly.get('severity', 'Unknown')} severity)"
            if anomaly.get('percentage'):
                summary += f" - {anomaly['percentage']:.1f}% of transactions"
            anomaly_summary.append(summary)
        
        insights_prompt = f"""
        Analyze these financial transaction anomalies detected in a municipal government system:
        
        DETECTED ANOMALIES:
        {chr(10).join(anomaly_summary)}
        
        Provide professional analysis including:
        
        1. PRIORITY ASSESSMENT: Which anomalies require immediate attention vs routine monitoring
        
        2. POTENTIAL CAUSES: Most likely explanations for each type of anomaly
        
        3. INVESTIGATION STEPS: Specific actions the finance team should take
        
        4. RISK MITIGATION: Recommended controls to prevent future anomalies
        
        5. COMPLIANCE CONSIDERATIONS: Any regulatory or audit implications
        
        Format as a clear, actionable report for municipal finance directors.
        """
        
        ai_response = self.secure_ai_request(
            insights_prompt,
            "anomaly_insights_generation",
            data_sources=["transaction_anomalies"],
            max_tokens=2000
        )
        
        return ai_response.get('response', 'AI insights generation failed')
    
    def _calculate_risk_scores(self, consolidated_anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall risk scores based on detected anomalies"""
        if not consolidated_anomalies:
            return {
                'overall_risk_score': 0,
                'risk_level': 'Low',
                'key_risk_factors': []
            }
        
        # Calculate weighted risk score
        severity_weights = {'High': 10, 'Medium': 5, 'Low': 2}
        total_score = 0
        max_possible_score = 0
        
        for anomaly in consolidated_anomalies:
            severity = anomaly.get('severity', 'Low')
            count = anomaly.get('count', 0)
            weight = severity_weights.get(severity, 2)
            
            # Score based on severity and frequency
            anomaly_score = min(weight * np.log1p(count), weight * 5)  # Cap individual scores
            total_score += anomaly_score
            max_possible_score += weight * 5
        
        # Normalize to 0-100 scale
        risk_score = (total_score / max(max_possible_score, 1)) * 100 if max_possible_score > 0 else 0
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = 'High'
        elif risk_score >= 40:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        # Identify key risk factors
        key_risk_factors = [
            f"{anomaly['type']} ({anomaly['count']} instances)"
            for anomaly in consolidated_anomalies[:5]
            if anomaly.get('severity') in ['High', 'Medium']
        ]
        
        return {
            'overall_risk_score': round(risk_score, 1),
            'risk_level': risk_level,
            'key_risk_factors': key_risk_factors,
            'total_anomalies': len(consolidated_anomalies),
            'high_severity_count': len([a for a in consolidated_anomalies if a.get('severity') == 'High'])
        }