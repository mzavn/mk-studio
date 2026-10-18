# mk-studio

Bộ skill **content** cho AI agent (Claude Code, omp và các agent đọc thư mục skill chuẩn): viết, video, marketing, đóng gói giá trị bản thân. Mỗi skill độc lập, cài riêng từng cái.

Hiện có:

- **`star`** — hệ nhật ký STAR 5 loại: agent dẫn bạn viết nhật ký từng câu, lưu bài ở máy, đếm tiến độ. Cài mặc định.

Bộ skill lập trình đi kèm (specs, dev, test, bảo mật) là **[mk-lab](https://github.com/mzavn/mk-lab)**.

*English summary at the end.*

## star — nhật ký STAR

`star` biến một lời than vãn thành quyết định, kế hoạch và bài học đóng gói được. Bạn kể một câu ("sáng nay cãi nhau với vợ về chuyện công ty"), agent đề xuất loại nhật ký hợp, hỏi từng câu theo mẫu và ghi nguyên văn câu trả lời vào một file markdown ở `~/nhat-ky-star/`.

| Loại | Viết khi |
|---|---|
| I · Daily Diary | trong ngày hoặc cuối ngày — mỗi ngày cải tiến 1% |
| II · Problem Solving | gặp thất bại, vướng mắc — bản đầy đủ 8 bước A–Z hoặc "viết nhanh" |
| III · Packing Value | sau một thành công — thành công thức chuyển giao được |
| IV · Creating Future | trước sự kiện, dự án, cuộc gặp quan trọng |
| V · Mentoring | trước buổi bán hàng, đào tạo, 1-1, coaching |

Kèm bộ câu hỏi cơ bản/chuyên sâu cho từng loại, 4 case giải mẫu và 28 case luyện tập, 8 dạng tài sản đóng gói, và `progress.py` đếm bài trọn vẹn theo cột mốc 28 / 300 / 1000 / 10000, nhắc One Action chưa làm và kết quả đến hạn ghi. Nhật ký là dữ liệu riêng: file chỉ ở máy bạn (agent cảnh báo nếu thư mục nằm trong git); nội dung trò chuyện vẫn đi qua nhà cung cấp AI của agent.

Cài xong, nói với agent: "viết nhật ký ngày", "viết nhật ký giải quyết vấn đề", "luyện case 05", "tiến độ nhật ký".

## Yêu cầu

- `bash` (macOS hoặc Linux), `python3` ≥ 3.8, `git`.
- Quyền đọc repo `mzavn/mk-studio` (repo đang **private**) và [GitHub CLI](https://cli.github.com) đã đăng nhập (`gh auth status`).
- Một coding agent hỗ trợ skill (Claude Code, omp, Codex…).

## Cài đặt

Hướng dẫn từng bước (đưa cho agent tự cài được): [INSTALL.md](INSTALL.md).

```bash
gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global
```

Lệnh chép `star` vào `~/.claude/skills/star` và `~/.agents/skills/star`. Các cách khác:

```bash
bash ~/.mk-studio/install.sh --project ~/code/my-blog               # vào một project: .claude/skills/star
bash ~/.mk-studio/install.sh --project . --agents-dir               # thêm .agents/skills/star (vd Codex)
bash ~/.mk-studio/install.sh --global --skill <tên>                 # skill khác của bộ (mặc định star)
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

Clone ở chỗ khác thì thay `~/.mk-studio` bằng đường dẫn đó (ghi trong `~/.claude/skills/star/.mk-studio-source`).

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
    └── star/
        ├── SKILL.md             điểm vào: chọn loại, cách dẫn, định dạng bài, an toàn
        ├── references/          tong-quan, loai-i … loai-v, case-mau, kho-case
        ├── assets/mau/          mẫu bài từng loại
        └── scripts/             progress.py, tests/
```

## Đóng góp

- Gửi vào nhánh `dev` (`main` chỉ chứa bản đã phát hành). Commit theo Conventional Commits, scope là tên skill (`feat(star): …`); loại commit quyết định số phiên bản (CHANGELOG.md) — đổi chữ trong `skills/` mà người dùng thấy khác là `feat`/`fix`, không phải `docs`.
- Scripts chỉ thư viện chuẩn, đầu ra tất định; chạy `python3 -m unittest discover -s skills/star/scripts/tests` và `python3 -m unittest discover -s tests` (installer).
- `SKILL.md` và mỗi reference dưới 300 dòng; ví dụ dùng dữ liệu giả.
- Ghi thay đổi vào mục `## Chưa phát hành` của CHANGELOG.md bằng lời người dùng.

## Ghi công

Skill `star` tổng hợp từ tài liệu **X3 Năng Suất** ([minhvq.notion.site](https://minhvq.notion.site)) — "Video tự học STAR bậc cao" và "Thực hành Giải quyết vấn đề từ A-Z"; phần do người tổng hợp soạn thêm ghi trong `skills/star/references/tong-quan.md` mục Nguồn gốc. Phát hành theo đồng ý của chủ nội dung.

## Giấy phép

MIT — xem [LICENSE](LICENSE).

---

## English

**mk-studio** is a set of content skills for AI coding agents — writing, video, marketing, packaging personal know-how. Its programming counterpart is [mk-lab](https://github.com/mzavn/mk-lab). The first skill, **star**, is a Vietnamese STAR journaling coach: five journal types (daily diary, A–Z problem solving with a short variant, packing a success, creating the future, mentoring), the full question bank with basic/deep tiers, four worked cases and 28 practice cases, and `progress.py` that counts complete entries against milestones. Entries are plain markdown files in `~/nhat-ky-star/`.

The repo is private for now. Install with `gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global` (copies to `~/.claude/skills/star` and `~/.agents/skills/star`; `--project <dir>` for one repo, `--skill <name>` for another skill, `--update` to pull the latest release and refresh every skill it installed, `--uninstall` to remove). Requirements: bash, python3 ≥ 3.8, git, an authenticated `gh`. Content of `star` is compiled from X3 Năng Suất material (minhvq.notion.site) with the owner's consent. License: MIT.
