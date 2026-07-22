"""
Mantis Chat Interface V2 - ChatGPT-Style Design
Clean, minimal interface with sidebar chat history and paperclip file uploads
"""

import streamlit as st
import asyncio
import uuid
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import base64

# Import the new orchestrator
from .mantis_ai_orchestrator import MantisAIOrchestrator, MantisResult
from .secure_file_handler import SecureFileHandler


def render_mantis_chat_v2(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the ChatGPT-style Mantis chat interface
    
    Args:
        org: Organization identifier
        org_display_name: Display name for the organization
    """
    
    # Initialize components in session state
    if 'mantis_orchestrator' not in st.session_state:
        st.session_state.mantis_orchestrator = MantisAIOrchestrator(org)
    
    if 'secure_file_handler' not in st.session_state:
        st.session_state.secure_file_handler = SecureFileHandler()
    
    if 'mantis_messages' not in st.session_state:
        st.session_state.mantis_messages = []
    
    if 'mantis_session_id' not in st.session_state:
        st.session_state.mantis_session_id = str(uuid.uuid4())
    
    if 'uploaded_file_data' not in st.session_state:
        st.session_state.uploaded_file_data = {}
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    orchestrator = st.session_state.mantis_orchestrator
    file_handler = st.session_state.secure_file_handler
    
    # ChatGPT-style CSS
    st.markdown("""
    <style>
    /* Hide default Streamlit elements */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stDecoration {display:none;}
    
    /* Clean main container */
    .main .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 1200px;
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        max-width: 70%;
    }
    
    .user-message {
        background-color: #f0f0f0;
        margin-left: auto;
        margin-right: 0;
    }
    
    .assistant-message {
        background-color: #ffffff;
        border: 1px solid #e5e5e5;
        margin-left: 0;
        margin-right: auto;
    }
    
    /* Input area styling */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 1rem;
        border-top: 1px solid #e5e5e5;
        z-index: 1000;
    }
    
    /* Paperclip icon */
    .paperclip-icon {
        cursor: pointer;
        padding: 8px;
        border-radius: 4px;
        color: #666;
    }
    
    .paperclip-icon:hover {
        background-color: #f0f0f0;
    }
    
    /* Sidebar styling */
    .sidebar-chat {
        background-color: #f9f9f9;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        cursor: pointer;
        border: 1px solid transparent;
    }
    
    .sidebar-chat:hover {
        border-color: #d0d0d0;
    }
    
    .sidebar-chat-active {
        border-color: #4A90E2;
        background-color: #e8f4fd;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar for chat history
    with st.sidebar:
        st.markdown("## Chat History")
        
        # New chat button
        if st.button("+ New Chat", use_container_width=True):
            # Save current chat if it has messages
            if st.session_state.mantis_messages:
                save_current_chat()
            
            # Start new chat
            st.session_state.mantis_messages = []
            st.session_state.mantis_session_id = str(uuid.uuid4())
            st.session_state.uploaded_file_data = {}
            orchestrator.context_manager.clear_session(st.session_state.mantis_session_id)
            st.rerun()
        
        st.markdown("---")
        
        # Display chat history
        for i, chat in enumerate(st.session_state.chat_history):
            chat_title = chat.get('title', f"Chat {i+1}")
            if len(chat_title) > 30:
                chat_title = chat_title[:30] + "..."
            
            if st.button(chat_title, key=f"chat_{i}", use_container_width=True):
                # Save current chat first
                if st.session_state.mantis_messages:
                    save_current_chat()
                
                # Load selected chat
                st.session_state.mantis_messages = chat['messages']
                st.session_state.mantis_session_id = chat['session_id']
                st.rerun()
        
        st.markdown("---")

        # Dual AI status panel
        st.markdown("### AI Engine Status")
        gpt_status = "Connected" if orchestrator.client else "No API Key"
        claude_available = (
            hasattr(orchestrator, 'claude_advisor')
            and orchestrator.claude_advisor is not None
            and orchestrator.claude_advisor.available
        )
        claude_status = "Connected" if claude_available else "No API Key"

        st.caption(f"GPT-4o (Financial): {gpt_status}")
        st.caption(f"Claude 3.5 (Technical): {claude_status}")

        if not orchestrator.client:
            st.warning("Configure OPENAI_API_KEY in Secrets")
        if not claude_available:
            st.warning("Configure ANTHROPIC_API_KEY in Secrets")

        if orchestrator.client and claude_available:
            st.success("Dual AI routing active")
            with st.expander("How routing works"):
                st.caption(
                    "Technical / coding questions are handled by Claude (Anthropic). "
                    "Financial analysis, data queries, grants, and GASB compliance use GPT-4o (OpenAI). "
                    "Add 'verify', 'confirm', or 'second opinion' to trigger cross-check mode, "
                    "where both models review each other's answer."
                )
    
    # Main chat area
    st.markdown("# MantisAI")
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display conversation
        if st.session_state.mantis_messages:
            for message in st.session_state.mantis_messages:
                if message['role'] == 'user':
                    with st.chat_message("user"):
                        st.markdown(message['content'])
                elif message['role'] == 'assistant':
                    with st.chat_message("assistant"):
                        if 'result' in message:
                            # Show which AI model handled this response
                            _render_model_badge(message['result'])
                            render_mantis_result(message['result'])
                        else:
                            st.markdown(message.get('content', ''))
        else:
            with st.chat_message("assistant"):
                st.markdown("""Welcome to MantisAI. I'm your municipal financial intelligence assistant.

**What I can do:**
- **Query your data** - Ask about budgets, expenditures, revenue, or any financial metric and I'll pull real numbers from your databases
- **Find grants** - Search federal and state grant opportunities matched to your municipality
- **Detect anomalies** - Identify unusual patterns in transactions, budgets, or vendor payments
- **Run scenarios** - Monte Carlo simulations and economic forecasting for budget planning
- **Analyze documents** - Upload PDFs or CSVs and I'll extract insights
- **Platform support** - Help you navigate GovSight features (Navi, Mantis, Vatica)

Try asking something like:
- "What is our total budget by department?"
- "Find infrastructure grants for water systems"
- "Check for anomalies in our budget data"
- "How do I create a budget scenario in Navi?"
""")
    
    # File upload area (hidden by default)
    if 'show_file_upload' not in st.session_state:
        st.session_state.show_file_upload = False
    
    if st.session_state.show_file_upload:
        with st.expander("File Upload", expanded=True):
            uploaded_files = st.file_uploader(
                "Upload PDF or CSV files",
                type=['pdf', 'csv'],
                accept_multiple_files=True,
                help="Files are processed securely in memory only"
            )
            
            if uploaded_files:
                process_uploaded_files(uploaded_files, file_handler)
            
            # Display uploaded files
            if st.session_state.uploaded_file_data:
                st.markdown("**Uploaded Files:**")
                for filename, file_info in st.session_state.uploaded_file_data.items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if file_info['type'] == 'pdf':
                            st.write(f"{filename} ({file_info.get('pages', 'N/A')} pages)")
                        else:
                            st.write(f"{filename} ({file_info.get('rows', 0):,} rows)")
                    with col2:
                        if st.button("Remove", key=f"remove_{filename}"):
                            del st.session_state.uploaded_file_data[filename]
                            st.rerun()
            
            if st.button("Close", use_container_width=True):
                st.session_state.show_file_upload = False
                st.rerun()
    
    # Input area at bottom
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)  # Spacer
    
    # Create input container
    input_container = st.container()
    with input_container:
        col1, col2 = st.columns([1, 20])
        
        with col1:
            # Paperclip button for file upload
            if st.button("Attach", help="Attach files", key="attach_btn"):
                st.session_state.show_file_upload = not st.session_state.show_file_upload
                st.rerun()
        
        with col2:
            # Chat input
            user_input = st.chat_input("Ask anything about your municipal data...")
            
            if user_input:
                # Add user message
                st.session_state.mantis_messages.append({
                    'role': 'user',
                    'content': user_input,
                    'timestamp': datetime.now()
                })
                
                # Process with orchestrator
                with st.spinner("Thinking..."):
                    try:
                        result = asyncio.run(orchestrator.process_message(
                            user_input,
                            context={
                                'uploaded_files': st.session_state.uploaded_file_data,
                            },
                            session_id=st.session_state.mantis_session_id
                        ))
                        
                        # Add assistant response
                        st.session_state.mantis_messages.append({
                            'role': 'assistant',
                            'result': result,
                            'timestamp': datetime.now()
                        })
                        
                    except Exception as e:
                        st.error(f"Error processing message: {e}")
                        st.session_state.mantis_messages.append({
                            'role': 'assistant',
                            'content': f"I encountered an error: {e}",
                            'timestamp': datetime.now()
                        })
                
                st.rerun()


