---
name: token-pattern
description: Chấm "điểm token" ước lượng theo pattern làm việc (số lượt, số lần sửa, file đính kèm, loại việc, model). Trong Claude Code, "/token-pattern sync" tự chấm mọi phiên gần đây từ log và ghi thẳng vào Nhật ký tiết kiệm; với chat web/desktop/mobile thì chấm phiên hiện tại và trả về mã TP1 để dán. Dùng khi người dùng gõ /token-pattern, "/token-pattern sync", "chấm điểm token", "phiên này tốn bao nhiêu token", "so với tuần trước", hoặc dán một mã bắt đầu bằng TP1|.
---

# Token pattern

Chấm điểm phiên chat hiện tại theo pattern, để nhân viên so cùng một loại việc giữa tuần này và tuần trước. Đây là **điểm ước lượng tương đối, không phải số token thật**. Luôn nói rõ điều này với người dùng.

LESSON = https://claude.ai/artifact/EBDXY3zeyzdM25ueUcdcp1 (bài giảng Token, phần "Nhật ký tiết kiệm")

## Tự động trong Claude Code: `/token-pattern sync`

Khi đang ở Claude Code và có công cụ `ArtifactData`, chấm điểm mọi phiên Claude Code gần đây rồi ghi thẳng vào Nhật ký tiết kiệm, không cần dán mã. Không hỏi lại người dùng:

1. `ArtifactData` `list`, `url` = LESSON, `collection` = `data/users/me`, `out_dir` = một thư mục tạm mới. Ghi lại `version` của từng tài liệu.
2. Chạy `python3 scripts/cc_patterns.py --days 14 --sync <thư mục tạm>`. Script đọc log phiên trong `~/.claude/projects`, dựng lại pattern từng phiên (số tin, số lần sửa, ảnh, model, có tìm web không, độ dài trả lời, loại việc), chấm điểm bằng `scripts/score.py`, và ghi các phiên mới hoặc đã thay đổi vào `<thư mục tạm>/merged/<id>.json`. Loại việc người dùng đã sửa trên trang được giữ nguyên.
3. Ghi bằng `ArtifactData` `batch` (tối đa 50 mục mỗi lần): mỗi file là `{op: "set", collection: "data/users/me", doc_id: <tên file bỏ .json>, file_path: file đó, if_version: version ở bước 1}`; bỏ `if_version` với phiên chưa có. Bị từ chối vì version đổi thì làm lại từ bước 1 một lần.
4. Nếu script báo có dòng cũ hơn 60 ngày: xóa các id trong `<thư mục tạm>/stale.txt` bằng `ArtifactData` `batch` với `op: "delete"` và `if_version` đọc ở bước 1. Chỉ xóa đúng các id đó.
5. Báo một dòng: số phiên đã thêm hoặc cập nhật. Nếu có đủ dữ liệu, thêm một câu so sánh điểm trung bình 7 ngày qua với 7 ngày trước đó theo loại việc.

`/token-usage setup` tạo tác vụ hằng ngày chạy cả `/token-usage sync` lẫn `/token-pattern sync`.

Chat trên web, desktop (tab chat) và điện thoại không có log để đọc, nên vẫn dùng cách thủ công bên dưới.

## Cách thủ công: chấm phiên chat hiện tại

## Bước 1: Đọc lại cuộc chat hiện tại và điền 10 trường

Dựa vào chính cuộc chat này (không tính tin nhắn gọi skill):

