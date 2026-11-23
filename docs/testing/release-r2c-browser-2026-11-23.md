# R2c — screenplay-context
Baseline dev 77452d3 (sau #106), Chrome 158 / Playwright 1.65.1.
RED: production build với API base :8034, fixture sạch; suite gốc timeout chờ scene list khi workspace còn ở stage Chất liệu.
GREEN: giữ nguyên mọi assertion; mở Viết & sửa trước khi chọn cảnh, kể cả sau reload; dùng nhãn hiện tại của ô yêu cầu sửa.
PASS buffer/focus, đóng/mở support không ghi/gọi AI, frozen source, trùng tên/đổi thứ tự cảnh, ảnh khác nguồn/thiếu ảnh, lưu và 1440/390/320px.
CI job browser chạy thêm fixture ui_workspace_fixture.py, SQLite/ảnh trong thư mục tạm và provider giả, PYTHON_DOTENV_DISABLED=1; không .env/model thật.
Typecheck/lint/28 frontend suites/build/diff-check PASS. Không đổi runtime hoặc assertion nội dung/hành vi của suite.
R2b onboarding vẫn tạm hoãn theo xác nhận người dùng: giữ mọi kỳ vọng cũ, kể cả 7 bước; không đưa suite đó vào CI như một ca đã đạt.
