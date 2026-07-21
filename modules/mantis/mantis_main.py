"""
Mantis Module - Comprehensive AI Intelligence Hub

Enhanced with MantisAI Orchestrator for unified AI capabilities including:
- Grant search and eligibility analysis
- Anomaly detection in financial data
- Data quality assessment
- Natural language queries
- Multi-database analysis
- Secure file processing
- Economic scenario analysis
"""

import streamlit as st
import sys
import os

# Add the root directory to the path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)

def render_mantis_module(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the comprehensive MantisAI module with all integrated AI capabilities
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    # Add navigation back button at the very top
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back to Dashboard", key="mantis_back_to_dashboard", use_container_width=True):
            st.session_state.selected_tab = "Dashboard"
            st.rerun()
    
    # Try to import and use the enhanced orchestrator
    try:
        from modules.mantis.mantis_chat_interface_v2 import render_mantis_chat_v2
        from modules.mantis.mantis_ai_orchestrator import MantisAIOrchestrator
        
        # Initialize the MantisAI orchestrator if not already in session
        if 'mantis_orchestrator' not in st.session_state:
            st.session_state.mantis_orchestrator = MantisAIOrchestrator(org=org)
        
        # Render the enhanced chat interface with orchestrator
        render_mantis_chat_v2(org, org_display_name)
        
    except ImportError as e:
        # Fallback to simple GPT interface if orchestrator not available
        st.warning("Enhanced orchestrator not available, using simple GPT interface...")
        from modules.mantis.mantis_gpt_simple import render_mantis_gpt_chat
        render_mantis_gpt_chat(org)
        
    except Exception as e:
        st.error(f"Error initializing MantisAI: {e}")
        
        # Final fallback
        st.info("""
        ### MantisAI is temporarily unavailable
        
        Please ensure:
        1. OPENAI_API_KEY is configured in environment
        2. All required modules are properly installed
        3. Check application logs for details
        
        Contact support if issues persist.
        """)