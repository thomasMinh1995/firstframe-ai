# M3 Gói 3 — Kiểm chứng mã nguồn ngắn với Qwen 2.5 7B

Ngày 27/10/2026. Nhánh `feat/screenplay-evidence-feedback`. Chạy đúng sáu lượt được duyệt, tối đa 60 giây/lượt, không retry hoặc sửa prompt trong đợt chạy. Không sửa runtime, plan/roadmap/prototype, cấu hình model, bằng chứng cũ; chưa commit/PR.

## Kết luận

**Cải thiện rõ hợp đồng tham chiếu trong bộ sáu ca này: 0/6 → 6/6 qua kiểm tra. Chưa chứng minh critic đủ tốt: vẫn chỉ nhận ra 2/3 vi phạm.** Ca đèn pin hỏng vẫn bị bỏ sót dù trích đúng hành động sai. Do phản hồi này nay qua guard tham chiếu, nhận xét thiếu căn cứ có thể đến người dùng; không tính thành đạt chất lượng chỉ vì không còn HTTP 502.

## Đóng băng và đối chứng

Dùng lại nguyên sáu project/snapshot, request, thứ tự ca và expected behavior từ baseline `m3-scene-review-qwen7b-2026-10-27`; không sinh lại UUID hoặc chỉnh dữ liệu. Schema output giữ nguyên. Thay đổi gồm mã nguồn ngắn, metadata `block_kind`/`is_target` và hướng dẫn đọc giao thức này; giữ nguyên nhiệm vụ suy luận còn lại. Không thể tách đóng góp riêng của ba thay đổi từ một lượt chạy này.

