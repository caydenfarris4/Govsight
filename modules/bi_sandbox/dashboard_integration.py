"""
Dashboard Integration - Streamlit integration for the visual analytics dashboard
Handles the embedding and API endpoints for the custom HTML dashboard
"""

import streamlit as st
import json
from typing import Dict, Any, Optional, List
import logging
from urllib.parse import quote

from .dashboard_api import get_dashboard_api, handle_dashboard_data_request, handle_ai_chat_request

logger = logging.getLogger(__name__)

class DashboardIntegration:
    """Integration class for embedding the dashboard in Streamlit"""
    
    def __init__(self):
        self.dashboard_api = get_dashboard_api()
        
    def render_dashboard(self, org: str = None, org_display_name: str = None):
        """
        Render the complete visual analytics dashboard
        
        Args:
            org: Organization identifier
            org_display_name: Display name for the organization
        """
        try:
            # Set up the dashboard container
            st.markdown("""
                <style>
                /* Hide Streamlit default elements for full dashboard experience */
                .main > div {
                    padding-top: 0rem;
                    padding-bottom: 0rem;
                }
                .stApp > header {
                    background-color: transparent;
                }
                .stApp {
                    margin-top: -80px;
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Load dashboard data
            dashboard_data = self.dashboard_api.get_dashboard_data(org)
            
            # Set up session state for API communication
            if 'dashboard_data' not in st.session_state:
                st.session_state.dashboard_data = dashboard_data
            else:
                st.session_state.dashboard_data = dashboard_data
                
            # Set up AI chat session state
            if 'dashboard_chat_history' not in st.session_state:
                st.session_state.dashboard_chat_history = []
            
            # Load the HTML template
            html_content = self._load_html_template()
            
            # Inject the dashboard data into the HTML
            html_with_data = self._inject_dashboard_data(html_content, dashboard_data)
            
            # Add API endpoint simulation for the embedded dashboard
            self._setup_api_endpoints()
            
            # Render the dashboard using Streamlit's HTML component
            st.components.v1.html(
                html_with_data,
                height=1000,
                scrolling=False
            )
            
        except Exception as e:
            logger.error(f"Error rendering dashboard: {e}")
            st.error("Error loading HTML application: Main HTML application not found")
            st.error("Failed to load the GovSight application. Please check the system logs.")
            
            # Show detailed error in development
            if st.checkbox("Show detailed error"):
                st.exception(e)
            
            # Fallback to basic dashboard
            self._render_fallback_dashboard()
    
    def _load_html_template(self) -> str:
        """Load the HTML dashboard template"""
        import os
        try:
            # Get the absolute path to the HTML file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            html_path = os.path.join(current_dir, 'visual_analytics.html')
            
            logger.info(f"Attempting to load HTML from: {html_path}")
            
            if not os.path.exists(html_path):
                logger.error(f"HTML file not found at: {html_path}")
                raise FileNotFoundError(f"Dashboard HTML file not found: {html_path}")
            
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"Successfully loaded HTML file ({len(content)} characters)")
                return content
                
        except Exception as e:
            logger.error(f"Error loading HTML template: {e}")
            raise
    
    def _inject_dashboard_data(self, html_content: str, dashboard_data: Dict[str, Any]) -> str:
        """Inject dashboard data and fast schema API into the HTML template"""
        try:
            # Convert dashboard data to JSON for injection
            data_json = json.dumps(dashboard_data, default=str)
            
            # Get fast schema for improved performance from real databases
            fast_schema = self.dashboard_api.get_fast_schema()
            
            # Ensure we have real data
            if not fast_schema or ('fields' not in fast_schema and 'field_types' not in fast_schema):
                logger.warning("No real database schema available, fetching directly...")
                # Try to get schema directly from database manager
                try:
                    from .multi_database_manager import multi_db_manager
                    # Use the correct method to get field catalog
                    field_catalog = multi_db_manager.get_unified_field_catalog()
                    fast_schema = self._catalog_to_schema_format(field_catalog)
                except Exception as e:
                    logger.error(f"Failed to get database schema: {e}")
                    fast_schema = {'error': 'Database connection failed', 'fields': []}
            
            schema_json = json.dumps(fast_schema, default=str)
            
            # Create JavaScript injection to replace the sample data loading
            data_injection = f"""
                <script>
                // Injected dashboard data from Streamlit backend
                window.streamlitDashboardData = {data_json};
                
                // Dashboard API with fast schema support
                window.dashboardAPI = {{
                    get_dashboard_data: function() {{ return {data_json}; }},
                    get_fast_schema: function() {{ return {schema_json}; }}
                }};
                
                console.log('Dashboard API injected with fast schema');
                console.log('Schema contains', Object.keys({schema_json}).length > 0 ? 'real data' : 'no data');
                console.log('Fast schema load time:', {fast_schema.get('load_time', 0)},'seconds');
                
                // Trigger field loading after injection
                if (typeof loadFieldsFromAPI === 'function') {{
                    setTimeout(loadFieldsFromAPI, 10);
                }}
                
                // Override the loadSampleData function to use real data
                function loadSampleData() {{
                    console.log('Loading data from Streamlit backend...');
                    dashboardData = window.streamlitDashboardData;
                    
                    // Update dashboard with real data
                    updateBreadcrumb();
                    updateFilters();
                    updateKPIs();
                    updateCharts();
                    updateInsights();
                    updateDataTable();
                }}
                
                // API endpoint simulation for AI chat
                async function callStreamlitAPI(endpoint, data) {{
                    // This simulates API calls by using Streamlit's session state
                    console.log('Simulating API call to:', endpoint, data);
                    
                    if (endpoint === '/api/mantis/dashboard-chat') {{
                        return await simulateAIResponse(data.message);
                    }}
                    
                    return {{ error: 'Endpoint not found' }};
                }}
                
                async function simulateAIResponse(message) {{
                    // This would be replaced with actual Streamlit callback in production
                    const responses = {{
                        'police': 'The Police department is currently 5% over budget ($42K over). This is primarily due to increased overtime costs from recent community events and staff shortages.',
                        'parks': 'Parks & Recreation is performing well, utilizing 98% of their budget efficiently. Citizen satisfaction surveys show 94% approval.',
                        'budget': 'Current budget performance shows overall health with a few departments requiring attention. Focus on Police overtime and Public Works equipment needs.',
                        'trends': 'Revenue is tracking 8% above forecast this quarter, primarily from property tax increases and federal grant funding.',
                        'default': 'I can help you analyze department budgets, identify trends, explain variances, and provide strategic insights. What specific area would you like to explore?'
                    }};
                    
                    const lowerMessage = message.toLowerCase();
                    let response = responses.default;
                    
                    for (const [key, value] of Object.entries(responses)) {{
                        if (lowerMessage.includes(key)) {{
                            response = value;
                            break;
                        }}
                    }}
                    
                    return {{
                        message: response,
                        dashboard_updates: null
                    }};
                }}
                
                // Override the fetch function for dashboard API calls
                const originalFetch = window.fetch;
                window.fetch = async function(url, options) {{
                    if (url.includes('/api/dashboard/data')) {{
                        return {{
                            ok: true,
                            json: async () => window.streamlitDashboardData
                        }};
                    }}
                    if (url.includes('/api/mantis/dashboard-chat')) {{
                        const body = JSON.parse(options.body);
                        const response = await simulateAIResponse(body.message);
                        return {{
                            ok: true,
                            json: async () => response
                        }};
                    }}
                    return originalFetch(url, options);
                }};
                </script>
            """
            
            # Inject the data script before the closing body tag
            html_with_data = html_content.replace('</body>', f'{data_injection}</body>')
            
            return html_with_data
            
        except Exception as e:
            logger.error(f"Error injecting dashboard data: {e}")
            return html_content
    
    def _setup_api_endpoints(self):
        """Set up API endpoint handling in Streamlit session"""
        try:
            # Store API handlers in session state for potential use
            if 'dashboard_api_handlers' not in st.session_state:
                st.session_state.dashboard_api_handlers = {
                    'data': handle_dashboard_data_request,
                    'ai_chat': handle_ai_chat_request
                }
                
        except Exception as e:
            logger.error(f"Error setting up API endpoints: {e}")
    
    def _catalog_to_schema_format(self, catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert field catalog to fast schema format"""
        fields = []
        
        for field in catalog:
            # Get field name - catalog uses 'column' as the field name
            field_name = field.get('column', 'unknown')
            if field_name and field_name != 'unknown':
                fields.append({
                    'field_name': field_name,
                    'display_name': field_name.replace('_', ' ').title(),
                    'table_name': field.get('table', 'unknown'),
                    'database': field.get('database', 'default'),
                    'data_type': field.get('data_type', 'text'),
                    'category': self._categorize_field(field.get('data_type', 'text'), field_name)
                })
        
        return {
            'fields': fields,
            'load_time': 0,
            'source': 'database',
            'total_fields': len(fields)
        }
    
    def _transform_raw_schema(self, raw_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw database schema to fast schema format"""
        fields = []
        
        for db_name, db_info in raw_schema.items():
            if isinstance(db_info, dict) and 'tables' in db_info:
                for table_name, table_info in db_info.get('tables', {}).items():
                    if isinstance(table_info, dict) and 'columns' in table_info:
                        for col_name, col_info in table_info['columns'].items():
                            fields.append({
                                'field_name': col_name,
                                'display_name': col_name.replace('_', ' ').title(),
                                'table_name': table_name,
                                'database': db_name,
                                'data_type': col_info.get('type', 'text'),
                                'category': self._categorize_field(col_info.get('type', 'text'), col_name)
                            })
        
        return {
            'fields': fields,
            'load_time': 0,
            'source': 'database',
            'total_fields': len(fields)
        }
    
    def _categorize_field(self, col_type: str, col_name: str) -> str:
        """Categorize a field based on its type and name"""
        col_type_lower = str(col_type).lower()
        col_name_lower = str(col_name).lower()
        
        # Check for date/time fields
        if any(dt in col_type_lower for dt in ['date', 'time', 'timestamp']):
            return 'date'
        if any(dt in col_name_lower for dt in ['_date', '_time', 'year', 'month', 'quarter']):
            return 'date'
        
        # Check for numeric/measure fields
        if any(num in col_type_lower for num in ['int', 'float', 'decimal', 'numeric', 'real', 'double']):
            return 'measure'
        if any(m in col_name_lower for m in ['amount', 'total', 'sum', 'count', 'avg', 'min', 'max', 'revenue', 'cost', 'budget']):
            return 'measure'
        
        # Default to dimension
        return 'dimension'
    
    def _render_fallback_dashboard(self):
        """Render a fallback dashboard if main dashboard fails"""
        st.warning("⚠️ Visual Analytics dashboard temporarily unavailable. Using simplified interface.")
        
        st.markdown("### Dashboard Controls")
        col1, col2 = st.columns(2)
        
        with col1:
            st.button("🔄 Retry Dashboard Loading", key="retry_dashboard")
        with col2:
            st.button("📊 Use Legacy Interface", key="use_legacy")
        
        st.markdown("### Quick Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Budget", "$2.34M", "12.3%")
        with col2:
            st.metric("Departments", "4", "3")
        with col3:
            st.metric("Variance", "-$45K", "-2.1%")
        with col4:
            st.metric("Utilization", "87%", "2.1%")
        
        st.info("💡 The Visual Analytics dashboard will be available shortly. Please refresh the page.")

def handle_dashboard_ai_query(message: str, context: Dict[str, Any] = None) -> str:
    """
    Handle AI queries from the dashboard
    This function can be called directly from Streamlit components
    """
    try:
        api = get_dashboard_api()
        
        if context is None:
            context = st.session_state.get('dashboard_context', {})
        
        response = api.process_ai_chat(message, context)
        
        # Store in chat history
        if 'dashboard_chat_history' not in st.session_state:
            st.session_state.dashboard_chat_history = []
        
        st.session_state.dashboard_chat_history.append({
            'message': message,
            'response': response['message'],
            'timestamp': response['timestamp']
        })
        
        return json.dumps(response)
        
    except Exception as e:
        logger.error(f"Error handling dashboard AI query: {e}")
        return json.dumps({
            'message': 'Sorry, I encountered an error processing your request.',
            'dashboard_updates': None,
            'error': str(e)
        })

# Export the main integration class
def create_dashboard_integration() -> DashboardIntegration:
    """Create and return a dashboard integration instance"""
    return DashboardIntegration()