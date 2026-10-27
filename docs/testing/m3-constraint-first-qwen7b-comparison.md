# M3 Gói 3 — Qwen 2.5 7B, prompt v3 so với v2

Ngày 27/10/2026. Nhánh `feat/screenplay-evidence-feedback`. Đúng sáu lượt được duyệt, tối đa 60 giây/lượt; đóng băng trước gọi, không retry hoặc chỉnh prompt theo kết quả. Không sửa runtime, plan/roadmap/prototype, cấu hình hoặc bằng chứng cũ trong lượt kiểm chứng; chưa commit/PR.

## Kết luận

**V3 phát hiện được ca đèn pin hỏng mà v2 bỏ sót, nhưng hồi quy ở các bản tuân thủ. Chưa nên chốt v3 là bản đạt chất lượng.** Phát hiện vi phạm tăng từ 2/3 lên 3/3 trong bộ này; đồng thời v3 gán sai lệch ý đồ cho 2/3 bản tuân thủ ở output thô và khuyên mở thư ở ca còn lại dù tác giả yêu cầu thư kín. Một nhận xét sai bị guard từ chối vì thiếu bằng chứng cảnh đích; nhận xét sai khác vẫn có thể hiển thị dù ID/quote đúng.

V2 cũng chưa đạt do bỏ sót đèn pin; kết quả này không biến v2 thành bản đã nghiệm thu. Không tự rollback hay mở thêm vòng tối ưu trong đợt này.

## Điều kiện đối chứng và bảo vệ dữ liệu

