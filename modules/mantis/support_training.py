"""
Mantis Support Training Module
Implements machine learning capabilities to train Mantis as a comprehensive support tool
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import pickle
from datetime import datetime
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
import sqlite3

class MantisKnowledgeBase:
    """Knowledge base for Mantis support capabilities"""
    
    def __init__(self):
        self.software_knowledge = self._initialize_software_knowledge()
        self.process_workflows = self._initialize_process_workflows()
        self.common_issues = self._initialize_common_issues()
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.support_model = None
        self.knowledge_vectors = None
        
    def _initialize_software_knowledge(self) -> Dict[str, Any]:
        """Initialize comprehensive knowledge about GovSight software"""
        return {
            "modules": {
                "navi": {
                    "name": "Navigation & Planning Hub",
                    "functions": [
                        "Scenario Planning",
                        "BI Sandbox", 
                        "Custom Visualizations",
                        "Monte Carlo Simulation",
                        "Position-Based Budgeting (Enhanced)",
                        "Municipal Investment Optimizer"
                    ],
                    "use_cases": [
                        "Budget scenario modeling",
                        "Data visualization and analysis",
                        "Financial forecasting",
                        "Risk assessment",
                        "Personnel budget management",
                        "Investment opportunity analysis"
                    ],
                    "key_features": [
                        "What-if analysis",
                        "Interactive charts",
                        "Export capabilities",
                        "Statistical analysis",
                        "Position history tracking",
                        "AI-powered budget insights",
                        "Union contract compliance",
                        "Department comparisons"
                    ],
                    "pbb_advanced_features": {
                        "position_history": {
                            "name": "Position History Audit Trail",
                            "description": "Track all changes to positions with timestamp, user, and field-level detail",
                            "capabilities": [
                                "View last 50 position changes",
                                "Filter by date, user, or position",
                                "Track field-level modifications",
                                "Export audit history"
                            ]
                        },
                        "advanced_filtering": {
                            "name": "Advanced Filtering Panel",
                            "description": "Multi-dimensional filtering for position data analysis",
                            "filters": [
                                "Salary range (min/max)",
                                "Department selection",
                                "Employment status (Filled/Vacant/Frozen)",
                                "Funding source (General/Grant/Enterprise)",
                                "Benefit package type",
                                "Data source (Payroll/Manual/FY Actuals)"
                            ]
                        },
                        "ai_budget_assistant": {
                            "name": "AI Budget Assistant",
                            "description": "Mantis-powered budget analysis and recommendations",
                            "analysis_types": [
                                "Anomaly Detection - Identify unusual patterns",
                                "Market Rate Comparison - Benchmark salaries",
                                "Cost Savings Recommendations - Find efficiencies",
                                "Grant Opportunities - Match positions to funding"
                            ]
                        },
                        "pdf_budget_book": {
                            "name": "PDF Budget Book Export",
                            "description": "Generate comprehensive budget documentation",
                            "contents": [
                                "Cover page with fiscal year",
                                "Executive summary with key metrics",
                                "Department-by-department breakdowns",
                                "Position detail listings",
                                "Budget totals and analysis"
                            ]
                        },
                        "union_compliance": {
                            "name": "Union Contract Compliance Checker",
                            "description": "Automated validation against union rules",
                            "rules": [
                                "Maximum overtime hours per week",
                                "Minimum step increase percentage",
                                "Maximum annual salary increase",
                                "Minimum FTE for benefits eligibility"
                            ]
                        },
                        "department_comparison": {
                            "name": "Department Comparison Mode",
                            "description": "Side-by-side departmental analysis",
                            "metrics": [
                                "Position count comparison",
                                "Total budget comparison",
                                "Difference calculations",
                                "Percentage variance indicators"
                            ]
                        },
                        "quick_actions": {
                            "name": "What-If Scenario Modeling (Quick Actions)",
                            "description": "Bulk operations for scenario planning",
                            "actions": [
                                "Apply COLA - Cost of living adjustments",
                                "Hiring Freeze - Freeze vacant positions",
                                "Merit Increase - Apply performance raises",
                                "Step Increase - Advance eligible employees",
                                "Bulk Overtime - Adjust overtime calculations"
                            ]
                        }
                    }
                },
                "mantis": {
                    "name": "AI Intelligence Hub",
                    "functions": [
                        "AI Assistant",
                        "Grant Intelligence",
                        "Document Analysis",
                        "Strategic Recommendations"
                    ],
                    "use_cases": [
                        "Natural language queries",
                        "Grant opportunity identification",
                        "Document processing",
                        "Financial insights"
                    ],
                    "key_features": [
                        "ChatGPT-style interface",
                        "Grant database search",
                        "PDF analysis",
                        "AI-powered insights"
                    ]
                },
                "vatica": {
                    "name": "Document & Collaboration Hub",
                    "functions": [
                        "Document Management",
                        "Annotation System",
                        "Collaborative Review",
                        "Version Control"
                    ],
                    "use_cases": [
                        "Document annotation",
                        "Collaborative editing",
                        "Review workflows",
                        "Content management"
                    ],
                    "key_features": [
                        "Real-time collaboration",
                        "Annotation tools",
                        "Export options",
                        "Version tracking"
                    ]
                }
            },
            "data_sources": {
                "financial_data": [
                    "Budget information",
                    "Actual expenditures",
                    "Revenue data",
                    "Department allocations"
                ],
                "grant_data": [
                    "FEMA grants",
                    "DOT funding",
                    "EPA programs",
                    "HUD opportunities",
                    "USDA programs",
                    "DOJ funding"
                ],
                "operational_data": [
                    "Performance metrics",
                    "Transaction records",
                    "Historical analysis",
                    "Forecasting data"
                ]
            },
            "visualization_types": [
                "Bar charts",
                "Line charts", 
                "Scatter plots",
                "Heatmaps",
                "Treemaps",
                "Waterfall charts",
                "Pie charts",
                "Box plots",
                "Violin plots",
                "Correlation matrices"
            ]
        }
    
    def _initialize_process_workflows(self) -> Dict[str, List[str]]:
        """Initialize step-by-step workflows for common processes"""
        return {
            "creating_budget_scenario": [
                "1. Navigate to Navi module",
                "2. Click on 'Scenario Planner' tab",
                "3. Select organization from dropdown",
                "4. Choose scenario type (Budget, Revenue, Mixed)",
                "5. Input scenario parameters",
                "6. Configure funding sources",
                "7. Run scenario analysis",
                "8. Review results and recommendations",
                "9. Export scenario report"
            ],
            "building_custom_visualization": [
                "1. Go to Navi module",
                "2. Select 'Custom Visualizations' tab",
                "3. Choose chart type from dropdown",
                "4. Select X-axis and Y-axis columns",
                "5. Configure color and styling options",
                "6. Click 'Generate Chart'",
                "7. Review chart preview",
                "8. Export as PNG, HTML, or CSV",
                "9. Save to dashboard if needed"
            ],
            "using_ai_assistant": [
                "1. Open Mantis module",
                "2. Start new conversation or continue existing",
                "3. Type your question in natural language",
                "4. Review AI response and recommendations",
                "5. Ask follow-up questions if needed",
                "6. Use quick action buttons for common tasks",
                "7. Export conversation or insights"
            ],
            "grant_research": [
                "1. Access Mantis AI Intelligence Hub",
                "2. Use Grant Intelligence feature",
                "3. Enter search criteria (agency, amount, category)",
                "4. Review matching opportunities",
                "5. Analyze eligibility requirements",
                "6. Get AI recommendations on best matches",
                "7. Export grant opportunities list"
            ],
            "data_analysis": [
                "1. Navigate to BI Sandbox in Navi",
                "2. Select data source and organization",
                "3. Use AI Analytics for natural language queries",
                "4. Apply filters and data exploration tools",
                "5. Create visualizations using chart builder",
                "6. Perform statistical analysis",
                "7. Generate insights and recommendations",
                "8. Export analysis results"
            ],
            "document_analysis": [
                "1. Go to Mantis module",
                "2. Upload PDF or document file",
                "3. Wait for AI processing",
                "4. Review extracted insights and summary",
                "5. Ask specific questions about content",
                "6. Get recommendations and action items",
                "7. Export analysis report"
            ],
            "using_position_history_audit": [
                "1. Navigate to Navi module",
                "2. Click on 'Position-Based Budgeting' tab",
                "3. Expand 'Position History' section",
                "4. Review the change history table showing last 50 modifications",
                "5. Check timestamp, user, position, field, old value, and new value columns",
                "6. Use this for accountability and tracking budget changes over time"
            ],
            "filtering_pbb_positions": [
                "1. Go to Navi module and open 'Position-Based Budgeting'",
                "2. Expand 'Advanced Filters' section",
                "3. Set salary range using minimum and maximum sliders",
                "4. Select departments from the multiselect dropdown",
                "5. Choose employment status (Filled, Vacant, or Frozen)",
                "6. Select funding sources (General Fund, Grant Funded, etc.)",
                "7. Choose benefit packages and data sources as needed",
                "8. Grid automatically updates with filtered results",
                "9. Click 'Clear All Filters' to reset and view all positions"
            ],
            "getting_ai_budget_analysis": [
                "1. Navigate to Navi > Position-Based Budgeting",
                "2. Expand 'AI Budget Assistant' section",
                "3. Select analysis type from dropdown:",
                "   - Anomaly Detection: Find unusual salary patterns",
                "   - Market Rate Comparison: Benchmark against market data",
                "   - Cost Savings Recommendations: Identify efficiency opportunities",
                "   - Grant Opportunities: Match positions to funding sources",
                "4. Click 'Analyze' button",
                "5. Review AI-generated insights including:",
                "   - Key findings about your budget data",
                "   - Budget recommendations for improvements",
                "   - Potential savings opportunities",
                "   - Risk areas to monitor",
                "6. Use insights for strategic budget planning"
            ],
            "exporting_pdf_budget_book": [
                "1. Navigate to Navi > Position-Based Budgeting",
                "2. Click 'PDF Budget Book' button in export section",
                "3. System generates comprehensive PDF with:",
                "   - Cover page showing fiscal year and generation date",
                "   - Executive summary with total positions and budget",
                "   - Department-by-department summaries",
                "   - Detailed position listings (up to 100 positions)",
                "   - Total budget calculations",
                "4. Click 'Download PDF Budget Book' button when ready",
                "5. Use PDF for board presentations, documentation, and reporting"
            ],
            "checking_union_compliance": [
                "1. Go to Navi > Position-Based Budgeting",
                "2. Expand 'Union Contract Compliance' section",
                "3. Configure compliance rules:",
                "   - Max Overtime Hours/Week (default: 10)",
                "   - Min Step Increase % (default: 3.0%)",
                "   - Max Annual Increase % (default: 5.0%)",
                "   - Min FTE for Benefits (default: 0.75)",
                "4. Click 'Check Compliance' button",
                "5. Review compliance results:",
                "   - If violations found: See detailed list with position names",
                "   - If compliant: Confirmation message displayed",
                "6. Address any violations before finalizing budget"
            ],
            "comparing_departments": [
                "1. Navigate to Navi > Position-Based Budgeting",
                "2. Expand 'Department Comparison' section",
                "3. Select first department from 'Department 1' dropdown",
                "4. Select second department from 'Department 2' dropdown",
                "5. Click 'Compare' button",
                "6. Review comparison metrics:",
                "   - Position count for each department",
                "   - Total budget for each department",
                "   - Differences showing variance",
                "   - Percentage change indicators",
                "7. Use comparison for budget allocation decisions"
            ],
            "using_quick_actions_pbb": [
                "1. Go to Navi > Position-Based Budgeting",
                "2. Click 'Quick Actions' button in the toolbar",
                "3. Choose from available bulk operations:",
                "   - Apply COLA: Enter percentage for cost-of-living adjustments",
                "   - Hiring Freeze: Freeze all vacant positions",
                "   - Merit Increase: Apply performance-based raises (e.g., 3%)",
                "   - Step Increase: Advance eligible employees to next step",
                "   - Bulk Overtime: Adjust overtime calculations",
                "4. Enter required parameters when prompted",
                "5. Confirm the bulk operation",
                "6. Review updated positions in the grid",
                "7. Save changes to persist the scenario",
                "8. Use for what-if analysis and scenario planning"
            ],
            "splitting_position_allocation": [
                "1. Navigate to Navi > Position-Based Budgeting",
                "2. Select exactly ONE position to split by clicking the checkbox",
                "3. Click 'Split Allocation' button in the toolbar",
                "4. Modal opens with two allocation rows (50%/50% default)",
                "5. For first allocation:",
                "   - Select Fund/GL Account from dropdown",
                "   - Enter percentage (e.g., 60)",
                "6. For second allocation:",
                "   - Select different Fund/GL Account",
                "   - Enter remaining percentage (e.g., 40)",
                "7. Add more allocations if needed using 'Add Allocation' button",
                "8. Ensure percentages total exactly 100%",
                "9. Click 'Save Split' button",
                "10. Original position is removed and TWO separate rows are created",
                "11. Each row shows its percentage in position name (e.g., 'Manager (60%)')",
                "12. Salary and benefits are proportionally allocated to each row"
            ]
        }
    
    def _initialize_common_issues(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common issues and their solutions"""
        return {
            "data_not_loading": {
                "symptoms": [
                    "Empty dashboard",
                    "No data available message",
                    "Charts not displaying"
                ],
                "causes": [
                    "Database connection issue",
                    "Incorrect organization selection",
                    "Data permissions"
                ],
                "solutions": [
                    "Check organization dropdown selection",
                    "Verify database connectivity",
                    "Contact administrator for data access",
                    "Try refreshing the page"
                ]
            },
            "visualization_errors": {
                "symptoms": [
                    "Chart not generating",
                    "Error creating visualization",
                    "Empty chart display"
                ],
                "causes": [
                    "Insufficient data",
                    "Incompatible column types",
                    "Missing required fields"
                ],
                "solutions": [
                    "Verify data contains required columns",
                    "Check data types (numeric vs categorical)",
                    "Try different chart type",
                    "Filter data to ensure sufficient records"
                ]
            },
            "slow_performance": {
                "symptoms": [
                    "Long loading times",
                    "Unresponsive interface",
                    "Timeout errors"
                ],
                "causes": [
                    "Large dataset",
                    "Complex calculations",
                    "Network connectivity"
                ],
                "solutions": [
                    "Apply data filters to reduce dataset size",
                    "Use sampling for large datasets",
                    "Check internet connection",
                    "Contact support for optimization"
                ]
            },
            "ai_assistant_issues": {
                "symptoms": [
                    "No AI response",
                    "Unclear answers",
                    "Error processing request"
                ],
                "causes": [
                    "API key issues",
                    "Unclear question",
                    "Service unavailable"
                ],
                "solutions": [
                    "Rephrase question more specifically",
                    "Check API key configuration",
                    "Try simpler queries first",
                    "Contact administrator if persistent"
                ]
            },
            "export_problems": {
                "symptoms": [
                    "Download not working",
                    "Corrupted files",
                    "Missing data in export"
                ],
                "causes": [
                    "Browser settings",
                    "File permissions",
                    "Large file size"
                ],
                "solutions": [
                    "Check browser download settings",
                    "Try different export format",
                    "Filter data before export",
                    "Use smaller date ranges"
                ]
            },
            "pbb_filters_not_working": {
                "symptoms": [
                    "Advanced filters not reducing data",
                    "Grid shows all positions despite filter settings",
                    "Filter selections not applying"
                ],
                "causes": [
                    "Filter criteria not set correctly",
                    "Data source mismatch",
                    "Browser cache issue"
                ],
                "solutions": [
                    "Verify filter criteria are selected (not just opened)",
                    "Try 'Clear All Filters' then reapply",
                    "Refresh the page and try again",
                    "Check that salary range sliders are moved from defaults"
                ]
            },
            "ai_budget_assistant_no_results": {
                "symptoms": [
                    "'No data to analyze' message",
                    "AI analysis returns empty results",
                    "Analysis button does nothing"
                ],
                "causes": [
                    "No positions in active sheet",
                    "Sheet not selected",
                    "Insufficient data for analysis"
                ],
                "solutions": [
                    "Ensure you have positions loaded in your active sheet",
                    "Select a sheet with data from the sheet tabs",
                    "Try loading positions from payroll database first",
                    "Check that at least one position exists before analyzing"
                ]
            },
            "pdf_budget_book_generation_failed": {
                "symptoms": [
                    "PDF export not generating",
                    "Error during PDF creation",
                    "Download button not appearing"
                ],
                "causes": [
                    "Too many positions (>1000)",
                    "Missing fpdf2 library",
                    "Invalid position data"
                ],
                "solutions": [
                    "Filter positions to reduce dataset before export",
                    "Contact administrator to install fpdf2 library",
                    "Verify all positions have valid department and salary data",
                    "Try exporting by department using filters"
                ]
            },
            "union_compliance_false_positives": {
                "symptoms": [
                    "Compliance violations showing incorrectly",
                    "All positions flagged as non-compliant",
                    "Unexpected violation messages"
                ],
                "causes": [
                    "Incorrect compliance rule thresholds",
                    "Missing benefit rate data",
                    "Data type mismatches"
                ],
                "solutions": [
                    "Verify compliance rule values match your union contract",
                    "Check that benefit rates are populated (not zero)",
                    "Ensure FTE values are decimals (0.75) not percentages (75)",
                    "Review flagged positions and update missing data"
                ]
            },
            "department_comparison_no_data": {
                "symptoms": [
                    "Department comparison shows zero metrics",
                    "No positions found for department",
                    "Comparison returns empty results"
                ],
                "causes": [
                    "Department names don't match position data",
                    "No positions assigned to selected departments",
                    "Case sensitivity in department names"
                ],
                "solutions": [
                    "Verify department names exactly match position assignments",
                    "Check that selected departments have positions loaded",
                    "Review position data to confirm department field is populated",
                    "Use department names from the dropdown (don't type manually)"
                ]
            },
            "quick_actions_not_applying": {
                "symptoms": [
                    "COLA or merit increase not updating salaries",
                    "Positions unchanged after quick action",
                    "Bulk operation appears to run but no changes"
                ],
                "causes": [
                    "Changes not saved to database",
                    "Incorrect position selection",
                    "Calculation errors"
                ],
                "solutions": [
                    "Click 'Save Sheet' button after applying quick actions",
                    "Verify percentage values are entered correctly (3.5 not 0.035)",
                    "Check that positions are not frozen or locked",
                    "Refresh page and reapply if needed",
                    "Review position history to verify changes were applied"
                ]
            },
            "position_history_empty": {
                "symptoms": [
                    "No change history available",
                    "Position history shows empty table",
                    "Recent changes not appearing"
                ],
                "causes": [
                    "No changes made yet",
                    "Audit logging not enabled",
                    "Database connection issue"
                ],
                "solutions": [
                    "Make a test change to a position to generate history",
                    "Verify you're viewing the correct sheet",
                    "Check database connectivity",
                    "History only shows last 50 changes - older changes are archived"
                ]
            },
            "split_allocation_not_working": {
                "symptoms": [
                    "Split allocation button does nothing",
                    "Modal won't open for split allocation",
                    "Can't select position to split"
                ],
                "causes": [
                    "Multiple positions selected (need exactly 1)",
                    "No position selected",
                    "JavaScript error in browser"
                ],
                "solutions": [
                    "Select EXACTLY ONE position using the checkbox",
                    "Deselect all, then select only the position to split",
                    "Refresh the page and try again",
                    "Check browser console for errors (F12)"
                ]
            },
            "split_allocation_percentages_wrong": {
                "symptoms": [
                    "Error: 'Percentages must total 100%'",
                    "Can't save split allocation",
                    "Split validation failing"
                ],
                "causes": [
                    "Allocation percentages don't add to 100",
                    "Empty percentage fields",
                    "Decimal rounding issues"
                ],
                "solutions": [
                    "Verify all percentages add exactly to 100 (e.g., 60 + 40 = 100)",
                    "Fill in all percentage fields (don't leave any blank)",
                    "For 3-way split, try 33.34 + 33.33 + 33.33 = 100",
                    "Use whole numbers when possible to avoid rounding errors"
                ]
            },
            "split_allocation_rows_not_created": {
                "symptoms": [
                    "Original position removed but no new rows",
                    "Split allocation saved but grid unchanged",
                    "Missing split position rows"
                ],
                "causes": [
                    "No fund/GL account selected",
                    "Grid transaction failed",
                    "Data not synced to backend"
                ],
                "solutions": [
                    "Ensure BOTH fund/GL accounts are selected (not blank)",
                    "Click 'Save Sheet' after split to persist changes",
                    "Refresh page to reload from database",
                    "Check that you have at least 2 allocation entries filled"
                ]
            }
        }

