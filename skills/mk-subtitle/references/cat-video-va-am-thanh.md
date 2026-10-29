# Cắt Video Con & Cân Bằng Âm Thanh (Video Chunking SOP)

Tài liệu kỹ thuật hướng dẫn cắt video bài giảng dài thành các video chuyên đề con từ Bảng chỉ dẫn Editor (Action Sheet)
bằng FFmpeg, bảo toàn nguyên bản 100% chất lượng hình ảnh và tự động cân bằng âm thanh.

---

## 1. Yêu Cầu Môi Trường

- **Hệ điều hành:** macOS (Apple Silicon M1/M2/M3/M4) / Linux / Windows.
- **Công cụ:** `ffmpeg` và `ffprobe` có sẵn trong PATH (`ffmpeg -version` $\ge$ 5.0, khuyến nghị 7.x trở lên).
- **Phần cứng:** Ổ đĩa SSD có dung lượng trống $\ge 1.5 \times$ kích thước video nguồn; RAM tối thiểu 4GB.

---

## 2. Chiến Lược Chất Lượng: "Giữ Nguyên Hoặc Tốt Hơn Source Gốc"

Không re-encode video bừa bãi để tránh suy hao thế hệ (Generation Loss). Quy trình tách biệt xử lý Video và Audio:
- **Video Stream:** Luôn sử dụng `-c:v copy` (Stream Copy) khi cắt phân đoạn. Hình ảnh được trích xuất trực tiếp
  từ các gói bitstream H.264 gốc, không giải mã, không nén lại, bảo toàn 100% độ phân giải, bitrate và màu sắc gốc.
  Tốc độ xử lý siêu tốc (vài giây cho video nhiều tiếng).
- **Audio Stream:** Có 3 chế độ xử lý tùy theo tình trạng âm thanh của video nguồn.

---

## 3. Khảo Sát Âm Thanh Trước Khi Cắt (Pre-Flight Audio Check)

Trước khi cắt hàng loạt, chạy lệnh khảo sát âm thanh 15–30 giây mẫu để xác định tình trạng kênh và độ lớn:
```bash
python3 <skill>/scripts/lecture.py probe-audio <video_nguồn.mp4> [--sample-time 00:15:00]
```

### Tiêu chí chẩn đoán tự động
- **Độ lệch 2 tai ($\Delta = |\text{RMS}_L - \text{RMS}_R|$):**
  - $\Delta \le 3\text{ dB}$: Hai tai cân bằng tốt.
  - $\Delta \ge 4\text{ dB}$: Lệch tai rõ rệt.
  - Một bên $< -55\text{ dB}$ trong khi bên kia $> -45\text{ dB}$: Bị "điếc một bên tai" (Single-ear mono).
- **Độ lớn trung bình ($\text{RMS}_{\text{avg}}$):**
  - $\text{RMS} \ge -24\text{ dB}$: Âm lượng vừa vặn.
  - $\text{RMS} < -24\text{ dB}$: Âm lượng quá nhỏ (người nghe phải mở volume tối đa mới nghe được).

---

## 4. Ba Chế Độ Sản Xuất (Production Modes)

### Mode 1 — Pure Stream Copy (`copy`)
Áp dụng khi âm thanh gốc đã cân bằng tốt và âm lượng đủ lớn.
- Video và Audio đều copy trực tiếp, không re-encode:
  ```bash
  ffmpeg -ss [BẮT_ĐẦU] -to [KẾT_THÚC] -i input.mp4 -c copy output.mp4 -y
  ```

### Mode 2 — Cân Bằng Kênh Dual-Mono (`balance`)
Áp dụng khi video gốc bị điếc tai trái/phải hoặc lệch âm lượng giữa 2 bên.
- Video giữ nguyên (`-c:v copy`), âm thanh áp dụng ma trận Pan gộp 50% Trái + 50% Phải rồi phát đều ra 2 tai:
  ```bash
  ffmpeg -ss [BẮT_ĐẦU] -to [KẾT_THÚC] -i input.mp4 \
    -c:v copy \
    -af "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1" \
    -c:a aac -b:a 192k \
    output.mp4 -y
  ```

### Mode 3 — Audio Mastering & Chuẩn Hóa EBU R128 (`master`)
Áp dụng khi video bài giảng (Zoom/micro cá nhân) có âm lượng quá nhỏ hoặc vừa nhỏ vừa lệch tai.
- Video giữ nguyên (`-c:v copy`), âm thanh vừa cân bằng 2 tai vừa kích âm lượng lên chuẩn phát thanh quốc tế `-16 LUFS`:
  ```bash
  ffmpeg -ss [BẮT_ĐẦU] -to [KẾT_THÚC] -i input.mp4 \
    -c:v copy \
    -af "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,loudnorm=I=-16:TP=-1.5:LRA=11" \
    -c:a aac -b:a 192k \
    output.mp4 -y
  ```

---

## 5. Cắt Video Hàng Loạt Bằng Script

Lệnh tự động đọc kế hoạch từ file `PLAN.txt` (tương thích Action Sheet) và cắt video con hàng loạt:
```bash
python3 <skill>/scripts/lecture.py cut-video <video_nguồn.mp4> --plan $T/plan.txt \
  --prefix "Buổi 1" --out-dir ./FINAL/ [--mode auto|copy|balance|master]
```
- Khi dùng `--mode auto` (mặc định): Script tự động chạy Pre-flight probe trước, nếu âm lượng nhỏ hoặc lệch tai
  sẽ chọn Mode 3 hoặc Mode 2, nếu âm thanh hoàn hảo sẽ chạy Mode 1 để tối đa tốc độ.
- Tên tệp xuất ra được tự động dọn sạch ký tự cấm: `Buổi 1_P01 - <Tiêu đề>.mp4`.
- Sau khi cắt, script tự động chạy `ffprobe` kiểm tra thời lượng và tính toàn vẹn của từng clip con.
