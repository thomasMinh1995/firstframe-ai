# M3 Gói 3 — Gemma 2 9B so với Qwen 2.5 7B, prompt v4

Ngày 27/10/2026. Chạy theo lựa chọn người dùng: Gemma 2 9B, cùng sáu ca/prompt v4, tối đa sáu lượt và 60 giây/lượt, không retry. Đợt chạy giữ nguyên runtime, plan/roadmap/prototype và bằng chứng cũ. Lần bổ sung vào PR #55 chỉ commit tài liệu và bằng chứng đã lưu, không chạy lại model.

## Kết luận

Gemma không gán sai trái lựa chọn tác giả cho ba bản tuân thủ trong mẫu này, khác hai cáo buộc sai của Qwen v4. Tuy nhiên, **cả hai chỉ có 4/6 lượt qua hợp đồng và 1/3 ca vi phạm có nhận xét chính đúng/đủ nguồn đến người dùng**. Gemma vẫn sinh nhiều góp ý thêm chi tiết chưa có căn cứ cần thiết, ba phản hồi tiếng Anh dù yêu cầu tiếng Việt, và ca đèn pin chưa có nhận xét trực tiếp/đủ bằng chứng dùng được.

Chưa có cơ sở tự chuyển model mặc định hoặc chốt chất lượng Gói 3. Đây là bằng chứng bổ sung, không thay nghiệm thu còn mở đã ghi trong PR #55. Không mở vòng prompt/model tiếp hoặc sửa critic trong đợt này.

## Đóng băng và điều kiện

- Model đã có sẵn `gemma2:9b-instruct-q4_K_M`, digest `c20bec88025f3aefa420efd64dca0ee4abc8e36078d6b74b0f660cdcbd5d1982`. Không tải model, không API trả phí. Chỉ clone provider trong runner riêng; `.env` và runtime giữ Qwen.
- Toàn bộ `inputs.json` giống Qwen v4 đã lưu: cùng project/request/ID/snapshot/expected/thứ tự và frozen request. Prompt `screenplay-review-v4-author-control`, schema, mã ngắn, action/dialogue/cảnh đích không đổi.
- Temperature 0,3, context yêu cầu 16384, timeout provider 60 giây; giống tham số yêu cầu của Qwen v4. Provider không gửi seed. Có preflight fake trước freeze, manifest/hash, source archive và lock chống chạy lại.
- Context thực sau gọi: Gemma **8192**, Qwen v4 đã ghi **16384**. Không thể gọi đây là đối chứng cùng effective context. Payload được giữ nguyên, không tự cắt, nhưng guard byte không chứng minh model đã xử lý mọi token hoặc chứng minh đã có truncation. Một mẫu/ca không đủ kết luận thống kê hay tách ảnh hưởng context khỏi model.

## Lớp 1 — Hợp đồng nguồn

| Chỉ số | Qwen v4 | Gemma v4 |
| --- | ---: | ---: |
| Model calls / retry | 6 / 0 | 6 / 0 |
| Có output / parse schema | 6/6 | 6/6 |
| Timeout | 0 | 0 |
| Lượt sai ID | 0 | 0 |
| Lượt quote không khớp đúng ID | 1 | 0 |
| Evidence khớp đúng ID/quote | 10/11 | 18/18 |
| Lượt có note thiếu text cảnh đích | 1 | **2** |
| Qua đầy đủ hợp đồng | **4/6** | **4/6** |

Hai lượt Gemma failed/HTTP 502 đều do note phụ chỉ dẫn S2 thuộc cảnh liền trước:

1. Tự quyết/vi phạm: note intent_mismatch đầu có đủ S5/A4 và phát hiện đúng; note uncertain cuối chỉ dẫn cảnh trước. Theo hợp đồng mỗi note cần text cảnh đích, cả lượt bị từ chối.
2. Đèn pin/vi phạm: note craft phụ chỉ dẫn S2 cảnh trước. Note chính dẫn S4/A1 đủ vai trò hình thức, nhưng S4 là kéo rèm, không phải hành động đèn pin sáng mà nhận xét nói tới; lỗi hỗ trợ lập luận này ghi riêng ở lớp nội dung.

Không sửa ID/quote, không lọc bỏ note phụ sau khi thấy output để biến failed thành ready, không chạy lại. Lỗi class/status/raw output/project sau gọi của cả sáu ca đều giữ. Không có lỗi provider/timeout/parse schema trong lượt mới. Bốn record ready lưu ID nguồn gốc, raw output giữ mã ngắn.

## Lớp 2 — Nhận xét có giúp người viết không?

Đối chiếu của Codex, chưa phải người viết/PO nghiệm thu. Giữ nguyên nhãn kỳ vọng và kết quả chấm trước. Không tự coi mọi góp ý craft là cáo buộc lệch ý đồ hoặc mọi đề xuất thêm là vi phạm.

