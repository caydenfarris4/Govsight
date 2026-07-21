"""
Regulatory Auto-Integrator Module

This module provides functionality for automatically integrating
regulatory insights and references into financial analysis.

It identifies relevant regulatory information based on financial data
and user queries, then retrieves appropriate guidance from regulatory
knowledge bases (GASB, GAAP, etc.)

The module has two operating modes:
1. Static Mode: Uses predefined regulatory information (default)
2. External Mode: Connects to external sources like GASB, IRS, and state websites
"""

import os
import json
import re
import requests
from datetime import datetime
from urllib.parse import quote
from typing import Dict, List, Optional, Any, Union, Tuple

# Import necessary for web scraping
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Dictionary of regulatory sources and their content
REGULATORY_SOURCES = {
    "gasb": {
        "description": "Government Accounting Standards Board",
        "statements": {
            "34": "Basic Financial Statements—and Management's Discussion and Analysis—for State and Local Governments",
            "54": "Fund Balance Reporting and Governmental Fund Type Definitions",
            "68": "Accounting and Financial Reporting for Pensions",
            "75": "Accounting and Financial Reporting for Postemployment Benefits Other Than Pensions",
            "87": "Leases",
            "89": "Accounting for Interest Cost Incurred before the End of a Construction Period",
            "91": "Conduit Debt Obligations",
            "96": "Subscription-Based Information Technology Arrangements"
        }
    },
    "gaap": {
        "description": "Generally Accepted Accounting Principles",
        "principles": {
            "consistency": "Accounting practices should remain consistent across time periods",
            "going_concern": "The entity will continue to operate in the foreseeable future",
            "materiality": "Financial statements should disclose all items that may influence decisions",
            "conservatism": "When in doubt, use the accounting treatment with the least favorable effect on net assets",
            "full_disclosure": "Financial statements should include all information necessary to understand the entity's financial position"
        }
    },
    "budget_law": {
        "description": "Municipal Budget Laws",
        "requirements": {
            "balanced_budget": "Most municipalities must adopt a balanced budget where revenues equal or exceed expenditures",
            "public_hearing": "Budget adoption typically requires public hearings and input",
            "amendment_process": "Budget amendments typically require formal approval through a specific process",
            "reserves": "Many jurisdictions require minimum reserve levels (e.g., rainy day funds)",
            "submission_deadlines": "Budgets must be submitted and approved by specific statutory deadlines"
        }
    },
    "procurement": {
        "description": "Procurement and Contracting Requirements",
        "rules": {
            "competitive_bidding": "Purchases above certain thresholds typically require competitive bidding",
            "vendor_selection": "Vendor selection must follow objective criteria and avoid conflicts of interest",
            "documentation": "Procurement processes must be documented with clear justification for decisions",
            "thresholds": "Different procurement methods are required based on dollar thresholds",
            "emergency_provisions": "Special provisions exist for emergency procurement situations"
        }
    }
}

def query_with_sources(query: str, source: str) -> str:
    """
    Query regulatory sources for relevant guidance
    
    Args:
        query (str): The user's query or context
        source (str): The regulatory source to query
        
    Returns:
        str: Relevant regulatory guidance or context
    """
    # Ensure lowercase source name for consistency
    source = source.lower()
    
    # Check if the source exists
    if source not in REGULATORY_SOURCES:
        return f"Source '{source}' not available"
    
    source_data = REGULATORY_SOURCES[source]
    
    # Determine which part of the source to query based on source type
    if source == "gasb":
        content = source_data["statements"]
        content_type = "statement"
    elif source == "gaap":
        content = source_data["principles"]
        content_type = "principle"
    elif source == "budget_law":
        content = source_data["requirements"]
        content_type = "requirement"
    elif source == "procurement":
        content = source_data["rules"]
        content_type = "rule"
    else:
        content = {}
        content_type = "item"
    
    # Build response with relevant items
    response = f"{source_data['description']} ({source.upper()}) Guidance:\n\n"
    
    # Find relevant items based on the query
    query_lower = query.lower()
    relevant_items = []
    
    for key, text in content.items():
        # Check if any words from the item are in the query
        item_words = set(key.lower().split("_"))
        text_words = set(text.lower().split())
        
        # Get words that appear in both the query and item/text
        query_words = set(query_lower.split())
        matching_words_key = item_words.intersection(query_words)
        matching_words_text = text_words.intersection(query_words)
        
        if matching_words_key or matching_words_text:
            relevant_items.append((key, text))
    
    # If no relevant items found, return most important ones
    if not relevant_items:
        # Take the first 3 items as "most important"
        relevant_items = list(content.items())[:3]
    
    # Build the response with relevant items
    for key, text in relevant_items:
        response += f"- {content_type.upper()} {key}: {text}\n"
    
    return response

