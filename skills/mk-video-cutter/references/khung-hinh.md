# Khung hình: viền thừa, tỉ lệ, độ phân giải

Đọc khi chạy `C frame` hoặc cắt có `--crop/--aspect/--res/--size`. `C` = `python3 <skill>/scripts/cutter.py`.

## 1. Cách script tìm khung nội dung

Video quay màn hình (cửa sổ Zoom, Meet, Teams) thường có phần thừa **đứng yên suốt buổi**: thanh menu máy tính, thanh tiêu đề và thanh công cụ của ứng dụng, dải đen hai bên khi video người giảng không lấp đầy cửa sổ. Phần bài giảng thì **chuyển động** (người nói, bảng, slide đổi).

1. Lấy 12 khung mẫu (`--samples`) rải đều **trong các đoạn KEEP** (có `--sheet`) hoặc cả video. Lấy trong KEEP để không bị đoạn đầu giờ/giải lao (bố cục khác) làm lệch.
2. Mỗi điểm ảnh: độ sáng chênh giữa các mẫu > 12 → "có chuyển động". Hàng/cột có ≥ 50% điểm chuyển động → thuộc nội dung.
3. Mép nội dung = hàng/cột đầu tiên từ mỗi phía mà liên tiếp ≥ 2% kích thước đều là nội dung. Mép bị tính lùi vào do phần nội dung đứng yên (giá sách, tường) → script dời mép **ra ngoài** tới đường biên sáng/tối rõ nhất và ổn định qua các mẫu (trong 4% kích thước). Chỉ dời ra ngoài, nên không làm mất nội dung.
4. Lùi vào 1 điểm ảnh phân tích (≈ 2 px ở 720p) để không dính mép thanh; toạ độ làm tròn số chẵn (yêu cầu của yuv420).
5. Khung là **hợp** của mọi bố cục trong các mẫu: không mất nội dung ở mẫu nào.

Dữ liệu giả để hình dung: video 1280×720 quay cửa sổ Zoom → `Viền thừa: có — trên 58 · dưới 40 · trái 80 · phải 90 px`, `Khung nội dung: 1110x622 → --crop 1110:622:80:58`.

## 2. Đọc kết quả `frame`

| Dòng in | Nghĩa | Agent làm gì |
|---|---|---|
| `Viền thừa: có … → --crop W:H:X:Y` | tìm được khung | cho xem 2 ảnh, dùng đúng giá trị `--crop` này khi cắt |
| `Viền thừa: không có` | video đầy khung | không dùng `--crop`; vẫn có thể đổi khung/độ phân giải |
| `không kết luận được — hình gần như đứng yên` | quá ít chuyển động (slide tĩnh cả buổi) | thử `--samples 30`; vẫn vậy → hỏi người dùng nhập `--crop` tay theo ảnh |
| `không kết luận được — vùng chuyển động quá nhỏ hoặc rời rạc` | có chuyển động nhưng không hàng/cột nào đủ 50% (nội dung nhỏ, vd cửa sổ video nhỏ giữa màn hình) | xem ảnh, nhập `--crop` tay |
| `không kết luận được — vùng nội dung quá nhỏ` | một phía viền > 30% | xem ảnh `khung-phat-hien.png`; thường là bố cục lạ → nhập `--crop` tay |
| `Cảnh báo: bố cục đổi giữa buổi — X/N mẫu bố cục hẹp … · đoạn …; Y/N mẫu bố cục rộng … · đoạn …` | Zoom đổi chế độ xem giữa buổi | đọc dòng `→` ngay sau, làm theo §3 |
| `Ghi chú: nền đen chiếm khoảng X% khung` | tỉ lệ nội dung khác khung đầu ra | bình thường với `pad`; báo người dùng nếu X > 10% |
| `Cảnh báo: phóng to xN` | nội dung nhỏ hơn khung đầu ra | nói thật: đạt khung chuẩn, không nét hơn gốc |

