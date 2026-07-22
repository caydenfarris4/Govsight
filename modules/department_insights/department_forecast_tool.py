import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression
import json

try:
    from modules.services.config_service import get_config_service
    _svc = get_config_service()
    CONFIG = _svc.get_namespace("city_config")
    if not CONFIG:
        raise ValueError("Empty config")
except Exception:
    try:
        with open("config.json") as f:
            CONFIG = json.load(f)
    except Exception as e:
        CONFIG = {}

# Set page config
st.set_page_config(
    page_title="GovSight Department Forecasting",
    page_icon="",
    layout="wide"
)

# Parse org from query parameters
org = st.query_params.get("org", None)

# Set default values for organization display
org_display_name = "GovSight Portal"
org_theme_color = "#0066cc"

# Handle organization selection logic
if not org or org not in CONFIG:
    # Show organization selection screen
    st.title(" GovSight: Multi-Organization Portal")
    st.markdown("""
    <div style="background-color: #f0f7ff; padding: 15px; border-radius: 5px; border-left: 5px solid #0066cc;">
    Please select an organization to continue:
    </div>
    """, unsafe_allow_html=True)
    
    # Display available organizations with styled cards
    if CONFIG:
        cols = st.columns(min(len(CONFIG), 2))
        for i, (org_name, org_data) in enumerate(CONFIG.items()):
            col_idx = i % len(cols)
            with cols[col_idx]:
                org_title = org_data.get("org_name", org_name)
                theme_color = org_data.get("theme_color", "#0066cc")
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 10px; margin-bottom: 20px; background-color: {theme_color}; color: white;">
                    <h3 style="margin-top: 0;">{org_title}</h3>
                    <p>Database: {org_data.get('database', 'N/A')}</p>
                    <a href="?org={org_name}" target="_self" style="background-color: white; color: {theme_color}; 
                       padding: 8px 16px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                       Access Portal
                    </a>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("No organization configurations found.")
    
    st.stop()
else:
    # We have a valid organization, get the config
    org_config = CONFIG[org]
    org_display_name = org_config.get("org_name", org)
    org_theme_color = org_config.get("theme_color", "#0066cc")

