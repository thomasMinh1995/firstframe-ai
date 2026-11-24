# BK-03 · Ngữ cảnh nhân vật khi viết cảnh

Kiểm ngày 24/11/2026 trên nhánh `codex/ff-sb-04-character-context`, từ `dev` tại `8f695f3a9376ffecf920ba022d244b912d00ca5f`. Đối chiếu [baseline BK-02](../bk-02-baseline-2026-11-24/README.md).

## Kiểm tra request

- Writer lấy brief và câu trả lời từ snapshot đã lưu của kịch bản. Luồng viết đầy đủ gửi cách tự xưng theo tên người nói khi đọc được lựa chọn rõ ràng. Với cảnh hai người, gửi thêm cách gọi người kia nếu tác giả đã chỉ rõ. Lựa chọn tùy ý vẫn nằm trong brief gốc.
- Hai luồng viết đưa câu Làm rõ chưa trả lời vào `unanswered_questions`, bên ngoài `author_intent`. Writer có chỉ dẫn để câu hỏi mở và có thể viết tiếp. Đề xuất của AI ở bước Làm rõ không đi vào request dưới dạng quyết định tác giả.
- Hai test request chạy đỏ trên `dev` vì thiếu dữ liệu và xanh với cùng assertions sau sửa. Test qua API dùng SQLite tạm để kiểm mục đích và xưng hô đã lưu. Test thứ hai đi qua luồng dựng cảnh theo hành động cố định. Test cũ về nguồn đã lưu và trần ngữ cảnh vẫn qua.
- Thêm phiên bản writer vào cấu hình lượt tạo tự động để dùng cơ chế chặn tiếp tục sẵn có khi prompt đã đổi. Test thứ ba tái hiện lượt cũ trên `dev`, sau sửa xác nhận lượt đó không gọi lại model và bản nháp đã lưu vẫn đọc được.

## Kết quả model local

Giữ digest và cấu hình BK-02 của `qwen2.5:7b` với nhiệt độ 0,3, ngữ cảnh 16.384 và timeout 180 giây. Tổng cộng 10 lượt trên hai ca phát triển, khoảng 5 phút 9 giây chạy các lượt thử, phí API bằng 0. Mỗi lượt gửi một request cho mỗi cảnh đã chọn. Lượt sau dùng cảnh đầu của chính lượt đó.

| Lượt | Kết quả đọc cảnh |
|---|---|
| 1 · Prompt chung ngắn hơn, 4 cảnh | Ca hành lang bỏ thoại, cảnh sau lặp đoạn mở và thiếu hành động cuối. Ca quầy ly dùng chị/em đúng vai ở các câu có tự xưng nhưng còn lặp thoại và nhầm chi tiết. |
| 2 · Yêu cầu bắt đầu từ hành động cảnh đích, 4 cảnh | Ca hành lang có câu gán nhầm ngôi “cháu” cho Cô Tư, rồi cho Cô Tư mở cửa và Ngân bước vào. Ca quầy ly lặp câu có tên người nói và dùng “anh Bình”. Loại cả hai lần sửa prompt chung. |
| Bản PR · Chỉ thêm chỉ dẫn khi có dữ liệu tương ứng, 2 cảnh gọi model | Cả hai cảnh hành lang hợp lệ và giữ đúng ID. Cô Tư gọi Ngân là “cháu” đúng vai, nhưng vẫn tự xưng “tôi” thay vì “cô”, lặp câu và thiếu thao tác cuối. Replay offline ca quầy ly xác nhận cả prompt lẫn JSON request của hai cảnh giống BK-02 từng byte. |

BK-03 đạt kiểm tra truyền ngữ cảnh. Chất lượng đầu ra còn lỗi, gồm giữ hành động giữa các cảnh (BK-04) và dùng đúng cách xưng hô trong thoại sinh ra (BK-05). Cả ba lượt dùng ca phát triển đã biết. Đánh giá độc lập và nghiệm thu người dùng thực hiện ở giai đoạn sau.

## Bằng chứng

Trong workspace, các thư mục `artifacts/bk03-character-context-20261124`, `artifacts/bk03-character-context-trial2-20261124` và `artifacts/bk03-character-context-final-20261124` giữ adapter, cấu hình, prompt trong request, toàn bộ phản hồi, kết quả và log. Dùng `shasum -a 256 -c sha256.txt` từ từng thư mục để kiểm tra bằng chứng model.
