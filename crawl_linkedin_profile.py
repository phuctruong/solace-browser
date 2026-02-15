#!/usr/bin/env python3
"""
LinkedIn Profile Crawler - OpenClaw Pattern
Auto-maps profile structure and creates PrimeWiki node
"""

import requests
import json
from datetime import datetime

API = "http://localhost:9222"

def crawl_section(url, section_name):
    """Crawl a specific profile section"""
    print(f"\n📍 Crawling: {section_name}")
    print(f"   URL: {url}")

    # Navigate
    result = requests.post(f"{API}/navigate", json={"url": url}, timeout=30)
    if not result.json().get('success'):
        print(f"   ❌ Navigation failed")
        return None

    import time
    time.sleep(3)

    # Get snapshot
    snapshot = requests.get(f"{API}/snapshot", timeout=30).json()

    # Get clean HTML
    html_result = requests.get(f"{API}/html-clean", timeout=30).json()
    html = html_result.get('html', '')

    # Take screenshot
    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()

    return {
        "section": section_name,
        "url": url,
        "snapshot": snapshot,
        "html_length": len(html),
        "screenshot": screenshot.get('path'),
        "crawled_at": datetime.now().isoformat()
    }

def extract_structured_data(section_data):
    """Extract structured data from section"""
    if not section_data:
        return {}

    html = section_data.get('html', '')

    # Extract key data points
    data = {
        "section": section_data['section'],
        "url": section_data['url']
    }

    # Section-specific extraction
    if 'projects' in section_data['section'].lower():
        # Extract project names
        import re
        projects = re.findall(r'<span[^>]*>([^<]+(?:\.com|THEORY|PHUCNET|PZIP|SOLACEAGI|STILLWATER)[^<]*)</span>', html)
        data['projects'] = list(set(projects))

    return data

def create_primewiki_node(profile_data):
    """Create PrimeWiki node from crawled data"""

    node = {
        "title": "LinkedIn Profile: Phuc Truong",
        "tier": 79,  # Genome-level (professional profile)
        "c_score": 0.95,  # High coherence (verified data)
        "g_score": 0.90,  # High gravity (authoritative source)
        "crawled_at": datetime.now().isoformat(),

        "canonical_claims": [],
        "evidence": [],
        "portals": {},
        "metadata": {
            "source": "https://linkedin.com/in/phucvinhtruong",
            "method": "browser_crawl",
            "tool": "solace_browser_crawler"
        }
    }

    # Extract claims from each section
    for section_name, section_data in profile_data.items():
        if not section_data:
            continue

        claim = {
            "claim": f"Profile contains {section_name} section",
            "confidence": 1.0,
            "evidence": {
                "type": "crawl_snapshot",
                "url": section_data['url'],
                "screenshot": section_data['screenshot'],
                "timestamp": section_data['crawled_at']
            }
        }
        node['canonical_claims'].append(claim)

    return node

def main():
    print("="*70)
    print("🕷️  LINKEDIN PROFILE CRAWLER")
    print("="*70)
    print("Auto-mapping profile structure (OpenClaw pattern)")
    print()

    # Check browser
    health = requests.get(f"{API}/health", timeout=10).json()
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        return

    print("✅ Browser server ready\n")

    # Define sections to crawl
    sections = {
        "profile_home": "https://www.linkedin.com/in/me/",
        "projects": "https://www.linkedin.com/in/me/details/projects/",
        "about": "https://www.linkedin.com/in/me/",  # About is on home page
    }

    # Crawl each section
    profile_data = {}
    for section_name, url in sections.items():
        profile_data[section_name] = crawl_section(url, section_name)

    print("\n" + "="*70)
    print("📊 CRAWL SUMMARY")
    print("="*70)

    for section_name, data in profile_data.items():
        if data:
            print(f"✅ {section_name}: {data['html_length']:,} chars")
            print(f"   Screenshot: {data['screenshot']}")

    # Create PrimeWiki node
    print("\n" + "="*70)
    print("📝 CREATING PRIMEWIKI NODE")
    print("="*70)

    wiki_node = create_primewiki_node(profile_data)

    # Save to file
    wiki_path = "primewiki/linkedin-profile-phuc-truong.primewiki.json"
    with open(wiki_path, 'w') as f:
        json.dump(wiki_node, f, indent=2)

    print(f"✅ PrimeWiki node saved: {wiki_path}")
    print(f"   Tier: {wiki_node['tier']}")
    print(f"   C-Score: {wiki_node['c_score']}")
    print(f"   G-Score: {wiki_node['g_score']}")
    print(f"   Claims: {len(wiki_node['canonical_claims'])}")

    # Also extract current project state
    print("\n" + "="*70)
    print("📋 CURRENT PROJECTS STATE")
    print("="*70)

    # Get projects HTML
    requests.post(f"{API}/navigate",
        json={"url": "https://www.linkedin.com/in/me/details/projects/"},
        timeout=30)

    import time
    time.sleep(3)

    html = requests.get(f"{API}/html-clean", timeout=30).json().get('html', '')

    # Extract all project names
    import re
    all_projects = re.findall(r'<span[^>]*aria-hidden="true">([^<]+)</span>', html)

    # Filter to just project names (look for our known ones)
    project_names = []
    keywords = ['THEORY', 'PHUCNET', 'PZIP', 'SOLACEAGI', 'STILLWATER', 'Stillwater', 'SolaceAgi', 'PZip', 'IFTheory', 'Phuc.net']

    for text in all_projects:
        if any(kw in text for kw in keywords):
            if text not in project_names and len(text) < 50:  # Avoid descriptions
                project_names.append(text)

    print("\nFound project names:")
    for proj in sorted(set(project_names)):
        is_old = proj.isupper() or '-' in proj
        status = "❌ OLD (delete)" if is_old else "✅ NEW (keep)"
        print(f"  {status} {proj}")

    # Count duplicates
    old_count = sum(1 for p in project_names if p.isupper() or '-' in p)
    new_count = sum(1 for p in project_names if '.com' in p or 'Phuc.net' in p)

    print(f"\nSummary:")
    print(f"  Old projects (delete): {old_count}")
    print(f"  New projects (keep): {new_count}")

    if old_count > 0:
        print(f"\n⚠️  {old_count} duplicate(s) still need manual deletion")
    else:
        print("\n✅ No duplicates! Profile clean!")

    print("\n" + "="*70)
    print("✅ CRAWL COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
