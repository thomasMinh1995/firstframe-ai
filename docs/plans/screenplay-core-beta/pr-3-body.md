# PR 3 — BK-02

Đo baseline bằng runner hiện có; chỉ bổ sung adapter đầu vào nhỏ nếu thật sự thiếu.

- Nhánh: `codex/ff-sb-03-quality-baseline`; base: `dev`; merge: **squash**.
- Phụ thuộc: PR 2; cấu hình và ngân sách model được chốt trước chạy.
- Phạm vi/dự toán: tối đa 300 dòng; tổng additions + deletions thực: ___ (<500, gồm test/docs/lockfile).
- Hoàn tất khi: Ghi SHA, model/digest, prompt, ngân sách, kết quả cả lỗi; chọn tối đa hai nhóm lỗi ưu tiên. Raw evidence lưu bền vững ngoài diff, có tham chiếu kiểm chứng.
- RED bắt buộc theo phạm vi: Nếu có sửa runner: test mới cho input/đường gọi chưa hỗ trợ phải đỏ trên dev. Nếu chỉ báo cáo: N/A, giữ cả ca baseline chưa đạt.
- Bằng chứng RED trên dev (SHA/lệnh/lỗi hoặc N/A có lý do): ___
- GREEN cùng test/assertions (SHA/lệnh/kết quả): ___
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check` trong frontend: ___
- Backend/browser/PDF/model evidence liên quan và giới hạn: ___
- Môi trường cách ly, không dùng .env/production; quyết định DB áp dụng: ___
- Khác biệt người dùng thấy và cách khôi phục khi lỗi: ___

Closes #___
