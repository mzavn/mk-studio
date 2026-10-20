# Phản biện: <tiêu đề bài>

- Bài: `<đường dẫn tuyệt đối>` · <số tiếng> tiếng
- Chân dung: `<đường dẫn tuyệt đối>` — người đọc chính: <ô "Ai đọc"> <(giả định) nếu chân dung ghi vậy>
- Thuật ngữ: `<đường dẫn tuyệt đối | không có>` · Luật repo: `<đường dẫn tuyệt đối | không có>`
- Hội đồng: CEO, <vai>, <vai> — <một câu vì sao chọn các vai này>

## 1. Nhận định nhanh

<Tối đa 5 dòng: bài đang làm tốt điều gì cho người đọc chính; vấn đề lớn nhất; mức dấu hiệu AI; tình trạng thuật ngữ; SEO/GEO/AEO một câu.>

## 2. Hội đồng đọc bài

<Mỗi vai một khối theo `references/hoi-dong.md` mục 4.>

## 3. Giọng văn

Mức dấu hiệu AI: <Thấp|Vừa|Cao> — <lý do>. Đây là đánh giá giọng văn, không phải kết luận ai viết.

<Tối đa 6 dòng: dấu hiệu chính, dòng, mã gợi ý A tương ứng.>

## 4. Thuật ngữ

| Khái niệm | Đang dùng (số lần, dòng) | Chuẩn đề xuất | Mã |
|---|---|---|---|

## 5. SEO · GEO · AEO

| Mục | Hiện trạng | Mã |
|---|---|---|

## 6. Ý tưởng cải thiện

<3–5 ý theo `references/hoi-dong.md` mục 6; mỗi ý mang mã Y.>

## 7. Danh sách gợi ý để duyệt

Mã: `C` hội đồng · `A` giọng AI · `T` thuật ngữ · `S` SEO/GEO/AEO · `Y` ý tưởng (Y chỉ sửa khi tác giả bảo "viết nháp" hoặc tự viết).
Loại:
- `chữ`: thay hoặc xoá **tối đa 3 tiếng liền nhau**, không đổi cấu trúc câu, **không chèn chữ mới** (vd chèn từ khoá) và không thêm chữ nước ngoài. Ngoài phạm vi đó → `câu`.
- `câu`: viết lại một câu. · `thêm`: thêm nội dung (mặc định ô `[điền: …]`); ô Đề xuất = **nguyên đoạn "trước" + phần chèn**, không bao giờ chỉ phần chèn. · `cấu trúc`: đổi tiêu đề mục (mọi thay đổi trên dòng `#…`, kể cả 1 chữ), chuyển vị trí.
- `meta`: đoạn nằm trong frontmatter (giữa hai dòng `---` đầu file). Dòng ngày cập nhật ở chân bài không phải `meta`.
- `thuật ngữ`: đổi một khái niệm ở nhiều chỗ.

| Mã | Mức | Dòng | Loại | Hiện tại (nguyên văn) | Đề xuất | Vì sao (gắn chân dung) |
|---|---|---|---|---|---|---|
| A1 | Cao | L12 | chữ | `<đoạn nguyên văn>` | `<đoạn sau sửa>` | <một câu> |
| T1 | Vừa | L23, L42 | thuật ngữ | nhiều chỗ | `<trước 1>` → `<sau 1>`<br>`<trước 2>` → `<sau 2>` | <một câu> |
| S1 | Vừa | L3 | meta | `<đoạn nguyên văn>` | 1: `<đoạn nguyên văn>` → `<phương án 1>`<br>2: `<đoạn nguyên văn>` → `<phương án 2>` | <một câu> |
| T2 | Thấp | config/glossary.yaml:cuối file | thuật ngữ | — | <mô tả mục cần thêm; giá trị chưa có thì hỏi ở mục 9> | <một câu> |

Luật bảng (`scripts/check_report.py` kiểm các luật có dấu ✓):
- ✓ Đoạn văn bài luôn đặt trong backtick `…` (đoạn có backtick bên trong thì ``…``), **không** thêm ngoặc kép bao ngoài. Chép nguyên văn kể cả `**`, dấu ngoặc kép của bài.
- ✓ Mỗi đoạn "trước" chỉ xuất hiện **đúng một lần** trong file và nằm ở dòng ghi trong cột Dòng; trùng → lấy dài thêm cho tới khi duy nhất. Loại `thêm`: đoạn đứng ngay trước chỗ chèn.
- ✓ Nhiều chỗ (mã T) hoặc nhiều phương án (meta, tiêu đề): mỗi cặp `` `trước` → `sau` `` một dòng, cách nhau bằng `<br>`; phương án đánh số `1:`, `2:` để tác giả duyệt `S1:2`.
- ✓ Đề xuất không có chữ số mới so với đoạn gốc, trừ trong ô `[điền: …]`; không thêm chữ nước ngoài/viết tắt mà đoạn gốc không có (trừ khi đó chính là mục đích của mã, nói rõ ở cột Vì sao).
- ✓ Đổi đích link, ảnh, mã neo `{#…}`, thẻ HTML hay URL luôn bị gắn ⚠ và không được duyệt hàng loạt; chỉ đề xuất khi thật cần, nói rõ ở cột Vì sao.
- ✓ Xếp theo Mức (Cao → Vừa → Thấp), cùng mức theo dòng đầu tiên. Mã đánh liên tục trong từng chữ cái (A1, A2…), không trùng.
- Sửa file khác bài (bảng thuật ngữ, file cấu hình): cột Dòng ghi `<file>:<chỗ>` cho **từng** file; không bao giờ đề xuất chèn `[điền]` vào file cấu hình (yaml/json) — thiếu giá trị thì hỏi ở mục 9.
- Không tự ghi ⚠ hay ký hiệu khác vào bảng; ô Mã chỉ là mã (`A1`). ⚠ do agent chính gắn sau khi kiểm.
- Tối đa 25 gợi ý; nhiều hơn → giữ mức Cao/Vừa, ghi "còn N gợi ý mức Thấp, xin thì đưa".

## 8. Giữ nguyên (đừng sửa)

<Dòng + trích ngắn những câu/đoạn mang giọng thật của tác giả, ví dụ đắt, chi tiết người làm thật mới biết.>

## 9. Cần bạn bổ sung

<Câu hỏi cho tác giả: số thật, ví dụ thật, "A và B là một hay hai thứ?", từ khoá người đọc gõ… Mỗi câu ghi mã gợi ý đang chờ câu trả lời. Không có thì ghi "Không".>
