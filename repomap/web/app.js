// UI: ELK layout of the visible view, SVG drawing, pan/zoom, toggles, arrow details.
(function () {
  "use strict";
  const MAX_VISIBLE = 400;
  const SVGNS = "http://www.w3.org/2000/svg";
  const model = JSON.parse(document.getElementById("model").textContent);
  const tree = RepoMap.buildTree(model);
  const elk = new ELK();
  const state = { expanded: new Set(), showTests: false, showDocs: false, showExternal: false, hidden: new Set() };
  const treeOpen = new Set(); // tree panel open/closed, independent of state.expanded
  let focusId = null;
  const $ = (id) => document.getElementById(id);
  const svg = $("map"), viewport = $("viewport"), panel = $("panel");
  let seq = 0, pinned = null, dragged = false;

  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(SVGNS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const label = (b) => b.collapsed ? `▸ ${b.name}/ (${b.fileCount} ${b.type === "extroot" ? "symbols" : "files"})`
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
      const grp = el("g", { class: `box ${b.type}${b.id === focusId ? " focus" : ""}${b.collapsed ? " collapsed" : ""}${b.type === "file" ? " k-" + (tree.byId.get(b.id).kind || "") : ""}`, "data-id": b.id }, boxLayer);
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
        grp.addEventListener("mouseleave", () => { if (!pinned) panel.hidden = true; });
        grp.addEventListener("click", (ev) => { ev.stopPropagation(); if (dragged) return; pinned = a; show(a); });
      }
    }
  }

  function show(a) {
    panel.textContent = "";
    const add = (tag, text, cls) => { const e = document.createElement(tag); e.textContent = text; if (cls) e.className = cls; panel.appendChild(e); return e; };
    add("div", `${a.src} → ${a.tgt}`, "head");
    add("div", `${a.count} links: ` + Object.entries(a.by_rel).map(([r, c]) => `${r} ${c}`).join(", "));
    const ul = add("ul", "");
    for (const s of a.samples) {
      const li = document.createElement("li");
      li.textContent = `${s.from} → ${s.to} (${s.rel}) ${s.loc}`;
      ul.appendChild(li);
    }
    if (a.count > a.samples.length) add("div", `… ${a.samples.length}/${a.count} samples`, "more");
    panel.hidden = false;
  }

  async function render() {
    const my = ++seq;
    const view = RepoMap.visibleView(tree, model, state);
    pinned = null; panel.hidden = true; // old arrow objects are gone after re-layout
    $("stats").textContent = `${view.boxes.length} boxes, ${view.arrows.length} arrows`;
    try {
      const g = await elk.layout(toElk(view));
      if (my === seq) { draw(g); focusId = null; } // focus lasts until the next draw
      return my === seq;
    } catch (err) {
      $("stats").textContent = "Layout error: " + err;
      console.error(err);
    }
  }

  const tooBig = () => {
    const n = RepoMap.visibleView(tree, model, state).total;
    return n > MAX_VISIBLE && !confirm(`This will show ${n} items and may be slow. Continue?`);
  };

  function toggle(id) {
    if (state.expanded.has(id)) {
      state.expanded.delete(id);
    } else {
      state.expanded.add(id);
      if (tooBig()) { state.expanded.delete(id); return; }
    }
    render();
  }

  function drawTree() {
    const box = $("tree"), a = document.activeElement;
    // Rebuilding drops focus; remember the focused control by row id + class to restore it.
    const keep = box.contains(a) ? [a.closest(".row").dataset.id, a.className] : null;
    box.textContent = "";
    for (const r of RepoMap.treeRows(tree, state, treeOpen, $("tree-search").value.trim())) {
      const row = document.createElement("div");
      row.className = "row" + (r.check === "off" ? " off" : "");
      row.dataset.id = r.id;
      row.style.paddingLeft = 8 + r.depth * 14 + "px";
      const tw = document.createElement(r.hasChildren ? "button" : "span");
      tw.className = "tw";
      if (r.hasChildren) {
        tw.type = "button"; tw.textContent = r.open ? "▾" : "▸";
        tw.setAttribute("aria-label", (r.open ? "Collapse " : "Expand ") + r.name);
        tw.addEventListener("click", () => { treeOpen.has(r.id) ? treeOpen.delete(r.id) : treeOpen.add(r.id); drawTree(); });
      }
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.className = "cb"; cb.checked = r.check === "on"; cb.indeterminate = r.check === "partial";
      cb.setAttribute("aria-label", "Show " + r.id);
      cb.addEventListener("change", () => setShown(r.id, cb.checked));
      const name = document.createElement("span");
      name.className = "name"; name.textContent = r.name + (r.type === "dir" ? "/" : ""); name.title = r.id;
      if (r.check !== "off") name.addEventListener("click", () => focusOn(r.id));
      row.append(tw, cb, name);
      box.appendChild(row);
      if (keep && keep[0] === r.id) row.querySelector("." + keep[1])?.focus();
    }
  }

  function setShown(id, on) {
    if (on) {
      const before = state.hidden;
      state.hidden = RepoMap.unhide(tree, before, id);
      if (tooBig()) state.hidden = before;
    } else state.hidden.add(id);
    render(); drawTree();
  }

  async function focusOn(id) {
    const added = RepoMap.revealPath(tree, id).filter((p) => !state.expanded.has(p));
    added.forEach((p) => state.expanded.add(p));
    if (tooBig()) { added.forEach((p) => state.expanded.delete(p)); return; }
    focusId = id;
    if (!(await render())) return;
    const node = viewport.querySelector(`[data-id="${CSS.escape(id)}"] rect`);
    if (!node) return;
    const b = node.getBBox(), r = svg.getBoundingClientRect();
    tx = r.width / 2 - (b.x + b.width / 2) * k; ty = r.height / 2 - (b.y + b.height / 2) * k; apply();
  }

  for (const [id, key] of [["opt-tests", "showTests"], ["opt-docs", "showDocs"], ["opt-ext", "showExternal"]]) {
    $(id).addEventListener("change", (ev) => {
      state[key] = ev.target.checked;
      if (ev.target.checked && tooBig()) { state[key] = ev.target.checked = false; return; }
      render(); drawTree();
    });
  }
  $("collapse-all").addEventListener("click", () => { state.expanded.clear(); render(); drawTree(); });
  $("show-all").addEventListener("click", () => {
    const before = state.hidden;
    state.hidden = new Set();
    if (tooBig()) { state.hidden = before; return; }
    render(); drawTree();
  });
  $("tree-search").addEventListener("input", drawTree);
  const setSide = (open) => { $("side").hidden = !open; $("side-toggle").setAttribute("aria-expanded", String(open)); };
  $("side-toggle").addEventListener("click", () => setSide($("side").hidden));
  setSide(window.innerWidth >= 640);
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
  svg.addEventListener("pointerdown", (ev) => { drag = { x: ev.clientX - tx, y: ev.clientY - ty, sx: ev.clientX, sy: ev.clientY }; dragged = false; });
  window.addEventListener("pointermove", (ev) => {
    if (!drag) return;
    if (!dragged && Math.hypot(ev.clientX - drag.sx, ev.clientY - drag.sy) <= 4) return;
    tx = ev.clientX - drag.x; ty = ev.clientY - drag.y; dragged = true; apply();
  });
  window.addEventListener("pointerup", () => { drag = null; });
  apply();
  render();
  drawTree();
})();
