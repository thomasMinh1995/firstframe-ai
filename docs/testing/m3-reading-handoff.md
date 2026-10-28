# M3 Gói 4 — Đọc toàn bản và chọn nguồn M4

Ngày 27/10/2026. Nhánh `feat/screenplay-reading-handoff`, bắt đầu từ `ff77241` của Gói 3. PR #55 còn mở lúc bắt đầu; Gói 4 được tách commit riêng trên nhánh kế thừa Gói 3. Chỉ triển khai Gói 4 theo plan M3 và đóng gói sau review; xử lý base PR theo lựa chọn của tác giả. Plan/roadmap/prototype, cấu hình provider/model và toàn bộ bằng chứng critic giữ nguyên.

## Phần đã triển khai

- Bản đọc lấy từ **project đã lưu** hoặc phiên bản lịch sử do tác giả chọn, tách khỏi buffer. Hiện đúng thứ tự mọi cảnh, tên, hành động/lời thoại/người nói, khoảng trắng/xuống dòng; cảnh/khối chưa có nội dung được hiện rõ, không bỏ khỏi bản đọc. Có phần mở nguồn M2, lựa chọn dàn cảnh và ý đồ/ràng buộc đi cùng đúng snapshot, kể cả bản lịch sử/nguồn đã chọn trước.
- Tác giả chủ động **Chọn bản đã đọc cho M4**. Chọn chỉ lưu metadata và bản sao nguồn bất biến; không tự lưu buffer, nhận proposal AI, khôi phục lịch sử hoặc gọi AI. Bản đang viết và bản nguồn đã chọn được đọc riêng; sửa/khôi phục/bắt đầu kịch bản khác không tự đổi nguồn M4.
- Bản nháp vẫn lưu được khi còn cảnh/khối thiếu. Để chọn nguồn, mọi cảnh phải có tên, ít nhất một khối, các khối có nội dung và lời thoại có người nói. Không dùng chất lượng AI, ảnh hoặc điểm số làm điều kiện. Cảnh thiếu có đường quay lại sửa; chọn lịch sử chưa đủ thì có thể dùng thao tác khôi phục hiện có để sửa, không tự khôi phục.
- Hướng dẫn tại M2/M3 và bước lưu của tour nêu đường lưu M2 → viết/sửa M3 → đọc bản đã lưu → chọn nguồn M4. Giữ nguyên sáu bước, storage version, tiến độ, bỏ qua/phát lại và xử lý lỗi của tour; không thêm một tour engine hoặc buộc phải dùng AI.

## Hợp đồng bàn giao và bảo vệ dữ liệu

`POST /api/projects/{project_id}/screenplay-selections` nhận `revision`, UUID `request_id`, `source_version_id` là `current` hoặc ID lịch sử của chính dự án. Không nhận snapshot, ID proposal hay cờ chất lượng từ client. Backend đọc đúng bản đã lưu, kiểm tra dữ liệu tối thiểu rồi giữ:

- `id`, `created_at`, `source_revision`, `source_version_id`;
- toàn bộ `screenplay` đã chọn, gồm ID/version, scene/block/order/text và nguồn M2/ý đồ bất biến.

`ProjectResponse.screenplay_selections` giữ lịch sử lựa chọn; `screenplay_handoff` là record cuối đã được tác giả chọn, không phải con trỏ tới screenplay hiện tại. M4 sau này phải dùng snapshot của record này. Chưa có M4/PDF/xuất bản trong gói này và không tuyên bố toàn hành trình đã hoàn tất.

Revision/CAS bảo vệ chọn nguồn giữa hai cửa sổ. Cùng request ID không tạo lựa chọn thứ hai; ID cũ dùng nguồn khác bị từ chối, replay sau lần chọn mới không kích hoạt lại nguồn cũ. Lỗi mạng có nút kiểm tra nguồn đã lưu, không tự gửi lại. Kiểm tra nguồn khi còn buffer chỉ đồng bộ metadata nguồn được yêu cầu, không ghi đè phần tác giả đang sửa; sửa nội dung ở cửa sổ khác vẫn bị phát hiện và giữ buffer.

Client cũ bỏ trường mới không xóa lựa chọn, client không ghi được selections/handoff qua PUT. Dataset M1 loại các trường M4 mới. Kết quả AI viết thử về muộn chỉ cập nhật proposal riêng, không làm mất nguồn M4 được chọn trong lúc chờ. Tối đa 100 lựa chọn/dự án; đạt giới hạn vẫn tự viết/lưu và đọc nguồn cũ được. Snapshot dùng ID/version thật, không tìm nguồn theo tên cảnh trùng nhau.

## Kiểm thử

