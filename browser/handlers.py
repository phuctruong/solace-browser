#!/usr/bin/env python3

"""
HTTP Handlers module - All endpoint handlers for the persistent browser server

This module contains all HTTP endpoint handler functions.
They are bound to the PersistentBrowserServer instance.
"""

import asyncio
import logging
from pathlib import Path
from aiohttp import web
from dataclasses import asdict

from browser.core import format_aria_tree, get_dom_snapshot
from browser.advanced import AriaRefMapper, get_llm_snapshot
from browser.semantic import get_semantic_analysis, get_meta_tags, get_js_state, get_api_calls

logger = logging.getLogger('browser-server')


def setup_handlers(app, server):
    """Setup all HTTP routes on the aiohttp app"""
    # Support both legacy endpoints (e.g. /status) and CLI-style endpoints (e.g. /api/status).
    # This keeps existing curl-based docs working while enabling solace-browser-cli-v3.sh.
    for prefix in ("", "/api"):
        app.router.add_get(f'{prefix}/health', lambda r: handle_health(r, server))
        app.router.add_get(f'{prefix}/status', lambda r: handle_status(r, server))
        app.router.add_post(f'{prefix}/navigate', lambda r: handle_navigate(r, server))

        # Snapshot is GET in the current server, but some clients POST /snapshot.
        app.router.add_get(f'{prefix}/snapshot', lambda r: handle_snapshot(r, server))
        app.router.add_post(f'{prefix}/snapshot', lambda r: handle_snapshot(r, server))

        app.router.add_get(f'{prefix}/html', lambda r: handle_html(r, server))
        app.router.add_get(f'{prefix}/html-clean', lambda r: handle_html_clean(r, server))
        app.router.add_get(f'{prefix}/detect-modals', lambda r: handle_detect_modals(r, server))
        app.router.add_post(f'{prefix}/click', lambda r: handle_click(r, server))
        app.router.add_post(f'{prefix}/fill', lambda r: handle_fill(r, server))
        app.router.add_post(f'{prefix}/keyboard', lambda r: handle_keyboard(r, server))
        app.router.add_post(f'{prefix}/evaluate', lambda r: handle_evaluate(r, server))
        app.router.add_post(f'{prefix}/save-session', lambda r: handle_save_session(r, server))

        # Screenshot is GET in the current server, but some clients POST /screenshot.
        app.router.add_get(f'{prefix}/screenshot', lambda r: handle_screenshot(r, server))
        app.router.add_post(f'{prefix}/screenshot', lambda r: handle_screenshot(r, server))

        # Unfair advantage features
        app.router.add_post(f'{prefix}/mouse-move', lambda r: handle_mouse_move(r, server))
        app.router.add_post(f'{prefix}/scroll-human', lambda r: handle_scroll_human(r, server))
        app.router.add_get(f'{prefix}/network-log', lambda r: handle_network_log(r, server))
        app.router.add_get(f'{prefix}/fingerprint-check', lambda r: handle_fingerprint_check(r, server))

        # Semantic layer
        app.router.add_get(f'{prefix}/semantic-analysis', lambda r: handle_semantic_analysis(r, server))
        app.router.add_get(f'{prefix}/meta-tags', lambda r: handle_meta_tags(r, server))
        app.router.add_get(f'{prefix}/js-state', lambda r: handle_js_state(r, server))
        app.router.add_get(f'{prefix}/api-calls', lambda r: handle_api_calls(r, server))

        # Rate limiting & registry
        app.router.add_get(f'{prefix}/rate-limit-status', lambda r: handle_rate_limit_status(r, server))
        app.router.add_get(f'{prefix}/check-registry', lambda r: handle_check_registry(r, server))


# ============================================================================
# Basic Handlers
# ============================================================================

async def handle_health(request, server):
    """Health check"""
    return web.json_response({"status": "ok", "browser_alive": server.browser is not None})


