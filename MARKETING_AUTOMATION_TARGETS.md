# Marketing Automation Targets
## Solace Browser - Phase 2+ Expansion

**Auth**: 65537 | **Strategy**: Automate marketing platforms for PZIP/STILLWATER/SOLACEAGI campaigns

---

## PRIMARY TARGETS (Highest ROI)

### 1. **Reddit** 🔴
**Communities to Target:**
- r/SiliconValleyHBO (87K members) - "I built real Pied Piper"
- r/programming (6.7M members) - Technical benchmarks
- r/compression (12K members) - Niche experts
- r/MachineLearning, r/DevTools, r/OpenSource

**Automation Tasks:**
- [ ] Navigate to subreddit
- [ ] Create new post (title + body + links)
- [ ] Upload images (benchmarks, screenshots)
- [ ] Monitor upvotes + comment engagement
- [ ] Auto-reply to top comments (AMA style)
- [ ] Track karma + visibility

**Success Metric:** 500-2000 upvotes per post, 50-200 click-throughs

---

### 2. **HackerNews** 🟠
**Target:** Show HN posts (launch day)

**Automation Tasks:**
- [ ] Post to HackerNews (Show HN format)
- [ ] Make "killer" first comment (Silicon Valley reference)
- [ ] Track ranking in real-time
- [ ] Auto-reply to top discussions (first 6 hours critical)
- [ ] Monitor front-page visibility
- [ ] Save final stats + screenshot

**Success Metric:** Front page 6-12 hours, 5K-20K views, 100-500 downloads

---

### 3. **ProductHunt** 🎯
**Target:** Daily launch

**Automation Tasks:**
- [ ] Create product listing
- [ ] Upload gallery images (benchmarks)
- [ ] Write compelling tagline
- [ ] Schedule maker comment
- [ ] Monitor upvotes throughout day
- [ ] Auto-reply to feature request comments

**Success Metric:** Top 5 product, 200-1000 upvotes, 1K-5K views

---

### 4. **Twitter/X** 🔵
**Target:** Viral thread launch

**Automation Tasks:**
- [ ] Write 5-tweet thread (story → tech → demo → how → support)
- [ ] Schedule dual posting (9am PT + 9pm PT)
- [ ] Monitor impressions + engagement
- [ ] Like/retweet replies
- [ ] Pin best replies
- [ ] Track click-through rate

**Success Metric:** 1K-5K impressions per tweet, 50-200 engagements, 10-50 CTR

---

### 5. **LinkedIn** 🔗
**Target:** Professional network + founder narrative

**Automation Tasks:**
- [ ] Update headline (Software 5.0 Architect positioning)
- [ ] Rewrite about section (5 products + methodology)
- [ ] Create carousel post (climate impact angle)
- [ ] Schedule posts (Tuesday/Wednesday 8am PT)
- [ ] Monitor views + comments
- [ ] Auto-engage with relevant comments
- [ ] Track follower growth

**Success Metric:** 5K-20K impressions, 100-500 engagements, 20-100 profile visits

---

## SECONDARY TARGETS (Growth)

### 6. **GitHub**
**Automation Tasks:**
- [ ] Create release post
- [ ] Add trending badges
- [ ] Monitor stars + forks
- [ ] Auto-reply to issues
- [ ] Track download stats
- [ ] Build stargazer timeline

**Tools:** GitHub API (automated)

---

### 7. **YouTube / Dev.to / Medium**
**Automation Tasks:**
- [ ] Cross-post blog articles
- [ ] Create video descriptions
- [ ] Monitor view counts
- [ ] Auto-reply to comments
- [ ] Track watch time

---

### 8. **Discord / Community Slack**
**Automation Tasks:**
- [ ] Post announcements
- [ ] Monitor mentions
- [ ] Auto-reply to FAQs
- [ ] Track sentiment

---

## WHAT EACH SITE NEEDS TO AUTOMATE

