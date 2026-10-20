#!/usr/bin/env python3
"""Tiến độ nhật ký STAR và lệnh đánh dấu (chỉ thư viện chuẩn, đầu ra tất định).

  progress.py [--dir DIR] [--today YYYY-MM-DD]        tiến độ, cột mốc, việc đến hạn, case, cảnh báo
  progress.py --da-lam FILE                           `- Đã làm: chưa` → `rồi` (trong ## Tổng kết)
  progress.py --ket-qua FILE                          `- Kết quả: chưa` → `đã ghi` (khối đầu)
  progress.py --gui-mentor FILE --ngay YYYY-MM-DD     thêm/thay `- Đã gửi mentor: D` sau dòng `Trạng thái`

Đọc không sửa gì; không tạo thư mục. Cảnh báo luôn thoát 0; lệnh đánh dấu lỗi thoát 1 và không sửa file.
Mã bắt buộc lấy từ mẫu bài ở ../assets/mau/ (mã Cơ bản và mã ghi `luôn hỏi`).
"""
import argparse
import datetime
import os
import re
import stat
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal

DEFAULT_DIR = "~/nhat-ky-star"
MAU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "mau")
TEMPLATES = {("I", ""): "i.md", ("II", "đầy đủ"): "ii-day-du.md", ("II", "ngắn"): "ii-ngan.md",
             ("III", ""): "iii.md", ("IV", ""): "iv.md", ("V", ""): "v.md"}
TYPES = ["I", "II", "III", "IV", "V"]
MILESTONES = [  # Tổng quan B16–B19, nguyên văn
    (28, "Trí tuệ phát triển bằng 5 năm trước cộng lại"),
    (300, "Thu nhập x2"),
    (1000, "Tốt nghiệp 5 bài học: sức khoẻ, thành công, hạnh phúc, ý nghĩa, tự do"),
    (10000, "Đa triệu phú đô la"),
]
SUMMARY_KEYS = ["Insight", "Pattern", "Tầng think", "One action tomorrow", "Người liên quan", "Đã làm"]
THINK_LAYERS = ["Feel", "Think", "Pain", "Fear", "Story", "Concept", "Identity", "Shadow", "Role-play"]
EMPTY_ANSWERS = {"", "(bỏ qua)", "(không chọn)"}
CASE_RANK = {"Đang viết": 1, "Xong": 2, "Đã gửi mentor": 3}
CODE = re.compile(r"^### (.+?) · (Cơ bản|Chuyên sâu)( · luôn hỏi)?\s*$")
FIELD = re.compile(r"^- ([^:]+):[ \t]*(.*?)\s*$")


def parse_date(text):
    try:
        return datetime.date.fromisoformat(text) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None
    except ValueError:
        return None


def required_codes(template):
    codes = []
    with open(os.path.join(MAU, template), encoding="utf-8") as f:
        for line in f:
            m = CODE.match(line)
            if m and (m.group(2) == "Cơ bản" or m.group(3)):
                codes.append(m.group(1))
    return codes


def parse_post(text):
    """Header fields, title, answers per code, summary fields (None = line absent)."""
    lines = text.splitlines()
    header, answers, summary = {}, {}, {}
    section, code, title = None, None, ""
    for line in lines:
        if line.startswith("# ") and section is None and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            code = None
            continue
        m = CODE.match(line)
        if m:
            code = m.group(1)
            answers.setdefault(code, [])
            continue
        if line.startswith("#"):
            code = None
            continue
        if section is None:
            f = FIELD.match(line)
            if f and f.group(1) not in header:
                header[f.group(1)] = f.group(2)
        elif section == "Tổng kết":
            f = FIELD.match(line)
            if f and f.group(1) in SUMMARY_KEYS and f.group(1) not in summary:
                summary[f.group(1)] = f.group(2)
        elif code is not None:
            answers[code].append(line)
    return title, header, answers, summary


