"""Tests for mk-subtitle/scripts/lecture.py. Run: python3 -m unittest discover -s skills/mk-subtitle/scripts/tests"""
import os
import re
import shutil
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

    def fails(self, *args):  # không đặt tên `fail`: unittest dùng self.fail() khi một assert hỏng
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
        self.assertIn("Quãng lặng ≥ 300 giây", out)  # bản .txt mốc theo đoạn: ngưỡng tối thiểu 5 phút

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
        self.assertIn("Dòng nhật ký khoá: | **Buổi 99** |", out)
        self.assertNotIn("kaizen", out.lower())
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
        self.assertIn("| **P1** |", md_text)
        self.assertIn("**Buổi 99-P1 - Phần Một**", md_text)  # cột tên file con = đúng tên file sẽ xuất
        csv_text = self.read("sheet.csv")
        self.assertIn("stt,lenh,ma,nhan,ten_file,bat_dau,ket_thuc,thoi_luong_giay,tieu_de,ghi_chu", csv_text)

    def test_plan_errors(self):
        src = self.path("bai.txt", SAMPLE_TXT)

        # Không bắt đầu từ 00:00:00
        p1 = self.path("p1.txt", "00:05:00 | KEEP | P1 | Tieu de | Note\n01:06:00 | END\n")
        err1 = self.fails("plan", src, "--plan", p1)
        self.assertIn("dòng đầu phải bắt đầu 00:00:00", err1)

        # Mốc lùi
        p2 = self.path("p2.txt", "00:00:00 | CUT | Đầu | | Note\n00:03:00 | KEEP | P1 | Tiêu đề | Note\n"
                                   "00:02:00 | KEEP | P2 | Tiêu đề 2 | Note\n01:06:00 | END\n")
        err2 = self.fails("plan", src, "--plan", p2)
        self.assertIn("không sau mốc dòng trước", err2)

        # Trùng mã KEEP
        p3 = self.path("p3.txt", "00:00:00 | KEEP | P1 | Tiêu đề A | Note\n00:30:00 | KEEP | P1 | Tiêu đề B | Note\n01:06:00 | END\n")
        err3 = self.fails("plan", src, "--plan", p3)
        self.assertIn("mã P1 trùng", err3)

        # CUT thiếu lý do
        p4 = self.path("p4.txt", "00:00:00 | CUT | Đầu | | \n00:05:00 | KEEP | P1 | Tiêu đề | Note\n01:06:00 | END\n")
        err4 = self.fails("plan", src, "--plan", p4)
        self.assertIn("CUT thiếu lý do", err4)

        # TXT thiếu END
        p5 = self.path("p5.txt", "00:00:00 | CUT | Đầu | | Note\n00:05:00 | KEEP | P1 | Tiêu đề | Note\n")
        err5 = self.fails("plan", src, "--plan", p5)
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
        err = self.fails("split", src, "--plan", plan, "--out-md", out_md)
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
        err = self.fails("split", src, "--plan", plan, "--out-srt-dir", out_dir)
        self.assertIn("phụ đề từng file con cần SRT/VTT thường", err)


TURNS_TXT = """Kinh Dịch Buổi 99 - YouTube

[00:00] Alo chào cả lớp nhé. >> Dạ chào thầy ạ. >> Em chào cả lớp.
[05:00] >> Hôm nay thầy giảng về âm dương. >> Vâng ạ.
[15:00] Khái niệm thứ nhất là âm dương đối đãi.
[30:00] Nghỉ giải lao năm phút nhé.
[35:30] >> Chúng ta tiếp tục phần hai.
[45:00] Phần hai là quẻ càn.
"""

TURNS_PLAN = """
00:00:00 | CUT  | Đầu giờ  | | Chào hỏi trước giờ học
00:05:00 | KEEP | P1       | Khởi Động | Mở bài
00:30:00 | CUT  | Giải lao | | Nghỉ giữa giờ
00:35:30 | KEEP | P2       | Chuyên Đề | Thân bài
00:50:00 | END
"""


