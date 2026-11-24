# R2b khôi phục hướng dẫn 7 bước

Baseline dev e8ce084. Bản hướng dẫn trước hiển thị 6 bước, nên browser suite legacy timeout tại Bước 1/7. Contract mới khôi phục Dự án mới, Chất liệu, Làm rõ, Story plan, Dàn cảnh, Viết & sửa và Lưu. Dữ liệu tiến độ v2 và v3 đọc được, với mục Phát triển câu chuyện chuyển về Làm rõ và Đọc & xuất chuyển về Lưu.

Unit test kiểm tra thứ tự, tiến độ cũ, chuyển bước theo dữ liệu dự án, lỗi, kết quả đến muộn và bỏ qua từ cửa sổ khác. Browser CI mở đủ 7 bước ở cả 1280px và 390px, kiểm tra focus ở lịch sử và lưu, trạng thái hoàn tất và dữ liệu/API giữ nguyên sau hướng dẫn.

Browser suite legacy giữ nguyên các kỳ vọng. Fixture dùng chung cập nhật xác nhận lưu. Toàn suite vẫn đỏ. Khi chạy tới Làm rõ, ca cũ đợi Tiếp tục và xác nhận lựa chọn trước khi lập kế hoạch. Giao diện hiện tại dùng ô trả lời mở với hành động tạo Story plan và có unit test cho contract đó. Một lượt chạy lại cũng timeout kiểm tra focus trong lúc huỷ hướng dẫn khi yêu cầu đang chờ. Hai kết quả này được theo dõi riêng với ca browser 7 bước trong CI.

Các ca chạy trên production build local với API giả. Đánh giá người dùng cuối thuộc R4.
