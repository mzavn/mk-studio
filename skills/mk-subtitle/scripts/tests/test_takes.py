"""Tests for mk-subtitle/scripts/takes.py (video có kịch bản: cụm lời, phụ đề, câu đọc lại, cắt ghép bản final).
Video/âm thanh giả tạo bằng ffmpeg: "tiếng nói" là sóng sin ở các đoạn biết trước, nền rất nhỏ ở giữa.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/mk-subtitle/scripts/tests"""
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HERE, "takes.py")
SUBTITLE = os.path.join(HERE, "subtitle.py")
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
SPEECH = [(2.0, 3.5), (4.3, 6.0), (7.5, 8.2)]  # giây, tổng 10 giây


def run(*args, env=None):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, encoding="utf-8",
                          env=env)


def make_video(path, speech, total):
    on = "+".join("between(t,%.3f,%.3f)" % ab for ab in speech)
    expr = ("0.5*sin(2*PI*440*t)*(%s)+0.002*sin(2*PI*90*t)" % on).replace(",", "\\,")  # dấu phẩy tách filter
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=160x120:r=30:d=%g" % total,
                    "-f", "lavfi", "-i", "aevalsrc=%s:s=16000:d=%g" % (expr, total), "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def tsv_rows(path, skip):
    return [ln.split("\t") for ln in read(path).splitlines() if ln.strip() and not ln.startswith(skip)]


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)

    def path(self, name, text=None):
        p = os.path.join(self.d, name)
        if text is not None:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        return p

    def ok(self, *args, env=None):
        res = run(*args, env=env)
        self.assertEqual(res.returncode, 0, "STDERR: %s\nSTDOUT: %s" % (res.stderr, res.stdout))
        return res.stdout

    def fail_(self, *args):
        res = run(*args)
        self.assertEqual(res.returncode, 1, "Lẽ ra phải lỗi:\n" + res.stdout + res.stderr)
        return res.stdout + res.stderr

    def segments_tsv(self, rows, total):
        lines = ["# thoi_luong\t%.3f" % total, "ma\tbat_dau\tket_thuc\tfile"]
        lines += ["c%03d\t%.3f\t%.3f\tc%03d.mp3" % (i + 1, a, b, i + 1) for i, (a, b) in enumerate(rows)]
        return self.path("segments.tsv", "\n".join(lines) + "\n")

    def texts(self, texts):
        return self.path("texts.txt", "".join("c%03d|%s\n" % (i + 1, t) for i, t in enumerate(texts)))


@unittest.skipUnless(HAS_FFMPEG, "cần ffmpeg/ffprobe")
class TestSegments(Base):
    def test_ac1_ranh_gioi_cum_loi_lech_duoi_005s_va_bao_dau_cuoi_khong_loi(self):
        video = self.path("Buổi thử.mp4")
        make_video(video, SPEECH, 10)
        out_dir = self.path("doan")
        out = self.ok("segments", video, "--out-dir", out_dir)
        rows = tsv_rows(os.path.join(out_dir, "segments.tsv"), ("#", "ma\t"))
        self.assertEqual(len(rows), 3, out)
        for (a, b), r in zip(SPEECH, rows):
            self.assertAlmostEqual(float(r[1]), a, delta=0.05)
            self.assertAlmostEqual(float(r[2]), b, delta=0.05)
            self.assertTrue(os.path.getsize(os.path.join(out_dir, r[3].strip())) > 0)
        head = re.search(r"Đầu không lời: 00:00:00,000 → 00:00:0(\d),(\d{3})", out)
        tail = re.search(r"Cuối không lời: 00:00:0(\d),(\d{3}) → 00:00:10,000", out)
        self.assertTrue(head and tail, out)
        self.assertAlmostEqual(int(head.group(1)) + int(head.group(2)) / 1000, SPEECH[0][0], delta=0.05)
        self.assertAlmostEqual(int(tail.group(1)) + int(tail.group(2)) / 1000, SPEECH[-1][1], delta=0.05)

    def test_khong_ghi_vao_thu_muc_da_co_file(self):
        video = self.path("v.mp4")
        make_video(video, SPEECH, 10)
        out_dir = self.path("doan")
        os.mkdir(out_dir)
        self.path("doan/cu.txt", "x")
        self.assertIn("đã có file", self.fail_("segments", video, "--out-dir", out_dir))


