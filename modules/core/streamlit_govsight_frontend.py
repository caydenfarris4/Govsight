import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sqlite3
from datetime import datetime

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
    .department-data {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"> GovSight Financial Analyzer</div>', unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
A powerful tool for municipal financial analysis and scenario planning. 
Connect to your municipal budget database, analyze funding sources, and visualize different scenarios.
</div>
""", unsafe_allow_html=True)

# Database Connection Functions
def get_database_connection():
    """Create a connection to the SQLite database"""
    try:
        return sqlite3.connect('budget.db')
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

# Main App Interface
# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["Scenario Planner", "Historical Analysis", "Department Insights"])

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
            st.error(" No projects found in the database. Please check your database connection.")
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
            st.error(" No departments found in the database. Please check your database connection.")
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
    st.download_button(" Download Scenario as CSV", data=csv_data, file_name="funding_scenario.csv", mime="text/csv")
    
    # Scenario history
    st.subheader(" Save & View Scenarios")
    
    # Load existing scenarios from database
    db_scenarios = get_scenarios(limit=6)
    
    # Custom scenario name with timestamp for uniqueness
    timestamp = datetime.now().strftime("%m/%d/%Y %H:%M")
    scenario_name = st.text_input("Scenario Name", value=f"Scenario for {selected_project_data['name']} - {timestamp}")
    
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
        st.subheader(" Previously Saved Scenarios")
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
    st.markdown('<div class="sub-header"> Historical Funding Analysis</div>', unsafe_allow_html=True)
    
    # Placeholder for historical analysis
    st.info("Historical analysis functionality will be implemented in the next phase. This section will show trend analysis of funding patterns, project completion rates, and budget allocation effectiveness over time.")
    
    # Sample visualization for demonstration
    years = ["2020", "2021", "2022", "2023", "2024"]
    funding_types = ["Tax Revenue", "Grants", "Bonds", "Department Reallocation"]
    
    data = {
        "Tax Revenue": [350000, 400000, 450000, 525000, 550000],
        "Grants": [225000, 275000, 250000, 400000, 450000],
        "Bonds": [800000, 750000, 650000, 500000, 450000],
        "Department Reallocation": [120000, 150000, 200000, 250000, 275000]
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
        title="5-Year Funding Trends",
        xaxis_title="Year",
        yaxis_title="Amount ($)",
        legend_title="Funding Type",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown('<div class="sub-header">🏢 Department Budget Insights</div>', unsafe_allow_html=True)
    
    # Load departments from database
    departments = get_departments()
    if not departments:
        st.error(" No departments found in the database. Please check your database connection.")
    else:
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
                title="Department Budget Overview",
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
        st.subheader("Department Budget Data")
        st.dataframe(dept_display, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    GovSight Financial Analyzer | A comprehensive tool for municipal financial planning
    <br>© 2024 GovSight Analytics
</div>
""", unsafe_allow_html=True)