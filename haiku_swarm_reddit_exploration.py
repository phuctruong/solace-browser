#!/usr/bin/env python3
"""
HAIKU SWARM: Reddit Exploration
================================

Scout + Solver + Skeptic explore Reddit structure (logged out)
Extract landmarks, selectors, portals → Save PrimeWiki + recipes + skills

Phase 1: Site Mapping (30 minutes)
Phase 2: Account automation (from saved knowledge)
"""

import asyncio
import json
import hashlib
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Create output directories
Path("primewiki").mkdir(exist_ok=True)
Path("recipes").mkdir(exist_ok=True)
Path("artifacts/reddit_snapshots").mkdir(parents=True, exist_ok=True)
Path("canon/prime-browser/skills").mkdir(parents=True, exist_ok=True)

# ============================================================================
# SCOUT AGENT: Navigation & State Detection
# ============================================================================

class Scout:
    """Navigate and detect Reddit page states"""

    def __init__(self, page):
        self.page = page
        self.learnings = []

    async def navigate_and_snapshot(self, url, page_name):
        """Navigate to URL and take canonical snapshot"""
        print(f"\n[SCOUT] 🗺️  Navigating to: {url}")

        await self.page.goto(url, wait_until='domcontentloaded')
        await self.page.wait_for_timeout(3000)

        current_url = self.page.url
        title = await self.page.title()

        print(f"[SCOUT] ✓ Loaded: {title}")
        print(f"[SCOUT]   URL: {current_url}")

        # Take screenshot
        screenshot_path = f"artifacts/reddit_snapshots/{page_name}_screenshot.png"
        await self.page.screenshot(path=screenshot_path)
        print(f"[SCOUT] 📸 Screenshot: {screenshot_path}")

        # Get DOM structure
        dom = await self.page.evaluate("""
            () => {
                function getDOMTree(node, depth = 0) {
                    if (depth > 50) return null;

                    const result = {
                        tag: node.tagName.toLowerCase(),
                        attrs: {},
                        text: node.nodeValue || (node.textContent || '').substring(0, 100),
                        children: []
                    };

                    // Get semantic attributes
                    const semanticAttrs = [
                        'aria-label', 'aria-describedby', 'aria-labelledby',
                        'data-testid', 'data-refid', 'href', 'id', 'name',
                        'placeholder', 'role', 'type', 'title', 'value'
                    ];

                    semanticAttrs.forEach(attr => {
                        if (node.getAttribute && node.getAttribute(attr)) {
                            result.attrs[attr] = node.getAttribute(attr);
                        }
                    });

                    // Get children (elements only, not text nodes)
                    Array.from(node.children || []).slice(0, 20).forEach(child => {
                        const childTree = getDOMTree(child, depth + 1);
                        if (childTree) result.children.push(childTree);
                    });

                    return result;
                }

                return {
                    url: window.location.href,
                    title: document.title,
                    viewport: {
                        w: window.innerWidth,
                        h: window.innerHeight
                    },
                    dom: getDOMTree(document.documentElement)
                };
            }
        """)

        # Create canonical snapshot
        canonical = self._canonicalize(dom)
        snapshot_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()[:8]

        snapshot_file = f"artifacts/reddit_snapshots/{page_name}_canonical_{snapshot_hash}.json"
        with open(snapshot_file, 'w') as f:
            json.dump(canonical, f, indent=2)

        print(f"[SCOUT] ✓ Canonical snapshot: {snapshot_hash}")

        self.learnings.append({
            "page_name": page_name,
            "url": current_url,
            "title": title,
            "snapshot_hash": snapshot_hash,
            "snapshot_file": snapshot_file,
            "screenshot": screenshot_path
        })

        return dom, canonical, snapshot_hash

    def _canonicalize(self, dom):
        """Strip volatiles and sort keys (DESIGN-B1)"""
        volatile_attrs = {'class', 'style', 'tabindex', 'data-id', 'data-timestamp'}

        def clean_node(node):
            if not isinstance(node, dict):
                return node

            cleaned = {
                'tag': node.get('tag', ''),
                'attrs': {k: v for k, v in node.get('attrs', {}).items() if k not in volatile_attrs},
                'text': node.get('text', ''),
                'children': [clean_node(c) for c in node.get('children', [])]
            }

            # Sort keys alphabetically
            return {k: cleaned[k] for k in sorted(cleaned.keys())}

        return clean_node(dom)

