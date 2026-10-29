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
| `--res auto` (khuyên dùng) | chuẩn cao nhất mà nội dung **và** khung không phải phóng quá 1,8× — tức một bậc chuẩn trên nguồn (§6) |
| `--res 1080` | cạnh ngắn = 1080 (16:9 → 1920×1080, 9:16 → 1080×1920, 4:5 → 1080×1350); `source` = không phóng to |
| `--enhance` | khử khối nén + khử nhiễu trên hình gốc, làm nét vừa phải sau khi phóng (§6) |
| `--size WxH` | kích thước cụ thể, bỏ qua `--aspect/--res` |
| `--fit pad` (mặc định) | giữ trọn nội dung, bù nền đen |
| `--fit blur` | giữ trọn nội dung, nền là chính hình đó phóng to làm mờ — hợp video dọc |
| `--fit fill` | phủ kín khung, **cắt mép nội dung** (in % bị mất) — chỉ khi người dùng chọn |

Không có `--crop/--aspect/--res/--size/--enhance` → hình giữ nguyên bằng stream copy (âm thanh vẫn theo `--mode`).

## 5. Chất lượng khi đổi khung (đo trên bài giảng thật 720p, 60 giây, Mac Apple Silicon)

| Bộ mã hoá | Tốc độ | Bitrate 1080p | VMAF so với khung chuẩn |
|---|---|---|---|
| x264 CRF 18, preset medium (mặc định) | ~4,8× thời gian thực | ~2,8 Mbps | 97,1 |
| VideoToolbox q65 (`--encoder videotoolbox`) | ~12× | ~3,3 Mbps | 93,6 |

VMAF ≥ 95 thường được coi là khó phân biệt bằng mắt. Phóng 720p lên 1080p dùng lanczos: chữ mịn hơn phóng thường, nhưng chi tiết không vượt bản gốc. Lợi ích thật: đạt khung chuẩn để nền tảng xếp video vào mức 1080p.

## 6. Chọn chuẩn phù hợp và làm nét vừa phải

Phóng to không thêm chi tiết; chỉ nên lên **một bậc chuẩn** so với khung nguồn. `--res auto` thử từ cao xuống, in từng bậc (khung ×, nội dung ×), lấy bậc đầu tiên đạt cả hai:
- **khung đầu ra ≤ 1,8× khung nguồn** (cạnh ngắn với cạnh ngắn): 720p → 1080p = ×1,5; 720p → 1440p = ×2,0 là quá;
- **nội dung sau cắt viền phóng ≤ 2,0×**: cho phép viền Zoom dày vẫn lên 1080p, chặn trường hợp phóng một mảnh nhỏ;
- **khung dọc/vuông** (9:16, 4:5, 1:1) tối đa 1080 cạnh ngắn — chuẩn Reels/TikTok/Shorts.

| Nguồn → nội dung sau cắt viền | `auto` chọn (16:9) | `auto` chọn (9:16) |
|---|---|---|
| 720p, đầy khung 1280×720 | 1920×1080 (khung ×1,5) | 1080×1920 |
| 720p, cắt viền Zoom còn ~1110×624 | 1920×1080 (nội dung ×1,73) | 1080×1920 |
| 720p, viền dày còn ~1040×582 | 1920×1080 (nội dung ×1,85) | 1080×1920 |
| 1080p | 2560×1440 (khung ×1,33) | 1080×1920 (trần khung dọc) |
| 480p | 1280×720 (khung ×1,5) | 720×1280 |
| 720p nhưng chỉ lấy một mảnh 356×200 | 640×360 (nội dung ×1,8) | 480×854 |

Người dùng nói rõ độ phân giải ("xuất 1080p", "làm bản 4K") → dùng `--res N` đúng ý họ; `auto` chỉ khi họ không nói. Script in `Cảnh báo: khung xA / nội dung xB vượt mức vừa phải … (chọn WxH)` khi số đó quá mức (vd ép 2160 từ nguồn 720p, hoặc 4K từ nguồn 1080p = ×2,0): nói thật là file to hơn, lộ khối vỡ, không nét hơn, đề xuất kích thước trong dòng đó. Người dùng vẫn giữ ý → cắt theo ý họ, ghi cảnh báo vào báo cáo; script không chặn.

