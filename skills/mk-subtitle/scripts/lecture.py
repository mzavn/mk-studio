#!/usr/bin/env python3
"""Chia buổi học / bài giảng dài thành file con: tín hiệu cắt, bảng lệnh CUT/KEEP cho editor, khung bài giảng theo
file con, phụ đề riêng từng file con, kiểm file bài giảng, khảo sát âm thanh & cắt video bằng FFmpeg (chỉ thư viện
chuẩn, đầu ra tất định, không sửa đầu vào).

  lecture.py scan IN [--gap 90] [--limit 12]
  lecture.py plan IN --plan PLAN.txt [--prefix "Buổi 3"] [--min 20 --max 30 --min-case 8 --gap 90]
                     [--name MẪU] [--label MẪU] [--video-dir DIR] [--out-md SHEET.md] [--out-csv SHEET.csv]
  lecture.py split IN --plan PLAN.txt [--prefix "Buổi 3"] [--name MẪU] [--label MẪU] [--video-dir DIR]
                      [--out-md BAI.md [--style khung|khoa] [--no-notes] [--source-label NGUỒN]] [--out-srt-dir DIR]
  lecture.py lint BAI.md [--plan PLAN.txt [--prefix "Buổi 3"] [--label MẪU]] [--source IN]
  lecture.py probe-audio VIDEO [--sample-time 00:15:00]... [--duration 30] [--course-dir DIR]
  lecture.py cut-video VIDEO --plan PLAN.txt [--prefix "Buổi 3"] --out-dir DIR [--name MẪU] [--label MẪU]
                       [--mode auto|copy|balance|master] [--dry-run]

IN: bản chép lời có mốc ở đầu dòng "[mm:ss] câu" / "[h:mm:ss] câu" (TXT/MD, vd bản chép lời YouTube), SRT hoặc VTT.
PLAN: mỗi dòng "bắt đầu | CUT hoặc KEEP | mã | tiêu đề | ghi chú"; dòng cuối "kết thúc | END". Dòng trống và dòng
bắt đầu bằng # bị bỏ qua. Mỗi phân đoạn kéo tới mốc bắt đầu của dòng sau, nên không có khoảng hở hay chồng lấn.
Tên file con (cột bảng editor, SRT con, video con) dùng một mẫu: --name "{prefix}_P{n:02} - {title}", không có thì
suy từ file video có sẵn (--video-dir; cut-video: --out-dir), không có nữa thì "{prefix}-P{n} - {title}". Nhãn hiển
thị (tiêu đề, mục lục): --label "{prefix} · P{n:02}", mặc định "<tiền tố>:P1".
cut-video: kế hoạch vượt thời lượng video → LỖI, không cắt; cắt vào thư mục tạm trong DIR, kiểm ffprobe (thời lượng
±1 giây, có hình + tiếng) rồi mới đặt tên thật; file hỏng → LỖI, không giao.
Thoát: 0 xong/qua (có thể kèm dòng "Cảnh báo:"); 1 lỗi đầu vào hoặc có dòng "LỖI:" — khi đó không ghi file nào
(cut-video: các file con đã kiểm và giao trước file hỏng vẫn giữ).
"""
import argparse
import csv
import io
import json
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subtitle as st  # noqa: E402  (read, die, blocks, load, srt, Cue)

LINE_TS = re.compile(r"^\s*\**\[(?:(\d+):)?(\d{1,2}):(\d{2})\]\**\s*(.*)$")
HMS = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")
CODE = re.compile(r"^P(\d+)(?:\.(\d+))?$")
FORBIDDEN = re.compile(r'[\\/:*?"<>|]')
HEADER = re.compile(r"^###\s*🎬\s*(.+?)\s*\[\s*([\d:]+)\s*-\s*([\d:]+)\s*\]")
QA = re.compile(r"\[(A|B)\s+(Hỏi|Đáp|Khai Tuệ|Đúc Kết)", re.I)
CALLOUT = re.compile(r"^\s*>\s*\[!([^\]]*)\]")
CALLOUTS = {"note", "abstract", "summary", "tldr", "info", "todo", "tip", "hint", "important", "success", "check",
            "done", "question", "help", "faq", "warning", "caution", "attention", "failure", "fail", "missing",
            "danger", "error", "bug", "example", "quote", "cite"}
SIGNALS = [
    ("Thủ tục / đầu giờ", [r"\bmic\b", r"\bmicro\b", r"nghe rõ", r"nghe (được|thấy) không", r"camera", r"điểm danh",
                           r"nội quy", r"vắng mặt", r"chào cả lớp", r"vào lớp", r"đến giờ", r"chia sẻ màn hình",
                           r"ghi hình", r"\bzoom\b", r"mất tiếng", r"tắt (mic|âm)"]),
    ("Giải lao", [r"giải lao", r"nghỉ (một|1) (chút|lát|tí)", r"nghỉ (\d+|năm|mười|mươi) phút",
                  r"(quay|trở) lại lớp", r"vào lại lớp", r"quay lại (đi|nhé|nha)"]),
    ("Vấn đáp", [r"cho (em|tôi|con|cháu|mình) hỏi", r"xin hỏi", r"câu hỏi", r"(ai|bạn nào|em nào) (có )?hỏi",
                 r"thầy ơi", r"cô ơi", r"hỏi thầy", r"hỏi cô"]),
    ("Kết buổi", [r"bế mạc", r"kết thúc buổi", r"hẹn gặp lại", r"buổi (sau|tới)", r"ngủ ngon", r"làm lễ"]),
]


class Line:
    __slots__ = ("start", "end", "text", "raw")

    def __init__(self, start, end, text, raw=None):
        self.start, self.end, self.text, self.raw = start, end, text, raw


# ---------------------------------------------------------------- thời gian

def hms_ms(text):
    m = HMS.match(text.strip())
    if not m or int(m.group(2)) >= 60 and m.group(1) or int(m.group(3)) >= 60:
        return None
    return ((int(m.group(1) or 0) * 60 + int(m.group(2))) * 60 + int(m.group(3))) * 1000


def long_(t):
    s = t // 1000
    return "%02d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60)


