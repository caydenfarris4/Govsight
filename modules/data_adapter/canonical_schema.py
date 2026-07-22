"""
Canonical data schema for GovSight ingestion.

Every external data source — the Caselle ERP API, other ERP REST APIs,
file exports, payroll systems — is massaged into these canonical entities
before anything downstream sees it. Modules never consume source-shaped
data directly; they consume canonical records, so adding a new source is
a mapping exercise, not a code change.

Each field carries enough metadata (type, aliases, description) for both
the AI mapping engine and the deterministic heuristic mapper to propose
source-to-canonical field mappings, and for the validator to enforce the
contract on every synced row.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CanonicalField:
    name: str
    dtype: str                      # 'string' | 'number' | 'date' | 'integer' | 'boolean'
    required: bool = False
    description: str = ""
    # Common names this field goes by in municipal ERP exports; used by the
    # heuristic mapper and given to the AI as hints
    aliases: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CanonicalEntity:
    name: str
    description: str
    fields: List[CanonicalField]
    # Fields that uniquely identify a record for idempotent re-syncs
    natural_key: List[str] = field(default_factory=list)

    def field_map(self) -> Dict[str, CanonicalField]:
        return {f.name: f for f in self.fields}

    def required_fields(self) -> List[str]:
        return [f.name for f in self.fields if f.required]


GL_ACCOUNTS = CanonicalEntity(
    name="gl_accounts",
    description="Chart of accounts with adopted budget and year-to-date actuals",
    natural_key=["account_number", "fiscal_year"],
    fields=[
        CanonicalField("account_number", "string", required=True,
                       description="Full GL account number including fund/department/object segments",
                       aliases=["account", "account_no", "acct", "gl_account", "account_code", "accountnumber"]),
        CanonicalField("account_name", "string", required=True,
                       description="Account description",
                       aliases=["description", "account_desc", "name", "title", "accountname"]),
        CanonicalField("account_type", "string", required=True,
                       description="Revenue, Expense, Asset, Liability, or Fund Balance",
                       aliases=["type", "acct_type", "category", "accounttype"]),
        CanonicalField("fund", "string", required=False,
                       description="Fund code or name",
                       aliases=["fund_code", "fund_no", "fund_id", "fund_name"]),
        CanonicalField("department", "string", required=False,
                       description="Department name or code",
                       aliases=["dept", "dept_name", "department_name", "dept_code", "division"]),
        CanonicalField("fiscal_year", "integer", required=True,
                       description="Fiscal year the amounts belong to",
                       aliases=["year", "fy", "fiscalyear", "budget_year"]),
        CanonicalField("budget_amount", "number", required=True,
                       description="Adopted/amended budget for the fiscal year",
                       aliases=["budget", "adopted_budget", "budgeted", "appropriation", "budget_amt"]),
        CanonicalField("ytd_actual", "number", required=True,
                       description="Year-to-date actual amount",
                       aliases=["actual", "ytd", "actual_amount", "ytd_amount", "actuals", "amount_ytd"]),
    ],
)

TRANSACTIONS = CanonicalEntity(
    name="transactions",
    description="General ledger transaction detail",
    natural_key=["source_transaction_id"],
    fields=[
        CanonicalField("source_transaction_id", "string", required=True,
                       description="Unique transaction identifier from the source system",
                       aliases=["transaction_id", "trans_id", "id", "pk_transaction", "doc_no", "reference"]),
        CanonicalField("transaction_date", "date", required=True,
                       description="Posting date",
                       aliases=["date", "post_date", "posting_date", "trans_date", "transactiondate"]),
        CanonicalField("account_number", "string", required=True,
                       description="GL account the transaction posted to",
                       aliases=["account", "gl_account", "acct", "account_code"]),
        CanonicalField("amount", "number", required=True,
                       description="Signed amount (positive = debit, negative = credit)",
                       aliases=["transaction_amount", "amt", "value", "total"]),
        CanonicalField("direction", "string", required=False,
                       description="Debit or Credit when the source separates them",
                       aliases=["dr_cr", "debit_credit", "dc", "type"]),
        CanonicalField("vendor_name", "string", required=False,
                       description="Vendor or payee",
                       aliases=["vendor", "payee", "supplier", "vendor_desc"]),
        CanonicalField("description", "string", required=False,
                       description="Transaction description or memo",
                       aliases=["memo", "desc", "narrative", "detail"]),
        CanonicalField("department", "string", required=False,
                       aliases=["dept", "dept_name", "department_name"]),
        CanonicalField("fund", "string", required=False,
                       aliases=["fund_code", "fund_no", "fund_name"]),
    ],
)

VENDORS = CanonicalEntity(
    name="vendors",
    description="Vendor master records",
    natural_key=["source_vendor_id"],
    fields=[
        CanonicalField("source_vendor_id", "string", required=True,
                       aliases=["vendor_id", "vendor_no", "id", "supplier_id"]),
        CanonicalField("vendor_name", "string", required=True,
                       aliases=["name", "vendor", "supplier", "company"]),
        CanonicalField("tax_id", "string", required=False,
                       description="EIN/TIN for 1099 tracking",
                       aliases=["ein", "tin", "tax_number", "federal_id"]),
        CanonicalField("is_1099", "boolean", required=False,
                       aliases=["ten99", "1099", "requires_1099", "flag_1099"]),
    ],
)

DEPARTMENTS = CanonicalEntity(
    name="departments",
    description="Department master records",
    natural_key=["source_department_id"],
    fields=[
        CanonicalField("source_department_id", "string", required=True,
                       aliases=["department_id", "dept_id", "dept_code", "id", "code"]),
        CanonicalField("department_name", "string", required=True,
                       aliases=["name", "dept_name", "department", "description"]),
        CanonicalField("fund", "string", required=False,
                       aliases=["fund_code", "fund_no", "fund_name"]),
    ],
)

CANONICAL_ENTITIES: Dict[str, CanonicalEntity] = {
    e.name: e for e in [GL_ACCOUNTS, TRANSACTIONS, VENDORS, DEPARTMENTS]
}


def get_entity(name: str) -> Optional[CanonicalEntity]:
    return CANONICAL_ENTITIES.get(name)


def entity_prompt_description(entity: CanonicalEntity) -> str:
    """Render an entity as a compact description for the AI mapping prompt."""
    lines = [f"Target entity: {entity.name} — {entity.description}", "Fields:"]
    for f in entity.fields:
        req = "REQUIRED" if f.required else "optional"
        alias_hint = f" (also seen as: {', '.join(f.aliases[:6])})" if f.aliases else ""
        lines.append(f"- {f.name} ({f.dtype}, {req}): {f.description}{alias_hint}")
    return "\n".join(lines)
