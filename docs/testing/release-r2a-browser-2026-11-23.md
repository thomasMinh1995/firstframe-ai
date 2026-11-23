# R2a — saved-library và fixture chung
Baseline dev fc1b0d0 (sau #104). Chrome 158, Playwright 1.65.1, production frontend local; mọi project/image request được mock.

RED: suite gốc timeout tại nút Dự án mới bị thu trong details. Không phải lỗi thiếu dependency hoặc DB.
GREEN: giữ nguyên toàn bộ assertion và file saved-library.browser.cjs; PASS ở 1280, 897, 390 và 320px.
Helper mở đúng details/stage qua UI; GET draft-runs trả [] theo contract thay vì project.
Suite vẫn kiểm nguồn theo ID/history, ảnh thiếu/sai nguồn, modal/focus, restore conflict/success, đổi dự án và không ghi/gọi AI khi đọc.
CI có job browser riêng, cài Playwright/Chrome ngoài dependency frontend; chạy suite trên build sạch.
Typecheck/lint/28 frontend suites/build/diff-check PASS. Không đổi runtime ứng dụng hoặc assertion của suite.
Suite onboarding 7 bước cũ được xử lý riêng ở R2b; screenplay-context riêng ở R2c.
