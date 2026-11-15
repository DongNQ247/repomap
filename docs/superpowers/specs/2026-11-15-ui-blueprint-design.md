# UI reskin: blueprint style

## Intent
Make the repomap web view look like protocol-explorer-alpha.vercel.app: technical/blueprint feel, monochrome navy, monospace caps headings. Style only — how the map works stays the same.

## Goals
- Navy palette for light (near-white bluish bg) and dark (deep navy bg), single accent ~`#1e3fae`; status colors (fresh/stale) kept.
- Embedded monospace font, works offline.
- Uppercase letter-spaced bold headings; 1px borders, square corners, no shadows; panel title bars with a divider rule.
- Square outlined buttons, active = solid accent + white text.
- Map: faint grid background, dashed light-blue edges, bold node labels.
- Details panel: key–value rows, uppercase bold keys, thin row separators.
- Manual light/dark toggle button in the top bar.

## Non-goals
Isometric icons, header/logo rework, filter tabs with counts, layout changes.

## Anti-goals
Breaking offline single-file output; slower render on big repos.

## Approaches
- **A. CSS reskin, layout unchanged** — chosen (+ theme toggle from B).
- B. A plus header rework, filter tabs, theme toggle — more JS; deferred except the toggle.

## Decisions
- Font embedded as base64 woff2 in `repomap/web/vendor/`, Latin subset, 2 weights, inlined the same way `elk.bundled.js` is (with its OFL license file).
- Toggle: sets `data-theme="light|dark"` on `<html>`; default follows `prefers-color-scheme`; choice saved in `localStorage` (try/catch, works without it).

## Builder's call (mine, correct me)
- Font: JetBrains Mono (OFL), regular + bold, from `@fontsource/jetbrains-mono`.
- Exact hex values tuned by eye against the screenshots.
- Grid drawn as an SVG `<pattern>` behind the map.
