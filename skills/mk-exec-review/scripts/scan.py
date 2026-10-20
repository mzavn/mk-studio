#!/usr/bin/env python3
"""Soi một bài markdown tiếng Việt để lấy số liệu cho buổi phản biện (chỉ thư viện chuẩn, chỉ đọc, đầu ra tất định).

  scan.py FILE [--glossary FILE] [--term CỤM]... [--keyword CỤM]...

  --glossary  file YAML có các dòng `term_vi:` / `term_en:` (mỗi mục bắt đầu bằng `- `); `term_vi: A (B)` → đếm cả A và B
  --term      cụm thuật ngữ cần đếm thêm (lặp được)
  --keyword   từ khoá tìm kiếm cần kiểm vị trí (tiêu đề, tóm tắt, 100 tiếng đầu, tiêu đề mục, thân bài)

In bốn phần: Tổng quan · Giọng AI (ứng viên) · Thuật ngữ · SEO/GEO/AEO. Mỗi phát hiện kèm `L<số dòng>` của file gốc.
Mọi dòng "ứng viên" chỉ là tín hiệu để người/agent đọc lại, không phải kết luận. Lỗi đọc file → thoát 1.
"""
import argparse
import re
import statistics
import sys
import unicodedata
from collections import Counter

TONES = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}  # huyền, sắc, ngã, hỏi, nặng
W = r"[^\W_]"  # một chữ cái/chữ số Unicode
QUESTION_WORDS = r"(là gì|vì sao|tại sao|như thế nào|thế nào|khi nào|bao nhiêu|có nên|làm sao|ở đâu|ai )"

AI_PATTERNS = [  # (nhãn, regex) — tiếng Việt, không phân biệt hoa thường
    ("mở bài sáo", r"trong (thời đại|kỷ nguyên|bối cảnh) (số|công nghệ|hiện nay|ngày nay|4\.0)"),
    ("không chỉ… mà còn…", r"không (chỉ|những)\b[^.!?\n]{1,80}?\bmà còn\b"),
    ("đối lập không phải… mà là…", r"không phải (là )?[^.!?\n]{1,60}?[,;]?\s*mà là\b"),
    ("từ phô trương", r"\b(then chốt|chìa kho[áa]|vô cùng|đáng kinh ngạc|toàn diện|vượt trội|bứt phá|nâng tầm|"
                      r"đột phá|cách mạng hoá|cách mạng hóa|tối ưu ho[áa]|hành trình|khám phá|bức tranh toàn cảnh|"
                      r"không thể phủ nhận|mang lại giá trị|thực sự|đóng vai trò (quan trọng|then chốt|chủ chốt))\b"),
    ("trạng từ rỗng", r"\bmột cách (hiệu quả|toàn diện|tối ưu|đáng kể|nhanh chóng|dễ dàng|chủ động)\b"),
    ("câu đệm", r"\b(điều quan trọng là|cần lưu ý rằng|đáng chú ý là|có thể nói|không thể không nhắc|"
                r"thực tế là|rõ ràng là)\b"),
    ("từ nối đầu câu", r"(^|[.!?]\s+)(hơn nữa|ngoài ra|bên cạnh đó|đặc biệt|tóm lại|nói tóm lại|nhìn chung|"
                       r"cuối cùng|tựu trung)\b"),
    ("tự hỏi tự đáp", r"(?<!nếu )\b(câu trả lời là|bạn có bao giờ tự hỏi|vậy đâu là|hãy tưởng tượng)\b"),
    ("mở/kết kiểu bài mẫu", r"\b(trong bài viết này|hy vọng bài viết|hãy cùng (tìm hiểu|khám phá)|hãy bắt đầu)\b"),
    ("câu dịch từ tiếng Anh", r"\b(đây là lý do (tại sao|vì sao)|điều này là bởi vì|chơi (một )?vai trò|vào cuối ngày|"
                              r"được thực hiện bởi|là chìa kho[áa] để|đây là nơi)\b"),
]
PASSIVE_VERBS = "cấp|gửi|ghi|ghi nhận|tính|gắn|lưu|xử lý|dùng|sử dụng|giữ|đánh dấu|cập nhật|gộp|xác nhận|xác minh|tạo|chuyển|đưa|chọn|thêm|sửa|xoá|xóa|hiển thị|đặt|bán|chăm sóc|thiết kế|xây dựng|triển khai|áp dụng|kiểm tra|phê duyệt|duyệt|giao|đào tạo|tuyển|trả|thanh toán|đăng|chia sẻ|báo cáo|thông báo|nhắc|liên hệ|phân|phân loại|định nghĩa|gọi|coi|xem|biết đến|nhắc đến|đề cập|thực hiện|hoàn thành|tích hợp|đồng bộ|nhập|xuất|tải|cài|bảo vệ|mã hoá|mã hóa|lưu trữ|ghi lại|đo|đếm|chấm|đánh giá|phát hiện|nhận ra|ưu tiên|hỗ trợ|quản lý|tổ chức|sắp xếp|thu thập|tổng hợp|dựng|nhận diện|hợp nhất|tách|ghép|sinh|lập|mở|đóng|khoá|khóa|đảm bảo|bảo đảm|cho phép|yêu cầu|mời|giới thiệu|tặng|giảm|tăng|miễn|hoàn|hướng dẫn|đọc|viết|in|chụp|quay|ký|ban hành|công bố|phát hành"  # "được" + động từ này → ứng viên bị động
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
STOP = set("là của và có một những các cho được bị trong thì mà này đó không với khi đã sẽ đang để từ về ra vào "
           "cũng như nhưng hay hoặc rồi lại nó họ ta bạn chị anh em cái thế nào nếu vì nên còn đều".split())
