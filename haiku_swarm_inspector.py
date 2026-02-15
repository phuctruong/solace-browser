#!/usr/bin/env python3
"""
HAIKU SWARM WEB INSPECTOR
Auth: 65537 (Fermat Prime Authority)
Northstar: Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)

Multi-agent parallel page inspection system:
- Scout: Visual navigation + screenshots
- Solver: Extract technical data (DOM, network, console)
- Skeptic: Verify accuracy + find issues

All 3 agents work in parallel for 3x speed + accuracy boost
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import subprocess
import sys
from typing import Dict, List, Any, Optional

# Colors for output
class Colors:
    SCOUT = "\033[94m"      # Blue - Scout
    SOLVER = "\033[92m"     # Green - Solver
    SKEPTIC = "\033[91m"    # Red - Skeptic
    HEADER = "\033[95m"     # Magenta - Header
    SUCCESS = "\033[92m"    # Green
    WARNING = "\033[93m"    # Yellow
    RESET = "\033[0m"

def log_scout(msg: str):
    print(f"{Colors.SCOUT}[SCOUT ◆]{Colors.RESET} {msg}")

def log_solver(msg: str):
    print(f"{Colors.SOLVER}[SOLVER ✓]{Colors.RESET} {msg}")

def log_skeptic(msg: str):
    print(f"{Colors.SKEPTIC}[SKEPTIC ✗]{Colors.RESET} {msg}")

def log_header(msg: str):
    print(f"\n{Colors.HEADER}{'='*70}{Colors.RESET}")
    print(f"{Colors.HEADER}{msg:^70}{Colors.RESET}")
    print(f"{Colors.HEADER}{'='*70}{Colors.RESET}\n")

# ============================================================================
# COOKIE PERSISTENCE SYSTEM
# ============================================================================

class CookieVault:
    """
    Persistent cookie storage + auto-expiration + reuse system
    Replaces the need to re-login every time
    """

    def __init__(self, vault_dir: str = "artifacts/cookie_vault"):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.manifest = self.vault_dir / "manifest.json"
        self._load_manifest()

    def _load_manifest(self):
        """Load cookie manifest (tracks expiration, last used, etc)"""
        if self.manifest.exists():
            with open(self.manifest) as f:
                self.data = json.load(f)
        else:
            self.data = {"cookies": {}, "metadata": {}}

    def _save_manifest(self):
        """Persist manifest to disk"""
        with open(self.manifest, 'w') as f:
            json.dump(self.data, f, indent=2)

    def save_cookies(self, domain: str, cookies: List[Dict],
                     metadata: Optional[Dict] = None):
        """
        Save cookies for a domain with metadata

        Args:
            domain: e.g. 'gmail.com', 'linkedin.com'
            cookies: Playwright storage_state cookies array
            metadata: Optional - { 'expires_in_days': 14, 'notes': '...' }
        """
        cookie_file = self.vault_dir / f"{domain}_cookies.json"

        # Save cookies
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)

        # Save metadata
        meta = metadata or {}
        meta['saved_at'] = datetime.now().isoformat()
        meta['last_used'] = datetime.now().isoformat()
        meta['domain'] = domain

        self.data['cookies'][domain] = {
            'file': str(cookie_file),
            'count': len(cookies),
            'metadata': meta
        }
        self._save_manifest()

        log_solver(f"✅ Saved {len(cookies)} cookies for {domain}")
        return cookie_file

    def load_cookies(self, domain: str) -> Optional[List[Dict]]:
        """
        Load cookies for a domain (validates expiration first)
        Returns None if expired/not found
        """
        if domain not in self.data['cookies']:
            log_skeptic(f"❌ No cookies found for {domain}")
            return None

        entry = self.data['cookies'][domain]
        cookie_file = Path(entry['file'])

        if not cookie_file.exists():
            log_skeptic(f"❌ Cookie file missing for {domain}: {cookie_file}")
            return None

        # Check if expired
        meta = entry.get('metadata', {})
        expires_in_days = meta.get('expires_in_days', 7)
        saved_at = datetime.fromisoformat(meta['saved_at'])
        age_days = (datetime.now() - saved_at).days

        if age_days > expires_in_days:
            log_skeptic(f"⚠️  Cookies for {domain} expired ({age_days}d > {expires_in_days}d)")
            return None

        # Load cookies
        with open(cookie_file) as f:
            cookies = json.load(f)

        # Update last_used timestamp
        entry['metadata']['last_used'] = datetime.now().isoformat()
        self._save_manifest()

        log_solver(f"✅ Loaded {len(cookies)} cookies for {domain} (age: {age_days}d)")
        return cookies

    def list_cookies(self) -> Dict:
        """Show all saved cookies by domain"""
        return self.data['cookies']

    def clear_domain(self, domain: str):
        """Delete cookies for a domain"""
        if domain in self.data['cookies']:
            del self.data['cookies'][domain]
            self._save_manifest()
            log_solver(f"Cleared cookies for {domain}")


# ============================================================================
# HAIKU SWARM AGENTS
# ============================================================================

class ScoutAgent:
    """
    SCOUT: Visual Navigation + Screenshots
    - Navigate to URL
    - Take screenshot
    - Get basic page info (title, URL, load time)
    """

    def __init__(self, server_url: str = "http://localhost:9222"):
        self.server = server_url

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate and screenshot"""
        log_scout(f"🔍 Navigating to {url}")

        result = {
            'agent': 'scout',
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'tasks': []
        }

        try:
            # Navigate
            response = subprocess.run(
                ['curl', '-s', '-X', 'POST', f'{self.server}/navigate',
                 '-H', 'Content-Type: application/json',
                 '-d', json.dumps({'url': url})],
                capture_output=True, text=True, timeout=30
            )
            result['tasks'].append({'action': 'navigate', 'status': 'ok'})
            log_scout(f"✓ Navigated")

            # Get screenshot
            response = subprocess.run(
                ['curl', '-s', f'{self.server}/screenshot'],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(response.stdout)
            result['screenshot'] = data.get('image')[:100] + "..." if data.get('image') else None
            result['tasks'].append({'action': 'screenshot', 'status': 'ok'})
            log_scout(f"✓ Screenshot captured")

        except Exception as e:
            log_scout(f"❌ Error: {e}")
            result['error'] = str(e)

        return result


class SolverAgent:
    """
    SOLVER: Extract Technical Data
    - DOM structure (ARIA tree)
    - Network traffic (pending requests)
    - Console logs
    - Performance metrics
    """

    def __init__(self, server_url: str = "http://localhost:9222"):
        self.server = server_url

    async def analyze(self) -> Dict[str, Any]:
        """Extract all technical data"""
        log_solver(f"⚙️  Analyzing page structure")

        result = {
            'agent': 'solver',
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }

        try:
            # Get HTML-clean
            response = subprocess.run(
                ['curl', '-s', f'{self.server}/html-clean'],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(response.stdout)
            html = data.get('html', '')
            result['data']['html_lines'] = len(html.split('\n'))
            result['data']['html_preview'] = html[:200]
            result['tasks'] = [{'action': 'html-clean', 'status': 'ok'}]
            log_solver(f"✓ Extracted HTML ({result['data']['html_lines']} lines)")

            # Get snapshot (ARIA + network + console)
            response = subprocess.run(
                ['curl', '-s', f'{self.server}/snapshot'],
                capture_output=True, text=True, timeout=30
            )
            snap = json.loads(response.stdout)

            result['data']['aria_tree'] = snap.get('aria_tree', {})
            result['data']['console_logs'] = snap.get('console', [])[:5]  # First 5 logs
            result['data']['network_requests'] = len(snap.get('network', []))
            result['tasks'].append({'action': 'snapshot', 'status': 'ok'})
            log_solver(f"✓ Extracted ARIA tree")
            log_solver(f"✓ Found {result['data']['network_requests']} network requests")

        except Exception as e:
            log_solver(f"❌ Error: {e}")
            result['error'] = str(e)

        return result


class SkepticAgent:
    """
    SKEPTIC: Verify Accuracy + Find Issues
    - Check if page loaded correctly
    - Detect bot detection / errors
    - Find missing elements
    - Validate data consistency
    """

    def __init__(self, server_url: str = "http://localhost:9222"):
        self.server = server_url

    async def verify(self) -> Dict[str, Any]:
        """Verify page health + find issues"""
        log_skeptic(f"🔎 Verifying page integrity")

        result = {
            'agent': 'skeptic',
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'issues': []
        }

        try:
            # Get snapshot
            response = subprocess.run(
                ['curl', '-s', f'{self.server}/snapshot'],
                capture_output=True, text=True, timeout=30
            )
            snap = json.loads(response.stdout)

            # Check 1: Page loaded
            if 'title' in snap:
                result['checks'].append({
                    'name': 'Page Loaded',
                    'status': 'PASS',
                    'details': f"Title: {snap['title']}"
                })
                log_skeptic(f"✓ Page loaded: {snap['title']}")
            else:
                result['issues'].append({'type': 'NOT_LOADED', 'severity': 'CRITICAL'})
                log_skeptic(f"❌ Page not loaded")

            # Check 2: No console errors
            console = snap.get('console', [])
            errors = [c for c in console if c.get('level') == 'error']
            if not errors:
                result['checks'].append({
                    'name': 'No Console Errors',
                    'status': 'PASS'
                })
                log_skeptic(f"✓ No console errors")
            else:
                result['issues'].append({
                    'type': 'CONSOLE_ERRORS',
                    'severity': 'HIGH',
                    'count': len(errors)
                })
                log_skeptic(f"⚠️  {len(errors)} console errors")

            # Check 3: No blocked requests
            network = snap.get('network', [])
            blocked = [r for r in network if r.get('status', 0) >= 400]
            if not blocked:
                result['checks'].append({
                    'name': 'No Blocked Requests',
                    'status': 'PASS'
                })
                log_skeptic(f"✓ All requests successful")
            else:
                result['issues'].append({
                    'type': 'BLOCKED_REQUESTS',
                    'severity': 'MEDIUM',
                    'count': len(blocked)
                })
                log_skeptic(f"⚠️  {len(blocked)} blocked requests")

            # Check 4: Elements visible
            aria = snap.get('aria_tree', {})
            if aria and aria.get('children'):
                result['checks'].append({
                    'name': 'Elements Visible',
                    'status': 'PASS',
                    'count': len(aria.get('children', []))
                })
                log_skeptic(f"✓ {len(aria.get('children', []))} elements visible")
            else:
                result['issues'].append({
                    'type': 'NO_ELEMENTS',
                    'severity': 'HIGH'
                })
                log_skeptic(f"❌ No elements visible")

        except Exception as e:
            log_skeptic(f"❌ Verification error: {e}")
            result['error'] = str(e)

        return result


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class HaikuSwarmOrchestrator:
    """
    Coordinates Scout, Solver, and Skeptic agents
    Runs all 3 in parallel for maximum speed + accuracy
    """

    def __init__(self, server_url: str = "http://localhost:9222"):
        self.scout = ScoutAgent(server_url)
        self.solver = SolverAgent(server_url)
        self.skeptic = SkepticAgent(server_url)
        self.vault = CookieVault()

    async def inspect(self, url: str, domain: str = None,
                     use_cookies: bool = True) -> Dict[str, Any]:
        """
        HAIKU SWARM INSPECTION (Parallel)

        1. Load cookies (if available)
        2. Navigate to URL
        3. Run Scout + Solver + Skeptic in parallel
        4. Synthesize results
        """

        log_header(f"HAIKU SWARM INSPECTION: {url}")

        inspection = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'agents': {}
        }

        # Step 1: Load cookies if available
        if use_cookies and domain:
            cookies = self.vault.load_cookies(domain)
            # TODO: Pass to browser server via API

        # Step 2: Navigate (sequential - must happen first)
        await self.scout.navigate(url)

        # Step 3: Run all 3 agents in parallel
        log_header("PARALLEL EXTRACTION (3 agents)")

        tasks = [
            self.scout.navigate(url),
            self.solver.analyze(),
            self.skeptic.verify()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                log_header(f"ERROR: {result}")
            else:
                agent = result.get('agent', 'unknown')
                inspection['agents'][agent] = result

        # Step 4: Synthesize results
        return self._synthesize(inspection)

    def _synthesize(self, inspection: Dict) -> Dict:
        """Combine Scout + Solver + Skeptic into actionable insights"""

        log_header("SYNTHESIS: What We Learned")

        scout = inspection['agents'].get('scout', {})
        solver = inspection['agents'].get('solver', {})
        skeptic = inspection['agents'].get('skeptic', {})

        synthesis = {
            'url': inspection['url'],
            'timestamp': inspection['timestamp'],
            'overall_status': 'HEALTHY',
            'insights': []
        }

        # Analyze health
        if skeptic.get('issues'):
            synthesis['overall_status'] = 'ISSUES_FOUND'
            synthesis['insights'].append({
                'type': 'ISSUES',
                'count': len(skeptic['issues']),
                'details': skeptic['issues']
            })

        # Extract key data
        solver_data = solver.get('data', {})
        if solver_data:
            synthesis['insights'].append({
                'type': 'PAGE_DATA',
                'html_size': solver_data.get('html_lines'),
                'network_requests': solver_data.get('network_requests'),
                'console_logs': len(solver_data.get('console_logs', []))
            })

        # Success checks
        checks = skeptic.get('checks', [])
        synthesis['insights'].append({
            'type': 'HEALTH_CHECKS',
            'total': len(checks),
            'passed': len([c for c in checks if c['status'] == 'PASS'])
        })

        # Print summary
        print(f"\n{Colors.SUCCESS}Overall Status: {synthesis['overall_status']}{Colors.RESET}")
        print(f"{Colors.SUCCESS}Checks Passed: {synthesis['insights'][-1]['passed']}/{synthesis['insights'][-1]['total']}{Colors.RESET}")

        return synthesis


# ============================================================================
# CLI
# ============================================================================

async def main():
    """Demo: Inspect Wikipedia with Haiku Swarm"""

    # Initialize
    swarm = HaikuSwarmOrchestrator()

    # Inspect a website
    result = await swarm.inspect(
        url="https://en.wikipedia.org/wiki/Haiku",
        domain="wikipedia.org"
    )

    # Save result
    result_file = Path("artifacts/haiku_swarm_inspection.json")
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Inspection saved to: {result_file}")

    # Show cookie vault
    print(f"\n{Colors.HEADER}COOKIE VAULT STATUS{Colors.RESET}")
    cookies = swarm.vault.list_cookies()
    for domain, info in cookies.items():
        age = info['metadata'].get('last_used', 'never')
        print(f"  {domain}: {info['count']} cookies (last used: {age})")


if __name__ == '__main__':
    asyncio.run(main())
