# Vai trò tác giả và góp ý có bằng chứng — Qwen 7B

## Thay đổi

- Planner đối chiếu người thực hiện/người nhận hành động và giai đoạn giữ vai trò; không suy từ việc tham gia/hoàn thành thành thành tích, được tuyển hoặc bị loại.
- Critic ưu tiên dữ kiện tác giả, phân biệt kết quả chưa biết với kết quả đã xác nhận. Bỏ mẫu trả lời mặc định `passed=true` và điểm 4 đồng loạt.
- Rút gọn rubric, đặt trước dữ kiện và bản thảo để hướng dẫn chung không lấn át lựa chọn tác giả.
- Hợp đồng nội bộ yêu cầu mỗi nhận xét có phần, trích dẫn, lý do; mỗi vấn đề chứa đề xuất sửa. Runtime kiểm tra trích dẫn trong đúng bản hiện tại và nguồn tác giả. Không tự sửa bản thảo.
- API và dữ liệu dự án giữ định dạng findings hiện tại; dataset hỗ trợ cả hợp đồng cũ và mới. Phản hồi không hợp lệ trả lỗi, giữ nguyên phiên bản đã lưu.

Đây không phải cổng kiểm tra tính trung thành của PR #18. Kiểm tra vị trí trích dẫn không chứng minh suy luận hoặc đề xuất là đúng.

## Cách chạy

```sh
cd backend
PYTHONPATH=. .venv/bin/python scripts/check_author_roles.py --model qwen2.5:7b --output /tmp/author-role-final-results.json
```

Ollama `qwen2.5:7b`, temperature 0.3, context 16384, timeout 180 giây. Mỗi ca chạy một lần trên phiên bản cuối; không phải thống kê độ tin cậy. Thời gian đo cả lời gọi provider, không phải chỉ thời gian sinh token.

Bốn ca tổng quát trong `demo/evaluations/author-role-cases.json` không chứa dữ liệu dự án riêng. Dữ liệu kiểm thử dự án thật chỉ lưu cục bộ. `status=completed` chỉ xác nhận schema và kiểm tra trích dẫn; nghiệm thu nội dung phải đọc riêng theo `review_checks`.

## Giới hạn

Các lượt thử trước đã cho thấy: chỉ sửa prompt vẫn có thể đảo vai, tự suy kết quả chưa biết thành thất bại, hoặc đòi thêm xung đột. Hợp đồng chuỗi cũ còn chấp nhận tên phần, câu trích và nhận xét thành các mục rời. Hợp đồng mới chặn cấu trúc đó và bằng chứng không có nguồn, nhưng không tự phát hiện mọi nhận xét sai ngữ nghĩa. Một phản hồi bị chặn có thể làm lượt lập kế hoạch/góp ý thất bại; hiện không có retry hoặc sửa tự động.

Các kết quả PR20 là lịch sử, không dùng làm bằng chứng chất lượng của prompt mới. Công cụ so sánh critic chuỗi cũ chỉ dành cho `--experimental-critic`; bộ chạy trên dùng hợp đồng hiện tại.

## Kết quả phiên bản cuối

| Ca | Thời gian | Kết quả kỹ thuật | Đánh giá nội dung |
| --- | --- | --- | --- |
| mentor-plan | Plan 102,931 s; critic 85,109 s | Critic bị chặn vì `Character` không phải tên phần thật | Giữ người hướng dẫn và kết quả chứng chỉ chưa biết; vẫn tự thêm khóa học nâng cao và việc hoàn thành khóa học. Critic chưa bắt đúng lỗi đó. |
| reversed-role-invented-outcome | 30,068 s | Bị chặn vì `Character` / `Conflict` không tồn tại | Bắt thành tích tự thêm, nhưng khen việc đổi người hướng dẫn thành học viên; đề xuất vẫn đi theo vai sai. Chưa đạt. |
| corrected-open-ending | 39,657 s | Bị chặn vì dùng tên tiêu chí rubric làm tên phần | Giữ vai trò và kết quả mở trong lời khen, nhưng vẫn ép thêm xung đột. Chưa đạt. |
| confirmed-outcome-en | 38,719 s | Bị chặn: `Logline` khác tên trường nguồn `logline` | Giữ chứng chỉ đã xác nhận và tiếng Anh, nhưng đòi thêm thử thách/chứng minh năng lực. Hợp đồng tên phần còn gây từ chối vì khác chữ hoa. |

**0/4 lượt hoàn thành qua kiểm tra runtime; chưa đạt nghiệm thu chất lượng.**
Không dùng số kiểm thử unit qua để che kết quả này. Bản sửa hiện chặn bằng chứng
không hợp lệ và bỏ mẫu khen mặc định; chưa chứng minh 7B phát hiện đúng mọi sai vai
hoặc ngừng tự thêm chi tiết. Các gợi ý có trích dẫn thật vẫn có thể sai.

PR nên giữ trạng thái Draft. Trước khi merge cần đạt các ca đảo vai và bản sửa đúng,
đồng thời giảm từ chối tên phần hợp lệ về nghĩa mà không cho phép trích dẫn sai vị trí.
Không tiếp tục thêm từ khóa riêng cho một câu chuyện. Cần đánh giá hợp đồng/khả năng
đối chiếu của model bằng bộ ca này; PR #18 vẫn độc lập và chưa merge.

## Kiểm thử mã

- Kiểm tra trích dẫn cũ, bịa, sai phần, nguồn tác giả bịa; chuỗi khen chung không đủ cấu trúc.
- Review lỗi không thay đổi phiên bản đã lưu; phản hồi gắn vào bản đang được review.
- Tương thích sửa dataset hợp đồng cũ/mới và replay demo; giữ thuật ngữ, ngôn ngữ đích.
- Replay bằng chứng tổng quát kiểm tra hash prompt/input và tái hiện kết quả runtime, không chấm chất lượng bằng cách dò từ khóa.
- Lint các tệp thay đổi qua. Lint toàn repo còn ba lỗi có sẵn ngoài phạm vi ở `health.py`, `core/__init__.py`, `core/harness/__init__.py`.

## Đối chiếu dự án cục bộ (không công bố dữ liệu)

Lượt lập kế hoạch: 108,186 s; critic: 93,383 s. Vai trò hướng dẫn đã được giữ ở
phần diễn biến và không còn thành tích “xuất sắc”, nhưng vẫn rút gọn thiếu một
giai đoạn và khẳng định một nhánh kết quả chưa được tác giả xác nhận. Critic lần
này phát hiện sai kết quả, song gắn một câu vào sai phần và tự tạo bằng chứng tác
giả; runtime chặn phản hồi. Đây là cải thiện một phần, chưa phải ca đạt.

Review bản đã sửa: 63,453 s. Nhận xét giữ vai trò hướng dẫn và kết quả mở, không
lặp lại kết quả sai của bản vừa sinh; vẫn ép thêm biến cố và gọi phần không tồn
tại `Character`, nên bị chặn. Không có thay đổi vào dự án đã lưu trong các phép
thử model này. Tổng kiểm thử backend cuối: **247 passed** (một cảnh báo deprecation
Starlette có sẵn).
