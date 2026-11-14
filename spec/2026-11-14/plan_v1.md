# Repo Map Implementation Plan (plan v1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI `python3 -m repomap graph.json -o map.html` → một file HTML tự chứa vẽ toàn repo dạng hộp lồng hộp (folder ⊃ file) với mũi tên file→file gộp được khi thu gọn.

**Architecture:** Python (stdlib) đọc `graph.json`, quy về mô hình cấp file (danh sách file + cạnh file→file có `count`, `by_rel`, `samples`), nhúng JSON vào template HTML. Trong trình duyệt: `aggregate.js` (thuần, test bằng Node) tính ô hiển thị + mũi tên gộp theo trạng thái mở/thu và các nút bật; `app.js` gọi ELK.js để bố cục và vẽ SVG.

**Tech Stack:** Python 3.10 stdlib (`json`, `argparse`, `unittest`), JS thuần, ELK.js `elkjs@0.9.3` (`elk.bundled.js`, nhúng inline), Node 24 (`node --test`) chỉ để test JS.

**Spec:** `spec/2026-11-14/spec_v1.md`

## Global Constraints

- Độc lập với graphify: không import graphify, không sửa repo graphify; chỉ phụ thuộc định dạng `graph.json`.
- Runtime Python chỉ dùng thư viện chuẩn; test Python dùng `unittest` (máy không có pytest).
- Chiều cạnh: `source → target` theo thứ tự trong link; nếu link có `_src`/`_tgt` thì dùng chúng. Không dùng NetworkX.
- Đầu ra: một file HTML tự chứa, mở offline (ELK nhúng inline, không CDN).
- Mũi tên chỉ từ relation `calls`, `imports`, `imports_from`. Bỏ cạnh trong cùng file.
- `count` = số link gốc, cộng chung các relation giữa cặp file.
- Mặc định: mọi folder thu gọn; mũi tên từ file test tắt; docs/config ẩn; khung "Bên ngoài" ẩn.
- Thư viện ngoài = node có `source_file` rỗng/thiếu; hiển thị theo `label`, không gom theo thư viện.
- Ngưỡng cảnh báo khi mở folder: `MAX_VISIBLE = 400` (ô + mũi tên hiển thị).

## Review Focus

1. `graph.json` thiếu khóa `links` (một số phiên bản NetworkX ghi `edges`) → vẫn đọc được. Test ở Task 1.
2. Link trỏ tới id node không tồn tại → bỏ qua, không crash. Test ở Task 1.
3. File chỉ có cạnh tới chính nó hoặc không có cạnh nào → vẫn hiện thành ô. Test ở Task 2.
4. Mở folder sâu nhiều cấp rồi thu folder cha → mũi tên quay về đúng ô cha, không mũi tên lơ lửng. Test ở Task 3.
5. Tên file chứa ký tự HTML (`<`, `&`, `</script>`) → không phá HTML. Test ở Task 4.

---

## File Structure

```
repomap/
  repomap/__init__.py
  repomap/__main__.py      # CLI
  repomap/load.py          # đọc graph.json + chiều cạnh
  repomap/model.py         # gộp về cấp file, phân loại file
  repomap/render.py        # nhúng model + JS vào template
  repomap/web/template.html
  repomap/web/aggregate.js # logic thuần: ô hiển thị + mũi tên gộp
  repomap/web/app.js       # ELK layout + vẽ SVG + tương tác
  repomap/web/vendor/elk.bundled.js
  tests/test_load.py  tests/test_model.py  tests/test_render.py
  tests/aggregate.test.mjs
  tests/fixtures/mini_graph.json
```

---

### Task 1: Đọc graph.json với chiều cạnh đúng

**Files:**
- Create: `repomap/__init__.py` (rỗng), `repomap/load.py`, `tests/__init__.py`, `tests/test_load.py`, `tests/fixtures/mini_graph.json`, `.gitignore` (`__pycache__/`, `out/`)

