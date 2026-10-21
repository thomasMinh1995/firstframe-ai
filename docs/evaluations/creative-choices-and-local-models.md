# Phần chưa quyết định và gợi ý sáng tạo — PR21

## Thay đổi

Phân biệt trong hướng dẫn cả ba bước:
- Đã chốt: dữ kiện trong ý tưởng, giới hạn và lựa chọn tác giả thực sự nhận.
- Chưa quyết định: chưa đủ cơ sở chọn; trì hoãn không xóa dữ kiện gốc. Kết mở có chủ ý là lựa chọn đã chốt.
- Gợi ý sáng tạo: cách kể có thể thử, cần nhãn tùy chọn; chỉ thành lựa chọn tác giả khi được chấp nhận.

Mentor có hợp đồng câu hỏi gồm một câu và đúng hai phương án không rỗng. Ứng dụng thêm nhãn tùy chọn và quyền chọn hướng khác/để sau. API vẫn dùng câu hỏi dạng chuỗi; chưa có giao diện chọn phương án riêng. Hợp đồng bảo đảm có phương án, không bảo đảm câu hỏi đúng ngữ cảnh.

Critic phân loại contradiction, open_choice, creative_proposal, craft. Hai loại tùy chọn chỉ xuất hiện ở phần gợi ý, không thành điểm yếu hoặc tự chặn bản thảo. Mâu thuẫn cần trích dẫn tác giả. Câu hỏi AI bị loại khỏi nguồn bằng chứng. Trích dẫn phải có thật trong đúng phần bản hiện tại; không có retry tự sửa dữ kiện.

Schema không gợi sẵn giá trị kind. Dữ liệu cũ thiếu kind vẫn đọc được như craft; dataset corrections giữ tương thích hợp đồng cũ/mới. Không di trú dữ liệu dự án; không triển khai routing model, không merge PR18. Nhãn trạng thái ở reasoning vẫn do model viết, chưa được bảo đảm bằng enum/giao diện riêng.

## Phương pháp và kết quả cuối

Ngày 2026-10-21, Ollama Qwen2.5 7B và 3B, temperature 0.3, context 16384, timeout 180 giây. Dùng cùng snapshot dự án riêng do người dùng cung cấp; phân tích lại, trả lời mọi câu hỏi bằng lựa chọn chưa quyết định, lập kế hoạch và góp ý. Không ghi vào kho dự án. Mỗi model có thể hỏi khác nhau và dùng profile riêng hiện có, nên đây là kiểm thử luồng, không phải so sánh kiểm soát mọi token giống nhau.

| Model | Hỏi bổ sung | Lập kế hoạch | Góp ý | Tổng ba bước | Kết quả runtime |
|---|---:|---:|---:|---:|---|
| 7B | 49,916 s | 141,315 s | 79,831 s | 271,062 s | Chặn trích dẫn tác giả sai nguồn |
| 3B | 26,431 s | 58,090 s | 75,444 s | 159,965 s | Chặn trích dẫn tác giả sai nguồn |

7B: đủ hai phương án/câu nhưng còn hỏi lại điều đã kể; một phần đã chốt bị gọi là chưa quyết định; nhãn trạng thái còn tiếng Anh. Planner rút gọn mất chuỗi hành động quan trọng, tự chốt cảm xúc. Critic dùng phương án trong câu hỏi chưa được chọn làm bằng chứng tác giả. Validator chặn đúng lỗi nguồn; không có phản hồi được chấp nhận từ lượt này.

3B: câu hỏi mở rộng sang biến cố/phương tiện không cần thiết; planner tự thêm tuổi/giới tính và phản ứng gia đình. Critic lấy câu bản thảo làm trích dẫn tác giả và gắn đề xuất thay đổi dữ kiện vào loại sáng tạo. Validator chặn bằng chứng sai. Không dùng JSON hợp lệ để kết luận nội dung đạt.

