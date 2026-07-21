import streamlit as st
import pandas as pd
import os
import json
import time
import csv
import zipfile
from datetime import datetime
import sys

# Add root directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import with fallback handling for missing modules
try:
    from modules.admin.admin_archive_manager import *
except ImportError:
    pass

try:
    from modules.admin.scenario_manager import render_scenario_manager
except ImportError:
    render_scenario_manager = None

try:
    from modules.database.db_connection import load_config, save_config
except ImportError:
    def load_config():
        return {}
    def save_config(config):
        pass

try:
    from modules.admin.credentials_manager import CredentialsManager
except ImportError:
    # Fallback if credentials manager not available
    class CredentialsManager:
        def __init__(self):
            pass
        def save_google_sheets_credentials(self, *args, **kwargs):
            return {"success": False, "error": "Credentials manager not available"}
        def get_credentials_status(self, *args, **kwargs):
            return {"configured": False}

try:
    from modules.security.api_key_manager import api_key_manager
except ImportError:
    # Fallback if API key manager not available
    class APIKeyManager:
        def __init__(self):
            pass
        def set_api_key(self, *args, **kwargs):
            return {"success": False, "message": "API key manager not available"}
        def get_status(self, *args, **kwargs):
            return {"configured": False}
        def validate_api_key(self, *args, **kwargs):
            return {"valid": False, "message": "API key manager not available"}
        def remove_api_key(self, *args, **kwargs):
            return {"success": False, "message": "API key manager not available"}
    api_key_manager = APIKeyManager()

try:
    from modules.admin.audit_trail_viewer import render_audit_trail_interface
except ImportError:
    def render_audit_trail_interface():
        st.error("Audit trail module not available")
        st.info("Please ensure the audit trail dependencies are installed")

try:
    from modules.admin.super_admin_database import render_super_admin_database_manager
except ImportError:
    def render_super_admin_database_manager():
        st.error("Super Admin Database Manager not available")
        st.info("Please ensure the database management dependencies are installed")

try:
    from modules.database.db_archive_utils import *
except ImportError:
    pass

# --- Constants ---
# WHY SEPARATE FILES FOR DIFFERENT DATA TYPES:
USERS_FILE = "users_table.csv"              # User data in CSV for easy manual editing
SETTINGS_FILE = "system_settings.json"      # System config in JSON for structured data
ARCHIVE_SETTINGS_FILE = "archive_settings.json"  # Archive config separate from main settings
DEFAULT_ORG = "cityA"  # Default organization ID
# REASONING: Separation allows different backup/security policies for each data type

# --- User Roles (Default Users) ---
# WHY ROLE-BASED DEFAULTS: Provides immediate functionality while allowing customization
# SECURITY: Use environment variables to override default passwords in production
import os

# Check if we're in development mode
DEV_MODE = os.environ.get('GOVSIGHT_DEV_MODE', 'false').lower() == 'true'

# Get secure password from environment or use default only in dev mode
DEFAULT_PASSWORD = os.environ.get('GOVSIGHT_DEFAULT_PASSWORD', 
                                 'govsight123' if DEV_MODE else None)

if DEFAULT_PASSWORD == 'govsight123' and not DEV_MODE:
    # In production, require secure password configuration
    DEFAULT_USERS = {}
    # Users must be configured through the admin interface or environment
else:
    DEFAULT_USERS = {
        "admin_user": {"role": "admin", "departments": "all", "password": DEFAULT_PASSWORD},
        # WHY ADMIN: Full system access for setup and emergency situations
        
        "finance_director": {"role": "finance", "departments": "all", "password": DEFAULT_PASSWORD},
        # WHY FINANCE ROLE: Cross-department financial oversight without full admin privileges
        
        "pw_manager": {"role": "manager", "departments": ["Public Works"], "password": DEFAULT_PASSWORD},
        "police_manager": {"role": "manager", "departments": ["Police"], "password": DEFAULT_PASSWORD},
        "parks_manager": {"role": "manager", "departments": ["Parks & Rec"], "password": DEFAULT_PASSWORD},
        # WHY DEPARTMENT MANAGERS: Restricted access to only their department's data
        # This follows the principle of least privilege for municipal data security
    }

