#!/usr/bin/env python3
"""
Gmail Login - Headed Mode with Full Recording
Records network calls, interactions, and creates recipe
"""

import requests
import time
import json
import configparser
from datetime import datetime
from pathlib import Path

API = "http://localhost:9222"

def read_credentials():
    config = configparser.ConfigParser()
    config.read('credentials.properties')
    return config.get('gmail', 'email'), config.get('gmail', 'password')

# Recipe storage
recipe = {
    "recipe_id": "gmail-login-oauth-flow",
    "created_at": datetime.now().isoformat(),
    "mode": "headed",
    "reasoning": {
        "discovery": "Google blocks headless Chrome aggressively. Strategy: Login once in headed mode, save session, replay in headless.",
        "network_tracking": "Recording all HTTP calls to understand OAuth flow",
        "llm_learnings": "Headed mode for initial login, then headless with saved session is the reliable pattern for Google services"
    },
    "execution_trace": [],
    "portals": {},
    "next_ai_instructions": "Use saved session cookies for headless automation. Refresh cookies periodically."
}

def record_step(step_name, action, details=None):
    """Record each step in the recipe"""
    step = {
        "timestamp": datetime.now().isoformat(),
        "step": step_name,
        "action": action,
    }
    if details:
        step["details"] = details
    recipe["execution_trace"].append(step)
    print(f"\n📝 Recorded: {step_name}")

print("="*70)
print("🔐 GMAIL LOGIN - HEADED MODE (WITH RECORDING)")
print("="*70)
print("Strategy: Login in headed mode, track everything, save recipe + session")
print()

email, password = read_credentials()
print(f"📧 Email: {email}")
print(f"🔑 Password: {'*' * len(password)}\n")

# Step 1: Navigate to Gmail
print("Step 1: Navigate to Gmail...")
start_time = time.time()
result = requests.post(f"{API}/navigate",
                      json={"url": "https://accounts.google.com/ServiceLogin?service=mail"},
                      timeout=60)

nav_time = time.time() - start_time
record_step("Navigate to Gmail", "navigate", {
    "url": "https://accounts.google.com/ServiceLogin?service=mail",
    "duration": nav_time,
    "final_url": result.json().get('url')
})

time.sleep(3)

# Step 2: Screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"📸 Screenshot: {screenshot.get('path')}")
record_step("Screenshot - Login page", "screenshot", {"path": screenshot.get('path')})

# Step 3: Get ARIA snapshot
print("\nStep 2: Get ARIA snapshot...")
snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
aria = snapshot.get('aria', [])
print(f"  Found {len(aria)} ARIA nodes")

# Find email field
textboxes = [n for n in aria if n.get('role') == 'textbox']
email_field = None
for tb in textboxes:
    name = tb.get('name', '').lower()
    if 'email' in name or 'phone' in name:
        email_field = tb
        break

if not email_field:
    print("❌ Could not find email field")
    print("Available textboxes:")
    for tb in textboxes:
        print(f"  - {tb.get('name')}")