VN_SYLLABLE = re.compile(r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdghklmnprstvx])?"
                         r"(oai|oay|uya|uyu|uay|ai|ao|au|ay|eo|ia|iu|oa|oe|oi|ua|ue|ui|uy|[aeiouy])"
                         r"(ch|ng|nh|[cmnpt])?$")


def die(msg):
    print("Lỗi: " + msg, file=sys.stderr)
    sys.exit(1)


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return unicodedata.normalize("NFC", fh.read()).split("\n")
    except (OSError, UnicodeDecodeError) as exc:
        die("không đọc được %s: %s" % (path, exc))


COMMENTS = set()  # số dòng có chú thích HTML, in riêng để kiểm bằng mắt


def split_doc(lines):
    """→ (frontmatter, thân bài [(số dòng, nội dung)] bỏ khối code và chân bài, dải dòng chân bài | None).

    Chân bài = phần sau đường kẻ `---` cuối cùng nếu còn ≤ 8 dòng có chữ (ngày cập nhật, lịch sử).
    """
    meta, start = {}, 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for raw in lines[1:i]:
                    m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
                    if m:
                        meta[m.group(1)] = m.group(2).strip().strip('"').strip("'")
                start = i + 1
                break
    body, fence, comment = [], False, False
    for n in range(start, len(lines)):
        if lines[n].lstrip().startswith("```") and not comment:
            fence = not fence
            continue
        if fence:
            continue
        text, kept = lines[n], ""
        while text:  # bỏ chú thích HTML <!-- … --> (có thể nhiều dòng): người đọc không thấy
            if comment:
                end = text.find("-->")
                COMMENTS.add(n + 1)
                if end < 0:
                    text = ""
                else:
                    text, comment = text[end + 3:], False
            else:
                begin = text.find("<!--")
                if begin < 0:
                    kept, text = kept + text, ""
                else:
                    kept, text, comment = kept + text[:begin], text[begin + 4:], True
                    COMMENTS.add(n + 1)
        body.append((n + 1, kept))
    rules = [i for i, (_, l) in enumerate(body) if l.strip() == "---"]
    if rules and sum(1 for _, l in body[rules[-1] + 1:] if l.strip()) <= 8:
        last = max(n for n, l in body[rules[-1]:] if l.strip())
        footer = (body[rules[-1]][0], last)
        return meta, body[:rules[-1]], footer
    return meta, body, None