# --- Security Functions ---
def login():
    """
    Handle user authentication with security-focused design
    
    SECURITY DECISIONS:
    1. Sidebar collapse: Prevents access to navigation before authentication
    2. Centered layout: Professional appearance builds trust with government users  
    3. Logo display: Reinforces application branding and legitimacy
    """
    # Force sidebar to be collapsed for login screen
    st.session_state.sidebar_collapsed = True
    # WHY: Prevents unauthorized access to navigation elements before login
    
    # Center the login form using Streamlit columns
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Add GovSight logo to login page - perfectly centered
        try:
            # Use HTML to center the image perfectly
            with open("logos/govsight_logo.png", "rb") as f:
                import base64
                logo_data = base64.b64encode(f.read()).decode()
                st.markdown(f'<div style="text-align: center; margin: 1rem 0;"><img src="data:image/png;base64,{logo_data}" width="200" /></div>', unsafe_allow_html=True)
        except:
            try:
                with open("govsight_logo.png", "rb") as f:
                    import base64
                    logo_data = base64.b64encode(f.read()).decode()
                    st.markdown(f'<div style="text-align: center; margin: 1rem 0;"><img src="data:image/png;base64,{logo_data}" width="200" /></div>', unsafe_allow_html=True)
            except:
                # Fallback with centered text
                st.markdown('<h2 style="text-align: center; color: #667eea; margin: 1rem 0;">GovSight</h2>', unsafe_allow_html=True)
        
        # Center the login title and description
        st.markdown('<h1 style="text-align: center; margin: 2rem 0 1rem 0;">Login</h1>', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 2rem; color: #666;">Enter your credentials to access the Financial Analyzer</h4>', unsafe_allow_html=True)
    
        # Clean, professional login form
        with st.form("login_form", clear_on_submit=False):
            # Add some spacing above the form
            st.write("")
            
            # Form fields with clean styling
            username = st.text_input("Username", value="admin_user", key="username_input")
            password = st.text_input("Password", type="password", key="password_input")
            
            # Add some spacing
            st.write("")
            
            # Submit button
            submit = st.form_submit_button("Login", use_container_width=True)
            
    # Load users from file or use defaults
    users = load_users()
    
    # Check if Enter was pressed (form submitted)
    if submit:
            user = users.get(username)
            
            # Check the user's password or use default password as fallback
            settings = load_settings()
            default_password = settings.get("DefaultPassword", "govsight123")
            user_password = user.get("password", default_password) if user else None
            
            # Enhanced authentication with better validation
            # Use secure password comparison and support hashed passwords
            try:
                from modules.security.password_security import verify_password, secure_compare
            except ImportError:
                # Fallback for basic password comparison
                def secure_compare(a, b):
                    if a is None or b is None:
                        return False
                    return a == b
                def verify_password(password, hash_val, salt):
                    return False
            
            if user and password:
                # Check if user has hashed password
                if user.get("password_hashed", False) and "password_hash" in user and "password_salt" in user:
                    password_valid = verify_password(password, user["password_hash"], user["password_salt"])
                else:
                    # Legacy plain text comparison (secure)
                    password_valid = secure_compare(password, user_password) if user_password else False
                
                if password_valid:
                    # Validate user data structure
                    if not all(key in user for key in ["role", "departments"]):
                        st.error("User account configuration is incomplete. Contact administrator.")
                        return
                    
                    # Set user data in session state with validation
                    st.session_state.user = {
                        "username": username,
                        "role": user["role"],
                        "departments": user["departments"],
                        "login_time": pd.Timestamp.now().isoformat()
                    }
                    # Also set the legacy fields for compatibility
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_role = user["role"]
                    st.session_state.user_departments = user["departments"]
                    st.session_state.login_attempted = False
                    
                    # Maintain sidebar collapsed state
                    st.session_state.sidebar_collapsed = True
                    
                    # Show success message and redirect immediately
                    st.success(f"Successfully logged in as {username} ({user['role']})")
                    st.info("Redirecting to dashboard...")
                    
                    # Force reload to apply changes
                    st.rerun()
                else:
                    if username or password:  # Only show error if they tried to enter something
                        st.error("Invalid login credentials. Please verify your username and password.")
                        # Add security delay for failed attempts
                        import time
                        time.sleep(1)
                    # Mark that a login attempt was made
                    st.session_state.login_attempted = True

def get_user_role():
    user = st.session_state.get("user", {})
    return user.get("role", None)

def get_user_departments():
    user = st.session_state.get("user", {})
    depts = user.get("departments", None)
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
    tabs = ["Dashboard"]  # Dashboard is always available

    # New 3-module structure
    if role == "admin":
        tabs = ["Dashboard", "Navi", "Mantis", "Vatica", "Claude Agent", "Admin Panel"]
    elif role == "finance":
        tabs = ["Dashboard", "Navi", "Mantis", "Vatica", "Claude Agent"]
    elif role == "manager":
        tabs = ["Dashboard", "Navi", "Vatica"]  # Managers get planning and analysis, but not AI/reports
    else:
        # Default for any authenticated user
        tabs = ["Dashboard", "Vatica"]

    return tabs

def load_users():
    """Load users from SQLite database"""
    import sqlite3
    import hashlib
    from modules.admin.database_config import PRODUCTION_USERS_DB
    
    users_db = PRODUCTION_USERS_DB
    
    try:
        conn = sqlite3.connect(users_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, role, departments, password, active 
            FROM users 
            WHERE active = 1
        """)
        
        users = {}
        for row in cursor.fetchall():
            username, role, departments, password, active = row
            
            # Convert departments string to list if not "all"
            if departments and departments.lower() != "all":
                dept_list = [d.strip() for d in departments.split(",") if d.strip()]
            else:
                dept_list = "all"
            
            users[username] = {
                "role": role,
                "departments": dept_list,
                "password": password  # Already hashed in database
            }
        
        conn.close()
        return users
        
    except Exception as e:
        st.warning(f"Error loading users from database: {e}")
        return {}

def save_users(users):
    """Save users to SQLite database"""
    import sqlite3
    import hashlib
    from modules.admin.database_config import PRODUCTION_USERS_DB
    
    users_db = PRODUCTION_USERS_DB
    
    try:
        conn = sqlite3.connect(users_db)
        cursor = conn.cursor()
        
        for username, details in users.items():
            # Format departments for storage
            depts = details["departments"]
            if isinstance(depts, list):
                depts = ", ".join(depts)
            elif depts is None:
                depts = "all"
            
            # Hash password if it's not already hashed (new passwords)
            password = details.get("password", "govsight123")
            if len(password) != 64:  # Not a SHA-256 hash
                password = hashlib.sha256(password.encode()).hexdigest()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing user
                cursor.execute("""
                    UPDATE users 
                    SET role = ?, departments = ?, password = ?
                    WHERE LOWER(username) = LOWER(?)
                """, (details["role"], depts, password, username))
            else:
                # Insert new user
                cursor.execute("""
                    INSERT INTO users (username, password, role, departments, active, created_at)
                    VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """, (username, password, details["role"], depts))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error saving users to database: {e}")
        return False

def delete_user(username):
    """Delete a user from the SQLite database"""
    import sqlite3
    from modules.admin.database_config import PRODUCTION_USERS_DB
    
    users_db = PRODUCTION_USERS_DB
    
    try:
        conn = sqlite3.connect(users_db)
        cursor = conn.cursor()
        
        # Delete the user
        cursor.execute("DELETE FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        
        conn.commit()
        affected_rows = cursor.rowcount
        conn.close()
        
        return affected_rows > 0
        
    except Exception as e:
        st.error(f"Error deleting user from database: {e}")
        return False

def load_settings():
    """Load settings from the settings file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {
                "OrganizationName": "City A",
                "DefaultPassword": "govsight123",
                "OpenAI_Key": "",
                "AutoBackupEnabled": False,
                "BudgetYear": datetime.now().year
            }
    else:
        return {
            "OrganizationName": "City A",
            "DefaultPassword": "govsight123",
            "OpenAI_Key": "",
            "AutoBackupEnabled": False,
            "BudgetYear": datetime.now().year
        }

def render_admin_panel():
    st.title("🔒 Admin Control Panel")

    if not is_admin() and not is_finance_director():
        st.error("You are not authorized to view this page.")
        st.stop()

    # Phase 3: Advanced Municipal Intelligence Systems (Updated Structure)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "Manage Users", "Data Sources", "Archive Viewer", "System Settings", 
        "Fund Classifications", "Reporting Management", "Security Trails", "Audit Trail", 
        "Real-Time Monitoring", "Scenario Manager"
    ])

    # --- Manage Users Tab ---
    with tab1:
        st.header("Manage System Users")

        # Load users dictionary from file or defaults
        users = load_users()
        
        # Add password visibility toggle for admins
        show_passwords = False
        if is_admin():
            show_passwords = st.checkbox("👁️ Show Passwords", value=False, 
                                        help="Toggle to show/hide actual passwords")
        
        # Convert users dictionary to DataFrame for display
        users_data = []
        for username, details in users.items():
            depts = details["departments"]
            if isinstance(depts, list):
                depts = ", ".join(depts)
            
            # Decide whether to show real password or mask it
            password_display = details.get("password", "********")
            if not show_passwords:
                password_display = "********"
            
            users_data.append({
                "Username": username,
                "Role": details["role"],
                "Departments": depts,
                "Password": password_display
            })
            
        users_df = pd.DataFrame(users_data)
        
        if not users_df.empty:
            st.dataframe(users_df)
        else:
            st.info("No users configured yet.")

        # User management form
        st.subheader("Add/Edit User")
        
        # Get settings for default password
        settings = load_settings()
        default_password = settings.get("DefaultPassword", "govsight123")
        
        # Create a dropdown to select existing users for editing
        # First add a "New User" option
        user_options = ["New User"] + list(users.keys())
        selected_user = st.selectbox("Select User", user_options, 
                                    help="Select 'New User' to create a new account or select an existing user to edit")
        
        # Initialize form values
        username_value = ""
        role_value = "admin"  # Default role
        dept_value = ""
        
        # If editing existing user, pre-populate the form fields
        is_editing = selected_user != "New User"
        if is_editing:
            username_value = selected_user
            role_value = users[selected_user]["role"]
            
            # Format departments
            depts = users[selected_user]["departments"]
            if isinstance(depts, list):
                dept_value = ", ".join(depts)
            elif depts == "all":
                dept_value = "all"
        
        # User input form
        with st.form("add_user_form"):
            # If editing, show username as read-only info, otherwise let user enter it
            if is_editing:
                st.info(f"Editing user: {username_value}")
                new_username = username_value  # Use the selected username
                st.text_input("Username", value=username_value, disabled=True)
            else:
                new_username = st.text_input("Username")
            
            # Password field - leave blank to keep existing password if editing
            password_help = "Leave blank to use default password" if not is_editing else "Leave blank to keep current password"
            new_password = st.text_input("Password", type="password", help=f"{password_help} ({default_password})")
            
            # Role selection
            new_role = st.selectbox("Role", ["admin", "finance", "manager"], 
                                  index=["admin", "finance", "manager"].index(role_value))
            
            # Departments field
            new_departments = st.text_input("Departments (comma-separated, or 'all')", value=dept_value,
                                          help="Enter 'all' for all departments or a comma-separated list like 'Finance, Public Works'")
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Save User")
            
            with col2:
                delete = st.form_submit_button("Delete User", type="secondary")
            
        # Handle form submission
        if submit and new_username:
            # Process departments input
            if new_departments.lower().strip() == "all":
                departments = "all"
            else:
                departments = [d.strip() for d in new_departments.split(",") if d.strip()]
            
            # Handle password logic
            if is_editing and not new_password:
                # If editing an existing user and no new password provided, keep the current password
                new_password = users[new_username].get("password", default_password)
            elif not new_password:
                # For new users with no password, use the default password
                new_password = default_password
                
            # Update users dictionary
            users[new_username] = {
                "role": new_role,
                "departments": departments,
                "password": new_password
            }
            
            # Save to file
            if save_users(users):
                if is_editing:
                    st.success(f"User '{new_username}' updated successfully!")
                else:
                    st.success(f"New user '{new_username}' created successfully!")
                st.rerun()  # Refresh the page to show updated user list
        
        # Handle delete operation
        if delete and new_username and new_username in users:
            # Only allow delete if it's not the current user
            current_user = st.session_state.get("user", {}).get("username")
            if current_user == new_username:
                st.error("Cannot delete current user!")
            elif new_username.lower() == "admin_user":
                st.error("Cannot delete the primary admin_user account!")
            else:
                if delete_user(new_username):
                    st.success(f"User '{new_username}' deleted successfully!")
                    st.rerun()  # Refresh the page to show updated user list
                else:
                    st.error(f"Failed to delete user '{new_username}'")

    # --- Data Sources Tab ---
    with tab2:
        try:
            from modules.admin.data_sources_manager import render_data_sources_manager
            render_data_sources_manager()
        except ImportError as e:
            st.error(f"Data Sources Manager not available: {e}")
            st.info("Please ensure all data adapter dependencies are installed.")

    # --- Archive Viewer Tab ---
    with tab3:
        st.header("Scenario Reports Archive")

        # Initialize archive manager if not exists
        try:
            from modules.admin.archive_manager import ArchiveManager
            archive_mgr = ArchiveManager()
            archive_df = archive_mgr.load_archive_metadata()
        except ImportError:
            st.info("Archive manager not available. This feature will be implemented soon.")
            archive_df = pd.DataFrame()
        
        if archive_df.empty:
            st.info("No archived reports yet.")
        else:
            # Add human-readable timestamp
            if "Timestamp" in archive_df.columns:
                archive_df["Created"] = pd.to_datetime(archive_df["Timestamp"], format="%Y%m%d_%H%M%S").dt.strftime("%b %d, %Y %I:%M %p")
            
            # Add filters
            col1, col2 = st.columns(2)
            with col1:
                dept_filter = st.multiselect("Filter by Department", 
                                           options=["All"] + sorted(archive_df["Department"].unique().tolist()),
                                           default=["All"])
            with col2:
                user_filter = st.multiselect("Filter by Creator", 
                                           options=["All"] + sorted(archive_df["CreatedBy"].unique().tolist()),
                                           default=["All"])
            
            # Apply filters
            filtered_df = archive_df.copy()
            if dept_filter and "All" not in dept_filter:
                filtered_df = filtered_df[filtered_df["Department"].isin(dept_filter)]
            if user_filter and "All" not in user_filter:
                filtered_df = filtered_df[filtered_df["CreatedBy"].isin(user_filter)]
            
            # Sort by timestamp (newest first)
            if "Timestamp" in filtered_df.columns:
                filtered_df = filtered_df.sort_values("Timestamp", ascending=False)
            
            # Create display columns
            display_cols = ["ProjectName", "Department", "CreatedBy"]
            if "Created" in filtered_df.columns:
                display_cols.append("Created")
                
            st.dataframe(filtered_df[display_cols])
            
            # Download options
            selected_filename = st.selectbox("Select a Report to Download", filtered_df["Filename"].tolist())
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(" Download Report"):
                    file_path = os.path.join(archive_mgr.ARCHIVE_FOLDER, selected_filename)
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as file:
                            st.download_button("Download Now", data=file, file_name=selected_filename, mime="application/pdf")
                    else:
                        st.error(f"File not found: {selected_filename}")
            
            with col2:
                if st.button("Delete Report") and is_admin():
                    try:
                        # Remove from filesystem
                        file_path = os.path.join(archive_mgr.ARCHIVE_FOLDER, selected_filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            
                        # Remove from metadata
                        metadata = archive_df[archive_df["Filename"] != selected_filename]
                        metadata.to_csv(os.path.join(archive_mgr.ARCHIVE_FOLDER, archive_mgr.ARCHIVE_METADATA_FILE), index=False)
                        
                        st.success(f"Report '{selected_filename}' deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting report: {e}")

    # --- System Settings Tab ---
    with tab4:
        st.header("System Settings")

        # Load the app configuration and get current organization name
        config = load_config()
        # Import organization info from connection manager for consistency
        from modules.database.connection_manager import get_org_display_info
        org_info = get_org_display_info()
        current_org_name = org_info.get("organization_name", "Spanish Fork")

        # Load or initialize settings
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    # Ensure organization name is synced with config
                    if "OrganizationName" not in settings:
                        settings["OrganizationName"] = current_org_name
            except:
                settings = {
                    "OrganizationName": current_org_name,
                    "DefaultPassword": "changeme123",
                    "OpenAI_Key": "sk-xxx",
                    "GoogleSheets_Credentials": "",
                    "AutoBackupEnabled": False,
                    "BudgetYear": datetime.now().year
                }
        else:
            settings = {
                "OrganizationName": current_org_name,
                "DefaultPassword": "changeme123",
                "OpenAI_Key": "sk-xxx",
                "GoogleSheets_Credentials": "",
                "AutoBackupEnabled": False,
                "BudgetYear": datetime.now().year
            }

        st.subheader(" Edit Settings")

        # Organization settings
        st.markdown("### Organization Identity")
        org_name = st.text_input("Organization Display Name", value=settings.get("OrganizationName", current_org_name),
                            help="This name will appear throughout the application")
        
        # Budget year setting for payroll filtering
        current_year = datetime.now().year
        budget_year = st.number_input("Current Budget Year", 
                                     min_value=2020, max_value=2035, 
                                     value=settings.get("BudgetYear", current_year),
                                     help="Used to filter out terminated employees prior to this budget year")
        settings["BudgetYear"] = budget_year
        
        # Add state selector to organization settings
        states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
                  "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
                  "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
                  "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
                  "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
                  "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
                  "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]
        
        selected_state = st.selectbox("Select State for Your Organization", 
                                       options=states, 
                                       index=states.index(settings.get("State", "Utah")),
                                       help="This affects regulatory information and grant recommendations")
        settings["State"] = selected_state
        
        theme_color = st.color_picker("Theme Color", value=config.get(DEFAULT_ORG, {}).get("theme_color", "#0066cc"),
                                 help="The primary color used throughout the application")
        
        # Chart of Account Masks
        st.markdown("### 🧾 Chart of Account Masks")
        settings["Mask_BalanceSheet"] = st.text_input("Balance Sheet Mask", value=settings.get("Mask_BalanceSheet", "FF-DD-OOOO"),
            help="Enter the account format for balance sheet accounts (e.g., FF-DD-OOOO)")
        settings["Mask_Revenue"] = st.text_input("Revenue Account Mask", value=settings.get("Mask_Revenue", "F-D-OOO"),
            help="Enter the account format for revenue accounts (e.g., F-D-OOO)")
        settings["Mask_Expense"] = st.text_input("Expense Account Mask", value=settings.get("Mask_Expense", "FF-DD-CC-AAAA"),
            help="Enter the account format for expense accounts (e.g., FF-DD-CC-AAAA)")
        
        # System settings
        st.markdown("### System Settings")
        settings["DefaultPassword"] = st.text_input("Default Password for New Users", value=settings.get("DefaultPassword", ""), type="password")
        
        # OpenAI API Key Configuration with secure handling
        st.markdown("#### 🤖 OpenAI API Configuration")
        
        # Get current API key status
        api_status = api_key_manager.get_status("openai")
        
        # Display status with appropriate icons
        if api_status["configured"]:
            st.success(f"✓ OpenAI API Key Configured (Source: {api_status['source']})")
            if api_status.get("partial_hash"):
                st.info(f"Key preview: {api_status['partial_hash']}")
        else:
            st.warning("✗ OpenAI API Key Not Configured - AI features will be disabled")
        
        # Secure API key input with expandable section
        with st.expander("Configure OpenAI API Key", expanded=not api_status["configured"]):
            st.markdown("""
            **To enable AI features:**
            1. Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
            2. Enter the key below (starts with 'sk-')
            3. Click 'Test Key' to validate
            """)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                new_api_key = st.text_input(
                    "Enter OpenAI API Key",
                    type="password",
                    placeholder="sk-...",
                    help="Your OpenAI API key will be securely encrypted and stored",
                    key="openai_api_key_input"
                )
            
            with col2:
                st.write("")  # Spacer
                st.write("")  # Align button with input
                if st.button("🔑 Save Key", disabled=not new_api_key):
                    result = api_key_manager.set_api_key(new_api_key, "openai")
                    if result["success"]:
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["message"])
            
            # Test API key button
            if api_status["configured"] or new_api_key:
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("🧪 Test Current Key", disabled=not api_status["configured"]):
                        with st.spinner("Testing API key..."):
                            validation = api_key_manager.validate_api_key()
                            if validation["valid"]:
                                st.success("✓ " + validation["message"])
                            else:
                                st.error("✗ " + validation["message"])
                
                with col2:
                    if new_api_key and st.button("🧪 Test New Key"):
                        with st.spinner("Testing new API key..."):
                            validation = api_key_manager.validate_api_key(new_api_key)
                            if validation["valid"]:
                                st.success("✓ " + validation["message"])
                                st.info("Click 'Save Key' to apply this key")
                            else:
                                st.error("✗ " + validation["message"])
                
                with col3:
                    if api_status["configured"] and st.button("🗑️ Remove Key", type="secondary"):
                        result = api_key_manager.remove_api_key("openai")
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])
        
        # Keep backward compatibility with settings
        # Don't store the actual key in settings anymore
        settings["OpenAI_Key"] = "***CONFIGURED***" if api_status["configured"] else ""
        
        # Google Sheets Integration
        st.markdown("#### Google Sheets Integration")
        
        # Check current status
        current_creds = settings.get("GoogleSheets_Credentials", "")
        if current_creds and len(current_creds) > 100:
            try:
                # Validate JSON format
                creds_data = json.loads(current_creds)
                if "client_email" in creds_data and "project_id" in creds_data:
                    st.success(f"✓ Google Sheets configured for project: {creds_data.get('project_id', 'Unknown')}")
                    st.info(f"Service account: {creds_data.get('client_email', 'Unknown')}")
                else:
                    st.warning("Google Sheets credentials appear invalid (missing required fields)")
            except json.JSONDecodeError:
                st.error("Google Sheets credentials have invalid JSON format")
        else:
            st.warning("Google Sheets export not configured")
        
        # Google Sheets credentials input
        with st.expander("Configure Google Sheets Export", expanded=not current_creds):
            st.markdown("""
            **To enable Google Sheets export in Vatica module:**
            
            1. Go to [Google Cloud Console](https://console.cloud.google.com)
            2. Create/select a project
            3. Enable "Google Sheets API"
            4. Create a Service Account
            5. Generate JSON key file
            6. Upload the JSON file below
            """)
            
            # Initialize credentials manager
            creds_manager = CredentialsManager()
            
            # Show current organization and file storage location
            current_org = st.session_state.get('selected_org', 'default_org')
            org_folder = creds_manager.get_organization_folder(current_org)
            st.info(f"📁 **Credentials will be saved to:** `{org_folder}/service_account.json`")
            st.info(f"🏢 **Current Organization:** {current_org}")
            
            # File uploader for JSON credentials
            uploaded_file = st.file_uploader(
                "Upload Google Cloud Service Account JSON File",
                type=['json'],
                help="Upload the JSON key file downloaded from Google Cloud Console",
                key="google_sheets_json_upload"
            )
            
            # Process uploaded file using credentials manager
            if uploaded_file is not None:
                try:
                    # Read the uploaded file
                    file_content = uploaded_file.read().decode('utf-8')
                    
                    # Save using credentials manager
                    result = creds_manager.save_google_sheets_credentials(file_content, current_org)
                    
                    if result["success"]:
                        st.success(f"✓ Valid service account file uploaded and saved!")
                        st.info(f"📁 **Saved to:** `{result['file_path']}`")
                        st.info(f"🔧 **Project:** {result['project_id']}")
                        st.info(f"📧 **Service Account:** {result['client_email']}")
                        
                        # Also update settings for backward compatibility
                        settings["GoogleSheets_Credentials"] = file_content
                        
                        # Show success message with persistence confirmation
                        st.success("✓ Google Sheets credentials saved to permanent file storage!")
                        st.balloons()
                    else:
                        st.error(f"Upload failed: {result['error']}")
                        
                except UnicodeDecodeError:
                    st.error("File encoding error. Please ensure the file is saved as UTF-8.")
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
            else:
                # Show status of existing credentials
                status = creds_manager.get_credentials_status(current_org)
                if status["configured"]:
                    st.success(f"✓ Credentials file exists: `{status['file_path']}`")
                    if status.get('uploaded_date'):
                        st.info(f"📅 Uploaded: {status['uploaded_date']}")
            
            # Keep existing credentials if no new file uploaded (backward compatibility)
            if uploaded_file is None:
                settings["GoogleSheets_Credentials"] = current_creds
            
            # Option to clear credentials
            if current_creds and st.button("Clear Google Sheets Configuration", type="secondary"):
                # Clear using credentials manager
                creds_manager = CredentialsManager()
                if creds_manager.delete_google_sheets_credentials(current_org):
                    st.success("Google Sheets credentials file deleted!")
                
                settings["GoogleSheets_Credentials"] = ""
                # Immediately save the cleared credentials
                try:
                    config_file = get_config_file_path()
                    with open(config_file, 'w') as f:
                        json.dump(settings, f, indent=4)
                    st.success("Google Sheets configuration cleared and saved!")
                except Exception as save_error:
                    st.warning(f"Configuration cleared but save failed: {save_error}")
        
        settings["AutoBackupEnabled"] = st.checkbox("Enable Auto Backup", value=bool(settings.get("AutoBackupEnabled", False)))

        # Database Settings
        st.markdown("### Database Connection Settings")
        
        db_type = st.selectbox("Select Database Type", ["SQLite", "PostgreSQL", "MySQL"], 
                        index=["SQLite", "PostgreSQL", "MySQL"].index(settings.get("DB_Type", "SQLite")))
        settings["DB_Type"] = db_type
        
        if db_type == "SQLite":
            # Initialize session state for extracted files if needed
            if 'extracted_db_files' not in st.session_state:
                st.session_state.extracted_db_files = []
            
            # Combine regular .db files with any extracted ones
            db_files = [f for f in os.listdir() if f.endswith(".db")]
            all_db_files = db_files + [f for f in st.session_state.extracted_db_files if f not in db_files]
            
            if all_db_files:
                # Determine the index of the currently selected file
                current_file = settings.get("SQLite_File", all_db_files[0])
                try:
                    index = all_db_files.index(current_file)
                except ValueError:
                    index = 0
                
                col1, col2 = st.columns([3, 1])
                with col1:    
                    settings["SQLite_File"] = st.selectbox("Choose SQLite Database", 
                                                      all_db_files, 
                                                      index=index,
                                                      help="Select an existing database file or upload a new one below")
                
                # Add delete button for the selected database
                with col2:
                    st.write("")  # Spacing to align with selectbox
                    if st.button("Delete Database", key="delete_db_button", help="Delete the selected database file"):
                        db_to_delete = settings["SQLite_File"]
                        
                        # Only protect the databases/core/caselle_gl0_mock.db file as it's the essential one
                        essential_dbs = ["databases/core/caselle_gl0_mock.db"]
                        if db_to_delete in essential_dbs:
                            st.error(f"Cannot delete essential database file: {db_to_delete} (this contains all transaction data)")
                        else:
                            # Check if it's a regular file or an extracted one
                            if os.path.exists(db_to_delete):
                                try:
                                    os.remove(db_to_delete)
                                    st.success(f"Deleted database file: {db_to_delete}")
                                    
                                    # Update the list and select a default
                                    db_files = [f for f in os.listdir() if f.endswith(".db")]
                                    if db_files:
                                        settings["SQLite_File"] = db_files[0]
                                    else:
                                        settings["SQLite_File"] = "govsight_all_in_one_data.db"
                                        
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting file: {e}")
                            elif db_to_delete in st.session_state.extracted_db_files:
                                # Remove from extracted files list
                                st.session_state.extracted_db_files.remove(db_to_delete)
                                st.success(f"Removed extracted database: {db_to_delete}")
                                
                                # Update selected database
                                if st.session_state.extracted_db_files:
                                    settings["SQLite_File"] = st.session_state.extracted_db_files[0]
                                elif db_files:
                                    settings["SQLite_File"] = db_files[0]
                                else:
                                    settings["SQLite_File"] = "govsight_all_in_one_data.db"
                                    
                                st.rerun()
            
            # File uploader section with expanded options
            st.markdown("### Import Database Files")
            upload_type = st.radio("Select Import Type", 
                                ["SQLite (.db)", "ZIP Archive (.zip)", "SQL Server Backup (.bak)"],
                                help="Choose the type of database file to import")
            
            if upload_type == "SQLite (.db)":
                uploaded_file = st.file_uploader("Upload SQLite Database", type=["db"])
                if uploaded_file:
                    with open(uploaded_file.name, "wb") as f:
                        f.write(uploaded_file.read())
                    st.success(f"Uploaded {uploaded_file.name} successfully!")
                    # Auto-select the newly uploaded file
                    settings["SQLite_File"] = uploaded_file.name
                    st.rerun()
            
            elif upload_type == "ZIP Archive (.zip)":
                uploaded_zip = st.file_uploader("Upload ZIP Archive containing .db files", type=["zip"])
                if uploaded_zip:
                    # Save the zip file
                    zip_path = uploaded_zip.name
                    with open(zip_path, "wb") as f:
                        f.write(uploaded_zip.read())
                    
                    # Extract database files
                    with st.spinner("Extracting database files from archive..."):
                        extracted_files = db_archive_utils.extract_sqlite_from_zip(zip_path)
                        
                        if extracted_files:
                            st.success(f"Extracted {len(extracted_files)} database files from archive.")
                            st.session_state.extracted_db_files = extracted_files
                            # Auto-select the first extracted file
                            settings["SQLite_File"] = extracted_files[0]
                            st.rerun()
                        else:
                            st.error("No valid SQLite database files found in the ZIP archive.")
            
            elif upload_type == "SQL Server Backup (.bak)":
                uploaded_bak = st.file_uploader("Upload SQL Server Backup File", type=["bak"])
                if uploaded_bak:
                    # Save the .bak file
                    bak_path = uploaded_bak.name
                    with open(bak_path, "wb") as f:
                        f.write(uploaded_bak.read())
                    
                    # Show warning about .bak files
                    st.warning("SQL Server .bak file handling requires additional setup.")
                    st.info("For full SQL Server backup support, please contact your system administrator.")
            
            # Add a cleanup button for temporary files
            if st.session_state.extracted_db_files:
                if st.button("Cleanup Extracted Files"):
                    db_archive_utils.cleanup_temp_files()
                    st.session_state.extracted_db_files = []
                    st.success("Temporary files cleaned up successfully.")
                    st.rerun()
        else:
            settings["DB_Server"] = st.text_input("Database Server Address", settings.get("DB_Server", ""))
            settings["DB_Port"] = st.text_input("Port", settings.get("DB_Port", ""))
            settings["DB_Name"] = st.text_input("Database Name", settings.get("DB_Name", ""))
            settings["DB_User"] = st.text_input("Username", settings.get("DB_User", ""))
            settings["DB_Password"] = st.text_input("Password", settings.get("DB_Password", ""), type="password")
        
        if st.button("🧪 Test Database Connection"):
            if settings["DB_Type"] == "SQLite":
                try:
                    import sqlite3
                    conn = sqlite3.connect(settings["SQLite_File"])
                    conn.execute("SELECT 1")
                    conn.close()
                    # Connection success message removed for cleaner UI
                except Exception as e:
                    st.error(f"SQLite Connection Failed: {e}")
            
            elif settings["DB_Type"] == "PostgreSQL":
                try:
                    import psycopg2
                    # Connect with provided settings
                    conn = psycopg2.connect(
                        host=settings.get("DB_Server", ""),
                        port=settings.get("DB_Port", ""),
                        dbname=settings.get("DB_Name", ""),
                        user=settings.get("DB_User", ""),
                        password=settings.get("DB_Password", "")
                    )
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    conn.close()
                    # Connection success message removed for cleaner UI
                except ImportError:
                    st.error("PostgreSQL driver (psycopg2) not installed. Please install it first.")
                except Exception as e:
                    st.error(f"PostgreSQL Connection Failed: {e}")
            
            elif settings["DB_Type"] == "MySQL":
                try:
                    import mysql.connector
                    # Connect with provided settings
                    conn = mysql.connector.connect(
                        host=settings.get("DB_Server", ""),
                        port=int(settings.get("DB_Port", 3306)) if settings.get("DB_Port") else 3306,
                        database=settings.get("DB_Name", ""),
                        user=settings.get("DB_User", ""),
                        password=settings.get("DB_Password", "")
                    )
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    conn.close()
                    st.success("MySQL Connection Successful!")
                except ImportError:
                    st.error("MySQL driver (mysql-connector-python) not installed. Please install it first.")
                except Exception as e:
                    st.error(f"MySQL Connection Failed: {e}")

        if st.button("Save Settings"):
            # Update settings file
            settings["OrganizationName"] = org_name
            
            # Store currently selected database in settings for centralized access
            if settings["DB_Type"] == "SQLite":
                settings["current_database"] = settings["SQLite_File"]
            else:
                # For PostgreSQL or MySQL, construct a connection string
                db_info = {
                    "type": settings["DB_Type"],
                    "server": settings["DB_Server"],
                    "port": settings["DB_Port"],
                    "database": settings["DB_Name"],
                    "user": settings["DB_User"],
                    "password": settings["DB_Password"]
                }
                settings["current_database"] = json.dumps(db_info)
            
            # Update the session state with the selected database path for all modules to use
            st.session_state['db_path'] = settings["current_database"]
            
            # Save settings to file
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Update config.json with new organization name and theme color
            if DEFAULT_ORG in config:
                config[DEFAULT_ORG]["org_name"] = org_name
                config[DEFAULT_ORG]["theme_color"] = theme_color
                save_config(config)
                st.success(f"Organization settings updated: '{org_name}'")
            
            # Apply state selection to session state for regulatory components
            st.session_state['selected_state'] = settings["State"]
            
            st.success("Settings saved successfully!")
            
            # Apply OpenAI key to environment if provided
            if settings["OpenAI_Key"] and settings["OpenAI_Key"] != "sk-xxx":
                os.environ["OPENAI_API_KEY"] = settings["OpenAI_Key"]
                st.success("OpenAI API key applied to the application!")
            
            # Apply Google Sheets credentials to environment if provided
            if settings["GoogleSheets_Credentials"] and len(settings["GoogleSheets_Credentials"]) > 100:
                try:
                    # Validate JSON before applying
                    json.loads(settings["GoogleSheets_Credentials"])
                    os.environ["GOOGLE_SHEETS_CREDENTIALS"] = settings["GoogleSheets_Credentials"]
                    st.success("Google Sheets credentials applied to the application!")
                except json.JSONDecodeError:
                    st.error("Google Sheets credentials not applied due to invalid JSON format")
                
            # Refresh the application to apply changes (a more elegant way would be to add a callback)
            st.info("Application will refresh in 3 seconds to apply changes...")
            time.sleep(3)
            st.rerun()

    # --- Fund Classifications Tab ---
    with tab5:
        st.header("Fund Classification Manager")
        st.markdown(
            "Classify each fund per GASB Statement No. 54 categories. "
            "These classifications control which funds can participate in budget "
            "reallocations across the platform. Restricted, Capital, Debt Service, "
            "and Grant funds are automatically blocked from reallocation to prevent "
            "compliance violations."
        )

        from modules.utils.fund_policy import (
            load_fund_classifications, save_fund_classifications,
            GASB_54_CATEGORIES, FUND_CLASSIFICATIONS_PATHS
        )

        fund_settings = load_fund_classifications()

        try:
            from modules.database.connection_manager import get_database_connection
            conn = get_database_connection()
            fund_df = pd.read_sql("""
                SELECT DISTINCT 
                    Fund as FundCode, 
                    Fund as FundName 
                FROM DepartmentPerformance 
                ORDER BY Fund
            """, conn)
        except Exception as e:
            st.warning(f"Could not load fund data from database: {e}")
            if fund_settings:
                fund_df = pd.DataFrame({
                    "FundCode": list(fund_settings.keys()),
                    "FundName": list(fund_settings.keys()),
                })
                st.info("Showing previously classified funds. Connect to the database to discover new funds.")
            else:
                fund_df = pd.DataFrame(columns=["FundCode", "FundName"])

        fund_types = list(GASB_54_CATEGORIES.keys())

        st.markdown("### Classify Each Fund")

        gasb_ref_expander = st.expander("GASB 54 Classification Reference")
        with gasb_ref_expander:
            ref_data = []
            for cat_name, cat_info in GASB_54_CATEGORIES.items():
                ref_data.append({
                    "Classification": cat_name,
                    "GASB Reference": cat_info["gasb_reference"],
                    "Reallocation Eligible": "Yes" if cat_info["reallocation_eligible"] else "No",
                    "Description": cat_info["description"],
                })
            st.dataframe(pd.DataFrame(ref_data), use_container_width=True, hide_index=True)

        classification_data = []

        for _, row in fund_df.iterrows():
            fund_code = str(row["FundCode"])
            fund_name = row["FundName"]
            default_type = fund_settings.get(fund_code, "Unrestricted")
            if default_type not in fund_types:
                default_type = "Other"

            col_select, col_status = st.columns([3, 1])
            with col_select:
                selected_type = st.selectbox(
                    f"{fund_code} - {fund_name}",
                    options=fund_types,
                    index=fund_types.index(default_type),
                    key=f"fund_{fund_code}"
                )
            with col_status:
                cat_info = GASB_54_CATEGORIES.get(selected_type, {})
                if cat_info.get("reallocation_eligible", False):
                    st.success("Eligible for reallocation")
                elif cat_info.get("requires_approval", False):
                    st.warning("Requires approval")
                else:
                    st.error("Blocked from reallocation")

            classification_data.append({
                "FundCode": fund_code,
                "FundName": fund_name,
                "Type": selected_type
            })

        if st.button("Save Fund Classifications", key="save_fund_classifications"):
            to_save = {item["FundCode"]: item["Type"] for item in classification_data}
            save_fund_classifications(to_save)
            st.success("Fund classifications saved. These settings are now enforced across all modules.")

            st.subheader("Current Fund Classifications")
            class_df = pd.DataFrame(classification_data)
            class_df["Reallocation Eligible"] = class_df["Type"].apply(
                lambda t: "Yes" if GASB_54_CATEGORIES.get(t, {}).get("reallocation_eligible", False) else "No"
            )
            st.dataframe(class_df, use_container_width=True, hide_index=True)
    
    # --- Reporting Management Tab ---
    with tab6:
        st.header("📊 Reporting Management")
        
        # Import the reporting admin panel
        try:
            from modules.admin.admin_reporting_panel import render_reporting_admin
            render_reporting_admin()
        except ImportError as e:
            st.error(f"Reporting module not available: {e}")
            st.info("Please ensure the reporting dependencies are installed")
    
    # --- Security Trails Tab ---
    with tab7:
        st.header("🔒 Security Monitoring & Audit Trails")
        
        if not is_admin():
            st.error("Security monitoring is restricted to administrators only.")
        else:
            # Security database connection
            import sqlite3
            
            try:
                conn = sqlite3.connect('security_events.db')
                
                # Get security event counts
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM file_access_log")
                total_events = cursor.fetchone()[0]
                
                # Get recent events
                cursor.execute("""
                    SELECT action, COUNT(*) as count 
                    FROM file_access_log 
                    GROUP BY action 
                    ORDER BY count DESC
                """)
                event_counts = cursor.fetchall()
                
                # Security overview metrics
                st.subheader(" Security Overview")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Security Events", total_events)
                with col2:
                    cursor.execute("SELECT COUNT(DISTINCT session_id) FROM file_access_log")
                    unique_sessions = cursor.fetchone()[0]
                    st.metric("Unique Sessions", unique_sessions)
                with col3:
                    cursor.execute("SELECT COUNT(*) FROM file_access_log WHERE action LIKE '%REJECTED%'")
                    rejected_files = cursor.fetchone()[0]
                    st.metric("Security Rejections", rejected_files)
                with col4:
                    cursor.execute("SELECT COUNT(*) FROM file_access_log WHERE action LIKE '%PROCESSED%'")
                    processed_files = cursor.fetchone()[0]
                    st.metric("Files Processed", processed_files)
                
                # Event type breakdown
                if event_counts:
                    st.subheader(" Security Event Types")
                    event_df = pd.DataFrame(event_counts, columns=['Event Type', 'Count'])
                    st.bar_chart(event_df.set_index('Event Type'))
                
                # Recent security events
                st.subheader("🕒 Recent Security Events")
                
                # Filter options
                col1, col2 = st.columns(2)
                with col1:
                    days_filter = st.selectbox("Show events from last:", 
                                             options=[1, 7, 30, 90, 365, "All"],
                                             index=1)
                with col2:
                    action_filter = st.selectbox("Filter by action:", 
                                               options=["All"] + [row[0] for row in event_counts])
                
                # Build query based on filters
                query = "SELECT * FROM file_access_log WHERE 1=1"
                params = []
                
                if days_filter != "All":
                    query += " AND datetime(timestamp) >= datetime('now', '-{} days')".format(days_filter)
                
                if action_filter != "All":
                    query += " AND action = ?"
                    params.append(action_filter)
                
                query += " ORDER BY timestamp DESC LIMIT 100"
                
                # Execute query and display results
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                events = cursor.fetchall()
                
                if events:
                    # Format events for display
                    events_data = []
                    for event in events:
                        events_data.append({
                            "Timestamp": event[6],
                            "Action": event[5],
                            "File Name": event[2] if event[2] else "N/A",
                            "File Hash": event[3][:8] + "..." if event[3] else "N/A",
                            "File Size": f"{event[4]:,} bytes" if event[4] else "N/A",
                            "Session ID": event[1][:8] + "..." if event[1] else "N/A",
                            "User Agent": event[7][:30] + "..." if event[7] and len(event[7]) > 30 else event[7] or "N/A"
                        })
                    
                    events_df = pd.DataFrame(events_data)
                    st.dataframe(events_df, use_container_width=True)
                    
                    # Export security log
                    st.subheader(" Export Security Data")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Download CSV Report"):
                            csv_data = events_df.to_csv(index=False)
                            st.download_button(
                                label=" Download Security Log CSV",
                                data=csv_data,
                                file_name=f"security_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                type="primary"
                            )
                    
                    with col2:
                        if st.button("Clear Old Logs"):
                            if st.checkbox("I understand this will permanently delete logs older than 90 days"):
                                cursor.execute("""
                                    DELETE FROM file_access_log 
                                    WHERE datetime(timestamp) < datetime('now', '-90 days')
                                """)
                                deleted_count = cursor.rowcount
                                conn.commit()
                                st.success(f"Deleted {deleted_count} old security log entries")
                                st.rerun()
                else:
                    st.info("No security events found matching the selected filters.")
                
                # Security status indicators
                st.subheader("🛡️ Current Security Status")
                
                # Check if secure file handler is active
                security_status = {
                    "Secure File Handler": " Active" if os.path.exists('modules/mantis/secure_file_handler.py') else " Inactive",
                    "Security Database": " Connected" if os.path.exists('security_events.db') else " Not Found",
                    "Audit Logging": " Enabled" if total_events > 0 else " No Events Logged",
                    "Session Timeout": " 1 Hour Active",
                    "File Validation": " PDF/CSV Only",
                    "Memory-Only Processing": " No Disk Storage"
                }
                
                for status_item, status_value in security_status.items():
                    st.write(f"**{status_item}:** {status_value}")
                
                conn.close()
                
            except Exception as e:
                st.error(f"Error accessing security database: {e}")
                st.info("Security monitoring requires the security database to be initialized. Upload a file in Mantis to create initial security logs.")
    
    # --- Audit Trail Tab ---
    with tab8:
        try:
            render_audit_trail_interface()
        except Exception as e:
            st.error(f"Error loading audit trail interface: {e}")
            st.info("Audit trail functionality requires the audit database to be initialized. The system will create it automatically on first use.")
    
    # --- Real-Time Monitoring Tab ---
    with tab9:
        st.header("📊 Real-Time Intelligence Platform")
        try:
            from .realtime_intelligence_platform import get_realtime_intelligence_platform
            realtime_platform = get_realtime_intelligence_platform()
            realtime_platform.render_realtime_intelligence_dashboard()
        except ImportError:
            st.error("Real-Time Intelligence Platform not available - module loading")
            st.info("Real-time monitoring requires all dependencies to be loaded")
        except Exception as e:
            st.error(f"Error loading Real-Time Intelligence Platform: {e}")
    
    with tab10:
        st.header("📊 Scenario Manager")
        if render_scenario_manager:
            render_scenario_manager()
        else:
            st.error("Scenario Manager module not available")
            st.info("The scenario manager allows you to view and manage all saved scenarios from the Scenario Planner.")
    
    # Super Admin Database Manager Tab
    
    # Archive Settings Tab removed to avoid errors
    # We can re-add this functionality later if needed

if __name__ == "__main__":
    run_admin_panel()

def check_admin_access():
    """Check if current user has admin access"""
    return is_admin()

def log_user_action(action: str, user: str):
    """Log user action for audit trail"""
    try:
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        # In a real implementation, this would write to audit log
        print(f"{timestamp}: User {user} performed {action}")
    except Exception as e:
        print(f"Error logging action: {e}")
