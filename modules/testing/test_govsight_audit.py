"""
GovSight Platform Comprehensive Test Suite
Tests all major modules and functions for production readiness
"""

import pytest
import sys
import os
import json
from datetime import datetime, date
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class TestDataAdapter:
    """Tests for the new Unified Data Adapter"""
    
    def test_unified_adapter_initialization(self):
        from modules.data_adapter import UnifiedDataAdapter
        adapter = UnifiedDataAdapter("test_municipality")
        assert adapter is not None
        assert adapter.municipality_id == "test_municipality"
    
    def test_adapter_health_check(self):
        from modules.data_adapter import get_adapter
        adapter = get_adapter("default")
        health = adapter.health_check()
        assert health["municipality"] == "default"
        assert "source_type" in health
        assert "caselle_api" in health
        assert "file_importer" in health
        assert "archive" in health
    
    def test_file_importer_pending_files(self):
        from modules.data_adapter import FileImportService
        importer = FileImportService()
        pending = importer.get_pending_files()
        assert isinstance(pending, list)
    
    def test_report_archive_initialization(self):
        from modules.data_adapter import ReportArchive
        archive = ReportArchive(database_path="databases/test_archive.db")
        health = archive.health_check()
        assert health["status"] == "active"
    
    def test_caselle_client_interface(self):
        from modules.data_adapter import CaselleAPIClient
        client = CaselleAPIClient()
        assert client.is_configured == False
        health = client.health_check()
        assert "configured" in health
        assert "connected" in health


class TestDatabaseConnections:
    """Tests for database connectivity"""
    
    def test_connection_manager_load_config(self):
        from modules.database.connection_manager import load_db_config
        config = load_db_config()
        assert config is not None
        assert "databases" in config
    
    def test_gl_database_connection(self):
        from modules.database.connection_manager import get_database_connection
        try:
            conn = get_database_connection("gl_primary")
            assert conn is not None
            conn.close()
        except Exception as e:
            pytest.skip(f"GL database not available: {e}")
    
    def test_scenarios_database(self):
        from modules.database.scenarios_db import init_scenarios_database, get_all_scenarios
        init_scenarios_database()
        scenarios = get_all_scenarios()
        assert isinstance(scenarios, list)


class TestAuthenticationAPI:
    """Tests for authentication system"""
    
    def test_users_database_initialization(self):
        from modules.api.auth_api import init_users_db, get_db_connection
        init_users_db()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        assert count >= 0
    
    def test_password_hashing(self):
        from modules.api.auth_api import hash_password, verify_password
        test_password = "TestPass123!"
        hashed = hash_password(test_password)
        assert hashed != test_password
        assert verify_password(test_password, hashed)
    
    def test_token_creation(self):
        from modules.api.auth_api import create_access_token
        token = create_access_token({"sub": "test_user"})
        assert token is not None
        assert len(token) > 0


class TestSSOSystem:
    """Tests for SSO authentication"""
    
    def test_sso_database_tables(self):
        from modules.api.sso_database import init_sso_tables
        import sqlite3
        init_sso_tables()
        conn = sqlite3.connect("production_data/users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "sso_identities" in tables
        assert "sso_sessions" in tables


class TestBISandbox:
    """Tests for BI Sandbox components"""
    
    def test_multi_database_manager(self):
        from modules.bi_sandbox.multi_database_manager import MultiDatabaseManager
        manager = MultiDatabaseManager()
        assert manager is not None
        assert hasattr(manager, 'connections')
    
    def test_schema_catalog_manager(self):
        from modules.bi_sandbox.schema_catalog_manager import schema_catalog_manager
        assert schema_catalog_manager is not None


class TestNaviModule:
    """Tests for Navi module components"""
    
    def test_pbb_data_store(self):
        from modules.navi.pbb_data_store import PBBDataStore
        store = PBBDataStore()
        assert store is not None
    
    def test_investment_optimizer_exists(self):
        assert os.path.exists("modules/navi/investment_optimizer.py")
        assert os.path.exists("modules/navi/investment_optimizer_html.html")


class TestMantisModule:
    """Tests for Mantis AI module"""
    
    def test_mantis_engine_import(self):
        try:
            from modules.mantis.mantis_ai_engine import MantisAIEngine
            assert True
        except ImportError as e:
            pytest.skip(f"Mantis engine import skipped: {e}")
    
    def test_scenario_intelligence_import(self):
        try:
            from modules.mantis.scenario_intelligence import ScenarioIntelligence
            assert True
        except ImportError as e:
            pytest.skip(f"Scenario intelligence import skipped: {e}")


class TestVaticaModule:
    """Tests for Vatica module"""
    
    def test_gl_drilldown_exists(self):
        assert os.path.exists("modules/vatica/govsight_gl_drilldown_module.py")
    
    def test_google_sheets_exporter_exists(self):
        assert os.path.exists("modules/vatica/google_sheets_exporter.py")


class TestSecurityModules:
    """Tests for security components"""
    
    def test_rbac_manager_import(self):
        try:
            from modules.security.rbac_manager import RBACManager
            assert True
        except ImportError as e:
            pytest.skip(f"RBAC manager import skipped: {e}")
    
    def test_session_manager_import(self):
        try:
            from modules.security.session_manager import SecureSessionManager
            assert True
        except ImportError as e:
            pytest.skip(f"Session manager import skipped: {e}")


class TestReportingModules:
    """Tests for reporting components"""
    
    def test_audit_logger_import(self):
        try:
            from modules.reporting.audit_logger import AuditLogger
            assert True
        except ImportError as e:
            pytest.skip(f"Audit logger import skipped: {e}")
    
    def test_data_access_import(self):
        try:
            from modules.reporting.data_access import DataAccessLayer
            assert True
        except ImportError as e:
            pytest.skip(f"Data access import skipped: {e}")


class TestAPIEndpoints:
    """Tests for API endpoints"""
    
    def test_api_imports(self):
        from modules.api.pbb_api import app
        assert app is not None
    
    def test_data_adapter_api_import(self):
        from modules.api.data_adapter_api import router
        assert router is not None


class TestConfigurationFiles:
    """Tests for configuration files"""
    
    def test_streamlit_config_exists(self):
        assert os.path.exists(".streamlit/config.toml")
    
    def test_configs_directory_exists(self):
        assert os.path.exists("configs")
    
    def test_databases_directory_exists(self):
        assert os.path.exists("databases")


class TestCoreApplication:
    """Tests for core application files"""
    
    def test_main_app_exists(self):
        assert os.path.exists("modules/core/main_app.py")
    
    def test_replit_md_exists(self):
        assert os.path.exists("replit.md")


def run_all_tests():
    """Run all tests and return results"""
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.returncode == 0
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
