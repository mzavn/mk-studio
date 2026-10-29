# Định Dạng Bảng Chỉ Dẫn Kỹ Thuật (Editor Action Sheet)

Tài liệu quy định cấu trúc và quy tắc phân tích các bảng chỉ dẫn cắt video con đầu vào cho `mk:video-cutter`.

---

## 1. Ba Định Dạng Đầu Vào Được Hỗ Trợ

Script `cutter.py` tự động phát hiện định dạng dựa trên cấu trúc văn bản:

### Định dạng 1: Markdown Action Sheet Table (Khuyến nghị chuẩn)
Xuất hiện trong các file bài giảng Markdown (như `Buổi X.md`):

```markdown
### ⏱️ Bảng lệnh cắt file con (Editor Action Sheet)

| Phân đoạn | Timecode video gốc | Lệnh | Thời lượng | Tên file con | Ghi chú cắt & điểm nối |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Đầu giờ** | `00:00:00 - 00:04:59` | 🛑 **CẮT BỎ (CUT)** | 5p 00s | *Nhiễu: Đầu giờ* | Mic check và điểm danh |
| **P1** | `00:05:00 - 00:29:59` | 🟢 **GIỮ LẠI (KEEP)** | 25p 00s | **Buổi 1:P1 - Khởi Động** | Bắt đầu câu giảng chính |
| **Giải lao** | `00:30:00 - 00:34:59` | 🛑 **CẮT BỎ (CUT)** | 5p 00s | *Nhiễu: Giải lao* | Nghỉ giữa giờ |
| **P2** | `00:35:00 - 01:05:59` | 🟢 **GIỮ LẠI (KEEP)** | 31p 00s | **Buổi 1:P2 - Chuyên Đề** | Nối tiếp sau nghỉ |
```
- Parser quét mọi dòng có chứa lệnh `🟢 **GIỮ LẠI (KEEP)**`.
- Trích xuất timecode bắt đầu và kết thúc từ cột thứ hai.
- Lấy tên file từ cột *Tên file con*.

### Định dạng 2: File Kế Hoạch Đơn Giản (`PLAN.txt`)
Mỗi dòng 5 cột phân cách bằng dấu gạch đứng `|`:
```text
00:00:00 | CUT  | Đầu giờ  | | Mic check
00:05:00 | KEEP | P1       | Khái Niệm Cốt Lõi | Bắt đầu bài giảng chính
00:30:00 | CUT  | Giải lao | | Nghỉ giữa giờ
00:35:00 | KEEP | P2       | Thực Hành & Vấn Đáp | Tiếp tục
01:06:00 | END
```
- Dòng cuối bắt buộc là `mốc | END`.
- Phân đoạn kéo dài tới mốc của dòng tiếp theo.

### Định dạng 3: Bảng Tính CSV (`sheet.csv`)
File CSV tiêu chuẩn có header:
```csv
stt,lenh,ma,nhan,ten_file,bat_dau,ket_thuc,thoi_luong_giay,tieu_de,ghi_chu
1,CUT,Đầu giờ,,Nhiễu,00:00:00,00:04:59,300,,Mic check
2,KEEP,P1,Buổi 1:P1,Buổi 1-P1 - Khởi Động,00:05:00,00:29:59,1500,Khởi Động,Điểm nối
```

---

## 2. Quy Tắc Làm Sạch Tên File (Sanitization)

Hệ thống file (macOS, Windows, Linux) cấm các ký tự đặc biệt trong tên tệp:
`\ / : * ? " < > |`

Script tự động:
1. Thay dấu `:` và `/` thành gạch ngang `-` hoặc gạch dưới `_`.
2. Thay các khoảng trắng liên tiếp thành một dấu cách đơn.
3. Cắt bỏ dấu chấm và khoảng trắng ở hai đầu tên file.
4. Gắn phần mở rộng `.mp4`.

Ví dụ:
`Buổi 1:P01 - Khai Giảng & Tổng Quan?` $\to$ `Buổi 1-P01 - Khai Giảng & Tổng Quan.mp4`
