# PR 4 — BK-03

Truyền đúng quan hệ, xưng hô, mục đích và điều còn để mở từ brief/câu trả lời hiện có vào writer; chỉ hỏi thêm khi thiếu.

- Nhánh: `codex/ff-sb-04-character-context`; base: `dev`; merge: **squash**.
- Phụ thuộc: PR 3.
- Phạm vi/dự toán: tối đa 350 dòng; tổng additions + deletions thực: ___ (<500, gồm test/docs/lockfile).
- Hoàn tất khi: Test request xác nhận ý đồ đã lưu đi tới đúng writer, đề xuất AI không thành lựa chọn tác giả; không thêm bảng hỏi bắt buộc.
- RED bắt buộc theo phạm vi: Test mới tái hiện một thông tin tác giả bị thiếu/gán sai trong request writer; đỏ trên dev, xanh với cùng assertions.
- Bằng chứng RED trên dev (SHA/lệnh/lỗi hoặc N/A có lý do): ___
- GREEN cùng test/assertions (SHA/lệnh/kết quả): ___
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check` trong frontend: ___
- Backend/browser/PDF/model evidence liên quan và giới hạn: ___
- Môi trường cách ly, không dùng .env/production; quyết định DB áp dụng: ___
- Khác biệt người dùng thấy và cách khôi phục khi lỗi: ___

Closes #___
