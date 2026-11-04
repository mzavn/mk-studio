# Chia Buổi Học Dài Thành File Con (Quy Trình Kaizen)

Tài liệu phương pháp luận và quy chuẩn biên tập: bẻ một bài giảng / buổi học dài (2–4 tiếng) thành các file con (20–30
phút/chủ đề) cho đội ngũ dựng video (Editor) và làm tài liệu học tập tinh hoa, không làm mất ngữ cảnh.

---

## 1. Cơ Chế Phản Biện 3 Trục (Fable-Thinking)

```
                            CƠ CHẾ PHẢN BIỆN 3 TRỤC
                                     ▲
                                     │ (1) TRỤC GIÁ TRỊ TRI THỨC
                                     │ (Knowledge Value vs Noise)
                                     │
        (3) TRỤC AN TOÀN DỮ LIỆU     ┼──────────────── (2) TRỤC TRẢI NGHIỆM NGƯỜI XEM
        (Data Safety & No Loss)      │                 (Viewer Retention & Clarity)
                                     ▼
```

1. **Trục giá trị tri thức (Knowledge Value vs. Fluff):**
   - *Đầu giờ lớp học:* 10–20 phút đầu thường chỉ gồm mic check, ổn định phòng Zoom, điểm danh, chào hỏi nhao nhao.
     **Cắt bỏ 100%** thủ tục hành chính và tạp âm kỹ thuật.
   - *Tâm sự lan man:* Học viên kể chuyện dài dòng không liên quan bài học → lược bỏ hoặc chỉ tóm câu hỏi cốt lõi.
   - *Tri thức cốt tủy:* Lời giảng nguyên lý, quy luật, giải mã của người hướng dẫn → **bảo toàn 100%**.
2. **Trục an toàn dữ liệu (Data Integrity & Reversibility):**
   - File transcript gốc là Single Source of Truth, **không bao giờ sửa hoặc xóa dòng**.
   - Mọi thao tác cắt gọt thực hiện qua **bảng lệnh CUT / KEEP** (Action Sheet). Trong file markdown chuẩn khoá
     (`split --style khoa`), đoạn cắt là khối `> [!WARNING] Lệnh Editor: CẮT BỎ (CUT)` kèm nguyên văn bên dưới (khung thô
     `--style khung` thu gọn vào `> [!CAUTION]-`) để khi cần kiểm tra chéo vẫn còn nguyên văn.
3. **Trục trải nghiệm người xem (Topic-First Architecture):**
   - Bài giảng dài 3–4 tiếng liên tục khiến người học ngợp và khó tra cứu.
   - Chuẩn vàng: **20–30 phút/file con** — vừa vặn một chu kỳ tập trung não bộ, dễ nghe podcast hoặc cắt clip ngắn.

---

## 2. Các Loại Đoạn Cắt Bỏ (CUT)

| Loại đoạn cắt | Dấu hiệu nhận diện | Xử lý |
|---|---|---|
| **Đầu giờ / Thủ tục** | Mic check, "nghe rõ chưa", "bật camera", điểm danh, nội quy, chào hỏi trước giờ giảng | 🛑 CUT từ `00:00:00` đến trước câu giảng chính thức đầu tiên |
| **Giải lao giữa giờ** | "Nghỉ giải lao 5 phút", "nghỉ một chút", khoảng lặng màn hình tĩnh giữa bài giảng | 🛑 CUT từ lúc bắt đầu thông báo nghỉ tới khi người giảng nói tiếp |
| **Mất tiếng / Kỹ thuật** | Đoạn câm không có lời thoại (quãng lặng ≥ 90 giây), sự cố đường truyền | 🛑 CUT sạch thời gian chết, ghi rõ lý do trong Action Sheet |
| **Thủ tục bế mạc** | MC nhắc đứng dậy làm lễ, thông báo hành chính sau khi người giảng đã chào kết | 🛑 CUT, chỉ giữ lại lời dặn dò / chúc ngủ ngon của người giảng |

---

## 3. Quy Chuẩn Giữ Ngữ Cảnh (Context Preservation)

### A. Nguyên tắc vàng "A Hỏi — B Đáp" trong Vấn đáp (Q&A)
- **Sai lầm phổ biến:** Cắt phăng câu hỏi của học viên (A) vì nghĩ là "nội dung của học viên", chỉ giữ câu trả lời của
  thầy (B) → người xem mất hoàn toàn ngữ cảnh, không hiểu vì sao thầy đưa ra lời khuyên đó.
