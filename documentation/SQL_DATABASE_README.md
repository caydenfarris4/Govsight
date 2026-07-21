# GovSight SQL Database Connection

This document explains how to use the SQL database connection tools to connect GovSight to various SQL database systems.

## Supported Database Types

The SQL connection module supports the following database types:

- **SQLite** (default, file-based)
- **PostgreSQL**
- **MySQL/MariaDB**
- **Microsoft SQL Server**

## Key Components

1. **sql_connection.py**: The core SQL connection module that handles connections to various database types
2. **enhanced_db_utils.py**: Enhanced database utilities that integrate with the existing application
3. **city_config_tool.py**: A command-line tool for adding and managing cities/organizations
4. **sql_database_demo.py**: A demonstration script showing how to use the SQL connection tools

## Adding a New City/Organization

To add a new city or organization to GovSight:

1. Run the city configuration tool:

```bash
python city_config_tool.py add-city
```

2. Follow the prompts to provide:
   - Organization ID (e.g., `cityC`, `countyD`)
   - Organization display name
   - Access password (optional)
   - Database type and connection details
   - Visual customization options

3. Test the database connection:

```bash
python city_config_tool.py test-connection cityC
```

4. Access the new city in GovSight by navigating to `/?org=cityC`

## Connection Examples

### SQLite (File-based)

```python
from sql_connection import SQLDatabase

# Connect to SQLite
db = SQLDatabase(
    dbtype='sqlite',
    database_path='cityC_dashboard_data.db'
)

# Execute a query
results = db.execute_query("SELECT * FROM departments")
```

### PostgreSQL

```python
from sql_connection import SQLDatabase

# Connect to PostgreSQL
db = SQLDatabase(
    dbtype='postgresql',
    host='localhost',
    port=5432,
    user='username',
    password='password',
    database='budget_db'
)

# Execute a query
results = db.execute_query("SELECT * FROM departments")
```

### MySQL/MariaDB

```python
from sql_connection import SQLDatabase

# Connect to MySQL
db = SQLDatabase(
    dbtype='mysql',
    host='localhost',
    port=3306,
    user='username',
    password='password',
    database='budget_db'
)

# Execute a query
results = db.execute_query("SELECT * FROM departments")
```

### Microsoft SQL Server

```python
from sql_connection import SQLDatabase

# Connect to MSSQL
db = SQLDatabase(
    dbtype='mssql',
    host='localhost',
    port=1433,
    user='username',
    password='password',
    database='budget_db'
)

# Execute a query
results = db.execute_query("SELECT * FROM departments")
```

## Using Environment Variables

You can also configure database connections using environment variables:

```python
from sql_connection import SQLDatabase

# Load from environment variables with prefix CITYC_
db = SQLDatabase(env_prefix='CITYC')
```

Required environment variables:
- `CITYC_DBTYPE`: Database type (sqlite, postgresql, mysql, mssql)
- `CITYC_DATABASE_PATH`: Path to SQLite database file (for sqlite)
- `CITYC_HOST`: Database host (for postgresql, mysql, mssql)
- `CITYC_PORT`: Database port (for postgresql, mysql, mssql)
- `CITYC_USER`: Database username (for postgresql, mysql, mssql)
- `CITYC_PASSWORD`: Database password (for postgresql, mysql, mssql)
- `CITYC_DATABASE`: Database name (for postgresql, mysql, mssql)

## Using with GovSight

To use these new SQL connection tools with the GovSight application:

1. Update imports in `app.py`:

```python
# Replace this:
from common_utils import get_connection, execute_query, get_departments

# With this:
from enhanced_db_utils import get_connection, execute_query, get_departments
```

2. The application will automatically use the correct database connection for each organization based on the configuration in `config.json`.

## Database Tables Required

For a new SQL database to work with GovSight, it needs to have the following tables:

### DepartmentPerformance

```sql
CREATE TABLE DepartmentPerformance (
    ID INTEGER PRIMARY KEY,
    Organization TEXT,
    Department TEXT,
    FiscalYear TEXT,
    Budget REAL,
    Actual REAL
);
```

### For scenarios and planning (in the main database):

```sql
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT,
    total_budget REAL,
    underspent REAL
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    cost REAL,
    department_id INTEGER,
    priority INTEGER,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE scenarios (
    id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    total_amount REAL,
    created_at DATETIME
);

CREATE TABLE scenario_departments (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER,
    department_id INTEGER,
    amount REAL,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id),
    FOREIGN KEY (department_id) REFERENCES departments(id)
);
```

## Migrating Data from SQLite to Another Database

1. Use the db_schema_converter.py tool to generate SQL for your target database:

```bash
python db_schema_converter.py sqlite_to_postgres_sql cityA_dashboard_data.db postgres_schema.sql
```

2. Create the new database and tables in your target database system.

3. Export data from SQLite and import it to your target database.

4. Update the organization's configuration to use the new database:

```bash
python city_config_tool.py add-city
```

## Troubleshooting

### Connection Issues

If you're having trouble connecting to a database:

1. Check the database credentials and connection details
2. Verify the database server is running and accessible
3. Test the connection using the city_config_tool:

```bash
python city_config_tool.py test-connection cityC
```

### Schema Issues

If tables or columns are missing:

1. Check the database schema using:

```bash
python city_config_tool.py test-connection cityC
```

2. Create any missing tables or columns based on the required schema above.

### Performance Issues

If the application is running slowly:

1. Check that connection pooling is enabled (default)
2. Add appropriate indexes to your database tables
3. Optimize your queries

## Support for Multiple Cities/Organizations

The GovSight application now supports multiple cities/organizations with their own:

1. Database connections (any supported SQL database type)
2. Access passwords
3. Visual customization (colors, logos)
4. Data isolation (each organization can only access its own data)

This allows you to scale the application to support many different municipalities from a single instance.