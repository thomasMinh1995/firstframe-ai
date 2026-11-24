# BK-02 · Baseline kịch bản và lời thoại Việt

Đo ngày 24/11/2026 trên `dev` tại `4747034e3aabb0082c5fe2a70b7320be5d135655` sau khi [BK-01 được merge](https://github.com/thomasMinh1995/firstframe-ai/pull/115). Đây là phép đọc kỹ thuật và nội dung của hai ca phát triển hư cấu. Người đọc độc lập sẽ đánh giá ca giữ lại ở lượt sau.

## Cấu hình và phạm vi

- Ollama ở localhost, model `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` trùng ở đầu và cuối lượt chạy. Nhiệt độ 0,3, ngữ cảnh 16.384 token và timeout provider 180 giây. Writer dùng `screenplay-scene-v25-bounded-reactions`. Request thực tế của cả bốn cảnh đi qua đường viết đầy đủ.
- Trần 12 lượt gọi và 12 phút. Dùng đủ 12 lượt, 503,62 giây trong provider và 549,56 giây toàn đợt, chi phí API 0. Một lượt cho mỗi request, gồm 2 Làm rõ, 2 planner, 4 critic và 4 writer.
- Hai brief từ [BK-01](../bk-01-writing-cases/README.md). Đi qua cùng route stream Làm rõ → Story plan → lưu một sửa đổi → góp ý. Dùng TestClient và SQLite/dataset riêng. Lượt writer dùng dàn cảnh kiểm soát và helper `prepare` của runner có sẵn, theo đúng thứ tự và truyền cảnh trước vào cảnh sau.
- Dữ liệu đầu vào chỉ gồm hai ca phát triển. Cả hai lượt làm rõ được trả lời từ dữ kiện đã chốt. Story plan không được dùng làm nguồn dàn cảnh của lượt writer riêng.

## Kết quả

| Công đoạn | BK01-D01 · Ổ khóa tầng ba | BK01-D02 · Bốn mươi cái ly |
|---|---|---|
| Làm rõ | Hỏi “Cách cô Tư giúp đỡ Ngân” dù phần tóm tắt đã ghi cô dùng đèn pin. | Hỏi lại quan hệ làm việc đã có trong ràng buộc. Tóm tắt đảo dữ kiện thành Bình “đặt bốn nắp ly giấy lên bàn”. |
| Story plan | Lưu được. Giữ hai người và cử chỉ đặt túi, nhưng đoạn kết dùng cảm ơn và cái nhìn để thay cho hành động soi ổ, thử chìa. | Lưu được. Logline giữ nghe nhầm “bốn ly” thành “bốn mươi”. Đoạn giữa kể nắp đã đặt lên ly rồi mới kể chị Hương quay lại với nắp trên tay. |
| Một sửa đổi đã lưu | Sửa đoạn kết để Ngân đặt túi xuống, thử xoay chìa dưới ánh đèn cô Tư và dừng khi cửa còn đóng. | Sửa đoạn giữa theo thứ tự Bình đếm xong, chị Hương trở lại với bốn nắp và Bình nhận ra ở cái nắp cuối. |
| Góp ý khi tạo plan và sau khi sửa | Cả hai lần bị guard từ chối. SQLite vẫn giữ đúng chữ và revision của bản đã sửa. | Cả hai lần bị guard từ chối. SQLite vẫn giữ đúng chữ và revision của bản đã sửa. |
| Writer trên dàn cảnh cố định | Đủ 2 cảnh hợp lệ về schema. Cả hai gán cho cô Tư câu “Cháu để ý thấy cô Tư mở cửa.” Cảnh cuối giữ túi trên gối và bỏ động tác đặt túi, thử chìa. | Đủ 2 cảnh hợp lệ về schema. Bình lặp câu có tiền tố tên người nói và lời “chỉ bốn ly thôi” dù nguồn là một dãy ly. Cảnh 2 lặp việc chị Hương quay lại sau khi đã đặt nắp. |

Góp ý có 4/4 phản hồi đọc được theo schema, 0/4 được guard chấp nhận. Replay trên đúng request đã gửi cho thấy cả bốn lần chọn `constraint-1` dù có `answer-0`. Guard báo `Card review did not compare any clarification answer.` Tách kết quả này khỏi đánh giá văn phong vì người dùng không nhận được góp ý sử dụng được. Writer qua kiểm tra kỹ thuật 4/4 cảnh và cả hai ca vẫn có lỗi nội dung theo phiếu đọc.

## Hai nhóm lỗi ưu tiên

1. **Giữ người nói, xưng hô và trạng thái cảnh khi viết.** Ưu tiên lỗi cô Tư nói bằng ngôi của Ngân và câu của Bình phủ nhận chính dãy ly đang thấy. Kiểm tiếp điểm dừng và đạo cụ ở cảnh sau. Dùng nguồn đã lưu và đoạn trước–sau để người đọc đánh giá lời thoại. Cho phép lược đại từ hoặc chọn câu khác phù hợp vai.
2. **Góp ý đối chiếu câu trả lời Làm rõ đã lưu.** Bắt đầu từ bốn request bị từ chối và xác nhận bước chấm tham chiếu đúng quyết định, đúng đoạn. Đối chiếu [PR #98](https://github.com/thomasMinh1995/firstframe-ai/pull/98) trước khi sửa. Bảo toàn guard nguồn và xác nhận ý nghĩa của trích đoạn, vì ID đúng vẫn có thể dẫn tới nhận xét sai.

Lỗi hỏi lại và sai thứ tự ở planner được ghi để theo dõi. Hai ca chỉ đủ để chọn lỗi cần sửa tiếp. Đánh giá độ tự nhiên của thoại vẫn cần người đọc thành tiếng và một lượt độc lập trên ca giữ lại.

## Bằng chứng

Tập evidence giữ tại thư mục workspace `artifacts/bk02-baseline-20261124`. Có adapter đã chạy, bộ input từ BK-01, cấu hình/digest, 12 cặp request–response, SHA-256 của system prompt từng request, sự kiện API, sửa đổi đã lưu, kết quả writer, SQLite kiểm thử và replay critic. Không đưa raw vào diff PR.

- `summary.json` ghi số call, thời gian, phí và kết quả từng nhóm.
- `BK01-D0*/plan-events.json`, `review-source.json`, `review-events.json` và `writer-*-result.json` chứa bằng chứng theo công đoạn.
- `critic-replay.json` ghi lý do từ chối cả bốn phản hồi. `replay-critic.py` kiểm trực tiếp guard và xác nhận hai bản sửa vẫn còn nguyên trong SQLite, không gọi model.
- SHA-256 của bảng kiểm `sha256.txt` là `0e78c8b7b411e4f2ba5439d7bdd21311657c3efeab888a073511bede6377f0fe`.
- Từ thư mục evidence, chạy `shasum -a 256 -c sha256.txt` để đối chiếu file. Dùng cùng checkout và helper đã lưu để tái lập. Hồi quy RED/GREEN của code không áp dụng cho PR báo cáo này.
