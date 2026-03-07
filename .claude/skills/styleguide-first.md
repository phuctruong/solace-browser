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

## FORBIDDEN
- Hardcoded hex/rgb colors in CSS or HTML
- Inline `style=""` attributes on any element
- New CSS color variables without explicit approval
- Skipping component gallery verification
- Desktop-first media queries (`max-width`)

## VERIFICATION CHECKLIST
Before marking any UI task as done:
- [ ] All colors reference `--sa-*` tokens
- [ ] Component renders at 320px, 768px, 1024px
- [ ] ARIA labels present on all interactive elements
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] `prefers-reduced-motion` respected (no forced animations)
- [ ] Component gallery updated if new component added
- [ ] Dark mode toggle does not break layout
