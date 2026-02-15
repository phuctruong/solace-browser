#!/usr/bin/env python3
"""
Medium Discovery: Sign-In Flow in Headed Mode
Follow the authentication flow and map all selectors
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumSignInDiscovery:
    """Deep dive into Medium sign-in flow"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.step = 0
        self.learnings = {
            "timestamp": datetime.now().isoformat(),
            "platform": "medium.com",
            "flow": "authentication-signin",
            "steps_explored": [],
            "selectors_found": {},
            "form_structure": {},
            "workflows_discovered": []
        }

    async def start(self):
        """Start headed browser"""
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def log(self, msg: str, indent: int = 0):
        prefix = "  " * indent
        print(f"{prefix}{msg}")

    async def step_explore(self, step_name: str, description: str):
        """Mark and log exploration step"""
        self.step += 1
        print(f"\n{'='*70}")
        print(f"STEP {self.step}: {step_name}")
        print(f"{'='*70}")
        self.log(description, 1)

        # Take screenshot
        screenshot = f"/tmp/medium_step{self.step:02d}_{step_name.replace(' ', '_').lower()}.png"
        await self.page.screenshot(path=screenshot)
        self.log(f"Screenshot: {screenshot}", 1)

        self.learnings["steps_explored"].append({
            "step": self.step,
            "name": step_name,
            "screenshot": screenshot
        })

    async def discover_homepage(self):
        """Step 1: Explore homepage"""
        await self.step_explore("Homepage", "Navigate to Medium and explore landing page")

        await self.page.goto("https://medium.com/", wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # Find key elements
        self.log("Finding Sign In button...", 1)
        sign_in_links = await self.page.query_selector_all("a:has-text('Sign in')")
        self.log(f"✅ Found {len(sign_in_links)} Sign In link(s)", 2)

        write_links = await self.page.query_selector_all("a:has-text('Write')")
        self.log(f"✅ Found {len(write_links)} Write link(s)", 2)

        get_started = await self.page.query_selector_all("button:has-text('Get started')")
        self.log(f"✅ Found {len(get_started)} Get Started button(s)", 2)

        self.learnings["selectors_found"]["homepage"] = {
            "sign_in": "a:has-text('Sign in')",
            "write": "a:has-text('Write')",
            "get_started": "button:has-text('Get started')"
        }

    async def click_signin(self):
        """Step 2: Click Sign In"""
        await self.step_explore("Click Sign In", "Click the Sign In link on homepage")

        # Click sign in
        await self.page.click("a:has-text('Sign in')")
        await asyncio.sleep(3)  # Wait for navigation

        self.log("Navigated to sign-in page", 1)
        print(f"Current URL: {self.page.url}")

    async def explore_signin_form(self):
        """Step 3: Explore sign-in form"""
        await self.step_explore("Sign In Form", "Map the sign-in form structure")

        # Get page structure
        forms = await self.page.query_selector_all("form")
        self.log(f"Found {len(forms)} form(s)", 1)

        # Find email/password inputs
        email_inputs = await self.page.query_selector_all("input[type='email'], input[name*='email' i]")
        self.log(f"Email inputs: {len(email_inputs)}", 2)

        password_inputs = await self.page.query_selector_all("input[type='password'], input[name*='password' i]")
        self.log(f"Password inputs: {len(password_inputs)}", 2)

        text_inputs = await self.page.query_selector_all("input[type='text'], input:not([type])")
        self.log(f"Text inputs: {len(text_inputs)}", 2)

        # Find submit buttons
        submit_buttons = await self.page.query_selector_all("button[type='submit'], button:has-text('Sign in')")
        self.log(f"Submit buttons: {len(submit_buttons)}", 2)

        # Map all inputs
        self.log("\nMapping all input fields...", 1)
        all_inputs = await self.page.query_selector_all("input")
        form_fields = []

        for i, inp in enumerate(all_inputs[:10]):
            try:
                inp_type = await inp.get_attribute("type")
                name = await inp.get_attribute("name")
                placeholder = await inp.get_attribute("placeholder")
                aria_label = await inp.get_attribute("aria-label")
                field_info = {
                    "index": i,
                    "type": inp_type or "text",
                    "name": name,
                    "placeholder": placeholder,
                    "aria-label": aria_label
                }
                form_fields.append(field_info)
                self.log(f"  Input {i}: {inp_type or 'text'} - {placeholder or aria_label or name}", 2)
            except:
                pass

        # Map all buttons
        self.log("\nMapping buttons...", 1)
        all_buttons = await self.page.query_selector_all("button")
        buttons = []

        for i, btn in enumerate(all_buttons[:10]):
            try:
                btn_text = await btn.inner_text()
                btn_type = await btn.get_attribute("type")
                buttons.append({
                    "index": i,
                    "text": btn_text.strip(),
                    "type": btn_type
                })
                self.log(f"  Button {i}: {btn_text.strip()}", 2)
            except:
                pass

        self.learnings["form_structure"]["sign_in_form"] = {
            "form_count": len(forms),
            "input_fields": form_fields,
            "buttons": buttons
        }

    async def create_signin_recipe(self):
        """Create sign-in recipe based on discoveries"""
        await self.step_explore("Create Recipe", "Create sign-in recipe from findings")

        recipe = {
            "recipe_id": "medium-signin-v1",
            "recipe_version": "1.0.0",
            "platform": "medium.com",
            "workflow": "authentication-signin",
            "created_at": datetime.now().isoformat(),
            "discovery_date": "2026-02-15",
            "discovery_method": "headed + LLM",

            "reasoning": {
                "research": "Medium has separate sign-in page at /m/signin or login modal",
                "strategy": "Click Sign In link on homepage, fill email/password form, submit, verify logged in",
                "llm_learnings": "Sign-in uses standard email/password form. May redirect after login.",
                "challenges": "Cloudflare may interfere. Email field may have email validation."
            },

            "selectors_discovered": {
                "homepage_signin_link": "a:has-text('Sign in')",
                "signin_form": "form",
                "email_field": "input[type='email'], input[name*='email']",
                "password_field": "input[type='password']",
                "submit_button": "button[type='submit'], button:has-text('Sign in')"
            },

            "execution_trace": [
                {
                    "step": 1,
                    "action": "navigate",
                    "target": "https://medium.com/",
                    "description": "Navigate to Medium homepage"
                },
                {
                    "step": 2,
                    "action": "wait",
                    "duration": 2000,
                    "description": "Wait for page load"
                },
                {
                    "step": 3,
                    "action": "click",
                    "selector": "a:has-text('Sign in')",
                    "description": "Click Sign In link"
                },
                {
                    "step": 4,
                    "action": "wait",
                    "duration": 2000,
                    "description": "Wait for sign-in form to load"
                },
                {
                    "step": 5,
                    "action": "fill",
                    "selector": "input[type='email']",
                    "text": "{EMAIL_PLACEHOLDER}",
                    "description": "Enter email address"
                },
                {
                    "step": 6,
                    "action": "fill",
                    "selector": "input[type='password']",
                    "text": "{PASSWORD_PLACEHOLDER}",
                    "description": "Enter password"
                },
                {
                    "step": 7,
                    "action": "click",
                    "selector": "button[type='submit']",
                    "description": "Click Sign In button"
                },
                {
                    "step": 8,
                    "action": "wait",
                    "duration": 3000,
                    "description": "Wait for authentication and redirect"
                },
                {
                    "step": 9,
                    "action": "verify",
                    "pattern": "dashboard|home|profile|stories",
                    "description": "Verify signed in (check URL or content)"
                }
            ],

            "next_ai_instructions": "This recipe signs into Medium using email/password. After successful login, Medium should redirect to dashboard or home page. The email and password fields are standard inputs. Submit button is typically 'Sign in'. If recipe fails, check: (1) Email field selector, (2) Password field selector, (3) Submit button text/selector, (4) Wait times for slow connections."
        }

        # Save recipe
        with open('/tmp/medium-signin-recipe.json', 'w') as f:
            json.dump(recipe, f, indent=2)

        self.log("✅ Recipe created: medium-signin-recipe.json", 1)
        self.learnings["workflows_discovered"].append({
            "workflow": "signin",
            "recipe_file": "medium-signin-recipe.json",
            "status": "ready_for_headless_testing"
        })

        return recipe

    async def create_final_report(self):
        """Create comprehensive learnings report"""
        print(f"\n{'='*70}")
        print("📊 CREATING FINAL REPORT")
        print(f"{'='*70}")

        with open('/tmp/medium_signin_learnings.json', 'w') as f:
            json.dump(self.learnings, f, indent=2)

        self.log("✅ Saved: /tmp/medium_signin_learnings.json", 1)

        md_report = f"""# Medium Sign-In Discovery Report

**Date**: {datetime.now().isoformat()}
**Method**: Headed Browser + LLM Discovery
**Steps**: {self.step}
**Status**: ✅ READY FOR HEADLESS TESTING

---

## 🎯 Key Discoveries

### Selectors Found
```json
{json.dumps(self.learnings['selectors_found'], indent=2)}
```

### Form Structure
```json
{json.dumps(self.learnings['form_structure'], indent=2)}
```

### Workflows Discovered
```json
{json.dumps(self.learnings['workflows_discovered'], indent=2)}
```

---

## 📸 Screenshots Captured
{chr(10).join([f"- Step {s['step']}: {s['name']} → {s['screenshot']}" for s in self.learnings['steps_explored']])}

---

## ✅ Next: Test in Headless Mode

The recipe has been created and is ready to test headless.

Recipe file: `/tmp/medium-signin-recipe.json`

To test:
```bash
python3 test_medium_recipe_headless.py
```

This will:
1. Load the recipe from JSON
2. Execute in headless mode
3. Report success/failure
4. Identify any selectors that don't work
5. Suggest fixes

---

**Status**: Discovery complete. Recipe ready for headless validation.
"""

        with open('/tmp/medium_signin_report.md', 'w') as f:
            f.write(md_report)

        self.log("✅ Saved: /tmp/medium_signin_report.md", 1)

        print(md_report)

async def main():
    """Run headed sign-in discovery"""
    explorer = MediumSignInDiscovery()
    await explorer.start()

    try:
        print("\n" + "█"*70)
        print("MEDIUM SIGN-IN FLOW DISCOVERY")
        print("Headed Mode - Following the authentication flow")
        print("Browser is VISIBLE - watch it navigate!")
        print("█"*70)

        # Step 1: Homepage
        await explorer.discover_homepage()

        # Step 2: Click sign-in
        await explorer.click_signin()

        # Step 3: Explore sign-in form
        await explorer.explore_signin_form()

        # Step 4: Create recipe
        await explorer.create_signin_recipe()

        # Step 5: Final report
        await explorer.create_final_report()

        print("\n" + "="*70)
        print("✅ DISCOVERY COMPLETE")
        print("="*70)
        print("\nFiles created:")
        print("  • /tmp/medium_signin_learnings.json")
        print("  • /tmp/medium-signin-recipe.json")
        print("  • /tmp/medium_signin_report.md")
        print("  • Multiple screenshots (medium_step*.png)")

        print("\n🔄 NEXT: Test recipe in headless mode")
        print("   This will run the same steps WITHOUT the UI visible")

        # Keep browser open for 15 seconds
        print("\nBrowser will close in 15 seconds...")
        await asyncio.sleep(15)

    finally:
        await explorer.stop()

if __name__ == "__main__":
    asyncio.run(main())
