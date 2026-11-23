# Chuẩn bị dev → main — 23/11/2026

Được yêu cầu triển khai R1–R3; không bao gồm merge dev vào main hoặc deploy.
Baseline đầu: origin/dev 41bca1c; main 9db2f6f. Dùng clone sạch, SQLite/ảnh tạm, không .env/production/model thật.
Mỗi nhánh tạo từ dev mới nhất sau PR trước đã squash merge; PR vào dev, tổng additions + deletions <500.
Thân PR copy mẫu tương ứng, điền ___ và Closes # bằng issue thật. Không sửa assertion hành vi cũ để che lỗi.

| Task | Nhánh | Phạm vi / nghiệm thu |
|---|---|---|
| R1 | codex/ff-release-01-main-ci | CI cho pull_request/push cả dev và main; test cấu hình đỏ trước sửa, xanh sau sửa. |
| R2a | codex/ff-release-02a-browser-setup | Sửa setup/điều hướng fixture dùng chung và saved-library, đưa suite vào CI; giữ kiểm tra nguồn, restore, ảnh, focus, không gọi AI. |
| R2b | codex/ff-release-02b-onboarding | TẠM HOÃN theo xác nhận người dùng: giữ nguyên mọi kỳ vọng cũ, kể cả 7 bước; không đổi metadata hoặc assertion của suite. |
| R2c | codex/ff-release-02c-screenplay-context | Khôi phục suite ngữ cảnh: mở đúng stage; giữ toàn bộ assertion buffer/nguồn/ảnh/lưu. |
| R3 | codex/ff-release-03-sqlite-recovery | DB sinh từ main cũ đọc/sửa được; backup/restore DB + ảnh trong thư mục tạm; integrity_check, restart, không mất bản/ảnh. |

R2 tách thành ba PR để tránh một diff lớn và xác nhận từng suite độc lập.
Nếu phải tách thêm: bổ sung nhánh/mẫu trước khi mở PR. Không bỏ ca cũ hoặc nới assertion để đạt trần dòng.
Contract giao diện hiện tại có 6 bước; người dùng yêu cầu giữ suite hướng dẫn 7 bước và để chờ xử lý riêng (23/11/2026).

Trước mỗi PR, từ frontend:
`pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check`
PR backend chạy thêm `PYTHON_DOTENV_DISABLED=1 python -m pytest -q` trong backend bằng venv riêng.
Browser chạy production build local và provider giả; lưu baseline thất bại và kết quả sau sửa. Test tương thích vốn xanh thì ghi baseline PASS, không tạo lỗi giả.
CI phải xanh trên đúng head trước squash merge vào dev. main không thay đổi trong R1–R3.

## Kết quả triển khai
- R1: #104 đã squash merge; CI nhận PR/push dev và main.
- R2a: #106 đã squash merge; saved-library xanh ở 4 kích thước và CI Linux, giữ assertion cũ.
- R2b: tạm hoãn theo yêu cầu người dùng; giữ nguyên mọi kỳ vọng, kể cả 7 bước.
- R2c: #108 đã squash merge; screenplay-context xanh local/CI, giữ assertion cũ; chỉ sửa cách mở stage/selector.
- R3: baseline hai ca tương thích/recovery đã PASS; bổ sung fixture main thật, hồi quy và runbook, không đổi runtime. Xem docs/testing/sqlite-recovery-2026-11-23.md.
