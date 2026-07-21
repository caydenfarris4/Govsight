"""
GovSight Unified Data Adapter
Abstracts data sources: Caselle API, File Import, or Legacy Database
"""

from modules.data_adapter.unified_adapter import UnifiedDataAdapter, get_adapter, refresh_adapter
from modules.data_adapter.caselle_client import CaselleAPIClient
from modules.data_adapter.file_importer import FileImportService
from modules.data_adapter.report_archive import ReportArchive

__all__ = [
    'UnifiedDataAdapter',
    'get_adapter',
    'refresh_adapter',
    'CaselleAPIClient', 
    'FileImportService',
    'ReportArchive'
]
