"""
Machine Learning Integration for BI Sandbox
Integrates anomaly detection, grant matching, and external data into BI Sandbox

This module provides the ML-enhanced features for the BI Sandbox interface
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Import ML pipeline components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.ml_pipeline.anomaly_detector import TransactionAnomalyDetector
from modules.ml_pipeline.grant_matcher import GrantMatcher, GrantOpportunity
from modules.external_data.fred_connector import FREDConnector
from modules.external_data.bea_connector import BEAConnector
from modules.external_data.cache_manager import CacheManager


def render_anomaly_detection_tab(org: str = "cityA"):
    """Render anomaly detection analysis tab"""
    st.markdown("### Transaction Anomaly Detection")
    st.markdown("Machine learning-powered detection of unusual financial patterns")
    
    # Initialize anomaly detector
    if 'anomaly_detector' not in st.session_state:
        st.session_state.anomaly_detector = TransactionAnomalyDetector()
        st.session_state.cache_manager = CacheManager()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Date range selector
        date_range = st.date_input(
            "Select Date Range",
            value=(datetime.now() - timedelta(days=365), datetime.now()),
            max_value=datetime.now()
        )
    
    with col2:
        # Contamination rate (expected anomaly percentage)
        contamination = st.slider(
            "Sensitivity (%)",
            min_value=1,
            max_value=10,
            value=5,
            help="Expected percentage of anomalies"
        ) / 100
    
    with col3:
        # Run detection button
        if st.button("🔍 Run Detection", type="primary"):
            st.session_state.run_detection = True
    
    # Run anomaly detection
    if st.session_state.get('run_detection', False):
        with st.spinner("Analyzing transactions for anomalies..."):
            # Load and analyze data
            start_date = date_range[0].strftime('%Y-%m-%d') if len(date_range) > 0 else None
            end_date = date_range[1].strftime('%Y-%m-%d') if len(date_range) > 1 else None
            
            # Load transaction data
            st.session_state.anomaly_detector.load_transaction_data(start_date, end_date)
            
            # Detect anomalies
            results = st.session_state.anomaly_detector.detect_anomalies(contamination)
            
            # Store results
            st.session_state.anomaly_results = results
            st.session_state.run_detection = False
    
    # Display results
    if 'anomaly_results' in st.session_state:
        results = st.session_state.anomaly_results
        anomalies = results[results['is_anomaly']]
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Transactions",
                f"{len(results):,}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Anomalies Detected",
                f"{len(anomalies):,}",
                delta=f"{(len(anomalies)/len(results)*100):.1f}%"
            )
        
        with col3:
            total_anomaly_amount = anomalies['Amount'].sum()
            st.metric(
                "Anomaly Amount",
                f"${abs(total_anomaly_amount):,.0f}",
                delta=None
            )
        
        with col4:
            avg_confidence = anomalies['confidence'].mean() if len(anomalies) > 0 else 0
            st.metric(
                "Avg Confidence",
                f"{avg_confidence:.1%}",
                delta=None
            )
        
        # Visualizations
        st.markdown("#### Anomaly Visualizations")
        
        # Get visualizations
        charts = st.session_state.anomaly_detector.create_anomaly_visualizations()
        
        # Display charts in tabs
        viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
            "Timeline", "Departments", "Score Distribution", "PCA Analysis"
        ])
        
        with viz_tab1:
            if 'timeline' in charts:
                st.plotly_chart(charts['timeline'], use_container_width=True)
        
        with viz_tab2:
            if 'department' in charts:
                st.plotly_chart(charts['department'], use_container_width=True)
        
        with viz_tab3:
            if 'scores' in charts:
                st.plotly_chart(charts['scores'], use_container_width=True)
        
        with viz_tab4:
            if 'pca' in charts:
                st.plotly_chart(charts['pca'], use_container_width=True)
        
        # Detailed anomaly table
        st.markdown("#### Anomaly Details")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dept_filter = st.selectbox(
                "Filter by Department",
                ["All"] + list(anomalies['DepartmentCode'].unique())
            )
        
        with col2:
            min_amount = st.number_input(
                "Min Amount ($)",
                value=0,
                step=1000
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                ["Anomaly Score", "Amount", "Date", "Confidence"]
            )
        
        # Apply filters
        filtered_anomalies = anomalies.copy()
        
        if dept_filter != "All":
            filtered_anomalies = filtered_anomalies[filtered_anomalies['DepartmentCode'] == dept_filter]
        
        if min_amount > 0:
            filtered_anomalies = filtered_anomalies[abs(filtered_anomalies['Amount']) >= min_amount]
        
        # Sort
        sort_column = {
            "Anomaly Score": "anomaly_score",
            "Amount": "Amount",
            "Date": "Date",
            "Confidence": "confidence"
        }[sort_by]
        
        filtered_anomalies = filtered_anomalies.sort_values(sort_column, ascending=(sort_by == "Anomaly Score"))
        
        # Display table
        if len(filtered_anomalies) > 0:
            display_columns = ['Date', 'DepartmentCode', 'Amount', 'Description', 
                             'confidence', 'anomaly_reason']
            
            # Format for display
            display_df = filtered_anomalies[display_columns].copy()
            display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.2f}")
            display_df['confidence'] = display_df['confidence'].apply(lambda x: f"{x:.1%}")
            display_df.columns = ['Date', 'Department', 'Amount', 'Description', 
                                 'Confidence', 'Reason']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Export option
            if st.button("📥 Export Anomalies to CSV"):
                csv = filtered_anomalies.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"anomalies_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No anomalies found matching the filter criteria.")
        
        # Department report
        st.markdown("#### Department Analysis")
        
        selected_dept = st.selectbox(
            "Select Department for Detailed Report",
            list(results['DepartmentCode'].unique())
        )
        
        if st.button("Generate Department Report"):
            dept_report = st.session_state.anomaly_detector.get_department_report(selected_dept)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**{selected_dept} Statistics**")
                st.write(f"Total Transactions: {dept_report['total_transactions']:,}")
                st.write(f"Anomalies Found: {dept_report['anomaly_count']}")
                st.write(f"Anomaly Rate: {dept_report['anomaly_rate']:.1%}")
                st.write(f"Total Anomaly Amount: ${dept_report['total_anomaly_amount']:,.2f}")
                st.write(f"Average Anomaly: ${dept_report['average_anomaly_amount']:,.2f}")
            
            with col2:
                st.markdown("**Top Anomalies**")
                for anomaly in dept_report['top_anomalies']:
                    st.write(f"• {anomaly['Date']}: ${anomaly['Amount']:,.2f}")
                    st.caption(f"  {anomaly['anomaly_reason']}")


def render_grant_opportunities_tab(org: str = "cityA"):
    """Render grant matching and opportunities tab"""
    st.markdown("### Grant Opportunity Matching")
    st.markdown("AI-powered matching of department needs with available grants")
    
    # Initialize grant matcher
    if 'grant_matcher' not in st.session_state:
        st.session_state.grant_matcher = GrantMatcher()
    
    # Load budget data for department analysis
    try:
        from modules.database.db_connection import load_org_data
        budget_data = load_org_data(org)
    except:
        # Use mock data if database unavailable
        budget_data = pd.DataFrame({
            'DepartmentCode': ['Police', 'Fire', 'Public Works', 'Parks', 'Water'],
            'Budget': [5000000, 3000000, 4000000, 2000000, 6000000],
            'Actual': [5200000, 2900000, 4100000, 1900000, 6200000]
        })
    
    # Department selector
    departments = budget_data['DepartmentCode'].unique().tolist() if 'DepartmentCode' in budget_data.columns else ['General']
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_dept = st.selectbox(
            "Select Department",
            ["All Departments"] + departments
        )
    
    with col2:
        min_score = st.slider(
            "Min Match Score (%)",
            min_value=20,
            max_value=80,
            value=30,
            help="Minimum relevance score for grant matches"
        ) / 100
    
    # Search grants
    search_col1, search_col2 = st.columns([3, 1])
    
    with search_col1:
        search_query = st.text_input(
            "Search Grants",
            placeholder="e.g., infrastructure, safety, water, climate"
        )
    
    with search_col2:
        search_button = st.button("🔍 Search", type="primary")
    
    # Display results based on search or department selection
    if search_button and search_query:
        # Search-based results
        with st.spinner("Searching grant database..."):
            search_results = st.session_state.grant_matcher.search_grants(search_query)
            
            st.markdown(f"### Search Results for '{search_query}'")
            
            if search_results:
                for grant in search_results[:10]:
                    with st.expander(f"💰 {grant.title} - {grant.agency}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Agency:** {grant.agency}")
                            st.markdown(f"**Category:** {grant.category}")
                            st.markdown(f"**Description:** {grant.description}")
                            st.markdown(f"**Eligibility:** {grant.eligibility}")
                            if grant.url:
                                st.markdown(f"**More Info:** [Visit Website]({grant.url})")
                        
                        with col2:
                            st.metric("Funding Range", 
                                    f"${grant.amount_min/1000:.0f}K - ${grant.amount_max/1000000:.1f}M")
                            st.metric("Deadline", grant.deadline)
                            st.metric("Match Score", f"{grant.match_score:.0%}")
            else:
                st.info("No grants found matching your search criteria.")
    
    else:
        # Department-based matching
        st.markdown("### Grant Recommendations")
        
        if selected_dept == "All Departments":
            # Get matches for all departments
            with st.spinner("Analyzing all departments and matching grants..."):
                all_matches = st.session_state.grant_matcher.get_all_department_matches(
                    budget_data, departments
                )
            
            # Display department tabs
            dept_tabs = st.tabs(departments[:8])  # Limit to 8 tabs for UI
            
            for i, dept in enumerate(departments[:8]):
                with dept_tabs[i]:
                    if dept in all_matches:
                        display_department_grants(dept, all_matches[dept], 
                                                st.session_state.grant_matcher)
        else:
            # Single department analysis
            with st.spinner(f"Analyzing {selected_dept} needs and matching grants..."):
                profile = st.session_state.grant_matcher.extract_department_needs(
                    budget_data, selected_dept
                )
                matches = st.session_state.grant_matcher.match_grants(profile, min_score)
            
            # Display department profile
            with st.expander(f"📊 {selected_dept} Profile", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Budget Analysis**")
                    st.write(f"Total Budget: ${profile['total_budget']:,.0f}")
                    st.write(f"Actual Spending: ${profile['actual_spending']:,.0f}")
                    st.write(f"Variance: ${profile['variance']:,.0f}")
                
                with col2:
                    st.markdown("**Identified Priorities**")
                    for priority in profile['priorities']:
                        st.write(f"• {priority}")
            
            # Display matches
            display_department_grants(selected_dept, matches, st.session_state.grant_matcher)
    
    # Grant statistics
    st.markdown("### Grant Database Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Grants", len(st.session_state.grant_matcher.grant_database))
    
    with col2:
        agencies = set(g.agency for g in st.session_state.grant_matcher.grant_database)
        st.metric("Agencies", len(agencies))
    
    with col3:
        categories = set(g.category for g in st.session_state.grant_matcher.grant_database)
        st.metric("Categories", len(categories))
    
    with col4:
        total_max = sum(g.amount_max for g in st.session_state.grant_matcher.grant_database)
        st.metric("Total Funding", f"${total_max/1000000000:.1f}B")


def display_department_grants(department: str, matches: List[GrantOpportunity], 
                             grant_matcher: GrantMatcher):
    """Display grant matches for a department"""
    
    if not matches:
        st.info(f"No matching grants found for {department}")
        return
    
    # Generate report
    report = grant_matcher.generate_grant_report(department, matches)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Opportunities", report['total_opportunities'])
    
    with col2:
        st.metric("Min Funding", f"${report['total_potential_funding_min']/1000000:.1f}M")
    
    with col3:
        st.metric("Max Funding", f"${report['total_potential_funding_max']/1000000:.1f}M")
    
    # Top matches
    st.markdown("#### Top Grant Matches")
    
    for i, grant_info in enumerate(report['top_matches'][:5], 1):
        with st.expander(f"{i}. {grant_info['title']} ({grant_info['match_score']})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Agency:** {grant_info['agency']}")
                st.markdown(f"**Funding:** {grant_info['amount_range']}")
                st.markdown(f"**Deadline:** {grant_info['deadline']}")
                
                if grant_info['reasons']:
                    st.markdown("**Why it matches:**")
                    for reason in grant_info['reasons']:
                        st.write(f"• {reason}")
                
                if grant_info['url']:
                    st.markdown(f"[🔗 Apply Now]({grant_info['url']})")
            
            with col2:
                st.metric("Match Score", grant_info['match_score'])
    
    # Upcoming deadlines
    if report['upcoming_deadlines']:
        st.markdown("#### ⏰ Upcoming Deadlines")
        
        deadline_df = pd.DataFrame(report['upcoming_deadlines'])
        st.dataframe(deadline_df, use_container_width=True, hide_index=True)
    
    # Export option
    if st.button(f"📥 Export {department} Grant Report"):
        # Create detailed export
        export_data = []
        for grant in matches:
            export_data.append({
                'Department': department,
                'Grant Title': grant.title,
                'Agency': grant.agency,
                'Min Amount': grant.amount_min,
                'Max Amount': grant.amount_max,
                'Match Score': grant.match_score,
                'Deadline': grant.deadline,
                'Category': grant.category,
                'URL': grant.url
            })
        
        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False)
        
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{department}_grants_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


def render_economic_indicators_tab():
    """Render economic indicators from external data sources"""
    st.markdown("### Economic Indicators Dashboard")
    st.markdown("Real-time economic data for budget planning")
    
    # Initialize connectors
    if 'cache_manager' not in st.session_state:
        st.session_state.cache_manager = CacheManager()
    
    if 'fred_connector' not in st.session_state:
        st.session_state.fred_connector = FREDConnector(cache_manager=st.session_state.cache_manager)
    
    if 'bea_connector' not in st.session_state:
        st.session_state.bea_connector = BEAConnector(cache_manager=st.session_state.cache_manager)
    
    # Data source selector
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        data_source = st.selectbox(
            "Data Source",
            ["FRED (Federal Reserve)", "BEA (Economic Analysis)", "Combined View"]
        )
    
    with col2:
        # Date range
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=730),
            max_value=datetime.now()
        )
    
    with col3:
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.session_state.cache_manager.refresh_all_external_data()
            st.rerun()
    
    # Display data based on source
    if data_source == "FRED (Federal Reserve)":
        render_fred_indicators(start_date)
    
    elif data_source == "BEA (Economic Analysis)":
        render_bea_indicators(start_date)
    
    else:  # Combined View
        render_combined_economic_view(start_date)
    
    # Cache statistics
    with st.expander("📊 Cache Statistics"):
        cache_stats = st.session_state.cache_manager.get_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Cache Hit Rate", cache_stats['performance']['hit_rate'])
            st.metric("Memory Items", cache_stats['memory']['items'])
        
        with col2:
            st.metric("Total Hits", cache_stats['performance']['hits'])
            st.metric("Total Misses", cache_stats['performance']['misses'])
        
        with col3:
            st.metric("DB Entries", cache_stats['database'].get('total_entries', 0))
            st.metric("Expired", cache_stats['database'].get('expired_entries', 0))


def render_fred_indicators(start_date):
    """Render FRED economic indicators"""
    
    with st.spinner("Loading FRED economic data..."):
        # Get all indicators
        indicators = st.session_state.fred_connector.get_all_indicators(
            start_date=start_date.strftime('%Y-%m-%d')
        )
        
        # Calculate economic impact
        impact = st.session_state.fred_connector.calculate_economic_impact(indicators)
        
        # Create visualizations
        charts = st.session_state.fred_connector.create_economic_dashboard(indicators)
    
    # Display impact summary
    st.markdown("#### Economic Impact Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Inflation Adjustment", 
                 f"{(impact['inflation_adjustment']-1)*100:.1f}%",
                 delta="Year-over-year")
    
    with col2:
        st.metric("Revenue Impact", 
                 f"{(impact['revenue_impact']-1)*100:.1f}%",
                 delta="Projected")
    
    with col3:
        st.metric("Economic Outlook", 
                 impact['economic_outlook'].title())
    
    with col4:
        borrowing_cost = impact['cost_pressures'].get('borrowing_cost', 'N/A')
        st.metric("Borrowing Cost", borrowing_cost)
    
    # Display charts
    if charts:
        chart_tabs = st.tabs(list(charts.keys()))
        
        for i, (name, chart) in enumerate(charts.items()):
            with chart_tabs[i]:
                st.plotly_chart(chart, use_container_width=True)
    
    # Recommendations
    if impact['recommendations']:
        st.markdown("#### 💡 Budget Recommendations")
        for rec in impact['recommendations']:
            st.info(f"• {rec}")


def render_bea_indicators(start_date):
    """Render BEA regional economic indicators"""
    
    with st.spinner("Loading BEA regional data..."):
        # Get regional indicators
        data = st.session_state.bea_connector.get_all_regional_indicators()
        
        # Calculate trends
        trends = st.session_state.bea_connector.calculate_economic_trends(data)
        
        # Create visualizations
        charts = st.session_state.bea_connector.create_regional_dashboard(data)
        
        # Get recommendations
        recommendations = st.session_state.bea_connector.get_budget_recommendations()
    
    # Display trends summary
    st.markdown("#### Regional Economic Trends")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        gdp_growth = trends.get('gdp_growth', 0)
        st.metric("GDP Growth", 
                 f"{gdp_growth*100:.1f}%",
                 delta="Annual")
    
    with col2:
        income_growth = trends.get('income_growth', 0)
        st.metric("Income Growth", 
                 f"{income_growth*100:.1f}%",
                 delta="Annual")
    
    with col3:
        emp_growth = trends.get('employment_growth', 0)
        st.metric("Employment Growth", 
                 f"{emp_growth*100:.1f}%",
                 delta="Annual")
    
    with col4:
        st.metric("Economic Health", 
                 trends['economic_health'].title())
    
    # Display charts
    if charts:
        chart_tabs = st.tabs(list(charts.keys()))
        
        for i, (name, chart) in enumerate(charts.items()):
            with chart_tabs[i]:
                st.plotly_chart(chart, use_container_width=True)
    
    # Budget recommendations
    st.markdown("#### 📊 Budget Planning Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Opportunities**")
        for opp in recommendations.get('opportunities', []):
            st.success(f"• {opp}")
    
    with col2:
        st.markdown("**Risks**")
        for risk in recommendations.get('risks', []):
            st.warning(f"• {risk}")


def render_combined_economic_view(start_date):
    """Render combined economic indicators from multiple sources"""
    
    st.markdown("#### Comprehensive Economic Analysis")
    
    # Load data from both sources
    with st.spinner("Loading comprehensive economic data..."):
        # FRED data
        fred_indicators = st.session_state.fred_connector.get_all_indicators(
            start_date=start_date.strftime('%Y-%m-%d')
        )
        fred_impact = st.session_state.fred_connector.calculate_economic_impact(fred_indicators)
        
        # BEA data
        bea_data = st.session_state.bea_connector.get_all_regional_indicators()
        bea_trends = st.session_state.bea_connector.calculate_economic_trends(bea_data)
    
    # Combined metrics dashboard
    st.markdown("##### National vs Regional Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**National Indicators (FRED)**")
        st.write(f"• Inflation Impact: {(fred_impact['inflation_adjustment']-1)*100:.1f}%")
        st.write(f"• Revenue Projection: {(fred_impact['revenue_impact']-1)*100:.1f}%")
        st.write(f"• Economic Outlook: {fred_impact['economic_outlook'].title()}")
        
        for pressure, value in fred_impact['cost_pressures'].items():
            st.write(f"• {pressure.replace('_', ' ').title()}: {value}")
    
    with col2:
        st.markdown("**Regional Indicators (BEA)**")
        st.write(f"• GDP Growth: {bea_trends.get('gdp_growth', 0)*100:.1f}%")
        st.write(f"• Income Growth: {bea_trends.get('income_growth', 0)*100:.1f}%")
        st.write(f"• Employment Growth: {bea_trends.get('employment_growth', 0)*100:.1f}%")
        st.write(f"• Economic Health: {bea_trends['economic_health'].title()}")
    
    # Combined recommendations
    st.markdown("##### Integrated Budget Planning Recommendations")
    
    all_recommendations = fred_impact['recommendations'] + bea_trends.get('trend_analysis', [])
    
    if all_recommendations:
        for rec in all_recommendations:
            st.info(f"📌 {rec}")
    
    # Export economic report
    if st.button("📄 Generate Economic Impact Report"):
        report = {
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'national_indicators': fred_impact,
            'regional_indicators': bea_trends,
            'recommendations': all_recommendations
        }
        
        st.json(report)
        
        # Option to download
        import json
        report_json = json.dumps(report, indent=2, default=str)
        st.download_button(
            label="Download Report (JSON)",
            data=report_json,
            file_name=f"economic_report_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )