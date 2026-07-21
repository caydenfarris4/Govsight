"""
Bill Lookup Service
Fetches bill details from Congress.gov API (federal) and state legislature websites.
Uses the Congress.gov API v3 for federal bills and trafilatura web scraping for state bills.
"""
import os
import re
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

CONGRESS_API_BASE = "https://api.congress.gov/v3"

STATE_LEGISLATURE_URLS = {
    "AL": {"name": "Alabama", "url": "https://legiscan.com/AL/legislation"},
    "AK": {"name": "Alaska", "url": "https://legiscan.com/AK/legislation"},
    "AZ": {"name": "Arizona", "url": "https://legiscan.com/AZ/legislation"},
    "AR": {"name": "Arkansas", "url": "https://legiscan.com/AR/legislation"},
    "CA": {"name": "California", "url": "https://leginfo.legislature.ca.gov"},
    "CO": {"name": "Colorado", "url": "https://leg.colorado.gov"},
    "CT": {"name": "Connecticut", "url": "https://legiscan.com/CT/legislation"},
    "DE": {"name": "Delaware", "url": "https://legiscan.com/DE/legislation"},
    "FL": {"name": "Florida", "url": "https://www.flsenate.gov"},
    "GA": {"name": "Georgia", "url": "https://legiscan.com/GA/legislation"},
    "HI": {"name": "Hawaii", "url": "https://legiscan.com/HI/legislation"},
    "ID": {"name": "Idaho", "url": "https://legiscan.com/ID/legislation"},
    "IL": {"name": "Illinois", "url": "https://www.ilga.gov"},
    "IN": {"name": "Indiana", "url": "https://legiscan.com/IN/legislation"},
    "IA": {"name": "Iowa", "url": "https://legiscan.com/IA/legislation"},
    "KS": {"name": "Kansas", "url": "https://legiscan.com/KS/legislation"},
    "KY": {"name": "Kentucky", "url": "https://legiscan.com/KY/legislation"},
    "LA": {"name": "Louisiana", "url": "https://legiscan.com/LA/legislation"},
    "ME": {"name": "Maine", "url": "https://legiscan.com/ME/legislation"},
    "MD": {"name": "Maryland", "url": "https://legiscan.com/MD/legislation"},
    "MA": {"name": "Massachusetts", "url": "https://malegislature.gov"},
    "MI": {"name": "Michigan", "url": "https://legiscan.com/MI/legislation"},
    "MN": {"name": "Minnesota", "url": "https://legiscan.com/MN/legislation"},
    "MS": {"name": "Mississippi", "url": "https://legiscan.com/MS/legislation"},
    "MO": {"name": "Missouri", "url": "https://legiscan.com/MO/legislation"},
    "MT": {"name": "Montana", "url": "https://legiscan.com/MT/legislation"},
    "NE": {"name": "Nebraska", "url": "https://legiscan.com/NE/legislation"},
    "NV": {"name": "Nevada", "url": "https://legiscan.com/NV/legislation"},
    "NH": {"name": "New Hampshire", "url": "https://legiscan.com/NH/legislation"},
    "NJ": {"name": "New Jersey", "url": "https://legiscan.com/NJ/legislation"},
    "NM": {"name": "New Mexico", "url": "https://legiscan.com/NM/legislation"},
    "NY": {"name": "New York", "url": "https://www.nysenate.gov"},
    "NC": {"name": "North Carolina", "url": "https://legiscan.com/NC/legislation"},
    "ND": {"name": "North Dakota", "url": "https://legiscan.com/ND/legislation"},
    "OH": {"name": "Ohio", "url": "https://legiscan.com/OH/legislation"},
    "OK": {"name": "Oklahoma", "url": "https://legiscan.com/OK/legislation"},
    "OR": {"name": "Oregon", "url": "https://legiscan.com/OR/legislation"},
    "PA": {"name": "Pennsylvania", "url": "https://legiscan.com/PA/legislation"},
    "RI": {"name": "Rhode Island", "url": "https://legiscan.com/RI/legislation"},
    "SC": {"name": "South Carolina", "url": "https://legiscan.com/SC/legislation"},
    "SD": {"name": "South Dakota", "url": "https://legiscan.com/SD/legislation"},
    "TN": {"name": "Tennessee", "url": "https://legiscan.com/TN/legislation"},
    "TX": {"name": "Texas", "url": "https://capitol.texas.gov"},
    "UT": {"name": "Utah", "url": "https://le.utah.gov"},
    "VT": {"name": "Vermont", "url": "https://legiscan.com/VT/legislation"},
    "VA": {"name": "Virginia", "url": "https://legiscan.com/VA/legislation"},
    "WA": {"name": "Washington", "url": "https://legiscan.com/WA/legislation"},
    "WV": {"name": "West Virginia", "url": "https://legiscan.com/WV/legislation"},
    "WI": {"name": "Wisconsin", "url": "https://legiscan.com/WI/legislation"},
    "WY": {"name": "Wyoming", "url": "https://legiscan.com/WY/legislation"}
}