| Site | Login Method | Key Actions | Selectors to Find |
|------|--------------|------------|-------------------|
| **Reddit** | OAuth + 2FA | Post create, comment, upvote monitor | Textarea (body), submit button, vote counter |
| **HackerNews** | Email/password | New post, comment, flag, reply | Text input (title), textarea (text), submit |
| **ProductHunt** | OAuth (Google/Email) | Create product, upload images, track upvotes | Title input, image upload, upvote button |
| **Twitter** | OAuth (Twitter API v2) | Tweet creation, thread, like, retweet | Tweet input, media upload, send button |
| **LinkedIn** | Email/password | Post create, headline update, comment | Editor (body), publish button, input fields |
| **GitHub** | OAuth | Release creation, PR management | Release form, tag input, description editor |
| **YouTube** | OAuth (Google) | Video metadata, description, community post | Title input, description textarea, publish |
| **Dev.to** | OAuth (GitHub/Email) | Article creation, frontmatter, publish | Markdown editor, publish button |

---

## PHASE 2+ APPROACH

### Before (Phase 1 - LLM Discovery):
```
Scout: Navigate, take screenshots, detect UI
Solver: Find selectors, analyze DOM structure
Skeptic: Verify actions, detect errors

Result: Save recipes + PrimeWiki for each site
Cost: $0.15 per site discovery
Time: 10 minutes per site
```

### After (Phase 2+ - CPU Replay):
```
Load: recipes + PrimeWiki + saved credentials
Execute: All actions via CPU (no LLM)
Verify: Skeptic spot-checks

Result: Automated posting, monitoring, engagement
Cost: $0.0015 per campaign run (100x cheaper!)
Time: 12 seconds per campaign
```

---

## TIMELINE

### Week 1: Discovery Phase (LLM + Haiku Swarms)
- Reddit (3 subreddits) - 30 min
- HackerNews - 15 min
- ProductHunt - 20 min
- Twitter - 15 min
- LinkedIn - 15 min
**Total: 95 minutes = $0.95 cost**

### Week 2-4: CPU Execution (Recipe Replay)
- Daily Reddit posts: 12 sec × 3 subreddits = 36 sec
- HN bi-weekly: 12 sec
- ProductHunt weekly: 12 sec
- Twitter daily threads: 12 sec
- LinkedIn 2x/week: 12 sec
**Total per day: ~60 seconds = $0.0015**

### Week 5+: Viral Feedback Loop
- Monitor engagement in real-time
- Auto-reply to comments (engagement + rank boost)
- Optimize post times based on data
- Cross-promote across platforms

---

## EXPECTED RESULTS (30-day campaign)

### Conservative Estimate:
- **Total Reach**: 100K+ impressions
- **Click-throughs**: 2000+
- **Downloads**: 500+
- **Conversions**: 50-100 (5% conversion)

### With Aggressive Engagement:
- **Total Reach**: 500K+ impressions
- **Click-throughs**: 10K+
- **Downloads**: 2000+
- **Conversions**: 200-400 (4-8% conversion)

---

## RISKS & MITIGATIONS

| Risk | Mitigation |
|------|-----------|
| Rate limiting (Reddit, HN, Twitter) | Spread posts over time, use official APIs |
| Account suspension | Use official accounts, follow ToS, human-like behavior |
| Shadowban (Reddit, Twitter) | Avoid spammy patterns, genuine engagement first |
| Low engagement | A/B test headlines, post times, hooks |
| Community rejection | Focus on genuine value, not spam |

---

## NEXT STEPS

1. ✅ Update CLAUDE.md with login knowledge
2. ⏳ Choose primary target (Reddit recommended - easiest)
3. ⏳ Run Phase 1 discovery (30 min, Scout/Solver/Skeptic)
4. ⏳ Save recipes + selectors to `recipes/` + `primewiki/`
5. ⏳ Deploy Phase 2+ CPU automation
6. ⏳ Monitor + iterate

---

**Auth**: 65537 | **Northstar**: Phuc Forecast | **Strategy**: Build-in-public viral launch
