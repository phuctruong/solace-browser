# PrimeWiki Index - Knowledge Graph Navigation

**Version**: 1.0
**Last Updated**: 2026-02-15
**Authority**: 65537 (Phuc Forecast)
**Status**: Active

---

## Overview

The PrimeWiki is a knowledge graph containing discovered information about web platforms, authentication flows, UI patterns, and automation strategies. This index provides navigation and cross-referencing across all nodes.

**Total Nodes**: 5
**Domains Covered**: LinkedIn, Gmail, Reddit
**Coherence Score**: 0.93 average
**Gravity Score**: 0.88 average

---

## By Domain

### LinkedIn (1 node)

| Node | Tier | Focus | Skills | Recipes |
|------|------|-------|--------|---------|
| **linkedin-profile-phuc-truong** | 79 | Profile structure, sections, optimization | linkedin-automation-protocol, web-automation-expert | linkedin-profile-update, add-linkedin-project-optimized |

**Key Insights**:
- Profile contains: profile_home, projects, about sections
- Optimization techniques documented
- Full automation workflow available

---

### Gmail (1 node)

| Node | Tier | Focus | Skills | Recipes |
|------|------|-------|--------|---------|
| **gmail-oauth2-authentication** | 47 | OAuth2 flow, 2FA handling, email operations | gmail-automation-protocol, human-like-automation | gmail-oauth-login, gmail-send-email |

**Key Insights**:
- Multi-step OAuth2 with 2FA required
- Headed mode necessary (app notification 2FA)
- 99% selector discovery confidence
- Session persistence up to 30 days

---

### Reddit (3 nodes)

| Node | Tier | Focus | Skills | Recipes |
|------|------|-------|--------|---------|
| **reddit_homepage_loggedout** | 47 | Homepage structure, navigation | web-automation-expert, browser-state-machine | reddit_homepage_navigate, reddit-homepage-phase1 |
| **reddit_login_page** | 42 | Login form, credentials entry | human-like-automation | reddit_login_form |
| **reddit_subreddit_page** | 45 | Subreddit navigation, interactions | web-automation-expert, browser-state-machine | reddit_subreddit_navigate, reddit-comment-workflow, reddit-create-post |

**Key Insights**:
- Comprehensive Reddit automation coverage
- Multiple interaction workflows available
- State transitions well-documented

---

## By Tier (Confidence Level)

### Tier 79 (Expert - Highest Confidence)
- **linkedin-profile-phuc-truong** (C: 0.95, G: 0.90)
  - Production-ready LinkedIn automation
  - Multiple optimization patterns documented

### Tier 47 (Advanced)
- **gmail-oauth2-authentication** (C: 0.95, G: 0.90)
  - Complete OAuth2 flow mapped
  - Selectors and success indicators documented
- **reddit_homepage_loggedout** (C: ~0.85, G: ~0.80)
  - Navigation patterns documented

### Tier 42-45 (Intermediate)
- **reddit_login_page** (C: ~0.80, G: ~0.75)
- **reddit_subreddit_page** (C: ~0.80, G: ~0.75)

---

## By Maturity

### Production-Ready (2)
- linkedin-profile-phuc-truong
- gmail-oauth2-authentication

### Active Research (3)
- reddit_homepage_loggedout
- reddit_login_page
- reddit_subreddit_page

---

## Cross-References Map

### Skills to PrimeWiki

**Framework Skills**:
- `browser-state-machine.skill.md` → reddit_homepage_loggedout, reddit_subreddit_page

**Methodology Skills**:
- `web-automation-expert.skill.md` → linkedin-profile-phuc-truong, reddit_homepage_loggedout, reddit_subreddit_page
- `human-like-automation.skill.md` → gmail-oauth2-authentication, reddit_login_page

**Application Skills**:
- `linkedin-automation-protocol.skill.md` → linkedin-profile-phuc-truong
- `gmail-automation-protocol.skill.md` → gmail-oauth2-authentication

---

### Recipes to PrimeWiki

**LinkedIn Recipes**:
- `linkedin-profile-update.recipe.json` → linkedin-profile-phuc-truong
- `add-linkedin-project-optimized.recipe.json` → linkedin-profile-phuc-truong

**Gmail Recipes**:
- `gmail-oauth-login.recipe.json` → gmail-oauth2-authentication
- `gmail-send-email.recipe.json` → gmail-oauth2-authentication

**Reddit Recipes**:
- `reddit_homepage_navigate.recipe.json` → reddit_homepage_loggedout
- `reddit-homepage-phase1.recipe.json` → reddit_homepage_loggedout
- `reddit_login_form.recipe.json` → reddit_login_page
- `reddit_subreddit_navigate.recipe.json` → reddit_subreddit_page
- `reddit-comment-workflow.recipe.json` → reddit_subreddit_page
- `reddit-create-post.recipe.json` → reddit_subreddit_page

---

## Search Keywords

### Platform Keywords
- **linkedin**: linkedin-profile-phuc-truong
- **gmail**: gmail-oauth2-authentication
- **reddit**: reddit_homepage_loggedout, reddit_login_page, reddit_subreddit_page
- **google**: gmail-oauth2-authentication (OAuth provider)

