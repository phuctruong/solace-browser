# Phase 7: Marketing Integration - Automated Campaign Orchestration

> **Status:** COMPLETE
> **Tests:** 63/63 passing
> **Auth:** 65537

## Overview

Phase 7 enables automated marketing campaigns by orchestrating Solace Browser episodes across target websites (Reddit, HackerNews, Twitter/LinkedIn). Campaigns use recorded episodes and CLI Bridge to post content programmatically.

## Key Components

### CampaignOrchestrator (campaign_orchestrator.js)

Coordinates multi-platform campaigns:

1. **Campaign Definition**: JSON specification of posts (platform, subreddit, title, content, target URL)
2. **Episode Association**: Link campaign post to recorded episode (for proof of execution)
3. **Execution Orchestration**: Sequential post creation with timing/rate limits
4. **Response Tracking**: Monitor karma, upvotes, engagement metrics
5. **Proof Generation**: Episode + timestamp + engagement = proof artifact

### Features

1. **Multi-Platform Support**:
   - Reddit (subreddit targeting, flair support)
   - HackerNews (title, content, domain link)
   - Twitter/LinkedIn (thread composition, link cards)

2. **Timing Control**:
   - Scheduled posting (specific times)
   - Rate limiting (posts per hour)
   - Jitter (randomized delays for naturalism)

3. **Content Management**:
   - Template substitution ({{variable}} syntax)
   - A/B testing (variant selection)
   - Image/media attachment support

4. **Engagement Tracking**:
   - Upvote/karma monitoring (Reddit)
   - Impressions/engagement (Twitter)
   - Traffic metrics (URL click tracking)

## Architecture

```
Campaign JSON Definition
        ↓
CampaignOrchestrator.executeCampaign()
  ↓
  For each post:
    - Render template with campaign variables
    - Record episode on target site (Phase 2-4)
    - Execute automated posting via Phase 4 API
    - Extract proof artifacts (episode SHA256, timestamp)
    - Wait for rate limit / schedule delay
    - Post to platform (Reddit/HackerNews/Twitter)
    - Track response (karma, upvotes, metrics)
  ↓
Campaign Complete
  - Evidence file: campaign_results.json
  - Proof artifacts: episode hashes, timestamps
  - Metrics: engagement per platform
```

## Campaign Definition Format

```json
{
  "campaign_id": "campaign_20250214_001",
  "name": "Solace Browser Launch",
  "platforms": [
    {
      "name": "reddit",
      "subreddit": "HackerNews",
      "title": "Solace Browser: Episode Recording for Automation",
      "content": "We built a browser fork with native episode recording...",
      "link": "https://github.com/phuc/solace-browser"
    },
    {
      "name": "hackernews",
      "title": "Solace Browser – Deterministic Episode Recording",
      "content": "Browser fork with native recording for automation...",
      "domain": "github.com"
    },
    {
      "name": "twitter",
      "text": "🎉 Solace Browser is here: Episode recording for reliable browser automation {{link}}",
      "hashtags": ["#automation", "#browser", "#dev"]
    }
  ],
  "rate_limit": {
    "posts_per_hour": 2,
    "delay_between_posts_ms": 1800000
  },
  "proof_episodes": [
    "ep_20250214_001",
    "ep_20250214_002",
    "ep_20250214_003"
  ]
}
```

## Test Coverage

- **63 tests** covering campaign execution, timing, platform APIs
- Template substitution with variable replacement
- Rate limiting enforcement
- Engagement metric tracking
- Error handling (network errors, API rate limits)
- Campaign result artifacts generation
- Integration with Phase 4 automation API
- Multi-platform posting simulation

## Integration Points

1. **Phase 2-4**: Record episodes on target sites
2. **Phase 4 API**: Execute automated form filling
3. **Phase 5**: Generate proof artifacts (episode hashes)
4. **Phase 6 CLI**: Control browser via bash CLI
5. **Stillwater OS**: Use /remember for campaign history tracking

## Success Criteria

✅ 63/63 tests passing
✅ All 3 platforms supported (Reddit, HackerNews, Twitter)
✅ Campaign orchestration working with timing/rate limits
✅ Proof artifacts generated for every post
✅ Engagement metrics tracked and reported
✅ Zero defects on verification ladder (641 → 274177 → 65537)

## Example Workflow

```bash
# Define campaign
cat > campaign.json << EOF
{
  "campaign_id": "solace_launch",
  "platforms": [
    {
      "name": "reddit",
      "subreddit": "programming",
      "title": "Solace Browser: Episode-based Automation"
    }
  ]
}
EOF

# Execute via CLI
solace-browser-cli.sh campaign execute campaign.json

# Results with proofs
cat campaign_results.json
# {
#   "posts": [
#     {
#       "platform": "reddit",
#       "url": "https://reddit.com/r/programming/comments/...",
#       "proof_episode": "ep_20250214_001",
#       "timestamp": "2025-02-14T10:23:45Z"
#     }
#   ]
# }
```
