# Nhật ký thay đổi

Mỗi bản có số dạng `X.Y.Z` (chung cho cả bộ skill):

- **Số cuối (Z)** tăng: sửa lỗi nhỏ, cách dùng không đổi.
- **Số giữa (Y)** tăng: có thêm tính năng; cập nhật xong dùng tiếp bình thường.
- **Số đầu (X)** tăng: cập nhật xong bạn cần làm thêm một bước — bản đó sẽ ghi rõ bước gì.

Cập nhật: `bash ~/.mk-studio/install.sh --update`.

## Chưa phát hành

Dự kiến: v0.6.0

### mk-subtitle

**Mới**

- **Lấy phụ đề từ link YouTube.** Chưa có file phụ đề mà video đã đăng YouTube (kể cả video không công khai) thì đưa link: skill tải phụ đề có sẵn (không tải video) trong vài giây và in tiêu đề, ngôn ngữ nói của video. Ưu tiên phụ đề chủ kênh tải lên; không có thì lấy phụ đề tự động **bản gốc**, có mốc thời gian từng từ để cắt "à, ừ" đúng chỗ (bản tự động có lúc lược bớt âm đệm — skill sẽ nhắc). Video nói ngôn ngữ khác thì phụ đề tiếng Việt là bản dịch: skill dừng và hỏi bạn lấy lời gốc hay chỉ cần bản dịch. Bản tự động dịch máy, link playlist hay link kênh bị từ chối. Video riêng tư: dùng phiên đăng nhập YouTube trên trình duyệt (`--cookies-from-browser`) khi bạn đồng ý. Cần `yt-dlp` trên máy (`brew install yt-dlp`).
- **Chỉ có file video, chưa đăng đâu:** skill không tự nhận giọng, mà hướng dẫn bạn tự cài whisper.cpp (miễn phí, chạy trên máy, không gửi âm thanh ra ngoài) để tạo file SRT, kèm các lỗi hay gặp: nghe sai tên riêng, từ Hán Việt; bịa câu lặp ở đoạn im lặng dài.

## v0.5.0 — 30/10/2026

### mk-video-cutter

**Mới**

- **Làm nét vừa phải (`--enhance`).** Khử khối vỡ do nén và nhiễu trên hình gốc, rồi làm nét có kiểm soát sau khi phóng. Nét phấn, chữ trên bảng gọn hơn, không vẽ thêm chi tiết nên chữ viết tay, chữ Hán giữ nguyên hình. Chạy khoảng 1/3 thời lượng clip trên Apple Silicon.
- **Tự chọn độ phân giải chuẩn (`--res auto`).** Lên đúng một bậc chuẩn so với video nguồn: 720p → 1080p (kể cả khi đã cắt viền Zoom dày), 1080p → 1440p, 480p → 720p; khung dọc và vuông tối đa 1080×1920 / 1080×1350 / 1080×1080 theo chuẩn Reels, TikTok, Shorts. Lệnh in từng bậc đã thử và lý do chọn. Bạn nói rõ độ phân giải thì skill dùng đúng số đó.
- **Cảnh báo khi ép 2K/4K từ nguồn thấp.** `--res 2160` trên nguồn 720p báo "vượt mức vừa phải", nói rõ chỉ làm file to và lộ khối vỡ, gợi ý kích thước phù hợp.
- Tài liệu skill giới thiệu các công cụ phóng to bằng AI cài thêm (Real-ESRGAN, Upscayl, Video2X, Topaz Video) cho ai muốn nét hơn nữa, kèm rủi ro (AI có thể vẽ lại sai chữ viết tay, chữ Hán) và cách thử an toàn. Skill không có sẵn và không tự cài các công cụ này.

## v0.4.0 — 29/10/2026

### mk-video-cutter

**Mới**

- **Khung hình sạch cho video quay màn hình Zoom.** Lệnh mới `frame` tự tìm vùng bài giảng, bỏ thanh menu, thanh tiêu đề, thanh công cụ Zoom và dải đen, rồi xuất 2 ảnh xem trước (khung đỏ trên 4 mẫu, và một khung hình thành phẩm) để bạn duyệt trước khi cắt. Nếu Zoom đổi bố cục giữa buổi, lệnh báo đoạn nào bị ảnh hưởng; dùng `--only P4` để cắt riêng đoạn đó với khung riêng.
- **Xuất khung 16:9, 9:16, 1:1, 4:5 hoặc kích thước tuỳ chỉnh, chuẩn 1080p.** Mặc định giữ trọn hình và bù nền đen (`--fit pad`); `blur` cho nền mờ ở video dọc; `fill` phủ kín nhưng cắt mép (lệnh báo rõ mất bao nhiêu phần trăm). Nâng 720p lên 1080p chỉ đạt khung chuẩn, không thêm chi tiết, và lệnh có in cảnh báo điều này.
- Đổi khung thì hình được nén lại bằng x264 CRF 18 (đo trên bài giảng thật: VMAF 97/100, khoảng 1/5 thời lượng clip trên Apple Silicon); `--encoder videotoolbox` nhanh hơn nhưng nét kém hơn. Không đổi khung thì hình vẫn giữ nguyên như trước.
- `verify --expect-size 1920x1080` kiểm thêm khung hình của từng clip; `verify --prefix` đối chiếu đúng tên clip đã cắt có tiền tố (trước đây thời lượng bị bỏ qua không báo). Clip lỗi giữa chừng không còn để lại file dở.

## v0.3.0 — 29/10/2026

### mk-video-cutter

**Mới**

