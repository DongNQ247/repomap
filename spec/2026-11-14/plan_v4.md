# Repo Map v4 Implementation Plan (plan v4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đóng gói repomap 1.0.0 thành CLI cài bằng `uv tool install git+…`, gõ `repomap` là tạo `map.html` cạnh `graphify-out/graph.json`, với thông báo terminal theo spec.

**Architecture:** Thêm `pyproject.toml` (backend `uv_build`, module ở gốc repo) + `LICENSE`. Viết lại `repomap/__main__.py`: tìm `graph.json`, gọi `load_graph`/`build_model`/`render_html` như cũ, in kết quả qua vài hàm định dạng nhỏ (màu chỉ khi là terminal và không có `NO_COLOR`). Không đổi bản đồ HTML.

**Tech Stack:** Python ≥3.10 stdlib (`argparse`, `importlib.metadata`, `json`), `uv_build`, uv 0.12, `unittest`.

**Spec:** `spec/2026-11-14/spec_v4.md`

## Global Constraints

- `name = "repomap"`, `version = "1.0.0"`, `requires-python = ">=3.10"`, không dependency, `license = "MIT"`, entry point `repomap = "repomap.__main__:main"`.
- Phiên bản chỉ ghi trong `pyproject.toml`; code đọc bằng `importlib.metadata.version("repomap")`.
- Gói phải chứa `repomap/web/` đầy đủ (gồm `vendor/elk.bundled.js`).
- Mặc định đọc `./graphify-out/graph.json`; ghi `map.html` cùng thư mục với `graph.json` đã đọc; ghi đè không hỏi; không mở trình duyệt.
- Mã thoát: 0 thành công; 1 lỗi đọc/ghi/dữ liệu; 2 tham số sai.
- Màu và ký tự `✓ ·` chỉ khi stream là TTY và không đặt `NO_COLOR`; ngược lại ASCII (`OK`, `-`).
- Chữ người dùng thấy bằng tiếng Anh. Không push, không tạo remote, không gắn tag trên remote.
- Repo mẫu `~/workspace/project/tests/repomap-test` không dùng git.

## Review Focus

1. Chạy `repomap` trong thư mục con của project (không có `graphify-out/` tại chỗ) → báo lỗi thiếu file kèm hướng dẫn, không traceback. Test ở Task 2.
2. `graph.json` là JSON hợp lệ nhưng không phải của graphify (ví dụ `[]` hoặc `{}`) → lỗi một dòng "does not look like a graphify graph.json", mã 1. Test ở Task 2.
3. Đường dẫn có khoảng trắng → vẫn chạy, dòng `file://` được mã hoá đúng (`Path.as_uri()`). Test ở Task 2.
4. Thư mục đích không ghi được (`-o` vào thư mục chỉ đọc) → lỗi "cannot write …", mã 1. Test ở Task 2.
5. Gói cài từ wheel thiếu `web/` → `repomap` lỗi khi render. Kiểm tra ở Task 1 (liệt kê file trong wheel) và Task 3 (cài thật).

---

### Task 1: pyproject, LICENSE, `--version`

**Files:** Create `pyproject.toml`, `LICENSE`; Modify `repomap/__main__.py` (chỉ thêm `--version`), `.gitignore` (thêm `dist/`, `.venv/`); Test `tests/test_cli.py` (mới)

**Interfaces:**
- Produces: `pyproject.toml` theo Global Constraints, thêm:
  ```toml
  [build-system]
  requires = ["uv_build>=0.12,<0.13"]
  build-backend = "uv_build"

  [tool.uv.build-backend]
  module-root = ""
  ```
  `description = "Render graphify's graph.json as an interactive nested file/folder call map"`, `readme = "README.md"`.
- Produces: `repomap.__main__.VERSION: str` = `importlib.metadata.version("repomap")`, fallback `"0+unknown"` khi chưa cài (`PackageNotFoundError`).
- `LICENSE`: văn bản MIT chuẩn, `Copyright (c) 2026 DongNQ225284`.
- Từ task này, chạy test bằng `uv run python -m unittest discover tests` (uv cài project dạng editable nên có metadata).

- [ ] **Step 1: Viết test** (`tests/test_cli.py`; helper `run(args, cwd, env=None)` gọi `[sys.executable, "-m", "repomap", *args]` qua `subprocess.run(..., capture_output=True, text=True)`)

```python
def test_version(self):
    r = run(["--version"], cwd=ROOT)
    self.assertEqual(r.returncode, 0)
    self.assertEqual(r.stdout.strip(), "repomap 1.0.0")
```

