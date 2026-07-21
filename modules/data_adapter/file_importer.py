"""
File Import Service
Handles CSV and PDF import from export folders for non-Caselle municipalities
"""

import os
import json
import csv
import shutil
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pdfplumber not available - PDF import disabled")

class FileImportService:
    """
    Service for importing financial data from exported files
    
    Supported formats:
    - CSV: Direct parsing into structured data
    - PDF: Text extraction and parsing (requires pdfplumber)
    
    Workflow:
    1. Files placed in incoming folder
    2. Service processes and parses files
    3. Data archived to report archive database
    4. Original files moved to processed folder
    """
    
    SUPPORTED_REPORT_TYPES = [
        "general_ledger",
        "budget",
        "accounts_payable",
        "accounts_receivable",
        "payroll",
        "utility_billing",
        "fixed_assets",
        "chart_of_accounts",
        "trial_balance",
        "cash_receipts",
        "check_register",
        "vendor_list",
        "employee_list"
    ]
    
    def __init__(
        self,
        incoming_folder: str = "imports/incoming",
        processed_folder: str = "imports/processed",
        archive_folder: str = "imports/archive",
        municipality_id: str = "default"
    ):
        self.incoming_folder = Path(incoming_folder)
        self.processed_folder = Path(processed_folder)
        self.archive_folder = Path(archive_folder)
        self.municipality_id = municipality_id
        
        self._ensure_folders()
    
    def _ensure_folders(self):
        """Create import folders if they don't exist"""
        self.incoming_folder.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.archive_folder.mkdir(parents=True, exist_ok=True)
    
    def get_pending_files(self) -> List[Dict[str, Any]]:
        """Get list of files waiting to be processed"""
        pending = []
        
        for file_path in self.incoming_folder.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in ['.csv', '.pdf']:
                    pending.append({
                        "filename": file_path.name,
                        "path": str(file_path),
                        "type": ext[1:],
                        "size_bytes": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "report_type": self._detect_report_type(file_path.name)
                    })
        
        return pending
    
    def _detect_report_type(self, filename: str) -> str:
        """Attempt to detect report type from filename"""
        filename_lower = filename.lower()
        
        type_keywords = {
            "general_ledger": ["gl", "general_ledger", "ledger", "journal"],
            "budget": ["budget", "appropriation"],
            "accounts_payable": ["ap", "payable", "vendor_payment", "invoice"],
            "accounts_receivable": ["ar", "receivable", "billing"],
            "payroll": ["payroll", "pay_", "wages", "salary"],
            "utility_billing": ["utility", "water", "sewer", "electric"],
            "fixed_assets": ["asset", "equipment", "vehicle", "property"],
            "chart_of_accounts": ["coa", "chart_of_account", "account_list"],
            "trial_balance": ["trial_balance", "tb_"],
            "cash_receipts": ["cash_receipt", "receipt"],
            "check_register": ["check_register", "check_", "disbursement"],
            "vendor_list": ["vendor_list", "vendors"],
            "employee_list": ["employee_list", "employees", "staff"]
        }
        
        for report_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return report_type
        
        return "unknown"
    
    def process_file(
        self,
        file_path: str,
        report_type: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        fiscal_period: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a single file and return parsed data
        
        Parameters:
        - file_path: Path to file to process
        - report_type: Type of report (auto-detected if not provided)
        - fiscal_year: Year the data belongs to
        - fiscal_period: Period (month/quarter) the data belongs to
        
        Returns:
        - success: Whether processing succeeded
        - result: Parsed data or error message
        """
        path = Path(file_path)
        
        if not path.exists():
            return False, {"error": f"File not found: {file_path}"}
        
        ext = path.suffix.lower()
        detected_type = report_type or self._detect_report_type(path.name)
        
        try:
            if ext == '.csv':
                data = self._process_csv(path, detected_type)
            elif ext == '.pdf':
                if not PDF_AVAILABLE:
                    return False, {"error": "PDF processing not available - install pdfplumber"}
                data = self._process_pdf(path, detected_type)
            else:
                return False, {"error": f"Unsupported file type: {ext}"}
            
            result = {
                "filename": path.name,
                "report_type": detected_type,
                "fiscal_year": fiscal_year or datetime.now().year,
                "fiscal_period": fiscal_period,
                "record_count": len(data) if isinstance(data, list) else 0,
                "processed_at": datetime.now().isoformat(),
                "municipality_id": self.municipality_id,
                "data": data
            }
            
            self._move_to_processed(path)
            
            return True, result
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return False, {"error": str(e)}
    
    def _process_csv(self, path: Path, report_type: str) -> List[Dict[str, Any]]:
        """Process CSV file and return structured data"""
        try:
            df = pd.read_csv(path)
            df = df.fillna('')
            df.columns = [self._clean_column_name(col) for col in df.columns]
            return df.to_dict('records')
        except Exception as e:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                return [
                    {self._clean_column_name(k): v for k, v in row.items()}
                    for row in reader
                ]
    
    def _process_pdf(self, path: Path, report_type: str) -> List[Dict[str, Any]]:
        """Process PDF file and extract data"""
        if not PDF_AVAILABLE:
            raise ImportError("pdfplumber required for PDF processing")
        
        import pdfplumber
        
        extracted_data = []
        
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        if len(table) > 1:
                            headers = [self._clean_column_name(str(h or '')) for h in table[0]]
                            for row in table[1:]:
                                if any(cell for cell in row):
                                    record = {
                                        headers[i]: str(cell or '') 
                                        for i, cell in enumerate(row) 
                                        if i < len(headers)
                                    }
                                    record['_source_page'] = page_num + 1
                                    extracted_data.append(record)
                else:
                    text = page.extract_text()
                    if text:
                        extracted_data.append({
                            "raw_text": text,
                            "_source_page": page_num + 1,
                            "_type": "text_extraction"
                        })
        
        return extracted_data
    
    def _clean_column_name(self, name: str) -> str:
        """Clean and standardize column names"""
        import re
        name = str(name).strip().lower()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '_', name)
        return name
    
    def _move_to_processed(self, path: Path):
        """Move processed file to processed folder with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{timestamp}_{path.name}"
        dest = self.processed_folder / new_name
        shutil.move(str(path), str(dest))
        logger.info(f"Moved processed file to {dest}")
    
    def process_all_pending(
        self,
        fiscal_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Process all pending files in incoming folder"""
        results = []
        
        for file_info in self.get_pending_files():
            success, result = self.process_file(
                file_info['path'],
                report_type=file_info.get('report_type'),
                fiscal_year=fiscal_year
            )
            results.append({
                "filename": file_info['filename'],
                "success": success,
                "result": result
            })
        
        return results
    
    def get_import_template(self, report_type: str) -> Dict[str, Any]:
        """Get expected column format for a report type"""
        templates = {
            "general_ledger": {
                "required_columns": ["date", "account_number", "description", "debit", "credit"],
                "optional_columns": ["fund", "department", "reference", "vendor", "check_number"],
                "sample_row": {
                    "date": "2024-01-15",
                    "account_number": "01-100-4100",
                    "description": "Property Tax Revenue",
                    "debit": "",
                    "credit": "15000.00",
                    "fund": "01",
                    "department": "100"
                }
            },
            "budget": {
                "required_columns": ["account_number", "account_description", "budget_amount"],
                "optional_columns": ["fund", "department", "fiscal_year", "revised_budget"],
                "sample_row": {
                    "account_number": "01-100-5100",
                    "account_description": "Salaries & Wages",
                    "budget_amount": "500000.00",
                    "fund": "01",
                    "department": "100"
                }
            },
            "payroll": {
                "required_columns": ["employee_id", "pay_date", "gross_pay"],
                "optional_columns": ["department", "position", "hours_worked", "deductions", "net_pay"],
                "sample_row": {
                    "employee_id": "EMP001",
                    "pay_date": "2024-01-15",
                    "gross_pay": "2500.00",
                    "department": "Police",
                    "position": "Officer"
                }
            }
        }
        
        return templates.get(report_type, {
            "required_columns": [],
            "optional_columns": [],
            "note": "Custom format - will attempt to auto-detect columns"
        })
    
    def health_check(self) -> Dict[str, Any]:
        """Check import service status"""
        return {
            "status": "active",
            "incoming_folder": str(self.incoming_folder),
            "pending_files": len(self.get_pending_files()),
            "pdf_support": PDF_AVAILABLE,
            "municipality": self.municipality_id,
            "timestamp": datetime.now().isoformat()
        }
