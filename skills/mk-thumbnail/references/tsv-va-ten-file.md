# Tên file, nhãn góc, tiêu đề và file `thumbnail.tsv`

Đọc ở Bước 1 (xem tên tách ra), Bước 4 (sửa TSV theo lời người dùng) và khi `check`/`render` in dòng `LỖI`. Ví dụ đều là dữ liệu giả.

## 1. Tên file → nhãn góc (badge) + tiêu đề (title)

Mẫu tên: `<Từ> <số>_P<số>[.<số>] - <tiêu đề>.<đuôi video>`. Script chuẩn hoá chữ Việt về NFC (tên file trên macOS có thể ở dạng tổ hợp NFD), gộp khoảng trắng thừa.

| Tên file (giả) | badge | title |
|---|---|---|
| `Buổi 2_P03 - Chợ Sáng & Quán Quen.mp4` | `Buổi 2 · P03` | `Chợ Sáng & Quán Quen` |
| `Buổi 0_P05.6 - Lời Chúc Của Chị Lan.mp4` | `Buổi 0 · P05.6` | `Lời Chúc Của Chị Lan` |
| `Buổi 1_P06 - Bánh Mì: Nướng vs Hấp (Phần 2) – Giá - Lãi.mp4` | `Buổi 1 · P06` | `Bánh Mì: Nướng vs Hấp (Phần 2) – Giá - Lãi` |
| `Tập 4_P01 - Quán Phở Đầu Ngõ.mov` | `Tập 4 · P01` | `Quán Phở Đầu Ngõ` |
| `so di cho tuan 3.mov` (không theo mẫu) | *(trống)* | `so di cho tuan 3` |

- Dấu phân cách giữa số buổi và phần: `_`, `-`, `–` hoặc `·`; giữa phần và tiêu đề: ` - `, ` – `, `:` hoặc khoảng trắng.
- Phần còn lại của tên là tiêu đề, giữ nguyên mọi dấu `:` `&` `(` `)` `–` `-` `vs`.
- `*` và `|` trong tên file là chữ thường, nhưng trong TSV chúng là ký hiệu (§3) → khi ghi title, script đổi `*` thành `·` và `|` thành `/`, in `Cảnh báo: <file>: tên có * hoặc | …`. TSV do `plan` ghi vì thế luôn qua `check`.
- Tên không theo mẫu → in `Cảnh báo: <file>: tên không theo mẫu …` (badge trống, title = cả tên): hỏi người dùng tiêu đề thật.
- Tên file có ký tự điều khiển (xuống dòng, tab, ESC…) → `Lỗi: tên file … có ký tự điều khiển` (in dạng `\xNN`), dừng; đổi tên file trước.
- Đuôi video nhận: `.mp4 .mov .mkv .m4v .webm .avi`. File ẩn (bắt đầu bằng `.`) và file khác bị bỏ qua; thư mục không đệ quy.
- Thứ tự: theo tên tự nhiên (`Buổi 2` trước `Buổi 10`).

`names` chỉ đọc tên, không mở video; mỗi dòng in: `số<TAB>badge<TAB>title<TAB>tên file`.

Mẫu nhãn góc: `--badge` (cho `names`, `plan`), mặc định `{word} {n} · P{p}`. Trường: `{word}` chữ trước số buổi (`Buổi`, `Tập`), `{n}` số buổi, `{p}` số phần (`03`, `05.6`). Ví dụ (giả) `--badge "Buổi {n} · Phần {p}"` → `Buổi 2 · Phần 03`. Mẫu sai (trường khác, có `|` `*`, dài quá 40 ký tự) → `Lỗi`, thoát 2.

Tên ảnh ra lấy từ tên video, đổi ký tự Windows/exFAT không cho: `:` → ` - `, `\ / * ? " < > |` → `-` (vd `Buổi 3_P02 - Chợ Sáng: Bánh Mì?.mp4` → `Buổi 3_P02 - Chợ Sáng - Bánh Mì-.jpg`). Hai video ra cùng tên ảnh → `LỖI … trùng tên ảnh`.

