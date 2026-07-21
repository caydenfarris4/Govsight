"""
Anomaly Detection Pipeline
Uses machine learning to detect anomalies in financial transactions

Features:
- Transaction anomaly detection using Isolation Forest
- Feature engineering for financial patterns
- Department-specific anomaly analysis
- Visualization and reporting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import json
import os


class AnomalyDetector:
    """Base anomaly detector with configurable algorithms"""
    
    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        """
        Initialize anomaly detector
        
        Args:
            contamination: Expected proportion of outliers
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.anomaly_scores = None
        
    def fit(self, X: pd.DataFrame) -> 'AnomalyDetector':
        """Fit the anomaly detection model"""
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Initialize and fit Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
            max_samples='auto'
        )
        self.model.fit(X_scaled)
        
        # Store feature names
        self.feature_names = list(X.columns)
        
        return self
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict anomalies
        
        Returns:
            Tuple of (predictions, anomaly_scores)
            predictions: 1 for normal, -1 for anomaly
            anomaly_scores: Lower scores indicate anomalies
        """
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        return predictions, scores
    
    def get_anomaly_details(self, X: pd.DataFrame, predictions: np.ndarray, 
                           scores: np.ndarray) -> pd.DataFrame:
        """Get detailed anomaly information"""
        results = X.copy()
        results['is_anomaly'] = predictions == -1
        results['anomaly_score'] = scores
        results['confidence'] = 1 - (scores - scores.min()) / (scores.max() - scores.min())
        
        return results


class TransactionAnomalyDetector:
    """Specialized anomaly detector for financial transactions"""
    
    def __init__(self, db_path: str = None):
        """Initialize transaction anomaly detector"""
        self.db_path = db_path or "databases/core/caselle_gl0_mock.db"
        self.detector = AnomalyDetector()
        self.transaction_data = None
        self.feature_data = None
        self.anomalies = None
        self.department_stats = {}
        self.vendor_stats = {}
        
    def load_transaction_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Load transaction data from database"""
        try:
            # Get absolute path
            if not os.path.isabs(self.db_path):
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                self.db_path = os.path.join(project_root, self.db_path)
            
            conn = sqlite3.connect(self.db_path)
            
            # Query GL transactions
            query = """
            SELECT 
                TransactionID,
                Date,
                Amount,
                Description,
                AccountCode,
                DepartmentCode,
                FundCode,
                VendorID,
                TransactionType,
                Period,
                FiscalYear
            FROM GL0
            WHERE Amount != 0
            """
            
            if start_date and end_date:
                query += f" AND Date BETWEEN '{start_date}' AND '{end_date}'"
            
            query += " ORDER BY Date DESC"
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Convert date column
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Add time-based features
            df['Month'] = df['Date'].dt.month
            df['Quarter'] = df['Date'].dt.quarter
            df['DayOfWeek'] = df['Date'].dt.dayofweek
            df['DayOfMonth'] = df['Date'].dt.day
            
            self.transaction_data = df
            return df
            
        except Exception as e:
            print(f"Error loading transaction data: {e}")
            # Return sample data for testing
            return self._generate_sample_data()
    
    def _generate_sample_data(self) -> pd.DataFrame:
        """Generate sample transaction data for testing"""
        np.random.seed(42)
        n_samples = 1000
        
        # Generate dates
        dates = pd.date_range(end=datetime.now(), periods=n_samples, freq='D')
        
        # Generate departments
        departments = np.random.choice(['Police', 'Fire', 'Public Works', 'Admin', 'Parks'], n_samples)
        
        # Generate amounts with some anomalies
        amounts = np.random.lognormal(8, 2, n_samples)
        # Add some anomalies
        anomaly_indices = np.random.choice(n_samples, size=int(n_samples * 0.05), replace=False)
        amounts[anomaly_indices] *= np.random.uniform(5, 10, len(anomaly_indices))
        
        df = pd.DataFrame({
            'TransactionID': range(1, n_samples + 1),
            'Date': dates,
            'Amount': amounts,
            'Description': [f'Transaction {i}' for i in range(n_samples)],
            'AccountCode': np.random.choice(['1000', '2000', '3000', '4000'], n_samples),
            'DepartmentCode': departments,
            'FundCode': np.random.choice(['100', '200', '300'], n_samples),
            'VendorID': np.random.choice(range(1, 50), n_samples),
            'TransactionType': np.random.choice(['Expense', 'Revenue'], n_samples, p=[0.8, 0.2]),
            'Period': np.random.choice(range(1, 13), n_samples),
            'FiscalYear': np.random.choice([2024, 2025], n_samples)
        })
        
        # Add time features
        df['Month'] = df['Date'].dt.month
        df['Quarter'] = df['Date'].dt.quarter
        df['DayOfWeek'] = df['Date'].dt.dayofweek
        df['DayOfMonth'] = df['Date'].dt.day
        
        self.transaction_data = df
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for anomaly detection"""
        features = pd.DataFrame()
        
        # Amount-based features
        features['amount'] = df['Amount'].abs()
        features['log_amount'] = np.log1p(df['Amount'].abs())
        
        # Calculate department statistics
        dept_stats = df.groupby('DepartmentCode')['Amount'].agg(['mean', 'std', 'median'])
        self.department_stats = dept_stats.to_dict('index')
        
        # Department deviation features
        df['dept_mean'] = df['DepartmentCode'].map(lambda x: self.department_stats.get(x, {}).get('mean', 0))
        df['dept_std'] = df['DepartmentCode'].map(lambda x: self.department_stats.get(x, {}).get('std', 1))
        features['dept_z_score'] = (df['Amount'] - df['dept_mean']) / df['dept_std'].replace(0, 1)
        
        # Vendor statistics
        vendor_stats = df.groupby('VendorID')['Amount'].agg(['mean', 'std', 'count'])
        self.vendor_stats = vendor_stats.to_dict('index')
        
        # Vendor features
        df['vendor_mean'] = df['VendorID'].map(lambda x: self.vendor_stats.get(x, {}).get('mean', 0))
        df['vendor_count'] = df['VendorID'].map(lambda x: self.vendor_stats.get(x, {}).get('count', 0))
        features['vendor_deviation'] = (df['Amount'] - df['vendor_mean']).abs()
        features['vendor_frequency'] = df['vendor_count']
        
        # Temporal features
        features['month'] = df['Month']
        features['quarter'] = df['Quarter']
        features['day_of_week'] = df['DayOfWeek']
        features['day_of_month'] = df['DayOfMonth']
        
        # Seasonal patterns
        monthly_avg = df.groupby('Month')['Amount'].mean()
        df['monthly_avg'] = df['Month'].map(monthly_avg)
        features['seasonal_deviation'] = (df['Amount'] - df['monthly_avg']).abs()
        
        # Transaction type encoding
        features['is_expense'] = (df['TransactionType'] == 'Expense').astype(int)
        
        # Rolling statistics (if enough data)
        if len(df) > 30:
            df_sorted = df.sort_values('Date')
            features['rolling_mean_7d'] = df_sorted['Amount'].rolling(window=7, min_periods=1).mean()
            features['rolling_std_7d'] = df_sorted['Amount'].rolling(window=7, min_periods=1).std()
            features['rolling_mean_30d'] = df_sorted['Amount'].rolling(window=30, min_periods=1).mean()
        
        # Fill any NaN values
        features = features.fillna(0)
        
        self.feature_data = features
        return features
    
    def detect_anomalies(self, contamination: float = 0.05) -> pd.DataFrame:
        """Run anomaly detection on transactions"""
        if self.transaction_data is None:
            self.load_transaction_data()
        
        # Engineer features
        features = self.engineer_features(self.transaction_data)
        
        # Initialize and train detector
        self.detector = AnomalyDetector(contamination=contamination)
        self.detector.fit(features)
        
        # Predict anomalies
        predictions, scores = self.detector.predict(features)
        
        # Create results dataframe
        results = self.transaction_data.copy()
        results['is_anomaly'] = predictions == -1
        results['anomaly_score'] = scores
        results['confidence'] = 1 - (scores - scores.min()) / (scores.max() - scores.min())
        
        # Add reason for anomaly
        results['anomaly_reason'] = self._determine_anomaly_reason(results, features)
        
        # Sort by anomaly score
        results = results.sort_values('anomaly_score')
        
        self.anomalies = results[results['is_anomaly']]
        
        return results
    
    def _determine_anomaly_reason(self, results: pd.DataFrame, features: pd.DataFrame) -> List[str]:
        """Determine the reason for each anomaly"""
        reasons = []
        
        for idx, row in results.iterrows():
            if not row['is_anomaly']:
                reasons.append("")
                continue
            
            reason_parts = []
            
            # Check amount deviation
            if abs(features.loc[idx, 'dept_z_score']) > 3:
                reason_parts.append(f"Unusual amount for {row['DepartmentCode']} department")
            
            # Check vendor pattern
            if features.loc[idx, 'vendor_deviation'] > self.vendor_stats.get(row['VendorID'], {}).get('std', 0) * 3:
                reason_parts.append(f"Unusual payment to vendor {row['VendorID']}")
            
            # Check seasonal pattern
            if features.loc[idx, 'seasonal_deviation'] > results['Amount'].std() * 2:
                reason_parts.append("Deviates from seasonal pattern")
            
            # Default reason
            if not reason_parts:
                reason_parts.append("Statistical outlier")
            
            reasons.append("; ".join(reason_parts))
        
        return reasons
    
    def create_anomaly_visualizations(self) -> Dict[str, go.Figure]:
        """Create visualizations for anomaly detection results"""
        if self.anomalies is None:
            self.detect_anomalies()
        
        visualizations = {}
        
        # 1. Time series with anomalies highlighted
        fig_timeline = go.Figure()
        
        # Normal transactions
        normal_data = self.transaction_data[~self.transaction_data['TransactionID'].isin(self.anomalies['TransactionID'])]
        fig_timeline.add_trace(go.Scatter(
            x=normal_data['Date'],
            y=normal_data['Amount'],
            mode='markers',
            name='Normal',
            marker=dict(color='blue', size=5, opacity=0.5)
        ))
        
        # Anomalies
        fig_timeline.add_trace(go.Scatter(
            x=self.anomalies['Date'],
            y=self.anomalies['Amount'],
            mode='markers',
            name='Anomaly',
            marker=dict(color='red', size=10, symbol='star'),
            text=self.anomalies['anomaly_reason'],
            hovertemplate='<b>Anomaly</b><br>Amount: $%{y:,.2f}<br>%{text}<extra></extra>'
        ))
        
        fig_timeline.update_layout(
            title='Transaction Anomalies Over Time',
            xaxis_title='Date',
            yaxis_title='Amount ($)',
            hovermode='closest'
        )
        
        visualizations['timeline'] = fig_timeline
        
        # 2. Department-wise anomaly distribution
        dept_anomalies = self.anomalies.groupby('DepartmentCode').size().reset_index(name='count')
        
        fig_dept = px.bar(
            dept_anomalies,
            x='DepartmentCode',
            y='count',
            title='Anomalies by Department',
            color='count',
            color_continuous_scale='Reds'
        )
        
        visualizations['department'] = fig_dept
        
        # 3. Anomaly score distribution
        fig_scores = go.Figure()
        
        fig_scores.add_trace(go.Histogram(
            x=self.transaction_data[self.transaction_data['is_anomaly']]['anomaly_score'],
            name='Anomalies',
            marker_color='red',
            opacity=0.7
        ))
        
        fig_scores.add_trace(go.Histogram(
            x=self.transaction_data[~self.transaction_data['is_anomaly']]['anomaly_score'],
            name='Normal',
            marker_color='blue',
            opacity=0.7
        ))
        
        fig_scores.update_layout(
            title='Anomaly Score Distribution',
            xaxis_title='Anomaly Score',
            yaxis_title='Count',
            barmode='overlay'
        )
        
        visualizations['scores'] = fig_scores
        
        # 4. Feature importance (using PCA)
        if self.feature_data is not None:
            pca = PCA(n_components=2)
            pca_features = pca.fit_transform(self.detector.scaler.transform(self.feature_data))
            
            fig_pca = go.Figure()
            
            # Normal points
            normal_mask = ~self.transaction_data['is_anomaly']
            fig_pca.add_trace(go.Scatter(
                x=pca_features[normal_mask, 0],
                y=pca_features[normal_mask, 1],
                mode='markers',
                name='Normal',
                marker=dict(color='blue', size=5, opacity=0.3)
            ))
            
            # Anomaly points
            anomaly_mask = self.transaction_data['is_anomaly']
            fig_pca.add_trace(go.Scatter(
                x=pca_features[anomaly_mask, 0],
                y=pca_features[anomaly_mask, 1],
                mode='markers',
                name='Anomaly',
                marker=dict(color='red', size=10),
                text=self.transaction_data[anomaly_mask]['anomaly_reason'],
                hovertemplate='<b>Anomaly</b><br>%{text}<extra></extra>'
            ))
            
            fig_pca.update_layout(
                title='Anomaly Detection - PCA Visualization',
                xaxis_title='First Principal Component',
                yaxis_title='Second Principal Component'
            )
            
            visualizations['pca'] = fig_pca
        
        return visualizations
    
    def get_department_report(self, department: str) -> Dict[str, Any]:
        """Generate anomaly report for specific department"""
        if self.anomalies is None:
            self.detect_anomalies()
        
        dept_anomalies = self.anomalies[self.anomalies['DepartmentCode'] == department]
        
        report = {
            'department': department,
            'total_transactions': len(self.transaction_data[self.transaction_data['DepartmentCode'] == department]),
            'anomaly_count': len(dept_anomalies),
            'anomaly_rate': len(dept_anomalies) / len(self.transaction_data[self.transaction_data['DepartmentCode'] == department]),
            'total_anomaly_amount': dept_anomalies['Amount'].sum(),
            'average_anomaly_amount': dept_anomalies['Amount'].mean() if len(dept_anomalies) > 0 else 0,
            'top_anomalies': dept_anomalies.nlargest(5, 'Amount')[['Date', 'Amount', 'Description', 'anomaly_reason']].to_dict('records'),
            'monthly_distribution': dept_anomalies.groupby('Month').size().to_dict()
        }
        
        return report
    
    def export_results(self, filepath: str = None) -> str:
        """Export anomaly detection results to file"""
        if self.anomalies is None:
            self.detect_anomalies()
        
        if filepath is None:
            filepath = f"anomaly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Prepare export data
        export_data = self.anomalies[[
            'TransactionID', 'Date', 'Amount', 'Description',
            'DepartmentCode', 'VendorID', 'anomaly_score',
            'confidence', 'anomaly_reason'
        ]]
        
        export_data.to_csv(filepath, index=False)
        
        return filepath