| Kiểm tra | Kết quả |
| --- | --- |
| Backend toàn bộ | **508 passed, 1 skipped**, 123,25 giây |
| Backend Gói 4 mới | 9 ca: snapshot/sửa/khôi phục/chọn mới/replay; incomplete draft vẫn lưu và chọn lịch sử hoàn chỉnh; revision/phạm vi/nguồn giả; client cũ/quota; chọn nguồn trong lúc writer trả kết quả muộn |
| Frontend build/typecheck | Production build qua; build QA riêng trỏ API fixture, sau kiểm tra khôi phục build mặc định |
| Contract frontend | Gói 4, screenplay Gói 1–2, review Gói 3, progress và onboarding qua. Kiểm whitelist, snapshot/ID/quyền chọn, incomplete source/latest pointer, escaped text và bản đọc không có editor |
| Browser Gói 4 | Qua hai đường viết tay và AI có quyền chọn, đọc bản đã lưu, cảnh trống, quay lại sửa, buffer không tự lưu, lịch sử không tự restore, nguồn bất biến, lost response không retry, reload, 409, đọc nguồn không ghi/gọi AI |
| Browser tour/hồi quy | Qua tour cũ: storage/tiến độ, replay/bỏ qua, thao tác bàn phím, lỗi, reload, đổi dự án, cross-tab, thiếu anchor và màn hẹp; các kiểm tra sửa tay/story-plan/ý đồ cũ cũng qua |
| Giao diện | Chrome headless 1280/390/320 px, không tràn ngang/page error; đã xem ảnh màn hẹp |

Diễn tập Gói 4 dùng SQLite/API/provider giả riêng, không mở database tác giả. Đi từ M2 đã lưu qua API, soạn/lưu/đọc/chọn bằng UI; một lượt fake writer được chủ động gọi và nhận vào buffer. Chọn nguồn trước khi lưu vẫn lấy bản manual cũ; sau tự lưu mới có thể chọn bản đã nhận phương án AI. Không có lượt critic, ảnh hoặc model thật trong diễn tập này.

Sau bổ sung nguồn M2/ý đồ lồng trong bản đọc, test browser ban đầu có selector summary không còn duy nhất; đổi selector sang summary trực tiếp của nguồn M4 rồi chạy lại toàn kịch bản trên fixture sạch, đạt. Không sửa runtime để né lỗi test. Warning Starlette/httpx và CSS `start` có sẵn còn nguyên.

`git diff --check` và kiểm hash xác nhận plan/roadmap/prototype, `.env`, mọi input/output/lỗi/manifest/audit critic cũ không thay. Các thay đổi tài liệu local từ trước ngoài phạm vi Gói 4 giữ nguyên, không đưa vào PR Gói 4.

## Giới hạn và nghiệm thu

Đã có bằng chứng kỹ thuật cho bản đọc/nguồn M4 bất biến và một vòng diễn tập viết tay/AI có quyền chọn. Chưa có M4 thật, xuất bản/PDF, deploy hay nghiệm thu người dùng. Chất lượng critic Gói 3 vẫn chưa đạt và nghiệm thu liên quan vẫn mở; Gói 4 không chữa hoặc bỏ qua lỗi dẫn sai, không đóng #7/#22/#26. Không thêm model thật, vòng prompt mới, judge, embedding hoặc thay đổi plan để tuyên bố hoàn tất.


## Review cuối trước khi đóng gói PR

Không phát hiện lỗi kỹ thuật chặn được xác nhận trong phạm vi local/phim ngắn. Đã đọc cả API/schema, ProjectStore/revision, nguồn lịch sử, đường lưu dự án, writer trả muộn, decoder/whitelist frontend, buffer/inspect/chọn nguồn, bản đọc và tour.

Các điểm an toàn được xác nhận: nguồn do server chụp từ bản đã lưu; lựa chọn cũ không tự đổi sau sửa/restore/new selection; replay không tạo trùng hoặc kích hoạt lại nguồn cũ; pending proposal/buffer không được nhận âm thầm; bản thiếu nội dung vẫn lưu được; 409/mất phản hồi giữ buffer; lịch sử/client cũ và dataset M1 được bảo vệ. Không có quality gate AI trong quyền tự viết/lưu/chọn nguồn.

Trong lượt review, 9 test API Gói 4 và các contract frontend selection/screenplay/review chạy lại qua. Full backend 508 passed/1 skipped, build/typecheck, browser Gói 4/tour và màn hẹp ở phần trên là bằng chứng của cùng code triển khai, không chạy lại model hoặc tự tuyên bố nghiệm thu. Không sửa runtime sau các kiểm tra này; chỉ bổ sung ghi nhận review trong tài liệu.

PR Gói 4 cần tách khỏi ba commit của PR #55 đang chờ merge ở thời điểm review. Không tự merge #55 hoặc mở một PR vào dev chứa lại cả Gói 3 khi chưa chốt cách xử lý phụ thuộc. Giữ nguyên plan/prototype, tài liệu local ngoài phạm vi và toàn bộ bằng chứng critic; M4/xuất bản vẫn chưa triển khai.
