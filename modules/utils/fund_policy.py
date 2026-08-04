"""
Fund Policy Module - Single source of truth for fund classifications and allocation eligibility.

Reads/writes fund classifications through the enterprise ConfigService (database-backed)
and provides helpers for determining which funds can participate in budget reallocations,
GASB compliance checks, and restricted fund enforcement.

ARCHITECTURAL DECISIONS:
1. Database-backed via ConfigService namespace 'fund_classifications'
   WHY: Atomic writes, audit trail, no JSON file race conditions in concurrent sessions
2. Fallback to JSON files if ConfigService unavailable (graceful degradation)
   WHY: System must remain functional during migration or if config DB is corrupted
3. Classification types align with GASB Statement No. 54 fund balance categories
   WHY: Municipal accounting standards require these specific classifications
4. Allocation eligibility is restrictive by default (only Unrestricted funds eligible)
   WHY: Accidentally including restricted funds in reallocations violates GASB/GAAP
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

logger = logging.getLogger(__name__)

FUND_CLASSIFICATIONS_PATHS = [
    "configs/application/fund_classifications.json",
    "fund_classifications.json",
]

GASB_54_CATEGORIES = {
    "Unrestricted": {
        "description": "General purpose funds with no external restrictions on use",
        "gasb_reference": "GASB 54 - Unassigned Fund Balance",
        "reallocation_eligible": True,
        "requires_approval": False,
    },
    "Restricted": {
        "description": "Funds with externally imposed constraints (legislation, creditors, grantors)",
        "gasb_reference": "GASB 54 - Restricted Fund Balance",
        "reallocation_eligible": False,
        "requires_approval": False,
    },
    "Capital": {
        "description": "Funds designated for capital projects and infrastructure",
        "gasb_reference": "GASB 54 - Committed Fund Balance / Capital Projects Fund",
        "reallocation_eligible": False,
        "requires_approval": True,
    },
    "Debt Service": {
        "description": "Funds restricted to debt principal and interest payments",
        "gasb_reference": "GASB 54 - Restricted Fund Balance (Debt Covenants)",
        "reallocation_eligible": False,
        "requires_approval": False,
    },
    "Grant": {
        "description": "Funds received from grants with specific expenditure requirements",
        "gasb_reference": "GASB 54 - Restricted Fund Balance (Grantor Restrictions)",
        "reallocation_eligible": False,
        "requires_approval": False,
    },
    "Other": {
        "description": "Funds not classified in standard categories - review individually",
        "gasb_reference": "GASB 54 - Assigned Fund Balance",
        "reallocation_eligible": False,
        "requires_approval": True,
    },
}

DEFAULT_REALLOCATION_ELIGIBLE_TYPES = ["Unrestricted"]


def _get_config_service():
    try:
        from modules.services.config_service import get_config_service
        return get_config_service()
    except Exception:
        return None


def _tenant_config_path() -> Optional[str]:
    """Per-city classifications when running inside a non-default tenant
    request (the founding city keeps the legacy locations)."""
    try:
        from modules.tenancy.context import DEFAULT_TENANT, current_tenant, tenant_db_path
        if current_tenant() != DEFAULT_TENANT:
            return tenant_db_path("fund_classifications.json")
    except Exception:
        pass
    return None


def _find_config_path() -> Optional[str]:
    tenant_path = _tenant_config_path()
    if tenant_path is not None:
        return tenant_path if os.path.exists(tenant_path) else None
    for path in FUND_CLASSIFICATIONS_PATHS:
        if os.path.exists(path):
            return path
    return None


def load_fund_classifications() -> Dict[str, str]:
    # Non-default tenants read only their own file - the shared
    # ConfigService belongs to the founding city
    tenant_path = _tenant_config_path()
    if tenant_path is not None:
        try:
            with open(tenant_path) as f:
                return json.load(f)
        except Exception:
            return {}
    svc = _get_config_service()
    if svc:
        try:
            data = svc.get_namespace("fund_classifications")
            if data:
                logger.info(f"Loaded fund classifications from ConfigService: {len(data)} funds")
                return data
        except Exception as e:
            logger.warning(f"ConfigService read failed, falling back to JSON: {e}")

    config_path = _find_config_path()
    if not config_path:
        logger.warning("No fund classifications found in database or JSON files.")
        return {}

    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded fund classifications from JSON fallback {config_path}: {len(data)} funds")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading fund classifications from {config_path}: {e}")
        return {}


def save_fund_classifications(classifications: Dict[str, str], updated_by: str = "admin") -> bool:
    tenant_path = _tenant_config_path()
    if tenant_path is not None:
        try:
            os.makedirs(os.path.dirname(tenant_path) or ".", exist_ok=True)
            with open(tenant_path, "w") as f:
                json.dump(classifications, f, indent=4)
            return True
        except IOError as e:
            logger.error(f"Error saving tenant fund classifications: {e}")
            return False
    svc = _get_config_service()
    if svc:
        try:
            result = svc.set_namespace("fund_classifications", classifications, updated_by=updated_by)
            if result:
                logger.info(f"Saved fund classifications to ConfigService: {len(classifications)} funds")
                return True
        except Exception as e:
            logger.error(f"ConfigService write failed: {e}")

    config_path = _find_config_path() or FUND_CLASSIFICATIONS_PATHS[0]
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(classifications, f, indent=4)
        logger.info(f"Saved fund classifications to JSON fallback {config_path}: {len(classifications)} funds")
        return True
    except IOError as e:
        logger.error(f"Error saving fund classifications: {e}")
        return False


def get_fund_classification(fund_code: str) -> str:
    classifications = load_fund_classifications()
    return classifications.get(str(fund_code), "Unclassified")


def is_fund_restricted(fund_code: str) -> bool:
    classification = get_fund_classification(fund_code)
    if classification == "Unclassified":
        return True
    category = GASB_54_CATEGORIES.get(classification, {})
    return not category.get("reallocation_eligible", False)


def is_fund_eligible_for_reallocation(
    fund_code: str,
    allowed_types: Optional[List[str]] = None
) -> Tuple[bool, str]:
    if allowed_types is None:
        allowed_types = DEFAULT_REALLOCATION_ELIGIBLE_TYPES

    classification = get_fund_classification(fund_code)

    if classification == "Unclassified":
        return False, f"Fund '{fund_code}' has not been classified. Classify it in the Admin Panel before including in reallocations."

    if classification not in allowed_types:
        category_info = GASB_54_CATEGORIES.get(classification, {})
        gasb_ref = category_info.get("gasb_reference", "")
        return False, (
            f"Fund '{fund_code}' is classified as '{classification}' and cannot be "
            f"included in budget reallocations per {gasb_ref}. "
            f"Reason: {category_info.get('description', 'Restricted use')}."
        )

    return True, f"Fund '{fund_code}' is classified as '{classification}' and is eligible for reallocation."


def get_eligible_funds_for_reallocation(
    fund_codes: List[str],
    allowed_types: Optional[List[str]] = None
) -> Tuple[List[str], List[Dict[str, str]]]:
    if allowed_types is None:
        allowed_types = DEFAULT_REALLOCATION_ELIGIBLE_TYPES

    classifications = load_fund_classifications()
    eligible = []
    excluded = []

    for fund_code in fund_codes:
        fund_code_str = str(fund_code)
        classification = classifications.get(fund_code_str, "Unclassified")

        if classification in allowed_types:
            eligible.append(fund_code_str)
        else:
            category_info = GASB_54_CATEGORIES.get(classification, {})
            excluded.append({
                "fund_code": fund_code_str,
                "classification": classification,
                "reason": category_info.get("description", "Not classified as eligible"),
                "gasb_reference": category_info.get("gasb_reference", ""),
            })

    return eligible, excluded


def filter_dataframe_by_fund_eligibility(
    df,
    fund_column: str = "Fund",
    allowed_types: Optional[List[str]] = None,
) -> Tuple[Any, Any, List[Dict[str, str]]]:
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for DataFrame filtering")

    if allowed_types is None:
        allowed_types = DEFAULT_REALLOCATION_ELIGIBLE_TYPES

    classifications = load_fund_classifications()

    df["_fund_classification"] = df[fund_column].astype(str).map(
        lambda x: classifications.get(str(x), "Unclassified")
    )

    eligible_mask = df["_fund_classification"].isin(allowed_types)
    eligible_df = df[eligible_mask].drop(columns=["_fund_classification"])
    excluded_df = df[~eligible_mask].copy()

    excluded_info = []
    if not excluded_df.empty:
        for classification in excluded_df["_fund_classification"].unique():
            fund_codes = excluded_df[excluded_df["_fund_classification"] == classification][fund_column].unique()
            category_info = GASB_54_CATEGORIES.get(classification, {})
            for fc in fund_codes:
                excluded_info.append({
                    "fund_code": str(fc),
                    "classification": classification,
                    "reason": category_info.get("description", "Not eligible"),
                    "gasb_reference": category_info.get("gasb_reference", ""),
                })

    excluded_df = excluded_df.drop(columns=["_fund_classification"])

    return eligible_df, excluded_df, excluded_info


def get_policy_snapshot() -> Dict[str, Any]:
    classifications = load_fund_classifications()

    summary = {}
    for fund_code, classification in classifications.items():
        if classification not in summary:
            summary[classification] = []
        summary[classification].append(fund_code)

    eligible_types = [
        cat_name for cat_name, cat_info in GASB_54_CATEGORIES.items()
        if cat_info.get("reallocation_eligible", False)
    ]

    return {
        "total_funds_classified": len(classifications),
        "classifications_by_type": summary,
        "reallocation_eligible_types": eligible_types,
        "gasb_reference": "GASB Statement No. 54 - Fund Balance Reporting and Governmental Fund Type Definitions",
        "policy_rules": [
            "Only funds classified as 'Unrestricted' may be included in budget reallocations by default",
            "Restricted funds (grants, debt service, externally restricted) are prohibited from reallocation",
            "Capital funds require governing body approval before any reallocation",
            "Unclassified funds are blocked from reallocation until properly classified in the Admin Panel",
            "All fund reclassifications must be documented and comply with GASB 54 requirements",
        ],
        "timestamp": datetime.now().isoformat(),
    }


def get_gasb_compliance_context(fund_code: Optional[str] = None, query: str = "") -> Dict[str, Any]:
    context = {
        "gasb_54": {
            "title": "GASB Statement No. 54 - Fund Balance Reporting",
            "summary": "Establishes fund balance classifications for governmental funds: "
                       "Nonspendable, Restricted, Committed, Assigned, and Unassigned. "
                       "Restricts how fund balances can be used based on their classification.",
            "key_requirements": [
                "Fund balances must be classified by the extent of constraints on use",
                "Restricted balances have externally enforceable limitations (creditors, grantors, laws)",
                "Committed balances require formal action by governing body to set aside",
                "Assigned balances are intended for specific purposes but not formally committed",
                "Unassigned balances are available for any purpose in the General Fund only",
            ],
        },
        "gasb_34": {
            "title": "GASB Statement No. 34 - Basic Financial Statements",
            "summary": "Requires government-wide financial statements and fund financial statements "
                       "with Management's Discussion and Analysis (MD&A).",
        },
        "reallocation_rules": {
            "general": "Budget reallocations between funds must respect fund-level restrictions. "
                       "Moving resources from restricted to unrestricted funds violates GASB 54.",
            "best_practices": [
                "Document the authority and rationale for all interfund transfers",
                "Ensure reallocation does not violate bond covenants or grant terms",
                "Obtain governing body approval for committed fund reclassifications",
                "Maintain audit trail for all fund balance reclassifications",
            ],
        },
    }

    if fund_code:
        classification = get_fund_classification(fund_code)
        eligible, reason = is_fund_eligible_for_reallocation(fund_code)
        context["fund_specific"] = {
            "fund_code": fund_code,
            "classification": classification,
            "reallocation_eligible": eligible,
            "compliance_note": reason,
            "category_details": GASB_54_CATEGORIES.get(classification, {}),
        }

    return context


def validate_reallocation_request(
    source_funds: List[str],
    target_fund: Optional[str] = None,
) -> Dict[str, Any]:
    results = {
        "valid": True,
        "approved_sources": [],
        "blocked_sources": [],
        "warnings": [],
        "gasb_violations": [],
    }

    for fund_code in source_funds:
        eligible, reason = is_fund_eligible_for_reallocation(fund_code)
        if eligible:
            results["approved_sources"].append({
                "fund_code": fund_code,
                "classification": get_fund_classification(fund_code),
                "status": "approved",
            })
        else:
            results["valid"] = False
            results["blocked_sources"].append({
                "fund_code": fund_code,
                "classification": get_fund_classification(fund_code),
                "reason": reason,
                "status": "blocked",
            })
            results["gasb_violations"].append(
                f"GASB 54 Violation: Cannot reallocate from {fund_code} "
                f"({get_fund_classification(fund_code)}). {reason}"
            )

    if target_fund:
        target_class = get_fund_classification(target_fund)
        if target_class in ["Debt Service"]:
            results["warnings"].append(
                f"Target fund '{target_fund}' is classified as '{target_class}'. "
                f"Ensure incoming transfers comply with debt covenant requirements."
            )

    return results
