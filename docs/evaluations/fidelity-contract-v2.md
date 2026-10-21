# Hợp đồng fidelity v2 và bộ nghiệm thu tổng quát — PR #18

## Mục tiêu và phạm vi

Đánh giá đúng nguồn tác giả và bản thảo hiện tại, không ép một cấu trúc truyện
hoặc kết thúc mẫu. Không tối ưu theo một dự án cụ thể. Bản này thay phần hợp
đồng scan/audit trong báo cáo fidelity trước đó; các bằng chứng cũ được giữ nguyên.
Đây là triển khai và bộ nghiệm thu đề xuất, **chưa phải chứng nhận model đạt**.

## Hợp đồng

Scan tạo tối đa ba **ứng viên mâu thuẫn**, không phải kết luận đã xác minh. Nó
đọc toàn bản; phân biệt mâu thuẫn rõ với diễn đạt tương đương, tóm tắt, chi tiết
ở phần khác, thiếu thông tin và sở thích nghệ thuật. Phản hồi scan giữ schema cũ
để giảm thay đổi dây chuyền; `issues` mang nghĩa ứng viên, phải qua audit.

Audit trả một đối tượng gồm hai ID nguồn và ba kết luận riêng, mỗi kết luận có
lý do bắt buộc:

| Trường | Giá trị | Câu hỏi |
| --- | --- | --- |
| relation | contradictory / compatible / uncertain | Hai trích dẫn có mâu thuẫn trong ngữ cảnh không? |
| concern | supported / unsupported / uncertain | Nhận xét có được bản hiện tại hỗ trợ không? |
| revision | aligned / violates / uncertain | Làm theo đề xuất có giữ quyết định tác giả không? |

Không còn verdict gộp. Gợi ý tốt không chứng minh nhận xét đúng; nhận xét đúng
không chứng minh gợi ý an toàn. Với fidelity, chỉ hiển thị gợi ý khi
`contradictory + supported + aligned`, nguồn trích hợp lệ và khớp ứng viên.
Với craft, relation có thể compatible nhưng concern phải supported và revision
phải aligned; uncertain ở bất kỳ kết luận cần thiết nào đều không duyệt gợi ý.

| Tình huống | Xử lý |
| --- | --- |
| Nhận xét bị bác hoặc fidelity tương thích | Không hiện card như lỗi; giữ raw trong dataset |
| Nhận xét có căn cứ, sửa đổi trái ý đồ | Giữ nguyên trích dẫn và nhận xét để đối chiếu; ẩn đề xuất sửa |
| Chưa đủ căn cứ, nguồn hợp lệ | Giữ trạng thái chưa xác minh và ba lý do |
| Audit đổi nguồn hoặc nguồn không tồn tại | Không duyệt; không gắn đánh giá của nguồn khác lên highlight cũ |
| Mọi điều kiện hợp lệ | Hiện gợi ý với nhãn “AI đánh giá … cần tác giả đối chiếu” |

`assessment` được lưu trong từng FidelityCheck. Trường tùy chọn hỗ trợ feedback
v1 đã lưu; không diễn dịch verdict cũ thành ba kết luận mới. Snapshot, ID phần,
nguyên văn và các cơ chế giữ bản nháp không đổi. Giao diện hiển thị cả ba kết
luận khi có assessment. Không tự áp dụng sửa đổi. Tối đa năm lượt model như cũ,
không tăng thêm ba lượt chỉ vì có ba kết luận. Nếu scan bỏ sót nhưng audit của
critic phát hiện mâu thuẫn có căn cứ, report chuyển thành issues (hoặc unverified
khi sửa đổi chưa hợp lệ), không giữ banner clear và không chấm nghệ thuật như
thể không có mâu thuẫn. Nhận xét có căn cứ vẫn còn dù gợi ý sửa bị bác.

Nguồn tác giả là ý tưởng, giới hạn, câu trả lời kèm ngữ cảnh câu hỏi. Câu hỏi
không phải lựa chọn. Lời đổi ý rõ ràng về sau thay ý trước; xung đột không có
thứ tự ưu tiên rõ phải để uncertain. Các prompt fidelity và critic không dùng
câu chuyện lab coach hay tên dự án mẫu làm quy tắc riêng.

## Bộ dữ liệu và nguyên tắc nghiệm thu

