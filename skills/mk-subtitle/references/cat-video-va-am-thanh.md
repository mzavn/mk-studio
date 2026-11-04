# Cắt Video Con & Cân Bằng Âm Thanh (Video Chunking SOP)

Tài liệu kỹ thuật hướng dẫn tải video nguồn, cắt video bài giảng dài thành các video chuyên đề con từ Bảng chỉ dẫn
Editor (Action Sheet) bằng FFmpeg, bảo toàn nguyên bản 100% chất lượng hình ảnh và cân bằng âm thanh khi cần.

---

## 1. Yêu Cầu Môi Trường & Tải Video Nguồn

- **Hệ điều hành:** macOS (Apple Silicon M1/M2/M3/M4) / Linux / Windows.
- **Công cụ:** `ffmpeg` và `ffprobe` có sẵn trong PATH (`ffmpeg -version` $\ge$ 5.0, khuyến nghị 7.x trở lên); tải
  video cần thêm `yt-dlp`. Thiếu công cụ → script báo cách cài, agent không tự cài.
- **Phần cứng:** Ổ đĩa SSD có dung lượng trống $\ge 1.5 \times$ kích thước video nguồn; RAM tối thiểu 4GB.

**Tải video nguồn từ YouTube** (chỉ khi người dùng yêu cầu, từ đúng link họ đưa):
```bash
python3 <skill>/scripts/subtitle.py fetch-video "<link>" --out "<thư mục video>/<tên>.mp4" \
  [--ref "<video buổi trước>.mp4"] [--format "…"] [--player-client "…"] [--cookies-from-browser chrome]
```
- Mặc định theo chuẩn khoá **720p, 30 khung/giây, H.264 + AAC** để file con các buổi đồng nhất:
  `--format "136+140/bv*[height=720][vcodec^=avc1]+ba[ext=m4a]"` (136 = 720p30 H.264, 140 = tiếng AAC; phần sau `/`
  là dự phòng vì danh sách định dạng có thể khác giữa các lần gọi). Khoá khác chuẩn → đổi `--format`.
- `--player-client` mặc định `web_embedded,default,-android_vr`: client `android_vr` hay bị YouTube trả
  **HTTP 403** và chỉ có 720p60. Vẫn 403 → thử client khác (vd `web`) hoặc nhờ người dùng cập nhật yt-dlp.
- Luôn `--no-overwrites`; tải vào thư mục tạm cạnh file đích rồi mới đặt tên, `--out` đã có → dừng trước khi gọi mạng.
- yt-dlp luôn chạy với `--ignore-config` (bỏ qua `yt-dlp.conf` ở thư mục hiện tại/thư mục nhà — file đó có thể chứa
  `--exec` hay cookies) và `--no-plugin-dirs` khi bản cài có tuỳ chọn này (bỏ qua plugin cục bộ).
- Sau khi tải, script `ffprobe` in độ phân giải, khung/giây, codec, thời lượng. Có `--ref` → so với video mẫu; dòng
  `LỆCH:` (thoát 1) → báo người dùng trước khi cắt, file đã tải vẫn giữ.
- Video riêng tư/cần đăng nhập → `--cookies-from-browser` chỉ khi người dùng đồng ý.

---

## 2. Chiến Lược Chất Lượng: "Giữ Nguyên Hoặc Tốt Hơn Source Gốc"

Không re-encode video bừa bãi để tránh suy hao thế hệ (Generation Loss). Quy trình tách biệt xử lý Video và Audio:
- **Video Stream:** Luôn sử dụng `-c:v copy` (Stream Copy) khi cắt phân đoạn. Hình ảnh được trích xuất trực tiếp
  từ các gói bitstream H.264 gốc, không giải mã, không nén lại, bảo toàn 100% độ phân giải, bitrate và màu sắc gốc.
  Tốc độ xử lý siêu tốc (vài giây cho video nhiều tiếng).
- **Audio Stream:** Có 3 chế độ xử lý tùy theo tình trạng âm thanh của video nguồn.

---

## 3. Khảo Sát Âm Thanh Trước Khi Cắt (Pre-Flight Audio Check)