def plain(text):
    """Bỏ cú pháp markdown giữ chữ: link, mã neo, in đậm/nghiêng, đầu dòng."""
    text = re.sub(r"\{#[^}]*\}", "", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s*(#+|[-*+]|\d+\.)\s+", "", text)
    return re.sub(r"[*_`>]", "", text)


def syllables(text):
    return re.findall(W + r"+", text)


def tone_key(word):
    """Khoá không phụ thuộc vị trí dấu thanh: hoá/hóa, thuỷ/thủy → cùng khoá."""
    nfd = unicodedata.normalize("NFD", word.lower())
    tones = [c for c in nfd if c in TONES]
    return "".join(c for c in nfd if c not in TONES) + "".join(tones)


def is_foreign(token):
    """Chữ không dấu không thể là một tiếng Việt (shop, email, re-targeting) hoặc viết tắt in hoa (CEO, CSKH)."""
    if len(token) < 2 or not token.isascii() or not (token.isalpha() or "-" in token):
        return False
    if "-" in token or (token.isupper() and len(token) >= 2):
        return True
    return not VN_SYLLABLE.match(token.lower())


def find_all(pattern, body, flags=re.I):
    hits = []
    for n, line in body:
        for m in re.finditer(pattern, plain(line), flags):
            hits.append((n, m.group(0).strip().lstrip(".!?… ")))
    return hits


def term_regex(term):
    return r"(?<!%s)%s(?!%s)" % (W, re.escape(term), W)


def parse_glossary(path):
    """→ [(tên chính, [biến thể trong ngoặc])]: `term_vi: Sổ khách (sổ cái)` → ("Sổ khách", ["sổ cái"])."""
    groups, main, paren = [], [], []
    for raw in read(path) + ["- "]:
        if re.match(r"^\s*-\s", raw) and (main or paren):
            groups.append((main, paren))
            main, paren = [], []
        m = re.match(r"^\s*-?\s*(term_vi|term_en):\s*(.+?)\s*$", raw)
        if m:
            value = m.group(2).strip('"').strip("'")
            paren.extend(p.strip() for p in re.findall(r"\(([^)]+)\)", value) if p.strip())
            head = re.sub(r"\s*\([^)]*\)", "", value).strip()
            if head:
                main.append(head)
    return groups


def lines_of(hits, limit=8):
    ns = sorted({n for n, _ in hits})
    more = " …+%d" % (len(ns) - limit) if len(ns) > limit else ""
    return " ".join("L%d" % n for n in ns[:limit]) + more


def overview(meta, body):
    print("== Tổng quan")
    paras, cur, sentences = [], [], []
    for n, line in body:
        text = plain(line).strip()
        if not text or line.lstrip().startswith("#") or text == "---":
            if cur:
                paras.append(cur)
            cur = []
            continue
        cur.append(n)
        for s in re.split(r"(?<=[.!?…])\s+", text):
            k = len(syllables(s))
            if k:
                sentences.append((k, n))
    if cur:
        paras.append(cur)
    lens = [k for k, _ in sentences]
    total = sum(len(syllables(plain(l))) for _, l in body)
    print("Số tiếng (âm tiết) thân bài: %d · đoạn: %d · câu: %d" % (total, len(paras), len(lens)))
    if lens:
        print("Độ dài câu: trung bình %.1f · độ lệch %.1f · ngắn nhất %d · dài nhất %d"
              % (statistics.mean(lens), statistics.pstdev(lens), min(lens), max(lens)))
        long_ = sorted([s for s in sentences if s[0] > 35], key=lambda s: (-s[0], s[1]))
        if long_:
            print("Câu trên 35 tiếng: " + " ".join("L%d(%d)" % (n, k) for k, n in long_[:8]))
    one = [p[0] for p in paras if len(p) == 1 and len(syllables(plain(dict(body)[p[0]]))) <= 15]
    if one:
        print("Đoạn một dòng ngắn (≤15 tiếng): %d — %s" % (len(one), " ".join("L%d" % n for n in one[:12])))
    print()


def ai_signals(body):
    print("== Giọng AI (ứng viên — đọc lại từng chỗ, không kết luận từ con số)")
    found = False
    for label, pattern in AI_PATTERNS:
        hits = find_all(pattern, body)
        if hits:
            found = True
            words = Counter(h.lower() for _, h in hits)
            print("- %s: %d · %s · %s" % (label, len(hits), ", ".join('"%s"' % w for w in sorted(words)),
                                         lines_of(hits)))
    dash = [(n, "—") for n, l in body for _ in range(l.count("—"))]
    if dash:
        found = True
        print("- gạch dài —: %d · %s" % (len(dash), lines_of(dash)))
    emoji = [(n, m) for n, l in body for m in EMOJI.findall(l)]
    if emoji:
        found = True
        print("- emoji: %d · %s" % (len(emoji), lines_of(emoji)))
    bullets = [(n, l) for n, l in body if re.match(r"^\s*([-*+]|\d+\.)\s+", l)]
    bold = [(n, l) for n, l in bullets if re.match(r"^\s*([-*+]|\d+\.)\s+\*\*", l)]
    if bullets:
        print("- gạch đầu dòng mở bằng in đậm: %d/%d" % (len(bold), len(bullets)))
    bi = find_all(r"(?<!chuẩn )(?<!thiết )(?<!trang )(?<!dự )(?<!phòng )\bbị\b", body)  # bỏ chuẩn bị, thiết bị…
    duoc_verb = find_all(r"\bđược\s+(%s)\b" % PASSIVE_VERBS, body)
    duoc_all = find_all(r"\bđược\b", body)
    if bi or duoc_verb:
        hits = bi + duoc_verb
        print("- ứng viên câu bị động (\"bị …\", \"được\" + động từ): %d · %s" % (len(hits), lines_of(hits, 12)))
    other = len(duoc_all) - len(duoc_verb)
    if other:
        print("- \"được\" khác (thường nghĩa có thể/nhận, không tính bị động): %d" % other)
    if not found:
        print("- không thấy cụm sáo trong danh sách")
    print()


def context(line, term, width=3):
    """Trích `width` tiếng hai bên chỗ xuất hiện đầu tiên của term trong dòng."""
    text = plain(line)
    m = re.search(term_regex(term), text, re.I)
    left = syllables(text[:m.start()])[-width:]
    right = syllables(text[m.end():])[:width]
    return " ".join(left + [m.group(0)] + right)


def count_term(t, body):
    hits = find_all(term_regex(t), body)
    return '"%s" %d%s' % (t, len(hits), (" · " + lines_of(hits, 6)) if hits else ""), hits


def sentence_start(text, pos):
    return not text[:pos].strip() or text[:pos].rstrip()[-1] in ".!?:…"


def terms(meta, body, glossary, extra):
    print("== Thuật ngữ")
    groups = (parse_glossary(glossary) if glossary else []) + [([t], []) for t in extra]
    lines = dict(body)
    for main, paren in groups:
        print("- " + " | ".join(count_term(t, body)[0] for t in main))
        for t in paren:
            hits = count_term(t, body)[1]
            where = ", ".join('L%d "…%s…"' % (n, context(lines[n], t)) for n in sorted({n for n, _ in hits}))
            print('  trong ngoặc của bảng (biến thể được phép/ẩn dụ — không gộp): "%s" %d%s'
                  % (t, len(hits), (" · " + where) if hits else ""))
    words = {}
    for n, line in body:
        for w in syllables(plain(line)):
            words.setdefault(tone_key(w), {}).setdefault(w.lower(), []).append(n)
    tone = [v for v in words.values() if len(v) > 1]
    for v in sorted(tone, key=lambda v: sorted(v)):
        print("- bỏ dấu khác nhau: " + " | ".join('"%s" %s' % (w, lines_of([(n, w) for n in v[w]], 6))
                                                for w in sorted(v)))
    latin, first = {}, {}
    for n, line in body:
        text = plain(line)
        quotes = [q.span() for q in re.finditer(r"[\"“][^\"”]*[\"”]", text)]
        for m in re.finditer(r"[^\W_]+(?:-[^\W_]+)*", text):
            w = m.group(0)
            if not is_foreign(w):
                continue
            if sentence_start(text, m.start()) and w[0].isupper() and w[1:].islower():
                w = w.lower()  # viết hoa vì đầu câu, không phải biến thể
            first.setdefault(w.lower(), (w, n))
            if not any(a < m.start() < b for a, b in quotes):  # lời thoại, tên trong ngoặc kép: không so
                latin.setdefault(w.lower().replace("-", ""), {}).setdefault(w, []).append(n)
    for v in sorted(latin.values(), key=lambda v: sorted(v)):
        if len(v) > 1:
            print("- viết khác nhau: " + " | ".join('"%s" %s' % (w, lines_of([(n, w) for n in v[w]], 6))
                                                  for w in sorted(v)))
    if first:
        print("- chữ nước ngoài/viết tắt, dòng đầu tiên (đã giải thích chưa?): "
              + ", ".join("%s L%d" % first[k] for k in sorted(first)))
    bold, quoted = Counter(), Counter()
    for _, line in body:
        for m in re.findall(r"\*\*([^*]{2,60}?)\*\*", line):
            phrase = m.strip(" .:,")
            if 1 <= len(syllables(phrase)) <= 6:
                bold[phrase] += 1
        for m in re.findall(r"[\"“]([^\"”]{2,60}?)[\"”]", line):
            phrase = m.strip(" .:,")
            if 2 <= len(syllables(phrase)) <= 6:
                quoted[phrase] += 1
    if bold:
        print("- cụm in đậm ngắn (ứng viên thuật ngữ tác giả đặt): " + ", ".join('"%s"' % p for p in sorted(bold)))
    again = [p for p in sorted(quoted) if len(find_all(term_regex(p), body)) >= 2]
    if again:
        print("- cụm trong ngoặc kép xuất hiện ≥2 lần: " + ", ".join('"%s"' % p for p in again))
    grams = Counter()
    for _, line in body:
        toks = [w.lower() for w in syllables(plain(line))]
        for size in (2, 3):
            for i in range(len(toks) - size + 1):
                g = toks[i:i + size]
                if g[0] not in STOP and g[-1] not in STOP:
                    grams[" ".join(g)] += 1
    drop = set()  # cụm 2 tiếng nằm trọn trong cụm 3 tiếng cùng số lần ("số điện" ⊂ "số điện thoại")
    for t, c in grams.items():
        words3 = t.split()
        if len(words3) == 3:
            drop.update(b for b in (" ".join(words3[:2]), " ".join(words3[1:])) if grams[b] == c)
    for b in drop:
        del grams[b]
    top = sorted([(c, g) for g, c in grams.items() if c >= 3], key=lambda x: (-x[0], x[1]))[:15]
    if top:
        print("- cụm lặp ≥3 lần: " + ", ".join("%s (%d)" % (g, c) for c, g in top))
    print()


def seo(meta, body, keywords):
    print("== SEO/GEO/AEO")
    title = meta.get("title", "")
    summary = meta.get("summary") or meta.get("description", "")
    print("Tiêu đề: %d ký tự%s" % (len(title), "" if title else " (không có `title` trong frontmatter)"))
    print("Tóm tắt (summary/description): %d ký tự%s" % (len(summary), "" if summary else " (không có)"))
    heads = [(n, l) for n, l in body if re.match(r"^#{1,6}\s", l)]
    h1 = [n for n, l in heads if re.match(r"^#\s", l)]
    if h1:
        print("Có # tiêu đề trong thân bài: " + " ".join("L%d" % n for n in h1))
    for n, l in heads:
        level = len(l) - len(l.lstrip("#"))
        text = plain(l).strip()
        tags = []
        if "?" in text or re.search(QUESTION_WORDS, text.lower() + " "):
            tags.append("dạng câu hỏi")
        if level == 2 and not re.search(r"\{#[a-z][a-z0-9-]*\}\s*$", l):
            tags.append("thiếu mã neo")
        print("  L%d %s %s%s" % (n, "#" * level, text, (" [" + ", ".join(tags) + "]") if tags else ""))
    first = []
    for _, line in body:
        if not line.lstrip().startswith("#"):
            first.extend(syllables(plain(line)))
        if len(first) >= 100:
            break
    first100 = " ".join(first[:100]).lower()
    body_text = " ".join(plain(l) for _, l in body)
    for kw in keywords:
        k = kw.lower()
        rx = term_regex(k)
        where = [name for name, txt in (("tiêu đề", title), ("tóm tắt", summary), ("100 tiếng đầu", first100),
                                        ("tiêu đề mục", " ".join(plain(l) for _, l in heads)))
                 if re.search(rx, txt.lower())]
        print('Từ khoá "%s": thân bài %d lần · có ở: %s' % (kw, len(re.findall(rx, body_text.lower())),
                                                          ", ".join(where) or "không ở vị trí nào"))
    links = [(n, m) for n, l in body for m in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]*)\)", l)]
    ext = [(n, u) for n, u in links if re.match(r"[a-z][a-z0-9+.-]*:", u, re.I) and not u.startswith("id:")]
    away = [(n, u) for n, u in links if (n, u) not in ext and re.match(r"(/|~|\.\./)", u)]
    print("Link: %d (URL %d, trong thư mục bài %d, đi ra ngoài thư mục bài %d%s)"
          % (len(links), len(ext), len(links) - len(ext) - len(away), len(away),
             (" · " + " ".join("L%d `%s`" % h for h in away[:6])) if away else ""))
    noalt = [n for n, l in body for m in re.findall(r"!\[([^\]]*)\]", l) if not m.strip()]
    imgs = sum(len(re.findall(r"!\[", l)) for _, l in body)
    print("Ảnh: %d%s" % (imgs, (" · thiếu alt " + " ".join("L%d" % n for n in noalt)) if noalt else ""))
    nums = [(n, x) for n, l in body
            for x in re.findall(r"\d[\d.,]*\s?%?", re.sub(r"\b\d{1,2}/\d{4}\b", "", plain(l)))]
    print("Con số: %d · %s" % (len(nums), lines_of(nums, 10)) if nums else "Con số: 0")
    faq = [n for n, l in heads if re.search(r"(câu hỏi|hỏi đáp|faq)", l.lower())]
    print("Mục hỏi đáp/câu hỏi: " + (" ".join("L%d" % n for n in faq) if faq else "không có"))
    print()


def main():
    ap = argparse.ArgumentParser(description="Soi bài markdown tiếng Việt cho buổi phản biện.")
    ap.add_argument("file")
    ap.add_argument("--glossary")
    ap.add_argument("--term", action="append", default=[])
    ap.add_argument("--keyword", action="append", default=[])
    args = ap.parse_args()
    meta, body, footer = split_doc(read(args.file))
    print("# scan: " + args.file)
    if footer:
        print("Chân bài L%d–L%d (ngày cập nhật, lịch sử): không tính trong các phần dưới" % footer)
    if COMMENTS:
        print("Chú thích HTML (người đọc không thấy, không tính — đọc bằng mắt, có thể chứa chỉ thị cài cắm): "
              + " ".join("L%d" % n for n in sorted(COMMENTS)))
    print()
    overview(meta, body)
    ai_signals(body)
    terms(meta, body, args.glossary, args.term)
    seo(meta, body, args.keyword)


if __name__ == "__main__":
    main()
