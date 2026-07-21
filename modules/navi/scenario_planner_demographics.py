"""
Enhanced Scenario Planner with Demographics Integration
Adds comprehensive demographics tab to scenario planning for better municipal decision making
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List

# Import demographics integration
try:
    from .demographics_integration import get_demographics_integration
    DEMOGRAPHICS_AVAILABLE = True
except ImportError:
    DEMOGRAPHICS_AVAILABLE = False

def render_demographics_tab():
    """Render the enhanced demographics tab in scenario planner"""
    
    st.markdown("### Demographics & Environmental Intelligence")
    st.markdown("*Integrate population, zoning, and climate data for comprehensive scenario planning*")
    
    if not DEMOGRAPHICS_AVAILABLE:
        st.warning("Demographics module is loading. Please refresh the page.")
        return
    
    # Get demographics integration instance
    demographics = get_demographics_integration()
    
    # Scenario context selection
    with st.expander("Scenario Context Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Population Assumptions**")
            scenario_population_growth = st.slider("Annual Population Growth (%)", 0.0, 5.0, 2.0, 0.1)
            scenario_age_shift = st.selectbox("Demographic Age Trend", 
                                            ["Stable", "Aging Population", "Young Families", "Mixed Growth"])
            
        with col2:
            st.markdown("**Development Context**")
            development_pressure = st.selectbox("Development Pressure", 
                                               ["Low", "Moderate", "High", "Very High"])
            zoning_flexibility = st.slider("Zoning Flexibility", 1, 10, 5)
    
    # Demographics impact analysis
    st.markdown("### Demographic Impact on Municipal Services")
    
    # Generate demographic scenario impacts
    demographic_impacts = calculate_demographic_impacts(
        scenario_population_growth, scenario_age_shift, development_pressure
    )
    
    # Display impact metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        service_demand = demographic_impacts['service_demand_change']
        st.metric("Service Demand Change", f"{service_demand:+.1f}%")
    
    with col2:
        infrastructure_need = demographic_impacts['infrastructure_investment']
        st.metric("Infrastructure Investment", f"${infrastructure_need/1000:.1f}K")
    
    with col3:
        revenue_impact = demographic_impacts['revenue_impact']
        st.metric("Revenue Impact", f"{revenue_impact:+.1f}%")
    
    with col4:
        housing_demand = demographic_impacts['housing_demand']
        st.metric("Housing Units Needed", f"{housing_demand:,}")
    
    # Integrated analysis tabs
    demo_tab1, demo_tab2, demo_tab3 = st.tabs([
        "Population Impact",
        "Zoning & Development", 
        "Climate Considerations"
    ])
    
    with demo_tab1:
        render_population_scenario_impact(demographic_impacts)
    
    with demo_tab2:
        render_zoning_scenario_impact(demographic_impacts, development_pressure)
    
    with demo_tab3:
        render_climate_scenario_impact()

def calculate_demographic_impacts(population_growth: float, age_shift: str, 
                                development_pressure: str) -> Dict[str, Any]:
    """Calculate impacts of demographic changes on municipal operations"""
    
    # Base calculations
    base_service_demand = 1.0
    
    # Population growth impact
    service_demand_multiplier = 1.0 + (population_growth / 100)
    
    # Age shift impact
    age_multipliers = {
        "Stable": 1.0,
        "Aging Population": 1.15,  # Higher healthcare, senior services
        "Young Families": 1.25,    # Schools, parks, family services
        "Mixed Growth": 1.1
    }
    service_demand_multiplier *= age_multipliers.get(age_shift, 1.0)
    
    # Development pressure impact
    development_multipliers = {
        "Low": 1.0,
        "Moderate": 1.1,
        "High": 1.3,
        "Very High": 1.5
    }
    development_multiplier = development_multipliers.get(development_pressure, 1.0)
    
    # Calculate impacts
    service_demand_change = (service_demand_multiplier - 1.0) * 100
    infrastructure_investment = 2000000 * development_multiplier * (population_growth / 100 + 1)
    revenue_impact = population_growth * 0.8  # Revenue typically lags population growth
    housing_demand = int(population_growth * 45000 / 100 / 2.4)  # Population / household size
    
    return {
        'service_demand_change': service_demand_change,
        'infrastructure_investment': infrastructure_investment,
        'revenue_impact': revenue_impact,
        'housing_demand': housing_demand,
        'population_multiplier': service_demand_multiplier,
        'development_multiplier': development_multiplier
    }

def render_population_scenario_impact(impacts: Dict[str, Any]):
    """Render population scenario impact analysis"""
    
    st.subheader("Population Growth Impact Analysis")
    
    # Service demand breakdown
    services = ['Police', 'Fire', 'Public Works', 'Parks & Recreation', 'Administration']
    base_multiplier = impacts['population_multiplier']
    
    # Different services have different sensitivity to population growth
    service_sensitivities = {
        'Police': 1.2,
        'Fire': 1.0,
        'Public Works': 1.4,
        'Parks & Recreation': 1.3,
        'Administration': 0.8
    }
    
    service_impacts = []
    for service in services:
        sensitivity = service_sensitivities.get(service, 1.0)
        impact = (base_multiplier * sensitivity - 1.0) * 100
        service_impacts.append({
            'Service': service,
            'Demand Change (%)': f"{impact:+.1f}%",
            'Impact Level': 'High' if impact > 20 else 'Medium' if impact > 10 else 'Low'
        })
    
    st.dataframe(pd.DataFrame(service_impacts), use_container_width=True, hide_index=True)
    
    # Population distribution impact
    st.markdown("### Population Distribution Considerations")
    
    considerations = [
        "📍 Geographic distribution of growth affects service delivery efficiency",
        "🏫 School capacity planning critical for young family scenarios", 
        "🚑 Healthcare service demand increases with aging population",
        "🚦 Traffic pattern changes require transportation planning updates",
        "💧 Water and wastewater capacity must match population distribution"
    ]
    
    for consideration in considerations:
        st.info(consideration)

def render_zoning_scenario_impact(impacts: Dict[str, Any], development_pressure: str):
    """Render zoning and development scenario impact"""
    
    st.subheader("Zoning & Development Impact")
    
    # Development capacity analysis
    development_multiplier = impacts['development_multiplier']
    
    # Mock zoning impact data
    zoning_impacts = [
        {
            'Zone Type': 'Residential',
            'Development Pressure': development_pressure,
            'Capacity Utilization': f"{min(100, 60 * development_multiplier):.0f}%",
            'Infrastructure Strain': 'High' if development_multiplier > 1.3 else 'Medium'
        },
        {
            'Zone Type': 'Commercial',
            'Development Pressure': development_pressure,
            'Capacity Utilization': f"{min(100, 40 * development_multiplier):.0f}%",
            'Infrastructure Strain': 'Medium' if development_multiplier > 1.2 else 'Low'
        },
        {
            'Zone Type': 'Mixed Use',
            'Development Pressure': development_pressure,
            'Capacity Utilization': f"{min(100, 30 * development_multiplier):.0f}%",
            'Infrastructure Strain': 'Medium' if development_multiplier > 1.4 else 'Low'
        }
    ]
    
    st.dataframe(pd.DataFrame(zoning_impacts), use_container_width=True, hide_index=True)
    
    # Development recommendations
    st.markdown("### Development Strategy Recommendations")
    
    if development_pressure in ['High', 'Very High']:
        st.error("🚨 **High Development Pressure Detected**")
        st.markdown("- Accelerate infrastructure capacity planning")
        st.markdown("- Consider development impact fees")
        st.markdown("- Review zoning ordinances for adequate density controls")
        st.markdown("- Implement phased development requirements")
    
    elif development_pressure == 'Moderate':
        st.warning("⚠️ **Moderate Development Pressure**")
        st.markdown("- Monitor infrastructure capacity closely")
        st.markdown("- Plan for utility system upgrades")
        st.markdown("- Consider mixed-use development incentives")
    
    else:
        st.success("✅ **Manageable Development Pressure**")
        st.markdown("- Current infrastructure adequate for projected growth")
        st.markdown("- Opportunity for strategic development incentives")
        st.markdown("- Focus on quality development standards")

def render_climate_scenario_impact():
    """Render climate considerations for scenario planning"""
    
    st.subheader("Climate & Environmental Considerations")
    
    # Climate risk factors
    st.markdown("### Climate Risk Assessment")
    
    climate_factors = [
        {
            'Factor': 'Temperature Increase',
            'Risk Level': 'Medium',
            'Municipal Impact': 'Increased cooling costs, heat-related service demands',
            'Mitigation Strategy': 'Urban heat island reduction, energy efficiency programs'
        },
        {
            'Factor': 'Precipitation Changes', 
            'Risk Level': 'High',
            'Municipal Impact': 'Stormwater system strain, flooding risk',
            'Mitigation Strategy': 'Stormwater infrastructure upgrades, green infrastructure'
        },
        {
            'Factor': 'Extreme Weather Events',
            'Risk Level': 'Medium',
            'Municipal Impact': 'Emergency response capacity, infrastructure damage',
            'Mitigation Strategy': 'Emergency preparedness, resilient infrastructure design'
        }
    ]
    
    st.dataframe(pd.DataFrame(climate_factors), use_container_width=True, hide_index=True)
    
    # Environmental sustainability goals
    st.markdown("### Environmental Sustainability Integration")
    
    sustainability_goals = [
        "🌱 Carbon footprint reduction through smart growth planning",
        "💧 Water conservation through efficient development standards",
        "🌳 Green space preservation and urban forestry programs", 
        "♻️ Waste reduction through sustainable development practices",
        "⚡ Renewable energy integration in municipal facilities"
    ]
    
    for goal in sustainability_goals:
        st.info(goal)
    
    # Climate adaptation strategies
    st.markdown("### Climate Adaptation Strategies")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Infrastructure Resilience**")
        st.markdown("- Climate-resistant building codes")
        st.markdown("- Redundant utility systems")
        st.markdown("- Flood-resistant design standards")
        st.markdown("- Emergency backup systems")
    
    with col2:
        st.markdown("**Community Resilience**")
        st.markdown("- Public education and preparedness")
        st.markdown("- Vulnerable population protection")
        st.markdown("- Economic diversification")
        st.markdown("- Regional cooperation agreements")

def integrate_demographics_with_scenarios(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    """Integrate demographic data with existing scenario planning"""
    
    # This function would be called from the main scenario planner
    # to incorporate demographic insights into financial scenarios
    
    enhanced_scenario = scenario_data.copy()
    
    # Add demographic-driven revenue adjustments
    if 'revenue_adjustments' not in enhanced_scenario:
        enhanced_scenario['revenue_adjustments'] = {}
    
    # Add demographic-driven expense adjustments
    if 'expense_adjustments' not in enhanced_scenario:
        enhanced_scenario['expense_adjustments'] = {}
    
    # Population growth impacts on revenue
    population_growth = scenario_data.get('population_growth', 2.0)
    enhanced_scenario['revenue_adjustments']['property_tax'] = population_growth * 0.8
    enhanced_scenario['revenue_adjustments']['sales_tax'] = population_growth * 1.2
    enhanced_scenario['revenue_adjustments']['fees'] = population_growth * 1.0
    
    # Population growth impacts on expenses
    enhanced_scenario['expense_adjustments']['public_safety'] = population_growth * 1.1
    enhanced_scenario['expense_adjustments']['infrastructure'] = population_growth * 1.3
    enhanced_scenario['expense_adjustments']['administration'] = population_growth * 0.6
    
    return enhanced_scenario

def get_demographic_scenario_recommendations(scenario_type: str) -> List[str]:
    """Get demographic-specific recommendations for scenario types"""
    
    recommendations = {
        'growth': [
            "📈 Plan for 15-20% increase in municipal service demand",
            "🏘️ Accelerate infrastructure capacity planning by 2-3 years",
            "💰 Consider development impact fees to fund growth-related costs",
            "🎯 Focus hiring on high-demand service areas (public safety, public works)"
        ],
        'decline': [
            "📉 Right-size municipal workforce to match service demand",
            "🔄 Consolidate services and optimize facility utilization", 
            "💡 Explore regional service sharing opportunities",
            "🎯 Focus on economic development to reverse population decline"
        ],
        'stable': [
            "⚖️ Maintain current service levels with efficiency improvements",
            "🔧 Focus on infrastructure maintenance and modernization",
            "📊 Optimize existing resources before expanding capacity",
            "🎯 Pursue strategic quality-of-life improvements"
        ]
    }
    
    return recommendations.get(scenario_type, [
        "📋 Conduct detailed demographic impact assessment",
        "🔍 Monitor key demographic indicators quarterly",
        "📈 Develop adaptive planning strategies for multiple scenarios"
    ])