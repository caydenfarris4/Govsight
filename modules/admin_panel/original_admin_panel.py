import streamlit as st
import pandas as pd
import admin_archive_manager as archive_mgr
import os
import json
import time
import csv
import zipfile
from datetime import datetime
from db_connection import load_config, save_config
import db_archive_utils

# --- Constants ---
USERS_FILE = "users_table.csv"
SETTINGS_FILE = "system_settings.json"
ARCHIVE_SETTINGS_FILE = "archive_settings.json"
DEFAULT_ORG = "cityA"  # Default organization ID

# --- User Roles (Default Users) ---
DEFAULT_USERS = {
    "admin_user": {"role": "admin", "departments": "all", "password": "govsight123"},
    "finance_director": {"role": "finance", "departments": "all", "password": "govsight123"},
    "pw_manager": {"role": "manager", "departments": ["Public Works"], "password": "govsight123"},
    "police_manager": {"role": "manager", "departments": ["Police"], "password": "govsight123"},
    "parks_manager": {"role": "manager", "departments": ["Parks & Rec"], "password": "govsight123"},
}

# --- Security Functions ---
def login():
    # Force sidebar to be collapsed for login screen
    st.session_state.sidebar_collapsed = True
    
    # Center the login form in the main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Add GovSight logo to login page
        try:
            # Center the logo
            logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
            with logo_col2:
                st.image("govsight_logo.png", width=250)
        except:
            # Fallback if logo file is not found
            st.markdown("### GovSight")
        
        st.title("Login")
        st.markdown("#### Enter your credentials to access the Financial Analyzer")
        
        # Put login form in the main content area
        with st.form("login_form", clear_on_submit=False):
            st.write("---")
            username = st.text_input("Username", value="admin_user", key="username_input")
            password = st.text_input("Password", type="password", key="password_input")
            submit = st.form_submit_button("Login", use_container_width=True)
            st.write("---")
            
            # Load users from file or use defaults
            users = load_users()
            
            # Check if Enter was pressed (form submitted)
            if submit or ('login_attempted' in st.session_state and st.session_state.login_attempted):
                user = users.get(username)
                
                # Check the user's password or use default password as fallback
                settings = load_settings()
                default_password = settings.get("DefaultPassword", "govsight123")
                user_password = user.get("password", default_password) if user else None
                
                # Enhanced authentication with better validation
                if user and password and (password == user_password):
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
                    st.session_state.login_attempted = False
                    
                    # Maintain sidebar collapsed state
                    st.session_state.sidebar_collapsed = True
                    
                    # Show success message
                    st.success(f"Logged in as {username} ({user['role']})")
                    
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
        tabs = ["Dashboard", "Scenario Planner", "Department Insights", "AI Assistant", "Historical Analysis", "BI Sandbox", "Balance Sheet", "Transaction Analyzer", "Reports", "Admin Panel"]
    elif role == "finance":
        tabs = ["Dashboard", "Scenario Planner", "Department Insights", "AI Assistant", "Historical Analysis", "BI Sandbox", "Balance Sheet", "Transaction Analyzer", "Reports"]
    elif role == "manager":
        tabs = ["Dashboard", "Scenario Planner", "Department Insights", "Historical Analysis", "BI Sandbox", "Transaction Analyzer"]

    return tabs

