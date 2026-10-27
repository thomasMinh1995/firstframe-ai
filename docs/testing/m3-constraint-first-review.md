# M3 Gói 3 — Đối chiếu hành động/ràng buộc trước góp ý

Ngày 27/10/2026. Nhánh `feat/screenplay-evidence-feedback`. Chỉ triển khai bước 3 bằng thay đổi prompt và kiểm chứng provider giả. Không gọi model thật, đổi model/cấu hình, commit hoặc tạo PR; giữ nguyên plan/roadmap/prototype và bằng chứng cũ.

## Thay đổi nhỏ

Prompt `screenplay-review-v3-constraint-first` yêu cầu thứ tự đọc:

1. Đối chiếu hành động/lời thoại thực xảy ra trong cảnh đích với ràng buộc và lựa chọn M2, gồm trạng thái/khả năng đồ vật và kết quả hành động. Câu khẳng định trong draft không tự cho phép bỏ ràng buộc tác giả.
2. Nêu mâu thuẫn rõ trước góp ý tùy chọn, dẫn cả khối cảnh đích và quyết định nguồn. Gợi ý nếu có phải xử lý hành động/kết quả mâu thuẫn; thêm thoại giải thích không sửa được hành động sai vẫn còn đó. Không có phương án nhỏ có căn cứ thì để suggestion rỗng; quan hệ chưa rõ dùng uncertain.
3. Sau đối chiếu mới cân nhắc craft có ích. Không mặc định thêm động tác/thoại, chê thoại không tồn tại hoặc coi khoảng lặng là lỗi. Cho notes rỗng; không thêm checklist, điểm số hay phán quyết tuân thủ vào output.

Hướng dẫn mang tính tổng quát, không hardcode đèn pin, Lan/Bình hoặc ca mẫu vào runtime. Chỉ sửa nội dung prompt và version; schema, adapter mã ngắn, kiểm ID/quote, nguồn bất biến, cơ chế HITL và API/UI giữ nguyên. Không thêm lượt gọi/judge, luật dò từ khóa hoặc bộ xác nhận lập luận tự động.

## Kiểm chứng

Lệnh từ `backend`:

```sh
.venv/bin/python -m pytest -q tests/test_screenplay_review.py tests/test_screenplay_review_priority.py tests/test_screenplay_writing.py tests/test_screenplays.py
```

**67 passed**, 4,40 giây; cảnh báo Starlette/httpx có sẵn còn nguyên. Đây là bộ backend tập trung, không phải lượt chạy lại toàn bộ repo/build/browser.

- Sáu đầu vào cũ tiếp tục qua API bằng provider giả, không đổi project/snapshot/request/expected. Guard ngữ cảnh vẫn cho phép gửi đủ nguồn với prompt mới; mã ngắn, action/dialogue/cảnh đích và ID gốc lưu lại vẫn đúng.
- Bốn ca fake tập trung đèn pin dùng output định trước: bản tuân thủ trả notes rỗng; bản vi phạm trả nhận xét mâu thuẫn với hai nguồn và gợi ý bỏ hành động đèn sáng; cùng nhận xét nhưng suggestion rỗng vẫn hợp lệ; góp ý craft sai trọng tâm về thoại vẫn qua kiểm tham chiếu nếu quote/ID đúng.
- Provider giả kiểm hướng dẫn thứ tự ưu tiên thực được truyền vào request, đúng khối action và ràng buộc đèn hỏng. API kiểm nguồn, lưu version v3, giữ nguyên screenplay/M2 và mở lại kết quả. Test không dùng thông tin nhãn để bổ sung vào request runtime.
- Mở lại cả sáu record v1 lỗi và sáu record v2 ready không gọi provider, không đổi version/trạng thái/bằng chứng. Hồi quy revision, idempotency, bỏ lượt/kết quả muộn, buffer/tự sửa/lưu ở lớp API, timeout, quote/mã sai, ngữ cảnh/quota và đường viết tay/viết thử tiếp tục qua.
- `git diff --check` qua; kiểm hash plan/roadmap/prototype, `.env` và toàn bộ hai đợt bằng chứng Qwen cũ không thay đổi. Code/prompt đúng lúc các đợt v1/v2 đã nằm trong thư mục source của từng đợt, khớp manifest gốc; không gán output cũ cho v3.

## Giới hạn và trạng thái

Fake trả output đã định sẵn để kiểm đường request/hợp đồng/dữ liệu; không chứng minh model đã làm phép đối chiếu hoặc nhận xét đúng. Test craft sai trọng tâm cố ý ghi rõ rằng guard chỉ xác nhận tham chiếu, không phát hiện được bỏ sót hay lập luận sai. Không tự nâng guard thành chứng nhận chất lượng, không chặn quyền tự viết/lưu của tác giả.

Lỗi bỏ sót đèn pin của Qwen vẫn chưa được chứng minh đã khắc phục. Chưa chạy lại model; chưa gọi Gói 3 đạt chất lượng AI. Nếu được duyệt kiểm chứng tiếp, cần đóng băng v3 riêng và đối chiếu cùng sáu ca với cả v1/v2, tách lỗi tham chiếu khỏi nhận xét; không chạy bù chọn lọc hoặc sửa nhãn theo output.

Tài liệu nền: [so sánh Qwen v2 với baseline](m3-short-sources-qwen7b-comparison.md), [adapter mã ngắn](m3-review-source-aliases.md).
