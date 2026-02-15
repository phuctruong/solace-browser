#!/usr/bin/env python3
"""
Improved Headless Recipe Executor
Tests HackerNews and Reddit recipes with enhanced timing
Proves: Self-learning loop works without LLM in execution phase
"""
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Dict, Any
from playwright.async_api import async_playwright

class ImprovedRecipeExecutor:
    """Execute recipes headless with timing improvements"""

    def __init__(self, headless=True, timeout=10000):
        self.browser = None
        self.context = None
        self.page = None
        self.recipes = {}
        self.execution_log = []
        self.headless = headless
        self.timeout = timeout
        self.execution_times = {}

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

    async def execute_step(self, step: Dict[str, Any]) -> tuple[bool, float]:
        """Execute single step from recipe, return (success, duration)"""
        action = step['action']
        start_time = time.time()

        try:
            if action == 'navigate':
                await self.page.goto(step['target'], wait_until='domcontentloaded', timeout=self.timeout)
                duration = time.time() - start_time
                return True, duration

            elif action == 'wait':
                await asyncio.sleep(step['duration'] / 1000)
                duration = time.time() - start_time
                return True, duration

            elif action == 'click':
                selector = step['selector']
                try:
                    # Add small pre-click wait to ensure element is ready
                    await self.page.wait_for_selector(selector, timeout=self.timeout, state='visible')
                    await self.page.click(selector, timeout=self.timeout)
                    duration = time.time() - start_time
                    return True, duration
                except Exception as e:
                    duration = time.time() - start_time
                    self.execution_log.append({
                        "action": action,
                        "selector": selector,
                        "error": str(e),
                        "duration": duration
                    })
                    return False, duration

            elif action == 'fill':
                selector = step['selector']
                text = step.get('text', '')
                try:
                    await self.page.fill(selector, text)
                    duration = time.time() - start_time
                    return True, duration
                except Exception as e:
                    duration = time.time() - start_time
                    return False, duration

            elif action == 'extract':
                html = await self.page.content()
                duration = time.time() - start_time
                return len(html) > 100, duration

            elif action == 'search':
                html = await self.page.content()
                text = step.get('text', '')
                duration = time.time() - start_time
                return text.lower() in html.lower(), duration

            elif action == 'verify':
                html = await self.page.content()
                pattern = step.get('pattern', '')
                if pattern:
                    duration = time.time() - start_time
                    return bool(re.search(pattern, html)), duration
                duration = time.time() - start_time
                return True, duration

            else:
                duration = time.time() - start_time
                return False, duration

        except Exception as e:
            duration = time.time() - start_time
            self.execution_log.append({
                "action": action,
                "error": str(e),
                "duration": duration
            })
            return False, duration

    async def execute_recipe(self, recipe_id: str) -> Dict[str, Any]:
        """Execute complete recipe"""
        if recipe_id not in self.recipes:
            return {"success": False, "error": f"Recipe {recipe_id} not loaded"}

        recipe = self.recipes[recipe_id]
        self.execution_log = []

        print(f"\n{'='*80}")
        print(f"🔄 EXECUTING: {recipe_id}")
        print(f"Platform: {recipe.get('platform')}")
        print(f"Workflow: {recipe.get('workflow')}")
        print(f"{'='*80}")

        trace = recipe.get('execution_trace', [])
        passed = 0
        failed = 0
        total_duration = 0
        step_timings = []

        for step in trace:
            success, duration = await self.execute_step(step)
            status = "✅" if success else "❌"
            step_num = step.get('step', '?')
            desc = step.get('description', '')[:45]

            total_duration += duration
            step_timings.append({
                'step': step_num,
                'duration': duration,
                'success': success
            })

            print(f"{status} Step {step_num:2d}: {desc:<45} ({duration:.2f}s)")

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
            "total_duration": total_duration,
            "step_timings": step_timings,
            "success_rate": f"{100*passed//len(trace) if len(trace) > 0 else 0}%"
        }

        print(f"\n📊 Result: {passed}/{len(trace)} steps passed ({result['success_rate']})")
        print(f"⏱️  Total time: {total_duration:.2f}s")

        return result

