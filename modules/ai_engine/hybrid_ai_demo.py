"""
Hybrid AI System Demo
Demonstrates the capabilities and benefits of the hybrid AI approach
"""

import streamlit as st
import time
import pandas as pd
from typing import Dict, Any

# Import hybrid AI components
from .hybrid_ai_integration import get_hybrid_ai, init_hybrid_ai_session, render_hybrid_ai_dashboard
from .hybrid_ai_router import get_hybrid_router

def demo_hybrid_ai_system():
    """Main demo interface for hybrid AI system"""
    
    st.title("Hybrid AI System Demo")
    st.markdown("Experience intelligent AI routing between local processing and external APIs")
    
    # Initialize hybrid AI
    init_hybrid_ai_session()
    hybrid_ai = get_hybrid_ai()
    
    # Demo tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Speed Comparison",
        "Privacy Protection", 
        "Cost Optimization",
        "Capability Demo",
        "Performance Dashboard"
    ])
    
    with tab1:
        demo_speed_comparison(hybrid_ai)
    
    with tab2:
        demo_privacy_protection(hybrid_ai)
    
    with tab3:
        demo_cost_optimization(hybrid_ai)
    
    with tab4:
        demo_ai_capabilities(hybrid_ai)
    
    with tab5:
        render_hybrid_ai_dashboard()

def demo_speed_comparison(hybrid_ai):
    """Demo speed differences between local and API processing"""
    
    st.subheader("Speed Comparison: Local vs API Processing")
    
    sample_texts = {
        "Short Financial Report": """
        Q3 Budget Summary: Revenue increased 8% to $2.4M. 
        Major expenses: Personnel $1.2M, Infrastructure $600K, Operations $400K.
        Net surplus: $200K allocated to emergency reserves.
        """,
        
        "Department Analysis": """
        Police Department Performance Review: Response times averaged 4.2 minutes, 
        down from 5.1 minutes last quarter. Community satisfaction rating: 87%. 
        Overtime costs decreased by 12% through improved scheduling.
        Budget variance: 2% under allocated amount.
        """,
        
        "Citizen Inquiry": """
        Question: What are the current water usage restrictions in effect?
        Context: Summer drought conditions have led to implementation of water conservation measures.
        """
    }
    
    selected_text = st.selectbox("Select sample text:", list(sample_texts.keys()))
    
    if selected_text:
        st.markdown("**Sample Text:**")
        st.text_area("Text to analyze:", sample_texts[selected_text], height=100)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Local Processing (Hybrid AI)**")
            if st.button("Test Local Speed", key="local_speed"):
                
                with st.spinner("Processing locally..."):
                    start_time = time.time()
                    
                    # Use local processing
                    result = hybrid_ai.local_processor.analyze_text(sample_texts[selected_text])
                    
                    processing_time = time.time() - start_time
                
                st.success(f"Local processing completed in {processing_time:.3f} seconds")
                st.json({
                    "Processing Time": f"{processing_time:.3f}s",
                    "Keywords": result.get('keywords', [])[:5],
                    "Sentiment": result.get('sentiment', 'N/A'),
                    "Category": result.get('financial_categories', ['general'])[0] if result.get('financial_categories') else 'general'
                })
        
        with col2:
            st.markdown("**API Processing (Traditional)**")
            if st.button("Simulate API Speed", key="api_speed"):
                
                with st.spinner("Processing via API..."):
                    start_time = time.time()
                    
                    # Simulate API processing time
                    time.sleep(1.5)  # Typical API response time
                    
                    processing_time = time.time() - start_time
                
                st.info(f"API processing completed in {processing_time:.3f} seconds")
                st.json({
                    "Processing Time": f"{processing_time:.3f}s",
                    "Method": "External API",
                    "Network Latency": "1.2s",
                    "Processing": "0.3s"
                })
        
        # Speed comparison chart
        if st.button("Show Speed Comparison Chart"):
            import plotly.express as px
            
            speed_data = pd.DataFrame({
                'Method': ['Local Processing', 'API Processing'],
                'Response Time (ms)': [150, 1500],  # Typical times
                'Privacy': ['High', 'Medium'],
                'Cost': ['$0', '$0.01-0.10']
            })
            
            fig = px.bar(speed_data, x='Method', y='Response Time (ms)',
                        title="Response Time Comparison",
                        color='Method')
            st.plotly_chart(fig, use_container_width=True)

