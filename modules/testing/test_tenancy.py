"""Unit tests for multi-tenancy: directory, isolation paths, and ACLs."""

import os

import pytest

from modules.tenancy.acl import allowed_departments, filter_bundle, filter_pacing_rows
from modules.tenancy.context import DEFAULT_TENANT, tenant_db_path, valid_tenant_id
from modules.tenancy.directory import TenantDirectory


@pytest.fixture
def directory(tmp_path):
    return TenantDirectory(db_path=str(tmp_path / "directory.db"))


class TestDirectory:
    def test_bootstrap_creates_default_tenant(self, directory):
        assert directory.get_tenant(DEFAULT_TENANT) is not None

    def test_create_and_authenticate_user(self, directory):
        directory.create_user("alice", "s3cret-pass", DEFAULT_TENANT,
                              role="editor", departments=["Police"])
        user = directory.authenticate("alice", "s3cret-pass")
        assert user["tenant_id"] == DEFAULT_TENANT
        assert user["role"] == "editor"
        assert user["departments"] == ["Police"]
        assert directory.authenticate("alice", "wrong-password") is None

    def test_password_rules(self, directory):
        with pytest.raises(ValueError):
            directory.create_user("bob", "short", DEFAULT_TENANT)
        with pytest.raises(ValueError):
            directory.create_user("has|pipe", "long-enough", DEFAULT_TENANT)

    def test_duplicate_username_rejected(self, directory):
        directory.create_user("carol", "password1", DEFAULT_TENANT)
        with pytest.raises(ValueError):
            directory.create_user("carol", "password2", DEFAULT_TENANT)

    def test_update_scoped_to_tenant(self, directory):
        directory.create_tenant("provo", "Provo", "UT",
                                admin_username="provo-admin",
                                admin_password="provo-pass-1")
        directory.create_user("dave", "password1", DEFAULT_TENANT)
        # A Provo admin cannot touch a Spanish Fork user
        with pytest.raises(ValueError):
            directory.update_user("dave", "provo", role="admin")
        updated = directory.update_user("dave", DEFAULT_TENANT,
                                        departments=["Fire", "Police"])
        assert updated["departments"] == ["Fire", "Police"]

    def test_deactivated_user_cannot_login(self, directory):
        directory.create_user("eve", "password1", DEFAULT_TENANT)
        directory.update_user("eve", DEFAULT_TENANT, active=False)
        assert directory.authenticate("eve", "password1") is None

    def test_password_change_rehashes(self, directory):
        directory.create_user("frank", "password1", DEFAULT_TENANT)
        directory.update_user("frank", DEFAULT_TENANT, password="password2")
        assert directory.authenticate("frank", "password1") is None
        assert directory.authenticate("frank", "password2") is not None

    def test_tenant_admin_created_with_tenant(self, directory):
        directory.create_tenant("lehi", "Lehi", "UT",
                                admin_username="lehi-admin",
                                admin_password="lehi-pass-1")
        admin = directory.get_user("lehi-admin")
        assert admin["tenant_id"] == "lehi"
        assert admin["role"] == "admin"
        assert admin["departments"] == "*"


class TestTenantPaths:
    def test_default_tenant_uses_legacy_layout(self):
        assert tenant_db_path("core/x.db", DEFAULT_TENANT) == \
            os.path.join("databases", "core", "x.db")

    def test_other_tenant_gets_own_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = tenant_db_path("core/x.db", "provo")
        assert path == os.path.join("databases", "tenants", "provo", "core", "x.db")

    def test_invalid_ids_rejected(self):
        for bad in ("", "UPPER", "has space", "../escape", "a" * 80):
            assert not valid_tenant_id(bad)
        with pytest.raises(ValueError):
            tenant_db_path("x.db", "../escape")

    def test_traversal_in_rel_path_rejected(self):
        with pytest.raises(ValueError):
            tenant_db_path("../directory.db", DEFAULT_TENANT)


class TestDepartmentACL:
    BUNDLE = {
        "accounts": [
            {"account_number": "10-20-5100", "department": "Police", "account_type": "Expense"},
            {"account_number": "10-35-5100", "department": "Parks", "account_type": "Expense"},
        ],
        "monthly_actuals": [
            {"account_number": "10-20-5100", "actual": 5},
            {"account_number": "10-35-5100", "actual": 7},
        ],
        "transactions": [
            {"id": "t1", "department": "Police"},
            {"id": "t2", "department": "Parks"},
        ],
        "positions": [{"position_id": "p1", "department": "Parks"}],
        "departments": ["Police", "Parks"],
        "balance_sheet": [{"account": "10-1010", "amount": 1}],
        "meta": {"organization": "Testville"},
    }

    def test_unrestricted_passthrough(self):
        user = {"departments": "*"}
        assert allowed_departments(user) is None
        assert filter_bundle(self.BUNDLE, None) is self.BUNDLE

    def test_restricted_bundle(self):
        allowed = allowed_departments({"departments": ["Police"]})
        out = filter_bundle(self.BUNDLE, allowed)
        assert [a["department"] for a in out["accounts"]] == ["Police"]
        assert [m["account_number"] for m in out["monthly_actuals"]] == ["10-20-5100"]
        assert [t["id"] for t in out["transactions"]] == ["t1"]
        assert out["positions"] == []
        assert out["departments"] == ["Police"]
        # fund-level data stays; scope is recorded
        assert out["balance_sheet"] == self.BUNDLE["balance_sheet"]
        assert out["meta"]["department_scope"] == ["Police"]
        # original untouched
        assert len(self.BUNDLE["accounts"]) == 2

    def test_pacing_rows_filtered(self):
        rows = [{"Department": "Police"}, {"Department": "Parks"}]
        assert filter_pacing_rows(rows, {"Parks"}) == [{"Department": "Parks"}]
        assert filter_pacing_rows(rows, None) == rows
