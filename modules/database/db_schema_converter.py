import sqlite3
import pandas as pd
import os
import argparse

def sqlite_to_postgres_sql(db_file, output_file):
    """Convert SQLite database schema to PostgreSQL-compatible SQL commands"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    with open(output_file, 'w') as f:
        f.write("-- PostgreSQL schema generated from SQLite database\n\n")
        
        for table in tables:
            table_name = table[0]
            
            # Skip SQLite system tables
            if table_name.startswith('sqlite_'):
                continue
                
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Get data
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            
            # Write CREATE TABLE statement
            f.write(f"-- Table: {table_name}\n")
            f.write(f"CREATE TABLE {table_name} (\n")
            
            column_defs = []
            primary_keys = []
            
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, is_pk = col
                
                # Convert SQLite types to PostgreSQL types
                pg_type = col_type.upper()
                if pg_type == 'INTEGER PRIMARY KEY':
                    pg_type = 'SERIAL'
                    is_pk = 1
                elif pg_type == 'INTEGER':
                    pg_type = 'INTEGER'
                elif pg_type == 'REAL':
                    pg_type = 'DOUBLE PRECISION'
                elif pg_type == 'TEXT':
                    pg_type = 'TEXT'
                elif pg_type == 'BLOB':
                    pg_type = 'BYTEA'
                elif 'CHAR' in pg_type:
                    pg_type = pg_type.replace('CHAR', 'VARCHAR')
                
                # Build column definition
                col_def = f"    {col_name} {pg_type}"
                
                if not_null:
                    col_def += " NOT NULL"
                    
                if default_val is not None:
                    if default_val.startswith("'") or col_type.upper() == 'TEXT':
                        col_def += f" DEFAULT '{default_val}'"
                    else:
                        col_def += f" DEFAULT {default_val}"
                
                column_defs.append(col_def)
                
                if is_pk:
                    primary_keys.append(col_name)
            
            # Add primary key constraint if there's a primary key
            if primary_keys:
                if len(primary_keys) == 1 and 'SERIAL' in column_defs[columns[0][0]]:
                    column_defs[columns[0][0]] += " PRIMARY KEY"
                else:
                    pk_constraint = f"    PRIMARY KEY ({', '.join(primary_keys)})"
                    column_defs.append(pk_constraint)
            
            f.write(',\n'.join(column_defs))
            f.write("\n);\n\n")
            
            # Write INSERT statements for data
            if rows:
                f.write(f"-- Data for table: {table_name}\n")
                
                for row in rows:
                    values = []
                    for i, val in enumerate(row):
                        if val is None:
                            values.append('NULL')
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        else:
                            # Escape single quotes in string values
                            val_str = str(val).replace("'", "''")
                            values.append(f"'{val_str}'")
                    
                    f.write(f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n")
                
                f.write("\n")
    
    conn.close()
    print(f"Schema exported to {output_file}")

def sqlite_to_mysql_sql(db_file, output_file):
    """Convert SQLite database schema to MySQL-compatible SQL commands"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    with open(output_file, 'w') as f:
        f.write("-- MySQL schema generated from SQLite database\n\n")
        
        for table in tables:
            table_name = table[0]
            
            # Skip SQLite system tables
            if table_name.startswith('sqlite_'):
                continue
                
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Get data
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            
            # Write CREATE TABLE statement
            f.write(f"-- Table: {table_name}\n")
            f.write(f"CREATE TABLE `{table_name}` (\n")
            
            column_defs = []
            primary_keys = []
            
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, is_pk = col
                
                # Convert SQLite types to MySQL types
                mysql_type = col_type.upper()
                if mysql_type == 'INTEGER PRIMARY KEY':
                    mysql_type = 'INT AUTO_INCREMENT'
                    is_pk = 1
                elif mysql_type == 'INTEGER':
                    mysql_type = 'INT'
                elif mysql_type == 'REAL':
                    mysql_type = 'DOUBLE'
                elif mysql_type == 'TEXT':
                    mysql_type = 'TEXT'
                elif mysql_type == 'BLOB':
                    mysql_type = 'BLOB'
                
                # Build column definition
                col_def = f"    `{col_name}` {mysql_type}"
                
                if not_null:
                    col_def += " NOT NULL"
                    
                if default_val is not None:
                    if default_val.startswith("'") or col_type.upper() == 'TEXT':
                        col_def += f" DEFAULT '{default_val}'"
                    else:
                        col_def += f" DEFAULT {default_val}"
                
                column_defs.append(col_def)
                
                if is_pk:
                    primary_keys.append(col_name)
            
            # Add primary key constraint if there's a primary key
            if primary_keys:
                pk_constraint = f"    PRIMARY KEY ({', '.join([f'`{pk}`' for pk in primary_keys])})"
                column_defs.append(pk_constraint)
            
            f.write(',\n'.join(column_defs))
            f.write("\n);\n\n")
            
            # Write INSERT statements for data
            if rows:
                f.write(f"-- Data for table: {table_name}\n")
                
                for row in rows:
                    values = []
                    for i, val in enumerate(row):
                        if val is None:
                            values.append('NULL')
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        else:
                            # Escape single quotes in string values
                            val_str = str(val).replace("'", "''")
                            values.append(f"'{val_str}'")
                    
                    f.write(f"INSERT INTO `{table_name}` VALUES ({', '.join(values)});\n")
                
                f.write("\n")
    
    conn.close()
    print(f"Schema exported to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Convert SQLite database to other SQL formats')
    parser.add_argument('--sqlite_file', type=str, default='budget.db', help='SQLite database file to convert')
    parser.add_argument('--format', type=str, choices=['postgres', 'mysql'], default='postgres', help='Target SQL format')
    parser.add_argument('--output', type=str, help='Output SQL file name (optional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.sqlite_file):
        print(f"Error: SQLite file '{args.sqlite_file}' not found.")
        return
    
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(args.sqlite_file)[0]
        output_file = f"{base_name}_{args.format}.sql"
    
    if args.format == 'postgres':
        sqlite_to_postgres_sql(args.sqlite_file, output_file)
    elif args.format == 'mysql':
        sqlite_to_mysql_sql(args.sqlite_file, output_file)
    
    print(f"Schema conversion complete. Output saved to {output_file}")
    print(f"Note: You may need to make manual adjustments to the SQL file for database-specific features.")

if __name__ == "__main__":
    main()