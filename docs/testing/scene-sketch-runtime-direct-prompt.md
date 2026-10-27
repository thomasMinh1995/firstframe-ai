# Gói 4 — tích hợp prompt mô tả trực tiếp

Ngày 27/10/2026, nhánh `feat/scene-staging-handoff`. Chỉ tích hợp formatter và kiểm chứng; chưa commit hoặc tạo PR.

## Thay đổi

Runtime dùng `scene-sketch-direct-v3`: nối trực tiếp hành động, nhân vật, nơi chốn, thời gian, các lựa chọn dàn cảnh, ý đồ và ràng buộc. Bỏ câu dẫn từng trường và dấu trích bao quanh giá trị do hệ thống thêm. Không xóa dấu trích vốn thuộc nội dung tác giả, không dịch/tóm tắt nguồn, không thêm lượt model hoặc hardcode ca thử.

Thứ tự lựa chọn dàn cảnh cố định, không phụ thuộc thứ tự key JSON. Câu hỏi và trả lời đã xác nhận đi cùng nhau; câu hỏi chưa trả lời không được đưa vào. Yêu cầu tinh chỉnh đứng trước giới hạn cảnh/tác giả; khi có tinh chỉnh, prompt nhắc ưu tiên giới hạn nguồn. Nếu cảnh có màu, giữ mô tả màu và yêu cầu chuyển thành sắc độ chì. Những nhánh này được kiểm tra hợp đồng, chưa được thử ảnh thật trong đợt này.

Giữ đoạn phong cách nét chì và giới hạn không tự thêm sự kiện/chốt kết. Prompt/version lịch sử v1 và visual-v2 giữ nguyên; chỉ lượt mới dùng direct-v3. Không di chuyển hay viết lại ảnh cũ.

## Bảo vệ dữ liệu

Không thay route, snapshot/revision, kiểm tra nguồn, checkpoint, quyền chọn giữ/bỏ, giới hạn ảnh hay provider. Test tiếp tục kiểm tra nguồn đổi khi đang chạy, kết quả về muộn sau khi bỏ, xung đột lưu, mất phản hồi không gọi thêm ảnh, file thiếu/lỗi, đường dẫn UUID, giới hạn số ảnh, khóa tiến trình và timeout. Database/ảnh QA riêng, provider giả; không dùng dữ liệu tác giả để chạy model.

Plan, roadmap, prototype và cấu hình local được so hash trước/sau và giữ nguyên. Tham số model giữ nguyên: 768×432, 9 bước, seed 42, giới hạn 180 giây; model/revision/runtime giống đợt thử trước.

## Kiểm chứng

- Test tập trung prompt/API: **26 passed**.
- Toàn bộ backend: **429 passed, 1 skipped** trong 124,96 giây.
- Build production frontend, kiểm tra TypeScript/lint: **đạt**; đã build lại cấu hình mặc định sau QA.
- Contract transport, progress và tour: **đạt**.
- Chrome với provider giả: **đạt**, gồm xem prompt, xem trước/giữ/bỏ, giữ lựa chọn cũ khi tạo thêm, tải lại, nguồn cũ không được chọn mới, timeout, giữ ghi chú chưa lưu, ảnh thiếu vẫn bàn giao text; độ rộng 1280/390/320.
- `git diff --check`: **đạt**.

Build có cảnh báo CSS `start` nên dùng `flex-start` trong `storyWorkspace.css` đã có; pytest cảnh báo Starlette/httpx deprecated. Không phát sinh dependency hay xử lý ngoài phạm vi để dọn các cảnh báo này.

## Nối với bằng chứng model đã lưu

Lưu [bốn mẫu từ formatter runtime](../evaluations/scene-sketch-runtime-direct-2026-10-27/samples.json) và [manifest/hash](../evaluations/scene-sketch-runtime-direct-2026-10-27/manifest.json). Test fixture xác nhận prompt runtime của hai cảnh sửa xe/sân ga **khớp từng ký tự** với prompt thí nghiệm mô tả trực tiếp đã chạy MFLUX. Tham số provider cũng khớp baseline. **Không gọi thêm model thật trong đợt tích hợp này.**

[Kết quả hai lượt thật trước đó](scene-sketch-direct-two-scenes.md) cho thấy không còn chữ trên cả hai ảnh, bố trí cảnh sửa xe tốt hơn. Đây là bằng chứng giới hạn trên hai cảnh tổng hợp tiếng Anh; không phải nghiệm thu chất lượng ảnh tổng quát. Cỡ cảnh, bình minh, dây phanh, vị trí sân ga và dấu hiệu khóa vẫn chưa đạt/chưa rõ. Việc nối đúng prompt không bảo đảm model luôn tuân thủ mọi ràng buộc; tác giả vẫn xem trước rồi tự chọn giữ/bỏ.
