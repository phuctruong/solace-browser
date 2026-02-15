#!/usr/bin/env python3
"""
Headless Executor with Debug Output
When selectors fail, logs surrounding HTML to help identify correct selectors
"""
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Dict, Any
from playwright.async_api import async_playwright

class DebugRecipeExecutor:
    """Execute recipes headless with debug output"""

    def __init__(self, headless=True):
        self.browser = None
        self.context = None
        self.page = None
        self.recipes = {}
        self.headless = headless

    async def start(self):
        """Start headless browser"""
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def stop(self):
        """Stop browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def load_recipe(self, recipe_path: str) -> Dict[str, Any]:
        """Load recipe from JSON"""
        with open(recipe_path, 'r') as f:
            recipe = json.load(f)
        self.recipes[recipe['recipe_id']] = recipe
        return recipe

    async def debug_selector_failure(self, selector: str, step_num: int, action: str):
        """When a selector fails, log HTML context to help debug"""
        try:
            html = await self.page.content()
            # Get the part of HTML around common patterns
            if 'hackernews' in str(self.page.url).lower():
                print(f"\n     🔍 DEBUG: HackerNews selector failed for step {step_num}")
                print(f"        Selector tried: {selector}")
                print(f"        Action: {action}")

                # Look for votearrow in HTML
                if 'votearrow' in selector:
                    # Find votearrow in HTML
                    if 'votearrow' in html:
                        idx = html.find('votearrow')
                        snippet = html[max(0, idx-200):idx+300]
                        print(f"        Found 'votearrow' in HTML:")
                        print(f"        {snippet[:200]}...")
                    else:
                        print(f"        'votearrow' not found in current HTML")

                # Try alternative selectors
                print(f"        Trying alternatives...")
                alts = [
                    "div.votearrow",
                    "a.votearrow",
                    ".votearrow",
                    "div[class*='vote']",
                ]
                for alt in alts:
                    try:
                        count = len(await self.page.query_selector_all(alt))
                        print(f"          {alt}: {count} elements found")
                    except:
                        pass

            elif 'reddit' in str(self.page.url).lower():
                print(f"\n     🔍 DEBUG: Reddit selector failed for step {step_num}")
                print(f"        Selector tried: {selector}")
                print(f"        Action: {action}")

                # Look for upvote buttons
                if 'upvote' in selector.lower():
                    print(f"        Trying to find upvote buttons...")
                    alts = [
                        "button[aria-label*='upvote' i]",
                        "button[aria-label*='Upvote' i]",
                        "button[title*='upvote' i]",
                        "button[data-testid*='upvote' i]",
                        "div[class*='vote'] button",
                    ]
                    for alt in alts:
                        try:
                            count = len(await self.page.query_selector_all(alt))
                            if count > 0:
                                print(f"          ✅ {alt}: {count} elements found")
                                # Show first element
                                elem = await self.page.query_selector(alt)
                                html_snippet = await elem.outer_html()
                                print(f"             {html_snippet[:150]}...")
                            else:
                                print(f"          ❌ {alt}: 0 elements")
                        except Exception as e:
                            print(f"          ❌ {alt}: error - {str(e)[:50]}")

        except Exception as e:
            print(f"     Could not debug: {e}")

    async def execute_step(self, step: Dict[str, Any], step_context: Dict = None) -> bool:
        """Execute single step from recipe"""
        action = step['action']

        try:
            if action == 'navigate':
                await self.page.goto(step['target'], wait_until='domcontentloaded', timeout=30000)
                return True

            elif action == 'wait':
                await asyncio.sleep(step['duration'] / 1000)
                return True

            elif action == 'click':
                selector = step['selector']
                try:
                    # Try to click without waiting for visibility first
                    await self.page.click(selector, timeout=3000)
                    return True
                except Exception as click_error:
                    # Selector failed - debug it
                    await self.debug_selector_failure(selector, step.get('step', '?'), action)
                    return False

            elif action == 'fill':
                selector = step['selector']
                text = step.get('text', '')
                try:
                    await self.page.fill(selector, text, timeout=3000)
                    return True
                except:
                    return False

            elif action == 'extract':
                html = await self.page.content()
                return len(html) > 100

            elif action == 'search':
                html = await self.page.content()
                text = step.get('text', '')
                return text.lower() in html.lower()

            elif action == 'verify':
                html = await self.page.content()
                pattern = step.get('pattern', '')
                if pattern:
                    return bool(re.search(pattern, html))
                return True

            else:
                return False

        except Exception as e:
            return False

    async def execute_recipe(self, recipe_id: str) -> Dict[str, Any]:
        """Execute complete recipe"""
        if recipe_id not in self.recipes:
            return {"success": False, "error": f"Recipe {recipe_id} not loaded"}

        recipe = self.recipes[recipe_id]

        print(f"\n{'='*80}")
        print(f"🔄 EXECUTING: {recipe_id}")
        print(f"{'='*80}")

        trace = recipe.get('execution_trace', [])
        passed = 0
        failed = 0

        for step in trace:
            success = await self.execute_step(step)
            status = "✅" if success else "❌"
            step_num = step.get('step', '?')
            desc = step.get('description', '')[:50]

            print(f"{status} Step {step_num:2d}: {desc}")

            if success:
                passed += 1
            else:
                failed += 1

        result = {
            "recipe_id": recipe_id,
            "success": failed == 0,
            "passed": passed,
            "failed": failed,
            "total": len(trace),
        }

        print(f"\n📊 Result: {passed}/{len(trace)} steps passed")
        return result

async def main():
    """Test recipes with debug output"""
    executor = DebugRecipeExecutor(headless=True)
    await executor.start()

    try:
        print("\n" + "█"*80)
        print("HEADLESS EXECUTOR WITH DEBUG OUTPUT")
        print("When selectors fail, shows available alternatives")
        print("█"*80)

        # Load recipes
        recipe_files = [
            Path("/home/phuc/projects/solace-browser/recipes/hackernews-upvote-workflow.recipe.json"),
            Path("/home/phuc/projects/solace-browser/recipes/reddit-upvote-workflow.recipe.json"),
        ]

        print(f"\n1️⃣  LOADING RECIPES")
        for recipe_file in recipe_files:
            if recipe_file.exists():
                recipe = executor.load_recipe(str(recipe_file))
                print(f"   ✅ {recipe['recipe_id']}")

        # Execute recipes
        print(f"\n2️⃣  EXECUTING WITH DEBUG OUTPUT")
        for recipe_id in list(executor.recipes.keys()):
            result = await executor.execute_recipe(recipe_id)
            if not result['success']:
                print(f"\n   💡 Debugging: Check output above for selector alternatives")

    finally:
        await executor.stop()

if __name__ == "__main__":
    asyncio.run(main())
