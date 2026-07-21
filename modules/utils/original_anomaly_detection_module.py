import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.ensemble import IsolationForest
import streamlit as st
from mask_parser import get_mask_from_settings, parse_account

def detect_anomalies(df, feature_cols=['Budget', 'Actual', 'PercentUsed']):
    """
    Detect budget anomalies using IsolationForest
    Returns dataframe with 'Anomaly' flag and 'Score'
    """
    model = IsolationForest(n_estimators=100, contamination='auto', random_state=42)
    df_clean = df[feature_cols].dropna()
    df_result = df.copy()

    if not df_clean.empty:
        model.fit(df_clean)
        df_result['Anomaly Score'] = model.decision_function(df_clean)
        df_result['Anomaly Flag'] = model.predict(df_clean)
        df_result['Anomaly Flag'] = df_result['Anomaly Flag'].apply(lambda x: 'Anomaly' if x == -1 else 'Normal')
    else:
        df_result['Anomaly Score'] = np.nan
        df_result['Anomaly Flag'] = 'No Data'

    return df_result

def render_anomaly_analysis(dept_data):
    st.subheader(" Budget Anomaly Detector")
    if dept_data.empty:
        st.warning("No department data available.")
        return

    # Create a copy to avoid modifying the original data
    df_work = dept_data.copy()
    
    if 'PercentUsed' not in df_work.columns:
        if 'Actual' in df_work.columns and 'Budget' in df_work.columns:
            df_work['PercentUsed'] = (df_work['Actual'] / df_work['Budget']) * 100

    # Parse department information from account codes using mask parsing
    try:
        # Get masks from settings
        balance_sheet_mask = get_mask_from_settings("balance_sheet")
        revenue_mask = get_mask_from_settings("revenue")
        expense_mask = get_mask_from_settings("expense")
        
        # Add department parsing based on AccountCode if available
        if 'AccountCode' in df_work.columns:
            df_work['Department'] = None
            df_work['DeptCode'] = None
            
            for idx, row in df_work.iterrows():
                account_code = str(row['AccountCode'])
                
                # Try parsing with expense mask first (most common for department analysis)
                if expense_mask:
                    try:
                        parsed = parse_account(account_code, expense_mask)
                        if 'Dept' in parsed:
                            df_work.at[idx, 'DeptCode'] = parsed['Dept']
                            # Map department codes to names
                            dept_mapping = {
                                '01': 'Administration',
                                '02': 'Finance', 
                                '03': 'Police',
                                '04': 'Fire',
                                '05': 'Public Works',
                                '06': 'Parks & Recreation'
                            }
                            df_work.at[idx, 'Department'] = dept_mapping.get(parsed['Dept'], f"Department {parsed['Dept']}")
                    except:
                        pass
                
                # Fallback to other masks if expense didn't work
                if pd.isna(df_work.at[idx, 'Department']):
                    for mask in [balance_sheet_mask, revenue_mask]:
                        if mask:
                            try:
                                parsed = parse_account(account_code, mask)
                                if 'Dept' in parsed:
                                    df_work.at[idx, 'DeptCode'] = parsed['Dept']
                                    dept_mapping = {
                                        '01': 'Administration',
                                        '02': 'Finance', 
                                        '03': 'Police',
                                        '04': 'Fire',
                                        '05': 'Public Works',
                                        '06': 'Parks & Recreation'
                                    }
                                    df_work.at[idx, 'Department'] = dept_mapping.get(parsed['Dept'], f"Department {parsed['Dept']}")
                                    break
                            except:
                                continue
            
            # If we couldn't parse any departments, use existing Department column if available
            if df_work['Department'].isna().all() and 'DepartmentName' in df_work.columns:
                df_work['Department'] = df_work['DepartmentName']
                
    except Exception as e:
        # Fallback: use existing department information if available
        if 'DepartmentName' in df_work.columns:
            df_work['Department'] = df_work['DepartmentName']
        elif 'Department' not in df_work.columns:
            df_work['Department'] = 'Unknown Department'

    df_result = detect_anomalies(df_work)
    
    # Filter for actual anomalies
    anomalies = df_result[df_result['Anomaly Flag'] == 'Anomaly']
    normal_data = df_result[df_result['Anomaly Flag'] == 'Normal']
    
    # Show anomaly summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", len(df_result))
    with col2:
        st.metric("Anomalies Found", len(anomalies), delta=f"{len(anomalies)/len(df_result)*100:.1f}%")
    with col3:
        if len(anomalies) > 0:
            avg_anomaly_score = anomalies['Anomaly Score'].mean()
            st.metric("Avg Anomaly Score", f"{avg_anomaly_score:.3f}")
        else:
            st.metric("Avg Anomaly Score", "N/A")
    
    # Show anomalies table with Excel-style filtering
    if len(anomalies) > 0:
        st.subheader("🚨 Detected Anomalies")
        st.data_editor(
            anomalies[['Fund', 'FiscalYear', 'Budget', 'Actual', 'PercentUsed', 'Anomaly Score']],
            use_container_width=True,
            hide_index=True,
            disabled=True,
            height=300,
            column_config={
                "Budget": st.column_config.NumberColumn(format="$%.0f"),
                "Actual": st.column_config.NumberColumn(format="$%.0f"),
                "PercentUsed": st.column_config.NumberColumn(format="%.1f%%"),
                "Anomaly Score": st.column_config.NumberColumn(format="%.3f")
            }
        )
    else:
        st.success(" No budget anomalies detected in the selected data.")
    
    # Create better visualizations
    try:
        # 1. Bar chart showing anomaly scores by record
        if len(df_result) > 0:
            st.subheader(" Anomaly Scores by Record")
            
            # Sort by anomaly score for better visualization
            df_sorted = df_result.sort_values('Anomaly Score', ascending=True)
            
            # Create meaningful x-axis labels combining Department and Year
            df_sorted['Record_Label'] = df_sorted.apply(
                lambda row: f"{row.get('Department', 'Unknown')} - {row.get('FiscalYear', 'N/A')}", 
                axis=1
            )
            
            # Create bar chart with color coding
            fig = px.bar(
                df_sorted,
                x='Record_Label',
                y='Anomaly Score',
                color='Anomaly Flag',
                hover_data=['Budget', 'Actual', 'PercentUsed', 'Department'],
                title='Anomaly Scores by Department and Year (Sorted Most to Least Anomalous)',
                color_discrete_map={'Anomaly': '#d32f2f', 'Normal': '#004AAD'}
            )
            
            fig.update_layout(
                xaxis_title='Department - Fiscal Year',
                yaxis_title='Anomaly Score (lower = more anomalous)',
                height=400,
                xaxis={'tickangle': 45}  # Rotate labels for better readability
            )
            
            # Add threshold line
            if len(anomalies) > 0:
                threshold = anomalies['Anomaly Score'].max()
                fig.add_hline(y=threshold, line_dash="dash", line_color="red", 
                             annotation_text="Anomaly Threshold")
            
            st.plotly_chart(fig, use_container_width=True)
        
        # 2. Heatmap of spending patterns if we have multiple years/departments
        if 'FiscalYear' in df_result.columns and 'Department' in df_result.columns:
            st.subheader(" Spending Pattern Heatmap")
            
            # Create pivot table for heatmap
            heatmap_data = df_result.pivot_table(
                values='PercentUsed', 
                index='Department', 
                columns='FiscalYear', 
                aggfunc='mean'
            ).fillna(0)
            
            if not heatmap_data.empty:
                fig = px.imshow(
                    heatmap_data,
                    title='Budget Utilization % by Department and Year',
                    color_continuous_scale='RdYlBu_r',
                    aspect='auto'
                )
                
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        # 3. Box plot showing distribution with outliers highlighted
        if len(df_result) > 3:
            st.subheader(" Budget Distribution Analysis")
            
            fig = px.box(
                df_result,
                y='PercentUsed',
                color='Anomaly Flag',
                title='Budget Utilization Distribution',
                color_discrete_map={'Anomaly': '#d32f2f', 'Normal': '#004AAD'}
            )
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.warning(f"Could not generate enhanced visualizations: {e}")
        
    # Show full data table at the bottom
    st.subheader(" Complete Analysis Data")
    st.data_editor(
        df_result[['Fund', 'FiscalYear', 'Budget', 'Actual', 'PercentUsed', 'Anomaly Score', 'Anomaly Flag']],
        use_container_width=True,
        hide_index=True,
        disabled=True,
        height=400,
        column_config={
            "Budget": st.column_config.NumberColumn(format="$%.0f"),
            "Actual": st.column_config.NumberColumn(format="$%.0f"),
            "PercentUsed": st.column_config.NumberColumn(format="%.1f%%"),
            "Anomaly Score": st.column_config.NumberColumn(format="%.3f")
        }
    )