"""
Mantis AI Engine - Centralized AI Hub with Hybrid AI Integration
Aggregates all AI capabilities from across the GovSight platform into a single, powerful interface
Enhanced with intelligent local/API routing for optimal performance and cost efficiency
"""

import streamlit as st
import pandas as pd
import openai
import os
import json
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid
import re

# Import conversational what-if simulator
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from modules.scenario_planner.whatif_simulator import process_whatif_question
    WHATIF_SIMULATOR_AVAILABLE = True
except ImportError:
    WHATIF_SIMULATOR_AVAILABLE = False

# Import Hybrid AI System
try:
    from ..ai_engine.hybrid_ai_integration import get_hybrid_ai, enhanced_ai_analyze, enhanced_municipal_ai
    from ..ai_engine.hybrid_ai_router import get_hybrid_router
    HYBRID_AI_AVAILABLE = True
except ImportError:
    HYBRID_AI_AVAILABLE = False

# Import secure API key manager
try:
    from modules.security.api_key_manager import api_key_manager, get_openai_client
    API_KEY_MANAGER_AVAILABLE = True
except ImportError:
    API_KEY_MANAGER_AVAILABLE = False
    api_key_manager = None

# Import RAG engine
try:
    from ..ai_engine.simple_rag_engine import SimpleRAGEngine, RAGQueryProcessor, get_rag_engine
    RAG_ENGINE_AVAILABLE = True
except ImportError:
    RAG_ENGINE_AVAILABLE = False
    SimpleRAGEngine = None
    RAGQueryProcessor = None

# Set up OpenAI client with secure key management
def get_ai_client():
    """Get OpenAI client with graceful degradation"""
    if API_KEY_MANAGER_AVAILABLE:
        return get_openai_client()
    else:
        # Fallback to environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key and api_key != "sk-xxx":
            try:
                return openai.OpenAI(api_key=api_key)
            except:
                return None
    return None

client = get_ai_client()

class MantisAI:
    """
    Mantis AI - The central intelligence hub for GovSight
    Combines all AI capabilities: analysis, insights, reporting, forecasting, and recommendations
    Enhanced with RAG (Retrieval-Augmented Generation) for accurate data retrieval
    """
    
    def __init__(self):
        self.model = "gpt-4o"  # Latest OpenAI model
        self.conversation_history = []
        self.context_sources = []
        self.rag_engine = None
        self.rag_processor = None
        self.initialize_chat_storage()
        self.initialize_rag_engine()
    
    def initialize_chat_storage(self):
        """Initialize the chat history storage database"""
        if 'mantis_chat_db' not in st.session_state:
            try:
                conn = sqlite3.connect('mantis_conversations.db')
                cursor = conn.cursor()
                
                # Create conversations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        messages TEXT
                    )
                ''')
                
                # Create context_sources table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS context_sources (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT,
                        source_type TEXT,
                        source_name TEXT,
                        data_summary TEXT,
                        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                    )
                ''')
                
                conn.commit()
                conn.close()
                st.session_state.mantis_chat_db = True
            except Exception as e:
                st.error(f"Failed to initialize chat storage: {e}")
    
    def save_conversation(self, conversation_id: str, title: str, messages: List[Dict]):
        """Save conversation to database"""
        try:
            conn = sqlite3.connect('mantis_conversations.db')
            cursor = conn.cursor()
            
            messages_json = json.dumps(messages)
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO conversations (id, title, created_at, updated_at, messages)
                VALUES (?, ?, COALESCE((SELECT created_at FROM conversations WHERE id = ?), ?), ?, ?)
            ''', (conversation_id, title, conversation_id, now, now, messages_json))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Failed to save conversation: {e}")
    
    def load_conversations(self) -> List[Dict]:
        """Load all conversations from database"""
        try:
            conn = sqlite3.connect('mantis_conversations.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, created_at, updated_at 
                FROM conversations 
                ORDER BY updated_at DESC
            ''')
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'id': row[0],
                    'title': row[1],
                    'created_at': row[2],
                    'updated_at': row[3]
                })
            
            conn.close()
            return conversations
        except Exception as e:
            st.error(f"Failed to load conversations: {e}")
            return []
    
    def load_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Load messages for a specific conversation"""
        try:
            conn = sqlite3.connect('mantis_conversations.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT messages FROM conversations WHERE id = ?', (conversation_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return json.loads(result[0])
            return []
        except Exception as e:
            st.error(f"Failed to load conversation messages: {e}")
            return []
    
    def initialize_rag_engine(self):
        """Initialize RAG engine for document retrieval"""
        if RAG_ENGINE_AVAILABLE:
            try:
                self.rag_engine = get_rag_engine()
                self.rag_processor = RAGQueryProcessor(self.rag_engine, client)
                
                # Index databases if not already indexed
                if len(self.rag_engine.documents) == 0:
                    self.index_databases()
                    
            except Exception as e:
                print(f"Failed to initialize RAG engine: {e}")
                self.rag_engine = None
                self.rag_processor = None
    
    def index_databases(self):
        """Index key databases for RAG retrieval"""
        if not self.rag_engine:
            return
        
        try:
            # Index GL database with table existence checks
            gl_path = "databases/core/caselle_gl0_mock.db"
            if os.path.exists(gl_path):
                available_tables = self._get_available_tables(gl_path)
                gl_tables_to_index = ['glaccounts', 'transactions', 'departments', 'funds', 'vendors']
                existing_gl_tables = [table for table in gl_tables_to_index if table in available_tables]
                
                if existing_gl_tables:
                    print(f"Indexing GL tables: {existing_gl_tables}")
                    self.rag_engine.index_database_tables(gl_path, tables_to_index=existing_gl_tables)
                else:
                    print("No GL tables found to index")
            
            # Index Payroll database with table existence checks
            payroll_path = "databases/payroll_city_payroll_demo.db"
            if os.path.exists(payroll_path):
                available_tables = self._get_available_tables(payroll_path)
                payroll_tables_to_index = ['employees', 'payroll_records', 'benefits', 'time_tracking']
                existing_payroll_tables = [table for table in payroll_tables_to_index if table in available_tables]
                
                if existing_payroll_tables:
                    print(f"Indexing Payroll tables: {existing_payroll_tables}")
                    self.rag_engine.index_database_tables(payroll_path, tables_to_index=existing_payroll_tables)
                else:
                    print("No Payroll tables found to index")
            
            print(f"Indexed {len(self.rag_engine.documents)} documents for RAG")
            
        except Exception as e:
            print(f"Failed to index databases: {e}")
    
    def _get_available_tables(self, db_path: str) -> list:
        """Get list of available tables in database"""
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tables
        except Exception as e:
            print(f"Error getting tables from {db_path}: {e}")
            return []
    
    def process_with_rag(self, query: str) -> Dict[str, Any]:
        """Process query using RAG for enhanced context retrieval"""
        if self.rag_processor:
            try:
                return self.rag_processor.process_query(query, use_openai=bool(client))
            except Exception as e:
                return {'error': f"RAG processing failed: {e}"}
        return {'error': 'RAG engine not available'}
    
    def get_financial_context(self, org: str = "cityA") -> str:
        """Gather comprehensive financial context from all available sources"""
        context_parts = []
        
        try:
            # Import database functions
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from modules.database.connection_manager import load_org_data
            from common_utils import get_departments
            
            # Get department performance data
            dept_data = load_org_data(org)
            if not dept_data.empty:
                # Summary statistics
                total_budget = dept_data['Budget'].sum()
                total_actual = dept_data['Actual'].sum()
                variance = total_budget - total_actual
                utilization = (total_actual / total_budget * 100) if total_budget > 0 else 0
                
                context_parts.append(f"""
