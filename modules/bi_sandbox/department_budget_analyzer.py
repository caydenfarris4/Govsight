"""
Department Budget vs Actual Analysis Module

Creates comprehensive budget variance analysis with visual charts and detailed tables
showing department performance against budget allocations.

ARCHITECTURAL DECISION: Dedicated module for budget analysis
WHY: Separates budget-specific analytics from general BI functionality, allowing
for specialized budget variance calculations and department-focused visualizations
that municipal finance teams need for budget monitoring and variance reporting.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3
from typing import Dict, List, Tuple, Optional
from modules.database.connection_manager import get_database_connection

def get_department_budget_data(org: str = "cityA") -> pd.DataFrame:
    """
    Retrieve department budget vs actual data from the database
    
    DESIGN DECISION: Direct SQL aggregation for performance
    WHY: Pre-aggregating at the database level reduces memory usage and
    provides faster response times for budget variance calculations
    """
    try:
        conn = get_database_connection(org)
        
        query = """
        SELECT 
            Department,
            SUM(Budget) as TotalBudget,
            SUM(Actual) as TotalActual,
            COUNT(*) as AccountCount
        FROM tblGLAccount 
        WHERE Department IS NOT NULL 
        AND Department != ''
        GROUP BY Department
        ORDER BY TotalBudget DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Calculate variance and variance percentage
        df['Variance'] = df['TotalActual'] - df['TotalBudget']
        df['VariancePercent'] = ((df['TotalActual'] - df['TotalBudget']) / df['TotalBudget'] * 100).round(2)
        
        # Add status indicators
        df['Status'] = df['VariancePercent'].apply(lambda x: 
            'Over Budget' if x > 5 else 
            'Under Budget' if x < -5 else 
            'On Track'
        )
        
        return df
        
    except Exception as e:
        st.error(f"Error retrieving department budget data: {str(e)}")
        return pd.DataFrame()

