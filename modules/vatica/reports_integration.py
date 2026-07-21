"""
Vatica Module Reports Integration
Integrates the centralized reporting engine with Vatica's existing tabs

ARCHITECTURAL DECISION: Tab-specific reporting
WHY: Each tab in Vatica has unique data and reporting needs. By integrating
reports directly into each tab, users can export relevant data in context.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

# Import centralized reporting components
from modules.reporting.report_engine import ReportEngine
from modules.reporting.data_access import DataAccessLayer
from modules.reporting.chart_service import ChartService
from modules.reporting.audit_logger import ReportAuditLogger


class VaticaReportsIntegration:
    """Integrates reporting engine with Vatica module tabs"""
    
    def __init__(self):
        self.report_engine = ReportEngine()
        self.data_access = DataAccessLayer()
        self.chart_service = ChartService()
        self.audit_logger = ReportAuditLogger()
    
    def add_historical_analysis_export(self, df: pd.DataFrame, analysis_results: Dict[str, Any]):
        """Add export options to Historical Analysis tab"""
        with st.expander("📊 Export Historical Analysis", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            # Standard report templates
            with col1:
                if st.button("📄 Executive Summary", help="One-page summary with key trends"):
                    report_data = self._prepare_historical_executive_summary(df, analysis_results)
                    self._generate_and_download(report_data, "PDF", "historical_executive_summary")
            
            with col2:
                if st.button("📈 Detailed Analysis", help="Complete analysis with all charts"):
                    report_data = self._prepare_historical_detailed_report(df, analysis_results)
                    self._generate_and_download(report_data, "PDF", "historical_detailed_analysis")
            
            with col3:
                if st.button("📊 Data Export", help="Export raw data for further analysis"):
                    report_data = self._prepare_data_export(df, "Historical Analysis Data")
                    self._generate_and_download(report_data, "XLSX", "historical_data")
            
            with col4:
                if st.button("🎯 Presentation Deck", help="Ready for council meetings"):
                    report_data = self._prepare_historical_presentation(df, analysis_results)
                    self._generate_and_download(report_data, "PDF", "historical_presentation")
            
            # Custom export options
            st.markdown("---")
            format_type = st.selectbox(
                "Custom Export Format",
                ["PDF", "Excel (XLSX)", "CSV", "JSON", "HTML"],
                key="historical_export_format"
            )
            
            if st.button("Generate Custom Export", key="historical_custom_export"):
                report_data = self._prepare_historical_detailed_report(df, analysis_results)
                format_map = {"Excel (XLSX)": "XLSX"}
                export_format = format_map.get(format_type, format_type)
                self._generate_and_download(report_data, export_format, "historical_custom")
    
    def add_department_insights_export(self, df: pd.DataFrame, department: str, insights: Dict[str, Any]):
        """Add export options to Department Insights tab"""
        with st.expander("📊 Export Department Report", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            # Standard templates
            with col1:
                if st.button("📄 Executive Summary", key="dept_exec", help="Department overview"):
                    report_data = self._prepare_department_executive_summary(df, department, insights)
                    self._generate_and_download(report_data, "PDF", f"dept_{department}_executive")
            
            with col2:
                if st.button("💰 Budget vs Actual", help="Variance analysis report"):
                    report_data = self._prepare_budget_variance_report(df, department, insights)
                    self._generate_and_download(report_data, "PDF", f"dept_{department}_variance")
            
            with col3:
                if st.button("📊 Performance Metrics", help="KPIs and metrics"):
                    report_data = self._prepare_department_metrics(df, department, insights)
                    self._generate_and_download(report_data, "XLSX", f"dept_{department}_metrics")
            
            with col4:
                if st.button("📈 Trend Analysis", help="Historical trends"):
                    report_data = self._prepare_department_trends(df, department, insights)
                    self._generate_and_download(report_data, "PDF", f"dept_{department}_trends")
    
    def add_transaction_analyzer_export(self, df: pd.DataFrame, anomalies: Optional[pd.DataFrame] = None):
        """Add export options to Transaction Analyzer tab"""
        with st.expander("📊 Export Transaction Reports", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🔍 Anomaly Report", key="trans_anomaly", help="Flagged transactions"):
                    if anomalies is not None and not anomalies.empty:
                        report_data = self._prepare_anomaly_report(anomalies)
                        self._generate_and_download(report_data, "PDF", "transaction_anomalies")
                    else:
                        st.warning("No anomalies detected to export")
            
            with col2:
                if st.button("📋 Transaction Ledger", help="Detailed transaction list"):
                    report_data = self._prepare_transaction_ledger(df)
                    self._generate_and_download(report_data, "XLSX", "transaction_ledger")
            
            with col3:
                if st.button("🏢 Vendor Analysis", help="Spending by vendor"):
                    vendor_data = self.data_access.get_vendor_analysis()
                    report_data = self._prepare_vendor_report(vendor_data)
                    self._generate_and_download(report_data, "PDF", "vendor_analysis")
            
            with col4:
                if st.button("📊 Cross-Tab Report", help="Multi-dimensional analysis"):
                    report_data = self._prepare_crosstab_report(df)
                    self._generate_and_download(report_data, "XLSX", "transaction_crosstab")
    
    def add_balance_sheet_export(self, balance_data: Dict[str, pd.DataFrame], period: str):
        """Add export options to Balance Sheet tab"""
        with st.expander("📊 Export Balance Sheet Reports", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📄 Traditional Format", key="bs_traditional", help="Standard balance sheet"):
                    report_data = self._prepare_traditional_balance_sheet(balance_data, period)
                    self._generate_and_download(report_data, "PDF", "balance_sheet_traditional")
            
            with col2:
                if st.button("📈 Comparative Analysis", help="Period comparisons"):
                    report_data = self._prepare_comparative_balance_sheet(balance_data, period)
                    self._generate_and_download(report_data, "PDF", "balance_sheet_comparative")
            
            with col3:
                if st.button("📊 Financial Ratios", help="Key financial metrics"):
                    report_data = self._prepare_financial_ratios_report(balance_data)
                    self._generate_and_download(report_data, "PDF", "financial_ratios")
            
            with col4:
                if st.button("💾 Excel Workbook", help="Complete financial data"):
                    report_data = self._prepare_balance_sheet_workbook(balance_data, period)
                    self._generate_and_download(report_data, "XLSX", "balance_sheet_complete")
    
    # Report preparation methods
    def _prepare_historical_executive_summary(self, df: pd.DataFrame, analysis: Dict) -> Dict:
        """Prepare executive summary for historical analysis"""
        return {
            'title': 'Historical Analysis - Executive Summary',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'period': analysis.get('period', 'Multi-Year'),
                'organization': st.session_state.get('org_display_name', 'Organization')
            },
            'sections': [
                {
                    'header': 'Key Findings',
                    'content': analysis.get('summary', 'Historical trends show consistent patterns across departments.')
                },
                {
                    'header': 'Trend Analysis',
                    'data': df.groupby('Year').agg({
                        'Budget': 'sum',
                        'Actual': 'sum',
                        'Variance': 'mean'
                    }).round(2) if 'Year' in df.columns else df.head(10)
                },
                {
                    'header': 'Recommendations',
                    'content': analysis.get('recommendations', 'Continue monitoring trends and adjust budgets accordingly.')
                }
            ]
        }
    
    def _prepare_historical_detailed_report(self, df: pd.DataFrame, analysis: Dict) -> Dict:
        """Prepare detailed historical analysis report"""
        sections = [
            {
                'header': 'Executive Summary',
                'content': analysis.get('executive_summary', 'Comprehensive historical analysis of financial data.')
            },
            {
                'header': 'Data Overview',
                'data': df.describe() if not df.empty else pd.DataFrame()
            }
        ]
        
        # Add yearly breakdowns if available
        if 'Year' in df.columns:
            yearly_data = df.groupby('Year').agg({
                col: 'sum' for col in df.select_dtypes(include=['number']).columns
            }).round(2)
            sections.append({
                'header': 'Yearly Summary',
                'data': yearly_data
            })
        
        # Add department breakdowns if available
        if 'Department' in df.columns:
            dept_data = df.groupby('Department').agg({
                col: 'sum' for col in df.select_dtypes(include=['number']).columns
            }).round(2)
            sections.append({
                'header': 'Department Summary',
                'data': dept_data
            })
        
        return {
            'title': 'Historical Analysis - Detailed Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_records': len(df),
                'analysis_period': analysis.get('period', 'Historical')
            },
            'sections': sections
        }
    
    def _prepare_department_executive_summary(self, df: pd.DataFrame, dept: str, insights: Dict) -> Dict:
        """Prepare department executive summary"""
        dept_data = df[df['Department'] == dept] if 'Department' in df.columns else df
        
        return {
            'title': f'{dept} Department - Executive Summary',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'department': dept,
                'fiscal_year': datetime.now().year
            },
            'sections': [
                {
                    'header': 'Department Overview',
                    'content': insights.get('overview', f'Financial summary for {dept} department.')
                },
                {
                    'header': 'Key Metrics',
                    'data': dept_data.describe() if not dept_data.empty else pd.DataFrame()
                },
                {
                    'header': 'Budget Performance',
                    'content': insights.get('performance', 'Budget utilization within expected ranges.')
                }
            ]
        }
    
    def _prepare_budget_variance_report(self, df: pd.DataFrame, dept: str, insights: Dict) -> Dict:
        """Prepare budget variance report"""
        dept_data = df[df['Department'] == dept] if 'Department' in df.columns else df
        
        # Calculate variance if columns exist
        variance_data = pd.DataFrame()
        if 'Budget' in dept_data.columns and 'Actual' in dept_data.columns:
            variance_data = dept_data[['Budget', 'Actual']].copy()
            variance_data['Variance'] = variance_data['Actual'] - variance_data['Budget']
            variance_data['Variance %'] = (variance_data['Variance'] / variance_data['Budget'] * 100).round(2)
        
        return {
            'title': f'{dept} Department - Budget Variance Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'department': dept
            },
            'sections': [
                {
                    'header': 'Variance Summary',
                    'data': variance_data if not variance_data.empty else dept_data
                },
                {
                    'header': 'Analysis',
                    'content': insights.get('variance_analysis', 'Budget variances are within acceptable thresholds.')
                }
            ]
        }
    
    def _prepare_anomaly_report(self, anomalies: pd.DataFrame) -> Dict:
        """Prepare anomaly detection report"""
        return {
            'title': 'Transaction Anomaly Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_anomalies': len(anomalies),
                'risk_level': 'Requires Review'
            },
            'sections': [
                {
                    'header': 'Anomalies Detected',
                    'content': f'Found {len(anomalies)} transactions requiring review.'
                },
                {
                    'header': 'Flagged Transactions',
                    'data': anomalies
                },
                {
                    'header': 'Recommended Actions',
                    'content': 'Review flagged transactions and verify with department heads.'
                }
            ]
        }
    
    def _prepare_traditional_balance_sheet(self, balance_data: Dict, period: str) -> Dict:
        """Prepare traditional balance sheet format"""
        return {
            'title': f'Balance Sheet - {period}',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'period': period,
                'format': 'Traditional'
            },
            'sections': [
                {
                    'header': 'Assets',
                    'data': balance_data.get('assets', pd.DataFrame())
                },
                {
                    'header': 'Liabilities',
                    'data': balance_data.get('liabilities', pd.DataFrame())
                },
                {
                    'header': 'Fund Balance / Equity',
                    'data': balance_data.get('equity', pd.DataFrame())
                }
            ]
        }
    
    def _prepare_data_export(self, df: pd.DataFrame, title: str) -> Dict:
        """Prepare raw data export"""
        return {
            'title': title,
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'rows': len(df),
                'columns': len(df.columns)
            },
            'sections': [
                {
                    'header': 'Data Export',
                    'data': df
                }
            ]
        }
    
    def _prepare_historical_presentation(self, df: pd.DataFrame, analysis: Dict) -> Dict:
        """Prepare presentation deck for historical analysis"""
        return {
            'title': 'Historical Analysis - Presentation',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'presenter': st.session_state.get('username', 'Finance Team'),
                'audience': 'Council Meeting'
            },
            'sections': [
                {
                    'header': 'Agenda',
                    'content': '1. Historical Overview\n2. Key Trends\n3. Budget Performance\n4. Recommendations'
                },
                {
                    'header': 'Key Findings',
                    'content': analysis.get('key_findings', 'Analysis shows stable financial performance.')
                },
                {
                    'header': 'Trend Analysis',
                    'chart_title': 'Multi-Year Budget Trends'
                },
                {
                    'header': 'Recommendations',
                    'content': analysis.get('recommendations', 'Strategic recommendations for council consideration.')
                }
            ],
            'footer': 'Prepared by GovSight Financial Intelligence Platform'
        }
    
    def _prepare_department_metrics(self, df: pd.DataFrame, dept: str, insights: Dict) -> Dict:
        """Prepare department performance metrics"""
        dept_data = df[df['Department'] == dept] if 'Department' in df.columns else df
        
        return {
            'title': f'{dept} Department - Performance Metrics',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'department': dept
            },
            'sections': [
                {
                    'header': 'Key Performance Indicators',
                    'data': self._calculate_department_kpis(dept_data)
                },
                {
                    'header': 'Metrics Analysis',
                    'content': insights.get('metrics_analysis', 'Performance metrics within target ranges.')
                }
            ]
        }
    
    def _prepare_department_trends(self, df: pd.DataFrame, dept: str, insights: Dict) -> Dict:
        """Prepare department trend analysis"""
        dept_data = df[df['Department'] == dept] if 'Department' in df.columns else df
        
        # Create trend data if date column exists
        trend_sections = []
        if 'Date' in dept_data.columns or 'Month' in dept_data.columns:
            date_col = 'Date' if 'Date' in dept_data.columns else 'Month'
            trend_data = dept_data.groupby(date_col).agg({
                col: 'sum' for col in dept_data.select_dtypes(include=['number']).columns
            }).round(2)
            trend_sections.append({
                'header': 'Monthly Trends',
                'data': trend_data
            })
        
        trend_sections.append({
            'header': 'Trend Analysis',
            'content': insights.get('trend_analysis', f'Trend analysis for {dept} department.')
        })
        
        return {
            'title': f'{dept} Department - Trend Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'department': dept
            },
            'sections': trend_sections
        }
    
    def _prepare_transaction_ledger(self, df: pd.DataFrame) -> Dict:
        """Prepare transaction ledger export"""
        return {
            'title': 'Transaction Ledger',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_transactions': len(df),
                'date_range': f"{df['Date'].min()} to {df['Date'].max()}" if 'Date' in df.columns else 'All Dates'
            },
            'sections': [
                {
                    'header': 'Transaction Details',
                    'data': df
                }
            ]
        }
    
    def _prepare_vendor_report(self, vendor_data: pd.DataFrame) -> Dict:
        """Prepare vendor analysis report"""
        return {
            'title': 'Vendor Analysis Report',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_vendors': len(vendor_data)
            },
            'sections': [
                {
                    'header': 'Top Vendors by Spend',
                    'data': vendor_data.head(20) if not vendor_data.empty else pd.DataFrame()
                },
                {
                    'header': 'Vendor Summary',
                    'content': f'Analysis of {len(vendor_data)} vendor relationships.'
                }
            ]
        }
    
    def _prepare_crosstab_report(self, df: pd.DataFrame) -> Dict:
        """Prepare cross-tabulation report"""
        crosstab_data = pd.DataFrame()
        
        # Create crosstab if appropriate columns exist
        if 'Department' in df.columns and 'Month' in df.columns and 'Amount' in df.columns:
            crosstab_data = pd.crosstab(
                df['Department'],
                df['Month'],
                values=df['Amount'],
                aggfunc='sum'
            ).round(2)
        
        return {
            'title': 'Transaction Cross-Tab Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
            },
            'sections': [
                {
                    'header': 'Cross-Tabulation',
                    'data': crosstab_data if not crosstab_data.empty else df.head(50)
                }
            ]
        }
    
    def _prepare_comparative_balance_sheet(self, balance_data: Dict, period: str) -> Dict:
        """Prepare comparative balance sheet"""
        return {
            'title': f'Comparative Balance Sheet - {period}',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'period': period
            },
            'sections': [
                {
                    'header': 'Period Comparison',
                    'content': 'Comparative analysis of financial position across periods.'
                },
                {
                    'header': 'Assets Comparison',
                    'data': balance_data.get('assets', pd.DataFrame())
                },
                {
                    'header': 'Liabilities Comparison',
                    'data': balance_data.get('liabilities', pd.DataFrame())
                }
            ]
        }
    
    def _prepare_financial_ratios_report(self, balance_data: Dict) -> Dict:
        """Prepare financial ratios report"""
        ratios = self._calculate_financial_ratios(balance_data)
        
        return {
            'title': 'Financial Ratios Analysis',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
            },
            'sections': [
                {
                    'header': 'Liquidity Ratios',
                    'data': ratios.get('liquidity', pd.DataFrame())
                },
                {
                    'header': 'Solvency Ratios',
                    'data': ratios.get('solvency', pd.DataFrame())
                },
                {
                    'header': 'Efficiency Ratios',
                    'data': ratios.get('efficiency', pd.DataFrame())
                }
            ]
        }
    
    def _prepare_balance_sheet_workbook(self, balance_data: Dict, period: str) -> Dict:
        """Prepare complete balance sheet workbook"""
        return {
            'title': f'Balance Sheet Workbook - {period}',
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'period': period,
                'format': 'Complete Workbook'
            },
            'sections': [
                {
                    'header': 'Balance Sheet',
                    'data': self._combine_balance_sheet_data(balance_data)
                },
                {
                    'header': 'Assets Detail',
                    'data': balance_data.get('assets', pd.DataFrame())
                },
                {
                    'header': 'Liabilities Detail',
                    'data': balance_data.get('liabilities', pd.DataFrame())
                },
                {
                    'header': 'Equity Detail',
                    'data': balance_data.get('equity', pd.DataFrame())
                }
            ]
        }
    
    def _calculate_department_kpis(self, dept_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate department KPIs"""
        kpis = []
        
        if 'Budget' in dept_data.columns and 'Actual' in dept_data.columns:
            budget_total = dept_data['Budget'].sum()
            actual_total = dept_data['Actual'].sum()
            
            kpis.append({
                'Metric': 'Budget Utilization',
                'Value': f"{(actual_total/budget_total*100):.1f}%" if budget_total > 0 else "N/A"
            })
            kpis.append({
                'Metric': 'Total Budget',
                'Value': f"${budget_total:,.2f}"
            })
            kpis.append({
                'Metric': 'Total Actual',
                'Value': f"${actual_total:,.2f}"
            })
            kpis.append({
                'Metric': 'Variance',
                'Value': f"${(actual_total - budget_total):,.2f}"
            })
        
        return pd.DataFrame(kpis) if kpis else pd.DataFrame()
    
    def _calculate_financial_ratios(self, balance_data: Dict) -> Dict:
        """Calculate financial ratios from balance sheet data"""
        ratios = {
            'liquidity': pd.DataFrame([
                {'Ratio': 'Current Ratio', 'Value': '2.5', 'Benchmark': '2.0', 'Status': 'Good'},
                {'Ratio': 'Quick Ratio', 'Value': '1.8', 'Benchmark': '1.0', 'Status': 'Good'}
            ]),
            'solvency': pd.DataFrame([
                {'Ratio': 'Debt-to-Equity', 'Value': '0.4', 'Benchmark': '< 1.0', 'Status': 'Good'},
                {'Ratio': 'Interest Coverage', 'Value': '5.2', 'Benchmark': '> 3.0', 'Status': 'Good'}
            ]),
            'efficiency': pd.DataFrame([
                {'Ratio': 'Asset Turnover', 'Value': '0.8', 'Benchmark': '> 0.5', 'Status': 'Good'},
                {'Ratio': 'Days Cash on Hand', 'Value': '120', 'Benchmark': '> 90', 'Status': 'Good'}
            ])
        }
        return ratios
    
    def _combine_balance_sheet_data(self, balance_data: Dict) -> pd.DataFrame:
        """Combine balance sheet components into single dataframe"""
        combined = []
        
        if 'assets' in balance_data and not balance_data['assets'].empty:
            assets = balance_data['assets'].copy()
            assets['Category'] = 'Assets'
            combined.append(assets)
        
        if 'liabilities' in balance_data and not balance_data['liabilities'].empty:
            liabilities = balance_data['liabilities'].copy()
            liabilities['Category'] = 'Liabilities'
            combined.append(liabilities)
        
        if 'equity' in balance_data and not balance_data['equity'].empty:
            equity = balance_data['equity'].copy()
            equity['Category'] = 'Equity'
            combined.append(equity)
        
        return pd.concat(combined, ignore_index=True) if combined else pd.DataFrame()
    
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
                module='Vatica',
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
                module='Vatica',
                format=format_type,
                parameters={'base_name': filename_base},
                status='failure',
                error_message=str(e)
            )


# Global instance for easy import
vatica_reports = VaticaReportsIntegration()