# DNA: `styleguide_first(component) = tokens(inventory) × a11y(audit) × mobile_first(320px); no_code_before_tokens`
# SKILL: styleguide-first v1.0
# Auth: 65537 | Created: 2026-02-28

## PURPOSE
Enforce design token alignment before any component code is written.
This skill sits 4th in the build chain: diagram-first -> webservice-first -> unit-test-first -> **styleguide-first** -> cli/browser dev.

## CORE RULES

1. **Token inventory first** — list ALL CSS custom properties (`--sa-*`) before writing any HTML
2. **Component gallery audit** — check `component-gallery.html`, verify new component matches existing patterns before shipping
3. **Mobile-first** — write 320px styles first, then scale up with `min-width` media queries
4. **Dark/light mode** — use CSS custom properties for both themes; never hardcode colors
5. **No inline styles** — all styles in `.css` classes matching existing token system
6. **Accessibility before visual** — ARIA roles, keyboard nav, `focus-visible`, `prefers-reduced-motion` FIRST
7. **Match existing patterns** — check `semantic-rungs.css` before creating new classes
8. **Zero new colors** — only use existing `--sa-blue`, `--sa-purple`, `--sa-orange`, `--sa-gold` palette

## Forbidden States

| State | Description |
|-------|-------------|
| HARDCODED_COLOR | Using hex/rgb colors in CSS or HTML instead of `--sa-*` tokens |
| INLINE_STYLE | Any `style=""` attribute on any element — use CSS classes |
| UNAPPROVED_COLOR_VAR | Creating new CSS color variables without explicit approval |
| SKIPPED_GALLERY_CHECK | Shipping a component without verifying it in component-gallery.html |
| DESKTOP_FIRST_QUERY | Using `max-width` media queries instead of mobile-first `min-width` |

## VERIFICATION CHECKLIST
Before marking any UI task as done:
- [ ] All colors reference `--sa-*` tokens
- [ ] Component renders at 320px, 768px, 1024px
- [ ] ARIA labels present on all interactive elements
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] `prefers-reduced-motion` respected (no forced animations)
- [ ] Component gallery updated if new component added
- [ ] Dark mode toggle does not break layout

---

## Interaction Effects

| Skill | Interaction | Resolution |
|-------|------------|------------|
| **prime-coder** | Coder writes component code; styleguide-first gates whether tokens are aligned first | styleguide-first runs before prime-coder's patch phase; token audit failure blocks code generation |
| **prime-safety** | Safety may flag inline styles or external resource loads as violations | prime-safety wins; styleguide-first ensures all styles use CSS custom properties to avoid CSP conflicts |
| **live-llm-browser-discovery** | Discovery may encounter dynamic UI that needs style classification | styleguide-first provides the token vocabulary that discovery uses to describe visual elements |
| **browser-snapshot** | Snapshots capture visual state; style consistency affects snapshot reliability | styleguide-first ensures deterministic visual output so snapshots are comparable across runs |
| **webservice-first** | API responses may include UI component data (themes, layouts) | styleguide-first validates that any server-rendered styles reference the canonical token set |

---

## Cross-References

| Reference | Type | Relationship |
|-----------|------|-------------|
| Paper 35 (Canonical Web Symmetry) | Architecture | Defines the symmetry pipeline that styleguide-first enforces at the component level |
| Paper 16 (SW5.0 Pipeline) | Pipeline | styleguide-first sits at stage [4] STYLEGUIDES in the build chain |
| `web/styleguides/theme-system.md` | Styleguide | Theme system specification that this skill enforces |
| `prime-coder.md` | Skill | Coder depends on styleguide-first completing token audit before patch phase |
| `prime-safety.md` | Skill | Safety gates any style that could introduce CSP violations or external network loads |
