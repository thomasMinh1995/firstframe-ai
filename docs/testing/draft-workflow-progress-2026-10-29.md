# Kiểm chứng tiến độ workflow DR 01 và DR 02

Ngày 29/10/2026. Nhánh `fix/draft-workflow-progress` từ `dev` sau PR #78. Phạm vi là hợp đồng và lưu tiến độ backend cho prototype Bản nháp & Review; phần card, đường chữ S và hiệu ứng thuộc DR-03–DR-08.

## Hợp đồng đã triển khai

GET danh sách/run và response tạo/tiếp tục/hủy giữ các trường cũ, bổ sung:

- `progress_version`: 1 cho run có dữ liệu tiến độ mới; 0 cho phép chiếu run cũ chỉ khi đọc.
- `progress_revision`: tăng khi item, trạng thái run, bước, yêu cầu hủy hoặc trạng thái nhận bản thay đổi. Không tăng do GET/poll hoặc chỉ ghi nhận raw call. Độc lập với `candidate_revision`.
- `workflow_items`: bảy mục nền `analysis`, `intent`, `plan`, `plan_review`, `outline`, `review`, `draft`; thêm một `write:<scene_id>` cho mỗi cảnh có ID screenplay. `review.children` giữ trạng thái review từng cảnh, với ID `review_scene:<scene_id>`.
- `can_continue`, `continue_block_reason`, `continue_block_message`: cùng điều kiện với giao dịch claim của route continue. Cấu hình AI không khả dụng không ngăn đọc lại bản đã lưu.

Mỗi item có kind, scene ID khi liên quan, status, thời điểm bắt đầu/kết thúc quan sát được, mã lỗi an toàn và tham chiếu kết quả cùng candidate revision. Các trạng thái là `pending`, `running`, `needs_input`, `completed`, `warning`, `failed`, `interrupted`, `cancelled`, `skipped`; thêm `unknown` cho phần lịch sử không đủ bằng chứng.

Card completed đòi hỏi tham chiếu kết quả đã lưu. Không thêm lần gọi AI cho mục ý đồ. Candidate và các thay đổi item của checkpoint được ghi cùng giao dịch SQLite; progress mới nằm trong JSON của bảng draft_runs hiện có, không thêm bảng hoặc queue.

Critic story plan được lưu riêng trong `plan_review_result`; GET candidate trả `plan_review` để đọc kết quả tương ứng. Response tiến độ dùng schema whitelist trong OpenAPI, không trả raw calls, prompt, cấu hình nội bộ, original hoặc candidate đầy đủ. `error`/`review_error` công khai được chuyển thành thông báo an toàn; chi tiết gốc tiếp tục nằm trong DB riêng của run.

## Hành vi lỗi và dữ liệu cũ

- Critic story plan lỗi: mục plan vẫn completed, critic warning, dàn cảnh/viết tiếp tục được.
- Review screenplay lỗi: văn bản vẫn đọc được, review warning; cảnh chưa review được đánh dấu skipped, không tính là thành công.
- Hủy: giữ kết quả về muộn đã lưu của bước đang gửi; các bước sau chưa chạy là skipped. Không gọi bước AI tiếp theo.
- Restart: item đang chạy chuyển interrupted trong cùng cập nhật run. Kết quả raw đã nhận trước crash được replay từ SQLite, không gọi model trùng. Lần gọi sinh nội dung chưa rõ kết quả vẫn bị chặn tiếp tục.
- Nếu restart trong critic đã gửi nhưng chưa lưu kết quả ứng dụng, resume không tự retry critic hoặc tô completed; giữ warning và tiếp tục phần sinh nội dung khi an toàn.
- Run cũ: chỉ chiếu thành công từ artifact hiện có; critic và ý đồ không đủ lịch sử hiện unknown; timestamp để null. GET không migrate/ghi DB. Khi run cũ thực sự tiếp tục hoặc chỉnh, tiến độ mới được lưu từ mốc có bằng chứng.
- Chỉnh candidate rỗng một cảnh: item cảnh và bản nháp đổi needs_input, run partial; nhận xét cũ giữ tham chiếu nguồn trước. Không tự sinh lại nội dung bị xóa.

`can_continue` mô tả trạng thái tại lần đọc, không thay kiểm tra revision/config trong transaction. Nó không đảm bảo một yêu cầu dùng revision cũ sẽ thành công khi có cập nhật đồng thời. Thay đổi cấu hình bên ngoài DB được phản ánh ở capability của lần đọc mới, không làm GET tự ghi progress revision.

## Kiểm thử

Provider giả và SQLite tạm được dùng để kiểm tra API/runner thực; không gọi model live và không sử dụng DB dự án đang viết.

39 ca tập trung gồm 15 ca draft-run hiện có và 24 ca tiến độ mới: 1/2/6 cảnh; cần làm rõ/đủ rõ; đọc plan trước critic; critic lỗi riêng; lỗi review; timeout sau một cảnh; hủy trước critic và trong lúc viết; crash sau nhận raw output nhưng trước checkpoint; restart critic; đọc run cũ không ghi; resume run cũ; điều kiện tiếp tục khi đổi cấu hình/chỉnh candidate/hủy/đã nhận/thiếu provider; rollback artifact và tiến độ; whitelist API và OpenAPI.

**Kết quả bản cuối: 39 ca tập trung đạt; toàn bộ backend 653 passed, 1 skipped.** Có một cảnh báo deprecation Starlette/httpx đã có từ trước. `git diff --check` đạt. Frontend không thay đổi trong mốc này.

Lệnh kiểm chứng từ repository root:

```bash
backend/.venv/bin/python -m pytest -q -c backend/pyproject.toml backend/tests/test_draft_progress.py backend/tests/test_draft_runs.py
cd backend
.venv/bin/pytest -q
```

Lệnh dùng môi trường Python backend đã cài; worktree có thể dùng đường dẫn tuyệt đối tới môi trường dùng chung.

Giai đoạn này chưa nghiệm thu giao diện S, skeleton/reveal, browser/mobile hoặc chất lượng nội dung model. Các phần đó giữ trong mốc triển khai tiếp theo và QA-01.
