# PBB Core - Data Loading and Basic Setup
# Position-Based Budgeting core functionality (~500 lines)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Any
import plotly.express as px
from modules.navi.payroll_live_adapter import _get_connection_type, _read_sql, get_positions
import os
import json

class PBBCore:
    """Core Position-Based Budgeting functionality - data loading and setup"""
    
    def __init__(self):
        self.global_settings = self._get_default_settings()
        self.budget_year = self._get_budget_year()
        self.employees_data = self._load_employees_data()
        self.positions_data = self._load_positions_data()
        
    def _get_default_settings(self) -> Dict[str, Any]:
        """Default global settings for calculations"""
        from modules.navi.payroll_rates import DEFAULT_PAYROLL_RATES
        current_year = date.today().year
        return {
            'year_start': date(current_year, 1, 1),
            'year_end': date(current_year, 12, 31),
            **DEFAULT_PAYROLL_RATES,
        }
    
    def _load_employees_data(self) -> pd.DataFrame:
        """Load employee data from payroll database or create mock data"""
        connection_type = _get_connection_type()
        
        if connection_type == "sqlite":
            # SQLite query - adapted for actual database structure (only existing columns)
            sql = f"""
            SELECT e.EmployeeID as EmpID,
                   (e.FirstName || ' ' || e.LastName) as Name,
                   e.FirstName,
                   e.LastName,
                   e.Position as PositionTitle,
                   e.Department,
                   'A1' as Grade,
                   '1' as Step,
                   e.Basis,
                   CASE 
                     WHEN e.Position LIKE '%Manager%' OR e.Position LIKE '%Director%' THEN 75000
                     WHEN e.Position LIKE '%Assistant%' OR e.Position LIKE '%Deputy%' THEN 55000
                     WHEN e.Position LIKE '%Supervisor%' THEN 65000
                     WHEN e.Position LIKE '%Officer%' OR e.Position LIKE '%Specialist%' THEN 45000
                     ELSE 40000 
                   END as BaseRate,
                   80 as HoursPerPeriod,
                   e.FTE
            FROM Employees e
            WHERE e.EmployeeID IS NOT NULL
            ORDER BY e.LastName, e.FirstName
            """
        else:
            # SQL Server query
            sql = """
            SELECT e.EmployeeID as EmpID,
                   e.FirstName + ' ' + e.LastName + ' (' + e.EmployeeID + ')' as Display,
                   CASE WHEN p.RateType = 'Salary' THEN 'Salary' ELSE 'Hourly' END as Basis,
                   CASE WHEN p.RateType = 'Salary' THEN p.Rate ELSE 0 END as AnnualSalary,
                   CASE WHEN p.RateType = 'Hourly' THEN p.Rate ELSE 0 END as HourlyRate,
                   COALESCE(pos.PayGrade, '') as Grade,
                   COALESCE(pos.Step, 1) as Step,
                   80 as HoursPP,
                   0 as OTHoursPP,
                   900 as BenefitsMonthly
            FROM vw_Payroll_Employees e
            LEFT JOIN vw_Payroll_Paycodes p ON e.EmployeeID = p.EmployeeID
            LEFT JOIN vw_Payroll_Positions pos ON e.PositionID = pos.PositionID
            WHERE e.EmployeeID IS NOT NULL
            ORDER BY e.LastName, e.FirstName
            """
        
        try:
            df, _ = _read_sql(sql, ())
            if df.empty:
                return self._create_mock_employees()
            return df
        except Exception as e:
            st.warning(f"Could not load employee data: {e}. Using mock data.")
            return self._create_mock_employees()
    
    def _create_mock_employees(self) -> pd.DataFrame:
        """Create mock employee data for demonstration"""
        mock_data = []
        for i in range(1, 51):
            emp_id = f"E{i:04d}"
            basis = "Salary" if i % 3 != 0 else "Hourly"
            annual = 55000 + (i % 10) * 2500 if basis == "Salary" else 0
            hourly = 0 if basis == "Salary" else 18 + (i % 12) * 1.5
            grade = f"G{10 + (i % 8)}"
            step = 1 + (i % 5)
            hours_pp = 80 if basis == "Hourly" else 0
            ot_hours_pp = 2 if basis == "Hourly" else 0
            benefits_monthly = 900 if i % 4 != 0 else 0
            display = f"{emp_id} - Employee {i} ({emp_id})"
            
            mock_data.append({
                'EmpID': emp_id,
                'Display': display,
                'Basis': basis,
                'AnnualSalary': annual,
                'HourlyRate': hourly,
                'Grade': grade,
                'Step': step,
                'HoursPP': hours_pp,
                'OTHoursPP': ot_hours_pp,
                'BenefitsMonthly': benefits_monthly
            })
        
        return pd.DataFrame(mock_data)
    
    def _load_positions_data(self) -> pd.DataFrame:
        """Load position data from database or create mock data"""
        try:
            positions, _ = get_positions()  # Unpack tuple - get_positions returns (DataFrame, Timestamp)
            if positions is not None and not positions.empty:
                return positions
        except Exception as e:
            st.warning(f"Could not load positions data: {e}. Using mock data.")
        
        # Create mock positions data
        mock_positions = [
            {'Title': 'City Manager', 'HomeDept': 'Administration', 'PayGrade': 'E5', 'FTE': 1.0, 'PositionID': 'P001'},
            {'Title': 'Finance Director', 'HomeDept': 'Finance', 'PayGrade': 'E4', 'FTE': 1.0, 'PositionID': 'P002'},
            {'Title': 'Public Works Director', 'HomeDept': 'Public Works', 'PayGrade': 'E4', 'FTE': 1.0, 'PositionID': 'P003'},
            {'Title': 'Police Chief', 'HomeDept': 'Police', 'PayGrade': 'E4', 'FTE': 1.0, 'PositionID': 'P004'},
            {'Title': 'Fire Chief', 'HomeDept': 'Fire', 'PayGrade': 'E4', 'FTE': 1.0, 'PositionID': 'P005'},
            {'Title': 'Administrative Assistant', 'HomeDept': 'Administration', 'PayGrade': 'A2', 'FTE': 1.0, 'PositionID': 'P006'},
            {'Title': 'Accountant', 'HomeDept': 'Finance', 'PayGrade': 'B3', 'FTE': 1.0, 'PositionID': 'P007'},
            {'Title': 'Librarian', 'HomeDept': 'Library', 'PayGrade': 'B2', 'FTE': 1.0, 'PositionID': 'P008'},
            {'Title': 'Library Assistant', 'HomeDept': 'Library', 'PayGrade': 'A1', 'FTE': 0.5, 'PositionID': 'P009'},
            {'Title': 'Maintenance Worker', 'HomeDept': 'Public Works', 'PayGrade': 'A3', 'FTE': 1.0, 'PositionID': 'P010'},
        ]
        
        return pd.DataFrame(mock_positions)
    
    def _get_budget_year(self) -> int:
        """Get the budget year from session state or current year"""
        return st.session_state.get('budget_year', date.today().year)
    
    def _auto_map_all_employees(self):
        """Automatically populate spreadsheet with all employees from database"""
        try:
            # Get employees from database
            connection_type = _get_connection_type()
            
            if connection_type == "sqlite":
                # Use direct database query
                sql = """
                SELECT e.EmployeeID as EmpID,
                       e.FirstName || ' ' || e.LastName || ' (' || e.EmployeeID || ')' as Name,
                       e.Position,
                       e.Department,
                       e.FTE,
                       e.Basis,
                       CASE 
                         WHEN e.Position LIKE '%Manager%' OR e.Position LIKE '%Director%' THEN 75000
                         WHEN e.Position LIKE '%Assistant%' OR e.Position LIKE '%Deputy%' THEN 55000
                         WHEN e.Position LIKE '%Supervisor%' THEN 65000
                         WHEN e.Position LIKE '%Officer%' OR e.Position LIKE '%Specialist%' THEN 45000
                         ELSE 40000 
                       END as BaseRate,
                       'A1' as Grade,
                       '1' as Step,
                       0 as COLA,
                       30 as BenefitsRate,
                       80 as HoursPerPeriod,
                       0 as OTHours,
                       1.5 as OTRate,
                       0 as VacancyMonths,
                       0 as StipendAnnual,
                       'standard' as BenefitsMode
                FROM Employees e
                WHERE e.EmployeeID IS NOT NULL
                  AND e.FirstName IS NOT NULL
                ORDER BY e.Department, e.LastName, e.FirstName
                """
                df, _ = _read_sql(sql, ())
                
                if not df.empty:
                    # Add calculated columns with zeros for initial load
                    calc_columns = ['FundedMonths', 'BaseWithCOLA', 'WagesBase', 'WagesOT', 
                                  'Stipends', 'Benefits', 'Taxes', 'TotalCost', 'AnnualCost', 'EffectiveRate']
                    for col in calc_columns:
                        df[col] = 0.0
                    
                    # Update session state
                    st.session_state.pbb_dataframe = df
                    st.success(f"Auto-mapped {len(df)} employees from database")
                else:
                    st.warning("No employees found in database")
            else:
                st.warning("Auto-mapping currently only supports SQLite databases")
                
        except Exception as e:
            st.error(f"Error auto-mapping employees: {e}")
    
    def _auto_map_department_employees(self, department: str):
        """Automatically populate spreadsheet with employees from specific department"""
        try:
            # Get employees from specific department
            connection_type = _get_connection_type()
            
            if connection_type == "sqlite":
                sql = """
                SELECT e.EmployeeID as EmpID,
                       e.FirstName || ' ' || e.LastName || ' (' || e.EmployeeID || ')' as Name,
                       e.Position,
                       e.Department,
                       e.FTE,
                       e.Basis,
                       CASE 
                         WHEN e.Position LIKE '%Manager%' OR e.Position LIKE '%Director%' THEN 75000
                         WHEN e.Position LIKE '%Assistant%' OR e.Position LIKE '%Deputy%' THEN 55000
                         WHEN e.Position LIKE '%Supervisor%' THEN 65000
                         WHEN e.Position LIKE '%Officer%' OR e.Position LIKE '%Specialist%' THEN 45000
                         ELSE 40000 
                       END as BaseRate,
                       'A1' as Grade,
                       '1' as Step,
                       0 as COLA,
                       30 as BenefitsRate,
                       80 as HoursPerPeriod,
                       0 as OTHours,
                       1.5 as OTRate,
                       0 as VacancyMonths,
                       0 as StipendAnnual,
                       'standard' as BenefitsMode
                FROM Employees e
                WHERE e.EmployeeID IS NOT NULL
                  AND e.FirstName IS NOT NULL
                  AND e.Department = ?
                ORDER BY e.LastName, e.FirstName
                """
                df, _ = _read_sql(sql, (department,))
                
                if not df.empty:
                    # Add calculated columns with zeros for initial load
                    calc_columns = ['FundedMonths', 'BaseWithCOLA', 'WagesBase', 'WagesOT', 
                                  'Stipends', 'Benefits', 'Taxes', 'TotalCost', 'AnnualCost', 'EffectiveRate']
                    for col in calc_columns:
                        df[col] = 0.0
                    
                    # Update session state - append to existing data
                    if 'pbb_dataframe' in st.session_state and not st.session_state.pbb_dataframe.empty:
                        # Remove existing rows from this department first
                        existing_df = st.session_state.pbb_dataframe
                        existing_df = existing_df[existing_df['Department'] != department]
                        # Append new department data
                        st.session_state.pbb_dataframe = pd.concat([existing_df, df], ignore_index=True)
                    else:
                        st.session_state.pbb_dataframe = df
                    
                    st.success(f"Auto-mapped {len(df)} employees from {department} department")
                else:
                    st.warning(f"No employees found in {department} department")
            else:
                st.warning("Auto-mapping currently only supports SQLite databases")
                
        except Exception as e:
            st.error(f"Error auto-mapping department employees: {e}")
    
    def _render_employee_visualization(self):
        """Render employee distribution visualization"""
        try:
            connection_type = _get_connection_type()
            
            if connection_type == "sqlite":
                # Get department and position distribution
                dept_sql = "SELECT Department, COUNT(*) as Count FROM Employees WHERE Department IS NOT NULL GROUP BY Department ORDER BY Count DESC"
                dept_df, _ = _read_sql(dept_sql, ())
                
                pos_sql = "SELECT Position, COUNT(*) as Count FROM Employees WHERE Position IS NOT NULL GROUP BY Position ORDER BY Count DESC LIMIT 10"
                pos_df, _ = _read_sql(pos_sql, ())
                
                if not dept_df.empty and not pos_df.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Employee Distribution by Department**")
                        fig_dept = px.pie(dept_df, values='Count', names='Department', 
                                        title='Employees by Department',
                                        height=300)
                        st.plotly_chart(fig_dept, use_container_width=True)
                    
                    with col2:
                        st.markdown("**Top 10 Positions**")
                        fig_pos = px.bar(pos_df, x='Count', y='Position', 
                                       orientation='h',
                                       text='Count',
                                       height=400)
                        
                        # Improve chart formatting
                        fig_pos.update_layout(
                            title={
                                'text': 'Employee Count by Position',
                                'font': {'size': 16, 'color': '#333333'},
                                'x': 0.5,
                                'xanchor': 'center',
                                'y': 0.95,
                                'yanchor': 'top'
                            },
                            yaxis={
                                'categoryorder': 'total ascending',
                                'tickfont': {'size': 10},
                                'title': {'text': '', 'font': {'size': 12}}
                            },
                            xaxis={
                                'title': {'text': 'Employee Count', 'font': {'size': 12}},
                                'tickfont': {'size': 10}
                            },
                            margin={'l': 150, 'r': 30, 't': 60, 'b': 50},
                            showlegend=False,
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            hovermode=False
                        )
                        
                        # Add text labels and disable hover
                        fig_pos.update_traces(
                            hoverinfo='none',
                            marker_color='#2E86AB',
                            marker_line={'color': '#1B5A73', 'width': 1},
                            textposition='outside',
                            textfont={'size': 11, 'color': '#333333'}
                        )
                        
                        st.plotly_chart(fig_pos, use_container_width=True)
                        
                    # Total employees
                    total_sql = "SELECT COUNT(*) as Total FROM Employees"
                    total_df, _ = _read_sql(total_sql, ())
                    if not total_df.empty:
                        total_employees = total_df.iloc[0]['Total']
                        st.info(f"**Total Employees in Database:** {total_employees:,}")
                else:
                    st.warning("No employee data available for visualization")
            else:
                st.info("Employee visualization currently only supports SQLite databases")
                
        except Exception as e:
            st.error(f"Error rendering employee visualization: {e}")
    
    def _create_initial_dataframe(self) -> pd.DataFrame:
        """Create initial empty dataframe with proper structure"""
        # Define all columns that should exist in the spreadsheet
        columns = [
            'Position', 'EmpID', 'Name', 'Department', 'FTE', 'Basis', 'BaseRate', 
            'Grade', 'Step', 'COLA', 'BenefitsRate', 'HoursPerPeriod', 'OTHours', 
            'OTRate', 'VacancyMonths', 'StipendAnnual', 'BenefitsMode',
            'FundedMonths', 'BaseWithCOLA', 'WagesBase', 'WagesOT', 'Stipends', 
            'Benefits', 'Taxes', 'TotalCost', 'AnnualCost', 'EffectiveRate'
        ]
        
        # Create dataframe with 5 empty rows for immediate use
        data = []
        for i in range(5):
            row = self._create_empty_row_dict()
            data.append(row)
        
        df = pd.DataFrame(data, columns=columns)
        return df
    
    def _create_empty_row_dict(self) -> Dict[str, Any]:
        """Create an empty row dictionary with completely blank values"""
        return {
            'Position': '',
            'EmpID': '',
            'Name': '',
            'Department': '',
            'FTE': None,
            'Basis': '',
            'BaseRate': None,
            'Grade': '',
            'Step': None,
            'COLA': None,
            'BenefitsRate': None,
            'HoursPerPeriod': None,
            'OTHours': None,
            'OTRate': None,
            'VacancyMonths': None,
            'StipendAnnual': None,
            'BenefitsMode': '',
            'FundedMonths': None,
            'BaseWithCOLA': None,
            'WagesBase': None,
            'WagesOT': None,
            'Stipends': None,
            'Benefits': None,
            'Taxes': None,
            'TotalCost': None,
            'AnnualCost': None,
            'EffectiveRate': None
        }
    
    def _get_employee_by_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get employee data by ID for auto-fill"""
        try:
            # Try from database first
            connection_type = _get_connection_type()
            if connection_type == "sqlite":
                sql = "SELECT EmployeeID as EmpID, FirstName || ' ' || LastName as Name, Department, Position, Basis, FTE FROM Employees WHERE EmployeeID = ? LIMIT 1"
                df, _ = _read_sql(sql, (employee_id,))
                if not df.empty:
                    emp = df.iloc[0]
                    return {
                        'Name': str(emp['Name']) if 'Name' in emp else '',
                        'Position': str(emp['Position']) if 'Position' in emp else '',
                        'Department': str(emp['Department']) if 'Department' in emp else '',
                        'Basis': str(emp['Basis']) if 'Basis' in emp else 'Salary',
                        'BaseRate': 50000.0,  # Default since not in database
                        'HoursPerPeriod': 80.0,  # Default since not in database
                        'FTE': float(emp['FTE']) if 'FTE' in emp else 1.0
                    }
            
            # Fallback to loaded data
            emp_data = self.employees_data[self.employees_data['EmpID'] == employee_id]
            if not emp_data.empty:
                emp = emp_data.iloc[0]
                return {
                    'Name': emp.get('Name', ''),
                    'Position': emp.get('Position', ''),
                    'Department': emp.get('Department', ''),
                    'Basis': emp.get('Basis', 'Salary'),
                    'BaseRate': emp.get('BaseRate', 50000.0),
                    'HoursPerPeriod': emp.get('HoursPerPeriod', 80.0),
                    'FTE': emp.get('FTE', 1.0)
                }
        except Exception as e:
            st.error(f"Error getting employee {employee_id}: {e}")
        return None
    
    def _get_position_from_employee_name(self, name_with_id: str) -> Optional[str]:
        """Get position from employee name (format: 'Name (EmpID)')"""
        try:
            # Extract EmpID from format "Name (EmpID)"
            if '(' in name_with_id and ')' in name_with_id:
                emp_id = name_with_id.split('(')[-1].rstrip(')')
                
                # Try database first
                connection_type = _get_connection_type()
                if connection_type == "sqlite":
                    sql = "SELECT Position FROM Employees WHERE EmployeeID = ? LIMIT 1"
                    df, _ = _read_sql(sql, (emp_id,))
                    if not df.empty:
                        return df.iloc[0]['Position']
                
                # Fallback to loaded data
                emp_data = self.employees_data[self.employees_data['EmpID'] == emp_id]
                if not emp_data.empty:
                    return emp_data.iloc[0].get('Position', '')
        except Exception as e:
            st.error(f"Error getting position for {name_with_id}: {e}")
        return None
    
    def _get_position_data(self, position_title: str) -> Optional[Dict[str, Any]]:
        """Get position data by title for auto-fill, including employee if position is filled"""
        try:
            pos_data = self.positions_data[self.positions_data['Title'] == position_title]
            if not pos_data.empty:
                pos = pos_data.iloc[0]
                result = {
                    'Department': pos.get('HomeDept', ''),
                    'Grade': pos.get('PayGrade', ''),
                    'FTE': pos.get('FTE', 1.0)
                }
                
                # Check if there's an employee assigned to this position
                position_id = pos.get('PositionID')
                if position_id:
                    emp_in_position = self.employees_data[
                        self.employees_data.get('PositionTitle', '') == position_title
                    ]
                    if not emp_in_position.empty:
                        # Auto-fill with the employee in this position
                        emp = emp_in_position.iloc[0]
                        first_name = emp.get('FirstName', '')
                        last_name = emp.get('LastName', '')
                        if not first_name and 'Name' in emp:
                            name_parts = str(emp['Name']).split(' ', 1)
                            first_name = name_parts[0] if len(name_parts) > 0 else ''
                            last_name = name_parts[1] if len(name_parts) > 1 else ''
                        
                        result.update({
                            'EmployeeID': emp.get('EmpID', 0),
                            'FirstName': first_name,
                            'LastName': last_name,
                            'Basis': emp.get('Basis', 'Salary'),
                            'BaseRate': emp.get('BaseRate', 50000.0),
                            'HoursPerPeriod': emp.get('HoursPerPeriod', 80.0),
                            'Status': 'Filled'
                        })
                
                return result
        except Exception as e:
            st.error(f"Error getting position data for {position_title}: {e}")
        return None
    
    def _get_employee_data(self, incumbent_display: str) -> Dict[str, Any]:
        """Get employee data from incumbent selection"""
        if not incumbent_display or incumbent_display == '':
            return {}
        
        # Extract EmpID from display name (format: "Name (EmpID)")
        try:
            emp_id = incumbent_display.split('(')[-1].rstrip(')')
            emp_row = self.employees_data[self.employees_data['EmpID'] == emp_id]
            if not emp_row.empty:
                emp = emp_row.iloc[0]
                return {
                    'EmpID': emp['EmpID'],
                    'EmpBasis': emp['Basis'],
                    'EmpBaseRate': emp['AnnualSalary'] if emp['Basis'] == 'Salary' else emp['HourlyRate'],
                    'EmpHoursPP': emp['HoursPP'] if emp['Basis'] == 'Hourly' else 0,
                    'EmpOTHoursPP': emp['OTHoursPP'],
                    'EmpBenefitsMonthly': emp['BenefitsMonthly']
                }
        except Exception:
            pass
        
        return {}
    
    def _calculate_funded_months(self, hire_start: Optional[date], hire_end: Optional[date], 
                               vacancy_months: float, year_start: date, year_end: date) -> float:
        """Calculate funded months based on hire dates and vacancy"""
        if hire_start and hire_end:
            # Use actual hire period
            start_date = max(hire_start, year_start)
            end_date = min(hire_end, year_end)
            if end_date >= start_date:
                days = (end_date - start_date).days + 1
                return max(0, days / 30.4375)  # Average month length
            return 0
        elif vacancy_months >= 0 and vacancy_months <= 12:
            # Use vacancy months
            return 12 - vacancy_months
        else:
            # Default to full year
            return 12.0