**Cả hai chưa đạt nghiệm thu chất lượng toàn luồng. PR giữ Draft.** Kiểm tra nguồn là hàng rào, chưa phải bộ xác minh ngữ nghĩa. Không tiếp tục thêm từ khóa riêng của dự án để làm đẹp một ca.

Lượt cuối dùng hợp đồng câu hỏi có cấu trúc và schema critic không có default kind. Sau lượt chạy chỉ chỉnh dấu chấm thừa khi hiển thị câu hỏi và ngôn ngữ nhãn trong trình biên tập dataset; không đổi prompt/model. Các lượt thử prompt trước đó là bằng chứng phát triển, không thay cho kết quả cuối.

Dữ liệu riêng giữ tại `/tmp/di-mua-vai-guided-final.json`, không đưa vào Git. Thời gian gồm overhead/load trên một máy, một lượt, không phải SLA. Bộ bốn ca tổng quát của commit 5095699 là bằng chứng lịch sử, chưa chạy lại với prompt hiện tại.

## 3B phù hợp với việc gì?

Thử thêm hai yêu cầu tổng hợp độc lập: đề xuất hai hình ảnh kết cho (1) người cháu vá áo tặng bà, (2) cha đón con sau lớp vẽ. Prompt yêu cầu tiếng Việt, nhãn tùy chọn, giữ dữ kiện và không thêm tiểu sử/biến cố. Output schema chỉ có options gồm hai chuỗi. Thời gian 4,499 s và 4,614 s.

Cả hai trả đủ hai mục, nhưng không ghi nhãn tùy chọn và chưa giải thích khác biệt cảm xúc. Ca thứ hai tự gán giới tính và lẫn tiếng Trung. Ca thứ nhất có hình ảnh khả dụng để cân nhắc, chưa đạt toàn bộ yêu cầu. Kết quả local: `/tmp/3b-small-creative-tasks.json`. Đây là thử nghiệm độc lập, chưa tích hợp thành feature.

| Feature | Khuyến nghị cho 3B |
|---|---|
| Đưa vài hình ảnh/cách diễn đạt cho một đoạn ngắn | Có thể thử có kiểm soát; ứng dụng gắn nhãn gợi ý, người dùng chọn; chưa đủ bằng chứng để phát hành tự động |
| Đề xuất tên phim hoặc biến thể giọng điệu | Ứng viên thử nghiệm tiếp; lượt này chưa kiểm thử |
| Tóm tắt dữ kiện, hỏi bổ sung toàn câu chuyện | Chưa giao tự động: đã thấy đổi chi tiết và hỏi sai trọng tâm |
| Lập kế hoạch toàn truyện | Chưa đạt: tự thêm tuổi/giới tính, động cơ và bỏ hành động quan trọng |
| Kiểm tra tính trung thành, chấm điểm, góp ý sửa | Chưa đạt: nhầm nguồn và gợi ý thay dữ kiện |
| Lưu/phiên bản, nhãn giao diện, xuất PDF | Không cần model; làm bằng mã ứng dụng |

Hướng tiếp theo: giới hạn từng tác vụ vào một lựa chọn/đoạn, hiển thị nguồn và để tác giả xác nhận trước khi cập nhật điều đã chốt. Đánh giá trên nhiều ca tổng quát, không tự nâng gợi ý AI thành dữ kiện. Chưa thêm tầng gọi model phụ hoặc tự động chuyển model trong PR này.

## Kiểm thử mã

259 tests passed; Ruff các tệp Python thay đổi và diff whitespace qua. Có ca kiểm tra hai phương án không rỗng, gợi ý tùy chọn không thành điểm yếu, mâu thuẫn cần nguồn, câu hỏi AI không là bằng chứng, phản hồi lỗi không ghi đè bản lưu, dataset cũ/mới. Một cảnh báo deprecation Starlette hiện có. Kiểm thử mã không chứng minh chất lượng suy luận model.
