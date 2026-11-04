#!/usr/bin/env python3
"""Ảnh thumbnail YouTube theo khuôn cho cả chuỗi video bài giảng: nhãn góc + tiêu đề tách từ tên file video (không
giải mã video), ghép với ảnh của người dùng — nền (ảnh AI họ tự tạo theo file prompt, hoặc nền vẽ sẵn), chân dung
(PNG tách nền giữ nguyên; ảnh thường cắt khung tròn có viền), logo — rồi in tiêu đề bằng ffmpeg có libass.
Chỉ thư viện chuẩn + ffmpeg; chạy offline (không gọi dịch vụ tạo ảnh nào); đầu ra tất định; không ghi đè file có sẵn.

  thumbnail.py names VIDEO|THƯ_MỤC [...] [--badge "{word} {n} · P{p}"]
  thumbnail.py prompt (VIDEO|THƯ_MỤC [...] | --tsv DIR/thumbnail.tsv) --assets DIR [--theme "…"] [--count 4] [--doc]
  thumbnail.py plan VIDEO|THƯ_MỤC [...] --out-dir DIR [--assets DIR] [--badge "…"] [--update]
  thumbnail.py check DIR/thumbnail.tsv [--doc] [--font Arial] [--ffmpeg PATH]
  thumbnail.py render DIR/thumbnail.tsv [--out-dir DIR] [--doc] [--font Arial] [--skip-existing] [--ffmpeg PATH]

Thư mục ảnh (--assets): nen/ (ảnh nền 16:9), nen-doc/ (tuỳ chọn, 9:16), chan-dung.png|jpg, logo.png|jpg.
TSV (tab): video, badge, title, nen, nen_doc, chan_dung, logo. Trong title: "|" = xuống dòng, *chữ* = chữ vàng.
ffmpeg có libass (check, render): --ffmpeg, rồi biến MK_THUMBNAIL_FFMPEG, ffmpeg trong PATH (không lấy bản nằm ở
thư mục đang làm việc), bản ffmpeg-full của Homebrew. Thoát: 0 xong (có thể kèm "Cảnh báo:"); 1 lỗi đầu vào/ffmpeg
hoặc có dòng "LỖI:" (không ghi ảnh); 2 sai cách gọi.
"""
import argparse
import itertools
import math
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import unicodedata

sys.dont_write_bytecode = True

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi")
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
HEADER = ["video", "badge", "title", "nen", "nen_doc", "chan_dung", "logo"]
IMAGE_COLS = {"nen": "nền", "nen_doc": "nền dọc", "chan_dung": "chân dung", "logo": "logo"}
TSV_NAME = "thumbnail.tsv"
ASSETS_LINE = re.compile(r"^#\s*assets:\s*(\S.*?)\s*$")
PROMPT_NAME = "prompt-nen.md"
PROMPT_DOC_NAME = "prompt-nen-doc.md"
TSV_NOTE = (
    "# mk:thumbnail — sửa cột rồi chạy: thumbnail.py check <file này>, rồi render <file này>\n"
    "# title: \"|\" = xuống dòng (tối đa 3 dòng), *chữ* = chữ vàng. badge trống = không có nhãn góc.\n"
    "# nen, nen_doc, chan_dung, logo: đường dẫn ảnh trong máy; trống = nền vẽ sẵn / nền ngang / không có.\n")
FFMPEG_FULL = ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "/usr/local/opt/ffmpeg-full/bin/ffmpeg")
INSTALL_HINT = ("cần ffmpeg có libass để in chữ lên ảnh — macOS: brew install ffmpeg-full (cài song song, không thay "
                "ffmpeg đang dùng); Windows: winget install Gyan.FFmpeg (bản full); Linux: sudo apt install ffmpeg; "
                "rồi chạy lại, hoặc chỉ đường dẫn bằng --ffmpeg")
NAME_RE = re.compile(r"^([^\W\d_]+) ?(\d+)\s*[_·\-–]\s*([Pp]\d+(?:\.\d+)*)(?:\s*[-–:]\s*|\s+)(\S.*)$")
YELLOW_ASS, YELLOW_BOX, GOLD = "&H0000D4FF", "0xFFD400", "0xE8C766"
JPG_LIMIT = 2 * 1024 * 1024   # giới hạn ảnh thumbnail của YouTube
TITLE_MAX = 200               # ký tự; dài hơn thì không thể vừa 3 dòng, dò cách ngắt cũng chậm

# Khuôn cho cả chuỗi. Chân dung ở bên phải, tiêu đề bên trái, căn giữa theo chiều dọc trong vùng chữ. Ảnh ngang: chân dung tách nền đứng chạm đáy trong khung
# x 790–1256 (mặt ở phần trên, ô thời lượng YouTube ở góc dưới-phải chỉ che phần thân); khung tròn đặt cao, đáy
# y≈560, chừa hẳn góc dưới-phải. Ảnh dọc (Shorts): tiêu đề trên, chân dung dưới; lề phải 151 px chừa nút của app.
# shade: độ tối (0–255) của lớp phủ sau tiêu đề, theo có/không chân dung; deco: tâm, bán kính vòng bát quái của nền
# vẽ sẵn (không chân dung → dời sang phải, ra khỏi vùng chữ).
LAYOUTS = {
    "ngang": {
        "w": 1280, "h": 720, "suffix": "", "badge": (54, 40, 34), "logo": (40, 34, 72),
        "title": {"ml": 64, "an": 4, "size": (100, 40), "y": {True: 389, False: 389}, "top": 110,
                  "xr": {True: 768, False: 1216}, "bottom": {True: 664, False: 664}},
        "cutout": (790, 40, 1256, 720), "circle": (1030, 330, 446, 8),
        "deco": {True: (1000, 360, 250), False: (1130, 360, 240)},
        "shade": {True: "200*clip(1.25-X/(0.66*W),0,1)", False: "70+80*clip(1-X/W,0,1)"},
    },
    "doc": {
        "w": 1080, "h": 1920, "suffix": " - doc", "badge": (64, 236, 42), "logo": (64, 230, 80),
        "title": {"ml": 64, "an": 4, "size": (120, 44), "y": {True: 665, False: 760}, "top": 340,
                  "xr": {True: 929, False: 929}, "bottom": {True: 990, False: 1180}},
        "cutout": (54, 1040, 1026, 1920), "circle": (540, 1310, 560, 10),
        "deco": {True: (540, 1310, 330), False: (540, 1500, 300)},
        "shade": {True: "150*clip((1150-Y)/300,0,1)", False: "130*clip((1350-Y)/300,0,1)"},
    },
}
PLATE = 185   # độ tối tấm mềm ôm sát vùng chữ (0–255), toả ra 70 px — giữ chữ đọc được trên nền rối
# Bát quái (tiên thiên) cho nền vẽ sẵn: 3 vạch từ trên xuống, 1 = vạch liền (dương), 0 = vạch đứt (âm);
# đi theo chiều kim đồng hồ từ đỉnh, quẻ đối diện là quẻ nghịch.
TRIGRAMS = ("111", "011", "010", "001", "000", "100", "101", "110")
PROMPT_MOODS = ("deep indigo night with faint gold light", "warm ink-wash on aged parchment, dark sepia tones",
                "jade green and black lacquer, soft mist", "midnight blue with drifting smoke and dim lantern glow",
                "charcoal stone texture with subtle bronze highlights", "dark teal gradient with soft paper grain")

# Độ rộng ký tự Arial đậm (phần nghìn em) để ước lượng ngắt dòng; kết quả thật đo lại bằng libass.
_W = {" ": 278, "!": 333, "\"": 474, "&": 722, "'": 238, "(": 333, ")": 333, ",": 278, "-": 333, ".": 278, "/": 278,
      ":": 333, ";": 333, "?": 611, "–": 556, "—": 1000, "·": 278, "I": 278, "J": 556, "M": 833, "W": 944, "f": 333,
      "i": 278, "j": 278, "l": 278, "m": 889, "r": 389, "t": 333, "w": 778, "z": 500, "đ": 611, "Đ": 722}
