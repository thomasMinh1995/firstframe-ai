# M3 Gói 3 — Qwen 2.5 7B, prompt v4 so với v3

Ngày 27/10/2026. Nhánh `feat/screenplay-evidence-feedback`. Đóng băng trước gọi, đúng sáu lượt được duyệt, timeout 60 giây/lượt, không retry hoặc chỉnh prompt trong đợt chạy. Giữ nguyên runtime, plan/roadmap/prototype, cấu hình và bằng chứng trước; chưa commit/PR.

## Kết luận

**V4 chưa cải thiện chất lượng critic trên bộ sáu ca này.** Hợp đồng bằng chứng giảm từ 5/6 xuống 4/6. Cả ba vi phạm vẫn được nhắc đúng về nội dung trong output thô, nhưng chỉ **1/3** có nhận xét đúng và đủ bằng chứng đến người dùng, so với 3/3 ở v3. Các bản tuân thủ vẫn nhận góp ý sai hoặc ép thêm quyết định/hành động không cần thiết.

Đổi kind từ intent_mismatch thành craft không đồng nghĩa sửa được lập luận: ca thư kín v4 vẫn nói sai rằng trạng thái thư không đúng yêu cầu tác giả; ca tự quyết vẫn đòi quyết định ngay. Suggestion rỗng cũng không xác nhận quan sát đúng: ca đặt đèn pin xuống có suggestion rỗng nhưng cáo buộc sai.

Không chốt v4/Gói 3 đạt chất lượng AI; không tự rollback hoặc mở vòng prompt/model tiếp. V3 trước đó cũng có lỗi chặn, nên đây không phải quyết định công nhận v3 đã đạt.

## Điều kiện đóng băng

Nguyên sáu project/request/ID/snapshot/thứ tự/expected từ Qwen v3. JSON input gửi model, schema output, mã nguồn ngắn và metadata action/dialogue/cảnh đích giữ nguyên; chỉ prompt đổi sang `screenplay-review-v4-author-control` và version tương ứng lưu trong record. Đã preflight fake trước freeze, giữ manifest/hash và bản sao source đúng lúc chạy.