# Password Authentication - Automatic login from query parameter
# Authentication state. A URL parameter must never grant access — the
# previous ?auth=true shortcut was an authentication bypass.
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Check if authentication is required
if not st.session_state.authenticated and "login_password" in org_config:
    st.markdown(f"""
    <div style="max-width: 500px; margin: 100px auto; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); background-color: white; border-top: 5px solid {org_theme_color};">
        <h2 style="text-align: center; color: {org_theme_color};">🔒 {org_display_name} Portal</h2>
        <p style="text-align: center;">Please enter your access password to continue.</p>
    </div>
    """, unsafe_allow_html=True)
    
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if password == org_config["login_password"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
            
    # Also add a link back to main portal
    st.markdown(f"<div style='text-align: center; margin-top: 20px;'><a href='/streamlit_multiorg_frontend.py?org={org}&auth=true' target='_self'>Return to main portal</a></div>", unsafe_allow_html=True)
    
    # Stop execution until authenticated
    st.stop()

# Header with organization info
st.markdown(f"""
<div style="background-color: {org_theme_color}; color: white; padding: 10px 15px; border-radius: 5px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
    <div>
        <h1 style="margin:0"> GovSight Department Forecasting Tool</h1>
        <h3 style="margin:0; opacity:0.8">Organization: {org_display_name}</h3>
    </div>
    <div>
        <a href="/streamlit_multiorg_frontend.py?org={org}&auth=true" target="_self" style="color:white; text-decoration:none; background-color:rgba(255,255,255,0.2); padding:5px 10px; border-radius:5px; margin-right: 10px;">
            Return to Dashboard
        </a>
        <a href="/" target="_self" style="color:white; text-decoration:none; background-color:rgba(255,255,255,0.2); padding:5px 10px; border-radius:5px;">
            Switch Organization
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

# Import our common utilities
import common_utils

# Load database connection utilities from common_utils
get_db_path_for_org = common_utils.get_db_path_for_org
load_org_data = common_utils.load_org_data
get_departments = common_utils.get_departments

# Get database path for the organization
DB_PATH = get_db_path_for_org(org)
if org and org in CONFIG and 'dashboard_db' in CONFIG[org]:
    st.sidebar.markdown(f"**Using custom DB:** {DB_PATH}")

# Load department data for the current organization using our consistent function
df = load_org_data(org)

if df.empty:
    st.warning(f"No data available for {org_display_name}. Please check the database connection.")
    st.stop()

st.title(" Departmental Insights & Forecasting")

# Object Code Grouping
with st.expander(" Custom Fund Grouping", expanded=False):
    st.subheader("Create Custom Fund Groups")
    if "groups" not in st.session_state:
        st.session_state.groups = {}

    group_name = st.text_input("Group Name")
    selected_objects = st.multiselect("Select Funds to Group", df["Fund"].unique())
    if st.button("Create Group"):
        if group_name and selected_objects:
            st.session_state.groups[group_name] = selected_objects
            st.success(f"Group '{group_name}' created.")

    if st.session_state.groups:
        st.write("Your Custom Groups:")
        for name, codes in st.session_state.groups.items():
            st.write(f"**{name}**: {', '.join(codes)}")

# Department Selection
col1, col2 = st.columns([2, 1])

with col1:
    # Department Selection
    departments = sorted(df["Department"].unique())
    selected_dept = st.selectbox("Select Department for Analysis", departments)
    df_dept = df[df["Department"] == selected_dept]

    # Fiscal Year Filter
    fiscal_years = sorted(df_dept["FiscalYear"].unique())
    selected_years = st.multiselect("Select Fiscal Years", fiscal_years, default=fiscal_years)
    
    if selected_years:
        df_dept = df_dept[df_dept["FiscalYear"].isin(selected_years)]
    else:
        st.warning("Please select at least one fiscal year.")
        st.stop()

with col2:
    # Department Summary Metrics
    st.subheader("Department Overview")
    total_budget = df_dept["Budget"].sum()
    total_actual = df_dept["Actual"].sum()
    total_difference = total_budget - total_actual
    difference_percent = (total_difference / total_budget) * 100 if total_budget > 0 else 0
    
    status = "Under Budget" if difference_percent > 0 else "Over Budget"
    status_color = "green" if difference_percent > 0 else "red"
    
    st.metric("Total Budget", f"${total_budget:,.2f}")
    st.metric("Total Actual Spending", f"${total_actual:,.2f}")
    st.metric(
        "Difference", 
        f"${total_difference:,.2f} ({difference_percent:.1f}%)",
        delta_color="normal" if difference_percent > 0 else "inverse"
    )
    st.markdown(f"<div style='color:{status_color}; font-weight:bold;'>{status}</div>", unsafe_allow_html=True)

# Current Actuals by Fund
st.subheader(f"Budget vs. Actuals by Fund – {selected_dept}")
fund_summary = df_dept.groupby("Fund").agg({
    "Budget": "sum",
    "Actual": "sum"
}).reset_index()
fund_summary["Difference"] = fund_summary["Budget"] - fund_summary["Actual"]
fund_summary["Difference%"] = (fund_summary["Difference"] / fund_summary["Budget"]) * 100

# Create a visualization
try:
    import plotly.express as px
    # Horizontal bar chart for fund comparison
    fig = px.bar(
        fund_summary, 
        y="Fund", 
        x=["Budget", "Actual"], 
        barmode="group", 
        orientation="h",
        title=f"{selected_dept} Budget vs. Actual by Fund",
        color_discrete_map={"Budget": "#3498db", "Actual": "#2ecc71"}
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    # Fallback to standard bar chart if plotly express is not available
    st.bar_chart(fund_summary.set_index("Fund")[["Budget", "Actual"]])

# Display the fund data
st.dataframe(fund_summary.style.format({
    "Budget": "${:,.2f}",
    "Actual": "${:,.2f}",
    "Difference": "${:,.2f}",
    "Difference%": "{:.1f}%"
}), use_container_width=True)

# Time Series Analysis
st.subheader(" Budget Trends Over Time")
time_series_df = df_dept.groupby("FiscalYear").agg({
    "Budget": "sum",
    "Actual": "sum"
}).reset_index()

# Create a line chart
fig = px.line(
    time_series_df, 
    x="FiscalYear", 
    y=["Budget", "Actual"],
    markers=True,
    title=f"{selected_dept} Budget and Actual Trends",
    labels={"value": "Amount ($)", "variable": "Type"}
)
st.plotly_chart(fig, use_container_width=True)

# Forecast Button and Logic
st.subheader("🔮 Forecast Future Actuals")
funds = sorted(df_dept["Fund"].unique())
selected_fund = st.selectbox("Choose a Fund to Forecast", funds)

df_fund = df_dept[df_dept["Fund"] == selected_fund]
df_fund_grouped = df_fund.groupby("FiscalYear").agg({
    "Budget": "sum",
    "Actual": "sum"
}).reset_index()

future_periods = st.number_input("How many future years to forecast?", min_value=1, max_value=10, value=3)

if st.button("Generate Forecast"):
    try:
        # First, ensure Budget and Actual are numeric
        try:
            df_fund_grouped['Budget'] = pd.to_numeric(df_fund_grouped['Budget'], errors='coerce')
            df_fund_grouped['Actual'] = pd.to_numeric(df_fund_grouped['Actual'], errors='coerce')
            
            # Drop any rows with NaN values after conversion
            df_fund_grouped = df_fund_grouped.dropna(subset=['Budget', 'Actual'])
            
            if df_fund_grouped.empty:
                st.error("No valid numeric data found for forecasting after data cleaning.")
                st.info("Please check that your data contains valid numeric values for Budget and Actual.")
                raise ValueError("No valid numeric data for forecasting")
        except Exception as data_err:
            st.error(f"Error preparing data for forecasting: {data_err}")
            st.info("Please check that your data contains valid numeric values for Budget and Actual.")
            raise ValueError(f"Data preparation error: {data_err}")
        
        # Prepare data for modeling
        df_fund_grouped["Year_Num"] = range(len(df_fund_grouped))
        
        # Create and train linear regression models for both Budget and Actual
        budget_model = LinearRegression()
        actual_model = LinearRegression()
        
        X = df_fund_grouped[["Year_Num"]]
        y_budget = df_fund_grouped["Budget"]
        y_actual = df_fund_grouped["Actual"]
        
        budget_model.fit(X, y_budget)
        actual_model.fit(X, y_actual)
        
        # Generate future years
        last_year_num = len(X) - 1
        future_years = list(range(last_year_num + 1, last_year_num + 1 + future_periods))
        future_X = np.array(future_years).reshape(-1, 1)
        
        # Get the last fiscal year and predict future fiscal years
        last_year = df_fund_grouped["FiscalYear"].iloc[-1]
        
        # Convert to string for consistent handling
        last_year_str = str(last_year)
        
        # Extract year number if format is like "FY 2024"
        if "FY" in last_year_str:
            try:
                # Find any number in the string
                import re
                year_match = re.search(r'\d+', last_year_str)
                if year_match:
                    year_num = int(year_match.group())
                    future_fiscal_years = [f"FY {year_num + i}" for i in range(1, future_periods + 1)]
                else:
                    future_fiscal_years = [f"Year +{i}" for i in range(1, future_periods + 1)]
            except:
                # If can't parse, just use generic labels
                future_fiscal_years = [f"Year +{i}" for i in range(1, future_periods + 1)]
        else:
            # Try to convert to number and increment
            try:
                year_num = int(float(last_year_str))
                future_fiscal_years = [str(year_num + i) for i in range(1, future_periods + 1)]
            except (ValueError, TypeError):
                future_fiscal_years = [f"Year +{i}" for i in range(1, future_periods + 1)]
        
        # Predict future values
        future_budget = budget_model.predict(future_X)
        future_actual = actual_model.predict(future_X)
        
        # Create forecast dataframe
        forecast_df = pd.DataFrame({
            "FiscalYear": future_fiscal_years,
            "Budget": future_budget,
            "Actual": future_actual,
            "Forecast": True
        })
        
        # Add indicator column to original data
        df_fund_grouped["Forecast"] = False
        
        # Combine historical and forecast data
        combined = pd.concat([df_fund_grouped, forecast_df])
        
        # Visualize the forecast with shaded forecast region
        fig = px.line(
            combined, 
            x="FiscalYear", 
            y=["Budget", "Actual"],
            markers=True,
            title=f"{selected_dept} - {selected_fund} Forecast",
            labels={"value": "Amount ($)", "variable": "Type"}
        )
        
        # Add shaded area for forecast region
        historical_years = len(df_fund_grouped)
        forecast_start = combined["FiscalYear"].iloc[historical_years-1]
        
        # Add vertical line at forecast boundary
        fig.add_vline(
            x=forecast_start, 
            line_dash="dash", 
            line_color="gray", 
            annotation_text="Forecast Start",
            annotation_position="top right"
        )
        
        # Update layout for better visualization
        fig.update_layout(
            xaxis_title="Fiscal Year",
            yaxis_title="Amount ($)",
            legend_title="Type",
            hovermode="x unified"
        )
        
        # Show the forecast visualization
        st.plotly_chart(fig, use_container_width=True)
        
        # Show the forecast data
        st.subheader("Forecast Data")
        st.dataframe(forecast_df.style.format({
            "Budget": "${:,.2f}",
            "Actual": "${:,.2f}"
        }), use_container_width=True)
        
        # Calculate budget variance in forecast
        forecast_df["Variance"] = forecast_df["Budget"] - forecast_df["Actual"]
        forecast_df["Variance%"] = (forecast_df["Variance"] / forecast_df["Budget"]) * 100
        
        avg_variance = forecast_df["Variance"].mean()
        avg_variance_pct = forecast_df["Variance%"].mean()
        
        # Show forecast insights
        st.subheader("Forecast Insights")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Average Forecast Variance", f"${avg_variance:,.2f}")
        with col2:
            st.metric("Average Variance Percentage", f"{avg_variance_pct:.1f}%")
        
        # Recommendation based on forecast
        if avg_variance_pct > 10:
            st.success(" This fund is projected to significantly underspend. Consider reallocating budget to other priorities.")
        elif avg_variance_pct < -10:
            st.error(" This fund is projected to significantly overspend. Consider increasing the budget allocation.")
        else:
            st.info("ℹ️ This fund's spending is projected to closely align with budgeted amounts.")
        
    except Exception as e:
        st.error(f"Error generating forecast: {e}")
        st.info("Make sure you have enough historical data points for a meaningful forecast.")

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #888;">
    GovSight Financial Analyzer - Department Forecasting Tool
    <br>© 2024 GovSight Analytics | Organization: {org_display_name}
</div>
""", unsafe_allow_html=True)