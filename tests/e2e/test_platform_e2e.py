"""
End-to-end Playwright tests for the GovSight platform.

Run against a live instance (Streamlit app plus, optionally, the PBB and
Budget Playground APIs):

    python3 -m streamlit run modules/core/main_app.py --server.port 5001 &
    GOVSIGHT_E2E_URL=http://127.0.0.1:5001 python3 -m pytest tests/e2e -q

Environment variables:
    GOVSIGHT_E2E_URL        base URL (default http://127.0.0.1:5001)
    GOVSIGHT_E2E_USER       login user (default admin_user)
    GOVSIGHT_E2E_PASSWORD   login password (default govsight123)
    GOVSIGHT_E2E_CHROMIUM   chromium executable path (optional)

Streamlit renders asynchronously, so assertions poll with generous
timeouts rather than assuming immediate paint.
"""

import os

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("GOVSIGHT_E2E_URL", "http://127.0.0.1:5001")
USERNAME = os.getenv("GOVSIGHT_E2E_USER", "admin_user")
PASSWORD = os.getenv("GOVSIGHT_E2E_PASSWORD", "govsight123")
CHROMIUM = os.getenv("GOVSIGHT_E2E_CHROMIUM") or None


def wait_for_gone(page, text, timeout_s=60, interval_ms=3000):
    waited = 0
    while waited < timeout_s * 1000:
        try:
            if text not in page.inner_text("body"):
                return True
        except Exception:
            pass
        page.wait_for_timeout(interval_ms)
        waited += interval_ms
    return False


def expand_sidebar(page):
    """Open Streamlit's collapsed sidebar if needed."""
    for sel in ("[data-testid='stExpandSidebarButton']",
                "[data-testid='stSidebarCollapsedControl'] button",
                "[data-testid='collapsedControl'] button",
                "[data-testid='stSidebarCollapseButton']"):
        loc = page.locator(sel)
        if loc.count():
            try:
                loc.first.click()
                page.wait_for_timeout(1500)
                return
            except Exception:
                continue


def wait_for_text(page, text, timeout_s=90, interval_ms=3000):
    """Poll the page body until `text` appears (Streamlit paints late)."""
    waited = 0
    while waited < timeout_s * 1000:
        try:
            if text in page.inner_text("body"):
                return True
        except Exception:
            pass
        page.wait_for_timeout(interval_ms)
        waited += interval_ms
    return False


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        kwargs = {}
        if CHROMIUM:
            kwargs["executable_path"] = CHROMIUM
        b = p.chromium.launch(**kwargs)
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    yield pg
    pg.close()


def login(page):
    page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(6000)
    if page.get_by_label("Username").count():
        page.get_by_label("Username").fill(USERNAME)
        page.get_by_label("Password", exact=True).fill(PASSWORD)
        page.get_by_role("button", name="Login").click()
    assert wait_for_text(page, "Choose Your Module"), "dashboard did not load"


class TestAuthentication:
    def test_wrong_password_rejected(self, page):
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(6000)
        if not page.get_by_label("Username").count():
            pytest.skip("already authenticated session state")
        page.get_by_label("Username").fill(USERNAME)
        page.get_by_label("Password", exact=True).fill("definitely-wrong")
        page.get_by_role("button", name="Login").click()
        page.wait_for_timeout(6000)
        assert "Choose Your Module" not in page.inner_text("body")

    def test_login_reaches_dashboard(self, page):
        login(page)
        body = page.inner_text("body")
        for module in ("GOVSIGHT NAVI", "GOVSIGHT MANTIS", "GOVSIGHT VATICA"):
            assert module in body, f"{module} card missing"


class TestAdminAccess:
    def test_admin_card_on_main_page(self, page):
        login(page)
        assert wait_for_text(page, "Administration", timeout_s=30), \
            "Admin card not on main page for admin user"
        assert page.get_by_role("button", name="Open Admin Settings").count()

    def test_admin_settings_open(self, page):
        login(page)
        page.get_by_role("button", name="Open Admin Settings").click()
        assert wait_for_gone(page, "Choose Your Module"), \
            "dashboard did not navigate away"
        assert wait_for_text(page, "Admin Control Panel", timeout_s=60), \
            "Admin Control Panel did not render"


class TestDemoDataProvisioning:
    def test_demo_data_caption_visible(self, page):
        login(page)
        assert wait_for_text(page, "Demo data ready", timeout_s=30), \
            "demo data provisioning caption missing for admin_user"
        body = page.inner_text("body")
        assert "GL accounts" in body and "transactions" in body


class TestNaviCashFlow:
    def test_cash_flow_uses_seasonal_demo_data(self, page):
        login(page)
        page.get_by_role("button", name="Enter Navi").click()
        assert wait_for_text(page, "Navigation & Planning Hub"), "Navi did not load"
        page.get_by_role("tab", name="Cash Flow").first.click()
        assert wait_for_text(page, "Lowest projected balance", timeout_s=60)
        body = page.inner_text("body")
        # Seasonal mode proves the demo monthly history is linked
        assert "historical monthly seasonality" in body
        assert "12-month term" in body


class TestVaticaMonthlyClose:
    def test_close_review_finds_planted_exceptions(self, page):
        login(page)
        page.get_by_role("button", name="Enter Vatica").click()
        assert wait_for_text(page, "Monthly Close", timeout_s=90), \
            "Vatica did not load"
        close_tab = page.get_by_role("tab", name="Monthly Close").first
        close_tab.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        close_tab.click(force=True)
        assert wait_for_text(page, "Monthly Close Assistant", timeout_s=60)
        # Demo close month is July 2026; the widget defaults match in-env.
        run_btn = page.get_by_role("button", name="Run close review").first
        run_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        run_btn.evaluate("el => el.click()")
        # The rerun resets st.tabs to the first tab, hiding the report panel;
        # re-select Monthly Close to reveal the rendered results
        page.wait_for_timeout(10000)
        reopen = page.get_by_role("tab", name="Monthly Close").first
        reopen.scroll_into_view_if_needed()
        reopen.click(force=True)
        assert wait_for_text(page, "Transactions reviewed", timeout_s=60)
        body = page.inner_text("body")
        assert "possible_duplicate" in body, "planted duplicate not surfaced"
        assert "threshold_hugging" in body, "planted threshold hugging not surfaced"


class TestLogout:
    def test_logout_returns_to_login(self, page):
        login(page)
        expand_sidebar(page)
        logout_btn = page.get_by_role("button", name="Logout").first
        logout_btn.evaluate("el => el.click()")
        page.wait_for_timeout(8000)
        assert page.get_by_label("Username").count(), "login form not shown after logout"
