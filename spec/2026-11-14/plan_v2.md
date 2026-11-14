# Repo Map v2 Implementation Plan (plan v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chữ trong công cụ chuyển sang tiếng Anh, và thêm panel cây bên trái (thu gọn được, tìm theo tên, checkbox ẩn/hiện từng file/folder, click tên để nhảy tới trên bản đồ).

**Architecture:** Logic thuần mở rộng trong `repomap/web/aggregate.js` (test bằng Node): `state.hidden` lọc ô và mũi tên; hàm mới `treeRows` sinh các dòng của cây (lọc, tìm, trạng thái checkbox) và `revealPath` tính folder cần mở. `app.js` chỉ vẽ panel từ `treeRows` và nối sự kiện. Không đổi phần Python ngoài test kiểm tra chữ.

**Tech Stack:** như v1 — JS thuần, ELK.js 0.9.3 inline, Python 3.10 stdlib + `unittest`, Node 24 (`node --test tests/*.test.mjs`).

**Spec:** `spec/2026-11-14/spec_v2.md` (kế thừa `spec_v1.md`). Mục 2 của spec v2 (bỏ diff) không cần code.

## Global Constraints

- Mọi chữ người dùng nhìn thấy (giao diện, `confirm`, README) bằng tiếng Anh; spec/plan giữ tiếng Việt.
- Ẩn file/folder → ô **và mọi mũi tên vào/ra nó biến mất hẳn**, không gộp lên folder cha. Ẩn folder = ẩn mọi thứ bên trong.
- Mở/thu trong cây **độc lập** với `state.expanded` của bản đồ.
- Cây chỉ liệt kê mục mà các nút lọc cho phép (doc khi `showDocs`; khung External khi `showExternal`). Mục bị ẩn bằng checkbox **vẫn nằm trong cây** (để bật lại).
- Trạng thái ẩn không lưu khi tải lại trang. Nút `Show all` xoá toàn bộ `hidden`.
- `total` và cảnh báo `MAX_VISIBLE = 400` tính sau khi bỏ mục ẩn.
- Không thêm thư viện; output vẫn là một file HTML tự chứa.

## Review Focus

1. Ẩn file là đầu mút của một mũi tên đã gộp lên folder thu gọn → phần đóng góp của file đó bị trừ khỏi `count`, các file khác vẫn còn. Test ở Task 1.
2. Ẩn mọi file trong một folder → folder biến khỏi bản đồ (không còn ô rỗng). Test ở Task 1.
3. Ẩn mục đang bị lọc bởi nút (doc khi `showDocs=false`) rồi bật nút → mục vẫn ẩn. Test ở Task 1.
4. Tìm theo tên không phân biệt hoa thường, khớp chuỗi con, ra cả folder cha để thấy đường dẫn. Test ở Task 1.
5. Click tên một file nằm sâu khi bản đồ đang thu gọn hết → mọi folder cha được mở, ô đó được cuộn tới và tô nổi. Kiểm tra thủ công ở Task 3.

---

### Task 1: Logic ẩn/hiện và dữ liệu cây (JS thuần)

**Files:** Modify `repomap/web/aggregate.js`, `tests/aggregate.test.mjs`

**Interfaces:**
- Consumes: `buildTree`, `visibleView` hiện có.
- Produces:
  - `state.hidden: Set<string>` (id file, dir như `"pkg/"`, `"ext:"` hoặc `"ext:<label>"`). `visibleView` coi một nút là không hiện nếu nó **hoặc bất kỳ tổ tiên nào** nằm trong `hidden`; vì `lift` trả `null` cho nút không hiện, mũi tên của nó tự bị bỏ. Thiếu `state.hidden` thì coi như rỗng.
  - `revealPath(tree, id) -> string[]` — id các folder/khung tổ tiên (không gồm gốc `""`), từ ngoài vào trong. Id không tồn tại → `[]`.
  - `treeRows(tree, state, treeOpen: Set<string>, query: string) -> Row[]`, `Row = {id, name, type, depth, hasChildren, open, check: "on"|"off"|"partial"}`, theo thứ tự duyệt cây, giữ đúng thứ tự `children` của `buildTree`.
    - Chỉ gồm nút được nút lọc cho phép (cùng quy tắc `shown` của `visibleView` **bỏ qua** `hidden`); dir/khung không còn con được phép thì bỏ.
    - `query` rỗng: con của nút chỉ xuất hiện khi nút nằm trong `treeOpen`; `open = treeOpen.has(id)`.
    - `query` khác rỗng: gồm nút có `name` chứa `query` (không phân biệt hoa thường) và mọi tổ tiên của chúng; bỏ qua `treeOpen`, `open = true` cho các tổ tiên đó.
    - `check`: lá → `"off"` nếu nó hoặc tổ tiên trong `hidden`, ngược lại `"on"`; dir/khung → `"off"` nếu chính nó hoặc tổ tiên trong `hidden`, `"on"` nếu không con cháu được phép nào bị ẩn, ngược lại `"partial"`.
    - `depth`: 0 cho con trực tiếp của gốc.
  - Thêm `revealPath`, `treeRows` vào `globalThis.RepoMap`.