class TestSplitCourseStyle(Base):
    def split_course(self, *extra):
        src = self.path("Buổi 99.txt", TURNS_TXT)
        plan = self.path("plan.txt", TURNS_PLAN)
        out_md = self.path("Buổi 99.md")
        self.ok("split", src, "--plan", plan, "--prefix", "Buổi 99", "--out-md", out_md, "--style", "khoa", *extra)
        return src, plan, self.read("Buổi 99.md")

    def test_moc_in_dam_va_moi_luot_mot_dong(self):
        _, _, md = self.split_course()
        self.assertIn("**[00:00]** Alo chào cả lớp nhé.\n\n> 🗣️ Dạ chào thầy ạ.\n\n> 🗣️ Em chào cả lớp.\n", md)
        self.assertIn("**[05:00]** > 🗣️ Hôm nay thầy giảng về âm dương.\n\n> 🗣️ Vâng ạ.\n", md)
        self.assertIn("**[15:00]** Khái niệm thứ nhất là âm dương đối đãi.\n", md)
        self.assertNotIn(">>", md)

    def test_cut_la_warning_va_co_muc_luc_abstract(self):
        _, _, md = self.split_course()
        self.assertIn("### 🛑 [00:00:00 - 00:04:59] ĐẦU GIỜ: CHÀO HỎI TRƯỚC GIỜ HỌC (EDITOR: CẮT BỎ TOÀN BỘ)", md)
        self.assertIn("> [!WARNING] Lệnh Editor: CẮT BỎ (CUT)\n> Chào hỏi trước giờ học\n", md)
        self.assertNotIn("[!CAUTION]-", md)
        self.assertIn("> [!ABSTRACT] Mục lục 2 file con", md)
        self.assertIn("> • **🛑 [00:00:00 - 00:04:59]:** Đầu giờ: Chào hỏi trước giờ học *(LỆNH: CẮT BỎ TOÀN BỘ)*", md)
        self.assertIn("> 1. **Buổi 99:P1 [05:00 - 29:59]:** Khởi Động", md)
        self.assertIn("> 2. **Buổi 99:P2 [35:30 - 49:59]:** Chuyên Đề", md)
        self.assertIn("### 🎬 Buổi 99:P1 [05:00 - 29:59] Khởi Động\n\n> [!NOTE] Lệnh Editor: GIỮ LẠI (KEEP)", md)
        self.assertIn("## 📖 Toàn văn phụ đề / Transcript chi tiết", md)
        # toàn văn phần CUT vẫn có, không thu gọn (editor đối chiếu được)
        self.assertIn("**[30:00]** Nghỉ giải lao năm phút nhé.", md)

    def test_dien_xong_thi_lint_0_loi(self):
        src, plan, md = self.split_course()
        filled = self.path("filled.md", re.sub(r"\{\{điền[^}]*\}\}", "Nội dung đã điền", md))
        out = self.ok("lint", filled, "--plan", plan, "--prefix", "Buổi 99", "--source", src)
        self.assertIn("Kết quả: 0 lỗi", out)

    def test_chay_hai_lan_cung_ket_qua_va_mac_dinh_giu_khung_cu(self):
        _, _, md = self.split_course("--no-notes")
        self.assertNotIn("## I. Tổng quan", md)
        src, plan = self.path("Buổi 99.txt"), self.path("plan.txt")
        again = self.path("lan2.md")
        self.ok("split", src, "--plan", plan, "--prefix", "Buổi 99", "--out-md", again, "--style", "khoa", "--no-notes")
        self.assertEqual(self.read("lan2.md"), md)
        old = self.path("cu.md")
        self.ok("split", src, "--plan", plan, "--prefix", "Buổi 99", "--out-md", old)
        self.assertIn("[!CAUTION]-", self.read("cu.md"))


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

