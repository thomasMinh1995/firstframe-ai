# PR 7 — BK-06

Hoàn thiện yêu cầu sửa riêng các khối thoại bằng API proposal hiện có và điều khiển UI tối thiểu.

- Nhánh: `feat/ff-sb-07-dialogue-revision`; base: `dev`; merge: **squash**.
- Phụ thuộc: PR 4, 6.
- Phạm vi/dự toán: tối đa 450 dòng; tổng additions + deletions thực: ___ (<500, gồm test/docs/lockfile).
- Hoàn tất khi: Preview/nhận/bỏ/hoàn tác được; giữ speaker, action và khối ngoài phạm vi; nguồn đổi thì từ chối nhận.
- RED bắt buộc theo phạm vi: Test mới tái hiện thao tác sửa thoại chưa hỗ trợ hoặc sửa tràn phạm vi; đỏ trên dev rồi xanh sau sửa.
- Bằng chứng RED trên dev (SHA/lệnh/lỗi hoặc N/A có lý do): ___
- GREEN cùng test/assertions (SHA/lệnh/kết quả): ___
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check` trong frontend: ___
- Backend/browser/PDF/model evidence liên quan và giới hạn: ___
- Môi trường cách ly, không dùng .env/production; quyết định DB áp dụng: ___
- Khác biệt người dùng thấy và cách khôi phục khi lỗi: ___

Closes #___
