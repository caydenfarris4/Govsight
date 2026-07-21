import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

# This script creates sample data for the City B database

def generate_cityB_data():
    """Generate and save sample data for City B"""
    try:
        # Create data structure
        departments = [
            'Infrastructure Services',
            'Parks & Community Services',
            'Public Safety',
            'City Administration',
            'Finance',
            'Human Resources',
            'Technology Services',
            'Community Development',
            'Economic Development',
            'Transportation',
            'Library'
        ]
        
        funds = [
            'General Fund',
            'Capital Improvement Fund',
            'Special Revenue Fund',
            'Enterprise Fund',
            'Technology Modernization Fund',
            'City B Development Fund',
            'Transportation Fund',
            'Parks Fund',
            'Community Grant Fund',
            'Water & Sewer Fund'
        ]
        
        fiscal_years = ['FY 2021', 'FY 2022', 'FY 2023', 'FY 2024']
        
        # Generate sample data
        data = []
        
        for dept in departments:
            for fund in np.random.choice(funds, size=min(4, len(funds)), replace=False):
                for year in fiscal_years:
                    # Generate consistent but varied budget by department and fund
                    base_budget = 100000 + (hash(dept) % 10) * 50000 + (hash(fund) % 5) * 100000
                    # Increase budget by 5% each year
                    year_index = fiscal_years.index(year)
                    budget = base_budget * (1.05 ** year_index)
                    
                    # Generate monthly data
                    for month in range(1, 13):
                        # For FY 2024, only include months up to current month
                        if year == 'FY 2024' and month > datetime.now().month:
                            continue
                            
                        # Monthly budget is annual budget / 12
                        monthly_budget = budget / 12
                        
                        # Actual varies by department and month
                        # Some departments overspend, some underspend
                        dept_factor = 0.85 + (hash(dept) % 100) / 250  # between 0.85 and 1.25
                        
                        # Spending typically increases throughout the year
                        month_factor = 0.85 + (month / 20)  # increases with month
                        
                        # Last month of year often has higher spending
                        if month == 12:
                            month_factor *= 1.2
                            
                        actual = monthly_budget * dept_factor * month_factor
                        
                        # Add some randomness
                        actual = actual * np.random.uniform(0.9, 1.1)
                        
                        data.append({
                            'Department': dept,
                            'Fund': fund,
                            'FiscalYear': year,
                            'Budget': round(monthly_budget, 2),
                            'Actual': round(actual, 2),
                            'Month': month,
                            'Organization': 'cityB'
                        })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Connect to database and save data
        conn = sqlite3.connect('cityB_dashboard_data.db')
        
        # Save to database
        df.to_sql('DepartmentPerformance', conn, if_exists='replace', index=False)
        
        print(f"Generated {len(df)} records for City B")
        print(f"Departments: {sorted(df['Department'].unique())}")
        print(f"Funds: {sorted(df['Fund'].unique())}")
        print(f"Fiscal Years: {sorted(df['FiscalYear'].unique())}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error generating City B data: {str(e)}")
        return False

if __name__ == "__main__":
    success = generate_cityB_data()
    if success:
        print("City B data generated successfully!")
    else:
        print("Failed to generate City B data.")