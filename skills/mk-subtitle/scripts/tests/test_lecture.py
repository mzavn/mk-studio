"""Tests for mk-subtitle/scripts/lecture.py. Run: python3 -m unittest discover -s skills/mk-subtitle/scripts/tests"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lecture.py")

SAMPLE_TXT = """Kinh Dịch Buổi 99 - YouTube

[00:00] Alo alo xin kính chào cả lớp, mọi người nghe rõ micro và bật hết camera lên chưa ạ. Chúng ta điểm danh rồi bắt đầu.
[05:00] Bác trưởng lớp chia sẻ màn hình giúp thầy với. Bây giờ thầy bắt đầu bài giảng chính hôm nay.
[15:00] Khái niệm thứ nhất là âm dương đối đãi trong tự nhiên.
[25:00] Khái niệm thứ hai là tam tài thiên địa nhân.
[30:00] Lớp mình dừng ở đây nghỉ giải lao năm phút nhé, quý vị quay lại lớp đúng giờ.
[35:30] Mời cả lớp vào lại lớp, chúng ta tiếp tục với phần ba.
[45:00] Phần ba là phân tích quẻ càn và ứng dụng thực tiễn.
[55:00] Học viên Chu Văn hỏi: Thầy ơi cho em hỏi câu hỏi về vận số có thay đổi được không.
[56:00] Thầy đáp: Số mệnh do nhân khí tu tập mà chuyển hóa, dịch cãi được số.
[1:05:00] Thầy dặn dò: Buổi học đến đây bế mạc, chúc cả lớp ngủ ngon và hẹn gặp lại buổi sau.
"""

SAMPLE_SRT = """1
00:00:00,000 --> 00:00:05,000
Mic check và chào lớp.

2
00:05:00,000 --> 00:05:10,000
Thầy bắt đầu giảng bài.

3
00:25:00,000 --> 00:25:10,000
Nội dung phần một.

4
00:30:00,000 --> 00:30:08,000
Nghỉ giải lao năm phút.

5
00:35:00,000 --> 00:35:10,000
Vào lại lớp học tiếp.

6
00:55:00,000 --> 00:55:10,000
Học viên đặt câu hỏi.

7
00:58:00,000 --> 00:58:10,000
Thầy giải đáp câu hỏi.

8
01:05:00,000 --> 01:06:00,000
Chúc ngủ ngon và bế mạc.
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


class TestScan(Base):
    def test_scan_txt_detects_signals(self):
        src = self.path("bai.txt", SAMPLE_TXT)
        out = self.ok("scan", src)
        self.assertIn("Loại: bản chép lời có mốc đầu dòng", out)
        self.assertIn("Thủ tục / đầu giờ", out)
        self.assertIn("Giải lao", out)
        self.assertIn("Vấn đáp", out)
        self.assertIn("Kết buổi", out)
        self.assertIn("Quãng lặng ≥ 90 giây", out)

    def test_scan_srt(self):
        src = self.path("bai.srt", SAMPLE_SRT)
        out = self.ok("scan", src)
        self.assertIn("Loại: SRT", out)
        self.assertIn("Thời lượng: 00:00:00 → 01:06:00", out)