_W.update({c: 722 for c in "ABCDHKNRU"})
_W.update({c: 667 for c in "EPSVXY"})
_W.update({c: 611 for c in "FLTZbdghnopqu"})
_W.update({c: 778 for c in "GOQ"})
_W.update({c: 556 for c in "0123456789acekmsvxy"})
_W.update({"m": 889, "k": 556})


def die(msg, code=1):
    print("Lỗi: " + msg, file=sys.stderr)
    sys.exit(code)


def utf8_stdio():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")


def run(cmd, cwd=None, binary=False):
    try:
        if binary:
            return subprocess.run(cmd, cwd=cwd, capture_output=True)
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        die("không chạy được %s: %s" % (cmd[0], e))


def nfc(text):
    return unicodedata.normalize("NFC", text)


def natural(name):
    return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.split(r"(\d+)", nfc(name).casefold())]


def has_control(text):
    return any(unicodedata.category(c) == "Cc" for c in text)


def shown(text):
    """Chuỗi để in: ký tự điều khiển (xuống dòng, ESC…) thành \\xNN — tên file không giả được dòng OK:/LỖI:."""
    return "".join("\\x%02x" % ord(c) if unicodedata.category(c) == "Cc" else c for c in text)


# ---------- tên file → nhãn + tiêu đề ----------

def expand(src):
    if os.path.isfile(src):
        if not src.lower().endswith(VIDEO_EXT):
            die("%s không phải file video (%s)" % (shown(src), ", ".join(VIDEO_EXT)))
        found = [os.path.abspath(src)]
    elif os.path.isdir(src):
        found = [os.path.abspath(os.path.join(src, f)) for f in os.listdir(src) if not f.startswith(".")
                 and f.lower().endswith(VIDEO_EXT) and os.path.isfile(os.path.join(src, f))]
        if not found:
            die("thư mục %s không có video (%s)" % (shown(src), ", ".join(VIDEO_EXT)))
    else:
        die("không thấy %s" % shown(src))
    for v in found:
        if has_control(os.path.basename(v)):
            die("tên file %s có ký tự điều khiển (xuống dòng, tab, ESC…) — đổi tên file trước" % shown(v))
    return found


def list_videos(srcs):
    """Các file/thư mục (không đệ quy) → danh sách video không trùng, xếp theo tên tự nhiên (Buổi 2 trước Buổi 10)."""
    found = {v for s in srcs for v in expand(s)}
    return sorted(found, key=lambda v: (natural(os.path.basename(v)), v))


def stem(path):
    return nfc(os.path.splitext(os.path.basename(path))[0])


FORBIDDEN = re.compile(r'[\\/*?"<>|]')


def out_name(path):
    """Tên ảnh ra từ tên video, dùng được trên Windows/exFAT: ':' → ' - ', các ký tự \\ / * ? " < > | → '-'."""
    name = FORBIDDEN.sub("-", stem(path).replace(":", " - "))
    return re.sub(r"\s+", " ", name).strip(" .") or "thumbnail"


DEFAULT_BADGE = "{word} {n} · P{p}"


def badge_template(tpl):
    """Kiểm mẫu nhãn góc (--badge): chỉ trường {word} (chữ trước số buổi, vd Buổi), {n} (số buổi), {p} (số phần,
    vd 03, 05.6). Sai → dừng, thoát 2."""
    try:
        fields = {f for _, f, spec, conv in string.Formatter().parse(tpl) if f is not None}
        sample = tpl.format(word="Buổi", n="1", p="01")
    except (ValueError, IndexError, KeyError) as e:
        die("--badge sai cú pháp (%s): %s" % (e, shown(tpl)), 2)
    if not fields <= {"word", "n", "p"} or has_control(tpl) or any(c in tpl for c in "|*") or len(sample) > 40:
        die("--badge chỉ dùng {word} {n} {p}, không có | * hay ký tự điều khiển, dài tối đa 40 ký tự; nhận: %s"
            % shown(tpl), 2)
    return tpl


def parse_name(path, badge_fmt=DEFAULT_BADGE):
    """→ (badge, title, các câu cảnh báo). '*' và '|' trong tên là chữ thường, không phải ký hiệu của TSV:
    đổi '*' → '·', '|' → '/' để TSV do plan ghi luôn qua check."""
    s = " ".join(stem(path).split())
    warns = []
    if "*" in s or "|" in s:
        s = s.replace("*", "·").replace("|", "/")
        warns.append("tên có * hoặc | — trong title đã đổi thành · và / (hai dấu này là ký hiệu của thumbnail.tsv)")
    m = NAME_RE.match(s)
    if not m:
        warns.append("tên không theo mẫu \"Buổi N_Pxx - Tiêu đề\" — badge trống, title = cả tên; hỏi người dùng "
                     "tiêu đề thật")
        return "", s, warns
    word, num, part, title = m.groups()
    return badge_fmt.format(word=word, n=num, p=part[1:]), title.strip(), warns


def cmd_names(args):
    warns, fmt = [], badge_template(args.badge)
    for n, v in enumerate(list_videos(args.src), 1):
        badge, title, w = parse_name(v, fmt)
        name = nfc(os.path.basename(v))
        print("%d\t%s\t%s\t%s" % (n, badge, title, name))
        warns += ["Cảnh báo: %s: %s" % (name, x) for x in w]
    for w in warns:
        print(w)


# ---------- ghi file an toàn ----------

def refuse_overwrite(*paths):
    for p in paths:
        if os.path.lexists(p):
            die("%s đã có — chọn thư mục khác (skill không ghi đè)" % shown(p))


def make_dir(path):
    if os.path.islink(path):
        die("%s là symlink — chọn thư mục thật (skill không ghi xuyên symlink)" % shown(path))
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        die("không tạo được thư mục %s: %s" % (shown(path), e))


def temp_in(folder, suffix):
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".mk-thumbnail-", suffix=suffix)
    os.close(fd)
    mask = os.umask(0)
    os.umask(mask)
    os.chmod(tmp, 0o666 & ~mask)   # mkstemp tạo quyền 600; file giao cho người dùng theo umask như file thường
    return tmp


def deliver(tmp, dest):
    """Đưa file tạm thành file đích mà không bao giờ ghi đè (os.link báo lỗi khi đích đã có)."""
    try:
        os.link(tmp, dest)
    except FileExistsError:
        os.remove(tmp)
        die("%s đã có — chọn thư mục khác (skill không ghi đè)" % shown(dest))
    except OSError:
        if os.path.lexists(dest):
            os.remove(tmp)
            die("%s đã có — chọn thư mục khác (skill không ghi đè)" % shown(dest))
        os.replace(tmp, dest)
        return
    os.remove(tmp)


