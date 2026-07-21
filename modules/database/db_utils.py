import sqlite3
import pandas as pd

def get_database_connection():
    """Create and return a database connection"""
    return sqlite3.connect('budget.db')

def execute_query(query, params=(), fetchall=True):
    """Execute a query and return results"""
    conn = get_database_connection()
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
    finally:
        conn.close()

def get_departments():
    """Get all departments from the database"""
    query = "SELECT id, name, total_budget, underspent FROM departments"
    departments_data = execute_query(query)
    
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
            # Get department ID
            dept_id_query = "SELECT id FROM departments WHERE name = ?"
            cursor.execute(dept_id_query, (dept_name,))
            dept_id = cursor.fetchone()[0]
            
            # Insert allocation
            cursor.execute('''
            INSERT INTO scenario_department_allocations 
            (scenario_id, department_id, allocation_amount)
            VALUES (?, ?, ?)
            ''', (scenario_id, dept_id, amount))
        
        conn.commit()
        return scenario_id
    finally:
        conn.close()

def get_scenarios(limit=10):
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
        for alloc in allocations_data:
            department_allocations[alloc[0]] = alloc[1]
        
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
            "Departmental Reallocation": sum(department_allocations.values())
        })
    
    return scenarios

def get_scenario_data_as_df(scenario_id):
    """Get scenario data as pandas DataFrame for CSV export"""
    # Get main scenario data
    scenario_query = '''
    SELECT name, total_cost, tax_revenue, grant_funding, private_investment, bonds_needed
    FROM scenarios WHERE id = ?
    '''
    scenario_data = execute_query(scenario_query, (scenario_id,), fetchall=False)
    
    if not scenario_data:
        return None, None
    
    # Get department allocations
    alloc_query = '''
    SELECT d.name, sda.allocation_amount
    FROM scenario_department_allocations sda
    JOIN departments d ON sda.department_id = d.id
    WHERE sda.scenario_id = ?
    '''
    allocations_data = execute_query(alloc_query, (scenario_id,))
    
    # Create DataFrame
    data = {
        "Funding Source": ["Departmental Reallocation", "Tax Revenue", "Grant Funding", 
                          "Private Investment", "Bonds Needed", "Total Cost"],
        "Amount": [sum([a[1] for a in allocations_data]) if allocations_data else 0, 
                  scenario_data[2], scenario_data[3], 
                  scenario_data[4], scenario_data[5],
                  scenario_data[1]]
    }
    
    df = pd.DataFrame(data)
    
    # Add department breakdown
    if allocations_data:
        dept_data = {
            "Department": [a[0] for a in allocations_data],
            "Allocation": [a[1] for a in allocations_data]
        }
        dept_df = pd.DataFrame(dept_data)
        
        return df, dept_df
    
    return df, None