# Repo Map — spec v3: mở file để thấy hàm/class bên trong

Ngày: 2026-11-14 · Trạng thái: đã duyệt · Kế thừa: `spec_v1.md`, `spec_v2.md` (mọi điểm không nhắc ở đây giữ nguyên)

## 1. Ý định và lý do

Hiện đơn vị nhỏ nhất trên bản đồ là **file**. Một trong các câu hỏi gốc khi review là "**function này** được những file nào gọi?" — bản đồ cấp file không trả lời được. `graph.json` đã có sẵn dữ liệu cấp hàm: mỗi hàm/class/method là một node (có `source_file`, `source_location`), cạnh `calls` nối **hàm → hàm**.

v3: **file mở rộng được ngay trên bản đồ** để thấy các thành phần bên trong và mũi tên giữa chúng.

## 2. Mục tiêu / Không phải mục tiêu

**Mục tiêu**
- Click một file → file mở ra như một khung, bên trong là các ô hàm/class; class mở được tiếp để thấy method (file ⊃ class ⊃ method).
- Mũi tên `calls` gắn vào đúng hàm khi hàm đang hiển thị; khi file/class thu gọn thì gộp lên ô gần nhất đang hiển thị — **cùng cơ chế gộp hiện có**.
- Panel cây bên trái có thêm cấp hàm/class/method; ẩn/hiện, tìm, click-để-nhảy-tới áp dụng cho cả hàm.

**Không phải mục tiêu**
- Bảng "gọi ai / được ai gọi" kiểu danh sách thay cho bản đồ (đã cân nhắc, người dùng chọn mở trên bản đồ).
- Hiển thị biến, hằng, tham số, docstring.
- Chạy lại phân tích; vẫn chỉ đọc `graph.json`.

## 3. Các cách đã cân nhắc

| Cách | Đánh đổi |
|---|---|
| **A. Mở file trên bản đồ (đã chọn)** | Nhất quán với mở/thu folder, thấy mũi tên hàm→hàm; bản đồ nặng hơn khi mở file lớn |
| B. Panel danh sách hàm khi click file | Ít việc, không làm nặng bản đồ; không thấy mũi tên giữa hàm |

## 4. Những gì đã quyết

- Người dùng chọn cách A.
- Mặc định mọi file **thu gọn** — bản đồ ban đầu giống v2.
- Logic gộp/ẩn/hiện/đếm/cảnh báo 400 mục dùng chung cho cấp hàm (cây chỉ sâu thêm).

## 5. Đề xuất của Claude (người dùng đã đồng ý)

**Dữ liệu (từ khảo sát `graph.json`)**
- Thành phần bên trong file = node `file_type: "code"` có `source_file` đó, **trừ node đại diện chính file** (node gốc mà các cạnh `contains` đi ra). Bỏ node `rationale` (docstring/comment) và node `document` (mục markdown).
- Quan hệ cha–con: `contains` (file → hàm/class), `method` (class → method). Thành phần không có cha rõ ràng → gắn thẳng vào file.
- Mũi tên cấp hàm: `calls`; `imports`/`imports_from` vẫn gắn vào **khung file** vì chúng thuộc về file, không thuộc hàm.
- Lời gọi từ code cấp module (ngoài mọi hàm) đã có nguồn là node file → gắn vào khung file.
- `count` cấp hàm = số link gốc như v1; tổng các mũi tên con khi gộp lên file phải bằng số hiện tại ở cấp file (không đổi số liệu v2).

**Hiển thị**
- Nhãn ô hàm như graphify ghi (`create_user()`, `.Build()`), kèm dòng (`L5`) trong tooltip/panel chi tiết.
- Màu/viền phân biệt file (khung), class (khung, nét khác), hàm/method (ô lá).
- File không có thành phần nào (ví dụ `__init__.py` rỗng) không mở được (không có `▸`).
- Panel chi tiết mũi tên: khi hai đầu là hàm, `samples` đã chính là cặp hàm — giữ nguyên.

**Quy mô**
- Cảnh báo 400 mục áp dụng khi mở file (file lớn nhất trong repo graphify có ~500 node code, ví dụ `tests/test_languages.py`).
- id thành phần dùng id node của graphify (đã ổn định, duy nhất), không trùng id file/folder.

## 6. Đã chốt thêm (người dùng đồng ý)

- **Không tính `indirect_call`** (cạnh graphify suy ra); mũi tên cấp hàm chỉ từ `calls`.
- Khi file vừa mở, **class thu gọn**, nhất quán với folder/file.
- Người dùng đồng ý toàn bộ đề xuất ở mục 5.

## 7. Cho builder

- Kiểm thử trên repo mẫu `~/workspace/project/tests/repomap-test` (cập nhật `EXPECTED.md` cấp hàm, ví dụ `run() → create_user()` = 1, `create_user() → save()` = 1). Repo mẫu cần thêm một class có method để thử cấp class ⊃ method. Repo mẫu không dùng git.