def answered(lines):
    body = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("> Gợi ý:")]
    return bool(body) and " ".join(body) not in EMPTY_ANSWERS


class Post:
    def __init__(self, name, path, text):
        self.name, self.path = name, path
        self.title, self.header, answers, self.summary = parse_post(text)
        self.problems = []  # format problems: always warned
        self.gaps = []      # completeness gaps: warned only when `xong`
        h = self.header
        self.loai, self.status = h.get("Loại", ""), h.get("Trạng thái", "")
        self.ban = h.get("Bản", "") if self.loai == "II" else ""
        self.date = parse_date(h.get("Ngày", ""))
        for key in ("Loại", "Ngày", "Trạng thái"):
            if key not in h:
                self.problems.append("thiếu `%s`" % key)
        if "Loại" in h and self.loai not in TYPES:
            self.problems.append("`Loại` không hợp lệ: %s" % self.loai)
        if "Ngày" in h and self.date is None:
            self.problems.append("`Ngày` không hợp lệ: %s" % h["Ngày"])
        if "Trạng thái" in h and self.status not in ("nháp", "xong"):
            self.problems.append("`Trạng thái` không hợp lệ: %s" % self.status)
        if self.loai == "II" and self.ban not in ("ngắn", "đầy đủ"):
            self.problems.append("loại II thiếu `Bản: ngắn|đầy đủ`")
        self.case = h.get("Case")
        if self.case is not None and not (re.fullmatch(r"\d{2}", self.case) and 1 <= int(self.case) <= 28):
            self.problems.append("`Case` không hợp lệ: %s" % self.case)
            self.case = None
        self.due = None
        if "Hẹn kết quả" in h:
            self.due = parse_date(h["Hẹn kết quả"])
            if self.due is None:
                self.problems.append("`Hẹn kết quả` không hợp lệ: %s" % h["Hẹn kết quả"])
        template = TEMPLATES.get((self.loai, self.ban))
        if template and not self.problems:
            missing = [c for c in required_codes(template) if not answered(answers.get(c, []))]
            if missing:
                self.gaps.append("thiếu trả lời mã " + ", ".join(missing))
        for key in SUMMARY_KEYS:
            val = self.summary.get(key)
            if val is None:
                self.gaps.append("thiếu dòng Tổng kết `%s`" % key)
            elif val in EMPTY_ANSWERS:
                self.gaps.append("Tổng kết `%s` chưa có giá trị" % key)
        layer = self.summary.get("Tầng think")
        if layer and layer not in EMPTY_ANSWERS and layer.lower() not in {t.lower() for t in THINK_LAYERS}:
            self.gaps.append("`Tầng think` ngoài 9 giá trị (%s): %s" % (", ".join(THINK_LAYERS), layer))
        done = self.summary.get("Đã làm")
        if done and done not in EMPTY_ANSWERS and done not in ("chưa", "rồi"):
            self.gaps.append("`Đã làm` phải là chưa hoặc rồi: %s" % done)
        self.complete = self.status == "xong" and not self.problems and not self.gaps

    def warnings(self):
        return self.problems + (self.gaps if self.status == "xong" else [])


