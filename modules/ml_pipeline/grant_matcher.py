"""
Grant Matching Pipeline
Uses machine learning to match department needs with grant opportunities

Features:
- TF-IDF text similarity for grant matching
- Department needs extraction from budget data
- Grant opportunity ranking and scoring
- Major federal grant sources integration
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import json
import os


class GrantOpportunity:
    """Represents a grant opportunity"""
    
    def __init__(self, grant_id: str, title: str, agency: str, amount_range: Tuple[float, float],
                 description: str, eligibility: str, deadline: str, category: str,
                 keywords: List[str], url: str = None):
        self.grant_id = grant_id
        self.title = title
        self.agency = agency
        self.amount_min = amount_range[0]
        self.amount_max = amount_range[1]
        self.description = description
        self.eligibility = eligibility
        self.deadline = deadline
        self.category = category
        self.keywords = keywords
        self.url = url
        self.match_score = 0.0
        self.relevance_reasons = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'grant_id': self.grant_id,
            'title': self.title,
            'agency': self.agency,
            'amount_min': self.amount_min,
            'amount_max': self.amount_max,
            'description': self.description,
            'eligibility': self.eligibility,
            'deadline': self.deadline,
            'category': self.category,
            'keywords': self.keywords,
            'url': self.url,
            'match_score': self.match_score,
            'relevance_reasons': self.relevance_reasons
        }


class GrantMatcher:
    """Machine learning-based grant matching system"""
    
    def __init__(self, db_path: str = None):
        """Initialize grant matcher"""
        self.db_path = db_path or "databases/core/grants.db"
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=1
        )
        self.grant_database = []
        self.department_profiles = {}
        self.grant_vectors = None
        self._initialize_grant_database()
    
    def _initialize_grant_database(self):
        """Initialize with major federal grant opportunities"""
        
        # FEMA Grants
        self.grant_database.extend([
            GrantOpportunity(
                "FEMA-2025-001",
                "Building Resilient Infrastructure and Communities (BRIC)",
                "FEMA",
                (500000, 50000000),
                "Funding for hazard mitigation projects to reduce risks from disasters and natural hazards. " +
                "Supports infrastructure hardening, nature-based solutions, and community resilience planning.",
                "State, local, tribal and territorial governments",
                "2025-12-31",
                "Disaster Preparedness",
                ["infrastructure", "disaster", "mitigation", "resilience", "flooding", "wildfire", "earthquake"],
                "https://www.fema.gov/grants/mitigation/building-resilient-infrastructure-communities"
            ),
            GrantOpportunity(
                "FEMA-2025-002",
                "Assistance to Firefighters Grant (AFG)",
                "FEMA",
                (10000, 1000000),
                "Funding for fire departments and EMS organizations for equipment, training, and wellness programs. " +
                "Supports critical response equipment, vehicles, and firefighter safety initiatives.",
                "Fire departments and EMS organizations",
                "2025-11-30",
                "Public Safety",
                ["fire", "emergency", "equipment", "training", "safety", "first responders", "ems"],
                "https://www.fema.gov/grants/preparedness/firefighters"
            ),
            GrantOpportunity(
                "FEMA-2025-003",
                "Flood Mitigation Assistance (FMA)",
                "FEMA",
                (100000, 10000000),
                "Reduces or eliminates the risk of repetitive flood damage to buildings insured by the NFIP. " +
                "Funds property acquisition, structure elevation, and floodproofing.",
                "States, territories, and federally recognized tribes",
                "2025-10-31",
                "Flood Mitigation",
                ["flood", "mitigation", "property", "insurance", "elevation", "acquisition", "water"],
                "https://www.fema.gov/grants/mitigation/floods"
            )
        ])
        
        # DOT Infrastructure Grants
        self.grant_database.extend([
            GrantOpportunity(
                "DOT-2025-001",
                "Rebuilding American Infrastructure with Sustainability and Equity (RAISE)",
                "Department of Transportation",
                (1000000, 25000000),
                "Funds for road, rail, transit and port projects that have significant local or regional impact. " +
                "Emphasizes environmental sustainability, racial equity, and economic competitiveness.",
                "State and local governments, territories, tribes, transit agencies",
                "2025-09-30",
                "Transportation Infrastructure",
                ["transportation", "roads", "bridges", "transit", "rail", "ports", "infrastructure", "equity"],
                "https://www.transportation.gov/RAISEgrants"
            ),
            GrantOpportunity(
                "DOT-2025-002",
                "Safe Streets and Roads for All (SS4A)",
                "Department of Transportation",
                (200000, 30000000),
                "Prevents roadway deaths and serious injuries through comprehensive safety action plans. " +
                "Supports Vision Zero initiatives and complete streets designs.",
                "Metropolitan planning organizations, cities, counties, tribes",
                "2025-08-31",
                "Traffic Safety",
                ["safety", "pedestrian", "bicycle", "traffic", "vision zero", "streets", "accidents"],
                "https://www.transportation.gov/grants/ss4a"
            ),
            GrantOpportunity(
                "DOT-2025-003",
                "Bridge Investment Program",
                "Department of Transportation",
                (2000000, 500000000),
                "Improve bridge condition, safety, efficiency, and reliability. Funds large bridge projects " +
                "and planning/design for bridge improvements.",
                "States, localities, tribes, federal land management agencies",
                "2025-07-31",
                "Bridge Infrastructure",
                ["bridge", "infrastructure", "repair", "replacement", "safety", "structural"],
                "https://www.fhwa.dot.gov/bridge/bip"
            )
        ])
        
        # EPA Environmental Grants
        self.grant_database.extend([
            GrantOpportunity(
                "EPA-2025-001",
                "Clean Water State Revolving Fund (CWSRF)",
                "Environmental Protection Agency",
                (500000, 100000000),
                "Low-cost financing for water quality infrastructure projects including wastewater treatment, " +
                "stormwater management, and green infrastructure.",
                "Publicly owned treatment works, municipalities, communities",
                "2025-06-30",
                "Water Infrastructure",
                ["water", "wastewater", "stormwater", "treatment", "infrastructure", "quality", "pollution"],
                "https://www.epa.gov/cwsrf"
            ),
            GrantOpportunity(
                "EPA-2025-002",
                "Brownfields Assessment and Cleanup Grants",
                "Environmental Protection Agency",
                (200000, 2000000),
                "Funds to assess and clean up contaminated properties for redevelopment. " +
                "Supports environmental assessment, cleanup, and area-wide planning.",
                "States, cities, counties, tribes, nonprofits",
                "2025-11-15",
                "Environmental Cleanup",
                ["brownfield", "contamination", "cleanup", "redevelopment", "environmental", "assessment"],
                "https://www.epa.gov/brownfields"
            ),
            GrantOpportunity(
                "EPA-2025-003",
                "Climate Pollution Reduction Grants",
                "Environmental Protection Agency",
                (1000000, 500000000),
                "Develop and implement plans to reduce greenhouse gas emissions and air pollution. " +
                "Supports clean energy, efficiency, and sustainable transportation.",
                "States, municipalities, tribes, air pollution control agencies",
                "2025-10-01",
                "Climate Action",
                ["climate", "emissions", "greenhouse gas", "clean energy", "sustainability", "pollution"],
                "https://www.epa.gov/inflation-reduction-act/climate-pollution-reduction-grants"
            )
        ])
        
        # HUD Community Development Grants
        self.grant_database.extend([
            GrantOpportunity(
                "HUD-2025-001",
                "Community Development Block Grant (CDBG)",
                "Housing and Urban Development",
                (100000, 20000000),
                "Flexible funding for community development needs including housing, infrastructure, " +
                "and economic development in low-income areas.",
                "Cities, counties, states, insular areas",
                "2025-05-31",
                "Community Development",
                ["housing", "community", "development", "low-income", "infrastructure", "economic"],
                "https://www.hud.gov/program_offices/comm_planning/cdbg"
            ),
            GrantOpportunity(
                "HUD-2025-002",
                "Choice Neighborhoods Implementation Grants",
                "Housing and Urban Development",
                (5000000, 35000000),
                "Transform distressed public housing and neighborhoods into mixed-income communities. " +
                "Comprehensive approach to neighborhood transformation.",
                "Public housing authorities, cities, counties, tribes, nonprofits",
                "2025-09-15",
                "Neighborhood Revitalization",
                ["housing", "neighborhood", "revitalization", "mixed-income", "transformation"],
                "https://www.hud.gov/cn"
            )
        ])
        
        # USDA Rural Development Grants
        self.grant_database.extend([
            GrantOpportunity(
                "USDA-2025-001",
                "Water & Waste Disposal Loan & Grant Program",
                "USDA Rural Development",
                (100000, 10000000),
                "Funding for clean and reliable drinking water systems, sanitary sewage disposal, " +
                "and storm water drainage for rural areas.",
                "Rural communities with populations of 10,000 or less",
                "2025-12-31",
                "Rural Water Infrastructure",
                ["water", "rural", "wastewater", "infrastructure", "sewage", "drainage"],
                "https://www.rd.usda.gov/programs-services/water-environmental-programs"
            ),
            GrantOpportunity(
                "USDA-2025-002",
                "Rural Energy for America Program (REAP)",
                "USDA Rural Development",
                (20000, 1000000),
                "Renewable energy systems and energy efficiency improvements for agricultural producers " +
                "and rural small businesses.",
                "Agricultural producers and rural small businesses",
                "2025-06-30",
                "Energy Efficiency",
                ["energy", "renewable", "efficiency", "solar", "wind", "rural", "agriculture"],
                "https://www.rd.usda.gov/programs-services/energy-programs/rural-energy-america-program"
            )
        ])
    
    def extract_department_needs(self, budget_data: pd.DataFrame, department: str) -> Dict[str, Any]:
        """Extract department needs from budget data"""
        
        dept_data = budget_data[budget_data['DepartmentCode'] == department] if 'DepartmentCode' in budget_data.columns else budget_data
        
        profile = {
            'department': department,
            'total_budget': dept_data['Budget'].sum() if 'Budget' in dept_data.columns else 0,
            'actual_spending': dept_data['Actual'].sum() if 'Actual' in dept_data.columns else 0,
            'variance': 0,
            'needs_text': "",
            'priorities': [],
            'keywords': []
        }
        
        # Calculate variance
        if profile['total_budget'] > 0:
            profile['variance'] = profile['actual_spending'] - profile['total_budget']
            profile['variance_pct'] = (profile['variance'] / profile['total_budget']) * 100
        
        # Determine needs based on department type and spending patterns
        dept_lower = department.lower()
        
        if 'police' in dept_lower or 'fire' in dept_lower or 'emergency' in dept_lower:
            profile['priorities'] = ['public safety', 'equipment', 'training', 'emergency response']
            profile['keywords'] = ['safety', 'emergency', 'equipment', 'training', 'first responders']
            profile['needs_text'] = f"{department} requires funding for public safety equipment, training programs, " + \
                                   "and emergency response capabilities. Focus on enhancing community safety and first responder resources."
        
        elif 'water' in dept_lower or 'sewer' in dept_lower or 'utility' in dept_lower:
            profile['priorities'] = ['infrastructure', 'water quality', 'system maintenance', 'environmental compliance']
            profile['keywords'] = ['water', 'infrastructure', 'utility', 'environmental', 'treatment']
            profile['needs_text'] = f"{department} needs infrastructure improvements for water and sewer systems, " + \
                                   "treatment facility upgrades, and environmental compliance measures."
        
        elif 'public works' in dept_lower or 'streets' in dept_lower or 'roads' in dept_lower:
            profile['priorities'] = ['infrastructure', 'roads', 'maintenance', 'transportation']
            profile['keywords'] = ['infrastructure', 'roads', 'streets', 'transportation', 'maintenance', 'bridges']
            profile['needs_text'] = f"{department} requires funding for road maintenance, infrastructure improvements, " + \
                                   "street repairs, and transportation system enhancements."
        
        elif 'parks' in dept_lower or 'recreation' in dept_lower:
            profile['priorities'] = ['community development', 'recreation', 'green spaces', 'facilities']
            profile['keywords'] = ['parks', 'recreation', 'community', 'facilities', 'green', 'environment']
            profile['needs_text'] = f"{department} seeks funding for park improvements, recreational facilities, " + \
                                   "community programs, and green space development."
        
        elif 'planning' in dept_lower or 'development' in dept_lower:
            profile['priorities'] = ['community development', 'housing', 'economic growth', 'planning']
            profile['keywords'] = ['development', 'planning', 'housing', 'economic', 'community', 'growth']
            profile['needs_text'] = f"{department} needs support for community development, affordable housing initiatives, " + \
                                   "economic development programs, and comprehensive planning efforts."
        
        else:
            # Generic department
            profile['priorities'] = ['operations', 'services', 'infrastructure', 'efficiency']
            profile['keywords'] = ['municipal', 'government', 'services', 'operations', 'efficiency']
            profile['needs_text'] = f"{department} requires operational funding for service delivery, " + \
                                   "infrastructure maintenance, and efficiency improvements."
        
        # Add budget stress indicators
        if profile.get('variance_pct', 0) < -10:
            profile['priorities'].append('budget relief')
            profile['needs_text'] += " Department faces budget constraints and requires additional funding sources."
        
        self.department_profiles[department] = profile
        return profile
    
    def match_grants(self, department_profile: Dict[str, Any], 
                    min_score: float = 0.3) -> List[GrantOpportunity]:
        """Match grants to department needs using TF-IDF similarity"""
        
        # Prepare text for matching
        dept_text = department_profile['needs_text'] + " " + " ".join(department_profile['keywords'])
        
        # Prepare grant texts
        grant_texts = []
        for grant in self.grant_database:
            grant_text = f"{grant.title} {grant.description} {grant.category} " + " ".join(grant.keywords)
            grant_texts.append(grant_text)
        
        # Create TF-IDF vectors
        all_texts = [dept_text] + grant_texts
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)
        
        # Calculate similarities
        dept_vector = tfidf_matrix[0:1]
        grant_vectors = tfidf_matrix[1:]
        similarities = cosine_similarity(dept_vector, grant_vectors)[0]
        
        # Score and rank grants
        matched_grants = []
        for i, grant in enumerate(self.grant_database):
            grant.match_score = similarities[i]
            
            if grant.match_score >= min_score:
                # Determine relevance reasons
                grant.relevance_reasons = []
                
                # Check keyword matches
                dept_keywords = set(department_profile['keywords'])
                grant_keywords = set(grant.keywords)
                matched_keywords = dept_keywords.intersection(grant_keywords)
                
                if matched_keywords:
                    grant.relevance_reasons.append(f"Keyword match: {', '.join(matched_keywords)}")
                
                # Check priority alignment
                for priority in department_profile['priorities']:
                    if priority.lower() in grant.description.lower() or priority.lower() in grant.title.lower():
                        grant.relevance_reasons.append(f"Aligns with priority: {priority}")
                
                # Check funding amount relevance
                if department_profile.get('variance', 0) < 0:
                    budget_gap = abs(department_profile['variance'])
                    if grant.amount_min <= budget_gap <= grant.amount_max:
                        grant.relevance_reasons.append("Funding amount matches budget gap")
                
                # Add deadline urgency
                try:
                    deadline_date = datetime.strptime(grant.deadline, "%Y-%m-%d")
                    days_until = (deadline_date - datetime.now()).days
                    if days_until <= 60:
                        grant.relevance_reasons.append(f"Urgent: {days_until} days until deadline")
                except:
                    pass
                
                matched_grants.append(grant)
        
        # Sort by match score and funding amount
        matched_grants.sort(key=lambda x: (x.match_score, x.amount_max), reverse=True)
        
        return matched_grants
    
    def get_all_department_matches(self, budget_data: pd.DataFrame, 
                                  departments: List[str] = None) -> Dict[str, List[GrantOpportunity]]:
        """Get grant matches for all departments"""
        
        if departments is None:
            if 'DepartmentCode' in budget_data.columns:
                departments = budget_data['DepartmentCode'].unique().tolist()
            else:
                departments = ['General']
        
        all_matches = {}
        
        for dept in departments:
            profile = self.extract_department_needs(budget_data, dept)
            matches = self.match_grants(profile)
            all_matches[dept] = matches
        
        return all_matches
    
    def generate_grant_report(self, department: str, matches: List[GrantOpportunity]) -> Dict[str, Any]:
        """Generate detailed grant report for department"""
        
        if not matches:
            return {
                'department': department,
                'total_opportunities': 0,
                'total_potential_funding': 0,
                'message': 'No matching grants found'
            }
        
        report = {
            'department': department,
            'profile': self.department_profiles.get(department, {}),
            'total_opportunities': len(matches),
            'total_potential_funding_min': sum(g.amount_min for g in matches),
            'total_potential_funding_max': sum(g.amount_max for g in matches),
            'top_matches': [],
            'by_agency': {},
            'by_category': {},
            'upcoming_deadlines': []
        }
        
        # Top matches
        for grant in matches[:10]:  # Top 10
            report['top_matches'].append({
                'title': grant.title,
                'agency': grant.agency,
                'amount_range': f"${grant.amount_min:,.0f} - ${grant.amount_max:,.0f}",
                'match_score': f"{grant.match_score:.1%}",
                'deadline': grant.deadline,
                'reasons': grant.relevance_reasons,
                'url': grant.url
            })
        
        # Group by agency
        for grant in matches:
            if grant.agency not in report['by_agency']:
                report['by_agency'][grant.agency] = []
            report['by_agency'][grant.agency].append(grant.title)
        
        # Group by category
        for grant in matches:
            if grant.category not in report['by_category']:
                report['by_category'][grant.category] = []
            report['by_category'][grant.category].append(grant.title)
        
        # Upcoming deadlines
        deadline_grants = []
        for grant in matches:
            try:
                deadline_date = datetime.strptime(grant.deadline, "%Y-%m-%d")
                days_until = (deadline_date - datetime.now()).days
                if days_until > 0:
                    deadline_grants.append((days_until, grant))
            except:
                pass
        
        deadline_grants.sort(key=lambda x: x[0])
        
        for days, grant in deadline_grants[:5]:  # Top 5 upcoming
            report['upcoming_deadlines'].append({
                'title': grant.title,
                'deadline': grant.deadline,
                'days_remaining': days,
                'amount_range': f"${grant.amount_min:,.0f} - ${grant.amount_max:,.0f}"
            })
        
        return report
    
    def search_grants(self, query: str, limit: int = 20) -> List[GrantOpportunity]:
        """Search grants by keyword query"""
        
        results = []
        query_lower = query.lower()
        
        for grant in self.grant_database:
            # Search in title, description, keywords, and category
            search_text = f"{grant.title} {grant.description} {grant.category} {' '.join(grant.keywords)}".lower()
            
            if query_lower in search_text:
                # Calculate relevance score based on where the match occurred
                score = 0
                if query_lower in grant.title.lower():
                    score += 3
                if query_lower in grant.category.lower():
                    score += 2
                if any(query_lower in k.lower() for k in grant.keywords):
                    score += 2
                if query_lower in grant.description.lower():
                    score += 1
                
                grant.match_score = score / 8.0  # Normalize to 0-1
                results.append(grant)
        
        # Sort by relevance
        results.sort(key=lambda x: x.match_score, reverse=True)
        
        return results[:limit]
    
    def add_custom_grant(self, grant: GrantOpportunity):
        """Add a custom grant opportunity to the database"""
        self.grant_database.append(grant)
    
    def export_matches(self, matches: Dict[str, List[GrantOpportunity]], 
                      filepath: str = None) -> str:
        """Export grant matches to CSV"""
        
        if filepath is None:
            filepath = f"grant_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Prepare data for export
        rows = []
        for dept, grants in matches.items():
            for grant in grants:
                rows.append({
                    'Department': dept,
                    'Grant Title': grant.title,
                    'Agency': grant.agency,
                    'Min Amount': grant.amount_min,
                    'Max Amount': grant.amount_max,
                    'Match Score': grant.match_score,
                    'Deadline': grant.deadline,
                    'Category': grant.category,
                    'URL': grant.url
                })
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        
        return filepath