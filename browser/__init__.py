#!/usr/bin/env python3

"""
Solace Browser - Consolidated Web Automation Module

Architecture:
├── core.py          - ARIA tree, DOM extraction, basic page operations
├── advanced.py      - Page observer, network monitor, ref mapper
├── semantic.py      - 5-layer semantic analysis (visual/data/api/metadata/network)
├── http_server.py   - Persistent HTTP server wrapper
└── handlers.py      - HTTP endpoint handlers

This module consolidates:
- browser_interactions.py (basic ARIA + DOM extraction)
- enhanced_browser_interactions.py (page observation + network monitoring)
- persistent_browser_server.py (HTTP server + endpoint handlers)
"""

# Core layer
from browser.core import (
    AriaNode,
    ClickAction,
    TypeAction,
    PressAction,
    HoverAction,
    ScrollIntoViewAction,
    WaitAction,
    FillAction,
    BrowserAction,
    format_aria_tree,
    get_dom_snapshot,
    get_page_state,
    execute_action,
    execute_click,
    execute_type,
    execute_press,
    execute_hover,
    execute_scroll_into_view,
    execute_wait,
    execute_fill,
)

# Advanced layer
from browser.advanced import (
    AriaRefMapper,
    PageObserver,
    NetworkMonitor,
    get_llm_snapshot,
    execute_click_via_ref,
    execute_type_via_ref,
)

# Semantic layer
from browser.semantic import (
    SemanticAnalyzer,
    get_semantic_analysis,
    get_meta_tags,
    get_js_state,
    get_api_calls,
    get_rate_limit_info,
)

# Server layer
from browser.http_server import PersistentBrowserServer

__all__ = [
    # Core data structures
    "AriaNode",
    "ClickAction",
    "TypeAction",
    "PressAction",
    "HoverAction",
    "ScrollIntoViewAction",
    "WaitAction",
    "FillAction",
    "BrowserAction",

    # Core functions
    "format_aria_tree",
    "get_dom_snapshot",
    "get_page_state",
    "execute_action",
    "execute_click",
    "execute_type",
    "execute_press",
    "execute_hover",
    "execute_scroll_into_view",
    "execute_wait",
    "execute_fill",

    # Advanced functions
    "AriaRefMapper",
    "PageObserver",
    "NetworkMonitor",
    "get_llm_snapshot",
    "execute_click_via_ref",
    "execute_type_via_ref",

    # Semantic functions
    "SemanticAnalyzer",
    "get_semantic_analysis",
    "get_meta_tags",
    "get_js_state",
    "get_api_calls",
    "get_rate_limit_info",

    # Server
    "PersistentBrowserServer",
]
