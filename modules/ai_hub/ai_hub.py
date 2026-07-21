# ai_hub.py
"""
AI Hub - Centralized AI Processing Module

ARCHITECTURAL DECISION: Centralizing all AI operations in a single hub
WHY: 
1. Consistent AI behavior across all modules
2. Single point for API key management and error handling
3. Unified prompt engineering and context building
4. Easier maintenance and upgrades to AI models
5. Cost control through centralized usage tracking

DESIGN PATTERNS:
- Context building: Standardized approach to providing data context to AI
- Error handling: Graceful degradation when AI services are unavailable
- Regulatory integration: Seamless connection to regulatory data sources
- Multi-format output: Support for text, PDF, and structured data responses
"""

import pandas as pd
import openai
import os
import streamlit as st
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import tempfile
from io import BytesIO
# PDF generation capability (optional)
try:
    from fpdf2 import FPDF
    PDF_AVAILABLE = True
except ImportError:
    try:
        from fpdf import FPDF
        PDF_AVAILABLE = True
    except ImportError:
        # PDF functionality will be disabled if fpdf2 is not available
        class FPDF:
            def __init__(self, *args, **kwargs):
                raise ImportError("PDF functionality requires fpdf2 package")
        PDF_AVAILABLE = False

# Import regulatory integrator with both static and external source capabilities
# WHY REGULATORY INTEGRATION: Municipal decisions must comply with regulations
# This integration provides real-time regulatory context for AI recommendations
from modules.vatica.regulatory_auto_integrator import (
    query_with_sources,                     # Static source queries - for cached/fast responses
    search_external_regulatory_source,      # External source queries for a single source
    query_external_sources,                 # External source queries for multiple sources
    format_external_results,                # Format external results for AI consumption
    get_available_external_sources,         # Get available external sources for user selection
    get_available_states                    # Get available states for state-specific regulations
    # WHY MULTIPLE QUERY TYPES: Different use cases need different performance/accuracy tradeoffs
)

# === Centralized Prompt Processor ===
def build_context(df: Optional[pd.DataFrame], sources: List[str], user_prompt: str) -> str:
    """
    Build comprehensive context for AI queries
    
    CONTEXT BUILDING STRATEGY:
    1. Data sample: Provides AI with actual data structure and values
    2. Regulatory sources: Ensures compliance with relevant regulations
    3. State context: Localizes regulatory advice to specific jurisdiction
    4. User prompt integration: Tailors context to specific user question
    
    WHY THIS APPROACH: AI needs sufficient context to provide accurate,
    relevant, and compliant recommendations for municipal financial decisions
    """
    context = ""
    
    # Add data context if available
    if df is not None and not df.empty:
        sample = df.head(10).to_csv(index=False)
        context += f"\n\nData Sample:\n{sample}"
        # WHY SAMPLE SIZE: 10 rows provides pattern recognition without token overflow
    
    # Check if we should use external regulatory sources
    use_external_sources = st.session_state.get('use_external_regulatory_sources', False)
    # WHY SESSION STATE: Allows users to toggle between fast local and comprehensive external sources
    
    # Get the selected state from session state
    selected_state = st.session_state.get('selected_state', 'Utah')  # Default to Utah if not set
    # WHY STATE SELECTION: Municipal regulations vary significantly by state
    
    if sources:
        if use_external_sources:
            try:
                # Include the state context in the log
                context += f"\n\n=== Using State Context: {selected_state} ===\n"
                
                # Query external regulatory sources
                results = query_external_sources(user_prompt, sources)
                context += f"\n\n=== External Regulatory Information ===\n"
                context += format_external_results(results)
            except Exception as e:
                context += f"\n\n[External Regulatory Sources Error]: {e}"
                # Fall back to static sources on error
                for src in sources:
                    try:
                        # When falling back to static sources, still mention the state
                        ref = query_with_sources(f"{user_prompt} for {selected_state}", src)
                        context += f"\n\n[{src.upper()} Reference for {selected_state}]:\n{ref}"
                    except Exception as e:
                        context += f"\n\n[{src.upper()} Reference Error]: {e}"
        else:
            # Use static regulatory sources but include state context
            for src in sources:
                try:
                    # Add state to the query to make it state-specific
                    ref = query_with_sources(f"{user_prompt} for {selected_state}", src)
                    context += f"\n\n[{src.upper()} Reference for {selected_state}]:\n{ref}"
                except Exception as e:
                    context += f"\n\n[{src.upper()} Reference Error]: {e}"

    return context

