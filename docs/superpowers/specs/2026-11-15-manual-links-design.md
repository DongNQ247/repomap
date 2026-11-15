# Manual links: tự thêm thành phần và liên kết mà graphify bỏ sót

## Ý định
graphify không chính xác 100%: (1) đôi khi thiếu mũi tên giữa hai thành phần có thật,
(2) không thấy những thứ chỉ có khi chạy code: file được tạo ra lúc chạy, và các "khái niệm",
tức là thứ bên ngoài mà code tương tác tới nhưng không có trong mã nguồn (ví dụ `SSD`).
Người dùng, hoặc Claude qua skill, cần bổ sung những thứ này bằng tay để map đúng với thực tế.

## Mục tiêu
- Lệnh `repomap link` để thêm/xoá node runtime (file hoặc khái niệm) và mũi tên.
- Loại quan hệ cố định: `calls`, `imports`, `creates`, `reads`. Loại khác thì báo lỗi (exit 2).
- Trên map: node và mũi tên tự thêm vẽ **nét đứt**; panel chi tiết ghi "added manually".
- Dữ liệu sống sót qua `graphify update` và commit được.

## Không làm
- Không quét hay phân tích mã nguồn (repomap chỉ đi kèm graphify).
- Không sửa `graph.json`.
- Không fingerprint node runtime/khái niệm (không có code để hash).
- Không cho tự đặt loại quan hệ tuỳ ý.

## Anti-goal
Dữ liệu tự thêm bị mất hoặc lặng lẽ biến mất khi code đổi tên. Mất dấu thì phải được báo, không được im lặng.

## Các hướng đã cân nhắc
- **A. File riêng `repomap-out/links.json` + lệnh `repomap link`** (đã chọn). Dùng lại cách đặt tên,
  `resolve`, ghi file atomic và cách báo thành phần đã mất của `notes.py`. Không bị graphify ghi đè.
- B. Một graph phụ cùng format `graph.json`: viết ít code load hơn, nhưng người/Claude phải viết JSON
  với id nội bộ của graphify, và format đó đổi là vỡ. Loại.
- C. Gộp vào `note add ... --creates Y`: trộn hai việc, xoá mũi tên rắc rối. Loại.
- (Ghi chú trong comment code: cần parser, trái hướng dự án. Loại.)

## CLI
```
repomap link node <path>             # file runtime, vd repomap-out/map.html
repomap link node <name> --concept   # khái niệm, vd SSD
repomap link add <src> <rel> <tgt>   # rel ∈ calls|imports|creates|reads
repomap link delete <src> <rel> <tgt>
repomap link delete <name>           # xoá node runtime/khái niệm
```
- Tên `src`/`tgt` dùng đúng cú pháp của `note` (`app/db`, `app/x.py`, `app/x.py::Cls.fn@L40`),
  hoặc tên của node runtime/khái niệm đã thêm. Tìm từ thư mục con giống `note` (`find_project`).
- Hai đầu mũi tên phải tồn tại lúc thêm (trên map hoặc đã `link node`), không thì báo lỗi như `resolve`.
- `delete` vẫn chạy với tên đã mất khỏi map (giống `note delete`).
- Thêm trùng là no-op và in ra "already exists".
- (mình chọn) `link node` chỉ nhận file, không nhận folder; folder ảo tự sinh từ đường dẫn. Không kiểm tra
  file có tồn tại trên đĩa (file sinh ra lúc chạy thường chưa có).
- (mình chọn) Tên khái niệm không được chứa `/` hay `::`. Tên trùng với thành phần đã có trên map
  hoặc node đã thêm thì từ chối ngay lúc thêm, nên `resolve` không bao giờ nhập nhằng.
- (mình chọn) Hai đầu mũi tên giữ **đúng box** người dùng chỉ (symbol, file hoặc folder) với mọi loại
  quan hệ, không gộp về file như graphify làm với `imports`. Mũi tên đầu folder đi qua `lift()` như mũi tên thường.

## Lưu trữ: `repomap-out/links.json`
```json
{"version": 1,
 "nodes": {"repomap-out/map.html": {"kind": "file"}, "SSD": {"kind": "concept"}},
 "edges": [{"src": "repomap/render.py::render_html", "rel": "creates", "tgt": "repomap-out/map.html"}]}
```
Ghi atomic, sort ổn định, quyền 0644, giống `save_notes`. JSON lỗi thì exit 1 kèm thông báo.

## Gộp vào map (lúc chạy `repomap .`)
- Node runtime kind `file`: thêm vào `model["files"]` với `"manual": true`, nên nằm đúng folder
  trong cây và tạo frame ảo nếu folder chưa có. Nếu graphify đã có file đó thì dùng node thật, không tạo bản trùng.
- Khái niệm: frame riêng **"Concepts"**, cạnh frame External, luôn hiện (không có nút lọc).
- Mũi tên: thêm vào `model["edges"]` với `by_rel` và sample `loc: "manual"`, `"manual": true`.
  Hai đầu là box id lấy từ `components()`.
- Node runtime và khái niệm cũng được nhận note (`note add SSD "..."`). Không có fingerprint nên
  note không bao giờ bị đánh dấu "may be outdated".
- Mũi tên hoặc node có đầu không còn trên map: bỏ qua khi vẽ và liệt kê sau khi chạy `repomap`,
  giống note bị mất, kèm gợi ý `repomap link delete ...`.
- (mình chọn) Node runtime mà graphify sau này đã thấy: liệt kê là "now found by graphify" để người dùng
  `link delete` cho gọn; mũi tên trỏ tới nó vẫn chạy bình thường.
- (mình chọn) Cờ "toàn bộ là manual" tính bằng số đếm (`manual_count == count`), không dựa vào samples (bị cắt ở 20).

## Web
- Box `manual` và frame Concepts: viền nét đứt.
- Mũi tên: nét đứt khi **mọi** liên kết gộp vào nó đều là tự thêm. Mũi tên trộn thì vẽ nét liền,
  panel liệt kê sample có dòng "(manual)".
- Có chú thích màu/nhãn cho `creates`, `reads`.

## Skill
Cập nhật `repomap/skill/SKILL.md`: chỉ thêm link khi người dùng yêu cầu ("thêm liên kết", "add link"),
cách đặt tên, 4 loại quan hệ, khi nào dùng `--concept`.

## Để lại cho người xây
- Tên module (`links.py` hay mở rộng `notes.py`), cách chia code JS, màu cụ thể.
- Test: unit cho đọc/ghi/resolve của links, test CLI cho từng lệnh con và các lỗi, test aggregate cho cờ nét đứt.
- README: thêm mục "Manual links".

## Các quyết định mình tự chọn (đã duyệt 2026-11-15)
- Lệnh tên `link`, file `links.json`.
- Frame "Concepts" luôn hiện.
- Mũi tên trộn vẽ nét liền.
- Thêm trùng là no-op.
- Xoá node runtime vẫn còn mũi tên trỏ tới thì từ chối và liệt kê các mũi tên đó.