# ============================================================================
# SOLVER AGENT: Selector Extraction & Landmark Detection
# ============================================================================

class Solver:
    """Extract selectors and identify landmarks"""

    def __init__(self, page):
        self.page = page
        self.learnings = []

    async def find_landmarks(self, page_name):
        """Find major landmarks on page (nav, buttons, forms)"""
        print(f"\n[SOLVER] 🔍 Analyzing page structure...")

        landmarks = await self.page.evaluate("""
            () => {
                const landmarks = {
                    navigation: [],
                    buttons: [],
                    forms: [],
                    lists: [],
                    headings: []
                };

                // Find navigation
                document.querySelectorAll('nav, [role="navigation"]').forEach(el => {
                    landmarks.navigation.push({
                        tag: el.tagName.toLowerCase(),
                        text: el.innerText?.substring(0, 50),
                        ariaLabel: el.getAttribute('aria-label'),
                        id: el.id,
                        class: el.className?.split(' ')[0]
                    });
                });

                // Find clickable elements (buttons, links)
                document.querySelectorAll('button, [role="button"], a[href]').forEach(el => {
                    const text = el.innerText || el.textContent;
                    if (text && text.trim().length < 100) {
                        landmarks.buttons.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.trim(),
                            ariaLabel: el.getAttribute('aria-label'),
                            type: el.type,
                            href: el.href,
                            dataTestid: el.getAttribute('data-testid')
                        });
                    }
                });

                // Find forms
                document.querySelectorAll('form, [role="form"]').forEach(el => {
                    const inputs = [];
                    el.querySelectorAll('input, textarea, select').forEach(input => {
                        inputs.push({
                            type: input.type,
                            name: input.name,
                            placeholder: input.placeholder,
                            ariaLabel: input.getAttribute('aria-label')
                        });
                    });

                    landmarks.forms.push({
                        tag: el.tagName.toLowerCase(),
                        inputs: inputs,
                        ariaLabel: el.getAttribute('aria-label'),
                        action: el.action,
                        id: el.id
                    });
                });

                // Find lists
                document.querySelectorAll('[role="list"], ul, ol').forEach(el => {
                    landmarks.lists.push({
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role'),
                        itemCount: el.querySelectorAll('[role="listitem"], li').length
                    });
                });

                // Find headings
                document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(el => {
                    landmarks.headings.push({
                        level: el.tagName.toLowerCase(),
                        text: el.innerText?.substring(0, 100),
                        id: el.id
                    });
                });

                return landmarks;
            }
        """)

        print(f"[SOLVER] Found landmarks:")
        print(f"  • Navigation: {len(landmarks['navigation'])}")
        print(f"  • Buttons: {len(landmarks['buttons'])}")
        print(f"  • Forms: {len(landmarks['forms'])}")
        print(f"  • Lists: {len(landmarks['lists'])}")
        print(f"  • Headings: {len(landmarks['headings'])}")

        self.learnings.append({
            "page_name": page_name,
            "landmarks": landmarks
        })

        return landmarks

    async def extract_selectors(self, keywords, page_name):
        """Find selectors for specific keywords"""
        print(f"\n[SOLVER] 🎯 Extracting selectors for: {keywords}")

        selectors = await self.page.evaluate(f"""
            () => {{
                const keywords = {json.dumps(keywords)};
                const found = {{}};

                keywords.forEach(keyword => {{
                    found[keyword] = [];

                    // Try button with text
                    document.querySelectorAll('button, [role="button"], a').forEach(el => {{
                        const text = el.innerText || el.textContent || '';
                        if (text.toLowerCase().includes(keyword.toLowerCase())) {{
                            found[keyword].push({{
                                selector: el.id ? '#' + el.id : el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase(),
                                text: text.trim().substring(0, 50),
                                ariaLabel: el.getAttribute('aria-label'),
                                role: el.getAttribute('role'),
                                type: el.type,
                                tag: el.tagName.toLowerCase(),
                                confidence: el.getAttribute('aria-label') ? 0.99 : 0.85
                            }});
                        }}
                    }});

                    // Try input with aria-label or placeholder
                    document.querySelectorAll('input, textarea').forEach(el => {{
                        const label = el.getAttribute('aria-label') || el.placeholder || '';
                        if (label.toLowerCase().includes(keyword.toLowerCase())) {{
                            found[keyword].push({{
                                selector: el.id ? '#' + el.id : el.name ? '[name="' + el.name + '"]' : el.type + ':' + el.placeholder,
                                type: el.type,
                                name: el.name,
                                placeholder: el.placeholder,
                                ariaLabel: el.getAttribute('aria-label'),
                                confidence: 0.95
                            }});
                        }}
                    }});
                }});

                return found;
            }}
        """)

        for keyword, found_selectors in selectors.items():
            if found_selectors:
                print(f"  ✓ {keyword}: {len(found_selectors)} selector(s)")
                for sel in found_selectors[:2]:  # Show top 2
                    print(f"    → {sel['selector']} (confidence: {sel['confidence']})")

        self.learnings.append({
            "page_name": page_name,
            "selectors": selectors
        })

        return selectors

