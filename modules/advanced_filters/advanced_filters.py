"""
Advanced Filtering Component

This module provides enhanced data filtering capabilities combining:
- Excel-style column filters and sorting
- Global search functionality
- Multi-column filtering
- Real-time data updates
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

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
        
    Returns:
        Filtered DataFrame
    """
    if df.empty:
        st.warning("No data available for filtering")
        return df
    
    # Initialize session state for this filter component
    filter_state_key = f"{key_prefix}_filters"
    search_key = f"{key_prefix}_search"
    sort_key = f"{key_prefix}_sort"
    page_key = f"{key_prefix}_page"
    
    if filter_state_key not in st.session_state:
        st.session_state[filter_state_key] = {}
    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    if sort_key not in st.session_state:
        st.session_state[sort_key] = {"column": default_sort_column, "ascending": True}
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    
    # Determine searchable columns
    if searchable_columns is None:
        searchable_columns = [col for col in df.columns if df[col].dtype == 'object']
    
    # Create filter interface
    st.markdown("###  Advanced Filters")
    
    # Global search bar
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input(
            "Search across all data",
            value=st.session_state[search_key],
            placeholder="Type to search...",
            key=f"{key_prefix}_search_input"
        )
        if search_term != st.session_state[search_key]:
            st.session_state[search_key] = search_term
            st.session_state[page_key] = 0  # Reset to first page
    
    with col2:
        if st.button("Clear All Filters", key=f"{key_prefix}_clear"):
            st.session_state[filter_state_key] = {}
            st.session_state[search_key] = ""
            st.session_state[page_key] = 0
            st.rerun()
    
    # Column-specific filters - use container to avoid nested expander issues
    st.markdown("**Column Filters**")
    filter_cols = st.columns(min(4, len(df.columns)))
    
    for i, column in enumerate(df.columns):
        with filter_cols[i % len(filter_cols)]:
            st.markdown(f"**{column}**")
            
            # Get unique values for this column
            unique_values = sorted(df[column].dropna().unique())
            
            # Handle different data types
            if df[column].dtype in ['int64', 'float64']:
                    # Numeric filters with safety check for identical min/max values
                    min_val, max_val = float(df[column].min()), float(df[column].max())
                    
                    # Safety check: if min and max are the same, show info and skip slider
                    if min_val == max_val:
                        st.info(f"{column}: All values are {min_val} (constant value)")
                        new_range = [min_val, max_val]
                    else:
                        current_range = st.session_state[filter_state_key].get(column, [min_val, max_val])
                        new_range = st.slider(
                            f"Range",
                            min_value=min_val,
                            max_value=max_val,
                            value=current_range,
                            key=f"{key_prefix}_{column}_range"
                        )
                        
                        if new_range != current_range:
                            st.session_state[filter_state_key][column] = new_range
                            st.session_state[page_key] = 0
                
            elif len(unique_values) <= 50:  # Categorical filters
                current_selection = st.session_state[filter_state_key].get(column, unique_values)
                
                new_selection = st.multiselect(
                    f"Select values",
                    options=unique_values,
                    default=current_selection,
                    key=f"{key_prefix}_{column}_multi"
                )
                
                if set(new_selection) != set(current_selection):
                    st.session_state[filter_state_key][column] = new_selection
                    st.session_state[page_key] = 0
            
            else:  # Text search for high-cardinality columns
                current_search = st.session_state[filter_state_key].get(column, "")
                
                new_search = st.text_input(
                    f"Search in {column}",
                    value=current_search,
                    key=f"{key_prefix}_{column}_search"
                )
                
                if new_search != current_search:
                    st.session_state[filter_state_key][column] = new_search
                    st.session_state[page_key] = 0
    
    # Apply filters
    filtered_df = df.copy()
    
    # Apply global search
    if st.session_state[search_key]:
        search_mask = pd.Series([False] * len(filtered_df))
        for col in searchable_columns:
            if col in filtered_df.columns:
                search_mask |= filtered_df[col].astype(str).str.contains(
                    st.session_state[search_key], case=False, na=False
                )
        filtered_df = filtered_df[search_mask]
    
    # Apply column-specific filters
    for column, filter_value in st.session_state[filter_state_key].items():
        if column not in filtered_df.columns:
            continue
            
        if isinstance(filter_value, list) and len(filter_value) == 2 and all(isinstance(x, (int, float)) for x in filter_value):
            # Numeric range filter
            filtered_df = filtered_df[
                (filtered_df[column] >= filter_value[0]) & 
                (filtered_df[column] <= filter_value[1])
            ]
        elif isinstance(filter_value, list):
            # Categorical filter
            if filter_value:  # Only filter if something is selected
                filtered_df = filtered_df[filtered_df[column].isin(filter_value)]
        elif isinstance(filter_value, str) and filter_value:
            # Text search filter
            filtered_df = filtered_df[
                filtered_df[column].astype(str).str.contains(filter_value, case=False, na=False)
            ]
    
    # Sorting interface
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sort_column = st.selectbox(
            "Sort by",
            options=["None"] + list(df.columns),
            index=0 if st.session_state[sort_key]["column"] is None else list(df.columns).index(st.session_state[sort_key]["column"]) + 1,
            key=f"{key_prefix}_sort_column"
        )
    
    with col2:
        sort_ascending = st.selectbox(
            "Order",
            options=["Ascending", "Descending"],
            index=0 if st.session_state[sort_key]["ascending"] else 1,
            key=f"{key_prefix}_sort_order"
        )
    
    with col3:
        st.metric("Filtered Records", len(filtered_df), delta=len(filtered_df) - len(df))
    
    # Update sort state
    if sort_column != "None":
        st.session_state[sort_key] = {
            "column": sort_column,
            "ascending": sort_ascending == "Ascending"
        }
        filtered_df = filtered_df.sort_values(sort_column, ascending=sort_ascending == "Ascending")
    
    # Pagination
    total_pages = (len(filtered_df) - 1) // items_per_page + 1 if len(filtered_df) > 0 else 1
    
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Previous", disabled=st.session_state[page_key] == 0, key=f"{key_prefix}_prev"):
                st.session_state[page_key] = max(0, st.session_state[page_key] - 1)
                st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state[page_key] + 1} of {total_pages}")
        
        with col3:
            if st.button("Next →", disabled=st.session_state[page_key] >= total_pages - 1, key=f"{key_prefix}_next"):
                st.session_state[page_key] = min(total_pages - 1, st.session_state[page_key] + 1)
                st.rerun()
    
    # Apply pagination
    start_idx = st.session_state[page_key] * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    return paginated_df

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
        st.info("No data to display with current filters")
        return
    
    # Configure column display
    column_config = {}
    for col in df.columns:
        if df[col].dtype in ['int64', 'float64']:
            if any(keyword in col.lower() for keyword in ['budget', 'actual', 'amount', 'cost', 'revenue']):
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    format="$%.2f"
                )
            else:
                column_config[col] = st.column_config.NumberColumn(col)
        elif df[col].dtype == 'object' and any(keyword in col.lower() for keyword in ['date', 'time']):
            try:
                # Try to parse as datetime
                pd.to_datetime(df[col].dropna().iloc[0] if not df[col].dropna().empty else "")
                column_config[col] = st.column_config.DatetimeColumn(col)
            except:
                pass
    
    # Display the dataframe
    st.dataframe(
        df,
        use_container_width=use_container_width,
        height=height,
        column_config=column_config,
        hide_index=True
    )
    
    # Export options
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        csv_data = df.to_csv(index=False)
        st.download_button(
            label=" Export CSV",
            data=csv_data,
            file_name=f"filtered_data_{key_prefix}.csv",
            mime="text/csv",
            key=f"{key_prefix}_csv_download"
        )
    
    with col2:
        try:
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Filtered Data', index=False)
            
            st.download_button(
                label=" Export Excel",
                data=buffer.getvalue(),
                file_name=f"filtered_data_{key_prefix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_prefix}_excel_download"
            )
        except ImportError:
            st.info("Excel export requires xlsxwriter package")

def create_summary_metrics(df: pd.DataFrame, original_df: pd.DataFrame) -> None:
    """
    Create summary metrics for filtered data
    
    Args:
        df: Filtered DataFrame
        original_df: Original DataFrame before filtering
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Records",
            len(df),
            delta=len(df) - len(original_df)
        )
    
    with col2:
        percentage = (len(df) / len(original_df) * 100) if len(original_df) > 0 else 0
        st.metric(
            "Percentage Shown",
            f"{percentage:.1f}%"
        )
    
    # Add numeric column summaries if available
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    
    if len(numeric_cols) > 0:
        with col3:
            total_sum = df[numeric_cols].sum().sum()
            st.metric(
                "Sum of Numeric Values",
                f"${total_sum:,.2f}" if any('budget' in col.lower() or 'amount' in col.lower() for col in numeric_cols) else f"{total_sum:,.2f}"
            )
        
        with col4:
            avg_value = df[numeric_cols].mean().mean()
            st.metric(
                "Average Value",
                f"${avg_value:,.2f}" if any('budget' in col.lower() or 'amount' in col.lower() for col in numeric_cols) else f"{avg_value:,.2f}"
            )