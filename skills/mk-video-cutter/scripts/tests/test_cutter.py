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

    def fail(self, *args):
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
        err = self.fail("parse", self.path("not_found.txt"))
        self.assertIn("không đọc được", err)


class TestProbe(Base):
    def test_probe_missing_file(self):
        err = self.fail("probe", self.path("not_found.mp4"))
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
        dup_err = self.fail("cut", vid, "--sheet", plan, "--prefix", "Buổi 1",
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


if __name__ == "__main__":
    unittest.main()