- [ ] **Step 2:** `uv run python -m unittest tests.test_cli -v` → FAIL (chưa có `pyproject.toml` / `--version`).
- [ ] **Step 3:** Tạo `pyproject.toml`, `LICENSE`, thêm `ap.add_argument("--version", action="version", version=f"repomap {VERSION}")`.
- [ ] **Step 4:** `uv run python -m unittest discover tests -v` → PASS (cả test cũ).
- [ ] **Step 5:** `uv build` → tạo `dist/repomap-1.0.0-py3-none-any.whl` và `.tar.gz`. Kiểm tra: `python3 -m zipfile -l dist/repomap-1.0.0-py3-none-any.whl` có `repomap/web/template.html`, `repomap/web/app.js`, `repomap/web/aggregate.js`, `repomap/web/vendor/elk.bundled.js`, và **không** có `tests/`, `spec/`, `out/`.
- [ ] **Step 6:** Commit `build: package as repomap 1.0.0 with uv_build` (kèm `spec/2026-11-14/spec_v4.md`, `spec/2026-11-14/plan_v4.md` nếu chưa commit; không commit `dist/`, `uv.lock` có thể commit).

---

### Task 2: Trải nghiệm terminal

**Files:** Modify `repomap/__main__.py`, `tests/test_cli.py`, `tests/test_render.py` (sửa `test_cli` cũ theo tên `map.html`)

**Interfaces:**
- Consumes: `load_graph`, `build_model`, `render_html` (không đổi), `VERSION` (Task 1).
- Produces (trong `__main__.py`):
  - `find_graph(arg: Path | None, cwd: Path) -> Path` — `None` → `cwd/"graphify-out"/"graph.json"`; `arg` là thư mục → `arg/graphify-out/graph.json` nếu có, ngược lại `arg/graph.json`; `arg` là file → chính nó. Trả về đường dẫn dự kiến (có thể không tồn tại); `main` kiểm tra tồn tại.
  - `main(argv: list[str] | None = None) -> int`. Tham số: `graph` (tuỳ chọn, `nargs="?"`), `-o/--out`, `-q/--quiet`, `--version`.
  - `style(stream) -> bool` — `stream.isatty()` và `"NO_COLOR" not in os.environ`.
- Thông báo — chữ chính xác (thay `<…>` bằng giá trị; `·`/`✓` khi `style`, ngược lại `-`/`OK`):
  - Thành công (stdout):
    ```
    repomap <VERSION> · reading <graph rel>
      <files> files · <symbols> symbols · <arrows> arrows
    ✓ wrote <out rel> (<size>)
      open it in your browser: <out.resolve().as_uri()>
    ```
    `files = len(model["files"])`, `symbols = len(model.get("symbols", []))`, `arrows = len(model["edges"])`, số có dấu phẩy nghìn (`f"{n:,}"`). `<size>`: `"3.5 MB"` (≥1 MB, 1 chữ số thập phân) hoặc `"812 KB"`. `rel` = tương đối so với `cwd` nếu nằm trong, ngược lại tuyệt đối.
  - `--quiet`: chỉ `str(out.resolve())`.
  - Thiếu file (stderr, mã 1), đúng nguyên văn spec §5 (dòng đầu `repomap: error: <graph rel> not found in <cwd tuyệt đối>` khi không tham số; `repomap: error: <arg> not found` khi có tham số), sau đó khối hướng dẫn 5 dòng của spec.
  - JSON hỏng: `repomap: error: <graph rel> is not valid JSON: <msg>`; sai định dạng (không phải dict có `nodes` là list): `repomap: error: <graph rel> does not look like a graphify graph.json (no nodes/links)`; ghi lỗi: `repomap: error: cannot write <out rel>: <strerror>`. Mỗi lỗi một dòng, mã 1. Khi `style(stderr)`, chữ `error:` màu đỏ (`\033[31m…\033[0m`); `✓` màu xanh (`\033[32m`).

- [ ] **Step 1: Viết test** (`tests/test_cli.py`; `SAMPLE` = bản sao `tests/fixtures/sym_graph.json` đặt vào `tmp/graphify-out/graph.json`; subprocess không phải TTY nên chữ trơn)

