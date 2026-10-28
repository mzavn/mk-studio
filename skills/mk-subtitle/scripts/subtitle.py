#!/usr/bin/env python3
"""Xử lý phụ đề SRT/VTT cho khâu dựng video (chỉ thư viện chuẩn, đầu ra tất định, không sửa file đầu vào).

  subtitle.py scan IN [--glossary FILE]... [--fix "sai=chuẩn"]... [--more "từ"]...
  subtitle.py fillers IN --out FILLERS.tsv [--more "từ"]...
  subtitle.py clean IN --fillers FILLERS.tsv --approve "A,F012,F020-F025" [--reject "F007"]
                       --out-srt OUT.srt --out-cuts PREFIX [--max-chars 42 --max-lines 2 --max-dur 6 --min-dur 1]
  subtitle.py export SRT --out TEXT.md
  subtitle.py build SRT --text TEXT.md --out OUT.srt
  subtitle.py check SRT [--ref REF.srt] [--lang vi|en] [--max-chars 42 --max-lines 2 --max-cps 20 --min-dur 0.7]
  subtitle.py retime SRT --cuts PREFIX.csv --out OUT.srt

Đầu vào: SRT; VTT thường; VTT tự động của YouTube (có mốc thời gian từng từ — cắt chính xác, chia lại câu).
Nhóm từ đệm: A = âm đệm giữa câu (à, ừ, ờ, ừm…) — đề xuất xoá; B = cần nghe lại (đầu/cuối câu, câu hỏi, lặp từ,
từ người dùng thêm bằng --more). Lỗi đầu vào/lệnh sai → in "Lỗi: …", thoát 1, không ghi file nào.
"""
import argparse
import csv
import hashlib
import html
import os
import re
import sys
import unicodedata

sys.dont_write_bytecode = True
HARD = {"à", "ừ", "ờ", "ừm", "ờm", "ơ", "ư", "hmm", "hm", "ừa"}
QUESTION_BEFORE = {"thế", "vậy", "sao", "hả", "à", "ư", "nhỉ", "chứ", "không"}
PUNCT = ".,;:!?…\"'“”‘’()[]{}-–—"
SENT_END = (".", "?", "!", "…")
CLAUSE_END = (",", ";", ":")
TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")
TAG = re.compile(r"<(\d{2}:\d{2}:\d{2}\.\d{3})><c>([^<]*)</c>")


def die(msg):
    print("Lỗi: " + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return unicodedata.normalize("NFC", fh.read().replace("\r\n", "\n").replace("\r", "\n"))
    except (OSError, UnicodeDecodeError) as exc:
        die("không đọc được %s: %s" % (path, exc))


def write(path, text):
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError as exc:
        die("không ghi được %s: %s" % (path, exc))


def refuse_overwrite(*paths):
    for p in paths:
        if os.path.lexists(p):
            die("%s đã có — chọn tên khác hoặc xoá file đó trước (skill không ghi đè)" % p)


def ms(text):
    m = TS.fullmatch(text.strip())
    if not m:
        die("mốc thời gian sai dạng: %s" % text.strip())
    h, mi, s, f = m.groups()
    return ((int(h or 0) * 60 + int(mi)) * 60 + int(s)) * 1000 + int(f)


def fmt(t):
    t = max(0, int(t))
    return "%02d:%02d:%02d,%03d" % (t // 3600000, t // 60000 % 60, t // 1000 % 60, t % 1000)


def norm(token):
    return token.lower().strip(PUNCT)


class Word:
    __slots__ = ("text", "start", "end", "cue", "timed", "brk")

    def __init__(self, text, start, end, cue, timed):
        self.text, self.start, self.end, self.cue, self.timed = text, start, end, cue, timed
        self.brk = False  # True: người nói đổi (dấu >> của YouTube) — luôn bắt đầu cue mới


def tidy(words):
    """Bỏ chú thích kiểu [âm nhạc] / [tiếng cười] (kể cả khi bị tách thành nhiều từ) và dấu >> đổi người nói.
    → (từ giữ lại, số chú thích đã bỏ)."""
    out, dropped, inside, brk = [], 0, False, False
    for w in words:
        w.text = html.unescape(w.text)
        if inside or w.text.startswith("["):
            if not inside:
                dropped += 1
            inside = not w.text.endswith("]")
            continue
        if w.text == ">>":
            brk = True
            continue
        w.brk, brk = brk, False
        out.append(w)
    return out, dropped


class Cue:
    __slots__ = ("start", "end", "lines")

    def __init__(self, start, end, lines):
        self.start, self.end, self.lines = start, end, lines


# ---------------------------------------------------------------- đọc file

def blocks(text):
    """→ [(start, end, [dòng chữ])] cho mọi khối có dòng thời gian (SRT và VTT).

    VTT: chỉ dòng rỗng thật mới tách khối (YouTube dùng dòng chỉ có dấu cách làm dòng chữ đầu của cue).
    """
    sep = r"\n\n+" if text.lstrip().startswith("WEBVTT") else r"\n[ \t]*\n"
    out = []
    for chunk in re.split(sep, text):
        lines = chunk.split("\n")
        for i, line in enumerate(lines):
            if "-->" in line:
                a, b = line.split("-->", 1)
                out.append((ms(a), ms(b.split()[0]), lines[i + 1:]))
                break
    return out


def load(path):
    """→ (loại, [Word], số chú thích kiểu [âm nhạc] đã bỏ). loại: youtube | srt | vtt."""
    text = read(path)
    bl = blocks(text)
    if not bl:
        die("%s không có khối phụ đề nào (cần SRT hoặc VTT)" % path)
    kind = "vtt" if text.lstrip().startswith("WEBVTT") else "srt"
    rolling = kind == "vtt" and ("<c>" in text or any(b - a <= 20 for a, b, _ in bl))
    words, dropped = [], 0
    if rolling:
        kind = "youtube"
        real = [(a, b, lines) for a, b, lines in bl if b - a > 20]
        for cue, (a, b, lines) in enumerate(real):
            new = [l for l in lines if l.strip()]
            if not new:
                continue
            last = new[-1]
            first = TAG.split(last)[0].strip()
            timed = [(a, first)] if first else []
            timed += [(ms(t), w.strip()) for t, w in TAG.findall(last)]
            if not TAG.search(last):  # dòng mới không có mốc từng từ: chia đều trong khối
                toks = re.sub(r"<[^>]+>", "", last).split()
                step = (b - a) // max(1, len(toks))
                timed = [(a + i * step, w) for i, w in enumerate(toks)]
            for t, w in timed:
                for tok in w.split():
                    words.append(Word(tok, t, None, cue, True))
        words, dropped = tidy(words)
        last_end = real[-1][1]
        for i, w in enumerate(words):
            nxt = words[i + 1].start if i + 1 < len(words) else last_end
            gap = nxt - w.start
            w.end = nxt if gap <= 1500 else w.start + 700
        return kind, words, dropped
    for cue, (a, b, lines) in enumerate(bl):
        body = " ".join(re.sub(r"<[^>]+>", "", l).strip() for l in lines if l.strip())
        toks = body.split()
        total = sum(len(t) + 1 for t in toks) or 1
        acc = 0
        for tok in toks:
            share = (b - a) * (len(tok) + 1) // total
            words.append(Word(tok, a + acc, a + acc + share, cue, False))
            acc += share
        if toks:
            words[-1].end = b
    words, dropped = tidy(words)
    return kind, words, dropped


def cues_of(path):
    """Đọc SRT ra [Cue] (cho export/build/check/retime)."""
    out = []
    for a, b, lines in blocks(read(path)):
        out.append(Cue(a, b, [l.rstrip() for l in lines if l.strip()]))
    return out


def srt(cues):
    return "".join("%d\n%s --> %s\n%s\n\n" % (i + 1, fmt(c.start), fmt(c.end), "\n".join(c.lines))
                   for i, c in enumerate(cues))


# ---------------------------------------------------------------- từ đệm

def context(words, i, width=4):
    left = " ".join(w.text for w in words[max(0, i - width):i])
    right = " ".join(w.text for w in words[i + 1:i + 1 + width])
    return ("%s [%s] %s" % (left, words[i].text, right)).strip()


def find_fillers(words, more=()):
    """→ [(nhóm, lý do, chỉ số từ)] theo thứ tự thời gian."""
    phrases = [m.lower().split() for m in more if m.strip()]
    hits, taken = [], set()
    for i, w in enumerate(words):
        n = norm(w.text)
        prev = words[i - 1] if i else None
        nxt = words[i + 1] if i + 1 < len(words) else None
        sent_start = prev is None or prev.text.endswith(SENT_END) or prev.cue != w.cue and not w.timed
        if n in HARD:
            if w.text.endswith("?") or (prev and norm(prev.text) in QUESTION_BEFORE and n in ("à", "ư")):
                hits.append(("B", "có thể là tiểu từ hỏi (thế à?, vậy ư?)", i))
            elif sent_start:
                hits.append(("B", "đầu câu hoặc ngay sau câu hỏi, có thể là câu đáp/cảm thán (Ừ đúng rồi, À thế thì)", i))
            elif n in ("à", "ơi", "ơ") and prev.text[:1].isupper():
                hits.append(("B", "sau tên riêng, có thể là tiếng gọi (Minh à)", i))
            elif w.text.endswith(SENT_END):
                hits.append(("B", "cuối câu, có thể là tiểu từ", i))
            else:
                hits.append(("A", "âm đệm giữa câu", i))
            taken.add(i)
            continue
        if prev and n and not n.isdigit() and n == norm(prev.text) and i not in taken:
            hits.append(("B", "lặp từ liền nhau (có thể là từ láy, vd dần dần)", i))
            taken.add(i)
            continue
        for p in phrases:
            seg = [norm(x.text) for x in words[i:i + len(p)]]
            if seg == p and not taken.intersection(range(i, i + len(p))):
                for k in range(i, i + len(p)):
                    hits.append(("B", "từ bạn thêm: %s" % " ".join(p), k))
                    taken.add(k)
    hits.sort(key=lambda h: h[2])
    return hits


def exactness(words, idx):
    w = words[idx]
    if w.timed:
        return "chính xác (từng từ)"
    same = [x for x in words if x.cue == w.cue]
    return "chính xác (cả cue)" if all(norm(x.text) in HARD for x in same) else "ước lượng"


def fingerprint(words):
    """Dấu vân tay của chuỗi từ đầu vào: file từ đệm chỉ dùng được cho đúng file đã quét."""
    return hashlib.sha1("\n".join("%s %d" % (w.text, w.start) for w in words).encode("utf-8")).hexdigest()[:12]


FILLER_COLS = ["ma", "nhom", "ly_do", "bat_dau", "ket_thuc", "do_chinh_xac", "tu", "vi_tri", "ngu_canh", "nguon"]


def write_fillers(path, words, hits):
    rows = [FILLER_COLS]
    src = fingerprint(words)
    for k, (group, why, i) in enumerate(hits, 1):
        w = words[i]
        rows.append(["F%03d" % k, group, why, fmt(w.start), fmt(w.end), exactness(words, i), w.text, str(i),
                     context(words, i), src])
    if not hits:
        rows.append(["-", "-", "không có từ đệm", "", "", "", "", "-1", "", src])
    try:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, delimiter="\t", lineterminator="\n").writerows(rows)
    except OSError as exc:
        die("không ghi được %s: %s" % (path, exc))


def read_table(path, delimiter):
    try:
        with open(path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            return reader.fieldnames or [], list(reader)
    except (OSError, UnicodeDecodeError) as exc:
        die("không đọc được %s: %s" % (path, exc))


def read_fillers(path, words):
    cols, rows = read_table(path, "\t")
    if cols != FILLER_COLS or not rows:
        die("%s không phải file từ đệm của lệnh fillers" % path)
    if rows[0]["nguon"] != fingerprint(words):
        die("%s không khớp file đầu vào (được tạo từ file khác hoặc file đã đổi) — chạy lại fillers trên đúng file này"
            % path)
    return [r for r in rows if r["ma"] != "-"]


def pick(rows, approve, reject):
    """Cú pháp duyệt: A, B, all, F012, F020-F025 (cách nhau bằng dấu phẩy/khoảng trắng)."""
    codes = {r["ma"] for r in rows}

    def expand(spec):
        out = set()
        for tok in re.split(r"[,\s]+", spec.strip()):
            if not tok:
                continue
            up = tok.upper()
            if up == "ALL":
                out |= codes
            elif up in ("A", "B"):
                out |= {r["ma"] for r in rows if r["nhom"] == up}
            elif re.fullmatch(r"F\d+-F?\d+", up):
                a, b = (int(x) for x in re.findall(r"\d+", up))
                out |= {"F%03d" % n for n in range(a, b + 1)} & codes
            elif re.fullmatch(r"F\d+", up):
                if "F%03d" % int(up[1:]) not in codes:
                    die("không có mã %s trong file từ đệm" % tok)
                out.add("F%03d" % int(up[1:]))
            else:
                die("không hiểu '%s' — dùng A, B, all, F012 hoặc F020-F025" % tok)
        return out

    return expand(approve) - expand(reject or "")


# ---------------------------------------------------------------- chia câu, ngắt dòng

def wrap(text, max_chars, max_lines):
    if len(text) <= max_chars or max_lines < 2:
        return [text]
    toks = text.split()
    best = None
    for k in range(1, len(toks)):
        a, b = " ".join(toks[:k]), " ".join(toks[k:])
        over = max(0, len(a) - max_chars) + max(0, len(b) - max_chars)  # vượt độ dài dòng: tránh trước tiên
        score = (over, max(len(a), len(b)) - (6 if toks[k - 1].endswith(CLAUSE_END + SENT_END) else 0))
        if best is None or score < best[0]:
            best = (score, [a, b])
    return best[1] if best else [text]


def fits(text, max_chars, max_lines):
    return all(len(line) <= max_chars for line in wrap(text, max_chars, max_lines))


def segment(words, max_chars, max_lines, max_dur, min_dur):
    """Chia từ có mốc thành cue: ngắt ở người nói đổi, quãng nghỉ ≥ 1 giây, cuối câu, khi không còn vừa
    max_lines × max_chars hoặc quá max_dur; không ngắt giữa hai từ lặp liền nhau (dần dần). Cue quá ngắn được
    ghép với cue kề bên (hai người nói → dạng hội thoại "- … / - …")."""
    groups, cur = [], []
    for w in words:
        if cur:
            prev = cur[-1]
            text = " ".join(x.text for x in cur + [w])
            hard = not fits(text, max_chars, max_lines) or w.end - cur[0].start > max_dur
            soft = (w.brk or w.start - prev.end >= 1000 or prev.text.endswith(SENT_END)
                    or prev.text.endswith(CLAUSE_END) and len(text) - len(w.text) - 1 >= max_chars)
            if hard or soft and not (norm(w.text) == norm(prev.text) and not w.brk):
                groups.append(cur)
                cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    groups = merge_short(groups, max_chars, max_lines, max_dur, min_dur)
    cues = []
    for g in groups:
        parts, part = [], []
        for w in g:
            if w.brk and part:
                parts.append(part)
                part = []
            part.append(w)
        parts.append(part)
        if len(parts) > 1:
            lines = ["- " + " ".join(w.text for w in p) for p in parts]
        else:
            lines = wrap(" ".join(w.text for w in g), max_chars, max_lines)
        cues.append(Cue(g[0].start, g[-1].end, lines))
    for i, c in enumerate(cues):
        limit = cues[i + 1].start if i + 1 < len(cues) else c.end + min_dur
        if c.end - c.start < min_dur:
            c.end = min(c.start + min_dur, limit)
        c.end = min(c.end, limit)
    return cues


def layout_ok(group, max_chars, max_lines):
    """Nhóm từ có hiển thị được trong một cue không: một người nói → ngắt dòng thường; hai người → mỗi người một dòng."""
    turns = sum(1 for k, w in enumerate(group) if k and w.brk) + 1
    if turns == 1:
        return fits(" ".join(w.text for w in group), max_chars, max_lines)
    if turns > max_lines:
        return False
    line, ok = [], True
    for k, w in enumerate(group):
        if k and w.brk:
            ok = ok and len("- " + " ".join(line)) <= max_chars
            line = []
        line.append(w.text)
    return ok and len("- " + " ".join(line)) <= max_chars


def merge_short(groups, max_chars, max_lines, max_dur, min_dur):
    """Ghép cue hiện dưới min_dur vào cue sau (ưu tiên) hoặc cue trước nếu vừa chỗ, không quá max_dur và hai cue
    cách nhau dưới 1 giây."""
    out = list(groups)
    i = 0
    while i < len(out):
        g = out[i]
        if g[-1].end - g[0].start < min_dur:
            for j in (i + 1, i - 1):
                if not 0 <= j < len(out):
                    continue
                a, b = (g, out[j]) if j > i else (out[j], g)
                joined = a + b
                if (b[0].start - a[-1].end < 1000 and joined[-1].end - joined[0].start <= max_dur
                        and layout_ok(joined, max_chars, max_lines)):
                    out[min(i, j)] = joined
                    del out[max(i, j)]
                    i = max(0, min(i, j) - 1)
                    break
            else:
                i += 1
            continue
        i += 1
    return out


def regroup(words, max_chars, max_lines, src_cues):
    """Đầu vào không có mốc từng từ: giữ ranh giới cue gốc, chỉ bỏ từ đã duyệt và ngắt dòng lại."""
    out = []
    for cue_id, (a, b) in enumerate(src_cues):
        kept = [w.text for w in words if w.cue == cue_id]
        if kept:
            out.append(Cue(a, b, wrap(" ".join(kept), max_chars, max_lines)))
    return out


# ---------------------------------------------------------------- đoạn cắt

def cut_ranges(words, removed):
    ranges = []
    for i in sorted(removed):
        w = words[i]
        exact = exactness(words, i) != "ước lượng"
        if ranges and w.start - ranges[-1]["end"] <= 50:
            r = ranges[-1]
            r["end"] = max(r["end"], w.end)
            r["ids"].append(i)
            r["exact"] = r["exact"] and exact
        else:
            ranges.append({"start": w.start, "end": w.end, "ids": [i], "exact": exact})
    return ranges


def read_cuts(path):
    cols, rows = read_table(path, ",")
    if "bat_dau" not in cols:
        die("%s không phải file cắt của lệnh clean" % path)
    return rows


def shift(t, cuts):
    """Thời điểm trên timeline gốc → timeline sau khi cắt mọi đoạn trong cuts."""
    out = t
    for a, b in cuts:
        if t >= b:
            out -= b - a
        elif t > a:
            out -= t - a
    return out


# ---------------------------------------------------------------- lệnh

def cmd_scan(args):
    kind, words, dropped = load(args.input)
    names = {"youtube": "VTT tự động YouTube (có mốc từng từ — cắt chính xác, chia lại câu)",
             "srt": "SRT (mốc theo cue — cắt từ đệm giữa câu là ước lượng)",
             "vtt": "VTT (mốc theo cue — cắt từ đệm giữa câu là ước lượng)"}
    print("# scan: %s" % args.input)
    print("Loại: %s" % names[kind])
    if words:
        print("Số từ: %d · thời lượng %s → %s" % (len(words), fmt(words[0].start), fmt(words[-1].end)))
    if dropped:
        print("Chú thích kiểu [âm nhạc] đã bỏ: %d" % dropped)
    hits = find_fillers(words, args.more)
    a = [h for h in hits if h[0] == "A"]
    b = [h for h in hits if h[0] == "B"]
    print("\n== Từ đệm")
    print("Nhóm A (âm đệm giữa câu, đề xuất xoá): %d" % len(a))
    counts = {}
    for _, _, i in a:
        counts[norm(words[i].text)] = counts.get(norm(words[i].text), 0) + 1
    if counts:
        print("  " + ", ".join("%s %d" % kv for kv in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))))
    print("Nhóm B (cần nghe lại): %d" % len(b))
    reasons = {}
    for _, why, _ in b:
        reasons[why] = reasons.get(why, 0) + 1
    for why, n in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %s: %d" % (why, n))
    fixes = []
    for g in args.glossary:
        fixes += parse_glossary(g)
    for f in args.fix:
        if "=" not in f:
            die("--fix cần dạng 'sai=chuẩn', nhận: %s" % f)
        wrong, right = f.split("=", 1)
        fixes.append(([x.strip() for x in wrong.split(",") if x.strip()], right.strip()))
    if fixes:
        print("\n== Thuật ngữ (ứng viên lỗi nhận giọng — xem ngữ cảnh trước khi sửa)")
        joined = [norm(w.text) for w in words]
        for variants, right in fixes:
            found = []
            for v in variants:
                vt = v.lower().split()
                for i in range(len(joined) - len(vt) + 1):
                    if joined[i:i + len(vt)] == vt and " ".join(w.text for w in words[i:i + len(vt)]) != right:
                        found.append((i, v))
            if found:
                where = " · ".join("%s \"%s\"" % (fmt(words[i].start), context(words, i, 3)) for i, _ in found[:3])
                print("- %s ← %s: %d · %s%s" % (right, ", ".join(sorted({v for _, v in found})), len(found), where,
                                                " …" if len(found) > 3 else ""))
    if kind != "youtube":
        cues = []
        for cue_id in sorted({w.cue for w in words}):
            ws = [w for w in words if w.cue == cue_id]
            cues.append(Cue(ws[0].start, ws[-1].end, [" ".join(w.text for w in ws)]))
        long_ = [c for c in cues if (c.end - c.start) and len(c.lines[0]) * 1000 / (c.end - c.start) > args.max_cps]
        print("\n== Nhịp đọc")
        print("Cue đọc nhanh hơn %s ký tự/giây: %d" % (args.max_cps, len(long_)))