class TestPlan(Base):
    def test_plan_valid_txt(self):
        src = self.path("bai.txt", SAMPLE_TXT)
        plan = self.path("plan.txt", """
00:00:00 | CUT  | Đầu giờ  | | Mic check và ổn định lớp
00:05:00 | KEEP | P1       | Khái Niệm Âm Dương & Tam Tài | Bắt đầu từ câu giảng chính
00:30:00 | CUT  | Giải lao | | Cắt sạch thời gian nghỉ giữa giờ
00:35:30 | KEEP | P2       | Phân Tích Quẻ Càn & Vấn Đáp  | Nối tiếp sau giải lao
01:06:00 | END
""")
        out = self.ok("plan", src, "--plan", plan, "--prefix", "Buổi 99")
        self.assertIn("Gốc 66p 00s · cắt 10p 30s (2 đoạn) · giữ 55p 30s · 2 file con", out)
        self.assertIn("Dòng kaizen: | **Buổi 99** |", out)
        self.assertIn("Đầu giờ 5p 00s + Giải lao 5p 30s", out)

    def test_plan_4_column_cut(self):
        src = self.path("bai.txt", SAMPLE_TXT)
        plan = self.path("plan4.txt", """
00:00:00 | CUT  | Đầu giờ  | Mic check và điểm danh
00:05:00 | KEEP | P1       | Khởi Động | Bắt đầu
01:06:00 | END
""")
        out = self.ok("plan", src, "--plan", plan, "--prefix", "Buổi 99")
        self.assertIn("Đầu giờ: Mic check và điểm danh", out)
    def test_plan_generates_md_and_csv_sheets(self):
        src = self.path("bai.srt", SAMPLE_SRT)
        plan = self.path("plan.txt", """
00:00:00 | CUT  | Đầu giờ  | | Mic check
00:05:00 | KEEP | P1       | Phần Một | Mở màn
00:30:00 | CUT  | Giải lao | | Nghỉ
00:35:00 | KEEP | P2       | Phần Hai | Tiếp tục
01:06:00 | END
""")
        out_md = self.path("sheet.md")
        out_csv = self.path("sheet.csv")
        self.ok("plan", src, "--plan", plan, "--prefix", "Buổi 99", "--out-md", out_md, "--out-csv", out_csv)
        self.assertTrue(os.path.exists(out_md))
        self.assertTrue(os.path.exists(out_csv))
        md_text = self.read("sheet.md")
        self.assertIn("### ⏱️ Bảng lệnh cắt file con (Editor Action Sheet)", md_text)
        self.assertIn("🛑 **CẮT BỎ (CUT)**", md_text)
        self.assertIn("🟢 **GIỮ LẠI (KEEP)**", md_text)
        self.assertIn("Buổi 99:P1 - Phần Một", md_text)
        csv_text = self.read("sheet.csv")
        self.assertIn("stt,lenh,ma,nhan,ten_file,bat_dau,ket_thuc,thoi_luong_giay,tieu_de,ghi_chu", csv_text)

    def test_plan_errors(self):
        src = self.path("bai.txt", SAMPLE_TXT)

        # Không bắt đầu từ 00:00:00
        p1 = self.path("p1.txt", "00:05:00 | KEEP | P1 | Tieu de | Note\n01:06:00 | END\n")
        err1 = self.fail("plan", src, "--plan", p1)
        self.assertIn("dòng đầu phải bắt đầu 00:00:00", err1)

        # Mốc lùi
        p2 = self.path("p2.txt", "00:00:00 | CUT | Đầu | | Note\n00:03:00 | KEEP | P1 | Tiêu đề | Note\n00:02:00 | END\n")
        err2 = self.fail("plan", src, "--plan", p2)
        self.assertIn("không sau mốc dòng trước", err2)

        # Trùng mã KEEP
        p3 = self.path("p3.txt", "00:00:00 | KEEP | P1 | Tiêu đề A | Note\n00:30:00 | KEEP | P1 | Tiêu đề B | Note\n01:06:00 | END\n")
        err3 = self.fail("plan", src, "--plan", p3)
        self.assertIn("mã P1 trùng", err3)

        # CUT thiếu lý do
        p4 = self.path("p4.txt", "00:00:00 | CUT | Đầu | | \n00:05:00 | KEEP | P1 | Tiêu đề | Note\n01:06:00 | END\n")
        err4 = self.fail("plan", src, "--plan", p4)
        self.assertIn("CUT thiếu lý do", err4)

        # TXT thiếu END
        p5 = self.path("p5.txt", "00:00:00 | CUT | Đầu | | Note\n00:05:00 | KEEP | P1 | Tiêu đề | Note\n")
        err5 = self.fail("plan", src, "--plan", p5)
        self.assertIn("thiếu dòng 'hh:mm:ss | END'", err5)

    def test_plan_warnings(self):
        src = self.path("bai.txt", SAMPLE_TXT)
        # 00:02:00 rơi vào giữa câu [00:00] kéo dài tới [05:00]
        # P1 dài 3 phút (dưới 20 phút)
        p = self.path("p.txt", """
00:00:00 | CUT  | Đầu      | | Note
00:02:00 | KEEP | P1       | Phần Ngắn | Note
00:05:00 | KEEP | P2       | Phần Hai   | Note
01:06:00 | END
""")
        out = self.ok("plan", src, "--plan", p)
        self.assertIn("Cảnh báo:", out)
        self.assertIn("rơi giữa câu [00:00]", out)
        self.assertIn("dài 3p 00s — ngoài khoảng 20–30 phút", out)


