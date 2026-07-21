"""
Advanced Grant Intelligence & Legislative Impact Analysis
Enhanced grant discovery with AI-powered eligibility matching and legislative analysis
"""

import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import trafilatura
from dataclasses import dataclass
import re

from modules.ai_engine.secure_ai_base import SecureAIBase, GOVSIGHT_AI_SECURITY

@dataclass
class GrantOpportunity:
    """Enhanced grant opportunity data structure"""
    grant_id: str
    title: str
    agency: str
    category: str
    description: str
    min_amount: int
    max_amount: int
    deadline: datetime
    eligibility_criteria: List[str]
    match_required: bool
    match_percentage: float
    cfda_number: str
    keywords: List[str]
    application_url: str
    estimated_awards: int
    total_funding: int
    eligibility_score: float = 0.0
    ai_analysis: str = ""
    legislative_impact: str = ""

class AdvancedGrantIntelligence(SecureAIBase):
    """
    Advanced AI-powered grant discovery and legislative analysis system
    
    CAPABILITIES:
    - Intelligent grant matching based on municipal profile
    - AI-powered eligibility assessment
    - Legislative impact analysis
    - Automated grant application guidance
    - Risk assessment and funding probability scoring
    """
    
    def __init__(self):
        super().__init__("AdvancedGrantIntelligence", GOVSIGHT_AI_SECURITY)
        
        self.federal_agencies = {
            "FEMA": {"focus": "Emergency Management", "typical_amounts": [25000, 5000000]},
            "DOT": {"focus": "Transportation Infrastructure", "typical_amounts": [100000, 50000000]},
            "EPA": {"focus": "Environmental Protection", "typical_amounts": [30000, 2000000]},
            "HUD": {"focus": "Housing & Urban Development", "typical_amounts": [500000, 100000000]},
            "USDA": {"focus": "Rural Development", "typical_amounts": [50000, 10000000]},
            "DOJ": {"focus": "Public Safety", "typical_amounts": [75000, 3000000]},
            "CDC": {"focus": "Public Health", "typical_amounts": [40000, 5000000]}
        }
        
        # Enhanced grant database with current opportunities
        self.grant_database = self._build_comprehensive_grant_database()
    
    def _build_comprehensive_grant_database(self) -> List[GrantOpportunity]:
        """Build comprehensive, realistic grant database"""
        grants = []
        
        # FEMA Grants
        grants.extend([
            GrantOpportunity(
                grant_id="FEMA-2025-AFG",
                title="Assistance to Firefighters Grant (AFG)",
                agency="FEMA",
                category="Public Safety & Emergency Services",
                description="Provides financial assistance to fire departments and non-affiliated EMS organizations for equipment, training, vehicle purchases, and facility modifications.",
                min_amount=25000,
                max_amount=2000000,
                deadline=datetime.now() + timedelta(days=45),
                eligibility_criteria=[
                    "Fire departments and EMS organizations",
                    "Must serve population under 1 million",
                    "Must demonstrate financial need",
                    "Cannot have received AFG grant in past 3 years for same category"
                ],
                match_required=True,
                match_percentage=5,
                cfda_number="97.044",
                keywords=["fire", "emergency", "equipment", "training", "vehicles", "safety"],
                application_url="https://www.fema.gov/grants/preparedness/assistance-firefighters",
                estimated_awards=3500,
                total_funding=355000000
            ),
            GrantOpportunity(
                grant_id="FEMA-2025-EMPG",
                title="Emergency Management Performance Grant",
                agency="FEMA",
                category="Emergency Management",
                description="Support state and local emergency management capabilities including planning, training, exercises, and personnel.",
                min_amount=50000,
                max_amount=1500000,
                deadline=datetime.now() + timedelta(days=75),
                eligibility_criteria=[
                    "State and local emergency management agencies",
                    "Must have approved Emergency Operations Plan",
                    "50% cost match required"
                ],
                match_required=True,
                match_percentage=50,
                cfda_number="97.042",
                keywords=["emergency management", "planning", "training", "exercises"],
                application_url="https://www.fema.gov/grants/preparedness/emergency-management-performance",
                estimated_awards=56,
                total_funding=355000000
            )
        ])
        
        # DOT Grants
        grants.extend([
            GrantOpportunity(
                grant_id="DOT-2025-HSIP",
                title="Highway Safety Improvement Program",
                agency="DOT",
                category="Infrastructure & Transportation",
                description="Funding for projects that achieve significant reduction in traffic fatalities and serious injuries on all public roads.",
                min_amount=100000,
                max_amount=15000000,
                deadline=datetime.now() + timedelta(days=90),
                eligibility_criteria=[
                    "State DOTs, local governments, tribal governments",
                    "Must demonstrate safety improvement potential",
                    "10% local match required"
                ],
                match_required=True,
                match_percentage=10,
                cfda_number="20.205",
                keywords=["highway", "road", "safety", "traffic", "infrastructure", "fatalities"],
                application_url="https://www.fhwa.dot.gov/legsregs/directives/orders/13734a.cfm",
                estimated_awards=500,
                total_funding=2500000000
            ),
            GrantOpportunity(
                grant_id="DOT-2025-TIGER",
                title="Transportation Investment Generating Economic Recovery (TIGER)",
                agency="DOT",
                category="Infrastructure & Transportation",
                description="Capital investments in surface transportation infrastructure with significant local or regional impact.",
                min_amount=5000000,
                max_amount=25000000,
                deadline=datetime.now() + timedelta(days=120),
                eligibility_criteria=[
                    "State and local governments",
                    "Metropolitan planning organizations",
                    "Must demonstrate economic development impact",
                    "No federal match required"
                ],
                match_required=False,
                match_percentage=0,
                cfda_number="20.933",
                keywords=["transportation", "infrastructure", "economic development", "multimodal"],
                application_url="https://www.transportation.gov/tiger",
                estimated_awards=65,
                total_funding=1500000000
            )
        ])
        
        # EPA Grants
        grants.extend([
            GrantOpportunity(
                grant_id="EPA-2025-EJ",
                title="Environmental Justice Small Grants Program",
                agency="EPA",
                category="Environmental & Sustainability",
                description="Support community-based organizations working on environmental justice issues in low-income and minority communities.",
                min_amount=30000,
                max_amount=100000,
                deadline=datetime.now() + timedelta(days=60),
                eligibility_criteria=[
                    "Community-based organizations",
                    "Tribal governments",
                    "Local governments serving EJ communities"
                ],
                match_required=False,
                match_percentage=0,
                cfda_number="66.604",
                keywords=["environmental justice", "community", "sustainability", "pollution"],
                application_url="https://www.epa.gov/environmentaljustice/environmental-justice-small-grants-program",
                estimated_awards=200,
                total_funding=7000000
            ),
            GrantOpportunity(
                grant_id="EPA-2025-WIFIA",
                title="Water Infrastructure Finance and Innovation Act (WIFIA)",
                agency="EPA",
                category="Water Infrastructure",
                description="Low-cost supplemental credit assistance for regionally or nationally significant water infrastructure projects.",
                min_amount=20000000,
                max_amount=500000000,
                deadline=datetime.now() + timedelta(days=150),
                eligibility_criteria=[
                    "Municipal water utilities",
                    "State infrastructure financing authorities",
                    "Project must be over $20M in eligible costs"
                ],
                match_required=False,
                match_percentage=0,
                cfda_number="66.849",
                keywords=["water", "infrastructure", "utility", "treatment", "distribution"],
                application_url="https://www.epa.gov/wifia",
                estimated_awards=45,
                total_funding=6000000000
            )
        ])
        
        return grants
    
    def analyze_municipal_profile(self, city_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze municipal profile to determine grant eligibility patterns
        
        Args:
            city_data: Dictionary containing municipal information
            
        Returns:
            Profile analysis with grant recommendations
        """
        profile = {
            'population': city_data.get('population', 50000),
            'budget_size': city_data.get('annual_budget', 25000000),
            'department_priorities': city_data.get('departments', []),
            'recent_projects': city_data.get('projects', []),
            'geographic_region': city_data.get('region', 'western'),
            'demographic_info': city_data.get('demographics', {}),
            'infrastructure_needs': city_data.get('infrastructure', [])
        }
        
        # AI-powered profile analysis
        analysis_prompt = f"""
        Analyze this municipal profile for federal grant opportunities:
        
        Population: {profile['population']:,}
        Annual Budget: ${profile['budget_size']:,}
        Key Departments: {', '.join(profile['department_priorities'])}
        Recent Projects: {', '.join(profile['recent_projects'])}
        Region: {profile['geographic_region']}
        Infrastructure Needs: {', '.join(profile['infrastructure_needs'])}
        
        Provide:
        1. Top 3 grant categories this municipality should prioritize
        2. Competitive advantages for grant applications
        3. Potential challenges or gaps to address
        4. Recommended application strategy
        """
        
        ai_response = self.secure_ai_request(
            analysis_prompt, 
            "municipal_profile_analysis",
            data_sources=["municipal_data"]
        )
        
        return {
            'profile': profile,
            'ai_analysis': ai_response.get('response', 'Analysis unavailable'),
            'success': ai_response.get('success', False)
        }
    
    def intelligent_grant_matching(self, municipal_profile: Dict[str, Any], 
                                 priority_areas: List[str] = None) -> List[GrantOpportunity]:
        """
        AI-powered grant matching based on municipal profile and priorities
        """
        if priority_areas is None:
            priority_areas = ["public safety", "infrastructure", "environmental"]
        
        # Score each grant against municipal profile
        scored_grants = []
        
        for grant in self.grant_database:
            score = 0.0
            
            # Population-based scoring
            population = municipal_profile.get('population', 50000)
            if population < 100000 and any(keyword in ['small', 'rural', 'community'] for keyword in grant.keywords):
                score += 0.2
            elif population > 100000 and any(keyword in ['urban', 'metropolitan'] for keyword in grant.keywords):
                score += 0.2
            
            # Budget compatibility
            budget_size = municipal_profile.get('budget_size', 25000000)
            if grant.min_amount <= budget_size * 0.1:  # Grant is reasonable size relative to budget
                score += 0.15
            
            # Priority area matching
            for priority in priority_areas:
                if any(priority.lower() in keyword.lower() for keyword in grant.keywords):
                    score += 0.25
            
            # Department alignment
            departments = municipal_profile.get('department_priorities', [])
            dept_keywords = ['fire', 'police', 'public works', 'parks', 'water', 'sewer']
            for dept in departments:
                for keyword in dept_keywords:
                    if keyword.lower() in dept.lower() and keyword in grant.keywords:
                        score += 0.1
            
            # Infrastructure needs alignment
            infrastructure_needs = municipal_profile.get('infrastructure_needs', [])
            for need in infrastructure_needs:
                if any(need.lower() in keyword.lower() for keyword in grant.keywords):
                    score += 0.15
            
            # Deadline urgency (prefer grants with reasonable deadlines)
            days_to_deadline = (grant.deadline - datetime.now()).days
            if 30 <= days_to_deadline <= 120:  # Sweet spot for application preparation
                score += 0.1
            elif days_to_deadline < 30:
                score -= 0.1  # Too rushed
            
            grant.eligibility_score = min(score, 1.0)  # Cap at 1.0
            
            # Add AI analysis for high-scoring grants
            if score > 0.5:
                grant.ai_analysis = self._generate_grant_analysis(grant, municipal_profile)
            
            scored_grants.append(grant)
        
        # Sort by eligibility score and return top matches
        scored_grants.sort(key=lambda x: x.eligibility_score, reverse=True)
        return scored_grants
    
    def _generate_grant_analysis(self, grant: GrantOpportunity, 
                               municipal_profile: Dict[str, Any]) -> str:
        """Generate AI-powered grant analysis and application guidance"""
        
        analysis_prompt = f"""
        Analyze this grant opportunity for a municipality:
        
        GRANT: {grant.title} ({grant.agency})
        Amount: ${grant.min_amount:,} - ${grant.max_amount:,}
        Category: {grant.category}
        Deadline: {grant.deadline.strftime('%B %d, %Y')}
        Match Required: {grant.match_percentage}% if {grant.match_required}
        
        MUNICIPALITY PROFILE:
        Population: {municipal_profile.get('population', 'Unknown'):,}
        Annual Budget: ${municipal_profile.get('budget_size', 0):,}
        Departments: {', '.join(municipal_profile.get('department_priorities', []))}
        
        Provide:
        1. Eligibility assessment and competitive positioning
        2. Key application requirements and deadlines
        3. Recommended project scope and budget allocation
        4. Success probability and risk factors
        5. Application strategy and tips
        """
        
        ai_response = self.secure_ai_request(
            analysis_prompt,
            "grant_analysis",
            data_sources=["grant_database", "municipal_profile"]
        )
        
        return ai_response.get('response', 'Analysis unavailable')
    
    def legislative_impact_analysis(self, legislation_text: str, 
                                  municipal_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze potential legislative impact on municipal finances
        
        Args:
            legislation_text: Text of proposed legislation
            municipal_context: Municipal profile and financial data
            
        Returns:
            Comprehensive impact analysis
        """
        
        # Validate and sanitize legislation text
        if len(legislation_text) > 50000:  # Reasonable limit for legislation analysis
            return {
                'success': False,
                'error': 'Legislation text too long for analysis (max 50,000 characters)'
            }
        
        analysis_prompt = f"""
        Analyze the fiscal impact of this proposed legislation on municipal government:
        
        LEGISLATION TEXT:
        {legislation_text[:10000]}{'...' if len(legislation_text) > 10000 else ''}
        
        MUNICIPAL CONTEXT:
        Population: {municipal_context.get('population', 'Unknown'):,}
        Annual Budget: ${municipal_context.get('budget_size', 0):,}
        Key Revenue Sources: {', '.join(municipal_context.get('revenue_sources', ['property tax', 'sales tax']))}
        Major Expenditures: {', '.join(municipal_context.get('major_expenses', ['personnel', 'infrastructure']))}
        
        Provide detailed analysis:
        
        1. DIRECT FISCAL IMPACTS:
           - New revenue requirements or restrictions
           - Additional expenditure mandates
           - Changes to existing funding sources
        
        2. IMPLEMENTATION COSTS:
           - Administrative costs to comply
           - Technology or infrastructure upgrades needed
           - Staff training or hiring requirements
        
        3. TIMELINE AND PHASING:
           - When impacts will begin
           - Phased implementation requirements
           - Critical deadlines for compliance
        
        4. RISK ASSESSMENT:
           - High, medium, low impact probability
           - Potential cost ranges (conservative and aggressive estimates)
           - Compliance risks and penalties
        
        5. STRATEGIC RECOMMENDATIONS:
           - Immediate actions to prepare
           - Budget planning considerations
           - Opportunities to leverage for grants or partnerships
        
        Format as a clear, professional analysis suitable for city council presentation.
        """
        
        ai_response = self.secure_ai_request(
            analysis_prompt,
            "legislative_impact_analysis",
            data_sources=["legislation", "municipal_data"],
            max_tokens=3000
        )
        
        if ai_response.get('success'):
            # Parse and structure the response
            analysis_text = ai_response.get('response', '')
            
            return {
                'success': True,
                'analysis': analysis_text,
                'generated_at': datetime.now().isoformat(),
                'municipal_context': municipal_context,
                'legislation_length': len(legislation_text),
                'security_status': ai_response.get('security_status')
            }
        else:
            return {
                'success': False,
                'error': ai_response.get('error', 'Analysis failed'),
                'security_status': ai_response.get('security_status')
            }
    
    def generate_grant_application_outline(self, grant: GrantOpportunity, 
                                         municipal_profile: Dict[str, Any],
                                         project_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered grant application outline and guidance
        """
        
        outline_prompt = f"""
        Create a comprehensive grant application outline for:
        
        GRANT: {grant.title}
        Agency: {grant.agency}
        Amount Requested: ${project_details.get('requested_amount', grant.min_amount):,}
        Project Title: {project_details.get('title', 'Municipal Project')}
        
        MUNICIPALITY:
        Name: {municipal_profile.get('name', 'City')}
        Population: {municipal_profile.get('population', 50000):,}
        
        PROJECT DETAILS:
        Description: {project_details.get('description', 'Project description needed')}
        Timeline: {project_details.get('timeline', '12 months')}
        Key Objectives: {', '.join(project_details.get('objectives', []))}
        
        Create a detailed application outline including:
        
        1. Executive Summary (2-3 paragraphs)
        2. Statement of Need (with data requirements)
        3. Project Description and Methodology
        4. Goals, Objectives, and Expected Outcomes
        5. Evaluation Plan and Success Metrics
        6. Budget Narrative and Justification
        7. Organizational Capacity and Experience
        8. Sustainability Plan
        9. Timeline and Milestones
        10. Appendices and Supporting Documents
        
        For each section, provide:
        - Key points to address
        - Recommended length
        - Critical data or documentation needed
        - Common pitfalls to avoid
        """
        
        ai_response = self.secure_ai_request(
            outline_prompt,
            "grant_application_outline",
            data_sources=["grant_database", "municipal_profile", "project_details"],
            max_tokens=2500
        )
        
        return {
            'grant_info': {
                'title': grant.title,
                'agency': grant.agency,
                'deadline': grant.deadline.strftime('%B %d, %Y'),
                'amount_range': f"${grant.min_amount:,} - ${grant.max_amount:,}"
            },
            'outline': ai_response.get('response', 'Outline generation failed'),
            'success': ai_response.get('success', False),
            'generated_at': datetime.now().isoformat()
        }
    
    def monitor_grant_opportunities(self, saved_searches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Monitor and alert on new grant opportunities matching saved searches
        """
        alerts = []
        
        for search in saved_searches:
            keywords = search.get('keywords', [])
            min_amount = search.get('min_amount', 0)
            max_amount = search.get('max_amount', float('inf'))
            categories = search.get('categories', [])
            
            # Find matching grants
            matching_grants = []
            for grant in self.grant_database:
                # Keyword matching
                keyword_match = any(
                    any(keyword.lower() in grant_keyword.lower() 
                        for grant_keyword in grant.keywords)
                    for keyword in keywords
                )
                
                # Amount range matching
                amount_match = (grant.min_amount >= min_amount and 
                               grant.max_amount <= max_amount)
                
                # Category matching
                category_match = (not categories or 
                                grant.category in categories)
                
                if keyword_match and amount_match and category_match:
                    matching_grants.append(grant)
            
            if matching_grants:
                alerts.append({
                    'search_name': search.get('name', 'Unnamed Search'),
                    'matches_found': len(matching_grants),
                    'grants': matching_grants[:3],  # Top 3 matches
                    'total_funding': sum(g.max_amount for g in matching_grants)
                })
        
        return {
            'alerts': alerts,
            'total_opportunities': sum(len(alert['grants']) for alert in alerts),
            'checked_at': datetime.now().isoformat()
        }