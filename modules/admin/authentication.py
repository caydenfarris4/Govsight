"""
Authentication Module - Admin Panel
Handles user login, session management, and basic authentication

Focused on authentication logic only (~200 lines)
"""

import streamlit as st
import os
from datetime import datetime
from .user_database import authenticate_user, get_user_role, get_user_departments, init_users_db

# --- Constants ---
DEFAULT_ORG = "cityA"

def login():
    """Handle user authentication with security-focused design"""
    # Note: st.set_page_config is already called in main_app.py
    
    # Center the login interface
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Display GovSight logo centered
        if os.path.exists("logos/govsight_logo.png"):
            # Center the logo with CSS
            st.markdown("""
            <div style="display: flex; justify-content: center; margin-bottom: 1rem;">
            </div>
            """, unsafe_allow_html=True)
            col_left, col_center, col_right = st.columns([1.2, 2, 0.8])
            with col_center:
                st.image("logos/govsight_logo.png", width=300)
        
        st.markdown("""
        <div style='text-align: center; padding: 1rem 0;'>
            <h3>Municipal Financial Intelligence Platform</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if username and password:  # Ensure both fields have values
                    try:
                        if authenticate_user(username, password):
                            st.session_state.authenticated = True
                            st.session_state.username = username
                            st.session_state.user_role = get_user_role(username)
                            st.session_state.user_departments = get_user_departments(username)
                            # CRITICAL FIX: Main app expects 'user' key in session state
                            st.session_state.user = {
                                'username': username,
                                'role': get_user_role(username),
                                'departments': get_user_departments(username)
                            }
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    except Exception as e:
                        st.error(f"Authentication error: {e}")
                else:
                    st.error("Please enter both username and password")

# User functions are now imported from user_database module

def is_admin(username: str = None) -> bool:
    """Check if user has admin role"""
    if username is None:
        username = st.session_state.get('username', '')
    if not username:
        return False
    return get_user_role(username) == 'admin'

def is_finance_director(username: str = None) -> bool:
    """Check if user has finance director role"""
    if username is None:
        username = st.session_state.get('username', '')
    if not username:
        return False
    return get_user_role(username) == 'finance'

def is_department_manager(username: str = None) -> bool:
    """Check if user has department manager role"""
    if username is None:
        username = st.session_state.get('username', '')
    if not username:
        return False
    return get_user_role(username) == 'manager'

def logout():
    """Clear authentication state"""
    for key in ['authenticated', 'username', 'user_role', 'user_departments', 'user']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()