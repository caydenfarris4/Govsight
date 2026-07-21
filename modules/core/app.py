import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
import os
import sqlite3
from datetime import datetime

# Import enhanced database utilities for flexible database connectivity
try:
    # Try to import the enhanced database utilities first
    from enhanced_db_utils import (
        get_connection, execute_query, get_departments, get_projects,
        run_dashboard_query, save_scenario, get_scenarios,
        format_currency, format_percentage, get_db_path_for_org
    )
    # Flag that we're using the enhanced database utilities
    USING_ENHANCED_DB = True
except ImportError:
    # Fall back to common_utils if enhanced_db_utils is not available
    from common_utils import (
        get_connection, execute_query, get_departments, 
        run_dashboard_query, format_currency, format_percentage,
        get_db_path_for_org
    )
    # Import common utilities module for other functions
    import common_utils
    # Flag that we're using the common utilities
    USING_ENHANCED_DB = False

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

# Note: Database functions are already imported from the enhanced_db_utils or common_utils module
# Showing a message about which database module we're using
if USING_ENHANCED_DB:
    st.sidebar.success(" Using enhanced database module")
    # Import additional database utilities if needed
else:
    st.sidebar.info("ℹ️ Using basic database module")
    # If we need to fall back to any specific functions not imported earlier

def generate_sql_from_prompt(prompt, org_name, history=[]):
    """Generate SQL from prompt using OpenAI (if available)"""
    if not OPENAI_AVAILABLE:
        # Use parameterized query to prevent SQL injection
        return "SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = ? LIMIT 10"
    
    # Default query to use if we can't generate one (parameterized)
    default_query = "SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = ? LIMIT 10"
    
    # Check if we already know the API key has quota issues
    if "insufficient_quota" in st.session_state.get('api_errors', ""):
        if "budget" in prompt.lower():
            return "SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = ? ORDER BY Budget DESC LIMIT 10"
        elif "department" in prompt.lower():
            return "SELECT DISTINCT Department, SUM(Budget) as TotalBudget, SUM(Actual) as TotalSpent FROM DepartmentPerformance WHERE Organization = ? GROUP BY Department ORDER BY TotalBudget DESC"
        elif "fiscal" in prompt.lower() or "year" in prompt.lower():
            return "SELECT FiscalYear, SUM(Budget) as YearlyBudget, SUM(Actual) as YearlySpent FROM DepartmentPerformance WHERE Organization = ? GROUP BY FiscalYear"
        else:
            return default_query
    
    try:
        # Get the API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = st.secrets.get("OPENAI_API_KEY", None)
            
        if not api_key:
            st.warning("OpenAI API key not found. Using default query.")
            return default_query
        
        # Create a client instance with the API key
        client = openai.OpenAI(api_key=api_key)
        
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
        
        # Use the client to create a chat completion
        response = client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released after your training data cutoff
            messages=messages
        )
        
        # Access the response content
        sql_query = response.choices[0].message.content.strip()
        # Remove any code block markers
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        return sql_query
    except Exception as e:
        error_str = str(e)
        # Store error message to avoid repeated API calls with insufficient quota
        if "insufficient_quota" in error_str:
            if 'api_errors' not in st.session_state:
                st.session_state['api_errors'] = error_str
            
            # Provide different queries based on the prompt content for better user experience
            if "budget" in prompt.lower():
                return f"SELECT Department, Budget, Actual, (Budget - Actual) as Underspent FROM DepartmentPerformance WHERE Organization = '{org_name}' ORDER BY Budget DESC LIMIT 10"
            elif "department" in prompt.lower():
                return f"SELECT DISTINCT Department, SUM(Budget) as TotalBudget, SUM(Actual) as TotalSpent FROM DepartmentPerformance WHERE Organization = '{org_name}' GROUP BY Department ORDER BY TotalBudget DESC"
            elif "fiscal" in prompt.lower() or "year" in prompt.lower():
                return f"SELECT FiscalYear, SUM(Budget) as YearlyBudget, SUM(Actual) as YearlySpent FROM DepartmentPerformance WHERE Organization = '{org_name}' GROUP BY FiscalYear"
        
        st.error(f"Error generating SQL: {error_str}")
        return default_query

