# PR 6 — BK-05

Cải thiện thoại đúng nhánh writer/composition đã đo; phân biệt ngữ cảnh nhân vật, tránh lặp câu mẫu và giữ quyền viết sửa.

- Nhánh: `codex/ff-sb-06-vietnamese-dialogue`; base: `dev`; merge: **squash**.
- Phụ thuộc: PR 4–5 nếu cần; model và ngân sách giữ cố định trong phép so sánh.
- Phạm vi/dự toán: tối đa 450 dòng; tổng additions + deletions thực: ___ (<500, gồm test/docs/lockfile).
- Hoàn tất khi: Đọc thành tiếng, đối chiếu trước–sau; không thêm sự kiện hoặc chốt kết thúc trái ý đồ; không tăng kho regex theo fixture để lấy điểm.
- RED bắt buộc theo phạm vi: Test mới cho lỗi kiểm soát thoại đỏ trên dev; chất lượng tự nhiên có baseline chưa đạt và đánh giá người đọc riêng, không sửa kỳ vọng cũ.
- Bằng chứng RED trên dev (SHA/lệnh/lỗi hoặc N/A có lý do): ___
- GREEN cùng test/assertions (SHA/lệnh/kết quả): ___
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check` trong frontend: ___
- Backend/browser/PDF/model evidence liên quan và giới hạn: ___
- Môi trường cách ly, không dùng .env/production; quyết định DB áp dụng: ___
- Khác biệt người dùng thấy và cách khôi phục khi lỗi: ___

Closes #___
