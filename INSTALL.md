# Cài mk-studio (skill star)

Hướng dẫn ngắn cho cả người và agent. Repo đang **private**: cần tài khoản GitHub có quyền đọc `mzavn/mk-studio`.

## Agent: làm theo thứ tự

1. **Kiểm điều kiện** — cần `bash`, `python3` ≥ 3.8, `git`, `gh` đã đăng nhập:
   ```bash
   bash --version | head -1; python3 --version; git --version; gh auth status
   ```
   Thiếu công cụ → báo người dùng, dừng. `gh auth status` báo chưa đăng nhập → nhờ người dùng chạy `gh auth login` (agent không tự nhập mật khẩu/token).

2. **Đã cài chưa?**
   ```bash
   grep -m1 -H 'version:' ~/.claude/skills/star/SKILL.md ~/.agents/skills/star/SKILL.md 2>/dev/null
   cat ~/.claude/skills/star/.mk-studio-source 2>/dev/null
   ```
   Có `.mk-studio-source` → bước 3 dùng `bash <đường dẫn đó>/install.sh --update`.

3. **Cài chung cho máy** (`~/.claude/skills/star` và `~/.agents/skills/star`):
   ```bash
   gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global
   ```
   `~/.mk-studio` đã có → chỉ chạy `bash ~/.mk-studio/install.sh --update`.

4. **Kiểm kết quả** — chạy lại lệnh ở bước 2: hai bản cùng phiên bản.

5. **Báo người dùng**: phiên bản đã cài; bài nhật ký lưu ở `~/nhat-ky-star/`, không cài vào repo, không cần `AGENTS.md`. Câu để bắt đầu: "viết nhật ký ngày".

## Cập nhật

```bash
bash ~/.mk-studio/install.sh --update                        # bản cài chung: mọi skill đã cài bằng install.sh
bash ~/.mk-studio/install.sh --update --global --project .   # đứng trong repo: cả hai
```

`--update` chỉ nhận bản đã phát hành ([CHANGELOG.md](CHANGELOG.md)). Bản tăng số đầu (X) cần làm thêm bước — CHANGELOG ghi rõ, đọc trước khi cập nhật.

## Gặp lỗi

| Thông báo | Làm gì |
|---|---|
| `Could not resolve to a Repository` / `cannot clone` | Tài khoản `gh` chưa có quyền repo private → người dùng xin quyền chủ repo, hoặc `gh auth login` đúng tài khoản |
| `was not installed by install.sh` | Đã có thư mục skill cùng tên (vd `~/.claude/skills/star`) không do installer tạo — có thể là skill khác. Hỏi người dùng; giữ thì đổi tên thư mục đó, bỏ thì chạy lại với `--force` |
| `has edits not made by install.sh` | Có người sửa tay file trong skill (đã liệt kê). Giữ bản sao nếu cần, rồi chạy lại với `--force` |
| `cannot fast-forward ~/.mk-studio` | Thư mục clone có sửa đổi riêng. Không cần giữ → `rm -rf ~/.mk-studio` rồi làm lại bước 3 |
| `no skill named '…'` | Tên sau `--skill` không có trong `skills/` (thông báo kèm danh sách) |
| `is a symlink` | Thư mục đích là đường tắt; thay bằng thư mục thật rồi chạy lại |

## Gỡ

```bash
bash ~/.mk-studio/install.sh --uninstall --global              # ~/nhat-ky-star/ giữ nguyên
bash ~/.mk-studio/install.sh --uninstall --project .
```