Ảnh xem trước (`--preview DIR`, không ghi đè ảnh đã có):
- `khung-phat-hien.png`: 4 mẫu ghép 2×2, khung đỏ = phần giữ. Script in mốc + mã đoạn của từng ô (`trên-trái: [00:02] · đoạn P1 (bố cục hẹp)`); khi bố cục đổi, 4 ô luôn có cả hai bố cục.
- `khung-dau-ra.png`: một khung hình của bố cục **đa số** chạy qua **đúng chuỗi lọc** sẽ dùng khi cắt — xem trước thế nào, ra video thế ấy.

## 3. Bố cục đổi giữa buổi

Khung hợp giữ đủ nội dung của bố cục rộng nhất, nhưng phần có bố cục hẹp sẽ còn dải đen. Cảnh báo chia mẫu thành hai nhóm (hẹp/rộng) kèm mốc và mã đoạn, rồi in một dòng `→`:

1. `→ Tách khung: chạy riêng --only P1,P2,P4 và --only P3` — mỗi nhóm đoạn chỉ có một bố cục. Chạy `frame` cho từng nhóm (dữ liệu giả):
   ```bash
   C frame <video> --sheet <sheet> --only P1,P2,P4 --preview $T/khung-a
   C frame <video> --sheet <sheet> --only P3 --preview $T/khung-b
   ```
   rồi cắt mỗi nhóm với `--only` và `--crop` riêng, cùng thư mục xuất (tên file không trùng nên không bị từ chối).
2. `→ Hai bố cục nằm chung đoạn …` — một đoạn tự nó có hai bố cục: giữ khung hợp (không mất nội dung, chấp nhận dải đen một phần đoạn) hoặc để người dùng tự cắt tay đoạn đó.

Mẫu rải đều theo thời gian, nên bố cục lạ chỉ kéo dài vài phút có thể không rơi vào mẫu nào → khung không bao phần đó. Người dùng biết có đoạn chia màn hình/xem nhiều người → tăng `--samples 30` hoặc chạy `--only` đúng đoạn đó.

## 4. Khung đầu ra

| Cờ | Ý nghĩa |
|---|---|
| `--aspect 16:9` / `9:16` / `1:1` / `4:5` / `W:H` | tỉ lệ khung; `source` = theo tỉ lệ nội dung |
| `--res 1080` | cạnh ngắn = 1080 (16:9 → 1920×1080, 9:16 → 1080×1920, 4:5 → 1080×1350); `source` = không phóng to |
| `--size WxH` | kích thước cụ thể, bỏ qua `--aspect/--res` |
| `--fit pad` (mặc định) | giữ trọn nội dung, bù nền đen |
| `--fit blur` | giữ trọn nội dung, nền là chính hình đó phóng to làm mờ — hợp video dọc |
| `--fit fill` | phủ kín khung, **cắt mép nội dung** (in % bị mất) — chỉ khi người dùng chọn |

Không có `--crop/--aspect/--res/--size` → hình giữ nguyên bằng stream copy (âm thanh vẫn theo `--mode`).

## 5. Chất lượng khi đổi khung (đo trên bài giảng thật 720p, 60 giây, Mac Apple Silicon)

| Bộ mã hoá | Tốc độ | Bitrate 1080p | VMAF so với khung chuẩn |
|---|---|---|---|
| x264 CRF 18, preset medium (mặc định) | ~4,8× thời gian thực | ~2,8 Mbps | 97,1 |
| VideoToolbox q65 (`--encoder videotoolbox`) | ~12× | ~3,3 Mbps | 93,6 |

VMAF ≥ 95 thường được coi là khó phân biệt bằng mắt. Phóng 720p lên 1080p dùng lanczos: chữ mịn hơn phóng thường, nhưng chi tiết không vượt bản gốc. Lợi ích thật: đạt khung chuẩn để nền tảng xếp video vào mức 1080p.
