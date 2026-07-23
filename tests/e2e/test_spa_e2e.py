"""
End-to-end Playwright tests for the GovSight SPA (the unified platform).

Run against a live platform instance:

    GOVSIGHT_INSECURE_COOKIES=1 python3 -m uvicorn modules.api.pbb_api:app --port 8000 &
    python3 -m pytest tests/e2e/test_spa_e2e.py -q

Environment variables:
    GOVSIGHT_SPA_URL        base URL (default http://127.0.0.1:8000)
    GOVSIGHT_E2E_USER       login user (default admin_user)
    GOVSIGHT_E2E_PASSWORD   login password (default govsight123)
    GOVSIGHT_E2E_CHROMIUM   chromium executable path (optional)

The SPA paints fast, but data views fetch the bundle and some defer to
platform engines, so assertions poll the body text.
"""

import os

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("GOVSIGHT_SPA_URL", "http://127.0.0.1:8000")
USERNAME = os.getenv("GOVSIGHT_E2E_USER", "admin_user")
PASSWORD = os.getenv("GOVSIGHT_E2E_PASSWORD", "govsight123")
CHROMIUM = os.getenv("GOVSIGHT_E2E_CHROMIUM") or None


def wait_text(page, needle, timeout_ms=20000):
    """Poll the body until `needle` appears (case-insensitive)."""
    try:
        page.wait_for_function(
            "n => document.body.innerText.toLowerCase().includes(n.toLowerCase())",
            arg=needle, timeout=timeout_ms)
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        kwargs = {"executable_path": CHROMIUM} if CHROMIUM else {}
        browser = p.chromium.launch(**kwargs)
        pg = browser.new_page(viewport={"width": 1400, "height": 950})
        try:
            pg.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=15000)
        except Exception:
            pytest.skip(f"platform not reachable at {BASE_URL}")
        pg.fill("input[name='username']", USERNAME)
        pg.fill("input[name='password']", PASSWORD)
        pg.click("button[type='submit']")
        assert wait_text(pg, "Select a module"), "login failed"
        yield pg
        browser.close()


def goto(page, route):
    page.goto(BASE_URL + "/#" + route, wait_until="domcontentloaded")


class TestShell:
    def test_dashboard_modules(self, page):
        goto(page, "/")
        for name in ("Navi", "Mantis", "Vatica"):
            assert wait_text(page, f"Enter {name}", 10000)

    def test_admin_card_for_admin(self, page):
        goto(page, "/")
        assert wait_text(page, "Open Admin Settings", 10000)


class TestNavi:
    def test_scenario_planner_first_tab(self, page):
        goto(page, "/navi/0")
        assert wait_text(page, "Scenario")

    def test_budget_ledger_and_forecast(self, page):
        goto(page, "/navi/1")
        assert wait_text(page, "Ledger & Scenarios")
        page.click("text=Revenue Forecast")
        assert wait_text(page, "forecast")

    def test_personnel_workbook_with_parity_cards(self, page):
        goto(page, "/navi/2")
        assert wait_text(page, "Position Workbook")
        assert wait_text(page, "Multi-Year Personnel Outlook")
        assert wait_text(page, "GL Personnel Budget Reconciliation")

    def test_treasury_cashflow_engine(self, page):
        goto(page, "/navi/3")
        assert wait_text(page, "Cash Flow")
        assert wait_text(page, "PLATFORM ENGINE"), \
            "cash flow should defer to the CashFlowEngine when live"
        page.click("text=Investment Optimizer")
        assert wait_text(page, "Investment")


class TestGrantFinder:
    """The Scenario Planner's grant search: live federal results are the
    primary source; the built-in library is a labeled reference fallback."""

    LIVE_PAYLOAD = {
        "success": True, "query": "water", "count": 1, "is_live": True,
        "message": None,
        "grants": [{
            "id": "EPA-2026-004", "name": "Clean Water Infrastructure Notice FY26",
            "agency": "EPA", "description": "", "min_amount": 500000,
            "max_amount": 8000000, "amount": 8000000, "deadline": "2026-10-15",
            "source": "grants.gov",
            "url": "https://www.grants.gov/search-results-detail/999001"}],
    }

    def _open_search(self, page):
        goto(page, "/navi/0")
        assert wait_text(page, "Scenario")
        page.click("button:has-text('Revenue')")
        assert wait_text(page, "Grant Pipeline")
        page.fill("input[placeholder*='Search by keyword']", "water")
        page.click("button:has-text('Search'):not(:has-text('Grants.gov'))")

    def test_live_results_first_with_source_badges(self, page):
        import json
        page.route("**/api/grants/search*", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps(self.LIVE_PAYLOAD)))
        try:
            self._open_search(page)
            assert wait_text(page, "1 live federal opportunity")
            assert wait_text(page, "LIVE — grants.gov")
            assert wait_text(page, "Clean Water Infrastructure Notice FY26")
        finally:
            page.unroute("**/api/grants/search*")

    def test_degraded_search_is_labeled_reference(self, page):
        import json
        empty = {"success": True, "query": "water", "grants": [], "count": 0,
                 "is_live": False, "message": "Live grant search returned no results."}
        page.route("**/api/grants/search*", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(empty)))
        try:
            self._open_search(page)
            assert wait_text(page, "reference library")
            assert wait_text(page, "REFERENCE")
            assert wait_text(page, "Typical deadline")
        finally:
            page.unroute("**/api/grants/search*")


class TestMantis:
    def test_chat_page_and_status(self, page):
        goto(page, "/mantis/0")
        assert wait_text(page, "Mantis AI Assistant", 15000)

    def test_chat_degrades_without_ai_key(self, page):
        status = page.evaluate(
            "() => fetch('/api/mantis/status', {credentials: 'same-origin'})"
            ".then(r => r.json())")
        if status.get("ai_available"):
            pytest.skip("platform has an AI key configured; degraded path not applicable")
        goto(page, "/mantis/0")
        wait_text(page, "Mantis AI Assistant", 15000)
        page.fill("input[placeholder*='Ask a question']", "How are revenues?")
        page.click("button:has-text('Send')")
        assert wait_text(page, "AI not configured")

    def test_ledger_insights(self, page):
        goto(page, "/mantis/1")
        assert wait_text(page, "insight")


class TestVatica:
    def test_bi_sandbox(self, page):
        goto(page, "/vatica/0")
        assert wait_text(page, "chart")

    def test_historical_dynamic_years(self, page):
        goto(page, "/vatica/1")
        assert wait_text(page, "Revenue vs Expenditures by Fiscal Year")

    def test_dept_insights_pacing_engine(self, page):
        goto(page, "/vatica/2")
        assert wait_text(page, "PLATFORM ENGINE"), \
            "dept insights should use the platform pacing engine when live"

    def test_transactions(self, page):
        goto(page, "/vatica/3")
        assert wait_text(page, "transaction")

    def test_balance_sheet(self, page):
        goto(page, "/vatica/4")
        assert wait_text(page, "fund")

    def test_monthly_close_engine(self, page):
        goto(page, "/vatica/5")
        assert wait_text(page, "Monthly Close Review")
        page.click("#close-run")
        assert wait_text(page, "findings")


class TestSession:
    def test_logout_returns_to_login(self, page):
        goto(page, "/")
        page.click("button:has-text('Logout')")
        assert wait_text(page, "Sign In", 10000)