def get_regulatory_context(prompt: str, department: str = "") -> Dict[str, str]:
    """
    Get regulatory context based on the query and department
    
    Args:
        prompt (str): The user's query or context
        department (str): Optional department name for context
        
    Returns:
        Dict[str, str]: Dictionary of regulatory sources and their relevant guidance
    """
    # Dictionary to store context by source
    context = {}
    
    # Convert all inputs to lowercase for comparison
    prompt_lower = prompt.lower()
    department_lower = department.lower()
    
    # Keywords that trigger different regulatory sources
    gasb_keywords = ["financial report", "statement", "fund balance", "pension", "lease"]
    gaap_keywords = ["accounting", "principle", "consistency", "materiality", "disclosure"]
    budget_keywords = ["budget", "allocation", "fiscal year", "amendment", "reserve"]
    procurement_keywords = ["contract", "bid", "purchase", "vendor", "procurement"]
    
    # Department-specific triggers
    finance_keywords = ["finance", "accounting", "budget"]
    if any(kw in department_lower for kw in finance_keywords):
        # Finance department should get GASB and GAAP guidance
        context["gasb"] = query_with_sources(prompt, "gasb")
        context["gaap"] = query_with_sources(prompt, "gaap")
    
    # Check prompt for keywords
    if any(kw in prompt_lower for kw in gasb_keywords):
        context["gasb"] = query_with_sources(prompt, "gasb")
        
    if any(kw in prompt_lower for kw in gaap_keywords):
        context["gaap"] = query_with_sources(prompt, "gaap")
        
    if any(kw in prompt_lower for kw in budget_keywords):
        context["budget_law"] = query_with_sources(prompt, "budget_law")
        
    if any(kw in prompt_lower for kw in procurement_keywords):
        context["procurement"] = query_with_sources(prompt, "procurement")
    
    return context

def enhance_prompt_with_regulatory_context(prompt: str, department: str = "") -> str:
    """
    Enhance a prompt with relevant regulatory context
    
    Args:
        prompt (str): The original prompt
        department (str): Optional department name for context
        
    Returns:
        str: Enhanced prompt with regulatory context
    """
    context_dict = get_regulatory_context(prompt, department)
    
    if not context_dict:
        return prompt
    
    # Add regulatory context to the prompt
    enhanced_prompt = prompt + "\n\nRelevant Regulatory Context:\n"
    
    for source, guidance in context_dict.items():
        enhanced_prompt += f"\n--- {source.upper()} ---\n{guidance}\n"
    
    return enhanced_prompt

# ===== EXTERNAL REGULATORY SOURCES =====

# Configure external regulatory sources
EXTERNAL_REGULATORY_SOURCES = {
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
    "Alabama": "https://finance.alabama.gov/",
    "Alaska": "https://doa.alaska.gov/dof/",
    "Arizona": "https://des.az.gov/",
    "Arkansas": "https://www.dfa.arkansas.gov/",
    "California": "https://www.dof.ca.gov/",
    "Colorado": "https://www.colorado.gov/dpa",
    "Connecticut": "https://portal.ct.gov/opm",
    "Delaware": "https://finance.delaware.gov/",
    "Florida": "https://www.myfloridacfo.com/",
    "Georgia": "https://oca.georgia.gov/",
    "Hawaii": "https://budget.hawaii.gov/",
    "Idaho": "https://dfm.idaho.gov/",
    "Illinois": "https://www2.illinois.gov/rev/",
    "Indiana": "https://www.in.gov/sba/",
    "Iowa": "https://dom.iowa.gov/",
    "Kansas": "https://admin.ks.gov/",
    "Kentucky": "https://finance.ky.gov/",
    "Louisiana": "https://www.doa.la.gov/",
    "Maine": "https://www.maine.gov/dafs/",
    "Maryland": "https://dbm.maryland.gov/",
    "Massachusetts": "https://www.mass.gov/orgs/executive-office-for-administration-and-finance",
    "Michigan": "https://www.michigan.gov/treasury/",
    "Minnesota": "https://mn.gov/mmb/",
    "Mississippi": "https://www.dfa.ms.gov/",
    "Missouri": "https://oa.mo.gov/",
    "Montana": "https://sfsd.mt.gov/",
    "Nebraska": "https://das.nebraska.gov/",
    "Nevada": "https://budget.nv.gov/",
    "New Hampshire": "https://das.nh.gov/",
    "New Jersey": "https://www.nj.gov/treasury/",
    "New Mexico": "https://www.dfa.nm.gov/",
    "New York": "https://www.budget.ny.gov/",
    "North Carolina": "https://www.osbm.nc.gov/",
    "North Dakota": "https://www.nd.gov/omb/",
    "Ohio": "https://obm.ohio.gov/",
    "Oklahoma": "https://omes.ok.gov/",
    "Oregon": "https://www.oregon.gov/das/",
    "Pennsylvania": "https://www.budget.pa.gov/",
    "Rhode Island": "https://omb.ri.gov/",
    "South Carolina": "https://cg.sc.gov/",
    "South Dakota": "https://bfm.sd.gov/",
    "Tennessee": "https://www.tn.gov/finance.html",
    "Texas": "https://comptroller.texas.gov/",
    "Utah": "https://finance.utah.gov/",
    "Vermont": "https://finance.vermont.gov/",
    "Virginia": "https://www.doa.virginia.gov/",
    "Washington": "https://ofm.wa.gov/",
    "West Virginia": "https://finance.wv.gov/",
    "Wisconsin": "https://doa.wi.gov/",
    "Wyoming": "https://ai.wyo.gov/"
}

