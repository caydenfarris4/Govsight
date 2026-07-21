import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sqlite3
import json
import os
from datetime import datetime
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Set page config
st.set_page_config(
    page_title="GovSight Financial Analyzer",
    page_icon="",
    layout="wide"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #0066cc;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #444;
    }
    .info-box {
        background-color: #f0f7ff;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #0066cc;
    }
    .org-banner {
        background-color: #0066cc;
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .department-data {
        font-size: 0.9rem;
    }
    .password-container {
        max-width: 500px;
        margin: 100px auto;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        background-color: white;
    }
    .ai-response {
        background-color: #f8f9fa;
        border-left: 4px solid #0066cc;
        padding: 15px;
        border-radius: 5px;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Load config
try:
    with open("config.json") as f:
        CONFIG = json.load(f)
except Exception as e:
    st.error(f"Error loading configuration: {e}")
    CONFIG = {}

# Parse org from query parameters
org = st.query_params.get("org", None)

# Set default values for organization display
org_display_name = "GovSight Portal"
org_theme_color = "#0066cc"

# Handle organization selection logic
if not org or org not in CONFIG:
    # Show organization selection screen
    st.title(" GovSight: Multi-Organization Portal")
    st.markdown("""
    <div class="info-box">
    Please select an organization to continue:
    </div>
    """, unsafe_allow_html=True)
    
    # Display available organizations with styled cards
    if CONFIG:
        cols = st.columns(min(len(CONFIG), 2))
        for i, (org_name, org_data) in enumerate(CONFIG.items()):
            col_idx = i % len(cols)
            with cols[col_idx]:
                org_title = org_data.get("org_name", org_name)
                theme_color = org_data.get("theme_color", "#0066cc")
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 10px; margin-bottom: 20px; background-color: {theme_color}; color: white;">
                    <h3 style="margin-top: 0;">{org_title}</h3>
                    <p>Database: {org_data.get('database', 'N/A')}</p>
                    <p>Budget Ceiling: ${org_data.get('budget_ceiling', 'N/A'):,}</p>
                    <a href="?org={org_name}" target="_self" style="background-color: white; color: {theme_color}; 
                       padding: 8px 16px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                       Access Portal
                    </a>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("No organization configurations found.")
    
    st.stop()
else:
    # We have a valid organization, get the config
    org_config = CONFIG[org]
    org_display_name = org_config.get("org_name", org)
    org_theme_color = org_config.get("theme_color", "#0066cc")

# Password Authentication - Automatic login from query parameter
# Add a query parameter for auto-login
auto_login = st.query_params.get("auth", None)

if "authenticated" not in st.session_state:
    if auto_login == "true":
        # Auto login if auth=true is in the URL
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False

# Check if authentication is required
if not st.session_state.authenticated and "login_password" in org_config:
    st.markdown(f"""
    <div class="password-container" style="border-top: 5px solid {org_theme_color};">
        <h2 style="text-align: center; color: {org_theme_color};">🔒 {org_display_name} Portal</h2>
        <p style="text-align: center;">Please enter your access password to continue.</p>
    </div>
    """, unsafe_allow_html=True)
    
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if password == org_config["login_password"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    
    # Stop execution until authenticated
    st.stop()

# Header with organization info
st.markdown(f"""
<div class="org-banner" style="background-color: {org_theme_color};">
    <div>
        <h1 style="margin:0"> GovSight Financial Analyzer</h1>
        <h3 style="margin:0; opacity:0.8">Connected to: {org_display_name}</h3>
    </div>
    <div>
        <a href="/" target="_self" style="color:white; text-decoration:none; background-color:rgba(255,255,255,0.2); padding:5px 10px; border-radius:5px;">
            Switch Organization
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar information
st.sidebar.markdown(f"### {org_display_name} Details")
st.sidebar.markdown(f"**Database:** {org_config['database']}")
st.sidebar.markdown(f"**Budget Ceiling:** ${org_config.get('budget_ceiling', 'N/A'):,}")

# Database Connection Functions
def get_connection(db_name='budget.db'):
    """Create a connection to the SQLite database"""
    try:
        # In a real implementation, this would use the db_config to connect to the org's database
        # For now, we'll continue using the local SQLite database for demonstration
        return sqlite3.connect(db_name)
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        return None

def execute_query(query, params=(), fetchall=True):
    """Execute a query and return results"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
            if fetchall:
                return cursor.fetchall()
            else:
                return cursor.fetchone()
        else:
            conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        st.error(f"Query execution error: {e}")
        return None
    finally:
        conn.close()

def get_departments():
    """Get all departments from the database"""
    query = "SELECT id, name, total_budget, underspent FROM departments"
    departments_data = execute_query(query)
    
    if not departments_data:
        return {}
    
    # Convert to dictionary with department name as key
    departments = {}
    for dept in departments_data:
        departments[dept[1]] = {
            "id": dept[0],
            "budget": dept[2],
            "underspent": dept[3]
        }
    
    return departments

def get_projects():
    """Get all projects from the database"""
    query = "SELECT id, name, description, total_cost, status FROM projects"
    projects_data = execute_query(query)
    
    if not projects_data:
        return []
    
    # Convert to list of dictionaries
    projects = []
    for proj in projects_data:
        projects.append({
            "id": proj[0],
            "name": proj[1],
            "description": proj[2],
            "total_cost": proj[3],
            "status": proj[4]
        })
    
    return projects

def save_scenario(scenario_data, department_allocations):
    """Save a funding scenario to the database"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Insert scenario
        cursor.execute('''
        INSERT INTO scenarios 
        (name, project_id, total_cost, tax_revenue, grant_funding, private_investment, bonds_needed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            scenario_data['name'],
            scenario_data.get('project_id', 1),  # Default to first project if not specified
            scenario_data['Total Cost'],
            scenario_data['Tax Revenue'],
            scenario_data['Grant Funding'],
            scenario_data['Private Investment'],
            scenario_data['Bonds Needed']
        ))
        
        scenario_id = cursor.lastrowid
        
        # Insert department allocations
        for dept_name, amount in department_allocations.items():
            if amount > 0:  # Only insert non-zero allocations
                # Get department ID
                dept_id_query = "SELECT id FROM departments WHERE name = ?"
                cursor.execute(dept_id_query, (dept_name,))
                dept_id_result = cursor.fetchone()
                
                if dept_id_result:
                    dept_id = dept_id_result[0]
                    
                    # Insert allocation
                    cursor.execute('''
                    INSERT INTO scenario_department_allocations 
                    (scenario_id, department_id, allocation_amount)
                    VALUES (?, ?, ?)
                    ''', (scenario_id, dept_id, amount))
        
        conn.commit()
        return scenario_id
    except sqlite3.Error as e:
        st.error(f"Error saving scenario: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_scenarios(limit=6):
    """Get the most recent scenarios from the database"""
    query = '''
    SELECT s.id, s.name, p.name as project_name, s.total_cost, s.tax_revenue, 
           s.grant_funding, s.private_investment, s.bonds_needed, s.creation_date
    FROM scenarios s
    JOIN projects p ON s.project_id = p.id
    ORDER BY s.creation_date DESC
    LIMIT ?
    '''
    
    scenarios_data = execute_query(query, (limit,))
    
    if not scenarios_data:
        return []
    
    # Convert to list of dictionaries
    scenarios = []
    for s in scenarios_data:
        # Get department allocations for this scenario
        alloc_query = '''
        SELECT d.name, sda.allocation_amount
        FROM scenario_department_allocations sda
        JOIN departments d ON sda.department_id = d.id
        WHERE sda.scenario_id = ?
        '''
        allocations_data = execute_query(alloc_query, (s[0],))
        
        department_allocations = {}
        total_reallocation = 0
        if allocations_data:
            for alloc in allocations_data:
                department_allocations[alloc[0]] = alloc[1]
                total_reallocation += alloc[1]
        
        scenarios.append({
            "id": s[0],
            "name": s[1],
            "Project": s[2],
            "Total Cost": s[3],
            "Tax Revenue": s[4],
            "Grant Funding": s[5],
            "Private Investment": s[6],
            "Bonds Needed": s[7],
            "Date": s[8],
            "Department Allocations": department_allocations,
            "Departmental Reallocation": total_reallocation
        })
    
    return scenarios

# Add AI Assistant Functions
def run_dashboard_query(query, org_filter=None):
    """Execute a query against the dashboard database"""
    try:
        # Check for unsafe SQL operations
        banned = ["drop", "delete", "update", "insert", "alter"]
        if any(word in query.lower() for word in banned):
            return " Unsafe query blocked."
            
        conn = get_connection('org_dashboard_data.db')
        if not conn:
            return "Database connection error"
        
        cursor = conn.cursor()
        
        # SECURITY FIX: Use parameterized queries to prevent SQL injection
        params = []
        if org_filter:
            # Import security validator
            from security_sql_injection_fixes import SQLSecurityValidator
            
            try:
                # Validate organization name
                safe_org = SQLSecurityValidator.validate_organization_name(org_filter)
                
                # Add organization filter using parameterized query
                if "WHERE" in query.upper():
                    query = query.replace("WHERE", "WHERE Organization = ? AND")
                    params.insert(0, safe_org)
                elif "GROUP BY" in query.upper():
                    query = query.replace("GROUP BY", "WHERE Organization = ? GROUP BY")
                    params.insert(0, safe_org)
                else:
                    # Add WHERE before any ORDER BY, LIMIT, etc.
                    for clause in ["ORDER BY", "LIMIT", "HAVING"]:
                        if clause in query.upper():
                            parts = query.split(clause, 1)
                            query = f"{parts[0]} WHERE Organization = ? {clause}{parts[1]}"
                            params.insert(0, safe_org)
                            break
                    else:
                        query += " WHERE Organization = ?"
                        params.append(safe_org)
            except ValueError as e:
                return f"Invalid organization parameter: {e}"
        
        # Execute the parameterized query safely
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=columns)
        conn.close()
        return df
    except Exception as e:
        return f"Error executing query: {str(e)}"

def generate_sql_from_prompt(prompt, org_name, history=[]):
    """Generate SQL from prompt using OpenAI (if available)"""
    # Import security utilities
    from modules.security import validate_organization_name
    
    # Validate organization name
    try:
        org_name = validate_organization_name(org_name)
    except ValueError:
        return "SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = ? LIMIT 10"
    
    if not OPENAI_AVAILABLE:
        return "SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = ? LIMIT 10"
    
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        if not api_key:
            st.warning("OpenAI API key not found in secrets. Using default query.")
            return "SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = ? LIMIT 10"
        
        openai.api_key = api_key
        
        # Format history if provided
        history_block = ""
        if history:
            history_block = "\n".join([f"Q: {q['question']}\nA: {q['sql']}" for q in history[-3:]])
            history_block = f"\n{history_block}\n"
        
        messages = [
            {"role": "system", "content": f"You are an assistant that helps generate SQL queries for budget performance data for {org_name}."},
            {"role": "user", "content": f"""Here is my SQLite schema:
DepartmentPerformance(Department, Fund, FiscalYear, Budget, Actual, Month, Organization)

Current Organization: {org_name}
{history_block}
Question: {prompt}

Return only the SQL query without explanation. Do not include 'WHERE Organization = {org_name}' in your query as I will add that filter automatically."""}
        ]
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        sql_query = response['choices'][0]['message']['content'].strip()
        # Remove any code block markers
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        return sql_query
    except Exception as e:
        st.error(f"Error generating SQL: {str(e)}")
        return f"SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = '{org_name}' LIMIT 10"

def generate_ai_commentary(df, prompt=None):
    """Generate AI commentary on the data"""
    if not OPENAI_AVAILABLE:
        return "AI commentary not available."
    
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        if not api_key:
            return "AI commentary not available (API key missing)."
        
        openai.api_key = api_key
        
        # Convert DataFrame to CSV for the prompt
        data_preview = df.head(10).to_csv(index=False)
        
        if prompt:
            user_prompt = f"Based on the following financial data, answer this question: {prompt}\n\nData:\n{data_preview}"
        else:
            user_prompt = f"Based on the following financial data, provide brief insights or recommendations:\n{data_preview}"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You analyze financial tables and suggest insights for government financial data."},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Could not generate insights: {str(e)}"

# Main App Interface
# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Scenario Planner", "Historical Analysis", "Department Insights", "AI Assistant"])

with tab1:
    st.markdown('<div class="sub-header"> Funding Scenario Planner</div>', unsafe_allow_html=True)
    
    # Create columns for better layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Project details
        st.subheader("Project Details")
        
        # Load projects from database
        projects = get_projects()
        if not projects:
            st.warning(f" No projects found in {org}'s database. Using sample data.")
            selected_project_data = {"id": 0, "name": "Sample Project", "description": "Sample description", "total_cost": 2000000}
            project_id = 0
        else:
            project_options = {p["name"]: p for p in projects}
            
            selected_project = st.selectbox(
                "Select Project", 
                options=list(project_options.keys()),
                index=0
            )
            
            # Get selected project details
            selected_project_data = project_options[selected_project]
            project_id = selected_project_data["id"]
        
        # Display project description
        st.markdown(f"**Description:** {selected_project_data['description']}")
        
        # Allow cost adjustment
        project_cost = st.number_input(
            "Total Project Cost ($)", 
            min_value=100000, 
            max_value=50000000,
            value=int(selected_project_data["total_cost"]), 
            step=50000,
            format="%d"
        )
        
        # Primary funding sources
        st.subheader("Primary Funding Sources")
        tax_revenue = st.number_input("Projected Tax Revenue Increase ($)", 
                                    min_value=0, 
                                    value=500000, 
                                    step=50000,
                                    format="%d")
        grant = st.number_input("Grant Funding ($)", 
                              min_value=0, 
                              value=300000, 
                              step=50000,
                              format="%d")
        private_investment = st.number_input("Private Investment ($)", 
                                          min_value=0, 
                                          value=0, 
                                          step=50000,
                                          format="%d")

    with col2:
        # Department-level reallocation
        st.subheader("Department Budget Reallocation")
        st.markdown("""
        Departments can contribute unspent budget allocations to help fund the project.
        Select which departments to include and adjust the reallocation amounts.
        """)
        
        # Load departments from database
        departments = get_departments()
        if not departments:
            st.warning(f" No departments found in {org}'s database. Using sample data.")
            departments = {
                "Public Works": {"budget": 1200000, "underspent": 300000},
                "Administration": {"budget": 800000, "underspent": 150000}
            }
        
        # Calculate department reallocation
        total_reallocation = 0
        reallocated_amounts = {}
        
        # Create an expander for department allocations to save space
        with st.expander("Department Allocations", expanded=True):
            for dept, data in departments.items():
                col_check, col_slider = st.columns([1, 3])
                with col_check:
                    include = st.checkbox(f"{dept}", value=True if dept in ["Public Works", "Administration"] else False, key=f"check_{dept}")
                
                if include:
                    with col_slider:
                        max_allowable = min(data["budget"] * 0.10, data["underspent"])
                        reallocation = st.slider(
                            f"{dept} Reallocation", 
                            0, 
                            int(max_allowable), 
                            int(max_allowable / 2),
                            format="$%d",
                            key=f"slider_{dept}"
                        )
                        total_reallocation += reallocation
                        reallocated_amounts[dept] = reallocation
                        st.markdown(f'<div class="department-data">Budget: ${data["budget"]:,} | Underspent: ${data["underspent"]:,}</div>', unsafe_allow_html=True)

    # Calculate funding breakdown
    st.subheader("Funding Analysis")
    col_analysis1, col_analysis2 = st.columns([2, 1])
    
    with col_analysis1:
        # Calculate total funding and bond need
        funding_total = total_reallocation + tax_revenue + grant + private_investment
        bonds_needed = max(0, project_cost - funding_total)
        funding_percentage = (funding_total / project_cost) * 100 if project_cost > 0 else 0
        
        # Create funding breakdown chart
        categories = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", "Private Investment", "Bonds Needed"]
        values = [total_reallocation, tax_revenue, grant, private_investment, bonds_needed]
        colors = ["#6c5ce7", "#00b894", "#fdcb6e", "#e84393", "#d63031"]
        
        # Filter out zero values
        non_zero_categories = []
        non_zero_values = []
        non_zero_colors = []
        
        for cat, val, col in zip(categories, values, colors):
            if val > 0:
                non_zero_categories.append(cat)
                non_zero_values.append(val)
                non_zero_colors.append(col)
        
        # Create the stacked bar chart
        fig = go.Figure()
        for i, (cat, val, col) in enumerate(zip(non_zero_categories, non_zero_values, non_zero_colors)):
            fig.add_trace(
                go.Bar(
                    name=cat, 
                    x=["Funding Breakdown"], 
                    y=[val], 
                    marker_color=col,
                    text=[f"${val:,}"],
                    textposition="auto"
                )
            )
        
        fig.update_layout(
            barmode="stack",
            template="plotly_white",
            height=400,
            showlegend=True,
            legend_title="Funding Source",
            margin=dict(l=10, r=10, t=10, b=10),
            title=dict(
                text="Project Funding Breakdown",
                x=0.5,
                xanchor="center"
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Department reallocation breakdown if there are reallocations
        if reallocated_amounts:
            # Create pie chart for department reallocation
            dept_fig = go.Figure(data=[
                go.Pie(
                    labels=list(reallocated_amounts.keys()),
                    values=list(reallocated_amounts.values()),
                    hole=.4,
                    textinfo="label+percent",
                    marker=dict(colors=["#a29bfe", "#74b9ff", "#55efc4", "#81ecec", "#ffeaa7", "#fab1a0", "#ff7675"])
                )
            ])
            
            dept_fig.update_layout(
                title=dict(
                    text="Department Reallocation Breakdown",
                    x=0.5,
                    xanchor="center"
                ),
                height=350,
                margin=dict(l=10, r=10, t=50, b=10)
            )
            
            st.plotly_chart(dept_fig, use_container_width=True)

    with col_analysis2:
        # Summary statistics
        st.subheader("Funding Summary")
        
        # Create a metrics display
        col_metrics1, col_metrics2 = st.columns(2)
        
        with col_metrics1:
            st.metric("Total Project Cost", f"${project_cost:,}")
            st.metric("Total Secured Funding", f"${funding_total:,}")
        
        with col_metrics2:
            st.metric("Funding Gap", f"${bonds_needed:,}")
            st.metric("Funding Percentage", f"{funding_percentage:.1f}%")
        
        # Department contributions
        if reallocated_amounts:
            st.subheader("Department Contributions")
            dept_df = pd.DataFrame({
                "Department": reallocated_amounts.keys(),
                "Contribution": reallocated_amounts.values()
            })
            dept_df["Contribution"] = dept_df["Contribution"].apply(lambda x: f"${x:,}")
            st.dataframe(dept_df, use_container_width=True)
        
        # Funding status
        st.subheader("Funding Status")
        if bonds_needed == 0:
            st.success(" Project is fully funded without bond issuance!")
        elif bonds_needed <= project_cost * 0.25:
            st.warning(f" Small funding gap of ${bonds_needed:,}. Consider additional funding sources or modest bond issuance.")
        else:
            st.error(f"❗ Significant funding gap of ${bonds_needed:,}. Bond issuance required or project scope reduction advised.")

    # Export to CSV
    st.subheader("Export Data")
    export_categories = categories
    export_values = values
    
    export_df = pd.DataFrame({
        "Funding Source": export_categories,
        "Amount": export_values
    })
    
    csv_data = export_df.to_csv(index=False).encode('utf-8')
    st.download_button(f" Download {org} Scenario as CSV", data=csv_data, file_name=f"{org}_funding_scenario.csv", mime="text/csv")
    
    # Scenario history
    st.subheader(" Save & View Scenarios")
    
    # Load existing scenarios from database
    db_scenarios = get_scenarios(limit=6)
    
    # Custom scenario name with timestamp for uniqueness
    timestamp = datetime.now().strftime("%m/%d/%Y %H:%M")
    scenario_name = st.text_input("Scenario Name", value=f"{org} - {selected_project_data['name']} - {timestamp}")
    
    # Save current scenario
    if st.button("Save This Scenario"):
        # Prepare scenario data
        scenario_data = {
            "name": scenario_name,
            "project_id": project_id,
            "Total Cost": project_cost,
            "Tax Revenue": tax_revenue,
            "Grant Funding": grant,
            "Private Investment": private_investment,
            "Bonds Needed": bonds_needed
        }
        
        # Save to database
        scenario_id = save_scenario(scenario_data, reallocated_amounts)
        
        if scenario_id:
            st.success(f" Scenario '{scenario_name}' saved to database!")
            # Refresh scenarios list
            db_scenarios = get_scenarios(limit=6)
        else:
            st.error(" Failed to save scenario to database.")
    
    # Display saved scenarios
    if db_scenarios:
        st.subheader(f" Previously Saved Scenarios for {org}")
        history_cols = st.columns(min(3, len(db_scenarios)))
        
        for i, scenario in enumerate(db_scenarios):
            col_index = i % len(history_cols)
            with history_cols[col_index]:
                st.markdown(f"**{scenario['name']}**")
                st.text(f"Project: {scenario['Project']}")
                st.text(f"Total Cost: ${scenario['Total Cost']:,}")
                st.text(f"Reallocation: ${scenario['Departmental Reallocation']:,}")
                st.text(f"Tax Revenue: ${scenario['Tax Revenue']:,}")
                st.text(f"Grant: ${scenario['Grant Funding']:,}")
                if scenario['Private Investment'] > 0:
                    st.text(f"Private: ${scenario['Private Investment']:,}")
                st.text(f"Bonds: ${scenario['Bonds Needed']:,}")
                funding_percent = ((scenario['Total Cost'] - scenario['Bonds Needed']) / scenario['Total Cost']) * 100 if scenario['Total Cost'] > 0 else 0
                st.progress(min(funding_percent/100, 1.0))
                st.text(f"Funded: {funding_percent:.1f}%")
                
                # Add download button for this scenario
                try:
                    # Create a DataFrame for this scenario
                    scenario_sources = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", 
                                      "Private Investment", "Bonds Needed", "Total Cost"]
                    scenario_amounts = [scenario["Departmental Reallocation"], scenario["Tax Revenue"], 
                                       scenario["Grant Funding"], scenario["Private Investment"], 
                                       scenario["Bonds Needed"], scenario["Total Cost"]]
                    
                    scenario_df = pd.DataFrame({
                        "Funding Source": scenario_sources,
                        "Amount": scenario_amounts
                    })
                    
                    scenario_csv = scenario_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        " Download CSV", 
                        data=scenario_csv, 
                        file_name=f"{scenario['name'].replace(' ', '_')}.csv", 
                        mime="text/csv",
                        key=f"dl_scenario_{scenario['id']}"
                    )
                except Exception as e:
                    st.text(f"Error generating CSV: {str(e)[:50]}")
                
                st.markdown("---")

with tab2:
    st.markdown(f'<div class="sub-header"> Historical Funding Analysis for {org_display_name}</div>', unsafe_allow_html=True)
    
    # Try to get historical budget data from the database
    try:
        conn = get_connection('org_dashboard_data.db')
        df = pd.read_sql_query(f"SELECT * FROM DepartmentPerformance WHERE Organization = '{org}'", conn)
        conn.close()
        has_real_data = not df.empty
    except Exception as e:
        st.error(f"Error loading historical data: {str(e)}")
        has_real_data = False
    
    if has_real_data:
        st.success(" Loaded historical budget data from database")
        
        # Dashboard KPIs at the top
        st.subheader("Budget Overview Metrics")
        total_budget = df["Budget"].sum()
        total_actual = df["Actual"].sum()
        total_underspent = total_budget - total_actual
        underspent_pct = (total_underspent / total_budget) * 100 if total_budget > 0 else 0
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Budget", f"${total_budget:,.0f}")
        kpi2.metric("Total Actual Spent", f"${total_actual:,.0f}")
        kpi3.metric("Total Underspent", f"${total_underspent:,.0f}")
        kpi4.metric("Underspent %", f"{underspent_pct:.1f}%")
        
        # Add a fiscal year filter
        fiscal_years = sorted(df["FiscalYear"].unique())
        selected_years = st.multiselect("Select Fiscal Years for Analysis", fiscal_years, default=fiscal_years)
        
        if not selected_years:
            st.warning("Please select at least one fiscal year.")
        else:
            filtered_df = df[df["FiscalYear"].isin(selected_years)]
            
            # Budget vs Actual by Fiscal Year
            st.subheader(" Budget vs. Actual by Fiscal Year")
            year_totals = filtered_df.groupby("FiscalYear").agg({"Budget": "sum", "Actual": "sum"}).reset_index()
            
            # Create a bar chart showing budget vs actual by year
            try:
                import plotly.express as px
                import numpy as np
                from sklearn.linear_model import LinearRegression
                
                fig1 = px.bar(year_totals, x="FiscalYear", y=["Budget", "Actual"], 
                             barmode="group", 
                             title=f"{org_display_name} Budget vs. Actual by Fiscal Year",
                             labels={"value": "Amount ($)", "variable": "Category"})
                st.plotly_chart(fig1, use_container_width=True)
                
                # Add forecasting option
                with st.expander("🔮 Generate Future Forecasts", expanded=False):
                    st.markdown("""
                    This tool uses machine learning to forecast future budget trends. It analyzes historical patterns
                    to predict how budgets and actual spending might change in the coming years if current patterns continue.
                    """)
                    
                    # Option for number of years to forecast
                    future_years = st.slider("Number of years to forecast", min_value=1, max_value=5, value=3)
                    
                    if st.button("Generate Forecast"):
                        # Prepare data for modeling
                        try:
                            year_totals["Year_Num"] = range(len(year_totals))
                            
                            # Create and train linear regression models for both Budget and Actual
                            budget_model = LinearRegression()
                            actual_model = LinearRegression()
                            
                            X = year_totals[["Year_Num"]]
                            y_budget = year_totals["Budget"]
                            y_actual = year_totals["Actual"]
                            
                            # Train models
                            budget_model.fit(X, y_budget)
                            actual_model.fit(X, y_actual)
                            
                            # Generate future years
                            last_year_num = len(X) - 1
                            future_year_nums = list(range(last_year_num + 1, last_year_num + 1 + future_years))
                            future_X = np.array(future_year_nums).reshape(-1, 1)
                            
                            # Get the last fiscal year and predict future fiscal years
                            last_year = year_totals["FiscalYear"].iloc[-1]
                            
                            # Extract year number if format is like "FY 2024"
                            if isinstance(last_year, str) and "FY" in last_year:
                                try:
                                    year_num = int(last_year.split()[-1])
                                    future_fiscal_years = [f"FY {year_num + i}" for i in range(1, future_years + 1)]
                                except:
                                    # If can't parse, just use generic labels
                                    future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                            else:
                                # If it's a number, just add to it
                                if isinstance(last_year, (int, float)):
                                    future_fiscal_years = [int(last_year) + i for i in range(1, future_years + 1)]
                                else:
                                    future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                            
                            # Predict future values
                            future_budget = budget_model.predict(future_X)
                            future_actual = actual_model.predict(future_X)
                            
                            # Create forecast dataframe
                            forecast_df = pd.DataFrame({
                                "FiscalYear": future_fiscal_years,
                                "Budget": future_budget,
                                "Actual": future_actual,
                                "Forecast": True
                            })
                            
                            # Add indicator column to original data
                            year_totals["Forecast"] = False
                            
                            # Combine historical and forecast data
                            combined = pd.concat([year_totals, forecast_df])
                            
                            # Visualize the forecast with a line chart
                            fig_forecast = px.line(
                                combined, 
                                x="FiscalYear", 
                                y=["Budget", "Actual"],
                                markers=True,
                                title=f"{org_display_name} - Budget and Actual Forecast",
                                labels={"value": "Amount ($)", "variable": "Type"}
                            )
                            
                            # Add vertical line at forecast boundary
                            historical_years = len(year_totals)
                            forecast_start = combined["FiscalYear"].iloc[historical_years-1]
                            
                            fig_forecast.add_vline(
                                x=forecast_start, 
                                line_dash="dash", 
                                line_color="gray", 
                                annotation_text="Forecast Start",
                                annotation_position="top right"
                            )
                            
                            # Update layout for better visualization
                            fig_forecast.update_layout(
                                xaxis_title="Fiscal Year",
                                yaxis_title="Amount ($)",
                                legend_title="Type",
                                hovermode="x unified"
                            )
                            
                            # Show the forecast visualization
                            st.plotly_chart(fig_forecast, use_container_width=True)
                            
                            # Show the forecast data
                            st.subheader("Forecast Data")
                            st.dataframe(forecast_df.style.format({
                                "Budget": "${:,.2f}",
                                "Actual": "${:,.2f}"
                            }), use_container_width=True)
                            
                            # Calculate budget variance in forecast
                            forecast_df["Variance"] = forecast_df["Budget"] - forecast_df["Actual"]
                            forecast_df["Variance%"] = (forecast_df["Variance"] / forecast_df["Budget"]) * 100
                            
                            avg_variance = forecast_df["Variance"].mean()
                            avg_variance_pct = forecast_df["Variance%"].mean()
                            
                            # Show forecast insights
                            st.subheader("Forecast Insights")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Average Forecast Variance", f"${avg_variance:,.2f}")
                            with col2:
                                st.metric("Average Variance Percentage", f"{avg_variance_pct:.1f}%")
                            
                            # Recommendation based on forecast
                            if avg_variance_pct > 10:
                                st.success(" The budget is projected to significantly underspend. Consider reallocating budget to other priorities.")
                            elif avg_variance_pct < -10:
                                st.error(" The budget is projected to significantly overspend. Consider increasing the budget allocation.")
                            else:
                                st.info("ℹ️ The budget spending is projected to closely align with budgeted amounts.")
                        except Exception as e:
                            st.error(f"Error generating forecast: {e}")
                            st.info("Make sure you have enough historical data points for a meaningful forecast.")
            except ImportError:
                # Fallback to regular plotly
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(x=year_totals["FiscalYear"], y=year_totals["Budget"], name="Budget"))
                fig1.add_trace(go.Bar(x=year_totals["FiscalYear"], y=year_totals["Actual"], name="Actual"))
                fig1.update_layout(barmode="group", title=f"{org_display_name} Budget vs. Actual by Fiscal Year")
                st.plotly_chart(fig1, use_container_width=True)
            
            # Department breakdown
            st.subheader("🏢 Department Budget Analysis")
            departments = sorted(filtered_df["Department"].unique())
            
            # Allow selecting specific departments
            selected_dept = st.selectbox("Select Department for Detailed Analysis", departments)
            
            # Create filtered data for the selected department
            dept_df = filtered_df[filtered_df["Department"] == selected_dept]
            dept_by_year = dept_df.groupby("FiscalYear").agg({"Budget": "sum", "Actual": "sum"}).reset_index()
            
            # Show department metrics
            dept_total_budget = dept_df["Budget"].sum()
            dept_total_actual = dept_df["Actual"].sum()
            dept_underspent = dept_total_budget - dept_total_actual
            dept_underspent_pct = (dept_underspent / dept_total_budget) * 100 if dept_total_budget > 0 else 0
            
            dept_kpi1, dept_kpi2, dept_kpi3 = st.columns(3)
            dept_kpi1.metric(f"{selected_dept} Total Budget", f"${dept_total_budget:,.0f}")
            dept_kpi2.metric(f"Total Actual", f"${dept_total_actual:,.0f}")
            dept_kpi3.metric(f"Underspent ({dept_underspent_pct:.1f}%)", f"${dept_underspent:,.0f}")
            
            # Create department trend chart
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=dept_by_year["FiscalYear"], 
                y=dept_by_year["Budget"],
                mode="lines+markers",
                name="Budget"
            ))
            fig2.add_trace(go.Scatter(
                x=dept_by_year["FiscalYear"], 
                y=dept_by_year["Actual"],
                mode="lines+markers",
                name="Actual"
            ))
            
            fig2.update_layout(
                title=f"{selected_dept} Budget Trends",
                xaxis_title="Fiscal Year",
                yaxis_title="Amount ($)",
                height=400
            )
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # Department-level forecasting
            with st.expander("🔮 Forecast Department Budget", expanded=False):
                st.markdown(f"""
                Forecast future budgets and spending for **{selected_dept}** based on historical trends.
                This will help plan for future budget allocations more effectively.
                """)
                
                # Option for number of years to forecast
                dept_future_years = st.slider("Number of years to forecast", min_value=1, max_value=5, value=3, key="dept_forecast_years")
                
                # Show advanced options
                advanced_options = st.checkbox("Show Advanced Options")
                if advanced_options:
                    growth_adj = st.slider("Growth adjustment (%)", min_value=-10, max_value=10, value=0, 
                                          help="Adjust the growth rate for forecasting. Positive values will increase the growth rate; negative values will decrease it.")
                else:
                    growth_adj = 0
                
                if st.button("Generate Department Forecast"):
                    try:
                        # Prepare data for modeling
                        dept_by_year["Year_Num"] = range(len(dept_by_year))
                        
                        # Create and train linear regression models for both Budget and Actual
                        dept_budget_model = LinearRegression()
                        dept_actual_model = LinearRegression()
                        
                        X = dept_by_year[["Year_Num"]]
                        y_budget = dept_by_year["Budget"]
                        y_actual = dept_by_year["Actual"]
                        
                        # Train models
                        dept_budget_model.fit(X, y_budget)
                        dept_actual_model.fit(X, y_actual)
                        
                        # Generate future years
                        last_year_num = len(X) - 1
                        future_year_nums = list(range(last_year_num + 1, last_year_num + 1 + dept_future_years))
                        future_X = np.array(future_year_nums).reshape(-1, 1)
                        
                        # Get the last fiscal year and predict future fiscal years
                        last_year = dept_by_year["FiscalYear"].iloc[-1]
                        
                        # Extract year number if format is like "FY 2024"
                        if isinstance(last_year, str) and "FY" in last_year:
                            try:
                                year_num = int(last_year.split()[-1])
                                future_fiscal_years = [f"FY {year_num + i}" for i in range(1, dept_future_years + 1)]
                            except:
                                # If can't parse, just use generic labels
                                future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                        else:
                            # If it's a number, just add to it
                            if isinstance(last_year, (int, float)):
                                future_fiscal_years = [int(last_year) + i for i in range(1, dept_future_years + 1)]
                            else:
                                future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                        
                        # Predict future values
                        future_budget = dept_budget_model.predict(future_X)
                        future_actual = dept_actual_model.predict(future_X)
                        
                        # Apply growth adjustment if specified
                        if growth_adj != 0:
                            # Apply adjustment factor to the growth
                            adj_factor = 1 + (growth_adj / 100)
                            
                            # Calculate the average growth rate per year
                            if len(future_budget) > 1:
                                budget_growth_per_year = (future_budget[-1] - future_budget[0]) / (len(future_budget) - 1)
                                actual_growth_per_year = (future_actual[-1] - future_actual[0]) / (len(future_actual) - 1)
                                
                                # Apply the adjustment to the growth rate
                                adjusted_budget_growth = budget_growth_per_year * adj_factor
                                adjusted_actual_growth = actual_growth_per_year * adj_factor
                                
                                # Recalculate the forecasted values with the adjusted growth
                                for i in range(1, len(future_budget)):
                                    future_budget[i] = future_budget[0] + (adjusted_budget_growth * i)
                                    future_actual[i] = future_actual[0] + (adjusted_actual_growth * i)
                            else:
                                # If only one forecasted year, apply the adjustment directly
                                future_budget[0] *= adj_factor
                                future_actual[0] *= adj_factor
                        
                        # Create forecast dataframe
                        dept_forecast_df = pd.DataFrame({
                            "FiscalYear": future_fiscal_years,
                            "Budget": future_budget,
                            "Actual": future_actual,
                            "Forecast": True
                        })
                        
                        # Add indicator column to original data
                        dept_by_year["Forecast"] = False
                        
                        # Combine historical and forecast data
                        dept_combined = pd.concat([dept_by_year, dept_forecast_df])
                        
                        # Visualize the forecast with a line chart
                        fig_dept_forecast = px.line(
                            dept_combined, 
                            x="FiscalYear", 
                            y=["Budget", "Actual"],
                            markers=True,
                            title=f"{selected_dept} - Budget and Actual Forecast",
                            labels={"value": "Amount ($)", "variable": "Type"}
                        )
                        
                        # Add vertical line at forecast boundary
                        historical_years = len(dept_by_year)
                        forecast_start = dept_combined["FiscalYear"].iloc[historical_years-1]
                        
                        fig_dept_forecast.add_vline(
                            x=forecast_start, 
                            line_dash="dash", 
                            line_color="gray", 
                            annotation_text="Forecast Start",
                            annotation_position="top right"
                        )
                        
                        # Update layout for better visualization
                        fig_dept_forecast.update_layout(
                            xaxis_title="Fiscal Year",
                            yaxis_title="Amount ($)",
                            legend_title="Type",
                            hovermode="x unified"
                        )
                        
                        # Show the forecast visualization
                        st.plotly_chart(fig_dept_forecast, use_container_width=True)
                        
                        # Show the forecast data
                        st.subheader(f"Forecast Data for {selected_dept}")
                        st.dataframe(dept_forecast_df.style.format({
                            "Budget": "${:,.2f}",
                            "Actual": "${:,.2f}"
                        }), use_container_width=True)
                        
                        # Calculate budget variance in forecast
                        dept_forecast_df["Variance"] = dept_forecast_df["Budget"] - dept_forecast_df["Actual"]
                        dept_forecast_df["Variance%"] = (dept_forecast_df["Variance"] / dept_forecast_df["Budget"]) * 100
                        
                        avg_variance = dept_forecast_df["Variance"].mean()
                        avg_variance_pct = dept_forecast_df["Variance%"].mean()
                        
                        # Show forecast insights
                        st.subheader(f"Forecast Insights for {selected_dept}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Average Forecast Variance", f"${avg_variance:,.2f}")
                        with col2:
                            st.metric("Average Variance Percentage", f"{avg_variance_pct:.1f}%")
                        
                        # Recommendation based on forecast
                        if growth_adj != 0:
                            st.info(f"ℹ️ This forecast includes a {growth_adj}% adjustment to the growth rate.")
                            
                        if avg_variance_pct > 10:
                            st.success(f" {selected_dept} is projected to significantly underspend. Consider reallocating budget to other departments.")
                        elif avg_variance_pct < -10:
                            st.error(f" {selected_dept} is projected to significantly overspend. Consider increasing their budget allocation.")
                        else:
                            st.info(f"ℹ️ {selected_dept}'s spending is projected to closely align with budgeted amounts.")
                            
                        # Final year forecast summary
                        final_year = dept_forecast_df.iloc[-1]
                        st.markdown(f"""
                        ### FY {final_year['FiscalYear']} Projected Budget
                        By fiscal year {final_year['FiscalYear']}, {selected_dept} is projected to have:
                        - Budget: **${final_year['Budget']:,.2f}**
                        - Expenditure: **${final_year['Actual']:,.2f}**
                        - Variance: **${final_year['Variance']:,.2f}** ({final_year['Variance%']:.1f}%)
                        """)
                        
                    except Exception as e:
                        st.error(f"Error generating department forecast: {e}")
                        st.info("Make sure you have enough historical data points for a meaningful forecast.")
            
            # Variance Analysis
            st.subheader(" Budget Variance Analysis")
            
            # Add variance to the dataset
            filtered_df["Variance"] = filtered_df["Budget"] - filtered_df["Actual"]
            filtered_df["Variance%"] = (filtered_df["Variance"] / filtered_df["Budget"]) * 100
            
            # Total variance by department
            variance_by_dept = filtered_df.groupby("Department").agg({
                "Budget": "sum", 
                "Actual": "sum", 
                "Variance": "sum"
            }).reset_index()
            
            variance_by_dept["Variance%"] = (variance_by_dept["Variance"] / variance_by_dept["Budget"]) * 100
            variance_by_dept = variance_by_dept.sort_values("Variance", ascending=False)
            
            # Show variance table
            st.dataframe(variance_by_dept.style.format({
                "Budget": "${:,.0f}",
                "Actual": "${:,.0f}",
                "Variance": "${:,.0f}",
                "Variance%": "{:.1f}%"
            }), use_container_width=True)
            
            # Create variance chart
            try:
                import plotly.express as px
                fig3 = px.bar(variance_by_dept, 
                             x="Department", 
                             y="Variance",
                             color="Variance%",
                             color_continuous_scale=["red", "yellow", "green"],
                             title="Budget Variance by Department",
                             labels={"Variance": "Amount Underspent ($)"})
                st.plotly_chart(fig3, use_container_width=True)
            except Exception as e:
                # Fallback to regular plotly
                fig3 = go.Figure(data=[
                    go.Bar(name='Variance', x=variance_by_dept["Department"], y=variance_by_dept["Variance"])
                ])
                fig3.update_layout(
                    title="Budget Variance by Department",
                    xaxis_title="Department",
                    yaxis_title="Variance ($)"
                )
                st.plotly_chart(fig3, use_container_width=True)
            
            # AI Insights
            st.subheader("🧠 AI Budget Analysis Insights")
            
            if st.button("Generate AI Budget Analysis"):
                with st.spinner("Analyzing budget data..."):
                    # Prepare data summary for the AI
                    year_summary = filtered_df.groupby(["FiscalYear", "Department"]).agg({
                        "Budget": "sum", 
                        "Actual": "sum",
                        "Variance": "sum",
                        "Variance%": "mean"
                    }).reset_index()
                    
                    # Generate AI insights
                    insights = generate_ai_commentary(
                        year_summary, 
                        f"Analyze the budget trends for {org_display_name} across years and departments. Identify patterns, outliers, and provide recommendations."
                    )
                    
                    # Display insights
                    st.markdown(f'<div class="ai-response">{insights}</div>', unsafe_allow_html=True)
            
    else:
        # Fallback to sample data if real data is not available
        st.info(f"Using sample historical data for {org_display_name}. Connect to a real database for production use.")
        
        # Sample visualization for demonstration
        years = ["2020", "2021", "2022", "2023", "2024"]
        funding_types = ["Tax Revenue", "Grants", "Bonds", "Department Reallocation"]
        
        # Modify data based on organization for demonstration
        if org == "cityA":
            data = {
                "Tax Revenue": [350000, 400000, 450000, 525000, 550000],
                "Grants": [225000, 275000, 250000, 400000, 450000],
                "Bonds": [800000, 750000, 650000, 500000, 450000],
                "Department Reallocation": [120000, 150000, 200000, 250000, 275000]
            }
        else:  # countyB or any other org
            data = {
                "Tax Revenue": [450000, 475000, 500000, 550000, 600000],
                "Grants": [300000, 350000, 375000, 450000, 500000],
                "Bonds": [900000, 800000, 700000, 600000, 500000],
                "Department Reallocation": [150000, 180000, 220000, 270000, 300000]
            }
        
        fig = go.Figure()
        for funding in funding_types:
            fig.add_trace(go.Scatter(
                x=years, 
                y=data[funding],
                mode='lines+markers',
                name=funding
            ))
        
        fig.update_layout(
            title=f"{org_display_name} 5-Year Funding Trends",
            xaxis_title="Year",
            yaxis_title="Amount ($)",
            legend_title="Funding Type",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown(f'<div class="sub-header">🏢 {org_display_name} Department Budget Insights</div>', unsafe_allow_html=True)
    
    # Query the dashboard database for department data
    try:
        query = f"SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = '{org}' AND FiscalYear = 'FY 2024'"
        dept_data = run_dashboard_query(query)
        
        if isinstance(dept_data, str):  # Error occurred
            st.error(f"Error loading department data: {dept_data}")
            departments_from_db = False
        else:
            departments_from_db = True
    except Exception as e:
        st.error(f"Error loading department data: {str(e)}")
        departments_from_db = False
    
    # Load departments data
    if departments_from_db:
        # Convert DataFrame to the expected format
        departments = {}
        for _, row in dept_data.iterrows():
            departments[row['Department']] = {
                "budget": row['Budget'],
                "underspent": row['Underspent']
            }
    else:
        # Fallback to hardcoded data
        st.warning(f" No departments found in {org_display_name}'s database. Using sample data.")
        if org == "cityA":
            departments = {
                "Public Works": {"budget": 1200000, "underspent": 300000},
                "Administration": {"budget": 800000, "underspent": 150000},
                "Parks & Recreation": {"budget": 600000, "underspent": 120000}
            }
        else:  # countyB or any other org
            departments = {
                "Planning & Development": {"budget": 1500000, "underspent": 350000},
                "Administration": {"budget": 900000, "underspent": 180000},
                "Social Services": {"budget": 2000000, "underspent": 100000}
            }
    
    # Create a bar chart of department budgets
    dept_names = list(departments.keys())
    total_budgets = [data["budget"] for data in departments.values()]
    underspent = [data["underspent"] for data in departments.values()]
    
    # Calculate percentage underspent
    percent_underspent = [(u / t) * 100 if t > 0 else 0 for u, t in zip(underspent, total_budgets)]
    
    # Create a DataFrame for the table
    dept_df = pd.DataFrame({
        "Department": dept_names,
        "Total Budget": total_budgets,
        "Underspent": underspent,
        "Percent Underspent": percent_underspent
    })
    
    # Format for display
    dept_display = dept_df.copy()
    dept_display["Total Budget"] = dept_display["Total Budget"].apply(lambda x: f"${x:,.2f}")
    dept_display["Underspent"] = dept_display["Underspent"].apply(lambda x: f"${x:,.2f}")
    dept_display["Percent Underspent"] = dept_display["Percent Underspent"].apply(lambda x: f"{x:.1f}%")
    
    # Department selection for detailed view
    selected_dept = st.selectbox("Select Department for Detailed View", dept_names)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create bar chart for all departments
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dept_names,
            y=total_budgets,
            name="Total Budget",
            marker_color="#3498db"
        ))
        fig.add_trace(go.Bar(
            x=dept_names,
            y=underspent,
            name="Underspent",
            marker_color="#e74c3c"
        ))
        
        fig.update_layout(
            title=f"{org_display_name} Department Budget Overview",
            xaxis_title="Department",
            yaxis_title="Amount ($)",
            barmode="group",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Show selected department details
        st.subheader(f"{selected_dept} Details")
        
        selected_data = departments[selected_dept]
        total = selected_data["budget"]
        unspent = selected_data["underspent"]
        spent = total - unspent
        
        # Metrics
        st.metric("Total Budget", f"${total:,}")
        st.metric("Spent", f"${spent:,}")
        st.metric("Underspent", f"${unspent:,}")
        
        # Donut chart for spent vs. unspent
        fig = go.Figure(data=[go.Pie(
            labels=["Spent", "Underspent"],
            values=[spent, unspent],
            hole=.6
        )])
        
        fig.update_layout(
            title="Budget Utilization",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Show department data table
    st.subheader(f"{org_display_name} Department Budget Data")
    st.dataframe(dept_display, use_container_width=True)

# AI Assistant Tab    
with tab4:
    st.markdown(f'<div class="sub-header"> {org_display_name} AI Budget Assistant</div>', unsafe_allow_html=True)
    
    # Initialize chat history in session state if not present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "policy_text" not in st.session_state:
        st.session_state.policy_text = ""
    
    # Create tabs for different AI assistant features
    ai_tab1, ai_tab2 = st.tabs([" Data Q&A", " Policy/Grant Assistant"])
    
    with ai_tab1:
        # Introduction
        st.markdown(f"""
        Ask questions about {org_display_name}'s budget data in plain English. The AI assistant will translate
        your questions into SQL queries and provide answers from the database.
        
        **Example questions:**
        - Which department has the largest budget?
        - What is the total underspent amount across all departments?
        - Compare actual spending versus budget for FY 2023 and FY 2024
        - Which department has the highest percentage of underspent budget?
        """)
        
        # User input
        user_question = st.text_area("💬 Ask your budget question", placeholder="e.g., Which department is most underspent in FY 2024?")
        
        # Execute button
        if st.button("Ask AI Assistant"):
            if not user_question:
                st.warning("Please enter a question to continue.")
            else:
                with st.spinner("Analyzing your question..."):
                    # Check if OpenAI is available
                    if not OPENAI_AVAILABLE:
                        st.warning("OpenAI integration is not available. Using default queries.")
                        
                    # Generate SQL from the user's prompt using chat history for context
                    sql_query = generate_sql_from_prompt(user_question, org, st.session_state.chat_history)
                    
                    # Add to chat history
                    st.session_state.chat_history.append({"question": user_question, "sql": sql_query})
                    
                    # Display the generated SQL
                    with st.expander("View Generated SQL Query"):
                        st.code(sql_query, language="sql")
                    
                    # Run the query
                    results = run_dashboard_query(sql_query, org_filter=org)
                    
                    # Display results
                    if isinstance(results, str):
                        st.error(f"Error: {results}")
                    elif isinstance(results, pd.DataFrame):
                        if results.empty:
                            st.info("No data found for your query.")
                        else:
                            st.markdown('<div class="ai-response">Here are the results:</div>', unsafe_allow_html=True)
                            
                            # Display as a styled table
                            st.dataframe(results, use_container_width=True)
                            
                            # Format numeric columns with commas (for display and downloads)
                            results_display = results.copy()
                            for col in results_display.columns:
                                if results_display[col].dtype in ['int64', 'float64']:
                                    results_display[col] = results_display[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else x)
                            
                            # Create a visualization if the data is suitable
                            if len(results) > 0 and len(results) <= 15:  # Only visualize reasonable sized datasets
                                st.subheader(" Visualization")
                                
                                try:
                                    # Check for numeric columns for visualization
                                    numeric_cols = [col for col in results.columns if results[col].dtype.kind in 'ifc']
                                    if len(numeric_cols) >= 1:
                                        # Get first string column as labels if present
                                        string_cols = [col for col in results.columns if results[col].dtype == 'object']
                                        if string_cols:
                                            label_col = st.selectbox("X-Axis", string_cols, index=0, key="x_axis_select")
                                            y_axis = st.selectbox("Y-Axis", numeric_cols, index=0, key="y_axis_select")
                                            
                                            # Create appropriate visualization using plotly express
                                            try:
                                                import plotly.express as px
                                                fig = px.bar(results, x=label_col, y=y_axis, title=f"Results for: {user_question[:50]}{'...' if len(user_question) > 50 else ''}")
                                                st.plotly_chart(fig, use_container_width=True)
                                            except ImportError:
                                                # Fallback to plotly graph_objects if express is not available
                                                fig = go.Figure()
                                                fig.add_trace(go.Bar(
                                                    x=results[label_col],
                                                    y=results[y_axis],
                                                    name=y_axis
                                                ))
                                                fig.update_layout(
                                                    title=f"Results for: {user_question[:50]}{'...' if len(user_question) > 50 else ''}",
                                                    xaxis_title=label_col,
                                                    yaxis_title=y_axis,
                                                    height=400
                                                )
                                                st.plotly_chart(fig, use_container_width=True)
                                except Exception as e:
                                    st.warning(f"Could not create visualization: {str(e)}")
                            
                            # AI commentary on the results
                            st.subheader("🧠 AI Insight")
                            insight = generate_ai_commentary(results, user_question)
                            st.markdown(f'<div class="ai-response">{insight}</div>', unsafe_allow_html=True)
                            
                            # Provide download option for results
                            csv = results.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                " Download Results as CSV",
                                data=csv,
                                file_name=f"{org}_query_results.csv",
                                mime="text/csv"
                            )
        
        # Show chat history if any exists
        if st.session_state.chat_history:
            with st.expander("Recent Questions", expanded=False):
                for i, qa in enumerate(reversed(st.session_state.chat_history[-5:])):
                    st.markdown(f"**Q{i+1}:** {qa['question']}")
                    st.markdown(f"**SQL:** `{qa['sql'][:100]}...`" if len(qa['sql']) > 100 else f"**SQL:** `{qa['sql']}`")
                    st.markdown("---")
    
    with ai_tab2:
        st.markdown(f"""
        #  Policy & Grant Assistant
        
        Upload policy documents, grant guidelines, or budget memos to ask questions about them.
        Use this assistant to:
        
        - Find relevant grant opportunities for your projects
        - Understand budget policies and restrictions
        - Get guidance on funding applications
        - Interpret complex financial regulations
        """)
        
        # File uploader for policy documents
        uploaded_file = st.file_uploader("Upload policy or grant document (TXT or PDF)", type=["txt", "pdf"])
        
        if uploaded_file:
            try:
                if uploaded_file.type == "text/plain":
                    # Handle text files
                    st.session_state.policy_text = uploaded_file.read().decode("utf-8")
                    st.success(f" Text file uploaded: {uploaded_file.name}")
                    
                elif uploaded_file.type == "application/pdf":
                    # Handle PDF files using PyPDF2
                    try:
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        full_text = ""
                        for page in pdf_reader.pages:
                            full_text += page.extract_text()
                        st.session_state.policy_text = full_text
                        st.success(f" PDF file uploaded: {uploaded_file.name} ({len(pdf_reader.pages)} pages)")
                    except ImportError:
                        st.error("PyPDF2 module not available. Please install it to process PDF files.")
                    except Exception as e:
                        st.error(f"Error processing PDF file: {str(e)}")
            except Exception as e:
                st.error(f"Error processing uploaded file: {str(e)}")
        
        # Display text preview if available
        if st.session_state.policy_text:
            with st.expander("Document Preview", expanded=False):
                st.markdown(f"**Document content ({len(st.session_state.policy_text)} characters):**")
                st.text_area("Content preview", st.session_state.policy_text[:1000] + "..." if len(st.session_state.policy_text) > 1000 else st.session_state.policy_text, height=200, disabled=True)
        
        # User question about policy documents
        policy_question = st.text_area(" Ask a question about the uploaded document", placeholder="e.g., What grants are available for IT infrastructure?")
        
        # Query button
        if st.button("Ask Policy AI"):
            if not st.session_state.policy_text:
                st.warning("Please upload a document first.")
            elif not policy_question:
                st.warning("Please enter a question about the document.")
            else:
                with st.spinner("Analyzing document..."):
                    if OPENAI_AVAILABLE:
                        try:
                            # Configure API
                            api_key = st.secrets.get("OPENAI_API_KEY", None)
                            if not api_key:
                                st.error("OpenAI API key not found. Please add it to your secrets.")
                            else:
                                openai.api_key = api_key
                                
                                # Format the prompt
                                prompt = f"""You are a policy advisor for {org_display_name}. 
Based on this document excerpt:
```
{st.session_state.policy_text[:3000]}
```
{'' if len(st.session_state.policy_text) <= 3000 else f'(Note: Document was truncated due to length. Original is {len(st.session_state.policy_text)} characters)'}

Question: {policy_question}

Provide a helpful answer based only on the information in the document. If the information is not in the document, clearly state that you cannot find the answer in the provided text."""
                                
                                # Generate response
                                response = openai.ChatCompletion.create(
                                    model="gpt-3.5-turbo",
                                    messages=[
                                        {"role": "system", "content": "You assist with government grants and budget policy interpretation."},
                                        {"role": "user", "content": prompt}
                                    ]
                                )
                                
                                st.markdown("**Answer:**")
                                st.markdown(f'<div class="ai-response">{response["choices"][0]["message"]["content"]}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error analyzing document: {str(e)}")
                    else:
                        st.error("OpenAI integration is not available. Please check your API key and try again.")

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #888;">
    GovSight Financial Analyzer | Organization: {org}
    <br>© 2024 GovSight Analytics | <a href="/?">Switch Organization</a>
</div>
""", unsafe_allow_html=True)