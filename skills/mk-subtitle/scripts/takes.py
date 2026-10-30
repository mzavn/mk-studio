#!/usr/bin/env python3
"""Video có kịch bản (quay một lần, có chỗ đọc lại/vấp): tách cụm lời theo khoảng ngừng đo trên âm thanh, dựng phụ
đề từ mốc thật + lời từng đoạn, tìm câu đọc lại → bảng giữ/cắt, cắt mốc lẻ giây và ghép một file final (FFmpeg).
Chỉ thư viện chuẩn + ffmpeg/ffprobe; đầu ra tất định; không sửa, không ghi đè file có sẵn.

  takes.py segments VIDEO --out-dir DIR [--threshold auto|-50] [--min-gap 0.25] [--merge-gap 0.4] [--max-chunk 6]
  takes.py srt DIR/segments.tsv --texts TEXTS [--texts TEXTS_BO_SUNG] --out FILE.srt
  takes.py texts DIR/segments.tsv --from SUB.srt|SUB.vtt --out TEXTS
  takes.py retakes DIR/segments.tsv --texts TEXTS [--texts TEXTS_BO_SUNG] --out PLAN.tsv
  takes.py cut VIDEO --plan PLAN.tsv --out FINAL.mp4 [--srt FULL.srt --out-srt FINAL.srt] [--dry-run]
  takes.py cut VIDEO --plan PLAN.tsv --srt FULL.en.srt --out-srt FINAL.en.srt --srt-only

TEXTS: mỗi dòng "mã|lời" (hoặc "mã<TAB>lời"), mã như cột `ma` của segments.tsv; lời "NONE" = đoạn không có lời nói.
       Nhiều --texts: file sau thay lời của file trước theo mã (lượt chép lại riêng vài cụm).
PLAN: TSV "bat_dau ket_thuc lenh ly_do" (giây, 3 chữ số lẻ; lenh KEEP hoặc CUT), phủ kín từ 0 tới hết video.
Thoát: 0 xong (có thể kèm dòng "Cảnh báo:"); 1 lỗi đầu vào/ffmpeg; 2 sai cách gọi.
"""
import argparse
import array
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subtitle as st  # noqa: E402  (die, utf8_stdio, blocks, read, srt, Cue, fmt, refuse_overwrite)

FRAME = 0.02          # giây mỗi khung đo âm lượng
SMOOTH = 2            # làm mượt ±2 khung (100 ms)
MIN_SEG = 0.15        # bỏ cụm ngắn hơn (tiếng tách)
LEAD, TAIL = 0.45, 0.8  # giữ trước câu đầu / sau câu cuối
EXACT_GAP, FUZZY_GAP = 0.5, 1.0  # ngừng tối thiểu trước lần đọc lại (đúng nguyên văn / gần giống)
MANY_CHUNKS = 150
DIGITS = {"0": "không", "1": "một", "2": "hai", "3": "ba", "4": "bốn", "5": "năm", "6": "sáu", "7": "bảy",
          "8": "tám", "9": "chín"}


def tc(sec):
    return st.fmt(int(round(sec * 1000)))


def need_tools():
    for name in ("ffmpeg", "ffprobe"):
        if not shutil.which(name):
            st.die("cần '%s' trong PATH — cài ffmpeg: brew install ffmpeg (macOS), winget install Gyan.FFmpeg "
                   "(Windows), rồi mở lại terminal" % name)


def arg_path(path):
    """Đường dẫn bắt đầu bằng '-' bị ffmpeg hiểu là tuỳ chọn → thêm './'."""
    return os.path.join(".", path) if path.startswith("-") else path


def probe(video):
    """→ (thời lượng giây, số khung/giây hoặc None khi không có hình)."""
    if not os.path.isfile(video):
        st.die("không thấy file %s" % video)
    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,r_frame_rate",
                          "-of", "json", arg_path(video)], capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    try:
        data = json.loads(res.stdout)
        dur = float(data["format"]["duration"])
    except (ValueError, KeyError):
        st.die("không đọc được thông số %s: %s" % (video, res.stderr.strip()[-300:]))
    streams = data.get("streams", [])
    if not any(s.get("codec_type") == "audio" for s in streams):
        st.die("%s không có âm thanh — không tách được cụm lời" % video)
    fps = None
    for s in streams:
        if s.get("codec_type") == "video":
            num, _, den = s.get("r_frame_rate", "0/1").partition("/")
            try:
                fps = float(num) / float(den or 1)
            except (ValueError, ZeroDivisionError):
                fps = None
            fps = fps if fps and fps > 0 else 30.0
            break
    return dur, fps


