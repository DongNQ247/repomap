# Repo Map — spec v2 (thay đổi so với v1)

Ngày: 2026-11-14 · Trạng thái: ghi nhận, sửa sau · Kế thừa: `spec_v1.md` (mọi điểm không nhắc ở đây giữ nguyên)

## 1. Ngôn ngữ giao diện: tiếng Anh

Mọi chữ người dùng nhìn thấy trong công cụ phải là **tiếng Anh**: giao diện bản đồ, thông báo, README.
Tài liệu spec/plan trong `spec/` vẫn viết tiếng Việt.

Các chỗ hiện đang là tiếng Việt (tại commit `4f785ed`):

| File | Hiện tại | Đề xuất tiếng Anh |
|---|---|---|
| `repomap/web/aggregate.js:16` | `Bên ngoài` | `External` |
| `repomap/web/template.html:39` | `Mũi tên từ test` | `Test arrows` |
| `repomap/web/template.html:41` | `Bên ngoài` | `External` |
| `repomap/web/template.html:42` | `Thu gọn hết` | `Collapse all` |
| `repomap/web/app.js:20` | `ký hiệu` / `file` | `symbols` / `files` |
| `repomap/web/app.js:97` | `… N/M mẫu` | `… N/M samples` |
| `repomap/web/app.js:105` | `N ô, M mũi tên` | `N boxes, M arrows` |
| `repomap/web/app.js:110` | `Lỗi bố cục:` | `Layout error:` |
| `repomap/web/app.js:117` | `Sẽ hiện N mục, có thể chậm. Tiếp tục?` | `This will show N items and may be slow. Continue?` |
| `README.md` | toàn bộ | viết lại bằng tiếng Anh |

Nhãn `Docs/config` đã là tiếng Anh, giữ nguyên.

## 2. Bỏ "giai đoạn 2: tô màu diff" khỏi phạm vi

Người dùng quyết định chưa cần tô màu phần agent thay đổi. Mọi nhắc tới **giai đoạn 2 / diff / PR** trong `spec_v1.md` (mục 2 "Không phải mục tiêu", mục 6 "Chuẩn bị cho giai đoạn 2") **không còn hiệu lực**: không lên kế hoạch, không thiết kế để chuẩn bị cho nó. Code hiện có (`data-id` ổn định trên mỗi ô) giữ nguyên, không cần gỡ.

## 3. Kiểm tra

Kiểm tra mục 1 khi sửa: `grep -rnP "[^\x00-\x7F]" repomap/ README.md` (trừ `vendor/`) chỉ còn các ký hiệu `▸ ▾ → …`.