**Interfaces:**
- Produces: `load_graph(path: str | Path) -> tuple[dict[str, dict], list[dict]]` — map `id → node`, và list link đã chuẩn hoá mỗi link có `src`, `tgt`, `relation` (giữ nguyên các trường khác).

Fixture `mini_graph.json` (dùng chung Task 1–4), node:
`a1`(`pkg/a.py`), `a2`(`pkg/a.py`), `b1`(`pkg/sub/b.py`), `c1`(`lib/c.py`), `t1`(`tests/test_a.py`), `d1`(`README.md`), `x1`(label `Path`, `source_file: ""`), `lone`(`pkg/lone.py`).
Link: `a1→b1 calls`; `a2→b1 calls`; `a1→c1 imports_from`; `a1→a2 calls` (cùng file); `b1→c1 calls` với `_src:"c1", _tgt:"b1"` (marker đảo chiều); `t1→a1 calls`; `d1→a1 references`; `a1→x1 calls`; `a1→ghost calls` (id không tồn tại); `a1→b1 contains`.

- [ ] **Step 1: Viết test**

```python
class TestLoad(unittest.TestCase):
    def test_direction_marker_wins(self):
        nodes, links = load_graph(FIXTURE)
        l = [x for x in links if {x["src"], x["tgt"]} == {"b1", "c1"}][0]
        self.assertEqual((l["src"], l["tgt"]), ("c1", "b1"))
    def test_arc_order_is_direction(self):
        _, links = load_graph(FIXTURE)
        self.assertIn(("a1", "b1", "calls"), {(x["src"], x["tgt"], x["relation"]) for x in links})
    def test_edges_key_fallback(self):  # Review Focus 1
        # ghi bản sao fixture với "links" đổi tên thành "edges" vào tempdir
        nodes, links = load_graph(tmp_edges_copy)
        self.assertEqual(len(links), 9)  # 10 link, bỏ 1 link tới "ghost"
    def test_dangling_link_dropped(self):  # Review Focus 2
        _, links = load_graph(FIXTURE)
        self.assertNotIn("ghost", {x["tgt"] for x in links})
```

- [ ] **Step 2:** `python3 -m unittest tests.test_load -v` → FAIL (ImportError).
- [ ] **Step 3:** Cài `load_graph` trong `repomap/load.py`. `links = d.get("links", d.get("edges", []))`; `src = l.get("_src", l["source"])`, tương tự `tgt`; bỏ link có đầu mút không thuộc `nodes`.
- [ ] **Step 4:** Chạy lại → PASS.
- [ ] **Step 5:** `git add -A && git commit -m "feat: load graph.json with edge direction"`

---

### Task 2: Mô hình cấp file

**Files:** Create `repomap/model.py`, `tests/test_model.py`

**Interfaces:**
- Consumes: `load_graph` (Task 1).
- Produces: `build_model(nodes: dict[str, dict], links: list[dict]) -> dict` với dạng:

```json
{
  "files":    [{"path": "pkg/a.py", "kind": "code|test|doc"}],
  "external": [{"id": "ext:Path", "label": "Path"}],
  "edges":    [{"src": "pkg/a.py", "tgt": "pkg/sub/b.py", "count": 2,
                "by_rel": {"calls": 2},
                "samples": [{"from": "a1-label", "to": "b1-label", "rel": "calls", "loc": "pkg/a.py:L3"}]}]
}
```

  Đầu mút ngoài dùng id `ext:<label>`. `files` sắp theo `path`; `samples` tối đa 20 mục mỗi cạnh.
- Produces: `classify(path: str) -> str` — `"test"` nếu một thành phần thư mục là `tests`/`test`/`__tests__` hoặc tên khớp `test_*`, `*_test.*`, `*.test.*`, `*.spec.*`; `"doc"` nếu đuôi thuộc `{md, rst, txt, json, yml, yaml, toml, ini, cfg, csv, xml, csproj, sln}`; ngược lại `"code"`. Test thắng doc.

