# M3 Gói 3 — Chạy lặp Qwen v4 trên cùng sáu ca

Ngày 27/10/2026. Người dùng chọn chạy lặp Qwen 2.5 7B, tối đa sáu lượt, timeout 60 giây/lượt, không retry. Đây là mẫu thứ hai độc lập trên mỗi input v4, không chạy bù chọn lọc các ca lỗi. Đợt chạy giữ nguyên runtime, plan/roadmap/prototype. Lần bổ sung vào PR #55 chỉ commit tài liệu và bằng chứng đã lưu, không chạy lại model.

## Kết luận

Lượt lặp có **5/6 ready**, so với 4/6 ở lượt Qwen v4 đầu. Tuy nhiên, **3/6 ca đổi trạng thái ready/failed**, nội dung góp ý cũng thay đổi và lỗi đọc ngược/ép thêm vẫn còn. Tỷ lệ qua hợp đồng cao hơn không chứng minh critic đã ổn định hay chất lượng đã đạt.

Không chọn output tốt hơn giữa hai lượt để công bố một bộ kết quả đạt. Hai mẫu/ca chưa đủ ước lượng độ tin cậy thống kê. Khác cách diễn đạt tự nó không phải lỗi; cần xét đúng quan sát, nguồn, tính hữu ích và dẫn sai.

## Đóng băng

