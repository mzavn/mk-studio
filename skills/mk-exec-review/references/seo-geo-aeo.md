# SEO · GEO · AEO cho bài tiếng Việt

Dành cho subagent phản biện. Ba lớp, cùng một nguyên tắc: **người đọc trước, máy sau**. Không nhồi từ khoá, không đổi giọng tác giả để chiều máy.

- **SEO** (Search Engine Optimization): bài hiện trên Google khi người đọc gõ đúng chữ của họ.
- **AEO** (Answer Engine Optimization): bài cho ra câu trả lời ngắn, đúng, lấy ra được ngay (đoạn trích nổi bật, "Mọi người cũng hỏi", trợ lý giọng nói).
- **GEO** (Generative Engine Optimization): ChatGPT, Gemini, Perplexity, Google AI Overviews trích bài, nêu tên bài/tác giả như nguồn.

Kết quả `scan.py` phần "SEO/GEO/AEO" là số liệu nền; mọi gợi ý vẫn phải đọc bài.

## 1. Từ khoá lấy từ chân dung, không lấy từ đầu agent

1. Từ chân dung: cụm "họ gõ tìm gì", câu "họ nghĩ mà không gõ", câu hỏi họ sẽ hỏi AI.
2. So với chữ trong bài: bài dùng chữ chuyên môn (vd giả: "giữ chân khách hàng") còn người đọc gõ chữ đời thường ("làm sao để khách quay lại quán") → gợi ý đặt chữ đời thường ở **một vài chỗ có trọng lượng** (tóm tắt, một câu mở, một tiêu đề mục), không thay thuật ngữ chuẩn của bài.
3. Một bài, một ý định tìm kiếm chính; 1–3 cụm phụ (cùng con số với `SKILL.md` Bước 1). Không chắc người đọc gõ gì → hỏi trong "Cần bạn bổ sung", không đoán.

## 2. Checklist SEO

| Mục | Đạt khi | Ghi chú |
|---|---|---|
| Tiêu đề (`title`) | chứa ý định tìm kiếm chính; ~50–65 ký tự để không bị cắt | repo có khuôn tiêu đề (vd `<nỗi đau>: <khái niệm>`) → giữ khuôn, chỉ gợi ý chữ |
| Tóm tắt / meta description | 120–160 ký tự; nói người đọc được gì; có cụm chính | |
| 100 tiếng đầu | nêu vấn đề và khái niệm chính | mở bài kể chuyện vẫn được, miễn khái niệm xuất hiện sớm |
| Tiêu đề mục | nói được ý của mục khi đọc lướt; vài mục ở dạng câu người đọc hỏi | |
| Link trong | dẫn sang bài liên quan có thật của repo, theo cú pháp repo | không bịa link |
| Ảnh | có alt mô tả nội dung | |
| Slug, mã neo | theo luật repo | bài đã đăng: không đổi slug/mã neo |

## 3. Checklist AEO — trả lời được ngay

| Mục | Đạt khi |
|---|---|
| Câu trả lời đầu mục | ngay dưới tiêu đề dạng câu hỏi ("X là gì", "Vì sao…", "Khi nào…") có **một câu/đoạn 40–60 tiếng trả lời thẳng**, rồi mới giải thích |
| Đoạn đứng một mình | câu trả lời không dùng "điều này", "nó", "như trên" trỏ về đoạn trước |
| Danh sách / bảng | bước làm, tiêu chí, so sánh để dạng danh sách đánh số hoặc bảng |
| Hỏi đáp | có một nhóm câu hỏi người đọc thật hay hỏi (từ chân dung), mỗi câu trả lời 1–3 câu; bài đã có mục câu hỏi → dùng lại, không tạo mục trùng |

## 4. Checklist GEO — đáng để AI trích

| Mục | Đạt khi |
|---|---|
| Khái niệm rõ ràng | định nghĩa một câu, có tên Việt và tên Anh ở lần đầu (vd giả: "Giữ chân khách hàng (Customer Retention)") để AI nối đúng khái niệm |
| Câu trích được | vài câu luận điểm tự đứng được, có chủ ngữ cụ thể, ≤ 30 tiếng (vd giả: "Khách quen bỏ quán thường không phàn nàn; họ chỉ không quay lại.") |
| Bằng chứng | số có nguồn hoặc ghi "giả định"; chi tiết đã làm thật; ngày cập nhật |
| Người viết | có dấu hiệu kinh nghiệm thật (E-E-A-T: trải nghiệm, chuyên môn, uy tín, tin cậy) — mục "từ thực tế", vai trò, việc đã làm |
| Nhất quán | thuật ngữ một dạng suốt bài (`thuat-ngu.md`); máy và người cùng đỡ nhầm |
| Không câu rỗng | câu đúng với mọi bài (xem `giong-ai.md`) không được AI trích; thay bằng chi tiết |

## 5. Dữ liệu có cấu trúc (chỉ gợi ý, không tự thêm)

Repo/website tự sinh schema → chỉ ghi nhận. Không có → gợi ý tác giả cân nhắc `Article` (tác giả, ngày đăng/cập nhật), `FAQPage` cho mục hỏi đáp, `HowTo` cho bài có bước. Đây là việc của hệ thống web, không chèn JSON vào bài trừ khi repo có quy ước.

## 6. Viết gợi ý (mã S)

- Mỗi gợi ý: mục checklist không đạt → chỗ trong bài (dòng, trích nguyên văn) → đề xuất sửa nhỏ nhất → vì sao, gắn chân dung ("người đọc gõ '…'").
- Đổi tiêu đề/tóm tắt trong frontmatter là loại `meta`; đề xuất 2 phương án đánh số `1:`, `2:` (khuôn ở `assets/mau-bao-cao.md`), giữ khuôn repo. Phương án **phải** giữ nguyên câu/ý chủ chốt tác giả đã đặt trong tóm tắt, chỉ thêm hoặc ghép cụm tìm kiếm; không đủ chỗ thì đề xuất bỏ phần khác, không bỏ câu chủ chốt. Dòng ngày cập nhật/lịch sử ở chân bài là thân bài, không phải `meta`.
- Thêm câu trả lời đầu mục, hỏi đáp, định nghĩa → loại `thêm`: ghi câu đề xuất **rút từ câu đã có trong bài** (chỉ ghép, cắt), không đủ chữ gốc → `[điền: …]`. Repo cấm AI viết câu → luôn `[điền: …]` kèm hướng dẫn (bất biến 5 trong `SKILL.md`).
- Chèn cụm tìm kiếm vào thân bài là loại `câu` (không phải `chữ`), tối đa mức **Vừa**, và chỉ ở chỗ có trọng lượng (mục 1.2). Cụm có chữ nước ngoài ("data", "CRM") mà bài viết bằng chữ Việt → đề xuất dạng Việt nếu người đọc cũng gõ dạng đó, hoặc chỉ đặt ở tóm tắt.
- Không gợi ý: nhồi từ khoá, lặp cụm chính nhiều lần, đổi thuật ngữ chuẩn sang chữ tìm kiếm, thêm số để "uy tín hơn".
- Mức: Cao = người đọc chính khó tìm thấy bài hoặc AI không trích được định nghĩa; Vừa = mất điểm ở đoạn trích/tóm tắt; Thấp = tinh chỉnh.