FINANCIAL OVERVIEW ({org.upper()}):
- Total Budget: ${total_budget:,.2f}
- Total Actual: ${total_actual:,.2f}
- Budget Variance: ${variance:,.2f}
- Utilization Rate: {utilization:.1f}%
- Departments: {dept_data['Department'].nunique()}
- Funds: {dept_data['Fund'].nunique()}
                """)
                
                # Department breakdown
                dept_summary = dept_data.groupby('Department').agg({
                    'Budget': 'sum',
                    'Actual': 'sum'
                }).round(2)
                
                context_parts.append("DEPARTMENT PERFORMANCE:")
                for dept, row in dept_summary.head(10).iterrows():
                    variance_pct = ((row['Actual'] / row['Budget'] - 1) * 100) if row['Budget'] > 0 else 0
                    context_parts.append(f"- {dept}: Budget ${row['Budget']:,.0f}, Actual ${row['Actual']:,.0f} ({variance_pct:+.1f}%)")
            
            # Get scenario planning context if available
            try:
                conn = sqlite3.connect('databases/core/caselle_gl0_mock.db')
                cursor = conn.cursor()
                
                cursor.execute("SELECT name, total_funding FROM scenarios ORDER BY created_at DESC LIMIT 5")
                scenarios = cursor.fetchall()
                
                if scenarios:
                    context_parts.append("\nRECENT SCENARIOS:")
                    for scenario in scenarios:
                        context_parts.append(f"- {scenario[0]}: ${scenario[1]:,.2f}")
                
                conn.close()
            except Exception:
                pass
                
        except Exception as e:
            context_parts.append(f"Note: Limited financial context available ({str(e)})")
        
        return "\n".join(context_parts)
    
    def get_multi_database_context(self) -> str:
        """Get comprehensive context from all connected databases"""
        from modules.database.connection_manager import (
            get_available_databases,
            execute_query
        )
        
        context_parts = ["MULTI-DATABASE SYSTEM CONTEXT:"]
        
        try:
            # Get all available databases
            available_dbs = get_available_databases()
            connected_dbs = {name: info for name, info in available_dbs.items() 
                           if info['status'] == 'connected'}
            
            context_parts.append(f"\nCONNECTED DATABASES ({len(connected_dbs)}):")
            for db_name, db_info in connected_dbs.items():
                context_parts.append(f"- {db_info['display_name']} ({db_info['type']}): {db_info['description']}")
            
            # Get data from GL Primary Database
            if 'gl_primary' in connected_dbs:
                context_parts.append("\n=== GL PRIMARY DATABASE DATA ===")
                gl_queries = [
                    ("Department Budget Summary", "SELECT department, SUM(budget) as total_budget, SUM(actual) as total_actual FROM financial_data GROUP BY department ORDER BY total_budget DESC LIMIT 5"),
                    ("Fund Analysis", "SELECT fund, SUM(budget) as fund_budget FROM financial_data GROUP BY fund ORDER BY fund_budget DESC LIMIT 5"),
                    ("Recent Transactions", "SELECT transaction_type, COUNT(*) as count FROM transactions WHERE date >= date('now', '-30 days') GROUP BY transaction_type LIMIT 5")
                ]
                
                for description, query in gl_queries:
                    try:
                        df = execute_query(query, db_name="gl_primary")
                        if not df.empty:
                            context_parts.append(f"\n{description}:")
                            for _, row in df.iterrows():
                                if 'budget' in description.lower():
                                    context_parts.append(f"- {row.iloc[0]}: Budget ${row.iloc[1]:,.0f}, Actual ${row.iloc[2]:,.0f}")
                                else:
                                    context_parts.append(f"- {row.iloc[0]}: {row.iloc[1]:,}")
                    except Exception as e:
                        context_parts.append(f"- {description}: Unable to retrieve ({str(e)})")
            
            # Get data from Utility Management Database
            if 'utility_management' in connected_dbs:
                context_parts.append("\n=== UTILITY MANAGEMENT DATABASE DATA ===")
                utility_queries = [
                    ("Customer Accounts", "SELECT account_status, COUNT(*) as count FROM customer_accounts GROUP BY account_status"),
                    ("Service Types", "SELECT service_type, COUNT(*) as customer_count FROM services GROUP BY service_type"),
                    ("Billing Summary", "SELECT billing_cycle, AVG(amount) as avg_bill FROM billing GROUP BY billing_cycle LIMIT 5"),
                    ("Meter Readings", "SELECT meter_type, COUNT(*) as meter_count FROM meters GROUP BY meter_type")
                ]
                
                for description, query in utility_queries:
                    try:
                        df = execute_query(query, db_name="utility_management")
                        if not df.empty:
                            context_parts.append(f"\n{description}:")
                            for _, row in df.iterrows():
                                context_parts.append(f"- {row.iloc[0]}: {row.iloc[1]:,}")
                    except Exception:
                        continue
            
            # Get data from Asset Management Database
            if 'asset_management' in connected_dbs:
                context_parts.append("\n=== ASSET MANAGEMENT DATABASE DATA ===")
                asset_queries = [
                    ("Asset Categories", "SELECT asset_category, COUNT(*) as asset_count FROM assets GROUP BY asset_category"),
                    ("Asset Condition", "SELECT condition_rating, COUNT(*) as count FROM assets GROUP BY condition_rating"),
                    ("Maintenance Status", "SELECT maintenance_status, COUNT(*) as count FROM maintenance_records GROUP BY maintenance_status"),
                    ("Infrastructure Types", "SELECT infrastructure_type, COUNT(*) as count FROM infrastructure GROUP BY infrastructure_type")
                ]
                
                for description, query in asset_queries:
                    try:
                        df = execute_query(query, db_name="asset_management")
                        if not df.empty:
                            context_parts.append(f"\n{description}:")
                            for _, row in df.iterrows():
                                context_parts.append(f"- {row.iloc[0]}: {row.iloc[1]:,}")
                    except Exception:
                        continue
            
            # Get data from Permits & Licensing Database
            if 'permits_licensing' in connected_dbs:
                context_parts.append("\n=== PERMITS & LICENSING DATABASE DATA ===")
                permits_queries = [
                    ("Permit Types", "SELECT permit_type, COUNT(*) as permit_count FROM permits GROUP BY permit_type"),
                    ("Application Status", "SELECT application_status, COUNT(*) as count FROM permit_applications GROUP BY application_status"),
                    ("License Categories", "SELECT license_category, COUNT(*) as license_count FROM licenses GROUP BY license_category"),
                    ("Revenue by Type", "SELECT fee_type, SUM(amount) as total_revenue FROM permit_fees GROUP BY fee_type ORDER BY total_revenue DESC LIMIT 5")
                ]
                
                for description, query in permits_queries:
                    try:
                        df = execute_query(query, db_name="permits_licensing")
                        if not df.empty:
                            context_parts.append(f"\n{description}:")
                            for _, row in df.iterrows():
                                if 'revenue' in description.lower():
                                    context_parts.append(f"- {row.iloc[0]}: ${row.iloc[1]:,.2f}")
                                else:
                                    context_parts.append(f"- {row.iloc[0]}: {row.iloc[1]:,}")
                    except Exception:
                        continue
            
            # Get data from Payroll Database
            if 'payroll' in connected_dbs:
                context_parts.append("\n=== PAYROLL DATABASE DATA ===")
                payroll_queries = [
                    ("Employee Count by Department", "SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department"),
                    ("Payroll Summary", "SELECT pay_period, SUM(gross_pay) as total_gross, SUM(net_pay) as total_net FROM payroll GROUP BY pay_period ORDER BY pay_period DESC LIMIT 3"),
                    ("Employee Status", "SELECT employment_status, COUNT(*) as count FROM employees GROUP BY employment_status"),
                    ("Benefits Enrollment", "SELECT benefit_type, COUNT(*) as enrolled_count FROM employee_benefits GROUP BY benefit_type"),
                    ("Time Tracking", "SELECT time_type, SUM(hours) as total_hours FROM time_entries WHERE entry_date >= date('now', '-30 days') GROUP BY time_type")
                ]
                
                for description, query in payroll_queries:
                    try:
                        df = execute_query(query, db_name="payroll")
                        if not df.empty:
                            context_parts.append(f"\n{description}:")
                            for _, row in df.iterrows():
                                if 'payroll summary' in description.lower():
                                    context_parts.append(f"- {row.iloc[0]}: Gross ${row.iloc[1]:,.2f}, Net ${row.iloc[2]:,.2f}")
                                elif 'hours' in description.lower():
                                    context_parts.append(f"- {row.iloc[0]}: {row.iloc[1]:,.1f} hours")
                                else:
                                    context_parts.append(f"- {row.iloc[0]}: {row.iloc[1]:,}")
                    except Exception:
                        continue
                        
        except Exception as e:
            context_parts.append(f"Multi-database context error: {str(e)}")
        
        return "\n".join(context_parts)
    
    def query_database(self, query: str, database_name: str = "gl_primary") -> pd.DataFrame:
        """Execute a query on a specific database and return results"""
        from modules.database.connection_manager import execute_query
        
        try:
            return execute_query(query, db_name=database_name)
        except Exception as e:
            st.error(f"Database query failed for {database_name}: {str(e)}")
            return pd.DataFrame()
    
    def get_database_schema_info(self, database_name: str) -> List[str]:
        """Get table names from a specific database"""
        try:
            # Try different schema discovery queries for different database types
            schema_queries = [
                "SELECT name FROM sqlite_master WHERE type='table'",  # SQLite
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'",  # PostgreSQL
                "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE()",  # MySQL
                "SELECT table_name FROM information_schema.tables"  # SQL Server
            ]
            
            for query in schema_queries:
                try:
                    df = self.query_database(query, database_name)
                    if not df.empty:
                        return df.iloc[:, 0].tolist()
                except:
                    continue
            return []
        except Exception:
            return []
    
    def get_ai_capabilities_context(self) -> str:
        """Document all AI capabilities available across the platform"""
        return """
