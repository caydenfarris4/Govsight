"""
Regulatory Data Connector

This module connects to external regulatory data sources including:
- GASB (Government Accounting Standards Board)
- IRS (Internal Revenue Service)
- State government websites
- Municipal code repositories

It provides a unified interface for retrieving regulatory information
from these external sources to enhance AI-driven financial analysis.
"""

import os
import json
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import streamlit as st
import requests
from urllib.parse import quote
try:
    import trafilatura
except ImportError:  # optional scraping dependency; degrade gracefully
    trafilatura = None

# Cache for regulatory data to avoid repeated API calls
if 'regulatory_cache' not in st.session_state:
    st.session_state.regulatory_cache = {}

# Configure available regulatory sources
REGULATORY_SOURCES = {
    "gasb": {
        "name": "Government Accounting Standards Board (GASB)",
        "base_url": "https://www.gasb.org/",
        "search_url": "https://www.gasb.org/page/PageContent?pageId=",
        "enabled": True
    },
    "irs": {
        "name": "Internal Revenue Service (IRS)",
        "base_url": "https://www.irs.gov/",
        "search_url": "https://www.irs.gov/search?query=",
        "enabled": True
    },
    "gfoa": {
        "name": "Government Finance Officers Association (GFOA)",
        "base_url": "https://www.gfoa.org/",
        "search_url": "https://www.gfoa.org/search?query=",
        "enabled": True
    },
    "state_finance": {
        "name": "State Financial Regulations",
        "base_url": "",  # This will be set based on the selected state
        "search_url": "",  # This will be set based on the selected state
        "enabled": True
    },
    "municipal_code": {
        "name": "Municipal Code References",
        "base_url": "",  # This will be set based on selected municipality
        "search_url": "",  # This will be set based on selected municipality
        "enabled": False  # Default to disabled until configured
    }
}

# State finance department URLs
STATE_FINANCE_URLS = {
    "California": "https://www.dof.ca.gov/",
    "Texas": "https://comptroller.texas.gov/",
    "New York": "https://www.budget.ny.gov/",
    "Florida": "https://www.myfloridacfo.com/",
    "Illinois": "https://www2.illinois.gov/rev/",
    # Add more states as needed
}

def get_website_text_content(url: str) -> str:
    """
    Get text content from a website using trafilatura
    
    Args:
        url (str): URL to scrape
        
    Returns:
        str: Extracted text content
    """
    if trafilatura is None:
        return "Web scraping not available (trafilatura package not installed)"
    try:
        # Check cache first
        if url in st.session_state.regulatory_cache:
            return st.session_state.regulatory_cache[url]

        # Download and extract content
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                # Cache the result
                st.session_state.regulatory_cache[url] = text
                return text
        
        return f"Could not extract content from {url}"
    except Exception as e:
        return f"Error extracting content: {str(e)}"

def search_regulatory_source(source_key: str, query: str) -> Dict[str, Any]:
    """
    Search a regulatory source for information related to a query
    
    Args:
        source_key (str): Key identifying the regulatory source
        query (str): Search query
        
    Returns:
        Dict[str, Any]: Search results and metadata
    """
    if source_key not in REGULATORY_SOURCES:
        return {"error": f"Source '{source_key}' not found"}
    
    source = REGULATORY_SOURCES[source_key]
    if not source["enabled"]:
        return {"error": f"Source '{source_key}' is not enabled"}
    
    # Create cache key
    cache_key = f"{source_key}_{query}"
    if cache_key in st.session_state.regulatory_cache:
        return st.session_state.regulatory_cache[cache_key]
    
    try:
        if source_key == "gasb":
            results = search_gasb(query)
        elif source_key == "irs":
            results = search_irs(query)
        elif source_key == "gfoa":
            results = search_gfoa(query)
        elif source_key == "state_finance":
            # Get selected state
            state = st.session_state.get("selected_state", "California")
            results = search_state_finance(state, query)
        elif source_key == "municipal_code":
            # Get selected municipality
            municipality = st.session_state.get("selected_municipality", "")
            results = search_municipal_code(municipality, query)
        else:
            results = {"error": f"Search not implemented for source '{source_key}'"}
        
        # Cache results
        st.session_state.regulatory_cache[cache_key] = results
        return results
    except Exception as e:
        return {"error": f"Error searching {source_key}: {str(e)}"}

