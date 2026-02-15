#!/usr/bin/env python3
"""Add one project using role-based selectors"""

import requests
import time

API = "http://localhost:9222"

PROJECT = {
    "name": "SolaceAgi.com",
    "description": "AI decision-making platform serving enterprise teams who need verified, explainable recommendations instead of black-box outputs.\n\nImpact:\n• 65,537+ decision templates across finance, healthcare, legal\n• 99.3% accuracy on complex reasoning tasks\n• Used by teams replacing costly consultant hours",
    "url": "https://solaceagi.com"
}

print("=" * 70)
print(f"Adding: {PROJECT['name']}")
print("=" * 70)

# Navigate to projects
print("\n1. Navigate to projects...")
requests.post(f"{API}/navigate",
              json={"url": "https://www.linkedin.com/in/me/details/projects/"},
              timeout=30)
time.sleep(2)

# Click Add new project
print("2. Click 'Add new project'...")
requests.post(f"{API}/click",
              json={"selector": 'role=link[name="Add new project"]'},
              timeout=30)
time.sleep(2)

# Fill project name using role selector
print(f"3. Fill project name: {PROJECT['name']}")
result = requests.post(f"{API}/fill",
                      json={
                          "selector": 'role=textbox[name="Project name*"]',
                          "text": PROJECT['name']
                      },
                      timeout=30)
print(f"   Name: {result.json().get('success')}")
time.sleep(1)

# Fill description
print(f"4. Fill description ({len(PROJECT['description'])} chars)")
result = requests.post(f"{API}/fill",
                      json={
                          "selector": 'role=textbox[name="Description"]',
                          "text": PROJECT['description'],
                          "slowly": True
                      },
                      timeout=120)
print(f"   Description: {result.json().get('success')}")
time.sleep(1)

# Take screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"\n📸 Screenshot: {screenshot.get('path')}")

# Try to find and click Save button
print("\n5. Click Save...")
save_selectors = [
    'role=button[name="Save"]',
    'role=button[name=/save/i]',
    "button:has-text('Save')"
]

saved = False
for selector in save_selectors:
    result = requests.post(f"{API}/click",
                          json={"selector": selector},
                          timeout=30)
    if result.json().get('success'):
        print(f"   ✓ Clicked Save")
        saved = True
        break

if saved:
    time.sleep(3)
    print(f"\n✅ Added {PROJECT['name']}!")
else:
    print("\n⚠️  Save button not found - check screenshot")

