"""
Mantis Simple GPT Chat Module
A clean, minimal implementation using only OpenAI's GPT API
"""

import streamlit as st
import os
from openai import OpenAI

def render_mantis_gpt_chat(org="cityA"):
    """
    Render a simple GPT chat interface for Mantis
    
    Args:
        org (str): Organization identifier (for context if needed)
    """
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #1a365d 0%, #2d3748 100%); border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 8px 25px rgba(26, 54, 93, 0.25);">
        <h1 style="color: white; margin: 0; font-family: 'Poppins', sans-serif; font-weight: 600;">MantisAI Assistant</h1>
        <p style="color: rgba(255, 255, 255, 0.9); margin: 10px 0 0 0; font-family: 'Poppins', sans-serif;">Municipal Financial Intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not configured")
        st.info("""
        Please set the OPENAI_API_KEY in your environment variables:
        1. Click on the 'Secrets' icon in the left sidebar
        2. Add a new secret with key: OPENAI_API_KEY
        3. Add your OpenAI API key as the value
        4. Refresh the page
        """)
        return
    
    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {e}")
        return
    
    # Initialize chat history in session state
    if "mantis_messages" not in st.session_state:
        st.session_state.mantis_messages = [
            {
                "role": "system", 
                "content": """You are MantisAI, a CPA-trained financial intelligence assistant for GovSight, a municipal government financial management platform.

You specialize in:
- Municipal finance, fund accounting (GAAP/GASB), and budgeting
- Financial analysis, variance analysis, and forecasting
- Grant opportunities (FEMA, DOT, EPA, HUD, USDA, DOJ) and funding strategies
- Budget optimization, cost reduction, and strategic planning
- Regulatory compliance, audit preparation, and reporting

GovSight Platform Support - you also help users navigate:
- Navi module: Scenario Planner, BI Sandbox, Position-Based Budgeting, Investment Optimizer, Legislative Impact Analysis
- Mantis module: This AI chat, grant search, document analysis, anomaly detection
- Vatica module: Document management, GL drilldowns, regulatory compliance

Provide clear, specific, actionable insights. Use dollar amounts and percentages when appropriate.
Keep responses professional and focused - municipal staff are busy professionals.
Never use emojis in your responses."""
            }
        ]
    
    # Add clear chat button
    col1, col2, col3 = st.columns([3, 1, 1])
    with col3:
        if st.button("Clear Chat", use_container_width=True):
            # Keep only the system message
            st.session_state.mantis_messages = st.session_state.mantis_messages[:1]
            st.rerun()
    
    # Create a container for chat messages
    chat_container = st.container()
    
    # Display chat history (skip system message)
    with chat_container:
        for message in st.session_state.mantis_messages[1:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask Mantis anything about municipal finance..."):
        # Add user message to history
        st.session_state.mantis_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Generate and display assistant response
        with chat_container:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                try:
                    # Create the chat completion with streaming
                    # Cast messages to list to satisfy type checker
                    messages_list = list(st.session_state.mantis_messages)
                    stream = client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages_list,  # type: ignore
                        stream=True,
                        temperature=0.7,
                        max_tokens=2000
                    )
                    
                    # Stream the response
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    
                    # Display final response without cursor
                    message_placeholder.markdown(full_response)
                    
                    # Add assistant response to history
                    st.session_state.mantis_messages.append({"role": "assistant", "content": full_response})
                    
                except Exception as e:
                    error_message = f"Error generating response: {str(e)}"
                    message_placeholder.error(error_message)
                    
                    # Add error message to history for context
                    st.session_state.mantis_messages.append({
                        "role": "assistant", 
                        "content": f"I encountered an error: {str(e)}. Please try again or check your API key."
                    })
    
    # Add helpful information in sidebar
    with st.sidebar:
        st.markdown("### Quick Tips")
        st.markdown("""
        - Ask about budget analysis
        - Request financial forecasts
        - Inquire about grant opportunities
        - Get help with strategic planning
        - Ask for cost optimization ideas
        """)
        
        # Show conversation stats
        num_messages = len(st.session_state.mantis_messages) - 1  # Exclude system message
        if num_messages > 0:
            st.markdown("---")
            st.markdown(f"**Conversation Length:** {num_messages} messages")