US_STATES = {v["name"]: k for k, v in STATE_LEGISLATURE_URLS.items()}


def parse_bill_number(bill_input: str) -> Tuple[str, str, Optional[int]]:
    """
    Parse a bill number input into bill type, number, and optional congress number.
    
    Examples:
        "HR 1234" -> ("hr", "1234", None)
        "S. 567" -> ("s", "567", None)
        "HR 1234 (119th)" -> ("hr", "1234", 119)
        "HB 100" -> ("hb", "100", None) # state bill
        "SB 200" -> ("sb", "200", None) # state bill
    """
    cleaned = bill_input.strip().upper()
    
    congress_match = re.search(r'\((\d+)(?:TH|ST|ND|RD)?\)', cleaned)
    congress = int(congress_match.group(1)) if congress_match else None
    if congress_match:
        cleaned = cleaned[:congress_match.start()].strip()
    
    cleaned = cleaned.replace(".", "").replace("-", " ").replace("_", " ")
    
    parts = cleaned.split()
    if len(parts) >= 2:
        bill_type = parts[0].lower()
        bill_number = parts[-1]
        
        type_map = {
            "hr": "hr",
            "h": "hr",
            "house": "hr",
            "s": "s",
            "sen": "s",
            "senate": "s",
            "hjres": "hjres",
            "sjres": "sjres",
            "hconres": "hconres",
            "sconres": "sconres",
            "hres": "hres",
            "sres": "sres",
            "hb": "hb",
            "sb": "sb",
            "hj": "hjres",
            "sj": "sjres",
        }
        
        bill_type = type_map.get(bill_type, bill_type)
        return bill_type, bill_number, congress
    
    return cleaned.lower(), "", congress


def get_current_congress() -> int:
    """Calculate the current Congress number based on date"""
    year = datetime.now().year
    return ((year - 1789) // 2) + 1


def lookup_federal_bill(bill_type: str, bill_number: str, congress: Optional[int] = None) -> Dict[str, Any]:
    """
    Look up a federal bill. Uses Congress.gov API if API key is configured,
    otherwise falls back to web scraping Congress.gov directly via trafilatura.
    """
    if congress is None:
        congress = get_current_congress()
    
    api_key = os.environ.get("CONGRESS_API_KEY", "")
    
    result = {
        "source": "federal",
        "bill_type": bill_type,
        "bill_number": bill_number,
        "congress": congress,
        "found": False,
        "lookup_time": datetime.now().isoformat()
    }
    
    if not api_key:
        api_key = "DEMO_KEY"
    
    try:
        url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}"
        params = {"format": "json", "api_key": api_key}
        
        headers = {"Accept": "application/json"}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            bill = data.get("bill", {})
            
            result["found"] = True
            result["title"] = bill.get("title", "")
            result["introduced_date"] = bill.get("introducedDate", "")
            
            latest_action = bill.get("latestAction")
            if isinstance(latest_action, dict):
                result["status"] = latest_action.get("text", "Unknown")
                result["status_date"] = latest_action.get("actionDate", "")
            
            result["sponsors"] = []
            sponsors = bill.get("sponsors")
            if isinstance(sponsors, list):
                for sponsor in sponsors:
                    result["sponsors"].append({
                        "name": sponsor.get("fullName", f"{sponsor.get('firstName', '')} {sponsor.get('lastName', '')}"),
                        "party": sponsor.get("party", ""),
                        "state": sponsor.get("state", "")
                    })
            
            committees = bill.get("committees")
            result["committees"] = committees.get("count", 0) if isinstance(committees, dict) else 0
            
            cosponsors = bill.get("cosponsors")
            result["cosponsors_count"] = cosponsors.get("count", 0) if isinstance(cosponsors, dict) else 0
            
            policy_area = bill.get("policyArea")
            result["policy_area"] = policy_area.get("name", "") if isinstance(policy_area, dict) else ""
            
            result["origin_chamber"] = bill.get("originChamber", "")
            result["congress_url"] = f"https://www.congress.gov/bill/{congress}th-congress/{_format_bill_type_display(bill_type)}/{bill_number}"
            
            cbo = bill.get("cboCostEstimates")
            if isinstance(cbo, list) and cbo:
                result["cbo_estimates"] = [
                    {"description": est.get("description", ""), "url": est.get("url", "")}
                    for est in cbo[:3]
                ]
            
            summary = _fetch_bill_summary(congress, bill_type, bill_number, api_key)
            if summary:
                result["summary"] = summary
            
            return result
        
        elif response.status_code == 404:
            result["error"] = f"Bill {bill_type.upper()} {bill_number} not found in {congress}th Congress"
            prev_congress = congress - 1
            result["suggestion"] = f"Try the {prev_congress}th Congress if this is an older bill"
        else:
            result["error"] = f"API returned status {response.status_code}"
            
    except requests.exceptions.Timeout:
        result["error"] = "Request timed out - Congress.gov may be slow"
    except requests.exceptions.ConnectionError:
        result["error"] = "Could not connect to Congress.gov API"
    except Exception as e:
        result["error"] = f"Lookup error: {str(e)}"
    
    if not result["found"]:
        scraped = _scrape_congress_bill(bill_type, bill_number, congress)
        if scraped and scraped.get("found"):
            return scraped
    
    return result


