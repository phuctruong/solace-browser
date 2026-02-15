#!/usr/bin/env python3
"""Add remaining 2 projects"""

import requests
import time

API = "http://localhost:9222"

PROJECTS = [
    {
        "name": "PZip.com",
        "description": "Universal compression tool that helps developers, data teams, and researchers reduce file sizes across all formats.\n\nImpact:\n• Beats industry standard LZMA on 91.4% of test cases\n• 4.075x average compression ratio\n• Open-source with commercial support available",
        "url": "https://pzip.com"
    },
    {
        "name": "Phuc.net",
        "description": "Solo founder ecosystem hub showcasing 5 verified AI products built in public with full transparency.\n\nImpact:\n• 100% SWE-bench verified (6/6 industry benchmarks)\n• Community-supported via Ko-fi tips\n• Harsh QA culture ensures quality over hype",
        "url": "https://phuc.net"
    }
]

def add_project(project):
    print("\n" + "=" * 70)
    print(f"Adding: {project['name']}")
    print("=" * 70)
    
    # Navigate
    requests.post(f"{API}/navigate",
                  json={"url": "https://www.linkedin.com/in/me/details/projects/"},
                  timeout=30)
    time.sleep(2)
    
    # Click Add new project
    requests.post(f"{API}/click",
                  json={"selector": 'role=link[name="Add new project"]'},
                  timeout=30)
    time.sleep(2)
    
    # Fill name
    print(f"  Filling name: {project['name']}")
    requests.post(f"{API}/fill",
                  json={
                      "selector": 'role=textbox[name="Project name*"]',
                      "text": project['name']
                  },
                  timeout=30)
    time.sleep(1)
    
    # Fill description
    print(f"  Filling description ({len(project['description'])} chars)")
    requests.post(f"{API}/fill",
                  json={
                      "selector": 'role=textbox[name="Description"]',
                      "text": project['description'],
                      "slowly": True
                  },
                  timeout=120)
    time.sleep(1)
    
    # Save
    print("  Saving...")
    result = requests.post(f"{API}/click",
                          json={"selector": 'role=button[name="Save"]'},
                          timeout=30)
    
    if result.json().get('success'):
        time.sleep(3)
        print(f"  ✅ Added {project['name']}")
        return True
    else:
        print(f"  ⚠️  Save failed")
        return False

# Add both projects
added = 0
for project in PROJECTS:
    if add_project(project):
        added += 1
    time.sleep(2)

print("\n" + "=" * 70)
print(f"✅ Added {added}/{len(PROJECTS)} projects")
print("=" * 70)

