# Review cuối PR #86 — Thoại và diễn tiến nhiều cảnh

Ngày 30/10/2026. Tiếp nối [baseline v24 chỉ đạt 2/5 nội dung](../qa01-new-briefs-qwen7b-2026-10-30/README.md). Giữ nguyên năm brief, tiêu chí, snapshot và mọi kết quả cũ. Đạt gate nội dung của PR này; QA-01 toàn sản phẩm vẫn còn thiết bị/người đọc độc lập và giới hạn sáng tác tự do.

## Kết quả

| Kiểm chứng | Kết quả |
| --- | --- |
| Năm brief mới, lượt đầu | **5/5**, đủ **19/19 cảnh**, một call mỗi cảnh — [report](pilot-v25/report.json) |
| Năm brief mới, lượt xác nhận | **5/5**, đủ **19/19 cảnh**, một call mỗi cảnh — [report](final-v25/report.json) |
| Tám ca hồi quy cũ | **8/8** kỹ thuật và content gate — [report cuối](previous-eight-final-v25/report.json) |
| Planner thật → ba cảnh → review → snapshot → PDF | **Đạt kỹ thuật và nội dung**, 16 calls, khoảng 143 giây — [report](full-workflow-v25/report.json), [đọc nội dung](full-workflow-v25/content-review.json) |
| Backend local | **831 passed, 1 skipped**; CI xác nhận trên head PR |

[Acceptance](acceptance.json) ghi từng ca ở cả hai lượt: đọc ngôn ngữ, người nói/xưng hô, trạng thái đạo cụ, kết mở và đối chiếu action trực tiếp với fixture. Đây là review bởi agent, không phải người đọc độc lập hay chứng nhận chất lượng văn chương.

- **Mẹ–con / vé tàu:** con chỉ nhận/cất vé sau khi mẹ đặt; không nói đã cất sớm, không tự chốt lên tàu.
- **Chị–em / radio:** đúng chị/em; Nam ngồi một lần, radio còn hỏng; không kể action trong thoại.
- **Mara–Owen / ô / English:** ô chỉ đổi chủ một lần; cửa còn đóng, quyết định chưa chốt; heading/action/thoại English.
- **Bố–Minh / hộp kín:** bố/con đúng vai; không ra lệnh ngồi lại, không mở hộp hay tự tha thứ; không lặp nguyên câu giữa các cảnh.
- **An–Bình / sáu cảnh im lặng:** đủ sáu action, An tưới một lần, bình rỗng sau tưới và cây chưa xanh ngay; không thêm thoại.

Toàn luồng thật nay có đủ đặt vé → nhận/cất vé → đứng ở cửa chưa quyết định; mỗi cảnh đúng hai lượt mẹ/con. Bản PDF khớp selection và xuất khi AI đã tắt. Outline AI vẫn chứa nhịp lặp/kết cục khác, được giữ nguyên như nguồn AI chưa xác nhận; không sửa snapshot để che lỗi cũ.

## Thay đổi giao

1. **Một nguồn viết nhất quán.** Nếu outline mới hoàn toàn từ AI, chưa có lựa chọn tác giả, brief tác giả đủ action cụ thể và các cảnh trước khớp nhịp đã dựng: dùng chuỗi action tác giả cho toàn bộ lần viết. Eligibility, future context và heading đều theo chuỗi đó. Quote/cast thiếu của AI ở một cảnh không còn làm writer đổi profile rồi bỏ nhịp. Khôi phục hai vai từ cast toàn outline chỉ trong trường hợp này và chỉ khi yêu cầu mỗi cảnh đã nêu đúng hai người. Outline, provenance và ID nguồn không bị sửa.
2. **Phản hồi thoại có cấu trúc.** Với yêu cầu rõ hai lượt mỗi cảnh, Qwen chọn ý thoại trong danh sách phản hồi không tạo sự kiện; ứng dụng dựng câu bằng ngôi xưng/cách gọi đã xác định. Lượt đầu mời nói/cho thời gian; lượt sau phản hồi. Câu đã dùng bởi cùng vai được loại khỏi schema của cảnh sau, kể cả label khác hoa/thường. Không chấp nhận text tự do rồi âm thầm sửa thành lời khác.
3. **Giữ khả năng biên tập.** Text kết quả vẫn là đề xuất AI, sửa được trong editor. Quote tác giả, scope khối, yêu cầu sửa riêng và xưng hô chưa đủ rõ vẫn dùng writer đầy đủ. Dạng xưng hô nhiều từ/không hỗ trợ không bị cắt ngắn thành một đại từ. Hết lựa chọn phản hồi sẽ dừng trước model để review, không retry.
4. **Dịch giữ phủ định.** Chỉ khi cần dịch action sang English, prompt yêu cầu giữ phủ định rõ, không thay bằng do dự/ý định. Không đổi gate cũ: lượt hồi quy [trước sửa](previous-eight-v25/report.json) có 7/8 vì bản dịch chỉ nói “hesitating to pick it up or open it”; giữ cả kết quả đó. Lượt cuối trở lại 8/8 với “not picking it up or opening it”.

Đây là đánh đổi có chủ đích cho bản nháp local 7B: action giữ sát nguồn, thoại phản hồi bảo thủ hơn. **Không coi 5/5 là bằng chứng Qwen đã viết thoại tự do đáng tin cậy** hoặc hiểu mọi quan hệ/tình huống ngoài bộ ca. Không chèn chủ đề/đạo cụ của năm fixture vào logic ứng dụng, không thay brief/tiêu chí, temperature, model, số cảnh hoặc thêm model call để sửa một response.

## Nguồn và phục hồi

[Source verification](source-verification.json) đối chiếu **49 response**: 38 từ hai lượt năm brief, 8 hồi quy cuối và 3 lượt viết trong luồng planner. Instructions/input/schema khớp mã giao; replay dựng cùng nội dung, chỉ bỏ UUID block mới. Nguồn proposal không bị sửa. Replay không phải model call bổ sung.

Profile ghi HEAD trước commit vì test trong worktree có thay đổi; SHA-256 ghi mã thực đã kiểm. [Model profile](model-profile.json) giữ digest Qwen thật; temperature 0.3, context 16384, output cap 4096. Không migration, nới count, sửa buffer/lịch sử, bật card mặc định hoặc tự nhận author confirmation. Các test còn kiểm tra source đổi sau preview, checkpoint, received-frame reuse và timeout không gửi lại.

Runner lưu proposal nén và delta kết quả (`scene/status/model/parameters/prompt_version`), tránh lặp nguyên snapshot trong mỗi result; dữ liệu lượt đầu đã được đối chiếu tái dựng chính xác trước khi thu gọn. Raw response vẫn giữ intent do Qwen chọn; text trong result là bản ứng dụng dựng rõ ràng theo `bounded-reactions-v1`.

## Tái lập

```sh
# Từ root repo; output phải là thư mục mới, Ollama đã có qwen2.5:7b.
backend/.venv/bin/python backend/scripts/check_multiscene_writing.py \
  --cases docs/evaluations/qa01-new-briefs-qwen7b-2026-10-30/cases.json \
  --output /tmp/ff-five-briefs-final
backend/.venv/bin/python backend/scripts/check_scene_writing.py \
  --all-cases --content-gate --output /tmp/ff-eight-regression-final
backend/.venv/bin/python backend/scripts/check_draft_release.py \
  --max-calls 24 \
  --brief-source docs/evaluations/qa01-new-briefs-qwen7b-2026-10-30/full-workflow-brief.json \
  --output /tmp/ff-three-scenes-final
```
