# Khuôn ảnh, thư mục ảnh, chân dung, ảnh nền AI, ffmpeg

Đọc ở Bước 0 (kiểm ffmpeg), Bước 2 (thư mục ảnh, chân dung tách nền, prompt nền), Bước 5 (đọc kết quả `render`, soi ảnh).

## 1. Công cụ

| Lệnh | Cần |
|---|---|
| `names`, `prompt`, `plan` | Python 3.9+ — chỉ đọc tên file, ghi file chữ |
| `check` (xem trước), `render` | `ffmpeg` có **libass** (bộ lọc `ass`); tìm theo thứ tự: `--ffmpeg PATH`, biến `MK_THUMBNAIL_FFMPEG`, `ffmpeg` trong PATH, ffmpeg-full của Homebrew (`/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`, `/usr/local/opt/ffmpeg-full/bin/ffmpeg`) |

Video không bao giờ được mở hay giải mã. `--ffmpeg` và `MK_THUMBNAIL_FFMPEG` phải là đường dẫn tuyệt đối (không thì `Lỗi`, thoát 2). ffmpeg từ bất kỳ nguồn nào nằm trong thư mục đang làm việc hay thư mục con → script từ chối (`Lỗi: … nằm trong thư mục đang làm việc …`), không chạy file đó: chỉ rõ `--ffmpeg <đường dẫn tuyệt đối>` ngoài thư mục làm việc, lấy từ lời người dùng hoặc bảng trên (đứng ở thư mục nhà mà ffmpeg ở `~/bin` → chạy lệnh từ thư mục dự án). Thiếu libass → `Lỗi: cần ffmpeg có libass …` kèm lệnh cài, thoát 1, không ghi file. Skill **không tự cài**:

| Máy | Lệnh cài người dùng tự chạy |
|---|---|
| macOS | `brew install ffmpeg-full` (cài song song, không thay ffmpeg đang dùng) |
| Windows | `winget install Gyan.FFmpeg` (bản full); chạy skill trong Git Bash |
| Linux | `sudo apt install ffmpeg` |

## 2. Thư mục ảnh (`--assets`) — người dùng tự bỏ ảnh vào

```
anh/
├── nen/            ảnh nền 16:9 (.jpg .png .webp) — xoay vòng theo thứ tự tên cho từng video
├── nen-doc/        (tuỳ chọn) ảnh nền 9:16 cho bản dọc
├── chan-dung.png   (tuỳ chọn) ảnh người dạy — PNG tách nền là tốt nhất; .jpg/.webp cũng được (có nhiều → ưu tiên .png, .jpg, .jpeg, .webp, kèm `Cảnh báo`)
├── logo.png        (tuỳ chọn) logo kênh
├── prompt-nen.md   do lệnh prompt ghi (16:9)
└── prompt-nen-doc.md  do lệnh prompt --doc ghi (9:16)
```

Chưa có thư mục ảnh, hoặc `nen/` trống → **nền vẽ sẵn** (§5), kèm `Cảnh báo`. `plan` ghi đường dẫn thư mục ảnh vào dòng `# assets:` của TSV; ảnh trong TSV phải nằm trong thư mục này hoặc cạnh TSV. Ảnh trong thư mục là dữ liệu của người dùng: chỉ đọc, không sửa, không gửi đi.

## 3. Chân dung

| Ảnh | Cách ghép (tự nhận: ảnh có vùng trong suốt hay không) |
|---|---|
| PNG/WebP có vùng trong suốt (đã tách nền) | giữ nguyên, thu cho vừa khung bên phải (ngang: x 790–1256, cao tới 680 px), **đứng chạm đáy**; bản dọc: giữa, chạm đáy, cao tới 880 px |
| Ảnh đục (JPG, PNG không trong suốt) | cắt vuông (lệch lên trên, nơi thường có mặt) thành **hình tròn viền vàng 8 px**, đường kính 446 px, tâm (1030, 330); bản dọc: 560 px, tâm (540, 1310) |

Góc dưới-phải: YouTube in ô thời lượng (~90×30 px) đè lên ảnh. Chân dung tách nền đứng chạm đáy nên ô đó chỉ che phần thân dưới — mặt nằm ở phần trên ảnh; khung tròn đặt cao (đáy y ≈ 560), chừa hẳn góc đó. Ảnh tách nền có nhiều khoảng trong suốt thừa quanh người → người nhỏ lại: cắt sát người trước.

