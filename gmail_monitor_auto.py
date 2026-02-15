#!/usr/bin/env python3
"""
Gmail Login - AUTO-MONITOR (no keyboard input needed)
Fills email, then polls to detect when YOU click Next
"""

import requests
import time
import json
import configparser

API = "http://localhost:9222"

def read_creds():
    config = configparser.ConfigParser()
    config.read('credentials.properties')
    return config.get('gmail', 'email'), config.get('gmail', 'password')

print("="*80)
print("🔬 GMAIL LOGIN - AUTO-MONITORING YOUR CLICK")
print("="*80)
print()

email, password = read_creds()

# Navigate
print("1. Navigating to Gmail...")
requests.post(f"{API}/navigate",
              json={"url": "https://accounts.google.com/ServiceLogin?service=mail"},
              timeout=60)
time.sleep(3)

# Fill email
print("\n2. Filling email...")
result = requests.post(f"{API}/fill",
                      json={"selector": "input[type='email']", "text": email},
                      timeout=30)
print(f"  ✅ Email filled: {email}")

# Screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"\n📸 Screenshot: {screenshot.get('path')}")

# Get initial state
snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
initial_url = snapshot.get('url', '')
print(f"\n📍 Current URL: {initial_url[:80]}...")

print("\n" + "="*80)
print("⏸️  WAITING FOR YOU TO CLICK NEXT")
print("="*80)
print("\n🖱️  GO AHEAD - Click the 'Next' button in the browser window!")
print("   I'm watching and will detect when the page changes...")
print("\n" + "="*80)

# Poll for URL change
print("\n🔍 Monitoring for page navigation...")
changed = False
for i in range(60):  # Wait up to 60 seconds
    time.sleep(1)
    try:
        snapshot = requests.get(f"{API}/snapshot", timeout=10).json()
        current_url = snapshot.get('url', '')

        if current_url != initial_url:
            print(f"\n✅ DETECTED NAVIGATION! ({i+1}s)")
            print(f"   New URL: {current_url[:80]}...")
            changed = True
            break

        # Show progress
        if i % 5 == 0 and i > 0:
            print(f"   Still waiting... ({i}s)")

    except Exception as e:
        print(f"   Error checking: {e}")

if not changed:
    print("\n⏱️  Timeout - didn't detect navigation")
    print("   Did you click Next? Check the browser window.")
    exit(1)

# Give it a moment to settle
time.sleep(2)

# Analyze what happened
print("\n" + "="*80)
print("🔬 ANALYZING WHAT HAPPENED")
print("="*80)

final_snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
final_url = final_snapshot.get('url', '')
aria = final_snapshot.get('aria', [])
console_msgs = final_snapshot.get('console', [])
network = final_snapshot.get('network', [])

print(f"\n📊 URL CHANGE:")
print(f"   Before: {initial_url[:70]}...")
print(f"   After:  {final_url[:70]}...")

print(f"\n🌐 NETWORK ACTIVITY:")
print(f"   Total requests captured: {len(network)}")
if network:
    print("   Recent requests:")
    for req in network[-10:]:
        url = req.get('url', '')
        method = req.get('method', 'GET')
        status = req.get('status', '?')
        print(f"   - [{method}] [{status}] {url[:70]}")

print(f"\n📝 CONSOLE:")
print(f"   Messages: {len(console_msgs)}")
if console_msgs:
    for msg in console_msgs[-5:]:
        print(f"   - [{msg.get('type')}] {msg.get('text', '')[:80]}")

print(f"\n🎯 PAGE ANALYSIS:")
print(f"   ARIA nodes: {len(aria)}")

# Look for password field
password_fields = [n for n in aria if n.get('role') == 'textbox' and
                   'password' in n.get('name', '').lower()]

if password_fields:
    print(f"\n✅ SUCCESS - PASSWORD PAGE!")
    pw_field = password_fields[0]
    print(f"   Password field found: {pw_field.get('name')}")
    print(f"   Selector: role=textbox[name=\"{pw_field.get('name')}\"]")

    # Save monitoring data
    monitor_data = {
        "timestamp": time.time(),
        "url_change": {"from": initial_url, "to": final_url},
        "network_requests": network[-20:],
        "console_messages": console_msgs,
        "password_field": pw_field,
        "success": True
    }

    with open('artifacts/gmail_monitor_success.json', 'w') as f:
        json.dump(monitor_data, f, indent=2)

    print(f"\n💾 Monitoring data saved: artifacts/gmail_monitor_success.json")

    # Continue with password?
    print("\n" + "="*80)
    print("🚀 READY FOR PASSWORD")
    print("="*80)
    print("\nI can now fill the password!")
    print("   (This script will exit - run the full login script next)")

else:
    # Check if blocked
    blocked = any('couldn\'t sign' in str(n.get('name', '')).lower() or
                  'not secure' in str(n.get('name', '')).lower()
                  for n in aria)

    if blocked:
        print(f"\n❌ BLOCKED BY GOOGLE")
        print("   Found blocking message in page")
    else:
        print(f"\n⚠️  Unexpected state")
        print("   Top ARIA elements:")
        for node in aria[:15]:
            if node.get('name'):
                print(f"   - {node.get('role')}: {node.get('name')}")

# Final screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"\n📸 Final screenshot: {screenshot.get('path')}")

print("\n" + "="*80)
print("✅ MONITORING COMPLETE")
print("="*80)
