# Manual Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `repomap link` lets the user add runtime files, concepts and typed arrows that graphify missed; the map draws them dashed.

**Architecture:** New `repomap/links.py` owns `links.json` I/O, validation and merging into the model (mirrors `notes.py`). `__main__.py` gets `link_main` and calls the merge before `annotate`/`note_view`. `aggregate.js` adds a Concepts frame and a `manual` flag on merged arrows; `app.js`/`template.html` draw dashed styles.

**Tech Stack:** Python 3.10 stdlib, unittest; vanilla JS ES modules, `node --test`.

**Spec:** `docs/superpowers/specs/2026-11-15-manual-links-design.md`

## Global Constraints

- Standard library only; no new dependencies.
- Relations exactly: `calls`, `imports`, `creates`, `reads`. Anything else → argparse error, exit 2.
- Storage: `repomap-out/links.json`, `{"version": 1, "nodes": {name: {"kind": "file"|"concept"}}, "edges": [{"src","rel","tgt"}]}`, atomic write, `sort_keys`, edges sorted by `(src, rel, tgt)`, mode 0644.
- Never modify `graph.json`. Never scan source code.
- Errors: user/data errors exit 1 via `fail()`; bad args exit 2.
- Concept ids in the model: `concept:<name>`; Concepts frame id `concept:`, always shown.

## Review Focus

1. Arrow to a component that was later renamed → not drawn, listed after `repomap .` with a `repomap link delete ...` hint (Task 3 test `test_render_lists_missing_links`).
2. `link delete` of a node that still has arrows → exit 1, arrows listed, file unchanged (Task 2 `test_delete_node_with_edges_refused`).
3. Concept name clashing with a map component (`repomap` vs folder `repomap/`) or containing `/`/`::` → exit 1 at add (Task 2 `test_concept_name_rules`).
4. Corrupt `links.json` → exit 1 on both `repomap .` and `repomap link`, file not overwritten (Task 2 `test_corrupt_links_json`, Task 3 `test_render_corrupt_links`).
5. Note on a concept/runtime file → shown, never stale (Task 3 `test_note_on_concept`).

---

### Task 1: links.py — storage, validation, merge

**Files:**
- Create: `repomap/links.py`
- Test: `tests/test_links.py`

**Interfaces:**
- Consumes: `components(model)` from `notes.py` (keys → `{"box","kind","file","start","end"}`), `resolve(name, comps)`.
- Produces:
  - `RELS = ("calls", "imports", "creates", "reads")`
  - `load_links(path) -> dict` — missing file → `{"nodes": {}, "edges": []}`; bad JSON/shape → `ValueError`.
  - `save_links(path, links) -> None`
  - `link_components(links, comps) -> dict` — returns new comps dict = comps + manual nodes not already in comps. Runtime file → `{"box": path, "kind": "file", "file": None, "start": 0, "end": None, "manual": True}` plus dir entries for its missing parent folders (`box` = `"a/b/"`, kind `dir`); concept → `{"box": "concept:"+name, "kind": "concept", "file": None, ...}`.
  - `merge_links(model, links, comps) -> dict` — mutates model; returns `{"missing": [str], "found": [str]}`. Adds manual files to `model["files"]` as `{"path", "kind": classify(path), "manual": True}` (kept sorted), concepts to `model["concepts"] = [{"id","label"}]` (always set, maybe empty), edges to `model["edges"]` as `{"src": box, "tgt": box, "count": 1, "manual_count": 1, "by_rel": {rel: 1}, "samples": [{"from": src, "to": tgt, "rel": rel, "loc": "manual"}]}`. Existing graphify edges get no `manual_count` (treat as 0). An edge with an end not in comps → skipped, its `"src rel tgt"` string in `missing`. A manual file node that graphify already has → in `found`, not duplicated.
- `fingerprint()` in notes.py must return `None` for comps with `file is None` (concept/runtime) — add `if comp.get("manual") or comp["kind"] == "concept": return None` there; `note_view` then must not mark stale when the stored hash is also `None` (already true: `None != None` is False).

