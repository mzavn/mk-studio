#!/usr/bin/env python3
"""Chia buổi học / bài giảng dài thành file con: tín hiệu cắt, bảng lệnh CUT/KEEP cho editor, khung bài giảng theo
file con, phụ đề riêng từng file con, kiểm file bài giảng, khảo sát âm thanh & cắt video bằng FFmpeg (chỉ thư viện
chuẩn, đầu ra tất định, không sửa đầu vào).

  lecture.py scan IN [--gap 90] [--limit 12]
  lecture.py plan IN --plan PLAN.txt [--prefix "Buổi 3"] [--min 20 --max 30 --min-case 8 --gap 90]
                     [--out-md SHEET.md] [--out-csv SHEET.csv]
  lecture.py split IN --plan PLAN.txt [--prefix "Buổi 3"] [--out-md BAI.md [--no-notes]] [--out-srt-dir DIR]
  lecture.py lint BAI.md [--plan PLAN.txt [--prefix "Buổi 3"]] [--source IN]
  lecture.py probe-audio VIDEO [--sample-time 00:15:00] [--duration 30]
  lecture.py cut-video VIDEO --plan PLAN.txt [--prefix "Buổi 3"] --out-dir DIR [--mode auto|copy|balance|master] [--dry-run]

IN: bản chép lời có mốc ở đầu dòng "[mm:ss] câu" / "[h:mm:ss] câu" (TXT/MD, vd bản chép lời YouTube), SRT hoặc VTT.
PLAN: mỗi dòng "bắt đầu | CUT hoặc KEEP | mã | tiêu đề | ghi chú"; dòng cuối "kết thúc | END". Dòng trống và dòng
bắt đầu bằng # bị bỏ qua. Mỗi phân đoạn kéo tới mốc bắt đầu của dòng sau, nên không có khoảng hở hay chồng lấn.
Thoát: 0 xong/qua (có thể kèm dòng "Cảnh báo:"); 1 lỗi đầu vào hoặc có dòng "LỖI:" — khi đó không ghi file nào.
"""
import argparse
import csv
import io
import os
import re
import shutil
import subprocess
import sys

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


def safe(name):
    return re.sub(r"\s+", " ", FORBIDDEN.sub("-", name)).strip(" .")


def parse_plan(path, prefix, lines=None, kind=None, opts=None):
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
            seg["label"] = label(prefix, code)
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
    segs, end, errors, warns = parse_plan(args.plan, args.prefix, lines, kind, args)
    for e in errors:
        print("LỖI: " + e)
    if errors:
        print("Kết quả: %d lỗi — chưa ghi file nào" % len(errors))
        sys.exit(1)
    return segs, end, warns


def stats(segs, end):
    cut = [s for s in segs if s["cmd"] == "CUT"]
    cut_ms = sum(s["end"] - s["start"] for s in cut)
    return {"total": end, "cut": cut_ms, "kept": end - cut_ms, "cuts": cut,
            "parts": sum(s["cmd"] == "KEEP" for s in segs)}


def cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def file_name(s):
    return safe("%s - %s" % (s["label"], s["title"]))


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
            out.append("| **%s** | %s | 🟢 **GIỮ LẠI (KEEP)** | %s | **%s - %s** | %s |" % (
                s["code"], span, dur(s["end"] - s["start"]), cell(s["label"]), cell(s["title"]), cell(s["note"])))
    if any(FORBIDDEN.search(s["label"] + s["title"]) for s in segs if s["cmd"] == "KEEP"):
        out += ["", "> Tên file khi xuất: thay `\\ / : * ? \" < > |` bằng `-` (hệ điều hành không cho các ký tự này "
                "trong tên file), vd `%s`." % file_name(next(s for s in segs if s["cmd"] == "KEEP"))]
    return "\n".join(out) + "\n"


def sheet_csv(segs):
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(["stt", "lenh", "ma", "nhan", "ten_file", "bat_dau", "ket_thuc", "thoi_luong_giay", "tieu_de",
                 "ghi_chu"])
    for i, s in enumerate(segs, 1):
        keep = s["cmd"] == "KEEP"
        wr.writerow([i, s["cmd"], s["code"], s["label"] if keep else "", file_name(s) if keep else "",
                     long_(s["start"]), long_(s["end"] - 1000), (s["end"] - s["start"]) // 1000,
                     s["title"], s["note"]])
    return buf.getvalue()


def kaizen_row(prefix, segs, end):
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
    print("Dòng kaizen: " + kaizen_row(args.prefix, segs, end))
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
               os.path.basename(args.input), dur(k["total"]), dur(k["kept"]), k["parts"]),
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
        write_new(args.out_md, lecture_md(args, segs, end, lines))
        print("Khung bài giảng → %s (điền mọi chỗ {{điền…}}, rồi chạy lint)" % args.out_md)
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
            name = os.path.join(args.out_srt_dir, file_name(s) + ".srt")
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
        segs, end, perrs, _ = parse_plan(args.plan, args.prefix)
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
                if not any(r.startswith("|") and ("**%s - " % s["label"]) in r for r in rows):
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
        st.die("không đọc được thông số âm thanh từ %s (file không có luồng audio hoặc định dạng không hỗ trợ)" % video)

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
        "video": video,
        "sample_time": sample_time,
        "duration": duration,
        "ch1": ch1,
        "ch2": ch2,
        "delta": delta,
        "overall": avg,
        "single_ear": single_ear,
        "imbalanced": imbalanced,
        "quiet": is_quiet,
        "mode": rec_mode,
    }


