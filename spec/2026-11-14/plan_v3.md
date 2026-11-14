# Repo Map v3 Implementation Plan (plan v3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** File mở rộng được ngay trên bản đồ để thấy hàm/class (class mở tiếp thấy method); mũi tên `calls` gắn vào hàm, gộp lên file/class khi thu gọn.

**Architecture:** Python thêm `symbols` vào model và cho đầu mút cạnh `calls` là id ký hiệu (cạnh import vẫn là file). JS coi file/class có con là "container" như folder: cùng `buildTree` → `visibleView` (nâng/gộp mũi tên) → `treeRows`. `app.js` chỉ thêm nhãn, click và kiểu vẽ.

**Tech Stack:** như v2 — Python 3.10 stdlib + `unittest`, JS thuần, ELK.js 0.9.3 inline, Node 24 (`node --test tests/*.test.mjs`).

**Spec:** `spec/2026-11-14/spec_v3.md` (kế thừa `spec_v1.md`, `spec_v2.md`).

## Global Constraints

- Ký hiệu = node `file_type == "code"` có `source_file`, **có cạnh đến** `contains` hoặc `method` từ một node **cùng `source_file`**. Cha = node nguồn của cạnh đó (node file → cha là file; node ký hiệu → cha là ký hiệu đó, tức class). Node `rationale`/`document` không bao giờ là ký hiệu.
- Node code không thoả điều kiện trên (node đại diện file, `__init__.py`, ký hiệu không có cha) → đầu mút là **file** của nó (như v2). *(Quyết định của plan: spec nói "gắn thẳng vào file"; phân biệt node-file với ký hiệu-mồ-côi không có trường riêng nên gộp cả hai về file.)*
- id ký hiệu trên bản đồ: `"sym:" + <id node graphify>` (không trùng path/`ext:`).
- Mũi tên: `calls`, `imports`, `imports_from` (không `indirect_call`). Đầu mút `calls` dùng ký hiệu nếu có; `imports*` luôn dùng file.
- Bỏ cạnh có hai đầu mút trùng nhau **sau khi** quy về đầu mút (ký hiệu hoặc file). Cạnh giữa hai ký hiệu cùng file được giữ (thấy khi mở file).
- Bất biến: khi mọi file thu gọn, mũi tên và `count` giống hệt v2.
- Mặc định file và class **thu gọn**; mở/thu dùng chung `state.expanded`.
- Ký hiệu thừa hưởng `kind` (code/test/doc) và luật lọc nút của file chứa nó.
- Chữ giao diện tiếng Anh. Repo mẫu `~/workspace/project/tests/repomap-test` không dùng git.

## Review Focus

1. Ẩn mọi hàm của một file → file vẫn hiện (còn code cấp module và import), chỉ mất mũi tên của các hàm đó. Test ở Task 2.
2. Mũi tên từ code cấp module (nguồn là node file) tới một hàm → khi mở file đích, gắn vào hàm đích, đầu nguồn vẫn là khung file. Test ở Task 2.
3. Hàm test gọi hàm code với `showTests=false` → không có mũi tên dù file test đang mở. Test ở Task 2.
4. Method của class thu gọn → mũi tên gộp lên ô class, không lên file. Test ở Task 2.
5. File không có ký hiệu (ví dụ `__init__.py`) → không có `▸`, click không làm gì. Kiểm tra ở Task 3.

---

### Task 1: Model cấp ký hiệu (Python)

**Files:** Modify `repomap/model.py`, `tests/test_model.py`; Create `tests/fixtures/sym_graph.json`

**Interfaces:**
- Consumes: `load_graph` (không đổi).
- Produces: `build_model(nodes, links)` trả thêm khoá:
  `"symbols": [{"id": "sym:<nid>", "name": <label>, "file": <source_file>, "parent": <file path | "sym:<nid> của class">, "kind": "class"|"func", "loc": <source_location hoặc "">}]`, sắp theo (`file`, `loc` số dòng, `name`).
  `kind = "class"` nếu node có ít nhất một cạnh `method` đi ra hoặc `_callable_class` truthy; ngược lại `"func"`.
  `edges[*].src/tgt` có thể là `"sym:<nid>"`. Khoá `files`, `external`, cấu trúc edge giữ nguyên.

