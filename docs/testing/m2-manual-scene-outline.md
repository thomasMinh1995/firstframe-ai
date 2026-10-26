# Kiểm chứng Gói 1 M2 dàn cảnh thủ công

- Ngày: 26/10/2026.
- Nhánh: `feat/scene-staging-manual-outline`.
- Phạm vi: Gói 1 dàn cảnh thủ công theo prototype đã chốt, chưa triển khai gói 2–4.
- Không thay model, prompt, prototype hoặc
  dữ liệu dự án thật; không gọi model/API trả phí.

## Phần đã triển khai

- Dàn cảnh có nguồn story plan do backend chụp từ bản hiện tại đã lưu
  hoặc phiên bản lịch sử được chọn. Giữ đúng ngữ cảnh/câu trả lời lịch sử,
  không khôi phục đè bản M1. Thay M1 báo khác nguồn, không tự sửa M2.
- Cảnh có UUID ổn định, thêm/xóa/sắp xếp và hoàn tác trong buffer; có thể
  xóa cảnh cuối. Hoàn tác không ghi đè những sửa đổi mới hơn.
- Dùng SQLite/revision hiện có; giữ lịch sử dàn cảnh và khôi phục riêng M2.
  Client bỏ trường M2 khi lưu không làm mất dàn cảnh. Client không được
  gửi lại nguồn/lịch sử như dữ liệu có thể sửa.
- Bảng cảnh chữ S, DOM theo thứ tự câu chuyện, popover với ba tab,
  hướng dẫn ⓘ và hai câu hỏi dàn cảnh tùy chọn. Các lựa chọn kỹ thuật chỉ
  mở ô chỉnh khi cần; chuyển tab hoặc đóng/Esc giữ phần đang viết.
- Lưu từ form ghi mọi sửa đang chờ của dự án. Có bản nguồn M3 chứa đúng
  ID/phiên bản/thứ tự cảnh đã lưu. UI nói rõ chưa có trình viết M3.
- Chưa có gợi ý AI hoặc tạo hình; card dùng khung trống có nhãn, không
  giả ảnh do AI tạo. Không có tác vụ AI khi thao tác M2.

## Kết quả kiểm tra

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend `python -m pytest -q` | 375 passed, 1 skipped; có cảnh báo deprecation TestClient/httpx hiện có |
| Backend M2 riêng `tests/test_scene_outline.py` | 4 passed: lưu/mở lại, khoảng trắng/ID, client cũ, M1 feedback giữ nguồn, 409, đổi thứ tự/xóa/restore, chọn nguồn lịch sử và câu trả lời legacy |
| Frontend production build `npm run build` | Đạt, bao gồm TypeScript và kiểm tra build |
| Transport M2 `tests/scene-contract.cjs` | Đạt: không gửi nguồn/lịch sử qua PUT; từ chối source/ID/trường sai; chấp nhận dữ liệu legacy |
| Unit checks progress/story editor/card feedback/onboarding | Đạt; giữ nguồn, buffer, feedback HITL và trạng thái tour |
| Chrome M2 `tests/scene-outline.browser.cjs` | Đạt với API/SQLite tạm thật, provider giả; không phát sinh lượt AI M2 |
| Chrome M1 `tests/workspace-dialogue.browser.cjs` | 2/2 ca đạt ở 1440px và 390px; API giả |
| Chrome M1 `tests/workspace-focus.browser.cjs` | 4/4 ca đạt: sửa/lưu/focus và luồng tạo ở desktop/mobile giả lập; API giả |
| Esc trả focus về card vừa mở | Đạt trong Chrome, không ghi dữ liệu |
| `git diff --check` | Đạt |

Bộ trình duyệt M2 dùng `tests/ui_workspace_fixture.py`, tạo SQLite và
dataset trong thư mục tạm riêng. Fixture tạo sẵn story plan bằng provider
giả; đếm stage provider trước/sau thao tác M2 để xác nhận không gọi AI.
Kiểm tra Chrome 155 ở 1280/768/390/320px, bàn phím, tabs và popover; đã xem
ảnh chụp desktop/mobile. Đây không phải kiểm thử thiết bị di động thật.

Các ca M2 gồm sáu cảnh để kiểm tra đường chữ S, đổi thứ tự giữ ID,
lưu/reload, xóa rồi sửa tiếp trước hoàn tác, hai cửa sổ lưu xung đột 409,
mất response sau khi server đã lưu, giữ tên dự án lẫn text cảnh trên màn
hình, xóa hết/hoàn tác cảnh cuối và chuẩn bị nguồn M3. Nội dung M1 và
nguồn feedback vẫn giữ nguyên qua lượt M2.

Đã chạy bộ smoke cũ `workspace-release.browser.cjs`; bộ này dừng ở thông
báo “Hãy trả lời các câu hỏi trước khi tạo bản phát triển.”. Chuỗi này
cũng không tồn tại trong `HEAD` trước thay đổi M2; script dùng luồng xác
nhận cũ. Không sửa M1 để chiều kỳ vọng cũ và không tính bộ smoke đó là đạt.
Hai bộ browser hiện hành nêu trên được chạy thay cho kết luận hồi quy UI;
chưa tuyên bố toàn bộ smoke release cũ đã hoàn thành.

## Giới hạn và bước sau

- Chưa kiểm chứng Safari/Firefox, trình đọc màn hình hoặc bàn phím/IME
  trên thiết bị thật. Chưa có nghiệm thu người dùng hay chất lượng sáng tác.
- Chưa có M3 để thử viết kịch bản thật; mới kiểm chứng payload bàn giao và
  trạng thái UI trung thực về giới hạn đó.
- Gói 2–4, provider tạo ảnh và nghiệm thu M1/#7/#22 vẫn còn ngoài kết quả
  này. Không đổi tiêu chí hoặc chuyển các issue đó sang đạt.
- PR Gói 1 chỉ gồm code, test và báo cáo này; không đưa tài liệu/thử nghiệm
  chưa commit từ các đợt trước hoặc thư mục prototype vào PR code này.

## Chạy lại kiểm tra trình duyệt M2

1. Từ `backend`, chạy `.venv/bin/python tests/ui_workspace_fixture.py`;
   ghi thư mục fixture được in ra, API QA ở `127.0.0.1:8034`.
2. Build frontend với `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8034`,
   chạy bản build ở `127.0.0.1:3034`.
3. Cấp `FIRSTFRAME_QA_DIRECTORY` đúng thư mục fixture và `NODE_PATH` trỏ
   tới runtime có Playwright, chạy `node frontend/tests/scene-outline.browser.cjs`
   từ repo root. Script yêu cầu fixture riêng, không chạy trên backend thật.
4. Với hai bộ hồi quy browser M1, đặt thêm
   `TOUR_TEST_URL=http://127.0.0.1:3034`; các request dự án được mock.

Chạy M2 bằng fixture sạch vì script thực hiện thêm/xóa/lưu. Giữ log kết
quả lỗi, không thử trên dự án của tác giả để thay dữ liệu fixture.
