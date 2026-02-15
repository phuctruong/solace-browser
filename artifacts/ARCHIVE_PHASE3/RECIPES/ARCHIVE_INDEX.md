# Archived Recipes Index

**Archive Date**: 2026-02-15
**Phase**: Phase 3.5 Knowledge Consolidation
**Authority**: 65537 (Phuc Forecast)

---

## Why These Recipes Were Archived

During Phase 3.5 consolidation, we identified recipe variants and test files. Rather than deleting them, they were archived for:
- Historical reference
- Variant tracking (which optimizations were tried)
- Recovery if needed
- Learning purposes

---

## Archived Variant Recipes

### LinkedIn Profile Update Variants

#### linkedin-profile-optimization-10-10.recipe.json
- **Type**: Variant of `linkedin-profile-update.recipe.json`
- **Difference**: More aggressive headline and about optimizations
- **Reason Archived**: Consolidated into canonical with variant metadata
- **Recovery**: Restore if optimization level settings needed

---

#### linkedin-harsh-qa-fixes.recipe.json
- **Type**: Variant of `linkedin-profile-update.recipe.json`
- **Difference**: QA-focused refinements
- **Reason Archived**: Consolidated into canonical with variant metadata
- **Recovery**: Restore to see QA-specific fixes applied

---

#### linkedin-update-5-projects-hr-approved.recipe.json
- **Type**: Variant of `linkedin-profile-update.recipe.json`
- **Difference**: Includes project additions and HR-approved updates
- **Reason Archived**: Consolidated into canonical with variant metadata
- **Recovery**: Restore for bulk project workflows

---

### LinkedIn Project Deletion Variants

#### delete-linkedin-projects-openclaw.recipe.json
- **Type**: Different workflow (project deletion, not update)
- **Difference**: OpenClaw-based deletion approach
- **Reason Archived**: Not a duplicate, but kept in archive for reference
- **Note**: Use `add-linkedin-project-optimized.recipe.json` for project management

---

#### delete-old-linkedin-projects.recipe.json
- **Type**: Earlier version of project deletion
- **Difference**: Older deletion workflow
- **Reason Archived**: Superseded by better workflow
- **Status**: Not maintained, use archive reference only

---

### Gmail Login Variants

#### gmail-oauth2-login.recipe.json
- **Type**: Variant of `gmail-oauth-login.recipe.json`
- **Difference**: OAuth 2.0 specific variant
- **Reason Archived**: Consolidated into canonical with variant metadata
- **Recovery**: Restore if explicit OAuth 2.0 flow needed

---

#### gmail-login-headed.recipe.json
- **Type**: Variant of `gmail-oauth-login.recipe.json`
- **Difference**: Headed browser variant (vs headless)
- **Reason Archived**: Consolidated into canonical with variant metadata
- **Recovery**: Restore for headed browser testing

---

## Archived Test Recipes

### test-ep-quick.recipe.json
- **Type**: Quick test recipe
- **Purpose**: Quick validation during development
- **Reason Archived**: Temporary test file, not part of core library
- **Status**: Safe to delete after 1 month

---

### demo-1771110591.recipe.json
- **Type**: Demo execution trace
- **Purpose**: Demonstration of workflow
- **Timestamp**: 1771110591
- **Reason Archived**: Demo/temporary file
- **Status**: Safe to delete after 1 month

---

### quick-validation-test.recipe.json
- **Type**: Validation test recipe
- **Purpose**: Testing validation workflows
- **Reason Archived**: Temporary test file
- **Status**: Safe to delete after 1 month

---

### quick-validation-workflow.recipe.json
- **Type**: Validation workflow recipe
- **Purpose**: Testing validation processes
- **Reason Archived**: Temporary test file
- **Status**: Safe to delete after 1 month

---

## How to Restore

To restore any archived recipe:

```bash
# Restore to recipes/
cp artifacts/ARCHIVE_PHASE3/RECIPES/<recipe-name>.recipe.json recipes/

# Or create a symlink
ln -s ../artifacts/ARCHIVE_PHASE3/RECIPES/<recipe-name>.recipe.json recipes/
```

---

## Consolidation Metadata

For each canonical recipe, variants are tracked in a `variants` metadata section:

```json
{
  "recipe_id": "linkedin-profile-update",
  "variants": [
    {
      "variant_id": "10-10-optimization",
      "file": "linkedin-profile-optimization-10-10.recipe.json",
      "differences": ["Added headline optimizations", "Improved headline formula"],
      "archived": true,
      "archive_location": "artifacts/ARCHIVE_PHASE3/RECIPES/"
    }
  ]
}
```

---

## Statistics

**Total Archived**: 11 files
- Recipe Variants: 7 files
- Test/Demo: 4 files

**Total Preserved**: 100% (nothing deleted)
**Archive Space**: ~150 KB
**Recovery Time**: <1 minute per file

---

## Cleanup Schedule

- **Immediate**: Keep all files (reference + learning)
- **1 Month**: Safe to delete test files (4 recipes)
- **3 Months**: All variants should be folded into canonical
- **6 Months**: Consider deleting if variants not accessed

---

**Authority**: 65537
**Status**: Archive complete, all files preserved
**Last Updated**: 2026-02-15

---

**See also**: [RECIPES_INDEX.md](../../recipes/RECIPES_INDEX.md)
