# UI workspace đã chốt

- Ngày chốt: 24/10/2026, sau demo trọn luồng với người dùng.
- Issue: [#35](https://github.com/thomasMinh1995/firstframe-ai/issues/35).
- Phạm vi: Ý tưởng → Làm rõ → Story plan trong cùng workspace.

## Hành vi đã chốt

1. Nhập ý tưởng ngắn và giới hạn muốn giữ. Giao diện card là giao diện duy nhất tại `/`; không có classic override.
2. Làm rõ theo hội thoại từng câu: 5–6 câu đầu; mỗi lượt hỏi tiếp nối tối đa ba câu, tối đa 20 câu trong bộ hiện tại. Giữ nguyên thứ tự và câu trả lời cũ; sửa hoặc để quyết định sau được.
3. Xem lại nguyên văn lựa chọn rồi FirstFrame hỏi xác nhận. Chỉ nút Đồng ý khởi chạy tạo bản phát triển; sửa lựa chọn phải xem lại và xác nhận lại.
4. Tạo plan hiển thị ba nhóm và tám bước con từ sự kiện backend thật. Bước chưa chạy hiện chờ/chưa thực hiện; giữ đúng thứ tự audit thử lại.
5. Story plan gồm card ngắn theo đường chữ S: ba cột desktop, hai cột ở khung vừa, một cột trên mobile hẹp; DOM giữ thứ tự câu chuyện. Sửa ngay card, giữ khoảng trắng và nội dung card khác.
6. Góp ý cạnh card chỉ gắn khi nguồn card/câu trả lời Làm rõ khớp snapshot đã lưu. Nội dung đổi phải báo góp ý thuộc bản trước.

## Dữ liệu và quyền quyết định

Giữ state project/saved và buffer chung; Xong chỉ đóng ô sửa, Hủy/Escape chỉ hoàn tác card hiện tại. Lưu trước AI, revision/409 hai tab, đề xuất riêng và lịch sử tiếp tục theo luồng hiện có. Không tự nhận đề xuất hay tự thay bản đang viết.

Giữ cấu trúc project và request revision. Thêm `/clarify` và `/clarify/stream`, mở rộng validation answers từ 3 lên 20; `/analyze` cũ giữ hành vi hiện tại. Không migration dự án và không thay model mặc định/cấu hình môi trường.

## Phần để sau

Dàn cảnh và Kịch bản vẫn chưa hỗ trợ; sẽ chốt UI riêng khi triển khai. Không chủ động thiết kế lại ba phần đã chốt nếu không có yêu cầu mới hoặc lỗi cần sửa.

Chốt UI không thay nghiệm thu chất lượng/độ trễ model thật, pilot người dùng mới hoặc thiết bị thật. Demo hoàn chỉnh gần nhất dùng provider QA cố định; các lượt Qwen3 trước đó còn lỗi ràng buộc/timeout.

Xem [báo cáo kiểm thử tổng hợp](../testing/approved-story-workspace.md).