`--enhance` (chuỗi lọc: `references/ffmpeg-recipes.md` §4):
- Khử khối 8×8 của bản nén và nhiễu nhẹ **trước** khi cắt viền (lưới khối còn thẳng hàng), làm nét có kiểm soát (`cas` 0,6) **sau** khi phóng, không phủ lên nền đen/nền mờ.
- Đo trên bài giảng 720p thật (bảng phấn, quay Zoom): độ nét vùng chữ tăng ~14%, nhiễu vùng bảng trống gần như không đổi (3,85 → 3,89); không thấy viền trắng quanh nét. 20 giây video xử lý trong 6,6 giây.
- Giới hạn: nguồn **nhiễu hạt nặng** (quay thiếu sáng, camera rẻ) thì bước làm nét làm hạt rõ hơn và file nặng hơn — xem `khung-dau-ra.png` trước; hạt lộ rõ → bỏ `--enhance`.
- Không tạo chi tiết mới, không đổi hình chữ — an toàn với chữ viết tay, chữ Hán trên bảng.

## 7. Muốn nét hơn mức này: công cụ AI cài thêm (ngoài skill)

Skill **không có sẵn** và **không tự cài** các công cụ dưới đây. Chỉ giới thiệu khi người dùng muốn nét hơn `--enhance`, kèm rủi ro, để họ tự quyết.

| Công cụ | Trên máy Mac | Ghi chú |
|---|---|---|
| Real-ESRGAN (ncnn-vulkan), miễn phí | bản chạy sẵn tải từ trang Releases của dự án | làm từng ảnh: tách video ra ảnh → phóng → ghép lại bằng ffmpeg; video 2 giờ là hàng trăm nghìn ảnh, cần **hàng trăm GB** ổ trống và nhiều giờ máy |
| Upscayl, miễn phí | `brew install --cask upscayl` | phóng **ảnh** (thumbnail, ảnh chụp bảng), không xử lý cả video |
| Video2X, miễn phí | chưa có bản chính thức cho macOS (Windows, Linux); có bản dựng cộng đồng chưa kiểm chứng | dùng trên máy Windows/Linux của chính người dùng |
| Topaz Video, trả phí | chạy trên Mac Apple Silicon (không hỗ trợ Mac Intel), xem yêu cầu hệ thống trước khi mua | có mẫu xử lý theo thời gian, ít nhấp nháy hơn mẫu từng ảnh; một số mẫu chạy qua máy chủ của hãng |

Rủi ro phải nói trước khi người dùng chọn AI:
- AI **vẽ thêm** chi tiết theo những gì nó đã học: chữ viết tay, chữ Hán trên bảng có thể bị đổi nét — với bài giảng là sai nội dung.
- Mặt người dễ mịn như sáp; mẫu xử lý từng ảnh dễ nhấp nháy giữa các khung.
- Video 2–3 giờ có hàng trăm nghìn khung hình: có thể tốn hàng chục giờ máy.
- Công cụ/mẫu chạy trên máy chủ ngoài hay dịch vụ online = **gửi video ra ngoài**: nói rõ điều này, người dùng tự quyết (agent không tải video lên đâu).

Cách thử an toàn: dùng chính skill cắt một mẫu 30–60 giây có chữ trên bảng và mặt người (PLAN một dòng `KEEP` + `END`, hoặc `--only` một đoạn ngắn), xuất 3 bản cạnh nhau (gốc / `--enhance` / AI), người dùng xem chữ trên bảng rồi mới quyết chạy cả buổi. Luôn giữ file gốc.

Nguồn: [Real-ESRGAN Releases](https://github.com/xinntao/Real-ESRGAN/releases) · [Upscayl](https://upscayl.org/) · [Video2X — hỗ trợ macOS (issue #1189)](https://github.com/k4yt3x/video2x/issues/1189) · [Topaz Video — yêu cầu hệ thống](https://docs.topazlabs.com/topaz-video/system-requirements).