def _fetch_bill_summary(congress: int, bill_type: str, bill_number: str, api_key: str = "") -> Optional[str]:
    """Fetch bill summary from the summaries endpoint"""
    try:
        if not api_key:
            api_key = "DEMO_KEY"
        url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}/summaries"
        params = {"format": "json", "api_key": api_key}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            summaries = data.get("summaries", [])
            if summaries:
                latest = summaries[-1]
                text = latest.get("text", "")
                text = re.sub(r'<[^>]+>', '', text)
                return text
    except Exception as e:
        logger.debug(f"Could not fetch summary: {e}")
    
    return None


def _format_bill_type_display(bill_type: str) -> str:
    """Format bill type for display URLs"""
    type_map = {
        "hr": "house-bill",
        "s": "senate-bill",
        "hjres": "house-joint-resolution",
        "sjres": "senate-joint-resolution",
        "hconres": "house-concurrent-resolution",
        "sconres": "senate-concurrent-resolution",
        "hres": "house-resolution",
        "sres": "senate-resolution"
    }
    return type_map.get(bill_type, bill_type)


def _scrape_congress_bill(bill_type: str, bill_number: str, congress: int) -> Optional[Dict[str, Any]]:
    """Fallback: scrape bill info from Congress.gov website"""
    try:
        import trafilatura
        
        type_display = _format_bill_type_display(bill_type)
        url = f"https://www.congress.gov/bill/{congress}th-congress/{type_display}/{bill_number}"
        
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        
        text = trafilatura.extract(downloaded)
        if not text:
            return None
        
        result = {
            "source": "federal",
            "bill_type": bill_type,
            "bill_number": bill_number,
            "congress": congress,
            "found": True,
            "title": "",
            "summary": text[:3000],
            "congress_url": url,
            "lookup_method": "web_scrape",
            "lookup_time": datetime.now().isoformat()
        }
        
        lines = text.split('\n')
        for line in lines[:5]:
            if bill_number in line or bill_type.upper() in line.upper():
                result["title"] = line.strip()
                break
        
        if not result["title"] and lines:
            result["title"] = lines[0].strip()[:200]
        
        return result
        
    except Exception as e:
        logger.error(f"Scraping fallback failed: {e}")
        return None