> [!invalid_callout] Sai callout

Chỗ này còn {{điền: nội dung}} chưa điền.

Mốc này phút vượt 60: [00:85:20].

### 🎬 Buổi 99:P1 [05:00 - 29:59] Phần 1
### 🎬 Buổi 99:P2 [20:00 - 45:00] Phần Chồng Lấn

> **👤 [A Hỏi - Lan] [30:00]:** Không ai trả lời câu này!

> **🧙‍♂️ [B Hỏi - Thầy] [35:00]:** Câu hỏi Socrates không ai đáp!

```python
unclosed fence
"""
        doc = self.path("bad.md", bad_md)
        err = self.fails("lint", doc)
        self.assertIn("khối code mở bằng ``` chưa đóng", err)
        self.assertIn("callout [!invalid_callout] không phải loại hợp lệ", err)
        self.assertIn("còn chỗ chưa điền", err)
        self.assertIn("mốc 00:85:20 sai", err)
        self.assertIn("chồng lên file con trước", err)
        self.assertIn("[A Hỏi] chưa có [B Đáp] đi kèm", err)


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def make_video(path, seconds, audio_seconds=None, size="160x120", abitrate=None, loud=None):
    """Video giả: hình testsrc `seconds` giây, tiếng sin `audio_seconds` giây (mặc định bằng hình)."""
    a = audio_seconds if audio_seconds is not None else seconds
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
           "testsrc=duration=%s:size=%s:rate=30" % (seconds, size), "-f", "lavfi", "-i",
           "aevalsrc=exprs='0.2*sin(2*PI*440*t)|0.2*sin(2*PI*440*t)':s=44100:d=%s" % a,
           "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if loud:
        cmd += ["-af", "loudnorm=I=%s" % loud]
    cmd += ["-c:a", "aac"] + (["-b:a", abitrate] if abitrate else []) + [path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    return path


class TestProbeAudio(Base):
    def wav(self, name, left, right=None, seconds=4, silence=0):
        """WAV giả: sóng sin biên độ left/right (right None → mono), có thể kèm `silence` giây im lặng ở đầu."""
        p = self.path(name)
        tone = "if(gte(t,%d),%%s*sin(2*PI*440*t),0)" % silence
        expr = tone % left if right is None else "%s|%s" % (tone % left, tone % right)
        res = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                              "aevalsrc=exprs='%s':s=44100:d=%d" % (expr, seconds + silence), p], capture_output=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return p

    def setUp(self):
        super().setUp()
        if not have_ffmpeg():
            self.skipTest("cần ffmpeg")

    def test_probe_audio_missing_file(self):
        err = self.fails("probe-audio", self.path("not_exist.mp4"))
        self.assertIn("không tìm thấy file", err)

    def test_chi_nhan_file_tren_may(self):
        err = self.fails("probe-audio", "http://example.com/a.mp4")
        self.assertIn("không tìm thấy file", err)

    def test_sat_nguong_24_lufs_canh_bao(self):
        out = self.ok("probe-audio", self.wav("sat.wav", 0.07, 0.07))
        self.assertRegex(out, r"Độ to tích hợp cả file: -2[345]\.\d LUFS")
        self.assertIn("Cảnh báo:", out)
        self.assertIn("sát ngưỡng", out)

    def test_giu_che_do_khoa_tu_file_con_da_co(self):
        course = os.path.join(self.d, "FINAL")
        os.mkdir(course)
        make_video(os.path.join(course, "Buổi 1_P01 - A.mp4"), 3, abitrate="192k", loud="-16")
        out = self.ok("probe-audio", self.wav("nho.wav", 0.01, 0.01), "--course-dir", course)
        self.assertIn("Chế độ khoá (đoán từ Buổi 1_P01 - A.mp4): master", out)
        self.assertIn("Khuyến nghị: Mode 3 (master)", out)
        out = self.ok("probe-audio", self.wav("ok.wav", 0.2, 0.2), "--course-dir", course)
        self.assertIn("Khuyến nghị: Mode 3 (master)", out)  # giữ chế độ khoá
        self.assertIn("Cảnh báo: số đo buổi này gợi ý copy, khác chế độ khoá master", out)

    def test_file_con_giu_nguyen_tieng_la_che_do_copy(self):
        course = os.path.join(self.d, "FINAL")
        os.mkdir(course)
        make_video(os.path.join(course, "Buổi 1_P01 - A.mp4"), 3, abitrate="128k")
        out = self.ok("probe-audio", self.wav("ok.wav", 0.2, 0.2), "--course-dir", course)
        self.assertIn("Chế độ khoá (đoán từ Buổi 1_P01 - A.mp4): copy", out)
        self.assertIn("Khuyến nghị: Mode 1 (copy)", out)

    def test_ca_file_du_to_can_bang_chon_copy(self):
        out = self.ok("probe-audio", self.wav("ok.wav", 0.2, 0.2))
        self.assertRegex(out, r"Độ to tích hợp cả file: -1\d\.\d LUFS")
        self.assertIn("Lệch kênh (Δ): 0.0 dB", out)
        self.assertIn("Khuyến nghị: Mode 1 (copy)", out)
        self.assertIn("cả khoá", out)

    def test_mau_im_lang_bi_bo_qua_khong_doi_khuyen_nghi(self):
        vid = self.wav("le.wav", 0.2, 0.2, silence=20)
        out = self.ok("probe-audio", vid, "--sample-time", "00:00:02", "--duration", "5")
        self.assertIn("Mẫu 00:00:02 (5 giây)", out)
        self.assertIn("gần im lặng", out)
        self.assertIn("bỏ qua", out)
        self.assertIn("Khuyến nghị: Mode 1 (copy)", out)

    def test_ca_file_nho_duoi_24_lufs_chon_master(self):
        out = self.ok("probe-audio", self.wav("nho.wav", 0.01, 0.01))
        self.assertIn("Khuyến nghị: Mode 3 (master)", out)
        self.assertIn("< -24 LUFS", out)

    def test_lech_kenh_tu_4_db_chon_balance(self):
        out = self.ok("probe-audio", self.wav("lech.wav", 0.2, 0.05))
        self.assertRegex(out, r"Lệch kênh \(Δ\): 1[12]\.\d dB")
        self.assertIn("Khuyến nghị: Mode 2 (balance)", out)

    def test_mono_chon_copy(self):
        out = self.ok("probe-audio", self.wav("mono.wav", 0.2))
        self.assertIn("1 kênh", out)
        self.assertIn("Khuyến nghị: Mode 1 (copy)", out)


