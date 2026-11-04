"""Test hành vi của scripts/thumbnail.py — chạy như agent chạy, kiểm dòng in ra, thoát mã, file.
Ảnh giả (nền, chân dung có/không nền trong suốt, logo) dựng bằng ffmpeg; video chỉ cần có tên (không giải mã).
Phần in chữ cần ffmpeg có libass (bỏ qua nếu máy không có).
Chạy: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/mk-thumbnail/scripts/tests
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

sys.dont_write_bytecode = True

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "thumbnail.py")
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
FFMPEG_FULL = ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "/usr/local/opt/ffmpeg-full/bin/ffmpeg")
HEADER = "video\tbadge\ttitle\tnen\tnen_doc\tchan_dung\tlogo"
# vừa 3 dòng bản ngang ở cỡ nhỏ, không vừa bản dọc (khung chữ hẹp hơn)
DOC_TOO_LONG = ("Chị Lan Bán Bánh Mì Đầu Ngõ: Bí Quyết Giữ Khách Quen, Tính Lãi Từng Ổ, Chuyển Khoản Không Nhầm, "
                "Giữ Giá Ổn Định Mùa Mưa & Hỏi Đáp Cuối Buổi Với Cả Xóm Chợ")


def libass_ffmpeg():
    for c in [os.environ.get("MK_THUMBNAIL_FFMPEG"), shutil.which("ffmpeg")] + list(FFMPEG_FULL):
        if c and os.path.isfile(c):
            out = subprocess.run([c, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
            if any(ln.split()[1:2] == ["ass"] for ln in out.splitlines()):
                return c
    return None


LIBASS = libass_ffmpeg() if HAS_FFMPEG else None


def run(*args, cwd=None, path=None, env_extra=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("MK_THUMBNAIL_FFMPEG", None)
    if path is not None:
        env["PATH"] = path
    env.update(env_extra or {})
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, encoding="utf-8",
                          env=env, cwd=cwd)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def readb(path):
    with open(path, "rb") as fh:
        return fh.read()


def row(video, badge="B", title="Quán Quen", nen="", nen_doc="", chan_dung="", logo=""):
    return "\t".join([video, badge, title, nen, nen_doc, chan_dung, logo])


def ffmpeg(*args):
    os.makedirs(os.path.dirname(args[-1]), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + list(args), check=True)


def make_color(path, color, size):
    ffmpeg("-f", "lavfi", "-i", "color=c=%s:s=%s:d=1" % (color, size), "-frames:v", "1", path)


def make_cutout(path):
    """300×400 RGBA: khối đỏ đục x 75–224, y 100–399 (chạm đáy), phần còn lại trong suốt."""
    ffmpeg("-f", "lavfi", "-i", "color=c=red:s=300x400:d=1", "-vf",
           "format=rgba,geq=r=255:g=0:b=0:a='255*between(X,75,224)*between(Y,100,399)'", "-frames:v", "1", path)


def image(path):
    """Ảnh thật khi có ffmpeg (check xem trước sẽ mở ảnh), không thì file rỗng (chỉ kiểm cột TSV)."""
    if HAS_FFMPEG:
        make_color(path, "gray", "64x36")
    else:
        write(path, "")


def dims(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,codec_name", "-of",
                          "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    codec, w, h = out.split(",")
    return codec, int(w), int(h)


def stat(path, key, x, y, w, h):
    res = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-frames:v", "1", "-vf",
                          "crop=%d:%d:%d:%d,signalstats,metadata=print:key=lavfi.signalstats.%s" % (w, h, x, y, key),
                          "-f", "null", "-"], capture_output=True, text=True)
    return float(re.findall(r"%s=([\d.]+)" % key, res.stderr)[-1])


def rows(tsv):
    return [ln.split("\t") for ln in read(tsv).splitlines() if ln and not ln.startswith("#") and ln != HEADER]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mk-thumbnail-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def ok(self, *args, **kw):
        res = run(*args, **kw)
        self.assertEqual(res.returncode, 0, "STDOUT: %s\nSTDERR: %s" % (res.stdout, res.stderr))
        return res.stdout

    def fail_with(self, text, *args, **kw):
        res = run(*args, **kw)
        self.assertEqual(res.returncode, 1, "STDOUT: %s\nSTDERR: %s" % (res.stdout, res.stderr))
        self.assertIn(text, res.stdout + res.stderr)
        return res


class TenFile(Base):
    """Tên file → nhãn góc (badge) và tiêu đề; chỉ đọc tên, không mở video."""

    def names(self, *files):
        os.makedirs(self.p("v"), exist_ok=True)
        for f in files:
            write(self.p("v", f), "")
        self.out = self.ok("names", self.p("v"))
        return [ln.split("\t") for ln in self.out.splitlines() if "\t" in ln]

    def test_tach_buoi_phan_va_tieu_de(self):
        got = self.names("Buổi 2_P03 - Chợ Sáng & Quán Quen.mp4")
        self.assertEqual(got[0][1:3], ["Buổi 2 · P03", "Chợ Sáng & Quán Quen"])

    def test_phan_co_so_le_va_dau_hai_cham_ngoac_gach(self):
        got = self.names("Buổi 0_P05.6 - Lời Chúc Của Chị Lan.mp4",
                         "Buổi 1_P06 - Bánh Mì: Nướng vs Hấp (Phần 2) – Giá - Lãi.mp4")
        self.assertEqual(got[0][1:3], ["Buổi 0 · P05.6", "Lời Chúc Của Chị Lan"])
        self.assertEqual(got[1][1:3], ["Buổi 1 · P06", "Bánh Mì: Nướng vs Hấp (Phần 2) – Giá - Lãi"])

    def test_ten_khong_theo_mau_lay_ca_ten_lam_tieu_de_va_danh_dau(self):
        got = self.names("so di cho tuan 3.mov")
        self.assertEqual(got[0][1:3], ["", "so di cho tuan 3"])
        self.assertIn("Cảnh báo: so di cho tuan 3.mov: tên không theo mẫu", self.out)

    def test_dau_sao_va_gach_dung_trong_ten_duoc_doi_khong_thanh_ky_hieu(self):
        got = self.names("Buổi 9_P01 - Giá *Sốc | Hôm Nay.mp4")
        self.assertEqual(got[0][2], "Giá ·Sốc / Hôm Nay")
        self.assertIn("Cảnh báo:", self.out)

    def test_ten_co_ky_tu_dieu_khien_bi_tu_choi_khong_in_tho(self):
        os.makedirs(self.p("v"))
        write(self.p("v", "Buổi 1_P01 - Quán\x1b[2KOK.mp4"), "")
        res = self.fail_with("ký tự điều khiển", "names", self.p("v"))
        self.assertNotIn("\x1b", res.stdout + res.stderr)

    def test_ten_nfd_thanh_nfc_thu_tu_tu_nhien_bo_file_khac(self):
        got = self.names(unicodedata.normalize("NFD", "Buổi 10_P01 - Quán Trà.mp4"), "Buổi 2_P01 - Quán Phở.mp4",
                         "ghi-chu.txt", ".an.mp4")
        self.assertEqual([g[1] for g in got], ["Buổi 2 · P01", "Buổi 10 · P01"])
        self.assertTrue(unicodedata.is_normalized("NFC", got[1][1] + got[1][2]))

    def test_thu_muc_khong_co_video_hoac_duong_dan_sai_bao_loi(self):
        write(self.p("rong", "a.txt"), "")
        self.fail_with("Lỗi:", "names", self.p("rong"))
        self.fail_with("Lỗi:", "names", self.p("khong-co"))


class KeHoach(Base):
    """plan: chỉ đọc tên video + thư mục ảnh của người dùng → thumbnail.tsv; không giải mã video."""

    def setUp(self):
        super().setUp()
        for f in ("Buổi 1_P01 - Quán Phở.mp4", "Buổi 1_P02 - Quán Trà.mp4", "Buổi 1_P03 - Giá *Sốc.mp4"):
            write(self.p("v", f), "")
        self.assets = self.p("anh")
        for f in ("nen/b.jpg", "nen/a.png", "nen/ghi-chu.txt", "nen-doc/d.png", "chan-dung.png", "logo.png"):
            write(os.path.join(self.assets, f), "")

    def test_xoay_vong_nen_chan_dung_logo_va_tsv_qua_check(self):
        stdout = self.ok("plan", self.p("v"), "--assets", self.assets, "--out-dir", self.p("o"))
        got = rows(self.p("o", "thumbnail.tsv"))
        self.assertEqual([os.path.basename(r[3]) for r in got], ["a.png", "b.jpg", "a.png"])
        self.assertEqual([os.path.basename(r[4]) for r in got], ["d.png"] * 3)
        self.assertEqual({r[5] for r in got}, {os.path.join(self.assets, "chan-dung.png")})
        self.assertEqual({r[6] for r in got}, {os.path.join(self.assets, "logo.png")})
        self.assertEqual(got[2][2], "Giá ·Sốc")
        self.assertIn("OK: Buổi 1_P01 - Quán Phở.mp4", stdout)
        # ảnh giả rỗng: chỉ kiểm cột TSV, không xem trước bằng libass (--ffmpeg trỏ chỗ không có)
        self.assertIn("OK", self.ok("check", self.p("o", "thumbnail.tsv"), "--ffmpeg", self.p("khong-co")))

    def test_thu_muc_anh_chua_co_thi_nen_ve_san_kem_canh_bao(self):
        stdout = self.ok("plan", self.p("v"), "--assets", self.p("chua-co"), "--out-dir", self.p("o"))
        self.assertIn("Cảnh báo:", stdout)
        self.assertIn("nền vẽ sẵn", stdout)
        self.assertEqual({tuple(r[3:]) for r in rows(self.p("o", "thumbnail.tsv"))}, {("", "", "", "")})

    def test_nhieu_anh_chan_dung_bao_anh_da_chon_va_dong_ok_co_logo(self):
        write(os.path.join(self.assets, "chan-dung.jpg"), "")
        stdout = self.ok("plan", self.p("v"), "--assets", self.assets, "--out-dir", self.p("o"))
        self.assertRegex(stdout, r"Cảnh báo: có \d+ ảnh chan-dung\.\* — dùng chan-dung\.png")
        self.assertIn("· logo logo.png", stdout)

    def test_mau_nhan_goc_theo_co_badge(self):
        self.ok("plan", self.p("v"), "--out-dir", self.p("o"), "--badge", "Buổi {n} · Phần {p}")
        self.assertEqual(rows(self.p("o", "thumbnail.tsv"))[0][1], "Buổi 1 · Phần 01")
        res = run("plan", self.p("v"), "--out-dir", self.p("o2"), "--badge", "Buổi {x}")
        self.assertEqual(res.returncode, 2)
        self.assertFalse(os.path.exists(self.p("o2")))

    def test_cap_nhat_giu_sua_tay_dien_cot_anh_moi_khong_ghi_de(self):
        self.ok("plan", self.p("v"), "--out-dir", self.p("o"))
        tsv = self.p("o", "thumbnail.tsv")
        old = read(tsv).replace("\tQuán Phở\t", "\tQuán *Phở* Đầu Ngõ\t").replace("Buổi 1 · P02", "Buổi 1 · Phần 02")
        write(tsv, old)
        stdout = self.ok("plan", self.p("v"), "--assets", self.assets, "--out-dir", self.p("o"), "--update")
        self.assertEqual(read(tsv), old)                                # TSV cũ nguyên vẹn
        new = self.p("o", "thumbnail-2.tsv")
        self.assertIn(new, stdout)
        got = rows(new)
        self.assertEqual(got[0][2], "Quán *Phở* Đầu Ngõ")
        self.assertEqual(got[1][1], "Buổi 1 · Phần 02")
        self.assertEqual([os.path.basename(r[3]) for r in got], ["a.png", "b.jpg", "a.png"])
        self.ok("plan", self.p("v"), "--assets", self.assets, "--out-dir", self.p("o"), "--update")
        self.assertTrue(os.path.exists(self.p("o", "thumbnail-3.tsv")))

    def test_khong_co_anh_thi_de_trong_va_khong_ghi_de(self):
        self.ok("plan", self.p("v"), "--out-dir", self.p("o"))
        got = rows(self.p("o", "thumbnail.tsv"))
        self.assertEqual({tuple(r[3:]) for r in got}, {("", "", "", "")})
        before = read(self.p("o", "thumbnail.tsv"))
        self.fail_with("không ghi đè", "plan", self.p("v"), "--out-dir", self.p("o"))
        self.assertEqual(read(self.p("o", "thumbnail.tsv")), before)
        self.ok("plan", self.p("v"), "--out-dir", self.p("o2"))
        self.assertEqual(read(self.p("o2", "thumbnail.tsv")), before)


class Prompt(Base):
    """prompt: ghi file prompt ảnh nền cho cả chuỗi, không gọi dịch vụ nào, không ghi đè."""

    def setUp(self):
        super().setUp()
        write(self.p("v", "Buổi 1_P01 - Quán Phở Đầu Ngõ.mp4"), "")
        write(self.p("v", "Buổi 1_P02 - Trà Sữa Chị Lan.mp4"), "")

    def test_prompt_16_9_khong_chu_cho_trong_va_danh_sach_tranh(self):
        out = self.p("anh", "prompt-nen.md")
        self.ok("prompt", self.p("v"), "--assets", self.p("anh"), "--theme", "quán ăn sáng phố cổ")
        text = read(out)
        for must in ("16:9", "no text", "quán ăn sáng phố cổ", "Negative", "Quán Phở Đầu Ngõ", "nen/",
                     "abstract linework"):
            self.assertIn(must, text)
        for never in ("9:16", "%%", "read as writing", "room for a person"):
            self.assertNotIn(never, text)
        self.assertTrue(os.path.isdir(self.p("anh", "nen")))
        self.fail_with("không ghi đè", "prompt", self.p("v"), "--assets", self.p("anh"))
        self.assertEqual(read(out), text)

    def test_prompt_doc_ghi_file_rieng_khi_file_ngang_da_co(self):
        self.ok("prompt", self.p("v"), "--assets", self.p("anh"))
        before = read(self.p("anh", "prompt-nen.md"))
        self.ok("prompt", self.p("v"), "--assets", self.p("anh"), "--doc")
        self.assertEqual(read(self.p("anh", "prompt-nen.md")), before)
        doc = read(self.p("anh", "prompt-nen-doc.md"))
        self.assertIn("9:16", doc)
        self.assertIn("nen-doc/", doc)
        self.fail_with("không ghi đè", "prompt", self.p("v"), "--assets", self.p("anh"), "--doc")

    def test_prompt_lay_tieu_de_da_sua_tu_tsv_va_chua_cho_chan_dung_khi_co(self):
        write(self.p("anh", "chan-dung.png"), "")
        self.ok("plan", self.p("v"), "--assets", self.p("anh"), "--out-dir", self.p("o"))
        tsv = self.p("o", "thumbnail.tsv")
        write(tsv, read(tsv).replace("\tQuán Phở Đầu Ngõ\t", "\tPhở Bò *Gia Truyền*\t"))
        self.ok("prompt", "--tsv", tsv, "--assets", self.p("anh"))
        text = read(self.p("anh", "prompt-nen.md"))
        self.assertIn("- Phở Bò Gia Truyền", text)
        self.assertNotIn("Quán Phở Đầu Ngõ", text)
        self.assertIn("room for a person", text)


class KiemTsv(Base):
    """File TSV người dùng sửa tay: kiểm từng dòng trước khi in."""

    def setUp(self):
        super().setUp()
        self.video = self.p("v", "Buổi 1_P01 - Quán Quen.mp4")
        write(self.video, "")
        self.tsv = self.p("out", "thumbnail.tsv")

    def tsv_with(self, *body):
        write(self.tsv, "# ghi chú\n# assets: %s\n" % self.tmp + HEADER + "\n" + "".join(b + "\n" for b in body))

    def test_anh_unc_hay_ngoai_thu_muc_tsv_va_thu_muc_anh_bi_tu_choi(self):
        outside = tempfile.mkdtemp(prefix="mk-thumbnail-ngoai-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        image(os.path.join(outside, "n.png"))
        write(self.tsv, HEADER + "\n" + "\n".join([row(self.video, nen="\\\\may-la\\chia-se\\n.png"),
                                                    row(self.video, logo="//may-la/chia-se/l.png"),
                                                    row(self.video, nen=os.path.join(outside, "n.png"))]) + "\n")
        res = self.fail_with("LỖI", "check", self.tsv)
        self.assertIn("thumbnail.tsv:2: cột nen là đường dẫn mạng", res.stdout)
        self.assertIn("thumbnail.tsv:3: cột logo là đường dẫn mạng", res.stdout)
        self.assertIn("thumbnail.tsv:4: ảnh nền phải nằm trong thư mục chứa TSV hoặc thư mục ảnh", res.stdout)

    def test_ffmpeg_qua_bien_moi_truong_hay_tuong_doi_trong_thu_muc_lam_viec_bi_tu_choi(self):
        if os.name == "nt":
            self.skipTest("ffmpeg giả là script Python, cần shebang")
        self.tsv_with(row(self.video))
        work = self.p("lam")
        fake = os.path.join(work, "tools", "ffmpeg")
        mark = self.p("da-chay")
        write(fake, "#!%s\nopen(%r, 'w').write('x')\nprint(' .. ass V->V x')\n" % (sys.executable, mark))
        os.chmod(fake, 0o755)
        res = self.fail_with("thư mục đang làm việc", "render", self.tsv, cwd=work,
                             env_extra={"MK_THUMBNAIL_FFMPEG": fake})
        self.assertIn("MK_THUMBNAIL_FFMPEG", res.stderr)
        res = run("render", self.tsv, "--ffmpeg", "tools/ffmpeg", cwd=work)
        self.assertEqual(res.returncode, 2)
        self.assertIn("tuyệt đối", res.stderr)
        self.fail_with("thư mục đang làm việc", "check", self.tsv, "--ffmpeg", fake, cwd=work)
        self.assertFalse(os.path.exists(mark))                         # ffmpeg lạ không bao giờ được chạy

    def test_hop_le(self):
        image(self.p("nen", "a.png"))
        self.tsv_with(row(self.video, title="Quán *Quen*|Phở Bò", nen=self.p("nen", "a.png")))
        self.assertIn("OK", self.ok("check", self.tsv))

    def test_loi_tung_dong_co_so_dong_va_khong_ghi_file(self):
        write(self.p("ghi-chu.txt"), "")
        self.tsv_with(row(self.video, title="Quán *Quen"),
                      row(self.video, title="A|B|C|D"),
                      row(self.video, title=" "),
                      row(self.p("v", "khong-co.mp4")),
                      row(self.video, nen="https://anh.example/nen.png"),
                      row(self.video, chan_dung=self.p("ghi-chu.txt")),
                      row(self.video, logo=self.p("khong-co.png")))
        before = sorted(os.listdir(self.p("out")))
        res = self.fail_with("LỖI", "check", self.tsv)
        for n in range(4, 11):
            self.assertIn("thumbnail.tsv:%d:" % n, res.stdout)
        self.assertIn("thumbnail.tsv:8: cột nen phải là đường dẫn file trong máy", res.stdout)
        self.assertIn("thumbnail.tsv:9: cột chan_dung phải là file ảnh", res.stdout)
        self.assertIn("thumbnail.tsv:10: không thấy ảnh logo", res.stdout)
        self.assertEqual(sorted(os.listdir(self.p("out"))), before)

    def test_cot_video_la_url_hay_khong_phai_video_bi_tu_choi(self):
        os.makedirs(self.p("http:", "h.example"))
        write(self.p("http:", "h.example", "x.mp4"), "")
        write(self.p("ghi-chu.txt"), "")
        self.tsv_with(row("http://h.example/x.mp4"), row(self.p("ghi-chu.txt")))
        res = self.fail_with("LỖI", "check", self.tsv, cwd=self.tmp)
        self.assertIn("thumbnail.tsv:4: cột video phải là đường dẫn file trong máy", res.stdout)
        self.assertIn("thumbnail.tsv:5: cột video phải là file video", res.stdout)

    def test_duong_dan_tuong_doi_tinh_tu_thu_muc_tsv(self):
        write(self.p("out", "v", "a.mp4"), "")
        image(self.p("out", "anh", "n.jpg"))
        self.tsv_with(row("v/a.mp4", nen="anh/n.jpg"))
        self.assertIn("OK", self.ok("check", self.tsv, cwd=self.p("v")))

    def test_title_qua_200_ky_tu_va_ky_tu_dieu_khien_bao_loi(self):
        self.tsv_with(row(self.video, title="Phở " * 51), row(self.video, title="Quán\x1bQuen"))
        res = self.fail_with("LỖI", "check", self.tsv)
        self.assertIn("thumbnail.tsv:4: title quá dài (203 ký tự, tối đa 200)", res.stdout)
        self.assertIn("thumbnail.tsv:5: có ký tự điều khiển", res.stdout)
        self.assertNotIn("\x1b", res.stdout)

    @unittest.skipUnless(LIBASS, "cần ffmpeg có libass")
    def test_check_in_cach_ngat_dong_tung_bo_cuc(self):
        write(self.p("v", "b.mp4"), "")
        self.tsv_with(row(self.video, title="Thử Nghiệm: Âm & Dương (Phần 1)"),
                      row(self.p("v", "b.mp4"), title="Chị Lan - Bán Bánh Mì vs Bán Cà Phê Sữa Đá Đầu Ngõ"))
        out = self.ok("check", self.tsv, "--doc", "--ffmpeg", LIBASS)
        ngang = re.search(r"thumbnail.tsv:4: ngang · cỡ \d+ · (.*)", out).group(1)
        self.assertEqual(ngang.split(" / ")[0], "Thử Nghiệm:", out)       # ngắt sau dấu :, không tách "Âm & Dương"
        self.assertEqual(len(re.findall(r"thumbnail.tsv:\d: (ngang|doc) · cỡ \d+ · ", out)), 4, out)
        self.assertNotRegex(out, r"/ [-–] ")                              # không dòng nào mở đầu bằng "- "
        self.assertNotRegex(out, r"(&|vs) /")                             # không dòng nào kết thúc bằng & / vs
        self.assertNotIn("Âm / & Dương", out)                            # cả bản dọc cũng không tách "Âm & Dương"

    def test_ffmpeg_nam_trong_thu_muc_dang_lam_bi_tu_choi(self):
        if os.name == "nt":
            self.skipTest("ffmpeg giả là script Python, cần shebang")
        self.tsv_with(row(self.video))
        work = self.p("lam")
        for name in ("ffmpeg", "ffprobe"):
            write(os.path.join(work, name), "#!%s\nprint(' .. ass V->V x')\n" % sys.executable)
            os.chmod(os.path.join(work, name), 0o755)
        path = ".:" + os.environ.get("PATH", "")
        for args in (("render", self.tsv), ("check", self.tsv)):
            res = self.fail_with("--ffmpeg", *args, cwd=work, path=path)
            self.assertIn("thư mục đang làm việc", res.stderr)
        self.assertEqual(os.listdir(self.p("out")), ["thumbnail.tsv"])

    def test_sai_tieu_de_cot(self):
        write(self.tsv, "video\ttitle\n%s\tQuán\n" % self.video)
        self.fail_with("LỖI", "check", self.tsv)

    def test_thieu_libass_bao_cach_cai_khong_tao_file(self):
        if os.name == "nt":
            self.skipTest("ffmpeg giả là script Python, cần shebang")
        self.tsv_with(row(self.video))
        fake = self.p("ffmpeg")
        write(fake, "#!%s\nprint(' .. drawbox V->V Draw a box.')\n" % sys.executable)
        os.chmod(fake, 0o755)
        res = self.fail_with("libass", "render", self.tsv, "--ffmpeg", fake)
        self.assertIn("brew install ffmpeg-full", res.stderr)
        self.assertEqual(os.listdir(self.p("out")), ["thumbnail.tsv"])


@unittest.skipUnless(LIBASS, "cần ffmpeg có libass")
class InAnh(Base):
    """Ghép ảnh 1280×720 JPG < 2 MB: nền, chân dung (tách nền / khung tròn), logo, nhãn, tiêu đề phía đối diện."""

    @classmethod
    def setUpClass(cls):
        cls.src = tempfile.mkdtemp(prefix="mk-thumbnail-src-")
        cls.video = os.path.join(cls.src, "Buổi 1_P01 - Quán Quen.mp4")
        write(cls.video, "")
        cls.nen = os.path.join(cls.src, "nen", "xam.png")
        make_color(cls.nen, "0x505050", "1920x1080")
        cls.cutout = os.path.join(cls.src, "chan-dung-tach.png")
        make_cutout(cls.cutout)
        cls.opaque = os.path.join(cls.src, "chan-dung.jpg")
        make_color(cls.opaque, "red", "400x400")
        cls.logo = os.path.join(cls.src, "logo.png")
        make_color(cls.logo, "blue", "200x80")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.src, ignore_errors=True)

    def tsv(self, title="Quán Quen", out="out", badge="Buổi 1 · P01", **cols):
        path = self.p(out, "thumbnail.tsv")
        write(path, "# assets: %s\n" % self.src + HEADER + "\n" + row(self.video, badge, title, **cols) + "\n")
        return path

    def render(self, tsv, *extra):
        return self.ok("render", tsv, "--ffmpeg", LIBASS, *extra)

    def out(self, d="out"):
        return self.p(d, "Buổi 1_P01 - Quán Quen.jpg")

    def area(self, stdout):
        m = re.search(r"(\d) dòng · vùng chữ x=(\d+)–(\d+) y=(\d+)–(\d+)", stdout)
        return [int(g) for g in m.groups()]

    def test_anh_1280x720_jpg_duoi_2mb_nen_ve_san_khi_khong_co_anh(self):
        stdout = self.render(self.tsv())
        self.assertEqual(dims(self.out()), ("mjpeg", 1280, 720))
        self.assertLess(os.path.getsize(self.out()), 2 * 1024 * 1024)
        self.assertIn("nền vẽ sẵn", stdout)
        self.assertIn("Font dùng thật", stdout)
        self.assertGreater(stat(self.out(), "YMAX", 760, 100, 480, 520) - stat(self.out(), "YMIN", 760, 100, 480, 520),
                           40)                                          # nền có hoa văn, không phẳng
        self.assertGreater(stat(self.out(), "YMAX", 30, 20, 150, 60), 180)  # nhãn góc trên-trái

    def test_chan_dung_tach_nen_giu_trong_suot_chu_ben_trai(self):
        stdout = self.render(self.tsv(nen=self.nen, chan_dung=self.cutout))
        x, y, w, h = [int(g) for g in re.search(r"chân dung tách nền x=(\d+),y=(\d+),w=(\d+),h=(\d+)", stdout).groups()]
        self.assertEqual(y + h, 720)                                    # đứng chạm đáy
        self.assertLessEqual(x + w, 1256)
        k = w / 300.0
        self.assertGreater(stat(self.out(), "VAVG", int(x + 120 * k), int(y + 220 * k), 40, 40), 180)  # khối đỏ
        self.assertLess(abs(stat(self.out(), "VAVG", x + 2, y + 2, int(30 * k), int(60 * k)) - 128), 12)  # trong suốt
        lines, x0, x1, y0, y1 = self.area(stdout)
        self.assertLessEqual(x1, 768)                                   # chữ ở phía đối diện chân dung
        self.assertGreater(stat(self.out(), "YMAX", x0, y0, x1 - x0, y1 - y0), 200)
        self.assertLess(stat(self.out(), "YMAX", 800, y0, 440, y1 - y0), 150)  # không chữ trắng bên phải

    def test_chan_dung_khong_trong_suot_thanh_khung_tron_vien_vang(self):
        stdout = self.render(self.tsv(nen=self.nen, chan_dung=self.opaque))
        x, y, w, h = [int(g) for g in re.search(r"chân dung khung tròn x=(\d+),y=(\d+),w=(\d+),h=(\d+)", stdout).groups()]
        self.assertEqual(w, h)
        self.assertLess(y + h, 660)                                     # chừa góc dưới-phải cho ô thời lượng
        self.assertGreater(stat(self.out(), "VAVG", x + w // 2 - 20, y + h // 2 - 20, 40, 40), 180)  # mặt đỏ ở giữa
        self.assertLess(abs(stat(self.out(), "VAVG", x, y, 24, 24) - 128), 12)           # góc ngoài vòng tròn: nền
        self.assertLess(stat(self.out(), "UAVG", x + w // 2 - 3, y + 1, 6, 4), 90)        # viền vàng ở mép trên

    def test_lop_toi_sau_vung_chu_dam_hon_quanh_chu(self):
        stdout = self.render(self.tsv(nen=self.nen))
        lines, x0, x1, y0, y1 = self.area(stdout)
        near = stat(self.out(), "YAVG", x1 - 140, y1 + 8, 120, 6)      # ngay dưới cuối dòng chữ
        far = stat(self.out(), "YAVG", x1 - 140, 700, 120, 6)          # cùng cột, xa vùng chữ
        self.assertLess(near + 5, far, stdout)                          # tấm tối mềm ôm sát vùng chữ

    def test_ban_doc_tieu_de_nam_giua_vung_chu_khong_de_khoang_trong(self):
        stdout = self.render(self.tsv("Chợ Sáng Bánh Mì & Trà Đá", nen=self.nen, chan_dung=self.cutout), "--doc")
        m = re.findall(r"vùng chữ x=\d+–\d+ y=(\d+)–(\d+)", stdout)[-1]
        self.assertLess(abs((int(m[0]) + int(m[1])) / 2 - 665), 60)    # giữa nhãn góc và chân dung

    def test_ten_anh_ra_doi_ky_tu_windows_khong_cho(self):
        video = os.path.join(self.src, "Buổi 1_P02 - Quán: Phở?.mp4")
        write(video, "")
        path = self.p("w", "thumbnail.tsv")
        write(path, "# assets: %s\n" % self.src + HEADER + "\n" + row(video) + "\n")
        stdout = self.render(path)
        self.assertTrue(os.path.exists(self.p("w", "Buổi 1_P02 - Quán - Phở-.jpg")), stdout)

    def test_logo_goc_tren_phai(self):
        self.render(self.tsv(nen=self.nen, logo=self.logo))
        self.assertGreater(stat(self.out(), "UAVG", 1280 - 40 - 60, 40, 40, 40), 180)

    def test_khong_chan_dung_tieu_de_dai_dung_ca_be_ngang_toi_da_3_dong(self):
        title = ("Chị Lan Bán Bánh Mì Đầu Ngõ: Bí Quyết Giữ Khách Quen, Tính Lãi Từng Ổ & Chuyển Khoản Không "
                 "Nhầm (Phần 2) – Hỏi Đáp Cuối Buổi Với Cả Xóm")
        lines, x0, x1, y0, y1 = self.area(self.render(self.tsv(title, nen=self.nen)))
        self.assertEqual(lines, 3)
        self.assertGreater(x1, 800)
        self.assertGreaterEqual(x0, 64)
        self.assertLessEqual(x1, 1216)
        self.assertGreaterEqual(y0, 110)
        self.assertLessEqual(y1, 664)
        self.assertLess(stat(self.out(), "YMAX", 0, 690, 1280, 30), 150)  # đáy trống

    def test_tieu_de_qua_dai_bao_loi_khong_tao_file(self):
        self.fail_with("LỖI", "render", self.tsv("Bánh Mì Pate Chả " * 11), "--ffmpeg", LIBASS, "--doc")
        self.assertFalse(os.path.exists(self.out()))

    def test_ngat_tay_qua_dai_goi_y_bo_dau_ngat(self):
        title = "Chị Lan Bán Bánh Mì Pate Chả Lụa Đầu Ngõ Và Bí Quyết Giữ Khách Quen Mỗi Sáng|Phần 2"
        res = self.fail_with("bỏ |", "render", self.tsv(title), "--ffmpeg", LIBASS)
        self.assertIn("(ngang)", res.stdout)
        self.assertFalse(os.path.exists(self.out()))

    def test_ban_doc_khong_vua_cho_ngat_tu_ngat_lai_khong_chan_ban_ngang(self):
        title = "Bí Quyết Giữ Khách Quen Cho Quán Phở Đầu Ngõ:|Từ Cách Chào Hỏi, Giữ Giá Ổn Định Đến Chăm Sóc Khách"
        stdout = self.render(self.tsv(title), "--doc")
        self.assertIn("(doc)", stdout)
        self.assertIn("Cảnh báo:", stdout)
        self.assertTrue(os.path.exists(self.out()))
        self.assertTrue(os.path.exists(self.p("out", "Buổi 1_P01 - Quán Quen - doc.jpg")))

    def test_ban_doc_qua_dai_van_in_ban_ngang(self):
        stdout = self.render(self.tsv(DOC_TOO_LONG), "--doc")
        self.assertIn("chưa in bản dọc", stdout)
        self.assertTrue(os.path.exists(self.out()))
        self.assertFalse(os.path.exists(self.p("out", "Buổi 1_P01 - Quán Quen - doc.jpg")))

    def test_lenh_ass_trong_tieu_de_la_chu_thuong(self):
        self.assertEqual(self.area(self.render(self.tsv("Quán {\\an8}Quen\\N")))[0], 1)

    def test_khong_ghi_de_khong_ghi_xuyen_symlink_bo_qua_khi_duoc_bao(self):
        tsv = self.tsv()
        self.render(tsv)
        before = readb(self.out())
        self.fail_with("không ghi đè", "render", tsv, "--ffmpeg", LIBASS)
        self.assertEqual(readb(self.out()), before)
        self.assertIn("Bỏ qua", self.render(tsv, "--skip-existing"))
        self.assertEqual(readb(self.out()), before)
        tsv2 = self.tsv(out="s")
        real = self.p("that.jpg")
        os.symlink(real, self.out("s"))
        self.fail_with("không ghi đè", "render", tsv2, "--ffmpeg", LIBASS)
        self.assertFalse(os.path.exists(real))

    def test_chay_hai_lan_cung_byte_va_ban_doc(self):
        cols = {"nen": self.nen, "chan_dung": self.cutout, "logo": self.logo}
        self.render(self.tsv(out="a", **cols), "--doc")
        stdout = self.render(self.tsv(out="b", **cols), "--doc")
        self.assertEqual(readb(self.out("a")), readb(self.out("b")))
        doc = self.p("b", "Buổi 1_P01 - Quán Quen - doc.jpg")
        self.assertEqual(readb(doc), readb(self.p("a", "Buổi 1_P01 - Quán Quen - doc.jpg")))
        self.assertEqual(dims(doc), ("mjpeg", 1080, 1920))
        self.assertLess(os.path.getsize(doc), 2 * 1024 * 1024)
        self.assertIn("doc.jpg", stdout)


if __name__ == "__main__":
    unittest.main()
