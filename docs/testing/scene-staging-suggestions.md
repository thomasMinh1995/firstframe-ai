# Kiểm chứng Gói 2 — gợi ý danh sách và từng cảnh

- Ngày: 26/10/2026; nhánh `feat/scene-staging-suggestions`, từ `dev` sau PR #48 (`212f5b9`).
- Phạm vi: Gói 2; không triển khai Gói 3–4, không đổi plan, roadmap, prototype, model mặc định hoặc cấu hình runtime.
- Trạng thái: chốt triển khai/hồ sơ kỹ thuật để mở **Draft PR vào dev**. Chất lượng gợi ý còn lỗi, chưa sẵn sàng merge/không tuyên bố đạt toàn bộ nghiệm thu Gói 2. Trải nghiệm người dùng thật chờ full workflow, không phải điều kiện bắt đầu Gói 3; giữ nguyên tiêu chí nghiệm thu.

## Hành vi và bảo vệ dữ liệu

- Từ nguồn story plan được tác giả chọn ở Gói 1: gợi ý danh sách ban đầu khi chưa có cảnh; thêm một cảnh sau vị trí đã chọn/cuối danh sách; hoặc phát triển một cảnh. Backend từ chối sinh lại toàn danh sách đang có.
- Model chỉ trả nội dung. Backend cấp UUID mới cho cảnh thêm; phát triển cảnh giữ ID, ghi chú tác giả và staging choices. List dùng schema 1–60 cảnh; append/develop dùng schema đúng một cảnh, kiểm tra lại sau provider. Không tự cắt/gộp output.
- Prompt `scene-suggestions-v2` phân biệt append với develop: cảnh nguồn là `reference_scenes` chỉ để tham chiếu; `insertion_context` chỉ rõ hai mốc chèn. Output phải có diễn tiến xảy ra tiếp theo trong `action`, không kể lại/thay đạo cụ của cảnh cũ hoặc chỉ viết hành động mới trong `transition`. Các quy tắc append có phạm vi riêng, không ép list/develop theo quy tắc này.
- Giữ snapshot story plan, ý đồ và dàn cảnh trước gọi AI. Proposal mới ghi phiên bản prompt từ checkpoint, kể cả provider lỗi; dữ liệu cũ không bị đổi nhãn prompt.
- Lưu ID tác vụ trước inference. Cùng ID chỉ trả trạng thái đã có; ID dùng cho yêu cầu khác bị từ chối. Mất phản hồi không tự retry write hoặc model. Progress hiển thị event thật, không coi kiểm tra schema là xác nhận chất lượng sáng tác.
- Lưu proposal riêng trong dự án, không lấy log làm kho phục hồi. Ghi kết quả muộn bằng transaction chỉ cập nhật proposal trên dự án mới nhất; không ghi đè sửa của tác giả ở cửa sổ khác. Mutation của tác giả vẫn dùng revision/409.
- Tác giả đọc toàn bộ preview, tự chỉnh/bỏ cảnh rồi dùng. Preview đã chỉnh nằm trong buffer/dirty, có thể lưu/mở lại riêng và không thay output AI gốc. Chọn dùng đưa vào buffer, chỉ đánh dấu đã dùng khi lưu thành công. Có hoàn tác nếu chưa sửa tiếp; không tự ghi đè phần mới.
- Chọn giữ cảnh như bản tự chỉnh bỏ marker áp dụng chưa lưu, giữ nguyên nội dung và nguồn cũ; hỗ trợ tác giả tự sửa cả ý đồ/story plan mà không gắn lại provenance của proposal.
- Nguồn M1/M2 đổi khiến proposal hết hiệu lực; kết quả muộn, đã bỏ hoặc đã dùng không tự được áp dụng. Không tự đồng bộ nguồn.
- Kiểm tra kết quả bằng GET chỉ nhận revision mới khi nội dung tác giả đã lưu không đổi. So sánh gồm cả preview đã lưu, không coi việc cửa sổ khác chỉnh preview là metadata AI. Nếu có thay đổi nội dung: giữ buffer và báo xung đột.
- Có thể bỏ yêu cầu chưa rõ kết quả; model trên máy chủ có thể vẫn chạy. Kết quả đến sau giữ trạng thái đã bỏ, không kích hoạt lại hoặc tự gọi thêm.
- Lỗi cấu hình, timeout, JSON sai hoặc mất phản hồi không chặn tự viết/lưu cảnh. Không có AI khi chỉ lưu, đổi tab hoặc dùng preview. Gợi ý là tham khảo; tác giả chọn dùng không chứng minh đúng ý hay chất lượng.

## Review và kiểm tra kỹ thuật

Review toàn luồng API → provider → proposal → preview → buffer/lưu, giả định ứng dụng local với một tác giả/các cửa sổ đồng thời. Đã sửa lỗi phát hiện trong review: `sameEditableContent` bỏ sót preview do cửa sổ khác sửa, có thể cho A nhận revision mới rồi lưu đè B. So sánh giờ bao gồm nội dung preview đã lưu, giữ việc nhận metadata AI an toàn; có test unit và browser hai cửa sổ tái hiện.