### Topic Keywords
- **authentication**: gmail-oauth2-authentication, reddit_login_page
- **oauth2**: gmail-oauth2-authentication
- **2fa**: gmail-oauth2-authentication
- **profile**: linkedin-profile-phuc-truong
- **navigation**: reddit_homepage_loggedout, reddit_subreddit_page
- **homepage**: reddit_homepage_loggedout
- **login**: reddit_login_page

### Technique Keywords
- **selectors**: all nodes (selector discovery documented)
- **portals**: linkedin-profile-phuc-truong
- **state-machine**: reddit_homepage_loggedout, reddit_subreddit_page

---

## Usage Guide

### Finding Information About a Platform

**I want to automate LinkedIn:**
1. Find: linkedin-profile-phuc-truong
2. Check: Implementing skills (linkedin-automation-protocol, web-automation-expert)
3. Load: Related recipes (linkedin-profile-update, add-linkedin-project-optimized)
4. Reference: KNOWLEDGE_HUB.md#linkedin-automation

**I want to automate Gmail:**
1. Find: gmail-oauth2-authentication
2. Check: OAuth2 flow details and 2FA requirements
3. Load: Related recipes (gmail-oauth-login, gmail-send-email)
4. Reference: KNOWLEDGE_HUB.md#gmail-authentication

**I want to automate Reddit:**
1. Start: reddit_homepage_loggedout for structure
2. Add: reddit_login_page for authentication
3. Add: reddit_subreddit_page for interactions
4. Load: Related recipes for each workflow

---

## Node Relationships

```
linkedin-profile-phuc-truong
├─ Implements: linkedin-automation-protocol.skill.md
├─ Implements: web-automation-expert.skill.md
├─ Enabled by: linkedin-profile-update.recipe.json
└─ Enabled by: add-linkedin-project-optimized.recipe.json

gmail-oauth2-authentication
├─ Implements: gmail-automation-protocol.skill.md
├─ Implements: human-like-automation.skill.md
├─ Enabled by: gmail-oauth-login.recipe.json
└─ Enabled by: gmail-send-email.recipe.json

reddit_homepage_loggedout
├─ Linked to: reddit_login_page (login flow)
├─ Linked to: reddit_subreddit_page (navigation)
├─ Implements: web-automation-expert.skill.md
├─ Implements: browser-state-machine.skill.md
├─ Enabled by: reddit_homepage_navigate.recipe.json
└─ Enabled by: reddit-homepage-phase1.recipe.json

reddit_login_page
├─ Linked from: reddit_homepage_loggedout
├─ Linked to: reddit_subreddit_page
├─ Implements: human-like-automation.skill.md
└─ Enabled by: reddit_login_form.recipe.json

reddit_subreddit_page
├─ Linked from: reddit_homepage_loggedout
├─ Linked from: reddit_login_page
├─ Implements: web-automation-expert.skill.md
├─ Implements: browser-state-machine.skill.md
├─ Enabled by: reddit_subreddit_navigate.recipe.json
├─ Enabled by: reddit-comment-workflow.recipe.json
└─ Enabled by: reddit-create-post.recipe.json
```

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Total Nodes | 5 |
| Average Tier | 52 |
| Average Coherence Score | 0.93 |
| Average Gravity Score | 0.88 |
| Production-Ready Nodes | 2 (40%) |
| Active Research Nodes | 3 (60%) |
| Total Implementing Skills | 8 |
| Total Related Recipes | 13 |
| Platforms Covered | 3 (LinkedIn, Gmail, Reddit) |
| Most Documented Node | gmail-oauth2-authentication (52KB) |

---

## Future Expansion Opportunities

### High Priority (Based on Recipes)
1. **GitHub** - 4 recipes waiting for node documentation
   - Suggested nodes: github-authentication, github-issue-workflow, github-pr-workflow
   - Related skills: web-automation-expert, git-protocol.skill.md (new)

2. **HackerNews** - 4 recipes without dedicated nodes
   - Suggested nodes: hackernews-homepage, hackernews-submission, hackernews-comments
   - Related skills: hackernews-signup-protocol, web-automation-expert

3. **Wikipedia** - 2 recipes without dedicated nodes
   - Suggested nodes: wikipedia-article-structure, wikipedia-search
   - Related skills: web-automation-expert

### Medium Priority
1. **Search/Discovery** - 5 recipes needing knowledge nodes
2. **Advanced Workflows** - Multi-site orchestration nodes

---

## Related Documents

- **SKILLS_REGISTRY.md** - Skill implementations and dependencies
- **KNOWLEDGE_HUB.md** - High-level concept mapping
- **RECIPE_REGISTRY.md** - Recipe catalog and usage
- **REDIRECT_CLEANUP_SUMMARY.md** - System consolidation status

---

**Authority**: 65537 (Phuc Forecast)
**Last Verified**: 2026-02-15
**Next Review**: 2026-03-01