def save_current_chat():
    """Save the current chat to history"""
    if st.session_state.mantis_messages:
        # Generate title from first user message
        title = "New Chat"
        for msg in st.session_state.mantis_messages:
            if msg['role'] == 'user':
                title = msg['content'][:50]
                break
        
        chat_data = {
            'title': title,
            'messages': st.session_state.mantis_messages.copy(),
            'session_id': st.session_state.mantis_session_id,
            'timestamp': datetime.now()
        }
        
        # Add to history (keep last 10 chats)
        st.session_state.chat_history.append(chat_data)
        if len(st.session_state.chat_history) > 10:
            st.session_state.chat_history = st.session_state.chat_history[-10:]


def process_uploaded_files(uploaded_files, file_handler):
    """Process uploaded files"""
    for uploaded_file in uploaded_files:
        if uploaded_file.name not in st.session_state.uploaded_file_data:
            try:
                file_data = file_handler.process_file_upload(uploaded_file)
                st.session_state.uploaded_file_data[uploaded_file.name] = file_data
                st.success(f"Processed {uploaded_file.name}")
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {e}")


def _render_model_badge(result) -> None:
    """
    Render a small, subtle indicator showing which AI model handled the response.
    Keeps users informed about which engine answered without cluttering the UI.
    """
    if not result or not hasattr(result, 'tool_used'):
        return

    tool = result.tool_used or ""
    metadata = result.metadata or {}

    if "claude" in tool.lower():
        st.caption("Answered by Claude 3.5 Sonnet (technical routing)")
    elif tool == "dual-ai-crosscheck":
        primary = metadata.get("primary_model", "primary model")
        reviewer = metadata.get("reviewer_model", "reviewer")
        st.caption(f"Cross-check: {primary} answered, reviewed by {reviewer}")
    elif tool in ("", "fallback_nlp", "error"):
        pass  # No badge for fallback/error responses
    else:
        st.caption("Answered by GPT-4o (financial routing)")


