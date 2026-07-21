# GovSight Financial Analyzer

A municipal funding scenario optimizer that provides intelligent, interactive financial analysis across multiple organizations.

## Key Features

- Multi-organization architecture with organization-specific dashboards
- Password-based authentication system with secure access controls
- Interactive financial analysis tools with Plotly visualizations
- AI-powered assistant for natural language querying of budget data
- Predictive forecasting tools integrated into the Historical Analysis tab
- Support for multiple database systems (SQLite, MySQL, PostgreSQL, MS SQL Server)

## Getting Started

### Authentication

The application uses a simple password-based authentication system. The default credentials are:

- Organization: `Cityville` - Password: `cityA2024`
- Organization: `Countyville` - Password: `countyB2024` 

You can modify these credentials in the `config.json` file.

### Database Connections

This application includes built-in support for connecting to different database systems. By default, it uses SQLite databases (`budget.db` and `org_dashboard_data.db`).

To configure the application for a different database system:

1. Run the interactive setup script:
   ```bash
   ./setup_database.sh
   ```

2. Follow the prompts to select your database type (MySQL, PostgreSQL, or MS SQL Server) and enter your connection details.

### Database Schema Conversion

If you need to convert your existing SQLite schema to PostgreSQL or MySQL:

```bash
# Convert to PostgreSQL
python db_schema_converter.py --sqlite_file budget.db --format postgres --output postgres_schema.sql

# Convert to MySQL
python db_schema_converter.py --sqlite_file budget.db --format mysql --output mysql_schema.sql
```

## AI Assistant Integration

The AI Assistant feature uses OpenAI's API for natural language processing. To enable this feature:

1. Set your OpenAI API key as an environment variable named `OPENAI_API_KEY`
2. The AI Assistant will then be available in the GovSight AI Assistant tab

## Multi-Organization Support

The application supports multiple organizations with independent data and dashboard views. Access is controlled via URL parameters and authentication.

To access a specific organization's dashboard:
- Use the URL parameter: `?org=Cityville` or `?org=Countyville`
- Enter the corresponding password when prompted

## User Guide

### Funding Scenarios Tab
Create and analyze different funding scenarios for municipal projects.

### Historical Analysis Tab
View historical budget performance and forecast future trends using the integrated forecasting tool.

### GovSight AI Assistant Tab
Ask natural language questions about budget data and get AI-powered responses and visualizations.

## Customization

### Adding New Organizations

To add a new organization:

1. Update the `config.json` file with the new organization details:
   ```json
   {
     "organizations": {
       "NewOrg": {
         "password": "your_secure_password",
         "display_name": "New Organization Name",
         "budget_ceiling": 10000000
       }
     }
   }
   ```

2. Add the organization's data to your database

### Modifying Dashboard Appearance

You can customize the application's appearance by modifying the `.streamlit/config.toml` file.

## Troubleshooting

If you encounter any issues:

1. Check the Streamlit logs for error messages
2. Verify your database connection settings
3. Ensure all required Python packages are installed
4. For database connection issues, try running `./setup_database.sh` again

## Technical Requirements

- Python 3.8 or higher
- Streamlit
- Pandas, NumPy
- Plotly for visualizations
- OpenAI API key (for AI Assistant features)
- Database connector packages depending on your database:
  - SQLite: Built-in
  - MySQL: mysql-connector-python
  - PostgreSQL: psycopg2-binary
  - MS SQL Server: pyodbc