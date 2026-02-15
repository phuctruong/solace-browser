#!/usr/bin/env python3
"""Quick test: Can we open and fill one project form?"""

import requests
import time

API = "http://localhost:9222"

print("Step 1: Navigate to projects page...")
requests.post(f"{API}/navigate", 
              json={"url": "https://www.linkedin.com/in/me/details/projects/"},
              timeout=30)
time.sleep(3)

print("Step 2: Click 'Add new project' link...")
result = requests.post(f"{API}/click",
                      json={"selector": 'role=link[name="Add new project"]'},
                      timeout=30)
print(f"   Click result: {result.json()}")

if result.json().get('success'):
    time.sleep(2)
    
    # Take screenshot of form
    print("Step 3: Screenshot of form...")
    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
    print(f"   Screenshot: {screenshot.get('path')}")
    
    # Get ARIA snapshot to see form fields
    print("Step 4: Get form field names from ARIA...")
    snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
    
    # Find all textbox/input elements
    textboxes = [n for n in snapshot.get('aria', []) 
                 if n.get('role') in ['textbox', 'combobox'] 
                 and n.get('name')]
    
    print(f"\n   Found {len(textboxes)} form fields:")
    for t in textboxes[:10]:  # Show first 10
        print(f"   - {t['ref']}: {t['role']} - {t['name']}")
        
    print("\n✅ Form opened successfully!")
else:
    print("❌ Could not open form")
    
