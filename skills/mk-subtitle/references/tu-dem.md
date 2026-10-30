# Từ đệm và lặp từ

Mục tiêu: bỏ tiếng ngập ngừng khỏi phụ đề và cho editor danh sách đoạn cắt, **không** bỏ chữ mang nghĩa. Script đánh dấu, người dùng quyết.

## 1. Hai nhóm script đưa ra

| Nhóm | Gồm | Mặc định đề xuất |
|---|---|---|
| A — âm đệm giữa câu | à, ừ, ờ, ừm, ờm, ơ, ư, hmm nằm giữa câu: không đứng đầu câu, không ngay sau câu hỏi, không sau tên riêng, không mang dấu hỏi | xoá + cắt |
| B — cần nghe lại | âm đệm đầu câu hoặc ngay sau câu hỏi ("…đúng không Nhi? Ừ đúng rồi", "À thế thì dễ"), sau tên riêng ("Minh à"), cuối câu ("…rồi ừ."), tiểu từ hỏi ("Thế à?", "Vậy ư?"), lặp từ liền nhau ("mình mình"), cụm người dùng thêm bằng `--more` | giữ, trừ khi người dùng duyệt từng mã |

Phân nhóm là quy tắc máy theo vị trí và dấu câu, không hiểu nghĩa; phụ đề tự động hay thiếu dấu câu nên nhóm A vẫn có thể lẫn chữ mang nghĩa. Agent đọc ngữ cảnh **từng** mã nhóm A trước khi trình; mã nào mang nghĩa (câu đáp, tiếng gọi, cảm thán) → nêu riêng, đề xuất `trừ` mã đó.

Phụ đề tự động YouTube có lúc **lược bớt** âm đệm khi nhận giọng (tuỳ người nói, tuỳ video). Nhóm A = 0 hoặc rất ít trên file tải bằng `fetch` không chứng minh video sạch: báo người dùng điều này, đề nghị nghe thử vài đoạn trước khi kết luận "không có gì để cắt".

## 2. Khi nào KHÔNG bỏ

- "Ừ"/"Ờ"/"Vâng"/"Dạ" là **câu trả lời** cho câu hỏi ngay trước (đồng ý, xác nhận).
- "à", "ư", "hả", "nhỉ" là **tiểu từ hỏi** hay cảm thán mang thái độ: "Thế à?", "Hay nhỉ!".
- Lặp là **từ láy** hay nhấn mạnh có chủ ý: "dần dần", "từ từ", "ngày ngày", "rất rất quan trọng".
- "ạ" là lễ phép, không phải từ đệm.

## 3. Trình bày để người dùng duyệt

```
Nhóm A — 12 chỗ (à 5 · ừ 4 · ờ 3), tổng khoảng 4 giây. Ví dụ:
- F003 · 00:00:46 · quán mình mở [ờ] thêm một chi nhánh
- F004 · 00:00:52 · khách cũ thì [à] mình gửi mã giảm giá
…
Nhóm B — 40 chỗ:
- lặp từ liền nhau (21): F001 · 00:00:22 · để chị gửi [gửi] file này … (15 dòng đầu; đủ danh sách ở <đường dẫn fillers.tsv>)
- đầu câu hoặc ngay sau câu hỏi (9): F010 · 00:01:05 · xong chưa Lan? [Ừ] xong rồi …
Gợi ý: duyệt A. Duyệt mã nào?
```

- Ngữ cảnh trích đúng cột `ngu_canh`; giờ lấy từ `bat_dau` (bỏ phần mili giây khi trình).
- Nhóm B dài: trình 15 dòng mỗi lý do, đưa đường dẫn file TSV cho phần còn lại; người dùng duyệt thêm bằng mã hoặc khoảng mã.

## 4. Đoạn cắt

| Độ chính xác | Khi nào | Editor làm gì |
|---|---|---|
| chính xác (từng từ) | đầu vào có mốc từng từ (VTT tự động YouTube) | cắt theo mốc; nghe lại một lượt vì mốc nhận giọng có thể lệch khoảng 0,1 giây |
| chính xác (cả cue) | cue chỉ toàn từ đệm | cắt cả cue |
| ước lượng | từ đệm nằm giữa cue của SRT/VTT thường — giờ chia theo độ dài chữ | dùng mốc để tìm chỗ, nghe rồi tự cắt |

- Đoạn cắt = từ lúc bắt đầu từ đệm tới lúc bắt đầu từ kế tiếp (gồm khoảng lặng ngay sau). Các từ đệm sát nhau (cách ≤ 50 ms) gộp một đoạn.
- `cat.srt` hiện mỗi đoạn cắt thành một dòng phụ đề `✂ F003 À` — nhập làm track tham chiếu để thấy chỗ cắt trên timeline; `cat.csv` là danh sách để đánh dấu đã cắt.
- Phụ đề `sau-cat` chỉ khớp khi editor cắt **đúng và đủ** mọi đoạn trong danh sách, dạng cắt kéo liền (ripple delete). Cắt thêm/bớt đoạn nào → dùng bản timeline gốc và cắt cả track phụ đề cùng video.
