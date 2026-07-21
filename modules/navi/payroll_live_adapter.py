# payroll_live_adapter.py
# Live, read-through adapter for Payroll DB (SQL Server-first).
# Uses lightweight watermarks to keep Streamlit UI 'live' without manual refresh.
#
# Connection precedence:
# 1) st.secrets['payroll_db'] dict with keys: driver, server, database, username, password
# 2) environment variable PAYROLL_ODBC_DSN (full ODBC connection string)
# 3) streamlit sidebar form (if running locally)
#
# Exposed functions return (df, watermark) where watermark is the max UpdatedAt or current timestamp.

from __future__ import annotations
import os
import datetime as dt
from typing import Tuple, Optional
import pandas as pd

try:
    import streamlit as st
except Exception:
    # Allow running outside Streamlit
    class _Dummy:
        def __getattr__(self, _): return {}
    st = _Dummy()

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False

DEFAULT_TTL_SECONDS = 10

class PayrollConnection:
    def __init__(self, odbc_conn_str: Optional[str] = None):
        self._conn_str = odbc_conn_str or self._get_conn_str_from_env_or_secrets()

    def _get_conn_str_from_env_or_secrets(self) -> str:
        # Priority: st.secrets -> env -> simple DSN name
        if hasattr(st, "secrets") and "payroll_db" in getattr(st, "secrets", {}):
            s = st.secrets["payroll_db"]
            driver = s.get("driver", "{ODBC Driver 17 for SQL Server}")
            server = s.get("server")
            database = s.get("database")
            username = s.get("username")
            password = s.get("password")
            trust = s.get("trusted_connection", "no")
            if trust.lower() in ("yes", "true", "1"):
                return f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
            return f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};"
        env = os.getenv("PAYROLL_ODBC_DSN")
        if env:
            return env
        # Fallback DSN name
        return "DSN=PAYROLL_DB"

    def connect(self):
        if not PYODBC_AVAILABLE:
            raise ImportError("pyodbc is required for payroll database connections")
        return pyodbc.connect(self._conn_str, timeout=5, autocommit=True)

# ---------- Query helpers ----------

def _get_connection_type() -> str:
    """Determine which type of payroll database connection to use"""
    import os
    import sqlite3
    
    # First check if payroll has been explicitly disconnected
    try:
        import streamlit as st
        if st.session_state.get("payroll_force_disconnected", False):
            return "none"
    except:
        pass
    
    # Check for SQL Server connection configuration first
    try:
        if hasattr(st, "secrets") and hasattr(st.secrets, "_data") and "payroll_db" in st.secrets._data:
            return "sqlserver"
    except:
        pass
    
    try:
        if hasattr(st, "secrets") and "payroll_db" in st.secrets:
            return "sqlserver"
    except:
        pass
    
    if os.getenv("PAYROLL_ODBC_DSN"):
        return "sqlserver"
    
    # Then check for SQLite databases (prioritize new uploads)
    sqlite_paths = [
        "databases/payroll_city_payroll_demo (1).db",  # New uploaded database first
        "databases/payroll_city_payroll_demo.db",
        "databases/payroll.db", 
        "attached_assets/city_payroll_demo_1755893488055.db"
    ]
    
    for db_path in sqlite_paths:
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                if tables:
                    return "sqlite"
            except Exception:
                continue
    
    return "none"

def _read_sql(query: str, params: Optional[tuple] = None) -> Tuple[pd.DataFrame, Optional[pd.Timestamp]]:
    try:
        connection_type = _get_connection_type()
        
        if connection_type == "sqlite":
            # Use SQLite connection
            import sqlite3
            import os
            
            sqlite_paths = [
                "databases/payroll_city_payroll_demo (1).db",  # New uploaded database first
                "databases/payroll_city_payroll_demo.db",
                "databases/payroll.db", 
                "attached_assets/city_payroll_demo_1755893488055.db"
            ]
            
            for db_path in sqlite_paths:
                if os.path.exists(db_path):
                    try:
                        conn = sqlite3.connect(db_path)
                        df = pd.read_sql(query, conn, params=params)
                        watermark = pd.Timestamp.utcnow()
                        conn.close()
                        return df, watermark
                    except Exception as e:
                        if 'conn' in locals():
                            conn.close()
                        continue
        
        elif connection_type == "sqlserver":
            # Use SQL Server ODBC connection
            conn = PayrollConnection().connect()
            try:
                df = pd.read_sql(query, conn, params=params)
                if not df.empty and "UpdatedAt" in df.columns:
                    watermark = pd.to_datetime(df["UpdatedAt"]).max()
                else:
                    watermark = pd.Timestamp.utcnow()
                return df, watermark
            finally:
                conn.close()
        
        # If no connection available, return empty DataFrame
        return pd.DataFrame(), pd.Timestamp.utcnow()
        
    except Exception as e:
        print(f"Payroll database connection error: {e}")
        return pd.DataFrame(), pd.Timestamp.utcnow()

