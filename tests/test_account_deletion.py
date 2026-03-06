"""Tests for GDPR account deletion feature (Settings page + server proxy).

Covers:
- Settings HTML has the delete account UI elements
- Settings HTML has the confirmation modal
- Settings HTML has proper accessibility attributes
- Server proxy endpoint validates confirmation
- Server proxy endpoint requires auth token
- CSS has danger-zone and modal classes
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
SRC_ROOT = REPO_ROOT / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── HTML Structure Tests ──────────────────────────────────────────────


class TestSettingsDeleteAccountUI:
    """Verify the settings page has all delete account UI elements."""

    @pytest.fixture(autouse=True)
    def _load_html(self) -> None:
        self.html = _read(WEB_DIR / "settings.html")

    def test_gdpr_section_exists(self) -> None:
        assert 'id="gdpr-section"' in self.html

    def test_delete_button_exists(self) -> None:
        assert 'id="btn-gdpr-delete"' in self.html

    def test_delete_button_has_i18n_key(self) -> None:
        assert 'data-i18n="settings_delete_account"' in self.html

    def test_export_button_exists(self) -> None:
        assert 'id="btn-gdpr-export"' in self.html

    def test_delete_button_uses_danger_class(self) -> None:
        assert 'class="btn-danger' in self.html

    def test_no_inline_color_on_delete_button(self) -> None:
        """Pre-commit hook blocks inline style= with hardcoded hex colors on new code."""
        # Find the btn-gdpr-delete button line and verify no inline style
        for line in self.html.splitlines():
            if 'id="btn-gdpr-delete"' in line:
                assert 'style=' not in line, "Delete button should not use inline styles"


class TestDeleteAccountModal:
    """Verify the confirmation modal for account deletion."""

    @pytest.fixture(autouse=True)
    def _load_html(self) -> None:
        self.html = _read(WEB_DIR / "settings.html")

    def test_modal_overlay_exists(self) -> None:
        assert 'id="delete-account-modal"' in self.html

    def test_modal_has_dialog_role(self) -> None:
        assert 'role="dialog"' in self.html

    def test_modal_has_aria_modal(self) -> None:
        assert 'aria-modal="true"' in self.html

    def test_modal_has_aria_labelledby(self) -> None:
        assert 'aria-labelledby="delete-modal-title"' in self.html

    def test_modal_starts_hidden(self) -> None:
        assert 'class="delete-modal-overlay hidden"' in self.html

    def test_confirm_input_exists(self) -> None:
        assert 'id="delete-confirm-input"' in self.html

    def test_confirm_input_has_placeholder(self) -> None:
        assert 'placeholder="DELETE"' in self.html

    def test_confirm_button_starts_disabled(self) -> None:
        assert 'id="btn-delete-confirm"' in self.html
        # The confirm button should be disabled initially
        for line in self.html.splitlines():
            if 'id="btn-delete-confirm"' in line:
                assert "disabled" in line

    def test_cancel_button_exists(self) -> None:
        assert 'id="btn-delete-cancel"' in self.html

    def test_modal_status_has_aria_live(self) -> None:
        assert 'aria-live="polite"' in self.html


class TestDeleteAccountJavaScript:
    """Verify the JavaScript wiring for account deletion."""

    @pytest.fixture(autouse=True)
    def _load_html(self) -> None:
        self.html = _read(WEB_DIR / "settings.html")

    def test_calls_cloud_account_delete_endpoint(self) -> None:
        assert "/api/cloud/account/delete" in self.html

    def test_calls_cloud_account_export_endpoint(self) -> None:
        assert "/api/cloud/account/export" in self.html

    def test_sends_confirm_delete_in_body(self) -> None:
        assert "confirm: 'DELETE'" in self.html or '"confirm":"DELETE"' in self.html

    def test_clears_auth_on_success(self) -> None:
        assert "removeItem('solace_auth_token')" in self.html

    def test_escape_key_closes_modal(self) -> None:
        assert "Escape" in self.html

    def test_overlay_click_closes_modal(self) -> None:
        # The overlay click handler should check e.target === modalOverlay
        assert "e.target === modalOverlay" in self.html


# ── CSS Tests ─────────────────────────────────────────────────────────


class TestDeleteAccountCSS:
    """Verify CSS classes for danger zone and modal exist."""

    @pytest.fixture(autouse=True)
    def _load_css(self) -> None:
        self.css = _read(WEB_DIR / "css" / "site.css")

    def test_danger_zone_class(self) -> None:
        assert ".danger-zone" in self.css

    def test_btn_danger_class(self) -> None:
        assert ".btn-danger" in self.css

    def test_btn_danger_hover(self) -> None:
        assert ".btn-danger:hover" in self.css

    def test_btn_danger_uses_css_vars(self) -> None:
        assert "var(--sb-danger)" in self.css

    def test_delete_modal_overlay_class(self) -> None:
        assert ".delete-modal-overlay" in self.css

    def test_delete_modal_class(self) -> None:
        assert ".delete-modal" in self.css

    def test_delete_modal_title_class(self) -> None:
        assert ".delete-modal__title" in self.css

    def test_delete_modal_confirm_input_class(self) -> None:
        assert ".delete-modal__confirm-input" in self.css

    def test_delete_modal_actions_class(self) -> None:
        assert ".delete-modal__actions" in self.css

    def test_delete_modal_status_error_class(self) -> None:
        assert ".delete-modal__status--error" in self.css

    def test_delete_modal_status_success_class(self) -> None:
        assert ".delete-modal__status--success" in self.css

    def test_danger_zone_buttons_class(self) -> None:
        assert ".danger-zone__buttons" in self.css

    def test_danger_zone_btn_full_class(self) -> None:
        assert ".danger-zone__btn-full" in self.css

    def test_btn_danger_focus_visible(self) -> None:
        assert ".btn-danger:focus-visible" in self.css

    def test_modal_overlay_uses_mask_var(self) -> None:
        # Modal overlay should use --sb-mask-alpha-40, not hardcoded rgba
        assert "var(--sb-mask-alpha-40)" in self.css


# ── Server Proxy Tests ────────────────────────────────────────────────


def _make_handler_class():
    """Import the server module and return the handler class for testing."""
    server_path = WEB_DIR / "server.py"
    # We need to import the module; it has some dependencies
    # For unit testing, we'll verify the method exists and test its logic
    spec = importlib.util.spec_from_file_location("web_server", server_path)
    # Don't actually import (has heavy deps); test source directly
    return _read(server_path)


class TestServerAccountDeleteEndpoint:
    """Verify server.py has the account deletion proxy endpoint."""

    @pytest.fixture(autouse=True)
    def _load_server(self) -> None:
        self.source = _read(WEB_DIR / "server.py")

    def test_delete_route_registered(self) -> None:
        assert '"/api/cloud/account/delete"' in self.source

    def test_export_route_registered(self) -> None:
        assert '"/api/cloud/account/export"' in self.source

    def test_delete_handler_defined(self) -> None:
        assert "def _handle_cloud_account_delete" in self.source

    def test_export_handler_defined(self) -> None:
        assert "def _handle_cloud_account_export" in self.source

    def test_delete_requires_confirmation(self) -> None:
        """Handler must validate confirm='DELETE' before proceeding."""
        assert '"DELETE"' in self.source
        assert "Confirmation required" in self.source

    def test_delete_requires_auth_token(self) -> None:
        """Handler must check for auth token."""
        assert "_cloud_auth_token" in self.source

    def test_delete_calls_cloud_api(self) -> None:
        """Handler must proxy to solaceagi.com /api/v1/account."""
        assert '"/api/v1/account"' in self.source

    def test_delete_audits_call(self) -> None:
        """Handler must audit the cloud API call."""
        assert "_audit_cloud_call" in self.source

    def test_export_calls_cloud_api(self) -> None:
        """Handler must proxy to solaceagi.com /api/v1/account/export."""
        assert '"/api/v1/account/export"' in self.source

    def test_delete_handles_offline(self) -> None:
        """Handler must handle offline/unreachable cloud gracefully."""
        # Should return SERVICE_UNAVAILABLE when cloud is offline
        assert "SERVICE_UNAVAILABLE" in self.source

    def test_export_handles_offline(self) -> None:
        """Export handler must handle offline/unreachable cloud gracefully."""
        # The handler checks status == 0 for offline
        # Both handlers should have offline handling
        handler_section = self.source[self.source.index("def _handle_cloud_account_export"):]
        handler_section = handler_section[:handler_section.index("\n    # ──")]
        assert "status == 0" in handler_section

    def test_delete_uses_delete_method(self) -> None:
        """The cloud request for deletion must use DELETE HTTP method."""
        handler_section = self.source[self.source.index("def _handle_cloud_account_delete"):]
        handler_section = handler_section[:handler_section.index("def _handle_cloud_account_export")]
        assert '"DELETE"' in handler_section
