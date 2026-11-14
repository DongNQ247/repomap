// UI: ELK layout of the visible view, SVG drawing, pan/zoom, toggles, arrow details.
(function () {
  "use strict";
  const MAX_VISIBLE = 400;
  const SVGNS = "http://www.w3.org/2000/svg";
  const model = JSON.parse(document.getElementById("model").textContent);
  const tree = RepoMap.buildTree(model);
  const elk = new ELK();
  const state = { expanded: new Set(), showTests: false, showDocs: false, showExternal: false };
  const $ = (id) => document.getElementById(id);
  const svg = $("map"), viewport = $("viewport"), panel = $("panel");
  let seq = 0, pinned = null, dragged = false;

  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(SVGNS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const label = (b) => b.collapsed ? `▸ ${b.name}/ (${b.fileCount} ${b.type === "extroot" ? "ký hiệu" : "file"})`
    : (b.type === "dir" ? `▾ ${b.name}/` : b.type === "extroot" ? `▾ ${b.name}` : b.name);
  const textW = (s) => Math.max(60, s.length * 7.2 + 20);
  const depth = (id) => id.startsWith("ext:") ? (id === "ext:" ? 0 : 1) : (id.replace(/\/$/, "").match(/\//g) || []).length;

  function toElk(view) {
    const kids = new Map();
    for (const b of view.boxes) (kids.get(b.parent) || kids.set(b.parent, []).get(b.parent)).push(b);
    const node = (b) => {
      const n = { id: b.id, box: b, labels: [{ text: label(b) }] };
      const open = (b.type === "dir" || b.type === "extroot") && !b.collapsed;
      if (open) {
        n.children = (kids.get(b.id) || []).map(node);
        n.layoutOptions = { "elk.padding": "[top=30,left=12,bottom=12,right=12]" };
      } else {
        n.width = textW(label(b));
        n.height = 30;
      }
      return n;
    };
    return {
      id: "__root__",
      layoutOptions: {
        "elk.algorithm": "layered", "elk.direction": "RIGHT",
        "elk.hierarchyHandling": "INCLUDE_CHILDREN", "elk.edgeRouting": "ORTHOGONAL",
        "elk.spacing.nodeNode": "20", "elk.layered.spacing.nodeNodeBetweenLayers": "40",
      },
      children: (kids.get("") || []).map(node),
      // Edges between different levels live at the root.
      edges: view.arrows.map((a, i) => ({ id: "e" + i, sources: [a.src], targets: [a.tgt], arrow: a })),
    };
  }

  function draw(g) {
    viewport.textContent = "";
    const boxLayer = el("g", {}, viewport), edgeLayer = el("g", {}, viewport);
    const drawNode = (n, ox, oy) => {
      const x = ox + n.x, y = oy + n.y, b = n.box;
      const grp = el("g", { class: `box ${b.type}${b.collapsed ? " collapsed" : ""}${b.type === "file" ? " k-" + (tree.byId.get(b.id).kind || "") : ""}`, "data-id": b.id }, boxLayer);
      const open = !!n.children;
      el("rect", { x, y, width: n.width, height: n.height, rx: 4, class: open ? `frame d${depth(b.id) % 4}` : "leaf" }, grp);
      const t = el("text", { x: x + 8, y: y + 19 }, grp);
      t.textContent = label(b);
      const title = el("title", {}, grp);
      title.textContent = b.id;
      if (b.type === "dir" || b.type === "extroot") grp.addEventListener("click", (ev) => { ev.stopPropagation(); if (!dragged) toggle(b.id); });
      for (const c of n.children || []) drawNode(c, x, y);
    };
    for (const c of g.children || []) drawNode(c, 0, 0);
    for (const { edge, sections } of RepoMap.absoluteLayout(g).edges) {
      const a = edge.arrow;
      for (const pts of sections) {
        const d = "M" + pts.map((p) => `${p.x},${p.y}`).join("L");
        const grp = el("g", { class: "arrow", "data-src": a.src, "data-tgt": a.tgt }, edgeLayer);
        el("path", { d, class: "hit" }, grp);
        el("path", { d, class: "line", "stroke-width": 1 + Math.log2(a.count), "marker-end": "url(#head)" }, grp);
        const m = pts[Math.floor((pts.length - 1) / 2)], m2 = pts[Math.floor((pts.length - 1) / 2) + 1] || m;
        const t = el("text", { x: (m.x + m2.x) / 2, y: (m.y + m2.y) / 2 - 4, class: "count" }, grp);
        t.textContent = a.count;
        grp.addEventListener("mouseenter", () => { if (!pinned) show(a); });
        grp.addEventListener("click", (ev) => { ev.stopPropagation(); pinned = a; show(a); });
      }
    }
  }

  function show(a) {
    panel.textContent = "";
    const add = (tag, text, cls) => { const e = document.createElement(tag); e.textContent = text; if (cls) e.className = cls; panel.appendChild(e); return e; };
    add("div", `${a.src} → ${a.tgt}`, "head");
    add("div", `${a.count} link: ` + Object.entries(a.by_rel).map(([r, c]) => `${r} ${c}`).join(", "));
    const ul = add("ul", "");
    for (const s of a.samples) {
      const li = document.createElement("li");
      li.textContent = `${s.from} → ${s.to} (${s.rel}) ${s.loc}`;
      ul.appendChild(li);
    }
    if (a.count > a.samples.length) add("div", `… ${a.samples.length}/${a.count} mẫu`, "more");
    panel.hidden = false;
  }

  async function render() {
    const my = ++seq;
    const view = RepoMap.visibleView(tree, model, state);
    $("stats").textContent = `${view.boxes.length} ô, ${view.arrows.length} mũi tên`;
    try {
      const g = await elk.layout(toElk(view));
      if (my === seq) draw(g);
    } catch (err) {
      $("stats").textContent = "Lỗi bố cục: " + err;
      console.error(err);
    }
  }

  function toggle(id) {
    if (state.expanded.has(id)) {
      state.expanded.delete(id);
    } else {
      state.expanded.add(id);
      const n = RepoMap.visibleView(tree, model, state).total;
      if (n > MAX_VISIBLE && !confirm(`Sẽ hiện ${n} mục, có thể chậm. Tiếp tục?`)) { state.expanded.delete(id); return; }
    }
    render();
  }

  for (const [id, key] of [["opt-tests", "showTests"], ["opt-docs", "showDocs"], ["opt-ext", "showExternal"]]) {
    $(id).addEventListener("change", (ev) => { state[key] = ev.target.checked; render(); });
  }
  $("collapse-all").addEventListener("click", () => { state.expanded.clear(); render(); });
  svg.addEventListener("click", () => { if (dragged) return; pinned = null; panel.hidden = true; });

  // Pan/zoom without libraries.
  let tx = 20, ty = 20, k = 1, drag = null;
  const apply = () => viewport.setAttribute("transform", `translate(${tx},${ty}) scale(${k})`);
  svg.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const r = svg.getBoundingClientRect(), px = ev.clientX - r.left, py = ev.clientY - r.top;
    const f = Math.exp(-ev.deltaY * 0.0015), nk = Math.min(4, Math.max(0.05, k * f));
    tx = px - (px - tx) * (nk / k); ty = py - (py - ty) * (nk / k); k = nk; apply();
  }, { passive: false });
  svg.addEventListener("pointerdown", (ev) => { drag = { x: ev.clientX - tx, y: ev.clientY - ty, }; dragged = false; });
  window.addEventListener("pointermove", (ev) => {
    if (!drag) return;
    tx = ev.clientX - drag.x; ty = ev.clientY - drag.y; dragged = true; apply();
  });
  window.addEventListener("pointerup", () => { drag = null; });
  apply();
  render();
})();