- Dùng nguyên sáu project/snapshot/request/thứ tự/expected của v2. Không sinh lại ID hay thay nội dung. Kiểm trước gọi xác nhận toàn bộ JSON input gửi model và schema output khớp v2, gồm mã ngắn, action/dialogue và is_target. Chỉ nội dung prompt đổi sang `screenplay-review-v3-constraint-first`; metadata version tương ứng được lưu riêng.
- Cùng `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, temperature 0,3, context 16384, timeout runner 60 giây. Provider không gửi seed; chỉ một mẫu/ca, không kết luận độ ổn định thống kê. Timeout runtime 180 giây và `.env` giữ nguyên.
- Preflight provider giả trước đóng băng; manifest giữ hash prompt/schema/input/code, bản sao source đúng lúc chạy và digest model. Có lock ngăn chạy lại, mỗi request chỉ gọi provider một lần.
- Database/dataset thử riêng dưới `backend/.data/m3-scene-review-constraint-first-qwen7b-2026-10-27`, không mở database tác giả. Cả sáu screenplay/M2 trước/sau giữ nguyên. Không tự sửa/nhận gợi ý hoặc thêm cổng chặn lưu nháp.
- Kiểm hash sau chạy xác nhận code đang kiểm chứng, plan/roadmap/prototype, cấu hình và toàn bộ hai đợt bằng chứng cũ không thay đổi. Kết quả chấm/expected trước giữ nguyên.

## Lớp 1 — ID, quote và độ đủ bằng chứng

| Chỉ số | V2 | V3 |
| --- | ---: | ---: |
| Model calls / retry | 6 / 0 | 6 / 0 |
| Parse schema | 6/6 | 6/6 |
| Lượt sai ID | 0 | 0 |
| Lượt quote không khớp ID đã cấp | 0 | 0 |
| Evidence khớp ID và quote | 11/11 | 11/11 |
| Thiếu bằng chứng văn bản cảnh đích | 0 | **1** |
| Qua đầy đủ hợp đồng bằng chứng | 6/6 | **5/6** |

Lỗi v3 ở `broken-flashlight-compliant`: chỉ dẫn `A5` — ràng buộc dùng ánh đèn đường — mà không dẫn khối kịch bản đích. ID và quote đó đều đúng, nhưng chưa đủ vai trò bằng chứng. API trả 502, checkpoint `failed`, không có note hợp lệ được lưu/hiển thị. Không sửa ID, bổ sung quote hộ model hoặc biến lượt lỗi thành notes rỗng.

Không có lỗi provider/timeout/parse schema; có một lỗi hợp đồng tham chiếu như trên. Toàn bộ request/raw output/project sau gọi/result đều lưu; nguyên nhân kỹ thuật và lỗi nội dung ghi riêng trong comparison. Năm lượt ready vẫn dùng ID nguồn gốc khi lưu, output provider giữ mã ngắn.

## Lớp 2 — Đúng nhận xét, hữu ích và dẫn sai

Đối chiếu của Codex, chưa phải tác giả/PO nghiệm thu. Đếm lệch ý đồ sai riêng với góp ý craft dẫn sai; không gộp thành điểm chất lượng.

| Ca | Output v3 và đối chiếu v2 | Kết quả API | Giây |
| --- | --- | --- | ---: |
| Kết mở / tuân thủ | Đòi thêm tương tác rồi khuyên cha **mở thư, đọc một đoạn**, trái giới hạn thư kín. Hồi quy so với v2 chỉ đề nghị nhìn/chạm thư | ready | 16,075 |
| Kết mở / vi phạm | Nhận ra xác nhận tha thứ trái kết mở; dẫn câu thoại và ràng buộc rõ. Giữ phát hiện đúng của v2; suggestion rỗng hợp lệ với HITL | ready | 8,180 |
| Tự quyết / tuân thủ | Gán `intent_mismatch` vì con gái chưa thể hiện quyết định ngay. Quyền tự quyết không bắt cô phải nói/quyết định ở cảnh này. Hồi quy từ uncertain/tùy chọn của v2 thành cáo buộc sai | ready | 11,335 |
| Tự quyết / vi phạm | Nhận ra giữ hộ chiếu ép ở lại, đủ hai nguồn; suggestion rỗng hợp lệ. Bỏ phương án v2 quá rộng “chỉ nói xin lỗi/không làm gì khác”. Có ký hiệu `S3:S5`/`A2:A5` trong observation gây nhiễu, không coi đó là evidence được guard xác nhận | ready | 10,391 |
| Đèn pin / tuân thủ | Gán sai kéo rèm là tạo nguồn sáng mới, dù M2 và ràng buộc cho dùng đèn đường qua rèm. Gợi ý tránh kéo rèm không có căn cứ. V2 chỉ góp ý thêm thoại ít ích lợi | failed: thiếu quote cảnh đích | 10,512 |
| Đèn pin / vi phạm | **Nhận ra đèn hỏng sáng trái giới hạn**, dẫn đúng hành động và ràng buộc; đề nghị dùng ánh sáng ngoài/rèm. Gỡ bỏ sót của v2 trong mẫu này. Diễn đạt nên nhắm vào kết quả đèn sáng: chỉ bấm công tắc đèn hỏng tự nó chưa phải mâu thuẫn | ready | 11,452 |

| Chỉ số nội dung | V2 | V3 |
| --- | ---: | ---: |
| Nhận ra vi phạm trong ba bản vi phạm | 2/3 | **3/3** |
| Bỏ sót trong ba bản vi phạm | 1/3 | 0/3 |
| Gán lệch ý đồ sai trong ba bản tuân thủ — output thô | 0/3 | **2/3** |
| Gán lệch ý đồ sai đến được UI — bản tuân thủ | 0/3 | **1/3** |
| Đề xuất rõ ràng phá ràng buộc ở bản tuân thủ | 0/3 | **1/3** |

Ca khuyên mở thư thuộc `craft`, nên không cộng thêm vào hai ca gán lệch ý đồ sai; nó vẫn là góp ý dẫn tác giả đi sai. Ca kéo rèm bị chặn không được tính là model đã nhận xét đúng hoặc không gây chặn oan về ngữ nghĩa. Guard chỉ chặn vì thiếu vai trò evidence, không vì hiểu được nội dung sai.

Đây là dấu hiệu trong output: ưu tiên tìm mâu thuẫn giúp bắt lỗi mục tiêu nhưng đồng thời model diễn giải quá mức điều chưa thể hiện thành vi phạm. Chưa có đủ mẫu để chứng minh quan hệ nhân quả ổn định hoặc kết luận v3 tốt hơn tổng thể.

## Ngân sách và điểm dừng

Đúng **6 model calls, 0 retry**; 8,180–16,075 giây/lượt, dưới 60 giây. Trung bình v3 11,324 giây so với v2 14,175 giây; chỉ là thời gian quan sát, không tuyên bố tối ưu độ trễ/SLA.

Chưa gọi Gói 3 đạt chất lượng AI hoặc dùng tỷ lệ bắt vi phạm 3/3 làm minh chứng tác phẩm/người viết tốt. Việc tiếp theo nếu được yêu cầu nên bắt đầu bằng người đọc xác nhận các ca gán sai và gợi ý mở thư, trước khi chọn một thay đổi hữu hạn; không tự mở thêm vòng prompt/model sau lượt này.

[Manifest đóng băng](../evaluations/m3-scene-review-constraint-first-qwen7b-2026-10-27/manifest.json) · [Input/request](../evaluations/m3-scene-review-constraint-first-qwen7b-2026-10-27/inputs.json) · [Sáu kết quả](../evaluations/m3-scene-review-constraint-first-qwen7b-2026-10-27/results.json) · [So sánh ID/quote và nội dung](../evaluations/m3-scene-review-constraint-first-qwen7b-2026-10-27/comparison.json) · [Audit](../evaluations/m3-scene-review-constraint-first-qwen7b-2026-10-27/integration-audit.json) · [Báo cáo v2](m3-short-sources-qwen7b-comparison.md).
