"""Tests for mk-subtitle/scripts/subtitle.py. Run: python3 -m unittest discover -s skills/mk-subtitle/scripts/tests"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "subtitle.py")

# VTT tự động kiểu YouTube (dữ liệu giả): dòng đầu cue chỉ có dấu cách, cue chuyển tiếp 10ms, mốc từng từ.
YOUTUBE = """WEBVTT
Kind: captions
Language: vi

00:00:00.500 --> 00:00:02.000 align:start position:0%
 
Chào.

00:00:02.000 --> 00:00:02.010 align:start position:0%
Chào.
 

00:00:02.010 --> 00:00:06.000 align:start position:0%
Chào.
Quán<00:00:02.400><c> mình</c><00:00:02.700><c> à</c><00:00:03.000><c> bán</c><00:00:03.300><c> trà</c><00:00:03.600><c> sữa.</c>

00:00:06.000 --> 00:00:06.010 align:start position:0%
Quán mình à bán trà sữa.
 

00:00:06.010 --> 00:00:10.000 align:start position:0%
Quán mình à bán trà sữa.
[âm<00:00:06.300><c> nhạc]</c><00:00:07.000><c> Thế</c><00:00:07.200><c> à?</c><00:00:07.600><c> &gt;&gt;</c><00:00:07.800><c> Ừ,</c><00:00:08.000><c> đúng</c><00:00:08.300><c> rồi.</c>

00:00:10.000 --> 00:00:13.000 align:start position:0%
Thế à? &gt;&gt; Ừ, đúng rồi.
Mình<00:00:10.300><c> mình</c><00:00:10.600><c> kiểu</c><00:00:10.800><c> như</c><00:00:11.000><c> ừm</c><00:00:11.400><c> mở</c><00:00:11.700><c> thêm.</c>
"""

SRT = """1
00:00:01,000 --> 00:00:03,000
Ừm

2
00:00:04,000 --> 00:00:08,000
Hôm nay ờ quán đông khách.

