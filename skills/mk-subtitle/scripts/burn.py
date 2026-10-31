#!/usr/bin/env python3
"""In phụ đề vào video (tuỳ chọn): lấy khung mẫu, tính bố cục theo khung hình + vùng an toàn nền tảng + khung mặt người
nói (ảnh xem trước để duyệt), xuất file ASS, in cứng bằng ffmpeg có libass. Ngắt dòng theo bố cục: subtitle.py reflow.
Chỉ thư viện chuẩn + ffmpeg/ffprobe; đầu ra tất định; không sửa, không ghi đè file có sẵn.

  burn.py frames VIDEO --out-dir DIR [--samples 6]
  burn.py layout DIR --out DIR/layout-1.json [--platform youtube|tiktok|shorts|reels|khung[,…]] [--faces DIR/mat.tsv]
                 [--style chuan|ngan] [--font Arial] [--size PX] [--bold] [--box] [--position auto|duoi|tren]
  burn.py ass SUB.srt --layout L.json --out PHU-DE.ass
  burn.py burn VIDEO --ass PHU-DE.ass --preview PREFIX [--fonts-dir DIR] [--ffmpeg PATH]   → PREFIX-1.png…
  burn.py burn VIDEO --ass PHU-DE.ass --out OUT.mp4 [--dry-run] [--fonts-dir DIR] [--ffmpeg PATH]

mat.tsv (khung mặt, tỉ lệ 0–1, gốc trên-trái): "tên ảnh<TAB>x<TAB>y<TAB>w<TAB>h" (nhiều dòng một ảnh được), "tên<TAB>NONE".
ffmpeg có libass: --ffmpeg, rồi biến môi trường MK_SUBTITLE_FFMPEG, ffmpeg trong PATH, bản ffmpeg-full của Homebrew.
Thoát: 0 xong (có thể kèm dòng "Cảnh báo:"); 1 lỗi đầu vào/ffmpeg hoặc có dòng "LỖI:" (không ghi file); 2 sai cách gọi.
"""
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subtitle as st  # noqa: E402  (die, read, blocks, srt, Cue, chunk, refuse_overwrite, utf8_stdio)
import takes as tk  # noqa: E402  (arg_path, tc, deliver)

# Vùng giao diện che video (tỉ lệ khung): trên, dưới, trái, phải. Video dọc 1080×1920, số liệu tổng hợp 2026;
# YouTube ngang: lề an toàn 5% + chừa thanh điều khiển ở đáy. references/chen-phu-de.md §2.
PLATFORMS = {
    "youtube": (0.05, 0.06, 0.05, 0.05),
    "khung": (0.05, 0.05, 0.05, 0.05),
    "tiktok": (0.07, 0.25, 0.06, 0.17),
    "shorts": (0.06, 0.16, 0.05, 0.14),
    "reels": (0.14, 0.35, 0.06, 0.11),
}
WIDE_TEXT = 0.68      # BBC: chữ phụ đề rộng tối đa 68% khung 16:9
CHAR_W = 0.5          # bề rộng trung bình một ký tự ≈ 0,5 × cỡ chữ: mức mục tiêu (chừa cho chữ hoa, số)
HARD_CHAR_W = 0.45    # mức trần: Arial chữ thường tiếng Việt đo được ~0,42 × cỡ chữ
LINE_H = 1.2          # chiều cao một dòng ≈ 1,2 × cỡ chữ
FACE_GAP = 0.02       # khoảng hở tối thiểu giữa chữ và mặt (tỉ lệ chiều cao)
FFMPEG_FULL = ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "/usr/local/opt/ffmpeg-full/bin/ffmpeg")
INSTALL_HINT = ("cần ffmpeg có libass để in phụ đề — macOS: brew install ffmpeg-full (cài song song, không thay "
                "ffmpeg đang dùng); Windows: winget install Gyan.FFmpeg (bản full); Linux: sudo apt install ffmpeg")


def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)


