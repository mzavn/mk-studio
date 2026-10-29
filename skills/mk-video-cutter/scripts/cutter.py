#!/usr/bin/env python3
"""Cắt nhỏ video bài giảng dài theo Action Sheet và tự động cân bằng âm thanh.

  cutter.py probe VIDEO [--sample-time 00:15:00] [--duration 30]
  cutter.py parse SHEET [--prefix "Buổi 1"]
  cutter.py cut VIDEO --sheet SHEET --out-dir DIR [--prefix "Buổi 1"] [--mode auto|copy|balance|master] [--dry-run]
  cutter.py verify DIR [--sheet SHEET]

Chỉ dùng thư viện chuẩn Python (Standard Library). Yêu cầu ffmpeg/ffprobe trong PATH.
"""
import argparse
import csv
import json
import os
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


def check_tools(*names):
    for name in names:
        if not shutil.which(name):
            die("cần công cụ '%s' trong PATH để thực hiện thao tác" % name)


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
    res = subprocess.run(cmd, capture_output=True, text=True)
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
    res = subprocess.run(cmd, capture_output=True, text=True)
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
        res = subprocess.run(cmd, capture_output=True, text=True)
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

    keep = parse_sheet_auto(args.sheet, args.prefix)
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

    print("\nBắt đầu cắt %d video con (chế độ: %s)..." % (len(keep), mode))
    for idx, s in enumerate(keep, 1):
        out_path = os.path.join(args.out_dir, s["out_name"])
        if not args.dry_run and os.path.lexists(out_path):
            die("%s đã có — xoá file hoặc đổi thư mục (không ghi đè)" % out_path)

        st_tc = long_(s["start"])
        en_tc = long_(s["end"])
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", st_tc, "-to", en_tc, "-i", args.video]

        if mode == "copy":
            cmd += ["-c", "copy"]
        elif mode == "balance":
            cmd += [
                "-c:v", "copy",
                "-af", pan_filter,
                "-c:a", "aac", "-b:a", "192k"
            ]
        elif mode == "master":
            cmd += [
                "-c:v", "copy",
                "-af", "%s,loudnorm=I=-16:TP=-1.5:LRA=11" % pan_filter,
                "-c:a", "aac", "-b:a", "192k"
            ]
        cmd += [out_path, "-y"]

        if args.dry_run:
            print("[%d/%d] DRY-RUN: %s (%s → %s)" % (idx, len(keep), s["out_name"], st_tc, en_tc))
            print("  Lệnh: %s" % " ".join(cmd))
            continue

        print("[%d/%d] Đang cắt: %s (%s → %s, %s)..." % (idx, len(keep), s["out_name"], st_tc, en_tc, dur(s["end"] - s["start"])))
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
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

    print("| STT | Tên file con | Dung lượng | Thời lượng | Trạng thái |")
    print("| :---: | :--- | :---: | :---: | :---: |")

    sheet_segs = {}
    if args.sheet:
        try:
            keep = parse_sheet_auto(args.sheet)
            sheet_segs = {s["out_name"]: s for s in keep}
        except Exception:
            pass

    errors = 0
    for idx, f in enumerate(files, 1):
        fpath = os.path.join(args.dir, f)
        size_mb = os.path.getsize(fpath) / (1024 * 1024)

        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", fpath
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        dur_sec = float(res.stdout.strip()) if res.stdout.strip() else 0.0

        status = "HỢP LỆ"
        if size_mb <= 0 or dur_sec <= 0:
            status = "LỖI: RỖNG"
            errors += 1
        elif f in sheet_segs:
            expected_sec = (sheet_segs[f]["end"] - sheet_segs[f]["start"]) / 1000
            if abs(dur_sec - expected_sec) > 3.0:
                status = "CẢNH BÁO: LỆCH THỜI LƯỢNG"

        print("| %d | %s | %.1f MB | %dp %02ds | %s |" % (
            idx, f, size_mb, int(dur_sec // 60), int(dur_sec % 60), status))

    print("\nKết quả kiểm tra: %d clip hợp lệ, %d lỗi" % (len(files) - errors, errors))
    if errors:
        sys.exit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cắt nhỏ video bài giảng dài theo Action Sheet.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe")
    p.add_argument("video")
    p.add_argument("--sample-time", default="00:15:00")
    p.add_argument("--duration", type=int, default=30)
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("parse")
    p.add_argument("sheet")
    p.add_argument("--prefix", default="")
    p.set_defaults(fn=cmd_parse)

    p = sub.add_parser("cut")
    p.add_argument("video")
    p.add_argument("--sheet", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--prefix", default="")
    p.add_argument("--mode", choices=["auto", "copy", "balance", "master"], default="auto")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_cut)

    p = sub.add_parser("verify")
    p.add_argument("dir")
    p.add_argument("--sheet")
    p.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