3
00:00:09,000 --> 00:00:10,000
[Vỗ tay]
"""


def run(*args):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def path(self, name, text=None):
        p = os.path.join(self.d, name)
        if text is not None:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        return p

    def read(self, name):
        with open(self.path(name), encoding="utf-8") as fh:
            return fh.read()

    def ok(self, *args):
        res = run(*args)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout

    def fillers(self, src):
        self.ok("fillers", src, "--out", self.path("f.tsv"), "--more", "kiểu như")
        with open(self.path("f.tsv"), encoding="utf-8") as fh:
            return {r["tu"] + "@" + r["bat_dau"]: r for r in csv.DictReader(fh, delimiter="\t")}


class YouTubeInput(Base):
    def test_words_keep_their_own_times_and_skip_transitions_annotations_and_speaker_marks(self):
        rows = self.fillers(self.path("in.vtt", YOUTUBE))
        mid = rows["à@00:00:02,700"]
        self.assertEqual((mid["nhom"], mid["ket_thuc"], mid["do_chinh_xac"]), ("A", "00:00:03,000", "chính xác (từng từ)"))
        self.assertEqual(mid["ngu_canh"], "Chào. Quán mình [à] bán trà sữa. Thế")
        self.assertNotIn("nhạc]", " ".join(r["ngu_canh"] for r in rows.values()))
        self.assertNotIn(">>", " ".join(r["ngu_canh"] for r in rows.values()))

    def test_meaningful_positions_go_to_group_b_and_hesitations_to_group_a(self):
        rows = self.fillers(self.path("in.vtt", YOUTUBE))
        self.assertEqual(rows["à?@00:00:07,200"]["nhom"], "B")       # Thế à? — tiểu từ hỏi
        self.assertEqual(rows["Ừ,@00:00:07,800"]["nhom"], "B")       # Ừ, đúng rồi. — câu đáp
        self.assertEqual(rows["mình@00:00:10,300"]["nhom"], "A")     # lặp trong cụm (vấp) → đề xuất cắt
        self.assertEqual(rows["kiểu@00:00:10,600"]["nhom"], "B")     # cụm người dùng thêm
        self.assertEqual(rows["như@00:00:10,800"]["nhom"], "B")
        self.assertEqual(rows["ừm@00:00:11,000"]["nhom"], "A")

    def test_clean_removes_only_approved_words_resegments_and_writes_exact_cuts(self):
        src = self.path("in.vtt", YOUTUBE)
        self.fillers(src)
        out = self.ok("clean", src, "--fillers", self.path("f.tsv"), "--approve", "A", "--out-srt",
                      self.path("vi.srt"), "--out-cuts", self.path("cuts"))
        self.assertIn("Đã bỏ 3 từ", out)  # 2 âm đệm + 1 lặp trong cụm (vấp)
        vi = self.read("vi.srt")
        self.assertIn("Chào. Quán mình bán trà sữa.", vi)   # cue "Chào." quá ngắn → ghép với cue sau
        self.assertIn("2\n00:00:07,000 --> 00:00:09,000\n- Thế à?\n- Ừ, đúng rồi.\n", vi)  # >> đổi người nói → hội thoại
        self.assertIn("Mình kiểu như mở thêm.", vi)
        with open(self.path("cuts.csv"), encoding="utf-8") as fh:
            cuts = list(csv.DictReader(fh))
        self.assertEqual([(c["bat_dau"], c["ket_thuc"], c["do_chinh_xac"]) for c in cuts],
                         [("00:00:02,700", "00:00:03,000", "chính xác"), ("00:00:10,300", "00:00:10,600", "chính xác"),
                          ("00:00:11,000", "00:00:11,400", "chính xác")])
        self.assertIn("✂", self.read("cuts.srt"))

    def test_retime_moves_later_cues_back_by_the_cut_time(self):
        src = self.path("in.vtt", YOUTUBE)
        self.fillers(src)
        self.ok("clean", src, "--fillers", self.path("f.tsv"), "--approve", "A", "--out-srt", self.path("vi.srt"),
                "--out-cuts", self.path("cuts"))
        self.ok("retime", self.path("vi.srt"), "--cuts", self.path("cuts.csv"), "--out", self.path("vi.cut.srt"))
        cut = self.read("vi.cut.srt")
        self.assertIn("00:00:06,700 --> ", cut)       # 07,000 − 0,3 giây đã cắt trước đó
        self.assertNotIn("00:00:07,000 --> ", cut)


class CueInput(Base):
    def test_srt_keeps_cue_bounds_marks_inline_cuts_as_estimates_and_drops_emptied_cues(self):
        src = self.path("in.srt", SRT)
        rows = self.fillers(src)
        self.assertEqual(rows["Ừm@00:00:01,000"]["do_chinh_xac"], "chính xác (cả cue)")
        self.assertEqual(rows["ờ@00:00:05,184"]["do_chinh_xac"], "ước lượng")
        self.ok("clean", src, "--fillers", self.path("f.tsv"), "--approve", "all", "--out-srt", self.path("vi.srt"),
                "--out-cuts", self.path("cuts"))
        self.assertEqual(self.read("vi.srt"), "1\n00:00:04,000 --> 00:00:08,000\nHôm nay quán đông khách.\n\n")
        res = run("retime", self.path("vi.srt"), "--cuts", self.path("cuts.csv"), "--out", self.path("x.srt"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("ước lượng", res.stderr)
        self.assertFalse(os.path.exists(self.path("x.srt")))


class Approval(Base):
    def setUp(self):
        super().setUp()
        self.src = self.path("in.vtt", YOUTUBE)
        self.fillers(self.src)

    def clean(self, approve, reject=""):
        return run("clean", self.src, "--fillers", self.path("f.tsv"), "--approve", approve, "--reject", reject,
                   "--out-srt", self.path("o%d.srt" % len(os.listdir(self.d))), "--out-cuts",
                   self.path("c%d" % len(os.listdir(self.d))))

    def test_ranges_and_rejections_select_exact_codes(self):
        res = self.clean("F001-F003", "F002")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Đã bỏ 2 từ", res.stdout)

    def test_unknown_code_or_word_is_refused_and_nothing_is_written(self):
        before = sorted(os.listdir(self.d))
        for spec in ("F099", "xoá hết"):
            res = self.clean(spec)
            self.assertEqual(res.returncode, 1, spec)
            self.assertIn("Lỗi:", res.stderr)
        self.assertEqual(sorted(os.listdir(self.d)), before)

    def test_fillers_file_from_another_input_is_refused(self):
        other = self.path("other.vtt", YOUTUBE.replace("Quán<", "Tiệm<"))
        res = run("clean", other, "--fillers", self.path("f.tsv"), "--approve", "A", "--out-srt",
                  self.path("x.srt"), "--out-cuts", self.path("x"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("không khớp file đầu vào", res.stderr)

    def test_existing_output_is_never_overwritten(self):
        self.path("o.srt", "giữ nguyên")
        res = run("clean", self.src, "--fillers", self.path("f.tsv"), "--approve", "A", "--out-srt",
                  self.path("o.srt"), "--out-cuts", self.path("c"))
        self.assertEqual(res.returncode, 1)
        self.assertEqual(self.read("o.srt"), "giữ nguyên")


class Layout(Base):
    def test_long_speech_is_split_into_cues_of_at_most_two_lines_within_the_line_limit(self):
        words = " ".join("<00:00:%02d.%03d><c> chữ%d</c>" % (1 + i // 4, i % 4 * 250, i) for i in range(40))
        text = "WEBVTT\n\n00:00:01.000 --> 00:00:12.000\n \nMở" + words + "\n"
        src = self.path("long.vtt", text)
        self.ok("fillers", src, "--out", self.path("f.tsv"))
        self.ok("clean", src, "--fillers", self.path("f.tsv"), "--approve", "", "--out-srt", self.path("o.srt"),
                "--out-cuts", self.path("c"))
        out = self.ok("check", self.path("o.srt"), "--max-cps", "100", "--min-dur", "0")
        self.assertIn("Tổng: 0 lỗi · 0 cảnh báo", out)
        self.assertGreater(self.read("o.srt").count("-->"), 2)


class EditRoundTrip(Base):
    def setUp(self):
        super().setUp()
        self.srt = self.path("vi.srt", "1\n00:00:01,000 --> 00:00:03,000\nbí trích\n\n"
                                       "2\n00:00:04,000 --> 00:00:06,000\nmở thêm quán\n\n")
        self.ok("export", self.srt, "--out", self.path("t.md"))

    def test_edited_text_is_rebuilt_with_original_timings_and_matches_as_reference(self):
        text = self.read("t.md").replace("bí trích", "Bitrix24")
        self.path("t2.md", text)
        out = self.ok("build", self.srt, "--text", self.path("t2.md"), "--out", self.path("vi2.srt"))
        self.assertIn("1 cue đổi chữ", out)
        self.assertIn("00:00:01,000 --> 00:00:03,000\nBitrix24", self.read("vi2.srt"))
        self.ok("check", self.path("vi2.srt"), "--ref", self.srt)

    def test_changed_timing_missing_cue_or_empty_text_is_refused(self):
        base = self.read("t.md")
        for bad, msg in ((base.replace("00:00:04,000", "00:00:04,500"), "đổi mốc thời gian"),
                         (base.split("\n[2]")[0], "có 1 khối"),
                         (base.replace("mở thêm quán", ""), "trống chữ")):
            self.path("bad.md", bad)
            res = run("build", self.srt, "--text", self.path("bad.md"), "--out", self.path("x.srt"))
            self.assertEqual(res.returncode, 1, msg)
            self.assertIn(msg, res.stderr)
            self.assertFalse(os.path.exists(self.path("x.srt")))

    def test_bo_ca_cau_bang_dong_danh_dau_giu_moc_cau_con_lai(self):
        self.path("drop.md", self.read("t.md").replace("bí trích", "[bỏ câu]"))
        out = self.ok("build", self.srt, "--text", self.path("drop.md"), "--out", self.path("vi2.srt"))
        self.assertIn("bỏ cue [1]", out)
        self.assertEqual(self.read("vi2.srt"), "1\n00:00:04,000 --> 00:00:06,000\nmở thêm quán\n\n")


class Check(Base):
    def test_overlap_and_reference_mismatch_fail_while_reading_speed_only_warns(self):
        a = self.path("a.srt", "1\n00:00:01,000 --> 00:00:03,000\nmột\n\n2\n00:00:02,500 --> 00:00:04,000\nhai\n\n")
        res = run("check", a)
        self.assertEqual(res.returncode, 1)
        self.assertIn("chồng lên cue trước", res.stdout)
        fast = self.path("f.srt", "1\n00:00:01,000 --> 00:00:01,800\nmột câu rất dài đọc không kịp\n\n")
        res = run("check", fast)
        self.assertEqual(res.returncode, 0)
        self.assertIn("ký tự/giây", res.stdout)
        res = run("check", fast, "--ref", a)
        self.assertEqual(res.returncode, 1)
        self.assertIn("khác bản đối chiếu", res.stdout)

    def test_english_file_with_leftover_vietnamese_is_flagged(self):
        en = self.path("en.srt", "1\n00:00:01,000 --> 00:00:04,000\nWe open at nine.\n\n"
                                 "2\n00:00:05,000 --> 00:00:08,000\nmình mở thêm quán\n\n")
        out = self.ok("check", en, "--lang", "en")
        self.assertIn("[2] còn chữ có dấu tiếng Việt", out)
        self.assertNotIn("[1] còn chữ", out)


def youtube(words):
    """VTT kiểu YouTube một khối, mỗi từ cách nhau 0,3 giây bắt đầu từ giây 1."""
    tagged = "".join("<00:00:%02d.%03d><c> %s</c>" % ((1300 + 300 * k) // 1000, (1300 + 300 * k) % 1000, w)
                     for k, w in enumerate(words[1:]))
    return "WEBVTT\n\n00:00:01.000 --> 00:00:30.000\n \n%s%s\n" % (words[0], tagged)


class GroupRules(Base):
    def test_reply_after_question_and_name_calls_are_not_group_a(self):
        rows = self.fillers(self.path("in.vtt", youtube(
            "Chiều nay họp đúng không Nhi? Ừ đúng rồi. Minh à xem lại giúp chị nhé quán mình ờ đông khách".split())))
        groups = {r["tu"]: r["nhom"] for r in rows.values()}
        self.assertEqual(groups, {"Ừ": "B", "à": "B", "ờ": "A"})

    def groups(self, sentence):
        rows = self.fillers(self.path("g%d.vtt" % len(os.listdir(self.d)), youtube(sentence.split())))
        return [(r["tu"], r["nhom"], r["ly_do"]) for r in sorted(rows.values(), key=lambda r: int(r["vi_tri"]))]

    def test_lap_qua_dau_cau_la_giu(self):
        got = self.groups("Quán mở cửa lúc bảy giờ. Giờ đó khách đông lắm")
        self.assertEqual([(t, g) for t, g, _ in got], [("Giờ", "G")])
        self.assertIn("dấu câu", got[0][2])

    def test_tu_lay_va_nhan_manh_la_giu(self):
        got = self.groups("khách đến dần dần đông lên trà rất rất ngon")
        self.assertEqual([(t, g) for t, g, _ in got], [("dần", "G"), ("rất", "G")])
        self.assertTrue(all("láy" in why for _, _, why in got))

    def test_lap_trong_cum_la_de_xuat_cat(self):
        got = self.groups("chị gửi gửi file cho em nhé")
        self.assertEqual([(t, g) for t, g, _ in got], [("gửi", "A")])
        self.assertIn("vấp", got[0][2])

    def test_sau_tu_xung_ho_la_can_nghe_lai(self):
        got = self.groups("Alo mẹ à mẹ nghe con nói này. Các em à hôm nay nghỉ sớm")
        self.assertEqual([(t, g) for t, g, _ in got], [("à", "B"), ("à", "B")])
        self.assertTrue(all("xưng hô" in why for _, _, why in got))

    def test_tieu_tu_liet_ke_la_giu(self):
        got = self.groups("rồi thì tiền ư danh ư cũng qua hết")
        self.assertEqual([(t, g) for t, g, _ in got], [("ư", "G"), ("ư", "G")])
        self.assertTrue(all("liệt kê" in why for _, _, why in got))

    def test_duyet_all_va_A_khong_lay_nhom_giu_chi_ma_rieng(self):
        src = self.path("d.vtt", youtube("chị gửi gửi file. File này ờ quan trọng".split()))
        self.ok("fillers", src, "--out", self.path("f.tsv"))
        with open(self.path("f.tsv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual([(r["tu"], r["nhom"]) for r in rows], [("gửi", "A"), ("File", "G"), ("ờ", "A")])
        for spec, n in (("all", 2), ("A", 2), ("F002", 1), ("G", 1)):
            res = run("clean", src, "--fillers", self.path("f.tsv"), "--approve", spec,
                      "--out-srt", self.path("o-%s.srt" % spec), "--out-cuts", self.path("c-%s" % spec))
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("Đã bỏ %d từ" % n, res.stdout)

    def test_scan_va_fillers_in_so_nhom_giu(self):
        src = self.path("s.vtt", youtube("chị gửi gửi file. File này ờ quan trọng".split()))
        out = self.ok("scan", src)
        self.assertIn("Nhóm A (đề xuất cắt", out)
        self.assertIn("Giữ (không đề xuất cắt): 1", out)
        out = self.ok("fillers", src, "--out", self.path("f2.tsv"))
        self.assertIn("A 2 · B 0 · giữ 1", out)


class Glossary(Base):
    def test_table_notes_and_correct_alternatives_are_not_treated_as_errors(self):
        g = self.path("CLAUDE.md", "| Ghi âm sai | Chuẩn |\n|---|---|\n| lít, list (thực thể) | **Lead** |\n"
                                   "| funel, phễu | **funnel / phễu** |\n")
        src = self.path("in.srt", "1\n00:00:01,000 --> 00:00:04,000\nmở list mới cho phễu và funel\n\n")
        out = self.ok("scan", src, "--glossary", g)
        self.assertIn("- Lead ← list: 1", out)
        self.assertIn("- funnel ← funel: 1", out)
        self.assertNotIn("phễu:", out)


class Reflow(Base):
    def blocks(self, name):
        return [b.split("\n") for b in self.read(name).strip().split("\n\n")]

    def test_cau_dai_tach_vua_kho_doc_thoi_gian_lien_mach_khong_mat_chu(self):
        text = ("Có những ngày đôi khi chúng ta đã thay quần áo, chuẩn bị giày dép, nhưng bước chân ra khỏi nhà "
                "vẫn là một việc rất khó khăn.")
        src = self.path("vi.srt", "1\n00:00:01,000 --> 00:00:09,000\n%s\n\n" % text)
        self.ok("reflow", src, "--max-chars", "26", "--out", self.path("doc.srt"))
        blocks = self.blocks("doc.srt")
        self.assertGreaterEqual(len(blocks), 2)
        times = [b[1].split(" --> ") for b in blocks]
        self.assertEqual((times[0][0], times[-1][1]), ("00:00:01,000", "00:00:09,000"))
        self.assertTrue(all(times[k][1] == times[k + 1][0] for k in range(len(times) - 1)))
        lines = [l for b in blocks for l in b[2:]]
        self.assertTrue(all(len(l) <= 26 for l in lines) and all(len(b) <= 4 for b in blocks), blocks)
        self.assertEqual(" ".join(lines).split(), text.split())
        ends = [(a.split()[-1], b.split()[0]) for a, b in zip(lines, lines[1:])]
        self.assertNotIn(("đôi", "khi"), ends)       # cặp chữ đi liền không bị tách
        self.assertNotIn(("chúng", "ta"), ends)

    def test_cau_da_vua_kho_giu_nguyen_cho_xuong_dong_sua_tay(self):
        src = self.path("vi.srt", "1\n00:00:01,000 --> 00:00:04,000\nHôm nay mình\nnói về chạy bộ.\n\n")
        self.ok("reflow", src, "--max-chars", "26", "--out", self.path("doc.srt"))
        self.assertEqual(self.blocks("doc.srt")[0][2:], ["Hôm nay mình", "nói về chạy bộ."])

    def test_doc_qua_nhanh_chi_canh_bao_va_khong_ghi_de(self):
        src = self.path("vi.srt", "1\n00:00:01,000 --> 00:00:01,600\nmột câu đọc không kịp\n\n")
        out = self.ok("reflow", src, "--out", self.path("doc.srt"))
        self.assertIn("ký tự/giây", out)
        self.assertIn("hiện 0.60 giây", out)
        res = run("reflow", src, "--out", self.path("doc.srt"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("đã có", res.stderr)



if __name__ == "__main__":
    unittest.main()
