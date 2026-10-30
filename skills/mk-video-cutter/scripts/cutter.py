#!/usr/bin/env python3
"""Cắt nhỏ video bài giảng dài theo Action Sheet: viền thừa, khung hình, độ phân giải, cân bằng âm thanh.

  cutter.py probe VIDEO [--sample-time 00:15:00] [--duration 30]
  cutter.py frame VIDEO [--sheet SHEET [--prefix P] [--only P1,P3]] [--samples 12] [--preview DIR]
                        [--crop auto|none|W:H:X:Y] [--aspect 16:9|9:16|W:H|source] [--res auto|1080|source]
                        [--size WxH] [--fit pad|fill|blur] [--enhance]
  cutter.py parse SHEET [--prefix "Buổi 1"]
  cutter.py cut VIDEO --sheet SHEET --out-dir DIR [--prefix "Buổi 1"] [--only …] [--mode auto|copy|balance|master]
                      [--crop none|auto|W:H:X:Y] [--aspect …] [--res …] [--size WxH] [--fit pad|fill|blur]
                      [--enhance] [--encoder x264|videotoolbox] [--crf 18] [--dry-run]
  cutter.py verify DIR [--sheet SHEET [--prefix P]] [--expect-size WxH]

Không có --crop/--aspect/--res/--size/--enhance → hình giữ nguyên (stream copy). Có một trong số đó → hình được mã hoá
lại (x264 CRF 18 mặc định). --fit pad (mặc định) giữ toàn bộ nội dung, thêm nền đen cho vừa khung. --res auto chọn chuẩn
cao nhất mà nội dung không phải phóng quá 1,8×; --enhance khử khối nén + nhiễu và làm nét vừa phải.
Thoát: 0 xong; 1 lỗi đầu vào/ffmpeg hoặc verify có clip lỗi. Chỉ thư viện chuẩn Python; cần ffmpeg/ffprobe trong PATH.
"""
import argparse
import shlex
import csv
import json
import os
import math
import re
import shutil
import subprocess
import sys
import unicodedata

sys.dont_write_bytecode = True

HMS = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")
FORBIDDEN = re.compile(r'[\\/:*?"<>|]')


def die(msg):
    print("Lỗi: " + msg, file=sys.stderr)
    sys.exit(1)


def utf8_stdio():
    """Windows ghi ra pipe bằng bảng mã hệ thống (cp1252…) → chữ Việt làm script dừng. Ép UTF-8 cho stdout/stderr."""
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")


