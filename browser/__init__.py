#!/usr/bin/env python3

"""
Solace Browser automation package.

This package exposes the reusable browser primitives used by the active
`solace_browser_server.py` webservice:
- `core.py`: ARIA tree, DOM extraction, page state, and basic actions
- `advanced.py`: observers, network monitoring, reference mapping
- `semantic.py`: metadata, API/network, and semantic analysis helpers

The only supported browser HTTP API lives in `solace_browser_server.py`.
There is no second supported server surface inside `browser/`.
"""

from browser.core import (
    AriaNode,
    BrowserAction,
    ClickAction,
    FillAction,
    HoverAction,
    PressAction,
    ScrollIntoViewAction,
    TypeAction,
    WaitAction,
    execute_action,
    execute_click,
    execute_fill,
    execute_hover,
    execute_press,
    execute_scroll_into_view,
    execute_type,
    execute_wait,
    format_aria_tree,
    get_dom_snapshot,
    get_page_state,
)
from browser.advanced import (
    AriaRefMapper,
    NetworkMonitor,
    PageObserver,
    execute_click_via_ref,
    execute_type_via_ref,
    get_llm_snapshot,
)
from browser.semantic import (
    SemanticAnalyzer,
    get_api_calls,
    get_js_state,
    get_meta_tags,
    get_rate_limit_info,
    get_semantic_analysis,
)

__all__ = [
    'AriaNode',
    'BrowserAction',
    'ClickAction',
    'FillAction',
    'HoverAction',
    'PressAction',
    'ScrollIntoViewAction',
    'TypeAction',
    'WaitAction',
    'execute_action',
    'execute_click',
    'execute_fill',
    'execute_hover',
    'execute_press',
    'execute_scroll_into_view',
    'execute_type',
    'execute_wait',
    'format_aria_tree',
    'get_dom_snapshot',
    'get_page_state',
    'AriaRefMapper',
    'NetworkMonitor',
    'PageObserver',
    'execute_click_via_ref',
    'execute_type_via_ref',
    'get_llm_snapshot',
    'SemanticAnalyzer',
    'get_api_calls',
    'get_js_state',
    'get_meta_tags',
    'get_rate_limit_info',
    'get_semantic_analysis',
]
