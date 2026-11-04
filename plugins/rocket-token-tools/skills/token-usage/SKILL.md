---
name: token-usage
description: Ghi lại số token đã dùng theo môi trường (web, desktop, mobile, Claude Code, API) và theo mục đích (slides, docs, email, code, dữ liệu, nghiên cứu, video/ảnh…), xuất các dòng mã TU1 để dán vào trang Bản đồ token 3D. Claude Code dùng số đo thật từ log phiên và có thể tự đồng bộ hằng ngày; chat trên web/desktop/mobile dùng số ước lượng. Dùng khi người dùng gõ /token-usage, "/token-usage sync", "/token-usage setup", "ghi token", "log usage", "tuần này tôi dùng bao nhiêu token", "token dùng cho việc gì".
---

# Token usage

Mục tiêu: mỗi người tự theo dõi mình dùng bao nhiêu token, **ở môi trường nào** và **cho mục đích gì**, rồi xem tất cả trên trang **Bản đồ token 3D**:

TOKEN_MAP = https://claude.ai/artifact/Ws74MHuN9cNXxKLnJieQvH

## Tự động: `/token-usage setup` (cài 1 lần) và `/token-usage sync`

Chỉ chạy được trong Claude Code trên app Claude desktop (cần công cụ `ArtifactData` để ghi vào trang, và công cụ tác vụ định kỳ để tự chạy).

**`/token-usage sync`**, không hỏi lại người dùng:
1. Đọc dữ liệu hiện có: `ArtifactData` `list`, `url` = TOKEN_MAP, `collection` = `data/users/me`, `out_dir` = một thư mục tạm mới (trong scratchpad nếu có). Ghi lại `version` của từng tài liệu tháng (`YYYY-MM`) trong kết quả.
2. Chạy `python3 scripts/claude_code_usage.py --days 3 --sync <thư mục tạm>`. Script gộp các phiên Claude Code mới hoặc đã tăng thêm token vào tài liệu tháng, giữ nguyên mục đích người dùng đã sửa, và ghi file vào `<thư mục tạm>/merged/YYYY-MM.json`.
3. Với mỗi file trong `merged/`: `ArtifactData` `set`, `collection` = `data/users/me`, `doc_id` = `YYYY-MM`, `file_path` = file đó, `if_version` = version đọc ở bước 1 (bỏ trống nếu tháng đó chưa có). Nếu bị từ chối vì version đã đổi: làm lại từ bước 1 một lần.
4. Báo một dòng: số phiên đã thêm hoặc cập nhật, tổng token 3 ngày qua. "Nothing new to sync" thì báo là không có gì mới.

**`/token-usage setup`**: tạo một tác vụ định kỳ (scheduled task, id `rocket-token-sync`) chạy mỗi ngày lúc 18:00 giờ máy, với lời nhắc tự đủ thông tin: thực hiện các bước `/token-usage sync` ở trên, rồi các bước `/token-pattern sync` trong skill token-pattern (đường dẫn script tuyệt đối, URL hai trang, collection `data/users/me`). Sau đó chạy cả hai lệnh sync một lần ngay để kiểm tra. Báo cho người dùng tên tác vụ, rằng tác vụ chỉ chạy khi app Claude đang mở (lỡ giờ thì chạy ở lần mở app sau), và cách tắt nó.

Chat trên web, desktop (tab chat) và điện thoại **không tự đồng bộ được**: các app này không cho công cụ nào đọc số token của từng cuộc chat. Với những cuộc chat đó, dùng Cách 2 bên dưới khi cuộc chat đáng ghi lại, hoặc xem phần trăm giới hạn ở Settings → Usage.

## Mã TU1 (định dạng chung)

Mỗi dòng là một phiên hoặc một cuộc chat:

```
TU1|date=2026-11-03|env=code|purpose=slides|tokens=184230|cached=920000|src=do|sid=<id phiên, chỉ Claude Code>|note=deck Q4 cho sales
```

