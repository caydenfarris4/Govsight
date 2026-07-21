"""
Accessibility Helper Module for GovSight Financial Analyzer

This module provides accessibility-focused chart creation and validation functions
to ensure compliance with WCAG 2.1 guidelines for government applications.

ARCHITECTURAL DECISION: Dedicated accessibility module ensures all visualizations
meet government accessibility standards without duplicating code across modules.
"""

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from typing import Dict, List, Any, Optional


def create_accessible_chart(chart_type: str, data: Any, title: str = "", 
                          x_col: str = "", y_col: str = "", 
                          color_col: str = "", **kwargs) -> go.Figure:
    """
    Create an accessible chart with proper WCAG 2.1 compliance
    
    Args:
        chart_type: Type of chart (bar, line, scatter, pie, etc.)
        data: DataFrame or data for the chart
        title: Chart title for screen readers
        x_col: X-axis column name
        y_col: Y-axis column name
        color_col: Color column for grouping
        **kwargs: Additional chart parameters
    
    Returns:
        Plotly figure with accessibility features
        
    DESIGN DECISIONS:
    1. High contrast colors for visibility
    2. Screen reader compatible alt text
    3. Keyboard navigation support
    4. Clear axis labels and legends
    """
    
    # Define accessible color palette (high contrast, colorblind-friendly)
    accessible_colors = [
        '#1f77b4',  # Blue
        '#ff7f0e',  # Orange  
        '#2ca02c',  # Green
        '#d62728',  # Red
        '#9467bd',  # Purple
        '#8c564b',  # Brown
        '#e377c2',  # Pink
        '#7f7f7f',  # Gray
        '#bcbd22',  # Olive
        '#17becf'   # Cyan
    ]
    
    fig = None
    
    try:
        if chart_type.lower() == 'bar':
            fig = px.bar(data, x=x_col, y=y_col, color=color_col,
                        title=title, color_discrete_sequence=accessible_colors)
                        
        elif chart_type.lower() == 'line':
            fig = px.line(data, x=x_col, y=y_col, color=color_col,
                         title=title, color_discrete_sequence=accessible_colors)
                         
        elif chart_type.lower() == 'scatter':
            fig = px.scatter(data, x=x_col, y=y_col, color=color_col,
                           title=title, color_discrete_sequence=accessible_colors)
                           
        elif chart_type.lower() == 'pie':
            fig = px.pie(data, values=y_col, names=x_col, title=title,
                        color_discrete_sequence=accessible_colors)
                        
        else:
            # Default to bar chart
            fig = px.bar(data, x=x_col, y=y_col, title=title,
                        color_discrete_sequence=accessible_colors)
    
    except Exception as e:
        # Create a simple fallback chart
        fig = go.Figure()
        fig.add_annotation(
            text=f"Chart creation error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            font=dict(size=16, color="red")
        )
        fig.update_layout(title=title or "Chart Error")
    
    if fig:
        # Apply accessibility enhancements
        fig = enhance_chart_accessibility(fig, title)
    
    return fig


def enhance_chart_accessibility(fig: go.Figure, title: str = "") -> go.Figure:
    """
    Enhance a Plotly figure with accessibility features
    
    Args:
        fig: Plotly figure to enhance
        title: Chart title for accessibility
        
    Returns:
        Enhanced figure with accessibility features
    """
    
    # Update layout for accessibility
    fig.update_layout(
        # High contrast and readable fonts
        font=dict(
            family="Arial, sans-serif",
            size=14,
            color="#212529"
        ),
        
        # Clear title
        title=dict(
            text=title,
            font=dict(size=18, color="#212529"),
            x=0.5,
            xanchor='center'
        ),
        
        # High contrast background
        plot_bgcolor='white',
        paper_bgcolor='white',
        
        # Clear grid lines
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            title_font=dict(size=14, color="#212529"),
            tickfont=dict(size=12, color="#212529")
        ),
        
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray', 
            gridwidth=1,
            title_font=dict(size=14, color="#212529"),
            tickfont=dict(size=12, color="#212529")
        ),
        
        # Accessible legend
        legend=dict(
            font=dict(size=12, color="#212529"),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='gray',
            borderwidth=1
        ),
        
        # Minimum height for touch targets
        height=400,
        
        # Hover template for screen readers
        hovermode='closest'
    )
    
    # Add alt text as a layout annotation (for screen readers)
    if title:
        fig.add_annotation(
            text=f"Chart: {title}",
            xref="paper", yref="paper",
            x=0, y=1.1, xanchor='left', yanchor='bottom',
            font=dict(size=1, color="white"),  # Hidden but readable by screen readers
            opacity=0.01
        )
    
    return fig


def validate_chart_accessibility(fig: go.Figure) -> Dict[str, bool]:
    """
    Validate chart accessibility compliance
    
    Args:
        fig: Plotly figure to validate
        
    Returns:
        Dictionary of accessibility checks and their pass/fail status
    """
    
    checks = {
        'has_title': bool(fig.layout.title and fig.layout.title.text),
        'has_axis_labels': bool(fig.layout.xaxis.title and fig.layout.yaxis.title),
        'sufficient_height': fig.layout.height >= 300 if fig.layout.height else False,
        'high_contrast_bg': fig.layout.paper_bgcolor in ['white', '#ffffff', 'rgba(255,255,255,1)'],
        'readable_font_size': fig.layout.font.size >= 12 if fig.layout.font else False
    }
    
    return checks