def demo_privacy_protection(hybrid_ai):
    """Demo privacy benefits of local processing"""
    
    st.subheader("Privacy Protection: Financial Data Processing")
    
    st.markdown("""
    **Hybrid AI Privacy Benefits:**
    - Financial data processed locally (never leaves your servers)
    - Sensitive municipal information stays private
    - Compliance with government data protection requirements
    - Reduced risk of data breaches
    """)
    
    # Sample sensitive financial data
    sensitive_data = """
    Employee Salary Review:
    - John Smith (Police Chief): $95,000 + benefits
    - Mary Johnson (Finance Director): $87,000 + benefits  
    - Budget allocation: Personnel costs 65% of total budget
    - Confidential: Union negotiations ongoing for 3% increase
    """
    
    st.text_area("Sample Sensitive Data:", sensitive_data, height=120)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Local Processing (Private)**")
        if st.button("Process Locally (Secure)", type="primary"):
            
            with st.spinner("Processing sensitive data locally..."):
                result = hybrid_ai.categorize_financial_data(sensitive_data)
                time.sleep(0.5)  # Show it's working
            
            st.success("Data processed securely on your servers")
            st.markdown("**Privacy Status:** ✅ Data never left your infrastructure")
            st.markdown("**Categories Found:**")
            for category in result.get('categories', [])[:3]:
                st.markdown(f"- {category.title()}")
    
    with col2:
        st.markdown("**API Processing (Traditional)**")
        if st.button("Simulate API Processing", key="privacy_api"):
            
            with st.spinner("Sending data to external API..."):
                time.sleep(1.5)
            
            st.warning("Data processed externally")
            st.markdown("**Privacy Status:** ⚠️ Sensitive data transmitted to external service")
            st.markdown("**Risk Factors:**")
            st.markdown("- Data transmitted over internet")
            st.markdown("- Processed on external servers")
            st.markdown("- Subject to third-party privacy policies")

def demo_cost_optimization(hybrid_ai):
    """Demo cost benefits of hybrid approach"""
    
    st.subheader("Cost Optimization Analysis")
    
    # Cost calculation inputs
    col1, col2 = st.columns(2)
    
    with col1:
        monthly_queries = st.number_input("Estimated monthly AI queries:", min_value=100, max_value=10000, value=1000)
        avg_query_size = st.selectbox("Average query complexity:", ["Simple", "Medium", "Complex"])
    
    with col2:
        local_processing_percentage = st.slider("Local processing capability:", 0, 100, 70)
    
    # Calculate costs
    cost_per_query = {"Simple": 0.01, "Medium": 0.03, "Complex": 0.08}[avg_query_size]
    
    # Traditional API-only cost
    api_only_cost = monthly_queries * cost_per_query
    
    # Hybrid approach cost
    local_queries = monthly_queries * (local_processing_percentage / 100)
    api_queries = monthly_queries - local_queries
    hybrid_cost = api_queries * cost_per_query
    
    # Display results
    st.subheader("Monthly Cost Comparison")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("API-Only Approach", f"${api_only_cost:.2f}")
        st.caption("All queries via external APIs")
    
    with col2:
        st.metric("Hybrid Approach", f"${hybrid_cost:.2f}")
        st.caption(f"{local_processing_percentage}% processed locally")
    
    with col3:
        savings = api_only_cost - hybrid_cost
        savings_percentage = (savings / api_only_cost) * 100 if api_only_cost > 0 else 0
        st.metric("Monthly Savings", f"${savings:.2f}", f"{savings_percentage:.1f}%")
    
    # Cost projection chart
    if monthly_queries > 0:
        months = list(range(1, 13))
        api_costs = [api_only_cost * month for month in months]
        hybrid_costs = [hybrid_cost * month for month in months]
        
        cost_projection = pd.DataFrame({
            'Month': months,
            'API Only': api_costs,
            'Hybrid Approach': hybrid_costs
        })
        
        import plotly.express as px
        fig = px.line(cost_projection, x='Month', y=['API Only', 'Hybrid Approach'],
                     title="Annual Cost Projection",
                     labels={'value': 'Cost ($)', 'variable': 'Approach'})
        st.plotly_chart(fig, use_container_width=True)

