"""
MantisAI Orchestrator - Comprehensive AI Hub with OpenAI GPT-4o Function Calling
Consolidates all GovSight AI capabilities into a unified chat interface
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import asyncio
import logging
import hashlib
import re

# OpenAI import
try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
except ImportError:
    OpenAI = None
    ChatCompletionMessageParam = dict
    ChatCompletionToolParam = dict

# Dual AI Router — Claude + GPT routing and cross-check
try:
    from modules.mantis.dual_ai_router import (
        classify_prompt, get_claude_advisor,
        ROUTE_GPT, ROUTE_CLAUDE, ROUTE_CROSSCHECK,
    )
    DUAL_AI_AVAILABLE = True
except ImportError:
    DUAL_AI_AVAILABLE = False
    ROUTE_GPT = "gpt"
    ROUTE_CLAUDE = "claude"
    ROUTE_CROSSCHECK = "crosscheck"

# Import AI components
from modules.ai_engine.advanced_grant_intelligence import AdvancedGrantIntelligence
from modules.ai_engine.enhanced_anomaly_detection import EnhancedAnomalyDetection
from modules.ai_engine.data_quality_engine import DataQualityEngine
from modules.ai_engine.enhanced_natural_language import EnhancedNaturalLanguage
from modules.bi_sandbox.multi_database_manager import MultiDatabaseManager
from modules.mantis.secure_file_handler import SecureFileHandler
from modules.scenario_planner.scenario_planner import (
    load_scenario_data_optimized,
    run_monte_carlo_optimized
)
from modules.external_data.economic_intelligence import EconomicIntelligence
from modules.audit.audit_logger import get_audit_logger, EventType, Severity

# Import GCP cloud services (graceful degradation)
try:
    from modules.cloud_services.document_archive import DocumentArchive
    from modules.cloud_services.bigquery_connector import BigQueryConnector
    from modules.cloud_services.vertex_ai_connector import VertexAIConnector
except ImportError:
    DocumentArchive = None
    BigQueryConnector = None
    VertexAIConnector = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MantisResult:
    """Unified result envelope for all AI operations"""
    type: str  # 'text', 'table', 'chart', 'cards', 'error'
    title: str
    message: str
    data: Optional[pd.DataFrame] = None
    figure: Optional[go.Figure] = None
    links: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    tool_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        result = {
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'tool_used': self.tool_used,
            'metadata': self.metadata
        }
        
        if self.data is not None:
            result['data'] = self.data.to_dict('records')
        if self.figure:
            result['figure'] = self.figure.to_dict()
        if self.links:
            result['links'] = self.links
            
        return result


class ContextManager:
    """Manages conversation context and caching"""
    
    def __init__(self):
        self.short_term_memory = {}  # Session-based chat history
        self.cache = {}  # Schema info, grant data cache
        self.session_metadata = {}
        self._init_context_db()
    
    def _init_context_db(self):
        """Initialize conversation context database"""
        try:
            conn = sqlite3.connect('nl_conversation_context.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mantis_context (
                    session_id TEXT PRIMARY KEY,
                    context TEXT,
                    schema_cache TEXT,
                    last_updated DATETIME,
                    user_org TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize context DB: {e}")
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieve relevant context for AI"""
        if session_id in self.short_term_memory:
            return self.short_term_memory[session_id]
        
        # Try to load from database
        try:
            conn = sqlite3.connect('nl_conversation_context.db')
            cursor = conn.cursor()
            cursor.execute(
                "SELECT context, schema_cache FROM mantis_context WHERE session_id = ?",
                (session_id,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                context = json.loads(result[0])
                schema_cache = json.loads(result[1]) if result[1] else {}
                self.short_term_memory[session_id] = context
                self.cache[f"{session_id}_schema"] = schema_cache
                return context
        except Exception as e:
            logger.error(f"Failed to load context: {e}")
        
        return {}
    
    def update_context(self, session_id: str, message: str, response: str, metadata: Dict = None):
        """Store conversation history and update context"""
        if session_id not in self.short_term_memory:
            self.short_term_memory[session_id] = {
                'messages': [],
                'metadata': metadata or {},
                'created': datetime.now().isoformat()
            }
        
        self.short_term_memory[session_id]['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        self.short_term_memory[session_id]['messages'].append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Persist to database
        self._save_context(session_id)
    
    def _save_context(self, session_id: str):
        """Persist context to database"""
        try:
            conn = sqlite3.connect('nl_conversation_context.db')
            cursor = conn.cursor()
            
            context = json.dumps(self.short_term_memory.get(session_id, {}))
            schema_cache = json.dumps(self.cache.get(f"{session_id}_schema", {}))
            
            cursor.execute('''
                INSERT OR REPLACE INTO mantis_context
                (session_id, context, schema_cache, last_updated, user_org)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, context, schema_cache, datetime.now(), 
                  self.session_metadata.get(session_id, {}).get('org', 'default')))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save context: {e}")
    
    def clear_session(self, session_id: str):
        """Clear session context"""
        if session_id in self.short_term_memory:
            del self.short_term_memory[session_id]
        if f"{session_id}_schema" in self.cache:
            del self.cache[f"{session_id}_schema"]


class MantisAIOrchestrator:
    """
    Comprehensive AI Orchestrator using OpenAI GPT-4o with Function Calling
    Consolidates all GovSight AI capabilities into a unified interface
    """
    
    def __init__(self, org: str = "cityA"):
        """Initialize the orchestrator with all AI components"""
        self.org = org
        self.context_manager = ContextManager()
        
        # Initialize OpenAI client (GPT-4o — financial analysis + function calling)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not configured")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

        # Initialize Claude advisor (technical questions + cross-check reviewer)
        if DUAL_AI_AVAILABLE:
            try:
                self.claude_advisor = get_claude_advisor()
                if self.claude_advisor.available:
                    logger.info("Claude (Anthropic) advisor ready for technical routing")
                else:
                    logger.info("Claude advisor unavailable — check ANTHROPIC_API_KEY")
            except Exception as e:
                logger.warning(f"Could not initialize Claude advisor: {e}")
                self.claude_advisor = None
        else:
            self.claude_advisor = None
        
        # Initialize the unified data adapter - routes to Caselle API or file imports
        self._init_data_adapter()
        
        # Initialize AI components
        self._init_ai_components()
        
        # Register tools for function calling
        self.tools = self._register_tools()
        
        # Security settings
        self.max_query_length = 10000
        self.audit_log = []
    
    def _init_data_adapter(self):
        """Initialize the unified data adapter for automatic data source routing"""
        try:
            from modules.data_adapter.unified_adapter import get_adapter
            from modules.data_adapter.config import DataSourceType
            self.data_adapter = get_adapter("default")
            health = self.data_adapter.health_check()
            self.active_data_source = health.get('source_type', 'file_import')
            caselle_health = health.get('caselle_api', {})
            self.caselle_active = caselle_health.get('status') == 'active' and caselle_health.get('configured', False)
            archive_health = health.get('archive', {})
            self.archive_records = archive_health.get('gl_records', 0)
            logger.info(f"Data adapter initialized - source: {self.active_data_source}, caselle_active: {self.caselle_active}, archive_records: {self.archive_records}")
        except Exception as e:
            logger.warning(f"Data adapter unavailable, falling back to direct DB access: {e}")
            self.data_adapter = None
            self.active_data_source = 'legacy_database'
            self.caselle_active = False
            self.archive_records = 0
    
    def _init_ai_components(self):
        """Initialize all AI component instances"""
        try:
            self.grant_intelligence = AdvancedGrantIntelligence()
        except Exception as e:
            logger.warning(f"Grant intelligence unavailable: {e}")
            self.grant_intelligence = None
        
        try:
            self.anomaly_detection = EnhancedAnomalyDetection()
        except Exception as e:
            logger.warning(f"Anomaly detection unavailable: {e}")
            self.anomaly_detection = None
        
        try:
            self.data_quality = DataQualityEngine()
        except Exception as e:
            logger.warning(f"Data quality engine unavailable: {e}")
            self.data_quality = None
        
        try:
            self.natural_language = EnhancedNaturalLanguage()
        except Exception as e:
            logger.warning(f"Natural language engine unavailable: {e}")
            self.natural_language = None
        
        try:
            self.db_manager = MultiDatabaseManager()
        except Exception as e:
            logger.warning(f"Database manager unavailable: {e}")
            self.db_manager = None
        
        try:
            self.file_handler = SecureFileHandler()
        except Exception as e:
            logger.warning(f"File handler unavailable: {e}")
            self.file_handler = None
        
        try:
            self.economic_intelligence = EconomicIntelligence()
        except Exception as e:
            logger.warning(f"Economic intelligence unavailable: {e}")
            self.economic_intelligence = None
        
        # Initialize GCP cloud services (graceful degradation)
        if DocumentArchive:
            try:
                self.document_archive = DocumentArchive()
            except Exception as e:
                logger.warning(f"Document archive unavailable: {e}")
                self.document_archive = None
        else:
            self.document_archive = None
        
        if BigQueryConnector:
            try:
                self.bigquery = BigQueryConnector()
            except Exception as e:
                logger.warning(f"BigQuery connector unavailable: {e}")
                self.bigquery = None
        else:
            self.bigquery = None
        
        if VertexAIConnector:
            try:
                self.vertex_ai = VertexAIConnector()
            except Exception as e:
                logger.warning(f"Vertex AI connector unavailable: {e}")
                self.vertex_ai = None
        else:
            self.vertex_ai = None
        
        # Initialize audit logger
        try:
            self.audit_logger = get_audit_logger()
        except Exception as e:
            logger.warning(f"Audit logger unavailable: {e}")
            self.audit_logger = None
    
    def _register_tools(self) -> List[Dict[str, Any]]:
        """Register all available tools for OpenAI function calling"""
        tools = []
        
        # Grant Intelligence Tools
        if self.grant_intelligence:
            tools.append({
                "type": "function",
                "function": {
                    "name": "search_grants",
                    "description": "Search for federal and state grant opportunities based on criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for grants (e.g., 'infrastructure grants', 'public safety funding')"
                            },
                            "agency": {
                                "type": "string",
                                "description": "Specific federal agency (e.g., 'FEMA', 'DOT', 'EPA')",
                                "enum": ["ALL", "FEMA", "DOT", "EPA", "HUD", "USDA", "DOJ", "CDC"]
                            },
                            "min_amount": {
                                "type": "number",
                                "description": "Minimum grant amount"
                            },
                            "max_amount": {
                                "type": "number",
                                "description": "Maximum grant amount"
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
            
            tools.append({
                "type": "function",
                "function": {
                    "name": "analyze_grant_eligibility",
                    "description": "Analyze eligibility for a specific grant opportunity",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "grant_id": {
                                "type": "string",
                                "description": "Grant identifier"
                            },
                            "organization_profile": {
                                "type": "object",
                                "description": "Organization details for eligibility assessment"
                            }
                        },
                        "required": ["grant_id"]
                    }
                }
            })
        
        # Anomaly Detection Tools
        if self.anomaly_detection:
            tools.append({
                "type": "function",
                "function": {
                    "name": "detect_anomalies",
                    "description": "Detect anomalies in financial transactions or budget data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data_type": {
                                "type": "string",
                                "description": "Type of data to analyze",
                                "enum": ["transactions", "budget", "vendors", "all"]
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Anomaly detection sensitivity (0.01 to 0.1)",
                                "default": 0.05
                            },
                            "time_period": {
                                "type": "string",
                                "description": "Time period for analysis",
                                "enum": ["current_month", "last_month", "current_quarter", "current_year", "all"]
                            }
                        },
                        "required": ["data_type"]
                    }
                }
            })
        
        # Data Quality Tools
        if self.data_quality:
            tools.append({
                "type": "function",
                "function": {
                    "name": "assess_data_quality",
                    "description": "Assess the quality of financial data and identify issues",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Database table to assess"
                            },
                            "auto_fix": {
                                "type": "boolean",
                                "description": "Automatically fix identified issues",
                                "default": False
                            }
                        },
                        "required": ["table_name"]
                    }
                }
            })
        
        # Natural Language Query Tools
        if self.natural_language:
            tools.append({
                "type": "function",
                "function": {
                    "name": "query_financial_data",
                    "description": "Query financial data using natural language",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query about financial data"
                            },
                            "visualization": {
                                "type": "boolean",
                                "description": "Generate visualization for results",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                }
            })
        
        # Database Query Tools
        if self.db_manager:
            tools.append({
                "type": "function",
                "function": {
                    "name": "query_database",
                    "description": "Execute a safe, read-only database query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "database": {
                                "type": "string",
                                "description": "Target database",
                                "enum": ["gl_primary", "payroll", "permits", "utilities", "assets"]
                            },
                            "query_description": {
                                "type": "string",
                                "description": "Description of what data to retrieve (NOT raw SQL)"
                            }
                        },
                        "required": ["database", "query_description"]
                    }
                }
            })
        
        # File Processing Tools
        if self.file_handler:
            tools.append({
                "type": "function",
                "function": {
                    "name": "analyze_uploaded_file",
                    "description": "Analyze content from uploaded PDF or CSV files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_name": {
                                "type": "string",
                                "description": "Name of the uploaded file"
                            },
                            "analysis_type": {
                                "type": "string",
                                "description": "Type of analysis to perform",
                                "enum": ["summary", "extract_data", "validate", "compare"]
                            }
                        },
                        "required": ["file_name", "analysis_type"]
                    }
                }
            })
        
        # Scenario Analysis Tools
        tools.append({
            "type": "function",
            "function": {
                "name": "analyze_scenario",
                "description": "Perform economic scenario analysis with Monte Carlo simulation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scenario_name": {
                            "type": "string",
                            "description": "Name of the scenario"
                        },
                        "base_amount": {
                            "type": "number",
                            "description": "Base amount for simulation"
                        },
                        "volatility": {
                            "type": "number",
                            "description": "Volatility factor (0.1 to 0.5)",
                            "default": 0.2
                        },
                        "simulations": {
                            "type": "integer",
                            "description": "Number of simulations",
                            "default": 1000
                        }
                    },
                    "required": ["scenario_name", "base_amount"]
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "check_gasb_compliance",
                "description": "Check GASB (Governmental Accounting Standards Board) compliance for fund usage, budget reallocations, or financial reporting questions. Returns relevant GASB standards, fund eligibility, and compliance guidance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The compliance question or scenario to evaluate"
                        },
                        "fund_code": {
                            "type": "string",
                            "description": "Specific fund code to check compliance for (optional)"
                        },
                        "check_type": {
                            "type": "string",
                            "description": "Type of compliance check",
                            "enum": ["reallocation", "fund_balance", "reporting", "general"]
                        }
                    },
                    "required": ["query"]
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "get_fund_policy",
                "description": "Get the current fund classification policy including which funds are eligible for budget reallocation and which are restricted. Uses classifications set in the Admin Panel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fund_code": {
                            "type": "string",
                            "description": "Specific fund code to check (optional - omit for full policy)"
                        }
                    }
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "validate_reallocation",
                "description": "Validate whether a proposed budget reallocation between funds complies with GASB 54 and the municipality's fund classification policy. Checks source funds for restrictions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_funds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of fund codes to reallocate FROM"
                        },
                        "target_fund": {
                            "type": "string",
                            "description": "Fund code to reallocate TO (optional)"
                        }
                    },
                    "required": ["source_funds"]
                }
            }
        })

        # Economic Intelligence Tools
        if self.economic_intelligence:
            tools.append({
                "type": "function",
                "function": {
                    "name": "get_economic_context",
                    "description": "Get comprehensive economic context including indicators, forecasts, and revenue impact for municipal planning",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "include_forecasts": {
                                "type": "boolean",
                                "description": "Include economic forecasts",
                                "default": True
                            }
                        }
                    }
                }
            })
            
            tools.append({
                "type": "function",
                "function": {
                    "name": "forecast_revenue",
                    "description": "Forecast municipal revenue using economic indicators like unemployment, GDP, and inflation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "revenue_type": {
                                "type": "string",
                                "description": "Type of revenue to forecast",
                                "enum": ["sales_tax", "property_tax", "total_revenue"]
                            },
                            "forecast_months": {
                                "type": "integer",
                                "description": "Number of months to forecast",
                                "default": 12
                            }
                        },
                        "required": ["revenue_type"]
                    }
                }
            })
            
            tools.append({
                "type": "function",
                "function": {
                    "name": "analyze_economic_scenarios",
                    "description": "Analyze multiple economic scenarios (optimistic, base, pessimistic) and their revenue impact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_revenue": {
                                "type": "number",
                                "description": "Current annual revenue for scenario analysis"
                            }
                        },
                        "required": ["base_revenue"]
                    }
                }
            })
        
        # Cloud Document Archive Tools (only register if GCP configured)
        if (self.document_archive and 
            hasattr(self.document_archive, 'connector') and 
            self.document_archive.connector and
            hasattr(self.document_archive.connector, 'is_configured') and
            self.document_archive.connector.is_configured()):
            tools.append({
                "type": "function",
                "function": {
                    "name": "search_cloud_documents",
                    "description": "Search archived financial documents in Google Cloud Storage (reports, exports, backups)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "archive_type": {
                                "type": "string",
                                "description": "Type of archive to search",
                                "enum": ["reports", "exports", "backups", "documents"]
                            },
                            "search_prefix": {
                                "type": "string",
                                "description": "File name prefix or pattern to search for"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date for search (YYYY-MM-DD format)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date for search (YYYY-MM-DD format)"
                            }
                        },
                        "required": ["archive_type"]
                    }
                }
            })
        
        # BigQuery Analytics Tools (only register if GCP configured)
        if (self.bigquery and 
            hasattr(self.bigquery, 'is_configured') and
            self.bigquery.is_configured()):
            tools.append({
                "type": "function",
                "function": {
                    "name": "query_bigquery_analytics",
                    "description": "Query BigQuery for historical financial analytics and trends",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "analysis_type": {
                                "type": "string",
                                "description": "Type of analytics to retrieve",
                                "enum": ["revenue_trends", "expense_analysis", "compliance_report", "custom"]
                            },
                            "time_period": {
                                "type": "string",
                                "description": "Time period for analysis",
                                "enum": ["last_month", "last_quarter", "last_year", "year_to_date", "all"]
                            },
                            "custom_query": {
                                "type": "string",
                                "description": "Custom SQL query (only for custom analysis_type)"
                            }
                        },
                        "required": ["analysis_type"]
                    }
                }
            })
        
        # Vertex AI Model Deployment Tools (only register if GCP configured)
        if (self.vertex_ai and 
            hasattr(self.vertex_ai, 'is_configured') and
            self.vertex_ai.is_configured()):
            tools.append({
                "type": "function",
                "function": {
                    "name": "deploy_ai_model",
                    "description": "Deploy an AI/ML model to Vertex AI for predictions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model_name": {
                                "type": "string",
                                "description": "Display name for the model"
                            },
                            "model_uri": {
                                "type": "string",
                                "description": "GCS URI containing model artifacts (gs://bucket/path)"
                            },
                            "container_image": {
                                "type": "string",
                                "description": "Docker container image for serving (e.g., us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-0:latest)"
                            }
                        },
                        "required": ["model_name", "model_uri", "container_image"]
                    }
                }
            })
            
            tools.append({
                "type": "function",
                "function": {
                    "name": "list_ai_models",
                    "description": "List all deployed AI/ML models in Vertex AI",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": "Optional filter (e.g., 'display_name=\"revenue_model\"')"
                            }
                        }
                    }
                }
            })
            
            tools.append({
                "type": "function",
                "function": {
                    "name": "get_model_prediction",
                    "description": "Get predictions from a deployed AI model",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "endpoint_id": {
                                "type": "string",
                                "description": "Vertex AI endpoint ID or resource name"
                            },
                            "input_data": {
                                "type": "object",
                                "description": "Input data for prediction as key-value pairs"
                            }
                        },
                        "required": ["endpoint_id", "input_data"]
                    }
                }
            })
        
        return tools
    
    async def process_message(self, message: str, context: Dict[str, Any] = None, 
                             session_id: str = None) -> MantisResult:
        """
        Process user message and route to the optimal AI model.

        Routing logic (see modules/mantis/dual_ai_router.py for full details):
        - ROUTE_CLAUDE:      Technical / coding question  → Anthropic Claude 3.5 Sonnet
        - ROUTE_CROSSCHECK:  Validation requested        → Both models; secondary reviews primary
        - ROUTE_GPT:         Financial / data question   → GPT-4o with function calling tools
        
        Args:
            message: User input message
            context: Additional context (uploaded files, session data)
            session_id: Session identifier for context management
            
        Returns:
            MantisResult with structured response
        """
        # Security: Validate and sanitize input
        if len(message) > self.max_query_length:
            return MantisResult(
                type="error",
                title="Input Too Long",
                message=f"Please limit your message to {self.max_query_length} characters.",
                tool_used="security_check"
            )
        
        message = self._sanitize_input(message)
        
        # Log for audit
        self._log_audit({
            'action': 'process_message',
            'session_id': session_id,
            'message_length': len(message),
            'timestamp': datetime.now().isoformat()
        })

        # --- Dual AI Routing ---
        # Classify the prompt before deciding which model to call.
        # Claude handles technical questions; GPT handles financial/data queries.
        # Cross-check mode runs both and has each review the other.
        if DUAL_AI_AVAILABLE and self.claude_advisor and self.claude_advisor.available:
            route, route_reason, tech_score, fin_score = classify_prompt(message)
            logger.info(f"Dual AI route: {route} | {route_reason}")

            if route == ROUTE_CLAUDE:
                return await self._handle_claude_route(message, route_reason)

            if route == ROUTE_CROSSCHECK:
                # For cross-check we need at least one API client
                if self.client:
                    return await self._handle_crosscheck_route(message, context, session_id, tech_score, fin_score)
                # Fall through to GPT if we can still answer
        
        # Handle missing OpenAI API key (GPT path)
        if not self.client:
            # Try Claude as fallback for GPT if available
            if self.claude_advisor and self.claude_advisor.available:
                return await self._handle_claude_route(
                    message, "GPT unavailable — using Claude as fallback"
                )
            return await self._fallback_processing(message, context)
        
        # Get conversation context
        if session_id:
            conversation_context = self.context_manager.get_context(session_id)
        else:
            conversation_context = {}
        
        # Build messages for GPT-4o
        messages = self._build_messages(message, context, conversation_context)
        
        try:
            # Call GPT-4o with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2000
            )
            
            # Process the response
            result = await self._process_gpt_response(response, context, session_id, message)
            
            # Update context
            if session_id:
                self.context_manager.update_context(
                    session_id, message, result.message, 
                    {'tool_used': result.tool_used}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"GPT-4o processing error: {e}")
            return await self._fallback_processing(message, context)
    
    # ------------------------------------------------------------------
    # Dual AI route handlers
    # ------------------------------------------------------------------

    async def _handle_claude_route(self, message: str, reason: str) -> MantisResult:
        """
        Handle a message routed to Claude (Anthropic).

        Claude excels at code, debugging, technical explanations, and
        GovSight platform configuration.  It does NOT have access to the
        function-calling tools — data queries still go through GPT-4o.
        """
        try:
            response_text = self.claude_advisor.ask(message)
            return MantisResult(
                type="text",
                title="MantisAI — Technical Advisor",
                message=response_text,
                tool_used="claude-3-5-sonnet",
                metadata={"model": "claude-3-5-sonnet-20241022", "routing_reason": reason},
            )
        except Exception as e:
            logger.error(f"Claude route failed: {e}")
            # Gracefully degrade: if Claude fails and GPT is available, use GPT
            if self.client:
                logger.info("Falling back to GPT-4o after Claude error")
                conversation_context = {}
                messages = self._build_messages(message, {}, conversation_context)
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        tools=self.tools,
                        tool_choice="auto",
                        temperature=0.7,
                        max_tokens=2000,
                    )
                    return await self._process_gpt_response(response, {}, None, message)
                except Exception as gpt_err:
                    logger.error(f"GPT fallback also failed: {gpt_err}")
            return MantisResult(
                type="error",
                title="AI Unavailable",
                message=f"Could not get a response from either AI model. Error: {e}",
                tool_used="error",
            )

    async def _handle_crosscheck_route(
        self,
        message: str,
        context: Dict,
        session_id: str,
        tech_score: int,
        fin_score: int,
    ) -> MantisResult:
        """
        Cross-check mode: both Claude and GPT-4o answer the question.
        The model with the weaker signal reviews the stronger model's answer.

        WHY CROSS-CHECK:
        - Financial decisions in municipal government are high-stakes.
        - Having both models independently reason about a question and then
          review each other catches errors, hallucinations, and blind spots.
        - The user sees: Primary Analysis → Peer Review → Combined Verdict.
        """
        # Determine primary model based on scores (or default to GPT for data access)
        if tech_score > fin_score:
            primary = "claude"
            reviewer = "gpt"
        else:
            primary = "gpt"
            reviewer = "claude"

        primary_answer = ""
        primary_label = ""
        review_text = ""

        # Step 1: Primary model answers
        if primary == "claude" and self.claude_advisor and self.claude_advisor.available:
            try:
                primary_answer = self.claude_advisor.ask(message)
                primary_label = "Claude 3.5 Sonnet (Technical Analysis)"
            except Exception as e:
                logger.error(f"Cross-check primary (Claude) failed: {e}")
                primary = "gpt"  # Flip to GPT
                reviewer = "claude"

        if primary == "gpt" or not primary_answer:
            try:
                conversation_context = self.context_manager.get_context(session_id) if session_id else {}
                messages = self._build_messages(message, context, conversation_context)
                gpt_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=2000,
                )
                gpt_result = await self._process_gpt_response(gpt_response, context, session_id, message)
                primary_answer = gpt_result.message
                primary_label = "GPT-4o (Financial Analysis)"
            except Exception as e:
                logger.error(f"Cross-check primary (GPT) failed: {e}")
                return MantisResult(
                    type="error",
                    title="Cross-Check Failed",
                    message=f"Could not complete cross-check: {e}",
                    tool_used="error",
                )

        # Step 2: Secondary model reviews
        if reviewer == "claude" and self.claude_advisor and self.claude_advisor.available:
            try:
                review_text = self.claude_advisor.review(message, primary_label, primary_answer)
                reviewer_label = "Claude 3.5 Sonnet"
            except Exception as e:
                logger.warning(f"Cross-check reviewer (Claude) failed: {e}")
                review_text = "Review unavailable."
                reviewer_label = "Claude 3.5 Sonnet (unavailable)"
        elif reviewer == "gpt" and self.client:
            try:
                from modules.mantis.dual_ai_router import _crosscheck_review_prompt
                review_prompt = _crosscheck_review_prompt(message, primary_label, primary_answer)
                gpt_review = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a precise, critical reviewer. Be direct and honest."},
                        {"role": "user", "content": review_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=800,
                )
                review_text = gpt_review.choices[0].message.content or "Review unavailable."
                reviewer_label = "GPT-4o"
            except Exception as e:
                logger.warning(f"Cross-check reviewer (GPT) failed: {e}")
                review_text = "Review unavailable."
                reviewer_label = "GPT-4o (unavailable)"
        else:
            review_text = "Second reviewer unavailable."
            reviewer_label = "N/A"

        # Step 3: Compose combined response
        combined = (
            f"**Primary Analysis ({primary_label})**\n\n"
            f"{primary_answer}\n\n"
            f"---\n\n"
            f"**Peer Review ({reviewer_label})**\n\n"
            f"{review_text}"
        )

        return MantisResult(
            type="text",
            title="MantisAI — Cross-Check Response",
            message=combined,
            tool_used="dual-ai-crosscheck",
            metadata={
                "primary_model": primary_label,
                "reviewer_model": reviewer_label,
                "routing_reason": "Cross-check requested by user",
            },
        )

    def _build_messages(self, message: str, context: Dict, conversation_context: Dict) -> List[ChatCompletionMessageParam]:
        """Build message array for GPT-4o with real data context"""
        
        data_context = self._get_data_context_summary()
        
        fund_policy_context = self._get_fund_policy_context()

        system_content = f"""You are MantisAI, a knowledgeable financial intelligence assistant for GovSight - a municipal government financial management platform.

YOUR ROLE:
- You are a CPA-trained municipal finance analyst and a helpful support agent for the GovSight platform.
- You provide actionable financial insights, budget analysis, grant guidance, and platform support.
- You speak in a professional, clear manner and always give specific, data-driven answers when possible.
- You understand municipal accounting (GAAP/GASB standards), fund accounting, budgeting cycles, and government finance best practices.

DATA PIPELINE STATUS:
The system routes through a unified data adapter that automatically uses the active data source.
When a Caselle ERP API is configured, data comes from the live API. Otherwise, data comes from
file imports (CSV/PDF) archived into the report database, or from legacy SQLite databases.

AVAILABLE DATA:
{data_context}

FUND CLASSIFICATION POLICY (GASB 54):
{fund_policy_context}

CRITICAL COMPLIANCE RULES:
- ALWAYS check fund classifications before recommending budget reallocations or fund transfers.
- Restricted, Capital, Debt Service, and Grant funds are BLOCKED from reallocation unless explicitly approved.
- Only Unrestricted funds may be used as sources for budget reallocation.
- Use the check_gasb_compliance tool when users ask about compliance, fund restrictions, or GASB standards.
- Use the validate_reallocation tool before recommending any interfund transfer.
- If a user asks to move money from a restricted fund, WARN them and explain the GASB 54 restriction.
- Fund classifications are managed in the Admin Panel's Fund Classification Manager tab.

TOOLS YOU CAN USE:
- query_database: Query financial data through the active data pipeline (Caselle API, file imports, or legacy databases)
- query_financial_data: Natural language queries against financial data with automatic visualization
- search_grants: Search federal/state grant opportunities (FEMA, DOT, EPA, HUD, USDA, DOJ)
- analyze_grant_eligibility: Analyze eligibility for specific grants
- detect_anomalies: Find unusual patterns in financial transactions or budget data
- assess_data_quality: Check data completeness and accuracy
- analyze_scenario: Run Monte Carlo simulations for budget scenarios
- get_economic_context: Get current economic indicators and their municipal impact
- forecast_revenue: Project future revenue using economic indicators
- analyze_economic_scenarios: Model optimistic/base/pessimistic economic outcomes
- analyze_uploaded_file: Process uploaded PDF or CSV files
- check_gasb_compliance: Check GASB compliance for fund usage, reallocations, or reporting
- get_fund_policy: Get current fund classification policy and reallocation eligibility
- validate_reallocation: Validate proposed budget reallocations against GASB 54 fund restrictions

PLATFORM SUPPORT KNOWLEDGE:
GovSight has 3 modules:
1. Navi (Navigation & Planning): Scenario Planner, BI Sandbox, Position-Based Budgeting, Investment Optimizer, Legislative Impact Analysis
2. Mantis (AI Intelligence Hub): This chat interface, grant search, document analysis, anomaly detection, GASB compliance
3. Vatica (Document & Collaboration): Document management, GL drilldowns, regulatory compliance

BEHAVIOR GUIDELINES:
- When users ask about their data, USE the query tools to get real answers - do not guess or use hypotheticals
- When users ask how to do something in GovSight, provide step-by-step guidance
- When users report issues, troubleshoot systematically
- Always give specific dollar amounts, percentages, and dates when the data supports it
- For budget questions, consider fund accounting structure (General Fund, Enterprise Funds, etc.)
- For any reallocation or fund transfer question, ALWAYS check fund policy first
- Keep responses focused and practical - municipal staff are busy professionals
- Data is processed securely and locally"""

        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history (last 10 messages for context)
        if conversation_context and 'messages' in conversation_context:
            recent_messages = conversation_context['messages'][-10:]
            for msg in recent_messages:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        # Add file context if available
        if context and 'uploaded_files' in context:
            file_summary = self._summarize_file_context(context['uploaded_files'])
            messages.append({
                "role": "system",
                "content": f"User has uploaded files: {file_summary}"
            })
        
        # Add the current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
    
    async def _process_gpt_response(self, response, context: Dict, session_id: str, original_message: str = "") -> MantisResult:
        """Process GPT-4o response and handle function calls"""
        message = response.choices[0].message
        
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            result = await self._execute_tool(function_name, function_args, context)
            
            if self.client:
                try:
                    result_summary = result.to_dict()
                    result_text = json.dumps(result_summary, default=str)
                    if len(result_text) > 8000:
                        result_text = result_text[:8000] + "...(truncated)"
                    
                    follow_up_messages = [
                        {"role": "system", "content": "You are MantisAI, a municipal financial intelligence assistant. Interpret the tool results and provide a clear, helpful response to the user's question. Be specific with numbers and actionable insights. Never use emojis."},
                        {"role": "user", "content": original_message},
                        {"role": "assistant", "content": None, "tool_calls": [
                            {"id": tool_call.id, "type": "function", "function": {"name": function_name, "arguments": tool_call.function.arguments}}
                        ]},
                        {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
                    ]
                    
                    final_response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=follow_up_messages,
                        temperature=0.7,
                        max_tokens=1500
                    )
                    
                    final_content = final_response.choices[0].message.content
                    if final_content:
                        result.message = final_content
                except Exception as e:
                    logger.error(f"Follow-up response error: {e}")
            
            return result
        
        # Direct response without function calling
        return MantisResult(
            type="text",
            title="AI Response",
            message=message.content,
            tool_used="direct_response"
        )
    
    async def _execute_tool(self, tool_name: str, args: Dict, context: Dict) -> MantisResult:
        """Execute a specific tool and return results"""
        try:
            if tool_name == "search_grants":
                return await self._search_grants_adapter(**args)
            
            elif tool_name == "analyze_grant_eligibility":
                return await self._analyze_grant_eligibility_adapter(**args)
            
            elif tool_name == "detect_anomalies":
                return await self._detect_anomalies_adapter(**args)
            
            elif tool_name == "assess_data_quality":
                return await self._assess_data_quality_adapter(**args)
            
            elif tool_name == "query_financial_data":
                return await self._query_financial_data_adapter(**args)
            
            elif tool_name == "query_database":
                return await self._query_database_adapter(**args)
            
            elif tool_name == "analyze_uploaded_file":
                return await self._analyze_file_adapter(context=context, **args)
            
            elif tool_name == "analyze_scenario":
                return await self._analyze_scenario_adapter(**args)
            
            elif tool_name == "get_economic_context":
                return await self._get_economic_context_adapter(**args)
            
            elif tool_name == "forecast_revenue":
                return await self._forecast_revenue_adapter(**args)
            
            elif tool_name == "analyze_economic_scenarios":
                return await self._analyze_economic_scenarios_adapter(**args)
            
            elif tool_name == "search_cloud_documents":
                return await self._search_cloud_documents_adapter(**args)
            
            elif tool_name == "query_bigquery_analytics":
                return await self._query_bigquery_analytics_adapter(**args)
            
            elif tool_name == "check_gasb_compliance":
                return await self._check_gasb_compliance_adapter(**args)

            elif tool_name == "get_fund_policy":
                return await self._get_fund_policy_adapter(**args)

            elif tool_name == "validate_reallocation":
                return await self._validate_reallocation_adapter(**args)

            elif tool_name == "deploy_ai_model":
                return await self._deploy_ai_model_adapter(**args)
            
            elif tool_name == "list_ai_models":
                return await self._list_ai_models_adapter(**args)
            
            elif tool_name == "get_model_prediction":
                return await self._get_model_prediction_adapter(**args)
            
            else:
                return MantisResult(
                    type="error",
                    title="Unknown Tool",
                    message=f"Tool '{tool_name}' is not recognized",
                    tool_used=tool_name
                )
                
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return MantisResult(
                type="error",
                title="Tool Execution Error",
                message=f"Error executing {tool_name}: {str(e)}",
                tool_used=tool_name
            )
    
    # Tool Adapter Methods
    
    async def _search_grants_adapter(self, query: str, agency: str = "ALL", 
                                    min_amount: float = None, max_amount: float = None) -> MantisResult:
        """Adapter for grant search functionality"""
        if not self.grant_intelligence:
            return MantisResult(
                type="error",
                title="Grant Search Unavailable",
                message="Grant intelligence module is not available",
                tool_used="search_grants"
            )
        
        try:
            # Get municipal profile for matching
            municipal_profile = {
                'type': 'municipality',
                'population': 50000,
                'budget': 100000000,
                'departments': ['Police', 'Fire', 'Public Works', 'Parks'],
                'priorities': [query] if query else []
            }
            
            # Search for grants using the correct method
            # The method expects municipal_profile and priority_areas
            priority_areas = []
            if query:
                priority_areas.append(query)
            if agency and agency != "ALL":
                priority_areas.append(agency)
                
            matching_grants = self.grant_intelligence.intelligent_grant_matching(
                municipal_profile=municipal_profile,
                priority_areas=priority_areas if priority_areas else None
            )
            
            # Filter by amounts if specified
            if min_amount or max_amount:
                filtered_grants = []
                for grant in matching_grants:
                    if min_amount and grant.min_amount < min_amount:
                        continue
                    if max_amount and grant.max_amount > max_amount:
                        continue
                    filtered_grants.append(grant)
                matching_grants = filtered_grants
            
            matching_result = {'matching_grants': matching_grants}
            
            grants = matching_result.get('matching_grants', [])
            
            if not grants:
                return MantisResult(
                    type="text",
                    title="No Grants Found",
                    message=f"No grants found matching '{query}'",
                    tool_used="search_grants"
                )
            
            # Format results as DataFrame
            df = pd.DataFrame([{
                'Title': g.title,
                'Agency': g.agency,
                'Amount': f"${g.min_amount:,.0f} - ${g.max_amount:,.0f}",
                'Deadline': g.deadline.strftime('%Y-%m-%d'),
                'Match Required': 'Yes' if g.match_required else 'No',
                'Eligibility Score': f"{g.eligibility_score:.1%}"
            } for g in grants[:10]])  # Limit to top 10
            
            return MantisResult(
                type="table",
                title=f"Grant Opportunities for '{query}'",
                message=f"Found {len(grants)} matching grants. Showing top {min(10, len(grants))}.",
                data=df,
                tool_used="search_grants",
                metadata={'total_grants': len(grants)}
            )
            
        except Exception as e:
            logger.error(f"Grant search error: {e}")
            return MantisResult(
                type="error",
                title="Grant Search Error",
                message=str(e),
                tool_used="search_grants"
            )
    
    async def _detect_anomalies_adapter(self, data_type: str, threshold: float = 0.05,
                                       time_period: str = "current_month") -> MantisResult:
        """Adapter for anomaly detection - routes through data adapter first, falls back to legacy DBs"""
        if not self.anomaly_detection:
            return MantisResult(
                type="error",
                title="Anomaly Detection Unavailable",
                message="Anomaly detection module is not available",
                tool_used="detect_anomalies"
            )
        
        try:
            real_data = None
            data_source = "unknown"
            
            real_data, data_source = self._load_anomaly_data_from_adapter(data_type)
            
            if real_data is None or real_data.empty:
                real_data, data_source = self._load_anomaly_data_from_legacy(data_type)
            
            if real_data is None or real_data.empty:
                return MantisResult(
                    type="text",
                    title="Anomaly Detection",
                    message=f"No {data_type} data available for anomaly detection. Please ensure data is loaded in the system.",
                    tool_used="detect_anomalies"
                )
            
            results = self.anomaly_detection.comprehensive_anomaly_analysis(real_data)
            
            anomalies_found = sum(
                len(layer.get('anomalies', [])) 
                for layer in results.get('anomaly_layers', {}).values()
            )
            
            if anomalies_found > 0:
                numeric_cols = real_data.select_dtypes(include=[np.number]).columns
                y_col = 'Amount' if 'Amount' in real_data.columns else (numeric_cols[0] if len(numeric_cols) > 0 else None)
                x_col = 'transaction_date' if 'transaction_date' in real_data.columns else ('Month' if 'Month' in real_data.columns else real_data.columns[0])
                color_col = 'Department' if 'Department' in real_data.columns else None
                
                if y_col:
                    fig = px.scatter(
                        real_data, x=x_col, y=y_col, 
                        color=color_col,
                        title=f'Anomaly Detection: {data_source}',
                        labels={y_col: 'Amount ($)'}
                    )
                else:
                    fig = go.Figure()
                
                return MantisResult(
                    type="chart",
                    title="Anomaly Detection Results",
                    message=f"Analyzed {len(real_data)} records from {data_source}. Found {anomalies_found} potential anomalies in {data_type} data ({time_period}).",
                    figure=fig,
                    data=real_data.head(20),
                    tool_used="detect_anomalies",
                    metadata={'anomalies_found': anomalies_found, 'records_analyzed': len(real_data), 'data_source': data_source}
                )
            else:
                return MantisResult(
                    type="text",
                    title="No Anomalies Detected",
                    message=f"Analyzed {len(real_data)} records from {data_source}. No significant anomalies found in {data_type} data for {time_period}.",
                    tool_used="detect_anomalies"
                )
                
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return MantisResult(
                type="error",
                title="Anomaly Detection Error",
                message=str(e),
                tool_used="detect_anomalies"
            )
    
    def _load_anomaly_data_from_adapter(self, data_type: str):
        """Try to load data for anomaly detection from the UnifiedDataAdapter"""
        if not self.data_adapter:
            return None, "no adapter"
        
        try:
            if data_type in ("budget", "all"):
                import datetime as dt
                for year in [dt.datetime.now().year, dt.datetime.now().year - 1]:
                    data = self.data_adapter.get_budget_data(fiscal_year=year)
                    if data:
                        df = pd.DataFrame(data)
                        source = f"{'Caselle API' if self.caselle_active else 'Data Adapter'} - Budget FY{year}"
                        return df, source
            
            if data_type in ("transactions", "vendors", "all"):
                data = self.data_adapter.get_general_ledger()
                if data:
                    df = pd.DataFrame(data)
                    if 'debit' in df.columns and 'credit' in df.columns:
                        df['Amount'] = df['debit'].fillna(0).astype(float) - df['credit'].fillna(0).astype(float)
                    source = f"{'Caselle API' if self.caselle_active else 'Data Adapter'} - General Ledger"
                    return df, source
            
            if data_type == "payroll":
                data = self.data_adapter.get_payroll_data()
                if data:
                    df = pd.DataFrame(data)
                    source = f"{'Caselle API' if self.caselle_active else 'Data Adapter'} - Payroll"
                    return df, source
        except Exception as e:
            logger.debug(f"Could not load anomaly data from adapter: {e}")
        
        return None, "adapter returned no data"
    
    def _load_anomaly_data_from_legacy(self, data_type: str):
        """Fallback: load data for anomaly detection from legacy SQLite databases"""
        try:
            from modules.database.db_connection import get_db_path_for_org
            db_path = get_db_path_for_org(self.org)
            conn = sqlite3.connect(db_path)
            
            try:
                if data_type in ("budget", "all"):
                    real_data = pd.read_sql_query(
                        "SELECT Department, Fund, FiscalYear, AccountCode, AccountName, "
                        "Budget, Actual, PercentUsed, Organization "
                        "FROM DepartmentPerformance ORDER BY FiscalYear", conn
                    )
                    if not real_data.empty:
                        return real_data, "Legacy DB - DepartmentPerformance"
                
                if data_type in ("transactions", "vendors", "all"):
                    real_data = pd.read_sql_query(
                        "SELECT transaction_id, account_id, description, debit, credit, transaction_date "
                        "FROM general_ledger ORDER BY transaction_date", conn
                    )
                    if not real_data.empty:
                        real_data['Amount'] = real_data['debit'] - real_data['credit']
                        return real_data, "Legacy DB - general_ledger"
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Could not load data from legacy DB for anomaly detection: {e}")
        
        return None, "no legacy data"
    
    async def _query_database_adapter(self, database: str, query_description: str) -> MantisResult:
        """
        Database query adapter that routes through the UnifiedDataAdapter.
        Automatically uses Caselle API if active, otherwise file imports/archive,
        with fallback to direct SQLite access for legacy databases.
        """
        try:
            import streamlit as st
            user_id = st.session_state.get('username', 'anonymous')
            logger.info(f"Database query - User: {user_id}, Database: {database}, Query: {query_description[:100]}...")
            
            sanitized_data = pd.DataFrame()
            rows_accessed = 0
            data_source_used = "unknown"
            
            adapter_data = self._try_adapter_query(database, query_description)
            if adapter_data is not None and not adapter_data.empty:
                sanitized_data = adapter_data
                rows_accessed = len(sanitized_data)
                data_source_used = f"{'Caselle API' if self.caselle_active else 'Data Adapter'}"
            else:
                conn = self._get_legacy_db_connection(database)
                if conn:
                    sanitized_data, rows_accessed = self._execute_legacy_query(conn, database, query_description)
                    data_source_used = "Legacy Database"
                    conn.close()
            
            if sanitized_data.empty:
                return MantisResult(
                    type="text",
                    title="Query Results",
                    message=f"No data found for: {query_description}. Data source: {data_source_used}.",
                    tool_used="query_database",
                    metadata={'rows_accessed': 0, 'data_source': data_source_used}
                )
            
            result_message = f"Query executed on {database}. Retrieved {rows_accessed} rows from {data_source_used}."
            
            chart_type = "table"
            figure = None
            try:
                if len(sanitized_data) > 1 and len(sanitized_data.columns) >= 2:
                    numeric_cols = sanitized_data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        chart_type = "chart"
                        first_col = sanitized_data.columns[0]
                        first_numeric = numeric_cols[0]
                        figure = go.Figure(data=[
                            go.Bar(
                                x=sanitized_data[first_col].head(10),
                                y=sanitized_data[first_numeric].head(10),
                                name=first_numeric
                            )
                        ])
                        figure.update_layout(
                            title=f"Data Analysis: {database}",
                            xaxis_title=first_col,
                            yaxis_title=first_numeric,
                            showlegend=True
                        )
            except Exception as viz_error:
                logger.warning(f"Visualization creation failed: {viz_error}")
                chart_type = "table"
                figure = None
            
            return MantisResult(
                type=chart_type,
                title=f"Query Results: {database}",
                message=result_message,
                data=sanitized_data.head(100),
                figure=figure,
                tool_used="query_database",
                metadata={
                    'rows_accessed': rows_accessed,
                    'data_source': data_source_used,
                    'caselle_active': self.caselle_active
                }
            )
            
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return MantisResult(
                type="error",
                title="Query Error",
                message=f"Error executing query: {str(e)}",
                tool_used="query_database"
            )
    
    def _try_adapter_query(self, database: str, query_description: str) -> pd.DataFrame:
        """Try to answer the query using the UnifiedDataAdapter"""
        if not self.data_adapter:
            return None
        
        try:
            query_lower = query_description.lower()
            db_lower = database.lower()
            
            if any(kw in query_lower for kw in ['general ledger', 'gl', 'transaction', 'journal']) or db_lower in ('gl_primary', 'general_ledger'):
                data = self.data_adapter.get_general_ledger()
                if data:
                    return pd.DataFrame(data)
            
            if any(kw in query_lower for kw in ['budget', 'appropriation', 'expenditure', 'revenue']):
                import datetime as dt
                for year in [dt.datetime.now().year, dt.datetime.now().year - 1]:
                    data = self.data_adapter.get_budget_data(fiscal_year=year)
                    if data:
                        return pd.DataFrame(data)
            
            if any(kw in query_lower for kw in ['payroll', 'salary', 'employee', 'compensation', 'wage']) or db_lower == 'payroll':
                data = self.data_adapter.get_payroll_data()
                if data:
                    return pd.DataFrame(data)
            
            if any(kw in query_lower for kw in ['vendor', 'accounts payable', 'ap ', 'invoice', 'payment']):
                data = self.data_adapter.get_accounts_payable()
                if data:
                    return pd.DataFrame(data)
            
            if any(kw in query_lower for kw in ['utility', 'water', 'sewer', 'billing']) or db_lower == 'utility':
                data = self.data_adapter.get_utility_billing()
                if data:
                    return pd.DataFrame(data)
            
            if any(kw in query_lower for kw in ['asset', 'depreciation', 'capital', 'equipment']) or db_lower == 'asset':
                data = self.data_adapter.get_fixed_assets()
                if data:
                    return pd.DataFrame(data)
            
            if any(kw in query_lower for kw in ['department']):
                data = self.data_adapter.get_departments()
                if data:
                    return pd.DataFrame(data)
            
            data = self.data_adapter.get_general_ledger()
            if data:
                return pd.DataFrame(data)
                
        except Exception as e:
            logger.debug(f"Adapter query failed, will fall back to legacy: {e}")
        
        return None
    
    def _get_legacy_db_connection(self, database: str):
        """Get a direct SQLite connection for legacy database access"""
        try:
            from modules.database.db_connection import get_db_path_for_org
            
            if database.lower() == "gl_primary" or "general ledger" in database.lower():
                db_path = get_db_path_for_org(self.org)
                return sqlite3.connect(db_path)
            elif database.lower() == "utility":
                path = 'databases/sample_utility_management.db'
                if os.path.exists(path): return sqlite3.connect(path)
            elif database.lower() == "asset":
                path = 'databases/sample_asset_management.db'
                if os.path.exists(path): return sqlite3.connect(path)
            elif database.lower() == "permits":
                path = 'databases/sample_permits_licensing.db'
                if os.path.exists(path): return sqlite3.connect(path)
            elif database.lower() == "payroll":
                path = 'databases/payroll_city_payroll_demo.db'
                if os.path.exists(path): return sqlite3.connect(path)
            else:
                db_path = get_db_path_for_org(self.org)
                return sqlite3.connect(db_path)
        except Exception as e:
            logger.warning(f"Could not get legacy DB connection for {database}: {e}")
        return None
    
    def _execute_legacy_query(self, conn, database: str, query_description: str):
        """Execute a query against a legacy SQLite connection"""
        sanitized_data = pd.DataFrame()
        rows_accessed = 0
        
        if self.natural_language:
            sql_result = self.natural_language.generate_sql_from_query(query_description, database)
            sql_query = sql_result.get('sql', '')
            if sql_query:
                try:
                    sanitized_data = pd.read_sql_query(sql_query, conn)
                    rows_accessed = len(sanitized_data)
                except Exception as sql_error:
                    logger.error(f"SQL execution error: {sql_error}")
                    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
                    if not tables.empty:
                        first_table = tables.iloc[0]['name']
                        sanitized_data = pd.read_sql_query(f"SELECT * FROM {first_table} LIMIT 100", conn)
                        rows_accessed = len(sanitized_data)
        else:
            tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
            sanitized_data = tables
            rows_accessed = len(tables)
        
        return sanitized_data, rows_accessed

    async def _check_gasb_compliance_adapter(self, query: str, fund_code: str = None,
                                              check_type: str = "general") -> MantisResult:
        """Check GASB compliance using regulatory modules and fund policy"""
        try:
            from modules.utils.fund_policy import (
                get_gasb_compliance_context, get_fund_classification,
                is_fund_eligible_for_reallocation, get_policy_snapshot
            )

            gasb_context = get_gasb_compliance_context(fund_code=fund_code, query=query)

            try:
                from modules.vatica.regulatory_auto_integrator import (
                    get_regulatory_context, enhance_prompt_with_regulatory_context
                )
                regulatory_context = get_regulatory_context(query)
            except ImportError:
                regulatory_context = {}

            response_parts = []

            if check_type == "reallocation" or "realloc" in query.lower():
                policy = get_policy_snapshot()
                response_parts.append("**Fund Reallocation Compliance Check**\n")
                response_parts.append(f"GASB Reference: {policy['gasb_reference']}\n")
                response_parts.append("\nPolicy Rules:")
                for rule in policy["policy_rules"]:
                    response_parts.append(f"- {rule}")

                if fund_code:
                    eligible, reason = is_fund_eligible_for_reallocation(fund_code)
                    response_parts.append(f"\n**Fund '{fund_code}' Status:** {reason}")

                eligible_types = policy.get("reallocation_eligible_types", [])
                response_parts.append(f"\nEligible fund types for reallocation: {', '.join(eligible_types)}")

                classified = policy.get("classifications_by_type", {})
                for cls_type, funds in classified.items():
                    status = "ELIGIBLE" if cls_type in eligible_types else "BLOCKED"
                    response_parts.append(f"- {cls_type}: {', '.join(funds)} [{status}]")

            response_parts.append("\n**GASB Standards Reference:**")
            for key, standard in gasb_context.items():
                if isinstance(standard, dict) and "title" in standard:
                    response_parts.append(f"\n{standard['title']}")
                    if "summary" in standard:
                        response_parts.append(f"{standard['summary']}")
                    if "key_requirements" in standard:
                        for req in standard["key_requirements"]:
                            response_parts.append(f"- {req}")

            if "reallocation_rules" in gasb_context:
                rules = gasb_context["reallocation_rules"]
                response_parts.append(f"\n**Reallocation Rules:** {rules.get('general', '')}")
                if "best_practices" in rules:
                    response_parts.append("\nBest Practices:")
                    for bp in rules["best_practices"]:
                        response_parts.append(f"- {bp}")

            if "fund_specific" in gasb_context:
                fs = gasb_context["fund_specific"]
                response_parts.append(f"\n**Fund-Specific Analysis ({fs['fund_code']}):**")
                response_parts.append(f"- Classification: {fs['classification']}")
                response_parts.append(f"- Reallocation Eligible: {'Yes' if fs['reallocation_eligible'] else 'No'}")
                response_parts.append(f"- {fs['compliance_note']}")

            if regulatory_context:
                response_parts.append("\n**Additional Regulatory Context:**")
                for source, guidance in regulatory_context.items():
                    response_parts.append(f"\n{guidance}")

            return MantisResult(
                type="compliance",
                title="GASB Compliance Analysis",
                message="\n".join(response_parts),
                tool_used="check_gasb_compliance",
                metadata={
                    "check_type": check_type,
                    "fund_code": fund_code,
                    "has_regulatory_context": bool(regulatory_context),
                }
            )
        except Exception as e:
            logger.error(f"GASB compliance check error: {e}")
            return MantisResult(
                type="error",
                title="GASB Compliance Check Error",
                message=f"Error checking GASB compliance: {str(e)}",
                tool_used="check_gasb_compliance"
            )

    async def _get_fund_policy_adapter(self, fund_code: str = None) -> MantisResult:
        """Get fund policy snapshot or specific fund classification"""
        try:
            from modules.utils.fund_policy import (
                get_policy_snapshot, get_fund_classification,
                is_fund_eligible_for_reallocation, GASB_54_CATEGORIES
            )

            if fund_code:
                classification = get_fund_classification(fund_code)
                eligible, reason = is_fund_eligible_for_reallocation(fund_code)
                category_info = GASB_54_CATEGORIES.get(classification, {})

                message = (
                    f"**Fund: {fund_code}**\n"
                    f"- Classification: {classification}\n"
                    f"- GASB Reference: {category_info.get('gasb_reference', 'N/A')}\n"
                    f"- Reallocation Eligible: {'Yes' if eligible else 'No'}\n"
                    f"- {reason}\n"
                    f"- Description: {category_info.get('description', 'N/A')}"
                )
            else:
                policy = get_policy_snapshot()
                parts = [
                    f"**Fund Classification Policy** (as of {policy['timestamp'][:10]})\n",
                    f"Total Classified Funds: {policy['total_funds_classified']}",
                    f"GASB Reference: {policy['gasb_reference']}\n",
                    f"Reallocation-Eligible Types: {', '.join(policy['reallocation_eligible_types'])}\n",
                    "**Funds by Classification:**",
                ]
                for cls_type, funds in policy.get("classifications_by_type", {}).items():
                    eligible_marker = " [ELIGIBLE]" if cls_type in policy["reallocation_eligible_types"] else " [BLOCKED]"
                    parts.append(f"- {cls_type}{eligible_marker}: {', '.join(funds)}")

                parts.append("\n**Policy Rules:**")
                for rule in policy.get("policy_rules", []):
                    parts.append(f"- {rule}")

                message = "\n".join(parts)

            return MantisResult(
                type="policy",
                title="Fund Classification Policy",
                message=message,
                tool_used="get_fund_policy",
                metadata={"fund_code": fund_code}
            )
        except Exception as e:
            logger.error(f"Fund policy lookup error: {e}")
            return MantisResult(
                type="error",
                title="Fund Policy Error",
                message=f"Error retrieving fund policy: {str(e)}",
                tool_used="get_fund_policy"
            )

    async def _validate_reallocation_adapter(self, source_funds: List[str],
                                              target_fund: str = None) -> MantisResult:
        """Validate a proposed budget reallocation against fund policy"""
        try:
            from modules.utils.fund_policy import validate_reallocation_request

            result = validate_reallocation_request(source_funds, target_fund)

            parts = []
            if result["valid"]:
                parts.append("**Reallocation Validation: APPROVED**\n")
                parts.append("All source funds are eligible for reallocation per GASB 54 and current fund policy.\n")
            else:
                parts.append("**Reallocation Validation: BLOCKED**\n")
                parts.append("One or more source funds cannot be used for reallocation.\n")

            if result["approved_sources"]:
                parts.append("**Approved Sources:**")
                for src in result["approved_sources"]:
                    parts.append(f"- {src['fund_code']} ({src['classification']}) - Approved")

            if result["blocked_sources"]:
                parts.append("\n**Blocked Sources:**")
                for src in result["blocked_sources"]:
                    parts.append(f"- {src['fund_code']} ({src['classification']}) - {src['reason']}")

            if result["gasb_violations"]:
                parts.append("\n**GASB Violations:**")
                for violation in result["gasb_violations"]:
                    parts.append(f"- {violation}")

            if result["warnings"]:
                parts.append("\n**Warnings:**")
                for warning in result["warnings"]:
                    parts.append(f"- {warning}")

            return MantisResult(
                type="validation",
                title="Reallocation Validation",
                message="\n".join(parts),
                tool_used="validate_reallocation",
                metadata={
                    "valid": result["valid"],
                    "source_funds": source_funds,
                    "target_fund": target_fund,
                    "violations_count": len(result["gasb_violations"]),
                }
            )
        except Exception as e:
            logger.error(f"Reallocation validation error: {e}")
            return MantisResult(
                type="error",
                title="Reallocation Validation Error",
                message=f"Error validating reallocation: {str(e)}",
                tool_used="validate_reallocation"
            )

    async def _analyze_scenario_adapter(self, scenario_name: str, base_amount: float,
                                       volatility: float = 0.2, simulations: int = 1000) -> MantisResult:
        """Adapter for scenario analysis with Monte Carlo"""
        try:
            # Run Monte Carlo simulation
            results = run_monte_carlo_optimized(base_amount, volatility, simulations)
            
            # Create visualization
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=results['simulated_values'],
                nbinsx=50,
                name='Simulated Outcomes'
            ))
            
            fig.add_vline(x=results['mean'], line_dash="dash", 
                         annotation_text=f"Mean: ${results['mean']:,.0f}")
            fig.add_vline(x=results['percentiles']['p5'], line_dash="dot",
                         annotation_text="5th Percentile", line_color="red")
            fig.add_vline(x=results['percentiles']['p95'], line_dash="dot",
                         annotation_text="95th Percentile", line_color="green")
            
            fig.update_layout(
                title=f"Monte Carlo Analysis: {scenario_name}",
                xaxis_title="Projected Value ($)",
                yaxis_title="Frequency",
                showlegend=True
            )
            
            return MantisResult(
                type="chart",
                title=f"Scenario Analysis: {scenario_name}",
                message=f"Ran {simulations} simulations. Mean outcome: ${results['mean']:,.0f}, "
                       f"90% confidence interval: ${results['percentiles']['p5']:,.0f} - "
                       f"${results['percentiles']['p95']:,.0f}",
                figure=fig,
                tool_used="analyze_scenario",
                metadata=results
            )
            
        except Exception as e:
            logger.error(f"Scenario analysis error: {e}")
            return MantisResult(
                type="error",
                title="Scenario Analysis Error",
                message=str(e),
                tool_used="analyze_scenario"
            )
    
    async def _fallback_processing(self, message: str, context: Dict) -> MantisResult:
        """Fallback processing when GPT-4o is unavailable"""
        # Use the existing natural language processor if available
        if self.natural_language:
            try:
                # Load actual database data for natural language processing
                available_data = {}
                if self.db_manager:
                    connections = self.db_manager.get_all_database_connections()
                    for db_name, conn_info in connections.items():
                        try:
                            conn = conn_info.get('connection')
                            if conn and db_name == 'gl_primary':
                                # Load general ledger data
                                query = "SELECT * FROM accounts LIMIT 1000"
                                df = pd.read_sql_query(query, conn)
                                available_data['accounts'] = df
                        except Exception as e:
                            logger.warning(f"Failed to load data from {db_name}: {e}")
                
                response = self.natural_language.process_natural_language_query(
                    user_query=message,
                    available_data=available_data if available_data else None
                )
                return MantisResult(
                    type="text",
                    title="AI Response (Fallback Mode)",
                    message=response.get('response', 'Unable to process request'),
                    tool_used="fallback_nlp"
                )
            except Exception as e:
                logger.error(f"Fallback processing error: {e}")
        
        return MantisResult(
            type="error",
            title="AI Unavailable",
            message="The AI system is temporarily unavailable. Please ensure the OpenAI API key is configured.",
            tool_used="error"
        )
    
    # Helper Methods

    def _get_fund_policy_context(self) -> str:
        """Build fund policy context for the AI system prompt"""
        try:
            from modules.utils.fund_policy import get_policy_snapshot
            policy = get_policy_snapshot()

            parts = [
                f"Classified Funds: {policy['total_funds_classified']}",
                f"GASB Reference: {policy['gasb_reference']}",
                f"Reallocation-Eligible Types: {', '.join(policy['reallocation_eligible_types'])}",
            ]
            for cls_type, funds in policy.get("classifications_by_type", {}).items():
                eligible = cls_type in policy["reallocation_eligible_types"]
                parts.append(f"  {cls_type}: {', '.join(funds)} [{'ELIGIBLE' if eligible else 'BLOCKED'}]")

            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"Could not load fund policy context: {e}")
            return "Fund policy not available. Recommend classifying funds in Admin Panel."

    def _get_data_context_summary(self) -> str:
        """Build a summary of available data for the AI system prompt.
        
        Routes through the UnifiedDataAdapter to pull from whatever data source
        is active (Caselle API, file imports, or legacy databases).
        """
        if hasattr(self, '_cached_data_context') and self._cached_data_context:
            return self._cached_data_context
        
        context_parts = []
        
        if self.caselle_active:
            context_parts.append("Data Source: Caselle ERP API (live connection)")
        elif self.archive_records > 0:
            context_parts.append(f"Data Source: Report Archive ({self.archive_records} GL records from file imports)")
        else:
            context_parts.append(f"Data Source: {self.active_data_source}")
        
        if self.data_adapter:
            try:
                gl_data = self.data_adapter.get_general_ledger()
                if gl_data:
                    context_parts.append(f"\nGeneral Ledger: {len(gl_data)} records available")
                    departments = set()
                    funds = set()
                    for r in gl_data[:200]:
                        if r.get('department'): departments.add(r['department'])
                        if r.get('fund'): funds.add(r['fund'])
                    if departments:
                        context_parts.append(f"  Departments: {', '.join(sorted(departments)[:15])}")
                    if funds:
                        context_parts.append(f"  Funds: {', '.join(sorted(funds)[:10])}")
            except Exception as e:
                logger.debug(f"Could not load GL data from adapter: {e}")
            
            try:
                import datetime as dt
                current_year = dt.datetime.now().year
                for year in [current_year, current_year - 1]:
                    budget_data = self.data_adapter.get_budget_data(fiscal_year=year)
                    if budget_data:
                        total_budget = sum(float(r.get('original_budget', 0) or 0) for r in budget_data)
                        total_actual = sum(float(r.get('actual_ytd', 0) or 0) for r in budget_data)
                        context_parts.append(f"\nFY{year} Budget: {len(budget_data)} line items, Total Budget ${total_budget:,.0f}, Actual YTD ${total_actual:,.0f}")
                        break
            except Exception as e:
                logger.debug(f"Could not load budget data from adapter: {e}")
            
            try:
                payroll_data = self.data_adapter.get_payroll_data()
                if payroll_data:
                    total_gross = sum(float(r.get('gross_pay', 0) or 0) for r in payroll_data)
                    context_parts.append(f"\nPayroll: {len(payroll_data)} records, Total Gross Pay ${total_gross:,.0f}")
            except Exception as e:
                logger.debug(f"Could not load payroll data from adapter: {e}")
            
            try:
                available_years = self.data_adapter.get_available_years()
                if available_years:
                    context_parts.append(f"\nAvailable fiscal years in archive: {', '.join(str(y) for y in available_years)}")
            except Exception as e:
                logger.debug(f"Could not get available years: {e}")
        
        self._load_legacy_db_context(context_parts)
        
        if context_parts:
            self._cached_data_context = "\n".join(context_parts)
        else:
            self._cached_data_context = "No data sources currently connected. Configure the Caselle API or import files via the Data Sources admin page."
        
        return self._cached_data_context
    
    def _load_legacy_db_context(self, context_parts: list):
        """Load schema info from legacy SQLite databases as supplemental context"""
        db_configs = {
            'General Ledger (GL)': 'databases/caselle_gl0_mock.db',
            'Payroll': 'databases/payroll_city_payroll_demo.db',
            'Utilities': 'databases/sample_utility_management.db',
            'Assets': 'databases/sample_asset_management.db',
            'Permits & Licensing': 'databases/sample_permits_licensing.db'
        }
        
        for db_name, db_path in db_configs.items():
            try:
                if not os.path.exists(db_path):
                    alt_path = f'databases/core/{os.path.basename(db_path)}'
                    if os.path.exists(alt_path):
                        db_path = alt_path
                    else:
                        continue
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
                
                if not tables:
                    conn.close()
                    continue
                
                table_details = []
                for table in tables[:8]:
                    try:
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [(row[1], row[2]) for row in cursor.fetchall()]
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        row_count = cursor.fetchone()[0]
                        col_str = ", ".join([f"{c[0]} ({c[1]})" for c in columns[:10]])
                        table_details.append(f"  - {table} ({row_count} rows): {col_str}")
                    except:
                        pass
                
                conn.close()
                
                if table_details:
                    context_parts.append(f"\n{db_name} Database:")
                    context_parts.extend(table_details)
                    
            except Exception as e:
                logger.debug(f"Could not load schema for {db_name}: {e}")
        
        try:
            gl_path = 'databases/caselle_gl0_mock.db'
            if not os.path.exists(gl_path):
                gl_path = 'databases/core/caselle_gl0_mock.db'
            if os.path.exists(gl_path):
                conn = sqlite3.connect(gl_path)
                try:
                    dept_data = pd.read_sql_query(
                        "SELECT Department, SUM(Budget) as TotalBudget, SUM(Actual) as TotalActual, "
                        "COUNT(*) as LineItems FROM DepartmentPerformance GROUP BY Department LIMIT 15", conn
                    )
                    if not dept_data.empty:
                        context_parts.append("\nBudget Summary by Department:")
                        for _, row in dept_data.iterrows():
                            variance = row.get('TotalBudget', 0) - row.get('TotalActual', 0)
                            context_parts.append(
                                f"  - {row['Department']}: Budget ${row.get('TotalBudget', 0):,.0f}, "
                                f"Actual ${row.get('TotalActual', 0):,.0f}, Variance ${variance:,.0f}"
                            )
                except:
                    pass
                conn.close()
        except:
            pass
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input for security - only remove actual injection attempts"""
        dangerous_patterns = [
            r'(?i)(script|javascript|vbscript)[:=]',
            r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]'
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text)
        
        return text.strip()
    
    def _generate_safe_query(self, database: str, description: str) -> str:
        """Generate safe SQL from natural language description"""
        # This is a simplified version - in production, use proper query builder
        # Never execute raw user input as SQL
        
        # Map common requests to safe queries
        safe_queries = {
            'departments': "SELECT Department, SUM(Amount) as Total FROM transactions GROUP BY Department",
            'vendors': "SELECT Vendor, COUNT(*) as Transactions FROM transactions GROUP BY Vendor",
            'monthly': "SELECT DATE_TRUNC('month', Date) as Month, SUM(Amount) FROM transactions GROUP BY Month",
            'budget': "SELECT Department, Budget, Actual, (Budget - Actual) as Variance FROM budgets"
        }
        
        # Find best matching query
        for key, query in safe_queries.items():
            if key.lower() in description.lower():
                return query
        
        # Default safe query
        return "SELECT COUNT(*) as total_records FROM transactions LIMIT 10"
    
    def _summarize_file_context(self, files: Dict) -> str:
        """Summarize uploaded file context"""
        summary_parts = []
        for filename, file_data in files.items():
            if file_data['type'] == 'pdf':
                summary_parts.append(f"PDF '{filename}' with {file_data.get('pages', 0)} pages")
            elif file_data['type'] == 'csv':
                summary_parts.append(f"CSV '{filename}' with {file_data.get('rows', 0)} rows")
        
        return ", ".join(summary_parts) if summary_parts else "No files"
    
    def _log_audit(self, event: Dict):
        """Log events for audit trail"""
        event['timestamp'] = datetime.now().isoformat()
        self.audit_log.append(event)
        
        # Persist to database
        try:
            conn = sqlite3.connect('security_events.db')
            cursor = conn.cursor()
            
            # Create audit_log table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    details TEXT,
                    timestamp TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT INTO audit_log (event_type, details, timestamp)
                VALUES (?, ?, ?)
            ''', (event.get('action', 'unknown'), json.dumps(event), event['timestamp']))
            conn.commit()
            conn.close()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                logger.warning(f"Audit table creation failed, skipping audit: {e}")
            else:
                logger.error(f"Audit logging error: {e}")
        except Exception as e:
            logger.error(f"Audit logging error: {e}")
    
    async def _analyze_grant_eligibility_adapter(self, grant_id: str, 
                                                organization_profile: Dict = None) -> MantisResult:
        """Adapter for grant eligibility analysis"""
        if not self.grant_intelligence:
            return MantisResult(
                type="error",
                title="Grant Analysis Unavailable",
                message="Grant intelligence module is not available",
                tool_used="analyze_grant_eligibility"
            )
        
        try:
            # Get default org profile if not provided
            if not organization_profile:
                organization_profile = {
                    'type': 'municipality',
                    'population': 50000,
                    'budget': 100000000,
                    'location': 'USA'
                }
            
            # Since assess_grant_eligibility doesn't exist, use intelligent matching
            # to find and analyze the grant
            matching_result = self.grant_intelligence.intelligent_grant_matching(
                municipal_profile=organization_profile,
                category_filter=None
            )
            
            # Find the specific grant
            grants = matching_result.get('matching_grants', [])
            target_grant = None
            for grant in grants:
                if grant.grant_id == grant_id:
                    target_grant = grant
                    break
            
            if target_grant:
                analysis = f"""Grant Eligibility Analysis for {target_grant.title}:
                
                Agency: {target_grant.agency}
                Amount Range: ${target_grant.min_amount:,.0f} - ${target_grant.max_amount:,.0f}
                Deadline: {target_grant.deadline.strftime('%Y-%m-%d')}
                Match Required: {'Yes' if target_grant.match_required else 'No'}
                Eligibility Score: {target_grant.eligibility_score:.1%}
                
                Eligibility Criteria:
                {', '.join(target_grant.eligibility_criteria)}
                
                AI Analysis: {target_grant.ai_analysis if target_grant.ai_analysis else 'Based on your organization profile, this grant appears to be a good match.'}
                """
            else:
                analysis = f"Grant with ID '{grant_id}' not found in available grants database."
            
            return MantisResult(
                type="text",
                title="Grant Eligibility Analysis",
                message=analysis,
                tool_used="analyze_grant_eligibility"
            )
            
        except Exception as e:
            logger.error(f"Eligibility analysis error: {e}")
            return MantisResult(
                type="error",
                title="Eligibility Analysis Error",
                message=str(e),
                tool_used="analyze_grant_eligibility"
            )
    
    async def _assess_data_quality_adapter(self, table_name: str, 
                                          auto_fix: bool = False) -> MantisResult:
        """Adapter for data quality assessment - routes through data adapter first, falls back to legacy"""
        if not self.data_quality:
            return MantisResult(
                type="error",
                title="Data Quality Assessment Unavailable",
                message="Data quality engine is not available",
                tool_used="assess_data_quality"
            )
        
        try:
            real_data = None
            
            if self.data_adapter:
                real_data = self._load_quality_data_from_adapter(table_name)
            
            if real_data is None or real_data.empty:
                real_data = self._load_quality_data_from_legacy(table_name)
            
            if real_data is None or real_data.empty:
                return MantisResult(
                    type="text",
                    title="Data Quality Assessment",
                    message=f"Table '{table_name}' not found or is empty. Available tables include: DepartmentPerformance, accounts, general_ledger, Employees, Positions, water_meters, building_permits, infrastructure_assets, vehicle_fleet.",
                    tool_used="assess_data_quality"
                )
            
            assessment_result = self.data_quality.comprehensive_quality_assessment(
                data=real_data,
                dataset_name=table_name
            )
            
            issues = assessment_result.get('issues', [])
            
            if not issues:
                return MantisResult(
                    type="text",
                    title="Data Quality Assessment",
                    message=f"Table '{table_name}' has no quality issues",
                    tool_used="assess_data_quality"
                )
            
            # Format issues as DataFrame
            df = pd.DataFrame([{
                'Issue Type': issue.issue_type,
                'Field': issue.field_name,
                'Severity': issue.severity,
                'Affected Rows': issue.affected_rows,
                'Fix Available': 'Yes' if issue.auto_fixable else 'No'
            } for issue in issues])
            
            return MantisResult(
                type="table",
                title=f"Data Quality Issues in '{table_name}'",
                message=f"Found {len(issues)} data quality issues",
                data=df,
                tool_used="assess_data_quality"
            )
            
        except Exception as e:
            logger.error(f"Data quality assessment error: {e}")
            return MantisResult(
                type="error",
                title="Data Quality Error",
                message=str(e),
                tool_used="assess_data_quality"
            )
    
    def _load_quality_data_from_adapter(self, table_name: str) -> pd.DataFrame:
        """Try to load data for quality assessment from the UnifiedDataAdapter"""
        try:
            name_lower = table_name.lower().replace(' ', '_')
            adapter_map = {
                'general_ledger': lambda: self.data_adapter.get_general_ledger(),
                'gl': lambda: self.data_adapter.get_general_ledger(),
                'budget': lambda: self.data_adapter.get_budget_data(fiscal_year=__import__('datetime').datetime.now().year),
                'budget_data': lambda: self.data_adapter.get_budget_data(fiscal_year=__import__('datetime').datetime.now().year),
                'payroll': lambda: self.data_adapter.get_payroll_data(),
                'payroll_data': lambda: self.data_adapter.get_payroll_data(),
                'accounts_payable': lambda: self.data_adapter.get_accounts_payable(),
                'accounts_receivable': lambda: self.data_adapter.get_accounts_receivable(),
                'utility_billing': lambda: self.data_adapter.get_utility_billing(),
                'fixed_assets': lambda: self.data_adapter.get_fixed_assets(),
            }
            
            if name_lower in adapter_map:
                data = adapter_map[name_lower]()
                if data:
                    return pd.DataFrame(data)
        except Exception as e:
            logger.debug(f"Could not load quality data from adapter for {table_name}: {e}")
        return None
    
    def _load_quality_data_from_legacy(self, table_name: str) -> pd.DataFrame:
        """Fallback: load data for quality assessment from legacy SQLite databases"""
        table_db_map = {
            'departmentperformance': ('databases/caselle_gl0_mock.db', 'DepartmentPerformance'),
            'accounts': ('databases/caselle_gl0_mock.db', 'accounts'),
            'general_ledger': ('databases/caselle_gl0_mock.db', 'general_ledger'),
            'employees': ('databases/payroll_city_payroll_demo.db', 'Employees'),
            'positions': ('databases/payroll_city_payroll_demo.db', 'Positions'),
            'water_meters': ('databases/sample_utility_management.db', 'water_meters'),
            'building_permits': ('databases/sample_permits_licensing.db', 'building_permits'),
            'infrastructure_assets': ('databases/sample_asset_management.db', 'infrastructure_assets'),
            'vehicle_fleet': ('databases/sample_asset_management.db', 'vehicle_fleet'),
        }
        
        lookup_key = table_name.lower().replace(' ', '_')
        if lookup_key in table_db_map:
            db_path, actual_table = table_db_map[lookup_key]
        else:
            db_path = 'databases/caselle_gl0_mock.db'
            actual_table = table_name
        
        try:
            if not os.path.exists(db_path):
                alt = f'databases/core/{os.path.basename(db_path)}'
                if os.path.exists(alt):
                    db_path = alt
            
            conn = sqlite3.connect(db_path)
            real_data = pd.read_sql_query(f"SELECT * FROM {actual_table} LIMIT 500", conn)
            conn.close()
            return real_data
        except Exception as e:
            logger.warning(f"Could not load table {table_name} from legacy DB: {e}")
        return None
    
    async def _query_financial_data_adapter(self, query: str, 
                                           visualization: bool = True) -> MantisResult:
        """Adapter for natural language financial queries"""
        if not self.natural_language:
            return MantisResult(
                type="error",
                title="Query Processing Unavailable",
                message="Natural language processor is not available",
                tool_used="query_financial_data"
            )
        
        try:
            # Dynamically discover and load financial data from available databases
            available_data = self._load_dynamic_financial_data()
            
            # Process natural language query with actual financial data
            results = self.natural_language.process_natural_language_query(
                user_query=query,
                available_data=available_data
            )
            
            if visualization and results.get('data') is not None:
                # Generate appropriate visualization
                fig = self._generate_smart_visualization(results['data'], query)
                
                return MantisResult(
                    type="chart",
                    title=results.get('title', 'Query Results'),
                    message=results.get('summary', ''),
                    figure=fig,
                    data=results.get('data'),
                    tool_used="query_financial_data"
                )
            
            return MantisResult(
                type="table" if results.get('data') is not None else "text",
                title=results.get('title', 'Query Results'),
                message=results.get('summary', ''),
                data=results.get('data'),
                tool_used="query_financial_data"
            )
            
        except Exception as e:
            logger.error(f"Financial query error: {e}")
            return MantisResult(
                type="error",
                title="Query Processing Error",
                message=str(e),
                tool_used="query_financial_data"
            )
    
    def _load_dynamic_financial_data(self) -> Dict[str, pd.DataFrame]:
        """
        Dynamically discover and load financial data from available databases
        Uses connection registry and session state to find active databases
        """
        available_data = {}
        
        # Try multiple methods to discover and connect to databases
        
        # Method 1: Check session state for configured database path
        if hasattr(self, 'db_manager') and self.db_manager:
            try:
                # Get active databases from multi-database manager
                active_dbs = self.db_manager.get_active_databases()
                for db_name, db_config in active_dbs.items():
                    if db_config and 'path' in db_config:
                        self._load_database_tables(db_config['path'], db_name, available_data)
            except Exception as e:
                logger.warning(f"Could not load from multi-database manager: {e}")
        
        # Method 2: Use database connection module's dynamic selection
        try:
            from modules.database.db_connection import get_selected_database, DEFAULT_DB_PATH
            selected_db = get_selected_database()
            if selected_db and os.path.exists(selected_db):
                self._load_database_tables(selected_db, 'selected', available_data)
        except Exception as e:
            logger.warning(f"Could not load from selected database: {e}")
        
        # Method 3: Check connection registry for live databases
        try:
            from modules.database.connection_registry import get_registry
            registry = get_registry()
            
            # Get live database connections
            for func_name, (set_id, db_name) in registry.live_connections.items():
                if set_id in registry.database_sets:
                    db_set = registry.database_sets[set_id]
                    if func_name == 'GL' and db_set.gl_database:
                        # Connect to GL database
                        conn_info = db_set.get_connection_info('GL')
                        if conn_info:
                            self._load_database_tables_from_connection(conn_info, 'GL', available_data)
        except Exception as e:
            logger.warning(f"Could not load from connection registry: {e}")
        
        # Method 4: Scan standard database directories for available databases
        database_dirs = ['databases/core', 'databases', '.']
        for dir_path in database_dirs:
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if file.endswith('.db'):
                        db_path = os.path.join(dir_path, file)
                        # Prioritize certain databases
                        if 'govsight' in file.lower() or 'gl' in file.lower() or 'budget' in file.lower():
                            self._load_database_tables(db_path, file[:-3], available_data)
                            if available_data:  # If we found data, we can stop
                                break
        
        # Log what was discovered
        if available_data:
            logger.info(f"Dynamically loaded financial data from {len(available_data)} tables")
            for table_name, df in available_data.items():
                logger.debug(f"  - {table_name}: {len(df)} rows, {len(df.columns)} columns")
        else:
            logger.warning("No financial data could be dynamically loaded")
        
        return available_data
    
    def _load_database_tables(self, db_path: str, db_identifier: str, data_dict: Dict) -> None:
        """Helper to load tables from a SQLite database"""
        if not os.path.exists(db_path):
            return
        
        try:
            conn = sqlite3.connect(db_path)
            
            # Get list of tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table_name_tuple in tables:
                table_name = table_name_tuple[0]
                if table_name.startswith('sqlite_'):
                    continue
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 1000", conn)
                    if len(df) > 0:
                        key = f"{db_identifier}_{table_name}" if db_identifier != 'selected' else table_name
                        data_dict[key] = df
                except Exception as e:
                    logger.debug(f"Could not load table {table_name}: {e}")
            
            conn.close()
        except Exception as e:
            logger.debug(f"Could not connect to {db_path}: {e}")
    
    def _load_database_tables_from_connection(self, conn_info: Dict, db_type: str, data_dict: Dict) -> None:
        """Helper to load tables from a database connection info"""
        # This would connect using the connection info from the registry
        # For now, we'll focus on SQLite connections
        pass
    
    def _generate_smart_visualization(self, data: pd.DataFrame, query: str) -> go.Figure:
        """Generate appropriate visualization based on data and query"""
        # Simplified smart visualization logic
        if 'date' in query.lower() or 'time' in query.lower():
            # Time series chart
            date_col = [col for col in data.columns if 'date' in col.lower()]
            value_col = [col for col in data.columns if col not in date_col][0] if date_col else None
            
            if date_col and value_col:
                return px.line(data, x=date_col[0], y=value_col, title="Trend Analysis")
        
        if 'department' in query.lower():
            # Department chart
            if 'Department' in data.columns and len(data.columns) > 1:
                value_col = [col for col in data.columns if col != 'Department'][0]
                return px.bar(data, x='Department', y=value_col, title="Department Analysis")
        
        # Default bar chart
        if len(data.columns) >= 2:
            return px.bar(data, x=data.columns[0], y=data.columns[1], title="Analysis Results")
        
        # Fallback to simple chart
        return go.Figure(data=[go.Table(
            header=dict(values=list(data.columns)),
            cells=dict(values=[data[col].tolist() for col in data.columns])
        )])
    
    async def _analyze_file_adapter(self, file_name: str, analysis_type: str, 
                                   context: Dict = None) -> MantisResult:
        """Adapter for uploaded file analysis"""
        if not self.file_handler or not context or 'uploaded_files' not in context:
            return MantisResult(
                type="error",
                title="File Analysis Unavailable",
                message="No files uploaded or file handler unavailable",
                tool_used="analyze_uploaded_file"
            )
        
        try:
            file_data = context['uploaded_files'].get(file_name)
            if not file_data:
                return MantisResult(
                    type="error",
                    title="File Not Found",
                    message=f"File '{file_name}' not found in uploaded files",
                    tool_used="analyze_uploaded_file"
                )
            
            if analysis_type == "summary":
                if file_data['type'] == 'pdf':
                    summary = f"PDF Document Analysis:\n"
                    summary += f"- Pages: {file_data.get('pages', 'Unknown')}\n"
                    summary += f"- Content Length: {len(file_data.get('content', ''))} characters\n"
                    summary += f"- Preview: {file_data.get('content', '')[:500]}..."
                else:  # CSV
                    df = file_data.get('content')
                    summary = f"CSV Data Analysis:\n"
                    summary += f"- Rows: {len(df)}\n"
                    summary += f"- Columns: {', '.join(df.columns)}\n"
                    summary += f"- Data Types: {df.dtypes.to_dict()}\n"
                
                return MantisResult(
                    type="text",
                    title=f"Summary of {file_name}",
                    message=summary,
                    tool_used="analyze_uploaded_file"
                )
            
            elif analysis_type == "extract_data" and file_data['type'] == 'csv':
                return MantisResult(
                    type="table",
                    title=f"Data from {file_name}",
                    message=f"Extracted {len(file_data['content'])} rows",
                    data=file_data['content'],
                    tool_used="analyze_uploaded_file"
                )
            
            elif analysis_type == "validate":
                # Run data quality checks on uploaded data
                if self.data_quality and file_data['type'] == 'csv':
                    # Use the correct method: comprehensive_quality_assessment
                    assessment = self.data_quality.comprehensive_quality_assessment(
                        data=file_data['content'],
                        dataset_name=file_name
                    )
                    issues = assessment.get('quality_issues', [])
                    return MantisResult(
                        type="text",
                        title=f"Validation Results for {file_name}",
                        message=f"Found {len(issues)} validation issues" if issues else "Data validation passed",
                        tool_used="analyze_uploaded_file"
                    )
            
            return MantisResult(
                type="text",
                title="File Analysis Complete",
                message=f"Analyzed {file_name} with {analysis_type} method",
                tool_used="analyze_uploaded_file"
            )
            
        except Exception as e:
            logger.error(f"File analysis error: {e}")
            return MantisResult(
                type="error",
                title="File Analysis Error",
                message=str(e),
                tool_used="analyze_uploaded_file"
            )
    
    def _generate_smart_visualization(self, data: pd.DataFrame, query: str) -> go.Figure:
        """Generate appropriate visualization based on data and query"""
        # Determine best chart type based on data shape and query keywords
        
        if 'trend' in query.lower() or 'over time' in query.lower():
            # Time series chart
            if 'Date' in data.columns or 'date' in data.columns:
                date_col = 'Date' if 'Date' in data.columns else 'date'
                value_cols = [col for col in data.columns if col != date_col]
                
                fig = go.Figure()
                for col in value_cols[:3]:  # Limit to 3 series
                    fig.add_trace(go.Scatter(
                        x=data[date_col],
                        y=data[col],
                        mode='lines+markers',
                        name=col
                    ))
                
                fig.update_layout(
                    title="Trend Analysis",
                    xaxis_title="Date",
                    yaxis_title="Value"
                )
                return fig
        
        elif 'comparison' in query.lower() or 'compare' in query.lower():
            # Bar chart for comparison
            if len(data.columns) >= 2:
                x_col = data.columns[0]
                y_col = data.columns[1]
                
                fig = px.bar(data, x=x_col, y=y_col, title="Comparison Analysis")
                return fig
        
        elif 'distribution' in query.lower() or 'breakdown' in query.lower():
            # Pie chart for distribution
            if len(data.columns) >= 2:
                labels_col = data.columns[0]
                values_col = data.columns[1]
                
                fig = px.pie(data, names=labels_col, values=values_col, 
                            title="Distribution Analysis")
                return fig
        
        # Default to simple bar chart
        fig = px.bar(data.head(20), title="Data Visualization")
        return fig
    
    async def _get_economic_context_adapter(self, include_forecasts: bool = True) -> MantisResult:
        """Adapter for getting comprehensive economic context"""
        if not self.economic_intelligence:
            return MantisResult(
                type="error",
                title="Economic Intelligence Unavailable",
                message="Economic intelligence module is not available",
                tool_used="get_economic_context"
            )
        
        try:
            context = self.economic_intelligence.get_economic_context(include_forecasts)
            
            indicators_summary = context.get('indicators', {})
            economic_health = context.get('economic_health', {})
            revenue_impact = context.get('revenue_impact', {})
            
            message = f"**Economic Health: {economic_health.get('rating', 'Unknown')}** (Score: {economic_health.get('score', 0)}/100)\n\n"
            message += "**Key Factors:**\n"
            for factor in economic_health.get('factors', [])[:5]:
                message += f"- {factor}\n"
            
            message += "\n**Current Indicators:**\n"
            for name, data in list(indicators_summary.items())[:5]:
                if 'current_value' in data:
                    message += f"- {name}: {data['current_value']:.2f}"
                    if data.get('change'):
                        direction = "↑" if data['change'] > 0 else "↓"
                        message += f" {direction} ({abs(data['change']):.2f})"
                    message += "\n"
            
            message += "\n**Revenue Impact:**\n"
            message += f"- Recommended adjustment factor: {revenue_impact.get('total_adjustment', 1.0):.2%}\n"
            for rec in revenue_impact.get('recommendations', [])[:3]:
                message += f"- {rec}\n"
            
            return MantisResult(
                type="text",
                title="Economic Context Analysis",
                message=message,
                metadata=context,
                tool_used="get_economic_context"
            )
            
        except Exception as e:
            logger.error(f"Economic context error: {e}")
            return MantisResult(
                type="error",
                title="Economic Analysis Error",
                message=str(e),
                tool_used="get_economic_context"
            )
    
    async def _forecast_revenue_adapter(self, revenue_type: str, forecast_months: int = 12) -> MantisResult:
        """Adapter for revenue forecasting"""
        if not self.economic_intelligence:
            return MantisResult(
                type="error",
                title="Forecasting Unavailable",
                message="Economic intelligence module is not available",
                tool_used="forecast_revenue"
            )
        
        try:
            # Load historical revenue data from database
            conn = sqlite3.connect(f'databases/{self.org}/caselle_gl0_mock.db')
            
            if revenue_type == "sales_tax":
                query = """
                SELECT Date, SUM(Amount) as revenue 
                FROM Transactions 
                WHERE AccountNumber LIKE '3%' 
                GROUP BY Date 
                ORDER BY Date
                """
            elif revenue_type == "property_tax":
                query = """
                SELECT Date, SUM(Amount) as revenue 
                FROM Transactions 
                WHERE AccountNumber LIKE '31%' 
                GROUP BY Date 
                ORDER BY Date
                """
            else:  # total_revenue
                query = """
                SELECT Date, SUM(Amount) as revenue 
                FROM Transactions 
                WHERE Amount > 0 
                GROUP BY Date 
                ORDER BY Date
                """
            
            historical_revenue = pd.read_sql_query(query, conn)
            conn.close()
            
            if historical_revenue.empty:
                return MantisResult(
                    type="error",
                    title="Insufficient Data",
                    message="No historical revenue data available for forecasting",
                    tool_used="forecast_revenue"
                )
            
            historical_revenue['date'] = pd.to_datetime(historical_revenue['Date'])
            self.economic_intelligence.forecast_months = forecast_months
            
            forecast_result = self.economic_intelligence.forecast_revenue(historical_revenue)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=historical_revenue['date'],
                y=historical_revenue['revenue'],
                mode='lines',
                name='Historical',
                line=dict(color='blue')
            ))
            
            forecast_dates = pd.to_datetime(forecast_result['dates'])
            fig.add_trace(go.Scatter(
                x=forecast_dates,
                y=forecast_result['forecasts'],
                mode='lines',
                name='Forecast',
                line=dict(color='green', dash='dash')
            ))
            
            fig.add_trace(go.Scatter(
                x=forecast_dates,
                y=forecast_result['upper_bound'],
                mode='lines',
                name='Upper Bound',
                line=dict(color='lightgreen', dash='dot'),
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=forecast_dates,
                y=forecast_result['lower_bound'],
                mode='lines',
                name='Lower Bound',
                line=dict(color='lightgreen', dash='dot'),
                fill='tonexty',
                fillcolor='rgba(0,255,0,0.1)',
                showlegend=False
            ))
            
            fig.update_layout(
                title=f"{revenue_type.replace('_', ' ').title()} Revenue Forecast",
                xaxis_title="Date",
                yaxis_title="Revenue ($)",
                hovermode='x unified'
            )
            
            message = f"**Revenue Forecast for {revenue_type.replace('_', ' ').title()}**\n\n"
            message += f"Forecast Method: {forecast_result.get('method', 'Unknown')}\n"
            message += f"Model Accuracy: {forecast_result.get('model_score', 0):.2%}\n"
            message += f"Economic Indicators Used: {', '.join(forecast_result.get('features_used', []))}\n\n"
            
            avg_forecast = np.mean(forecast_result['forecasts'])
            message += f"Average Monthly Forecast: ${avg_forecast:,.2f}\n"
            message += f"Projected {forecast_months}-Month Total: ${sum(forecast_result['forecasts']):,.2f}"
            
            return MantisResult(
                type="chart",
                title=f"{revenue_type.replace('_', ' ').title()} Forecast",
                message=message,
                figure=fig,
                metadata=forecast_result,
                tool_used="forecast_revenue"
            )
            
        except Exception as e:
            logger.error(f"Revenue forecasting error: {e}")
            return MantisResult(
                type="error",
                title="Forecasting Error",
                message=str(e),
                tool_used="forecast_revenue"
            )
    
    async def _analyze_economic_scenarios_adapter(self, base_revenue: float) -> MantisResult:
        """Adapter for economic scenario analysis"""
        if not self.economic_intelligence:
            return MantisResult(
                type="error",
                title="Scenario Analysis Unavailable",
                message="Economic intelligence module is not available",
                tool_used="analyze_economic_scenarios"
            )
        
        try:
            analysis = self.economic_intelligence.analyze_economic_scenarios(base_revenue)
            
            scenarios = analysis['scenarios']
            current_conditions = analysis['current_conditions']
            recommendation = analysis['recommendation']
            
            scenario_df = pd.DataFrame([
                {
                    'Scenario': s['name'],
                    'Revenue Impact': f"{s['revenue_impact']:.1%}",
                    'Projected Revenue': f"${s['projected_revenue']:,.0f}",
                    'Revenue Change': f"${s['revenue_change']:,.0f}",
                    'Probability': f"{s['probability']:.0%}",
                    'GDP Growth': f"{s['gdp_growth']:.1%}",
                    'Unemployment Change': f"{s['unemployment_change']:+.1f}%"
                }
                for name, s in scenarios.items()
            ])
            
            fig = go.Figure()
            
            for scenario_name, scenario_data in scenarios.items():
                fig.add_trace(go.Bar(
                    name=scenario_data['name'],
                    x=['Projected Revenue'],
                    y=[scenario_data['projected_revenue']],
                    text=[f"${scenario_data['projected_revenue']:,.0f}"],
                    textposition='auto'
                ))
            
            fig.add_hline(
                y=base_revenue,
                line_dash="dash",
                line_color="red",
                annotation_text="Current Revenue"
            )
            
            fig.update_layout(
                title="Economic Scenario Analysis",
                yaxis_title="Revenue ($)",
                barmode='group',
                showlegend=True
            )
            
            message = f"**Economic Scenario Analysis**\n\n"
            message += f"Base Revenue: ${base_revenue:,.0f}\n\n"
            
            for name, scenario in scenarios.items():
                message += f"**{scenario['name']}** (Probability: {scenario['probability']:.0%})\n"
                message += f"- Projected Revenue: ${scenario['projected_revenue']:,.0f}\n"
                message += f"- Revenue Change: ${scenario['revenue_change']:+,.0f} ({scenario['revenue_impact']:.1%})\n"
                message += f"- GDP Growth: {scenario['gdp_growth']:+.1%}, Unemployment: {scenario['unemployment_change']:+.1f}%\n\n"
            
            message += f"**Recommendation:** {recommendation}"
            
            return MantisResult(
                type="chart",
                title="Economic Scenario Analysis",
                message=message,
                figure=fig,
                data=scenario_df,
                metadata=analysis,
                tool_used="analyze_economic_scenarios"
            )
            
        except Exception as e:
            logger.error(f"Scenario analysis error: {e}")
            return MantisResult(
                type="error",
                title="Scenario Analysis Error",
                message=str(e),
                tool_used="analyze_economic_scenarios"
            )
    
    async def _search_cloud_documents_adapter(self, archive_type: str, 
                                              search_prefix: str = None,
                                              start_date: str = None,
                                              end_date: str = None) -> MantisResult:
        """Adapter for GCS document search"""
        if not self.document_archive:
            return MantisResult(
                type="error",
                title="Cloud Archive Unavailable",
                message="GCP document archive is not configured. Set GOOGLE_CLOUD_PROJECT to enable cloud features.",
                tool_used="search_cloud_documents"
            )
        
        if not self.document_archive.connector.is_configured():
            return MantisResult(
                type="error",
                title="GCP Not Configured",
                message="Google Cloud Platform is not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable cloud archiving.",
                tool_used="search_cloud_documents"
            )
        
        try:
            start_dt = datetime.fromisoformat(start_date) if start_date else None
            end_dt = datetime.fromisoformat(end_date) if end_date else None
            
            results = self.document_archive.search_archives(
                archive_type,
                start_date=start_dt,
                end_date=end_dt,
                filter_prefix=search_prefix
            )
            
            if not results:
                return MantisResult(
                    type="text",
                    title="No Documents Found",
                    message=f"No documents found in {archive_type} archive matching your criteria.",
                    tool_used="search_cloud_documents"
                )
            
            df = pd.DataFrame([{
                'Name': doc['name'],
                'Size (KB)': round(doc['size'] / 1024, 2),
                'Type': doc['content_type'],
                'Created': doc['created'].strftime('%Y-%m-%d %H:%M'),
                'Bucket': doc['bucket']
            } for doc in results])
            
            message = f"Found {len(results)} documents in {archive_type} archive.\n\n"
            if search_prefix:
                message += f"Filter: '{search_prefix}'\n"
            if start_date or end_date:
                message += f"Date Range: {start_date or 'earliest'} to {end_date or 'latest'}\n"
            
            return MantisResult(
                type="table",
                title=f"Cloud Documents: {archive_type}",
                message=message,
                data=df,
                tool_used="search_cloud_documents",
                metadata={'total_documents': len(results), 'archive_type': archive_type}
            )
            
        except Exception as e:
            logger.error(f"Cloud document search error: {e}")
            return MantisResult(
                type="error",
                title="Document Search Error",
                message=str(e),
                tool_used="search_cloud_documents"
            )
    
    async def _query_bigquery_analytics_adapter(self, analysis_type: str,
                                                time_period: str = "all",
                                                custom_query: str = None) -> MantisResult:
        """Adapter for BigQuery analytics"""
        if not self.bigquery:
            return MantisResult(
                type="error",
                title="BigQuery Unavailable",
                message="BigQuery connector is not configured. Set GOOGLE_CLOUD_PROJECT to enable cloud analytics.",
                tool_used="query_bigquery_analytics"
            )
        
        if not self.bigquery.is_configured():
            return MantisResult(
                type="error",
                title="GCP Not Configured",
                message="Google Cloud Platform is not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable BigQuery analytics.",
                tool_used="query_bigquery_analytics"
            )
        
        try:
            # Map time periods to SQL conditions
            date_filter = ""
            if time_period == "last_month":
                date_filter = "WHERE DATE(transaction_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)"
            elif time_period == "last_quarter":
                date_filter = "WHERE DATE(transaction_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)"
            elif time_period == "last_year":
                date_filter = "WHERE DATE(transaction_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)"
            elif time_period == "year_to_date":
                date_filter = "WHERE EXTRACT(YEAR FROM transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE())"
            
            # Execute predefined analytics views or custom query
            if analysis_type == "revenue_trends":
                query = f"""
                SELECT * FROM `{self.bigquery.project_id}.{self.bigquery.dataset_id}.revenue_trends`
                {date_filter}
                ORDER BY month DESC
                LIMIT 100
                """
            elif analysis_type == "expense_analysis":
                query = f"""
                SELECT * FROM `{self.bigquery.project_id}.{self.bigquery.dataset_id}.expense_analysis`
                {date_filter}
                ORDER BY month DESC, department
                LIMIT 100
                """
            elif analysis_type == "compliance_report":
                query = f"""
                SELECT * FROM `{self.bigquery.project_id}.{self.bigquery.dataset_id}.compliance_report`
                {date_filter}
                ORDER BY audit_date DESC
                LIMIT 100
                """
            elif analysis_type == "custom" and custom_query:
                query = custom_query
            else:
                return MantisResult(
                    type="error",
                    title="Invalid Analysis Type",
                    message="Please specify a valid analysis type or provide a custom query.",
                    tool_used="query_bigquery_analytics"
                )
            
            df = self.bigquery.execute_query(query)
            
            if df.empty:
                return MantisResult(
                    type="text",
                    title="No Data Found",
                    message=f"No data found for {analysis_type} analysis in the specified time period.",
                    tool_used="query_bigquery_analytics"
                )
            
            # Create visualization if numeric data is present
            figure = None
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if numeric_cols and len(df) > 1:
                first_col = df.columns[0]
                first_numeric = numeric_cols[0]
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=df[first_col].head(10),
                        y=df[first_numeric].head(10),
                        name=first_numeric
                    )
                ])
                
                fig.update_layout(
                    title=f"BigQuery Analytics: {analysis_type.replace('_', ' ').title()}",
                    xaxis_title=first_col,
                    yaxis_title=first_numeric,
                    showlegend=True
                )
                
                figure = fig
            
            message = f"**BigQuery {analysis_type.replace('_', ' ').title()} Analysis**\n\n"
            message += f"Time Period: {time_period.replace('_', ' ').title()}\n"
            message += f"Records Retrieved: {len(df)}\n"
            
            return MantisResult(
                type="chart" if figure else "table",
                title=f"BigQuery: {analysis_type.replace('_', ' ').title()}",
                message=message,
                data=df.head(50),
                figure=figure,
                tool_used="query_bigquery_analytics",
                metadata={'analysis_type': analysis_type, 'time_period': time_period, 'rows': len(df)}
            )
            
        except Exception as e:
            logger.error(f"BigQuery analytics error: {e}")
            return MantisResult(
                type="error",
                title="BigQuery Analytics Error",
                message=str(e),
                tool_used="query_bigquery_analytics"
            )
    
    async def _deploy_ai_model_adapter(self, model_name: str,
                                       model_uri: str,
                                       container_image: str) -> MantisResult:
        """Adapter for Vertex AI model deployment"""
        if not self.vertex_ai:
            return MantisResult(
                type="error",
                title="Vertex AI Unavailable",
                message="Vertex AI connector is not configured. Set GOOGLE_CLOUD_PROJECT to enable AI model deployment.",
                tool_used="deploy_ai_model"
            )
        
        if not self.vertex_ai.is_configured():
            return MantisResult(
                type="error",
                title="GCP Not Configured",
                message="Google Cloud Platform is not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable Vertex AI.",
                tool_used="deploy_ai_model"
            )
        
        try:
            deployment_info = self.vertex_ai.deploy_model(
                model_display_name=model_name,
                model_artifact_uri=model_uri,
                serving_container_image_uri=container_image
            )
            
            if not deployment_info:
                return MantisResult(
                    type="error",
                    title="Deployment Failed",
                    message="Failed to deploy model to Vertex AI. Check logs for details.",
                    tool_used="deploy_ai_model"
                )
            
            message = f"**Model Deployment Successful**\n\n"
            message += f"Model: {deployment_info['model_display_name']}\n"
            message += f"Endpoint: {deployment_info['endpoint_display_name']}\n"
            message += f"Deployment Time: {deployment_info['deployment_time']}\n\n"
            message += f"Model Resource: `{deployment_info['model_name']}`\n"
            message += f"Endpoint Resource: `{deployment_info['endpoint_name']}`"
            
            return MantisResult(
                type="text",
                title="AI Model Deployed",
                message=message,
                tool_used="deploy_ai_model",
                metadata=deployment_info
            )
            
        except Exception as e:
            logger.error(f"Model deployment error: {e}")
            return MantisResult(
                type="error",
                title="Model Deployment Error",
                message=str(e),
                tool_used="deploy_ai_model"
            )
    
    async def _list_ai_models_adapter(self, filter: str = None) -> MantisResult:
        """Adapter for listing Vertex AI models"""
        if not self.vertex_ai:
            return MantisResult(
                type="error",
                title="Vertex AI Unavailable",
                message="Vertex AI connector is not configured. Set GOOGLE_CLOUD_PROJECT to enable AI model management.",
                tool_used="list_ai_models"
            )
        
        if not self.vertex_ai.is_configured():
            return MantisResult(
                type="error",
                title="GCP Not Configured",
                message="Google Cloud Platform is not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable Vertex AI.",
                tool_used="list_ai_models"
            )
        
        try:
            models = self.vertex_ai.list_models(filter_str=filter)
            
            if not models:
                return MantisResult(
                    type="text",
                    title="No Models Found",
                    message="No AI models found in Vertex AI. Deploy a model first.",
                    tool_used="list_ai_models"
                )
            
            df = pd.DataFrame([{
                'Display Name': model['display_name'],
                'Resource Name': model['name'].split('/')[-1],
                'Created': model['create_time'] or 'N/A',
                'Updated': model['update_time'] or 'N/A',
                'Deployed': 'Yes' if model['deployed'] else 'No'
            } for model in models])
            
            message = f"Found {len(models)} AI models in Vertex AI.\n\n"
            if filter:
                message += f"Filter: {filter}\n"
            
            return MantisResult(
                type="table",
                title="Vertex AI Models",
                message=message,
                data=df,
                tool_used="list_ai_models",
                metadata={'total_models': len(models), 'filter': filter}
            )
            
        except Exception as e:
            logger.error(f"List models error: {e}")
            return MantisResult(
                type="error",
                title="List Models Error",
                message=str(e),
                tool_used="list_ai_models"
            )
    
    async def _get_model_prediction_adapter(self, endpoint_id: str,
                                           input_data: Dict[str, Any]) -> MantisResult:
        """Adapter for Vertex AI model predictions"""
        if not self.vertex_ai:
            return MantisResult(
                type="error",
                title="Vertex AI Unavailable",
                message="Vertex AI connector is not configured. Set GOOGLE_CLOUD_PROJECT to enable AI predictions.",
                tool_used="get_model_prediction"
            )
        
        if not self.vertex_ai.is_configured():
            return MantisResult(
                type="error",
                title="GCP Not Configured",
                message="Google Cloud Platform is not configured. Set GOOGLE_CLOUD_PROJECT environment variable to enable Vertex AI.",
                tool_used="get_model_prediction"
            )
        
        try:
            # Convert input_data dict to list of instances
            instances = [input_data]
            
            predictions = self.vertex_ai.get_predictions(
                endpoint_id=endpoint_id,
                instances=instances
            )
            
            if not predictions:
                return MantisResult(
                    type="error",
                    title="Prediction Failed",
                    message="Failed to get predictions from the model. Check endpoint ID and input format.",
                    tool_used="get_model_prediction"
                )
            
            # Format predictions
            message = f"**AI Model Prediction Results**\n\n"
            message += f"Endpoint: {endpoint_id}\n"
            message += f"Input Data: {input_data}\n\n"
            message += f"**Predictions:**\n"
            
            for i, pred in enumerate(predictions):
                message += f"{i+1}. {pred}\n"
            
            return MantisResult(
                type="text",
                title="Model Predictions",
                message=message,
                tool_used="get_model_prediction",
                metadata={'endpoint_id': endpoint_id, 'input': input_data, 'predictions': predictions}
            )
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return MantisResult(
                type="error",
                title="Prediction Error",
                message=str(e),
                tool_used="get_model_prediction"
            )