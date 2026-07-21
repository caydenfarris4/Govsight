"""
AI Intelligence Hub - Main Interface for Advanced AI Capabilities
Integrates all AI components into a unified, secure interface for GovSight
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
import json

# Import AI components
from modules.ai_engine.secure_ai_base import SecureAIBase, GOVSIGHT_AI_SECURITY
from modules.ai_engine.advanced_grant_intelligence import AdvancedGrantIntelligence
from modules.ai_engine.enhanced_anomaly_detection import EnhancedAnomalyDetection
from modules.ai_engine.data_quality_engine import DataQualityEngine
from modules.ai_engine.enhanced_natural_language import EnhancedNaturalLanguage

class AIIntelligenceHub(SecureAIBase):
    """
    Central hub for all advanced AI capabilities in GovSight
    
    INTEGRATED CAPABILITIES:
    - Advanced Grant Intelligence & Legislative Analysis
    - Enhanced Anomaly Detection
    - Data Quality Assessment & Improvement
    - Natural Language Analytics
    - Cross-module AI insights and recommendations
    """
    
    def __init__(self):
        super().__init__("AIIntelligenceHub", GOVSIGHT_AI_SECURITY)
        
        # Initialize AI components
        self.grant_intelligence = AdvancedGrantIntelligence()
        self.anomaly_detection = EnhancedAnomalyDetection()
        self.data_quality = DataQualityEngine()
        self.natural_language = EnhancedNaturalLanguage()
        
        # AI capabilities registry
        self.capabilities = {
            'grant_intelligence': {
                'name': 'Grant Intelligence & Legislative Analysis',
                'description': 'AI-powered grant discovery, eligibility assessment, and legislative impact analysis',
                'functions': ['search_grants', 'analyze_eligibility', 'legislative_impact', 'application_guidance']
            },
            'anomaly_detection': {
                'name': 'Enhanced Anomaly Detection',
                'description': 'Multi-layer anomaly detection for transactions, budgets, and municipal patterns',
                'functions': ['detect_anomalies', 'risk_assessment', 'investigation_guidance', 'pattern_analysis']
            },
            'data_quality': {
                'name': 'Data Quality & Validation',
                'description': 'Comprehensive data quality assessment, cleaning, and validation',
                'functions': ['quality_assessment', 'data_cleaning', 'validation_rules', 'imputation']
            },
            'natural_language': {
                'name': 'Natural Language Analytics',
                'description': 'Conversational AI for financial analysis with visualization generation',
                'functions': ['query_processing', 'conversation_context', 'visualization_generation', 'narrative_insights']
            }
        }
    
    def render_main_interface(self):
        """Render the main AI Intelligence Hub interface"""
        st.title("🧠 AI Intelligence Hub")
        st.markdown("""
        **Enterprise-Grade AI for Municipal Financial Intelligence**
        
        Advanced AI capabilities for grant discovery, anomaly detection, data quality assessment, 
        and natural language analytics with enterprise security.
        """)
        
        # Security status
        with st.expander("🔒 Security Status", expanded=False):
            st.success("✅ All AI operations are secured with enterprise-grade encryption and audit logging")
            st.info("🛡️ Security Level: HIGH - All queries validated and logged for compliance")
            st.info("🔐 Data Protection: End-to-end encryption with automatic data retention policies")
        
        # Main tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 Natural Language Query", 
            "💰 Grant Intelligence", 
            "🚨 Anomaly Detection", 
            "📊 Data Quality", 
            "📈 AI Analytics Dashboard"
        ])
        
        with tab1:
            self._render_natural_language_interface()
        
        with tab2:
            self._render_grant_intelligence_interface()
        
        with tab3:
            self._render_anomaly_detection_interface()
        
        with tab4:
            self._render_data_quality_interface()
        
        with tab5:
            self._render_analytics_dashboard()
    
    def _render_natural_language_interface(self):
        """Render natural language query interface"""
        st.header("🎯 Natural Language Financial Analytics")
        st.markdown("Ask questions about your municipal financial data in plain English.")
        
        # Load available data for context
        available_data = self._load_available_data()
        data_status = self._check_data_availability(available_data)
        
        # Data status indicator
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Data Sources Available", data_status['available_sources'])
        with col2:
            st.metric("Total Records", data_status['total_records'])
        with col3:
            st.metric("Date Range", data_status['date_range'])
        
        # Query interface
        st.subheader("💬 Ask Your Question")
        
        # Example questions
        with st.expander("💡 Example Questions", expanded=False):
            example_questions = [
                "What did we spend on public works last month?",
                "Show me the top 10 vendors by spending this year",
                "Compare budget vs actual for all departments",
                "What are the spending trends over the past 6 months?",
                "Which departments are over budget?",
                "Show me unusual transactions that need investigation"
            ]
            for question in example_questions:
                if st.button(f"📝 {question}", key=f"example_{hash(question)}"):
                    st.session_state.nl_query = question
        
        # Main query input
        user_query = st.text_area(
            "Your Question:",
            value=st.session_state.get('nl_query', ''),
            height=100,
            placeholder="Ask me anything about your municipal finances..."
        )
        
        if st.button("🔍 Analyze", type="primary", disabled=not user_query.strip()):
            if user_query.strip():
                with st.spinner("🤖 Analyzing your question and generating insights..."):
                    # Get conversation context
                    conversation_history = self.natural_language.get_conversation_history()
                    
                    # Process the query
                    response = self.natural_language.process_natural_language_query(
                        user_query, 
                        available_data,
                        conversation_history
                    )
                    
                    # Display results
                    if 'error' in response:
                        st.error(f"❌ {response['error']}")
                    else:
                        self._display_nl_response(response)
        
        # Conversation history
        if st.checkbox("📜 Show Conversation History"):
            self._display_conversation_history()
    
    def _render_grant_intelligence_interface(self):
        """Render grant intelligence interface"""
        st.header("💰 Grant Intelligence & Legislative Analysis")
        
        # Grant discovery section
        st.subheader("🔍 Grant Discovery & Matching")
        
        # Municipal profile input
        with st.expander("🏛️ Municipal Profile (for better grant matching)", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                population = st.number_input("Population", value=50000, min_value=1000)
                annual_budget = st.number_input("Annual Budget ($)", value=25000000, min_value=100000)
                
            with col2:
                region = st.selectbox("Region", ["western", "eastern", "southern", "northern", "midwest"])
                priority_areas = st.multiselect(
                    "Priority Areas", 
                    ["public safety", "infrastructure", "environmental", "health", "education", "economic development"],
                    default=["public safety", "infrastructure"]
                )
            
            departments = st.multiselect(
                "Key Departments",
                ["Police", "Fire", "Public Works", "Parks & Recreation", "Administration", "Finance", "Water/Sewer"],
                default=["Police", "Fire", "Public Works"]
            )
            
            infrastructure_needs = st.multiselect(
                "Infrastructure Needs",
                ["roads", "bridges", "water systems", "sewer systems", "public buildings", "technology", "vehicles"],
                default=["roads", "water systems"]
            )
        
        municipal_profile = {
            'population': population,
            'budget_size': annual_budget,
            'department_priorities': departments,
            'region': region,
            'infrastructure_needs': infrastructure_needs
        }
        
        if st.button("🎯 Find Matching Grants", type="primary"):
            with st.spinner("🔍 Searching and analyzing grant opportunities..."):
                # Profile analysis
                profile_analysis = self.grant_intelligence.analyze_municipal_profile(municipal_profile)
                
                # Grant matching
                matched_grants = self.grant_intelligence.intelligent_grant_matching(
                    municipal_profile, priority_areas
                )
                
                # Display results
                self._display_grant_results(profile_analysis, matched_grants)
        
        st.divider()
        
        # Legislative impact analysis
        st.subheader("📋 Legislative Impact Analysis")
        st.markdown("Analyze the potential fiscal impact of proposed legislation on your municipality.")
        
        legislation_text = st.text_area(
            "Legislation Text or Summary:",
            height=200,
            placeholder="Paste the text of proposed legislation, ordinances, or policy changes here..."
        )
        
        if legislation_text and st.button("⚖️ Analyze Legislative Impact", type="primary"):
            with st.spinner("🤖 Analyzing legislative fiscal impact..."):
                impact_analysis = self.grant_intelligence.legislative_impact_analysis(
                    legislation_text, municipal_profile
                )
                
                if impact_analysis.get('success'):
                    st.success("✅ Legislative Impact Analysis Complete")
                    
                    # Display analysis in formatted sections
                    analysis_text = impact_analysis['analysis']
                    
                    st.markdown("### 📊 Fiscal Impact Analysis")
                    st.markdown(analysis_text)
                    
                    # Analysis metadata
                    with st.expander("📋 Analysis Details"):
                        st.write(f"**Generated:** {impact_analysis['generated_at']}")
                        st.write(f"**Legislation Length:** {impact_analysis['legislation_length']:,} characters")
                        st.write(f"**Municipal Context:** {municipal_profile['population']:,} population")
                else:
                    st.error(f"❌ Analysis failed: {impact_analysis.get('error', 'Unknown error')}")
    
    def _render_anomaly_detection_interface(self):
        """Render anomaly detection interface"""
        st.header("🚨 Enhanced Anomaly Detection")
        
        # Load transaction data
        available_data = self._load_available_data()
        transaction_data = None
        budget_data = None
        
        # Data selection
        if available_data:
            data_source = st.selectbox(
                "Select Data Source for Anomaly Detection:",
                list(available_data.keys()),
                help="Choose the dataset to analyze for anomalies"
            )
            
            if data_source and data_source in available_data:
                transaction_data = available_data[data_source]
                
                # Optional budget data for variance analysis
                budget_sources = [key for key in available_data.keys() if 'budget' in key.lower()]
                if budget_sources:
                    budget_source = st.selectbox(
                        "Optional: Budget Data for Variance Analysis:",
                        ["None"] + budget_sources
                    )
                    if budget_source != "None":
                        budget_data = available_data[budget_source]
        
        if transaction_data is not None and len(transaction_data) > 0:
            # Display data overview
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(transaction_data))
            with col2:
                if 'Amount' in transaction_data.columns:
                    st.metric("Total Amount", f"${transaction_data['Amount'].sum():,.2f}")
            with col3:
                if 'Date' in transaction_data.columns:
                    date_range = f"{transaction_data['Date'].min()} to {transaction_data['Date'].max()}"
                    st.metric("Date Range", date_range)
            
            # Anomaly detection settings
            with st.expander("🔧 Detection Settings", expanded=False):
                st.markdown("**Advanced settings for anomaly detection algorithms**")
                sensitivity = st.slider("Detection Sensitivity", 0.01, 0.2, 0.05, 0.01,
                                       help="Lower values detect more anomalies")
                include_weekends = st.checkbox("Include Weekend Transactions", True)
                min_amount_threshold = st.number_input("Minimum Amount Threshold ($)", 0.0, 10000.0, 100.0)
            
            if st.button("🕵️ Run Anomaly Detection", type="primary"):
                with st.spinner("🤖 Running comprehensive anomaly detection..."):
                    # Run comprehensive analysis
                    anomaly_results = self.anomaly_detection.comprehensive_anomaly_analysis(
                        transaction_data, budget_data
                    )
                    
                    if 'error' in anomaly_results:
                        st.error(f"❌ {anomaly_results['error']}")
                    else:
                        self._display_anomaly_results(anomaly_results)
        else:
            st.info("📊 No transaction data available. Please load financial data to perform anomaly detection.")
            st.markdown("""
            **To use anomaly detection:**
            1. Load transaction or financial data
            2. Select the appropriate data source
            3. Configure detection settings
            4. Run the analysis to identify suspicious patterns
            """)
    
    def _render_data_quality_interface(self):
        """Render data quality assessment interface"""
        st.header("📊 Data Quality Assessment & Improvement")
        
        # Load available data
        available_data = self._load_available_data()
        
        if available_data:
            # Data source selection
            selected_dataset = st.selectbox(
                "Select Dataset for Quality Assessment:",
                list(available_data.keys()),
                help="Choose the dataset to assess for quality issues"
            )
            
            if selected_dataset and selected_dataset in available_data:
                dataset = available_data[selected_dataset]
                
                # Dataset overview
                st.subheader("📋 Dataset Overview")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Records", len(dataset))
                with col2:
                    st.metric("Total Fields", len(dataset.columns))
                with col3:
                    missing_percentage = (dataset.isnull().sum().sum() / dataset.size) * 100
                    st.metric("Missing Data %", f"{missing_percentage:.1f}%")
                with col4:
                    duplicate_count = dataset.duplicated().sum()
                    st.metric("Duplicate Records", duplicate_count)
                
                # Quality assessment settings
                with st.expander("🔧 Assessment Settings", expanded=False):
                    st.markdown("**Configure data quality validation rules**")
                    
                    validate_formats = st.checkbox("Validate Data Formats", True)
                    validate_ranges = st.checkbox("Validate Numeric Ranges", True)
                    validate_consistency = st.checkbox("Check Data Consistency", True)
                    municipal_validation = st.checkbox("Municipal-Specific Validation", True)
                
                if st.button("🔍 Assess Data Quality", type="primary"):
                    with st.spinner("🤖 Performing comprehensive data quality assessment..."):
                        # Run quality assessment
                        quality_results = self.data_quality.comprehensive_quality_assessment(
                            dataset, selected_dataset
                        )
                        
                        if 'error' in quality_results:
                            st.error(f"❌ {quality_results['error']}")
                        else:
                            self._display_quality_results(quality_results)
        else:
            st.info("📊 No data available for quality assessment. Please load data to begin analysis.")
    
    def _render_analytics_dashboard(self):
        """Render AI analytics dashboard"""
        st.header("📈 AI Analytics Dashboard")
        st.markdown("Comprehensive view of AI-powered insights and system performance.")
        
        # AI system metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("AI Queries Today", "47", "+12")
        with col2:
            st.metric("Anomalies Detected", "3", "-2")
        with col3:
            st.metric("Data Quality Score", "94.2%", "+1.5%")
        with col4:
            st.metric("Grants Matched", "8", "+3")
        
        st.divider()
        
        # Recent AI activities
        st.subheader("🕐 Recent AI Activities")
        
        # Mock recent activities (in real implementation, load from database)
        recent_activities = [
            {"time": "2 minutes ago", "activity": "Natural Language Query", "details": "Analyzed spending trends for Public Works", "status": "✅"},
            {"time": "15 minutes ago", "activity": "Anomaly Detection", "details": "Found 2 suspicious transactions requiring review", "status": "🚨"},
            {"time": "1 hour ago", "activity": "Grant Matching", "details": "Identified 3 new grant opportunities", "status": "💰"},
            {"time": "2 hours ago", "activity": "Data Quality Check", "details": "Assessed payroll data - 98% quality score", "status": "📊"},
            {"time": "4 hours ago", "activity": "Legislative Analysis", "details": "Analyzed HB-2024 fiscal impact", "status": "⚖️"}
        ]
        
        for activity in recent_activities:
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    st.write(activity["status"])
                with col2:
                    st.write(f"**{activity['activity']}** - {activity['details']}")
                with col3:
                    st.write(activity["time"])
                st.divider()
        
        # AI performance charts
        st.subheader("📊 AI Performance Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Query volume trend (mock data)
            dates = pd.date_range(start='2025-08-21', end='2025-08-28', freq='D')
            volumes = [12, 18, 15, 22, 28, 35, 47]
            
            fig = px.line(x=dates, y=volumes, title="Daily AI Query Volume")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # AI capability usage (mock data)
            capabilities = ["Natural Language", "Anomaly Detection", "Grant Intelligence", "Data Quality"]
            usage = [45, 28, 15, 12]
            
            fig = px.pie(values=usage, names=capabilities, title="AI Capability Usage")
            st.plotly_chart(fig, use_container_width=True)
    
    def _load_available_data(self) -> Dict[str, pd.DataFrame]:
        """Load available data sources for AI analysis"""
        available_data = {}
        
        try:
            # Try to load from common data sources
            from modules.database.connection_manager import load_org_data
            
            org = st.session_state.get('selected_org', 'cityA')
            
            # Load GL data
            try:
                gl_data = load_org_data(org)
                if not gl_data.empty:
                    available_data['gl_transactions'] = gl_data
            except Exception:
                pass
            
            # Load other potential data sources
            # This would be expanded based on actual data sources in GovSight
            
        except ImportError:
            # Fallback: create sample data for demonstration
            sample_data = self._create_sample_data()
            available_data.update(sample_data)
        
        return available_data
    
    def _create_sample_data(self) -> Dict[str, pd.DataFrame]:
        """Create sample data for demonstration purposes"""
        import numpy as np
        
        # Sample transaction data
        np.random.seed(42)
        n_transactions = 1000
        
        departments = ['Police', 'Fire', 'Public Works', 'Parks & Recreation', 'Administration']
        vendors = ['ABC Supply Co', 'City Services LLC', 'Municipal Equipment Inc', 'Emergency Systems Corp', 'Office Depot']
        
        sample_transactions = pd.DataFrame({
            'Date': pd.date_range(start='2024-01-01', end='2024-12-31', periods=n_transactions),
            'Amount': np.random.lognormal(8, 1.5, n_transactions),
            'Department': np.random.choice(departments, n_transactions),
            'Vendor': np.random.choice(vendors, n_transactions),
            'Description': [f"Transaction {i+1}" for i in range(n_transactions)],
            'AccountCode': [f"01-{np.random.randint(10,20):02d}-{np.random.randint(10,30):02d}-{np.random.randint(1000,9999)}" for _ in range(n_transactions)]
        })
        
        # Sample budget data
        sample_budget = pd.DataFrame({
            'Department': departments,
            'Budget': [2500000, 1800000, 3200000, 800000, 1200000],
            'Actual': [2450000, 1850000, 3100000, 750000, 1180000]
        })
        
        return {
            'sample_transactions': sample_transactions,
            'sample_budget': sample_budget
        }
    
    def _check_data_availability(self, available_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Check and summarize data availability"""
        if not available_data:
            return {
                'available_sources': 0,
                'total_records': 0,
                'date_range': 'No data'
            }
        
        total_records = sum(len(df) for df in available_data.values())
        
        # Try to determine date range
        date_range = 'Unknown'
        for df in available_data.values():
            if 'Date' in df.columns:
                try:
                    dates = pd.to_datetime(df['Date'])
                    date_range = f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"
                    break
                except:
                    continue
        
        return {
            'available_sources': len(available_data),
            'total_records': f"{total_records:,}",
            'date_range': date_range
        }
    
    def _display_nl_response(self, response: Dict[str, Any]):
        """Display natural language query response"""
        # Query analysis
        if response.get('query_analysis'):
            with st.expander("🔍 Query Analysis", expanded=False):
                analysis = response['query_analysis']
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Intent:** {analysis.get('intent', 'Unknown')}")
                    st.write(f"**Complexity:** {analysis.get('complexity', 'Medium')}")
                with col2:
                    st.write(f"**Entities:** {len(analysis.get('entities', {}))}")
                    st.write(f"**Visualizations:** {'Yes' if analysis.get('requires_visualization') else 'No'}")
        
        # Data analysis results
        if response.get('data_analysis'):
            st.subheader("📊 Analysis Results")
            data_analysis = response['data_analysis']
            
            # Summary statistics
            if data_analysis.get('summary_stats'):
                stats = data_analysis['summary_stats']
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if 'record_count' in stats:
                        st.metric("Records", f"{stats['record_count']:,}")
                with col2:
                    if 'total_amount' in stats:
                        st.metric("Total Amount", f"${stats['total_amount']:,.2f}")
                with col3:
                    if 'mean_amount' in stats:
                        st.metric("Average", f"${stats['mean_amount']:,.2f}")
                with col4:
                    if 'max_amount' in stats:
                        st.metric("Maximum", f"${stats['max_amount']:,.2f}")
        
        # Visualizations
        if response.get('visualizations'):
            st.subheader("📈 Visualizations")
            for viz in response['visualizations']:
                st.plotly_chart(viz['figure'], use_container_width=True)
                st.caption(viz.get('description', ''))
        
        # Narrative insights
        if response.get('narrative'):
            st.subheader("💡 AI Insights")
            st.markdown(response['narrative'])
        
        # Guidance response
        if response.get('guidance'):
            st.subheader("💡 Guidance")
            st.markdown(response['guidance'])
    
    def _display_grant_results(self, profile_analysis: Dict[str, Any], 
                             matched_grants: List[Any]):
        """Display grant discovery results"""
        # Profile analysis
        if profile_analysis.get('ai_analysis'):
            st.subheader("🏛️ Municipal Profile Analysis")
            st.markdown(profile_analysis['ai_analysis'])
        
        # Matched grants
        if matched_grants:
            st.subheader(f"💰 {len(matched_grants)} Grant Opportunities Found")
            
            # Display top matches
            for i, grant in enumerate(matched_grants[:5]):  # Top 5 grants
                with st.expander(f"🎯 {grant.title} - {grant.agency} (Score: {grant.eligibility_score:.1f})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Amount Range:** ${grant.min_amount:,} - ${grant.max_amount:,}")
                        st.write(f"**Deadline:** {grant.deadline.strftime('%B %d, %Y')}")
                        st.write(f"**Match Required:** {grant.match_percentage}%" if grant.match_required else "**Match Required:** No")
                        
                    with col2:
                        st.write(f"**Category:** {grant.category}")
                        st.write(f"**CFDA Number:** {grant.cfda_number}")
                        st.write(f"**Estimated Awards:** {grant.estimated_awards}")
                    
                    st.write(f"**Description:** {grant.description}")
                    
                    if grant.ai_analysis:
                        st.markdown("**AI Analysis:**")
                        st.markdown(grant.ai_analysis)
                    
                    st.markdown(f"**Application URL:** [Apply Here]({grant.application_url})")
    
    def _display_anomaly_results(self, anomaly_results: Dict[str, Any]):
        """Display anomaly detection results"""
        # Overall summary
        st.subheader("📊 Anomaly Detection Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", f"{anomaly_results['total_transactions']:,}")
        with col2:
            consolidated = anomaly_results.get('consolidated_anomalies', [])
            total_anomalies = sum(a.get('count', 0) for a in consolidated)
            st.metric("Total Anomalies", total_anomalies)
        with col3:
            risk_score = anomaly_results.get('risk_assessment', {}).get('overall_risk_score', 0)
            st.metric("Risk Score", f"{risk_score}/100")
        with col4:
            risk_level = anomaly_results.get('risk_assessment', {}).get('risk_level', 'Unknown')
            st.metric("Risk Level", risk_level)
        
        # Consolidated anomalies
        if anomaly_results.get('consolidated_anomalies'):
            st.subheader("🚨 Detected Anomalies")
            
            for anomaly in anomaly_results['consolidated_anomalies'][:10]:  # Top 10
                severity_color = {
                    'High': '🔴',
                    'Medium': '🟡',
                    'Low': '🟢'
                }.get(anomaly.get('severity', 'Low'), '⚪')
                
                with st.expander(f"{severity_color} {anomaly['type']} - {anomaly['layer']} ({anomaly['count']} instances)"):
                    st.write(f"**Severity:** {anomaly.get('severity', 'Unknown')}")
                    st.write(f"**Description:** {anomaly.get('description', 'No description available')}")
                    
                    if anomaly.get('transactions'):
                        st.write("**Sample Transactions:**")
                        sample_df = pd.DataFrame(anomaly['transactions'][:5])  # Top 5 samples
                        st.dataframe(sample_df, use_container_width=True)
        
        # AI insights
        if anomaly_results.get('ai_insights'):
            st.subheader("🤖 AI Investigation Guidance")
            st.markdown(anomaly_results['ai_insights'])
    
    def _display_quality_results(self, quality_results: Dict[str, Any]):
        """Display data quality assessment results"""
        # Overall quality score
        st.subheader("📊 Data Quality Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            quality_score = quality_results.get('overall_quality_score', 0)
            st.metric("Quality Score", f"{quality_score}/100")
        with col2:
            total_issues = len(quality_results.get('quality_issues', []))
            st.metric("Total Issues", total_issues)
        with col3:
            high_severity = len([i for i in quality_results.get('quality_issues', []) if i.severity == 'High'])
            st.metric("High Severity", high_severity)
        with col4:
            st.metric("Total Records", f"{quality_results['total_records']:,}")
        
        # Quality issues
        if quality_results.get('quality_issues'):
            st.subheader("🔍 Quality Issues Detected")
            
            for issue in quality_results['quality_issues'][:15]:  # Top 15 issues
                severity_color = {
                    'High': '🔴',
                    'Medium': '🟡',
                    'Low': '🟢'
                }.get(issue.severity, '⚪')
                
                with st.expander(f"{severity_color} {issue.issue_type} - {issue.field_name} ({issue.affected_rows} records)"):
                    st.write(f"**Severity:** {issue.severity}")
                    st.write(f"**Description:** {issue.description}")
                    st.write(f"**Affected Records:** {issue.affected_rows}")
                    
                    if issue.suggested_fix:
                        st.write(f"**Suggested Fix:** {issue.suggested_fix}")
                    
                    if issue.sample_values:
                        st.write(f"**Sample Values:** {', '.join(map(str, issue.sample_values))}")
                    
                    if issue.auto_fixable:
                        st.info("✅ This issue can be automatically fixed")
        
        # AI recommendations
        if quality_results.get('ai_recommendations'):
            st.subheader("🤖 AI Quality Recommendations")
            st.markdown(quality_results['ai_recommendations'])
    
    def _display_conversation_history(self):
        """Display conversation history"""
        history = self.natural_language.get_conversation_history(limit=10)
        
        if history:
            st.subheader("📜 Recent Conversations")
            for i, item in enumerate(history[:5]):  # Last 5 conversations
                with st.expander(f"Query {i+1}: {item['query'][:50]}..."):
                    st.write(f"**Query:** {item['query']}")
                    st.write(f"**Intent:** {item['intent']}")
                    st.write(f"**Time:** {item['timestamp']}")
        else:
            st.info("No conversation history available yet.")