def parse_glossary(path):
    """Bảng markdown 2 cột: | sai1, sai2 | **Chuẩn** | → [([sai…], chuẩn)]. Bỏ dòng tiêu đề và dòng kẻ."""
    out = []
    for line in read(path).split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or set(cells[0]) <= set("-: ") or not cells[0]:
            continue
        rights = [x.strip(" *") for x in cells[1].split("/") if x.strip(" *")]
        right = rights[0] if rights else ""
        ok = {x.lower() for x in rights}
        wrong = [re.sub(r"\s*\([^)]*\)", "", v).strip() for v in cells[0].split(",")]  # bỏ ghi chú "(thực thể)"
        wrong = [v for v in wrong if v and v.lower() not in ok]
        if right and wrong and not re.search(r"(?i)ghi âm sai|^sai$|chuẩn", cells[0] + "|" + cells[1].strip("* ")[:6]):
            out.append((wrong, right))
    return out


def cmd_fillers(args):
    refuse_overwrite(args.out)
    _, words, _ = load(args.input)
    hits = find_fillers(words, args.more)
    write_fillers(args.out, words, hits)
    print("%d từ đệm (A %d · B %d) → %s" % (len(hits), sum(h[0] == "A" for h in hits),
                                            sum(h[0] == "B" for h in hits), args.out))


