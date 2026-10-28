# Bàn giao phụ đề: <tên video>

- Nguồn phụ đề: `<tên file gốc>` · thời lượng <hh:mm:ss>
- Ngày chuẩn bị: <dd/mm/yyyy>
- Đã bỏ <n> từ đệm (<tổng giây> giây) · <n> cue tiếng Việt đổi chữ · <n> cue của `<tên>.vi.srt` có cảnh báo nhịp đọc

## File trong thư mục

| File | Dùng khi |
|---|---|
| `<tên>.vi.srt` | phụ đề tiếng Việt, khớp **video gốc chưa cắt** |
| `<tên>.en.srt` | phụ đề tiếng Anh, khớp video gốc chưa cắt |
| `<tên>.vi.sau-cat.srt` | phụ đề tiếng Việt, khớp video **sau khi đã cắt đúng và đủ** mọi đoạn trong `<tên>.cat.csv` |
| `<tên>.en.sau-cat.srt` | như trên, tiếng Anh |
| `<tên>.cat.srt` | track tham chiếu: mỗi đoạn cần cắt là một dòng `✂ <mã> <từ>` đúng vị trí trên timeline |
| `<tên>.cat.csv` | danh sách đoạn cắt (giờ bắt đầu, kết thúc, từ, ngữ cảnh, độ chính xác) để đánh dấu đã cắt |

## Cách làm

1. Nhập video gốc lên timeline.
2. Nhập `<tên>.cat.srt` làm một track phụ đề riêng — CapCut, Premiere Pro, DaVinci Resolve, Final Cut Pro đều nhận file `.srt` (vị trí lệnh nhập tuỳ phiên bản phần mềm).
3. Cắt từng đoạn theo track `✂`, dạng cắt kéo liền (ripple delete). Nghe lại mỗi chỗ cắt: mốc lấy từ nhận giọng tự động, có thể lệch khoảng 0,1 giây.
4. Cắt xong toàn bộ → xoá track `✂`, nhập `<tên>.vi.sau-cat.srt` (và `<tên>.en.sau-cat.srt` nếu cần song ngữ).
5. Không cắt, hoặc cắt khác danh sách → dùng `<tên>.vi.srt` / `<tên>.en.srt`, nhập **trước** khi cắt và cắt cả track phụ đề cùng video.

## Cần nghe lại

<Đoạn cắt "ước lượng" — giờ · từ · ngữ cảnh. Không có thì ghi "Không".>

## Chỗ chưa chắc

<cue · giờ · chữ đang có · đoán / bản dịch · lý do. Không có thì ghi "Không".>
