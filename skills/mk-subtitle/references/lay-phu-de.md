# Lấy phụ đề khi người dùng chưa có file SRT/VTT

Đọc khi người dùng đưa link YouTube hoặc chỉ có file video. `S` = `python3 <skill>/scripts/subtitle.py`.

## 1. Thứ tự nguồn

| Ưu tiên | Người dùng có | Làm gì | Ghi chú cho skill |
|---|---|---|---|
| 1 | File SRT/VTT | dùng luôn | tuỳ file |
| 2 | Link YouTube (video đã đăng, kể cả không công khai) | `S fetch` (§2) | bản tự động gốc có **mốc từng từ** — cắt đúng chỗ, nhưng có thể đã lược bớt âm đệm (§2) |
| 3 | Chỉ có file video, chưa đăng YouTube | người dùng **tự cài** công cụ nhận giọng (§3), hoặc tự đăng không công khai rồi quay lại mục 2 | mốc theo câu; tên riêng, từ Hán Việt hay sai |

Video đã có trên YouTube thì ưu tiên mục 2, kể cả khi người dùng có sẵn file video: vài giây, không tốn máy, có mốc từng từ. Người dùng có bản chép lời `.txt` sao từ trang YouTube (mốc theo đoạn khoảng 30 giây) mà có link → đề xuất tải lại bằng `fetch`.

## 2. Tải phụ đề YouTube — `S fetch`

```bash
S fetch "<link YouTube>" --out-dir <thư mục> [--name <tên>] [--lang vi] [--kind any|manual|auto] \
  [--cookies-from-browser chrome] [--allow-translation]
```

- Cần `yt-dlp` trên máy; chưa có → script báo cách cài (`brew install yt-dlp` hoặc `pip install yt-dlp`). Hỏi người dùng trước khi cài.
- `<thư mục>`: thư mục người dùng chỉ định, không nói thì thư mục làm việc hiện tại. `--name`: tên ngắn người dùng đặt; chưa có → chạy không `--name` (tên = mã video), dòng `Video:` in tiêu đề để đặt tên cho các bước sau.
- Chỉ tải phụ đề, **không tải video**. Chỉ nhận link trỏ tới **một video** (`watch?v=`, `youtu.be/`, `/shorts/`, `/live/`; thiếu `https://` cũng được); link playlist, kênh bị từ chối. Từ chối ghi đè trước khi gọi mạng.
- `--kind any` (mặc định): lấy phụ đề **chủ kênh tải lên** nếu có; không có thì lấy phụ đề **tự động gốc** (`vi-orig`). `--kind auto`: buộc lấy bản tự động gốc (mốc từng từ) — dùng khi bản tải lên đã bị biên tập mà cần cắt từ đệm.
- **Bản dịch:** script đọc ngôn ngữ nói của video (`Video: … · ngôn ngữ nói: en`). Khác `--lang` → dừng, vì phụ đề tiếng Việt khi đó là bản dịch: không làm luồng từ đệm, chuẩn hoá, tính lại giờ trên bản dịch. Muốn lời gốc → `--lang en` (dịch sang Việt là việc ngoài skill; skill chỉ dịch Việt → Anh). Chỉ cần bản dịch để dùng nguyên → `--allow-translation` (chỉ lấy bản chủ kênh tải lên; dòng `Nguồn` ghi `BẢN DỊCH`). Bản dịch hay có cue ghi tên người dịch ở đầu (`Translator: …`) — báo người dùng.
- Phụ đề tự động chỉ nhận bản gốc `<lang>-orig`; bản `vi` tự động không kèm `-orig` là dịch máy → không dùng.
- **Âm đệm:** phụ đề tự động YouTube có lúc lược bớt "à, ừ, ờ" (tuỳ người nói, tuỳ video). `S scan` ra nhóm A = 0 **không có nghĩa** video sạch: báo người dùng, đề nghị nghe thử vài đoạn; cần cắt kỹ thì dùng công cụ ở §3.
- Video **riêng tư** hoặc cần đăng nhập: script gợi ý `--cookies-from-browser chrome` (hoặc `safari`, `firefox`…) — yt-dlp đọc phiên đăng nhập YouTube trên trình duyệt đó. Hỏi người dùng trước, nói rõ việc này.

Dòng in ra: `Video: <tiêu đề> · ngôn ngữ nói: …`, `Nguồn: …`, `Loại: có mốc từng từ` hoặc `mốc theo câu`, `→ <đường dẫn>`. File ra `<thư mục>/<tên>.<lang>.vtt`, dùng ngay cho `S scan` (mode phụ đề) hoặc `L scan` (mode chia buổi).

## 3. Chỉ có file video: người dùng tự tạo phụ đề

Skill **không có sẵn** và **không tự cài** công cụ nhận giọng. Đưa người dùng hai lựa chọn, họ tự quyết:

**A. Đăng YouTube ở chế độ không công khai** (unlisted), chờ YouTube tạo phụ đề tự động (thường vài phút tới vài giờ với video dài), rồi dùng `fetch` như §2. Không cần cài gì; đổi lại video nằm trên YouTube — nội dung nội bộ/nhạy cảm thì cân nhắc.

**B. Nhận giọng trên máy bằng whisper.cpp** (miễn phí, chạy tốt trên Mac Apple Silicon, không gửi âm thanh ra ngoài):

1. Cài: `brew install whisper-cpp ffmpeg` (kiểm bằng `whisper-cli -h`). Windows/Linux: bản dựng sẵn hoặc tự build theo trang whisper.cpp.
2. Tải mô hình một lần, vd `large-v3-turbo` (khoảng 1,6 GB):
   ```bash
   mkdir -p ~/whisper-models
   curl -L -o ~/whisper-models/ggml-large-v3-turbo.bin \
     https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
   ```
3. Thử 5 phút trước (đo tốc độ, xem chất lượng):
   ```bash
   ffmpeg -t 300 -i <video> -vn -ac 1 -ar 16000 -c:a pcm_s16le thu-5-phut.wav
   whisper-cli -m ~/whisper-models/ggml-large-v3-turbo.bin -l vi -f thu-5-phut.wav -osrt -of thu-5-phut.vi
   ```
4. Ưng thì chạy cả video (bỏ `-t 300`, đổi tên file): ra `<tên>.vi.srt` → đưa vào skill như file SRT bình thường.

Lựa chọn khác: **PhoWhisper** (VinAI, huấn luyện riêng cho tiếng Việt, cài qua Python, phức tạp hơn): <https://github.com/VinAIResearch/PhoWhisper>.

Phải nói trước với người dùng (lựa chọn B):
- **Tên riêng, từ Hán Việt hay bị nghe sai** (tên quẻ, tên người) → bước chuẩn hoá thuật ngữ của skill sửa được nếu có bảng thuật ngữ (`--glossary`).
- **Đoạn im lặng dài** (giờ giải lao, mất tiếng đầu buổi) Whisper hay **bịa câu lặp đi lặp lại** → cắt bỏ đoạn đó trước, hoặc kiểm kỹ các đoạn đó.
- Mốc theo câu, không có mốc từng từ: cắt từ đệm giữa câu chỉ là ước lượng (`references/tu-dem.md` §4).
- Tốn giờ máy: buổi học 2–3 tiếng có thể mất từ vài chục phút đến hơn một giờ, tuỳ mô hình và máy — bước thử 5 phút cho số thật.

Nguồn: [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [whisper.cpp](https://github.com/ggml-org/whisper.cpp) · [mô hình whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp) · [PhoWhisper](https://github.com/VinAIResearch/PhoWhisper).
