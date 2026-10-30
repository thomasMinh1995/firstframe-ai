# QA-01: kiểm thử IME thật và VoiceOver trên Safari

Trạng thái: **đang chờ môi trường, chưa nghiệm thu**.

Nhánh `fix/safari-real-ime-voiceover` bắt đầu từ `dev` tại `1f3b9c4` (PR #87). Đợt này tiếp nối [kiểm thử mobile/Safari và IME logic](qa01-mobile-safari-ime-2026-10-30.md), tập trung vào bộ gõ và screen reader thật. Kết quả của PR #87 không được dùng thay cho bằng chứng của hai mục này.

## Đã chuẩn bị

- Tạo nhánh mới từ `dev`.
- Khởi động frontend/API QA riêng tại cổng 3035/8035, tái sử dụng `backend/tests/ui_workspace_fixture.py` với SQLite/dataset trong thư mục tạm và provider giả. Không dùng dữ liệu chính hoặc gọi model.
- Tạo project synthetic `QA IME thật và VoiceOver`, gồm hai cảnh `Lá thư chưa mở` và `Khoảng lặng`. Cảnh đầu có hành động và thoại của `Con gái`.
- Mở editor trên Safari native, sẵn các trường tiêu đề, hành động, người nói và lời thoại.
- Đọc lại đường xử lý composition, autosave, phím editor, dialog review và trạng thái tiến trình. Chưa xác nhận lỗi mới cần sửa từ đợt kiểm thử thật này.

Các tiến trình và dữ liệu tạm trên chỉ là môi trường đã chuẩn bị trong phiên làm việc, không phải dịch vụ được đảm bảo còn chạy khi mở lại báo cáo. Khi tiếp tục cần kiểm tra hoặc tạo lại fixture riêng.

## Chặn hiện tại

Công cụ điều khiển máy trả về `Computer Use was not approved to use System Settings` và `Computer Use was not approved to use VoiceOver`. Vì vậy chưa thể cấu hình hoặc kiểm chứng hoạt động thực tế của bộ gõ và VoiceOver qua các ứng dụng đó.

Đã yêu cầu người dùng bật VoiceOver, chọn bộ gõ tiếng Việt có sẵn và cho biết tên bộ gõ. Chưa nhận được xác nhận cấu hình. Không thay quyền hệ thống hoặc cài bộ gõ để vượt qua giới hạn này.

**Chưa có bằng chứng IME thật hoặc VoiceOver thật.** Unicode paste, sự kiện composition giả, unit test và cây accessibility không được tính là nghiệm thu thay thế. Chưa sửa mã ứng dụng và chưa chạy lại bộ test runtime trong đợt này.

## Checklist khi tiếp tục

Mọi mục bên dưới đều **chưa chạy**, không phải kết quả pass.

| Nhóm | Ca kiểm thử | Bằng chứng cần giữ |
| --- | --- | --- |
| Môi trường | Xác nhận phiên bản Safari/macOS, tên bộ gõ, kiểu Telex/VNI và VoiceOver đang bật | Cấu hình thực tế; phân biệt thông tin người dùng xác nhận với quan sát trực tiếp |
| IME nhập liệu | Gõ có dấu bằng bộ gõ thật ở ý tưởng, hành động, người nói và lời thoại; sửa dấu, xóa và chọn vị trí giữa câu | Chuỗi phím, nội dung cuối và dữ liệu API sau autosave/reload; không dùng paste làm bằng chứng bộ gõ |
| IME và phím editor | Enter xác nhận chữ/candidate không tách khối hoặc chuyển sang thoại sớm; Enter thường và Shift+Enter vẫn đúng sau khi kết thúc composition | Số khối, nội dung, người nói và vị trí focus trước/sau |
| IME và review | Escape khi đang composition không đóng nhầm panel hoặc hủy phần sửa; thử đóng/mở và đổi breakpoint sau khi nhập | Buffer còn nguyên; phân biệt Escape của bộ gõ với Escape đóng dialog |
| IME và lưu | Dừng khi đang ghép chữ, kết thúc nhập rồi chờ lưu; chuyển cảnh và mở lại | Không lưu trạng thái nhập dở; nội dung cuối được giữ, không gọi AI ngoài yêu cầu |
| VoiceOver và editor | Đọc heading, nhãn trường, cảnh đang chọn, trạng thái lưu; tương tác trường nhập bằng lệnh VoiceOver | Lệnh đã dùng và nội dung được đọc thực tế; chưa suy ra từ AX snapshot |
| VoiceOver và review | Mở/đóng dialog, thứ tự đọc và focus; modal mobile giới hạn trong panel, desktop vẫn điều hướng được editor | Kết quả đọc/focus ở desktop và Safari RDM; không coi RDM là thiết bị iOS thật |
| VoiceOver và tiến trình | Gọi review qua provider giả, đóng sheet lúc busy, theo dõi tiến trình và hoàn tất/lỗi | Close dùng được, nội dung vẫn khóa, focus hợp lý, thông báo không bị đọc lặp bởi timer |

Nếu phát hiện lỗi: lưu ca tái hiện trước sửa, sửa tại nơi dùng chung, thêm hồi quy phù hợp và lặp lại ca bằng đúng bộ gõ/VoiceOver. Sau đó chạy typecheck, frontend tests, production build và kiểm tra CI trên commit cuối.

PR của tài liệu này giữ dạng draft cho đến khi có bằng chứng kiểm thử thật và xử lý xong các lỗi tìm được. QA-01 và các gate thiết bị/screen reader tiếp tục mở; không đổi cờ rollout UI.
