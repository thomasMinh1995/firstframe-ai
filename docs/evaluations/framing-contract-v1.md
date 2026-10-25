# Hợp đồng nhận diện góc nhìn offline v1

Nhánh `fix/harness-framing-contract` dành cho ba phần: đơn giản hóa output,
chốt prompt/bằng chứng/unclear, rồi kiểm chứng guardrail và bộ ca mới. Đợt
thay đổi đầu chỉ chốt schema, prompt và kiểm tra hợp đồng; chưa chạy model,
chưa triển khai runner/gate mới, chưa thay plan harness hoặc runtime.

Trạng thái sau phần 3: đã đóng băng prompt/schema/nhãn và chạy đủ 60 lượt
Gemma 2 trên 18 ca hồi quy + 12 ca mới, hai lượt mỗi ca. Guardrail sandbox
đạt về nguồn/snapshot/lưu-sửa, nhưng chất lượng xuất bản chưa đạt do bỏ sót
4/16 lượt phải block. Xem `issue-7-framing-v1-guardrail-2026-10-25.md` trong
cùng thư mục. Đây không phải thay đổi plan harness hoặc tích hợp runtime.

## Schema nguồn duy nhất

`backend/scripts/framing_contract.py:FramingAssessment` cung cấp schema qua
`model_json_schema()`. Prompt ở `backend/scripts/prompts/framing_assessment_vi.md`.
Các module này chỉ thuộc bộ thử offline, không nối vào app hoặc domain prompts.

## Cập nhật prompt: siết yêu cầu suy luận

Giữ nguyên schema v1 và validator, chỉ làm rõ thứ tự nhận diện:

1. Xác định phạm vi chủ đề có mặt; không có thì not_applicable, không yêu
   cầu bổ sung ngữ cảnh cho chủ đề không liên quan.
2. Tìm nguồn góc nhìn trong toàn draft trước khi gán nhãn. Lời nhân vật,
   hành vi xấu hoặc việc chịu hậu quả chưa tự chứng minh quan điểm tác phẩm.
3. Chỉ gán critical/endorsing khi nguồn hỗ trợ đúng ý nghĩa. Không có dấu
   hiệu ủng hộ không đủ suy thành phản đối, và ngược lại.
4. Chưa đủ nguồn hoặc dấu hiệu trái chiều chưa được giải quyết thì unclear;
   không bịa thái độ, tự giả định mỉa mai hay ép thêm lời lên án.
5. Tự kiểm tra nhãn với quote đã chọn, nhưng không thêm chuỗi suy luận,
   explanation hoặc field mới vào JSON.

Ngôn từ tiếp tục xét độc lập: policy rõ và draft phù hợp thì no_violation;
không đòi thêm góc nhìn đạo đức không liên quan. Cảnh phê phán vẫn có thể
vi phạm policy ngôn từ riêng của bản trẻ em.

Các ranh giới dùng để review prompt, chưa phải kết quả thử model:

| Nguồn hiện có | Kết luận cần giữ |
| --- | --- |
| Không có chủ đề trong phạm vi đã định | not_applicable, không ép hỏi thêm |
| Chỉ thấy hành vi hoặc lời của một nhân vật | Chưa đủ để chắc chắn về góc nhìn; unclear nếu thiếu nguồn khác |
| Có nguồn tác phẩm phản đối rõ | critical, trích nguồn phản đối |
| Có nguồn tác phẩm ca ngợi rõ | endorsing, trích nguồn ca ngợi |
| Dấu hiệu trái chiều chưa xác định được góc nhìn | unclear, không tự chọn phía |
| Policy ngôn từ rõ nhưng cảnh thuộc nhãn critical | Vẫn xét ngôn từ theo policy, không miễn trừ |

Tại thời điểm hoàn tất bước 2 chưa gọi Gemma 2. Test hợp đồng chỉ xác
nhận tương thích schema/validator, không chứng minh các yêu cầu suy luận
này đã được model làm đúng. Không thêm test tìm chuỗi trong prompt rồi coi
đó là bằng chứng về chất lượng ngữ nghĩa.

## Cấu trúc output

```json
{
  "themes": [
    {"topic_id": "R1", "stance": "unclear", "evidence": []},
    {"topic_id": "R2", "stance": "not_applicable", "evidence": []},
    {"topic_id": "R3", "stance": "not_applicable", "evidence": []}
  ],
  "language": {"status": "no_violation", "evidence": []}
}
```

Đúng một mục cho mỗi R1/R2/R3, không phụ thuộc thứ tự. Mỗi bằng chứng chỉ có
`card_id` và `quote`. Không còn behavior_evidence/viewpoint_evidence; không
thêm giải thích hoặc quyết định block vào nhiệm vụ nhận diện.

