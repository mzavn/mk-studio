# Từ đệm và lặp từ

Mục tiêu: bỏ tiếng ngập ngừng khỏi phụ đề và cho editor danh sách đoạn cắt, **không** bỏ chữ mang nghĩa. Script đánh dấu, người dùng quyết.

## 1. Ba nhóm script đưa ra

Máy tự quyết những chỗ chắc chắn, chỉ để chỗ mập mờ cho người nghe lại. Không mã nào bị cắt khi chưa được duyệt.

| Nhóm | Gồm | Mặc định đề xuất |
|---|---|---|
| A — đề xuất cắt | âm đệm à, ừ, ờ, ừm, ờm, ơ, ư, hmm nằm giữa câu (không đứng đầu câu, không ngay sau câu hỏi, không sau tên riêng hay từ xưng hô, không mang dấu hỏi); **lặp từ trong cụm** — hai từ giống nhau liền nhau, không có dấu câu ở giữa, không phải từ láy ("chị gửi gửi file") | xoá + cắt |
| B — cần nghe lại | âm đệm đầu câu hoặc ngay sau câu hỏi ("…đúng không Nhi? Ừ đúng rồi", "À thế thì dễ"), sau tên riêng ("Minh à") hay từ xưng hô ("mẹ à", "em à" — có thể là tiếng gọi, có thể là âm đệm), cuối câu ("…rồi ừ."), tiểu từ hỏi ("Thế à?", "Vậy ư?"), cụm người dùng thêm bằng `--more` | giữ, trừ khi người dùng duyệt từng mã |
| G — giữ | lặp **qua dấu câu** (từ trước kết thúc bằng `. , ? ! ; : …` — "…bảy giờ. Giờ đó…" là câu mới); **từ láy / nhấn mạnh** (vân vân, dần dần, từ từ, luôn luôn, ngày ngày, mãi mãi, rất rất, này này…); **tiểu từ liệt kê** ("tiền ư danh ư") | không đề xuất; chỉ trình số đếm + vài mẫu |

Lý do từng mã nằm ở cột `ly_do` (nhóm G bắt đầu bằng `giữ:`). Phân nhóm là quy tắc máy theo vị trí và dấu câu, không hiểu nghĩa; trên một bộ mẫu bài giảng có nhãn người chấm, nhóm A đúng khoảng 9/10 (âm đệm giữa câu khoảng 96%, lặp trong cụm khoảng 85%), nhóm G đúng khoảng 96%, nhóm B thật sự mập mờ (khoảng 2/3 nên cắt). Phụ đề tự động hay thiếu dấu câu nên A vẫn có thể lẫn chữ mang nghĩa: agent đọc ngữ cảnh **từng** mã A trước khi trình; mã nào mang nghĩa (câu đáp, tiếng gọi, cảm thán, tên riêng bị lặp) → nêu riêng, đề xuất `trừ` mã đó. Thấy mã G rõ là vấp → nêu riêng để người dùng duyệt mã đó.

Phụ đề tự động YouTube có lúc **lược bớt** âm đệm khi nhận giọng (tuỳ người nói, tuỳ video). Nhóm A = 0 hoặc rất ít trên file tải bằng `fetch` không chứng minh video sạch: báo người dùng điều này, đề nghị nghe thử vài đoạn trước khi kết luận "không có gì để cắt".

## 2. Khi nào KHÔNG bỏ

- "Ừ"/"Ờ"/"Vâng"/"Dạ" là **câu trả lời** cho câu hỏi ngay trước (đồng ý, xác nhận).
- "à", "ư", "hả", "nhỉ" là **tiểu từ hỏi** hay cảm thán mang thái độ: "Thế à?", "Hay nhỉ!".
- Lặp là **từ láy** hay nhấn mạnh có chủ ý: "dần dần", "từ từ", "ngày ngày", "rất rất quan trọng" — hoặc lặp sang câu mới ("Quả này là núi. Núi thì…").
- "ạ" là lễ phép, không phải từ đệm.

## 3. Trình bày để người dùng duyệt

```
Nhóm A — đề xuất cắt, 12 chỗ (à 5 · ừ 4 · lặp trong cụm 3), tổng khoảng 4 giây. Ví dụ:
- F003 · 00:00:46 · quán mình mở [ờ] thêm một chi nhánh
- F004 · 00:00:52 · chị gửi [gửi] file cho em
…
Nhóm B — cần nghe lại, 9 chỗ:
- đầu câu hoặc ngay sau câu hỏi (9): F010 · 00:01:05 · xong chưa Lan? [Ừ] xong rồi …
Giữ (không đề xuất), 21 chỗ: lặp qua dấu câu 14 · từ láy 5 · liệt kê 2 — vd F001 · khách đến dần [dần] đông lên
Gợi ý: duyệt A. Duyệt mã nào?
```

- Ngữ cảnh trích đúng cột `ngu_canh`; giờ lấy từ `bat_dau` (bỏ phần mili giây khi trình).
- Nhóm B dài: trình 15 dòng mỗi lý do, đưa đường dẫn file TSV cho phần còn lại; người dùng duyệt thêm bằng mã hoặc khoảng mã.
- Câu duyệt: `duyệt A`, `duyệt A trừ F007`, `duyệt all` (= A + B, **không** gồm G), mã/khoảng mã; mã G chỉ bỏ khi người dùng nêu rõ mã đó (hoặc `G`).

## 4. Đoạn cắt

| Độ chính xác | Khi nào | Editor làm gì |
|---|---|---|
| chính xác (từng từ) | đầu vào có mốc từng từ (VTT tự động YouTube) | cắt theo mốc; nghe lại một lượt vì mốc nhận giọng có thể lệch khoảng 0,1 giây |
| chính xác (cả cue) | cue chỉ toàn từ đệm | cắt cả cue |
| ước lượng | từ đệm nằm giữa cue của SRT/VTT thường — giờ chia theo độ dài chữ | dùng mốc để tìm chỗ, nghe rồi tự cắt |

- Đoạn cắt = từ lúc bắt đầu từ đệm tới lúc bắt đầu từ kế tiếp (gồm khoảng lặng ngay sau). Các từ đệm sát nhau (cách ≤ 50 ms) gộp một đoạn.
- `cat.srt` hiện mỗi đoạn cắt thành một dòng phụ đề `✂ F003 À` — nhập làm track tham chiếu để thấy chỗ cắt trên timeline; `cat.csv` là danh sách để đánh dấu đã cắt.
- Phụ đề `sau-cat` chỉ khớp khi editor cắt **đúng và đủ** mọi đoạn trong danh sách, dạng cắt kéo liền (ripple delete). Cắt thêm/bớt đoạn nào → dùng bản timeline gốc và cắt cả track phụ đề cùng video.