def load_users():
    """Load users from a CSV file or return default users if file doesn't exist"""
    if os.path.exists(USERS_FILE):
        try:
            users = {}
            with open(USERS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert departments string to list if not "all"
                    if row.get("Departments", "").lower() != "all":
                        departments = [d.strip() for d in row.get("Departments", "").split(",") if d.strip()]
                    else:
                        departments = "all"
                    
                    users[row["Username"]] = {
                        "role": row["Role"],
                        "departments": departments,
                        "password": row.get("Password", "govsight123")
                    }
            return users
        except Exception as e:
            st.error(f"Error loading users: {e}")
            return DEFAULT_USERS
    else:
        return DEFAULT_USERS

def save_users(users):
    """Save users to a CSV file"""
    try:
        with open(USERS_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Username", "Role", "Departments", "Password"])
            writer.writeheader()
            for username, details in users.items():
                depts = details["departments"]
                if isinstance(depts, list):
                    depts = ", ".join(depts)
                writer.writerow({
                    "Username": username,
                    "Role": details["role"],
                    "Departments": depts,
                    "Password": details.get("password", "govsight123")
                })
        return True
    except Exception as e:
        st.error(f"Error saving users: {e}")
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
                "AutoBackupEnabled": False
            }
    else:
        return {
            "OrganizationName": "City A",
            "DefaultPassword": "govsight123",
            "OpenAI_Key": "",
            "AutoBackupEnabled": False
        }

def run_admin_panel():
    st.title("Admin Control Panel")

    if not is_admin() and not is_finance_director():
        st.error("You are not authorized to view this page.")
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(["👥 Manage Users", "📂 Archive Viewer", "⚙️ System Settings", "🏦 Fund Classifications"])

    # --- Manage Users Tab ---
    with tab1:
        st.header("👥 Manage System Users")

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
        st.subheader(" Add/Edit User")
        
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
            else:
                users.pop(new_username)
                if save_users(users):
                    st.success(f"User '{new_username}' deleted successfully!")
                    st.rerun()  # Refresh the page to show updated user list

    # --- Archive Viewer Tab ---
    with tab2:
        st.header("📂 Scenario Reports Archive")

        archive_df = archive_mgr.load_archive_metadata()
        
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
    with tab3:
        st.header("⚙️ System Settings")

        # Load the app configuration and get current organization name
        config = load_config()
        current_org_name = config.get(DEFAULT_ORG, {}).get("org_name", "City A")

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
                    "AutoBackupEnabled": False,
                    "DB_Type": "SQLite",
                    "SQLite_File": "govsight_all_in_one_data.db",
                    "DB_Server": "",
                    "DB_Port": "",
                    "DB_Name": "",
                    "DB_User": "",
                    "DB_Password": ""
                }
        else:
            settings = {
                "OrganizationName": current_org_name,
                "DefaultPassword": "changeme123",
                "OpenAI_Key": "sk-xxx",
                "AutoBackupEnabled": False,
                "DB_Type": "SQLite",
                "SQLite_File": "govsight_all_in_one_data.db",
                "DB_Server": "",
                "DB_Port": "",
                "DB_Name": "",
                "DB_User": "",
                "DB_Password": ""
            }

        st.subheader(" Edit Settings")

        # Organization settings
        st.markdown("### Organization Identity")
        org_name = st.text_input("Organization Display Name", value=settings.get("OrganizationName", current_org_name),
                            help="This name will appear throughout the application")
        
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
        settings["OpenAI_Key"] = st.text_input("OpenAI API Key", value=settings.get("OpenAI_Key", ""), type="password")
        settings["AutoBackupEnabled"] = st.checkbox("Enable Auto Backup", value=bool(settings.get("AutoBackupEnabled", False)))

        # Database Settings
        st.markdown("###  Database Connection Settings")
        
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
                    st.success("SQLite Database Connected Successfully!")
                except Exception as e:
                    st.error(f" SQLite Connection Failed: {e}")
            
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
                    st.success("PostgreSQL Connection Successful!")
                except ImportError:
                    st.error(" PostgreSQL driver (psycopg2) not installed. Please install it first.")
                except Exception as e:
                    st.error(f" PostgreSQL Connection Failed: {e}")
            
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
                    st.error(" MySQL driver (mysql-connector-python) not installed. Please install it first.")
                except Exception as e:
                    st.error(f" MySQL Connection Failed: {e}")

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
                
            # Refresh the application to apply changes (a more elegant way would be to add a callback)
            st.info("Application will refresh in 3 seconds to apply changes...")
            time.sleep(3)
            st.rerun()

    # --- Fund Classifications Tab ---
    with tab4:
        st.header("🏦 Fund Classification Manager")
        
        # Constants
        FUND_SETTINGS_FILE = "fund_classifications.json"
        
        # Connect to the database and pull fund data from the correct table
        try:
            from db_connection import get_connection
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
            # Create empty dataframe if database access fails
            fund_df = pd.DataFrame(columns=["FundCode", "FundName"])
        
        # Load previous classifications if available
        if os.path.exists(FUND_SETTINGS_FILE):
            with open(FUND_SETTINGS_FILE, "r") as f:
                fund_settings = json.load(f)
        else:
            fund_settings = {}
        
        # Fund types
        fund_types = ["Unrestricted", "Restricted", "Capital", "Debt Service", "Grant", "Other"]
        
        # Display table
        st.markdown("### Classify Each Fund")
        st.write("This classification helps organize financial data and reporting by fund type.")
        
        classification_data = []
        
        for _, row in fund_df.iterrows():
            fund_code = str(row["FundCode"])
            fund_name = row["FundName"]
            default_type = fund_settings.get(fund_code, "Unrestricted")
            selected_type = st.selectbox(
                f"{fund_code} - {fund_name}", 
                options=fund_types, 
                index=fund_types.index(default_type),
                key=f"fund_{fund_code}"
            )
            classification_data.append({"FundCode": fund_code, "FundName": fund_name, "Type": selected_type})
        
        # Save on click
        if st.button("Save Fund Classifications", key="save_fund_classifications"):
            to_save = {item["FundCode"]: item["Type"] for item in classification_data}
            with open(FUND_SETTINGS_FILE, "w") as f:
                json.dump(to_save, f, indent=4)
            st.success("Fund classifications saved successfully!")
            
            # Show current classifications as a table
            st.subheader("Current Fund Classifications")
            class_df = pd.DataFrame(classification_data)
            st.dataframe(class_df, use_container_width=True)
    
    # Archive Settings Tab removed to avoid errors
    # We can re-add this functionality later if needed

if __name__ == "__main__":
    run_admin_panel()