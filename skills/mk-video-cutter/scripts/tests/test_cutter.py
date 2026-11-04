"""Tests for mk-video-cutter/scripts/cutter.py. Run: python3 -m unittest discover -s skills/mk-video-cutter/scripts/tests"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cutter.py")

SAMPLE_PLAN = """
00:00:00 | CUT  | Đầu giờ  | | Mic check
00:00:01 | KEEP | P1       | Khởi Động | Bắt đầu
00:00:02 | END
"""

SAMPLE_MD = """# Buổi 1: Tổng Quan

### ⏱️ Bảng lệnh cắt file con (Editor Action Sheet)

| Phân đoạn | Timecode video gốc | Lệnh | Thời lượng | Tên file con | Ghi chú cắt & điểm nối |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Đầu giờ** | `00:00:00 - 00:00:00` | 🛑 **CẮT BỎ (CUT)** | 1p 00s | *Nhiễu: Đầu giờ* | Mic |
| **P1** | `00:00:01 - 00:00:02` | 🟢 **GIỮ LẠI (KEEP)** | 1p 00s | **Buổi 1:P1 - Khởi Động** | Điểm nối |
"""

SAMPLE_CSV = """stt,lenh,ma,nhan,ten_file,bat_dau,ket_thuc,thoi_luong_giay,tieu_de,ghi_chu
1,CUT,Đầu giờ,,Nhiễu,00:00:00,00:00:00,1,,Mic
2,KEEP,P1,Buổi 1:P1,Buổi 1-P1 - Khởi Động,00:00:01,00:00:02,1,Khởi Động,Điểm nối
"""


def run(*args):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for root, dirs, files in os.walk(self.d, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError:
                    pass
        try:
            os.rmdir(self.d)
        except OSError:
            pass

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
        self.assertEqual(res.returncode, 0, "STDERR: %s\nSTDOUT: %s" % (res.stderr, res.stdout))
        return res.stdout

    def fails(self, *args):  # không đặt tên `fail`: sẽ che TestCase.fail và nuốt mọi assert hỏng
        res = run(*args)
        self.assertNotEqual(res.returncode, 0, "Lẽ ra phải lỗi nhưng thoát 0:\n" + res.stdout)
        return res.stdout + res.stderr


class TestParse(Base):
    def test_parse_plan_txt(self):
        plan_file = self.path("plan.txt", SAMPLE_PLAN)
        out = self.ok("parse", plan_file, "--prefix", "Buổi 1")
        self.assertIn("1 phân đoạn KEEP", out)
        self.assertIn("Buổi 1-P1 - Khởi Động.mp4", out)

    def test_parse_md_action_sheet(self):
        md_file = self.path("sheet.md", SAMPLE_MD)
        out = self.ok("parse", md_file)
        self.assertIn("1 phân đoạn KEEP", out)
        self.assertIn("Buổi 1-P1 - Khởi Động.mp4", out)

    def test_parse_csv(self):
        csv_file = self.path("sheet.csv", SAMPLE_CSV)
        out = self.ok("parse", csv_file)
        self.assertIn("1 phân đoạn KEEP", out)
        self.assertIn("Buổi 1-P1 - Khởi Động.mp4", out)

    def test_parse_missing_file(self):
        err = self.fails("parse", self.path("not_found.txt"))
        self.assertIn("không đọc được", err)


class TestProbe(Base):
    def test_probe_missing_file(self):
        err = self.fails("probe", self.path("not_found.mp4"))
        self.assertIn("không đọc được thông số", err)

    def test_probe_synthetic(self):
        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
            self.skipTest("cần ffmpeg")
        vid = self.path("test.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=1",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-c:a", "aac", vid
        ], capture_output=True)
        out = self.ok("probe", vid, "--sample-time", "00:00:00", "--duration", "1")
        self.assertIn("# probe:", out)
        self.assertIn("Khuyến nghị:", out)

    def tone(self, name, left, right, seconds):
        """Âm thanh tổng hợp stereo 8 kHz: biểu thức ffmpeg cho từng kênh."""
        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
            self.skipTest("cần ffmpeg")
        out = self.path(name)
        res = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                              "aevalsrc=exprs=%s|%s:s=8000:d=%d" % (left, right, seconds),
                              "-c:a", "pcm_s16le", out], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return out

    def test_probe_silence_at_old_sample_is_copy(self):
        # 16 phút tiếng to, im lặng đúng quanh 00:15:00 (mốc mẫu cũ) → đo cả file vẫn copy
        loud = "0.3*sin(2*PI*440*t)*not(between(t\\,880\\,940))"
        wav = self.tone("pause.wav", loud, loud, 960)
        out = self.ok("probe", wav)
        self.assertIn("Độ to tích hợp cả file:", out)
        self.assertIn("Khuyến nghị: Mode 1 (copy)", out)
        self.assertIn("Giữ một chế độ cho cả khoá", out)
        out = self.ok("probe", wav, "--sample-time", "00:15:00", "--sample-time", "00:01:00")
        self.assertIn("Mẫu 00:15:00 (30 giây):", out)
        self.assertIn("gần im lặng (< -45 dB), bỏ qua", out)
        self.assertIn("Mẫu 00:01:00 (30 giây):", out)
        self.assertIn("chỉ để tham khảo", out)
        self.assertIn("Khuyến nghị: Mode 1 (copy)", out)

    def test_probe_one_channel_dead_is_balance(self):
        wav = self.tone("left.wav", "0.3*sin(2*PI*440*t)", "0", 20)
        out = self.ok("probe", wav)
        self.assertIn("Điếc 1 bên tai", out)
        self.assertIn("Lệch kênh (Δ): ∞ dB", out)
        self.assertIn("Khuyến nghị: Mode 2 (balance)", out)

    def test_probe_quiet_file_is_master(self):
        quiet = "0.01*sin(2*PI*440*t)"
        wav = self.tone("quiet.wav", quiet, quiet, 20)
        out = self.ok("probe", wav)
        self.assertIn("Âm lượng quá nhỏ (< -24 LUFS)", out)
        self.assertIn("Khuyến nghị: Mode 3 (master)", out)

    def test_probe_near_threshold_warns(self):
        # sine 1 kHz biên độ 0.07, stereo → cả file ≈ −23.1 LUFS, trong ±1 LU quanh −24
        near = "0.07*sin(2*PI*1000*t)"
        wav = self.tone("near.wav", near, near, 20)
        out = self.ok("probe", wav)
        self.assertIn("sát ngưỡng", out)


class TestCut(Base):
    def test_cut_dry_run_and_execution(self):
        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
            self.skipTest("cần ffmpeg")
        vid = self.path("sample.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=1",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-c:a", "aac", vid
        ], capture_output=True)
        plan = self.path("plan.txt", SAMPLE_PLAN)
        out_dir = self.path("output_cuts")

        # 1. Dry run
        dry_out = self.ok("cut", vid, "--sheet", plan, "--prefix", "Buổi 1",
                          "--out-dir", out_dir, "--dry-run")
        self.assertIn("DRY-RUN:", dry_out)
        self.assertFalse(os.path.exists(out_dir))

        # 2. Execution thật với mode copy
        cut_out = self.ok("cut", vid, "--sheet", plan, "--prefix", "Buổi 1",
                          "--out-dir", out_dir, "--mode", "copy")
        self.assertIn("Hoàn tất cắt 1 video con", cut_out)
        target_clip = os.path.join(out_dir, "Buổi 1-P1 - Khởi Động.mp4")
        self.assertTrue(os.path.exists(target_clip))

        # 3. Chống ghi đè
        dup_err = self.fails("cut", vid, "--sheet", plan, "--prefix", "Buổi 1",
                            "--out-dir", out_dir, "--mode", "copy")
        self.assertIn("đã có — xoá file hoặc đổi thư mục (không ghi đè)", dup_err)


class TestVerify(Base):
    def test_verify_files(self):
        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
            self.skipTest("cần ffmpeg")
        out_dir = self.path("verify_dir")
        os.makedirs(out_dir, exist_ok=True)
        clip = os.path.join(out_dir, "Buổi 1-P1 - Khởi Động.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-c:a", "aac", clip
        ], capture_output=True)
        out = self.ok("verify", out_dir)
        self.assertIn("Nghiệm thu video con trong:", out)
        self.assertIn("Buổi 1-P1 - Khởi Động.mp4", out)
        self.assertIn("HỢP LỆ", out)



def has_ffmpeg():
    return subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0


def make_video(path, vf, size="320x180", src="testsrc2", seconds=12):
    """Video giả: nội dung chuyển động (testsrc2 + nhiễu theo thời gian, như người giảng cử động) hoặc đứng yên
    (color), có thể bọc viền tĩnh bằng pad."""
    source = "%s%ssize=%s:rate=5:duration=%d" % (src, ":" if "=" in src else "=", size, seconds)
    chain = vf if src.startswith("color") else "noise=alls=30:allf=t," + vf
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", source,
                    "-f", "lavfi", "-i", "sine=frequency=500:duration=%d" % seconds, "-vf", chain,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path],
                   capture_output=True, check=True)


def dims(path):
    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True)
    return res.stdout.strip()


PLAN_12S = "00:00:00 | KEEP | P1 | Thử Khung | x\n00:00:12 | END\n"
# Nội dung 320x180 chuyển động, bọc viền tĩnh xám kiểu thanh Zoom: trên 40, dưới 40, trái 40, phải 40 → khung 400x260
ZOOM_LIKE = "pad=400:260:40:40:color=0x303030"


def make_layout_change(path):
    """32 giây kiểu Zoom: thanh xám trên/dưới 40 px; nội dung hẹp (dải đen 80 px hai bên), riêng 13–19 giây đổi sang
    bố cục rộng (dải đen 40 px) — như Zoom chuyển chế độ xem giữa đoạn P2."""
    graph = ("[0:v]noise=alls=30:allf=t,split[a][b];[a]crop=320:220,pad=480:300:80:40:color=black[n];"
             "[b]pad=480:300:40:40:color=black[w];[n][w]overlay=enable='between(t,13,19)',"
             "drawbox=0:0:480:40:color=0x303030:t=fill,drawbox=0:260:480:40:color=0x303030:t=fill[v]")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=400x220:rate=5:duration=32",
                    "-f", "lavfi", "-i", "sine=frequency=500:duration=32", "-filter_complex", graph,
                    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path],
                   capture_output=True, check=True)


PLAN_3 = ("00:00:00 | KEEP | P1 | Mở Đầu | x\n00:00:10 | KEEP | P2 | Chia Màn Hình | x\n"
          "00:00:22 | KEEP | P3 | Hỏi Đáp | x\n00:00:32 | END\n")


@unittest.skipUnless(has_ffmpeg(), "cần ffmpeg")
class TestFrame(Base):
    def crop_of(self, out):
        line = [l for l in out.splitlines() if "--crop" in l][0]
        return [int(v) for v in line.rsplit("--crop ", 1)[1].split(":")]

    def test_phat_hien_vien_tinh_va_giu_tron_noi_dung(self):
        vid = self.path("zoom.mp4")
        make_video(vid, ZOOM_LIKE)
        out = self.ok("frame", vid)
        self.assertIn("Viền thừa: có", out)
        w, h, x, y = self.crop_of(out)
        # khung đề xuất bám sát vùng nội dung 320x180 tại (40,40), sai số ≤ 4 px, không lấn ra viền quá 4 px
        for got, want in ((w, 320), (h, 180), (x, 40), (y, 40)):
            self.assertLessEqual(abs(got - want), 4, out)
        self.assertTrue(w % 2 == 0 and h % 2 == 0 and x % 2 == 0 and y % 2 == 0, "toạ độ crop phải chẵn")

    def test_video_khong_vien_giu_nguyen_khung(self):
        vid = self.path("clean.mp4")
        make_video(vid, "null")
        out = self.ok("frame", vid)
        self.assertIn("Viền thừa: không có", out)
        self.assertNotIn("--crop", out)

    def test_hinh_dung_yen_khong_ket_luan_va_khong_cat(self):
        vid = self.path("still.mp4")
        make_video(vid, "null", src="color=c=gray")
        out = self.ok("frame", vid, "--aspect", "16:9", "--res", "180")
        self.assertIn("không kết luận được", out)
        self.assertNotIn("crop=", out)

    def test_preview_ghi_hai_anh_va_khong_ghi_de(self):
        vid = self.path("zoom.mp4")
        make_video(vid, ZOOM_LIKE)
        prev = self.path("xem-truoc")
        self.ok("frame", vid, "--aspect", "16:9", "--res", "360", "--preview", prev)
        self.assertEqual(dims(os.path.join(prev, "khung-dau-ra.png")), "640,360")
        self.assertTrue(os.path.getsize(os.path.join(prev, "khung-phat-hien.png")) > 0)
        err = self.fails("frame", vid, "--preview", prev)
        self.assertIn("không ghi đè", err)

    def test_crop_ngoai_khung_bi_tu_choi(self):
        vid = self.path("zoom.mp4")
        make_video(vid, ZOOM_LIKE, seconds=6)
        err = self.fails("frame", vid, "--crop", "400:260:10:0")
        self.assertIn("nằm ngoài khung", err)

    def test_only_ma_khong_co_bao_loi(self):
        vid = self.path("zoom.mp4")
        make_video(vid, ZOOM_LIKE, seconds=6)
        err = self.fails("frame", vid, "--sheet", self.path("plan.txt", PLAN_12S), "--only", "P9")
        self.assertIn("không có đoạn KEEP mã P9", err)

    def test_bo_cuc_doi_chi_dung_doan_va_anh_co_ca_hai_bo_cuc(self):
        vid = self.path("doi.mp4")
        make_layout_change(vid)
        prev = self.path("xem")
        out = self.ok("frame", vid, "--sheet", self.path("plan.txt", PLAN_3), "--preview", prev)
        warn = [l for l in out.splitlines() if l.startswith("Cảnh báo: bố cục đổi")][0]
        self.assertRegex(warn, r"rộng \(dùng hết khung\) [^;]*· đoạn P2\.")
        self.assertIn("→ Tách khung: chạy riêng --only P1,P3 và --only P2", out)
        # ảnh 4 mẫu phải có cả hai bố cục để người dùng thấy dải đen sẽ còn ở đâu
        self.assertIn("(bố cục hẹp)", out)
        self.assertIn("(bố cục rộng)", out)
        self.assertIn("bố cục đa số", out)

    def test_only_rong_bi_tu_choi(self):
        vid = self.path("zoom.mp4")
        make_video(vid, ZOOM_LIKE, seconds=6)
        err = self.fails("frame", vid, "--sheet", self.path("plan.txt", PLAN_12S), "--only", ",")
        self.assertIn("cần ít nhất một mã", err)


@unittest.skipUnless(has_ffmpeg(), "cần ffmpeg")
class TestCutFrame(Base):
    def setUp(self):
        super().setUp()
        self.vid = self.path("zoom.mp4")
        make_video(self.vid, ZOOM_LIKE)
        self.plan = self.path("plan.txt", PLAN_12S)
        self.clip = "Buổi 9-P1 - Thử Khung.mp4"

    def test_cat_vien_nang_16_9_nen_den(self):
        out_dir = self.path("out")
        self.ok("cut", self.vid, "--sheet", self.plan, "--prefix", "Buổi 9", "--out-dir", out_dir, "--mode", "copy",
                "--crop", "320:180:40:40", "--aspect", "16:9", "--res", "360")
        self.assertEqual(dims(os.path.join(out_dir, self.clip)), "640,360")
        out = self.ok("verify", out_dir, "--expect-size", "640x360")
        self.assertIn("640x360", out)

    def test_khung_doc_9_16_nen_mo(self):
        out_dir = self.path("out")
        self.ok("cut", self.vid, "--sheet", self.plan, "--prefix", "Buổi 9", "--out-dir", out_dir, "--mode", "copy",
                "--crop", "320:180:40:40", "--aspect", "9:16", "--res", "180", "--fit", "blur")
        self.assertEqual(dims(os.path.join(out_dir, self.clip)), "180,320")

    def test_kich_thuoc_tuy_chinh(self):
        out_dir = self.path("out")
        self.ok("cut", self.vid, "--sheet", self.plan, "--prefix", "Buổi 9", "--out-dir", out_dir, "--mode", "copy",
                "--size", "200x250")
        self.assertEqual(dims(os.path.join(out_dir, self.clip)), "200,250")

    def test_khong_tuy_chon_khung_thi_giu_nguyen_hinh(self):
        out = self.ok("cut", self.vid, "--sheet", self.plan, "--out-dir", self.path("out"), "--mode", "copy",
                      "--dry-run")
        self.assertIn("-c:v copy", out)
        self.assertNotIn("-vf", out)

    def test_verify_sai_khung_bao_loi(self):
        out_dir = self.path("out")
        self.ok("cut", self.vid, "--sheet", self.plan, "--prefix", "Buổi 9", "--out-dir", out_dir, "--mode", "copy")
        out = self.fails("verify", out_dir, "--expect-size", "1920x1080")
        self.assertIn("LỖI: KHUNG 400x260 ≠ 1920x1080", out)

    def test_verify_doi_chieu_ten_co_prefix(self):
        out_dir = self.path("out")
        self.ok("cut", self.vid, "--sheet", self.plan, "--prefix", "Buổi 9", "--out-dir", out_dir, "--mode", "copy")
        out = self.ok("verify", out_dir, "--sheet", self.plan, "--prefix", "Buổi 9")
        self.assertNotIn("không clip nào khớp", out)
        out = self.ok("verify", out_dir, "--sheet", self.plan)
        self.assertIn("không clip nào khớp", out)

    def test_lam_net_nhe_ma_hoa_lai_va_giu_khung(self):
        out_dir = self.path("out")
        dry = self.ok("cut", self.vid, "--sheet", self.plan, "--out-dir", out_dir, "--mode", "copy",
                      "--crop", "320:180:40:40", "--enhance", "--dry-run")
        self.assertIn("deblock", dry)
        self.assertIn("cas=", dry)
        self.assertNotIn("-c:v copy", dry)
        self.ok("cut", self.vid, "--sheet", self.plan, "--prefix", "Buổi 9", "--out-dir", out_dir, "--mode", "copy",
                "--crop", "320:180:40:40", "--enhance")
        self.assertEqual(dims(os.path.join(out_dir, self.clip)), "320,180")


@unittest.skipUnless(has_ffmpeg(), "cần ffmpeg")
class TestResAuto(Base):
    """Nguồn 720p: auto lên đúng một bậc chuẩn (1080p) ở mọi tỉ lệ khung, không lên 2K/4K."""

    def setUp(self):
        super().setUp()
        self.vid = self.path("hd.mp4")
        make_video(self.vid, "null", size="1280x720", seconds=4)

    def output_of(self, *extra):
        out = self.ok("frame", self.vid, "--crop", "none", "--res", "auto", *extra)
        return [l for l in out.splitlines() if l.startswith("Đầu ra:")][0], out

    def test_720p_ngang_len_1080p(self):
        line, out = self.output_of("--aspect", "16:9")
        self.assertIn("1920x1080", line)
        self.assertIn("1440p (khung x2.00", out)

    def test_720p_doc_9_16_len_1080x1920_khong_phinh_2k(self):
        line, _ = self.output_of("--aspect", "9:16", "--fit", "blur")
        self.assertIn("1080x1920", line)

    def test_nguon_nho_khong_phong_qua_muc(self):
        small = self.path("nho.mp4")
        make_video(small, "null", size="320x180", seconds=4)
        out = self.ok("frame", small, "--crop", "none", "--aspect", "16:9", "--res", "auto")
        self.assertIn("Đầu ra: 320x180", out)  # 360p đã là x2.00 > x1.8 → giữ cỡ nguồn

    def test_ep_len_4k_bi_canh_bao(self):
        out = self.ok("frame", self.vid, "--crop", "none", "--aspect", "16:9", "--res", "2160")
        self.assertIn("vượt mức vừa phải", out)
        self.assertIn("chọn 1920x1080", out)

    def test_720p_cat_vien_day_van_len_1080p(self):
        # viền Zoom dày: nội dung còn 1040x582, vẫn là nguồn 720p → 1080p (nội dung phóng x1.85 ≤ x2.0)
        out = self.ok("frame", self.vid, "--crop", "1040:582:120:70", "--aspect", "16:9", "--res", "auto")
        self.assertIn("Đầu ra: 1920x1080", out)

    def test_1080p_khung_doc_giu_1080x1920(self):
        fhd = self.path("fhd.mp4")
        make_video(fhd, "null", size="1920x1080", seconds=3)
        out = self.ok("frame", fhd, "--crop", "none", "--aspect", "9:16", "--res", "auto", "--fit", "blur")
        self.assertIn("Đầu ra: 1080x1920", out)  # chuẩn Reels/TikTok, không phình 1440x2560
        out = self.ok("frame", fhd, "--crop", "none", "--aspect", "16:9", "--res", "auto")
        self.assertIn("Đầu ra: 2560x1440", out)  # khung ngang: một bậc trên nguồn


class TestWindowsPipeEncoding(Base):
    """Windows ghi ra pipe bằng bảng mã hệ thống (cp1252): chữ Việt không được làm script dừng."""

    def test_parse_prints_vietnamese_under_cp1252(self):
        plan_file = self.path("plan.txt", SAMPLE_PLAN)
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        res = subprocess.run([sys.executable, SCRIPT, "parse", plan_file, "--prefix", "Buổi 1"],
                             capture_output=True, env=env)
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
        self.assertIn("Buổi 1-P1 - Khởi Động.mp4", res.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