MANTIS AI CAPABILITIES:
1. Multi-Database Intelligence & Analysis
   - Access to all connected databases (GL, Utility, Asset, Permits, Payroll)
   - Cross-database correlation and analysis
   - Comprehensive municipal data integration
   - Real-time data from live database connections (PostgreSQL, MySQL, SQL Server)
   - Unified reporting across all municipal systems

2. Financial Analysis & Insights
   - Budget variance analysis and trend identification
   - Department performance evaluation across all funds
   - Fund allocation optimization recommendations
   - Predictive spending forecasts with multi-source data
   - GL account analysis with period filtering

3. Utility Management Intelligence
   - Customer account analysis and service optimization
   - Billing pattern analysis and revenue forecasting
   - Meter reading data and consumption trends
   - Service interruption tracking and response optimization
   - Water, sewer, and electric utility integration

4. Asset Management Intelligence
   - Infrastructure condition assessment and prioritization
   - Maintenance scheduling optimization
   - Asset lifecycle analysis and replacement planning
   - Capital improvement project prioritization
   - Equipment performance tracking and analysis

5. Permits & Licensing Intelligence
   - Building permit trend analysis and revenue forecasting
   - Application processing time optimization
   - License renewal tracking and compliance monitoring
   - Fee structure analysis and optimization
   - Development pattern analysis

6. Payroll & HR Intelligence
   - Employee payroll analysis and cost tracking
   - Benefits enrollment and cost management
   - Time tracking and overtime analysis
   - Department staffing level optimization
   - Compensation analysis and benchmarking
   - HR metrics and workforce analytics

7. Scenario Planning & Modeling
   - What-if scenario analysis across all databases
   - Monte Carlo simulations with real municipal data
   - Funding strategy optimization
   - Risk assessment and mitigation

8. Grant Intelligence & Search
   - Real-time federal grant database search
   - State-specific grant opportunity identification
   - AI-powered grant recommendations based on financial needs
   - Grant eligibility analysis and match requirements
   - Integration with federal agencies (FEMA, DOT, EPA, HUD, USDA, DOJ)

9. Scenario Intelligence & Analysis
   - Access to all saved budget scenarios and project plans
   - Comprehensive scenario comparison and analysis
   - Funding mix analysis and risk assessment
   - Implementation complexity evaluation
   - Scenario impact analysis and recommendations

5. Data Visualization & Charts
   - Automatic chart generation when appropriate (bar, line, pie, scatter, tables)
   - Interactive Plotly visualizations for budget analysis
   - Department spending comparisons and trend analysis
   - Budget vs actual variance charts
   - Financial data tables with professional formatting

6. Document Analysis & Processing
   - PDF financial report analysis and extraction
   - CSV data file processing and statistical analysis
   - Multi-file upload and comprehensive document insights
   - AI-powered document recommendations and action items

7. Regulatory & Compliance Intelligence
   - GASB standards interpretation and guidance
   - Policy impact analysis
   - Compliance requirement tracking
   - Regulatory change monitoring

8. Reporting & Documentation
   - Automated report generation
   - Executive summary creation
   - Data visualization recommendations
   - Audit trail documentation

9. Anomaly Detection & Monitoring
   - Unusual spending pattern identification
   - Fraud detection algorithms
   - Performance anomaly alerts
   - Budget deviation warnings

10. Strategic Recommendations
    - Resource allocation optimization
    - Cost reduction opportunities
    - Revenue enhancement strategies
    - Operational efficiency improvements
        """
    
    def chat(self, prompt: str, org: str = "cityA") -> str:
        """Main chat method for conversational AI interactions with RAG support"""
        # Check if OpenAI client is available
        ai_client = get_ai_client()
        if not ai_client:
            return self._handle_no_api_key()
        
        try:
            # Try RAG first for data-specific questions
            rag_context = ""
            rag_sources = []
            if self.rag_processor:
                rag_result = self.process_with_rag(prompt)
                if 'context' in rag_result and rag_result['context']:
                    rag_context = f"\n\nRAG RETRIEVAL CONTEXT:\n{rag_result['context']}"
                    if 'sources' in rag_result:
                        rag_sources = rag_result['sources']
            
            # Get comprehensive context from all sources
            financial_context = self.get_financial_context(org)
            multi_db_context = self.get_multi_database_context()
            capabilities_context = self.get_ai_capabilities_context()
            
            # Check for uploaded file context
            file_context = ""
            if 'uploaded_file_contents' in st.session_state:
                file_context = "\n\nUPLOADED FILE CONTEXT:\n"
                for file_name, file_data in st.session_state.uploaded_file_contents.items():
                    file_context += f"\nFile: {file_name}\n"
                    if file_data['type'] == 'pdf':
                        file_context += f"Content: {file_data.get('content', '')[:1000]}...\n"
                    elif file_data['type'] == 'csv':
                        if 'content' in file_data and isinstance(file_data['content'], pd.DataFrame):
                            file_context += f"Columns: {list(file_data['content'].columns)}\n"
                            file_context += f"Sample data:\n{file_data['content'].head().to_string()}\n"
            
            # Construct the system prompt with multi-database context
            system_prompt = f"""You are Mantis, the advanced AI assistant for GovSight Financial Analyzer with multi-database intelligence capabilities. You are a municipal finance expert with comprehensive knowledge of:

{capabilities_context}

CURRENT FINANCIAL CONTEXT:
{financial_context}

MULTI-DATABASE CONTEXT:
{multi_db_context}

{rag_context}

{file_context}

Your role is to:
1. Provide expert financial analysis and recommendations across all connected databases
2. Answer questions about municipal finance, budgets, utilities, assets, and permits
3. Leverage data from GL, utility management, asset management, and permits databases
4. Analyze uploaded documents when provided
5. Generate actionable insights and strategic advice using integrated municipal data
6. Use data-driven approaches for all recommendations based on real connected database information

