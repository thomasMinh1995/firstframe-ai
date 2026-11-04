# Task 2 — Review việc chọn quyết định và giữ ràng buộc

Ngày 04/11/2026, tiếp tục issue #96 từ `e71d863` trên nhánh
`fix/screenplay-quality-and-feedback`. Giữ nguyên
[báo cáo ngữ cảnh card](task-2-card-context.md).

## Kết quả bàn giao

**Chưa sửa đạt lỗi chọn quyết định hoặc bỏ sót ràng buộc.** Đã thử và review
năm ứng viên nhỏ; không ứng viên nào đủ điều kiện nhận. Tất cả thay đổi thử
trong prompt, adapter, thứ tự schema và test đi kèm đã được loại khỏi
runtime. Source ứng dụng khớp `e71d863`; PR #98 vẫn draft, #96 còn mở.

Không coi việc trả `mismatch`, JSON hợp lệ hoặc test kỹ thuật đạt là sửa
đúng: nhận xét cần chỉ đúng chi tiết, trích đúng quyết định, và bước sửa
không được giữ hoặc tạo vi phạm khác.

## Phạm vi và phép thử

Tận dụng API `/review`, provider và thao tác đo từ đợt trước. Không đổi
model, thêm call mỗi lần review, field output, migration, UI, dependency,
agent hoặc framework QA. Chỉ thử:

- Yêu cầu đọc toàn bộ quyết định trước khi chọn một nhận xét; ưu tiên vi
  phạm có căn cứ hơn lời khen cho chi tiết khác phù hợp.
- Sinh quan sát/kết luận trước `decision_id`, rồi thử trước cả ID card.
  Chỉ đổi thứ tự field hiện có, không thêm field hoặc enum mới.
- Đặt giới hạn/câu trả lời trước ý tưởng chung trong input. Giữ nguyên ID,
  text và câu hỏi; đoạn nguồn liên tục vẫn đứng trước các mẩu card.
- Yêu cầu bước sửa dạng chỉ dẫn biên tập, kiểm lại mọi giới hạn, rồi thử
  hướng dẫn ngắn hơn. Không thêm rule theo đạo cụ/câu chữ fixture.

Hai đối chứng phát triển giữ snapshot sau review đã lưu, chỉ Ending thuộc
focus (runner kiểm trước call): thêm cãi nhau/đi mua bánh; thêm chủ áo quay
lại/bạn gái cũ. Nguồn, schema field và model giữ như baseline trong từng
cặp; thứ tự field là một biến thử ở các ứng viên có ghi rõ.

Ngân sách chốt trước là **28 call / 1.200 giây provider**. Cấu hình giữ Qwen
`qwen2.5:7b`, temperature 0,3, context 16384, timeout 180 giây. SQLite và
dataset tạm, chỉ dùng snapshot tổng hợp. Có ca may cúc mới để kiểm tra ngoài
hai ví dụ phát triển; đo baseline trước, chưa chạy ứng viên trên ca giữ lại
vì không ứng viên nào qua cổng phát triển. Không tuyên bố có kiểm chứng khả
năng áp dụng ngoài ví dụ.

Ca may cúc positive đầu đặt việc cắt chỉ *sau* điểm dừng đã yêu cầu, nên
không phải đối chứng sạch. Giữ nguyên ca/output/hash ban đầu, bổ sung ID
`sewing-before-cut` với cắt chỉ trước khi siết mũi cuối và đo baseline riêng.
Không đổi kỳ vọng cũ theo output model. Baseline mới aligned; baseline
negative phát hiện một phần lỗi nhưng đề nghị giữ thao tác cắt vải bị cấm.

## Đọc kết quả và review

| Ứng viên | Kết quả quan sát được | Kết luận |
| --- | --- | --- |
| `candidate-*`: thêm hướng dẫn kiểm mọi quyết định | Ca bánh viện `constraint-1` về người thứ ba/ai ăn bánh, dù vấn đề trực tiếp là `constraint-2`; ca áo đề nghị giữ bạn gái cũ/chia tay | Loại |
| `ordered-*`: sinh so sánh trước quyết định | Ca bánh vẫn viện ý tưởng chung, đề nghị để tình huống tự giải quyết; ca áo nhận xét chung chung, chưa giải thích đúng chi tiết và đủ bước sửa | Loại |
| `choices-first-*`: quyết định cụ thể trước brief, quan sát trước ID card | Ca bánh chọn đúng `constraint-2` nhưng vẫn viết lại cảnh đi mua bánh; ca áo trả aligned dù thêm người/quan hệ | Loại |
| `editing-*`: bước sửa dạng chỉ dẫn, phân biệt cấm/cho phép | Ca bánh chọn đúng giới hạn và bỏ cả hai hành động, nhưng quan sát còn gán thêm giới hạn không có căn cứ; ca áo viện `constraint-2` vốn là quyền đề xuất rồi thêm kỷ niệm chia tay | Loại |
| `concise-*`: hướng dẫn ngắn hơn | Ca bánh bỏ cả hai hành động nhưng viện giới hạn khác và giải thích sai; ca áo gán nội dung thành mất mát dù bản sửa kể bạn gái cũ/chia tay | Loại |

