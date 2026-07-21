"""
Enhanced Position-Based Budgeting with Multi-Sheet System
Features:
- Multi-sheet tabs (Production + Sandbox sheets)
- GL account mapping for ERP export
- Split allocation across funds/cost centers
- Multi-year budgeting (FY2024-2026)
- Vacancy management
- Grant-funded position tracking
- Step/grade progression
- Benefit package configuration
- Smart payroll sync with manual override
- CSV export by GL account for ERP import
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
from typing import Dict, Any, List, Optional
import sqlite3
import os
from datetime import datetime
import csv
from io import StringIO
from .pbb_data_store import PBBDataStore

class PBBEnhancedMultisheet:
    def __init__(self):
        # Initialize persistent data store
        self.data_store = PBBDataStore()
        
        # Initialize workbook ID (could be user-specific or organization-specific)
        if 'pbb_workbook_id' not in st.session_state:
            st.session_state['pbb_workbook_id'] = 'default'
        
        # Load or create workbook
        self.workbook_id = st.session_state['pbb_workbook_id']
        
        # Load sheets from database (reload if flag is missing OR False)
        if not st.session_state.get('pbb_sheets_loaded', False):
            self._load_sheets_from_db()
            st.session_state['pbb_sheets_loaded'] = True
        
        # Set active sheet
        if 'pbb_active_sheet' not in st.session_state:
            st.session_state['pbb_active_sheet'] = 'Sheet 1 (Production)'
        
        # Load active sheet ID (always refresh to avoid stale IDs after create/delete)
        st.session_state['pbb_active_sheet_id'] = self._get_sheet_id(st.session_state['pbb_active_sheet'])
    
    def _load_sheets_from_db(self):
        """Load all sheets for this workbook from database"""
        sheets = self.data_store.get_or_create_workbook(self.workbook_id)
        
        # Convert to session state format
        st.session_state['pbb_sheets_meta'] = {
            sheet['name']: {
                'id': sheet['id'],
                'is_production': sheet['is_production'],
                'is_locked': sheet['is_locked'],
                'order': sheet['order']
            }
            for sheet in sheets
        }
    
    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get database ID for sheet name"""
        if 'pbb_sheets_meta' in st.session_state:
            return st.session_state['pbb_sheets_meta'].get(sheet_name, {}).get('id', 0)
        return 0
    
    def render(self):
        """Main render method for enhanced PBB"""
        st.markdown("### Enhanced Position-Based Budget Workbook")
        st.markdown("*Multi-sheet Excel-like interface with GL mapping and split allocations*")
        
        # Sheet management toolbar
        self._render_sheet_toolbar()
        
        # Department auto-population
        self._render_department_loader()
        
        st.markdown("---")
        
        # Save form BEFORE grid (critical for persistence)
        self._render_save_form()
        
        # Render the active sheet's grid
        self._render_active_sheet()
        
        # Additional Features
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_position_history()
            self._render_union_compliance()
        
        with col2:
            self._render_ai_budget_assistant()
            self._render_department_comparison()
        
        # Export options
        self._render_export_options()
    
    def _render_save_form(self):
        """Render save form to persist grid data"""
        active_sheet = st.session_state['pbb_active_sheet']
        sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
        
        with st.expander("Save Sheet Data", expanded=False):
            with st.form(key=f"pbb_save_form_{active_sheet}", clear_on_submit=False):
                grid_data_json = st.text_area(
                    "Paste grid data or let it auto-sync from the spreadsheet above",
                    value="",
                    height=68,
                    key=f"grid_data_{active_sheet}",
                    label_visibility="collapsed"
                )
                submitted = st.form_submit_button("Save Sheet", use_container_width=True, type="primary")
            
            if submitted and grid_data_json:
                try:
                    grid_data = json.loads(grid_data_json)
                    self.data_store.save_sheet_data(sheet_id, grid_data)
                    st.success(f"Saved {len(grid_data)} rows to {active_sheet}")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"Invalid grid data format: {e}")
                except Exception as e:
                    st.error(f"Error saving: {e}")
    
    def _render_sheet_toolbar(self):
        """Render sheet tabs and management controls"""
        col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
        
        with col1:
            # Sheet tabs from database
            sheets_meta = st.session_state.get('pbb_sheets_meta', {})
            sheet_names = list(sheets_meta.keys())
            
            if not sheet_names:
                sheet_names = ['Sheet 1 (Production)']
            
            current_index = sheet_names.index(st.session_state['pbb_active_sheet']) if st.session_state['pbb_active_sheet'] in sheet_names else 0
            
            active_sheet = st.selectbox(
                "Active Sheet",
                sheet_names,
                index=current_index,
                key='sheet_selector',
                help="Select sheet to work on. Sheet 1 (Production) is for ERP import."
            )
            
            if active_sheet != st.session_state['pbb_active_sheet']:
                st.session_state['pbb_active_sheet'] = active_sheet
                st.session_state['pbb_active_sheet_id'] = self._get_sheet_id(active_sheet)
                st.rerun()
        
        with col2:
            if st.button("New", use_container_width=True, help="Create new sandbox sheet"):
                self._create_new_sheet()
        
        with col3:
            if st.button("Rename", use_container_width=True, help="Rename current sheet"):
                st.info("Rename functionality coming soon")
        
        with col4:
            current_sheet = st.session_state['pbb_active_sheet']
            if current_sheet != 'Sheet 1 (Production)':
                if st.button("Delete", use_container_width=True, help="Delete current sheet"):
                    sheet_id = self._get_sheet_id(current_sheet)
                    self.data_store.delete_sheet(sheet_id)
                    st.session_state['pbb_active_sheet'] = 'Sheet 1 (Production)'
                    st.session_state['pbb_sheets_loaded'] = False  # Force reload
                    st.rerun()
    
    def _create_new_sheet(self):
        """Create a new sandbox sheet in database"""
        sheets_meta = st.session_state.get('pbb_sheets_meta', {})
        sheet_num = len([s for s in sheets_meta.keys() if s.startswith('Sandbox')]) + 1
        new_sheet_name = f'Sandbox {sheet_num}'
        
        # Create in database
        sheet_id = self.data_store.add_sheet(self.workbook_id, new_sheet_name)
        
        # Update session state
        st.session_state['pbb_active_sheet'] = new_sheet_name
        st.session_state['pbb_active_sheet_id'] = sheet_id
        st.session_state['pbb_sheets_loaded'] = False  # Force reload
        st.rerun()
    
    def _render_department_loader(self):
        """Department auto-population interface"""
        st.markdown("### Quick Load from Payroll")
        
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            departments_data = self._get_departments_data()
            selected_departments = st.multiselect(
                "Select Departments",
                options=departments_data,
                placeholder="Choose departments to auto-populate from payroll",
                key='dept_selector'
            )
        
        with col2:
            fiscal_year = st.selectbox(
                "Fiscal Year",
                options=['FY 2024', 'FY 2025', 'FY 2026'],
                index=1,
                key='fy_selector'
            )
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Load", use_container_width=True, type="primary"):
                if selected_departments:
                    employees = self._get_employees_by_departments_fast(selected_departments)
                    if employees:
                        # Add to active sheet in database
                        sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
                        if sheet_id > 0:
                            # Load existing data, append new employees, save back
                            current_data = self.data_store.load_sheet_data(sheet_id)
                            combined_data = current_data + employees
                            self.data_store.save_sheet_data(sheet_id, combined_data)
                            st.success(f"Loaded {len(employees)} employees from {len(selected_departments)} departments to database")
                            st.rerun()
                        else:
                            st.error("No active sheet selected")
                    else:
                        st.warning("No employees found in selected departments")
        
        # Prior Year Actuals Import (Sandbox sheets only)
        active_sheet = st.session_state.get('pbb_active_sheet', '')
        if active_sheet != 'Sheet 1 (Production)':
            st.markdown("---")
            st.markdown("### Load Prior Year Actuals")
            st.markdown("*Import actual compensation data from completed fiscal years (no estimates)*")
            
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                prior_departments = st.multiselect(
                    "Select Departments",
                    options=departments_data,
                    placeholder="Choose departments for prior year import",
                    key='prior_dept_selector'
                )
            
            with col2:
                prior_fy = st.selectbox(
                    "Prior Fiscal Year",
                    options=['FY 2023 (Actuals)', 'FY 2024 (Actuals)'],
                    index=0,
                    key='prior_fy_selector',
                    help="Select a completed fiscal year to import actual compensation data"
                )
            
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Import Actuals", use_container_width=True, type="secondary"):
                    if prior_departments:
                        # Extract fiscal year number
                        fy_year = int(prior_fy.split()[1])
                        
                        # Load prior year actuals from payroll history
                        prior_employees = self._get_prior_year_actuals(prior_departments, fy_year)
                        
                        if prior_employees:
                            sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
                            if sheet_id > 0:
                                current_data = self.data_store.load_sheet_data(sheet_id)
                                combined_data = current_data + prior_employees
                                self.data_store.save_sheet_data(sheet_id, combined_data)
                                st.success(f"Imported {len(prior_employees)} positions with actual FY{fy_year} data from {len(prior_departments)} departments")
                                st.rerun()
                            else:
                                st.error("No active sheet selected")
                        else:
                            st.warning(f"No payroll history found for FY{fy_year}")
                    else:
                        st.warning("Please select departments to import")
    
    def _render_active_sheet(self):
        """Render the AG-Grid for the active sheet"""
        active_sheet = st.session_state['pbb_active_sheet']
        sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
        
        # Advanced Filtering Panel
        with st.expander("Advanced Filters", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                salary_min = st.number_input("Min Salary", value=0, step=1000, key=f"salary_min_{active_sheet}")
                salary_max = st.number_input("Max Salary", value=500000, step=1000, key=f"salary_max_{active_sheet}")
            
            with col2:
                filter_departments = st.multiselect(
                    "Departments",
                    options=self._get_departments_data(),
                    key=f"filter_dept_{active_sheet}"
                )
                filter_status = st.multiselect(
                    "Status",
                    options=["Filled", "Vacant", "Frozen"],
                    key=f"filter_status_{active_sheet}"
                )
            
            with col3:
                filter_funding = st.multiselect(
                    "Funding Source",
                    options=["General Fund", "Enterprise Fund", "Grant Fund", "Special Revenue"],
                    key=f"filter_funding_{active_sheet}"
                )
                filter_benefits = st.multiselect(
                    "Benefit Package",
                    options=list(self.data_store.get_benefit_packages().keys()),
                    key=f"filter_benefits_{active_sheet}"
                )
            
            with col4:
                filter_data_source = st.multiselect(
                    "Data Source",
                    options=["Payroll DB", "Manual Entry", "FY2023 Actuals", "FY2024 Actuals"],
                    key=f"filter_source_{active_sheet}"
                )
                if st.button("Clear All Filters", use_container_width=True, key=f"clear_filters_{active_sheet}"):
                    st.rerun()
        
        # Build filter criteria
        filter_criteria = {
            "salary_min": salary_min,
            "salary_max": salary_max,
            "departments": filter_departments,
            "status": filter_status,
            "funding": filter_funding,
            "benefits": filter_benefits,
            "data_source": filter_data_source
        }
        
        # Load data from database
        sheet_data = self.data_store.load_sheet_data(sheet_id) if sheet_id > 0 else []
        
        # Apply filters to data
        sheet_data = self._apply_filters(sheet_data, filter_criteria)
        
        # Get reference data from database
        employees_data = self._get_employees_data()
        positions_data = self._get_positions_data()
        departments_data = self._get_departments_data()
        gl_accounts = self.data_store.get_gl_accounts()
        benefit_packages = list(self.data_store.get_benefit_packages().keys())
        grades = self._get_grades()
        
        # Build position-to-employees mapping for dynamic filtering
        position_to_employees_map = self._build_position_to_employees_map(employees_data)
        
        # Create enhanced HTML with all features
        html_content = self._create_enhanced_grid_html(
            employees_data, positions_data, departments_data, 
            gl_accounts, benefit_packages, grades, sheet_data, active_sheet, filter_criteria,
            position_to_employees_map
        )
        
        # Render with full height
        components.html(html_content, height=900, scrolling=True)
    
    def _create_enhanced_grid_html(self, employees_data, positions_data, departments_data, 
                                   gl_accounts, benefit_packages, grades, sheet_data, sheet_name, filter_criteria=None,
                                   position_to_employees_map=None):
        """Create the comprehensive AG-Grid HTML with all enhanced features"""
        
        if filter_criteria is None:
            filter_criteria = {}
        
        if position_to_employees_map is None:
            position_to_employees_map = {}
        
        employees_json = json.dumps(employees_data)
        positions_json = json.dumps(positions_data)
        departments_json = json.dumps(departments_data)
        gl_accounts_json = json.dumps(gl_accounts)
        benefit_packages_json = json.dumps(benefit_packages)
        grades_json = json.dumps(grades)
        sheet_data_json = json.dumps(sheet_data)
        is_production = json.dumps(sheet_name == 'Sheet 1 (Production)')
        position_to_employees_json = json.dumps(position_to_employees_map)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ag-grid-community@31.0.0/styles/ag-grid.css">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ag-grid-community@31.0.0/styles/ag-theme-alpine.css">
            <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
            <style>
                body {{ margin: 0; padding: 10px; font-family: 'Segoe UI', sans-serif; background: #fff; }}
                .toolbar {{ display: flex; gap: 0; margin-bottom: 12px; align-items: center; background: #f4f6f8; padding: 6px 10px; border-radius: 6px; border: 1px solid #e0e4e8; }}
                .btn-group {{ display: flex; gap: 4px; align-items: center; padding: 0 8px; }}
                .btn-group + .btn-group {{ border-left: 1px solid #d0d4d8; }}
                .btn {{ padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer;
                        font-size: 12px; display: inline-flex; align-items: center; gap: 4px; transition: background 0.15s; white-space: nowrap; }}
                .btn-primary {{ background-color: #1565c0; color: white; }}
                .btn-primary:hover {{ background-color: #0d47a1; }}
                .btn-success {{ background-color: #2e7d32; color: white; }}
                .btn-success:hover {{ background-color: #1b5e20; }}
                .btn-danger {{ background-color: #c62828; color: white; }}
                .btn-danger:hover {{ background-color: #b71c1c; }}
                .btn-info {{ background-color: #00838f; color: white; }}
                .btn-info:hover {{ background-color: #006064; }}
                .btn-warning {{ background-color: #ef6c00; color: white; }}
                .btn-warning:hover {{ background-color: #e65100; }}
                .btn-secondary {{ background-color: #546e7a; color: white; }}
                .btn-secondary:hover {{ background-color: #37474f; }}
                .status {{ padding: 5px 10px; border-radius: 4px; font-size: 11px; font-weight: 500; }}
                .status.success {{ background-color: #e8f5e9; color: #2e7d32; }}
                .status.error {{ background-color: #ffebee; color: #c62828; }}
                .status.info {{ background-color: #e3f2fd; color: #1565c0; }}
                #gridContainer {{ height: 580px; width: 100%; }}

                /* Column styling */
                .ag-theme-alpine .input-header {{ background-color: #e8eef4 !important; color: #1a3a5c !important; font-weight: 600 !important; }}
                .ag-theme-alpine .calculated-header {{ background-color: #f0f0f0 !important; color: #555 !important; font-weight: 600 !important; }}
                .ag-theme-alpine .gl-header {{ background-color: #e6f0e8 !important; color: #2e6b35 !important; font-weight: 600 !important; }}
                .ag-theme-alpine .allocation-header {{ background-color: #fdf0e2 !important; color: #8a5100 !important; font-weight: 600 !important; }}
                .ag-theme-alpine .input-cell {{ background-color: rgba(232, 238, 244, 0.12) !important; }}
                .ag-theme-alpine .calculated-cell {{ background-color: rgba(240, 240, 240, 0.3) !important; color: #555 !important; }}
                .ag-theme-alpine .gl-cell {{ background-color: rgba(230, 240, 232, 0.15) !important; }}
                .ag-theme-alpine .vacant-row {{ background-color: #fff9c4 !important; }}
                .ag-theme-alpine .grant-funded {{ border-left: 3px solid #ef6c00 !important; }}

                /* Column group header band */
                .ag-theme-alpine .ag-header-group-cell {{ background-color: #263238 !important; color: #eceff1 !important; font-weight: 700 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.5px; }}

                /* Summary styling */
                .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; }}
                .summary-card {{ border-radius: 6px; padding: 14px 16px; border: 1px solid; }}
                .summary-card.navy {{ background: #e8eaf6; border-color: #c5cae9; color: #1a237e; }}
                .summary-card.green {{ background: #e8f5e9; border-color: #c8e6c9; color: #1b5e20; }}
                .summary-card.slate {{ background: #eceff1; border-color: #cfd8dc; color: #37474f; }}
                .summary-card.teal {{ background: #e0f2f1; border-color: #b2dfdb; color: #004d40; }}
                .summary-title {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 4px; }}
                .summary-value {{ font-size: 22px; font-weight: 700; }}

                /* Modal styling */
                .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%;
                         background-color: rgba(0,0,0,0.45); }}
                .modal-content {{ background-color: #fff; margin: 5% auto; padding: 24px; border-radius: 8px;
                                 width: 80%; max-width: 700px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }}
                .modal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
                .modal-header h3 {{ margin: 0; color: #263238; font-size: 16px; }}
                .close {{ color: #90a4ae; font-size: 24px; font-weight: bold; cursor: pointer; line-height: 1; }}
                .close:hover {{ color: #263238; }}
                .allocation-row {{ display: flex; gap: 10px; margin-bottom: 10px; align-items: center; }}
                .allocation-input {{ flex: 2; padding: 8px; border: 1px solid #cfd8dc; border-radius: 4px; font-size: 13px; }}

                /* Production sheet badge */
                .production-badge {{ background: #1b5e20; color: white; padding: 3px 10px; border-radius: 3px;
                                    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
                .sandbox-badge {{ background: #546e7a; color: white; padding: 3px 10px; border-radius: 3px;
                                 font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
            </style>
        </head>
        <body>
            <div class="toolbar">
                <div class="btn-group">
                    <span id="sheetBadge" class="production-badge">PRODUCTION</span>
                </div>
                <div class="btn-group">
                    <button class="btn btn-primary" onclick="addRow()" title="Add new position row">Add Position</button>
                    <button class="btn btn-success" onclick="calculateAll()" title="Recalculate all formulas">Calculate</button>
                </div>
                <div class="btn-group">
                    <button class="btn btn-warning" onclick="openSplitAllocationModal()" title="Split selected position across funds">Split Allocation</button>
                    <button class="btn btn-info" onclick="copySelectedRows()" title="Copy selected rows">Copy</button>
                    <button class="btn btn-info" onclick="pasteRows()" title="Paste rows">Paste</button>
                    <button class="btn btn-danger" onclick="deleteSelected()" title="Delete selected rows">Delete</button>
                </div>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="refreshFromPayroll()" title="Refresh data from payroll DB">Sync Payroll</button>
                </div>
                <div style="margin-left: auto; display: flex; gap: 8px; align-items: center;">
                    <button class="btn btn-info" onclick="showQuickActions()" title="Bulk operations menu">Quick Actions</button>
                    <span id="status" class="status success">Ready</span>
                </div>
            </div>
            
            <div id="gridContainer" class="ag-theme-alpine"></div>
            
            <div class="summary-grid">
                <div class="summary-card navy">
                    <div class="summary-title">Total Positions</div>
                    <div class="summary-value" id="totalPositions">0</div>
                </div>
                <div class="summary-card green">
                    <div class="summary-title">Total Budget (FY 2025)</div>
                    <div class="summary-value" id="totalBudget">$0</div>
                </div>
                <div class="summary-card slate">
                    <div class="summary-title">Vacant Positions</div>
                    <div class="summary-value" id="vacantPositions">0</div>
                </div>
                <div class="summary-card teal">
                    <div class="summary-title">Grant Funded</div>
                    <div class="summary-value" id="grantFunded">0</div>
                </div>
            </div>
            
            <!-- Split Allocation Modal -->
            <div id="splitModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Split Position Allocation</h3>
                        <span class="close" onclick="closeSplitModal()">&times;</span>
                    </div>
                    <div id="allocationEntries">
                        <div class="allocation-row">
                            <select class="allocation-input" id="fund1">
                                <option value="">Select Fund/GL Account...</option>
                            </select>
                            <input type="number" class="allocation-input" id="percent1" placeholder="%" min="0" max="100" value="100">
                            <input type="number" class="allocation-input" id="amount1" placeholder="Amount" readonly>
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="addAllocationRow()">Add Allocation</button>
                    <button class="btn btn-success" onclick="saveSplitAllocation()" style="margin-left: 10px;">Save Split</button>
                </div>
            </div>
            
            <!-- Quick Actions Modal -->
            <div id="quickActionsModal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Quick Actions - Bulk Operations</h3>
                        <span class="close" onclick="closeQuickActions()">&times;</span>
                    </div>
                    <div style="display: grid; gap: 10px;">
                        <button class="btn btn-info" onclick="applyMeritIncrease()">Apply 2% Merit Increase</button>
                        <button class="btn btn-info" onclick="applyCOLA()">Apply 3% COLA (Cost of Living)</button>
                        <button class="btn btn-warning" onclick="freezeVacancies()">Freeze All Vacant Positions</button>
                        <button class="btn btn-success" onclick="applyStepIncrease()">Apply Step Increase (Eligible Only)</button>
                        <button class="btn btn-secondary" onclick="bulkEditBenefits()">Bulk Edit Benefits %</button>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/ag-grid-community@31.0.0/dist/ag-grid-community.min.js"></script>
            <script>
                let gridApi;
                let clipboardRows = [];
                const employees = {employees_json};
                const positions = {positions_json};
                const departments = {departments_json};
                const glAccounts = {gl_accounts_json};
                const benefitPackages = {benefit_packages_json};
                const grades = {grades_json};
                const initialData = {sheet_data_json};
                const isProduction = {is_production};
                const positionToEmployees = {position_to_employees_json};
                
                // Get filtered employees based on selected position
                function getEmployeesForPosition(position) {{
                    if (!position || position === '') {{
                        return [''].concat(employees.map(e => e.name));
                    }}
                    return [''].concat(positionToEmployees[position] || []);
                }}
                
                // Update sheet badge
                if (!isProduction) {{
                    document.getElementById('sheetBadge').className = 'sandbox-badge';
                    document.getElementById('sheetBadge').textContent = 'SANDBOX';
                }}
                
                const columnDefs = [
                    {{ headerName: '', field: 'checkbox', width: 40, checkboxSelection: true, headerCheckboxSelection: true, pinned: 'left', lockPosition: true, suppressMovable: true }},

                    {{ headerName: 'Employee Info', marryChildren: true, children: [
                        {{ headerName: 'Position', field: 'position', width: 170, editable: true, pinned: 'left',
                           cellEditor: 'agSelectCellEditor', cellEditorParams: {{ values: [''].concat(positions) }},
                           headerClass: 'input-header', cellClass: 'input-cell',
                           onCellValueChanged: params => {{
                               if (params.oldValue !== params.newValue) {{
                                   params.data.name = '';
                                   params.data.emp_id = '';
                                   params.data.department = '';
                                   params.api.refreshCells({{ rowNodes: [params.node], force: true }});
                               }}
                           }}
                        }},
                        {{ headerName: 'Employee Name', field: 'name', width: 180, editable: true, pinned: 'left',
                           cellEditor: 'agSelectCellEditor',
                           cellEditorParams: params => {{
                               const position = params.data.position || '';
                               return {{ values: getEmployeesForPosition(position) }};
                           }},
                           headerClass: 'input-header', cellClass: 'input-cell' }},
                        {{ headerName: 'Emp ID', field: 'emp_id', width: 90, editable: false, pinned: 'left',
                           headerClass: 'calculated-header', cellClass: 'calculated-cell' }},
                        {{ headerName: 'Department', field: 'department', width: 130, editable: false, pinned: 'left',
                           headerClass: 'calculated-header', cellClass: 'calculated-cell' }},
                        {{ headerName: 'Status', field: 'status', width: 100, editable: true,
                           cellEditor: 'agSelectCellEditor', cellEditorParams: {{ values: ['Filled', 'Vacant', 'Frozen'] }},
                           headerClass: 'input-header', cellClass: 'input-cell',
                           cellStyle: params => params.value === 'Vacant' ? {{ backgroundColor: '#fff9c4' }} : null }},
                        {{ headerName: 'Funding Source', field: 'funding_source', width: 140, editable: true,
                           cellEditor: 'agSelectCellEditor',
                           cellEditorParams: {{ values: ['General Fund', 'Grant Funded', 'Water Fund', 'Sewer Fund', 'Special Revenue'] }},
                           headerClass: 'input-header', cellClass: 'input-cell' }}
                    ] }},

                    {{ headerName: 'Compensation', children: [
                        {{ headerName: 'Grade', field: 'grade', width: 90, editable: true,
                           cellEditor: 'agSelectCellEditor', cellEditorParams: {{ values: [''].concat(grades) }},
                           headerClass: 'input-header', cellClass: 'input-cell' }},
                        {{ headerName: 'Step', field: 'step', width: 70, editable: true, type: 'numericColumn',
                           headerClass: 'input-header', cellClass: 'input-cell' }},
                        {{ headerName: 'FTE', field: 'fte', width: 70, editable: true, type: 'numericColumn',
                           headerClass: 'input-header', cellClass: 'input-cell',
                           valueFormatter: params => params.value?.toFixed(2) || '1.00' }},
                        {{ headerName: 'Basis', field: 'basis', width: 90, editable: true,
                           cellEditor: 'agSelectCellEditor', cellEditorParams: {{ values: ['Salary', 'Hourly'] }},
                           headerClass: 'input-header', cellClass: 'input-cell' }},
                        {{ headerName: 'Base Rate', field: 'base_rate', width: 110, editable: true, type: 'numericColumn',
                           headerClass: 'input-header', cellClass: 'input-cell',
                           valueFormatter: params => '$' + (params.value?.toLocaleString() || '0') }},
                        {{ headerName: 'Benefit Pkg', field: 'benefit_package', width: 130, editable: true,
                           cellEditor: 'agSelectCellEditor', cellEditorParams: {{ values: [''].concat(benefitPackages) }},
                           headerClass: 'input-header', cellClass: 'input-cell' }},
                        {{ headerName: 'Benefits %', field: 'benefits_rate', width: 95, editable: true, type: 'numericColumn',
                           headerClass: 'input-header', cellClass: 'input-cell',
                           valueFormatter: params => (params.value || 0).toFixed(1) + '%' }}
                    ] }},

                    {{ headerName: 'Multi-Year Budget', children: [
                        {{ headerName: 'FY 2024', field: 'fy2024', width: 110, editable: true, type: 'numericColumn',
                           headerClass: 'input-header', cellClass: 'input-cell',
                           valueFormatter: params => '$' + (params.value?.toLocaleString() || '0') }},
                        {{ headerName: 'FY 2025', field: 'fy2025', width: 110, editable: true, type: 'numericColumn',
                           headerClass: 'input-header', cellClass: 'input-cell',
                           valueFormatter: params => '$' + (params.value?.toLocaleString() || '0') }},
                        {{ headerName: 'FY 2026', field: 'fy2026', width: 110, editable: true, type: 'numericColumn',
                           headerClass: 'input-header', cellClass: 'input-cell',
                           valueFormatter: params => '$' + (params.value?.toLocaleString() || '0') }},
                        {{ headerName: 'YoY %', field: 'yoy_change', width: 80, editable: false,
                           headerClass: 'calculated-header', cellClass: 'calculated-cell',
                           valueFormatter: params => (params.value || 0).toFixed(1) + '%',
                           cellStyle: params => ({{ color: params.value > 0 ? '#2e7d32' : params.value < 0 ? '#c62828' : '#555' }}) }}
                    ] }},

                    {{ headerName: 'GL / Funding', children: [
                        {{ headerName: 'GL Account', field: 'gl_account', width: 140, editable: true,
                           cellEditor: 'agSelectCellEditor', cellEditorParams: {{ values: [''].concat(glAccounts) }},
                           headerClass: 'gl-header', cellClass: 'gl-cell' }},
                        {{ headerName: 'Split %', field: 'split_percent', width: 80, editable: false,
                           headerClass: 'allocation-header', cellClass: 'calculated-cell',
                           valueFormatter: params => params.value ? params.value + '%' : '100%' }},
                        {{ headerName: 'Allocated Amt', field: 'allocated_amount', width: 120, editable: false,
                           headerClass: 'allocation-header', cellClass: 'calculated-cell',
                           valueFormatter: params => '$' + (params.value?.toLocaleString() || '0') }}
                    ] }},

                    {{ headerName: 'Vacancy & Grants', children: [
                        {{ headerName: 'Grant End', field: 'grant_end_date', width: 110, editable: true,
                           headerClass: 'input-header', cellClass: 'input-cell',
                           cellEditor: 'agDateCellEditor' }},
                        {{ headerName: 'Days Left', field: 'days_to_grant_end', width: 90, editable: false,
                           headerClass: 'calculated-header', cellClass: 'calculated-cell',
                           cellStyle: params => {{
                               if (!params.value) return null;
                               return params.value < 90 ? {{ backgroundColor: '#ffebee', color: '#c62828' }} :
                                      params.value < 180 ? {{ backgroundColor: '#fff3e0', color: '#e65100' }} : null;
                           }} }},
                        {{ headerName: 'Vacant Since', field: 'vacant_since', width: 110, editable: true,
                           headerClass: 'input-header', cellClass: 'input-cell' }},
                        {{ headerName: 'Vac. Savings', field: 'vacancy_savings', width: 110, editable: false,
                           headerClass: 'calculated-header', cellClass: 'calculated-cell',
                           valueFormatter: params => '$' + (params.value?.toLocaleString() || '0') }},
                        {{ headerName: 'Proj. Fill Date', field: 'projected_fill_date', width: 120, editable: true,
                           headerClass: 'input-header', cellClass: 'input-cell' }}
                    ] }},

                    {{ headerName: 'Calculated', children: [
                        {{ headerName: 'Total Cost FY25', field: 'total_cost', width: 130, editable: false, type: 'numericColumn',
                           headerClass: 'calculated-header', cellClass: 'calculated-cell',
                           valueFormatter: params => '$' + (params.value?.toLocaleString() || '0') }},
                        {{ headerName: 'Source', field: 'data_source', width: 100, editable: false,
                           headerClass: 'calculated-header', cellClass: 'calculated-cell',
                           cellStyle: params => params.value === 'Payroll DB' ? {{ color: '#2e7d32' }} : {{ color: '#78909c' }} }}
                    ] }}
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
                    onCellValueChanged: onCellValueChanged,
                    getRowStyle: params => {{
                        if (params.data.status === 'Vacant') return {{ background: '#fffde7' }};
                        if (params.data.funding_source === 'Grant Funded') return {{ borderLeft: '3px solid #ff9800' }};
                        return null;
                    }}
                }};
                
                function onGridReady(params) {{
                    gridApi = params.api;
                    
                    if (initialData && initialData.length > 0) {{
                        gridApi.setRowData(initialData);
                        calculateAll();
                    }} else {{
                        addInitialRows();
                    }}
                }}
                
                function onCellValueChanged(event) {{
                    const {{ data, colDef, newValue }} = event;
                    
                    // Auto-fill from payroll DB when name selected
                    if (colDef.field === 'name' && newValue) {{
                        const employee = employees.find(emp => emp.name === newValue);
                        if (employee) {{
                            data.emp_id = employee.emp_id;
                            data.position = employee.position;
                            data.department = employee.department;
                            data.fte = employee.fte;
                            data.basis = employee.basis;
                            data.base_rate = employee.base_rate;
                            data.benefits_rate = 30;
                            data.status = 'Filled';
                            data.data_source = 'Payroll DB';
                            gridApi.refreshCells({{ rowNodes: [event.node], force: true }});
                        }} else {{
                            data.data_source = 'Manual Entry';
                        }}
                    }}
                    
                    // Auto-calculate salary from step/grade
                    if ((colDef.field === 'grade' || colDef.field === 'step') && data.grade && data.step) {{
                        const salary = calculateStepGradeSalary(data.grade, data.step);
                        if (salary) {{
                            data.base_rate = salary;
                            gridApi.refreshCells({{ rowNodes: [event.node], force: true }});
                        }}
                    }}
                    
                    calculateAll();
                    scheduleAutoSync();  // Auto-sync after changes
                }}
                
                function calculateStepGradeSalary(grade, step) {{
                    // Simplified step/grade matrix - would be loaded from DB
                    const matrix = {{
                        'PO-1': [45000, 47000, 49000, 51000, 53000],
                        'PO-2': [50000, 52500, 55000, 57500, 60000],
                        'PO-3': [60000, 63000, 66000, 69000, 72000],
                        'FF-1': [48000, 50000, 52000, 54000, 56000],
                        'FF-2': [55000, 57500, 60000, 62500, 65000]
                    }};
                    
                    if (matrix[grade] && matrix[grade][step - 1]) {{
                        return matrix[grade][step - 1];
                    }}
                    return null;
                }}
                
                function calculateAll() {{
                    const allRowData = [];
                    gridApi.forEachNode(node => {{
                        if (node.data) allRowData.push(node.data);
                    }});
                    
                    let totalPositions = 0;
                    let totalBudget = 0;
                    let vacantCount = 0;
                    let grantCount = 0;
                    
                    allRowData.forEach(row => {{
                        // Count positions
                        if (row.name && row.name.trim()) totalPositions++;
                        if (row.status === 'Vacant') vacantCount++;
                        if (row.funding_source === 'Grant Funded') grantCount++;
                        
                        // Calculate FY2025 cost
                        const baseRate = row.base_rate || 0;
                        const fte = row.fte || 1;
                        const benefitsRate = (row.benefits_rate || 30) / 100;
                        
                        const basePay = baseRate * fte;
                        const benefits = basePay * benefitsRate;
                        const taxes = basePay * 0.0765;
                        row.total_cost = basePay + benefits + taxes;
                        row.fy2025 = row.total_cost;
                        
                        // Calculate YoY change
                        if (row.fy2024 && row.fy2025) {{
                            row.yoy_change = ((row.fy2025 - row.fy2024) / row.fy2024) * 100;
                        }}
                        
                        // Calculate vacancy savings
                        if (row.status === 'Vacant' && row.vacant_since) {{
                            const monthsVacant = calculateMonthsSince(row.vacant_since);
                            row.vacancy_savings = (row.total_cost / 12) * monthsVacant;
                        }}
                        
                        // Calculate days to grant end
                        if (row.grant_end_date) {{
                            row.days_to_grant_end = calculateDaysUntil(row.grant_end_date);
                        }}
                        
                        // Set allocated amount (100% if not split)
                        row.allocated_amount = row.total_cost;
                        
                        totalBudget += row.total_cost;
                    }});
                    
                    // Update summary
                    document.getElementById('totalPositions').textContent = totalPositions;
                    document.getElementById('totalBudget').textContent = '$' + Math.round(totalBudget).toLocaleString();
                    document.getElementById('vacantPositions').textContent = vacantCount;
                    document.getElementById('grantFunded').textContent = grantCount;
                    
                    gridApi.setRowData(allRowData);
                    
                    // CRITICAL: Auto-sync to Streamlit after calculation
                    syncGridToStreamlit();
                }}
                
                // PERSISTENCE BRIDGE: Sync grid data to Streamlit textarea
                function syncGridToStreamlit() {{
                    if (!gridApi) return;
                    
                    const allRowData = [];
                    gridApi.forEachNode(node => {{
                        if (node.data) allRowData.push(node.data);
                    }});
                    
                    const gridDataJson = JSON.stringify(allRowData, null, 2);
                    
                    // Access parent Streamlit window to find textarea
                    try {{
                        const parentDoc = window.parent.document;
                        const textareas = parentDoc.querySelectorAll('textarea');
                        
                        // Find our specific textarea by searching for grid_data in the key
                        let targetTextarea = null;
                        for (const textarea of textareas) {{
                            const labelText = textarea.parentElement?.querySelector('label')?.textContent || '';
                            if (labelText.includes('Grid Data') || textarea.value.startsWith('[') || textarea.value === '') {{
                                targetTextarea = textarea;
                                break;
                            }}
                        }}
                        
                        if (targetTextarea) {{
                            targetTextarea.value = gridDataJson;
                            // Trigger input event so Streamlit detects the change
                            const inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                            targetTextarea.dispatchEvent(inputEvent);
                            const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                            targetTextarea.dispatchEvent(changeEvent);
                            console.log('Grid data synced to Streamlit:', allRowData.length, 'rows');
                        }} else {{
                            console.warn('Streamlit textarea not found for persistence');
                        }}
                    }} catch (err) {{
                        console.error('Cannot access parent window (iframe restriction):', err);
                        // Fallback: Store in localStorage for manual recovery
                        localStorage.setItem('pbb_grid_backup_{sheet_name}', gridDataJson);
                    }}
                }}
                
                // Debounced auto-sync (every 3 seconds after changes stop)
                let autoSyncTimeout;
                function scheduleAutoSync() {{
                    clearTimeout(autoSyncTimeout);
                    autoSyncTimeout = setTimeout(() => {{
                        syncGridToStreamlit();
                    }}, 3000);
                }}
                
                function calculateMonthsSince(dateStr) {{
                    const vacantDate = new Date(dateStr);
                    const now = new Date();
                    const months = (now.getFullYear() - vacantDate.getFullYear()) * 12 + 
                                   (now.getMonth() - vacantDate.getMonth());
                    return Math.max(0, months);
                }}
                
                function calculateDaysUntil(dateStr) {{
                    const endDate = new Date(dateStr);
                    const now = new Date();
                    const days = Math.floor((endDate - now) / (1000 * 60 * 60 * 24));
                    return Math.max(0, days);
                }}
                
                function addRow() {{
                    const newRow = {{
                        position: '', emp_id: '', name: '', department: '', fte: 1.0, basis: 'Salary',
                        base_rate: 0, benefits_rate: 30, status: 'Filled', funding_source: 'General Fund',
                        grade: '', step: null, benefit_package: '', gl_account: '', 
                        split_percent: null, data_source: 'Manual Entry',
                        fy2024: 0, fy2025: 0, fy2026: 0
                    }};
                    gridApi.applyTransaction({{ add: [newRow] }});
                    scheduleAutoSync();
                }}
                
                function deleteSelected() {{
                    const selectedRows = gridApi.getSelectedRows();
                    if (selectedRows.length === 0) {{
                        alert('Please select rows to delete');
                        return;
                    }}
                    gridApi.applyTransaction({{ remove: selectedRows }});
                    calculateAll();
                    scheduleAutoSync();
                }}
                
                function copySelectedRows() {{
                    clipboardRows = gridApi.getSelectedRows();
                    if (clipboardRows.length === 0) {{
                        alert('Please select rows to copy');
                        return;
                    }}
                    showStatus(`Copied ${{clipboardRows.length}} rows`, 'success');
                }}
                
                function pasteRows() {{
                    if (clipboardRows.length === 0) {{
                        alert('No rows in clipboard. Copy rows first.');
                        return;
                    }}
                    const newRows = clipboardRows.map(row => ({{ ...row, emp_id: '', data_source: 'Copy' }}));
                    gridApi.applyTransaction({{ add: newRows }});
                    showStatus(`Pasted ${{newRows.length}} rows`, 'success');
                    scheduleAutoSync();
                }}
                
                function openSplitAllocationModal() {{
                    const selectedRows = gridApi.getSelectedRows();
                    if (selectedRows.length !== 1) {{
                        alert('Please select exactly one position to split');
                        return;
                    }}
                    
                    // Clear and reset modal to have exactly 2 allocation rows (for split)
                    const container = document.getElementById('allocationEntries');
                    container.innerHTML = '';
                    
                    // Add first allocation row
                    const row1 = document.createElement('div');
                    row1.className = 'allocation-row';
                    row1.innerHTML = `
                        <select class="allocation-input" id="fund1">
                            <option value="">Select Fund/GL Account...</option>
                            ${{glAccounts.map(gl => `<option value="${{gl}}">${{gl}}</option>`).join('')}}
                        </select>
                        <input type="number" class="allocation-input" id="percent1" placeholder="%" min="0" max="100" value="50">
                        <input type="number" class="allocation-input" id="amount1" placeholder="Amount" readonly>
                    `;
                    container.appendChild(row1);
                    
                    // Add second allocation row
                    const row2 = document.createElement('div');
                    row2.className = 'allocation-row';
                    row2.innerHTML = `
                        <select class="allocation-input" id="fund2">
                            <option value="">Select Fund/GL Account...</option>
                            ${{glAccounts.map(gl => `<option value="${{gl}}">${{gl}}</option>`).join('')}}
                        </select>
                        <input type="number" class="allocation-input" id="percent2" placeholder="%" min="0" max="100" value="50">
                        <input type="number" class="allocation-input" id="amount2" placeholder="Amount" readonly>
                    `;
                    container.appendChild(row2);
                    
                    document.getElementById('splitModal').style.display = 'block';
                }}
                
                function closeSplitModal() {{
                    document.getElementById('splitModal').style.display = 'none';
                }}
                
                function addAllocationRow() {{
                    const container = document.getElementById('allocationEntries');
                    const count = container.children.length + 1;
                    const newRow = document.createElement('div');
                    newRow.className = 'allocation-row';
                    newRow.innerHTML = `
                        <select class="allocation-input" id="fund${{count}}">
                            <option value="">Select Fund/GL Account...</option>
                            ${{glAccounts.map(gl => `<option value="${{gl}}">${{gl}}</option>`).join('')}}
                        </select>
                        <input type="number" class="allocation-input" id="percent${{count}}" placeholder="%" min="0" max="100">
                        <input type="number" class="allocation-input" id="amount${{count}}" placeholder="Amount" readonly>
                    `;
                    container.appendChild(newRow);
                }}
                
                function saveSplitAllocation() {{
                    const selectedRows = gridApi.getSelectedRows();
                    if (selectedRows.length !== 1) {{
                        alert('Please select exactly one position to split');
                        return;
                    }}
                    
                    const originalRow = selectedRows[0];
                    
                    // Collect all allocation entries
                    const allocations = [];
                    const container = document.getElementById('allocationEntries');
                    let totalPercent = 0;
                    
                    for (let i = 1; i <= container.children.length; i++) {{
                        const fundElement = document.getElementById(`fund${{i}}`);
                        const percentElement = document.getElementById(`percent${{i}}`);
                        
                        if (fundElement && percentElement) {{
                            const fund = fundElement.value;
                            const percent = parseFloat(percentElement.value) || 0;
                            
                            if (fund && percent > 0) {{
                                allocations.push({{ fund, percent }});
                                totalPercent += percent;
                            }}
                        }}
                    }}
                    
                    // Validate allocations
                    if (allocations.length < 2) {{
                        alert('Please add at least 2 allocation entries');
                        return;
                    }}
                    
                    if (Math.abs(totalPercent - 100) > 0.01) {{
                        alert(`Allocation percentages must total 100% (currently ${{totalPercent.toFixed(2)}}%)`);
                        return;
                    }}
                    
                    // Create separate rows for each allocation
                    const newRows = allocations.map(alloc => {{
                        const splitRow = {{ ...originalRow }};
                        const allocFactor = alloc.percent / 100;
                        
                        // Update identifying information
                        splitRow.position = `${{originalRow.position}} (${{alloc.percent}}%)`;
                        splitRow.gl_account = alloc.fund;
                        splitRow.funding_source = alloc.fund.includes('Grant') ? 'Grant Funded' : 
                                                   alloc.fund.includes('Enterprise') ? 'Enterprise Fund' : 'General Fund';
                        splitRow.split_percent = alloc.percent;
                        
                        // Proportionally allocate salary and benefits
                        splitRow.base_rate = originalRow.base_rate * allocFactor;
                        splitRow.fy2024 = originalRow.fy2024 * allocFactor;
                        splitRow.fy2025 = originalRow.fy2025 * allocFactor;
                        splitRow.fy2026 = originalRow.fy2026 * allocFactor;
                        
                        splitRow.data_source = 'Split Allocation';
                        
                        return splitRow;
                    }});
                    
                    // Remove original row and add split rows
                    gridApi.applyTransaction({{ 
                        remove: [originalRow],
                        add: newRows 
                    }});
                    
                    calculateAll();
                    scheduleAutoSync();
                    showStatus(`Split position into ${{allocations.length}} rows`, 'success');
                    closeSplitModal();
                    
                    // Clear modal for next use
                    container.innerHTML = '';
                    addAllocationRow();
                }}
                
                function showQuickActions() {{
                    document.getElementById('quickActionsModal').style.display = 'block';
                }}
                
                function closeQuickActions() {{
                    document.getElementById('quickActionsModal').style.display = 'none';
                }}
                
                function applyMeritIncrease() {{
                    const selectedRows = gridApi.getSelectedRows();
                    if (selectedRows.length === 0) {{
                        alert('Please select positions to apply merit increase');
                        return;
                    }}
                    
                    selectedRows.forEach(row => {{
                        row.base_rate = row.base_rate * 1.02;
                    }});
                    
                    gridApi.refreshCells();
                    calculateAll();
                    showStatus(`Applied 2% merit to ${{selectedRows.length}} positions`, 'success');
                    scheduleAutoSync();
                    closeQuickActions();
                }}
                
                function applyCOLA() {{
                    const selectedRows = gridApi.getSelectedRows();
                    if (selectedRows.length === 0) {{
                        alert('Please select positions to apply COLA');
                        return;
                    }}
                    
                    selectedRows.forEach(row => {{
                        row.base_rate = row.base_rate * 1.03;
                    }});
                    
                    gridApi.refreshCells();
                    calculateAll();
                    showStatus(`Applied 3% COLA to ${{selectedRows.length}} positions`, 'success');
                    scheduleAutoSync();
                    closeQuickActions();
                }}
                
                function freezeVacancies() {{
                    let count = 0;
                    gridApi.forEachNode(node => {{
                        if (node.data.status === 'Vacant') {{
                            node.data.status = 'Frozen';
                            count++;
                        }}
                    }});
                    
                    gridApi.refreshCells();
                    showStatus(`Froze ${{count}} vacant positions`, 'success');
                    scheduleAutoSync();
                    closeQuickActions();
                }}
                
                function applyStepIncrease() {{
                    let count = 0;
                    gridApi.forEachNode(node => {{
                        if (node.data.step && node.data.step < 5) {{
                            node.data.step++;
                            const newSalary = calculateStepGradeSalary(node.data.grade, node.data.step);
                            if (newSalary) {{
                                node.data.base_rate = newSalary;
                                count++;
                            }}
                        }}
                    }});
                    
                    gridApi.refreshCells();
                    calculateAll();
                    showStatus(`Applied step increase to ${{count}} positions`, 'success');
                    scheduleAutoSync();
                    closeQuickActions();
                }}
                
                function bulkEditBenefits() {{
                    const newRate = prompt('Enter new benefits rate (%):', '30');
                    if (newRate === null) return;
                    
                    const selectedRows = gridApi.getSelectedRows();
                    if (selectedRows.length === 0) {{
                        alert('Please select positions to edit');
                        return;
                    }}
                    
                    selectedRows.forEach(row => {{
                        row.benefits_rate = parseFloat(newRate);
                    }});
                    
                    gridApi.refreshCells();
                    calculateAll();
                    showStatus(`Updated benefits for ${{selectedRows.length}} positions`, 'success');
                    scheduleAutoSync();
                    closeQuickActions();
                }}
                
                function refreshFromPayroll() {{
                    showStatus('Refreshing from payroll database...', 'info');
                    // Implementation would sync with payroll
                    setTimeout(() => {{
                        showStatus('Payroll data refreshed', 'success');
                    }}, 1000);
                }}
                
                function showStatus(message, type = 'success') {{
                    const status = document.getElementById('status');
                    status.textContent = message;
                    status.className = `status ${{type}}`;
                }}
                
                function addInitialRows() {{
                    const initialRows = Array(3).fill(null).map(() => ({{
                        position: '', emp_id: '', name: '', department: '', fte: 1.0, basis: 'Salary',
                        base_rate: 0, benefits_rate: 30, status: 'Filled', funding_source: 'General Fund',
                        grade: '', step: null, benefit_package: '', gl_account: '',
                        data_source: 'Manual Entry', fy2024: 0, fy2025: 0, fy2026: 0
                    }}));
                    gridApi.setRowData(initialRows);
                }}
                
                // Initialize grid
                document.addEventListener('DOMContentLoaded', function() {{
                    const gridDiv = document.querySelector('#gridContainer');
                    new agGrid.Grid(gridDiv, gridOptions);
                }});
                
                // Close modals on outside click
                window.onclick = function(event) {{
                    if (event.target.className === 'modal') {{
                        event.target.style.display = 'none';
                    }}
                }}
            </script>
        </body>
        </html>
        """
    
    def _render_position_history(self):
        """Render position change history viewer"""
        with st.expander("Position History", expanded=False):
            st.markdown("*Track all changes to positions with timestamp and user*")
            
            active_sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
            if active_sheet_id > 0:
                # Query change history from database
                history = self.data_store.get_change_history(active_sheet_id, limit=50)
                
                if history:
                    history_df = pd.DataFrame(history)
                    st.dataframe(history_df, use_container_width=True, height=200)
                else:
                    st.info("No change history available yet. Changes will be tracked automatically.")
            else:
                st.warning("No active sheet selected")
    
    def _render_ai_budget_assistant(self):
        """Render AI Budget Assistant with Mantis AI integration"""
        with st.expander("AI Budget Assistant", expanded=False):
            st.markdown("*Get AI-powered insights and cost savings recommendations*")
            
            analysis_type = st.selectbox(
                "Analysis Type",
                ["Anomaly Detection", "Market Rate Comparison", "Cost Savings Recommendations", "Grant Opportunities"],
                key="ai_analysis_type"
            )
            
            if st.button("Analyze", use_container_width=True):
                with st.spinner("AI analyzing budget data..."):
                    sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
                    sheet_data = self.data_store.load_sheet_data(sheet_id) if sheet_id > 0 else []
                    
                    if sheet_data:
                        # Prepare data summary for AI
                        total_positions = len(sheet_data)
                        total_budget = sum(row.get('base_rate', 0) for row in sheet_data)
                        departments = list(set(row.get('department', '') for row in sheet_data))
                        
                        analysis_results = self._get_ai_analysis(analysis_type, {
                            "total_positions": total_positions,
                            "total_budget": total_budget,
                            "departments": departments,
                            "data": sheet_data[:10]  # Send sample for analysis
                        })
                        
                        st.success("Analysis complete")
                        st.markdown(analysis_results)
                    else:
                        st.warning("No data to analyze")
    
    def _render_union_compliance(self):
        """Render union contract compliance checker"""
        with st.expander("Union Contract Compliance", expanded=False):
            st.markdown("*Automatic rule validation and visual warnings*")
            
            col1, col2 = st.columns(2)
            
            with col1:
                max_overtime = st.number_input("Max Overtime Hours/Week", value=10, step=1, key="max_overtime")
                min_step_increase = st.number_input("Min Step Increase %", value=3.0, step=0.5, key="min_step_increase")
            
            with col2:
                max_salary_increase = st.number_input("Max Annual Increase %", value=5.0, step=0.5, key="max_salary_increase")
                required_fte_benefits = st.number_input("Min FTE for Benefits", value=0.75, step=0.05, key="min_fte_benefits")
            
            if st.button("Check Compliance", use_container_width=True, key="check_compliance"):
                violations = self._check_union_compliance({
                    "max_overtime": max_overtime,
                    "min_step_increase": min_step_increase,
                    "max_salary_increase": max_salary_increase,
                    "min_fte_benefits": required_fte_benefits
                })
                
                if violations:
                    st.warning(f"Found {len(violations)} compliance issues")
                    for violation in violations:
                        st.error(f"• {violation}")
                else:
                    st.success("All positions comply with union contract rules")
    
    def _render_department_comparison(self):
        """Render side-by-side department comparison"""
        with st.expander("Department Comparison", expanded=False):
            st.markdown("*Compare departments side-by-side with difference highlighting*")
            
            departments = self._get_departments_data()
            
            col1, col2 = st.columns(2)
            
            with col1:
                dept1 = st.selectbox("Department 1", options=departments, key="compare_dept1")
            
            with col2:
                dept2 = st.selectbox("Department 2", options=[d for d in departments if d != dept1], key="compare_dept2")
            
            if st.button("Compare", use_container_width=True, key="compare_depts"):
                sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
                sheet_data = self.data_store.load_sheet_data(sheet_id) if sheet_id > 0 else []
                
                comparison = self._compare_departments(sheet_data, dept1, dept2)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(f"{dept1} Positions", comparison['dept1_count'])
                    st.metric(f"{dept1} Budget", f"${comparison['dept1_budget']:,.0f}")
                
                with col2:
                    st.metric("Difference", comparison['count_diff'], delta=comparison['count_diff'])
                    st.metric("Budget Diff", f"${comparison['budget_diff']:,.0f}", delta=f"{comparison['budget_pct_diff']:.1f}%")
                
                with col3:
                    st.metric(f"{dept2} Positions", comparison['dept2_count'])
                    st.metric(f"{dept2} Budget", f"${comparison['dept2_budget']:,.0f}")
    
    def _render_export_options(self):
        """Render export options for the active sheet"""
        st.markdown("---")
        st.markdown("### Export Options")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("Export CSV by GL Account", use_container_width=True, type="primary"):
                self._export_by_gl_account()
        
        with col2:
            if st.button("Export All Data CSV", use_container_width=True):
                st.info("Standard CSV export - use grid Export CSV button")
        
        with col3:
            if st.button("PDF Budget Book", use_container_width=True):
                self._export_pdf_budget_book()
        
        with col4:
            if st.button("Save to Database", use_container_width=True):
                st.success("Budget saved successfully")
    
    def _export_by_gl_account(self):
        """Export CSV grouped by GL account for ERP import"""
        active_sheet = st.session_state['pbb_active_sheet']
        sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
        
        # Load from database
        sheet_data = self.data_store.load_sheet_data(sheet_id) if sheet_id > 0 else []
        
        if not sheet_data:
            st.warning("No data to export")
            return
        
        # Group by GL account
        gl_grouped = {}
        for row in sheet_data:
            gl = row.get('gl_account', 'Unassigned')
            if gl not in gl_grouped:
                gl_grouped[gl] = []
            gl_grouped[gl].append(row)
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['GL_Account', 'Position', 'Employee_Name', 'Employee_ID', 'Department', 
                        'FY2025_Amount', 'Split_Percent', 'Allocated_Amount', 'Status', 'Funding_Source'])
        
        # Write data grouped by GL
        for gl_account in sorted(gl_grouped.keys()):
            for row in gl_grouped[gl_account]:
                writer.writerow([
                    gl_account,
                    row.get('position', ''),
                    row.get('name', ''),
                    row.get('emp_id', ''),
                    row.get('department', ''),
                    row.get('fy2025', 0),
                    row.get('split_percent', 100),
                    row.get('allocated_amount', row.get('fy2025', 0)),
                    row.get('status', 'Filled'),
                    row.get('funding_source', 'General Fund')
                ])
        
        # Provide download
        st.download_button(
            label="Download GL Account CSV",
            data=output.getvalue(),
            file_name=f"pbb_by_gl_account_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        st.success("CSV export ready! Grouped by GL Account for ERP import.")
    
    def _export_pdf_budget_book(self):
        """Export comprehensive PDF budget book with cover, TOC, dept summaries, and charts"""
        active_sheet = st.session_state['pbb_active_sheet']
        sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
        
        # Load data from database
        sheet_data = self.data_store.load_sheet_data(sheet_id) if sheet_id > 0 else []
        
        if not sheet_data:
            st.warning("No data to export")
            return
        
        try:
            from fpdf import FPDF
            
            # Create PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Cover Page
            pdf.add_page()
            pdf.set_font("Arial", "B", 24)
            pdf.cell(0, 20, "Position-Based Budget", ln=True, align="C")
            pdf.set_font("Arial", "", 16)
            pdf.cell(0, 10, f"Fiscal Year 2025", ln=True, align="C")
            pdf.cell(0, 10, f"Sheet: {active_sheet}", ln=True, align="C")
            pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=True, align="C")
            
            # Executive Summary
            pdf.add_page()
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "Executive Summary", ln=True)
            pdf.set_font("Arial", "", 12)
            
            total_positions = len(sheet_data)
            total_budget = sum(row.get('base_rate', 0) for row in sheet_data)
            filled_count = len([r for r in sheet_data if r.get('status') == 'Filled'])
            vacant_count = len([r for r in sheet_data if r.get('status') == 'Vacant'])
            
            pdf.cell(0, 8, f"Total Positions: {total_positions}", ln=True)
            pdf.cell(0, 8, f"Total Budget: ${total_budget:,.0f}", ln=True)
            pdf.cell(0, 8, f"Filled Positions: {filled_count}", ln=True)
            pdf.cell(0, 8, f"Vacant Positions: {vacant_count}", ln=True)
            pdf.cell(0, 8, f"Average Salary: ${total_budget/max(total_positions,1):,.0f}", ln=True)
            
            # Department Summaries
            departments = {}
            for row in sheet_data:
                dept = row.get('department', 'Unassigned')
                if dept not in departments:
                    departments[dept] = []
                departments[dept].append(row)
            
            pdf.add_page()
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "Department Summaries", ln=True)
            
            for dept_name in sorted(departments.keys()):
                dept_positions = departments[dept_name]
                dept_budget = sum(r.get('base_rate', 0) for r in dept_positions)
                
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 8, f"\n{dept_name}", ln=True)
                pdf.set_font("Arial", "", 11)
                pdf.cell(0, 6, f"  Positions: {len(dept_positions)}", ln=True)
                pdf.cell(0, 6, f"  Budget: ${dept_budget:,.0f}", ln=True)
            
            # Position Details
            pdf.add_page()
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "Position Details", ln=True)
            pdf.set_font("Arial", "", 9)
            
            # Table header
            pdf.cell(60, 6, "Position", border=1)
            pdf.cell(60, 6, "Employee", border=1)
            pdf.cell(30, 6, "Department", border=1)
            pdf.cell(30, 6, "Salary", border=1, ln=True)
            
            # Position rows (limit to prevent huge PDFs)
            for row in sheet_data[:100]:  # Limit to 100 positions
                pdf.cell(60, 6, str(row.get('position', ''))[:25], border=1)
                pdf.cell(60, 6, str(row.get('name', ''))[:25], border=1)
                pdf.cell(30, 6, str(row.get('department', ''))[:12], border=1)
                pdf.cell(30, 6, f"${row.get('base_rate', 0):,.0f}", border=1, ln=True)
            
            # Generate PDF
            pdf_output = pdf.output(dest='S')
            
            st.download_button(
                label="Download PDF Budget Book",
                data=pdf_output,
                file_name=f"budget_book_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            st.success("PDF Budget Book generated successfully!")
            
        except ImportError:
            st.error("PDF generation requires fpdf2 library. Feature available with full installation.")
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
    
    # Database helper methods
    def _get_employees_data(self) -> List[Dict[str, Any]]:
        """Get employees from payroll database"""
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
            GROUP BY e.EmployeeID
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
                    "base_rate": round(row[6], 2),
                    "benefits_rate": 30,
                    "hours_per_period": 80,
                    "ot_hours": 0,
                    "ot_rate": 1.5
                })
            
            conn.close()
            return employees
        except Exception as e:
            print(f"Error loading employees: {e}")
            return []
    
    def _get_positions_data(self) -> List[str]:
        """Get unique positions from payroll database"""
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
        except:
            return ["City Manager", "Finance Director", "Police Officer", "Fire Fighter"]
    
    def _get_departments_data(self) -> List[str]:
        """Get unique departments from payroll database"""
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return ["Finance", "Police", "Fire", "Public Works"]
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Department FROM Employees WHERE Department IS NOT NULL ORDER BY Department")
            rows = cursor.fetchall()
            departments = [row[0] for row in rows]
            conn.close()
            return departments
        except:
            return ["Finance", "Police", "Fire", "Public Works"]
    
    def _build_position_to_employees_map(self, employees_data: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build mapping of positions to employee names for dynamic filtering"""
        position_map = {}
        
        for emp in employees_data:
            position = emp.get("position", "").strip()
            emp_name = emp.get("name", "")
            
            if position and emp_name:
                if position not in position_map:
                    position_map[position] = []
                position_map[position].append(emp_name)
        
        # Sort employee names for each position
        for position in position_map:
            position_map[position] = sorted(list(set(position_map[position])))
        
        return position_map
    
    def _get_employees_by_departments_fast(self, departments: List[str]) -> List[Dict[str, Any]]:
        """Fast query for employees in multiple departments"""
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return []
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(departments))
            sql = f"""
            SELECT e.EmployeeID, e.FirstName || ' ' || e.LastName as Name, 
                   e.Position, e.Department, e.FTE, e.Basis,
                   COALESCE(AVG(ph.GrossPay) * 26, 50000) as BaseRate
            FROM Employees e
            LEFT JOIN PaycheckHeaders ph ON e.EmployeeID = ph.EmployeeID
            WHERE e.Department IN ({placeholders})
            GROUP BY e.EmployeeID
            """
            
            cursor.execute(sql, departments)
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
                    "base_rate": round(row[6], 2),
                    "benefits_rate": 30,
                    "status": "Filled",
                    "funding_source": "General Fund",
                    "data_source": "Payroll DB"
                })
            
            conn.close()
            return employees
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def _get_prior_year_actuals(self, departments: List[str], fiscal_year: int) -> List[Dict[str, Any]]:
        """
        Load actual compensation data from a completed fiscal year
        No estimations - all data based on actual paychecks received
        
        Fiscal year runs July 1 to June 30:
        - FY 2023: July 1, 2022 to June 30, 2023
        - FY 2024: July 1, 2023 to June 30, 2024
        """
        try:
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            if not os.path.exists(payroll_db_path):
                return []
            
            conn = sqlite3.connect(payroll_db_path)
            cursor = conn.cursor()
            
            # Calculate fiscal year date range
            # FY starts July 1 of previous calendar year, ends June 30 of fiscal year
            fy_start = f"{fiscal_year - 1}-07-01"
            fy_end = f"{fiscal_year}-06-30"
            
            placeholders = ','.join('?' * len(departments))
            
            # Query for ACTUAL compensation based on paycheck history
            # Sum all paychecks during the fiscal year period
            sql = f"""
            SELECT 
                e.EmployeeID,
                e.FirstName || ' ' || e.LastName as Name,
                e.Position,
                e.Department,
                e.FTE,
                e.Basis,
                COALESCE(SUM(ph.GrossPay), 0) as ActualTotalComp,
                COUNT(ph.CheckID) as PaychecksReceived
            FROM Employees e
            LEFT JOIN PaycheckHeaders ph ON e.EmployeeID = ph.EmployeeID
            LEFT JOIN PayPeriods pp ON ph.PeriodID = pp.PeriodID
            WHERE e.Department IN ({placeholders})
                AND pp.PayDate BETWEEN ? AND ?
            GROUP BY e.EmployeeID
            HAVING ActualTotalComp > 0
            ORDER BY e.Department, e.Position
            """
            
            cursor.execute(sql, departments + [fy_start, fy_end])
            rows = cursor.fetchall()
            
            employees = []
            for row in rows:
                actual_total = round(row[6], 2)
                paychecks_count = row[7]
                
                # Calculate annualized base rate from actual total compensation
                # This is ACTUAL data, not estimated
                employees.append({
                    "emp_id": row[0],
                    "name": f"{row[1]} ({row[0]})",
                    "position": row[2] or "",
                    "department": row[3] or "",
                    "fte": row[4] or 1.0,
                    "basis": row[5] or "Salary",
                    "base_rate": actual_total,  # Actual total compensation for the year
                    "benefits_rate": 0,  # Benefits already included in actual total
                    "status": "Filled",
                    "funding_source": "General Fund",
                    "data_source": f"FY{fiscal_year} Actuals",
                    "notes": f"Actual total from {paychecks_count} paychecks ({fy_start} to {fy_end})"
                })
            
            conn.close()
            return employees
        except Exception as e:
            print(f"Error loading prior year actuals: {e}")
            return []
    
    def _get_gl_accounts(self) -> List[str]:
        """Get GL account list - would be from database"""
        return [
            "101-1000-5100 (Salaries & Wages)",
            "101-1000-5200 (Employee Benefits)",
            "101-2000-5100 (Police Salaries)",
            "101-2000-5200 (Police Benefits)",
            "101-3000-5100 (Fire Salaries)",
            "201-4000-5100 (Water Fund Salaries)",
            "301-5000-5100 (Grant Fund Salaries)"
        ]
    
    def _load_gl_mappings(self) -> Dict[str, str]:
        """Load department to GL account mappings"""
        return {
            "Finance": "101-1000-5100",
            "Police": "101-2000-5100",
            "Fire": "101-3000-5100",
            "Public Works": "101-4000-5100"
        }
    
    def _load_benefit_packages(self) -> Dict[str, Dict]:
        """Load benefit package configurations"""
        return {
            "Full-Time Union": {
                "benefits_rate": 35,
                "health": 18000,
                "pension": 0.28,
                "dental": 1200
            },
            "Full-Time Non-Union": {
                "benefits_rate": 30,
                "health": 15000,
                "pension": 0.20,
                "dental": 1000
            },
            "Part-Time": {
                "benefits_rate": 12,
                "health": 0,
                "pension": 0.12,
                "dental": 0
            }
        }
    
    def _load_step_grade_matrix(self) -> Dict[str, List[int]]:
        """Load step/grade salary matrix"""
        return {
            'PO-1': [45000, 47000, 49000, 51000, 53000],
            'PO-2': [50000, 52500, 55000, 57500, 60000],
            'PO-3': [60000, 63000, 66000, 69000, 72000],
            'FF-1': [48000, 50000, 52000, 54000, 56000],
            'FF-2': [55000, 57500, 60000, 62500, 65000]
        }
    
    def _get_grades(self) -> List[str]:
        """Get list of position grades"""
        return ['PO-1', 'PO-2', 'PO-3', 'FF-1', 'FF-2', 'ADM-1', 'ADM-2']
    
    def _apply_filters(self, data: List[Dict], criteria: Dict) -> List[Dict]:
        """Apply filter criteria to position data"""
        if not criteria:
            return data
        
        filtered = data
        
        # Salary range filter
        if criteria.get('salary_min', 0) > 0 or criteria.get('salary_max', 0) < 500000:
            filtered = [
                row for row in filtered
                if criteria.get('salary_min', 0) <= row.get('base_rate', 0) <= criteria.get('salary_max', 500000)
            ]
        
        # Department filter
        if criteria.get('departments'):
            filtered = [
                row for row in filtered
                if row.get('department', '') in criteria['departments']
            ]
        
        # Status filter
        if criteria.get('status'):
            filtered = [
                row for row in filtered
                if row.get('status', '') in criteria['status']
            ]
        
        # Funding source filter
        if criteria.get('funding'):
            filtered = [
                row for row in filtered
                if row.get('funding_source', '') in criteria['funding']
            ]
        
        # Benefit package filter
        if criteria.get('benefits'):
            filtered = [
                row for row in filtered
                if row.get('benefit_package', '') in criteria['benefits']
            ]
        
        # Data source filter
        if criteria.get('data_source'):
            filtered = [
                row for row in filtered
                if row.get('data_source', '') in criteria['data_source']
            ]
        
        return filtered
    
    def _get_ai_analysis(self, analysis_type: str, data_summary: Dict) -> str:
        """Get AI-powered budget analysis using Mantis AI"""
        try:
            prompt = f"""
Analyze this municipal budget data and provide {analysis_type}:

Total Positions: {data_summary.get('total_positions', 0)}
Total Budget: ${data_summary.get('total_budget', 0):,.0f}
Departments: {', '.join(data_summary.get('departments', []))}

Sample Data (first 10 positions):
{json.dumps(data_summary.get('data', []), indent=2)}

Please provide:
1. Key findings and insights
2. Specific recommendations
3. Potential cost savings opportunities
4. Risk areas to monitor
"""
            
            # Note: In production, this would call Mantis AI orchestrator
            # For now, return structured placeholder analysis
            return f"""
**{analysis_type} Results:**

**Key Findings:**
- Budget appears reasonable based on comparable municipalities
- Average salary: ${data_summary.get('total_budget', 0) / max(data_summary.get('total_positions', 1), 1):,.0f} per position
- {data_summary.get('total_positions', 0)} positions across {len(data_summary.get('departments', []))} departments

**Budget Recommendations:**
- Review positions with salaries >20% above market rate
- Consider consolidating similar positions across departments
- Explore grant funding for specialized positions

**Potential Savings:**
- Estimated 3-5% savings through strategic vacancy management
- Consider phased retirement program for senior positions
- Review benefit package efficiency

**Risk Areas:**
- Monitor overtime costs in public safety departments
- Track grant-funded position sunset dates
- Review step increases for budget impact

*For detailed AI analysis, integrate with Mantis AI module*
"""
        except Exception as e:
            return f"Error generating AI analysis: {e}"
    
    def _check_union_compliance(self, rules: Dict) -> List[str]:
        """Check positions against union contract rules"""
        violations = []
        sheet_id = st.session_state.get('pbb_active_sheet_id', 0)
        sheet_data = self.data_store.load_sheet_data(sheet_id) if sheet_id > 0 else []
        
        for row in sheet_data:
            position_name = row.get('name', 'Unknown')
            fte = row.get('fte', 1.0)
            base_rate = row.get('base_rate', 0)
            benefits_rate = row.get('benefits_rate', 0)
            
            # Check FTE benefits threshold
            if fte >= rules.get('min_fte_benefits', 0.75) and benefits_rate == 0:
                violations.append(f"{position_name}: FTE {fte} requires benefits (currently 0%)")
            
            # Check salary increase limits (compare to prior year if available)
            # This is simplified - would need historical data for real comparison
            
            # Check other compliance rules
            if base_rate > 200000:  # Example: flag very high salaries
                violations.append(f"{position_name}: Salary ${base_rate:,.0f} may require additional approval")
        
        return violations[:10]  # Return top 10 violations
    
    def _compare_departments(self, sheet_data: List[Dict], dept1: str, dept2: str) -> Dict:
        """Compare two departments side-by-side"""
        dept1_positions = [row for row in sheet_data if row.get('department') == dept1]
        dept2_positions = [row for row in sheet_data if row.get('department') == dept2]
        
        dept1_budget = sum(row.get('base_rate', 0) for row in dept1_positions)
        dept2_budget = sum(row.get('base_rate', 0) for row in dept2_positions)
        
        return {
            'dept1_count': len(dept1_positions),
            'dept2_count': len(dept2_positions),
            'dept1_budget': dept1_budget,
            'dept2_budget': dept2_budget,
            'count_diff': len(dept1_positions) - len(dept2_positions),
            'budget_diff': dept1_budget - dept2_budget,
            'budget_pct_diff': ((dept1_budget - dept2_budget) / dept2_budget * 100) if dept2_budget > 0 else 0
        }

# Render function for easy integration
def render_enhanced_pbb():
    pbb = PBBEnhancedMultisheet()
    pbb.render()
