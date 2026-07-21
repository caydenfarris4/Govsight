"""
Security Manager Module

SECURITY ARCHITECTURE DECISIONS:
1. Role-based access control: Three-tier system (admin, finance, manager)
   WHY: Municipal organizations need hierarchical access to sensitive financial data

2. Department-based data isolation: Managers only see their department's data
   WHY: Follows principle of least privilege and municipal organizational structure

3. Session-based authentication: User credentials stored in Streamlit session state
   WHY: Maintains security while providing smooth user experience

4. Centralized user management: All user roles defined in single location
   WHY: Simplifies user administration and security updates

5. Default credentials for demo: Standardized passwords for initial setup
   WHY: Allows immediate deployment while requiring password changes in production
"""

import streamlit as st

# --- User Roles ---
# WHY THREE-TIER ROLE SYSTEM: Matches typical municipal government hierarchy
USERS = {
    "admin_user": {"role": "admin", "departments": "all"},           # Full system access
    "finance_director": {"role": "finance", "departments": "all"},   # Financial oversight across departments
    "pw_manager": {"role": "manager", "departments": ["Public Works"]},    # Department-specific access
    "police_manager": {"role": "manager", "departments": ["Police"]},      # Department-specific access
    "parks_manager": {"role": "manager", "departments": ["Parks & Rec"]},  # Department-specific access
    # WHY DEPARTMENT ISOLATION: Municipal departments often need data privacy from each other
}

# --- Security Functions ---

def login():
    # Force sidebar to be collapsed for login screen
    st.session_state.sidebar_collapsed = True
    
    # Center the login form in the main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("GovSight Login")
        st.markdown("#### Enter your credentials to access the GovSight Financial Analyzer")
        
        # Put login form in the main content area
        with st.form("login_form", clear_on_submit=False):
            st.write("---")
            username = st.text_input("Username", value="admin_user", key="username_input")
            password = st.text_input("Password", type="password", key="password_input")
            submit = st.form_submit_button("Login", use_container_width=True)
            st.write("---")
            
            # Check if Enter was pressed (form submitted)
            if submit or ('login_attempted' in st.session_state and st.session_state.login_attempted):
                user = USERS.get(username)
                if user and password == "govsight123":
                    # Set user data in session state
                    st.session_state.user = {
                        "username": username,
                        "role": user["role"],
                        "departments": user["departments"]
                    }
                    st.session_state.login_attempted = False
                    
                    # Maintain sidebar collapsed state
                    st.session_state.sidebar_collapsed = True
                    
                    # Show success message
                    st.success(f"Logged in as {username} ({user['role']})")
                    
                    # Force reload to apply changes
                    st.rerun()
                else:
                    if username or password:  # Only show error if they tried to enter something
                        st.error("Invalid login credentials. Please try again.")
                    # Mark that a login attempt was made
                    st.session_state.login_attempted = True

def get_user_role():
    return st.session_state.get("user", {}).get("role", None)

def get_user_departments():
    depts = st.session_state.get("user", {}).get("departments", None)
    if depts == "all":
        return None
    else:
        return depts

def is_admin():
    return get_user_role() == "admin"

def is_finance_director():
    return get_user_role() == "finance"

def is_department_manager():
    return get_user_role() == "manager"

def authorized_tabs():
    role = get_user_role()
    tabs = []

    if role == "admin":
        tabs = ["Dashboard", "Scenario Planner", "Department Insights", "AI Assistant", "Historical Analysis", "BI Sandbox", "Balance Sheet", "GL Drilldown", "Reports", "Admin Panel"]
    elif role == "finance":
        tabs = ["Dashboard", "Scenario Planner", "Department Insights", "AI Assistant", "Historical Analysis", "BI Sandbox", "Balance Sheet", "GL Drilldown", "Reports"]
    elif role == "manager":
        tabs = ["Dashboard", "Scenario Planner", "Department Insights", "Historical Analysis", "BI Sandbox"]

    return tabs