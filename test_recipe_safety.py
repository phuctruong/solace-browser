#!/usr/bin/env python3
"""
Test recipe safety fixes - verify timeouts work
"""
import subprocess
import time
import signal
import sys

def test_timeout_protection():
    """Test that recipe times out gracefully when server is down"""
    print("🔬 Testing Recipe Safety Timeouts")
    print("=" * 60)

    # Test 1: Server not running - should timeout quickly
    print("\n[Test 1] Server Down - Should timeout in 30s")
    print("-" * 60)

    # Create minimal test recipe
    test_recipe = {
        "recipe_id": "safety-test",
        "execution_trace": [
            {
                "step": 1,
                "type": "navigate",
                "target": "https://example.com",
                "reasoning": "Test timeout behavior"
            }
        ]
    }

    # Write test recipe
    import json
    with open('/tmp/test_safety.recipe.json', 'w') as f:
        json.dump(test_recipe, f)

    # Run replay with timeout
    start = time.time()
    try:
        result = subprocess.run(
            ['python3', 'replay_recipe.py', '/tmp/test_safety.recipe.json'],
            timeout=35,  # Should complete before this (30s request timeout)
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start

        print(f"Elapsed: {elapsed:.1f}s")
        print(f"Exit code: {result.returncode}")

        # Check for timeout message in output
        if "Timeout" in result.stdout or "not running" in result.stdout:
            print("✅ PASS - Graceful timeout detected")
            print(f"Output: {result.stdout[:200]}")
            return True
        else:
            print("❌ FAIL - No timeout message found")
            print(f"Output: {result.stdout[:200]}")
            return False

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"❌ FAIL - Process didn't timeout (ran {elapsed:.1f}s)")
        return False

if __name__ == "__main__":
    print("\n🛡️  Recipe Safety Test Suite")
    print("=" * 60)
    print("Testing protections added to prevent system freeze")
    print()

    # Ensure server is NOT running for this test
    subprocess.run(['pkill', '-f', 'persistent_browser_server'],
                   stderr=subprocess.DEVNULL)
    time.sleep(1)

    success = test_timeout_protection()

    print("\n" + "=" * 60)
    if success:
        print("✅ SAFETY VERIFIED - Timeouts working correctly")
        sys.exit(0)
    else:
        print("❌ SAFETY ISSUE - Review timeout implementation")
        sys.exit(1)
