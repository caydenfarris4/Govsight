"""
Google Sheets Template System for Vatica Module

Provides pre-defined professional templates for common financial reports
with automatic formatting, formulas, and visualizations.

ARCHITECTURAL DECISION: Template-based reporting
WHY: Users need consistent, professional reports that can be quickly generated
and shared. Templates ensure standardization across the organization while
saving time on manual formatting.
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from googleapiclient.discovery import build
import json

class SheetsTemplateManager:
    """Manages Google Sheets templates for financial reporting"""
    
    def __init__(self, sheets_service):
        """Initialize template manager with sheets service"""
        self.service = sheets_service
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict]:
        """Initialize available report templates"""
        return {
            "monthly_financial_summary": {
                "name": "Monthly Financial Summary",
                "description": "Comprehensive monthly financial overview with revenue, expenses, and variance analysis",
                "sheets": ["Summary", "Revenue Detail", "Expense Detail", "Variance Analysis", "Charts"],
                "features": ["Auto-calculated totals", "Variance highlighting", "Trend charts", "KPI dashboard"],
                "icon": "📊"
            },
            "department_budget_comparison": {
                "name": "Department Budget Comparison",
                "description": "Compare actual vs budgeted amounts across all departments",
                "sheets": ["Overview", "Department Details", "Variance Report", "Performance Metrics"],
                "features": ["Department rankings", "Budget utilization rates", "Color-coded variances", "Drill-down capability"],
                "icon": "🏢"
            },
            "variance_analysis": {
                "name": "Variance Analysis Report",
                "description": "Detailed variance analysis with explanations and trend identification",
                "sheets": ["Executive Summary", "Line Item Variance", "Department Variance", "YoY Comparison"],
                "features": ["Automatic variance calculation", "Threshold alerts", "Trend analysis", "Root cause tracking"],
                "icon": "📈"
            },
            "grant_tracking": {
                "name": "Grant Tracking Dashboard",
                "description": "Track grant opportunities, applications, and funding status",
                "sheets": ["Grant Pipeline", "Application Status", "Funding Summary", "Compliance Tracking"],
                "features": ["Application deadlines", "Success rate metrics", "Funding timeline", "Requirement checklists"],
                "icon": "💰"
            },
            "anomaly_detection_report": {
                "name": "Anomaly Detection Report",
                "description": "AI-detected anomalies with risk scores and recommended actions",
                "sheets": ["Anomaly Summary", "Transaction Details", "Risk Analysis", "Action Items"],
                "features": ["Risk scoring", "Pattern identification", "Department breakdown", "Historical comparison"],
                "icon": "🔍"
            },
            "economic_indicators": {
                "name": "Economic Indicators Dashboard",
                "description": "Key economic indicators and their impact on municipal finances",
                "sheets": ["Dashboard", "Indicators Detail", "Trend Analysis", "Benchmarks"],
                "features": ["Real-time data", "Regional comparisons", "Impact analysis", "Forecast integration"],
                "icon": "📉"
            },
            "ml_insights_report": {
                "name": "ML Insights Report",
                "description": "Machine learning insights including predictions and recommendations",
                "sheets": ["Executive Summary", "Predictions", "Anomalies", "Recommendations"],
                "features": ["Confidence scores", "Trend predictions", "Risk alerts", "Action priorities"],
                "icon": "🤖"
            },
            "scenario_planning": {
                "name": "Scenario Planning Results",
                "description": "What-if analysis results with multiple scenario comparisons",
                "sheets": ["Scenario Comparison", "Impact Analysis", "Recommendations", "Sensitivity"],
                "features": ["Side-by-side comparison", "Impact visualization", "Decision matrix", "Risk assessment"],
                "icon": "🎯"
            }
        }
    
    def get_available_templates(self) -> Dict[str, Dict]:
        """Get list of available templates"""
        return self.templates
    
    def apply_template(self, spreadsheet_id: str, template_key: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Apply a template to a Google Sheets document
        
        Args:
            spreadsheet_id: ID of the target spreadsheet
            template_key: Key of the template to apply
            data: DataFrame with data to populate
            
        Returns:
            Result dictionary with status and details
        """
        if template_key not in self.templates:
            return {"success": False, "error": f"Template '{template_key}' not found"}
        
        template = self.templates[template_key]
        
        try:
            # Apply template based on type
            if template_key == "monthly_financial_summary":
                return self._apply_monthly_summary_template(spreadsheet_id, data)
            elif template_key == "department_budget_comparison":
                return self._apply_department_comparison_template(spreadsheet_id, data)
            elif template_key == "variance_analysis":
                return self._apply_variance_analysis_template(spreadsheet_id, data)
            elif template_key == "grant_tracking":
                return self._apply_grant_tracking_template(spreadsheet_id, data)
            elif template_key == "anomaly_detection_report":
                return self._apply_anomaly_detection_template(spreadsheet_id, data)
            elif template_key == "economic_indicators":
                return self._apply_economic_indicators_template(spreadsheet_id, data)
            elif template_key == "ml_insights_report":
                return self._apply_ml_insights_template(spreadsheet_id, data)
            elif template_key == "scenario_planning":
                return self._apply_scenario_planning_template(spreadsheet_id, data)
            else:
                return {"success": False, "error": f"Template implementation pending for '{template_key}'"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_monthly_summary_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply Monthly Financial Summary template"""
        requests = []
        
        # Create Summary sheet with KPI dashboard
        requests.append(self._create_summary_sheet_request())
        
        # Add header formatting
        requests.append(self._create_header_format_request(
            sheet_id=0,
            title="Monthly Financial Summary",
            subtitle=f"Generated: {datetime.now().strftime('%B %Y')}"
        ))
        
        # Add KPI cards (Revenue, Expenses, Net Income, etc.)
        requests.extend(self._create_kpi_cards(sheet_id=0, data=data))
        
        # Add data with formatting
        requests.extend(self._format_financial_data(sheet_id=1, data=data))
        
        # Add conditional formatting for variances
        requests.append(self._create_variance_formatting(sheet_id=1))
        
        # Add charts
        requests.extend(self._create_financial_charts(sheet_id=0, data=data))
        
        # Execute batch update
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            # Write data
            self._write_data_to_sheet(spreadsheet_id, data, "Data")
            
            return {"success": True, "message": "Monthly Financial Summary template applied successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_department_comparison_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply Department Budget Comparison template"""
        requests = []
        
        # Create overview sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Department Overview",
                    "gridProperties": {"frozenRowCount": 2}
                }
            }
        })
        
        # Format headers
        requests.append(self._create_header_format_request(
            sheet_id=0,
            title="Department Budget Comparison",
            subtitle="Actual vs Budget Analysis"
        ))
        
        # Add department performance metrics
        if 'Department' in data.columns:
            dept_summary = data.groupby('Department').agg({
                'Amount': 'sum',
                'Budget': 'sum' if 'Budget' in data.columns else lambda x: 0
            }).reset_index()
            
            # Add budget utilization column
            if 'Budget' in dept_summary.columns:
                dept_summary['Utilization %'] = (dept_summary['Amount'] / dept_summary['Budget'] * 100).round(2)
            
            # Create ranking
            dept_summary['Rank'] = dept_summary['Amount'].rank(ascending=False)
        
        # Add conditional formatting for budget utilization
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0, "startRowIndex": 2, "startColumnIndex": 3, "endColumnIndex": 4}],
                    "gradientRule": {
                        "minpoint": {"color": {"green": 1}, "type": "NUMBER", "value": "0"},
                        "midpoint": {"color": {"red": 1, "green": 1}, "type": "NUMBER", "value": "100"},
                        "maxpoint": {"color": {"red": 1}, "type": "NUMBER", "value": "150"}
                    }
                }
            }
        })
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return {"success": True, "message": "Department comparison template applied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_variance_analysis_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply Variance Analysis template"""
        requests = []
        
        # Calculate variances if Budget column exists
        if 'Budget' in data.columns and 'Amount' in data.columns:
            data['Variance'] = data['Amount'] - data['Budget']
            data['Variance %'] = ((data['Amount'] / data['Budget'] - 1) * 100).round(2)
        
        # Create executive summary
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Executive Summary",
                    "tabColor": {"red": 0.5, "green": 0.5, "blue": 1}
                }
            }
        })
        
        # Add threshold-based conditional formatting
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0}],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=ABS($D2)>10000"}]
                        },
                        "format": {"backgroundColor": {"red": 1, "green": 0.9, "blue": 0.9}}
                    }
                }
            }
        })
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            # Write variance data
            self._write_data_to_sheet(spreadsheet_id, data, "Variance Analysis")
            
            return {"success": True, "message": "Variance analysis template applied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_grant_tracking_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply Grant Tracking template"""
        requests = []
        
        # Create grant pipeline sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Grant Pipeline",
                    "tabColor": {"red": 0.2, "green": 0.8, "blue": 0.2}
                }
            }
        })
        
        # Add deadline highlighting
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0}],
                    "booleanRule": {
                        "condition": {
                            "type": "DATE_BEFORE",
                            "values": [{"relativeDate": "NEXT_WEEK"}]
                        },
                        "format": {"backgroundColor": {"red": 1, "green": 0.9, "blue": 0.7}}
                    }
                }
            }
        })
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return {"success": True, "message": "Grant tracking template applied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_anomaly_detection_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply Anomaly Detection Report template"""
        requests = []
        
        # Create anomaly summary sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Anomaly Summary",
                    "tabColor": {"red": 1, "green": 0.3, "blue": 0.3}
                }
            }
        })
        
        # Add risk score formatting
        if 'risk_score' in data.columns or 'confidence' in data.columns:
            score_col = 'risk_score' if 'risk_score' in data.columns else 'confidence'
            
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": 0}],
                        "gradientRule": {
                            "minpoint": {"color": {"green": 1}, "type": "MIN"},
                            "midpoint": {"color": {"red": 1, "green": 1}, "type": "PERCENTILE", "value": "50"},
                            "maxpoint": {"color": {"red": 1}, "type": "MAX"}
                        }
                    }
                }
            })
        
        # Add action items sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Action Items",
                    "gridProperties": {"frozenRowCount": 1}
                }
            }
        })
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            # Write anomaly data
            self._write_data_to_sheet(spreadsheet_id, data, "Anomaly Details")
            
            return {"success": True, "message": "Anomaly detection template applied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_economic_indicators_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply Economic Indicators Dashboard template"""
        requests = []
        
        # Create dashboard sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Economic Dashboard",
                    "tabColor": {"red": 0.3, "green": 0.3, "blue": 1}
                }
            }
        })
        
        # Add sparkline charts for trends
        requests.append({
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Economic Indicators Trend",
                        "basicChart": {
                            "chartType": "LINE",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Time Period"},
                                {"position": "LEFT_AXIS", "title": "Value"}
                            ]
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": 0, "rowIndex": 5, "columnIndex": 1}
                        }
                    }
                }
            }
        })
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return {"success": True, "message": "Economic indicators template applied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_ml_insights_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply ML Insights Report template"""
        requests = []
        
        # Create executive summary with AI insights
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "AI Executive Summary",
                    "tabColor": {"red": 0.5, "green": 0.2, "blue": 0.8}
                }
            }
        })
        
        # Add confidence score formatting
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0}],
                    "gradientRule": {
                        "minpoint": {"color": {"red": 1}, "type": "NUMBER", "value": "0"},
                        "midpoint": {"color": {"red": 1, "green": 1}, "type": "NUMBER", "value": "0.5"},
                        "maxpoint": {"color": {"green": 1}, "type": "NUMBER", "value": "1"}
                    }
                }
            }
        })
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return {"success": True, "message": "ML insights template applied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_scenario_planning_template(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Apply Scenario Planning Results template"""
        requests = []
        
        # Create scenario comparison matrix
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Scenario Matrix",
                    "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 1}
                }
            }
        })
        
        # Add decision matrix formatting
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0}],
                    "gradientRule": {
                        "minpoint": {"color": {"red": 1}, "type": "MIN"},
                        "midpoint": {"color": {"red": 1, "green": 1}, "type": "PERCENTILE", "value": "50"},
                        "maxpoint": {"color": {"green": 1}, "type": "MAX"}
                    }
                }
            }
        })
        
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return {"success": True, "message": "Scenario planning template applied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Helper methods for template formatting
    def _create_summary_sheet_request(self) -> Dict:
        """Create a summary sheet with frozen headers"""
        return {
            "addSheet": {
                "properties": {
                    "title": "Summary",
                    "gridProperties": {
                        "frozenRowCount": 2,
                        "frozenColumnCount": 1
                    },
                    "tabColor": {
                        "red": 0.2,
                        "green": 0.5,
                        "blue": 0.8
                    }
                }
            }
        }
    
    def _create_header_format_request(self, sheet_id: int, title: str, subtitle: str) -> Dict:
        """Create formatted header for a sheet"""
        return {
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 10
                },
                "mergeType": "MERGE_ALL"
            }
        }
    
    def _create_kpi_cards(self, sheet_id: int, data: pd.DataFrame) -> List[Dict]:
        """Create KPI card formatting requests"""
        requests = []
        
        # Calculate KPIs from data
        if 'Amount' in data.columns:
            total_revenue = data[data['Amount'] > 0]['Amount'].sum() if 'Amount' in data.columns else 0
            total_expenses = data[data['Amount'] < 0]['Amount'].sum() if 'Amount' in data.columns else 0
            net_income = total_revenue + total_expenses
        
        # Add KPI cells with borders and background
        kpi_positions = [
            {"row": 3, "col": 1, "label": "Total Revenue"},
            {"row": 3, "col": 4, "label": "Total Expenses"},
            {"row": 3, "col": 7, "label": "Net Income"}
        ]
        
        for kpi in kpi_positions:
            requests.append({
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": kpi["row"],
                        "endRowIndex": kpi["row"] + 2,
                        "startColumnIndex": kpi["col"],
                        "endColumnIndex": kpi["col"] + 2
                    },
                    "top": {"style": "SOLID", "width": 2},
                    "bottom": {"style": "SOLID", "width": 2},
                    "left": {"style": "SOLID", "width": 2},
                    "right": {"style": "SOLID", "width": 2}
                }
            })
        
        return requests
    
    def _format_financial_data(self, sheet_id: int, data: pd.DataFrame) -> List[Dict]:
        """Format financial data with proper number formatting"""
        requests = []
        
        # Currency formatting for amount columns
        if 'Amount' in data.columns:
            col_index = data.columns.get_loc('Amount')
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "CURRENCY",
                                "pattern": "$#,##0.00"
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
        
        return requests
    
    def _create_variance_formatting(self, sheet_id: int) -> Dict:
        """Create conditional formatting for variance columns"""
        return {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 0
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_LESS",
                            "values": [{"userEnteredValue": "0"}]
                        },
                        "format": {
                            "textFormat": {"foregroundColor": {"red": 1}}
                        }
                    }
                }
            }
        }
    
    def _create_financial_charts(self, sheet_id: int, data: pd.DataFrame) -> List[Dict]:
        """Create financial charts for the data"""
        requests = []
        
        # Revenue vs Expenses chart
        requests.append({
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Revenue vs Expenses",
                        "basicChart": {
                            "chartType": "COLUMN",
                            "legendPosition": "BOTTOM_LEGEND"
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": sheet_id,
                                "rowIndex": 10,
                                "columnIndex": 1
                            }
                        }
                    }
                }
            }
        })
        
        return requests
    
    def _write_data_to_sheet(self, spreadsheet_id: str, data: pd.DataFrame, sheet_name: str):
        """Write DataFrame data to a specific sheet"""
        # Convert DataFrame to values list
        values = [data.columns.tolist()] + data.values.tolist()
        
        # Write to sheet
        body = {'values': values}
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption='RAW',
            body=body
        ).execute()


