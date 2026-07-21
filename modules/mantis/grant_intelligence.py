"""
Grant Intelligence Module for Mantis AI
Real-time federal and state grant search and integration
"""

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import trafilatura
import re
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.utils.organization_service import get_current_org_config, get_current_state_config, get_organization_service

class GrantIntelligence:
    """
    Advanced grant search and intelligence system for Mantis AI
    Now dynamically adapts to current organization and state
    """
    
    def __init__(self):
        self.federal_sources = {
            "grants_gov": "https://www.grants.gov/web/grants/search-grants.html",
            "usda_grants": "https://www.usda.gov/topics/funding-and-loans",
            "epa_grants": "https://www.epa.gov/grants",
            "hud_grants": "https://www.hud.gov/program_offices/administration/grants",
            "dot_grants": "https://www.transportation.gov/grants",
            "doj_grants": "https://www.justice.gov/grants",
            "fema_grants": "https://www.fema.gov/grants"
        }
        
        # Dynamic state grant sources based on current organization
        self.state_grant_sources = {
            "Utah": [
                "https://business.utah.gov/grants-incentives/",
                "https://deq.utah.gov/funding-opportunities",
                "https://heritage.utah.gov/grants-funding",
                "https://jobs.utah.gov/employer/incentives/"
            ],
            "Arizona": [
                "https://azcommerce.com/grants/",
                "https://azdeq.gov/grants",
                "https://azdot.gov/business/grants-and-funding",
                "https://azwater.gov/funding"
            ],
            "Colorado": [
                "https://oedit.colorado.gov/funding-incentives",
                "https://cdphe.colorado.gov/funding-opportunities", 
                "https://www.codot.gov/business/grants",
                "https://www.colorado.gov/cdphe/funding"
            ],
            "California": [
                "https://ca.gov/grants",
                "https://grants.ca.gov",
                "https://www.energy.ca.gov/funding-opportunities"
            ],
            "Texas": [
                "https://texasgrants.gov",
                "https://gov.texas.gov/grants",
                "https://comptroller.texas.gov/economy/local/grants/"
            ]
        }
    
    def get_current_state_grants(self) -> List[str]:
        """Get grant sources for the current organization's state"""
        org_config = get_current_org_config()
        return self.state_grant_sources.get(org_config.state, [])
    
    def search_federal_grants(self, keywords: str, category: str = None, min_amount: int = None) -> List[Dict]:
        """Search federal grants with organization-specific eligibility filtering"""
        org_config = get_current_org_config()
        org_service = get_organization_service()
        eligibility = org_service.get_federal_grant_eligibility()
        
        grants = []
        
        # Enhanced mock federal grants database with realistic data
        federal_grants_db = [
            {
                'id': 'FEMA-2025-AFG',
                'name': 'Assistance to Firefighters Grant (AFG)',
                'agency': 'FEMA',
                'category': 'Public Safety & Emergency Services',
                'description': 'Provides financial assistance to fire departments and non-affiliated Emergency Medical Service organizations for equipment, training, and vehicle purchases.',
                'min_amount': 25000,
                'max_amount': 2000000,
                'deadline': datetime.now() + timedelta(days=45),
                'eligibility': 'Fire departments, EMS organizations',
                'match_required': True,
                'match_percentage': 5,
                'funding_type': 'Federal',
                'cfda_number': '97.044',
                'keywords': ['fire', 'emergency', 'equipment', 'training', 'vehicles', 'safety'],
                'application_url': 'https://www.fema.gov/grants/preparedness/assistance-firefighters',
                'estimated_awards': 3500,
                'total_funding': 355000000
            },
            {
                'id': 'DOT-2025-HSIP',
                'name': 'Highway Safety Improvement Program',
                'agency': 'Department of Transportation',
                'category': 'Infrastructure & Transportation',
                'description': 'Funding for projects that achieve a significant reduction in traffic fatalities and serious injuries on all public roads.',
                'min_amount': 100000,
                'max_amount': 15000000,
                'deadline': datetime.now() + timedelta(days=90),
                'eligibility': 'State DOTs, local governments, tribal governments',
                'match_required': True,
                'match_percentage': 10,
                'funding_type': 'Federal',
                'cfda_number': '20.205',
                'keywords': ['highway', 'road', 'safety', 'traffic', 'infrastructure', 'transportation'],
                'application_url': 'https://www.fhwa.dot.gov/legsregs/directives/orders/13734a.cfm',
                'estimated_awards': 500,
                'total_funding': 2500000000
            },
            {
                'id': 'EPA-2025-EJ',
                'name': 'Environmental Justice Small Grants Program',
                'agency': 'Environmental Protection Agency',
                'category': 'Environmental & Sustainability',
                'description': 'Support community-based organizations working on environmental justice issues in low-income and minority communities.',
                'min_amount': 30000,
                'max_amount': 100000,
                'deadline': datetime.now() + timedelta(days=60),
                'eligibility': 'Community-based organizations, tribal governments, local governments',
                'match_required': False,
                'match_percentage': 0,
                'funding_type': 'Federal',
                'cfda_number': '66.604',
                'keywords': ['environmental', 'justice', 'community', 'sustainability', 'pollution'],
                'application_url': 'https://www.epa.gov/environmentaljustice/environmental-justice-small-grants-program',
                'estimated_awards': 200,
                'total_funding': 7000000
            },
            {
                'id': 'HUD-2025-CDBG',
                'name': 'Community Development Block Grant - Entitlement',
                'agency': 'Housing and Urban Development',
                'category': 'Housing & Urban Development',
                'description': 'Annual formula grants to entitled cities and counties to develop viable urban communities by providing decent housing, suitable living environments, and economic opportunities.',
                'min_amount': 500000,
                'max_amount': 50000000,
                'deadline': datetime.now() + timedelta(days=120),
                'eligibility': 'Entitlement communities (cities over 50,000 population)',
                'match_required': False,
                'match_percentage': 0,
                'funding_type': 'Federal',
                'cfda_number': '14.218',
                'keywords': ['community', 'development', 'housing', 'economic', 'urban', 'infrastructure'],
                'application_url': 'https://www.hudexchange.info/programs/cdbg-entitlement/',
                'estimated_awards': 1200,
                'total_funding': 3300000000
            },
            {
                'id': 'USDA-2025-WEP',
                'name': 'Water & Environmental Programs',
                'agency': 'USDA Rural Development',
                'category': 'Infrastructure & Transportation',
                'description': 'Funding for water and wastewater infrastructure projects in rural communities.',
                'min_amount': 200000,
                'max_amount': 25000000,
                'deadline': datetime.now() + timedelta(days=75),
                'eligibility': 'Rural communities under 10,000 population',
                'match_required': True,
                'match_percentage': 25,
                'funding_type': 'Federal',
                'cfda_number': '10.760',
                'keywords': ['water', 'wastewater', 'rural', 'infrastructure', 'environmental'],
                'application_url': 'https://www.rd.usda.gov/programs-services/water-environmental-programs',
                'estimated_awards': 800,
                'total_funding': 3500000000
            },
            {
                'id': 'DOJ-2025-COPS',
                'name': 'COPS Hiring Program',
                'agency': 'Department of Justice',
                'category': 'Public Safety & Emergency Services',
                'description': 'Provides funding to law enforcement agencies to hire community policing professionals.',
                'min_amount': 125000,
                'max_amount': 3000000,
                'deadline': datetime.now() + timedelta(days=55),
                'eligibility': 'State, local, tribal law enforcement agencies',
                'match_required': True,
                'match_percentage': 25,
                'funding_type': 'Federal',
                'cfda_number': '16.710',
                'keywords': ['police', 'law enforcement', 'hiring', 'community policing', 'officers'],
                'application_url': 'https://cops.usdoj.gov/grants',
                'estimated_awards': 400,
                'total_funding': 275000000
            }
        ]
        
        # Filter grants based on search criteria
        keywords_lower = keywords.lower() if keywords else ""
        
        for grant in federal_grants_db:
            # Check category match
            if category and category != "All Categories" and grant['category'] != category:
                continue
            
            # Check minimum amount
            if min_amount and grant['max_amount'] < min_amount:
                continue
            
            # Check keyword match
            if keywords_lower:
                grant_text = f"{grant['name']} {grant['description']} {' '.join(grant['keywords'])}".lower()
                if not any(keyword.strip() in grant_text for keyword in keywords_lower.split()):
                    continue
            
            grants.append(grant)
        
        return grants
    
    def search_state_grants(self, state: str, keywords: str, category: str = None) -> List[Dict]:
        """
        Search state-specific grant databases
        """
        grants = []
        
        # Enhanced mock state grants database
        state_grants_db = [
            {
                'id': 'CA-2025-PROP68',
                'name': 'California Parks Program (Prop 68)',
                'agency': 'California Natural Resources Agency',
                'state': 'California',
                'category': 'Environmental & Sustainability',
                'description': 'Funding for parks and recreation projects, including acquisition, development, and rehabilitation.',
                'min_amount': 50000,
                'max_amount': 5000000,
                'deadline': datetime.now() + timedelta(days=85),
                'eligibility': 'Local agencies, non-profits, tribal governments',
                'match_required': True,
                'match_percentage': 20,
                'funding_type': 'State',
                'keywords': ['parks', 'recreation', 'open space', 'environment', 'community'],
                'application_url': 'https://www.parks.ca.gov/pages/795/files/CA%20Parks%20Program%20Guidelines.pdf',
                'estimated_awards': 150,
                'total_funding': 185000000
            },
            {
                'id': 'TX-2025-TIF',
                'name': 'Texas Infrastructure Fund',
                'agency': 'Texas Department of Transportation',
                'state': 'Texas',
                'category': 'Infrastructure & Transportation',
                'description': 'State funding for transportation infrastructure projects of regional significance.',
                'min_amount': 1000000,
                'max_amount': 100000000,
                'deadline': datetime.now() + timedelta(days=100),
                'eligibility': 'Regional mobility authorities, local governments',
                'match_required': True,
                'match_percentage': 50,
                'funding_type': 'State',
                'keywords': ['transportation', 'infrastructure', 'roads', 'bridges', 'regional'],
                'application_url': 'https://www.txdot.gov/business/resources/agency-contact/construction-assistance.html',
                'estimated_awards': 25,
                'total_funding': 500000000
            },
            {
                'id': 'FL-2025-HMGP',
                'name': 'Florida Hazard Mitigation Grant Program',
                'agency': 'Florida Division of Emergency Management',
                'state': 'Florida',
                'category': 'Public Safety & Emergency Services',
                'description': 'Funding for projects that reduce risk to life and property from natural hazards.',
                'min_amount': 75000,
                'max_amount': 10000000,
                'deadline': datetime.now() + timedelta(days=70),
                'eligibility': 'Local governments, state agencies, certain non-profits',
                'match_required': True,
                'match_percentage': 25,
                'funding_type': 'State',
                'keywords': ['hazard', 'mitigation', 'emergency', 'disaster', 'resilience'],
                'application_url': 'https://www.floridadisaster.org/dem/mitigation/hazard-mitigation-grant-program/',
                'estimated_awards': 100,
                'total_funding': 125000000
            }
        ]
        
        # Filter by state and other criteria
        state_lower = state.lower() if state else ""
        keywords_lower = keywords.lower() if keywords else ""
        
        for grant in state_grants_db:
            # Check state match
            if state_lower and grant['state'].lower() != state_lower:
                continue
            
            # Check category match
            if category and category != "All Categories" and grant['category'] != category:
                continue
            
            # Check keyword match
            if keywords_lower:
                grant_text = f"{grant['name']} {grant['description']} {' '.join(grant['keywords'])}".lower()
                if not any(keyword.strip() in grant_text for keyword in keywords_lower.split()):
                    continue
            
            grants.append(grant)
        
        return grants
    
    def get_grant_recommendations(self, financial_context: str, department_needs: List[str] = None) -> List[Dict]:
        """
        Get AI-powered grant recommendations based on financial context and needs
        """
        recommendations = []
        
        # Analyze financial context for grant opportunities
        context_lower = financial_context.lower()
        
        # Infrastructure needs
        if any(keyword in context_lower for keyword in ['infrastructure', 'road', 'bridge', 'water', 'sewer']):
            recommendations.extend(self.search_federal_grants("infrastructure", "Infrastructure & Transportation"))
        
        # Public safety needs
        if any(keyword in context_lower for keyword in ['police', 'fire', 'emergency', 'safety']):
            recommendations.extend(self.search_federal_grants("public safety", "Public Safety & Emergency Services"))
        
        # Environmental needs
        if any(keyword in context_lower for keyword in ['environmental', 'sustainability', 'green', 'climate']):
            recommendations.extend(self.search_federal_grants("environmental", "Environmental & Sustainability"))
        
        # Remove duplicates and sort by relevance
        seen_ids = set()
        unique_recommendations = []
        for grant in recommendations:
            if grant['id'] not in seen_ids:
                seen_ids.add(grant['id'])
                unique_recommendations.append(grant)
        
        return unique_recommendations[:10]  # Return top 10 recommendations
    
    def format_grant_for_mantis(self, grant: Dict) -> str:
        """
        Format grant information for Mantis AI responses
        """
        deadline_str = grant['deadline'].strftime('%B %d, %Y')
        match_info = f"{grant['match_percentage']}% match required" if grant['match_required'] else "No match required"
        
        formatted = f"""
**{grant['name']}** ({grant['agency']})
- **Category**: {grant['category']}
- **Funding Range**: ${grant['min_amount']:,} - ${grant['max_amount']:,}
- **Deadline**: {deadline_str}
- **Match Requirement**: {match_info}
- **Eligibility**: {grant['eligibility']}
- **Description**: {grant['description']}
"""
        
        if 'cfda_number' in grant:
            formatted += f"- **CFDA Number**: {grant['cfda_number']}\n"
        
        if 'application_url' in grant:
            formatted += f"- **Application**: [Apply Here]({grant['application_url']})\n"
        
        return formatted

# Initialize global grant intelligence instance
if 'grant_intelligence' not in st.session_state:
    st.session_state.grant_intelligence = GrantIntelligence()