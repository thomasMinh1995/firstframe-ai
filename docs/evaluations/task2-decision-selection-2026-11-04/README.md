# Task 2 — Chọn quyết định, 04/11/2026

[Báo cáo và review](../../testing/task-2-decision-selection.md) ·
[Tổng hợp](summary.json) · [Ngân sách/case](cases.json) ·
[Case ban đầu](cases-initial.json) · [Ledger](calls.json).

Không ứng viên nào được nhận. Runtime được trả về `e71d863`, PR #98 draft,
#96 mở. Đã dùng 15/28 call, 280,233/1.200 giây provider, không retry. Dừng
vì các ứng viên còn sai, không phải hết ngân sách. Chưa chạy xác nhận ba
lượt hoặc so sánh ứng viên trên ca giữ lại; không tuyên bố nghiệm thu.

[raw-evidence.tar.gz](raw-evidence.tar.gz) chứa đầy đủ 15 thư mục call,
bao gồm request, response thô/parsed, source, API result và profile/diff.
Archive đã được đối chiếu byte với bản gốc. SHA-256:

`aeff6dfaf203f6a5e79ea9061e84731a611a08b6d42575dda5d3284762c8683d`

- `baseline-*`: năm baseline, gồm ca may cúc positive đầu có điểm dừng mơ
  hồ và ca bổ sung `sewing-before-cut`. Không thay/xóa ca ban đầu.
- `candidate-*`, `ordered-*`, `choices-first-*`, `editing-*`, `concise-*`:
  năm ứng viên, mỗi ứng viên hai ca phát triển. Xem diff trong profile của
  từng call để phân biệt chính xác source thử, không gộp thành ba lượt.
- Diff của mọi ứng viên, gồm bản cuối bị loại, được giữ trong profile của
  từng call; không cần lưu thêm một bản patch trùng lặp ngoài archive.

`run.py` lưu thao tác đo API một lần, tái dùng script từ đợt trước với
nguồn snapshot tổng hợp; không thêm dịch vụ hoặc QA framework. Không chạy
thêm vào ledger/evidence đã bàn giao; đợt tiếp theo dùng ngân sách/thư mục
riêng. Không thay đổi output hoặc kỳ vọng để tăng tỷ lệ đạt.
