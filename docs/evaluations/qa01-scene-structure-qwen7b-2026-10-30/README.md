# QA-01 — cấu trúc viết cảnh và giới hạn cảnh tác giả

Ngày 2026-10-30, nhánh `fix/qwen-scene-structure-limits`, từ dev `d5d12fe`.
**Đạt các kiểm tra cấu trúc/count dưới đây; chưa đóng QA-01 hoặc phê duyệt phát hành.**

## Thay đổi được kiểm chứng

- `screenplay-scene-v2`: prompt nêu rõ root `scene`; scene không có ID do AI cấp. Schema tách action (`speaker` rỗng) và dialogue (bắt buộc speaker/text). Backend tiếp tục kiểm tra khoảng trắng, kích thước, đúng đích và phạm vi; không sửa/chấp nhận âm thầm JSON sai.
- `scene-suggestions-v3`: bỏ yêu cầu cứng 2–6. Bounds lấy từ ý tưởng, constraints và câu trả lời thật của tác giả; không lấy từ story plan, câu hỏi chưa được trả lời hay chi tiết AI tự sinh. Schema gửi model và validation backend cùng giữ bounds. Luồng tự động vẫn hỗ trợ tối đa 6 cảnh.
- Hỗ trợ số viết bằng chữ 1–6 hoặc chữ số, giới hạn tối đa/tối thiểu, số chính xác và khoảng, bằng các cách viết Việt/Anh trong `test_scene_count.py`. Không suy số cảnh từ số nhân vật/địa điểm hoặc “hai cảnh cuối”. Đây là bộ đọc quy tắc cho cách diễn đạt rõ ràng, chưa phải bộ hiểu mọi câu ngôn ngữ tự nhiên.
- Bounds mâu thuẫn hoặc số chính xác vượt mức hỗ trợ dừng trước call tạo dàn cảnh. Kết quả dư/thiếu cảnh bị từ chối, không cắt danh sách. AI append cũng không được thêm vượt giới hạn; develop vẫn sửa được cảnh hiện có. Không hạn chế việc tác giả tự viết/lưu.
- Giữ checkpoint và quy tắc không gửi lại call chưa rõ kết quả; không migration dữ liệu và không đổi cờ UI opt-in.

## Model và cách chạy

Ollama `qwen2.5:7b`, context 16384, temperature 0.3, review 0, output viết/review tối đa 4096 token. Digest và hash nguồn ở [source-profile.json](source-profile.json).
Các profile ghi HEAD nền do chạy trước commit; request thực tế là nguồn xác nhận prompt/schema. Lượt brief tối đa hai cảnh chạy trước khi thêm đoạn giải thích `scene_count` vào prompt dàn cảnh; bounds/schema viết cảnh giữ nguyên. Lượt một cảnh dùng đoạn giải thích mới.
`source-profile.json` giữ hash của đợt đầu trên commit `9529b2b`, trước các sửa phát hiện khi review cuối bên dưới; không sửa lại bằng chứng lịch sử thành kết quả của code mới.

```sh
# Từ root repo, với backend venv và Ollama đã sẵn sàng:
backend/.venv/bin/python backend/scripts/check_scene_writing.py --output /tmp/ff-scenes-new
backend/.venv/bin/python backend/scripts/check_draft_release.py --output /tmp/ff-draft-new \
  --brief-source docs/evaluations/qa01-scene-structure-qwen7b-2026-10-30/one-scene-brief.json
```

Runner từ chối ghi đè output cũ, không retry khi model lỗi; lưu request/schema, JSON thô, validation cause, snapshot và timing. Toàn bộ dữ liệu ở đây là brief synthetic, SQLite thử nghiệm riêng.

## Kết quả

| Ca | Cấu trúc/count | Call model | Thời gian model |
| --- | --- | --- | --- |
| [Quiet open ending](saved-scenes/quiet-open-ending/report.json) | Đạt, giữ target/source ID | 1 | 15.874s |
| [Gentle comedy](saved-scenes/gentle-comedy/report.json) | Đạt, action/dialogue tách đúng schema | 1 | 21.619s |
| [Limited resources](saved-scenes/limited-resources/report.json) | Đạt | 1 | 8.123s |
| [Snapshot lượt trước lỗi JSON](saved-scenes/draft-workflow-qwen7b-2026-10-30/report.json) | Đạt schema; lỗi nội dung còn lại | 1 | 14.309s |
| [Snapshot brief cũ 30 giây](saved-scenes/draft-workflow-qwen7b-saved-brief-2026-10-30/report.json) | Đạt schema; lỗi diễn tiến còn lại | 1 | 24.420s |
| [Toàn luồng, brief cũ tối đa 2 cảnh](saved-two-scenes/report.json) | 1 cảnh trong bounds 1–2; ready, review, chọn đúng bản, PDF khi AI tắt | 9 | 93.793s |
| [Toàn luồng, biến thể tối đa 1 cảnh](saved-one-scene/report.json) | Đúng 1 cảnh; ready, review, chọn đúng bản, PDF khi AI tắt | 9 | 138.518s |

