import test from "node:test";
import assert from "node:assert/strict";
import { buildTree, visibleView, absoluteLayout, revealPath, treeRows, unhide } from "../repomap/web/aggregate.js";

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
const S = (o = {}) => ({ showTests: false, showDocs: false, showExternal: false, ...o, expanded: new Set(o.expanded || []), hidden: new Set(o.hidden || []) });
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

test("absoluteLayout offsets edge points by their container", () => {
  const g = { id: "__root__", children: [{ id: "p/", x: 100, y: 50, width: 200, height: 100, children: [
    { id: "p/a", x: 10, y: 30, width: 40, height: 30 }, { id: "p/b", x: 100, y: 30, width: 40, height: 30 }] }],
    edges: [
      { id: "e0", container: "p/", sections: [{ startPoint: { x: 50, y: 45 }, endPoint: { x: 100, y: 45 } }] },
      { id: "e1", sections: [{ startPoint: { x: 1, y: 2 }, bendPoints: [{ x: 3, y: 4 }], endPoint: { x: 5, y: 6 } }] }] };
  const { pos, edges } = absoluteLayout(g);
  assert.deepEqual(pos.get("p/b"), { x: 200, y: 80, width: 40, height: 30 });
  assert.deepEqual(edges[0].sections, [[{ x: 150, y: 95 }, { x: 200, y: 95 }]]);
  assert.deepEqual(edges[1].sections, [[{ x: 1, y: 2 }, { x: 3, y: 4 }, { x: 5, y: 6 }]]);
});

test("hide file: its arrows vanish, siblings' remain", () => {  // Review Focus 1
  const v = visibleView(tree, model, S({ expanded: ["pkg/"], hidden: ["pkg/sub/b.py"] }));
  assert.ok(!v.boxes.some(b => b.id === "pkg/sub/"));           // sub/ chỉ có b.py → biến mất (Focus 2)
  assert.ok(!arrowSet(v).some(s => s.includes("pkg/sub/")));
  assert.ok(arrowSet(v).includes("pkg/a.py->lib/:1"));
});
test("hide inside collapsed folder subtracts only that file", () => {
  const v = visibleView(tree, model, S({ hidden: ["pkg/a.py"] }));
  assert.deepEqual(arrowSet(v), ["lib/->pkg/:1"]);              // c->b còn, a->c mất
});
test("hide folder hides subtree and lowers total", () => {
  const a = visibleView(tree, model, S()), b = visibleView(tree, model, S({ hidden: ["lib/"] }));
  assert.ok(!b.boxes.some(x => x.id === "lib/"));
  assert.ok(b.total < a.total);
});
test("hidden survives filter toggle", () => {  // Review Focus 3
  const v = visibleView(tree, model, S({ showDocs: true, hidden: ["README.md"] }));
  assert.ok(!v.boxes.some(b => b.id === "README.md"));
});
test("revealPath", () => {
  assert.deepEqual(revealPath(tree, "pkg/sub/b.py"), ["pkg/", "pkg/sub/"]);
  assert.deepEqual(revealPath(tree, "ext:Path"), ["ext:"]);
  assert.deepEqual(revealPath(tree, "nope"), []);
});
test("treeRows: collapsed, filters, open", () => {
  const ids = (rows) => rows.map(r => r.id);
  assert.deepEqual(ids(treeRows(tree, S(), new Set(), "")), ["lib/", "pkg/", "tests/"]);
  assert.ok(ids(treeRows(tree, S({ showDocs: true, showExternal: true }), new Set(), "")).includes("README.md"));
  const open = treeRows(tree, S(), new Set(["pkg/"]), "");
  assert.deepEqual(ids(open), ["lib/", "pkg/", "pkg/a.py", "pkg/lone.py", "pkg/sub/", "tests/"]);
  const sub = open.find(r => r.id === "pkg/sub/");
  assert.equal(sub.open, false); assert.equal(sub.hasChildren, true); assert.equal(sub.depth, 1);
});
test("treeRows: search", () => {  // Review Focus 4
  const rows = treeRows(tree, S(), new Set(), "B.P");
  assert.deepEqual(rows.map(r => r.id), ["pkg/", "pkg/sub/", "pkg/sub/b.py"]);
  assert.ok(rows.every(r => r.type === "file" || r.open));
});
test("treeRows: check states", () => {
  const c = (h, id) => treeRows(tree, S({ hidden: h }), new Set(["pkg/", "pkg/sub/"]), "").find(r => r.id === id).check;
  assert.equal(c(["pkg/sub/b.py"], "pkg/"), "partial");
  assert.equal(c(["pkg/"], "pkg/sub/b.py"), "off");
  assert.equal(c([], "pkg/"), "on");
});
test("unhide: file inside hidden folder becomes the only visible one on its path", () => {
  const ids = (s) => [...s].sort();
  assert.deepEqual(ids(unhide(tree, new Set(["pkg/"]), "pkg/sub/b.py")), ["pkg/a.py", "pkg/lone.py"]);
  assert.deepEqual(ids(unhide(tree, new Set(["pkg/", "lib/"]), "pkg/a.py")), ["lib/", "pkg/lone.py", "pkg/sub/"]);
  assert.deepEqual(ids(unhide(tree, new Set(["pkg/sub/b.py", "pkg/a.py"]), "pkg/")), []);
  assert.deepEqual(ids(unhide(tree, new Set(["lib/c.py"]), "lib/c.py")), []);
});
test("treeRows: folder matching by name lists its children", () => {
  const rows = treeRows(tree, S(), new Set(), "sub");
  assert.deepEqual(rows.map(r => r.id), ["pkg/", "pkg/sub/", "pkg/sub/b.py"]);
  assert.deepEqual(treeRows(tree, S(), new Set(), "pkg").map(r => r.id), ["pkg/", "pkg/a.py", "pkg/lone.py", "pkg/sub/"]);
});
test("treeRows: folder with every allowed leaf hidden is off", () => {
  const r = treeRows(tree, S({ hidden: ["pkg/a.py", "pkg/lone.py", "pkg/sub/b.py"] }), new Set(), "");
  assert.equal(r.find(x => x.id === "pkg/").check, "off");
});