def search_gasb(query: str) -> Dict[str, Any]:
    """
    Search GASB website for information (simulation)
    
    In a real implementation, this would make actual API calls to GASB.
    For now, we'll return structured data about relevant GASB statements.
    
    Args:
        query (str): Search query
        
    Returns:
        Dict[str, Any]: Search results and metadata
    """
    # In a real implementation, this would use APIs or web scraping
    # For this prototype, we'll use predefined content
    
    gasb_statements = {
        "statement_34": {
            "title": "Basic Financial Statements—and Management's Discussion and Analysis—for State and Local Governments",
            "summary": "Establishes financial reporting requirements including MD&A, government-wide statements, fund statements, notes, and RSI.",
            "url": "https://www.gasb.org/page/PageContent?pageId=26175",
            "effective_date": "June 15, 1999"
        },
        "statement_54": {
            "title": "Fund Balance Reporting and Governmental Fund Type Definitions",
            "summary": "Establishes fund balance classifications based on constraints and clarifies governmental fund type definitions.",
            "url": "https://www.gasb.org/page/PageContent?pageId=26176",
            "effective_date": "June 15, 2010"
        },
        "statement_68": {
            "title": "Accounting and Financial Reporting for Pensions",
            "summary": "Revises and establishes new financial reporting requirements for governments that provide pension benefits.",
            "url": "https://www.gasb.org/page/PageContent?pageId=26177",
            "effective_date": "June 15, 2014"
        },
        "statement_87": {
            "title": "Leases",
            "summary": "Requires recognition of certain lease assets and liabilities for leases previously classified as operating leases.",
            "url": "https://www.gasb.org/page/PageContent?pageId=26178",
            "effective_date": "June 15, 2021"
        }
    }
    
    # Find relevant statements based on query
    query_terms = set(query.lower().split())
    results = []
    
    for statement_id, data in gasb_statements.items():
        # Check if any query terms appear in title or summary
        title_terms = set(data["title"].lower().split())
        summary_terms = set(data["summary"].lower().split())
        
        # Count matching terms
        matching_title = query_terms.intersection(title_terms)
        matching_summary = query_terms.intersection(summary_terms)
        
        if matching_title or matching_summary:
            # Score based on number of matching terms
            score = len(matching_title) * 2 + len(matching_summary)
            results.append({
                "id": statement_id,
                "relevance_score": score,
                **data
            })
    
    # Sort by relevance
    results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "source": "gasb",
        "query": query,
        "result_count": len(results),
        "results": results
    }

def search_irs(query: str) -> Dict[str, Any]:
    """
    Search IRS website for information (simulation)
    
    In a real implementation, this would make actual API calls to the IRS website.
    For now, we'll return structured data about relevant IRS publications.
    
    Args:
        query (str): Search query
        
    Returns:
        Dict[str, Any]: Search results and metadata
    """
    # In a real implementation, this would use APIs or web scraping
    # For this prototype, we'll use predefined content
    
    irs_publications = {
        "publication_963": {
            "title": "Federal-State Reference Guide",
            "summary": "A guide for government entities regarding federal tax withholding and reporting requirements.",
            "url": "https://www.irs.gov/pub/irs-pdf/p963.pdf",
            "relevance_tags": ["government", "withholding", "reporting", "compliance"]
        },
        "publication_1542": {
            "title": "Per Diem Rates",
            "summary": "Information on per diem rates for travel expenses.",
            "url": "https://www.irs.gov/pub/irs-pdf/p1542.pdf",
            "relevance_tags": ["travel", "expenses", "reimbursement", "per diem"]
        },
        "publication_5307": {
            "title": "Tax Reform Basics for Individuals and Families",
            "summary": "Explains tax reform changes affecting individuals and families.",
            "url": "https://www.irs.gov/pub/irs-pdf/p5307.pdf",
            "relevance_tags": ["tax reform", "individuals", "families", "deductions"]
        }
    }
    
    # Find relevant publications based on query
    query_terms = set(query.lower().split())
    results = []
    
    for pub_id, data in irs_publications.items():
        # Check query against title, summary and tags
        title_terms = set(data["title"].lower().split())
        summary_terms = set(data["summary"].lower().split())
        tag_terms = set(data["relevance_tags"])
        
        # Count matching terms
        matching_title = query_terms.intersection(title_terms)
        matching_summary = query_terms.intersection(summary_terms)
        matching_tags = query_terms.intersection(tag_terms)
        
        if matching_title or matching_summary or matching_tags:
            # Score based on number of matching terms
            score = len(matching_title) * 3 + len(matching_summary) * 2 + len(matching_tags)
            results.append({
                "id": pub_id,
                "relevance_score": score,
                **data
            })
    
    # Sort by relevance
    results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "source": "irs",
        "query": query,
        "result_count": len(results),
        "results": results
    }

