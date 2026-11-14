# Repo Map — spec v4: đóng gói CLI (uv, git) và trải nghiệm terminal

Ngày: 2026-11-14 · Trạng thái: chờ duyệt · Kế thừa: `spec_v1.md` … `spec_v3.md` (mọi điểm không nhắc ở đây giữ nguyên)

## 1. Ý định

Biến repomap thành một CLI **ai cũng cài được bằng uv từ git**, phiên bản **1.0.0**. Gõ `repomap` trong project đã chạy graphify là có ngay `map.html` cạnh `graph.json`.

## 2. Mục tiêu / Không phải mục tiêu

**Mục tiêu**
- Cài: `uv tool install git+https://github.com/<owner>/repomap` (bản mới nhất) hoặc `…/repomap@v1.0.0` (đúng bản). Sau đó lệnh `repomap` dùng được ở mọi nơi.
- Repo công khai, license **MIT**.
- Phiên bản **1.0.0**: trong `pyproject.toml`, `repomap --version`, tag git `v1.0.0`.
- Đầu ra mặc định đổi tên: **`map.html` cạnh `graph.json`** (trước đây `repomap.html`).

**Không phải mục tiêu**
- Đăng lên PyPI.
- Tự mở trình duyệt (người dùng chọn: chỉ in đường dẫn).
- Thay đổi gì ở bản đồ HTML.

## 3. Các cách đã cân nhắc (công cụ build)

| Cách | Đánh đổi |
|---|---|
| **1. `uv_build` (đã chọn)** | Hợp với uv, cấu hình ngắn nhất, tự kèm file trong package (gồm `web/`); còn mới |
| 2. `hatchling` | Phổ biến, ổn định, tự kèm file trong package; thêm một công cụ bên cạnh uv |
| 3. `setuptools` | Phải khai `package-data` cho `web/`, dễ quên → gói thiếu template; không dùng |

## 4. Đóng gói — đã quyết

- `pyproject.toml`: `name = "repomap"`, `version = "1.0.0"`, `requires-python = ">=3.10"`, **không dependency**, `license = "MIT"`, build backend `uv_build`, entry point `repomap = "repomap.__main__:main"`.
- Gói phải chứa toàn bộ `repomap/web/` (`template.html`, `aggregate.js`, `app.js`, `vendor/elk.bundled.js`).
- File `LICENSE` (MIT), chủ sở hữu theo tên git của người dùng.
- `repomap --version` in `repomap 1.0.0`; phiên bản đọc từ metadata gói (`importlib.metadata`), không lặp số ở nhiều nơi. *(Claude quyết)*
- README (tiếng Anh): cài đặt bằng uv từ git (cả dạng ghim `@v1.0.0`), yêu cầu có graphify (`uv tool install graphifyy`, `graphify update .`), cách dùng mặc định, `-o`, `--quiet`, `--version`, phần dùng bản đồ hiện có giữ nguyên.

## 5. Trải nghiệm terminal — đã quyết

**Cách gọi**
- `repomap` (không tham số) → đọc `./graphify-out/graph.json` trong thư mục hiện tại.
- `repomap PATH` → đọc `PATH` (file `graph.json`). *(Claude quyết: nếu `PATH` là thư mục thì tìm `PATH/graphify-out/graph.json`, rồi `PATH/graph.json`.)*
- Đầu ra mặc định: `map.html` cùng thư mục với `graph.json` đã đọc. `-o FILE` ghi nơi khác.
- Ghi đè `map.html` có sẵn, không hỏi.
- Không tự mở trình duyệt.

**Khi thành công** (stdout):
```
repomap 1.0.0 · reading graphify-out/graph.json
  1,129 files · 12,409 symbols · 23,114 arrows
✓ wrote graphify-out/map.html (3.5 MB)
  open it in your browser: file:///…/graphify-out/map.html
```
- Đường dẫn hiển thị tương đối so với thư mục hiện tại nếu nằm trong nó, ngược lại tuyệt đối; dòng `file://` luôn tuyệt đối.
- "arrows" = số cạnh trong model (cấp ký hiệu/file trước khi gộp).

**Khi thiếu `graph.json`** (stderr, mã thoát 1):
```
repomap: error: graphify-out/graph.json not found in /…/myproject

repomap draws a map from graphify's output. To create it:
  1. install graphify:   uv tool install graphifyy
  2. build the graph:    graphify update .
  3. run again:          repomap
Or pass a path:          repomap path/to/graph.json
```
Khi người dùng đưa `PATH` mà không tồn tại: cùng thông báo, dòng đầu nêu đúng `PATH`.

**Lỗi khác** (stderr, một dòng, không traceback, mã thoát 1): JSON hỏng (`… is not valid JSON: <lý do>`), sai định dạng (`… does not look like a graphify graph.json (no nodes/links)`), không ghi được file (`cannot write …: <lý do>`).

**Mã thoát**: 0 thành công; 1 lỗi đọc/ghi/dữ liệu; 2 tham số sai (mặc định argparse).

**Màu và ký hiệu**: màu (✓ xanh, `error:` đỏ) và ký tự `✓ ·` chỉ khi stream là terminal thật và không đặt biến `NO_COLOR`; ngược lại chữ trơn ASCII (`OK wrote …`, `-`). *(Claude quyết thay thế ASCII)*

**`--quiet` / `-q`**: chỉ in một dòng đường dẫn tuyệt đối của file đã ghi (cho script); lỗi vẫn in ra stderr.

## 6. Kiểm tra (cho builder)

- Test `unittest` cho CLI: không tham số trong thư mục có/không có `graphify-out/graph.json`; `PATH` file/thư mục/không tồn tại; JSON hỏng; `--quiet`; `--version`; mã thoát; không màu khi không phải terminal.
- Build và cài thật: `uv build`, rồi `uv tool install` từ thư mục repo (hoặc từ wheel) vào môi trường sạch; chạy `repomap` trong `~/workspace/project/tests/repomap-test` → `graphify-out/map.html` được tạo, mở offline được (đủ ELK). Gỡ tool sau khi thử.
- Repo mẫu không dùng git.

## 7. Để người dùng làm

- Tạo remote GitHub, push, và gắn tag `v1.0.0` (Claude chỉ chuẩn bị; không push khi chưa được yêu cầu). URL thật thay cho `<owner>` trong README khi biết.
