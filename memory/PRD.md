# AI Operator Hub — Homepage Redesign

## Problem statement
Redesign the Flask AI Operator Hub homepage to match the AI Tool Finder branding: clean modern SaaS, white background, deep navy text, teal/green accent, rounded buttons, subtle cards and borders, professional analytics/productivity feel. Only edit templates/home.html, templates/_nav.html (if needed), and static/style.css. Do not change Flask routes, Disqus, Analytics, article URLs, or SEO title/meta.

## Stack
- Flask 3 (Python), gunicorn
- Jinja templates + static/style.css
- Disqus and Google Analytics includes (untouched)

## What's been implemented (Jan 2026)
- Updated `static/style.css` design tokens:
  - White background (`--bg: #ffffff`), soft strip `--bg-soft`
  - Deep navy text (`--navy: #0b1c34`), muted `#5b6b80`
  - Teal accent `#0d9488` with darker `#0f766e` and soft `#ecfdf5`
  - Radius scale incl. pill radius, soft shadow tokens
- Redesigned hero in `home.html`:
  - Lighter overlay (0.78 → 0.55 → 0.28 teal-tinted gradient) + soft white fade at bottom
  - Smaller cleaner H1 (`clamp(2.2rem, 4.6vw, 3.6rem)`, weight 700)
  - Stronger value prop copy focused on small business AI workflows
  - Pill-shaped primary CTA (to Tool Finder, UTM preserved) + ghost secondary CTA (Articles)
- New trust/value strip with 4 metrics (Playbooks, 3-tool stack, Free, Weekly)
- New "How AI Operator Hub helps" section: 3 feature cards with soft icon chips
- Article grid: teal tag pills, hover lift, cleaner meta line with bullet separator, "View all articles →" link
- Softer mint gradient site CTA panel
- Preserved: nav include (unchanged), Disqus, Google Analytics, all Flask routes, article URLs, SEO title/meta

## Files touched
- /app/templates/home.html (rewritten)
- /app/static/style.css (updated tokens, hero, buttons, cards, added trust strip + feature grid + section-heading-row + text-link)
- /app/templates/_nav.html — NOT changed (already fit the new brand once CSS was updated)

## Backlog / future
- Add screenshots or logos to trust strip
- Add category filter chips on articles page
- Consider dark-mode variant
