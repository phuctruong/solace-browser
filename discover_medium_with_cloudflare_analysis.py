#!/usr/bin/env python3
"""
Medium Discovery + Cloudflare JavaScript Challenge Analysis
=========================================================
Goal: Understand Cloudflare's bot detection by inspecting network requests
Strategy: Reuse Gmail session, access Medium as logged-in user, track JS execution
Hypothesis: Cloudflare sends JS challenge that needs to be routed back
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright
from datetime import datetime

class MediumCloudflareAnalyzer:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.network_log = []
        self.js_challenges = []
        self.cookies_used = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "sessions": [],
            "network_analysis": [],
            "cloudflare_challenges": [],
            "findings": []
        }

    async def start(self):
        """Start headed browser with network interception"""
        print("🖥️  Starting HEADED browser with network monitoring...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)  # HEADED MODE
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        # Set up network request logging
        async def log_request(request):
            self.network_log.append({
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "resource_type": request.resource_type,
                "timestamp": datetime.now().isoformat()
            })
            print(f"  📡 {request.resource_type.upper()}: {request.url[:80]}")

        async def log_response(response):
            try:
                size = len(await response.body()) if response.resource_type == 'document' else '?'
                print(f"     ✓ {response.status} ({size} bytes)")
            except:
                pass

        self.page.on("request", log_request)
        self.page.on("response", log_response)

        print("✅ Browser started in HEADED mode with network monitoring\n")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def test_gmail_cookie_reuse(self):
        """Test if Gmail session cookie can be reused"""
        print("=" * 70)
        print("STEP 1: Test Gmail Cookie Reuse")
        print("=" * 70)

        print("\n📱 Navigate to Gmail...")
        await self.page.goto("https://gmail.com", wait_until='domcontentloaded', timeout=15000)

        # Check if already logged in
        try:
            await self.page.wait_for_selector("span:has-text('Inbox')", timeout=3000)
            print("✅ Already logged in (Gmail OAuth2 session persisted!)")

            # Capture cookies
            cookies = await self.context.cookies()
            gmail_cookies = {c['name']: c['value'] for c in cookies if 'google' in c['domain'].lower()}
            self.cookies_used = gmail_cookies

            print(f"✅ Found {len(cookies)} cookies from Gmail session")
            print(f"   Key cookies: {list(gmail_cookies.keys())}")

            return True
        except:
            print("❌ Not logged in - would need to login again")
            return False

    async def analyze_cloudflare_js(self):
        """Analyze Cloudflare JavaScript challenge"""
        print("\n" + "=" * 70)
        print("STEP 2: Analyze Cloudflare JavaScript Challenge")
        print("=" * 70)

        print("\n🎯 Navigate to Medium with network monitoring...")

        # Clear network log for this specific request
        self.network_log = []

        try:
            await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=20000)
            print("✅ Page loaded")
        except Exception as e:
            print(f"⚠️  Page load timeout: {str(e)[:100]}")

        # Take screenshot
        screenshot_path = "/tmp/medium_with_cf_analysis.png"
        await self.page.screenshot(path=screenshot_path)
        print(f"📸 Screenshot: {screenshot_path}")

        # Analyze network requests
        print("\n" + "─" * 70)
        print("NETWORK ANALYSIS")
        print("─" * 70)

        cf_requests = [r for r in self.network_log if 'cloudflare' in r['url'].lower()]
        print(f"\n🔍 Found {len(cf_requests)} Cloudflare requests:")
        for req in cf_requests[:10]:
            print(f"  • {req['resource_type']}: {req['url'][:70]}")

        # Look for JavaScript execution challenges
        print("\n🔍 Checking for JavaScript challenges...")

        # Get page content
        html = await self.page.content()

        # Look for Cloudflare challenge indicators
        cf_indicators = [
            ("challenge", html.count("challenge")),
            ("Ray ID", html.count("cfrequestid")),
            ("__cf_", html.count("__cf_")),
            ("cf-challenge", html.count("cf-challenge")),
            ("cf_clearance", html.count("cf_clearance"))
        ]

        for indicator, count in cf_indicators:
            if count > 0:
                print(f"  ✓ Found: {indicator} ({count} times)")
                self.js_challenges.append(indicator)

        # Check for script tags
        scripts = await self.page.query_selector_all("script")
        print(f"\n  • {len(scripts)} script tags found")

        # Look for inline challenge scripts
        for i, script in enumerate(scripts[:5]):
            content = await script.text_content()
            if "cf" in content.lower() or "cloudflare" in content.lower():
                print(f"    ✓ Script {i}: Contains Cloudflare references ({len(content)} chars)")

        return {
            "cloudflare_requests": len(cf_requests),
            "challenges_detected": self.js_challenges,
            "total_requests": len(self.network_log)
        }

    async def extract_cloudflare_headers(self):
        """Extract and analyze Cloudflare-related headers"""
        print("\n" + "=" * 70)
        print("STEP 3: Cloudflare Headers & Challenge Details")
        print("=" * 70)

        print("\n🔍 Analyzing response headers from Cloudflare...")

        cf_headers = {}
        for req in self.network_log:
            if req['resource_type'] == 'document':
                for header, value in req['headers'].items():
                    if 'cf-' in header.lower() or 'cloudflare' in header.lower():
                        cf_headers[header] = value
                        print(f"  {header}: {value[:100]}")

        # Look for specific challenge headers
        important_headers = [
            'cf-ray',
            'cf-cache-status',
            'cf-request-id',
            'server',
            'set-cookie'
        ]

        print("\n📋 Important headers found:")
        for req in self.network_log[-5:]:
            if req['resource_type'] == 'document':
                print(f"\n  URL: {req['url']}")
                for header in important_headers:
                    for h, v in req['headers'].items():
                        if h.lower() == header.lower():
                            print(f"    {h}: {v[:80]}")

        return cf_headers

    async def test_medium_as_logged_in(self):
        """Try to access Medium as logged-in user"""
        print("\n" + "=" * 70)
        print("STEP 4: Access Medium as Logged-In User")
        print("=" * 70)

        print("\n🌐 Navigate to Medium homepage...")
        self.network_log = []

        try:
            await self.page.goto("https://medium.com/", wait_until='domcontentloaded', timeout=15000)

            # Wait a bit for any JS to execute
            await asyncio.sleep(3)

            # Check page content
            html = await self.page.content()

            if "Just a moment" in html:
                print("⚠️  Still seeing Cloudflare challenge page")
                self.results["findings"].append("Challenge persists even with logged-in status")
            elif len(html) > 50000:
                print("✅ Real Medium content loaded!")
                self.results["findings"].append("Successfully loaded Medium as logged-in user")

                # Extract some page info
                try:
                    articles = await self.page.query_selector_all("article")
                    print(f"   Found {len(articles)} article elements")
                except:
                    pass
            else:
                print("⚠️  Unclear if page loaded properly")

        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")

    async def analyze_cloudflare_flow(self):
        """Analyze the complete Cloudflare challenge flow"""
        print("\n" + "=" * 70)
        print("STEP 5: Complete Cloudflare Challenge Flow Analysis")
        print("=" * 70)

        print("\n📊 Network Timeline:")

        # Group requests by type
        by_type = {}
        for req in self.network_log:
            rt = req['resource_type']
            if rt not in by_type:
                by_type[rt] = 0
            by_type[rt] += 1

        for resource_type, count in sorted(by_type.items()):
            print(f"  {resource_type:15} : {count:3} requests")

        # Analyze request order (cf-challenge pattern)
        print("\n📡 Cloudflare Challenge Pattern:")

        cf_pattern = []
        for req in self.network_log:
            if 'cloudflare' in req['url'].lower() or 'cf-challenge' in req['url'].lower():
                cf_pattern.append({
                    "type": req['resource_type'],
                    "url": req['url'].split('/')[-1][:40]
                })

        for i, item in enumerate(cf_pattern[:10]):
            print(f"  {i+1}. {item['type']:8} → {item['url']}")

        return {
            "request_types": by_type,
            "cf_pattern": cf_pattern
        }

    async def run_analysis(self):
        """Run complete analysis"""
        print("\n" + "█" * 70)
        print("MEDIUM + CLOUDFLARE JAVASCRIPT CHALLENGE ANALYSIS")
        print("Testing cookie reuse and understanding bot detection mechanism")
        print("█" * 70)

        try:
            # Step 1: Test cookie reuse
            cookie_reuse = await self.test_gmail_cookie_reuse()
            self.results["sessions"].append({
                "session": "gmail",
                "cookie_reuse_success": cookie_reuse
            })

            # Step 2: Analyze Cloudflare
            cf_analysis = await self.analyze_cloudflare_js()
            self.results["network_analysis"].append(cf_analysis)

            # Step 3: Extract headers
            headers = await self.extract_cloudflare_headers()
            self.results["cloudflare_challenges"].append({
                "headers": headers
            })

            # Step 4: Test as logged-in
            await asyncio.sleep(2)
            await self.test_medium_as_logged_in()

            # Step 5: Complete flow analysis
            flow = await self.analyze_cloudflare_flow()
            self.results["network_analysis"].append(flow)

        finally:
            # Save results
            with open('/tmp/cloudflare_analysis_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)

            print("\n" + "=" * 70)
            print("✅ ANALYSIS COMPLETE")
            print("=" * 70)
            print(f"\n📊 Results saved: /tmp/cloudflare_analysis_results.json")
            print(f"\n📋 Key Findings:")
            for finding in self.results["findings"]:
                print(f"   • {finding}")

async def main():
    analyzer = MediumCloudflareAnalyzer()
    await analyzer.start()

    try:
        await analyzer.run_analysis()
    finally:
        await analyzer.stop()

if __name__ == "__main__":
    asyncio.run(main())