class TestSplit(Base):
    def test_split_generates_md_skeleton(self):
        src = self.path("bai.txt", SAMPLE_TXT)
        plan = self.path("plan.txt", """
00:00:00 | CUT  | Đầu giờ  | | Mic check
00:05:00 | KEEP | P1       | Khởi Động | Mở bài
00:30:00 | CUT  | Giải lao | | Nghỉ giữa giờ
00:35:30 | KEEP | P2       | Chuyên Đề | Thân bài
01:06:00 | END
""")
        out_md = self.path("bai_out.md")
        out = self.ok("split", src, "--plan", plan, "--prefix", "Buổi 99", "--out-md", out_md)
        self.assertIn("Khung bài giảng →", out)
        self.assertTrue(os.path.exists(out_md))
        content = self.read("bai_out.md")
        self.assertIn("# {{điền: tên khoá", content)
        self.assertIn("### ⏱️ Bảng lệnh cắt file con", content)
        self.assertIn("### 🛑 [00:00 - 04:59] Đầu giờ — CẮT BỎ", content)
        self.assertIn("### 🎬 Buổi 99:P1 [05:00 - 29:59] Khởi Động", content)
        self.assertIn("### 🛑 [30:00 - 35:29] Giải lao — CẮT BỎ", content)
        self.assertIn("### 🎬 Buổi 99:P2 [35:30 - 1:05:59] Chuyên Đề", content)

    def test_split_refuses_overwrite(self):
        src = self.path("bai.txt", SAMPLE_TXT)
        plan = self.path("plan.txt", "00:00:00 | KEEP | P1 | Tieu de | Note\n01:06:00 | END\n")
        out_md = self.path("exist.md", "old content")
        err = self.fail("split", src, "--plan", plan, "--out-md", out_md)
        self.assertIn("đã có — chọn tên khác", err)

    def test_split_srt_dir(self):
        src = self.path("bai.srt", SAMPLE_SRT)
        plan = self.path("plan.txt", """
00:00:00 | CUT  | Đầu giờ  | | Mic
00:05:00 | KEEP | P1       | Phần Một | Khởi đầu
00:30:00 | CUT  | Giải lao | | Nghỉ
00:35:00 | KEEP | P2       | Phần Hai | Tiếp
01:06:00 | END
""")
        out_dir = os.path.join(self.d, "subtitles")
        out = self.ok("split", src, "--plan", plan, "--prefix", "Buổi 99", "--out-srt-dir", out_dir)
        self.assertIn("Buổi 99:P1: 2 cue", out)
        self.assertIn("Buổi 99:P2: 4 cue", out)
        p1_file = os.path.join(out_dir, "Buổi 99-P1 - Phần Một.srt")
        self.assertTrue(os.path.exists(p1_file))
        with open(p1_file, encoding="utf-8") as fh:
            p1_content = fh.read()
        self.assertTrue(p1_content.startswith("1\n00:00:00,000 --> 00:00:10,000\nThầy bắt đầu giảng bài."))

    def test_split_srt_dir_refuses_txt(self):
        src = self.path("bai.txt", SAMPLE_TXT)
        plan = self.path("plan.txt", "00:00:00 | KEEP | P1 | T | N\n01:00:00 | END\n")
        out_dir = os.path.join(self.d, "subtitles")
        err = self.fail("split", src, "--plan", plan, "--out-srt-dir", out_dir)
        self.assertIn("phụ đề từng file con cần SRT/VTT thường", err)


class TestLint(Base):
    def test_lint_clean_file(self):
        clean_md = """# Buổi 99: Triết Lý Âm Dương

> **Nguồn:** `bai.txt` · gốc 66p 00s · giữ 55p 30s · 2 file con

### ⏱️ Bảng lệnh cắt file con (Editor Action Sheet)

| Phân đoạn | Timecode video gốc | Lệnh | Thời lượng | Tên file con | Ghi chú cắt & điểm nối |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Đầu giờ** | `00:00:00 - 00:04:59` | 🛑 **CẮT BỎ (CUT)** | 5p 00s | *Nhiễu: Đầu giờ* | Mic |
| **P1** | `00:05:00 - 00:29:59` | 🟢 **GIỮ LẠI (KEEP)** | 25p 00s | **Buổi 99:P1 - Khởi Động** | Điểm nối |
| **P2** | `00:30:00 - 01:05:59` | 🟢 **GIỮ LẠI (KEEP)** | 36p 00s | **Buổi 99:P2 - Chuyên Đề** | Điểm nối |

### 🎬 Buổi 99:P1 [05:00 - 29:59] Khởi Động

[05:00] Nội dung bài mở đầu.

### 🎬 Buổi 99:P2 [30:00 - 1:05:59] Chuyên Đề

[30:00] Nội dung chuyên đề tiếp theo.

> **👤 [A Hỏi - Học viên Lan] [40:00]:** Cho em hỏi về âm dương.
> **🧙‍♂️ [B Đáp - Thầy] [41:00]:** Âm dương là quy luật cân bằng.

> **🧙‍♂️ [B Hỏi - Thầy] [50:00]:** Tại sao lại gọi là càn?
> **👤 [A Đáp - Học viên]:** Vì càn là trời ạ.
> **🧙‍♂️ [B Khai Tuệ - Thầy] [51:00]:** Đúng nhưng sâu xa càn là năng lượng sáng thế.
"""
        doc = self.path("clean.md", clean_md)
        out = self.ok("lint", doc)
        self.assertIn("Kết quả: 0 lỗi", out)

    def test_lint_detects_all_defect_types(self):
        bad_md = """# Buổi Lỗi

```python
unclosed fence

> [!invalid_callout] Sai callout

Chỗ này còn {{điền: nội dung}} chưa điền.

Mốc này phút vượt 60: [00:85:20].

### 🎬 Buổi 99:P1 [05:00 - 29:59] Phần 1
### 🎬 Buổi 99:P2 [20:00 - 45:00] Phần Chồng Lấn

> **👤 [A Hỏi - Lan] [30:00]:** Không ai trả lời câu này!

> **🧙‍♂️ [B Hỏi - Thầy] [35:00]:** Câu hỏi Socrates không ai đáp!
"""
        doc = self.path("bad.md", bad_md)
        err = self.fail("lint", doc)
        self.assertIn("khối code mở bằng ``` chưa đóng", err)
        self.assertIn("callout [!invalid_callout] không phải loại hợp lệ", err)
        self.assertIn("còn chỗ chưa điền", err)
        self.assertIn("mốc 00:85:20 sai", err)
        self.assertIn("chồng lên file con trước", err)
        self.assertIn("[A Hỏi] chưa có [B Đáp] đi kèm", err)


