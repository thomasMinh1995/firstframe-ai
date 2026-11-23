# PR 1 — Nền kiểm thử

Làm bộ lệnh kiểm tra frontend chạy không tương tác; cấu hình lint và CI tương ứng; chặn tự nạp dotenv khi kiểm thử.

- Nhánh: `codex/ff-sb-01-isolated-checks`; base: `dev`; merge: **squash**.
- Phụ thuộc: Không; đã chốt SQLite tạm cách ly, không dùng `.env` hoặc `backend/.data`.
- Phạm vi/dự toán: tối đa 400 dòng; tổng additions + deletions thực: ___ (<500, gồm test/docs/lockfile).
- Hoàn tất khi: Bộ lệnh bắt buộc chạy được trong frontend của checkout sạch; test/backend không nạp .env; không cài hoặc đổi DB ngầm.
- RED bắt buộc theo phạm vi: Test mới chứng minh tiến trình kiểm thử từ chối hoặc bỏ qua .env; xác nhận lint hiện tại lỗi/đòi tương tác nếu có, rồi ghi kết quả.
- Bằng chứng RED trên dev (SHA/lệnh/lỗi hoặc N/A có lý do): ___
- GREEN cùng test/assertions (SHA/lệnh/kết quả): ___
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check` trong frontend: ___
- Backend/browser/PDF/model evidence liên quan và giới hạn: ___
- Môi trường cách ly, không dùng .env/production; quyết định DB áp dụng: ___
- Khác biệt người dùng thấy và cách khôi phục khi lỗi: ___

Closes #___