def write_text(dest, text):
    tmp = temp_in(os.path.dirname(dest) or ".", ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError as e:
        os.remove(tmp)
        die("không ghi được %s: %s" % (shown(dest), e))
    deliver(tmp, dest)


# ---------- thư mục ảnh, prompt, plan ----------

def asset_images(folder):
    if not os.path.isdir(folder):
        return []
    names = [f for f in os.listdir(folder) if not f.startswith(".") and f.lower().endswith(IMG_EXT)
             and os.path.isfile(os.path.join(folder, f))]
    for f in names:
        if has_control(f):
            die("tên ảnh %s có ký tự điều khiển — đổi tên file trước" % shown(os.path.join(folder, f)))
    return [os.path.join(folder, f) for f in sorted(names, key=lambda f: (natural(f), f))]


def asset_file(assets, base):
    """→ (ảnh được dùng, mọi ảnh <base>.* tìm thấy). Ưu tiên theo đuôi: .png, .jpg, .jpeg, .webp."""
    found = [os.path.join(assets, base + ext) for ext in IMG_EXT if os.path.isfile(os.path.join(assets, base + ext))]
    return (found[0] if found else ""), found


PROMPT_RULES = ("No people, no faces, no hands, no text, no letters or characters of any script, no numbers, no "
                "logos, no watermark, no frame or border; any symbols only as abstract linework (thin lines, circles, "
                "solid and broken bars), never as writing. Soft cinematic lighting, gentle depth of field, clean and "
                "uncluttered, rich but dark tones so white bold text stays readable.")
PROMPT_LAYOUT = {
    ("ngang", True): "the left 60% of the image is calm, dark and almost empty (smooth gradient or soft texture) to "
                     "hold a large title added later; subtle elements only in the right third, soft and slightly out "
                     "of focus, leaving room for a person to be composited on the right.",
    ("ngang", False): "the left two thirds are calm, dark and almost empty (smooth gradient or soft texture) to hold a "
                      "large title added later; subtle elements only near the right edge, soft and slightly out of "
                      "focus.",
    ("doc", True): "the upper half is calm, dark and almost empty to hold a large title added later; subtle elements "
                   "only in the lower half, soft and slightly out of focus, leaving room for a person to be "
                   "composited at the bottom.",
    ("doc", False): "the upper two thirds are calm, dark and almost empty to hold a large title added later; subtle "
                    "elements only near the bottom, soft and slightly out of focus.",
}
NEGATIVE = ("text, letters, words, captions, calligraphy, numbers, watermark, signature, logo, people, face, portrait, "
            "hands, busy background, clutter, bright white areas, high-frequency detail behind the title area, frame, "
            "border, low resolution, jpeg artifacts")


def prompt_text(kind, theme, titles, portrait, count, assets):
    folder, ratio, size = ("nen/", "16:9", "1920×1080") if kind == "ngang" else ("nen-doc/", "9:16", "1080×1920")
    out = ["# Prompt ảnh nền %s — mk:thumbnail" % ratio, "",
           "Chủ đề chuỗi: %s · %d video · %s chân dung." % (theme, len(titles), "có" if portrait else "không"), "",
           "Cách dùng: dán từng prompt vào công cụ tạo ảnh bạn chọn (prompt viết tiếng Anh cho mọi công cụ). Lưu ảnh "
           "vào `%s`, tên tuỳ ý, đuôi .jpg/.png/.webp. Rồi chạy `plan … --assets %s` (đã có TSV: thêm `--update`): "
           "các ảnh được xoay vòng cho từng video. Ảnh có chữ, có người hay quá rối → bỏ, tạo lại." % (folder, assets),
           ""]
    lead = "Wide 16:9" if kind == "ngang" else "Tall 9:16"
    for k in range(count):
        out += ["## Nền %d — %s (%s)" % (k + 1, ratio, size), "",
                "%s background art for a YouTube lecture thumbnail. Theme: %s. Mood: %s. Composition: %s %s"
                % (lead, theme, PROMPT_MOODS[k], PROMPT_LAYOUT[(kind, portrait)], PROMPT_RULES), ""]
    out += ["## Negative prompt (ô \"negative\" nếu công cụ có)", "", NEGATIVE, "",
            "## Tiêu đề trong chuỗi (để chọn chủ đề — không đưa chữ vào ảnh)", ""]
    out += ["- %s" % t for t in titles]
    return "\n".join(out) + "\n"


def cmd_prompt(args):
    if not 1 <= args.count <= len(PROMPT_MOODS):
        die("--count phải từ 1 đến %d" % len(PROMPT_MOODS), 2)
    if has_control(args.theme):
        die("--theme có ký tự điều khiển", 2)
    if bool(args.src) == bool(args.tsv):
        die("cần đúng một nguồn tiêu đề: video/thư mục, hoặc --tsv <thumbnail.tsv> (tiêu đề đã sửa)", 2)
    assets = os.path.abspath(args.assets)
    if args.tsv:
        rows, errors = read_tsv(args.tsv)
        if errors:
            report_errors(args.tsv, errors)
            sys.exit(1)
        titles = [" ".join(plain(ln) for ln in r["hard"]) for r in rows]
        portrait = any(r["chan_dung"] for r in rows)
    else:
        titles = [parse_name(v)[1] for v in list_videos(args.src)]
        portrait = bool(asset_file(assets, "chan-dung")[0])
    wide, tall = os.path.join(assets, PROMPT_NAME), os.path.join(assets, PROMPT_DOC_NAME)
    todo = [("ngang", wide)] if not os.path.lexists(wide) else []
    if args.doc and not os.path.lexists(tall):
        todo.append(("doc", tall))
    if not todo:
        refuse_overwrite(wide, *([tall] if args.doc else []))
    make_dir(assets)
    theme = " ".join(args.theme.split())
    for kind, dest in todo:
        make_dir(os.path.join(assets, "nen" if kind == "ngang" else "nen-doc"))
        write_text(dest, prompt_text(kind, theme, titles, portrait, args.count, assets))
        print("OK: %s · %d prompt %s · %s chân dung" % (dest, args.count, "16:9" if kind == "ngang" else "9:16",
                                                      "chừa chỗ" if portrait else "không chừa chỗ"))
    if args.doc and ("ngang", wide) not in todo and os.path.lexists(wide):
        print("Giữ nguyên: %s (đã có)" % wide)


def tsv_versions(out):
    """thumbnail.tsv, thumbnail-2.tsv, … đang có trong thư mục xuất → (bản mới nhất hoặc None, tên bản kế tiếp)."""
    latest, n = None, 1
    if os.path.lexists(os.path.join(out, TSV_NAME)):
        latest = os.path.join(out, TSV_NAME)
        n = 2
        while os.path.lexists(os.path.join(out, "thumbnail-%d.tsv" % n)):
            latest = os.path.join(out, "thumbnail-%d.tsv" % n)
            n += 1
    return latest, os.path.join(out, TSV_NAME if latest is None else "thumbnail-%d.tsv" % n)


def old_rows(path):
    """TSV cũ (đọc dễ dãi, không kiểm) → ({video tuyệt đối: {cột: giá trị}}, dòng # assets: hoặc None)."""
    try:
        with open(path, encoding="utf-8-sig") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        die("không đọc được %s: %s" % (shown(path), e))
    base, head, found, assets = os.path.dirname(path), None, {}, None
    for line in lines:
        line = line.rstrip("\r")
        m = ASSETS_LINE.match(line)
        if m and head is None:
            assets = m.group(1)
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = line.split("\t")
        if head is None:
            head = cells
            if "video" not in head:
                die("%s không có dòng tên cột — không cập nhật được; chạy plan vào thư mục khác" % shown(path))
            continue
        cell = dict(zip(head, cells))
        video = cell.get("video", "").strip()
        if video and not any(has_control(c) for c in cells):
            found[os.path.abspath(os.path.join(base, video))] = cell
    return found, assets


def cmd_plan(args):
    fmt = badge_template(args.badge)
    videos = list_videos(args.src)
    nen, nen_doc, portrait, logo, assets = [], [], "", "", None
    if args.assets:
        assets = os.path.abspath(args.assets)
        if has_control(assets):
            die("--assets có ký tự điều khiển", 2)
        if not os.path.isdir(assets):
            print("Cảnh báo: chưa có thư mục ảnh %s — dùng nền vẽ sẵn, không chân dung, không logo; bỏ ảnh vào đó rồi "
                  "chạy lại plan … --update" % shown(assets))
        else:
            nen = asset_images(os.path.join(assets, "nen"))
            nen_doc = asset_images(os.path.join(assets, "nen-doc"))
            portrait, found = asset_file(assets, "chan-dung")
            if len(found) > 1:
                print("Cảnh báo: có %d ảnh chan-dung.* — dùng %s (ưu tiên .png, .jpg, .jpeg, .webp); muốn ảnh khác thì "
                      "đổi cột chan_dung" % (len(found), os.path.basename(portrait)))
            logo, found = asset_file(assets, "logo")
            if len(found) > 1:
                print("Cảnh báo: có %d ảnh logo.* — dùng %s" % (len(found), os.path.basename(logo)))
            if not nen:
                print("Cảnh báo: %s chưa có ảnh — dùng nền vẽ sẵn; muốn nền riêng: chạy prompt rồi lưu ảnh vào đó"
                      % shown(os.path.join(assets, "nen") + os.sep))
    out = os.path.abspath(args.out_dir)
    latest, tsv = tsv_versions(out)
    old, old_assets = {}, None
    if latest and not args.update:
        refuse_overwrite(latest)
    if latest:
        old, old_assets = old_rows(latest)
    header = "# assets: %s\n" % assets if assets else ("# assets: %s\n" % old_assets if old_assets else "")
    lines, kept = [TSV_NOTE + header + "\t".join(HEADER)], 0
    for i, v in enumerate(videos):
        name = nfc(os.path.basename(v))
        badge, title, warns = parse_name(v, fmt)
        for w in warns:
            print("Cảnh báo: %s: %s" % (name, w))
        cols = {"nen": nen[i % len(nen)] if nen else "", "nen_doc": nen_doc[i % len(nen_doc)] if nen_doc else "",
                "chan_dung": portrait, "logo": logo}
        prev = old.pop(v, None)
        if prev:   # giữ sửa tay của người dùng; cột ảnh trống thì điền ảnh mới
            kept += 1
            badge, title = prev.get("badge", badge), prev.get("title", title)
            cols = {c: prev.get(c) or cols[c] for c in cols}
        lines.append("\t".join([v, badge, title, cols["nen"], cols["nen_doc"], cols["chan_dung"], cols["logo"]]))
        print("OK: %s · nền %s · chân dung %s · logo %s" % (name, os.path.basename(cols["nen"]) or "vẽ sẵn",
                                                          os.path.basename(cols["chan_dung"]) or "không",
                                                          os.path.basename(cols["logo"]) or "không"))
    for v in sorted(old):
        print("Cảnh báo: %s có trong %s nhưng không có trong nguồn — bỏ khỏi bản mới" % (
            shown(nfc(os.path.basename(v))), os.path.basename(latest)))
    make_dir(out)
    write_text(tsv, "\n".join(lines) + "\n")
    if latest:
        print("Cập nhật: giữ title/badge/ảnh đã chọn của %d video từ %s (bản cũ giữ nguyên)" % (kept, latest))
    print("TSV: %s" % tsv)


# ---------- đọc, kiểm TSV ----------

def parse_title(title):
    """'Quán *Quen*|Phở' → các dòng cứng, mỗi dòng là danh sách từ, mỗi từ là danh sách (ký tự, vàng?)."""
    lines, words, word, accent = [], [], [], False
    for ch in title + "|":
        if ch == "*":
            accent = not accent
        elif ch == "|" or ch.isspace():
            if word:
                words.append(word)
                word = []
            if ch == "|":
                lines.append(words)
                words = []
        else:
            word.append((ch, accent))
    return lines


def inside(path, root):
    real, top = os.path.realpath(path), os.path.realpath(root)
    return real == top or real.startswith(top.rstrip(os.sep) + os.sep)


def remote(raw):
    """Lý do một ô/dòng đường dẫn không phải file trong máy, hoặc None."""
    if raw.startswith(("\\\\", "//")):
        return "là đường dẫn mạng (UNC \\\\máy\\thư mục, //máy/…) — chỉ nhận file trong máy (skill chạy offline)"
    drive = os.name == "nt" and re.match(r"^[a-zA-Z]:[\\/]", raw)
    if "://" in raw or (not drive and re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw)):
        return "phải là đường dẫn file trong máy, không phải địa chỉ mạng/URL (skill chạy offline)"
    return None


