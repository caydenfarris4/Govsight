"""
Annotations System - Main Application

A comprehensive document annotation system with AI-powered suggestions,
collaborative features, and export capabilities.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import base64
import io

# Page configuration
st.set_page_config(
    page_title="Annotations System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for annotation interface
st.markdown("""
<style>
    .annotation-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        background: #f9f9f9;
    }
    
    .annotation-highlight {
        background-color: #ffeb3b;
        padding: 2px 4px;
        border-radius: 3px;
    }
    
    .annotation-comment {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 10px;
        margin: 5px 0;
    }
    
    .annotation-tag {
        display: inline-block;
        background: #4caf50;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if "annotations" not in st.session_state:
        st.session_state.annotations = []
    if "current_document" not in st.session_state:
        st.session_state.current_document = None
    if "annotation_mode" not in st.session_state:
        st.session_state.annotation_mode = "highlight"

def render_sidebar():
    """Render the sidebar with annotation tools"""
    st.sidebar.title(" Annotation Tools")
    
    # Document upload
    st.sidebar.subheader("Document Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Choose a document",
        type=['txt', 'pdf', 'docx'],
        help="Upload a document to annotate"
    )
    
    if uploaded_file:
        st.session_state.current_document = uploaded_file
    
    # Annotation mode selection
    st.sidebar.subheader("Annotation Mode")
    annotation_mode = st.sidebar.selectbox(
        "Select annotation type",
        ["highlight", "comment", "tag", "question", "suggestion"]
    )
    st.session_state.annotation_mode = annotation_mode
    
    # Annotation categories
    st.sidebar.subheader("Categories")
    categories = st.sidebar.multiselect(
        "Filter by category",
        ["Important", "Review", "Question", "Suggestion", "Error", "Reference"],
        default=["Important"]
    )
    
    return categories

def render_document_viewer():
    """Render the main document viewer"""
    st.header("Document Viewer")
    
    if st.session_state.current_document is None:
        st.info("Upload a document to start annotating")
        return
    
    # Display document content
    try:
        if st.session_state.current_document.type == "text/plain":
            content = str(st.session_state.current_document.read(), "utf-8")
            st.text_area("Document Content", content, height=400, disabled=True)
        elif st.session_state.current_document.type == "application/pdf":
            st.info("PDF viewer will be implemented with annotation overlay")
            # Placeholder for PDF content
            st.text_area("PDF Content (placeholder)", 
                        "PDF content would be displayed here with annotation capabilities", 
                        height=400, disabled=True)
        else:
            st.warning("Document type not yet supported for annotation")
    except Exception as e:
        st.error(f"Error loading document: {e}")

def render_annotation_panel():
    """Render the annotation creation panel"""
    st.subheader("Add Annotation")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Text selection (placeholder for now)
        selected_text = st.text_input("Selected text", placeholder="Select text to annotate")
        
        # Annotation content
        annotation_content = st.text_area(
            "Annotation content",
            placeholder=f"Add your {st.session_state.annotation_mode} here..."
        )
    
    with col2:
        # Annotation metadata
        category = st.selectbox("Category", 
                               ["Important", "Review", "Question", "Suggestion", "Error", "Reference"])
        
        # AI suggestion button
        if st.button(" Get AI Suggestion"):
            if selected_text:
                ai_suggestion = get_ai_annotation_suggestion(selected_text)
                if ai_suggestion:
                    annotation_content = ai_suggestion
                    st.rerun()
    
    # Add annotation button
    if st.button("Add Annotation", type="primary"):
        if annotation_content and selected_text:
            add_annotation(selected_text, annotation_content, category, st.session_state.annotation_mode)
            st.success("Annotation added successfully!")
            st.rerun()
        else:
            st.warning("Please select text and add annotation content")

def get_ai_annotation_suggestion(text):
    """Get AI-powered annotation suggestions"""
    try:
        # Import OpenAI here to avoid issues if not available
        from openai import OpenAI
        import os
        
        if not os.getenv("OPENAI_API_KEY"):
            st.warning("OpenAI API key not configured for AI suggestions")
            return None
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""
        Analyze this text and provide a helpful annotation suggestion:
        
        Text: "{text}"
        
        Provide a concise, helpful annotation that could include:
        - Key insights or interpretations
        - Questions for further consideration
        - Connections to related concepts
        - Potential improvements or suggestions
        
        Keep the response under 100 words.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"AI suggestion error: {e}")
        return None

