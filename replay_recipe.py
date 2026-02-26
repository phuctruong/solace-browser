#!/usr/bin/env python3
"""
Prime Recipe Replay Engine
Executes saved recipes automatically - zero manual clicking needed
"""

import json
import sys
import time
import requests
from pathlib import Path

# Browser server endpoint
BROWSER_API = "http://localhost:9222"

# Safety limits
REQUEST_TIMEOUT = 30  # seconds - prevent infinite hangs
MAX_EXECUTION_TIME = 600  # 10 minutes max for entire recipe

def execute_action(action):
    """Execute a single recipe action"""
    action_type = action.get('type')
    target = action.get('target')
    value = action.get('value', '')

    # Handle comment/note actions (no execution needed)
    if action_type == 'comment' or action_type == 'note':
        note = action.get('note', action.get('value', ''))
        print(f"  📝 Note: {note}")
        return True

    print(f"  ⚡ {action_type.upper()}: {target[:50] if target else 'N/A'}...")

    try:
        if action_type == 'navigate':
            response = requests.post(f"{BROWSER_API}/navigate",
                json={"url": target}, timeout=REQUEST_TIMEOUT)

        elif action_type == 'click':
            response = requests.post(f"{BROWSER_API}/click",
                json={"selector": target}, timeout=REQUEST_TIMEOUT)

        elif action_type == 'fill' or action_type == 'type':
            response = requests.post(f"{BROWSER_API}/fill",
                json={"selector": target, "text": value}, timeout=REQUEST_TIMEOUT)

        else:
            print(f"  ❌ Unknown action type: {action_type}")
            return False

    except requests.Timeout:
        print(f"  ❌ Timeout after {REQUEST_TIMEOUT}s - server may be hung")
        return False
    except requests.RequestException as e:
        print(f"  ❌ Request failed: {e}")
        return False

    # Check success
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"  ✓ Success")
            return True
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
            return False
    else:
        print(f"  ❌ HTTP {response.status_code}")
        return False

def collect_evidence():
    """Collect evidence that actions worked"""
    try:
        # Get current status
        status_response = requests.get(f"{BROWSER_API}/status", timeout=REQUEST_TIMEOUT)
        status = status_response.json()

        # Take screenshot
        screenshot_response = requests.get(f"{BROWSER_API}/screenshot", timeout=REQUEST_TIMEOUT)
        screenshot = screenshot_response.json()

        evidence = {
            "url": status.get('url'),
            "title": status.get('title'),
            "screenshot": screenshot.get('path'),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"  📊 Evidence: {evidence['url']}")
        return evidence

    except Exception as e:
        print(f"  ⚠️  Evidence collection failed: {e}")
        return {}

def replay_recipe(recipe_path):
    """
    Replay a saved recipe

    Args:
        recipe_path: Path to recipe JSON file

    Returns:
        success: Boolean indicating if all actions succeeded
    """
    print("=" * 80)
    print("🎬 PRIME RECIPE REPLAY ENGINE")
    print("=" * 80)

    # Load recipe
    recipe_file = Path(recipe_path)
    if not recipe_file.exists():
        print(f"❌ Recipe not found: {recipe_path}")
        return False

    with open(recipe_file, 'r') as f:
        recipe = json.load(f)

    print(f"📖 Recipe: {recipe.get('recipe_id')}")
    print(f"📝 Description: {recipe.get('metadata', {}).get('title', 'N/A')}")
    print(f"🎯 Actions: {len(recipe.get('execution_trace', []))}")
    print()

    # Check browser server
    try:
        health = requests.get(f"{BROWSER_API}/health", timeout=REQUEST_TIMEOUT).json()
        if health.get('status') != 'ok':
            print("❌ Browser server not healthy")
            return False
        print("✓ Browser server ready")
        print()
    except Exception as e:
        print(f"❌ Browser server not running: {e}")
        print("   Start with: python persistent_browser_server.py")
        return False

    # Execute actions with global timeout
    execution_trace = recipe.get('execution_trace', [])
    success_count = 0
    start_time = time.time()

    for i, action in enumerate(execution_trace, 1):
        # Safety check - prevent runaway execution
        elapsed = time.time() - start_time
        if elapsed > MAX_EXECUTION_TIME:
            print(f"\n❌ Recipe exceeded max execution time ({MAX_EXECUTION_TIME}s)")
            print(f"   Completed {i-1}/{len(execution_trace)} steps")
            return False

        step = action.get('step', i)
        print(f"[{i}/{len(execution_trace)}] Step {step}")

        # Show reasoning if present
        if 'reasoning' in action:
            print(f"  💭 {action['reasoning']}")

        # Execute action
        success = execute_action(action)

        if success:
            success_count += 1

            # Collect evidence if specified
            if action.get('evidence'):
                evidence = collect_evidence()
        else:
            # Action failed - check if we should continue
            if not recipe.get('continue_on_error', False):
                print(f"\n❌ Recipe failed at step {step}")
                return False

        # Small delay between actions (smart waiting)
        time.sleep(0.2)
        print()

    # Final evidence collection
    print("=" * 80)
    print("📊 FINAL VERIFICATION")
    print("=" * 80)
    final_evidence = collect_evidence()

    # Summary
    print()
    print("=" * 80)
    print("📈 EXECUTION SUMMARY")
    print("=" * 80)
    print(f"✓ Actions executed: {success_count}/{len(execution_trace)}")
    print(f"✓ Success rate: {success_count/len(execution_trace)*100:.1f}%")

    if success_count == len(execution_trace):
        print(f"✅ RECIPE REPLAY COMPLETE")
        return True
    else:
        print(f"⚠️  Some actions failed")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python replay_recipe.py <recipe.json>")
        print()
        print("Available recipes:")
        recipes_dir = Path("data/default/recipes")
        if recipes_dir.exists():
            for recipe_file in sorted(recipes_dir.glob("*.json")):
                print(f"  - {recipe_file.name}")
        sys.exit(1)

    recipe_path = sys.argv[1]
    success = replay_recipe(recipe_path)
    sys.exit(0 if success else 1)