- [ ] **Step 1: Write failing tests** in `tests/test_links.py` (unittest, tempdir):
  - `test_load_missing_returns_empty`: `load_links(tmp/"x.json") == {"nodes": {}, "edges": []}`.
  - `test_save_load_roundtrip`: save then load equal; file ends with `"\n"`; mode `0o644`.
  - `test_load_bad_shape`: `'{"version":1}'` and `'[1]'` and `'{'` each raise `ValueError`.
  - `test_merge_runtime_file_and_concept`: tiny model `{"files":[{"path":"a/x.py","kind":"code"}],"symbols":[],"external":[],"edges":[]}`; links nodes `{"out/map.html":{"kind":"file"},"SSD":{"kind":"concept"}}`, edges `[{"src":"a/x.py","rel":"creates","tgt":"out/map.html"},{"src":"a/x.py","rel":"reads","tgt":"SSD"}]`. After merge: `"out/map.html"` in file paths with `manual: True`; `model["concepts"] == [{"id":"concept:SSD","label":"SSD"}]`; edges contain `src "a/x.py" tgt "out/map.html"` and `tgt "concept:SSD"`, each `manual_count == 1`; result `{"missing": [], "found": []}`.
  - `test_merge_missing_end`: edge to `"a/gone.py"` → not in edges, `missing == ["a/gone.py calls ..."]` form `f"{src} {rel} {tgt}"`.
  - `test_merge_found_by_graphify`: manual file node `"a/x.py"` → `found == ["a/x.py"]`, files not duplicated.
  - `test_symbol_and_folder_ends_kept`: edge src `"a/x.py::f"` (symbol in comps) → edge src is that symbol's box (`"sym:..."`); src `"a"` → `"a/"`.
- [ ] **Step 2:** `python -m unittest tests.test_links -v` → FAIL (ImportError).
- [ ] **Step 3:** Implement `repomap/links.py` per Interfaces; copy the atomic-write pattern of `save_notes` (prefix `.links-`). Patch `fingerprint` as above.
- [ ] **Step 4:** `python -m unittest discover tests -v` → all PASS.
- [ ] **Step 5:** Commit `feat(links): links.json storage and model merge`.

### Task 2: `repomap link` CLI

**Files:**
- Modify: `repomap/__main__.py` (add `link_main`, dispatch in `main` next to `note`)
- Test: `tests/test_cli.py` (new class `LinkCliTest`, reuse `run()` and fixture `NOTES_PROJ` copied into tmp)

**Interfaces:**
- Consumes: Task 1 functions; `find_project`, `read_model`, `components`, `resolve`, `fail`, `style`, `rel`.
- Produces: subcommands
  - `link node <name> [--concept]`
  - `link add <src> <rel> <tgt>` (`rel` uses `choices=RELS`)
  - `link delete <args...>` — 1 arg = node, 3 args = edge, else argparse-style error exit 2.
- Output on success: `"{ok} added node X"`, `"{ok} added link S rel T"`, `"{ok} deleted ..."`; duplicate → exit 0, `"already exists: ..."`.

Rules (from spec):
- `node` without `--concept`: name normalised like `resolve` (strip, rstrip `/`); refused if contains `::` or already a comp/manual node.
- `--concept`: refused (exit 1) if contains `/` or `::`, or equals any comp key or manual node name.
- `add`: each end resolved by `resolve(name, link_components(links, comps))`; KeyError → exit 1 with its message. Store the resolved key (not the box).
- `delete` edge works even if ends no longer resolve (match raw stored strings, also try resolved form). `delete` node with edges referencing it → exit 1: `"X still has links: <list>; delete them first"`.

