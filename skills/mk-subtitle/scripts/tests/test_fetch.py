"""Tests for `subtitle.py fetch` (tải phụ đề YouTube bằng yt-dlp). Không gọi mạng: yt-dlp giả đặt đầu PATH, đọc kịch bản
từ biến môi trường FAKE_YT (JSON): ngôn ngữ nói + tiêu đề (cho --print), phụ đề tải lên / tự động có sẵn, lỗi.
Run: python3 -m unittest discover -s skills/mk-subtitle/scripts/tests"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "subtitle.py")
VID = "abc123XYZ_-"
URL = "https://www.youtube.com/watch?v=" + VID

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
sc = json.loads(os.environ.get("FAKE_YT", "{}"))
a = sys.argv[1:]
if "--help" in a:  # dò tuỳ chọn, không ghi log
    print("  --ignore-config\n" + ("  --no-plugin-dirs\n" if sc.get("plugin_dirs") else "")); sys.exit(0)
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps(a) + "\n")
if sc.get("error"):
    sys.stderr.write("ERROR: " + sc["error"] + "\n"); sys.exit(1)
if "--print" in a:
    print("%s\t%s" % (sc.get("spoken", "vi"), sc.get("title", "Bài giảng thử"))); sys.exit(0)
out = a[a.index("-o") + 1]
want = a[a.index("--sub-langs") + 1]
if want in sc.get("auto" if "--write-auto-subs" in a else "manual", []):
    body = sc.get("body", "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nchào cả lớp\n")
    with open(out.replace("%(id)s", "abc123XYZ_-").replace("%(ext)s", want + ".vtt"), "w") as fh:
        fh.write(body)
'''

# VTT tự động kiểu YouTube (giả): có mốc từng từ
AUTO_BODY = ("WEBVTT\nKind: captions\nLanguage: vi\n\n00:00:00.500 --> 00:00:03.000 align:start position:0%\n \n"
             "hôm<00:00:01.000><c> nay</c><00:00:01.400><c> học</c><00:00:01.800><c> quẻ</c><00:00:02.200><c> càn</c>\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.bin = os.path.join(self.d, "bin")
        os.mkdir(self.bin)
        fake = os.path.join(self.bin, "yt-dlp")
        with open(fake, "w") as fh:
            fh.write(FAKE)
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.d, "calls.log")
        self.out = os.path.join(self.d, "phu-de")

    def run_fetch(self, scenario, *extra, url=URL, path=None):
        env = dict(os.environ, FAKE_YT=json.dumps(scenario), FAKE_LOG=self.log,
                   PATH=path if path is not None else self.bin + os.pathsep + os.environ.get("PATH", ""))
        return subprocess.run([sys.executable, SCRIPT, "fetch", url, "--out-dir", self.out] + list(extra),
                              capture_output=True, text=True, env=env)

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as fh:
            return [json.loads(l) for l in fh]

    def downloads(self):
        return [c for c in self.calls() if "--print" not in c]


class TestFetch(Base):
    def test_uu_tien_phu_de_chu_kenh_tai_len(self):
        res = self.run_fetch({"manual": ["vi"], "auto": ["vi-orig"]})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Video: Bài giảng thử · ngôn ngữ nói: vi", res.stdout)
        self.assertIn("phụ đề chủ kênh tải lên (vi)", res.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.out, VID + ".vi.vtt")))
        self.assertFalse(any("--write-auto-subs" in c for c in self.calls()))  # có bản tải lên thì không tải bản tự động

    def test_khong_co_ban_tai_len_thi_lay_tu_dong_goc_co_moc_tung_tu(self):
        res = self.run_fetch({"auto": ["vi-orig"], "body": AUTO_BODY}, "--name", "buoi-2")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("phụ đề tự động YouTube (vi-orig)", res.stdout)
        self.assertIn("có mốc từng từ", res.stdout)
        self.assertIn("có thể đã lược bớt à, ừ", res.stdout)
        with open(os.path.join(self.out, "buoi-2.vi.vtt"), encoding="utf-8") as fh:
            self.assertIn("<c> càn</c>", fh.read())

    def test_khong_lay_ban_tu_dong_khong_phai_ban_goc(self):
        # chủ kênh không khai ngôn ngữ; YouTube chỉ có "vi" tự động (dịch máy), không có "vi-orig"
        res = self.run_fetch({"spoken": "NA", "auto": ["vi"]})
        self.assertEqual(res.returncode, 1)
        self.assertIn("vi-orig", res.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_video_noi_tieng_khac_chan_ban_dich_truoc_khi_tai(self):
        res = self.run_fetch({"spoken": "en", "manual": ["vi"], "auto": ["en-orig"]})
        self.assertEqual(res.returncode, 1)
        self.assertIn("bản dịch", res.stderr)
        self.assertIn("--lang en", res.stderr)
        self.assertEqual(self.downloads(), [])

    def test_cho_phep_ban_dich_thi_tai_va_ghi_ro(self):
        res = self.run_fetch({"spoken": "en", "manual": ["vi"]}, "--allow-translation")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("BẢN DỊCH", res.stdout)
        self.assertFalse(any("--write-auto-subs" in c for c in self.calls()))  # bản tự động "vi" là dịch máy

    def test_kind_manual_thieu_thi_goi_y_dung(self):
        res = self.run_fetch({"auto": ["vi-orig"]}, "--kind", "manual")
        self.assertEqual(res.returncode, 1)
        self.assertIn("bỏ --kind manual", res.stderr)

    def test_khong_tai_video_va_dung_link_chuan(self):
        self.run_fetch({"auto": ["vi-orig"]}, url="youtu.be/%s?si=chiase" % VID)  # thiếu https, có tham số chia sẻ
        self.assertTrue(self.calls())
        for call in self.calls():
            self.assertIn("--skip-download", call)
            self.assertEqual(call[-2:], ["--", URL])  # link chuẩn, luôn sau "--": không bị hiểu thành tuỳ chọn

    def test_link_playlist_kenh_va_trang_khac_bi_tu_choi(self):
        for bad in ("https://www.youtube.com/playlist?list=PL123", "https://www.youtube.com/@kenh-bai-giang",
                    "https://example.com/watch?v=" + VID, "https://youtube.com.evil.com/watch?v=" + VID):
            res = self.run_fetch({}, url=bad)
            self.assertEqual(res.returncode, 1, bad)
        self.assertEqual(self.calls(), [])

    def test_khong_ghi_de_va_tu_choi_truoc_khi_goi_mang(self):
        os.makedirs(self.out)
        for name in ("buoi-2", VID):
            with open(os.path.join(self.out, name + ".vi.vtt"), "w") as fh:
                fh.write("cũ")
        for extra in (["--name", "buoi-2"], []):
            res = self.run_fetch({"auto": ["vi-orig"]}, *extra)
            self.assertEqual(res.returncode, 1)
            self.assertIn("không ghi đè", res.stderr)
        self.assertEqual(self.calls(), [])
        with open(os.path.join(self.out, "buoi-2.vi.vtt")) as fh:
            self.assertEqual(fh.read(), "cũ")

    def test_video_rieng_tu_goi_y_cookies(self):
        res = self.run_fetch({"error": "Private video. Sign in if you've been granted access to this video"})
        self.assertEqual(res.returncode, 1)
        self.assertIn("--cookies-from-browser", res.stderr)

    def test_thieu_yt_dlp_huong_dan_cai(self):
        res = self.run_fetch({}, path=os.path.join(self.d, "trong"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("brew install yt-dlp", res.stderr)

    def test_bo_qua_config_va_plugin_cuc_bo(self):
        res = self.run_fetch({"auto": ["vi-orig"]})
        self.assertEqual(res.returncode, 0, res.stderr)
        for call in self.calls():
            self.assertEqual(call[0], "--ignore-config")
            self.assertNotIn("--no-plugin-dirs", call)  # bản yt-dlp này không có tuỳ chọn đó
        os.remove(self.log)
        shutil.rmtree(self.out)
        res = self.run_fetch({"auto": ["vi-orig"], "plugin_dirs": True})
        self.assertEqual(res.returncode, 0, res.stderr)
        for call in self.calls():
            self.assertEqual(call[:2], ["--ignore-config", "--no-plugin-dirs"])


class TestVideoFile(Base):
    def test_dua_nham_file_video_vao_scan(self):
        vid = os.path.join(self.d, "bai-giang.mp4")
        with open(vid, "wb") as fh:
            fh.write(b"\x00\x00\x00\x18ftypmp42\xad\xde")
        res = subprocess.run([sys.executable, SCRIPT, "scan", vid], capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)
        self.assertIn("là file video/âm thanh", res.stderr)
        self.assertIn("lay-phu-de.md", res.stderr)


if __name__ == "__main__":
    unittest.main()