When users ask about:
- Financial data: Query the GL Primary database
- Utility operations: Query the Utility Management database  
- Infrastructure/assets: Query the Asset Management database
- Permits/licenses: Query the Permits & Licensing database
- Payroll/HR: Query the Payroll database

Always be professional, concise, and focused on municipal excellence. Reference specific data points from connected databases when available."""

            # Make API call
            response = ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except openai.AuthenticationError:
            return "🔐 **Authentication Error:** The OpenAI API key is invalid. Please check your configuration in the Admin Panel."
        except openai.RateLimitError:
            return "⏱️ **Rate Limit:** Too many requests. Please wait a moment and try again."
        except openai.APIConnectionError:
            return "🌐 **Connection Error:** Unable to connect to OpenAI. Please check your internet connection."
        except Exception as e:
            return f"⚠️ **Error:** {str(e)}\n\nPlease contact your administrator if this issue persists."
    
    def _handle_no_api_key(self) -> str:
        """Handle gracefully when no API key is configured"""
        return (
            "🤖 **AI Features Unavailable**\n\n"
            "The AI assistant requires an OpenAI API key to function. "
            "Please configure your API key in the Admin Panel:\n\n"
            "1. Navigate to the Admin Panel\n"
            "2. Find the 'OpenAI API Configuration' section\n"
            "3. Enter your OpenAI API key\n"
            "4. Click 'Save Key' and test the connection\n\n"
            "If you don't have an API key, you can get one from [OpenAI Platform](https://platform.openai.com/api-keys)."
        )
    
    def _is_whatif_question(self, user_message: str) -> bool:
        """Detect if the user is asking a what-if scenario question"""
        whatif_keywords = [
            'what if', 'what would happen if', 'simulate', 'scenario',
            'increase by', 'decrease by', 'cut by', 'raise by', 'boost by',
            'reallocate', 'move budget', 'transfer funds', 'reduce budget',
            'increase budget', 'compare scenarios', 'if we cut', 'if we increase',
            'budget simulation', 'test scenario', 'hypothetical'
        ]
        
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in whatif_keywords)
    
    def generate_response(self, user_message: str, conversation_history: List[Dict], org: str = "cityA", file_context: Optional[Dict] = None) -> str:
        """Generate AI response with full context and capabilities"""
        # Check if OpenAI client is available
        ai_client = get_ai_client()
        if not ai_client:
            return self._handle_no_api_key()
        
        try:
            # Build comprehensive context
            financial_context = self.get_financial_context(org)
            capabilities_context = self.get_ai_capabilities_context()
            
            # Check if user is asking about grants and provide real grant data
            grant_context = ""
            if any(keyword in user_message.lower() for keyword in ['grant', 'funding', 'federal', 'state', 'fema', 'hud', 'dot', 'epa']):
                grant_context = self.get_grant_intelligence_context(user_message, financial_context)
            
            # Check for what-if scenario questions first
            whatif_result = None
            if WHATIF_SIMULATOR_AVAILABLE and self._is_whatif_question(user_message):
                whatif_result = process_whatif_question(user_message, org)
            
            # Check if user is asking about scenarios and provide scenario data
            scenario_context = ""
            if any(keyword in user_message.lower() for keyword in ['scenario', 'plan', 'project', 'saved', 'compare', 'analysis']):
                scenario_context = self.get_scenario_intelligence_context(user_message)
            
            # Add file analysis context if files are uploaded
            file_analysis_context = ""
            if file_context:
                file_analysis_context = self.get_file_analysis_context(file_context)
            
            # Create system message with comprehensive municipal finance expertise
            system_message = f"""You are Mantis, the intelligent AI assistant embedded in GovSight, a government finance analytics and project planning platform. Your role is to help finance directors, analysts, city managers, and other authorized users turn complex financial accounting data into clear, actionable managerial insights.

CORE OBJECTIVES:
1. **Translate Accounting into Action** - Convert financial accounting data (e.g., from Caselle or other ERP systems) into managerial insights such as trends, anomalies, forecasts, over/under-spending, and fund usage recommendations.

2. **Support Decision-Making** - Help users explore budget scenarios, simulate fund reallocations, and make data-driven policy decisions that comply with GASB regulations and grant restrictions.

3. **Answer in Plain English** - Respond with clear, non-technical summaries when requested. Offer technical details (e.g., SQL queries, budget formulas, or GASB references) only when relevant or requested.

CURRENT FINANCIAL CONTEXT:
{financial_context}

MULTI-DATABASE CONTEXT:
{self.get_multi_database_context()}

AVAILABLE CAPABILITIES:
{capabilities_context}

{grant_context}

{scenario_context}

{file_analysis_context}

HOW YOU THINK AND WORK:
- You are aware of the organization, state, and fund classification settings stored in the platform
- You access financial data through SQL structure (typically tblTransaction) using keys like GLAccount, TransactionDate, and Amount
- You can reason across multiple modules: Scenario Planner, Historical Analysis, Department Insights, BI Sandbox, Legislative Impact Analyzer, and more
- You are context-aware: If a user selects a fund, department, or account, apply that context to follow-up questions automatically unless they change it
- You automatically create visualizations when users request charts, graphs, tables, or when analyzing data that would benefit from visual representation
- When creating visualizations, mention what type of chart you're generating and why it's appropriate for the analysis

TONE AND STYLE:
- **Tone**: Professional, clear, supportive — like a senior CPA or government finance analyst who knows their stuff but speaks like a normal human
- **Avoid**: Jargon, fear-mongering, or excessive optimism. Be honest, precise, and unbiased
- **Formatting**: Use tables and bullet points for financial breakdowns, graphs or charts when helpful, bold key takeaways or red flags

SAFETY AND GUARDRAILS:
- Never suggest reallocation from restricted funds unless the user explicitly confirms the transfer is permissible
- Cite state-specific rules using stored organization metadata
- Clarify ambiguous inputs or missing information with a polite follow-up prompt
- Respect department-level permissions — don't show data outside a user's access scope

CURRENT ORGANIZATION CONTEXT:
The user is working with {org.upper()} municipal financial data. Provide responses that are:
1. Specific to their municipal financial situation
2. Actionable and implementable  
3. Grounded in the actual data available
4. Strategic and forward-thinking
5. Compliant with municipal finance best practices

