"""Tests for star/scripts/progress.py (UC-504). Run: python3 -m unittest discover -s skills/star/scripts/tests"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS = os.path.join(SCRIPTS, "progress.py")
MAU = os.path.join(os.path.dirname(SCRIPTS), "assets", "mau")
TEMPLATE = {("I", None): "i.md", ("II", "đầy đủ"): "ii-day-du.md", ("II", "ngắn"): "ii-ngan.md",
            ("III", None): "iii.md", ("IV", None): "iv.md", ("V", None): "v.md"}
TODAY = "2026-10-17"
SUMMARY = {"Insight": "Khó hay dễ phụ thuộc vào vai ta đang đóng.", "Pattern": "—", "Tầng think": "Story",
           "One action tomorrow": "6h00 Chủ nhật 18/10 chạy 5km", "Người liên quan": "Vợ", "Đã làm": "chưa"}


def post_text(loai, ban=None, ngay=TODAY, status="xong", extra=(), answers=None, summary=None, title="Bài thử"):
    """A post built from the real template of its type/version; every code answered unless overridden."""
    with open(os.path.join(MAU, TEMPLATE[(loai, ban)]), encoding="utf-8") as f:
        text = f.read()
    answers = answers or {}
    summ = dict(SUMMARY, **(summary or {}))

    def fill(m):
        ans = answers.get(m.group(2), "Câu trả lời của bạn.")
        return m.group(1) if ans is None else m.group(1) + "\n\n" + ans

    text = re.sub(r"^(### (.+?) · .+)$", fill, text, flags=re.M)
    text = text.replace("# <tiêu đề bài>", "# " + title, 1)
    text = text.replace("- Ngày: YYYY-MM-DD", "- Ngày: " + ngay, 1)
    text = text.replace("- Trạng thái: nháp", "\n".join(["- Trạng thái: " + status] + list(extra)), 1)
    for key, val in summ.items():
        pattern = r"^- %s:.*$" % re.escape(key)
        text = re.sub(pattern, "" if val is None else ("- %s: %s" % (key, val)).rstrip(), text, count=1, flags=re.M)
    return text


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self._tmp.name, "nhat-ky")
        os.mkdir(self.dir)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def run_cli(self, *args, today=TODAY, directory=None):
        cmd = [sys.executable, PROGRESS, "--dir", directory or self.dir, "--today", today, *args]
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    def progress(self, today=TODAY):
        res = self.run_cli(today=today)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout

    def mark(self, *args):
        return subprocess.run([sys.executable, PROGRESS, *args], capture_output=True, text=True, encoding="utf-8")


class ProgressCountTest(Base):
    def test_counts_complete_posts_by_type_drafts_and_four_milestones(self):  # AC-1
        self.write("2026-10-15-i-nhat-ky-ngay.md", post_text("I", ngay="2026-10-15"))
        self.write("2026-10-16-ii-cai-nhau.md", post_text("II", "đầy đủ", ngay="2026-10-16"))
        self.write("2026-10-16-ii-viet-nhanh.md", post_text("II", "ngắn", ngay="2026-10-16"))
        self.write("2026-10-17-iii-thang-hop-dong.md", post_text("III", status="nháp"))
        out = self.progress()
        self.assertIn("Bài trọn vẹn: 3 (I: 1 · II: 2)", out)
        self.assertIn("Nháp: 1", out)
        self.assertIn("28 bài: còn 25 (10,7%) — Trí tuệ phát triển bằng 5 năm trước cộng lại (theo tài liệu)", out)
        self.assertIn("300 bài: còn 297 (1,0%) — Thu nhập x2 (theo tài liệu)", out)
        self.assertIn("1000 bài: còn 997 (0,3%) — Tốt nghiệp 5 bài học: sức khoẻ, thành công, hạnh phúc, ý nghĩa, "
                      "tự do (theo tài liệu)", out)
        self.assertIn("10000 bài: còn 9997 (< 0,1%) — Đa triệu phú đô la (theo tài liệu)", out)

    def test_milestone_reached_prints_dat(self):
        for i in range(30):
            self.write("p%02d.md" % i, post_text("I") if i < 28 else post_text("IV"))
        out = self.progress()
        self.assertIn("Bài trọn vẹn: 30 (I: 28 · IV: 2)", out)
        self.assertIn("28 bài: đạt", out)
        self.assertNotIn("28 bài: còn", out)
        self.assertIn("300 bài: còn 270 (10,0%)", out)

    def test_percent_rounds_half_up_to_one_decimal(self):
        for i in range(25):
            self.write("p%02d.md" % i, post_text("III"))
        out = self.progress()
        self.assertIn("28 bài: còn 3 (89,3%)", out)
        self.assertIn("1000 bài: còn 975 (2,5%)", out)
        self.assertIn("10000 bài: còn 9975 (0,3%)", out)

    def test_no_complete_post_shows_zero_percent_not_less_than(self):
        self.write("2026-10-17-v-sale.md", post_text("V", status="nháp"))
        out = self.progress()
        self.assertIn("Bài trọn vẹn: 0", out)
        self.assertIn("10000 bài: còn 10000 (0,0%)", out)
        self.assertNotIn("< 0,1%", out)

    def test_short_version_complete_without_gap_impact_or_packing(self):
        text = post_text("II", "ngắn")
        for code in ("GAP", "IMPACT", "NGUYÊN NHÂN", "PACKING", "MEASURE"):
            self.assertNotIn("### " + code, text)
        self.write("2026-10-17-ii-viet-nhanh.md", text)
        out = self.progress()
        self.assertIn("Bài trọn vẹn: 1 (II: 1)", out)
        self.assertNotIn("Cảnh báo", out)

    def test_packing_skipped_in_full_version_is_not_complete(self):
        self.write("2026-10-17-ii-cai-nhau.md", post_text("II", "đầy đủ", answers={"PACKING": "(bỏ qua)"}))
        out = self.progress()
        self.assertIn("Bài trọn vẹn: 0", out)
        self.assertRegex(out, r"Cảnh báo: .*2026-10-17-ii-cai-nhau\.md: .*PACKING")

    def test_answer_with_only_hint_line_counts_as_missing(self):
        hint = "> Gợi ý: Viết như camera ghi lại: ai, ở đâu, khi nào, nói câu gì, làm gì. Chưa đánh giá."
        self.write("2026-10-17-ii-cai-nhau.md", post_text("II", "đầy đủ", answers={"SITUATION": hint}))
        out = self.progress()
        self.assertIn("Bài trọn vẹn: 0", out)
        self.assertRegex(out, r"Cảnh báo: .*2026-10-17-ii-cai-nhau\.md: .*SITUATION")

    def test_unchosen_deep_code_does_not_break_completeness(self):
        answers = {"FEAR": "(không chọn)", "SHADOW": "(không chọn)", "BLINDSPOT": None}
        self.write("2026-10-17-ii-cai-nhau.md", post_text("II", "đầy đủ", answers=answers))
        out = self.progress()
        self.assertIn("Bài trọn vẹn: 1 (II: 1)", out)
        self.assertNotIn("Cảnh báo", out)


class ReminderTest(Base):
    def test_lists_one_action_not_done_from_earlier_days_only(self):  # AC-2
        old = self.write("2026-10-16-i-nhat-ky-ngay.md", post_text(
            "I", ngay="2026-10-16", summary={"One action tomorrow": "6h00 thứ bảy 17/10 chạy 5km"}))
        self.write("2026-10-17-i-nhat-ky-ngay.md", post_text(
            "I", summary={"One action tomorrow": "5h30 Chủ nhật 18/10 thiền 30 phút"}))
        out = self.progress()
        self.assertIn("6h00 thứ bảy 17/10 chạy 5km", out)
        self.assertIn(old, out)
        self.assertNotIn("5h30 Chủ nhật 18/10 thiền 30 phút", out)

    def test_lists_result_due_from_its_date_onward_only(self):  # AC-3
        extra = ("- Hẹn kết quả: 2026-10-17", "- Kết quả: chưa")
        path = self.write("2026-10-10-ii-chay-bo.md", post_text("II", "đầy đủ", ngay="2026-10-10", extra=extra))
        self.assertNotIn("đến hạn ghi kết quả", self.progress(today="2026-10-16").lower())
        for day in ("2026-10-17", "2026-10-20"):
            out = self.progress(today=day)
            self.assertIn("đến hạn ghi kết quả", out.lower())
            self.assertIn(path, out)

    def test_result_already_recorded_is_not_listed(self):
        extra = ("- Hẹn kết quả: 2026-10-17", "- Kết quả: đã ghi")
        self.write("2026-10-10-ii-chay-bo.md", post_text("II", "đầy đủ", ngay="2026-10-10", extra=extra))
        self.assertNotIn("đến hạn ghi kết quả", self.progress().lower())


class WarningTest(Base):
    def test_invalid_done_posts_are_named_with_reason_not_counted_and_exit_zero(self):  # AC-4
        self.write("a-thieu-ma.md", post_text("I", answers={"BIẾT ƠN": None}))
        self.write("b-thieu-tong-ket.md", post_text("III", summary={"Người liên quan": None}))
        self.write("c-tang-think.md", post_text("IV", summary={"Tầng think": "Sâu lắm"}))
        self.write("d-thieu-dau.md", post_text("V").replace("- Ngày: %s\n" % TODAY, ""))
        self.write("e-dung.md", post_text("V", summary={"Tầng think": "role-play"}))
        res = self.run_cli()
        self.assertEqual(res.returncode, 0)
        out = res.stdout
        self.assertIn("Bài trọn vẹn: 1 (V: 1)", out)
        self.assertRegex(out, r"Cảnh báo: .*a-thieu-ma\.md: .*BIẾT ƠN")
        self.assertRegex(out, r"Cảnh báo: .*b-thieu-tong-ket\.md: .*Người liên quan")
        self.assertRegex(out, r"Cảnh báo: .*c-tang-think\.md: .*Tầng think")
        self.assertRegex(out, r"Cảnh báo: .*d-thieu-dau\.md: .*Ngày")
        self.assertNotIn("e-dung.md", out)


class CaseTest(Base):
    def test_case_status_takes_highest_per_case_and_counts_done_plus_sent(self):  # AC-5
        full = ("II", "đầy đủ")
        self.write("c01.md", post_text(*full, extra=("- Case: 01",)))
        self.write("c05.md", post_text(*full, extra=("- Đã gửi mentor: 2026-10-16", "- Case: 05")))
        self.write("c07.md", post_text(*full, status="nháp", extra=("- Case: 07",)))
        self.write("c09a.md", post_text(*full, status="nháp", extra=("- Case: 09",)))
        self.write("c09b.md", post_text(*full, extra=("- Case: 09",)))
        out = self.progress()
        self.assertIn("Case đã xong: 3/28", out)
        self.assertIn("01 Xong", out)
        self.assertIn("05 Đã gửi mentor", out)
        self.assertIn("07 Đang viết", out)
        self.assertIn("09 Xong", out)

    def test_case_28_done_only_with_complete_type_ii_and_type_iv(self):
        self.write("c28-ii.md", post_text("II", "đầy đủ", extra=("- Case: 28",)))
        out = self.progress()
        self.assertIn("28 Đang viết", out)
        self.assertIn("Case đã xong: 0/28", out)
        self.write("c28-iv.md", post_text("IV", extra=("- Case: 28",)))
        out = self.progress()
        self.assertIn("28 Xong", out)
        self.assertIn("Case đã xong: 1/28", out)


class MarkTest(Base):
    def read(self, path):
        with open(path, "rb") as f:
            return f.read()

    def test_da_lam_changes_only_the_summary_line(self):  # AC-6
        path = self.write("x.md", post_text("I"))
        before = self.read(path)
        res = self.mark("--da-lam", path)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.read(path), before.replace("- Đã làm: chưa".encode(), "- Đã làm: rồi".encode()))

    def test_ket_qua_changes_only_the_header_line(self):  # AC-6
        path = self.write("x.md", post_text("II", "đầy đủ", extra=("- Hẹn kết quả: 2026-10-25", "- Kết quả: chưa")))
        before = self.read(path)
        res = self.mark("--ket-qua", path)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.read(path), before.replace("- Kết quả: chưa".encode(), "- Kết quả: đã ghi".encode()))

    def test_gui_mentor_inserts_after_status_then_replaces_date(self):  # AC-6
        path = self.write("x.md", post_text("II", "đầy đủ", extra=("- Case: 05",)))
        before = self.read(path)
        res = self.mark("--gui-mentor", path, "--ngay", "2026-10-17")
        self.assertEqual(res.returncode, 0, res.stderr)
        inserted = before.replace("- Trạng thái: xong\n".encode(),
                                  "- Trạng thái: xong\n- Đã gửi mentor: 2026-10-17\n".encode())
        self.assertEqual(self.read(path), inserted)
        res = self.mark("--gui-mentor", path, "--ngay", "2026-10-20")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.read(path), inserted.replace(b"2026-10-17\n- Case", b"2026-10-20\n- Case"))

    def test_mark_refuses_and_keeps_file_when_line_missing_or_duplicated(self):  # AC-6
        crlf = post_text("I").replace("\n", "\r\n")
        cases = [
            ("--da-lam", post_text("I", summary={"Đã làm": "rồi"})),
            ("--da-lam", post_text("I") + "\n- Đã làm: chưa\n"),
            ("--ket-qua", post_text("I")),
            ("--ket-qua", post_text("II", "đầy đủ", extra=("- Kết quả: chưa", "- Kết quả: chưa"))),
        ]
        for flag, text in cases:
            path = self.write("y.md", text)
            before = self.read(path)
            res = self.mark(flag, path)
            self.assertEqual(res.returncode, 1, (flag, res.stdout))
            self.assertIn("Lỗi", res.stdout + res.stderr)
            self.assertEqual(self.read(path), before)
        path = self.write("z.md", crlf)
        self.assertEqual(self.mark("--da-lam", path).returncode, 0)
        self.assertEqual(self.read(path), crlf.replace("- Đã làm: chưa", "- Đã làm: rồi").encode())


class MissingDirTest(Base):
    def test_missing_directory_says_no_posts_and_is_not_created(self):  # AC-7
        missing = os.path.join(self.dir, "chua-co")
        res = self.run_cli(directory=missing)
        self.assertEqual(res.returncode, 0)
        self.assertIn("chưa có bài nào ở %s" % missing, res.stdout)
        self.assertNotIn("git", res.stdout)
        self.assertFalse(os.path.exists(missing))

    def test_directory_inside_git_work_tree_adds_one_warning_line(self):  # AC-7
        os.mkdir(os.path.join(self._tmp.name, ".git"))
        missing = os.path.join(self.dir, "chua-co")
        res = self.run_cli(directory=missing)
        self.assertEqual(res.returncode, 0)
        self.assertIn("chưa có bài nào ở %s" % missing, res.stdout)
        self.assertEqual(sum("git" in line for line in res.stdout.splitlines()), 1)
        self.write("2026-10-17-i-nhat-ky-ngay.md", post_text("I"))
        out = self.progress()
        self.assertEqual(sum("git" in line for line in out.splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
