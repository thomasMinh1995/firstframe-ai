# UX tiến trình thao tác AI

Nhánh `feature/workflow-progress` dựa trên `dev` (1249d67). PR #18 vẫn độc lập;
không đưa implementation fidelity của PR đó vào PR UX. Khi PR #18 được ghép,
các stage `fidelity` và `fidelity_audit` tự xuất hiện theo sự kiện thực tế.

## Hành vi

- Analyze, plan và review lưu thay đổi trước khi gọi endpoint streaming.
- Backend gửi NDJSON cho bắt đầu/kết thúc/lỗi của từng model call và bước lưu.
  Endpoint thường vẫn giữ nguyên. Request vẫn kiểm tra revision như trước.
- UI thêm bước khi nhận sự kiện, không dựng trước các bước có thể bị bỏ qua.
  Audit lặp có số thứ tự riêng; hoàn tất từng call không đồng nghĩa toàn thao tác hoàn tất.
- Đồng hồ tính từ click đến result/error, gồm lưu bản nháp; dừng khi kết thúc,
  reset khi chạy lần tiếp theo. Chỉ result hợp lệ, đúng project mới nhận vào editor.
- Hoàn tất chỉ xác nhận xử lý/lưu, không chứng nhận chất lượng bản thảo.
- Lỗi lưu: giữ bản chưa lưu trên màn hình, hướng dẫn thử lưu hoặc tải JSON trước reload.
  Lỗi AI: giữ bản đã lưu và phản hồi cũ; không báo phản hồi cũ là của bản mới.
- Mất kết nối không hủy tác vụ backend. Người dùng cần kiểm tra dự án trước khi chạy lại;
  UI không có chức năng resume tiến trình sau reload.
- Nhãn tiến trình Việt/Anh theo lựa chọn ngôn ngữ đầu ra tường minh. `auto` giữ giao diện
  tiến trình tiếng Việt hiện tại; không chạy lại nhận diện ngôn ngữ hoặc dịch nội dung.
  Đổi lựa chọn không gọi AI, không lưu hay thay thế bản nháp. Đây không phải bản dịch
  toàn bộ giao diện: các thông báo backend/giao diện cũ ngoài bảng tiến trình vẫn như cũ.

## Kiểm thử

Ngày 21/10/2026:

- Dev + UX: toàn bộ 219 test backend pass; test projects sau cập nhật assertion: 28 pass.
- Checkout tạm ghép PR #18 tại 8daee1e + UX: 270 test backend pass.
- TypeScript và production build pass; Ruff các file backend thay đổi và git diff --check pass.
- Frontend checks: stage có điều kiện, audit lặp, đổi nhãn, render trạng thái lỗi lưu/lỗi AI,
  timer hoàn tất, parser UTF-8 chia chunk, dòng heartbeat, result không có newline cuối,
  stream thiếu result, xung đột revision, sai project, lỗi mạng và không mutate input.
- Browser trên frontend 3019/backend 8019 riêng, SQLite thử nghiệm, provider giả có độ trễ:
  sửa nội dung có `lab coach`, đổi Việt → Anh → Việt giữ nguyên bản chưa lưu;
  nhãn tiến trình đổi theo lựa chọn; review lưu đúng bản sửa trước AI;
  hiện fidelity → evaluation → fidelity_audit → saving; timer dừng sau hoàn tất.
  Model lỗi giữ bản sửa và feedback cũ, reload vẫn còn nội dung/ngôn ngữ đã lưu.
  Backend tắt trước bước lưu giữ bản chưa lưu, chỉ bước chuẩn bị báo lỗi, không gọi AI.
  Thử lại thành công sau lỗi.

Không benchmark Ollama hoặc đánh giá lại chất lượng suy luận trong thay đổi UX này.
Bộ kiểm thử này kiểm tra điều phối, dữ liệu và hiển thị; không thay nghiệm thu model PR #18.

Chạy frontend checks từ thư mục frontend:

```sh
npx tsc app/OperationProgress.tsx app/progressState.ts app/projectsApi.ts --outDir /tmp/firstframe-progress-tests --module commonjs --target es2023 --jsx react-jsx --skipLibCheck
NODE_PATH="$PWD/node_modules" node tests/progress.cjs /tmp/firstframe-progress-tests
```

Checklist PO: thử cả ba thao tác; xác nhận chỉ bước thực chạy xuất hiện, audit lặp không
đè lượt trước, đổi ngôn ngữ không sửa nội dung; thử lỗi trước/sau khi lưu và mở lại dự án.

## Review PR #19 — xử lý mất kết nối và sửa tiếp sau lỗi

Các lỗi đã sửa:

1. Kết nối không trả thêm dữ liệu nhưng chưa đóng khiến UI chờ vô hạn và khóa editor.
   Fetch/lưu có deadline 45 giây; stream dùng deadline im lặng 45 giây, reset bởi
   mọi chunk kể cả heartbeat 15 giây. Đây không phải giới hạn tổng thời gian chạy AI.
   Abort chỉ dừng chờ phía trình duyệt, không khẳng định backend đã dừng.
2. Sau lỗi AI hoặc hoàn tất, người dùng có thể sửa tiếp. Bảng tiến trình trước đây
   vẫn hướng dẫn mở lại dự án hoặc nói kết quả đã lưu mà không xét các thay đổi mới.
   Giờ trạng thái dirty được truyền vào bảng: nhắc lưu/tải JSON trước khi mở lại,
   và phân biệt kết quả lần chạy trước với các thay đổi mới chưa lưu.
3. Stream JSON hỏng/null hoặc event không hợp lệ có thể hiện lỗi JavaScript thô.
   Giờ kiểm tra envelope/type/status và trả thông báo lỗi dữ liệu rõ ràng, giữ editor.

Kiểm chứng sau review: 220 test backend trên nhánh PR; 271 test khi ghép PR #18;
production build và frontend regression checks pass. Có thêm test deadline bằng
đồng hồ điều khiển, heartbeat reset, timeout bước lưu, envelope hỏng, dirty sau lỗi
và sau thành công. Test đóng stream kiểm tra backend vẫn lưu khi revision không đổi,
nhưng không ghi đè khi người dùng đã lưu phiên bản mới hơn.
Browser kiểm tra lại: AI lỗi → sửa nội dung có lab coach → đổi Việt/Anh vẫn giữ
bản chưa lưu, hướng dẫn bảo vệ bản nháp cập nhật đúng. Không dùng model thật để
nghiệm thu chất lượng AI trong review UX này.
