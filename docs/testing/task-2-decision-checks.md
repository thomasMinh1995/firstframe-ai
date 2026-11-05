# Task 2.2a — Triển khai đối chiếu từng quyết định và review

Ngày 04/11/2026. Nhánh `fix/screenplay-quality-and-feedback`, baseline
`8d97d5a`. Theo [plan 2.2a](../plans/screenplay-quality-and-feedback.md).

## Bản triển khai để review

- Thêm `DecisionCheck` và phản hồi critic có `decision_checks` bắt buộc,
  đặt sau `reviews`; mỗi quyết định có trạng thái/căn cứ bản sửa và trạng
  thái/lý do đối chiếu đúng suggestion vừa sinh. Card và decision enum lấy
  từ nguồn hiện có, số mục bằng số quyết định thực, không cắt bớt.
- Dùng một helper phạm vi card cho schema/input/checks. Adapter từ chối
  thiếu/trùng/ID lạ, căn cứ ngoài scope, vi phạm bị bỏ qua, nguồn nhận xét
  không liên quan, aligned thiếu căn cứ hoặc còn bất định, và suggestion
  tự bị đánh dấu vi phạm/bất định. Không có suggestion thì check của nó
  phải là `not_applicable`. Giữ lỗi tiếp nối độc lập với vi phạm lựa chọn.
- Model/provider trả shape legacy cho request mới cũng bị từ chối bằng lỗi
  review hiện có; không fallback. Runtime và dataset dùng cùng kiểm tra
  nhất quán. Dataset chọn parser theo schema đã ghi, giữ ID/count contract
  của bản ghi và kiểm lại khi replay; bản cũ vẫn giữ hợp đồng cũ.
- Vẫn một call model, một nhận xét chính. Chỉ dataset/evidence giữ checks;
  public API, feedback/RevisionNote dự án, database và UI không thêm field.
  Không đổi model, planner, writer, critic v8 hoặc workflow tác giả.

Code được giữ trên **nhánh draft để review**, chưa được nhận vào `dev`.
Phần kỹ thuật đã triển khai; ứng viên chưa qua cổng chất lượng mục C.

## Kiểm thử và các lỗi đã sửa qua review

**Full backend cuối: 894 passed, 1 skipped.** Suite tập trung cuối đạt
133 test. Thêm 26 ca kiểm tra hợp đồng/khôi phục lỗi; không dùng mock để
khẳng định model hiểu đúng sáng tác.

- Test đỏ trước sửa tái hiện request mới vẫn nhận response thiếu checks.
- Review phát hiện shape legacy có thể thành TypeError thay vì lỗi review;
  đã chuyển thành lỗi provider hợp lệ. Ba ca API kiểm thiếu check, shape
  legacy và suggestion chưa được xác minh đều trả 502, giữ nguyên toàn bộ
  project và chỉ gọi model một lần.
- Review phát hiện aligned có thể thiếu card làm căn cứ; đã có test đỏ và
  guard yêu cầu check được dẫn có căn cứ trong cặp nhận xét chính.
- Có ca đủ/thiếu/trùng/ID lạ, blank reason, nguồn ngoài scope, kết luận
  bất nhất, nguồn vi phạm khác với nguồn được trích, `uncertain` có/không
  câu hỏi, câu trả lời không liên quan, lỗi tiếp nối khi lựa chọn vẫn được
  giữ, enum dataset đã ghi và schema cũ/mới. Test 23 quyết định xác nhận
  không cắt checklist khi có 20 constraint; đây không phải phép đo model.
- Full suite đầu còn một fixture HTTP Ollama dùng model legacy; đã cập nhật
  fixture theo schema request mới và chạy lại full suite đạt như trên.

Đã đọc lại callers từ plan mới/manual review, nguồn và bước lưu feedback,
dataset sửa/replay, fake provider và lỗi hồi phục. Giả định tải vẫn là MVP
local một người; không thêm call, trạng thái hoặc công việc nền. Không phát
hiện lỗi kỹ thuật còn mở trong phạm vi review này; hai lỗi nội dung dưới
đây vẫn chặn việc nhận ứng viên.

## Model thật: chưa đạt, không đề nghị merge