Fixture `sym_graph.json` (repo nhỏ, có class):
- Node: `fa` (label `a.py`, `pkg/a.py`, code, L1); `run` (`run()`, `pkg/a.py`, code, L3); `K` (`K`, `pkg/a.py`, code, L6, `_callable_class: true`); `km` (`.go()`, `pkg/a.py`, code, L7); `doc` (`"""doc"""`, `pkg/a.py`, `file_type: rationale`, L4); `fb` (`b.py`, `pkg/b.py`, code, L1); `g` (`g()`, `pkg/b.py`, code, L2); `ti` (`__init__.py`, `pkg/__init__.py`, code); `ft` (`test_a.py`, `tests/test_a.py`, code); `t1` (`test_run()`, `tests/test_a.py`, code, L2).
- Link: `fa→run contains`; `fa→K contains`; `K→km method`; `fa→doc contains` (node rationale bị loại dù có contains); `doc→run rationale_for`; `fb→g contains`; `ft→t1 contains`; `run→g calls`; `km→g calls`; `run→km calls`; `fa→fb imports_from`; `fa→g calls` (cấp module); `run→g indirect_call`; `t1→run calls`.

- [ ] **Step 1: Viết test** (`tests/test_model.py`, class mới `TestSymbols`)

```python
def ms(): return build_model(*load_graph(SYM))
class TestSymbols(unittest.TestCase):
    def test_symbols(self):
        s = {x["id"]: x for x in ms()["symbols"]}
        self.assertEqual(set(s), {"sym:run", "sym:K", "sym:km", "sym:g", "sym:t1"})
        self.assertEqual(s["sym:km"]["parent"], "sym:K")
        self.assertEqual(s["sym:run"]["parent"], "pkg/a.py")
        self.assertEqual((s["sym:K"]["kind"], s["sym:run"]["kind"]), ("class", "func"))
        self.assertEqual(s["sym:run"]["loc"], "L3")
    def test_endpoints(self):
        e = {(x["src"], x["tgt"]): x for x in ms()["edges"]}
        self.assertIn(("sym:run", "sym:g"), e)
        self.assertEqual(e[("sym:run", "sym:g")]["by_rel"], {"calls": 1})      # indirect_call bỏ
        self.assertIn(("sym:km", "sym:g"), e)
        self.assertIn(("sym:run", "sym:km"), e)                                # cùng file, khác ký hiệu
        self.assertIn(("pkg/a.py", "pkg/b.py"), e)                             # import ở cấp file
        self.assertIn(("pkg/a.py", "sym:g"), e)                                # cấp module → hàm
    def test_v1_fixture_unchanged(self):
        self.assertEqual(m()["symbols"], [])   # mini_graph không có contains cùng file
```

- [ ] **Step 2:** `python3 -m unittest tests.test_model -v` → FAIL.
- [ ] **Step 3:** Cài trong `model.py`: tính map `nid → cha` từ link `contains`/`method` cùng `source_file` (bỏ node không phải `code`); `end(nid, rel)` trả `"sym:"+nid` nếu `rel == "calls"` và nid là ký hiệu, ngược lại file/`ext:` như cũ.
- [ ] **Step 4:** `python3 -m unittest discover tests -v` → PASS (cả test cũ).
- [ ] **Step 5:** Commit `feat: symbol-level model` (kèm `spec/2026-11-14/plan_v3.md`).

---

### Task 2: Cây và logic gộp cấp ký hiệu (JS thuần)

**Files:** Modify `repomap/web/aggregate.js`, `tests/aggregate.test.mjs`

**Interfaces:**
- Consumes: model có `symbols` (Task 1). Thiếu `symbols` → coi là `[]`.
- Produces (giữ tên hàm, mở rộng hành vi):
  - `buildTree`: thêm nút `{id, name, type: "class"|"func", kind: <kind của file>, loc, children}` dưới cha (`parent`), giữ thứ tự `symbols`.
  - **Container** = `dir`, `extroot`, `file` có con, `class` có con. Box của container có `collapsed` và `fileCount` như cũ; thêm `childCount` = số con trực tiếp đang hiện (dùng cho nhãn file/class).
  - **Lọc nút**: ký hiệu theo luật của file chứa nó (`allowedLeaf` của file tổ tiên).
  - **Hiện**: file hiện nếu được phép và không ẩn (không phụ thuộc ký hiệu con); ký hiệu hiện nếu file được phép và nó/tổ tiên không ẩn; dir/extroot hiện nếu còn ít nhất một file/ext hiện. `fileCount` vẫn đếm file (hoặc ký hiệu ngoài với extroot).
  - `showTests=false` bỏ cạnh có đầu nguồn `kind === "test"` (ký hiệu thừa hưởng kind).
  - `treeRows`: file/class có con → `hasChildren: true`; tìm theo tên khớp cả ký hiệu; `check` tính trên các nút lá (nút không có con được phép) — file có ký hiệu là container trong cây.
  - `revealPath`, `unhide` hoạt động nguyên trạng với cấp mới.

- [ ] **Step 1: Viết test** (model viết tay theo `sym_graph.json` sau `build_model`, trong một `describe`/nhóm riêng)

```js
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
```

