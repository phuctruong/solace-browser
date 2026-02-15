# Content + SEO + GEO Engine

> **Star:** CONTENT_SEO_GEO
> **Version:** v3.0.0
> **Authority:** 65537 (F4 Fermat Prime)
> **Channel:** 5 (Logic — Content Architecture)
> **GLOW:** 91 (Discovery = Existence)
> **Lane:** A (CPU-Deterministic)
> **Status:** ACTIVE
> **Supersedes:** seo-automation-skill.md v2.0.0

---

## DNA-23

```
Discovery = SEO + GEO + Zero_Click
S = {keyword_strategy, content_templates, structured_data}
R = f(S, search_trends, AI_citation_patterns)
|S| << |R|  # Strategy is tiny; content is vast

2026 SHIFT: SEO alone is dead. Dual SEO/GEO is required.
Gartner: Search engine volume drops 25% by 2026 due to AI chatbots
AI platforms process 2.5B+ queries/month
```

---

## CONTRACT

**Input**: Product positioning, target keywords, competitive content landscape
**Output**: Content strategy, SEO-optimized pages, GEO-structured content, programmatic SEO templates
**Guarantees**:
- Dual-optimized (Google + AI citation engines)
- Counter Bypass for all metrics (Counter(), not LLM estimation)
- E-E-A-T compliant (Experience, Expertise, Authoritativeness, Trust)
- Never black-hat (sustainable rankings only)

---

## GENOME-79: THE 3 PILLARS

### Pillar 1: Traditional SEO (Google + Bing)

```
KEYWORD_RESEARCH (Counter Bypass Protocol):

def research_keywords(product, industry):
    """CPU-deterministic keyword scoring. Never LLM estimation."""
    base = extract_seed_keywords(product)
    expanded = []
    for kw in base:
        expanded += get_synonyms(kw)        # WordNet (deterministic)
        expanded += get_related(kw)          # Knowledge graph
        expanded += get_long_tail(kw)        # "how to X", "X vs Y", "best X for Y"

    scored = Counter()
    for kw in set(expanded):
        score = (
            search_volume(kw) * 0.3 +
            relevance(kw, product) * 0.3 +
            competition_inverse(kw) * 0.2 +
            intent_match(kw) * 0.2
        )
        scored[kw] = score

    return scored.most_common(50)  # Top 50, sorted deterministically

ON-PAGE SEO CHECKLIST:
  ✅ Title tag: primary keyword + brand (≤60 chars)
  ✅ Meta description: value prop + CTA (≤155 chars)
  ✅ H1: one per page, contains primary keyword
  ✅ H2/H3: structured hierarchy with secondary keywords
  ✅ URL: clean, keyword-containing slug
  ✅ Internal links: 3-5 relevant links per page
  ✅ Image alt text: descriptive, keyword-relevant
  ✅ Schema markup: Product, FAQ, HowTo, Article
  ✅ Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
  ✅ Mobile-first: responsive, touch-friendly
```

### Pillar 2: GEO (Generative Engine Optimization)

```
GEO = Structuring content so AI search engines cite you

AI CITATION ENGINES:
  - Google AI Overviews (replaces featured snippets)
  - ChatGPT (browsing mode, citations)
  - Perplexity (citation-first search)
  - Claude (with web search)
  - Bing Copilot

GEO OPTIMIZATION RULES:
  1. CLEAR CLAIMS: State facts explicitly, not implicitly
     ❌ "We offer great compression"
     ✅ "PZIP achieves 3.2x better compression than LZMA on structured data"

  2. CITE SOURCES: Link to evidence for every claim
     ✅ "Validated on 3,184 files across 17 file types (see benchmarks)"

  3. STRUCTURED DATA: Use schema.org markup
     ✅ Product schema, FAQ schema, HowTo schema

  4. ENTITY CLARITY: Make entities unambiguous
     ✅ "Stillwater OS, created by Phuc Truong, is a compiler-grade AI operating system"

  5. DIRECT ANSWERS: Structure content as Q&A pairs
     ✅ "What is PZIP? PZIP is a compression engine that..."

  6. COMPARISON TABLES: AI loves structured comparisons
     ✅ Feature comparison tables with clear winners

  7. DEFINITIONS FIRST: Lead paragraphs with definitions
     ✅ "PZIP (Prime ZIP) is a next-generation compression..."

GEO MONITORING TOOLS:
  - Goodie AI: Tracks visibility across ChatGPT, Gemini, Perplexity, Claude
  - Otterly AI: Monitors AI citations
  - Semrush AI Toolkit: Traditional SEO + GEO features
  - Manual: Search product name in each AI engine weekly
```

### Pillar 3: Programmatic SEO (pSEO)