- [ ] **Step 1: Viết test**

```python
def m(): return build_model(*load_graph(FIXTURE))
class TestModel(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("tests/fixtures/x.go"), "test")
        self.assertEqual(classify("src/foo.spec.ts"), "test")
        self.assertEqual(classify("README.md"), "doc")
        self.assertEqual(classify("pkg/a.py"), "code")
    def test_counts_merge_relations(self):
        e = {(x["src"], x["tgt"]): x for x in m()["edges"]}
        self.assertEqual(e[("pkg/a.py", "pkg/sub/b.py")]["count"], 2)
        self.assertEqual(e[("pkg/a.py", "lib/c.py")]["by_rel"], {"imports_from": 1})
        self.assertIn(("lib/c.py", "pkg/sub/b.py"), e)
    def test_ignored(self):
        e = {(x["src"], x["tgt"]) for x in m()["edges"]}
        self.assertNotIn(("pkg/a.py", "pkg/a.py"), e)      # cùng file
        self.assertNotIn(("README.md", "pkg/a.py"), e)     # references
    def test_external_and_lonely(self):  # Review Focus 3
        model = m()
        self.assertIn({"id": "ext:Path", "label": "Path"}, model["external"])
        self.assertIn(("pkg/a.py", "ext:Path"), {(x["src"], x["tgt"]) for x in model["edges"]})
        self.assertIn("pkg/lone.py", [f["path"] for f in model["files"]])
```

- [ ] **Step 2:** `python3 -m unittest tests.test_model -v` → FAIL.
- [ ] **Step 3:** Cài `classify` và `build_model` trong `repomap/model.py`. `files` = mọi `source_file` khác rỗng; `loc` = `f"{source_file}:{source_location}"` của link.
- [ ] **Step 4:** Chạy lại → PASS.
- [ ] **Step 5:** `git commit -am "feat: file-level model"` (thêm file mới bằng `git add`).

---

### Task 3: Logic gộp mũi tên (JS thuần)

**Files:** Create `repomap/web/aggregate.js`, `tests/aggregate.test.mjs`

**Interfaces:**
- Consumes: dạng model của Task 2.
- Produces (ES module, cũng gán vào `globalThis.RepoMap` để dùng inline):
  - `buildTree(model) -> Tree` — cây folder; mỗi nút `{id, name, type: "dir"|"file"|"extroot"|"ext", kind?, children}`; id của dir là đường dẫn có `/` cuối (`"pkg/"`), file là path, gốc `""`, khung ngoài `"ext:"`.
  - `visibleView(tree, model, state) -> {boxes: Box[], arrows: Arrow[], total: number}`
    - `state = {expanded: Set<string>, showTests: bool, showDocs: bool, showExternal: bool}`
    - `Box = {id, name, type, parent, collapsed: bool, fileCount: number}` — chỉ các nút đang thấy (con của nút gốc/khung đang mở).
    - `Arrow = {src, tgt, count, by_rel, samples}` — đầu mút là box hiển thị gần nhất; trùng cặp thì cộng `count`, gộp `by_rel`, nối `samples` (cắt 20); bỏ nếu `src === tgt`.
    - `total = boxes.length + arrows.length`.
  - Lọc: `showTests=false` → bỏ cạnh có file nguồn `kind==="test"` (ô vẫn hiện); `showDocs=false` → ẩn file `kind==="doc"` và cạnh của chúng (dir chỉ còn doc thì ẩn); `showExternal=false` → ẩn khung `ext:` và cạnh tới nó.

- [ ] **Step 1: Viết test** (model nhỏ viết tay trong file test, cùng nội dung fixture)

