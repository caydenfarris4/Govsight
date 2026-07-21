"""
Unified Data Adapter
Single entry point for all data access across GovSight modules

Automatically selects data source based on municipality configuration:
1. Caselle API (primary for Caselle municipalities)
2. File Import (for non-Caselle municipalities)
3. Report Archive (for historical data queries)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date

from modules.data_adapter.config import (
    DataSourceType,
    get_municipality_config,
    load_config
)
from modules.data_adapter.caselle_client import CaselleAPIClient
from modules.data_adapter.file_importer import FileImportService
from modules.data_adapter.report_archive import ReportArchive

logger = logging.getLogger(__name__)

class UnifiedDataAdapter:
    """
    Unified interface for all data access in GovSight
    
    This adapter abstracts the data source, allowing modules to fetch data
    without knowing whether it comes from Caselle API, file imports, or archive.
    
    Usage:
        adapter = UnifiedDataAdapter(municipality_id="spanish_fork")
        
        gl_data = adapter.get_general_ledger(fiscal_year=2024)
        budget = adapter.get_budget_data(fiscal_year=2024)
        payroll = adapter.get_payroll_data(fiscal_year=2024)
    """
    
    _instances: Dict[str, 'UnifiedDataAdapter'] = {}
    
    def __new__(cls, municipality_id: str = "default"):
        if municipality_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[municipality_id] = instance
        return cls._instances[municipality_id]
    
    def __init__(self, municipality_id: str = "default"):
        if hasattr(self, '_initialized'):
            return
        
        self.municipality_id = municipality_id
        self.config = get_municipality_config(municipality_id)
        
        caselle_config = self.config.get('caselle_api', {})
        self.caselle_client = CaselleAPIClient(
            base_url=caselle_config.get('base_url', ''),
            client_id=caselle_config.get('client_id', ''),
            municipality_id=municipality_id
        )
        
        file_config = self.config.get('file_import', {})
        self.file_importer = FileImportService(
            incoming_folder=file_config.get('incoming_folder', 'imports/incoming'),
            processed_folder=file_config.get('processed_folder', 'imports/processed'),
            archive_folder=file_config.get('archive_folder', 'imports/archive'),
            municipality_id=municipality_id
        )
        
        archive_config = self.config.get('report_archive', {})
        self.archive = ReportArchive(
            database_path=archive_config.get('database_path', 'databases/report_archive.db'),
            municipality_id=municipality_id
        )
        
        self._initialized = True
        logger.info(f"UnifiedDataAdapter initialized for municipality: {municipality_id}")
    
    @property
    def source_type(self) -> DataSourceType:
        """Get current data source type"""
        source = self.config.get('source_type', DataSourceType.FILE_IMPORT.value)
        return DataSourceType(source)
    
    def _use_caselle(self) -> bool:
        """Check if Caselle API should be used"""
        return (
            self.source_type == DataSourceType.CASELLE_API and 
            self.caselle_client.is_configured
        )
    
    def get_general_ledger(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        fiscal_year: Optional[int] = None,
        fund: Optional[str] = None,
        department: Optional[str] = None,
        account: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch General Ledger data
        
        First attempts Caselle API if configured, otherwise uses archive.
        """
        if self._use_caselle():
            data = self.caselle_client.get_general_ledger(
                start_date=start_date,
                end_date=end_date,
                fund=fund,
                department=department,
                account=account
            )
            if data:
                return data
        
        return self.archive.get_general_ledger(
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            fiscal_year=fiscal_year,
            fund=fund,
            department=department,
            account=account
        )
    
    def get_budget_data(
        self,
        fiscal_year: int,
        fund: Optional[str] = None,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch budget data"""
        if self._use_caselle():
            data = self.caselle_client.get_budget_data(
                fiscal_year=fiscal_year,
                fund=fund,
                department=department
            )
            if data:
                return data
        
        return self.archive.get_budget_data(
            fiscal_year=fiscal_year,
            fund=fund,
            department=department
        )
    
    def get_payroll_data(
        self,
        fiscal_year: Optional[int] = None,
        pay_period_start: Optional[date] = None,
        pay_period_end: Optional[date] = None,
        department: Optional[str] = None,
        employee_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch payroll data"""
        if self._use_caselle():
            data = self.caselle_client.get_payroll_data(
                pay_period_start=pay_period_start,
                pay_period_end=pay_period_end,
                department=department,
                employee_id=employee_id
            )
            if data:
                return data
        
        return self.archive.get_payroll_data(
            fiscal_year=fiscal_year,
            department=department,
            employee_id=employee_id
        )
    
    def get_accounts_payable(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        vendor: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch Accounts Payable data"""
        if self._use_caselle():
            return self.caselle_client.get_accounts_payable(
                start_date=start_date,
                end_date=end_date,
                vendor=vendor,
                status=status
            )
        return []
    
    def get_accounts_receivable(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        customer: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch Accounts Receivable data"""
        if self._use_caselle():
            return self.caselle_client.get_accounts_receivable(
                start_date=start_date,
                end_date=end_date,
                customer=customer
            )
        return []
    
    def get_utility_billing(
        self,
        billing_period: Optional[str] = None,
        service_type: Optional[str] = None,
        account_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch utility billing data"""
        if self._use_caselle():
            return self.caselle_client.get_utility_billing(
                billing_period=billing_period,
                service_type=service_type,
                account_number=account_number
            )
        return []
    
    def get_fixed_assets(
        self,
        asset_type: Optional[str] = None,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch fixed assets data"""
        if self._use_caselle():
            return self.caselle_client.get_fixed_assets(
                asset_type=asset_type,
                department=department
            )
        return []
    
    def get_chart_of_accounts(self) -> List[Dict[str, Any]]:
        """Fetch chart of accounts"""
        if self._use_caselle():
            return self.caselle_client.get_chart_of_accounts()
        return []
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """Fetch department list"""
        if self._use_caselle():
            return self.caselle_client.get_departments()
        return []
    
    def get_funds(self) -> List[Dict[str, Any]]:
        """Fetch fund list"""
        if self._use_caselle():
            return self.caselle_client.get_funds()
        return []
    
    def get_vendors(self) -> List[Dict[str, Any]]:
        """Fetch vendor list"""
        if self._use_caselle():
            return self.caselle_client.get_vendors()
        return []
    
    def get_employees(
        self,
        department: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Fetch employee list"""
        if self._use_caselle():
            return self.caselle_client.get_employees(
                department=department,
                active_only=active_only
            )
        return []
    
    def get_available_years(self) -> List[int]:
        """Get list of years with data available"""
        return self.archive.get_available_years()
    
    def import_file(
        self,
        file_path: str,
        report_type: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        fiscal_period: Optional[str] = None,
        auto_archive: bool = True
    ) -> Dict[str, Any]:
        """
        Import a file and optionally archive it
        
        Parameters:
        - file_path: Path to CSV or PDF file
        - report_type: Type of report (auto-detected if not provided)
        - fiscal_year: Year the data belongs to
        - fiscal_period: Period (month/quarter)
        - auto_archive: Whether to automatically archive the imported data
        
        Returns import result with status and record count
        """
        success, result = self.file_importer.process_file(
            file_path=file_path,
            report_type=report_type,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period
        )
        
        if success and auto_archive:
            session_id = self.archive.archive_import(result)
            result['archive_session_id'] = session_id
            result['archived'] = True
        
        return {
            "success": success,
            "result": result
        }
    
    def process_pending_imports(
        self,
        fiscal_year: Optional[int] = None,
        auto_archive: bool = True
    ) -> List[Dict[str, Any]]:
        """Process all pending files in import folder"""
        results = []
        
        for file_info in self.file_importer.get_pending_files():
            import_result = self.import_file(
                file_path=file_info['path'],
                report_type=file_info.get('report_type'),
                fiscal_year=fiscal_year,
                auto_archive=auto_archive
            )
            results.append(import_result)
        
        return results
    
    def get_pending_imports(self) -> List[Dict[str, Any]]:
        """Get list of files waiting to be imported"""
        return self.file_importer.get_pending_files()
    
    def get_import_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent import history"""
        return self.archive.get_import_history(limit)
    
    def get_import_template(self, report_type: str) -> Dict[str, Any]:
        """Get expected format for a report type"""
        return self.file_importer.get_import_template(report_type)
    
    def health_check(self) -> Dict[str, Any]:
        """Check all data adapter components"""
        return {
            "municipality": self.municipality_id,
            "source_type": self.source_type.value,
            "caselle_api": self.caselle_client.health_check(),
            "file_importer": self.file_importer.health_check(),
            "archive": self.archive.health_check(),
            "timestamp": datetime.now().isoformat()
        }


def get_adapter(municipality_id: str = "default") -> UnifiedDataAdapter:
    """Get or create UnifiedDataAdapter instance for a municipality"""
    return UnifiedDataAdapter(municipality_id)


def refresh_adapter(municipality_id: str = "default") -> UnifiedDataAdapter:
    """Force refresh of adapter configuration"""
    if municipality_id in UnifiedDataAdapter._instances:
        del UnifiedDataAdapter._instances[municipality_id]
    return UnifiedDataAdapter(municipality_id)
