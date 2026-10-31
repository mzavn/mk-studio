# Phụ đề đẹp: ngắt dòng, vị trí, in vào video

Áp cho mọi file SRT skill tạo ra (§1) và cho bước tuỳ chọn in phụ đề vào video (§3). `B` = `python3 <skill>/scripts/burn.py`.

## 1. Khổ phụ đề — áp ngay khi tạo SRT

Phụ đề ra đẹp ngay từ bước lấy phụ đề, để người dùng nhập thẳng vào CapCut hậu kỳ tiếp, hoặc in luôn bằng §3.

| Khung video | Ký tự/dòng | Dòng | Ghi chú |
|---|---|---|---|
| Ngang (16:9) | 42 | 2 | Netflix tiếng Việt; chữ rộng tối đa ~68% khung (BBC) |
| Dọc (9:16) | 26 | 2 | khớp `B layout` mặc định (TikTok + Shorts, chữ 3,3% chiều cao) |
| Dọc, kiểu "ngắn" | theo `B layout --style ngan` | 1 | chữ to, một dòng; ngắt bằng `S reflow --max-chars <số D2 in ra> --max-lines 1` |

Đo khung: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 <video>` (rộng > cao là ngang). Không có video → hỏi người dùng đăng ở đâu; mặc định ngang.
Truyền khổ vào lệnh tạo phụ đề: `S clean … --max-chars 26`, `K srt … --max-chars 26`, `S check … --max-chars 26`. Đã có SRT khổ khác → `S reflow <file> --max-chars 26 --out <tên>.doc.srt`: câu đã vừa khổ giữ nguyên (kể cả chỗ xuống dòng sửa tay), câu dài tách thành nhiều câu, mốc chia theo số ký tự trong khoảng của câu gốc.

**Luật ngắt dòng** (script áp sẵn; agent rà lại):
- Vừa một dòng thì để một dòng. Hai dòng: ngắt sau dấu câu, trước liên từ (và, nhưng, mà, thì, vì, nên, nếu…) hoặc giới từ (của, cho, với, trong, từ…).
- Không tách: số với đơn vị ("30 phút"), họ với tên, chữ phủ định/trợ từ với chữ sau ("không | phải", "đã | làm"), chủ ngữ với động từ khi còn cách khác.
- Dòng dưới dài hơn dòng trên; không để 1–2 chữ lẻ ở dòng trên; không để một chữ lẻ thành một câu riêng.
- **Từ ghép:** script không có từ điển; nó tránh ngắt giữa hai chữ nội dung nhưng vẫn có thể tách "thể | thao", "trở | thành" khi không còn chỗ khác. Agent đọc từng câu, sửa qua `S export` → sửa → `S build` (giữ mốc):
  - trong một câu: chuyển một chữ lên/xuống dòng cho liền từ ghép;
  - giữa hai câu kề nhau: chuyển chữ sang câu bên cạnh, kiểm lại nhịp đọc câu nhận thêm chữ — mục tiêu 17 ký tự/giây, chấp nhận tới 20 cho riêng câu này; vượt 20 thì không chuyển;
  - không có chỗ ngắt khác: để dòng dài hơn khổ, tối đa khổ + 3 (ngang 45, dọc 29) — khi in vào video thì theo mức "dòng khó ngắt" `B layout` in ra. `S check` chỉ cảnh báo dòng dài; `B ass` báo `LỖI` khi chữ tràn vùng phụ đề;
  - cả ba cách đều không được (vd "trở | thành" ở câu 30 ký tự khổ dọc): giữ chỗ tách, liệt kê câu đó cho người dùng kèm hai lựa chọn — để nguyên, hoặc bỏ bớt một chữ không mang nghĩa trong câu (chỉ khi người dùng đồng ý, theo `references/chuan-hoa-tieng-viet.md` §3).

**Nhịp đọc:** bản đăng mạng xã hội hoặc in vào video theo Netflix tiếng Việt — ≤ 17 ký tự/giây (`S reflow` dùng sẵn mức này; `S check … --max-cps 17`), mỗi câu hiện 5/6 giây – 7 giây. `S check` mặc định 20 (lời họp, nói nhanh). Script chỉ cảnh báo; rút gọn chữ theo `references/chuan-hoa-tieng-viet.md` §3 (chỉ khi người dùng bảo).

**Nhập vào CapCut:** CapCut Desktop (Captions → Add captions → Import file) và CapCut Web (Captions → Upload caption file) nhập được `.srt` UTF-8 — file skill tạo đã là UTF-8. CapCut trên điện thoại không nhập được file phụ đề: nhập trên Desktop/Web rồi mở dự án trên điện thoại qua đồng bộ cloud ([CapCut Help](https://www.capcut.com/help/how-to-import-subtitles)). Kiểu chữ, vị trí chỉnh tiếp trong CapCut ("Apply to all captions").

## 2. Vị trí an toàn và cỡ chữ

Vùng giao diện che video (tỉ lệ khung). Số liệu video dọc là tổng hợp 2026 ([nguồn](https://github.com/stkzlv/ContentEngineAI/blob/main/docs/explanation/platform-safe-zones.md)), không phải tài liệu chính thức của từng hãng — trừ Reels (Meta công bố 14% trên / 35% dưới). Giao diện các app đổi theo thời gian: luôn xem ảnh xem trước.

| `--platform` | Trên | Dưới | Trái | Phải (cột nút) |
|---|---|---|---|---|
| `youtube` (ngang) | 5% | 6% | 5% | 5% |
| `khung` (không app) | 5% | 5% | 5% | 5% |
| `tiktok` | 7% | 25% | 6% | 17% |
| `shorts` | 6% | 16% | 5% | 14% |
| `reels` | 14% | 35% | 6% | 11% |

Nhiều nền tảng (`tiktok,shorts`) → lấy vùng chừa lớn nhất mỗi cạnh. Mặc định: ngang `youtube`, dọc `tiktok,shorts`. Thêm `reels` thì đáy chừa 35%: người nói ngồi giữa khung thường không còn chỗ dưới mặt → script đưa phụ đề lên trên đầu hoặc cảnh báo.

**Không che mặt** (Netflix tiếng Việt §18, BBC §10): phụ đề không đè miệng, mặt, chữ có sẵn trên hình. Script đặt phụ đề sát vùng an toàn ở đáy; nếu đè khung mặt → lên trên đầu nếu vừa; không vừa đâu → cảnh báo. Cả video một vị trí (không để câu nhảy lên xuống).

**Cỡ chữ** (theo chiều cao video): ngang 5,5% (59px ở 1080p); dọc chuẩn 3,3% (63px ở 1920); dọc kiểu ngắn 4,5%, một dòng. BBC: một dòng cao ~8% khung là cỡ tối đa. Chữ trắng, viền đen (mặc định) hoặc nền mờ sau chữ (`--box`, hợp nền sáng/rối).

**Font** — cần có đủ dấu tiếng Việt:

| Font | Có sẵn | Ghi chú |
|---|---|---|
| Arial (mặc định) | macOS, Windows | Netflix tiếng Việt dùng làm chuẩn |
| Be Vietnam Pro | cài thêm (Google Fonts, miễn phí) | thiết kế cho tiếng Việt, hợp video mạng xã hội |
| Roboto, Inter, Montserrat, Noto Sans | cài thêm (Google Fonts, miễn phí) | không cài thì chỉ thư mục chứa file `.ttf` bằng `--fonts-dir` |

`B layout` kiểm font bằng `fc-list` (nếu máy có); `B burn --preview` in dòng **Font dùng thật** — khác font đã chọn nghĩa là máy không có font đó, libass đã thay font khác.

## 3. Luồng D — In phụ đề vào video (tuỳ chọn)

Chỉ chạy khi người dùng yêu cầu ("in phụ đề vào video", "làm luôn bản đăng TikTok"). Đầu vào: video hoàn chỉnh (thường là `<tên>-final.mp4`) và phụ đề cùng timeline (`<tên>-final.vi.srt`). Video ngang đăng YouTube → khuyên tải `.srt` lên YouTube Studio thay vì in cứng (người xem bật/tắt, YouTube tự dịch), chỉ in khi người dùng vẫn muốn.

**Cần ffmpeg có libass.** Thiếu → `B burn` dừng và in cách cài; không tự cài, hỏi người dùng (macOS: `brew install ffmpeg-full`, cài song song, không thay `ffmpeg` đang dùng; Windows: `winget install Gyan.FFmpeg` là bản full; Linux: `sudo apt install ffmpeg`). `B burn` tìm ffmpeg có libass theo thứ tự: `--ffmpeg <đường dẫn>`, biến môi trường `MK_SUBTITLE_FFMPEG`, `ffmpeg` trong PATH, bản `ffmpeg-full` của Homebrew. Các bước D1–D4 chạy với mọi ffmpeg.

Các bước, lệnh, định nghĩa "duyệt": `SKILL.md` Luồng D. Ghi chú thêm:
- **D1 — đo mặt:** Vision chạy trên máy, không gửi ảnh đi. Máy không phải macOS: ảnh khung mẫu có mặt người — agent chỉ tự xem để ước khung mặt (ghi `mat.tsv`, tỉ lệ 0–1) khi người dùng đồng ý; mặc định bỏ `--faces`, người dùng tự xem ảnh D2.
- **D2 — ảnh xem trước:** xám = giao diện app, đỏ = mặt, xanh = vùng phụ đề. `Cảnh báo … thiếu khung mẫu` → đo mặt dừng giữa chừng, đo lại.
- **D3 — mức chữ:** D2 in "tối đa N ký tự (dòng khó ngắt được tới M)": N là khổ mục tiêu cho `S reflow`, M là mức trần trước khi chữ tràn vùng xanh.
- **D5 — ảnh mẫu** ghi vào `$T` (không vào thư mục video); chạy lại sau khi sửa → tiền tố mới (`chu-2`). `Cảnh báo` phụ đề dài hơn video hoặc hết quá sớm → kiểm lại đúng phụ đề của bản final.
- **D6:** video mã hoá lại (libx264 CRF 18), tiếng giữ nguyên.

Nhiều nền tảng có vùng chừa khác nhau → một file chung theo `tiktok,shorts` (mặc định); người dùng cần đúng từng app → mỗi app một lượt D2–D6 với `--out <tên>-sub-<app>.mp4`.

## 4. Giới hạn

- Chỉ tránh mặt theo chiều dọc (đưa phụ đề lên/xuống); không né chữ có sẵn trên hình — agent xem ảnh xem trước.
- Khung mặt đo trên 6 khung mẫu: người nói di chuyển nhiều → tăng `B frames --samples` (tối đa 12).
- Không hiệu ứng chữ chạy theo từng từ, không tô màu từ khoá: làm trong CapCut với file `.srt`.
- Số liệu vùng an toàn video dọc là tổng hợp, app có thể đổi giao diện.
