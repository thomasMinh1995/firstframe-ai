# BK-01 · Bộ ca đọc kịch bản và lời thoại Việt

Phiên bản đề nghị duyệt ngày 24/11/2026. Hai ca phát triển dành cho PR 3. Ca giữ lại dành cho đánh giá độc lập sau khi chốt bản sửa. Biên kịch hoặc chủ sản phẩm xác nhận nguồn, điều phải giữ và tiêu chí đọc trước khi dùng làm baseline.

| Ca | File | Điểm cần đọc |
|---|---|---|
| BK01-D01 | [Ổ khóa tầng ba](development.md#bk01-d01--ổ-khóa-tầng-ba) | Chất liệu đời thường, hàm ý trong quan hệ cô/cháu, kết để mở. |
| BK01-D02 | [Bốn mươi cái ly](development.md#bk01-d02--bốn-mươi-cái-ly) | Hiểu lầm nhỏ giữa đồng nghiệp, sự hài hước đến từ hành động và nhịp nói. |
| BK01-H01 | [Đèn máy in](holdout.md) | Cảnh quan sát không thoại, diễn tiến nhìn thấy được và điểm dừng rõ. |

Các brief, nguồn cảnh kiểm soát và đoạn mẫu được viết mới cho FirstFrame, là tình huống hư cấu. Có thể dùng trong test nội bộ của repo. File phân biệt dữ kiện tác giả giả lập, lời thoại minh họa và kết quả model sẽ thu ở PR sau. Hai đoạn trước–sau minh họa cách đọc lỗi. Người viết có thể tìm cách diễn đạt khác nếu vẫn giữ ý đồ.

## Đường chạy khi đo baseline

1. Tạo dự án thử cho từng brief phát triển. Nhập phần **Brief** và ràng buộc đã chốt. Chỉ dùng phần **Trả lời nếu được hỏi** để trả lời đúng câu hỏi xuất hiện. Ghi câu để mở, dữ kiện model tự thêm và câu hỏi đã được trả lời ngay trong brief.
2. Qua Làm rõ → Story plan → sửa một chi tiết có lý do → lưu → góp ý trên bản đã sửa. Ghi đoạn trước/sau và nguồn góp ý. Chấm plan theo hành động có thể hình dung, diễn tiến và ý đồ, rồi chấm lời thoại ở bản cảnh.
3. Để đọc riêng writer, dùng dàn cảnh kiểm soát tương ứng, theo thứ tự đã ghi. So sánh trên cùng nguồn và ngôn ngữ `vi`. Ghi kết quả từng cảnh và đọc thoại thành tiếng. Lượt này đo viết cảnh trên dàn cảnh cố định. Kết quả bước 2 đo đường từ brief đến plan và góp ý.
4. Ghi SHA, model và digest nếu có, hash prompt, tham số, lần gọi, thời gian, phí nếu có và toàn bộ kết quả kể cả lỗi. Chốt cấu hình, ngân sách và cách lưu bằng chứng trước khi chạy model ở PR 3. Đọc hai ca phát triển trước khi chọn tối đa hai nhóm lỗi để sửa.

Ca giữ lại nằm trong file riêng để tránh gửi nhầm vào lượt phát triển. Chạy đối chiếu bản nền và bản sửa sau khi đã chốt thay đổi; giao kết quả cho người đọc độc lập. Nếu đội dùng ca đó để tiếp tục chỉnh prompt, chuyển trạng thái ca sang phát triển và bổ sung ca giữ lại khác.

## Phiếu đọc dùng chung

| Tiêu chí | Cách đối chiếu |
|---|---|
| Ý đồ và quyền quyết định | Trích chi tiết trong brief hoặc câu tác giả đã trả lời. Chỉ ra đề xuất model nào hữu ích, dữ kiện nào bị gán nhầm hoặc lựa chọn nào bị chốt hộ. |
| Diễn tiến | Theo dõi vị trí người, đạo cụ và điểm dừng theo cảnh. Đánh dấu động tác bị lặp, kết quả chưa xảy ra bị kể là đã xảy ra, hoặc bước chuyển thiếu nguyên nhân. |
| Thoại và hàm ý | Đọc hai vai thành tiếng. Kiểm người nói, quan hệ, xưng hô, nhịp ngắt và câu giải thích điều hình ảnh đã cho thấy. Chấp nhận lược chủ ngữ, cách nói thân mật và phương án diễn đạt khác hợp vai. |
| Ích lợi của góp ý | Dẫn câu hoặc hành động cụ thể từ đúng bản đang được góp ý. Ghi một điều đáng giữ hoặc một lựa chọn sửa được. Cảnh im lặng được đánh giá qua động tác, âm thanh và khoảng dừng. |

Mỗi tiêu chí ghi **Đạt**, **Chưa đạt** hoặc **Không áp dụng**, kèm trích đoạn và lý do. Sai dữ kiện tác giả đã chốt, sai quan hệ hoặc tự viết vượt điểm dừng được ghi lỗi nguồn. Câu đúng nghĩa nhưng khó nói thành tiếng được ghi lỗi chất lượng. Khác biệt khẩu vị ghi riêng. Người đọc ghi chữ ký/ngày và kết luận từng ca, kể cả khi bằng chứng còn thiếu.

Mẫu ghi một dòng

```text
Ca / công đoạn / lượt / tiêu chí | kết luận | trích đoạn và nguồn | điều muốn giữ hoặc sửa | người đọc / ngày
```

Trạng thái duyệt nội dung đang chờ biên kịch hoặc chủ sản phẩm. PR này chuẩn bị dữ liệu và tiêu chí. Đo model thuộc PR 3, còn nghiệm thu với người dùng cuối thuộc R4.