def cmd_probe_audio(args):
    info = probe_audio(args.video, args.sample_time, args.duration)
    print("# probe-audio: %s" % info["video"])
    print("Mẫu phân tích: %s (thời lượng %ds)" % (info["sample_time"], info["duration"]))
    if info["ch1"] is not None:
        print("Kênh 1 (Trái): %.1f dB" % info["ch1"])
    if info["ch2"] is not None:
        print("Kênh 2 (Phải): %.1f dB" % info["ch2"])
        print("Độ lệch kênh (Δ): %.1f dB" % info["delta"])
    print("Độ lớn trung bình: %.1f dB" % info["overall"])

    status_parts = []
    if info["single_ear"]:
        status_parts.append("Điếc 1 bên tai")
    elif info["imbalanced"]:
        status_parts.append("Lệch kênh (Δ ≥ 4 dB)")
    elif info["ch2"] is not None:
        status_parts.append("Cân bằng tốt (Δ ≤ 3 dB)")
    else:
        status_parts.append("Âm thanh Mono (1 kênh)")

    if info["quiet"]:
        status_parts.append("Âm lượng quá nhỏ (RMS < -24 dB)")
    else:
        status_parts.append("Âm lượng vừa vặn (RMS ≥ -24 dB)")

    print("Tình trạng: %s" % " · ".join(status_parts))

    rec_desc = {
        "copy": "Mode 1 (copy) — Pure Stream Copy (không re-encode)",
        "balance": "Mode 2 (balance) — Cân bằng Dual-Mono (re-encode AAC 192k)",
        "master": "Mode 3 (master) — Dual-Mono + Loudnorm -16 LUFS (re-encode AAC 192k)"
    }
    print("Khuyến nghị: %s" % rec_desc[info["mode"]])


def cmd_cut_video(args):
    if not os.path.isfile(args.video):
        st.die("không tìm thấy file video nguồn: %s" % args.video)
    check_tools("ffmpeg")

    segs, end, errors, warns = parse_plan(args.plan, args.prefix)
    if end is None:
        errors.append("%s: thiếu dòng 'hh:mm:ss | END' ở cuối file kế hoạch" % args.plan)
    if errors:
        for e in errors:
            print("LỖI: " + e)
        st.die("kế hoạch cắt có %d lỗi — chưa thực hiện cắt" % len(errors))

    keep_segs = [s for s in segs if s["cmd"] == "KEEP"]
    if not keep_segs:
        st.die("kế hoạch không có phân đoạn KEEP nào để cắt")

    mode = args.mode
    info = None
    if mode == "auto":
        print("Khảo sát âm thanh trước khi cắt (Pre-flight probe)...")
        info = probe_audio(args.video, sample_time="00:15:00", duration=30)
        mode = info["mode"]
        print("→ Tự động chọn chế độ: %s (RMS: %.1f dB, Δ: %.1f dB)" % (mode, info["overall"], info["delta"]))

    if not args.dry_run:
        try:
            os.makedirs(args.out_dir, exist_ok=True)
        except OSError as exc:
            st.die("không tạo được thư mục đầu ra %s: %s" % (args.out_dir, exc))

    is_mono = (info.get("ch2") is None) if info else False
    pan_filter = "pan=stereo|c0=c0|c1=c0" if is_mono else "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"

    print("Bắt đầu cắt %d video con (chế độ: %s)..." % (len(keep_segs), mode))

    for idx, s in enumerate(keep_segs, 1):
        out_name = file_name(s) + ".mp4"
        out_path = os.path.join(args.out_dir, out_name)
        if not args.dry_run and os.path.lexists(out_path):
            st.die("%s đã có — xoá file hoặc đổi thư mục (không ghi đè)" % out_path)

        start_tc = long_(s["start"])
        end_tc = long_(s["end"])

        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", start_tc, "-to", end_tc, "-i", args.video]
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
            print("[%d/%d] DRY-RUN: %s (%s → %s)" % (idx, len(keep_segs), out_name, start_tc, end_tc))
            print("  Lệnh: %s" % " ".join(cmd))
            continue

        print("[%d/%d] Đang cắt: %s (%s → %s, %s)..." % (
            idx, len(keep_segs), out_name, start_tc, end_tc, dur(s["end"] - s["start"])))
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            st.die("Lỗi ffmpeg khi cắt %s: %s" % (out_name, res.stderr))

    if not args.dry_run:
        print("\nHoàn tất cắt %d video con vào thư mục: %s" % (len(keep_segs), args.out_dir))
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

    p = sub.add_parser("scan")
    p.add_argument("input")
    p.add_argument("--gap", type=int, default=90)
    p.add_argument("--limit", type=int, default=12)
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("plan", parents=[plan_opts])
    p.add_argument("input")
    p.add_argument("--out-md")
    p.add_argument("--out-csv")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("split", parents=[plan_opts])
    p.add_argument("input")
    p.add_argument("--out-md")
    p.add_argument("--out-srt-dir")
    p.add_argument("--no-notes", action="store_true")
    p.set_defaults(fn=cmd_split)

    p = sub.add_parser("lint")
    p.add_argument("input")
    p.add_argument("--plan")
    p.add_argument("--prefix", default="")
    p.add_argument("--source")
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("probe-audio")
    p.add_argument("video")
    p.add_argument("--sample-time", default="00:15:00")
    p.add_argument("--duration", type=int, default=30)
    p.set_defaults(fn=cmd_probe_audio)

    p = sub.add_parser("cut-video")
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
