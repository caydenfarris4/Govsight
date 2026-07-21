"""
BI Sandbox API endpoints for ECharts dashboard

This module provides API endpoints for the ECharts dashboard to fetch fields and data.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json

router = APIRouter()

@router.get("/api/bi-sandbox/fields")
async def get_fields():
    """Get available fields for the BI Sandbox dashboard"""
    try:
        # Return sample fields for demonstration
        fields = [
            # Dimensions
            {"name": "Department", "type": "text", "category": "dimension", "source": "GL", "display_name": "Department"},
            {"name": "Account", "type": "text", "category": "dimension", "source": "GL", "display_name": "Account"},
            {"name": "Category", "type": "text", "category": "dimension", "source": "GL", "display_name": "Category"},
            {"name": "Vendor", "type": "text", "category": "dimension", "source": "GL", "display_name": "Vendor"},
            {"name": "Project", "type": "text", "category": "dimension", "source": "GL", "display_name": "Project"},
            {"name": "Location", "type": "text", "category": "dimension", "source": "GL", "display_name": "Location"},
            {"name": "Status", "type": "text", "category": "dimension", "source": "GL", "display_name": "Status"},
            {"name": "Type", "type": "text", "category": "dimension", "source": "GL", "display_name": "Type"},
            
            # Measures
            {"name": "Budget", "type": "number", "category": "measure", "source": "GL", "display_name": "Budget"},
            {"name": "Actual", "type": "number", "category": "measure", "source": "GL", "display_name": "Actual"},
            {"name": "Variance", "type": "number", "category": "measure", "source": "GL", "display_name": "Variance"},
            {"name": "Revenue", "type": "number", "category": "measure", "source": "GL", "display_name": "Revenue"},
            {"name": "Expenses", "type": "number", "category": "measure", "source": "GL", "display_name": "Expenses"},
            {"name": "Count", "type": "number", "category": "measure", "source": "GL", "display_name": "Count"},
            {"name": "Amount", "type": "number", "category": "measure", "source": "GL", "display_name": "Amount"},
            {"name": "Percentage", "type": "number", "category": "measure", "source": "GL", "display_name": "Percentage"},
            
            # Date Fields
            {"name": "Date", "type": "date", "category": "date", "source": "GL", "display_name": "Date"},
            {"name": "Month", "type": "date", "category": "date", "source": "GL", "display_name": "Month"},
            {"name": "Quarter", "type": "date", "category": "date", "source": "GL", "display_name": "Quarter"},
            {"name": "Year", "type": "date", "category": "date", "source": "GL", "display_name": "Year"},
            {"name": "Created", "type": "datetime", "category": "date", "source": "GL", "display_name": "Created Date"},
            {"name": "Updated", "type": "datetime", "category": "date", "source": "GL", "display_name": "Updated Date"}
        ]
        
        return fields
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/bi-sandbox/data")
async def get_dashboard_data(chart_type: str = "bar", config: str = "{}"):
    """Get data for a specific chart type and configuration"""
    try:
        # Parse configuration
        config_dict = json.loads(config)
        
        # Return sample data based on chart type
        if chart_type == "bar":
            return {
                "categories": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "values": [120, 200, 150, 80, 70, 110]
            }
        elif chart_type == "pie":
            return {
                "pieData": [
                    {"value": 335, "name": "Direct"},
                    {"value": 310, "name": "Email"},
                    {"value": 234, "name": "Ads"},
                    {"value": 1548, "name": "Search"}
                ]
            }
        elif chart_type == "line":
            return {
                "categories": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "values": [120, 200, 150, 80, 70, 110]
            }
        else:
            return {"data": []}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))