"""
Grant Finder - Search and integrate grant opportunities into scenarios
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

def render_grant_finder():
    """Grant finder and integration interface"""
    st.subheader("Grant Opportunity Finder")
    
    st.markdown("""
    Find relevant grant opportunities and integrate them into your budget scenarios.
    Search by category, funding amount, or keywords.
    """)
    
    # Grant search interface
    render_grant_search()
    
    # Selected grants management
    render_selected_grants()

def render_grant_search():
    """Grant search interface"""
    st.markdown("#### Search Grant Opportunities")
    
    # Search filters
    col1, col2 = st.columns(2)
    
    with col1:
        grant_category = st.selectbox(
            "Grant Category",
            options=[
                "All Categories",
                "Infrastructure & Transportation",
                "Public Safety & Emergency Services",
                "Environmental & Sustainability",
                "Education & Community Development",
                "Healthcare & Social Services",
                "Technology & Innovation",
                "Housing & Urban Development",
                "Economic Development",
                "Arts & Culture"
            ],
            key="grant_category"
        )
    
    with col2:
        funding_range = st.selectbox(
            "Funding Range",
            options=[
                "Any Amount",
                "Under $50,000",
                "$50,000 - $250,000",
                "$250,000 - $1,000,000",
                "$1,000,000 - $5,000,000",
                "Over $5,000,000"
            ],
            key="funding_range"
        )
    
    # Keyword search
    search_keywords = st.text_input(
        "Search Keywords",
        placeholder="Enter keywords like 'police equipment', 'road repair', 'water infrastructure'...",
        key="grant_keywords"
    )
    
    # Search button
    if st.button("Search Grants", type="primary"):
        if search_keywords or grant_category != "All Categories":
            grants = search_grants(grant_category, funding_range, search_keywords)
            display_grant_results(grants)
        else:
            st.warning("Please enter search keywords or select a specific category.")

def search_grants(category: str, funding_range: str, keywords: str) -> List[Dict[str, Any]]:
    """Search for grants using real API integration only - NO FALLBACK/FAKE DATA"""
    
    try:
        # Import real grants API
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from modules.external_data.grants_api import get_grants_api
        
        # Get grants API instance
        grants_api = get_grants_api()
        
        # Search all grant sources - only real grants with verified URLs
        real_grants = grants_api.search_all_grants(
            keywords=keywords,
            category=category,
            funding_range=funding_range,
            state="utah"  # Default to Utah, could be made configurable
        )
        
        return real_grants
        
    except Exception as e:
        st.error(f"Unable to connect to grant APIs: {str(e)}")
        st.info("💡 **Grant Search Tips:**\n"
               "- Try searching on [Grants.gov](https://www.grants.gov) directly\n"
               "- Contact your regional federal grants office\n"
               "- Check with state and local funding agencies\n"
               "- Consider reaching out to grant consultants")
        
        # Return empty results instead of fake data - critical requirement
        return []

def funding_range_matches(grant: Dict[str, Any], funding_range: str) -> bool:
    """Check if grant matches funding range criteria"""
    min_amount = grant['min_amount']
    max_amount = grant['max_amount']
    
    if funding_range == "Under $50,000":
        return max_amount < 50000
    elif funding_range == "$50,000 - $250,000":
        return min_amount >= 50000 and max_amount <= 250000
    elif funding_range == "$250,000 - $1,000,000":
        return min_amount >= 250000 and max_amount <= 1000000
    elif funding_range == "$1,000,000 - $5,000,000":
        return min_amount >= 1000000 and max_amount <= 5000000
    elif funding_range == "Over $5,000,000":
        return min_amount > 5000000
    
    return True

def display_grant_results(grants: List[Dict[str, Any]]):
    """Display grant search results"""
    if not grants:
        st.info("No grants found matching your criteria. Try different keywords or broader categories.")
        return
    
    st.markdown(f"#### Search Results ({len(grants)} grants found)")
    
    # Add source indicator
    sources = set(grant.get('source', 'Unknown') for grant in grants)
    if len(sources) > 1:
        st.info(f"🌐 Searching across multiple sources: {', '.join(sources)}")
    
    for i, grant in enumerate(grants):
        # Create a more descriptive header with source
        source = grant.get('source', 'Grant Database')
        header = f"{grant['name']} - {grant['agency']} ({source})"
        
        with st.expander(header):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Category:** {grant['category']}")
                st.markdown(f"**Funding Range:** ${grant['min_amount']:,.0f} - ${grant['max_amount']:,.0f}")
                st.markdown(f"**Deadline:** {grant['deadline'].strftime('%B %d, %Y')}")
                st.markdown(f"**Description:** {grant['description']}")
                st.markdown(f"**Eligibility:** {grant['eligibility']}")
                
                if grant['match_required']:
                    st.markdown(f"**Match Required:** {grant['match_percentage']}%")
                else:
                    st.markdown("**Match Required:** No")
                
                # Add source and URL if available
                if 'url' in grant and grant['url']:
                    st.markdown(f"**More Info:** [View Grant Details]({grant['url']})")
            
            with col2:
                if st.button("Add to Scenario", key=f"add_grant_{i}"):
                    add_grant_to_scenario(grant)
                
                # Add quick info button for grant details
                if st.button("Quick Info", key=f"info_grant_{i}"):
                    st.info(f"💰 **{grant['name']}**\n\n"
                           f"**Agency:** {grant['agency']}\n"
                           f"**Range:** ${grant['min_amount']:,.0f} - ${grant['max_amount']:,.0f}\n"
                           f"**Deadline:** {grant['deadline'].strftime('%B %d, %Y')}\n"
                           f"**Source:** {grant.get('source', 'Grant Database')}")

def add_grant_to_scenario(grant: Dict[str, Any]):
    """Add grant to selected grants for scenario planning"""
    if 'selected_grants' not in st.session_state:
        st.session_state.selected_grants = []
    
    # Check if grant already selected
    grant_names = [g['name'] for g in st.session_state.selected_grants]
    
    if grant['name'] not in grant_names:
        st.session_state.selected_grants.append(grant)
        st.success(f"Added '{grant['name']}' to your scenario grants!")
        # Removed st.rerun() to prevent navigation reset
    else:
        st.warning(f"'{grant['name']}' is already in your selected grants.")

def render_selected_grants():
    """Display and manage selected grants"""
    st.markdown("#### Selected Grants for Scenario Planning")
    
    if 'selected_grants' not in st.session_state or not st.session_state.selected_grants:
        st.info("No grants selected yet. Search and add grants above to include them in your scenarios.")
        return
    
    # Summary of selected grants
    total_min = sum(grant['min_amount'] for grant in st.session_state.selected_grants)
    total_max = sum(grant['max_amount'] for grant in st.session_state.selected_grants)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Selected Grants", len(st.session_state.selected_grants))
    
    with col2:
        st.metric("Min Total Funding", f"${total_min:,.0f}")
    
    with col3:
        st.metric("Max Total Funding", f"${total_max:,.0f}")
    
    # Grant details
    for i, grant in enumerate(st.session_state.selected_grants):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"**{grant['name']}** - {grant['agency']}")
            st.markdown(f"Amount: ${grant['min_amount']:,.0f} - ${grant['max_amount']:,.0f}")
            st.markdown(f"Deadline: {grant['deadline'].strftime('%B %d, %Y')}")
            
            if grant['match_required']:
                st.markdown(f" Match Required: {grant['match_percentage']}%")
        
        with col2:
            if st.button("Remove", key=f"remove_grant_{i}"):
                st.session_state.selected_grants.pop(i)
                # Removed st.rerun() to prevent navigation reset
    
    # Actions
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear All Selected Grants"):
            st.session_state.selected_grants = []
            # Removed st.rerun() to prevent navigation reset
    
    with col2:
        if st.button("Export Grant List"):
            export_selected_grants()

def export_selected_grants():
    """Export selected grants to CSV"""
    if 'selected_grants' not in st.session_state or not st.session_state.selected_grants:
        st.warning("No grants to export.")
        return
    
    # Convert to DataFrame
    grants_data = []
    for grant in st.session_state.selected_grants:
        grants_data.append({
            'Grant Name': grant['name'],
            'Agency': grant['agency'],
            'Category': grant['category'],
            'Min Amount': grant['min_amount'],
            'Max Amount': grant['max_amount'],
            'Deadline': grant['deadline'].strftime('%Y-%m-%d'),
            'Match Required': 'Yes' if grant['match_required'] else 'No',
            'Match Percentage': grant['match_percentage'],
            'Description': grant['description']
        })
    
    grants_df = pd.DataFrame(grants_data)
    csv = grants_df.to_csv(index=False)
    
    st.download_button(
        label="Download Grant List CSV",
        data=csv,
        file_name=f"selected_grants_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )