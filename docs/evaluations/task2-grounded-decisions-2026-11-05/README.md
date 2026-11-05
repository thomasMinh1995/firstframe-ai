# Task 2.2a — Neo quote vào nguồn, 05/11/2026

[Triển khai/review](../../testing/task-2-grounded-decisions.md) ·
[Tổng hợp](summary.json) · [Case/ngân sách](cases.json) · [Ledger](calls.json) ·
[Replay adapter cuối](final-contract-replay.json) · [Model metadata](model.json).

Baseline `f77385c`. Bản kỹ thuật giữ trên draft PR #98, #96 còn mở. Full
backend 902 passed, 1 skipped; model vẫn 0/5 output được nhận, không coi
guard trả 502 là phát hiện đúng vi phạm. Chưa xác nhận ba lượt/ca giữ lại.

Đã dùng 7/28 call, 487,798/1.800 giây provider. Hai baseline mới; ba baseline
còn lại lấy từ archive đợt 04/11 và không tính thành call mới. Source/input
đã được đối chiếu giống hệt. Không retry, sửa output hoặc đổi model.

[raw-evidence.tar.gz](raw-evidence.tar.gz) giữ nguồn, request/schema, response
thô/parsed, API result, project mở lại và profile/diff của cả bảy call.
Archive đã được đối chiếu byte với bản gốc. SHA-256:

`58aa34fd835d6b20b33f698ff56d451bed89d2ea68901a58d1d55f2e406f2273`

Các call đầu dùng guard quote một card; review bổ sung quote qua nhóm card
liền nhau đã dẫn và sửa câu mô tả. Xem profile thực dùng ở từng call và hash
source cuối trong summary. Replay năm output qua adapter cuối vẫn từ chối
cả năm; đây không phải năm lượt model mới hoặc xác nhận chất lượng.

`run.py` tái dùng thao tác đo API một lần của đợt trước, SQLite/dataset tạm,
nguồn tổng hợp; không thêm QA framework. Ledger đã đóng: batch tiếp theo
cần thư mục/ngân sách riêng, không thêm call vào bằng chứng đã bàn giao.