Năm replay gọi mỗi snapshot đúng một lần, không sửa nguồn. Ba ca M3 dùng proposal trước khi nhận phương án; hai snapshot DR dựng lại checkpoint trước cảnh đầu bằng cách làm rỗng blocks, giữ nguyên outline và author context. Không resume lượt cũ chưa rõ kết quả.

[Baseline trước sửa](baseline/result.json) cũng trả schema hợp lệ ở một lần replay (17.441s), nhưng nhét lời thoại trong action. **Không tái hiện được lỗi JSON của lần chạy lịch sử**: lần đó không lưu raw output. Vì vậy kết quả mới là kiểm chứng hợp đồng chặt hơn trên bộ ca cố định, không chứng minh đã xác định mọi nguyên nhân lỗi lịch sử.

[harness-error-before-model](harness-error-before-model/) giữ dấu vết một lỗi của bộ ghi evidence trước khi gửi model: thử parse input reasoning dạng text như JSON. Đã sửa runner để lưu nguyên `input_text`; lượt đó không tính là model failure và không có model call thực.

Hồi quy local: toàn backend **692 passed, 1 skipped** trước hai bổ sung cuối cho append và cách nói “hai cảnh cuối”; **42 passed** trên count/scene suggestions sau các bổ sung đó. Ma trận API có brief yêu cầu đúng 1/2/6 cảnh, cả cần/không cần làm rõ; kiểm tra schema min/max, checkpoint, review, chọn bản và PDF. Ca AI trả dư kiểm tra giữ plan, không viết tiếp và không gọi lặp. Kiểm tra block revision, scope, ID và lưu dữ liệu cũ nằm trong suite backend. CI chạy lại toàn bộ backend/frontend trên PR.

## Review cuối PR #84

Đã sửa các lỗi có ca hồi quy đỏ trước khi sửa:

- Regex câu hỏi trước đây hiểu câu trả lời số cho “Bao nhiêu nhân vật trong cảnh?” là số cảnh. Nay chỉ đọc câu trả lời số khi câu hỏi hỏi trực tiếp số lượng cảnh, giữ đúng loại tối đa/tối thiểu. Có hồi quy Việt/Anh và ca API tự động với câu trả lời `2` nhân vật vẫn viết được một cảnh.
- Giới hạn trong `author_request` trước đây chỉ gửi model như text. Nay được giao với bounds của nguồn để dựng schema và kiểm tra backend; yêu cầu mới được thu hẹp, không được nới giới hạn nguồn. Không thay source context lưu trong dự án. Prompt cập nhật khiến lượt chạy cũ khác cấu hình không được tiếp tục bằng prompt mới.
- Chuỗi số quá dài trong ý tưởng (4400 chữ số, vẫn trong giới hạn 5000 ký tự) trước đây làm `int()` ném lỗi ngoài xử lý validation. Nay trả `SceneCountConflict` để API trả 422 thay vì 500.
- Bộ lọc “hai cảnh cuối” trước đây bỏ cả giới hạn rõ ràng kèm mô tả thời gian như “Chỉ một cảnh sau cơn mưa” hoặc “Tối đa một cảnh trước khi trời tối”. Nay ưu tiên dấu hiệu giới hạn rõ ràng; vẫn không suy count từ tham chiếu cảnh đầu/cuối không có giới hạn.

[Lượt Qwen kiểm tra cuối](final-review/report.json): một call 16.346s, biến thể từ brief hai cảnh đã lưu, thêm trả lời `2` nhân vật và yêu cầu trực tiếp tối đa một cảnh. Kết quả đúng một cảnh, schema maxItems=1, nguồn giữ nguyên. Request/raw response/profile lưu cạnh report; không retry, không resume run cũ. Đây là kiểm chứng count, không bổ sung nghiệm thu ngữ nghĩa.

## Gate còn mở

[Đọc nội dung trực tiếp](content-review.json) phát hiện: chữ Trung Quốc xen vào action tiếng Việt; xưng hô cha–con `Tôi/bạn`; lặp hành động ngồi xuống/đưa áo; và diễn tiến nhân vật cần tác giả xem lại. Không che các lỗi bằng retry, lọc chữ hoặc cắt nội dung. `technical_pass` chỉ nói về cấu trúc và toàn luồng kỹ thuật, không phải nghiệm thu ngữ nghĩa. PDF chỉ được kiểm tra xuất đúng snapshot, không bổ sung nghiệm thu thị giác/thiết bị trong đợt này.

QA-01 tiếp tục mở cho chất lượng nội dung/model, người đọc độc lập, thiết bị thật và khả năng tiếp cận. Chưa bật card làm mặc định.
