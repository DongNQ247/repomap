// Pure logic: which boxes are visible and which (lifted, merged) arrows connect them.

export function buildTree(model) {
  const root = { id: "", name: "", type: "dir", parent: null, children: [] };
  const byId = new Map([["", root]]);
  const add = (node, parent) => { node.parent = parent; parent.children.push(node); byId.set(node.id, node); return node; };
  for (const f of model.files) {
    const parts = f.path.split("/");
    let cur = root, prefix = "";
    for (const dir of parts.slice(0, -1)) {
      prefix += dir + "/";
      cur = byId.get(prefix) || add({ id: prefix, name: dir, type: "dir", children: [] }, cur);
    }
    add({ id: f.path, name: parts[parts.length - 1], type: "file", kind: f.kind, children: [] }, cur);
  }
  const ext = add({ id: "ext:", name: "External", type: "extroot", children: [] }, root);
  for (const x of model.external) add({ id: x.id, name: x.label, type: "ext", children: [] }, ext);
  root.byId = byId;
  return root;
}

// Filter-button rule for a leaf (file or external symbol); ignores `hidden`.
const allowedLeaf = (n, state) => n.type === "file" ? (state.showDocs || n.kind !== "doc") : state.showExternal;
const isLeaf = (n) => n.type === "file" || n.type === "ext";

// True if the node or any ancestor is in `hidden`.
export function isHidden(n, hidden) {
  if (!hidden) return false;
  for (; n; n = n.parent) if (hidden.has(n.id)) return true;
  return false;
}

// Filter-button rule for any node: leaves by allowedLeaf, containers if they hold an allowed leaf.
export function allowed(n, state) {
  return isLeaf(n) ? allowedLeaf(n, state) : n.children.some((c) => allowed(c, state));
}

export function visibleView(tree, model, state) {
  const byId = tree.byId;
  const shown = (n) => isLeaf(n) ? allowedLeaf(n, state) && !isHidden(n, state.hidden) : leafCount(n) > 0;
  const counts = new Map();
  function leafCount(n) {
    if (counts.has(n.id)) return counts.get(n.id);
    let c = 0;
    for (const ch of n.children) c += isLeaf(ch) ? (shown(ch) ? 1 : 0) : leafCount(ch);
    counts.set(n.id, c);
    return c;
  }
  const isOpen = (n) => n.id === "" || state.expanded.has(n.id);

  const boxes = [], visible = new Set();
  (function walk(n) {
    for (const ch of n.children) {
      if (!shown(ch)) continue;
      const container = ch.type === "dir" || ch.type === "extroot";
      boxes.push({ id: ch.id, name: ch.name, type: ch.type, parent: n.id,
        collapsed: container && !isOpen(ch), fileCount: container ? leafCount(ch) : 0 });
      visible.add(ch.id);
      if (container && isOpen(ch)) walk(ch);
    }
  })(tree);

  // Lift an endpoint to its nearest visible ancestor (null if hidden or unknown).
  const lift = (id) => {
    let n = byId.get(id);
    if (!n || !shown(n)) return null;
    while (n && !visible.has(n.id)) n = n.parent;
    return n ? n.id : null;
  };
  const merged = new Map();
  for (const e of model.edges) {
    const srcNode = byId.get(e.src);
    if (!state.showTests && srcNode && srcNode.kind === "test") continue;
    const s = lift(e.src), t = lift(e.tgt);
    if (s === null || t === null || s === t) continue;
    const key = s + "\u0000" + t;
    let a = merged.get(key);
    if (!a) merged.set(key, a = { src: s, tgt: t, count: 0, by_rel: {}, samples: [] });
    a.count += e.count;
    for (const [r, c] of Object.entries(e.by_rel)) a.by_rel[r] = (a.by_rel[r] || 0) + c;
    if (a.samples.length < 20) a.samples.push(...e.samples.slice(0, 20 - a.samples.length));
  }
  const arrows = [...merged.values()];
  return { boxes, arrows, total: boxes.length + arrows.length };
}

// ELK gives node x/y relative to the parent and edge points relative to e.container
// (root when absent); return absolute boxes by id and absolute point lists per edge.
export function absoluteLayout(g) {
  const pos = new Map([[g.id, { x: 0, y: 0, width: g.width, height: g.height }]]);
  const walk = (n, ox, oy) => {
    for (const c of n.children || []) {
      const x = ox + c.x, y = oy + c.y;
      pos.set(c.id, { x, y, width: c.width, height: c.height });
      walk(c, x, y);
    }
  };
  walk(g, 0, 0);
  const edges = (g.edges || []).map((e) => {
    const o = pos.get(e.container) || pos.get(g.id);
    return { edge: e, sections: (e.sections || []).map((s) =>
      [s.startPoint, ...(s.bendPoints || []), s.endPoint].map((p) => ({ x: p.x + o.x, y: p.y + o.y }))) };
  });
  return { pos, edges };
}

// Ancestor folder/frame ids of `id` (outermost first, root excluded); [] if unknown.
export function revealPath(tree, id) {
  const out = [];
  for (let n = tree.byId.get(id)?.parent; n && n.id !== ""; n = n.parent) out.unshift(n.id);
  return out;
}

// Hidden set after re-showing `id`: drop it and its hidden descendants; for each hidden
// ancestor, unhide it but hide its other children, so only `id` (and its path) appears.
export function unhide(tree, hidden, id) {
  const self = new Set([id]), path = [...revealPath(tree, id), id];
  const out = new Set([...hidden].filter((h) => !isHidden(tree.byId.get(h), self)));
  let covered = false;
  for (let i = 0; i < path.length - 1; i++) {
    covered = out.delete(path[i]) || covered;
    if (covered) for (const c of tree.byId.get(path[i]).children) if (c.id !== path[i + 1]) out.add(c.id);
  }
  return out;
}

// Rows of the side tree panel, in tree order. A folder whose name matches the query lists
// all its children; deeper levels then follow treeOpen as without a query.
export function treeRows(tree, state, treeOpen, query) {
  const q0 = (query || "").toLowerCase(), rows = [];
  const nameHit = (n) => n.name.toLowerCase().includes(q0);
  const matches = (n) => nameHit(n) || n.children.some((c) => allowed(c, state) && matches(c));
  const check = (n) => {
    const leaves = [];
    (function collect(m) { if (isLeaf(m)) leaves.push(m); else m.children.forEach((c) => allowed(c, state) && collect(c)); })(n);
    const on = leaves.filter((l) => !isHidden(l, state.hidden)).length;
    return on === 0 ? "off" : on < leaves.length ? "partial" : "on";
  };
  (function walk(n, depth, q) { // q: "" once inside a name-matched folder
    for (const ch of n.children) {
      if (!allowed(ch, state) || (q && !matches(ch))) continue;
      const hasChildren = !isLeaf(ch);
      const open = hasChildren && (q ? true : treeOpen.has(ch.id));
      rows.push({ id: ch.id, name: ch.name, type: ch.type, depth, hasChildren, open, check: check(ch) });
      if (open) walk(ch, depth + 1, nameHit(ch) ? "" : q);
    }
  })(tree, 0, q0);
  return rows;
}

globalThis.RepoMap = { buildTree, visibleView, absoluteLayout, revealPath, treeRows, unhide };