def probe(video):
    if not os.path.isfile(video):
        st.die("không thấy file %s" % video)
    res = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
               "-of", "json", tk.arg_path(video)])
    try:
        data = json.loads(res.stdout)
        dur = float(data["format"]["duration"])
        v = next(s for s in data["streams"] if s.get("codec_type") == "video")
        return int(v["width"]), int(v["height"]), dur
    except (ValueError, KeyError, StopIteration):
        st.die("không đọc được khung hình của %s: %s" % (video, res.stderr.strip()[-300:]))


def write_new(path, text):
    st.refuse_overwrite(path)
    with open(path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ---------------------------------------------------------------- frames: khung mẫu

def cmd_frames(args):
    tk.need_tools()
    w, h, dur = probe(args.video)
    if os.path.lexists(args.out_dir) and (not os.path.isdir(args.out_dir) or os.path.islink(args.out_dir)
                                          or os.listdir(args.out_dir)):
        st.die("%s đã có file — chọn thư mục mới (skill không ghi đè)" % args.out_dir)
    os.makedirs(args.out_dir, exist_ok=True)
    n = max(1, min(args.samples, 12))
    rows = ["# video\t%s" % os.path.abspath(args.video), "# kich_thuoc\t%d\t%d" % (w, h), "# thoi_luong\t%.3f" % dur,
            "file\tgiay"]
    for k in range(n):
        t = dur * (k + 0.5) / n
        name = "mau-%02d.png" % (k + 1)
        res = run(["ffmpeg", "-v", "error", "-n", "-ss", "%.3f" % t, "-i", tk.arg_path(args.video), "-frames:v", "1",
                   tk.arg_path(os.path.join(args.out_dir, name))])
        if res.returncode != 0:
            st.die("ffmpeg không lấy được khung ở %s: %s" % (tk.tc(t), res.stderr.strip()[-300:]))
        rows.append("%s\t%.3f" % (name, t))
    with open(os.path.join(args.out_dir, "mau.tsv"), "x", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(rows) + "\n")
    print("%dx%d · %s · %d khung mẫu → %s" % (w, h, "ngang" if w > h else "dọc", n, args.out_dir))


def read_frames(folder):
    meta, frames = {}, []
    path = os.path.join(folder, "mau.tsv")
    if not os.path.isfile(path):
        st.die("%s không có mau.tsv — chạy burn.py frames trước" % folder)
    for ln in st.read(path).splitlines():
        cols = ln.split("\t")
        if ln.startswith("# "):
            meta[cols[0][2:]] = cols[1:]
        elif cols[0] != "file" and len(cols) == 2:
            try:
                frames.append((os.path.basename(cols[0]), float(cols[1])))
            except ValueError:
                st.die("%s: dòng khung mẫu sai dạng: %s" % (path, ln))
    try:
        w, h = int(meta["kich_thuoc"][0]), int(meta["kich_thuoc"][1])
        return meta["video"][0], w, h, float(meta["thoi_luong"][0]), frames
    except (KeyError, IndexError, ValueError):
        st.die("%s thiếu dòng # video / # kich_thuoc / # thoi_luong" % path)


def read_faces(path):
    """→ {tên ảnh: [(x, y, w, h)]} tỉ lệ 0–1."""
    faces = {}
    for n, ln in enumerate(st.read(path).splitlines(), 1):
        cols = ln.strip().split("\t")
        if not ln.strip() or ln.startswith("#"):
            continue
        name = os.path.basename(cols[0])
        if len(cols) == 2 and cols[1] == "NONE":
            faces.setdefault(name, [])
            continue
        try:
            box = tuple(float(c) for c in cols[1:5])
        except ValueError:
            box = ()
        if len(box) != 4 or not all(0 <= v <= 1 for v in box):
            st.die("%s:%d: cần 'tên ảnh<TAB>x<TAB>y<TAB>w<TAB>h' (tỉ lệ 0–1) hoặc 'tên<TAB>NONE'" % (path, n))
        faces.setdefault(name, []).append(box)
    return faces


# ---------------------------------------------------------------- layout: bố cục

def safe_zone(platforms):
    names = [p.strip() for p in platforms.split(",") if p.strip()]
    bad = [p for p in names if p not in PLATFORMS]
    if not names or bad:
        st.die("--platform không biết: %s (có: %s)" % (", ".join(bad) or "(trống)", ", ".join(PLATFORMS)))
    return names, tuple(max(PLATFORMS[p][i] for p in names) for i in range(4))


def plan_layout(w, h, platforms, faces, style, size, position):
    """→ dict bố cục (pixel) + danh sách cảnh báo. Tất định."""
    horizontal = w > h
    names, (top, bottom, left, right) = safe_zone(platforms or ("youtube" if horizontal else "tiktok,shorts"))
    if horizontal:
        side = (1 - WIDE_TEXT) / 2
        left, right = max(left, side), max(right, side)
    max_lines = 1 if style == "ngan" else 2
    font = size or round(h * (0.055 if horizontal else 0.045 if style == "ngan" else 0.033))
    text_w = w * (1 - left - right)
    max_chars = max(8, min(42, int(text_w / (CHAR_W * font))))
    hard_chars = max(max_chars, int(text_w / (HARD_CHAR_W * font)))
    outline = max(2, round(font * 0.07))
    block_h = max_lines * LINE_H * font + 2 * outline
    floor_y, ceil_y = h * (1 - bottom), h * top
    gap = h * FACE_GAP
    warns = []
    boxes = [b for bs in faces.values() for b in bs]
    face_top = min((b[1] for b in boxes), default=None)
    face_bottom = max((b[1] + b[3] for b in boxes), default=None)
    fits_below = face_bottom is None or floor_y - block_h >= face_bottom * h + gap
    fits_above = face_top is not None and ceil_y + block_h <= face_top * h - gap
    if position == "tren" or position == "auto" and not fits_below and fits_above:
        align, margin_v = "tren", round(ceil_y)
    else:
        align, margin_v = "duoi", round(h * bottom)
    if face_bottom is not None and align == "duoi" and not fits_below:
        hit = sum(1 for bs in faces.values() if any(b[1] + b[3] > (floor_y - block_h - gap) / h for b in bs))
        warns.append("phụ đề ở dưới sẽ che phần dưới mặt (cằm, miệng) ở %d/%d khung mẫu — thử --style ngan, --size "
                     "nhỏ hơn, --position tren, hoặc bỏ bớt nền tảng có vùng chừa lớn (reels)" % (hit, len(faces)))
    if face_top is not None and align == "tren" and not fits_above:
        warns.append("phụ đề ở trên sẽ che mặt — xem ảnh xem trước")
    if not faces:
        warns.append("chưa có khung mặt (--faces): xem ảnh xem trước, vùng xanh không được đè lên mặt người nói")
    return {
        "width": w, "height": h, "orientation": "ngang" if horizontal else "doc", "platforms": names,
        "safe": {"top": round(ceil_y), "bottom": round(h * bottom), "left": round(w * left), "right": round(w * right)},
        "style": style, "font_size": font, "outline": outline, "max_chars": max_chars, "hard_chars": hard_chars,
        "max_lines": max_lines,
        "align": align, "margin_v": margin_v, "margin_l": round(w * left), "margin_r": round(w * right),
        "block_h": round(block_h), "face_top": face_top, "face_bottom": face_bottom,
    }, warns


def preview_layout(folder, frames, lay, faces, out_png):
    """Ảnh xem trước: vùng giao diện nền tảng (xám), khung mặt (đỏ), vùng phụ đề (xanh) trên từng khung mẫu."""
    w, h = lay["width"], lay["height"]
    boxes = []
    for p in lay["platforms"]:
        t, b, _, r = PLATFORMS[p]
        boxes += ["drawbox=x=0:y=0:w=%d:h=%d:color=gray@0.45:t=fill" % (w, round(h * t)),
                  "drawbox=x=0:y=%d:w=%d:h=%d:color=gray@0.45:t=fill" % (round(h * (1 - b)), w, round(h * b))]
        if lay["orientation"] == "doc":
            boxes.append("drawbox=x=%d:y=%d:w=%d:h=%d:color=gray@0.45:t=fill" % (
                round(w * (1 - r)), round(h * 0.3), round(w * r), round(h * 0.5)))
    y = lay["margin_v"] if lay["align"] == "tren" else h - lay["margin_v"] - lay["block_h"]
    sub = "drawbox=x=%d:y=%d:w=%d:h=%d:color=lime@0.45:t=fill" % (
        lay["margin_l"], y, w - lay["margin_l"] - lay["margin_r"], lay["block_h"])
    tmp = tempfile.mkdtemp(prefix="mk-subtitle-xem-")
    try:
        parts = []
        for k, (name, _) in enumerate(frames):
            face = ["drawbox=x=%d:y=%d:w=%d:h=%d:color=red@0.9:t=%d" % (
                round(fx * w), round(fy * h), round(fw * w), round(fh * h), max(2, w // 240))
                for fx, fy, fw, fh in faces.get(name, [])]
            one = os.path.join(tmp, "%02d.png" % k)
            res = run(["ffmpeg", "-v", "error", "-i", tk.arg_path(os.path.join(folder, name)), "-vf",
                       ",".join(boxes + face + [sub, "scale=-2:480"]), tk.arg_path(one)])
            if res.returncode != 0:
                st.die("ffmpeg không vẽ được ảnh xem trước: %s" % res.stderr.strip()[-300:])
            parts.append(one)
        cmd = ["ffmpeg", "-v", "error", "-n"]
        for p in parts:
            cmd += ["-i", tk.arg_path(p)]
        graph = "hstack=inputs=%d" % len(parts) if len(parts) > 1 else "null"
        res = run(cmd + ["-filter_complex", graph, tk.arg_path(out_png)])
        if res.returncode != 0:
            st.die("ffmpeg không ghép được ảnh xem trước: %s" % res.stderr.strip()[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def font_check(font):
    """Có fc-list → kiểm font có trong máy và có chữ tiếng Việt. → dòng cảnh báo hoặc None."""
    if not shutil.which("fc-list"):
        return None
    res = run(["fc-list", ":family=%s:lang=vi" % font, "family"])
    if not res.stdout.strip():
        return ("không thấy font '%s' có đủ chữ tiếng Việt trên máy — libass sẽ dùng font khác; cài font đó, hoặc "
                "chỉ thư mục font bằng burn --fonts-dir, rồi xem dòng 'Font dùng thật' ở ảnh mẫu" % font)
    return None


def cmd_layout(args):
    tk.need_tools()
    video, w, h, dur, frames = read_frames(args.dir)
    if not args.out.endswith(".json"):
        st.die("--out phải là file .json")
    png = args.out[:-5] + ".png"
    st.refuse_overwrite(args.out, png)
    if any(c in args.font for c in ",;\r\n"):
        st.die("--font không được chứa dấu phẩy, chấm phẩy hay xuống dòng")
    faces = read_faces(args.faces) if args.faces else {}
    unknown = sorted(set(faces) - {n for n, _ in frames})
    if unknown:
        st.die("%s có ảnh không nằm trong mau.tsv: %s" % (args.faces, ", ".join(unknown[:6])))
    lay, warns = plan_layout(w, h, args.platform, faces, args.style, args.size, args.position)
    missing = [n for n, _ in frames if faces and n not in faces]
    if missing:
        warns.append("%s thiếu khung mẫu %s (đo mặt dừng giữa chừng?) — đo lại trước khi duyệt" % (
            args.faces, ", ".join(missing)))
    lay.update({"video": video, "duration": dur, "font": args.font, "bold": args.bold, "box": args.box})
    fw = font_check(args.font)
    if fw:
        warns.append(fw)
    preview_layout(args.dir, frames, lay, faces, png)
    write_new(args.out, json.dumps(lay, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print("%dx%d %s · nền tảng: %s" % (w, h, "ngang" if lay["orientation"] == "ngang" else "dọc",
                                       ", ".join(lay["platforms"])))
    print("Chữ: %s %dpx · tối đa %d dòng × %d ký tự (dòng khó ngắt được tới %d) · %s, cách mép %dpx" % (
        args.font, lay["font_size"], lay["max_lines"], lay["max_chars"], lay["hard_chars"],
        "phía trên" if lay["align"] == "tren" else "phía dưới", lay["margin_v"]))
    print("Ngắt dòng theo bố cục: subtitle.py reflow <phụ đề> --max-chars %d --max-lines %d --out <file>" % (
        lay["max_chars"], lay["max_lines"]))
    if lay["face_bottom"] is not None:
        print("Mặt người nói: %.0f%% → %.0f%% chiều cao (%d khung có mặt)" % (
            lay["face_top"] * 100, lay["face_bottom"] * 100, sum(1 for v in faces.values() if v)))
    for w_ in warns:
        print("Cảnh báo: " + w_)
    print("→ %s · ảnh xem trước %s (xám: giao diện nền tảng · đỏ: mặt · xanh: vùng phụ đề)" % (args.out, png))


def read_layout(path):
    try:
        lay = json.loads(st.read(path))
        for k in ("width", "height", "font_size", "max_chars", "hard_chars", "max_lines", "align", "margin_v",
                  "margin_l", "margin_r", "outline", "font"):
            lay[k]
    except (ValueError, KeyError, TypeError) as exc:
        st.die("%s không phải file bố cục của burn.py layout (%s)" % (path, exc))
    if not isinstance(lay["font"], str) or any(c in lay["font"] for c in ",;\r\n"):
        st.die("%s: tên font không hợp lệ" % path)
    return lay


# ---------------------------------------------------------------- ass: file phụ đề có kiểu chữ, vị trí

def ass_time(ms):
    cs = int(round(ms / 10))
    return "%d:%02d:%02d.%02d" % (cs // 360000, cs // 6000 % 60, cs // 100 % 60, cs % 100)


def ass_text(lines):
    """Chữ phụ đề là dữ liệu: libass không có cách viết dấu \\ thường, nên chèn U+2060 (vô hình) sau mỗi \\ để
    \\N, \\h, \\an8… không thành lệnh; { } thoát bằng \\{ \\}."""
    return "\\N".join(l.replace("\\", "\\\u2060").replace("{", "\\{").replace("}", "\\}") for l in lines)


def cmd_ass(args):
    lay = read_layout(args.layout)
    st.refuse_overwrite(args.out)
    cues = [(a, b, [l.strip() for l in lines if l.strip()]) for a, b, lines in st.blocks(st.read(args.input))]
    errors, warns = [], []
    for n, (a, b, lines) in enumerate(cues, 1):
        if len(lines) > lay["max_lines"]:
            errors.append("câu %d có %d dòng (tối đa %d)" % (n, len(lines), lay["max_lines"]))
        for line in lines:
            if len(line) > lay["hard_chars"]:
                errors.append("câu %d dòng dài %d ký tự, tràn vùng phụ đề (tối đa %d): %s" % (
                    n, len(line), lay["hard_chars"], line))
            elif len(line) > lay["max_chars"]:
                warns.append("câu %d dòng %d ký tự (nên ≤ %d, vẫn vừa vùng phụ đề): %s" % (
                    n, len(line), lay["max_chars"], line))
    if errors:
        for e in errors:
            print("LỖI: " + e)
        print("Ngắt lại bằng subtitle.py reflow, hoặc sửa chữ (subtitle.py export → sửa → build) rồi chạy lại")
        sys.exit(1)
    box = lay.get("box")
    style = ",".join(str(v) for v in (
        "Default", lay["font"], lay["font_size"], "&H00FFFFFF", "&H000000FF",
        "&H60000000" if box else "&H00000000", "&H80000000", -1 if lay.get("bold") else 0, 0, 0, 0, 100, 100, 0, 0,
        3 if box else 1, lay["outline"], 0 if box else 1, 8 if lay["align"] == "tren" else 2,
        lay["margin_l"], lay["margin_r"], lay["margin_v"], 1))
    out = ["[Script Info]", "; burn.py ass từ %s" % os.path.basename(args.input), "ScriptType: v4.00+",
           "PlayResX: %d" % lay["width"], "PlayResY: %d" % lay["height"], "WrapStyle: 2",
           "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "", "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
           "MarginR, MarginV, Encoding", "Style: " + style, "", "[Events]",
           "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    out += ["Dialogue: 0,%s,%s,Default,,0,0,0,,%s" % (ass_time(a), ass_time(b), ass_text(lines))
            for a, b, lines in cues if lines]
    write_new(args.out, "\n".join(out) + "\n")
    print("%d câu → %s" % (len(cues), args.out))
    for w_ in warns:
        print("Cảnh báo: " + w_)


# ---------------------------------------------------------------- burn: in cứng

def find_ffmpeg(explicit):
    cands = [explicit] if explicit else [os.environ.get("MK_SUBTITLE_FFMPEG"), shutil.which("ffmpeg")]
    cands += [] if explicit else list(FFMPEG_FULL)
    for c in cands:
        if c and os.path.isfile(c):
            res = run([c, "-hide_banner", "-filters"])
            if any(ln.split()[1:2] == ["ass"] for ln in res.stdout.splitlines()):
                return c
    st.die(INSTALL_HINT + (" (%s không có libass)" % explicit if explicit else ""))


def cmd_burn(args):
    tk.need_tools()
    w, h, dur = probe(args.video)
    if bool(args.preview) == bool(args.out):
        st.die("cần đúng một trong hai: --preview PREFIX (ảnh mẫu) hoặc --out OUT.mp4 (in cả video)")
    events = read_events(args.ass)
    timeline_warnings(events, dur)
    if args.preview:
        picks = {events[0], max(events, key=lambda e: (e[2], -e[0])), events[-1]}
        times = [round((a + b) / 2, 3) for a, b, _ in sorted(picks)]
        outs = ["%s-%d.png" % (args.preview, k + 1) for k in range(len(times))]
        st.refuse_overwrite(*outs)
    else:
        root, ext = os.path.splitext(args.out)
        tmp = root + ".dang-ghi" + (ext or ".mp4")
        st.refuse_overwrite(args.out, tmp)
    ff = find_ffmpeg(args.ffmpeg)
    work = tempfile.mkdtemp(prefix="mk-subtitle-in-")
    try:
        # ffmpeg cần tên file trong chuỗi filter; chép ASS (và font) vào thư mục làm việc để khỏi thoát ký tự đường dẫn
        shutil.copyfile(args.ass, os.path.join(work, "phu-de.ass"))
        vf = "ass=phu-de.ass"
        if args.fonts_dir:
            if not os.path.isdir(args.fonts_dir):
                st.die("không thấy thư mục font %s" % args.fonts_dir)
            os.mkdir(os.path.join(work, "fonts"))
            for f in sorted(os.listdir(args.fonts_dir)):
                if f.lower().endswith((".ttf", ".otf", ".ttc")):
                    shutil.copyfile(os.path.join(args.fonts_dir, f), os.path.join(work, "fonts", f))
            vf += ":fontsdir=fonts"
        video = os.path.abspath(args.video)
        if args.preview:
            used = set()
            for t, png in zip(times, outs):
                res = run([ff, "-hide_banner", "-v", "info", "-n", "-ss", "%.3f" % t, "-copyts", "-i", video, "-vf", vf,
                           "-frames:v", "1", os.path.abspath(png)], cwd=work)
                if res.returncode != 0:
                    st.die("ffmpeg không in được ảnh mẫu: %s" % res.stderr.strip()[-400:])
                used |= {font_used(ln) for ln in res.stderr.splitlines() if "fontselect:" in ln}
            for f in sorted(used):
                print("Font dùng thật: " + f)
            print("Ảnh mẫu có chữ: " + ", ".join(outs))
            return
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-n", "-i", video, "-vf", vf, "-map", "0:v:0", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy",
               "-movflags", "+faststart", os.path.abspath(tmp)]
        if args.dry_run:
            print("DRY-RUN: chưa ghi file. Lệnh (chạy trong thư mục chứa phu-de.ass): %s" % shlex.join(
                cmd[:-1] + [os.path.abspath(args.out)]))
            return
        res = run(cmd, cwd=work)
        if res.returncode != 0:
            if os.path.lexists(tmp) and "already exists" not in res.stderr:
                os.remove(tmp)  # file dở do chính lệnh này tạo (ffmpeg -n không ghi vào file đã có)
            st.die("ffmpeg lỗi khi in phụ đề: %s" % res.stderr.strip()[-400:])
        got = tk.deliver(tmp, args.out, dur, "in phụ đề")
        print("→ %s · %dx%d · %s" % (args.out, w, h, tk.tc(got)))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def read_events(ass_path):
    """→ [(bắt đầu, kết thúc, độ dài chữ)] giây, theo thứ tự trong file ASS."""
    events = []
    for n, ln in enumerate(st.read(ass_path).splitlines(), 1):
        if ln.startswith("Dialogue:"):
            f = ln.split(",", 9)
            try:
                a, b = (sum(float(x) * m for x, m in zip(t.split(":"), (3600, 60, 1))) for t in f[1:3])
                events.append((a, b, len(f[9])))
            except (ValueError, IndexError):
                st.die("%s:%d: dòng Dialogue sai dạng" % (ass_path, n))
    if not events:
        st.die("%s không có câu Dialogue nào" % ass_path)
    return events


def timeline_warnings(events, dur):
    last = max(b for _, b, _ in events)
    if last > dur + 0.5:
        print("Cảnh báo: phụ đề kéo tới %s, video chỉ dài %s — có đúng phụ đề của video này (bản final)?" % (
            tk.tc(last), tk.tc(dur)))
    elif last < dur * 0.5:
        print("Cảnh báo: phụ đề hết ở %s, video dài %s — có đúng phụ đề của video này?" % (tk.tc(last), tk.tc(dur)))


def font_used(line):
    """'fontselect: (Arial, 400, 0) -> /đường/dẫn/Arial.ttf, -1, ArialMT' → 'ArialMT (/đường/dẫn/Arial.ttf)'."""
    parts = [p.strip() for p in line.split("->", 1)[1].split(",")]
    return "%s (%s)" % (parts[-1], parts[0]) if len(parts) >= 3 else parts[0]


def main(argv=None):
    st.utf8_stdio()
    ap = argparse.ArgumentParser(description="In phụ đề vào video: khung mẫu, bố cục, ngắt dòng, ASS, in cứng.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("frames", help="lấy khung mẫu để đo mặt, xem bố cục")
    p.add_argument("video")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--samples", type=int, default=6)
    p.set_defaults(fn=cmd_frames)
    p = sub.add_parser("layout", help="tính bố cục phụ đề + ảnh xem trước")
    p.add_argument("dir")
    p.add_argument("--out", required=True)
    p.add_argument("--platform")
    p.add_argument("--faces")
    p.add_argument("--style", choices=["chuan", "ngan"], default="chuan")
    p.add_argument("--font", default="Arial")
    p.add_argument("--size", type=int)
    p.add_argument("--bold", action="store_true")
    p.add_argument("--box", action="store_true")
    p.add_argument("--position", choices=["auto", "duoi", "tren"], default="auto")
    p.set_defaults(fn=cmd_layout)
    p = sub.add_parser("ass", help="xuất file ASS theo bố cục")
    p.add_argument("input")
    p.add_argument("--layout", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_ass)
    p = sub.add_parser("burn", help="in cứng phụ đề (cần ffmpeg có libass)")
    p.add_argument("video")
    p.add_argument("--ass", required=True)
    p.add_argument("--out")
    p.add_argument("--preview", metavar="PREFIX", help="chỉ in ảnh mẫu PREFIX-1.png… (câu đầu, dài nhất, cuối)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fonts-dir")
    p.add_argument("--ffmpeg")
    p.set_defaults(fn=cmd_burn)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
