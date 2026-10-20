# Chuẩn hoá thuật ngữ

Dành cho subagent phản biện. Mục tiêu: một khái niệm, một tên gọi trong cả bài; thuật ngữ tác giả tự đặt được giới thiệu rõ và dùng nhất quán. Không làm nghèo chữ: hai chữ khác nhau cho hai khái niệm khác nhau phải giữ.

## 1. Gom danh sách khái niệm

Nguồn, theo thứ tự ưu tiên:

1. **Bảng thuật ngữ** của repo (`--glossary` trong scan): tên Việt, tên Anh. Biến thể trong ngoặc của bảng (scan in riêng, kèm ngữ cảnh) là **biến thể được phép**, không phải lỗi.
2. **Câu định nghĩa trong bài:** "X là …", "gọi là X", "tạm gọi X", "X (tiếng Anh: Y)".
3. **Cụm in đậm ngắn**, **cụm ngoặc kép lặp ≥2 lần** và **cụm lặp ≥3 lần** (scan) có vẻ là khái niệm, không phải chữ thường hay lời thoại.
4. **Chữ nước ngoài/viết tắt** (scan): CRM, CSKH, upsell, retargeting…

## 2. Tìm biến thể

| Kiểu biến thể | Ví dụ (giả) | Cách thấy |
|---|---|---|
| Đồng nghĩa trôi | "sổ khách" / "danh sách khách gốc" / "bảng khách chính" cho cùng một thứ | đọc ngữ cảnh từng lần xuất hiện |
| Bỏ dấu kiểu cũ/mới | hoá/hóa, khoẻ/khỏe, thuỷ/thủy | scan "bỏ dấu khác nhau" |
| Gạch nối, viết hoa giữa câu | check-list/checklist, Zalo OA/zalo oa | scan "viết khác nhau" (viết hoa vì đầu câu không tính) |
| Việt/Anh lẫn lộn | "chăm sóc khách hàng" / "CSKH" / "customer care" | chữ nước ngoài + đọc |
| Viết tắt không giải thích | "CDP" xuất hiện mà chưa từng viết đủ | chữ nước ngoài ở dòng đầu tiên |
| Tên khác giữa tiêu đề và thân bài | tiêu đề "gộp khách trùng", thân bài "hợp nhất hồ sơ" | so frontmatter với thân bài |

## 3. Khi nào KHÔNG gộp

- Hai chữ chỉ **hai khái niệm** tác giả cố ý tách (vd giả: "quầy" là nơi bán, "kênh" là cách khách liên hệ). Gộp là làm sai ý bài. Tác giả đã nói ở Bước 2 → theo lời tác giả.
- Chữ nằm trong **lời nhân vật / trích dẫn nguyên văn** ("Dạ, quán em có ship chị ơi!"): giữ cách nói của nhân vật.
- **Biến thể trong ngoặc của bảng thuật ngữ** (vd giả: `term_vi: Sổ khách (sổ cái)`) và biến thể dùng để giải thích lần đầu: giữ, không gợi ý thay.
- Chữ ẩn dụ cho sinh động, không phải thuật ngữ (vd giả: "khách quen là vốn của quán"); chữ trùng mặt chữ nhưng khác nghĩa ("kênh" bán hàng / "kênh" YouTube).

Không chắc là một hay hai khái niệm → không gợi ý gộp; đưa vào "Cần bạn bổ sung": "<chữ A> và <chữ B> là một thứ hay hai thứ?".

## 4. Chọn tên chuẩn

1. Có trong bảng thuật ngữ → dùng `term_vi` của bảng (phần ngoài ngoặc).
2. Tác giả có câu định nghĩa → dùng đúng chữ trong câu đó.
3. Còn lại → chữ xuất hiện nhiều nhất; hoà nhau → chữ gần người đọc hơn (theo chân dung: chữ họ gõ tìm).
4. Bỏ dấu: theo kiểu đa số trong bài; repo có quy ước → theo quy ước.
5. Viết tắt: lần đầu viết đủ + tắt trong ngoặc ("chăm sóc khách hàng (CSKH)"), sau đó dùng một dạng.
6. Thuật ngữ có tên tiếng Anh trong bảng → lần nhắc đầu (thường ở mục định nghĩa) ghi "tên Việt (tên Anh)"; giúp cả người đọc lẫn máy tìm kiếm/AI nối khái niệm (xem `seo-geo-aeo.md`).

## 5. Thuật ngữ tác giả tự đặt

Dấu hiệu: cụm lạ, in đậm, có định nghĩa riêng, lặp lại như một khái niệm (vd giả: "cửa khách", "sổ người").

- Lần đầu xuất hiện phải có một câu định nghĩa ngắn **ngay tại chỗ**; chưa có → gợi ý `thêm` với `[điền: định nghĩa một câu]`.
- Dùng đúng một dạng suốt bài.
- Chưa có trong bảng thuật ngữ của repo → gợi ý riêng (mã T, cột Dòng = `<file bảng>:<chỗ>`) để tác giả cân nhắc thêm vào. Giá trị bắt buộc của bảng (id, tên Anh…) chưa có → hỏi ở mục "Cần bạn bổ sung", không đề xuất `[điền]` trong file cấu hình.

## 6. Viết gợi ý (mã T)

Mỗi khái niệm một mã. Mục 4 của báo cáo ghi phần phân tích:

```
Khái niệm: <mô tả ngắn>
Đang dùng: "<biến thể 1>" L.., L.. · "<biến thể 2>" L..
Chuẩn đề xuất: "<tên>" — vì <bảng thuật ngữ | câu định nghĩa L.. | đa số>
Giữ nguyên: L.. (lời nhân vật / giải thích lần đầu / ẩn dụ)
```

Mục 7 (bảng duyệt) ghi từng chỗ đổi theo `assets/mau-bao-cao.md`: Hiện tại = `nhiều chỗ`, Đề xuất = các cặp `` `đoạn nguyên văn` → `đoạn sau sửa` `` cách nhau bằng `<br>`, mỗi đoạn "trước" duy nhất trong file.

Mức: Cao = người đọc có thể hiểu thành hai thứ khác nhau; Vừa = chỉ lệch chữ, gây khựng; Thấp = bỏ dấu, gạch nối.
