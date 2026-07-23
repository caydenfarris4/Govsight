"""
Standalone FastAPI Backend for Position-Based Budgeting System
Simplified version without complex dependencies
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sqlite3
import os
import pandas as pd
from datetime import datetime
import json
import sys
import numpy as np
import uuid

# Add modules to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import the enhanced dashboard API and multi-database manager
try:
    from modules.bi_sandbox.enhanced_dashboard_api import enhanced_dashboard_api
    from modules.bi_sandbox.multi_database_manager import MultiDatabaseManager
    DASHBOARD_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Dashboard API not available - {e}")
    DASHBOARD_API_AVAILABLE = False

# Import scenarios database management with renamed functions to avoid conflicts
try:
    from modules.database.scenarios_db import (
        init_scenarios_database,
        get_all_scenarios as db_get_all_scenarios,
        get_scenario as db_get_scenario,
        create_scenario as db_create_scenario,
        update_scenario as db_update_scenario,
        delete_scenario as db_delete_scenario,
        save_ai_proposal as db_save_ai_proposal,
        get_scenario_proposals as db_get_scenario_proposals
    )
    # Initialize database on startup
    init_scenarios_database()
    SCENARIOS_DB_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Scenarios database not available - {e}")
    SCENARIOS_DB_AVAILABLE = False

# Import BI Sandbox API
try:
    from modules.api.bi_sandbox_api import router as bi_sandbox_router
    BI_SANDBOX_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: BI Sandbox API not available - {e}")
    BI_SANDBOX_API_AVAILABLE = False

# Import Archive API
try:
    from modules.api.archive_api import router as archive_router
    ARCHIVE_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Archive API not available - {e}")
    ARCHIVE_API_AVAILABLE = False

# Import Authentication API
try:
    from modules.api.auth_api import router as auth_router
    AUTH_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Auth API not available - {e}")
    AUTH_API_AVAILABLE = False

# Import SSO API and database initialization
try:
    from modules.api.sso_endpoints import router as sso_router
    from modules.api.sso_database import init_sso_tables
    # Initialize SSO tables on startup (includes security backfill)
    init_sso_tables()
    SSO_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: SSO API not available - {e}")
    SSO_API_AVAILABLE = False

# Import Data Adapter API
try:
    from modules.api.data_adapter_api import router as data_adapter_router
    DATA_ADAPTER_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Data Adapter API not available - {e}")
    DATA_ADAPTER_API_AVAILABLE = False

app = FastAPI(title="GovSight Platform API", version="2.0.0")

# Load admin-configured AI keys (encrypted store) into the environment so
# every service that reads os.environ - Mantis, grants AI, data mapper -
# is live without requiring deployment env vars.
try:
    from modules.security.api_key_manager import api_key_manager as _akm
    _akm.hydrate_environment()
except Exception as _akm_err:
    print(f"API key hydration skipped: {_akm_err}")

# ── Unified platform routers ────────────────────────────────────────────────
# Session auth, Budget Playground (Node parity, /api/bp), live data bundle,
# and the Mantis chat bridge. Each is optional-imported so one missing
# dependency cannot take the whole API down.
for _router_module in ("auth", "budget_playground", "data", "mantis"):
    try:
        import importlib
        _mod = importlib.import_module(f"modules.api.routers.{_router_module}")
        app.include_router(_mod.router)
    except Exception as _router_exc:
        print(f"Router {_router_module} unavailable: {_router_exc}")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Enable CORS for React frontend and Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://0.0.0.0:3000", 
        "http://localhost:5173",
        "http://localhost:5000",  # Streamlit development
        "http://0.0.0.0:5000",     # Streamlit external access
        "https://*.replit.app",    # Replit deployment
        "https://*.repl.co",       # Alternative Replit domain
        "*"                        # Allow all origins for embedded content
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include BI Sandbox API router
if BI_SANDBOX_API_AVAILABLE:
    app.include_router(bi_sandbox_router)

# Include Archive API router
if ARCHIVE_API_AVAILABLE:
    app.include_router(archive_router)

# Include Authentication API router
if AUTH_API_AVAILABLE:
    app.include_router(auth_router)

# Include SSO API router
if SSO_API_AVAILABLE:
    app.include_router(sso_router)

# Include Data Adapter API router
if DATA_ADAPTER_API_AVAILABLE:
    app.include_router(data_adapter_router)

# Monte Carlo Simulation Models
class MonteCarloRequest(BaseModel):
    revenueMin: float
    revenueLikely: float
    revenueMax: float
    costMin: float
    costLikely: float
    costMax: float
    iterations: int = Field(default=1000, le=10000)

class MonteCarloResponse(BaseModel):
    success: bool
    distribution: List[float]
    statistics: Dict[str, float]
    netPosition: Dict[str, float]
    probability: Dict[str, float]

# Pydantic models for API requests/responses
class EmployeeData(BaseModel):
    emp_id: str
    name: str
    position: str
    department: str
    fte: float
    basis: str
    base_rate: float

class BudgetRow(BaseModel):
    position: Optional[str] = ""
    emp_id: Optional[str] = ""
    name: Optional[str] = ""
    department: Optional[str] = ""
    fte: Optional[float] = None
    basis: Optional[str] = ""
    base_rate: Optional[float] = None
    grade: Optional[str] = ""
    step: Optional[int] = None
    cola: Optional[float] = None
    benefits_rate: Optional[float] = None
    hours_per_period: Optional[float] = None
    ot_hours: Optional[float] = None
    ot_rate: Optional[float] = None
    vacancy_months: Optional[float] = None
    stipend_annual: Optional[float] = None
    benefits_mode: Optional[str] = "standard"

class BudgetResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    message: Optional[str] = None

class CalculationRequest(BaseModel):
    rows: List[BudgetRow]

# Global settings for calculations — canonical rates shared with the
# Streamlit PBB engine so both surfaces compute identical budgets
from modules.navi.payroll_rates import DEFAULT_PAYROLL_RATES
GLOBAL_SETTINGS = dict(DEFAULT_PAYROLL_RATES)

def get_db_connection():
    """Get database connection"""
    payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
    if not os.path.exists(payroll_db_path):
        raise HTTPException(status_code=404, detail="Payroll database not found")
    return sqlite3.connect(payroll_db_path)

def calculate_wages_and_benefits(row_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate wages, benefits, and taxes for a row"""
    
    # Extract values with defaults
    basis = row_data.get('basis', 'Salary') or 'Salary'
    base_rate = row_data.get('base_rate') or 0
    cola_pct = (row_data.get('cola') or 0) / 100
    benefits_rate = (row_data.get('benefits_rate') or 30) / 100
    hours_pp = row_data.get('hours_per_period') or 80
    ot_hours = row_data.get('ot_hours') or 0
    ot_rate = row_data.get('ot_rate') or 1.5
    funded_months = 12 - (row_data.get('vacancy_months') or 0)
    fte = row_data.get('fte') or 1.0
    stipend_annual = row_data.get('stipend_annual') or 0
    
    pay_periods = GLOBAL_SETTINGS['pay_periods']
    
    # Apply COLA to base rate
    base_with_cola = base_rate * (1 + cola_pct)
    
    # Calculate base wages
    if basis == 'Salary':
        wages_base = base_with_cola * (funded_months / 12) * fte
    else:
        # For hourly employees, convert annual BaseRate to hourly rate
        if base_with_cola > 0:
            annual_hours = hours_pp * pay_periods
            hourly_rate = base_with_cola / annual_hours if annual_hours > 0 else 0
        else:
            hourly_rate = 0
        wages_base = hours_pp * hourly_rate * pay_periods * (funded_months / 12) * fte
    
    # Calculate overtime
    if basis == 'Salary':
        hourly_equivalent = base_with_cola / (hours_pp * pay_periods) if hours_pp > 0 else 0
        wages_ot = ot_hours * hourly_equivalent * ot_rate * pay_periods * (funded_months / 12) * fte if ot_hours else 0
    else:
        if base_with_cola > 0:
            annual_hours = hours_pp * pay_periods
            hourly_rate = base_with_cola / annual_hours if annual_hours > 0 else 0
        else:
            hourly_rate = 0
        wages_ot = ot_hours * hourly_rate * ot_rate * pay_periods * (funded_months / 12) * fte if ot_hours else 0
    
    # Calculate stipends
    stipends = stipend_annual * (funded_months / 12) * fte
    
    # Calculate benefits
    total_wages = wages_base + wages_ot + stipends
    benefits = benefits_rate * total_wages
    
    # Calculate taxes
    fica_tax = min(total_wages, GLOBAL_SETTINGS['fica_wage_base']) * GLOBAL_SETTINGS['fica_pct']
    medicare_tax = total_wages * GLOBAL_SETTINGS['medicare_pct']
    retirement_tax = total_wages * GLOBAL_SETTINGS['retirement_pct']
    unemployment_tax = min(total_wages, GLOBAL_SETTINGS['unemployment_base']) * GLOBAL_SETTINGS['unemployment_pct']
    workers_comp_tax = total_wages * GLOBAL_SETTINGS['workers_comp_pct']
    total_taxes = fica_tax + medicare_tax + retirement_tax + unemployment_tax + workers_comp_tax
    
    # Total cost
    total_cost = wages_base + wages_ot + stipends + benefits + total_taxes
    
    # Annual cost
    annual_cost = total_cost * (12 / funded_months) if funded_months > 0 else 0
    
    # Effective rate calculation
    if basis == 'Hourly':
        total_hours = (hours_pp + ot_hours) * pay_periods * (funded_months / 12) * fte
        effective_rate = total_cost / total_hours if total_hours > 0 else 0
    else:
        total_hours = hours_pp * pay_periods * (funded_months / 12) * fte
        effective_rate = total_cost / total_hours if total_hours > 0 else 0
    
    return {
        'FundedMonths': round(funded_months, 2),
        'BaseWithCOLA': round(base_with_cola, 2),
        'WagesBase': round(wages_base, 2),
        'WagesOT': round(wages_ot, 2),
        'Stipends': round(stipends, 2),
        'Benefits': round(benefits, 2),
        'Taxes': round(total_taxes, 2),
        'TotalCost': round(total_cost, 2),
        'AnnualCost': round(annual_cost, 2),
        'EffectiveRate': round(effective_rate, 2)
    }