| Trường | Cách điền |
|---|---|
| `task` | Một trong: `qa` (hỏi đáp nhanh), `email` (email, văn bản ngắn), `summary` (tóm tắt tài liệu), `docs` (tạo file Docs/Word), `excel` (phân tích Excel, dữ liệu), `slides` (tạo slides), `research` (nghiên cứu web sâu). Chọn việc chiếm nhiều công sức nhất. |
| `turns` | Số tin nhắn người dùng đã gửi cho việc này. |
| `fix` | Trong số đó, bao nhiêu tin là để sửa, chỉnh, "làm lại", "không phải vậy". |
| `pages` | Tổng số trang tài liệu đính kèm (PDF, Word; file Excel tính ~1 trang mỗi 50 dòng). |
| `img` | Số ảnh, ảnh chụp màn hình đính kèm. |
| `len` | Độ dài trung bình câu trả lời của bạn: `ngan` (< 150 chữ), `vua`, `dai` (> 600 chữ hoặc có file/code dài). |
| `model` | `nhe` (Haiku), `vua` (Sonnet), `manh` (Opus hoặc có bật suy nghĩ mở rộng). Không chắc thì hỏi người dùng một câu. |
| `web` | `1` nếu có dùng tìm kiếm web, ngược lại `0`. |
| `old` | Số lượt chat trước đó thuộc chủ đề khác mà cuộc chat này vẫn mang theo. `0` nếu chat mới mở cho việc này. |
| `date` | Ngày hôm nay, dạng YYYY-MM-DD. |

## Bước 2: Tính điểm

Nếu có thể chạy code, chạy:

```bash
python3 scripts/score.py "TP1|task=...|turns=...|fix=...|pages=...|img=...|len=...|model=...|web=...|old=..."
```

Nếu người dùng dán thêm mã TP1 của tuần trước cho cùng loại việc, truyền nó làm đối số thứ hai để so sánh.

Nếu không chạy được code, tính tay theo đúng công thức trong `scripts/score.py`:
`n = turns`, `tri = n(n+1)/2`, `w` = trọng số model (nhe 0.35, vua 1, manh 1.7).
Tổng = w × [ n·old·900 + n·(pages·1500 + img·1600) + 200·tri + A·len·tri + (T + web·4000)·tri ], với A, T theo bảng TASKS trong script (len: ngan 0.5, vua 1, dai 2; web không cộng thêm khi task là research). Điểm = Tổng / 1000, làm tròn 1 chữ số.

## Bước 3: Trả lời người dùng bằng tiếng Việt, theo mẫu

```
Điểm token phiên này: <điểm> (ước lượng tương đối, không phải số token thật)
Loại việc: <tên> · <turns> lượt, <fix> lần sửa, <pages> trang, <img> ảnh, model <model>

Phần tốn nhiều nhất: <1–2 phần lớn nhất theo % từ script>

3 cách làm gọn hơn lần sau:
1. ...
2. ...
3. ...

Mã để dán vào Nhật ký tiết kiệm:
TP1|date=YYYY-MM-DD|task=...|turns=...|fix=...|pages=...|img=...|len=...|model=...|web=...|old=...
```

Đặt mã TP1 trong một khối code riêng để dễ copy. Gợi ý phải cụ thể cho phiên này, ví dụ:
- `fix` ≥ 2: lần sau bấm Edit sửa tin gốc thay vì gửi tin sửa mới; viết yêu cầu đủ ngay từ đầu.
- `old` > 0: mở chat mới cho mỗi việc, hoặc tóm tắt rồi sang chat mới.
- `pages` lớn: chỉ gửi trang hoặc đoạn cần thiết.
- `slides` hoặc `docs` có nhiều lượt: chốt dàn ý bằng chữ trước, tạo file một lần ở cuối, gom sửa đổi vào một tin.
- `model=manh` cho việc nhẹ: dùng model nhẹ hơn.
- `len=dai` mà không cần: yêu cầu độ dài và định dạng cụ thể.

## So với tuần trước

Nếu người dùng muốn so tuần này với tuần trước, có hai cách:
1. Họ dán mã TP1 của phiên tuần trước (cùng loại việc) → chạy script với hai mã và nêu % tiết kiệm cùng các trường đã thay đổi.
2. Họ dán mã vào trang **Nhật ký tiết kiệm** (phần 12 của bài giảng Token), trang tự so trung bình 7 ngày qua với 7 ngày trước đó theo từng loại việc.

Không bịa số liệu tuần trước. Nếu không có mã cũ, nói rõ chỉ chấm được phiên hiện tại.
