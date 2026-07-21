import sqlite3
import pandas as pd
import os

# This script recreates the cityB_dashboard_data.db with modified data for City B

def recreate_database():
    """Recreate the database structure for City B"""
    try:
        # First, remove the existing database if it exists
        if os.path.exists('cityB_dashboard_data.db'):
            os.remove('cityB_dashboard_data.db')
            print("Removed existing cityB_dashboard_data.db")
        
        # Connect to the original database to get schema
        orig_conn = sqlite3.connect('org_dashboard_data.db')
        orig_cursor = orig_conn.cursor()
        
        # Get the CREATE TABLE statement for DepartmentPerformance
        orig_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='DepartmentPerformance'")
        create_table_sql = orig_cursor.fetchone()[0]
        
        # Create the new database
        new_conn = sqlite3.connect('cityB_dashboard_data.db')
        new_cursor = new_conn.cursor()
        
        # Create the table using the same schema
        new_cursor.execute(create_table_sql)
        new_conn.commit()
        
        # Get data from the original database
        query = "SELECT * FROM DepartmentPerformance"
        df = pd.read_sql_query(query, orig_conn)
        
        # Show initial statistics
        print(f"Original database has {len(df)} records")
        print(f"Organizations in original data: {df['Organization'].unique()}")
        
        # Replace all instances of organization names with 'cityB'
        df['Organization'] = 'cityB'
        
        # Modify the Budget and Actual values to make them different
        # Increase budgets by 20% and actuals by different percentages
        df['Budget'] = (df['Budget'] * 1.2).round(2)  # 20% higher budget
        
        # Vary actuals based on department to create different performance trends
        for department in df['Department'].unique():
            # Get the department-specific adjustment factor (between 0.8 and 1.3)
            adjustment = 0.8 + ((hash(department) % 50) / 100)
            dept_mask = df['Department'] == department
            df.loc[dept_mask, 'Actual'] = (df.loc[dept_mask, 'Actual'] * adjustment).round(2)
        
        # Change some department names to reflect City B's unique structure
        department_mapping = {
            'Public Works': 'Infrastructure Services',
            'Parks & Recreation': 'Parks & Community Services',
            'City Manager': 'City Administration',
            'IT': 'Technology Services'
        }
        
        for old_dept, new_dept in department_mapping.items():
            df.loc[df['Department'] == old_dept, 'Department'] = new_dept
        
        # Create new records with unique funds for City B
        new_records = []
        
        # Sample existing data to create new fund records
        for i, row in df.sample(n=min(10, len(df))).iterrows():
            new_row = row.copy()
            new_row['Fund'] = 'City B Development Fund'
            new_row['Budget'] = round(new_row['Budget'] * 1.1, 2)
            new_row['Actual'] = round(new_row['Budget'] * 0.85, 2)
            new_records.append(new_row)
            
        for i, row in df.sample(n=min(8, len(df))).iterrows():
            new_row = row.copy()
            new_row['Fund'] = 'Technology Modernization Fund'
            new_row['Budget'] = round(new_row['Budget'] * 1.15, 2)
            new_row['Actual'] = round(new_row['Budget'] * 0.92, 2)
            new_records.append(new_row)
        
        # Convert new records to DataFrame and append to original data
        new_records_df = pd.DataFrame(new_records)
        df = pd.concat([df, new_records_df], ignore_index=True)
        
        # Remove the ID column to let SQLite auto-generate new IDs
        if 'id' in df.columns:
            df = df.drop('id', axis=1)
        
        # Insert the modified data into the City B database
        df.to_sql('DepartmentPerformance', new_conn, if_exists='append', index=False)
        
        # Show final statistics
        print(f"Modified database now has {len(df)} records")
        print(f"Organizations in new data: {df['Organization'].unique()}")
        print(f"Departments in new data: {sorted(df['Department'].unique())}")
        print(f"Funds in new data: {sorted(df['Fund'].unique())}")
        
        # Close connections
        orig_conn.close()
        new_conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error creating City B database: {str(e)}")
        return False

if __name__ == "__main__":
    success = recreate_database()
    if success:
        print("City B database created successfully!")
    else:
        print("Failed to create City B database.")