PARTS_PLAN = """
00:00:00 | CUT  | Đầu  | | Cắt đầu
00:00:01 | KEEP | P1   | Khởi Động | Đoạn 1
00:00:02 | KEEP | P5.1 | Hỏi Đáp: Vận Số? | Ca 1
00:00:03 | KEEP | P12  | Đối Thoại "Sơn Nhân" / Thủy Trí | Ca 2
00:00:04 | END
"""


class TestCutVideoNames(Base):
    def setUp(self):
        super().setUp()
        if not have_ffmpeg():
            self.skipTest("cần ffmpeg + ffprobe")
        self.vid = make_video(self.path("nguon.mp4"), 5)
        self.plan = self.path("plan.txt", PARTS_PLAN)
        self.out = os.path.join(self.d, "FINAL")

    def cut(self, *extra):
        return run("cut-video", self.vid, "--plan", self.plan, "--prefix", "Buổi 9", "--out-dir", self.out,
                   "--mode", "copy", *extra)

    def touch(self, *names):
        os.makedirs(self.out, exist_ok=True)
        for n in names:
            open(os.path.join(self.out, n), "w").close()

    def test_mau_ten_name_ho_tro_phan_con_va_lam_sach_ky_tu(self):
        res = self.cut("--name", "{prefix}_P{n:02} - {title}", "--dry-run")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("DRY-RUN: Buổi 9_P01 - Khởi Động.mp4", res.stdout)
        self.assertIn("DRY-RUN: Buổi 9_P05.1 - Hỏi Đáp - Vận Số.mp4", res.stdout)
        self.assertIn("DRY-RUN: Buổi 9_P12 - Đối Thoại Sơn Nhân - Thủy Trí.mp4", res.stdout)
        self.assertFalse(os.path.exists(self.out))

    def test_suy_quy_uoc_tu_file_co_san_trong_thu_muc_dich(self):
        self.touch("Buổi 0_P01 - Mở Đầu.mp4", "Buổi 0_P05.1 - Vấn Đáp.mp4", "Buổi 1_P02 - Tiếp.mp4", "ghi-chu.txt")
        res = self.cut("--dry-run")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Mẫu tên: {prefix}_P{n:02} - {title} (suy từ 3 file có sẵn", res.stdout)
        self.assertIn("DRY-RUN: Buổi 9_P01 - Khởi Động.mp4", res.stdout)
        self.assertIn("DRY-RUN: Buổi 9_P05.1 - Hỏi Đáp - Vận Số.mp4", res.stdout)

    def test_thu_muc_trong_giu_ten_mac_dinh_va_lam_sach(self):
        res = self.cut("--dry-run")
        self.assertIn("DRY-RUN: Buổi 9-P1 - Khởi Động.mp4", res.stdout)
        self.assertIn("DRY-RUN: Buổi 9-P5.1 - Hỏi Đáp - Vận Số.mp4", res.stdout)
        self.assertIn("DRY-RUN: Buổi 9-P12 - Đối Thoại Sơn Nhân - Thủy Trí.mp4", res.stdout)

    def test_thu_muc_lan_kieu_lay_dung_kieu_nhieu_nhat(self):
        self.touch("A_P01 - x.mp4", "A_P02 - y.mp4", "B-P1 - z.mp4", "C_P10 - w.mp4")
        res = self.cut("--dry-run")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Mẫu tên: {prefix}_P{n:02} - {title}", res.stdout)
        self.assertIn("Cảnh báo:", res.stdout)

    def test_hai_kieu_ngang_nhau_thi_hoi(self):
        self.touch("A_P01 - x.mp4", "B-P1 - z.mp4")
        res = self.cut("--dry-run")
        self.assertEqual(res.returncode, 1)
        self.assertIn("--name", res.stderr)

    def test_trung_ten_file_co_san_dung_truoc_khi_cat(self):
        self.touch("Buổi 9_P05.1 - Hỏi Đáp - Vận Số.mp4", "Buổi 9_P12 - Đối Thoại Sơn Nhân - Thủy Trí.mp4")
        for extra in (["--dry-run"], []):
            res = self.cut("--name", "{prefix}_P{n:02} - {title}", *extra)
            self.assertEqual(res.returncode, 1)
            self.assertIn("không ghi đè", res.stderr)
            self.assertIn("P05.1", res.stdout + res.stderr)  # liệt kê mọi tên trùng
            self.assertIn("P12", res.stdout + res.stderr)
        self.assertEqual(len(os.listdir(self.out)), 2)

    def test_mau_ten_sai_bi_tu_choi(self):
        for bad in ("{prefix}_{x} - {title}", "{title.__class__}_P{n}", "{prefix} - {title}", "a/P{n} - {title}"):
            res = self.cut("--name", bad, "--dry-run")
            self.assertEqual(res.returncode, 1, bad)
            self.assertIn("--name", res.stderr, bad)


class TestCutVideo(Base):
    def test_cut_video_missing_file(self):
        plan = self.path("plan.txt", "00:00:00 | KEEP | P1 | T | N\n00:00:01 | END\n")
        err = self.fails("cut-video", self.path("not_exist.mp4"), "--plan", plan, "--out-dir", self.path("out"))
        self.assertIn("không tìm thấy file video nguồn", err)

    def test_cut_video_dry_run_and_execution(self):
        if not have_ffmpeg():
            self.skipTest("cần ffmpeg + ffprobe")
        vid = make_video(self.path("sample.mp4"), 4)
        plan = self.path("plan.txt", """
00:00:00 | CUT  | Đầu | | Cắt đầu
00:00:01 | KEEP | P1  | Khởi Động | Đoạn 1
00:00:03 | END
""")
        out_dir = self.path("final_cuts")

        # Dry-run
        out_dry = self.ok("cut-video", vid, "--plan", plan, "--prefix", "Buổi 99",
                          "--out-dir", out_dir, "--dry-run")
        self.assertIn("DRY-RUN: Buổi 99-P1 - Khởi Động.mp4", out_dry)
        self.assertFalse(os.path.exists(out_dir))

        # Thực thi thật: kiểm ffprobe từng file con
        out_real = self.ok("cut-video", vid, "--plan", plan, "--prefix", "Buổi 99",
                           "--out-dir", out_dir, "--mode", "copy")
        self.assertIn("OK: Buổi 99-P1 - Khởi Động.mp4", out_real)
        self.assertIn("Hoàn tất cắt 1 video con", out_real)
        self.assertEqual(os.listdir(out_dir), ["Buổi 99-P1 - Khởi Động.mp4"])  # không để lại file tạm

        # Kiểm tra chống ghi đè
        err_overwrite = self.fails("cut-video", vid, "--plan", plan, "--prefix", "Buổi 99",
                                  "--out-dir", out_dir, "--mode", "copy")
        self.assertIn("đã có", err_overwrite)
        self.assertIn("xoá file hoặc đổi thư mục (không ghi đè)", err_overwrite)

    def test_ke_hoach_dai_hon_video_bi_tu_choi_ca_dry_run(self):
        if not have_ffmpeg():
            self.skipTest("cần ffmpeg + ffprobe")
        vid = make_video(self.path("ngan.mp4"), 2)
        plan = self.path("plan.txt", "00:00:00 | KEEP | P1 | Dài | x\n00:00:30 | KEEP | P2 | Dài Hơn | y\n00:01:00 | END\n")
        out_dir = self.path("out")
        for extra in (["--dry-run"], []):
            res = run("cut-video", vid, "--plan", plan, "--out-dir", out_dir, "--mode", "copy", *extra)
            self.assertEqual(res.returncode, 1)
            self.assertIn("LỖI:", res.stdout)
            self.assertIn("P1", res.stdout)
            self.assertIn("P2", res.stdout)
            self.assertIn("vượt thời lượng video", res.stdout)
        self.assertFalse(os.path.exists(out_dir))

    def test_file_con_hong_khong_giao_duoi_ten_that(self):
        if not have_ffmpeg():
            self.skipTest("cần ffmpeg + ffprobe")
        vid = make_video(self.path("mat-tieng.mp4"), 10, audio_seconds=2)  # tiếng chỉ có 2 giây đầu
        plan = self.path("plan.txt", "00:00:00 | CUT | Đầu | | x\n00:00:05 | KEEP | P1 | Không Tiếng | y\n"
                                     "00:00:07 | END\n")
        out_dir = self.path("out")
        res = run("cut-video", vid, "--plan", plan, "--out-dir", out_dir, "--mode", "balance")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("LỖI:", res.stdout)
        self.assertIn("tiếng", res.stdout)
        self.assertEqual(os.listdir(out_dir), [])


NAMING_PLAN = """
00:00:00 | CUT  | Đầu giờ  | | Mic
00:05:00 | KEEP | P1       | Phần Một: Mở | Khởi đầu
00:30:00 | CUT  | Giải lao | | Nghỉ
00:35:00 | KEEP | P2       | Phần Hai | Tiếp
01:06:00 | END
"""


class TestOneNamingSource(Base):
    """Cột tên file con trong md, file SRT con và video con dùng cùng một mẫu tên."""

    TPL = "{prefix}_P{n:02} - {title}"

    def test_plan_va_split_dung_cung_mau_ten_va_nhan(self):
        src = self.path("bai.srt", SAMPLE_SRT)
        plan = self.path("plan.txt", NAMING_PLAN)
        args = ["--plan", plan, "--prefix", "Buổi 99", "--name", self.TPL, "--label", "{prefix} · P{n:02}"]
        self.ok("plan", src, *args, "--out-md", self.path("sheet.md"), "--out-csv", self.path("sheet.csv"))
        sheet = self.read("sheet.md")
        self.assertIn("**Buổi 99_P01 - Phần Một - Mở**", sheet)
        self.assertIn("Buổi 99 · P01,Buổi 99_P01 - Phần Một - Mở", self.read("sheet.csv"))
        srt_dir = os.path.join(self.d, "srt")
        self.ok("split", src, *args, "--out-srt-dir", srt_dir, "--out-md", self.path("bai.md"), "--style", "khoa")
        self.assertEqual(sorted(os.listdir(srt_dir)), ["Buổi 99_P01 - Phần Một - Mở.srt", "Buổi 99_P02 - Phần Hai.srt"])
        md = self.read("bai.md")
        self.assertIn("### 🎬 Buổi 99 · P01 [05:00 - 29:59] Phần Một: Mở", md)
        self.assertIn("> 1. **Buổi 99 · P01 [05:00 - 29:59]:** Phần Một: Mở", md)
        self.assertNotIn("Buổi 99:P1", md)
        filled = self.path("filled.md", re.sub(r"\{\{điền[^}]*\}\}", "x", md))
        out = self.ok("lint", filled, "--plan", plan, "--prefix", "Buổi 99", "--label", "{prefix} · P{n:02}",
                      "--source", src)
        self.assertIn("Kết quả: 0 lỗi", out)

    def test_split_suy_mau_ten_tu_thu_muc_video(self):
        src = self.path("bai.srt", SAMPLE_SRT)
        plan = self.path("plan.txt", NAMING_PLAN)
        vdir = os.path.join(self.d, "FINAL")
        os.mkdir(vdir)
        open(os.path.join(vdir, "Buổi 0_P01 - Cũ.mp4"), "w").close()
        srt_dir = os.path.join(self.d, "srt")
        out = self.ok("split", src, "--plan", plan, "--prefix", "Buổi 99", "--video-dir", vdir,
                      "--out-srt-dir", srt_dir)
        self.assertIn("Mẫu tên: {prefix}_P{n:02} - {title}", out)
        self.assertIn("Buổi 99_P02 - Phần Hai.srt", os.listdir(srt_dir))

    def test_nhan_sai_bi_tu_choi(self):
        src = self.path("bai.srt", SAMPLE_SRT)
        plan = self.path("plan.txt", NAMING_PLAN)
        for bad in ("{prefix} [P{n}]", "{prefix} | {n}", "{prefix}"):
            err = self.fails("plan", src, "--plan", plan, "--label", bad)
            self.assertIn("--label", err, bad)

    def test_file_nguon_ghi_nguon_ben_vung(self):
        src = self.path("abc.vi.vtt", "WEBVTT\n\n" + SAMPLE_SRT.replace(",", "."))
        plan = self.path("plan.txt", NAMING_PLAN)
        self.ok("split", src, "--plan", plan, "--prefix", "Buổi 99", "--out-md", self.path("b.md"), "--style", "khoa",
                "--source-label", "https://www.youtube.com/watch?v=abc123XYZ_-")
        md = self.read("b.md")
        self.assertIn("**File nguồn:** `https://www.youtube.com/watch?v=abc123XYZ_-`", md)
        self.assertNotIn("abc.vi.vtt", md)


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
