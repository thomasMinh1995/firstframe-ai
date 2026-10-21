# Tour người dùng mới: kiểm chứng và review

Triển khai theo [issue #22](https://github.com/thomasMinh1995/firstframe-ai/issues/22)
và [plan đã review](../plans/new-user-tour.md), từ `dev` sau merge PR #23.

## Hành vi

- Workspace mới mời xem tour sau khi tải thành công. Người đã có dự án mở
  bằng **Hướng dẫn sử dụng**; điểm vào ưu tiên brief cần làm rõ trước draft cũ.
- Sáu bước có một spotlight mỗi bước. **Thực hành** đóng thẻ và focus control
  thật; **Tiếp tục hướng dẫn** là thao tác chủ động, không tự bật overlay sau AI.
- Nhập ý tưởng/sửa draft có thể tiếp tục mà không lưu hoặc gọi AI. Chờ
  create/analyze/plan chỉ được mở khóa bởi kết quả đúng phiên tour/lượt request.
- Các nút thật của workspace giữ luồng lưu trước AI. Tour không ghi dự án,
  thay buffer, tự chạy AI hoặc chứng nhận chất lượng câu chuyện.
- Đóng/Escape/Bỏ qua và tín hiệu dismissed/completed từ tab khác dừng tour.
  Reload chỉ cho chọn tiếp tục, không phát lại request. Storage lỗi/version
  không hỗ trợ chỉ tắt lời mời tự động, vẫn xem thủ công được.
- Dialog chặn tương tác nền và giữ vòng Tab/Shift+Tab. Viewport quá thấp
  dùng thẻ cuộn trong màn hình; Thực hành/Hoàn tất trả focus về đích phù hợp.

## Kết quả kiểm tra

Ngày 21/10/2026: tất cả bộ kiểm tra dưới đây đã pass trên macOS, với Chrome
headless chạy frontend production. Dữ liệu được tổng hợp; không dùng kho dự
án thật hoặc gọi provider AI. Ảnh cuối tài liệu lấy từ lượt chạy production.

- TypeScript và production build.
- State checks: schema storage, sáu bước, input-only practice, draft cũ,
  tạo dự án đổi ID, save/AI thất bại, request lặp/sai ID, phiên tour cũ,
  reload, đổi dự án, cross-tab terminal state và hoàn tất.
- Frontend regression `progress.cjs`: parsing stream, deadline, giữ input,
  các bước lỗi/thành công và nhãn ngôn ngữ.
- Browser: đi đủ sáu bước, so sánh buffer trước/sau tour và đếm request ghi;
  không câu hỏi/không section/không feedback, câu trả lời còn thiếu/để sau,
  chọn lại ngôn ngữ khi analysis đã có, lỗi PUT trước AI và lỗi AI sau PUT.
- Browser: reload, đổi dự án, tab khác bỏ qua khi analyze đang chờ, storage
  hỏng/bị chặn, tải workspace lỗi và mất anchor trong lúc thẻ đang mở.
- Browser: Tab/Shift+Tab/Escape, focus sau thực hành/hoàn tất, ngăn bấm xuyên
  spotlight, desktop 1280×900, mobile 390×844 và viewport thấp 320×260.

Chưa kiểm chứng bằng trình đọc màn hình thật, bàn phím ảo trên thiết bị thật
hoặc Safari/Firefox. Chưa thực hiện pilot 3–5 người mới; PR chờ review UX và
issue #22 vẫn mở cho nghiệm thu. Không dùng kiểm thử tour để kết luận chất
lượng AI hoặc tốc độ model.

## Chạy lại

Từ `frontend/`, cài dependency bằng `npm ci`. State/regression checks:

```sh
npx tsc app/onboardingState.ts app/OperationProgress.tsx app/progressState.ts app/projectsApi.ts --outDir /tmp/firstframe-tour-tests --module commonjs --target es2023 --jsx react-jsx --skipLibCheck
node tests/onboarding.cjs /tmp/firstframe-tour-tests
NODE_PATH="$PWD/node_modules" node tests/progress.cjs /tmp/firstframe-tour-tests
npx tsc --noEmit
npm run build
npm run start -- -p 3033
```

Trong terminal thứ hai, từ `frontend/`, cần Google Chrome. Playwright chỉ là
công cụ kiểm thử bên ngoài repository, không phải dependency runtime:

```sh
npm install --prefix /tmp/firstframe-tour-browser-tools --no-audit --no-fund playwright@1.61.1
NODE_PATH=/tmp/firstframe-tour-browser-tools/node_modules TOUR_TEST_URL=http://localhost:3033 node tests/onboarding.browser.cjs
```

Browser suite chặn toàn bộ `/api/projects` bằng route giả trong context mới,
kể cả khi máy có backend đang chạy. Không cần khởi động backend. Ảnh ghi vào
`/private/tmp/firstframe-tour-screenshots` mặc định; đổi bằng `TOUR_SCREENSHOTS`.

## Ảnh để review

![Tour trên desktop](assets/new-user-tour-desktop.png)

![Tour trên mobile](assets/new-user-tour-mobile.png)
