# Góp ý AI có Human-in-the-loop — 26/10/2026

## Thay đổi

- Phần góp ý chung, góp ý cạnh card và góp ý legacy được chọn đều nói rõ AI
  có thể sai/bỏ sót; góp ý/điểm không đánh giá năng lực người viết hoặc chứng
  minh bản thảo tốt hơn. Tác giả đối chiếu ý đồ và tự quyết định giữ/sửa.
- Kết quả cũ không còn đổi `passed` thành nhãn sẵn sàng demo/cần chỉnh sửa.
  Điểm vẫn đọc được dưới nhãn tham khảo; không thay payload hoặc dữ liệu cũ.
- Dùng chung nội dung Việt/Anh, giữ kiểm tra nguồn, snapshot, độ mới, buffer,
  revision và hành vi chỉ điều hướng. Không tích hợp bản vá một-card offline.

## Kiểm chứng

- TypeScript no-emit và production build: qua.
- Bốn checks `card-feedback.cjs`, `story-editor.cjs`, `onboarding.cjs`,
  `progress.cjs`: qua. Kiểm tra mới bao phủ Việt/Anh, `passed` true/false/null,
  điểm tham khảo, structured/legacy, card hiện tại/cũ, không gọi callback hoặc
  đổi dữ liệu chỉ vì render.
- Chrome 155.0.8059.86, production frontend tại localhost:33442:
  **24/24 tình huống qua**, gồm desktop 1440×1000 và mobile mô phỏng 390×844.
  Dùng `revision-targets.browser.cjs` với assertion HITL bổ sung ở góp ý chung,
  inspector và đường chọn legacy. Giữ kiểm tra focus, toàn bộ buffer, nguồn
  sai/cũ/thiếu, cặp mục tiêu, và không tự retry/review sau mất response lưu.
- Đã đọc ảnh inspector desktop/mobile: thông điệp rõ, không tràn khung.
  Report/ảnh local: `/tmp/firstframe-hitl-browser-pass-20261026/`.
- Một lượt trước có 2 lỗi selector của test legacy: tìm chữ nút thay vì
  accessible name. Sửa selector, chạy lại đủ 24 ca trên cùng build, không sửa
  ứng dụng để vượt test. Log lỗi giữ ở
  `/tmp/firstframe-hitl-browser-final-20261026.log`.

## Phạm vi bằng chứng

Trình duyệt dùng profile/dự án QA riêng, toàn bộ project API được mock; không
chạy backend/model hoặc tác động dữ liệu thật. Không chạy Firefox/WebKit,
Safari thật, thiết bị mobile thật hoặc pilot trong lượt này. Không dùng kết
quả này thay nghiệm thu toàn luồng, chất lượng critic hoặc người dùng hiểu
đúng thông điệp. N1/N2 vẫn là giới hạn cần xử lý/kiểm chứng riêng; lời nhắc
HITL không làm góp ý sai trở thành đúng hoặc tự hoàn tất #7.

Chạy lại: production frontend + Playwright qua `NODE_PATH`, đặt
`TOUR_TEST_URL=http://127.0.0.1:33442`, `TOUR_BROWSER=chrome`, rồi chạy
`node frontend/tests/revision-targets.browser.cjs` từ repo root. Mọi bộ
browser cần môi trường QA/API mock, không dùng smoke release với dữ liệu thật.
