# Task 2 — Ngữ cảnh thời gian và lựa chọn nguồn đối chiếu

Ngày 04/11/2026. Tiếp tục #96 trên `fix/screenplay-quality-and-feedback`,
baseline `b650c49`. Giữ nguyên [báo cáo đợt trước](task-2-screenplay-quality.md).

## Thay đổi đang review

- `review_context()` giữ thêm từng đoạn nguyên văn và danh sách card trong
  đoạn theo thứ tự nguồn. Card vẫn giữ ID và text cũ để dẫn chứng chính xác.
- `_evaluation_input()` đưa đoạn liên tục lên trước, chỉ gửi các đoạn chứa
  card đang sửa/lân cận. Giữ phạm vi target như trước; đoạn nguyên không mở
  thêm đích cho model hoặc ghi đè nguồn.
- `_card_review_schema()` cho chọn trong toàn bộ brief/ràng buộc/câu trả
  lời có thật. Bỏ điều kiện buộc một nhận xét duy nhất phải viện câu trả lời
  làm rõ dù nó nói về chuyện khác. Không chọn quyết định bằng regex/đạo cụ.
- Prompt card ngắn hơn, hỏi khả năng tiếp nối hợp lý thay cho lời nhắc dài
  thiên về tìm lỗi. Tiếng Việt dùng hướng dẫn tiếng Việt; bản tiếng Anh giữ
  cùng nhiệm vụ. Không đổi output API, số call mỗi lần review, model hoặc UI.

Giữ kiểm tra ID có thật, nguồn nguyên văn, target thuộc bản sửa/cặp lân cận,
không self-pair và mismatch cần bước sửa. `aligned` kèm suggestion vẫn bị
từ chối. Các bản ghi dataset cũ vẫn bị ràng bởi enum/schema đã ghi; mở rộng
lựa chọn runtime không cho sửa một record cũ bằng ID ngoài schema của nó.

## Kiểm chứng bằng model thật

Ngân sách chốt trước: tối đa 24 call, 900 giây provider. Qwen `qwen2.5:7b`,
temperature 0,3, context 16384, timeout provider 180 giây; không đổi model,
không retry. API/TestClient và SQLite/dataset tạm, lấy snapshot tổng hợp từ
archive đợt trước. Case đóng sách là ca mới và có một câu trả lời về keo
không liên quan đến việc đọc trình tự xỏ dây–buộc nút.

### Ứng viên đầu — không nhận

Chỉ thêm đoạn nguyên sau danh sách card và bổ sung hướng dẫn vào prompt dài
không giúp đủ: cả chín lượt positive vẫn có báo sai về sự tiếp nối. Đã dừng
phần còn lại trước model, giữ các lượt đã hoàn tất. Không dùng kết quả đó
để tuyên bố lỗi đã sửa.

### Bản đang review — tiến bộ cục bộ, chưa đủ nghiệm thu

| Ca | Kết quả đọc thực |
| --- | --- |
| Ngồi trong bếp → đứng dậy cầm cốc | **3/3** nhận đúng sự tiếp nối, không đòi vừa ngồi vừa đứng, suggestion rỗng; dùng `idea` thay vì áp số người/địa điểm để cấm đổi tư thế |
| Đóng sách: đặt giấy → xỏ dây → buộc nút | Một lượt nhận đúng sự tiếp nối, dùng brief; không bị buộc viện câu trả lời về keo. Chưa có ba lượt xác nhận cho ca này |
| Ending thêm cãi nhau và đi mua bánh | Nhận ra cãi nhau chưa phù hợp nhưng viện ý tưởng chung, vẫn đề nghị đi mua bánh trái `constraint-2`. **Chưa đạt** việc chọn quyết định và đề xuất giữ đủ ràng buộc |
| Ending thêm chủ áo/bạn gái cũ | Trả aligned dù trái ràng buộc về nhân vật/quan hệ. **Bỏ sót vi phạm, chưa đạt** |

Một lượt khác trả aligned kèm suggestion thêm bối cảnh: API trả 502 theo
guard hiện có; không tự xóa suggestion để cứu output. Draft nguồn vẫn giữ.

Hai ca vi phạm ban đầu kế thừa snapshot *trước* lượt review đã lưu, nên có
cả sửa Beginning lẫn Ending; critic được chọn phần mở đầu phù hợp. Đây
không phải đối chứng sạch để khẳng định model đã đọc Ending. Đã giữ toàn bộ
ca/kỳ vọng cũ, bổ sung hai ID ca mới lấy snapshot *sau* review, và kiểm trước
call rằng chỉ Ending nằm trong focus. Không thay output/kỳ vọng cũ để tăng
tỷ lệ đạt. `cases-initial.json` khớp hash các profile trước bổ sung.

Đã dùng đủ **24 call, 400,089 giây provider**; không gọi thêm dù còn thời
gian. Provider có 24 response hợp schema; API nhận 23 và từ chối một output
aligned/suggestion sai hợp đồng. Không có retry hoặc kết quả bị bỏ khỏi báo cáo.

## Kiểm thử kỹ thuật

- Thêm test cho đoạn nguyên/thứ tự, scope card lân cận, lựa chọn brief hoặc
  constraint khi có câu trả lời không liên quan và enum dataset legacy.
  Ba lỗi dữ liệu/schema được tái hiện bằng test trước sửa.
- Full backend với adapter đầu: **868 passed, 1 skipped**. Sau rút gọn prompt,
  full suite có **866 passed, 2 failed, 1 skipped**; hai failure là assertion
  chuỗi chỉ dẫn ngôn ngữ cũ. Đã cập nhật assertion theo câu chỉ dẫn mới và
  chạy lại hai ca đạt; **119 test tập trung cuối đạt** trên source cuối.
- Frontend **25 suite đạt** và typecheck đạt. Source note/quote và public API
  không đổi. Không gọi model trả phí, thêm dependency hay dựng hệ thống QA mới.

## Trạng thái bàn giao

Đã có bản sửa adapter và ca hồi quy kỹ thuật để review. **PR #98 vẫn là
draft, chưa đề nghị merge hoặc công bố critic đã đạt chất lượng.** Ca ngồi
→ đứng có tiến bộ rõ nhưng việc chọn quyết định cụ thể và giữ đầy đủ giới
hạn trong gợi ý vẫn chưa đạt. Planner không đổi trong lượt này; #96 còn mở.

Evidence của cả hai ứng viên, nguồn, schema, output, lỗi API và ngân sách:
[task2-card-context-2026-11-04](../evaluations/task2-card-context-2026-11-04/).
Các nhận xét nội dung là của agent; chưa có PO/người đọc độc lập nghiệm thu.

Bước tiếp theo cần một đợt có ngân sách riêng: xử lý việc chọn brief chung
thay vì giới hạn cụ thể, đồng thời giữ đối chứng vi phạm. Không sửa bằng
cách ép mọi lượt aligned, bỏ guard hay thêm rule theo câu chữ fixture.
