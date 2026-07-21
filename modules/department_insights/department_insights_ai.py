"""
Department Insights AI Module

This module adds enhanced AI analysis capabilities to the Department Insights tab,
leveraging the centralized AI Hub for more consistent and maintainable AI functionality.
"""

import streamlit as st
import pandas as pd
from typing import Optional, List
import os
import sqlite3

# Import the centralized AI Hub
from ai_hub import ask_ai, generate_dept_insights

# Import database functions
from modules.database.db_connection import load_org_data, format_currency, format_percentage, get_db_path_for_org

def generate_ai_commentary(df, prompt=None):
    """
    Generate AI commentary on department data using the centralized AI Hub
    
    Args:
        df (DataFrame): pandas DataFrame with department data
        prompt (str, optional): User prompt for specific analysis. Defaults to None.
        
    Returns:
        str: AI commentary on the data
    """
    # Create a fallback response in case AI is not available
    fallback_response = """
    Based on the department financial data analysis:
    
    1. Look for consistent patterns in budget allocation across funds
    2. Compare actual vs. budgeted amounts to identify areas of concern
    3. Identify key spending categories that drive department costs
    4. Consider seasonal or periodic spending patterns that may affect projections
    """
    
    try:
        # Get current department for context
        department = ""
        if 'selected_dept' in st.session_state:
            department = st.session_state.selected_dept
            
        # Use the department-specific AI insights function from the centralized hub
        return generate_dept_insights(df, department, prompt)
    except Exception as e:
        # If centralized AI fails, fall back to basic response
        if st.session_state.get("debug_mode", False):
            st.warning(f"Enhanced AI features unavailable. Using fallback response. Error: {str(e)}")
        return fallback_response

def generate_department_performance_insights(df, department_name, fiscal_years):
    """
    Generate comprehensive department performance insights using the AI Hub
    
    Args:
        df (DataFrame): Department data
        department_name (str): Name of the department
        fiscal_years (List): List of selected fiscal years
        
    Returns:
        str: AI-generated insights
    """
    prompt = f"""
    Analyze the financial performance of the {department_name} department for fiscal years {', '.join(map(str, fiscal_years))}.
    Focus on:
    1. Budget vs. actual performance trends
    2. Spending patterns and anomalies
    3. Areas of concern or opportunities
    4. Actionable recommendations for budget optimization
    
    Provide specific insights based on the data. Be concise but thorough.
    """
    
    return generate_dept_insights(df, department_name, prompt)

def get_fund_allocation_recommendations(df, department_name):
    """
    Get AI recommendations for fund allocation optimization
    
    Args:
        df (DataFrame): Fund allocation data
        department_name (str): Name of the department
        
    Returns:
        str: AI-generated recommendations
    """
    prompt = f"""
    Based on the fund allocation data for the {department_name} department,
    provide specific recommendations for optimizing fund allocation to maximize efficiency and impact.
    Consider historical performance, spending patterns, and potential areas for reallocation.
    """
    
    return generate_dept_insights(df, department_name, prompt)

def analyze_gl_accounts(gl_data, department_name):
    """
    Generate detailed analysis of GL account data using AI
    
    Args:
        gl_data (DataFrame): GL account data
        department_name (str): Name of the department
        
    Returns:
        str: AI-generated analysis
    """
    if gl_data is None or gl_data.empty:
        return "No GL account data available for analysis."
    
    prompt = f"""
    Analyze the General Ledger account data for the {department_name} department.
    Identify:
    1. Key expense categories and their proportion of the total budget
    2. Accounts with significant variances between budget and actual
    3. Spending trends across accounts
    4. Potential areas for cost control or efficiency improvements
    
    Focus on actionable insights that can help improve financial management.
    """
    
    return generate_dept_insights(gl_data, department_name, prompt)

def answer_department_question(df, question, department_name, fiscal_years):
    """
    Answer a specific question about department performance using AI
    
    Args:
        df (DataFrame): Department data
        question (str): User's question
        department_name (str): Name of the department
        fiscal_years (List): List of selected fiscal years
        
    Returns:
        str: AI response to the question
    """
    context = f"Department: {department_name}\nFiscal Years: {', '.join(map(str, fiscal_years))}"
    prompt = f"Based on the municipal financial performance data, answer this question: '{question}'\n{context}"
    
    return generate_dept_insights(df, department_name, prompt)

def compare_departments(df, departments, fiscal_years):
    """
    Generate a comparative analysis between multiple departments
    
    Args:
        df (DataFrame): Organization-wide data
        departments (List): List of departments to compare
        fiscal_years (List): List of selected fiscal years
        
    Returns:
        str: AI-generated comparative analysis
    """
    dept_list = ", ".join(departments)
    prompt = f"""
    Compare the financial performance of these departments: {dept_list} for fiscal years {', '.join(map(str, fiscal_years))}.
    Include:
    1. Budget efficiency (which departments are closest to their budget targets)
    2. Growth trends (which departments show increasing/decreasing spending)
    3. Budget allocation (proportion of total budget for each department)
    4. Recommendations for resource reallocation based on performance
    """
    
    return ask_ai(prompt, df)