# Nhật ký thay đổi

Mỗi bản có số dạng `X.Y.Z` (chung cho cả bộ skill):

- **Số cuối (Z)** tăng: sửa lỗi nhỏ, cách dùng không đổi.
- **Số giữa (Y)** tăng: có thêm tính năng; cập nhật xong dùng tiếp bình thường.
- **Số đầu (X)** tăng: cập nhật xong bạn cần làm thêm một bước — bản đó sẽ ghi rõ bước gì.

Cập nhật: `bash ~/.mk-studio/install.sh --update`.
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
