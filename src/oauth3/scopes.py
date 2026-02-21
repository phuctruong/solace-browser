"""
OAuth3 Scope Registry -- v0.1 (triple-segment format)

Scope naming convention: platform.action.resource

All scopes are:
  - Named (human-readable description)
  - Risk-classified: "low", "medium", "high"
  - Platform-grouped
  - Marked as destructive where applicable (requires step-up)

Pattern: ^[a-z][a-z0-9_-]+[.][a-z][a-z0-9_-]+[.][a-z][a-z0-9_-]+$

Reference: oauth3-spec-v0.1.md section 2
Rung: 641
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Scope format pattern (normative — oauth3-spec §2.1)
# ---------------------------------------------------------------------------

_SCOPE_PATTERN = re.compile(
    r"^[a-z][a-z0-9_-]+\.[a-z][a-z0-9_-]+\.[a-z][a-z0-9_-]+$"
)


def _scope_is_well_formed(scope: str) -> bool:
    """Return True if the scope string matches the triple-segment pattern."""
    return bool(_SCOPE_PATTERN.match(scope))


# ---------------------------------------------------------------------------
# Canonical scope registry — 30+ scopes across 5 platforms (spec §2.3)
# ---------------------------------------------------------------------------

SCOPE_REGISTRY: Dict[str, Dict] = {

    # -------------------------------------------------------------------------
    # LinkedIn
    # -------------------------------------------------------------------------

    "linkedin.read.feed": {
        "platform": "linkedin",
        "description": "Read the user's LinkedIn feed",
        "risk_level": "low",
        "destructive": False,
    },
    "linkedin.read.messages": {
        "platform": "linkedin",
        "description": "Read received LinkedIn messages",
        "risk_level": "low",
        "destructive": False,
    },
    "linkedin.read.profile": {
        "platform": "linkedin",
        "description": "Read LinkedIn profile data",
        "risk_level": "low",
        "destructive": False,
    },
    "linkedin.read.notifications": {
        "platform": "linkedin",
        "description": "Read LinkedIn notifications",
        "risk_level": "low",
        "destructive": False,
    },
    "linkedin.post.text": {
        "platform": "linkedin",
        "description": "Create a new text post on LinkedIn",
        "risk_level": "high",
        "destructive": True,
    },
    "linkedin.post.article": {
        "platform": "linkedin",
        "description": "Publish a long-form LinkedIn article",
        "risk_level": "high",
        "destructive": True,
    },
    "linkedin.edit.post": {
        "platform": "linkedin",
        "description": "Edit an existing LinkedIn post",
        "risk_level": "high",
        "destructive": True,
    },
    "linkedin.delete.post": {
        "platform": "linkedin",
        "description": "Delete a LinkedIn post (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },
    "linkedin.react.like": {
        "platform": "linkedin",
        "description": "Like a LinkedIn post",
        "risk_level": "low",
        "destructive": False,
    },
    "linkedin.comment.text": {
        "platform": "linkedin",
        "description": "Post a comment on LinkedIn",
        "risk_level": "high",
        "destructive": True,
    },
    "linkedin.send.message": {
        "platform": "linkedin",
        "description": "Send a LinkedIn direct message",
        "risk_level": "high",
        "destructive": True,
    },
    "linkedin.connect.request": {
        "platform": "linkedin",
        "description": "Send a LinkedIn connection request",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # Gmail
    # -------------------------------------------------------------------------

    "gmail.read.inbox": {
        "platform": "gmail",
        "description": "Read inbox messages",
        "risk_level": "low",
        "destructive": False,
    },
    "gmail.read.labels": {
        "platform": "gmail",
        "description": "Read Gmail label list",
        "risk_level": "low",
        "destructive": False,
    },
    "gmail.send.email": {
        "platform": "gmail",
        "description": "Send an email on behalf of the user (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },
    "gmail.delete.email": {
        "platform": "gmail",
        "description": "Delete an email permanently (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },
    "gmail.label.apply": {
        "platform": "gmail",
        "description": "Apply a label to a Gmail message",
        "risk_level": "low",
        "destructive": False,
    },
    "gmail.draft.create": {
        "platform": "gmail",
        "description": "Create a draft email (not sent)",
        "risk_level": "low",
        "destructive": False,
    },
    "gmail.search.messages": {
        "platform": "gmail",
        "description": "Search Gmail messages",
        "risk_level": "low",
        "destructive": False,
    },

    # -------------------------------------------------------------------------
    # Reddit
    # -------------------------------------------------------------------------

    "reddit.read.feed": {
        "platform": "reddit",
        "description": "Read subreddit posts",
        "risk_level": "low",
        "destructive": False,
    },
    "reddit.post.text": {
        "platform": "reddit",
        "description": "Create a text post on Reddit",
        "risk_level": "high",
        "destructive": True,
    },
    "reddit.post.link": {
        "platform": "reddit",
        "description": "Create a link post on Reddit",
        "risk_level": "high",
        "destructive": True,
    },
    "reddit.comment.text": {
        "platform": "reddit",
        "description": "Post a comment on Reddit",
        "risk_level": "high",
        "destructive": True,
    },
    "reddit.vote.up": {
        "platform": "reddit",
        "description": "Upvote a Reddit post or comment",
        "risk_level": "low",
        "destructive": False,
    },
    "reddit.delete.post": {
        "platform": "reddit",
        "description": "Delete a Reddit post (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # GitHub
    # -------------------------------------------------------------------------

    "github.read.issues": {
        "platform": "github",
        "description": "Read GitHub issues and pull requests",
        "risk_level": "low",
        "destructive": False,
    },
    "github.create.issue": {
        "platform": "github",
        "description": "Open a new GitHub issue",
        "risk_level": "medium",
        "destructive": False,
    },
    "github.comment.issue": {
        "platform": "github",
        "description": "Comment on a GitHub issue",
        "risk_level": "medium",
        "destructive": False,
    },
    "github.create.pr": {
        "platform": "github",
        "description": "Open a GitHub pull request",
        "risk_level": "high",
        "destructive": True,
    },
    "github.merge.pr": {
        "platform": "github",
        "description": "Merge a GitHub pull request (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },
    "github.delete.branch": {
        "platform": "github",
        "description": "Delete a GitHub branch (irreversible)",
        "risk_level": "high",
        "destructive": True,
    },

    # -------------------------------------------------------------------------
    # HackerNews
    # -------------------------------------------------------------------------

    "hackernews.read.feed": {
        "platform": "hackernews",
        "description": "Read the HackerNews front page",
        "risk_level": "low",
        "destructive": False,
    },
    "hackernews.vote.up": {
        "platform": "hackernews",
        "description": "Upvote a HackerNews post or comment",
        "risk_level": "low",
        "destructive": False,
    },
    "hackernews.comment.text": {
        "platform": "hackernews",
        "description": "Post a HackerNews comment",
        "risk_level": "high",
        "destructive": True,
    },
    "hackernews.submit.link": {
        "platform": "hackernews",
        "description": "Submit a link post to HackerNews",
        "risk_level": "high",
        "destructive": True,
    },
}


# ---------------------------------------------------------------------------
# Derived sets for fast lookups
# ---------------------------------------------------------------------------

# All registered scope strings
ALL_SCOPES: frozenset = frozenset(SCOPE_REGISTRY.keys())

# Scopes that are high-risk (step-up required before execution)
HIGH_RISK_SCOPES: frozenset = frozenset(
    scope for scope, meta in SCOPE_REGISTRY.items()
    if meta["risk_level"] == "high"
)

# Scopes marked as destructive (irreversible action)
DESTRUCTIVE_SCOPES: frozenset = frozenset(
    scope for scope, meta in SCOPE_REGISTRY.items()
    if meta["destructive"]
)

# Backward compat alias (old code imports STEP_UP_REQUIRED_SCOPES and SCOPES)
STEP_UP_REQUIRED_SCOPES: List[str] = sorted(HIGH_RISK_SCOPES)

SCOPES: Dict[str, str] = {
    scope: meta["description"]
    for scope, meta in SCOPE_REGISTRY.items()
}


# ---------------------------------------------------------------------------
# Scope validation helpers
# ---------------------------------------------------------------------------

def validate_scopes(requested: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all requested scopes are registered in SCOPE_REGISTRY.

    Also checks that each scope is well-formed (triple-segment pattern).
    Two-segment or four-segment scopes are rejected per spec §2.1.

    Args:
        requested: List of scope strings to validate.

    Returns:
        (is_valid: bool, invalid_scopes: List[str])
        is_valid is True only if all scopes are registered and well-formed.
    """
    invalid = []
    for s in requested:
        if not _scope_is_well_formed(s):
            invalid.append(s)
        elif s not in SCOPE_REGISTRY:
            invalid.append(s)
    return len(invalid) == 0, invalid