class TestProbeAudio(Base):
    def test_probe_audio_missing_file(self):
        err = self.fail("probe-audio", self.path("not_exist.mp4"))
        self.assertIn("không đọc được thông số âm thanh", err)

    def test_probe_audio_synthetic(self):
        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
            self.skipTest("cần ffmpeg")
        vid = self.path("sample.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=1",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-c:a", "aac", vid
        ], capture_output=True)
        out = self.ok("probe-audio", vid, "--sample-time", "00:00:00", "--duration", "1")
        self.assertIn("# probe-audio:", out)
        self.assertIn("Khuyến nghị:", out)


class TestCutVideo(Base):
    def test_cut_video_missing_file(self):
        plan = self.path("plan.txt", "00:00:00 | KEEP | P1 | T | N\n00:00:01 | END\n")
        err = self.fail("cut-video", self.path("not_exist.mp4"), "--plan", plan, "--out-dir", self.path("out"))
        self.assertIn("không tìm thấy file video nguồn", err)

    def test_cut_video_dry_run_and_execution(self):
        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
            self.skipTest("cần ffmpeg")
        vid = self.path("sample.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=1",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-c:a", "aac", vid
        ], capture_output=True)
        plan = self.path("plan.txt", """
00:00:00 | CUT  | Đầu | | Cắt đầu
00:00:01 | KEEP | P1  | Khởi Động | Đoạn 1
00:00:02 | END
""")
        out_dir = self.path("final_cuts")

        # Dry-run
        out_dry = self.ok("cut-video", vid, "--plan", plan, "--prefix", "Buổi 99",
                          "--out-dir", out_dir, "--dry-run")
        self.assertIn("DRY-RUN: Buổi 99-P1 - Khởi Động.mp4", out_dry)
        self.assertFalse(os.path.exists(out_dir))

        # Thực thi thật
        out_real = self.ok("cut-video", vid, "--plan", plan, "--prefix", "Buổi 99",
                           "--out-dir", out_dir, "--mode", "copy")
        self.assertIn("Hoàn tất cắt 1 video con", out_real)
        expected_file = os.path.join(out_dir, "Buổi 99-P1 - Khởi Động.mp4")
        self.assertTrue(os.path.exists(expected_file))

        # Kiểm tra chống ghi đè
        err_overwrite = self.fail("cut-video", vid, "--plan", plan, "--prefix", "Buổi 99",
                                  "--out-dir", out_dir, "--mode", "copy")
        self.assertIn("đã có — xoá file hoặc đổi thư mục (không ghi đè)", err_overwrite)


class TestWindowsPipeEncoding(Base):
    """Windows ghi ra pipe bằng bảng mã hệ thống (cp1252): chữ Việt không được làm script dừng."""

    def test_scan_prints_vietnamese_under_cp1252(self):
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        cases = ((SCRIPT, self.path("Buổi 99.txt", SAMPLE_TXT)),
                 (os.path.join(os.path.dirname(SCRIPT), "subtitle.py"), self.path("Buổi 99.srt", SAMPLE_SRT)))
        for script, src in cases:
            res = subprocess.run([sys.executable, script, "scan", src], capture_output=True, env=env)
            self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
            self.assertIn("Loại:", res.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
