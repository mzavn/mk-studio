"""Tests for mk-exec-review/scripts/check_report.py. Run: python3 -m unittest discover -s skills/mk-exec-review/scripts/tests"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "check_report.py")

ARTICLE = """---
title: "Một khách, ba hồ sơ"
---

Quán trà sữa của chị Mai bán qua Zalo và Shopee.

Hơn nữa, việc ghi sổ khách đóng vai trò then chốt trong tăng trưởng.

Sổ khách giúp chị biết ai mua lại. Sổ khách là sổ gốc.
"""


def report(*rows):
    head = "# Phản biện\n\n## 7. Danh sách gợi ý để duyệt\n\n| Mã | Mức | Dòng | Loại | Hiện tại | Đề xuất | Vì sao |\n|---|---|---|---|---|---|---|\n"
    return head + "\n".join(rows) + "\n\n## 8. Giữ nguyên\n\n| X1 | Cao | L1 | chữ | `zzz` | `y` | không phải bảng 7 |\n"


class CheckReport(unittest.TestCase):
    def run_check(self, *rows, article=ARTICLE):
        tmp = tempfile.mkdtemp()
        art, rep = os.path.join(tmp, "bai.md"), os.path.join(tmp, "bao-cao.md")
        with open(art, "w", encoding="utf-8") as fh:
            fh.write(article)
        with open(rep, "w", encoding="utf-8") as fh:
            fh.write(report(*rows))
        res = subprocess.run([sys.executable, CHECK, rep, art], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.summary = res.stdout
        return dict(l.split(" ", 1) for l in res.stdout.strip().split("\n") if re.match(r"^[A-Z]\d+ ", l))

    def test_exact_unique_snippet_on_cited_line_passes(self):
        out = self.run_check("| A1 | Cao | L7 | chữ | `Hơn nữa, việc` | `Việc` | từ nối |")
        self.assertEqual(out["A1"], "OK")

    def test_snippet_missing_or_repeated_or_on_another_line_is_flagged(self):
        out = self.run_check(
            "| A1 | Cao | L7 | chữ | `vai trò chủ chốt` | `vai trò` | x |",
            "| T1 | Vừa | L9 | thuật ngữ | nhiều chỗ | `Sổ khách` → `Sổ người` | x |",
            "| A2 | Vừa | L9 | chữ | `bán qua Zalo` | `bán trên Zalo` | x |")
        self.assertIn("⚠ không khớp file: `vai trò chủ chốt` 0 lần", out["A1"])
        self.assertIn("⚠ trùng: `Sổ khách` 2 lần", out["T1"])
        self.assertIn("lệch dòng: `bán qua Zalo` ở L5", out["A2"])

    def test_word_edit_rewriting_more_than_three_syllables_is_relabelled_as_sentence(self):
        out = self.run_check("| A1 | Cao | L7 | chữ | `đóng vai trò then chốt trong tăng trưởng` | "
                             "`quyết định quán có giữ được khách quen` | x |")
        self.assertIn("đổi nhãn → câu", out["A1"])

    def test_word_edit_that_inserts_new_words_or_foreign_words_is_flagged(self):
        out = self.run_check(
            "| A1 | Cao | L5 | chữ | `bán qua Zalo` | `bán data qua Zalo` | x |",
            "| A2 | Vừa | L9 | chữ | `là sổ gốc` | `là CRM gốc` | x |")
        self.assertIn("đổi nhãn → câu: chèn chữ mới", out["A1"])
        self.assertIn("chữ nước ngoài mới: data", out["A1"])
        self.assertIn("chữ nước ngoài mới: CRM", out["A2"])
        self.assertNotIn("đổi nhãn", out["A2"])

    def test_rerun_after_editing_marks_applied_codes_without_warning(self):
        out = self.run_check("| A1 | Cao | L5 | chữ | `bán qua Zalo` | `bán trên Zalo` | x |",
                             article=ARTICLE.replace("bán qua Zalo", "bán trên Zalo"))
        self.assertEqual(out["A1"], "đã áp: `bán trên Zalo`")
        self.assertIn("Tổng: 1 mã · 0 có ⚠", self.summary)

    def test_heading_edit_must_be_structure_and_insertion_must_keep_the_original(self):
        article = ARTICLE + "\n## Gộp khách {#merge}\n"
        out = self.run_check(
            "| T1 | Thấp | L11 | chữ | `## Gộp khách` | `## Hợp nhất khách` | x |",
            "| C1 | Cao | L9 | thêm | `Sổ khách là sổ gốc.` | `[điền: định nghĩa sổ gốc]` | x |",
            "| C2 | Cao | L9 | thêm | `Sổ khách là sổ gốc.` | `Sổ khách là sổ gốc. [điền: định nghĩa]` | x |",
            article=article)
        self.assertIn("đổi nhãn → cấu trúc: đổi tiêu đề mục L11", out["T1"])
        self.assertIn("thêm nhưng xoá đoạn gốc", out["C1"])
        self.assertEqual(out["C2"], "OK")

    def test_softening_a_claim_or_adding_invisible_characters_is_flagged(self):
        out = self.run_check(
            "| A1 | Cao | L9 | chữ | `Sổ khách là sổ gốc.` | `Sổ khách có thể là sổ gốc.` | x |",
            "| A2 | Vừa | L5 | chữ | `bán qua Zalo` | `bán qua Za\u200blo` | x |")
        self.assertIn('làm mềm khẳng định: thêm "có thể"', out["A1"])
        self.assertIn("ký tự vô hình mới: U+200B", out["A2"])

    def test_gaps_in_numbering_and_missing_report_sections_are_reported(self):
        self.run_check("| A1 | Cao | L7 | chữ | `Hơn nữa, việc` | `Việc` | x |",
                       "| A3 | Cao | L7 | chữ | `then chốt` | `chính` | x |")
        self.assertIn("Đánh mã: thiếu A2", self.summary)
        self.assertIn("Mục báo cáo: thiếu mục 1, 2, 3, 4, 5, 6, 9", self.summary)

    def test_meta_label_must_match_frontmatter_and_new_digits_are_flagged(self):
        out = self.run_check(
            "| S1 | Cao | L2 | chữ | `Một khách, ba hồ sơ` | `Một khách, 3 hồ sơ` | x |",
            "| S2 | Vừa | L5 | meta | `bán qua Zalo và Shopee` | `bán qua Zalo [điền: 2 kênh khác]` | x |")
        self.assertIn("đổi nhãn → meta", out["S1"])
        self.assertIn("số mới: 3", out["S1"])
        self.assertIn("đổi nhãn → không meta", out["S2"])
        self.assertNotIn("số mới", out["S2"])

    def test_meta_options_each_checked_and_pipes_inside_backticks_do_not_split_cells(self):
        out = self.run_check("| S1 | Cao | L2 | meta | `title: \"Một khách, ba hồ sơ\"` | "
                             "1: `title: \"Một khách | ba hồ sơ\"` → `x`<br>2: `Một khách, ba hồ sơ` → `Bốn hồ sơ` | x |")
        self.assertIn("không khớp file: `title: \"Một khách | ba hồ sơ\"` 0 lần", out["S1"])
        self.assertNotIn("`Một khách, ba hồ sơ`", out["S1"])  # phương án 2 khớp đúng 1 lần ở frontmatter

    def test_bad_code_level_kind_duplicates_and_outside_files(self):
        out = self.run_check(
            "| B1 | Rất cao | L7 | sửa | `Hơn nữa` | `` | x |",
            "| T2 | Thấp | config/glossary.yaml:cuối file | thuật ngữ | — | thêm `sổ gốc` | x |",
            "| T3 | Thấp | L9 | chữ | `là sổ gốc` | `là sổ chính` | x |",
            "| T3 | Thấp | L9 | chữ | `là sổ gốc` | `là sổ chính` | x |")
        self.assertIn("sai khuôn (mã B1, mức Rất cao, loại sửa)", out["B1"])
        self.assertIn("ngoài bài — kiểm tay: config/glossary.yaml:cuối file", out["T2"])
        self.assertIn("sai khuôn: mã trùng", out["T3"])  # dòng sau ghi đè dòng đầu trong dict

    def test_changing_link_target_or_adding_image_or_html_is_flagged_even_for_word_edits(self):
        article = ARTICLE + "\nXem [hướng dẫn](https://vi-du.vn/a) ở đây.\n"
        out = self.run_check(
            "| A1 | Cao | L11 | chữ | `[hướng dẫn](https://vi-du.vn/a)` | `[hướng dẫn](https://khac.vn/a)` | x |",
            "| A2 | Cao | L11 | chữ | `ở đây.` | `ở đây. ![](https://khac.vn/p.png)` | x |",
            "| A3 | Vừa | L11 | chữ | `ở đây.` | `<b>ở đây.</b>` | x |",
            "| A4 | Vừa | L11 | chữ | `Xem [hướng dẫn]` | `Đọc [hướng dẫn]` | x |",
            article=article)
        for code in ("A1", "A2", "A3"):
            self.assertIn("đổi link/ảnh/neo/HTML", out[code], code)
        self.assertNotIn("đổi link", out["A4"])  # chữ quanh link đổi, đích link giữ nguyên

    def test_overlong_table_row_exits_1(self):
        tmp = tempfile.mkdtemp()
        rep, art = os.path.join(tmp, "r.md"), os.path.join(tmp, "a.md")
        with open(rep, "w", encoding="utf-8") as fh:
            fh.write(report("| A1 | Cao | L7 | chữ | `" + "`" * 6000 + "` | `x` | x |"))
        with open(art, "w", encoding="utf-8") as fh:
            fh.write(ARTICLE)
        res = subprocess.run([sys.executable, CHECK, rep, art], capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 1)
        self.assertIn("dài hơn 5000 ký tự", res.stderr)

    def test_missing_section_7_exits_1(self):
        tmp = tempfile.mkdtemp()
        rep = os.path.join(tmp, "r.md")
        with open(rep, "w", encoding="utf-8") as fh:
            fh.write("# Báo cáo\n\nkhông có bảng\n")
        res = subprocess.run([sys.executable, CHECK, rep, rep], capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)
        self.assertIn("không thấy mục `## 7.`", res.stderr)


if __name__ == "__main__":
    unittest.main()
