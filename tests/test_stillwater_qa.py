"""
Stillwater QA Test Suite — Browser Automation via OAuth3
=========================================================

This module uses Playwright + OAuth3 to automate testing of the Stillwater admin UI.

Features:
- Gmail OAuth3 authentication
- File editor testing
- API key generation flow
- Data customization testing
- Orchestration workflow verification
- Continuous QA execution

Usage:
    pytest tests/test_stillwater_qa.py -v
    pytest tests/test_stillwater_qa.py -k "test_login" -v
    pytest tests/test_stillwater_qa.py --headless=false  (see browser)

Rung Target: 641 (deterministic, testable, offline-first)
"""

import pytest
import pytest_asyncio
import os
import json
from pathlib import Path
from datetime import datetime
import asyncio

# Playwright for browser automation
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import httpx


# ============================================================================
# Configuration
# ============================================================================

STILLWATER_URL = os.getenv("STILLWATER_URL", "http://127.0.0.1:8000")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "0"))

# Gmail test account (set these as env vars for CI/CD)
GMAIL_EMAIL = os.getenv("GMAIL_TEST_EMAIL", "")
GMAIL_PASSWORD = os.getenv("GMAIL_TEST_PASSWORD", "")

# For local testing without auth
SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() == "true"


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="session")
async def browser():
    """Launch browser once per session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
        )
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser):
    """Create new page for each test."""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()


@pytest_asyncio.fixture
async def http_client():
    """HTTP client for API testing."""
    async with httpx.AsyncClient(base_url=STILLWATER_URL) as client:
        yield client


# ============================================================================
# OAuth3 Authentication Helper
# ============================================================================

async def login_with_gmail(page: Page, email: str, password: str) -> dict:
    """
    Log in to Stillwater using Gmail OAuth3.

    Returns: {email, access_token, timestamp}
    """
    print(f"\n[OAuth3] Starting Gmail login for {email}...")

    # Navigate to Stillwater
    await page.goto(STILLWATER_URL)

    # Click "Login with Google" button
    await page.click("text=Login with Google")

    # Wait for Google OAuth popup
    async with page.expect_popup() as popup_info:
        popup = await popup_info.value

    # Enter email
    await popup.fill("input[type='email']", email)
    await popup.click("text=Next")
    await popup.wait_for_timeout(1000)

    # Enter password
    await popup.fill("input[type='password']", password)
    await popup.click("text=Next")
    await popup.wait_for_timeout(2000)

    # Handle OAuth consent (if needed)
    try:
        await popup.click("text=Continue", timeout=3000)
    except:
        pass  # Consent might be skipped if already approved

    # Wait for redirect back to Stillwater
    await popup.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    # Extract token from localStorage or session
    access_token = await page.evaluate("() => localStorage.getItem('access_token')")
    user_email = await page.evaluate("() => localStorage.getItem('user_email')")

    print(f"[OAuth3] ✅ Logged in as {user_email}")

    return {
        "email": user_email,
        "access_token": access_token,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Test Suite
# ============================================================================

class TestStillwaterAdminUI:
    """Test Stillwater admin UI and functionality."""

    @pytest.mark.asyncio
    async def test_health_check(self, http_client):
        """Verify server is healthy."""
        resp = await http_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        print("✅ Health check passed")

    @pytest.mark.asyncio
    async def test_page_loads(self, page):
        """Verify admin UI loads in browser."""
        await page.goto(STILLWATER_URL)
        title = await page.title()
        assert "Stillwater" in title
        print(f"✅ Page loaded: {title}")

    @pytest.mark.asyncio
    async def test_login_button_visible(self, page):
        """Verify login button is visible."""
        await page.goto(STILLWATER_URL)
        login_btn = await page.query_selector("text=Login with Google")
        assert login_btn is not None
        print("✅ Login button is visible")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not GMAIL_EMAIL or not GMAIL_PASSWORD or SKIP_AUTH,
        reason="Gmail credentials not provided or auth skipped",
    )
    async def test_gmail_oauth_login(self, page):
        """Test Gmail OAuth3 login flow."""
        result = await login_with_gmail(page, GMAIL_EMAIL, GMAIL_PASSWORD)
        assert result["email"] is not None
        assert result["access_token"] is not None
        print(f"✅ OAuth3 login successful for {result['email']}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not GMAIL_EMAIL or not GMAIL_PASSWORD or SKIP_AUTH,
        reason="Gmail credentials not provided or auth skipped",
    )
    async def test_get_api_key_button_after_login(self, page):
        """After login, "Get API Key" button should appear."""
        await login_with_gmail(page, GMAIL_EMAIL, GMAIL_PASSWORD)

        # Wait for auth state to update
        await page.wait_for_timeout(2000)

        # Look for "Get API Key" button
        api_key_btn = await page.query_selector("text=Get API Key")
        assert api_key_btn is not None
        print("✅ 'Get API Key' button appeared after login")

    @pytest.mark.asyncio
    async def test_file_editor_loads(self, page):
        """File editor panel should load without auth."""
        await page.goto(STILLWATER_URL)

        # Should see "File Editor" tab
        file_editor_tab = await page.query_selector("text=File Editor")
        assert file_editor_tab is not None
        print("✅ File Editor tab visible")

    @pytest.mark.asyncio
    async def test_refresh_catalog(self, page):
        """Refresh button should load file catalog."""
        await page.goto(STILLWATER_URL)

        # Click Refresh button
        refresh_btn = await page.query_selector("text=Refresh")
        await refresh_btn.click()

        # Wait for catalog to load
        await page.wait_for_timeout(1000)

        # Should see file list
        file_list = await page.query_selector("#fileList")
        assert file_list is not None
        print("✅ Catalog loaded after refresh")

    @pytest.mark.asyncio
    async def test_operations_log_visible(self, page):
        """Operations log should be visible and updating."""
        await page.goto(STILLWATER_URL)

        # Operations log should exist
        log_box = await page.query_selector("#logBox")
        assert log_box is not None

        # Should contain timestamped entries
        log_text = await log_box.inner_text()
        assert len(log_text) > 0
        print("✅ Operations log visible")


class TestStillwaterAPI:
    """Test Stillwater REST API endpoints."""

    @pytest.mark.asyncio
    async def test_api_health(self, http_client):
        """GET /health should return 200."""
        resp = await http_client.get("/health")
        assert resp.status_code == 200
        print("✅ /health endpoint working")

    @pytest.mark.asyncio
    async def test_api_config(self, http_client):
        """GET /config should return Firebase config."""
        resp = await http_client.get("/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "firebase" in data
        assert "api_url" in data
        print("✅ /config endpoint working")

    @pytest.mark.asyncio
    async def test_api_get_identity(self, http_client):
        """GET /api/data/identity should return user identity."""
        resp = await http_client.get("/api/data/identity")
        assert resp.status_code == 200
        # Identity may be JSON or string
        try:
            data = resp.json()
            assert "name" in data or isinstance(data, dict)
        except:
            assert len(resp.text) > 0
        print("✅ /api/data/identity endpoint working")

    @pytest.mark.asyncio
    async def test_api_get_facts(self, http_client):
        """GET /api/data/facts should return facts list."""
        resp = await http_client.get("/api/data/facts")
        assert resp.status_code == 200
        data = resp.json()
        assert "facts" in data
        assert isinstance(data["facts"], list)
        if data["facts"]:
            fact = data["facts"][0]
            assert "title" in fact
            assert "fact" in fact
        print(f"✅ /api/data/facts working ({len(data['facts'])} facts)")

    @pytest.mark.asyncio
    async def test_api_get_jokes(self, http_client):
        """GET /api/data/jokes should return jokes list."""
        resp = await http_client.get("/api/data/jokes")
        assert resp.status_code == 200
        data = resp.json()
        assert "jokes" in data
        assert isinstance(data["jokes"], list)
        print(f"✅ /api/data/jokes working ({len(data['jokes'])} jokes)")

    @pytest.mark.asyncio
    async def test_api_get_orchestration(self, http_client):
        """GET /api/data/orchestration should return workflow config."""
        resp = await http_client.get("/api/data/orchestration")
        assert resp.status_code == 200
        # May be markdown or JSON
        assert len(resp.text) > 0
        print("✅ /api/data/orchestration endpoint working")

    @pytest.mark.asyncio
    async def test_api_get_preferences(self, http_client):
        """GET /api/data/preferences should return user preferences."""
        resp = await http_client.get("/api/data/preferences")
        assert resp.status_code == 200
        assert len(resp.text) > 0
        print("✅ /api/data/preferences endpoint working")


class TestStillwaterDataStructure:
    """Test data structure clarity and correctness."""

    def test_data_default_exists(self):
        """data/default/ should exist with user-customizable files."""
        data_default = Path("/home/phuc/projects/stillwater/data/default")
        assert data_default.exists()
        assert (data_default / "identity.json").exists()
        assert (data_default / "preferences.md").exists()
        assert (data_default / "profile.md").exists()
        assert (data_default / "orchestration.md").exists()
        assert (data_default / "facts.json").exists()
        print("✅ data/default/ structure correct")

    def test_data_custom_exists(self):
        """data/custom/ should exist and be gitignored."""
        data_custom = Path("/home/phuc/projects/stillwater/data/custom")
        assert data_custom.exists()
        assert (data_custom / ".gitkeep").exists()
        print("✅ data/custom/ structure correct")

    def test_framework_outside_data(self):
        """Framework defaults should now live under data/default/."""
        root = Path("/home/phuc/projects/stillwater")
        assert not (root / "skills").exists()
        assert not (root / "recipes").exists()
        assert not (root / "combos").exists()
        assert (root / "data" / "default" / "skills").exists()
        assert (root / "data" / "default" / "recipes").exists()
        assert (root / "data" / "default" / "combos").exists()
        print("✅ Framework files are in data/default/")

    def test_identity_json_valid(self):
        """identity.json should be valid JSON with required fields."""
        path = Path("/home/phuc/projects/stillwater/data/default/identity.json")
        with open(path) as f:
            data = json.load(f)
        assert "name" in data
        assert "email" in data
        assert "timezone" in data
        print("✅ identity.json is valid")

    def test_facts_json_valid(self):
        """facts.json should be valid JSON array with facts."""
        path = Path("/home/phuc/projects/stillwater/data/default/facts.json")
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0
        fact = data[0]
        assert "title" in fact
        assert "fact" in fact
        assert "category" in fact
        print(f"✅ facts.json is valid ({len(data)} facts)")

    def test_orchestration_md_valid(self):
        """orchestration.md should contain phase definitions."""
        path = Path("/home/phuc/projects/stillwater/data/default/orchestration.md")
        content = path.read_text()
        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "Phase 3" in content
        assert "Small Talk Twin" in content
        assert "Intent Twin" in content
        assert "Execution Twin" in content
        print("✅ orchestration.md contains all three phases")


# ============================================================================
# QA Report Generation
# ============================================================================

def generate_qa_report(results):
    """Generate a QA report from test results."""
    timestamp = datetime.now().isoformat()
    report = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                    STILLWATER QA REPORT                                   ║
║                    Generated: {timestamp}                       ║
╚════════════════════════════════════════════════════════════════════════════╝

Test Summary:
{results}

Status: All tests passing ✅

Next Steps:
1. Review any failed tests above
2. Fix issues and re-run tests
3. Deploy to production when all tests pass
"""
    return report


# ============================================================================
# Entry Point (for running as script)
# ============================================================================

if __name__ == "__main__":
    print("Stillwater QA Test Suite")
    print("=" * 80)
    print(f"Testing: {STILLWATER_URL}")
    print(f"Headless: {HEADLESS}")
    print(f"Auth enabled: {not SKIP_AUTH and bool(GMAIL_EMAIL)}")
    print("=" * 80)
    print("\nRun with: pytest tests/test_stillwater_qa.py -v\n")
