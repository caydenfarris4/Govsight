"""
Mantis Chat Interface - ChatGPT-style conversational interface
Provides a modern chat experience with conversation history and persistence
"""

import streamlit as st
import asyncio
import uuid
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict
from .mantis_ai_engine import MantisAI
from .secure_file_handler import SecureFileHandler
from .intelligent_support_assistant import integrate_support_with_mantis_chat, render_support_response

# File processing imports
try:
    import PyPDF2
except ImportError:
    st.error("PyPDF2 not installed. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "PyPDF2"])
    import PyPDF2

def render_mantis_chat_interface(org: str = "cityA"):
    """
    Render the ChatGPT-style interface for Mantis AI
    Always starts with a fresh conversation, similar to ChatGPT behavior
    """
    # Initialize session state - Always start fresh like ChatGPT
    if 'mantis_ai' not in st.session_state:
        st.session_state.mantis_ai = MantisAI()
    
    # Initialize secure file handler
    if 'secure_file_handler' not in st.session_state:
        st.session_state.secure_file_handler = SecureFileHandler()
    
    # Initialize support assistant
    if 'mantis_support_assistant' not in st.session_state:
        st.session_state.mantis_support_assistant = integrate_support_with_mantis_chat()
    
    # Always reset to new conversation when entering Mantis (ChatGPT behavior)
    if 'mantis_fresh_start' not in st.session_state:
        st.session_state.mantis_fresh_start = True
    
    # Initialize conversation state if not exists or force fresh start
    if 'current_conversation_id' not in st.session_state or st.session_state.mantis_fresh_start:
        st.session_state.current_conversation_id = None
        st.session_state.conversation_messages = []
        st.session_state.mantis_fresh_start = False  # Reset flag after initial load
    
    mantis_ai = st.session_state.mantis_ai
    
    # Sidebar with conversation history
    with st.sidebar:
        st.markdown("### Mantis AI")
        st.markdown("*Your Financial Intelligence Hub*")
        
        # New conversation button
        if st.button("+ New Conversation", use_container_width=True):
            st.session_state.current_conversation_id = None
            st.session_state.conversation_messages = []
            st.session_state.mantis_fresh_start = False  # User manually started new conversation
            # Ensure we stay on the Mantis tab
            st.session_state.selected_tab = "Mantis"
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Chat History")
        
        # Load and display conversation history
        conversations = mantis_ai.load_conversations()
        
        if conversations:
            for conv in conversations:
                # Format date
                try:
                    date_obj = datetime.fromisoformat(conv['updated_at'])
                    date_str = date_obj.strftime("%m/%d %H:%M")
                except:
                    date_str = "Recent"
                
                # Truncate title
                display_title = conv['title'][:30] + "..." if len(conv['title']) > 30 else conv['title']
                
                if st.button(
                    f"{display_title}\n*{date_str}*",
                    key=f"conv_{conv['id']}",
                    use_container_width=True
                ):
                    st.session_state.current_conversation_id = conv['id']
                    st.session_state.conversation_messages = mantis_ai.load_conversation_messages(conv['id'])
                    st.session_state.mantis_fresh_start = False  # User selected existing conversation
                    st.rerun()
        else:
            st.info("No previous conversations")
        

    
    # Main chat interface with file upload
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px;">
        <h1 style="color: white; margin: 0; font-size: 3em;">Mantis</h1>
        <p style="color: white; margin: 10px 0 0 0; font-size: 1.3em; opacity: 0.9;">AI Financial Intelligence Hub</p>
        <p style="color: white; margin: 5px 0 0 0; font-size: 1em; opacity: 0.7;">Comprehensive analysis • Strategic insights • Document analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get secure file handler
    secure_handler = st.session_state.secure_file_handler
    
    # Check for session timeout
    if secure_handler.enforce_session_timeout():
        st.rerun()
    
    # Security status display
    with st.expander("🔒 Security Information", expanded=False):
        security_status = secure_handler.get_security_status()
        st.markdown("**Data Security Features:**")
        for feature in security_status['security_features']:
            st.markdown(f"• {feature}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max File Size", f"{security_status['max_file_size_mb']}MB")
        with col2:
            st.metric("Session Timeout", f"{security_status['session_timeout']//60} min")
        with col3:
            st.metric("Allowed Types", len(security_status['allowed_types']))
    
    # File upload section
    st.markdown("### Secure Document Upload & Analysis")
    st.info("🔒 **Secure Processing**: Files are processed in memory only and never saved to disk. All uploads are logged for audit purposes.")
    
    uploaded_files = st.file_uploader(
        "Upload PDF or CSV files for analysis",
        type=['pdf', 'csv'],
        accept_multiple_files=True,
        help="Upload sensitive financial documents for AI analysis. Files are processed securely in memory."
    )
    
    # Process uploaded files securely
    if uploaded_files:
        file_contents = {}
        
        # Clear existing files on new upload for security
        if 'uploaded_file_contents' in st.session_state:
            secure_handler.clear_file_data()
        
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            
            # Validate file security
            is_valid, validation_message = secure_handler.validate_file_security(uploaded_file)
            
            if not is_valid:
                st.error(f"Security validation failed for {file_name}: {validation_message}")
                continue
            
            file_type = file_name.split('.')[-1].lower()
            
            try:
                if file_type == 'pdf':
                    # Secure PDF processing
                    file_data = secure_handler.process_pdf_securely(uploaded_file)
                elif file_type == 'csv':
                    # Secure CSV processing
                    file_data = secure_handler.process_csv_securely(uploaded_file)
                
                if 'error' not in file_data:
                    file_contents[file_name] = file_data
                else:
                    st.error(f"Error processing {file_name}: {file_data['error']}")
                    
            except Exception as e:
                st.error(f"Critical error processing {file_name}: {str(e)}")
                secure_handler.log_file_access("CRITICAL_ERROR", file_name)
        
        # Store file contents securely in session state
        if file_contents:
            st.session_state.uploaded_file_contents = file_contents
            st.session_state.file_upload_timestamp = datetime.now().isoformat()
            
            # Display file summaries with security indicators
            st.success(f" Successfully processed {len(file_contents)} file(s) securely")
            
            for file_name, file_data in file_contents.items():
                with st.expander(f"🔒 {file_name} (Secure)", expanded=False):
                    if file_data['type'] == 'pdf':
                        st.write(f"**Pages:** {file_data.get('pages', 'N/A')}")
                        st.write(f"**Security Hash:** {file_data.get('security_hash', 'N/A')}")
                        content_preview = file_data.get('content', '')[:200]
                        st.write(f"**Content Preview:** {content_preview}...")
                        st.caption(" Full document content available for AI analysis")
                        
                    elif file_data['type'] == 'csv':
                        st.write(f"**Rows:** {file_data.get('rows', 0):,}")
                        st.write(f"**Columns:** {len(file_data.get('columns', []))}")
                        st.write(f"**Security Hash:** {file_data.get('security_hash', 'N/A')}")
                        st.write(f"**Summary:** {file_data.get('summary', 'N/A')}")
                        
                        # Show sample data if available
                        if 'content' in file_data and isinstance(file_data['content'], pd.DataFrame):
                            st.caption(" Sample Data (first 3 rows):")
                            st.dataframe(file_data['content'].head(3))
                        st.caption(" Full dataset available for AI analysis")
                    
                    st.caption(f"🕒 Processed: {file_data.get('processed_at', 'Unknown')}")
        
        # Security cleanup options
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All Files (Security)", type="secondary"):
                secure_handler.clear_file_data()
                st.success("All uploaded files cleared securely from memory")
                st.rerun()
        with col2:
            if 'uploaded_file_contents' in st.session_state:
                files_count = len(st.session_state.uploaded_file_contents)
                st.info(f" {files_count} file(s) in secure memory")
    
    # Simplified CSS for Mantis chat input positioning
    st.markdown("""
    <style>
    /* Mantis chat input styling - simpler approach */
    .stChatInput {
        position: sticky !important;
        bottom: 0 !important;
        z-index: 100 !important;
        background: white !important;
        border-top: 2px solid #667eea !important;
        padding: 15px 0 !important;
        margin-top: 20px !important;
        box-shadow: 0 -4px 12px rgba(102, 126, 234, 0.15) !important;
    }
    
    /* Style the Mantis input field */
    .stChatInput input {
        border-radius: 25px !important;
        border: 2px solid #667eea !important;
        padding: 14px 24px !important;
        font-size: 16px !important;
        background: #f8f9ff !important;
        transition: all 0.3s ease !important;
    }
    
    .stChatInput input:focus {
        border-color: #764ba2 !important;
        background: white !important;
        box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.1) !important;
        outline: none !important;
    }
    
    /* Ensure content doesn't overlap */
    .main .block-container {
        padding-bottom: 100px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display conversation messages
        if st.session_state.conversation_messages:
            for message in st.session_state.conversation_messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                elif message["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
        else:
            # Welcome message for new conversations
            with st.chat_message("assistant"):
                st.markdown(f"""
Welcome to Mantis! I'm your intelligent AI assistant for all of your financial needs.

How I can help you today:

• **Secure Document Analysis** - Upload PDF reports or CSV data files for secure, memory-only analysis and insights
• **Translate Accounting into Action** - Turn your financial data into management insights, trends, and recommendations
• **Budget Analysis & Forecasting** - Analyze variances, project future spending, and identify over/under-spending patterns
• **Scenario Intelligence** - Access and analyze your saved budget scenarios with comprehensive impact analysis
• **Real-Time Grant Intelligence** - Search federal and state grant databases, get AI-powered recommendations based on your needs
• **Department Performance** - Evaluate departmental efficiency and identify cost-saving opportunities
• **Intelligent Support** - Get instant help with GovSight features, processes, and troubleshooting

I can now securely analyze your uploaded documents! Upload PDF or CSV files above - they're processed in memory only for maximum security.

**Need help using GovSight?** Just ask me questions like:
- "How do I create a budget scenario?"
- "Why isn't my data loading?"
- "What charts can I create?"
                """)
    
    # Add spacer for proper spacing above the fixed input
    st.markdown("<div style='height: 100px; width: 100%;'></div>", unsafe_allow_html=True)
    
    # Chat input (Always fixed at viewport bottom)
    if prompt := st.chat_input("Ask Mantis anything about your municipal finances or securely uploaded documents...", key="mantis_chat_input"):
        # Add user message to conversation
        user_message = {"role": "user", "content": prompt}
        st.session_state.conversation_messages.append(user_message)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display AI response
        with st.chat_message("assistant"):
            with st.spinner("Mantis is analyzing your request..."):
                # Initialize support assistant
                support_assistant = integrate_support_with_mantis_chat()
                
                # Check if this is a support request
                intent_analysis = support_assistant.detect_support_intent(prompt)
                
                # Generate response with file context if available
                try:
                    file_context = st.session_state.get('uploaded_file_contents', {})
                    
                    # If this is a support request with high confidence, provide support response
                    if intent_analysis["is_support_request"] and intent_analysis["confidence"] > 0.3:
                        support_response = support_assistant.generate_support_response(prompt, intent_analysis)
                        
                        if support_response:
                            # Display support response
                            render_support_response(support_response)
                            
                            # Also get AI response for additional context
                            ai_response = mantis_ai.generate_response(
                                f"User asked: '{prompt}' - This appears to be a support question about {intent_analysis['primary_intent']}. Please provide additional helpful context and encourage them to explore the relevant features.", 
                                st.session_state.conversation_messages[:-1], 
                                org, 
                                file_context
                            )
                            
                            st.markdown("---")
                            st.markdown("### Additional AI Insights")
                            response = ai_response
                        else:
                            response = mantis_ai.generate_response(prompt, st.session_state.conversation_messages[:-1], org, file_context)
                    else:
                        response = mantis_ai.generate_response(prompt, st.session_state.conversation_messages[:-1], org, file_context)
                    
                    # Check if we should create a visualization
                    should_viz, chart_type, viz_description = mantis_ai.should_create_visualization(prompt, file_context)
                    
                    # Display the text response
                    st.markdown(response)
                    
                    # Create and display visualization if appropriate
                    if should_viz:
                        with st.spinner("Creating visualization..."):
                            try:
                                fig = mantis_ai.create_visualization(viz_description, chart_type)
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Add visualization note to conversation
                                viz_note = f"\n\n*Generated {chart_type} visualization: {viz_description}*"
                                response += viz_note
                            except Exception as viz_error:
                                st.error(f"Visualization error: {str(viz_error)}")
                    
                except Exception as e:
                    response = f"I apologize, but I encountered an error while processing your request: {str(e)}"
                    st.markdown(response)
        
        # Add AI response to conversation
        assistant_message = {"role": "assistant", "content": response}
        st.session_state.conversation_messages.append(assistant_message)
        
        # Save conversation
        if not st.session_state.current_conversation_id:
            st.session_state.current_conversation_id = str(uuid.uuid4())
            # Generate title from first user message
            title = prompt[:50] + "..." if len(prompt) > 50 else prompt
        else:
            title = st.session_state.conversation_messages[0]["content"][:50]
        
        mantis_ai.save_conversation(
            st.session_state.current_conversation_id,
            title,
            st.session_state.conversation_messages
        )
        
        # Rerun to refresh the interface while keeping input at bottom
        st.rerun()

    
    # Quick action buttons
    st.markdown("---")
    st.markdown("### Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Budget Variance Analysis", use_container_width=True):
            quick_prompt = "Show me where departments overspent or underspent their budgets. Highlight the most significant variances and explain what might be causing them."
            # Add user message to conversation
            st.session_state.conversation_messages.append({"role": "user", "content": quick_prompt})
            # Automatically process the prompt and generate AI response
            with st.spinner("Analyzing budget variances..."):
                try:
                    ai_response = mantis_ai.chat(quick_prompt, org=org)
                    st.session_state.conversation_messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    error_msg = f"Error processing quick action: {str(e)}"
                    st.session_state.conversation_messages.append({"role": "assistant", "content": error_msg})
            st.rerun()
    
    with col2:
        if st.button("Visualize Department Data", use_container_width=True):
            quick_prompt = "Create a chart showing department budget vs actual spending comparison. Include a breakdown table with variance percentages."
            st.session_state.conversation_messages.append({"role": "user", "content": quick_prompt})
            with st.spinner("Creating visualizations..."):
                try:
                    ai_response = mantis_ai.chat(quick_prompt, org=org)
                    st.session_state.conversation_messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    error_msg = f"Error processing quick action: {str(e)}"
                    st.session_state.conversation_messages.append({"role": "assistant", "content": error_msg})
            st.rerun()
    
    with col3:
        if st.button("Grant Opportunities", use_container_width=True):
            quick_prompt = "Search for federal and state grants that match our current budget needs and spending patterns. Focus on infrastructure, public safety, and community development opportunities."
            st.session_state.conversation_messages.append({"role": "user", "content": quick_prompt})
            with st.spinner("Searching for grants..."):
                try:
                    ai_response = mantis_ai.chat(quick_prompt, org=org)
                    st.session_state.conversation_messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    error_msg = f"Error processing quick action: {str(e)}"
                    st.session_state.conversation_messages.append({"role": "assistant", "content": error_msg})
            st.rerun()
    
    with col4:
        if st.button("Scenario Analysis", use_container_width=True):
            quick_prompt = "Analyze my saved budget scenarios. Compare their funding mixes, identify risks, and provide recommendations for implementation."
            st.session_state.conversation_messages.append({"role": "user", "content": quick_prompt})
            with st.spinner("Analyzing scenarios..."):
                try:
                    ai_response = mantis_ai.chat(quick_prompt, org=org)
                    st.session_state.conversation_messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    error_msg = f"Error processing quick action: {str(e)}"
                    st.session_state.conversation_messages.append({"role": "assistant", "content": error_msg})
            st.rerun()