# PBB UI Spreadsheet - Main Spreadsheet Interface
# Position-Based Budgeting spreadsheet UI rendering (~450 lines)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Any
import plotly.express as px
from modules.navi.payroll_live_adapter import _get_connection_type, _read_sql, get_positions

class PBBSpreadsheetUI:
    """Position-Based Budgeting spreadsheet user interface"""
    
    def __init__(self, core_instance, calculations_instance):
        self.core = core_instance
        self.calculations = calculations_instance
    
    def render_spreadsheet_tab(self):
        """Render the main spreadsheet interface tab"""
        
        # Use enhanced hybrid interface as default
        try:
            from .pbb_hybrid_interface import PBBHybridInterface
            hybrid_interface = PBBHybridInterface()
            hybrid_interface.render_hybrid_spreadsheet()
            return
        except Exception as e:
            st.error(f"Error loading enhanced interface: {e}")
            st.info("Loading fallback interface...")
        
        # Fallback to original interface  
        st.markdown("### Excel-Style Position-Based Budgeting Spreadsheet")
        st.markdown("**Blue columns** are editable inputs. **Grey columns** are automatically calculated.")
        
        # Initialize session state for the dataframe if it doesn't exist
        if 'pbb_dataframe' not in st.session_state:
            st.session_state.pbb_dataframe = self.core._create_initial_dataframe()
        
        # Control panel with organized sections
        st.markdown("---")
        st.markdown("### Spreadsheet Controls")
        
        # Get department options from database
        department_options = []
        try:
            connection_type = _get_connection_type()
            if connection_type == "sqlite":
                dept_sql = "SELECT DISTINCT Department FROM Employees WHERE Department IS NOT NULL ORDER BY Department"
                dept_df, _ = _read_sql(dept_sql, ())
                if not dept_df.empty:
                    department_options = dept_df['Department'].tolist()
        except Exception as e:
            st.warning(f"Could not load departments: {e}")

        # Row 1: Row Management
        st.markdown("**Row Management**")
        row_col1, row_col2, row_col3, row_col4 = st.columns([2, 2, 2, 2])
        with row_col1:
            if st.button("Add Row", help="Add a new empty row to the spreadsheet", use_container_width=True):
                new_row = self.core._create_empty_row_dict()
                st.session_state.pbb_dataframe = pd.concat([
                    st.session_state.pbb_dataframe, 
                    pd.DataFrame([new_row])
                ], ignore_index=True)
                st.rerun()
        with row_col2:
            if st.button("Clear All", help="Clear all rows in spreadsheet", use_container_width=True):
                st.session_state.pbb_dataframe = self.core._create_initial_dataframe()
                st.rerun()
        with row_col3:
            total_rows = len(st.session_state.pbb_dataframe)
            st.write(f"**Total Rows:** {total_rows}")
        with row_col4:
            show_employee_viz = st.checkbox("Show Employee Data", value=False)

        # Row 2: Auto-Mapping Tools
        st.markdown("**Auto-Mapping Tools**")
        auto_col1, auto_col2 = st.columns([1, 1])
        with auto_col1:
            if st.button("Auto-Map All Employees", help="Automatically populate spreadsheet with all employees from database", use_container_width=True):
                self.core._auto_map_all_employees()
                st.rerun()
        with auto_col2:
            # Department-specific auto-mapping in expandable section
            with st.expander("Department-Specific Auto-Mapping"):
                selected_department = st.selectbox(
                    "Select Department",
                    options=[''] + department_options,
                    help="Choose a department to auto-map only employees from that department"
                )
                if st.button("Auto-Map Department", help="Auto-map only employees from selected department", disabled=not selected_department, use_container_width=True):
                    if selected_department:
                        self.core._auto_map_department_employees(selected_department)
                        st.rerun()
        
        # Show employee visualization if requested
        if show_employee_viz:
            self.core._render_employee_visualization()
        
        # Add custom CSS for column header styling
        st.markdown("""
        <style>
        /* Input columns - Blue headers */
        [data-testid="stDataFrameResizable"] thead th:nth-child(1),  /* Position */
        [data-testid="stDataFrameResizable"] thead th:nth-child(2),  /* EmpID */
        [data-testid="stDataFrameResizable"] thead th:nth-child(3),  /* Name */
        [data-testid="stDataFrameResizable"] thead th:nth-child(4),  /* Department */
        [data-testid="stDataFrameResizable"] thead th:nth-child(5),  /* FTE */
        [data-testid="stDataFrameResizable"] thead th:nth-child(6),  /* Basis */
        [data-testid="stDataFrameResizable"] thead th:nth-child(7),  /* BaseRate */
        [data-testid="stDataFrameResizable"] thead th:nth-child(8),  /* Grade */
        [data-testid="stDataFrameResizable"] thead th:nth-child(9),  /* Step */
        [data-testid="stDataFrameResizable"] thead th:nth-child(10), /* COLA */
        [data-testid="stDataFrameResizable"] thead th:nth-child(11), /* BenefitsRate */
        [data-testid="stDataFrameResizable"] thead th:nth-child(12), /* HoursPerPeriod */
        [data-testid="stDataFrameResizable"] thead th:nth-child(13), /* OTHours */
        [data-testid="stDataFrameResizable"] thead th:nth-child(14), /* OTRate */
        [data-testid="stDataFrameResizable"] thead th:nth-child(15), /* VacancyMonths */
        [data-testid="stDataFrameResizable"] thead th:nth-child(16), /* StipendAnnual */
        [data-testid="stDataFrameResizable"] thead th:nth-child(17)  /* BenefitsMode */
        {
            background-color: #E3F2FD !important;
            color: #1976D2 !important;
            font-weight: bold !important;
            border-bottom: 3px solid #2196F3 !important;
        }
        
        /* Calculated columns - Grey headers */
        [data-testid="stDataFrameResizable"] thead th:nth-child(15), /* FundedMonths */
        [data-testid="stDataFrameResizable"] thead th:nth-child(16), /* WagesBase */
        [data-testid="stDataFrameResizable"] thead th:nth-child(17), /* WagesOT */
        [data-testid="stDataFrameResizable"] thead th:nth-child(18), /* Stipends */
        [data-testid="stDataFrameResizable"] thead th:nth-child(19), /* Benefits */
        [data-testid="stDataFrameResizable"] thead th:nth-child(20), /* Taxes */
        [data-testid="stDataFrameResizable"] thead th:nth-child(21)  /* TotalCost */
        {
            background-color: #F5F5F5 !important;
            color: #757575 !important;
            font-weight: bold !important;
            border-bottom: 3px solid #BDBDBD !important;
        }
        
        /* Legend styling */
        .column-legend {
            display: flex;
            gap: 20px;
            margin: 10px 0;
            font-size: 14px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .legend-color {
            width: 20px;
            height: 15px;
            border-radius: 3px;
            border: 1px solid #ddd;
        }
        
        .input-color {
            background-color: #E3F2FD;
        }
        
        .calculated-color {
            background-color: #F5F5F5;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Add column legend
        st.markdown("""
        <div class="column-legend">
            <div class="legend-item">
                <div class="legend-color input-color"></div>
                <span><strong>Blue Headers:</strong> Input Columns (Editable)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color calculated-color"></div>
                <span><strong>Grey Headers:</strong> Calculated Columns (Auto-computed)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Setup for dynamic employee filtering based on position
        position_to_employees = self._build_position_employee_mapping()
        all_names, all_ids = self._get_all_employee_options()
        
        # Configure spreadsheet columns
        column_order = [
            'Position', 'EmpID', 'Name', 'Department', 'FTE', 'Basis', 'BaseRate', 
            'Grade', 'Step', 'COLA', 'BenefitsRate', 'HoursPerPeriod', 'OTHours', 
            'OTRate', 'VacancyMonths', 'StipendAnnual', 'BenefitsMode',
            'FundedMonths', 'BaseWithCOLA', 'WagesBase', 'WagesOT', 'Stipends', 
            'Benefits', 'Taxes', 'TotalCost', 'AnnualCost', 'EffectiveRate'
        ]
        
        # Get filtered employee options based on current position selections
        filtered_names, filtered_ids = self._get_filtered_employee_options(
            st.session_state.pbb_dataframe, position_to_employees, all_names, all_ids
        )
        
        # Column configuration for the spreadsheet
        column_config = {
            "Position": st.column_config.SelectboxColumn(
                "Position",
                help="Select position title",
                options=[''] + [pos for pos in self.core.positions_data['Title'].tolist() if pos],
                width="large"
            ),
            "EmpID": st.column_config.SelectboxColumn(
                "Employee ID",
                help="Select employee ID (filtered by position)",
                options=filtered_ids,
                width="medium"
            ),
            "Name": st.column_config.SelectboxColumn(
                "Name",
                help="Select employee name (filtered by position)", 
                options=filtered_names,
                width="large"
            ),
            "Department": st.column_config.TextColumn("Department", width="medium"),
            "FTE": st.column_config.NumberColumn("FTE", min_value=0.0, max_value=2.0, step=0.1, format="%.2f", width="small"),
            "Basis": st.column_config.SelectboxColumn(
                "Basis",
                help="Salary or Hourly",
                options=["Salary", "Hourly"],
                width="small"
            ),
            "BaseRate": st.column_config.NumberColumn("Base Rate", format="$%.2f", width="medium"),
            "Grade": st.column_config.TextColumn("Grade", width="small"),
            "Step": st.column_config.NumberColumn("Step", min_value=1, max_value=20, step=1, width="small"),
            "COLA": st.column_config.NumberColumn("COLA %", min_value=0.0, max_value=10.0, step=0.1, format="%.1f", width="small"),
            "BenefitsRate": st.column_config.NumberColumn("Benefits %", min_value=0.0, max_value=50.0, step=1.0, format="%.1f", width="small"),
            "HoursPerPeriod": st.column_config.NumberColumn("Hours/PP", min_value=0, max_value=120, step=1, width="small"),
            "OTHours": st.column_config.NumberColumn("OT Hours", min_value=0, max_value=40, step=1, width="small"),
            "OTRate": st.column_config.NumberColumn("OT Rate", min_value=1.0, max_value=3.0, step=0.1, format="%.1f", width="small"),
            "VacancyMonths": st.column_config.NumberColumn("Vacant Mo.", min_value=0, max_value=12, step=0.5, format="%.1f", width="small"),
            "StipendAnnual": st.column_config.NumberColumn("Stipend", format="$%.2f", width="medium"),
            "BenefitsMode": st.column_config.SelectboxColumn(
                "Ben. Mode",
                help="Benefits calculation mode",
                options=["standard", "elections"],
                width="small"
            ),
            # Calculated columns (read-only appearance)
            "FundedMonths": st.column_config.NumberColumn("Fund Mo.", format="%.1f", width="small"),
            "BaseWithCOLA": st.column_config.NumberColumn("Base+COLA", format="$%.2f", width="medium"),
            "WagesBase": st.column_config.NumberColumn("Base Wages", format="$%.2f", width="medium"),
            "WagesOT": st.column_config.NumberColumn("OT Wages", format="$%.2f", width="medium"),
            "Stipends": st.column_config.NumberColumn("Stipends", format="$%.2f", width="medium"),
            "Benefits": st.column_config.NumberColumn("Benefits", format="$%.2f", width="medium"),
            "Taxes": st.column_config.NumberColumn("Taxes", format="$%.2f", width="medium"),
            "TotalCost": st.column_config.NumberColumn("Total Cost", format="$%.2f", width="medium"),
            "AnnualCost": st.column_config.NumberColumn("Annual Cost", format="$%.2f", width="medium"),
            "EffectiveRate": st.column_config.NumberColumn("Eff. Rate", format="$%.2f", width="medium")
        }
        
        # Row deletion controls (only show if there are rows with data)
        if len(st.session_state.pbb_dataframe) > 0:
            # Only show delete controls if user has selected rows
            if 'selected_rows' in st.session_state and st.session_state.selected_rows:
                st.markdown("---")
                del_col1, del_col2 = st.columns([1, 3])
                with del_col1:
                    if st.button("Delete Selected Rows", help="Delete all checked rows from the spreadsheet", use_container_width=True):
                        # Remove selected rows
                        st.session_state.pbb_dataframe = st.session_state.pbb_dataframe.drop(
                            index=st.session_state.selected_rows
                        ).reset_index(drop=True)
                        st.session_state.selected_rows = []
                        st.rerun()
                with del_col2:
                    selected_count = len(st.session_state.selected_rows)
                    st.info(f"{selected_count} row(s) selected for deletion")
        
        # Apply any pending autofill logic to session state before displaying
        if 'pbb_pending_autofill' not in st.session_state:
            st.session_state.pbb_pending_autofill = False
        
        # Add row selection checkboxes and data editor
        if len(st.session_state.pbb_dataframe) > 0:
            # Add a selection column to the dataframe for display
            display_df = st.session_state.pbb_dataframe.copy()
            display_df.insert(0, 'Select', False)
            
            # Update column config to include the selection column
            selection_column_config = {
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Check to select row for deletion",
                    width="small"
                )
            }
            selection_column_config.update(column_config)
            
            # Display order with selection column first
            selection_column_order = ['Select'] + column_order
            
            # Editable spreadsheet with row selection
            edited_df = st.data_editor(
                display_df[selection_column_order],
                column_config=selection_column_config,
                use_container_width=True,
                num_rows="dynamic",
                key="pbb_editor",
                height=600,
                hide_index=True
            )
            
            # Store selected rows for deletion
            if 'Select' in edited_df.columns:
                st.session_state.selected_rows = edited_df.index[edited_df['Select']].tolist()
                # Remove the Select column for processing
                edited_df = edited_df.drop('Select', axis=1)
            
        else:
            # No rows to display, create empty dataframe for processing
            edited_df = pd.DataFrame(columns=column_order)
        
        # Update session state and recalculate when data changes
        if not edited_df.empty and len(edited_df) > 0:
            # Reorder the edited dataframe to match the original structure
            edited_df_reordered = edited_df.reindex(columns=st.session_state.pbb_dataframe.columns)
            
            # Check if this is different from current session state
            if not edited_df_reordered.equals(st.session_state.pbb_dataframe):
                # Check if ONLY Name or EmpID columns changed (not manual fields)
                name_empid_changed = self._check_name_empid_changes_only(edited_df_reordered, st.session_state.pbb_dataframe)
                
                # Debug logging to track what's happening
                changed_columns = []
                for idx in edited_df_reordered.index:
                    if idx < len(st.session_state.pbb_dataframe):
                        for col in edited_df_reordered.columns:
                            old_val = st.session_state.pbb_dataframe.iloc[idx].get(col)
                            new_val = edited_df_reordered.iloc[idx].get(col)
                            if str(old_val) != str(new_val):
                                changed_columns.append(col)
                
                if changed_columns:
                    print(f"DEBUG: Changed columns: {list(set(changed_columns))}")
                    print(f"DEBUG: Name/EmpID changed: {name_empid_changed}")
                
                if name_empid_changed:
                    # Apply autofill only for employee name/ID changes
                    autofilled_df = self._apply_selective_autofill(edited_df_reordered, st.session_state.pbb_dataframe)
                    
                    # Recalculate and update session state
                    final_df = self.calculations._recalculate_all_rows(autofilled_df)
                    st.session_state.pbb_dataframe = final_df
                    self._autosave_export_data()
                    
                    # Refresh UI for autofill changes
                    print("Employee autofill applied, refreshing...")
                    st.rerun()
                else:
                    # Just manual field edits - update calculations without autofill or rerun
                    print("DEBUG: Manual field edit detected, no UI refresh")
                    final_df = self.calculations._recalculate_all_rows(edited_df_reordered)
                    st.session_state.pbb_dataframe = final_df
                    self._autosave_export_data()
        
        # Summary section
        st.markdown("---")
        st.markdown("### Budget Summary")
        
        # Calculate totals using the session state dataframe
        df_for_totals = st.session_state.pbb_dataframe
        total_positions = len(df_for_totals[df_for_totals['Position'].fillna('') != ''])
        total_fte = df_for_totals['FTE'].sum()
        total_wages = df_for_totals['WagesBase'].sum() + df_for_totals['WagesOT'].sum()
        total_benefits = df_for_totals['Benefits'].sum()
        total_taxes = df_for_totals['Taxes'].sum()
        total_cost = df_for_totals['TotalCost'].sum()
        
        # Use HTML for custom small font size metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="font-size: 8px; color: #666; margin-bottom: 2px;">Positions</div>
                <div style="font-size: 12px; font-weight: bold; color: #262730;">{total_positions:,}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="font-size: 8px; color: #666; margin-bottom: 2px;">Total FTE</div>
                <div style="font-size: 12px; font-weight: bold; color: #262730;">{total_fte:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="font-size: 8px; color: #666; margin-bottom: 2px;">Total Wages</div>
                <div style="font-size: 12px; font-weight: bold; color: #262730;">${total_wages:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="font-size: 8px; color: #666; margin-bottom: 2px;">Total Benefits</div>
                <div style="font-size: 12px; font-weight: bold; color: #262730;">${total_benefits:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="font-size: 8px; color: #666; margin-bottom: 2px;">Total Taxes</div>
                <div style="font-size: 12px; font-weight: bold; color: #262730;">${total_taxes:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col6:
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;">
                <div style="font-size: 8px; color: #666; margin-bottom: 2px;">Total Cost</div>
                <div style="font-size: 12px; font-weight: bold; color: #262730;">${total_cost:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
    
    def _build_position_employee_mapping(self):
        """Build mapping of positions to their employees for filtering"""
        try:
            connection_type = _get_connection_type()
            position_mapping = {}
            
            if connection_type == "sqlite":
                # Query to get all employees grouped by position
                sql = """
                SELECT Position, 
                       EmployeeID as EmpID,
                       FirstName || ' ' || LastName || ' (' || EmployeeID || ')' as Name
                FROM Employees 
                WHERE Position IS NOT NULL 
                  AND FirstName IS NOT NULL
                ORDER BY Position, LastName, FirstName
                """
                df, _ = _read_sql(sql, ())
                
                if not df.empty:
                    for _, row in df.iterrows():
                        position = row['Position']
                        emp_id = str(row['EmpID'])
                        name = row['Name']
                        
                        if position not in position_mapping:
                            position_mapping[position] = {'names': set(), 'ids': set()}
                        
                        position_mapping[position]['names'].add(name)
                        position_mapping[position]['ids'].add(emp_id)
                    
                    # Convert sets to sorted lists
                    for position in position_mapping:
                        position_mapping[position]['names'] = sorted(list(position_mapping[position]['names']))
                        position_mapping[position]['ids'] = sorted(list(position_mapping[position]['ids']))
            
            return position_mapping
            
        except Exception as e:
            print(f"Error building position mapping: {e}")
            return {}
    
    def _get_all_employee_options(self):
        """Get all employee name and ID options including auto-generated generic employees"""
        try:
            connection_type = _get_connection_type()
            all_names = ['']
            all_ids = ['']
            
            if connection_type == "sqlite":
                # Get specific employees
                sql = """
                SELECT EmployeeID as EmpID,
                       FirstName || ' ' || LastName || ' (' || EmployeeID || ')' as Name
                FROM Employees 
                WHERE FirstName IS NOT NULL
                ORDER BY LastName, FirstName
                """
                df, _ = _read_sql(sql, ())
                
                if not df.empty:
                    all_names.extend(df['Name'].tolist())
                    all_ids.extend([str(id) for id in df['EmpID'].tolist()])
                
                # Add generic employees for each position with unique IDs
                try:
                    from .payroll_live_adapter import get_position_averages
                    position_avg_df, _ = get_position_averages()
                    
                    if not position_avg_df.empty:
                        for _, row in position_avg_df.iterrows():
                            position = row['Position']
                            # Use unique generic ID from the database query
                            generic_id = str(row.get('generic_id', 999999))
                            # Create generic employee entry with unique ID
                            generic_name = f"Generic {position} ({generic_id})"
                            
                            all_names.append(generic_name)
                            all_ids.append(generic_id)
                            
                except Exception as e:
                    print(f"Error adding generic employees: {e}")
            
            return all_names, all_ids
            
        except Exception as e:
            print(f"Error getting all employee options: {e}")
            return [''], ['']
    
    def _get_filtered_employee_options(self, dataframe, position_to_employees, all_names, all_ids):
        """Get filtered employee options based on position selections, including generic employees"""
        try:
            # Get all unique positions currently selected in the dataframe
            selected_positions = set()
            if not dataframe.empty:
                for _, row in dataframe.iterrows():
                    position = row.get('Position', '')
                    if position and position != '':
                        selected_positions.add(position)
            
            # If no positions selected, return all options (including generic employees)
            if not selected_positions:
                return all_names, all_ids
            
            # Combine employees from all selected positions
            filtered_names = set([''])  # Always include empty option
            filtered_ids = set([''])    # Always include empty option
            
            # Add specific employees for selected positions
            for position in selected_positions:
                if position in position_to_employees:
                    filtered_names.update(position_to_employees[position]['names'])
                    filtered_ids.update(position_to_employees[position]['ids'])
            
            # Add generic employees for matching positions with unique IDs
            try:
                from .payroll_live_adapter import get_position_averages
                position_avg_df, _ = get_position_averages()
                
                if not position_avg_df.empty:
                    # Add generic employees for selected positions
                    matching_positions = position_avg_df[position_avg_df['Position'].isin(selected_positions)]
                    
                    for _, row in matching_positions.iterrows():
                        position = row['Position']
                        # Use unique generic ID from the database query
                        generic_id = str(row.get('generic_id', 999999))
                        generic_name = f"Generic {position} ({generic_id})"
                        
                        filtered_names.add(generic_name)
                        filtered_ids.add(generic_id)
                        
            except Exception as e:
                print(f"Error adding filtered generic employees: {e}")
            
            # Convert to sorted lists
            filtered_names_list = sorted(list(filtered_names))
            filtered_ids_list = sorted(list(filtered_ids))
            
            return filtered_names_list, filtered_ids_list
            
        except Exception as e:
            print(f"Error in filtering employee options: {e}")
            return all_names, all_ids
    
    def _extract_generic_id_from_name(self, name):
        """Extract generic ID from a generic position name"""
        try:
            # Name format: "📊 Position Name (Avg: $50,000 | 3 employees)"
            if name.startswith('📊'):
                # Extract position name between 📊 and (Avg:
                position_part = name.split('(Avg:')[0].strip()
                position_name = position_part.replace('📊', '').strip()
                # Convert to generic ID format
                generic_id = f"GENERIC_{position_name.replace(' ', '_').upper()}"
                return generic_id
        except Exception as e:
            print(f"Error extracting generic ID from name: {e}")
        return None

    def _populate_generic_employee_data(self, row_data, position_name, generic_id=None):
        """Populate row data for a generic employee selection with unique ID"""
        try:
            # Get position averages data
            from .payroll_live_adapter import get_position_averages
            position_avg_df, _ = get_position_averages()
            
            if not position_avg_df.empty:
                # Find the matching position (case insensitive)
                matching_position = position_avg_df[position_avg_df['Position'].str.upper() == position_name.upper()]
                
                if not matching_position.empty:
                    pos_data = matching_position.iloc[0]
                    
                    # Use the unique generic ID from the data or extract from the generic_id field
                    if generic_id is None:
                        generic_id = str(pos_data.get('generic_id', 999999))
                    
                    # Populate the row with generic employee data including metadata
                    row_data.update({
                        'Position': pos_data['Position'],
                        'EmpID': generic_id,
                        'Name': f"Generic {pos_data['Position']} ({generic_id})",
                        'Department': pos_data.get('primary_department', 'General'),
                        'FTE': 1.0,
                        'Basis': pos_data.get('common_basis', 'Salary'),
                        'BaseRate': float(pos_data['avg_base_rate']),
                        'Grade': 'N/A',
                        'Step': 1,
                        'COLA': 0.0,
                        'BenefitsRate': float(pos_data.get('avg_benefits_rate', 30.0)),  # Dynamic benefits from actual data
                        'HoursPerPeriod': 80,
                        'OTHours': 0,
                        'OTRate': 1.5,
                        'VacancyMonths': 0.0,
                        'StipendAnnual': 0.0,
                        'BenefitsMode': 'standard',
                        'is_generic': True,  # Metadata flag
                        'source_position': pos_data['Position']  # Source tracking
                    })
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error populating generic employee data: {e}")
            return False
    
    def _check_name_empid_changes_only(self, new_df, old_df):
        """Check if only Name or EmpID columns changed (ignoring manual field edits)"""
        try:
            # Check each row to see if Name or EmpID changed
            for idx in new_df.index:
                if idx < len(old_df):
                    old_name = str(old_df.iloc[idx].get('Name', '')).strip()
                    old_empid = str(old_df.iloc[idx].get('EmpID', '')).strip()
                    new_name = str(new_df.iloc[idx].get('Name', '')).strip()
                    new_empid = str(new_df.iloc[idx].get('EmpID', '')).strip()
                    
                    # If Name or EmpID changed, this qualifies for autofill
                    if old_name != new_name or old_empid != new_empid:
                        return True
                else:
                    # New row added - check if it has Name or EmpID
                    new_name = str(new_df.iloc[idx].get('Name', '')).strip()
                    new_empid = str(new_df.iloc[idx].get('EmpID', '')).strip()
                    if new_name or new_empid:
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error checking name/empid changes: {e}")
            return False
    
    def _apply_selective_autofill(self, new_df, old_df):
        """Apply autofill only when employee names/IDs change, not on manual field edits"""
        try:
            # Only apply autofill if Name or EmpID columns have changed
            changes_made = False
            modified_df = new_df.copy()
            
            # Check which rows have Name or EmpID changes
            for idx in new_df.index:
                if idx < len(old_df):
                    old_name = str(old_df.iloc[idx].get('Name', '')).strip()
                    old_empid = str(old_df.iloc[idx].get('EmpID', '')).strip()
                    new_name = str(new_df.iloc[idx].get('Name', '')).strip()
                    new_empid = str(new_df.iloc[idx].get('EmpID', '')).strip()
                    
                    # Only autofill if Name or EmpID actually changed
                    if old_name != new_name or old_empid != new_empid:
                        autofilled_row = self._autofill_employee_data(modified_df.iloc[idx])
                        if autofilled_row is not None:
                            for col, value in autofilled_row.items():
                                # Don't overwrite manually entered values for these fields
                                if col not in ['BenefitsRate', 'HoursPerPeriod', 'OTHours', 'OTRate', 'Grade', 'Step', 'VacancyMonths']:
                                    modified_df.at[idx, col] = value
                            changes_made = True
                else:
                    # New row - check if it needs autofill
                    autofilled_row = self._autofill_employee_data(modified_df.iloc[idx])
                    if autofilled_row is not None:
                        for col, value in autofilled_row.items():
                            # Don't overwrite manually entered values for these fields, even on new rows
                            current_value = modified_df.iloc[idx].get(col)
                            if col not in ['BenefitsRate', 'HoursPerPeriod', 'OTHours', 'OTRate', 'Grade', 'Step', 'VacancyMonths'] or not current_value:
                                modified_df.at[idx, col] = value
                        changes_made = True
            
            return modified_df
            
        except Exception as e:
            print(f"Error in selective autofill: {e}")
            return new_df
    
    def _autofill_employee_data(self, row):
        """Autofill employee data for a single row, including generic employees"""
        try:
            # Check if this row needs autofill
            name = str(row.get('Name', '')).strip()
            emp_id = str(row.get('EmpID', '')).strip()
            
            # Handle generic employee selection (IDs starting with 999)
            if emp_id.startswith('999') or (name and name.startswith('Generic ')):
                # This is a generic employee selection
                row_data = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
                
                # Extract position name and generic ID from the generic employee name
                if name.startswith('Generic '):
                    # Name format: "Generic Librarian (999001)"
                    import re
                    match = re.match(r"Generic (.+) \((\d+)\)", name)
                    if match:
                        position_name = match.group(1).strip()
                        generic_id = match.group(2)
                    else:
                        # Fallback to old format
                        position_name = name.replace('Generic ', '').split(' (')[0].strip()
                        generic_id = emp_id
                    
                    if self._populate_generic_employee_data(row_data, position_name, generic_id):
                        return row_data
                
                return None
            
            # Handle specific employee selection (existing logic)
            import sqlite3
            import os
            
            employee_lookup = {}
            payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
            
            if os.path.exists(payroll_db_path):
                conn = sqlite3.connect(payroll_db_path)
                cursor = conn.cursor()
                
                # Get employee data
                sql = "SELECT EmployeeID as EmpID, FirstName || ' ' || LastName as Name, Position, Department, FTE, Basis FROM Employees WHERE FirstName IS NOT NULL"
                cursor.execute(sql)
                rows = cursor.fetchall()
                
                # Get salary data
                salary_data = {}
                try:
                    salary_sql = "SELECT ph.EmployeeID, AVG(ph.GrossPay) as AvgGrossPay FROM PaycheckHeaders ph GROUP BY ph.EmployeeID"
                    cursor.execute(salary_sql)
                    salary_rows = cursor.fetchall()
                    for salary_row in salary_rows:
                        emp_id_db = str(salary_row[0])
                        avg_gross = salary_row[1] or 0
                        annual_rate = avg_gross * 26 if avg_gross > 0 else 0
                        salary_data[emp_id_db] = round(annual_rate, 2)
                except:
                    pass
                
                # Build lookup
                for emp_row in rows:
                    emp_id_db = str(emp_row[0])
                    name_db = emp_row[1]
                    position = emp_row[2] or ''
                    department = emp_row[3] or ''
                    fte = emp_row[4] if emp_row[4] is not None else 1.0
                    basis = emp_row[5] or 'Salary'
                    base_rate = salary_data.get(emp_id_db, 0)
                    
                    name_with_id = f"{name_db} ({emp_id_db})"
                    
                    employee_lookup[emp_id_db] = {
                        'Name': name_with_id, 'Position': position, 'Department': department,
                        'FTE': fte, 'Basis': basis, 'BaseRate': base_rate
                    }
                    employee_lookup[name_with_id] = {
                        'EmpID': emp_id_db, 'Position': position, 'Department': department,
                        'FTE': fte, 'Basis': basis, 'BaseRate': base_rate
                    }
                
                conn.close()
            
            if name and name in employee_lookup:
                emp_data = employee_lookup[name]
                # Get additional budgeting data from database
                budget_data = self._get_employee_budget_data(emp_data['EmpID'])
                
                result = {
                    'EmpID': emp_data['EmpID'],
                    'Position': emp_data['Position'],
                    'Department': emp_data['Department'],
                    'FTE': emp_data['FTE'],
                    'Basis': emp_data['Basis'],
                    'BaseRate': emp_data['BaseRate']
                }
                
                # Add budget data if available
                result.update(budget_data)
                return result
            elif emp_id and emp_id in employee_lookup:
                emp_data = employee_lookup[emp_id]
                
                # Get additional budgeting data from database  
                budget_data = self._get_employee_budget_data(emp_id)
                
                result = {
                    'Name': emp_data['Name'],
                    'Position': emp_data['Position'],
                    'Department': emp_data['Department'],
                    'FTE': emp_data['FTE'],
                    'Basis': emp_data['Basis'],
                    'BaseRate': emp_data['BaseRate']
                }
                
                # Add budget data if available
                result.update(budget_data)
                return result
            
            return None
            
        except Exception as e:
            print(f"Error in employee data autofill: {e}")
            return None
    
    def _get_employee_budget_data(self, emp_id):
        """Get budgeting data (Hours/PP, OT Hours, OT Rate, Benefits%) from database"""
        try:
            from .payroll_live_adapter import _get_connection_type, _read_sql
            
            budget_data = {}
            connection_type = _get_connection_type()
            
            if connection_type == "none":
                # Provide safe defaults when no database is available
                return {
                    'HoursPerPeriod': 80,
                    'OTRate': 1.5,
                    'OTHours': 0,
                    'BenefitsRate': 30.0
                }
            
            # 1. Get standard overtime rate from PayCodes (default to 1.5x)
            try:
                ot_sql = "SELECT Multiplier FROM PayCodes WHERE Type = 'Overtime' AND Code = 'OT1'"
                ot_df, _ = _read_sql(ot_sql, ())
                if not ot_df.empty:
                    budget_data['OTRate'] = float(ot_df.iloc[0]['Multiplier'])
                else:
                    budget_data['OTRate'] = 1.5
            except:
                budget_data['OTRate'] = 1.5
            
            # 2. Calculate Hours/PP based on FTE (40 hours * FTE * 2 weeks = Hours per pay period)
            try:
                fte_sql = "SELECT FTE FROM Employees WHERE EmployeeID = ?"
                fte_df, _ = _read_sql(fte_sql, (emp_id,))
                if not fte_df.empty and fte_df.iloc[0]['FTE']:
                    fte = float(fte_df.iloc[0]['FTE'])
                    budget_data['HoursPerPeriod'] = round(80 * fte, 1)  # 80 hours for full-time bi-weekly
                else:
                    budget_data['HoursPerPeriod'] = 80
            except:
                budget_data['HoursPerPeriod'] = 80
            
            # 3. Provide defaults for other fields
            budget_data['OTHours'] = 0  # Default to no overtime
            
            return budget_data
            
        except Exception as e:
            print(f"Error getting budget data for {emp_id}: {e}")
            return {
                'OTRate': 1.5,
                'HoursPerPeriod': 80,
                'OTHours': 0,
                'BenefitsRate': 30
            }
    
    def _apply_selectbox_autofill(self, df):
        """Apply autofill logic based on selectbox selections (mirrors position filtering approach)"""
        try:
            # Build employee lookup table
            employee_lookup = {}
            
            try:
                import sqlite3
                import os
                
                payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
                if os.path.exists(payroll_db_path):
                    conn = sqlite3.connect(payroll_db_path)
                    cursor = conn.cursor()
                    
                    # First get employee basic info
                    sql = "SELECT EmployeeID as EmpID, FirstName || ' ' || LastName as Name, Position, Department, FTE, Basis FROM Employees WHERE FirstName IS NOT NULL"
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    # Get salary data from recent paychecks
                    salary_data = {}
                    try:
                        salary_sql = """
                        SELECT ph.EmployeeID, AVG(ph.GrossPay) as AvgGrossPay, COUNT(*) as PayPeriods 
                        FROM PaycheckHeaders ph 
                        GROUP BY ph.EmployeeID
                        """
                        cursor.execute(salary_sql)
                        salary_rows = cursor.fetchall()
                        for salary_row in salary_rows:
                            emp_id = str(salary_row[0])
                            avg_gross = salary_row[1] or 0
                            periods = salary_row[2] or 0
                            # Calculate approximate annual rate (assuming 26 pay periods)
                            annual_rate = avg_gross * 26 if periods > 0 else 0
                            salary_data[emp_id] = {
                                'BaseRate': round(annual_rate, 2),
                                'AvgGrossPay': round(avg_gross, 2)
                            }
                    except Exception as e:
                        print(f"Could not load salary data: {e}")
                    
                    for row in rows:
                        emp_id = str(row[0])
                        name = row[1]
                        position = row[2] or ''
                        department = row[3] or ''
                        fte = row[4] if row[4] is not None else 1.0
                        basis = row[5] or 'Salary'
                        
                        # Get salary info if available
                        base_rate = 0
                        if emp_id in salary_data:
                            base_rate = salary_data[emp_id]['BaseRate']
                        
                        name_with_id = f"{name} ({emp_id})"
                        
                        # Create lookup entries with only actual database data
                        employee_lookup[emp_id] = {
                            'Name': name_with_id, 
                            'Position': position, 
                            'Department': department,
                            'FTE': fte,
                            'Basis': basis,
                            'BaseRate': base_rate
                        }
                        employee_lookup[name_with_id] = {
                            'EmpID': emp_id, 
                            'Position': position, 
                            'Department': department,
                            'FTE': fte,
                            'Basis': basis,
                            'BaseRate': base_rate
                        }
                        
                    conn.close()
                    
            except Exception as e:
                print(f"Error loading employee data: {e}")
                return df
            
            # Apply autofill row by row (like position filtering does)
            modified_df = df.copy()
            changes_made = False
            
            for idx, row in modified_df.iterrows():
                emp_id = str(row.get('EmpID', '')).strip()
                name = str(row.get('Name', '')).strip()
                position = str(row.get('Position', '')).strip()
                department = str(row.get('Department', '')).strip()
                
                # Clean up None values
                if emp_id in ['None', 'nan', 'NaN']: emp_id = ''
                if name in ['None', 'nan', 'NaN']: name = ''
                if position in ['None', 'nan', 'NaN']: position = ''
                if department in ['None', 'nan', 'NaN']: department = ''
                
                # Case 1: Name selected from dropdown, autofill other fields
                if name and name in employee_lookup:
                    emp_data = employee_lookup[name]
                    fields_updated = []
                    
                    if not emp_id:
                        modified_df.at[idx, 'EmpID'] = emp_data['EmpID']
                        changes_made = True
                        fields_updated.append(f"EmpID={emp_data['EmpID']}")
                    if not position:
                        modified_df.at[idx, 'Position'] = emp_data['Position']
                        changes_made = True
                        fields_updated.append(f"Position={emp_data['Position']}")
                    if not department:
                        modified_df.at[idx, 'Department'] = emp_data['Department']
                        changes_made = True
                        fields_updated.append(f"Department={emp_data['Department']}")
                    
                    # Autofill FTE, Basis, and BaseRate if not set
                    current_fte = row.get('FTE')
                    current_basis = row.get('Basis')
                    current_base_rate = row.get('BaseRate')
                    
                    if not current_fte or current_fte == 0:
                        modified_df.at[idx, 'FTE'] = emp_data['FTE']
                        changes_made = True
                        fields_updated.append(f"FTE={emp_data['FTE']}")
                    
                    if not current_basis or current_basis == '':
                        modified_df.at[idx, 'Basis'] = emp_data['Basis']
                        changes_made = True
                        fields_updated.append(f"Basis={emp_data['Basis']}")
                    
                    if (not current_base_rate or current_base_rate == 0) and emp_data['BaseRate'] > 0:
                        modified_df.at[idx, 'BaseRate'] = emp_data['BaseRate']
                        changes_made = True
                        fields_updated.append(f"BaseRate=${emp_data['BaseRate']:,.0f}")
                    
                    if fields_updated:
                        print(f"Autofilled from Name {name}: {', '.join(fields_updated)}")
                
                # Case 2: EmpID selected from dropdown, autofill other fields  
                elif emp_id and emp_id in employee_lookup:
                    emp_data = employee_lookup[emp_id]
                    fields_updated = []
                    
                    if not name:
                        modified_df.at[idx, 'Name'] = emp_data['Name']
                        changes_made = True
                        fields_updated.append(f"Name={emp_data['Name']}")
                    if not position:
                        modified_df.at[idx, 'Position'] = emp_data['Position']
                        changes_made = True
                        fields_updated.append(f"Position={emp_data['Position']}")
                    if not department:
                        modified_df.at[idx, 'Department'] = emp_data['Department']
                        changes_made = True
                        fields_updated.append(f"Department={emp_data['Department']}")
                    
                    # Autofill FTE, Basis, and BaseRate if not set
                    current_fte = row.get('FTE')
                    current_basis = row.get('Basis')
                    current_base_rate = row.get('BaseRate')
                    
                    if not current_fte or current_fte == 0:
                        modified_df.at[idx, 'FTE'] = emp_data['FTE']
                        changes_made = True
                        fields_updated.append(f"FTE={emp_data['FTE']}")
                    
                    if not current_basis or current_basis == '':
                        modified_df.at[idx, 'Basis'] = emp_data['Basis']
                        changes_made = True
                        fields_updated.append(f"Basis={emp_data['Basis']}")
                    
                    if (not current_base_rate or current_base_rate == 0) and emp_data['BaseRate'] > 0:
                        modified_df.at[idx, 'BaseRate'] = emp_data['BaseRate']
                        changes_made = True
                        fields_updated.append(f"BaseRate=${emp_data['BaseRate']:,.0f}")
                    
                    if fields_updated:
                        print(f"Autofilled from EmpID {emp_id}: {', '.join(fields_updated)}")
            
            if changes_made:
                print("Selectbox autofill completed")
            
            return modified_df
            
        except Exception as e:
            print(f"Error in selectbox autofill: {e}")
            return df
    
    
    def _apply_autofill_logic(self, df):
        """Apply autofill logic when Employee ID or Name is selected"""
        try:
            # Use the exact same database approach as the working filtering code
            employee_lookup = {}
            
            # Build the lookup table with the same SQL as filtering
            try:
                # Use sqlite3 directly like the filtering code does successfully
                import sqlite3
                import os
                
                # Try to connect to the payroll database
                payroll_db_path = "databases/payroll_city_payroll_demo (1).db"
                if os.path.exists(payroll_db_path):
                    conn = sqlite3.connect(payroll_db_path)
                    cursor = conn.cursor()
                    
                    # Same SQL as the filtering code uses
                    sql = "SELECT EmployeeID as EmpID, FirstName || ' ' || LastName as Name, Position, Department FROM Employees WHERE FirstName IS NOT NULL"
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        emp_id = str(row[0])  # EmpID
                        name = row[1]         # Name
                        position = row[2]     # Position
                        department = row[3]   # Department
                        
                        name_with_id = f"{name} ({emp_id})"
                        
                        # EmpID to employee data lookup
                        employee_lookup[emp_id] = {
                            'Name': name_with_id,
                            'Position': position or '',
                            'Department': department or ''
                        }
                        
                        # Name (with ID) to employee data lookup
                        employee_lookup[name_with_id] = {
                            'EmpID': emp_id,
                            'Position': position or '',
                            'Department': department or ''
                        }
                        
                        # Also add case-insensitive and partial name lookups
                        name_lower = name.lower()
                        name_with_id_lower = name_with_id.lower()
                        
                        employee_lookup[name_lower] = {
                            'EmpID': emp_id,
                            'Position': position or '',
                            'Department': department or '',
                            'Name': name_with_id
                        }
                        
                        employee_lookup[name_with_id_lower] = {
                            'EmpID': emp_id,
                            'Position': position or '',
                            'Department': department or '',
                            'Name': name_with_id
                        }
                    
                    conn.close()
                    print(f"Loaded {len(rows)} employees for autofill")
                    
            except Exception as e:
                print(f"Error loading employee data for autofill: {e}")
                return df
            
            # Apply autofill for each row - one direction per row to prevent overwrites
            changes_made = False
            for idx, row in df.iterrows():
                emp_id = str(row.get('EmpID', '')).strip()
                name = str(row.get('Name', '')).strip()
                
                # Clean up "None" values that come from empty cells
                if emp_id == 'None' or emp_id == 'nan':
                    emp_id = ''
                if name == 'None' or name == 'nan':
                    name = ''
                
                print(f"Processing row {idx}: EmpID='{emp_id}', Name='{name}'")
                
                # Determine which field to use as the "source" for autofill
                # Priority: If both are filled, assume user just changed one and don't overwrite
                autofill_performed = False
                
                # Case 1: EmpID is filled but Name is empty - autofill Name, Position, Department
                if emp_id and emp_id != '' and (not name or name == '') and emp_id in employee_lookup:
                    emp_data = employee_lookup[emp_id]
                    # Force string conversion and handle None values
                    df.at[idx, 'Name'] = str(emp_data['Name']) if emp_data['Name'] else ''
                    df.at[idx, 'Position'] = str(emp_data['Position']) if emp_data['Position'] else ''
                    df.at[idx, 'Department'] = str(emp_data['Department']) if emp_data['Department'] else ''
                    print(f"Autofilled employee data for EmpID {emp_id}: {emp_data['Name']}, {emp_data['Position']}, {emp_data['Department']}")
                    print(f"Row {idx} after autofill: Name='{df.at[idx, 'Name']}', Position='{df.at[idx, 'Position']}', Department='{df.at[idx, 'Department']}'")
                    changes_made = True
                    autofill_performed = True
                
                # Case 2: Name is filled but EmpID is empty - autofill EmpID, Position, Department
                elif name and name != '' and (not emp_id or emp_id == ''):
                    # Try exact match first
                    emp_data = None
                    if name in employee_lookup:
                        emp_data = employee_lookup[name]
                    # Try case-insensitive match
                    elif name.lower() in employee_lookup:
                        emp_data = employee_lookup[name.lower()]
                    
                    if emp_data:
                        # Force string conversion and handle None values
                        df.at[idx, 'EmpID'] = str(emp_data['EmpID']) if emp_data['EmpID'] else ''
                        df.at[idx, 'Position'] = str(emp_data['Position']) if emp_data['Position'] else ''
                        df.at[idx, 'Department'] = str(emp_data['Department']) if emp_data['Department'] else ''
                        # Update the name to the proper format if we have it
                        if 'Name' in emp_data and emp_data['Name']:
                            df.at[idx, 'Name'] = str(emp_data['Name'])
                        print(f"Autofilled employee data for Name {name}: {emp_data['EmpID']}, {emp_data['Position']}, {emp_data['Department']}")
                        print(f"Row {idx} after autofill: EmpID='{df.at[idx, 'EmpID']}', Position='{df.at[idx, 'Position']}', Department='{df.at[idx, 'Department']}'")
                        changes_made = True
                        autofill_performed = True
                
                # Case 3: Both are filled - autofill Position and Department if they're empty
                elif emp_id and name and emp_id in employee_lookup:
                    emp_data = employee_lookup[emp_id]
                    current_position = str(row.get('Position', '')).strip()
                    current_department = str(row.get('Department', '')).strip()
                    
                    # Autofill Position if empty
                    if not current_position or current_position == '':
                        df.at[idx, 'Position'] = emp_data['Position']
                        changes_made = True
                        print(f"Autofilled Position for {name}: {emp_data['Position']}")
                    
                    # Autofill Department if empty
                    if not current_department or current_department == '':
                        df.at[idx, 'Department'] = emp_data['Department']
                        changes_made = True
                        print(f"Autofilled Department for {name}: {emp_data['Department']}")
            
            if not changes_made:
                print("No autofill changes needed")
            
            return df
            
        except Exception as e:
            print(f"Error in autofill logic: {e}")
            return df
    
    def _autosave_export_data(self):
        """Automatically update export data when spreadsheet changes"""
        try:
            if 'pbb_dataframe' in st.session_state:
                df = st.session_state.pbb_dataframe
                # Filter out empty rows for export
                export_df = df[df['Position'].fillna('') != ''].copy()
                
                if not export_df.empty:
                    # Generate export data that matches the spreadsheet exactly
                    export_data = self._generate_export_data(export_df)
                    st.session_state.pbb_export_data = export_data
                    print(f"Autosaved export data for {len(export_df)} positions")
                else:
                    # Clear export data if no positions
                    st.session_state.pbb_export_data = []
        except Exception as e:
            print(f"Error in autosave export data: {e}")
    
    def _generate_export_data(self, df):
        """Generate export data from the dataframe"""
        export_data = []
        for _, row in df.iterrows():
            if pd.notna(row['Position']) and row['Position'] != '':
                export_data.append({
                    'Position': row['Position'],
                    'Employee': f"{row.get('Name', '')} ({row.get('EmpID', '')})" if row.get('Name') else '',
                    'Department': row.get('Department', ''),
                    'FTE': row.get('FTE', 1.0),
                    'Total_Cost': row.get('TotalCost', 0),
                    'Base_Wages': row.get('WagesBase', 0),
                    'OT_Wages': row.get('WagesOT', 0),
                    'Benefits': row.get('Benefits', 0),
                    'Taxes': row.get('Taxes', 0)
                })
        return export_data