@app.get("/", include_in_schema=False)
async def root():
    # Serve the SPA at the root when it has been built; the API health
    # message remains the fallback for API-only deployments.
    index = os.path.join("frontend", "dist", "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "GovSight PBB API is running"}

@app.get("/health")
async def health_check():
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "payroll_connected": True}
    except:
        return {"status": "healthy", "payroll_connected": False}

@app.get("/health/databases")
async def database_health_check():
    """
    Comprehensive database health check endpoint for all 5 municipal databases.
    Returns actual connection status, driver availability, and schema information.
    """
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from modules.database.connection_manager import (
        load_db_config, test_connection, get_available_databases
    )
    from modules.bi_sandbox.multi_database_manager import MultiDatabaseManager
    
    try:
        # Check driver availability
        driver_status = {
            "psycopg2": False,
            "mysql_connector": False, 
            "pyodbc": False
        }
        
        try:
            import psycopg2
            driver_status["psycopg2"] = True
        except ImportError:
            pass
            
        try:
            import mysql.connector
            driver_status["mysql_connector"] = True
        except ImportError:
            pass
            
        try:
            import pyodbc
            driver_status["pyodbc"] = True
        except ImportError:
            pass
        
        # Initialize multi-database manager to ensure sample databases exist
        multi_db_manager = MultiDatabaseManager()
        
        # Get database configuration
        db_config = load_db_config()
        database_status = {}
        
        total_tables = 0
        total_connections = 0
        
        # Test each database connection
        for db_name, db_info in db_config.get("databases", {}).items():
            status_info = {
                "display_name": db_info.get("display_name", db_name),
                "description": db_info.get("description", ""),
                "type": db_info.get("type", "sqlite"),
                "connection_status": "not_connected",
                "driver_available": False,
                "connection_test": None,
                "schema_info": {
                    "tables_count": 0,
                    "sample_tables": [],
                    "discovery_timestamp": None
                },
                "error": None
            }
            
            # Check if required driver is available
            db_type = db_info.get("type", "sqlite")
            if db_type == "sqlite":
                status_info["driver_available"] = True
            elif db_type == "postgres":
                status_info["driver_available"] = driver_status["psycopg2"]
            elif db_type == "mysql":
                status_info["driver_available"] = driver_status["mysql_connector"]
            elif db_type == "sqlserver":
                status_info["driver_available"] = driver_status["pyodbc"]
            
            # Test actual connection
            try:
                connection_test = test_connection(db_name)
                status_info["connection_test"] = connection_test
                
                if connection_test.get("success", False):
                    status_info["connection_status"] = "connected"
                    total_connections += 1
                    
                    # Get schema information
                    try:
                        schemas = multi_db_manager.discover_database_schemas()
                        if db_name in schemas:
                            db_schema = schemas[db_name]
                            if "tables" in db_schema:
                                tables_count = len(db_schema["tables"])
                                status_info["schema_info"]["tables_count"] = tables_count
                                status_info["schema_info"]["sample_tables"] = list(db_schema["tables"].keys())[:5]
                                status_info["schema_info"]["discovery_timestamp"] = datetime.now().isoformat()
                                total_tables += tables_count
                    except Exception as schema_error:
                        status_info["schema_info"]["error"] = str(schema_error)
                        
                else:
                    status_info["connection_status"] = "failed"
                    status_info["error"] = connection_test.get("error", "Connection failed")
                    
            except Exception as e:
                status_info["connection_status"] = "error"
                status_info["error"] = str(e)
            
            database_status[db_name] = status_info
        
        # Calculate overall health
        all_connected = total_connections == len(database_status)
        
        health_response = {
            "status": "healthy" if all_connected else "partial",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_databases": len(database_status),
                "connected_databases": total_connections,
                "total_tables_discovered": total_tables,
                "all_drivers_available": all(driver_status.values()),
                "overall_health": "excellent" if all_connected and total_tables > 20 else "good" if total_connections >= 3 else "needs_attention"
            },
            "drivers": driver_status,
            "databases": database_status,
            "verification": {
                "phase3_requirements_met": all_connected and total_tables >= 20,
                "schema_catalog_available": total_tables > 0,
                "multi_database_integration": total_connections >= 3
            }
        }
        
        return health_response
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "summary": {
                "total_databases": 0,
                "connected_databases": 0, 
                "total_tables_discovered": 0,
                "overall_health": "critical_error"
            }
        }

