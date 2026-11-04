#!/usr/bin/env python3
"""Đọc, kiểm và ghi có kiểm soát file KAIZEN.md — luật riêng của dự án cho các skill mk.

  kaizen.py find PATH...                         KAIZEN.md theo luật tìm, gần trước xa sau
  kaizen.py list PATH... [--skill mk:x] [--all]  luật đang áp dụng sau thứ tự ưu tiên (kèm file:dòng, mã)
  kaizen.py check FILE                           định dạng, mã trùng, giá trị hợp lệ, Thay cho, luật trùng
  kaizen.py add FILE --skill S --loai L --luat "…" --nguon "…" [--thay-cho K-NNN] [--ngay YYYY-MM-DD]
                [--tao [--ten "<tên dự án>"]]      thêm mục mới cuối file (mã kế tiếp)
  kaizen.py promote PATH...                      ứng viên đưa vào skill (≥2 dự án, hoặc loại lỗi ≥3 lần); chỉ in
  kaizen.py set-status FILE K-NNN --trang-thai "đã vào skill vX.Y.Z"|bỏ

Luật tìm: điểm đầu = thư mục chứa mỗi PATH (PATH là thư mục thì chính nó); từ đó đi lên tới thư mục có `.git`.
Không bao giờ đọc KAIZEN.md ở thư mục nhà ($HOME), thư mục cao hơn nó, hay gốc ổ đĩa. KAIZEN.md là symlink → bỏ
qua, có Cảnh báo. Nhiều điểm đầu: gộp, xếp theo số bậc đi lên (ít bậc = gần), hoà thì theo thứ tự PATH.
Chỉ add/set-status ghi, và chỉ ghi đúng FILE tên KAIZEN.md (không symlink), qua file tạm cùng thư mục rồi thay
thế; add không sửa mục cũ, trừ trạng thái mục ghi ở --thay-cho. Ngày mặc định = ngày theo giờ máy.
Thoát: 0 xong/qua; 1 lỗi hoặc check có LỖI; 2 sai cách gọi.
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import tempfile
import unicodedata

sys.dont_write_bytecode = True

NAME = "KAIZEN.md"
LOAI = ("lỗi", "yêu-cầu", "thảo-luận")
ACTIVE = "đang áp dụng"
DROPPED = "bỏ"
SHIPPED = re.compile(r"^đã vào skill v\d+\.\d+\.\d+$")
SKILL = re.compile(r"^(?:mk:[a-z0-9]+(?:-[a-z0-9]+)*|\*)$")
ID = re.compile(r"^K-\d{3,}$")
HEAD = re.compile(r"^## (.*)$")
FIELD = re.compile(r"^- ([^:]+): ?(.*)$")
FIELDS = ("Luật", "Nguồn", "Ngày", "Thay cho")
REQUIRED = ("Luật", "Nguồn", "Ngày")
SEP = " · "
HIDDEN = ("Cc", "Zl", "Zp")  # ký tự điều khiển, ngắt dòng/đoạn Unicode
BLURB = ("> Luật riêng của dự án cho các skill mk. Mục \"đang áp dụng\" ghi đè mặc định của skill, "
         "không ghi đè Chính sách an toàn.")


def shown(s):
    """Thoát ký tự điều khiển/ngắt dòng ẩn để chữ trong file không giả được dòng in ra."""
    out = []
    for c in s:
        if unicodedata.category(c) in HIDDEN:
            out.append("\\x%02x" % ord(c) if ord(c) < 256 else "\\u%04x" % ord(c))
        else:
            out.append(c)
    return "".join(out)


def say(s):
    print(shown(s))


def die(msg):
    print("Lỗi: " + shown(msg), file=sys.stderr)
    sys.exit(1)


def nfc(s):
    return unicodedata.normalize("NFC", s)


def has_hidden(s):
    return any(unicodedata.category(c) in HIDDEN for c in s)


def norm_rule(s):
    s = " ".join(nfc(s).casefold().split())
    return s.rstrip(" .")


def valid_status(s):
    return s in (ACTIVE, DROPPED) or bool(SHIPPED.match(s))


class Entry:
    def __init__(self, path, line, id_, skill, loai, status):
        self.path, self.line, self.id, self.skill, self.loai, self.status = path, line, id_, skill, loai, status
        self.fields = {}
        self.bad = False  # mục có lỗi định dạng → không áp

    @property
    def rule(self):
        return self.fields.get("Luật", ("", 0))[0]

    @property
    def active(self):
        return self.status == ACTIVE


def split_lines(text):
    """Chỉ ngắt ở \\n (bỏ \\r cuối dòng) — giống cách người mở file bằng trình soạn thảo thấy."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [l[:-1] if l.endswith("\r") else l for l in lines]


