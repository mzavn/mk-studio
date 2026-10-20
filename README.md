# mk-studio

Bộ skill **content** cho AI agent (Claude Code, omp và các agent đọc thư mục skill chuẩn): viết, video, marketing, đóng gói giá trị bản thân. Mỗi skill độc lập, cài riêng từng cái.

Hiện có:

- **`/mk:star`** — hệ nhật ký STAR 5 loại: agent dẫn bạn viết nhật ký từng câu, lưu bài ở máy, đếm tiến độ. Cài mặc định.
- **`/mk:exec-review`** — hội đồng CEO / C-level phản biện bài viết của bạn: đọc bằng mắt chân dung khách hàng, soi giọng AI, chuẩn hoá thuật ngữ, tối ưu SEO / GEO / AEO; bạn duyệt gợi ý nào thì agent sửa đúng chỗ đó. Cài bằng `--skill mk-exec-review`.

Gọi skill như bộ ak: gõ `/mk:<tên>` trong Claude Code (vd `/mk:star`), hoặc nói bằng lời — agent tự nhận ra. Cài và gỡ theo tên thư mục `mk-<tên>` (`--skill mk-exec-review`). Tiền tố `mk:` là quy ước đặt tên của bộ này, không phải plugin: đã cài một plugin tên `mk` thì kiểm `/mk:star` mở đúng skill; quyền trong settings ghi theo tên mới, vd `Skill(mk:star)`.