def local_file(raw, base, exts, col, roots=None):
    """Ô đường dẫn trong TSV → (đường dẫn tuyệt đối, lỗi). Chỉ file trong máy: URL và UNC bị bác; đường dẫn tương đối
    tính từ thư mục chứa TSV; luôn tuyệt đối nên ffmpeg không hiểu nhầm thành giao thức (concat:, subfile,…). Ảnh
    (roots) phải nằm trong thư mục chứa TSV hoặc thư mục ảnh ghi ở dòng '# assets:' (theo symlink tới đích thật)."""
    why = remote(raw)
    if why:
        return None, "cột %s %s" % (col, why)
    path = os.path.abspath(os.path.join(base, raw))
    if not path.lower().endswith(exts):
        return None, "cột %s phải là file %s (%s)" % (col, "video" if exts == VIDEO_EXT else "ảnh", ", ".join(exts))
    if not os.path.isfile(path):
        what = "video" if col == "video" else "ảnh " + IMAGE_COLS[col]
        return None, "không thấy %s %s" % (what, path)
    if roots and not any(inside(path, r) for r in roots):
        return None, ("ảnh %s phải nằm trong thư mục chứa TSV hoặc thư mục ảnh (dòng `# assets:` của TSV): %s — chép ảnh "
                      "vào thư mục ảnh" % (IMAGE_COLS[col], path))
    return path, None


def read_tsv(path):
    if not os.path.isfile(path):
        die("không thấy %s" % shown(path))
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as e:
        die("không đọc được %s (cần UTF-8): %s" % (shown(path), e))
    base = os.path.dirname(os.path.abspath(path))
    rows, errors, header_seen, outs, roots = [], [], False, {}, [base]
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\r")
        m = ASSETS_LINE.match(line)
        if m and not header_seen:
            why = remote(m.group(1)) or ("có ký tự điều khiển" if has_control(m.group(1)) else None)
            if why:
                errors.append((n, "dòng # assets: %s" % why))
            else:
                roots.append(os.path.abspath(os.path.join(base, m.group(1))))
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = line.split("\t")
        if not header_seen:
            header_seen = True
            if cells != HEADER:
                errors.append((n, "dòng tên cột phải là: %s (cách nhau bằng tab)" % " ".join(HEADER)))
                break
            continue
        if len(cells) != len(HEADER):
            errors.append((n, "cần %d cột cách nhau bằng tab, có %d" % (len(HEADER), len(cells))))
            continue
        if any(has_control(c) for c in cells):
            errors.append((n, "có ký tự điều khiển (ESC, xuống dòng lạ…) trong dòng — xoá đi"))
            continue
        cell = dict(zip(HEADER, (c.strip() for c in cells)))
        err, row = [], {"line": n, "badge": cell["badge"], "title": cell["title"]}
        row["video"], e = local_file(cell["video"], base, VIDEO_EXT, "video")
        err += [e] if e else []
        for col in IMAGE_COLS:
            row[col] = None
            if cell[col]:
                row[col], e = local_file(cell[col], base, IMG_EXT, col, roots)
                err += [e] if e else []
        title = cell["title"]
        if len(title) > TITLE_MAX:   # chặn trước khi dò cách ngắt dòng (dò trên title rất dài rất chậm)
            err.append("title quá dài (%d ký tự, tối đa %d) — rút ngắn" % (len(title), TITLE_MAX))
        else:
            if title.count("*") % 2:
                err.append("dấu * (chữ vàng) phải đi theo cặp")
            row["hard"] = parse_title(title)
            if not any(row["hard"]):
                err.append("title trống")
            elif len(row["hard"]) > 3 or not all(row["hard"]):
                err.append("title tối đa 3 dòng, không dòng trống (dấu | là xuống dòng)")
        if len(cell["badge"]) > 40 or any(c in cell["badge"] for c in "|*"):
            err.append("badge tối đa 40 ký tự, không có | hay *")
        key = out_name(cell["video"]).casefold()
        if key in outs:
            err.append("trùng tên ảnh với dòng %d" % outs[key])
        outs[key] = n
        errors += [(n, e) for e in err]
        if not err:
            rows.append(row)
    if not header_seen:
        errors.append((1, "file không có dòng tên cột: %s" % " ".join(HEADER)))
    elif not rows and not errors:
        errors.append((1, "không có dòng video nào"))
    return rows, errors