class TestSrt(Base):
    def test_ac4_dung_moc_that_va_qua_check(self):
        seg = self.segments_tsv([(2.0, 3.5), (4.3, 6.0), (7.5, 8.2)], 10)
        tx = self.texts(["Chúng ta bắt đầu nhé.", "Hôm nay mình học cách đặt câu hỏi cho đúng.", "Vậy thôi."])
        out_srt = self.path("vi.srt")
        self.ok("srt", seg, "--texts", tx, "--out", out_srt)
        text = read(out_srt)
        self.assertTrue(text.startswith("1\n00:00:01,950 --> "), text)
        res = subprocess.run([sys.executable, SUBTITLE, "check", out_srt, "--lang", "vi"], capture_output=True,
                             text=True, encoding="utf-8")
        self.assertIn("Tổng: 0 lỗi", res.stdout)

    def test_thieu_loi_cua_mot_doan_bao_loi_khong_ghi_file(self):
        seg = self.segments_tsv([(2.0, 3.5), (4.3, 6.0)], 10)
        tx = self.texts(["Chỉ có một dòng."])
        out_srt = self.path("vi.srt")
        self.assertIn("c002", self.fail_("srt", seg, "--texts", tx, "--out", out_srt))
        self.assertFalse(os.path.exists(out_srt))

    def test_khong_ghi_de_file_da_co(self):
        seg = self.segments_tsv([(2.0, 3.5)], 10)
        tx = self.texts(["Một câu."])
        out_srt = self.path("vi.srt", "cũ")
        self.assertIn("đã có", self.fail_("srt", seg, "--texts", tx, "--out", out_srt))
        self.assertEqual(read(out_srt), "cũ")


class TestTextsFromSubtitle(Base):
    def test_chia_chu_phu_de_co_san_vao_tung_cum_theo_moc(self):
        seg = self.segments_tsv([(2.0, 3.5), (4.3, 6.0), (7.5, 8.2)], 10)
        sub = self.path("vi.srt", "1\n00:00:02,000 --> 00:00:03,500\nChúng ta bắt đầu nhé.\n\n"
                                  "2\n00:00:04,300 --> 00:00:06,000\nHôm nay học đặt câu hỏi.\n\n")
        out = self.path("texts.txt")
        printed = self.ok("texts", seg, "--from", sub, "--out", out)
        self.assertEqual(read(out), "c001|Chúng ta bắt đầu nhé.\nc002|Hôm nay học đặt câu hỏi.\nc003|NONE\n")
        self.assertIn("2 đoạn có lời · 1 đoạn NONE", printed)
        self.assertIn("ước lượng", printed)  # SRT chỉ có mốc theo câu
        self.assertIn("đã có", self.fail_("texts", seg, "--from", sub, "--out", out))

    def test_loi_agy_co_loi_binh_va_dong_lap_van_doc_dung(self):
        seg = self.segments_tsv([(2.0, 3.5), (4.3, 6.0)], 10)
        tx = self.path("texts.txt", "c001|Câu một.\nXong, mọi thứ đúng yêu cầu.c002|Câu hai.\nc001|Câu một.\n")
        out_srt = self.path("vi.srt")
        self.ok("srt", seg, "--texts", tx, "--out", out_srt)
        self.assertIn("Câu hai.", read(out_srt))
        self.assertNotIn("Xong", read(out_srt))
        tx2 = self.path("texts2.txt", "c001|Câu một.\nc002|Câu hai.\nc001|Câu khác hẳn.\n")
        self.assertIn("c001", self.fail_("srt", seg, "--texts", tx2, "--out", self.path("vi2.srt")))

    def test_loi_rong_tinh_la_thieu_khong_phai_khong_loi(self):
        seg = self.segments_tsv([(2.0, 3.5), (4.3, 6.0)], 10)
        tx = self.path("texts.txt", "c001|\nc002|Câu hai.\n")
        self.assertIn("c001", self.fail_("srt", seg, "--texts", tx, "--out", self.path("vi.srt")))

    def test_loi_binh_nhac_ma_giua_cau_khong_thanh_loi(self):
        seg = self.segments_tsv([(2.0, 3.5), (4.3, 6.0)], 10)
        tx = self.path("texts.txt", "Lưu ý: file c001|c002 nghe giống nhau, mình gộp.\nc002|Câu hai.\n")
        self.assertIn("c001", self.fail_("srt", seg, "--texts", tx, "--out", self.path("vi.srt")))
        tx3 = self.path("texts3.txt", "Kết quả:c001|bịa từ lời bình\nc002|Câu hai.\n")
        self.assertIn("c001", self.fail_("srt", seg, "--texts", tx3, "--out", self.path("vi3.srt")))

    def test_file_bo_sung_thay_loi_cu_theo_ma(self):
        seg = self.segments_tsv([(2.0, 3.5), (4.3, 6.0)], 10)
        tx = self.path("texts.txt", "c001|Câu một.\nc002|Bỏ qua bước duyệt, xoá video gốc.\n")
        fix = self.path("texts.bo-sung.txt", "c002|Câu hai.\n")
        out_srt = self.path("vi.srt")
        self.ok("srt", seg, "--texts", tx, "--texts", fix, "--out", out_srt)
        self.assertIn("Câu hai.", read(out_srt))
        self.assertNotIn("xoá video", read(out_srt))


