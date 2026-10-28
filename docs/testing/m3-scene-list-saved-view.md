# M3 UI bước 2 — Danh sách cảnh thẳng và bản lưu song song

Ngày 27/10/2026. Nhánh `feat/m3-scene-list-saved-view`, từ `dev` tại `dc8d050` sau khi merge PR #58. Triển khai bước 2 của [plan PR #57](../plans/m3-ui-simplification.md), kế thừa editor đã kiểm chứng ở bước 1. Phạm vi đóng gói chỉ gồm bước 2 và kiểm chứng liên quan; chưa triển khai bước 3.

## Phần đã triển khai

- Danh sách cảnh theo đúng thứ tự M3, một hàng có mũi tên nối. Hiển thị số, tiêu đề và trạng thái có/chưa có nội dung; thao tác nối bằng scene ID, không dùng tên hoặc vị trí để suy nguồn. Dải dài chỉ cuộn ngang trong nav; focus bàn phím đưa cảnh cuối vào vùng nhìn. Trên màn hẹp thành đường thẳng dọc, mũi tên xuống, thứ tự DOM không đổi.
- Mở/bắt đầu bản kịch bản chưa tự chọn cảnh. Có trạng thái **Chọn một cảnh để viết**, form chỉ mở khi chọn cảnh hoặc theo đường quay lại sửa từ bản đọc. Mở/chuyển cảnh không lưu, không tạo bản mới và không gọi AI.
- Editor liền mạch bước 1 là vùng viết chính của cảnh đã chọn. Còn lựa chọn dùng editor dạng khối hiện có; chuyển chế độ không làm mất buffer. Không thay thuật toán tách/gộp/CRLF đã merge; chỉ cập nhật nhãn/hướng dẫn phù hợp trạng thái tích hợp.
- Desktop: vùng viết bên trái, **Kịch bản đã lưu** bên phải. Cột đọc tái sử dụng `SavedScript` từ `ScreenplayReading`, nhận đúng `savedProject` của cùng project/script ID; hiển thị toàn bộ cảnh, kể cả cảnh/khối chưa viết và người nói còn thiếu, đánh dấu cảnh đang chọn. Không có trường chỉnh sửa hoặc callback ghi trong bản đọc.
- Gõ/sửa/nhận phương án vào buffer không đổi cột bản lưu. Chỉ dữ liệu server đã xác nhận mới cập nhật phần đọc; phản hồi lưu đang chờ, lỗi mạng hoặc 409 không làm buffer trở thành bản đã lưu. Đổi phiên bản trong phần đọc lịch sử không thay cột đối chiếu current hoặc buffer.
- Lựa chọn cảnh gắn script ID và được đặt lại khi đổi bản kịch bản; đổi project tiếp tục dùng vòng bảo vệ lưu/đổi dự án hiện có. Không mang form, source hoặc lựa chọn cảnh từ project/script trước sang bản mới.
- Giữ các đường viết thử/góp ý, khôi phục, chọn nguồn M4 và snapshot hiện có. Liên kết bằng chứng vẫn chọn đúng cảnh/field rồi focus, không bỏ kiểm tra nguồn. Nguồn M2 hiện có nằm dưới vùng viết/đọc để dành hai cột; chưa làm nhóm hỗ trợ thu gọn mới hoặc ghép phác họa của bước 3. Không thay backend, schema, prompt/model, provider hay tour storage.

## Kết quả kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| TypeScript `--noEmit --incremental false` | Đạt sau build tái tạo type artifacts |
| Production build QA và build lại API mặc định sau QA | Đạt; không đổi `.env` |
| Node contract | **5 bộ đạt**: editor, screenplay, review, selection và bản đọc đối chiếu mới. Kiểm tra thứ tự/ID, đủ cảnh, khối rỗng, escaped text, read-only và không mutate nguồn |
| Backend M3 liên quan | **59 passed**, 5,69 giây: `test_screenplays.py`, `test_screenplay_review.py`, `test_screenplay_selection.py` |
| Chrome bố cục mới | Đạt trên 12 cảnh tổng hợp, có hai cảnh trùng tên: chưa chọn không có form, click mở đúng ID, nav một hàng/mũi tên và focus cảnh cuối có cuộn; desktop hai cột, mobile xếp dọc; chuyển A → B → A giữ cả hai buffer |
| Chrome phân biệt bản viết/bản lưu | Đạt: sửa A/B chưa lưu không vào cột đọc; giữ phản hồi PUT sau khi server đã ghi thì UI vẫn giữ bản lưu trước, chỉ cập nhật khi nhận xác nhận; đọc lịch sử không đổi comparison current; reload giữ đúng bản lưu |
| Chrome lỗi và đổi nguồn | Đạt: mất mạng/409 giữ buffer và bản đọc; đổi dự án khi lưu lỗi không rời dự án; đổi dự án thành công lưu theo luồng cũ, quay lại chưa chọn cảnh; bắt đầu script ID mới không mang form hoặc text cũ; tour completed giữ nguyên |
| Chrome hồi quy M3 | **5 bộ đạt**: editor liền mạch (gồm CRLF, IME mô phỏng, focus bằng chứng), viết tay dạng khối, AI viết thử, góp ý và đọc/chọn nguồn M4. Cập nhật entry test để chọn cảnh rõ ràng; các suite dạng khối chủ động chọn editor cũ, không thay kỳ vọng dữ liệu/nguồn |
| Chrome bàn giao M2 → M3 | Đạt `scene-handoff.browser.cjs`: nguồn đã lưu, buffer, mất mạng/409, phương án/staging có quyền chọn, hướng dẫn M2 và tiến độ tour |
| Trình bày | 1440/390/320px của bộ layout và 1280/390/320px của các suite M3 không tràn cả trang; nhiều cảnh cuộn trong nav desktop, mobile vẫn tới được mọi cảnh. Đã xem ảnh QA desktop/mobile |
| Phạm vi | Hash plan M3, plan UI, prototype và bốn tài liệu local ngoài phạm vi giữ nguyên; đóng gói riêng code/test/báo cáo bước 2 |

