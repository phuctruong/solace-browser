#!/usr/bin/env python3
# Diagram: 01-triangle-architecture
"""
Prime Recipe Replay Engine
Executes saved recipes automatically - zero manual clicking needed
"""

import json
import logging
import sys
import time
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

# Browser server endpoint
BROWSER_API = "http://localhost:8888"

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
        logger.info("Note: %s", note)
        return True

    logger.info("%s: %s", action_type.upper(), target[:50] if target else 'N/A')

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
            logger.error("Unknown action type: %s", action_type)
            return False

    except requests.Timeout:
        logger.error("Timeout after %ds - server may be hung", REQUEST_TIMEOUT)
        return False
    except requests.RequestException as e:
        logger.error("Request failed: %s", e)
        return False

    # Check success
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            logger.info("Action succeeded")
            return True
        else:
            logger.error("Action failed: %s", result.get('error', 'Unknown error'))
            return False
    else:
        logger.error("HTTP %d", response.status_code)
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

        logger.info("Evidence collected: %s", evidence['url'])
        return evidence

    except (requests.RequestException, OSError, KeyError, ValueError) as e:
        logger.warning("Evidence collection failed: %s", e)
        return {}

def replay_recipe(recipe_path):
    """
    Replay a saved recipe

    Args:
        recipe_path: Path to recipe JSON file

    Returns:
        success: Boolean indicating if all actions succeeded
    """
    logger.info("=" * 80)
    logger.info("PRIME RECIPE REPLAY ENGINE")
    logger.info("=" * 80)

    # Load recipe
    recipe_file = Path(recipe_path)
    if not recipe_file.exists():
        logger.error("Recipe not found: %s", recipe_path)
        return False

    with open(recipe_file, 'r') as f:
        recipe = json.load(f)

    logger.info("Recipe: %s", recipe.get('recipe_id'))
    logger.info("Description: %s", recipe.get('metadata', {}).get('title', 'N/A'))
    logger.info("Actions: %d", len(recipe.get('execution_trace', [])))

    # Check browser server
    try:
        health = requests.get(f"{BROWSER_API}/health", timeout=REQUEST_TIMEOUT).json()
        if health.get('status') != 'ok':
            logger.error("Browser server not healthy")
            return False
        logger.info("Browser server ready")
    except (requests.RequestException, OSError, ConnectionError) as e:
        logger.error("Browser server not running: %s", e)
        logger.error("Start with: python persistent_browser_server.py")
        return False

    # Execute actions with global timeout
    execution_trace = recipe.get('execution_trace', [])
    success_count = 0
    start_time = time.time()

    for i, action in enumerate(execution_trace, 1):
        # Safety check - prevent runaway execution
        elapsed = time.time() - start_time
        if elapsed > MAX_EXECUTION_TIME:
            logger.error(
                "Recipe exceeded max execution time (%ds). Completed %d/%d steps",
                MAX_EXECUTION_TIME, i - 1, len(execution_trace),
            )
            return False

        step = action.get('step', i)
        logger.info("[%d/%d] Step %s", i, len(execution_trace), step)

        # Show reasoning if present
        if 'reasoning' in action:
            logger.debug("Reasoning: %s", action['reasoning'])

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
                logger.error("Recipe failed at step %s", step)
                return False

        # Small delay between actions (smart waiting)
        time.sleep(0.2)

    # Final evidence collection
    logger.info("=" * 80)
    logger.info("FINAL VERIFICATION")
    logger.info("=" * 80)
    final_evidence = collect_evidence()

    # Summary
    logger.info("=" * 80)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 80)
    logger.info("Actions executed: %d/%d", success_count, len(execution_trace))
    logger.info("Success rate: %.1f%%", success_count / len(execution_trace) * 100)

    if success_count == len(execution_trace):
        logger.info("RECIPE REPLAY COMPLETE")
        return True
    else:
        logger.warning("Some actions failed")
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