def get_website_text_content(url: str) -> str:
    """
    Get text content from a website using trafilatura
    
    Args:
        url (str): URL to scrape
        
    Returns:
        str: Extracted text content
    """
    if not TRAFILATURA_AVAILABLE:
        return f"Web scraping not available (trafilatura package not installed)"
        
    try:
        # Check cache if using Streamlit
        if STREAMLIT_AVAILABLE and 'regulatory_cache' in st.session_state:
            if url in st.session_state.regulatory_cache:
                return st.session_state.regulatory_cache[url]
        
        # Download and extract content
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                # Cache the result if using Streamlit
                if STREAMLIT_AVAILABLE and 'regulatory_cache' not in st.session_state:
                    st.session_state['regulatory_cache'] = {}
                if STREAMLIT_AVAILABLE:
                    st.session_state.regulatory_cache[url] = text
                return text
        
        return f"Could not extract content from {url}"
    except Exception as e:
        return f"Error extracting content: {str(e)}"

def search_external_regulatory_source(source_key: str, query: str) -> Dict[str, Any]:
    """
    Search an external regulatory source for information related to a query
    
    Args:
        source_key (str): Key identifying the regulatory source
        query (str): Search query
        
    Returns:
        Dict[str, Any]: Search results and metadata
    """
    if source_key not in EXTERNAL_REGULATORY_SOURCES:
        return {"error": f"Source '{source_key}' not found"}
    
    source = EXTERNAL_REGULATORY_SOURCES[source_key]
    if not source["enabled"]:
        return {"error": f"Source '{source_key}' is not enabled"}
    
    # Create cache key
    cache_key = f"{source_key}_{query}"
    if STREAMLIT_AVAILABLE and 'regulatory_cache' in st.session_state:
        if cache_key in st.session_state.regulatory_cache:
            return st.session_state.regulatory_cache[cache_key]
    
    try:
        # Call the appropriate search function based on the source
        if source_key == "gasb":
            results = search_gasb_external(query)
        elif source_key == "irs":
            results = search_irs_external(query)
        elif source_key == "gfoa":
            results = search_gfoa_external(query)
        elif source_key == "state_finance":
            # Get selected state
            state = "California"  # Default
            if STREAMLIT_AVAILABLE:
                state = st.session_state.get("selected_state", "California")
            results = search_state_finance_external(state, query)
        elif source_key == "municipal_code":
            # Get selected municipality
            municipality = ""
            if STREAMLIT_AVAILABLE:
                municipality = st.session_state.get("selected_municipality", "")
            results = search_municipal_code_external(municipality, query)
        else:
            results = {"error": f"Search not implemented for source '{source_key}'"}
        
        # Cache results if using Streamlit
        if STREAMLIT_AVAILABLE:
            if 'regulatory_cache' not in st.session_state:
                st.session_state['regulatory_cache'] = {}
            st.session_state.regulatory_cache[cache_key] = results
            
        return results
    except Exception as e:
        return {"error": f"Error searching {source_key}: {str(e)}"}

def search_gasb_external(query: str) -> Dict[str, Any]:
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

def search_irs_external(query: str) -> Dict[str, Any]:
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

def search_gfoa_external(query: str) -> Dict[str, Any]:
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

