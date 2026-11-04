# Task 2 — Evidence đợt đầu, 04/11/2026

[Báo cáo và kết luận](../../testing/task-2-screenplay-quality.md).
[Tổng hợp kiểm chứng](summary.json), [bộ ca/ngân sách](cases.json),
[model](model-info.json), [ledger](calls.json).

Không có thay đổi runtime được nhận. Hai prompt ứng viên không đạt; issue
#96 tiếp tục mở. `passed`/`aligned` trong output model không phải nhãn
chất lượng của người đọc.

Raw request, schema, response, project snapshot và profile nằm nguyên vẹn
trong [raw-evidence.tar.gz](raw-evidence.tar.gz), để diff tài liệu không bị
che bởi hàng nghìn dòng JSON. SHA-256 archive:

`c8ba9f4cac6ce74c8a8f23f24dfa317f7686451164ede8e86dbe21d44152c878`

Các nhóm trong archive:

- `baseline-raincoat`: setup lỗi đường dẫn trước khi gọi model.
- `baseline-raincoat-1`: sandbox chặn kết nối local, không có response model.
- `baseline-raincoat-2`, `baseline-empty-fridge`, `baseline-held-out`:
  baseline API analyze → plan (kèm góp ý ban đầu).
- `edited-raincoat`, `edited-empty-fridge`, `edited-held-out`: bản sửa thủ
  công, review và request/response, giữ nguyên nội dung draft sau review.
- `candidate-review-<case>-1..3`: sáu lượt replay cùng input/schema, thay
  prompt góp ý. Các nhận xét thiếu căn cứ vẫn còn; không nhận prompt.
- `candidate-plan-<case>-1..3`: chín lượt replay, ba lượt cho mỗi ca, thay
  prompt planner. Có vi phạm nguồn/điểm dừng; không nhận prompt.

Mỗi thư mục có `profile.json` ghi baseline commit và diff prompt thực dùng;
`request-*.json` giữ instructions thực đã gửi. Runtime đã trả về baseline
nên diff hiện tại không còn những ứng viên đó. Không sửa output lịch sử.

Để đọc, giải nén vào một thư mục tạm mới:

```sh
task2_evidence=$(mktemp -d)
tar -xzf docs/evaluations/task2-story-quality-2026-11-04/raw-evidence.tar.gz -C "$task2_evidence"
```

`run.py` lưu cách đo một lần, không phải entrypoint ứng dụng hoặc bộ QA mới.
Ngân sách của đợt này đã dừng; không tự chạy tiếp hoặc ghi vào evidence cũ.
Các sửa thủ công và lý do vẫn để ở JSON riêng cạnh archive để đọc nhanh.