- **Skill `mk:video-cutter` — Cắt nhỏ video bài giảng & tự động cân bằng âm thanh:** Gõ `/mk:video-cutter <video> --sheet <file>`. Tự động bóc tách Action Sheet từ Markdown bài giảng, file `PLAN.txt` hoặc CSV; chạy Pre-flight probe khảo sát âm thanh; cắt hàng loạt video con chuyên đề bảo toàn nguyên bản 100% độ nét gốc (`-c:v copy`), tự động cân bằng âm thanh Dual-Mono và chuẩn hóa âm lượng EBU R128 (`-16 LUFS`); chạy nghiệm thu tính toàn vẹn và thời lượng clip con bằng `ffprobe`.

### mk-subtitle

**Mới**

- **Chia buổi học dài thành file con (Quy trình Kaizen):** Hỗ trợ xử lý bản chép lời bài giảng 2–4 tiếng (TXT có mốc đầu dòng `[mm:ss]`, SRT, VTT). Quét tín hiệu rác đầu giờ (mic check, điểm danh, ổn định lớp), giờ nghỉ giải lao, quãng lặng bất thường; lập Bảng chỉ dẫn Editor (Action Sheet) chuẩn 20–30 phút/file con kèm lệnh 🛑 CUT / 🟢 KEEP; bảo toàn 100% ngữ cảnh vấn đáp `[A Hỏi - B Đáp]` và đối thoại Socrates 3 nhịp; xuất khung bài giảng Markdown; xuất phụ đề `.srt` riêng từng file con (được tính lại giờ bắt đầu từ 00:00:00); kiểm tra lỗi bằng lệnh lint máy và tự động tạo dòng tổng kết Kaizen cho nhật ký khoá học.
- **Khảo sát âm thanh & Cắt video con tự động (FFmpeg Stream Copy):** Thêm subcommand `probe-audio` (đo RMS, kiểm tra lệch kênh stereo/mono hoặc điếc một bên tai, đề xuất 3 chế độ `copy`/`balance`/`master`) và subcommand `cut-video` (đọc Action Sheet cắt hàng loạt video con giữ nguyên 100% chất lượng hình ảnh gốc `-c:v copy`, tự động cân bằng âm thanh và đưa về chuẩn -16 LUFS khi cần, hỗ trợ `--dry-run`).

## v0.2.0 — 28/10/2026

### mk-subtitle

**Mới**

- **Skill `mk:subtitle` — phụ đề cho khâu dựng video.** Gõ `/mk:subtitle <file .srt/.vtt>` (kể cả phụ đề tự động của YouTube). Agent đánh dấu từ đệm "à, ừ, ờ, ừm…" và lặp từ thành hai nhóm để bạn duyệt; mã nào được duyệt mới bị xoá khỏi phụ đề và đưa vào danh sách đoạn cắt cho editor (chính xác tới từng từ với phụ đề YouTube). Sau đó chia câu, ngắt dòng theo chuẩn phụ đề, sửa lỗi nhận giọng và thuật ngữ tiếng Việt theo bảng thuật ngữ của repo, dịch sang tiếng Anh cùng mốc thời gian, và tính lại giờ phụ đề cho video đã cắt. Kết quả là một thư mục mới (file gốc giữ nguyên) gồm các file `.srt` dùng được với CapCut, Premiere Pro, DaVinci Resolve, Final Cut Pro và `BAN-GIAO.md` hướng dẫn editor. Cài: `bash ~/.mk-studio/install.sh --global --skill mk-subtitle`.

## v0.1.0 — 20/10/2026

### mk-star

**Mới**

- **Skill `mk:star` — nhật ký STAR.** Gõ `/mk:star` hoặc kể một chuyện, agent đề xuất một trong 5 loại nhật ký (ngày, giải quyết vấn đề A–Z hoặc viết nhanh, đóng gói thành công, kiến tạo tương lai, dẫn dắt người khác), hỏi từng câu theo mẫu và ghi nguyên văn câu trả lời vào `~/nhat-ky-star/`. Có đủ bộ câu hỏi cơ bản/chuyên sâu, 4 case giải mẫu, 28 case luyện tập, 8 dạng tài sản đóng gói. Xem tiến độ: số bài trọn vẹn theo cột mốc 28 / 300 / 1000 / 10000, việc hẹn hôm qua chưa làm, kết quả đến hạn ghi.
- Cài bằng `install.sh` của bộ mk-studio: `gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global`. Thư mục skill cùng tên mà không do `install.sh` tạo thì bị từ chối thay vì bị ghi đè. Installer không ghi xuyên đường tắt (symlink, kể cả `~/.claude/skills`), và `--update` chỉ chạy bản đã phát hành (có tag `vX.Y.Z`).

### mk-exec-review

**Mới**

- **Skill `mk:exec-review` — hội đồng C-level phản biện bài viết.** Gõ `/mk:exec-review <file>` hoặc nói "phản biện bài <file>": agent đọc bài, luật viết của repo, chân dung khách hàng (không có thì hỏi bạn) và bảng thuật ngữ; hỏi bạn phần còn thiếu (người đọc chính, mục tiêu, nơi đăng, từ khoá, thuật ngữ tự đặt, mức sửa); rồi giao **một agent riêng** đóng vai CEO, CFO, CMO, COO, CTO đọc bài bằng mắt người đọc. Báo cáo gồm: chỗ giữ chân và chỗ mất niềm tin của từng vai, dấu hiệu giọng AI, thuật ngữ dùng lệch, SEO / GEO / AEO, ý tưởng cải thiện, và bảng gợi ý đánh mã. Bạn duyệt mã nào thì agent sửa đúng chỗ đó, giữ ý, ví dụ và giọng của bạn; chỗ cần số liệu để ô `[điền: …]`, không bịa. Cài: `bash ~/.mk-studio/install.sh --global --skill mk-exec-review`.
