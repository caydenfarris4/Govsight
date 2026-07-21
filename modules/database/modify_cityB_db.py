import sqlite3
import pandas as pd

# This script modifies the cityB_dashboard_data.db to contain unique data for City B

def migrate_and_modify():
    """Modify the database to replace 'City A' with 'City B' and update some values"""
    try:
        # Connect to the database
        conn = sqlite3.connect('cityB_dashboard_data.db')
        cursor = conn.cursor()
        
        # Check if the database has the expected table structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables or ('DepartmentPerformance',) not in tables:
            print("Error: Required table 'DepartmentPerformance' not found in database.")
            conn.close()
            return False
        
        # Get the table schema to check if 'id' is auto-increment
        cursor.execute("PRAGMA table_info(DepartmentPerformance)")
        columns = cursor.fetchall()
        print(f"Table columns: {columns}")
        
        # Check if table has id column
        has_id_column = any(col[1] == 'id' for col in columns)
            
        # Get data from the database
        query = "SELECT * FROM DepartmentPerformance"
        df = pd.read_sql_query(query, conn)
        
        # Show initial statistics
        print(f"Original database has {len(df)} records")
        print(f"Organizations in original data: {df['Organization'].unique()}")
        
        # Remove id column if it exists to avoid UNIQUE constraint issues
        if has_id_column and 'id' in df.columns:
            df = df.drop('id', axis=1)
            print("Dropped id column to avoid constraint issues")
        
        # Replace all instances of 'City A' or 'Cityville' with 'City B'
        df['Organization'] = df['Organization'].str.replace('cityA', 'cityB')
        df['Organization'] = df['Organization'].str.replace('City A', 'City B')
        df['Organization'] = df['Organization'].str.replace('Cityville', 'City B')
        
        # Modify the Budget and Actual values to make them different
        # Increase budgets by 20% and actuals by different percentages to create a different pattern
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
            df['Department'] = df['Department'].str.replace(old_dept, new_dept)
        
        # Add some new funds specific to City B
        df_sample = df.sample(n=min(50, len(df)))
        df_sample['Fund'] = 'City B Development Fund'
        df_sample2 = df.sample(n=min(40, len(df)))
        df_sample2['Fund'] = 'Technology Modernization Fund'
        
        # Combine the original data with new fund samples
        df = pd.concat([df, df_sample, df_sample2], ignore_index=True)
        
        # Clear the existing data in the DepartmentPerformance table
        cursor.execute("DELETE FROM DepartmentPerformance")
        conn.commit()
        
        # Recreate the table schema if necessary (without id column)
        if has_id_column:
            # Get column names and types excluding 'id'
            column_defs = []
            for col in columns:
                if col[1] != 'id':  # Skip the id column
                    col_name = col[1]
                    col_type = col[2]
                    not_null = "NOT NULL" if col[3] == 1 else ""
                    column_defs.append(f"{col_name} {col_type} {not_null}")
            
            # Drop original table and create a version without auto-increment ID
            cursor.execute("DROP TABLE DepartmentPerformance")
            create_stmt = f"CREATE TABLE DepartmentPerformance ({', '.join(column_defs)})"
            print(f"Recreating table with new schema: {create_stmt}")
            cursor.execute(create_stmt)
            conn.commit()
        
        # Insert the modified data back into the database
        df.to_sql('DepartmentPerformance', conn, if_exists='replace', index=False)
        
        # Show final statistics
        print(f"Modified database now has {len(df)} records")
        print(f"Organizations in new data: {df['Organization'].unique()}")
        print(f"Departments in new data: {sorted(df['Department'].unique())}")
        print(f"Funds in new data: {sorted(df['Fund'].unique())}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error modifying City B database: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_and_modify()
    if success:
        print("City B database modified successfully!")
    else:
        print("Failed to modify City B database.")