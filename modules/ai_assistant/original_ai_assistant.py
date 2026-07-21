"""
AI Assistant Module

This module handles all functionality related to the AI Assistant tab, including:
- Conversational AI interface for budget questions
- Document analysis for policy questions
- AI-powered budget insights and recommendations
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from common_utils import get_db_path_for_org
from ai_hub import ask_ai, analyze_document
from accessibility_helper import (
    create_accessible_button, create_accessible_text_input, 
    create_accessible_dataframe, announce_to_screen_reader
)

def generate_ai_commentary(df, prompt=None, sources=None):
    """
    Generate AI commentary on the data with optional regulatory context
    
    Args:
        df (DataFrame): pandas DataFrame with data to analyze
        prompt (str, optional): Specific prompt or question. Defaults to None.
        sources (list, optional): List of regulatory sources to include. Defaults to None.
        
    Returns:
        str: AI-generated commentary on the data
    """
    if sources is None:
        sources = []
    
    # Use centralized AI Hub function
    if prompt:
        return ask_ai(prompt=prompt, df=df, sources=sources)
    else:
        return ask_ai(
            prompt="Provide insights and analysis on this municipal financial data", 
            df=df, 
            sources=sources
        )

def call_ai_with_context(prompt: str = "", df: pd.DataFrame = None, sources: list = None, model="gpt-4o", max_tokens=600) -> str:
    """
    Call AI with enhanced context from data and regulatory sources (using the centralized AI Hub)
    
    Args:
        prompt (str): The user prompt or question
        df (pd.DataFrame, optional): Dataframe with relevant data
        sources (list, optional): List of regulatory sources to include
        model (str, optional): AI model to use
        max_tokens (int, optional): Maximum tokens for response
        
    Returns:
        str: AI response incorporating context from data and regulatory sources
    """
    if sources is None:
        sources = []
    
    return ask_ai(prompt=prompt, df=df, sources=sources, model=model, max_tokens=max_tokens)

def render_ai_assistant(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the AI Assistant tab
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    st.title(" AI Assistant")
    st.markdown(f"""
    Welcome to the {org_display_name} AI Assistant! This tool provides intelligent analysis and insights 
    about your municipal financial data. Ask questions about budgets, departments, or upload documents for analysis.
    """)
    
    # Initialize session state for chat history if not exists
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Tabs for different AI assistant modes
    tab1, tab2, tab3 = st.tabs(["💬 Ask a Question", " Data Analysis", " Document Analysis"])
    
    with tab1:
        st.subheader("Ask about Budget & Finance")
        
        # Create accessible chat interface
        for i, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                st.markdown(f"""
                <div role="log" aria-label="User message {i+1}" 
                     style='background-color:#d1ecf1; color:#0c5460; padding:15px; border-radius:8px; margin-bottom:10px; border: 2px solid #bee5eb;'>
                    <strong>You:</strong> {message['content']}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div role="log" aria-label="AI Assistant response {i+1}" 
                     style='background-color:#003080; color:white; padding:15px; border-radius:8px; margin-bottom:10px; border: 2px solid #ffffff;'>
                    <strong>AI Assistant:</strong> {message['content']}
                </div>""", unsafe_allow_html=True)
        
        # Add source selection expander
        with st.expander("Regulatory Source Settings", expanded=False):
            st.subheader("Data Sources Configuration")
            
            # External sources toggle
            use_external = st.checkbox("Use External Regulatory Sources", 
                                      value=st.session_state.get('use_external_regulatory_sources', False),
                                      help="Connect to external regulatory websites like GASB, IRS, and state websites")
            
            if use_external != st.session_state.get('use_external_regulatory_sources', False):
                st.session_state['use_external_regulatory_sources'] = use_external
            
            # Source selection
            st.write("Select regulatory sources to include:")
            
            # Static sources
            col1, col2 = st.columns(2)
            with col1:
                use_gasb = st.checkbox("GASB Standards", value=True, 
                                     help="Government Accounting Standards Board pronouncements")
                use_gaap = st.checkbox("GAAP Principles", value=True,
                                     help="Generally Accepted Accounting Principles")
            
            with col2:
                use_budget = st.checkbox("Budget Laws", value=True,
                                      help="Municipal budget laws and requirements")
                use_procurement = st.checkbox("Procurement Rules", value=True,
                                           help="Government procurement and contracting requirements")
            
            # Store selected sources in session state
            selected_sources = []
            if use_gasb: selected_sources.append("gasb")
            if use_gaap: selected_sources.append("gaap")
            if use_budget: selected_sources.append("budget_law")
            if use_procurement: selected_sources.append("procurement")
            
            st.session_state["selected_sources"] = selected_sources
        
        # Load data for context
        try:
            db_path = get_db_path_for_org(org)
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query("SELECT * FROM DepartmentPerformance LIMIT 10", conn)
            conn.close()
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            df = pd.DataFrame()
        
        # Input for user question with accessibility
        user_question = create_accessible_text_input(
            label="Ask me anything about your budget data:",
            key="ai_question_input",
            help_text="Type your question about budget data, departments, or financial analysis"
        )
        
        if user_question:
            user_question = st.text_area(
                "Question details:", 
                value=user_question,
                height=100, 
                placeholder="e.g., Which department spent the most this year? What are the budget variances?",
                label_visibility="collapsed"
            )
        
        if create_accessible_button("Ask AI", key="ask_ai_btn", help_text="Submit your question to the AI assistant") and user_question:
            # Get selected sources from session state
            sources = st.session_state.get("selected_sources", [])
            
            # Add question to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            
            # Announce to screen readers
            announce_to_screen_reader("Processing your question with AI assistant")
            
            with st.spinner("Analyzing your question..."):
                try:
                    # Generate AI response using the centralized AI Hub
                    # Ensure df is properly handled for AI context
                    valid_df = df if df is not None and not df.empty else pd.DataFrame()
                    ai_response = call_ai_with_context(
                        prompt=user_question,
                        df=valid_df,
                        sources=sources or []
                    )
                    
                    # Add response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    
                    # Announce completion to screen readers
                    announce_to_screen_reader("AI response received and displayed")
                    
                    # Refresh the page to show the new messages
                    st.rerun()
                    
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "quota" in error_msg.lower():
                        st.error("🔑 AI service quota exceeded. Please check your OpenAI account billing or provide a new API key with available credits.")
                        st.info(" You can still use other features like data visualization, exports, and manual analysis while the AI service is unavailable.")
                    elif "401" in error_msg or "unauthorized" in error_msg.lower():
                        st.error("🔑 AI service authentication failed. Please verify your API key is correct and active.")
                    elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                        st.error("🌐 Network connection issue. Please check your internet connection and try again.")
                    else:
                        st.error(f"AI service temporarily unavailable: {error_msg}")
                        st.info(" Please try again in a moment. Other features remain fully functional.")
        
        # Clear chat button
        if st.button("Clear Conversation"):
            st.session_state.chat_history = []
            st.rerun()
    
    with tab2:
        st.subheader("Data Analysis & Insights")
        
        # Load available data
        try:
            db_path = get_db_path_for_org(org)
            conn = sqlite3.connect(db_path)
            
            # Get available tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [table[0] for table in cursor.fetchall()]
            
            if tables:
                selected_table = st.selectbox("Select data to analyze:", tables, index=0)
                
                # Load data from selected table
                query = f"SELECT * FROM {selected_table}"
                analysis_df = pd.read_sql_query(query, conn)
                
                st.write(f"**Data Analysis for {selected_table}:**")
                
                # Use advanced filtering for data analysis
                from advanced_filters import create_advanced_filter_component, display_filtered_dataframe, create_summary_metrics
                
                # Apply advanced filtering
                filtered_analysis_df = create_advanced_filter_component(
                    df=analysis_df,
                    key_prefix=f"ai_analysis_{selected_table}",
                    items_per_page=20
                )
                
                # Display summary metrics
                create_summary_metrics(filtered_analysis_df, analysis_df)
                
                # Display the filtered data
                display_filtered_dataframe(
                    filtered_analysis_df,
                    key_prefix=f"ai_display_{selected_table}",
                    height=300
                )
                
                # Analysis options
                analysis_type = st.selectbox("Type of Analysis:", [
                    "General Summary",
                    "Budget Variance Analysis", 
                    "Department Performance Review",
                    "Financial Trend Analysis",
                    "Custom Analysis"
                ])
                
                custom_prompt = ""
                if analysis_type == "Custom Analysis":
                    custom_prompt = st.text_area("Describe what you want to analyze:", 
                                                height=100,
                                                placeholder="e.g., Focus on departments with highest overspend...")
                
                if st.button("Generate Analysis"):
                    with st.spinner("Generating AI analysis..."):
                        try:
                            # Create analysis prompt based on type
                            if analysis_type == "Custom Analysis" and custom_prompt:
                                prompt = custom_prompt
                            else:
                                prompt = f"Perform a {analysis_type.lower()} on this municipal financial data"
                            
                            # Get selected sources from session state
                            sources = st.session_state.get("selected_sources", [])
                            
                            # Generate analysis using centralized AI Hub
                            analysis_result = call_ai_with_context(
                                prompt=prompt,
                                df=analysis_df,
                                sources=sources
                            )
                            
                            st.subheader("AI Analysis Results")
                            st.markdown(analysis_result)
                            
                        except Exception as e:
                            st.error(f"Error generating analysis: {str(e)}")
            else:
                st.warning("No data tables found in the database.")
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error loading data for analysis: {str(e)}")
    
    with tab3:
        st.subheader("Document Analysis")
        
        # File upload
        uploaded_file = st.file_uploader("Upload a document for AI analysis", 
                                       type=['pdf', 'txt'], 
                                       help="Upload PDF or text files for analysis")
        
        if uploaded_file:
            # Extract text from document
            document_text = extract_text_from_document(uploaded_file)
            
            if document_text:
                st.success("Document uploaded successfully!")
                
                # Show document preview
                with st.expander("Document Preview", expanded=False):
                    st.text_area("Document Content Preview:", 
                               value=document_text[:1000] + "..." if len(document_text) > 1000 else document_text,
                               height=200, disabled=True)
                
                # Analysis type selection
                doc_analysis_type = st.selectbox("Analysis Type:", [
                    "General Summary",
                    "Policy Analysis",
                    "Compliance Review",
                    "Budget Impact Assessment",
                    "Custom Document Analysis"
                ])
                
                doc_prompt = ""
                if doc_analysis_type == "Custom Document Analysis":
                    doc_prompt = st.text_area("Custom analysis instructions:", 
                                            height=100,
                                            placeholder="e.g., Focus on financial implications...")
                
                if st.button("Analyze Document"):
                    with st.spinner("Analyzing document..."):
                        try:
                            # Use the centralized document analysis function
                            analysis_prompt = doc_prompt if doc_analysis_type == "Custom Document Analysis" else doc_analysis_type
                            doc_analysis = analyze_document(document_text, analysis_prompt)
                            
                            st.subheader("Document Analysis Results")
                            st.markdown(doc_analysis)
                        except Exception as e:
                            st.error(f"Error analyzing document: {str(e)}")
            else:
                st.error("Could not extract text from the document. Please check the file format.")

def extract_text_from_document(uploaded_file):
    """
    Extract text from an uploaded document (PDF or TXT) with comprehensive validation
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        str: Extracted text from the document
    """
    if not uploaded_file:
        st.error("No file was uploaded.")
        return None
    
    # File size validation (limit to 10MB)
    if uploaded_file.size > 10 * 1024 * 1024:
        st.error("File size exceeds 10MB limit. Please upload a smaller file.")
        return None
    
    # File type validation
    allowed_types = ["application/pdf", "text/plain", "text/csv"]
    if uploaded_file.type not in allowed_types:
        st.error(f"Unsupported file type: {uploaded_file.type}. Please upload PDF or text files only.")
        return None
    
    try:
        if uploaded_file.type == "application/pdf":
            # Extract text from PDF
            try:
                import PyPDF2
                from io import BytesIO
                
                # Reset file pointer
                uploaded_file.seek(0)
                pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
                
                if len(pdf_reader.pages) == 0:
                    st.error("PDF file appears to be empty or corrupted.")
                    return None
                
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        st.warning(f"Could not extract text from page {page_num + 1}: {str(e)}")
                        continue
                
                if not text.strip():
                    st.error("No readable text found in the PDF. The file may be image-based or corrupted.")
                    return None
                    
                return text.strip()
                
            except ImportError:
                st.error("PDF processing library not available. Please upload a text file instead.")
                return None
        else:
            # Handle text files with encoding detection
            try:
                # Reset file pointer
                uploaded_file.seek(0)
                text = uploaded_file.read().decode('utf-8')
                
                if not text.strip():
                    st.error("Text file appears to be empty.")
                    return None
                    
                return text.strip()
                
            except UnicodeDecodeError:
                try:
                    # Try alternative encoding
                    uploaded_file.seek(0)
                    text = uploaded_file.read().decode('latin-1')
                    return text.strip()
                except Exception as e:
                    st.error(f"Could not decode text file. Please ensure it's in UTF-8 or Latin-1 encoding: {str(e)}")
                    return None
                    
    except Exception as e:
        st.error(f"Unexpected error processing file: {str(e)}")
        return None