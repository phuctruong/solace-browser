=== SKILL: STYLEGUIDE-FIRST ===

HARD RULES for visual/code review:
1. All colors via CSS custom properties (--sa-* design tokens), never hardcoded hex
2. Mobile-first: 320px base styles, scale up with min-width media queries
3. Accessibility before visual: ARIA roles, keyboard nav, focus-visible, prefers-reduced-motion
4. No inline styles: all styles in CSS classes matching existing token system
5. Dark/light/midnight theme support via CSS custom properties
6. Zero new colors: only existing palette (--sa-blue, --sa-purple, --sa-orange, --sa-gold)
7. Typography hierarchy: h1 > h2 > h3 > body using --font-* scale tokens
8. Spacing: use --spacing-* tokens (xs through 5xl), never raw px values
9. Border radius: use --radius-* tokens for consistency
10. Breakpoints: 375px (mobile), 768px (tablet), 1024px (desktop), 1280px (wide)

When reviewing: flag ANY hardcoded color, px spacing outside tokens, missing ARIA, or inline style.