class MantisMLTrainer:
    """Machine learning trainer for Mantis support capabilities"""
    
    def __init__(self, knowledge_base: MantisKnowledgeBase):
        self.kb = knowledge_base
        self.training_data = self._generate_training_data()
        self.intent_classifier = None
        self.response_generator = None
        
    def _generate_training_data(self) -> List[Dict[str, Any]]:
        """Generate training data from knowledge base"""
        training_data = []
        
        # Generate FAQ-style training data
        faqs = [
            {
                "question": "How do I create a budget scenario?",
                "intent": "process_help",
                "workflow": "creating_budget_scenario",
                "module": "navi"
            },
            {
                "question": "How to build custom charts?",
                "intent": "process_help", 
                "workflow": "building_custom_visualization",
                "module": "navi"
            },
            {
                "question": "How does the AI assistant work?",
                "intent": "feature_explanation",
                "workflow": "using_ai_assistant",
                "module": "mantis"
            },
            {
                "question": "Where can I find grant opportunities?",
                "intent": "process_help",
                "workflow": "grant_research",
                "module": "mantis"
            },
            {
                "question": "My data is not loading, what should I do?",
                "intent": "troubleshooting",
                "issue": "data_not_loading"
            },
            {
                "question": "Charts are not displaying properly",
                "intent": "troubleshooting",
                "issue": "visualization_errors"
            },
            {
                "question": "The application is running slowly",
                "intent": "troubleshooting",
                "issue": "slow_performance"
            },
            {
                "question": "What modules are available in GovSight?",
                "intent": "feature_explanation",
                "type": "modules_overview"
            },
            {
                "question": "What types of charts can I create?",
                "intent": "feature_explanation",
                "type": "visualization_types"
            },
            {
                "question": "How do I export my analysis?",
                "intent": "process_help",
                "type": "export_help"
            },
            {
                "question": "How do I view position change history?",
                "intent": "process_help",
                "workflow": "using_position_history_audit",
                "module": "navi"
            },
            {
                "question": "How to filter positions in PBB?",
                "intent": "process_help",
                "workflow": "filtering_pbb_positions",
                "module": "navi"
            },
            {
                "question": "How do I get AI budget analysis?",
                "intent": "process_help",
                "workflow": "getting_ai_budget_analysis",
                "module": "navi"
            },
            {
                "question": "How to export PDF budget book?",
                "intent": "process_help",
                "workflow": "exporting_pdf_budget_book",
                "module": "navi"
            },
            {
                "question": "How do I check union compliance?",
                "intent": "process_help",
                "workflow": "checking_union_compliance",
                "module": "navi"
            },
            {
                "question": "How to compare departments?",
                "intent": "process_help",
                "workflow": "comparing_departments",
                "module": "navi"
            },
            {
                "question": "How do I use Quick Actions in PBB?",
                "intent": "process_help",
                "workflow": "using_quick_actions_pbb",
                "module": "navi"
            },
            {
                "question": "Advanced filters not working in PBB",
                "intent": "troubleshooting",
                "issue": "pbb_filters_not_working"
            },
            {
                "question": "AI Budget Assistant shows no data",
                "intent": "troubleshooting",
                "issue": "ai_budget_assistant_no_results"
            },
            {
                "question": "PDF budget book won't generate",
                "intent": "troubleshooting",
                "issue": "pdf_budget_book_generation_failed"
            },
            {
                "question": "Union compliance checker showing wrong violations",
                "intent": "troubleshooting",
                "issue": "union_compliance_false_positives"
            },
            {
                "question": "Department comparison not showing data",
                "intent": "troubleshooting",
                "issue": "department_comparison_no_data"
            },
            {
                "question": "Quick Actions not updating positions",
                "intent": "troubleshooting",
                "issue": "quick_actions_not_applying"
            },
            {
                "question": "Position history is empty",
                "intent": "troubleshooting",
                "issue": "position_history_empty"
            },
            {
                "question": "How do I split a position across cost centers?",
                "intent": "process_help",
                "workflow": "splitting_position_allocation",
                "module": "navi"
            },
            {
                "question": "Split allocation button not working",
                "intent": "troubleshooting",
                "issue": "split_allocation_not_working"
            },
            {
                "question": "Percentages don't add up to 100 in split allocation",
                "intent": "troubleshooting",
                "issue": "split_allocation_percentages_wrong"
            },
            {
                "question": "Split rows not being created",
                "intent": "troubleshooting",
                "issue": "split_allocation_rows_not_created"
            }
        ]
        
        # Expand training data with variations
        for faq in faqs:
            training_data.append(faq)
            
            # Generate variations of questions
            variations = self._generate_question_variations(faq["question"])
            for variation in variations:
                variation_data = faq.copy()
                variation_data["question"] = variation
                training_data.append(variation_data)
        
        return training_data
    
    def _generate_question_variations(self, question: str) -> List[str]:
        """Generate variations of questions for training"""
        variations = []
        
        # Simple variations based on common question patterns
        if "how do i" in question.lower():
            variations.append(question.replace("How do I", "How can I"))
            variations.append(question.replace("How do I", "What's the process to"))
        
        if "how to" in question.lower():
            variations.append(question.replace("How to", "How do I"))
            variations.append(question.replace("How to", "Steps to"))
        
        if "what" in question.lower():
            variations.append(question.replace("What", "Which"))
            variations.append(question.replace("What", "Can you tell me about"))
        
        return variations
    
    def train_intent_classifier(self) -> MultinomialNB:
        """Train intent classification model"""
        questions = [item["question"] for item in self.training_data]
        intents = [item["intent"] for item in self.training_data]
        
        # Vectorize questions
        question_vectors = self.kb.vectorizer.fit_transform(questions)
        
        # Train classifier
        self.intent_classifier = MultinomialNB()
        self.intent_classifier.fit(question_vectors, intents)
        
        return self.intent_classifier
    
    def train_similarity_model(self):
        """Train similarity-based response model"""
        questions = [item["question"] for item in self.training_data]
        self.kb.knowledge_vectors = self.kb.vectorizer.fit_transform(questions)
    
    def predict_intent_and_response(self, user_question: str) -> Dict[str, Any]:
        """Predict intent and generate appropriate response"""
        if not self.intent_classifier:
            self.train_intent_classifier()
            
        if self.kb.knowledge_vectors is None:
            self.train_similarity_model()
        
        # Vectorize user question
        question_vector = self.kb.vectorizer.transform([user_question])
        
        # Predict intent
        predicted_intent = self.intent_classifier.predict(question_vector)[0]
        intent_confidence = max(self.intent_classifier.predict_proba(question_vector)[0])
        
        # Find most similar question
        similarities = cosine_similarity(question_vector, self.kb.knowledge_vectors).flatten()
        most_similar_idx = similarities.argmax()
        similarity_score = similarities[most_similar_idx]
        
        # Get matching training data
        similar_item = self.training_data[most_similar_idx]
        
        # Generate response
        response = self._generate_response(predicted_intent, similar_item, similarity_score)
        
        return {
            "intent": predicted_intent,
            "confidence": float(intent_confidence),
            "similarity_score": float(similarity_score),
            "response": response,
            "similar_question": similar_item["question"]
        }
    
    def _generate_response(self, intent: str, similar_item: Dict[str, Any], similarity_score: float) -> Dict[str, Any]:
        """Generate structured response based on intent and matching item"""
        
        if intent == "process_help" and "workflow" in similar_item:
            workflow_name = similar_item["workflow"]
            steps = self.kb.process_workflows.get(workflow_name, [])
            
            return {
                "type": "workflow",
                "title": f"How to: {workflow_name.replace('_', ' ').title()}",
                "steps": steps,
                "module": similar_item.get("module", ""),
                "confidence": similarity_score
            }
        
        elif intent == "troubleshooting" and "issue" in similar_item:
            issue_name = similar_item["issue"]
            issue_info = self.kb.common_issues.get(issue_name, {})
            
            return {
                "type": "troubleshooting",
                "title": f"Troubleshooting: {issue_name.replace('_', ' ').title()}",
                "symptoms": issue_info.get("symptoms", []),
                "causes": issue_info.get("causes", []),
                "solutions": issue_info.get("solutions", []),
                "confidence": similarity_score
            }
        
        elif intent == "feature_explanation":
            if similar_item.get("type") == "modules_overview":
                return {
                    "type": "feature_explanation",
                    "title": "GovSight Modules Overview",
                    "modules": self.kb.software_knowledge["modules"],
                    "confidence": similarity_score
                }
            elif similar_item.get("type") == "visualization_types":
                return {
                    "type": "feature_explanation", 
                    "title": "Available Visualization Types",
                    "charts": self.kb.software_knowledge["visualization_types"],
                    "confidence": similarity_score
                }
        
        # Default response for low confidence
        return {
            "type": "general",
            "title": "I can help you with:",
            "suggestions": [
                "Creating budget scenarios",
                "Building custom visualizations", 
                "Using the AI assistant",
                "Finding grant opportunities",
                "Troubleshooting common issues",
                "Understanding software features"
            ],
            "confidence": similarity_score
        }