def lookup_state_bill(state_code: str, bill_type: str, bill_number: str) -> Dict[str, Any]:
    """
    Look up a state bill using web scraping of state legislature websites.
    Uses LegiScan search pages as a reliable cross-state source.
    """
    result = {
        "source": "state",
        "state": state_code,
        "state_name": STATE_LEGISLATURE_URLS.get(state_code, {}).get("name", state_code),
        "bill_type": bill_type,
        "bill_number": bill_number,
        "found": False,
        "lookup_time": datetime.now().isoformat()
    }
    
    try:
        import trafilatura
        
        bill_id = f"{bill_type.upper()}{bill_number}"
        search_url = f"https://legiscan.com/{state_code}/bill/{bill_id}"
        
        downloaded = trafilatura.fetch_url(search_url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 100:
                result["found"] = True
                result["raw_text"] = text[:5000]
                result["legislature_url"] = search_url
                
                lines = text.split('\n')
                for line in lines[:10]:
                    line_clean = line.strip()
                    if len(line_clean) > 20 and bill_number in line_clean:
                        result["title"] = line_clean[:300]
                        break
                
                if not result.get("title") and lines:
                    for line in lines[:5]:
                        if len(line.strip()) > 20:
                            result["title"] = line.strip()[:300]
                            break
                
                status_keywords = ["passed", "enrolled", "signed", "vetoed", "introduced", 
                                 "committee", "referred", "amended", "engrossed", "chaptered"]
                for line in lines:
                    line_lower = line.lower()
                    for keyword in status_keywords:
                        if keyword in line_lower:
                            result["status"] = line.strip()[:200]
                            break
                    if result.get("status"):
                        break
                
                result["summary"] = text[:3000]
                return result
        
        state_info = STATE_LEGISLATURE_URLS.get(state_code, {})
        if state_info.get("url") and "legiscan" not in state_info["url"]:
            state_url = state_info["url"]
            state_downloaded = trafilatura.fetch_url(f"{state_url}/bill/{bill_id}")
            if state_downloaded:
                state_text = trafilatura.extract(state_downloaded)
                if state_text and len(state_text) > 50:
                    result["found"] = True
                    result["raw_text"] = state_text[:5000]
                    result["summary"] = state_text[:3000]
                    result["legislature_url"] = f"{state_url}/bill/{bill_id}"
                    
                    lines = state_text.split('\n')
                    if lines:
                        result["title"] = lines[0].strip()[:300]
                    
                    return result
        
        result["error"] = f"Could not find {bill_type.upper()} {bill_number} in {result['state_name']}"
        result["suggestion"] = f"Check the bill number format. State bills typically use HB/SB prefixes. Try searching directly at {state_info.get('url', 'your state legislature website')}."
        
    except ImportError:
        result["error"] = "Web scraping library not available"
    except Exception as e:
        result["error"] = f"State bill lookup error: {str(e)}"
    
    return result


def search_bills_by_keyword(keyword: str, level: str = "federal", state_code: str = None) -> Dict[str, Any]:
    """Search for bills by keyword"""
    result = {
        "keyword": keyword,
        "level": level,
        "found": False,
        "bills": [],
        "lookup_time": datetime.now().isoformat()
    }
    
    if level == "federal":
        try:
            api_key = os.environ.get("CONGRESS_API_KEY", "")
            url = f"{CONGRESS_API_BASE}/bill"
            params = {
                "format": "json",
                "limit": 10,
                "query": keyword
            }
            if api_key:
                params["api_key"] = api_key
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                bills = data.get("bills", [])
                for bill in bills[:10]:
                    result["bills"].append({
                        "bill_type": bill.get("type", ""),
                        "bill_number": bill.get("number", ""),
                        "congress": bill.get("congress", ""),
                        "title": bill.get("title", ""),
                        "status": bill.get("latestAction", {}).get("text", ""),
                        "introduced": bill.get("introducedDate", "")
                    })
                result["found"] = len(result["bills"]) > 0
        except Exception as e:
            result["error"] = str(e)
    
    elif level == "state" and state_code:
        try:
            import trafilatura
            url = f"https://legiscan.com/{state_code}/search?query={keyword.replace(' ', '+')}"
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                if text:
                    result["found"] = True
                    result["search_results_text"] = text[:3000]
                    result["search_url"] = url
        except Exception as e:
            result["error"] = str(e)
    
    return result


def get_bill_financial_keywords(bill_data: Dict[str, Any]) -> list:
    """Extract financial-related keywords from bill data for impact analysis"""
    keywords = []
    
    text = ""
    for field in ["title", "summary", "raw_text"]:
        if bill_data.get(field):
            text += " " + bill_data[field]
    
    text_lower = text.lower()
    
    financial_terms = {
        "tax": "Tax Policy",
        "revenue": "Revenue Impact",
        "appropriation": "Appropriations",
        "budget": "Budget Impact",
        "funding": "Funding Changes",
        "grant": "Grant Programs",
        "infrastructure": "Infrastructure Spending",
        "wage": "Wage/Labor Costs",
        "minimum wage": "Minimum Wage",
        "pension": "Pension/Retirement",
        "healthcare": "Healthcare Costs",
        "insurance": "Insurance Requirements",
        "compliance": "Compliance Costs",
        "regulation": "Regulatory Impact",
        "environmental": "Environmental Compliance",
        "water": "Water/Utilities",
        "public safety": "Public Safety",
        "education": "Education Funding",
        "housing": "Housing Programs",
        "transportation": "Transportation",
        "broadband": "Technology/Broadband",
        "electric": "Energy/Utilities",
        "renewable": "Clean Energy",
        "emission": "Environmental Compliance",
        "police": "Law Enforcement",
        "fire": "Fire Services",
        "zoning": "Land Use/Zoning",
        "bond": "Bond/Debt",
        "debt": "Bond/Debt",
        "unfunded mandate": "Unfunded Mandates",
        "mandate": "Mandated Requirements",
        "procurement": "Procurement Rules",
        "prevailing wage": "Labor Requirements",
        "davis-bacon": "Labor Requirements",
        "medicaid": "Medicaid/Healthcare",
        "arpa": "Federal Relief Funds",
        "cdbg": "Community Development"
    }
    
    for term, category in financial_terms.items():
        if term in text_lower and category not in keywords:
            keywords.append(category)
    
    return keywords if keywords else ["General Legislative Impact"]
