# QA-01 — ngôn ngữ, xưng hô và diễn tiến khi viết cảnh

Ngày 2026-10-30, nhánh `fix/qwen-scene-language-continuity`, từ dev `08605df`.
**Kết luận: có phần hardening dùng được, nhưng gate ngữ nghĩa chưa đạt; PR giữ draft, QA-01 còn mở.**

## Phần triển khai

- Chặn phản hồi AI đưa thêm chữ thuộc hệ chữ ngoài Latin chưa có trong input. Áp dụng cho heading/text/speaker của cảnh mới và các replacement được chọn trong sửa khối. Không sửa/xóa câu chữ để làm kết quả thành hợp lệ; phản hồi sai bị từ chối, giữ snapshot, buffer và checkpoint. Tên riêng/trích dẫn đã có trong input, tiếng Việt có dấu, tiếng Anh và emoji được giữ.
- Đây là bộ chặn **script drift**, không phải bộ phân loại toàn bộ ngôn ngữ: tiếng Việt xen tiếng Anh cùng dùng Latin vẫn có thể lọt; các chữ ngoài Latin đã có trong nguồn cũng có thể bị model dùng lại sai. Không dùng nó làm bằng chứng cảnh đúng nghĩa.
- Request giữ nguyên toàn bộ story plan, author context, dàn cảnh và screenplay cũ; thêm vị trí cảnh và nhãn nguồn theo từng field. `author_choice` chỉ xuất hiện khi provenance thật cho biết tác giả nhập/xác nhận; AI và legacy không được nâng thành ý đồ tác giả. Đặt author_intent cuối input để đối chiếu. Test frozen xác nhận không cắt nguồn hoặc lấy context mới ngoài snapshot.
- Prompt `screenplay-scene-v10` làm rõ actor/action, cảnh trước/sau, nhịp cuối, xưng hô cha–con/chị–em và ngôn ngữ đã chọn. Giữ nguyên schema output, một call cho mỗi lượt viết, temperature cấu hình, timeout, output/context budget, giới hạn số cảnh, ID và scope. Không có bước tự retry/repair hoặc gọi thêm model trong bản giao.
- Prompt được giữ ngắn để ma trận sáu cảnh còn chạy trong context hiện có. Thử nghiệm prompt dài, trích nguồn và chuẩn bị riêng không được đưa vào runtime.

## Kiểm thử phần mềm

Backend local: **721 passed, 1 skipped**. Có hồi quy cho response Qwen cũ lẫn chữ Trung Quốc; heading/text/speaker sai; tên/trích dẫn nguồn; sửa khối giữ nguyên chữ tác giả ngoài scope; nguồn AI/author/legacy; và lỗi ở luồng tự động giữ checkpoint, không gọi lại model khi tiếp tục cùng kết quả đã nhận. Ma trận 1/2/6 cảnh, review, nhận bản và PDF tiếp tục qua.

Không sửa frontend, không migration dữ liệu hoặc bật UI card mặc định. CI trên PR kiểm tra cả backend/frontend. Chưa chạy thêm luồng Qwen→PDF trong đợt này vì gate nội dung viết cảnh chưa đạt; kiểm thử PDF ở đây là API hồi quy.

## Ca model cuối

Ollama `qwen2.5:7b`, temperature 0.3, context 16384, output reserve 4096; digest/hash nguồn ở [source-profile.json](source-profile.json). Chạy trước commit trên working tree; request và raw response ở từng thư mục là bằng chứng chính xác. Mỗi ca cuối gọi một lần, không retry và không resume run lịch sử.

