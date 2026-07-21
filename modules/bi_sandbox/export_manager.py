"""
BI Sandbox Export Manager - Data export and report generation
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
from io import BytesIO
from datetime import datetime
import tempfile
import os
from typing import List, Dict, Any, Optional
import base64

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.database.db_connection import format_currency, format_percentage

def export_to_csv(df: pd.DataFrame) -> bytes:
    """
    Export DataFrame to CSV format
    
    Args:
        df: DataFrame to export
        
    Returns:
        CSV data as bytes
    """
    
    try:
        return df.to_csv(index=False).encode('utf-8')
    except Exception as e:
        st.error(f"Error exporting to CSV: {str(e)}")
        return b""

def export_to_excel(df: pd.DataFrame, filename: str = "sandbox_export.xlsx") -> bytes:
    """
    Export DataFrame to Excel format
    
    Args:
        df: DataFrame to export
        filename: Output filename
        
    Returns:
        Excel data as bytes
    """
    
    try:
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Data', index=False)
            
            # Get the workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Data']
            
            # Add formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Apply header formatting
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(df.columns):
                max_len = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
                worksheet.set_column(i, i, min(max_len, 50))
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        st.error(f"Error exporting to Excel: {str(e)}")
        return b""

def generate_pdf_report(df: pd.DataFrame, charts: List[Dict[str, Any]] = None, 
                       org_name: str = "GovSight") -> bytes:
    """
    Generate comprehensive PDF report
    
    Args:
        df: Data to include in report
        charts: List of chart configurations and figures
        org_name: Organization name for report header
        
    Returns:
        PDF data as bytes
    """
    
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Title page
        create_title_page(pdf, org_name)
        
        # Data summary page
        create_data_summary_page(pdf, df)
        
        # Charts pages
        if charts:
            create_charts_pages(pdf, charts)
        
        # Data tables page
        create_data_tables_page(pdf, df)
        
        return pdf.output(dest='S').encode('utf-8', errors='replace')
        
    except Exception as e:
        st.error(f"Error generating PDF report: {str(e)}")
        return b""

def create_title_page(pdf: FPDF, org_name: str):
    """Create PDF title page"""
    
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 24)
    pdf.cell(0, 20, f"{org_name} BI Dashboard Report", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "Self-Service Business Intelligence Analysis", ln=True, align="C")
    
    # Date and time
    pdf.set_font("Arial", "", 12)
    pdf.ln(20)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align="C")
    
    # Add some space and description
    pdf.ln(30)
    pdf.set_font("Arial", "", 11)
    
    description = """
This report contains analysis from the GovSight BI Sandbox, including:

• Data visualizations and charts
• Summary statistics and metrics  
• Detailed data tables
• Key insights and trends

The BI Sandbox enables self-service analytics for budget and financial data,
allowing users to create custom visualizations and explore data interactively.
"""
    
    pdf.multi_cell(0, 8, description)

def create_data_summary_page(pdf: FPDF, df: pd.DataFrame):
    """Create data summary page"""
    
    pdf.add_page()
    
    # Page title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "Data Summary", ln=True)
    pdf.ln(5)
    
    # Basic statistics
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Dataset Overview", ln=True)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Total Records: {len(df):,}", ln=True)
    pdf.cell(0, 6, f"Total Columns: {len(df.columns)}", ln=True)
    
    # Numeric columns summary
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Numeric Columns Summary", ln=True)
        
        for col in numeric_cols[:5]:  # Limit to first 5 for space
            if col in df.columns:
                total = df[col].sum()
                avg = df[col].mean()
                
                pdf.set_font("Arial", "", 10)
                if 'Budget' in col or 'Actual' in col or 'Amount' in col:
                    pdf.cell(0, 6, f"{col}: Total {format_currency(total)}, Average {format_currency(avg)}", ln=True)
                else:
                    pdf.cell(0, 6, f"{col}: Total {total:,.2f}, Average {avg:.2f}", ln=True)
    
    # Department breakdown if available
    if 'Department' in df.columns:
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Department Breakdown", ln=True)
        
        dept_counts = df['Department'].value_counts().head(10)
        
        for dept, count in dept_counts.items():
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"{dept}: {count:,} records", ln=True)

def create_charts_pages(pdf: FPDF, charts: List[Dict[str, Any]]):
    """Create pages for charts"""
    
    for i, chart_data in enumerate(charts):
        pdf.add_page()
        
        # Chart title
        pdf.set_font("Arial", "B", 14)
        chart_config = chart_data.get('config', {})
        chart_title = f"Chart {i+1}: {chart_config.get('chart_type', 'Unknown')} - {chart_config.get('measure', 'Unknown Measure')}"
        pdf.cell(0, 10, chart_title, ln=True)
        
        # Chart configuration details
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Dimensions: {', '.join(chart_config.get('dimensions', []))}", ln=True)
        pdf.cell(0, 6, f"Measure: {chart_config.get('measure', 'Unknown')}", ln=True)
        pdf.cell(0, 6, f"Aggregation: {chart_config.get('aggregation', 'Unknown')}", ln=True)
        pdf.cell(0, 6, f"Created: {chart_config.get('created_at', 'Unknown')}", ln=True)
        pdf.ln(5)
        
        # Placeholder for chart image
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 6, "[Chart visualization would appear here in the web interface]", ln=True)
        
        # Add some analysis text if available
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Chart Analysis", ln=True)
        
        pdf.set_font("Arial", "", 10)
        analysis_text = f"""
