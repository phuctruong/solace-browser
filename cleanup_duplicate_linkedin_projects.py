#!/usr/bin/env python3
"""
Delete old duplicate LinkedIn projects (technical jargon versions)
Keep only the new HR-approved domain-named versions
"""

import requests
import time

BROWSER_API = "http://localhost:9222"

# Old projects to delete (will be listed on profile)
OLD_PROJECTS_TO_DELETE = [
    "STILLWATER OS",
    "SOLACEAGI",
    "PZIP",
    "PHUCNET",
    "IF-THEORY"
]

def navigate(url):
    """Navigate to URL"""
    response = requests.post(f"{BROWSER_API}/navigate",
                            json={"url": url},
                            timeout=30)
    return response.json()

def click(selector):
    """Click element"""
    response = requests.post(f"{BROWSER_API}/click",
                            json={"selector": selector},
                            timeout=30)
    return response.json()

def delete_project_by_name(project_name):
    """Delete a LinkedIn project by its name"""
    print(f"\n{'='*60}")
    print(f"Deleting project: {project_name}")
    print('='*60)

    # Navigate to projects page
    print("1. Navigating to projects page...")
    result = navigate("https://www.linkedin.com/in/me/details/projects/")
    if not result.get('success'):
        print(f"❌ Failed to navigate: {result}")
        return False
    time.sleep(1)

    # Find and click edit button for this specific project
    # LinkedIn uses data-test-id for project cards
    # Each project has an edit icon button
    print(f"2. Looking for '{project_name}' edit button...")

    # Try to click the pencil icon for this project
    # The selector pattern for editing a specific project
    selectors_to_try = [
        f"button[aria-label*='Edit {project_name}']",
        f"a[href*='/edit/forms/project/'][href*='{project_name.lower().replace(' ', '-')}']",
        # Generic - will need to identify by position
        "button[aria-label^='Edit ']",
    ]

    # For now, let's use a simpler approach:
    # Navigate directly to projects list and manually delete
    print("3. Using manual approach - navigate and delete...")

    # Just provide instructions for now - LinkedIn's dynamic IDs make this tricky
    print(f"""
    📋 Manual Steps Required:
    1. On LinkedIn projects page
    2. Find project titled: "{project_name}"
    3. Click the pencil/edit icon
    4. Click Delete
    5. Confirm deletion
    """)

    return True

def main():
    print("🗑️  LinkedIn Project Cleanup")
    print("="*60)
    print("Deleting old projects (technical jargon)")
    print("Keeping new projects (HR-approved domain names)")
    print()

    # Check browser health
    try:
        health = requests.get(f"{BROWSER_API}/health", timeout=10).json()
        if health.get('status') != 'ok':
            print("❌ Browser server not healthy")
            return
    except Exception as e:
        print(f"❌ Browser server not running: {e}")
        return

    print("✅ Browser server ready\n")

    # Navigate to projects page first
    print("Navigating to LinkedIn projects page...")
    result = navigate("https://www.linkedin.com/in/me/details/projects/")
    if not result.get('success'):
        print(f"❌ Failed: {result}")
        return

    time.sleep(2)

    # Take screenshot to see current state
    screenshot = requests.get(f"{BROWSER_API}/screenshot", timeout=30).json()
    print(f"📸 Screenshot: {screenshot.get('path')}")
    print()

    print("="*60)
    print("OLD PROJECTS TO DELETE:")
    print("="*60)
    for i, proj in enumerate(OLD_PROJECTS_TO_DELETE, 1):
        print(f"{i}. {proj}")

    print("\n" + "="*60)
    print("NEW PROJECTS TO KEEP:")
    print("="*60)
    new_projects = [
        "Stillwater.com",
        "SolaceAgi.com",
        "PZip.com",
        "IFTheory.com",
        "Phuc.net"
    ]
    for i, proj in enumerate(new_projects, 1):
        print(f"{i}. {proj}")

    print("\n" + "="*60)
    print("⚠️  Manual deletion required - LinkedIn has dynamic IDs")
    print("Use browser GUI to delete old projects")
    print("="*60)

if __name__ == "__main__":
    main()