| Kiểm tra | Kết quả đợt chốt |
| --- | --- |
| Toàn bộ backend, chạy từ `backend`: `.venv/bin/python -m pytest -q` | **390 passed, 1 skipped**; cảnh báo TestClient/httpx hiện có |
| Gói 1–2 `test_scene_outline.py` + `test_scene_suggestions.py` | **19 passed**: schema, nguồn/ID, lịch sử/409, pending/idempotency, lỗi/manual fallback, kết quả muộn/discard, preview riêng, vị trí chèn và prompt version |
| Frontend `npm run build` | Đạt, gồm TypeScript; cảnh báo CSS `start` trong mã nền hiện có |
| Transport `scene-contract.cjs` | Đạt: legacy, nguồn read-only, schema proposal, buffer/marker/stream input; phát hiện preview khác cửa sổ, cho phép metadata status thuần túy |
| Progress `progress.cjs` | Đạt: event thật, timeout/kết nối đứt, lỗi, bảo toàn input và nhãn song ngữ |
| Chrome `scene-suggestions.browser.cjs` | Đạt với API/SQLite thật tạm và provider giả; 1280/390/320px |
| Chrome M1 `workspace-focus.browser.cjs` | 4/4 đạt: desktop/mobile giả lập |
| Chrome M1 `workspace-dialogue.browser.cjs` | 2/2 đạt: desktop/mobile giả lập |
| `git diff --check` | Đạt |

Browser Gói 2 kiểm tra preview chỉnh/bỏ/lưu/mở lại riêng, dùng/undo/lưu, append đúng vị trí, develop giữ ID/ghi chú, giữ thành bản tự chỉnh, mất response không tạo trùng, discard, tự viết trước khi kiểm tra lỗi rồi vẫn lưu được. Ca bổ sung: B chỉ chỉnh/lưu preview; A giữ sửa chưa lưu rồi kiểm tra kết quả — A nhận lỗi xung đột, giữ text A, server giữ text B. Script chỉ reload bỏ buffer của fixture sau khi đã xác nhận bảo vệ, không làm với dữ liệu tác giả.

Không dùng database người viết hoặc model thật trong browser. Chưa kiểm tra Safari/Firefox, screen reader, bàn phím/IME trên thiết bị thật hay tải nhiều người dùng. Smoke release cũ có kỳ vọng câu chữ không còn đúng từ trước Gói 1; không tuyên bố smoke đó đạt. Không có nghiệm thu người dùng.

## Kiểm chứng model trong phạm vi hữu hạn

Đã đóng băng và chạy **đúng ba ca append v2** đã lưu với Gemma 2 9B, temperature 0.3, yêu cầu num_ctx 16384, hạn 120 giây/yêu cầu, một lần/ca. Không đổi model mặc định Qwen, không gọi API trả phí, không sửa prompt tiếp hoặc mở benchmark sau kết quả.

- 3/3 đúng schema; thời gian 16,143 / 10,835 / 8,988 giây.
- quiet/limits quay về phần mở đầu; comedy lặp nguyên action nguồn, chỉ có tiếng cười ở transition. **Chưa có ca chứng minh append mới hữu ích.** Giảm số trùng chữ không được coi là cải thiện nếu vẫn kể lại phần khác của story plan.
- [Báo cáo, baseline ba ca và toàn bộ raw/manifest/audit](../evaluations/scene-staging-append-v2-gemma2-2026-10-26.md) nằm trong PR, tự đủ liên kết.
- Các đợt v1 trước từng cho Qwen/Gemma 2/Gemma 3 đạt 9/9 hợp đồng sau sửa schema một cảnh, nhưng vẫn thiếu diễn tiến hoặc đi ngược ý đồ. Các bộ benchmark rộng và báo cáo cũ giữ ở local, ngoài PR này; không dùng kết quả v1 để tuyên bố v2 đạt. V2 chưa kiểm chứng lại list/develop hoặc model Qwen mặc định.

Không tiếp tục tối ưu critic/prompt trong phạm vi chốt này. Giữ lỗi chất lượng mở, không đóng #7/#22/#26 hay gắn nhãn đã nghiệm thu; người đọc có kinh nghiệm/PO đối chiếu khi phù hợp. Chốt kỹ thuật để review không đồng nghĩa sẵn sàng demo toàn bộ gợi ý AI.

## Chạy lại kiểm tra trình duyệt

1. Từ `backend`, chạy `.venv/bin/python tests/ui_workspace_fixture.py`. API QA ở `127.0.0.1:8034`; ghi thư mục `firstframe-workspace-*` được in ra.
2. Build/chạy frontend với `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8034`, port 3034.
3. Đặt `FIRSTFRAME_QA_DIRECTORY` đúng thư mục fixture, `NODE_PATH` trỏ runtime có Playwright; chạy `node frontend/tests/scene-suggestions.browser.cjs` từ repo root.
4. Với hồi quy M1, đặt thêm `TOUR_TEST_URL=http://127.0.0.1:3034`; API dự án của các bộ này được mock.
5. Mỗi bộ có mutation cần fixture sạch. Không dùng database thật; dừng server QA sau khi thử. Runner model từ chối ghi đè kết quả đã có; không chạy lại để chọn mẫu đẹp.
