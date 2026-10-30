# DR-10 — brief đã lưu, Qwen 7b

Chạy độc lập, giữ nguyên ý tưởng/constraints của [ca phase 6](../phase6-qwen7b-2026-10-29/result.json), không tái sử dụng văn bản model cũ. Application revision `d1f4a64`, cùng model/nhiệt độ/context với ca mới. Đây không phải retry run lỗi; cả hai kết quả được giữ trong báo cáo.

**Đạt đường kỹ thuật:** 12 call được ghi nhận (kể cả các call review theo logic có sẵn); model 126.016s, toàn lượt 128.963s. Một lần bắt đầu, một lần tiếp tục sau câu hỏi; để mở các câu trả lời. Hai cảnh có nội dung, hai review đã lưu, `review_error=null`. Nhận/chọn/PDF đều HTTP 200; selection giữ đúng screenplay. Chặn provider trong bước chọn/xuất, không thêm call AI. Không suy ra độ chính xác của góp ý từ trạng thái completed.

PDF một trang đã render bằng Poppler: tiếng Việt, heading, thứ tự block và số trang đọc được, không thấy chữ bị cắt hoặc ô vuông. Đã mở run này qua UI trong evidence viewer chặn AI writes, hiển thị chín card, chọn/tải lại PDF; text PDF từ UI khớp PDF từ API.

**Chưa đạt chất lượng/phát hành:** đọc thủ công bởi agent thấy đổi chủ thể đặt chìa khóa từ con gái sang cha, câu vừa cho cha đứng vừa cho cả hai ngồi, và cảnh hai lặp nhịp uống trà. Chi tiết ở `content-observations.json`. Đây không thay cho người đọc độc lập; không chỉnh văn bản để làm đẹp kết quả.

- `report.json`: kết quả kỹ thuật và `release_approved=false`.
- `profile.json`, `model-info.json`, `brief.json`: cấu hình và nguồn synthetic.
- `calls.json`, `progress.json`, `run.json`, `candidate.json.gz`: dữ liệu thực đã ghi.
- `selection.json`, `screenplay.pdf`: snapshot đã chọn và PDF đúng snapshot.

```sh
backend/.venv/bin/python backend/scripts/check_draft_release.py --output /tmp/firstframe-saved-brief-result --brief-source docs/evaluations/phase6-qwen7b-2026-10-29/result.json
```