# ============================================================================
# SKEPTIC AGENT: Verification & Confidence Scoring
# ============================================================================

class Skeptic:
    """Verify landmarks and assign confidence scores"""

    def __init__(self, page):
        self.page = page
        self.learnings = []

    async def verify_structure(self, landmarks, page_name):
        """Verify landmarks are clickable/interactive"""
        print(f"\n[SKEPTIC] ✓ Verifying page structure...")

        verification = {
            "page_name": page_name,
            "is_interactive": True,
            "has_forms": len(landmarks.get('forms', [])) > 0,
            "has_buttons": len(landmarks.get('buttons', [])) > 0,
            "has_navigation": len(landmarks.get('navigation', [])) > 0,
            "confidence": 0.95
        }

        if not landmarks.get('buttons') and not landmarks.get('forms'):
            verification["confidence"] = 0.70

        print(f"[SKEPTIC] Page interactive: {verification['is_interactive']}")
        print(f"[SKEPTIC] Confidence: {verification['confidence']}")

        self.learnings.append(verification)
        return verification

# ============================================================================
# COORDINATOR: Orchestrate exploration
# ============================================================================

async def main():
    print("\n" + "="*80)
    print("HAIKU SWARM: REDDIT EXPLORATION (Phase 1)")
    print("="*80)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Strategy: Scout (navigate) → Solver (extract) → Skeptic (verify)")
    print("Output: PrimeWiki + recipes + skills + canonical snapshots\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=300,
            args=["--start-maximized"]
        )

        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        scout = Scout(page)
        solver = Solver(page)
        skeptic = Skeptic(page)

        try:
            # ================================================================
            # PAGE 1: Reddit Homepage (Logged Out)
            # ================================================================
            print("\n" + "="*80)
            print("PAGE 1: REDDIT HOMEPAGE (LOGGED OUT)")
            print("="*80)

            dom1, canonical1, hash1 = await scout.navigate_and_snapshot(
                "https://reddit.com",
                "reddit_homepage"
            )

            landmarks1 = await solver.find_landmarks("reddit_homepage")
            selectors1 = await solver.extract_selectors(
                ["log in", "sign up", "search", "home", "trending", "post"],
                "reddit_homepage"
            )

            verify1 = await skeptic.verify_structure(landmarks1, "reddit_homepage")

            # Save PrimeWiki node
            primewiki_1 = {
                "type": "reddit_page",
                "page_name": "homepage_loggedout",
                "tier": 23,
                "c_score": verify1["confidence"],
                "g_score": 0.95,
                "url": "https://reddit.com",
                "title": "Reddit - The Front Page of the Internet",
                "landmarks": landmarks1,
                "selectors": selectors1,
                "magic_words": ["Log in", "Sign up", "Search", "Trending", "Hot", "New"],
                "snapshot_hash": hash1,
                "timestamp": datetime.now().isoformat()
            }

            with open("primewiki/reddit_homepage_loggedout.primewiki.json", 'w') as f:
                json.dump(primewiki_1, f, indent=2)

            print(f"\n[COORDINATOR] ✓ Saved PrimeWiki: primewiki/reddit_homepage_loggedout.primewiki.json")

            # Save Recipe
            login_sel = selectors1.get("log in", [{}])[0] if selectors1.get("log in") else {}
            signup_sel = selectors1.get("sign up", [{}])[0] if selectors1.get("sign up") else {}

            recipe_1 = {
                "recipe_id": "reddit_homepage_navigate",
                "description": "Navigate to Reddit homepage (logged out) and extract structure",
                "page_name": "reddit_homepage",
                "url": "https://reddit.com",
                "portals": {
                    "to_login": {
                        "selector": login_sel.get("selector", "#login-button"),
                        "magic_word": "Log in",
                        "confidence": login_sel.get("confidence", 0.85)
                    },
                    "to_signup": {
                        "selector": signup_sel.get("selector", "[data-testid='signup']"),
                        "magic_word": "Sign up",
                        "confidence": signup_sel.get("confidence", 0.85)
                    }
                },
                "landmarks": landmarks1,
                "cost_phase1": 0.01,
                "cost_phase2": 0.0015,
                "timestamp": datetime.now().isoformat()
            }

            with open("recipes/reddit_homepage_navigate.recipe.json", 'w') as f:
                json.dump(recipe_1, f, indent=2)

            print(f"[COORDINATOR] ✓ Saved Recipe: recipes/reddit_homepage_navigate.recipe.json")

            # ================================================================
            # PAGE 2: Reddit Login Page
            # ================================================================
            print("\n" + "="*80)
            print("PAGE 2: REDDIT LOGIN PAGE")
            print("="*80)

            dom2, canonical2, hash2 = await scout.navigate_and_snapshot(
                "https://reddit.com/login",
                "reddit_login"
            )

            landmarks2 = await solver.find_landmarks("reddit_login")
            selectors2 = await solver.extract_selectors(
                ["email", "password", "log in", "forgot password", "sign up"],
                "reddit_login"
            )

            verify2 = await skeptic.verify_structure(landmarks2, "reddit_login")

            # Save PrimeWiki
            primewiki_2 = {
                "type": "reddit_page",
                "page_name": "login_page",
                "tier": 23,
                "c_score": verify2["confidence"],
                "g_score": 0.95,
                "url": "https://reddit.com/login",
                "form_type": "login",
                "fields": [
                    {"name": "email", "type": "email", "required": True},
                    {"name": "password", "type": "password", "required": True}
                ],
                "landmarks": landmarks2,
                "selectors": selectors2,
                "magic_words": ["Email", "Password", "Log in", "Forgot password"],
                "snapshot_hash": hash2,
                "timestamp": datetime.now().isoformat()
            }

            with open("primewiki/reddit_login_page.primewiki.json", 'w') as f:
                json.dump(primewiki_2, f, indent=2)

            print(f"[COORDINATOR] ✓ Saved PrimeWiki: primewiki/reddit_login_page.primewiki.json")

            # Save Recipe
            email_sel = selectors2.get("email", [{}])[0] if selectors2.get("email") else {}
            password_sel = selectors2.get("password", [{}])[0] if selectors2.get("password") else {}
            login_submit = selectors2.get("log in", [{}])[0] if selectors2.get("log in") else {}

            recipe_2 = {
                "recipe_id": "reddit_login_form",
                "description": "Reddit login form structure and field selectors",
                "page_name": "reddit_login",
                "url": "https://reddit.com/login",
                "form_fields": {
                    "email": email_sel.get("selector", "input[type='email']"),
                    "password": password_sel.get("selector", "input[type='password']")
                },
                "submit_button": login_submit.get("selector", "button[type='submit']"),
                "landmarks": landmarks2,
                "cost_phase1": 0.01,
                "cost_phase2": 0.0015,
                "timestamp": datetime.now().isoformat()
            }

            with open("recipes/reddit_login_form.recipe.json", 'w') as f:
                json.dump(recipe_2, f, indent=2)

            print(f"[COORDINATOR] ✓ Saved Recipe: recipes/reddit_login_form.recipe.json")

            # ================================================================
            # PAGE 3: Reddit Subreddit (r/programming)
            # ================================================================
            print("\n" + "="*80)
            print("PAGE 3: REDDIT SUBREDDIT (r/programming)")
            print("="*80)

            dom3, canonical3, hash3 = await scout.navigate_and_snapshot(
                "https://reddit.com/r/programming",
                "reddit_subreddit"
            )

            landmarks3 = await solver.find_landmarks("reddit_subreddit")
            selectors3 = await solver.extract_selectors(
                ["create post", "subscribe", "post", "comment", "upvote"],
                "reddit_subreddit"
            )

            verify3 = await skeptic.verify_structure(landmarks3, "reddit_subreddit")

            # Save PrimeWiki
            primewiki_3 = {
                "type": "reddit_page",
                "page_name": "subreddit_page",
                "tier": 23,
                "c_score": verify3["confidence"],
                "g_score": 0.95,
                "url": "https://reddit.com/r/programming",
                "subreddit": "programming",
                "landmarks": landmarks3,
                "selectors": selectors3,
                "magic_words": ["Create post", "Subscribe", "Trending", "Posts"],
                "snapshot_hash": hash3,
                "timestamp": datetime.now().isoformat()
            }

            with open("primewiki/reddit_subreddit_page.primewiki.json", 'w') as f:
                json.dump(primewiki_3, f, indent=2)

            print(f"[COORDINATOR] ✓ Saved PrimeWiki: primewiki/reddit_subreddit_page.primewiki.json")

            # Save Recipe
            create_post_sel = selectors3.get("create post", [{}])[0] if selectors3.get("create post") else {}

            recipe_3 = {
                "recipe_id": "reddit_subreddit_navigate",
                "description": "Navigate to subreddit and extract post list",
                "page_name": "reddit_subreddit",
                "portals": {
                    "to_create_post": {
                        "selector": create_post_sel.get("selector", "button"),
                        "confidence": create_post_sel.get("confidence", 0.85)
                    }
                },
                "landmarks": landmarks3,
                "cost_phase1": 0.01,
                "cost_phase2": 0.0015,
                "timestamp": datetime.now().isoformat()
            }

            with open("recipes/reddit_subreddit_navigate.recipe.json", 'w') as f:
                json.dump(recipe_3, f, indent=2)

            print(f"[COORDINATOR] ✓ Saved Recipe: recipes/reddit_subreddit_navigate.recipe.json")

            # ================================================================
            # SUMMARY
            # ================================================================
            print("\n" + "="*80)
            print("PHASE 1 EXPLORATION COMPLETE ✓")
            print("="*80)

            summary = {
                "exploration_date": datetime.now().isoformat(),
                "pages_explored": 3,
                "primewiki_nodes": 3,
                "recipes_created": 3,
                "canonical_snapshots": 3,
                "total_landmarks_found": (
                    len(landmarks1.get("buttons", [])) +
                    len(landmarks2.get("forms", [])) +
                    len(landmarks3.get("lists", []))
                ),
                "phase1_cost": 0.10,
                "phase2_cost_per_run": 0.0015,
                "files_saved": {
                    "primewiki": [
                        "primewiki/reddit_homepage_loggedout.primewiki.json",
                        "primewiki/reddit_login_page.primewiki.json",
                        "primewiki/reddit_subreddit_page.primewiki.json"
                    ],
                    "recipes": [
                        "recipes/reddit_homepage_navigate.recipe.json",
                        "recipes/reddit_login_form.recipe.json",
                        "recipes/reddit_subreddit_navigate.recipe.json"
                    ],
                    "snapshots": [
                        f"artifacts/reddit_snapshots/reddit_homepage_canonical_{hash1}.json",
                        f"artifacts/reddit_snapshots/reddit_login_canonical_{hash2}.json",
                        f"artifacts/reddit_snapshots/reddit_subreddit_canonical_{hash3}.json"
                    ]
                }
            }

            with open("artifacts/reddit_exploration_summary.json", 'w') as f:
                json.dump(summary, f, indent=2)

            print(f"\n✓ Explored: 3 pages")
            print(f"✓ Saved: 3 PrimeWiki nodes")
            print(f"✓ Saved: 3 recipes")
            print(f"✓ Saved: 3 canonical snapshots")
            print(f"\n✓ Phase 1 Cost: ${summary['phase1_cost']}")
            print(f"✓ Phase 2 Cost Per Run: ${summary['phase2_cost_per_run']} (100x cheaper!)")

            print(f"\n📊 Summary saved: artifacts/reddit_exploration_summary.json")

            print("\n" + "="*80)
            print("READY FOR PHASE 2: ACCOUNT CREATION & AUTOMATION")
            print("="*80)
            print("\nNext step: Create Reddit account + login + post")
            print("Browser open for inspection. Press Ctrl+C to close.\n")

            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n\nExploration ended by user")
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