- **Quy chuẩn:** Mỗi ca vấn đáp **bắt buộc đủ cả 2 phần**:
  - `> **👤 [A Hỏi - <Tên học viên / bối cảnh>] [mm:ss]:** <hoàn cảnh, nghề nghiệp, bế tắc, câu hỏi>`
  - `> **🧙‍♂️ [B Đáp - <Tên người giảng>] [mm:ss]:** <lời khai tuệ, phân tích, tâm pháp, chỉ dẫn>`
- Với chuỗi vấn đáp nhiều ca độc lập cuối buổi: tách thành từng sub-part `P5.1`, `P5.2`… (thời lượng 10–18 phút/ca).

### B. Đối thoại Socrates: "Giảng viên hỏi — Học viên đáp — Giảng viên khai tuệ"
Khi người giảng chủ động chất vấn học viên để bẻ gãy định kiến (Socratic Questioning):
- `> **🧙‍♂️ [B Hỏi - <Người giảng>] [mm:ss]:** <câu hỏi truy vấn bản chất>`
- `> **👤 [A Đáp - <Học viên>] [mm:ss]:** <câu trả lời thông thường / góc nhìn thế tục>`
- `> **🧙‍♂️ [B Khai Tuệ - <Người giảng>] [mm:ss]:** <đúc kết triết lý, bẻ gãy nhãn dán, chỉ ra chân lý>`
Giữ nguyên nhịp 3 bước này vì đây là "hook" đắt giá nhất của bài giảng.

---

## 4. Quy Chuẩn Đặt Tên Định Danh File Con (Naming Convention)

Nhằm quản lý tệp tin khi xuất hàng loạt video và bàn giao editor:
1. **Cấu trúc nhãn hiển thị:** `<Tiền tố buổi>:P<k> - <Tên chủ đề tóm lược>` (hoặc `P<k>.<m>` cho ca vấn đáp).
   - Ví dụ: `Buổi 1:P1 - Bản Chất Của Đạo & "Dịch Vô Tự"`
   - Ví dụ ca vấn đáp: `Buổi 0:P5.1 - Bác Trần Sĩ Hà: Tam Trụ & Dịch Mệnh`
2. **Đồng bộ hai chiều:** Nhãn định danh phải khớp từng chữ giữa **Bảng lệnh Editor** và **Tiêu đề phân đoạn**
   (`### 🎬 Buổi 1:P1 [11:36 - 30:30] ...`). Lệnh `lecture.py lint` sẽ chặn nếu lệch.
3. **An toàn tên file khi xuất:** Tên file trên đĩa thay các ký tự cấm `\ / : * ? " < > |` bằng dấu `-`:
   - `Buổi 1:P1 - Bản Chất Của Đạo` → `Buổi 1-P1 - Bản Chất Của Đạo.srt`

---

## 5. Bảng Chỉ Dẫn Editor (Action Sheet Specification)

Bảng Markdown đặt ở đầu file bài giảng, gồm 6 cột chuẩn:

| Cột | Ý nghĩa | Ví dụ |
|---|---|---|
| **Phân đoạn** | Mã phân đoạn | `Đầu giờ`, `P1`, `Giải lao`, `P2`, `Bế mạc` |
| **Timecode video gốc** | Khoảng thời gian trên timeline gốc | `00:00:00 - 00:09:55` |
| **Lệnh** | Lệnh kỹ thuật rõ ràng cho editor | 🛑 **CẮT BỎ (CUT)** hoặc 🟢 **GIỮ LẠI (KEEP)** |
| **Thời lượng** | Độ dài đoạn tính theo phút giây | `9p 55s`, `25p 30s` |
| **Tên file con** | Tên gợi ý cho project/file xuất | `Buổi 5:P1 - Phương Pháp Học Đại Trí` (hoặc `*Nhiễu: Đầu giờ*`) |
| **Ghi chú cắt & điểm nối** | Điểm in/out, lời mở đầu/kết thúc | `Bắt đầu từ câu giảng chính của Thầy lúc [09:56]` |

---

## 6. Vòng Lặp Kaizen (Continuous Improvement)

Mỗi buổi học sau khi biên tập xong, chốt một dòng tổng kết theo định dạng Kaizen:
```markdown
| **Buổi X** | <Chủ đề cốt lõi> | <Thời lượng gốc> | **<Thời lượng cắt>** (<Chi tiết cắt>) | **<Thời lượng giữ>** | <N> file con | <Điểm nhấn> |
```
- Số liệu gốc, cắt, giữ và số file con lấy tự động từ dòng in của `lecture.py plan`.
- Ghi nhận những tình huống mới (vd: buổi có 2 lần giải lao, buổi mất tiếng 20 phút, buổi có chuỗi 5 ca vấn đáp)
  để bổ sung vào bộ từ khoá và kinh nghiệm xử lý cho các buổi tiếp theo.
