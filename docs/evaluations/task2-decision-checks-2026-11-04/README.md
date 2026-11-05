# Task 2.2a — Đối chiếu từng quyết định, 04/11/2026

[Triển khai và review](../../testing/task-2-decision-checks.md) ·
[Tổng hợp](summary.json) · [Case/ngân sách chốt trước](cases.json) ·
[Ledger](calls.json) · [Model metadata](model.json).

Baseline `8d97d5a`; bản triển khai giữ trên nhánh draft để review, chưa nhận
vào dev. Full backend 894 passed, 1 skipped. Model thật chưa đạt: 0/5 lượt
ứng viên được API nhận; không coi việc trả lỗi là phát hiện đúng vi phạm.

Đã dùng 12/28 call, 394,002/1.500 giây provider. Không retry hoặc chỉnh
output. Dừng vì lượt đầu chưa qua cổng chất lượng, chưa xác nhận ba lượt
hoặc chạy ứng viên trên cặp ca mới giữ lại. PR #98 draft, #96 mở.

[raw-evidence.tar.gz](raw-evidence.tar.gz) chứa đủ request/schema, source,
response thô/parsed, kết quả API, project mở lại sau call và profile/diff
của cả 12 call. Đã so sánh source/input trước-sau và đối chiếu byte archive
với bản gốc. SHA-256:

`f6489f21c738939bb82ad1b44eff42ef76b33dbf5d3e4521a16a235638752cbd`

- `baseline-*`: bảy ca trên checkout baseline tách biệt, có cặp gốm giữ lại.
- `checks-*`: năm lượt phát triển trên bản triển khai 2.2a, kể cả mọi lỗi.
  Xem cả response và result/reopened để phân biệt model hợp shape với
  output qua guard. Metadata provider ghi tham số yêu cầu, không có token
  usage/context thực từ adapter.

`run.py` tái dùng thao tác đo API một lần của đợt trước. `TASK2_SOURCE_ROOT`
chọn checkout baseline; mặc định dùng repo hiện tại. SQLite/dataset tạm;
source tổng hợp từ archive đợt đầu. Không có dịch vụ hoặc QA framework mới.
Không chạy thêm vào ledger đã bàn giao; batch sau cần nguồn/ngân sách riêng.