def get_high_risk_scopes(scopes: List[str]) -> List[str]:
    """
    Return the subset of scopes that are high-risk (require step-up auth).

    Args:
        scopes: List of scope strings.

    Returns:
        List of scopes from `scopes` that have risk_level == "high".
    """
    return [s for s in scopes if s in HIGH_RISK_SCOPES]


def group_by_platform(scopes: List[str]) -> Dict[str, List[str]]:
    """
    Group a list of scopes by their platform segment.

    Args:
        scopes: List of scope strings in platform.action.resource format.

    Returns:
        Dict mapping platform name → list of scopes for that platform.
        Scopes not found in SCOPE_REGISTRY are grouped under "unknown".
    """
    result: Dict[str, List[str]] = {}
    for scope in scopes:
        if scope in SCOPE_REGISTRY:
            platform = SCOPE_REGISTRY[scope]["platform"]
        else:
            # Best-effort: extract platform from first segment
            parts = scope.split(".")
            platform = parts[0] if parts else "unknown"
        result.setdefault(platform, []).append(scope)
    return result


def get_scope_description(scope: str) -> str | None:
    """
    Return human-readable description for a scope.

    Args:
        scope: Scope string (e.g. 'linkedin.post.text').

    Returns:
        Description string, or None if scope is unknown.
    """
    entry = SCOPE_REGISTRY.get(scope)
    return entry["description"] if entry else None


def get_scope_risk_level(scope: str) -> str:
    """
    Return risk level for a scope: "high", "medium", or "low".

    Unknown scopes return "high" (fail-closed).

    Args:
        scope: Scope string.

    Returns:
        "high", "medium", or "low".
    """
    entry = SCOPE_REGISTRY.get(scope)
    if entry is None:
        return "high"  # fail-closed: unknown scope treated as high risk
    return entry["risk_level"]


def is_step_up_required(scope: str) -> bool:
    """
    Return True if the given scope requires step-up re-consent.

    Args:
        scope: Scope string to check.

    Returns:
        True if scope is high-risk (risk_level == "high").
    """
    return scope in HIGH_RISK_SCOPES
