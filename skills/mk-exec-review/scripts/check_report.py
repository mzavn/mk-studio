#!/usr/bin/env python3
"""Kiểm cơ học bảng gợi ý (mục 7) của báo cáo phản biện so với file bài (chỉ thư viện chuẩn, chỉ đọc, tất định).

  check_report.py BÁO_CÁO BÀI

Mỗi dòng bảng: `| Mã | Mức | Dòng | Loại | Hiện tại | Đề xuất | Vì sao |`. Đoạn văn bài nằm trong backtick
(`…`, có backtick bên trong thì ``…``). Nhiều chỗ / nhiều phương án: cặp `trước` → `sau`, cách nhau bằng <br>.

In mỗi mã một dòng `OK` hoặc `⚠ …`:
  không khớp file / trùng N lần   đoạn "trước" phải có đúng 1 lần trong bài
  lệch dòng                       đoạn có thật nhưng ở dòng khác cột Dòng
  đã áp (không ⚠)                 không thấy "trước" nhưng thấy "sau" (mã đã sửa ở lần trước)
  đổi nhãn → câu                  loại `chữ` mà đổi quá 3 tiếng hoặc chèn chữ mới
  chữ nước ngoài mới              đề xuất thêm chữ nước ngoài/viết tắt không có ở đoạn gốc
  đổi nhãn → meta / → không meta  loại `meta` ⇔ đoạn nằm trong frontmatter
  số mới                          đề xuất có chữ số không có ở đoạn gốc (ngoài ô [điền: …])
  đổi nhãn → cấu trúc             đổi chữ trên dòng tiêu đề mục `#…` mà loại không phải `cấu trúc`
  thêm nhưng xoá đoạn gốc         loại `thêm` mà "sau" không chứa nguyên "trước"
  làm mềm khẳng định              đề xuất thêm "có thể", "thường", "có lẽ"… mà đoạn gốc không có
  ký tự vô hình mới               đề xuất có ký tự định dạng vô hình (U+200B…) mà đoạn gốc không có
  đổi link/ảnh/neo/HTML           đích link, ảnh, mã neo {#…}, thẻ HTML hoặc URL khác đoạn gốc
  sai khuôn                       mã/mức/loại không hợp lệ, mã trùng
Cuối cùng: thứ tự bảng (mức Cao → Thấp, cùng mức theo dòng), mã liên tục, đủ mục 1–9.
Không đọc được file / không thấy bảng → thoát 1.
"""
import difflib
import os
import re
import sys
import unicodedata

sys.dont_write_bytecode = True  # không để __pycache__ trong thư mục skill
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan import is_foreign  # noqa: E402

HEDGES = ("có thể", "thường", "có lẽ", "phần nào", "dường như")  # thêm vào câu tác giả nói chắc = làm mềm
MAX_ROW = 5000  # dòng bảng dài hơn → sai khuôn (và tránh quét backtick quá lâu)
LEVELS = {"Cao": 0, "Vừa": 1, "Thấp": 2}
KINDS = {"chữ", "câu", "thêm", "cấu trúc", "meta", "thuật ngữ"}
SPAN = re.compile(r"(`+)(.+?)\1", re.S)
PAIR = re.compile(r"(`+)(.+?)\1\s*→\s*(`+)(.*?)\3", re.S)