- [ ] **Step 1: Viết test** (dùng `model`/`tree` sẵn có; sửa helper `S` thêm `hidden: new Set(o.hidden || [])`)

```js
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
```

- [ ] **Step 2:** `node --test tests/*.test.mjs` → FAIL (`revealPath`/`treeRows` chưa có, `hidden` chưa có hiệu lực).
- [ ] **Step 3:** Cài trong `aggregate.js`. Tách `allowed(n, state)` (quy tắc lọc theo nút, không xét `hidden`) và `isHidden(n, hidden)` (đi lên tổ tiên) để `visibleView` và `treeRows` dùng chung.
- [ ] **Step 4:** `node --test tests/*.test.mjs` → PASS (gồm 6 test cũ).
- [ ] **Step 5:** Commit `feat: hidden set and tree rows logic`.

---

### Task 2: Chữ giao diện sang tiếng Anh

**Files:** Modify `repomap/web/aggregate.js`, `repomap/web/template.html`, `repomap/web/app.js`, `README.md`, `tests/test_render.py`

**Interfaces:** Không đổi API. Chuỗi thay theo bảng ở mục 1 của `spec_v2.md` (`External`, `Test arrows`, `Collapse all`, `symbols`/`files`, `… N/M samples`, `N boxes, M arrows`, `Layout error:`, `This will show N items and may be slow. Continue?`); `<html lang="en">`; trong panel chi tiết `"N link: "` → `"N links: "`. README viết lại tiếng Anh với cùng nội dung, thêm mô tả panel cây (Task 3).

- [ ] **Step 1: Viết test** trong `tests/test_render.py`

```python
def test_ui_text_is_english(self):
    allowed = set("▸▾→…")
    for rel in ["repomap/web/aggregate.js", "repomap/web/app.js", "repomap/web/template.html", "README.md"]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        bad = sorted({ch for ch in text if ord(ch) > 127 and ch not in allowed})
        self.assertEqual(bad, [], rel)
```

  (`ROOT` = thư mục gốc repo, tính từ `Path(__file__).resolve().parents[1]`.)
- [ ] **Step 2:** `python3 -m unittest tests.test_render -v` → FAIL, liệt kê ký tự tiếng Việt.
- [ ] **Step 3:** Thay chuỗi theo bảng; sửa test JS nào so khớp `"Bên ngoài"` nếu có.
- [ ] **Step 4:** `python3 -m unittest discover tests -v && node --test tests/*.test.mjs` → PASS.
- [ ] **Step 5:** Commit `feat: English UI text`.

---

### Task 3: Panel cây bên trái

**Files:** Modify `repomap/web/template.html`, `repomap/web/app.js`, `README.md`

**Interfaces:**
- Consumes: `RepoMap.treeRows`, `RepoMap.revealPath`, `state.hidden` (Task 1).
- Produces: giao diện. Phần tử: `#side` (panel), `#side-toggle` (nút trên `#bar`, nhãn `Tree`), `#tree-search` (input, placeholder `Search files…`), `#show-all` (nút `Show all`), `#tree` (danh sách dòng).

