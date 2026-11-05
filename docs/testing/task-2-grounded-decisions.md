# Task 2.2a — Neo nhận định vào trích đoạn bản thảo

Ngày 05/11/2026, baseline `f77385c`, nhánh
`fix/screenplay-quality-and-feedback`. Theo [plan 2.2a](../plans/screenplay-quality-and-feedback.md),
tiếp [đợt checklist](task-2-decision-checks.md).

## Thay đổi kỹ thuật

Check cũ có ID card và lời giải thích nhưng chưa có bằng chứng rằng lời
giải thích đang đối chiếu đúng văn bản đó. Bản mới thêm `draft_quote` bắt
buộc vào phản hồi nội bộ; không thêm field dự án/public API/UI hoặc call.

- `aligned`/`mismatch` phải có trích đoạn nguyên văn thuộc card được dẫn.
  Quote bịa, lấy từ lựa chọn tác giả hoặc thuộc card khác bị từ chối.
  `uncertain`/`not_applicable` có thể không có quote khi không có căn cứ.
- Quote có thể đi qua một nhóm card liền nhau trong cùng đoạn nguồn nếu
  mọi card bị đi qua đều được dẫn. Giữ nguyên dấu câu/khoảng cách từ đoạn
  gốc bằng `card_spans()` hiện có; không nối tắt qua một card không dẫn.
- Tách shape có quote khỏi checklist 2.2a cũ. Request mới không nhận shape
  cũ; dataset chọn parser từ schema đã ghi. Bản ghi cũ không bị thêm quote,
  diễn giải lại hoặc migrate. Mọi guard quyết định/suggestion cũ vẫn giữ.
- Prompt Việt/Anh phân biệt sự kiện bản thảo với yêu cầu/điều cấm/quyền đề
  xuất; nhắc xét đúng suggestion và hỏi lại khi lựa chọn tác giả xung đột.
  Không thêm luật theo đạo cụ, phân loại ý đồ bằng regex, model judge hoặc
  lớp điều phối. Đây vẫn là góp ý cục bộ, không chấm toàn phim.

## Kiểm chứng kỹ thuật và review

Full backend cuối **902 passed, 1 skipped**. Module decision checks đạt
**34 test**. Suite tập trung cuối đạt **162 test**.

Test đỏ tái hiện thiếu yêu cầu quote. Thêm ca quote bịa, lấy nội dung từ
quyết định, sai card, thiếu quote, và shape checklist cũ trên request mới;
lỗi API giữ nguyên project và không retry. Kiểm bản ghi checklist cũ sửa
được theo schema cũ và không bị thêm field quote.

Review sửa thêm hai điểm: cho phép quote nguyên văn qua các card liền kề
đã dẫn (ca 3 câu, chỉ dẫn 2 câu đầu), đồng thời từ chối quote đi qua card
không dẫn; card chỉ xuất hiện trong focus metadata nhưng không có trong
nguồn thực cũng bị từ chối. Dùng lại cách tách card, không thêm parser mới.

Đã đọc đường runtime/recorded schema/replay, source scope và lỗi hồi phục.
Giả định tải là MVP local một người. Không còn phát hiện kỹ thuật mở trong
phạm vi thay đổi này; các lỗi nội dung bên dưới vẫn chặn nghiệm thu.

## Model thật: chưa đạt cổng chất lượng

