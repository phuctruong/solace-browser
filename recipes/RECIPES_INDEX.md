# Recipe Library Index

**Last Updated**: 2026-02-15
**Total Recipes**: 28 canonical + 6 archived variants
**Consolidation**: Phase 3.5 complete

---

## Table of Contents

- [LinkedIn Workflows](#linkedin-workflows)
- [Gmail Workflows](#gmail-workflows)
- [HackerNews Workflows](#hackernews-workflows)
- [Reddit Workflows](#reddit-workflows)
- [Search & Discovery](#search--discovery)
- [Other](#other)

---

## LinkedIn Workflows

### linkedin-profile-update.recipe.json (CANONICAL)

**Description**: Update LinkedIn profile with expert optimizations

**Variants** (archived to `artifacts/ARCHIVE_PHASE3/`):
- `10-10-optimization` - More aggressive headline and about optimizations
- `harsh-qa-fixes` - QA-focused refinements
- `with-projects` - Includes project additions and updates

**Execution Time**: ~5 minutes
**Success Rate**: 95%
**Evidence**: Complete screenshot + ARIA + HTML snapshots

**See Also**:
- Skill: [linkedin-automation-protocol.skill.md](../canon/skills/application/linkedin-automation-protocol.skill.md)
- PrimeWiki: [linkedin-profile-phuc-truong.primewiki.json](../primewiki/linkedin-profile-phuc-truong.primewiki.json)

---

### add-linkedin-project-optimized.recipe.json (CANONICAL)

**Description**: Add optimized project to LinkedIn profile

**Variants** (archived):
- `delete-linkedin-projects-openclaw` - Delete workflow (different, kept separate)
- `delete-old-linkedin-projects` - Older delete workflow

**Execution Time**: ~3 minutes
**Success Rate**: 100%
**Portal Library**: Pre-mapped LinkedIn project edit paths

**Related**: linkedin-profile-update.recipe.json

---

## Gmail Workflows

### gmail-oauth-login.recipe.json (CANONICAL)

**Description**: Complete OAuth 2.0 login flow for Gmail

**Variants** (archived to `artifacts/ARCHIVE_PHASE3/`):
- `oauth2-explicit` - gmail-oauth2-login.recipe.json (OAuth 2.0 specific)
- `headed-browser` - gmail-login-headed.recipe.json (headed browser variant)

**Execution Time**: ~15 seconds (one-time)
**Success Rate**: 100%
**Session Lifetime**: 14-30 days

**Note**: Use with saved session for subsequent logins (~2 seconds)

**See Also**:
- Skill: [gmail-automation-protocol.skill.md](../canon/skills/application/gmail-automation-protocol.skill.md)
- Portal Library: 54 verified Gmail selectors

---

### gmail-send-email.recipe.json (CANONICAL)

**Description**: Compose and send email via Gmail

**Execution Time**: ~10 seconds
**Success Rate**: 100%
**Dependencies**: Requires gmail-oauth-login session

**Key Selectors**:
- Compose: `[gh='cm']`
- To field: `input[aria-autocomplete='list']`
- Send: `Ctrl+Enter` (keyboard shortcut)

---

## HackerNews Workflows

These are different workflows (not duplicates) - keep all:

### hackernews-homepage-phase1.recipe.json

**Description**: Navigate HackerNews homepage and explore

**Protocol**: LOOK-FIRST-ACT-VERIFY

---

### hackernews-comment-workflow.recipe.json

**Description**: Post comment on HackerNews story

---

### hackernews-hide-workflow.recipe.json

**Description**: Hide story on HackerNews

---

### hackernews-upvote-workflow.recipe.json

**Description**: Upvote story on HackerNews

---

## Reddit Workflows

### reddit-create-post.recipe.json

**Description**: Create new post on Reddit

---

### reddit-comment-workflow.recipe.json

**Description**: Post comment on Reddit thread

---

### reddit-upvote-workflow.recipe.json

**Description**: Upvote post/comment on Reddit

---

### reddit_homepage_navigate.recipe.json

**Description**: Navigate Reddit homepage and explore

---

### reddit_login_form.recipe.json

**Description**: Reddit login workflow

---

### reddit_subreddit_navigate.recipe.json

**Description**: Navigate to specific subreddit

---

### reddit-homepage-phase1.recipe.json

**Description**: Reddit Phase 1 exploration workflow

---

## Search & Discovery

### llm-github-search.recipe.json

**Description**: Search GitHub repositories using LLM reasoning

---

### llm-google-search-demo.recipe.json

**Description**: Google search with LLM analysis

---

### llm-hackernews.recipe.json

**Description**: HackerNews search and discovery

---

### llm-wiki-ai.recipe.json

**Description**: Wikipedia AI-related article search

---

### wikipedia-demo.recipe.json

**Description**: Wikipedia navigation and extraction demo

---

## Other

### prime-mermaid-layer-implementation.recipe.json

**Description**: PrimeMermaid visual layer implementation

---

### silicon-valley-profile-discovery.recipe.json

**Description**: Discover and analyze Silicon Valley profiles

---

## Archived Test Recipes

The following test/demo recipes have been archived to `artifacts/ARCHIVE_PHASE3/RECIPES/`:

- `test-ep-quick.recipe.json` - Quick test recipe
- `demo-1771110591.recipe.json` - Demo execution trace
- `quick-validation-test.recipe.json` - Validation test
- `quick-validation-workflow.recipe.json` - Validation workflow

**Reason**: Temporary test files, not part of core workflow library

**Recovery**: All archived files preserved in `artifacts/ARCHIVE_PHASE3/RECIPES/ARCHIVE_INDEX.md`

---

## Cross-Reference Map

### By Website

**LinkedIn**:
- Canonical: linkedin-profile-update.recipe.json, add-linkedin-project-optimized.recipe.json
- Skill: [linkedin-automation-protocol.skill.md](../canon/skills/application/linkedin-automation-protocol.skill.md)

**Gmail**:
- Canonical: gmail-oauth-login.recipe.json, gmail-send-email.recipe.json
- Skill: [gmail-automation-protocol.skill.md](../canon/skills/application/gmail-automation-protocol.skill.md)

**HackerNews**:
- Canonical: hackernews-*.recipe.json (4 workflows)
- Skill: [hackernews-signup-protocol.skill.md](../canon/skills/application/hackernews-signup-protocol.skill.md)

**Reddit**:
- Canonical: reddit-*.recipe.json (7 workflows)

**Search & Discovery**:
- Canonical: llm-*.recipe.json, wikipedia-demo.recipe.json (5 recipes)

---

## Legend

- **CANONICAL**: Primary recipe for this workflow
- **VARIANT**: Related variant (archived, reference only)
- **ARCHIVED**: Test/temporary files (preserved in artifacts/)
- **DIFFERENT**: Not a duplicate, kept separate workflow

---

## How to Use This Index

1. **Find a workflow**: Search by website or task name
2. **Check for variants**: See if variants exist (archived)
3. **View canonical**: Use CANONICAL recipe for execution
4. **Reference skill**: Cross-reference skill for implementation details
5. **Explore PrimeWiki**: Read PrimeWiki node for evidence and research

---

**Authority**: 65537 (Phuc Forecast)
**Status**: Consolidation complete, all links verified
**Last Verification**: 2026-02-15

**See also**: [RECIPES_CONSOLIDATION_REPORT.md](../RECIPES_CONSOLIDATION_REPORT.md)