# ---------- Public API (views expected to exist) ----------
# You may customize schema/view names in st.secrets['payroll_db']['schema_prefix'] (e.g., 'Payroll.')

def _schema_prefix() -> str:
    """Get schema prefix for SQL Server views with safe error handling"""
    try:
        if hasattr(st, "secrets") and "payroll_db" in st.secrets:
            return st.secrets["payroll_db"].get("schema_prefix", "")
    except:
        pass
    return ""

def get_paycodes() -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Get pay codes from either SQLite tables or SQL Server views"""
    connection_type = _get_connection_type()
    
    if connection_type == "sqlite":
        # SQLite table query with column mapping
        sql = """
        SELECT 
            PayCodeID,
            Code,
            Type,
            CalcBasis,
            Multiplier,
            DefaultGL
        FROM PayCodes 
        LIMIT 100
        """
    else:
        # SQL Server view query
        sql = f"""
            SELECT PayCodeID, Code, [Type], CalcBasis, Multiplier, DefaultGL, UpdatedAt
            FROM {_schema_prefix()}vw_Payroll_PayCodes
        """
    
    return _read_sql(sql)

def get_compplan(asof: Optional[pd.Timestamp] = None) -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Get compensation plan from either SQLite tables or SQL Server views"""
    connection_type = _get_connection_type()
    
    if connection_type == "sqlite":
        # For SQLite, check if we have a compensation/salary table
        # If not available, return empty DataFrame with expected columns
        try:
            sql = "SELECT * FROM Employees LIMIT 10"  # Use employee data as fallback
            df, watermark = _read_sql(sql)
            if not df.empty:
                # Create a mock compensation plan structure from employee data
                comp_df = pd.DataFrame({
                    'PayGrade': ['Grade1', 'Grade2', 'Grade3'],
                    'Step': [1, 1, 1],
                    'AnnualRate': [45000, 55000, 65000],
                    'HourlyRate': [21.63, 26.44, 31.25],
                    'EffectiveDate': [pd.Timestamp.now().strftime('%Y-%m-%d')] * 3
                })
                return comp_df, watermark
        except:
            pass
        return pd.DataFrame(), pd.Timestamp.utcnow()
    else:
        # SQL Server view query
        sql = f"""
            SELECT PayGrade, [Step], AnnualRate, HourlyRate, EffectiveDate, UpdatedAt
            FROM {_schema_prefix()}vw_Payroll_CompPlan
        """
        return _read_sql(sql)