```js
test("initial view: top level only, arrows lifted", () => {
  const v = visibleView(tree, model, S());   // S(): mọi cờ false, expanded rỗng
  assert.deepEqual(v.boxes.map(b => b.id).sort(), ["lib/", "pkg/", "tests/"]);
  assert.deepEqual(arrowSet(v), ["lib/->pkg/:1", "pkg/->lib/:1"]);  // pkg/a->lib/c, lib/c->pkg/sub/b
});
test("expand pkg/: inner arrows appear, sub/ still collapsed", () => {
  const v = visibleView(tree, model, S({expanded: ["pkg/"]}));
  assert.ok(arrowSet(v).includes("pkg/a.py->pkg/sub/:2"));
});
test("collapse parent after deep expand → no dangling arrows", () => {  // Review Focus 4
  const v = visibleView(tree, model, S({expanded: ["pkg/sub/"]}));  // cha pkg/ đang thu
  const ids = new Set(v.boxes.map(b => b.id));
  v.arrows.forEach(a => { assert.ok(ids.has(a.src) && ids.has(a.tgt)); });
});
test("toggles", () => {
  assert.ok(!arrowSet(visibleView(tree, model, S())).some(s => s.startsWith("tests/")));
  assert.ok(arrowSet(visibleView(tree, model, S({showTests: true}))).includes("tests/->pkg/:1"));
  assert.ok(visibleView(tree, model, S({showDocs: true})).boxes.some(b => b.id === "README.md"));
  assert.ok(visibleView(tree, model, S({showExternal: true})).boxes.some(b => b.id === "ext:"));
});
```

- [ ] **Step 2:** `node --test tests/` → FAIL.
- [ ] **Step 3:** Cài trong `aggregate.js`. Nâng đầu mút: đi từ file lên tổ tiên cho tới khi gặp nút có cha đang mở (gốc luôn mở).
- [ ] **Step 4:** `node --test tests/` → PASS.
- [ ] **Step 5:** Commit `feat: arrow aggregation logic`.

---

### Task 4: Render HTML + CLI

**Files:** Create `repomap/render.py`, `repomap/__main__.py`, `repomap/web/template.html`, `repomap/web/vendor/elk.bundled.js`, `tests/test_render.py`

**Interfaces:**
- Consumes: `load_graph`, `build_model`, `aggregate.js`.
- Produces: `render_html(model: dict) -> str`; CLI `python3 -m repomap GRAPH_JSON [-o OUT]` (mặc định `repomap.html` cạnh `GRAPH_JSON`), in đường dẫn file đã ghi; lỗi đọc file → thông báo lên stderr, exit 1.

`template.html` có 4 chỗ thay thế: `/*__ELK__*/`, `/*__AGGREGATE__*/`, `/*__APP__*/`, và `__MODEL__` trong `<script id="model" type="application/json">`. Tải ELK: `curl -L https://cdn.jsdelivr.net/npm/elkjs@0.9.3/lib/elk.bundled.js -o repomap/web/vendor/elk.bundled.js`. `aggregate.js` khi inline phải bỏ từ khóa `export` (render thay `export function` → `function`).

- [ ] **Step 1: Viết test**

```python
class TestRender(unittest.TestCase):
    def test_self_contained(self):
        html = render_html(build_model(*load_graph(FIXTURE)))
        self.assertNotIn("http://", html.split("<script")[0])
        self.assertNotIn('src="http', html)
        self.assertIn("pkg/sub/b.py", html)
    def test_html_escaping(self):  # Review Focus 5
        model = {"files": [{"path": "x</script><b>&.py", "kind": "code"}], "external": [], "edges": []}
        html = render_html(model)
        self.assertEqual(html.count("</script>"), html.count("<script"))
    def test_cli(self):
        # subprocess: python3 -m repomap FIXTURE -o tmp/out.html → returncode 0, file tồn tại
        # file không tồn tại → returncode 1
```

- [ ] **Step 2:** `python3 -m unittest tests.test_render -v` → FAIL.
- [ ] **Step 3:** Cài `render_html` (JSON nhúng: `json.dumps(model).replace("<", "\\u003c")`) và `__main__.py` (`argparse`).
- [ ] **Step 4:** Chạy lại → PASS.
- [ ] **Step 5:** Commit `feat: html render and CLI`.

