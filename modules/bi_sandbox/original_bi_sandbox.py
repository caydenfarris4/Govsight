"""
BI Sandbox Module

This module offers a self-service BI environment where users can:
- Select dimensions and values to analyze
- Create various visualizations (tables, charts)
- Save and manage scenarios
- Export results to CSV or PDF
- Generate comprehensive reports
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import sqlite3
import base64

# Import mask parser for account code interpretation
from mask_parser import get_mask_from_settings, parse_account
import tempfile
import os
import sys
from db_connection import (
    get_db_path_for_org, 
    format_currency, 
    format_percentage, 
    get_detailed_scenario_data,
    load_org_data
)

# Import security module
from modules.admin.admin_panel import get_user_departments, is_admin, is_finance_director

# Import report generator module
import summary_report_generator as report_gen

# Import AI Hub for enhanced PDF functions and forecasting
from ai_hub import generate_multi_chart_report, generate_forecast

def run_bi_sandbox():
    """
    Run the BI Sandbox with security features
    """
    st.title("GovSight: Self-Service BI Sandbox")

    df = load_org_data()
    if df.empty:
        st.warning("No data found.")
        st.stop()

    # Apply department security filter
    allowed_depts = get_user_departments()
    if allowed_depts and not df.empty:
        # Check if "DepartmentName" or "Department" column exists
        dept_col = None
        if "DepartmentName" in df.columns:
            dept_col = "DepartmentName"
        elif "Department" in df.columns:
            dept_col = "Department"
        
        # Apply filter only if the department column exists
        if dept_col:
            df = df[df[dept_col].isin(allowed_depts)]
        else:
            st.warning("Department column not found in data. Security filtering disabled.")

    st.header("Field Selection")
    
    # Column names are now hidden from the UI
    
    # Create two columns for the field selection interface
    col1, col2 = st.columns(2)
    
    with col1:
        # Adjusted to use the actual column names from the dataframe
        dimensions = st.multiselect("Select dimensions (X-axis)", 
                                   df.columns.tolist(), 
                                   default=[df.columns[0] if not df.empty and len(df.columns) > 0 else ""])
        
        # Make all columns available for Y-axis
        measure_options = df.columns.tolist()
        
        # Add a "Budget - Actual" option if both Budget and Actual columns exist
        if "Budget" in measure_options and "Actual" in measure_options:
            measure_options.append("Budget - Actual")
        
        if not measure_options:
            st.error("No columns found in the data for Y-axis selection.")
            measure_options = ["No columns"]
        
        # Set default to "Actual" if it exists in the options
        default_index = measure_options.index("Actual") if "Actual" in measure_options else 0
        value = st.selectbox("Select value to measure (Y-axis)", 
                           measure_options,
                           index=default_index)
    
    with col2:
        agg_func = st.selectbox("Aggregation Method", ["sum", "mean", "max", "min"])
        chart_type = st.selectbox("Chart Type", ["Table", "Bar", "Line", "Pie"])

    if value == "Budget - Actual":
        df["Budget - Actual"] = df["Budget"] - df["Actual"]
    
    # Check if dimensions is empty or None
    if not dimensions:
        st.error("Please select at least one dimension for the X-axis.")
        grouped = df.head(10)  # Show a sample of data instead of grouping
    else:
        try:
            # Use a safer way to reset the index that avoids duplicate column names
            grouped = df.groupby(dimensions, as_index=False).agg({value: agg_func})
        except Exception as e:
            st.error(f"Error grouping data: {e}")
            # Show helpful message and fallback to showing raw data
            st.info("Try selecting different columns or aggregation methods.")
            grouped = df.head(10)
    
    # Display data table with Excel-style filtering
    st.subheader("Data Table")
    
    # Use Streamlit's data editor with Excel-style column filtering
    st.data_editor(
        grouped,
        use_container_width=True,
        hide_index=True,
        disabled=True,  # Make it read-only with filtering enabled
        height=400,
        column_config={
            col: st.column_config.NumberColumn(
                format="$%.2f" if col in ["Budget", "Actual", value] and "%" not in col else None
            ) if grouped[col].dtype in ['int64', 'float64'] else None
            for col in grouped.columns
        }
    )
    
    # Add export option
    if len(grouped) > 0:
        csv_data = grouped.to_csv(index=False)
        st.download_button(
            label="Download Data as CSV",
            data=csv_data,
            file_name=f"bi_sandbox_data.csv",
            mime="text/csv"
        )

    # Initialize chart list in session state if not there
    if "charts" not in st.session_state:
        st.session_state["charts"] = []

    st.subheader("Preview Visualization")
    
    # Initialize forecast-related variables in session state for persistence
    if "show_forecast_on_chart" not in st.session_state:
        st.session_state.show_forecast_on_chart = False
    
    # Create visualization preview
    if chart_type == "Table":
        st.dataframe(grouped)
    elif not dimensions:
        st.warning("Please select at least one dimension for the X-axis to create a visualization.")
    elif chart_type == "Bar":
        try:
            # Check if forecast data exists and should be shown
            has_forecast_data = False
            forecast_df = None
            
            # Forecast from session state
            if 'forecast_data' in st.session_state and st.session_state.show_forecast_on_chart:
                forecast_info = st.session_state.forecast_data
                forecast_df = forecast_info['forecast_df']
                forecast_time_dim = forecast_info['time_dim']
                display_time_dim = forecast_info.get('display_time_dim', forecast_time_dim)
                forecast_value = forecast_info['value']
                ci = forecast_info.get('ci', 80)
                
                if forecast_value == value:
                    has_forecast_data = (forecast_df is not None and 
                                      not forecast_df.empty and 
                                      'Source' in forecast_df.columns)
                else:
                    st.warning("Forecast is for a different value than currently selected")
            
            # Create the base chart
            fig = px.bar(grouped, x=dimensions[0], y=value, 
                      color=dimensions[1] if len(dimensions) > 1 and not has_forecast_data else None, 
                      barmode="group", 
                      labels={"_index": dimensions[0]})
            
            # Add forecast bars if available
            forecast_data_in_session = 'forecast_data' in st.session_state
            
            # Check if forecast data exists in session state
            if has_forecast_data or (forecast_data_in_session and st.session_state.show_forecast_on_chart):
                # Get forecast data from session state if needed
                if forecast_data_in_session and st.session_state.show_forecast_on_chart:
                    forecast_info = st.session_state.forecast_data
                    forecast_df = forecast_info['forecast_df']
                    forecast_time_dim = forecast_info['time_dim']
                    display_time_dim = forecast_info['display_time_dim']
                    forecast_value = forecast_info['value']
                    
                    # Only use if value matches current selection
                    if forecast_value != value:
                        st.warning("Forecast is for a different value than currently selected")
                        has_forecast_data = False
                    else:
                        has_forecast_data = True
                # For clarity in the visualization
                fig.data[0].name = "Actual" if len(dimensions) <= 1 else fig.data[0].name
                
                # Get forecast data
                forecast = forecast_df[forecast_df["Source"] == "Forecast"]
                
                # Determine which x-axis column to use (handle Month_Display for month names)
                x_col = dimensions[0]
                # Only use these variables if they exist
                if 'forecast_data' in st.session_state and 'forecast_info' in locals():
                    # Get display_time_dim from session state if available
                    display_time_dim = forecast_info.get('display_time_dim', forecast_info.get('time_dim', x_col))
                    if x_col == 'Month' and display_time_dim == 'Month_Display' and 'Month_Display' in forecast.columns:
                        x_col = 'Month_Display'
                
                try:
                    if x_col == 'Month' and 'Month_Numeric' in forecast.columns:
                        # Create a temp mapping back to month names if needed
                        inverse_month_map = {
                            1: 'January', 2: 'February', 3: 'March', 4: 'April',
                            5: 'May', 6: 'June', 7: 'July', 8: 'August',
                            9: 'September', 10: 'October', 11: 'November', 12: 'December'
                        }
                        
                        # Make sure Month_Numeric is the right type for mapping
                        forecast['Month_Numeric'] = forecast['Month_Numeric'].astype(int)
                        forecast['Month'] = forecast['Month_Numeric'].map(inverse_month_map)
                        
                        # Handle any missing mappings
                        if forecast['Month'].isna().any():
                            # Fallback: use original values where mapping failed
                            mask = forecast['Month'].isna()
                            forecast.loc[mask, 'Month'] = forecast.loc[mask, 'Month_Numeric'].astype(str) + ' (month)'
                except Exception as e:
                    # If anything goes wrong, make sure we can still use Month for display
                    st.warning(f"Month conversion warning: {e}")
                    if 'Month_Numeric' in forecast.columns and 'Month' not in forecast.columns:
                        forecast['Month'] = forecast['Month_Numeric'].astype(str)
                
                # Add the forecast trace
                fig.add_trace(
                    go.Bar(
                        x=forecast[x_col if x_col in forecast.columns else dimensions[0]],
                        y=forecast[value],
                        name="Forecast",
                        marker_color='#e67e22'
                    )
                )
                
                # Update title to indicate forecast is included
                fig.update_layout(title=f"{value} by {dimensions[0]} with Forecast")
            
            # Display the chart
            st.plotly_chart(fig, use_container_width=True)
            
            # If we have forecast data, display a legend explaining the forecast
            if has_forecast_data:
                st.info("**Forecast included:** Orange bars show forecasted values.")
            
        except Exception as e:
            st.error(f"Error creating bar chart: {e}")
            st.info("Try selecting different dimensions or values.")
    elif chart_type == "Line":
        try:
            # Add error protection for dimensions list
            if not dimensions or len(dimensions) == 0:
                st.error("Please select at least one dimension for the X-axis")
                return
                
            # Check if forecast data exists and should be shown
            has_forecast_data = False
            forecast_df = None
            
            # Forecast from session state
            if 'forecast_data' in st.session_state and st.session_state.show_forecast_on_chart:
                forecast_info = st.session_state.forecast_data
                forecast_df = forecast_info['forecast_df']
                forecast_time_dim = forecast_info['time_dim']
                display_time_dim = forecast_info.get('display_time_dim', forecast_time_dim)
                forecast_value = forecast_info['value']
                ci = forecast_info.get('ci', 80)
                
                if forecast_value == value:
                    has_forecast_data = (forecast_df is not None and 
                                      not forecast_df.empty and 
                                      'Source' in forecast_df.columns)
                else:
                    st.warning("Forecast is for a different value than currently selected")
            
            # Create the base chart
            fig = px.line(grouped, x=dimensions[0], y=value, 
                       color=dimensions[1] if len(dimensions) > 1 and not has_forecast_data else None)
            
            # Add forecast lines if available
            forecast_data_in_session = 'forecast_data' in st.session_state
            
            # Check if forecast data exists in session state
            if has_forecast_data or (forecast_data_in_session and st.session_state.show_forecast_on_chart):
                # Get forecast data from session state if needed
                if forecast_data_in_session and st.session_state.show_forecast_on_chart:
                    forecast_info = st.session_state.forecast_data
                    forecast_df = forecast_info['forecast_df']
                    forecast_time_dim = forecast_info['time_dim']
                    display_time_dim = forecast_info['display_time_dim']
                    forecast_value = forecast_info['value']
                    ci = forecast_info.get('ci', 80)
                    
                    # Only use if value matches current selection
                    if forecast_value != value:
                        st.warning("Forecast is for a different value than currently selected")
                        has_forecast_data = False
                    else:
                        has_forecast_data = True
                # For clarity in the visualization
                if len(dimensions) <= 1:
                    fig.data[0].name = "Actual"
                
                # Get forecast data
                forecast = forecast_df[forecast_df["Source"] == "Forecast"]
                historical = forecast_df[forecast_df["Source"] == "Actual"]
                
                # Determine which x-axis column to use (handle Month_Display for month names)
                x_col = dimensions[0] 
                # Only use these variables if they exist and are defined
                if 'forecast_data' in st.session_state and 'forecast_info' in locals() and 'forecast_time_dim' in locals():
                    # Get display_time_dim from session state if available
                    display_time_dim = forecast_info.get('display_time_dim', forecast_time_dim)
                    if x_col == 'Month' and display_time_dim == 'Month_Display' and 'Month_Display' in forecast.columns:
                        x_col = 'Month_Display'
                
                # Handle month numeric mapping if available
                try:
                    if x_col == 'Month' and 'Month_Numeric' in forecast.columns:
                        # Create a temp mapping back to month names if needed
                        inverse_month_map = {
                            1: 'January', 2: 'February', 3: 'March', 4: 'April',
                            5: 'May', 6: 'June', 7: 'July', 8: 'August',
                            9: 'September', 10: 'October', 11: 'November', 12: 'December'
                        }
                        
                        # Make sure Month_Numeric is the right type for mapping
                        forecast['Month_Numeric'] = forecast['Month_Numeric'].astype(int)
                        forecast['Month'] = forecast['Month_Numeric'].map(inverse_month_map)
                        
                        # Handle any missing mappings
                        if forecast['Month'].isna().any():
                            # Fallback: use original values where mapping failed
                            mask = forecast['Month'].isna()
                            forecast.loc[mask, 'Month'] = forecast.loc[mask, 'Month_Numeric'].astype(str) + ' (month)'
                except Exception as e:
                    # If anything goes wrong, make sure we can still use Month for display
                    st.warning(f"Month conversion warning: {e}")
                    if 'Month_Numeric' in forecast.columns and 'Month' not in forecast.columns:
                        forecast['Month'] = forecast['Month_Numeric'].astype(str)
                
                # Add the forecast trace with a dashed line
                fig.add_trace(
                    go.Scatter(
                        x=forecast[x_col if x_col in forecast.columns else dimensions[0]],
                        y=forecast[value],
                        mode='lines+markers',
                        name='Forecast',
                        line=dict(color='#e67e22', width=2, dash='dash'),
                        marker=dict(size=8)
                    )
                )
                
                # Add confidence interval if configured
                if 'ci' in locals() and ci > 0:
                    # Calculate error margins based on confidence level
                    ci_factor = ci / 100.0
                    
                    # Estimate error margin based on historical volatility
                    if len(historical[value]) > 1:
                        std_dev = historical[value].std()
                        error_margin = std_dev * ci_factor
                        
                        # Create upper and lower bounds
                        forecast_upper = forecast[value] + error_margin
                        forecast_lower = forecast[value] - error_margin
                        
                        # Add confidence interval
                        fig.add_trace(
                            go.Scatter(
                                x=forecast[x_col if x_col in forecast.columns else dimensions[0]],
                                y=forecast_upper,
                                mode='lines',
                                name=f'Upper {ci}% CI',
                                line=dict(width=0),
                                showlegend=False
                            )
                        )
                        
                        fig.add_trace(
                            go.Scatter(
                                x=forecast[x_col if x_col in forecast.columns else dimensions[0]],
                                y=forecast_lower,
                                mode='lines',
                                name=f'Lower {ci}% CI',
                                line=dict(width=0),
                                fill='tonexty',
                                fillcolor='rgba(230, 126, 34, 0.2)',
                                showlegend=False
                            )
                        )
                
                # Add a vertical line at the forecast start point if we have historical data
                if not historical.empty:
                    # Get the last historical point's x value
                    time_dim = dimensions[0]
                    last_historical = historical[time_dim].iloc[-1]
                    
                    # Add vertical line 
                    fig.add_vline(
                        x=last_historical,
                        line_width=1,
                        line_dash="dash",
                        line_color="gray",
                        annotation_text="Forecast Start",
                        annotation_position="top right"
                    )
                
                # Update title to indicate forecast is included
                fig.update_layout(title=f"{value} by {dimensions[0]} with Forecast")
            
            # Display the chart
            st.plotly_chart(fig, use_container_width=True)
            
            # If we have forecast data, display a legend explaining the forecast
            if has_forecast_data:
                st.info("**Forecast included:** Orange dashed line shows forecasted values. Shaded area represents confidence interval.")
            
        except Exception as e:
            st.error(f"Error creating line chart: {e}")
            st.info("Try selecting different dimensions or values.")
    elif chart_type == "Pie":
        try:
            if len(grouped) > 30:
                st.warning("Too many slices for pie chart. Try filtering or grouping differently.")
            else:
                fig = px.pie(grouped, names=dimensions[0], values=value)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating pie chart: {e}")
            st.info("Try selecting different dimensions or values.")
    
    # The show_forecast_on_chart variable is already initialized at the top of the visualization section
    
    # Add forecasting option as a separate feature
    if chart_type in ["Bar", "Line"] and not dimensions:
        st.warning("Please select at least one dimension for the X-axis to enable forecasting.")
    elif chart_type in ["Bar", "Line"]:
        # Option to add forecast directly to the existing chart - use session state for persistence
        st.session_state.show_forecast_on_chart = st.checkbox("Show Forecast on Current Chart", 
                                       value=st.session_state.show_forecast_on_chart,
                                       help="Enable to add forecast lines directly on the current chart")
        
        # Create an expander for forecast settings (auto-expanded when forecast is enabled)
        with st.expander("Forecast Settings", expanded=st.session_state.show_forecast_on_chart):
            st.info("Add forecasting to predict future values based on historical trends")
            
            # Check if we have time-based dimensions
            time_dim = None
            for dim in dimensions:
                if any(time_word in dim.lower() for time_word in ["year", "month", "date", "time", "period", "fiscal"]):
                    time_dim = dim
                    break
            
            if not time_dim:
                st.warning("No time-based dimension detected. For forecasting, please select a dimension like 'Year', 'Month', 'Date', or 'FiscalYear' in your X-axis.")
            else:
                # Create forecasting parameters
                forecast_col1, forecast_col2 = st.columns(2)
                
                with forecast_col1:
                    # Number of periods to forecast
                    periods = st.slider("Number of Periods to Forecast", 1, 10, 3)
                
                with forecast_col2:
                    # Confidence level
                    ci = st.slider("Confidence Level (%)", 50, 95, 80, 5)
                
                # Decide on button text based on whether we're showing forecast on current chart
                button_text = "Apply Forecast to Chart" if st.session_state.show_forecast_on_chart else "Generate Forecast"
                
                # Add button to generate forecast
                if st.button(button_text):
                    with st.spinner("Generating forecast..."):
                        try:
                            # Make sure data is sorted by time dimension
                            df_forecast = grouped.copy()
                            
                            # Sort months in chronological order if the time_dim is 'Month'
                            if time_dim.lower() == 'month':
                                # Create month order mapping
                                month_order = {
                                    'january': 1, 'jan': 1, 'jan.': 1,
                                    'february': 2, 'feb': 2, 'feb.': 2,
                                    'march': 3, 'mar': 3, 'mar.': 3,
                                    'april': 4, 'apr': 4, 'apr.': 4,
                                    'may': 5,
                                    'june': 6, 'jun': 6, 'jun.': 6,
                                    'july': 7, 'jul': 7, 'jul.': 7,
                                    'august': 8, 'aug': 8, 'aug.': 8,
                                    'september': 9, 'sep': 9, 'sep.': 9, 'sept': 9, 'sept.': 9,
                                    'october': 10, 'oct': 10, 'oct.': 10,
                                    'november': 11, 'nov': 11, 'nov.': 11,
                                    'december': 12, 'dec': 12, 'dec.': 12
                                }
                                
                                # Create temporary column for sorting
                                df_forecast['__month_order'] = df_forecast[time_dim].str.lower().map(month_order)
                                
                                # Sort by the numeric month order
                                df_forecast = df_forecast.sort_values(by='__month_order').drop(columns=['__month_order'])
                                st.write("Debug: Sorted months in chronological order")
                            else:
                                # For other time dimensions, use standard sorting
                                df_forecast = df_forecast.sort_values(by=time_dim)
                            
                            # Debug: Print data shape and columns that will be used for forecasting
                            st.write(f"Debug: Data shape for forecasting: {df_forecast.shape}")
                            st.write(f"Debug: Data columns: {df_forecast.columns.tolist()}")
                            st.write(f"Debug: Time dimension: {time_dim}, Value column: {value}")
                            
                            # Sample of data being used for forecasting
                            st.write("Debug: Sample of data for forecasting:")
                            st.write(df_forecast.head(3))
                            
                            # Create a copy to avoid modifying the original
                            df_forecast_prep = df_forecast.copy()
                            
                            # Check if time dimension is a month name, create a mapping
                            if time_dim.lower() == 'month':
                                st.write("Debug: Converting month names to numeric values...")
                                # Create a standardized month mapping
                                month_mapping = {
                                    'january': 1, 'jan': 1, 'jan.': 1,
                                    'february': 2, 'feb': 2, 'feb.': 2,
                                    'march': 3, 'mar': 3, 'mar.': 3,
                                    'april': 4, 'apr': 4, 'apr.': 4,
                                    'may': 5,
                                    'june': 6, 'jun': 6, 'jun.': 6,
                                    'july': 7, 'jul': 7, 'jul.': 7,
                                    'august': 8, 'aug': 8, 'aug.': 8,
                                    'september': 9, 'sep': 9, 'sep.': 9, 'sept': 9, 'sept.': 9,
                                    'october': 10, 'oct': 10, 'oct.': 10,
                                    'november': 11, 'nov': 11, 'nov.': 11,
                                    'december': 12, 'dec': 12, 'dec.': 12
                                }
                                
                                # Create a temporary numeric month column
                                try:
                                    df_forecast_prep['Month_Numeric'] = df_forecast_prep[time_dim].str.lower().map(month_mapping)
                                    
                                    # Add fallback for any missing mappings
                                    if df_forecast_prep['Month_Numeric'].isna().any():
                                        st.warning("Some month values could not be mapped to numbers. Using sequential order instead.")
                                        # Create sequential numbers for any unmapped months
                                        unique_months = df_forecast_prep[time_dim].unique()
                                        seq_mapping = {month: i+1 for i, month in enumerate(unique_months)}
                                        df_forecast_prep['Month_Numeric'] = df_forecast_prep[time_dim].map(seq_mapping)
                                    
                                    st.write(f"Debug: Month conversion results: {df_forecast_prep['Month_Numeric'].tolist()}")
                                    
                                    # Use this as the time dimension for forecasting
                                    original_time_dim = time_dim
                                    time_dim = 'Month_Numeric'
                                except Exception as e:
                                    st.error(f"Error converting months to numeric: {e}")
                                    # Fall back to using a sequential index
                                    df_forecast_prep['Month_Numeric'] = range(1, len(df_forecast_prep) + 1)
                                    original_time_dim = time_dim
                                    time_dim = 'Month_Numeric'
                            
                            # Generate forecast using AI Hub's function
                            try:
                                # For other time dimensions, convert to numeric if possible
                                if time_dim.lower() != 'month_numeric':  # Skip if we already did month conversion
                                    try:
                                        if df_forecast_prep[time_dim].dtype == 'object':
                                            st.write(f"Debug: Converting {time_dim} to numeric...")
                                            df_forecast_prep[time_dim] = pd.to_numeric(df_forecast_prep[time_dim], errors='coerce')
                                            df_forecast_prep = df_forecast_prep.dropna(subset=[time_dim])
                                            st.write(f"Debug: After numeric conversion: {df_forecast_prep.shape} rows remain")
                                    except Exception as type_error:
                                        st.warning(f"Note: Could not convert time dimension to numeric. {type_error}")
                                
                                # Debug info about the dataframe we're passing to the forecast function
                                st.write(f"Debug: Prepared data for forecasting, shape: {df_forecast_prep.shape}")
                                st.write(f"Debug: First few rows of prepared data:")
                                st.write(df_forecast_prep.head(3))
                                
                                # Use the prepared dataframe with the numeric time dimension
                                forecast_df = generate_forecast(
                                    df=df_forecast_prep,
                                    year_col=time_dim,
                                    value_col=value,
                                    forecast_years=periods
                                )
                                
                                # If we used a month mapping, convert the Month_Numeric back to month names for display
                                if time_dim == 'Month_Numeric' and not forecast_df.empty and 'Source' in forecast_df.columns:
                                    # Reverse the month mapping for display purposes
                                    inverse_month_map = {
                                        1: 'January', 2: 'February', 3: 'March', 4: 'April',
                                        5: 'May', 6: 'June', 7: 'July', 8: 'August',
                                        9: 'September', 10: 'October', 11: 'November', 12: 'December'
                                    }
                                    
                                    # Create a display column with month names
                                    forecast_df['Month_Display'] = forecast_df[time_dim].map(inverse_month_map)
                                    
                                    # Use this for display in charts, but keep numeric for sorting
                                    display_time_dim = 'Month_Display'
                                else:
                                    display_time_dim = time_dim
                                
                                # Debug: Print result of forecast
                                st.write(f"Debug: Forecast result shape: {forecast_df.shape if forecast_df is not None else 'None'}")
                                st.write(f"Debug: Forecast result columns: {forecast_df.columns.tolist() if forecast_df is not None and not forecast_df.empty else 'Empty'}")
                                
                                # Verify forecast data has required columns
                                if forecast_df.empty or "Source" not in forecast_df.columns:
                                    st.error("Unable to generate forecast with the selected data.")
                                    st.info("Try selecting different dimensions for the time axis or a different value to forecast.")
                                    return
                                
                                # Store the forecast data in session state so it's available for the main chart
                                if 'forecast_data' not in st.session_state:
                                    st.session_state.forecast_data = {}
                                
                                # Save all the forecast related data
                                st.session_state.forecast_data = {
                                    'forecast_df': forecast_df,
                                    'time_dim': time_dim,
                                    'display_time_dim': display_time_dim if 'display_time_dim' in locals() else time_dim,
                                    'value': value,
                                    'ci': ci
                                }
                                
                                # Display success message
                                st.success(f"Forecast generated! {len(forecast_df[forecast_df['Source'] == 'Forecast'])} periods forecasted.")
                                
                                # Debug info to help troubleshoot - avoiding nested expanders
                                st.write("---")
                                st.write("**Debug Information:**")
                                st.write("Forecast data in session state:")
                                st.write(f"- Time dimension: {time_dim}")
                                st.write(f"- Display dimension: {display_time_dim if 'display_time_dim' in locals() else time_dim}")
                                st.write(f"- Value column: {value}")
                                st.write(f"- Shape: {forecast_df.shape}")
                                st.write(f"- Columns: {forecast_df.columns.tolist()}")
                                st.dataframe(forecast_df)
                                st.write("---")
                                
                                # Trigger a rerun to ensure the main chart uses the forecast data
                                if st.session_state.show_forecast_on_chart:
                                    st.info("Adding forecast to main chart... refreshing display.")
                                    st.rerun()
                            except Exception as forecast_error:
                                st.error(f"Error generating forecast: {forecast_error}")
                                st.info("Try selecting different dimensions or values for forecasting.")
                                return
                            
                            # Create combined chart with historical and forecast data
                            fig = go.Figure()
                            
                            # Add historical data
                            historical = forecast_df[forecast_df["Source"] == "Actual"]
                            # Use display_time_dim if available (for month names) or fall back to time_dim
                            x_axis = display_time_dim if 'display_time_dim' in locals() and display_time_dim in historical.columns else time_dim
                            st.write(f"Debug: Using {x_axis} as x-axis for display")
                            
                            fig.add_trace(
                                go.Scatter(
                                    x=historical[x_axis],
                                    y=historical[value],
                                    mode='lines+markers',
                                    name='Historical',
                                    line=dict(color='#2c3e50', width=2),
                                    marker=dict(size=8)
                                )
                            )
                            
                            # Add forecasted data
                            forecast = forecast_df[forecast_df["Source"] == "Forecast"]
                            fig.add_trace(
                                go.Scatter(
                                    x=forecast[x_axis], 
                                    y=forecast[value],
                                    mode='lines+markers',
                                    name='Forecast',
                                    line=dict(color='#e67e22', width=2, dash='dash'),
                                    marker=dict(size=8)
                                )
                            )
                            
                            # Add confidence interval
                            if ci > 0:
                                # Calculate simple error margins based on confidence level
                                ci_factor = ci / 100.0
                                
                                # Estimate error margin based on historical volatility
                                if len(historical[value]) > 1:
                                    std_dev = historical[value].std()
                                    mean_val = historical[value].mean()
                                    error_margin = std_dev * ci_factor
                                    
                                    # Create upper and lower bounds for forecast values
                                    forecast_upper = forecast[value] + error_margin
                                    forecast_lower = forecast[value] - error_margin
                                    
                                    # Add confidence interval
                                    fig.add_trace(
                                        go.Scatter(
                                            x=forecast[time_dim],
                                            y=forecast_upper,
                                            mode='lines',
                                            name=f'Upper {ci}% CI',
                                            line=dict(width=0),
                                            showlegend=False
                                        )
                                    )
                                    
                                    fig.add_trace(
                                        go.Scatter(
                                            x=forecast[time_dim],
                                            y=forecast_lower,
                                            mode='lines',
                                            name=f'Lower {ci}% CI',
                                            line=dict(width=0),
                                            fill='tonexty',
                                            fillcolor='rgba(230, 126, 34, 0.2)',
                                            showlegend=False
                                        )
                                    )
                            
                            # Update layout
                            fig.update_layout(
                                title=f'Forecast: {value} by {time_dim}',
                                xaxis_title=time_dim,
                                yaxis_title=value,
                                template='plotly_white',
                                height=450,
                                legend=dict(
                                    orientation="h",
                                    yanchor="bottom",
                                    y=1.02,
                                    xanchor="right",
                                    x=1
                                )
                            )
                            
                            # Add a vertical line at the forecast start point
                            last_historical = historical[time_dim].iloc[-1] if not historical.empty else None
                            if last_historical is not None:
                                fig.add_vline(
                                    x=last_historical,
                                    line_width=1,
                                    line_dash="dash",
                                    line_color="gray",
                                    annotation_text="Forecast Begins",
                                    annotation_position="top right"
                                )
                            
                            # Display the forecast chart
                            st.subheader("Forecast Visualization")
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Show the forecast data
                            forecast_data_col1, forecast_data_col2 = st.columns([2, 1])
                            
                            with forecast_data_col1:
                                st.subheader("Forecast Data")
                                st.dataframe(forecast_df)
                            
                            with forecast_data_col2:
                                # Add forecast metrics
                                if not forecast.empty and not historical.empty:
                                    st.subheader("Forecast Metrics")
                                    
                                    # Last historical value
                                    last_actual = historical[value].iloc[-1] if not historical.empty else 0
                                    st.metric("Last Actual Value", f"{last_actual:,.2f}")
                                    
                                    # Last forecast value
                                    last_forecast = forecast[value].iloc[-1] if not forecast.empty else 0
                                    st.metric("Final Forecast Value", f"{last_forecast:,.2f}")
                                    
                                    # Growth percentage
                                    growth = ((last_forecast - last_actual) / last_actual * 100) if last_actual != 0 else 0
                                    st.metric("Projected Growth", f"{growth:,.2f}%")
                            
                            # Add option to save forecast chart
                            if st.button("Add Forecast to Dashboard"):
                                # Make a copy of the current chart configuration
                                forecast_chart_config = {
                                    "dimensions": dimensions.copy(),
                                    "value": value,
                                    "agg_func": agg_func,
                                    "chart_type": "Forecast",  # Use "Forecast" as a special internal type
                                    "title": f"Forecast: {value} by {time_dim}",
                                    "description": f"Forecast for {periods} periods with {ci}% confidence interval",
                                    "forecast_data": forecast_df.to_dict(),
                                    "time_dim": time_dim,
                                    "periods": periods,
                                    "ci": ci
                                }
                                
                                # Add the forecast chart to saved charts
                                if "charts" not in st.session_state:
                                    st.session_state["charts"] = []
                                
                                st.session_state.charts.append(forecast_chart_config)
                                st.success("Forecast chart added to dashboard!")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Error generating forecast: {e}")
                            st.info("Try selecting different dimensions or values for forecasting.")
    
    # Removed the "Forecast" chart type as it's been replaced with the expandable forecasting section below
    
    # Add options to save this chart
    st.subheader("Save Current Chart")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        chart_title = st.text_input("Chart Title", value=f"Chart {len(st.session_state.charts)+1}")
    
    with chart_col2:
        chart_desc = st.text_input("Chart Description (optional)")
    
    if st.button(" Add Chart to Dashboard"):
        # Add the current chart configuration to saved charts
        st.session_state.charts.append({
            "dimensions": dimensions,
            "value": value,
            "agg_func": agg_func,
            "chart_type": chart_type,
            "title": chart_title,
            "description": chart_desc
        })
        st.success(f"Chart '{chart_title}' added to dashboard!")
    
    # Display saved charts
    if st.session_state.charts:
        st.subheader("Your Dashboard Charts")
        for i, chart_config in enumerate(st.session_state.charts):
            chart_type = chart_config.get('chart_type')
            with st.expander(f"Chart {i+1}: {chart_config.get('title')}"):
                st.write(f"**Dimensions:** {', '.join(chart_config.get('dimensions', []))}")
                st.write(f"**Value:** {chart_config.get('value')}")
                st.write(f"**Chart Type:** {chart_type}")
                
                # For forecast charts, render the saved forecast
                if chart_type == "Forecast" and chart_config.get('forecast_data'):
                    try:
                        # If forecast data is saved, recreate the visualization
                        st.write("### Forecast Visualization")
                        
                        # Convert the saved forecast data back to a dataframe
                        forecast_df = pd.DataFrame(chart_config.get('forecast_data'))
                        
                        # Verify the dataframe has expected columns
                        if forecast_df.empty or "Source" not in forecast_df.columns:
                            st.error("Forecast data is invalid or missing required information.")
                            st.button("Recreate Forecast", key=f"recreate_forecast_{i}")
                            continue
                            
                        time_dim = chart_config.get('time_dim')
                        value = chart_config.get('value')
                        ci = chart_config.get('ci', 80)
                        
                        # Create combined chart with historical and forecast data
                        fig = go.Figure()
                        
                        # Add historical data
                        historical = forecast_df[forecast_df["Source"] == "Actual"]
                        fig.add_trace(
                            go.Scatter(
                                x=historical[time_dim],
                                y=historical[value],
                                mode='lines+markers',
                                name='Historical',
                                line=dict(color='#2c3e50', width=2),
                                marker=dict(size=8)
                            )
                        )
                        
                        # Add forecasted data
                        forecast = forecast_df[forecast_df["Source"] == "Forecast"]
                        fig.add_trace(
                            go.Scatter(
                                x=forecast[time_dim], 
                                y=forecast[value],
                                mode='lines+markers',
                                name='Forecast',
                                line=dict(color='#e67e22', width=2, dash='dash'),
                                marker=dict(size=8)
                            )
                        )
                        
                        # Update layout
                        fig.update_layout(
                            title=f'Forecast: {value} by {time_dim}',
                            xaxis_title=time_dim,
                            yaxis_title=value,
                            template='plotly_white',
                            height=400
                        )
                        
                        # Add a vertical line at the forecast start point
                        last_historical = historical[time_dim].iloc[-1] if not historical.empty else None
                        if last_historical is not None:
                            fig.add_vline(
                                x=last_historical,
                                line_width=1,
                                line_dash="dash",
                                line_color="gray",
                                annotation_text="Forecast Begins"
                            )
                        
                        # Display the chart
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Show metrics in columns
                        if not forecast.empty and not historical.empty:
                            metrics_cols = st.columns(3)
                            
                            # Last historical value
                            last_actual = historical[value].iloc[-1] if not historical.empty else 0
                            metrics_cols[0].metric("Last Actual", f"{last_actual:,.2f}")
                            
                            # Last forecast value
                            last_forecast = forecast[value].iloc[-1] if not forecast.empty else 0
                            metrics_cols[1].metric("Final Forecast", f"{last_forecast:,.2f}")
                            
                            # Growth percentage
                            growth = ((last_forecast - last_actual) / last_actual * 100) if last_actual != 0 else 0
                            metrics_cols[2].metric("Growth", f"{growth:,.2f}%")
                    
                    except Exception as e:
                        st.error(f"Error displaying forecast chart: {e}")
                
                # Show delete button
                if st.button(f"Remove Chart", key=f"delete_chart_{i}"):
                    st.session_state.charts.pop(i)
                    st.success("Chart removed. Refreshing...")
                    st.rerun()

    st.markdown("###  Export Current Results")
    export_cols = st.columns(2)
    
    with export_cols[0]:
        csv = grouped.to_csv(index=False).encode("utf-8")
        st.download_button("Download Current View as CSV", csv, file_name="govsight_sandbox_output.csv", mime="text/csv")
    
    with export_cols[1]:
        if st.button("Generate PDF Report for Current View"):
            try:
                # Create a placeholder for progress messages
                pdf_status = st.empty()
                pdf_status.info("Generating PDF report for current view... Please wait.")
                
                # Create PDF
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # Add title page
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(190, 10, f"GovSight BI Dashboard Report - Current View", ln=True, align="C")
                pdf.set_font("Arial", "I", 10)
                pdf.cell(190, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
                pdf.ln(5)
                
                # Create a temporary directory
                with tempfile.TemporaryDirectory() as tempdir:
                    # Add a page for the current chart
                    pdf.add_page()
                    
                    # Add chart title
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(190, 10, "Current View Analysis", ln=True)
                    
                    # Add chart parameters
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(190, 10, "Chart Parameters:", ln=True)
                    pdf.set_font("Arial", "", 10)
                    pdf.cell(190, 5, f"Dimensions: {', '.join(dimensions)}", ln=True)
                    pdf.cell(190, 5, f"Value: {value}", ln=True)
                    pdf.cell(190, 5, f"Aggregation: {agg_func}", ln=True)
                    pdf.cell(190, 5, f"Chart Type: {chart_type}", ln=True)
                    pdf.ln(5)
                    
                    # Add a note about visualizations
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(190, 10, "Chart Visualization:", ln=True)
                    pdf.set_font("Arial", "I", 10)
                    pdf.cell(190, 10, "The visualization can be viewed in the BI Sandbox interface.", ln=True)
                    pdf.ln(5)
                    
                    # Add data table for this chart
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(190, 10, "Data Table:", ln=True)
                    pdf.set_font("Arial", "B", 8)
                    
                    # Calculate column width (limited to 8 columns maximum for better readability)
                    num_cols = min(len(grouped.columns), 8)
                    col_width = 180 / num_cols
                    
                    # Add headers
                    for col in grouped.columns[:num_cols]:  # Limit to first 8 columns if more
                        pdf.cell(col_width, 10, str(col), border=1)
                    pdf.ln()
                    
                    # Add data rows (limit to max 50 rows for PDF readability)
                    pdf.set_font("Arial", "", 8)
                    for _, row in grouped.head(50).iterrows():  # Limit to first 50 rows
                        for item in row[:num_cols]:  # Limit to first 8 columns
                            # Format numbers if possible
                            if isinstance(item, (int, float)):
                                if "Budget" in value or "Actual" in value or "Amount" in value:
                                    formatted_val = format_currency(item).replace("$", "")
                                elif item < 1:
                                    formatted_val = format_percentage(item * 100)
                                else:
                                    formatted_val = f"{item:,.2f}"
                            else:
                                formatted_val = str(item)
                            
                            pdf.cell(col_width, 7, formatted_val[:15], border=1)  # Truncate long values
                        pdf.ln()
                    
                    # Add note if data was truncated
                    if len(grouped) > 50 or len(grouped.columns) > 8:
                        pdf.set_font("Arial", "I", 8)
                        pdf.cell(190, 5, "(Data table truncated for PDF report)", ln=True)
                    
                    # Output PDF
                    pdf.output(dest='F', name=os.path.join(tempdir, "current_view_report.pdf"))
                    
                    # Read the generated PDF file
                    with open(os.path.join(tempdir, "current_view_report.pdf"), 'rb') as f:
                        pdf_data = f.read()
                    
                    # Clear status and show success
                    pdf_status.success("PDF report generated successfully!")
                    
                    # Provide download button
                    st.download_button(
                        "Download PDF Report",
                        pdf_data,
                        file_name=f"govsight_current_view_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
            
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
    
    st.divider()

def render_bi_sandbox(org: str = "cityA", org_display_name: str = "City A"):
    """
    Render the Self-Service BI Sandbox tab
    
    Args:
        org (str): Organization identifier
        org_display_name (str): Display name for the organization
    """
    # Header
    st.markdown(f"<h2>Self-Service BI Sandbox - {org_display_name}</h2>", unsafe_allow_html=True)
    st.markdown("Create custom visualizations and scenarios by selecting fields and chart types.")
    
    # Check if there's a scenario to load from Scenario Planner
    funding_scenario_data = None
    if "funding_scenario_for_bi" in st.session_state and st.session_state.funding_scenario_for_bi.get("action") == "load_to_bi_sandbox":
        scenario_id = st.session_state.funding_scenario_for_bi.get("scenario_id")
        scenario_name = st.session_state.funding_scenario_for_bi.get("scenario_name")
        
        # Display alert about incoming scenario
        st.info(f"Loading funding scenario: {scenario_name}")
        
        # Get detailed scenario data
        funding_scenario_data = get_detailed_scenario_data(scenario_id)
        
        if funding_scenario_data:
            # Create a Pandas DataFrame for visualization
            scenario_df = pd.DataFrame(funding_scenario_data["formatted_data"])
            
            # Add button to clear the loaded scenario
            if st.button(" Clear Loaded Scenario"):
                # Clear the loaded scenario
                st.session_state.funding_scenario_for_bi = {"action": "cleared"}
                st.rerun()
            
            # Display funding scenario details
            st.markdown("### Funding Scenario Details")
            
            # Create columns for scenario details
            details_col1, details_col2 = st.columns(2)
            
            with details_col1:
                st.markdown(f"**Project:** {funding_scenario_data['project_name']}")
                st.markdown(f"**Total Cost:** {format_currency(funding_scenario_data['total_cost'])}")
                
                # Calculate total funding
                total_funding = sum([
                    funding_scenario_data['tax_revenue'] or 0,
                    funding_scenario_data['grant_funding'] or 0,
                    funding_scenario_data['private_investment'] or 0,
                    sum(funding_scenario_data['department_allocations'].values())
                ])
                funding_percentage = (total_funding / funding_scenario_data['total_cost']) * 100 if funding_scenario_data['total_cost'] > 0 else 0
                
                st.markdown(f"**Total Funding:** {format_currency(total_funding)} ({format_percentage(funding_percentage)})")
                
            with details_col2:
                st.markdown(f"**Funding Gap:** {format_currency(funding_scenario_data['bonds_needed'])}")
                st.markdown(f"**Departments Contributing:** {len(funding_scenario_data['department_allocations'])}")
                st.markdown(f"**Created:** {funding_scenario_data['creation_date']}")
            
            # Create visualizations for the funding scenario
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                # Create funding source breakdown chart
                funding_sources = scenario_df[scenario_df['Category'] == 'Funding']
                if not funding_sources.empty:
                    fig1 = px.bar(
                        funding_sources,
                        x='FundingSource',
                        y='Amount',
                        title='Funding Source Breakdown',
                        color='FundingSource',
                        text_auto=True
                    )
                    fig1.update_traces(texttemplate='%{text:$,.2f}', textposition='outside')
                    fig1.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
                    st.plotly_chart(fig1, use_container_width=True)
            
            with viz_col2:
                # Create department allocation pie chart
                dept_allocations = scenario_df[scenario_df['Category'] == 'Department']
                if not dept_allocations.empty:
                    fig2 = px.pie(
                        dept_allocations,
                        names='FundingSource',
                        values='Amount',
                        title='Department Allocation Breakdown',
                        hole=0.4
                    )
                    fig2.update_traces(textinfo='label+percent+value')
                    st.plotly_chart(fig2, use_container_width=True)
            
            # Add a separator
            st.markdown("---")
            
            # Offer to generate charts based on the funding scenario
            st.markdown("###  Generate Charts for Funding Scenario")
            
            if st.button("Generate Standard Funding Charts"):
                # Clear existing charts
                st.session_state.charts = []
                
                # Chart 1: Funding sources breakdown bar chart
                st.session_state.charts.append({
                    "dimensions": ["FundingSource"],
                    "value": "Amount",
                    "agg_func": "sum",
                    "chart_type": "Bar",
                    "title": f"Funding Sources for {scenario_name}",
                    "description": "Breakdown of funding sources for the project, including department contributions, grants, tax revenue, and any funding gap."
                })
                
                # Chart 2: Department contributions pie chart
                if dept_allocations.shape[0] > 0:
                    st.session_state.charts.append({
                        "dimensions": ["FundingSource"],
                        "value": "Amount",
                        "agg_func": "sum",
                        "chart_type": "Pie",
                        "title": f"Department Contributions for {scenario_name}",
                        "description": "Breakdown of department contributions to the project funding."
                    })
                
                # Add the scenario data as a hidden session variable
                st.session_state.scenario_data = scenario_df
                
                st.success("Charts generated! Scroll down to view and customize them.")
                st.rerun()
    
    # Get the database path for the organization
    db_path = get_db_path_for_org(org)
    
    # Cache data loading
    @st.cache_data
    def load_data(db_path):
        """Load data from database"""
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query("SELECT * FROM DepartmentPerformance", conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()  # Return empty DataFrame if error
    
    # Load regular data if no scenario is loaded, or if we need it alongside scenario data
    df = load_data(db_path)
    
    # Debug: Check for duplicates in the DepartmentName field
    if not df.empty and 'DepartmentName' in df.columns:
        # Show counts by department name to identify duplicates
        dept_counts = df.groupby('DepartmentName').size().reset_index(name='count')
        with st.expander("Database Info (Debug)", expanded=False):
            st.write("Database Path:", db_path)
            st.write("Found", len(df), "records")
            st.write("Department Counts:")
            st.dataframe(dept_counts)
            
            # Check for duplicate records that might be causing duplicates in visualizations
            st.write("Sample data (first 5 rows):")
            st.dataframe(df.head())
            
            # Check if there are duplicate combinations of DepartmentName and other key fields
            if 'FiscalYear' in df.columns:
                duplicate_groups = df.groupby(['DepartmentName', 'FiscalYear']).size().reset_index(name='count')
                st.write("Department/FiscalYear combinations:")
                st.dataframe(duplicate_groups)
    
    # If we have scenario data in session state, use it for special charts
    if "scenario_data" in st.session_state and not st.session_state.scenario_data.empty:
        scenario_df = st.session_state.scenario_data
        
        # For charts that use scenario data, we'll substitute it for the regular df later
    
    if df.empty and not funding_scenario_data:
        st.warning("No data available for analysis. Please check your database connection.")
        return
    
    # Initialize charts state if not exists
    if "charts" not in st.session_state:
        st.session_state.charts = []
        # Add a first empty chart configuration
        st.session_state.charts.append({
            "dimensions": ["FiscalYear"],
            "value": "Budget",
            "agg_func": "sum",
            "chart_type": "Bar",
            "title": "",
            "description": ""
        })
    
    # Chart management controls (within the BI Sandbox module)
    st.markdown("### Chart Management")
    st.info("Create and manage multiple charts for your analysis dashboard.")
    
    chart_mgmt_col1, chart_mgmt_col2 = st.columns(2)
    
    with chart_mgmt_col1:
        if st.button(" Add New Chart"):
            # Add a new empty chart configuration
            st.session_state.charts.append({
                "dimensions": ["FiscalYear"],
                "value": "Budget",
                "agg_func": "sum",
                "chart_type": "Bar",
                "title": "",
                "description": ""
            })
            st.rerun()
    
    with chart_mgmt_col2:
        # Option to remove charts if there's more than one
        if len(st.session_state.charts) > 1:
            chart_to_remove = st.selectbox(
                "Remove Chart",
                options=range(1, len(st.session_state.charts) + 1),
                format_func=lambda x: f"Chart {x}"
            )
            
            if st.button(" Remove Selected Chart"):
                st.session_state.charts.pop(chart_to_remove - 1)
                st.rerun()
    
    st.markdown("---")
    
    # Main content area
    for i, chart_config in enumerate(st.session_state.charts):
        st.markdown(f"## Chart {i+1}")
        
        # Create layout with columns for this chart
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Field Selection")
            
            # Custom title for the chart
            chart_title = st.text_input(
                "Chart Title (optional)",
                value=chart_config.get("title", ""),
                key=f"title_{i}"
            )
            st.session_state.charts[i]["title"] = chart_title
            
            # Select dimensions (categories) - use actual columns from the dataframe
            # Handle both regular df and scenario_df cases
            current_df = scenario_df if "scenario_data" in st.session_state and not st.session_state.scenario_data.empty else df
            
            # Get column list from appropriate dataframe
            column_list = current_df.columns.tolist()
            default_dim = chart_config.get("dimensions", [])
            if not default_dim or default_dim[0] not in column_list:
                default_dim = [column_list[0]] if column_list else []
            
            dimensions = st.multiselect(
                "Select dimensions (X-axis)",
                column_list,
                default=default_dim,
                key=f"dimensions_{i}"
            )
            st.session_state.charts[i]["dimensions"] = dimensions
            
            # Make all columns available for Y-axis
            measure_options = current_df.columns.tolist()
            
            # Add a "Budget - Actual" option if both Budget and Actual columns exist
            if "Budget" in measure_options and "Actual" in measure_options:
                measure_options.append("Budget - Actual")
            
            # Default to "Amount" for scenario data if available
            default_value = chart_config.get("value", "Budget")
            if default_value not in measure_options:
                default_value = measure_options[0] if measure_options else "No columns"
            
            if not measure_options:
                st.error("No columns found in the data for Y-axis selection.")
                measure_options = ["No columns"]
                default_value = "No columns"
            
            # Find the index of the default value
            try:
                default_index = measure_options.index(default_value)
            except ValueError:
                default_index = 0 if measure_options else 0
            
            value = st.selectbox(
                "Select value to measure (Y-axis)",
                measure_options,
                index=default_index,
                key=f"value_{i}"
            )
            st.session_state.charts[i]["value"] = value
            
            # Select aggregation method
            agg_func = st.selectbox(
                "Aggregation Method",
                ["sum", "mean", "max", "min", "count"],
                index=["sum", "mean", "max", "min", "count"].index(
                    chart_config.get("agg_func", "sum")
                ),
                key=f"agg_func_{i}"
            )
            st.session_state.charts[i]["agg_func"] = agg_func
            
            # Chart type selection
            chart_type = st.selectbox(
                "Chart Type",
                ["Table", "Bar", "Line", "Pie", "Area", "Scatter"],
                index=["Table", "Bar", "Line", "Pie", "Area", "Scatter"].index(
                    chart_config.get("chart_type", "Bar")
                ),
                key=f"chart_type_{i}"
            )
            st.session_state.charts[i]["chart_type"] = chart_type
            
            # Description for the chart
            chart_description = st.text_area(
                "Chart Description (optional)",
                value=chart_config.get("description", ""),
                key=f"description_{i}",
                height=100
            )
            st.session_state.charts[i]["description"] = chart_description
        
        # Determine which dataset to use for this chart
        chart_data = df
        is_funding_scenario_chart = False
        
        # Check if this is a chart for scenario data (from Scenario Planner)
        if "scenario_data" in st.session_state and not st.session_state.scenario_data.empty:
            if dimensions and dimensions[0] == "FundingSource" and value == "Amount":
                # Use scenario data for this chart
                chart_data = st.session_state.scenario_data
                is_funding_scenario_chart = True
                
                # If we want only department allocations
                if chart_type == "Pie" and "Department Contributions" in chart_title:
                    chart_data = chart_data[chart_data["Category"] == "Department"]
                # If we want all funding sources
                elif "Funding Sources" in chart_title:
                    chart_data = chart_data[chart_data["Category"] == "Funding"]
        
        # Process data for this chart
        if not is_funding_scenario_chart and value == "Budget - Actual" and "Budget - Actual" not in chart_data.columns:
            chart_data["Budget - Actual"] = chart_data["Budget"] - chart_data["Actual"]
        
        if dimensions:
            # Group data based on selections (skip grouping for scenario data that's already in correct format)
            if is_funding_scenario_chart:
                grouped = chart_data
            else:
                try:
                    # Use a safer way to reset the index that avoids duplicate column name errors
                    grouped = chart_data.groupby(dimensions, as_index=False).agg({value: agg_func})
                except Exception as e:
                    st.error(f"Error grouping data: {e}")
                    st.info("Try selecting different columns or aggregation methods.")
                    grouped = chart_data.head(10)  # Show a sample instead
            
            with col2:
                st.markdown("### Data Visualization")
                
                # Display custom title if provided
                if chart_title:
                    st.markdown(f"#### {chart_title}")
                
                # Display description if provided
                if chart_description:
                    st.markdown(f"*{chart_description}*")
                    st.markdown("---")
                
                # Show data table with advanced filtering
                with st.expander("Data Table with Advanced Filters", expanded=False):
                    from advanced_filters import create_advanced_filter_component, display_filtered_dataframe, create_summary_metrics
                    
                    # Apply advanced filtering to the grouped data
                    filtered_data = create_advanced_filter_component(
                        df=grouped,
                        key_prefix=f"bi_chart_{i}",
                        items_per_page=25
                    )
                    
                    # Display summary metrics
                    create_summary_metrics(filtered_data, grouped)
                    
                    # Display the filtered data
                    display_filtered_dataframe(
                        filtered_data,
                        key_prefix=f"bi_display_{i}",
                        height=300
                    )
                
                # Create visualization based on chart type
                if chart_type == "Table":
                    st.dataframe(grouped)
                elif not dimensions:
                    st.warning("Please select at least one dimension for the X-axis to create a visualization.")
                elif chart_type == "Bar":
                    try:
                        fig = px.bar(
                            grouped, 
                            x=dimensions[0], 
                            y=value, 
                            color=dimensions[1] if len(dimensions) > 1 else None,
                            barmode="group",
                            title=chart_title or f"{value} by {', '.join(dimensions)} (Aggregation: {agg_func})"
                        )
                        # For currency values, format the hover template
                        if value == "Amount" or "Budget" in value or "Actual" in value:
                            fig.update_traces(hovertemplate="%{x}<br>%{y:$,.2f}<extra></extra>")
                            # Add dollar formatting to y-axis
                            fig.update_layout(yaxis=dict(tickprefix="$", tickformat=","))
                        
                        # Add value labels on bars for funding charts
                        if is_funding_scenario_chart:
                            fig.update_traces(texttemplate='%{y:$,.2f}', textposition='outside')
                        
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating bar chart: {e}")
                        st.info("Try selecting different dimensions or values.")
                elif chart_type == "Line":
                    try:
                        fig = px.line(
                            grouped, 
                            x=dimensions[0], 
                            y=value, 
                            color=dimensions[1] if len(dimensions) > 1 else None,
                            title=chart_title or f"{value} by {', '.join(dimensions)} (Aggregation: {agg_func})"
                        )
                        # For currency values, format the hover template
                        if value == "Amount" or "Budget" in value or "Actual" in value:
                            fig.update_traces(hovertemplate="%{x}<br>%{y:$,.2f}<extra></extra>")
                            # Add dollar formatting to y-axis
                            fig.update_layout(yaxis=dict(tickprefix="$", tickformat=","))
                        
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating line chart: {e}")
                        st.info("Try selecting different dimensions or values.")
                elif chart_type == "Pie":
                    try:
                        if len(grouped) > 30:
                            st.warning("Too many slices for pie chart. Try filtering or grouping differently.")
                        else:
                            fig = px.pie(
                                grouped, 
                                names=dimensions[0], 
                                values=value,
                                title=chart_title or f"{value} by {dimensions[0]} (Aggregation: {agg_func})"
                            )
                            # For funding charts, add value and percentage to labels
                            if is_funding_scenario_chart:
                                fig.update_traces(textinfo='label+percent+value', 
                                                 hovertemplate="%{label}<br>%{value:$,.2f} (%{percent})<extra></extra>")
                            
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating pie chart: {e}")
                        st.info("Try selecting different dimensions or values.")
                elif chart_type == "Area":
                    try:
                        fig = px.area(
                            grouped, 
                            x=dimensions[0], 
                            y=value, 
                            color=dimensions[1] if len(dimensions) > 1 else None,
                            title=chart_title or f"{value} by {', '.join(dimensions)} (Aggregation: {agg_func})"
                        )
                        # For currency values, format the hover template
                        if value == "Amount" or "Budget" in value or "Actual" in value:
                            fig.update_traces(hovertemplate="%{x}<br>%{y:$,.2f}<extra></extra>")
                            # Add dollar formatting to y-axis
                            fig.update_layout(yaxis=dict(tickprefix="$", tickformat=","))
                        
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating area chart: {e}")
                        st.info("Try selecting different dimensions or values.")
                elif chart_type == "Scatter":
                    try:
                        if len(dimensions) < 2:
                            st.warning("Scatter plot requires at least 2 dimensions.")
                        else:
                            fig = px.scatter(
                                chart_data, 
                                x=dimensions[0], 
                                y=dimensions[1],
                                color=dimensions[2] if len(dimensions) > 2 else None,
                                size=value,
                                title=chart_title or f"{dimensions[1]} vs {dimensions[0]} sized by {value}"
                            )
                            # For currency values, format the hover template
                            if value == "Amount" or "Budget" in value or "Actual" in value:
                                fig.update_traces(hovertemplate="%{x}<br>%{y}<br>%{marker.size:$,.2f}<extra></extra>")
                            
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating scatter chart: {e}")
                        st.info("Try selecting different dimensions or values.")
        
        # Add a separator between charts
        st.markdown("---")
        
    # --- Save to Scenario Feature (outside the chart loop) ---
    st.markdown("### Save Dashboard to Scenario")
    scenario_col1, scenario_col2 = st.columns(2)
    
    with scenario_col1:
        scenario_name = st.text_input("Scenario Name")
    
    with scenario_col2:
        scenario_tags = st.text_input("Tags (comma separated)")
    
    scenario_notes = st.text_area("Scenario Notes")
    
    if st.button("Save Dashboard as Scenario"):
        if not scenario_name:
            st.warning("Please enter a scenario name.")
        else:
            # Initialize scenarios in session state if not exists
            if "sandbox_scenarios" not in st.session_state:
                st.session_state.sandbox_scenarios = []
            
            # Save scenario information with all charts
            st.session_state.sandbox_scenarios.append({
                "name": scenario_name,
                "notes": scenario_notes,
                "tags": [tag.strip() for tag in scenario_tags.split(",")] if scenario_tags else [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "charts": st.session_state.charts.copy(),  # Save all chart configurations
                "organization": org
            })
            st.success(f"Dashboard scenario '{scenario_name}' with {len(st.session_state.charts)} charts saved!")
        
    # --- Show Saved Scenarios ---
    if "sandbox_scenarios" in st.session_state and st.session_state.sandbox_scenarios:
        st.markdown("###  Saved Scenarios")
        
        # Display saved scenarios
        for i, scenario in enumerate(st.session_state.sandbox_scenarios):
            if scenario["organization"] == org:  # Only show scenarios for current org
                with st.expander(f"{scenario['name']} ({scenario['timestamp']})"):
                    if scenario.get("notes"):
                        st.markdown(f"**Notes:** {scenario['notes']}")
                    
                    if scenario.get("tags"):
                        st.markdown(f"**Tags:** {', '.join(scenario['tags'])}")
                    
                    # Check if this is a new multi-chart scenario or old single-chart scenario
                    if "charts" in scenario:
                        # Multi-chart scenario
                        st.markdown(f"**Number of charts:** {len(scenario['charts'])}")
                        
                        # Display chart information
                        for j, chart in enumerate(scenario['charts']):
                            with st.expander(f"Chart {j+1}: {chart.get('title') or 'Untitled Chart'}"):
                                st.markdown(f"**Dimensions:** {', '.join(chart['dimensions'])}")
                                st.markdown(f"**Value:** {chart['value']} (Aggregation: {chart['agg_func']})")
                                st.markdown(f"**Chart type:** {chart['chart_type']}")
                                
                                if chart.get('description'):
                                    st.markdown(f"**Description:** {chart['description']}")
                                
                                # Load the data for this chart configuration
                                if chart.get('dimensions') and chart.get('value') and chart.get('agg_func'):
                                    try:
                                        # Create a copy of df for this chart
                                        chart_df = df.copy()
                                        
                                        # Add "Budget - Actual" if needed
                                        if chart['value'] == "Budget - Actual" and "Budget - Actual" not in chart_df.columns:
                                            chart_df["Budget - Actual"] = chart_df["Budget"] - chart_df["Actual"]
                                        
                                        # Group data based on chart selections
                                        try:
                                            chart_grouped = chart_df.groupby(chart['dimensions'], as_index=False).agg({chart['value']: chart['agg_func']})
                                        except Exception as e:
                                            st.error(f"Error grouping saved chart data: {e}")
                                            chart_grouped = chart_df.head(5)
                                        
                                        # Display data for this chart
                                        st.dataframe(chart_grouped)
                                        
                                        # Display visualization based on chart type
                                        if chart['chart_type'] != "Table":
                                            st.markdown("**Visualization Preview:**")
                                            if chart['chart_type'] == "Bar":
                                                fig = px.bar(
                                                    chart_grouped, 
                                                    x=chart['dimensions'][0], 
                                                    y=chart['value'], 
                                                    color=chart['dimensions'][1] if len(chart['dimensions']) > 1 else None,
                                                    barmode="group",
                                                    title=chart.get('title') or f"{chart['value']} by {', '.join(chart['dimensions'])}"
                                                )
                                                st.plotly_chart(fig, use_container_width=True)
                                            # Similar for other chart types...
                                    except Exception as e:
                                        st.error(f"Could not recreate chart: {e}")
                    else:
                        # Legacy single-chart scenario
                        st.markdown(f"**Dimensions:** {', '.join(scenario['dimensions'])}")
                        st.markdown(f"**Value:** {scenario['value']} (Aggregation: {scenario['agg_func']})")
                        st.markdown(f"**Chart type:** {scenario['chart_type']}")
                        
                        # Convert scenario data back to DataFrame if available
                        if 'data' in scenario:
                            scenario_df = pd.DataFrame(scenario['data'])
                            st.dataframe(scenario_df)
                    
                    # Option to load scenario to current session
                    if st.button(f"Load This Scenario", key=f"load_{i}"):
                        if "charts" in scenario:
                            # Load all charts from saved scenario
                            st.session_state.charts = scenario['charts'].copy()
                        else:
                            # Create a chart from legacy scenario
                            st.session_state.charts = [{
                                "dimensions": scenario['dimensions'],
                                "value": scenario['value'],
                                "agg_func": scenario['agg_func'],
                                "chart_type": scenario['chart_type'],
                                "title": scenario['name'],
                                "description": scenario.get('notes', "")
                            }]
                        st.success(f"Loaded scenario '{scenario['name']}'. Refreshing...")
                        st.rerun()
                    
                    # Option to delete scenario
                    if st.button(f"Delete Scenario", key=f"delete_{i}"):
                        st.session_state.sandbox_scenarios.pop(i)
                        st.success("Scenario deleted. Refresh to update the view.")
                        st.rerun()
    
    # --- Export Options ---
    st.markdown("###  Export Your Dashboard")
    st.markdown("Export all your saved charts in various formats:")
    export_col1, export_col2 = st.columns(2)
    
    # Generate a combined CSV of all charts
    try:
        with export_col1:
            # Create a list to hold all chart data
            all_data = []
            
            # For each chart, add its data with a chart identifier
            for i, chart_config in enumerate(st.session_state.charts):
                dimensions = chart_config.get("dimensions")
                value = chart_config.get("value")
                agg_func = chart_config.get("agg_func")
                chart_type = chart_config.get("chart_type")
                
                if dimensions and value and agg_func:
                    # Create a copy of df for this chart
                    chart_df = df.copy()
                    
                    # Check if this is a funding scenario chart
                    is_funding_scenario_chart = False
                    if "scenario_data" in st.session_state and not isinstance(st.session_state.scenario_data, str):
                        if dimensions and dimensions[0] == "FundingSource" and value == "Amount":
                            # Use scenario data for this chart
                            chart_df = st.session_state.scenario_data.copy()
                            is_funding_scenario_chart = True
                            
                            # If we want only department allocations
                            chart_title = chart_config.get('title') or ''
                            if chart_type == "Pie" and "Department Contributions" in chart_title:
                                chart_df = chart_df[chart_df["Category"] == "Department"]
                            # If we want all funding sources
                            elif "Funding Sources" in chart_title:
                                chart_df = chart_df[chart_df["Category"] == "Funding"]
                    
                    # Add "Budget - Actual" if needed
                    if value == "Budget - Actual" and "Budget - Actual" not in chart_df.columns:
                        chart_df["Budget - Actual"] = chart_df["Budget"] - chart_df["Actual"]
                    
                    # Group data based on chart selections
                    try:
                        if is_funding_scenario_chart:
                            chart_grouped = chart_df
                        else:
                            chart_grouped = chart_df.groupby(dimensions, as_index=False).agg({value: agg_func})
                    except Exception as e:
                        st.error(f"Error grouping export data: {e}")
                        chart_grouped = chart_df.head(5)
                    
                    # Add chart identifier column
                    chart_grouped["Chart"] = f"Chart {i+1}: {chart_config.get('title') or 'Untitled'}"
                    
                    # Add to the combined data
                    all_data.append(chart_grouped)
            
            if all_data:
                # Combine all charts' data
                combined_df = pd.concat(all_data, ignore_index=True)
                
                # Provide download button for combined data
                csv = combined_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download All Charts as CSV",
                    csv,
                    file_name=f"govsight_dashboard_{org}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No chart data available to export. Create and save charts first.")
        
        with export_col2:
            if st.button("Generate PDF Report with Charts"):
                if not st.session_state.charts:
                    st.warning("Please create and save at least one chart before generating a PDF report.")
                else:
                    try:
                        # Create a placeholder for progress messages
                        pdf_status = st.empty()
                        pdf_status.info("Generating PDF report with charts... Please wait.")
                        
                        # Create PDF
                        pdf = FPDF()
                        pdf.set_auto_page_break(auto=True, margin=15)
                        
                        # Add title page
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 16)
                        pdf.cell(190, 10, f"GovSight BI Dashboard Report - {org_display_name}", ln=True, align="C")
                        pdf.set_font("Arial", "I", 10)
                        pdf.cell(190, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
                        pdf.ln(5)
                        
                        # Add overview
                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(190, 10, "Dashboard Overview", ln=True)
                        pdf.set_font("Arial", "", 10)
                        pdf.cell(190, 5, f"Number of charts: {len(st.session_state.charts)}", ln=True)
                        pdf.ln(5)
                        
                        # Create a temporary directory for chart images
                        with tempfile.TemporaryDirectory() as tempdir:
                            # Add each chart's details
                            for i, chart_config in enumerate(st.session_state.charts):
                                dimensions = chart_config.get("dimensions")
                                value = chart_config.get("value")
                                agg_func = chart_config.get("agg_func")
                                chart_title = chart_config.get("title") or f"Chart {i+1}"
                                chart_desc = chart_config.get("description") or ""
                                chart_type = chart_config.get("chart_type")
                                
                                # Update status
                                pdf_status.info(f"Processing chart {i+1} of {len(st.session_state.charts)}...")
                                
                                # Only process charts with valid configurations
                                if dimensions and value and agg_func:
                                    # Add a page for each chart
                                    pdf.add_page()
                                    
                                    # Add chart title
                                    pdf.set_font("Arial", "B", 14)
                                    pdf.cell(190, 10, f"Chart {i+1}: {chart_title}", ln=True)
                                    
                                    # Add chart description if available
                                    if chart_desc:
                                        pdf.set_font("Arial", "I", 10)
                                        pdf.multi_cell(190, 5, f"Description: {chart_desc}", ln=True)
                                        pdf.ln(3)
                                    
                                    # Add chart parameters
                                    pdf.set_font("Arial", "B", 12)
                                    pdf.cell(190, 10, "Chart Parameters:", ln=True)
                                    pdf.set_font("Arial", "", 10)
                                    pdf.cell(190, 5, f"Dimensions: {', '.join(dimensions)}", ln=True)
                                    pdf.cell(190, 5, f"Value: {value}", ln=True)
                                    pdf.cell(190, 5, f"Aggregation: {agg_func}", ln=True)
                                    pdf.cell(190, 5, f"Chart Type: {chart_type}", ln=True)
                                    pdf.ln(5)
                                    
                                    # Determine which dataset to use for this chart
                                    chart_df = df.copy()
                                    is_funding_scenario_chart = False
                                    
                                    # Check if this is a chart for scenario data (from Scenario Planner)
                                    if "scenario_data" in st.session_state and not isinstance(st.session_state.scenario_data, str):
                                        if dimensions and dimensions[0] == "FundingSource" and value == "Amount":
                                            # Use scenario data for this chart
                                            chart_df = st.session_state.scenario_data.copy()
                                            is_funding_scenario_chart = True
                                            
                                            # If we want only department allocations
                                            if chart_type == "Pie" and "Department Contributions" in chart_title:
                                                chart_df = chart_df[chart_df["Category"] == "Department"]
                                            # If we want all funding sources
                                            elif "Funding Sources" in chart_title:
                                                chart_df = chart_df[chart_df["Category"] == "Funding"]
                                    
                                    # Add "Budget - Actual" if needed
                                    if value == "Budget - Actual" and "Budget - Actual" not in chart_df.columns:
                                        chart_df["Budget - Actual"] = chart_df["Budget"] - chart_df["Actual"]
                                    
                                    # Group data based on chart selections
                                    try:
                                        if is_funding_scenario_chart:
                                            chart_grouped = chart_df
                                        else:
                                            chart_grouped = chart_df.groupby(dimensions, as_index=False).agg({value: agg_func})
                                    except Exception as e:
                                        # For PDF generation, just use a sample if there's an error
                                        chart_grouped = chart_df.head(5)
                                        # Add a note in the PDF about the error
                                        pdf.set_font("Arial", "I", 10)
                                        pdf.cell(190, 5, f"Error grouping data: {e}", ln=True)
                                        pdf.set_font("Arial", "", 10)
                                    
                                    # Add a note about visualizations
                                    pdf.set_font("Arial", "B", 12)
                                    pdf.cell(190, 10, "Chart Visualization:", ln=True)
                                    pdf.set_font("Arial", "I", 10)
                                    pdf.cell(190, 10, "The visualization can be viewed in the BI Sandbox interface.", ln=True)
                                    pdf.ln(5)
                                    
                                    # Add data table for this chart
                                    pdf.set_font("Arial", "B", 12)
                                    pdf.cell(190, 10, "Data Table:", ln=True)
                                    pdf.set_font("Arial", "B", 8)
                                    
                                    # Calculate column width (limited to 8 columns maximum for better readability)
                                    num_cols = min(len(chart_grouped.columns), 8)
                                    col_width = 180 / num_cols
                                    
                                    # Add headers
                                    for col in chart_grouped.columns[:num_cols]:  # Limit to first 8 columns if more
                                        pdf.cell(col_width, 10, str(col), border=1)
                                    pdf.ln()
                                    
                                    # Add data rows (limit to max 50 rows for PDF readability)
                                    pdf.set_font("Arial", "", 8)
                                    for _, row in chart_grouped.head(50).iterrows():  # Limit to first 50 rows
                                        for item in row[:num_cols]:  # Limit to first 8 columns
                                            # Format numbers if possible
                                            if isinstance(item, (int, float)):
                                                if "Budget" in value or "Actual" in value or "Amount" in value:
                                                    formatted_val = format_currency(item).replace("$", "")
                                                elif item < 1:
                                                    formatted_val = format_percentage(item * 100)
                                                else:
                                                    formatted_val = f"{item:,.2f}"
                                            else:
                                                formatted_val = str(item)
                                            
                                            pdf.cell(col_width, 7, formatted_val[:15], border=1)  # Truncate long values
                                        pdf.ln()
                                    
                                    # Add note if data was truncated
                                    if len(chart_grouped) > 50 or len(chart_grouped.columns) > 8:
                                        pdf.set_font("Arial", "I", 8)
                                        pdf.cell(190, 5, "(Data table truncated for PDF report)", ln=True)
                            
                            # Update status
                            pdf_status.info("Finalizing PDF report...")
                            
                            # Output PDF
                            pdf.output(dest='F', name=os.path.join(tempdir, "report.pdf"))
                            
                            # Read the generated PDF file
                            with open(os.path.join(tempdir, "report.pdf"), 'rb') as f:
                                pdf_data = f.read()
                            
                            # Clear status and show success
                            pdf_status.success("PDF report generated successfully!")
                            
                            # Provide download button
                            st.download_button(
                                "Download PDF Report",
                                pdf_data,
                                file_name=f"govsight_dashboard_report_{org}_{datetime.now().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf"
                            )
                    
                    except Exception as e:
                        st.error(f"Error generating PDF: {e}")
    except Exception as e:
        st.error(f"Error in export section: {e}")