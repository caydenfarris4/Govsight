"""
Advanced Filtering Component - Clean Version

This module provides enhanced data filtering capabilities combining:
- Excel-style column filters and sorting
- Global search functionality
- Multi-column filtering
- Real-time data updates
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from io import BytesIO
import xlsxwriter

def create_advanced_filter_component(
    df: pd.DataFrame, 
    key_prefix: str = "filter",
    searchable_columns: Optional[List[str]] = None,
    default_sort_column: Optional[str] = None,
    items_per_page: int = 50,
    use_expander: bool = True
) -> pd.DataFrame:
    """
    Create an advanced filtering component with Excel-style filters and search
    
    Args:
        df: DataFrame to filter
        key_prefix: Unique prefix for session state keys
        searchable_columns: Columns to include in search (default: all text columns)
        default_sort_column: Default column for sorting
        items_per_page: Number of items to display per page
        use_expander: Whether to use expander for column filters
        
    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df
    
    # Initialize session state keys
    filter_state_key = f"{key_prefix}_filters"
    search_key = f"{key_prefix}_search"
    sort_key = f"{key_prefix}_sort"
    sort_asc_key = f"{key_prefix}_sort_asc"
    page_key = f"{key_prefix}_page"
    
    # Initialize session state
    if filter_state_key not in st.session_state:
        st.session_state[filter_state_key] = {}
    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    if sort_key not in st.session_state:
        st.session_state[sort_key] = default_sort_column or df.columns[0]
    if sort_asc_key not in st.session_state:
        st.session_state[sort_asc_key] = True
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    
    # Global search
    search_cols = st.columns([3, 1])
    with search_cols[0]:
        search_term = st.text_input(
            "Search all columns",
            value=st.session_state[search_key],
            key=f"{key_prefix}_search_input",
            placeholder="Search across all data..."
        )
        if search_term != st.session_state[search_key]:
            st.session_state[search_key] = search_term
            st.session_state[page_key] = 0
    
    with search_cols[1]:
        if st.button("Clear All Filters", key=f"{key_prefix}_clear"):
            st.session_state[filter_state_key] = {}
            st.session_state[search_key] = ""
            st.session_state[page_key] = 0
            st.rerun()
    
    # Column-specific filters
    if use_expander:
        with st.expander("Column Filters", expanded=False):
            _render_column_filters(df, key_prefix, filter_state_key)
    else:
        st.markdown("**Column Filters**")
        _render_column_filters(df, key_prefix, filter_state_key)
    
    # Apply filters
    filtered_df = _apply_filters(df, st.session_state[filter_state_key], search_term, searchable_columns)
    
    # Sorting controls
    sort_cols = st.columns([2, 1])
    with sort_cols[0]:
        sort_column = st.selectbox(
            "Sort by",
            options=df.columns.tolist(),
            index=df.columns.tolist().index(st.session_state[sort_key]) if st.session_state[sort_key] in df.columns else 0,
            key=f"{key_prefix}_sort_select"
        )
        if sort_column != st.session_state[sort_key]:
            st.session_state[sort_key] = sort_column
    
    with sort_cols[1]:
        sort_ascending = st.checkbox(
            "Ascending",
            value=st.session_state[sort_asc_key],
            key=f"{key_prefix}_sort_asc_check"
        )
        if sort_ascending != st.session_state[sort_asc_key]:
            st.session_state[sort_asc_key] = sort_ascending
    
    # Apply sorting
    if not filtered_df.empty:
        filtered_df = filtered_df.sort_values(by=sort_column, ascending=sort_ascending)
    
    # Pagination
    total_items = len(filtered_df)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        page_cols = st.columns([1, 2, 1])
        with page_cols[1]:
            current_page = st.selectbox(
                f"Page (showing {items_per_page} items per page)",
                options=list(range(total_pages)),
                index=min(st.session_state[page_key], total_pages - 1),
                format_func=lambda x: f"Page {x + 1} of {total_pages}",
                key=f"{key_prefix}_page_select"
            )
            if current_page != st.session_state[page_key]:
                st.session_state[page_key] = current_page
    else:
        current_page = 0
    
    # Apply pagination
    start_idx = current_page * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    return paginated_df

