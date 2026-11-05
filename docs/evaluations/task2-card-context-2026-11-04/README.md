# Task 2 — Đo ngữ cảnh card, 04/11/2026

[Báo cáo](../../testing/task-2-card-context.md) · [Tổng hợp](summary.json) ·
[Ngân sách/case ban đầu](cases-initial.json) · [Case bổ sung đúng focus](cases.json) ·
[Ledger toàn bộ call](calls.json).

PR #98 tiếp tục là draft. Adapter đã có test hồi quy và ca ngồi → đứng đạt
3/3; đối chứng vi phạm còn sai nên không coi critic đã được nghiệm thu.

[raw-evidence.tar.gz](raw-evidence.tar.gz) giữ các request, response, schema,
source project, kết quả API và profile/diff của 24 call. Archive đã được
giải nén và đối chiếu byte với bản gốc. SHA-256:

`90fb14c3bb10f727be07247edd9f2ea659fd003b16e96265872aa38ee7cd1a27`

- `baseline-*`: ba lượt trước sửa adapter, gồm ca mới đóng sách.
- `candidate-*`: đoạn nguyên đặt sau cards/prompt dài. Giữ chín lượt positive
  báo sai và ba lượt đối chứng có nhiều phần cùng thuộc focus. Đã dừng trước
  các ca còn lại khi xác nhận ứng viên không đạt; không retry model.
- `focused-*`: đoạn nguyên đặt lên trước/prompt ngắn. Ba lượt ngồi → đứng
  đúng; ba lượt đối chứng cũ bị lựa chọn phần mở đầu hoặc trả sai hợp đồng.
- `scoped-*`: hai đối chứng mới có preflight chỉ Ending thuộc focus và một
  lượt ca đóng sách. Cả hai đối chứng vi phạm vẫn chưa đạt nội dung.

Không thay thế các case cũ bằng case bổ sung để tính điểm. Profile ghi hash
case trước từng call và diff source thực dùng; `cases-initial.json` khớp hash
các lượt trước bổ sung. Raw response có thể hợp schema provider nhưng bị
guard ứng dụng từ chối; xem cả `response.json` và `result.json`.

Giải nén để đọc trong một thư mục tạm mới:

```sh
task2_card_evidence=$(mktemp -d)
tar -xzf docs/evaluations/task2-card-context-2026-11-04/raw-evidence.tar.gz -C "$task2_card_evidence"
```

`run.py` là bản lưu thao tác đo một lần, dùng API và snapshot từ archive đợt
trước, không phải dịch vụ/QA framework mới. Đợt này đã dùng đủ số call được
chốt; không chạy tiếp vào ledger/evidence cũ. Đợt mới cần ngân sách và thư
mục riêng. Output không được tự sửa, loại hoặc sinh lại để đạt tiêu chí.
