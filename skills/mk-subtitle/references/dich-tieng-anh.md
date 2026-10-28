# Dịch phụ đề sang tiếng Anh

Mục tiêu: người xem đọc tiếng Anh hiểu đúng điều người nói, trong đúng khoảng thời gian câu đó xuất hiện. Dịch từ bản tiếng Việt **đã chuẩn hoá**.

## 1. Khớp cue

- Một khối `[số]` tiếng Việt → đúng một khối tiếng Anh cùng số, cùng mốc. Không gộp, không tách, không để trống (`build` từ chối).
- Câu tiếng Việt vắt qua hai cue: dịch cả câu trong đầu, rồi chia bản dịch theo đúng chỗ ngắt, sao cho mỗi cue tự đọc được. Trật tự từ khác nhau giữa hai ngôn ngữ thì đẩy ý về cue chứa ý đó trong lời nói.

## 2. Văn phong

- Tiếng Anh nói tự nhiên, ngắn; không dịch từng chữ. Lời họp nội bộ → giọng công việc thân mật.
- Xưng hô anh/chị/em/mình → `I`, `you`, `we` theo ngữ cảnh; gọi tên thì giữ tên ("chị Lan" → "Lan"). Không thêm Mr./Ms. nếu người nói không trang trọng.
- Tiểu từ "ạ", "nhé", "nha", "đó" → bỏ hoặc chuyển thành ngữ điệu ("…, okay?") khi cần giữ thái độ.
- Giữ nguyên tên riêng, tên sản phẩm, mã; thuật ngữ theo bảng thuật ngữ Việt–Anh của repo nếu có (vd giả: "khách tiềm năng" → "lead").
- Số, tiền: "2 triệu" → "2 million VND" (hoặc theo quy ước repo); ngày dạng "October 9".

## 3. Độ dài

- Tối đa 2 dòng, mỗi dòng ≤ 42 ký tự; `check` cảnh báo khi vượt 20 ký tự/giây.
- Vượt nhịp đọc → rút gọn cách diễn đạt **tiếng Anh** (bỏ từ thừa, chọn từ ngắn), giữ đủ ý; không bỏ thông tin (số, tên, phủ định).

## 4. Chỗ chưa chắc

- Câu tiếng Việt mơ hồ, thuật ngữ nội bộ không rõ nghĩa, chữ nhận giọng vô nghĩa → dịch an toàn nhất theo ngữ cảnh, ghi vào danh sách "chỗ chưa chắc" (`[số] · giờ · câu Việt · bản dịch · lý do`). Không cue nào để nguyên tiếng Việt; không đoán ra nghĩa thì dịch phần hiểu được và ghi rõ trong danh sách.
- Không chèn chú thích, dấu `[?]` hay ngoặc giải thích vào phụ đề.
- Cue hội thoại `- … / - …`: dịch giữ hai dòng, giữ dấu `- `.

## 5. Ví dụ (giả)

| Tiếng Việt | Tiếng Anh |
|---|---|
| `Mai mình gửi báo giá cho khách nhé.` | `Let's send the client the quote tomorrow.` |
| `Khách cũ quay lại thì mình tính là khách mới à?` | `So returning customers count as new ones?` |
| `Tháng này doanh thu tăng 30%,` / `nhưng chi phí cũng tăng.` | `Revenue is up 30% this month,` / `but so are costs.` |