Always aim to save the user time, make data actionable, improve transparency and trust, and help cities turn numbers into neighborhood impact."""

            # Handle what-if scenario responses with charts
            if WHATIF_SIMULATOR_AVAILABLE and self._is_whatif_question(user_message):
                whatif_result = process_whatif_question(user_message, org)
                
                if whatif_result and whatif_result['success']:
                    # Display the scenario chart
                    if whatif_result.get('chart'):
                        st.plotly_chart(whatif_result['chart'], use_container_width=True)
                    
                    # Return AI response with scenario summary
                    whatif_context = f"\n\nWHAT-IF SCENARIO RESULTS:\n{whatif_result.get('summary', '')}\n"
                    
                    # Generate AI response incorporating the what-if results
                    api_messages = [{"role": "system", "content": system_message + whatif_context}]
                    api_messages.append({"role": "user", "content": f"I just ran this what-if scenario: '{user_message}'. Please analyze the results and provide insights based on the scenario analysis that was generated."})
                    
                    response = ai_client.chat.completions.create(
                        model=self.model,
                        messages=api_messages,
                        max_tokens=800,
                        temperature=0.7
                    )
                    
                    return f"{whatif_result.get('message', '')}\n\n{response.choices[0].message.content}"
                elif whatif_result:
                    # What-if failed, fall back to regular AI with error message
                    api_messages = [{"role": "system", "content": system_message}]
                    api_messages.append({"role": "user", "content": user_message})
                    
                    response = ai_client.chat.completions.create(
                        model=self.model,
                        messages=api_messages,
                        max_tokens=1000,
                        temperature=0.7
                    )
                    
                    return f"{whatif_result.get('message', 'I had trouble processing that scenario.')}\n\n{response.choices[0].message.content}"
            
            # Prepare messages for API - ensure proper typing
            api_messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history with proper message format
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                    api_messages.append({
                        "role": msg["role"],
                        "content": str(msg["content"])
                    })
            
            # Add current user message
            api_messages.append({"role": "user", "content": user_message})
            
            # Generate response - cast to proper type for OpenAI API
            from typing import cast
            response = ai_client.chat.completions.create(
                model=self.model,
                messages=cast(list, api_messages),
                max_tokens=1000,
                temperature=0.7
            )
            
            # Safely extract content
            content = response.choices[0].message.content
            return content if content is not None else "I apologize, but I couldn't generate a response. Please try again."
            
        except openai.AuthenticationError:
            return "🔐 **Authentication Error:** The OpenAI API key is invalid. Please check your configuration in the Admin Panel."
        except openai.RateLimitError:
            return "⏱️ **Rate Limit:** Too many requests. Please wait a moment and try again."
        except openai.APIConnectionError:
            return "🌐 **Connection Error:** Unable to connect to OpenAI. Please check your internet connection."
        except Exception as e:
            return f"⚠️ **Error:** {str(e)}\n\nPlease ensure your OpenAI API key is properly configured in the Admin Panel."
    
    def get_file_analysis_context(self, file_context: Optional[Dict]) -> str:
        """Generate context from uploaded files for AI analysis"""
        if not file_context:
            return ""
        
        context_parts = ["UPLOADED DOCUMENTS FOR ANALYSIS:"]
        
        for file_name, file_data in file_context.items():
            file_type = file_data.get('type', 'unknown')
            
            if file_type == 'pdf':
                pages = file_data.get('pages', 0)
                content_preview = file_data.get('content', '')[:1000]  # First 1000 chars
                context_parts.append(f"""
**{file_name}** (PDF Document)
- Pages: {pages}
- Content Sample: {content_preview}...
- Analysis Available: Full text extraction and analysis capabilities
                """)
                
            elif file_type == 'csv':
                rows = file_data.get('rows', 0)
                columns = file_data.get('columns', [])
                summary = file_data.get('summary', '')
                
                # Get sample data for context
                df = file_data.get('content')
                sample_data = ""
                if df is not None and not df.empty:
                    sample_data = df.head(3).to_string()
                
                context_parts.append(f"""
**{file_name}** (CSV Data File)
- Rows: {rows:,}
- Columns: {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}
- Sample Data:
{sample_data}
- Statistical Summary:
{summary[:500]}...
- Analysis Available: Full data analysis, statistical insights, trend analysis
                """)
        
        context_parts.append("""
