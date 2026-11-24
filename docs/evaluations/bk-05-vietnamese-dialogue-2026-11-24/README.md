# BK-05 · Thoại tự chọn trong cảnh nối tiếp

Đo ngày 24/11/2026 từ `dev` tại `6647b6e12981a7d0df8190b3a535d4357e28412e`. Dùng cùng cảnh thứ hai và cảnh trước đã lưu từ [BK-02](../bk-02-baseline-2026-11-24/README.md), qua nhánh dựng cảnh [BK-04](../bk-04-scene-progression-2026-11-24/README.md). Ca giữ lại dành cho đánh giá độc lập.

## Kiểm soát bản đề xuất

- Chỉ dẫn tiếng Việt gắn câu nói với điều nhân vật muốn người kia hiểu, xưng hô và nhịp hành động đã tới. Cảnh vẫn có thể để im lặng.
- Bỏ nhãn người nói do model chép vào câu. Lọc câu dài trùng nguyên phần lời dù đổi tiếng gọi hoặc đổi người nói. Giữ lời ngắn thường được lặp và câu có trong tư liệu tác giả đã cung cấp.
- Khi một câu tự chọn trùng động tác hoặc vi phạm kiểm tra xưng hô sẵn có, giữ cảnh và các câu khác. Các quy tắc về thứ tự nhịp, yêu cầu thoại bắt buộc, sửa khối và văn bản tác giả đã lưu giữ nguyên. Bản đề xuất vẫn cần tác giả chọn dùng.

## So sánh cùng đầu vào

Ollama `qwen2.5:7b` giữ digest BK-02, nhiệt độ 0,3, ngữ cảnh 16.384 và timeout 180 giây. Mỗi bản có hai lượt gọi, một lượt mỗi cảnh. Sáu lượt của bản nền và hai lần thử mất khoảng 1 phút 37 giây, phí API 0.

| Ca | Bản nền | Bản chốt |
|---|---|---|
| BK01-D01 · Ổ khóa tầng ba | Model đặt các câu sai thứ tự nhịp, nên ứng dụng báo lỗi. Câu raw của Cô Tư xưng “cháu” và nhắc lại việc mở cửa đã qua. | Đủ nhịp, cửa còn đóng. “Cô xem thử, cháu ạ.” dùng đúng vai và tránh giải thích dài. |
| BK01-D02 · Bốn mươi cái ly | Hai người nói gần như cùng câu “em đã đếm rồi, chỉ bốn ly thôi”, trái với dãy ly dư. | Giữ đủ nhịp đặt nắp và điểm cắt. Ứng dụng bỏ hai câu model chép từ cảnh trước dù một câu đã đổi tiếng gọi và người nói. Cảnh còn phần hành động, chưa có câu thoại mới dùng được. |

Bản chốt dùng prompt lượt một. Lượt hai thử nhấn mạnh thứ tự và câu mới, nhưng Cô Tư tự xưng “mẹ” và chị Hương vẫn giao việc đặt nắp đã xong. Giữ toàn bộ hai lượt thử. Replay offline kiểm request, schema và kết quả với bản chốt, dùng đúng hai phản hồi của prompt đã chọn.

## Bản đọc và giới hạn

Đã tạo bốn bản đọc bằng giọng Việt Linh trên macOS, cùng bản chữ và vị trí hành động trong cảnh. Bản trước của D01 ghi rõ đây là thoại raw của đề xuất bị lỗi thứ tự. Đối chiếu văn bản cho thấy D01 có một câu hợp vai và D02 chưa có bằng chứng cải thiện độ tự nhiên. Bản đọc tổng hợp phục vụ nghe lại. Phiếu đọc của biên kịch hoặc người dùng thật vẫn còn chờ.

Bốn ca hồi quy từ cùng test đỏ trên dev và xanh sau sửa. Kiểm tra giữ câu dùng được, câu đáp ngắn và nguyên hành động ngay cả khi model gửi câu tùy chọn bị lỗi. Các test thoại bắt buộc, im lặng và nguồn cảnh vẫn qua.

Bằng chứng nằm trong `artifacts/bk05-vietnamese-dialogue-20261124` của workspace, gồm toàn bộ request và response, kết quả hai lượt thử, replay bản chốt và tệp `reading/*.aiff`. Kiểm bằng `shasum -a 256 -c sha256.txt` tại thư mục đó.
