"""
Demo script showing how to use the audit trail system for GL database operations

This demonstrates how to replace dangerous delete operations with audited ones
"""

import streamlit as st
import pandas as pd
from modules.database.audit_trail_manager import safe_delete_with_audit, audit_manager

def demo_audited_delete():
    """Demo function showing audited delete operation"""
    
    st.markdown("### 🧪 Demo: Audited Database Delete Operations")
    st.markdown("This demo shows how the audit trail captures all delete operations on GL databases.")
    
    # Get user context for demo
    user = st.session_state.get('user', {})
    user_context = {
        'user_id': user.get('username', 'demo_user'),
        'user_role': user.get('role', 'admin'),
        'session_id': st.session_state.get('session_id', 'demo_session'),
        'reason': 'Demo of audit trail functionality'
    }
    
    # Demo: Show how to safely delete with audit
    st.markdown("#### Example: Delete old budget entries")
    
    if st.button("🗑️ Demo Delete with Audit Trail"):
        # Example delete operation with audit trail
        result = safe_delete_with_audit(
            database_name="gl_primary",
            table_name="budget_line_items",
            delete_query="DELETE FROM budget_line_items WHERE fiscal_year < 2020",
            user_context=user_context
        )
        
        if result['success']:
            st.success(f"✅ {result['message']}")
            if result['audit_id']:
                st.info(f"🔍 Audit ID: {result['audit_id']} - All deleted data has been preserved in audit trail")
        else:
            st.error(f"❌ {result['message']}")
    
    # Show recent audit trail
    st.markdown("#### Recent Delete Operations")
    try:
        recent_audits = audit_manager.get_audit_trail(limit=10)
        if not recent_audits.empty:
            st.dataframe(recent_audits[['delete_timestamp', 'gl_database', 'table_name', 'deleted_record_count', 'user_id', 'operation_reason']])
        else:
            st.info("No audit records found. Perform a delete operation to see audit trail in action.")
    except Exception as e:
        st.error(f"Error loading audit trail: {e}")

def show_integration_examples():
    """Show code examples for integrating audit trail"""
    
    st.markdown("### 💻 Integration Examples")
    st.markdown("How to integrate audit trail into existing code:")
    
    # Example 1: Before/After comparison
    st.markdown("#### ❌ Before - Dangerous Delete")
    st.code("""
# OLD: Direct delete - NO audit trail
def delete_old_records():
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE date < '2020-01-01'")
    conn.commit()
    conn.close()
    return "Records deleted"  # No idea what was deleted!
    """, language="python")
    
    st.markdown("#### ✅ After - Safe Delete with Audit")
    st.code("""
# NEW: Audited delete - Full audit trail
def delete_old_records_safely():
    from modules.database.audit_trail_manager import safe_delete_with_audit
    
    user_context = {
        'user_id': st.session_state.get('username', 'unknown'),
        'user_role': st.session_state.get('role', 'unknown'),
        'session_id': st.session_state.get('session_id'),
        'reason': 'Cleanup old transaction records per policy'
    }
    
    result = safe_delete_with_audit(
        database_name="gl_primary",
        table_name="transactions", 
        delete_query="DELETE FROM transactions WHERE date < '2020-01-01'",
        user_context=user_context
    )
    
    return result  # Full details + audit trail created
    """, language="python")
    
    # Example 2: Manual logging
    st.markdown("#### 🔧 Manual Audit Logging")
    st.code("""
# For complex operations, log manually
from modules.database.audit_trail_manager import audit_manager

# Capture data before deletion
deleted_data = pd.read_sql("SELECT * FROM accounts WHERE status='closed'", conn)

# Perform deletion
cursor.execute("DELETE FROM accounts WHERE status='closed'")

# Log to audit trail
audit_id = audit_manager.log_delete_operation(
    database_name="gl_primary",
    table_name="accounts",
    delete_criteria="status='closed'", 
    deleted_data=deleted_data,
    user_id="finance_user",
    operation_reason="Closed account cleanup"
)

print(f"Audit ID: {audit_id}")
    """, language="python")

def show_recovery_demo():
    """Demo data recovery functionality"""
    
    st.markdown("### 🔄 Data Recovery Demo")
    st.markdown("How to recover deleted data from audit trail:")
    
    # Get list of audit records for demo
    try:
        audits = audit_manager.get_audit_trail(limit=5)
        if not audits.empty:
            # Show audit records
            st.markdown("#### Available Recovery Points")
            for idx, row in audits.iterrows():
                with st.expander(f"Audit ID {row['id']}: {row['table_name']} - {row['deleted_record_count']} records"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **Deleted:** {row['delete_timestamp']}  
                        **Table:** {row['table_name']}  
                        **Records:** {row['deleted_record_count']}  
                        **User:** {row['user_id']}  
                        **Reason:** {row['operation_reason']}
                        """)
                    
                    with col2:
                        if st.button(f"🔍 View Data", key=f"view_{row['id']}"):
                            # Show deleted data
                            deleted_info = audit_manager.get_deleted_data(row['id'])
                            if 'error' not in deleted_info:
                                st.json(deleted_info['deleted_data'])
                                st.success("✅ Data integrity verified")
                            else:
                                st.error(deleted_info['error'])
        else:
            st.info("No audit records available for recovery demo.")
    
    except Exception as e:
        st.error(f"Error loading recovery demo: {e}")

if __name__ == "__main__":
    # This would be called from within the admin panel or a dedicated page
    demo_audited_delete()
    st.markdown("---")
    show_integration_examples() 
    st.markdown("---")
    show_recovery_demo()