Hai vấn đề **cần sửa trước khi nghiệm thu**:

1. **Nguồn được dẫn chưa chứng minh nhận xét.** Có ID thật và trích dẫn
   nguyên văn không bảo đảm model dùng đúng nội dung nguồn. Chẳng hạn,
   `concise-fridge-ending-violation-1` viện giới hạn về người thứ ba trong
   đoạn chỉ có hai người. Không nên trình bày đó là đối chiếu đúng ý tác giả.
2. **Bước sửa có thể giữ lại điều bị cấm.** Trong
   `choices-first-fridge-ending-violation-1`, nguồn đã dẫn chính giới hạn
   cấm mua bánh nhưng suggestion vẫn cho hai người đi mua bánh. Trong
   `editing-raincoat-ending-violation-1`, suggestion còn bịa thêm kỷ niệm.
   Người viết làm theo sẽ nhận một bản sửa vẫn trái lựa chọn đã lưu.

Luồng kỹ thuật đã được đọc lại: API lấy bản sửa và nguồn review trước,
adapter giữ nguồn nguyên văn/ID/cặp lân cận, model chọn một nhận xét, server
kiểm liên kết và gắn trích dẫn, rồi lưu feedback cùng đúng draft. Các guard
hiện tại kiểm tính hợp lệ của liên kết, không chứng minh suy luận ngữ nghĩa.
Không nới guard, ép mọi ca mismatch/aligned, tự sửa output hoặc retry để
che hai lỗi trên. Giả định tải vẫn là MVP local một người; thử nghiệm không
thêm chi phí, trạng thái hoặc công việc nền vào ứng dụng.

## Kiểm chứng và điểm dừng

- **15 call, 280,233 giây provider**: 5 baseline và 10 call cho năm ứng viên.
  Tất cả API 200, draft không đổi và feedback_source gắn đúng draft.
- Dừng trước vòng xác nhận ba lượt và trước so sánh ứng viên trên ca giữ
  lại, vì cả năm ứng viên đều còn lỗi quan sát được. Không dùng hết ngân
  sách chỉ để thử lại output; không loại một lượt xấu khỏi mẫu thống kê.
- Có test đỏ xác nhận thứ tự field cũ và test hồi quy trong các ứng viên;
  đã loại cùng thay đổi chưa được nhận. Hai helper/assertion test dùng vị
  trí mảng cũng được sửa khi thử input mới, rồi trả lại cùng baseline.
- Full backend trên ứng viên adapter cuối đạt **869 passed, 1 skipped**;
  focused suite trên prompt ngắn đạt **123 passed**. Đây là kiểm chứng kỹ
  thuật của ứng viên bị loại, không phải bằng chứng critic hiểu đúng.
- Sau trả runtime về baseline: full backend **868 passed, 1 skipped**.
  Không chạy UI/frontend/build/model v8 theo cảnh vì không giao thay đổi
  runtime, UI, public contract hoặc critic theo cảnh trong đợt này.

Toàn bộ [evidence](../evaluations/task2-decision-selection-2026-11-04/)
giữ request/input/schema, response thô, source, kết quả API, profile/diff,
ledger, ca ban đầu và ca bổ sung. Archive được đối chiếu byte trước bàn giao.

Kết luận review của agent: **chưa ship; không nhận năm ứng viên này**.
Chưa có người đọc độc lập/PO duyệt. Hướng tiếp theo cần review lại cách
biểu diễn việc kiểm từng quyết định trong hợp đồng nội bộ, thay vì tiếp tục
nối dài prompt rồi suy từ một ID rằng mọi ràng buộc đã được xét. Đợt này
chưa mở rộng hợp đồng hay thêm công đoạn đó; #96 không được tự đóng.