This {chart_config.get('chart_type', 'chart')} visualization shows {chart_config.get('measure', 'the selected measure')} 
broken down by {', '.join(chart_config.get('dimensions', ['the selected dimensions']))}.

The data has been aggregated using {chart_config.get('aggregation', 'the selected method')} to provide
meaningful insights into the budget and financial patterns.
"""
        pdf.multi_cell(0, 6, analysis_text)

def create_data_tables_page(pdf: FPDF, df: pd.DataFrame):
    """Create data tables page"""
    
    pdf.add_page()
    
    # Page title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "Data Tables", ln=True)
    pdf.ln(5)
    
    # Limit data for PDF display
    display_df = df.head(50)  # Show first 50 rows
    display_cols = df.columns[:6]  # Show first 6 columns
    
    if len(display_cols) > 0:
        # Calculate column width
        col_width = 180 / len(display_cols)
        
        # Table headers
        pdf.set_font("Arial", "B", 9)
        for col in display_cols:
            pdf.cell(col_width, 8, str(col)[:15], border=1, align='C')  # Truncate long column names
        pdf.ln()
        
        # Table data
        pdf.set_font("Arial", "", 8)
        for _, row in display_df.iterrows():
            for col in display_cols:
                value = row[col]
                
                # Format the value
                if pd.isna(value):
                    formatted_value = ""
                elif isinstance(value, (int, float)):
                    if 'Budget' in col or 'Actual' in col or 'Amount' in col:
                        formatted_value = f"${value:,.0f}"
                    else:
                        formatted_value = f"{value:,.2f}"
                else:
                    formatted_value = str(value)[:12]  # Truncate long text
                
                pdf.cell(col_width, 6, formatted_value, border=1, align='C')
            pdf.ln()
    
    # Add notes about data limitations
    pdf.ln(5)
    pdf.set_font("Arial", "I", 9)
    
    notes = []
    if len(df) > 50:
        notes.append(f"Showing first 50 rows of {len(df)} total rows")
    if len(df.columns) > 6:
        notes.append(f"Showing first 6 columns of {len(df.columns)} total columns")
    
    if notes:
        pdf.cell(0, 6, "Note: " + "; ".join(notes), ln=True)

def create_chart_image_for_pdf(figure, filename: str) -> str:
    """
    Convert plotly figure to image for PDF inclusion
    
    Args:
        figure: Plotly figure object
        filename: Output filename
        
    Returns:
        Path to generated image file
    """
    
    try:
        # This would normally convert the plotly figure to an image
        # For now, we'll create a placeholder
        
        # Create a temporary file
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        
        # In a real implementation, you would use:
        # figure.write_image(temp_path, format='png', width=800, height=600)
        
        return temp_path
        
    except Exception as e:
        st.warning(f"Could not generate chart image: {str(e)}")
        return ""

def generate_summary_statistics_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive summary statistics"""
    
    if df.empty:
        return {"error": "No data available for analysis"}
    
    summary = {
        "dataset_info": {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum(),
            "generation_time": datetime.now().isoformat()
        }
    }
    
    # Numeric columns analysis
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        summary["numeric_analysis"] = {}
        
        for col in numeric_cols:
            col_stats = {
                "count": df[col].count(),
                "mean": df[col].mean(),
                "median": df[col].median(),
                "std": df[col].std(),
                "min": df[col].min(),
                "max": df[col].max(),
                "missing_values": df[col].isnull().sum(),
                "unique_values": df[col].nunique()
            }
            
            # Add quartiles
            quartiles = df[col].quantile([0.25, 0.75])
            col_stats["q1"] = quartiles[0.25]
            col_stats["q3"] = quartiles[0.75]
            col_stats["iqr"] = col_stats["q3"] - col_stats["q1"]
            
            summary["numeric_analysis"][col] = col_stats
    
    # Categorical columns analysis
    categorical_cols = df.select_dtypes(include=['object']).columns
    if len(categorical_cols) > 0:
        summary["categorical_analysis"] = {}
        
        for col in categorical_cols:
            col_stats = {
                "count": df[col].count(),
                "unique_values": df[col].nunique(),
                "missing_values": df[col].isnull().sum(),
                "mode": df[col].mode().iloc[0] if not df[col].mode().empty else None,
                "top_values": df[col].value_counts().head(5).to_dict()
            }
            
            summary["categorical_analysis"][col] = col_stats
    
    return summary