"""
Enhanced Natural Language Analytics for GovSight
Advanced conversational AI with municipal finance domain expertise
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import re
import json
import sqlite3
import numpy as np

from modules.ai_engine.secure_ai_base import SecureAIBase, GOVSIGHT_AI_SECURITY

class EnhancedNaturalLanguage(SecureAIBase):
    """
    Advanced conversational AI for municipal financial analysis
    
    CAPABILITIES:
    - Natural language query processing for financial data
    - Intelligent chart and visualization generation
    - Conversational financial analytics
    - Municipal finance domain expertise
    - Multi-turn conversation context management
    - Voice-enabled query processing
    - Automated narrative report generation
    """
    
    def __init__(self):
        super().__init__("EnhancedNaturalLanguage", GOVSIGHT_AI_SECURITY)
        
        # Municipal finance domain knowledge
        self.municipal_domain_knowledge = {
            'financial_terms': {
                'revenue': ['income', 'receipts', 'earnings', 'collections', 'taxes'],
                'expenditure': ['spending', 'expenses', 'costs', 'outlay', 'disbursements'],
                'budget': ['allocation', 'appropriation', 'plan', 'forecast'],
                'variance': ['difference', 'deviation', 'gap', 'shortfall', 'surplus'],
                'department': ['division', 'unit', 'bureau', 'office', 'service'],
                'vendor': ['supplier', 'contractor', 'provider', 'company'],
                'fund': ['account', 'pool', 'reserve', 'source']
            },
            'common_questions': {
                'spending_patterns': [
                    'how much did we spend', 'what are our expenses', 'spending by department',
                    'largest expenses', 'cost analysis', 'expenditure breakdown'
                ],
                'budget_analysis': [
                    'budget vs actual', 'over budget', 'under budget', 'variance analysis',
                    'budget performance', 'allocation utilization'
                ],
                'vendor_analysis': [
                    'top vendors', 'vendor spending', 'supplier costs', 'contractor payments',
                    'vendor performance', 'procurement analysis'
                ],
                'trend_analysis': [
                    'spending trends', 'monthly trends', 'year over year', 'seasonal patterns',
                    'growth analysis', 'comparative analysis'
                ],
                'compliance': [
                    'audit trail', 'compliance check', 'regulatory requirements',
                    'approval workflow', 'authorization limits'
                ]
            },
            'chart_types': {
                'comparison': ['bar chart', 'column chart', 'horizontal bar'],
                'trends': ['line chart', 'area chart', 'time series'],
                'composition': ['pie chart', 'donut chart', 'stacked bar'],
                'distribution': ['histogram', 'box plot', 'scatter plot'],
                'geographic': ['map', 'choropleth', 'geographic distribution']
            },
            'time_periods': {
                'current': ['this month', 'current month', 'mtd', 'month to date'],
                'previous': ['last month', 'previous month', 'prior month'],
                'quarterly': ['this quarter', 'q1', 'q2', 'q3', 'q4', 'quarterly'],
                'annual': ['this year', 'ytd', 'year to date', 'annual', 'yearly'],
                'comparative': ['year over year', 'yoy', 'vs last year', 'compared to']
            }
        }
        
        # Initialize conversation context database
        self._initialize_context_db()
    
    def _initialize_context_db(self):
        """Initialize conversation context tracking database"""
        try:
            conn = sqlite3.connect('nl_conversation_context.db')
            cursor = conn.cursor()
            
            # Conversation context table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_context (
                    session_id TEXT,
                    turn_number INTEGER,
                    user_query TEXT,
                    parsed_intent TEXT,
                    extracted_entities TEXT,
                    generated_response TEXT,
                    chart_generated BOOLEAN,
                    data_sources TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, turn_number)
                )
            ''')
            
            # Entity resolution table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entity_resolution (
                    entity_type TEXT,
                    user_term TEXT,
                    canonical_term TEXT,
                    confidence REAL,
                    context TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Failed to initialize NL context database: {e}")
    
    def process_natural_language_query(self, user_query: str, 
                                     available_data: Dict[str, pd.DataFrame] = None,
                                     conversation_context: List[Dict] = None) -> Dict[str, Any]:
        """
        Process natural language query and generate intelligent response
        
        Args:
            user_query: Natural language query from user
            available_data: Dict of available dataframes
            conversation_context: Previous conversation history
            
        Returns:
            Comprehensive response with analysis, visualizations, and insights
        """
        if not user_query.strip():
            return {'error': 'Empty query provided'}
        
        # Parse user intent and extract entities
        query_analysis = self._analyze_user_query(user_query, conversation_context or [])
        
        response = {
            'user_query': user_query,
            'timestamp': datetime.now().isoformat(),
            'query_analysis': query_analysis,
            'response_components': []
        }
        
        # Generate data analysis based on intent
        if query_analysis['intent'] and available_data:
            data_analysis = self._generate_data_analysis(
                query_analysis, available_data, conversation_context
            )
            response['data_analysis'] = data_analysis
            
            # Generate visualizations if appropriate
            if query_analysis['requires_visualization']:
                visualizations = self._generate_visualizations(
                    query_analysis, data_analysis, available_data
                )
                response['visualizations'] = visualizations
            
            # Generate narrative insights
            narrative = self._generate_narrative_insights(
                query_analysis, data_analysis, user_query
            )
            response['narrative'] = narrative
        else:
            # Handle general questions or provide guidance
            guidance = self._generate_guidance_response(user_query, query_analysis)
            response['guidance'] = guidance
        
        # Save conversation context
        self._save_conversation_context(user_query, query_analysis, response)
        
        return response
    
    def _analyze_user_query(self, user_query: str, 
                          conversation_context: List[Dict]) -> Dict[str, Any]:
        """Analyze user query to understand intent and extract entities"""
        
        analysis_prompt = f"""
        Analyze this natural language query about municipal finances:
        
        USER QUERY: "{user_query}"
        
        CONVERSATION CONTEXT: {json.dumps(conversation_context[-3:] if conversation_context else [], indent=2)}
        
        Analyze and extract:
        
        1. PRIMARY INTENT (choose one):
           - data_query: User wants specific data or metrics
           - comparison: User wants to compare different items/periods
           - trend_analysis: User wants to see trends over time
           - budget_analysis: User wants budget vs actual analysis
           - vendor_analysis: User wants vendor/supplier information
           - department_analysis: User wants department-specific analysis
           - compliance_check: User wants audit/compliance information
           - general_question: General question about finances
           - help_request: User needs guidance or help
        
        2. ENTITIES (extract all that apply):
           - time_period: specific dates, months, quarters, years
           - departments: specific departments mentioned
           - vendors: specific vendors or suppliers
           - account_codes: specific account codes or categories
           - amounts: specific dollar amounts or ranges
           - comparison_items: what should be compared
        
        3. DATA REQUIREMENTS:
           - required_data_sources: what data sources are needed
           - required_calculations: what calculations are needed
           - aggregation_level: department, monthly, vendor, etc.
        
        4. VISUALIZATION NEEDS:
           - requires_visualization: true/false
           - suggested_chart_type: bar, line, pie, table, etc.
           - chart_purpose: comparison, trend, composition, etc.
        
        5. CONTEXTUAL INFORMATION:
           - follows_up_previous: does this reference previous conversation
           - ambiguity_level: high/medium/low
           - complexity: simple/medium/complex
        
        Respond in JSON format with these exact field names.
        """
        
        ai_response = self.secure_ai_request(
            analysis_prompt,
            "natural_language_query_analysis",
            data_sources=["user_query", "conversation_context"],
            max_tokens=1500
        )
        
        if ai_response.get('success'):
            try:
                # Parse AI response as JSON
                analysis_text = ai_response.get('response', '{}')
                # Extract JSON from response if wrapped in text
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = json.loads(analysis_text)
                
                # Validate and set defaults
                analysis.setdefault('intent', 'general_question')
                analysis.setdefault('entities', {})
                analysis.setdefault('requires_visualization', False)
                analysis.setdefault('complexity', 'medium')
                
                return analysis
                
            except json.JSONDecodeError as e:
                # Fallback to rule-based analysis
                return self._rule_based_query_analysis(user_query)
        else:
            # Fallback to rule-based analysis
            return self._rule_based_query_analysis(user_query)
    
    def _rule_based_query_analysis(self, user_query: str) -> Dict[str, Any]:
        """Fallback rule-based query analysis"""
        query_lower = user_query.lower()
        
        analysis = {
            'intent': 'general_question',
            'entities': {},
            'requires_visualization': False,
            'complexity': 'medium',
            'method': 'rule_based_fallback'
        }
        
        # Intent detection
        if any(term in query_lower for term in ['spend', 'expense', 'cost', 'payment']):
            analysis['intent'] = 'data_query'
            analysis['requires_visualization'] = True
        elif any(term in query_lower for term in ['compare', 'vs', 'versus', 'difference']):
            analysis['intent'] = 'comparison'
            analysis['requires_visualization'] = True
        elif any(term in query_lower for term in ['trend', 'over time', 'monthly', 'growth']):
            analysis['intent'] = 'trend_analysis'
            analysis['requires_visualization'] = True
        elif any(term in query_lower for term in ['budget', 'actual', 'variance']):
            analysis['intent'] = 'budget_analysis'
            analysis['requires_visualization'] = True
        elif any(term in query_lower for term in ['vendor', 'supplier', 'contractor']):
            analysis['intent'] = 'vendor_analysis'
            analysis['requires_visualization'] = True
        elif any(term in query_lower for term in ['department', 'division']):
            analysis['intent'] = 'department_analysis'
            analysis['requires_visualization'] = True
        
        # Entity extraction
        entities = {}
        
        # Time periods
        time_terms = ['january', 'february', 'march', 'april', 'may', 'june',
                     'july', 'august', 'september', 'october', 'november', 'december',
                     'q1', 'q2', 'q3', 'q4', 'quarter', 'month', 'year', '2024', '2023']
        
        found_time_terms = [term for term in time_terms if term in query_lower]
        if found_time_terms:
            entities['time_period'] = found_time_terms
        
        # Department detection
        dept_terms = ['police', 'fire', 'public works', 'parks', 'administration', 'finance']
        found_dept_terms = [term for term in dept_terms if term in query_lower]
        if found_dept_terms:
            entities['departments'] = found_dept_terms
        
        analysis['entities'] = entities
        
        return analysis
    
    def _generate_data_analysis(self, query_analysis: Dict[str, Any],
                              available_data: Dict[str, pd.DataFrame],
                              conversation_context: List[Dict]) -> Dict[str, Any]:
        """Generate data analysis based on query analysis"""
        
        data_analysis = {
            'analysis_type': query_analysis['intent'],
            'data_used': [],
            'results': {},
            'summary_stats': {}
        }
        
        # Select appropriate dataset
        primary_data = None
        data_source_name = None
        
        # Priority order for data selection
        data_priorities = ['transactions', 'budget', 'gl_data', 'department_data']
        for priority in data_priorities:
            if priority in available_data and not available_data[priority].empty:
                primary_data = available_data[priority]
                data_source_name = priority
                break
        
        if primary_data is None or primary_data.empty:
            return {'error': 'No suitable data available for analysis'}
        
        data_analysis['data_used'] = [data_source_name]
        
        # Perform analysis based on intent
        if query_analysis['intent'] == 'data_query':
            results = self._perform_data_query_analysis(primary_data, query_analysis)
        elif query_analysis['intent'] == 'comparison':
            results = self._perform_comparison_analysis(primary_data, query_analysis)
        elif query_analysis['intent'] == 'trend_analysis':
            results = self._perform_trend_analysis(primary_data, query_analysis)
        elif query_analysis['intent'] == 'budget_analysis':
            results = self._perform_budget_analysis(primary_data, query_analysis)
        elif query_analysis['intent'] == 'vendor_analysis':
            results = self._perform_vendor_analysis(primary_data, query_analysis)
        elif query_analysis['intent'] == 'department_analysis':
            results = self._perform_department_analysis(primary_data, query_analysis)
        else:
            results = self._perform_general_analysis(primary_data, query_analysis)
        
        data_analysis['results'] = results
        
        # Generate summary statistics
        data_analysis['summary_stats'] = self._generate_summary_statistics(primary_data, results)
        
        return data_analysis
    
    def _perform_data_query_analysis(self, data: pd.DataFrame, 
                                   query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform general data query analysis"""
        results = {}
        
        # Handle amount-based queries
        if 'Amount' in data.columns:
            results['total_amount'] = float(data['Amount'].sum())
            results['transaction_count'] = len(data)
            results['average_amount'] = float(data['Amount'].mean())
            results['largest_transaction'] = float(data['Amount'].max())
            
            # Department breakdown if available
            if 'Department' in data.columns:
                dept_summary = data.groupby('Department')['Amount'].agg(['sum', 'count']).round(2)
                results['by_department'] = dept_summary.to_dict('index')
            
            # Monthly breakdown if date available
            if 'Date' in data.columns:
                data_copy = data.copy()
                data_copy['Date'] = pd.to_datetime(data_copy['Date'])
                data_copy['Month'] = data_copy['Date'].dt.to_period('M')
                monthly_summary = data_copy.groupby('Month')['Amount'].sum().round(2)
                results['by_month'] = monthly_summary.to_dict()
        
        return results
    
    def _perform_comparison_analysis(self, data: pd.DataFrame, 
                                   query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comparison analysis"""
        results = {}
        
        entities = query_analysis.get('entities', {})
        
        # Department comparison
        if 'Department' in data.columns and 'Amount' in data.columns:
            dept_comparison = data.groupby('Department').agg({
                'Amount': ['sum', 'mean', 'count']
            }).round(2)
            dept_comparison.columns = ['Total_Amount', 'Avg_Amount', 'Transaction_Count']
            results['department_comparison'] = dept_comparison.to_dict('index')
        
        # Time period comparison
        if 'Date' in data.columns and 'Amount' in data.columns:
            data_copy = data.copy()
            data_copy['Date'] = pd.to_datetime(data_copy['Date'])
            data_copy['Month'] = data_copy['Date'].dt.to_period('M')
            
            monthly_comparison = data_copy.groupby('Month')['Amount'].sum().round(2)
            if len(monthly_comparison) >= 2:
                latest_month = monthly_comparison.index[-1]
                previous_month = monthly_comparison.index[-2]
                
                results['time_comparison'] = {
                    'current_period': {
                        'period': str(latest_month),
                        'amount': float(monthly_comparison.iloc[-1])
                    },
                    'previous_period': {
                        'period': str(previous_month),
                        'amount': float(monthly_comparison.iloc[-2])
                    },
                    'variance': float(monthly_comparison.iloc[-1] - monthly_comparison.iloc[-2]),
                    'percent_change': float(((monthly_comparison.iloc[-1] - monthly_comparison.iloc[-2]) / monthly_comparison.iloc[-2]) * 100)
                }
        
        return results
    
    def _perform_trend_analysis(self, data: pd.DataFrame, 
                              query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform trend analysis"""
        results = {}
        
        if 'Date' in data.columns and 'Amount' in data.columns:
            data_copy = data.copy()
            data_copy['Date'] = pd.to_datetime(data_copy['Date'])
            data_copy = data_copy.sort_values('Date')
            
            # Monthly trends
            data_copy['YearMonth'] = data_copy['Date'].dt.to_period('M')
            monthly_trends = data_copy.groupby('YearMonth')['Amount'].sum()
            
            results['monthly_trend'] = {
                'periods': [str(period) for period in monthly_trends.index],
                'amounts': [float(amount) for amount in monthly_trends.values],
                'trend_direction': 'increasing' if monthly_trends.iloc[-1] > monthly_trends.iloc[0] else 'decreasing',
                'total_change': float(monthly_trends.iloc[-1] - monthly_trends.iloc[0]),
                'percent_change': float(((monthly_trends.iloc[-1] - monthly_trends.iloc[0]) / monthly_trends.iloc[0]) * 100) if monthly_trends.iloc[0] != 0 else 0
            }
            
            # Calculate trend statistics
            if len(monthly_trends) > 1:
                # Simple linear trend
                x = np.arange(len(monthly_trends))
                y = monthly_trends.values
                trend_slope = np.polyfit(x, y, 1)[0]
                
                results['trend_statistics'] = {
                    'slope': float(trend_slope),
                    'average_monthly_change': float(trend_slope),
                    'volatility': float(np.std(y)),
                    'data_points': len(monthly_trends)
                }
        
        return results
    
    def _perform_budget_analysis(self, data: pd.DataFrame, 
                               query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform budget vs actual analysis"""
        results = {}
        
        if 'Budget' in data.columns and 'Actual' in data.columns:
            # Calculate variances
            data_copy = data.copy()
            data_copy['Variance'] = data_copy['Actual'] - data_copy['Budget']
            data_copy['Variance_Percent'] = (data_copy['Variance'] / data_copy['Budget']) * 100
            
            results['budget_summary'] = {
                'total_budget': float(data_copy['Budget'].sum()),
                'total_actual': float(data_copy['Actual'].sum()),
                'total_variance': float(data_copy['Variance'].sum()),
                'variance_percent': float((data_copy['Variance'].sum() / data_copy['Budget'].sum()) * 100),
                'over_budget_count': int((data_copy['Variance'] > 0).sum()),
                'under_budget_count': int((data_copy['Variance'] < 0).sum())
            }
            
            # Department-level budget analysis
            if 'Department' in data_copy.columns:
                dept_budget = data_copy.groupby('Department').agg({
                    'Budget': 'sum',
                    'Actual': 'sum',
                    'Variance': 'sum',
                    'Variance_Percent': 'mean'
                }).round(2)
                
                results['department_budget_analysis'] = dept_budget.to_dict('index')
            
            # Identify significant variances (>20% or >$10,000)
            significant_variances = data_copy[
                (abs(data_copy['Variance_Percent']) > 20) | 
                (abs(data_copy['Variance']) > 10000)
            ]
            
            if len(significant_variances) > 0:
                results['significant_variances'] = {
                    'count': len(significant_variances),
                    'items': significant_variances[['Budget', 'Actual', 'Variance', 'Variance_Percent']].to_dict('records')[:10]
                }
        
        return results
    
    def _perform_vendor_analysis(self, data: pd.DataFrame, 
                               query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform vendor analysis"""
        results = {}
        
        if 'Vendor' in data.columns and 'Amount' in data.columns:
            vendor_analysis = data.groupby('Vendor').agg({
                'Amount': ['sum', 'count', 'mean']
            }).round(2)
            vendor_analysis.columns = ['Total_Spend', 'Transaction_Count', 'Avg_Transaction']
            vendor_analysis = vendor_analysis.sort_values('Total_Spend', ascending=False)
            
            results['vendor_summary'] = {
                'total_vendors': len(vendor_analysis),
                'top_10_vendors': vendor_analysis.head(10).to_dict('index'),
                'vendor_concentration': {
                    'top_5_percent': float((vendor_analysis.head(5)['Total_Spend'].sum() / vendor_analysis['Total_Spend'].sum()) * 100),
                    'top_10_percent': float((vendor_analysis.head(10)['Total_Spend'].sum() / vendor_analysis['Total_Spend'].sum()) * 100)
                }
            }
            
            # Vendor transaction patterns
            if len(vendor_analysis) > 0:
                results['vendor_patterns'] = {
                    'high_volume_low_value': len(vendor_analysis[
                        (vendor_analysis['Transaction_Count'] > vendor_analysis['Transaction_Count'].median()) &
                        (vendor_analysis['Avg_Transaction'] < vendor_analysis['Avg_Transaction'].median())
                    ]),
                    'low_volume_high_value': len(vendor_analysis[
                        (vendor_analysis['Transaction_Count'] < vendor_analysis['Transaction_Count'].median()) &
                        (vendor_analysis['Avg_Transaction'] > vendor_analysis['Avg_Transaction'].median())
                    ])
                }
        
        return results
    
    def _perform_department_analysis(self, data: pd.DataFrame, 
                                   query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform department-specific analysis"""
        results = {}
        
        if 'Department' in data.columns and 'Amount' in data.columns:
            dept_analysis = data.groupby('Department').agg({
                'Amount': ['sum', 'count', 'mean', 'std']
            }).round(2)
            dept_analysis.columns = ['Total_Amount', 'Transaction_Count', 'Avg_Amount', 'Std_Amount']
            dept_analysis = dept_analysis.sort_values('Total_Amount', ascending=False)
            
            results['department_summary'] = dept_analysis.to_dict('index')
            
            # Department efficiency metrics (if applicable)
            if len(dept_analysis) > 1:
                results['department_metrics'] = {
                    'most_active': dept_analysis['Transaction_Count'].idxmax(),
                    'highest_spending': dept_analysis['Total_Amount'].idxmax(),
                    'highest_avg_transaction': dept_analysis['Avg_Amount'].idxmax(),
                    'most_variable': dept_analysis['Std_Amount'].idxmax()
                }
        
        return results
    
    def _perform_general_analysis(self, data: pd.DataFrame, 
                                query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform general analysis for unspecified queries"""
        results = {
            'data_overview': {
                'total_records': len(data),
                'columns': list(data.columns),
                'date_range': None
            }
        }
        
        if 'Amount' in data.columns:
            results['data_overview']['total_amount'] = float(data['Amount'].sum())
            results['data_overview']['avg_amount'] = float(data['Amount'].mean())
        
        if 'Date' in data.columns:
            try:
                dates = pd.to_datetime(data['Date'])
                results['data_overview']['date_range'] = {
                    'start': dates.min().strftime('%Y-%m-%d'),
                    'end': dates.max().strftime('%Y-%m-%d')
                }
            except:
                pass
        
        return results
    
    def _generate_summary_statistics(self, data: pd.DataFrame, 
                                   analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for the analysis"""
        summary = {
            'record_count': len(data),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        if 'Amount' in data.columns:
            amounts = data['Amount'].dropna()
            summary.update({
                'total_amount': float(amounts.sum()),
                'mean_amount': float(amounts.mean()),
                'median_amount': float(amounts.median()),
                'min_amount': float(amounts.min()),
                'max_amount': float(amounts.max()),
                'std_amount': float(amounts.std()) if len(amounts) > 1 else 0
            })
        
        return summary
    
    def _generate_visualizations(self, query_analysis: Dict[str, Any],
                               data_analysis: Dict[str, Any],
                               available_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Generate appropriate visualizations based on analysis"""
        visualizations = []
        
        intent = query_analysis['intent']
        results = data_analysis.get('results', {})
        
        if intent == 'comparison' and 'department_comparison' in results:
            # Department comparison bar chart
            dept_data = results['department_comparison']
            departments = list(dept_data.keys())
            amounts = [dept_data[dept]['Total_Amount'] for dept in departments]
            
            fig = px.bar(
                x=departments, 
                y=amounts,
                title="Department Spending Comparison",
                labels={'x': 'Department', 'y': 'Total Amount ($)'}
            )
            
            visualizations.append({
                'type': 'plotly',
                'title': 'Department Spending Comparison',
                'figure': fig,
                'description': 'Bar chart comparing total spending across departments'
            })
        
        elif intent == 'trend_analysis' and 'monthly_trend' in results:
            # Monthly trend line chart
            trend_data = results['monthly_trend']
            
            fig = px.line(
                x=trend_data['periods'],
                y=trend_data['amounts'],
                title="Monthly Spending Trend",
                labels={'x': 'Month', 'y': 'Amount ($)'}
            )
            
            visualizations.append({
                'type': 'plotly',
                'title': 'Monthly Spending Trend',
                'figure': fig,
                'description': 'Line chart showing spending trends over time'
            })
        
        elif intent == 'vendor_analysis' and 'vendor_summary' in results:
            # Top vendors bar chart
            vendor_data = results['vendor_summary']['top_10_vendors']
            vendors = list(vendor_data.keys())[:10]  # Top 10
            amounts = [vendor_data[vendor]['Total_Spend'] for vendor in vendors]
            
            fig = px.bar(
                x=amounts,
                y=vendors,
                orientation='h',
                title="Top 10 Vendors by Spending",
                labels={'x': 'Total Spend ($)', 'y': 'Vendor'}
            )
            
            visualizations.append({
                'type': 'plotly',
                'title': 'Top 10 Vendors by Spending',
                'figure': fig,
                'description': 'Horizontal bar chart showing top vendors by total spending'
            })
        
        elif intent == 'budget_analysis' and 'department_budget_analysis' in results:
            # Budget vs actual comparison
            budget_data = results['department_budget_analysis']
            departments = list(budget_data.keys())
            budget_amounts = [budget_data[dept]['Budget'] for dept in departments]
            actual_amounts = [budget_data[dept]['Actual'] for dept in departments]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Budget', x=departments, y=budget_amounts))
            fig.add_trace(go.Bar(name='Actual', x=departments, y=actual_amounts))
            
            fig.update_layout(
                title='Budget vs Actual by Department',
                xaxis_title='Department',
                yaxis_title='Amount ($)',
                barmode='group'
            )
            
            visualizations.append({
                'type': 'plotly',
                'title': 'Budget vs Actual by Department',
                'figure': fig,
                'description': 'Grouped bar chart comparing budgeted vs actual spending by department'
            })
        
        return visualizations
    
    def _generate_narrative_insights(self, query_analysis: Dict[str, Any],
                                   data_analysis: Dict[str, Any],
                                   original_query: str) -> str:
        """Generate narrative insights using AI"""
        
        insights_prompt = f"""
        Generate professional narrative insights for this municipal financial analysis:
        
        ORIGINAL QUERY: "{original_query}"
        
        ANALYSIS TYPE: {query_analysis['intent']}
        
        ANALYSIS RESULTS: {json.dumps(data_analysis.get('results', {}), indent=2, default=str)}
        
        SUMMARY STATISTICS: {json.dumps(data_analysis.get('summary_stats', {}), indent=2, default=str)}
        
        Generate a clear, professional narrative that:
        
        1. DIRECTLY ANSWERS the user's question
        2. HIGHLIGHTS KEY FINDINGS from the data analysis
        3. PROVIDES CONTEXT for the financial patterns observed
        4. IDENTIFIES potential areas of concern or opportunity
        5. SUGGESTS follow-up questions or deeper analysis
        
        Write in a clear, professional tone suitable for municipal finance directors.
        Focus on actionable insights rather than just restating the data.
        Keep the response concise but comprehensive (2-4 paragraphs).
        """
        
        ai_response = self.secure_ai_request(
            insights_prompt,
            "narrative_insights_generation",
            data_sources=["data_analysis", "query_analysis"],
            max_tokens=1500
        )
        
        return ai_response.get('response', 'Unable to generate narrative insights at this time.')
    
    def _generate_guidance_response(self, user_query: str, 
                                  query_analysis: Dict[str, Any]) -> str:
        """Generate guidance response for general questions or help requests"""
        
        guidance_prompt = f"""
        The user asked: "{user_query}"
        
        This appears to be a general question or help request about municipal financial analysis.
        
        Provide helpful guidance including:
        
        1. How to phrase financial queries for better results
        2. What types of analysis are available
        3. Example questions they could ask
        4. Available data sources and capabilities
        
        Keep the response helpful, professional, and specific to municipal finance.
        """
        
        ai_response = self.secure_ai_request(
            guidance_prompt,
            "guidance_response_generation",
            data_sources=["user_query"],
            max_tokens=1000
        )
        
        return ai_response.get('response', 'I can help you analyze municipal financial data. Try asking specific questions about spending, budgets, vendors, or departments.')
    
    def _save_conversation_context(self, user_query: str, 
                                 query_analysis: Dict[str, Any],
                                 response: Dict[str, Any]):
        """Save conversation context to database"""
        try:
            session_id = st.session_state.get('session_id', 'default')
            turn_number = st.session_state.get('nl_turn_number', 0) + 1
            st.session_state.nl_turn_number = turn_number
            
            conn = sqlite3.connect('nl_conversation_context.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO conversation_context
                (session_id, turn_number, user_query, parsed_intent, extracted_entities,
                 generated_response, chart_generated, data_sources)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                turn_number,
                user_query,
                query_analysis.get('intent', ''),
                json.dumps(query_analysis.get('entities', {})),
                json.dumps(response, default=str)[:5000],  # Truncate for storage
                len(response.get('visualizations', [])) > 0,
                json.dumps(response.get('data_analysis', {}).get('data_used', []))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Failed to save conversation context: {e}")
    
    def get_conversation_history(self, session_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve conversation history for context"""
        try:
            session_id = session_id or st.session_state.get('session_id', 'default')
            
            conn = sqlite3.connect('nl_conversation_context.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_query, parsed_intent, extracted_entities, timestamp
                FROM conversation_context
                WHERE session_id = ?
                ORDER BY turn_number DESC
                LIMIT ?
            ''', (session_id, limit))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'query': row[0],
                    'intent': row[1],
                    'entities': json.loads(row[2]) if row[2] else {},
                    'timestamp': row[3]
                })
            
            conn.close()
            return history
            
        except Exception as e:
            st.error(f"Failed to retrieve conversation history: {e}")
            return []