Bộ skill lập trình đi kèm (specs, dev, test, bảo mật) là **[mk-lab](https://github.com/mzavn/mk-lab)**.

*English summary at the end.*

## mk:star — nhật ký STAR

`star` biến một lời than vãn thành quyết định, kế hoạch và bài học đóng gói được. Bạn kể một câu ("sáng nay cãi nhau với vợ về chuyện công ty"), agent đề xuất loại nhật ký hợp, hỏi từng câu theo mẫu và ghi nguyên văn câu trả lời vào một file markdown ở `~/nhat-ky-star/`.

| Loại | Viết khi |
|---|---|
| I · Daily Diary | trong ngày hoặc cuối ngày — mỗi ngày cải tiến 1% |
| II · Problem Solving | gặp thất bại, vướng mắc — bản đầy đủ 8 bước A–Z hoặc "viết nhanh" |
| III · Packing Value | sau một thành công — thành công thức chuyển giao được |
| IV · Creating Future | trước sự kiện, dự án, cuộc gặp quan trọng |
| V · Mentoring | trước buổi bán hàng, đào tạo, 1-1, coaching |

Kèm bộ câu hỏi cơ bản/chuyên sâu cho từng loại, 4 case giải mẫu và 28 case luyện tập, 8 dạng tài sản đóng gói, và `progress.py` đếm bài trọn vẹn theo cột mốc 28 / 300 / 1000 / 10000, nhắc One Action chưa làm và kết quả đến hạn ghi. Nhật ký là dữ liệu riêng: file chỉ ở máy bạn (agent cảnh báo nếu thư mục nằm trong git); nội dung trò chuyện vẫn đi qua nhà cung cấp AI của agent.

Cài xong, gõ `/mk:star` (Claude Code) hoặc nói với agent: "viết nhật ký ngày", "viết nhật ký giải quyết vấn đề", "luyện case 05", "tiến độ nhật ký".

## mk:exec-review — hội đồng C-level phản biện bài viết

Gõ `/mk:exec-review <đường dẫn bài>` (Claude Code) hoặc nói "phản biện bài `<đường dẫn>`". Agent đọc bài, luật viết của repo (`AGENTS.md`, `CLAUDE.md`…), file chân dung khách hàng (bắt buộc — không tìm thấy thì hỏi bạn) và bảng thuật ngữ nếu có; chạy `scan.py` đếm dấu hiệu giọng AI, biến thể thuật ngữ, vị trí từ khoá; hỏi bạn những gì file không trả lời được (người đọc chính, mục tiêu, nơi đăng, từ khoá, thuật ngữ tự đặt, mức sửa). Phần phản biện do **một agent riêng** làm — không phải agent đang trò chuyện với bạn — với các vai CEO, CFO, CMO, COO, CTO tuỳ bài. Báo cáo có bảng gợi ý đánh mã (`A1`, `T2`, `S3`…); bạn trả lời "duyệt A1 T1-T3" thì agent mới sửa file, giữ nguyên ý, ví dụ và giọng của bạn, không thêm số liệu (chỗ cần số để ô `[điền: …]`).

```bash
bash ~/.mk-studio/install.sh --global --skill mk-exec-review
```

## Yêu cầu

- `bash` (macOS hoặc Linux), `python3` ≥ 3.8, `git`.
- Quyền đọc repo `mzavn/mk-studio` (repo đang **private**) và [GitHub CLI](https://cli.github.com) đã đăng nhập (`gh auth status`).
- Một coding agent hỗ trợ skill (Claude Code, omp, Codex…).

## Cài đặt

Hướng dẫn từng bước (đưa cho agent tự cài được): [INSTALL.md](INSTALL.md).

```bash
gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global
```

Lệnh chép `mk-star` vào `~/.claude/skills/mk-star` và `~/.agents/skills/mk-star`. Các cách khác:

```bash
bash ~/.mk-studio/install.sh --project ~/code/my-blog               # vào một project: .claude/skills/mk-star
bash ~/.mk-studio/install.sh --project . --agents-dir               # thêm .agents/skills/mk-star (vd Codex)
bash ~/.mk-studio/install.sh --global --skill <tên>                 # skill khác của bộ, theo tên thư mục (mặc định mk-star)
```

- Luôn **chép**, không symlink; chạy lại bao nhiêu lần cũng được, script in phiên bản cũ → mới.
- Chỉ chép thư mục skill — không tạo cấu hình, không đụng `AGENTS.md`/`CLAUDE.md`.
- Thư mục skill cùng tên mà không do `install.sh` tạo thì bị từ chối (có thể là skill của công cụ khác), trừ `--force`. Bản trong project có file sửa tay cũng bị từ chối, kèm danh sách file.

## Cập nhật

Skill phát hành theo bản (`vX.Y.Z`, xem [CHANGELOG.md](CHANGELOG.md)); nhánh `main` chỉ chứa bản đã phát hành.

```bash
bash ~/.mk-studio/install.sh --update                          # bản cài chung: mọi skill đã cài bằng install.sh
bash ~/.mk-studio/install.sh --update --global --project .     # đứng trong project: cả hai
```

Clone ở chỗ khác thì thay `~/.mk-studio` bằng đường dẫn đó (ghi trong `~/.claude/skills/mk-star/.mk-studio-source`).

## Gỡ cài đặt

```bash
bash ~/.mk-studio/install.sh --uninstall --global
bash ~/.mk-studio/install.sh --uninstall --project ~/code/my-blog
```

Gỡ `star` không đụng bài nhật ký trong `~/nhat-ky-star/`.

## Cấu trúc repo

```
mk-studio/
├── install.sh
├── INSTALL.md
├── CHANGELOG.md
├── LICENSE
├── README.md
├── tests/                       test cho install.sh (không chép vào skill)
└── skills/
    ├── mk-star/
    │   ├── SKILL.md             điểm vào: chọn loại, cách dẫn, định dạng bài, an toàn
    │   ├── references/          tong-quan, loai-i … loai-v, case-mau, kho-case
    │   ├── assets/mau/          mẫu bài từng loại
    │   └── scripts/             progress.py, tests/
    └── mk-exec-review/
        ├── SKILL.md             luồng: gom ngữ cảnh → hỏi → agent riêng phản biện → duyệt → sửa
        ├── references/          hoi-dong, giong-ai, thuat-ngu, seo-geo-aeo
        ├── assets/              goi-phan-bien (giao việc cho agent riêng), mau-bao-cao
        └── scripts/             scan.py, check_report.py, tests/
```

## Đóng góp

- Gửi vào nhánh `dev` (`main` chỉ chứa bản đã phát hành). Commit theo Conventional Commits, scope là tên skill (`feat(mk-star): …`); loại commit quyết định số phiên bản (CHANGELOG.md) — đổi chữ trong `skills/` mà người dùng thấy khác là `feat`/`fix`, không phải `docs`.
- Scripts chỉ thư viện chuẩn, đầu ra tất định; chạy `python3 -m unittest discover -s skills/<tên>/scripts/tests` cho từng skill và `python3 -m unittest discover -s tests` (installer).
- `SKILL.md` và mỗi reference dưới 300 dòng; ví dụ dùng dữ liệu giả.
- Ghi thay đổi vào mục `## Chưa phát hành` của CHANGELOG.md bằng lời người dùng.

## Ghi công

Skill `mk:star` tổng hợp từ tài liệu **X3 Năng Suất** ([minhvq.notion.site](https://minhvq.notion.site)) — "Video tự học STAR bậc cao" và "Thực hành Giải quyết vấn đề từ A-Z"; phần do người tổng hợp soạn thêm ghi trong `skills/star/references/tong-quan.md` mục Nguồn gốc. Phát hành theo đồng ý của chủ nội dung.

## Giấy phép

MIT — xem [LICENSE](LICENSE).

---

## English

**mk-studio** is a set of content skills for AI coding agents — writing, video, marketing, packaging personal know-how. Its programming counterpart is [mk-lab](https://github.com/mzavn/mk-lab). The first skill, **mk:star**, is a Vietnamese STAR journaling coach: five journal types (daily diary, A–Z problem solving with a short variant, packing a success, creating the future, mentoring), the full question bank with basic/deep tiers, four worked cases and 28 practice cases, and `progress.py` that counts complete entries against milestones. Entries are plain markdown files in `~/nhat-ky-star/`. **mk:exec-review** has a separate sub-agent critique a Vietnamese article as a C-level panel reading through your customer persona — AI-sounding prose, terminology consistency, SEO/GEO/AEO — and edits the file only for the suggestion codes you approve, keeping your voice.

The repo is private for now. Install with `gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global` (copies to `~/.claude/skills/mk-star` and `~/.agents/skills/mk-star`; `--project <dir>` for one repo, `--skill <name>` for another skill, `--update` to pull the latest release and refresh every skill it installed, `--uninstall` to remove). Requirements: bash, python3 ≥ 3.8, git, an authenticated `gh`. Content of `star` is compiled from X3 Năng Suất material (minhvq.notion.site) with the owner's consent. License: MIT.
