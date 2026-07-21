"""
FastAPI Backend for Position-Based Budgeting System
Provides REST API endpoints for the React frontend
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os

# Add the modules path to sys.path to import our existing code
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import existing PBB logic
from modules.navi.pbb_core import PBBCore
from modules.navi.pbb_calculations import PBBCalculations
from modules.navi.payroll_live_adapter import PayrollConnectionManager
import pandas as pd
import json

app = FastAPI(title="GovSight PBB API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://0.0.0.0:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PBB components
pbb_core = PBBCore()
pbb_calculations = PBBCalculations()
payroll_manager = PayrollConnectionManager()

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

@app.get("/")
async def root():
    return {"message": "GovSight PBB API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "payroll_connected": payroll_manager.test_connection()}

@app.get("/employees", response_model=BudgetResponse)
async def get_employees():
    """Get all employees from payroll database for autofill"""
    try:
        # Get employee data using existing logic
        employees_data = []
        
        # Use the existing payroll adapter logic
        import sqlite3
        payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
        
        if os.path.exists(payroll_db_path):
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
            # Get employee data with salary information
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
        import sqlite3
        payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
        
        if not os.path.exists(payroll_db_path):
            raise HTTPException(status_code=404, detail="Payroll database not found")
        
        conn = sqlite3.connect(payroll_db_path)
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
        # Convert request to DataFrame format expected by existing calculation engine
        rows_data = []
        for row in request.rows:
            row_dict = {
                'Position': row.position or '',
                'EmpID': row.emp_id or '',
                'Name': row.name or '',
                'Department': row.department or '',
                'FTE': row.fte or 1.0,
                'Basis': row.basis or 'Salary',
                'BaseRate': row.base_rate or 0,
                'Grade': row.grade or '',
                'Step': row.step or None,
                'COLA': row.cola or 0,
                'BenefitsRate': row.benefits_rate or 30,
                'HoursPerPeriod': row.hours_per_period or 80,
                'OTHours': row.ot_hours or 0,
                'OTRate': row.ot_rate or 1.5,
                'VacancyMonths': row.vacancy_months or 0,
                'StipendAnnual': row.stipend_annual or 0,
                'BenefitsMode': row.benefits_mode or 'standard'
            }
            rows_data.append(row_dict)
        
        # Create DataFrame
        df = pd.DataFrame(rows_data)
        
        # Use existing calculation engine
        calculated_df = pbb_calculations._recalculate_all_rows(df)
        
        # Convert back to JSON-serializable format
        result_data = []
        for _, row in calculated_df.iterrows():
            row_dict = {}
            for col, value in row.items():
                if pd.isna(value):
                    row_dict[col] = None
                elif isinstance(value, (int, float)):
                    row_dict[col] = float(value) if not pd.isna(value) else None
                else:
                    row_dict[col] = str(value)
            result_data.append(row_dict)
        
        return BudgetResponse(success=True, data=result_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

@app.get("/positions")
async def get_positions():
    """Get all available positions for dropdown"""
    try:
        # Use existing positions data from PBB core
        if hasattr(pbb_core, 'positions_data') and not pbb_core.positions_data.empty:
            positions = pbb_core.positions_data['Title'].dropna().unique().tolist()
        else:
            # Fallback to basic list
            positions = ["City Manager", "Finance Director", "Assistant Finance Director", 
                        "Police Officer", "Fire Fighter", "Public Works Director"]
        
        return {"success": True, "data": positions}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching positions: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)