| Nhãn | Điều kiện | Bằng chứng |
| --- | --- | --- |
| not_applicable | Chủ đề không xuất hiện | Prompt yêu cầu rỗng; không ép tìm nguồn cho chủ đề vắng mặt |
| critical | Có bằng chứng tác phẩm phản đối hành vi | Ít nhất một nguồn hỗ trợ góc nhìn, không chỉ hành vi |
| endorsing | Có bằng chứng tác phẩm ủng hộ/hợp thức hóa hành vi | Ít nhất một nguồn hỗ trợ góc nhìn, không chỉ hành vi |
| unclear | Chủ đề có mặt, chưa đủ cơ sở xác định góc nhìn | Được phép rỗng; không bắt phải tìm phản ứng chưa tồn tại |

Không có dấu hiệu cổ súy không đủ kết luận phê phán. Không có chủ đề khác
với có chủ đề nhưng chưa rõ góc nhìn. Schema chỉ bắt nhãn chắc chắn có nguồn;
không thể chứng minh bằng code rằng nguồn đó thực sự hỗ trợ nhãn. Việc này
phải chấm riêng trong thử nghiệm model, không lấy test hợp đồng làm chứng
nhận chất lượng ngữ nghĩa của prompt.

Các điều kiện chéo (nhãn chắc chắn cần evidence, đủ ba topic khác nhau) được
kiểm tra bằng validator Pydantic sau sinh; không giả định grammar JSON của
Ollama tự cưỡng chế được mọi điều kiện này. Output đúng JSON vẫn có thể sai
hợp đồng hoặc sai ý nghĩa.

Ngôn từ vẫn độc lập: no_violation / clear_violation / uncertain. Vi phạm rõ
cần nguồn; thiếu audience/policy chỉ cần uncertain khi thực sự có ngôn từ
cần xét. Cảnh phê phán không được miễn policy bản trẻ em.

## Kiểm tra nguồn và lỗi giao thức

`validate_sources()` chỉ nhận bản assessment đã parse cùng map ID → text của
snapshot hiện hành; không đọc/ghi project, gọi model hoặc sửa kết quả.

- ID phải tồn tại và quote phải là đoạn nguyên văn không rỗng trong đúng card.
- Không fuzzy matching, đổi ID, tự thêm nguồn hoặc tự đổi stance.
- Cùng ID có thể có nhiều đoạn trích khác nhau; cặp ID/quote lặp nguyên bị
  từ chối. Không nhầm nhiều đoạn nguồn hợp lệ với việc bịa nguồn.
- unclear không quote là kết quả hợp lệ, không phải lỗi kỹ thuật cần giữ xuất
  bản. not_applicable có evidence vẫn được kiểm tra nguồn nếu model trả;
  không tạo thêm lỗi giao thức chỉ vì bằng chứng thừa nhưng hợp lệ. Độ phù
  hợp của evidence/nhãn vẫn phải chấm riêng.
- critical/endorsing không evidence là lỗi hợp đồng. Không tự chuyển thành
  unclear hoặc chọn quote khác sau sinh để làm output qua kiểm tra.

Chưa bổ sung cơ chế quyết định xuất bản trong đợt này. Bước nối tiếp phải
giữ kiểm tra snapshot (gồm draft/audience/policy), quyền lưu/sửa, kết quả cũ
không áp vào bản mới; phân biệt lỗi giao thức với vi phạm nội dung và đo cả
block oan lẫn giữ oan. Không coi nhãn model là phê duyệt tự động để block.

## Quy trình phần 3 đã thực hiện trong cùng nhánh

1. Dùng schema/prompt này trong runner offline, chốt hash trước inference.
2. Giữ bộ 18 ca hồi quy; bổ sung 12 ca mới và nhãn trước khi chạy, ưu tiên
   unclear, chủ đề không xuất hiện và nguồn chỉ mô tả hành vi.
3. Gemma 2 với tham số cũ, hai lượt mỗi ca; đo nhãn, căn cứ, lỗi hợp đồng,
   block/giữ oan, vi phạm được xuất bản và trạng thái sau sửa. Không retry
   chọn lọc hoặc cứu output sau sinh. Báo cáo riêng bộ cũ và mới.

Quy trình đã chạy; kết quả không đạt nghiệm thu chất lượng xuất bản. Các báo
cáo/fixture chưa commit từ các đợt trước được giữ nguyên. Test hợp đồng không
phụ thuộc chúng; runner hồi quy dùng fixture 18 ca đã lưu như đã mô tả.