## 2. Cột của `thumbnail.tsv`

File UTF-8, cột cách nhau bằng **tab**; dòng bắt đầu bằng `#` là ghi chú, trừ dòng `# assets: <thư mục ảnh>` (do `plan --assets` ghi, trước dòng tên cột); dòng tên cột đúng thứ tự:

```
video	badge	title	nen	nen_doc	chan_dung	logo
/…/Buổi 2_P03 - Chợ Sáng & Quán Quen.mp4	Buổi 2 · P03	Chợ Sáng & Quán Quen	/…/anh/nen/01.jpg		/…/anh/chan-dung.png	/…/anh/logo.png
```

| Cột | Ai sửa | Nghĩa |
|---|---|---|
| `video` | không sửa | video gốc — chỉ để lấy tên ảnh ra, không mở/giải mã video; phải là file có đuôi video (§1) |
| `badge` | người dùng | nhãn nhỏ góc trên-trái; để trống = không có nhãn; ≤ 40 ký tự, không có `\|` hay `*` |
| `title` | người dùng | tiêu đề lớn (ký hiệu ở §3), tối đa 200 ký tự |
| `nen` | người dùng | ảnh nền 16:9; `plan` xoay vòng các ảnh trong `<thư mục ảnh>/nen/` theo thứ tự tên; trống = nền vẽ sẵn |
| `nen_doc` | người dùng | ảnh nền 9:16 cho bản dọc, xoay vòng từ `nen-doc/`; trống = cắt giữa ảnh `nen` |
| `chan_dung` | người dùng | ảnh người dạy (`chan-dung.png`/`.jpg`…); trống = không chân dung, tiêu đề dùng cả bề ngang |
| `logo` | người dùng | logo (`logo.png`…) ở góc trên-phải; trống = không logo |

Cột đường dẫn (`video` và 4 cột ảnh): chỉ nhận file trong máy — URL (`http://…`, `x:…`) và đường dẫn mạng (`\\máy\thư mục\…`, `//máy/…`) bị bác; đường dẫn tương đối tính từ thư mục chứa TSV; ảnh nhận `.png .jpg .jpeg .webp` và phải nằm trong thư mục chứa TSV hoặc thư mục ghi ở dòng `# assets:` (tính theo đích thật nếu là symlink).

Cập nhật sau khi đã sửa tay: `plan … --update` ghi `thumbnail-2.tsv` (rồi `-3`…) cạnh bản mới nhất — giữ `badge`, `title` và ô ảnh đã có của từng video, chỉ điền ô ảnh còn trống; video không còn trong nguồn bị bỏ (có `Cảnh báo`); bản cũ không bị sửa. Muốn một video dùng nền khác → đổi ô `nen` của dòng đó sang ảnh khác trong `nen/`.

## 3. Ký hiệu trong `title`

| Ký hiệu | Nghĩa | Ví dụ (giả) |
|---|---|---|
| `\|` | xuống dòng đúng chỗ này (tối đa 3 dòng, không dòng trống) | `Chợ Sáng:\|Bánh Mì & Trà Đá` |
| `*…*` | đoạn chữ màu vàng (đi theo cặp) | `Bí Quyết *Giữ Khách Quen*` |

