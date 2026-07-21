# PBB Calculations - Calculation Engine and Formulas
# Position-Based Budgeting calculation methods (~400 lines)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Any

class PBBCalculations:
    """Position-Based Budgeting calculation engine"""
    
    def __init__(self, global_settings: Dict[str, Any]):
        self.global_settings = global_settings
    
    def _recalculate_all_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Recalculate all calculated fields for all rows"""
        calculated_df = df.copy()
        
        for index, row in calculated_df.iterrows():
            # Convert row to dictionary for easier processing
            row_dict = row.to_dict()
            
            # Skip empty rows
            if not row_dict.get('Position') or row_dict['Position'] == '':
                continue
            
            # Calculate funded months
            row_dict['FundedMonths'] = self._calculate_funded_months(
                row_dict.get('HireStartDate'), 
                row_dict.get('HireEndDate'), 
                row_dict.get('VacancyMonths') or 0,
                self.global_settings['year_start'], 
                self.global_settings['year_end']
            )
            
            # Calculate wages and benefits
            calculated = self._calculate_wages_and_benefits_from_row(row_dict)
            
            # Update the DataFrame row
            for key, value in calculated.items():
                if key in calculated_df.columns:
                    calculated_df.loc[index, key] = value
        
        return calculated_df
    
    def _calculate_wages_and_benefits_from_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate wages, benefits, and taxes for a row dictionary with enhanced PBB formulas"""
        # Use input values directly from spreadsheet with proper None handling
        eff_basis = row.get('Basis', 'Salary') or 'Salary'
        base_rate = row.get('BaseRate') or 0
        cola_pct = (row.get('COLA') or 0) / 100  # Convert percentage to decimal
        benefits_rate = (row.get('BenefitsRate') or 30) / 100  # Convert percentage to decimal
        eff_hours_pp = row.get('HoursPerPeriod') or 80
        eff_ot_hours = row.get('OTHours') or 0
        ot_rate = row.get('OTRate') or 1.5  # Use custom overtime multiplier
        
        funded_months = row.get('FundedMonths') or 12
        fte = row.get('FTE') or 1.0
        pay_periods = self.global_settings['pay_periods']
        
        # Apply COLA to base rate
        base_with_cola = base_rate * (1 + cola_pct)
        
        # Calculate base wages
        if eff_basis == 'Salary':
            wages_base = base_with_cola * (funded_months / 12) * fte
        else:
            # For hourly employees, convert annual BaseRate to hourly rate
            # BaseRate from database is annual salary, need to convert to hourly
            if base_with_cola > 0:
                annual_hours = eff_hours_pp * pay_periods  # Total annual regular hours
                hourly_rate = base_with_cola / annual_hours if annual_hours > 0 else 0
            else:
                hourly_rate = 0
            wages_base = eff_hours_pp * hourly_rate * pay_periods * (funded_months / 12) * fte
        
        # Calculate overtime
        if eff_basis == 'Salary':
            # OT as hours converted to dollar amount for salary
            hourly_equivalent = base_with_cola / (eff_hours_pp * pay_periods) if eff_hours_pp > 0 else 0
            wages_ot = eff_ot_hours * hourly_equivalent * ot_rate * pay_periods * (funded_months / 12) * fte if eff_ot_hours else 0
        else:
            # OT hours for hourly - use the same hourly rate calculated above
            if base_with_cola > 0:
                annual_hours = eff_hours_pp * pay_periods
                hourly_rate = base_with_cola / annual_hours if annual_hours > 0 else 0
            else:
                hourly_rate = 0
            wages_ot = eff_ot_hours * hourly_rate * ot_rate * pay_periods * (funded_months / 12) * fte if eff_ot_hours else 0
        
        # Calculate stipends
        stipends = (row.get('StipendAnnual') or 0) * (funded_months / 12) * fte
        
        # Calculate benefits using custom benefits rate or standard
        total_wages = wages_base + wages_ot + stipends
        if row.get('BenefitsMode', 'standard') == 'standard':
            benefits = benefits_rate * total_wages
        else:
            # Use basic calculation for elections mode
            benefits = benefits_rate * total_wages * 0.8
        
        # Calculate taxes
        fica_tax = min(total_wages, self.global_settings['fica_wage_base']) * self.global_settings['fica_pct']
        medicare_tax = total_wages * self.global_settings['medicare_pct']
        retirement_tax = total_wages * self.global_settings['retirement_pct']
        unemployment_tax = min(total_wages, self.global_settings['unemployment_base']) * self.global_settings['unemployment_pct']
        workers_comp_tax = total_wages * self.global_settings['workers_comp_pct']
        total_taxes = fica_tax + medicare_tax + retirement_tax + unemployment_tax + workers_comp_tax
        
        # Total cost
        total_cost = wages_base + wages_ot + stipends + benefits + total_taxes
        
        # Annual cost (if position is not full year)
        annual_cost = total_cost * (12 / funded_months) if funded_months > 0 else 0
        
        # Effective rate calculation
        if eff_basis == 'Hourly':
            total_hours = (eff_hours_pp + eff_ot_hours) * pay_periods * (funded_months / 12) * fte
            effective_rate = total_cost / total_hours if total_hours > 0 else 0
        else:
            # For salary, calculate effective hourly rate
            total_hours = eff_hours_pp * pay_periods * (funded_months / 12) * fte
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
    
    def _calculate_wages_and_benefits(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate wages, benefits, and taxes for a position"""
        # Determine effective values (employee vs. input)
        if row['Status'] == 'Filled' and row['Incumbent']:
            emp_data = self._get_employee_data(row['Incumbent'])
            eff_basis = emp_data.get('EmpBasis', row['Basis'])
            eff_base_rate = emp_data.get('EmpBaseRate', row['BaseRate'])
            eff_hours_pp = emp_data.get('EmpHoursPP', row['HoursPP'])
            eff_ot_hours = emp_data.get('EmpOTHoursPP', row['OTHoursPP'])
            eff_benefits_monthly = emp_data.get('EmpBenefitsMonthly', row['BenefitsMonthly'])
        else:
            eff_basis = row['Basis']
            eff_base_rate = row['BaseRate']
            eff_hours_pp = row['HoursPP']
            eff_ot_hours = row['OTHoursPP']
            eff_benefits_monthly = row['BenefitsMonthly']
        
        # Calculate funded months
        funded_months = self._calculate_funded_months(
            row.get('HireStart'), 
            row.get('HireEnd'), 
            row.get('VacancyMonths', 0),
            self.global_settings['year_start'], 
            self.global_settings['year_end']
        )
        
        # Calculate base wages
        if eff_basis == 'Salary':
            wages_base = eff_base_rate * (funded_months / 12) * row['FTE']
        else:
            wages_base = eff_hours_pp * eff_base_rate * self.global_settings['pay_periods'] * (funded_months / 12) * row['FTE']
        
        # Calculate overtime
        if eff_basis == 'Salary':
            # Overtime not typically applicable to salary positions
            wages_ot = 0
        else:
            wages_ot = eff_ot_hours * eff_base_rate * 1.5 * self.global_settings['pay_periods'] * (funded_months / 12) * row['FTE']
        
        # Calculate benefits
        if eff_benefits_monthly > 0:
            # Use employee-specific benefits
            benefits = eff_benefits_monthly * funded_months * row['FTE']
        else:
            # Use standard percentage
            total_wages = wages_base + wages_ot
            benefits = total_wages * self.global_settings['std_benefits_pct']
        
        # Calculate taxes (employer portion)
        total_wages = wages_base + wages_ot
        fica_tax = min(total_wages, self.global_settings['fica_wage_base']) * self.global_settings['fica_pct']
        medicare_tax = total_wages * self.global_settings['medicare_pct']
        retirement_tax = total_wages * self.global_settings['retirement_pct']
        unemployment_tax = min(total_wages, self.global_settings['unemployment_base']) * self.global_settings['unemployment_pct']
        workers_comp_tax = total_wages * self.global_settings['workers_comp_pct']
        
        total_taxes = fica_tax + medicare_tax + retirement_tax + unemployment_tax + workers_comp_tax
        
        # Total cost
        total_cost = wages_base + wages_ot + benefits + total_taxes
        
        # Annual cost (if position is not full year)
        annual_cost = total_cost * (12 / funded_months) if funded_months > 0 else 0
        
        # Effective rate calculation
        if eff_basis == 'Hourly':
            total_hours = (eff_hours_pp + eff_ot_hours) * self.global_settings['pay_periods'] * (funded_months / 12) * row['FTE']
            effective_rate = total_cost / total_hours if total_hours > 0 else 0
        else:
            # For salary, calculate effective hourly rate
            total_hours = 40 * 52 * (funded_months / 12) * row['FTE']  # Assume 40 hours/week
            effective_rate = total_cost / total_hours if total_hours > 0 else 0
        
        return {
            'FundedMonths': round(funded_months, 2),
            'WagesBase': round(wages_base, 2),
            'WagesOT': round(wages_ot, 2),
            'Benefits': round(benefits, 2),
            'Taxes': round(total_taxes, 2),
            'TotalCost': round(total_cost, 2),
            'AnnualCost': round(annual_cost, 2),
            'EffectiveRate': round(effective_rate, 2)
        }
    
    def _calculate_funded_months(self, hire_start: Optional[date], hire_end: Optional[date], 
                               vacancy_months: float, year_start: date, year_end: date) -> float:
        """Calculate funded months based on hire dates and vacancy"""
        # Handle None values properly
        vacancy_months = vacancy_months or 0
        
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
    
    def _generate_simulated_actuals(self, position, year):
        """Generate simulated actual data based on position and year"""
        # Base multipliers by year (simulate actual cost trends)
        year_multipliers = {
            "2024": 0.95,  # Actuals typically 95% of current budget
            "2023": 0.88,  # 88% for previous year
            "2022": 0.82,  # 82% for 2022
            "2021": 0.78,  # 78% for 2021
            "2020": 0.75   # 75% for 2020
        }
        
        # Position-based salary estimates (annual)
        position_estimates = {
            'City Manager': 120000,
            'Finance Director': 95000,
            'Public Works Director': 85000,
            'Police Chief': 90000,
            'Fire Chief': 88000,
            'Administrative Assistant': 45000,
            'Accountant': 55000,
            'Librarian': 50000,
            'Library Assistant': 35000,
            'Maintenance Worker': 42000,
            'Police Officer': 65000,
            'Firefighter': 55000,
            'Dispatcher': 40000,
            'Utilities Manager': 70000,
            'Engineer': 75000,
            'Clerk': 38000,
            'default': 50000
        }
        
        multiplier = year_multipliers.get(year, 0.80)
        base_salary = position_estimates.get(position, position_estimates['default'])
        
        # Simulate actual costs with some variance
        import random
        variance = random.uniform(0.9, 1.1)  # ±10% variance
        
        wages_base = base_salary * multiplier * variance
        wages_ot = wages_base * 0.08 * variance  # ~8% overtime
        benefits = (wages_base + wages_ot) * 0.30 * variance  # ~30% benefits
        total_cost = wages_base + wages_ot + benefits
        
        return {
            'wages_base': wages_base,
            'wages_ot': wages_ot,
            'benefits': benefits,
            'total_cost': total_cost
        }