```
pSEO = Automated creation of targeted pages for long-tail keywords

IMPLEMENTATION:
  1. Identify search query patterns
     Example: "PZIP vs [competitor]" for each competitor
     Example: "[file type] compression benchmark" for each file type
     Example: "how to compress [format]" for each format

  2. Acquire structured data
     - Benchmark results (from PZIP test runs)
     - File type specifications (from codec library)
     - Competitor feature lists (from SERP analysis)

  3. Design page templates
     Template: "PZIP vs {competitor}: {file_type} Compression Benchmark"
     Sections: Overview, Benchmark Results, When to Use Each, Conclusion

  4. Auto-generate pages
     For each (competitor, file_type) pair → unique page
     Content: 500+ words, 30%+ unique per page

  5. Technical SEO implementation
     - XML sitemap with all generated pages
     - Canonical URLs (prevent duplicate content)
     - Internal linking between related pages

  6. Progressive rollout
     Week 1: 10 pages (test indexing)
     Week 2-4: 50 pages (monitor performance)
     Month 2-3: 100+ pages (scale winners)

  QUALITY THRESHOLDS:
    - 500+ words unique content per page
    - 30%+ differentiation between pages
    - Monthly pruning of underperformers
    - Progressive rollout (never 10K pages at once)

  TIMELINE:
    Indexing: 2-4 weeks
    Traffic: 4-8 weeks
    Meaningful organic growth: 3-6 months
```

---

## E-E-A-T CONTENT FRAMEWORK

```
E-E-A-T = Experience + Expertise + Authoritativeness + Trustworthiness

EXPERIENCE:
  - First-person accounts of using the product
  - "I built X with PZIP and saved Y"
  - Real benchmarks, not theoretical claims

EXPERTISE:
  - Technical depth (show the math, show the code)
  - Author credentials (link to profiles, papers)
  - Domain-specific knowledge (compression theory, not generic)

AUTHORITATIVENESS:
  - Cited by other sources (backlinks)
  - Referenced in AI answers (GEO)
  - Community endorsement (GitHub stars, testimonials)

TRUSTWORTHINESS:
  - Accurate claims with evidence
  - Updated content (not stale)
  - Transparent about limitations
  - HTTPS, privacy policy, accessible
```

---

## CONTENT CREATION PROTOCOL

```
HUMAN-AI CO-CREATION:

1. STRATEGY (Human):
   - Define topic from keyword research
   - Choose content type (blog, tutorial, comparison, case study)
   - Outline key points and unique angle

2. DRAFT (AI — Haiku for speed):
   - Generate first draft from outline
   - Include structured data markup
   - Optimize for both SEO and GEO

3. ENRICH (Human):
   - Add personal experience and unique insights
   - Add real data, benchmarks, screenshots
   - Inject brand voice and personality

4. OPTIMIZE (CPU):
   - SEO score computation (keyword density, readability, structure)
   - GEO compliance check (clear claims, citations, structured data)
   - Flesch readability score ≥ 60
   - If score < 80%, iterate

5. APPROVE (Human gate):
   - Final review before publishing
   - Fact-check all claims
   - Verify links and references
```

---

## STATE MACHINE

```
STATES = {
  KEYWORD_RESEARCH,    # Discover opportunities
  CONTENT_PLANNING,    # Editorial calendar
  CONTENT_CREATION,    # Write + optimize
  TECHNICAL_SEO,       # On-page + schema + CWV
  GEO_OPTIMIZATION,    # AI citation optimization
  PSEO_GENERATION,     # Programmatic page creation
  MONITORING,          # Rank tracking + AI citation monitoring
  PRUNING              # Remove underperformers
}

TRANSITIONS:
  KEYWORD_RESEARCH → CONTENT_PLANNING    (≥50 keywords scored)
  CONTENT_PLANNING → CONTENT_CREATION    (calendar defined)
  CONTENT_CREATION → TECHNICAL_SEO       (content published)
  TECHNICAL_SEO → GEO_OPTIMIZATION       (SEO checklist complete)
  GEO_OPTIMIZATION → MONITORING          (GEO compliance verified)
  MONITORING → PRUNING                   (30-day data collected)
  PRUNING → CONTENT_PLANNING             (cycle continues)

  PSEO_GENERATION runs in parallel with CONTENT_CREATION

FORBIDDEN:
  CONTENT_CREATION before KEYWORD_RESEARCH (writing without strategy)
  PSEO_GENERATION before TECHNICAL_SEO (scaling without foundation)
```

---

## VERIFICATION

```
641 Edge Tests (7, prime!):
  - No keyword stuffing (density < 3%)
  - Readability ≥ 60 Flesch score
  - All pages have meta title + description
  - Schema markup validates (Google Rich Results Test)
  - No broken internal links
  - All images have alt text
  - Mobile-friendly (Google Mobile Test)

274177 Stress Tests (5):
  - Rank tracking improvement over 30 days
  - AI citation monitoring (mentioned in ≥1 AI engine)
  - pSEO pages indexed within 2 weeks
  - Content freshness: all pages updated within 90 days
  - Cross-browser rendering (Chrome, Firefox, Safari)

65537 God Approval (3):
  - Organic traffic increase ≥ 20% (90-day window)
  - AI citation rate ≥ 10% of target queries
  - Domain authority increase (Ahrefs/Moz)
```

---

## INTEGRATION

- **Upstream**: positioning-engine.md (messaging), community-growth-engine.md (content topics)
- **Downstream**: landing-page-architect.md (page content), social-media-automation-skill.md
- **Supersedes**: seo-automation-skill.md v2.0.0 (fully replaced)

---

*"SEO alone is dead. Dual SEO/GEO or invisible." — 2026 Reality*
*"Auth: 65537"*
