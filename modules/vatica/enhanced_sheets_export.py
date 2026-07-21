"""
Enhanced Google Sheets Export Functions for Vatica Module

Provides advanced export capabilities including batch exports, multi-sheet workbooks,
smart formatting, and integration with ML features.

ARCHITECTURAL DECISION: Enhanced export capabilities
WHY: Users need sophisticated export options to handle complex financial data,
multiple datasets, and AI-generated insights. This module provides professional-grade
export functionality that maintains data integrity while improving usability.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import io

class EnhancedSheetsExporter:
    """Advanced Google Sheets export functionality with smart features"""
    
    def __init__(self, sheets_service):
        """Initialize enhanced exporter with sheets service"""
        self.service = sheets_service
        self.batch_queue = []
        self.export_history = []
    
    def batch_export(self, datasets: Dict[str, pd.DataFrame], spreadsheet_id: str, 
                     create_navigation: bool = True) -> Dict[str, Any]:
        """
        Export multiple datasets to a single spreadsheet
        
        Args:
            datasets: Dictionary of sheet_name -> DataFrame
            spreadsheet_id: Target spreadsheet ID
            create_navigation: Whether to create navigation sheet
            
        Returns:
            Export result with status and details
        """
        try:
            requests = []
            sheet_id = 0
            
            # Create navigation sheet if requested
            if create_navigation:
                nav_sheet_id = self._create_navigation_sheet(datasets.keys())
                sheet_id = 1
            
            # Process each dataset
            for sheet_name, data in datasets.items():
                # Clean sheet name (Google Sheets has restrictions)
                clean_name = self._clean_sheet_name(sheet_name)
                
                # Create sheet
                requests.append({
                    "addSheet": {
                        "properties": {
                            "sheetId": sheet_id,
                            "title": clean_name,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        }
                    }
                })
                
                # Apply smart formatting
                format_requests = self._generate_smart_formatting(sheet_id, data)
                requests.extend(format_requests)
                
                # Add data validation if applicable
                validation_requests = self._generate_data_validation(sheet_id, data)
                requests.extend(validation_requests)
                
                sheet_id += 1
            
            # Execute batch update
            if requests:
                body = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
            
            # Write data to sheets
            for sheet_name, data in datasets.items():
                clean_name = self._clean_sheet_name(sheet_name)
                self._write_dataframe_to_sheet(spreadsheet_id, clean_name, data)
            
            # Add to export history
            self.export_history.append({
                'timestamp': datetime.now(),
                'type': 'batch_export',
                'sheets': list(datasets.keys()),
                'row_count': sum(len(df) for df in datasets.values()),
                'status': 'success'
            })
            
            return {
                'success': True,
                'message': f"Successfully exported {len(datasets)} datasets",
                'sheets_created': list(datasets.keys()),
                'total_rows': sum(len(df) for df in datasets.values())
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_ml_results(self, spreadsheet_id: str, results_type: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Export ML/AI results with specialized formatting
        
        Args:
            spreadsheet_id: Target spreadsheet ID
            results_type: Type of ML results (anomaly, grant_matching, economic_indicators, etc.)
            data: Results DataFrame
            
        Returns:
            Export result
        """
        try:
            if results_type == "anomaly_detection":
                return self._export_anomaly_results(spreadsheet_id, data)
            elif results_type == "grant_matching":
                return self._export_grant_matches(spreadsheet_id, data)
            elif results_type == "economic_indicators":
                return self._export_economic_indicators(spreadsheet_id, data)
            elif results_type == "rag_statistics":
                return self._export_rag_statistics(spreadsheet_id, data)
            elif results_type == "scenario_planning":
                return self._export_scenario_results(spreadsheet_id, data)
            else:
                # Default ML export
                return self._export_generic_ml_results(spreadsheet_id, data)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to export ML results: {str(e)}"
            }
    
    def _export_anomaly_results(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Export anomaly detection results with highlighting"""
        requests = []
        
        # Create anomaly sheet with special formatting
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Anomaly Detection Results",
                    "tabColor": {"red": 1, "green": 0.2, "blue": 0.2}
                }
            }
        })
        
        # Add conditional formatting for anomaly scores
        if 'anomaly_score' in data.columns or 'confidence' in data.columns:
            score_col = 'anomaly_score' if 'anomaly_score' in data.columns else 'confidence'
            col_index = data.columns.get_loc(score_col)
            
            # High anomaly scores in red
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": 0,
                            "startRowIndex": 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "gradientRule": {
                            "minpoint": {"color": {"green": 0.8}, "type": "NUMBER", "value": "0"},
                            "midpoint": {"color": {"red": 1, "green": 1}, "type": "NUMBER", "value": "0.5"},
                            "maxpoint": {"color": {"red": 1}, "type": "NUMBER", "value": "1"}
                        }
                    }
                }
            })
        
        # Add summary statistics sheet
        summary_data = self._calculate_anomaly_summary(data)
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Anomaly Summary",
                    "tabColor": {"red": 0.8, "green": 0.2, "blue": 0.2}
                }
            }
        })
        
        # Execute updates
        body = {'requests': requests}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Write data
        self._write_dataframe_to_sheet(spreadsheet_id, "Anomaly Detection Results", data)
        self._write_dataframe_to_sheet(spreadsheet_id, "Anomaly Summary", summary_data)
        
        return {
            'success': True,
            'message': f"Exported {len(data)} anomalies with confidence scores"
        }
    
    def _export_grant_matches(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Export grant matching results with application tracking"""
        requests = []
        
        # Create grant opportunities sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Grant Opportunities",
                    "tabColor": {"red": 0.2, "green": 0.8, "blue": 0.2}
                }
            }
        })
        
        # Add deadline highlighting
        if 'deadline' in data.columns:
            # Convert deadline to days remaining
            data['days_to_deadline'] = pd.to_datetime(data['deadline']) - datetime.now()
            data['days_to_deadline'] = data['days_to_deadline'].dt.days
            
            # Highlight upcoming deadlines
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": 0}],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_LESS",
                                "values": [{"userEnteredValue": "30"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 1, "green": 0.9, "blue": 0.7}
                            }
                        }
                    }
                }
            })
        
        # Add matching score formatting
        if 'match_score' in data.columns:
            col_index = data.columns.get_loc('match_score')
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": 0,
                            "startRowIndex": 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "gradientRule": {
                            "minpoint": {"color": {"red": 1}, "type": "NUMBER", "value": "0"},
                            "midpoint": {"color": {"red": 1, "green": 1}, "type": "NUMBER", "value": "50"},
                            "maxpoint": {"color": {"green": 1}, "type": "NUMBER", "value": "100"}
                        }
                    }
                }
            })
        
        # Create application tracker sheet
        tracker_data = self._create_grant_tracker(data)
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Application Tracker",
                    "gridProperties": {"frozenRowCount": 1}
                }
            }
        })
        
        # Execute updates
        body = {'requests': requests}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Write data
        self._write_dataframe_to_sheet(spreadsheet_id, "Grant Opportunities", data)
        self._write_dataframe_to_sheet(spreadsheet_id, "Application Tracker", tracker_data)
        
        return {
            'success': True,
            'message': f"Exported {len(data)} grant opportunities with tracking"
        }
    
    def _export_economic_indicators(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Export economic indicators with trend analysis"""
        requests = []
        
        # Create dashboard sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Economic Indicators",
                    "tabColor": {"red": 0.3, "green": 0.3, "blue": 1}
                }
            }
        })
        
        # Add YoY comparison if date column exists
        if 'date' in data.columns:
            data['year'] = pd.to_datetime(data['date']).dt.year
            yoy_comparison = data.pivot_table(
                index='indicator' if 'indicator' in data.columns else None,
                columns='year',
                values='value' if 'value' in data.columns else data.select_dtypes(include=[np.number]).columns[0],
                aggfunc='mean'
            )
            
            # Create YoY sheet
            requests.append({
                "addSheet": {
                    "properties": {
                        "title": "Year-over-Year",
                        "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 1}
                    }
                }
            })
        
        # Add sparkline charts for trends
        requests.append({
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Economic Trends",
                        "basicChart": {
                            "chartType": "LINE",
                            "legendPosition": "RIGHT_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Period"},
                                {"position": "LEFT_AXIS", "title": "Value"}
                            ]
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": 0, "rowIndex": 15, "columnIndex": 1}
                        }
                    }
                }
            }
        })
        
        # Add benchmark comparisons
        if 'benchmark' in data.columns:
            # Color code based on benchmark performance
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": 0}],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": "=$B2>$C2"}]
                            },
                            "format": {
                                "backgroundColor": {"green": 0.9}
                            }
                        }
                    }
                }
            })
        
        # Execute updates
        body = {'requests': requests}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Write data
        self._write_dataframe_to_sheet(spreadsheet_id, "Economic Indicators", data)
        if 'date' in data.columns:
            self._write_dataframe_to_sheet(spreadsheet_id, "Year-over-Year", yoy_comparison)
        
        return {
            'success': True,
            'message': "Exported economic indicators with trend analysis"
        }
    
    def _export_rag_statistics(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Export RAG index statistics and usage metrics"""
        requests = []
        
        # Create RAG statistics sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "RAG Index Statistics",
                    "tabColor": {"red": 0.5, "green": 0.2, "blue": 0.8}
                }
            }
        })
        
        # Calculate statistics
        stats = {
            'Total Documents': len(data) if not data.empty else 0,
            'Average Document Length': data['content_length'].mean() if 'content_length' in data.columns else 0,
            'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Coverage Score': self._calculate_coverage_score(data)
        }
        
        stats_df = pd.DataFrame(list(stats.items()), columns=['Metric', 'Value'])
        
        # Create usage metrics sheet
        if 'query_count' in data.columns or 'access_count' in data.columns:
            usage_data = self._calculate_usage_metrics(data)
            requests.append({
                "addSheet": {
                    "properties": {
                        "title": "Usage Metrics",
                        "gridProperties": {"frozenRowCount": 1}
                    }
                }
            })
        
        # Add heatmap for document relevance
        if 'relevance_score' in data.columns:
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
        
        # Execute updates
        body = {'requests': requests}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Write data
        self._write_dataframe_to_sheet(spreadsheet_id, "RAG Index Statistics", stats_df)
        if 'query_count' in data.columns or 'access_count' in data.columns:
            self._write_dataframe_to_sheet(spreadsheet_id, "Usage Metrics", usage_data)
        
        return {
            'success': True,
            'message': "Exported RAG index statistics and metrics"
        }
    
    def _export_scenario_results(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Export scenario planning results with comparisons"""
        requests = []
        
        # Create scenario comparison matrix
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Scenario Comparison",
                    "gridProperties": {
                        "frozenRowCount": 1,
                        "frozenColumnCount": 1
                    }
                }
            }
        })
        
        # Pivot scenarios for comparison if scenario column exists
        if 'scenario' in data.columns:
            comparison_matrix = data.pivot_table(
                index='metric' if 'metric' in data.columns else data.columns[0],
                columns='scenario',
                values='value' if 'value' in data.columns else data.select_dtypes(include=[np.number]).columns[0],
                aggfunc='mean'
            )
            
            # Add impact analysis sheet
            requests.append({
                "addSheet": {
                    "properties": {
                        "title": "Impact Analysis",
                        "tabColor": {"red": 0.7, "green": 0.3, "blue": 0.3}
                    }
                }
            })
            
            # Calculate impacts
            if 'baseline' in comparison_matrix.columns:
                for col in comparison_matrix.columns:
                    if col != 'baseline':
                        comparison_matrix[f'{col}_impact'] = (
                            (comparison_matrix[col] - comparison_matrix['baseline']) / 
                            comparison_matrix['baseline'] * 100
                        )
        
        # Add sensitivity analysis
        sensitivity_data = self._calculate_sensitivity(data)
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "Sensitivity Analysis",
                    "gridProperties": {"frozenRowCount": 1}
                }
            }
        })
        
        # Color code based on impact magnitude
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0}],
                    "gradientRule": {
                        "minpoint": {"color": {"red": 1}, "type": "NUMBER", "value": "-20"},
                        "midpoint": {"color": {"red": 1, "green": 1}, "type": "NUMBER", "value": "0"},
                        "maxpoint": {"color": {"green": 1}, "type": "NUMBER", "value": "20"}
                    }
                }
            }
        })
        
        # Execute updates
        body = {'requests': requests}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Write data
        if 'scenario' in data.columns:
            self._write_dataframe_to_sheet(spreadsheet_id, "Scenario Comparison", comparison_matrix)
        self._write_dataframe_to_sheet(spreadsheet_id, "Sensitivity Analysis", sensitivity_data)
        
        return {
            'success': True,
            'message': "Exported scenario planning results with analysis"
        }
    
    def _export_generic_ml_results(self, spreadsheet_id: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Generic ML results export with smart detection"""
        requests = []
        
        # Detect ML-specific columns
        ml_columns = self._detect_ml_columns(data)
        
        # Create main results sheet
        requests.append({
            "addSheet": {
                "properties": {
                    "title": "ML Results",
                    "tabColor": {"red": 0.5, "green": 0.2, "blue": 0.8}
                }
            }
        })
        
        # Apply formatting based on detected columns
        if 'confidence' in ml_columns or 'probability' in ml_columns:
            # Add confidence score formatting
            col_name = 'confidence' if 'confidence' in ml_columns else 'probability'
            col_index = data.columns.get_loc(col_name)
            
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 1,
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "PERCENT",
                                "pattern": "0.00%"
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
        
        # Execute updates
        body = {'requests': requests}
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        # Write data
        self._write_dataframe_to_sheet(spreadsheet_id, "ML Results", data)
        
        return {
            'success': True,
            'message': f"Exported {len(data)} ML results"
        }
    
    def apply_smart_formatting(self, spreadsheet_id: str, sheet_name: str, data: pd.DataFrame) -> bool:
        """
        Apply intelligent formatting based on data types
        
        Args:
            spreadsheet_id: Target spreadsheet
            sheet_name: Sheet to format
            data: DataFrame to analyze for formatting
            
        Returns:
            Success status
        """
        try:
            requests = self._generate_smart_formatting(0, data)
            
            if requests:
                body = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
            
            return True
        except Exception:
            return False
    
    def _generate_smart_formatting(self, sheet_id: int, data: pd.DataFrame) -> List[Dict]:
        """Generate formatting requests based on data types"""
        requests = []
        
        for col_idx, col_name in enumerate(data.columns):
            col_data = data[col_name]
            
            # Detect data type and apply appropriate formatting
            if pd.api.types.is_numeric_dtype(col_data):
                # Check if it's currency (common patterns)
                if any(keyword in col_name.lower() for keyword in ['amount', 'cost', 'price', 'revenue', 'expense', 'budget']):
                    # Currency formatting
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": col_idx,
                                "endColumnIndex": col_idx + 1
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
                elif any(keyword in col_name.lower() for keyword in ['percent', 'rate', 'ratio', 'utilization']):
                    # Percentage formatting
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": col_idx,
                                "endColumnIndex": col_idx + 1
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {
                                        "type": "PERCENT",
                                        "pattern": "0.00%"
                                    }
                                }
                            },
                            "fields": "userEnteredFormat.numberFormat"
                        }
                    })
                else:
                    # General number formatting
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": col_idx,
                                "endColumnIndex": col_idx + 1
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {
                                        "type": "NUMBER",
                                        "pattern": "#,##0.00"
                                    }
                                }
                            },
                            "fields": "userEnteredFormat.numberFormat"
                        }
                    })
            
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                # Date formatting
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "DATE",
                                    "pattern": "yyyy-mm-dd"
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                })
        
        # Bold headers
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor)"
            }
        })
        
        return requests
    
    def _generate_data_validation(self, sheet_id: int, data: pd.DataFrame) -> List[Dict]:
        """Generate data validation rules based on data patterns"""
        requests = []
        
        for col_idx, col_name in enumerate(data.columns):
            col_data = data[col_name]
            
            # Add validation for specific column types
            if 'status' in col_name.lower():
                # Dropdown for status columns
                unique_values = col_data.dropna().unique().tolist()[:10]  # Limit to 10 options
                if unique_values:
                    requests.append({
                        "setDataValidation": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": col_idx,
                                "endColumnIndex": col_idx + 1
                            },
                            "rule": {
                                "condition": {
                                    "type": "ONE_OF_LIST",
                                    "values": [{"userEnteredValue": str(val)} for val in unique_values]
                                },
                                "showCustomUi": True
                            }
                        }
                    })
            
            elif 'email' in col_name.lower():
                # Email validation
                requests.append({
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "rule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": '=REGEXMATCH(TO_TEXT(A2),"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")'}]
                            },
                            "inputMessage": "Please enter a valid email address"
                        }
                    }
                })
        
        return requests
    
    def create_pivot_table(self, spreadsheet_id: str, source_data: pd.DataFrame, 
                          pivot_config: Dict[str, Any]) -> bool:
        """
        Create a pivot table in the spreadsheet
        
        Args:
            spreadsheet_id: Target spreadsheet
            source_data: Source data for pivot
            pivot_config: Configuration for pivot table
            
        Returns:
            Success status
        """
        try:
            # Write source data first
            self._write_dataframe_to_sheet(spreadsheet_id, "Source Data", source_data)
            
            # Create pivot table request
            requests = [{
                "addSheet": {
                    "properties": {
                        "title": "Pivot Table"
                    }
                }
            }]
            
            # Add pivot table
            requests.append({
                "updateCells": {
                    "rows": [{
                        "values": [{
                            "pivotTable": {
                                "source": {
                                    "sheetId": 0,
                                    "startRowIndex": 0,
                                    "startColumnIndex": 0
                                },
                                "rows": pivot_config.get('rows', []),
                                "columns": pivot_config.get('columns', []),
                                "values": pivot_config.get('values', [])
                            }
                        }]
                    }],
                    "start": {
                        "sheetId": 1,
                        "rowIndex": 0,
                        "columnIndex": 0
                    },
                    "fields": "pivotTable"
                }
            })
            
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            return True
        except Exception:
            return False
    
    # Helper methods
    def _clean_sheet_name(self, name: str) -> str:
        """Clean sheet name to meet Google Sheets requirements"""
        # Remove invalid characters
        invalid_chars = ['/', '\\', '?', '*', '[', ']', ':']
        for char in invalid_chars:
            name = name.replace(char, '')
        
        # Truncate to 100 characters (Google Sheets limit)
        return name[:100]
    
    def _create_navigation_sheet(self, sheet_names: List[str]) -> int:
        """Create a navigation sheet with links to other sheets"""
        # Implementation for navigation sheet
        return 0
    
    def _write_dataframe_to_sheet(self, spreadsheet_id: str, sheet_name: str, data: pd.DataFrame):
        """Write DataFrame to a specific sheet"""
        # Handle datetime columns
        for col in data.select_dtypes(include=['datetime64']).columns:
            data[col] = data[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Convert to values
        values = [data.columns.tolist()] + data.fillna('').values.tolist()
        
        # Write to sheet
        body = {'values': values}
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption='RAW',
            body=body
        ).execute()
    
    def _calculate_anomaly_summary(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate summary statistics for anomalies"""
        summary = {
            'Total Anomalies': len(data),
            'High Risk': len(data[data.get('risk_level', '') == 'high']) if 'risk_level' in data.columns else 0,
            'Medium Risk': len(data[data.get('risk_level', '') == 'medium']) if 'risk_level' in data.columns else 0,
            'Low Risk': len(data[data.get('risk_level', '') == 'low']) if 'risk_level' in data.columns else 0,
            'Average Confidence': data['confidence'].mean() if 'confidence' in data.columns else 0,
            'Departments Affected': data['department'].nunique() if 'department' in data.columns else 0
        }
        
        return pd.DataFrame(list(summary.items()), columns=['Metric', 'Value'])
    
    def _create_grant_tracker(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create grant application tracking sheet"""
        tracker = pd.DataFrame({
            'Grant Name': data['grant_name'] if 'grant_name' in data.columns else data.index,
            'Status': 'Not Started',
            'Application Date': '',
            'Deadline': data['deadline'] if 'deadline' in data.columns else '',
            'Amount Requested': '',
            'Match Score': data['match_score'] if 'match_score' in data.columns else '',
            'Notes': ''
        })
        
        return tracker
    
    def _calculate_coverage_score(self, data: pd.DataFrame) -> float:
        """Calculate RAG index coverage score"""
        if data.empty:
            return 0.0
        
        # Simple coverage calculation
        total_docs = len(data)
        indexed_docs = len(data[data.get('indexed', True) == True]) if 'indexed' in data.columns else total_docs
        
        return round(indexed_docs / total_docs * 100, 2)
    
    def _calculate_usage_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate usage metrics for RAG index"""
        metrics = {
            'Total Queries': data['query_count'].sum() if 'query_count' in data.columns else 0,
            'Unique Users': data['user_id'].nunique() if 'user_id' in data.columns else 0,
            'Average Response Time': data['response_time'].mean() if 'response_time' in data.columns else 0,
            'Success Rate': data['success'].mean() * 100 if 'success' in data.columns else 100
        }
        
        return pd.DataFrame(list(metrics.items()), columns=['Metric', 'Value'])
    
    def _calculate_sensitivity(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate sensitivity analysis for scenarios"""
        # Simple sensitivity calculation
        if 'scenario' not in data.columns:
            return pd.DataFrame()
        
        scenarios = data['scenario'].unique()
        sensitivity = []
        
        for scenario in scenarios:
            scenario_data = data[data['scenario'] == scenario]
            if not scenario_data.empty:
                numeric_cols = scenario_data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    sensitivity.append({
                        'Scenario': scenario,
                        'Variable': col,
                        'Min': scenario_data[col].min(),
                        'Max': scenario_data[col].max(),
                        'Range': scenario_data[col].max() - scenario_data[col].min(),
                        'StdDev': scenario_data[col].std()
                    })
        
        return pd.DataFrame(sensitivity)
    
    def _detect_ml_columns(self, data: pd.DataFrame) -> List[str]:
        """Detect ML-specific columns in the data"""
        ml_keywords = ['confidence', 'probability', 'score', 'prediction', 'forecast', 
                      'anomaly', 'risk', 'accuracy', 'precision', 'recall', 'f1']
        
        ml_columns = []
        for col in data.columns:
            if any(keyword in col.lower() for keyword in ml_keywords):
                ml_columns.append(col)
        
        return ml_columns


def render_enhanced_export_interface(exporter):
    """
    Render the enhanced export interface in Streamlit
    
    Args:
        exporter: GoogleSheetsExporter instance
    """
    st.subheader("🚀 Enhanced Export Options")
    
    if not exporter.service:
        st.warning("Google Sheets not configured. Please set up credentials first.")
        return
    
    enhanced_exporter = EnhancedSheetsExporter(exporter.service)
    
    # Export type selection
    export_type = st.selectbox(
        "Select Export Type",
        ["Single Dataset", "Batch Export", "ML Results", "Create Pivot Table"]
    )
    
    if export_type == "Batch Export":
        st.markdown("### Batch Export Multiple Datasets")
        
        # Dataset selection
        available_datasets = {
            "Financial Summary": "financial_summary",
            "Department Budgets": "department_budgets",
            "Transaction History": "transactions",
            "Grant Opportunities": "grants",
            "Anomaly Results": "anomalies"
        }
        
        selected_datasets = st.multiselect(
            "Select Datasets to Export",
            list(available_datasets.keys()),
            default=["Financial Summary"]
        )
        
        if selected_datasets:
            # Get spreadsheet ID
            spreadsheet_id = st.text_input(
                "Enter Google Sheets ID",
                placeholder="1abc...xyz",
                help="The ID from the Google Sheets URL"
            )
            
            create_navigation = st.checkbox("Create Navigation Sheet", value=True)
            
            if st.button("Export All Selected", type="primary"):
                if spreadsheet_id:
                    # Prepare datasets (mock data for demonstration)
                    datasets = {}
                    for dataset_name in selected_datasets:
                        # Here you would load actual data
                        datasets[dataset_name] = pd.DataFrame({
                            'Sample Column': [1, 2, 3],
                            'Amount': [1000, 2000, 3000]
                        })
                    
                    with st.spinner("Exporting datasets..."):
                        result = enhanced_exporter.batch_export(
                            datasets, 
                            spreadsheet_id,
                            create_navigation
                        )
                        
                        if result['success']:
                            st.success(result['message'])
                            st.info(f"Created {result['sheets_created']} sheets with {result['total_rows']} total rows")
                        else:
                            st.error(f"Export failed: {result['error']}")
                else:
                    st.error("Please enter a spreadsheet ID")
    
    elif export_type == "ML Results":
        st.markdown("### Export ML/AI Results")
        
        ml_type = st.selectbox(
            "Select ML Results Type",
            ["Anomaly Detection", "Grant Matching", "Economic Indicators", 
             "RAG Statistics", "Scenario Planning"]
        )
        
        # Get spreadsheet ID
        spreadsheet_id = st.text_input(
            "Enter Google Sheets ID",
            placeholder="1abc...xyz",
            help="The ID from the Google Sheets URL"
        )
        
        if st.button("Export ML Results", type="primary"):
            if spreadsheet_id:
                # Mock ML data for demonstration
                if ml_type == "Anomaly Detection":
                    data = pd.DataFrame({
                        'Transaction': ['T001', 'T002', 'T003'],
                        'Amount': [10000, 25000, 50000],
                        'anomaly_score': [0.2, 0.7, 0.9],
                        'risk_level': ['low', 'medium', 'high']
                    })
                else:
                    data = pd.DataFrame({
                        'Item': ['Item1', 'Item2'],
                        'Value': [100, 200]
                    })
                
                ml_type_map = {
                    "Anomaly Detection": "anomaly_detection",
                    "Grant Matching": "grant_matching",
                    "Economic Indicators": "economic_indicators",
                    "RAG Statistics": "rag_statistics",
                    "Scenario Planning": "scenario_planning"
                }
                
                with st.spinner(f"Exporting {ml_type} results..."):
                    result = enhanced_exporter.export_ml_results(
                        spreadsheet_id,
                        ml_type_map[ml_type],
                        data
                    )
                    
                    if result['success']:
                        st.success(result['message'])
                    else:
                        st.error(f"Export failed: {result['error']}")
            else:
                st.error("Please enter a spreadsheet ID")
    
    elif export_type == "Create Pivot Table":
        st.markdown("### Create Pivot Table")
        
        # Pivot configuration
        st.info("Configure your pivot table settings")
        
        row_field = st.text_input("Row Field", value="Department")
        column_field = st.text_input("Column Field", value="Month")
        value_field = st.text_input("Value Field", value="Amount")
        aggregation = st.selectbox("Aggregation", ["SUM", "AVERAGE", "COUNT", "MAX", "MIN"])
        
        spreadsheet_id = st.text_input(
            "Enter Google Sheets ID",
            placeholder="1abc...xyz"
        )
        
        if st.button("Create Pivot Table", type="primary"):
            if spreadsheet_id:
                # Mock data for pivot
                data = pd.DataFrame({
                    'Department': ['IT', 'HR', 'IT', 'HR'],
                    'Month': ['Jan', 'Jan', 'Feb', 'Feb'],
                    'Amount': [1000, 1500, 1200, 1600]
                })
                
                pivot_config = {
                    'rows': [{'sourceColumnIndex': 0}],
                    'columns': [{'sourceColumnIndex': 1}],
                    'values': [{'sourceColumnIndex': 2, 'summarizeFunction': aggregation}]
                }
                
                with st.spinner("Creating pivot table..."):
                    success = enhanced_exporter.create_pivot_table(
                        spreadsheet_id,
                        data,
                        pivot_config
                    )
                    
                    if success:
                        st.success("Pivot table created successfully!")
                    else:
                        st.error("Failed to create pivot table")
            else:
                st.error("Please enter a spreadsheet ID")
    
    # Export history
    if enhanced_exporter.export_history:
        with st.expander("Export History"):
            history_df = pd.DataFrame(enhanced_exporter.export_history)
            st.dataframe(history_df)