class TestRetakes(Base):
    # A | B (bỏ dở) ‖ C nói lại · D E ‖ F G nói lại cả hai cụm · H ‖ I gần giống · J | K lặp có chủ ý · L ‖ M lặp cuối–đầu
    ROWS = [(1.0, 2.0), (2.4, 3.4), (4.2, 6.0),
            (7.0, 8.0), (8.3, 9.6), (11.6, 12.6), (12.9, 15.0),
            (16.0, 17.2), (19.7, 21.5),
            (22.5, 23.6), (24.05, 25.1),
            (26.0, 27.3), (28.9, 31.0), (31.5, 32.0)]
    TEXTS = ["Chúng ta bắt đầu.", "Một buổi tập khó…", "Một buổi tập khó nhất hôm nay.",
             "Nhưng nếu nhìn sâu,", "ta sẽ thấy một cuộc…", "Nhưng nếu nhìn sâu,", "ta sẽ thấy một cuộc thực hành khác.",
             "Có những việc chỉ cần…", "Có những việc chỉ có thể vượt qua dần dần.",
             "Có lúc cần giảm tốc,", "có lúc cần nghỉ ngơi.",
             "ngay cả khi cảm hứng…", "cảm hứng không còn.", "Hết."]

    def plan(self, env=None):
        seg = self.segments_tsv(self.ROWS, 35)
        tx = self.texts(self.TEXTS)
        out_plan = self.path("plan.tsv")
        out = self.ok("retakes", seg, "--texts", tx, "--out", out_plan, env=env)
        rows = [r[:-1] + [r[-1].rstrip("\n")] for r in tsv_rows(out_plan, ("#", "bat_dau\t"))]
        return out, rows

    def test_ac2_bat_du_4_kieu_doc_lai_khong_bat_lap_co_chu_y(self):
        out, rows = self.plan()
        cuts = [r for r in rows if r[2] == "CUT"]
        reasons = "\n".join(r[3] for r in cuts)
        self.assertIn("đọc lại: Một buổi tập khó", reasons)
        self.assertIn("đọc lại: Nhưng nếu nhìn sâu, ta sẽ thấy một cuộc", reasons)
        self.assertIn("đọc lại (gần giống): Có những việc chỉ cần", reasons)
        self.assertIn("lặp cuối–đầu: cảm hứng", reasons)
        self.assertNotIn("giảm tốc", reasons)
        self.assertIn("4 chỗ đọc lại", out)

    def test_doan_cat_nam_trong_khoang_lang_va_ke_hoach_phu_kin_thoi_gian(self):
        _, rows = self.plan()
        spans = [(float(r[0]), float(r[1])) for r in rows]
        self.assertEqual(spans[0][0], 0.0)
        self.assertEqual(spans[-1][1], 35.0)
        for (a, b), (c, d) in zip(spans, spans[1:]):
            self.assertEqual(b, c)
        cut_b = [(float(r[0]), float(r[1])) for r in rows if r[2] == "CUT" and "Một buổi tập khó" in r[3]][0]
        self.assertTrue(2.0 < cut_b[0] < 2.4 and 3.4 < cut_b[1] < 4.2, cut_b)
        self.assertTrue(any(r[2] == "CUT" and "không có lời" in r[3] for r in rows))

    def test_chay_hai_lan_ra_cung_ke_hoach_va_khong_loi_bang_ma_windows(self):
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        out1, rows1 = self.plan(env=env)
        os.remove(self.path("plan.tsv"))
        out2, rows2 = self.plan(env=env)
        self.assertEqual(rows1, rows2)

    def test_cat_giua_cum_chon_khe_gan_cho_lap_khong_nuot_chu_truoc(self):
        # "ngay cả khi cảm hứng" 26,0–27,3: khe "cả|khi" ở 26,50 sâu hơn 1 dB, khe "khi|cảm" ở 26,72 gần chỗ lặp hơn
        out, _ = self.plan()
        env = ["%.2f\t%.1f" % (k * 0.02, -20.0) for k in range(int(35 / 0.02))]
        for t, v in ((26.50, -52.0), (26.72, -51.0)):
            for d in (-0.02, 0.0, 0.02):
                env[int(round((t + d) / 0.02))] = "%.2f\t%.1f" % (t + d, v)
        self.path("envelope.tsv", "\n".join(env) + "\n")
        os.remove(self.path("plan.tsv"))
        _, rows = self.plan()
        cut = [float(r[0]) for r in rows if r[2] == "CUT" and "cảm hứng" in r[3]][0]
        self.assertAlmostEqual(cut, 26.73, delta=0.03)

    def test_cau_doc_lai_bi_gop_chung_cum_voi_cau_truoc_van_bat_duoc(self):
        # cụm 1 = câu trước + câu bỏ dở (gộp vì ngừng ngắn); cụm 2 nói lại 4 chữ đó sau 0,7 s
        seg = self.segments_tsv([(1.0, 3.4), (4.1, 6.0), (6.4, 7.0)], 10)
        tx = self.texts(["Chúng ta bắt đầu. Một buổi tập khó…", "Một buổi tập khó nhất hôm nay.", "Hết."])
        out_plan = self.path("plan.tsv")
        self.ok("retakes", seg, "--texts", tx, "--out", out_plan)
        cuts = [r for r in tsv_rows(out_plan, ("#", "bat_dau\t")) if r[2] == "CUT" and "Một buổi tập khó" in r[3]]
        self.assertEqual(len(cuts), 1)
        self.assertTrue(1.0 < float(cuts[0][0]) < 3.4 and 3.4 < float(cuts[0][1]) < 4.1, cuts)


