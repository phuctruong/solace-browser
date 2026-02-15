#!/usr/bin/env python3
"""
Optimized project addition - Performance tuned version
Removes arbitrary sleeps, uses faster typing, minimal waits
"""

import requests
import time

API = "http://localhost:9222"

PROJECT = {
    "name": "TestOptimized.com",
    "description": "Performance test project with optimized automation workflow. " * 3,
    "url": "https://test.com"
}

def add_project_optimized(project):
    """Add project with optimized timing"""
    print(f"Adding: {project['name']}")
    start = time.time()

    # Navigate (no sleep after - page ready when returns)
    requests.post(f"{API}/navigate",
                  json={"url": "https://www.linkedin.com/in/me/details/projects/"},
                  timeout=30)

    # Click Add new project (no sleep after)
    requests.post(f"{API}/click",
                  json={"selector": 'role=link[name="Add new project"]'},
                  timeout=30)

    # Small wait for modal to appear (modal animation)
    time.sleep(0.5)  # Reduced from 2s

    # Fill name (fast)
    requests.post(f"{API}/fill",
                  json={
                      "selector": 'role=textbox[name="Project name*"]',
                      "text": project['name']
                  },
                  timeout=30)

    # Fill description (OPTIMIZED: 15ms delay instead of 50ms)
    requests.post(f"{API}/fill",
                  json={
                      "selector": 'role=textbox[name="Description"]',
                      "text": project['description'],
                      "slowly": True,
                      "delay": 15  # 3.3x faster than default 50ms
                  },
                  timeout=120)

    # Save
    requests.post(f"{API}/click",
                  json={"selector": 'role=button[name="Save"]'},
                  timeout=30)

    # Wait for save to complete (page updates)
    time.sleep(1)  # Reduced from 3s

    duration = time.time() - start
    print(f"  Completed in {duration:.2f}s")
    return duration

def main():
    print("="*70)
    print("🚀 OPTIMIZED PROJECT ADDITION")
    print("="*70)

    # Add project
    duration = add_project_optimized(PROJECT)

    print(f"\n✅ Total time: {duration:.2f}s")
    print(f"   (Estimated baseline: ~29s)")
    print(f"   Speedup: {29/duration:.1f}x")

if __name__ == "__main__":
    main()
