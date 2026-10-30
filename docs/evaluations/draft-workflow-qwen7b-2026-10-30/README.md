# DR-10 — synthetic brief mới, Qwen 7b

Một lần chạy độc lập trên application revision `d1f4a64`, `qwen2.5:7b`, nhiệt độ 0.3, context 16384. Profile/model digest, brief, toàn bộ call nhận được, checkpoint và candidate nén đi cùng thư mục này. Không có DB tác giả hoặc tự retry call lỗi.

**Không đạt kỹ thuật:** 5 call, model 109.662s, toàn lượt 109.934s. Reasoning/plan/critic/outline được lưu; call viết cảnh đầu tiên trả structured response không hợp lệ. Run `interrupted`, hai scene rỗng, không có review/PDF. `review_error=null` không được tính thành review thành công: bước review chưa chạy. Frontend/backend giữ bản đã có và chặn tiếp tục vì call chưa rõ kết quả.

Không có ảnh PDF cho ca này vì kịch bản chưa có nội dung để xuất. Không dùng kết quả của ca khác để lấp dữ liệu của run này. Giới hạn này chặn phê duyệt phát hành.

Chạy lại như một phép thử mới, output directory mới:

```sh
backend/.venv/bin/python backend/scripts/check_draft_release.py --output /tmp/firstframe-new-brief-result
```
