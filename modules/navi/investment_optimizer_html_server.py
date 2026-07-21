"""
HTML/TypeScript Investment Optimizer Server
Serves the modern HTML/TypeScript investment optimizer interface
"""

import streamlit as st
import streamlit.components.v1 as components
import os

def render_investment_optimizer_html():
    """
    Render the HTML/TypeScript Investment Optimizer
    """
    # Get the path to the HTML file
    html_path = os.path.join(os.path.dirname(__file__), 'investment_optimizer_html.html')
    
    # Read the HTML file
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Render the HTML component
    components.html(html_content, height=1200, scrolling=True)
