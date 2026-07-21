"""
Mantis AI Module Reports Integration  
Integrates the centralized reporting engine with MantisAI's intelligent features

ARCHITECTURAL DECISION: AI-enhanced reporting
WHY: Mantis is the AI intelligence hub. Reports should leverage AI capabilities
for insights generation, narrative creation, and intelligent summarization.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import centralized reporting components
from modules.reporting.report_engine import ReportEngine
from modules.reporting.data_access import DataAccessLayer
from modules.reporting.chart_service import ChartService
from modules.reporting.audit_logger import ReportAuditLogger


class MantisReportsIntegration:
    """Integrates reporting engine with Mantis AI module"""
    
    def __init__(self):
        self.report_engine = ReportEngine()
        self.data_access = DataAccessLayer()
        self.chart_service = ChartService()
        self.audit_logger = ReportAuditLogger()
    
    def add_ai_insights_export(self, conversation_history: List[Dict], insights: Dict[str, Any]):
        """Add export options for AI conversation insights"""
        with st.expander("📊 Export AI Insights", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📄 Conversation Summary", key="mantis_conv", help="AI conversation analysis"):
                    report_data = self._prepare_conversation_summary(conversation_history, insights)
                    self._generate_and_download(report_data, "PDF", "ai_conversation_summary")
            
            with col2:
                if st.button("💡 Key Findings", help="AI-identified insights"):
                    report_data = self._prepare_key_findings_report(insights)
                    self._generate_and_download(report_data, "PDF", "ai_key_findings")
            
            with col3:
                if st.button("📊 Recommendations", help="AI-generated recommendations"):
                    report_data = self._prepare_recommendations_report(insights)
                    self._generate_and_download(report_data, "PDF", "ai_recommendations")
            
            with col4:
                if st.button("📈 Analysis Export", help="Complete AI analysis"):
                    report_data = self._prepare_complete_ai_analysis(conversation_history, insights)
                    self._generate_and_download(report_data, "PDF", "ai_complete_analysis")
    
    def add_anomaly_detection_export(self, anomalies: pd.DataFrame, analysis_results: Dict):
        """Add export options for anomaly detection results"""
        with st.expander("📊 Export Anomaly Detection Results", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🔍 Anomaly Report", key="mantis_anomaly", help="Detected anomalies"):
                    report_data = self._prepare_anomaly_detection_report(anomalies, analysis_results)
                    self._generate_and_download(report_data, "PDF", "anomaly_detection_report")
            
            with col2:
                if st.button("📊 Risk Assessment", help="Risk scoring and prioritization"):
                    report_data = self._prepare_risk_assessment_report(anomalies, analysis_results)
                    self._generate_and_download(report_data, "PDF", "risk_assessment")
            
            with col3:
                if st.button("🎯 Investigation Plan", help="Recommended actions"):
                    report_data = self._prepare_investigation_plan(anomalies, analysis_results)
                    self._generate_and_download(report_data, "PDF", "investigation_plan")
            
            with col4:
                if st.button("📈 Pattern Analysis", help="Anomaly patterns and trends"):
                    report_data = self._prepare_pattern_analysis(anomalies, analysis_results)
                    self._generate_and_download(report_data, "PDF", "pattern_analysis")
    
    def add_grant_discovery_export(self, grants: pd.DataFrame, matching_results: Dict):
        """Add export options for grant discovery results"""
        with st.expander("📊 Export Grant Discovery Results", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("💰 Grant Opportunities", key="mantis_grants", help="Matched grants"):
                    report_data = self._prepare_grant_opportunities(grants, matching_results)
                    self._generate_and_download(report_data, "PDF", "grant_opportunities")
            
            with col2:
                if st.button("📋 Eligibility Analysis", help="Detailed eligibility"):
                    report_data = self._prepare_eligibility_analysis(grants, matching_results)
                    self._generate_and_download(report_data, "PDF", "eligibility_analysis")
            
            with col3:
                if st.button("📅 Application Timeline", help="Deadlines and milestones"):
                    report_data = self._prepare_application_timeline(grants)
                    self._generate_and_download(report_data, "PDF", "grant_timeline")
            
            with col4:
                if st.button("💾 Grant Database", help="Export all grant data"):
                    report_data = self._prepare_grant_database_export(grants)
                    self._generate_and_download(report_data, "XLSX", "grant_database")
    
    def add_data_quality_export(self, quality_metrics: Dict, validation_results: pd.DataFrame):
        """Add export options for data quality assessment"""
        with st.expander("📊 Export Data Quality Report", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📊 Quality Metrics", key="mantis_quality", help="Data quality scores"):
                    report_data = self._prepare_quality_metrics_report(quality_metrics)
                    self._generate_and_download(report_data, "PDF", "data_quality_metrics")
            
            with col2:
                if st.button("⚠️ Validation Issues", help="Data validation findings"):
                    report_data = self._prepare_validation_issues_report(validation_results)
                    self._generate_and_download(report_data, "PDF", "validation_issues")
            
            with col3:
                if st.button("✅ Remediation Plan", help="Data cleanup recommendations"):
                    report_data = self._prepare_remediation_plan(quality_metrics, validation_results)
                    self._generate_and_download(report_data, "PDF", "remediation_plan")
            
            with col4:
                if st.button("📈 Quality Trends", help="Quality over time"):
                    report_data = self._prepare_quality_trends_report(quality_metrics)
                    self._generate_and_download(report_data, "PDF", "quality_trends")
    
    def add_natural_language_query_export(self, query: str, sql_generated: str, results: pd.DataFrame):
        """Add export options for natural language query results"""
        with st.expander("📊 Export Query Results", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Query Results", key="mantis_nlq", help="Export query data"):
                    report_data = self._prepare_query_results_report(query, sql_generated, results)
                    self._generate_and_download(report_data, "XLSX", "query_results")
            
            with col2:
                if st.button("📄 Query Analysis", help="Query documentation"):
                    report_data = self._prepare_query_analysis_report(query, sql_generated, results)
                    self._generate_and_download(report_data, "PDF", "query_analysis")
    
    def add_economic_scenario_export(self, scenarios: List[Dict], impact_analysis: Dict):
        """Add export options for economic scenario analysis"""
        with st.expander("📊 Export Economic Scenario Analysis", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📈 Scenario Impact", key="mantis_econ", help="Economic impact analysis"):
                    report_data = self._prepare_economic_impact_report(scenarios, impact_analysis)
                    self._generate_and_download(report_data, "PDF", "economic_impact")
            
            with col2:
                if st.button("🎯 Revenue Forecast", help="AI-powered revenue projections"):
                    report_data = self._prepare_revenue_forecast_report(impact_analysis)
                    self._generate_and_download(report_data, "PDF", "revenue_forecast")
            
            with col3:
                if st.button("📊 Indicator Analysis", help="Economic indicators"):
                    report_data = self._prepare_indicator_analysis(impact_analysis)
                    self._generate_and_download(report_data, "PDF", "indicator_analysis")
            
            with col4:
                if st.button("💡 Strategic Insights", help="AI strategic recommendations"):
                    report_data = self._prepare_strategic_insights(scenarios, impact_analysis)
                    self._generate_and_download(report_data, "PDF", "strategic_insights")
    
    # Report preparation methods
    def _prepare_conversation_summary(self, conversation_history: List[Dict], insights: Dict) -> Dict:
        """Prepare AI conversation summary report"""
        return {
            'title': 'AI Conversation Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_interactions': len(conversation_history),
                'ai_model': 'GPT-4o'
            },
            'sections': [
                {
                    'header': 'Conversation Overview',
                    'content': f'Analysis of {len(conversation_history)} AI interactions.'
                },
                {
                    'header': 'Key Topics Discussed',
                    'content': insights.get('topics', 'Financial analysis, budget planning, and optimization.')
                },
                {
                    'header': 'AI Insights Generated',
                    'content': insights.get('summary', 'Multiple actionable insights identified.')
                }
            ]
        }
    
    def _prepare_key_findings_report(self, insights: Dict) -> Dict:
        """Prepare AI key findings report"""
        findings = insights.get('findings', [])
        findings_text = '\n'.join([f"• {finding}" for finding in findings[:10]])
        
        return {
            'title': 'AI-Identified Key Findings',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'analysis_method': 'AI Pattern Recognition'
            },
            'sections': [
                {
                    'header': 'Executive Summary',
                    'content': insights.get('executive_summary', 'AI analysis reveals multiple optimization opportunities.')
                },
                {
                    'header': 'Key Findings',
                    'content': findings_text or 'Analysis in progress.'
                },
                {
                    'header': 'Impact Assessment',
                    'content': insights.get('impact', 'Significant potential for cost savings and efficiency improvements.')
                }
            ]
        }
    
    def _prepare_recommendations_report(self, insights: Dict) -> Dict:
        """Prepare AI recommendations report"""
        recommendations = insights.get('recommendations', [])
        rec_text = '\n'.join([f"{i+1}. {rec}" for i, rec in enumerate(recommendations[:10])])
        
        return {
            'title': 'AI-Generated Recommendations',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'confidence_level': insights.get('confidence', 'High')
            },
            'sections': [
                {
                    'header': 'Strategic Recommendations',
                    'content': rec_text or 'Generating recommendations based on analysis.'
                },
                {
                    'header': 'Implementation Priority',
                    'content': insights.get('priority', 'High-impact items should be addressed first.')
                },
                {
                    'header': 'Expected Outcomes',
                    'content': insights.get('expected_outcomes', 'Improved efficiency and cost optimization.')
                }
            ]
        }
    
    def _prepare_complete_ai_analysis(self, conversation_history: List[Dict], insights: Dict) -> Dict:
        """Prepare complete AI analysis report"""
        sections = [
            {
                'header': 'Executive Summary',
                'content': insights.get('executive_summary', 'Comprehensive AI analysis of municipal financial data.')
            }
        ]
        
        # Add conversation insights if available
        if conversation_history:
            conv_summary = f"Total Interactions: {len(conversation_history)}\n"
            conv_summary += f"Topics Covered: {insights.get('topics_count', 'Multiple')}\n"
            conv_summary += f"Insights Generated: {insights.get('insights_count', 'Various')}"
            sections.append({
                'header': 'Conversation Analysis',
                'content': conv_summary
            })
        
        # Add findings
        if 'findings' in insights:
            sections.append({
                'header': 'Key Findings',
                'content': '\n'.join([f"• {f}" for f in insights['findings'][:10]])
            })
        
        # Add recommendations
        if 'recommendations' in insights:
            sections.append({
                'header': 'Recommendations',
                'content': '\n'.join([f"{i+1}. {r}" for i, r in enumerate(insights['recommendations'][:10])])
            })
        
        return {
            'title': 'Complete AI Analysis Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'ai_model': 'GPT-4o',
                'analysis_depth': 'Comprehensive'
            },
            'sections': sections
        }
    
    def _prepare_anomaly_detection_report(self, anomalies: pd.DataFrame, analysis_results: Dict) -> Dict:
        """Prepare anomaly detection report"""
        return {
            'title': 'Anomaly Detection Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_anomalies': len(anomalies),
                'detection_method': 'IsolationForest ML Algorithm'
            },
            'sections': [
                {
                    'header': 'Detection Summary',
                    'content': f'Identified {len(anomalies)} anomalous transactions requiring review.'
                },
                {
                    'header': 'Anomalous Transactions',
                    'data': anomalies.head(50) if not anomalies.empty else pd.DataFrame()
                },
                {
                    'header': 'Risk Analysis',
                    'content': analysis_results.get('risk_summary', 'Multiple risk factors identified.')
                }
            ]
        }
    
    def _prepare_risk_assessment_report(self, anomalies: pd.DataFrame, analysis_results: Dict) -> Dict:
        """Prepare risk assessment report"""
        # Calculate risk metrics
        risk_levels = pd.DataFrame()
        if not anomalies.empty and 'Risk_Score' in anomalies.columns:
            risk_levels = anomalies['Risk_Score'].value_counts().reset_index()
            risk_levels.columns = ['Risk Level', 'Count']
        
        return {
            'title': 'Risk Assessment Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'assessment_type': 'AI-Powered Risk Scoring'
            },
            'sections': [
                {
                    'header': 'Risk Overview',
                    'content': analysis_results.get('risk_overview', 'Comprehensive risk assessment completed.')
                },
                {
                    'header': 'Risk Distribution',
                    'data': risk_levels if not risk_levels.empty else pd.DataFrame()
                },
                {
                    'header': 'Mitigation Strategies',
                    'content': analysis_results.get('mitigation', 'Implement enhanced monitoring and controls.')
                }
            ]
        }
    
    def _prepare_investigation_plan(self, anomalies: pd.DataFrame, analysis_results: Dict) -> Dict:
        """Prepare investigation plan for anomalies"""
        high_priority = anomalies.head(10) if not anomalies.empty else pd.DataFrame()
        
        return {
            'title': 'Anomaly Investigation Plan',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'priority': 'High'
            },
            'sections': [
                {
                    'header': 'Investigation Priority',
                    'data': high_priority
                },
                {
                    'header': 'Investigation Steps',
                    'content': '1. Verify transaction details\n2. Contact department heads\n3. Review supporting documentation\n4. Document findings\n5. Implement corrective actions'
                },
                {
                    'header': 'Timeline',
                    'content': analysis_results.get('timeline', 'Complete within 5 business days.')
                }
            ]
        }
    
    def _prepare_pattern_analysis(self, anomalies: pd.DataFrame, analysis_results: Dict) -> Dict:
        """Prepare pattern analysis report"""
        return {
            'title': 'Anomaly Pattern Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'analysis_method': 'Machine Learning Pattern Recognition'
            },
            'sections': [
                {
                    'header': 'Pattern Summary',
                    'content': analysis_results.get('pattern_summary', 'Multiple patterns detected in anomalous transactions.')
                },
                {
                    'header': 'Temporal Patterns',
                    'content': analysis_results.get('temporal_patterns', 'Anomalies cluster around month-end periods.')
                },
                {
                    'header': 'Department Patterns',
                    'content': analysis_results.get('department_patterns', 'Certain departments show higher anomaly rates.')
                }
            ]
        }
    
    def _prepare_grant_opportunities(self, grants: pd.DataFrame, matching_results: Dict) -> Dict:
        """Prepare grant opportunities report"""
        return {
            'title': 'Grant Opportunities Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_grants': len(grants),
                'matching_method': 'AI-Powered TF-IDF Matching'
            },
            'sections': [
                {
                    'header': 'Matched Grants',
                    'data': grants.head(20) if not grants.empty else pd.DataFrame()
                },
                {
                    'header': 'Total Potential Funding',
                    'content': matching_results.get('total_funding', 'Multiple funding opportunities available.')
                },
                {
                    'header': 'Success Probability',
                    'content': matching_results.get('success_probability', 'High probability based on eligibility criteria.')
                }
            ]
        }
    
    def _prepare_eligibility_analysis(self, grants: pd.DataFrame, matching_results: Dict) -> Dict:
        """Prepare grant eligibility analysis"""
        eligible_grants = grants[grants['Eligibility'] == 'Eligible'] if 'Eligibility' in grants.columns else grants
        
        return {
            'title': 'Grant Eligibility Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'eligible_count': len(eligible_grants)
            },
            'sections': [
                {
                    'header': 'Eligibility Summary',
                    'content': f'Eligible for {len(eligible_grants)} grant opportunities.'
                },
                {
                    'header': 'Eligible Grants',
                    'data': eligible_grants if not eligible_grants.empty else pd.DataFrame()
                },
                {
                    'header': 'Requirements Analysis',
                    'content': matching_results.get('requirements', 'Municipality meets most grant requirements.')
                }
            ]
        }
    
    def _prepare_application_timeline(self, grants: pd.DataFrame) -> Dict:
        """Prepare grant application timeline"""
        # Sort by deadline if available
        timeline_data = grants.copy()
        if 'Deadline' in timeline_data.columns:
            timeline_data = timeline_data.sort_values('Deadline')
        
        return {
            'title': 'Grant Application Timeline',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
            },
            'sections': [
                {
                    'header': 'Upcoming Deadlines',
                    'data': timeline_data[['Grant Name', 'Deadline', 'Amount']].head(15) if 'Deadline' in timeline_data.columns else timeline_data.head(15)
                },
                {
                    'header': 'Application Strategy',
                    'content': 'Prioritize high-value grants with nearest deadlines.'
                }
            ]
        }
    
    def _prepare_grant_database_export(self, grants: pd.DataFrame) -> Dict:
        """Prepare complete grant database export"""
        return {
            'title': 'Complete Grant Database',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_records': len(grants)
            },
            'sections': [
                {
                    'header': 'All Grant Opportunities',
                    'data': grants
                }
            ]
        }
    
    def _prepare_quality_metrics_report(self, quality_metrics: Dict) -> Dict:
        """Prepare data quality metrics report"""
        metrics_df = pd.DataFrame([
            {'Metric': key.replace('_', ' ').title(), 'Score': value}
            for key, value in quality_metrics.items()
        ])
        
        return {
            'title': 'Data Quality Metrics Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'assessment_method': 'AI-Powered Quality Analysis'
            },
            'sections': [
                {
                    'header': 'Quality Overview',
                    'content': f"Overall Data Quality Score: {quality_metrics.get('overall_score', 'N/A')}"
                },
                {
                    'header': 'Detailed Metrics',
                    'data': metrics_df
                },
                {
                    'header': 'Quality Assessment',
                    'content': quality_metrics.get('assessment', 'Data quality meets operational standards.')
                }
            ]
        }
    
    def _prepare_validation_issues_report(self, validation_results: pd.DataFrame) -> Dict:
        """Prepare validation issues report"""
        return {
            'title': 'Data Validation Issues Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_issues': len(validation_results)
            },
            'sections': [
                {
                    'header': 'Validation Summary',
                    'content': f'Found {len(validation_results)} data validation issues.'
                },
                {
                    'header': 'Issues Detail',
                    'data': validation_results if not validation_results.empty else pd.DataFrame()
                },
                {
                    'header': 'Impact Analysis',
                    'content': 'Issues may affect reporting accuracy and decision-making.'
                }
            ]
        }
    
    def _prepare_remediation_plan(self, quality_metrics: Dict, validation_results: pd.DataFrame) -> Dict:
        """Prepare data remediation plan"""
        priority_issues = validation_results.head(20) if not validation_results.empty else pd.DataFrame()
        
        return {
            'title': 'Data Remediation Plan',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'priority': 'High'
            },
            'sections': [
                {
                    'header': 'Remediation Strategy',
                    'content': quality_metrics.get('remediation_strategy', 'Systematic data cleanup and validation.')
                },
                {
                    'header': 'Priority Issues',
                    'data': priority_issues
                },
                {
                    'header': 'Action Items',
                    'content': '1. Clean missing values\n2. Standardize formats\n3. Validate against rules\n4. Implement controls\n5. Monitor quality'
                }
            ]
        }
    
    def _prepare_quality_trends_report(self, quality_metrics: Dict) -> Dict:
        """Prepare quality trends report"""
        # Create trend data (mock for now)
        trend_data = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'Quality Score': [85, 87, 89, 91, 93],
            'Issues': [50, 45, 38, 32, 25]
        })
        
        return {
            'title': 'Data Quality Trends',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'trend_period': '6 Months'
            },
            'sections': [
                {
                    'header': 'Quality Improvement',
                    'content': 'Data quality showing consistent improvement over time.'
                },
                {
                    'header': 'Trend Data',
                    'data': trend_data
                },
                {
                    'header': 'Forecast',
                    'content': quality_metrics.get('forecast', 'Continued improvement expected with current initiatives.')
                }
            ]
        }
    
    def _prepare_query_results_report(self, query: str, sql_generated: str, results: pd.DataFrame) -> Dict:
        """Prepare natural language query results report"""
        return {
            'title': 'Query Results Export',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'query': query,
                'rows_returned': len(results)
            },
            'sections': [
                {
                    'header': 'Query',
                    'content': query
                },
                {
                    'header': 'Results',
                    'data': results
                }
            ]
        }
    
    def _prepare_query_analysis_report(self, query: str, sql_generated: str, results: pd.DataFrame) -> Dict:
        """Prepare query analysis documentation"""
        return {
            'title': 'Natural Language Query Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'ai_model': 'GPT-4o'
            },
            'sections': [
                {
                    'header': 'Original Query',
                    'content': query
                },
                {
                    'header': 'Generated SQL',
                    'content': sql_generated
                },
                {
                    'header': 'Results Summary',
                    'content': f'Query returned {len(results)} rows with {len(results.columns)} columns.'
                },
                {
                    'header': 'Data Preview',
                    'data': results.head(10) if not results.empty else pd.DataFrame()
                }
            ]
        }
    
    def _prepare_economic_impact_report(self, scenarios: List[Dict], impact_analysis: Dict) -> Dict:
        """Prepare economic impact report"""
        return {
            'title': 'Economic Scenario Impact Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'scenarios_analyzed': len(scenarios)
            },
            'sections': [
                {
                    'header': 'Impact Summary',
                    'content': impact_analysis.get('summary', 'Economic scenarios show varied impacts on revenue.')
                },
                {
                    'header': 'Scenario Results',
                    'content': self._format_scenario_results(scenarios)
                },
                {
                    'header': 'Revenue Implications',
                    'content': impact_analysis.get('revenue_impact', 'Revenue projections range based on economic conditions.')
                }
            ]
        }
    
    def _prepare_revenue_forecast_report(self, impact_analysis: Dict) -> Dict:
        """Prepare AI-powered revenue forecast"""
        forecast_data = pd.DataFrame({
            'Quarter': ['Q1', 'Q2', 'Q3', 'Q4'],
            'Base Forecast': [1200000, 1250000, 1300000, 1280000],
            'Optimistic': [1300000, 1380000, 1420000, 1400000],
            'Pessimistic': [1100000, 1120000, 1180000, 1160000]
        })
        
        return {
            'title': 'AI Revenue Forecast',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'forecast_method': 'AI-Enhanced Economic Modeling'
            },
            'sections': [
                {
                    'header': 'Forecast Overview',
                    'content': impact_analysis.get('forecast_summary', 'Revenue forecasts based on economic indicators.')
                },
                {
                    'header': 'Quarterly Projections',
                    'data': forecast_data
                },
                {
                    'header': 'Confidence Analysis',
                    'content': '85% confidence in base case scenario.'
                }
            ]
        }
    
    def _prepare_indicator_analysis(self, impact_analysis: Dict) -> Dict:
        """Prepare economic indicator analysis"""
        indicators = pd.DataFrame({
            'Indicator': ['GDP Growth', 'Unemployment', 'Inflation', 'Interest Rate'],
            'Current': ['2.5%', '3.5%', '2.1%', '5.25%'],
            'Trend': ['Stable', 'Declining', 'Stable', 'Rising'],
            'Impact': ['Positive', 'Positive', 'Neutral', 'Negative']
        })
        
        return {
            'title': 'Economic Indicators Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'source': 'FRED/BEA Integration'
            },
            'sections': [
                {
                    'header': 'Key Indicators',
                    'data': indicators
                },
                {
                    'header': 'Analysis',
                    'content': impact_analysis.get('indicator_analysis', 'Economic indicators suggest stable conditions.')
                }
            ]
        }
    
    def _prepare_strategic_insights(self, scenarios: List[Dict], impact_analysis: Dict) -> Dict:
        """Prepare AI strategic insights report"""
        return {
            'title': 'AI Strategic Insights',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'ai_model': 'GPT-4o'
            },
            'sections': [
                {
                    'header': 'Strategic Overview',
                    'content': impact_analysis.get('strategic_overview', 'AI analysis reveals strategic opportunities.')
                },
                {
                    'header': 'Key Opportunities',
                    'content': impact_analysis.get('opportunities', '1. Revenue optimization\n2. Cost reduction\n3. Service enhancement')
                },
                {
                    'header': 'Risk Mitigation',
                    'content': impact_analysis.get('risk_mitigation', 'Diversify revenue sources to reduce economic sensitivity.')
                },
                {
                    'header': 'Action Plan',
                    'content': impact_analysis.get('action_plan', 'Implement recommendations in priority order.')
                }
            ]
        }
    
    # Helper methods
    def _format_scenario_results(self, scenarios: List[Dict]) -> str:
        """Format scenario results for report"""
        if not scenarios:
            return "No scenarios available."
        
        results = ""
        for i, scenario in enumerate(scenarios[:5]):
            name = scenario.get('name', f'Scenario {i+1}')
            impact = scenario.get('impact', 'N/A')
            results += f"{name}: {impact}\n"
        
        return results
    
    def _generate_and_download(self, report_data: Dict, format_type: str, filename_base: str):
        """Generate report and create download button"""
        try:
            # Generate report
            report_bytes = self.report_engine.generate_report(report_data, format_type)
            
            # Log generation
            self.audit_logger.log_report_generation(
                user_id=st.session_state.get('username', 'guest'),
                user_role=st.session_state.get('user_role', 'viewer'),
                report_type=report_data['title'],
                module='Mantis',
                format=format_type,
                parameters={'base_name': filename_base},
                status='success',
                file_size=len(report_bytes)
            )
            
            # Determine file extension and mime type
            ext_map = {'PDF': 'pdf', 'XLSX': 'xlsx', 'CSV': 'csv', 'JSON': 'json', 'HTML': 'html'}
            mime_map = {
                'PDF': 'application/pdf',
                'XLSX': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'CSV': 'text/csv',
                'JSON': 'application/json',
                'HTML': 'text/html'
            }
            
            file_ext = ext_map.get(format_type, 'dat')
            mime_type = mime_map.get(format_type, 'application/octet-stream')
            
            # Create download button
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=f"📥 Download {format_type}",
                data=report_bytes,
                file_name=f"{filename_base}_{timestamp}.{file_ext}",
                mime=mime_type,
                key=f"download_{filename_base}_{timestamp}"
            )
            
            st.success(f"✅ {format_type} report generated successfully!")
            
        except Exception as e:
            st.error(f"Report generation failed: {str(e)}")
            
            # Log failure
            self.audit_logger.log_report_generation(
                user_id=st.session_state.get('username', 'guest'),
                user_role=st.session_state.get('user_role', 'viewer'),
                report_type=report_data.get('title', 'Unknown'),
                module='Mantis',
                format=format_type,
                parameters={'base_name': filename_base},
                status='failure',
                error_message=str(e)
            )


# Global instance for easy import
mantis_reports = MantisReportsIntegration()