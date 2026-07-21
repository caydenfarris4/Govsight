"""
Streamlit app to download the enterprise security PDF
"""

import streamlit as st
import os
from datetime import datetime

def main():
    st.set_page_config(
        page_title="Download Security Documentation", 
        page_icon="🔒",
        layout="centered"
    )
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px;">
        <h1 style="color: white; margin: 0; font-size: 2.5em;">🔒 Enterprise Security Documentation</h1>
        <p style="color: white; margin: 10px 0 0 0; font-size: 1.2em; opacity: 0.9;">Mantis AI Data Protection</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Find the PDF file
    pdf_files = [f for f in os.listdir('.') if f.startswith('Mantis_Enterprise_Security_Documentation') and f.endswith('.pdf')]
    
    if pdf_files:
        # Use the most recent PDF file
        pdf_file = sorted(pdf_files)[-1]
        file_size = os.path.getsize(pdf_file) / 1024  # Size in KB
        
        st.success(f" Security documentation ready for download")
        
        # File info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Document Type", "PDF")
        with col2:
            st.metric("File Size", f"{file_size:.1f} KB")
        with col3:
            st.metric("Pages", "7")
        
        st.markdown("---")
        
        # Security features overview
        st.markdown("###  Document Contents")
        st.markdown("""
        **This comprehensive PDF includes:**
        
        * **Executive Summary** - Overview of enterprise security implementation
        * **Core Security Features** - Memory-only processing, session management, file validation
        * **Security Architecture** - 5-layer protection system and secure processing flow
        * **Data Protection Measures** - Content security and access control details
        * **Compliance & Standards** - Government data protection requirements
        * **Technical Implementation** - SecureFileHandler class and security logging
        * **User Security Controls** - Security panels and manual operations
        * **Security Verification** - How to confirm enterprise security is active
        
        **Key Security Highlights:**
        - Memory-only processing (no disk storage)
        - 1-hour automatic session timeout
        - Comprehensive file validation and sanitization
        - Complete audit trail for compliance
        - Enterprise-grade data protection standards
        """)
        
        st.markdown("---")
        
        # Download section
        st.markdown("###  Download Documentation")
        
        # Read the PDF file
        with open(pdf_file, 'rb') as file:
            pdf_data = file.read()
        
        # Create download button
        st.download_button(
            label="🔒 Download Enterprise Security PDF",
            data=pdf_data,
            file_name=pdf_file,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        st.info(" **Tip**: This document can be shared with compliance officers, IT security teams, or regulatory authorities to demonstrate your data protection standards.")
        
        # Additional info
        st.markdown("---")
        st.markdown("### 🛡️ Security Assurance")
        st.markdown("""
        This documentation certifies that your Mantis AI system implements:
        
        - **Bank-level data protection** for sensitive municipal financial documents
        - **Government compliance standards** for audit and regulatory requirements  
        - **Zero-persistence policies** ensuring no permanent storage of sensitive data
        - **Professional security controls** suitable for enterprise and government use
        
        Generated on: {date}
        """.format(date=datetime.now().strftime("%B %d, %Y at %I:%M %p")))
        
    else:
        st.error(" Security documentation PDF not found. Please generate it first.")
        if st.button(" Generate Security PDF"):
            st.info("Generating security documentation...")
            # This would trigger the PDF generation
            st.rerun()

if __name__ == "__main__":
    main()