Chốt trước **28 call / 1.500 giây provider**, Qwen `qwen2.5:7b`, temperature
0,3, num_ctx 16384, timeout 180 giây. Metadata digest lưu riêng; thời gian là
wall time quanh provider, không phải benchmark hiệu năng độc lập. Có lúc
test kỹ thuật chạy cùng quá trình đo. Provider không trả context thực/token
usage qua adapter này nên không suy từ tham số yêu cầu rằng đã kiểm hết
mọi giới hạn kích thước.

Đã dùng **12 call / 394,002 giây**: 7 baseline trên checkout tách biệt
`8d97d5a`, 5 lượt đầu của ứng viên trên các ca phát triển. Đã đối chiếu
source project và input_text trước/sau giống hệt cho cả năm ca; chỉ
instructions/schema/adapter thay đổi. SQLite/dataset tạm, nguồn tổng hợp,
không retry, chỉnh output, tải/đổi model hoặc thêm API trả phí.

| Ca phát triển | Kết quả ứng viên đọc thực | Kết quả API |
| --- | --- | --- |
| Ending cãi nhau/đi mua bánh | Vẫn chọn idea và aligned; check `constraint-2` phủ nhận những hành động đang có thật. Suggestion rỗng nhưng check của nó lại aligned | 502 |
| Ending thêm chủ áo/bạn gái cũ | Hiểu sai nguồn thành người thợ để quên áo; coi quyền đề xuất là vi phạm, vẫn gợi ý thêm bạn gái cũ. Tự đánh dấu suggestion mismatch | 502 |
| Ngồi → đứng, có câu trả lời về màu áo không liên quan | Nhận xét bối cảnh thay vì xác minh bước chuyển, self-pair card; check câu trả lời thành uncertain và check suggestion rỗng thành aligned | 502 |
| Áo mưa, bản tuân thủ/quyền đề xuất | Nhận đúng diễn tiến nhỏ, nhưng mọi check suggestion rỗng đều aligned thay vì not_applicable | 502 |
| Hai lựa chọn kết mâu thuẫn | Review aligned với một phía, check phía kia mismatch và đề nghị thêm khách; không hỏi lại tác giả | 502 |

Mọi response model đủ shape để parse, nhưng **0/5 được API nhận**. Giữ
draft và feedback cũ/feedback_source đúng như trước call ở cả năm ca. Không
đếm 502 là phát hiện đúng vi phạm: ca bánh bị chặn do bất nhất check
suggestion, trong khi suy luận về ràng buộc vẫn sai. Ca tuân thủ cũng bị
chặn, nên kết quả này chưa giúp tác giả nhận góp ý mới đáng tin cậy.

Đã dừng trước ba lượt xác nhận và trước ứng viên trên cặp ca gốm giữ lại.
Hai ca giữ lại mới đo baseline; chưa có bằng chứng áp dụng ngoài ca phát
triển. Không dùng phần ngân sách còn lại để thử lại hoặc chọn lượt đẹp.

## Kết luận review

1. **Cần sửa trước khi nhận: checks có thể đủ mục nhưng sai nội dung.** Ca
   bánh phủ nhận điều có trong bản sửa; ca áo vẫn bỏ sót giới hạn và gán
   sai quyền đề xuất. Guard cấu trúc không chứng minh được suy luận; tác
   giả không nên nhận các kết luận đó như đối chiếu đúng lựa chọn.
2. **Cần sửa trước khi nhận: hợp đồng mới chưa được model tuân thủ ổn định.**
   Cả năm output bị từ chối, gồm cả bản tuân thủ. Không nới guard, đổi nhãn
   hoặc xóa suggestion để cứu output. Bản triển khai hiện tại chưa đạt khả
   năng sử dụng của vòng góp ý, dù giữ dữ liệu an toàn.

**Chưa ship.** Giữ ứng viên kỹ thuật trên PR #98 draft để review; không
merge, không đóng #96 và không công bố đã sửa xong critic. Kết luận nội dung
ở đây là của agent; chưa có PO/người đọc độc lập duyệt. Không chạy frontend,
build, model writer/v8 hay PDF vì không đổi UI/public contract/các công đoạn
đó. Toàn bộ [evidence](../evaluations/task2-decision-checks-2026-11-04/) được
giữ để đối chiếu, không biến kết quả tự kiểm của AI thành ý đồ tác giả.