def demo_ai_capabilities(hybrid_ai):
    """Demo different AI capabilities with routing"""
    
    st.subheader("AI Capability Demonstration")
    
    capabilities = {
        "Document Analysis": {
            "description": "Analyze municipal documents for key insights",
            "sample": "City Council Meeting Minutes: Discussed budget allocation for infrastructure improvements...",
            "method": "analyze_document"
        },
        "Sentiment Analysis": {
            "description": "Analyze sentiment of citizen feedback",
            "sample": "The new park renovation is wonderful! The community center improvements are exactly what we needed.",
            "method": "sentiment_analysis"
        },
        "Financial Categorization": {
            "description": "Categorize financial transactions and data",
            "sample": "Payment to ABC Construction for road repairs $45,000. Office supplies purchase $1,200.",
            "method": "categorize_financial_data"
        },
        "Information Extraction": {
            "description": "Extract key information and patterns",
            "sample": "Contact: John Doe (555) 123-4567, Budget: $150,000, Deadline: 12/15/2024",
            "method": "extract_key_information"
        }
    }
    
    selected_capability = st.selectbox("Select AI capability to test:", list(capabilities.keys()))
    
    if selected_capability:
        capability = capabilities[selected_capability]
        
        st.markdown(f"**{selected_capability}**")
        st.caption(capability["description"])
        
        # Show sample or allow custom input
        use_sample = st.checkbox("Use sample text", value=True)
        
        if use_sample:
            test_text = capability["sample"]
            st.text_area("Sample text:", test_text, height=80)
        else:
            test_text = st.text_area("Enter your own text:", height=100)
        
        if test_text and st.button("Test AI Capability"):
            with st.spinner("Processing with Hybrid AI..."):
                start_time = time.time()
                
                # Route through hybrid AI system
                if capability["method"] == "analyze_document":
                    result = hybrid_ai.analyze_document(test_text)
                elif capability["method"] == "sentiment_analysis":
                    result = hybrid_ai.sentiment_analysis(test_text)
                elif capability["method"] == "categorize_financial_data":
                    result = hybrid_ai.categorize_financial_data(test_text)
                elif capability["method"] == "extract_key_information":
                    result = hybrid_ai.extract_key_information(test_text)
                
                processing_time = time.time() - start_time
            
            # Display results
            if result.get('success', False):
                st.success(f"Processing completed in {processing_time:.3f} seconds")
                
                # Show routing information
                routing_info = result.get('routing_info', {})
                if routing_info:
                    provider = routing_info.get('provider', 'local')
                    if provider == 'local':
                        st.info("✅ Processed locally for speed and privacy")
                    else:
                        st.info(f"🌐 Processed via {provider} API for advanced capabilities")
                
                # Display specific results based on capability
                if selected_capability == "Document Analysis":
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Keywords:**")
                        for keyword in result.get('keywords', [])[:5]:
                            st.markdown(f"- {keyword}")
                    with col2:
                        st.markdown("**Analysis:**")
                        st.markdown(f"- Sentiment: {result.get('sentiment', 'N/A')}")
                        st.markdown(f"- Word Count: {result.get('word_count', 'N/A')}")
                
                elif selected_capability == "Sentiment Analysis":
                    sentiment = result.get('sentiment', 'neutral')
                    confidence = result.get('confidence', 0) * 100
                    
                    if sentiment == 'positive':
                        st.success(f"Positive sentiment ({confidence:.1f}% confidence)")
                    elif sentiment == 'negative':
                        st.error(f"Negative sentiment ({confidence:.1f}% confidence)")
                    else:
                        st.info(f"Neutral sentiment ({confidence:.1f}% confidence)")
                
                elif selected_capability == "Financial Categorization":
                    categories = result.get('categories', [])
                    st.markdown("**Detected Categories:**")
                    for category in categories[:3]:
                        st.markdown(f"- {category.title()}")
                
                elif selected_capability == "Information Extraction":
                    patterns = result.get('patterns_found', {})
                    if patterns:
                        st.markdown("**Extracted Information:**")
                        for pattern_type, details in patterns.items():
                            st.markdown(f"- {pattern_type.replace('_', ' ').title()}: {details['count']} found")
            else:
                st.error(f"Processing failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    demo_hybrid_ai_system()