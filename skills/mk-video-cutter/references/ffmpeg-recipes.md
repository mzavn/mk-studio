# Cẩm Nang Lệnh FFmpeg Cho Cắt Video & Tái Cân Bằng Âm Thanh

Tài liệu tham khảo chuyên sâu các kỹ thuật xử lý video và âm thanh bài giảng bằng FFmpeg, bảo toàn 100% chất lượng hình ảnh gốc và đạt chuẩn âm học phát thanh.

---

## 1. Nguyên Lý "Zero Quality Loss" Với Stream Copy

Cắt ghép video thông thường thường mắc lỗi **re-encode bừa bãi** (giải mã rồi nén lại với bitrate thấp), dẫn đến suy hao thế hệ (**Generation Loss**):
- Chữ trên slide bài giảng bị vỡ nét, nhòe cạnh.
- Màu sắc bị bệt do chuyển đổi không gian màu.
- Mất thời gian CPU/GPU để mã hóa lại.

### Cú pháp Stream Copy (`-c copy`)
```bash
ffmpeg -ss [START] -to [END] -i input.mp4 -c copy output.mp4 -y
```
- **Vị trí `-ss` và `-to` trước `-i`:** FFmpeg dùng cơ chế fast seek nhảy trực tiếp tới keyframe mà không giải mã luồng.
- **Tốc độ:** Xử lý bằng tốc độ I/O ổ đĩa SSD (3000x realtime, 2–3 giây cho file nhiều tiếng).
- **Chất lượng:** Bit-by-bit identical với video nguồn.

---

## 2. Kỹ Thuật Tái Cân Bằng Âm Thanh (Dual-Mono Center)

### Vấn đề thường gặp
Micro mono (cài áo, micro bàn) cắm vào cổng stereo 3.5mm thường chỉ ghi tín hiệu vào kênh Trái (`CH1`) hoặc kênh Phải (`CH2`), làm người nghe qua tai nghe bị **điếc một bên tai**.

### Ma trận FFmpeg Pan Filter
| Nguồn âm thanh | Cú pháp `-af` | Cơ chế xử lý |
|---|---|---|
| Chỉ có tiếng tai Trái | `pan=stereo\|c0=c0\|c1=c0` | Nhân bản CH1 sang cả hai bên |
| Chỉ có tiếng tai Phải | `pan=stereo\|c0=c1\|c1=c1` | Nhân bản CH2 sang cả hai bên |
| **Lệch kênh / Không rõ kênh** | `pan=stereo\|c0=0.5*c0+0.5*c1\|c1=0.5*c0+0.5*c1` | **Dual-Mono Center:** Trộn đều 50% Trái + 50% Phải rồi phát ra giữa hai tai |

> [!TIP]
> Luôn kết hợp `-c:v copy` để giữ nguyên hình ảnh, chỉ re-encode audio luồng âm thanh sang AAC 192k:
> ```bash
> ffmpeg -ss [START] -to [END] -i input.mp4 \
>   -c:v copy \
>   -af "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1" \
>   -c:a aac -b:a 192k output.mp4 -y
> ```

---

## 3. Chuẩn Hóa Âm Lượng Theo Tiêu Chuẩn Quốc Tế EBU R128

Video ghi âm qua Zoom hoặc lớp học trực tuyến thường có âm lượng quá nhỏ ($\text{RMS} < -24\text{ dB}$). Người nghe phải mở volume 100% trên điện thoại/tai nghe vẫn khó nghe.

### Bộ lọc `loudnorm`
Chuẩn hóa độ lớn tích hợp (Integrated Loudness) theo chuẩn phát thanh YouTube/Podcast:
```bash
loudnorm=I=-16:TP=-1.5:LRA=11
```
- `I=-16`: Âm lượng mục tiêu là `-16 LUFS` (chuẩn quốc tế cho web/mobile podcast).
- `TP=-1.5`: True Peak tối đa không vượt quá `-1.5 dBFS` để tránh hiện tượng vỡ tiếng (clipping).
- `LRA=11`: Loudness Range cho bài giảng nói chuyện rõ ràng, đồng đều.

### Lệnh Master Hoàn Chỉnh (Video Copy + Dual-Mono + Loudnorm)
```bash
ffmpeg -ss [START] -to [END] -i input.mp4 \
  -c:v copy \
  -af "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:a aac -b:a 192k output.mp4 -y
```

---

## 4. Tăng Tốc Phần Cứng (Hardware Acceleration)

Khi bắt buộc phải re-encode lại video (ví dụ cần cắt chính xác từng frame không phụ thuộc keyframe, hoặc chèn watermark/bộ lọc hình):

- **macOS Apple Silicon (M1/M2/M3/M4):**
  Dùng VideoToolbox encoder:
  ```bash
  -c:v h264_videotoolbox -b:v 1500k
  ```
- **Linux / Windows với GPU NVIDIA:**
  Dùng NVENC encoder:
  ```bash
  -c:v h264_nvenc -b:v 1500k
  ```
