# BK-04 · Diễn tiến và đạo cụ giữa hai cảnh

Đo ngày 24/11/2026 từ `dev` tại `ace12f66874805bc6b630466c779355cd0cd8007`. Hai đầu vào cảnh thứ hai lấy từ [BK-02](../bk-02-baseline-2026-11-24/README.md), gồm cùng dàn cảnh, brief và cảnh trước đã viết.

## Phạm vi

Khi viết một cảnh tiếng Việt còn trống ngay sau một cảnh có hành động đã lưu, writer dùng các nhịp hành động có sẵn nếu tác giả đã viết hoặc xác nhận hành động của cảnh đích và nguồn đáp ứng điều kiện dựng cảnh. Ứng dụng ghép nhịp theo thứ tự. Model có thể đề xuất thoại theo vai ở giữa các nhịp khi phù hợp. Cảnh yêu cầu im lặng có giới hạn thoại bằng 0. Bản đề xuất vẫn cần tác giả chọn dùng.

Quy tắc mới áp dụng khi không có yêu cầu viết lại. Các trường hợp như sửa khối, đổi staging và cảnh thiếu hành động đủ rõ đi qua đường viết hiện có. Phiên bản writer mới dùng cơ chế kiểm tra tiếp tục lượt tạo tự động có sẵn. Lượt dở ở phiên bản cũ vẫn đọc được bản đã lưu và cần một lượt mới để gọi AI tiếp.

## Trước và sau

Ollama localhost với `qwen2.5:7b`, cùng digest BK-02, nhiệt độ 0,3, ngữ cảnh 16.384 và timeout 180 giây. Bốn lượt gọi mất khoảng 1 phút 43 giây, phí API 0. Mỗi bản viết cùng hai cảnh, mỗi cảnh gọi một lần. Hai đầu vào trùng nhau ngoài nhãn phiên bản writer gắn với từng bản.

| Cảnh kế tiếp | Trên dev | Sau BK-04 |
|---|---|---|
| BK01-D01 · Ổ khóa tầng ba | Giữ túi trên tay, bỏ việc đặt túi và thử chìa. | Đủ bốn nhịp theo dàn cảnh, gồm Cô Tư soi đèn, Ngân đặt túi rồi thử chìa và cửa còn đóng. |
| BK01-D02 · Bốn mươi cái ly | Lặp việc Hương quay lại, bỏ điểm Bình nhận ra ở cái nắp cuối. | Đủ bốn nhịp theo dàn cảnh, gồm Hương đặt nắp, Bình nhận ra ở cái nắp cuối và dãy ly dư còn nguyên. |

Kết quả khớp toàn bộ nhịp hành động theo thứ tự tăng từ 0/2 lên 2/2. Phần thoại vẫn có lỗi: Cô Tư lặp câu xưng “cháu” và Chị Hương bảo Bình đặt nắp ngay sau khi mình đã đặt. Chất lượng thoại và nghiệm thu với người dùng thật vẫn cần đánh giá ở các bước sau.

## Kiểm tra và bằng chứng

- Hai ca test hồi quy đều đỏ trên dev do nhận lại hành động cảnh trước và tự mở đạo cụ còn niêm phong. Sau sửa, cùng assertions qua cho cảnh có thoại và cảnh im lặng. Test cũng kiểm ID cảnh, nội dung nguồn và cách xưng hô từ BK-03.
- Replay offline hai phản hồi model xác nhận request và schema bản cuối trùng từng byte với lượt đo sau sửa. Kết quả có cùng ID cảnh và nội dung khối.
- `artifacts/bk04-scene-progression-20261124` trong workspace giữ adapter, bốn cặp request và response, kết quả, profile và log. Chạy `shasum -a 256 -c sha256.txt` từ thư mục đó để kiểm tệp bằng chứng model.
