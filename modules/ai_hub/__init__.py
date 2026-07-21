"""
AI Hub Module

Centralized AI functionality and prompt management
"""

# Import from root ai_hub.py for compatibility
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from ai_hub import (
        ask_ai, build_context, generate_dept_insights, 
        analyze_document, generate_forecast, simulate_adjustment,
        generate_pdf_report, generate_multi_chart_report
    )
except ImportError:
    # Fallback implementations for testing
    def ask_ai(prompt, df=None, sources=[], model="gpt-4o", max_tokens=750):
        return "AI response placeholder"
    
    def build_context(df, sources, user_prompt):
        return "Context placeholder"
    
    def generate_dept_insights(df, dept_name="", prompt=None):
        return "Department insights placeholder"
    
    def analyze_document(doc_text, analysis_type="General Summary"):
        return "Document analysis placeholder"
    
    def generate_forecast(df, year_col, value_col, forecast_years=3):
        return df
    
    def simulate_adjustment(prompt, df, model="gpt-3.5-turbo"):
        return df
    
    def generate_pdf_report(df, title="Report", analysis_text=None, include_data=True, include_charts=True):
        return b"PDF placeholder"
    
    def generate_multi_chart_report(charts_data, org_name="GovSight", title="Report"):
        return b"PDF placeholder"

__all__ = [
    'ask_ai',
    'build_context',
    'generate_dept_insights',
    'analyze_document',
    'generate_forecast',
    'simulate_adjustment',
    'generate_pdf_report',
    'generate_multi_chart_report'
]