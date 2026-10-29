# QA-01 — review cuối PR #77, 29/10/2026

Ca đèn pin và lỗi diễn giải của v7 đã được sửa bằng cách thu hẹp trách nhiệm của model. Hai lượt API thực tế với `qwen2.5:7b` đều đạt **10/10 ca**: đúng cặp bằng chứng, không thêm cáo buộc, đúng nội dung hiển thị và giữ nguyên kịch bản. Đây là nghiệm thu kỹ thuật trên bộ ca phát triển đã lưu, không phải kết luận chất lượng tổng quát hoặc hoàn tất QA-01 phát hành.

## Thiết kế được kiểm tra

- Backend so khớp phủ định, toàn bộ vị ngữ và người/vật được nêu trực tiếp trong nguồn tác giả đã xác nhận. Khớp người nói với dialogue và nhân vật với action; ưu tiên giới hạn rõ ràng hơn ý tưởng chung. Đèn pin hỏng không làm ánh đèn đường trở thành vi phạm. Hai ca bổ sung phân biệt cửa sổ với cửa tủ và kiểm tra đối chứng được phép.
- Qwen chỉ trả một mã độ rõ cho từng đoạn đích; không chọn nguồn tác giả hoặc viết diễn giải. Backend tạo observation/impact bằng mẫu Việt/Anh cố định và lấy nguyên văn bằng chứng từ snapshot. Không dùng lời khen, số thứ tự do model bịa, gợi ý sửa hay câu hỏi do model sinh.
- Giữ nguồn đầy đủ, lịch sử cũ và public schema; không sửa các review v6/v7 đã lưu. Không đổi screenplay khi review. Đường đề xuất sửa có kiểm soát tiếp tục độc lập.
- Một call cho mỗi đoạn đích không rỗng, cùng deadline 60 giây bao gồm kiểm tra kết quả. Kiểm tra ngân sách toàn bộ nguồn trước khi bắt đầu; không tăng guard, cắt nguồn hoặc retry để đạt kết quả. Đoạn toàn khoảng trắng được lưu nhưng không gửi model.

## Kết quả chạy thật

| Chỉ số | Lượt 1 | Lượt 2 |
| --- | ---: | ---: |
| API HTTP 200 / số ca | 10/10 | 10/10 |
| Đúng cặp nguồn và nội dung hiển thị | 10/10 | 10/10 |
| Cáo buộc thừa / bỏ sót xung đột kỳ vọng | 0 / 0 | 0 / 0 |
| Lời góp ý ngoài kỳ vọng / CJK | 0 / 0 | 0 / 0 |
| Call model | 20 | 20 |
| Tổng thời gian model | 9.742s | 9.686s |
| Tổng model lâu nhất cho một review | 1.597s | 1.514s |
| Screenplay giữ nguyên | 10/10 | 10/10 |

Request lớn nhất là 2.009 byte; không có output bị cắt. Model Q4_K_M, digest và Ollama version lưu trong [model-info.json](model-info.json); review temperature 0, num_ctx 16384, num_predict 4096. Mỗi lượt dùng SQLite/data tạm riêng và model local, không gọi OpenAI. Hai lượt CLI đều exit 0. Các gate được khai báo trước hai lượt cuối, không retry từng ca lỗi.

[run-1](run-1/summary.json) và [run-2](run-2/summary.json) có raw calls, kết quả API và summary. [expectations.json](expectations.json) chứa tám ca cũ cùng hai đối chứng bổ sung trong [additional-inputs.json](additional-inputs.json). Các ca này đã được dùng khi phát triển, không phải bộ đánh giá độc lập. Hai mươi regression replay xác nhận input/prompt/schema khớp bản cuối và kết quả lưu có nguồn bất biến. Tái lập từ repository root: `backend/.venv/bin/python backend/scripts/check_review_context.py --output /tmp/firstframe-review-v8-new-run`, với Ollama và model mục tiêu đã bật; thư mục output phải chưa tồn tại.

Các thử nghiệm không đạt trong quá trình phát triển được giữ trong [development.json.gz](development.json.gz), đọc bằng `gzip -dc development.json.gz`. Bao gồm dữ liệu thô có sẵn và một số probe chỉ lưu nhãn đã parse; không coi mọi thử nghiệm là có bản ghi HTTP đầy đủ. Báo cáo v7 trước đó được giữ nguyên để đối chiếu thất bại.

## Kiểm thử kỹ thuật

Backend: **629 passed, 1 skipped**. Frontend: **15/15 bộ kiểm thử và TypeScript đạt**. `git diff --check` đạt. GitHub không có Actions/check/status thực thi; các kiểm thử được chạy local, không coi legacy pending với total_count=0 là CI đang chạy.

## Giới hạn còn lại

Đây là kiểm tra xung đột trực tiếp thận trọng, không phải suy luận ngữ nghĩa tổng quát. Bí danh, khác biệt thuộc tính không có vị ngữ chung (ví dụ áo đỏ/áo xanh), phạm vi mơ hồ hoặc nhiều chủ thể không chắc chắn sẽ không bị kết luận xung đột. Không có góp ý không đồng nghĩa tác phẩm tuân thủ toàn bộ ý đồ. Mã craft vẫn do model chọn nên chưa được chứng minh chính xác ngoài bộ ca này; mẫu hiển thị chỉ ngăn model thêm diễn giải không có nguồn. Người viết tiếp tục quyết định giữ hay yêu cầu sửa.

QA-01 phát hành vẫn cần người đọc độc lập, pilot và kiểm tra thiết bị/IME/screen reader/Safari. Trường `release_acceptance` trong raw summary được giữ nguyên trạng thái pending, phù hợp giới hạn đó. PR có thể merge kỹ thuật vào dev để sửa lỗi đã tái hiện; không đánh dấu toàn bộ QA-01 hoàn tất.