Trước khi cắt hàng loạt, đo âm thanh **cả file** (một lần chạy, khoảng 10–20 giây máy cho video 2 giờ):
```bash
python3 <skill>/scripts/lecture.py probe-audio <video_nguồn.mp4> [--course-dir <thư mục file con>] \
  [--sample-time 00:15:00]... [--duration 30]
```
Một mẫu 30 giây dễ rơi vào chỗ ngừng nói (−54 dB, −71 dB) và khuyên nhầm `master` dù cả file vẫn đủ to — vì vậy
khuyến nghị chỉ dựa trên số đo cả file. `--sample-time` (lặp được) chỉ in thêm để tham khảo; mẫu có kênh to nhất dưới
−45 dB bị ghi "gần im lặng, bỏ qua".

### Tiêu chí chẩn đoán tự động
- **Độ to tích hợp cả file** (`ebur128`, LUFS):
  - $\ge -24$ LUFS: âm lượng đủ (bài giảng thu tốt thường khoảng −19 LUFS).
  - $< -24$ LUFS: âm lượng quá nhỏ (người nghe phải mở volume tối đa mới nghe được).
- **Độ lệch 2 tai** ($\Delta = |\text{RMS}_L - \text{RMS}_R|$, `astats` cả file):
  - $\Delta < 4\text{ dB}$: Hai tai cân bằng.
  - $\Delta \ge 4\text{ dB}$: Lệch tai rõ rệt.
  - Một bên $< -55\text{ dB}$ trong khi bên kia $> -45\text{ dB}$: Bị "điếc một bên tai" (Single-ear mono).
- **Khuyến nghị:** nhỏ → `master`; không nhỏ mà lệch → `balance`; còn lại → `copy`.
- **Sát ngưỡng:** độ to trong khoảng −25 … −23 LUFS (±1 LU) → `Cảnh báo`: chế độ có thể lật giữa `copy` và `master`
  chỉ vì sai số đo — giữ chế độ khoá hoặc hỏi người dùng, không tự đổi.
- **Một chế độ cho cả khoá:** các buổi dùng cùng chế độ để file con nghe đều nhau. `--course-dir` (và `cut-video
  --mode auto` với thư mục xuất đã có file) đọc một file con có sẵn để đoán chế độ khoá: tiếng AAC ~192 kb/s và độ to
  ~−16 LUFS → `master`; AAC ~192 kb/s → `balance`; tiếng giữ nguyên → `copy`. Khuyến nghị là chế độ khoá; số đo buổi
  này khác → `Cảnh báo`, báo số đo, hỏi người dùng trước khi đổi. Luật Kaizen ghi chế độ khoá → truyền thẳng `--mode`.

---

## 4. Ba Chế Độ Sản Xuất (Production Modes)

### Mode 1 — Pure Stream Copy (`copy`)
Áp dụng khi âm thanh gốc đã cân bằng tốt và âm lượng đủ lớn.
- Video và Audio đều copy trực tiếp, không re-encode:
  ```bash
  ffmpeg -ss [BẮT_ĐẦU] -to [KẾT_THÚC] -i input.mp4 -c copy -n output.mp4
  ```

### Mode 2 — Cân Bằng Kênh Dual-Mono (`balance`)
Áp dụng khi video gốc bị điếc tai trái/phải hoặc lệch âm lượng giữa 2 bên.
- Video giữ nguyên (`-c:v copy`), âm thanh áp dụng ma trận Pan gộp 50% Trái + 50% Phải rồi phát đều ra 2 tai:
  ```bash
  ffmpeg -ss [BẮT_ĐẦU] -to [KẾT_THÚC] -i input.mp4 \
    -c:v copy \
    -af "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1" \
    -c:a aac -b:a 192k \
    -n output.mp4
  ```

