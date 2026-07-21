"""
Centralized Report Builder Service
Handles report generation in multiple formats: PDF, CSV, XLSX, JSON, HTML
"""

import io
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
import base64
from pathlib import Path
import streamlit as st

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False


class ReportEngine:
    """Unified report generation engine for all modules"""
    
    def __init__(self):
        self.styles = self._initialize_styles()
        self.export_formats = ['PDF', 'CSV', 'XLSX', 'JSON', 'HTML']
        
    def _initialize_styles(self):
        """Initialize report styles for consistent formatting"""
        return {
            'title': {'size': 18, 'bold': True, 'color': '#1e3a8a'},
            'subtitle': {'size': 14, 'bold': True, 'color': '#3b82f6'},
            'header': {'size': 12, 'bold': True, 'color': '#000000'},
            'body': {'size': 10, 'bold': False, 'color': '#374151'},
            'footer': {'size': 8, 'bold': False, 'color': '#6b7280'}
        }
        
    def generate_report(self, 
                       report_data: Dict[str, Any],
                       format_type: str = 'PDF',
                       include_charts: bool = True) -> bytes:
        """
        Generate a report in the specified format
        
        Args:
            report_data: Dictionary containing report sections, data, and metadata
            format_type: Export format (PDF, CSV, XLSX, JSON, HTML)
            include_charts: Whether to include charts in the report
            
        Returns:
            Bytes object containing the report in requested format
        """
        format_type = format_type.upper()
        
        if format_type == 'PDF':
            return self._generate_pdf(report_data, include_charts)
        elif format_type == 'CSV':
            return self._generate_csv(report_data)
        elif format_type == 'XLSX':
            return self._generate_xlsx(report_data, include_charts)
        elif format_type == 'JSON':
            return self._generate_json(report_data)
        elif format_type == 'HTML':
            return self._generate_html(report_data, include_charts)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
            
    def _generate_pdf(self, report_data: Dict[str, Any], include_charts: bool) -> bytes:
        """Generate PDF report using ReportLab"""
        if not REPORTLAB_AVAILABLE:
            return self._generate_fallback_pdf(report_data)
            
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=self.styles['title']['size'],
            textColor=colors.HexColor(self.styles['title']['color']),
            alignment=TA_CENTER
        )
        
        if 'title' in report_data:
            story.append(Paragraph(report_data['title'], title_style))
            story.append(Spacer(1, 0.5*inch))
        
        # Metadata
        if 'metadata' in report_data:
            metadata = report_data['metadata']
            info_text = f"Generated: {metadata.get('generated_at', datetime.now().strftime('%Y-%m-%d %H:%M'))}<br/>"
            info_text += f"Department: {metadata.get('department', 'All Departments')}<br/>"
            info_text += f"Period: {metadata.get('period', 'Current Period')}"
            story.append(Paragraph(info_text, styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        # Sections
        for section in report_data.get('sections', []):
            # Section header
            if 'header' in section:
                header_style = ParagraphStyle(
                    'SectionHeader',
                    parent=styles['Heading2'],
                    fontSize=self.styles['subtitle']['size'],
                    textColor=colors.HexColor(self.styles['subtitle']['color'])
                )
                story.append(Paragraph(section['header'], header_style))
                story.append(Spacer(1, 0.2*inch))
            
            # Section content
            if 'content' in section:
                story.append(Paragraph(section['content'], styles['Normal']))
                story.append(Spacer(1, 0.2*inch))
            
            # Data tables
            if 'data' in section and isinstance(section['data'], pd.DataFrame):
                df = section['data']
                # Convert DataFrame to table data
                table_data = [df.columns.tolist()] + df.values.tolist()
                
                # Create table
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.3*inch))
            
            # Charts (as images if available)
            if include_charts and 'chart' in section and section['chart']:
                # Add chart image placeholder
                story.append(Paragraph("📊 Chart: " + section.get('chart_title', 'Data Visualization'), styles['Normal']))
                story.append(Spacer(1, 0.2*inch))
        
        # Footer
        if 'footer' in report_data:
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=self.styles['footer']['size'],
                textColor=colors.HexColor(self.styles['footer']['color']),
                alignment=TA_CENTER
            )
            story.append(PageBreak())
            story.append(Paragraph(report_data['footer'], footer_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _generate_fallback_pdf(self, report_data: Dict[str, Any]) -> bytes:
        """Generate simple PDF when ReportLab is not available"""
        # Generate HTML and return as text file with .pdf extension notice
        html_content = self._generate_html(report_data, False)
        return html_content.encode('utf-8')
    
    def _generate_csv(self, report_data: Dict[str, Any]) -> bytes:
        """Generate CSV export of data tables"""
        buffer = io.StringIO()
        
        # Combine all data sections into single CSV
        all_data = []
        for section in report_data.get('sections', []):
            if 'data' in section and isinstance(section['data'], pd.DataFrame):
                # Add section header as separator
                if 'header' in section:
                    all_data.append(pd.DataFrame([[f"--- {section['header']} ---"]]))
                all_data.append(section['data'])
                all_data.append(pd.DataFrame([[]]))  # Empty row separator
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df.to_csv(buffer, index=False)
        else:
            # Create minimal CSV with report metadata
            metadata_df = pd.DataFrame([report_data.get('metadata', {})])
            metadata_df.to_csv(buffer, index=False)
        
        return buffer.getvalue().encode('utf-8')
    
    def _generate_xlsx(self, report_data: Dict[str, Any], include_charts: bool) -> bytes:
        """Generate Excel workbook with multiple sheets"""
        if not XLSXWRITER_AVAILABLE:
            # Fallback to CSV if XlsxWriter not available
            return self._generate_csv(report_data)
            
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Add formats
            title_format = workbook.add_format({
                'bold': True,
                'font_size': self.styles['title']['size'],
                'font_color': self.styles['title']['color'],
                'align': 'center'
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'font_size': self.styles['header']['size'],
                'bg_color': '#3b82f6',
                'font_color': 'white',
                'border': 1
            })
            
            # Summary sheet
            summary_df = pd.DataFrame([{
                'Report Title': report_data.get('title', 'GovSight Report'),
                'Generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'Department': report_data.get('metadata', {}).get('department', 'All'),
                'Period': report_data.get('metadata', {}).get('period', 'Current')
            }])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add data sections as separate sheets
            for idx, section in enumerate(report_data.get('sections', [])):
                if 'data' in section and isinstance(section['data'], pd.DataFrame):
                    sheet_name = section.get('header', f'Data_{idx+1}')[:31]  # Excel sheet name limit
                    df = section['data']
                    
                    # Write dataframe
                    df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
                    
                    # Get worksheet
                    worksheet = writer.sheets[sheet_name]
                    
                    # Write section title
                    worksheet.write(0, 0, section.get('header', 'Data Section'), title_format)
                    
                    # Format headers
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(1, col_num, value, header_format)
                    
                    # Auto-fit columns
                    for col_idx, col in enumerate(df.columns):
                        max_len = max(
                            df[col].astype(str).map(len).max(),
                            len(str(col))
                        ) + 2
                        worksheet.set_column(col_idx, col_idx, min(max_len, 50))
                    
                    # Add chart if requested
                    if include_charts and len(df) > 0:
                        # Add simple column chart for numeric data
                        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
                        if len(numeric_cols) > 0:
                            chart = workbook.add_chart({'type': 'column'})
                            for col_idx, col in enumerate(numeric_cols[:3]):  # Limit to 3 series
                                chart.add_series({
                                    'name': col,
                                    'categories': [sheet_name, 2, 0, len(df)+1, 0],
                                    'values': [sheet_name, 2, col_idx+1, len(df)+1, col_idx+1],
                                })
                            chart.set_title({'name': section.get('chart_title', 'Data Visualization')})
                            worksheet.insert_chart(f'A{len(df)+5}', chart)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _generate_json(self, report_data: Dict[str, Any]) -> bytes:
        """Generate JSON export of report data"""
        # Convert DataFrames to dictionaries
        export_data = report_data.copy()
        
        for section in export_data.get('sections', []):
            if 'data' in section and isinstance(section['data'], pd.DataFrame):
                section['data'] = section['data'].to_dict('records')
        
        # Add timestamp
        export_data['export_timestamp'] = datetime.now().isoformat()
        
        return json.dumps(export_data, indent=2, default=str).encode('utf-8')
    
    def _generate_html(self, report_data: Dict[str, Any], include_charts: bool) -> str:
        """Generate HTML report with embedded styles"""
        html_parts = ["""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>GovSight Report</title>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9fafb;
                }
                .report-title {
                    color: #1e3a8a;
                    text-align: center;
                    margin-bottom: 30px;
                }
                .metadata {
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .section {
                    background: white;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .section-header {
                    color: #3b82f6;
                    margin-bottom: 15px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }
                th {
                    background-color: #3b82f6;
                    color: white;
                    padding: 10px;
                    text-align: left;
                }
                td {
                    padding: 8px;
                    border-bottom: 1px solid #e5e7eb;
                }
                tr:hover {
                    background-color: #f3f4f6;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    color: #6b7280;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
        """]
        
        # Title
        if 'title' in report_data:
            html_parts.append(f'<h1 class="report-title">{report_data["title"]}</h1>')
        
        # Metadata
        if 'metadata' in report_data:
            metadata = report_data['metadata']
            html_parts.append('<div class="metadata">')
            html_parts.append(f'<p><strong>Generated:</strong> {metadata.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))}</p>')
            html_parts.append(f'<p><strong>Department:</strong> {metadata.get("department", "All Departments")}</p>')
            html_parts.append(f'<p><strong>Period:</strong> {metadata.get("period", "Current Period")}</p>')
            html_parts.append('</div>')
        
        # Sections
        for section in report_data.get('sections', []):
            html_parts.append('<div class="section">')
            
            if 'header' in section:
                html_parts.append(f'<h2 class="section-header">{section["header"]}</h2>')
            
            if 'content' in section:
                html_parts.append(f'<p>{section["content"]}</p>')
            
            if 'data' in section and isinstance(section['data'], pd.DataFrame):
                html_parts.append(section['data'].to_html(classes='data-table', index=False))
            
            if include_charts and 'chart' in section:
                html_parts.append(f'<div class="chart-placeholder">📊 Chart: {section.get("chart_title", "Data Visualization")}</div>')
            
            html_parts.append('</div>')
        
        # Footer
        if 'footer' in report_data:
            html_parts.append(f'<div class="footer">{report_data["footer"]}</div>')
        
        html_parts.append('</body></html>')
        
        return ''.join(html_parts)
    
    def create_download_button(self, 
                             report_data: Dict[str, Any],
                             format_type: str,
                             button_label: str = None,
                             filename: str = None) -> None:
        """
        Create a Streamlit download button for report export
        
        Args:
            report_data: Report data dictionary
            format_type: Export format
            button_label: Optional custom button label
            filename: Optional custom filename
        """
        if button_label is None:
            button_label = f"📥 Export as {format_type}"
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = format_type.lower()
            if extension == 'xlsx':
                extension = 'xlsx'
            elif extension == 'json':
                extension = 'json'
            filename = f"govsight_report_{timestamp}.{extension}"
        
        # Generate report
        report_bytes = self.generate_report(report_data, format_type)
        
        # Determine MIME type
        mime_types = {
            'PDF': 'application/pdf',
            'CSV': 'text/csv',
            'XLSX': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'JSON': 'application/json',
            'HTML': 'text/html'
        }
        
        mime_type = mime_types.get(format_type.upper(), 'application/octet-stream')
        
        # Create download button
        st.download_button(
            label=button_label,
            data=report_bytes,
            file_name=filename,
            mime=mime_type,
            key=f"download_{format_type}_{datetime.now().timestamp()}"
        )