def cmd_clean(args):
    refuse_overwrite(args.out_srt, args.out_cuts + ".srt", args.out_cuts + ".csv")
    kind, words, _ = load(args.input)
    rows = read_fillers(args.fillers, words)
    chosen = pick(rows, args.approve, args.reject)
    removed = set()
    for r in rows:
        if r["ma"] in chosen:
            i = int(r["vi_tri"])
            if i >= len(words) or words[i].text != r["tu"]:
                die("%s không khớp file đầu vào (vị trí %s) — chạy lại fillers trên đúng file này" % (r["ma"], i))
            removed.add(i)
    kept, brk = [], False
    for i, w in enumerate(words):
        if i in removed:
            brk = brk or w.brk  # từ đệm bị bỏ đang mang dấu đổi người nói → chuyển sang từ kế tiếp
            continue
        w.brk, brk = w.brk or brk, False
        kept.append(w)
    if kind == "youtube":
        cues = segment(kept, args.max_chars, args.max_lines, int(args.max_dur * 1000), int(args.min_dur * 1000))
    else:
        src = [(a, b) for a, b, _ in blocks(read(args.input))]
        cues = regroup(kept, args.max_chars, args.max_lines, src)
    ranges = cut_ranges(words, removed)
    code = {int(r["vi_tri"]): r["ma"] for r in rows}
    write(args.out_srt, srt(cues))
    write(args.out_cuts + ".srt", srt([Cue(r["start"], r["end"], ["✂ %s %s" % (
        " ".join(code[i] for i in r["ids"]), " ".join(words[i].text for i in r["ids"]))]) for r in ranges]))
    with open(args.out_cuts + ".csv", "w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["stt", "bat_dau", "ket_thuc", "do_dai_ms", "ma", "tu", "do_chinh_xac", "ngu_canh"])
        for k, r in enumerate(ranges, 1):
            wr.writerow([k, fmt(r["start"]), fmt(r["end"]), r["end"] - r["start"],
                         " ".join(code[i] for i in r["ids"]), " ".join(words[i].text for i in r["ids"]),
                         "chính xác" if r["exact"] else "ước lượng", context(words, r["ids"][0])])
    total = sum(r["end"] - r["start"] for r in ranges)
    print("Đã bỏ %d từ · %d cue → %s" % (len(removed), len(cues), args.out_srt))
    print("Đoạn cắt: %d (tổng %.1f giây, %d ước lượng) → %s.srt, %s.csv" % (
        len(ranges), total / 1000, sum(not r["exact"] for r in ranges), args.out_cuts, args.out_cuts))


def cmd_export(args):
    refuse_overwrite(args.out)
    cues = cues_of(args.input)
    write(args.out, "".join("[%d] %s --> %s\n%s\n\n" % (i + 1, fmt(c.start), fmt(c.end), "\n".join(c.lines))
                            for i, c in enumerate(cues)))
    print("%d cue → %s (sửa chữ dưới mỗi dòng [số], giữ nguyên dòng [số] và mốc thời gian)" % (len(cues), args.out))


def cmd_build(args):
    refuse_overwrite(args.out)
    cues = cues_of(args.input)
    text = read(args.text)
    parts = re.split(r"^\[(\d+)\] (\S+) --> (\S+)[ \t]*$", text, flags=re.M)
    if len(parts) < 4:
        die("%s không có khối [số] mốc --> mốc nào" % args.text)
    got = []
    for k in range(1, len(parts), 4):
        n, a, b, body = int(parts[k]), ms(parts[k + 1]), ms(parts[k + 2]), parts[k + 3]
        lines = [l.rstrip() for l in body.strip("\n").split("\n") if l.strip()]
        got.append((n, a, b, lines))
    if len(got) != len(cues):
        die("%s có %d khối, phụ đề gốc có %d cue — không thêm/bớt cue" % (args.text, len(got), len(cues)))
    changed = 0
    for idx, ((n, a, b, lines), c) in enumerate(zip(got, cues), 1):
        if n != idx:
            die("khối thứ %d mang số [%d] — giữ nguyên thứ tự và số" % (idx, n))
        if (a, b) != (c.start, c.end):
            die("cue [%d] đổi mốc thời gian (%s --> %s) — chỉ được sửa chữ" % (n, fmt(a), fmt(b)))
        if not lines:
            die("cue [%d] trống chữ" % n)
        changed += lines != c.lines
        c.lines = lines
    write(args.out, srt(cues))
    print("%d cue (%d cue đổi chữ) → %s" % (len(cues), changed, args.out))


def vietnamese(text):
    return "đ" in text.lower() or any("\u0300" <= ch <= "\u036f" for ch in unicodedata.normalize("NFD", text))


def check_cues(cues, max_chars, max_lines, max_cps, min_dur, lang=None):
    errors, warns = [], []
    for i, c in enumerate(cues, 1):
        if c.end <= c.start:
            errors.append("[%d] kết thúc không sau bắt đầu" % i)
        if i > 1 and c.start < cues[i - 2].end:
            errors.append("[%d] chồng lên cue trước (%s < %s)" % (i, fmt(c.start), fmt(cues[i - 2].end)))
        if not c.lines:
            errors.append("[%d] trống chữ" % i)
            continue
        body = " ".join(c.lines)
        if re.search(r"<[^>]+>|\[điền|\[\?\]", body):
            errors.append("[%d] còn thẻ hoặc ô chưa điền: %s" % (i, body[:60]))
        if lang == "en" and vietnamese(body):
            warns.append("[%d] còn chữ có dấu tiếng Việt (tên riêng thì bỏ qua): %s" % (i, body[:50]))
        if max_lines and len(c.lines) > max_lines:
            warns.append("[%d] %d dòng (tối đa %d)" % (i, len(c.lines), max_lines))
        for line in c.lines:
            if max_chars and len(line) > max_chars:
                warns.append("[%d] dòng %d ký tự (tối đa %d): %s" % (i, len(line), max_chars, line[:50]))
        dur = c.end - c.start
        if dur > 0 and max_cps and len(body) * 1000 / dur > max_cps:
            warns.append("[%d] %.1f ký tự/giây (tối đa %s)" % (i, len(body) * 1000 / dur, max_cps))
        if dur > 0 and min_dur and dur < min_dur:
            warns.append("[%d] hiện %.2f giây (tối thiểu %.2f)" % (i, dur / 1000, min_dur / 1000))
    return errors, warns


def cmd_check(args):
    cues = cues_of(args.input)
    if not cues:
        die("%s không có cue nào" % args.input)
    errors, warns = check_cues(cues, args.max_chars, args.max_lines, args.max_cps, int(args.min_dur * 1000), args.lang)
    if args.ref:
        ref = cues_of(args.ref)
        if len(ref) != len(cues):
            errors.append("số cue %d khác bản đối chiếu %d" % (len(cues), len(ref)))
        else:
            diff = [i for i, (a, b) in enumerate(zip(cues, ref), 1) if (a.start, a.end) != (b.start, b.end)]
            if diff:
                errors.append("mốc thời gian khác bản đối chiếu ở cue %s" % " ".join("[%d]" % i for i in diff[:10]))
    print("# check: %s · %d cue" % (args.input, len(cues)))
    for e in errors:
        print("LỖI " + e)
    for w in warns[:args.limit]:
        print("cảnh báo " + w)
    if len(warns) > args.limit:
        print("cảnh báo … còn %d dòng (thêm --limit để xem hết)" % (len(warns) - args.limit))
    print("Tổng: %d lỗi · %d cảnh báo" % (len(errors), len(warns)))
    sys.exit(1 if errors else 0)


def cmd_retime(args):
    refuse_overwrite(args.out)
    rows = read_cuts(args.cuts)
    if any(r["do_chinh_xac"] != "chính xác" for r in rows):
        die("%s có đoạn cắt ước lượng — chỉ tính lại giờ khi mọi đoạn cắt chính xác" % args.cuts)
    cuts = sorted((ms(r["bat_dau"]), ms(r["ket_thuc"])) for r in rows)
    out = []
    for c in cues_of(args.input):
        a, b = shift(c.start, cuts), shift(c.end, cuts)
        if b > a:
            out.append(Cue(a, b, c.lines))
    write(args.out, srt(out))
    print("%d cue, đã trừ %d đoạn cắt (%.1f giây) → %s" % (len(out), len(cuts), sum(b - a for a, b in cuts) / 1000,
                                                          args.out))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Xử lý phụ đề SRT/VTT cho khâu dựng video.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    fmt_opts = argparse.ArgumentParser(add_help=False)
    fmt_opts.add_argument("--max-chars", type=int, default=42)
    fmt_opts.add_argument("--max-lines", type=int, default=2)

    p = sub.add_parser("scan")
    p.add_argument("input")
    p.add_argument("--glossary", action="append", default=[])
    p.add_argument("--fix", action="append", default=[])
    p.add_argument("--more", action="append", default=[])
    p.add_argument("--max-cps", type=float, default=20)
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("fillers")
    p.add_argument("input")
    p.add_argument("--out", required=True)
    p.add_argument("--more", action="append", default=[])
    p.set_defaults(fn=cmd_fillers)

    p = sub.add_parser("clean", parents=[fmt_opts])
    p.add_argument("input")
    p.add_argument("--fillers", required=True)
    p.add_argument("--approve", required=True)
    p.add_argument("--reject", default="")
    p.add_argument("--out-srt", required=True)
    p.add_argument("--out-cuts", required=True)
    p.add_argument("--max-dur", type=float, default=6)
    p.add_argument("--min-dur", type=float, default=1)
    p.set_defaults(fn=cmd_clean)

    p = sub.add_parser("export")
    p.add_argument("input")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("build")
    p.add_argument("input")
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("check", parents=[fmt_opts])
    p.add_argument("input")
    p.add_argument("--ref")
    p.add_argument("--lang", choices=["vi", "en"])
    p.add_argument("--max-cps", type=float, default=20)
    p.add_argument("--min-dur", type=float, default=0.7)
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("retime")
    p.add_argument("input")
    p.add_argument("--cuts", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_retime)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