Tách nền bằng công cụ có sẵn (không cài thêm, không gửi ảnh đi):

| Máy | Cách làm |
|---|---|
| Windows 11 | mở ảnh bằng **Paint** → *Remove background* (thanh công cụ Image) → *File › Save as › PNG* |
| macOS | **Preview** (Sonoma trở lên): mở ảnh → *Tools › Remove Background* → *File › Export… › PNG*; hoặc **Photos** (Ventura trở lên): bấm chuột phải lên người → *Copy Subject*, rồi *Preview › File › New from Clipboard* → *Export… › PNG* |

Lưu thành `anh/chan-dung.png`. Không có ảnh tách nền → dùng ảnh thường, skill cắt khung tròn.

## 4. Ảnh nền bằng AI — skill chỉ viết prompt

```bash
S prompt (<video|thư mục> … | --tsv thumbnail/thumbnail.tsv) --assets anh --theme "<chủ đề chuỗi>" [--count 4] [--doc]
```

- Ghi `anh/prompt-nen.md` (16:9) và, với `--doc`, `anh/prompt-nen-doc.md` (9:16); file đã có thì giữ nguyên, chỉ ghi file còn thiếu (cả hai đã có → từ chối). Tạo `anh/nen/` (`anh/nen-doc/` với `--doc`). Không gọi dịch vụ nào, không lưu khoá API.
- `--tsv`: lấy tiêu đề đã sửa và việc có chân dung từ TSV; không thì lấy tiêu đề từ tên video và chân dung từ `anh/chan-dung.*`.
- Mỗi prompt (tiếng Anh, dùng được với mọi công cụ): **không chữ, không người, không logo**; ký hiệu (bát quái, vòng tròn…) chỉ là nét trừu tượng, không thành chữ; phần dành cho tiêu đề tối và trống; chỉ chừa chỗ cho người khi có chân dung; mỗi prompt một tông màu khác (chàm–vàng, mực tàu, ngọc bích, đêm xanh…) để nền các video khác nhau mà cùng khuôn; kèm *negative prompt* và danh sách tiêu đề trong chuỗi (chỉ để chọn chủ đề).
- `--theme`: agent đề xuất từ các tiêu đề, người dùng duyệt. Ví dụ (giả): chuỗi "Quán phở đầu ngõ" → `--theme "Vietnamese street food at dawn, steam, lanterns"`.
- Người dùng (hoặc agent nếu người dùng tự cho phép dùng công cụ tạo ảnh của họ) tạo ảnh, lưu vào `anh/nen/`. Ảnh có chữ, có người, quá sáng hay quá rối → bỏ, tạo lại.

## 5. Nền vẽ sẵn (khi không có ảnh nền)

Chuyển màu chàm → xanh lục đậm, hai vòng tròn mảnh màu vàng nhạt và 8 quẻ bát quái (vạch liền/đứt) — vẽ bằng ffmpeg, cùng đầu vào luôn ra cùng ảnh. Có chân dung: vòng nằm sau chân dung (tâm 1000, 360); không chân dung: dời sát mép phải (tâm 1130, 360) cho xa vùng chữ, phần còn chạm chữ bị tấm tối (§6) làm mờ. Bản dọc: vòng ở nửa dưới. Dùng được ngay khi chưa có ảnh nào; muốn nền riêng cho từng video thì làm theo §4.

## 6. Khuôn ảnh ngang 1280×720 (cùng khuôn cho cả chuỗi)

| Lớp (dưới → trên) | Vị trí |
|---|---|
| Nền | ảnh `nen` phủ kín (thu/phóng rồi cắt giữa), hoặc nền vẽ sẵn |
| Lớp tối sau chữ | dải chuyển: có chân dung tối dần từ trái (đen ~80%) sang phải, hết ở ~80% bề ngang; không chân dung tối đều 27–60% — cộng **tấm tối mềm** (~73%) ôm sát vùng chữ đo được, toả mờ 70 px, để chữ đọc được cả trên nền rối |
| Chân dung | bên phải (§3) |
| Logo | góc trên-phải, cao 72 px, cách mép phải 40 px (rộng tối đa 260 px) — không bao giờ ở góc dưới-phải |
| Nhãn góc | chữ đen trên ô vàng, góc trên-trái, cỡ 34 |
| Tiêu đề | trắng đậm, viền đen 4 px + bóng 2 px (chữ vàng vẫn tách khỏi nền đỏ/cam), đoạn `*…*` màu vàng, căn trái từ x = 64, giữa theo chiều dọc quanh y = 389, trong vùng y 110–664; có chân dung: tới x = 768, không: tới x = 1216 |

