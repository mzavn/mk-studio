# Nhật ký thay đổi

Mỗi bản có số dạng `X.Y.Z` (chung cho cả bộ skill):

- **Số cuối (Z)** tăng: sửa lỗi nhỏ, cách dùng không đổi.
- **Số giữa (Y)** tăng: có thêm tính năng; cập nhật xong dùng tiếp bình thường.
- **Số đầu (X)** tăng: cập nhật xong bạn cần làm thêm một bước — bản đó sẽ ghi rõ bước gì.

Cập nhật: `bash ~/.mk-studio/install.sh --update`.

## Chưa phát hành

Dự kiến: v0.2.0

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
