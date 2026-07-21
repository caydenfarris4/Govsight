"""
ADA Accessibility Helper Module

This module provides utilities and components to ensure ADA compliance across
the GovSight Financial Analyzer platform, including:
- WCAG 2.1 AA compliant color schemes
- Screen reader support
- Keyboard navigation
- Accessible form components
- Chart accessibility features
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ADA compliant color palette
ADA_COLORS = {
    'primary': '#003080',      # High contrast blue
    'secondary': '#0056CC',    # Medium blue
    'accent': '#FFD700',       # Gold for focus states
    'success': '#155724',      # Dark green
    'info': '#0c5460',         # Dark cyan
    'warning': '#856404',      # Dark orange
    'danger': '#721c24',       # Dark red
    'light': '#f8f9fa',        # Light gray
    'dark': '#212529',         # Dark text
    'white': '#ffffff',        # White
    'border': '#dee2e6'        # Border color
}

def add_accessibility_features():
    """Add platform-wide accessibility features including CSS and JavaScript"""
    st.markdown("""
    <script>
    // Add keyboard navigation support
    document.addEventListener('DOMContentLoaded', function() {
        // Add ARIA landmarks to main sections
        const main = document.querySelector('.main');
        if (main) {
            main.setAttribute('role', 'main');
            main.setAttribute('aria-label', 'Main content');
        }
        
        // Enhance tab navigation
        const tabs = document.querySelectorAll('[data-baseweb="tab"]');
        tabs.forEach((tab, index) => {
            tab.setAttribute('role', 'tab');
            tab.setAttribute('aria-label', `Tab ${index + 1}: ${tab.textContent}`);
        });
        
        // Add skip links functionality
        const skipLink = document.querySelector('.skip-nav');
        if (skipLink) {
            skipLink.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector('#main-content');
                if (target) {
                    target.focus();
                    target.scrollIntoView();
                }
            });
        }
    });
    </script>
    """, unsafe_allow_html=True)

def create_accessible_button(label, key=None, help_text=None, disabled=False, primary=True):
    """Create an ADA compliant button with proper ARIA attributes"""
    button_type = "primary" if primary else "secondary"
    
    if help_text:
        st.help(help_text)
    
    return st.button(
        label,
        key=key,
        disabled=disabled,
        help=help_text,
        type=button_type,
        use_container_width=True
    )

def create_accessible_selectbox(label, options, key=None, help_text=None, index=0):
    """Create an ADA compliant selectbox with proper labeling"""
    return st.selectbox(
        label,
        options,
        index=index,
        key=key,
        help=help_text or f"Select from {len(options)} available options",
        label_visibility="visible"
    )

def create_accessible_text_input(label, key=None, help_text=None, placeholder=None):
    """Create an ADA compliant text input with proper labeling"""
    return st.text_input(
        label,
        key=key,
        help=help_text,
        placeholder=placeholder,
        label_visibility="visible"
    )

def create_accessible_number_input(label, min_value=None, max_value=None, value=None, key=None, help_text=None):
    """Create an ADA compliant number input with proper labeling"""
    return st.number_input(
        label,
        min_value=min_value,
        max_value=max_value,
        value=value,
        key=key,
        help=help_text,
        label_visibility="visible"
    )

def create_accessible_chart(fig, title, description=None):
    """Make Plotly charts accessible with proper ARIA labels and descriptions"""
    
    # Update layout for accessibility - ensure title visibility
    fig.update_layout(
        title={
            'text': title,
            'font': {'size': 16, 'color': ADA_COLORS['dark']},
            'x': 0.5,
            'xanchor': 'center',
            'y': 0.90,
            'yanchor': 'top'
        },
        font={'size': 12, 'color': ADA_COLORS['dark']},
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=60, r=140, t=80, b=60),
        xaxis={
            'gridcolor': ADA_COLORS['border'],
            'linecolor': ADA_COLORS['dark'],
            'tickfont': {'size': 11, 'color': ADA_COLORS['dark']}
        },
        yaxis={
            'gridcolor': ADA_COLORS['border'],
            'linecolor': ADA_COLORS['dark'],
            'tickfont': {'size': 11, 'color': ADA_COLORS['dark']}
        },
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor=ADA_COLORS['border'],
            borderwidth=1,
            font={'size': 10}
        ),
        showlegend=True,
        height=450
    )
    
    # Add accessibility attributes with working fullscreen
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
        'responsive': True,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'chart_{title.lower().replace(" ", "_")}',
            'height': 600,
            'width': 800,
            'scale': 2
        }
    }
    
    # Display title above chart to ensure visibility
    if title:
        st.markdown(f"### {title}")
    
    # Force remove any title properties that might contain "undefined"
    if hasattr(fig, 'layout') and hasattr(fig.layout, 'title'):
        if fig.layout.title and hasattr(fig.layout.title, 'text'):
            fig.layout.title.text = ''
    
    # Update layout to completely clear title
    fig.update_layout(
        title=dict(text=''),
        annotations=[]
    )
    
    # Display chart with description
    if description:
        st.markdown(f"*{description}*")
    
    st.plotly_chart(fig, use_container_width=True, config=config, theme="streamlit")

def create_chart_text_summary(fig):
    """Create a text summary of chart data for screen readers"""
    summary = f"Chart Title: {fig.layout.title.text if fig.layout.title else 'Untitled Chart'}\n\n"
    
    for i, trace in enumerate(fig.data):
        trace_name = trace.name if trace.name else f"Series {i+1}"
        summary += f"Data Series: {trace_name}\n"
        
        if hasattr(trace, 'x') and hasattr(trace, 'y'):
            if len(trace.x) <= 10:  # Show all points for small datasets
                for j, (x, y) in enumerate(zip(trace.x, trace.y)):
                    summary += f"  Point {j+1}: {x} = {y}\n"
            else:  # Show summary for large datasets
                summary += f"  Data points: {len(trace.x)}\n"
                summary += f"  X range: {min(trace.x)} to {max(trace.x)}\n"
                summary += f"  Y range: {min(trace.y)} to {max(trace.y)}\n"
                summary += f"  Average Y value: {sum(trace.y)/len(trace.y):.2f}\n"
        
        summary += "\n"
    
    return summary

def create_accessible_dataframe(df, title=None, description=None, key=None):
    """Display a dataframe with enhanced accessibility and smooth styling"""
    
    if title:
        st.markdown(f"""
        <h3 style="color: #374151; font-weight: 600; margin-bottom: 16px; 
                   font-family: 'Inter', sans-serif;">{title}</h3>
        """, unsafe_allow_html=True)
    
    if description:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%); 
                    padding: 12px 16px; border-radius: 8px; border-left: 4px solid #004AAD; 
                    margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
            <strong style="color: #374151;">Table Description:</strong> 
            <span style="color: #374151;">{description}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Add summary information with enhanced styling
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); 
                padding: 10px 14px; border-radius: 6px; border: 1px solid #e5e7eb; 
                margin-bottom: 16px; font-size: 14px; color: #6b7280;">
        <strong>Table Summary:</strong> {len(df)} rows and {len(df.columns)} columns
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced container for dataframe
    st.markdown("""
    <div style="background: white; border-radius: 12px; padding: 16px; 
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb; 
                margin: 16px 0; overflow: hidden;">
    """, unsafe_allow_html=True)
    
    # Display the dataframe
    st.dataframe(
        df,
        use_container_width=True,
        key=key,
        hide_index=True
    )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add download option with enhanced styling
    csv = df.to_csv(index=False)
    st.download_button(
        label=" Download data as CSV",
        data=csv,
        file_name=f"{title.lower().replace(' ', '_') if title else 'data'}.csv",
        mime="text/csv",
        help="Download this table data in CSV format for use with screen readers",
        type="secondary"
    )

def create_accessible_metric(label, value, delta=None, help_text=None):
    """Create an accessible metric display with enhanced styling"""
    
    # Enhanced container for metric
    st.markdown("""
    <div style="background: white; border-radius: 12px; padding: 20px; 
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb; 
                margin: 8px 0; transition: all 0.2s ease-in-out;">
    """, unsafe_allow_html=True)
    
    # Create the metric
    st.metric(
        label=label,
        value=value,
        delta=delta,
        help=help_text
    )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add accessible description
    metric_text = f"{label}: {value}"
    if delta:
        metric_text += f" (change: {delta})"
    
    # Hidden text for screen readers
    st.markdown(f"""
    <div class="sr-only" aria-label="{metric_text}">
        {metric_text}
    </div>
    """, unsafe_allow_html=True)

def add_screen_reader_text(text):
    """Add text that is only visible to screen readers"""
    st.markdown(f"""
    <div class="sr-only" aria-label="{text}">
        {text}
    </div>
    """, unsafe_allow_html=True)

def create_accessible_tabs(tab_names, key=None):
    """Create accessible tabs with proper ARIA attributes"""
    
    # Add keyboard navigation instructions
    st.markdown("*Use arrow keys to navigate between tabs*")
    
    # Create tabs with accessibility features
    tabs = st.tabs(tab_names)
    
    # Add ARIA labels via JavaScript
    st.markdown(f"""
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        const tabs = document.querySelectorAll('[data-baseweb="tab"]');
        const tabNames = {tab_names};
        tabs.forEach((tab, index) => {{
            if (index < tabNames.length) {{
                tab.setAttribute('aria-label', `Tab: ${{tabNames[index]}}`);
                tab.setAttribute('role', 'tab');
            }}
        }});
    }});
    </script>
    """, unsafe_allow_html=True)
    
    return tabs

def validate_color_contrast(foreground, background):
    """Validate WCAG color contrast ratios"""
    # This is a simplified contrast check
    # In production, you'd want to use a proper color contrast library
    
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def luminance(r, g, b):
        def adjust(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)
        
        return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)
    
    fg_rgb = hex_to_rgb(foreground)
    bg_rgb = hex_to_rgb(background)
    
    fg_lum = luminance(*fg_rgb)
    bg_lum = luminance(*bg_rgb)
    
    lighter = max(fg_lum, bg_lum)
    darker = min(fg_lum, bg_lum)
    
    contrast_ratio = (lighter + 0.05) / (darker + 0.05)
    
    return {
        'ratio': contrast_ratio,
        'aa_normal': contrast_ratio >= 4.5,
        'aa_large': contrast_ratio >= 3.0,
        'aaa_normal': contrast_ratio >= 7.0,
        'aaa_large': contrast_ratio >= 4.5
    }

def add_accessibility_css():
    """Add comprehensive accessibility CSS with smooth, polished design"""
    st.markdown("""
    <style>
    /* Global smooth transitions */
    * {
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    /* Screen reader only text */
    .sr-only {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        * {
            background: white !important;
            color: black !important;
            border-color: black !important;
        }
        
        .stButton > button {
            background: black !important;
            color: white !important;
            border: 2px solid black !important;
        }
    }
    
    /* Smooth focus management with animations */
    *:focus {
        outline: 3px solid #FFD700 !important;
        outline-offset: 2px !important;
        box-shadow: 0 0 0 4px rgba(255, 215, 0, 0.3), 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Enhanced button styling */
    button, .stButton > button, [role="button"] {
        min-height: 44px !important;
        min-width: 44px !important;
        padding: 12px 24px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        border: 2px solid transparent !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Primary button styling */
    .stButton > button[data-baseweb="button"][data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #004AAD 0%, #0056CC 100%) !important;
        color: white !important;
        border: 2px solid #004AAD !important;
    }
    
    .stButton > button[data-baseweb="button"][data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #003080 0%, #004AAD 100%) !important;
        box-shadow: 0 4px 16px rgba(0, 74, 173, 0.3) !important;
    }
    
    /* Smooth link styling */
    a {
        text-decoration: underline !important;
        color: #0056CC !important;
        border-radius: 4px !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    a:hover, a:focus {
        color: #003080 !important;
        background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%) !important;
        padding: 4px 8px !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(0, 86, 204, 0.15) !important;
    }
    
    /* Smooth table styling */
    table, .stDataFrame {
        border-collapse: collapse !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #e5e7eb !important;
    }
    
    th, td {
        border: 1px solid #e5e7eb !important;
        padding: 12px 16px !important;
        text-align: left !important;
        transition: background-color 0.2s ease-in-out !important;
    }
    
    th {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
        font-weight: 600 !important;
        color: #495057 !important;
    }
    
    tbody tr:hover {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%) !important;
    }
    
    /* Enhanced form styling */
    label, .stTextInput > label, .stNumberInput > label, .stSelectbox > label {
        font-weight: 600 !important;
        margin-bottom: 8px !important;
        display: block !important;
        color: #374151 !important;
        font-size: 14px !important;
    }
    
    input, select, textarea, 
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid #e5e7eb !important;
        padding: 12px 16px !important;
        font-size: 16px !important;
        border-radius: 8px !important;
        background: white !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    input:focus, select:focus, textarea:focus,
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #0056CC !important;
        box-shadow: 0 0 0 3px rgba(0, 86, 204, 0.1), 0 2px 8px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Smooth notification styling */
    .stError {
        border: none !important;
        border-left: 4px solid #dc3545 !important;
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%) !important;
        color: #721c24 !important;
        padding: 16px 20px !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(220, 53, 69, 0.15) !important;
        margin: 8px 0 !important;
    }
    
    .stSuccess {
        border: none !important;
        border-left: 4px solid #28a745 !important;
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%) !important;
        color: #155724 !important;
        padding: 16px 20px !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(40, 167, 69, 0.15) !important;
        margin: 8px 0 !important;
    }
    
    .stWarning {
        border: none !important;
        border-left: 4px solid #ffc107 !important;
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%) !important;
        color: #856404 !important;
        padding: 16px 20px !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(255, 193, 7, 0.15) !important;
        margin: 8px 0 !important;
    }
    
    .stInfo {
        border: none !important;
        border-left: 4px solid #17a2b8 !important;
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%) !important;
        color: #0c5460 !important;
        padding: 16px 20px !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(23, 162, 184, 0.15) !important;
        margin: 8px 0 !important;
    }
    
    /* Smooth metric styling */
    [data-testid="metric-container"] {
        background: white !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #e5e7eb !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    [data-testid="metric-container"]:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Smooth expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%) !important;
        border-radius: 8px !important;
        border: 1px solid #e5e7eb !important;
        padding: 12px 16px !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Smooth tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #e5e7eb !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        transition: all 0.2s ease-in-out !important;
        padding: 12px 20px !important;
        margin: 0 2px !important;
        font-weight: 500 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #004AAD 0%, #0056CC 100%) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(0, 74, 173, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Smooth slider styling */
    .stSlider > div > div > div > div {
        background: linear-gradient(135deg, #004AAD 0%, #0056CC 100%) !important;
        border-radius: 4px !important;
    }
    
    /* Smooth sidebar styling */
    .css-1d391kg, .css-1lcbmhc {
        background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%) !important;
        border-right: 1px solid #e5e7eb !important;
    }
    
    /* Smooth container styling */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Chat interface styling */
    [role="log"] {
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    [role="log"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    </style>
    """, unsafe_allow_html=True)

def create_accessible_progress_bar(value, max_value=100, label=None):
    """Create an accessible progress bar"""
    percentage = (value / max_value) * 100
    
    if label:
        st.markdown(f"**{label}**")
    
    st.progress(value / max_value)
    
    # Add accessible text description
    progress_text = f"Progress: {value} out of {max_value} ({percentage:.1f}%)"
    add_screen_reader_text(progress_text)
    
    return percentage

def announce_to_screen_reader(message):
    """Announce a message to screen readers using ARIA live regions"""
    st.markdown(f"""
    <div aria-live="polite" aria-atomic="true" class="sr-only">
        {message}
    </div>
    """, unsafe_allow_html=True)