Chốt trước **28 call / 1.800 giây provider**. Dùng nguyên Qwen `qwen2.5:7b`,
digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`,
temperature 0,3, num_ctx 16384, timeout 180 giây. Không đổi model, `.env`,
thêm API trả phí, retry output hoặc tự sửa kết quả.

Đã dùng **7 call / 487,798 giây**: hai baseline đo mới tại `f77385c` và năm
lượt đầu của ứng viên. Với ba ca còn lại dùng baseline đã ghi ngày 04/11,
không tính thành call mới. Đã so source project và input_text trước/sau
giống hệt ở cả năm ca; không đổi nguồn để tăng tỷ lệ đạt.

| Ca | Kết quả đọc thực | API |
| --- | --- | --- |
| Cãi nhau/đi mua bánh | Chọn đúng `constraint-2`, có quote thật; nhưng observation lại viện nội dung của giới hạn khác và cho rằng cãi nhau là giải thích ai ăn bánh. Check suggestion tiếp tục đánh giá bản thảo thay vì bước sửa | 502 |
| Chủ áo/bạn gái cũ | Review aligned dù thêm người/quan hệ. Check có quote từ phần giữa nhưng diễn giải lệnh cấm thành yêu cầu phải giải thích chủ áo; còn suy đoán suggestion dù nó rỗng | 502 |
| Ngồi → đứng, màu áo không liên quan | Check màu áo đã được để không áp dụng; nhưng main review chọn card thành cặp với chính nó và không xác minh bước chuyển | 502 |
| Áo mưa tuân thủ/quyền đề xuất | Có quote thật và check suggestion rỗng đúng không áp dụng; main review vẫn self-pair, giải thích quyền đề xuất còn sai | 502 |
| Hai lựa chọn kết xung đột | Không hỏi lại tác giả; báo mismatch với kết thúc trong khi suggestion rỗng. Một check aligned không có quote | 502 |

**0/5 output mới được nhận.** Bản thảo, feedback cũ và feedback_source giữ
nguyên trong cả bảy call lỗi. Đây là kiểm chứng bảo toàn dữ liệu, không
phải bằng chứng đã sửa cách hiểu ràng buộc hoặc giúp người viết nhận được
góp ý tốt hơn.

Trong lượt review đã sửa guard quote liền kề và câu mô tả tương ứng sau
khi các call bắt đầu. Profile từng call giữ diff thực dùng. Đã replay năm
output đã ghi qua adapter cuối: vẫn 0/5 được nhận; replay không gọi model
và không được tính thành lượt xác nhận. Chưa có batch inference xác nhận
ba lượt trên source cuối, vì cổng nội dung đầu đã thất bại rõ.

Cặp ca lên dây đàn giữ lại đã đóng băng nhưng chưa gọi. Không chi tiếp
ngân sách để thử lại một output xấu, không nới guard hoặc ép mọi ca thành
mismatch/aligned. Thời gian đo là wall time provider, có tải test đồng thời;
adapter không ghi token usage/context thực nên không kết luận benchmark.

Worktree `/private/tmp` đã bị dọn, được khôi phục đúng nhánh đã push. Lần
khởi động chậm nằm ở đọc SDK OpenAI 2.54.0 trong venv; dùng đúng phiên bản
wheel đã xác minh từ PyPI trong thư mục tạm, không đổi dependency repo hay
venv người dùng. Một lần khởi động trùng tên output bị chặn trước provider;
không có inference bị lặp hoặc output bị bỏ khỏi ledger.

## Kết luận review

1. **Chưa nhận: quote thật không bảo đảm suy luận đúng.** Ca bánh vẫn viện
   sai nội dung dù có ID/quote; ca áo đọc ngược lệnh cấm. Không thể dùng
   kiểm chuỗi/ID để khẳng định model hiểu ý tác giả.
2. **Chưa nhận: các bản tuân thủ vẫn không nhận được góp ý mới.** Self-pair,
   thiếu quote hoặc kiểm nhầm suggestion làm API từ chối. Không đổi nguồn,
   tự sửa output hoặc bỏ guard để làm tỷ lệ đạt đẹp hơn.

**Giữ PR #98 draft, #96 mở; chưa merge.** Code neo nguồn được giữ trên nhánh
để review, không phải ứng viên đã được nghiệm thu chất lượng. Chưa có PO/
người đọc độc lập duyệt. Không chạy frontend/build/writer/v8/PDF vì không
đổi UI/public contract/các công đoạn đó. [Evidence đầy đủ](../evaluations/task2-grounded-decisions-2026-11-05/).
