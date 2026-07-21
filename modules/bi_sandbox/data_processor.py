"""
BI Sandbox Data Processor - Data manipulation and filtering
"""

import pandas as pd
import streamlit as st
from typing import Dict, List, Any, Optional
import numpy as np

def process_sandbox_data(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Process data for sandbox analysis
    
    Args:
        df: Raw data DataFrame
        config: Processing configuration
        
    Returns:
        Processed DataFrame
    """
    
    if df.empty:
        return df
    
    try:
        # Apply data cleaning
        processed_df = clean_data(df)
        
        # Apply transformations if specified
        if 'transformations' in config:
            processed_df = apply_transformations(processed_df, config['transformations'])
        
        # Apply aggregations if specified
        if 'aggregations' in config:
            processed_df = apply_aggregations(processed_df, config['aggregations'])
        
        return processed_df
        
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare data for analysis"""
    
    cleaned_df = df.copy()
    
    # Handle missing values
    for col in cleaned_df.columns:
        if cleaned_df[col].dtype in ['object', 'string']:
            # Fill missing categorical values
            cleaned_df[col] = cleaned_df[col].fillna('Unknown')
        elif cleaned_df[col].dtype in ['int64', 'float64']:
            # Fill missing numeric values with 0
            cleaned_df[col] = cleaned_df[col].fillna(0)
    
    # Remove completely empty rows
    cleaned_df = cleaned_df.dropna(how='all')
    
    # Convert string numbers to numeric where possible
    for col in cleaned_df.select_dtypes(include=['object']).columns:
        if cleaned_df[col].str.replace(',', '').str.replace('$', '').str.replace('-', '').str.isnumeric().any():
            try:
                cleaned_df[col] = pd.to_numeric(
                    cleaned_df[col].str.replace(',', '').str.replace('$', ''), 
                    errors='ignore'
                )
            except:
                pass
    
    return cleaned_df

def apply_filters(df: pd.DataFrame, filters: Dict[str, List[Any]]) -> pd.DataFrame:
    """
    Apply filters to DataFrame
    
    Args:
        df: DataFrame to filter
        filters: Dictionary of column names and selected values
        
    Returns:
        Filtered DataFrame
    """
    
    filtered_df = df.copy()
    
    for column, selected_values in filters.items():
        if column in filtered_df.columns and selected_values:
            # Apply filter only if values are selected
            filtered_df = filtered_df[filtered_df[column].isin(selected_values)]
    
    return filtered_df

def apply_transformations(df: pd.DataFrame, transformations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Apply data transformations"""
    
    transformed_df = df.copy()
    
    for transform in transformations:
        transform_type = transform.get('type', '')
        
        if transform_type == 'calculate_variance':
            transformed_df = calculate_variance(transformed_df, transform)
        elif transform_type == 'calculate_ratio':
            transformed_df = calculate_ratio(transformed_df, transform)
        elif transform_type == 'calculate_percentage':
            transformed_df = calculate_percentage(transformed_df, transform)
        elif transform_type == 'date_extraction':
            transformed_df = extract_date_components(transformed_df, transform)
    
    return transformed_df

def calculate_variance(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Calculate variance between two columns"""
    
    col1 = config.get('column1', 'Budget')
    col2 = config.get('column2', 'Actual')
    new_col = config.get('new_column', f'{col1}_vs_{col2}_Variance')
    
    if col1 in df.columns and col2 in df.columns:
        df[new_col] = df[col1] - df[col2]
    
    return df

def calculate_ratio(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Calculate ratio between two columns"""
    
    numerator = config.get('numerator', 'Actual')
    denominator = config.get('denominator', 'Budget')
    new_col = config.get('new_column', f'{numerator}_to_{denominator}_Ratio')
    
    if numerator in df.columns and denominator in df.columns:
        # Avoid division by zero
        df[new_col] = df[numerator] / df[denominator].replace(0, np.nan)
    
    return df

def calculate_percentage(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Calculate percentage of total for a column"""
    
    column = config.get('column', 'Budget')
    new_col = config.get('new_column', f'{column}_Percentage')
    group_by = config.get('group_by', None)
    
    if column in df.columns:
        if group_by and group_by in df.columns:
            # Calculate percentage within groups
            df[new_col] = df.groupby(group_by)[column].transform(lambda x: x / x.sum() * 100)
        else:
            # Calculate percentage of total
            df[new_col] = df[column] / df[column].sum() * 100
    
    return df

def extract_date_components(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """Extract date components from date columns"""
    
    date_column = config.get('date_column', 'Date')
    components = config.get('components', ['year', 'month', 'quarter'])
    
    if date_column not in df.columns:
        return df
    
    # Convert to datetime if not already
    try:
        df[date_column] = pd.to_datetime(df[date_column])
    except:
        st.warning(f"Could not convert {date_column} to datetime")
        return df
    
    # Extract requested components
    for component in components:
        if component == 'year':
            df[f'{date_column}_Year'] = df[date_column].dt.year
        elif component == 'month':
            df[f'{date_column}_Month'] = df[date_column].dt.month
        elif component == 'quarter':
            df[f'{date_column}_Quarter'] = df[date_column].dt.quarter
        elif component == 'day_of_week':
            df[f'{date_column}_DayOfWeek'] = df[date_column].dt.day_name()
        elif component == 'week':
            df[f'{date_column}_Week'] = df[date_column].dt.isocalendar().week
    
    return df

def apply_aggregations(df: pd.DataFrame, aggregations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Apply data aggregations"""
    
    aggregated_dfs = []
    
    for agg_config in aggregations:
        group_by = agg_config.get('group_by', [])
        measures = agg_config.get('measures', {})
        
        if not group_by or not measures:
            continue
        
        # Perform aggregation
        agg_df = df.groupby(group_by).agg(measures).reset_index()
        
        # Flatten column names if needed
        if isinstance(agg_df.columns, pd.MultiIndex):
            agg_df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in agg_df.columns]
        
        aggregated_dfs.append(agg_df)
    
    # Return the first aggregation result, or original data if no aggregations
    return aggregated_dfs[0] if aggregated_dfs else df

def get_data_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Get summary statistics for the data"""
    
    if df.empty:
        return {'message': 'No data available'}
    
    summary = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'numeric_columns': len(df.select_dtypes(include=['number']).columns),
        'categorical_columns': len(df.select_dtypes(include=['object']).columns),
        'missing_values': df.isnull().sum().sum(),
        'data_types': df.dtypes.to_dict()
    }
    
    # Add column-specific summaries
    summary['column_summaries'] = {}
    
    for col in df.columns:
        col_summary = {
            'type': str(df[col].dtype),
            'unique_values': df[col].nunique(),
            'missing_count': df[col].isnull().sum()
        }
        
        if df[col].dtype in ['int64', 'float64']:
            col_summary.update({
                'min': df[col].min(),
                'max': df[col].max(),
                'mean': df[col].mean(),
                'median': df[col].median()
            })
        else:
            # For categorical columns
            top_values = df[col].value_counts().head(5)
            col_summary['top_values'] = top_values.to_dict()
        
        summary['column_summaries'][col] = col_summary
    
    return summary

def validate_data_for_analysis(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """Validate data quality for analysis"""
    
    errors = []
    warnings = []
    
    # Check if data is empty
    if df.empty:
        errors.append("Dataset is empty")
        return False, errors
    
    # Check for minimum columns
    if len(df.columns) < 2:
        errors.append("Dataset must have at least 2 columns for analysis")
    
    # Check for numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        warnings.append("No numeric columns found - limited analysis options")
    
    # Check for excessive missing values
    missing_pct = (df.isnull().sum() / len(df)) * 100
    high_missing_cols = missing_pct[missing_pct > 50].index.tolist()
    
    if high_missing_cols:
        warnings.append(f"Columns with >50% missing values: {high_missing_cols}")
    
    # Check for duplicate rows
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        warnings.append(f"Found {duplicate_count} duplicate rows")
    
    # Check data consistency
    for col in df.select_dtypes(include=['object']).columns:
        unique_count = df[col].nunique()
        if unique_count > len(df) * 0.8:  # Too many unique values for categorical
            warnings.append(f"Column '{col}' has many unique values ({unique_count}) - consider if it should be categorical")
    
    return len(errors) == 0, errors + warnings

def create_data_sample(df: pd.DataFrame, sample_size: int = 1000) -> pd.DataFrame:
    """Create a representative sample of the data for faster processing"""
    
    if len(df) <= sample_size:
        return df
    
    # Stratified sampling if possible
    categorical_cols = df.select_dtypes(include=['object']).columns
    
    if len(categorical_cols) > 0:
        # Use the first categorical column for stratification
        strat_col = categorical_cols[0]
        
        try:
            # Sample proportionally from each category
            sampled_dfs = []
            for category in df[strat_col].unique():
                cat_df = df[df[strat_col] == category]
                cat_sample_size = max(1, int(sample_size * len(cat_df) / len(df)))
                
                if len(cat_df) > cat_sample_size:
                    cat_sample = cat_df.sample(n=cat_sample_size, random_state=42)
                else:
                    cat_sample = cat_df
                
                sampled_dfs.append(cat_sample)
            
            return pd.concat(sampled_dfs, ignore_index=True)
            
        except Exception:
            # Fall back to simple random sampling
            return df.sample(n=sample_size, random_state=42)
    else:
        # Simple random sampling
        return df.sample(n=sample_size, random_state=42)