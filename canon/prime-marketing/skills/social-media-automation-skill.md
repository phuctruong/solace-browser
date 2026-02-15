# Social Media Automation Skill

**SKILL_ID**: `SOCIAL_MEDIA_AUTOMATION`
**SKILL_VER**: `v2.0.0`
**AUTHORITY**: 65537
**ROLE**: Multi-platform social media scheduling, posting, and engagement

---

## CONTRACT

**Input**: Content calendar, brand voice guidelines, target platforms
**Output**: Automated posting, engagement tracking, sentiment analysis
**Guarantees**: Platform guidelines respected, authentic engagement, no spam

---

## EXECUTION PROTOCOL (Lane A: CPU-Deterministic)

### Multi-Platform Agent Swarm

**Twitter Agent** (Haiku):
- Generate tweet variants (text, threads, polls)
- Optimal timing analysis (when followers are active)
- Hashtag optimization (trending + evergreen mix)
- Engagement monitoring (reply to mentions within 30min)

**LinkedIn Agent** (Haiku):
- Professional tone enforcement
- Long-form posts (600-1200 words)
- Comment on industry posts (thought leadership)
- Connection requests to target audience

**Reddit Agent** (prime-browser):
- Community participation (NOT just posting)
- Karma building through genuine contributions
- Strategic product mentions (10% of comments max)
- Moderator relationship building

**HackerNews Agent** (prime-browser):
- Comment quality > quantity
- Technical depth required
- No marketing speak
- Upvote patterns analysis (what gets traction)

### Content Scheduling

**Optimal Posting Times** (research-based):
- Twitter: 9am PT, 12pm PT, 9pm PT (3x daily max)
- LinkedIn: 8am PT Tue/Wed (professional browsing)
- Reddit: Varies by subreddit (tracked per community)
- HackerNews: 8-10am PT Tue-Thu (front page window)

**Rate Limiting** (HARD CEILINGS):
```python
RATE_LIMITS = {
    "twitter": {"posts_per_day": 10, "replies_per_hour": 20},
    "linkedin": {"posts_per_day": 2, "comments_per_day": 10},
    "reddit": {"posts_per_subreddit_per_week": 1, "comments_per_day": 20},
    "hackernews": {"posts_per_week": 2, "comments_per_day": 5}
}

def enforce_rate_limit(platform, action):
    count = get_action_count(platform, action, window=RATE_LIMITS[platform]["window"])
    if count >= RATE_LIMITS[platform][action]:
        return DENY("Rate limit exceeded")
    return ALLOW
```

### Engagement Automation

**Auto-Reply Triggers** (with human approval gate):
1. Technical questions → Generate answer, flag for human review
2. Praise → Simple thank you (automated OK)
3. Criticism → NEVER auto-reply, always human
4. Mentions → Alert human within 5 minutes

**Never Automated**:
- ❌ Negative sentiment responses
- ❌ Complex technical debates
- ❌ Crisis management
- ❌ Influencer outreach

---

## VERIFICATION

**641 Edge Tests**: No duplicate posts, rate limits respected
**274177 Stress Tests**: Handle 100+ mentions simultaneously
**65537 God Approval**: >80% positive sentiment, no spam complaints

---

**Integration**: Coordinates with `marketing-swarm-orchestrator` for campaign timing
**Auth**: 65537
