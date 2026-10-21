# Issue #14: ngôn ngữ góp ý với Qwen 2.5 3B

Ngày kiểm thử: 21/10/2026. Nhánh sửa xuất phát từ `dev` tại `80495d2`.

## Thay đổi

Critic chọn prompt tiếng Việt đầy đủ khi ngôn ngữ đích là Vietnamese; các lượt
tiếng Anh giữ prompt hiện có. Cùng đường chọn này phục vụ góp ý sau tạo bản phát
triển, `/api/generate` và review bản đã sửa. Không rút gọn rubric, ngữ cảnh tác
giả hay bản thảo; không thêm lượt AI dịch lại, thử lại hoặc sửa nội dung tác giả.

Prompt Việt giữ các yêu cầu về bằng chứng, quyền quyết định của tác giả, cặp
góp ý và kết mở của prompt hiện có. Diễn giải dùng tiếng Việt, nhưng lab coach,
build phase, AI, VinUni, tên phần và trích dẫn được giữ nguyên. Không áp đặt từ
thuần Việt. Bộ nhận diện ngôn ngữ và nhãn giao diện thuộc issue #15.

Chỉ thêm lời nhắc ngôn ngữ vào cuối prompt tiếng Anh đã không đủ trong pilot:
Qwen vẫn có lượt trả diễn giải tiếng Anh. Vì vậy bản triển khai dùng bản dịch
đầy đủ, không bật candidate critic rút gọn từng bị loại trong đánh giá trước.

## Phương pháp và bằng chứng

