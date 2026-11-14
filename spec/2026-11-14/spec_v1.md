# Repo Map — bản đồ file/folder gọi nhau từ graph.json (spec v1)

Ngày: 2026-11-14 · Trạng thái: chờ duyệt

## 1. Ý định và lý do

Agent viết code nhanh; nút thắt là **người review kiểm soát được code agent viết**. Khi review, người dùng không trả lời được:

- Code này sống ở đâu (file, folder)?
- Hàm/file này được những file nào gọi?
- Folder này có gọi sang chỗ khác không?
- Các phần của repo tương tác thế nào?

Graphify đã phân tích repo bằng AST và ghi kết quả ra `graph.json` (file, dòng, `calls`, `imports`… — chính xác, không đoán). Nhưng `graph.html` hiện vẽ toàn bộ ~24k node dạng force-directed nên quá rối để review.

Công cụ này đọc `graph.json` và xuất **một bản đồ toàn repo theo đúng cấu trúc thư mục, cho thấy file/folder nào gọi file/folder nào**, mở rộng/thu gọn được.

## 2. Mục tiêu / Không phải mục tiêu / Phản mục tiêu

**Mục tiêu (giai đoạn 1)**
- Bản đồ toàn repo dạng **hộp lồng hộp + mũi tên** (folder = khung, file = ô, folder con = khung lồng trong khung cha).
- Mở đầu **thu gọn**: chỉ hiện các mục cấp gốc. Click folder để mở/thu.
- Mũi tên phản ánh quan hệ **file → file**; khi đầu mũi tên nằm trong folder đang thu gọn thì gộp lên ô folder, hiện tổng số lần.
- Trả lời được 4 câu hỏi ở mục 1 bằng cách mở dần bản đồ.

**Không phải mục tiêu (giai đoạn 1)**
- Làm nổi bật diff/PR của agent → **giai đoạn 2**, nhưng thiết kế phải cho phép tô màu file/cạnh lên chính bản đồ này.
- Cấp hàm/class (bản đồ dừng ở cấp file).
- Gom nhóm tự động, đặt tên thành phần, file cấu hình thành phần.
- Chạy lại phân tích AST — công cụ chỉ đọc `graph.json` có sẵn.

**Phản mục tiêu (làm thế này là thất bại dù chạy được)**
- Bản đồ ban đầu rối như `graph.html`.
- Cấu trúc hiển thị khác cấu trúc thư mục thật (người review phải "dịch" lại).
- Số liệu/mũi tên sai hướng hoặc bịa (phải truy được về cạnh trong `graph.json`).

## 3. Ràng buộc

- **Độc lập với graphify** (cách 3): không import code graphify, không sửa repo graphify. Chỉ phụ thuộc vào định dạng `graph.json`.
- Phải xử lý đúng **chiều cạnh** của `graph.json`: file ghi `"directed": false` nhưng **thứ tự `source → target` của mỗi link là chiều**; nếu link có `_src`/`_tgt` thì các trường đó thắng (xem `ARCHITECTURE.md`, mục "Edge direction in graph.json"). Đọc JSON thô, không dùng `node_link_graph()` của NetworkX.
- Quy mô tham chiếu: repo graphify — 24.484 node, 52.062 cạnh, ~1.130 file nguồn. Phải mở mượt ở quy mô này.
- Đầu ra là **một file HTML tự chứa**, mở offline bằng trình duyệt.

## 4. Các cách đã cân nhắc

| Cách | Mô tả | Đánh đổi |
|---|---|---|
| 1. Lệnh export mới trong graphify | `graphify export map-html`, dùng lại loader của graphify | Tận dụng code sẵn; nhưng phải gộp với upstream khi fork cập nhật |
| 2. Mở rộng `tree_html.py` (`graphify tree`) | Thêm mũi tên vào cây D3 sẵn có | Ít code nhất; nhưng bố cục cây ngang không phải hộp lồng hộp, mũi tên chéo nhánh rối — trái với kiểu A |
| **3. Công cụ riêng ngoài graphify (đã chọn)** | Script độc lập đọc `graph.json` | Không phụ thuộc/không đụng upstream, dùng với mọi `graph.json`; phải tự viết loader (gồm xử lý chiều cạnh) |

Người dùng chọn **cách 3** để tách khỏi graphify.

Kiểu trình bày: đã so sánh A (hộp lồng + mũi tên), B (cây + bảng gọi/được gọi), C (ma trận). Người dùng chọn **A**.

## 5. Những gì đã quyết

