"""
Scenario Intelligence Module for Mantis AI
Provides comprehensive access to saved scenarios and scenario analysis capabilities
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

class ScenarioIntelligence:
    """
    Advanced scenario analysis and intelligence system for Mantis AI
    """
    
    def __init__(self):
        self.db_path = "databases/core/caselle_gl0_mock.db"
    
    def get_connection(self):
        """Get database connection"""
        try:
            return sqlite3.connect(self.db_path)
        except Exception as e:
            st.error(f"Database connection error: {e}")
            return None
    
    def get_all_scenarios(self, limit: int = 20) -> List[Dict]:
        """Get all saved scenarios with comprehensive details"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            # Get scenarios with full funding details
            cursor.execute("""
                SELECT s.id, s.name, s.total_cost, s.tax_revenue, s.grant_funding, 
                       s.private_investment, s.bonds_needed, s.creation_date, s.project_id 
                FROM scenarios s 
                ORDER BY s.creation_date DESC 
                LIMIT ?
            """, (limit,))
            
            scenarios = []
            for row in cursor.fetchall():
                scenario_id = row[0]
                
                # Get department allocations for this scenario
                cursor.execute("""
                    SELECT d.name, sda.allocation_amount 
                    FROM scenario_department_allocations sda 
                    JOIN departments d ON sda.department_id = d.id 
                    WHERE sda.scenario_id = ?
                """, (scenario_id,))
                
                department_allocations = {}
                total_reallocation = 0
                for dept_row in cursor.fetchall():
                    dept_name = dept_row[0]
                    amount = dept_row[1] or 0
                    department_allocations[dept_name] = amount
                    total_reallocation += amount
                
                # Get project information
                project_name = "Unknown Project"
                if row[8]:  # project_id exists
                    cursor.execute("SELECT name FROM projects WHERE id = ?", (row[8],))
                    proj_result = cursor.fetchone()
                    if proj_result:
                        project_name = proj_result[0]
                
                scenario = {
                    "id": scenario_id,
                    "name": row[1] or f"Scenario {scenario_id}",
                    "project_name": project_name,
                    "total_cost": row[2] or 0,
                    "tax_revenue": row[3] or 0,
                    "grant_funding": row[4] or 0,
                    "private_investment": row[5] or 0,
                    "bonds_needed": row[6] or 0,
                    "creation_date": row[7],
                    "department_allocations": department_allocations,
                    "total_reallocation": total_reallocation,
                    "funding_sources": {
                        "Tax Revenue": row[3] or 0,
                        "Grant Funding": row[4] or 0,
                        "Private Investment": row[5] or 0,
                        "Bonds": row[6] or 0
                    }
                }
                
                # Calculate additional metrics
                scenario["total_funding"] = sum(scenario["funding_sources"].values())
                scenario["grant_percentage"] = (scenario["grant_funding"] / scenario["total_funding"] * 100) if scenario["total_funding"] > 0 else 0
                scenario["department_count"] = len(department_allocations)
                
                scenarios.append(scenario)
            
            return scenarios
            
        except Exception as e:
            st.error(f"Error fetching scenarios: {e}")
            return []
        finally:
            conn.close()
    
    def get_scenario_by_id(self, scenario_id: int) -> Optional[Dict]:
        """Get detailed information for a specific scenario"""
        scenarios = self.get_all_scenarios()
        for scenario in scenarios:
            if scenario["id"] == scenario_id:
                return scenario
        return None
    
    def get_scenario_by_name(self, scenario_name: str) -> Optional[Dict]:
        """Get detailed information for a scenario by name"""
        scenarios = self.get_all_scenarios()
        for scenario in scenarios:
            if scenario["name"].lower() == scenario_name.lower():
                return scenario
        return None
    
    def analyze_scenario_funding_mix(self, scenario: Dict) -> Dict:
        """Analyze the funding mix of a scenario"""
        analysis = {
            "total_funding": scenario["total_funding"],
            "funding_breakdown": {},
            "risk_assessment": {},
            "recommendations": []
        }
        
        # Calculate funding percentages
        for source, amount in scenario["funding_sources"].items():
            if scenario["total_funding"] > 0:
                percentage = (amount / scenario["total_funding"]) * 100
                analysis["funding_breakdown"][source] = {
                    "amount": amount,
                    "percentage": percentage
                }
        
        # Risk assessment
        grant_pct = analysis["funding_breakdown"].get("Grant Funding", {}).get("percentage", 0)
        bonds_pct = analysis["funding_breakdown"].get("Bonds", {}).get("percentage", 0)
        private_pct = analysis["funding_breakdown"].get("Private Investment", {}).get("percentage", 0)
        
        if grant_pct > 50:
            analysis["risk_assessment"]["grant_dependency"] = "High - Over 50% grant dependent"
            analysis["recommendations"].append("Consider diversifying funding sources to reduce grant dependency risk")
        elif grant_pct > 30:
            analysis["risk_assessment"]["grant_dependency"] = "Moderate - 30-50% grant dependent"
        else:
            analysis["risk_assessment"]["grant_dependency"] = "Low - Less than 30% grant dependent"
        
        if bonds_pct > 40:
            analysis["risk_assessment"]["debt_burden"] = "High - Over 40% debt financed"
            analysis["recommendations"].append("High debt burden may impact future borrowing capacity")
        elif bonds_pct > 20:
            analysis["risk_assessment"]["debt_burden"] = "Moderate - 20-40% debt financed"
        else:
            analysis["risk_assessment"]["debt_burden"] = "Low - Less than 20% debt financed"
        
        return analysis
    
    def compare_scenarios(self, scenario_ids: List[int]) -> Dict:
        """Compare multiple scenarios"""
        scenarios = []
        for scenario_id in scenario_ids:
            scenario = self.get_scenario_by_id(scenario_id)
            if scenario:
                scenarios.append(scenario)
        
        if len(scenarios) < 2:
            return {"error": "Need at least 2 scenarios to compare"}
        
        comparison = {
            "scenarios": scenarios,
            "funding_comparison": {},
            "cost_comparison": {},
            "department_comparison": {},
            "recommendations": []
        }
        
        # Compare funding sources
        for source in ["tax_revenue", "grant_funding", "private_investment", "bonds_needed"]:
            amounts = [s[source] for s in scenarios]
            comparison["funding_comparison"][source] = {
                "min": min(amounts),
                "max": max(amounts),
                "avg": sum(amounts) / len(amounts),
                "scenarios": [(s["name"], s[source]) for s in scenarios]
            }
        
        # Compare total costs
        costs = [s["total_cost"] for s in scenarios]
        comparison["cost_comparison"] = {
            "min_cost": min(costs),
            "max_cost": max(costs),
            "cost_range": max(costs) - min(costs),
            "avg_cost": sum(costs) / len(costs)
        }
        
        return comparison
    
    def get_scenario_impact_analysis(self, scenario: Dict) -> Dict:
        """Analyze the potential impact of a scenario"""
        analysis = {
            "financial_impact": {},
            "departmental_impact": {},
            "funding_sustainability": {},
            "implementation_complexity": {}
        }
        
        # Financial impact analysis
        analysis["financial_impact"]["total_investment"] = scenario["total_funding"]
        analysis["financial_impact"]["annual_debt_service"] = scenario["bonds_needed"] * 0.06 if scenario["bonds_needed"] > 0 else 0  # Assume 6% interest
        analysis["financial_impact"]["grant_match_required"] = scenario["grant_funding"] * 0.25 if scenario["grant_funding"] > 0 else 0  # Assume 25% match
        
        # Departmental impact
        if scenario["department_allocations"]:
            total_dept_allocation = sum(scenario["department_allocations"].values())
            analysis["departmental_impact"]["departments_affected"] = len(scenario["department_allocations"])
            analysis["departmental_impact"]["average_allocation"] = total_dept_allocation / len(scenario["department_allocations"])
            analysis["departmental_impact"]["largest_allocation"] = max(scenario["department_allocations"].values()) if scenario["department_allocations"] else 0
            analysis["departmental_impact"]["most_impacted_dept"] = max(scenario["department_allocations"], key=scenario["department_allocations"].get) if scenario["department_allocations"] else None
        
        # Implementation complexity
        complexity_factors = 0
        if scenario["grant_funding"] > 0:
            complexity_factors += 1
        if scenario["private_investment"] > 0:
            complexity_factors += 1
        if len(scenario["department_allocations"]) > 3:
            complexity_factors += 1
        if scenario["bonds_needed"] > 1000000:  # > $1M in bonds
            complexity_factors += 1
        
        complexity_levels = ["Low", "Low-Medium", "Medium", "Medium-High", "High"]
        analysis["implementation_complexity"]["level"] = complexity_levels[min(complexity_factors, 4)]
        analysis["implementation_complexity"]["factors"] = complexity_factors
        
        return analysis
    
    def format_scenario_for_mantis(self, scenario: Dict, include_analysis: bool = True) -> str:
        """Format scenario information for Mantis AI responses"""
        creation_date = scenario["creation_date"]
        if isinstance(creation_date, str):
            try:
                date_obj = datetime.fromisoformat(creation_date)
                date_str = date_obj.strftime("%B %d, %Y")
            except:
                date_str = creation_date
        else:
            date_str = str(creation_date)
        
        formatted = f"""
**{scenario['name']}** (ID: {scenario['id']})
- **Project**: {scenario['project_name']}
- **Total Cost**: ${scenario['total_cost']:,}
- **Created**: {date_str}

**Funding Breakdown**:
- Tax Revenue: ${scenario['tax_revenue']:,} ({scenario['tax_revenue']/scenario['total_funding']*100:.1f}%)
- Grant Funding: ${scenario['grant_funding']:,} ({scenario['grant_funding']/scenario['total_funding']*100:.1f}%)
- Private Investment: ${scenario['private_investment']:,} ({scenario['private_investment']/scenario['total_funding']*100:.1f}%)
- Bonds Needed: ${scenario['bonds_needed']:,} ({scenario['bonds_needed']/scenario['total_funding']*100:.1f}%)

**Department Allocations** ({scenario['department_count']} departments affected):"""
        
        if scenario["department_allocations"]:
            for dept, amount in scenario["department_allocations"].items():
                formatted += f"\n- {dept}: ${amount:,}"
        else:
            formatted += "\n- No specific department allocations"
        
        if include_analysis:
            analysis = self.analyze_scenario_funding_mix(scenario)
            formatted += f"\n\n**Risk Assessment**:"
            for risk_type, assessment in analysis["risk_assessment"].items():
                formatted += f"\n- {risk_type.replace('_', ' ').title()}: {assessment}"
            
            if analysis["recommendations"]:
                formatted += f"\n\n**Recommendations**:"
                for rec in analysis["recommendations"]:
                    formatted += f"\n- {rec}"
        
        return formatted
    
    def search_scenarios(self, query: str) -> List[Dict]:
        """Search scenarios by name, project, or keywords"""
        all_scenarios = self.get_all_scenarios()
        query_lower = query.lower()
        
        matching_scenarios = []
        for scenario in all_scenarios:
            # Search in scenario name, project name, and department allocations
            searchable_text = f"{scenario['name']} {scenario['project_name']} {' '.join(scenario['department_allocations'].keys())}".lower()
            if query_lower in searchable_text:
                matching_scenarios.append(scenario)
        
        return matching_scenarios

# Initialize global scenario intelligence instance
if 'scenario_intelligence' not in st.session_state:
    st.session_state.scenario_intelligence = ScenarioIntelligence()