- [ ] **Step 2:** `node --test tests/*.test.mjs` → FAIL (test mới).
- [ ] **Step 3:** Cài trong `aggregate.js`. Thay `isLeaf`/`container` cứng theo type bằng: container = có con (với `dir`/`extroot` theo type như cũ); giữ một hàm `fileOf(n)` (đi lên tới nút `file`) cho luật lọc và `kind`.
- [ ] **Step 4:** `node --test tests/*.test.mjs` → PASS (gồm 17 test cũ).
- [ ] **Step 5:** Commit `feat: symbol containers in tree and aggregation`.

---

### Task 3: Giao diện, repo mẫu, kiểm tra thực tế

**Files:** Modify `repomap/web/app.js`, `repomap/web/template.html`, `README.md`; ngoài repo: `~/workspace/project/tests/repomap-test/` (không git)

**Interfaces:**
- Consumes: box có `type` `file|class|func`, `collapsed`, `childCount` (Task 2); nút cây có `loc`.

Yêu cầu:
- Nhãn: file thu gọn có con `▸ a.py (N symbols)`, mở `▾ a.py`; class thu gọn `▸ K (N methods)`, mở `▾ K`; hàm/method: tên như graphify ghi. File không con: tên như cũ, không `▸`.
- Click file/class có con → `toggle(id)` (cùng `tooBig()`); file không con không làm gì.
- `toElk`: container mở = mọi box có `collapsed === false` (không chỉ dir/extroot).
- Kiểu vẽ: khung file mở viền liền mảnh (phân biệt khung folder nét đứt); khung class viền chấm; ô hàm/method góc bo nhiều hơn. Dùng token màu sẵn có, cả dark mode.
- Tooltip `<title>` và panel chi tiết: thêm `file:loc` cho ký hiệu.
- Panel cây: thụt lề/biểu tượng cho class/func; click tên ký hiệu → mở mọi tổ tiên (gồm file, class) rồi nhảy tới.
- README: mục "Expanding files".
- Repo mẫu: thêm `app/models.py` với `class User` có method `display(self)` gọi `log` từ `app.utils`, và `app/services/user.py` dùng `User(...).display()` trong `get_user`. Chạy `graphify update .` trong repo mẫu, tạo lại `repomap.html`, cập nhật `EXPECTED.md` bằng mục "Cấp hàm" (đếm tay từ code; ví dụ `run() → create_user()` = 1, `create_user() → save()` = 1, method `display()` → `log()`), ghi rõ những gì graphify **không** bắt được (ví dụ lời gọi qua instance) nếu kết quả khác đếm tay.

- [ ] **Step 1:** Cài UI.
- [ ] **Step 2:** `node --check repomap/web/app.js && python3 -m unittest discover tests && node --test tests/*.test.mjs` → PASS.
- [ ] **Step 3: Kiểm tra thực tế**
  - Repo mẫu: cập nhật code, `graphify update .`, `python3 -m repomap <repo mẫu>/graphify-out/graph.json -o <repo mẫu>/repomap.html`. Chạy `visibleView` trong Node trên model thật: các trường hợp trong `EXPECTED.md` khớp (cấp file như cũ; mở `app/`, `app/main.py`, `app/services/`, `app/services/user.py` → `sym:…run… → sym:…create_user…` = 1).
  - Bất biến trên repo graphify (chỉ đọc, **không** cần ghi bản đồ): build model từ `~/workspace/project/graphify/graphify-out/graph.json`, `visibleView` với `expanded = {"graphify/","graphify/extractors/"}` → `graphify/extract.py → graphify/extractors/resolution.py` vẫn = 116, `graphify/extract.py → …` các số khác không đổi so với v2.
  - Ghi rõ phần không xem được bằng mắt (không có trình duyệt).
- [ ] **Step 4:** Commit `feat: expand files to symbols in the UI`.

---

## Self-review

- Spec v3 §2 mục tiêu: mở file (T2 container, T3 click), class ⊃ method (T1 `method`, T2), mũi tên vào hàm và gộp (T1 endpoints, T2), panel cây cấp hàm + tìm + nhảy tới (T2 `treeRows`/`revealPath`, T3). §5: lọc node rationale/document (T1 Global Constraints + fixture `doc`), imports ở file (T1), cấp module (T1, T2 Focus 2), bất biến số cấp file (T2 test 1, T3 real-data), nhãn + `loc` (T3), file rỗng không mở (T2 `hasChildren`, T3), cảnh báo 400 (T3 `tooBig`), id ổn định (Global Constraints). §6: không `indirect_call` (T1 test), class thu gọn (T2 test 2). §7: repo mẫu có class (T3).
- Tên nhất quán: `symbols`, `sym:`, `childCount`, `fileOf`, `toggle`, `tooBig`.