else:
    print(f"✅ Found email field: {email_field.get('name')}")

    # Step 4: Fill email
    print("\nStep 3: Fill email...")
    email_selector = f"role=textbox[name=\"{email_field.get('name')}\"]"

    result = requests.post(f"{API}/fill",
                          json={"selector": email_selector, "text": email},
                          timeout=60)

    if result.json().get('success'):
        print(f"  ✅ Email filled!")
        record_step("Fill email", "fill", {
            "selector": email_selector,
            "field": email_field.get('name')
        })
    else:
        print(f"  ❌ Failed: {result.json().get('error')}")

    time.sleep(1)

    # Step 5: Click Next
    print("\nStep 4: Click Next...")
    buttons = [n for n in aria if n.get('role') == 'button' and
               n.get('name') and 'next' in n.get('name').lower()]

    if buttons:
        next_btn = buttons[0]
        next_selector = f"role=button[name=\"{next_btn.get('name')}\"]"

        result = requests.post(f"{API}/click",
                              json={"selector": next_selector},
                              timeout=60)

        if result.json().get('success'):
            print(f"  ✅ Next clicked!")
            record_step("Click Next (email)", "click", {
                "selector": next_selector,
                "button": next_btn.get('name')
            })

        time.sleep(4)

        # Screenshot after Next
        screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
        print(f"\n📸 Screenshot: {screenshot.get('path')}")

        # Step 6: Get password page snapshot
        print("\nStep 5: Get ARIA for password page...")
        snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
        aria = snapshot.get('aria', [])

        textboxes = [n for n in aria if n.get('role') == 'textbox']
        print(f"  Found {len(textboxes)} textboxes")

        # Check if we're blocked
        page_text = snapshot.get('aria', [])
        blocked_keywords = ['couldn\'t sign', 'browser', 'not secure', 'not be secure']
        is_blocked = any(
            keyword in str(node.get('name', '')).lower()
            for node in page_text
            for keyword in blocked_keywords
        )

        if is_blocked:
            print("\n⚠️  BLOCKED BY GOOGLE!")
            print("This should NOT happen in headed mode.")
            print("Check screenshot to see the error.")
            record_step("Blocked by Google", "error", {
                "message": "Google detected automation even in headed mode"
            })
        else:
            # Find password field
            password_field = None
            for tb in textboxes:
                name = tb.get('name', '').lower()
                if 'password' in name:
                    password_field = tb
                    break

            if password_field:
                print(f"\n✅ Found password field: {password_field.get('name')}")
                password_selector = f"role=textbox[name=\"{password_field.get('name')}\"]"

                print("\nStep 6: Fill password...")
                result = requests.post(f"{API}/fill",
                                      json={"selector": password_selector, "text": password},
                                      timeout=60)

                if result.json().get('success'):
                    print(f"  ✅ Password filled!")
                    record_step("Fill password", "fill", {
                        "selector": password_selector,
                        "field": password_field.get('name')
                    })

                time.sleep(1)

                # Click Next/Sign in
                print("\nStep 7: Click Next/Sign in...")
                snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
                aria = snapshot.get('aria', [])

                buttons = [n for n in aria if n.get('role') == 'button']
                next_buttons = [b for b in buttons if b.get('name') and
                               any(word in b.get('name').lower() for word in ['next', 'sign in'])]

                if next_buttons:
                    btn = next_buttons[0]
                    selector = f"role=button[name=\"{btn.get('name')}\"]"

                    result = requests.post(f"{API}/click",
                                          json={"selector": selector},
                                          timeout=60)

                    if result.json().get('success'):
                        print(f"  ✅ Clicked: {btn.get('name')}")
                        record_step("Click Next (password)", "click", {
                            "selector": selector,
                            "button": btn.get('name')
                        })

                    time.sleep(5)

                    # Final state check
                    print("\n" + "="*70)
                    print("🔍 FINAL STATE CHECK")
                    print("="*70)

                    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
                    print(f"\n📸 Screenshot: {screenshot.get('path')}")

                    snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
                    aria = snapshot.get('aria', [])

                    # Check for OAuth/2FA
                    oauth_keywords = ['verify', 'code', '2-step', 'phone', 'security', 'recovery']
                    oauth_elements = [n for n in aria if n.get('name') and
                                     any(kw in n.get('name').lower() for kw in oauth_keywords)]

                    # Check for Gmail
                    gmail_keywords = ['inbox', 'compose', 'primary', 'starred', 'search mail']
                    gmail_elements = [n for n in aria if n.get('name') and
                                     any(kw in n.get('name').lower() for kw in gmail_keywords)]

                    if gmail_elements:
                        print("\n✅ LOGGED IN TO GMAIL!")
                        print("\nGmail elements found:")
                        for elem in gmail_elements[:10]:
                            print(f"  - {elem.get('name')}")

                        record_step("Login successful", "success", {
                            "gmail_elements": len(gmail_elements)
                        })

                        # Save session
                        print("\n💾 Saving session...")
                        result = requests.post(f"{API}/save-session", timeout=30).json()
                        if result.get('success'):
                            print(f"  ✅ Session saved: {result.get('path')}")
                            record_step("Save session", "save_session", {
                                "path": result.get('path')
                            })

                    elif oauth_elements:
                        print("\n🔐 OAUTH/2FA PROMPT DETECTED")
                        print("\nOAuth elements:")
                        for elem in oauth_elements[:10]:
                            print(f"  - {elem.get('name')}")

                        record_step("OAuth/2FA detected", "oauth_prompt", {
                            "elements": [e.get('name') for e in oauth_elements[:5]]
                        })

                        print("\n" + "="*70)
                        print("⏸️  PAUSED FOR USER ACTION")
                        print("="*70)
                        print("\nPlease complete OAuth/2FA in the browser window.")
                        print("Then I'll save the session!")

                        input("\nPress Enter when you've completed OAuth...")

                        # Save session after OAuth
                        print("\n💾 Saving session...")
                        result = requests.post(f"{API}/save-session", timeout=30).json()
                        if result.get('success'):
                            print(f"  ✅ Session saved: {result.get('path')}")
                            record_step("Save session (after OAuth)", "save_session", {
                                "path": result.get('path')
                            })

                    else:
                        print("\n⚠️  UNKNOWN STATE")
                        print(f"  Found {len(aria)} ARIA elements")
                        record_step("Unknown state", "warning", {
                            "aria_count": len(aria)
                        })

# Save recipe
print("\n" + "="*70)
print("💾 SAVING RECIPE")
print("="*70)

recipe_path = "recipes/gmail-login-headed.recipe.json"
Path(recipe_path).parent.mkdir(parents=True, exist_ok=True)

with open(recipe_path, 'w') as f:
    json.dump(recipe, f, indent=2)

print(f"\n✅ Recipe saved: {recipe_path}")
print(f"   {len(recipe['execution_trace'])} steps recorded")

print("\n" + "="*70)
print("✅ LOGIN FLOW COMPLETE")
print("="*70)
print("\nNext steps:")
print("1. Session cookies saved in artifacts/linkedin_session.json")
print("2. Recipe saved in recipes/gmail-login-headed.recipe.json")
print("3. Now you can use headless mode with saved session!")