@app.get("/employees", response_model=BudgetResponse)
async def get_employees(position: Optional[str] = None):
    """Get all employees from payroll database for autofill, optionally filtered by position"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get employee data with salary information, optionally filtered by position
        if position:
            sql = """
            SELECT e.EmployeeID, e.FirstName || ' ' || e.LastName as Name, 
                   e.Position, e.Department, e.FTE, e.Basis,
                   COALESCE(AVG(ph.GrossPay) * 26, 0) as BaseRate
            FROM Employees e
            LEFT JOIN PaycheckHeaders ph ON e.EmployeeID = ph.EmployeeID
            WHERE e.FirstName IS NOT NULL AND e.Position = ?
            GROUP BY e.EmployeeID, e.FirstName, e.LastName, e.Position, e.Department, e.FTE, e.Basis
            """
            cursor.execute(sql, (position,))
        else:
            sql = """
            SELECT e.EmployeeID, e.FirstName || ' ' || e.LastName as Name, 
                   e.Position, e.Department, e.FTE, e.Basis,
                   COALESCE(AVG(ph.GrossPay) * 26, 0) as BaseRate
            FROM Employees e
            LEFT JOIN PaycheckHeaders ph ON e.EmployeeID = ph.EmployeeID
            WHERE e.FirstName IS NOT NULL
            GROUP BY e.EmployeeID, e.FirstName, e.LastName, e.Position, e.Department, e.FTE, e.Basis
            """
            cursor.execute(sql)
        
        rows = cursor.fetchall()
        
        employees_data = []
        for row in rows:
            employees_data.append({
                "emp_id": row[0],
                "name": f"{row[1]} ({row[0]})",
                "position": row[2] or "",
                "department": row[3] or "",
                "fte": row[4] or 1.0,
                "basis": row[5] or "Salary",
                "base_rate": round(row[6], 2)
            })
        
        conn.close()
        return BudgetResponse(success=True, data=employees_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching employees: {str(e)}")

@app.get("/employee/{emp_id}/budget-data")
async def get_employee_budget_data(emp_id: str):
    """Get autofill budget data for a specific employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        budget_data = {}
        
        # Get overtime rate from PayCodes
        try:
            cursor.execute("SELECT Multiplier FROM PayCodes WHERE Type = 'Overtime' AND Code = 'OT1'")
            ot_rate_row = cursor.fetchone()
            budget_data['ot_rate'] = float(ot_rate_row[0]) if ot_rate_row else 1.5
        except:
            budget_data['ot_rate'] = 1.5
        
        # Calculate Hours/PP based on FTE
        try:
            cursor.execute("SELECT FTE FROM Employees WHERE EmployeeID = ?", (emp_id,))
            fte_row = cursor.fetchone()
            if fte_row and fte_row[0]:
                fte = float(fte_row[0])
                budget_data['hours_per_period'] = round(80 * fte, 1)
            else:
                budget_data['hours_per_period'] = 80
        except:
            budget_data['hours_per_period'] = 80
        
        # Estimate OT hours from paycheck history
        try:
            cursor.execute("""
                SELECT AVG(CASE WHEN ph.RegularPay > 0 
                    THEN (ph.GrossPay - ph.RegularPay) / ph.RegularPay * ? 
                    ELSE 0 END) as AvgOTHours
                FROM PaycheckHeaders ph 
                WHERE ph.EmployeeID = ? AND ph.GrossPay > 0
                LIMIT 12
            """, (budget_data.get('hours_per_period', 80), emp_id))
            ot_hours_row = cursor.fetchone()
            if ot_hours_row and ot_hours_row[0]:
                estimated_ot = max(0, min(20, ot_hours_row[0]))
                budget_data['ot_hours'] = round(estimated_ot, 1)
            else:
                budget_data['ot_hours'] = 0
        except:
            budget_data['ot_hours'] = 0
        
        # Calculate Benefits% from BenefitPlans
        try:
            cursor.execute("""
                SELECT SUM(bp.MonthlyEmployerAmt) as MonthlyBenefits
                FROM BenefitPlans bp 
                WHERE bp.Type IN ('LifeSingle', 'HealthSingle', 'HealthES')
            """)
            benefits_row = cursor.fetchone()
            if benefits_row and benefits_row[0]:
                monthly_benefits = float(benefits_row[0])
                # Get employee's monthly gross
                cursor.execute("""
                    SELECT AVG(ph.GrossPay) * 2 as MonthlyGross 
                    FROM PaycheckHeaders ph 
                    WHERE ph.EmployeeID = ? AND ph.GrossPay > 0
                    LIMIT 6
                """, (emp_id,))
                gross_row = cursor.fetchone()
                if gross_row and gross_row[0] and gross_row[0] > 0:
                    benefits_pct = (monthly_benefits / gross_row[0]) * 100
                    budget_data['benefits_rate'] = round(min(50, max(10, benefits_pct)), 1)
                else:
                    budget_data['benefits_rate'] = 30
            else:
                budget_data['benefits_rate'] = 30
        except:
            budget_data['benefits_rate'] = 30
        
        conn.close()
        return budget_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching budget data: {str(e)}")