def short(t):
    s = t // 1000
    return "%d:%02d:%02d" % (s // 3600, s // 60 % 60, s % 60) if s >= 3600 else "%02d:%02d" % (s // 60, s % 60)


def dur(t):
    s = t // 1000
    return "%dp %02ds" % (s // 60, s % 60)


def ceil_s(t):
    return -(-t // 1000) * 1000


# ---------------------------------------------------------------- đọc đầu vào

def load_lines(path):
    """→ (loại, [Line]). loại: txt | srt | vtt | youtube. Line.end = None ở dòng cuối của TXT."""
    text = st.read(path)
    if "-->" in text:
        kind, words, _ = st.load(path)
        if kind == "youtube":
            out = []
            for w in words:
                if out and out[-1][0] == w.cue:
                    out[-1][1].append(w)
                else:
                    out.append((w.cue, [w]))
            lines = [Line(ws[0].start, ws[-1].end, " ".join((">> " if w.brk else "") + w.text for w in ws))
                     for _, ws in out]
        else:
            lines = []
            for a, b, body in st.blocks(text):
                raw = [ln.rstrip() for ln in body if ln.strip()]
                plain = " ".join(re.sub(r"<[^>]+>", "", ln).strip() for ln in raw)
                if plain:
                    lines.append(Line(a, b, plain, raw))
    else:
        kind, lines = "txt", []
        for row in text.split("\n"):
            m = LINE_TS.match(row)
            if m:
                h, mi, s = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
                lines.append(Line(((h * 60 + mi) * 60 + s) * 1000, None, m.group(4).strip()))
            elif lines and row.strip() and not re.match(r"\s*(#|>|\||---|```)", row):
                lines[-1].text = (lines[-1].text + " " + row.strip()).strip()
        for i in range(len(lines) - 1):
            lines[i].end = lines[i + 1].start
    if not lines:
        st.die("%s không có dòng nào có mốc thời gian (cần '[mm:ss] câu', SRT hoặc VTT)" % path)
    for i in range(1, len(lines)):
        if lines[i].start < lines[i - 1].start:
            st.die("%s: mốc thời gian lùi ở [%s] sau [%s]" % (path, short(lines[i].start), short(lines[i - 1].start)))
    return kind, lines


def gap_of(kind, a, b):
    return b.start - (a.start if kind == "txt" or a.end is None else a.end)


# ---------------------------------------------------------------- kế hoạch cắt

def label(prefix, code):
    return "%s:%s" % (prefix, code) if prefix else code


def check_label(args):
    tpl = getattr(args, "label", None)
    return check_template(tpl, "--label", LABEL_FIELDS, LABEL_FORBIDDEN, "mẫu nhãn hiển thị") if tpl else None


def parse_plan(path, prefix, lines=None, kind=None, opts=None, label_tpl=None):
    """→ (segments, end, errors, warns). segment: dict(n, start, end, cmd, code, title, note, label)."""
    errors, warns, segs, end, end_n = [], [], [], None, None
    for n, row in enumerate(st.read(path).split("\n"), 1):
        if not row.strip() or row.lstrip().startswith("#"):
            continue
        cells = [c.strip() for c in row.split("|")]
        where = "%s:%d" % (path, n)
        t = hms_ms(cells[0])
        if t is None:
            errors.append("%s: mốc '%s' sai dạng (cần hh:mm:ss hoặc mm:ss)" % (where, cells[0]))
            continue
        cmd = cells[1].upper() if len(cells) > 1 else ""
        if end is not None:
            errors.append("%s: có dòng sau END" % where)
            continue
        if cmd == "END":
            end, end_n = t, n
            continue
        if cmd not in ("CUT", "KEEP"):
            errors.append("%s: lệnh '%s' — chỉ nhận CUT, KEEP, END" % (where, cells[1] if len(cells) > 1 else ""))
            continue
        code, title, note = (cells + ["", "", ""])[2:5]
        if cmd == "CUT":
            note = note or title
            title = ""
            seg = {"n": n, "start": t, "cmd": cmd, "code": code or "Cắt", "title": title, "note": note}
            if not note:
                errors.append("%s: CUT thiếu lý do (cột ghi chú)" % where)
        else:
            seg = {"n": n, "start": t, "cmd": cmd, "code": code, "title": title, "note": note}
            if not CODE.match(code):
                errors.append("%s: mã KEEP '%s' sai dạng (P1, P2… hoặc P5.1 cho ca vấn đáp)" % (where, code))
            elif any(s["code"] == code for s in segs if s["cmd"] == "KEEP"):
                errors.append("%s: mã %s trùng" % (where, code))
            if not title:
                errors.append("%s: KEEP %s thiếu tiêu đề" % (where, code))
            seg["label"] = render_label(label_tpl, prefix, code) if CODE.match(code) else label(prefix, code)
        if segs and t <= segs[-1]["start"]:
            errors.append("%s: %s không sau mốc dòng trước (%s)" % (where, long_(t), long_(segs[-1]["start"])))
        segs.append(seg)
    if not segs:
        errors.append("%s: không có dòng CUT/KEEP nào" % path)
        return segs, end, errors, warns
    if segs[0]["start"] != 0:
        errors.append("%s:%d: dòng đầu phải bắt đầu 00:00:00 — mọi giây của video cần lệnh CUT hoặc KEEP"
                      % (path, segs[0]["n"]))
    if lines is not None:
        last = lines[-1]
        if end is None:
            if kind == "txt":
                errors.append("%s: thiếu dòng 'hh:mm:ss | END' — bản chép lời không cho biết video kết thúc lúc nào"
                              % path)
            else:
                end = ceil_s(last.end)
        if end is not None and end < last.start:
            errors.append("%s:%s: END %s trước câu cuối [%s] — phần sau END không có lệnh"
                          % (path, end_n or "-", long_(end), short(last.start)))
    if end is not None and end <= segs[-1]["start"]:
        errors.append("%s:%s: END %s không sau phân đoạn cuối" % (path, end_n or "-", long_(end)))
    for i, s in enumerate(segs):
        s["end"] = segs[i + 1]["start"] if i + 1 < len(segs) else end
    if errors or lines is None:
        return segs, end, errors, warns
    o = opts
    for s in segs[1:] + [{"n": end_n, "start": end}]:
        t = s["start"]
        for ln in lines:
            if ln.end is None:
                continue
            pad = 0 if kind == "txt" else 500
            if ln.start + pad < t < ln.end - pad:
                warns.append("%s:%s: %s rơi giữa câu [%s] (%s–%s) — editor sẽ cắt giữa câu; dời về %s hoặc %s"
                             % (path, s["n"] or "-", long_(t), short(ln.start), short(ln.start), short(ln.end),
                                long_(ln.start - ln.start % 1000), long_(ceil_s(ln.end))))
                break
    prev = None
    for s in segs:
        if s["cmd"] != "KEEP":
            continue
        m = CODE.match(s["code"])
        num = (int(m.group(1)), int(m.group(2) or 0))
        if prev and num <= prev:
            warns.append("%s:%d: mã %s không tăng dần so với phân đoạn KEEP trước" % (path, s["n"], s["code"]))
        prev = num
        length = s["end"] - s["start"]
        lo = (o.min_case if m.group(2) else o.min) * 60000
        if length < lo or length > o.max * 60000:
            warns.append("%s:%d: %s dài %s — ngoài khoảng %d–%d phút" % (
                path, s["n"], s["label"], dur(length), lo // 60000, o.max))
        inside = [ln for ln in lines if s["start"] <= ln.start < s["end"]]
        thresh = max(o.gap * 1000, 300000) if kind == "txt" else o.gap * 1000
        for a, b in zip(inside, inside[1:]):
            if gap_of(kind, a, b) >= thresh:
                warns.append("%s:%d: %s có quãng lặng %s từ [%s] tới [%s] — giải lao / mất tiếng? tách thành CUT"
                             % (path, s["n"], s["label"], dur(gap_of(kind, a, b)), short(a.start), short(b.start)))
    return segs, end, errors, warns


def plan_or_die(args, lines, kind):
    ltpl = check_label(args)
    segs, end, errors, warns = parse_plan(args.plan, args.prefix, lines, kind, args, label_tpl=ltpl)
    for e in errors:
        print("LỖI: " + e)
    if errors:
        print("Kết quả: %d lỗi — chưa ghi file nào" % len(errors))
        sys.exit(1)
    resolve_names(args, segs, args.video_dir)
    return segs, end, warns


def stats(segs, end):
    cut = [s for s in segs if s["cmd"] == "CUT"]
    cut_ms = sum(s["end"] - s["start"] for s in cut)
    return {"total": end, "cut": cut_ms, "kept": end - cut_ms, "cuts": cut,
            "parts": sum(s["cmd"] == "KEEP" for s in segs)}


def source_label(args):
    return getattr(args, "source_label", None) or os.path.basename(args.input)


def cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def sheet_md(segs, end):
    k = stats(segs, end)
    out = ["### ⏱️ Bảng lệnh cắt file con (Editor Action Sheet)", "",
           "Gốc **%s** · cắt **%s** (%d đoạn) · giữ **%s** · **%d file con**" % (
               dur(k["total"]), dur(k["cut"]), len(k["cuts"]), dur(k["kept"]), k["parts"]), "",
           "| Phân đoạn | Timecode video gốc | Lệnh | Thời lượng | Tên file con | Ghi chú cắt & điểm nối |",
           "| :--- | :---: | :---: | :---: | :--- | :--- |"]
    for s in segs:
        span = "`%s - %s`" % (long_(s["start"]), long_(s["end"] - 1000))
        if s["cmd"] == "CUT":
            out.append("| **%s** | %s | 🛑 **CẮT BỎ (CUT)** | %s | *Nhiễu: %s* | %s |" % (
                cell(s["code"]), span, dur(s["end"] - s["start"]), cell(s["code"]), cell(s["note"])))
        else:
            out.append("| **%s** | %s | 🟢 **GIỮ LẠI (KEEP)** | %s | **%s** | %s |" % (
                s["code"], span, dur(s["end"] - s["start"]), cell(s["file"]), cell(s["note"])))
    return "\n".join(out) + "\n"


def sheet_csv(segs):
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(["stt", "lenh", "ma", "nhan", "ten_file", "bat_dau", "ket_thuc", "thoi_luong_giay", "tieu_de",
                 "ghi_chu"])
    for i, s in enumerate(segs, 1):
        keep = s["cmd"] == "KEEP"
        wr.writerow([i, s["cmd"], s["code"], s["label"] if keep else "", s["file"] if keep else "",
                     long_(s["start"]), long_(s["end"] - 1000), (s["end"] - s["start"]) // 1000,
                     s["title"], s["note"]])
    return buf.getvalue()


def log_row(prefix, segs, end):
    """Dòng nhật ký khoá (bảng tổng kết các buổi) — không phải luật KAIZEN.md."""
    k = stats(segs, end)
    detail = " + ".join("%s %s" % (s["code"], dur(s["end"] - s["start"])) for s in k["cuts"]) or "không cắt"
    return "| **%s** | {{chủ đề}} | %s | **%s** (%s) | **%s** | %d file con | {{điểm nhấn}} |" % (
        prefix or "{{buổi}}", dur(k["total"]), dur(k["cut"]), detail, dur(k["kept"]), k["parts"])


# ---------------------------------------------------------------- ghi file

def refuse(*paths):
    for p in paths:
        if p and os.path.lexists(p):
            st.die("%s đã có — chọn tên khác hoặc xoá file đó trước (skill không ghi đè)" % p)


def write_new(path, text):
    try:
        with open(path, "x", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError as exc:
        st.die("không ghi được %s: %s" % (path, exc))


# ---------------------------------------------------------------- lệnh

def cmd_scan(args):
    kind, lines = load_lines(args.input)
    names = {"txt": "bản chép lời có mốc đầu dòng (mốc theo đoạn — điểm cắt nên trùng mốc đầu đoạn)",
             "srt": "SRT", "vtt": "VTT", "youtube": "VTT tự động YouTube"}
    print("# scan: %s" % args.input)
    print("Loại: %s · %d dòng có mốc" % (names[kind], len(lines)))
    if kind == "txt":
        print("Thời lượng: [%s] → [%s] (video dài ít nhất tới mốc cuối; ghi END theo video)"
              % (short(lines[0].start), short(lines[-1].start)))
    else:
        print("Thời lượng: %s → %s" % (long_(lines[0].start), long_(ceil_s(lines[-1].end))))
    for name, pats in SIGNALS:
        rx = re.compile("|".join("(?:%s)" % p for p in pats), re.I)
        hits = []
        for ln in lines:
            m = rx.search(ln.text)
            if m:
                a = max(0, m.start() - 40)
                hits.append("  [%s] %s: …%s…" % (short(ln.start), m.group(0).lower(), ln.text[a:m.end() + 40]))
        print("\n== %s: %d dòng" % (name, len(hits)))
        for h in hits[:args.limit]:
            print(h)
        if len(hits) > args.limit:
            print("  … còn %d dòng (thêm --limit để xem hết)" % (len(hits) - args.limit))
    thresh = max(args.gap * 1000, 300000) if kind == "txt" else args.gap * 1000
    gaps = [(a, b) for a, b in zip(lines, lines[1:]) if gap_of(kind, a, b) >= thresh]
    print("\n== Quãng lặng ≥ %d giây: %d" % (thresh // 1000, len(gaps)))
    for a, b in gaps:
        print("  [%s] → [%s] (%s)" % (short(a.start), short(b.start), dur(gap_of(kind, a, b))))
    print("\nTín hiệu là gợi ý theo từ khoá — đọc ngữ cảnh trước khi đề xuất CUT.")


def cmd_plan(args):
    refuse(args.out_md, args.out_csv)
    kind, lines = load_lines(args.input)
    segs, end, warns = plan_or_die(args, lines, kind)
    for w in warns:
        print("Cảnh báo: " + w)
    for s in segs:
        print("%-4s %s - %s  %8s  %s" % (s["cmd"], long_(s["start"]), long_(s["end"] - 1000),
                                         dur(s["end"] - s["start"]),
                                         ("%s - %s" % (s["label"], s["title"])) if s["cmd"] == "KEEP"
                                         else "%s: %s" % (s["code"], s["note"])))
    k = stats(segs, end)
    print("Gốc %s · cắt %s (%d đoạn) · giữ %s · %d file con" % (
        dur(k["total"]), dur(k["cut"]), len(k["cuts"]), dur(k["kept"]), k["parts"]))
    print("Dòng nhật ký khoá: " + log_row(args.prefix, segs, end))
    if args.out_md:
        write_new(args.out_md, sheet_md(segs, end))
        print("→ %s" % args.out_md)
    if args.out_csv:
        write_new(args.out_csv, sheet_csv(segs))
        print("→ %s" % args.out_csv)
    print("Kết quả: 0 lỗi · %d cảnh báo" % len(warns))


def lecture_md(args, segs, end, lines):
    k = stats(segs, end)
    notes = not args.no_notes
    out = ["# {{điền: tên khoá — buổi — chủ đề chính}}", "",
           "> **Nguồn:** `%s` · gốc %s · giữ %s · %d file con  " % (
               source_label(args), dur(k["total"]), dur(k["kept"]), k["parts"]),
           "> **Người giảng:** {{điền: tên người giảng}}  ",
           "> **Chủ đề chính:** {{điền: một câu}}", "", "---", "", "## 🎬 Chỉ dẫn cho editor", "",
           "> [!IMPORTANT] Quy tắc cắt dựng",
           "> 1. Cắt bỏ mọi đoạn 🛑 CUT, nối liền đoạn trước và sau (ripple delete).",
           "> 2. Mỗi đoạn 🟢 KEEP xuất thành một file con, đặt tên theo cột *Tên file con*.",
           "> 3. Vấn đáp giữ đủ cả hai phía: người hỏi (bối cảnh) và người giảng (lời đáp).", "",
           sheet_md(segs, end).rstrip("\n"), "", "---", ""]
    if notes:
        out += ["## I. Tổng quan & mục tiêu buổi học", "", "{{điền: 4–8 gạch đầu dòng}}", "",
                "## II. Nguyên lý & khái niệm cốt lõi", "", "{{điền: khái niệm, bảng nếu cần}}", "", "---", ""]
    out += ["## III. Nội dung chi tiết theo file con", ""]
    for s in segs:
        body = ["[%s] %s" % (short(ln.start), ln.text) for ln in lines if s["start"] <= ln.start < s["end"]]
        span = "[%s - %s]" % (short(s["start"]), short(s["end"] - 1000))
        if s["cmd"] == "CUT":
            out += ["### 🛑 %s %s — CẮT BỎ" % (span, s["code"]), "",
                    "> [!CAUTION]- Lệnh editor: CẮT BỎ (CUT) · %s" % dur(s["end"] - s["start"]),
                    "> Lý do: %s" % s["note"]]
            if body:
                out += [">"] + ["> " + b for b in body]
            out += ["", "---", ""]
        else:
            out += ["### 🎬 %s %s %s" % (s["label"], span, s["title"]), "",
                    "> [!NOTE] Điểm cắt: vào `%s` · ra `%s` · %s" % (
                        long_(s["start"]), long_(s["end"] - 1000), dur(s["end"] - s["start"]))]
            if s["note"]:
                out.append("> " + s["note"])
            out.append("")
            for b in body:
                out += [b, ""]
    if notes:
        while out and out[-1] in ("", "---"):
            out.pop()
        out += ["", "---", "", "## IV. Bài học & ứng dụng", "", "{{điền}}", "", "## V. Thuật ngữ", "",
                "| Thuật ngữ | Nghĩa trong buổi học |", "| :--- | :--- |", "| {{điền}} | {{điền}} |"]
    return "\n".join(out).rstrip("\n") + "\n"


def course_turns(ln):
    """Một dòng chép lời → khối chuẩn khoá: mốc in đậm, mỗi lượt '>>' một dòng '> 🗣️' riêng."""
    parts = [p.strip() for p in re.split(r"\s*>>\s*", ln.text)]
    first, rest = parts[0], [p for p in parts[1:] if p]
    stamp = "**[%s]**" % short(ln.start)
    if first:
        head = "%s %s" % (stamp, first)
    elif rest:
        head = "%s > 🗣️ %s" % (stamp, rest.pop(0))
    else:
        head = stamp
    return [head] + ["> 🗣️ " + p for p in rest]


def course_md(args, segs, end, lines):
    """Khuôn chuẩn khoá (như file bài giảng mẫu của khoá): bảng editor, mục I–V, toàn văn có mục lục [!ABSTRACT]."""
    k = stats(segs, end)
    out = ["# {{điền: tên khoá — buổi — chủ đề chính}}", "",
           "> **Giảng viên:** {{điền: tên người giảng}}  ",
           "> **Chủ đề chính:** {{điền: một câu}}", "", "---", "",
           "## 🎬 BẢNG CHỈ DẪN KỸ THUẬT DÀNH CHO EDITOR (TIMECODE & PRODUCTION SPEC)", "",
           "> [!IMPORTANT]", "> **QUY TẮC CẮT DỰNG VIDEO CHUẨN:**",
           "> 1. Cắt bỏ mọi đoạn 🛑 CUT, nối liền đoạn trước và sau (ripple delete).",
           "> 2. Mỗi đoạn 🟢 KEEP xuất thành một file con, đặt tên theo cột *Tên file con*.",
           "> 3. Vấn đáp giữ đủ cả hai phía: người hỏi (bối cảnh) và người giảng (lời đáp).", "",
           sheet_md(segs, end).rstrip("\n"), "", "---", ""]
    if not args.no_notes:
        out += ["## I. Tổng quan & Mục tiêu buổi học", "", "{{điền: 4–8 gạch đầu dòng}}", "",
                "## II. Các nguyên lý & Khái niệm cốt lõi", "", "{{điền: khái niệm, bảng nếu cần}}", "",
                "## III. Nội dung chi tiết bài giảng", "", "{{điền: tóm tắt theo chủ đề}}", "",
                "## IV. Bài học, Ứng dụng & Chiêm nghiệm thực tiễn", "", "{{điền}}", "",
                "## V. Thuật ngữ & Lưu ý quan trọng", "", "| Thuật ngữ | Nghĩa trong buổi học |", "| :--- | :--- |",
                "| {{điền}} | {{điền}} |", "", "---", ""]
    toc, n = [], 0
    for s in segs:
        if s["cmd"] == "CUT":
            toc.append("> • **🛑 [%s - %s]:** %s: %s *(LỆNH: CẮT BỎ TOÀN BỘ)*" % (
                long_(s["start"]), long_(s["end"] - 1000), s["code"], s["note"]))
        else:
            n += 1
            toc.append("> %d. **%s [%s - %s]:** %s" % (n, s["label"], short(s["start"]), short(s["end"] - 1000),
                                                     s["title"]))
    out += ["## 📖 Toàn văn phụ đề / Transcript chi tiết (Chuẩn Markdown)", "",
            "> [!NOTE] Thông tin bản ghi",
            "> - **File nguồn:** `%s`" % source_label(args),
            "> - **Thời lượng:** gốc %s · cắt %s · giữ %s · %d file con" % (
                dur(k["total"]), dur(k["cut"]), dur(k["kept"]), k["parts"]), "",
            "> [!ABSTRACT] Mục lục %d file con (Topic-First dành cho Editor)" % k["parts"]] + toc + ["", "---", ""]
    for s in segs:
        if s["cmd"] == "CUT":
            out += ["### 🛑 [%s - %s] %s (EDITOR: CẮT BỎ TOÀN BỘ)" % (
                long_(s["start"]), long_(s["end"] - 1000), ("%s: %s" % (s["code"], s["note"])).upper()), "",
                    "> [!WARNING] Lệnh Editor: CẮT BỎ (CUT)", "> " + s["note"], "", "---", ""]
        else:
            out += ["### 🎬 %s [%s - %s] %s" % (s["label"], short(s["start"]), short(s["end"] - 1000), s["title"]),
                    "", "> [!NOTE] Lệnh Editor: GIỮ LẠI (KEEP)"]
            if s["note"]:
                out.append("> " + s["note"])
            out += ["> Điểm cắt: vào `%s` · ra `%s` · %s" % (long_(s["start"]), long_(s["end"] - 1000),
                                                              dur(s["end"] - s["start"])), ""]
        for ln in lines:
            if s["start"] <= ln.start < s["end"]:
                for row in course_turns(ln):
                    out += [row, ""]
        out += ["---", ""]
    while out and out[-1] in ("", "---"):
        out.pop()
    return "\n".join(out) + "\n"


def cmd_split(args):
    if not args.out_md and not args.out_srt_dir:
        st.die("cần --out-md hoặc --out-srt-dir")
    refuse(args.out_md, args.out_srt_dir)
    kind, lines = load_lines(args.input)
    if args.out_srt_dir and kind not in ("srt", "vtt"):
        st.die("phụ đề từng file con cần SRT/VTT thường (%s không có mốc kết thúc từng câu hoặc là VTT cuộn của "
               "YouTube) — làm mode phụ đề trước rồi dùng file .srt đã sạch" % args.input)
    segs, end, warns = plan_or_die(args, lines, kind)
    for w in warns:
        print("Cảnh báo: " + w)
    if args.out_md:
        write_new(args.out_md, (course_md if args.style == "khoa" else lecture_md)(args, segs, end, lines))
        print("%s → %s (điền mọi chỗ {{điền…}}, rồi chạy lint)" % (
            "Bài giảng chuẩn khoá" if args.style == "khoa" else "Khung bài giảng", args.out_md))
    if args.out_srt_dir:
        try:
            os.mkdir(args.out_srt_dir)
        except OSError as exc:
            st.die("không tạo được %s: %s" % (args.out_srt_dir, exc))
        for s in segs:
            if s["cmd"] != "KEEP":
                continue
            a, b = s["start"], s["end"]
            cues = [st.Cue(max(ln.start, a) - a, min(ln.end, b) - a, ln.raw)
                    for ln in lines if ln.end > a and ln.start < b and min(ln.end, b) > max(ln.start, a)]
            name = os.path.join(args.out_srt_dir, s["file"] + ".srt")
            write_new(name, st.srt(cues))
            print("%s: %d cue (%s) → %s" % (s["label"], len(cues), dur(b - a), name))
    print("Kết quả: 0 lỗi · %d cảnh báo" % len(warns))


def tc_ok(tc):
    parts = [int(p) for p in tc.split(":")]
    return all(p < 60 for p in parts[1:])


def cmd_lint(args):
    text = st.read(args.input)
    rows = text.split("\n")
    errs, fence, headers, pending, stamps = [], None, [], None, set()

    def err(n, msg):
        errs.append("%s:%d: %s" % (args.input, n, msg))

    def close_pending():
        if pending:
            n, kind_, stage = pending
            err(n, "[A Hỏi] chưa có [B Đáp] đi kèm" if kind_ == "AB" else
                "đối thoại [B Hỏi] thiếu %s" % ("[A Đáp]" if stage == 0 else "[B Khai Tuệ] / [B Đúc Kết]"))

    for n, line in enumerate(rows, 1):
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            if fence is None:
                fence = (s[:3], n)
            elif s[:3] == fence[0]:
                fence = None
            continue
        if fence:
            continue
        m = CALLOUT.match(line)
        if m and m.group(1).strip().rstrip("+-").lower() not in CALLOUTS:
            err(n, "callout [!%s] không phải loại hợp lệ" % m.group(1))
        if "{{điền" in line:
            err(n, "còn chỗ chưa điền: %s" % s[:60])
        for span in re.findall(r"\[([^\]\n]*)\]|`([^`\n]*)`", line):
            for tc in re.findall(r"(?<![\d:])(\d{1,3}(?::\d{2}){1,2})(?![\d:])", span[0] or span[1]):
                if not tc_ok(tc):
                    err(n, "mốc %s sai (phút/giây phải dưới 60)" % tc)
        for tc in re.findall(r"\[((?:\d+:)?\d{1,2}:\d{2})\]", line):
            if tc_ok(tc):
                stamps.add(hms_ms(tc))
        h = HEADER.match(s)
        if s.startswith("#"):
            close_pending()
            pending = None
        if h:
            a, b = hms_ms(h.group(2)), hms_ms(h.group(3))
            if a is None or b is None or b < a:
                err(n, "tiêu đề file con có khoảng thời gian sai: [%s - %s]" % (h.group(2), h.group(3)))
            else:
                if headers and a <= headers[-1][2]:
                    err(n, "%s [%s - %s] chồng lên file con trước" % (h.group(1), h.group(2), h.group(3)))
                headers.append((h.group(1), a, b, n))
        for who, what in QA.findall(line):
            tag = "%s %s" % (who.upper(), what.lower())
            if tag == "A hỏi" or tag == "B hỏi":
                close_pending()
                pending = (n, "AB" if tag == "A hỏi" else "SOC", 0)
            elif pending and pending[1] == "AB" and tag == "B đáp":
                pending = None
            elif pending and pending[1] == "SOC" and pending[2] == 0 and tag == "A đáp":
                pending = (pending[0], "SOC", 1)
            elif pending and pending[1] == "SOC" and pending[2] == 1 and tag in ("B khai tuệ", "B đúc kết"):
                pending = None
    close_pending()
    if fence:
        err(fence[1], "khối code mở bằng %s chưa đóng" % fence[0])
    if args.plan:
        segs, end, perrs, _ = parse_plan(args.plan, args.prefix, label_tpl=check_label(args))
        if perrs:
            errs.extend(perrs)
        else:
            keep = [s for s in segs if s["cmd"] == "KEEP"]
            got = {h[0]: h for h in headers}
            for s in keep:
                h = got.get(s["label"])
                if not h:
                    errs.append("%s: thiếu tiêu đề '### 🎬 %s [..]' cho file con" % (args.input, s["label"]))
                    continue
                want_end = s["end"] - 1000 if s["end"] is not None else h[2]
                if (h[1], h[2]) != (s["start"], want_end):
                    err(h[3], "%s ghi [%s - %s], kế hoạch là [%s - %s]" % (
                        s["label"], short(h[1]), short(h[2]), short(s["start"]), short(want_end)))
                if not any(r.startswith("| **%s** |" % s["code"]) for r in rows):
                    errs.append("%s: bảng lệnh thiếu dòng của %s" % (args.input, s["label"]))
            for name, _, _, n in headers:
                if name not in {s["label"] for s in keep}:
                    err(n, "file con %s không có trong kế hoạch" % name)
    if args.source:
        _, lines = load_lines(args.source)
        lost = sorted({ln.start - ln.start % 1000 for ln in lines} - stamps)
        if lost:
            errs.append("%s: %d mốc của bản gốc không còn trong file (mất đoạn?): %s" % (
                args.input, len(lost), ", ".join("[%s]" % short(t) for t in lost[:8]) + (" …" if len(lost) > 8 else "")))
    for e in errs:
        print("LỖI: " + e)
    print("%s: %d dòng · %d file con · %d lỗi" % (args.input, len(rows), len(headers), len(errs)))
    print("Kết quả: %s" % ("0 lỗi" if not errs else "%d lỗi" % len(errs)))
    sys.exit(1 if errs else 0)


# ---------------------------------------------------------------- âm thanh & cắt video

def check_tools(*names):
    for name in names:
        if not shutil.which(name):
            st.die("cần công cụ '%s' trong PATH để xử lý video/âm thanh — cài ffmpeg: brew install ffmpeg (macOS), "
                   "winget install Gyan.FFmpeg (Windows), rồi mở lại terminal" % name)


QUIET_LUFS = -24.0     # cả file nhỏ hơn mức này → master
IMBALANCE_DB = 4.0     # lệch kênh từ mức này → balance
SILENT_DB = -45.0      # mẫu có kênh to nhất dưới mức này → coi như im lặng, bỏ qua


def channel_rms(stderr):
    """Đọc dòng RMS từng kênh của astats (thứ tự Channel 1, 2…). -inf → float('-inf')."""
    out = []
    for block in re.split(r"Channel:\s*\d+", stderr.split("Overall")[0])[1:]:
        m = re.search(r"RMS level dB:\s*(-?inf|[-\d.]+)", block, re.I)
        if m:
            out.append(float("-inf") if "inf" in m.group(1).lower() else float(m.group(1)))
    return out


def ffmpeg_audio(video, af, pre=()):
    cmd = ["ffmpeg", "-hide_banner", "-nostats"] + list(pre) + ["-i", os.path.abspath(video), "-map", "0:a:0", "-vn", "-sn", "-dn",
                                                                 "-af", af, "-f", "null", "-"]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


BORDERLINE_LU = 1.0   # cách ngưỡng −24 LUFS trong khoảng này → chế độ có thể lật, cảnh báo
BORDERLINE_MSG = ("độ to sát ngưỡng %d LUFS (±%d LU) — đo lại hay đổi bản tải là chế độ có thể lật giữa copy và "
                  "master; giữ chế độ khoá hoặc hỏi người dùng" % (QUIET_LUFS, BORDERLINE_LU))


def integrated(video):
    res = ffmpeg_audio(video, "ebur128=framelog=quiet")
    m = re.search(r"Integrated loudness:\s*I:\s*(-?[\d.]+|-?inf)\s*LUFS", res.stderr, re.S)
    return None if not m else float("-inf") if "inf" in m.group(1) else float(m.group(1))


def course_mode(folder):
    """Đoán chế độ âm thanh khoá đã dùng từ một file con có sẵn trong `folder` → (tên file, chế độ, lý do) | None.
    Dấu hiệu: balance/master của skill mã hoá lại AAC 192 kb/s; master còn đưa độ to về khoảng −16 LUFS."""
    try:
        names = sorted(f for f in os.listdir(folder) if not f.startswith(".")
                       and os.path.splitext(f)[1].lower() in VIDEO_EXT and os.path.isfile(os.path.join(folder, f)))
    except OSError:
        return None
    for f in names:
        path = os.path.join(folder, f)
        res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                              "stream=codec_name,bit_rate", "-of", "json", os.path.abspath(path)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            a = (json.loads(res.stdout).get("streams") or [None])[0] if res.returncode == 0 else None
        except ValueError:
            a = None
        if not a:
            continue  # file rỗng / không có tiếng: thử file sau
        codec, kbps = a.get("codec_name") or "?", int(a.get("bit_rate") or 0) // 1000
        if codec == "aac" and 176 <= kbps <= 208:
            lufs = integrated(path)
            if lufs is not None and -17.5 <= lufs <= -14.5:
                return f, "master", "tiếng mã hoá lại AAC %d kb/s, độ to %s LUFS" % (kbps, db(lufs))
            return f, "balance", "tiếng mã hoá lại AAC %d kb/s, độ to %s LUFS" % (kbps, db(lufs) if lufs else "?")
        return f, "copy", "tiếng giữ nguyên %s %d kb/s" % (codec, kbps)
    return None


def probe_audio(video, samples=(), duration=30):
    """Đo cả file: độ to tích hợp (ebur128) + RMS từng kênh (astats). Mẫu (nếu có) chỉ để tham khảo; mẫu im lặng bị
    bỏ qua. Khuyến nghị dựa trên số đo cả file."""
    if not os.path.isfile(video):
        st.die("không tìm thấy file video/âm thanh trên máy: %s (probe-audio chỉ đo file cục bộ)" % video)
    check_tools("ffmpeg")
    res = ffmpeg_audio(video, "ebur128=framelog=quiet,astats")
    m = re.search(r"Integrated loudness:\s*I:\s*(-?[\d.]+|-?inf)\s*LUFS", res.stderr, re.S)
    chans = channel_rms(res.stderr)
    if res.returncode != 0 or not m or not chans:
        st.die("không đọc được thông số âm thanh từ %s (không có luồng audio hoặc định dạng không hỗ trợ)" % video)
    lufs = float("-inf") if "inf" in m.group(1) else float(m.group(1))
    delta, single_ear = 0.0, False
    if len(chans) >= 2:
        l, r = chans[0], chans[1]
        single_ear = (l < -55.0 and r > -45.0) or (r < -55.0 and l > -45.0)
        delta = float("inf") if single_ear and (l == float("-inf") or r == float("-inf")) else abs(l - r)
    imbalanced = single_ear or delta >= IMBALANCE_DB
    quiet = lufs < QUIET_LUFS
    mode = "master" if quiet else "balance" if imbalanced else "copy"
    found = []
    for t in samples:
        sr = ffmpeg_audio(video, "astats", pre=["-ss", t, "-t", str(duration)])
        sc = channel_rms(sr.stderr)
        found.append((t, sc, bool(sc) and max(sc) < SILENT_DB))
    return {"video": video, "lufs": lufs, "chans": chans, "delta": delta, "single_ear": single_ear,
            "imbalanced": imbalanced, "quiet": quiet, "mode": mode, "samples": found, "duration": duration,
            "borderline": abs(lufs - QUIET_LUFS) <= BORDERLINE_LU}


def db(x):
    return "-inf" if x == float("-inf") else "%.1f" % x


def cmd_probe_audio(args):
    info = probe_audio(args.video, args.sample_time or (), args.duration)
    print("# probe-audio: %s" % info["video"])
    print("Đo: cả file (ebur128 + astats)")
    print("Độ to tích hợp cả file: %s LUFS" % db(info["lufs"]))
    chans = info["chans"]
    names = ["trái", "phải"]
    for i, v in enumerate(chans[:2]):
        print("Kênh %d (%s, cả file): %s dB RMS" % (i + 1, names[i], db(v)))
    if len(chans) >= 2:
        print("Lệch kênh (Δ): %s dB" % ("∞" if info["delta"] == float("inf") else "%.1f" % info["delta"]))
    for t, sc, silent in info["samples"]:
        vals = " · ".join("%s %s dB" % (names[i] if i < 2 else "kênh %d" % (i + 1), db(v)) for i, v in enumerate(sc))
        tail = ("gần im lặng (< %d dB), bỏ qua" % SILENT_DB) if silent else (
            "không đọc được, bỏ qua" if not sc else "chỉ để tham khảo")
        print("Mẫu %s (%d giây): %s — %s" % (t, info["duration"], vals or "-", tail))
    parts = ["Điếc 1 bên tai" if info["single_ear"] else
             "Lệch kênh (Δ ≥ %d dB)" % IMBALANCE_DB if info["imbalanced"] else
             "Âm thanh 1 kênh (mono)" if len(chans) < 2 else "Cân bằng tốt (Δ < %d dB)" % IMBALANCE_DB,
             "Âm lượng quá nhỏ (< %d LUFS)" % QUIET_LUFS if info["quiet"] else "Âm lượng đủ (≥ %d LUFS)" % QUIET_LUFS]
    print("Tình trạng: %s" % " · ".join(parts))
    if info["borderline"]:
        print("Cảnh báo: " + BORDERLINE_MSG)
    rec = info["mode"]
    course = course_mode(args.course_dir) if args.course_dir else None
    if args.course_dir and not course:
        print("Chế độ khoá: %s chưa có file con đọc được — chưa có chế độ khoá để so" % args.course_dir)
    if course:
        print("Chế độ khoá (đoán từ %s): %s — %s" % course)
        if course[1] != rec:
            print("Cảnh báo: số đo buổi này gợi ý %s, khác chế độ khoá %s — hỏi người dùng trước khi đổi" % (
                rec, course[1]))
        rec = course[1]
    rec_desc = {
        "copy": "Mode 1 (copy) — Pure Stream Copy (không re-encode)",
        "balance": "Mode 2 (balance) — Cân bằng Dual-Mono (re-encode AAC 192k)",
        "master": "Mode 3 (master) — Dual-Mono + Loudnorm -16 LUFS (re-encode AAC 192k)"
    }
    print("Khuyến nghị: %s" % rec_desc[rec])
    print("Giữ một chế độ cho cả khoá để các file con nghe đều nhau (--course-dir <thư mục file con> để so).")


# ---------------------------------------------------------------- tên file con & nhãn (một nguồn cho md, SRT, video)

NAME_FIELDS = ("prefix", "n", "code", "title")
LABEL_FIELDS = ("prefix", "n", "code")
LABEL_FORBIDDEN = re.compile(r"[\[\]|`*\n]")
DEFAULT_NAME = "{prefix}-P{n} - {title}"
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".webm")
EXISTING = re.compile(r"^(?P<pre>.*?\S)(?P<sep>[ _\-]*)P(?P<num>\d+)(?:\.\d+)?(?P<mid>\s+-\s+)\S")


class PartNo:
    """Số phần cho mẫu tên: {n:02} → 05 với P5, 05.1 với P5.1."""

    def __init__(self, code):
        m = CODE.match(code)
        self.major, self.sub = int(m.group(1)), m.group(2)

    def __format__(self, spec):
        return format(self.major, spec) + ("." + self.sub if self.sub else "")


def clean_part(text):
    """Phần tên file: `: / \\ |` → ' - ', bỏ `? * " < >`, gọn khoảng trắng và gạch nối lặp."""
    t = re.sub(r"\s*[\\/:|]\s*", " - ", text)
    t = re.sub(r'[?*"<>]', "", t)
    t = re.sub(r"\s*-(?:\s*-)+\s*", " - ", re.sub(r"\s+", " ", t))
    return t.strip(" .-_")


def check_template(tpl, opt="--name", fields=NAME_FIELDS, forbidden=FORBIDDEN, what="mẫu tên file"):
    try:
        parsed = list(string.Formatter().parse(tpl))
    except ValueError as exc:
        st.die("%s sai cú pháp (%s): %s" % (opt, exc, tpl))
    if forbidden.search("".join(lit for lit, _, _, _ in parsed)):
        st.die("%s là %s, không chứa %s; nhận: %s" % (
            opt, what, "\\ / : * ? \" < > |" if forbidden is FORBIDDEN else "[ ] | ` *", tpl))
    used = set()
    for _, field, spec, conv in parsed:
        if field is None:
            continue
        if field not in fields or conv or (spec and (field != "n" or not re.fullmatch(r"0?\d", spec))):
            st.die("%s chỉ nhận %s (vd {n:02}); nhận {%s%s%s}" % (
                opt, ", ".join("{%s}" % f for f in fields), field, "!" + conv if conv else "", ":" + spec if spec else ""))
        used.add(field)
    if not used & {"n", "code"}:
        st.die("%s cần {n} hoặc {code} để các file con không trùng; nhận: %s" % (opt, tpl))
    return tpl


def render_name(tpl, prefix, code, title):
    name = tpl.format(prefix=clean_part(prefix), n=PartNo(code), code=code, title=clean_part(title))
    return re.sub(r"\s+", " ", name).strip(" ._-")


def render_label(tpl, prefix, code):
    if not tpl:
        return label(prefix, code)
    return re.sub(r"\s+", " ", tpl.format(prefix=prefix, n=PartNo(code), code=code)).strip(" :·._-")


def infer_template(folder):
    """Quy ước tên từ file video đã có trong thư mục → (mẫu, số file khớp, [cảnh báo]); không có → (None, 0, []).
    Bỏ phiếu theo cả kiểu (dấu nối, độ rộng số, gạch giữa); hai kiểu ngang phiếu → dừng, cần --name."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return None, 0, []
    exact, loose, count = {}, {}, 0
    for f in names:
        stem, ext = os.path.splitext(f)
        m = EXISTING.match(stem)
        if f.startswith(".") or ext.lower() not in VIDEO_EXT or not m:
            continue
        count += 1
        num = m.group("num")
        if num.startswith("0") or len(num) == 1:
            key = (m.group("sep"), len(num), m.group("mid"))
            exact[key] = exact.get(key, 0) + 1
        else:  # P10, P12…: không biết có đệm số 0 không
            key = (m.group("sep"), m.group("mid"))
            loose[key] = loose.get(key, 0) + 1
    if not count:
        return None, 0, []
    score = {k: v + loose.get((k[0], k[2]), 0) for k, v in exact.items()} or {
        (sep, 1, mid): v for (sep, mid), v in loose.items()}
    ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))
    fmt = lambda k: "{prefix}%sP{n%s}%s{title}" % (k[0], ":0%d" % k[1] if k[1] > 1 else "", k[2])
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        st.die("%s có các kiểu tên ngang nhau: %s — hỏi người dùng rồi truyền --name" % (
            folder, "; ".join("%s (%d file)" % (fmt(k), v) for k, v in ranked)))
    warns = []
    if len(ranked) > 1 or (len(score) == 1 and len(loose) > 1):
        warns.append("%s có nhiều kiểu tên (%s) — dùng kiểu nhiều nhất; muốn kiểu khác thì truyền --name" % (
            folder, "; ".join("%s: %d" % (fmt(k), v) for k, v in ranked)))
    return fmt(ranked[0][0]), count, warns


def resolve_names(args, segs, folder):
    """Đặt s['file'] (tên file con không đuôi) cho mọi KEEP theo --name / quy ước của `folder` / mặc định."""
    if getattr(args, "name", None):
        tpl = check_template(args.name)
        print("Mẫu tên: %s (--name)" % tpl)
    else:
        tpl, count, warns = infer_template(folder) if folder else (None, 0, [])
        if tpl:
            print("Mẫu tên: %s (suy từ %d file có sẵn trong %s)" % (tpl, count, folder))
            for w in warns:
                print("Cảnh báo: " + w)
        else:
            tpl = DEFAULT_NAME
            print("Mẫu tên: mặc định %s (chưa có quy ước — luật khoá/quy ước thư mục video → truyền --name)" % tpl)
    for s in segs:
        if s["cmd"] == "KEEP":
            s["file"] = render_name(tpl, args.prefix, s["code"], s["title"])
    return tpl


# ---------------------------------------------------------------- cắt video con

def probe_media(path):
    """ffprobe → dict(duration giây, video bool, audio bool, streams {loại: thời lượng|None}); không đọc được → None."""
    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration:format=duration",
                          "-of", "json", os.path.abspath(path)], capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    try:
        data = json.loads(res.stdout) if res.returncode == 0 else None
    except ValueError:
        data = None
    if not data:
        return None
    streams = {}
    for s in data.get("streams") or []:
        kind = s.get("codec_type")
        if kind in ("video", "audio") and kind not in streams:
            try:
                streams[kind] = float(s["duration"]) if s.get("duration") not in (None, "N/A") else None
            except ValueError:
                streams[kind] = None
    try:
        total = float((data.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        total = None
    return {"duration": total, "video": "video" in streams, "audio": "audio" in streams, "streams": streams}


TOLERANCE = 1.0  # giây: cắt -c copy theo khung hình chính lệch được chút ít


def verify_part(path, planned, need_audio):
    info = probe_media(path)
    if not info:
        return ["ffprobe không đọc được file"]
    errs = []
    if info["duration"] is None or abs(info["duration"] - planned) > TOLERANCE:
        errs.append("thời lượng %s giây, kế hoạch %.1f giây" % (
            "?" if info["duration"] is None else "%.1f" % info["duration"], planned))
    if not info["video"]:
        errs.append("không có luồng hình")
    if need_audio and not info["audio"]:
        errs.append("không có luồng tiếng")
    for kind, name in (("video", "hình"), ("audio", "tiếng")):
        d = info["streams"].get(kind)
        if d is not None and abs(d - planned) > TOLERANCE:
            errs.append("luồng %s dài %.1f giây, kế hoạch %.1f giây" % (name, d, planned))
    return errs


def deliver(tmp, dest):
    """Đặt file đã kiểm vào tên thật, không bao giờ ghi đè (hard link; FS không có link → tạo mới 'xb' rồi chép)."""
    try:
        os.link(tmp, dest)
        return
    except FileExistsError:
        st.die("%s xuất hiện trong lúc cắt — không ghi đè, dừng" % dest)
    except OSError:
        pass
    try:
        with open(tmp, "rb") as src, open(dest, "xb") as out:
            shutil.copyfileobj(src, out)
    except FileExistsError:
        st.die("%s xuất hiện trong lúc cắt — không ghi đè, dừng" % dest)


def cmd_cut_video(args):
    if not os.path.isfile(args.video):
        st.die("không tìm thấy file video nguồn: %s" % args.video)
    check_tools("ffmpeg", "ffprobe")

    segs, end, errors, warns = parse_plan(args.plan, args.prefix, label_tpl=check_label(args))
    if end is None:
        errors.append("%s: thiếu dòng 'hh:mm:ss | END' ở cuối file kế hoạch" % args.plan)
    if errors:
        for e in errors:
            print("LỖI: " + e)
        st.die("kế hoạch cắt có %d lỗi — chưa thực hiện cắt" % len(errors))

    keep_segs = [s for s in segs if s["cmd"] == "KEEP"]
    if not keep_segs:
        st.die("kế hoạch không có phân đoạn KEEP nào để cắt")

    resolve_names(args, segs, args.out_dir)
    out_names = [s["file"] + ".mp4" for s in keep_segs]
    dup = sorted(set(n for n in out_names if out_names.count(n) > 1))
    taken = [n for n in out_names if os.path.lexists(os.path.join(args.out_dir, n))]
    for n in dup:
        print("LỖI: mẫu tên cho ra nhiều file con cùng tên %s — thêm {n} hoặc {code} vào --name" % n)
    for n in taken:
        print("LỖI: %s đã có" % os.path.join(args.out_dir, n))
    if dup or taken:
        st.die("%d tên trùng — xoá file hoặc đổi thư mục (không ghi đè); chưa cắt file nào" % (len(dup) + len(taken)))

    src = probe_media(args.video)
    if not src or src["duration"] is None:
        st.die("ffprobe không đọc được thời lượng %s" % args.video)
    over = [s for s in keep_segs if s["end"] / 1000.0 > src["duration"] + 0.5]
    for s in over:
        print("LỖI: %s (%s → %s) vượt thời lượng video %s — kế hoạch không khớp video này?" % (
            s["label"], long_(s["start"]), long_(s["end"]), long_(int(src["duration"] * 1000))))
    if over:
        st.die("%d phần vượt thời lượng video — chưa cắt file nào" % len(over))

    mode = args.mode
    info = None
    if mode == "auto":
        print("Khảo sát âm thanh cả file trước khi cắt (Pre-flight probe)...")
        info = probe_audio(args.video)
        mode = info["mode"]
        course = course_mode(args.out_dir)
        if info["borderline"]:
            print("Cảnh báo: " + BORDERLINE_MSG)
        if course:
            print("Chế độ khoá (đoán từ %s): %s — %s" % course)
            if course[1] != mode:
                print("Cảnh báo: số đo buổi này gợi ý %s, khác chế độ khoá %s — giữ chế độ khoá" % (mode, course[1]))
            mode = course[1]
        print("→ Chọn chế độ: %s (cả file %s LUFS, Δ %.1f dB)" % (mode, db(info["lufs"]), info["delta"]))

    is_mono = len(info["chans"]) < 2 if info else False
    pan_filter = "pan=stereo|c0=c0|c1=c0" if is_mono else "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"
    audio_args = {"copy": ["-c", "copy"],
                  "balance": ["-c:v", "copy", "-af", pan_filter, "-c:a", "aac", "-b:a", "192k"],
                  "master": ["-c:v", "copy", "-af", "%s,loudnorm=I=-16:TP=-1.5:LRA=11" % pan_filter,
                             "-c:a", "aac", "-b:a", "192k"]}[mode]

    tmp = None
    if not args.dry_run:
        try:
            os.makedirs(args.out_dir, exist_ok=True)
            tmp = tempfile.mkdtemp(prefix=".mk-subtitle-cut.", dir=args.out_dir)
        except OSError as exc:
            st.die("không tạo được thư mục đầu ra %s: %s" % (args.out_dir, exc))

    print("Bắt đầu cắt %d video con (chế độ: %s)..." % (len(keep_segs), mode))
    try:
        for idx, (s, out_name) in enumerate(zip(keep_segs, out_names), 1):
            start_tc, end_tc = long_(s["start"]), long_(s["end"])
            part = os.path.join(tmp, "p%03d.mp4" % idx) if tmp else os.path.join(args.out_dir, out_name)
            cmd = (["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", start_tc, "-to", end_tc,
                    "-i", os.path.abspath(args.video)] + audio_args + ["-n", part])  # -n: không bao giờ ghi đè
            if args.dry_run:
                print("[%d/%d] DRY-RUN: %s (%s → %s)" % (idx, len(keep_segs), out_name, start_tc, end_tc))
                print("  Lệnh: %s" % " ".join(cmd))
                continue
            print("[%d/%d] Đang cắt: %s (%s → %s, %s)..." % (
                idx, len(keep_segs), out_name, start_tc, end_tc, dur(s["end"] - s["start"])))
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if res.returncode != 0:
                st.die("Lỗi ffmpeg khi cắt %s: %s" % (out_name, res.stderr.strip()[-300:]))
            bad = verify_part(part, (s["end"] - s["start"]) / 1000.0, src["audio"])
            if bad:
                for b in bad:
                    print("LỖI: %s: %s" % (out_name, b))
                st.die("%s hỏng — không giao (đã giao %d/%d file trước đó)" % (out_name, idx - 1, len(keep_segs)))
            dest = os.path.join(args.out_dir, out_name)
            deliver(part, dest)
            got = probe_media(dest)
            print("OK: %s (%.1f giây, hình%s)" % (out_name, got["duration"], " + tiếng" if got["audio"] else ""))
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    if not args.dry_run:
        print("\nHoàn tất cắt %d video con vào thư mục: %s (đã kiểm ffprobe từng file)" % (len(keep_segs), args.out_dir))
    else:
        print("\nHoàn tất kiểm tra lệnh dry-run cho %d video con" % len(keep_segs))


def main(argv=None):
    st.utf8_stdio()
    ap = argparse.ArgumentParser(description="Chia buổi học dài thành file con cho editor.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    plan_opts = argparse.ArgumentParser(add_help=False)
    plan_opts.add_argument("--plan", required=True)
    plan_opts.add_argument("--prefix", default="")
    plan_opts.add_argument("--min", type=float, default=20)
    plan_opts.add_argument("--max", type=float, default=30)
    plan_opts.add_argument("--min-case", type=float, default=8)
    plan_opts.add_argument("--gap", type=int, default=90)
    name_opts = argparse.ArgumentParser(add_help=False)
    name_opts.add_argument("--name", help='mẫu tên file con (md, SRT, video), vd "{prefix}_P{n:02} - {title}"')
    name_opts.add_argument("--label", help='mẫu nhãn hiển thị, vd "{prefix} · P{n:02}" (mặc định "<tiền tố>:P1")')

    p = sub.add_parser("scan")
    p.add_argument("input")
    p.add_argument("--gap", type=int, default=90)
    p.add_argument("--limit", type=int, default=12)
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("plan", parents=[plan_opts, name_opts])
    p.add_argument("--video-dir", help="thư mục file con video: suy quy ước tên khi không có --name")
    p.add_argument("input")
    p.add_argument("--out-md")
    p.add_argument("--out-csv")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("split", parents=[plan_opts, name_opts])
    p.add_argument("--video-dir", help="thư mục file con video: suy quy ước tên khi không có --name")
    p.add_argument("--source-label", help="nguồn ghi ở dòng 'File nguồn' (link YouTube, tên bản chép lời gốc)")
    p.add_argument("input")
    p.add_argument("--out-md")
    p.add_argument("--out-srt-dir")
    p.add_argument("--no-notes", action="store_true")
    p.add_argument("--style", choices=["khung", "khoa"], default="khung",
                   help="khung: khung thô (mặc định); khoa: chuẩn khoá — mốc in đậm, mỗi lượt >> một dòng, CUT [!WARNING]")
    p.set_defaults(fn=cmd_split)

    p = sub.add_parser("lint")
    p.add_argument("input")
    p.add_argument("--plan")
    p.add_argument("--prefix", default="")
    p.add_argument("--source")
    p.add_argument("--label")
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("probe-audio")
    p.add_argument("video")
    p.add_argument("--sample-time", action="append", help="mẫu tham khảo (lặp được); khuyến nghị luôn theo cả file")
    p.add_argument("--duration", type=int, default=30)
    p.add_argument("--course-dir", help="thư mục file con các buổi trước: đoán chế độ âm thanh khoá đã dùng")
    p.set_defaults(fn=cmd_probe_audio)

    p = sub.add_parser("cut-video", parents=[name_opts])
    p.add_argument("video")
    p.add_argument("--plan", required=True)
    p.add_argument("--prefix", default="")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--mode", choices=["auto", "copy", "balance", "master"], default="auto")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_cut_video)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
