# Streaming Interfaces — SI-01/SI-02 local

- Ngày: 02/11/2026.
- Nhánh: `fix/streaming-interfaces`; nền `fd71196a915ae870b629601c2d6076f9d0b6d4fb`. Các kết quả dưới đây được ghi trước khi stage/commit và push theo yêu cầu tiếp theo.
- Theo dõi: [issue #91](https://github.com/thomasMinh1995/firstframe-ai/issues/91), [plan](../plans/streaming-interfaces.md).
- Chỉ dùng provider giả và SQLite/dataset tạm; không gọi AI thật, không chạy QA workflow toàn bộ.

## Phần đã triển khai

- Backend opt-in `plan/stream?checkpoints=true`, snapshot serialize sau lưu checkpoint và trước critic; mặc định giữ giao thức cũ, không thêm lần lưu/gọi provider. Listener theo request được reset cả khi lỗi.
- Parser kiểm tra project/generation/source/revision, snapshot pending, lặp hợp lệ và terminal; checkpoint không resolve Promise hoặc cập nhật project/autosave.
- Vùng đọc ngoài fieldset inert, tách khỏi editor/export/nhận đề xuất. Terminal cập nhật cùng DOM, trạng thái và góp ý; lỗi hoặc thiếu terminal giữ snapshot. Callback/kết quả cũ bị cô lập, terminal kiểm tra buffer trước khi nhận project.
- Khi vùng đọc mở, tiến trình không tự thay trạng thái mở/thu gọn làm mất vị trí đọc. Nút đóng ở phía trên; người dùng chủ động đóng để trở lại vùng sửa/đề xuất.
- Draft run giữ polling/reader/card/follow/adoption hiện có; nhãn làm rõ Story plan đang góp ý, cảnh đã lưu và toàn bộ nháp sẵn sàng khi candidate đã tải.

## Kiểm tra đã chạy

1. `python -m pytest -q tests/test_plan_content_checkpoint.py tests/test_plan_recovery.py`: **50 passed**. Bao gồm opt-in/legacy, bản đầu/tạo lại, critic lỗi, snapshot bất biến, revision conflict, disconnect và iterator nhận checkpoint khi critic còn bị barrier chặn.
2. TypeScript strict compile các module Workspace và dependency: đạt.
3. Các bộ frontend `streaming-checkpoint.cjs`, `progress.cjs`, `draft-follow-reader.cjs`, `workspace-tools.cjs`, `autosave.cjs`, `candidate-autosave.cjs`, `draft-workflow-actions.cjs`: đạt. Bao gồm UTF-8 chia chunk, event sai nguồn/ID/revision, event trùng, thiếu terminal, backend cũ, preview không sửa input và trạng thái lỗi.
4. Production build từ bản sao chỉ chứa source cần dùng, loại các tệp duplicate local không liên quan: đạt. Còn warning CSS autoprefixer `start` hiện có và Starlette/httpx deprecation trong test backend.
5. HTTP/browser kiểm tra riêng với `streaming_checkpoint_fixture.py` và `streaming-checkpoint.browser.cjs`: desktop **1280×900 thành công**, mobile **390×900 critic thất bại** đều đạt. Browser nhìn thấy nội dung khi critic còn bị chặn; terminal giữ DOM reader, focus và vị trí dòng văn bản trong viewport, không tràn ngang hoặc lỗi JS. Mỗi case có đúng **1 planning + 1 evaluation trên FakeProvider**.

Kiểm tra trình duyệt theo dõi vị trí dòng đọc trong viewport, không yêu cầu `scrollY` tuyệt đối giữ nguyên khi browser scroll anchoring bù thay đổi bố cục phía trên.

## Tái chạy kiểm tra HTTP/browser hẹp

Backend fixture độc lập: chạy `python tests/streaming_checkpoint_fixture.py` từ thư mục backend bằng môi trường test đã cài dependencies. Fixture tạo SQLite/dataset trong thư mục tạm mới và chỉ dùng FakeProvider, mở cổng 8055.

Dùng bản sao frontend riêng, build với `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8055`, rồi start trên `127.0.0.1:3055`. Chạy `node tests/streaming-checkpoint.browser.cjs` từ frontend với Playwright có sẵn qua NODE_PATH. Test xác nhận marker fixture trước khi thao tác; không trỏ vào backend dữ liệu thật. Đóng cả hai server sau kiểm tra.

## Chưa kiểm chứng trong lần này

- Chưa có số đo model thật hoặc bằng chứng giảm thời gian chờ thực tế; số lần gọi nêu trên là provider giả.
- Chưa chạy QA workflow toàn bộ, toàn bộ ma trận browser/Safari/trợ năng, fixture draft run 2/6 cảnh hoặc đồng thời nhiều tab qua browser. Các hồi quy dữ liệu/CAS/disconnect dùng test backend và các test frontend hẹp; không thay bằng chứng còn thiếu của SI-03.
- Chưa tạo PR hoặc thay trạng thái hoàn tất issue #91.

Đối chiếu cuối trước commit xác nhận cả hai SQLite dự án/lượt tạo giữ nguyên hash dữ liệu; 1.366 tệp untracked có sẵn khác không đổi. Khi ghi kết quả, HEAD là `fd71196`, index không có tệp stage; cả hai server fixture đã dừng. Ảnh desktop/mobile và kết quả kiểm tra nằm trong `artifacts/streaming-interfaces-si01-si02-2026-11-02` (local, không push).
