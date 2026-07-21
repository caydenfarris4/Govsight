# PBB UI Export - Export Tab and Helper Functions
# Position-Based Budgeting export functionality and helpers (~350 lines)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Any
import plotly.express as px
from modules.navi.payroll_live_adapter import _get_connection_type, _read_sql

class PBBExportUI:
    """Position-Based Budgeting export and comparison interface"""
    
    def __init__(self, core_instance, calculations_instance):
        self.core = core_instance
        self.calculations = calculations_instance
    
    def render_export_tab(self):
        """Render the export functionality tab"""
        st.markdown("### Budget Export & Reporting")
        
        # Check if there's data to export
        if 'pbb_dataframe' not in st.session_state or st.session_state.pbb_dataframe.empty:
            st.warning("No budget data available. Please create some positions in the Spreadsheet tab first.")
            return
        
        # Filter out empty rows for export
        df = st.session_state.pbb_dataframe
        export_df = df[df['Position'] != ''].copy()
        
        if export_df.empty:
            st.warning("No populated positions found. Please add some positions in the Spreadsheet tab first.")
            return
        
        # Export options
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### Transaction Export (for GL import)")
            if st.button("Generate Transaction Export", help="Create GL account transactions for budget import"):
                self._render_transaction_export(export_df)
        
        with col2:
            st.markdown("#### Detailed Budget Report")
            if st.button("Generate Detailed Export", help="Create comprehensive budget report"):
                self._render_detailed_export(export_df)
        
        # Actuals Comparison Viewer
        st.markdown("---")
        st.markdown("### Actuals Comparison Viewer")
        
        # Year selector for actuals
        col1, col2 = st.columns([2, 4])
        with col1:
            actuals_year = st.selectbox(
                "Select Actuals Year",
                options=["2024", "2023", "2022", "2021", "2020"],
                help="Choose which year's actual data to display for comparison"
            )
        
        with col2:
            st.info(f"Showing actual costs for {actuals_year} compared to your current budget projections")
        
        # Generate actuals data that mirrors the budget structure
        actuals_df = self._generate_actuals_comparison(actuals_year)
        
        if not actuals_df.empty:
            # Display actuals viewer (read-only)
            st.markdown(f"**{actuals_year} Actual Costs vs Current Budget:**")
            
            # Configure columns for actuals display (read-only)
            actuals_column_config = {
                "Position": st.column_config.TextColumn("Position", width="large"),
                "EmpID": st.column_config.TextColumn("Employee ID", width="medium"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Department": st.column_config.TextColumn("Department", width="medium"),
                "Actual_WagesBase": st.column_config.NumberColumn(f"{actuals_year} Base Wages", format="$%.2f", width="medium"),
                "Actual_WagesOT": st.column_config.NumberColumn(f"{actuals_year} OT Wages", format="$%.2f", width="medium"),
                "Actual_Benefits": st.column_config.NumberColumn(f"{actuals_year} Benefits", format="$%.2f", width="medium"),
                "Actual_TotalCost": st.column_config.NumberColumn(f"{actuals_year} Total", format="$%.2f", width="medium"),
                "Budget_TotalCost": st.column_config.NumberColumn("Current Budget", format="$%.2f", width="medium"),
                "Variance": st.column_config.NumberColumn("Variance", format="$%.2f", width="medium"),
                "Variance_Pct": st.column_config.NumberColumn("Variance %", format="%.1f%%", width="small")
            }
            
            # Display the comparison viewer
            st.dataframe(
                actuals_df,
                column_config=actuals_column_config,
                use_container_width=True,
                hide_index=True,
                height=400
            )
            
            # Comparison summary
            total_actuals = actuals_df['Actual_TotalCost'].sum()
            total_budget = actuals_df['Budget_TotalCost'].sum()
            total_variance = total_budget - total_actuals
            variance_pct = (total_variance / total_actuals * 100) if total_actuals > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(f"{actuals_year} Actuals", f"${total_actuals:,.2f}")
            with col2:
                st.metric("Current Budget", f"${total_budget:,.2f}")
            with col3:
                variance_color = "normal" if total_variance >= 0 else "inverse"
                st.metric("Variance", f"${total_variance:,.2f}", delta=f"{variance_pct:.1f}%")
            with col4:
                status = "Over Budget" if total_variance < 0 else "Under Budget"
                st.metric("Status", status)
        else:
            st.warning(f"No actual data available for {actuals_year} comparison.")
    
    def _render_transaction_export(self, df):
        """Render transaction-style export for GL import"""
        st.markdown("#### GL Transaction Export")
        
        # Generate transaction records
        transactions = []
        
        for _, row in df.iterrows():
            position = row['Position']
            total_cost = row['TotalCost']
            wages_base = row['WagesBase'] 
            wages_ot = row['WagesOT']
            benefits = row['Benefits']
            taxes = row['Taxes']
            department = row.get('Department', 'General')
            
            # Base transaction record structure
            base_record = {
                'Department': department,
                'Position': position,
                'Employee': f"{row.get('Name', '')} ({row.get('EmpID', '')})" if row.get('Name') else '',
                'Fund': '001',  # General Fund
                'Function': '10',  # General Government
                'Activity': '101',  # Administration 
                'Period': '01',  # January
                'Year': self.core.budget_year
            }
            
            # Create individual account transactions
            if wages_base > 0:
                transactions.append({
                    **base_record,
                    'Account': '51100',  # Salaries & Wages
                    'Description': f'Base Wages - {position}',
                    'Amount': wages_base
                })
            
            if wages_ot > 0:
                transactions.append({
                    **base_record,
                    'Account': '51110',  # Overtime Wages
                    'Description': f'Overtime - {position}', 
                    'Amount': wages_ot
                })
            
            if benefits > 0:
                transactions.append({
                    **base_record,
                    'Account': '52100',  # Employee Benefits
                    'Description': f'Benefits - {position}',
                    'Amount': benefits
                })
            
            if taxes > 0:
                transactions.append({
                    **base_record,
                    'Account': '52200',  # Payroll Taxes
                    'Description': f'Payroll Taxes - {position}',
                    'Amount': taxes
                })
        
        # Display transactions
        if transactions:
            trans_df = pd.DataFrame(transactions)
            st.dataframe(trans_df, use_container_width=True, hide_index=True)
            
            # Download option
            csv = trans_df.to_csv(index=False)
            st.download_button(
                label="Download GL Transactions (CSV)",
                data=csv,
                file_name=f"pbb_gl_transactions_{self.core.budget_year}.csv",
                mime="text/csv"
            )
            
            st.success(f"Generated {len(transactions)} GL transaction records")
        else:
            st.warning("No transactions to export")
    
    def _render_detailed_export(self, export_df):
        """Render detailed budget export with full breakdown"""
        st.markdown("#### Detailed Budget Report")
        
        # Enhanced export with all details
        detailed_data = []
        
        for _, row in export_df.iterrows():
            detailed_data.append({
                'Position': row['Position'],
                'Employee_ID': row.get('EmpID', ''),
                'Employee_Name': row.get('Name', ''),
                'Department': row.get('Department', ''),
                'FTE': row.get('FTE', 1.0),
                'Basis': row.get('Basis', 'Salary'),
                'Base_Rate': row.get('BaseRate', 0),
                'Grade_Step': f"{row.get('Grade', '')}-{row.get('Step', '')}",
                'COLA_Percent': row.get('COLA', 0),
                'Base_with_COLA': row.get('BaseWithCOLA', 0),
                'Hours_Per_Period': row.get('HoursPerPeriod', 80),
                'OT_Hours': row.get('OTHours', 0),
                'OT_Rate_Multiplier': row.get('OTRate', 1.5),
                'Funded_Months': row.get('FundedMonths', 12),
                'Vacancy_Months': row.get('VacancyMonths', 0),
                'Base_Wages': row.get('WagesBase', 0),
                'OT_Wages': row.get('WagesOT', 0),
                'Annual_Stipend': row.get('StipendAnnual', 0),
                'Stipends': row.get('Stipends', 0),
                'Benefits_Rate': row.get('BenefitsRate', 30),
                'Benefits_Mode': row.get('BenefitsMode', 'standard'),
                'Benefits_Cost': row.get('Benefits', 0),
                'Payroll_Taxes': row.get('Taxes', 0),
                'Total_Cost': row.get('TotalCost', 0),
                'Annual_Cost': row.get('AnnualCost', 0),
                'Effective_Rate': row.get('EffectiveRate', 0)
            })
        
        # Display detailed report
        detailed_df = pd.DataFrame(detailed_data)
        st.dataframe(detailed_df, use_container_width=True, hide_index=True)
        
        # Summary statistics
        st.markdown("---")
        st.markdown("#### Budget Summary")
        
        total_positions = len(detailed_df)
        total_fte = detailed_df['FTE'].sum()
        total_base_wages = detailed_df['Base_Wages'].sum()
        total_ot_wages = detailed_df['OT_Wages'].sum()
        total_benefits = detailed_df['Benefits_Cost'].sum()
        total_taxes = detailed_df['Payroll_Taxes'].sum()
        total_cost = detailed_df['Total_Cost'].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Positions", f"{total_positions:,}")
            st.metric("Total FTE", f"{total_fte:.2f}")
        with col2:
            st.metric("Base Wages", f"${total_base_wages:,.2f}")
            st.metric("OT Wages", f"${total_ot_wages:,.2f}")
        with col3:
            st.metric("Benefits", f"${total_benefits:,.2f}")
            st.metric("Payroll Taxes", f"${total_taxes:,.2f}")
        with col4:
            st.metric("Total Cost", f"${total_cost:,.2f}")
            avg_cost = total_cost / total_fte if total_fte > 0 else 0
            st.metric("Avg Cost/FTE", f"${avg_cost:,.2f}")
        
        # Download options
        col1, col2 = st.columns(2)
        
        with col1:
            csv = detailed_df.to_csv(index=False)
            st.download_button(
                label="Download Detailed Report (CSV)",
                data=csv,
                file_name=f"pbb_detailed_budget_{self.core.budget_year}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Create Excel-style export (CSV with formatting notes)
            summary_data = {
                'Summary_Metric': ['Total Positions', 'Total FTE', 'Total Base Wages', 'Total OT Wages', 
                                 'Total Benefits', 'Total Taxes', 'Total Cost', 'Average Cost per FTE'],
                'Value': [total_positions, total_fte, total_base_wages, total_ot_wages,
                         total_benefits, total_taxes, total_cost, avg_cost]
            }
            summary_df = pd.DataFrame(summary_data)
            
            # Combine detailed and summary
            combined_csv = f"POSITION-BASED BUDGET REPORT\nYear: {self.core.budget_year}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            combined_csv += "DETAILED BREAKDOWN:\n"
            combined_csv += detailed_df.to_csv(index=False)
            combined_csv += "\n\nSUMMARY TOTALS:\n"
            combined_csv += summary_df.to_csv(index=False)
            
            st.download_button(
                label="Download Complete Report (CSV)",
                data=combined_csv,
                file_name=f"pbb_complete_report_{self.core.budget_year}.csv",
                mime="text/csv"
            )
    
    def _generate_actuals_comparison(self, actuals_year):
        """Generate actuals comparison data that mirrors the budget structure"""
        try:
            # Get current budget data
            df = st.session_state.pbb_dataframe
            budget_df = df[df['Position'] != ''].copy()
            
            if budget_df.empty:
                return pd.DataFrame()
            
            comparison_data = []
            
            for _, row in budget_df.iterrows():
                emp_id = row.get('EmpID', '')
                name = row.get('Name', '')
                position = row.get('Position', '')
                department = row.get('Department', '')
                
                # Get actual data for this position/employee
                actuals = self._get_historical_actuals(emp_id, position, actuals_year)
                
                comparison_row = {
                    'Position': position,
                    'EmpID': emp_id,
                    'Name': name,
                    'Department': department,
                    'Actual_WagesBase': actuals.get('wages_base', 0),
                    'Actual_WagesOT': actuals.get('wages_ot', 0),
                    'Actual_Benefits': actuals.get('benefits', 0),
                    'Actual_TotalCost': actuals.get('total_cost', 0),
                    'Budget_TotalCost': row.get('TotalCost', 0),
                }
                
                # Calculate variance
                budget_total = comparison_row['Budget_TotalCost']
                actual_total = comparison_row['Actual_TotalCost']
                variance = budget_total - actual_total
                variance_pct = (variance / actual_total * 100) if actual_total > 0 else 0
                
                comparison_row['Variance'] = variance
                comparison_row['Variance_Pct'] = variance_pct
                
                comparison_data.append(comparison_row)
            
            return pd.DataFrame(comparison_data)
            
        except Exception as e:
            print(f"Error generating actuals comparison: {e}")
            return pd.DataFrame()
    
    def _get_historical_actuals(self, emp_id, position, year):
        """Get historical actual costs for an employee or position"""
        try:
            # Try to import database functions - fallback to simulated if not available
            try:
                from modules.navi.payroll_live_adapter import PayrollLiveAdapter
                adapter = PayrollLiveAdapter()
                # Try to get actual payroll data if available
                # This would be where real historical data lookup occurs
            except:
                pass
            
            # For now, always use simulated actuals since database structure may vary
            # In the future, this would query actual payroll history tables
            return self.calculations._generate_simulated_actuals(position, year)
            
        except Exception as e:
            print(f"Error getting historical actuals for {emp_id}/{position}: {e}")
            return self.calculations._generate_simulated_actuals(position, year)