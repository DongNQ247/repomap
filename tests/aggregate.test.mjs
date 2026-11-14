import test from "node:test";
import assert from "node:assert/strict";
import { buildTree, visibleView } from "../repomap/web/aggregate.js";

// Same content as tests/fixtures/mini_graph.json after build_model.
const E = (src, tgt, count, rel) => ({ src, tgt, count, by_rel: { [rel]: count }, samples: [] });
const model = {
  files: [
    { path: "README.md", kind: "doc" }, { path: "lib/c.py", kind: "code" },
    { path: "pkg/a.py", kind: "code" }, { path: "pkg/lone.py", kind: "code" },
    { path: "pkg/sub/b.py", kind: "code" }, { path: "tests/test_a.py", kind: "test" },
  ],
  external: [{ id: "ext:Path", label: "Path" }],
  edges: [
    E("pkg/a.py", "pkg/sub/b.py", 2, "calls"), E("pkg/a.py", "lib/c.py", 1, "imports_from"),
    E("lib/c.py", "pkg/sub/b.py", 1, "calls"), E("tests/test_a.py", "pkg/a.py", 1, "calls"),
    E("pkg/a.py", "ext:Path", 1, "calls"),
  ],
};
const tree = buildTree(model);
const S = (o = {}) => ({ showTests: false, showDocs: false, showExternal: false, ...o, expanded: new Set(o.expanded || []) });
const arrowSet = (v) => v.arrows.map((a) => `${a.src}->${a.tgt}:${a.count}`).sort();

test("initial view: top level only, arrows lifted", () => {
  const v = visibleView(tree, model, S());
  assert.deepEqual(v.boxes.map((b) => b.id).sort(), ["lib/", "pkg/", "tests/"]);
  assert.deepEqual(arrowSet(v), ["lib/->pkg/:1", "pkg/->lib/:1"]);
  assert.equal(v.total, 5);
  assert.equal(v.boxes.find((b) => b.id === "pkg/").fileCount, 3);
  assert.ok(v.boxes.every((b) => b.collapsed && b.parent === ""));
});
test("expand pkg/: inner arrows appear, sub/ still collapsed", () => {
  const v = visibleView(tree, model, S({ expanded: ["pkg/"] }));
  assert.ok(arrowSet(v).includes("pkg/a.py->pkg/sub/:2"));
  assert.ok(arrowSet(v).includes("lib/->pkg/sub/:1"));
  assert.ok(v.boxes.find((b) => b.id === "pkg/sub/").collapsed);
});
test("merged arrows sum count and by_rel", () => {
  const m2 = { ...model, edges: [...model.edges, E("pkg/lone.py", "lib/c.py", 3, "calls")] };
  const a = visibleView(buildTree(m2), m2, S()).arrows.find((x) => x.src === "pkg/" && x.tgt === "lib/");
  assert.equal(a.count, 4);
  assert.deepEqual(a.by_rel, { imports_from: 1, calls: 3 });
});
test("collapse parent after deep expand -> no dangling arrows", () => {
  const v = visibleView(tree, model, S({ expanded: ["pkg/sub/"] }));
  const ids = new Set(v.boxes.map((b) => b.id));
  assert.ok(!ids.has("pkg/sub/"));
  v.arrows.forEach((a) => assert.ok(ids.has(a.src) && ids.has(a.tgt)));
});
test("toggles", () => {
  assert.ok(!arrowSet(visibleView(tree, model, S())).some((s) => s.startsWith("tests/")));
  assert.ok(arrowSet(visibleView(tree, model, S({ showTests: true }))).includes("tests/->pkg/:1"));
  assert.ok(visibleView(tree, model, S({ showDocs: true })).boxes.some((b) => b.id === "README.md"));
  const ve = visibleView(tree, model, S({ showExternal: true, expanded: ["ext:"] }));
  assert.ok(ve.boxes.some((b) => b.id === "ext:"));
  assert.ok(ve.boxes.some((b) => b.id === "ext:Path" && b.name === "Path"));
  assert.ok(arrowSet(ve).includes("pkg/->ext:Path:1"));
});
