"""
Enhanced Dashboard API for Multi-Database Integration
Provides endpoints for the enhanced Visual Analytics dashboard with multi-database support.
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Import the multi-database manager
from modules.bi_sandbox.multi_database_manager import multi_db_manager

logger = logging.getLogger(__name__)

class EnhancedDashboardAPI:
    """Enhanced API class for multi-database dashboard functionality."""
    
    def __init__(self):
        self.db_manager = multi_db_manager
        self.logger = logging.getLogger(__name__)
    
    def get_multi_database_schema(self) -> Dict[str, Any]:
        """
        Get unified schema from all databases for the field tree.
        
        Returns:
            Dictionary containing hierarchical database schema information
        """
        try:
            # Discover schemas from all databases
            schemas = self.db_manager.discover_database_schemas()
            
            # Get database summary
            summary = self.db_manager.get_database_summary()
            
            # Build hierarchical field tree structure
            field_tree = self._build_field_tree_structure(schemas)
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "summary": summary,
                "schemas": schemas,
                "field_tree": field_tree,
                "unified_catalog": self.db_manager.get_unified_field_catalog()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting multi-database schema: {e}")
            return {
                "success": False,
                "error": str(e),
                "field_tree": {},
                "unified_catalog": []
            }
    
    def _build_field_tree_structure(self, schemas: Dict[str, Any]) -> Dict[str, Any]:
        """Build hierarchical field tree structure for the HTML interface."""
        
        field_tree = {
            "databases": {}
        }
        
        # Database type icons and colors
        db_type_config = {
            "sqlite": {
                "icon": "🗄️",
                "color": "#4CAF50",
                "description": "SQLite Database"
            },
            "postgres": {
                "icon": "🐘", 
                "color": "#336791",
                "description": "PostgreSQL Database"
            },
            "mysql": {
                "icon": "🐬",
                "color": "#00758F", 
                "description": "MySQL Database"
            },
            "sqlserver": {
                "icon": "🏢",
                "color": "#CC2927",
                "description": "SQL Server Database"
            }
        }
        
        for db_name, db_schema in schemas.items():
            if "error" in db_schema:
                continue
                
            db_type = db_schema.get("database_type", "unknown")
            type_config = db_type_config.get(db_type, {"icon": "🗃️", "color": "#666666", "description": "Database"})
            
            # Build database node
            db_node = {
                "id": f"db_{db_name}",
                "name": db_name,
                "display_name": db_schema.get("display_name", db_name),
                "description": db_schema.get("description", ""),
                "type": db_type,
                "icon": type_config["icon"],
                "color": type_config["color"],
                "type_description": type_config["description"],
                "expanded": False,
                "schemas": {}
            }
            
            # For SQLite, we don't have separate schemas, so group by table type
            if db_type == "sqlite":
                # Categorize tables by type/purpose
                table_categories = self._categorize_sqlite_tables(db_schema.get("tables", {}))
                
                for category, tables in table_categories.items():
                    if not tables:
                        continue
                        
                    schema_node = {
                        "id": f"schema_{db_name}_{category}",
                        "name": category,
                        "display_name": category.replace("_", " ").title(),
                        "icon": self._get_category_icon(category),
                        "expanded": False,
                        "tables": {}
                    }
                    
                    for table_name, table_info in tables.items():
                        table_node = self._build_table_node(db_name, category, table_name, table_info)
                        schema_node["tables"][table_name] = table_node
                    
                    db_node["schemas"][category] = schema_node
            else:
                # For other database types, use actual schemas (simplified for demo)
                main_schema = {
                    "id": f"schema_{db_name}_main",
                    "name": "main",
                    "display_name": "Main Schema",
                    "icon": "📂",
                    "expanded": False,
                    "tables": {}
                }
                
                for table_name, table_info in db_schema.get("tables", {}).items():
                    table_node = self._build_table_node(db_name, "main", table_name, table_info)
                    main_schema["tables"][table_name] = table_node
                
                db_node["schemas"]["main"] = main_schema
            
            field_tree["databases"][db_name] = db_node
        
        return field_tree
    
    def _categorize_sqlite_tables(self, tables: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Categorize SQLite tables by their purpose/type."""
        categories = {
            "financial": {},
            "operational": {},
            "administrative": {},
            "reference": {}
        }
        
        # Keywords to categorize tables
        financial_keywords = ["budget", "fund", "account", "transaction", "payment", "revenue", "expense", "gl"]
        operational_keywords = ["water", "utility", "meter", "infrastructure", "asset", "vehicle", "equipment", "permit", "license", "inspection"]
        admin_keywords = ["employee", "payroll", "department", "user", "role", "audit", "log"]
        
        for table_name, table_info in tables.items():
            table_lower = table_name.lower()
            
            if any(keyword in table_lower for keyword in financial_keywords):
                categories["financial"][table_name] = table_info
            elif any(keyword in table_lower for keyword in operational_keywords):
                categories["operational"][table_name] = table_info
            elif any(keyword in table_lower for keyword in admin_keywords):
                categories["administrative"][table_name] = table_info
            else:
                categories["reference"][table_name] = table_info
        
        return categories
    
    def _get_category_icon(self, category: str) -> str:
        """Get icon for table category."""
        icons = {
            "financial": "💰",
            "operational": "⚙️", 
            "administrative": "👥",
            "reference": "📋"
        }
        return icons.get(category, "📂")
    
    def _build_table_node(self, db_name: str, schema_name: str, table_name: str, table_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build table node with columns."""
        
        table_node = {
            "id": f"table_{db_name}_{schema_name}_{table_name}",
            "name": table_name,
            "display_name": table_name.replace("_", " ").title(),
            "icon": "📊",
            "row_count": table_info.get("row_count", 0),
            "has_data": table_info.get("metadata", {}).get("has_data", False),
            "expanded": False,
            "columns": []
        }
        
        # Add columns
        for column_info in table_info.get("columns", []):
            column_node = {
                "id": f"col_{db_name}_{schema_name}_{table_name}_{column_info['column_name']}",
                "name": column_info["column_name"],
                "display_name": column_info["column_name"].replace("_", " ").title(),
                "data_type": column_info["data_type"],
                "nullable": column_info["nullable"],
                "is_primary_key": column_info.get("is_primary_key", False),
                "icon": self._get_column_icon(column_info["data_type"], column_info.get("is_primary_key", False)),
                "full_path": f"{db_name}.{schema_name}.{table_name}.{column_info['column_name']}",
                "searchable": True,
                "filterable": True
            }
            table_node["columns"].append(column_node)
        
        return table_node
    
    def _get_column_icon(self, data_type: str, is_primary_key: bool) -> str:
        """Get icon for column based on data type and properties."""
        if is_primary_key:
            return "🔑"
        
        data_type_lower = data_type.lower()
        
        if "int" in data_type_lower or "number" in data_type_lower:
            return "🔢"
        elif "text" in data_type_lower or "char" in data_type_lower or "string" in data_type_lower:
            return "📝"
        elif "date" in data_type_lower or "time" in data_type_lower:
            return "📅"
        elif "bool" in data_type_lower:
            return "☑️"
        elif "decimal" in data_type_lower or "float" in data_type_lower or "real" in data_type_lower:
            return "💯"
        else:
            return "📄"
    
    def test_database_connections(self) -> Dict[str, Any]:
        """Test connections to all databases."""
        try:
            results = self.db_manager.test_all_connections()
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Error testing database connections: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": {}
            }
    
    def get_database_field_suggestions(self, widget_type: str) -> Dict[str, Any]:
        """Get field suggestions for specific chart/widget types across all databases."""
        try:
            unified_catalog = self.db_manager.get_unified_field_catalog()
            
            # Field type preferences by widget type
            widget_preferences = {
                "bar_chart": {
                    "x_axis": ["text", "varchar", "char"],
                    "y_axis": ["integer", "decimal", "real", "numeric"]
                },
                "line_chart": {
                    "x_axis": ["date", "datetime", "timestamp"],
                    "y_axis": ["integer", "decimal", "real", "numeric"]
                },
                "pie_chart": {
                    "categories": ["text", "varchar", "char"],
                    "values": ["integer", "decimal", "real", "numeric"]
                },
                "table": {
                    "any": ["text", "varchar", "char", "integer", "decimal", "real", "date"]
                }
            }
            
            preferences = widget_preferences.get(widget_type, {"any": []})
            suggestions = {"databases": {}}
            
            # Group suggestions by database
            for field in unified_catalog:
                db_name = field["database"]
                if db_name not in suggestions["databases"]:
                    suggestions["databases"][db_name] = {
                        "display_name": field["database_display_name"],
                        "suggested_fields": []
                    }
                
                # Check if field matches preferences
                field_type_lower = field["data_type"].lower()
                is_suggested = False
                
                for pref_type, data_types in preferences.items():
                    if any(dt in field_type_lower for dt in data_types):
                        is_suggested = True
                        break
                
                if is_suggested or "any" in preferences:
                    suggestions["databases"][db_name]["suggested_fields"].append({
                        "table": field["table"],
                        "column": field["column"],
                        "data_type": field["data_type"],
                        "full_name": field["full_name"],
                        "display_name": field["display_name"]
                    })
            
            return {
                "success": True,
                "widget_type": widget_type,
                "suggestions": suggestions
            }
            
        except Exception as e:
            self.logger.error(f"Error getting field suggestions: {e}")
            return {
                "success": False,
                "error": str(e),
                "suggestions": {}
            }

# Global instance
enhanced_dashboard_api = EnhancedDashboardAPI()

# Streamlit API endpoints (if running in Streamlit context)
def api_get_multi_database_schema():
    """Streamlit endpoint for getting multi-database schema."""
    return enhanced_dashboard_api.get_multi_database_schema()

def api_test_database_connections():
    """Streamlit endpoint for testing database connections."""
    return enhanced_dashboard_api.test_database_connections()

def api_get_field_suggestions(widget_type: str):
    """Streamlit endpoint for getting field suggestions."""
    return enhanced_dashboard_api.get_database_field_suggestions(widget_type)