- [ ] **Step 1: Write failing tests:** `test_link_node_and_add` (writes links.json with expected content), `test_link_bad_rel_exit2`, `test_link_unknown_end_exit1`, `test_link_duplicate_noop`, `test_delete_edge`, `test_delete_edge_after_rename` (edit links.json to point at gone file, delete still exit 0), `test_delete_node_with_edges_refused`, `test_concept_name_rules` (`a/b`, `x::y`, and an existing folder name each exit 1), `test_corrupt_links_json` (exit 1, file bytes unchanged), `test_link_from_subfolder`.
- [ ] **Step 2:** `python -m unittest tests.test_cli -v` → new tests FAIL.
- [ ] **Step 3:** Implement `link_main(argv)`.
- [ ] **Step 4:** full suite PASS.
- [ ] **Step 5:** Commit `feat(cli): repomap link node/add/delete`.

### Task 3: merge into `repomap .` and report

**Files:**
- Modify: `repomap/__main__.py` `main()` (after `components(model)`: load links, `comps = link_components(...)`, `merge_links(...)`, then `annotate`/`note_view` with the extended comps); `note_main` also uses `link_components` so notes can target concepts/runtime files.
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: model keys `concepts`, edges with `manual_count`, files with `manual` — consumed by Task 4.
- Summary lines (only when non-empty): `"  {n} manual links"`, `"  {n} links point to missing components: a, b — remove with: repomap link delete <src> <rel> <tgt>"`, `"  {n} manual nodes now found by graphify: x — remove with: repomap link delete x"`.

- [ ] **Step 1: Write failing tests:** `test_render_with_links` (map.html contains `"concept:SSD"` and `"manual_count"`), `test_render_lists_missing_links`, `test_render_corrupt_links` (exit 1), `test_note_on_concept` (`note add SSD "disk"` exit 0; map.html note has `"stale": false`).
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** full suite PASS.
- [ ] **Step 5:** Commit `feat: draw manual links on the map`.

### Task 4: web — Concepts frame and dashed styles

**Files:**
- Modify: `repomap/web/aggregate.js`, `repomap/web/app.js`, `repomap/web/template.html` (CSS)
- Test: `tests/aggregate.test.mjs`

**Interfaces:**
- Consumes: model from Task 3.
- Produces:
  - `buildTree`: after External, add `{id: "concept:", name: "Concepts", type: "conroot"}` with children `{id, name: label, type: "concept"}` from `model.concepts || []` — only when non-empty. File nodes carry `manual: true` when `f.manual`.
  - `isLeaf`/`shown`/`leafCount` treat `concept` like `ext`; `allowedLeaf` returns `true` for `concept` (always shown).
  - Merged arrow gets `manual: true` iff sum of `e.manual_count || 0` equals its `count`.
  - app.js: box class `manual` for manual files, `conroot`/`concept` types; arrow group class `manual` when `a.manual`; samples with `loc === "manual"` render as `"… (manual)"` instead of the loc.
  - CSS: `.box.manual rect, .box.conroot rect, .box.concept rect, .arrow.manual .line { stroke-dasharray: 4 3; }`; add legend/colour entries for `creates`, `reads` wherever relation colours/labels are listed.

- [ ] **Step 1: Write failing tests:** `concepts frame always visible even with showExternal false`; `no concepts frame when model.concepts empty`; `arrow manual only when all links manual` (one model with a manual-only edge and a mixed pair merged into the same lifted arrow → `manual` true / false).
- [ ] **Step 2:** `node --test tests/` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** `node --test tests/` and `python -m unittest discover tests` PASS; run `repomap .` in this repo after `repomap link add repomap/render.py::render_html creates repomap-out/map.html` and open map.html to eyeball dashed box/arrow (then `link delete` both).
- [ ] **Step 5:** Commit `feat(web): dashed manual links and Concepts frame`.

### Task 5: skill + README

**Files:**
- Modify: `repomap/skill/SKILL.md`, `README.md`

- [ ] **Step 1:** SKILL.md: add link only when the user asks ("thêm liên kết", "add link", "link this"); naming = note naming; 4 relations; `--concept` for things outside the code (SSD, external service); runtime files use their path; delete arrows before their node. Also add trigger words to its `description`.
- [ ] **Step 2:** README: "Manual links" section with the CLI block from the spec, storage file, dashed rendering, suggest committing `links.json`.
- [ ] **Step 3:** full suite PASS; commit `docs: manual links in README and skill`.
