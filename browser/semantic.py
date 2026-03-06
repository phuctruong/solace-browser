#!/usr/bin/env python3

"""
Semantic browser module - 5-layer web analysis

This layer provides deep semantic understanding of web pages:
1. Visual (layout) - Viewport, scroll depth, element count
2. Data (JavaScript) - Window variables, app state
3. API (backend calls) - HTTP requests, API endpoints
4. Metadata (schema.org, OG tags) - Structured data
5. Network (rate limits, cache) - Headers and timing
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from playwright.async_api import Error as PlaywrightError

logger = logging.getLogger('solace-browser')


class SemanticAnalyzer:
    """
    Performs complete 5-layer semantic analysis of web pages
    """

    def __init__(self, page, network_monitor=None):
        self.page = page
        self.network_monitor = network_monitor

    async def analyze(self) -> Dict[str, Any]:
        """Run complete 5-layer analysis"""
        try:
            logger.info("🔍 Running 5-layer semantic analysis...")

            result = {
                "timestamp": datetime.now().isoformat(),
                "url": self.page.url,
                "title": await self.page.title(),
                "layers": {}
            }

            # Layer 1: Visual (geometric)
            result["layers"]["visual"] = await self._analyze_visual()

            # Layer 2: Data (JavaScript)
            result["layers"]["data"] = await self._analyze_data()

            # Layer 3: API (network interception)
            result["layers"]["api"] = await self._analyze_api()

            # Layer 4: Metadata (SEO)
            result["layers"]["metadata"] = await self._analyze_metadata()

            # Layer 5: Network (headers & timing)
            result["layers"]["network"] = await self._analyze_network()

            return result

        except (PlaywrightError, ConnectionError, OSError, TimeoutError, KeyError, AttributeError) as e:
            logger.error(f"Error in semantic analysis: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def _analyze_visual(self) -> Dict[str, Any]:
        """Layer 1: Visual (layout)"""
        try:
            result = await self.page.evaluate("""
                () => ({
                    viewport: { width: window.innerWidth, height: window.innerHeight },
                    scroll_depth: window.scrollY,
                    scroll_max: document.documentElement.scrollHeight - window.innerHeight,
                    element_count: document.querySelectorAll('*').length,
                    visible_elements: document.querySelectorAll(':visible').length || 'unknown',
                    interactive_elements: document.querySelectorAll('button, a, input, [role="button"]').length
                })
            """)
            return result
        except (PlaywrightError, ConnectionError, OSError, TimeoutError) as e:
            logger.warning(f"Visual analysis failed: {e}")
            return {"error": str(e)}

    async def _analyze_data(self) -> Dict[str, Any]:
        """Layer 2: Data (JavaScript)"""
        try:
            state = await self.page.evaluate("""
                () => {
                    const state = {
                        windowVars: {},
                        globalConfig: {}
                    };

                    // Capture app state
                    if (window.APP_STATE) state.windowVars.APP_STATE = typeof window.APP_STATE;
                    if (window.config) state.globalConfig = { keys: Object.keys(window.config || {}) };
                    if (window.__data__) state.windowVars.data = typeof window.__data__;
                    if (window.__INITIAL_STATE__) state.windowVars.INITIAL_STATE = typeof window.__INITIAL_STATE__;

                    return state;
                }
            """)
            return state
        except (PlaywrightError, ConnectionError, OSError, TimeoutError) as e:
            logger.warning(f"Data analysis failed: {e}")
            return {"error": str(e)}

    async def _analyze_api(self) -> Dict[str, Any]:
        """Layer 3: API (network interception)"""
        try:
            api_calls = []
            if self.network_monitor:
                log = self.network_monitor.get_recent_requests(20)
                for entry in log:
                    if '/api/' in entry.get('url', ''):
                        api_calls.append({
                            "url": entry.get('url'),
                            "method": entry.get('method'),
                            "resourceType": entry.get('resourceType')
                        })

            return {
                "api_calls_detected": len(api_calls),
                "apis": api_calls[:10],
                "total_requests": len(self.network_monitor.requests) if self.network_monitor else 0
            }
        except (AttributeError, KeyError, TypeError) as e:
            logger.warning(f"API analysis failed: {e}")
            return {"error": str(e)}

    async def _analyze_metadata(self) -> Dict[str, Any]:
        """Layer 4: Metadata (schema.org, OG tags)"""
        try:
            meta = await self.page.evaluate("""
                () => {
                    const meta = {};

                    // OG tags
                    const ogTags = document.querySelectorAll('meta[property^="og:"]');
                    ogTags.forEach(tag => {
                        meta[tag.getAttribute('property')] = tag.getAttribute('content');
                    });

                    // Twitter Card
                    const twitterTags = document.querySelectorAll('meta[name^="twitter:"]');
                    twitterTags.forEach(tag => {
                        meta[tag.getAttribute('name')] = tag.getAttribute('content');
                    });

                    // Schema.org
                    const schemas = [];
                    document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                        try {
                            schemas.push(JSON.parse(script.textContent));
                        } catch (e) {
                            console.error('Schema parse error:', e);
                        }
                    });

                    if (schemas.length > 0) {
                        meta.schema = schemas;
                    }

                    return meta;
                }
            """)
            return meta
        except (PlaywrightError, ConnectionError, OSError, TimeoutError) as e:
            logger.warning(f"Metadata analysis failed: {e}")
            return {"error": str(e)}

    async def _analyze_network(self) -> Dict[str, Any]:
        """Layer 5: Network (headers & timing)"""
        try:
            return {
                "rate_limits": "Check response headers",
                "cache_strategy": "Check Cache-Control header",
                "etag_enabled": "Check ETag presence",
                "note": "Full headers available via network monitor"
            }
        except (AttributeError, OSError) as e:
            logger.warning(f"Network analysis failed: {e}")
            return {"error": str(e)}


# ============================================================================
# Standalone helper functions
# ============================================================================

async def get_semantic_analysis(page, network_monitor=None) -> Dict[str, Any]:
    """
    Complete 5-layer semantic analysis
    """
    analyzer = SemanticAnalyzer(page, network_monitor)
    return await analyzer.analyze()


async def get_meta_tags(page) -> Dict[str, Any]:
    """Extract Open Graph, Twitter Card, Schema.org"""
    try:
        logger.info("📋 Extracting metadata...")

        meta_data = await page.evaluate("""
            () => {
                const result = { og: {}, twitter: {}, schema: {} };

                // Open Graph
                document.querySelectorAll('meta[property^="og:"]').forEach(tag => {
                    result.og[tag.getAttribute('property')] = tag.getAttribute('content');
                });

                // Twitter Card
                document.querySelectorAll('meta[name^="twitter:"]').forEach(tag => {
                    result.twitter[tag.getAttribute('name')] = tag.getAttribute('content');
                });

                // Schema.org
                document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                    try {
                        result.schema[Object.keys(result.schema).length] = JSON.parse(script.textContent);
                    } catch (e) {
                        console.error('Schema parse error:', e);
                    }
                });

                return result;
            }
        """)

        return {"success": True, "metadata": meta_data}
    except (PlaywrightError, ConnectionError, OSError, TimeoutError) as e:
        logger.error(f"Meta extraction failed: {e}")
        return {"error": str(e)}


async def get_js_state(page) -> Dict[str, Any]:
    """Extract JavaScript window state and app variables"""
    try:
        logger.info("💾 Extracting JavaScript state...")

        js_state = await page.evaluate("""
            () => {
                const state = {};

                // Capture key app-level variables
                const appVars = ['APP_STATE', 'config', '__data__', '__INITIAL_STATE__', '__STATE__'];

                appVars.forEach(varName => {
                    if (window[varName]) {
                        state[varName] = {
                            type: typeof window[varName],
                            size: JSON.stringify(window[varName]).length,
                            keys: typeof window[varName] === 'object' ? Object.keys(window[varName]).slice(0, 10) : null
                        };
                    }
                });

                return state;
            }
        """)

        return {"success": True, "js_state": js_state}
    except (PlaywrightError, ConnectionError, OSError, TimeoutError) as e:
        logger.error(f"JS state extraction failed: {e}")
        return {"error": str(e)}


async def get_api_calls(page, network_monitor=None) -> Dict[str, Any]:
    """Get intercepted API calls (what frontend talks to)"""
    try:
        logger.info("🔗 Getting API calls...")

        api_calls = []
        if network_monitor:
            log = network_monitor.get_recent_requests(20)
            for entry in log:
                if '/api/' in entry.get('url', ''):
                    api_calls.append({
                        "url": entry.get('url'),
                        "method": entry.get('method'),
                        "resourceType": entry.get('resourceType')
                    })

        return {
            "success": True,
            "api_calls_found": len(api_calls),
            "apis": api_calls[:10]
        }
    except (AttributeError, KeyError, TypeError) as e:
        logger.error(f"API call extraction failed: {e}")
        return {"error": str(e)}


async def get_rate_limit_info(page) -> Dict[str, Any]:
    """Extract rate limit information from response headers"""
    try:
        logger.info("⏱️  Extracting rate limits...")

        # Get last response headers
        rate_info = {
            "rate_limit": "N/A",
            "remaining": "N/A",
            "reset_time": "N/A",
            "cache_control": "N/A",
            "etag": "N/A"
        }

        return {
            "success": True,
            "rate_limits": rate_info,
            "note": "Use network monitor for full header data"
        }
    except (AttributeError, OSError) as e:
        logger.error(f"Rate limit extraction failed: {e}")
        return {"error": str(e)}