async def handle_status(request, server):
    """Get current browser status"""
    if not server.page:
        return web.json_response({"error": "No page"}, status=400)

    session_path = Path(server.session_file) if getattr(server, "session_file", None) else None
    return web.json_response({
        "success": True,
        "url": server.page.url,
        "title": await server.page.title(),
        "has_session": session_path.exists() if session_path else False,
        "session_file": str(session_path) if session_path else None,
        "session_file_bytes": session_path.stat().st_size if session_path and session_path.exists() else 0,
        "autosave_seconds": getattr(server, "autosave_seconds", None),
    })


async def handle_navigate(request, server):
    """Navigate to URL"""
    try:
        data = await request.json()
    except ValueError as e:
        logger.error(f"Invalid JSON: {e}")
        return web.json_response(
            {"error": f"Invalid JSON: {str(e)}", "code": "INVALID_JSON"},
            status=400
        )

    url = data.get('url')
    wait_strategy = data.get('wait_until', 'networkidle')
    wait_for_content = data.get('wait_for_content', True)

    if not url:
        return web.json_response(
            {"error": "Missing required field: 'url'", "code": "MISSING_FIELD"},
            status=400
        )

    logger.info(f"Navigating to: {url}")

    try:
        await server.page.goto(url, wait_until=wait_strategy, timeout=30000)
    except Exception as e:
        logger.warning(f"Navigation timeout (may still have loaded): {e}")

    if wait_for_content:
        try:
            logger.info("Waiting for page content...")
            await server.page.wait_for_function(
                "() => document.body.innerHTML.length > 100",
                timeout=8000
            )
        except Exception as e1:
            logger.warning(f"Content wait timeout: {e1}")

    await server.page.evaluate("() => new Promise(r => setTimeout(r, 800))")

    body_size = await server.page.evaluate("() => document.body.innerHTML.length")
    elem_count = await server.page.evaluate("() => document.querySelectorAll('*').length")

    return web.json_response({
        "success": True,
        "url": server.page.url,
        "title": await server.page.title(),
        "body_size": body_size,
        "element_count": elem_count
    })


async def handle_snapshot(request, server):
    """Get page snapshot (ARIA + DOM + console + network)"""
    logger.info("Getting snapshot...")

    aria_tree = await format_aria_tree(server.page, limit=500)
    dom_tree = await get_dom_snapshot(server.page, limit=800)

    server.ref_mapper = AriaRefMapper()
    await server.ref_mapper.build_map(server.page, [asdict(node) for node in aria_tree])

    snapshot = await get_llm_snapshot(
        server.page,
        [asdict(node) for node in aria_tree],
        dom_tree,
        server.observer,
        server.network
    )

    logger.info(f"Snapshot ready: {len(aria_tree)} ARIA nodes")

    ok = "error" not in snapshot
    return web.json_response({"success": ok, **snapshot})


async def handle_click(request, server):
    """Click element by CSS selector"""
    try:
        data = await request.json()
    except ValueError as e:
        return web.json_response(
            {"error": f"Invalid JSON: {str(e)}", "code": "INVALID_JSON"},
            status=400
        )

    selector = data.get('selector')

    if not selector:
        return web.json_response(
            {"error": "Missing required field: 'selector'", "code": "MISSING_FIELD"},
            status=400
        )

    logger.info(f"Clicking: {selector}")
    try:
        await server.page.click(selector, timeout=5000)
        await server.page.wait_for_load_state('domcontentloaded')
        return web.json_response({"success": True})
    except TimeoutError:
        return web.json_response(
            {"error": f"Element not found: {selector}", "code": "TIMEOUT"},
            status=408
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Click failed: {str(e)}", "code": "CLICK_FAILED"},
            status=500
        )


async def handle_fill(request, server):
    """Fill text into field"""
    try:
        data = await request.json()
    except ValueError as e:
        return web.json_response(
            {"error": f"Invalid JSON: {str(e)}", "code": "INVALID_JSON"},
            status=400
        )

    selector = data.get('selector')
    text = data.get('text')
    slowly = data.get('slowly', False)
    delay_ms = data.get('delay', 15)

    if not selector or text is None:
        return web.json_response(
            {"error": "Missing required fields: 'selector' and 'text'", "code": "MISSING_FIELD"},
            status=400
        )

    logger.info(f"Filling: {selector} (slowly={slowly})")

    try:
        if slowly:
            await server.page.click(selector, timeout=8000)
            await asyncio.sleep(0.1)
            await server.page.keyboard.press("Control+A")
            await asyncio.sleep(0.05)
            await server.page.keyboard.type(text, delay=delay_ms)
        else:
            await server.page.fill(selector, text)

        return web.json_response({"success": True})

    except TimeoutError:
        return web.json_response(
            {"error": f"Element not found: {selector}", "code": "TIMEOUT"},
            status=408
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Fill failed: {str(e)}", "code": "FILL_FAILED"},
            status=500
        )