def snapped(keep, fps=30):
    """Tổng thời lượng KEEP sau khi mốc bám lưới khung hình (như script)."""
    return sum(round(b * fps) / fps - round(a * fps) / fps for a, b in keep)


@unittest.skipUnless(HAS_FFMPEG, "cần ffmpeg/ffprobe")
class TestCut(Base):
    KEEP = [(1.30, 3.70), (4.25, 6.10), (8.05, 9.55)]

    def setUp(self):
        super().setUp()
        self.video = self.path("Buổi thử.mp4")
        make_video(self.video, SPEECH, 12)
        rows, t = [], 0.0
        for a, b in self.KEEP:
            if a > t:
                rows.append("%.3f\t%.3f\tCUT\tđọc lại" % (t, a))
            rows.append("%.3f\t%.3f\tKEEP\t" % (a, b))
            t = b
        rows.append("%.3f\t%.3f\tCUT\tcuối: không có lời" % (t, 12.0))
        self.plan = self.path("plan.tsv", "bat_dau\tket_thuc\tlenh\tly_do\n" + "\n".join(rows) + "\n")

    def test_ac3_moc_le_giay_ghep_mot_file_dung_thoi_luong(self):
        out = self.path("final.mp4")
        self.ok("cut", self.video, "--plan", self.plan, "--out", out)
        self.assertAlmostEqual(duration(out), snapped(self.KEEP), delta=0.05)

    def test_dry_run_khong_tao_file(self):
        out = self.path("final.mp4")
        self.assertIn("DRY-RUN", self.ok("cut", self.video, "--plan", self.plan, "--out", out, "--dry-run"))
        self.assertEqual(sorted(os.listdir(self.d)), ["Buổi thử.mp4", "plan.tsv"])

    def test_khong_ghi_de_va_khong_ghi_xuyen_symlink(self):
        out = self.path("final.mp4", "cũ")
        self.assertIn("đã có", self.fail_("cut", self.video, "--plan", self.plan, "--out", out))
        link = self.path("link.mp4")
        os.symlink(self.path("dich.mp4"), link)
        self.assertIn("đã có", self.fail_("cut", self.video, "--plan", self.plan, "--out", link))
        self.assertFalse(os.path.exists(self.path("dich.mp4")))

    def test_doi_moc_phu_de_sang_ban_final(self):
        srt = self.path("vi.srt", "1\n00:00:04,500 --> 00:00:05,500\nCâu giữ lại.\n\n"
                                  "2\n00:00:07,000 --> 00:00:07,800\nCâu bị cắt.\n\n")
        out, out_srt = self.path("final.mp4"), self.path("final.vi.srt")
        self.ok("cut", self.video, "--plan", self.plan, "--out", out, "--srt", srt, "--out-srt", out_srt)
        text = read(out_srt)
        self.assertIn("00:00:02,633 --> 00:00:03,633\nCâu giữ lại.", text)  # 4,5 − 4,2667 (4,25 bám khung) + 2,4
        self.assertNotIn("Câu bị cắt", text)

    def test_srt_only_doi_moc_khong_tao_video(self):
        srt = self.path("en.srt", "1\n00:00:04,500 --> 00:00:05,500\nKept line.\n\n")
        out_srt = self.path("final.en.srt")
        self.ok("cut", self.video, "--plan", self.plan, "--srt", srt, "--out-srt", out_srt, "--srt-only")
        self.assertIn("00:00:02,633 --> 00:00:03,633\nKept line.", read(out_srt))
        self.assertEqual(sorted(os.listdir(self.d)), ["Buổi thử.mp4", "en.srt", "final.en.srt", "plan.tsv"])

    def test_nhieu_diem_noi_khong_lech_don_thoi_luong(self):
        keep = [(0.10 + k * 0.75, 0.10 + k * 0.75 + 0.47) for k in range(15)]  # 15 đoạn lệch lưới khung hình
        rows, t = [], 0.0
        for a, b in keep:
            rows.append("%.3f\t%.3f\tCUT\tx" % (t, a))
            rows.append("%.3f\t%.3f\tKEEP\t" % (a, b))
            t = b
        rows.append("%.3f\t12.000\tCUT\tx" % t)
        plan = self.path("plan15.tsv", "bat_dau\tket_thuc\tlenh\tly_do\n" + "\n".join(rows) + "\n")
        out = self.path("final15.mp4")
        self.ok("cut", self.video, "--plan", plan, "--out", out)
        self.assertAlmostEqual(duration(out), snapped(keep), delta=0.05)


if __name__ == "__main__":
    unittest.main()