### Mode 3 — Audio Mastering & Chuẩn Hóa EBU R128 (`master`)
Áp dụng khi video bài giảng (Zoom/micro cá nhân) có âm lượng cả file quá nhỏ hoặc vừa nhỏ vừa lệch tai.
- Video giữ nguyên (`-c:v copy`), âm thanh vừa cân bằng 2 tai vừa kích âm lượng lên chuẩn phát thanh quốc tế `-16 LUFS`:
  ```bash
  ffmpeg -ss [BẮT_ĐẦU] -to [KẾT_THÚC] -i input.mp4 \
    -c:v copy \
    -af "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,loudnorm=I=-16:TP=-1.5:LRA=11" \
    -c:a aac -b:a 192k \
    -n output.mp4
  ```

---

## 5. Cắt Video Hàng Loạt Bằng Script

Lệnh tự động đọc kế hoạch từ file `PLAN.txt` (tương thích Action Sheet) và cắt video con hàng loạt:
```bash
python3 <skill>/scripts/lecture.py cut-video <video_nguồn.mp4> --plan $T/plan.txt \
  --prefix "Buổi 1" --out-dir ./FINAL/ [--name "{prefix}_P{n:02} - {title}"] [--label "{prefix} · P{n:02}"] \
  --mode <chế độ khoá> [--dry-run]
```
- `--mode auto` chỉ cho buổi đầu: đo âm thanh cả file như §3, thư mục xuất đã có file con thì giữ chế độ khoá.
- **Một nguồn tên:** `plan`, `split` (cột *Tên file con*, SRT con) và `cut-video` dùng cùng tham số `--name`
  (luật Kaizen → truyền theo luật, không hỏi); không có `--name` thì suy từ file video có sẵn (`--video-dir` ở
  `plan`/`split`, `--out-dir` ở `cut-video`); vẫn không có → mặc định `{prefix}-P{n} - {title}`.
  - Mẫu nhận `{prefix}`, `{n}`, `{code}`, `{title}`. `{n:02}` → số phần 2 chữ số, ca vấn đáp con giữ đuôi:
    `P1` → `P01`, `P5.1` → `P05.1`; `{code}` → mã nguyên (`P5.1`).
  - Mẫu phải có `{n}` hoặc `{code}` (để không trùng tên) và không chứa `\ / : * ? " < > |`.
  - Suy quy ước: bỏ phiếu theo cả kiểu (dấu nối, độ rộng số, gạch giữa), lấy đúng kiểu nhiều file nhất (dòng
    `Mẫu tên: … (suy từ N file có sẵn …)`; nhiều kiểu → `Cảnh báo`); hai kiểu ngang nhau → dừng, hỏi rồi truyền `--name`.
  - Tiêu đề và tiền tố được làm sạch ở mọi đường (kể cả mặc định): `:` `/` `\` `|` → ` - `; bỏ `?` `*` `"` `<` `>`
    (vd `Hỏi Đáp: Vận Số?` → `Buổi 1-P5.1 - Hỏi Đáp - Vận Số.mp4`; với mẫu khoá → `Buổi 1_P05.1 - Hỏi Đáp - Vận Số.mp4`).
  - Nhãn hiển thị (tiêu đề `### 🎬`, mục lục) mặc định `Buổi 1:P1`; `--label "{prefix} · P{n:02}"` → `Buổi 1 · P01`
    (nhãn không chứa `[`, `]`, `|`, `*` hay dấu backtick). `lint` cần cùng `--label`.
- **Kiểm trước khi cắt** (kể cả `--dry-run`): tên trùng file có sẵn hoặc trùng nhau → liệt kê hết, dừng; phần nào kết
  thúc sau thời lượng video nguồn (`ffprobe`) → `LỖI`, dừng — kế hoạch không khớp video này.
- **Kiểm sau khi cắt:** mỗi phần cắt vào thư mục tạm trong `--out-dir`, `ffprobe` kiểm thời lượng (±1 giây so kế
  hoạch, từng luồng), có luồng hình và luồng tiếng (khi nguồn có tiếng); qua mới đặt tên thật (hard link, không ghi
  đè; ổ không có hard link → tạo mới rồi chép). Hỏng → `LỖI`, không giao dưới tên thật, thoát 1; các phần trước đó đã
  kiểm vẫn giữ. Dòng `OK: <tên> (giây, hình + tiếng)` cho mỗi file đã giao. FFmpeg chạy với `-n`.