[24 ca cố định](../../demo/evaluations/fidelity-suite/cases.json): 16 development,
8 holdout, chia theo **cả họ tình huống**, không chia hai biến thể của cùng truyện.
Có 10 bản mâu thuẫn, 12 bản tương thích và 2 bản thiếu/xung đột ý đồ. Cả VI và EN;
thuật ngữ nghề nghiệp hỗn hợp; các cặp vai trò, thứ tự, kết quả bên ngoài, kết mở,
quan hệ, giới hạn lời thoại, diễn đạt tương đương, nghề nghiệp, lựa chọn nhận việc,
địa điểm; thêm quyết định mới, câu trả lời để sau và thiếu ngữ cảnh.

Mỗi ca có nguồn, bản thảo, một nhận xét/đề xuất cố định và nhãn mong đợi. Có cả
nhận xét đúng nhưng sửa sai. Scanner không thấy candidate hay nhãn. Auditor thấy
candidate nhưng không thấy nhãn, rationale hoặc split. Kiểm tra audit độc lập
với việc scanner phát hiện được lỗi để không bỏ qua ca khó do scan trả clear.
Đây là kiểm tra các thành phần production bằng cùng hàm scan/audit; không giả
làm một lượt review UI đầy đủ hoặc đo chất lượng critic nghệ thuật.

Nhãn được soạn trong quá trình triển khai, `proposed_for_PO_review`; PO cần duyệt
trước nghiệm thu chính thức. Bộ nhỏ, câu ngắn, chưa đại diện mọi bản thảo dài.
Không sửa nhãn theo kết quả model; không chỉnh prompt sau khi xem holdout. Nếu
sau này dùng holdout để tối ưu, phải thay holdout bằng câu chuyện chưa dùng.

## Cách chạy và đọc kết quả

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/accept_fidelity.py \
  --output /tmp/fidelity-general-new.jsonl
