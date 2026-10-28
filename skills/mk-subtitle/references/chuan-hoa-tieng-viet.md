# Chuẩn hoá phụ đề tiếng Việt

Mục tiêu: chữ trên màn hình đúng điều người nói, đọc kịp, thuật ngữ thống nhất. **Trung thành với lời nói**: sửa lỗi, không viết lại ý, không tóm tắt, không đổi giọng người nói.

## 1. Thứ tự sửa trong mỗi khối

1. **Lỗi nhận giọng.** Dùng bảng thuật ngữ của repo ("ghi âm sai → chuẩn") và kết quả `scan`. Chỉ thay khi ngữ cảnh khớp: bảng ghi "co → company" nhưng "cái co concept" là "concept" bị nhận dính âm — đọc cả câu trước khi thay. Tên người nói và tên riêng người dùng nêu ở Bước 0 không có trong `scan`: tự dò các chữ nghe gần giống (vd giả "Lan Anh" bị nhận thành "lan an") và sửa theo ngữ cảnh. Không có bảng: chỉ sửa lỗi hiển nhiên (vd "nguười" → "người").
2. **Chính tả và bỏ dấu.** Một kiểu bỏ dấu thống nhất trong cả file (theo đa số trong file hoặc theo quy ước repo: hoá/hóa, thuỷ/thủy).
3. **Dấu câu và viết hoa.** Chấm hết câu, phẩy chỗ ngắt hơi, chấm hỏi cho câu hỏi; viết hoa đầu câu và tên riêng; tên sản phẩm theo đúng cách viết của hãng (Bitrix24, Zalo, Shopee — vd giả trong bảng thuật ngữ).
4. **Số.** Giữ cách nói nếu là lời thoại tự nhiên; số đo, tiền, giờ, phần trăm viết bằng chữ số: "mười lăm phần trăm" → "15%", "chín giờ sáng" → "9 giờ sáng".
5. **Từ nói trùng, văn nói thừa** đã được xử lý ở bước từ đệm; ở bước này **không** tự xoá thêm "thì", "là", "cái", "ấy". Người dùng muốn gọn hơn → đề xuất cụm cụ thể, chờ duyệt.

## 2. Ngắt dòng

- Tối đa 2 dòng, mỗi dòng ≤ 42 ký tự (kể cả dấu cách). Script đã chia sẵn; sửa chữ làm dòng dài ra → ngắt lại.
- Ngắt sau dấu câu nếu được; hai dòng dài gần bằng nhau, dòng dưới có thể dài hơn.
- Không tách: tên riêng nhiều tiếng, số với đơn vị ("15 %"), cụm động từ ngắn ("đi rồi"), giới từ khỏi danh từ theo sau ("của / chị Lan" → không).
- Không đổi cách chia cue (đã chia theo câu và quãng nghỉ, khớp mốc thời gian). Cue có hai người nói ở dạng hội thoại (`- Thế à?` / `- Ừ, đúng rồi.`): giữ mỗi người một dòng, giữ dấu `- `.

## 3. Nhịp đọc

- `check` cảnh báo cue vượt 20 ký tự/giây (mặc định cho lời họp, nói nhanh; phát sóng hay dùng 17 — người dùng đổi bằng `--max-cps`).
- Mặc định **không** rút gọn để kịp nhịp đọc: báo số cue vượt và vài ví dụ. Người dùng bảo rút gọn → chỉ bỏ từ không mang nghĩa trong cue đó, giữ nguyên ý, liệt kê cue đã rút gọn.

## 4. Chỗ chưa chắc

- Nghe không rõ, nhiều cách hiểu, tên riêng lạ → giữ chữ gốc trong file, ghi vào danh sách "chỗ chưa chắc": `[số] · giờ · chữ đang có · đoán`. Không chèn `[?]` hay ghi chú vào phụ đề (script `check` coi là lỗi).
- Cùng một chữ lạ lặp nhiều lần → hỏi một lần, áp cho mọi chỗ sau khi người dùng trả lời.

## 5. Ví dụ (giả)

| Trước | Sau | Vì sao |
|---|---|---|
| `mở quán ở quận ba từ năm hai không hai mươi` | `mở quán ở quận 3 từ năm 2020` | số địa chỉ, năm |
| `khách nhắn qua da lô rồi chuyển khoản` | `khách nhắn qua Zalo rồi chuyển khoản` | bảng thuật ngữ: da lô → Zalo |
| `thế thì mình làm tiếp nhé` | `Thế thì mình làm tiếp nhé.` | viết hoa đầu câu, dấu chấm |
| `doanh thu tăng ba mươi phần trăm` | `doanh thu tăng 30%` | phần trăm |