def add_annotation(text, content, category, annotation_type):
    """Add a new annotation"""
    annotation = {
        "id": len(st.session_state.annotations) + 1,
        "text": text,
        "content": content,
        "category": category,
        "type": annotation_type,
        "timestamp": datetime.now().isoformat(),
        "author": "Current User"  # This would be dynamic in a real system
    }
    
    st.session_state.annotations.append(annotation)

def render_annotations_list():
    """Render the list of existing annotations"""
    st.subheader("Annotations")
    
    if not st.session_state.annotations:
        st.info("No annotations yet. Start by selecting text and adding annotations.")
        return
    
    for annotation in st.session_state.annotations:
        with st.expander(f"{annotation['type'].title()}: {annotation['text'][:50]}..."):
            st.markdown(f"**Category:** {annotation['category']}")
            st.markdown(f"**Text:** {annotation['text']}")
            st.markdown(f"**Annotation:** {annotation['content']}")
            st.markdown(f"**Created:** {annotation['timestamp']}")
            st.markdown(f"**Author:** {annotation['author']}")
            
            # Edit/Delete buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"Edit", key=f"edit_{annotation['id']}"):
                    st.info("Edit functionality will be implemented")
            with col2:
                if st.button(f"Delete", key=f"delete_{annotation['id']}"):
                    st.session_state.annotations.remove(annotation)
                    st.rerun()

def render_export_section():
    """Render annotation export options"""
    st.subheader("Export Annotations")
    
    if not st.session_state.annotations:
        st.info("No annotations to export")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export as JSON"):
            json_data = json.dumps(st.session_state.annotations, indent=2)
            st.download_button(
                "Download JSON",
                json_data,
                file_name=f"annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("Export as CSV"):
            df = pd.DataFrame(st.session_state.annotations)
            csv_data = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv_data,
                file_name=f"annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col3:
        if st.button("Generate Report"):
            report = generate_annotation_report()
            st.download_button(
                "Download Report",
                report,
                file_name=f"annotation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )

def generate_annotation_report():
    """Generate a comprehensive annotation report"""
    report = f"""# Annotation Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total Annotations: {len(st.session_state.annotations)}
- Document: {st.session_state.current_document.name if st.session_state.current_document else 'No document'}

## Annotations by Category
"""
    
    # Group by category
    category_counts = {}
    for annotation in st.session_state.annotations:
        category = annotation['category']
        category_counts[category] = category_counts.get(category, 0) + 1
    
    for category, count in category_counts.items():
        report += f"- {category}: {count}\n"
    
    report += "\n## Detailed Annotations\n\n"
    
    for i, annotation in enumerate(st.session_state.annotations, 1):
        report += f"""### {i}. {annotation['type'].title()} - {annotation['category']}
**Text:** {annotation['text']}
**Annotation:** {annotation['content']}
**Created:** {annotation['timestamp']}
**Author:** {annotation['author']}

---

"""
    
    return report

def main():
    """Main application function"""
    st.title(" Annotations System")
    st.markdown("Collaborative document annotation with AI-powered suggestions")
    
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar
    categories = render_sidebar()
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["Document", "Annotate", "Manage"])
    
    with tab1:
        render_document_viewer()
    
    with tab2:
        render_annotation_panel()
    
    with tab3:
        col1, col2 = st.columns([2, 1])
        with col1:
            render_annotations_list()
        with col2:
            render_export_section()

if __name__ == "__main__":
    main()