```

Có `--split development|holdout` và `--case-id` để chạy lại lỗi kỹ thuật của một
ca vào file mới. Không ghi đè file cũ. Lưu SHA256 toàn fixture, prompt, schema,
input, output, model/parameters, lỗi và thời gian từng bước. Không mở project DB,
không ghi training store, không gửi nhãn đáp án cho model. Lỗi vẫn nằm trong
mẫu số, không tính là model đã từ chối an toàn.

Chấm tự động: scan đúng nhãn (với mâu thuẫn phải đúng cả hai trích dẫn), từng
chiều audit, backend cho phép đúng và số gợi ý sai được duyệt. Chấm này **không
chứng minh lý do đúng nghĩa hoặc đúng ngôn ngữ**; hai mục đó luôn pending_human
cho đến khi người đánh giá đọc. Việc chặn tất cả gợi ý không phải thành công:
phải đo cả gợi ý hợp lệ bị chặn và bản tương thích bị báo oan.

Ngưỡng đề xuất trước nghiệm thu: toàn bộ kiểm tra code về nguồn/phiên bản/giữ
nháp đạt; phát hiện >=90% mâu thuẫn; ít nhất 90% bản tương thích được nhận đúng (không tính abstention là đúng);
ít nhất 90% đề xuất sửa hợp lệ được cho phép; không có
unsafe approval trên các ca nghiêm trọng; lý do và ngôn ngữ phải được PO duyệt.
Với bộ nhỏ, báo số đếm và mẫu số bên cạnh phần trăm. Một lượt temperature 0.3
không seed chỉ là khảo sát, không chứng minh độ ổn định. Cần chạy lặp các ca
nghiêm trọng trước khi chuyển PR sang ready, và model đối chứng nếu Qwen không đạt.


### Kiểm soát công cụ kiểm thử

Lượt pilot đầu dùng mã `vi/en` trực tiếp, trong khi production chuyển chúng qua
`resolve_response_language` thành `Vietnamese/English`. Đã dùng chính hàm production
và chạy lại toàn bộ 24 ca với fixture/prompt giữ nguyên; dùng lượt sau làm kết quả
chính. Pilot được giữ để truy vết, không chọn kết quả tốt hơn giữa các lượt.

Pilot cũng lộ lỗi harness khi tạo EvidenceIssue từ author_quote rỗng ở ca thiếu
ý đồ. Đã sửa để vẫn chạy audit nhưng không tạo nguồn giả, thêm test hồi quy; một
lượt retry riêng được lưu bên cạnh pilot. Đây là sửa công cụ, không sửa nhãn hay
prompt theo kết quả. Lượt chính chạy lại đầy đủ bằng harness đã sửa.

Các metric tự động chỉ là khớp nhãn/nguồn. Ví dụ pilot boat-role-conflict chọn
đúng status và hai ID nhưng giải thích đảo vai Mai với em trai; điểm scan không
thể thay cho việc đọc lý do. Không gọi số scan khớp nhãn là độ chính xác ngữ nghĩa.

## Kết quả Qwen trên bộ tổng quát

Model `qwen2.5:3b`, temperature 0.3, context 16384, không seed. Không sửa prompt
hoặc fixture theo kết quả pilot/holdout. [Raw lượt chính](../../demo/evaluations/fidelity-suite/qwen-final.jsonl)
và [tổng hợp](../../demo/evaluations/fidelity-suite/summary.json) được lưu cùng
[pilot](../../demo/evaluations/fidelity-suite/qwen-pilot.jsonl) và
[retry lỗi harness](../../demo/evaluations/fidelity-suite/qwen-pilot-retry.jsonl).

| Chỉ số lượt chính | Kết quả |
| --- | --- |
| Ca chạy đủ, không lỗi kỹ thuật | 24/24 |
| Scan khớp nhãn và nguồn | 11/24 |
| Nhãn mâu thuẫn + nguồn khớp trên bản có mâu thuẫn | 10/10; không chứng minh giải thích đúng |
| Bản tương thích được nhận đúng | 0/12; cả 12 bị báo mâu thuẫn |
| Gợi ý hợp lệ được duyệt | 0/7 |
| Gợi ý không hợp lệ được duyệt | 0; mọi gợi ý đều bị chặn, không phải thành công |
| Cả ba nhãn audit khớp + scan + quyết định cho phép khớp | 3/24 |
| Holdout: scan khớp nhãn/nguồn | 3/8 |
| Holdout: bản tương thích được nhận đúng | 0/4 |

Audit trả cùng bộ nhãn **contradictory / supported / violates trong cả 24 ca**,
kể cả ca không có ý đồ. Đây là dấu hiệu không phân biệt được các tình huống
trong bộ này, không phải hệ thống đã kiểm chứng mọi lỗi. Đọc một số lý do cho
thấy model đảo nguồn và vai trò dù ID đúng; phần lý do/ngôn ngữ vẫn cần PO đánh
giá, không được nâng các con số khớp nhãn thành độ chính xác ngữ nghĩa.

Đã replay toàn bộ 24 bộ output đã ghi qua code hiện tại, không gọi model: input
và prompt khớp, snapshot/report và điểm chấm khớp 24/24. Kiểm tra này xác nhận
code áp dụng hợp đồng nhất quán, không xác nhận suy luận của Qwen đúng.

### Kiểm tra tích hợp bằng góp ý do Qwen tự sinh

Bốn ca development đã chọn: boat-role conflict/control và open-letter
conflict/control. [Input](../../demo/evaluations/fidelity-suite/integration-inputs.jsonl)
và [raw review](../../demo/evaluations/fidelity-suite/qwen-integration.jsonl).
Chạy qua service.review thật bằng script replay_fidelity, không truyền đáp án,
không dùng candidate cố định, không mở database dự án. Cả bốn request completed,
không lỗi, đều unverified và không duyệt gợi ý nào; không tới critic vì scan
đã báo issues. Chưa đạt về tính hữu ích; không lấy việc chặn hết làm nghiệm thu.

`dataset_workflow_complete=false` là cờ dataset dành riêng cho plan/generate,
không có nghĩa các lượt review này bị lỗi; xem run_status=completed/error_type=null.
Dữ liệu không được tự phê duyệt cho huấn luyện.

### Kiểm tra kỹ thuật cuối

- **266 tests backend đạt**, gồm các tổ hợp 3 chiều, nguồn sai, snapshot đúng bản
  sửa/lịch sử, timeout giữ dữ liệu, audit phát hiện mâu thuẫn sau scan clear,
  chạy harness thiếu ý đồ, không lộ nhãn cho model, mẫu số lỗi/thiếu ca.
- **22 assertions frontend đạt**, gồm tương thích báo cáo cũ, validation hợp đồng
  mới, ba kết luận riêng và ẩn đề xuất chưa được duyệt; production build đạt.
- Ruff và diff-check đạt. Một cảnh báo Starlette/httpx có sẵn trong bộ backend.
- Không chạy browser E2E mới trong lượt này; việc giữ nháp có kiểm thử hồi quy và
  bằng chứng UI từ review trước. Không sửa checkout dev hoặc dự án trên cổng 3001.

**Kết luận: phần hợp đồng và bộ nghiệm thu đã triển khai; Qwen chưa đạt các ngưỡng
đề xuất. Giữ PR Draft.** Nhãn cần PO duyệt; chưa có model đối chứng, chưa đo ổn
định qua nhiều seed, bộ câu ngắn chưa đại diện bản thảo dài. Không tiếp tục vá
prompt theo từng ca để làm đẹp điểm của bộ này.