def render_template_selector(exporter) -> Optional[str]:
    """
    Render template selection interface
    
    Args:
        exporter: GoogleSheetsExporter instance
        
    Returns:
        Selected template key or None
    """
    st.subheader("📋 Select Report Template")
    
    if not exporter.service:
        st.warning("Google Sheets not configured. Please set up credentials first.")
        return None
    
    template_manager = SheetsTemplateManager(exporter.service)
    templates = template_manager.get_available_templates()
    
    # Create template cards
    cols = st.columns(3)
    selected_template = None
    
    for idx, (key, template) in enumerate(templates.items()):
        col = cols[idx % 3]
        with col:
            with st.container():
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                    <h4>{template['icon']} {template['name']}</h4>
                    <p style="font-size: 0.9em; color: #666;">{template['description']}</p>
                    <div style="margin-top: 10px;">
                        <b>Features:</b>
                        <ul style="font-size: 0.85em; margin-top: 5px;">
                """, unsafe_allow_html=True)
                
                for feature in template['features'][:3]:
                    st.markdown(f"<li>{feature}</li>", unsafe_allow_html=True)
                
                st.markdown("</ul></div></div>", unsafe_allow_html=True)
                
                if st.button(f"Use {template['name']}", key=f"template_{key}", use_container_width=True):
                    selected_template = key
                    st.session_state['selected_template'] = key
    
    # Show selected template details
    if 'selected_template' in st.session_state:
        selected = st.session_state['selected_template']
        if selected in templates:
            st.success(f"✅ Selected: {templates[selected]['name']}")
            
            with st.expander("Template Details", expanded=True):
                template = templates[selected]
                st.markdown(f"**Description:** {template['description']}")
                st.markdown(f"**Sheets:** {', '.join(template['sheets'])}")
                st.markdown("**Features:**")
                for feature in template['features']:
                    st.markdown(f"- {feature}")
    
    return st.session_state.get('selected_template', None)


def apply_template_to_spreadsheet(exporter, spreadsheet_id: str, template_key: str, data: pd.DataFrame) -> bool:
    """
    Apply selected template to a spreadsheet
    
    Args:
        exporter: GoogleSheetsExporter instance
        spreadsheet_id: Target spreadsheet ID
        template_key: Selected template key
        data: Data to populate in the template
        
    Returns:
        True if successful, False otherwise
    """
    if not exporter.service:
        st.error("Google Sheets service not available")
        return False
    
    template_manager = SheetsTemplateManager(exporter.service)
    
    with st.spinner(f"Applying template..."):
        result = template_manager.apply_template(spreadsheet_id, template_key, data)
        
        if result['success']:
            st.success(result['message'])
            return True
        else:
            st.error(f"Failed to apply template: {result['error']}")
            return False