def parse(path):
    """Trả về (danh sách Entry, danh sách (dòng, lỗi), có tiêu đề). Không đổi file."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        die("không đọc được %s (%s)" % (path, exc.strerror or exc))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        die("%s không phải UTF-8" % path)
    lines = split_lines(nfc(text))
    entries, errors, cur, heads = [], [], None, []
    first = next((i for i, l in enumerate(lines) if l.strip()), None)
    has_title = first is not None and lines[first].startswith("# KAIZEN")
    if not has_title:
        errors.append((1 if first is None else first + 1, "thiếu tiêu đề `# KAIZEN — <tên dự án>` ở dòng đầu"))
    for i, line in enumerate(lines, 1):
        if has_hidden(line):
            errors.append((i, "dòng có ký tự điều khiển hoặc ngắt dòng ẩn (%s)"
                           % ", ".join(sorted({shown(c) for c in line if unicodedata.category(c) in HIDDEN}))))
        m = HEAD.match(line)
        if m:
            parts = m.group(1).split(SEP)
            cur = None
            if len(parts) != 4:
                heads.append((i, None))
                errors.append((i, "đầu mục sai dạng, cần `## K-NNN · <skill> · <loại> · <trạng thái>`"))
                continue
            id_, skill, loai, status = (p.strip() for p in parts)
            cur = Entry(path, i, id_, skill, loai, status)
            entries.append(cur)
            heads.append((i, cur))
            if not ID.match(id_):
                errors.append((i, "mã `%s` sai dạng, cần K-NNN" % id_))
            if not SKILL.match(skill):
                errors.append((i, "skill `%s` sai, cần mk:<tên> hoặc *" % skill))
            if loai not in LOAI:
                errors.append((i, "loại `%s` sai, cần một trong: %s" % (loai, ", ".join(LOAI))))
            if not valid_status(status):
                errors.append((i, "trạng thái `%s` sai, cần: đang áp dụng, bỏ, đã vào skill vX.Y.Z" % status))
            continue
        if line.startswith("#") and i - 1 != first:
            errors.append((i, "tiêu đề lạ, chỉ dùng `## K-NNN · …` cho mục"))
            continue
        if cur is None:  # phần mở đầu, hoặc thân của đầu mục sai dạng (đã báo một lỗi)
            continue
        if not line.strip():
            continue
        f = FIELD.match(line)
        if not f or f.group(1) not in FIELDS:
            errors.append((i, "dòng lạ trong mục %s, chỉ dùng `- %s: …`" % (cur.id, "`/`- ".join(FIELDS))))
            continue
        key, val = f.group(1), f.group(2).strip()
        if key in cur.fields:
            errors.append((i, "trường `%s` lặp trong mục %s" % (key, cur.id)))
            continue
        cur.fields[key] = (val, i)
    ids = {}
    for e in entries:
        for key in REQUIRED:
            if not e.fields.get(key, ("", 0))[0]:
                errors.append((e.line, "mục %s thiếu trường `%s`" % (e.id, key)))
        if "Ngày" in e.fields and e.fields["Ngày"][0]:
            val, ln = e.fields["Ngày"]
            try:
                ok = re.match(r"^\d{4}-\d{2}-\d{2}$", val) and datetime.date.fromisoformat(val)
            except ValueError:
                ok = False
            if not ok:
                errors.append((ln, "Ngày `%s` sai, cần YYYY-MM-DD" % val))
        if e.id in ids:
            errors.append((e.line, "trùng mã %s (đã có ở dòng %d)" % (e.id, ids[e.id].line)))
        else:
            ids[e.id] = e
    for e in entries:
        if "Thay cho" not in e.fields:
            continue
        val, ln = e.fields["Thay cho"]
        target = ids.get(val)
        if val == e.id:
            errors.append((ln, "mục %s tự thay cho chính nó" % e.id))
        elif target is None:
            errors.append((ln, "Thay cho `%s` không có trong file" % val))
        elif target.active and e.status != DROPPED:
            errors.append((target.line, "mục %s bị %s thay nhưng vẫn đang áp dụng (đổi sang `bỏ`)" % (val, e.id)))
    seen = {}
    for e in entries:
        if not e.active or not e.rule:
            continue
        key = (e.skill, norm_rule(e.rule))
        if key in seen:
            errors.append((e.line, "trùng luật đang áp dụng với %s (cùng skill %s)" % (seen[key].id, e.skill)))
        else:
            seen[key] = e
    errors.sort()
    for ln, _ in errors:  # lỗi thuộc thân mục nào → mục đó không áp
        owner = None
        for hl, he in heads:
            if hl > ln:
                break
            owner = he
        if owner is not None:
            owner.bad = True
    return entries, errors, has_title


def start_dir(path):
    if not os.path.lexists(path) and not os.path.isdir(os.path.dirname(os.path.abspath(path))):
        die("không có %s" % path)
    p = os.path.abspath(path)
    return p if os.path.isdir(p) else os.path.dirname(p)


def home_real():
    return os.path.realpath(os.path.expanduser("~"))


def walk_up(d):
    """Thư mục được đọc từ d đi lên (gần trước) và gốc git (None nếu không gặp)."""
    home = home_real()
    dirs, cur = [], d
    while True:
        real = os.path.realpath(cur)
        if real == os.path.dirname(real) or real == home or home.startswith(real.rstrip(os.sep) + os.sep):
            return dirs, None  # gốc ổ đĩa, thư mục nhà hoặc cao hơn: dừng, không đọc
        dirs.append(cur)
        if os.path.lexists(os.path.join(cur, ".git")):
            return dirs, cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return dirs, None
        cur = parent


def find_files(paths):
    """Danh sách KAIZEN.md (gần trước) và cảnh báo, gộp từ mọi điểm đầu."""
    best, warns = {}, []
    for idx, p in enumerate(paths):
        dirs, _ = walk_up(start_dir(p))
        for dist, c in enumerate(dirs):
            try:
                names = os.listdir(c)
            except OSError:
                continue
            if NAME not in names:
                continue
            f = os.path.join(c, NAME)
            if os.path.islink(f):
                w = "Cảnh báo: bỏ qua %s — là symlink" % f
                if w not in warns:
                    warns.append(w)
                continue
            if not os.path.isfile(f):
                continue
            key = os.path.realpath(f)
            if key not in best or (dist, idx) < best[key][:2]:
                best[key] = (dist, idx, f)
    return [f for _, _, f in sorted(best.values())], warns


def cmd_find(a):
    found, warns = find_files(a.paths)
    for w in warns:
        say(w)
    for f in found:
        say("KAIZEN: " + f)
    if not found:
        say("Không có KAIZEN.md")
    return 0


def fmt(e):
    return "%s:%d %s · %s · %s — %s" % (e.path, e.line, e.id, e.skill, e.loai, e.rule)


def cmd_list(a):
    if a.skill and not SKILL.match(a.skill):
        die("skill `%s` sai, cần mk:<tên> hoặc *" % a.skill)
    found, warns = find_files(a.paths)
    for w in warns:
        say(w)
    applied, others, kept, dropped = [], [], {}, {}
    for f in found:
        entries, errors, _ = parse(f)
        if errors:
            say("Cảnh báo: %s có %d lỗi định dạng — chạy `check`" % (f, len(errors)))
        mine = [e for e in sorted(entries, key=lambda x: x.line) if not a.skill or e.skill in (a.skill, "*")]
        for e in mine:
            if e.bad:
                say("KHÔNG ÁP (lỗi định dạng): " + fmt(e))
                continue
            if not e.active:
                others.append(e)
                continue
            key = (e.skill, norm_rule(e.rule))
            if key in dropped:
                d = dropped[key]
                say("Bỏ qua: %s:%d %s (đã bỏ ở %s:%d %s)" % (e.path, e.line, e.id, d.path, d.line, d.id))
                continue
            if key in kept:
                k = kept[key]
                say("Bỏ qua: %s:%d %s trùng %s:%d %s" % (e.path, e.line, e.id, k.path, k.line, k.id))
                continue
            kept[key] = e
            applied.append(e)
        for e in mine:  # luật đã bỏ ở file này chặn luật cùng chữ ở file xa hơn
            if not e.bad and e.status == DROPPED and e.rule:
                dropped.setdefault((e.skill, norm_rule(e.rule)), e)
    for e in applied:
        say("ÁP: " + fmt(e))
    if a.all:
        for e in others:
            say("KHÁC: %s · %s" % (fmt(e), e.status))
    say("Tổng: %d luật đang áp dụng%s (file gần hơn đứng trước, thắng khi mâu thuẫn)"
        % (len(applied), " cho " + a.skill if a.skill else ""))
    return 0


def no_symlink(path):
    parent = os.path.dirname(os.path.abspath(path))
    if os.path.islink(path) or os.path.islink(parent):
        die("%s là symlink (hoặc nằm trong thư mục symlink) — không đọc/ghi xuyên symlink" % path)


def cmd_check(a):
    no_symlink(a.file)
    if not os.path.isfile(a.file):
        die("không có file %s" % a.file)
    entries, errors, _ = parse(a.file)
    for ln, msg in errors:
        say("LỖI: %s:%d: %s" % (a.file, ln, msg))
    if not errors:
        say("OK: %s: %d mục (%d đang áp dụng)" % (a.file, len(entries), sum(e.active for e in entries)))
    say("Kết quả: %d lỗi" % len(errors))
    return 1 if errors else 0


def guard_target(path):
    if os.path.basename(path) != NAME:
        die("chỉ ghi vào file tên %s, không ghi %s" % (NAME, path))
    no_symlink(path)
    if os.path.lexists(path) and not os.path.isfile(path):
        die("%s không phải file thường" % path)
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        die("không có thư mục %s" % parent)


def atomic_write(path, text, create=False):
    parent = os.path.dirname(os.path.abspath(path))
    try:
        fd, tmp = tempfile.mkstemp(prefix=".kaizen-", suffix=".tmp", dir=parent)
    except OSError as exc:
        die("không ghi được vào %s (%s)" % (parent, exc.strerror or exc))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        if not create:
            shutil.copymode(path, tmp)
            os.replace(tmp, path)
            return
        try:
            os.link(tmp, path)  # tạo mới, không bao giờ ghi đè
        except FileExistsError:
            die("%s vừa được tạo bởi tiến trình khác — chạy lại" % path)
        except OSError:  # ổ không có hard link (exFAT, một số ổ mạng)
            if os.path.lexists(path):
                die("%s vừa được tạo bởi tiến trình khác — chạy lại" % path)
            os.replace(tmp, path)
            return
        os.unlink(tmp)
    except OSError as exc:
        die("không ghi được %s (%s)" % (path, exc.strerror or exc))
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


def read_raw(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def one_line(name, val):
    val = val.strip()
    if not val:
        die("`--%s` trống" % name)
    if len(val.splitlines()) != 1 or has_hidden(val):
        die("`--%s` phải là một dòng, không có ký tự điều khiển hay ngắt dòng ẩn" % name)
    return nfc(val)


def set_line_status(text, line_no, status):
    """Đổi trạng thái ở đúng dòng đầu mục (đếm dòng theo \\n như parse), giữ nguyên mọi byte khác."""
    lines = text.split("\n")
    body = lines[line_no - 1]
    end = "\r" if body.endswith("\r") else ""
    body = body[:-1] if end else body
    lines[line_no - 1] = body.rsplit(SEP, 1)[0] + SEP + status + end
    return "\n".join(lines)


def cmd_add(a):
    path = a.file
    guard_target(path)
    skill = one_line("skill", a.skill)
    if not SKILL.match(skill):
        die("skill `%s` sai, cần mk:<tên> hoặc *" % skill)
    loai = nfc(a.loai)
    if loai not in LOAI:
        die("loại `%s` sai, cần một trong: %s" % (a.loai, ", ".join(LOAI)))
    luat, nguon = one_line("luat", a.luat), one_line("nguon", a.nguon)
    ngay = a.ngay or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(ngay)
    except ValueError:
        die("`--ngay` sai, cần YYYY-MM-DD")
    create = not os.path.lexists(path)
    if create:
        if not a.tao:
            die("chưa có %s — thêm `--tao` để tạo file mới" % path)
        ten = one_line("ten", a.ten or os.path.basename(os.path.dirname(os.path.abspath(path))) or "dự án")
        text = "# KAIZEN — %s\n\n%s\n" % (ten, BLURB)
        entries = []
    else:
        text = read_raw(path)
        entries, errors, _ = parse(path)
        if errors:
            die("%s có %d lỗi định dạng — chạy `check` và sửa trước khi thêm" % (path, len(errors)))
    by_id = {e.id: e for e in entries}
    for e in entries:
        if e.active and e.skill == skill and norm_rule(e.rule) == norm_rule(luat) and e.id != a.thay_cho:
            die("luật này đã có, đang áp dụng: %s (dòng %d)" % (e.id, e.line))
    target = None
    if a.thay_cho:
        target = by_id.get(a.thay_cho)
        if target is None:
            die("Thay cho `%s` không có trong %s (Thay cho chỉ trỏ tới mục cùng file)" % (a.thay_cho, path))
        if target.skill != skill and "*" not in (target.skill, skill):
            die("%s là luật của %s, không thay bằng luật của %s: «%s»" % (target.id, target.skill, skill, target.rule))
    nums = [int(e.id[2:]) for e in entries if ID.match(e.id)]
    new_id = "K-%03d" % (max(nums) + 1 if nums else 1)
    nl = "\r\n" if "\r\n" in text else "\n"
    if target is not None and target.active:
        text = set_line_status(text, target.line, DROPPED)
    block = ["## %s · %s · %s · %s" % (new_id, skill, loai, ACTIVE), "- Luật: " + luat, "- Nguồn: " + nguon,
             "- Ngày: " + ngay]
    if target is not None:
        block.append("- Thay cho: " + target.id)
    if text and not text.endswith("\n"):
        text += nl
    text += nl + nl.join(block) + nl
    line_no = text.count("\n") - len(block) + 1
    atomic_write(path, text, create=create)
    if create:
        say("OK: đã tạo %s" % path)
    say("OK: đã thêm %s vào %s:%d" % (new_id, path, line_no))
    if target is not None:
        if target.active:
            say("OK: %s → bỏ (thay bằng %s) — luật cũ: «%s»" % (target.id, new_id, target.rule))
        else:
            say("Cảnh báo: %s đã ở trạng thái `%s`, không đổi — luật cũ: «%s»" % (target.id, target.status, target.rule))
    return 0


def cmd_set_status(a):
    path = a.file
    guard_target(path)
    if not os.path.isfile(path):
        die("không có file %s" % path)
    status = nfc(a.trang_thai.strip())
    if status != DROPPED and not SHIPPED.match(status):
        die("trạng thái `%s` không dùng được ở đây, cần `bỏ` hoặc `đã vào skill vX.Y.Z`" % a.trang_thai)
    entries, _, _ = parse(path)
    matches = [e for e in entries if e.id == a.id]
    if not matches:
        die("không có mục %s trong %s" % (a.id, path))
    if len(matches) > 1:
        die("mã %s lặp trong %s — chạy `check`, sửa trước" % (a.id, path))
    e = matches[0]
    if e.status == status:
        say("OK: %s đã là `%s`, không đổi" % (e.id, status))
        return 0
    atomic_write(path, set_line_status(read_raw(path), e.line, status))
    say("OK: %s:%d %s `%s` → `%s` — «%s»" % (path, e.line, e.id, e.status, status, e.rule))
    return 0


def collect(paths):
    """(file, dự án) — dự án = gốc git của file; không có git → đường dẫn được đưa vào lệnh."""
    files, seen = [], set()
    for p in paths:
        if os.path.isfile(p) and not os.path.islink(p):
            cands = [os.path.abspath(p)]
            fallback = os.path.dirname(os.path.abspath(p))
        elif os.path.isdir(p):
            cands, fallback = [], os.path.abspath(p)
            for root, dirs, names in os.walk(os.path.abspath(p)):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not os.path.islink(os.path.join(root, d)))
                f = os.path.join(root, NAME)
                if NAME in names and os.path.isfile(f) and not os.path.islink(f):
                    cands.append(f)
        else:
            die("không có %s (hoặc là symlink)" % p)
        for f in cands:
            r = os.path.realpath(f)
            if r in seen:
                continue
            seen.add(r)
            git = walk_up(os.path.dirname(f))[1]
            files.append((f, os.path.realpath(git or fallback)))
    return sorted(files)


def cmd_promote(a):
    files = collect(a.paths)
    groups = {}
    for f, project in files:
        entries, errors, _ = parse(f)
        if errors:
            say("Cảnh báo: %s có %d lỗi định dạng — chạy `check`" % (f, len(errors)))
        for e in entries:
            if e.active and not e.bad and e.rule:
                groups.setdefault((e.skill, norm_rule(e.rule)), []).append((e, project))
    found = 0
    for key in sorted(groups):
        items = sorted(groups[key], key=lambda x: (x[0].path, x[0].line))
        nproj = len({p for _, p in items})
        nloi = sum(e.loai == "lỗi" for e, _ in items)
        why = []
        if nproj >= 2:
            why.append("%d dự án" % nproj)
        if nloi >= 3:
            why.append("lỗi ×%d" % nloi)
        if not why:
            continue
        found += 1
        say("ỨNG VIÊN: %s — %s (%s)" % (key[0], items[0][0].rule, ", ".join(why)))
        for e, _ in items:
            say("  - %s:%d %s · %s" % (e.path, e.line, e.id, e.loai))
    say("Đã đọc %d file KAIZEN.md, %d dự án (so khớp đúng chữ luật)" % (len(files), len({p for _, p in files})))
    say("Tổng: %d ứng viên" % found if found else "Không có ứng viên")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="kaizen.py", description="KAIZEN.md — luật riêng của dự án cho skill mk.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("find")
    s.add_argument("paths", nargs="+")
    s = sub.add_parser("list")
    s.add_argument("paths", nargs="+")
    s.add_argument("--skill")
    s.add_argument("--all", action="store_true")
    s = sub.add_parser("check")
    s.add_argument("file")
    s = sub.add_parser("add")
    s.add_argument("file")
    s.add_argument("--skill", required=True)
    s.add_argument("--loai", required=True)
    s.add_argument("--luat", required=True)
    s.add_argument("--nguon", required=True)
    s.add_argument("--thay-cho", dest="thay_cho")
    s.add_argument("--ngay")
    s.add_argument("--tao", action="store_true")
    s.add_argument("--ten")
    s = sub.add_parser("promote")
    s.add_argument("paths", nargs="+")
    s = sub.add_parser("set-status")
    s.add_argument("file")
    s.add_argument("id")
    s.add_argument("--trang-thai", dest="trang_thai", required=True)
    a = p.parse_args(argv)
    return {"find": cmd_find, "list": cmd_list, "check": cmd_check, "add": cmd_add, "promote": cmd_promote,
            "set-status": cmd_set_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
