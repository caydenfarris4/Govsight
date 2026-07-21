import sqlite3
import os

# Check if the database already exists and delete if it does
if os.path.exists('budget.db'):
    os.remove('budget.db')

# Create a new database
conn = sqlite3.connect('budget.db')
cursor = conn.cursor()

# Create departments table
cursor.execute('''
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    total_budget REAL NOT NULL,
    underspent REAL NOT NULL
)
''')

# Create funding_sources table
cursor.execute('''
CREATE TABLE funding_sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
)
''')

# Create projects table
cursor.execute('''
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    total_cost REAL NOT NULL,
    status TEXT DEFAULT 'Proposed'
)
''')

# Create scenarios table to store saved scenarios
cursor.execute('''
CREATE TABLE scenarios (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    project_id INTEGER,
    total_cost REAL NOT NULL,
    tax_revenue REAL NOT NULL,
    grant_funding REAL NOT NULL,
    private_investment REAL NOT NULL,
    bonds_needed REAL NOT NULL,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
)
''')

# Create scenario_department_allocations table
cursor.execute('''
CREATE TABLE scenario_department_allocations (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    allocation_amount REAL NOT NULL,
    FOREIGN KEY (scenario_id) REFERENCES scenarios (id),
    FOREIGN KEY (department_id) REFERENCES departments (id)
)
''')

# Insert sample departments
departments = [
    ("Public Works", 1200000, 300000),
    ("Administration", 800000, 150000),
    ("Parks & Recreation", 600000, 120000),
    ("IT Services", 500000, 50000),
    ("Police", 2000000, 80000),
    ("Fire Department", 1800000, 70000),
    ("Community Development", 750000, 130000)
]

cursor.executemany('''
INSERT INTO departments (name, total_budget, underspent)
VALUES (?, ?, ?)
''', departments)

# Insert sample funding sources
funding_sources = [
    ("Tax Revenue", "Projected increase in tax revenue from project"),
    ("Grant Funding", "Available grants from state and federal sources"),
    ("Private Investment", "Funds from private sector partners"),
    ("Bond Issuance", "Municipal bonds to cover funding gaps")
]

cursor.executemany('''
INSERT INTO funding_sources (name, description)
VALUES (?, ?)
''', funding_sources)

# Insert sample projects
projects = [
    ("Downtown Revitalization", "Redevelopment of the downtown area to increase economic activity", 2000000, "Proposed"),
    ("Community Center Expansion", "Expanding the existing community center with new facilities", 1500000, "Proposed"),
    ("Public Park Improvements", "Upgrading equipment and adding amenities to city parks", 800000, "Proposed"),
    ("Smart City Infrastructure", "Implementing IoT sensors and digital infrastructure", 3000000, "Proposed")
]

cursor.executemany('''
INSERT INTO projects (name, description, total_cost, status)
VALUES (?, ?, ?, ?)
''', projects)

# Commit changes and close connection
conn.commit()
conn.close()

print("Database created successfully with sample data!")