def search_gfoa(query: str) -> Dict[str, Any]:
    """
    Search GFOA website for information (simulation)
    
    In a real implementation, this would make actual API calls to GFOA.
    For now, we'll return structured data about GFOA best practices.
    
    Args:
        query (str): Search query
        
    Returns:
        Dict[str, Any]: Search results and metadata
    """
    # In a real implementation, this would use APIs or web scraping
    # For this prototype, we'll use predefined content
    
    gfoa_best_practices = {
        "bp_budget": {
            "title": "Best Practices in Budget Development",
            "summary": "Recommendations for developing comprehensive budgets that align resources with government priorities.",
            "url": "https://www.gfoa.org/best-practices-in-budget-development",
            "category": "Budgeting"
        },
        "bp_financial_reporting": {
            "title": "Best Practices in Financial Reporting",
            "summary": "Guidelines for effective and transparent financial reporting for government entities.",
            "url": "https://www.gfoa.org/best-practices-in-financial-reporting",
            "category": "Financial Reporting"
        },
        "bp_debt_management": {
            "title": "Best Practices in Debt Management",
            "summary": "Strategies for managing government debt effectively and responsibly.",
            "url": "https://www.gfoa.org/best-practices-in-debt-management",
            "category": "Debt Management"
        },
        "bp_capital_planning": {
            "title": "Best Practices in Capital Planning",
            "summary": "Framework for developing and implementing capital improvement plans.",
            "url": "https://www.gfoa.org/best-practices-in-capital-planning",
            "category": "Capital Planning"
        }
    }
    
    # Find relevant best practices based on query
    query_terms = set(query.lower().split())
    results = []
    
    for bp_id, data in gfoa_best_practices.items():
        # Check query against title, summary and category
        title_terms = set(data["title"].lower().split())
        summary_terms = set(data["summary"].lower().split())
        category_terms = set(data["category"].lower().split())
        
        # Count matching terms
        matching_title = query_terms.intersection(title_terms)
        matching_summary = query_terms.intersection(summary_terms)
        matching_category = query_terms.intersection(category_terms)
        
        if matching_title or matching_summary or matching_category:
            # Score based on number of matching terms
            score = len(matching_title) * 3 + len(matching_summary) * 2 + len(matching_category)
            results.append({
                "id": bp_id,
                "relevance_score": score,
                **data
            })
    
    # Sort by relevance
    results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "source": "gfoa",
        "query": query,
        "result_count": len(results),
        "results": results
    }

def search_state_finance(state: str, query: str) -> Dict[str, Any]:
    """
    Search state finance department website for information (simulation)
    
    In a real implementation, this would make actual API calls to state websites.
    For now, we'll return structured data about state financial regulations.
    
    Args:
        state (str): State name
        query (str): Search query
        
    Returns:
        Dict[str, Any]: Search results and metadata
    """
    # In a real implementation, this would use APIs or web scraping
    # For this prototype, we'll use predefined content
    
    if state not in STATE_FINANCE_URLS:
        return {"error": f"State '{state}' not supported"}
    
    # Example state financial regulations (in a real implementation, this would be fetched from the state website)
    state_regulations = {
        "California": {
            "budget_process": {
                "title": "California Budget Process",
                "summary": "Guidelines for the California state budget development and approval process.",
                "url": "https://www.dof.ca.gov/budget/budget_process/",
                "keywords": ["budget", "process", "approval", "development"]
            },
            "financial_reporting": {
                "title": "California Financial Reporting Requirements",
                "summary": "Requirements for financial reporting by California local governments.",
                "url": "https://www.dof.ca.gov/accounting/financial_reporting/",
                "keywords": ["financial", "reporting", "requirements", "statements"]
            }
        },
        "Texas": {
            "budget_process": {
                "title": "Texas Budget Process",
                "summary": "Guidelines for the Texas state budget development and approval process.",
                "url": "https://comptroller.texas.gov/transparency/budget/",
                "keywords": ["budget", "process", "approval", "development"]
            },
            "financial_reporting": {
                "title": "Texas Financial Reporting Requirements",
                "summary": "Requirements for financial reporting by Texas local governments.",
                "url": "https://comptroller.texas.gov/transparency/local/financial-reporting/",
                "keywords": ["financial", "reporting", "requirements", "statements"]
            }
        }
    }
    
    if state not in state_regulations:
        return {"error": f"No regulations available for state '{state}'"}
    
    # Find relevant regulations based on query
    query_terms = set(query.lower().split())
    results = []
    
    for reg_id, data in state_regulations[state].items():
        # Check query against title, summary and keywords
        title_terms = set(data["title"].lower().split())
        summary_terms = set(data["summary"].lower().split())
        keyword_terms = set(data["keywords"])
        
        # Count matching terms
        matching_title = query_terms.intersection(title_terms)
        matching_summary = query_terms.intersection(summary_terms)
        matching_keywords = query_terms.intersection(keyword_terms)
        
        if matching_title or matching_summary or matching_keywords:
            # Score based on number of matching terms
            score = len(matching_title) * 3 + len(matching_summary) * 2 + len(matching_keywords)
            results.append({
                "id": reg_id,
                "relevance_score": score,
                **data
            })
    
    # Sort by relevance
    results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "source": f"state_finance_{state}",
        "query": query,
        "result_count": len(results),
        "results": results
    }