// Symbol level (spec v3): same content as tests/fixtures/sym_graph.json after build_model.
const SM = { files: [{path:"pkg/__init__.py",kind:"code"},{path:"pkg/a.py",kind:"code"},{path:"pkg/b.py",kind:"code"},{path:"tests/test_a.py",kind:"test"}],
  external: [],
  symbols: [{id:"sym:run",name:"run()",file:"pkg/a.py",parent:"pkg/a.py",kind:"func",loc:"L3"},
            {id:"sym:K",name:"K",file:"pkg/a.py",parent:"pkg/a.py",kind:"class",loc:"L6"},
            {id:"sym:km",name:".go()",file:"pkg/a.py",parent:"sym:K",kind:"func",loc:"L7"},
            {id:"sym:g",name:"g()",file:"pkg/b.py",parent:"pkg/b.py",kind:"func",loc:"L2"},
            {id:"sym:t1",name:"test_run()",file:"tests/test_a.py",parent:"tests/test_a.py",kind:"func",loc:"L2"}],
  edges: [E("sym:run","sym:g",1,"calls"),E("sym:km","sym:g",1,"calls"),E("sym:run","sym:km",1,"calls"),
          E("pkg/a.py","pkg/b.py",1,"imports_from"),E("pkg/a.py","sym:g",1,"calls"),E("sym:t1","sym:run",1,"calls")] };
const ST = buildTree(SM);

test("files collapsed: same as file level", () => {
  assert.deepEqual(arrowSet(visibleView(ST, SM, S({expanded:["pkg/"]}))), ["pkg/a.py->pkg/b.py:4"]);
});
test("open a.py: functions and collapsed class", () => {
  const v = visibleView(ST, SM, S({expanded:["pkg/","pkg/a.py"]}));
  assert.ok(v.boxes.some(b => b.id === "sym:K" && b.collapsed && b.childCount === 1));
  assert.deepEqual(arrowSet(v), ["pkg/a.py->pkg/b.py:2", "sym:K->pkg/b.py:1", "sym:run->pkg/b.py:1", "sym:run->sym:K:1"]);  // Focus 4
});
test("module-level source stays on file frame", () => {  // Focus 2
  const v = visibleView(ST, SM, S({expanded:["pkg/","pkg/a.py","pkg/b.py"]}));
  assert.ok(arrowSet(v).includes("pkg/a.py->sym:g:1"));
  assert.ok(arrowSet(v).includes("pkg/a.py->pkg/b.py:1"));
});
test("hide all functions of a file: file stays", () => {  // Focus 1
  const v = visibleView(ST, SM, S({expanded:["pkg/","pkg/a.py"], hidden:["sym:run","sym:K"]}));
  assert.ok(v.boxes.some(b => b.id === "pkg/a.py"));
  assert.deepEqual(arrowSet(v), ["pkg/a.py->pkg/b.py:2"]);
});
test("test symbol arrows follow showTests", () => {  // Focus 3
  const st = (t) => arrowSet(visibleView(ST, SM, S({showTests:t, expanded:["pkg/","pkg/a.py","tests/","tests/test_a.py"]})));
  assert.ok(!st(false).some(s => s.startsWith("sym:t1")));
  assert.ok(st(true).includes("sym:t1->sym:run:1"));
});
test("treeRows: file has children, search finds symbols", () => {
  const rows = treeRows(ST, S(), new Set(["pkg/"]), "");
  assert.equal(rows.find(r => r.id === "pkg/a.py").hasChildren, true);
  assert.equal(rows.find(r => r.id === "pkg/__init__.py").hasChildren, false);
  assert.deepEqual(treeRows(ST, S(), new Set(), "go").map(r => r.id), ["pkg/", "pkg/a.py", "sym:K", "sym:km"]);
  assert.equal(revealPath(ST, "sym:km").join(","), "pkg/,pkg/a.py,sym:K");
});
