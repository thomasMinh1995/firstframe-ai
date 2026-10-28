# M3 Gói 3 — Gemma 2 9B so với Qwen 2.5 7B, cùng prompt v3

Ngày 27/10/2026. Nhánh `feat/screenplay-evidence-feedback`. Chạy đúng sáu lượt Gemma được duyệt, timeout provider 60 giây/lượt; đóng băng trước gọi và không retry. Không thay runtime, plan/roadmap/prototype, `.env` hoặc bằng chứng Qwen; chưa commit/PR.

## Kết luận

**Chưa có cơ sở chuyển runtime sang Gemma để gỡ lỗi critic.** Gemma có output ở 3/6 ca và timeout ở ba ca còn lại, gồm cả ca đèn pin vi phạm. Không thể kết luận Gemma đã xử lý tốt lỗi đèn pin hoặc ít gán sai hơn trên đủ bộ ca.

Trong các output nhận được, Gemma giữ được ID/quote và nhận ra lời tha thứ đóng kết mở. Nhưng cùng phản hồi đó lại bàn cách làm rõ sự do dự trước khi tha thứ, đi lệch hướng kết mở; một phản hồi tiếng Anh dù yêu cầu tiếng Việt. Hai bản tuân thủ có output vẫn bị đề nghị thêm biểu cảm hoặc làm hành động cụ thể hơn mà chưa chỉ ra lỗi rõ.

**Có lý do sửa phạm vi/hướng dẫn góp ý của critic ở mức nhỏ, chưa có lý do xây lại harness hoặc thêm judge.** Cần phân biệt mâu thuẫn thật với điều chưa thể hiện, cho phép không góp ý, và giữ toàn bộ phản hồi nhất quán với ý đồ tác giả. Chưa triển khai sửa này trong đợt kiểm chứng.

## Điều kiện thử và giới hạn đối chứng

Chọn model local đã có sẵn `gemma2:9b-instruct-q4_K_M`, digest `c20bec88025f3aefa420efd64dca0ee4abc8e36078d6b74b0f660cdcbd5d1982`, 9.2B Q4_K_M theo metadata local. Không tải model hoặc gọi API trả phí. Chỉ clone cấu hình provider trong runner riêng sang Gemma; `.env` và đường runtime tiếp tục giữ Qwen.

Toàn bộ `inputs.json` khớp byte/hash với đợt Qwen v3: cùng sáu project/request/ID/snapshot/expected/thứ tự, prompt `screenplay-review-v3-constraint-first`, schema output, mã ngắn và metadata action/dialogue/cảnh đích. Giữ temperature 0,3, yêu cầu `num_ctx=16384`, timeout 60 giây; provider hiện không gửi seed. Freeze gồm code/prompt/schema/input/digest, bản sao source và preflight fake trước gọi thật.

**Giới hạn context thực tế:** tag Gemma và `/api/ps` sau chạy ghi context 8192 dù request yêu cầu 16384. Đợt Qwen cũ không ghi `/api/ps` để đối chiếu context thực. Vì vậy không gọi đây là đối chứng cùng effective context. Guard byte giữ nguyên payload, không tự cắt nguồn, nhưng không có token metrics để chứng minh model đã tiếp nhận toàn bộ context hoặc khẳng định đã bị cắt. Không tự giảm context/chỉnh input/chạy lại để làm kết quả đẹp hơn.

Timeout client không bảo đảm server đã dừng sinh, nên các lượt sau có thể chịu ảnh hưởng; đây không phải benchmark tải cô lập hoặc bằng chứng khả năng tổng quát của hai model. Chỉ một mẫu/ca, không kết luận thống kê.

## Kết quả đủ sáu lượt

| Ca | Gemma | Tổng giây API | Đối chiếu nội dung với Qwen v3 đã lưu |
| --- | --- | ---: | --- |
| Kết mở / tuân thủ | ready, 1 note | 22,430 | Đề nghị thêm mắt trĩu nặng/bàng hoàng để diễn đạt suy tư. Chưa chứng minh cần thêm biểu cảm. Không khuyên mở thư như Qwen |
| Kết mở / vi phạm | ready, 3 notes | 39,548 | Nhận ra xác nhận tha thứ trái kết mở, đủ hai nguồn. Nhưng note craft tiếp lại khuyên làm rõ do dự trước khi tha thứ, note uncertain hỏi tha thứ thật hay để làm cha vui; phản hồi tiếng Anh trái yêu cầu tiếng Việt |
| Tự quyết / tuân thủ | ready, 1 note | 52,403 | Không gán intent_mismatch như Qwen, nhưng hỏi thêm hành động cụ thể hơn dù đặt thư/lùi lại/để lối đi trống đã cụ thể; ích lợi thấp |
| Tự quyết / vi phạm | timeout, failed | **61,417** | Không có output, chưa chấm được. Qwen có phát hiện đúng |
| Đèn pin / tuân thủ | timeout, failed | **60,388** | Không có output, chưa biết Gemma giữ đúng hay gán sai. Qwen gán sai kéo rèm là tạo nguồn sáng mới và bị từ chối vì thiếu target evidence |
| Đèn pin / vi phạm | timeout, failed | **60,323** | Không có output, chưa biết Gemma phát hiện được lỗi mục tiêu. Qwen có phát hiện đúng |