DOCUMENT ANALYSIS INSTRUCTIONS:
- When users ask about uploaded files, provide specific analysis based on actual content
- For PDFs: Extract key financial information, identify important dates, amounts, and recommendations
- For CSV files: Perform statistical analysis, identify trends, calculate variances, and provide insights
- Always reference specific data points from the uploaded files in your responses
- Offer actionable recommendations based on the document content
        """)
        
        return "\n".join(context_parts)
    
    def create_visualization(self, data_description: str, chart_type: str, data_source: str = None) -> go.Figure:
        """Create comprehensive Plotly visualizations with full library integration"""
        try:
            # Import database functions for real data
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from modules.database.connection_manager import load_org_data
            
            # Load actual municipal data
            org_data = load_org_data("cityA")
            
            if org_data.empty:
                return self._create_no_data_figure()
            
            # Enhanced chart type routing with full Plotly capabilities
            chart_type = chart_type.lower()
            
            # Basic chart types
            if chart_type in ['bar', 'column', 'bar_chart']:
                return self.create_bar_chart(org_data, data_description)
            elif chart_type in ['line', 'trend', 'line_chart', 'time_series']:
                return self.create_line_chart(org_data, data_description)
            elif chart_type in ['pie', 'donut', 'pie_chart']:
                return self.create_pie_chart(org_data, data_description)
            elif chart_type in ['scatter', 'correlation', 'scatter_plot']:
                return self.create_scatter_plot(org_data, data_description)
            
            # Advanced chart types
            elif chart_type in ['heatmap', 'correlation_matrix']:
                return self.create_heatmap(org_data, data_description)
            elif chart_type in ['box', 'box_plot', 'boxplot']:
                return self.create_box_plot(org_data, data_description)
            elif chart_type in ['violin', 'violin_plot']:
                return self.create_violin_plot(org_data, data_description)
            elif chart_type in ['histogram', 'distribution']:
                return self.create_histogram(org_data, data_description)
            elif chart_type in ['treemap', 'tree_map']:
                return self.create_treemap(org_data, data_description)
            elif chart_type in ['sunburst', 'sun_burst']:
                return self.create_sunburst(org_data, data_description)
            elif chart_type in ['waterfall', 'waterfall_chart']:
                return self.create_waterfall_chart(org_data, data_description)
            elif chart_type in ['funnel', 'funnel_chart']:
                return self.create_funnel_chart(org_data, data_description)
            elif chart_type in ['gauge', 'gauge_chart', 'kpi']:
                return self.create_gauge_chart(org_data, data_description)
            elif chart_type in ['radar', 'radar_chart', 'spider']:
                return self.create_radar_chart(org_data, data_description)
            elif chart_type in ['sankey', 'sankey_diagram']:
                return self.create_sankey_diagram(org_data, data_description)
            elif chart_type in ['3d_scatter', '3d_surface']:
                return self.create_3d_chart(org_data, data_description, chart_type)
            elif chart_type in ['candlestick', 'ohlc']:
                return self.create_candlestick_chart(org_data, data_description)
            elif chart_type in ['parallel_coordinates', 'parallel']:
                return self.create_parallel_coordinates(org_data, data_description)
            elif chart_type in ['subplot', 'subplots', 'multi_chart']:
                return self.create_subplot_chart(org_data, data_description)
            elif chart_type in ['table', 'summary', 'data_table']:
                return self.create_data_table(org_data, data_description)
            
            # Default to intelligent chart selection
            else:
                return self.create_intelligent_chart(org_data, data_description)
                
        except Exception as e:
            return self._create_error_figure(str(e))
    
    def _create_no_data_figure(self) -> go.Figure:
        """Create a professional no-data figure"""
        fig = go.Figure()
        fig.add_annotation(
            text="📊 No data available for visualization<br><br>Please ensure your data source is connected",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray"),
            align="center"
        )
        fig.update_layout(
            title="Data Visualization",
            height=400,
            paper_bgcolor="white",
            plot_bgcolor="white"
        )
        return fig
    
    def _create_error_figure(self, error_message: str) -> go.Figure:
        """Create a professional error figure"""
        fig = go.Figure()
        fig.add_annotation(
            text=f"⚠️ Visualization Error<br><br>{error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red"),
            align="center"
        )
        fig.update_layout(
            title="Visualization Error",
            height=400,
            paper_bgcolor="white",
            plot_bgcolor="white"
        )
        return fig
    
    def create_bar_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create budget variance bar chart"""
        try:
            # Calculate budget vs actual for departments
            dept_summary = data.groupby('Department').agg({
                'Budget': 'sum',
                'Actual': 'sum'
            }).round(2)
            
            dept_summary['Variance'] = dept_summary['Budget'] - dept_summary['Actual']
            dept_summary['Variance_Pct'] = (dept_summary['Variance'] / dept_summary['Budget'] * 100).round(1)
            
            # Create grouped bar chart
            fig = go.Figure()
            
            # Add Budget bars
            fig.add_trace(go.Bar(
                name='Budget',
                x=dept_summary.index,
                y=dept_summary['Budget'],
                marker_color='lightblue',
                text=[f'${val:,.0f}' for val in dept_summary['Budget']],
                textposition='outside'
            ))
            
            # Add Actual bars
            fig.add_trace(go.Bar(
                name='Actual',
                x=dept_summary.index,
                y=dept_summary['Actual'],
                marker_color='darkblue',
                text=[f'${val:,.0f}' for val in dept_summary['Actual']],
                textposition='outside'
            ))
            
            fig.update_layout(
                title='Department Budget vs Actual Spending',
                xaxis_title='Department',
                yaxis_title='Amount ($)',
                barmode='group',
                height=500,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            return self.create_error_chart(f"Bar chart error: {str(e)}")
    
    def create_line_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create spending trend line chart"""
        try:
            # Create monthly spending trend (simulate monthly data from annual)
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            # Get top 5 departments by budget
            top_depts = data.groupby('Department')['Actual'].sum().nlargest(5)
            
            fig = go.Figure()
            
            for dept in top_depts.index:
                # Simulate monthly progression (cumulative spending)
                annual_actual = top_depts[dept]
                monthly_progression = [annual_actual * (i+1)/12 for i in range(12)]
                
                fig.add_trace(go.Scatter(
                    x=months,
                    y=monthly_progression,
                    mode='lines+markers',
                    name=dept,
                    line=dict(width=3),
                    marker=dict(size=6)
                ))
            
            fig.update_layout(
                title='Department Spending Trends (Cumulative)',
                xaxis_title='Month',
                yaxis_title='Cumulative Spending ($)',
                height=500,
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            return self.create_error_chart(f"Line chart error: {str(e)}")
    
    def create_pie_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create budget allocation pie chart"""
        try:
            # Department budget allocation
            dept_budgets = data.groupby('Department')['Budget'].sum().sort_values(ascending=False)
            
            fig = go.Figure(data=[go.Pie(
                labels=dept_budgets.index,
                values=dept_budgets.values,
                hole=0.3,  # Donut style
                textinfo='label+percent',
                textposition='outside'
            )])
            
            fig.update_layout(
                title='Budget Allocation by Department',
                height=500,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            return self.create_error_chart(f"Pie chart error: {str(e)}")
    
    def create_scatter_plot(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create budget vs actual scatter plot"""
        try:
            dept_summary = data.groupby('Department').agg({
                'Budget': 'sum',
                'Actual': 'sum'
            }).reset_index()
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=dept_summary['Budget'],
                y=dept_summary['Actual'],
                mode='markers+text',
                text=dept_summary['Department'],
                textposition='top center',
                marker=dict(
                    size=12,
                    color='darkblue',
                    opacity=0.7
                ),
                name='Departments'
            ))
            
            # Add perfect correlation line
            max_val = max(dept_summary['Budget'].max(), dept_summary['Actual'].max())
            fig.add_trace(go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode='lines',
                line=dict(dash='dash', color='red'),
                name='Perfect Correlation'
            ))
            
            fig.update_layout(
                title='Budget vs Actual Spending Correlation',
                xaxis_title='Budget ($)',
                yaxis_title='Actual Spending ($)',
                height=500
            )
            
            return fig
            
        except Exception as e:
            return self.create_error_chart(f"Scatter plot error: {str(e)}")
    
    def create_data_table(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create formatted data table"""
        try:
            # Create department summary table
            dept_summary = data.groupby('Department').agg({
                'Budget': 'sum',
                'Actual': 'sum'
            }).round(2)
            
            dept_summary['Variance'] = dept_summary['Budget'] - dept_summary['Actual']
            dept_summary['Variance %'] = (dept_summary['Variance'] / dept_summary['Budget'] * 100).round(1)
            dept_summary['Utilization %'] = (dept_summary['Actual'] / dept_summary['Budget'] * 100).round(1)
            
            # Format currency columns
            for col in ['Budget', 'Actual', 'Variance']:
                dept_summary[col] = dept_summary[col].apply(lambda x: f'${x:,.0f}')
            
            # Reset index to get Department as column
            dept_summary = dept_summary.reset_index()
            
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=list(dept_summary.columns),
                    fill_color='lightblue',
                    align='left',
                    font=dict(size=12, color='darkblue')
                ),
                cells=dict(
                    values=[dept_summary[col] for col in dept_summary.columns],
                    fill_color='white',
                    align='left',
                    font=dict(size=11)
                )
            )])
            
            fig.update_layout(
                title='Department Financial Summary',
                height=400
            )
            
            return fig
            
        except Exception as e:
            return self.create_error_chart(f"Table error: {str(e)}")
    
    def create_error_chart(self, error_message: str) -> go.Figure:
        """Create error message chart"""
        fig = go.Figure()
        fig.add_annotation(
            text=error_message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title="Visualization Error",
            height=400,
            paper_bgcolor="white",
            plot_bgcolor="white"
        )
        return fig
    
    # Advanced Plotly Visualization Methods
    
    def create_heatmap(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create correlation heatmap"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) < 2:
                return self._create_error_figure("Need at least 2 numeric columns for heatmap")
            
            correlation_matrix = data[numeric_cols].corr()
            
            fig = px.imshow(
                correlation_matrix,
                title="Financial Data Correlation Matrix",
                color_continuous_scale="RdYlBu_r",
                aspect="auto"
            )
            
            fig.update_layout(height=500)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Heatmap error: {str(e)}")
    
    def create_box_plot(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create box plot for distribution analysis"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) == 0:
                return self._create_error_figure("No numeric columns found for box plot")
            
            fig = go.Figure()
            
            for col in numeric_cols[:5]:  # Limit to 5 columns
                fig.add_trace(go.Box(
                    y=data[col],
                    name=col,
                    boxpoints='outliers'
                ))
            
            fig.update_layout(
                title="Distribution Analysis - Box Plot",
                yaxis_title="Values",
                height=500
            )
            
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Box plot error: {str(e)}")
    
    def create_violin_plot(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create violin plot for detailed distribution"""
        try:
            if 'Department' not in data.columns or 'Budget' not in data.columns:
                return self._create_error_figure("Need Department and Budget columns for violin plot")
            
            fig = px.violin(
                data, 
                x="Department", 
                y="Budget",
                title="Budget Distribution by Department",
                box=True
            )
            
            fig.update_layout(height=500)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Violin plot error: {str(e)}")
    
    def create_histogram(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create histogram for value distribution"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) == 0:
                return self._create_error_figure("No numeric columns found for histogram")
            
            col = 'Budget' if 'Budget' in numeric_cols else numeric_cols[0]
            
            fig = px.histogram(
                data,
                x=col,
                title=f"Distribution of {col}",
                nbins=30
            )
            
            fig.update_layout(height=500)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Histogram error: {str(e)}")
    
    def create_treemap(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create treemap for hierarchical data"""
        try:
            if 'Department' not in data.columns or 'Budget' not in data.columns:
                return self._create_error_figure("Need Department and Budget columns for treemap")
            
            dept_summary = data.groupby('Department')['Budget'].sum().reset_index()
            
            fig = px.treemap(
                dept_summary,
                path=['Department'],
                values='Budget',
                title="Budget Allocation by Department (Treemap)"
            )
            
            fig.update_layout(height=500)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Treemap error: {str(e)}")
    
    def create_sunburst(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create sunburst chart for hierarchical visualization"""
        try:
            if 'Department' not in data.columns or 'Budget' not in data.columns:
                return self._create_error_figure("Need Department and Budget columns for sunburst")
            
            # Create hierarchy: Total -> Department -> Category
            dept_summary = data.groupby(['Department']).agg({
                'Budget': 'sum'
            }).reset_index()
            
            fig = px.sunburst(
                dept_summary,
                path=['Department'],
                values='Budget',
                title="Budget Hierarchy (Sunburst)"
            )
            
            fig.update_layout(height=500)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Sunburst error: {str(e)}")
    
    def create_waterfall_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create waterfall chart for variance analysis"""
        try:
            if 'Department' not in data.columns or 'Budget' not in data.columns or 'Actual' not in data.columns:
                return self._create_error_figure("Need Department, Budget, and Actual columns for waterfall")
            
            dept_summary = data.groupby('Department').agg({
                'Budget': 'sum',
                'Actual': 'sum'
            }).reset_index()
            
            dept_summary['Variance'] = dept_summary['Actual'] - dept_summary['Budget']
            
            fig = go.Figure()
            
            # Starting budget
            cumulative = 0
            for i, row in dept_summary.iterrows():
                variance = row['Variance']
                color = 'green' if variance >= 0 else 'red'
                
                fig.add_trace(go.Bar(
                    name=row['Department'],
                    x=[row['Department']],
                    y=[abs(variance)],
                    marker_color=color,
                    text=f"${variance:,.0f}",
                    textposition='outside'
                ))
            
            fig.update_layout(
                title="Budget Variance Waterfall",
                yaxis_title="Variance Amount ($)",
                height=500
            )
            
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Waterfall error: {str(e)}")
    
    def create_funnel_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create funnel chart for process analysis"""
        try:
            if 'Department' not in data.columns or 'Budget' not in data.columns:
                return self._create_error_figure("Need Department and Budget columns for funnel")
            
            dept_summary = data.groupby('Department')['Budget'].sum().sort_values(ascending=False)
            
            fig = go.Figure(go.Funnel(
                y=dept_summary.index,
                x=dept_summary.values,
                textinfo="value+percent initial",
                text=[f"${val:,.0f}" for val in dept_summary.values]
            ))
            
            fig.update_layout(
                title="Department Budget Funnel",
                height=500
            )
            
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Funnel error: {str(e)}")
    
    def create_gauge_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create gauge chart for KPI visualization"""
        try:
            if 'Budget' not in data.columns or 'Actual' not in data.columns:
                return self._create_error_figure("Need Budget and Actual columns for gauge")
            
            total_budget = data['Budget'].sum()
            total_actual = data['Actual'].sum()
            utilization = (total_actual / total_budget * 100) if total_budget > 0 else 0
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=utilization,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Budget Utilization %"},
                delta={'reference': 100},
                gauge={
                    'axis': {'range': [None, 150]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 75], 'color': "lightgray"},
                        {'range': [75, 100], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 100
                    }
                }
            ))
            
            fig.update_layout(height=500)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Gauge error: {str(e)}")
    
    def create_radar_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create radar chart for multi-dimensional analysis"""
        try:
            if 'Department' not in data.columns:
                return self._create_error_figure("Need Department column for radar chart")
            
            # Get top 5 departments
            top_depts = data.groupby('Department')['Budget'].sum().nlargest(5)
            
            numeric_cols = data.select_dtypes(include=['number']).columns[:6]  # Max 6 dimensions
            
            fig = go.Figure()
            
            for dept in top_depts.index[:3]:  # Show top 3 departments
                dept_data = data[data['Department'] == dept]
                values = []
                for col in numeric_cols:
                    if len(dept_data) > 0:
                        values.append(dept_data[col].mean())
                    else:
                        values.append(0)
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=numeric_cols,
                    fill='toself',
                    name=dept
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max([data[col].max() for col in numeric_cols])]
                    )),
                title="Multi-Dimensional Department Analysis",
                height=500
            )
            
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Radar error: {str(e)}")
    
    def create_sankey_diagram(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create Sankey diagram for flow analysis"""
        try:
            if 'Department' not in data.columns or 'Budget' not in data.columns:
                return self._create_error_figure("Need Department and Budget columns for Sankey")
            
            # Simplified Sankey: Budget allocation flow
            dept_summary = data.groupby('Department')['Budget'].sum()
            
            # Create nodes
            source_indices = [0] * len(dept_summary)  # All from "Total Budget"
            target_indices = list(range(1, len(dept_summary) + 1))  # To each department
            values = dept_summary.values.tolist()
            
            labels = ['Total Budget'] + dept_summary.index.tolist()
            
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=labels
                ),
                link=dict(
                    source=source_indices,
                    target=target_indices,
                    value=values
                )
            )])
            
            fig.update_layout(
                title="Budget Allocation Flow",
                height=500
            )
            
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Sankey error: {str(e)}")
    
    def create_3d_chart(self, data: pd.DataFrame, description: str, chart_subtype: str) -> go.Figure:
        """Create 3D visualizations"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) < 3:
                return self._create_error_figure("Need at least 3 numeric columns for 3D chart")
            
            x_col, y_col, z_col = numeric_cols[0], numeric_cols[1], numeric_cols[2]
            
            if chart_subtype == '3d_scatter':
                fig = px.scatter_3d(
                    data,
                    x=x_col,
                    y=y_col,
                    z=z_col,
                    color='Department' if 'Department' in data.columns else None,
                    title="3D Scatter Plot"
                )
            else:  # 3d_surface
                # Create surface plot with aggregated data
                fig = go.Figure(data=[go.Surface(
                    x=data[x_col],
                    y=data[y_col],
                    z=data[z_col].values.reshape((int(len(data)**0.5), -1)) if len(data) > 4 else [[0, 1], [1, 0]]
                )])
                fig.update_layout(title="3D Surface Plot")
            
            fig.update_layout(height=600)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"3D chart error: {str(e)}")
    
    def create_candlestick_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create candlestick chart (adapted for budget data)"""
        try:
            if 'Department' not in data.columns or 'Budget' not in data.columns:
                return self._create_error_figure("Need Department and Budget columns for candlestick")
            
            # Simulate OHLC data from budget information
            dept_summary = data.groupby('Department').agg({
                'Budget': ['min', 'max', 'mean'],
                'Actual': ['min', 'max', 'mean']
            }).round(2)
            
            # Flatten column names
            dept_summary.columns = ['Budget_Low', 'Budget_High', 'Budget_Open', 'Actual_Low', 'Actual_High', 'Actual_Close']
            
            fig = go.Figure(data=[go.Candlestick(
                x=dept_summary.index,
                open=dept_summary['Budget_Open'],
                high=dept_summary['Budget_High'],
                low=dept_summary['Budget_Low'],
                close=dept_summary['Actual_Close'],
                name="Budget vs Actual"
            )])
            
            fig.update_layout(
                title="Budget Performance (Candlestick Style)",
                yaxis_title="Amount ($)",
                height=500
            )
            
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Candlestick error: {str(e)}")
    
    def create_parallel_coordinates(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create parallel coordinates plot"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) < 2:
                return self._create_error_figure("Need at least 2 numeric columns for parallel coordinates")
            
            # Sample data for performance
            sample_data = data.sample(min(100, len(data))) if len(data) > 100 else data
            
            fig = px.parallel_coordinates(
                sample_data,
                dimensions=numeric_cols[:6],  # Limit to 6 dimensions
                color='Budget' if 'Budget' in numeric_cols else numeric_cols[0],
                title="Multi-Dimensional Data Analysis"
            )
            
            fig.update_layout(height=500)
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Parallel coordinates error: {str(e)}")
    
    def create_subplot_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Create subplot with multiple chart types"""
        try:
            # Create subplots with 2x2 grid
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Budget vs Actual', 'Department Distribution', 'Trend Analysis', 'Variance'),
                specs=[[{"secondary_y": False}, {"type": "pie"}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            if 'Department' in data.columns and 'Budget' in data.columns:
                # Subplot 1: Bar chart
                dept_summary = data.groupby('Department').agg({'Budget': 'sum', 'Actual': 'sum'})
                fig.add_trace(
                    go.Bar(name='Budget', x=dept_summary.index, y=dept_summary['Budget']),
                    row=1, col=1
                )
                
                # Subplot 2: Pie chart
                fig.add_trace(
                    go.Pie(labels=dept_summary.index, values=dept_summary['Budget'], name="Budget"),
                    row=1, col=2
                )
                
                # Subplot 3: Line chart (simulated trend)
                months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
                cumulative = [dept_summary['Actual'].sum() * (i+1)/6 for i in range(6)]
                fig.add_trace(
                    go.Scatter(x=months, y=cumulative, mode='lines+markers', name='Cumulative'),
                    row=2, col=1
                )
                
                # Subplot 4: Variance analysis
                variance = dept_summary['Actual'] - dept_summary['Budget']
                fig.add_trace(
                    go.Bar(name='Variance', x=dept_summary.index, y=variance),
                    row=2, col=2
                )
            
            fig.update_layout(
                title="Comprehensive Financial Dashboard",
                height=800,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            return self._create_error_figure(f"Subplot error: {str(e)}")
    
    def create_intelligent_chart(self, data: pd.DataFrame, description: str) -> go.Figure:
        """Intelligent chart selection based on data characteristics"""
        try:
            # Analyze data to suggest best chart type
            numeric_cols = data.select_dtypes(include=['number']).columns
            categorical_cols = data.select_dtypes(include=['object', 'category']).columns
            
            # Decision logic for intelligent chart selection
            if 'Department' in data.columns and len(numeric_cols) >= 2:
                # Budget analysis - use grouped bar chart
                return self.create_bar_chart(data, description)
            elif len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
                # Categorical vs numeric - use bar chart
                return self.create_bar_chart(data, description)
            elif len(numeric_cols) >= 3:
                # Multiple numeric - use correlation heatmap
                return self.create_heatmap(data, description)
            elif len(numeric_cols) >= 2:
                # Two numeric - use scatter plot
                return self.create_scatter_plot(data, description)
            else:
                # Fallback to simple summary
                return self.create_data_table(data, description)
                
        except Exception as e:
            return self._create_error_figure(f"Intelligent chart error: {str(e)}")
    
    def should_create_visualization(self, user_message: str, file_context: Optional[Dict] = None) -> tuple[bool, str, str]:
        """Determine if a visualization should be created based on user message"""
        # Keywords that suggest visualization needs
        viz_keywords = {
            'chart': 'bar',
            'graph': 'line', 
            'plot': 'scatter',
            'table': 'table',
            'visualize': 'bar',
            'show me': 'bar',
            'compare': 'bar',
            'trend': 'line',
            'over time': 'line',
            'breakdown': 'pie',
            'allocation': 'pie',
            'distribution': 'pie',
            'correlation': 'scatter',
            'relationship': 'scatter'
        }
        
        message_lower = user_message.lower()
        
        # Check for visualization keywords
        for keyword, chart_type in viz_keywords.items():
            if keyword in message_lower:
                return True, chart_type, f"Data visualization: {keyword}"
        
        # Check if analyzing CSV data
        if file_context:
            for file_name, file_data in file_context.items():
                if file_data.get('type') == 'csv':
                    # Automatically suggest visualization for CSV data analysis
                    if any(word in message_lower for word in ['analyze', 'summary', 'insights', 'trends']):
                        return True, 'bar', f"CSV data analysis: {file_name}"
        
        return False, '', ''
    
    def get_grant_intelligence_context(self, user_message: str, financial_context: str) -> str:
        """Get relevant grant information based on user query and financial context"""
        try:
            # Import grant intelligence
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from grant_intelligence import GrantIntelligence
            
            grant_intel = GrantIntelligence()
            
            # Extract keywords from user message
            grant_keywords = self.extract_grant_keywords(user_message)
            
            # Search for relevant grants
            federal_grants = grant_intel.search_federal_grants(grant_keywords)
            recommendations = grant_intel.get_grant_recommendations(financial_context)
            
            if not federal_grants and not recommendations:
                return ""
            
            context = "\nRELEVANT GRANT OPPORTUNITIES:\n"
            
            # Add search results
            if federal_grants:
                context += "Based on your query, here are relevant federal grants:\n"
                for grant in federal_grants[:3]:  # Top 3 results
                    context += grant_intel.format_grant_for_mantis(grant)
                    context += "\n"
            
            # Add AI recommendations
            if recommendations:
                context += "\nAI-RECOMMENDED GRANTS (based on your financial profile):\n"
                for grant in recommendations[:2]:  # Top 2 recommendations
                    context += grant_intel.format_grant_for_mantis(grant)
                    context += "\n"
            
            return context
            
        except Exception as e:
            return f"\nNote: Grant search capabilities are temporarily limited: {str(e)}"
    
    def extract_grant_keywords(self, message: str) -> str:
        """Extract relevant keywords for grant searching"""
        # Common municipal department and need keywords
        keywords_map = {
            'police': 'law enforcement officers hiring equipment',
            'fire': 'firefighters equipment vehicles training',
            'road': 'transportation infrastructure highway safety',
            'water': 'infrastructure environmental wastewater',
            'park': 'recreation community development environment',
            'emergency': 'disaster preparedness safety mitigation',
            'infrastructure': 'transportation roads bridges water',
            'safety': 'public safety emergency equipment',
            'environment': 'sustainability green climate',
            'community': 'development housing social services'
        }
        
        message_lower = message.lower()
        extracted_keywords = []
        
        for key, keywords in keywords_map.items():
            if key in message_lower:
                extracted_keywords.extend(keywords.split())
        
        # If no specific keywords found, use the message itself
        if not extracted_keywords:
            # Remove common words and return relevant terms
            common_words = {'the', 'and', 'or', 'but', 'for', 'with', 'what', 'how', 'can', 'help', 'me', 'find', 'search'}
            words = [word.strip('.,!?') for word in message_lower.split() if word not in common_words and len(word) > 2]
            return ' '.join(words[:5])  # Return first 5 relevant words
        
        return ' '.join(list(set(extracted_keywords))[:10])  # Return unique keywords, max 10
    
    def get_scenario_intelligence_context(self, user_message: str) -> str:
        """Get relevant scenario information based on user query"""
        try:
            # Import scenario intelligence
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from scenario_intelligence import ScenarioIntelligence
            
            scenario_intel = ScenarioIntelligence()
            
            # Check if user is asking for specific scenario analysis
            message_lower = user_message.lower()
            
            # Search for scenario names or keywords in the message
            if 'compare' in message_lower:
                # User wants scenario comparison
                scenarios = scenario_intel.get_all_scenarios(limit=5)
                if len(scenarios) >= 2:
                    context = "\nSAVED SCENARIOS FOR COMPARISON:\n"
                    for scenario in scenarios[:3]:
                        context += scenario_intel.format_scenario_for_mantis(scenario, include_analysis=False)
                        context += "\n---\n"
                    return context
            
            elif any(word in message_lower for word in ['scenario', 'saved', 'plan', 'project']):
                # User is asking about scenarios in general
                scenarios = scenario_intel.get_all_scenarios(limit=5)
                if scenarios:
                    context = "\nYOUR SAVED SCENARIOS:\n"
                    context += f"You have {len(scenarios)} saved scenarios. Here are your most recent:\n\n"
                    
                    for scenario in scenarios[:3]:
                        context += f"**{scenario['name']}** (${scenario['total_cost']:,})\n"
                        context += f"- Project: {scenario['project_name']}\n"
                        context += f"- Grant Funding: ${scenario['grant_funding']:,}\n"
                        context += f"- Departments: {scenario['department_count']}\n"
                        context += f"- Created: {scenario['creation_date']}\n\n"
                    
                    return context
            
            # Look for specific scenario names mentioned
            scenarios = scenario_intel.get_all_scenarios()
            for scenario in scenarios:
                if scenario['name'].lower() in message_lower or scenario['project_name'].lower() in message_lower:
                    context = f"\nRELEVANT SCENARIO DATA:\n"
                    context += scenario_intel.format_scenario_for_mantis(scenario, include_analysis=True)
                    return context
            
            return ""
            
        except Exception as e:
            return f"\nNote: Scenario analysis capabilities are temporarily limited: {str(e)}"

# Initialize global Mantis AI instance
if 'mantis_ai' not in st.session_state:
    st.session_state.mantis_ai = MantisAI()