# M3 Gói 3 — Sửa nhỏ critic để giữ lựa chọn tác giả

Ngày 27/10/2026. Nhánh `feat/screenplay-evidence-feedback`. Chỉ sửa hướng dẫn critic và version, kiểm chứng bằng provider giả. Không chạy model thật, đổi cấu hình/provider, commit hoặc tạo PR. Giữ nguyên plan/roadmap/prototype và mọi bằng chứng model trước.

## Thay đổi

Prompt `screenplay-review-v4-author-control` thay hai phần hướng dẫn v3, không thêm pipeline hoặc schema:

- Chỉ báo intent_mismatch nếu hành động/kết quả trực tiếp trái lựa chọn tác giả trong ngữ cảnh. Thiếu biểu cảm/thoại/quyết định ngay không tự là vi phạm, trừ khi tác giả yêu cầu rõ chi tiết ấy phải có trong cảnh đích. Phân biệt dùng yếu tố đã cho phép với thêm yếu tố mới bị cấm.
- Không dùng uncertain/câu hỏi như cách thay thế một cáo buộc thiếu căn cứ. Craft cần vấn đề/tác động cụ thể; không có điều hữu ích thì trả notes rỗng.
- Bỏ câu mệnh lệnh chung “Suggest a small action…”. Suggestion là tùy chọn, chỉ đưa nếu giải quyết vấn đề có căn cứ và giữ tất cả lựa chọn tác giả; không thêm hành động/thoại để lấp trường. Giữ nguyên quyền tác giả tự sửa và suggestion rỗng.
- Toàn bộ observation, impact, suggestion và question phải nhất quán với ý đồ và mâu thuẫn đã phát hiện. Không giữ note craft/uncertain thứ cấp tiếp tục phát triển chính kết quả vừa bị chỉ ra là trái nguồn, như phát hiện lỗi chốt tha thứ rồi lại bàn cách làm rõ cảnh tha thứ.

Giữ hướng đối chiếu hành động/kết quả với trạng thái đồ vật trước góp ý tùy chọn, không hardcode thư/rèm/đèn pin hoặc nhân vật vào prompt. Giữ schema, mã nguồn ngắn, metadata action/dialogue/cảnh đích, kiểm quote/ID gốc, snapshot và HITL. Không thêm judge, auto-fix, bộ dò từ khóa, chấm điểm hoặc cổng chặn lưu/sửa.

## Kiểm chứng provider giả

Từ `backend`:

```sh
.venv/bin/python -m pytest -q tests/test_screenplay_review.py tests/test_screenplay_review_priority.py tests/test_screenplay_writing.py tests/test_screenplays.py
```

**70 passed**, 4,48 giây. Đây là bộ backend tập trung, không phải chạy lại toàn repo/build/browser. Warning Starlette/httpx có sẵn còn nguyên.

- Sáu input đã lưu đi qua API bằng provider giả; xác nhận hướng dẫn v4 thực được truyền, cùng nguồn/metadata và schema hiện có. Cả ba bản tuân thủ nhận output notes rỗng định trước; ba bản vi phạm nhận output giả hai nguồn. Test kiểm giao thức và dữ liệu, không kiểm năng lực phát hiện của model.
- Các ca đèn pin có output giả vi phạm với/không có suggestion, notes rỗng, craft sai trọng tâm và phản hồi có note thứ cấp trái ràng buộc. Trường hợp cuối cố ý vẫn qua guard tham chiếu khi ID/quote đúng, để ghi rõ kiểm nguồn không chứng nhận tính nhất quán ngữ nghĩa. Không tự nhận bất kỳ thay đổi nào vào screenplay/M2.
- Mở lại 24 record từ các đợt Qwen v1/v2/v3 và Gemma v3: giữ nguyên review/version/status/snapshot, không gọi provider hoặc chuyển failed thành ready.
- Hồi quy nguồn, alias/quote sai, vai trò bằng chứng cảnh đích/ý đồ, revision/idempotency, kết quả muộn sau sửa/bỏ, ngữ cảnh/quota, timeout và quyền tự viết/lưu tiếp tục qua. Gói viết tay/AI viết thử không bị thay đổi.
- `git diff --check` và kiểm hash plan/roadmap/prototype, `.env`, tất cả bằng chứng model cũ đều qua. Bản sao source của từng đợt cũ vẫn khớp manifest lịch sử; không sửa manifest/output/nhãn để gán cho v4.

## Giới hạn

Provider giả trả output đã định trước. Việc test qua chỉ chứng minh hướng dẫn được gửi và các bảo vệ dữ liệu vẫn hoạt động; không chứng minh Qwen/Gemma hết gán sai, ép thêm hành động/thoại hoặc tự mâu thuẫn giữa các note. Guard vẫn chỉ xác thực nguồn/quote, không có bộ chấm lập luận. Lỗi chất lượng AI và nghiệm thu Gói 3 còn mở, chưa chạy thêm model hay chuẩn bị PR trong đợt này.

Tài liệu nền: [Gemma so với Qwen v3](m3-gemma2-vs-qwen-v3.md), [Qwen v3 so với v2](m3-constraint-first-qwen7b-comparison.md).
