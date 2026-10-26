# Critic: chưa đủ căn cứ không phải yêu cầu sửa

## Hành vi

`uncertain` cho phép `suggestion` là chuỗi rỗng hoặc câu hỏi/gợi ý tùy chọn.
Nó tạo finding `clarification-*` mức `info`, không tạo điểm yếu. UI tách nhóm
“Chưa đủ căn cứ — cần làm rõ”, cho xem nguồn và điều hướng tới đúng card để
tác giả đối chiếu; không ép sửa. `mismatch` vẫn cần gợi ý không rỗng;
`aligned` vẫn không được kèm lời sửa.

Verdict của lượt mới được backend tính từ reviews: có mismatch → `false`;
không mismatch nhưng có uncertain → `null`; chỉ aligned → `true`. Không lấy
trường passed do model tự trả làm kết luận, không đổi verdict đã lưu của các
lượt cũ. Đây là trạng thái đánh giá AI, không chứng nhận chất lượng tác phẩm.

Nguồn dẫn cần được người đọc đối chiếu theo ba phần: yêu cầu nguyên văn của
tác giả, chi tiết draft liên quan, và lý do chi tiết đó phù hợp/trái yêu cầu.
Trích đúng chữ không tự chứng minh lý do đúng. Hai hành động ở hai thời điểm
không tự mâu thuẫn; sở thích biên tập không tự thành vi phạm ý đồ.

## Bảo vệ giữ nguyên

- Không thêm trường bắt buộc hoặc di trú dữ liệu; note uncertain cũ có lời
  sửa tiếp tục đọc được, verdict và lịch sử cũ không bị chấm lại.
- Giữ kiểm tra project/artifact, ID/quote, snapshot, câu trả lời tác giả,
  focus/card cạnh, revision và độ mới. Nguồn sai/thiếu/cũ không tạo link đoán.
- Xem nguồn/điều hướng không đổi buffer, lưu, gọi AI hoặc tự áp dụng gợi ý.
  Tác giả vẫn tự chọn giữ hay sửa; lỗi lưu chưa rõ không tự kích hoạt review.
- Tạo plan, lưu/mở lại, lịch sử và phục hồi plan khi critic lỗi không đổi.

## Kiểm chứng — 26/10/2026

- Backend: 371 test qua, 1 bỏ qua; gồm provider giả cho aligned/mismatch/
  uncertain, suggestion rỗng/câu hỏi, verdict model không đáng tin, note hỗn
  hợp, lịch sử cũ, nguồn, stale feedback và xung đột revision.
- TypeScript và production build: qua.
- `card-feedback.cjs` và `story-editor.cjs`: qua, gồm render Việt/Anh,
  nguồn chính xác, nhóm trung lập, fallback legacy và không sửa dữ liệu khi đọc.
- Chrome QA với API mock: 30/30 ca trên 1440×1000 và 390×844 mô phỏng;
  có kiểm tra mở nguồn/điều hướng uncertain, buffer và nguồn sai/cũ.
  Chạy bằng `frontend/tests/revision-targets.browser.cjs` với frontend
  production, `TOUR_TEST_URL`, `TOUR_BROWSER=chrome` và runtime có Playwright.

## Giới hạn

Prompt/model runtime giữ nguyên. Đây là sửa hợp đồng và cách trình bày,
không phải bộ kiểm tra đúng/sai ngữ nghĩa hoặc bản khắc phục N1/N2. Không chạy
model thật, đổi plan/roadmap, thêm embedding/judge, dàn cảnh hoặc xuất bản
trong thay đổi này. Chưa có nghiệm thu người dùng hoặc thiết bị mobile thật.