def get_benefit_plans(asof: Optional[pd.Timestamp] = None) -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Get benefit plans from either SQLite tables or SQL Server views"""
    connection_type = _get_connection_type()
    
    if connection_type == "sqlite":
        # SQLite table query with column mapping
        sql = """
        SELECT 
            Code as BenefitCode,
            Description as Type,
            'Percentage' as CalcBasis,
            CAST(EmployerShare as REAL) as RatePct,
            0 as Ceiling,
            CAST(EmployerShare as REAL) as EmployerSharePct,
            0 as MonthlyEmployerAmt,
            datetime('now') as EffectiveDate
        FROM BenefitPlans 
        LIMIT 100
        """
    else:
        # SQL Server view query
        sql = f"""
            SELECT BenefitCode, [Type], CalcBasis, RatePct, Ceiling, EmployerSharePct, MonthlyEmployerAmt,
                   EffectiveDate, UpdatedAt
            FROM {_schema_prefix()}vw_Payroll_BenefitPlans
        """
    
    return _read_sql(sql)

def get_positions() -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Get positions from either SQLite tables or SQL Server views"""
    connection_type = _get_connection_type()
    
    if connection_type == "sqlite":
        # SQLite table query - pull distinct positions from Employees table since that's where the actual data is
        sql = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY Position) as PositionID,
            Position as Title,
            'General' as HomeDept,
            'A1' as PayGrade,
            1 as Step,
            1.0 as FTE,
            'Active' as Status,
            'General' as HomeFund
        FROM (SELECT DISTINCT Position FROM Employees WHERE Position IS NOT NULL AND Position != '') 
        ORDER BY Position
        """
    else:
        # SQL Server view query
        sql = f"""
            SELECT PositionID, Title, PayGrade, [Step], FTE, [Status], HomeFund, HomeDept, UpdatedAt
            FROM {_schema_prefix()}vw_Payroll_Positions
        """
    
    return _read_sql(sql)

def get_allocations() -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Get position allocations from either SQLite tables or SQL Server views"""
    connection_type = _get_connection_type()
    
    if connection_type == "sqlite":
        # For SQLite, create mock allocations based on positions since this table may not exist
        try:
            positions_df, watermark = get_positions()
            if not positions_df.empty:
                # Create simple allocations - each position allocated 100% to its home department
                allocations_df = pd.DataFrame({
                    'PositionID': positions_df['PositionID'],
                    'Fund': ['General'] * len(positions_df),
                    'Department': positions_df['HomeDept'],
                    'ObjectCode': ['51000'] * len(positions_df),  # Standard personnel object code
                    'Percent': [100.0] * len(positions_df)
                })
                return allocations_df, watermark
        except:
            pass
        # Return empty DataFrame if positions not available
        return pd.DataFrame(columns=['PositionID', 'Fund', 'Department', 'ObjectCode', 'Percent']), pd.Timestamp.utcnow()
    else:
        # SQL Server view query
        sql = f"""
            SELECT PositionID, Fund, Department, ObjectCode, [Percent], UpdatedAt
            FROM {_schema_prefix()}vw_Payroll_PositionAllocations
        """
        return _read_sql(sql)