- Ollama `qwen2.5:3b`, digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`,
  temperature 0.3, context 16.384. API dùng cấu hình runtime, không cố định seed.
- Phát lại đúng hai snapshot ban đầu/sau sửa của “AI chông gai” và hai snapshot
  tương ứng của ca tiếng Anh. Mỗi snapshot dùng seed 42 và 73: tám đầu ra.
  Ngữ cảnh, draft, schema không đổi. Output cũ được giữ làm bằng chứng lỗi,
  không phải baseline chạy cùng seed để so sánh chất lượng.
- Chạy hai workflow API thật trong SQLite và dataset tạm: tạo → nhập brief →
  analyze → xử lý câu hỏi nếu có → plan → sửa Ending → lưu → review → mở lại.
  Ca Việt chứa lab coach/build phase và câu trích “Keep learning.”; ca Anh sau
  sửa chứa câu trích “Cứ học tiếp.”. Tổng cộng bốn đầu ra critic. Không ghi lên
  dự án hoặc dataset đang dùng của người dùng.
- Chạy sáu tình huống critic đã có trong repo, seed 42, chỉ biến thể after với
  prompt runtime mới. Không bật `--experimental-critic`.
- Đọc thủ công mọi nhóm strengths/weaknesses/suggestions để xác định ngôn ngữ
  diễn giải; không dùng số từ tiếng Anh làm tiêu chí thuần Việt. Một tên phần,
  thuật ngữ hoặc trích dẫn tiếng Anh không bị coi là lỗi.

[Fixture phát lại](../../demo/evaluations/feedback-language-cases-2026-10-21.jsonl)
và [bằng chứng đầu ra](../../demo/evaluations/feedback-language-qwen-2026-10-21.json)
giữ input, schema, effective prompt/hash, raw output, tham số mô hình và các
kiểm tra API. Đây là dữ liệu hồi quy chưa duyệt chất lượng, không tự dùng làm
demo hoặc training.

## Kết quả

| Nhóm | Đúng ngôn ngữ diễn giải trong mẫu thử |
| --- | --- |
| Hai snapshot Việt × hai seed | 4/4 tiếng Việt |
| Hai snapshot Anh × hai seed | 4/4 tiếng Anh |
| Hai workflow API: ban đầu và sau sửa | 4/4 theo ngôn ngữ đích |
| Sáu tình huống hồi quy tiếng Việt | 6/6 tiếng Việt |

Tổng 18/18 đầu ra trong mẫu này giữ ngôn ngữ diễn giải. Thuật ngữ và tên phần
tiếng Anh vẫn xuất hiện hợp lệ. Các trích dẫn song ngữ được giữ nguyên trong
bản thảo gửi review và nội dung mở lại; không yêu cầu model phải trích lại chúng.

Cả hai workflow API xác nhận: draft không bị review sửa; ý tưởng và giới hạn
không đổi; phản hồi mới có ID mới và đúng khóa nội dung; phiên bản trước còn
nguyên; mở lại khớp chính xác bản sau lưu/review.

Kiểm tra tự động: **184 passed**, gồm toàn bộ test backend được Git quản lý và
test mới về ngôn ngữ. Ruff đạt trên các tệp Python thay đổi; `git diff --check`
đạt. Local có các bản sao chưa track tên `* 2.py` chứa kỳ vọng cũ; lượt `pytest`
không chọn file lúc đầu đã thu cả các bản sao và báo ba lỗi từ đó. Lượt xác nhận
184 test chọn toàn bộ file test được track cùng test mới, không sửa/xóa hoặc
commit các bản sao này. Có một cảnh báo deprecation TestClient/httpx hiện có.

## Giới hạn cần PO biết

Đúng ngôn ngữ không chứng minh góp ý đúng ý nghĩa. Lượt review Việt seed 42 có
ba điểm yếu nhưng sáu gợi ý. Có lượt vẫn đòi tiết lộ kết quả tuyển dụng trái
kết mở. Sáu ca hồi quy vượt kiểm tra cặp về cấu trúc nhưng còn các lỗi:

- quiet-waiting: đề nghị thoại và chuyển động trái lựa chọn im lặng/quan sát;
- apology-passport: vẫn giữ hành động giấu hộ chiếu khi đề nghị hướng chỉ xin lỗi;
- production-limit: chưa giải quyết đúng giới hạn phòng trọ/một người;
- deferred-choice: đề xuất mở thư thay vì giữ quyết định chưa chốt;
- silent-visual-story: góp ý chưa chỉ ra vấn đề có căn cứ;
- revision-conflict: bỏ sót mâu thuẫn chính ở phần kết.

Một số lượt còn chép cách diễn đạt mẫu chung thay vì phân tích chi tiết. Issue
#14 không được coi là sửa những lỗi này hoặc hoàn thành issue #7. Không có đánh
giá độc lập của tác giả, không kết luận chất lượng nghệ thuật đã tăng hoặc giữ
ngang baseline. Chưa chạy mô hình OpenAI thật; test fake kiểm tra việc chọn và
ghi nhận prompt xuyên provider. Mẫu thử hữu hạn không bảo đảm mọi lần sinh sau
đều tuân thủ ngôn ngữ; bộ nhận diện hiện tại vẫn có các lỗi thuộc issue #15.

## Chạy lại các lượt critic

Chạy từ thư mục gốc repo, chọn tên output mới để giữ bằng chứng trước:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/compare_ollama_prompts.py \
  --dataset demo/evaluations/feedback-language-cases-2026-10-21.jsonl \
  --output /tmp/feedback-language-replay-new.json \
  --seeds 42 73 --stages evaluation --variants after

PYTHONPATH=backend backend/.venv/bin/python backend/scripts/compare_ollama_prompts.py \
  --dataset demo/evaluations/critic-cases-2026-10-21.jsonl \
  --output /tmp/feedback-language-six-cases-new.json \
  --seeds 42 --stages evaluation --variants after
```

Script chọn prompt critic theo ngôn ngữ đích như runtime, giữ nguyên fixture
và schema, không ghi kho dự án hoặc duyệt dataset. Các chỉ số marker/cặp cấu
trúc trong script chỉ để sàng lọc; cần đọc output để kết luận ngôn ngữ và ý nghĩa.
