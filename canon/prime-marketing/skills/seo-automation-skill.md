# SEO Automation Skill

**SKILL_ID**: `SEO_AUTOMATION`
**SKILL_VER**: `v2.0.0`
**AUTHORITY**: 65537
**ROLE**: AI-powered SEO research, optimization, and content strategy

---

## CONTRACT

**Input**: Target keywords, product description, competitor URLs
**Output**: SEO-optimized content, keyword strategy, SERP analysis
**Guarantees**: Data-driven recommendations, no black-hat tactics, sustainable rankings

---

## EXECUTION PROTOCOL (Lane A: CPU-Deterministic)

### Keyword Research (Counter Bypass Protocol)

```python
def research_keywords(product, industry):
    """Deterministic keyword analysis using Counter(), not LLM estimation."""

    # Base keywords from product
    base_keywords = extract_keywords(product)

    # Expand using semantic relationships (deterministic)
    related = []
    for kw in base_keywords:
        related.extend(get_synonyms(kw))  # From WordNet, not LLM
        related.extend(get_related_terms(kw))  # From knowledge graph

    # Score keywords (CPU-based scoring)
    scored = Counter()
    for kw in set(base_keywords + related):
        score = (
            search_volume(kw) * 0.4 +  # From keyword DB
            relevance_score(kw, product) * 0.3 +  # Cosine similarity
            competition_inverse(kw) * 0.3  # From SERP analysis
        )
        scored[kw] = score

    # Return top 20, sorted deterministically
    return scored.most_common(20)
```

### SERP Analysis

**Scrape top 10 results** for each keyword using prime-browser:
- Title patterns
- Meta description patterns
- H1/H2 structure
- Word count
- Backlink profile
- Domain authority

**Identify gaps** (what top results DON'T cover):
- Missing subtopics
- Unanswered questions
- Better UX opportunities

### Content Optimization

**AI-generated content** PLUS **human review gate**:
1. LLM generates draft (Haiku for speed)
2. SEO score computed (CPU-based)
3. If score < 80%, iterate
4. Human approval required before publishing

---

## VERIFICATION

**641 Edge Tests**: No keyword stuffing, readability >60 Flesch score
**274177 Stress Tests**: Rank tracking over 30 days
**65537 God Approval**: Organic traffic increase >20%

---

**Integration**: Feeds content to `marketing-swarm-orchestrator`
**Auth**: 65537