Cùng model `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, prompt `screenplay-review-v4-author-control`, temperature 0,3, context 16384, timeout runner 60 giây. Provider không gửi seed. Không thay `.env` hoặc timeout runtime 180 giây.

Toàn bộ `inputs.json` giống lượt v4 đầu: prompt/input/schema, project/request/ID/snapshot/expected/thứ tự giữ nguyên. Có preflight provider giả, manifest/hash, source archive và lock chống chạy lại trước gọi thật. Database/dataset thử riêng tại `backend/.data/m3-scene-review-author-control-qwen7b-repeat2-2026-10-27`, không mở database tác giả.

## Tham chiếu và hợp đồng bằng chứng

| Chỉ số | V4 lượt đầu | V4 lượt lặp |
| --- | ---: | ---: |
| Calls / retry | 6 / 0 | 6 / 0 |
| Parse schema / timeout | 6 / 0 | 6 / 0 |
| Sai ID | 0 | 0 |
| Lượt sai quote tại ID được cấp | 1 | 0 |
| Quote khớp đúng ID | 10/11 | 11/11 |
| Lượt thiếu text cảnh đích | 1 | 1 |
| Qua đầy đủ hợp đồng | 4/6 | **5/6** |

Lượt mới failed ở đèn pin/tuân thủ: chỉ dẫn A5, thiếu quote cảnh đích. Lượt đầu failed ở kết mở/vi phạm do quote sai và đèn pin/vi phạm do thiếu quote kịch bản. Không thêm hoặc sửa evidence để cứu output. Tất cả request/raw output/result/project sau gọi và lỗi đều được giữ.

## Đối chiếu từng ca giữa hai lượt

Đây là nhận xét của Codex, chưa phải người viết/PO nghiệm thu; kết quả chấm cũ và kỳ vọng trước gọi không thay đổi.

| Ca | Trạng thái đầu → lặp | Nhận xét lượt lặp | Giây lặp |
| --- | --- | --- | ---: |
| Kết mở/tuân thủ | ready → ready | Nói con gái vẫn chưa nói gì khi chỉ dẫn S4, không đối chiếu câu “Cha…” ở S5; khuyên cha xin lỗi thêm. Nếu chỉ mô tả khoảnh khắc trước câu thoại thì cần giới hạn cách hiểu, chưa có căn cứ từ cả cảnh để đòi thêm thoại. Không còn cáo buộc thư kín sai trạng thái, nhưng chưa gọi là góp ý hữu ích | 12,491 |
| Kết mở/vi phạm | failed → ready | Nhận ra xác nhận tha thứ trái kết mở và nay dẫn đúng S5/A2. Vẫn dùng kind craft cho cáo buộc lệch ý đồ; nguồn đã đúng nhưng phân loại chưa đúng | 7,496 |
| Tự quyết/tuân thủ | ready → ready | Không còn ép bước ra cửa để quyết định ngay, nhưng vẫn nói động tác chưa rõ rồi đề nghị nghiêng người/nhíu mày để tăng cảm xúc. Lựa chọn tùy tác giả, chưa chứng minh cần sửa | 10,863 |
| Tự quyết/vi phạm | ready → ready | Nhận ra giấu hộ chiếu hạn chế tự quyết, đúng kind/hai nguồn; suggestion rỗng hợp lệ. Đây là ca giữ được phát hiện rõ và hợp đồng ở cả hai lượt | 8,271 |
| Đèn pin/tuân thủ | ready → failed | Gán kéo rèm/lấy ánh đèn đường trực tiếp là thêm nguồn sáng mới, dù M2 cho chính cách đó. Lượt đầu gán đặt đèn xuống trái M2; lỗi đọc ngược vẫn còn, lần này guard chặn vì thiếu text cảnh đích | 8,658 |
| Đèn pin/vi phạm | failed → ready | Dẫn đúng hành động đèn sáng và M2 đặt đèn xuống; nhận ra khác hành động đã chọn. Chưa trực tiếp giải thích đèn hỏng không thể sáng, nên không gọi là đã lý giải đầy đủ lỗi vật lý chỉ vì evidence hợp lệ | 7,838 |

Lượt lặp có hai ca vi phạm với nhận xét chính rõ và đủ nguồn (tha thứ/hộ chiếu), nhưng ca tha thứ vẫn sai kind. Ca đèn pin có nguồn hợp lệ cho khác biệt M2, còn trọng tâm suy luận chưa đầy đủ. Không gộp ba ready thành 3/3 đạt chất lượng. Trên bản tuân thủ, một ca đọc không đủ/không rõ phạm vi, một ca gợi ý động tác ít căn cứ và một ca gán sai rõ vẫn tồn tại.

## Ngân sách và bảo vệ dữ liệu

Đúng **6 calls, 0 retry**, 7,496–12,491 giây/lượt, tất cả dưới 60 giây. Trung bình 9,270 giây so với 10,122 giây trước; chỉ là thời gian quan sát, không benchmark tốc độ/SLA. Không thay seed hoặc chỉnh tham số để tìm output đẹp hơn.

Tất cả screenplay/M2 trước/sau bằng nhau; ready notes lưu bằng ID gốc, raw output giữ mã ngắn. Kiểm hash prompt/code/schema/input đang chạy, toàn bộ runtime, plan/roadmap/prototype, `.env` và mọi đợt bằng chứng cũ đều qua. Runtime khi chạy ở commit `e257960` của PR #55. Lần cập nhật PR sau đó chỉ bổ sung tài liệu/bằng chứng theo yêu cầu; audit giữ trạng thái tại thời điểm chạy. Không sửa code, rollback hoặc chạy thêm model.

Kết quả củng cố việc tách kỹ thuật khỏi chất lượng: nguồn/checkpoint/quyền tự sửa tiếp tục giữ dữ liệu, nhưng model chưa ổn định về hợp đồng và nhận xét. Nghiệm thu chất lượng critic/Gói 3 còn mở; không coi một lượt lặp có tỷ lệ ready cao hơn là đã gỡ lỗi chặn.

[Manifest](../evaluations/m3-scene-review-author-control-qwen7b-repeat2-2026-10-27/manifest.json) · [Input đóng băng](../evaluations/m3-scene-review-author-control-qwen7b-repeat2-2026-10-27/inputs.json) · [Kết quả/lỗi](../evaluations/m3-scene-review-author-control-qwen7b-repeat2-2026-10-27/results.json) · [So sánh từng ca](../evaluations/m3-scene-review-author-control-qwen7b-repeat2-2026-10-27/comparison.json) · [Audit](../evaluations/m3-scene-review-author-control-qwen7b-repeat2-2026-10-27/integration-audit.json) · [Lượt Qwen v4 đầu](m3-author-control-qwen7b-comparison.md).
