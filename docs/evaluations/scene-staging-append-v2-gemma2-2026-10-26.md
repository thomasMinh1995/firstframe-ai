# Chốt hữu hạn Gói 2 — ba ca append v2

- Ngày 26/10/2026; nhánh `feat/scene-staging-suggestions`.
- Theo phạm vi đã thống nhất: đúng ba ca append đã lưu, một model Gemma 2 9B, 120 giây/yêu cầu, không retry hoặc tối ưu thêm. Không yêu cầu phiên trải nghiệm người dùng trước khi tiếp tục Gói 3; chưa thay tiêu chí nghiệm thu.
- **Kết luận:** 3/3 qua hợp đồng/thời gian, nhưng chưa có ca nào chứng minh thêm được diễn tiến tiếp nối hữu ích. Dừng vòng prompt tại đây, giữ lỗi nội dung còn mở. PR dùng để review kỹ thuật, **chưa sẵn sàng merge/không tuyên bố Gói 2 đạt toàn bộ nghiệm thu**.

## Đóng băng và bằng chứng

[Manifest](scene-staging-append-v2-gemma2-2026-10-26/manifest.json) được ghi trước inference, chứa thời điểm, digest model, hash prompt/schema/service/input/runner và thứ tự lượt chạy.

- Model `gemma2:9b-instruct-q4_K_M`, temperature 0.3, yêu cầu num_ctx 16384; ngân sách/hạn tường 120 giây. Gemma 2 có giới hạn context native 8192 đã ghi nhận ở đợt trước; đây không phải so sánh context chuẩn hóa.
- Giữ đúng nguồn/cặp draft, ID và yêu cầu tác giả của ba ca append trong đợt schema một cảnh. Chỉ prompt v2 và cách biểu diễn đầu vào tham chiếu/vị trí chèn là thay đổi cần thử; không sửa `.env` hoặc model mặc định.
- [Input ba ca](scene-staging-append-v2-gemma2-2026-10-26/inputs.json), [prompt v2](scene-staging-append-v2-gemma2-2026-10-26/prompt.md), [schema một cảnh](scene-staging-append-v2-gemma2-2026-10-26/single-schema.json), [runner](scene-staging-append-v2-gemma2-2026-10-26/run.py).
- [Baseline v1 của đúng ba ca](scene-staging-append-v2-gemma2-2026-10-26/baseline.json) sao nguyên object output/raw/thời gian từ đợt Gemma 2 schema một cảnh, không đổi nhãn hay chạy lại baseline.
- [Toàn bộ kết quả v2](scene-staging-append-v2-gemma2-2026-10-26/results.json), [audit và hash từng file](scene-staging-append-v2-gemma2-2026-10-26/audit.json). Giữ cả HTTP request/raw response, output sau kiểm tra và thời gian từng lượt, không chọn lọc.
- Gọi hàm service/provider thật bằng Ollama local; không sửa database tác giả, không tự dùng kết quả, không chạy API trả phí. Chưa phải luồng browser với model thật hoặc nghiệm thu người dùng.

## So sánh trước/sau

| Ca | V1 | V2 / thời gian | Đối chiếu nội dung |
| --- | --- | --- | --- |
| quiet-append | Đúng schema; action sao nguyên cảnh cha đã đặt thư/con gái nhìn thư. | Đúng schema / 16,143 giây | Quay về mở đầu: “Cha ngồi bên bàn bếp với lá thư … Con gái bước vào”. Mốc chèn đã là sau khi đặt thư/rút tay; đây là kể lại phần trước, không phải hành động tiếp nối. |
| comedy-append | Đúng schema; action sao nguyên sự cố muối và đẩy đường. | Đúng schema / 10,835 giây | Action vẫn sao nguyên sự cố và đẩy đường; tiếng cười chỉ nằm trong transition. Chọn dùng không tự đưa transition vào action, nên chưa có diễn tiến mới trong cảnh. |
| limits-append | Đúng schema; action sao nguyên việc Nam đặt cốc/Mai dừng tay. | Đúng schema / 8,988 giây | Quay về mở đầu: “Mai đứng lên, cầm túi … Nam … nhìn chiếc cốc trống”. Không tiếp tục từ mốc Nam đã đặt thêm cốc. |

Cả ba không tự mở thư/thêm người bị cấm trong lượt này, nhưng giữ giới hạn không đủ để coi là đúng tác vụ append. Số action trùng nguyên văn cảnh tham chiếu giảm từ 3 xuống 1; **không coi đó là cải thiện hữu ích**, vì hai ca còn lại lặp phần khác của story plan. Trung vị v2 10,835 giây; một lượt mỗi ca, không kiểm soát cache/tải máy nên không kết luận prompt làm model nhanh hơn.

Đối chiếu do Codex thực hiện trên ca tổng hợp, chưa thay người viết/PO. Không thêm vòng sửa, judge, router model hoặc ép thêm tiêu chí để làm kết quả đạt.

## Trạng thái sau chốt

- Chốt phạm vi triển khai và hồ sơ kỹ thuật Gói 2 để mở **Draft PR vào dev**. Các bảo vệ source/revision/preview/lưu được kiểm tra riêng; không đồng nhất với chất lượng sáng tác.
- Lỗi còn mở: append lặp/quay ngược nguồn; các đợt v1 từng có thiếu diễn tiến hoặc đi ngược ý đồ. V2 chỉ kiểm chứng ba append bằng Gemma 2, chưa xác nhận lại list/develop hoặc model Qwen mặc định. Không tự đổi model hay gọi toàn bộ Gói 2 đã đạt.
- Phiên người dùng thật chờ full workflow theo quyết định của tác giả, không phải điều kiện bắt đầu công việc Gói 3. Các tiêu chí chất lượng và nghiệm thu vẫn giữ nguyên.