async def handle_keyboard(request, server):
    """Handle keyboard press"""
    try:
        data = await request.json()
    except ValueError as e:
        return web.json_response(
            {"error": f"Invalid JSON: {str(e)}", "code": "INVALID_JSON"},
            status=400
        )

    key = data.get('key')

    if not key:
        return web.json_response(
            {"error": "Missing required field: 'key'", "code": "MISSING_FIELD"},
            status=400
        )

    logger.info(f"Keyboard press: {key}")
    try:
        await server.page.keyboard.press(key)
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response(
            {"error": f"Keyboard press failed: {str(e)}", "code": "KEYBOARD_FAILED"},
            status=500
        )


async def handle_evaluate(request, server):
    """Execute JavaScript in page context"""
    try:
        data = await request.json()
        script = data.get('script')

        if not script:
            return web.json_response({"error": "script required"}, status=400)

        logger.info(f"Evaluating JS: {script[:100]}...")
        result = await server.page.evaluate(script)
        return web.json_response({"success": True, "result": result})
    except Exception as e:
        logger.error(f"JS evaluation failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def handle_save_session(request, server):
    """Save browser session"""
    if not server.context:
        return web.json_response({"error": "No context"}, status=400)

    Path(server.session_file).parent.mkdir(parents=True, exist_ok=True)
    await server.context.storage_state(path=server.session_file)

    logger.info(f"Session saved: {server.session_file}")

    return web.json_response({"success": True, "path": server.session_file})


async def handle_screenshot(request, server):
    """Take screenshot"""
    data = {}
    if request.method == "POST":
        try:
            data = await request.json()
        except Exception:
            data = {}

    requested = (
        data.get("path")
        or request.query.get("path")
        or data.get("filename")
        or request.query.get("filename")
    )

    # Backward-compatible default used by many existing scripts and PrimeWiki nodes.
    path = "artifacts/screenshot.png"
    if requested:
        p = Path(str(requested))

        # If user passed a bare filename, keep it under artifacts/ for convenience.
        if len(p.parts) == 1:
            p = Path("artifacts") / p

        if p.is_absolute() or ".." in p.parts:
            return web.json_response({"error": "Invalid screenshot path"}, status=400)

        path = str(p)

    Path(path).parent.mkdir(parents=True, exist_ok=True)

    full_page = bool(data.get("full_page", False)) if isinstance(data, dict) else False
    await server.page.screenshot(path=path, full_page=full_page)
    logger.info(f"Screenshot: {path}")

    # Return both keys for compatibility with different clients.
    return web.json_response({"success": True, "path": path, "filepath": path})


async def handle_html(request, server):
    """Get current page HTML (raw)"""
    logger.info("Getting page HTML...")

    html = await server.page.content()

    return web.json_response({
        "success": True,
        "url": server.page.url,
        "title": await server.page.title(),
        "html": html,
        "html_length": len(html)
    })


async def handle_html_clean(request, server):
    """Get cleaned/simplified HTML for LLM understanding"""
    logger.info("Getting cleaned HTML...")

    html = await server.page.evaluate("""
    () => {
        const clone = document.documentElement.cloneNode(true);

        const removeTags = ['script', 'style', 'noscript', 'svg', 'path'];
        removeTags.forEach(tag => {
            clone.querySelectorAll(tag).forEach(el => el.remove());
        });

        const removeComments = (node) => {
            for (let i = node.childNodes.length - 1; i >= 0; i--) {
                const child = node.childNodes[i];
                if (child.nodeType === 8) {
                    node.removeChild(child);
                } else if (child.nodeType === 1) {
                    removeComments(child);
                }
            }
        };
        removeComments(clone);

        return clone.outerHTML;
    }
    """)

    return web.json_response({
        "success": True,
        "url": server.page.url,
        "title": await server.page.title(),
        "html": html,
        "html_length": len(html)
    })


async def handle_detect_modals(request, server):
    """Detect modals, popups, CAPTCHAs"""
    logger.info("Detecting modals, CAPTCHAs, popups...")

    detection = await server.page.evaluate("""
    () => {
        const detections = {
            timestamp: new Date().toISOString(),
            modals: [],
            captchas: [],
            popups: [],
            interactive_elements: [],
            title: document.title,
            url: window.location.href
        };

        const modalSelectors = [
            '[role="dialog"]',
            '[role="alertdialog"]',
            '.modal',
            '.modal-content',
            '[class*="modal"]',
            '[class*="popup"]',
            '[class*="overlay"]',
            '[aria-modal="true"]',
            '.lightbox',
            '.dialog'
        ];

        modalSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                    const rect = el.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0;
                    if (isVisible) {
                        detections.modals.push({
                            selector: selector,
                            text: el.innerText.substring(0, 200),
                            visible: true
                        });
                    }
                }
            });
        });

        // Check for Cloudflare
        if (document.querySelector('iframe[src*="challenges.cloudflare.com"]')) {
            detections.captchas.push({
                type: "cloudflare-turnstile",
                detected_by: "iframe src"
            });
        }

        // Check for reCAPTCHA
        if (document.querySelector('iframe[src*="recaptcha"]') || window.grecaptcha) {
            detections.captchas.push({
                type: "recaptcha",
                detected_by: "iframe or window.grecaptcha"
            });
        }

        return detections;
    }
    """)

    return web.json_response({
        "success": True,
        "detection": detection,
        "has_modals": len(detection.get("modals", [])) > 0,
        "has_captchas": len(detection.get("captchas", [])) > 0
    })


# ============================================================================
# Unfair Advantage Features
# ============================================================================

async def handle_mouse_move(request, server):
    """Human-like mouse movement using Bezier curves"""
    try:
        data = await request.json()
        from_x = data.get('from_x')
        from_y = data.get('from_y')
        to_x = data.get('to_x')
        to_y = data.get('to_y')
        duration_ms = data.get('duration_ms', 800)

        logger.info(f"Human mouse move: ({from_x},{from_y}) → ({to_x},{to_y})")

        await server.page.mouse.move(from_x, from_y)

        steps = max(10, duration_ms // 16)
        for i in range(steps + 1):
            progress = i / steps
            eased = progress if progress < 0.5 else 1 - (1 - progress) ** 2

            current_x = int(from_x + (to_x - from_x) * eased)
            current_y = int(from_y + (to_y - from_y) * eased)

            await server.page.mouse.move(current_x, current_y)
            await asyncio.sleep(duration_ms / (steps * 1000))

        return web.json_response({"success": True})
    except Exception as e:
        logger.error(f"Mouse move failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def handle_scroll_human(request, server):
    """Natural scroll behavior with inertia"""
    try:
        data = await request.json()
        distance_px = data.get('distance_px', data.get('distance', 300))
        direction = data.get('direction', 'down')
        duration_ms = data.get('duration_ms', 1000)

        logger.info(f"Human scroll: {distance_px}px {direction}")

        scroll_distance = distance_px if direction == 'down' else -distance_px

        await server.page.evaluate(f"""
            () => {{
                const distance = {scroll_distance};
                const duration = {duration_ms};
                const start = window.scrollY;
                const startTime = performance.now();

                const easeOutQuad = (t) => 1 - (1 - t) * (1 - t);

                const scroll = (currentTime) => {{
                    const elapsed = currentTime - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = easeOutQuad(progress);

                    window.scrollTo(0, start + distance * eased);

                    if (progress < 1) {{
                        requestAnimationFrame(scroll);
                    }}
                }};

                requestAnimationFrame(scroll);
                return new Promise(resolve => setTimeout(resolve, duration));
            }}
        """)

        return web.json_response({"success": True, "scrolled": distance_px})
    except Exception as e:
        logger.error(f"Scroll failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def handle_network_log(request, server):
    """Get raw network intercept log"""
    if not server.network:
        return web.json_response({"error": "Network monitor not initialized"}, status=400)

    try:
        requests = server.network.get_recent_requests(20)
        responses = server.network.get_recent_responses(20)
        failures = server.network.get_recent_failures(20) if hasattr(server.network, "get_recent_failures") else []
        return web.json_response({
            "success": True,
            "requests": requests,
            "responses": responses,
            "failures": failures,
        })
    except Exception as e:
        logger.error(f"Network log failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def handle_fingerprint_check(request, server):
    """Check what the website can detect about us"""
    try:
        logger.info("Checking fingerprint...")

        fingerprint = await server.page.evaluate("""
            () => {
                const result = {};

                result.webdriver = navigator.webdriver;
                result.chromeDetected = !!window.chrome;
                result.headless = navigator.userAgent.includes('HeadlessChrome');
                result.pluginCount = navigator.plugins.length;
                result.languages = navigator.languages;
                result.language = navigator.language;
                result.timezone = new Date().getTimezoneOffset();
                result.hardwareConcurrency = navigator.hardwareConcurrency;
                result.deviceMemory = navigator.deviceMemory;
                result.userAgent = navigator.userAgent;

                return result;
            }
        """)

        return web.json_response({
            "success": True,
            "fingerprint": fingerprint
        })
    except Exception as e:
        logger.error(f"Fingerprint check failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


# ============================================================================
# Semantic Layer Handlers
# ============================================================================

async def handle_semantic_analysis(request, server):
    """Complete 5-layer semantic analysis"""
    try:
        result = await get_semantic_analysis(server.page, server.network)
        return web.json_response({"success": True, "analysis": result})
    except Exception as e:
        logger.error(f"Semantic analysis failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def handle_meta_tags(request, server):
    """Extract Open Graph, Twitter Card, Schema.org"""
    try:
        result = await get_meta_tags(server.page)
        return web.json_response(result)
    except Exception as e:
        logger.error(f"Meta extraction failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def handle_js_state(request, server):
    """Extract JavaScript window state"""
    try:
        result = await get_js_state(server.page)
        return web.json_response(result)
    except Exception as e:
        logger.error(f"JS state extraction failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def handle_api_calls(request, server):
    """Get intercepted API calls"""
    try:
        result = await get_api_calls(server.page, server.network)
        return web.json_response(result)
    except Exception as e:
        logger.error(f"API call extraction failed: {e}")
        return web.json_response({"error": str(e)}, status=400)


# ============================================================================
# Rate Limiting & Registry
# ============================================================================

async def handle_rate_limit_status(request, server):
    """Check rate limit status for a domain"""
    try:
        url = request.query.get('url', server.page.url if server.page else 'example.com')

        if not url:
            return web.json_response(
                {"error": "Missing 'url' parameter"},
                status=400
            )

        stats = server.rate_limiter.get_stats(url)

        return web.json_response({
            "success": True,
            "current_domain": stats,
            "message": f"Rate limit for {stats['domain']}: {stats.get('requests_used', 0)}/{stats.get('requests_limit', '?')} requests"
        })
    except Exception as e:
        logger.error(f"Rate limit status check failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_check_registry(request, server):
    """Check if recipe exists for a domain"""
    try:
        url = request.query.get('url', server.page.url if server.page else None)

        if not url:
            return web.json_response(
                {"error": "Missing 'url' parameter", "code": "MISSING_URL"},
                status=400
            )

        result = server.registry.check(url)

        return web.json_response({
            "success": True,
            "url": url,
            "domain": result['domain'],
            "found": result['found'],
            "recipe_ids": result['recipe_ids'],
            "primary_recipe": result['primary_recipe'],
            "action": result['action'],
            "cost_savings_usd": result['cost_savings_usd'],
            "advice": result['advice']
        })
    except Exception as e:
        logger.error(f"Registry check failed: {e}")
        return web.json_response(
            {"error": f"Registry check failed: {str(e)}", "code": "REGISTRY_ERROR"},
            status=500
        )