def get_position_averages() -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Get position averages for generic employee budgeting with unique IDs and dynamic benefits"""
    connection_type = _get_connection_type()
    
    if connection_type == "sqlite":
        # SQLite query to calculate position averages from payroll data
        # Using a simplified approach due to limited payroll data columns
        sql = """
        SELECT 
            e.Position,
            COUNT(DISTINCT e.EmployeeID) as employee_count,
            ROUND(AVG(ph.GrossPay * 26), 2) as avg_base_rate,  -- Annualize bi-weekly pay
            MAX(e.Department) as primary_department,
            CASE 
                WHEN COUNT(CASE WHEN e.Basis = 'Salary' THEN 1 END) >= COUNT(CASE WHEN e.Basis = 'Hourly' THEN 1 END)
                THEN 'Salary'
                ELSE 'Hourly'
            END as common_basis,
            -- Calculate dynamic benefits based on NetPay vs GrossPay difference
            ROUND(
                CASE 
                    WHEN AVG(ph.GrossPay) > 0 THEN 
                        ((AVG(ph.GrossPay) - AVG(ph.NetPay)) / AVG(ph.GrossPay)) * 100
                    ELSE 30.0
                END, 1
            ) as avg_benefits_rate,
            ROUND(MIN(ph.GrossPay * 26), 2) as min_base_rate,
            ROUND(MAX(ph.GrossPay * 26), 2) as max_base_rate,
            1 as is_generic,  -- Metadata flag
            e.Position as source_position  -- Source position tracking
        FROM Employees e
        INNER JOIN PaycheckHeaders ph ON e.EmployeeID = ph.EmployeeID
        WHERE e.Position IS NOT NULL 
            AND e.Position != '' 
            AND ph.GrossPay > 0
        GROUP BY e.Position
        ORDER BY e.Position
        """
    else:
        # SQL Server query for position averages with unique IDs and dynamic benefits
        sql = f"""
        WITH position_benefits AS (
            -- Calculate actual benefits rate per position
            SELECT 
                Position,
                AVG(CASE 
                    WHEN TotalBenefits IS NOT NULL AND BaseRate > 0 
                    THEN (TotalBenefits / BaseRate) * 100 
                    ELSE NULL 
                END) as calc_benefits_rate
            FROM {_schema_prefix()}vw_Payroll_Employees
            WHERE Position IS NOT NULL AND Position != ''
            GROUP BY Position
        )
        SELECT 
            e.Position,
            COUNT(*) as employee_count,
            ROUND(AVG(e.BaseRate), 2) as avg_base_rate,
            MAX(e.Department) as primary_department,
            CASE 
                WHEN COUNT(CASE WHEN e.Basis = 'Salary' THEN 1 END) >= COUNT(CASE WHEN e.Basis = 'Hourly' THEN 1 END)
                THEN 'Salary'
                ELSE 'Hourly'
            END as common_basis,
            -- Use calculated benefits rate if available, otherwise use average BenefitsRate field, fallback to 30%
            ROUND(COALESCE(pb.calc_benefits_rate, 
                          AVG(CASE WHEN e.BenefitsRate IS NOT NULL THEN e.BenefitsRate ELSE NULL END),
                          30.0), 1) as avg_benefits_rate,
            MIN(e.BaseRate) as min_base_rate,
            MAX(e.BaseRate) as max_base_rate,
            ROW_NUMBER() OVER (ORDER BY e.Position) + 999000 as generic_id,  -- Unique ID per position
            1 as is_generic,  -- Metadata flag
            e.Position as source_position,  -- Source position tracking
            MAX(e.UpdatedAt) as UpdatedAt
        FROM {_schema_prefix()}vw_Payroll_Employees e
        LEFT JOIN position_benefits pb ON e.Position = pb.Position
        WHERE e.Position IS NOT NULL 
            AND e.Position != '' 
            AND e.BaseRate > 0
        GROUP BY e.Position, pb.calc_benefits_rate
        ORDER BY e.Position
        """
    
    try:
        df, watermark = _read_sql(sql)
        
        # Generate unique generic IDs for each position (999001, 999002, etc.)
        if not df.empty:
            # Add generic_id column with unique IDs starting from 999001
            df['generic_id'] = range(999001, 999001 + len(df))
            # Ensure generic_id is integer type for consistent handling
            df['generic_id'] = df['generic_id'].astype(int)
        
        return df, watermark
    except Exception:
        # Return empty DataFrame if query fails
        return pd.DataFrame(columns=[
            "Position", "employee_count", "avg_base_rate", "primary_department", 
            "common_basis", "avg_benefits_rate", "min_base_rate", "max_base_rate",
            "generic_id", "is_generic", "source_position"
        ]), pd.Timestamp.utcnow()

def get_benefit_elections() -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Get benefit elections from either SQLite tables or SQL Server views"""
    connection_type = _get_connection_type()
    
    if connection_type == "sqlite":
        # SQLite table query - use EmployeeBenefitElections table if available
        try:
            sql = """
            SELECT 
                EmployeeID,
                PositionID,
                BenefitCode,
                Tier,
                EmployerMonthlyAmt
            FROM EmployeeBenefitElections 
            LIMIT 100
            """
            return _read_sql(sql)
        except:
            # Return empty DataFrame if table doesn't exist
            return pd.DataFrame(columns=[
                "EmployeeID","PositionID","BenefitCode","Tier","EmployerMonthlyAmt"
            ]), pd.Timestamp.utcnow()
    else:
        # SQL Server view query
        sql = f"""
            SELECT EmployeeID, PositionID, BenefitCode, Tier, EmployerMonthlyAmt, UpdatedAt
            FROM {_schema_prefix()}vw_Payroll_BenefitElections
        """
        try:
            return _read_sql(sql)
        except Exception:
            # Optional view; return empty
            return pd.DataFrame(columns=[
                "EmployeeID","PositionID","BenefitCode","Tier","EmployerMonthlyAmt","UpdatedAt"
            ]), pd.Timestamp.utcnow()