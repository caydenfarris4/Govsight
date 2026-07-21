"""
UI/UX Helper Module - Centralized UI utilities for consistent user experience

This module provides reusable UI components and helpers for:
- Loading indicators and progress feedback
- Error handling with recovery guidance
- Form validation utilities
- Responsive layout helpers
- Consistent styling
"""

import streamlit as st
from typing import Any, Callable, Optional, Dict, List, Tuple
import time
from contextlib import contextmanager
import pandas as pd

# ============================================================================
# CONSISTENT STYLING
# ============================================================================

def apply_custom_styling():
    """Apply consistent custom CSS styling across all modules"""
    st.markdown("""
    <style>
    /* Responsive container adjustments */
    .stApp {
        max-width: 100%;
        padding: 1rem;
    }
    
    /* Consistent spacing for sections */
    .section-header {
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }
    
    /* Button styling consistency */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 10px rgba(0,0,0,0.2);
    }
    
    /* Responsive columns */
    @media (max-width: 768px) {
        .row-widget.stColumns {
            flex-direction: column !important;
        }
        .row-widget.stColumns > div {
            width: 100% !important;
            margin-left: 0 !important;
        }
    }
    
    /* Data table improvements */
    .dataframe {
        font-size: 14px;
    }
    
    /* Metric cards styling */
    [data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Form input validation styling */
    .input-error {
        border-color: #dc3545 !important;
        background-color: #fff5f5 !important;
    }
    
    .input-success {
        border-color: #28a745 !important;
        background-color: #f5fff5 !important;
    }
    
    /* Loading spinner customization */
    .stSpinner > div {
        text-align: center;
        margin: 2rem auto;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        font-weight: 500;
    }
    
    /* Scrollable containers */
    .scrollable-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #dee2e6;
        border-radius: 8px;
    }
    
    /* Progress bar styling */
    .stProgress > div > div {
        background-color: #0056CC;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# LOADING INDICATORS
# ============================================================================

@contextmanager
def show_spinner(message: str = "Processing...", show_progress: bool = False):
    """
    Context manager for showing loading spinner with optional progress
    
    Usage:
        with show_spinner("Loading data...", show_progress=True) as progress:
            # Your long-running operation
            if show_progress:
                progress.update(0.5)  # Update progress to 50%
    """
    spinner_placeholder = st.empty()
    progress_bar = None
    
    with spinner_placeholder.container():
        with st.spinner(message):
            if show_progress:
                progress_bar = st.progress(0)
            
            class ProgressUpdater:
                def update(self, value: float):
                    if progress_bar:
                        progress_bar.progress(min(1.0, max(0.0, value)))
            
            yield ProgressUpdater() if show_progress else None
    
    spinner_placeholder.empty()

def show_operation_feedback(
    operation_func: Callable,
    loading_message: str = "Processing...",
    success_message: str = "Operation completed successfully!",
    error_prefix: str = "Operation failed"
) -> Optional[Any]:
    """
    Execute an operation with automatic loading, success, and error feedback
    
    Args:
        operation_func: Function to execute
        loading_message: Message to show during operation
        success_message: Message to show on success
        error_prefix: Prefix for error messages
    
    Returns:
        Result of operation_func or None if failed
    """
    try:
        with st.spinner(loading_message):
            result = operation_func()
        st.success(success_message)
        return result
    except Exception as e:
        show_error_with_guidance(f"{error_prefix}: {str(e)}")
        return None

# ============================================================================
# ERROR HANDLING
# ============================================================================

def show_error_with_guidance(
    error_message: str,
    recovery_steps: Optional[List[str]] = None,
    contact_support: bool = True
):
    """
    Display error message with recovery guidance
    
    Args:
        error_message: The error message to display
        recovery_steps: List of steps user can take to recover
        contact_support: Whether to show contact support message
    """
    st.error(f"⚠️ {error_message}")
    
    if recovery_steps:
        with st.expander("How to resolve this issue", expanded=True):
            st.markdown("### Suggested steps:")
            for i, step in enumerate(recovery_steps, 1):
                st.markdown(f"{i}. {step}")
    
    if contact_support:
        st.info("💡 If the issue persists, please contact your system administrator.")

def handle_database_error(error: Exception) -> None:
    """Handle database-specific errors with appropriate guidance"""
    error_str = str(error).lower()
    
    if "connection" in error_str or "connect" in error_str:
        show_error_with_guidance(
            "Database connection failed",
            recovery_steps=[
                "Check your network connection",
                "Verify database server is running",
                "Confirm database credentials in Admin Panel",
                "Try refreshing the page"
            ]
        )
    elif "permission" in error_str or "access" in error_str:
        show_error_with_guidance(
            "Database access denied",
            recovery_steps=[
                "Verify your user permissions",
                "Contact your database administrator",
                "Check if your account is active"
            ]
        )
    elif "not found" in error_str or "does not exist" in error_str:
        show_error_with_guidance(
            "Required database table or column not found",
            recovery_steps=[
                "Run database migration from Admin Panel",
                "Verify database schema is up to date",
                "Check if all required tables are created"
            ]
        )
    else:
        show_error_with_guidance(f"Database error: {error}")

# ============================================================================
# FORM VALIDATION
# ============================================================================

def validate_numeric_input(
    value: float,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "Value"
) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric input with range checking
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"
    
    if min_value is not None and value < min_value:
        return False, f"{field_name} must be at least {min_value:,.2f}"
    
    if max_value is not None and value > max_value:
        return False, f"{field_name} must be at most {max_value:,.2f}"
    
    return True, None

def validate_percentage(
    value: float,
    field_name: str = "Percentage",
    allow_negative: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate percentage input
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    min_val = -100 if allow_negative else 0
    return validate_numeric_input(value, min_val, 100, field_name)

def validate_triangular_distribution(
    min_val: float,
    likely_val: float,
    max_val: float,
    field_name: str = "Distribution"
) -> Tuple[bool, Optional[str]]:
    """
    Validate triangular distribution parameters (min ≤ likely ≤ max)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if min_val > likely_val:
        return False, f"{field_name}: Minimum ({min_val:,.2f}) cannot be greater than Most Likely ({likely_val:,.2f})"
    
    if likely_val > max_val:
        return False, f"{field_name}: Most Likely ({likely_val:,.2f}) cannot be greater than Maximum ({max_val:,.2f})"
    
    if min_val > max_val:
        return False, f"{field_name}: Minimum ({min_val:,.2f}) cannot be greater than Maximum ({max_val:,.2f})"
    
    return True, None

def show_validation_error(field_name: str, error_message: str):
    """Display validation error for a specific field"""
    st.error(f"❌ {field_name}: {error_message}")

def show_validation_success(message: str = "All inputs validated successfully"):
    """Display validation success message"""
    st.success(f"✅ {message}")

# ============================================================================
# RESPONSIVE LAYOUT HELPERS
# ============================================================================

def create_responsive_columns(
    num_columns: int,
    mobile_stack: bool = True
) -> List:
    """
    Create responsive columns that stack on mobile
    
    Args:
        num_columns: Number of columns to create
        mobile_stack: Whether to stack columns on mobile devices
    
    Returns:
        List of column objects
    """
    if mobile_stack:
        # Add CSS for mobile stacking
        st.markdown("""
        <style>
        @media (max-width: 768px) {
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    return st.columns(num_columns)

def create_scrollable_dataframe(
    df: pd.DataFrame,
    height: int = 400,
    key: Optional[str] = None
) -> None:
    """
    Display dataframe in a scrollable container
    
    Args:
        df: DataFrame to display
        height: Maximum height in pixels
        key: Optional unique key for the component
    """
    st.dataframe(
        df,
        use_container_width=True,
        height=min(height, len(df) * 35 + 50),  # Dynamic height based on rows
        key=key
    )

def create_metric_cards(
    metrics: Dict[str, Dict[str, Any]],
    columns_per_row: int = 3
) -> None:
    """
    Create responsive metric cards
    
    Args:
        metrics: Dictionary of metric data
            Format: {"label": {"value": x, "delta": y, "delta_color": "normal"}}
        columns_per_row: Number of columns per row
    """
    metric_items = list(metrics.items())
    
    for i in range(0, len(metric_items), columns_per_row):
        cols = create_responsive_columns(min(columns_per_row, len(metric_items) - i))
        
        for j, col in enumerate(cols):
            if i + j < len(metric_items):
                label, data = metric_items[i + j]
                with col:
                    st.metric(
                        label=label,
                        value=data.get("value"),
                        delta=data.get("delta"),
                        delta_color=data.get("delta_color", "normal")
                    )

# ============================================================================
# PROGRESS INDICATORS
# ============================================================================

class MultiStepProgress:
    """Helper class for multi-step operations with progress tracking"""
    
    def __init__(self, steps: List[str], title: str = "Processing"):
        self.steps = steps
        self.title = title
        self.current_step = 0
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.start_time = time.time()
        
        self._update_display()
    
    def next_step(self):
        """Move to the next step"""
        if self.current_step < len(self.steps):
            self.current_step += 1
            self._update_display()
    
    def complete(self, message: str = "Completed successfully!"):
        """Mark the operation as complete"""
        self.progress_bar.progress(1.0)
        elapsed = time.time() - self.start_time
        self.status_text.success(f"✅ {message} (took {elapsed:.1f}s)")
    
    def error(self, message: str = "Operation failed"):
        """Mark the operation as failed"""
        self.status_text.error(f"❌ {message}")
    
    def _update_display(self):
        """Update the progress display"""
        progress = self.current_step / len(self.steps)
        self.progress_bar.progress(progress)
        
        if self.current_step < len(self.steps):
            current_step_name = self.steps[self.current_step]
            self.status_text.info(
                f"**{self.title}** - Step {self.current_step + 1}/{len(self.steps)}: {current_step_name}"
            )

# ============================================================================
# USER FEEDBACK
# ============================================================================

def show_info_banner(
    title: str,
    message: str,
    icon: str = "ℹ️",
    type: str = "info"
) -> None:
    """
    Show an informational banner with custom styling
    
    Args:
        title: Banner title
        message: Banner message
        icon: Icon to display
        type: Type of banner (info, warning, success, error)
    """
    color_map = {
        "info": "#d1ecf1",
        "warning": "#fff3cd",
        "success": "#d4edda",
        "error": "#f8d7da"
    }
    
    border_color_map = {
        "info": "#bee5eb",
        "warning": "#ffeeba",
        "success": "#c3e6cb",
        "error": "#f5c6cb"
    }
    
    bg_color = color_map.get(type, color_map["info"])
    border_color = border_color_map.get(type, border_color_map["info"])
    
    st.markdown(f"""
    <div style="
        background-color: {bg_color};
        border: 1px solid {border_color};
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    ">
        <h4 style="margin: 0 0 0.5rem 0;">{icon} {title}</h4>
        <p style="margin: 0;">{message}</p>
    </div>
    """, unsafe_allow_html=True)

def confirm_action(
    action_name: str,
    warning_message: Optional[str] = None
) -> bool:
    """
    Show a confirmation dialog for destructive actions
    
    Args:
        action_name: Name of the action to confirm
        warning_message: Optional warning message
    
    Returns:
        True if user confirms, False otherwise
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if warning_message:
            st.warning(warning_message)
        st.write(f"Are you sure you want to {action_name}?")
    
    with col2:
        if st.button("Confirm", type="primary", key=f"confirm_{action_name}"):
            return True
        if st.button("Cancel", key=f"cancel_{action_name}"):
            return False
    
    return False

# ============================================================================
# REAL-TIME VALIDATION
# ============================================================================

def create_validated_input(
    input_type: str,
    label: str,
    validation_func: Callable,
    key: str,
    **input_kwargs
) -> Tuple[Any, bool]:
    """
    Create an input field with real-time validation
    
    Args:
        input_type: Type of input (number, text, etc.)
        label: Input label
        validation_func: Function to validate input
        key: Unique key for the input
        **input_kwargs: Additional arguments for the input field
    
    Returns:
        Tuple of (value, is_valid)
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if input_type == "number":
            value = st.number_input(label, key=key, **input_kwargs)
        elif input_type == "text":
            value = st.text_input(label, key=key, **input_kwargs)
        elif input_type == "selectbox":
            value = st.selectbox(label, key=key, **input_kwargs)
        else:
            value = None
    
    with col2:
        is_valid, error_msg = validation_func(value)
        if value is not None:
            if is_valid:
                st.success("✓")
            else:
                st.error("✗")
                if error_msg:
                    st.caption(error_msg)
    
    return value, is_valid

# ============================================================================
# EXPORT FUNCTIONALITY
# ============================================================================

__all__ = [
    'apply_custom_styling',
    'show_spinner',
    'show_operation_feedback',
    'show_error_with_guidance',
    'handle_database_error',
    'validate_numeric_input',
    'validate_percentage',
    'validate_triangular_distribution',
    'show_validation_error',
    'show_validation_success',
    'create_responsive_columns',
    'create_scrollable_dataframe',
    'create_metric_cards',
    'MultiStepProgress',
    'show_info_banner',
    'confirm_action',
    'create_validated_input'
]