# === Central AI Caller ===
def ask_ai(prompt: str, df: Optional[pd.DataFrame] = None, sources: List[str] = [], model="gpt-4o", max_tokens=750) -> str:
    # Ensure we have valid inputs
    if prompt is None:
        prompt = ""
    if sources is None:
        sources = []
        
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY", None)
        except:
            pass
            
    if not api_key:
        return "AI assistance not available (API key missing)."
            
    context = build_context(df, sources, prompt)
    full_prompt = f"{prompt}\n\n{context}"

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a CPA-trained assistant offering budget and compliance insights based on provided data and laws."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=max_tokens
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            return "AI service quota exceeded. Please check your OpenAI account billing or provide a new API key with available credits."
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            return "AI service authentication failed. Please verify your API key is correct and active."
        elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            return "Network connection issue. Please check your internet connection and try again."
        else:
            return f"AI service temporarily unavailable: {error_msg}"

# === Department Specific AI Commentary ===
def generate_dept_insights(df: pd.DataFrame, dept_name: str = "", prompt: Optional[str] = None) -> str:
    """
    Generate AI insights for a specific department's financial data
    
    Args:
        df (pd.DataFrame): Department financial data
        dept_name (str): Department name for context
        prompt (Optional[str]): Custom prompt if provided
        
    Returns:
        str: AI-generated insights
    """
    # Default prompt based on department
    if prompt is None:
        if dept_name:
            prompt = f"Analyze the financial performance of the {dept_name} department. Identify key trends, variances, and provide actionable recommendations."
        else:
            prompt = "Analyze this municipal financial data and provide key insights and recommendations."
    
    # Get relevant regulatory sources based on department
    sources = []
    if "budget" in prompt.lower() or "allocation" in prompt.lower():
        sources.append("budget_law")
    if "finance" in dept_name.lower() or "accounting" in prompt.lower():
        sources.append("gaap")
        sources.append("gasb")
    if "contract" in prompt.lower() or "vendor" in prompt.lower() or "purchase" in prompt.lower():
        sources.append("procurement")
    
    # Call the main AI function
    return ask_ai(prompt, df, sources)

# === Optional: Source Memory Tracking ===
def get_default_sources(session) -> List[str]:
    if "selected_sources" not in session:
        session["selected_sources"] = ["gasb"]
    return session["selected_sources"]

# === Document Analysis ===
def analyze_document(doc_text: str, analysis_type: str = "General Summary") -> str:
    """
    Analyze a document with AI
    
    Args:
        doc_text (str): Text extracted from the document
        analysis_type (str): Type of analysis to perform
        
    Returns:
        str: AI analysis of the document
    """
    # Limit document text to prevent token overflows
    doc_preview = doc_text[:3000] + ("..." if len(doc_text) > 3000 else "")
    
    # Build prompt based on analysis type
    if analysis_type == "General Summary":
        prompt = f"Provide a comprehensive summary of this document: {doc_preview}"
        sources = []
    elif analysis_type == "Budget Impact Assessment":
        prompt = f"Assess the potential budget impact of the policies or changes described in this document: {doc_preview}"
        sources = ["budget_law", "gasb"]
    elif analysis_type == "Regulatory Compliance":
        prompt = f"Identify the regulatory implications and compliance requirements mentioned in this document: {doc_preview}"
        sources = ["gaap", "gasb", "budget_law"]
    elif analysis_type == "Policy Analysis":
        prompt = f"Analyze this document for policy compliance issues and highlight any areas of concern: {doc_preview}"
        sources = ["gaap", "gasb", "budget_law", "procurement"]
    else:
        # Custom analysis
        prompt = f"{analysis_type}\n\nDocument content: {doc_preview}"
        sources = ["gaap", "gasb"]
    
    # Call the main AI function with appropriate sources
    return ask_ai(prompt, None, sources, max_tokens=1000)

