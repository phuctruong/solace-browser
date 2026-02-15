#!/usr/bin/env python3
"""
Gmail Login - MONITOR REAL USER CLICK
Genius approach: Fill email, pause, user clicks Next, we monitor EVERYTHING
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
print("🔬 GMAIL LOGIN - MONITOR REAL USER INTERACTION")
print("="*80)
print("Strategy: Fill email, YOU click Next, I'll watch and learn!")
print("="*80)
print()

email, password = read_creds()

# Step 1: Navigate
print("Step 1: Navigating to Gmail...")
requests.post(f"{API}/navigate",
              json={"url": "https://accounts.google.com/ServiceLogin?service=mail"},
              timeout=60)
time.sleep(3)

# Step 2: Fill email
print("\nStep 2: Filling email field...")
result = requests.post(f"{API}/fill",
                      json={"selector": "input[type='email']", "text": email},
                      timeout=30)

if result.json().get('success'):
    print(f"  ✅ Email filled: {email}")
else:
    print(f"  ❌ Failed: {result.json()}")
    exit(1)

time.sleep(1)

# Step 3: Take screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"\n📸 Screenshot saved: {screenshot.get('path')}")

# Step 4: Get initial state
print("\nStep 3: Capturing INITIAL state...")
initial_snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
initial_url = initial_snapshot.get('url', '')
initial_console = initial_snapshot.get('console', [])
print(f"  Initial URL: {initial_url}")
print(f"  Initial console messages: {len(initial_console)}")

# Step 5: PAUSE FOR USER
print("\n" + "="*80)
print("⏸️  PAUSED - READY FOR YOU TO CLICK")
print("="*80)
print("\n🖱️  Please do the following:")
print("   1. Look at the browser window (it should be visible)")
print("   2. You should see the email field filled with:", email)
print("   3. Click the 'Next' button with your mouse")
print("   4. Wait for the password page to load")
print("   5. Then come back here and press Enter")
print("\n💡 While you click, I'll be monitoring:")
print("   - Network requests")
print("   - Console logs")
print("   - Page navigation")
print("   - DOM changes")
print("   - Everything!")
print("\n" + "="*80)

input("\n👉 Press Enter AFTER you've clicked Next and the password page loaded...")

# Step 6: Capture what changed
print("\n" + "="*80)
print("🔬 ANALYZING WHAT HAPPENED...")
print("="*80)

time.sleep(2)  # Let everything settle

# Get final state
final_snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
final_url = final_snapshot.get('url', '')
final_console = final_snapshot.get('console', [])

print(f"\n📊 STATE CHANGES:")
print(f"   Before URL: {initial_url}")
print(f"   After URL:  {final_url}")
print(f"   URL changed: {initial_url != final_url}")

print(f"\n📝 CONSOLE ACTIVITY:")
new_console = final_console[len(initial_console):]
if new_console:
    print(f"   New console messages: {len(new_console)}")
    for msg in new_console[-10:]:  # Last 10 messages
        print(f"   - [{msg.get('type')}] {msg.get('text', '')[:100]}")
else:
    print("   No new console messages")

# Check network activity (from final snapshot)
network = final_snapshot.get('network', [])
print(f"\n🌐 NETWORK ACTIVITY:")
print(f"   Total requests: {len(network)}")
if network:
    print("   Recent requests:")
    for req in network[-10:]:  # Last 10 requests
        url = req.get('url', '')
        status = req.get('status', '')
        print(f"   - [{status}] {url[:80]}")

# Analyze page structure
aria_after = final_snapshot.get('aria', [])
print(f"\n🎯 PAGE ANALYSIS:")
print(f"   ARIA nodes: {len(aria_after)}")

# Look for password field
password_fields = [n for n in aria_after if n.get('role') == 'textbox' and
                   'password' in n.get('name', '').lower()]

if password_fields:
    print(f"\n✅ SUCCESS! Found password page!")
    print(f"   Password field: {password_fields[0].get('name')}")
    print(f"   Selector would be: role=textbox[name=\"{password_fields[0].get('name')}\"]")
else:
    print(f"\n⚠️  Didn't find password field yet")
    print(f"   Current ARIA elements:")
    for node in aria_after[:20]:
        if node.get('name'):
            print(f"   - {node.get('role')}: {node.get('name')}")

# Save the monitoring data
monitor_data = {
    "initial_url": initial_url,
    "final_url": final_url,
    "url_changed": initial_url != final_url,
    "new_console_messages": new_console,
    "network_requests": network[-20:] if network else [],
    "final_aria": aria_after[:50],  # First 50 for analysis
    "password_field_found": len(password_fields) > 0
}

with open('artifacts/gmail_monitor_data.json', 'w') as f:
    json.dump(monitor_data, f, indent=2)

print(f"\n💾 Monitoring data saved to: artifacts/gmail_monitor_data.json")

# Take final screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"📸 Final screenshot: {screenshot.get('path')}")

print("\n" + "="*80)
print("🎓 LEARNING COMPLETE!")
print("="*80)
print("\nNow I know exactly what happens when YOU click Next!")
print("I can analyze the data and reproduce it in automation.")

if password_fields:
    print("\n🚀 READY TO AUTOMATE!")
    print("   I can now fill the password and complete the login!")

    cont = input("\n   Continue with password? (y/n): ")

    if cont.lower() == 'y':
        print("\n Step 4: Filling password...")
        pw_field = password_fields[0]
        pw_selector = f"role=textbox[name=\"{pw_field.get('name')}\"]"

        result = requests.post(f"{API}/fill",
                              json={"selector": pw_selector, "text": password},
                              timeout=30)

        if result.json().get('success'):
            print(f"  ✅ Password filled!")

            print("\n  🖱️  Now YOU click the Sign In / Next button")
            print("     Then I'll save the session!")

            input("\n  👉 Press Enter after clicking Sign In...")

            time.sleep(3)

            # Save session
            print("\n💾 Saving session...")
            result = requests.post(f"{API}/save-session", timeout=30).json()
            if result.get('success'):
                print(f"  ✅ Session saved: {result.get('path')}")
                print("\n🎉 NOW you can use headless mode with saved cookies!")

print("\n" + "="*80)
print("✅ MONITORING SESSION COMPLETE")
print("="*80)