@app.post("/calculate", response_model=BudgetResponse)
async def calculate_budget(request: CalculationRequest):
    """Calculate budget totals for all rows"""
    try:
        result_data = []
        
        for row in request.rows:
            # Convert row to dictionary
            row_dict = {
                'position': row.position or '',
                'emp_id': row.emp_id or '',
                'name': row.name or '',
                'department': row.department or '',
                'fte': row.fte or 1.0,
                'basis': row.basis or 'Salary',
                'base_rate': row.base_rate or 0,
                'grade': row.grade or '',
                'step': row.step or None,
                'cola': row.cola or 0,
                'benefits_rate': row.benefits_rate or 30,
                'hours_per_period': row.hours_per_period or 80,
                'ot_hours': row.ot_hours or 0,
                'ot_rate': row.ot_rate or 1.5,
                'vacancy_months': row.vacancy_months or 0,
                'stipend_annual': row.stipend_annual or 0,
                'benefits_mode': row.benefits_mode or 'standard'
            }
            
            # Calculate financial totals
            calculated = calculate_wages_and_benefits(row_dict)
            
            # Merge input and calculated data
            result_row = {**row_dict, **calculated}
            
            # Convert field names to match frontend expectations
            frontend_row = {
                'position': result_row['position'],
                'emp_id': result_row['emp_id'],
                'name': result_row['name'],
                'department': result_row['department'],
                'fte': result_row['fte'],
                'basis': result_row['basis'],
                'base_rate': result_row['base_rate'],
                'grade': result_row['grade'],
                'step': result_row['step'],
                'cola': result_row['cola'],
                'benefits_rate': result_row['benefits_rate'],
                'hours_per_period': result_row['hours_per_period'],
                'ot_hours': result_row['ot_hours'],
                'ot_rate': result_row['ot_rate'],
                'vacancy_months': result_row['vacancy_months'],
                'stipend_annual': result_row['stipend_annual'],
                'benefits_mode': result_row['benefits_mode'],
                'funded_months': result_row['FundedMonths'],
                'base_with_cola': result_row['BaseWithCOLA'],
                'wages_base': result_row['WagesBase'],
                'wages_ot': result_row['WagesOT'],
                'stipends': result_row['Stipends'],
                'benefits': result_row['Benefits'],
                'taxes': result_row['Taxes'],
                'total_cost': result_row['TotalCost'],
                'annual_cost': result_row['AnnualCost'],
                'effective_rate': result_row['EffectiveRate']
            }
            
            result_data.append(frontend_row)
        
        return BudgetResponse(success=True, data=result_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

@app.get("/positions")
async def get_positions():
    """Get all available positions for dropdown"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT Position FROM Employees WHERE Position IS NOT NULL ORDER BY Position")
        rows = cursor.fetchall()
        positions = [row[0] for row in rows]
        
        conn.close()
        return {"success": True, "data": positions}
    
    except Exception as e:
        # Fallback to basic list
        positions = ["City Manager", "Finance Director", "Assistant Finance Director", 
                    "Police Officer", "Fire Fighter", "Public Works Director"]
        return {"success": True, "data": positions}

# BI Dashboard Schema API Endpoints
@app.get("/api/schema/catalog")
async def get_schema_catalog():
    """
    Get unified schema catalog for BI Dashboard field tree.
    Returns all database schemas in hierarchical format for drag-and-drop functionality.
    """
    if not DASHBOARD_API_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Dashboard API not available - missing dependencies"
        )
    
    try:
        # Get multi-database schema from enhanced dashboard API
        schema_data = enhanced_dashboard_api.get_multi_database_schema()
        
        return schema_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving schema catalog: {str(e)}"
        )

@app.get("/api/schema/database/{database_name}")
async def get_database_schema(database_name: str):
    """Get schema for a specific database."""
    if not DASHBOARD_API_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Dashboard API not available - missing dependencies"
        )
    
    try:
        # Get all schemas first
        all_schemas = enhanced_dashboard_api.get_multi_database_schema()
        
        if not all_schemas.get("success", False):
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve database schemas"
            )
        
        # Find the specific database
        schemas = all_schemas.get("schemas", {})
        if database_name not in schemas:
            raise HTTPException(
                status_code=404,
                detail=f"Database '{database_name}' not found"
            )
        
        return {
            "success": True,
            "database": database_name,
            "schema": schemas[database_name],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving schema for database {database_name}: {str(e)}"
        )

@app.get("/api/schema/field-suggestions/{widget_type}")
async def get_field_suggestions(widget_type: str):
    """Get field suggestions for specific visualization types (bar_chart, line_chart, pie_chart, table)."""
    if not DASHBOARD_API_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Dashboard API not available - missing dependencies"
        )
    
    try:
        suggestions = enhanced_dashboard_api.get_database_field_suggestions(widget_type)
        return suggestions
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting field suggestions for {widget_type}: {str(e)}"
        )

@app.get("/api/test/database-connections")  
async def test_database_connections():
    """Test connections to all configured databases."""
    if not DASHBOARD_API_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Dashboard API not available - missing dependencies"
        )
    
    try:
        connection_results = enhanced_dashboard_api.test_database_connections()
        return connection_results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error testing database connections: {str(e)}"
        )

# ============== Scenario Planner API Endpoints ==============

# Pydantic models for Scenario Planner - made flexible for different input formats
class FundingSource(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = ""
    type: str  # 'tax', 'grant', 'bond', 'private', 'other'
    description: Optional[str] = ""
    amount: float
    recurring: Optional[bool] = False

class DepartmentAllocation(BaseModel):
    name: str
    currentBudget: Optional[float] = 0
    proposedBudget: Optional[float] = 0
    allocation: Optional[float] = 0  # Alternative field name
    percentageChange: Optional[float] = 0
    priority: Optional[str] = "medium"

class SimulationAssumptions(BaseModel):
    revenueMin: Optional[float] = 0
    revenueLikely: Optional[float] = 0
    revenueMax: Optional[float] = 0
    costVolatility: Optional[float] = 0.1
    iterations: Optional[int] = 1000
    inflationRate: Optional[float] = 3.0
    growthRate: Optional[float] = 2.5
    riskTolerance: Optional[str] = "moderate"

class Scenario(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    years: int
    costs: List[float]
    fundingSources: List[FundingSource]
    departments: List[DepartmentAllocation]
    assumptions: SimulationAssumptions
    createdAt: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())
    modifiedAt: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())

class MonteCarloParams(BaseModel):
    revenueMin: float
    revenueLikely: float
    revenueMax: float
    costMin: float
    costLikely: float
    costMax: float
    iterations: int = Field(default=1000, le=10000)

class LegislativeImpactParams(BaseModel):
    category: str
    projectCost: float
    legislativeText: Optional[str] = ""
    timeHorizon: str = "3-5 Years"

class BillLookupParams(BaseModel):
    billNumber: str
    level: str = "federal"
    state: Optional[str] = None
    congress: Optional[int] = None
    annualBudget: float = 5000000

class WhatIfQuery(BaseModel):
    query: str

# Removed in-memory storage - now using database
# scenarios_storage is now handled by scenarios_db module

@app.get("/api/scenarios")
async def get_scenarios():
    """Get all scenarios from database"""
    if not SCENARIOS_DB_AVAILABLE:
        # Fallback to empty response if database not available
        return {"scenarios": [], "count": 0}
    
    try:
        scenarios = db_get_all_scenarios()
        # Convert snake_case to camelCase for frontend compatibility
        for scenario in scenarios:
            if 'funding_sources' in scenario:
                scenario['fundingSources'] = scenario.pop('funding_sources')
            if 'created_at' in scenario:
                scenario['createdAt'] = scenario.pop('created_at')
            if 'modified_at' in scenario:
                scenario['modifiedAt'] = scenario.pop('modified_at')
            if 'created_by' in scenario:
                scenario['createdBy'] = scenario.pop('created_by')
        
        return {
            "scenarios": scenarios,
            "count": len(scenarios)
        }
    except Exception as e:
        print(f"Error getting scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scenarios")
async def create_scenario(scenario: Scenario):
    """Create a new scenario in database"""
    if not SCENARIOS_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        # Convert Pydantic model to dict for database
        scenario_dict = scenario.dict()
        
        # Create scenario in database
        scenario_id = db_create_scenario(scenario_dict)
        
        return {
            "success": True, 
            "id": scenario_id, 
            "scenario": scenario_dict,
            "message": "Scenario saved successfully to database"
        }
    except Exception as e:
        print(f"Error creating scenario: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save scenario: {str(e)}")

@app.get("/api/scenarios/{scenario_id}")
async def get_scenario_by_id(scenario_id: str):
    """Get a specific scenario from database"""
    if not SCENARIOS_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        scenario = db_get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Convert snake_case to camelCase for frontend
        if 'funding_sources' in scenario:
            scenario['fundingSources'] = scenario.pop('funding_sources')
        if 'created_at' in scenario:
            scenario['createdAt'] = scenario.pop('created_at')
        if 'modified_at' in scenario:
            scenario['modifiedAt'] = scenario.pop('modified_at')
        
        return scenario
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/scenarios/{scenario_id}")
async def update_scenario_by_id(scenario_id: str, scenario: Scenario):
    """Update an existing scenario in database"""
    if not SCENARIOS_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        # Convert Pydantic model to dict
        scenario_dict = scenario.dict()
        scenario_dict['modifiedAt'] = datetime.now().isoformat()
        
        # Update in database
        success = db_update_scenario(scenario_id, scenario_dict)
        if not success:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        return {
            "success": True, 
            "scenario": scenario_dict,
            "message": "Scenario updated successfully in database"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating scenario: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update scenario: {str(e)}")

@app.delete("/api/scenarios/{scenario_id}")
async def delete_scenario_by_id(scenario_id: str):
    """Delete a scenario from database"""
    if not SCENARIOS_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        success = db_delete_scenario(scenario_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        return {
            "success": True, 
            "message": "Scenario deleted successfully from database"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting scenario: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete scenario: {str(e)}")

@app.get("/api/departments")
async def get_departments():
    """Get list of departments with budget data"""
    try:
        # Try to get from the main database
        db_path = "databases/core/govsight_all_in_one_data.db"
        if not os.path.exists(db_path):
            # Fallback to sample data
            return {
                "departments": [
                    {"name": "Police", "budget": 5000000},
                    {"name": "Fire", "budget": 4500000},
                    {"name": "Public Works", "budget": 3000000},
                    {"name": "Parks & Recreation", "budget": 2000000},
                    {"name": "Administration", "budget": 1500000},
                    {"name": "Finance", "budget": 1000000},
                    {"name": "Planning", "budget": 800000},
                    {"name": "Library", "budget": 600000}
                ]
            }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Try to get department budget data
        cursor.execute("""
            SELECT Department, SUM(Budget) as TotalBudget
            FROM budget_data
            GROUP BY Department
            ORDER BY TotalBudget DESC
        """)
        
        departments = []
        for row in cursor.fetchall():
            departments.append({
                "name": row[0],
                "budget": row[1]
            })
        
        conn.close()
        return {"departments": departments}
        
    except Exception as e:
        # Return sample data on error
        return {
            "departments": [
                {"name": "Police", "budget": 5000000},
                {"name": "Fire", "budget": 4500000},
                {"name": "Public Works", "budget": 3000000},
                {"name": "Parks & Recreation", "budget": 2000000},
                {"name": "Administration", "budget": 1500000}
            ]
        }

@app.post("/api/monte-carlo/run")
async def run_monte_carlo(params: MonteCarloParams):
    """Run Monte Carlo simulation with proper revenue and cost distributions"""
    try:
        # Set random seed for reproducibility in testing
        np.random.seed(None)  # Use None for random results in production
        
        # Triangular distribution for revenue
        revenue_samples = np.random.triangular(
            params.revenueMin,
            params.revenueLikely,
            params.revenueMax,
            params.iterations
        )
        
        # Triangular distribution for costs
        cost_samples = np.random.triangular(
            params.costMin,
            params.costLikely,
            params.costMax,
            params.iterations
        )
        
        # Calculate net position (revenue - costs)
        net_positions = revenue_samples - cost_samples
        
        # Calculate statistics for net positions
        mean_net = np.mean(net_positions)
        std_net = np.std(net_positions)
        
        # Calculate percentiles
        percentiles = np.percentile(net_positions, [5, 25, 50, 75, 95])
        
        # Calculate probability of profit
        prob_profit = np.sum(net_positions > 0) / params.iterations * 100
        prob_loss = np.sum(net_positions < 0) / params.iterations * 100
        
        # Create histogram data
        hist, bins = np.histogram(net_positions, bins=30)
        
        return {
            "success": True,
            "distribution": [float(x) for x in net_positions[:100]],  # Return sample for visualization
            "histogram": {
                "bins": [float((bins[i] + bins[i + 1]) / 2) for i in range(len(hist))],
                "frequencies": [int(x) for x in hist]
            },
            "statistics": {
                "mean": float(mean_net),
                "stdDev": float(std_net),
                "min": float(np.min(net_positions)),
                "max": float(np.max(net_positions))
            },
            "netPosition": {
                "revenue": {
                    "mean": float(np.mean(revenue_samples)),
                    "min": float(np.min(revenue_samples)),
                    "max": float(np.max(revenue_samples))
                },
                "cost": {
                    "mean": float(np.mean(cost_samples)),
                    "min": float(np.min(cost_samples)),
                    "max": float(np.max(cost_samples))
                },
                "net": {
                    "mean": float(mean_net),
                    "p5": float(percentiles[0]),
                    "p25": float(percentiles[1]),
                    "p50": float(percentiles[2]),
                    "p75": float(percentiles[3]),
                    "p95": float(percentiles[4])
                }
            },
            "probability": {
                "profit": float(prob_profit),
                "loss": float(prob_loss),
                "breakeven": float(100 - prob_profit - prob_loss)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")

@app.post("/api/ai/legislative-impact")
async def analyze_legislative_impact(params: LegislativeImpactParams):
    """Analyze legislative impact using AI"""
    try:
        compliance_score = np.random.randint(60, 95)
        additional_cost = params.projectCost * np.random.uniform(0.05, 0.20)
        
        return {
            "success": True,
            "complianceScore": compliance_score,
            "summary": f"Based on {params.category} requirements, your project shows {compliance_score}% compliance.",
            "findings": [
                f"Project must comply with {params.category} standards",
                f"Time horizon of {params.timeHorizon} allows for phased implementation",
                "Additional documentation required for regulatory approval",
                "Environmental impact assessment recommended"
            ],
            "recommendations": [
                "Allocate budget for compliance documentation",
                "Consider hiring regulatory consultant",
                "Plan for quarterly compliance reviews",
                "Build in 10-15% contingency for regulatory changes"
            ],
            "estimatedCost": additional_cost,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@app.post("/api/ai/bill-lookup")
async def lookup_bill(params: BillLookupParams):
    """Look up a bill by number from Congress.gov or state legislature"""
    if not params.billNumber or not params.billNumber.strip():
        raise HTTPException(status_code=400, detail="Bill number is required")
    
    if params.level == "state" and not params.state:
        raise HTTPException(status_code=400, detail="State is required for state bill lookups")
    
    try:
        from modules.scenario_planner.bill_lookup_service import (
            parse_bill_number, lookup_federal_bill, lookup_state_bill,
            get_bill_financial_keywords, US_STATES
        )
        
        bill_type, bill_number, bill_congress = parse_bill_number(params.billNumber)
        
        if not bill_number:
            return {"success": True, "data": {"found": False, "error": "Could not parse bill number. Use format: HR 1234, S 567, HB 100"}}
        
        if params.level == "federal":
            congress = params.congress or bill_congress
            bill_data = lookup_federal_bill(bill_type, bill_number, congress)
        else:
            state_code = US_STATES.get(params.state, params.state or "")
            bill_data = lookup_state_bill(state_code, bill_type, bill_number)
        
        if bill_data.get("found"):
            financial_keywords = get_bill_financial_keywords(bill_data)
            bill_data["financial_keywords"] = financial_keywords
            
            bill_title = bill_data.get("title", "Unknown")
            bill_summary = bill_data.get("summary", "")[:2500]
            bill_id = f"{bill_data.get('bill_type', '').upper()} {bill_data.get('bill_number', '')}"
            status = bill_data.get("status", "Unknown")
            policy_area = bill_data.get("policy_area", "General")
            source_label = "Federal" if bill_data.get("source") == "federal" else bill_data.get("state_name", "State")
            
            prompt = f"""You are a municipal financial analyst. Analyze the following {source_label} legislation 
and project its financial impact on a municipality with an annual budget of ${params.annualBudget:,.0f}.

BILL: {bill_id}
TITLE: {bill_title}
STATUS: {status}
POLICY AREA: {policy_area}
IDENTIFIED IMPACT AREAS: {', '.join(financial_keywords)}

BILL SUMMARY/TEXT:
{bill_summary}

Provide a structured analysis covering:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. FINANCIAL IMPACT PROJECTION (estimated annual cost/savings, one-time costs, revenue impact, % of budget affected)
3. AFFECTED DEPARTMENTS (which departments and estimated budget impact)
4. IMPLEMENTATION TIMELINE
5. COMPLIANCE REQUIREMENTS (new reporting, staffing, technology needs)
6. RISK ASSESSMENT (probability of passage, financial risk level)
7. RECOMMENDED ACTIONS (immediate steps, budget planning, advocacy)

Be specific with dollar estimates relative to the ${params.annualBudget:,.0f} budget."""

            try:
                from modules.ai_hub.ai_hub import ask_ai
                ai_analysis = ask_ai(
                    prompt=prompt,
                    sources=[f"Legislative analysis: {bill_id}", "Municipal budget impact"],
                    max_tokens=1500
                )
            except Exception as e:
                ai_analysis = f"AI analysis unavailable: {str(e)}. Review the bill details for manual assessment."
            
            bill_data["impact_analysis"] = ai_analysis
        
        return {"success": True, "data": bill_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bill lookup error: {str(e)}")

@app.post("/api/ai/bill-search")
async def search_bills(query: str = "", level: str = "federal", state: str = None):
    """Search for bills by keyword"""
    try:
        from modules.scenario_planner.bill_lookup_service import search_bills_by_keyword, US_STATES
        
        state_code = US_STATES.get(state, state) if state else None
        results = search_bills_by_keyword(query, level, state_code)
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/api/ai/whatif-analysis")
async def analyze_whatif(query_obj: WhatIfQuery):
    """
    Analyze complex multi-factor what-if scenarios using GL data + AI reasoning.
    Returns factors[], three scenario branches (optimistic/expected/worst), and
    matched GL accounts. No random numbers — all outputs are deterministic and
    grounded in either real GL data or a representative fallback dataset.
    """
    import sqlite3 as _sqlite3
    import os as _os

    query_raw = query_obj.query
    ql = query_raw.lower()

    # ── 1. Load GL accounts for context ───────────────────────────────────────
    gl_revenue, gl_expense = [], []
    db_candidates = [
        _os.path.join(_os.path.dirname(__file__), '..', '..', 'databases', 'core', 'govsight_all_in_one_data.db'),
    ]
    for db_path in db_candidates:
        if not _os.path.exists(db_path):
            continue
        try:
            conn = _sqlite3.connect(db_path, timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT account_number, account_name, account_type, department, budget_amount, ytd_actual FROM gl_accounts")
            for row in cur.fetchall():
                num, name, atype, dept, budget, actual = row
                entry = {'number': num or '', 'name': name or '', 'department': dept or '', 'budget': budget or 0, 'actual': actual or 0}
                if (atype or '').lower() == 'revenue':
                    gl_revenue.append(entry)
                elif (atype or '').lower() == 'expense':
                    gl_expense.append(entry)
            conn.close()
            break
        except Exception:
            pass

    total_revenue = sum(a['budget'] for a in gl_revenue) or 12800000  # fallback
    total_expense = sum(a['budget'] for a in gl_expense) or 11000000

    # ── 2. Multi-factor extraction ─────────────────────────────────────────────
    import re as _re

    # Magnitude extraction
    pct_matches = _re.findall(r'(\d+\.?\d*)\s*%', ql)
    dollar_matches = _re.findall(r'\$\s*([\d,]+\.?\d*)\s*(k|m|million|thousand)?', ql, _re.I)

    def parse_dollar(m):
        val = float(m[0].replace(',', ''))
        u = m[1].lower() if len(m) > 1 else ''
        if u in ('k', 'thousand'): val *= 1000
        if u in ('m', 'million'):  val *= 1000000
        return val

    pcts = [float(p) for p in pct_matches]
    dollars = [parse_dollar(m) for m in dollar_matches]

    # Keyword classifiers — grouped by factor type to prevent misclassification.
    # Direction is determined by the CONTEXT keywords rather than a generic increase/decrease
    # search, which is what caused "accounting for 8%" to be misread as a positive event.
    DISASTER_KW   = r'burns?\s+down|destroy|fire|flood|disaster|collapse|explosion|earthquake|catastroph|loss|lost|gone'
    REMOVE_KW     = r"won'?t\s+need|no\s+longer|eliminat|remov|saves?\s+us|save\s+on|discontinu|shut\s+down|clos"
    CLEANUP_KW    = r'cleanup|clean.up|remediat|demolit|rebuild|haul\s+away|debris|decontaminat|restor|repair\s+cost'
    REVENUE_KW    = r'revenue|income|receiv|earns?|generat|contribut|account\s+for|utility|fund|tax'
    EXPENSE_KW    = r'expense|cost|maintain|mainten|operat|server|staff|employ|salary|utilities'
    HIRE_KW       = r'hire|new\s+(firefighter|officer|employee|staff|worker)'
    INCREASE_KW   = r'\b(increase|raise|add|boost|grow)\b'
    DECREASE_KW   = r'\b(cut|reduc|decreas|slash|lower|trim)\b'

    is_disaster   = bool(_re.search(DISASTER_KW, ql))
    is_remove_exp = bool(_re.search(REMOVE_KW, ql))
    is_cleanup    = bool(_re.search(CLEANUP_KW, ql))
    is_hire       = bool(_re.search(HIRE_KW, ql))
    has_revenue   = bool(_re.search(REVENUE_KW, ql))
    has_expense   = bool(_re.search(EXPENSE_KW, ql))
    is_increase   = bool(_re.search(INCREASE_KW, ql)) and not is_disaster
    is_decrease   = bool(_re.search(DECREASE_KW, ql)) and not is_disaster

    # ── GL account keyword matching ────────────────────────────────────────────
    def match_accounts(accounts, keywords):
        kws = [w for w in keywords if len(w) > 3]
        matched = [a for a in accounts if any(kw in a['name'].lower() or kw in a['department'].lower() for kw in kws)]
        return matched[:5]

    query_words = _re.findall(r'[a-z]+', ql)
    matched_rev  = match_accounts(gl_revenue, query_words)
    matched_exp  = match_accounts(gl_expense, query_words)

    # ── 3. Compute factor list ─────────────────────────────────────────────────
    factors = []

    # Factor A — revenue loss from disaster
    if is_disaster and has_revenue and pcts:
        rev_pct  = pcts[0]
        rev_loss = total_revenue * (rev_pct / 100)
        factors.append({
            'type': 'revenue_loss',
            'label': f'Revenue loss ({rev_pct:.1f}% of total revenue)',
            'annualImpact': -rev_loss,
            'pct': rev_pct,
            'matchedAccounts': matched_rev or [],
        })

    # Factor B — expense elimination (ongoing savings)
    if (is_remove_exp or is_disaster) and has_expense:
        if dollars:
            exp_saved = dollars[0]
        elif matched_exp:
            exp_saved = sum(a['budget'] for a in matched_exp[:3]) * 0.8
        else:
            exp_saved = total_expense * 0.02  # default 2% when ambiguous
        factors.append({
            'type': 'expense_removed',
            'label': 'Ongoing expense elimination (no longer maintaining asset)',
            'annualImpact': exp_saved,
            'dollar': exp_saved,
            'matchedAccounts': matched_exp or [],
        })

    # Factor C — one-time cleanup / remediation costs
    # A dollar amount is "consumed" if any prior factor already claimed it via the
    # 'dollar' key.  Only reuse the stated amount for cleanup when it wasn't already
    # spoken for — otherwise estimate as 2.5× the revenue loss (matching the HTML parser).
    if is_cleanup or is_disaster:
        dollar_consumed = any(f.get('dollar') for f in factors)
        if len(dollars) >= 2:
            cleanup = dollars[1]
        elif dollars and not dollar_consumed:
            cleanup = dollars[0]
        else:
            rev_factor = next((f for f in factors if f['type'] == 'revenue_loss'), None)
            cleanup = (abs(rev_factor['annualImpact']) * 2.5) if rev_factor else 200000
        factors.append({
            'type': 'onetime_cost',
            'label': 'One-time cleanup / remediation costs',
            'annualImpact': 0,
            'onetimeCost': abs(cleanup),
            'matchedAccounts': [],
        })

    # Factor D — simple budget increase / decrease (when no disaster)
    if not factors and pcts:
        direction = -1 if is_decrease else 1
        impact = total_expense * (pcts[0] / 100) * direction
        factors.append({
            'type': 'budget_change',
            'label': f'Budget {"increase" if direction > 0 else "reduction"} ({pcts[0]:.1f}%)',
            'annualImpact': impact,
            'pct': pcts[0],
            'matchedAccounts': (matched_rev if direction > 0 else matched_exp) or [],
        })

    # Factor E — hiring
    hire_match = _re.search(r'(\d+)\s+new\s+\w+', ql)
    if is_hire and hire_match:
        count = int(hire_match.group(1))
        cost  = count * 72000
        factors.append({
            'type': 'expense_added',
            'label': f'New hire compensation ({count} positions × $72,000 avg total comp)',
            'annualImpact': -cost,
            'dollar': cost,
            'matchedAccounts': [],
        })

    # Fallback — return something even for totally unrecognised queries
    if not factors:
        factors.append({
            'type': 'unknown',
            'label': 'Scenario could not be fully parsed. Review the factor breakdown.',
            'annualImpact': 0,
            'matchedAccounts': [],
        })

    # ── 4. Three-branch computation ────────────────────────────────────────────
    def compute_branch(factor_overrides):
        annual_net = 0
        onetime    = 0
        for f, ov in zip(factors, factor_overrides):
            annual_net += f.get('annualImpact', 0) * ov.get('impact_mult', 1)
            onetime    += f.get('onetimeCost', 0)  * ov.get('onetime_mult', 1)
        return {'annualNet': round(annual_net, 2), 'onetimeCost': round(onetime, 2)}

    # Overrides: each entry matches position in factors[]
    n = len(factors)
    opt_overrides   = [{'impact_mult': 0.7,  'onetime_mult': 0.5}] * n
    exp_overrides   = [{'impact_mult': 1.0,  'onetime_mult': 1.0}] * n
    worst_overrides = [{'impact_mult': 1.3,  'onetime_mult': 2.0}] * n

    optimistic = compute_branch(opt_overrides)
    expected   = compute_branch(exp_overrides)
    worst_case = compute_branch(worst_overrides)

    net_annual = expected['annualNet']
    net_pct    = net_annual / total_revenue if total_revenue else 0

    # ── 5. Build a plain-English summary ──────────────────────────────────────
    factor_desc = '; '.join(f['label'] for f in factors)
    interpretation = (
        f"This scenario involves {len(factors)} financial factor(s): {factor_desc}. "
        f"Expected net annual impact: ${net_annual:+,.0f} ({net_pct*100:+.1f}% of total revenue). "
        f"Worst case includes ${worst_case['onetimeCost']:,.0f} in one-time remediation costs."
        if factors else "Unable to extract specific financial factors from this scenario description."
    )

    # ── 6. Try AI enrichment (graceful fallback if unavailable) ───────────────
    try:
        from modules.ai_hub.ai_hub import ask_ai
        gl_context = '; '.join(f"{a['name']} (${a['budget']:,.0f} budget)" for a in (matched_rev + matched_exp)[:6])
        ai_prompt = (
            f"Municipal finance what-if scenario: \"{query_raw}\"\n"
            f"Matched GL accounts: {gl_context or 'none identified'}\n"
            f"Total municipal revenue: ${total_revenue:,.0f}\n"
            f"Extracted factors: {factor_desc}\n"
            f"Expected net annual impact: ${net_annual:+,.0f}\n\n"
            f"Provide a 3-4 sentence professional assessment of the financial risk and recommended actions for a municipal finance director. "
            f"Include any additional factors or second-order effects not captured by the mechanical analysis."
        )
        ai_text = ask_ai(prompt=ai_prompt, sources=["GL accounts", "Municipal finance"], max_tokens=400)
        interpretation = interpretation + "\n\n" + ai_text
    except Exception:
        pass

    # Chart: current vs expected vs worst annual net positions per factor
    chart_labels = [f['label'][:30] + ('...' if len(f['label']) > 30 else '') for f in factors]
    chart_current  = [0.0] * len(factors)
    chart_expected = [round(f.get('annualImpact', 0), 2) for f in factors]
    chart_worst    = [round(f.get('annualImpact', 0) * 1.3, 2) for f in factors]

    return {
        "success": True,
        "interpretation": interpretation,
        "totalImpact": net_annual,
        "percentageChange": net_pct,
        "affectedDepartments": len(set(a['department'] for f in factors for a in f.get('matchedAccounts', []))),
        "factors": factors,
        "scenarios": {
            "optimistic": optimistic,
            "expected":   expected,
            "worstCase":  worst_case,
        },
        "matchedRevenueAccounts": matched_rev,
        "matchedExpenseAccounts": matched_exp,
        "chartData": {
            "labels":   chart_labels or ['No factors'],
            "current":  chart_current or [0],
            "proposed": chart_expected or [0],
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/grants/search")
async def search_grants(q: str = Query(..., description="Search query for grants")):
    """Search for available grants via live federal sources (grants.gov,
    Simpler.Grants.gov, USASpending). Returns an honest empty result with
    is_live=false when the live search is unavailable — no fabricated
    sample grants."""
    try:
        from modules.external_data.grants_api import get_grants_api
        results = get_grants_api().search_all_grants(keywords=q)
        grants = [{
            "id": g.get("id") or g.get("url", ""),
            "name": g.get("title", ""),
            "agency": g.get("agency", ""),
            "description": g.get("description", "")[:400],
            "min_amount": g.get("min_amount", 0),
            "max_amount": g.get("max_amount", 0),
            "amount": g.get("max_amount", 0),
            "deadline": str(g.get("deadline", ""))[:10],
            "source": g.get("source", ""),
            "url": g.get("url", ""),
        } for g in results]

        return {
            "success": True,
            "query": q,
            "grants": grants,
            "count": len(grants),
            "is_live": bool(grants),
            "message": None if grants else (
                "Live grant search returned no results (the federal APIs may be "
                "unreachable from this deployment). No sample grants are substituted.")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET PLAYGROUND — Dynamic Re-Forecasting & Scenario Modeling
# ══════════════════════════════════════════════════════════════════════════════
# These endpoints power the Budget Playground tab in Navi. Unlike PBB (which
# models payroll by position), the Playground covers all Revenue + non-payroll
# Expense accounts — the kind of lines you re-forecast mid-year when a
# development comes in hot, impact fees shift, or a department submits a
# supplemental request.

import uuid as _uuid_module

BP_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'databases', 'budget_playground.db')
GL_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'databases', 'core', 'govsight_all_in_one_data.db')

def _bp_connect():
    conn = sqlite3.connect(BP_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_bp_db():
    conn = _bp_connect()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS bp_scenarios (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            fiscal_year INTEGER NOT NULL DEFAULT 2025,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            is_locked   INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS bp_scenario_lines (
            id              TEXT PRIMARY KEY,
            scenario_id     TEXT NOT NULL,
            account_number  TEXT NOT NULL,
            revised_budget  REAL,
            forecast_yr2    REAL,
            forecast_yr3    REAL,
            note            TEXT DEFAULT '',
            updated_at      TEXT NOT NULL,
            UNIQUE(scenario_id, account_number)
        );
        CREATE TABLE IF NOT EXISTS bp_supplementals (
            id              TEXT PRIMARY KEY,
            scenario_id     TEXT NOT NULL,
            account_number  TEXT,
            department      TEXT,
            category        TEXT NOT NULL DEFAULT 'Supplemental',
            amount          REAL NOT NULL DEFAULT 0,
            justification   TEXT DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            submitted_at    TEXT NOT NULL,
            reviewed_at     TEXT
        );
    """)
    conn.commit()
    # Seed a default scenario if none exist
    cur.execute("SELECT COUNT(*) FROM bp_scenarios")
    if cur.fetchone()[0] == 0:
        _seed_default_scenario(cur, conn)
    conn.close()