# === Forecasting Function ===
def generate_forecast(df: pd.DataFrame, year_col: str, value_col: str, forecast_years: int = 3) -> pd.DataFrame:
    """
    Generate simple linear forecast based on historical data
    
    Args:
        df (pd.DataFrame): DataFrame with historical data
        year_col (str): Column name for years or date periods
        value_col (str): Column name for values to forecast
        forecast_years (int): Number of years to forecast
        
    Returns:
        pd.DataFrame: Combined historical and forecast data with a Source column
    """
    print(f"FORECAST DEBUG: Starting generate_forecast with columns: {df.columns.tolist()}")
    print(f"FORECAST DEBUG: Year column: {year_col}, Value column: {value_col}")
    print(f"FORECAST DEBUG: DataFrame shape: {df.shape}")
    
    # Check if dataframe is empty or missing required columns
    if df.empty:
        print("FORECAST DEBUG: DataFrame is empty")
        return pd.DataFrame({year_col: [], value_col: [], "Source": []})
        
    if year_col not in df.columns:
        print(f"FORECAST DEBUG: Year column '{year_col}' not in columns")
        return pd.DataFrame({year_col: [], value_col: [], "Source": []})
        
    if value_col not in df.columns:
        print(f"FORECAST DEBUG: Value column '{value_col}' not in columns")
        return pd.DataFrame({year_col: [], value_col: [], "Source": []})

    print(f"FORECAST DEBUG: Year column type: {df[year_col].dtype}")
    print(f"FORECAST DEBUG: Value column type: {df[value_col].dtype}")
    print(f"FORECAST DEBUG: First few rows:\n{df.head(3)}")

    # Create a copy to avoid modifying the original dataframe
    working_df = df.copy()
    
    # Ensure value column is numeric
    try:
        if working_df[value_col].dtype == 'object':
            print(f"FORECAST DEBUG: Converting value column to numeric")
            working_df[value_col] = pd.to_numeric(working_df[value_col], errors='coerce')
            working_df = working_df.dropna(subset=[value_col])
    except Exception as e:
        print(f"FORECAST DEBUG: Error converting value column: {e}")
        
    # Select only the columns we need and aggregate by the year column
    try:
        print(f"FORECAST DEBUG: Grouping by year column")
        working_df = working_df[[year_col, value_col]].groupby(year_col, as_index=False).sum()
        working_df = working_df.sort_values(by=year_col)
        print(f"FORECAST DEBUG: After grouping, shape: {working_df.shape}")
    except Exception as e:
        print(f"FORECAST DEBUG: Error in grouping: {e}")
        return pd.DataFrame({year_col: [], value_col: [], "Source": []})
    
    # Try to convert year column to numeric for calculations
    print(f"FORECAST DEBUG: Converting year column to numeric form")
    try:
        # If the year_col is already numeric, this will work
        working_df["Year_Numeric"] = pd.to_numeric(working_df[year_col], errors="coerce")
        print(f"FORECAST DEBUG: Initial numeric conversion - non-NA count: {working_df['Year_Numeric'].count()}")
    except Exception as e:
        print(f"FORECAST DEBUG: Error in initial numeric conversion: {e}")
        # If conversion fails (e.g., for string dates), try to extract year from it
        try:
            print("FORECAST DEBUG: Trying to extract year from string")
            working_df["Year_Numeric"] = working_df[year_col].astype(str).str.extract(r'(\d{4})').astype(float)
            print(f"FORECAST DEBUG: After extraction - non-NA count: {working_df['Year_Numeric'].count()}")
        except Exception as extract_error:
            print(f"FORECAST DEBUG: Error extracting year: {extract_error}")
            # Last resort: create a sequence based on position
            print("FORECAST DEBUG: Using position-based sequence")
            working_df["Year_Numeric"] = range(len(working_df))
    
    # Remove any rows where conversion failed
    print(f"FORECAST DEBUG: Before NA removal: {len(working_df)} rows")
    working_df = working_df.dropna(subset=["Year_Numeric"])
    print(f"FORECAST DEBUG: After NA removal: {len(working_df)} rows")
    
    # Need at least 2 data points for linear forecasting
    if len(working_df) < 2:
        print("FORECAST DEBUG: Not enough data points after processing")
        return pd.DataFrame({year_col: [], value_col: [], "Source": []})

    # Get the values for linear regression
    x = working_df["Year_Numeric"].values
    y = working_df[value_col].values
    print(f"FORECAST DEBUG: X values: {x}")
    print(f"FORECAST DEBUG: Y values: {y}")

    # Calculate slope for linear forecast
    try:
        coef = (y[-1] - y[0]) / (x[-1] - x[0]) if (x[-1] - x[0]) != 0 else 0
        last_year_numeric = x[-1]
        last_year_actual = working_df[year_col].iloc[-1]
        last_value = y[-1]
        print(f"FORECAST DEBUG: Coefficient: {coef}")
        print(f"FORECAST DEBUG: Last year (numeric): {last_year_numeric}")
        print(f"FORECAST DEBUG: Last year (actual): {last_year_actual}")
        print(f"FORECAST DEBUG: Last value: {last_value}")
    except Exception as e:
        print(f"FORECAST DEBUG: Error calculating trend: {e}")
        return pd.DataFrame({year_col: [], value_col: [], "Source": []})
    
    # For non-numeric year columns, we need to determine how to increment
    is_numeric_year = False
    try:
        # Try to convert to int first (common for year values)
        print(f"FORECAST DEBUG: Determining year type. Type: {type(last_year_actual)}")
        year_increment = 1
        if isinstance(last_year_actual, (int, float)):
            is_numeric_year = True
            print("FORECAST DEBUG: Year is already numeric")
        elif isinstance(last_year_actual, str) and last_year_actual.isdigit():
            last_year_actual = int(last_year_actual)
            is_numeric_year = True
            print("FORECAST DEBUG: Year was string but converted to numeric")
        else:
            # If it's not a simple numeric value, use position-based forecasting
            is_numeric_year = False
            print("FORECAST DEBUG: Using position-based forecasting")
    except Exception as e:
        print(f"FORECAST DEBUG: Error determining year type: {e}")
        is_numeric_year = False
        
    # Generate forecast data
    forecast = []
    print(f"FORECAST DEBUG: Generating {forecast_years} forecast periods")
    for i in range(1, forecast_years + 1):
        try:
            # Calculate new value based on linear trend
            new_value = last_value + coef * i
            
            # Determine the new year value
            if is_numeric_year:
                # For numeric years (e.g., 2024, 2025), simply increment
                new_year = last_year_actual + i
                print(f"FORECAST DEBUG: Period {i}: Year={new_year}, Value={new_value}")
            else:
                # For non-numeric years or complex formats, use the numeric values we calculated
                new_year = last_year_numeric + i
                print(f"FORECAST DEBUG: Period {i}: NumericYear={new_year}, Value={new_value}")
                
            # Add to forecast list
            forecast.append({
                year_col: new_year, 
                value_col: round(new_value, 2)
            })
        except Exception as e:
            print(f"FORECAST DEBUG: Error generating forecast period {i}: {e}")

    # Create dataframe with forecast data
    try:
        print(f"FORECAST DEBUG: Creating forecast DataFrame with {len(forecast)} periods")
        forecast_df = pd.DataFrame(forecast) if forecast else pd.DataFrame({year_col: [], value_col: []})
        print(f"FORECAST DEBUG: Forecast DataFrame columns: {forecast_df.columns.tolist()}")
    except Exception as e:
        print(f"FORECAST DEBUG: Error creating forecast DataFrame: {e}")
        forecast_df = pd.DataFrame({year_col: [], value_col: []})
    
    # Add source columns to distinguish historical from forecast data
    if not forecast_df.empty:
        try:
            forecast_df["Source"] = "Forecast"
            print("FORECAST DEBUG: Added Source column to forecast data")
        except Exception as e:
            print(f"FORECAST DEBUG: Error adding Source column to forecast: {e}")
            # Try to fix the forecast DataFrame
            forecast_df = pd.DataFrame({
                year_col: [f[year_col] for f in forecast],
                value_col: [f[value_col] for f in forecast],
                "Source": ["Forecast"] * len(forecast)
            })
        
    # Create a copy of the working dataframe with only the columns we need
    try:
        print("FORECAST DEBUG: Creating historical DataFrame")
        historical_df = working_df[[year_col, value_col]].copy()
        historical_df["Source"] = "Actual"
        print(f"FORECAST DEBUG: Historical DataFrame columns: {historical_df.columns.tolist()}")
    except Exception as e:
        print(f"FORECAST DEBUG: Error creating historical DataFrame: {e}")
        # Try to create a minimal historical DataFrame
        historical_df = pd.DataFrame({
            year_col: working_df[year_col].tolist(),
            value_col: working_df[value_col].tolist(),
            "Source": ["Actual"] * len(working_df)
        })
    
    # Combine historical and forecast data
    try:
        print("FORECAST DEBUG: Combining historical and forecast data")
        if forecast_df.empty:
            result = historical_df
        else:
            result = pd.concat([historical_df, forecast_df], ignore_index=True)
        print(f"FORECAST DEBUG: Final result columns: {result.columns.tolist()}")
        print(f"FORECAST DEBUG: Final result shape: {result.shape}")
    except Exception as e:
        print(f"FORECAST DEBUG: Error combining data: {e}")
        # If everything fails, return a valid DataFrame with Source column
        result = pd.DataFrame({year_col: [], value_col: [], "Source": []})
    
    return result

