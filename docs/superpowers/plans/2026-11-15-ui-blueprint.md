# UI Blueprint Reskin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the repomap web view in a navy blueprint style with an embedded monospace font and a light/dark toggle.

**Architecture:** Fonts live as base64 `@font-face` CSS in `repomap/web/vendor/fonts.css`, inlined by `render.py` through a new `/*__FONTS__*/` slot, the same way ELK is. All styling is CSS tokens in `template.html`; the toggle is a few lines in `app.js` setting `data-theme` on `<html>`.

**Tech Stack:** Python stdlib (render), vanilla JS/CSS/SVG, JetBrains Mono woff2 (OFL) from `@fontsource/jetbrains-mono`.

**Spec:** `docs/superpowers/specs/2026-11-15-ui-blueprint-design.md`

## Global Constraints
- Output HTML stays a single self-contained file: no `<link>`, no `http` URLs (existing `test_self_contained`).
- No new Python dependencies.
- Status colors `--fresh` / `--stale` keep their meaning.
- UI text stays English (`test_ui_text_is_english`).
- Layout (bar / tree / map / panel, grips) unchanged.

## Review Focus
- `localStorage` throws (private mode / file://) → toggle still works for the session, page renders.
- No saved choice → theme follows `prefers-color-scheme`, and flips live when OS theme changes.
- Saved `dark` on a light OS (and vice versa) → every token flips, including SVG fills and the grid.
- Large repo map → grid is one `<pattern>` fill, not per-cell elements; pan/zoom no slower.
- Fonts file accidentally containing `</style` → never; base64 only (asserted in Task 1 test).

---

### Task 1: Embed font

**Files:**
- Create: `repomap/web/vendor/fonts.css`, `repomap/web/vendor/LICENSE-jetbrains-mono.txt`
- Modify: `repomap/render.py:15-20`, `repomap/web/template.html` (first line inside `<style>`)
- Test: `tests/test_render.py`

**Interfaces:**
- Produces: CSS font family `"JBMono"` (weights 400, 700) available to all later CSS.

- [ ] **Step 1: Write failing test** in `TestRender`:
```python
def test_font_embedded(self):
    html = render_html(build_model(*load_graph(FIXTURE)))
    self.assertIn("@font-face", html)
    self.assertIn("font/woff2;base64,", html)
    self.assertEqual(html.count("</style"), 1)
```
- [ ] **Step 2:** `python -m unittest tests.test_render -v` → FAIL on `@font-face`.
- [ ] **Step 3:** Download `@fontsource/jetbrains-mono@5.1.1` tarball (npm registry) into a fresh scratch dir; take `files/jetbrains-mono-latin-400-normal.woff2` and `-700-normal.woff2` and its `LICENSE`. Write `fonts.css` with two `@font-face { font-family: "JBMono"; font-weight: N; font-display: block; src: url(data:font/woff2;base64,...) format("woff2"); }`. Add `"/*__FONTS__*/": (WEB / "vendor/fonts.css").read_text(encoding="utf-8")` to `parts`; put `/*__FONTS__*/` as the first line of `<style>`.
- [ ] **Step 4:** Tests pass (whole suite: `python -m unittest discover tests -v`).
- [ ] **Step 5:** Commit `feat(web): embed JetBrains Mono font`.

### Task 2: Blueprint reskin (CSS + grid)

**Files:**
- Modify: `repomap/web/template.html` (`<style>`, `<svg id="map">` defs), `repomap/web/app.js` (only if a class/attr is needed for labels)

**Interfaces:**
- Consumes: `"JBMono"` from Task 1.
- Produces: token set on `:root` used by Task 3: `--bg --fg --muted --line --border --panel --leaf --d0..--d3 --inner --stale --fresh --accent --grid`.

- [ ] **Step 1: Tokens.** Light: `--bg #f5f7fc`, `--panel #ffffff`, `--fg #14245c`, `--muted #5b6b94`, `--accent #1e3fae`, `--line #6f8ad6`, `--border #c3cde6`, `--grid #e3e9f6`, `--leaf #ffffff`, `--d0..--d3` very light blue tints (`#f0f4ff #eaf0fd #e4ebfb #dee6f9`). Dark: `--bg #0d1729`, `--panel #101d33`, `--fg #dbe4ff`, `--muted #8293bd`, `--accent #2f5bea`, `--line #5b7be0`, `--border #263a63`, `--grid #16243f`, `--leaf #13213b`, `--d0..--d3` navy steps (`#12203a #152542 #182a4a #1b2f52`). Keep `--stale/--fresh/--inner` values. Dark block moves to selectors `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {...} }` and `:root[data-theme="dark"] {...}`; `:root[data-theme="light"]` sets `color-scheme: light`, dark sets `color-scheme: dark`.
- [ ] **Step 2: Type & chrome.** `body` font `13px "JBMono", ui-monospace, monospace`; drop system-ui everywhere (incl. `.note`, `.count`). `#bar` buttons/inputs: 1px `--border`, `border-radius: 0`, uppercase, `letter-spacing: .08em`, bold; `button[aria-pressed="true"]`/`[aria-expanded="true"]` = solid `--accent`, white text. All `border-radius` → 0. `#panel .head` uppercase, 700, `letter-spacing: .1em`, 1px bottom rule. Panel key–value lists: keys uppercase bold, rows separated by 1px `--border`.
- [ ] **Step 3: Map.** In `<defs>` add `<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" class="gridline"/></pattern>`; insert `<rect id="grid-bg" width="100%" height="100%" fill="url(#grid)"/>` before `#viewport` (static, does not pan — cheapest). `.gridline { stroke: var(--grid); }`. `.arrow .line { stroke-dasharray: 5 4; }`; `.box text` font-weight 700.
- [ ] **Step 4: Verify.** `python -m unittest discover tests -v` passes; `node --test tests/aggregate.test.mjs` passes; `python -m repomap tests/fixtures/mini_graph.json -o out/demo.html` (check CLI flags with `--help`), open in a browser in light and dark OS mode, compare to spec screenshots.
- [ ] **Step 5:** Commit `feat(web): blueprint navy reskin`.

### Task 3: Light/dark toggle

**Files:**
- Modify: `repomap/web/template.html` (`#bar`), `repomap/web/app.js`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `data-theme` selectors from Task 2.

- [ ] **Step 1: Failing test:**
```python
def test_theme_toggle_present(self):
    html = render_html(build_model(*load_graph(FIXTURE)))
    self.assertIn('id="theme-toggle"', html)
    self.assertIn("repomap-theme", html)
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Add `<button id="theme-toggle" type="button" aria-label="Toggle dark mode">Theme</button>` before `#stats`. In `app.js`: on load read `localStorage["repomap-theme"]` (try/catch) and set `document.documentElement.dataset.theme` if `light|dark`; on click compute current (dataset or `matchMedia('(prefers-color-scheme: dark)')`), flip, set dataset, save (try/catch), set `aria-pressed` to dark-ness. Label text: `Dark` / `Light` (the mode it switches to).
- [ ] **Step 4:** Unit tests pass; in browser: toggle flips all colors, reload keeps choice, works with storage blocked.
- [ ] **Step 5:** Commit `feat(web): light/dark toggle`.