def report_errors(path, errors):
    for n, e in errors:
        print("LỖI: %s:%d: %s" % (shown(path), n, shown(e)))


# ---------- ffmpeg ----------

def has_filter(ff, name):
    res = run([ff, "-hide_banner", "-filters"])
    return any(ln.split()[1:2] == [name] for ln in res.stdout.splitlines())


def under_cwd(path):
    """Đường dẫn (sau khi theo symlink) nằm trong thư mục đang làm việc hoặc thư mục con của nó?"""
    real, cwd = os.path.realpath(path), os.path.realpath(os.getcwd())
    return real == cwd or real.startswith(cwd.rstrip(os.sep) + os.sep)


def refuse_in_cwd(path, source):
    if under_cwd(path):
        die("%s (%s) nằm trong thư mục đang làm việc (%s) — skill không chạy chương trình lấy từ thư mục làm việc, repo "
            "hay thư mục video; chỉ rõ ffmpeg bằng --ffmpeg <đường dẫn tuyệt đối> ngoài thư mục này"
            % (shown(path), source, shown(os.getcwd())))


def from_path(name):
    """Tìm chương trình trong PATH, nhưng không bao giờ lấy bản nằm trong thư mục đang làm việc hay thư mục con
    (Windows tìm ở thư mục hiện tại trước PATH; PATH có '.' cũng vậy)."""
    found = shutil.which(name)
    if found:
        refuse_in_cwd(found, name + " trong PATH")
    return found


def find_ffmpeg(explicit, required=True):
    """ffmpeg có libass: --ffmpeg, rồi MK_THUMBNAIL_FFMPEG, ffmpeg trong PATH, bản ffmpeg-full của Homebrew. --ffmpeg và
    biến môi trường phải là đường dẫn tuyệt đối; mọi nguồn đều bị từ chối khi nằm trong thư mục đang làm việc. Không
    có → dừng kèm lệnh cài (required) hoặc trả None."""
    env = os.environ.get("MK_THUMBNAIL_FFMPEG")
    for value, source in ((explicit, "--ffmpeg"), (env, "MK_THUMBNAIL_FFMPEG")):
        if value:
            if has_control(value) or not os.path.isabs(value):
                die("%s phải là đường dẫn tuyệt đối tới ffmpeg, đang là: %s" % (source, shown(value)), 2)
            refuse_in_cwd(value, source)
    if explicit:
        cands = [lambda: explicit]
    else:
        cands = [lambda: env, lambda: from_path("ffmpeg")] + [lambda c=c: c for c in FFMPEG_FULL]
    for get in cands:
        c = get()
        if c and os.path.isfile(c) and not under_cwd(c) and has_filter(c, "ass"):
            return c
    if required:
        die(INSTALL_HINT + (" (%s không có libass)" % shown(explicit) if explicit else ""))
    return None


def font_check(font):
    fc = shutil.which("fc-list")
    if not fc or under_cwd(fc):
        return None
    res = run([fc, ":family=%s:lang=vi" % font, "family"])
    if not res.stdout.strip():
        return ("không thấy font '%s' có đủ chữ tiếng Việt trên máy — libass sẽ dùng font khác; xem dòng 'Font dùng "
                "thật' và ảnh ra, hoặc chọn font khác bằng --font" % font)
    return None


def check_font(font):
    if any(c in font for c in ",;{}") or has_control(font):
        die("--font không được chứa dấu phẩy, chấm phẩy, ngoặc nhọn hay ký tự điều khiển", 2)


def font_used(line):
    parts = [p.strip() for p in line.split("->", 1)[1].split(",")]
    return "%s (%s)" % (parts[-1], parts[0]) if len(parts) >= 3 else parts[0]


def image_input(path):
    # image2 + pattern_type none: tên ảnh có % không bị hiểu thành dãy ảnh
    return ["-f", "image2", "-pattern_type", "none", "-i", path]


def image_info(ff, path, cache):
    """→ (rộng, cao, có vùng trong suốt?) hoặc None khi ffmpeg không đọc được ảnh."""
    if path not in cache:
        res = run([ff, "-hide_banner", "-nostdin"] + image_input(path) +
                  ["-frames:v", "1", "-vf", "format=rgba,alphaextract,signalstats,metadata=print", "-f", "null", "-"])
        size = re.search(r"Video: [^\n]*?\b(\d{2,5})x(\d{2,5})\b", res.stderr)
        amin = re.search(r"lavfi\.signalstats\.YMIN=(\d+)", res.stderr)
        ok = res.returncode == 0 and size and amin
        cache[path] = (int(size.group(1)), int(size.group(2)), int(amin.group(1)) < 128) if ok else None
    return cache[path]


# ---------- chữ: ASS, đo, ngắt dòng ----------

def esc(ch):
    return {"\\": "\\\u2060", "{": "\\{", "}": "\\}"}.get(ch, ch)


def ass_lines(lines):
    """Dòng → chữ ASS: chữ người dùng là dữ liệu (\\ chèn U+2060, { } thoát), chữ vàng bằng thẻ màu."""
    out = []
    for words in lines:
        text, accent = "", False
        for i, word in enumerate(words):
            for ch, acc in word:
                if acc != accent:
                    text += "{\\c%s&}" % (YELLOW_ASS if acc else "&H00FFFFFF")
                    accent = acc
                text += esc(ch)
            if i < len(words) - 1:
                text += " "
        if accent:
            text += "{\\c&H00FFFFFF&}"
        out.append(text)
    return "\\N".join(out)


def ass_doc(v, font, events):
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n" % (v["w"], v["h"]))
    # viền đen 4 px + bóng 2 px: chữ trắng và chữ vàng vẫn tách khỏi nền đỏ/cam; M (đo) vẽ viền, bóng màu trắng
    styles = ("Style: T,{f},40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,2,1,0,0,0,1\n"
              "Style: M,{f},40,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,1,4,2,1,0,0,0,1\n"
              "Style: B,{f},40,&H00000000,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n"
              "Style: W,{f},40,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n"
              ).format(f=font)
    ev = "".join("Dialogue: 0,0:00:00.00,0:00:10.00,%s,,0,0,0,,%s\n" % e for e in events)
    return head + styles + "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + ev


def title_geom(v, portrait):
    t = v["title"]
    return {"ml": t["ml"], "an": t["an"], "y": t["y"][portrait], "top": t["top"], "size": t["size"],
            "xr": t["xr"][portrait], "bottom": t["bottom"][portrait]}


def title_event(g, lines, size, style):
    # viền chữ 4 px + phần thừa của nét nghiêng lấn trái → lùi 6 px để mép chữ thật nằm trong lề
    return (style, "{\\an%d\\pos(%d,%d)\\fs%d}%s" % (g["an"], g["ml"] + 6, g["y"], size, ass_lines(lines)))


def badge_event(v, badge, style):
    x, y, size = v["badge"]
    return (style, "{\\an7\\pos(%d,%d)\\fs%d}%s" % (x, y, size, "".join(esc(c) for c in badge)))


