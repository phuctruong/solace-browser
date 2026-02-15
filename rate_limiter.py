#!/usr/bin/env python3
"""
RATE LIMITER - Prevent site bans by respecting rate limits
Implements token bucket algorithm with per-domain rate limit enforcement

Usage:
    from rate_limiter import RateLimiter

    limiter = RateLimiter()
    await limiter.wait_if_needed('reddit.com')
    # Automatically waits if hitting rate limits

Supported Sites & Limits:
    - reddit.com: 60 req/hour, 10 sec min interval
    - gmail.com: 10 req/hour, 30 sec min interval
    - linkedin.com: 50 req/hour, 2 sec min interval
    - hn.algolia.com: 30 req/hour, 5 sec min interval
    - github.com: 60 req/hour, 2 sec min interval
    - twitter.com: 15 req/hour, 60 sec min interval
    - wikipedia.org: unlimited (no rate limit)
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a domain's rate limits"""
    requests_per_hour: int
    min_interval_sec: float
    description: str = ""


class RateLimiter:
    """
    Token bucket rate limiter for preventing site bans.

    Implements two strategies:
    1. Hourly rate limit: e.g., "max 60 requests per hour"
    2. Minimum interval: e.g., "minimum 10 seconds between requests"

    The limiter respects BOTH constraints - it's the most restrictive that wins.
    """

    # Default rate limits for common sites
    DEFAULT_LIMITS: Dict[str, RateLimitConfig] = {
        "reddit.com": RateLimitConfig(
            requests_per_hour=60,
            min_interval_sec=10,
            description="Reddit - conservative to avoid shadowban"
        ),
        "gmail.com": RateLimitConfig(
            requests_per_hour=10,
            min_interval_sec=30,
            description="Gmail - very strict, OAuth required"
        ),
        "mail.google.com": RateLimitConfig(
            requests_per_hour=10,
            min_interval_sec=30,
            description="Gmail inbox - same as gmail.com"
        ),
        "linkedin.com": RateLimitConfig(
            requests_per_hour=50,
            min_interval_sec=2,
            description="LinkedIn - rate limited but not too strict"
        ),
        "hn.algolia.com": RateLimitConfig(
            requests_per_hour=30,
            min_interval_sec=5,
            description="HackerNews - moderate rate limit"
        ),
        "news.ycombinator.com": RateLimitConfig(
            requests_per_hour=30,
            min_interval_sec=5,
            description="HackerNews - moderate rate limit"
        ),
        "github.com": RateLimitConfig(
            requests_per_hour=60,
            min_interval_sec=2,
            description="GitHub - reasonable for authenticated requests"
        ),
        "api.github.com": RateLimitConfig(
            requests_per_hour=60,
            min_interval_sec=2,
            description="GitHub API - same as web"
        ),
        "twitter.com": RateLimitConfig(
            requests_per_hour=15,
            min_interval_sec=60,
            description="Twitter - very strict rate limiting"
        ),
        "x.com": RateLimitConfig(
            requests_per_hour=15,
            min_interval_sec=60,
            description="X (formerly Twitter) - very strict"
        ),
        "facebook.com": RateLimitConfig(
            requests_per_hour=20,
            min_interval_sec=30,
            description="Facebook - IP-based rate limiting"
        ),
        "amazon.com": RateLimitConfig(
            requests_per_hour=30,
            min_interval_sec=10,
            description="Amazon - WAF protection"
        ),
        "wikipedia.org": RateLimitConfig(
            requests_per_hour=1000,  # Very high - Wikipedia allows scraping
            min_interval_sec=0.1,
            description="Wikipedia - user-agent required but no strict limits"
        ),
    }

    def __init__(self, custom_limits: Optional[Dict[str, RateLimitConfig]] = None):
        """
        Initialize rate limiter.

        Args:
            custom_limits: Override default limits with custom config
        """
        self.limits = self.DEFAULT_LIMITS.copy()
        if custom_limits:
            self.limits.update(custom_limits)

        # Track request times per domain
        self.request_times: Dict[str, List[float]] = {}

        logger.info(f"📊 RateLimiter initialized with {len(self.limits)} domains")

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if "://" in url:
            domain = urlparse(url).netloc
        else:
            domain = url

        # Normalize: remove www. prefix
        domain = domain.lstrip("www.")
        return domain

    async def wait_if_needed(self, url: str, reason: str = "") -> Dict:
        """
        Wait if necessary to respect rate limits.

        This is a blocking operation - will sleep if hitting limits.

        Args:
            url: Full URL or domain name (e.g., "https://reddit.com/r/python")
            reason: Optional reason for logging (e.g., "fetch profiles")

        Returns:
            Dict with stats: {
                "domain": "reddit.com",
                "waited": False,
                "wait_time_sec": 0,
                "requests_this_hour": 5,
                "limit_per_hour": 60,
                "next_request_allowed": True,
                "message": ""
            }
        """
        domain = self._extract_domain(url)
        config = self.limits.get(domain)

        # No rate limit defined - allow immediately
        if not config:
            logger.debug(f"⏭️  No rate limit for {domain} - allowing request")
            return {
                "domain": domain,
                "waited": False,
                "wait_time_sec": 0,
                "requests_this_hour": 0,
                "limit_per_hour": "unlimited",
                "next_request_allowed": True,
                "message": f"No rate limit defined for {domain}"
            }

        now = time.time()
        wait_reason = ""

        # ===== STRATEGY 1: Hourly Rate Limit =====
        recent_requests = [
            t for t in self.request_times.get(domain, [])
            if now - t < 3600  # Last hour
        ]

        if len(recent_requests) >= config.requests_per_hour:
            # Hit hourly limit - calculate wait time
            oldest_request = recent_requests[0]
            wait_time = 3600 - (now - oldest_request) + 1  # +1 second buffer
            wait_reason = f"Hourly rate limit hit ({len(recent_requests)}/{config.requests_per_hour})"

            logger.warning(
                f"⏱️  {domain}: {wait_reason}. Waiting {wait_time:.0f}s "
                f"(reason: {reason})" if reason else ""
            )

            await asyncio.sleep(wait_time)
            now = time.time()
            recent_requests = []

        # ===== STRATEGY 2: Minimum Interval Between Requests =====
        last_request = self.request_times.get(domain, [None])[-1] if self.request_times.get(domain) else None

        if last_request:
            interval = now - last_request
            if interval < config.min_interval_sec:
                wait_time = config.min_interval_sec - interval
                if not wait_reason:
                    wait_reason = f"Minimum interval ({config.min_interval_sec}s between requests)"

                logger.debug(
                    f"⏱️  {domain}: Waiting {wait_time:.2f}s "
                    f"(reason: {reason})" if reason else ""
                )

                await asyncio.sleep(wait_time)
                now = time.time()

        # Record this request
        if domain not in self.request_times:
            self.request_times[domain] = []

        self.request_times[domain].append(now)

        # Clean old entries (older than 1 hour)
        self.request_times[domain] = [
            t for t in self.request_times[domain]
            if now - t < 3600
        ]

        return {
            "domain": domain,
            "waited": bool(wait_reason),
            "wait_reason": wait_reason,
            "requests_this_hour": len(recent_requests),
            "limit_per_hour": config.requests_per_hour,
            "min_interval_sec": config.min_interval_sec,
            "next_request_allowed": True,
            "message": f"✅ Ready to request {domain}"
        }

    def get_stats(self, url: str) -> Dict:
        """
        Get current rate limit stats for a domain.

        Returns:
            Dict with current request counts and limits
        """
        domain = self._extract_domain(url)
        config = self.limits.get(domain)

        if not config:
            return {
                "domain": domain,
                "status": "unlimited",
                "message": f"No rate limit for {domain}"
            }

        requests = self.request_times.get(domain, [])
        now = time.time()
        recent = [t for t in requests if now - t < 3600]

        requests_remaining = max(0, config.requests_per_hour - len(recent))
        oldest_request = recent[0] if recent else None
        time_until_reset = None

        if oldest_request and len(recent) >= config.requests_per_hour:
            time_until_reset = 3600 - (now - oldest_request)

        return {
            "domain": domain,
            "status": "limited",
            "requests_used": len(recent),
            "requests_limit": config.requests_per_hour,
            "requests_remaining": requests_remaining,
            "min_interval_sec": config.min_interval_sec,
            "time_until_reset_sec": round(time_until_reset, 1) if time_until_reset else None,
            "description": config.description,
            "next_request_allowed": time.time() - (requests[-1] if requests else 0) >= config.min_interval_sec
        }

    def reset_domain(self, domain: str = None):
        """
        Reset rate limit counter for a domain (admin only).

        Args:
            domain: Domain to reset, or None to reset all
        """
        if domain:
            domain = self._extract_domain(domain)
            if domain in self.request_times:
                self.request_times[domain] = []
                logger.info(f"🔄 Reset rate limiter for {domain}")
        else:
            self.request_times = {}
            logger.info(f"🔄 Reset all rate limiters")

    def get_all_stats(self) -> Dict:
        """Get stats for all tracked domains"""
        return {
            domain: self.get_stats(domain)
            for domain in self.request_times.keys()
        }


if __name__ == '__main__':
    # Test rate limiter
    logging.basicConfig(level=logging.DEBUG)

    async def test():
        limiter = RateLimiter()

        print("=== Rate Limiter Test ===\n")

        # Test 1: First request (should be immediate)
        print("Test 1: First Reddit request")
        result = await limiter.wait_if_needed("https://reddit.com/r/python")
        print(f"  Waited: {result['waited']}")
        print(f"  Stats: {limiter.get_stats('reddit.com')}\n")

        # Test 2: Rapid requests (should wait)
        print("Test 2: Second Reddit request (immediate)")
        result = await limiter.wait_if_needed("https://reddit.com/r/python")
        print(f"  Waited: {result['waited']}\n")

        # Test 3: Different domain
        print("Test 3: First GitHub request")
        result = await limiter.wait_if_needed("https://github.com/phuc")
        print(f"  Waited: {result['waited']}")
        print(f"  Stats: {limiter.get_stats('github.com')}\n")

        # Test 4: View all stats
        print("Test 4: All domain stats")
        for domain, stats in limiter.get_all_stats().items():
            print(f"  {domain}: {stats['requests_used']}/{stats['requests_limit']} requests")

    asyncio.run(test())