Model `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, temperature 0,3, context 16384, timeout runner 60 giây, khớp baseline. Provider hiện không gửi seed; mỗi input chỉ có một mẫu nên không coi đây là bằng chứng ổn định qua nhiều lần chạy. Không thay `.env` hoặc timeout runtime 180 giây hiện có.

Đã preflight bằng provider giả, đóng băng prompt/schema/input/code/digest trước gọi; lưu source code đúng lúc chạy và kiểm hash sau chạy. Database/dataset riêng dưới `backend/.data/m3-scene-review-short-sources-qwen7b-2026-10-27`, không mở database tác giả. Giữ lock không chạy lại.

## Lớp 1 — ID, quote và hợp đồng bằng chứng

| Chỉ số | Baseline | Mã ngắn + metadata |
| --- | ---: | ---: |
| Model calls / retry | 6 / 0 | 6 / 0 |
| Parse schema | 6/6 | 6/6 |
| Qua đầy đủ hợp đồng bằng chứng | 0/6 | **6/6** |
| Lượt có ID không tồn tại đúng dạng được cấp | 5/6 | **0/6** |
| Sai quote tại ID đã xác định được | 0 | 0 |
| Quote khớp tại đúng ID được cấp | 2/8 evidence | **11/11 evidence** |
| Lượt chỉ dẫn ý đồ, thiếu quote kịch bản (ID vốn đúng) | 1 | **0** |

Baseline có tám quote đều tìm thấy nguyên văn ở đâu đó trong nguồn, nhưng chỉ hai quote đi cùng ID hợp lệ; không đánh đồng lỗi ID với bịa nội dung trích dẫn. Lượt kết mở/vi phạm trước chỉ dẫn M2 và ý tưởng; lần mới dẫn cả câu thoại đích và M2. Tất cả bảy nhận xét mới lưu bằng ID nguồn gốc, còn output provider giữ mã ngắn; không sửa mã hoặc tìm quote để cứu phản hồi.

Không có lỗi provider, timeout, schema hay tham chiếu trong lượt mới; vẫn lưu toàn bộ request/raw output/project sau gọi/result cho cả sáu ca. Lỗi nội dung được ghi riêng trong comparison, không biến thành lỗi HTTP hoặc tự đổi nhãn.

## Lớp 2 — Nhận xét đúng, hữu ích và khả năng dẫn sai

Đây là đối chiếu của Codex, chưa phải tác giả/PO nghiệm thu. Không sửa kết quả chấm cũ hoặc kỳ vọng đã đóng băng. Craft/uncertain không tự bị chấm thành vi phạm ý đồ chỉ vì người đọc không thích đề xuất.

| Ca | Baseline | Lượt mới | Giây mới |
| --- | --- | --- | ---: |
| Kết mở / tuân thủ | Nói sai con gái không hành động | Không còn nhận xét sai đó. Gợi ý thêm tương tác/căng thẳng vẫn thiên về gu, chưa chứng minh cần thêm; không chốt tha thứ hoặc mở thư | 14,471 |
| Kết mở / vi phạm | Nhận ra mâu thuẫn nhưng thiếu dẫn câu kịch bản | Nhận ra lời tha thứ đóng kết mở, đủ hai nguồn. Không đề xuất sửa vẫn hợp lệ với HITL; tác giả tự quyết | 10,015 |
| Tự quyết / tuân thủ | Ví dụ lẫn tiếng Trung/nội tâm, hữu ích thấp | Ghi nhận lối đi trống phù hợp; thêm uncertain về nhìn cửa. Không còn lẫn ngôn ngữ, nhưng thêm cử chỉ vẫn chưa thật cần thiết | 13,852 |
| Tự quyết / vi phạm | Nhận ra giữ hộ chiếu trái tự quyết, sai ID | Nhận xét đúng và đủ nguồn. Gợi ý “cha chỉ nói xin lỗi và không làm gì khác” quá rộng, có thể làm mất hành động đặt thư đã chọn; chưa gọi là phương án sửa tốt | 10,750 |
| Đèn pin / tuân thủ | Chê thoại cứng trong cảnh chỉ có action | Không còn khẳng định thoại đang có bị cứng, nhưng vẫn đề nghị thêm câu giải thích điều hành động đã thể hiện; hữu ích thấp | 15,841 |
| Đèn pin / vi phạm | Bỏ sót, khuyên chỉnh ánh đèn pin hỏng | **Vẫn bỏ sót** đèn hỏng sáng; chuyển sang nhận xét sự tự nhiên lời thoại dù cảnh chỉ có action. Thêm thoại không loại bỏ hành động sai | 20,120 |

Phát hiện vi phạm trên output thô giữ **2/3 → 2/3**, bỏ sót **1/3 → 1/3**. Hai nhận xét sai thực tế trên bản tuân thủ của baseline không lặp lại trong mẫu mới. Tuy vậy cả ba bản tuân thủ vẫn nhận góp ý có tính tùy chọn hoặc ích lợi thấp; không được coi bản tuân thủ bắt buộc phải có notes rỗng. Ca đèn pin/vi phạm không còn trực tiếp khuyên chỉnh ánh đèn pin như baseline, nhưng việc chuyển sang thêm thoại vẫn không sửa được vi phạm. Sửa ID không giải quyết được lỗi hiểu nội dung này.

## Ngân sách và bảo vệ dữ liệu

Sáu lượt nằm trong **10,015–20,120 giây**, dưới 60 giây/lượt. Trung bình baseline 12,794 giây, lượt mới 14,175 giây; không có bằng chứng cải thiện độ trễ và không tối ưu độ trễ trong đợt này.

Mọi screenplay/M2 trước và sau bằng nhau; không tự nhận hoặc sửa theo góp ý. Snapshot, raw output, manifest, nhãn/kết quả baseline giữ nguyên. Kiểm hash plan/roadmap/prototype/`.env` và code đang chạy đều qua. Không mở vòng tự sửa, judge mới hoặc chạy bù ca lỗi.

## Đề xuất nhỏ tiếp theo

Giữ adapter mã ngắn và metadata vì lỗi tham chiếu đã giảm trong bộ đối chứng. **Chưa gọi Gói 3 đạt chất lượng AI.** Nếu triển khai bước 3 tiếp, giới hạn vào lỗi đã xác nhận: ưu tiên đối chiếu hành động thực có với ràng buộc trước khi nêu góp ý tùy chọn, không mặc định thêm thoại để sửa cảnh. Chưa thực hiện thay đổi hoặc chạy kiểm chứng đó trong đợt này; không mở chuỗi tối ưu model/prompt.

[Manifest trước chạy](../evaluations/m3-scene-review-short-sources-qwen7b-2026-10-27/manifest.json) · [Sáu input và request đóng băng](../evaluations/m3-scene-review-short-sources-qwen7b-2026-10-27/inputs.json) · [Kết quả đủ sáu lượt](../evaluations/m3-scene-review-short-sources-qwen7b-2026-10-27/results.json) · [So sánh kỹ thuật và nhận xét từng ca](../evaluations/m3-scene-review-short-sources-qwen7b-2026-10-27/comparison.json) · [Audit bảo vệ dữ liệu/hash](../evaluations/m3-scene-review-short-sources-qwen7b-2026-10-27/integration-audit.json).