def _is_payroll_account(acct_number: str) -> bool:
    import re
    return bool(re.search(r'-(5100|5200)$', str(acct_number or '')))

def _get_nonpayroll_accounts():
    rows = []
    try:
        conn = sqlite3.connect(GL_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT account_number, account_name, account_type, department, fund,
                   budget_amount, ytd_actual
            FROM gl_accounts
            ORDER BY account_type DESC, department, account_number
        """)
        rows = [dict(r) for r in cur.fetchall() if not _is_payroll_account(r['account_number'])]
        conn.close()
    except Exception as e:
        print(f"Budget Playground: GL DB error: {e}")
    return rows

def _seed_default_scenario(cur, conn):
    sid  = str(_uuid_module.uuid4())
    now  = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO bp_scenarios (id,name,description,fiscal_year,created_at,updated_at,is_locked) VALUES (?,?,?,2025,?,?,0)",
        (sid, 'Adopted Budget FY 2025', 'Original adopted budget', now, now)
    )
    accounts = _get_nonpayroll_accounts()
    for a in accounts:
        cur.execute(
            "INSERT INTO bp_scenario_lines (id,scenario_id,account_number,revised_budget,forecast_yr2,forecast_yr3,note,updated_at) VALUES (?,?,?,?,?,?,'',?)",
            (str(_uuid_module.uuid4()), sid, a['account_number'], a['budget_amount'], a['budget_amount'], a['budget_amount'], now)
        )
    conn.commit()

# Initialize on import
try:
    _init_bp_db()
except Exception as _e:
    print(f"Budget Playground DB init warning: {_e}")

# ── Pydantic models ────────────────────────────────────────────────────────────

class BPScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = ''
    fiscal_year: Optional[int] = 2025
    copy_from_id: Optional[str] = None

class BPScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_locked: Optional[int] = None

class BPLineItem(BaseModel):
    account_number: str
    revised_budget: Optional[float] = None
    forecast_yr2: Optional[float] = None
    forecast_yr3: Optional[float] = None
    note: Optional[str] = ''

class BPSupplementalCreate(BaseModel):
    scenario_id: str
    account_number: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = 'Supplemental'
    amount: float
    justification: Optional[str] = ''

class BPSupplementalUpdate(BaseModel):
    status: Optional[str] = None
    amount: Optional[float] = None
    justification: Optional[str] = None

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/api/budget-playground/accounts")
async def bp_get_accounts():
    accounts = _get_nonpayroll_accounts()
    return accounts

@app.get("/api/budget-playground/scenarios")
async def bp_list_scenarios():
    conn = _bp_connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM bp_scenarios ORDER BY created_at ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/api/budget-playground/scenarios", status_code=201)
async def bp_create_scenario(body: BPScenarioCreate):
    conn = _bp_connect()
    cur  = conn.cursor()
    sid  = str(_uuid_module.uuid4())
    now  = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO bp_scenarios (id,name,description,fiscal_year,created_at,updated_at,is_locked) VALUES (?,?,?,?,?,?,0)",
        (sid, body.name, body.description or '', body.fiscal_year or 2025, now, now)
    )
    if body.copy_from_id:
        source_lines = cur.execute(
            "SELECT * FROM bp_scenario_lines WHERE scenario_id=?", (body.copy_from_id,)
        ).fetchall()
        for sl in source_lines:
            cur.execute(
                "INSERT INTO bp_scenario_lines (id,scenario_id,account_number,revised_budget,forecast_yr2,forecast_yr3,note,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (str(_uuid_module.uuid4()), sid, sl['account_number'], sl['revised_budget'], sl['forecast_yr2'], sl['forecast_yr3'], sl['note'] or '', now)
            )
    else:
        accounts = _get_nonpayroll_accounts()
        for a in accounts:
            cur.execute(
                "INSERT INTO bp_scenario_lines (id,scenario_id,account_number,revised_budget,forecast_yr2,forecast_yr3,note,updated_at) VALUES (?,?,?,?,?,?,'',?)",
                (str(_uuid_module.uuid4()), sid, a['account_number'], a['budget_amount'], a['budget_amount'], a['budget_amount'], now)
            )
    conn.commit()
    result = dict(cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (sid,)).fetchone())
    conn.close()
    return result

@app.get("/api/budget-playground/scenarios/{scenario_id}")
async def bp_get_scenario(scenario_id: str):
    conn = _bp_connect()
    cur  = conn.cursor()
    row  = cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (scenario_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario  = dict(row)
    lines_raw = cur.execute("SELECT * FROM bp_scenario_lines WHERE scenario_id=?", (scenario_id,)).fetchall()
    conn.close()
    line_map  = {l['account_number']: dict(l) for l in lines_raw}
    accounts  = _get_nonpayroll_accounts()
    merged = []
    for a in accounts:
        line = line_map.get(a['account_number'])
        merged.append({
            **a,
            'revised_budget': line['revised_budget'] if line else a['budget_amount'],
            'forecast_yr2':   line['forecast_yr2']   if line else a['budget_amount'],
            'forecast_yr3':   line['forecast_yr3']   if line else a['budget_amount'],
            'note':           line['note']            if line else '',
            'has_override':   line is not None,
        })
    scenario['lines'] = merged
    return scenario

@app.put("/api/budget-playground/scenarios/{scenario_id}")
async def bp_update_scenario(scenario_id: str, body: BPScenarioUpdate):
    conn = _bp_connect()
    cur  = conn.cursor()
    row  = cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (scenario_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Scenario not found")
    now  = datetime.now().isoformat()
    cur.execute(
        "UPDATE bp_scenarios SET name=COALESCE(?,name), description=COALESCE(?,description), is_locked=COALESCE(?,is_locked), updated_at=? WHERE id=?",
        (body.name, body.description, body.is_locked, now, scenario_id)
    )
    conn.commit()
    result = dict(cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (scenario_id,)).fetchone())
    conn.close()
    return result

@app.delete("/api/budget-playground/scenarios/{scenario_id}")
async def bp_delete_scenario(scenario_id: str):
    conn = _bp_connect()
    cur  = conn.cursor()
    row  = cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (scenario_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Not found")
    if row['is_locked']:
        conn.close()
        raise HTTPException(status_code=403, detail="Scenario is locked and cannot be deleted")
    cur.execute("DELETE FROM bp_scenario_lines WHERE scenario_id=?", (scenario_id,))
    cur.execute("DELETE FROM bp_scenarios WHERE id=?", (scenario_id,))
    conn.commit()
    conn.close()
    return {"deleted": scenario_id}

@app.put("/api/budget-playground/scenarios/{scenario_id}/lines")
async def bp_upsert_lines(scenario_id: str, lines: List[BPLineItem]):
    conn = _bp_connect()
    cur  = conn.cursor()
    row  = cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (scenario_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Scenario not found")
    if row['is_locked']:
        conn.close()
        raise HTTPException(status_code=403, detail="Scenario is locked")
    now = datetime.now().isoformat()
    for line in lines:
        cur.execute("""
            INSERT INTO bp_scenario_lines (id,scenario_id,account_number,revised_budget,forecast_yr2,forecast_yr3,note,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(scenario_id,account_number) DO UPDATE SET
                revised_budget=excluded.revised_budget,
                forecast_yr2=excluded.forecast_yr2,
                forecast_yr3=excluded.forecast_yr3,
                note=excluded.note,
                updated_at=excluded.updated_at
        """, (str(_uuid_module.uuid4()), scenario_id, line.account_number,
              line.revised_budget, line.forecast_yr2, line.forecast_yr3,
              line.note or '', now))
    conn.commit()
    conn.close()
    return {"saved": len(lines)}

from fastapi.responses import StreamingResponse
import io

@app.get("/api/budget-playground/scenarios/{scenario_id}/export.csv")
async def bp_export_csv(scenario_id: str):
    conn = _bp_connect()
    cur  = conn.cursor()
    row  = cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (scenario_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Not found")
    scenario  = dict(row)
    lines_raw = cur.execute("SELECT * FROM bp_scenario_lines WHERE scenario_id=?", (scenario_id,)).fetchall()
    conn.close()
    line_map  = {l['account_number']: dict(l) for l in lines_raw}
    accounts  = _get_nonpayroll_accounts()

    output = io.StringIO()
    output.write("Account #,Account Name,Department,Type,Adopted Budget,Revised Budget,Variance,% Variance,Yr+1 Forecast,Yr+2 Forecast,Note\n")
    for a in accounts:
        line    = line_map.get(a['account_number'], {})
        adopted = a['budget_amount'] or 0
        revised = line.get('revised_budget', adopted) or 0
        var     = revised - adopted
        var_pct = f"{(var/adopted*100):.1f}%" if adopted else "0%"
        yr2     = line.get('forecast_yr2', adopted) or 0
        yr3     = line.get('forecast_yr3', adopted) or 0
        note    = (line.get('note') or '').replace('"', "'")
        output.write(f'{a["account_number"]},"{a["account_name"]}",{a["department"]},{a["account_type"]},{adopted:.2f},{revised:.2f},{var:.2f},{var_pct},{yr2:.2f},{yr3:.2f},"{note}"\n')

    filename = f"budget_playground_{scenario['fiscal_year']}_{scenario['name'].replace(' ','_')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/budget-playground/supplementals")
async def bp_list_supplementals(scenario_id: Optional[str] = None):
    conn = _bp_connect()
    cur  = conn.cursor()
    if scenario_id:
        rows = cur.execute("SELECT * FROM bp_supplementals WHERE scenario_id=? ORDER BY submitted_at DESC", (scenario_id,)).fetchall()
    else:
        rows = cur.execute("SELECT * FROM bp_supplementals ORDER BY submitted_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/budget-playground/supplementals", status_code=201)
async def bp_create_supplemental(body: BPSupplementalCreate):
    conn = _bp_connect()
    cur  = conn.cursor()
    sid  = str(_uuid_module.uuid4())
    now  = datetime.now().isoformat()
    cur.execute(
        "INSERT INTO bp_supplementals (id,scenario_id,account_number,department,category,amount,justification,status,submitted_at) VALUES (?,?,?,?,?,?,?,'pending',?)",
        (sid, body.scenario_id, body.account_number, body.department, body.category or 'Supplemental', body.amount, body.justification or '', now)
    )
    conn.commit()
    result = dict(cur.execute("SELECT * FROM bp_supplementals WHERE id=?", (sid,)).fetchone())
    conn.close()
    return result

@app.put("/api/budget-playground/supplementals/{sup_id}")
async def bp_update_supplemental(sup_id: str, body: BPSupplementalUpdate):
    conn = _bp_connect()
    cur  = conn.cursor()
    now  = datetime.now().isoformat()
    reviewed = now if body.status in ('approved', 'denied') else None
    cur.execute(
        "UPDATE bp_supplementals SET status=COALESCE(?,status), amount=COALESCE(?,amount), justification=COALESCE(?,justification), reviewed_at=COALESCE(?,reviewed_at) WHERE id=?",
        (body.status, body.amount, body.justification, reviewed, sup_id)
    )
    conn.commit()
    row = cur.execute("SELECT * FROM bp_supplementals WHERE id=?", (sup_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(row)

@app.delete("/api/budget-playground/supplementals/{sup_id}")
async def bp_delete_supplemental(sup_id: str):
    conn = _bp_connect()
    cur  = conn.cursor()
    cur.execute("DELETE FROM bp_supplementals WHERE id=?", (sup_id,))
    conn.commit()
    conn.close()
    return {"deleted": sup_id}

@app.post("/api/budget-playground/scenarios/{scenario_id}/apply-supplementals")
async def bp_apply_supplementals(scenario_id: str):
    conn = _bp_connect()
    cur  = conn.cursor()
    row  = cur.execute("SELECT * FROM bp_scenarios WHERE id=?", (scenario_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Not found")
    if row['is_locked']:
        conn.close()
        raise HTTPException(status_code=403, detail="Scenario is locked")
    approved = cur.execute(
        "SELECT * FROM bp_supplementals WHERE scenario_id=? AND status='approved'", (scenario_id,)
    ).fetchall()
    now = datetime.now().isoformat()
    count = 0
    for s in approved:
        cur.execute("""
            INSERT INTO bp_scenario_lines (id,scenario_id,account_number,revised_budget,forecast_yr2,forecast_yr3,note,updated_at)
            VALUES (?,?,?,?,?,?,'[Supplemental applied]',?)
            ON CONFLICT(scenario_id,account_number) DO UPDATE SET
                revised_budget=revised_budget + excluded.revised_budget,
                note=note||' [Supplemental applied]',
                updated_at=excluded.updated_at
        """, (str(_uuid_module.uuid4()), scenario_id, s['account_number'], s['amount'], 0, 0, now))
        count += 1
    conn.commit()
    conn.close()
    return {"applied": count}

# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Investment rates and portfolio tracking
# ─────────────────────────────────────────────────────────────────────────────

class HoldingRequest(BaseModel):
    instrument_type: str
    description: str
    principal: float
    rate: float
    purchase_date: str
    maturity_date: Optional[str] = None
    fund: Optional[str] = ""
    notes: Optional[str] = ""


@app.get("/api/investment/rates")
def get_investment_rates():
    """Aggregated investment opportunities with per-rate freshness flags."""
    try:
        from modules.financial_data.investment_aggregator import get_investment_aggregator
        return get_investment_aggregator().get_all_opportunities()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rate aggregation error: {e}")


@app.get("/api/portfolio")
def list_portfolio(include_inactive: bool = False):
    from modules.financial_data.portfolio_manager import get_portfolio_manager
    return {"holdings": get_portfolio_manager().list_holdings(include_inactive)}


@app.post("/api/portfolio")
def add_portfolio_holding(holding: HoldingRequest):
    from modules.financial_data.portfolio_manager import get_portfolio_manager
    holding_id = get_portfolio_manager().add_holding(holding.dict())
    return {"id": holding_id}


@app.put("/api/portfolio/{holding_id}")
def update_portfolio_holding(holding_id: int, data: Dict[str, Any]):
    from modules.financial_data.portfolio_manager import get_portfolio_manager
    get_portfolio_manager().update_holding(holding_id, data)
    return {"ok": True}


@app.delete("/api/portfolio/{holding_id}")
def delete_portfolio_holding(holding_id: int):
    from modules.financial_data.portfolio_manager import get_portfolio_manager
    get_portfolio_manager().delete_holding(holding_id)
    return {"ok": True}


@app.get("/api/portfolio/analytics")
def portfolio_analytics(idle_cash: float = 0.0, benchmark_rate: Optional[float] = None):
    from modules.financial_data.portfolio_manager import get_portfolio_manager
    return get_portfolio_manager().analytics(idle_cash=idle_cash,
                                             benchmark_rate=benchmark_rate)



# ── SPA serving ─────────────────────────────────────────────────────────────
# Serves the built React frontend (frontend/dist) with an index.html
# fallback for client-side routes. API routes above always win.
from fastapi.responses import FileResponse
from fastapi import Request as _Request

_FRONTEND_DIST = os.path.join("frontend", "dist")


@app.get("/{spa_path:path}", include_in_schema=False)
def serve_spa(spa_path: str):
    if spa_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = os.path.normpath(os.path.join(_FRONTEND_DIST, spa_path))
    if not candidate.startswith(os.path.normpath(_FRONTEND_DIST)):
        raise HTTPException(status_code=404, detail="Not found")
    if spa_path and os.path.isfile(candidate):
        return FileResponse(candidate)
    index = os.path.join(_FRONTEND_DIST, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return {"detail": "Frontend not built. Run: cd frontend && npm run build"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)