def _render_column_filters(df: pd.DataFrame, key_prefix: str, filter_state_key: str):
    """Render column-specific filters"""
    filter_cols = st.columns(min(4, len(df.columns)))
    
    for i, column in enumerate(df.columns):
        with filter_cols[i % len(filter_cols)]:
            st.markdown(f"**{column}**")
            
            # Get unique values for this column
            unique_values = sorted(df[column].dropna().unique())
            
            # Handle different data types
            if df[column].dtype in ['int64', 'float64']:
                # Numeric filters
                min_val, max_val = float(df[column].min()), float(df[column].max())
                current_range = st.session_state[filter_state_key].get(column, [min_val, max_val])
                
                new_range = st.slider(
                    f"Range",
                    min_value=min_val,
                    max_value=max_val,
                    value=current_range,
                    key=f"{key_prefix}_range_{column}"
                )
                
                if new_range != current_range:
                    st.session_state[filter_state_key][column] = new_range
            
            elif len(unique_values) <= 20:
                # Categorical filters with few options
                current_selection = st.session_state[filter_state_key].get(column, unique_values)
                
                new_selection = st.multiselect(
                    f"Select values",
                    options=unique_values,
                    default=current_selection,
                    key=f"{key_prefix}_select_{column}"
                )
                
                if new_selection != current_selection:
                    st.session_state[filter_state_key][column] = new_selection
            
            else:
                # Text search for columns with many unique values
                search_term = st.text_input(
                    f"Search",
                    key=f"{key_prefix}_search_{column}",
                    placeholder=f"Search {column}..."
                )
                
                if search_term:
                    # Filter unique values based on search
                    filtered_values = [v for v in unique_values if search_term.lower() in str(v).lower()]
                    
                    current_selection = st.session_state[filter_state_key].get(column, filtered_values)
                    
                    new_selection = st.multiselect(
                        f"Select from filtered",
                        options=filtered_values,
                        default=[v for v in current_selection if v in filtered_values],
                        key=f"{key_prefix}_filtered_select_{column}"
                    )
                    
                    if new_selection != current_selection:
                        st.session_state[filter_state_key][column] = new_selection

def _apply_filters(df: pd.DataFrame, filters: Dict, search_term: str, searchable_columns: Optional[List[str]]) -> pd.DataFrame:
    """Apply all filters to the dataframe"""
    filtered_df = df.copy()
    
    # Apply column-specific filters
    for column, filter_value in filters.items():
        if column not in df.columns:
            continue
            
        if isinstance(filter_value, list) and len(filter_value) == 2 and all(isinstance(x, (int, float)) for x in filter_value):
            # Numeric range filter
            filtered_df = filtered_df[
                (filtered_df[column] >= filter_value[0]) & 
                (filtered_df[column] <= filter_value[1])
            ]
        elif isinstance(filter_value, list):
            # Multi-select filter
            if filter_value:  # Only apply if there are selected values
                filtered_df = filtered_df[filtered_df[column].isin(filter_value)]
    
    # Apply global search
    if search_term:
        search_columns = searchable_columns or [col for col in df.columns if df[col].dtype == 'object']
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        
        for col in search_columns:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)
        
        filtered_df = filtered_df[mask]
    
    return filtered_df

def display_filtered_dataframe(
    df: pd.DataFrame,
    key_prefix: str = "display",
    height: int = 400,
    use_container_width: bool = True
) -> None:
    """
    Display a DataFrame with advanced filtering in a clean format
    
    Args:
        df: DataFrame to display
        key_prefix: Unique prefix for component keys
        height: Height of the dataframe display
        use_container_width: Whether to use full container width
    """
    if df.empty:
        st.info("No data matches the current filters.")
        return
    
    # Display options
    display_cols = st.columns([2, 1])
    with display_cols[1]:
        export_data = st.button("Export to Excel", key=f"{key_prefix}_export")
        
        if export_data:
            # Create Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Filtered Data', index=False)
            
            st.download_button(
                label="Download Excel file",
                data=output.getvalue(),
                file_name=f"filtered_data_{key_prefix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_prefix}_download"
            )
    
    # Display the dataframe
    st.dataframe(df, height=height, use_container_width=use_container_width)

def create_summary_metrics(df: pd.DataFrame, original_df: pd.DataFrame) -> None:
    """
    Create summary metrics for filtered data
    
    Args:
        df: Filtered DataFrame
        original_df: Original DataFrame before filtering
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Filtered Records", len(df))
    
    with col2:
        st.metric("Total Records", len(original_df))
    
    with col3:
        if len(original_df) > 0:
            percentage = (len(df) / len(original_df)) * 100
            st.metric("Showing", f"{percentage:.1f}%")
        else:
            st.metric("Showing", "0%")
    
    # Show summary for numeric columns
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) > 0:
        st.markdown("**Numeric Summary**")
        summary_cols = st.columns(len(numeric_cols))
        
        for i, col in enumerate(numeric_cols):
            with summary_cols[i]:
                if not df[col].empty:
                    col_mean = df[col].mean()
                    col_sum = df[col].sum()
                    st.metric(f"{col} (Avg)", f"{col_mean:,.2f}")
                    st.metric(f"{col} (Sum)", f"{col_sum:,.2f}")