Yêu cầu:
- Bố cục: `#side` cố định bên trái, rộng 280px, cuộn dọc riêng; `#map` chiếm phần còn lại. `#side-toggle` ẩn/hiện panel (bản đồ giãn ra toàn bộ khi ẩn). Mặc định panel **mở**. Màn hình hẹp (< 640px) mặc định đóng.
- `const treeOpen = new Set()` riêng cho cây. Vẽ `#tree` từ `treeRows(tree, state, treeOpen, query)`; mỗi dòng: thụt lề `depth * 14px`, nút `▸/▾` khi `hasChildren` (click → toggle `treeOpen`, vẽ lại cây), checkbox (`checked = check === "on"`, `indeterminate = check === "partial"`), tên.
- Checkbox: bỏ chọn → `state.hidden.add(id)`; chọn → `state.hidden.delete(id)` **và** xoá khỏi `hidden` mọi id con cháu của nó (để bật lại folder hiện lại toàn bộ). Sau đó `render()` bản đồ và vẽ lại cây. Không hỏi `tooBig` khi ẩn; khi hiện lại thì dùng `tooBig()` như các nút lọc, từ chối thì hoàn tác.
- Ô tìm: `input` → vẽ lại cây với `query` (trim).
- `Show all`: `state.hidden.clear()`, `render()`, vẽ lại cây.
- Thay đổi nút lọc (`Test arrows`, `Docs/config`, `External`) và `Collapse all` cũng vẽ lại cây.
- Click tên một dòng (không phải mục đang ẩn): thêm `revealPath(tree, id)` vào `state.expanded` (chỉ tổ tiên, không mở chính `id`), kiểm `tooBig()` (từ chối → hoàn tác), `render()`; sau khi vẽ xong, đặt `tx/ty` để tâm ô `data-id === id` nằm giữa `#map` (giữ `k`), và thêm class `focus` cho ô đó (viền đậm màu `--line`) tới lần vẽ sau. `render()` cần trả về Promise để chờ.
- Chữ tiếng Anh.

- [ ] **Step 1:** Cài panel trong `template.html` (HTML + CSS dùng token màu sẵn có, cả dark mode) và `app.js`.
- [ ] **Step 2:** `node --check repomap/web/app.js && python3 -m unittest discover tests && node --test tests/*.test.mjs` → tất cả PASS.
- [ ] **Step 3: Kiểm tra thực tế**
  Run: `python3 -m repomap ~/workspace/project/graphify/graphify-out/graph.json -o out/map.html`.
  Nếu không có trình duyệt: chạy headless trong Node (stub DOM tối thiểu hoặc chỉ gọi logic) để xác nhận: `treeRows` trên model thật cho cấp gốc = `graphify/ scripts/ tests/ tools/ worked/`; ẩn `graphify/extractors/resolution.py` làm biến mất mũi tên `graphify/extract.py → graphify/extractors/resolution.py` (116) khi mở `graphify/` + `extractors/`, và mũi tên `extract.py → extractors/` (khi `extractors/` thu gọn) giảm đúng 116 (378 → 262). Ghi rõ phần không xem được bằng mắt.
  Expected (khi người dùng mở trình duyệt): panel cây bên trái, nút `Tree` đóng/mở được; bỏ chọn file → ô và mũi tên biến mất; checkbox folder hiện trạng thái một phần; tìm `resolution` ra đường dẫn tới file; click tên file sâu → bản đồ mở tới và tô nổi ô.
- [ ] **Step 4:** Cập nhật README (mục panel cây). Commit `feat: tree side panel with show/hide`.

---

## Self-review

- Spec v2 §1 → Task 2 (bảng chuỗi + test chặn ký tự non-ASCII). §2 → không code. §3: panel thu gọn + cây mở rộng (T3), checkbox ẩn + mũi tên biến mất hẳn (T1 logic, T3 UI), ẩn folder (T1), trạng thái partial (T1 `check`, T3 `indeterminate`), cây độc lập bản đồ (T3 `treeOpen`), click → nhảy tới (T1 `revealPath`, T3), tìm (T1, T3), cây theo nút lọc (T1 `allowed`), không lưu + Show all (T3), đếm/cảnh báo sau khi ẩn (T1 `total`, T3 `tooBig`), tiếng Anh (T2, T3).
- Tên nhất quán: `state.hidden`, `revealPath`, `treeRows`, `treeOpen`, `allowed`, `isHidden`, `tooBig`, `MAX_VISIBLE`.
