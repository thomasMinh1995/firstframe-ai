# Kiểm tra phục hồi plan khi critic lỗi

Phạm vi: phần 4 của `docs/plans/harness-improvement.md`. Dùng kho dự án SQLite
hiện có; raw dataset chỉ ghi bằng chứng, không phải nguồn khôi phục.

## Hành vi và bảo vệ dữ liệu

- Sau planner, lưu bản và nguồn trước khi gọi critic. `plan_generations` giữ
  ID lượt tạo, revision/content nguồn, ý đồ hiệu lực, draft và trạng thái
  `pending`, `failed` hoặc `reviewed`. Dự án cũ thiếu trường này đọc như danh
  sách rỗng; đọc không ghi hoặc di trú dữ liệu.
- Chưa có draft: lưu trực tiếp bản đầu, không có feedback giả hoặc bước nhận.
  Critic thành công chỉ gắn feedback vào đúng draft/ngữ cảnh đã đọc.
- Đã có draft: mọi lần tạo lại giữ thành đề xuất, kể cả khi critic thành công.
  Draft, feedback và lịch sử đang dùng không bị thay. Có thể xem đề xuất cùng
  ý đồ nguồn và góp ý riêng; mở xem không ghi dữ liệu hoặc gọi AI.
- Nhận đề xuất là thao tác riêng có revision. Chỉ cho nhận khi nguồn/draft
  còn khớp; lưu lịch sử trước khi thay. Nhận lặp, nguồn đổi hoặc response muộn
  không tự cập nhật revision rồi thử ghi lại. Đề xuất thiếu nguồn feedback
  hợp lệ không được dùng feedback của draft cũ.
- UI chặn nhận/mở lại khi có buffer chưa lưu. Mất response không làm UI tự
  tải lại hoặc retry; buffer vẫn giữ. Khi không có sửa chưa lưu, tác giả tự
  mở lại bằng GET để xác nhận trạng thái đã lưu.
- Nếu critic lỗi, API trả dự án đã giữ với trạng thái `failed`; UI báo rõ
  chưa có góp ý hợp lệ. Nếu tiến trình dừng sau checkpoint, bản `pending`
  vẫn mở lại/nhận được. Có thể tự sửa rồi review riêng, không phải gọi lại
  planner. Không thêm retry tự động hoặc vòng AI tự sửa.
- Lượt critic lỗi vẫn có dataset status `failed`, `workflow_complete=false`.
  Đề xuất chưa nhận không được ghép với feedback đang dùng để phát lại demo
  hoặc đưa vào mẫu đã hoàn thành. Bản ghi thành công giữ snapshot dự án thật
  và `plan_generation` riêng của lượt đó; không sửa raw recording khi nhận.

## Test tự động

Backend: `backend/tests/test_plan_recovery.py`, cùng regression projects,
dataset/demo, workflow và provider.

| Ca | Kỳ vọng |
| --- | --- |
| Bản đầu / tạo lại × HTTP / stream × timeout, request, JSON lỗi, thiếu cấu hình | Checkpoint tồn tại trước critic; mở lại đúng bản, trạng thái và nguồn |
| Critic lỗi rồi sửa/nhận và review | Một lần planner, hai lần critic (một lỗi và một review); không sinh lại plan |
| Tạo lại thành công | Đề xuất và feedback riêng; chỉ thay draft khi nhận; giữ lịch sử |
| Cửa sổ khác lưu trước checkpoint hoặc trong critic | 409; không ghi đè hoặc gắn feedback muộn; không đổi revision để retry |
| Nhận hai lần hoặc nhận sau đổi draft/brief/answers/ngôn ngữ | Từ chối; bản mới và nguồn feedback không đổi |
| Nhận bản pending trong lúc critic chạy | Giữ bản đã nhận; critic muộn xung đột, không gắn feedback |
| Ngắt stream sau checkpoint | Công việc kết thúc lưu; mở lại bằng client mới vẫn có bản |
| Planner lỗi trước checkpoint | Không thêm draft, đề xuất hoặc revision |
| Dữ liệu cũ / client gửi trường phục hồi | Đọc không ghi; client không thể sửa metadata phục hồi qua PUT |

Frontend: `frontend/tests/progress.cjs` kiểm tra dữ liệu trả về và payload
chỉ chứa các trường được phép sửa. `frontend/tests/onboarding.browser.cjs`
chạy trên production build, chặn toàn bộ API để không dùng dữ liệu thật:

- Desktop 1280×900 và mobile 390×844; Chrome và WebKit.
- Bản đầu không có nút nhận; tạo lại giữ editor cũ tới khi chọn nhận.
- Critic lỗi có thông báo thiếu review; mở lại và review không gọi lại plan.
- Xem nguồn/đề xuất không gửi request; buffer chưa lưu chặn nhận/mở lại.
- Mất response plan/nhận, retry nhận, hai cửa sổ: giữ buffer/lịch sử và không
  tự retry hoặc tải lại; tác giả có thể mở lại bằng GET để xác nhận.
- Đề xuất có critic hợp lệ giữ feedback riêng sau nhận; đề xuất thiếu review
  không nhận feedback cũ. Lựa chọn góp ý tạm được bỏ khi nhận draft khác.

Các ca provider giả đo số lần gọi planner; đây là kiểm chứng phục hồi tác vụ,
không phải đo chất lượng sáng tác hoặc benchmark model thật. Chưa thay thế
nghiệm thu demo 9/9, ngân sách chờ đã chốt hoặc pilot người dùng.
