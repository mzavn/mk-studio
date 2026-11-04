"""Tests for `subtitle.py fetch-video` (tải video YouTube theo chuẩn khoá bằng yt-dlp, rồi ffprobe so với video mẫu).
Không gọi mạng: yt-dlp giả đặt đầu PATH, ghi lại tham số và chép file video giả (FAKE_SRC) vào đường dẫn `-o`.
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
import json, os, shutil, sys
a = sys.argv[1:]
if "--help" in a:  # dò tuỳ chọn, không ghi log
    print("  --ignore-config\n" + ("  --no-plugin-dirs\n" if os.environ.get("FAKE_PLUGIN_DIRS") else "")); sys.exit(0)
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps(a) + "\n")
err = os.environ.get("FAKE_ERROR")
if err:
    out = a[a.index("-o") + 1].replace("%(ext)s", "f136.mp4.part")
    open(out, "w").close()  # file dở của yt-dlp
    sys.stderr.write("ERROR: " + err + "\n"); sys.exit(1)
out = a[a.index("-o") + 1].replace("%(ext)s", "mp4")
shutil.copyfile(os.environ["FAKE_SRC"], out)
'''

DEFAULT_FORMAT = "136+140/bv*[height=720][vcodec^=avc1]+ba[ext=m4a]"
DEFAULT_CLIENT = "youtube:player_client=web_embedded,default,-android_vr"


def make_video(path, size="320x240", rate=30):
    res = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                          "testsrc=duration=1:size=%s:rate=%d" % (size, rate), "-f", "lavfi", "-i",
                          "sine=frequency=440:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                          "-shortest", path], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    return path


class Base(unittest.TestCase):
    def setUp(self):
        if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            self.skipTest("cần ffmpeg + ffprobe")
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.bin = os.path.join(self.d, "bin")
        os.mkdir(self.bin)
        fake = os.path.join(self.bin, "yt-dlp")
        with open(fake, "w") as fh:
            fh.write(FAKE)
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.d, "calls.log")
        self.src = make_video(os.path.join(self.d, "nguon-gia.mp4"))
        self.out_dir = os.path.join(self.d, "VIDEO")
        self.out = os.path.join(self.out_dir, "Buổi 9.mp4")

    def run_fetch(self, *extra, url=URL, error=None):
        env = dict(os.environ, FAKE_LOG=self.log, FAKE_SRC=self.src,
                   PATH=self.bin + os.pathsep + os.environ.get("PATH", ""))
        env.pop("FAKE_ERROR", None)
        if error:
            env["FAKE_ERROR"] = error
        return subprocess.run([sys.executable, SCRIPT, "fetch-video", url, "--out", self.out] + list(extra),
                              capture_output=True, text=True, env=env)

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as fh:
            return [json.loads(l) for l in fh]


class TestFetchVideo(Base):
    def test_tai_theo_chuan_khoa_mac_dinh(self):
        res = self.run_fetch()
        self.assertEqual(res.returncode, 0, res.stderr)
        (call,) = self.calls()
        self.assertEqual(call[0], "--ignore-config")
        self.assertNotIn("--no-plugin-dirs", call)
        self.assertEqual(call[call.index("--extractor-args") + 1], DEFAULT_CLIENT)
        self.assertEqual(call[call.index("-f") + 1], DEFAULT_FORMAT)
        self.assertIn("--no-overwrites", call)
        self.assertEqual(call[call.index("--merge-output-format") + 1], "mp4")
        self.assertIn("--no-playlist", call)
        self.assertEqual(call[-2:], ["--", URL])
        self.assertTrue(os.path.isfile(self.out))
        self.assertIn("320×240 · 30 khung/giây · h264 + aac", res.stdout)
        self.assertIn("→ %s" % self.out, res.stdout)
        self.assertEqual(os.listdir(self.out_dir), ["Buổi 9.mp4"])  # không để lại thư mục tạm

    def test_doi_dinh_dang_va_client(self):
        res = self.run_fetch("--format", "22/best", "--player-client", "web")
        self.assertEqual(res.returncode, 0, res.stderr)
        (call,) = self.calls()
        self.assertEqual(call[call.index("-f") + 1], "22/best")
        self.assertEqual(call[call.index("--extractor-args") + 1], "youtube:player_client=web")

    def test_khop_video_mau(self):
        ref = make_video(os.path.join(self.d, "buoi-truoc.mp4"))
        res = self.run_fetch("--ref", ref)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Khớp video mẫu", res.stdout)

    def test_lech_video_mau_bao_loi_va_giu_file(self):
        ref = make_video(os.path.join(self.d, "buoi-truoc.mp4"), size="640x360", rate=25)
        res = self.run_fetch("--ref", ref)
        self.assertEqual(res.returncode, 1)
        self.assertIn("LỆCH: độ phân giải 320×240 ≠ 640×360", res.stdout)
        self.assertIn("LỆCH: khung/giây 30 ≠ 25", res.stdout)
        self.assertTrue(os.path.isfile(self.out))

    def test_khong_ghi_de_va_tu_choi_truoc_khi_goi_mang(self):
        os.makedirs(self.out_dir)
        with open(self.out, "w") as fh:
            fh.write("cũ")
        res = self.run_fetch()
        self.assertEqual(res.returncode, 1)
        self.assertIn("không ghi đè", res.stderr)
        self.assertEqual(self.calls(), [])
        with open(self.out) as fh:
            self.assertEqual(fh.read(), "cũ")

    def test_ban_yt_dlp_co_no_plugin_dirs_thi_dung(self):
        os.environ["FAKE_PLUGIN_DIRS"] = "1"
        self.addCleanup(os.environ.pop, "FAKE_PLUGIN_DIRS", None)
        res = self.run_fetch()
        self.assertEqual(res.returncode, 0, res.stderr)
        (call,) = self.calls()
        self.assertEqual(call[:2], ["--ignore-config", "--no-plugin-dirs"])

    def test_dich_la_symlink_bi_tu_choi(self):
        os.makedirs(self.out_dir)
        os.symlink(os.path.join(self.d, "khac.mp4"), self.out)
        res = self.run_fetch()
        self.assertEqual(res.returncode, 1)
        self.assertEqual(self.calls(), [])

    def test_link_khong_phai_youtube_bi_tu_choi(self):
        for bad in ("https://example.com/watch?v=" + VID, "https://www.youtube.com/playlist?list=PL1"):
            res = self.run_fetch(url=bad)
            self.assertEqual(res.returncode, 1, bad)
            self.assertIn("fetch-video", res.stderr)
        self.assertEqual(self.calls(), [])

    def test_video_mau_khong_co_thi_dung_truoc_khi_tai(self):
        res = self.run_fetch("--ref", os.path.join(self.d, "khong-co.mp4"))
        self.assertEqual(res.returncode, 1)
        self.assertEqual(self.calls(), [])

    def test_loi_403_khong_de_file_do(self):
        res = self.run_fetch(error="unable to download video data: HTTP Error 403: Forbidden")
        self.assertEqual(res.returncode, 1)
        self.assertIn("403", res.stderr)
        self.assertIn("--player-client", res.stderr)
        self.assertFalse(os.path.lexists(self.out))
        self.assertEqual(os.listdir(self.out_dir), [])

    def test_duoi_khong_phai_mp4_bi_tu_choi(self):
        self.out = os.path.join(self.out_dir, "Buổi 9.mkv")
        res = self.run_fetch()
        self.assertEqual(res.returncode, 1)
        self.assertIn(".mp4", res.stderr)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
