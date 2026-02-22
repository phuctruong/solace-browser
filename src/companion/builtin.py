"""
companion/builtin.py — Built-in companion apps that ship with Solace Browser.

Built-in apps demonstrate the companion app API and provide immediately useful
functionality out of the box.

Apps:
  ClipboardMonitor  — watches clipboard for URLs/text, suggests actions
  SessionRecorder   — records browser sessions as JSON logs for replay
  TaskTracker       — tracks multi-step task progress, integrates with workflow

All built-in apps follow the CompanionApp contract:
  - Required scopes declared at class level (includes companion.app.run)
  - handle_event() returns AppResponse
  - get_state() returns a copy of internal state (no cross-app leakage)
  - Int arithmetic only (no float)
  - No external dependencies beyond stdlib

Rung: 641 (local correctness)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from companion.apps import AppEvent, AppResponse, CompanionApp


# ---------------------------------------------------------------------------
# ClipboardMonitor
# ---------------------------------------------------------------------------

# Simple URL pattern — no external libs
_URL_PATTERN = re.compile(
    r"https?://[^\s\"'<>]+"
)


class ClipboardMonitor(CompanionApp):
    """
    Watches clipboard for URLs and text; suggests browser/recipe actions.

    Scope: companion.clipboard.monitor (+ base companion.app.run)

    Events handled:
        clipboard_change — data["content"] is the new clipboard text

    Actions suggested:
        - "open_url:<url>"        — navigate to a detected URL
        - "suggest_recipe:<url>"  — run a recipe matching the URL domain

    get_state():
        {
          "last_content": str,      — last clipboard text seen
          "url_count": int,         — number of URLs detected total
          "suggestion_count": int,  — number of suggestions emitted total
        }
    """

    app_id = "builtin.clipboard_monitor"
    name = "Clipboard Monitor"
    version = "1.0.0"
    required_scopes = ["companion.app.run", "companion.clipboard.monitor"]
    description = "Watches clipboard for URLs and text, suggests browser actions."

    def __init__(self) -> None:
        super().__init__()
        self._state.update({
            "last_content": "",
            "url_count": 0,
            "suggestion_count": 0,
        })

    def handle_event(self, event: AppEvent) -> AppResponse:
        """
        Handle clipboard_change events.

        For other event types, returns an 'ok' response with no actions.
        """
        if event.event_type != "clipboard_change":
            return AppResponse(status="ok", data={"ignored": event.event_type})

        content: str = str(event.data.get("content", ""))
        self._state["last_content"] = content

        urls = _URL_PATTERN.findall(content)
        actions: List[str] = []
        for url in urls:
            actions.append(f"open_url:{url}")
            actions.append(f"suggest_recipe:{url}")

        url_count = len(urls)
        self._state["url_count"] = self._state["url_count"] + url_count
        self._state["suggestion_count"] = (
            self._state["suggestion_count"] + len(actions)
        )

        return AppResponse(
            status="ok",
            data={
                "urls_detected": urls,
                "content_length": len(content),
            },
            actions=actions,
        )

    def get_state(self) -> Dict[str, Any]:
        return dict(self._state)


# ---------------------------------------------------------------------------
# SessionRecorder
# ---------------------------------------------------------------------------

@dataclass
class _RecordedEvent:
    """A single recorded browser event."""
    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: int


class SessionRecorder(CompanionApp):
    """
    Records browser sessions as JSON event logs for later replay.

    Scope:
        companion.recorder.capture  — to record sessions
        companion.recorder.replay   — to replay (step-up required)

    Events handled:
        session_start  — begins a new recording session
        session_stop   — ends the current recording session
        browser_event  — records a browser action (navigation, click, type)
                         data["action"] is redacted if "sensitive": True

    get_state():
        {
          "recording": bool,        — True if currently recording
          "session_id": str|None,   — current session identifier
          "event_count": int,       — events recorded in current session
          "sessions_completed": int,— total completed sessions
        }

    export_session() → dict:
        {
          "session_id": str,
          "started_at": int,
          "stopped_at": int|None,
          "events": [{"event_type": str, "source": str, "data": dict, "timestamp": int}, ...]
        }
    """

    app_id = "builtin.session_recorder"
    name = "Session Recorder"
    version = "1.0.0"
    required_scopes = [
        "companion.app.run",
        "companion.recorder.capture",
        "companion.recorder.replay",
    ]
    description = "Records browser sessions as JSON event logs for replay."

    def __init__(self) -> None:
        super().__init__()
        self._recording: bool = False
        self._session_id: Optional[str] = None
        self._started_at: Optional[int] = None
        self._stopped_at: Optional[int] = None
        self._recorded_events: List[_RecordedEvent] = []
        self._sessions_completed: int = 0
        self._state.update({
            "recording": False,
            "session_id": None,
            "event_count": 0,
            "sessions_completed": 0,
        })

    def handle_event(self, event: AppEvent) -> AppResponse:
        if event.event_type == "session_start":
            return self._handle_session_start(event)
        if event.event_type == "session_stop":
            return self._handle_session_stop(event)
        if event.event_type == "browser_event":
            return self._handle_browser_event(event)
        return AppResponse(status="ok", data={"ignored": event.event_type})

    def _handle_session_start(self, event: AppEvent) -> AppResponse:
        if self._recording:
            return AppResponse(
                status="error",
                data={"error": "already_recording", "session_id": self._session_id},
            )
        session_id = str(event.data.get("session_id", f"session_{int(time.time())}"))
        self._session_id = session_id
        self._recording = True
        self._started_at = int(time.time())
        self._stopped_at = None
        self._recorded_events = []
        self._state.update({
            "recording": True,
            "session_id": session_id,
            "event_count": 0,
        })
        return AppResponse(
            status="ok",
            data={"session_id": session_id, "started_at": self._started_at},
        )

    def _handle_session_stop(self, event: AppEvent) -> AppResponse:
        if not self._recording:
            return AppResponse(
                status="error",
                data={"error": "not_recording"},
            )
        self._recording = False
        self._stopped_at = int(time.time())
        self._sessions_completed += 1
        self._state.update({
            "recording": False,
            "sessions_completed": self._sessions_completed,
        })
        return AppResponse(
            status="ok",
            data={
                "session_id": self._session_id,
                "event_count": len(self._recorded_events),
                "stopped_at": self._stopped_at,
            },
        )

    def _handle_browser_event(self, event: AppEvent) -> AppResponse:
        if not self._recording:
            return AppResponse(
                status="deferred",
                data={"reason": "not_recording"},
            )
        data = dict(event.data)
        # Redact sensitive fields
        if data.get("sensitive"):
            data["value"] = "[REDACTED]"
        self._recorded_events.append(
            _RecordedEvent(
                event_type=event.event_type,
                source=event.source,
                data=data,
                timestamp=int(time.time()),
            )
        )
        event_count = len(self._recorded_events)
        self._state["event_count"] = event_count
        return AppResponse(
            status="ok",
            data={"event_count": event_count},
        )

    def export_session(self) -> Dict[str, Any]:
        """
        Export the current (or most recently completed) session as a JSON-serializable dict.

        Format:
            {
              "session_id": str,
              "started_at": int,
              "stopped_at": int | None,
              "events": [{"event_type": str, "source": str, "data": dict, "timestamp": int}, ...]
            }
        """
        return {
            "session_id": self._session_id,
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "events": [
                {
                    "event_type": e.event_type,
                    "source": e.source,
                    "data": e.data,
                    "timestamp": e.timestamp,
                }
                for e in self._recorded_events
            ],
        }

    def get_state(self) -> Dict[str, Any]:
        return dict(self._state)


# ---------------------------------------------------------------------------
# TaskTracker
# ---------------------------------------------------------------------------

@dataclass
class _TrackedTask:
    """Internal representation of a tracked task."""
    task_id: str
    name: str
    steps_total: int
    steps_completed: int = 0
    estimated_seconds: int = 0    # 0 = unknown; int only
    created_at: int = field(default_factory=lambda: int(time.time()))
    completed_at: Optional[int] = None
    done: bool = False


class TaskTracker(CompanionApp):
    """
    Tracks multi-step task progress; integrates with the workflow state machine.

    Scope: companion.tracker.manage (+ base companion.app.run)

    Events handled:
        task_create   — data: {task_id, name, steps_total, estimated_seconds?}
        task_step     — data: {task_id} — advances steps_completed by 1
        task_complete — data: {task_id} — marks task as done
        task_cancel   — data: {task_id} — removes task from tracker

    get_state():
        {
          "active_tasks": int,    — number of non-completed tasks
          "total_tasks": int,     — total tasks ever registered
          "tasks": {task_id: {name, steps_total, steps_completed, done, estimated_seconds}}
        }

    get_task(task_id) → dict | None
    """

    app_id = "builtin.task_tracker"
    name = "Task Tracker"
    version = "1.0.0"
    required_scopes = ["companion.app.run", "companion.tracker.manage"]
    description = "Tracks multi-step task progress and estimated completion time."

    def __init__(self) -> None:
        super().__init__()
        self._tasks: Dict[str, _TrackedTask] = {}
        self._total_created: int = 0
        self._state.update({
            "active_tasks": 0,
            "total_tasks": 0,
            "tasks": {},
        })

    def handle_event(self, event: AppEvent) -> AppResponse:
        if event.event_type == "task_create":
            return self._handle_create(event)
        if event.event_type == "task_step":
            return self._handle_step(event)
        if event.event_type == "task_complete":
            return self._handle_complete(event)
        if event.event_type == "task_cancel":
            return self._handle_cancel(event)
        return AppResponse(status="ok", data={"ignored": event.event_type})

    def _handle_create(self, event: AppEvent) -> AppResponse:
        task_id = str(event.data.get("task_id", ""))
        name = str(event.data.get("name", "Unnamed task"))
        steps_total = int(event.data.get("steps_total", 1))
        estimated_seconds = int(event.data.get("estimated_seconds", 0))

        if not task_id:
            return AppResponse(status="error", data={"error": "task_id_required"})
        if task_id in self._tasks:
            return AppResponse(
                status="error",
                data={"error": "duplicate_task_id", "task_id": task_id},
            )
        if steps_total < 1:
            steps_total = 1

        task = _TrackedTask(
            task_id=task_id,
            name=name,
            steps_total=steps_total,
            estimated_seconds=estimated_seconds,
        )
        self._tasks[task_id] = task
        self._total_created += 1
        self._refresh_state()
        return AppResponse(
            status="ok",
            data={"task_id": task_id, "steps_total": steps_total},
        )

    def _handle_step(self, event: AppEvent) -> AppResponse:
        task_id = str(event.data.get("task_id", ""))
        task = self._tasks.get(task_id)
        if task is None:
            return AppResponse(status="error", data={"error": "task_not_found", "task_id": task_id})
        if task.done:
            return AppResponse(status="error", data={"error": "task_already_done", "task_id": task_id})
        task.steps_completed = min(task.steps_completed + 1, task.steps_total)
        # Auto-complete if all steps done
        if task.steps_completed >= task.steps_total:
            task.done = True
            task.completed_at = int(time.time())
        self._refresh_state()
        return AppResponse(
            status="ok",
            data={
                "task_id": task_id,
                "steps_completed": task.steps_completed,
                "steps_remaining": task.steps_total - task.steps_completed,
                "done": task.done,
            },
        )

    def _handle_complete(self, event: AppEvent) -> AppResponse:
        task_id = str(event.data.get("task_id", ""))
        task = self._tasks.get(task_id)
        if task is None:
            return AppResponse(status="error", data={"error": "task_not_found", "task_id": task_id})
        task.done = True
        task.steps_completed = task.steps_total
        task.completed_at = int(time.time())
        self._refresh_state()
        return AppResponse(
            status="ok",
            data={"task_id": task_id, "done": True, "completed_at": task.completed_at},
        )

    def _handle_cancel(self, event: AppEvent) -> AppResponse:
        task_id = str(event.data.get("task_id", ""))
        if task_id not in self._tasks:
            return AppResponse(status="error", data={"error": "task_not_found", "task_id": task_id})
        del self._tasks[task_id]
        self._refresh_state()
        return AppResponse(status="ok", data={"task_id": task_id, "cancelled": True})

    def _refresh_state(self) -> None:
        """Recompute the _state snapshot from current task data."""
        tasks_snapshot: Dict[str, Any] = {}
        active = 0
        for tid, t in self._tasks.items():
            tasks_snapshot[tid] = {
                "name": t.name,
                "steps_total": t.steps_total,
                "steps_completed": t.steps_completed,
                "steps_remaining": t.steps_total - t.steps_completed,
                "estimated_seconds": t.estimated_seconds,
                "done": t.done,
            }
            if not t.done:
                active += 1
        self._state.update({
            "active_tasks": active,
            "total_tasks": self._total_created,
            "tasks": tasks_snapshot,
        })

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return a dict snapshot of the given task, or None if not found."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        return {
            "task_id": task.task_id,
            "name": task.name,
            "steps_total": task.steps_total,
            "steps_completed": task.steps_completed,
            "steps_remaining": task.steps_total - task.steps_completed,
            "estimated_seconds": task.estimated_seconds,
            "done": task.done,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
        }

    def get_state(self) -> Dict[str, Any]:
        return dict(self._state)


# ---------------------------------------------------------------------------
# Convenience registry helper
# ---------------------------------------------------------------------------

def get_builtin_apps() -> List[CompanionApp]:
    """Return one fresh instance of each built-in companion app."""
    return [
        ClipboardMonitor(),
        SessionRecorder(),
        TaskTracker(),
    ]