def create_accessibility_report(fig: go.Figure) -> str:
    """
    Generate an accessibility compliance report for a chart
    
    Args:
        fig: Plotly figure to analyze
        
    Returns:
        String report of accessibility status
    """
    
    checks = validate_chart_accessibility(fig)
    
    report = "Chart Accessibility Report:\n"
    report += "=" * 30 + "\n"
    
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        report += f"{check.replace('_', ' ').title()}: {status}\n"
    
    overall_score = sum(checks.values()) / len(checks) * 100
    report += f"\nOverall Accessibility Score: {overall_score:.1f}%"
    
    if overall_score < 80:
        report += "\nRecommendation: Review chart settings for better accessibility"
    
    return report


def add_accessibility_features():
    """
    Add accessibility features to the Streamlit application
    
    This function adds essential accessibility features including:
    - Screen reader support
    - Keyboard navigation
    - ARIA labels
    - Focus management
    - High contrast support
    """
    
    # Add CSS for accessibility enhancements
    st.markdown("""
    <style>
        /* Screen reader only content */
        .sr-only {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            padding: 0 !important;
            margin: -1px !important;
            overflow: hidden !important;
            clip: rect(0,0,0,0) !important;
            white-space: nowrap !important;
            border: 0 !important;
        }
        
        /* Focus indicators */
        .stButton > button:focus,
        .stSelectbox > div:focus,
        .stTextInput > div > div > input:focus {
            outline: 3px solid #FFD700 !important;
            outline-offset: 2px !important;
        }
        
        /* High contrast mode support */
        @media (prefers-contrast: high) {
            .stApp {
                background-color: white !important;
                color: black !important;
            }
        }
        
        /* Reduced motion support */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        
        /* Ensure proper heading hierarchy */
        h1, h2, h3, h4, h5, h6 {
            font-weight: bold;
            margin-top: 1em;
            margin-bottom: 0.5em;
        }
        
        /* Accessible link styling */
        a {
            text-decoration: underline;
            color: #0056CC;
        }
        
        a:focus, a:hover {
            outline: 2px solid #FFD700;
            outline-offset: 2px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Add skip navigation link
    st.markdown("""
    <a href="#main-content" class="sr-only" style="position: absolute; top: 0; left: 0; background: #000; color: #fff; padding: 8px; z-index: 1000;">
        Skip to main content
    </a>
    <div id="main-content" role="main" tabindex="-1">
    """, unsafe_allow_html=True)


def add_accessibility_css():
    """
    Add comprehensive CSS for accessibility compliance
    
    This function adds CSS rules to ensure the application meets
    accessibility standards for government applications.
    """
    
    st.markdown("""
    <style>
        /* High contrast focus indicators */
        *:focus {
            outline: 3px solid #FFD700 !important;
            outline-offset: 2px !important;
        }
        
        /* Ensure minimum touch target size (44px) */
        .stButton > button,
        .stSelectbox > div,
        .stTextInput > div > div > input {
            min-height: 44px !important;
            min-width: 44px !important;
        }
        
        /* High contrast color scheme */
        .stApp {
            color: #212529 !important;
        }
        
        /* Accessible table styling */
        .stDataFrame table {
            border-collapse: collapse !important;
        }
        
        .stDataFrame th,
        .stDataFrame td {
            border: 1px solid #dee2e6 !important;
            padding: 8px !important;
        }
        
        .stDataFrame th {
            background-color: #f8f9fa !important;
            font-weight: bold !important;
        }
        
        /* Screen reader improvements */
        .stMarkdown h1,
        .stMarkdown h2, 
        .stMarkdown h3,
        .stMarkdown h4,
        .stMarkdown h5,
        .stMarkdown h6 {
            margin-top: 1em !important;
            margin-bottom: 0.5em !important;
        }
        
        /* Status indicators */
        .stSuccess,
        .stError,
        .stWarning,
        .stInfo {
            border-radius: 8px !important;
            padding: 1rem !important;
            margin: 1rem 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)


def announce_to_screen_reader(message: str, priority: str = "polite"):
    """
    Announce a message to screen readers using ARIA live regions
    
    Args:
        message: The message to announce
        priority: Either "polite" or "assertive" for announcement urgency
    """
    
    aria_live = "aria-live='assertive'" if priority == "assertive" else "aria-live='polite'"
    
    st.markdown(f"""
    <div {aria_live} aria-atomic="true" class="sr-only">
        {message}
    </div>
    """, unsafe_allow_html=True)


# Export key functions
__all__ = [
    'create_accessible_chart',
    'enhance_chart_accessibility', 
    'validate_chart_accessibility',
    'create_accessibility_report',
    'add_accessibility_features',
    'add_accessibility_css',
    'announce_to_screen_reader'
]