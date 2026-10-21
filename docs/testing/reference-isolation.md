# Tách ví dụ khỏi dữ kiện sáng tác

## Nguyên nhân và phạm vi sửa

Trên `dev` trước bản sửa, planner của 7B nhận nguyên cốt truyện từ
`domains/short-film/examples`, các `beginner_example` trong glossary/rules và
các mẫu diễn biến trong `story_patterns`. Nhiều mục cùng kể chuyện cha–con,
sân bay và lời xin lỗi. Prompt mentor/critic còn chứa các tình huống hiệu chỉnh.
Lỗi được quan sát là model đưa quan hệ và tình tiết của ví dụ vào đề tài
không liên quan; critic tiếp tục khuyến khích diễn biến đã bị lệch.

Đây là nhiều nguồn dữ liệu tham khảo cạnh tranh với brief, không chỉ một câu
prompt thiếu cảnh báo. Profile 3B đã bỏ khối knowledge/examples ở planner,
nhưng vẫn dùng critic chung có ví dụ hiệu chỉnh.

Bản sửa:

- Không nạp cốt truyện mẫu vào planner. Không gửi `story_patterns`.
- Chỉ chọn các trường định nghĩa/hướng dẫn của glossary và rules; không gửi
  `beginner_example` hay trường tham khảo mới vô tình được thêm sau này.
- Chuyển tình huống hiệu chỉnh mentor/critic sang
  [tài liệu offline](prompt-calibration-examples.md). Giữ quy tắc chung trong prompt.
- Planner mặc định yêu cầu đánh dấu đề xuất thay vì coi quan hệ, tiểu sử hoặc
  kết quả chưa biết là sự thật.
- Giữ nguyên brief, câu trả lời, ngôn ngữ và bản thảo hiện tại. Không lọc tên
  Linh, sân bay hoặc chi tiết mà tác giả thật sự chọn.

Đây là sửa đường truyền ngữ cảnh. Nó không phát hiện mọi sự kiện model tự bịa,
không thay thế kiểm tra tính trung thành và không bao gồm PR #18.

## Kiểm thử tự động

`backend/tests/test_reference_isolation.py` kiểm tra cả profile 3B, 7B và model
khác: không gọi loader ví dụ, không lọt dữ kiện đánh dấu trong glossary/rules,
giữ câu trả lời và nội dung sửa mới nhất. Có ca đối chứng tác giả chủ động chọn
Linh, cha, sân bay và móc khóa để phát hiện việc lọc sai dữ kiện hợp lệ.

Chạy từ `backend`:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check app/application/workflow.py scripts/check_reference_isolation.py tests/test_reference_isolation.py tests/test_generate_workflow.py tests/test_qwen_prompt_profile.py
```

## Kiểm thử model thật

```sh
PYTHONPATH=. .venv/bin/python scripts/check_reference_isolation.py --output /tmp/reference-isolation.json
```

Mặc định chạy tuần tự `qwen2.5:3b` và `qwen2.5:7b`, nhiệt độ 0.3, ngữ cảnh
16384, timeout 180 giây mỗi lời gọi. Hai brief tổng hợp nằm trong
`demo/evaluations/reference-isolation-cases.json`: quan sát tiệm sửa xe
và chuyện cha–con do chính tác giả chọn. Các fixture này được viết để kiểm thử,
không lấy từ dự án của người dùng. Script gọi planner rồi critic qua
service thực tế, lưu prompt/input/output/thời gian; không ghi vào dự án.

`status=completed` chỉ xác nhận lời gọi và schema thành công. Người review phải
đọc đầu ra theo `review_checks`, phân biệt chi tiết do tác giả chọn với ví dụ
lọt vào, đồng thời ghi riêng các sai lệch khác. Không dùng blacklist tên riêng
hoặc điểm tự chấm của model để kết luận chất lượng đạt.

## Kết quả ngày 2026-10-21

225 kiểm thử backend đạt; Ruff và `git diff --check` đạt. Bằng chứng được đưa
vào repo chỉ gồm bốn lượt planner + critic trên hai fixture tổng hợp (tám lời
gọi, không timeout/lỗi schema). Đầu ra và hash request nằm trong
`demo/evaluations/reference-isolation-results.json`. Payload của dự án người
dùng được giữ local, không đưa vào commit hay PR.

| Model | Fixture | Lập kế hoạch (giây) | Góp ý (giây) |
|---|---|---:|---:|
| qwen2.5:3b | repair-shop | 15.7 | 12.9 |
| qwen2.5:3b | author-family | 20.3 | 28.9 |
| qwen2.5:7b | repair-shop | 86.1 | 39.2 |
| qwen2.5:7b | author-family | 93.5 | 44.1 |

Đọc thủ công: không tái hiện cốt truyện cha–con/sân bay trong đề tài tiệm sửa
xe trên cả hai model. Ở fixture cha–con, cả hai model vẫn giữ Linh, cha, sân
bay và móc khóa. Đây là quan sát một lượt mỗi ca, không chứng minh model sẽ
không bao giờ tự bịa.

Các lỗi còn lại phải tách khỏi kết quả sửa đường truyền ví dụ:

- 3B/sửa xe: critic còn chép câu placeholder tiếng Anh từ mẫu định dạng và
  đòi thêm tiểu sử cho phim quan sát. Bản sửa này chỉ loại tình tiết ví dụ,
  chưa thay hợp đồng/định dạng critic.
- Ca đối chứng: 3B đổi việc trả móc khóa thành giữ móc khóa; 7B tự thêm du học
  và cuộc gặp sau thời gian dài. Không có bộ lọc dữ kiện tác giả, nhưng chất
  lượng diễn giải vẫn chưa bảo đảm trung thành.
- Critic 7B chấm đạt và không nêu vấn đề trong hai ca; không xem điểm tự chấm
  này là tiêu chí nghiệm thu.

Thời gian có cả xử lý prompt/nạp model, không có seed cố định và không được
đo lặp. Không suy ra tăng tốc hay mức cải thiện chất lượng tổng thể từ bảng.
Không kiểm thử UI/mất kết nối trong PR này; API lưu dự án không thay đổi.
PR #18 vẫn mở, không được merge hay đưa vào nhánh này.