| Trường | Giá trị |
|---|---|
| `env` | `web` (claude.ai trên trình duyệt), `desktop` (app Claude, tab chat), `mobile`, `code` (Claude Code: CLI, IDE, tab Code của desktop), `api` (API / Console / SDK), `other` (Claude trong Chrome, Excel, Slack…) |
| `purpose` | `slides`, `docs`, `email`, `code`, `data`, `research`, `media` (video, ảnh, giọng đọc), `qa` (hỏi đáp nhanh), `other` |
| `tokens` | Token tính phí chính: đầu vào mới + ghi cache + đầu ra. |
| `cached` | Token đọc lại từ cache (rẻ hơn nhiều). `0` nếu không biết. |
| `src` | `do` = đo thật, `est` = ước lượng. |
| `note` | Mô tả ngắn, không chứa dấu `|`. |

Luôn đặt các dòng TU1 trong một khối code để người dùng copy một lần.

## Cách 1: Đang ở Claude Code (có quyền chạy lệnh trên máy)

1. Chạy `python3 scripts/claude_code_usage.py --days 7 --json` (đổi `--days` theo yêu cầu của người dùng).
2. Script đọc `~/.claude/projects/**/*.jsonl` và cộng trường `usage` của từng câu trả lời. Đây là **số đo thật** (`src=do`).
3. Đọc trường `prompt` và `project` của từng phiên rồi chọn lại `purpose` cho đúng; `purpose_guess` chỉ là gợi ý theo từ khóa. Viết `note` ngắn gọn bằng tiếng Việt.
4. Xuất danh sách TU1, kèm một bảng tóm tắt: tổng token theo mục đích, 3 phiên tốn nhất và một nhận xét ngắn (ví dụ: "một phiên chiếm 40% tổng token tuần, vì kéo dài cả ngày, nên chia nhỏ hoặc dùng /compact").

Không gửi nội dung log đi đâu. Chỉ đưa ra mã TU1 và phần tóm tắt.

## Cách 2: Đang chat trên web, desktop hoặc mobile

Các app này không hiện số token theo từng chat, nên **ước lượng** (`src=est`):

1. Đọc lại cuộc chat hiện tại (không tính tin gọi skill). Với mỗi lượt, ước lượng số ký tự tin của người dùng và câu trả lời của bạn.
2. Đếm số trang tài liệu đính kèm, số ảnh và ước lượng token kết quả công cụ (mỗi lần tìm web ~3.000–5.000; mỗi lần tạo file docx/pptx bằng code ~3.000–10.000).
3. Nếu chạy được code: `python3 scripts/estimate_chat.py --turns "u1:r1,u2:r2,..." --lang vi --pages N --images M --tool-tokens T`. Nếu không, tính tay theo cùng logic: mỗi lượt đọc lại toàn bộ lịch sử + file đính kèm; tiếng Việt ~2,5 ký tự/token, tiếng Anh ~4, một trang ~2.000 token, một ảnh ~1.600 token.
4. Hỏi người dùng đang dùng `web`, `desktop` hay `mobile` nếu không rõ. Chọn `purpose` theo việc chính của cuộc chat.
5. Xuất 1 dòng TU1 với `cached=0|src=est`, và nhắc rằng đây là ước lượng (không gồm hướng dẫn hệ thống ẩn; cache có thể làm chi phí thật thấp hơn).

## Cách 3: API

Mỗi phản hồi API có trường `usage`. Hướng dẫn người dùng lấy tổng theo ngày ở trang Usage của Claude Console, rồi tạo dòng TU1 với `env=api|src=do` cho từng mục đích họ cho biết.

## Bước cuối

Nhắc người dùng dán các dòng TU1 vào ô **Nhập mã TU1** trên trang Bản đồ token 3D. Trang tự gom theo môi trường, mục đích và ngày.

Không bịa số. Không đủ thông tin thì hỏi lại hoặc ghi rõ là ước lượng.
