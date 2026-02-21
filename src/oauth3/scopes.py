"""
OAuth3 Scope Registry

Scope naming convention: {platform}.{action_class}

All scopes are:
  - Named (human-readable description)
  - Risk-classified (step-up required for destructive actions)
  - Platform-grouped

Rung: 641
"""

from typing import List, Optional


# -------------------------------------------------------------------------
# Canonical scope registry
# -------------------------------------------------------------------------

SCOPES: dict = {
    # LinkedIn
    "linkedin.read_messages":  "Read your LinkedIn messages",
    "linkedin.create_post":    "Create posts on your behalf",
    "linkedin.edit_post":      "Edit your existing posts",
    "linkedin.delete_post":    "Delete your posts (STEP-UP REQUIRED)",
    "linkedin.react":          "React to posts on your behalf",
    "linkedin.comment":        "Comment on posts on your behalf",

    # Gmail
    "gmail.read_inbox":        "Read your Gmail inbox",
    "gmail.send_email":        "Send email on your behalf",
    "gmail.search":            "Search your email",
    "gmail.label":             "Apply labels to email",
    "gmail.delete_email":      "Delete email permanently (STEP-UP REQUIRED)",

    # HackerNews
    "hackernews.submit":       "Submit stories to HackerNews",
    "hackernews.comment":      "Comment on HackerNews",

    # Reddit
    "reddit.create_post":      "Post to subreddits on your behalf",
    "reddit.comment":          "Comment on Reddit posts on your behalf",
    "reddit.upvote":           "Upvote posts and comments on your behalf",
    "reddit.delete_post":      "Delete your Reddit posts (STEP-UP REQUIRED)",

    # Notion
    "notion.read_page":        "Read your Notion pages",
    "notion.write_page":       "Write to your Notion pages",

    # Substack (Phase 2 — reserved)
    "substack.publish_post":   "Publish posts to your Substack newsletter",
    "substack.get_stats":      "Read your Substack subscriber and engagement stats",
    "substack.schedule_post":  "Schedule future posts on your Substack",

    # Twitter/X (Phase 2 — reserved)
    "twitter.post_tweet":      "Post tweets on your behalf",
    "twitter.read_timeline":   "Read your Twitter timeline",
    "twitter.check_notifications": "Read your Twitter notifications",
}


# -------------------------------------------------------------------------
# Step-up required scopes (destructive / high-risk)
# -------------------------------------------------------------------------

STEP_UP_REQUIRED_SCOPES: List[str] = [
    "linkedin.delete_post",
    "gmail.delete_email",
    "reddit.delete_post",
]


# -------------------------------------------------------------------------
# Scope validation helpers
# -------------------------------------------------------------------------

def validate_scopes(requested: List[str]) -> tuple:
    """
    Validate that all requested scopes are registered.

    Args:
        requested: List of scope strings to validate.

    Returns:
        (is_valid: bool, unknown_scopes: List[str])
        is_valid is True only if all requested scopes exist in SCOPES.
    """
    unknown = [s for s in requested if s not in SCOPES]
    return len(unknown) == 0, unknown


def get_scope_description(scope: str) -> Optional[str]:
    """
    Return human-readable description for a scope.

    Args:
        scope: Scope string (e.g. "linkedin.create_post").

    Returns:
        Description string, or None if scope is unknown.
    """
    return SCOPES.get(scope)


def is_step_up_required(scope: str) -> bool:
    """
    Return True if the given scope requires step-up re-consent.

    Args:
        scope: Scope string to check.

    Returns:
        True if scope is in STEP_UP_REQUIRED_SCOPES.
    """
    return scope in STEP_UP_REQUIRED_SCOPES


def get_platform_scopes(platform: str) -> dict:
    """
    Return all scopes for a given platform.

    Args:
        platform: Platform name (e.g. "linkedin", "gmail").

    Returns:
        Dict of {scope: description} for all scopes matching the platform.
    """
    prefix = f"{platform}."
    return {k: v for k, v in SCOPES.items() if k.startswith(prefix)}


def get_scope_risk_level(scope: str) -> str:
    """
    Return risk level for a scope: "high", "medium", or "low".

    High-risk = step-up required (destructive actions).
    Medium = write/send actions.
    Low = read-only actions.

    Args:
        scope: Scope string.

    Returns:
        "high", "medium", or "low".
    """
    if scope in STEP_UP_REQUIRED_SCOPES:
        return "high"

    action = scope.split(".")[-1] if "." in scope else scope

    write_actions = {
        "create_post", "edit_post", "send_email", "label", "submit",
        "comment", "react", "upvote", "write_page", "post_tweet",
        "publish_post", "schedule_post",
    }

    if action in write_actions:
        return "medium"

    return "low"