def generate_ai_commentary(df, prompt=None):
    """Generate AI commentary on the data"""
    if not OPENAI_AVAILABLE:
        return "AI commentary not available."
    
    try:
        # Get the API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = st.secrets.get("OPENAI_API_KEY", None)
            
        if not api_key:
            return "AI commentary not available (API key missing)."
        
        # Check if API key is having quota issues (before making API call)
        if "insufficient_quota" in st.session_state.get('api_errors', ""):
            return """Sorry, the OpenAI API key has reached its quota limit. 
            
When analyzing this financial data, consider:
1. Look for departments with consistent underspending that may have budget adjustment opportunities
2. Compare actual vs. budgeted amounts to identify areas needing better forecasting
3. Track year-over-year trends to identify seasonal patterns
4. Consider areas with highest variance for potential budget reallocation"""
            
        try:
            # Create a client instance with the API key
            client = openai.OpenAI(api_key=api_key)
            
            # Convert DataFrame to CSV for the prompt
            data_preview = df.head(10).to_csv(index=False)
            
            if prompt:
                user_prompt = f"Based on the following financial data, answer this question: {prompt}\n\nData:\n{data_preview}"
            else:
                user_prompt = f"Based on the following financial data, provide brief insights or recommendations:\n{data_preview}"
            
            # Use the client to create a chat completion
            response = client.chat.completions.create(
                model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released after your training data cutoff
                messages=[
                    {"role": "system", "content": "You analyze financial tables and suggest insights for government financial data."},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Access the response content
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            # Store error message to avoid repeated API calls with insufficient quota
            if "insufficient_quota" in error_str:
                if 'api_errors' not in st.session_state:
                    st.session_state['api_errors'] = error_str
            return f"Could not generate insights: {error_str}"
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
        
        # Use the standardized get_departments function to ensure consistency across all tabs
        departments = get_departments(org)
        
        # Use fallback data if needed
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
                    # Default checked for first two departments
                    is_default = dept in list(departments.keys())[:2]
                    include = st.checkbox(f"{dept}", value=is_default, key=f"check_{dept}")
                
                if include:
                    with col_slider:
                        # Calculate maximum allowed reallocation (10% of budget or underspent amount, whichever is less)
                        max_allowable = min(data["budget"] * 0.10, data.get("underspent", 0))
                        
                        # Ensure max_allowable is at least $1,000 for UI purposes
                        max_allowable = max(1000, max_allowable)
                        
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
                        st.markdown(f'<div class="department-data">Budget: ${data["budget"]:,} | Underspent: ${data.get("underspent", 0):,}</div>', unsafe_allow_html=True)

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
            st.metric("Total Project Cost", format_currency(project_cost))
            st.metric("Total Secured Funding", format_currency(funding_total))
        
        with col_metrics2:
            st.metric("Funding Gap", format_currency(bonds_needed))
            st.metric("Funding Percentage", format_percentage(funding_percentage))
        
        # Department contributions
        if reallocated_amounts:
            st.subheader("Department Contributions")
            dept_df = pd.DataFrame({
                "Department": reallocated_amounts.keys(),
                "Contribution": reallocated_amounts.values()
            })
            # Apply the format_currency function for consistent decimal places
            dept_df["Contribution"] = dept_df["Contribution"].apply(lambda x: format_currency(x))
            st.dataframe(dept_df, use_container_width=True)
        
        # Funding status
        st.subheader("Funding Status")
        if bonds_needed == 0:
            st.success(" Project is fully funded without bond issuance!")
        elif bonds_needed <= project_cost * 0.25:
            st.warning(f" Small funding gap of {format_currency(bonds_needed)}. Consider additional funding sources or modest bond issuance.")
        else:
            st.error(f"❗ Significant funding gap of {format_currency(bonds_needed)}. Bond issuance required or project scope reduction advised.")

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
        
        # Check if db_scenarios is a list of dictionaries with the expected structure
        if db_scenarios and isinstance(db_scenarios, list) and len(db_scenarios) > 0:
            # Check if the scenario has the expected keys
            if isinstance(db_scenarios[0], dict) and 'name' in db_scenarios[0]:
                # Original format - use as is
                scenarios_to_display = db_scenarios
            else:
                # New format from enhanced_db_utils - convert to expected format
                scenarios_to_display = []
                for s in db_scenarios:
                    # Handle both dictionary and tuple/list formats
                    if isinstance(s, dict):
                        scenario = {
                            "name": s.get('name', "Unnamed Scenario"),
                            "id": s.get('id', 0),
                            "Project": s.get('description', "Project"),
                            "Total Cost": s.get('total_amount', 0),
                            "Tax Revenue": 0,
                            "Grant Funding": 0,
                            "Private Investment": 0,
                            "Bonds Needed": 0,
                            "Departmental Reallocation": 0
                        }
                    else:
                        # Handle tuple/list format
                        scenario = {
                            "name": s[1] if len(s) > 1 else "Unnamed Scenario",
                            "id": s[0] if len(s) > 0 else 0,
                            "Project": s[2] if len(s) > 2 else "Project",
                            "Total Cost": s[3] if len(s) > 3 else 0,
                            "Tax Revenue": 0,
                            "Grant Funding": 0,
                            "Private Investment": 0,
                            "Bonds Needed": 0,
                            "Departmental Reallocation": 0
                        }
                    scenarios_to_display.append(scenario)
            
            # Display the scenarios
            history_cols = st.columns(min(3, len(scenarios_to_display)))
            
            for i, scenario in enumerate(scenarios_to_display):
                col_index = i % len(history_cols)
                with history_cols[col_index]:
                    st.markdown(f"**{scenario['name']}**")
                    st.text(f"Project: {scenario.get('Project', 'N/A')}")
                    st.text(f"Total Cost: ${scenario.get('Total Cost', 0):,}")
                    st.text(f"Reallocation: ${scenario.get('Departmental Reallocation', 0):,}")
                    
                    # Only show these if they exist
                    if 'Tax Revenue' in scenario:
                        st.text(f"Tax Revenue: ${scenario['Tax Revenue']:,}")
                    if 'Grant Funding' in scenario:
                        st.text(f"Grant: ${scenario['Grant Funding']:,}")
                    if 'Private Investment' in scenario and scenario['Private Investment'] > 0:
                        st.text(f"Private: ${scenario['Private Investment']:,}")
                    if 'Bonds Needed' in scenario:
                        st.text(f"Bonds: ${scenario['Bonds Needed']:,}")
                        
                        # Calculate funding percentage if possible
                        if 'Total Cost' in scenario and scenario['Total Cost'] > 0:
                            funding_percent = ((scenario['Total Cost'] - scenario['Bonds Needed']) / scenario['Total Cost']) * 100
                            st.progress(min(funding_percent/100, 1.0))
                            st.text(f"Funded: {funding_percent:.2f}%")
                    
                    # Add download button for this scenario
                    try:
                        # Create a DataFrame for this scenario
                        scenario_sources = ["Departmental Reallocation", "Tax Revenue", "Grant Funding", 
                                          "Private Investment", "Bonds Needed", "Total Cost"]
                        scenario_amounts = [
                            scenario.get("Departmental Reallocation", 0), 
                            scenario.get("Tax Revenue", 0), 
                            scenario.get("Grant Funding", 0), 
                            scenario.get("Private Investment", 0), 
                            scenario.get("Bonds Needed", 0), 
                            scenario.get("Total Cost", 0)
                        ]
                        
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
                            key=f"dl_scenario_{scenario.get('id', i)}"
                        )
                    except Exception as e:
                        st.text(f"Error generating CSV: {str(e)[:50]}")
                    
                    st.markdown("---")
        else:
            # Handle empty or unexpected format
            st.info("No saved scenarios found or scenarios are in an unexpected format.")
            
    # CSV download moved to inside the main scenario display block above

with tab2:
    st.markdown(f'<div class="sub-header"> Historical Funding Analysis for {org_display_name}</div>', unsafe_allow_html=True)
    
    # Try to get historical budget data from the organization's database
    try:
        # Use direct SQLite connections for organizations we know well
        if org in ["cityA", "cityB"]:
            # Use the specific path for these organizations to ensure advanced features work
            db_path = f"{org}_dashboard_data.db"
            
            # Verify database file exists
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                
                # We know the table structure for these organizations
                df = pd.read_sql_query("SELECT * FROM DepartmentPerformance", conn)
                conn.close()
                
                # Add Organization column if not present (for compatibility)
                if 'Organization' not in df.columns:
                    df['Organization'] = org
            else:
                st.warning(f"Database file not found: {db_path}")
                # Create empty dataframe with required columns
                df = pd.DataFrame(columns=['Department', 'Fund', 'FiscalYear', 'Budget', 'Actual', 'Month', 'Organization'])
                df['Organization'] = org
                
        else:
            # For other organizations, use our enhanced database utilities
            try:
                # Use the enhanced system to get the connection based on organization config
                conn = get_connection(org)  # Use org parameter directly, not db_path
                
                if conn is not None:
                    # First check if the DepartmentPerformance table exists
                    query = "SELECT name FROM sqlite_master WHERE type='table' AND name='DepartmentPerformance'"
                    tables = pd.read_sql_query(query, conn)
                    
                    if not tables.empty:
                        # Table exists, try to get column names
                        query = f"PRAGMA table_info(DepartmentPerformance)"
                        columns = pd.read_sql_query(query, conn)
                        has_org_column = 'Organization' in columns['name'].values
                        
                        # Query data based on column structure
                        if has_org_column:
                            df = pd.read_sql_query(f"SELECT * FROM DepartmentPerformance WHERE Organization = '{org}'", conn)
                        else:
                            df = pd.read_sql_query(f"SELECT * FROM DepartmentPerformance", conn)
                            df['Organization'] = org  # Add org column for consistency
                    else:
                        # Table doesn't exist, create empty dataframe with required columns
                        df = pd.DataFrame(columns=['Department', 'Fund', 'FiscalYear', 'Budget', 'Actual', 'Month', 'Organization'])
                        df['Organization'] = org
                    
                    try:
                        conn.close()
                    except:
                        pass
                else:
                    st.warning(f"Could not establish database connection for {org}")
                    # Create empty dataframe with required columns
                    df = pd.DataFrame(columns=['Department', 'Fund', 'FiscalYear', 'Budget', 'Actual', 'Month', 'Organization'])
                    df['Organization'] = org
            except Exception as inner_e:
                st.warning(f"Could not load data for {org}: {str(inner_e)}")
                # Create empty dataframe with required columns
                df = pd.DataFrame(columns=['Department', 'Fund', 'FiscalYear', 'Budget', 'Actual', 'Month', 'Organization'])
                df['Organization'] = org
        
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
        kpi1.metric("Total Budget", format_currency(total_budget))
        kpi2.metric("Total Actual Spent", format_currency(total_actual))
        kpi3.metric("Total Underspent", format_currency(total_underspent))
        kpi4.metric("Underspent %", format_percentage(underspent_pct))
        
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
                            # First, ensure Budget and Actual are numeric
                            try:
                                year_totals['Budget'] = pd.to_numeric(year_totals['Budget'], errors='coerce')
                                year_totals['Actual'] = pd.to_numeric(year_totals['Actual'], errors='coerce')
                                
                                # Drop any rows with NaN values after conversion
                                year_totals = year_totals.dropna(subset=['Budget', 'Actual'])
                                
                                if year_totals.empty:
                                    st.error("No valid numeric data found for forecasting after data cleaning.")
                                    st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                                    raise ValueError("No valid numeric data for forecasting")
                            except Exception as data_err:
                                st.error(f"Error preparing data for forecasting: {data_err}")
                                st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                                raise ValueError(f"Data preparation error: {data_err}")
                                
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
                            try:
                                last_year = year_totals["FiscalYear"].iloc[-1]
                                
                                # Convert to string for consistent handling
                                last_year_str = str(last_year)
                                
                                # Extract year number if format is like "FY 2024"
                                if "FY" in last_year_str:
                                    try:
                                        # Find any number in the string
                                        import re
                                        year_match = re.search(r'\d+', last_year_str)
                                        if year_match:
                                            year_num = int(year_match.group())
                                            future_fiscal_years = [f"FY {year_num + i}" for i in range(1, future_years + 1)]
                                        else:
                                            future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                                    except:
                                        # If can't parse, just use generic labels
                                        future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                                else:
                                    # Try to convert to number and increment
                                    try:
                                        year_num = int(float(last_year_str))
                                        future_fiscal_years = [str(year_num + i) for i in range(1, future_years + 1)]
                                    except (ValueError, TypeError):
                                        future_fiscal_years = [f"Year +{i}" for i in range(1, future_years + 1)]
                            except (IndexError, TypeError, KeyError) as e:
                                # Something went wrong, use generic labels
                                st.warning(f"Using generic year labels for forecast due to data format issue: {str(e)}")
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
                            # Create a copy to apply formatting
                            forecast_display = forecast_df.copy()
                            forecast_display["Budget"] = forecast_display["Budget"].apply(lambda x: format_currency(x))
                            forecast_display["Actual"] = forecast_display["Actual"].apply(lambda x: format_currency(x))
                            st.dataframe(forecast_display, use_container_width=True)
                            
                            # Calculate budget variance in forecast
                            forecast_df["Variance"] = forecast_df["Budget"] - forecast_df["Actual"]
                            forecast_df["Variance%"] = (forecast_df["Variance"] / forecast_df["Budget"]) * 100
                            
                            avg_variance = forecast_df["Variance"].mean()
                            avg_variance_pct = forecast_df["Variance%"].mean()
                            
                            # Show forecast insights
                            st.subheader("Forecast Insights")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Average Forecast Variance", format_currency(avg_variance))
                            with col2:
                                st.metric("Average Variance Percentage", format_percentage(avg_variance_pct))
                            
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
            dept_kpi1.metric(f"{selected_dept} Total Budget", format_currency(dept_total_budget))
            dept_kpi2.metric(f"Total Actual", format_currency(dept_total_actual))
            dept_kpi3.metric(f"Underspent ({format_percentage(dept_underspent_pct)})", format_currency(dept_underspent))
            
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
                        # First, ensure Budget and Actual are numeric
                        try:
                            dept_by_year['Budget'] = pd.to_numeric(dept_by_year['Budget'], errors='coerce')
                            dept_by_year['Actual'] = pd.to_numeric(dept_by_year['Actual'], errors='coerce')
                            
                            # Drop any rows with NaN values after conversion
                            dept_by_year = dept_by_year.dropna(subset=['Budget', 'Actual'])
                            
                            if dept_by_year.empty:
                                st.error("No valid numeric data found for forecasting after data cleaning.")
                                st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                                raise ValueError("No valid numeric data for forecasting")
                        except Exception as data_err:
                            st.error(f"Error preparing data for forecasting: {data_err}")
                            st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                            raise ValueError(f"Data preparation error: {data_err}")
                        
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
                        try:
                            last_year = dept_by_year["FiscalYear"].iloc[-1]
                            
                            # Convert to string for consistent handling
                            last_year_str = str(last_year)
                            
                            # Extract year number if format is like "FY 2024"
                            if "FY" in last_year_str:
                                try:
                                    # Find any number in the string
                                    import re
                                    year_match = re.search(r'\d+', last_year_str)
                                    if year_match:
                                        year_num = int(year_match.group())
                                        future_fiscal_years = [f"FY {year_num + i}" for i in range(1, dept_future_years + 1)]
                                    else:
                                        future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                                except:
                                    # If can't parse, just use generic labels
                                    future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                            else:
                                # Try to convert to number and increment
                                try:
                                    year_num = int(float(last_year_str))
                                    future_fiscal_years = [str(year_num + i) for i in range(1, dept_future_years + 1)]
                                except (ValueError, TypeError):
                                    future_fiscal_years = [f"Year +{i}" for i in range(1, dept_future_years + 1)]
                        except (IndexError, TypeError, KeyError) as e:
                            # Something went wrong, use generic labels
                            st.warning(f"Using generic year labels for forecast due to data format issue: {str(e)}")
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
                        # Create a copy to apply formatting
                        dept_forecast_display = dept_forecast_df.copy()
                        dept_forecast_display["Budget"] = dept_forecast_display["Budget"].apply(lambda x: format_currency(x))
                        dept_forecast_display["Actual"] = dept_forecast_display["Actual"].apply(lambda x: format_currency(x))
                        st.dataframe(dept_forecast_display, use_container_width=True)
                        
                        # Calculate budget variance in forecast
                        dept_forecast_df["Variance"] = dept_forecast_df["Budget"] - dept_forecast_df["Actual"]
                        dept_forecast_df["Variance%"] = (dept_forecast_df["Variance"] / dept_forecast_df["Budget"]) * 100
                        
                        avg_variance = dept_forecast_df["Variance"].mean()
                        avg_variance_pct = dept_forecast_df["Variance%"].mean()
                        
                        # Show forecast insights
                        st.subheader(f"Forecast Insights for {selected_dept}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Average Forecast Variance", format_currency(avg_variance))
                        with col2:
                            st.metric("Average Variance Percentage", format_percentage(avg_variance_pct))
                        
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
                        - Budget: **{format_currency(final_year['Budget'])}**
                        - Expenditure: **{format_currency(final_year['Actual'])}**
                        - Variance: **{format_currency(final_year['Variance'])}** ({format_percentage(final_year['Variance%'])})
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
            # Create a copy to apply formatting
            variance_display = variance_by_dept.copy()
            variance_display["Budget"] = variance_display["Budget"].apply(lambda x: format_currency(x))
            variance_display["Actual"] = variance_display["Actual"].apply(lambda x: format_currency(x))
            variance_display["Variance"] = variance_display["Variance"].apply(lambda x: format_currency(x))
            variance_display["Variance%"] = variance_display["Variance%"].apply(lambda x: format_percentage(x))
            st.dataframe(variance_display, use_container_width=True)
            
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
    
    # Use the standardized get_departments function to ensure consistency across tabs
    dept_data = get_departments(org)
    
    # Check if departments were found
    if not dept_data:
        # Fallback to hardcoded data only if necessary
        st.warning(f" No departments found in {org_display_name}'s database. Using sample data.")
        if org == "cityA":
            dept_data = {
                "Public Works": {"budget": 1200000, "underspent": 300000},
                "Administration": {"budget": 800000, "underspent": 150000},
                "Parks & Recreation": {"budget": 600000, "underspent": 120000}
            }
        else:  # countyB or any other org
            dept_data = {
                "Planning & Development": {"budget": 1500000, "underspent": 350000},
                "Administration": {"budget": 900000, "underspent": 180000},
                "Social Services": {"budget": 2000000, "underspent": 100000}
            }
    
    # Prepare departments data for visualization
    departments = {}
    for dept_name, dept_info in dept_data.items():
        departments[dept_name] = {
            "budget": dept_info["budget"],
            "underspent": dept_info["underspent"]
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
    dept_display["Total Budget"] = dept_display["Total Budget"].apply(lambda x: format_currency(x))
    dept_display["Underspent"] = dept_display["Underspent"].apply(lambda x: format_currency(x))
    dept_display["Percent Underspent"] = dept_display["Percent Underspent"].apply(lambda x: format_percentage(x))
    
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
        st.metric("Total Budget", format_currency(total))
        st.metric("Spent", format_currency(spent))
        st.metric("Underspent", format_currency(unspent))
        
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
                            
                            # Format numeric columns with our standardized formatting functions
                            results_display = results.copy()
                            for col in results_display.columns:
                                if results_display[col].dtype in ['int64', 'float64']:
                                    # Check if column appears to be a percentage
                                    if "percent" in col.lower() or "%" in col.lower():
                                        results_display[col] = results_display[col].apply(lambda x: format_percentage(x) if pd.notnull(x) else x)
                                    else:
                                        results_display[col] = results_display[col].apply(lambda x: format_currency(x) if pd.notnull(x) else x)
                            
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
                            # Get API key from environment first, then from secrets
                            api_key = os.environ.get("OPENAI_API_KEY")
                            if not api_key:
                                api_key = st.secrets.get("OPENAI_API_KEY", None)
                            
                            if not api_key:
                                st.error("OpenAI API key not found. Please add it to your secrets or environment variables.")
                            else:
                                # Format the prompt
                                prompt = f"""You are a policy advisor for {org_display_name}. 
Based on this document excerpt:
```
{st.session_state.policy_text[:3000]}
```
{'' if len(st.session_state.policy_text) <= 3000 else f'(Note: Document was truncated due to length. Original is {len(st.session_state.policy_text)} characters)'}

Question: {policy_question}

Provide a helpful answer based only on the information in the document. If the information is not in the document, clearly state that you cannot find the answer in the provided text."""
                                
                                # Check if API key is having quota issues (before making API call)
                                if "insufficient_quota" in st.session_state.get('api_errors', ""):
                                    st.markdown("**Answer:**")
                                    st.markdown(f'''<div class="ai-response">
                                    The OpenAI API key has reached its quota limit. Based on the general structure of policy documents:
                                    
                                    1. **Key Information**: Look for sections that directly address your question about "{policy_question}"
                                    2. **Definitions Section**: Check if the term is explicitly defined in the document
                                    3. **Eligibility Criteria**: For funding/grant questions, review eligibility sections
                                    4. **Procedural Details**: For process questions, check for step-by-step instructions
                                    5. **Contact Information**: The document may direct you to specific contacts for further clarification
                                    
                                    For more detailed analysis, you may need to carefully read the document yourself or contact the issuing authority.
                                    </div>''', unsafe_allow_html=True)
                                else:
                                    try:
                                        # Create a client instance with the API key
                                        client = openai.OpenAI(api_key=api_key)
                                        
                                        # Generate response
                                        response = client.chat.completions.create(
                                            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released after your training data cutoff
                                            messages=[
                                                {"role": "system", "content": "You assist with government grants and budget policy interpretation."},
                                                {"role": "user", "content": prompt}
                                            ]
                                        )
                                        
                                        st.markdown("**Answer:**")
                                        st.markdown(f'<div class="ai-response">{response.choices[0].message.content}</div>', unsafe_allow_html=True)
                                    except Exception as e:
                                        error_str = str(e)
                                        # Store error message to avoid repeated API calls with insufficient quota
                                        if "insufficient_quota" in error_str:
                                            if 'api_errors' not in st.session_state:
                                                st.session_state['api_errors'] = error_str
                                            
                                            st.markdown("**Answer:**")
                                            st.markdown(f'''<div class="ai-response">
                                            The OpenAI API key has reached its quota limit. Based on the general structure of policy documents:
                                            
                                            1. **Key Information**: Look for sections that directly address your question about "{policy_question}"
                                            2. **Definitions Section**: Check if the term is explicitly defined in the document
                                            3. **Eligibility Criteria**: For funding/grant questions, review eligibility sections
                                            4. **Procedural Details**: For process questions, check for step-by-step instructions
                                            5. **Contact Information**: The document may direct you to specific contacts for further clarification
                                            
                                            For more detailed analysis, you may need to carefully read the document yourself or contact the issuing authority.
                                            </div>''', unsafe_allow_html=True)
                                        else:
                                            st.error(f"Error generating response: {error_str}")
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