# === What-If Adjustment Simulation ===
def simulate_adjustment(prompt: str, df: pd.DataFrame, model: str = "gpt-3.5-turbo") -> pd.DataFrame:
    """
    Simulate adjustments to financial data based on a natural language prompt
    
    Args:
        prompt (str): User's natural language request for adjustment
        df (pd.DataFrame): Original data to adjust
        model (str): AI model to use for the simulation (defaults to gpt-3.5-turbo for quota limits)
        
    Returns:
        pd.DataFrame: Modified data based on the prompt or the original dataframe with a new 'Simulated' column
    """
    if df.empty:
        return pd.DataFrame()
    
    # Verify that the dataframe has expected structure for financial data
    # If not, we'll add placeholder columns to make it work with simulations
    required_columns = ["Fund", "FiscalYear", "Budget", "Actual"]
    
    # Check if we need to adapt the data for simulation
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    # If we're missing columns, create a compatible version of the dataframe
    if missing_columns:
        print(f"Missing columns for simulation: {missing_columns}")
        # Create a compatible dataframe that preserves original columns but adds required ones
        simulation_df = df.copy()
        
        # Add any missing financial columns with default values
        for col in missing_columns:
            if col == "Fund":
                simulation_df["Fund"] = "General Fund"
            elif col == "FiscalYear":
                simulation_df["FiscalYear"] = 2023  # Default year
            elif col == "Budget":
                # Use a numeric column if available, otherwise default
                numeric_cols = simulation_df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    simulation_df["Budget"] = simulation_df[numeric_cols[0]]
                else:
                    simulation_df["Budget"] = 100000
            elif col == "Actual":
                # Set as 90% of budget by default
                if "Budget" in simulation_df.columns:
                    simulation_df["Actual"] = simulation_df["Budget"] * 0.9
                else:
                    simulation_df["Actual"] = 90000
    else:
        simulation_df = df.copy()
        
    # Sample 10 rows to fit into the token window
    context_sample = simulation_df.head(10).to_csv(index=False)
    system_msg = "You are a government finance analyst. Simulate the effect of the user's request on the data."

    try:
        # Try to use the OpenAI API to simulate changes
        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=model,  # Using gpt-3.5-turbo to avoid quota issues
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"User request: {prompt}\n\nOriginal Data:\n{context_sample}\n\nReturn only the modified rows as a CSV."}
                ],
                max_tokens=750
            )

            csv_response = response.choices[0].message.content.strip()
            modified_df = pd.read_csv(pd.compat.StringIO(csv_response))
            
            # If we had to add synthetic columns for the API call, now remove them
            if missing_columns:
                # Keep only original columns plus new ones that weren't in missing_columns
                original_columns = df.columns.tolist()
                for col in modified_df.columns:
                    if col not in original_columns and col not in missing_columns:
                        original_columns.append(col)
                
                # Ensure we don't lose any original data
                result_df = df.copy()
                
                # Add any new columns that the model created
                for col in modified_df.columns:
                    if col not in missing_columns and col not in result_df.columns:
                        result_df[col] = modified_df[col]
                
                # Add a simulation indicator
                result_df["Simulated"] = "Yes"
                
                return result_df
            else:
                # We didn't need to add any columns, so return the modified data directly
                return modified_df
                
        except Exception as api_error:
            print(f"OpenAI API error: {api_error}")
            # Fall back to rule-based simulation if API fails
            
            # Add a simulation column to the original data
            simulated_df = df.copy()
            
            # Create a simple rule-based simulation based on the prompt
            if "Simulated" not in simulated_df.columns:
                simulated_df["Simulated"] = "Yes"
                
            # Look for percentages in the prompt
            import re
            percentage_match = re.search(r'(\d+)%', prompt)
            percentage = float(percentage_match.group(1))/100 if percentage_match else 0.05
            
            # Apply changes based on keywords in the prompt
            if "Budget" in simulated_df.columns:
                if "cut" in prompt.lower() or "reduce" in prompt.lower() or "decrease" in prompt.lower():
                    simulated_df["Budget"] = simulated_df["Budget"] * (1 - percentage)
                    simulated_df["Budget Change"] = "Decreased"
                elif "increase" in prompt.lower() or "raise" in prompt.lower() or "grow" in prompt.lower():
                    simulated_df["Budget"] = simulated_df["Budget"] * (1 + percentage)
                    simulated_df["Budget Change"] = "Increased"
            
            return simulated_df
            
    except Exception as e:
        print(f"Simulation error: {e}")
        # Return original with a simulation indicator
        result_df = df.copy()
        result_df["Simulation Error"] = str(e)
        return result_df