- Không có `|` → script tự ngắt: ưu tiên sau `:` `,` `;` hoặc trước `&` `–` `-` `vs` `(`, tránh dòng chỉ một từ, chọn cỡ chữ lớn nhất vừa ≤ 3 dòng.
- Có `|` → giữ đúng các dòng đó, chỉ thu nhỏ cỡ chữ cho vừa. Bản dọc (`--doc`) có khung chữ hẹp hơn: chỗ `|` không vừa thì bản dọc tự ngắt lại (có `Cảnh báo … (doc)`), bản ngang vẫn giữ `|`.
- Xem trước cách ngắt mà không ghi ảnh: `check … [--doc]` in dòng `Xem trước: <file>:<dòng>: ngang|doc · cỡ N · dòng 1 / dòng 2 …`.
- Chữ khác (`\`, `{`, `}`, `\N`) là chữ thường, không thành lệnh định dạng.
- Muốn dấu `|` hay `*` hiện ra thật trong tiêu đề: không hỗ trợ — đổi sang dấu khác (`/`, `·`).

## 4. Dòng `LỖI` của `check` / `render`

Mọi dòng có dạng `LỖI: <file>:<số dòng>: <lý do>`; có lỗi thì không ảnh nào được ghi. Lỗi bố cục có hậu tố `(ngang)`; với bản dọc, cùng lỗi đó chỉ là `Cảnh báo: … (doc) — chưa in bản dọc; bản ngang vẫn in` (bản ngang không bị chặn).

| Lý do in ra | Cách sửa |
|---|---|
| `dòng tên cột phải là: video badge title nen nen_doc chan_dung logo` | khôi phục dòng tên cột (cách nhau bằng tab) |
| `cần 7 cột cách nhau bằng tab, có N` | trình sửa đã đổi tab thành dấu cách → gõ lại tab |
| `có ký tự điều khiển … trong dòng` | xoá ký tự lạ (thường do dán từ nơi khác) |
| `cột video phải là đường dẫn file trong máy, không phải địa chỉ mạng/URL` | skill chạy offline: tải video về máy rồi chạy lại `plan` |
| `cột video phải là file video (…)` | cột `video` trỏ vào file không phải video → chạy lại `plan` |
| `không thấy video …` | video bị đổi tên/chuyển chỗ → chạy lại `plan` |
| `cột nen/nen_doc/chan_dung/logo phải là đường dẫn file trong máy …` | tải ảnh về máy, ghi đường dẫn file |
| `cột … phải là file ảnh (.png, .jpg, .jpeg, .webp)` | chuyển ảnh sang một trong các đuôi đó |
| `không thấy ảnh nền / chân dung / logo …` | ảnh bị đổi tên/chuyển chỗ → sửa ô đó hoặc chạy lại `plan` |
| `cột … là đường dẫn mạng (UNC …)` | chép ảnh về máy, vào thư mục ảnh |
| `ảnh … phải nằm trong thư mục chứa TSV hoặc thư mục ảnh (dòng # assets: …)` | chép ảnh vào thư mục ảnh rồi sửa ô đó |
| `ffmpeg không đọc được ảnh …` (`check`/`render`) | ảnh hỏng hoặc sai đuôi → mở thử, lưu lại bằng trình xem ảnh |
| `dấu * (chữ vàng) phải đi theo cặp` | thêm hoặc bỏ một dấu `*` |
| `title tối đa 3 dòng, không dòng trống` | bớt dấu `\|`, bỏ `\|` thừa ở đầu/cuối hay hai dấu liền nhau |
| `title trống` | gõ tiêu đề |
| `title quá dài (N ký tự, tối đa 200)` (`check`) | rút ngắn — 200 ký tự không bao giờ vừa 3 dòng |
| `badge tối đa 40 ký tự, không có \| hay *` | rút ngắn nhãn |
| `trùng tên ảnh với dòng N` | hai dòng cùng tên video → xoá bớt một dòng |
| `title quá dài: cỡ chữ nhỏ nhất … vẫn không vừa 3 dòng — rút ngắn title` (`check`/`render`) | rút ngắn tiêu đề (script đã thử mọi cách tự ngắt) |
| `các dòng ngắt bằng \| không vừa ở cỡ nhỏ nhất … (dòng dài nhất: «…»)` | bỏ `\|` để script tự ngắt, hoặc dời chỗ ngắt cho dòng được nêu ngắn lại |
| `badge quá dài (quá 60% bề ngang ảnh)` (`render`) | rút ngắn nhãn |
