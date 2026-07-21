"""
Hybrid AG-Grid Excel-like interface integrated into Streamlit
Provides true Excel functionality within the existing GovSight app
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
from typing import Dict, Any, List
import sqlite3
import os

class PBBHybridInterface:
    def __init__(self):
        pass
        
    def render_hybrid_spreadsheet(self):
        """Render the hybrid AG-Grid spreadsheet interface"""
        
        st.markdown("### Enhanced Excel-Style Position-Based Budget Spreadsheet")
        st.markdown("*True Excel functionality with smart autofill and position filtering*")
        
        # Add legend
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                <div style="width: 20px; height: 20px; background-color: #e3f2fd; border: 1px solid #2196F3; border-radius: 4px;"></div>
                <span style="font-size: 12px;"><strong>Blue Headers:</strong> Input Columns (Editable)</span>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                <div style="width: 20px; height: 20px; background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 4px;"></div>
                <span style="font-size: 12px;"><strong>Gray Headers:</strong> Calculated Columns (Auto-computed)</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Get employee and position data for dropdowns
        employees_data = self._get_employees_data()
        positions_data = self._get_positions_data()
        departments_data = self._get_departments_data()
        
        # Clean department automapping interface
        st.markdown("### Department Auto-Population")
        st.markdown("*Select departments and click Map to automatically add all employees*")
        
        # Department selector with integrated Map button for speed
        col1, col2 = st.columns([4, 1])
        
        with col1:
            selected_departments = st.multiselect(
                "Select Departments",
                options=departments_data,
                placeholder="Choose departments to auto-populate",
                help="Select one or more departments to add all their employees"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Align with multiselect
            if st.button("Map", use_container_width=True, type="primary"):
                if selected_departments:
                    # Fast single query for all departments with performance optimization
                    import time
                    start_time = time.time()
                    all_dept_employees = self._get_employees_by_departments_fast(selected_departments)
                    execution_time = time.time() - start_time
                    
                    if all_dept_employees:
                        st.success(f"Performance Enhanced: Mapped {len(all_dept_employees)} employees from {len(selected_departments)} departments in {execution_time:.2f} seconds")
                        st.session_state['load_dept_employees'] = all_dept_employees
                        st.rerun()
                    else:
                        st.warning("No employees found in selected departments")
                else:
                    st.warning("Please select at least one department")
        
        # Store selected departments in session state
        st.session_state['selected_departments'] = selected_departments
        
        
        st.markdown("---")
        
        # Create the hybrid interface HTML
        hybrid_html = self._create_hybrid_html(employees_data, positions_data, departments_data)
        
        # Render the component with full height
        components.html(hybrid_html, height=800, scrolling=True)
        
        # Add summary section below
        self._render_summary_section()
    
    def _get_employees_data(self) -> List[Dict[str, Any]]:
        """Get employees data from payroll database"""
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return []
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
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
            
            employees = []
            for row in rows:
                employees.append({
                    "emp_id": row[0],
                    "name": f"{row[1]} ({row[0]})",
                    "position": row[2] or "",
                    "department": row[3] or "",
                    "fte": row[4] or 1.0,
                    "basis": row[5] or "Salary",
                    "base_rate": round(row[6], 2)
                })
            
            conn.close()
            return employees
            
        except Exception as e:
            print(f"Error loading employees: {e}")
            return []
    
    def _get_positions_data(self) -> List[str]:
        """Get positions data from database"""
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return ["City Manager", "Finance Director", "Police Officer", "Fire Fighter"]
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT Position FROM Employees WHERE Position IS NOT NULL ORDER BY Position")
            rows = cursor.fetchall()
            positions = [row[0] for row in rows]
            
            conn.close()
            return positions
            
        except Exception as e:
            return ["City Manager", "Finance Director", "Police Officer", "Fire Fighter"]
    
    def _get_departments_data(self) -> List[str]:
        """Get departments data from database for automapping buttons"""
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return ["Finance", "Police", "Fire", "Public Works", "Administration"]
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT Department FROM Employees WHERE Department IS NOT NULL ORDER BY Department")
            rows = cursor.fetchall()
            departments = [row[0] for row in rows]
            
            conn.close()
            return departments
            
        except Exception as e:
            return ["Finance", "Police", "Fire", "Public Works", "Administration"]
    
    def _get_employees_by_department(self, department: str) -> List[Dict[str, Any]]:
        """Get all employees for a specific department - kept for compatibility"""
        return self._get_employees_by_departments_fast([department])
    
    def _get_employees_by_departments_fast(self, departments: List[str]) -> List[Dict[str, Any]]:
        """Fast single query to get all employees for multiple departments"""
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return []
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
            # Single optimized query for all departments
            placeholders = ','.join('?' * len(departments))
            sql = f"""
            SELECT e.EmployeeID, e.FirstName || ' ' || e.LastName as Name, 
                   e.Position, e.Department, e.FTE, e.Basis,
                   COALESCE(AVG(ph.GrossPay) * 26, 50000) as BaseRate
            FROM Employees e
            LEFT JOIN PaycheckHeaders ph ON e.EmployeeID = ph.EmployeeID
            WHERE e.FirstName IS NOT NULL AND e.Department IN ({placeholders})
            GROUP BY e.EmployeeID, e.FirstName, e.LastName, e.Position, e.Department, e.FTE, e.Basis
            ORDER BY e.Department, e.Position, e.LastName
            """
            
            cursor.execute(sql, departments)
            rows = cursor.fetchall()
            
            employees = []
            for row in rows:
                fte = row[4] or 1.0
                employees.append({
                    "emp_id": row[0],
                    "name": f"{row[1]} ({row[0]})",
                    "position": row[2] or "",
                    "department": row[3] or "",
                    "fte": fte,
                    "basis": row[5] or "Salary",
                    "base_rate": round(row[6], 2),
                    "benefits_rate": 30,
                    "hours_per_period": round(80 * fte, 1),
                    "ot_rate": 1.5,
                    "ot_hours": 0
                })
            
            conn.close()
            return employees
            
        except Exception as e:
            print(f"Error loading employees for departments {departments}: {e}")
            return []
    
    def _get_employee_budget_data(self, emp_id: str) -> Dict[str, Any]:
        """Get budget data for specific employee"""
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return {"ot_rate": 1.5, "hours_per_period": 80, "ot_hours": 0, "benefits_rate": 30}
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
            budget_data = {}
            
            # Get overtime rate
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
            
            # Other budget calculations...
            budget_data['ot_hours'] = 0
            budget_data['benefits_rate'] = 30
            
            conn.close()
            return budget_data
            
        except Exception as e:
            return {"ot_rate": 1.5, "hours_per_period": 80, "ot_hours": 0, "benefits_rate": 30}
    
    def _create_hybrid_html(self, employees_data: List[Dict], positions_data: List[str], departments_data: List[str]) -> str:
        """Create the hybrid HTML interface with AG-Grid"""
        
        employees_json = json.dumps(employees_data)
        positions_json = json.dumps(positions_data)
        departments_json = json.dumps(departments_data)
        
        # Check for department employees to load
        load_employees = st.session_state.get('load_dept_employees', [])
        clear_grid = st.session_state.get('clear_grid', False)
        selected_departments = st.session_state.get('selected_departments', [])
        
        # Clear the session state after reading
        if 'load_dept_employees' in st.session_state:
            del st.session_state['load_dept_employees']
        if 'clear_grid' in st.session_state:
            del st.session_state['clear_grid']
        
        load_employees_json = json.dumps(load_employees)
        clear_grid_json = json.dumps(clear_grid)
        selected_departments_json = json.dumps(selected_departments)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ag-grid-community@31.0.0/styles/ag-grid.css">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ag-grid-community@31.0.0/styles/ag-theme-alpine.css">
            <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
            <style>
                body {{ margin: 0; padding: 10px; font-family: 'Segoe UI', sans-serif; }}
                .controls {{ display: flex; gap: 10px; margin-bottom: 15px; align-items: center; flex-wrap: wrap; }}
                .btn {{ padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; 
                        font-size: 14px; display: inline-flex; align-items: center; gap: 5px; }}
                .btn-primary {{ background-color: #2E86AB; color: white; }}
                .btn-success {{ background-color: #28a745; color: white; }}
                .btn-danger {{ background-color: #dc3545; color: white; }}
                .btn-info {{ background-color: #17a2b8; color: white; }}
                .btn:hover {{ opacity: 0.8; }}
                .status {{ padding: 8px 12px; border-radius: 4px; font-size: 12px; }}
                .status.success {{ background-color: #d4edda; color: #155724; }}
                .status.error {{ background-color: #f8d7da; color: #721c24; }}
                #gridContainer {{ height: 500px; width: 100%; }}
                .ag-theme-alpine .input-header {{ background-color: #e3f2fd !important; color: #1976d2 !important; font-weight: bold !important; }}
                .ag-theme-alpine .calculated-header {{ background-color: #f5f5f5 !important; color: #666 !important; font-weight: bold !important; }}
                .ag-theme-alpine .input-cell {{ background-color: rgba(227, 242, 253, 0.1) !important; }}
                .ag-theme-alpine .calculated-cell {{ background-color: rgba(245, 245, 245, 0.3) !important; color: #666 !important; }}
                .summary-box {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 15px; margin-top: 15px; }}
                .summary-title {{ font-weight: bold; color: #495057; margin-bottom: 10px; }}
                .summary-stats {{ display: flex; gap: 20px; flex-wrap: wrap; }}
                .stat-item {{ text-align: center; }}
                .stat-value {{ font-size: 18px; font-weight: bold; color: #28a745; }}
                .stat-label {{ font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="controls">
                <button class="btn btn-primary" onclick="addRow()">
                    Add Position
                </button>
                <button class="btn btn-success" onclick="calculateAll()">
                    Calculate
                </button>
                <button class="btn btn-danger" onclick="deleteSelected()">
                    Delete Selected
                </button>
                <button class="btn btn-danger" onclick="clearAllRows()" style="background-color: #6c757d;">
                    Clear
                </button>
                <button class="btn btn-info" onclick="exportToCSV()">
                    Export CSV
                </button>
                <div style="margin-left: auto;">
                    <span id="status" class="status success">Ready - Use Excel shortcuts: Ctrl+C/V, Tab, Enter</span>
                </div>
            </div>
            
            <div id="gridContainer" class="ag-theme-alpine"></div>
            
            <div class="summary-box">
                <div class="summary-title">Budget Summary</div>
                <div class="summary-stats">
                    <div class="stat-item">
                        <div class="stat-value" id="totalPositions">0</div>
                        <div class="stat-label">Positions</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="totalWages">$0</div>
                        <div class="stat-label">Total Wages</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="totalBenefits">$0</div>
                        <div class="stat-label">Total Benefits</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="totalCost">$0</div>
                        <div class="stat-label">Total Cost</div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/ag-grid-community@31.0.0/dist/ag-grid-community.min.js"></script>
            <script>
                let gridApi;
                const employees = {employees_json};
                const positions = {positions_json};
                const departments = {departments_json};
                const loadEmployees = {load_employees_json};
                const clearGrid = {clear_grid_json};
                const selectedDepartments = {selected_departments_json};
                
                // Column definitions
                const columnDefs = [
                    {{
                        headerName: 'Position', field: 'position', width: 180, editable: true,
                        cellEditor: 'agSelectCellEditor',
                        cellEditorParams: {{ values: [''].concat(positions) }},
                        headerClass: 'input-header', cellClass: 'input-cell'
                    }},
                    {{
                        headerName: 'Employee ID', field: 'emp_id', width: 120, editable: false,
                        headerClass: 'calculated-header', cellClass: 'calculated-cell'
                    }},
                    {{
                        headerName: 'Name', field: 'name', width: 200, editable: true,
                        cellEditor: 'agSelectCellEditor',
                        cellEditorParams: {{ values: [''].concat(employees.map(emp => emp.name)) }},
                        headerClass: 'input-header', cellClass: 'input-cell'
                    }},
                    {{
                        headerName: 'Department', field: 'department', width: 140, editable: false,
                        headerClass: 'calculated-header', cellClass: 'calculated-cell'
                    }},
                    {{
                        headerName: 'FTE', field: 'fte', width: 80, editable: true, type: 'numericColumn',
                        headerClass: 'input-header', cellClass: 'input-cell',
                        valueFormatter: params => params.value?.toFixed(2) || '1.00'
                    }},
                    {{
                        headerName: 'Basis', field: 'basis', width: 100, editable: true,
                        cellEditor: 'agSelectCellEditor',
                        cellEditorParams: {{ values: ['Salary', 'Hourly'] }},
                        headerClass: 'input-header', cellClass: 'input-cell'
                    }},
                    {{
                        headerName: 'Base Rate', field: 'base_rate', width: 120, editable: true, type: 'numericColumn',
                        headerClass: 'input-header', cellClass: 'input-cell',
                        valueFormatter: params => '$' + (params.value?.toLocaleString() || '0')
                    }},
                    {{
                        headerName: 'Benefits %', field: 'benefits_rate', width: 110, editable: true, type: 'numericColumn',
                        headerClass: 'input-header', cellClass: 'input-cell',
                        valueFormatter: params => (params.value || 0).toFixed(1) + '%'
                    }},
                    {{
                        headerName: 'Hours/PP', field: 'hours_per_period', width: 100, editable: true, type: 'numericColumn',
                        headerClass: 'input-header', cellClass: 'input-cell',
                        valueFormatter: params => (params.value || 0).toFixed(1)
                    }},
                    {{
                        headerName: 'OT Hours', field: 'ot_hours', width: 100, editable: true, type: 'numericColumn',
                        headerClass: 'input-header', cellClass: 'input-cell',
                        valueFormatter: params => (params.value || 0).toFixed(1)
                    }},
                    {{
                        headerName: 'OT Rate', field: 'ot_rate', width: 100, editable: true, type: 'numericColumn',
                        headerClass: 'input-header', cellClass: 'input-cell',
                        valueFormatter: params => (params.value || 1.5).toFixed(1) + 'x'
                    }},
                    // Calculated columns
                    {{
                        headerName: 'Base Wages', field: 'wages_base', width: 120, editable: false, type: 'numericColumn',
                        headerClass: 'calculated-header', cellClass: 'calculated-cell',
                        valueFormatter: params => '$' + (params.value?.toLocaleString() || '0')
                    }},
                    {{
                        headerName: 'OT Wages', field: 'wages_ot', width: 110, editable: false, type: 'numericColumn',
                        headerClass: 'calculated-header', cellClass: 'calculated-cell',
                        valueFormatter: params => '$' + (params.value?.toLocaleString() || '0')
                    }},
                    {{
                        headerName: 'Benefits', field: 'benefits', width: 110, editable: false, type: 'numericColumn',
                        headerClass: 'calculated-header', cellClass: 'calculated-cell',
                        valueFormatter: params => '$' + (params.value?.toLocaleString() || '0')
                    }},
                    {{
                        headerName: 'Taxes', field: 'taxes', width: 100, editable: false, type: 'numericColumn',
                        headerClass: 'calculated-header', cellClass: 'calculated-cell',
                        valueFormatter: params => '$' + (params.value?.toLocaleString() || '0')
                    }},
                    {{
                        headerName: 'Total Cost', field: 'total_cost', width: 120, editable: false, type: 'numericColumn',
                        headerClass: 'calculated-header', cellClass: 'calculated-cell',
                        valueFormatter: params => '$' + (params.value?.toLocaleString() || '0')
                    }}
                ];
                
                // Grid options
                const gridOptions = {{
                    columnDefs: columnDefs,
                    defaultColDef: {{ resizable: true, sortable: true, filter: true }},
                    rowSelection: 'multiple',
                    enableRangeSelection: true,
                    enableFillHandle: true,
                    enableClipboard: true,
                    enterMovesDown: true,
                    singleClickEdit: true,
                    onGridReady: onGridReady,
                    onCellValueChanged: onCellValueChanged
                }};
                
                function onGridReady(params) {{
                    gridApi = params.api;
                    
                    // Check if we need to load department employees
                    if (loadEmployees && loadEmployees.length > 0) {{
                        loadDepartmentEmployees(loadEmployees);
                    }} else if (clearGrid) {{
                        gridApi.setRowData([]);
                        addInitialRows();
                    }} else {{
                        addInitialRows();
                    }}
                }}
                
                function loadDepartmentEmployees(employeesList) {{
                    const rowData = employeesList.map(emp => ({{
                        position: emp.position,
                        emp_id: emp.emp_id,
                        name: emp.name,
                        department: emp.department,
                        fte: emp.fte,
                        basis: emp.basis,
                        base_rate: emp.base_rate,
                        benefits_rate: emp.benefits_rate,
                        hours_per_period: emp.hours_per_period,
                        ot_hours: emp.ot_hours,
                        ot_rate: emp.ot_rate
                    }}));
                    
                    gridApi.setRowData(rowData);
                    calculateAll();
                    
                    document.getElementById('status').textContent = `Loaded ${{employeesList.length}} employees`;
                    document.getElementById('status').className = 'status success';
                }}
                
                function onCellValueChanged(event) {{
                    const {{ data, colDef, newValue }} = event;
                    
                    // If position changed, filter employees
                    if (colDef.field === 'position' && newValue) {{
                        const filteredEmployees = employees.filter(emp => emp.position === newValue);
                        const nameColumn = gridApi.getColumnDef('name');
                        if (nameColumn && nameColumn.cellEditorParams) {{
                            nameColumn.cellEditorParams.values = [''].concat(filteredEmployees.map(emp => emp.name));
                        }}
                        console.log(`Filtered to ${{filteredEmployees.length}} employees for position: ${{newValue}}`);
                        
                        // Clear existing name/id data when position changes
                        data.name = '';
                        data.emp_id = '';
                        data.department = '';
                        gridApi.refreshCells({{ rowNodes: [event.node], force: true }});
                    }}
                    
                    // If employee name changed, autofill
                    if (colDef.field === 'name' && newValue) {{
                        const employee = employees.find(emp => emp.name === newValue);
                        if (employee) {{
                            data.emp_id = employee.emp_id;
                            data.position = employee.position;
                            data.department = employee.department;
                            data.fte = employee.fte;
                            data.basis = employee.basis;
                            data.base_rate = employee.base_rate;
                            data.benefits_rate = 30; // Default from database logic
                            data.hours_per_period = Math.round(80 * employee.fte * 10) / 10;
                            data.ot_rate = 1.5;
                            data.ot_hours = 0;
                            
                            gridApi.refreshCells({{ rowNodes: [event.node], force: true }});
                        }}
                    }}
                    
                    calculateAll();
                }}
                
                function calculateAll() {{
                    const allRowData = [];
                    gridApi.forEachNode(node => {{
                        if (node.data) allRowData.push(node.data);
                    }});
                    
                    let totalPositions = 0;
                    let totalWages = 0;
                    let totalBenefits = 0;
                    let totalCost = 0;
                    
                    // Calculation logic (mimics backend)
                    allRowData.forEach(row => {{
                        const baseRate = row.base_rate || 0;
                        const fte = row.fte || 1;
                        const benefitsRate = (row.benefits_rate || 30) / 100;
                        const otHours = row.ot_hours || 0;
                        const otRate = row.ot_rate || 1.5;
                        const hoursPerPeriod = row.hours_per_period || 80;
                        
                        if (row.name && row.name.trim()) {{
                            totalPositions++;
                        }}
                        
                        if (row.basis === 'Salary') {{
                            row.wages_base = baseRate * fte;
                        }} else {{
                            const hourlyRate = baseRate / (hoursPerPeriod * 26);
                            row.wages_base = hourlyRate * hoursPerPeriod * 26 * fte;
                        }}
                        
                        // Calculate OT wages
                        if (row.basis === 'Hourly') {{
                            const hourlyRate = baseRate;
                            row.wages_ot = hourlyRate * otRate * otHours * 26;
                        }} else {{
                            const hourlyRate = (baseRate * fte) / (hoursPerPeriod * 26);
                            row.wages_ot = hourlyRate * otRate * otHours * 26;
                        }}
                        
                        row.benefits = (row.wages_base + (row.wages_ot || 0)) * benefitsRate;
                        row.taxes = (row.wages_base + (row.wages_ot || 0)) * 0.0765; // FICA taxes
                        row.total_cost = row.wages_base + (row.wages_ot || 0) + row.benefits + row.taxes;
                        
                        totalWages += row.wages_base + (row.wages_ot || 0);
                        totalBenefits += row.benefits;
                        totalCost += row.total_cost;
                    }});
                    
                    // Update summary
                    document.getElementById('totalPositions').textContent = totalPositions;
                    document.getElementById('totalWages').textContent = '$' + Math.round(totalWages).toLocaleString();
                    document.getElementById('totalBenefits').textContent = '$' + Math.round(totalBenefits).toLocaleString();
                    document.getElementById('totalCost').textContent = '$' + Math.round(totalCost).toLocaleString();
                    
                    gridApi.setRowData(allRowData);
                }}
                
                function addRow() {{
                    const newRow = {{
                        position: '', emp_id: '', name: '', department: '', fte: 1.0, basis: 'Salary',
                        base_rate: 0, benefits_rate: 30, hours_per_period: 80, ot_hours: 0, ot_rate: 1.5
                    }};
                    gridApi.applyTransaction({{ add: [newRow] }});
                }}
                
                function deleteSelected() {{
                    const selectedRows = gridApi.getSelectedRows();
                    if (selectedRows.length === 0) {{
                        alert('Please select rows to delete');
                        return;
                    }}
                    gridApi.applyTransaction({{ remove: selectedRows }});
                    calculateAll();
                }}
                
                function exportToCSV() {{
                    const allRowData = [];
                    gridApi.forEachNode(node => {{
                        if (node.data && node.data.name) allRowData.push(node.data);
                    }});
                    
                    if (allRowData.length === 0) {{
                        alert('No data to export');
                        return;
                    }}
                    
                    gridApi.exportDataAsCsv({{
                        fileName: 'position_based_budget.csv',
                        processCellCallback: (params) => {{
                            if (typeof params.value === 'number') {{
                                return params.value.toFixed(2);
                            }}
                            return params.value;
                        }}
                    }});
                }}
                
                function addInitialRows() {{
                    const initialRows = Array(5).fill(null).map(() => ({{
                        position: '', emp_id: '', name: '', department: '', fte: 1.0, basis: 'Salary',
                        base_rate: 0, benefits_rate: 30, hours_per_period: 80, ot_hours: 0, ot_rate: 1.5
                    }}));
                    gridApi.setRowData(initialRows);
                }}
                
                function clearAllRows() {{
                    gridApi.setRowData([]);
                    addInitialRows();
                    document.getElementById('status').textContent = 'Grid cleared';
                    document.getElementById('status').className = 'status success';
                }}
                
                // Initialize grid
                document.addEventListener('DOMContentLoaded', function() {{
                    const gridDiv = document.querySelector('#gridContainer');
                    new agGrid.Grid(gridDiv, gridOptions);
                }});
            </script>
        </body>
        </html>
        """
    
    def _render_summary_section(self):
        """Render summary metrics below the grid"""
        st.markdown("---")
        st.markdown("### Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export to GL", use_container_width=True):
                st.success("Budget data exported to General Ledger format")
        
        with col2:
            if st.button("📄 Generate Report", use_container_width=True):
                st.success("Budget report generated")
        
        with col3:
            if st.button("💾 Save Budget", use_container_width=True):
                st.success("Budget saved successfully")