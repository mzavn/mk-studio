# Nhật ký thay đổi

Mỗi bản có số dạng `X.Y.Z` (chung cho cả bộ skill):

- **Số cuối (Z)** tăng: sửa lỗi nhỏ, cách dùng không đổi.
- **Số giữa (Y)** tăng: có thêm tính năng; cập nhật xong dùng tiếp bình thường.
- **Số đầu (X)** tăng: cập nhật xong bạn cần làm thêm một bước — bản đó sẽ ghi rõ bước gì.

Cập nhật: `bash ~/.mk-studio/install.sh --update`.

## Chưa phát hành

Dự kiến: v0.1.0

### star

**Mới**

- **Skill `star` — nhật ký STAR.** Kể một chuyện, agent đề xuất một trong 5 loại nhật ký (ngày, giải quyết vấn đề A–Z hoặc viết nhanh, đóng gói thành công, kiến tạo tương lai, dẫn dắt người khác), hỏi từng câu theo mẫu và ghi nguyên văn câu trả lời vào `~/nhat-ky-star/`. Có đủ bộ câu hỏi cơ bản/chuyên sâu, 4 case giải mẫu, 28 case luyện tập, 8 dạng tài sản đóng gói. Xem tiến độ: số bài trọn vẹn theo cột mốc 28 / 300 / 1000 / 10000, việc hẹn hôm qua chưa làm, kết quả đến hạn ghi.
- Cài bằng `install.sh` của bộ mk-studio: `gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global`. Thư mục skill cùng tên mà không do `install.sh` tạo thì bị từ chối thay vì bị ghi đè.
