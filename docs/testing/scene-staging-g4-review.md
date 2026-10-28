# Review Gói 4 trước PR

Ngày 27/10/2026, nhánh `feat/scene-staging-handoff`, base `dev` tại `97b3d39` (đã fetch/đối chiếu).

## Kết luận review

Không phát hiện lỗi chặn merge trong phạm vi ứng dụng local một người dùng. Code gồm hướng dẫn M2/tour, đối chiếu bản dàn cảnh đã lưu để bàn giao M3, provider ảnh MFLUX riêng, snapshot/metadata và luồng xem trước → giữ/bỏ. Review cả caller/frontend, route/schema, SQLite update, provider/filesystem, transport và các test liên quan; không chỉ đọc diff.

Các bảo vệ chính đã đối chiếu:

- Lưu ID yêu cầu và snapshot trước khi gọi provider; gửi lại cùng ID không gọi thêm ảnh. ID khác nội dung bị từ chối. Không retry tự động.
- Kết quả về muộn cập nhật riêng record bằng transaction, giữ sửa văn bản và quyết định bỏ đang có; ảnh mới không tự được chọn. Giữ ảnh dùng revision và kiểm tra nguồn hiện tại; nguồn cũ không được chọn mới.
- UUID do ứng dụng cấp, ảnh thuộc đúng project, kiểm tra PNG/kích thước/byte, re-encode bỏ metadata. Không phục vụ URL/HTML do model đưa ra; JSON không chứa binary.
- Provider chạy subprocess không qua shell, cache offline, khóa một tiến trình ảnh, giới hạn 180 giây và dừng process group. Lỗi/thiếu cấu hình/ảnh không cản lưu text.
- Prompt direct-v3 dùng trường của đúng cảnh và ý đồ trong nguồn M2 đã chọn, không lấy cảnh bên cạnh hoặc ý đồ M1 vừa thay. Prompt cũ không bị viết lại. Quyền giữ/bỏ thuộc tác giả.
- Bàn giao chỉ dùng dàn cảnh/lựa chọn đã lưu, không lấy buffer hoặc góp ý chưa nhận. Tour M1 không đổi storage/reducer/số bước.

## Kiểm chứng lại

- Toàn bộ backend: **429 passed, 1 skipped**, 141,79 giây; cảnh báo Starlette/httpx deprecated hiện có.
- Build production frontend/TypeScript/lint: đạt; cảnh báo CSS `start` hiện có.
- Node contract, progress và tour: đạt.
- Chrome bàn giao: đạt đường thủ công không gọi AI, đường trợ giúp bằng provider giả, nguồn/lưu/reload/order, lỗi mạng/409 và 1280/390/320px.
- Chrome vòng đời ảnh và hồi quy tour M1: **đạt**; ảnh/nguồn/keep/discard/lost-response/timeout/reload và tour/recovery/HITL/đọc plan/ý đồ ở desktop/mobile.
- `git diff --check`: đạt.
- Không chạy thêm model thật, không tải model hoặc thay cấu hình. Các kết quả MFLUX cũ giữ nguyên, gồm cả lỗi.

## Giới hạn còn mở

Không coi merge này là nghiệm thu M2/M3/người dùng. Chất lượng ảnh vẫn có thể sai cỡ cảnh, tuổi, ánh sáng, vị trí và chi tiết khóa; tác giả cần đối chiếu rồi tự giữ/bỏ. Hai prompt runtime khớp thí nghiệm thật đã lưu nhưng không chứng minh mọi cảnh đều đạt. Xem [kết quả prompt runtime](scene-sketch-runtime-direct-prompt.md) và [so sánh ảnh hai cảnh](scene-sketch-direct-two-scenes.md).

Cấu hình MFLUX này dành cho Apple Silicon local, không phải triển khai nhiều người dùng. Chưa kiểm tra Safari/Firefox, thiết bị thật hoặc tải production. Phân phối/deploy weights cần đối chiếu điều khoản bản lượng tử hóa đã ghi trong [báo cáo MFLUX](scene-sketch-mflux.md); không đưa runtime, weights, `.env`, SQLite hoặc ảnh tác giả vào Git.

PR chỉ gồm code/test Gói 4 và bằng chứng tổng hợp liên quan. Giữ nguyên plan, roadmap, prototype và các thay đổi #7 đang local; không đóng issue nghiệm thu.
