#!/usr/bin/env python3

"""
Core browser module - ARIA tree, DOM extraction, basic page operations

This layer provides fundamental browser interaction capabilities:
- ARIA accessibility tree extraction
- DOM tree snapshot
- Basic actions (click, type, press, hover, etc)
- Page state management
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, asdict

logger = logging.getLogger('solace-browser')


@dataclass
class AriaNode:
    """Accessibility tree node with reference"""
    ref: str  # "n1", "n2", etc.
    role: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    value: Optional[str] = None
    disabled: bool = False
    checked: Optional[bool] = None
    level: int = 0  # heading level for h1-h6


@dataclass
class ClickAction:
    """Click action with human-like options"""
    kind: Literal["click"] = "click"
    ref: str = ""
    double_click: bool = False
    button: Literal["left", "right", "middle"] = "left"
    modifiers: List[Literal["alt", "ctrl", "shift", "meta"]] = None
    delay_ms: int = 0
    timeout_ms: Optional[int] = None


@dataclass
class TypeAction:
    """Type action with human-like options"""
    kind: Literal["type"] = "type"
    ref: str = ""
    text: str = ""
    slowly: bool = False  # Type character by character
    delay_ms: int = 50    # Delay between characters when slowly=True
    submit: bool = False  # Press Enter after typing
    timeout_ms: Optional[int] = None


@dataclass
class PressAction:
    """Press key action"""
    kind: Literal["press"] = "press"
    key: str = ""
    delay_ms: int = 0
    timeout_ms: Optional[int] = None


@dataclass
class HoverAction:
    """Hover action"""
    kind: Literal["hover"] = "hover"
    ref: str = ""
    timeout_ms: Optional[int] = None


@dataclass
class ScrollIntoViewAction:
    """Scroll element into view"""
    kind: Literal["scrollIntoView"] = "scrollIntoView"
    ref: str = ""
    timeout_ms: Optional[int] = None


@dataclass
class WaitAction:
    """Wait for condition"""
    kind: Literal["wait"] = "wait"
    text: Optional[str] = None  # Wait for text to appear
    text_gone: Optional[str] = None  # Wait for text to disappear
    url: Optional[str] = None  # Wait for URL change
    selector: Optional[str] = None  # Wait for element
    load_state: Optional[Literal["load", "domcontentloaded", "networkidle"]] = None
    fn: Optional[str] = None  # Wait for custom JavaScript function to return true
    timeout_ms: int = 30000


@dataclass
class FillAction:
    """Fill multiple form fields"""
    kind: Literal["fill"] = "fill"
    fields: List[Dict[str, Any]] = None  # [{"ref": "n1", "text": "value"}]
    timeout_ms: Optional[int] = None


# Union type for all actions
BrowserAction = (
    ClickAction | TypeAction | PressAction | HoverAction |
    ScrollIntoViewAction | WaitAction | FillAction
)


async def format_aria_tree(page, limit: int = 500) -> List[AriaNode]:
    """
    Extract accessibility tree from page using CDP
    Returns ARIA nodes with ref IDs for structured AI interaction.
    """
    try:
        # Try Playwright accessibility API first
        if hasattr(page, 'accessibility'):
            snapshot = await page.accessibility.snapshot()
            if snapshot:
                nodes = []
                counter = [0]

                def traverse(node, depth=0):
                    if len(nodes) >= limit:
                        return

                    counter[0] += 1
                    ref = f"n{counter[0]}"

                    aria_node = AriaNode(
                        ref=ref,
                        role=node.get("role"),
                        name=node.get("name"),
                        text=node.get("value", ""),
                        disabled=node.get("disabled", False),
                        checked=node.get("checked"),
                        level=depth
                    )

                    nodes.append(aria_node)

                    # Traverse children
                    children = node.get("children", [])
                    for child in children:
                        if len(nodes) < limit:
                            traverse(child, depth + 1)

                traverse(snapshot)
                return nodes

        # Fallback: Use CDP directly
        logger.info("Using CDP for ARIA tree extraction")
        cdp = await page.context.new_cdp_session(page)

        # Enable Accessibility domain
        await cdp.send('Accessibility.enable')

        # Get full AX tree
        result = await cdp.send('Accessibility.getFullAXTree')

        nodes = []
        counter = [0]

        for ax_node in result.get('nodes', [])[:limit]:
            counter[0] += 1
            ref = f"n{counter[0]}"

            # Extract role
            role = None
            if 'role' in ax_node:
                role_obj = ax_node['role']
                if isinstance(role_obj, dict):
                    role = role_obj.get('value', '')
                else:
                    role = str(role_obj)

            # Extract name
            name = None
            if 'name' in ax_node:
                name_obj = ax_node['name']
                if isinstance(name_obj, dict):
                    name = name_obj.get('value', '')
                else:
                    name = str(name_obj)

            # Extract value
            value = None
            if 'value' in ax_node:
                value_obj = ax_node['value']
                if isinstance(value_obj, dict):
                    value = value_obj.get('value', '')
                else:
                    value = str(value_obj)

            # Skip if no role or name
            if not role and not name:
                continue

            aria_node = AriaNode(
                ref=ref,
                role=role,
                name=name,
                text=value or "",
                disabled=ax_node.get('disabled', {}).get('value', False) if 'disabled' in ax_node else False,
                checked=ax_node.get('checked', {}).get('value') if 'checked' in ax_node else None
            )

            nodes.append(aria_node)

        await cdp.detach()
        logger.info(f"Extracted {len(nodes)} ARIA nodes via CDP")
        return nodes

    except Exception as e:
        logger.error(f"Error extracting ARIA tree: {e}")
        return []


async def get_dom_snapshot(page, limit: int = 800) -> List[Dict[str, Any]]:
    """
    Extract DOM tree from page
    Returns DOM nodes with ref IDs for structured AI interaction.
    """
    try:
        # Get DOM structure via JavaScript
        dom_tree = await page.evaluate("""
        () => {
            const maxNodes = """ + str(limit) + """;
            const nodes = [];
            const root = document.documentElement;
            if (!root) return { nodes };

            const stack = [{ el: root, depth: 0, parentRef: null }];
            let nodeCount = 0;

            while (stack.length && nodeCount < maxNodes) {
                const cur = stack.pop();
                const el = cur.el;
                if (!el || el.nodeType !== 1) continue;

                const ref = "n" + String(nodeCount + 1);
                const tag = (el.tagName || "").toLowerCase();
                const id = el.id ? String(el.id) : undefined;
                const className = el.className ? String(el.className).slice(0, 300) : undefined;
                const role = el.getAttribute("role") || undefined;
                const ariaLabel = el.getAttribute("aria-label") || undefined;

                let text = "";
                try {
                    text = String(el.innerText || "").trim().slice(0, 220);
                } catch {}

                const href = el.href ? String(el.href) : undefined;
                const type = el.type ? String(el.type) : undefined;
                const value = el.value ? String(el.value).slice(0, 500) : undefined;
                const placeholder = el.placeholder ? String(el.placeholder) : undefined;

                nodes.push({
                    ref,
                    parentRef: cur.parentRef,
                    tag,
                    id,
                    className,
                    role,
                    ariaLabel,
                    text: text || undefined,
                    href,
                    type,
                    value,
                    placeholder,
                    visible: el.offsetParent !== null
                });

                nodeCount++;

                // Add children to stack
                const children = Array.from(el.children).reverse();
                for (const child of children) {
                    stack.push({
                        el: child,
                        depth: cur.depth + 1,
                        parentRef: ref
                    });
                }
            }

            return { nodes };
        }
        """)

        return dom_tree.get("nodes", [])
    except Exception as e:
        logger.error(f"Error extracting DOM tree: {e}")
        return []


async def get_page_state(page) -> Dict[str, Any]:
    """
    Get comprehensive page state for AI analysis
    Returns ARIA tree, DOM tree, and screenshot together
    """
    try:
        aria_tree = await format_aria_tree(page)
        dom_tree = await get_dom_snapshot(page)
        current_url = page.url
        title = await page.title()

        return {
            "url": current_url,
            "title": title,
            "aria": [asdict(node) for node in aria_tree],
            "dom": dom_tree,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Error getting page state: {e}")
        return {"error": str(e)}


async def execute_action(page, action: BrowserAction) -> Dict[str, Any]:
    """
    Execute a structured action on the page
    Supports human-like behaviors (slow typing, hover, modifiers, etc.)
    """
    try:
        if action.kind == "click":
            return await execute_click(page, action)
        elif action.kind == "type":
            return await execute_type(page, action)
        elif action.kind == "press":
            return await execute_press(page, action)
        elif action.kind == "hover":
            return await execute_hover(page, action)
        elif action.kind == "scrollIntoView":
            return await execute_scroll_into_view(page, action)
        elif action.kind == "wait":
            return await execute_wait(page, action)
        elif action.kind == "fill":
            return await execute_fill(page, action)
        else:
            return {"error": f"Unknown action kind: {action.kind}"}
    except Exception as e:
        logger.error(f"Error executing action: {e}")
        return {"error": str(e)}


async def execute_click(page, action: ClickAction) -> Dict[str, Any]:
    """Execute click action with modifiers and double-click support"""
    try:
        # Find element by ref (would need to resolve from ARIA snapshot)
        # For now, use a simple selector approach
        timeout_ms = action.timeout_ms or 5000

        # Try to find by aria-label first
        selector = f"[aria-label='{action.ref}']"

        try:
            await page.wait_for_selector(selector, timeout=timeout_ms)
        except:
            # Fallback to using the ref as is
            selector = action.ref

        kwargs = {
            "timeout": timeout_ms,
            "modifiers": action.modifiers or []
        }

        if action.delay_ms:
            await asyncio.sleep(action.delay_ms / 1000)

        if action.double_click:
            await page.double_click(selector, button=action.button, **kwargs)
            logger.info(f"Double-clicked: {action.ref}")
        else:
            await page.click(selector, button=action.button, **kwargs)
            logger.info(f"Clicked: {action.ref}")

        return {
            "success": True,
            "action": "click",
            "ref": action.ref,
            "url": page.url
        }
    except Exception as e:
        logger.error(f"Click action failed: {e}")
        return {"error": str(e)}


async def execute_type(page, action: TypeAction) -> Dict[str, Any]:
    """Execute type action with slow-typing support"""
    try:
        timeout_ms = action.timeout_ms or 5000

        # Find element
        selector = action.ref
        await page.wait_for_selector(selector, timeout=timeout_ms)

        if action.slowly:
            # Type character by character (looks human-like)
            logger.info(f"Typing slowly into {action.ref}: '{action.text}'")
            for char in action.text:
                await page.type(selector, char)
                if action.delay_ms:
                    await asyncio.sleep(action.delay_ms / 1000)
        else:
            # Fast fill
            await page.fill(selector, action.text)
            logger.info(f"Typed into {action.ref}: '{action.text}'")

        if action.submit:
            await page.press(selector, "Enter")
            logger.info(f"Submitted by pressing Enter")

        return {
            "success": True,
            "action": "type",
            "ref": action.ref,
            "text": action.text,
            "slowly": action.slowly,
            "url": page.url
        }
    except Exception as e:
        logger.error(f"Type action failed: {e}")
        return {"error": str(e)}


async def execute_press(page, action: PressAction) -> Dict[str, Any]:
    """Execute key press action"""
    try:
        if action.delay_ms:
            await asyncio.sleep(action.delay_ms / 1000)

        await page.keyboard.press(action.key)
        logger.info(f"Pressed key: {action.key}")

        return {
            "success": True,
            "action": "press",
            "key": action.key,
            "url": page.url
        }
    except Exception as e:
        logger.error(f"Press action failed: {e}")
        return {"error": str(e)}


async def execute_hover(page, action: HoverAction) -> Dict[str, Any]:
    """Execute hover action (useful for triggering tooltips)"""
    try:
        timeout_ms = action.timeout_ms or 5000
        selector = action.ref

        await page.wait_for_selector(selector, timeout=timeout_ms)
        await page.hover(selector)
        logger.info(f"Hovered over: {action.ref}")

        return {
            "success": True,
            "action": "hover",
            "ref": action.ref,
            "url": page.url
        }
    except Exception as e:
        logger.error(f"Hover action failed: {e}")
        return {"error": str(e)}


async def execute_scroll_into_view(page, action: ScrollIntoViewAction) -> Dict[str, Any]:
    """Execute scroll-into-view action"""
    try:
        timeout_ms = action.timeout_ms or 5000
        selector = action.ref

        await page.wait_for_selector(selector, timeout=timeout_ms)

        await page.evaluate(f"""
        (selector) => {{
            const el = document.querySelector("{selector}");
            if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
        """, selector)

        logger.info(f"Scrolled into view: {action.ref}")

        return {
            "success": True,
            "action": "scrollIntoView",
            "ref": action.ref,
            "url": page.url
        }
    except Exception as e:
        logger.error(f"Scroll into view action failed: {e}")
        return {"error": str(e)}


async def execute_wait(page, action: WaitAction) -> Dict[str, Any]:
    """Execute smart wait action"""
    try:
        timeout_ms = action.timeout_ms or 30000

        if action.text:
            await page.get_by_text(action.text, exact=False).first.wait_for(timeout=timeout_ms)
            logger.info(f"Waited for text: '{action.text}'")
            return {"success": True, "action": "wait", "reason": f"text appeared"}

        if action.text_gone:
            await page.get_by_text(action.text_gone, exact=False).first.wait_for(state="hidden", timeout=timeout_ms)
            logger.info(f"Waited for text to disappear: '{action.text_gone}'")
            return {"success": True, "action": "wait", "reason": f"text disappeared"}

        if action.url:
            await page.wait_for_url(f"*{action.url}*", timeout=timeout_ms)
            logger.info(f"Waited for URL change to: {action.url}")
            return {"success": True, "action": "wait", "reason": f"URL changed"}

        if action.load_state:
            await page.wait_for_load_state(action.load_state, timeout=timeout_ms)
            logger.info(f"Waited for load state: {action.load_state}")
            return {"success": True, "action": "wait", "reason": f"load state: {action.load_state}"}

        if action.fn:
            await page.wait_for_function(action.fn, timeout=timeout_ms)
            logger.info(f"Waited for custom function")
            return {"success": True, "action": "wait", "reason": f"custom function returned true"}

        if action.selector:
            await page.wait_for_selector(action.selector, timeout=timeout_ms)
            logger.info(f"Waited for selector: {action.selector}")
            return {"success": True, "action": "wait", "reason": f"element appeared"}

        return {"error": "No wait condition specified"}

    except Exception as e:
        logger.error(f"Wait action failed: {e}")
        return {"error": str(e)}


async def execute_fill(page, action: FillAction) -> Dict[str, Any]:
    """Execute fill multiple form fields at once"""
    try:
        if not action.fields:
            return {"error": "No fields to fill"}

        for field in action.fields:
            ref = field.get("ref")
            text = field.get("text", "")

            if not ref:
                continue

            timeout_ms = action.timeout_ms or 5000
            await page.wait_for_selector(ref, timeout=timeout_ms)
            await page.fill(ref, str(text))
            logger.info(f"Filled field {ref} with: '{text}'")

        return {
            "success": True,
            "action": "fill",
            "fields_filled": len(action.fields),
            "url": page.url
        }
    except Exception as e:
        logger.error(f"Fill action failed: {e}")
        return {"error": str(e)}