---

### Task 5: Giao diện: bố cục ELK, vẽ, tương tác

**Files:** Create `repomap/web/app.js`; Modify `repomap/web/template.html`

**Interfaces:**
- Consumes: `RepoMap.buildTree`, `RepoMap.visibleView` (Task 3); `ELK` global; JSON trong `#model`.
- Produces: trang hoàn chỉnh.

Yêu cầu (không có test tự động; kiểm tra thủ công ở Step 3):
- Thanh công cụ: 3 checkbox "Mũi tên từ test", "Docs/config", "Bên ngoài" (mặc định bỏ chọn) + nút "Thu gọn hết".
- Chuyển `visibleView` sang đồ thị ELK: box dir/extroot đang mở → nút compound chứa con; box thu gọn/file → nút lá (nhãn tên; dir thu gọn thêm `▸` và `(N file)`). Tùy chọn ELK: `elk.algorithm: layered`, `elk.direction: RIGHT`, `elk.hierarchyHandling: INCLUDE_CHILDREN`, `elk.edgeRouting: ORTHOGONAL`. Cạnh nối giữa các cấp khác nhau: đặt tại nút gốc.
- Vẽ SVG từ kết quả ELK; khung dir viền nét đứt, màu theo cấp; nhãn số `count` trên mũi tên; độ dày mũi tên tăng theo log `count`.
- Click box dir/extroot: toggle trong `state.expanded`. Trước khi áp dụng mở: nếu `visibleView(...).total > MAX_VISIBLE (400)` → `confirm("Sẽ hiện N mục, có thể chậm. Tiếp tục?")`.
- Hover/click mũi tên: panel hiện `src → tgt`, `by_rel`, danh sách `samples` (`from → to (rel) loc`).
- Pan/zoom bằng chuột (wheel + kéo), không cần thư viện.
- Mỗi box giữ `data-id` = id ổn định (chuẩn bị giai đoạn 2 tô màu diff).

- [ ] **Step 1:** Cài `app.js`, nối vào template.
- [ ] **Step 2:** Chạy toàn bộ test: `python3 -m unittest discover tests -v && node --test tests/` → PASS.
- [ ] **Step 3: Kiểm tra trên dữ liệu thật**
  Run: `python3 -m repomap ~/workspace/project/graphify/graphify-out/graph.json -o out/map.html` (`out/` đã nằm trong `.gitignore`) rồi mở trong trình duyệt.
  Expected: thấy các mục cấp gốc của repo graphify (`graphify/`, `tests/`, `tools/`, `scripts/`, `worked/`…); mở `graphify/` thấy mũi tên `extract.py → extractors/` có số; mở tiếp `extractors/` thấy `extract.py → extractors/resolution.py` = số khớp với đếm link `calls|imports|imports_from` giữa 2 file trong graph.json; bật "Mũi tên từ test" thấy mũi tên từ `tests/`; không lỗi console.
- [ ] **Step 4:** Viết `README.md` ngắn (cách chạy, các nút). Commit `feat: interactive map UI`.

---

## Self-review

- Spec coverage: hộp lồng/thu gọn/gộp (T3, T5); toàn repo mở đầu thu gọn (T3 test 1); file code luôn hiện (T2 test lonely); test/docs/external toggles (T2 classify, T3 toggles, T5 UI); count + truy vết (T2 samples, T5 panel); hiệu năng/ngưỡng (T5 `MAX_VISIBLE`); offline (T4); chiều cạnh (T1); id ổn định cho giai đoạn 2 (T5); độc lập graphify (Global Constraints).
- Tên nhất quán: `load_graph`, `build_model`, `classify`, `render_html`, `buildTree`, `visibleView`, `MAX_VISIBLE`.
