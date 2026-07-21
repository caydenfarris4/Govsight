"""
Streamlit-AG Grid persistence bridge
Handles bidirectional communication between AG-Grid (JavaScript) and Streamlit (Python)
"""

import streamlit as st
import json
from typing import Dict, Any, List

class PBBPersistenceBridge:
    """Bridge to sync AG-Grid state with Streamlit session state"""
    
    @staticmethod
    def save_grid_data(sheet_name: str, grid_data_json: str):
        """Save grid data from JavaScript to session state"""
        try:
            grid_data = json.loads(grid_data_json)
            if 'pbb_sheets' not in st.session_state:
                st.session_state['pbb_sheets'] = {}
            
            if sheet_name not in st.session_state['pbb_sheets']:
                st.session_state['pbb_sheets'][sheet_name] = {'data': [], 'locked': False}
            
            st.session_state['pbb_sheets'][sheet_name]['data'] = grid_data
            return True
        except Exception as e:
            st.error(f"Error saving grid data: {e}")
            return False
    
    @staticmethod
    def create_save_form(sheet_name: str) -> str:
        """Create hidden form for grid data persistence"""
        form_key = f"pbb_save_form_{sheet_name.replace(' ', '_')}"
        
        with st.form(key=form_key, clear_on_submit=False):
            grid_data_input = st.text_area(
                "Grid Data (Hidden)",
                value="",
                key=f"grid_data_{sheet_name}",
                height=1,
                label_visibility="collapsed",
                help="Grid data is auto-saved here"
            )
            
            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
            
            if submitted and grid_data_input:
                if PBBPersistenceBridge.save_grid_data(sheet_name, grid_data_input):
                    st.success(f"✓ Saved {sheet_name} successfully!")
                    st.rerun()
        
        return form_key
    
    @staticmethod
    def generate_persistence_js(sheet_name: str, form_key: str) -> str:
        """Generate JavaScript code to sync grid with Streamlit form"""
        textarea_id = f"grid_data_{sheet_name}".replace(' ', '_').replace('(', '').replace(')', '')
        
        return f"""
        <script>
        // Auto-sync grid data to Streamlit on changes
        function syncGridToStreamlit() {{
            if (!gridApi) {{
                console.warn('Grid API not ready');
                return;
            }}
            
            const allRowData = [];
            gridApi.forEachNode(node => {{
                if (node.data) allRowData.push(node.data);
            }});
            
            const gridDataJson = JSON.stringify(allRowData, null, 2);
            
            // Find the hidden textarea by searching for it
            const textareas = parent.document.querySelectorAll('textarea');
            let targetTextarea = null;
            
            for (const textarea of textareas) {{
                if (textarea.id && textarea.id.includes('{textarea_id}')) {{
                    targetTextarea = textarea;
                    break;
                }}
            }}
            
            if (targetTextarea) {{
                targetTextarea.value = gridDataJson;
                targetTextarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                console.log('Grid data synced to Streamlit:', allRowData.length, 'rows');
            }} else {{
                console.warn('Could not find Streamlit textarea for persistence');
            }}
        }}
        
        // Debounced auto-save every 2 seconds after changes
        let autoSaveTimeout;
        function scheduleAutoSave() {{
            clearTimeout(autoSaveTimeout);
            autoSaveTimeout = setTimeout(() => {{
                syncGridToStreamlit();
            }}, 2000);
        }}
        
        // Hook into grid changes
        if (typeof gridOptions !== 'undefined') {{
            const originalOnCellValueChanged = gridOptions.onCellValueChanged;
            gridOptions.onCellValueChanged = function(event) {{
                if (originalOnCellValueChanged) originalOnCellValueChanged(event);
                scheduleAutoSave();
            }};
        }}
        
        // Save on button clicks
        window.addEventListener('message', function(event) {{
            if (event.data === 'save_grid') {{
                syncGridToStreamlit();
            }}
        }});
        </script>
        """