def percent(count, total):
    value = (Decimal(count) * 100 / Decimal(total)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if count >= 1 and value == 0:
        return "< 0,1%"
    return str(value).replace(".", ",") + "%"


def git_root(path):
    """Nearest existing directory at or above `path`, then the first ancestor holding `.git`."""
    cur = os.path.abspath(path)
    while not os.path.isdir(cur):
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def case_status(posts):
    """Case number → status (highest of its posts; case 28 needs complete II and IV)."""
    by_case = {}
    for p in posts:
        if p.case:
            by_case.setdefault(p.case, []).append(p)
    result = {}
    for case, items in sorted(by_case.items()):
        if case == "28":
            done = [p for p in items if p.complete]
            if {"II", "IV"} <= {p.loai for p in done}:
                sent = any("Đã gửi mentor" in p.header for p in done)
                result[case] = "Đã gửi mentor" if sent else "Xong"
            else:
                result[case] = "Đang viết"
            continue
        best = "Đang viết"
        for p in items:
            st = ("Đã gửi mentor" if "Đã gửi mentor" in p.header else "Xong") if p.complete else "Đang viết"
            if CASE_RANK[st] > CASE_RANK[best]:
                best = st
        result[case] = best
    return result


def report(shown_dir, today):
    real = os.path.expanduser(shown_dir)
    out = []
    root = git_root(real)
    if root:
        out.append("Cảnh báo: thư mục nhật ký %s nằm trong git work tree %s — nhật ký là dữ liệu cá nhân, "
                   "đừng commit; nên chọn thư mục ngoài repo." % (shown_dir, root))
    names = sorted(n for n in os.listdir(real) if n.endswith(".md")
                   and os.path.isfile(os.path.join(real, n))) if os.path.isdir(real) else []
    if not names:
        out.append("chưa có bài nào ở %s" % shown_dir)
        return out
    posts = []
    for n in names:
        with open(os.path.join(real, n), encoding="utf-8", errors="replace") as f:
            posts.append(Post(n, os.path.join(shown_dir, n), f.read()))
    complete = [p for p in posts if p.complete]
    by_type = ["%s: %d" % (t, sum(p.loai == t for p in complete)) for t in TYPES
               if any(p.loai == t for p in complete)]
    out.append("Bài trọn vẹn: %d" % len(complete) + (" (%s)" % " · ".join(by_type) if by_type else ""))
    out.append("Nháp: %d" % sum(p.status == "nháp" and not p.problems for p in posts))
    for total, meaning in MILESTONES:
        n = len(complete)
        state = "đạt" if n >= total else "còn %d (%s)" % (total - n, percent(n, total))
        out.append("%d bài: %s — %s (theo tài liệu)" % (total, state, meaning))
    pending = [p for p in complete if p.date < today and p.summary.get("Đã làm") == "chưa"]
    if pending:
        out.append("One Action chưa đánh dấu đã làm:")
        out += ["- %s · %s · %s" % (p.date.isoformat(), p.summary["One action tomorrow"], p.path) for p in pending]
    due = [p for p in posts if not p.problems and p.due and p.due <= today and p.header.get("Kết quả") == "chưa"]
    if due:
        out.append("Đến hạn ghi kết quả:")
        out += ["- %s · %s · %s" % (p.due.isoformat(), p.title, p.path) for p in due]
    cases = case_status(posts)
    if cases:
        out.append("Case đã xong: %d/28" % sum(s in ("Xong", "Đã gửi mentor") for s in cases.values()))
        out.append("Trạng thái case: " + " · ".join("%s %s" % kv for kv in cases.items()))
    for p in posts:
        reasons = p.warnings()
        if reasons:
            out.append("Cảnh báo: %s: %s — không tính trọn vẹn" % (p.path, "; ".join(reasons))
                       if p.status == "xong" else "Cảnh báo: %s: %s" % (p.path, "; ".join(reasons)))
    return out


def mark(path, kind, day=None):
    """Edit exactly one line; return error message or None."""
    if os.path.islink(path):
        return "%s là đường tắt (symlink) — không sửa qua đường tắt" % path
    if not os.path.isfile(path):
        return "không có file %s" % path
    with open(path, "rb") as f:
        raw = f.read()
    try:
        lines = raw.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return "%s không phải UTF-8" % path
    first_section = next((i for i, ln in enumerate(lines) if ln.startswith("## ")), len(lines))
    if kind == "da-lam":
        start = next((i + 1 for i, ln in enumerate(lines) if ln.rstrip("\r\n").strip() == "## Tổng kết"), None)
        if start is None:
            return "%s không có phần ## Tổng kết" % path
        end = next((i for i in range(start, len(lines)) if lines[i].startswith("#")), len(lines))
        span, old, new = range(start, end), "- Đã làm: chưa", "- Đã làm: rồi"
    elif kind == "ket-qua":
        span, old, new = range(first_section), "- Kết quả: chưa", "- Kết quả: đã ghi"
    else:
        span = range(first_section)
        sent = [i for i in span if lines[i].startswith("- Đã gửi mentor:")]
        status = [i for i in span if lines[i].startswith("- Trạng thái:")]
        if len(sent) > 1:
            return "%s có %d dòng `- Đã gửi mentor:`" % (path, len(sent))
        if sent:
            i = sent[0]
            ending = lines[i][len(lines[i].rstrip("\r\n")):]
            lines[i] = "- Đã gửi mentor: %s%s" % (day, ending)
        elif len(status) != 1:
            return "%s có %d dòng `- Trạng thái:` trong khối đầu (cần đúng 1)" % (path, len(status))
        else:
            i = status[0]
            ending = lines[i][len(lines[i].rstrip("\r\n")):]
            if not ending:  # `Trạng thái` is the last line, without newline
                lines[i] += "\n"
            lines.insert(i + 1, "- Đã gửi mentor: %s%s" % (day, ending))
        return write_lines(path, lines)
    hits = [i for i in span if lines[i].rstrip("\r\n").rstrip() == old]
    if len(hits) != 1:
        where = "## Tổng kết" if kind == "da-lam" else "khối đầu"
        return "%s có %d dòng `%s` trong %s (cần đúng 1)" % (path, len(hits), old, where)
    i = hits[0]
    lines[i] = new + lines[i][len(lines[i].rstrip("\r\n")):]
    return write_lines(path, lines)


def write_lines(path, lines):
    """Write next to the post, then rename over it: a crash never leaves a half-written journal entry."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".%s." % os.path.basename(path))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write("".join(lines).encode("utf-8"))
        os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))
        os.replace(tmp, path)
    except OSError as exc:
        if os.path.exists(tmp):
            os.remove(tmp)
        return "không ghi được %s: %s" % (path, exc)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tiến độ nhật ký STAR và lệnh đánh dấu.")
    ap.add_argument("--dir", default=DEFAULT_DIR, help="thư mục nhật ký (mặc định %(default)s)")
    ap.add_argument("--today", help="ngày tính tiến độ YYYY-MM-DD (mặc định: ngày máy)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--da-lam", metavar="FILE", help="đánh dấu One Action đã làm")
    group.add_argument("--ket-qua", metavar="FILE", help="đánh dấu đã ghi kết quả thật")
    group.add_argument("--gui-mentor", metavar="FILE", help="ghi ngày đã gửi mentor (cần --ngay)")
    ap.add_argument("--ngay", help="ngày cho --gui-mentor, YYYY-MM-DD")
    args = ap.parse_args(argv)
    if args.da_lam or args.ket_qua or args.gui_mentor:
        if args.gui_mentor and parse_date(args.ngay or "") is None:
            print("Lỗi: --gui-mentor cần --ngay YYYY-MM-DD hợp lệ")
            return 1
        if args.ngay and not args.gui_mentor:
            print("Lỗi: --ngay chỉ dùng với --gui-mentor")
            return 1
        path = args.da_lam or args.ket_qua or args.gui_mentor
        kind = "da-lam" if args.da_lam else "ket-qua" if args.ket_qua else "gui-mentor"
        err = mark(path, kind, args.ngay)
        if err:
            print("Lỗi: %s. Không sửa file." % err)
            return 1
        done = {"da-lam": "Đã làm: rồi", "ket-qua": "Kết quả: đã ghi",
                "gui-mentor": "Đã gửi mentor: %s" % args.ngay}[kind]
        print("Đã đánh dấu %s · %s" % (path, done))
        return 0
    today = datetime.date.today() if args.today is None else parse_date(args.today)
    if today is None:
        print("Lỗi: --today cần dạng YYYY-MM-DD")
        return 1
    print("\n".join(report(args.dir, today)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