def render_support_training_interface():
    """Render the support training interface for Mantis"""
    
    st.markdown("## Mantis Support Training")
    st.markdown("Train Mantis to act as an intelligent support tool for GovSight")
    
    # Initialize knowledge base and trainer
    if 'mantis_kb' not in st.session_state:
        st.session_state.mantis_kb = MantisKnowledgeBase()
        st.session_state.mantis_trainer = MantisMLTrainer(st.session_state.mantis_kb)
    
    kb = st.session_state.mantis_kb
    trainer = st.session_state.mantis_trainer
    
    # Training status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Train Intent Classifier"):
            with st.spinner("Training intent classification model..."):
                classifier = trainer.train_intent_classifier()
                st.success(f"Trained on {len(trainer.training_data)} examples")
    
    with col2:
        if st.button("Train Similarity Model"):
            with st.spinner("Training similarity model..."):
                trainer.train_similarity_model()
                st.success("Similarity model trained successfully")
    
    with col3:
        training_size = len(trainer.training_data)
        st.metric("Training Examples", training_size)
    
    # Test the trained model
    st.markdown("### Test Support Capabilities")
    
    user_question = st.text_input(
        "Ask a support question:",
        placeholder="e.g., How do I create a budget scenario?"
    )
    
    if user_question and st.button("Get Support Response"):
        with st.spinner("Analyzing question and generating response..."):
            try:
                result = trainer.predict_intent_and_response(user_question)
                
                # Display results
                st.markdown(f"**Intent Detected:** {result['intent']}")
                st.markdown(f"**Confidence:** {result['confidence']:.2%}")
                st.markdown(f"**Similarity Score:** {result['similarity_score']:.2%}")
                
                response = result['response']
                
                if response['type'] == 'workflow':
                    st.markdown(f"### {response['title']}")
                    st.markdown(f"**Module:** {response['module'].title()}")
                    st.markdown("**Steps:**")
                    for step in response['steps']:
                        st.markdown(f"- {step}")
                
                elif response['type'] == 'troubleshooting':
                    st.markdown(f"### {response['title']}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**Symptoms:**")
                        for symptom in response['symptoms']:
                            st.markdown(f"- {symptom}")
                    
                    with col2:
                        st.markdown("**Possible Causes:**")
                        for cause in response['causes']:
                            st.markdown(f"- {cause}")
                    
                    with col3:
                        st.markdown("**Solutions:**")
                        for solution in response['solutions']:
                            st.markdown(f"- {solution}")
                
                elif response['type'] == 'feature_explanation':
                    st.markdown(f"### {response['title']}")
                    
                    if 'modules' in response:
                        for module_key, module_info in response['modules'].items():
                            with st.expander(f"{module_info['name']} ({module_key.upper()})"):
                                st.markdown("**Functions:**")
                                for func in module_info['functions']:
                                    st.markdown(f"- {func}")
                                
                                st.markdown("**Use Cases:**")
                                for use_case in module_info['use_cases']:
                                    st.markdown(f"- {use_case}")
                    
                    elif 'charts' in response:
                        chart_cols = st.columns(3)
                        for i, chart in enumerate(response['charts']):
                            with chart_cols[i % 3]:
                                st.markdown(f"- {chart}")
                
                else:  # general response
                    st.markdown(f"### {response['title']}")
                    for suggestion in response['suggestions']:
                        st.markdown(f"- {suggestion}")
                
            except Exception as e:
                st.error(f"Error generating response: {e}")
    
    # Knowledge base overview
    with st.expander("Knowledge Base Overview"):
        st.markdown("### Current Knowledge Base")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Modules Covered:**")
            for module, info in kb.software_knowledge['modules'].items():
                st.markdown(f"- {info['name']} ({module.upper()})")
        
        with col2:
            st.markdown("**Process Workflows:**")
            for workflow in kb.process_workflows.keys():
                st.markdown(f"- {workflow.replace('_', ' ').title()}")
        
        st.markdown("**Common Issues Covered:**")
        issue_cols = st.columns(2)
        for i, issue in enumerate(kb.common_issues.keys()):
            with issue_cols[i % 2]:
                st.markdown(f"- {issue.replace('_', ' ').title()}")
    
    # Training data management
    with st.expander("Training Data Management"):
        st.markdown("### Add Custom Training Data")
        
        new_question = st.text_input("New Question:")
        intent_type = st.selectbox("Intent Type:", ["process_help", "troubleshooting", "feature_explanation"])
        
        if st.button("Add Training Example"):
            if new_question:
                new_example = {
                    "question": new_question,
                    "intent": intent_type,
                    "custom": True,
                    "date_added": datetime.now().isoformat()
                }
                trainer.training_data.append(new_example)
                st.success("Training example added successfully!")
        
        # Export training data
        if st.button("Export Training Data"):
            training_df = pd.DataFrame(trainer.training_data)
            csv = training_df.to_csv(index=False)
            st.download_button(
                label="Download Training Data CSV",
                data=csv,
                file_name=f"mantis_training_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )