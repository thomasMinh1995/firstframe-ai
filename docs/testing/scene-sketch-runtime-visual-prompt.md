# Gói 4 — prompt mô tả thị giác theo dữ liệu cảnh trong runtime

- Ngày: 27/10/2026; nhánh `feat/scene-staging-handoff`, tiếp tục bộ Gói 4 đang local.
- Phạm vi mới: thay cách ghép prompt ảnh từ JSON thành các câu mô tả theo snapshot cảnh; kiểm thử và báo cáo trước PR.
- Không thay plan/roadmap/prototype, cấu hình, model ảnh/văn bản, ngân sách provider hoặc các bảo vệ nguồn/tệp. Chưa commit/push/tạo PR.

## Thay đổi runtime

`sketch_prompt()` vẫn là điểm ghép prompt được route Gói 4 gọi, nhưng không dump đối tượng JSON vào đầu vào model nữa. Bộ ghép câu xác định đưa nội dung vào các đoạn mô tả, giữ nguyên giá trị tác giả đã viết; không thêm lượt LLM, dịch/tóm tắt hoặc suy luận một kịch bản mới.

| Dữ liệu nguồn | Cách đưa vào prompt |
| --- | --- |
| Diễn tiến, nhân vật, địa điểm, thời điểm của cảnh chọn | Mô tả hành động nhìn thấy, người có mặt, không gian và thời điểm; bỏ trường trống |
| Các lựa chọn `staging_choices` đã nhận/lưu vào cảnh | Câu tương ứng vị trí/chuyển động, diễn xuất, bối cảnh/đạo cụ, ánh sáng, màu sắc, trang phục, bố cục, cỡ cảnh, góc máy, khoảnh khắc |
| Mục tiêu, đóng góp cảnh, cảm nhận người xem | Tham chiếu ý nghĩa để thể hiện bằng hành vi, không thành chữ trên ảnh |
| Ý đồ/giới hạn/câu trả lời đã xác nhận trong story plan nguồn | Giữ làm bối cảnh và giới hạn; không dùng ý đồ M1 hiện tại khác snapshot hoặc câu hỏi chưa trả lời |
| Ghi chú giữ/tránh và yêu cầu phác tùy chọn | Giới hạn nguồn ưu tiên hơn yêu cầu phác; yêu cầu không được thay diễn tiến hoặc phong cách nét vẽ |

Phần phong cách chung yêu cầu nét viền graphite mảnh/hơi bất quy tắc, ít hatch, giấy trắng; không ảnh chụp, chữ, nhãn hay chia khung. Các chỉ dẫn tuổi, hướng nhìn và trạng thái đạo cụ là **điều kiện theo nguồn**: không gắn sẵn tuổi 55/25, trái/phải, hai nhân vật, quan hệ mẹ–con, căn bếp hoặc phong bì. Cảnh yêu cầu nhìn khác hướng, không có người hoặc đạo cụ mở vẫn được giữ nguyên dữ liệu; không ép nhìn nhau hoặc đóng tất cả đồ vật. Màu sắc nếu có vẫn giữ nguyên ý định bằng text, hướng dẫn diễn đạt bằng sắc độ graphite cho phong cách đen trắng hiện tại.

Không đưa ID, tiêu đề cảnh, các tên trường JSON, cảnh hàng xóm, ảnh/proposal cũ hoặc góp ý chưa nhận thành nội dung hình. Tên cảnh và toàn snapshot vẫn được lưu trong metadata; chỉ không yêu cầu model vẽ tên thành chữ. Dữ liệu tham chiếu được đặt trong dấu trích dẫn và phân biệt với chỉ dẫn; đây là hướng dẫn prompt, không chứng minh model miễn nhiễm với diễn giải sai hoặc prompt injection.

Route gắn **`prompt_version=scene-sketch-visual-v2`** cho lượt ảnh mới. Default cũ trong schema giữ `scene-sketch-v1` cho dữ liệu legacy; không đổi nhãn, viết lại prompt/ảnh hoặc metadata cũ. Prompt thực sự gửi provider được lưu nguyên trong record, mở lại/đối chiếu được bằng UI hiện có.

## Bảo vệ dữ liệu giữ nguyên

- Cảnh và context lấy từ snapshot dàn cảnh/story plan đã chọn, server gắn nguồn; không tin source/path/URL/selection do client hoặc model đưa vào.
- Request ID, checkpoint trước AI, revision/CAS, transaction ghi kết quả muộn, nguồn cũ/409, một tiến trình ảnh, thời hạn 180 giây, quota và không tự retry giữ nguyên.
- Kiểm tra PNG/byte/kích thước, UUID và membership dự án, tệp/metadata lưu riêng, xem trước không thay ảnh đang giữ, giữ/bỏ chủ động và fallback text giữ nguyên.
- Không thêm lượt model văn bản để viết prompt, không tự nhận góp ý hoặc sửa cảnh. Tự viết/lưu/bàn giao text vẫn hoạt động khi ảnh lỗi.
- Thay prompt không tự gọi AI hoặc tạo lại ảnh cũ. Muốn dùng prompt mới, tác giả chủ động yêu cầu lượt mới từ nguồn đã lưu.

## Kiểm thử

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend | **426 passed, 1 skipped**; cảnh báo TestClient/httpx hiện có |
| Prompt unit + API ảnh chuyên biệt | **23 passed**: 6 ca prompt và 17 ca API/provider ảnh, gồm các bảo vệ cũ |
| Prompt theo cảnh khác nhau | Thợ sửa xe 68 tuổi/người trẻ 19 tuổi; người bán hàng 43 tuổi bằng tiếng Việt; sân ga không người/hộp dụng cụ khóa; hai bạn trưởng thành tuổi chưa chốt và quay lưng/nhìn khác hướng |
| Trường thiếu/nguồn/đầu ra | Không tự thêm tuổi, số người, trái/phải, cỡ cảnh/góc máy mặc định; giữ tiếng Việt và khoảng trắng; bỏ câu hỏi chưa trả lời/trường trống; đủ mười mục lựa chọn; không mutate scene/context |
| API prompt/provenance | Prompt trong record đúng prompt provider nhận, version mới; không trộn hành động cảnh khác hoặc M1 hiện tại đã đổi với context nguồn; prompt/version legacy giữ nguyên; không đổi scene, selection, nguồn phản hồi M1 hay gọi model văn bản |
| Frontend production build/TypeScript | Đạt; cảnh báo CSS `start` hiện có |
| Node contract/progress/onboarding | Đạt |
| Chrome `scene-sketch.browser.cjs` | Đạt: đúng version mới, prompt có nội dung cảnh, không JSON object dump; UI đối chiếu hiển thị đúng prompt đã lưu; đóng/mở details không đóng popover. Đồng thời qua giữ/bỏ, preview mới/ảnh cũ, chủ động thay, mất response không tăng lượt, reload, ID/order/nguồn cũ, timeout, buffer, tệp thiếu không chặn bàn giao và 1280/390/320px |
| `git diff --check` và hash plan/prototype/config | Đạt |

Test API mới lúc đầu so sánh cả revision bàn giao như nội dung bất biến nên lỗi. Đã sửa kỳ vọng: checkpoint ảnh tăng revision dự án là đúng, còn scene/source/version/thứ tự/lựa chọn văn bản giữ nguyên. Không sửa cơ chế revision để chiều test.

Các test dùng provider giả/DB tổng hợp riêng. Đợt này **0 lượt model thật, 0 API trả phí**; không chạy lại hay ghi đè các bộ thử ảnh đã đóng băng trước đó. Không cần dùng ảnh tạo mới để xác nhận hợp đồng ghép câu/lưu nguồn. Các ví dụ prompt runtime và hash nguồn được lưu tại [samples](../evaluations/scene-sketch-runtime-prompt-2026-10-27/samples.json), [manifest](../evaluations/scene-sketch-runtime-prompt-2026-10-27/manifest.json).

## Giới hạn còn cần kiểm chứng

Đã xác nhận cơ chế runtime lấy đúng dữ liệu từng cảnh và giữ các hợp đồng kỹ thuật. **Chưa xác nhận chất lượng ảnh từ bộ ghép câu tự động.** Những ảnh tốt hơn ở các đợt trước dùng prompt viết thủ công riêng cho ca mẹ–con; không chuyển các kết quả đó thành bằng chứng nghiệm thu formatter tổng quát.

Nguồn tiếng Việt giữ nguyên, không tự dịch; kiểm tra text có mặt trong prompt không chứng minh MFLUX hiểu đúng tiếng Việt. Không suy ra tuổi, số người, ánh nhìn hoặc trạng thái vật từ nội dung mơ hồ, và không bảo đảm model sẽ tuân thủ mọi chỉ dẫn. Các câu trích dẫn vẫn có thể bị model vẽ thành chữ; chưa có lượt thật cho format mới để xác nhận đã hết vấn đề đó.

Chưa nghiệm thu Gói 4/M2 đầy đủ hoặc người dùng, không triển khai M3, không hạ tiêu chí hoặc đổi plan. Nếu kiểm chứng ảnh thật tiếp, cần một bộ cảnh/prompt/config đóng băng và ngân sách riêng; không dùng lại quota 2 lượt của đợt prompt thủ công trước. Chưa tạo PR.
