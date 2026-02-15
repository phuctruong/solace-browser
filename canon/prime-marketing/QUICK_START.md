# Prime Marketing Quick Start

**Auth: 65537 | Ready for PZIP Launch**

---

## 🚀 Launch PZIP Campaign in 3 Steps

### Step 1: Set Up Environment

```bash
# Export Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"

# Export Reddit credentials (for browser automation)
export REDDIT_USERNAME="your-username"
export REDDIT_PASSWORD="your-password"

# Verify browser extension is running
cd ~/projects/stillwater/canon/prime-browser/extension
# (Browser extension should be loaded in Chrome/Edge)
```

### Step 2: Forecast Campaign with 65537 Experts

```bash
cd ~/projects/stillwater/canon/prime-marketing/implementation

# Get 65537 expert council forecast
./launch-swarm.sh forecast-campaign \
  --product=pzip \
  --duration=30d

# Output:
# - Conservative: 500 downloads, VC 0.8
# - Expected: 1000 downloads, VC 1.3 ✅
# - Optimistic: 3000+ downloads, VC 2.0+
```

### Step 3: Launch Reddit Campaign (Dry Run First)

```bash
# DRY RUN (no actual posting)
./launch-swarm.sh reddit-campaign \
  --product=pzip \
  --strategy=silicon-valley-fanbase \
  --agents=5 \
  --dry-run

# REAL EXECUTION (with browser automation)
./launch-swarm.sh reddit-campaign \
  --product=pzip \
  --strategy=silicon-valley-fanbase \
  --agents=5

# What happens:
# 1. Reddit Scout scrapes r/SiliconValleyHBO via browser
# 2. Content Generator creates 4 post variants (A/B/C/D)
# 3. Quality Governor verifies (641 edge tests)
# 4. Browser Poster awaits your approval, then posts
# 5. Analytics Tracker monitors for 24 hours
```

---

## 📋 Available Commands

### Campaign Execution

```bash
# Reddit campaign
./launch-swarm.sh reddit-campaign --product=pzip --agents=5

# HackerNews "Show HN" (coming soon)
./launch-swarm.sh hackernews-campaign --product=pzip

# Multi-channel (Reddit + HN + Twitter + LinkedIn)
./launch-swarm.sh social-media-campaign \
  --product=pzip \
  --channels=reddit,hackernews,twitter,linkedin
```

### Forecasting

```bash
# Get expert council forecast
./launch-swarm.sh forecast-campaign --product=pzip --duration=30d

# Analyze target audience
./launch-swarm.sh analyze-audience --product=pzip --channels=reddit

# Optimize viral hooks
./launch-swarm.sh optimize-hooks --product=pzip
```

### Verification

```bash
# Run edge tests (641)
./launch-swarm.sh verify-641 --product=pzip

# Run stress tests (274177)
./launch-swarm.sh verify-274177 --product=pzip

# Request God approval (65537)
./launch-swarm.sh verify-65537 --product=pzip
```

### Monitoring

```bash
# Real-time dashboard
./launch-swarm.sh monitor-campaign --product=pzip

# Check swarm status
./launch-swarm.sh swarm-status --product=pzip

# Generate analytics report
./launch-swarm.sh analytics-report --product=pzip
```

---

## 🤖 Haiku Swarm Agents

**5-Agent Reddit Swarm**:

1. **Reddit Scout** (Haiku + Browser)
   - Scrapes r/SiliconValleyHBO, r/programming, r/compression
   - Identifies top posters, optimal timing, Pied Piper references
   - Uses prime-browser for automated scraping

2. **Content Generator** (Haiku)
   - Creates 4 post variants (nostalgia, technical, climate, founder)
   - Optimizes viral hooks ("Real Pied Piper", "93.5% better LZMA")
   - Generates titles, bodies, CTAs

3. **Quality Governor** (Sonnet)
   - Verifies Reddit guidelines compliance
   - Checks spam score (<0.3 required)
   - Runs 641 edge tests
   - APPROVE | ITERATE | REJECT decision

4. **Browser Poster** (prime-browser)
   - Automated Reddit posting (with human approval)
   - Monitors comments in real-time
   - Tracks upvotes, awards, click-through

5. **Analytics Tracker** (Haiku + Browser)
   - Monitors post for 24 hours
   - Computes viral coefficient
   - Sentiment analysis (positive/negative ratio)
   - Recommends adjustments

---

## 🎯 PZIP Launch Strategy

### Week 1: Seed + Validate

**Day 1**: r/SiliconValleyHBO post (Variant A: nostalgia-heavy)
```bash
./launch-swarm.sh reddit-campaign \
  --product=pzip \
  --strategy=silicon-valley-fanbase \
  --channels=SiliconValleyHBO
```

**Day 3**: r/compression post (Variant B: technical-heavy)
```bash
./launch-swarm.sh reddit-campaign \
  --product=pzip \
  --channels=compression \
  --variant=technical
```