**Dữ liệu**
- Node có `source_file` → thuộc file đó. Cây thư mục dựng từ đường dẫn `source_file`.
- Cạnh tính mũi tên: `calls`, `imports`, `imports_from`. Bỏ `contains` (đã thể hiện bằng lồng hộp). Các relation khác *(builder quyết, xem mục 6)*.
- Cạnh nối 2 node cùng file → bỏ. Cạnh giữa 2 file khác nhau → cộng dồn thành 1 cạnh file→file có `count`.
- Không gom nhóm tự động; giữ đúng cấu trúc thư mục.

**Hiển thị**
- Kiểu A: hộp lồng hộp theo cấp thư mục, mũi tên có hướng, nhãn số = số lời gọi/import.
- Ban đầu: mọi folder thu gọn, chỉ hiện mục cấp gốc.
- Click folder: mở/thu. Folder thu gọn hiện số file bên trong.
- Gộp mũi tên: khi đầu mút nằm trong folder đang thu gọn, mũi tên nối tới ô folder gần nhất đang hiển thị; nhiều mũi tên trùng 2 đầu → gộp, cộng `count`. Mũi tên mà cả 2 đầu cùng rơi vào 1 ô thu gọn → ẩn.

**Test và thư viện ngoài** (đề xuất của Claude, người dùng đồng ý)
- File test (trong `tests/`/`test/` hoặc tên kiểu `test_*.py`, `*_test.go`, `*.spec.ts`, `*.test.*`): **folder/file vẫn hiện**, nhưng **mũi tên xuất phát từ file test mặc định tắt**, có nút bật.
- Thư viện ngoài (node có `source_file` rỗng, ví dụ `Path`, `Counter`): **mặc định ẩn**, có nút bật; khi bật, hiện thành **một khung "Bên ngoài"** ở rìa, mở ra thấy từng **tên ký hiệu** (`label`). **Không gom theo thư viện** — `graph.json` không ghi tên thư viện (id node mang tiền tố của file *dùng* nó), đoán sẽ sinh mũi tên sai. *(Claude quyết, sau builder check: 767 node như vậy, chạm 2.818 cạnh.)*

**File nào thành ô** (người dùng chọn theo đề xuất)
- **Mọi file code đều vẽ**, kể cả file không có mũi tên (để trả lời "code sống ở đâu").
- **Docs và config** (`.md`, `.json`, `.yml`/`.yaml`, `.toml`…): **mặc định ẩn**, có nút bật, cùng cơ chế với test.
- File test và fixture trong `tests/` vẫn là file code, theo quy tắc test ở trên.

**Số trên mũi tên** *(Claude quyết)*
- `count` = **số link gốc** trong `graph.json` (mỗi link `calls`/`imports`/`imports_from` tính 1), **cộng chung** mọi relation giữa cặp file.
- Hover/click mũi tên: tách theo relation và liệt kê cặp ký hiệu gọi nhau kèm `source_file:source_location` — để mọi con số truy được về cạnh gốc.

**Hiệu năng** *(Claude quyết)*
- Chỉ dựng và tính layout cho phần **đang hiển thị**; nội dung folder chỉ dựng khi mở.
- Mở một folder khiến số ô/mũi tên hiển thị vượt ngưỡng (builder chọn, cỡ vài trăm) → cảnh báo trước, không treo trình duyệt.

## 6. Để builder quyết (Claude đề xuất mặc định)

- **Ngôn ngữ/đóng gói**: Python 3 chỉ dùng thư viện chuẩn, một lệnh `repomap graph.json -o map.html` *(Claude chọn: dễ chạy cạnh graphify vốn là Python)*.
- **Bố cục**: ELK.js (layered, hỗ trợ compound/nested node) chạy trong trình duyệt; tính lại layout khi mở/thu. Nhúng inline hoặc từ CDN có ghim phiên bản — builder quyết, ưu tiên inline để chạy offline.
- **Relation khác** (`indirect_call`, `inherits`, `uses`, `references` từ docs…): mặc định chỉ 3 loại ở mục 5; builder có thể thêm bộ lọc relation nếu rẻ.
- Hiển thị chi tiết khi hover/click mũi tên (ví dụ danh sách cặp hàm gọi nhau, file:dòng) — nên có nếu rẻ, vì phục vụ truy vết.
- Chuẩn bị cho giai đoạn 2: dữ liệu nhúng vào HTML nên có định danh file ổn định để sau này tô màu theo danh sách file/cạnh thay đổi.

## 7. Vị trí

Repo riêng: `~/workspace/project/repomap` (người dùng chọn). Spec/plan theo quy ước `spec/<date>/spec_v<x>.md` và `spec/<date>/plan_v<x>.md` trong repo này. Repo graphify không bị sửa.