Cùng `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, temperature 0,3, context yêu cầu 16384, timeout runner 60 giây; provider không gửi seed. `/api/ps` sau đợt này ghi context 16384. Timeout runtime hiện có 180 giây và `.env` không đổi. Một mẫu/ca không đủ chứng minh độ ổn định thống kê hoặc quan hệ nhân quả tổng quát.

## Lớp 1 — ID, quote và vai trò bằng chứng

| Chỉ số | V3 | V4 |
| --- | ---: | ---: |
| Model calls / retry | 6 / 0 | 6 / 0 |
| Parse schema | 6/6 | 6/6 |
| Timeout | 0 | 0 |
| Lượt có ID không tồn tại | 0 | 0 |
| Lượt quote không khớp chính ID đã dẫn | 0 | **1** |
| Evidence khớp đúng ID/quote | 11/11 | **10/11** |
| Lượt thiếu quote văn bản cảnh đích | 1 | 1 |
| Qua đầy đủ hợp đồng bằng chứng | 5/6 | **4/6** |

Hai lỗi v4 khác nhau, không gộp thành bịa ID:

- **Kết mở / vi phạm:** dẫn câu tha thứ dưới S4, nhưng S4 thực là hành động nhìn cha/kéo ghế. S5 cũng dẫn đúng câu tha thứ, tuy vậy một quote sai làm cả lượt failed/HTTP 502. Note còn dùng kind craft cho cáo buộc lệch ý đồ và không dẫn nguồn quyết định tác giả; đây là lỗi phân loại/đủ căn cứ bổ sung, không tự đổi kind hoặc thêm source để cứu ca. Theo validator hiện có, yêu cầu author_choice phụ thuộc kind, nên phần này được người đọc ghi riêng thay vì giả là guard đã bắt được hết.
- **Đèn pin / vi phạm:** chỉ dẫn A4 “Đèn pin bị hỏng, không thể sáng.” ID/quote đúng nhưng thiếu bằng chứng hành động kịch bản; failed/HTTP 502. Không biến lỗi thành notes rỗng hoặc bổ sung quote hộ model.

Không có lỗi provider/parse schema. Mỗi ca giữ request, raw output nguyên văn, project sau gọi và result; nguyên nhân tham chiếu và nội dung ghi riêng trong comparison. Bốn record ready lưu bằng ID gốc; raw provider giữ mã ngắn.

## Lớp 2 — Đối chiếu nhận xét

Đây là đọc đối chiếu của Codex, chưa phải tác giả/PO nghiệm thu; expected và kết quả chấm cũ không sửa. Đọc ý nghĩa của nhận xét, không chỉ đếm enum kind.

| Ca | Output v4 và đối chiếu v3 | API | Giây |
| --- | --- | --- | ---: |
| Kết mở / tuân thủ | Nói phong thư còn kín không phản ánh đúng trạng thái tác giả yêu cầu, dù A5 yêu cầu chính thư kín; đề xuất đổi câu thành “Phong thư kín vẫn nằm trên bàn” chỉ diễn đạt lại điều vốn đúng. Không còn khuyên mở thư như v3, nhưng vẫn tạo lỗi không tồn tại dưới kind craft | ready | 13,802 |
| Kết mở / vi phạm | Nhận ra xác nhận tha thứ làm mất kết mở nhưng dùng craft, sai một quote và thiếu dẫn ý đồ; v3 đúng kind/đủ hai nguồn | failed | 9,031 |
| Tự quyết / tuân thủ | Coi chưa có quyết định cuối cùng là cảnh lủng củng, khuyên bước ra cửa để quyết định. Nay dùng craft thay intent_mismatch của v3 nhưng vẫn ép thêm diễn tiến không được yêu cầu | ready | 8,876 |
| Tự quyết / vi phạm | Nhận ra giấu hộ chiếu trái quyền tự quyết, đủ hai nguồn; suggestion rỗng hợp lệ. Giữ phát hiện đúng và bỏ ký hiệu phạm vi ID gây nhiễu của v3 | ready | 8,575 |
| Đèn pin / tuân thủ | Nói Bình đặt đèn pin hỏng xuống trái M2, trong khi chính quote M2 nói “Bình đặt đèn pin hỏng xuống”. Hai nguồn đúng nhưng nhận xét sai. V3 gán sai việc kéo rèm và bị guard chặn; v4 nhận xét sai đến được UI | ready | 11,609 |
| Đèn pin / vi phạm | Nhận ra đèn hỏng không thể sáng nhưng không dẫn hành động đèn sáng; v3 có đủ hai nguồn. Diễn đạt vẫn nhắm vào “bật”, trong khi kết quả đèn sáng mới là mâu thuẫn quyết định | failed | 8,840 |

| Chỉ số nội dung | V3 | V4 |
| --- | ---: | ---: |
| Nhắc đúng mâu thuẫn trong output thô của ba bản vi phạm | 3/3 | 3/3 |
| Nhận xét đúng, qua hợp đồng, đến người dùng ở bản vi phạm | 3/3 | **1/3** |
| Cáo buộc sai trái lựa chọn tác giả ở bản tuân thủ — bất kể kind, output thô | 2/3 | 2/3 |
| Cáo buộc sai như trên đến được UI | 1/3 | **2/3** |
| Bản tuân thủ vẫn có góp ý sai hoặc ép thêm thiếu căn cứ | 3/3 | 3/3 |

Hai cáo buộc sai v4 là thư kín và đặt đèn xuống; ca thư kín nằm trong impact của craft. Ca tự quyết v4 không tuyên bố bắt buộc theo tác giả như v3, nhưng vẫn gây áp lực đưa ra quyết định không cần thiết. Giữ các loại lỗi riêng thay vì giảm điểm sai chỉ nhờ đổi tên nhãn.

## Ngân sách, dữ liệu và điểm dừng

Đúng **6 calls, 0 retry**, 8,575–13,802 giây/lượt, tất cả dưới 60 giây. Trung bình v4 10,122 giây so với v3 11,324 giây; chỉ là quan sát, không phải tối ưu độ trễ/SLA hoặc bằng chứng v4 tốt hơn.

Database/dataset riêng dưới `backend/.data/m3-scene-review-author-control-qwen7b-2026-10-27`; không mở database tác giả. Từng screenplay/M2 trước/sau bằng nhau, không tự sửa/nhận theo góp ý. Kiểm hash runtime/prompt đang chạy, plan/roadmap/prototype, `.env` và mọi bằng chứng model cũ đều qua; schema/input/nhãn/manifest cũ không bị sửa.

Đợt kiểm chứng kết thúc đủ sáu lượt. Không dùng test fake hoặc quote đúng làm nghiệm thu chất lượng. Không cần thêm một tầng guard suy luận hoặc vòng prompt v5 trong phạm vi yêu cầu này; trước quyết định tiếp cần giữ rõ lỗi diễn giải nguồn, lỗi ép thêm và lỗi hợp đồng bằng chứng vừa quan sát. Chưa triển khai thay đổi hoặc tạo PR.

[Manifest](../evaluations/m3-scene-review-author-control-qwen7b-2026-10-27/manifest.json) · [Input/request đóng băng](../evaluations/m3-scene-review-author-control-qwen7b-2026-10-27/inputs.json) · [Sáu kết quả](../evaluations/m3-scene-review-author-control-qwen7b-2026-10-27/results.json) · [So sánh tham chiếu và nội dung](../evaluations/m3-scene-review-author-control-qwen7b-2026-10-27/comparison.json) · [Audit](../evaluations/m3-scene-review-author-control-qwen7b-2026-10-27/integration-audit.json) · [Báo cáo v3](m3-constraint-first-qwen7b-comparison.md).
