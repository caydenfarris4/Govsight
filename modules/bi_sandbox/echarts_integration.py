"""
ECharts Integration Module - Connects the hybrid visualization system with Streamlit

This module provides the integration layer between the ECharts/D3.js dashboard
and the existing Streamlit BI Sandbox interface.
"""

import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import json
import pandas as pd
from typing import Dict, Any, Optional

from modules.bi_sandbox.dashboard_api_echarts import dashboard_api

class EChartsIntegration:
    """Integration handler for ECharts dashboard in Streamlit"""
    
    def __init__(self):
        self.dashboard_api = dashboard_api
        self.html_path = Path(__file__).parent / "visual_analytics_echarts.html"
        
    def render_dashboard(self, height: int = 800):
        """Render the ECharts dashboard in Streamlit"""
        
        # Initialize session state for dashboard
        if 'echarts_config' not in st.session_state:
            st.session_state.echarts_config = {
                'visualizations': [],
                'fields': [],
                'data_source': 'gl_primary'
            }
        
        # Create columns for layout
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.markdown("### Dashboard Controls")
            
            # Data Source Selector
            data_source = st.selectbox(
                "Data Source",
                options=['gl_primary', 'utility', 'asset', 'permits', 'payroll'],
                format_func=lambda x: {
                    'gl_primary': 'General Ledger',
                    'utility': 'Utility Management',
                    'asset': 'Asset Management',
                    'permits': 'Permits & Licensing',
                    'payroll': 'Payroll & HR'
                }.get(x, x)
            )
            
            st.session_state.echarts_config['data_source'] = data_source
            
            # Load available fields
            fields = self.dashboard_api.get_available_fields(data_source)
            st.session_state.echarts_config['fields'] = fields
            
            # Display field counts
            dimensions = [f for f in fields if f.get('category') == 'dimension']
            measures = [f for f in fields if f.get('category') == 'measure']
            dates = [f for f in fields if f.get('category') == 'date']
            
            st.info(f"""
            **Available Fields:**
            - Dimensions: {len(dimensions)}
            - Measures: {len(measures)}
            - Date/Time: {len(dates)}
            """)
            
            # Dashboard Actions
            st.markdown("### Actions")
            
            if st.button("Refresh Data", use_container_width=True):
                self._refresh_data()
                st.rerun()
            
            if st.button("Clear Dashboard", use_container_width=True):
                st.session_state.echarts_config['visualizations'] = []
                st.rerun()
            
            # Export Options
            st.markdown("### Export")
            export_format = st.selectbox("Format", ["PDF", "PNG", "JSON"])
            
            if st.button("Export Dashboard", use_container_width=True):
                self._export_dashboard(export_format)
            
            # Quick Templates
            st.markdown("### Quick Templates")
            
            if st.button("Financial Overview", use_container_width=True):
                self._load_financial_template()
                st.rerun()
            
            if st.button("Department Analysis", use_container_width=True):
                self._load_department_template()
                st.rerun()
            
            if st.button("Performance Metrics", use_container_width=True):
                self._load_performance_template()
                st.rerun()
        
        with col1:
            # Read and prepare HTML content
            html_content = self._prepare_html_content()
            
            # Render the dashboard
            components.html(html_content, height=height, scrolling=True)
    
    def _prepare_html_content(self) -> str:
        """Prepare HTML content with injected data"""
        
        # Read the HTML file
        with open(self.html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Inject field data into the HTML
        fields = st.session_state.echarts_config.get('fields', [])
        
        # Prepare JavaScript to populate fields
        js_injection = f"""
        <script>
        // Inject field data from Python
        window.dashboardFields = {json.dumps(fields)};
        
        // Initialize fields when document is ready
        document.addEventListener('DOMContentLoaded', function() {{
            if (window.dashboardFields && window.dashboardFields.length > 0) {{
                // Categorize and render fields
                dashboardState.fields = categorizeFields(window.dashboardFields);
                renderFieldLists();
            }}
        }});
        </script>
        """
        
        # Inject before closing body tag
        html_content = html_content.replace('</body>', f'{js_injection}</body>')
        
        return html_content
    
    def _refresh_data(self):
        """Refresh data from all databases"""
        try:
            # Reload fields from all databases
            all_fields = []
            for db in ['gl_primary', 'utility', 'asset', 'permits', 'payroll']:
                fields = self.dashboard_api.get_available_fields(db)
                all_fields.extend(fields)
            
            st.session_state.echarts_config['fields'] = all_fields
            st.success("Data refreshed successfully!")
            
        except Exception as e:
            st.error(f"Error refreshing data: {str(e)}")
    
    def _export_dashboard(self, format: str):
        """Export dashboard in specified format"""
        try:
            config = st.session_state.echarts_config
            export_data = self.dashboard_api.export_dashboard(config, format.lower())
            
            # Create download button
            st.download_button(
                label=f"Download {format}",
                data=export_data,
                file_name=f"dashboard.{format.lower()}",
                mime=self._get_mime_type(format)
            )
            
        except Exception as e:
            st.error(f"Error exporting dashboard: {str(e)}")
    
    def _get_mime_type(self, format: str) -> str:
        """Get MIME type for export format"""
        mime_types = {
            'PDF': 'application/pdf',
            'PNG': 'image/png',
            'JSON': 'application/json'
        }
        return mime_types.get(format, 'application/octet-stream')
    
    def _load_financial_template(self):
        """Load financial overview template"""
        st.session_state.echarts_config['visualizations'] = [
            {
                'id': 'viz_financial_1',
                'type': 'waterfall',
                'title': 'Revenue Flow',
                'config': {
                    'axis': [{'field': 'Period', 'type': 'text'}],
                    'values': [{'field': 'Amount', 'type': 'number'}]
                }
            },
            {
                'id': 'viz_financial_2',
                'type': 'gauge',
                'title': 'Budget Utilization',
                'config': {
                    'values': [{'field': 'Percentage', 'type': 'number'}]
                }
            },
            {
                'id': 'viz_financial_3',
                'type': 'sankey',
                'title': 'Fund Allocation',
                'config': {
                    'source': [{'field': 'Source', 'type': 'text'}],
                    'target': [{'field': 'Target', 'type': 'text'}],
                    'values': [{'field': 'Amount', 'type': 'number'}]
                }
            }
        ]
    
    def _load_department_template(self):
        """Load department analysis template"""
        st.session_state.echarts_config['visualizations'] = [
            {
                'id': 'viz_dept_1',
                'type': 'treemap',
                'title': 'Department Budget Hierarchy',
                'config': {
                    'category': [{'field': 'Department', 'type': 'text'}],
                    'values': [{'field': 'Budget', 'type': 'number'}]
                }
            },
            {
                'id': 'viz_dept_2',
                'type': 'radar',
                'title': 'Department Performance',
                'config': {
                    'dimensions': [{'field': 'Metric', 'type': 'text'}],
                    'values': [{'field': 'Score', 'type': 'number'}]
                }
            },
            {
                'id': 'viz_dept_3',
                'type': 'bar',
                'title': 'Budget vs Actual',
                'config': {
                    'axis': [{'field': 'Department', 'type': 'text'}],
                    'values': [
                        {'field': 'Budget', 'type': 'number'},
                        {'field': 'Actual', 'type': 'number'}
                    ]
                }
            }
        ]
    
    def _load_performance_template(self):
        """Load performance metrics template"""
        st.session_state.echarts_config['visualizations'] = [
            {
                'id': 'viz_perf_1',
                'type': 'kpi',
                'title': 'Key Metrics',
                'config': {
                    'values': [{'field': 'Value', 'type': 'number'}]
                }
            },
            {
                'id': 'viz_perf_2',
                'type': 'line',
                'title': 'Trend Analysis',
                'config': {
                    'axis': [{'field': 'Date', 'type': 'date'}],
                    'values': [{'field': 'Performance', 'type': 'number'}]
                }
            },
            {
                'id': 'viz_perf_3',
                'type': 'heatmap',
                'title': 'Performance Matrix',
                'config': {
                    'x': [{'field': 'Category', 'type': 'text'}],
                    'y': [{'field': 'Department', 'type': 'text'}],
                    'values': [{'field': 'Score', 'type': 'number'}]
                }
            }
        ]
    
    def render_custom_d3_viz(self, viz_type: str):
        """Render custom D3.js visualization"""
        
        st.markdown(f"### Custom D3 Visualization: {viz_type.replace('_', ' ').title()}")
        
        # Get data for D3 visualization
        data = self.dashboard_api._get_d3_viz_data(viz_type)
        
        # Create HTML for D3 viz
        d3_html = self._generate_d3_html(viz_type, data)
        
        # Render
        components.html(d3_html, height=400)
    
    def _generate_d3_html(self, viz_type: str, data: Dict) -> str:
        """Generate HTML for D3 visualization"""
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
                svg {{ border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div id="viz-container"></div>
            <script>
                const data = {json.dumps(data)};
                const container = d3.select('#viz-container');
                const width = 600;
                const height = 400;
                
                const svg = container.append('svg')
                    .attr('width', width)
                    .attr('height', height);
                
                // Visualization specific rendering
                {self._get_d3_viz_code(viz_type)}
            </script>
        </body>
        </html>
        """
        
        return html_template
    
    def _get_d3_viz_code(self, viz_type: str) -> str:
        """Get D3.js visualization code for specific type"""
        
        if viz_type == 'budget_flow':
            return """
            // Budget flow visualization
            const simulation = d3.forceSimulation(data.nodes)
                .force('link', d3.forceLink(data.links).id(d => d.id))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2));
            
            const link = svg.append('g')
                .selectAll('line')
                .data(data.links)
                .enter().append('line')
                .attr('stroke', '#999')
                .attr('stroke-width', d => Math.sqrt(d.value / 50000));
            
            const node = svg.append('g')
                .selectAll('circle')
                .data(data.nodes)
                .enter().append('circle')
                .attr('r', d => Math.sqrt(d.value / 10000))
                .attr('fill', d => d.group === 1 ? '#0078d4' : '#00bcf2');
            
            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
            });
            """
        
        elif viz_type == 'department_network':
            return """
            // Department network visualization
            const centerX = width / 2;
            const centerY = height / 2;
            const radius = Math.min(width, height) / 3;
            
            const angleStep = (Math.PI * 2) / data.departments.length;
            
            data.departments.forEach((dept, i) => {
                const angle = i * angleStep;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                
                svg.append('circle')
                    .attr('cx', x)
                    .attr('cy', y)
                    .attr('r', 30)
                    .attr('fill', '#0078d4');
                
                svg.append('text')
                    .attr('x', x)
                    .attr('y', y)
                    .attr('text-anchor', 'middle')
                    .style('fill', 'white')
                    .text(dept);
            });
            """
        
        else:
            return "// Custom visualization code"

def render_echarts_dashboard():
    """Main function to render ECharts dashboard in Streamlit"""
    
    st.title("Visual Analytics Dashboard")
    
    # Add description
    st.markdown("""
    This advanced dashboard provides **60+ chart types** with drag-and-drop functionality, 
    powered by **Apache ECharts** for standard visualizations and **D3.js** for custom graphics.
    
    **Features:**
    - Drag fields from the right panel onto visualizations
    - Choose from extensive chart library (Basic, Advanced, Statistical, Business, Geographic, 3D)
    - Create custom municipal visualizations with D3.js
    - Connect to all 5 municipal databases
    - Export dashboards in multiple formats
    """)
    
    # Initialize integration
    echarts = EChartsIntegration()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard Builder", "Custom D3 Visualizations", "Templates"])
    
    with tab1:
        echarts.render_dashboard(height=900)
    
    with tab2:
        st.markdown("### Custom D3.js Visualizations")
        st.info("These are specialized visualizations designed specifically for municipal data analysis.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Budget Flow Diagram", use_container_width=True):
                echarts.render_custom_d3_viz('budget_flow')
            
            if st.button("Department Network", use_container_width=True):
                echarts.render_custom_d3_viz('department_network')
            
            if st.button("Tax Distribution", use_container_width=True):
                echarts.render_custom_d3_viz('tax_distribution')
        
        with col2:
            if st.button("Project Timeline", use_container_width=True):
                echarts.render_custom_d3_viz('project_timeline')
            
            if st.button("Utility Infrastructure", use_container_width=True):
                echarts.render_custom_d3_viz('utility_infrastructure')
            
            if st.button("Financial Health", use_container_width=True):
                echarts.render_custom_d3_viz('financial_health')
    
    with tab3:
        st.markdown("### Dashboard Templates")
        st.info("Quick-start templates for common municipal analytics scenarios.")
        
        templates = {
            "Financial Overview": "Complete financial health dashboard with revenue flow, budget utilization, and fund allocation visualizations.",
            "Department Analysis": "Comprehensive department performance analysis with budget hierarchy, performance radar, and variance analysis.",
            "Performance Metrics": "Key performance indicators dashboard with trend analysis and performance matrices.",
            "Utility Management": "Utility services dashboard with usage patterns, revenue analysis, and infrastructure mapping.",
            "Capital Projects": "Project tracking dashboard with timelines, budget burn rates, and milestone tracking."
        }
        
        for template_name, description in templates.items():
            with st.expander(template_name):
                st.write(description)
                if st.button(f"Load {template_name}", key=f"template_{template_name}"):
                    st.success(f"Loading {template_name} template...")
                    # Template loading logic would go here