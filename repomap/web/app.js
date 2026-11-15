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
  let seq = 0, dragged = false, selected = null; // selected: box id or arrow object shown in the panel
  const notes = model.notes || {};
  const refs = new Map((model.symbols || []).map((x) => [x.id, x.ref]));
  // Name the CLI uses: symbol ref, folder without trailing "/", file path.
  const ref = (id) => refs.get(id) || id.replace(/\/$/, "").replace(/^concept:/, "");

  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(SVGNS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const label = (b) => baseLabel(b) + (notes[b.id] ? " 📝" : "");
  const baseLabel = (b) => {
    if (b.type === "file" || b.type === "class") {
      if (!b.hasChildren) return b.name;
      const n = b.childCount ? `${b.childCount} ${b.type === "file" ? "symbols" : "methods"}` : "0 shown";
      const hid = b.hiddenCount ? `, ${b.hiddenCount} hidden` : "";
      if (b.collapsed) return `▸ ${b.name} (${n}${hid})`;
      return b.childCount ? `▾ ${b.name}` : `▾ ${b.name} (${n}${hid})`;
    }
    return b.collapsed ? `▸ ${b.name}/ (${b.fileCount} ${b.type === "extroot" ? "symbols" : b.type === "conroot" ? "concepts" : "files"})`
      : (b.type === "dir" ? `▾ ${b.name}/` : b.type === "extroot" || b.type === "conroot" ? `▾ ${b.name}` : b.name);
  };
  const container = (b) => b.type === "dir" || b.type === "extroot" || b.type === "conroot" || b.hasChildren;
  // "file:Lnn" for symbols, the id otherwise.
  const where = (id) => {
    let n = tree.byId.get(id), f = n;
    if (!n || (n.type !== "func" && n.type !== "class")) return id;
    while (f.type !== "file") f = f.parent;
    return `${n.name} ${f.id}:${n.loc}`;
  };
  const textW = (s) => Math.max(60, s.length * 7.2 + 20);
  const depth = (id) => RepoMap.revealPath(tree, id).length;

  function toElk(view) {
    const kids = new Map();
    for (const b of view.boxes) (kids.get(b.parent) || kids.set(b.parent, []).get(b.parent)).push(b);
    const node = (b) => {
      const n = { id: b.id, box: b, labels: [{ text: label(b) }] };
      const ch = kids.get(b.id) || [];
      if (container(b) && !b.collapsed && ch.length) { // open with nothing visible: drawn as a leaf, still clickable
        n.children = ch.map(node);
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
      const grp = el("g", { class: `box ${b.type}${b.id === focusId ? " focus" : ""}${notes[b.id] ? (notes[b.id].stale ? " stale" : " noted") : ""}${b.collapsed ? " collapsed" : ""}${b.manual ? " manual" : ""}${b.type === "file" ? " k-" + (tree.byId.get(b.id).kind || "") : ""}`, "data-id": b.id }, boxLayer);
      const open = !!n.children;
      el("rect", { x, y, width: n.width, height: n.height, class: open ? `frame d${depth(b.id) % 4}` : "leaf", rx: b.type === "func" ? 10 : 4 }, grp);
      const t = el("text", { x: x + 8, y: y + 19 }, grp);
      t.textContent = label(b);
      const title = el("title", {}, grp);
      title.textContent = where(b.id);
      grp.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (dragged) return;
        if (container(b)) { select(b.id); toggle(b.id); } else if (b.type !== "ext") selected === b.id ? closePanel() : select(b.id);
      });
      for (const c of n.children || []) drawNode(c, x, y);
    };
    for (const c of g.children || []) drawNode(c, 0, 0);
    for (const { edge, sections } of RepoMap.absoluteLayout(g).edges) {
      const a = edge.arrow;
      for (const pts of sections) {
        const d = "M" + pts.map((p) => `${p.x},${p.y}`).join("L");
        const grp = el("g", { class: (a.inner ? "arrow self" : "arrow") + (a.manual ? " manual" : ""), "data-src": a.src, "data-tgt": a.tgt }, edgeLayer);
        el("path", { d, class: "hit" }, grp);
        el("path", { d, class: "line", "stroke-width": 1 + Math.log2(a.count), "marker-end": "url(#head)" }, grp);
        const m = pts[Math.floor((pts.length - 1) / 2)], m2 = pts[Math.floor((pts.length - 1) / 2) + 1] || m;
        const t = el("text", { x: (m.x + m2.x) / 2, y: (m.y + m2.y) / 2 - 4, class: "count" }, grp);
        t.textContent = a.count;
        grp.addEventListener("click", (ev) => { ev.stopPropagation(); if (dragged) return; selected = a; show(a); });
      }
    }
  }

  const add = (tag, text, cls, parent = panel) => { const e = document.createElement(tag); e.textContent = text; if (cls) e.className = cls; parent.appendChild(e); return e; };
  function openPanel(head) {
    panel.textContent = "";
    const top = add("div", "", "top");
    add("div", head, "head", top);
    const x = add("button", "✕", "close", top);
    x.type = "button"; x.setAttribute("aria-label", "Close details");
    x.addEventListener("click", closePanel);
    panel.hidden = false;
  }
  function closePanel() { selected = null; panel.hidden = true; }

  const KIND = { dir: "folder", file: "file", class: "class", func: "function", conroot: "concepts", concept: "concept" };
  function select(id) {
    const n = tree.byId.get(id);
    if (!n || !KIND[n.type]) return;
    selected = id;
    openPanel(KIND[n.type]);
    add("div", where(id));
    const note = notes[id], name = ref(id);
    if (n.manual || n.type === "concept") { add("div", "added manually", "more"); add("code", `repomap link delete ${name}`); }
    if (note) {
      add("div", note.text, "note");
      if (note.stale) { add("span", "may be outdated", "badge"); add("code", `Checked it? Run: repomap note ok ${name}`); }
    } else {
      add("div", 'No note yet. Ask your agent about it, then say "save it".', "more");
      add("code", `repomap note add ${name} "..."`);
    }
    const under = RepoMap.notesUnder(tree, notes, id);
    if (under.length) {
      const ul = add("ul", "");
      for (const u of under) add("li", `${u.name}: ${u.text.split("\n")[0]}` + (u.stale ? " (may be outdated)" : ""), "", ul);
    }
  }

  function show(a) {
    openPanel(`${where(a.src)} → ${where(a.tgt)}`);
    if (a.inner) add("div", `(within ${where(RepoMap.revealPath(tree, a.tgt).includes(a.src) ? a.src : a.tgt)})`, "more");
    add("div", `${a.count} links: ` + Object.entries(a.by_rel).map(([r, c]) => `${r} ${c}`).join(", "));
    const ul = add("ul", "");
    for (const s of a.samples) {
      const li = document.createElement("li");
      li.textContent = `${s.from} → ${s.to} (${s.rel}) ${s.loc === "manual" ? "(manual)" : s.loc}`;
      ul.appendChild(li);
    }
    if (a.count > a.samples.length) add("div", `… ${a.samples.length}/${a.count} samples`, "more");
  }

  async function render() {
    const my = ++seq;
    const view = RepoMap.visibleView(tree, model, state);
    // Old arrow objects are gone after re-layout; a selected box stays only while it is drawn.
    if (selected && (typeof selected !== "string" || !view.boxes.some((b) => b.id === selected))) closePanel();
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
      name.className = "name t-" + r.type; name.textContent = r.name + (r.type === "dir" ? "/" : "") + (notes[r.id] ? " 📝" : "");
      name.title = where(r.id);
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
  // Theme: explicit choice in data-theme, else follow the OS. Storage may throw (private mode, file://).
  const root = document.documentElement, darkOS = matchMedia("(prefers-color-scheme: dark)");
  const isDark = () => root.dataset.theme ? root.dataset.theme === "dark" : darkOS.matches;
  const syncTheme = () => { const d = isDark(); $("theme-toggle").textContent = d ? "Light" : "Dark"; $("theme-toggle").setAttribute("aria-pressed", String(d)); };
  try { const t = localStorage.getItem("repomap-theme"); if (t === "light" || t === "dark") root.dataset.theme = t; } catch (e) {}
  $("theme-toggle").addEventListener("click", () => {
    root.dataset.theme = isDark() ? "light" : "dark";
    try { localStorage.setItem("repomap-theme", root.dataset.theme); } catch (e) {}
    syncTheme();
  });
  darkOS.addEventListener("change", syncTheme);
  syncTheme();
  svg.addEventListener("click", () => { if (!dragged) closePanel(); });

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
  // Drag/arrow-key resize for side tree and details panel; width remembered per viewer.
  document.querySelectorAll(".grip").forEach((g) => {
    const el = $(g.dataset.for), right = g.dataset.for === "panel", key = "repomap.w." + g.dataset.for, def = el.offsetWidth || (right ? 320 : 280);
    const set = (w) => { w = Math.round(Math.min(innerWidth * 0.6, Math.max(200, w))); el.style.width = w + "px"; try { localStorage.setItem(key, w); } catch (e) {} };
    try { const w = +localStorage.getItem(key); if (w) el.style.width = Math.min(innerWidth * 0.6, Math.max(200, w)) + "px"; } catch (e) {}
    g.addEventListener("pointerdown", (ev) => {
      ev.preventDefault(); g.setPointerCapture(ev.pointerId);
      const mv = (e) => set(right ? innerWidth - e.clientX : e.clientX - el.getBoundingClientRect().left);
      g.addEventListener("pointermove", mv);
      g.addEventListener("pointerup", () => g.removeEventListener("pointermove", mv), { once: true });
    });
    g.addEventListener("dblclick", () => set(def));
    g.addEventListener("keydown", (ev) => {
      const d = { ArrowLeft: -20, ArrowRight: 20 }[ev.key];
      if (d) { ev.preventDefault(); set(el.offsetWidth + (right ? -d : d)); }
    });
  });
  apply();
  render();
  drawTree();
})();
