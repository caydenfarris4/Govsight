# PBB Spreadsheet Main Interface - Integrated Components
# Excel-style Position-Based Budgeting with editable spreadsheet interface

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Any
import plotly.express as px
from modules.navi.payroll_live_adapter import _get_connection_type, _read_sql, get_positions
import os
import json

# Import the separated modules
from modules.navi.pbb_core import PBBCore
from modules.navi.pbb_calculations import PBBCalculations
from modules.navi.pbb_ui_spreadsheet import PBBSpreadsheetUI
from modules.navi.pbb_ui_export import PBBExportUI

class PBBSpreadsheet:
    """Excel-style Position-Based Budgeting Spreadsheet Interface - Main Coordinator"""
    
    def __init__(self):
        # Initialize core components
        self.core = PBBCore()
        self.calculations = PBBCalculations(self.core.global_settings)
        self.spreadsheet_ui = PBBSpreadsheetUI(self.core, self.calculations)
        self.export_ui = PBBExportUI(self.core, self.calculations)
        
        # Maintain backward compatibility
        self.global_settings = self.core.global_settings
        self.budget_year = self.core.budget_year
        self.employees_data = self.core.employees_data
        self.positions_data = self.core.positions_data
    
    def render_spreadsheet_tab(self):
        """Delegate to spreadsheet UI component"""
        return self.spreadsheet_ui.render_spreadsheet_tab()
    
    def render_export_tab(self):
        """Delegate to export UI component"""
        return self.export_ui.render_export_tab()
    
    def render(self):
        """Main render method with tabs"""
        tab1, tab2 = st.tabs(["Spreadsheet", "Export"])
        
        with tab1:
            self.render_spreadsheet_tab()
        
        with tab2:
            self.render_export_tab()

def render_pbb_spreadsheet():
    """Entry point for PBB Spreadsheet module"""
    pbb = PBBSpreadsheet()
    pbb.render()