```python
def test_default_finds_graphify_out(self):
    r = run([], cwd=proj)
    self.assertEqual(r.returncode, 0, r.stderr)
    self.assertTrue((proj / "graphify-out" / "map.html").exists())
    self.assertIn("repomap 1.0.0 - reading graphify-out/graph.json", r.stdout)
    self.assertRegex(r.stdout, r"\d+ files - \d+ symbols - \d+ arrows")
    self.assertIn("OK wrote graphify-out/map.html (", r.stdout)
    self.assertIn("file://", r.stdout)
    self.assertNotIn("\033[", r.stdout)
def test_missing_graph_gives_guide(self):          # Focus 1
    r = run([], cwd=empty_dir)
    self.assertEqual(r.returncode, 1)
    self.assertIn("graphify-out/graph.json not found in", r.stderr)
    self.assertIn("uv tool install graphifyy", r.stderr)
    self.assertIn("graphify update .", r.stderr)
    self.assertNotIn("Traceback", r.stderr)
def test_path_dir_and_file(self):
    self.assertEqual(run([str(proj)], cwd=elsewhere).returncode, 0)
    self.assertEqual(run([str(proj / "graphify-out" / "graph.json")], cwd=elsewhere).returncode, 0)
    r = run(["nope.json"], cwd=elsewhere)
    self.assertEqual(r.returncode, 1); self.assertIn("repomap: error: nope.json not found", r.stderr)
def test_bad_json_and_wrong_shape(self):          # Focus 2
    for text, msg in [("{oops", "is not valid JSON"), ("[]", "does not look like a graphify graph.json"), ("{}", "does not look like a graphify graph.json")]:
        # ghi text vào graphify-out/graph.json của một tmp project
        r = run([], cwd=bad_proj)
        self.assertEqual(r.returncode, 1); self.assertIn(msg, r.stderr); self.assertNotIn("Traceback", r.stderr)
def test_quiet(self):
    r = run(["-q"], cwd=proj)
    self.assertEqual(r.stdout.strip(), str((proj / "graphify-out" / "map.html").resolve()))
def test_space_in_path(self):                      # Focus 3
    r = run([], cwd=proj_with_space)               # tmp/"my project"
    self.assertEqual(r.returncode, 0); self.assertIn("my%20project", r.stdout)
def test_unwritable_out(self):                     # Focus 4
    r = run(["-o", str(readonly_dir / "map.html")], cwd=proj)   # os.chmod(readonly_dir, 0o500); bỏ qua nếu chạy root
    self.assertEqual(r.returncode, 1); self.assertIn("cannot write", r.stderr)
def test_bad_args_exit_2(self):
    self.assertEqual(run(["--nope"], cwd=proj).returncode, 2)
```

- [ ] **Step 2:** `uv run python -m unittest tests.test_cli -v` → FAIL.
- [ ] **Step 3:** Cài trong `__main__.py`. Kiểm tra dạng dữ liệu trước khi gọi `load_graph` (đọc JSON một lần; `load_graph` có thể nhận đường dẫn như cũ — chấp nhận đọc hai lần cho đơn giản, hoặc tách `load_graph_data(dict)` nếu gọn hơn). Sửa `tests/test_render.py::test_cli` cho đúng hành vi mới (mặc định `map.html`).
- [ ] **Step 4:** `uv run python -m unittest discover tests -v && node --test tests/*.test.mjs` → PASS.
- [ ] **Step 5:** Commit `feat(cli): default graphify-out lookup, map.html output, friendly messages`.

---

### Task 3: README và cài thật

**Files:** Modify `README.md`

Yêu cầu README (tiếng Anh, theo spec §4): mục **Install** (`uv tool install git+https://github.com/<owner>/repomap` và dạng ghim `…/repomap@v1.0.0`; `uv tool upgrade repomap`; gỡ `uv tool uninstall repomap`), **Requirements** (Python ≥3.10, graphify: `uv tool install graphifyy` rồi `graphify update .`), **Usage** (`repomap` trong project → `graphify-out/map.html`; `repomap PATH`; `-o`; `-q`; `--version`; mô tả lỗi khi thiếu `graph.json`), giữ các mục dùng bản đồ hiện có, mục **License: MIT**. Giữ `<owner>` làm chỗ trống, ghi chú cần thay khi có URL.

- [ ] **Step 1:** Viết README. `uv run python -m unittest tests.test_render` → PASS (`test_ui_text_is_english` vẫn đúng).
- [ ] **Step 2: Cài thật trong môi trường tách biệt**
  ```bash
  uv build
  uv tool install --force dist/repomap-1.0.0-py3-none-any.whl
  repomap --version                       # → repomap 1.0.0
  cd ~/workspace/project/tests/repomap-test && repomap   # → tạo graphify-out/map.html
  cd /tmp && repomap; echo $?             # → thông báo hướng dẫn, mã 1
  uv tool uninstall repomap
  ```
  Kiểm tra thêm `map.html` vừa tạo chứa ELK (chuỗi `ELK` xuất hiện, không có `src="http`). Nếu có thể, thử `uv tool install --force git+file://<đường dẫn repo>` sau khi commit để mô phỏng cài từ git, rồi gỡ.
- [ ] **Step 3:** Commit `docs: install and usage for repomap 1.0.0`. Gắn tag cục bộ `git tag v1.0.0` (không push).

---

## Self-review

- Spec §2 mục tiêu: cài từ git (T3 README + thử `git+file://`), MIT (T1), 1.0.0 ở pyproject/`--version`/tag (T1, T3), `map.html` (T2). §4: pyproject đủ trường, `web/` trong wheel (T1 Step 5), version từ metadata (T1), README (T3). §5: mặc định/PATH/thư mục (T2 `find_graph`), ghi đè (T2 hành vi mặc định của `write_text`), thông báo thành công/thiếu file/lỗi khác (T2), mã thoát (T2), màu/ASCII (T2 `style` + test không có `\033[`), `--quiet` (T2). §6 kiểm tra (T2, T3). §7 không push (Global Constraints, tag cục bộ).
- Tên nhất quán: `VERSION`, `find_graph`, `style`, `main`.
