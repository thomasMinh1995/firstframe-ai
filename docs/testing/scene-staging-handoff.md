# Gói 4 M2 — hướng dẫn và kiểm chứng bàn giao văn bản

> Báo cáo này ghi lượt văn bản trước khi có provider ảnh. Phần tích hợp MFLUX được thực hiện sau theo yêu cầu riêng; xem [báo cáo ảnh và giới hạn chất lượng](scene-sketch-mflux.md). Không coi các trạng thái “chưa có provider” dưới đây là kết luận hiện tại sau tích hợp.

- Ngày: 27/10/2026.
- Nhánh: `feat/scene-staging-handoff`, từ `dev` tại `97b3d39` sau PR #50.
- Theo xác nhận của tác giả: **chưa có provider ảnh; để phần ảnh còn mở**.
- Không sửa plan, roadmap hoặc prototype; không đổi model văn bản, gọi model thật/API trả phí, tải model ảnh hoặc tạo PR trong lượt này.
- **Gói 4 và M2 đầy đủ chưa hoàn tất.** Kết quả dưới đây chỉ xác nhận phần hướng dẫn, đường văn bản và hợp đồng bàn giao; không phải nghiệm thu ảnh, viết kịch bản thật hoặc người dùng.

## Provider ảnh còn thiếu

Factory hiện chỉ tạo provider văn bản OpenAI/Ollama qua `StructuredProvider`; chưa có hợp đồng hoặc đường tích hợp ảnh. Cấu hình mẫu và tên biến trong `.env` không có cấu hình ảnh; kiểm tra PATH không thấy `mflux-generate`, `comfy`, `invokeai-web` trên máy macOS arm64. Đây là kiểm tra cấu hình/công cụ thường dùng, không chứng minh mọi ứng dụng hoặc provider ảnh khác đều không tồn tại trên máy.

Chưa chốt provider, quyền truy cập/tái sử dụng, cách chạy, chi phí, chính sách dữ liệu hoặc ngân sách chờ tạo ảnh. Không áp ngân sách text 120 giây sang ảnh. Theo plan và xác nhận của tác giả, không mở hạ tầng ảnh giả định, không dùng ảnh có sẵn như kết quả AI và không gọi công cụ tạo ảnh trong phiên này.

Tab Phác hình nói rõ chưa triển khai và chưa có provider được tích hợp/kiểm chứng; card tiếp tục dùng khung trống có nhãn. Chưa có API ảnh, tệp ảnh, metadata ảnh hoặc nút giữ/bỏ/tạo lại ảnh. Các kiểm tra MIME/byte, phân quyền tệp theo dự án, nguồn cũ/response muộn, mất mạng, mở lại/ảnh thiếu và backup binary vẫn phải làm khi tích hợp provider; không tuyên bố các phần đó đã đạt.

## Phần đã triển khai

- Hướng dẫn M2 ba bước nằm trong icon thông tin có thể mở/đóng: chọn nguồn và thêm cảnh → tự viết/cân nhắc góp ý → lưu và đối chiếu bản viết tiếp. Không ép AI hoặc hình ảnh.
- Tour M1 vẫn sáu bước, giữ nguyên reducer, khóa storage, tiến độ, bỏ qua và phát lại. Ở bước lưu có lối tùy chọn sang hướng dẫn M2, tạm dừng tour và trả focus tới đúng nút thông tin; không ghi project hoặc gọi AI.
- Màn đối chiếu bản dàn cảnh đã lưu hiển thị phiên bản/revision, tên story plan nguồn, thứ tự/ID cảnh, diễn tiến, thông tin/ghi chú và các lựa chọn đã lưu. Trùng tên không gộp cảnh. Nguồn M1 khác hiện tại vẫn được cảnh báo và giữ nguyên.
- Khi còn sửa trên màn hình, bản đối chiếu tiếp tục đọc từ `saved.scene_handoff` và báo rõ chưa bao gồm sửa chưa lưu. Lỗi mạng/409 không thay bản đang viết hoặc giả như đã cập nhật bản bàn giao.
- Tái sử dụng `scene_handoff` do backend tính từ dàn cảnh đã lưu, cùng cơ chế lưu/revision/lịch sử có sẵn. Đây là hợp đồng để M3 dùng sau này, **chưa có thao tác tạo screenplay hay bản bàn giao được M3 tiếp nhận**. Nút lưu không sinh thêm workflow hoặc tự nhận các proposal/ý riêng.
- Không thêm schema, mutation, provider hoặc dependency runtime mới; không thay khóa nội dung/nguồn phản hồi M1. Các lựa chọn chưa dùng hoặc đã bỏ vẫn ở lịch sử góp ý riêng.

## Kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend `python -m pytest -q` | **403 passed, 1 skipped**; có cảnh báo TestClient/httpx hiện có |
| `tests/test_scene_handoff.py` mới | **3 passed**: chọn nguồn lịch sử khác M1 hiện tại, ID/order/cảnh trùng tên, text/ghi chú/lựa chọn giữ nguyên, nguồn không bị client giả mạo, reload, đường AI giả chỉ nhận lựa chọn đã dùng/lưu, bỏ/preview không lọt vào bàn giao, nguồn cũ/409 và cảnh chưa đủ nội dung |
| Frontend production build/TypeScript | Đạt; build QA có cảnh báo CSS `start` hiện có trong `storyWorkspace.css` |
| Node contract/progress/onboarding | Đạt; giữ sáu bước, storage, request/session isolation và trạng thái tour cũ |
| Chrome `scene-handoff.browser.cjs` | Đạt với API/SQLite tổng hợp riêng; đường thủ công không có lượt AI, đường trợ giúp chỉ có đúng hai stage provider giả `scene_generation`/`staging_generation` |
| Chrome `onboarding.browser.cjs` | Đạt: tour M1, khôi phục plan, HITL, đọc story plan và ý đồ; không có model thật |
| Chrome `workspace-focus.browser.cjs` | **4/4 đạt**, desktop và mobile giả lập |
| `git diff --check` | Đạt |

Browser Gói 4 kiểm tra: mở hướng dẫn M2 giữ bước M1 đang dừng; bỏ qua/phát lại/hoàn tất; không mutation do tour; khung ảnh trung thực; lưu và đối chiếu đúng bản đã lưu; sửa chưa lưu không lọt vào preview; mất mạng/409 giữ text và bản lưu; nhận cảnh G2 sau tự chỉnh; bỏ ý, chỉnh ý chưa nhận và dùng một ý G3; lưu/reload giữ ID/order và không đổi nguồn phản hồi M1. Không gọi ảnh để đi hết luồng. Đã kiểm tra 1280/390/320px và xem ảnh mobile bằng mắt; Chrome 156 trên máy này, không phải thiết bị di động thật.

Lượt browser đầu đã thực hiện các ca nhưng bị đánh lỗi bởi script thiết lập `localStorage` ở tài liệu không cho phép storage. Đã sửa init script để xử lý trường hợp này và chạy lại toàn bộ trên DB tổng hợp sạch; chỉ lượt sau được tính đạt. Lệnh compile CJS đầu thiếu thư viện `dom.iterable`; chạy lại với đúng thư viện đã đạt, production build không gặp lỗi này.

## Phần chưa đạt và điểm dừng

- Chưa tạo ảnh thật, chưa lưu/giữ/bỏ/phác lại hoặc mở lại ảnh. Provider, chi phí, dữ liệu và ngân sách chờ vẫn chưa chốt; ảnh là phần còn mở đúng theo xác nhận của tác giả.
- Chưa có M3 để kiểm chứng nhận nguồn và viết kịch bản thật. Không kết luận hoàn thành M2 đầy đủ hoặc thay đổi tiêu chí nghiệm thu #7/#22/#26.
- Không chạy thêm model để chấm chất lượng; giới hạn góp ý/độ trễ trong báo cáo Gói 2–3 còn nguyên. Chưa có nghiệm thu người dùng, Safari/Firefox, screen reader/IME thiết bị thật hoặc tải production nhiều người dùng.
- Code/test và báo cáo đang local trên nhánh mới; chưa commit/push/tạo PR.

## Chạy lại browser Gói 4

1. Từ `backend`, chạy `.venv/bin/python tests/ui_workspace_fixture.py`; API QA tại `127.0.0.1:8034`, ghi lại thư mục `firstframe-workspace-*` được in ra. Không dùng DB tác giả.
2. Build frontend với `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8034`, chạy production server tại `127.0.0.1:3034`.
3. Đặt `FIRSTFRAME_QA_DIRECTORY` đúng thư mục fixture và `NODE_PATH` tới runtime có Playwright, chạy `node frontend/tests/scene-handoff.browser.cjs` từ repo root. Mỗi lần chạy dùng fixture sạch vì test sửa dữ liệu tổng hợp.
4. Với các bộ browser M1, đặt `TOUR_TEST_URL=http://127.0.0.1:3034`; các request project của chúng được mock.
