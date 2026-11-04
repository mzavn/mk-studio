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

Video ghi âm qua Zoom hoặc lớp học trực tuyến thường có âm lượng quá nhỏ (độ to tích hợp cả file $< -24\text{ LUFS}$). Người nghe phải mở volume 100% trên điện thoại/tai nghe vẫn khó nghe.

### Bảng quyết định của `cutter.py probe` (đo cả file)
Một lượt ffmpeg trên toàn bộ file: `-af ebur128=framelog=quiet,astats` (astats **không** `reset`: `reset=1` chỉ báo khung âm cuối, không phải cả đoạn). Không dựa vào một mẫu 30 giây: mẫu có thể rơi vào chỗ ngừng nói và khuyên nhầm `master`.

| Số đo cả file | Chế độ |
|---|---|
| Độ to tích hợp $< -24$ LUFS | `master` |
| Không nhỏ, nhưng Δ Trái/Phải $\ge 4$ dB hoặc một kênh chết (< −55 dB trong khi kênh kia > −45 dB) | `balance` |
| Còn lại | `copy` |

- Cả file trong ±1 LU quanh −24 LUFS → script in `Cảnh báo: … sát ngưỡng`; đối chiếu chế độ buổi trước rồi mới chốt.
- `--sample-time` (lặp được) chỉ in số đo mẫu để tham khảo; mẫu có kênh to nhất < −45 dB bị coi là im lặng và bỏ qua.
- Giữ **một chế độ cho cả khoá** để các file con nghe đều nhau; muốn đổi giữa khoá → hỏi người dùng.

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

## 4. Đổi Khung Hình (Cắt Viền, Tỉ Lệ, 1080p)

Đổi khung bắt buộc mã hoá lại hình; `cutter.py` dựng chuỗi lọc từ `--crop/--aspect/--res/--size/--fit` (cách chọn: `references/khung-hinh.md`). Ví dụ (dữ liệu giả) nội dung 1110×622 tại (80,58) → 1920×1080:

| `--fit` | Chuỗi lọc sau `crop=1110:622:80:58,` |
|---|---|
| `pad` | `scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1` |
| `fill` | `scale=1920:1080:force_original_aspect_ratio=increase:…:flags=lanczos,crop=1920:1080,setsar=1` |
| `blur` | `split[a][b];[a]scale=…increase,crop=…,boxblur=20:2[bg];[b]scale=…decrease…[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1` |

`--enhance` thêm hai khúc vào chuỗi trên (vị trí có lý do):
```text
deblock=filter=strong:block=8,hqdn3d=1.5:1.5:3:3,crop=…,scale=…:flags=lanczos,cas=strength=0.6,pad=…
```
- `deblock` + `hqdn3d` đứng **trước** `crop`: khối nén 8×8 nằm theo lưới của khung gốc; cắt viền trước sẽ lệch lưới.
- `cas` (làm nét theo độ tương phản) đứng **sau** `scale`, **trước** `pad`/nền mờ: làm nét đúng phần nội dung đã phóng, không đụng nền.

Bộ mã hoá:
```bash
-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -tag:v avc1 -movflags +faststart   # mặc định
-c:v h264_videotoolbox -q:v 65 -pix_fmt yuv420p -tag:v avc1                               # --encoder videotoolbox (macOS)
```
- `-ss`/`-to` đặt trước `-i`: khi mã hoá lại, ffmpeg cắt chính xác tới khung hình (không phụ thuộc keyframe như stream copy).
- Số đo tốc độ và chất lượng: `references/khung-hinh.md` §5.