# ---------------------------------------------------------------- đo âm lượng dải giọng nói

def envelope(video):
    """→ (dB thô, dB làm mượt 100 ms) mỗi khung 20 ms, chỉ dải tần giọng nói (250–3800 Hz) để nhạc nền ít ảnh hưởng.
    Bản mượt để tách cụm lời; bản thô để tìm khe cắt giữa hai chữ (khe ~40 ms bị làm mượt lấp mất)."""
    res = subprocess.run(["ffmpeg", "-v", "error", "-i", arg_path(video), "-vn", "-ac", "1", "-ar", "16000",
                          "-af", "highpass=f=250,lowpass=f=3800", "-f", "s16le", "-"], capture_output=True)
    if res.returncode != 0:
        st.die("ffmpeg không đọc được âm thanh: %s" % res.stderr.decode("utf-8", "replace").strip()[-300:])
    pcm = array.array("h")
    pcm.frombytes(res.stdout[:len(res.stdout) // 2 * 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    n = int(16000 * FRAME)
    raw = []
    for i in range(0, len(pcm) - n + 1, n):
        win = pcm[i:i + n]
        raw.append(10 * math.log10(sum(x * x for x in win) / n / 32768.0 ** 2 + 1e-12))
    out = []
    for i in range(len(raw)):
        part = raw[max(0, i - SMOOTH):i + SMOOTH + 1]
        out.append(sum(part) / len(part))
    return raw, out


def speech_segments(env, threshold, min_gap):
    """→ [(bắt đầu, kết thúc)] giây: các đoạn giữa những khoảng dưới ngưỡng dài ≥ min_gap."""
    segs, start, quiet = [], None, 0
    need = int(round(min_gap / FRAME))
    for i, v in enumerate(env + [-999.0] * (need + 1)):
        if v >= threshold:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet >= need:
                end = i - quiet + 1
                if (end - start) * FRAME >= MIN_SEG:
                    segs.append((round(start * FRAME, 3), round(end * FRAME, 3)))
                start, quiet = None, 0
    return segs


def chunks(segs, merge_gap, max_chunk):
    out = []
    for a, b in segs:
        if out and a - out[-1][1] < merge_gap and b - out[-1][0] <= max_chunk:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def cmd_segments(args):
    need_tools()
    dur, _ = probe(args.video)
    if os.path.lexists(args.out_dir) and (not os.path.isdir(args.out_dir) or os.path.islink(args.out_dir)
                                          or os.listdir(args.out_dir)):
        st.die("%s đã có file — chọn thư mục mới (skill không ghi đè)" % args.out_dir)
    raw, env = envelope(args.video)
    if not env:
        st.die("âm thanh quá ngắn")
    srt_ = sorted(env)
    p10, p90 = srt_[len(srt_) // 10], srt_[len(srt_) * 9 // 10]
    th = p10 + 11 if args.threshold == "auto" else float(args.threshold)
    segs = chunks(speech_segments(env, th, args.min_gap), args.merge_gap, args.max_chunk)
    print("Âm lượng dải giọng: p10 %.1f dB · p90 %.1f dB · ngưỡng %.1f dB" % (p10, p90, th))
    if p90 - p10 < 20:
        print("Cảnh báo: giọng khó tách khỏi nền (chênh %.0f dB < 20) — ranh giới cụm lời có thể sai, nghe kỹ" % (
            p90 - p10))
    if not segs:
        st.die("không tìm thấy lời nói (thử --threshold thấp hơn ngưỡng %.1f)" % th)
    os.makedirs(args.out_dir, exist_ok=True)
    rows = ["# thoi_luong\t%.3f" % dur, "ma\tbat_dau\tket_thuc\tfile"]
    for i, (a, b) in enumerate(segs, 1):
        name = "c%03d.mp3" % i
        res = subprocess.run(["ffmpeg", "-v", "error", "-n", "-ss", "%.3f" % max(0, a - 0.1), "-to", "%.3f" % (b + 0.1),
                              "-i", arg_path(args.video), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
                              arg_path(os.path.join(args.out_dir, name))], capture_output=True, text=True,
                             encoding="utf-8",
                             errors="replace")
        if res.returncode != 0:
            st.die("ffmpeg không tách được đoạn %s: %s" % (name, res.stderr.strip()[-300:]))
        rows.append("c%03d\t%.3f\t%.3f\t%s" % (i, a, b, name))
    with open(os.path.join(args.out_dir, "segments.tsv"), "x", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(rows) + "\n")
    with open(os.path.join(args.out_dir, "envelope.tsv"), "x", encoding="utf-8", newline="\n") as fh:
        fh.write("".join("%.2f\t%.1f\n" % (i * FRAME, v) for i, v in enumerate(raw)))
    print("Lời từ %s tới %s · %d đoạn → %s" % (tc(segs[0][0]), tc(segs[-1][1]), len(segs),
                                              os.path.join(args.out_dir, "segments.tsv")))
    if segs[0][0] - LEAD > 0.05:  # cùng ngưỡng với `retakes`
        print("Đầu không lời: %s → %s (%.1f giây; bước retakes đề xuất cắt tới %s, giữ %.2f giây trước câu đầu)" % (
            tc(0), tc(segs[0][0]), segs[0][0], tc(segs[0][0] - LEAD), LEAD))
    if dur - (segs[-1][1] + TAIL) > 0.05:
        print("Cuối không lời: %s → %s (%.1f giây; bước retakes đề xuất cắt từ %s)" % (
            tc(segs[-1][1]), tc(dur), dur - segs[-1][1], tc(segs[-1][1] + TAIL)))
    if len(segs) > MANY_CHUNKS:
        print("Cảnh báo: %d đoạn — quá nhiều để gửi một lượt; video dài nên lấy phụ đề YouTube (S fetch) "
              "hoặc chia nhỏ video" % len(segs))


# ---------------------------------------------------------------- đọc segments.tsv, lời từng đoạn

def read_segments(path):
    dur, segs = None, []
    for ln in st.read(path).splitlines():
        if not ln.strip():
            continue
        cols = ln.split("\t")
        if ln.startswith("#"):
            if cols[0].strip() == "# thoi_luong" and len(cols) > 1:
                dur = float(cols[1])
            continue
        if cols[0] == "ma":
            continue
        try:
            segs.append((cols[0], float(cols[1]), float(cols[2])))
        except (IndexError, ValueError):
            st.die("%s: dòng sai định dạng: %s" % (path, ln))
    if not segs or dur is None:
        st.die("%s: không có đoạn nào hoặc thiếu dòng '# thoi_luong'" % path)
    return dur, segs


CODE_LINE = re.compile(r"(?:^\s*|(?<=[.!?…\"'”)\]]))(c\d{3,})[ \t]*[|\t][ \t]*(.*?)\s*$")


def read_texts(paths, segs):
    """Lời từng cụm từ một hoặc nhiều file; file sau thay lời của file trước theo mã (lượt chép bổ sung)."""
    texts = {}
    for path in paths:
        mine = {}
        for ln in st.read(path).splitlines():
            # mã ở đầu dòng, hoặc dính liền sau dấu kết câu (agy đôi khi dán lời bình ngay trước mã); mã đứng sau
            # dấu cách giữa câu ("file c003|c004 …") là lời bình, không phải lời
            m = CODE_LINE.search(ln)
            if not m or not m.group(2):  # lời rỗng = thiếu (chỉ NONE mới là "không có lời")
                continue
            text = "" if m.group(2).upper() == "NONE" else re.sub(r"\s+", " ", m.group(2))
            if m.group(1) in mine and mine[m.group(1)] != text:
                st.die("%s: mã %s có hai lời khác nhau — chép lại riêng đoạn đó vào file bổ sung" % (path, m.group(1)))
            mine[m.group(1)] = text
        texts.update(mine)
    codes = [c for c, _, _ in segs]
    missing = [c for c in codes if c not in texts]
    extra = sorted(set(texts) - set(codes))
    if missing:
        st.die("thiếu lời của %d đoạn: %s (đoạn không có lời ghi NONE)" % (len(missing), ", ".join(missing[:12])))
    if extra:
        st.die("lời có mã không nằm trong segments.tsv: %s" % ", ".join(extra[:12]))
    return texts


def words(text):
    return [DIGITS.get(w, w) for w in re.sub(r"[^\w\s]", " ", text.lower()).split()]


def write_new(path, text):
    st.refuse_overwrite(path)
    with open(path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ---------------------------------------------------------------- phụ đề

def wrap(text, width=42):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])


def finish_cues(items, total):
    """items: [(bắt đầu, kết thúc, [dòng])] giây → [Cue] ms: lùi 0,05 s, kéo dài 0,3 s, tối thiểu 0,8 s, không chồng."""
    out = []
    for k, (a, b, lines) in enumerate(items):
        s = max(0.0, a - 0.05)
        nxt = max(0.0, items[k + 1][0] - 0.05) if k + 1 < len(items) else total
        e = min(max(b + 0.3, s + 0.8), nxt - 0.04)
        out.append(st.Cue(int(round(s * 1000)), int(round(max(e, s + 0.1) * 1000)), lines))
    return out


def cmd_srt(args):
    dur, segs = read_segments(args.segments)
    texts = read_texts(args.texts, segs)
    st.refuse_overwrite(args.out)
    items = []
    for code, a, b in segs:
        lines = wrap(texts[code])
        if not lines:
            continue
        groups = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        total = sum(len(" ".join(g)) for g in groups)
        t = a
        for g in groups:
            span = (b - a) * len(" ".join(g)) / total
            items.append((t, t + span, g))
            t += span
    if not items:
        st.die("không đoạn nào có lời")
    write_new(args.out, st.srt(finish_cues(items, dur)))
    print("%d câu → %s (kiểm bằng: subtitle.py check %s)" % (len(items), args.out, args.out))


def cmd_texts(args):
    """Đã có phụ đề (SRT/VTT, kể cả VTT YouTube mốc từng từ) → lời từng cụm theo mốc, khỏi gửi âm thanh đi."""
    _, segs = read_segments(args.segments)
    st.refuse_overwrite(args.out)
    kind, ws, _ = st.load(args.sub)
    bucket = {c: [] for c, _, _ in segs}
    for w in ws:
        mid = (w.start + w.end) / 2000.0
        code = min(segs, key=lambda s: (0 if s[1] <= mid <= s[2] else min(abs(mid - s[1]), abs(mid - s[2])), s[1]))[0]
        bucket[code].append(w.text)
    lines = ["%s|%s" % (c, " ".join(bucket[c]) or "NONE") for c, _, _ in segs]
    write_new(args.out, "\n".join(lines) + "\n")
    spoken = sum(1 for c, _, _ in segs if bucket[c])
    print("%d đoạn có lời · %d đoạn NONE → %s" % (spoken, len(segs) - spoken, args.out))
    if kind != "youtube":
        print("Cảnh báo: %s chỉ có mốc theo câu — chia chữ vào từng cụm là ước lượng, đọc lại %s trước khi tìm "
              "câu đọc lại" % (args.sub, args.out))


# ---------------------------------------------------------------- câu đọc lại → bảng giữ/cắt

def find_retakes(segs, texts):
    """→ [(kiểu, chỉ số đầu, chỉ số cuối, chữ)]: đoạn i..j-1 bị đọc lại ở j; kiểu 'cuối-đầu' = bỏ n chữ cuối đoạn i."""
    w = [words(texts[c]) for c, _, _ in segs]
    found, cut = [], set()
    for j in range(1, len(segs)):
        gap = segs[j][1] - segs[j - 1][2]
        follow = [x for k in range(j, min(len(segs), j + 4)) for x in w[k]]
        for i in range(max(0, j - 3), j):
            if any(k in cut for k in range(i, j)):
                continue
            run = [x for k in range(i, j) for x in w[k]]
            if len(run) < 2:
                continue
            same = 0
            while same < min(len(run), len(follow)) and run[same] == follow[same]:
                same += 1
            text = " ".join(texts[segs[k][0]] for k in range(i, j)).rstrip(" ….")
            if same == len(run) and gap >= EXACT_GAP:
                found.append(("đọc lại", i, j - 1, text))
                cut.update(range(i, j))
                break
            if same >= 3 and same >= len(run) / 2 and gap >= FUZZY_GAP:
                found.append(("đọc lại (gần giống)", i, j - 1, text))
                cut.update(range(i, j))
                break
        a, b = w[j - 1], w[j]
        if j - 1 in cut or gap < EXACT_GAP:
            continue
        for n in range(min(4, len(a) - 1, len(b)), 1, -1):
            # ≥ 3 chữ lặp khó là trùng hợp: ngừng ≥ 0,5 s đủ; 2 chữ cần ngừng ≥ 1 s mới coi là đọc lại
            if a[-n:] == b[:n] and gap >= (EXACT_GAP if n >= 3 else FUZZY_GAP):
                found.append(("lặp cuối–đầu", j - 1, n, " ".join(texts[segs[j][0]].split()[:n]).rstrip(",.…")))
                break
    return found


def quietest(env_path, lo, hi, guess):
    """Khe yên nhất trong [lo, hi] theo envelope.tsv (trung bình 3 khung 20 ms), phạt 20 dB mỗi giây xa chỗ đoán:
    hai khe sâu ngang nhau (vd giữa "cả|khi" và "khi|cảm") thì chọn khe gần chỗ lặp, không nuốt chữ. Không có file → None."""
    if not os.path.isfile(env_path):
        return None
    pts = []
    for ln in st.read(env_path).splitlines():
        t, v = ln.split("\t")
        pts.append((float(t), float(v)))
    win = [(t, v) for t, v in pts if lo <= t <= hi]
    if len(win) < 3:
        return None
    best = min(range(1, len(win) - 1), key=lambda k: (sum(v for _, v in win[k - 1:k + 2]) / 3
                                                     + 20 * abs(win[k][0] - guess), win[k][0]))
    return win[best][0] + FRAME / 2


def cmd_retakes(args):
    dur, segs = read_segments(args.segments)
    texts = read_texts(args.texts, segs)
    st.refuse_overwrite(args.out)
    spoken = [k for k, (c, _, _) in enumerate(segs) if texts[c]]
    if not spoken:
        st.die("không đoạn nào có lời")
    env_path = os.path.join(os.path.dirname(os.path.abspath(args.segments)), "envelope.tsv")
    cuts, warns = [], []
    first, last = segs[spoken[0]][1], segs[spoken[-1]][2]
    if first - LEAD > 0.05:
        cuts.append((0.0, round(first - LEAD, 3), "đầu: không có lời — xem hình trước khi bỏ"))
    if dur - (last + TAIL) > 0.05:
        cuts.append((round(last + TAIL, 3), dur, "cuối: không có lời — xem hình trước khi bỏ"))
    found = find_retakes(segs, texts)
    for kind, i, j_or_n, text in found:
        if kind == "lặp cuối–đầu":
            code, a, b = segs[i]
            nxt = segs[i + 1][1]
            ws = texts[code].split()
            ratio = len(" ".join(ws[:len(ws) - j_or_n])) / max(1, len(texts[code]))
            guess = a + (b - a) * ratio
            t = quietest(env_path, max(a, guess - 0.3), min(b, guess + 0.3), guess) or guess
            end = nxt - min(0.2, (nxt - b) / 2)
            cuts.append((round(t, 3), round(end, 3), "%s: %s" % (kind, text)))
            warns.append("cắt giữa đoạn %s ở %s — nghe lại chỗ nối" % (code, tc(t)))
            continue
        a, b = segs[i][1], segs[j_or_n][2]
        prev_end = segs[i - 1][2] if i > 0 else max(0.0, a - 0.6)
        nxt = segs[j_or_n + 1][1]
        start = prev_end + min(0.3, (a - prev_end) / 2)
        end = nxt - min(0.2, (nxt - b) / 2)
        cuts.append((round(start, 3), round(end, 3), "%s: %s" % (kind, text)))
    cuts.sort()
    merged = []
    for a, b, why in cuts:
        if merged and a <= merged[-1][1]:
            pa, pb, pw = merged[-1]
            merged[-1] = (pa, max(pb, b), pw + " + " + why)
        else:
            merged.append((a, b, why))
    rows, t = [], 0.0
    for a, b, why in merged:
        if a > t:
            rows.append((t, a, "KEEP", ""))
        rows.append((max(a, t), b, "CUT", why))
        t = b
    if t < dur:
        rows.append((t, dur, "KEEP", ""))
    write_new(args.out, "bat_dau\tket_thuc\tlenh\tly_do\n" + "".join(
        "%.3f\t%.3f\t%s\t%s\n" % r for r in rows))
    for a, b, cmd, why in rows:
        print("%s %s → %s%s" % (cmd, tc(a), tc(b), " · " + why if why else ""))
    for w_ in warns:
        print("Cảnh báo: " + w_)
    kept = sum(b - a for a, b, c, _ in rows if c == "KEEP")
    print("%d chỗ đọc lại · giữ %s / gốc %s → %s" % (len(found), tc(kept), tc(dur), args.out))


# ---------------------------------------------------------------- cắt, ghép, dời mốc phụ đề

def read_plan(path, dur):
    keep = []
    for n, ln in enumerate(st.read(path).splitlines(), 1):
        cols = ln.split("\t")
        if not ln.strip() or ln.startswith("#") or cols[0] == "bat_dau":
            continue
        if len(cols) < 3 or cols[2].strip().upper() not in ("KEEP", "CUT"):
            st.die("%s:%d: cần 'bat_dau<TAB>ket_thuc<TAB>KEEP|CUT<TAB>lý do'" % (path, n))
        try:
            a, b = float(cols[0]), float(cols[1])
        except ValueError:
            st.die("%s:%d: mốc phải là số giây (vd 25.300)" % (path, n))
        if not 0 <= a < b <= dur + 0.05:
            st.die("%s:%d: đoạn %.3f → %.3f nằm ngoài video (%.3f giây)" % (path, n, a, b, dur))
        if cols[2].strip().upper() == "KEEP":
            keep.append((a, min(b, dur)))
    keep.sort()
    for (a, b), (c, d) in zip(keep, keep[1:]):
        if c < b:
            st.die("%s: hai đoạn KEEP chồng nhau (%.3f → %.3f và %.3f → %.3f)" % (path, a, b, c, d))
    if not keep:
        st.die("%s: không có đoạn KEEP nào" % path)
    return keep


def remap_srt(path, keep):
    """→ ([Cue] trên bản final, [cảnh báo]). Câu nằm hẳn trong phần cắt bị bỏ; câu bị cắt một phần được báo."""
    offs, acc = [], 0
    km = [(int(round(a * 1000)), int(round(b * 1000))) for a, b in keep]
    for a, b in km:
        offs.append(acc)
        acc += b - a
    cues, warns = [], []
    for s, e, lines in st.blocks(st.read(path)):
        parts = [(max(s, a), min(e, b), o + max(s, a) - a) for (a, b), o in zip(km, offs) if min(e, b) > max(s, a)]
        if not parts:
            continue
        kept = sum(b - a for a, b, _ in parts)
        if e - s - kept > 350:
            warns.append("câu %d của bản final bị cắt một phần — sửa chữ cho khớp lời còn lại" % (len(cues) + 1))
        start = parts[0][2]
        end = parts[-1][2] + parts[-1][1] - parts[-1][0]
        cues.append(st.Cue(start, end, lines))
    return cues, warns


def cmd_cut(args):
    need_tools()
    dur, fps = probe(args.video)
    if not fps:
        st.die("%s không có hình" % args.video)
    keep = read_plan(args.plan, dur)
    if bool(args.srt) != bool(args.out_srt):
        st.die("--srt và --out-srt phải đi cùng nhau")
    # Mốc cắt bám lưới khung hình: không bám thì mỗi đoạn dài thêm tới gần một khung, lệch dồn qua các điểm nối
    raw_keep = keep
    keep = [(round(a * fps) / fps, round(b * fps) / fps) for a, b in keep]
    keep = [(a, b) for a, b in keep if b > a]
    print("Mốc cắt bám khung hình %.3g khung/giây: lệch tối đa nửa khung (%.3f giây) so với bảng" % (fps, 0.5 / fps))
    for (a, b), (c, d) in zip(raw_keep, raw_keep[1:]):
        if c > b and round(c * fps) == round(b * fps):
            print("Cảnh báo: đoạn CUT %s → %s ngắn hơn một khung hình — bị bỏ qua" % (tc(b), tc(c)))
    if args.srt_only:
        if not args.srt:
            st.die("--srt-only cần --srt và --out-srt")
        st.refuse_overwrite(args.out_srt)
        return remap_to(args.srt, args.out_srt, keep)
    if not args.out:
        st.die("cần --out <file final.mp4>")
    st.refuse_overwrite(*[p for p in (args.out, args.out_srt) if p])
    root, ext = os.path.splitext(args.out)
    tmp, bad = root + ".dang-ghi" + (ext or ".mp4"), root + ".loi" + (ext or ".mp4")
    st.refuse_overwrite(tmp)
    total = sum(b - a for a, b in keep)
    parts, labels = [], ""
    for i, (a, b) in enumerate(keep):
        d = b - a
        # hình: mốc đặt giữa hai khung (lùi nửa khung) → không lấy dư khung do làm tròn, đúng cả với video VFR
        parts.append("[0:v]trim=start=%.6f:end=%.6f,setpts=PTS-STARTPTS[v%d]" % (
            max(0.0, a - 0.5 / fps), b - 0.5 / fps, i))
        parts.append("[0:a]atrim=start=%.6f:end=%.6f,asetpts=PTS-STARTPTS,afade=t=in:d=0.02,"
                     "afade=t=out:st=%.6f:d=0.02[a%d]" % (a, b, max(0.0, d - 0.02), i))
        labels += "[v%d][a%d]" % (i, i)
    graph = ";".join(parts) + ";%sconcat=n=%d:v=1:a=1[v][a]" % (labels, len(keep))
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", arg_path(args.video), "-filter_complex", graph,
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", arg_path(tmp)]
    for i, (a, b) in enumerate(keep, 1):
        print("KEEP %d: %s → %s (%.2f giây)" % (i, tc(a), tc(b), b - a))
    print("Tổng: %s (gốc %s, bỏ %s)" % (tc(total), tc(dur), tc(dur - total)))
    if args.dry_run:
        print("DRY-RUN: chưa ghi file. Lệnh: %s" % shlex.join(cmd[:-1] + [args.out]))
        return
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        if os.path.lexists(tmp):
            os.remove(tmp)  # file dở do chính lệnh này tạo
        st.die("ffmpeg lỗi khi cắt: %s" % res.stderr.strip()[-400:])
    got, _ = probe(tmp)
    if abs(got - total) > 0.1:
        if not os.path.lexists(bad):
            os.replace(tmp, bad)
        st.die("thời lượng %s lệch dự kiến %s — không giao; file để ở %s" % (
            tc(got), tc(total), bad if not os.path.lexists(tmp) else tmp))
    try:
        os.link(tmp, args.out)  # thất bại nếu file đích vừa xuất hiện trong lúc mã hoá
        os.remove(tmp)
    except FileExistsError:
        st.die("%s vừa xuất hiện trong lúc cắt — không ghi đè; bản mới để ở %s" % (args.out, tmp))
    except OSError:
        if os.path.lexists(args.out):
            st.die("%s vừa xuất hiện trong lúc cắt — không ghi đè; bản mới để ở %s" % (args.out, tmp))
        os.replace(tmp, args.out)
    print("→ %s · %s" % (args.out, tc(got)))
    if args.srt:
        remap_to(args.srt, args.out_srt, keep)


def remap_to(src, dst, keep):
    cues, warns = remap_srt(src, keep)
    write_new(dst, st.srt(cues))
    print("%d câu → %s" % (len(cues), dst))
    for w_ in warns:
        print("Cảnh báo: " + w_)


def main(argv=None):
    st.utf8_stdio()
    ap = argparse.ArgumentParser(description="Video có kịch bản: cụm lời, phụ đề, câu đọc lại, cắt ghép bản final.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("segments", help="tách cụm lời theo khoảng ngừng, xuất từng đoạn âm thanh")
    p.add_argument("video")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--threshold", default="auto")
    p.add_argument("--min-gap", type=float, default=0.25)
    p.add_argument("--merge-gap", type=float, default=0.4)
    p.add_argument("--max-chunk", type=float, default=6.0)
    p.set_defaults(fn=cmd_segments)
    p = sub.add_parser("srt", help="dựng phụ đề từ mốc thật + lời từng đoạn")
    p.add_argument("segments")
    p.add_argument("--texts", required=True, action="append")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_srt)
    p = sub.add_parser("texts", help="đã có phụ đề → lời từng cụm theo mốc")
    p.add_argument("segments")
    p.add_argument("--from", dest="sub", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_texts)
    p = sub.add_parser("retakes", help="tìm câu đọc lại → bảng giữ/cắt")
    p.add_argument("segments")
    p.add_argument("--texts", required=True, action="append")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_retakes)
    p = sub.add_parser("cut", help="cắt mốc lẻ giây, ghép một file final")
    p.add_argument("video")
    p.add_argument("--plan", required=True)
    p.add_argument("--out")
    p.add_argument("--srt")
    p.add_argument("--out-srt")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--srt-only", action="store_true", help="chỉ dời mốc phụ đề theo PLAN, không cắt video")
    p.set_defaults(fn=cmd_cut)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
