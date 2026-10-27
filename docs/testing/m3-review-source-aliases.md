# M3 Gói 3 — Mã nguồn ngắn và loại khối rõ ràng

Ngày 27/10/2026, nhánh `feat/screenplay-evidence-feedback`. Chỉ triển khai bước 1–2 sau phân tích sáu output Qwen: adapter mã ngắn và metadata phân biệt cảnh đích/action/dialogue. Không triển khai thay đổi cách góp ý ở bước 3, không gọi model thật, không commit/PR. Giữ nguyên plan, roadmap, prototype và cấu hình local.

## Thay đổi

Request gửi provider dùng mã `S1…` cho nguồn kịch bản, `A1…` cho lựa chọn tác giả và `C1…` cho ngữ cảnh. Bảng ánh xạ chỉ tồn tại trong lượt gọi đó. Không đưa scene/block UUID làm tham chiếu để model phải chép; nguồn có `is_target`, `block_kind: action | dialogue | null` và `field` để phân biệt nội dung, tên người nói, tiêu đề hoặc lựa chọn nguồn.

Backend chỉ nhận đúng mã đã cấp, kiểm quote trong chính nguồn tương ứng, rồi chuyển bằng chứng về ID gốc trước khi lưu. Không lowercase/trim/đoán mã, tự thêm hậu tố hoặc tìm quote ở nguồn khác để cứu output. Không sửa output thô của provider. Nguồn/snapshot và hợp đồng API/frontend giữ nguyên; không cần migration hoặc sửa UI.

Giữ yêu cầu có bằng chứng khối văn bản cảnh đích; nghi lệch ý đồ cần thêm nguồn quyết định tác giả. Quote chỉ từ cảnh lân cận, tên người nói hoặc lựa chọn tác giả không đủ làm bằng chứng cảnh đích. Các bảo vệ checkpoint, revision, idempotency, kết quả muộn, bỏ lượt, lưu nháp, giới hạn ngữ cảnh/quota và quyền tự sửa giữ nguyên.

Prompt đổi version từ `screenplay-review-v1` sang `screenplay-review-v2-short-sources`, thêm hướng dẫn đọc mã/metadata mới. Chưa siết hoặc thay nhiệm vụ suy luận/tiêu chí nhận xét.

## Kiểm chứng bằng provider giả

Lệnh từ `backend`: `.venv/bin/python -m pytest -q tests/test_screenplay_review.py tests/test_screenplay_writing.py tests/test_screenplays.py`.

**62 passed**, 4,50 giây; gồm 29 ca review và 33 ca hồi quy viết tay/AI viết thử. Warning Starlette/httpx có sẵn còn nguyên. Có 14 ca kiểm chứng mới:

- Mã ngắn duy nhất, đúng nhóm; không gửi trường ID cảnh/khối gốc; cờ cảnh đích và loại action/dialogue/speaker đúng với snapshot. Bằng chứng lưu về ID gốc, output provider vẫn giữ mã ngắn, reload giữ nguyên dữ liệu.
- Từ chối sáu trường hợp: mã viết thường, mã có khoảng trắng, trả ID gốc thay mã được cấp, quote thuộc nguồn khác, chỉ dẫn lựa chọn tác giả và chỉ dẫn tên người nói. Mã không tồn tại/quote bịa/cảnh lân cận/thiếu lựa chọn ý đồ tiếp tục được kiểm ở các test cũ. Không tự retry hay mất bản tác giả khi lỗi.
- Đưa lại **đủ sáu đầu vào đã lưu** qua API với provider giả: ba bản tuân thủ trả `notes: []`, ba bản vi phạm trả nhận xét giả có hai nguồn để kiểm ánh xạ. Cả sáu qua hợp đồng, nguồn/loại khối/cảnh đích đúng, screenplay/M2 không đổi. Đây là output fixture đã định sẵn, **không phải model phát hiện đúng hoặc cải thiện chất lượng**.
- Mở lại cả sáu record lỗi `v1` cũ qua API không gọi provider, không nâng thành ready hoặc viết lại bằng chứng.

Contract frontend M3 review và screenplay đều qua, xác nhận nguồn/ID gốc và bảo vệ dữ liệu hiện có vẫn tương thích. `git diff --check` qua. Không sửa frontend nên không chạy lại build/browser trong đợt adapter này; bộ toàn backend 477 passed/1 skipped và browser trước đó là bằng chứng của lượt Gói 3 ban đầu, không được tính như đã chạy lại trên code mới.

## Giữ nguyên bằng chứng trước và giới hạn

Trước khi sửa, đã lưu code/prompt đúng lúc sáu lượt Qwen vào [thư mục source của đợt cũ](../evaluations/m3-scene-review-qwen7b-2026-10-27/source/). Hash từng file khớp manifest gốc. Input/schema/output/raw lỗi/comparison/manifest/audit cũ không sửa. Runner cũ vẫn từ chối code hash mới và không được chạy lại; không gán kết quả Qwen v1 cho adapter v2.

Kiểm hash sau thay đổi xác nhận plan/roadmap/prototype, `.env` và mọi bằng chứng cũ giữ nguyên. Chưa kiểm chứng model có sử dụng mã ngắn đúng hơn hay đọc action/dialogue chính xác hơn. Lỗi nhận xét sai và bỏ sót đèn pin ở sáu output cũ vẫn còn nguyên trạng thái chưa giải quyết; không gọi Gói 3 đạt chất lượng AI từ kết quả provider giả.