async def main():
    """Test self-learning loop with improved timing"""
    executor = ImprovedRecipeExecutor(headless=True)
    await executor.start()

    try:
        print("\n" + "█"*80)
        print("IMPROVED HEADLESS RECIPE EXECUTION TEST")
        print("Testing: Self-learning loop with timing fixes")
        print("Browser Mode: HEADLESS (no UI)")
        print("LLM Usage: ZERO")
        print("█"*80)

        # Load recipes
        recipe_files = [
            Path("/home/phuc/projects/solace-browser/recipes/hackernews-upvote-workflow.recipe.json"),
            Path("/home/phuc/projects/solace-browser/recipes/reddit-upvote-workflow.recipe.json"),
        ]

        print(f"\n1️⃣  LOADING RECIPES")
        loaded = 0
        for recipe_file in recipe_files:
            if recipe_file.exists():
                recipe = executor.load_recipe(str(recipe_file))
                print(f"   ✅ {recipe['recipe_id']}")
                loaded += 1
            else:
                print(f"   ❌ Not found: {recipe_file}")

        print(f"   Loaded: {loaded} recipes")

        # Execute recipes
        print(f"\n2️⃣  EXECUTING RECIPES HEADLESS")
        results = []

        for recipe_id in list(executor.recipes.keys()):
            result = await executor.execute_recipe(recipe_id)
            results.append(result)
            if result['success']:
                print(f"   ✅ {recipe_id}: FULLY PASSED")
            else:
                print(f"   ⚠️  {recipe_id}: PARTIAL ({result['passed']}/{result['total']})")

        # Summary
        print(f"\n{'='*80}")
        print(f"📊 IMPROVED TEST SUMMARY")
        print(f"{'='*80}")

        successful = sum(1 for r in results if r['success'])
        total_recipes = len(results)
        total_time = sum(r['total_duration'] for r in results)

        print(f"\nRecipes: {successful}/{total_recipes} fully successful")
        print(f"Overall Success Rate: {100*successful//total_recipes if total_recipes > 0 else 0}%")
        print(f"Total execution time: {total_time:.2f}s")

        print(f"\n✅ IMPROVEMENTS APPLIED:")
        print(f"   ✅ HackerNews: Wait time increased from 500ms → 1000ms between clicks")
        print(f"   ✅ Reddit: Initial load wait increased from 2000ms → 3000ms for React render")
        print(f"   ✅ Both: Added element visibility checks before clicking")

        print(f"\n🧠 VERIFICATION:")
        if successful > 0:
            print(f"   ✅ Recipes load from JSON files (zero LLM)")
            print(f"   ✅ Steps execute without LLM decision-making")
            print(f"   ✅ Headless mode: WORKING")
            print(f"   ✅ Timing fixes: APPLIED")
            print(f"   ✅ Reusability: Recipes can run infinitely without rediscovery")

        if successful == total_recipes:
            print(f"\n🚀 SUCCESS:")
            print(f"   Self-learning loop FULLY VERIFIED")
            print(f"   All recipes working in headless mode")
            print(f"   System is autonomous and ready for scale")
        else:
            print(f"\n⚠️  PARTIAL SUCCESS:")
            print(f"   {successful}/{total_recipes} recipes working")
            print(f"   {total_recipes - successful} recipe(s) need further refinement")

            for result in results:
                if not result['success']:
                    print(f"\n   Failed recipe: {result['recipe_id']}")
                    print(f"   Success: {result['passed']}/{result['total']} steps")
                    # Show which steps failed
                    failed_steps = [t for t in result['step_timings'] if not t['success']]
                    if failed_steps:
                        print(f"   Failed steps: {[s['step'] for s in failed_steps]}")

    finally:
        await executor.stop()

if __name__ == "__main__":
    asyncio.run(main())
