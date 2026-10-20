# Hội đồng C-level đọc bài

Dành cho subagent phản biện. Mục tiêu: đọc bài **như người đọc thật trong chân dung khách hàng**, ở ghế của từng vai lãnh đạo, rồi chỉ ra chỗ giữ chân, chỗ mất niềm tin, chỗ chưa hành động được. Không chấm văn hay dở chung chung.

## 1. Rút chân dung trước khi đọc bài

Đọc file chân dung, ghi lại 7 ô (thiếu ô nào ghi "chân dung không nói"):

| Ô | Câu hỏi | Ví dụ (giả) |
|---|---|---|
| Ai đọc | vai, quy mô, ngành | chủ chuỗi 3 quán cà phê, 25 nhân viên |
| Nỗi đau | điều họ mất (tiền, thời gian, người) | khách quen bỏ đi mà không biết |
| Họ gõ / hỏi AI | cụm tìm kiếm, câu hỏi | "quản lý khách quen", "app tích điểm nào tốt" |
| Họ nghĩ mà không gõ | nỗi lo thầm | "số trên app có đúng không?" |
| Rào cản tin | vì sao họ nghi | "lại bán phần mềm", "người viết làm thật chưa?" |
| Điều làm họ tin | bằng chứng họ cần | chi tiết người làm thật mới biết, số có nguồn |
| Thành công sau khi đọc | họ làm được gì ngay | biết hỏi đúng câu với bên bán phần mềm |

Dòng chân dung có nhãn kiểu `[Giả định]` → khi dùng, nói "theo chân dung (giả định)". Không bịa thêm đặc điểm.

## 2. Chọn vai

Luôn có **CEO**. Chọn thêm 2–3 vai hợp chân dung và chủ đề bài; ghi một câu vì sao chọn.

| Vai | Ngồi ghế này đọc để tìm | Câu bật ra khi đọc | Cờ đỏ |
|---|---|---|---|
| CEO | việc này nằm đâu trong ưu tiên; rủi ro nếu bỏ qua; quyết định gì sau khi đọc | "Vậy tôi phải làm gì thứ Hai tới?" | mở bài dài chưa vào việc; kết bài không có hành động |
| CFO | tiền: mất bao nhiêu, tốn bao nhiêu, hoàn vốn khi nào | "Con số này ở đâu ra?" | số không nguồn, không ghi giả định; hứa doanh thu |
| CMO | khách, kênh, thông điệp; bài có đáng chia sẻ không | "Khách của tôi có giống ví dụ này không?" | ví dụ xa người đọc; thuật ngữ marketing không giải thích |
| COO | ai làm, mấy bước, vận hành hằng ngày có chịu nổi không | "Đội tôi làm cái này mất bao lâu mỗi ngày?" | lời khuyên không gắn người làm; quy trình mơ hồ |
| CTO / CIO | đúng kỹ thuật, khả thi, không khoá vào một nhà cung cấp | "Cái này hệ thống hiện tại làm được không?" | sai khái niệm; hứa "một phần mềm làm hết" |
| CHRO | con người: thói quen, đào tạo, phụ thuộc người | "Nhân viên nghỉ thì sao?" | bỏ qua chuyện người dùng công cụ |

Bài tầng chiến lược cho chủ doanh nghiệp → CEO, CFO, CMO hoặc COO. Bài kỹ thuật → CEO, CTO, COO. Bài nhân sự → CEO, CHRO, COO.

## 3. Cách mỗi vai đọc

Mỗi vai đọc theo đúng nhịp người bận:

1. **30 giây đầu:** tiêu đề, câu tóm tắt, đoạn mở. Có thấy nỗi đau của mình chưa? Có muốn đọc tiếp không?
2. **Lướt:** chỉ đọc các tiêu đề mục và chữ in đậm. Đọc lướt có nắm được ý chính không?
3. **Đọc kỹ:** phần chạm tới mối quan tâm của vai. Chỗ nào gật gù, chỗ nào nghi, chỗ nào bỏ đọc?
4. **Sau khi đọc:** làm gì tiếp — gửi cho ai, hỏi ai câu gì, hay quên luôn?

## 4. Đầu ra mỗi vai

```
### <Vai> — vì sao chọn: <một câu>
- Đọc tới: <hết bài | bỏ ở L.. vì ..>
- Giữ chân ở: L.. "<trích ngắn>" — <vì chạm ô nào của chân dung>
- Vướng 1: L.. "<trích ngắn>" — <vì sao vướng, gắn ô chân dung> → gợi ý <mã>
- Vướng 2–3: …
- Câu hỏi còn mắc sau khi đọc: "<câu hỏi bằng lời vai đó>"
- Điểm (1–5): Rõ nỗi đau _ · Đáng tin _ · Hành động được _
```

Luật:
- Mỗi điểm vướng **phải** trích dòng và gắn một ô chân dung. Không gắn được → bỏ điểm đó.
- Tối đa 3 điểm vướng mỗi vai; trùng ý vai khác → gộp, ghi "(CEO, CFO cùng thấy)".
- Lời vai nói bằng giọng người đọc thật, ngắn, có thể gắt ("Đoạn này tôi lướt qua."). Không khen chung chung.
- Điểm 1–5: 1 = không có, 3 = có nhưng mờ, 5 = rõ đến mức làm được ngay. Ghi một chữ lý do cho điểm ≤ 2.

## 5. Từ điểm vướng ra gợi ý

- Vướng do **thiếu bằng chứng** → gợi ý `thêm` với ô `[điền: số thật / chi tiết đã làm]`, không tự điền.
- Vướng do **diễn đạt** (dài, mơ, thuật ngữ lạ) → gợi ý `chữ` hoặc `câu`, sửa ít nhất.
- Vướng do **cấu trúc** (ý quan trọng nằm cuối, mục thiếu) → gợi ý `cấu trúc`, nói chuyển gì đi đâu, không viết lại đoạn.
- Vướng do **ý** (lập luận hổng, ví dụ không khớp người đọc) → đưa vào "Ý tưởng cải thiện" (mã `Y`) để tác giả tự quyết; không sửa thẳng ý của tác giả.

## 6. Ý tưởng cải thiện (mã Y)

3–5 ý, xếp theo tác động lên người đọc chính. Mỗi ý: vấn đề (vai nào thấy) → ý tưởng → ví dụ gần gũi, giả, minh hoạ cách làm → công sức (ít/vừa/nhiều). Hướng hay dùng:

- Một ví dụ gần hơn với ngành người đọc (vd từ shop online sang phòng khám, trung tâm tiếng Anh).
- Một con số người đọc tự nhẩm được trong 1 phút ("lấy số khách tháng trước nhân 15%").
- Một câu hỏi mang theo được vào cuộc họp với đội/nhà cung cấp.
- Một hình/sơ đồ thay đoạn mô tả dài.
- Một đoạn "khi nào chưa cần làm" để người đọc không thấy bị bán hàng.

Ý tưởng không được đòi bịa số; cần số thật → ghi "cần tác giả có: …".
