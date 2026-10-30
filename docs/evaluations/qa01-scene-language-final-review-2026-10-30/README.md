# PR #85 — Kiểm thử cuối ngôn ngữ, xưng hô và diễn tiến

Ngày 2026-10-30. Tiếp nối [bản v10 còn lỗi nội dung](../qa01-scene-language-qwen7b-2026-10-30/README.md), giữ nguyên mọi snapshot lịch sử. Phạm vi nghiệm thu đợt này: tám ca synthetic đã lưu, đặc biệt thoại cha–con và diễn tiến; không đóng toàn bộ QA-01.

## Kết quả cuối

**Cả hai lượt cuối đạt 8/8 kỹ thuật và nội dung**, bằng Ollama `qwen2.5:7b`, temperature 0.3, context 16384, một call mỗi ca, không retry. [Lượt 1](final-v19-pass-1/report.json), [lượt 2](final-v19-pass-2/report.json). Mỗi thư mục ca giữ proposal, request/schema, raw response, bản dựng và report.

| Ca | Đọc kết quả thực ở cả hai lượt |
| --- | --- |
| Quiet open ending | Cha đặt thư rồi lùi; con chỉ đặt tay cạnh thư, chưa nhận/mở; kết mở |
| Gentle comedy | Nam che khóa kẹt; Hà chờ; Nam đưa vạt áo một lần; không tự sửa xong khóa |
| Limited resources | Bình đặt đèn pin xuống; Lan kéo rèm, dùng ánh đèn đường; đèn pin không tự sáng |
| Linh nhận thư | Bố trao trước, Linh nhận sau; thư chưa mở |
| Căn bếp 30 giây | Con gái đặt chìa khóa; không đổi thành cha; không lấy nhịp ngồi/uống trà của cảnh sau |
| Thoại cha–con | Đúng hai câu, thứ tự Cha → Con gái; xưng Cha/Con; không tôi/bạn, không kể hành động trong thoại, không tự tha thứ |
| English | Heading `SCENE 2`; hai action tiếng Anh giữ nguyên ý thư kín, chưa nhận/mở |
| Cảnh tiếp theo | Linh đang giữ thư, không trao lại, không mở lại |

Thoại thật ở cả hai lượt: “Cha chưa biết phải nói thế nào.” / “Con chưa biết phải nói thế nào.” Đây là gợi ý ngắn có cấu trúc, còn cần tác giả biên tập về sắc thái. Gate tự động kiểm tra các tiêu chí cố định; việc đọc nghĩa bản dịch và thoại ở bảng trên bổ sung cho gate, không phải đánh giá ngữ nghĩa tổng quát.

[Đối chiếu mã cuối](source-verification.json) xác nhận input, instructions và schema của cả 16 call khớp mã giao; replay dựng cùng nội dung, chỉ bỏ qua UUID block mới. Profile ghi HEAD trước commit khi test; SHA-256 trong đối chiếu bao gồm cả file mới chưa được git theo dõi.

Backend local: **783 passed, 1 skipped**. Bao gồm nguồn tác giả/legacy, schema sai bị từ chối, API adoption/idempotency, không sửa cảnh bên cạnh, nguồn đổi sau preview, checkpoint 1/2/6 cảnh, frame đã nhận không gửi lại và timeout không retry. CI kiểm tra backend trên Python 3.13 cùng frontend typecheck/test/build.

## Toàn luồng một cảnh

[Lượt toàn luồng v19](full-draft-v19-one-scene/report.json) đạt brief → plan → outline → viết → review → chọn bản → PDF, tám model calls tổng cộng, một cảnh đúng giới hạn tác giả. [Đọc nội dung](full-draft-v19-one-scene/content-review.json): đủ ba nhịp đặt chìa khóa → cha đặt thư và lùi lại → con ngồi uống trà một lần; thư chưa mở. Action khớp toàn bộ brief cụ thể của tác giả theo đúng thứ tự. Bản được chọn khớp kịch bản và tải PDF thành công khi AI tắt.

[Model profile](model-profile.json) ghi digest thực; schema/input/raw output nằm cùng từng ca.

## Cách sửa và giới hạn

- Với Qwen 7B và cảnh nguồn có hành động cụ thể, không có chỉnh sửa dàn dựng/khối/thoại có sẵn cần giữ: dùng profile `source-preserving-v1`. Action tiếng Việt lấy nguyên văn nhịp nguồn, giữ thứ tự; không nhờ model phóng tác lại action rồi âm thầm thay từ sai. Đây là đánh đổi có chủ đích: bản nháp bảo thủ hơn, chưa chứng minh chất lượng sáng tác tự do của Qwen.
- Yêu cầu rõ mỗi vai gia đình một câu trong cảnh còn mở: schema cố định vai, vị trí và ngôi xưng; model chọn một trong ba ý thoại chưa quyết định/cần thời gian/có thể chờ; ứng dụng dựng câu theo ngôn ngữ. Không tự gán lời tác giả. Yêu cầu xưng hô riêng, trích dẫn, hành động mới, dàn dựng, sửa khối và nội dung tác giả đã viết vẫn dùng writer đầy đủ.
- Tiếng Anh: model dịch từng nhịp; schema cố định heading tiếng Anh. Bộ chặn hệ chữ mới vẫn áp dụng, không xóa tên/trích dẫn có trong nguồn. Gate tiếng Anh là smoke check cho ca này, không chứng minh mọi bản dịch.
- Dàn cảnh AI mới, hoàn toàn chưa được tác giả chọn, có thể dùng các câu hành động cụ thể trong brief tác giả theo đúng thứ tự và số cảnh hiện có. Việc này giữ đủ nhịp nếu AI chia cảnh sai người hoặc bỏ sót. Không sửa snapshot outline; lưu `outline_reconciled` trong tham số proposal. Cảnh đã viết phải khớp phần nguồn đã dựng để tiếp tục; nguồn tác giả đã xác nhận/chỉnh sửa hoặc không đủ căn cứ sẽ không bị tự chia lại. Mâu thuẫn không giải quyết an toàn trả 422 trước model, giữ dữ liệu để review.
- Không đổi temperature toàn cục, không thêm model call, migration hay nới giới hạn số cảnh. Giữ bản gốc, lịch sử và scope. Cấu hình prompt mới làm lượt chạy cũ cần tạo lại theo cơ chế sẵn có, không phát lại call không rõ kết quả.

QA-01 còn mở cho thiết bị thật, người đọc độc lập và chất lượng/ngữ nghĩa ngoài tám ca. `release_approved:false` trong runner biểu thị chưa nghiệm thu phát hành toàn sản phẩm, không phủ nhận tám tiêu chí đã đạt của PR này.

## Bằng chứng thử nghiệm

[Archive](experiments.json.gz) giữ 14 lượt trước bản cuối, toàn bộ 354 file gồm raw output và lần lỗi; [index](experiments-index.json) giữ report. Mỗi entry có encoding, text và SHA-256; đã giải nén đối chiếu byte trước khi gộp. Có cả lần toàn luồng đúng kỹ thuật nhưng thiếu thư/trà: không coi đó là đạt nội dung. Các cách tách frame, regex ngôi xưng hoặc cloze tự do vẫn lỗi nên không giao.

```sh
# Từ root repo; Ollama đã có qwen2.5:7b, output phải là thư mục mới:
backend/.venv/bin/python backend/scripts/check_scene_writing.py \
  --all-cases --content-gate --output /tmp/ff-eight-cases-new
```
