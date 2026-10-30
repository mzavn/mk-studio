# mk-studio

Bộ skill **content, review và đóng gói giá trị** cho AI coding agent (Claude Code, omp, Codex và các agent hỗ trợ chuẩn Agent Skills). Mỗi skill hoạt động độc lập, cài đặt riêng biệt theo nhu cầu.

Bộ skill kỹ thuật & lập trình đi kèm là **[mk-lab](https://github.com/mzavn/mk-lab)** (Spec-Driven Development).

---

## Danh mục skill hiện có

| Skill | Lệnh Claude Code | Gọi bằng lời tự nhiên | Mục đích chính |
|---|---|---|---|
| **`mk-star`** | `/mk:star` | *"viết nhật ký ngày"*, *"giải quyết vấn đề"*, *"luyện case 05"* | Hệ nhật ký STAR 5 loại: biến cảm xúc/vấn đề/thành công thành quyết định, kế hoạch và tài sản đóng gói. Lưu hoàn toàn ở máy cá nhân (`~/nhat-ky-star/`). |
| **`mk-exec-review`** | `/mk:exec-review <file>` | *"phản biện bài <đường dẫn>"*, *"đọc bài như CEO"*, *"soát bài"* | Hội đồng C-level (CEO, CFO, CMO, COO, CTO) phản biện bài viết theo chân dung khách hàng thật, bóc giọng văn AI, chuẩn hóa thuật ngữ, tối ưu SEO/GEO/AEO, duyệt từng mã gợi ý trước khi sửa. |
| **`mk-subtitle`** | `/mk:subtitle <file hoặc link YouTube>` | *"xử lý phụ đề <file>"*, *"lấy phụ đề youtube"*, *"cắt ừ à"*, *"chia file con"*, *"cắt bài giảng"* | Phụ đề cho khâu dựng video và chia buổi học dài thành file con: tải phụ đề có sẵn từ link YouTube (có mốc từng từ), duyệt từ đệm xoá khỏi phụ đề kèm danh sách cắt, chuẩn hoá tiếng Việt, dịch tiếng Anh, lập Bảng lệnh Editor (Action Sheet) cắt rác/giải lao và chia bài giảng 20–30p giữ trọn vẹn ngữ cảnh vấn đáp. |
| **`mk-video-cutter`** | `/mk:video-cutter <video>` | *"cắt video"*, *"chia clip con"*, *"bỏ thanh zoom"*, *"video dọc 9:16"*, *"nâng 1080p"*, *"làm nét video"* | Cắt video bài giảng dài thành clip chuyên đề theo Action Sheet: tự cắt viền thừa của video quay màn hình (thanh menu, thanh Zoom, dải đen) có ảnh xem trước để duyệt, xuất khung 16:9 / 9:16 / tuỳ chỉnh ở chuẩn phù hợp nguồn (720p → 1080p), làm nét vừa phải, giữ trọn hình, hoặc giữ nguyên hình gốc; cân bằng âm thanh hai tai, chuẩn âm lượng -16 LUFS, nghiệm thu bằng `ffprobe`. |

> **Lưu ý tên lệnh và quyền:**
> - Gọi nhanh qua slash command: `/mk:star`, `/mk:exec-review`, `/mk:subtitle`, `/mk:video-cutter`. Thư mục cài đặt và cờ `--skill` dùng tên gạch nối: `mk-star`, `mk-exec-review`, `mk-subtitle`, `mk-video-cutter`.
> - Tiền tố `mk:` là quy ước định danh riêng của bộ skill này, **không** phải plugin Claude Code tên `mk`. Nếu bạn cấu hình quyền trong `settings.json`, hãy khai báo theo tên skill, vd `Skill(mk:star)`.
---

## 1. mk:star — Hệ nhật ký STAR (5 loại)

`mk:star` đồng hành dẫn dắt bạn viết nhật ký từng câu hỏi theo đúng khuôn mẫu chuẩn, lưu thành từng file Markdown độc lập tại thư mục riêng (`~/nhat-ky-star/`) và theo dõi tiến độ qua các cột mốc thực hành.

### 5 loại nhật ký

| Loại | Thời điểm viết | Trọng tâm đầu ra |
|---|---|---|
| **I · Daily Diary** | Trong ngày hoặc cuối ngày | Cải tiến 1% mỗi ngày, cam kết hành động ngày mai (*One Action* có giờ cụ thể). |
| **II · Problem Solving** | Gặp khó khăn, vướng mắc, thất bại | Bản đầy đủ 8 bước A–Z (Situation → Think & Feel → SEE → UNDERSTAND → DECIDED → ACTION → EVOLVE) hoặc bản "viết nhanh" 4 bước (R → S → T → A). |
| **III · Packing Value** | Sau một thành công hoặc kết quả tốt | Đóng gói kinh nghiệm thành 1 trong 8 dạng tài sản chuyển giao được. |
| **IV · Creating Future** | Trước sự kiện, dự án hoặc cuộc gặp quan trọng | Kiến tạo kịch bản, chuẩn bị tâm thế và phương án ứng phó trước khi hành động. |
| **V · Mentoring** | Trước buổi 1-1, đào tạo, coaching, bán hàng | Thấu cảm người đối diện (R → S → T → A) rồi soi chiếu lại năng lực người dẫn dắt. |

### Tính năng đi kèm
- **Kho bài tập & Case thực hành:** 4 case giải mẫu chi tiết từng bước và 28 case tình huống quản trị/đời sống để luyện tập phản xạ giải quyết vấn đề.
- **Theo dõi tiến độ (`progress.py`):** Tự động đếm số bài trọn vẹn theo 4 cột mốc (28 / 300 / 1.000 / 10.000 bài), cảnh báo việc hẹn chưa làm và kết quả đến hạn nghiệm thu.
- **An toàn dữ liệu cá nhân:** Nhật ký lưu hoàn toàn cục bộ trên máy bạn; script cảnh báo nếu thư mục nằm trong git; ghi file nguyên tử (`os.replace`) chống mất dữ liệu khi gián đoạn; từ chối can thiệp qua symlink.

---

## 2. mk:exec-review — Hội đồng C-level phản biện bài viết

`mk:exec-review` đóng vai trò một ban cố vấn lãnh đạo độc lập đọc bài viết tiếng Việt (Markdown) bằng lăng kính của chân dung khách hàng mục tiêu (*Customer Persona*), rà soát toàn diện trước khi xuất bản.

### 5 góc nhìn phản biện

1. **Hội đồng C-level theo Persona:** Chọn 2–4 vai lãnh đạo phù hợp (CEO: chiến lược & hành động; CFO: chi phí & ROI; CMO: khách hàng & thông điệp; COO: quy trình vận hành; CTO: khả thi công nghệ). Chỉ ra chính xác dòng giữ chân, dòng gây mất niềm tin và câu hỏi còn mắc lại.
2. **Soi dấu hiệu giọng văn AI:** Nhận diện các cấu trúc sáo mòn tiếng Việt (mở bài sáo, đối lập lật ngược lặp lại, từ ngữ phô trương, dịch thô từ tiếng Anh, lạm dụng gạch nối `—`), bảo vệ các câu mang chất giọng người thật và ví dụ thực chiến.
3. **Chuẩn hóa thuật ngữ:** Phát hiện đồng nghĩa trôi dạt, sai lệch vị trí dấu thanh (hoá/hóa), gạch nối/viết hoa giữa câu (Fanpage/fanpage); đề xuất dạng chuẩn dựa trên bảng thuật ngữ hoặc định nghĩa gốc của tác giả; tuyệt đối không gộp các khái niệm cố ý tách biệt hoặc từ ngữ ẩn dụ.
4. **Tối ưu SEO / GEO / AEO:** 
   - *SEO:* Khớp ý định tìm kiếm thực tế của persona, tối ưu tiêu đề và thẻ mô tả.
   - *AEO (Answer Engine):* Câu trả lời định nghĩa súc tích 40–60 tiếng ngay dưới tiêu đề dạng hỏi, cấu trúc độc lập.
   - *GEO (Generative Engine - ChatGPT/Perplexity/AI Overviews):* Trích dẫn được, thực thể định danh rõ ràng, E-E-A-T minh bạch từ trải nghiệm thực tế.
5. **Ý tưởng cải thiện (Mã Y):** Đề xuất 3–5 hướng nâng cấp bài viết (ví dụ gần gũi hơn, con số tự nhẩm trong 1 phút, câu hỏi mang vào cuộc họp) có xếp hạng mức độ tác động.

### Bất biến & Quy trình duyệt sửa
- **Tác giả làm chủ:** Phản biện được tách riêng sang một subagent độc lập (chỉ đọc). Báo cáo trả về bảng gợi ý đánh mã (`A` giọng AI, `T` thuật ngữ, `S` SEO/GEO, `C` hội đồng, `Y` ý tưởng).
- **Kiểm cơ học bằng script (`check_report.py`):** Kiểm tra tính duy nhất của đoạn trích, vị trí dòng, loại sửa, không sinh số liệu mới, không đổi đích link/ảnh/HTML ngầm.
- **Duyệt trước khi sửa:** Tác giả duyệt mã nào (`duyệt A1 T1-T3`, `S1:2`), agent chỉ sửa đúng mã đó. Tuyệt đối giữ nguyên tone giọng, cấu trúc lập luận và ví dụ gốc của tác giả. Chỗ thiếu số liệu sẽ để ô `[điền: …]`, không bao giờ bịa đặt.

---

## 3. mk:subtitle — Phụ đề & chia file con cho khâu dựng video

Gõ `/mk:subtitle <file .srt, .vtt hoặc .txt>` hoặc đưa **link YouTube**. Skill cung cấp hai mode nghiệp vụ.

**Chưa có phụ đề?** Video đã đăng YouTube (kể cả không công khai) → skill tải phụ đề có sẵn trong vài giây (cần `yt-dlp`), ưu tiên bản chủ kênh tải lên, không có thì bản tự động gốc có mốc từng từ; bản dịch máy bị từ chối. Chỉ có file video → skill không tự nhận giọng, hướng dẫn bạn tự cài whisper.cpp (miễn phí, chạy trên máy) để tạo SRT rồi quay lại.

### Mode phụ đề (SRT / VTT)

1. **Từ đệm "à, ừ, ờ, ừm…" và lặp từ:** đánh dấu thành hai nhóm — A (âm đệm giữa câu, đề xuất xoá) và B (cần nghe lại: câu đáp "Ừ, đúng rồi", tiểu từ hỏi "Thế à?", lặp từ). Bạn duyệt mã nào thì mới xoá khỏi phụ đề và đưa vào danh sách đoạn cắt cho editor.
2. **Chia câu, ngắt dòng:** tối đa 2 dòng × 42 ký tự, cảnh báo cue đọc không kịp.
3. **Chuẩn hoá tiếng Việt:** sửa lỗi nhận giọng theo bảng thuật ngữ của repo, chính tả, dấu câu; giữ đúng lời người nói, chỗ chưa chắc đưa vào danh sách xác nhận.
4. **Dịch tiếng Anh:** mỗi cue dịch đúng một cue, cùng mốc thời gian.
5. **Đầu ra:** thư mục giao file gồm phụ đề Việt/Anh timeline gốc, phụ đề sau cắt, track `✂` tham chiếu timeline, `cat.csv` và `BAN-GIAO.md`.

### Mode chia buổi học dài thành file con (Quy trình Kaizen)

Áp dụng cho bài giảng dài 2–4 tiếng (bản chép lời có mốc `[mm:ss]` TXT/MD, SRT hoặc VTT):

1. **Phản biện 3 trục (Fable-Thinking):** lọc sạch 100% thời gian chết (mic check đầu giờ, giải lao giữa bài, mất tiếng, thủ tục bế mạc) nhưng bảo toàn trọn vẹn tri thức cốt lõi.
2. **Topic-First 20–30 phút:** chia bài giảng thành các file con chuẩn vàng kèm mã định danh đồng bộ (`Buổi 1:P1`, `Buổi 1:P2`…; ca vấn đáp độc lập đặt mã `P5.1`, `P5.2`…).
3. **Bảo toàn ngữ cảnh:** bắt buộc đủ cấu trúc hai vế `[A Hỏi]` (bối cảnh) và `[B Đáp]` (khai tuệ); giữ trọn vẹn nhịp 3 bước của đối thoại Socrates `[B Hỏi]` → `[A Đáp]` → `[B Khai Tuệ]`.
4. **Đầu ra hoàn chỉnh cho Editor:** xuất **Bảng lệnh Editor (Action Sheet)** với timecode chính xác và lệnh 🛑 CUT / 🟢 KEEP; sinh khung bài giảng Markdown; xuất phụ đề `.srt` riêng từng file con (bắt đầu từ 00:00:00); kiểm tra lỗi bằng lệnh lint và xuất dòng tổng kết Kaizen sau mỗi buổi.
5. **Cắt video con & Cân bằng âm thanh (Lossless FFmpeg):** khảo sát âm lượng/lệch kênh hai tai bằng lệnh `probe-audio`, tự động cắt hàng loạt video con theo Action Sheet với tốc độ siêu tốc (`-c:v copy` giữ nguyên 100% chất lượng hình ảnh gốc, chỉ re-encode audio sang AAC 192k khi cần cân bằng âm thanh và đưa về chuẩn -16 LUFS).
---

## 4. mk:video-cutter — Cắt video bài giảng: khung hình sạch, âm thanh đều

Gõ `/mk:video-cutter <file_video.mp4> --sheet <file_action_sheet>`. Skill phân rã video bài giảng dài (2–4 tiếng) thành các clip chuyên đề (10–30 phút) theo Action Sheet:

1. **Khảo sát âm thanh:** đo độ lớn hai tai, phát hiện điếc một bên hoặc âm lượng quá nhỏ, chọn chế độ `copy` (giữ nguyên), `balance` (dual-mono) hoặc `master` (dual-mono + chuẩn -16 LUFS).
2. **Khung hình sạch (mới):** video quay cả cửa sổ Zoom thường dính thanh menu, thanh công cụ và dải đen. Skill tìm vùng bài giảng (phần chuyển động) và xuất 2 ảnh xem trước: khung đỏ = phần giữ, và một khung hình thành phẩm. Bạn duyệt rồi mới cắt. Nếu Zoom đổi bố cục giữa buổi, skill báo đoạn bị ảnh hưởng để cắt riêng.
3. **Khung đầu ra:** 16:9, 9:16, 1:1, 4:5 hoặc kích thước tuỳ chỉnh. `--res auto` lên đúng một bậc chuẩn so với nguồn (720p → 1080p, phóng tối đa 1,8×); ép 2K/4K từ nguồn 720p sẽ bị cảnh báo vì chỉ làm file to, không nét hơn. Mặc định giữ trọn hình và bù nền đen; video dọc có thể dùng nền mờ.
4. **Làm nét vừa phải (`--enhance`):** khử khối vỡ do nén, khử nhiễu, làm nét nhẹ; chữ trên bảng gọn hơn mà không bị vẽ lại. Muốn nét hơn nữa thì tài liệu skill giới thiệu công cụ AI cài thêm (Real-ESRGAN, Topaz Video…) kèm rủi ro; skill không có sẵn các công cụ này.
5. **Chất lượng:** không đổi khung thì hình giữ nguyên từng điểm ảnh, cắt cả bài trong vài giây. Đổi khung thì máy nén lại ở mức cao (đo trên bài giảng thật: VMAF 97/100), mất khoảng 1/5 thời lượng clip trên Mac Apple Silicon (có làm nét: khoảng 1/3).
6. **Nghiệm thu:** `ffprobe` kiểm dung lượng, thời lượng, khung hình từng clip (`--expect-size 1920x1080`).

---

## Yêu cầu môi trường

- Hệ điều hành: macOS hoặc Linux (hỗ trợ `bash` 3.2 trở lên). Windows: chạy `install.sh` trong Git Bash (đi kèm [Git for Windows](https://git-scm.com/downloads/win)); hiện `mk-subtitle` và `mk-video-cutter` đã xử lý bảng mã cho Windows (in tiếng Việt qua pipe).
- Python: `python3` ≥ 3.8 (chỉ sử dụng thư viện chuẩn, không cần cài thư viện ngoài).
- Công cụ: `git`, [GitHub CLI](https://cli.github.com) đã đăng nhập (`gh auth status`), và `ffmpeg` / `ffprobe` (cho tính năng khảo sát âm thanh & cắt video).
- Coding agent: Bất kỳ agent nào đọc thư mục skill chuẩn (`.claude/skills` hoặc `.agents/skills` như Claude Code, omp, Codex…).

---

## Cài đặt

Xem chi tiết từng bước cho người và agent tại [INSTALL.md](INSTALL.md).

### 1. Cài đặt toàn hệ thống (Global)
Mặc định cài đặt `mk-star` vào `~/.claude/skills/mk-star` và `~/.agents/skills/mk-star`:

```bash
gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global
```

### 2. Cài đặt skill cụ thể
Chỉ định tên thư mục skill qua cờ `--skill`:

```bash
# Cài đặt bộ phản biện exec-review cho toàn hệ thống
bash ~/.mk-studio/install.sh --global --skill mk-exec-review

# Cài đặt cả 3 skill
bash ~/.mk-studio/install.sh --global --skill mk-star
bash ~/.mk-studio/install.sh --global --skill mk-exec-review
bash ~/.mk-studio/install.sh --global --skill mk-subtitle
```

### 3. Cài đặt vào một dự án cụ thể (Project-level)
Chép skill vào thư mục `.claude/skills/<tên-skill>` của dự án (thêm `--agents-dir` nếu dùng Codex/omp):

```bash
bash ~/.mk-studio/install.sh --project ~/code/my-content --skill mk-exec-review
bash ~/.mk-studio/install.sh --project . --agents-dir --skill mk-exec-review
```

*Nguyên tắc cài đặt:* Luôn sao chép trực tiếp file, không dùng symlink; có manifest kiểm soát thay đổi; từ chối ghi đè nếu phát hiện sửa đổi thủ công trừ khi có `--force`.

---

## Cập nhật & Gỡ cài đặt

### Cập nhật
Cập nhật kéo bản phát hành mới nhất từ nhánh `main` (chỉ cập nhật tới commit có gắn tag release `vX.Y.Z`):

```bash
# Cập nhật tất cả skill đã cài đặt toàn hệ thống
bash ~/.mk-studio/install.sh --update

# Cập nhật cả bản global và bản project hiện tại
bash ~/.mk-studio/install.sh --update --global --project .
```

### Gỡ cài đặt
Gỡ bỏ thư mục skill an toàn (không làm ảnh hưởng tới bài viết hay dữ liệu nhật ký tại `~/nhat-ky-star/`):

```bash
bash ~/.mk-studio/install.sh --uninstall --global --skill mk-exec-review
bash ~/.mk-studio/install.sh --uninstall --project ~/code/my-content --skill mk-exec-review
```

---

## An toàn & Bảo mật

Bộ công cụ được thiết kế theo tiêu chuẩn an toàn cho Agentic SE:
- **Bảo vệ đường dẫn & Symlink:** Bộ installer từ chối ghi hoặc xoá xuyên qua symlink (kể cả thư mục cha như `~/.claude` hay `~/.claude/skills`); ngăn chặn rò rỉ đường dẫn máy cá nhân vào dotfiles công khai.
- **Toàn vẹn phát hành:** Lệnh `--update` bắt buộc kiểm tra chữ ký/tag phát hành ngữ nghĩa (`vX.Y.Z`), từ chối thực thi mã chưa qua phát hành chính thức từ nhánh `main`.
- **Chống Prompt Injection & Rò rỉ dữ liệu:**
  - Dữ liệu bài viết, chân dung khách hàng và quy ước dự án được đối xử là **dữ liệu thuần túy**, không phải câu lệnh chỉ thị.
  - Subagent phản biện bị cô lập trong môi trường chỉ đọc (`read-only`), không quyền thực thi lệnh shell, không truy cập internet, không duyệt link trỏ ra ngoài repository.
  - Mọi thao tác tạm thời của phiên làm việc diễn ra trong thư mục bảo mật riêng biệt (`mktemp -d`), được dọn dẹp sạch sau khi hoàn tất.

---

## Cấu trúc repository

```
mk-studio/
├── install.sh                       # Bộ cài đặt idempotent chuẩn POSIX (bash 3.2+)
├── INSTALL.md                       # Sổ tay hướng dẫn cài đặt cho người và agent
├── CHANGELOG.md                     # Lịch sử thay đổi các phiên bản
├── LICENSE                          # Giấy phép nguồn mở MIT
├── README.md
├── tests/                           # Kiểm thử tự động cho installer
└── skills/
    ├── mk-star/                     # Skill nhật ký STAR (/mk:star)
    │   ├── SKILL.md                 # Điểm điều phối, bộ câu hỏi, quy tắc an toàn
    │   ├── references/              # Hướng dẫn chi tiết 5 loại, kho case, bảng đối chiếu
    │   ├── assets/mau/              # Khung mẫu bài viết chuẩn cho từng loại
    │   └── scripts/                 # progress.py đo lường tiến độ và test suite
    ├── mk-exec-review/              # Skill hội đồng phản biện CxO (/mk:exec-review)
    │   ├── SKILL.md                 # Quy trình 5 bước: gom ngữ cảnh -> giao việc -> kiểm duyệt -> sửa
    │   ├── references/              # Bộ tiêu chí hội đồng, bóc giọng AI, chuẩn thuật ngữ, SEO/GEO/AEO
    │   ├── assets/                  # Mẫu giao việc cho subagent và mẫu báo cáo chuẩn
    │   └── scripts/                 # scan.py quét số liệu, check_report.py kiểm cơ học và test suite
    └── mk-subtitle/                 # Skill phụ đề cho khâu dựng video (/mk:subtitle)
        ├── SKILL.md                 # Quy trình: quét -> duyệt từ đệm -> chuẩn hoá -> dịch -> giao editor
        ├── references/              # Từ đệm, chuẩn hoá tiếng Việt, dịch tiếng Anh
        ├── assets/                  # Mẫu BAN-GIAO.md cho editor
        └── scripts/                 # subtitle.py (scan, fillers, clean, export, build, check, retime) và test suite
```

---

## Đóng góp & Phát triển

Dự án phát triển trên nhánh `dev` (`main` chỉ chứa các bản phát hành chính thức).

1. Commit tuân thủ chuẩn Conventional Commits, scope là tên thư mục skill: `feat(mk-star): …`, `feat(mk-subtitle): …`, `fix(install): …`.
2. Kiểm tra chất lượng (Definition of Done) trước khi phát hành:
   ```bash
   # Chạy toàn bộ test suites
   python3 -m unittest discover -s skills/mk-star/scripts/tests && \
   python3 -m unittest discover -s skills/mk-exec-review/scripts/tests && \
   python3 -m unittest discover -s skills/mk-subtitle/scripts/tests && \
   python3 -m unittest discover -s tests && \
   python3 -m unittest discover -s tools/tests

   # Kiểm tra cú pháp shell
   bash -n install.sh && /bin/bash -n install.sh
   ```
---

## Ghi công

- Skill **`mk:star`** được tổng hợp và chuyển hóa từ phương pháp luận nhật ký của **X3 Năng Suất** ([minhvq.notion.site](https://minhvq.notion.site)) — *"Video tự học STAR bậc cao"* và *"Thực hành Giải quyết vấn đề từ A-Z"*, phát hành theo sự đồng ý của tác giả nội dung.
- Skill **`mk:exec-review`** kế thừa tư duy biên tập thực chiến và mô hình kiểm duyệt đa tầng cho nhà sáng tạo nội dung.
- Skill **`mk:subtitle`** đúc kết từ quy trình biên tập transcript họp và giao phụ đề cho team dựng video.

---

## Giấy phép

Phát hành theo giấy phép nguồn mở [MIT License](LICENSE).

---

## English Summary

**mk-studio** is a collection of production-grade content and review skills for AI coding agents (Claude Code, omp, Codex, etc.). Its technical engineering counterpart is **[mk-lab](https://github.com/mzavn/mk-lab)**.

- **`/mk:star` (STAR Journaling Coach):** Guides users through five structured reflective journaling frameworks (Daily Diary, Problem Solving A–Z, Packing Value, Creating Future, Mentoring), backed by a 28-case practice repository, automated milestone metrics (`progress.py`), and privacy-first local storage in `~/nhat-ky-star/`.
- **`/mk:exec-review` (C-Suite Editorial Review):** Deploys an isolated read-only subagent acting as an executive board (CEO, CFO, CMO, COO, CTO) to critique Vietnamese Markdown articles through real customer personas. Audits AI-generated writing tells, standardizes specialized/coined terminology, optimizes for SEO/AEO/GEO, and enforces strict mechanical verification (`check_report.py`) before applying user-approved edits while preserving authentic author voice.
- **`/mk:subtitle` (Subtitles for Video Editing):** Takes an existing SRT/VTT file (including YouTube auto-captions with per-word timing), flags filler sounds and stutters for user approval, removes approved ones and exports an exact cut list, re-splits lines to subtitle standards, fixes Vietnamese speech-recognition errors and terminology, translates to English on the same timings, and re-times subtitles for the cut timeline — all as `.srt` files that CapCut, Premiere Pro, DaVinci Resolve and Final Cut Pro import.

Install via `bash install.sh --global --skill <name>`. All skills adhere to strict local isolation, symlink protection, release tag verification, and data safety constraints. Licensed under MIT.