def die(msg):
    print("Lỗi: " + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return unicodedata.normalize("NFC", fh.read())
    except (OSError, UnicodeDecodeError) as exc:
        die("không đọc được %s: %s" % (path, exc))


def code(text):
    """Nội dung một code span: ``…`` bỏ một khoảng trắng đầu/cuối như CommonMark."""
    return text[1:-1] if len(text) > 2 and text[0] == text[-1] == " " else text


def cells(row):
    """Tách ô bảng theo `|`, không tách bên trong backtick."""
    out, cur, i = [], "", 0
    while i < len(row):
        m = SPAN.match(row, i) if row[i] == "`" else None
        if m:
            cur += m.group(0)
            i = m.end()
        elif row[i] == "|":
            out.append(cur.strip())
            cur = ""
            i += 1
        else:
            cur += row[i]
            i += 1
    out.append(cur.strip())
    return out[1:-1] if row.strip().startswith("|") else out


def table(report):
    m = re.search(r"^## 7\..*?$(.*?)(?=^## |\Z)", report, re.M | re.S)
    if not m:
        die("không thấy mục `## 7.` (danh sách gợi ý) trong báo cáo")
    rows = []
    for line in m.group(1).split("\n"):
        if not line.strip().startswith("|"):
            continue
        if len(line) > MAX_ROW:
            die("một dòng ở mục 7 dài hơn %d ký tự — báo cáo sai khuôn, gửi lại subagent" % MAX_ROW)
        c = cells(line)
        if len(c) < 6 or c[0] in ("Mã", "") or set(c[0]) <= set("-: "):
            continue
        rows.append(c)
    if not rows:
        die("mục 7 không có dòng gợi ý nào")
    return rows


def where(article, snippet):
    """→ [số dòng bắt đầu] của mọi lần đoạn xuất hiện."""
    out, start = [], article.find(snippet)
    while start != -1:
        out.append(article.count("\n", 0, start) + 1)
        start = article.find(snippet, start + 1)
    return out


def words(text):
    """Chữ của đoạn, bỏ ô [điền: …], mã neo {#…} và đích link (…)."""
    text = re.sub(r"\[điền[^\]]*\]|\{#[^}]*\}|\]\([^)]*\)", " ", text)
    return re.findall(r"[^\W_]+(?:-[^\W_]+)*", text)


def count_word(phrase, text):
    return len(re.findall(r"(?<![^\W_])%s(?![^\W_])" % re.escape(phrase), text.lower()))


def markup(text):
    """Link, ảnh, mã neo, thẻ HTML, URL của đoạn — phần `words()` bỏ qua nên phải so riêng."""
    return (sorted(re.findall(r"\]\(([^)]*)\)", text)), sorted(re.findall(r"\{#[^}]*\}", text)), text.count("!["),
            sorted(re.findall(r"<[A-Za-z/!][^>]*>", text)), sorted(re.findall(r"https?://[^\s)>\]]+", text)))


def changed(before, after):
    """→ (số tiếng thay/xoá/chèn, có chèn chữ không có trong đoạn gốc không)."""
    a, b = [w.lower() for w in words(before)], [w.lower() for w in words(after)]
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    size = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in ops if tag != "equal")
    return size, any(tag == "insert" and set(b[j1:j2]) - set(a) for tag, i1, i2, j1, j2 in ops)


