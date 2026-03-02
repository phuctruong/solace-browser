"""
UI utilities for SolaceBrowser terminal output.

Modules:
  scope_display       — plain-English OAuth3 scope confirmation UI
  execution_progress  — step-by-step recipe execution progress tracker
  preview_explainer   — recipe preview plain-English explainer

Rung: 641
"""

from .execution_progress import (
    ExecutionProgress,
    StepState,
    StepRecord,
    ANSI,
)

from .preview_explainer import PreviewExplainer

from .scope_display import (
    ScopeDisplay,
    describe_scope,
    categorize_scopes,
    render_scope_modal,
    render_scope_diff,
)

__all__ = [
    # execution_progress
    "ExecutionProgress",
    "StepState",
    "StepRecord",
    "ANSI",
    # scope_display
    "ScopeDisplay",
    "describe_scope",
    "categorize_scopes",
    "render_scope_modal",
    "render_scope_diff",
    # preview_explainer
    "PreviewExplainer",
]

__version__ = "0.2.0"
__rung__ = 274177
