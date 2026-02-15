# Email Marketing Swarm Skill

**SKILL_ID**: `EMAIL_MARKETING_SWARM`
**SKILL_VER**: `v2.0.0`
**AUTHORITY**: 65537
**ROLE**: AI-powered email campaign creation, A/B testing, and personalization

---

## CONTRACT

**Input**: Email list, campaign goals, brand voice
**Output**: Personalized email campaigns, A/B test results, conversion tracking
**Guarantees**: CAN-SPAM compliant, unsubscribe honored, no purchased lists

---

## EXECUTION PROTOCOL (Lane A: CPU-Deterministic)

### Email Swarm Agents

**Copywriter Agent** (Haiku):
- Generate subject line variants (10 per campaign)
- Body copy generation with personalization tokens
- CTA optimization (button text, placement, color)

**A/B Test Agent** (Haiku):
- Test subject lines (5 variants to 10% of list)
- Winner sent to remaining 90%
- Statistical significance check (p < 0.05 required)

**Personalization Agent** (Haiku):
- Dynamic content based on user data
- Industry-specific examples
- Timezone-aware sending (local 9am for each recipient)

**Deliverability Agent** (CPU):
- Spam score analysis (<5/10 required)
- Blacklist checking
- Authentication verification (SPF, DKIM, DMARC)

### Drip Campaign Automation

**Developer Onboarding Flow** (for PZIP):
```yaml
day_0:
  trigger: "User downloads PZIP"
  email: "welcome_email"
  subject: "You downloaded PZIP! Here's how to get started"
  content: "Quick start guide + first benchmark"

day_3:
  trigger: "User hasn't run second compression"
  email: "tips_email"
  subject: "PZIP tips: Try it on CSV files for best results"
  content: "Case study: 93.5% savings on real datasets"

day_7:
  trigger: "User compressed 5+ files"
  email: "power_user_email"
  subject: "You're a PZIP power user! Here's what's next"
  content: "Advanced features + community invite"

day_14:
  trigger: "User inactive for 7 days"
  email: "re_engagement_email"
  subject: "We miss you! New PZIP features you might like"
  content: "What's new + use case ideas"
```

### Unsubscribe Handling

**ONE-CLICK UNSUBSCRIBE** (legally required):
```python
def handle_unsubscribe(email):
    # Immediate removal (no confirmation page tricks)
    remove_from_list(email)
    log_unsubscribe(email, timestamp=now())

    # Send confirmation (but NO re-engagement attempts)
    send_email(email, template="unsubscribe_confirmation")

    # Global suppression (never email again, even if re-imported)
    add_to_global_suppression_list(email)

    return {"status": "unsubscribed", "confirmed": True}
```

---

## VERIFICATION

**641 Edge Tests**: Spam score <5/10, all links work, unsubscribe functional
**274177 Stress Tests**: Send 10K emails without throttling issues
**65537 God Approval**: >25% open rate, >3% CTR, <0.1% spam complaints

---

**Integration**: Captures leads from `marketing-swarm-orchestrator` campaigns
**Auth**: 65537