def create_budget_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create interactive budget vs actual comparison chart
    
    VISUALIZATION DECISION: Grouped bar chart with variance indicators
    WHY: Grouped bars clearly show budget vs actual side-by-side comparison
    while color coding provides immediate visual feedback on variance status
    """
    if df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Add budget bars
    fig.add_trace(go.Bar(
        name='Budget',
        x=df['Department'],
        y=df['TotalBudget'],
        marker_color='#4287f5',
        text=[f'${val:,.0f}' for val in df['TotalBudget']],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Budget: $%{y:,.0f}<extra></extra>'
    ))
    
    # Add actual bars with color based on variance
    colors = df['VariancePercent'].apply(lambda x: 
        '#e74c3c' if x > 5 else  # Red for over budget
        '#27ae60' if x < -5 else  # Green for under budget
        '#f39c12'  # Orange for on track
    )
    
    fig.add_trace(go.Bar(
        name='Actual',
        x=df['Department'],
        y=df['TotalActual'],
        marker_color=colors,
        text=[f'${val:,.0f}' for val in df['TotalActual']],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Actual: $%{y:,.0f}<br>Variance: %{customdata:.1f}%<extra></extra>',
        customdata=df['VariancePercent']
    ))
    
    fig.update_layout(
        title={
            'text': 'Department Budget vs Actual Spending Analysis',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2c3e50'}
        },
        xaxis_title='Department',
        yaxis_title='Amount ($)',
        barmode='group',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(t=80, b=60, l=60, r=60)
    )
    
    # Format y-axis to show currency
    fig.update_layout(yaxis=dict(tickformat='$,.0f'))
    
    return fig

def create_variance_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create variance percentage chart showing over/under budget performance
    
    DESIGN DECISION: Horizontal bar chart for variance percentages
    WHY: Horizontal layout better accommodates department names and makes
    it easier to compare variance percentages across departments
    """
    if df.empty:
        return go.Figure()
    
    # Sort by variance percentage for better visualization
    df_sorted = df.sort_values('VariancePercent')
    
    colors = df_sorted['VariancePercent'].apply(lambda x:
        '#e74c3c' if x > 5 else  # Red for over budget
        '#27ae60' if x < -5 else  # Green for under budget  
        '#f39c12'  # Orange for on track
    )
    
    fig = go.Figure(go.Bar(
        x=df_sorted['VariancePercent'],
        y=df_sorted['Department'],
        orientation='h',
        marker_color=colors,
        text=[f'{val:+.1f}%' for val in df_sorted['VariancePercent']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Variance: %{x:+.1f}%<br>Status: %{customdata}<extra></extra>',
        customdata=df_sorted['Status']
    ))
    
    # Add vertical line at 0%
    fig.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
    
    fig.update_layout(
        title={
            'text': 'Budget Variance by Department',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#2c3e50'}
        },
        xaxis_title='Variance Percentage (%)',
        yaxis_title='Department',
        height=300 + len(df_sorted) * 40,  # Dynamic height based on number of departments
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(t=60, b=60, l=120, r=60)
    )
    
    # Add reference zones
    fig.add_vrect(x0=-5, x1=5, fillcolor="lightgray", opacity=0.2, 
                  annotation_text="Target Range", annotation_position="top")
    
    return fig

def create_budget_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create formatted summary table with variance analysis
    
    FORMATTING DECISION: Currency formatting and status indicators
    WHY: Professional municipal finance reporting requires clear currency
    formatting and immediate status identification for budget oversight
    """
    if df.empty:
        return df
    
    # Create display table with formatted columns
    display_df = df.copy()
    
    # Format currency columns with error handling
    def format_currency(x):
        try:
            return f'${float(x):,.0f}'
        except (ValueError, TypeError):
            return str(x)
    
    def format_currency_variance(x):
        try:
            return f'${float(x):+,.0f}'
        except (ValueError, TypeError):
            return str(x)
    
    def format_percentage(x):
        try:
            return f'{float(x):+.1f}%'
        except (ValueError, TypeError):
            return str(x)
    
    display_df['Budget'] = display_df['TotalBudget'].apply(format_currency)
    display_df['Actual'] = display_df['TotalActual'].apply(format_currency)
    display_df['Variance'] = display_df['Variance'].apply(format_currency_variance)
    display_df['Variance %'] = display_df['VariancePercent'].apply(format_percentage)
    
    # Select and reorder columns for display
    summary_df = display_df[['Department', 'Budget', 'Actual', 'Variance', 'Variance %', 'Status', 'AccountCount']].copy()
    summary_df.rename(columns={'AccountCount': 'GL Accounts'}, inplace=True)
    
    return summary_df

def render_department_budget_analysis(org: str = "cityA", org_display_name: str = "Spanish Fork"):
    """
    Main function to render the complete department budget analysis interface
    
    INTERFACE DECISION: Three-panel layout with chart, variance, and table
    WHY: Progressive information disclosure - start with overview chart,
    then detailed variance analysis, then comprehensive data table for
    different levels of analytical depth
    """
    st.markdown("### Department Budget vs Actual Analysis")
    st.markdown(f"**Organization:** {org_display_name}")
    
    # Get budget data
    with st.spinner("Loading department budget data..."):
        budget_df = get_department_budget_data(org)
    
    if budget_df.empty:
        st.warning("No department budget data available for analysis.")
        return
    
    # Display key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    total_budget = budget_df['TotalBudget'].sum()
    total_actual = budget_df['TotalActual'].sum()
    total_variance = total_actual - total_budget
    variance_pct = (total_variance / total_budget * 100) if total_budget > 0 else 0
    
    with col1:
        st.metric("Total Budget", f"${total_budget:,.0f}")
    with col2:
        st.metric("Total Actual", f"${total_actual:,.0f}")
    with col3:
        st.metric("Total Variance", f"${total_variance:+,.0f}", 
                 f"{variance_pct:+.1f}%")
    with col4:
        departments_over = len(budget_df[budget_df['VariancePercent'] > 5])
        st.metric("Depts Over Budget", departments_over)
    
    st.markdown("---")
    
    # Budget comparison chart
    st.markdown("#### Budget vs Actual Comparison")
    budget_chart = create_budget_comparison_chart(budget_df)
    st.plotly_chart(budget_chart, use_container_width=True)
    
    # Variance analysis chart
    st.markdown("#### Variance Analysis")
    variance_chart = create_variance_chart(budget_df)
    st.plotly_chart(variance_chart, use_container_width=True)
    
    # Summary table
    st.markdown("#### Detailed Budget Analysis Table")
    summary_table = create_budget_summary_table(budget_df)
    
    # Color-code the status column
    def highlight_status(val):
        if val == 'Over Budget':
            return 'background-color: #fadbd8'
        elif val == 'Under Budget':
            return 'background-color: #d5f4e6'
        else:
            return 'background-color: #fdeaa7'
    
    styled_table = summary_table.style.applymap(highlight_status, subset=['Status'])
    st.dataframe(styled_table, use_container_width=True, hide_index=True)
    
    # Export options
    st.markdown("#### Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export Chart Data to CSV", use_container_width=True):
            csv_data = budget_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"department_budget_analysis_{org}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📈 Export Summary Table", use_container_width=True):
            summary_csv = summary_table.to_csv(index=False)
            st.download_button(
                label="Download Summary CSV",
                data=summary_csv,
                file_name=f"budget_variance_summary_{org}.csv",
                mime="text/csv"
            )
    
    # Analysis insights
    st.markdown("#### Key Insights")
    
    # Generate automated insights
    over_budget_depts = budget_df[budget_df['VariancePercent'] > 5]
    under_budget_depts = budget_df[budget_df['VariancePercent'] < -5]
    
    insights = []
    
    if len(over_budget_depts) > 0:
        max_variance_idx = over_budget_depts['VariancePercent'].argmax()
        worst_performer = over_budget_depts.iloc[max_variance_idx]
        insights.append(f"🔴 **{worst_performer['Department']}** is the most over budget at {worst_performer['VariancePercent']:+.1f}% (${worst_performer['Variance']:+,.0f})")
    
    if len(under_budget_depts) > 0:
        min_variance_idx = under_budget_depts['VariancePercent'].argmin()
        best_performer = under_budget_depts.iloc[min_variance_idx]
        insights.append(f"🟢 **{best_performer['Department']}** is significantly under budget at {best_performer['VariancePercent']:+.1f}% (${best_performer['Variance']:+,.0f})")
    
    on_track_depts = budget_df[(budget_df['VariancePercent'] >= -5) & (budget_df['VariancePercent'] <= 5)]
    if len(on_track_depts) > 0:
        insights.append(f"✅ **{len(on_track_depts)} department(s)** are within the target variance range of ±5%")
    
    insights.append(f"📊 **Overall organization** variance is {variance_pct:+.1f}% with total variance of ${total_variance:+,.0f}")
    
    for insight in insights:
        st.markdown(f"- {insight}")