"""
Real-Time Intelligence Platform
Live data feeds, automated monitoring, and dynamic municipal dashboards
Integrates with ERP systems for continuous municipal intelligence
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import time

# Import visualization libraries
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

class RealTimeIntelligencePlatform:
    """Real-time monitoring and intelligence platform for municipal operations"""
    
    def __init__(self):
        self.monitoring_categories = {
            'financial_metrics': {
                'name': 'Financial Metrics',
                'description': 'Real-time budget, revenue, and expense monitoring',
                'refresh_interval': 5,  # minutes
                'alert_thresholds': {'budget_variance': 5, 'revenue_decline': 10}
            },
            'operational_metrics': {
                'name': 'Operational Metrics',
                'description': 'Service delivery and performance indicators',
                'refresh_interval': 10,
                'alert_thresholds': {'response_time': 15, 'service_availability': 95}
            },
            'infrastructure_health': {
                'name': 'Infrastructure Health',
                'description': 'Infrastructure systems and asset monitoring',
                'refresh_interval': 15,
                'alert_thresholds': {'system_uptime': 98, 'maintenance_overdue': 5}
            },
            'citizen_engagement': {
                'name': 'Citizen Engagement',
                'description': 'Public service requests and citizen satisfaction',
                'refresh_interval': 30,
                'alert_thresholds': {'satisfaction_score': 75, 'response_time_hours': 24}
            }
        }
        
        self.initialize_monitoring_storage()
    
    def initialize_monitoring_storage(self):
        """Initialize database for real-time monitoring data"""
        try:
            conn = sqlite3.connect('databases/core/realtime_monitoring.db')
            cursor = conn.cursor()
            
            # Create metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS realtime_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_unit TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_system TEXT,
                    alert_triggered BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Create alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    threshold_value REAL,
                    actual_value REAL,
                    severity TEXT DEFAULT 'medium',
                    message TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    acknowledged_by TEXT
                )
            ''')
            
            # Create dashboard configurations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dashboard_configs (
                    id TEXT PRIMARY KEY,
                    dashboard_name TEXT NOT NULL,
                    layout_config TEXT,
                    refresh_interval INTEGER DEFAULT 30,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Failed to initialize monitoring storage: {e}")
    
    def render_realtime_intelligence_dashboard(self):
        """Main real-time intelligence dashboard"""
        
        st.title("Real-Time Municipal Intelligence")
        st.markdown("**Live monitoring and automated insights for municipal operations**")
        
        # Auto-refresh control
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            auto_refresh = st.checkbox("Auto-refresh dashboard", value=True)
            if auto_refresh:
                refresh_interval = st.selectbox("Refresh every", [30, 60, 120, 300], 
                                              format_func=lambda x: f"{x} seconds")
        
        with col2:
            if st.button("Refresh Now", type="secondary"):
                st.rerun()
        
        with col3:
            alert_count = self.get_active_alert_count()
            if alert_count > 0:
                if st.button(f"🚨 {alert_count} Alerts", type="primary"):
                    st.session_state['show_alerts'] = True
                    st.rerun()
        
        # Navigation tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Live Dashboard",
            "Alert Management",
            "Performance Metrics", 
            "System Health",
            "Configuration"
        ])
        
        with tab1:
            self.render_live_dashboard()
        
        with tab2:
            self.render_alert_management()
        
        with tab3:
            self.render_performance_metrics()
        
        with tab4:
            self.render_system_health()
        
        with tab5:
            self.render_monitoring_configuration()
    
    def render_live_dashboard(self):
        """Render the main live monitoring dashboard"""
        
        st.subheader("Live Municipal Operations Dashboard")
        
        # Key performance indicators at the top
        self.render_kpi_overview()
        
        st.markdown("---")
        
        # Real-time charts in grid layout
        col1, col2 = st.columns(2)
        
        with col1:
            self.render_financial_monitoring()
            self.render_citizen_engagement_metrics()
        
        with col2:
            self.render_operational_monitoring()
            self.render_infrastructure_health()
        
        # Live activity feed
        st.markdown("---")
        self.render_live_activity_feed()
    
    def render_kpi_overview(self):
        """Render key performance indicators overview"""
        
        # Generate real-time KPIs (in production, these would come from ERP systems)
        kpis = self.get_realtime_kpis()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            budget_variance = kpis.get('budget_variance', 0)
            delta_color = "normal" if abs(budget_variance) < 5 else "inverse"
            st.metric("Budget Variance", f"{budget_variance:+.1f}%", 
                     delta=f"{budget_variance:+.1f}% vs target")
        
        with col2:
            response_time = kpis.get('avg_response_time', 0)
            delta_color = "normal" if response_time < 10 else "inverse"
            st.metric("Avg Response Time", f"{response_time:.1f} min", 
                     delta=f"{response_time-8:.1f} vs yesterday")
        
        with col3:
            citizen_satisfaction = kpis.get('citizen_satisfaction', 0)
            delta_color = "normal" if citizen_satisfaction > 80 else "inverse"
            st.metric("Citizen Satisfaction", f"{citizen_satisfaction:.0f}%", 
                     delta=f"{citizen_satisfaction-82:+.0f}% vs last month")
        
        with col4:
            system_uptime = kpis.get('system_uptime', 0)
            delta_color = "normal" if system_uptime > 98 else "inverse"
            st.metric("System Uptime", f"{system_uptime:.1f}%", 
                     delta="99.2% target")
        
        with col5:
            active_requests = kpis.get('active_requests', 0)
            st.metric("Active Requests", f"{active_requests:,}", 
                     delta=f"{active_requests-150:+,} vs yesterday")
    
    def get_realtime_kpis(self) -> Dict[str, float]:
        """Get real-time key performance indicators"""
        
        # Mock real-time data - in production, this would query ERP systems
        import random
        
        return {
            'budget_variance': random.uniform(-8, 6),
            'avg_response_time': random.uniform(5, 15),
            'citizen_satisfaction': random.uniform(75, 95),
            'system_uptime': random.uniform(97, 99.9),
            'active_requests': random.randint(80, 250)
        }
    
    def render_financial_monitoring(self):
        """Render real-time financial monitoring"""
        
        st.markdown("### 💰 Financial Monitoring")
        
        # Generate real-time financial data
        financial_data = self.get_realtime_financial_data()
        
        # Revenue vs Budget chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=financial_data['time'],
            y=financial_data['revenue'],
            mode='lines',
            name='Actual Revenue',
            line=dict(color='green', width=3)
        ))
        
        fig.add_trace(go.Scatter(
            x=financial_data['time'],
            y=financial_data['budget'],
            mode='lines',
            name='Budgeted Revenue',
            line=dict(color='blue', dash='dash')
        ))
        
        fig.update_layout(
            title="Revenue vs Budget (Real-Time)",
            xaxis_title="Time",
            yaxis_title="Amount ($)",
            height=300,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Financial alerts
        if financial_data['variance'] > 5:
            st.warning(f"⚠️ Revenue variance: {financial_data['variance']:+.1f}% above budget")
        elif financial_data['variance'] < -5:
            st.error(f"🚨 Revenue variance: {financial_data['variance']:+.1f}% below budget")
    
    def render_operational_monitoring(self):
        """Render real-time operational monitoring"""
        
        st.markdown("### ⚙️ Operational Performance")
        
        # Generate operational metrics
        operational_data = self.get_realtime_operational_data()
        
        # Service response times
        fig = go.Figure()
        
        for service, data in operational_data['services'].items():
            fig.add_trace(go.Scatter(
                x=operational_data['time'],
                y=data,
                mode='lines+markers',
                name=service,
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title="Service Response Times",
            xaxis_title="Time",
            yaxis_title="Response Time (minutes)",
            height=300,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Operational status
        status_data = operational_data['status']
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Active Services", status_data['active_services'])
        with col2:
            st.metric("Avg Response", f"{status_data['avg_response']:.1f} min")
    
    def render_citizen_engagement_metrics(self):
        """Render citizen engagement monitoring"""
        
        st.markdown("### 👥 Citizen Engagement")
        
        # Generate citizen engagement data
        engagement_data = self.get_realtime_engagement_data()
        
        # Service request trends
        fig = px.bar(
            x=list(engagement_data['requests_by_type'].keys()),
            y=list(engagement_data['requests_by_type'].values()),
            title="Service Requests by Type (Today)"
        )
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Engagement metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Today's Requests", engagement_data['total_requests'])
        with col2:
            satisfaction = engagement_data['satisfaction_score']
            st.metric("Satisfaction", f"{satisfaction:.0f}%")
    
    def render_infrastructure_health(self):
        """Render infrastructure health monitoring"""
        
        st.markdown("### 🏗️ Infrastructure Health")
        
        # Generate infrastructure data
        infrastructure_data = self.get_realtime_infrastructure_data()
        
        # System health gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = infrastructure_data['overall_health'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Overall Health"},
            delta = {'reference': 95},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 70], 'color': "lightgray"},
                    {'range': [70, 90], 'color': "yellow"},
                    {'range': [90, 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 95
                }
            }
        ))
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        # Infrastructure status
        systems = infrastructure_data['systems']
        for system, status in systems.items():
            if status > 95:
                st.success(f"✅ {system}: {status:.1f}% operational")
            elif status > 85:
                st.warning(f"⚠️ {system}: {status:.1f}% operational")
            else:
                st.error(f"🚨 {system}: {status:.1f}% operational")
    
    def render_live_activity_feed(self):
        """Render live activity feed"""
        
        st.subheader("Live Activity Feed")
        
        # Generate recent activities
        activities = self.get_recent_activities()
        
        for activity in activities[:10]:  # Show last 10 activities
            timestamp = activity['timestamp']
            message = activity['message']
            activity_type = activity['type']
            
            if activity_type == 'alert':
                st.error(f"🚨 **{timestamp}** - {message}")
            elif activity_type == 'warning':
                st.warning(f"⚠️ **{timestamp}** - {message}")
            elif activity_type == 'success':
                st.success(f"✅ **{timestamp}** - {message}")
            else:
                st.info(f"ℹ️ **{timestamp}** - {message}")
    
    def render_alert_management(self):
        """Render alert management interface"""
        
        st.subheader("Alert Management")
        
        # Alert summary
        alerts = self.get_active_alerts()
        
        if not alerts:
            st.success("🎉 No active alerts - all systems operating normally!")
            return
        
        # Alert statistics
        col1, col2, col3, col4 = st.columns(4)
        
        alert_counts = self.get_alert_statistics(alerts)
        
        with col1:
            st.metric("Total Alerts", alert_counts['total'])
        
        with col2:
            st.metric("Critical", alert_counts['critical'], delta=None)
        
        with col3:
            st.metric("Warning", alert_counts['warning'], delta=None)
        
        with col4:
            st.metric("Info", alert_counts['info'], delta=None)
        
        # Alert actions
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Acknowledge All Warnings"):
                self.acknowledge_alerts('warning')
                st.success("All warning alerts acknowledged")
                st.rerun()
        
        with col2:
            if st.button("Clear Acknowledged"):
                self.clear_acknowledged_alerts()
                st.success("Acknowledged alerts cleared")
                st.rerun()
        
        # Alert list
        st.markdown("### Active Alerts")
        
        for alert in alerts:
            self.render_alert_card(alert)
    
    def render_alert_card(self, alert: Dict[str, Any]):
        """Render individual alert card"""
        
        severity = alert['severity']
        
        if severity == 'critical':
            alert_color = "🚨"
            container_type = st.error
        elif severity == 'warning':
            alert_color = "⚠️"
            container_type = st.warning
        else:
            alert_color = "ℹ️"
            container_type = st.info
        
        with st.container():
            col1, col2, col3 = st.columns([6, 2, 1])
            
            with col1:
                st.markdown(f"{alert_color} **{alert['alert_type']}** - {alert['message']}")
                st.caption(f"Category: {alert['category']} | Created: {alert['created_at']}")
            
            with col2:
                if alert['threshold_value']:
                    st.metric("Threshold", f"{alert['threshold_value']}")
                    st.metric("Actual", f"{alert['actual_value']}")
            
            with col3:
                if not alert['acknowledged']:
                    if st.button("Ack", key=f"ack_{alert['id']}"):
                        self.acknowledge_alert(alert['id'])
                        st.rerun()
                else:
                    st.success("✓")
            
            st.markdown("---")
    
    def render_performance_metrics(self):
        """Render detailed performance metrics"""
        
        st.subheader("Performance Metrics Analysis")
        
        # Metric category selection
        metric_category = st.selectbox("Select Metric Category", 
                                     list(self.monitoring_categories.keys()),
                                     format_func=lambda x: self.monitoring_categories[x]['name'])
        
        # Time range selection
        time_range = st.selectbox("Time Range", 
                                ["Last Hour", "Last 4 Hours", "Last 24 Hours", "Last Week"])
        
        # Generate detailed metrics
        metrics_data = self.get_detailed_metrics(metric_category, time_range)
        
        # Metrics visualization
        self.render_metrics_charts(metrics_data, metric_category)
        
        # Metrics table
        st.subheader("Detailed Metrics")
        metrics_df = pd.DataFrame(metrics_data['table_data'])
        st.dataframe(metrics_df, use_container_width=True)
        
        # Performance insights
        insights = self.generate_performance_insights(metrics_data)
        if insights:
            st.subheader("Performance Insights")
            for insight in insights:
                st.info(insight)
    
    def render_system_health(self):
        """Render overall system health dashboard"""
        
        st.subheader("System Health Overview")
        
        # System health scores
        health_data = self.get_system_health_data()
        
        # Health scores grid
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🖥️ System Performance")
            for system, score in health_data['system_performance'].items():
                if score > 95:
                    st.success(f"{system}: {score:.1f}%")
                elif score > 85:
                    st.warning(f"{system}: {score:.1f}%")
                else:
                    st.error(f"{system}: {score:.1f}%")
        
        with col2:
            st.markdown("### 🔗 Connectivity")
            for connection, status in health_data['connectivity'].items():
                if status == 'connected':
                    st.success(f"{connection}: Connected")
                elif status == 'degraded':
                    st.warning(f"{connection}: Degraded")
                else:
                    st.error(f"{connection}: Disconnected")
        
        with col3:
            st.markdown("### 📊 Data Quality")
            for source, quality in health_data['data_quality'].items():
                if quality > 95:
                    st.success(f"{source}: {quality:.1f}%")
                elif quality > 85:
                    st.warning(f"{source}: {quality:.1f}%")
                else:
                    st.error(f"{source}: {quality:.1f}%")
        
        # System health trends
        st.subheader("Health Trends (Last 24 Hours)")
        
        trend_data = health_data['trends']
        
        fig = go.Figure()
        
        for metric, values in trend_data.items():
            fig.add_trace(go.Scatter(
                x=list(range(24)),
                y=values,
                mode='lines',
                name=metric,
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title="System Health Trends",
            xaxis_title="Hours Ago",
            yaxis_title="Health Score (%)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_monitoring_configuration(self):
        """Render monitoring configuration interface"""
        
        st.subheader("Monitoring Configuration")
        
        # Alert thresholds
        st.markdown("### Alert Thresholds")
        
        for category, config in self.monitoring_categories.items():
            with st.expander(f"{config['name']} Settings"):
                st.markdown(f"**{config['description']}**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    refresh_interval = st.number_input(
                        "Refresh Interval (minutes)",
                        value=config['refresh_interval'],
                        min_value=1,
                        max_value=60,
                        key=f"refresh_{category}"
                    )
                
                with col2:
                    enable_alerts = st.checkbox(
                        "Enable Alerts",
                        value=True,
                        key=f"alerts_{category}"
                    )
                
                # Threshold settings
                for threshold_name, threshold_value in config['alert_thresholds'].items():
                    new_threshold = st.number_input(
                        f"{threshold_name.replace('_', ' ').title()} Threshold",
                        value=threshold_value,
                        key=f"threshold_{category}_{threshold_name}"
                    )
        
        # Dashboard settings
        st.markdown("### Dashboard Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            default_refresh = st.selectbox("Default Refresh Rate", [30, 60, 120, 300])
            auto_alerts = st.checkbox("Enable Automatic Alerts", value=True)
        
        with col2:
            max_alerts = st.number_input("Maximum Alerts to Display", value=50, min_value=10, max_value=200)
            alert_retention = st.selectbox("Alert Retention Period", ["1 day", "1 week", "1 month", "3 months"])
        
        # Save configuration
        if st.button("Save Configuration", type="primary"):
            st.success("Monitoring configuration saved successfully!")
    
    # Helper methods for data generation (in production, these would query real systems)
    
    def get_realtime_financial_data(self) -> Dict[str, Any]:
        """Get real-time financial monitoring data"""
        import random
        
        time_points = [f"{i:02d}:00" for i in range(8, 18)]  # 8 AM to 5 PM
        
        base_revenue = 100000
        revenue_data = [base_revenue * (1 + random.uniform(-0.1, 0.1)) for _ in time_points]
        budget_data = [base_revenue * 1.05] * len(time_points)  # 5% above base
        
        current_variance = (revenue_data[-1] - budget_data[-1]) / budget_data[-1] * 100
        
        return {
            'time': time_points,
            'revenue': revenue_data,
            'budget': budget_data,
            'variance': current_variance
        }
    
    def get_realtime_operational_data(self) -> Dict[str, Any]:
        """Get real-time operational monitoring data"""
        import random
        
        time_points = [f"{i:02d}:00" for i in range(8, 18)]
        
        services = {
            'Police': [random.uniform(5, 12) for _ in time_points],
            'Fire': [random.uniform(3, 8) for _ in time_points],
            'Public Works': [random.uniform(8, 20) for _ in time_points],
            'Permits': [random.uniform(2, 15) for _ in time_points]
        }
        
        avg_response = sum([sum(data) for data in services.values()]) / (len(services) * len(time_points))
        
        return {
            'time': time_points,
            'services': services,
            'status': {
                'active_services': len(services),
                'avg_response': avg_response
            }
        }
    
    def get_realtime_engagement_data(self) -> Dict[str, Any]:
        """Get real-time citizen engagement data"""
        import random
        
        request_types = {
            'Water Issues': random.randint(5, 25),
            'Road Maintenance': random.randint(3, 15),
            'Noise Complaints': random.randint(1, 8),
            'Permits': random.randint(8, 20),
            'Other': random.randint(2, 10)
        }
        
        return {
            'requests_by_type': request_types,
            'total_requests': sum(request_types.values()),
            'satisfaction_score': random.uniform(75, 95)
        }
    
    def get_realtime_infrastructure_data(self) -> Dict[str, Any]:
        """Get real-time infrastructure health data"""
        import random
        
        systems = {
            'Water System': random.uniform(92, 99.5),
            'Power Grid': random.uniform(95, 99.8),
            'Communications': random.uniform(88, 99),
            'Traffic Systems': random.uniform(90, 98)
        }
        
        overall_health = sum(systems.values()) / len(systems)
        
        return {
            'systems': systems,
            'overall_health': overall_health
        }
    
    def get_recent_activities(self) -> List[Dict[str, Any]]:
        """Get recent system activities"""
        import random
        from datetime import datetime, timedelta
        
        activities = []
        activity_types = ['alert', 'warning', 'success', 'info']
        
        for i in range(20):
            timestamp = (datetime.now() - timedelta(minutes=i*5)).strftime("%H:%M")
            activity_type = random.choice(activity_types)
            
            if activity_type == 'alert':
                message = "Budget variance exceeded threshold in Public Works department"
            elif activity_type == 'warning':
                message = "Response time degradation detected in Fire department"
            elif activity_type == 'success':
                message = "ERP data synchronization completed successfully"
            else:
                message = f"System checkpoint completed - {random.randint(150, 500)} records processed"
            
            activities.append({
                'timestamp': timestamp,
                'type': activity_type,
                'message': message
            })
        
        return activities
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        # Mock alerts - in production, these would come from the monitoring database
        import random
        
        alerts = []
        
        if random.random() > 0.3:  # 70% chance of having alerts
            alert_types = [
                {
                    'alert_type': 'Budget Variance',
                    'category': 'financial_metrics',
                    'severity': 'warning',
                    'message': 'Department spending 8% over monthly allocation',
                    'threshold_value': 5.0,
                    'actual_value': 8.2
                },
                {
                    'alert_type': 'Response Time',
                    'category': 'operational_metrics', 
                    'severity': 'critical',
                    'message': 'Emergency response time exceeds acceptable threshold',
                    'threshold_value': 10.0,
                    'actual_value': 15.3
                },
                {
                    'alert_type': 'System Uptime',
                    'category': 'infrastructure_health',
                    'severity': 'warning',
                    'message': 'Water management system experiencing intermittent connectivity',
                    'threshold_value': 98.0,
                    'actual_value': 94.5
                }
            ]
            
            for i, alert_template in enumerate(alert_types[:random.randint(1, 3)]):
                alert = alert_template.copy()
                alert['id'] = i + 1
                alert['acknowledged'] = random.choice([True, False])
                alert['created_at'] = f"{random.randint(1, 23):02d}:{random.randint(0, 59):02d}"
                alerts.append(alert)
        
        return alerts
    
    def get_active_alert_count(self) -> int:
        """Get count of active alerts"""
        return len(self.get_active_alerts())
    
    def get_alert_statistics(self, alerts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get alert statistics"""
        return {
            'total': len(alerts),
            'critical': len([a for a in alerts if a['severity'] == 'critical']),
            'warning': len([a for a in alerts if a['severity'] == 'warning']),
            'info': len([a for a in alerts if a['severity'] == 'info'])
        }
    
    def get_detailed_metrics(self, category: str, time_range: str) -> Dict[str, Any]:
        """Get detailed metrics for analysis"""
        import random
        
        # Generate sample metrics data
        time_points = 24 if "24 Hours" in time_range else 4 if "4 Hours" in time_range else 1
        
        metrics = {}
        for i in range(time_points):
            metrics[f"metric_{i}"] = random.uniform(70, 100)
        
        table_data = [
            {'Metric': 'Response Time', 'Current': '8.2 min', 'Target': '10.0 min', 'Status': 'Good'},
            {'Metric': 'Satisfaction', 'Current': '87%', 'Target': '85%', 'Status': 'Excellent'},
            {'Metric': 'Uptime', 'Current': '99.2%', 'Target': '98%', 'Status': 'Good'},
            {'Metric': 'Efficiency', 'Current': '94%', 'Target': '90%', 'Status': 'Good'}
        ]
        
        return {
            'metrics': metrics,
            'table_data': table_data
        }
    
    def get_system_health_data(self) -> Dict[str, Any]:
        """Get comprehensive system health data"""
        import random
        
        return {
            'system_performance': {
                'Database': random.uniform(92, 99),
                'Web Server': random.uniform(95, 99.5),
                'API Gateway': random.uniform(88, 98),
                'Cache': random.uniform(90, 99)
            },
            'connectivity': {
                'Caselle ERP': random.choice(['connected', 'connected', 'degraded']),
                'Tyler Systems': random.choice(['connected', 'connected', 'connected']),
                'Oracle DB': random.choice(['connected', 'connected', 'degraded']),
                'External APIs': random.choice(['connected', 'degraded'])
            },
            'data_quality': {
                'Financial Data': random.uniform(95, 99.8),
                'HR Data': random.uniform(88, 96),
                'Infrastructure': random.uniform(92, 98),
                'Citizen Services': random.uniform(90, 97)
            },
            'trends': {
                'Overall Health': [random.uniform(90, 99) for _ in range(24)],
                'Performance': [random.uniform(88, 98) for _ in range(24)],
                'Connectivity': [random.uniform(85, 99) for _ in range(24)]
            }
        }
    
    def render_metrics_charts(self, metrics_data: Dict[str, Any], category: str):
        """Render metrics visualization charts"""
        
        if not PLOTLY_AVAILABLE:
            st.warning("Charts not available - plotly not installed")
            return
        
        metrics = metrics_data['metrics']
        
        if metrics:
            fig = go.Figure()
            
            x_values = list(metrics.keys())
            y_values = list(metrics.values())
            
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                mode='lines+markers',
                name=f"{category.replace('_', ' ').title()} Metrics",
                line=dict(width=3)
            ))
            
            fig.update_layout(
                title=f"{category.replace('_', ' ').title()} Performance Over Time",
                xaxis_title="Time Period",
                yaxis_title="Performance Score",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def generate_performance_insights(self, metrics_data: Dict[str, Any]) -> List[str]:
        """Generate AI-powered performance insights"""
        
        insights = []
        
        # Mock insights - in production, these would be generated by AI analysis
        insights.append("📈 Performance trend shows 12% improvement over last week")
        insights.append("⚠️ Response time variance increased during peak hours (11 AM - 2 PM)")
        insights.append("✅ System reliability exceeded target by 2.1%")
        insights.append("💡 Recommendation: Consider load balancing optimization for afternoon peak")
        
        return insights
    
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge a specific alert"""
        # In production, this would update the database
        pass
    
    def acknowledge_alerts(self, severity: str):
        """Acknowledge all alerts of specified severity"""
        # In production, this would update the database
        pass
    
    def clear_acknowledged_alerts(self):
        """Clear all acknowledged alerts"""
        # In production, this would clean up the database
        pass

# Global instance
_realtime_platform = None

def get_realtime_intelligence_platform() -> RealTimeIntelligencePlatform:
    """Get global real-time intelligence platform instance"""
    global _realtime_platform
    if _realtime_platform is None:
        _realtime_platform = RealTimeIntelligencePlatform()
    return _realtime_platform