def search_municipal_code(municipality: str, query: str) -> Dict[str, Any]:
    """
    Search municipal code for information (simulation)
    
    In a real implementation, this would make actual API calls to municipal code repositories.
    For now, we'll return structured data about municipal financial regulations.
    
    Args:
        municipality (str): Municipality name
        query (str): Search query
        
    Returns:
        Dict[str, Any]: Search results and metadata
    """
    # This is a placeholder for municipal code search
    # In a real implementation, this would connect to municipal code repositories
    
    if not municipality:
        return {"error": "No municipality specified"}
    
    # Return a basic result
    return {
        "source": f"municipal_code_{municipality}",
        "query": query,
        "result_count": 0,
        "results": [],
        "message": "Municipal code search will be implemented in a future version."
    }

def get_regulatory_sources(enabled_only: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Get available regulatory sources
    
    Args:
        enabled_only (bool): If True, only return enabled sources
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of regulatory sources
    """
    if enabled_only:
        return {k: v for k, v in REGULATORY_SOURCES.items() if v["enabled"]}
    return REGULATORY_SOURCES

def get_available_states() -> List[str]:
    """
    Get list of available states
    
    Returns:
        List[str]: List of state names
    """
    return sorted(STATE_FINANCE_URLS.keys())

def enable_regulatory_source(source_key: str, enabled: bool = True) -> bool:
    """
    Enable or disable a regulatory source
    
    Args:
        source_key (str): Key identifying the regulatory source
        enabled (bool): True to enable, False to disable
        
    Returns:
        bool: Success status
    """
    if source_key in REGULATORY_SOURCES:
        REGULATORY_SOURCES[source_key]["enabled"] = enabled
        return True
    return False

def query_regulatory_sources(query: str, sources: List[str] = None) -> Dict[str, Any]:
    """
    Query multiple regulatory sources
    
    Args:
        query (str): Search query
        sources (List[str], optional): List of source keys to query. If None, query all enabled sources.
        
    Returns:
        Dict[str, Any]: Aggregated search results
    """
    if not sources:
        # Use all enabled sources
        sources = [k for k, v in REGULATORY_SOURCES.items() if v["enabled"]]
    
    results = {}
    for source in sources:
        results[source] = search_regulatory_source(source, query)
    
    return {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "sources_queried": sources,
        "results": results
    }

def format_regulatory_results(results: Dict[str, Any]) -> str:
    """
    Format regulatory search results as text
    
    Args:
        results (Dict[str, Any]): Search results from query_regulatory_sources
        
    Returns:
        str: Formatted text for AI context
    """
    formatted_text = f"Regulatory Information for: {results['query']}\n\n"
    
    for source_key, source_results in results["results"].items():
        if "error" in source_results:
            formatted_text += f"[{source_key.upper()}]: {source_results['error']}\n\n"
            continue
        
        formatted_text += f"[{source_key.upper()}] - Found {source_results['result_count']} results\n"
        
        for i, result in enumerate(source_results.get("results", [])):
            if i >= 3:  # Limit to top 3 results per source
                break
                
            formatted_text += f"- {result['title']}\n"
            formatted_text += f"  Summary: {result['summary']}\n"
            if "url" in result:
                formatted_text += f"  Reference: {result['url']}\n"
            formatted_text += "\n"
    
    return formatted_text