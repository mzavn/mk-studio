# Giọng văn AI trong bài tiếng Việt

Dành cho subagent phản biện. Mục tiêu: chỉ ra **chỗ nghe như máy viết** để tác giả sửa, giữ giọng thật của tác giả. Không có cách nào chắc chắn biết bài do AI viết; chỉ nói "dấu hiệu", không kết tội.

## 1. Cách đọc

1. Mở phần "Giọng AI (ứng viên)" của kết quả `scan.py`: đó là chỗ máy đếm thấy, chưa phải kết luận. Đọc lại từng dòng trong ngữ cảnh.
2. Đọc to trong đầu từng đoạn: người thật có nói câu này với một chủ doanh nghiệp đang uống cà phê không?
3. Tìm cả dấu hiệu máy không đếm được (mục 3).
4. Ghi luôn **dấu hiệu giọng người** (mục 4) vào "Giữ nguyên" để không ai sửa mất.

## 2. Dấu hiệu từ ngữ

| Nhóm | Ví dụ | Vì sao nghe như AI | Sửa (ít nhất) |
|---|---|---|---|
| Mở bài sáo | "Trong thời đại số…", "Trong bối cảnh hiện nay…" | câu đúng với mọi bài | xoá; bắt đầu bằng câu thứ hai |
| Từ phô trương | then chốt, chìa khoá, toàn diện, vượt trội, bứt phá, nâng tầm, hành trình, khám phá | tính từ không đo được | xoá hoặc thay bằng chi tiết **đã có trong bài** |
| Trạng từ rỗng | "một cách hiệu quả", "một cách toàn diện" | thêm chữ không thêm ý | xoá |
| Câu đệm | "Điều quan trọng là…", "Cần lưu ý rằng…", "Có thể nói…" | rào trước khi nói | xoá phần đệm, giữ vế sau |
| Từ nối đầu câu dày | Hơn nữa, Ngoài ra, Bên cạnh đó, Đặc biệt, Tóm lại | nối như bài luận | xoá từ nối; hoặc nối bằng ý ("Còn một chuyện nữa:") nếu tác giả hay nói vậy |
| Câu dịch từ tiếng Anh | "Đây là lý do tại sao…", "chơi một vai trò", "vào cuối ngày", "được thực hiện bởi" | cấu trúc tiếng Anh | đổi sang câu chủ động tiếng Việt: "…nên…", "…đóng góp…", "rốt cuộc", "<ai> làm" |
| Mở/kết kiểu mẫu | "Trong bài viết này…", "Hy vọng bài viết giúp ích…", "Hãy cùng tìm hiểu…" | khuôn bài SEO cũ | xoá |
| Ký hiệu | gạch dài — dày đặc, emoji đầu dòng | thói quen của mô hình | thay phần lớn — bằng dấu phẩy, dấu hai chấm, tách câu |

## 3. Dấu hiệu cấu trúc (máy khó đếm)

| Dấu hiệu | Ví dụ (giả) | Gợi ý |
|---|---|---|
| Đối lập lật ngược lặp lại | "Đây không phải chuyện phần mềm. Đây là chuyện con người." xuất hiện 3+ lần | giữ lần đắt nhất, các lần khác nói thẳng |
| Bộ ba đều tăm tắp | "nhanh hơn, rẻ hơn, và hiệu quả hơn" ở nhiều đoạn | giữ hai, hoặc thay bằng một ví dụ cụ thể |
| Câu chốt đạo lý cuối mỗi đoạn | đoạn nào cũng kết bằng một câu kiểu châm ngôn | giữ câu chốt ở 1–2 đoạn quan trọng nhất |
| Tự hỏi tự đáp | "Vậy giải pháp là gì? Câu trả lời là…" | hỏi thật (để người đọc tự nghĩ) hoặc nói thẳng |
| Gạch đầu dòng nào cũng **In đậm:** giải thích | 10/10 gạch đầu dòng cùng khuôn | giữ khuôn cho danh sách cần lướt; danh sách ngắn viết thành câu |
| Nhịp câu đều | độ lệch độ dài câu thấp (scan: "độ lệch" < 5 với trung bình > 15) | xen một câu rất ngắn sau ý mạnh; tách câu quá dài |
| Kết bài tóm tắt lại thân bài | "Tóm lại, tích điểm khách quen giúp…" lặp ý các mục | xoá, hoặc kết bằng một hành động / câu hỏi |
| Khẳng định chung không chủ thể | "Nhiều doanh nghiệp gặp vấn đề này." | gắn chủ thể cụ thể đã có trong bài, hoặc `[điền: ai, bao nhiêu]` |
| Chữ "chúng ta" chung chung | "chúng ta cần thay đổi tư duy" | theo luật xưng hô của repo; không có luật → "bạn" hoặc chủ ngữ cụ thể |
| Hedging dày | "có thể", "thường", "phần nào" ở hầu hết câu | giữ ở chỗ thật sự không chắc |

**Câu bị động** ("được/bị") chỉ là ứng viên: "được" còn nghĩa "có thể" ("gỡ ra được"). Chỉ gợi ý đổi khi luật repo yêu cầu câu chủ động và câu đổi rõ hơn.

## 4. Dấu hiệu giọng người — giữ nguyên

- Khẩu ngữ, cảm thán có chủ ý ("Thành thật đi nào", "rất bình thường đó").
- Chi tiết chỉ người trong nghề biết (tên tính năng, mẹo vận hành, lỗi từng gặp).
- Nhân vật có tên, có hoàn cảnh (lương về, ngày sale, chuyển khoản hộ).
- Câu thừa nhận chưa biết, chưa làm xong.
- Quan điểm gắt, hơi lệch chuẩn nhưng có lý.

Gợi ý nào làm mất những thứ này → không đưa ra.

## 5. Mức kết luận

| Mức | Khi nào |
|---|---|
| Thấp | 0–2 dấu hiệu rải rác; giọng người rõ |
| Vừa | dấu hiệu tập trung ở vài đoạn (thường mở bài, kết bài, danh sách) |
| Cao | dấu hiệu khắp bài, ít chi tiết thật, câu nào cũng đúng với mọi doanh nghiệp |

Ghi: "Mức dấu hiệu AI: <mức> — <một câu lý do>. Đây là đánh giá giọng văn, không phải kết luận ai viết."

## 6. Viết gợi ý sửa giọng (mã A)

- "Hiện tại": trích **nguyên văn** đúng đoạn cần đổi (đủ ngắn, đủ duy nhất trong file).
- "Đề xuất": bản sửa nhỏ nhất, dùng lại từ của tác giả. Loại `chữ` (xoá/đổi vài chữ) ưu tiên hơn `câu` (viết lại câu).
- Không thêm thông tin mới. Câu cần chi tiết mới để bớt chung chung → `[điền: <chi tiết>]`.
- Không đề xuất thêm lỗi chính tả, câu cụt giả để "qua mặt máy dò".

Ví dụ (giả):

| Hiện tại | Đề xuất | Loại |
|---|---|---|
| "Hơn nữa, việc này đóng vai trò then chốt trong tăng trưởng." | "Việc này quyết định quán có giữ được khách quen hay không." *(ý "giữ khách quen" đã có ở đoạn trên)* | câu |
| "Trong thời đại số, quán trà sữa nào cũng bán qua Zalo." | "Quán trà sữa nào cũng bán qua Zalo." | chữ |
