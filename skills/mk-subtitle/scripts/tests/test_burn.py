"""Tests for mk-subtitle/scripts/burn.py (in phụ đề vào video). Video giả tạo bằng ffmpeg; phần in cứng cần ffmpeg có
libass (bỏ qua nếu máy không có).
Run: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/mk-subtitle/scripts/tests"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HERE, "burn.py")
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def libass_ffmpeg():
    for c in [os.environ.get("MK_SUBTITLE_FFMPEG"), shutil.which("ffmpeg"), "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
              "/usr/local/opt/ffmpeg-full/bin/ffmpeg"]:
        if c and os.path.isfile(c):
            out = subprocess.run([c, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
            if any(ln.split()[1:2] == ["ass"] for ln in out.splitlines()):
                return c
    return None


LIBASS = libass_ffmpeg() if HAS_FFMPEG else None


def run(*args):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, encoding="utf-8")


def make_video(path, w, h, total=4):
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=%dx%d:r=25:d=%g" % (w, h, total),
                    "-f", "lavfi", "-i", "sine=f=440:d=%g" % total, "-shortest", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-c:a", "aac", path], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return float(out)


def ymax(path, t, crop):
    res = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf",
                          "crop=%s,signalstats,metadata=print:key=lavfi.signalstats.YMAX" % crop, "-f", "null", "-"],
                         capture_output=True, text=True)
    return float(re.findall(r"YMAX=([\d.]+)", res.stderr)[-1])


@unittest.skipUnless(HAS_FFMPEG, "cần ffmpeg/ffprobe")
class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="mk-subtitle-test-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def path(self, name, text=None):
        p = os.path.join(self.dir, name)
        if text is not None:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        return p

    def ok(self, *args):
        res = run(*args)
        self.assertEqual(res.returncode, 0, "STDOUT: %s\nSTDERR: %s" % (res.stdout, res.stderr))
        return res.stdout

    def frames(self, w, h, name="mau"):
        video = self.path("v-%dx%d.mp4" % (w, h))
        if not os.path.exists(video):
            make_video(video, w, h)
        self.ok("frames", video, "--out-dir", self.path(name), "--samples", "3")
        return video, self.path(name)

    def layout(self, folder, out, *extra):
        stdout = self.ok("layout", folder, "--out", os.path.join(folder, out), *extra)
        with open(os.path.join(folder, out), encoding="utf-8") as fh:
            return json.load(fh), stdout

    def faces(self, folder, y, hgt):
        rows = ["mau-%02d.png\t0.300\t%.3f\t0.400\t%.3f" % (k, y, hgt) for k in (1, 2, 3)]
        return self.path(os.path.join(folder, "mat.tsv"), "\n".join(rows) + "\n")


class TestFramesAndLayout(Base):
    def test_khung_mau_va_khong_ghi_vao_thu_muc_da_co_file(self):
        video, folder = self.frames(720, 1280)
        self.assertEqual(sorted(os.listdir(folder)), ["mau-01.png", "mau-02.png", "mau-03.png", "mau.tsv"])
        res = run("frames", video, "--out-dir", folder)
        self.assertEqual(res.returncode, 1)
        self.assertIn("không ghi đè", res.stderr)

    def test_doc_mac_dinh_tiktok_shorts_nam_tren_vung_nut_va_duoi_mat(self):
        _, folder = self.frames(720, 1280)
        lay, out = self.layout(folder, "l1.json", "--faces", self.faces(folder, 0.38, 0.26))
        self.assertEqual(lay["platforms"], ["tiktok", "shorts"])
        self.assertEqual(lay["align"], "duoi")
        self.assertEqual(lay["margin_v"], 320)                       # chừa 25% đáy của TikTok
        self.assertGreaterEqual(lay["margin_r"], round(720 * 0.17))  # cột nút bên phải
        top_of_text = 1280 - lay["margin_v"] - lay["block_h"]
        self.assertGreaterEqual(top_of_text, 0.64 * 1280)            # không đè lên mặt
        self.assertLessEqual(lay["max_chars"], 30)
        self.assertTrue(os.path.isfile(os.path.join(folder, "l1.png")))
        self.assertNotIn("Cảnh báo: phụ đề", out)

    def test_mat_thap_thi_dua_len_tren_dau(self):
        _, folder = self.frames(720, 1280)
        lay, _ = self.layout(folder, "l.json", "--faces", self.faces(folder, 0.50, 0.30))
        self.assertEqual(lay["align"], "tren")
        self.assertLessEqual(lay["margin_v"] + lay["block_h"], 0.50 * 1280)

    def test_reels_chua_35_phan_tram_day_khong_con_cho_duoi_mat(self):
        _, folder = self.frames(720, 1280)
        lay, _ = self.layout(folder, "l.json", "--platform", "reels", "--faces", self.faces(folder, 0.38, 0.26))
        self.assertEqual(lay["align"], "tren")
        self.assertGreaterEqual(lay["margin_v"], round(1280 * 0.14))

    def test_mat_chiem_ca_khung_thi_canh_bao_che_mat(self):
        _, folder = self.frames(720, 1280)
        _, out = self.layout(folder, "l.json", "--faces", self.faces(folder, 0.10, 0.85))
        self.assertIn("che phần dưới mặt", out)

    def test_ngang_youtube_42_ky_tu_cach_day_6_phan_tram(self):
        _, folder = self.frames(1280, 720)
        lay, _ = self.layout(folder, "l.json")
        self.assertEqual((lay["orientation"], lay["platforms"], lay["max_chars"]), ("ngang", ["youtube"], 42))
        self.assertEqual(lay["margin_v"], round(720 * 0.06))
        self.assertGreaterEqual(lay["margin_l"], round(1280 * 0.16))  # chữ rộng tối đa 68% khung

    def test_kieu_ngan_mot_dong_chu_to_hon(self):
        _, folder = self.frames(720, 1280)
        std, _ = self.layout(folder, "a.json")
        short, _ = self.layout(folder, "b.json", "--style", "ngan")
        self.assertEqual(short["max_lines"], 1)
        self.assertGreater(short["font_size"], std["font_size"])

    def test_file_mat_co_anh_la_va_ghi_de_bi_tu_choi(self):
        _, folder = self.frames(720, 1280)
        bad = self.path(os.path.join(folder, "x.tsv"), "khac.png\t0.1\t0.1\t0.2\t0.2\n")
        self.assertEqual(run("layout", folder, "--out", os.path.join(folder, "l.json"), "--faces", bad).returncode, 1)
        self.layout(folder, "l.json")
        res = run("layout", folder, "--out", os.path.join(folder, "l.json"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("không ghi đè", res.stderr)


class TestAss(Base):
    def setUp(self):
        super().setUp()
        _, self.folder = self.frames(720, 1280)
        self.lay, _ = self.layout(self.folder, "l.json")
        self.lay_path = os.path.join(self.folder, "l.json")

    def test_ass_theo_bo_cuc_va_chu_la_du_lieu(self):
        src = self.path("fit.srt", "1\n00:00:01,000 --> 00:00:02,500\nmở {quán} \\N mới\n\n")
        self.ok("ass", src, "--layout", self.lay_path, "--out", self.path("p.ass"))
        with open(self.path("p.ass"), encoding="utf-8") as fh:
            ass = fh.read()
        self.assertIn("PlayResX: 720\nPlayResY: 1280", ass)
        self.assertIn(",2,%d,%d,%d,1\n" % (self.lay["margin_l"], self.lay["margin_r"], self.lay["margin_v"]), ass)
        self.assertIn("Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,mở \\{quán\\} \\\u2060N mới\n", ass)

    def test_dong_hoi_dai_canh_bao_tran_vung_thi_bao_loi(self):
        soft = "x" * (self.lay["max_chars"] + 1)
        self.assertLessEqual(len(soft), self.lay["hard_chars"])
        src = self.path("a.srt", "1\n00:00:01,000 --> 00:00:03,000\n%s\n\n" % soft)
        out = self.ok("ass", src, "--layout", self.lay_path, "--out", self.path("a.ass"))
        self.assertIn("Cảnh báo: câu 1 dòng", out)
        src = self.path("b.srt", "1\n00:00:01,000 --> 00:00:03,000\n%s\n\n" % ("x" * (self.lay["hard_chars"] + 1)))
        res = run("ass", src, "--layout", self.lay_path, "--out", self.path("b.ass"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("LỖI: câu 1 dòng dài", res.stdout)
        self.assertFalse(os.path.exists(self.path("b.ass")))


class TestBurn(Base):
    def setUp(self):
        super().setUp()
        self.video, folder = self.frames(720, 1280)
        self.lay, _ = self.layout(folder, "l.json")
        self.layout_path = os.path.join(folder, "l.json")
        src = self.path("fit.srt", "1\n00:00:01,000 --> 00:00:03,000\nMở quán trà sữa\n\n")
        self.ok("ass", src, "--layout", self.layout_path, "--out", self.path("p.ass"))

    def test_thieu_libass_bao_cach_cai_khong_tao_file(self):
        if os.name == "nt":
            self.skipTest("ffmpeg giả là script Python, cần shebang")
        fake = self.path("ffmpeg", "#!%s\nprint(' .. drawbox V->V Draw a box.')\n" % sys.executable)
        os.chmod(fake, 0o755)
        res = run("burn", self.video, "--ass", self.path("p.ass"), "--out", self.path("o.mp4"), "--ffmpeg", fake)
        self.assertEqual(res.returncode, 1)
        self.assertIn("libass", res.stderr)
        self.assertIn("brew install ffmpeg-full", res.stderr)
        self.assertFalse(os.path.exists(self.path("o.mp4")))

    @unittest.skipUnless(LIBASS, "cần ffmpeg có libass")
    def test_in_cung_dung_thoi_luong_chu_hien_dung_vung_va_khong_ghi_de(self):
        out = self.path("o.mp4")
        self.ok("burn", self.video, "--ass", self.path("p.ass"), "--out", out, "--ffmpeg", LIBASS)
        self.assertAlmostEqual(duration(out), duration(self.video), delta=0.1)
        y = 1280 - self.lay["margin_v"] - self.lay["block_h"]
        region = "%d:%d:%d:%d" % (720 - self.lay["margin_l"] - self.lay["margin_r"], self.lay["block_h"],
                                  self.lay["margin_l"], y)
        self.assertGreater(ymax(out, 2.0, region), 200)   # chữ trắng trong vùng phụ đề lúc có câu
        self.assertLess(ymax(out, 3.5, region), 160)      # hết câu thì chỉ còn nền xám
        res = run("burn", self.video, "--ass", self.path("p.ass"), "--out", out, "--ffmpeg", LIBASS)
        self.assertEqual(res.returncode, 1)
        self.assertIn("không ghi đè", res.stderr)

    @unittest.skipUnless(LIBASS, "cần ffmpeg có libass")
    def test_anh_mau_va_dry_run_khong_tao_video(self):
        out = self.path("o.mp4")
        stdout = self.ok("burn", self.video, "--ass", self.path("p.ass"), "--preview", self.path("mau"),
                         "--ffmpeg", LIBASS)
        self.assertTrue(os.path.isfile(self.path("mau-1.png")))
        self.assertIn("Font dùng thật", stdout)
        self.assertFalse(os.path.exists(out))
        stdout = self.ok("burn", self.video, "--ass", self.path("p.ass"), "--out", out, "--dry-run", "--ffmpeg", LIBASS)
        self.assertIn("DRY-RUN", stdout)
        self.assertFalse(os.path.exists(out))
        res = run("burn", self.video, "--ass", self.path("p.ass"), "--ffmpeg", LIBASS)
        self.assertEqual(res.returncode, 1)                 # thiếu cả --out lẫn --preview

    @unittest.skipUnless(LIBASS, "cần ffmpeg có libass")
    def test_lenh_ass_trong_chu_phu_de_khong_them_dong(self):
        src = self.path("x.srt", "1\n00:00:01,000 --> 00:00:03,000\nMở\\Nquán {\\an8}\n\n")
        self.ok("ass", src, "--layout", self.layout_path, "--out", self.path("x.ass"))
        self.ok("burn", self.video, "--ass", self.path("x.ass"), "--preview", self.path("x"), "--ffmpeg", LIBASS)
        y = 1280 - self.lay["margin_v"] - self.lay["block_h"]
        width = 720 - self.lay["margin_l"] - self.lay["margin_r"]
        half = self.lay["block_h"] // 2
        upper = "%d:%d:%d:%d" % (width, half - 4, self.lay["margin_l"], y)
        lower = "%d:%d:%d:%d" % (width, half, self.lay["margin_l"], y + half)
        self.assertGreater(ymax(self.path("x-1.png"), 0, lower), 200)  # một dòng chữ ở đáy vùng
        self.assertLess(ymax(self.path("x-1.png"), 0, upper), 160)     # \N không thành dòng thứ hai, \an8 không đổi chỗ


if __name__ == "__main__":
    unittest.main()
