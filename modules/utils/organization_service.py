"""
Organization Service - Centralized organization configuration management
Provides dynamic city/state data for all API integrations
"""

import streamlit as st
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class OrganizationConfig:
    """Organization configuration data structure"""
    org_id: str
    name: str
    city: str
    state: str
    state_code: str
    county: str
    latitude: float
    longitude: float
    fips_code: str
    place_code: str
    population: int
    timezone: str = "America/Denver"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API usage"""
        return {
            'org_id': self.org_id,
            'name': self.name,
            'city': self.city,
            'state': self.state,
            'state_code': self.state_code,
            'county': self.county,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'fips_code': self.fips_code,
            'place_code': self.place_code,
            'population': self.population,
            'timezone': self.timezone
        }

class OrganizationService:
    """Centralized service for organization configuration and API coordination"""
    
    def __init__(self):
        # Comprehensive organization configurations
        self.organizations = {
            "cityA": OrganizationConfig(
                org_id="cityA",
                name="Spanish Fork",
                city="Spanish Fork",
                state="Utah",
                state_code="49",
                county="Utah County",
                latitude=40.1149,
                longitude=-111.6549,
                fips_code="4970660",
                place_code="70660",
                population=47428
            ),
            "cityB": OrganizationConfig(
                org_id="cityB",
                name="Provo",
                city="Provo",
                state="Utah",
                state_code="49",
                county="Utah County",
                latitude=40.2338,
                longitude=-111.6585,
                fips_code="4962470",
                place_code="62470",
                population=115162
            ),
            "cityC": OrganizationConfig(
                org_id="cityC",
                name="Salt Lake City",
                city="Salt Lake City",
                state="Utah",
                state_code="49",
                county="Salt Lake County",
                latitude=40.7608,
                longitude=-111.8910,
                fips_code="4967000",
                place_code="67000",
                population=200567
            ),
            "cityD": OrganizationConfig(
                org_id="cityD",
                name="Phoenix",
                city="Phoenix",
                state="Arizona",
                state_code="04",
                county="Maricopa County",
                latitude=33.4484,
                longitude=-112.0740,
                fips_code="0455000",
                place_code="55000",
                population=1608139
            ),
            "cityE": OrganizationConfig(
                org_id="cityE",
                name="Denver",
                city="Denver",
                state="Colorado",
                state_code="08",
                county="Denver County",
                latitude=39.7392,
                longitude=-104.9903,
                fips_code="0820000",
                place_code="20000",
                population=715522
            )
        }
    
    def get_current_organization(self) -> OrganizationConfig:
        """Get the currently selected organization configuration"""
        current_org_id = st.session_state.get('selected_org', 'cityA')
        return self.organizations.get(current_org_id, self.organizations['cityA'])
    
    def get_organization_by_id(self, org_id: str) -> Optional[OrganizationConfig]:
        """Get specific organization by ID"""
        return self.organizations.get(org_id)
    
    def get_all_organizations(self) -> Dict[str, OrganizationConfig]:
        """Get all available organizations"""
        return self.organizations
    
    def get_state_specific_data(self) -> Dict[str, Any]:
        """Get state-specific configuration for APIs"""
        org = self.get_current_organization()
        
        # State-specific API configurations
        state_configs = {
            "Utah": {
                "grant_sources": [
                    "https://business.utah.gov/grants-incentives/",
                    "https://deq.utah.gov/funding-opportunities",
                    "https://heritage.utah.gov/grants-funding"
                ],
                "legislative_session": "2025 General Session",
                "legislative_url": "https://le.utah.gov/",
                "state_agencies": ["UDOT", "DEQ", "DWS", "DHS"],
                "climate_zone": "semi-arid",
                "economic_region": "Wasatch Front"
            },
            "Arizona": {
                "grant_sources": [
                    "https://azcommerce.com/grants/",
                    "https://azdeq.gov/grants",
                    "https://azdot.gov/business/grants-and-funding"
                ],
                "legislative_session": "2025 Session",
                "legislative_url": "https://www.azleg.gov/",
                "state_agencies": ["ADOT", "ADEQ", "DWR", "DHS"],
                "climate_zone": "desert",
                "economic_region": "Phoenix Metro"
            },
            "Colorado": {
                "grant_sources": [
                    "https://oedit.colorado.gov/funding-incentives",
                    "https://cdphe.colorado.gov/funding-opportunities",
                    "https://www.codot.gov/business/grants"
                ],
                "legislative_session": "2025 Session",
                "legislative_url": "https://leg.colorado.gov/",
                "state_agencies": ["CDOT", "CDPHE", "CDA", "CHFA"],
                "climate_zone": "continental",
                "economic_region": "Front Range"
            }
        }
        
        return state_configs.get(org.state, state_configs["Utah"])
    
    def get_federal_grant_eligibility(self) -> Dict[str, Any]:
        """Get federal grant eligibility based on organization size and type"""
        org = self.get_current_organization()
        
        # Federal grant eligibility by population size
        if org.population < 50000:
            return {
                "eligible_programs": [
                    "USDA Rural Development",
                    "EPA Small Communities",
                    "CDBG Non-Entitlement",
                    "FEMA Assistance to Firefighters",
                    "DOT Rural Surface Transportation"
                ],
                "priority_level": "Small Municipality",
                "match_requirements": "Typically 10-25%"
            }
        elif org.population < 200000:
            return {
                "eligible_programs": [
                    "CDBG Entitlement",
                    "EPA Environmental Justice",
                    "DOT Highway Safety Improvement",
                    "HUD Community Development",
                    "NSF Smart Cities"
                ],
                "priority_level": "Medium Municipality", 
                "match_requirements": "Typically 15-30%"
            }
        else:
            return {
                "eligible_programs": [
                    "CDBG Entitlement",
                    "DOT TIGER/INFRA",
                    "EPA Brownfields",
                    "HUD Choice Neighborhoods",
                    "DHS Urban Area Security"
                ],
                "priority_level": "Large Municipality",
                "match_requirements": "Typically 20-50%"
            }

# Singleton instance
_org_service = None

def get_organization_service() -> OrganizationService:
    """Get the singleton organization service instance"""
    global _org_service
    if _org_service is None:
        _org_service = OrganizationService()
    return _org_service

def get_current_org_config() -> OrganizationConfig:
    """Quick access to current organization configuration"""
    return get_organization_service().get_current_organization()

def get_current_state_config() -> Dict[str, Any]:
    """Quick access to current state configuration"""
    return get_organization_service().get_state_specific_data()