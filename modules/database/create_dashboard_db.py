import sqlite3
import os

# Check if the database exists and delete if it does
if os.path.exists('org_dashboard_data.db'):
    os.remove('org_dashboard_data.db')

# Create a new database
conn = sqlite3.connect('org_dashboard_data.db')
cursor = conn.cursor()

# Create department performance table
cursor.execute('''
CREATE TABLE DepartmentPerformance (
    id INTEGER PRIMARY KEY,
    Department TEXT NOT NULL,
    Fund TEXT NOT NULL,
    FiscalYear TEXT NOT NULL,
    Budget REAL NOT NULL,
    Actual REAL NOT NULL,
    Month INTEGER,
    Organization TEXT NOT NULL
)
''')

# Sample data for City A (FY 2024)
city_a_data_2024 = [
    ("Public Works", "General Fund", "FY 2024", 1200000, 950000, 12, "cityA"),
    ("Administration", "General Fund", "FY 2024", 800000, 720000, 12, "cityA"),
    ("Parks & Recreation", "General Fund", "FY 2024", 600000, 550000, 12, "cityA"),
    ("IT Services", "General Fund", "FY 2024", 500000, 475000, 12, "cityA"),
    ("Police", "General Fund", "FY 2024", 2000000, 1940000, 12, "cityA"),
    ("Fire Department", "General Fund", "FY 2024", 1800000, 1750000, 12, "cityA"),
    ("Community Development", "General Fund", "FY 2024", 750000, 680000, 12, "cityA")
]

# Sample data for City A (FY 2023)
city_a_data_2023 = [
    ("Public Works", "General Fund", "FY 2023", 1100000, 1050000, 12, "cityA"),
    ("Administration", "General Fund", "FY 2023", 750000, 700000, 12, "cityA"),
    ("Parks & Recreation", "General Fund", "FY 2023", 550000, 520000, 12, "cityA"),
    ("IT Services", "General Fund", "FY 2023", 450000, 430000, 12, "cityA"),
    ("Police", "General Fund", "FY 2023", 1900000, 1850000, 12, "cityA"),
    ("Fire Department", "General Fund", "FY 2023", 1700000, 1680000, 12, "cityA"),
    ("Community Development", "General Fund", "FY 2023", 700000, 650000, 12, "cityA")
]

# Sample data for County B (FY 2024)
county_b_data_2024 = [
    ("Planning & Development", "General Fund", "FY 2024", 1500000, 1350000, 12, "countyB"),
    ("Administration", "General Fund", "FY 2024", 900000, 820000, 12, "countyB"),
    ("Social Services", "General Fund", "FY 2024", 2000000, 1920000, 12, "countyB"),
    ("IT Services", "General Fund", "FY 2024", 600000, 570000, 12, "countyB"),
    ("Sheriff", "General Fund", "FY 2024", 2200000, 2150000, 12, "countyB"),
    ("Public Health", "General Fund", "FY 2024", 1700000, 1600000, 12, "countyB"),
    ("Economic Development", "General Fund", "FY 2024", 850000, 780000, 12, "countyB")
]

# Sample data for County B (FY 2023)
county_b_data_2023 = [
    ("Planning & Development", "General Fund", "FY 2023", 1400000, 1350000, 12, "countyB"),
    ("Administration", "General Fund", "FY 2023", 850000, 800000, 12, "countyB"),
    ("Social Services", "General Fund", "FY 2023", 1900000, 1850000, 12, "countyB"),
    ("IT Services", "General Fund", "FY 2023", 550000, 530000, 12, "countyB"),
    ("Sheriff", "General Fund", "FY 2023", 2100000, 2070000, 12, "countyB"),
    ("Public Health", "General Fund", "FY 2023", 1600000, 1550000, 12, "countyB"),
    ("Economic Development", "General Fund", "FY 2023", 800000, 750000, 12, "countyB")
]

# Insert all data
all_data = city_a_data_2024 + city_a_data_2023 + county_b_data_2024 + county_b_data_2023

cursor.executemany('''
INSERT INTO DepartmentPerformance 
(Department, Fund, FiscalYear, Budget, Actual, Month, Organization)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', all_data)

# Commit and close
conn.commit()
conn.close()

print("Dashboard database created successfully with sample data!")