def read_text(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return unicodedata.normalize("NFC", fh.read().replace("\r\n", "\n").replace("\r", "\n"))
    except (OSError, UnicodeDecodeError) as exc:
        die("không đọc được %s: %s" % (path, exc))


def hms_ms(text):
    text = text.strip()
    m = HMS.match(text)
    if not m:
        return None
    h, mi, s = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
    if (m.group(1) and mi >= 60) or s >= 60:
        return None
    return ((h * 60 + mi) * 60 + s) * 1000


def long_(ms):
    s = ms // 1000
    return "%02d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60)


def dur(ms):
    s = ms // 1000
    return "%dp %02ds" % (s // 60, s % 60)


def safe_filename(name):
    clean = FORBIDDEN.sub("-", name).replace(":", "-")
    return re.sub(r"\s+", " ", clean).strip(" .")


def refuse(*paths):
    for p in paths:
        if p and os.path.lexists(p):
            die("%s đã có — xoá file hoặc đổi tên (không ghi đè)" % p)


def check_tools(*names):
    for name in names:
        if not shutil.which(name):
            die("cần công cụ '%s' trong PATH để thực hiện thao tác — cài ffmpeg: brew install ffmpeg (macOS), "
                "winget install Gyan.FFmpeg (Windows), rồi mở lại terminal" % name)


# ---------------------------------------------------------------- Bóc tách Action Sheet

def parse_plan_text(text, prefix=""):
    segs, end = [], None
    for n, row in enumerate(text.split("\n"), 1):
        line = row.strip()
        if not line or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.split("|")]
        t = hms_ms(cells[0])
        if t is None:
            continue
        cmd = cells[1].upper() if len(cells) > 1 else ""
        if cmd == "END":
            end = t
            continue
        if cmd not in ("CUT", "KEEP"):
            continue
        code = cells[2] if len(cells) > 2 else ""
        title = cells[3] if len(cells) > 3 else ""
        note = cells[4] if len(cells) > 4 else ""
        label = "%s:%s" % (prefix, code) if prefix else code
        segs.append({
            "n": n, "start": t, "cmd": cmd, "code": code,
            "title": title, "note": note, "label": label
        })
    for i, s in enumerate(segs):
        s["end"] = segs[i + 1]["start"] if i + 1 < len(segs) else end

    keep = []
    for s in segs:
        if s["cmd"] == "KEEP":
            name = safe_filename("%s - %s" % (s["label"], s["title"])) if s["title"] else safe_filename(s["label"])
            s["out_name"] = name + ".mp4"
            keep.append(s)
    return keep, end


def parse_markdown_table(text, prefix=""):
    rows = text.split("\n")
    keep, prev = [], None
    for line in rows:
        line = line.strip()
        if not line.startswith("|") or "GIỮ LẠI (KEEP)" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        code = cells[0].replace("*", "").strip()
        span_str = cells[1].replace("`", "").strip()
        name_str = cells[4].replace("*", "").strip()
        
        span_m = re.findall(r"(\d{1,2}:\d{2}(?::\d{2})?)", span_str)
        if len(span_m) >= 2:
            st_ms = hms_ms(span_m[0])
            en_ms = hms_ms(span_m[1])
            if st_ms is not None and en_ms is not None:
                # Nếu timecode kết thúc bằng :59 (viết dạng bao hàm), làm tròn lên giây kế tiếp cho điểm cắt
                if span_m[1].endswith(":59"):
                    en_ms += 1000
                label = "%s:%s" % (prefix, code) if prefix and not name_str.startswith(prefix) else code
                title = name_str
                fname = safe_filename(name_str)
                keep.append({
                    "start": st_ms, "end": en_ms, "cmd": "KEEP",
                    "code": code, "label": label, "title": title,
                    "out_name": fname + ".mp4"
                })
    return keep, None


def parse_csv_file(text):
    keep = []
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        cmd = row.get("lenh", "").upper()
        if cmd != "KEEP":
            continue
        st_ms = hms_ms(row.get("bat_dau", ""))
        en_str = row.get("ket_thuc", "").strip()
        en_ms = hms_ms(en_str)
        if st_ms is None or en_ms is None:
            continue
        if en_str.endswith(":59"):
            en_ms += 1000
        fname = row.get("ten_file") or ("%s - %s" % (row.get("nhan", ""), row.get("tieu_de", "")))
        fname = safe_filename(fname)
        keep.append({
            "start": st_ms, "end": en_ms, "cmd": "KEEP",
            "code": row.get("ma", ""), "label": row.get("nhan", ""),
            "title": row.get("tieu_de", ""), "out_name": fname + ".mp4"
        })
    return keep, None


def parse_sheet_auto(path, prefix=""):
    text = read_text(path)
    if "stt,lenh" in text or "bat_dau,ket_thuc" in text:
        keep, end = parse_csv_file(text)
    elif "### ⏱️" in text or "| Phân đoạn |" in text or "GIỮ LẠI (KEEP)" in text:
        keep, end = parse_markdown_table(text, prefix)
    else:
        keep, end = parse_plan_text(text, prefix)
    
    if not keep:
        die("không tìm thấy phân đoạn KEEP hợp lệ nào trong %s" % path)
    for s in keep:
        if s.get("end") is None:
            die("phân đoạn %s thiếu mốc kết thúc (cần mốc END trong kế hoạch)" % s["code"])
        if s["end"] <= s["start"]:
            die("phân đoạn %s có mốc kết thúc không sau mốc bắt đầu" % s["code"])
    return keep


# ---------------------------------------------------------------- Khảo sát (Probe)

def probe_metadata(video):
    check_tools("ffprobe")
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=index,codec_name,codec_type,width,height",
        "-of", "json", video
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        die("không đọc được thông số video từ %s: %s" % (video, res.stderr))
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        die("lỗi phân tích dữ liệu ffprobe từ %s" % video)
    return data


def probe_audio(video, sample_time="00:15:00", duration=30):
    check_tools("ffmpeg")
    cmd = [
        "ffmpeg", "-hide_banner", "-ss", sample_time, "-t", str(duration),
        "-i", video, "-af", "astats=metadata=1:reset=1", "-f", "null", "-"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = res.stderr

    ch1_m = re.search(r"Channel:\s*1.*?RMS level dB:\s*([-\d.inf]+)", out, re.S | re.I)
    ch2_m = re.search(r"Channel:\s*2.*?RMS level dB:\s*([-\d.inf]+)", out, re.S | re.I)
    overall_m = re.search(r"Overall.*?RMS level dB:\s*([-\d.inf]+)", out, re.S | re.I)

    # Nếu tua quá thời lượng video, thử lại từ 00:00:00
    if not ch1_m and not overall_m and sample_time != "00:00:00":
        sample_time = "00:00:00"
        cmd = [
            "ffmpeg", "-hide_banner", "-ss", sample_time, "-t", str(duration),
            "-i", video, "-af", "astats=metadata=1:reset=1", "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = res.stderr
        ch1_m = re.search(r"Channel:\s*1.*?RMS level dB:\s*([-\d.inf]+)", out, re.S | re.I)
        ch2_m = re.search(r"Channel:\s*2.*?RMS level dB:\s*([-\d.inf]+)", out, re.S | re.I)
        overall_m = re.search(r"Overall.*?RMS level dB:\s*([-\d.inf]+)", out, re.S | re.I)

    def parse_db(m):
        if not m:
            return None
        val = m.group(1).strip()
        if "inf" in val:
            return float("-inf")
        try:
            return float(val)
        except ValueError:
            return None

    ch1 = parse_db(ch1_m)
    ch2 = parse_db(ch2_m)
    overall = parse_db(overall_m)

    if ch1 is None and overall is None:
        die("không đọc được thông số âm thanh từ %s (file không có luồng audio hoặc định dạng không hỗ trợ)" % video)

    if ch1 is not None and ch2 is not None:
        delta = abs(ch1 - ch2)
        avg = overall if overall is not None else (ch1 + ch2) / 2.0
        single_ear = (ch1 < -55.0 and ch2 > -45.0) or (ch2 < -55.0 and ch1 > -45.0)
        imbalanced = delta >= 4.0 or single_ear
    else:
        delta = 0.0
        avg = overall if overall is not None else (ch1 if ch1 is not None else -30.0)
        single_ear = False
        imbalanced = False

    is_quiet = avg < -24.0

    if is_quiet:
        rec_mode = "master"
    elif imbalanced:
        rec_mode = "balance"
    else:
        rec_mode = "copy"

    return {
        "sample_time": sample_time, "duration": duration,
        "ch1": ch1, "ch2": ch2, "delta": delta, "overall": avg,
        "single_ear": single_ear, "imbalanced": imbalanced, "quiet": is_quiet,
        "mode": rec_mode
    }


# ---------------------------------------------------------------- Khung hình (viền thừa, tỉ lệ, độ phân giải)

ACTIVE_DELTA = 12      # một điểm ảnh "có chuyển động" khi độ sáng giữa các mẫu chênh hơn mức này (0–255)
ACTIVE_ROW = 0.5       # hàng/cột thuộc nội dung khi ≥ 50% điểm ảnh của nó có chuyển động
MAX_BAND = 0.3         # viền mỗi phía tối đa 30% kích thước, quá mức → không kết luận


def video_info(video):
    check_tools("ffprobe")
    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", video],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        data = json.loads(res.stdout)
        st = data["streams"][0]
        return int(st["width"]), int(st["height"]), int(float(data["format"]["duration"]) * 1000)
    except (ValueError, KeyError, IndexError):
        die("không đọc được khung hình từ %s" % video)


def even(n):
    return max(2, int(n) // 2 * 2)


def short_tc(ms):
    s = ms // 1000
    return "%d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60) if s >= 3600 else "%02d:%02d" % (s // 60, s % 60)


def segment_of(keep, t):
    for s in keep or []:
        if s["start"] <= t < s["end"]:
            return s["code"]
    return "?"


def select_only(keep, only):
    """--only "P1,P5.2" → chỉ giữ các đoạn KEEP có mã đó; mã không có → lỗi (không lặng lẽ bỏ qua)."""
    if not only:
        return keep
    want = [c.strip() for c in only.split(",") if c.strip()]
    if not want:
        die("--only cần ít nhất một mã đoạn KEEP, vd --only P1,P3")
    missing = [c for c in want if c not in {s["code"] for s in keep}]
    if missing:
        die("--only: không có đoạn KEEP mã %s (có: %s)" % (", ".join(missing), ", ".join(s["code"] for s in keep)))
    return [s for s in keep if s["code"] in want]


def sample_times(dur_ms, keep, n):
    """Mốc lấy mẫu đều nhau (ms); có sheet → chỉ lấy trong các đoạn KEEP, chừa 2 giây hai đầu."""
    if keep:
        spans = [(s["start"] + 2000, s["end"] - 2000) for s in keep if s["end"] - s["start"] > 4000]
        spans = [(a, min(b, dur_ms - 500)) for a, b in spans if a < dur_ms - 500]
        total = sum(b - a for a, b in spans)
        if total > 0:
            out = []
            for k in range(n):
                pos = total * (2 * k + 1) // (2 * n)
                for a, b in spans:
                    if pos < b - a:
                        out.append(a + pos)
                        break
                    pos -= b - a
            return out
    return [dur_ms * (10 + 180 * k // max(1, n - 1)) // 200 if n > 1 else dur_ms // 2 for k in range(n)]


def grab_gray(video, t_ms, aw, ah):
    res = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % (t_ms / 1000), "-i", video, "-frames:v", "1",
                          "-vf", "scale=%d:%d,format=gray" % (aw, ah), "-f", "rawvideo", "-"], capture_output=True)
    return res.stdout if len(res.stdout) == aw * ah else None


def first_run(profile, need):
    for i in range(len(profile) - need + 1):
        if all(v >= ACTIVE_ROW for v in profile[i:i + need]):
            return i
    return None


def snap_out(band, size, profiles):
    """Mép nội dung tĩnh (vd giá sách đứng yên) bị tính nhầm là viền → dời mép RA NGOÀI tới đường biên sáng/tối rõ
    nhất và ổn định qua các mẫu (biên thanh công cụ), trong phạm vi 4% kích thước. Chỉ dời ra ngoài: không mất nội dung."""
    best, best_e = band, 0.0
    for y in range(max(1, band - max(3, size * 4 // 100)), band + 1):
        e = sum(abs(p[y] - p[y - 1]) for p in profiles) / len(profiles)
        if e > best_e:
            best, best_e = y, e
    return best if best_e >= 6 else band


def detect_content(video, w, h, times):
    """Khung nội dung = vùng có chuyển động qua các mẫu; viền tĩnh (thanh menu, thanh công cụ Zoom, dải đen) bị loại.
    Khung là hợp của mọi bố cục nên không mất nội dung; mẫu nào còn dải đen sát mép khung = bố cục đổi.
    → (rect dict | None, lý do, [mốc mẫu còn dải đen], [mốc mọi mẫu đọc được])."""
    aw = min(640, w) // 2 * 2
    ah = even(round(h * aw / w))
    pairs = [(t, f) for t, f in ((t, grab_gray(video, t, aw, ah)) for t in times) if f]
    frames = [f for _, f in pairs]
    used = [t for t, _ in pairs]
    if len(frames) < 4:
        return None, "chỉ đọc được %d khung mẫu (cần ≥ 4)" % len(frames), [], used
    hi, lo = bytearray(frames[0]), bytearray(frames[0])
    for f in frames[1:]:
        hi = bytearray(map(max, hi, f))
        lo = bytearray(map(min, lo, f))
    act = [a - b > ACTIVE_DELTA for a, b in zip(hi, lo)]
    rows = [sum(act[y * aw:(y + 1) * aw]) / aw for y in range(ah)]
    cols = [sum(act[x::aw]) / ah for x in range(aw)]
    top, bottom = first_run(rows, max(2, ah // 50)), first_run(rows[::-1], max(2, ah // 50))
    left, right = first_run(cols, max(2, aw // 50)), first_run(cols[::-1], max(2, aw // 50))
    if None in (top, bottom, left, right):
        if sum(act) > 0.01 * len(act):
            return None, ("vùng chuyển động quá nhỏ hoặc rời rạc (không hàng/cột nào ≥ %d%% chuyển động) — xem ảnh "
                          "mẫu, tự nhập --crop" % (ACTIVE_ROW * 100)), [], used
        return None, "hình gần như đứng yên qua %d mẫu — không đủ chuyển động để phân biệt nội dung với viền" % len(
            frames), [], used
    rmean = [[sum(f[y * aw:(y + 1) * aw]) / aw for y in range(ah)] for f in frames]
    cmean = [[sum(f[x::aw]) / ah for x in range(aw)] for f in frames]
    oriented = (rmean, [p[::-1] for p in rmean], cmean, [p[::-1] for p in cmean])
    bands = []
    for band, size, prof in zip((top, bottom, left, right), (ah, ah, aw, aw), oriented):
        if band > MAX_BAND * size:
            return None, "vùng nội dung quá nhỏ (một phía viền > %d%%) — kiểm tra ảnh mẫu, tự nhập --crop" % (
                MAX_BAND * 100), [], used
        band = snap_out(band, size, prof)
        bands.append(0 if band <= size * 0.005 else band + 1)  # +1 điểm ảnh: lùi vào trong, tránh dính mép viền
    sy, sx = h / ah, w / aw
    y0 = math.ceil(bands[0] * sy / 2) * 2   # mép trên/trái làm tròn lên số chẵn (yuv420 cần toạ độ chẵn)
    x0 = math.ceil(bands[2] * sx / 2) * 2
    y1 = h - math.ceil(bands[1] * sy)
    x1 = w - math.ceil(bands[3] * sx)
    rect = {"x": x0, "y": y0, "w": even(x1 - x0), "h": even(y1 - y0)}
    rect.update(top=rect["y"], left=rect["x"], bottom=h - rect["y"] - rect["h"], right=w - rect["x"] - rect["w"])
    ty, by, lx, rx = bands[0], ah - bands[1], bands[2], aw - bands[3]
    ky, kx = max(2, ah // 50), max(2, aw // 50)
    dark = []
    for t, f in pairs:
        strips = (
            [f[y * aw + x] for y in range(ty, ty + ky) for x in range(lx, rx)],
            [f[y * aw + x] for y in range(by - ky, by) for x in range(lx, rx)],
            [f[y * aw + x] for y in range(ty, by) for x in range(lx, lx + kx)],
            [f[y * aw + x] for y in range(ty, by) for x in range(rx - kx, rx)],
        )
        if any(s and max(s) < 32 for s in strips):
            dark.append(t)
    return rect, "%d mẫu" % len(frames), dark, used


def stamp(keep, ts):
    """[00:42], [00:47] · đoạn P2 — mã đoạn theo thứ tự trong sheet."""
    codes = [s["code"] for s in keep or [] if any(s["start"] <= t < s["end"] for t in ts)]
    return ", ".join("[%s]" % short_tc(t) for t in ts) + (" · đoạn " + ", ".join(codes) if codes else "")


def layout_warning(keep, dark, used):
    """Bố cục đổi giữa các mẫu: nói rõ nhóm hẹp (còn dải đen trong khung hợp) và nhóm rộng, chỉ cách tách đúng hướng."""
    wide = [t for t in used if t not in dark]
    if not dark or not wide:
        return
    print("Cảnh báo: bố cục đổi giữa buổi — %d/%d mẫu bố cục hẹp (sẽ còn dải đen trong clip) %s; %d/%d mẫu bố cục "
          "rộng (dùng hết khung) %s. Khung trên là hợp của hai bố cục: đủ nội dung, nhưng phần bố cục hẹp còn dải đen." % (
              len(dark), len(used), stamp(keep, dark), len(wide), len(used), stamp(keep, wide)))
    if not keep:
        print("→ Thêm --sheet để biết đoạn nào thuộc bố cục nào, rồi tách bằng --only")
        return
    seg_of = lambda ts: [s["code"] for s in keep if any(s["start"] <= t < s["end"] for t in ts)]  # noqa: E731
    narrow_only = [c for c in seg_of(dark) if c not in seg_of(wide)]
    if narrow_only and seg_of(wide):
        print("→ Tách khung: chạy riêng --only %s và --only %s, mỗi nhóm một --crop" % (
            ",".join(narrow_only), ",".join(seg_of(wide))))
    else:
        print("→ Hai bố cục nằm chung đoạn %s: giữ khung trên (đủ nội dung) hoặc cắt tay đoạn đó" % ", ".join(
            seg_of(dark + wide)))


def parse_crop(text, w, h):
    m = re.fullmatch(r"(\d+):(\d+):(\d+):(\d+)", text.strip())
    if not m:
        die("--crop cần dạng W:H:X:Y (vd 1116:626:78:56), 'auto' hoặc 'none'; nhận: %s" % text)
    cw, ch, x, y = (int(v) for v in m.groups())
    if cw < 2 or ch < 2 or x + cw > w or y + ch > h:
        die("--crop %s nằm ngoài khung %dx%d" % (text, w, h))
    x, y = x // 2 * 2, y // 2 * 2  # yuv420 cần toạ độ chẵn; in ra đúng số thực dùng
    return {"x": x, "y": y, "w": even(cw), "h": even(ch), "top": y, "left": x,
            "bottom": h - y - even(ch), "right": w - x - even(cw)}


def parse_ratio(text):
    m = re.fullmatch(r"(\d+)[:/x](\d+)", text.strip())
    if not m or not int(m.group(1)) or not int(m.group(2)):
        die("tỉ lệ khung cần dạng W:H (vd 16:9, 9:16, 4:5); nhận: %s" % text)
    return int(m.group(1)), int(m.group(2))


STANDARDS = (2160, 1440, 1080, 720, 480, 360)   # cạnh ngắn chuẩn: 4K, 2K, Full HD, HD, SD
MAX_UPSCALE = 1.8    # khung đầu ra so với khung nguồn (cạnh ngắn): 720p → 1080p = ×1,5; 720p → 1440p = ×2,0 là quá
MAX_CONTENT = 2.0    # nội dung sau cắt viền phóng tối đa: viền Zoom dày (nội dung ~580 px) → 1080 = ×1,86 vẫn được
PORTRAIT_MAX = 1080  # khung dọc/vuông: chuẩn Reels/TikTok/Shorts 1080×1920, 1080×1350, 1080×1080
ENHANCE_PRE = "deblock=filter=strong:block=8,hqdn3d=1.5:1.5:3:3"   # trên khung gốc: lưới khối nén 8×8 còn thẳng
ENHANCE_POST = "cas=strength=0.6"   # sau khi phóng: làm nét có kiểm soát, không bịa chi tiết


def fit_scale(cw, ch, W, H, fit):
    return max(W / cw, H / ch) if fit == "fill" else min(W / cw, H / ch)


def upscale_of(src, cw, ch, W, H, fit):
    """→ (khung, nội dung): khung đầu ra lớn hơn khung nguồn bao nhiêu (cạnh ngắn so cạnh ngắn — "720p → 1080p" = ×1,5),
    và nội dung sau cắt viền bị phóng bao nhiêu."""
    return min(W, H) / min(src), fit_scale(cw, ch, W, H, fit)


def too_big(k):
    return k[0] > MAX_UPSCALE + 1e-9 or k[1] > MAX_CONTENT + 1e-9


def output_size(src, cw, ch, aspect, res, size, fit="pad", trail=None):
    """→ (W, H). src = (w, h) khung nguồn. res auto: thử chuẩn từ cao xuống, lấy chuẩn đầu tiên không quá mức — tức một
    bậc chuẩn trên nguồn (720p → 1080p, 1080p → 1440p, 480p → 720p); khung dọc/vuông tối đa 1080 cạnh ngắn.
    trail (list) nhận từng bước thử để in lý do chọn."""
    if size:
        sw, sh = parse_ratio(size)
        return even(sw), even(sh)
    aw, ah = parse_ratio(aspect) if aspect and aspect != "source" else (cw, ch)

    def dims(short):
        return (even(short * aw / ah + 1), even(short)) if aw > ah else (even(short), even(short * ah / aw + 1))

    if res == "auto":
        for s in STANDARDS:
            if aw <= ah and s > PORTRAIT_MAX:
                continue
            k = upscale_of(src, cw, ch, *dims(s), fit)
            if trail is not None:
                trail.append("%dp (khung x%.2f, nội dung x%.2f) %s" % (s, k[0], k[1], "quá" if too_big(k) else "✓"))
            if not too_big(k):
                return dims(s)
        res = "source"
    if res == "source":
        return dims(min(cw, ch) if (aw >= ah) == (cw >= ch) else max(cw, ch) * min(aw, ah) // max(aw, ah))
    if not str(res).isdigit() or int(res) < 2:
        die("--res cần số điểm ảnh cạnh ngắn (vd 1080), 'auto' hoặc 'source'; nhận: %s" % res)
    return dims(int(res))


def video_filter(rect, out, fit, enhance=False):
    """Một chuỗi lọc dùng chung cho ảnh xem trước và lệnh cắt — xem trước thế nào, ra video thế ấy.
    enhance: khử khối nén + khử nhiễu trên khung gốc, làm nét nhẹ sau khi phóng (không phủ lên nền đen/nền mờ)."""
    parts = ([ENHANCE_PRE] if enhance else []) + (
        ["crop=%d:%d:%d:%d" % (rect["w"], rect["h"], rect["x"], rect["y"])] if rect else [])
    sharpen = "," + ENHANCE_POST if enhance else ""
    if not out:
        return ",".join(parts) + sharpen if parts else ""
    W, H = out
    fitted = "scale=%d:%d:force_original_aspect_ratio=%%s:force_divisible_by=2:flags=lanczos" % (W, H)
    if fit == "fill":
        tail = (fitted % "increase") + ",crop=%d:%d" % (W, H) + sharpen + ",setsar=1"
    elif fit == "blur":
        tail = ("split[a][b];[a]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=20:2[bg];"
                "[b]%s%s[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1" % (W, H, W, H, fitted % "decrease", sharpen))
    else:
        tail = (fitted % "decrease") + sharpen + ",pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1" % (W, H)
    return ",".join(parts + [tail])


def frame_plan(args, video, w, h, keep, crop_default):
    """In kết quả khung hình và kế hoạch đầu ra. → (rect, out, vf, dark, used); vf rỗng = giữ nguyên hình;
    dark/used = mốc mẫu bố cục hẹp / mọi mẫu (cho ảnh xem trước)."""
    crop = args.crop or crop_default
    times = sample_times(video_info(video)[2], keep, args.samples)
    rect, dark, used = None, [], times
    if crop == "auto":
        rect, why, dark, used = detect_content(video, w, h, times)
        if rect is None:
            print("Viền thừa: không kết luận được — %s. Giữ nguyên khung." % why)
        elif not (rect["top"] or rect["bottom"] or rect["left"] or rect["right"]):
            print("Viền thừa: không có (%s) — giữ nguyên khung %dx%d." % (why, w, h))
            rect = None
        else:
            print("Viền thừa: có (%s) — trên %d · dưới %d · trái %d · phải %d px" % (
                why, rect["top"], rect["bottom"], rect["left"], rect["right"]))
            print("Khung nội dung: %dx%d → --crop %d:%d:%d:%d" % (
                rect["w"], rect["h"], rect["w"], rect["h"], rect["x"], rect["y"]))
        layout_warning(keep, dark, used)
    elif crop != "none":
        rect = parse_crop(crop, w, h)
        print("Khung nội dung (nhập tay): %dx%d tại %d,%d" % (rect["w"], rect["h"], rect["x"], rect["y"]))
    cw, ch = (rect["w"], rect["h"]) if rect else (w, h)
    out, trail = None, []
    if args.aspect or args.res or args.size:
        out = output_size((w, h), cw, ch, args.aspect, args.res or "source", args.size, args.fit, trail)
    if out:
        W, H = out
        rc, rt = cw / ch, W / H
        lost = 1 - min(rc, rt) / max(rc, rt)
        k = upscale_of((w, h), cw, ch, W, H, args.fit)
        how = {"pad": "giữ toàn bộ nội dung, nền đen", "fill": "phủ kín khung, cắt bớt mép nội dung",
               "blur": "giữ toàn bộ nội dung, nền mờ"}[args.fit]
        print("Đầu ra: %dx%d (%s) · nội dung %dx%d · tỉ lệ nội dung %.2f, khung %.2f · khung x%.2f so với nguồn, "
              "nội dung phóng x%.2f" % (W, H, how, cw, ch, rc, rt, k[0], k[1]))
        if trail:
            print("Chuẩn tự chọn (--res auto: một bậc trên nguồn, khung ≤ x%.1f, nội dung ≤ x%.1f%s): %s" % (
                MAX_UPSCALE, MAX_CONTENT, ", khung dọc/vuông ≤ %d" % PORTRAIT_MAX if W <= H else "",
                " · ".join(trail)))
        if lost > 0.005:
            print("%s: %s %.0f%% khung" % (
                "Cảnh báo" if args.fit == "fill" else "Ghi chú",
                "fill cắt mất mép nội dung, khoảng" if args.fit == "fill" else
                ("nền đen" if args.fit == "pad" else "nền mờ") + " chiếm khoảng", lost * 100))
        if too_big(k):
            print("Cảnh báo: khung x%.2f / nội dung x%.2f vượt mức vừa phải (khung ≤ x%.1f như 720p → 1080p, nội dung "
                  "≤ x%.1f). Nguồn %dx%d lên %dx%d chỉ làm file to hơn và lộ khối vỡ, không nét hơn — dùng --res auto "
                  "(chọn %dx%d)" % (k[0], k[1], MAX_UPSCALE, MAX_CONTENT, w, h, W, H,
                                    *output_size((w, h), cw, ch, args.aspect, "auto", None, args.fit)))
        elif k[1] > 1.01:
            print("Ghi chú: nội dung phóng x%.2f (vừa phải) — hình đạt khung chuẩn %dx%d, độ nét không vượt bản gốc%s" % (
                k[1], W, H, "" if args.enhance else "; thêm --enhance để làm sạch và làm nét nhẹ"))
    elif rect:
        print("Đầu ra: %dx%d (chỉ cắt viền, không đổi cỡ)" % (cw, ch))
    if args.enhance:
        print("Làm nét nhẹ: khử khối nén + khử nhiễu trên hình gốc, làm nét vừa phải sau khi phóng (không tạo chi tiết "
              "mới, không đổi nét chữ)")
    vf = video_filter(rect, out, args.fit, args.enhance) if (rect or out or args.enhance) else ""
    return rect, out, vf, dark, used


def preview_paths(out_dir):
    return os.path.join(out_dir, "khung-phat-hien.png"), os.path.join(out_dir, "khung-dau-ra.png")


def spread(ts, n):
    return [ts[i * (len(ts) - 1) // max(1, n - 1)] for i in range(n)] if len(ts) > n else list(ts)


def write_previews(video, h, rect, vf, used, dark, keep, out_dir):
    """Hai ảnh để duyệt bằng mắt: 4 mẫu có khung đỏ (đủ cả hai bố cục nếu bố cục đổi) và 1 khung đầu ra lấy từ bố cục
    đa số, chạy qua đúng chuỗi lọc sẽ dùng khi cắt."""
    detect, final = preview_paths(out_dir)
    refuse(detect, final)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        die("không tạo được thư mục %s: %s" % (out_dir, exc))
    wide = [t for t in used if t not in dark]
    if dark and wide:
        nd = min(len(dark), max(2, 4 - len(wide)))
        picks = sorted(spread(dark, nd) + spread(wide, 4 - nd))
    else:
        picks = spread(used, 4)
    cmd = ["ffmpeg", "-v", "error", "-n"]
    for t in picks:
        cmd += ["-ss", "%.3f" % (t / 1000), "-i", video]
    box = "drawbox=%d:%d:%d:%d:color=red@0.9:t=%d," % (
        rect["x"], rect["y"], rect["w"], rect["h"], max(2, h // 120)) if rect else ""
    parts = ["[%d:v]%sscale=640:-2,setsar=1[v%d]" % (i, box, i) for i in range(len(picks))]
    if len(picks) == 4:
        graph = ";".join(parts) + ";[v0][v1][v2][v3]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[o]"
    else:
        graph = parts[0].replace("[v0]", "[o]")
    res = subprocess.run(cmd + ["-filter_complex", graph, "-map", "[o]", "-frames:v", "1", detect],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        die("không tạo được ảnh %s: %s" % (detect, res.stderr.strip()))
    group = dark if len(dark) > len(wide) else (wide or used)
    mid = group[len(group) // 2]
    res = subprocess.run(["ffmpeg", "-v", "error", "-n", "-ss", "%.3f" % (mid / 1000), "-i", video,
                          "-vf", vf or "null", "-frames:v", "1", final], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if res.returncode != 0:
        die("không tạo được ảnh %s: %s" % (final, res.stderr.strip()))
    print("Ảnh xem trước: %s (%s)" % (detect, "khung đỏ = phần giữ lại" if rect else "không vẽ khung: giữ khung gốc"))
    places = ["trên-trái", "trên-phải", "dưới-trái", "dưới-phải"] if len(picks) == 4 else ["ảnh"]
    for place, t in zip(places, picks):
        print("  %s: %s%s" % (place, stamp(keep, [t]), " (bố cục hẹp)" if dark and wide and t in dark else
                                " (bố cục rộng)" if dark and wide else ""))
    print("Ảnh xem trước: %s (khung đầu ra, mẫu %s%s)" % (final, stamp(keep, [mid]),
                                                       ", bố cục đa số" if dark and wide else ""))


def wants_frame(args):
    return bool((args.crop and args.crop != "none") or args.aspect or args.res or args.size or args.enhance)


def encoder_args(args):
    if args.encoder == "videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-q:v", "65", "-pix_fmt", "yuv420p", "-tag:v", "avc1"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf), "-pix_fmt", "yuv420p", "-tag:v", "avc1"]


def cmd_frame(args):
    if not os.path.isfile(args.video):
        die("không tìm thấy file video nguồn: %s" % args.video)
    check_tools("ffmpeg", "ffprobe")
    w, h, d = video_info(args.video)
    if args.only and not args.sheet:
        die("--only cần --sheet")
    if args.preview:
        refuse(*preview_paths(args.preview))
    keep = select_only(parse_sheet_auto(args.sheet, args.prefix), args.only) if args.sheet else None
    print("# frame: %s" % args.video)
    print("Khung gốc: %dx%d · %s · mẫu lấy %s" % (w, h, long_(d), "trong đoạn KEEP" if keep else "đều cả video"))
    rect, out, vf, dark, used = frame_plan(args, args.video, w, h, keep, "auto")
    if vf:
        print("Chuỗi lọc: %s" % vf)
    if args.preview:
        write_previews(args.video, h, rect, vf, used, dark, keep, args.preview)


# ---------------------------------------------------------------- Lệnh CLI

def cmd_probe(args):
    meta = probe_metadata(args.video)
    audio = probe_audio(args.video, args.sample_time, args.duration)

    v_stream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "audio"), None)
    duration_s = float(meta.get("format", {}).get("duration", 0))

    print("# probe: %s" % args.video)
    print("Thời lượng: %s (%dp %02ds)" % (long_(int(duration_s * 1000)), int(duration_s // 60), int(duration_s % 60)))
    if v_stream:
        print("Video stream: %s (%dx%d)" % (v_stream.get("codec_name"), v_stream.get("width", 0), v_stream.get("height", 0)))
    if a_stream:
        print("Audio stream: %s" % a_stream.get("codec_name"))

    print("\n--- Khảo sát âm thanh (mẫu: %s, %ds) ---" % (audio["sample_time"], audio["duration"]))
    if audio["ch1"] is not None:
        print("Kênh 1 (Trái): %.1f dB" % audio["ch1"])
    if audio["ch2"] is not None:
        print("Kênh 2 (Phải): %.1f dB" % audio["ch2"])
        print("Độ lệch kênh (Δ): %.1f dB" % audio["delta"])
    print("Độ lớn trung bình: %.1f dB" % audio["overall"])

    status = []
    if audio["single_ear"]:
        status.append("Điếc 1 bên tai")
    elif audio["imbalanced"]:
        status.append("Lệch kênh (Δ ≥ 4 dB)")
    elif audio["ch2"] is not None:
        status.append("Cân bằng tốt (Δ ≤ 3 dB)")
    else:
        status.append("Mono (1 kênh)")

    if audio["quiet"]:
        status.append("Âm lượng nhỏ (RMS < -24 dB)")
    else:
        status.append("Âm lượng vừa vặn (RMS ≥ -24 dB)")
    print("Tình trạng: %s" % " · ".join(status))

    desc = {
        "copy": "Mode 1 (copy) — Pure Stream Copy (không re-encode, tốc độ tối đa)",
        "balance": "Mode 2 (balance) — Cân bằng Dual-Mono (re-encode AAC 192k)",
        "master": "Mode 3 (master) — Dual-Mono + Loudnorm -16 LUFS (re-encode AAC 192k)"
    }
    print("Khuyến nghị: %s" % desc[audio["mode"]])


def cmd_parse(args):
    keep = parse_sheet_auto(args.sheet, args.prefix)
    print("# parse: %s" % args.sheet)
    print("Tổng số: %d phân đoạn KEEP\n" % len(keep))
    print("| STT | Timecode gốc | Thời lượng | Tên file xuất |")
    print("| :---: | :---: | :---: | :--- |")
    for i, s in enumerate(keep, 1):
        span = "%s - %s" % (long_(s["start"]), long_(s["end"]))
        print("| %d | `%s` | %s | %s |" % (i, span, dur(s["end"] - s["start"]), s["out_name"]))


def cmd_cut(args):
    if not os.path.isfile(args.video):
        die("không tìm thấy file video nguồn: %s" % args.video)
    check_tools("ffmpeg")

    keep = select_only(parse_sheet_auto(args.sheet, args.prefix), args.only)
    vf = ""
    if wants_frame(args):  # kiểm khung trước khảo sát âm thanh: --crop sai bị từ chối ngay
        w, h, _ = video_info(args.video)
        print("Khung hình (gốc %dx%d):" % (w, h))
        _, _, vf, _, _ = frame_plan(args, args.video, w, h, keep, "none")
        print("→ Hình mã hoá lại: %s" % ("x264 CRF %d" % args.crf if args.encoder == "x264"
                                          else "VideoToolbox (nhanh hơn, nét kém hơn x264)"))

    mode = args.mode
    audio = None
    if mode == "auto":
        print("Khảo sát âm thanh trước khi cắt (Pre-flight probe)...")
        audio = probe_audio(args.video)
        mode = audio["mode"]
        print("→ Tự động chọn chế độ: %s (RMS: %.1f dB, Δ: %.1f dB)" % (mode, audio["overall"], audio["delta"]))

    if not args.dry_run:
        try:
            os.makedirs(args.out_dir, exist_ok=True)
        except OSError as exc:
            die("không tạo được thư mục đầu ra %s: %s" % (args.out_dir, exc))

    is_mono = (audio.get("ch2") is None) if audio else False
    pan_filter = "pan=stereo|c0=c0|c1=c0" if is_mono else "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"
    video_args = ["-vf", vf] + encoder_args(args) if vf else ["-c:v", "copy"]
    if mode == "balance":
        audio_args = ["-af", pan_filter, "-c:a", "aac", "-b:a", "192k"]
    elif mode == "master":
        audio_args = ["-af", "%s,loudnorm=I=-16:TP=-1.5:LRA=11" % pan_filter, "-c:a", "aac", "-b:a", "192k"]
    else:
        audio_args = ["-c:a", "copy"]

    print("\nBắt đầu cắt %d video con (âm thanh: %s · hình: %s)..." % (
        len(keep), mode, "mã hoá lại" if vf else "giữ nguyên"))
    for idx, s in enumerate(keep, 1):
        out_path = os.path.join(args.out_dir, s["out_name"])
        if not args.dry_run and os.path.lexists(out_path):
            die("%s đã có — xoá file hoặc đổi thư mục (không ghi đè)" % out_path)

        st_tc = long_(s["start"])
        en_tc = long_(s["end"])
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", st_tc, "-to", en_tc, "-i", args.video]
        cmd += video_args + audio_args + ["-movflags", "+faststart", "-n", out_path]

        if args.dry_run:
            print("[%d/%d] DRY-RUN: %s (%s → %s)" % (idx, len(keep), s["out_name"], st_tc, en_tc))
            print("  Lệnh: %s" % shlex.join(cmd))
            continue

        print("[%d/%d] Đang cắt: %s (%s → %s, %s)..." % (idx, len(keep), s["out_name"], st_tc, en_tc, dur(s["end"] - s["start"])))
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            if os.path.exists(out_path):
                os.remove(out_path)  # file dở do chính lệnh này tạo (đã kiểm chưa tồn tại trước khi chạy)
            die("Lỗi ffmpeg khi cắt %s: %s" % (s["out_name"], res.stderr))

    if not args.dry_run:
        print("\nHoàn tất cắt %d video con vào: %s" % (len(keep), args.out_dir))
    else:
        print("\nHoàn tất kiểm tra lệnh dry-run cho %d video con" % len(keep))


def cmd_verify(args):
    check_tools("ffprobe")
    if not os.path.isdir(args.dir):
        die("%s không phải thư mục" % args.dir)

    files = sorted([f for f in os.listdir(args.dir) if f.lower().endswith(".mp4")])
    print("Nghiệm thu video con trong: %s (%d files)\n" % (args.dir, len(files)))
    if not files:
        print("Thư mục trống, không có file .mp4 nào.")
        return

    print("| STT | Tên file con | Dung lượng | Thời lượng | Khung hình | Trạng thái |")
    print("| :---: | :--- | :---: | :---: | :---: | :---: |")
    expect = None
    if args.expect_size:
        ew, eh = parse_ratio(args.expect_size)
        expect = "%dx%d" % (ew, eh)

    sheet_segs = {}
    if args.sheet:
        sheet_segs = {s["out_name"]: s for s in parse_sheet_auto(args.sheet, args.prefix)}

    errors = 0
    for idx, f in enumerate(files, 1):
        fpath = os.path.join(args.dir, f)
        size_mb = os.path.getsize(fpath) / (1024 * 1024)

        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
            "-of", "json", fpath
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            info = json.loads(res.stdout or "{}")
            dur_sec = float(info.get("format", {}).get("duration", 0))
            st = (info.get("streams") or [{}])[0]
            size = "%sx%s" % (st.get("width", "?"), st.get("height", "?"))
        except ValueError:
            dur_sec, size = 0.0, "?"

        status = "HỢP LỆ"
        if size_mb <= 0 or dur_sec <= 0:
            status = "LỖI: RỖNG"
            errors += 1
        elif expect and size != expect:
            status = "LỖI: KHUNG %s ≠ %s" % (size, expect)
            errors += 1
        elif f in sheet_segs:
            expected_sec = (sheet_segs[f]["end"] - sheet_segs[f]["start"]) / 1000
            if abs(dur_sec - expected_sec) > 3.0:
                status = "CẢNH BÁO: LỆCH THỜI LƯỢNG"

        print("| %d | %s | %.1f MB | %dp %02ds | %s | %s |" % (
            idx, f, size_mb, int(dur_sec // 60), int(dur_sec % 60), size, status))
    if sheet_segs and not set(files) & set(sheet_segs):
        print("Cảnh báo: không clip nào khớp tên trong %s — thời lượng chưa được đối chiếu; kiểm --prefix giống lúc cắt"
              % args.sheet)

    print("\nKết quả kiểm tra: %d clip hợp lệ, %d lỗi" % (len(files) - errors, errors))
    if errors:
        sys.exit(1)


def main(argv=None):
    utf8_stdio()
    ap = argparse.ArgumentParser(description="Cắt nhỏ video bài giảng dài theo Action Sheet.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    frame_opts = argparse.ArgumentParser(add_help=False)
    frame_opts.add_argument("--crop", help="auto | none | W:H:X:Y")
    frame_opts.add_argument("--aspect", help="16:9 | 9:16 | 1:1 | 4:5 | W:H | source")
    frame_opts.add_argument("--res", help="cạnh ngắn đầu ra: auto (chuẩn phù hợp nguồn) | 1080 | 720 … | source")
    frame_opts.add_argument("--enhance", action="store_true",
                            help="làm sạch khối nén + nhiễu, làm nét vừa phải (mã hoá lại hình)")
    frame_opts.add_argument("--size", help="kích thước tuỳ chỉnh WxH, vd 1080x1350")
    frame_opts.add_argument("--fit", choices=["pad", "fill", "blur"], default="pad")
    frame_opts.add_argument("--samples", type=int, default=12)
    frame_opts.add_argument("--only", help="chỉ các đoạn KEEP có mã này, vd P4,P5.1")

    p = sub.add_parser("probe")
    p.add_argument("video")
    p.add_argument("--sample-time", default="00:15:00")
    p.add_argument("--duration", type=int, default=30)
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("frame", parents=[frame_opts])
    p.add_argument("video")
    p.add_argument("--sheet")
    p.add_argument("--prefix", default="")
    p.add_argument("--preview", help="thư mục ghi ảnh xem trước")
    p.set_defaults(fn=cmd_frame)

    p = sub.add_parser("parse")
    p.add_argument("sheet")
    p.add_argument("--prefix", default="")
    p.set_defaults(fn=cmd_parse)

    p = sub.add_parser("cut", parents=[frame_opts])
    p.add_argument("video")
    p.add_argument("--sheet", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--prefix", default="")
    p.add_argument("--mode", choices=["auto", "copy", "balance", "master"], default="auto")
    p.add_argument("--encoder", choices=["x264", "videotoolbox"], default="x264")
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_cut)

    p = sub.add_parser("verify")
    p.add_argument("dir")
    p.add_argument("--sheet")
    p.add_argument("--prefix", default="")
    p.add_argument("--expect-size", help="WxH mọi clip phải đạt, vd 1920x1080")
    p.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    if getattr(args, "samples", 4) < 4:
        die("--samples cần ≥ 4")
    args.fn(args)


if __name__ == "__main__":
    main()
