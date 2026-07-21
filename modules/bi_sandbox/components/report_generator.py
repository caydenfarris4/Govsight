"""
Report Generation Module for BI Sandbox

This module provides PDF report generation, data export capabilities,
and automated report creation functionality.
"""

import streamlit as st
import pandas as pd
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
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from io import BytesIO
import base64

class PDFReportGenerator:
    """Generate professional PDF reports from dashboard data"""
    
    def __init__(self):
        self.pdf = None
        self.temp_dir = None
    
    def create_report(self, title: str, org_name: str, charts_data: List[Dict], summary_data: Dict = None) -> bytes:
        """Create comprehensive PDF report"""
        # Initialize PDF
        self.pdf = FPDF()
        self.pdf.add_page()
        
        # Report header
        self._add_header(title, org_name)
        
        # Executive summary
        if summary_data:
            self._add_summary_section(summary_data)
        
        # Charts section
        self._add_charts_section(charts_data)
        
        # Generate PDF data
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            self.pdf.output(tmp_file.name)
            with open(tmp_file.name, 'rb') as f:
                pdf_data = f.read()
            os.unlink(tmp_file.name)
        
        return pdf_data
    
    def _add_header(self, title: str, org_name: str):
        """Add report header with title and organization"""
        self.pdf.set_font("Arial", "B", 20)
        self.pdf.cell(190, 15, title, ln=True, align="C")
        
        self.pdf.set_font("Arial", "B", 14)
        self.pdf.cell(190, 10, org_name, ln=True, align="C")
        
        self.pdf.set_font("Arial", "I", 10)
        self.pdf.cell(190, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
        self.pdf.ln(10)
    
    def _add_summary_section(self, summary_data: Dict):
        """Add executive summary section"""
        self.pdf.set_font("Arial", "B", 16)
        self.pdf.cell(190, 10, "Executive Summary", ln=True)
        self.pdf.ln(5)
        
        self.pdf.set_font("Arial", "", 10)
        
        # Key metrics
        if 'metrics' in summary_data:
            for metric, value in summary_data['metrics'].items():
                self.pdf.cell(190, 6, f"• {metric}: {value}", ln=True)
        
        # Insights
        if 'insights' in summary_data:
            self.pdf.ln(5)
            self.pdf.set_font("Arial", "B", 12)
            self.pdf.cell(190, 8, "Key Insights:", ln=True)
            self.pdf.set_font("Arial", "", 10)
            
            for insight in summary_data['insights']:
                self.pdf.multi_cell(190, 6, f"• {insight}")
        
        self.pdf.ln(10)
    
    def _add_charts_section(self, charts_data: List[Dict]):
        """Add charts and data tables section"""
        self.pdf.set_font("Arial", "B", 16)
        self.pdf.cell(190, 10, "Data Analysis", ln=True)
        self.pdf.ln(5)
        
        for i, chart_config in enumerate(charts_data):
            if i > 0:
                self.pdf.add_page()
            
            self._add_chart_page(chart_config, i + 1)
    
    def _add_chart_page(self, chart_config: Dict, chart_number: int):
        """Add individual chart page"""
        chart_title = chart_config.get('title', f'Chart {chart_number}')
        
        # Chart title
        self.pdf.set_font("Arial", "B", 14)
        self.pdf.cell(190, 10, f"Chart {chart_number}: {chart_title}", ln=True)
        
        # Chart description
        if 'description' in chart_config:
            self.pdf.set_font("Arial", "I", 10)
            self.pdf.multi_cell(190, 6, chart_config['description'])
            self.pdf.ln(3)
        
        # Chart parameters
        self.pdf.set_font("Arial", "B", 12)
        self.pdf.cell(190, 8, "Chart Configuration:", ln=True)
        self.pdf.set_font("Arial", "", 10)
        
        if 'dimensions' in chart_config:
            self.pdf.cell(190, 6, f"Dimensions: {', '.join(chart_config['dimensions'])}", ln=True)
        if 'value' in chart_config:
            self.pdf.cell(190, 6, f"Measure: {chart_config['value']}", ln=True)
        if 'chart_type' in chart_config:
            self.pdf.cell(190, 6, f"Chart Type: {chart_config['chart_type']}", ln=True)
        
        self.pdf.ln(5)
        
        # Data table
        if 'data' in chart_config:
            self._add_data_table(chart_config['data'])
    
    def _add_data_table(self, data: pd.DataFrame):
        """Add data table to PDF"""
        if data.empty:
            return
        
        self.pdf.set_font("Arial", "B", 10)
        self.pdf.cell(190, 8, "Data Summary:", ln=True)
        
        # Limit columns and rows for PDF readability
        max_cols = 6
        max_rows = 20
        
        display_data = data.head(max_rows)
        cols_to_show = data.columns[:max_cols]
        
        # Table headers
        self.pdf.set_font("Arial", "B", 8)
        col_width = 180 / len(cols_to_show)
        
        for col in cols_to_show:
            self.pdf.cell(col_width, 8, str(col)[:12], border=1, align='C')
        self.pdf.ln()
        
        # Table data
        self.pdf.set_font("Arial", "", 8)
        for _, row in display_data.iterrows():
            for col in cols_to_show:
                value = str(row[col])
                if len(value) > 12:
                    value = value[:12] + "..."
                self.pdf.cell(col_width, 6, value, border=1, align='C')
            self.pdf.ln()
        
        # Add note if data was truncated
        if len(data) > max_rows or len(data.columns) > max_cols:
            self.pdf.set_font("Arial", "I", 8)
            self.pdf.cell(190, 5, f"(Showing {min(max_rows, len(data))} rows of {len(data)}, {min(max_cols, len(data.columns))} columns of {len(data.columns)})", ln=True)

class DataExporter:
    """Export data in multiple formats"""
    
    @staticmethod
    def export_to_csv(data: pd.DataFrame, filename: str = None) -> bytes:
        """Export DataFrame to CSV"""
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        csv_buffer = BytesIO()
        data.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
    
    @staticmethod
    def export_to_excel(data: pd.DataFrame, sheet_name: str = "Data", filename: str = None) -> bytes:
        """Export DataFrame to Excel"""
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            data.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return excel_buffer.getvalue()
    
    @staticmethod
    def export_to_json(data: pd.DataFrame, filename: str = None) -> bytes:
        """Export DataFrame to JSON"""
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        json_str = data.to_json(orient='records', indent=2)
        return json_str.encode('utf-8')
    
    @staticmethod
    def create_download_link(data: bytes, filename: str, mime_type: str) -> str:
        """Create download link for exported data"""
        b64_data = base64.b64encode(data).decode()
        return f'<a href="data:{mime_type};base64,{b64_data}" download="{filename}">Download {filename}</a>'

class AutomatedReportGenerator:
    """Generate automated reports based on data patterns"""
    
    def __init__(self):
        self.pdf_generator = PDFReportGenerator()
        self.data_exporter = DataExporter()
    
    def generate_financial_summary_report(self, data: pd.DataFrame, org_name: str) -> Dict[str, Any]:
        """Generate automated financial summary report"""
        report_data = {
            'title': 'Financial Summary Report',
            'org_name': org_name,
            'summary': self._analyze_financial_data(data),
            'charts': self._create_financial_charts_config(data)
        }
        
        # Generate PDF
        pdf_data = self.pdf_generator.create_report(
            report_data['title'],
            org_name,
            report_data['charts'],
            report_data['summary']
        )
        
        return {
            'pdf_data': pdf_data,
            'summary': report_data['summary'],
            'filename': f"financial_report_{org_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        }
    
    def _analyze_financial_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze financial data for automated insights"""
        if data.empty:
            return {}
        
        summary = {
            'metrics': {},
            'insights': []
        }
        
        # Calculate key metrics
        numeric_columns = data.select_dtypes(include=['number']).columns
        
        for col in numeric_columns:
            if 'budget' in col.lower():
                total_budget = data[col].sum()
                summary['metrics'][f'Total {col}'] = f"${total_budget:,.2f}"
            
            elif 'actual' in col.lower():
                total_actual = data[col].sum()
                summary['metrics'][f'Total {col}'] = f"${total_actual:,.2f}"
        
        # Generate insights
        if len(numeric_columns) >= 2:
            # Budget vs Actual analysis
            budget_cols = [col for col in numeric_columns if 'budget' in col.lower()]
            actual_cols = [col for col in numeric_columns if 'actual' in col.lower()]
            
            if budget_cols and actual_cols:
                budget_total = data[budget_cols[0]].sum()
                actual_total = data[actual_cols[0]].sum()
                variance = actual_total - budget_total
                variance_pct = (variance / budget_total * 100) if budget_total != 0 else 0
                
                if variance_pct > 5:
                    summary['insights'].append(f"Spending exceeded budget by ${variance:,.2f} ({variance_pct:.1f}%)")
                elif variance_pct < -5:
                    summary['insights'].append(f"Spending was under budget by ${abs(variance):,.2f} ({abs(variance_pct):.1f}%)")
                else:
                    summary['insights'].append(f"Spending was close to budget (variance: {variance_pct:.1f}%)")
        
        # Department analysis
        if 'department' in [col.lower() for col in data.columns]:
            dept_col = next(col for col in data.columns if col.lower() == 'department')
            dept_count = data[dept_col].nunique()
            summary['metrics']['Departments Analyzed'] = str(dept_count)
            
            # Top spending department
            if numeric_columns:
                dept_spending = data.groupby(dept_col)[numeric_columns[0]].sum()
                top_dept = dept_spending.idxmax()
                top_amount = dept_spending.max()
                summary['insights'].append(f"{top_dept} has the highest spending at ${top_amount:,.2f}")
        
        return summary
    
    def _create_financial_charts_config(self, data: pd.DataFrame) -> List[Dict]:
        """Create chart configurations for financial data"""
        charts = []
        
        # Budget vs Actual chart
        budget_cols = [col for col in data.columns if 'budget' in col.lower()]
        actual_cols = [col for col in data.columns if 'actual' in col.lower()]
        dept_cols = [col for col in data.columns if 'department' in col.lower()]
        
        if budget_cols and actual_cols and dept_cols:
            charts.append({
                'title': 'Budget vs Actual by Department',
                'chart_type': 'Bar',
                'dimensions': [dept_cols[0]],
                'value': budget_cols[0],
                'description': 'Comparison of budgeted amounts versus actual spending by department',
                'data': data[[dept_cols[0], budget_cols[0], actual_cols[0]]]
            })
        
        # Variance analysis
        if budget_cols and actual_cols:
            variance_data = data.copy()
            variance_data['Variance'] = variance_data[actual_cols[0]] - variance_data[budget_cols[0]]
            
            charts.append({
                'title': 'Budget Variance Analysis',
                'chart_type': 'Waterfall',
                'dimensions': dept_cols[:1] if dept_cols else ['Category'],
                'value': 'Variance',
                'description': 'Analysis of budget variances showing over/under spending patterns',
                'data': variance_data
            })
        
        return charts
    
    def schedule_report_generation(self, report_config: Dict, schedule: str) -> Dict[str, Any]:
        """Schedule automated report generation"""
        # This would integrate with a task scheduler in a production environment
        return {
            'status': 'scheduled',
            'report_type': report_config.get('type', 'custom'),
            'schedule': schedule,
            'next_run': 'Not implemented in demo',
            'message': 'Report scheduling would be implemented in production environment'
        }