| Ca | Schema/guard | Đánh giá nội dung trực tiếp |
| --- | --- | --- |
| [Quiet open ending](final-v10/quiet-open-ending/report.json) | Đạt | Thư vẫn kín, tay đặt cạnh thư, không thêm cha rời đi |
| [Gentle comedy](final-v10/gentle-comedy/report.json) | Đạt | Nam xưng em/gọi chị; đưa vạt áo một lần, chưa sửa xong khóa |
| [Limited resources](final-v10/limited-resources/report.json) | Đạt | Đèn pin không tự sáng; giữ rèm, ánh đèn đường và tờ giấy |
| [Linh nhận thư](final-v10/draft-workflow-qwen7b-2026-10-30/report.json) | Đạt | **Chưa đạt:** Linh đã cầm thư trước khi bố trao thư |
| [Brief căn bếp 30 giây](final-v10/draft-workflow-qwen7b-saved-brief-2026-10-30/report.json) | Đạt | **Chưa đạt:** cha đặt chìa khóa thay con; con ngồi hai lần; lấy nhịp uống trà của cảnh sau |
| [Yêu cầu thoại cha–con](variants-v10/parent-dialogue/report.json) | Đạt | **Chưa đạt:** cả hai câu thuộc con gái; con đổi từ con sang tôi |
| [Chọn đầu ra tiếng Anh](variants-v10/english/report.json) | Đạt | **Chưa đạt toàn bộ ngôn ngữ:** action tiếng Anh nhưng heading vẫn “Khoảnh khắc” |
| [Cảnh tiếp theo](variants-v10/later-scene/report.json) | Đạt | Thư vẫn trong tay Linh, không trao/mở lại; mô tả ánh sáng còn cần biên tập |

**8/8 đạt kỹ thuật không đồng nghĩa đạt ngữ nghĩa.** [content-review.json](content-review.json) ghi từng chiều language/address/progression và lỗi. Không tuyên bố đã sửa hết xưng hô hoặc diễn tiến. Ca có sai diễn tiến/xưng hô vẫn phải được tác giả review và sửa; không được tự nhận làm bản đúng.

Ba biến thể mới khai báo ở profile: thoại được yêu cầu rõ; response language chọn `en`; hoặc cảnh thứ hai với một đoạn đầu synthetic đã lưu rằng thư được trao. Không sửa các snapshot lịch sử. Bản sửa vẫn chưa đủ điều kiện bỏ review của tác giả hay đóng QA-01.

## Thử nghiệm không chọn

[experiments-index.json](experiments-index.json) liệt kê bảy lượt, 39 model calls thực. [experiments.json.gz](experiments.json.gz) giữ **toàn bộ** request/schema/raw output/report/profile/proposal của các lượt đó, gồm nguyên văn từng file; archive đã được đọc lại và đối chiếu trước khi gộp. Không xóa kết quả xấu để chỉ giữ lần đạt.

- v3/v4: tăng ưu tiên nguồn và chỉ dẫn xưng hô; vẫn sai người làm hành động, lặp hoặc thiếu nhịp.
- v5: prompt tiếng Việt + temperature 0 chưa khắc phục diễn tiến; không giữ thay đổi temperature.
- v6: trích nguồn trong schema bị model trích nhầm/phóng tác; một ca chưa gửi được vì context, hồi quy sáu cảnh lỗi. Không giữ schema mới.
- v7: prompt tiếng Việt ngắn vẫn sai xưng hô/diễn tiến; không giữ prompt riêng.
- v8: chuẩn bị nhịp riêng hai calls vẫn kéo sự kiện cũ vào cảnh và hoàn thành việc quá sớm. Không giao bước gọi thêm này.
- v9: diễn tiến/xưng hô vẫn lỗi và prompt dài làm hỏng hồi quy sáu cảnh. v10 rút gọn để phục hồi hồi quy; **không coi đó là chữa hết ngữ nghĩa**.

Đọc archive: `gzip.open(path, 'rt')` rồi `json.load`; từng key phiên bản chứa mapping tên file → `{encoding, text}`. Chuỗi raw output bên trong text giữ nguyên. Các report `technical_pass` lịch sử chỉ phản ánh schema/validation tại thời điểm thử.

## Tái lập

```sh
# Từ root repo, với backend venv và Ollama sẵn sàng:
backend/.venv/bin/python backend/scripts/check_scene_writing.py --output /tmp/ff-scene-check-new
backend/.venv/bin/python backend/scripts/check_scene_writing.py --output /tmp/ff-scene-variants-new --variants-only
```

Output phải là thư mục mới. Runner ghi từng request/response có số thứ tự và số call thật. Thiết bị thật, IME, screen reader và người đọc độc lập chưa được kiểm chứng trong đợt này.

## Tiếp nối review cuối

Các lỗi và trạng thái draft bên trên là kết quả v10 được giữ nguyên. Xem [báo cáo review cuối PR #85](../qa01-scene-language-final-review-2026-10-30/README.md) cho bản v19, hai lượt đủ tám ca và giới hạn của profile giữ nguồn.
