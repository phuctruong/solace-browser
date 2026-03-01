"""YinyangSupportBridge — classifies user requests as local-fixable or must-escalate.

Handles local actions (edit config, toggle settings, show history, re-run) directly.
Escalates new app requests, bug reports, recipe changes, billing questions, and
feature requests by creating support tickets.

Anti-Clippy: Never auto-escalates. Always returns classification for user review.
Fallback Ban: No silent failures. Specific exceptions only. No broad catches.

Channel [7] — Context + Tools.  Rung: 65537.
DNA: support(classify, handle_local | create_ticket, check_status) → {action, result} → Anti-Clippy
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inbox_outbox import InboxOutboxManager

logger = logging.getLogger("solace-browser.yinyang.support_bridge")

# Default support ticket storage directory
_DEFAULT_SOLACE_HOME = Path("~/.solace").expanduser()

# Keywords that indicate a local action (CAN_FIX)
_LOCAL_KEYWORDS: dict[str, list[str]] = {
    "edit_config": [
        "edit config", "change config", "update config", "modify config",
        "edit settings", "change settings", "update settings", "modify settings",
        "edit my", "change my", "update my",
    ],
    "toggle_setting": [
        "toggle", "turn on", "turn off", "enable", "disable",
        "switch on", "switch off", "activate", "deactivate",
    ],
    "explain": [
        "explain", "how does", "how do", "what does", "what is",
        "tell me about", "help me understand", "show me how",
    ],
    "show_history": [
        "show history", "run history", "show runs", "list runs",
        "past runs", "previous runs", "show log", "show logs",
    ],
    "rerun": [
        "re-run", "rerun", "run again", "repeat", "redo",
        "execute again", "try again",
    ],
}

# Keywords that indicate escalation (MUST_ESCALATE)
_ESCALATE_KEYWORDS: dict[str, list[str]] = {
    "new_app": [
        "new app", "add app", "install app", "add a new app",
        "new integration", "add integration", "connect",
    ],
    "bug_report": [
        "bug", "broken", "error", "crash", "not working",
        "doesn't work", "failed", "issue", "problem",
    ],
    "recipe_change": [
        "change recipe", "update recipe", "modify recipe", "new recipe",
        "edit recipe", "recipe doesn't", "recipe broken",
    ],
    "billing": [
        "billing", "payment", "charge", "invoice", "subscription",
        "cancel", "refund", "upgrade", "downgrade", "pricing",
    ],
    "feature_request": [
        "feature request", "wish", "would be nice", "suggest",
        "can you add", "please add", "i want", "i need", "missing feature",
    ],
}

# Ticket statuses
VALID_TICKET_STATUSES = frozenset({"created", "open", "in_progress", "resolved", "closed"})


class TicketNotFoundError(Exception):
    """Raised when a ticket_id is not found."""


class InvalidActionError(Exception):
    """Raised when an invalid local action is requested."""


class YinyangSupportBridge:
    """Classifies user requests as CAN_FIX (local) or MUST_ESCALATE (ticket).

    CAN FIX locally:
    - Edit config.yaml (app settings)
    - Toggle settings
    - Explain how an app works
    - Show run history
    - Re-run a previous task

    MUST ESCALATE (creates support ticket):
    - New app requests
    - Bug reports
    - Recipe changes
    - Billing questions
    - Feature requests
    """

    def __init__(
        self,
        inbox_outbox: InboxOutboxManager,
        api_base_url: str = "https://solaceagi.com",
        solace_home: Path | None = None,
    ) -> None:
        self._inbox_outbox = inbox_outbox
        self._api_base_url = api_base_url.rstrip("/")
        self._solace_home = Path(solace_home) if solace_home is not None else _DEFAULT_SOLACE_HOME
        self._tickets_dir = self._solace_home / "support" / "tickets"

    def classify(self, user_message: str) -> dict[str, Any]:
        """Classify a user request as local or escalate.

        Returns:
            {
                action: "local" | "escalate",
                category: str,  # e.g., "edit_config", "bug_report"
                confidence: float,  # 0.0 to 1.0
            }
        """
        if not user_message or not user_message.strip():
            raise ValueError("user_message must not be empty")

        message_lower = user_message.strip().lower()

        # Check local keywords first (higher priority for direct commands)
        local_match = self._match_keywords(message_lower, _LOCAL_KEYWORDS)
        escalate_match = self._match_keywords(message_lower, _ESCALATE_KEYWORDS)

        if local_match is not None and escalate_match is not None:
            # Both matched — use the one with higher confidence (more keyword hits)
            local_category, local_confidence = local_match
            escalate_category, escalate_confidence = escalate_match
            if local_confidence >= escalate_confidence:
                return {
                    "action": "local",
                    "category": local_category,
                    "confidence": local_confidence,
                }
            return {
                "action": "escalate",
                "category": escalate_category,
                "confidence": escalate_confidence,
            }

        if local_match is not None:
            category, confidence = local_match
            return {
                "action": "local",
                "category": category,
                "confidence": confidence,
            }

        if escalate_match is not None:
            category, confidence = escalate_match
            return {
                "action": "escalate",
                "category": category,
                "confidence": confidence,
            }

        # No match — default to escalate with low confidence
        return {
            "action": "escalate",
            "category": "unknown",
            "confidence": 0.3,
        }

    def handle_local(self, app_id: str, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle a local action (edit config, toggle setting, show history, re-run).

        Args:
            app_id: The app to act on.
            action: One of "edit_config", "toggle_setting", "explain", "show_history", "rerun".
            params: Action-specific parameters.

        Returns:
            {success: bool, result: str}
        """
        valid_actions = frozenset({"edit_config", "toggle_setting", "explain", "show_history", "rerun"})
        if action not in valid_actions:
            raise InvalidActionError(
                f"Invalid action '{action}'. Must be one of: {', '.join(sorted(valid_actions))}"
            )

        if not app_id or not app_id.strip():
            raise ValueError("app_id must not be empty")

        if action == "edit_config":
            return self._handle_edit_config(app_id, params)
        elif action == "toggle_setting":
            return self._handle_toggle_setting(app_id, params)
        elif action == "explain":
            return self._handle_explain(app_id, params)
        elif action == "show_history":
            return self._handle_show_history(app_id)
        elif action == "rerun":
            return self._handle_rerun(app_id, params)

        # Unreachable due to validation above, but satisfies type checker
        raise InvalidActionError(f"Unhandled action: {action}")  # pragma: no cover

    def create_ticket(
        self,
        description: str,
        category: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a support ticket.

        Writes ticket to local file (offline-capable). In production,
        would POST to solaceagi.com API.

        Returns:
            {ticket_id: str, status: "created", url: str, created_at: str}
        """
        if not description or not description.strip():
            raise ValueError("description must not be empty")
        if not category or not category.strip():
            raise ValueError("category must not be empty")

        ticket_id = f"tkt-{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()

        ticket = {
            "ticket_id": ticket_id,
            "status": "created",
            "category": category.strip(),
            "description": description.strip(),
            "context": context,
            "created_at": created_at,
            "updated_at": created_at,
            "url": f"{self._api_base_url}/support/tickets/{ticket_id}",
        }

        # Write to local file
        self._tickets_dir.mkdir(parents=True, exist_ok=True)
        ticket_path = self._tickets_dir / f"{ticket_id}.json"
        ticket_path.write_text(
            json.dumps(ticket, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        logger.info("Created support ticket %s (category=%s)", ticket_id, category)

        return {
            "ticket_id": ticket_id,
            "status": "created",
            "url": ticket["url"],
            "created_at": created_at,
        }

    def check_ticket_status(self, ticket_id: str) -> dict[str, Any]:
        """Check ticket status from local storage.

        Returns:
            {ticket_id: str, status: str, updated_at: str}
        """
        if not ticket_id or not ticket_id.strip():
            raise ValueError("ticket_id must not be empty")

        ticket_path = self._tickets_dir / f"{ticket_id}.json"
        if not ticket_path.exists():
            raise TicketNotFoundError(f"Ticket not found: {ticket_id}")

        raw = json.loads(ticket_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TicketNotFoundError(f"Ticket data corrupt: {ticket_id}")

        return {
            "ticket_id": raw["ticket_id"],
            "status": raw["status"],
            "updated_at": raw["updated_at"],
        }

    # -----------------------------------------------------------------------
    # Private: local action handlers
    # -----------------------------------------------------------------------

    def _handle_edit_config(self, app_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """Edit an app's config settings.

        Reads the config file from ~/.solace/config/{app_id}.json, updates
        the specified key, and writes it back. Creates the file if it
        does not exist.
        """
        key = params.get("key", "")
        value = params.get("value", "")
        if not key:
            raise ValueError("params must include 'key' for edit_config action")

        try:
            self._inbox_outbox.read_manifest(app_id)
        except FileNotFoundError:
            return {
                "success": False,
                "result": f"App '{app_id}' not found or missing manifest.",
            }

        # Actually write the config change to ~/.solace/config/{app_id}.json
        config_dir = self._solace_home / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / f"{app_id}.json"

        if config_path.exists():
            config_data = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(config_data, dict):
                config_data = {}
        else:
            config_data = {}

        config_data[key] = value
        config_path.write_text(
            json.dumps(config_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return {
            "success": True,
            "result": f"Config '{key}' set to '{value}' for app '{app_id}'.",
        }

    def _handle_toggle_setting(self, app_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """Toggle an app setting on or off.

        Reads ~/.solace/config/settings.json, updates the setting key
        for the given app_id, and writes it back. Creates the file if
        it does not exist.
        """
        setting = params.get("setting", "")
        enabled = params.get("enabled")
        if not setting:
            raise ValueError("params must include 'setting' for toggle_setting action")
        if enabled is None:
            raise ValueError("params must include 'enabled' (bool) for toggle_setting action")

        # Actually toggle the setting in ~/.solace/config/settings.json
        config_dir = self._solace_home / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_path = config_dir / "settings.json"

        if settings_path.exists():
            settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(settings_data, dict):
                settings_data = {}
        else:
            settings_data = {}

        if app_id not in settings_data:
            settings_data[app_id] = {}
        settings_data[app_id][setting] = bool(enabled)

        settings_path.write_text(
            json.dumps(settings_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        state_str = "enabled" if enabled else "disabled"
        return {
            "success": True,
            "result": f"Setting '{setting}' {state_str} for app '{app_id}'.",
        }

    def _handle_explain(self, app_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """Explain how an app works by reading its manifest."""
        try:
            manifest = self._inbox_outbox.read_manifest(app_id)
        except FileNotFoundError:
            return {
                "success": False,
                "result": f"App '{app_id}' not found or missing manifest.",
            }

        name = manifest.get("name", app_id)
        description = manifest.get("description", "No description available.")
        return {
            "success": True,
            "result": f"{name}: {description}",
        }

    def _handle_show_history(self, app_id: str) -> dict[str, Any]:
        """Show run history for an app."""
        try:
            runs = self._inbox_outbox.list_runs(app_id)
        except FileNotFoundError:
            return {
                "success": False,
                "result": f"App '{app_id}' not found.",
            }

        if not runs:
            return {
                "success": True,
                "result": f"No run history for app '{app_id}'.",
            }

        lines = [f"Run history for '{app_id}' ({len(runs)} runs):"]
        for run in runs[:10]:  # Show last 10
            run_id = run.get("run_id", "unknown")
            state = run.get("state", "unknown")
            created = run.get("created_at", "unknown")
            lines.append(f"  - {run_id}: {state} ({created})")

        return {
            "success": True,
            "result": "\n".join(lines),
        }

    def _handle_rerun(self, app_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """Re-run a previous task.

        Raises NotImplementedError because rerun queuing requires the
        full execution lifecycle which is not yet wired up here.
        """
        run_id = params.get("run_id", "")
        if not run_id:
            raise ValueError("params must include 'run_id' for rerun action")

        # Verify the run exists
        try:
            runs = self._inbox_outbox.list_runs(app_id)
        except FileNotFoundError:
            return {
                "success": False,
                "result": f"App '{app_id}' not found.",
            }

        matching = [r for r in runs if r.get("run_id") == run_id]
        if not matching:
            return {
                "success": False,
                "result": f"Run '{run_id}' not found for app '{app_id}'.",
            }

        raise NotImplementedError("Rerun queuing not yet implemented")

    # -----------------------------------------------------------------------
    # Private: keyword matching
    # -----------------------------------------------------------------------

    @staticmethod
    def _match_keywords(
        message: str,
        keyword_map: dict[str, list[str]],
    ) -> tuple[str, float] | None:
        """Match a message against keyword categories.

        Returns (category, confidence) or None if no match.
        Confidence is based on the length of the matched keyword relative
        to the message length, capped at 1.0.
        """
        best_category: str | None = None
        best_confidence: float = 0.0
        best_keyword_len: int = 0

        for category, keywords in keyword_map.items():
            for keyword in keywords:
                if keyword in message:
                    keyword_len = len(keyword)
                    # Longer keyword matches are more confident
                    confidence = min(1.0, 0.5 + (keyword_len / max(len(message), 1)) * 0.5)
                    if keyword_len > best_keyword_len:
                        best_category = category
                        best_confidence = confidence
                        best_keyword_len = keyword_len

        if best_category is not None:
            return (best_category, round(best_confidence, 3))
        return None