def search_state_finance_external(state: str, query: str) -> Dict[str, Any]:
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
    
    # Get the base URL for the selected state
    state_url = STATE_FINANCE_URLS.get(state, "")
    
    # Create a generic state regulations template and then customize for specific states
    generic_regulations = {
        "budget_process": {
            "title": f"{state} Budget Process",
            "summary": f"Guidelines for the {state} state budget development and approval process.",
            "url": f"{state_url}budget/",
            "keywords": ["budget", "process", "approval", "development"]
        },
        "financial_reporting": {
            "title": f"{state} Financial Reporting Requirements",
            "summary": f"Requirements for financial reporting by {state} local governments.",
            "url": f"{state_url}financial-reporting/",
            "keywords": ["financial", "reporting", "requirements", "statements"]
        },
        "grants": {
            "title": f"{state} Grant Opportunities",
            "summary": f"Current grant opportunities and programs available in {state} for local governments.",
            "url": f"{state_url}grants/",
            "keywords": ["grants", "funding", "opportunities", "assistance"]
        },
        "compliance": {
            "title": f"{state} Compliance Requirements",
            "summary": f"Regulatory compliance requirements for local governments in {state}.",
            "url": f"{state_url}compliance/",
            "keywords": ["compliance", "regulations", "requirements", "laws"]
        }
    }
    
    # Example state financial regulations with specific URLs for known states
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
            },
            "grants": {
                "title": "California Grant Opportunities",
                "summary": "Current grant opportunities and programs available in California for local governments.",
                "url": "https://www.dof.ca.gov/programs/grants/",
                "keywords": ["grants", "funding", "opportunities", "assistance"]
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
            },
            "grants": {
                "title": "Texas Grant Opportunities",
                "summary": "Current grant opportunities and programs available in Texas for local governments.",
                "url": "https://comptroller.texas.gov/transparency/local/grant-funding/",
                "keywords": ["grants", "funding", "opportunities", "assistance"]
            }
        },
        "Utah": {
            "budget_process": {
                "title": "Utah Budget Process",
                "summary": "Guidelines for the Utah state budget development and approval process.",
                "url": "https://finance.utah.gov/reporting-budget-execution/",
                "keywords": ["budget", "process", "approval", "development"]
            },
            "financial_reporting": {
                "title": "Utah Financial Reporting Requirements",
                "summary": "Requirements for financial reporting by Utah local governments.",
                "url": "https://finance.utah.gov/fixed-asset-accounting-financial-reporting/",
                "keywords": ["financial", "reporting", "requirements", "statements"]
            },
            "grants": {
                "title": "Utah Grant Opportunities",
                "summary": "Current grant opportunities and programs available in Utah for local governments.",
                "url": "https://finance.utah.gov/grants/",
                "keywords": ["grants", "funding", "opportunities", "assistance"]
            }
        }
    }
    
    # If state isn't in our specialized data, use the generic template
    if state not in state_regulations:
        state_regulations[state] = generic_regulations
    
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

def search_municipal_code_external(municipality: str, query: str) -> Dict[str, Any]:
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

def get_available_external_sources(enabled_only: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Get available external regulatory sources
    
    Args:
        enabled_only (bool): If True, only return enabled sources
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of regulatory sources
    """
    if enabled_only:
        return {k: v for k, v in EXTERNAL_REGULATORY_SOURCES.items() if v["enabled"]}
    return EXTERNAL_REGULATORY_SOURCES

def get_available_states() -> List[str]:
    """
    Get list of available states
    
    Returns:
        List[str]: List of state names
    """
    return sorted(STATE_FINANCE_URLS.keys())

def enable_external_source(source_key: str, enabled: bool = True) -> bool:
    """
    Enable or disable an external regulatory source
    
    Args:
        source_key (str): Key identifying the regulatory source
        enabled (bool): True to enable, False to disable
        
    Returns:
        bool: Success status
    """
    if source_key in EXTERNAL_REGULATORY_SOURCES:
        EXTERNAL_REGULATORY_SOURCES[source_key]["enabled"] = enabled
        return True
    return False

def query_external_sources(query: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Query multiple external regulatory sources
    
    Args:
        query (str): Search query
        sources (List[str], optional): List of source keys to query. If None, query all enabled sources.
        
    Returns:
        Dict[str, Any]: Aggregated search results
    """
    if not sources:
        # Use all enabled sources
        sources = [k for k, v in EXTERNAL_REGULATORY_SOURCES.items() if v["enabled"]]
    
    results = {}
    for source in sources:
        results[source] = search_external_regulatory_source(source, query)
    
    return {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "sources_queried": sources,
        "results": results
    }

def format_external_results(results: Dict[str, Any]) -> str:
    """
    Format external search results as text
    
    Args:
        results (Dict[str, Any]): Search results from query_external_sources
        
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