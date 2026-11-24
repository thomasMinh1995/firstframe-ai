# PR 2 — BK-01

Chốt tiêu chí cùng biên kịch, vài cảnh mẫu trước–sau và nguồn được phép dùng; tách ca phát triển với ca giữ lại.

- Nhánh: `codex/ff-sb-02-writing-cases`; base: `dev`; merge: **squash**.
- Phụ thuộc: PR 1.
- Phạm vi/dự toán: tối đa 350 dòng; tổng additions + deletions thực: ___ (<500, gồm test/docs/lockfile).
- Hoàn tất khi: Có lý do sửa và lựa chọn cần giữ cho từng ca; biên kịch/PO duyệt; không đưa chất liệu riêng vào repo.
- RED bắt buộc theo phạm vi: N/A: dữ liệu/tiêu chí, không sửa runtime. Ghi bản duyệt và nguồn; không tạo test đỏ giả.
- Bằng chứng RED trên dev (SHA/lệnh/lỗi hoặc N/A có lý do): ___
- GREEN cùng test/assertions (SHA/lệnh/kết quả): ___
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check` trong frontend: ___
- Backend/browser/PDF/model evidence liên quan và giới hạn: ___
- Môi trường cách ly, không dùng .env/production; quyết định DB áp dụng: ___
- Khác biệt người dùng thấy và cách khôi phục khi lỗi: ___

Closes #___
