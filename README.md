# rocket-token-tools

Công cụ nội bộ Rocket Group giúp mỗi người tự theo dõi mình dùng bao nhiêu token với Claude, ở môi trường nào, cho việc gì, và tuần này có làm việc tiết kiệm hơn tuần trước không.

Gồm hai skill:

| Skill | Làm gì | Ghi vào |
|---|---|---|
| `token-usage` | Số token **đo thật** của từng phiên Claude Code (đọc log trên máy), và số ước lượng cho chat web, desktop, điện thoại | [Bản đồ token 3D](https://claude.ai/artifact/Ws74MHuN9cNXxKLnJieQvH) |
| `token-pattern` | **Điểm tiết kiệm** theo cách làm việc: số tin, số lần sửa, file đính kèm, model. So tuần này với tuần trước | [Bài giảng Token, phần Nhật ký tiết kiệm](https://claude.ai/artifact/EBDXY3zeyzdM25ueUcdcp1#nhatky) |

Dữ liệu của mỗi người lưu riêng trong tài khoản claude.ai của người đó. Người khác, kể cả người quản lý trang, không xem được.

## Cài cho Claude Code (khuyên dùng, tự động)

Cài một lần:

```bash
claude plugin marketplace add <github-org>/rocket-token-tools
```

```bash
claude plugin install rocket-token-tools@rocketgroup-claude
```

Hoặc trong một phiên Claude Code: `/plugin marketplace add <github-org>/rocket-token-tools`, rồi `/plugin install rocket-token-tools@rocketgroup-claude`.

Sau đó, trong Claude Code trên app Claude desktop, gõ:

```
/rocket-token-tools:token-usage setup
```

Lệnh này tạo tác vụ chạy mỗi ngày lúc 18:00. Mỗi lần chạy, Claude đọc log phiên Claude Code trên máy, ghi số token thật lên Bản đồ token, và chấm điểm từng phiên vào Nhật ký tiết kiệm. Tác vụ chỉ chạy khi app Claude đang mở; nếu lỡ giờ, nó chạy ở lần mở app sau.

Muốn đồng bộ ngay: `/rocket-token-tools:token-usage sync` và `/rocket-token-tools:token-pattern sync`.

> Repo private: mỗi người cần có quyền đọc repo, và máy đã đăng nhập git với GitHub (ví dụ qua `gh auth login`).

## Cài cho chat trên claude.ai (web, desktop, điện thoại)

Tải hai file trong thư mục [`dist/`](dist/), rồi vào **Settings → Capabilities → Skills → Upload skill** cho từng file.

Các app chat không cho công cụ nào đọc số token của từng cuộc chat, nên ở đây **chưa tự động được**. Cuối một cuộc chat đáng ghi lại:

- gõ `/token-pattern`: Claude chấm điểm phiên đó và trả về một mã `TP1|…` để dán vào Nhật ký tiết kiệm;
- gõ `/token-usage`: Claude ước lượng số token và trả về một mã `TU1|…` để dán vào Bản đồ token.

## Điểm token là gì

Điểm token là **ước lượng tương đối** dựa trên cách làm việc, không phải số token thật. Nó dùng để so cùng một loại việc theo thời gian. Công thức nằm trong [`score.py`](plugins/rocket-token-tools/skills/token-pattern/scripts/score.py) và giống hệt công thức trên trang Nhật ký tiết kiệm.

Số token thật (chỉ có với Claude Code và API) nằm ở skill `token-usage` và Bản đồ token.

## Cập nhật bản mới

```bash
claude plugin marketplace update rocketgroup-claude
```

## Cấu trúc repo

```
.claude-plugin/marketplace.json          danh mục plugin của Rocket
plugins/rocket-token-tools/
  .claude-plugin/plugin.json
  skills/token-usage/                     số token thật + ước lượng → Bản đồ token
  skills/token-pattern/                   điểm tiết kiệm → Nhật ký tiết kiệm
dist/                                     file zip để upload lên claude.ai
build.sh                                  tạo lại các file zip trong dist/
```