# === PDF Reporting ===
def generate_pdf_report(df: pd.DataFrame, title: str = "AI Analysis Report", analysis_text: Optional[str] = None, 
                       include_data: bool = True, include_charts: bool = True) -> bytes:
    """
    Generate a PDF report with data analysis, insights, and relevant charts
    
    Args:
        df (pd.DataFrame): DataFrame containing the data to include in the report
        title (str): Title for the report
        analysis_text (Optional[str]): AI-generated analysis text to include, can be None
        include_data (bool): Whether to include data table in the report
        include_charts (bool): Whether to include relevant Plotly charts in the report
        
    Returns:
        bytes: PDF file as bytes for download
    """
    try:
        # Create a temporary directory for any files needed
        with tempfile.TemporaryDirectory() as tempdir:
            # Create PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Add title page
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, title, ln=True, align="C")
            pdf.set_font("Arial", "I", 10)
            pdf.cell(190, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
            pdf.ln(5)
            
            # Add AI Analysis if provided
            if analysis_text:
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(190, 10, "AI Analysis", ln=True)
                pdf.set_font("Arial", "", 10)
                
                # Make sure analysis_text is a string and split into paragraphs
                analysis_text_str = str(analysis_text) if analysis_text is not None else ""
                
                # Split text into manageable chunks to avoid FPDF limitations
                for paragraph in analysis_text_str.split("\n\n"):
                    pdf.multi_cell(190, 5, paragraph, ln=True)
                    pdf.ln(3)
            
            # Add charts if requested and enhanced report generator is available
            if include_charts and not df.empty:
                try:
                    from modules.reports.enhanced_report_generator import EnhancedReportGenerator
                    
                    # Create chart generator
                    chart_gen = EnhancedReportGenerator()
                    
                    # Determine report type based on data characteristics
                    report_type = "general"
                    if "Department" in df.columns:
                        report_type = "department"
                    elif "FiscalYear" in df.columns:
                        report_type = "historical"
                    elif "AccountType" in df.columns:
                        report_type = "balance_sheet"
                    
                    # Generate relevant charts
                    charts = chart_gen._generate_relevant_charts(df, report_type, None)
                    
                    # Add charts to PDF
                    for i, chart_info in enumerate(charts[:3]):  # Limit to 3 charts for PDF size
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(190, 10, chart_info['title'], ln=True)
                        
                        if 'description' in chart_info:
                            pdf.set_font("Arial", "", 10)
                            pdf.multi_cell(190, 5, chart_info['description'])
                            pdf.ln(5)
                        
                        # Save chart as image and embed
                        try:
                            chart_path = os.path.join(tempdir, f"chart_{i}.png")
                            chart_info['figure'].write_image(chart_path, width=800, height=500)
                            pdf.image(chart_path, x=10, w=170)
                        except Exception as chart_error:
                            pdf.set_font("Arial", "I", 8)
                            pdf.cell(190, 5, f"Chart embedding error: {str(chart_error)}", ln=True)
                            
                except ImportError:
                    # Enhanced report generator not available, skip charts
                    pass
                except Exception as e:
                    pdf.add_page()
                    pdf.set_font("Arial", "I", 10)
                    pdf.cell(190, 10, f"Chart generation error: {str(e)}", ln=True)
            
            # Add data table if requested
            if include_data and not df.empty:
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(190, 10, "Data Table", ln=True)
                
                # Calculate column width (limited to 8 columns maximum for better readability)
                num_cols = min(len(df.columns), 8)
                col_width = 180 / num_cols
                
                # Add headers
                pdf.set_font("Arial", "B", 8)
                for col in df.columns[:num_cols]:  # Limit to first 8 columns if more
                    pdf.cell(col_width, 10, str(col), border=1)
                pdf.ln()
                
                # Add data rows (limit to max 50 rows for PDF readability)
                pdf.set_font("Arial", "", 8)
                for _, row in df.head(50).iterrows():  # Limit to first 50 rows
                    for item in row[:num_cols]:  # Limit to first 8 columns
                        # Format numbers if possible
                        if isinstance(item, (int, float)):
                            formatted_val = f"{item:,.2f}"
                        else:
                            formatted_val = str(item)
                        
                        pdf.cell(col_width, 7, formatted_val[:15], border=1)  # Truncate long values
                    pdf.ln()
                
                # Add note if data was truncated
                if len(df) > 50 or len(df.columns) > 8:
                    pdf.set_font("Arial", "I", 8)
                    pdf.cell(190, 5, "(Data table truncated for PDF report)", ln=True)
            
            # Output PDF to file
            pdf_output_path = os.path.join(tempdir, "ai_report.pdf")
            pdf.output(dest='F', name=pdf_output_path)
            
            # Read the file back in as bytes
            with open(pdf_output_path, "rb") as f:
                return f.read()
    
    except Exception as e:
        # If PDF generation fails, return an error message
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(190, 10, "Error Generating PDF Report", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(190, 10, f"An error occurred: {str(e)}", ln=True)
        
        # Create temporary file for PDF output
        with tempfile.TemporaryDirectory() as tempdir:
            pdf_output_path = os.path.join(tempdir, "error_report.pdf")
            pdf.output(dest='F', name=pdf_output_path)
            
            # Read the file back in as bytes
            with open(pdf_output_path, "rb") as f:
                return f.read()

# === Multi-Chart PDF Reporting for BI Sandbox ===
def generate_multi_chart_report(charts_data: List[Dict], org_name: str = "GovSight", title: str = "Multi-Chart Report") -> bytes:
    """
    Generate a PDF report with multiple charts for BI Sandbox
    
    Args:
        charts_data (List[Dict]): List of chart configurations and associated data
                                 Each dict should have keys: 'config', 'data', 'title'
        org_name (str): Organization name for the report header
        title (str): Title for the report
        
    Returns:
        bytes: PDF file as bytes for download
    """
    try:
        # Create a temporary directory for any files needed
        with tempfile.TemporaryDirectory() as tempdir:
            # Create PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Add title page
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, f"{title} - {org_name}", ln=True, align="C")
            pdf.set_font("Arial", "I", 10)
            pdf.cell(190, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
            pdf.ln(5)
            
            # Add overview page
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(190, 10, "Dashboard Overview", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(190, 5, f"Number of charts: {len(charts_data)}", ln=True)
            pdf.cell(190, 5, f"Organization: {org_name}", ln=True)
            pdf.ln(5)
            
            # Process each chart
            for i, chart_info in enumerate(charts_data):
                # Extract chart data
                chart_title = chart_info.get('title', f"Chart {i+1}")
                chart_config = chart_info.get('config', {})
                chart_data = chart_info.get('data', pd.DataFrame())
                chart_desc = chart_info.get('description', '')
                
                # Add a page for this chart
                pdf.add_page()
                
                # Add chart title
                pdf.set_font("Arial", "B", 14)
                pdf.cell(190, 10, f"Chart {i+1}: {chart_title}", ln=True)
                
                # Add chart description if available
                if chart_desc:
                    pdf.set_font("Arial", "I", 10)
                    pdf.multi_cell(190, 5, f"Description: {chart_desc}", ln=True)
                    pdf.ln(3)
                
                # Add chart parameters if available
                if chart_config:
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(190, 10, "Chart Parameters:", ln=True)
                    pdf.set_font("Arial", "", 10)
                    
                    for key, value in chart_config.items():
                        if isinstance(value, list):
                            value_str = ", ".join(str(v) for v in value)
                        else:
                            value_str = str(value)
                        pdf.cell(190, 5, f"{key}: {value_str}", ln=True)
                    pdf.ln(5)
                
                # Add data table for this chart
                if not chart_data.empty:
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(190, 10, "Data Table:", ln=True)
                    
                    # Calculate column width (limited to 8 columns maximum for better readability)
                    num_cols = min(len(chart_data.columns), 8)
                    col_width = 180 / num_cols
                    
                    # Add headers
                    pdf.set_font("Arial", "B", 8)
                    for col in chart_data.columns[:num_cols]:
                        pdf.cell(col_width, 10, str(col), border=1)
                    pdf.ln()
                    
                    # Add data rows (limit to max 50 rows for PDF readability)
                    pdf.set_font("Arial", "", 8)
                    for _, row in chart_data.head(50).iterrows():
                        for item in row[:num_cols]:
                            # Format numbers if possible
                            if isinstance(item, (int, float)):
                                formatted_val = f"{item:,.2f}"
                            else:
                                formatted_val = str(item)
                            
                            pdf.cell(col_width, 7, formatted_val[:15], border=1)  # Truncate long values
                        pdf.ln()
                    
                    # Add note if data was truncated
                    if len(chart_data) > 50 or len(chart_data.columns) > 8:
                        pdf.set_font("Arial", "I", 8)
                        pdf.cell(190, 5, "(Data table truncated for PDF report)", ln=True)
            
            # Output PDF to file
            pdf_output_path = os.path.join(tempdir, "multi_chart_report.pdf")
            pdf.output(dest='F', name=pdf_output_path)
            
            # Read the file back in as bytes
            with open(pdf_output_path, "rb") as f:
                return f.read()
    
    except Exception as e:
        # If PDF generation fails, return an error message
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(190, 10, "Error Generating Multi-Chart Report", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(190, 10, f"An error occurred: {str(e)}", ln=True)
        
        # Create temporary file for PDF output
        with tempfile.TemporaryDirectory() as tempdir:
            pdf_output_path = os.path.join(tempdir, "error_report.pdf")
            pdf.output(dest='F', name=pdf_output_path)
            
            # Read the file back in as bytes
            with open(pdf_output_path, "rb") as f:
                return f.read()