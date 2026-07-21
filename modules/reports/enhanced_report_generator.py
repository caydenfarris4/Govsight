"""
Enhanced Report Generator with Comprehensive Plotly Visualizations

ARCHITECTURAL DECISION: Centralized reporting with intelligent chart selection
WHY: 
- Consistent visual style across all modules
- Automatic chart type selection based on data characteristics
- Executive summary generation with relevant visualizations
- Professional PDF output with embedded charts
- Modular design allows easy extension for new chart types

VISUALIZATION STRATEGY:
- Financial data: Bar charts, line trends, pie charts for allocations
- Time series: Line charts with trend indicators and forecasting
- Comparative analysis: Grouped bar charts, scatter plots
- Distribution analysis: Histograms, box plots
- Geographic data: Choropleth maps when applicable
- Budget scenarios: Waterfall charts, stacked bars
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
# PDF generation capability (optional)
try:
    from fpdf2 import FPDF
    PDF_AVAILABLE = True
except ImportError:
    try:
        from fpdf import FPDF
        PDF_AVAILABLE = True
    except ImportError:
        # PDF functionality will be disabled if fpdf2 is not available
        class FPDF:
            def __init__(self, *args, **kwargs):
                raise ImportError("PDF functionality requires fpdf2 package")
        PDF_AVAILABLE = False
import tempfile
import base64
from io import BytesIO
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Import AI functions for intelligent report generation - using lazy loading to avoid circular imports
def get_ai_function():
    """Lazy load AI function to avoid circular imports"""
    try:
        from modules.ai_hub.ai_hub import ask_ai
        return ask_ai
    except ImportError:
        # Fallback if AI module is not available
        def mock_ai(prompt, context=""):
            return "AI analysis not available"
        return mock_ai

class EnhancedReportGenerator:
    """
    Comprehensive report generator with intelligent chart selection and executive summaries
    
    WHY CLASS-BASED DESIGN: Maintains state for consistent styling and configuration
    across multiple chart generation calls within a single report
    """
    
    def __init__(self, org_name: str = "GovSight", theme_color: str = "#003080"):
        """
        Initialize report generator with organization branding
        
        Args:
            org_name: Organization name for report headers
            theme_color: Primary color for charts and branding
        """
        self.org_name = org_name
        self.theme_color = theme_color
        self.chart_config = {
            'font_family': 'Arial',
            'font_size': 12,
            'color_palette': [
                '#003080', '#0056CC', '#4A90E2', '#7BB3F0', 
                '#B8D4F0', '#E8F4FD', '#FFD700', '#FFA500',
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'
            ],
            'background_color': '#FFFFFF',
            'grid_color': '#E5E5E5'
        }
        
    def generate_comprehensive_report(self, data: pd.DataFrame, report_type: str, 
                                    title: str, additional_data: Dict = None) -> Dict[str, Any]:
        """
        Generate a comprehensive report with executive summary, relevant charts, and detailed analysis
        
        Args:
            data: Primary dataset for the report
            report_type: Type of report (scenario, department, historical, etc.)
            title: Report title
            additional_data: Additional datasets or configuration
            
        Returns:
            Dictionary containing charts, summary, and PDF bytes
        """
        # WHY COMPREHENSIVE APPROACH: Municipal stakeholders need complete analysis
        # with both high-level summaries and detailed supporting data
        
        try:
            # Generate executive summary using AI
            executive_summary = self._generate_executive_summary(data, report_type, additional_data)
            
            # Select and generate relevant charts based on data characteristics
            charts = self._generate_relevant_charts(data, report_type, additional_data)
            
            # Create key metrics summary
            key_metrics = self._calculate_key_metrics(data, report_type)
            
            # Generate PDF with embedded charts
            pdf_bytes = self._create_pdf_report(title, executive_summary, charts, key_metrics, data)
            
            return {
                'executive_summary': executive_summary,
                'charts': charts,
                'key_metrics': key_metrics,
                'pdf_bytes': pdf_bytes,
                'chart_count': len(charts)
            }
            
        except Exception as e:
            st.error(f"Error generating comprehensive report: {str(e)}")
            return {
                'executive_summary': f"Report generation error: {str(e)}",
                'charts': [],
                'key_metrics': {},
                'pdf_bytes': b"",
                'chart_count': 0
            }

    def _generate_executive_summary(self, data: pd.DataFrame, report_type: str, 
                                  additional_data: Dict = None) -> str:
        """Generate AI-powered executive summary based on data analysis"""
        try:
            # Build context for AI analysis
            data_summary = self._create_data_summary_for_ai(data)
            
            # Create report-specific prompt
            if report_type == "scenario":
                prompt = f"""
                Analyze this budget scenario data and provide an executive summary for municipal leadership:
                
                {data_summary}
                
                Focus on:
                - Key financial impacts and budget implications
                - Risk factors and opportunities
                - Recommendations for decision-makers
                - Compliance and regulatory considerations
                
                Keep the summary concise but comprehensive (2-3 paragraphs).
                """
            elif report_type == "department":
                prompt = f"""
                Analyze this department financial data and provide an executive summary:
                
                {data_summary}
                
                Focus on:
                - Department performance against budget
                - Spending patterns and trends
                - Areas of concern or exceptional performance
                - Resource allocation recommendations
                
                Keep the summary concise but actionable (2-3 paragraphs).
                """
            elif report_type == "historical":
                prompt = f"""
                Analyze this historical financial data and provide an executive summary:
                
                {data_summary}
                
                Focus on:
                - Long-term trends and patterns
                - Year-over-year changes and their significance
                - Forecasting implications
                - Strategic planning recommendations
                
                Keep the summary insightful and forward-looking (2-3 paragraphs).
                """
            else:
                prompt = f"""
                Analyze this financial data and provide an executive summary:
                
                {data_summary}
                
                Provide insights on financial performance, trends, and recommendations.
                Keep the summary concise and actionable (2-3 paragraphs).
                """
            
            # Generate AI summary with regulatory context using lazy loading
            ask_ai_func = get_ai_function()
            summary = ask_ai_func(prompt, data, ["budget_law", "gasb"], max_tokens=500)
            return summary
            
        except Exception as e:
            return f"Executive summary generation error: {str(e)}"

    def _generate_relevant_charts(self, data: pd.DataFrame, report_type: str, 
                                additional_data: Dict = None) -> List[Dict[str, Any]]:
        """
        Generate relevant charts based on data characteristics and report type
        
        WHY INTELLIGENT CHART SELECTION: Different data types require different 
        visualization approaches for maximum insight and clarity
        """
        charts = []
        
        try:
            # Detect data characteristics
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            date_cols = data.select_dtypes(include=['datetime64']).columns.tolist()
            categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
            
            # Generate charts based on report type and data structure
            if report_type == "scenario":
                charts.extend(self._create_scenario_charts(data, numeric_cols, categorical_cols))
            elif report_type == "department":
                charts.extend(self._create_department_charts(data, numeric_cols, categorical_cols))
            elif report_type == "historical":
                charts.extend(self._create_historical_charts(data, numeric_cols, date_cols, categorical_cols))
            elif report_type == "balance_sheet":
                charts.extend(self._create_balance_sheet_charts(data, numeric_cols, categorical_cols))
            elif report_type == "transaction":
                charts.extend(self._create_transaction_charts(data, numeric_cols, date_cols, categorical_cols))
            
            # Add general financial overview charts
            charts.extend(self._create_general_financial_charts(data, numeric_cols, categorical_cols))
            
            return charts
            
        except Exception as e:
            st.error(f"Error generating charts: {str(e)}")
            return []

    def _create_scenario_charts(self, data: pd.DataFrame, numeric_cols: List[str], 
                              categorical_cols: List[str]) -> List[Dict[str, Any]]:
        """Create charts specific to budget scenario analysis"""
        charts = []
        
        try:
            # Funding source allocation pie chart
            if 'FundingSource' in categorical_cols and any('amount' in col.lower() for col in numeric_cols):
                amount_col = next((col for col in numeric_cols if 'amount' in col.lower()), numeric_cols[0])
                
                funding_summary = data.groupby('FundingSource')[amount_col].sum().reset_index()
                
                fig = px.pie(funding_summary, 
                           values=amount_col, 
                           names='FundingSource',
                           title="Funding Source Allocation",
                           color_discrete_sequence=self.chart_config['color_palette'])
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color']
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Funding Source Allocation",
                    'description': "Distribution of funding across different sources",
                    'chart_type': 'pie'
                })
            
            # Department budget comparison
            if 'Department' in categorical_cols and len(numeric_cols) >= 2:
                dept_summary = data.groupby('Department')[numeric_cols[:2]].sum().reset_index()
                
                fig = px.bar(dept_summary, 
                           x='Department', 
                           y=numeric_cols[:2],
                           title="Department Budget Comparison",
                           barmode='group',
                           color_discrete_sequence=self.chart_config['color_palette'])
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color'],
                    xaxis=dict(tickangle=45)
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Department Budget Comparison",
                    'description': "Comparison of budget allocations across departments",
                    'chart_type': 'bar'
                })
            
            # Scenario impact waterfall chart (if applicable)
            if len(numeric_cols) >= 3:
                fig = go.Figure(go.Waterfall(
                    name="Budget Impact",
                    orientation="v",
                    measure=["relative", "relative", "relative", "total"],
                    x=["Base Budget", "New Project", "Savings", "Final Budget"],
                    textposition="outside",
                    text=[f"${val:,.0f}" for val in data[numeric_cols[:4]].sum().values],
                    y=data[numeric_cols[:4]].sum().values,
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                ))
                
                fig.update_layout(
                    title="Budget Impact Analysis",
                    showlegend=False,
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color']
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Budget Impact Analysis",
                    'description': "Waterfall analysis showing budget changes from scenario",
                    'chart_type': 'waterfall'
                })
                
        except Exception as e:
            st.warning(f"Error creating scenario charts: {str(e)}")
            
        return charts

    def _create_department_charts(self, data: pd.DataFrame, numeric_cols: List[str], 
                                categorical_cols: List[str]) -> List[Dict[str, Any]]:
        """Create charts specific to department analysis"""
        charts = []
        
        try:
            # Budget vs Actual spending
            if 'Budget' in numeric_cols and 'Actual' in numeric_cols:
                fig = px.scatter(data, 
                               x='Budget', 
                               y='Actual',
                               title="Budget vs Actual Spending",
                               hover_data=categorical_cols[:2] if categorical_cols else None)
                
                # Add diagonal line for perfect budget execution
                max_val = max(data['Budget'].max(), data['Actual'].max())
                fig.add_shape(
                    type="line",
                    x0=0, y0=0, x1=max_val, y1=max_val,
                    line=dict(color="red", width=2, dash="dash"),
                )
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color']
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Budget vs Actual Analysis",
                    'description': "Comparison of budgeted vs actual spending with perfect execution line",
                    'chart_type': 'scatter'
                })
            
            # Spending efficiency by category
            if 'PercentUsed' in numeric_cols and categorical_cols:
                category_col = categorical_cols[0]
                efficiency_data = data.groupby(category_col)['PercentUsed'].mean().reset_index()
                
                fig = px.bar(efficiency_data, 
                           x=category_col, 
                           y='PercentUsed',
                           title="Budget Efficiency by Category",
                           color='PercentUsed',
                           color_continuous_scale='RdYlGn_r')
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color'],
                    xaxis=dict(tickangle=45)
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Budget Efficiency Analysis",
                    'description': "Average budget utilization rates by category",
                    'chart_type': 'bar'
                })
                
        except Exception as e:
            st.warning(f"Error creating department charts: {str(e)}")
            
        return charts

    def _create_historical_charts(self, data: pd.DataFrame, numeric_cols: List[str], 
                                date_cols: List[str], categorical_cols: List[str]) -> List[Dict[str, Any]]:
        """Create charts specific to historical analysis"""
        charts = []
        
        try:
            # Time series trend analysis
            if date_cols and numeric_cols:
                date_col = date_cols[0]
                value_col = numeric_cols[0]
                
                # Ensure date column is datetime
                if data[date_col].dtype != 'datetime64[ns]':
                    data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
                
                # Group by date and sum values
                time_series = data.groupby(date_col)[value_col].sum().reset_index()
                
                fig = px.line(time_series, 
                            x=date_col, 
                            y=value_col,
                            title="Historical Trend Analysis",
                            markers=True)
                
                # Add trendline
                fig.add_trace(go.Scatter(
                    x=time_series[date_col],
                    y=time_series[value_col].rolling(window=3, center=True).mean(),
                    mode='lines',
                    name='Trend Line',
                    line=dict(color='red', width=2, dash='dash')
                ))
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color']
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Historical Trend Analysis",
                    'description': "Time series analysis with trend line",
                    'chart_type': 'line'
                })
            
            # Year-over-year comparison
            if 'FiscalYear' in data.columns and len(numeric_cols) >= 1:
                yearly_summary = data.groupby('FiscalYear')[numeric_cols[0]].sum().reset_index()
                yearly_summary['YoY_Change'] = yearly_summary[numeric_cols[0]].pct_change() * 100
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Add bars for absolute values
                fig.add_trace(
                    go.Bar(x=yearly_summary['FiscalYear'], 
                          y=yearly_summary[numeric_cols[0]], 
                          name="Total Amount",
                          marker_color=self.chart_config['color_palette'][0]),
                    secondary_y=False,
                )
                
                # Add line for YoY change
                fig.add_trace(
                    go.Scatter(x=yearly_summary['FiscalYear'], 
                             y=yearly_summary['YoY_Change'], 
                             name="YoY Change %",
                             line=dict(color=self.chart_config['color_palette'][2], width=3),
                             mode='lines+markers'),
                    secondary_y=True,
                )
                
                fig.update_layout(title="Year-over-Year Analysis")
                fig.update_yaxes(title_text="Amount ($)", secondary_y=False)
                fig.update_yaxes(title_text="YoY Change (%)", secondary_y=True)
                
                charts.append({
                    'figure': fig,
                    'title': "Year-over-Year Analysis",
                    'description': "Annual totals with year-over-year percentage changes",
                    'chart_type': 'combo'
                })
                
        except Exception as e:
            st.warning(f"Error creating historical charts: {str(e)}")
            
        return charts

    def _create_balance_sheet_charts(self, data: pd.DataFrame, numeric_cols: List[str], 
                                   categorical_cols: List[str]) -> List[Dict[str, Any]]:
        """Create charts specific to balance sheet analysis"""
        charts = []
        
        try:
            # Assets vs Liabilities
            if 'AccountType' in categorical_cols and 'Balance' in numeric_cols:
                balance_summary = data.groupby('AccountType')['Balance'].sum().reset_index()
                
                fig = px.bar(balance_summary, 
                           x='AccountType', 
                           y='Balance',
                           title="Balance Sheet Overview",
                           color='Balance',
                           color_continuous_scale='RdYlBu')
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color']
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Balance Sheet Overview",
                    'description': "Summary of account types and balances",
                    'chart_type': 'bar'
                })
                
        except Exception as e:
            st.warning(f"Error creating balance sheet charts: {str(e)}")
            
        return charts

    def _create_transaction_charts(self, data: pd.DataFrame, numeric_cols: List[str], 
                                 date_cols: List[str], categorical_cols: List[str]) -> List[Dict[str, Any]]:
        """Create charts specific to transaction analysis"""
        charts = []
        
        try:
            # Transaction volume over time
            if date_cols and 'Amount' in numeric_cols:
                date_col = date_cols[0]
                
                # Ensure date column is datetime
                if data[date_col].dtype != 'datetime64[ns]':
                    data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
                
                # Daily transaction volume
                daily_volume = data.groupby(data[date_col].dt.date)['Amount'].sum().reset_index()
                daily_volume.columns = ['Date', 'Total_Amount']
                
                fig = px.area(daily_volume, 
                            x='Date', 
                            y='Total_Amount',
                            title="Daily Transaction Volume")
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color']
                )
                
                charts.append({
                    'figure': fig,
                    'title': "Transaction Volume Analysis",
                    'description': "Daily transaction volumes over time",
                    'chart_type': 'area'
                })
                
        except Exception as e:
            st.warning(f"Error creating transaction charts: {str(e)}")
            
        return charts

    def _create_general_financial_charts(self, data: pd.DataFrame, numeric_cols: List[str], 
                                       categorical_cols: List[str]) -> List[Dict[str, Any]]:
        """Create general financial overview charts applicable to any dataset"""
        charts = []
        
        try:
            # Distribution analysis for primary numeric column
            if numeric_cols:
                primary_col = numeric_cols[0]
                
                fig = px.histogram(data, 
                                 x=primary_col,
                                 title=f"Distribution of {primary_col}",
                                 nbins=20,
                                 color_discrete_sequence=[self.chart_config['color_palette'][0]])
                
                fig.update_layout(
                    font=dict(family=self.chart_config['font_family'], size=self.chart_config['font_size']),
                    plot_bgcolor=self.chart_config['background_color']
                )
                
                charts.append({
                    'figure': fig,
                    'title': f"{primary_col} Distribution",
                    'description': f"Distribution analysis of {primary_col} values",
                    'chart_type': 'histogram'
                })
            
            # Summary statistics table as a chart
            if numeric_cols:
                stats_df = data[numeric_cols].describe().round(2)
                
                fig = go.Figure(data=[go.Table(
                    header=dict(values=['Statistic'] + list(stats_df.columns),
                               fill_color=self.chart_config['color_palette'][0],
                               font=dict(color='white')),
                    cells=dict(values=[stats_df.index] + [stats_df[col] for col in stats_df.columns],
                              fill_color='lightgrey'))
                ])
                
                fig.update_layout(title="Summary Statistics")
                
                charts.append({
                    'figure': fig,
                    'title': "Summary Statistics",
                    'description': "Descriptive statistics for numeric columns",
                    'chart_type': 'table'
                })
                
        except Exception as e:
            st.warning(f"Error creating general charts: {str(e)}")
            
        return charts

    def _calculate_key_metrics(self, data: pd.DataFrame, report_type: str) -> Dict[str, Any]:
        """Calculate key performance metrics based on report type"""
        metrics = {}
        
        try:
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            
            # General metrics
            metrics['total_records'] = len(data)
            
            if numeric_cols:
                primary_col = numeric_cols[0]
                metrics['total_amount'] = data[primary_col].sum()
                metrics['average_amount'] = data[primary_col].mean()
                metrics['median_amount'] = data[primary_col].median()
                
                # Report-specific metrics
                if report_type == "scenario":
                    if 'Budget' in numeric_cols and 'Actual' in numeric_cols:
                        metrics['budget_variance'] = data['Actual'].sum() - data['Budget'].sum()
                        metrics['budget_variance_percent'] = (metrics['budget_variance'] / data['Budget'].sum()) * 100
                
                elif report_type == "department":
                    if 'PercentUsed' in numeric_cols:
                        metrics['avg_budget_utilization'] = data['PercentUsed'].mean()
                        metrics['departments_over_budget'] = len(data[data['PercentUsed'] > 100])
                
                elif report_type == "historical":
                    if 'FiscalYear' in data.columns:
                        metrics['years_analyzed'] = data['FiscalYear'].nunique()
                        latest_year = data['FiscalYear'].max()
                        previous_year = latest_year - 1
                        
                        if previous_year in data['FiscalYear'].values:
                            current_total = data[data['FiscalYear'] == latest_year][primary_col].sum()
                            previous_total = data[data['FiscalYear'] == previous_year][primary_col].sum()
                            metrics['yoy_growth'] = ((current_total - previous_total) / previous_total) * 100
                            
        except Exception as e:
            metrics['calculation_error'] = str(e)
            
        return metrics

    def _create_data_summary_for_ai(self, data: pd.DataFrame) -> str:
        """Create a concise data summary for AI analysis"""
        try:
            summary = f"Dataset contains {len(data)} records with {len(data.columns)} columns.\n\n"
            
            # Numeric column summaries
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                summary += "Numeric columns summary:\n"
                for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
                    summary += f"- {col}: Total={data[col].sum():,.2f}, Mean={data[col].mean():.2f}, Range={data[col].min():.2f} to {data[col].max():.2f}\n"
                summary += "\n"
            
            # Categorical column summaries
            categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
            if categorical_cols:
                summary += "Categorical columns:\n"
                for col in categorical_cols[:3]:  # Limit to first 3 categorical columns
                    unique_count = data[col].nunique()
                    summary += f"- {col}: {unique_count} unique values\n"
                    if unique_count <= 10:
                        top_values = data[col].value_counts().head(3)
                        summary += f"  Top values: {', '.join([f'{val} ({count})' for val, count in top_values.items()])}\n"
                summary += "\n"
            
            return summary
            
        except Exception as e:
            return f"Error creating data summary: {str(e)}"

    def _create_pdf_report(self, title: str, executive_summary: str, charts: List[Dict], 
                          key_metrics: Dict, data: pd.DataFrame) -> bytes:
        """
        Create comprehensive PDF report with embedded charts
        
        WHY PDF OUTPUT: Municipal reports need to be shared with stakeholders
        who may not have access to the web application
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # Title page
                pdf.add_page()
                pdf.set_font("Arial", "B", 20)
                pdf.cell(0, 20, title, ln=True, align="C")
                pdf.set_font("Arial", "I", 12)
                pdf.cell(0, 10, f"{self.org_name}", ln=True, align="C")
                pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
                
                # Executive summary page
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 15, "Executive Summary", ln=True)
                pdf.set_font("Arial", "", 11)
                
                # Split summary into paragraphs and add to PDF
                for paragraph in executive_summary.split('\n\n'):
                    if paragraph.strip():
                        pdf.multi_cell(0, 6, paragraph.strip())
                        pdf.ln(3)
                
                # Key metrics page
                if key_metrics:
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 15, "Key Metrics", ln=True)
                    pdf.set_font("Arial", "", 11)
                    
                    for metric, value in key_metrics.items():
                        if isinstance(value, (int, float)):
                            if 'percent' in metric.lower() or 'rate' in metric.lower():
                                pdf.cell(0, 8, f"{metric.replace('_', ' ').title()}: {value:.2f}%", ln=True)
                            elif 'amount' in metric.lower() or 'total' in metric.lower():
                                pdf.cell(0, 8, f"{metric.replace('_', ' ').title()}: ${value:,.2f}", ln=True)
                            else:
                                pdf.cell(0, 8, f"{metric.replace('_', ' ').title()}: {value:,.0f}", ln=True)
                        else:
                            pdf.cell(0, 8, f"{metric.replace('_', ' ').title()}: {str(value)}", ln=True)
                
                # Charts pages
                for i, chart_info in enumerate(charts):
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 15, chart_info['title'], ln=True)
                    
                    if 'description' in chart_info:
                        pdf.set_font("Arial", "", 10)
                        pdf.multi_cell(0, 5, chart_info['description'])
                        pdf.ln(5)
                    
                    # Save chart as image and embed
                    try:
                        chart_path = os.path.join(temp_dir, f"chart_{i}.png")
                        chart_info['figure'].write_image(chart_path, width=800, height=500)
                        pdf.image(chart_path, x=10, w=190)
                    except Exception as e:
                        pdf.set_font("Arial", "I", 10)
                        pdf.cell(0, 10, f"Chart could not be embedded: {str(e)}", ln=True)
                
                # Data appendix (first 50 rows)
                if not data.empty:
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 15, "Data Appendix", ln=True)
                    pdf.set_font("Arial", "", 8)
                    
                    # Add table headers
                    col_width = 180 / min(len(data.columns), 6)  # Limit to 6 columns
                    for col in data.columns[:6]:
                        pdf.cell(col_width, 8, str(col)[:15], border=1)
                    pdf.ln()
                    
                    # Add data rows (limit to 50)
                    for _, row in data.head(50).iterrows():
                        for item in row[:6]:
                            if isinstance(item, (int, float)):
                                cell_text = f"{item:,.1f}" if abs(item) > 1000 else f"{item:.2f}"
                            else:
                                cell_text = str(item)[:15]
                            pdf.cell(col_width, 6, cell_text, border=1)
                        pdf.ln()
                
                # Generate PDF bytes with UTF-8 encoding (fixed from latin-1)
                pdf_output = pdf.output(dest='S').encode('utf-8', errors='replace')
                return pdf_output
                
        except Exception as e:
            st.error(f"Error creating PDF: {str(e)}")
            return b""

# Convenience function for easy import
def generate_enhanced_report(data: pd.DataFrame, report_type: str, title: str, 
                           org_name: str = "GovSight", additional_data: Dict = None) -> Dict[str, Any]:
    """
    Convenience function to generate enhanced reports
    
    Args:
        data: Primary dataset
        report_type: Type of report (scenario, department, historical, etc.)
        title: Report title
        org_name: Organization name
        additional_data: Additional datasets or configuration
        
    Returns:
        Complete report with charts, summary, and PDF
    """
    generator = EnhancedReportGenerator(org_name)
    return generator.generate_comprehensive_report(data, report_type, title, additional_data)