def render_mantis_result(result: MantisResult, detailed: bool = True):
    """Render a MantisResult in ChatGPT style"""
    if not result:
        return
    
    if result.type == "text":
        st.markdown(result.message)
    
    elif result.type == "table":
        st.markdown(f"**{result.title}**")
        if result.message:
            st.markdown(result.message)
        if result.data is not None:
            st.dataframe(result.data, use_container_width=True)
    
    elif result.type == "chart":
        st.markdown(f"**{result.title}**")
        if result.message:
            st.markdown(result.message)
        if result.figure:
            st.plotly_chart(result.figure, use_container_width=True)
    
    elif result.type == "cards":
        st.markdown(f"**{result.title}**")
        if result.message:
            st.markdown(result.message)
        
        if result.data is not None and isinstance(result.data, list):
            for i, item in enumerate(result.data):
                if isinstance(item, dict):
                    with st.expander(f"{item.get('title', f'Item {i+1}')}"):
                        for key, value in item.items():
                            if key != 'title':
                                st.write(f"**{key}:** {value}")
    
    elif result.type == "error":
        st.error(result.message)
    
    # Show underlying data if requested and available
    if detailed and result.data is not None and result.type != "table":
        with st.expander("View underlying data"):
            if isinstance(result.data, pd.DataFrame):
                st.dataframe(result.data)
            else:
                st.json(result.data)
    
    # Show metadata in minimal way
    if detailed and result.metadata:
        with st.expander("Technical details"):
            st.caption(f"Tool used: {result.tool_used}")
            if hasattr(result, 'execution_time') and result.execution_time:
                st.caption(f"Execution time: {result.execution_time:.2f}s")