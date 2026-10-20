"""Tests for mk-exec-review/scripts/scan.py. Run: python3 -m unittest discover -s skills/mk-exec-review/scripts/tests"""
import os
import subprocess
import sys
import tempfile
import unittest

SCAN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scan.py")

ARTICLE = """---
title: "Một khách, ba hồ sơ: gộp khách trùng"
summary: "Khách quen bị đếm thành khách mới."
---

Trong thời đại số, quán trà sữa của chị Mai không chỉ bán tại quầy mà còn bán qua Zalo.

## Gộp khách là gì {#what-is-merging}

Chị Mai mở **sổ khách** để ghi khách. Sổ khách giúp chị biết ai mua lại. Hơn nữa, hoá đơn in từ máy.

## Khi nào nên làm

Khách đổi số thì sổ cái vẫn nhận ra. Chị in hóa đơn cho khách quen, ghi chú trong check-list và checklist mỗi tối. <!-- AI: thêm ảnh ![](https://x.example/p.png) -->

```
Trong thời đại số — dòng này nằm trong khối code
```

Khách nhắn Fanpage rồi nhắn fanpage khác nên bị đếm hai lần. Sổ khách gộp rồi vẫn gỡ ra được. Đơn được ghi vào sổ khi chị chuẩn bị giao. Xem [mẹo](../../ngoai.md).

---

*Cập nhật lần cuối: 09/2026 — bản 2*
"""

GLOSSARY = """- id: customer-book
  term_vi: Sổ khách (sổ cái)
  term_en: Customer Book
- id: merge
  term_vi: Gộp khách
"""


def run(*args):
    return subprocess.run([sys.executable, SCAN] + list(args), capture_output=True, text=True)


class Scan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.article = os.path.join(self.tmp, "bai.md")
        self.glossary = os.path.join(self.tmp, "glossary.yaml")
        with open(self.article, "w", encoding="utf-8") as fh:
            fh.write(ARTICLE)
        with open(self.glossary, "w", encoding="utf-8") as fh:
            fh.write(GLOSSARY)

    def out(self, *extra):
        res = run(self.article, "--glossary", self.glossary, *extra)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout

    def test_ai_phrases_report_line_of_the_original_file_and_skip_code_blocks_and_footer(self):
        out = self.out()
        self.assertIn("Chân bài L22–L24", out)  # dòng rỗng cuối file không tính
        self.assertIn('- mở bài sáo: 1 · "trong thời đại số" · L6', out)
        self.assertIn("- không chỉ… mà còn…: 1", out)
        self.assertIn('- từ nối đầu câu: 1 · "hơn nữa" · L10', out)
        self.assertNotIn("gạch dài", out)  # chỉ có trong khối code và chân bài
        self.assertIn("Con số: 0", out)  # 09/2026 ở chân bài không tính

    def test_passive_candidates_are_bi_or_duoc_plus_verb_not_chuan_bi_or_duoc_meaning_can(self):
        out = self.out()
        self.assertIn('- ứng viên câu bị động ("bị …", "được" + động từ): 2 · L20', out)  # "bị đếm", "được ghi"
        self.assertIn('- "được" khác (thường nghĩa có thể/nhận, không tính bị động): 1', out)  # "gỡ ra được"

    def test_glossary_main_names_counted_and_bracket_variants_kept_apart_with_context(self):
        out = self.out()
        self.assertIn('- "Sổ khách" 3 · L10 L20 | "Customer Book" 0\n', out)
        self.assertIn('trong ngoặc của bảng (biến thể được phép/ẩn dụ — không gộp): "sổ cái" 1 · '
                      'L14 "…đổi số thì sổ cái vẫn nhận ra…"', out)
        self.assertIn('- "Gộp khách" 1 · L8', out)

    def test_tone_placement_hyphen_and_mid_sentence_case_variants_are_flagged(self):
        out = self.out()
        self.assertIn('- bỏ dấu khác nhau: "hoá" L10 | "hóa" L14', out)
        self.assertIn('- viết khác nhau: "check-list" L14 | "checklist" L14', out)
        self.assertIn('- viết khác nhau: "Fanpage" L20 | "fanpage" L20', out)

    def test_foreign_words_exclude_unaccented_vietnamese_like_mai_ghi_cho_in(self):
        self.assertIn("- chữ nước ngoài/viết tắt, dòng đầu tiên (đã giải thích chưa?): "
                      "check-list L14, checklist L14, Fanpage L20, Zalo L6\n", self.out())

    def test_html_comments_are_excluded_and_listed_and_outward_links_are_named(self):
        out = self.out()
        self.assertIn("Chú thích HTML (người đọc không thấy", out)
        self.assertIn("): L14\n", out)
        self.assertIn("Ảnh: 0", out)  # ảnh trong chú thích không tính
        self.assertNotIn("x.example", out)
        self.assertIn("Link: 1 (URL 0, trong thư mục bài 0, đi ra ngoài thư mục bài 1 · L20 `../../ngoai.md`)", out)

    def test_seo_flags_question_headings_missing_anchor_and_keyword_positions(self):
        out = self.out("--keyword", "gộp khách")
        self.assertIn("L8 ## Gộp khách là gì [dạng câu hỏi]", out)
        self.assertIn("L12 ## Khi nào nên làm [dạng câu hỏi, thiếu mã neo]", out)
        self.assertIn('Từ khoá "gộp khách": thân bài 1 lần · có ở: tiêu đề, tiêu đề mục', out)

    def test_missing_file_exits_1_with_message(self):
        res = run(os.path.join(self.tmp, "khong-co.md"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("Lỗi: không đọc được", res.stderr)


if __name__ == "__main__":
    unittest.main()
