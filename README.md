# repomap

Vẽ bản đồ toàn repo từ `graph.json` của graphify: folder là khung, file là ô, mũi tên file→file
(`calls`, `imports`, `imports_from`) có số lần. Một file HTML tự chứa, mở offline.

```
python3 -m repomap path/to/graphify-out/graph.json -o out/map.html
```

Mặc định ghi `repomap.html` cạnh `graph.json`. Chỉ dùng thư viện chuẩn Python 3.10+.

## Dùng

- Click folder để mở/thu. Ban đầu mọi folder thu gọn; mũi tên tới folder thu gọn được gộp, cộng số.
- Hover mũi tên: xem tách theo relation và các cặp ký hiệu kèm `file:dòng`. Click để ghim, click nền để bỏ.
- Cuộn chuột để zoom, kéo để di chuyển.
- **Mũi tên từ test**: bật mũi tên xuất phát từ file test (ô test luôn hiện).
- **Docs/config**: hiện file `.md`, `.json`, `.yml`, `.toml`…
- **Bên ngoài**: hiện khung ký hiệu ngoài repo (node không có `source_file`), theo tên ký hiệu.
- **Thu gọn hết**: về trạng thái ban đầu.
- Mở folder làm số ô + mũi tên vượt 400 sẽ hỏi xác nhận trước.

## Test

```
python3 -m unittest discover tests -v
node --test tests/*.test.mjs
```