def frontmatter_end(article):
    lines = article.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def check(row, article, fm_end):
    mã, mức, dòng, loại, hiện, đề = row[:6]
    warn = []
    if not re.match(r"^[CATSY]\d+$", mã) or mức not in LEVELS or loại not in KINDS:
        warn.append("sai khuôn (mã %s, mức %s, loại %s)" % (mã, mức, loại))
    if re.search(r"(^|[\s,;])[\w./-]+\.(ya?ml|json|toml|md):", dòng) and not dòng.lstrip().startswith("L"):
        return warn + ["ngoài bài — kiểm tay: %s" % dòng], []
    pairs = [(code(m.group(2)), code(m.group(4))) for m in PAIR.finditer(đề)]
    if not pairs:
        befores = [code(m.group(2)) for m in SPAN.finditer(hiện)]
        afters = [code(m.group(2)) for m in SPAN.finditer(đề)] or [""]
        pairs = [(b, a) for b in befores for a in afters]
    if not pairs:
        return (warn if mã.startswith("Y") else warn + ["sai khuôn: không có đoạn `…` để đối chiếu"]), []
    refs = set()
    for a, b in re.findall(r"L(\d+)(?:\s*[–-]\s*L?(\d+))?", dòng):
        refs.update(range(int(a), int(b or a) + 1))
    applied = []
    lines = article.split("\n")
    for before, after in pairs:
        found = where(article, before)
        short = before if len(before) <= 40 else before[:37] + "…"
        if not found and after and after not in before and len(where(article, after)) == 1:
            applied.append("`%s`" % (after if len(after) <= 40 else after[:37] + "…"))
            continue
        if len(found) != 1:
            warn.append("%s: `%s` %d lần" % ("không khớp file" if not found else "trùng", short, len(found)))
            continue
        line = found[0]
        if refs and line not in refs:
            warn.append("lệch dòng: `%s` ở L%d" % (short, line))
        in_fm = line <= fm_end
        if loại == "meta" and not in_fm:
            warn.append("đổi nhãn → không meta: `%s` ở thân bài L%d" % (short, line))
        if loại != "meta" and in_fm:
            warn.append("đổi nhãn → meta: `%s` ở frontmatter L%d" % (short, line))
        if not in_fm and lines[line - 1].lstrip().startswith("#") and loại != "cấu trúc" and before != after:
            warn.append("đổi nhãn → cấu trúc: đổi tiêu đề mục L%d" % line)
        if loại == "thêm" and before not in after:
            warn.append("thêm nhưng xoá đoạn gốc: \"sau\" phải chứa nguyên \"trước\"")
        if markup(before) != markup(after):
            warn.append("đổi link/ảnh/neo/HTML — kiểm bằng mắt, không duyệt hàng loạt")
        size, inserted = changed(before, after)
        if loại == "chữ" and (size > 3 or inserted):
            warn.append("đổi nhãn → câu: %s" % ("chèn chữ mới" if size <= 3 else "đổi %d tiếng" % size))
        old = {w.lower() for w in words(before)}
        foreign = sorted({w for w in words(after) if is_foreign(w) and w.lower() not in old})
        if foreign:
            warn.append("chữ nước ngoài mới: %s" % ", ".join(foreign))
        new = set(re.findall(r"\d+", re.sub(r"\[điền[^\]]*\]", "", after))) - set(re.findall(r"\d+", before))
        if new:
            warn.append("số mới: %s" % ", ".join(sorted(new)))
        softer = [h for h in HEDGES if count_word(h, after) > count_word(h, before)]
        if softer:
            warn.append("làm mềm khẳng định: thêm %s" % ", ".join('"%s"' % h for h in softer))
        hidden = sorted({"U+%04X" % ord(c) for c in after if unicodedata.category(c) == "Cf"}
                        - {"U+%04X" % ord(c) for c in before if unicodedata.category(c) == "Cf"})
        if hidden:
            warn.append("ký tự vô hình mới: %s" % ", ".join(hidden))
    return list(dict.fromkeys(warn)), applied  # bỏ cảnh báo lặp (nhiều phương án cùng đoạn "trước")


def missing_sections(report):
    have = set(re.findall(r"^## (\d+)\.", report, re.M))
    return [str(i) for i in range(1, 10) if str(i) not in have]


def numbering(rows):
    """Mã phải liên tục trong từng chữ cái: A1, A2… (không thiếu số)."""
    by = {}
    for row in rows:
        m = re.match(r"^([CATSY])(\d+)$", row[0])
        if m:
            by.setdefault(m.group(1), set()).add(int(m.group(2)))
    gaps = ["%s%d" % (k, i) for k, nums in sorted(by.items()) for i in range(1, max(nums) + 1) if i not in nums]
    return gaps


def main():
    if len(sys.argv) != 3:
        die("dùng: check_report.py BÁO_CÁO BÀI")
    report, article = read(sys.argv[1]), read(sys.argv[2])
    rows = table(report)
    fm_end, seen, keys, flagged = frontmatter_end(article), set(), [], 0
    for row in rows:
        warn, applied = check(row, article, fm_end)
        if row[0] in seen:
            warn.insert(0, "sai khuôn: mã trùng")
        seen.add(row[0])
        flagged += bool(warn)
        parts = (["⚠ " + " · ".join(warn)] if warn else []) + (["đã áp: " + ", ".join(applied)] if applied else [])
        print("%s %s" % (row[0], " · ".join(parts) or "OK"))
        first = re.search(r"L(\d+)", row[2])
        keys.append((LEVELS.get(row[1], 3), int(first.group(1)) if first else 10 ** 9))
    print("Thứ tự bảng: " + ("đúng" if keys == sorted(keys) else "chưa theo mức → dòng"))
    gaps = numbering(rows)
    print("Đánh mã: " + ("liên tục" if not gaps else "thiếu " + ", ".join(gaps)))
    missing = missing_sections(report)
    print("Mục báo cáo: " + ("đủ 1–9" if not missing else "thiếu mục " + ", ".join(missing)))
    print("Tổng: %d mã · %d có ⚠" % (len(rows), flagged))


if __name__ == "__main__":
    main()