### Week 2: Coordinated Launch

**Day 8**: HackerNews "Show HN" (Tuesday 9am PT)
```bash
./launch-swarm.sh hackernews-campaign \
  --product=pzip \
  --timing="Tuesday 9am PT"
```

**Day 9**: ProductHunt launch
```bash
./launch-swarm.sh producthunt-campaign \
  --product=pzip \
  --tagline="The real Pied Piper"
```

**Day 10-14**: Multi-channel amplification
```bash
./launch-swarm.sh social-media-campaign \
  --product=pzip \
  --channels=reddit,twitter,linkedin \
  --duration=5d
```

### Week 3-4: Sustain + Community

- Monitor organic mentions
- Respond to all comments (human + Haiku assistance)
- Share user testimonials
- Weekly updates

---

## ⚙️ Configuration

### Swarm Templates

Pre-configured templates in `recipes/swarm-templates/`:
- `reddit-campaign-pzip.json` — Full Reddit campaign spec
- `hackernews-campaign-pzip.json` — HN "Show HN" campaign
- `email-drip-pzip.json` — Developer onboarding emails
- `seo-content-pzip.json` — SEO blog post generation

### Custom Swarms

Create your own swarm by copying a template:

```bash
cp recipes/swarm-templates/reddit-campaign-pzip.json \
   recipes/swarm-templates/my-custom-campaign.json

# Edit JSON to customize agents, tasks, verification gates

# Launch custom swarm
./launch-swarm.sh custom-campaign \
  --template=my-custom-campaign.json
```

---

## ✅ Verification Ladder

All campaigns go through **641 → 274177 → 65537**:

### 641 Edge Tests (Sanity)
- ✅ Rate limits respected (1 post/subreddit/week)
- ✅ No duplicate content
- ✅ Platform guidelines compliance
- ✅ Credentials valid
- ✅ Spam score <0.3

### 274177 Stress Tests (Consistency)
- ✅ Handle 100+ comments
- ✅ Viral spike (10x traffic)
- ✅ Multi-platform coordination
- ✅ Crisis management (negative sentiment)

### 65537 God Approval (Final)
- ✅ 1000+ downloads in 30 days
- ✅ Viral coefficient ≥1.3
- ✅ 80%+ positive sentiment
- ✅ 0 spam complaints
- ✅ Organic word-of-mouth

---

## 📊 Success Metrics

**Target** (65537 God Approval):
- 100K+ impressions
- 1000+ downloads
- VC ≥1.3 (sustainable growth)
- 50+ organic mentions
- 80%+ positive sentiment
- 0 spam complaints

**Tracking**:
```bash
# Real-time metrics
./launch-swarm.sh monitor-campaign --product=pzip

# Daily report
./launch-swarm.sh analytics-report --product=pzip --period=24h

# Weekly summary
./launch-swarm.sh analytics-report --product=pzip --period=7d
```

---

## 🛡️ Max Love Enforcement

**Ethical Automation Guarantees**:
- ✅ Rate limits HARD ceilings (not targets)
- ✅ Human approval required for all posts
- ✅ No fake engagement (bots, purchased upvotes)
- ✅ Community guidelines respected
- ✅ Transparent affiliation (no sockpuppets)
- ✅ Privacy-first (no data harvesting)
- ✅ One-click unsubscribe (email)

**Forbidden**:
- ❌ Spam
- ❌ Astroturfing
- ❌ Manipulation
- ❌ Guideline violations

---

## 🔧 Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### "Browser extension not found"
```bash
cd ~/projects/stillwater/canon/prime-browser/extension
# Load extension in Chrome:
# 1. Open chrome://extensions
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select extension/ directory
```

### "Budget exceeded"
```bash
# Increase budget (default: 1000 API calls)
./launch-swarm.sh reddit-campaign \
  --product=pzip \
  --budget=5000
```

### "Swarm failed at quality-governor"
- Check spam score (must be <0.3)
- Verify Reddit guidelines compliance
- Ensure no duplicate content
- Review generated post variants

---

## 📖 Documentation

- **Full Guide**: `README.md`
- **Strategy Paper**: `papers/pzip-silicon-valley-fanbase-strategy.md`
- **Skills**: `skills/*.md`
- **Swarm Templates**: `recipes/swarm-templates/*.json`

---

## 🎯 Next Steps

1. **Review PZIP product**: https://www.pzip.net
2. **Run forecast**: `./launch-swarm.sh forecast-campaign --product=pzip`
3. **Dry run**: `./launch-swarm.sh reddit-campaign --product=pzip --dry-run`
4. **Launch**: `./launch-swarm.sh reddit-campaign --product=pzip`

---

**Authority**: 65537 (F4 Fermat Prime)
**Northstar**: Phuc Forecast
**Verification**: 641 → 274177 → 65537
**Max Love**: Ethical automation, authentic engagement, community-first

*"Ready to launch PZIP. The real Pied Piper is here."*