| Ca | Gemma v4 và đối chiếu Qwen v4 | API | Giây |
| --- | --- | --- | ---: |
| Kết mở/tuân thủ | Ghi nhận kết mở phù hợp, đề nghị khoảng dừng trước “Cha…”. Có thể là lựa chọn nhịp tùy tác giả, chưa chứng minh bản hiện tại sai; không phán thư kín sai trạng thái như Qwen. Phản hồi tiếng Anh | ready | 23,401 |
| Kết mở/vi phạm | Note đầu nhận ra câu tha thứ trái kết mở, đủ S5/A1. Note craft phụ thêm im lặng/ánh mắt để mơ hồ, nhưng thêm biểu cảm không tự loại bỏ câu chốt tha thứ. Có ích ở nhận xét chính, không coi toàn bộ phương án đã giải quyết lỗi. Tiếng Anh | ready | 23,094 |
| Tự quyết/tuân thủ | Không ép con gái quyết định ngay như Qwen. Đề nghị đảo thứ tự đặt thư/lùi lại và thêm biểu cảm để tăng cảm xúc; chưa chỉ ra lỗi cụ thể. Thay dàn cảnh là lựa chọn sáng tạo để tác giả cân nhắc, không phải sửa bắt buộc | ready | 23,097 |
| Tự quyết/vi phạm | Nhận ra giữ hộ chiếu trái giới hạn, đủ hai nguồn ở note chính; các note thêm cảm xúc/căng thẳng ích lợi thấp và note cuối thiếu nguồn cảnh đích. Qwen có phát hiện đúng đến được UI; Gemma cả lượt failed | failed | 31,344 |
| Đèn pin/tuân thủ | Không cáo buộc đặt đèn xuống trái M2 như Qwen. Nhưng đòi mô tả rõ cách đọc rồi thêm cúi người/đọc to từng câu dù ánh đèn và nghiêng giấy đã gợi cách đọc; ích lợi chưa rõ, không nên ép thêm | ready | 38,683 |
| Đèn pin/vi phạm | Nhắc dùng đèn pin hỏng/đèn đường khác M2, nhưng không chỉ rõ kết quả đèn hỏng sáng là mâu thuẫn chính và không dẫn S5. Note phụ đòi phản ứng cảm xúc, chỉ dẫn cảnh trước. Nhận ra khác biệt một phần, chưa gọi phát hiện đầy đủ/có ích | failed | 44,644 |

Tổng hợp nội dung:

- Qwen v4 nhắc đúng ba vi phạm trong output thô nhưng chỉ ca hộ chiếu qua hợp đồng. Gemma nhận ra rõ hai vi phạm tha thứ/hộ chiếu; ca đèn pin chỉ một phần và thiếu bằng chứng trực tiếp. Chỉ ca tha thứ có nhận xét chính đúng/đủ nguồn đến người dùng.
- Gemma không lặp hai cáo buộc sai về thư kín/đặt đèn xuống của Qwen, nhưng điều đó không đồng nghĩa ba bản tuân thủ được góp ý hữu ích. Ca nhịp im lặng là tùy chọn; các đề xuất tăng cảm xúc/đọc to cần tác giả quyết định và chưa chứng minh cần thiết.
- Gemma có **3/6 phản hồi tiếng Anh**: hai ca kết mở và ca đèn pin vi phạm. Đây là lỗi bám yêu cầu ngôn ngữ/khả năng sử dụng, không phải lỗi source ID/quote.
- Số note thô Gemma **11** so với Qwen **6**. Góp ý nhiều hơn không phải bằng chứng tốt hơn; note phụ còn làm hai lượt mất kết quả hợp lệ ở mức toàn lượt.

## Ngân sách, dữ liệu và điểm dừng

Đúng **6 lượt, 0 retry**, tất cả **23,094–44,644 giây**, dưới 60 giây. Trung bình Gemma **30,710 giây**, Qwen v4 **10,122 giây**; chỉ là thời gian quan sát, không benchmark tải cô lập/SLA hoặc bằng chứng tốc độ ổn định. Không lấy ba timeout ở đợt Gemma v3 để thay kết quả của đợt v4 này.

Database/dataset riêng dưới `backend/.data/m3-scene-review-author-control-gemma2-2026-10-27`; không mở database tác giả. Mọi screenplay/M2 trước/sau bằng nhau. Kiểm hash code/prompt/schema/input đã freeze, runtime, plan/roadmap/prototype, `.env` và các đợt bằng chứng cũ đều qua. Code runtime vẫn là bản đã review trong PR #55. Lần cập nhật PR này chỉ bổ sung báo cáo/bằng chứng, không sửa runtime hoặc thay kết quả; audit giữ trạng thái tại thời điểm chạy.

Đợt này kết thúc đủ sáu lượt. Không tự đổi runtime sang Gemma, không cứu output failed để tăng tỷ lệ đạt và không mở prompt v5. Chất lượng critic và nghiệm thu Gói 3 tiếp tục mở; kết quả kỹ thuật đã review trong PR #55 không bị biến thành chứng nhận chất lượng model.

[Manifest](../evaluations/m3-scene-review-author-control-gemma2-2026-10-27/manifest.json) · [Sáu input](../evaluations/m3-scene-review-author-control-gemma2-2026-10-27/inputs.json) · [Mọi kết quả/lỗi](../evaluations/m3-scene-review-author-control-gemma2-2026-10-27/results.json) · [So sánh kỹ thuật/nội dung](../evaluations/m3-scene-review-author-control-gemma2-2026-10-27/comparison.json) · [Audit](../evaluations/m3-scene-review-author-control-gemma2-2026-10-27/integration-audit.json) · [Qwen v4 đã lưu](m3-author-control-qwen7b-comparison.md).
