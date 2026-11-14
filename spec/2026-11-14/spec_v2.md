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

## 3. Ẩn/hiện file và folder qua panel cây bên trái

**Người dùng yêu cầu**
- Thêm tính năng **ẩn/hiện từng file (và folder)** trên bản đồ.
- Một **panel bên trái, thu gọn được** (nút đóng/mở panel), hiển thị **cấu trúc cây** thư mục của repo; các node trong cây **mở rộng/thu gọn được**.

**Đề xuất của Claude — người dùng đã đồng ý toàn bộ** (ẩn file → mũi tên biến mất hẳn, không gộp lên cha)
- Mỗi dòng trong cây có một **checkbox hiện/ẩn**. Bỏ chọn → file/folder đó biến khỏi bản đồ **cùng mọi mũi tên đi vào/ra nó** (không gộp lên folder cha — mục đích là bớt nhiễu). Ẩn folder = ẩn mọi thứ bên trong; checkbox folder ở trạng thái "một phần" khi chỉ ẩn một số con.
- Mở/thu trong **cây** chỉ để duyệt, **độc lập** với mở/thu trên **bản đồ**. Click tên một mục trong cây → bản đồ mở các folder cha cần thiết và cuộn tới, làm nổi bật mục đó.
- Cây có ô **tìm theo tên** để lọc nhanh.
- Cây chỉ hiện những mục mà các nút lọc hiện tại cho phép (docs ẩn khi "Docs/config" tắt; khung External chỉ khi bật).
- Trạng thái ẩn không lưu lại khi tải lại trang; nút "Show all" để hiện lại tất cả.
- Đếm `boxes/arrows` và cảnh báo 400 mục tính sau khi đã bỏ các mục ẩn.
- Chữ trên panel bằng tiếng Anh (mục 1).

## 4. Kiểm tra

Kiểm tra mục 1 khi sửa: `grep -rnP "[^\x00-\x7F]" repomap/ README.md` (trừ `vendor/`) chỉ còn các ký hiệu `▸ ▾ → …`.