def bbox(ff, v, font, event, work):
    """Vẽ chữ trắng lên nền đen rồi đo khung chữ thật (x0, y0, x1, y1) + font libass đã dùng."""
    with open(os.path.join(work, "do.ass"), "w", encoding="utf-8") as fh:
        fh.write(ass_doc(v, font, [event]))
    res = run([ff, "-hide_banner", "-nostdin", "-v", "info", "-f", "lavfi", "-i",
               "color=c=black:s=%dx%d:r=1:d=1" % (v["w"], v["h"]), "-vf", "ass=do.ass", "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "gray", "-"], cwd=work, binary=True)
    log = res.stderr.decode("utf-8", "replace")
    data = res.stdout
    if res.returncode != 0 or len(data) < v["w"] * v["h"]:
        die("ffmpeg không vẽ được chữ để đo: %s" % log.strip()[-400:])
    fonts = {font_used(ln) for ln in log.splitlines() if "fontselect:" in ln and "->" in ln}
    table = bytes(0 if i < 40 else 255 for i in range(256))
    w = v["w"]
    y0 = y1 = None
    x0, x1 = w, -1
    for y in range(v["h"]):
        line = data[y * w:(y + 1) * w].translate(table)
        if not line.strip(b"\0"):
            continue
        y0 = y if y0 is None else y0
        y1 = y
        x0 = min(x0, len(line) - len(line.lstrip(b"\0")))
        x1 = max(x1, len(line.rstrip(b"\0")) - 1)
    return (None if y0 is None else (x0, y0, x1, y1)), fonts


def est(word, size):
    total = 0
    for ch, _ in word:
        base = unicodedata.normalize("NFD", ch)[0]
        total += _W.get(ch, _W.get(base, 600 if base.isupper() else 560))
    return total * size / 1117.0


DASHES = ("-", "–", "—")


def break_cost(words, i):
    """Giá của chỗ ngắt trước từ thứ i: 0 sau : ; · 4 sau , hay sau dấu gạch, trước & vs ( · 14 giữa một cụm từ ·
    24 khi tách cặp ngắn "X & Y" (X đứng ngay sau đầu câu hay dấu : ; ,) · 28 khi dòng mới mở đầu bằng dấu gạch
    (trông như gạch đầu dòng) hay dòng trên kết thúc bằng & / vs."""
    prev = "".join(c for c, _ in words[i - 1])
    nxt = "".join(c for c, _ in words[i])
    if nxt in DASHES or prev in ("&", "vs"):
        return 28
    if nxt in ("&", "vs") and (i < 2 or "".join(c for c, _ in words[i - 2])[-1] in ":;,"):
        return 24   # "Âm & Dương" ngay sau dấu : — cặp ngắn, đừng tách
    if prev[-1] in ":;":
        return 0
    if prev[-1] == "," or prev in DASHES or nxt in ("&", "vs") or nxt.startswith("("):
        return 4
    return 14


def split_lines(words, size, n, maxw):
    """Chia từ thành n dòng vừa maxw: ít dòng một-từ nhất, chỗ ngắt rẻ nhất, rồi dòng dài nhất ngắn nhất
    → (số dòng một-từ, giá các chỗ ngắt, các dòng), hoặc None khi không cách chia nào vừa."""
    pre = [0.0]
    for w in words:
        pre.append(pre[-1] + est(w, size))
    sp = _W[" "] * size / 1117.0
    k = len(words)
    best = None
    for cut in itertools.combinations(range(1, k), n - 1):
        b = (0,) + cut + (k,)
        spans = [(b[i], b[i + 1]) for i in range(n)]
        widest = max(pre[j] - pre[i] + sp * (j - i - 1) for i, j in spans)
        if widest > maxw:
            continue
        orphans = sum(j - i == 1 for i, j in spans) if n > 1 else 0
        key = (orphans, sum(break_cost(words, c) for c in cut), widest)
        if best is None or key < best[0]:
            best = (key, [words[i:j] for i, j in spans])
    return (best[0][0], best[0][1], best[1]) if best else None


def candidates(g, hard, maxw):
    """Mọi cách đặt (cỡ chữ, các dòng) ≤ 3 dòng vừa vùng chữ theo ước lượng, xếp theo điểm: cỡ chữ to, trừ giá các
    chỗ ngắt (break_cost), trừ 24 điểm mỗi dòng chỉ một từ."""
    smax, smin = g["size"]
    avail = g["bottom"] - g["top"]
    out = []
    for size in range(smax, smin - 1, -2):
        if len(hard) > 1:
            if len(hard) * size <= avail and all(split_lines(ln, size, 1, maxw) for ln in hard):
                out.append((size, size, hard))
            continue
        for n in range(1, min(3, len(hard[0])) + 1):
            got = split_lines(hard[0], size, n, maxw) if n * size <= avail else None
            if got:
                orphans, cost, lines = got
                out.append((size - cost - 24 * orphans, size, lines))
    out.sort(key=lambda c: (-c[0], -c[1], len(c[2])))
    return out


def fits(g, box):
    x0, y0, x1, y1 = box
    return x0 >= g["ml"] and x1 <= g["xr"] - 1 and y0 >= g["top"] and y1 <= g["bottom"]


def plain(words):
    return " ".join("".join(c for c, _ in w) for w in words)


def fit_title(ff, v, g, font, hard, work):
    """Cách đặt điểm cao nhất mà chữ thật (đo bằng libass) nằm trong vùng chữ → bố cục hoặc None."""
    maxw = g["xr"] - g["ml"] - 16   # trừ phần lùi 6 px, viền và bóng
    fonts = set()
    for _, size, lines in candidates(g, hard, maxw)[:12]:
        box, f = bbox(ff, v, font, title_event(g, lines, size, "M"), work)
        fonts |= f
        if box and fits(g, box):
            return {"size": size, "lines": lines, "box": box, "fonts": fonts}
    return None


# ---------- bố cục, ghép ảnh ----------

def place_portrait(ff, v, path, cache):
    """→ (chỗ đặt chân dung, lỗi). PNG có vùng trong suốt: giữ nguyên, thu cho vừa khung, đứng chạm đáy; ảnh đục:
    cắt vuông (lệch lên trên, nơi thường có mặt) thành hình tròn viền vàng."""
    info = image_info(ff, path, cache)
    if not info:
        return None, "ffmpeg không đọc được ảnh chân dung %s" % path
    iw, ih, alpha = info
    if alpha:
        bx0, by0, bx1, by1 = v["cutout"]
        k = min((bx1 - bx0) / float(iw), (by1 - by0) / float(ih))
        w, h = max(2, int(iw * k) // 2 * 2), max(2, int(ih * k) // 2 * 2)
        return {"mode": "tách nền", "x": (bx0 + bx1) // 2 - w // 2, "y": by1 - h, "w": w, "h": h}, None
    cx, cy, d, b = v["circle"]
    o = d + 2 * b
    return {"mode": "khung tròn", "x": cx - o // 2, "y": cy - o // 2, "w": o, "h": o, "d": d, "b": b}, None


def place_logo(ff, v, path, cache):
    info = image_info(ff, path, cache)
    if not info:
        return None, "ffmpeg không đọc được ảnh logo %s" % path
    iw, ih, _ = info
    mr, y, lh = v["logo"]
    w, h = int(round(iw * lh / float(ih))), lh
    if w > 260:
        w, h = 260, int(round(ih * 260.0 / iw))
    w, h = max(2, w // 2 * 2), max(2, h // 2 * 2)
    return {"x": v["w"] - mr - w, "y": y, "w": w, "h": h}, None


def plan_layout(ff, v, font, row, work, cache):
    """→ (bố cục, lỗi, ghi chú). Bản dọc: chỗ ngắt | không vừa thì tự ngắt lại (ghi chú), không chặn bản ngang."""
    lay = {"portrait": None, "logo": None}
    if row["chan_dung"]:
        lay["portrait"], err = place_portrait(ff, v, row["chan_dung"], cache)
        if err:
            return None, err, None
    if row["logo"]:
        lay["logo"], err = place_logo(ff, v, row["logo"], cache)
        if err:
            return None, err, None
    for col in ("nen", "nen_doc"):
        if row[col] and not image_info(ff, row[col], cache):
            return None, "ffmpeg không đọc được ảnh %s %s" % (IMAGE_COLS[col], row[col]), None
    g = title_geom(v, bool(row["chan_dung"]))
    hard, note = row["hard"], None
    fit = fit_title(ff, v, g, font, hard, work)
    if not fit and len(hard) > 1 and v["suffix"]:
        fit = fit_title(ff, v, g, font, [[w for ln in hard for w in ln]], work)
        if fit:
            note = "chỗ ngắt | không vừa khung chữ hẹp của bản dọc — bản dọc tự ngắt lại"
    if not fit:
        smin = g["size"][1]
        if len(hard) > 1:
            widest = max(hard, key=lambda ln: sum(est(w, smin) for w in ln))
            return None, ("các dòng ngắt bằng | không vừa ở cỡ nhỏ nhất %d px (dòng dài nhất: «%s») — bỏ | để script "
                          "tự ngắt, hoặc dời chỗ ngắt cho dòng đó ngắn lại" % (smin, plain(widest))), None
        return None, "title quá dài: cỡ chữ nhỏ nhất %d px vẫn không vừa 3 dòng — rút ngắn title" % smin, None
    lay.update(fit)
    if row["badge"]:
        bb, f = bbox(ff, v, font, badge_event(v, row["badge"], "W"), work)
        lay["fonts"] |= f
        if not bb or bb[2] + 16 > v["w"] * 0.6:
            return None, "badge quá dài (quá 60% bề ngang ảnh) — rút ngắn cột badge", None
        lay["badge_box"] = (bb[0] - 16, bb[1] - 10, bb[2] - bb[0] + 33, bb[3] - bb[1] + 21)
    return lay, None, note


def plan_all(ff, font, tsv, jobs, work):
    """Đo bố cục mọi việc (row, kind, dest). Lỗi bản ngang → errors (chặn cả lượt in); lỗi bản dọc → cảnh báo, bỏ
    riêng bản dọc đó."""
    plans, errors, warns, fonts, cache = [], [], [], set(), {}
    for row, kind, dest in jobs:
        lay, err, note = plan_layout(ff, LAYOUTS[kind], font, row, work, cache)
        if err and kind == "ngang":
            errors.append((row["line"], "%s (ngang)" % err))
            continue
        if err:
            warns.append("%s:%d: %s (doc) — chưa in bản dọc; bản ngang vẫn in. Sửa title rồi in lại bản dọc: "
                         "render --doc --skip-existing" % (shown(tsv), row["line"], err))
            continue
        if note:
            warns.append("%s:%d: %s (doc)" % (shown(tsv), row["line"], note))
        fonts |= lay["fonts"]
        plans.append((row, kind, dest, lay))
    return plans, errors, warns, fonts


def fallback_background(v, portrait):
    """Nền vẽ sẵn, tất định: chuyển màu chàm → xanh, hai vòng tròn mảnh và 8 quẻ bát quái màu vàng nhạt."""
    w, h = v["w"], v["h"]
    cx, cy, r = v["deco"][portrait]
    ring = ("(clip(2.5-abs(hypot(X-{cx},Y-{cy})-{r}),0,1)+clip(2.5-abs(hypot(X-{cx},Y-{cy})-{r2}),0,1))"
            .format(cx=cx, cy=cy, r=r, r2=int(r * 0.42)))
    chain = ["color=c=black:s=%dx%d:r=1:d=1" % (w, h), "format=rgb24",
             "geq=r='14+26*Y/H+150*%s':g='20+30*X/W+120*%s':b='46+46*(1-Y/H)+40*%s'" % (ring, ring, ring)]
    bar, half, thick, gap = 60, 26, 9, 9
    for k, bits in enumerate(TRIGRAMS):
        ang = math.radians(-90 + 45 * k)
        tx = int(round(cx + 0.70 * r * math.cos(ang))) - bar // 2
        ty = int(round(cy + 0.70 * r * math.sin(ang))) - (3 * thick + 2 * gap) // 2
        for j, bit in enumerate(bits):
            y = ty + j * (thick + gap)
            parts = [(tx, bar)] if bit == "1" else [(tx, half), (tx + bar - half, half)]
            chain += ["drawbox=x=%d:y=%d:w=%d:h=%d:color=%s@0.55:t=fill" % (x, y, bw, thick, GOLD) for x, bw in parts]
    return ",".join(chain + ["format=rgba"])


def build_graph(v, row, lay, bg):
    """→ (đối số -i, chuỗi filter_complex). Thứ tự lớp: nền → lớp tối (dải chuyển + tấm mềm ôm vùng chữ) → chân dung →
    logo → nhãn → chữ."""
    w, h = v["w"], v["h"]
    inputs, chains, n = [], [], 0
    if bg:
        inputs += image_input(bg)
        chains.append("[0:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1,format=rgba[bg]"
                      % (w, h, w, h))
        n = 1
    else:
        chains.append(fallback_background(v, bool(row["chan_dung"])) + "[bg]")
    x0, y0, x1, y1 = lay["box"]
    out = "hypot(max(max(%d-X,X-%d),0),max(max(%d-Y,Y-%d),0))" % (x0 - 24, x1 + 24, y0 - 18, y1 + 18)
    plate = "%d*clip(1-%s/70,0,1)" % (PLATE, out)
    chains.append("color=c=black:s=%dx%d:r=1:d=1,format=rgba,geq=r=0:g=0:b=0:a='max(%s,%s)'[sh]"
                  % (w, h, v["shade"][bool(row["chan_dung"])], plate))
    chains.append("[bg][sh]overlay=0:0[l0]")
    last = "l0"
    p = lay["portrait"]
    if p:
        inputs += image_input(row["chan_dung"])
        if p["mode"] == "tách nền":
            chains.append("[%d:v]format=rgba,scale=%d:%d[p]" % (n, p["w"], p["h"]))
        else:
            d, b, o = p["d"], p["b"], p["w"]
            circle = "255*clip(%g-hypot(X-%g,Y-%g)+0.5,0,1)"
            chains.append("[%d:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d:(iw-%d)/2:(ih-%d)/4,"
                          "setsar=1,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='%s'[pm]"
                          % (n, d, d, d, d, d, d, circle % (d / 2.0, d / 2.0 - 0.5, d / 2.0 - 0.5)))
            chains.append("color=c=%s:s=%dx%d:r=1:d=1,format=rgba,geq=r=255:g=212:b=0:a='%s'[pr]"
                          % (YELLOW_BOX, o, o, circle % (o / 2.0, o / 2.0 - 0.5, o / 2.0 - 0.5)))
            chains.append("[pr][pm]overlay=%d:%d[p]" % (b, b))
        chains.append("[%s][p]overlay=%d:%d[l1]" % (last, p["x"], p["y"]))
        last, n = "l1", n + 1
    lg = lay["logo"]
    if lg:
        inputs += image_input(row["logo"])
        chains.append("[%d:v]format=rgba,scale=%d:%d[lg]" % (n, lg["w"], lg["h"]))
        chains.append("[%s][lg]overlay=%d:%d[l2]" % (last, lg["x"], lg["y"]))
        last, n = "l2", n + 1
    draw = []
    if row["badge"]:
        draw.append("drawbox=x=%d:y=%d:w=%d:h=%d:color=%s:t=fill" % (lay["badge_box"] + (YELLOW_BOX,)))
    draw.append("ass=in.ass")
    chains.append("[%s]%s[out]" % (last, ",".join(draw)))
    return inputs, ";".join(chains)


def render_one(ff, v, font, row, lay, dest, work):
    with open(os.path.join(work, "in.ass"), "w", encoding="utf-8") as fh:
        events = [title_event(title_geom(v, bool(row["chan_dung"])), lay["lines"], lay["size"], "T")]
        if row["badge"]:
            events.append(badge_event(v, row["badge"], "B"))
        fh.write(ass_doc(v, font, events))
    inputs, graph = build_graph(v, row, lay, lay["bg"])
    tmp = temp_in(os.path.dirname(dest), ".jpg")
    for q in (2, 5, 10):
        res = run([ff, "-hide_banner", "-loglevel", "error", "-nostdin"] + inputs +
                  ["-filter_complex", graph, "-map", "[out]", "-frames:v", "1", "-q:v", str(q), "-y", tmp], cwd=work)
        if res.returncode != 0 or os.path.getsize(tmp) == 0:
            os.remove(tmp)
            die("ffmpeg không ghép được ảnh %s: %s" % (shown(dest), res.stderr.strip()[-400:]))
        if os.path.getsize(tmp) < JPG_LIMIT:
            break
    size = os.path.getsize(tmp)
    if size >= JPG_LIMIT:
        os.remove(tmp)
        die("ảnh %s vẫn ≥ 2 MB sau khi nén — YouTube không nhận" % shown(dest))
    deliver(tmp, dest)
    return size


def describe(row, kind, lay):
    bg = row["nen_doc"] if kind == "doc" and row["nen_doc"] else row["nen"]
    lay["bg"] = bg
    p = lay["portrait"]
    who = "%s x=%d,y=%d,w=%d,h=%d" % (p["mode"], p["x"], p["y"], p["w"], p["h"]) if p else "không"
    return "nền %s · chân dung %s" % (os.path.basename(bg) if bg else "vẽ sẵn", who)


# ---------- check, render ----------

def cmd_check(args):
    rows, errors = read_tsv(args.tsv)
    if errors:
        report_errors(args.tsv, errors)
        sys.exit(1)
    check_font(args.font)
    ff = find_ffmpeg(args.ffmpeg, required=False)
    if not ff:
        print("Cảnh báo: chưa có ffmpeg có libass — chưa xem trước được cách ngắt dòng (TSV vẫn hợp lệ)")
        print("OK: %s: %d dòng hợp lệ" % (shown(args.tsv), len(rows)))
        return
    kinds = ["ngang"] + (["doc"] if args.doc else [])
    work = tempfile.mkdtemp(prefix="mk-thumbnail-")
    try:
        plans, errors, warns, fonts = plan_all(ff, args.font, args.tsv, [(r, k, None) for r in rows for k in kinds],
                                               work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    warn = font_check(args.font)
    if warn:
        print("Cảnh báo: " + warn)
    for f in sorted(fonts):
        print("Font dùng thật: " + f)
    for row, kind, _, lay in plans:
        print("Xem trước: %s:%d: %s · cỡ %d · %s · %s" % (shown(args.tsv), row["line"], kind, lay["size"],
                                                         " / ".join(plain(ln) for ln in lay["lines"]),
                                                         describe(row, kind, lay)))
    for w in warns:
        print("Cảnh báo: " + w)
    if errors:
        report_errors(args.tsv, errors)
        sys.exit(1)
    print("OK: %s: %d dòng hợp lệ" % (shown(args.tsv), len(rows)))


def cmd_render(args):
    rows, errors = read_tsv(args.tsv)
    if errors:
        report_errors(args.tsv, errors)
        sys.exit(1)
    check_font(args.font)
    out = os.path.abspath(args.out_dir or os.path.dirname(os.path.abspath(args.tsv)))
    kinds = ["ngang"] + (["doc"] if args.doc else [])
    jobs, skipped = [], []
    for row in rows:
        for kind in kinds:
            dest = os.path.join(out, out_name(row["video"]) + LAYOUTS[kind]["suffix"] + ".jpg")
            if os.path.lexists(dest):
                if not args.skip_existing:
                    die("%s đã có — chọn thư mục khác, hoặc chạy lại với --skip-existing (skill không ghi đè)"
                        % shown(dest))
                skipped.append(dest)
                continue
            jobs.append((row, kind, dest))
    ff = find_ffmpeg(args.ffmpeg)
    warn = font_check(args.font)
    work = tempfile.mkdtemp(prefix="mk-thumbnail-")
    try:
        plans, errors, warns, fonts = plan_all(ff, args.font, args.tsv, jobs, work)
        if errors:
            report_errors(args.tsv, errors)
            sys.exit(1)
        if warn:
            print("Cảnh báo: " + warn)
        for f in sorted(fonts):
            print("Font dùng thật: " + f)
        for w in warns:
            print("Cảnh báo: " + w)
        for dest in skipped:
            print("Bỏ qua (đã có): %s" % shown(dest))
        if plans:
            make_dir(out)
        for row, kind, dest, lay in plans:
            v = LAYOUTS[kind]
            info = describe(row, kind, lay)
            size = render_one(ff, v, args.font, row, lay, dest, work)
            x0, y0, x1, y1 = lay["box"]
            print("OK: %s · %dx%d · %d KB · %s · cỡ chữ %d · %d dòng · vùng chữ x=%d–%d y=%d–%d" % (
                shown(dest), v["w"], v["h"], (size + 1023) // 1024, info, lay["size"], len(lay["lines"]),
                x0, x1, y0, y1))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    utf8_stdio()
    ap = argparse.ArgumentParser(description="Thumbnail YouTube theo khuôn: tên file → tiêu đề, ghép nền + chân dung.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("names", help="xem nhãn + tiêu đề tách từ tên file (không mở video)")
    p.add_argument("src", nargs="+")
    p.add_argument("--badge", default=DEFAULT_BADGE, help="mẫu nhãn góc, trường {word} {n} {p}")
    p.set_defaults(fn=cmd_names)
    p = sub.add_parser("prompt", help="ghi file prompt ảnh nền cho cả chuỗi (không gọi dịch vụ nào)")
    p.add_argument("src", nargs="*")
    p.add_argument("--tsv", help="lấy tiêu đề đã sửa và việc có chân dung từ thumbnail.tsv")
    p.add_argument("--assets", required=True)
    p.add_argument("--theme", default="calm scholarly lecture series")
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--doc", action="store_true", help="thêm prompt 9:16 cho bản dọc")
    p.set_defaults(fn=cmd_prompt)
    p = sub.add_parser("plan", help="ghi thumbnail.tsv: tiêu đề + ảnh nền/chân dung/logo cho từng video")
    p.add_argument("src", nargs="+")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--assets")
    p.add_argument("--badge", default=DEFAULT_BADGE, help="mẫu nhãn góc, trường {word} {n} {p}")
    p.add_argument("--update", action="store_true", help="đã có TSV: ghi bản mới thumbnail-N.tsv giữ sửa tay")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("check", help="kiểm thumbnail.tsv sau khi sửa tay, xem trước cách ngắt dòng")
    p.add_argument("tsv")
    p.add_argument("--doc", action="store_true", help="xem trước cả bản dọc")
    p.add_argument("--font", default="Arial")
    p.add_argument("--ffmpeg")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("render", help="ghép ảnh + in tiêu đề, nhãn → JPG")
    p.add_argument("tsv")
    p.add_argument("--out-dir")
    p.add_argument("--doc", action="store_true", help="thêm bản dọc 1080×1920")
    p.add_argument("--font", default="Arial")
    p.add_argument("--skip-existing", action="store_true")
    p.add_argument("--ffmpeg")
    p.set_defaults(fn=cmd_render)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
