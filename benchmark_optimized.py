#!/usr/bin/env python3
"""
Benchmark OPTIMIZED LinkedIn automation performance
Compare to baseline
"""

import requests
import time
import json

API = "http://localhost:9222"

def timed_operation(name, func):
    """Time an operation"""
    print(f"\n⏱️  {name}")
    start = time.time()
    result = func()
    duration = time.time() - start
    print(f"   Duration: {duration:.2f}s")
    return duration, result

def main():
    print("\n" + "="*70)
    print("⚡ OPTIMIZED PERFORMANCE BENCHMARK")
    print("="*70)

    # Check browser
    health = requests.get(f"{API}/health", timeout=10).json()
    if health.get('status') != 'ok':
        print("❌ Browser not ready")
        return

    print("✅ Browser ready\n")

    results = {}

    # Navigation (no sleep after)
    def navigate():
        requests.post(f"{API}/navigate",
                     json={"url": "https://www.linkedin.com/in/me/details/projects/"},
                     timeout=30)
        # NO SLEEP - optimized!
        return True

    duration, _ = timed_operation("Navigate (optimized)", navigate)
    results['navigation'] = duration

    # ARIA snapshot
    def snapshot():
        result = requests.get(f"{API}/snapshot", timeout=30)
        return len(result.json().get('aria', []))

    duration, count = timed_operation("ARIA Snapshot", snapshot)
    results['aria_snapshot'] = duration
    results['node_count'] = count

    # Screenshot
    def screenshot():
        requests.get(f"{API}/screenshot", timeout=30)
        return True

    duration, _ = timed_operation("Screenshot", screenshot)
    results['screenshot'] = duration

    # Click (minimal wait)
    def click():
        requests.post(f"{API}/click",
                     json={"selector": 'role=link[name="Add new project"]'},
                     timeout=30)
        time.sleep(0.5)  # Reduced from 2s
        return True

    duration, _ = timed_operation("Click (optimized wait)", click)
    results['click'] = duration

    # Fill fast
    def fill_fast():
        requests.post(f"{API}/fill",
                     json={
                         "selector": 'role=textbox[name="Project name*"]',
                         "text": "TestProject.com"
                     },
                     timeout=30)
        # NO SLEEP
        return True

    duration, _ = timed_operation("Fill Name (fast)", fill_fast)
    results['fill_fast'] = duration

    # Fill slowly with OPTIMIZED delay (15ms instead of 50ms)
    def fill_slow():
        text = "Test description with multiple sentences. " * 5  # ~200 chars
        requests.post(f"{API}/fill",
                     json={
                         "selector": 'role=textbox[name="Description"]',
                         "text": text,
                         "slowly": True,
                         "delay": 15  # OPTIMIZED from 50ms
                     },
                     timeout=120)
        # NO SLEEP
        return True

    duration, _ = timed_operation("Fill Description (optimized slowly)", fill_slow)
    results['fill_slow'] = duration

    # Calculate totals
    print("\n" + "="*70)
    print("📊 OPTIMIZED RESULTS")
    print("="*70)

    total_time = sum(v for k, v in results.items() if isinstance(v, (int, float)) and k != 'node_count')

    print(f"\nOperation Timings:")
    print(f"  Navigation:        {results.get('navigation', 0):.2f}s")
    print(f"  ARIA Snapshot:     {results.get('aria_snapshot', 0):.2f}s")
    print(f"  Screenshot:        {results.get('screenshot', 0):.2f}s")
    print(f"  Click Element:     {results.get('click', 0):.2f}s")
    print(f"  Fill (Fast):       {results.get('fill_fast', 0):.2f}s")
    print(f"  Fill (Slowly):     {results.get('fill_slow', 0):.2f}s")

    print(f"\nTotal measured:    {total_time:.2f}s")

    # Load baseline for comparison
    try:
        with open('benchmark_baseline.json', 'r') as f:
            baseline = json.load(f)

        print("\n" + "="*70)
        print("📈 PERFORMANCE COMPARISON")
        print("="*70)

        baseline_results = baseline['results']
        print(f"\n{'Operation':<20} {'Baseline':<10} {'Optimized':<10} {'Speedup':<10}")
        print("-" * 55)

        for key in ['navigation', 'aria_snapshot', 'screenshot', 'click', 'fill_fast', 'fill_slow']:
            if key in baseline_results and key in results:
                b = baseline_results[key]
                o = results[key]
                speedup = b / o if o > 0 else 0
                print(f"{key:<20} {b:>8.2f}s  {o:>8.2f}s  {speedup:>8.2f}x")

        baseline_total = baseline['total_time']
        speedup_total = baseline_total / total_time if total_time > 0 else 0

        print("-" * 55)
        print(f"{'TOTAL':<20} {baseline_total:>8.2f}s  {total_time:>8.2f}s  {speedup_total:>8.2f}x")

        # Estimated full workflow
        full_add_optimized = results.get('navigation', 0) + results.get('click', 0) + \
                           results.get('fill_fast', 0) + results.get('fill_slow', 0) * 1.5 + 0.5

        full_add_baseline = baseline.get('estimated_full_add', 0)

        print(f"\nEstimated full add project:")
        print(f"  Baseline:  {full_add_baseline:.2f}s")
        print(f"  Optimized: {full_add_optimized:.2f}s")
        print(f"  Speedup:   {full_add_baseline/full_add_optimized:.2f}x")

        print(f"\nEstimated 5 projects:")
        print(f"  Baseline:  {full_add_baseline * 5:.2f}s ({full_add_baseline * 5 / 60:.1f} min)")
        print(f"  Optimized: {full_add_optimized * 5:.2f}s ({full_add_optimized * 5 / 60:.1f} min)")
        print(f"  Time saved: {(full_add_baseline - full_add_optimized) * 5:.2f}s")

    except FileNotFoundError:
        print("\n⚠️  No baseline found for comparison")

    # Save results
    with open('benchmark_optimized.json', 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "results": results,
            "total_time": total_time
        }, f, indent=2)

    print("\n✅ Results saved to benchmark_optimized.json")

if __name__ == "__main__":
    main()