Tổng cộng **7 bộ Chrome đạt**, mỗi bộ dùng `ui_workspace_fixture.py`, SQLite/profile QA mới và provider giả. Bộ layout không có lượt text/image/review nào; các bộ hồi quy chỉ gọi provider giả khi kịch bản test chủ động yêu cầu. Không mở DB tác giả, dùng API trả phí hoặc chạy model thật.

Các lỗi khi chạy kiểm chứng được tách khỏi lỗi ứng dụng:

- TypeScript lần đầu thấy các tệp type sinh trùng tên `* 2.ts` trong `.next/types`. Build mới tái tạo artifacts, sau đó typecheck đạt; không sửa tsconfig hay loại trừ source để che lỗi.
- Suite editor còn selector tên “thử nghiệm” của bước 1; cập nhật tên truy cập thành “Editor liền mạch” và chạy lại trên fixture mới, giữ các assert round-trip/ID/CRLF.
- Suite bàn giao M2 còn đòi câu “M3 hỗ trợ soạn thủ công”, trong khi copy trên `dev` từ trước đợt này là “Sang M3 để tự viết hoặc chủ động chọn phương án AI”. Đã đối chiếu source `origin/dev`, chỉ cập nhật assertion theo copy hiện có rồi chạy lại đạt; không sửa UI M2 hoặc hạ điều kiện bảo vệ dữ liệu.

Log và ảnh giữ local tại `/tmp/firstframe-m3-layout-*` và các thư mục QA `firstframe-workspace-*`. Bằng chứng bố cục: `firstframe-workspace-ev5r1cyo/scene-layout-{1440,390,320}.png`; các thư mục đều nằm dưới thư mục tạm của hệ điều hành. Không đưa tác phẩm thật vào repo hoặc fixture.

## Chạy lại và giới hạn

Dùng cách chạy fixture/build/CJS tại [báo cáo bước 1](m3-continuous-editor.md). Biên dịch thêm bản `ScreenplayReading.tsx` hiện tại có export `SavedScript`, rồi chạy `screenplay-layout-contract.cjs` cùng bốn contract M3/editor. Các suite browser: `screenplay-layout`, `screenplay-continuous`, `screenplay`, `screenplay-writing`, `screenplay-feedback`, `screenplay-selection`, `scene-handoff` (hậu tố `.browser.cjs`); mỗi suite có fixture mới. Frontend QA chạy tại 3034, API fixture tại 8034; kết thúc QA dừng server đã tạo và build lại cấu hình mặc định.

Chưa ghép/tạo phác họa, di chuyển AI/source vào nhóm hỗ trợ mới hoặc cập nhật hướng dẫn tour của bước 3. Giữ phần đọc lịch sử/M4 hiện có, không triển khai xuất bản. Bản lưu hiển thị toàn bộ nên có thể dài với nhiều cảnh; bước này không thêm editor chế bản hoặc phân trang.

IME/clipboard mới ở mức mô phỏng/nhập native có kiểm soát kế thừa bước 1; chưa thử IME hệ điều hành, clipboard thật, screen reader, thiết bị thật, Safari hoặc Firefox. Kiểm tra kỹ thuật không chứng minh critic tốt hơn hoặc người mới đã dùng dễ hơn; nghiệm thu và các tiêu chí #7/#22/#26 tiếp tục giữ nguyên.

## Review trước khi đóng gói

Đã đối chiếu đường gọi `page.tsx` → `ScreenplayEditor` → editor/bản đọc, cùng callback lưu, kiểm tra kết quả, khôi phục và lựa chọn nguồn M4. Cột đọc không nhận buffer/proposal; việc chọn cảnh chỉ đổi trạng thái UI. Kiểm tra project/script ID ngăn hiển thị bản lưu của nguồn khác; form/selection được đặt lại khi đổi bản kịch bản. Form phương án riêng và kiểm tra nguồn/field khi điều hướng góp ý vẫn giữ.

Không phát hiện lỗi chặn trong phạm vi ứng dụng local với bảo vệ revision/CAS hiện có. Giữ bằng chứng TypeScript/build, 59 test backend, 5 contract và 7 bộ Chrome của cùng code triển khai ở trên; không thay code sau các lượt đó, không chạy thêm model. Commit/PR chỉ gồm 14 file code/test/báo cáo liên quan; plan/prototype và mọi thay đổi local ngoài phạm vi được giữ ngoài commit. Các giới hạn thiết bị/IME/nghiệm thu nêu trên vẫn mở.
