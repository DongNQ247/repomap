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
  const ext = add({ id: "ext:", name: "Bên ngoài", type: "extroot", children: [] }, root);
  for (const x of model.external) add({ id: x.id, name: x.label, type: "ext", children: [] }, ext);
  root.byId = byId;
  return root;
}

export function visibleView(tree, model, state) {
  const byId = tree.byId;
  const shown = (n) => n.type === "file" ? (state.showDocs || n.kind !== "doc")
    : n.type === "ext" ? state.showExternal
    : n.type === "extroot" ? state.showExternal && n.children.length > 0
    : leafCount(n) > 0;
  const counts = new Map();
  function leafCount(n) {
    if (counts.has(n.id)) return counts.get(n.id);
    let c = 0;
    for (const ch of n.children) c += (ch.type === "file" || ch.type === "ext") ? (shown(ch) ? 1 : 0) : leafCount(ch);
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

globalThis.RepoMap = { buildTree, visibleView };