Ba lượt thành công đều dưới 60 giây. Ba lượt timeout có cấu hình provider 60 giây nhưng tổng API quan sát 60,323–61,417 giây; **không đạt ngân sách**, không trình bày như tất cả lượt dưới 60 giây. Giữ nguyên lỗi `ProviderTimeoutError`, HTTP 504 và checkpoint failed. Raw output các ca timeout là null, không có output để chấm; không cố lấy lại hoặc chạy bù. Ba lượt có output đều parse schema và qua hợp đồng nguồn. Không có lỗi parse schema trong output đã nhận.

## Tách tham chiếu khỏi nội dung

| Chỉ số | Qwen v3 | Gemma v3 |
| --- | ---: | ---: |
| Số lượt / retry | 6 / 0 | 6 / 0 |
| Có output để đọc/chấm | 6/6 | **3/6** |
| Timeout | 0 | **3** |
| Lượt sai ID/quote trong số có output | 0/6 | 0/3 |
| Evidence khớp ID/quote | 11/11 | 6/6 |
| Thiếu vai trò bằng chứng cảnh đích | 1 | 0 trong 3 output |
| Ready qua đầy đủ hợp đồng | 5/6 | **3/6** |
| Phát hiện vi phạm | 3/3 bản vi phạm có output | **1/1 bản vi phạm có output; 2 ca timeout chưa chấm** |
| Gán lệch ý đồ sai ở bản tuân thủ — output thô | 2/3 | **0/2 bản có output; 1 ca timeout chưa chấm** |

Không viết Gemma “0/3 gán sai” hoặc “1/3 phát hiện” như điểm năng lực: timeout là thiếu bằng chứng, không phải nhận xét đúng hay bỏ sót. Mặt khác, trong ngân sách đã duyệt, người dùng chỉ nhận được một phản hồi có phát hiện vi phạm; phản hồi đó còn chứa góp ý thứ cấp đi ngược ý đồ.

Phần note nhận ra lỗi có ích không tự xác nhận các note còn lại cùng lượt có ích. Lỗi ngôn ngữ/craft/suy diễn không phải lỗi ID/quote nên guard hiện tại không chặn; đây là giới hạn của việc xác thực bằng chứng, không phải bằng chứng guard bị hỏng.

## Có nên sửa critic?

**Có, ở phạm vi hướng dẫn đánh giá và điều kiện đưa góp ý.** Các dữ liệu đã lưu cho thấy thay model chưa loại bỏ khuynh hướng đòi thêm chi tiết mà không chứng minh vấn đề. Cách sửa nhỏ nhất được đề xuất, chưa áp dụng:

1. Chỉ kết luận intent_mismatch khi hành động/kết quả mâu thuẫn trực tiếp với lựa chọn tác giả. Thiếu biểu cảm/thoại/quyết định tức thời không tự là vi phạm, trừ khi tác giả bắt buộc chi tiết đó xuất hiện ở cảnh này. Nếu không có vấn đề có căn cứ, trả notes rỗng; không mặc định thêm hành động/thoại.
2. Áp dụng bảo toàn ý đồ cho **toàn bộ observation, impact, suggestion và question**, không chỉ trường suggestion. Sau khi đã phát hiện chốt tha thứ trái nguồn, không thêm note craft/uncertain tiếp tục giả định cần phát triển cảnh tha thứ. Suggestion rỗng vẫn hợp lệ; tác giả tự sửa.

Giữ schema, mã nguồn ngắn, snapshot, kiểm ID/quote và HITL. Chưa có bằng chứng cần thêm router/model judge, hai lượt review hay vòng tự sửa. Không nên đổi model mặc định chỉ từ ba output và không nên tiếp tục nhiều vòng prompt không có điểm dừng. Chưa gọi critic đạt chất lượng hoặc thay đổi tiêu chí nghiệm thu. Bất kỳ lượt kiểm chứng sửa tiếp cần đóng băng và được duyệt riêng; đợt này đã kết thúc đủ sáu lượt.

## Dữ liệu và bằng chứng

Database/dataset thử riêng dưới `backend/.data/m3-scene-review-constraint-first-gemma2-2026-10-27`; không mở database tác giả. Mọi screenplay/M2 trước/sau giữ nguyên; ready notes lưu ID nguồn gốc, raw provider giữ mã ngắn. Checkpoint lỗi vẫn cho tự viết/lưu; không tự nhận, retry hoặc sửa dữ liệu theo góp ý.

Kiểm hash cuối xác nhận toàn bộ backend runtime, prompt, plan/roadmap/prototype, `.env` và các đợt Qwen cũ không thay. Không chạy lại build/browser vì không sửa runtime/UI; các assert tích hợp xác nhận request đóng băng và dữ liệu trước/sau từng ca. `git diff --check` qua.

[Manifest](../evaluations/m3-scene-review-constraint-first-gemma2-2026-10-27/manifest.json) · [Sáu input](../evaluations/m3-scene-review-constraint-first-gemma2-2026-10-27/inputs.json) · [Mọi kết quả/lỗi](../evaluations/m3-scene-review-constraint-first-gemma2-2026-10-27/results.json) · [So sánh và nhận xét từng ca](../evaluations/m3-scene-review-constraint-first-gemma2-2026-10-27/comparison.json) · [Context thực sau chạy](../evaluations/m3-scene-review-constraint-first-gemma2-2026-10-27/ollama-ps-after.json) · [Audit](../evaluations/m3-scene-review-constraint-first-gemma2-2026-10-27/integration-audit.json).