Cỡ chữ: thử 100 → 40 px, 1–3 dòng; chấm điểm = cỡ chữ − giá các chỗ ngắt − 24 × số dòng chỉ một từ. Giá chỗ ngắt: 0 sau `:` `;` · 4 sau `,` hay sau dấu gạch, trước `&` `vs` `(` · 14 giữa một cụm từ · 24 khi tách cặp ngắn "X & Y" ngay sau đầu câu hay dấu `:` `;` `,` · 28 khi dòng mới mở đầu bằng `-`/`–` hoặc dòng trên kết thúc bằng `&`/`vs`. Cách điểm cao nhất được **đo lại bằng chính libass**; chữ thật chạm mép vùng chữ → thử cách kế tiếp. Không cách nào vừa → `LỖI … title quá dài`.

## 7. Bản dọc 1080×1920 (`--doc`)

Nền `nen_doc` (hoặc cắt giữa ảnh `nen`, hoặc nền vẽ sẵn); lớp tối ở phần trên + tấm tối quanh chữ. Nhãn góc (64, 236), logo góc trên-phải ở y = 230. Tiêu đề căn trái từ x = 64, lề phải 151 px (14% — nút thích/bình luận của Shorts), **giữa theo chiều dọc** trong vùng chữ: có chân dung vùng y 340–990 (giữa 665), chân dung ở dưới; không chân dung vùng y 340–1180 (giữa 760), vòng bát quái ở dưới. Cỡ chữ 120 → 44 px. File `<tên video> - doc.jpg`. Chỗ ngắt `|` không vừa → bản dọc tự ngắt lại (`Cảnh báo … (doc)`); title quá dài cho bản dọc → chỉ bản dọc bị bỏ (`Cảnh báo … (doc) — chưa in bản dọc; bản ngang vẫn in`).

## 8. Kết quả `render`

```
Font dùng thật: Arial-BoldMT (/…/Arial Bold.ttf)
OK: <thư mục>/<tên ảnh>.jpg · 1280x720 · 74 KB · nền 01.jpg · chân dung khung tròn x=799,y=99,w=462,h=462 · cỡ chữ 76 · 3 dòng · vùng chữ x=68–767 y=273–504
```

- `Font dùng thật` khác font đã chọn, hoặc `Cảnh báo: không thấy font … có đủ chữ tiếng Việt` → soi kỹ dấu (ơ, ư, ạ, ẫ); đổi `--font`.
- Ảnh luôn JPG đúng cỡ, dưới 2 MB (giới hạn YouTube); cùng TSV, cùng ảnh, cùng máy → cùng từng byte.
- `Bỏ qua (đã có): …` — chỉ khi chạy với `--skip-existing`; ảnh cũ giữ nguyên.
- Hậu tố `(ngang)` / `(doc)`: lỗi hay cảnh báo thuộc bố cục nào. `LỖI … (ngang)` chặn cả lượt in; vấn đề của bản dọc chỉ là `Cảnh báo … (doc)`.

## 9. Soi ảnh sau khi in (agent tự mở file JPG)

1. Dấu tiếng Việt đủ, không ô vuông/ký tự lạ; chữ đọc rõ trên nền.
2. Chữ không đè lên mặt người; chân dung không bị cắt mất đầu.
3. Nhãn góc trên-trái, logo góc trên-phải, góc dưới-phải không có gì quan trọng.
4. Nền không có chữ/người lạ (ảnh AI hay tự thêm) — có thì đề xuất bỏ ảnh đó khỏi `nen/`.
5. Cả chuỗi nhìn cùng một khuôn; nền nào lệch tông quá thì đề xuất đổi ô `nen` của dòng đó.
