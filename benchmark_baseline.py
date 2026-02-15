#!/usr/bin/env python3
"""
Benchmark current LinkedIn automation performance
Measure: navigation, deletion, addition workflows
"""

import requests
import time
import json

API = "http://localhost:9222"

def timed_operation(name, func):
    """Time an operation and return duration"""
    print(f"\n{'='*70}")
    print(f"⏱️  TIMING: {name}")
    print('='*70)
    start = time.time()
    result = func()
    duration = time.time() - start
    print(f"Duration: {duration:.2f}s")
    return duration, result

def benchmark_navigation():
    """Time navigation to LinkedIn projects page"""
    def navigate():
        result = requests.post(f"{API}/navigate",
                              json={"url": "https://www.linkedin.com/in/me/details/projects/"},
                              timeout=30)
        time.sleep(2)  # Current wait time
        return result.json().get('success')

    duration, success = timed_operation("Navigate to LinkedIn", navigate)
    return {"navigation": duration, "success": success}

def benchmark_aria_snapshot():
    """Time ARIA snapshot extraction"""
    def snapshot():
        result = requests.get(f"{API}/snapshot", timeout=30)
        data = result.json()
        return len(data.get('aria', []))

    duration, count = timed_operation("ARIA Snapshot Extraction", snapshot)
    return {"aria_snapshot": duration, "node_count": count}

def benchmark_screenshot():
    """Time screenshot capture"""
    def screenshot():
        result = requests.get(f"{API}/screenshot", timeout=30)
        return result.json().get('success')

    duration, success = timed_operation("Screenshot Capture", screenshot)
    return {"screenshot": duration, "success": success}

def benchmark_click():
    """Time clicking an element"""
    def click():
        result = requests.post(f"{API}/click",
                              json={"selector": 'role=link[name="Add new project"]'},
                              timeout=30)
        time.sleep(2)  # Current wait time
        return result.json().get('success')

    duration, success = timed_operation("Click Element", click)
    return {"click": duration, "success": success}

def benchmark_form_fill_fast():
    """Time filling form WITHOUT slowly"""
    def fill():
        # Fill name (short text)
        result = requests.post(f"{API}/fill",
                              json={
                                  "selector": 'role=textbox[name="Project name*"]',
                                  "text": "TestProject.com"
                              },
                              timeout=30)
        time.sleep(1)
        return result.json().get('success')

    duration, success = timed_operation("Fill Name (Fast)", fill)
    return {"fill_fast": duration, "success": success}

def benchmark_form_fill_slow():
    """Time filling form WITH slowly"""
    def fill():
        # Fill description (long text with slowly)
        text = "Test description with multiple sentences. " * 5  # ~200 chars
        result = requests.post(f"{API}/fill",
                              json={
                                  "selector": 'role=textbox[name="Description"]',
                                  "text": text,
                                  "slowly": True
                              },
                              timeout=120)
        time.sleep(1)
        return result.json().get('success')

    duration, success = timed_operation("Fill Description (Slowly)", fill)
    return {"fill_slow": duration, "success": success}

def benchmark_delete_workflow():
    """Time complete deletion workflow"""
    def delete():
        # Navigate
        requests.post(f"{API}/navigate",
                     json={"url": "https://www.linkedin.com/in/me/details/projects/"},
                     timeout=30)
        time.sleep(2)

        # Find edit link
        snapshot = requests.get(f"{API}/snapshot", timeout=30).json()

        # Click edit (if any project exists)
        projects = [n for n in snapshot.get('aria', [])
                   if n.get('name', '').startswith('Edit project')]

        if projects:
            project_name = projects[0]['name'].replace('Edit project ', '')
            requests.post(f"{API}/click",
                         json={"selector": f'role=link[name="Edit project {project_name}"]'},
                         timeout=30)
            time.sleep(1.5)

            # Click delete
            requests.post(f"{API}/click",
                         json={"selector": 'role=button[name="Delete"]'},
                         timeout=30)
            time.sleep(1)

            # Confirm
            requests.post(f"{API}/click",
                         json={"selector": 'role=button[name="Delete"]'},
                         timeout=30)
            time.sleep(2)

            return True
        return False

    duration, success = timed_operation("Complete Delete Workflow", delete)
    return {"delete_workflow": duration, "success": success}

def main():
    print("\n" + "="*70)
    print("📊 BASELINE PERFORMANCE BENCHMARK")
    print("="*70)
    print("Measuring current automation speed...")
    print()

    # Check browser
    health = requests.get(f"{API}/health", timeout=10).json()
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        return

    print("✅ Browser ready (headless mode)\n")

    results = {}

    # Run benchmarks
    results.update(benchmark_navigation())
    results.update(benchmark_aria_snapshot())
    results.update(benchmark_screenshot())
    results.update(benchmark_click())
    results.update(benchmark_form_fill_fast())
    results.update(benchmark_form_fill_slow())
    # results.update(benchmark_delete_workflow())  # Skip to avoid deleting real projects

    # Calculate totals
    print("\n" + "="*70)
    print("📈 BASELINE RESULTS")
    print("="*70)

    total_time = sum(v for k, v in results.items() if isinstance(v, (int, float)) and k != 'node_count')

    print(f"\nOperation Timings:")
    print(f"  Navigation:        {results.get('navigation', 0):.2f}s")
    print(f"  ARIA Snapshot:     {results.get('aria_snapshot', 0):.2f}s ({results.get('node_count', 0)} nodes)")
    print(f"  Screenshot:        {results.get('screenshot', 0):.2f}s")
    print(f"  Click Element:     {results.get('click', 0):.2f}s")
    print(f"  Fill (Fast):       {results.get('fill_fast', 0):.2f}s")
    print(f"  Fill (Slowly):     {results.get('fill_slow', 0):.2f}s (~200 chars)")

    print(f"\nTotal measured:    {total_time:.2f}s")

    # Estimate full workflow
    full_add = results.get('navigation', 0) + results.get('click', 0) + \
               results.get('fill_fast', 0) + results.get('fill_slow', 0) * 1.5 + 2

    print(f"\nEstimated full add project: {full_add:.2f}s")
    print(f"Estimated 5 projects:       {full_add * 5:.2f}s")

    # Save results
    with open('benchmark_baseline.json', 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "results": results,
            "total_time": total_time,
            "estimated_full_add": full_add
        }, f, indent=2)

    print("\n✅ Baseline saved to benchmark_baseline.json")

    # Identify bottlenecks
    print("\n" + "="*70)
    print("🔍 BOTTLENECK ANALYSIS")
    print("="*70)

    bottlenecks = []
    if results.get('fill_slow', 0) > 10:
        bottlenecks.append(f"⚠️  Slowly typing: {results.get('fill_slow', 0):.2f}s (MAJOR BOTTLENECK)")
    if results.get('navigation', 0) > 3:
        bottlenecks.append(f"⚠️  Navigation wait: {results.get('navigation', 0):.2f}s")
    if results.get('click', 0) > 3:
        bottlenecks.append(f"⚠️  Click wait: {results.get('click', 0):.2f}s")

    for b in bottlenecks:
        print(b)

    if not bottlenecks:
        print("✅ No major bottlenecks found")

    print("\n" + "="*70)

if __name__ == "__main__":
    main()
