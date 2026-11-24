# PR 5 — BK-04

Sửa một nhóm lỗi diễn tiến đã tái hiện: lặp hành động, đổi chủ thể hoặc vượt điểm dừng; chọn đúng một công đoạn gây lỗi.

- Nhánh: `codex/ff-sb-05-scene-progression`; base: `dev`; merge: **squash**.
- Phụ thuộc: PR 3–4; bỏ task nếu baseline không có lỗi này.
- Phạm vi/dự toán: tối đa 350 dòng; tổng additions + deletions thực: ___ (<500, gồm test/docs/lockfile).
- Hoàn tất khi: Hồi quy lỗi qua; trước–sau cùng input cải thiện; giữ các ca người nói, đạo cụ và kết mở hiện có.
- RED bắt buộc theo phạm vi: Test mới của lỗi nguồn/diễn tiến đỏ trên dev; nếu chỉ đổi prompt, lưu baseline thất bại ở content gate đã chốt và kiểm đúng prompt/profile.
- Bằng chứng RED trên dev (SHA/lệnh/lỗi hoặc N/A có lý do): ___
- GREEN cùng test/assertions (SHA/lệnh/kết quả): ___
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check` trong frontend: ___
- Backend/browser/PDF/model evidence liên quan và giới hạn: ___
- Môi trường cách ly, không dùng .env/production; quyết định DB áp dụng: ___
- Khác biệt người dùng thấy và cách khôi phục khi lỗi: ___

Closes #___
