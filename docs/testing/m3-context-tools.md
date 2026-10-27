# M3 UI bước 3 — Nguồn, ảnh và thao tác sẵn có

Ngày 27/10/2026. Nhánh `feat/m3-context-tools`, từ `origin/dev` tại `11ca5b7` sau PR #59. Phạm vi: bước 3 của [plan PR #57](../plans/m3-ui-simplification.md); chưa triển khai bước 4 hoặc M4.

## Thay đổi

- Nguồn M2/ý đồ, ảnh, viết thử và góp ý nằm trong các mục hỗ trợ thu gọn ngay trong cột viết. Lần đầu các mục đóng; mở/đóng chỉ đổi UI, không lưu hoặc gọi AI. Component bên trong vẫn được giữ khi thu gọn, nên yêu cầu thêm, trạng thái chưa rõ kết quả và đường kiểm tra kết quả không bị đặt lại.
- Tái sử dụng toàn bộ callback đang có: lưu trước tác vụ AI, chỉnh phương án riêng, xác nhận dùng đúng một cảnh, bỏ/hoàn tác; góp ý mở nguồn đã giữ, dẫn tới đúng field khi còn khớp, ghi nhận hữu ích/dẫn sai và để tác giả tự sửa. Không đổi prompt, model hoặc hợp đồng backend. Thu hẹp anchor tới `.screenplay-author-fields` để không focus nhầm form phương án nằm cùng cột.
- Giữ phần đọc toàn bản đã lưu/lịch sử, khôi phục và chọn nguồn M4 hiện có. Bản đọc vẫn dùng `savedProject`, không nhận buffer/proposal. Không đổi điều kiện đủ bản M4, revision/CAS, request ID, kiểm tra sau mất response hoặc snapshot bất biến.
- Danh sách cảnh có ảnh M2 đang chọn giữ nếu khớp nguồn M3. Ghép bằng `source_scene_id`, lấy từ lựa chọn ảnh của **dự án đã lưu**, đối chiếu toàn bộ ID/nội dung/ý đồ trong `screenplay.source_outline`; không ghép bằng tên/thứ tự, không dùng M2 hiện tại thay snapshot cũ. Chỉ bỏ qua bộ đếm lưu `outline.version`; thứ tự key object không được coi là thay đổi nội dung.
- Không dựa vào `applicable_sketch_ids` của M2 hiện tại để quyết định ảnh hợp với M3 cũ: ảnh đang giữ có thể vẫn đúng nguồn M3 dù M2 đã đổi. Nếu tác giả chọn ảnh mới khác nguồn, không tự lấy ảnh cũ chưa được chọn làm thumbnail thay thế. Ảnh khác nguồn chỉ có trong mục đối chiếu mang cảnh báo riêng.
- Nhãn nói rõ ảnh tham khảo theo lựa chọn M2 hiện đang lưu, có thể đổi; **M3 chưa chụp lựa chọn ảnh theo lịch sử**. Không tuyên bố ảnh bất biến đi cùng bản kịch bản. Không có ảnh/asset lỗi vẫn tự viết và lưu được. Chỉ dùng đường đọc asset theo project/sketch có sẵn; không thêm tạo ảnh, OCR, suy luận ảnh, migration hoặc provider.
- Hướng dẫn tại chỗ và hai đoạn mô tả tour được cập nhật theo cách chọn cảnh/mở hỗ trợ. Không đổi sáu bước tour, storage/version, tiến độ, bỏ qua hoặc phát lại.

## Kiểm chứng

Fixture tổng hợp, SQLite/profile QA riêng, frontend production QA tại `3034`, API fixture `8034`. Không dùng DB tác giả hoặc model thật. Không thay `.env`; kết thúc QA dừng server tạo trong phiên và build lại cấu hình mặc định.

| Kiểm tra | Kết quả |
| --- | --- |
| TypeScript `--noEmit --incremental false` | Đạt |
| Production build QA / build lại mặc định | Đạt |
| Frontend contract | **6 bộ đạt**: editor, screenplay, review, selection, bản đọc song song và helper ảnh mới |
| Backend | **76 passed**: `test_screenplays.py`, `test_screenplay_review.py`, `test_screenplay_selection.py`, `test_scene_sketches.py`. Có một cảnh báo deprecation Starlette/httpx hiện hữu; không đổi dependency |
| Chrome nguồn/ảnh mới | Đạt: mặc định thu gọn, giữ yêu cầu khi đóng/mở, toggle/chuyển cảnh không ghi hoặc gọi AI; hai cảnh trùng tên không tráo ảnh; đổi thứ tự/nội dung M2 vẫn đọc nguồn M3 cũ; lựa chọn ảnh mới khác nguồn không thành thumbnail hợp lệ; asset 404 có fallback và vẫn lưu được |
| Chrome editor/bố cục | Đạt: round-trip, ID/Unicode/CRLF, các thao tác editor cũ, 12 cảnh, buffer tách bản lưu, lỗi mạng/409/response chậm, đổi project/script và anchor góp ý |
| Chrome viết thử/góp ý | Đạt: phương án riêng, dùng/bỏ/hoàn tác, stale source, quote/focus, ghi nhận thủ công, lỗi/timeout, mất response không retry. Đóng/mở phần hỗ trợ sau mất response vẫn giữ khóa gửi mới cho đến kiểm tra kết quả |
| Chrome lịch sử/M4/M2/tour | Đạt: đọc current/history không lưu buffer, khôi phục, chọn đúng bản đã đọc và giữ lựa chọn sau sửa tiếp; bàn giao M2, ảnh M2, tour bỏ qua/phát lại và tiến độ |
| Kích thước | Ca mới kiểm tra 1440/390/320px, không tràn trang; các suite kế thừa giữ desktop/mobile và bàn phím. Đã xem ảnh QA desktop và mobile |
| Bảo toàn phạm vi | Hash bảy file được bảo vệ khớp trước/sau: plan M3 UI/M3, prototype và bốn tài liệu local đang sửa từ trước. Không chỉnh backend, prompt/model, plan, roadmap hoặc prototype |

Lượt triển khai ban đầu có chín bộ browser đạt: `screenplay-context`, `screenplay-layout`, `screenplay-continuous`, `screenplay`, `screenplay-writing`, `screenplay-feedback`, `screenplay-selection`, `scene-handoff`, `scene-sketch` (hậu tố `.browser.cjs`). Mỗi bộ dùng fixture mới. Sau đó chạy riêng lại ca context để bổ sung kiểm tra round-trip khi gõ trước frame điều hướng và ảnh chụp đúng vùng M3; đạt.

**Review cuối:** mười bộ Chrome của cùng bản code cuối đều đạt, gồm thêm `screenplay-focus.browser.cjs` với hai tình huống focus nêu dưới. Typecheck/build, sáu contract và 76 test backend cũng đạt; không còn lỗi chặn đã tái hiện.

Trong bộ context, chỉ có **2 yêu cầu ảnh giả** được tạo chủ động khi chuẩn bị dữ liệu; không có yêu cầu viết thử/review hoặc provider văn bản do điều hướng/thu gọn. Các bộ viết thử/review dùng provider giả riêng để kiểm tra thao tác AI; không phải kết quả chất lượng model.

### Review cuối — nguyên nhân editor và sửa focus

Lượt ban đầu lỗi ở `screenplay-continuous` vì sau lưu không có `blocks[0]`. Đọc lại **SQLite QA của chính lượt lỗi** cho thấy `heading` là `Lá thư  Cha đặt thư.  Con gái nhìn 🙂.  `, còn `blocks` rỗng. Đây là đoạn định nhập vào hành động bị chèn sang tiêu đề; xuống dòng bị loại theo hành vi của input một dòng. Không phải backend nhận khối hành động rồi tự bỏ đi.

Đã làm đối chứng có kiểm soát: giữ nguyên bước 3, chỉ tạm bỏ điều kiện chống giành focus trong callback điều hướng. Ca mới giữ đúng frame của editor, focus ô hành động rồi cho callback chạy trước khi chèn văn bản. Kết quả **đỏ đúng assertion**: focus `TEXTAREA → INPUT`, nội dung UI/payload PUT/bản server đều nằm trong tiêu đề, `blocks=[]`, cùng dạng dữ liệu với lỗi ban đầu. Bản đối chứng tạm đã được loại khỏi code bàn giao.

Review còn phát hiện bảo vệ trước đó chỉ kiểm tra vùng tác giả, nên vẫn giành focus nếu người dùng bắt đầu gõ yêu cầu viết thử trong phần hỗ trợ. Ca kiểm tra này cũng đỏ trước sửa. Sửa nhỏ cuối cùng ghi lại phần tử đang focus lúc yêu cầu chọn cảnh; callback chỉ focus tiêu đề nếu người dùng chưa chuyển focus sang nơi khác. Không đổi dữ liệu, API, schema hoặc thuật toán editor.

`screenplay-focus.browser.cjs` trên bản cuối xác nhận cả ô hành động và ô yêu cầu hỗ trợ giữ đúng nội dung; tiêu đề không bị sửa. Nội dung hành động khớp ở UI → payload PUT → server → reload, giữ nguồn và ID; nhập yêu cầu hỗ trợ không lưu hoặc gọi model. Frame giả dùng ID âm, tách khỏi ID frame native, và chờ đúng callback editor để tránh một phép thử vô tình hủy callback cần kiểm tra.

Bằng chứng [đối chiếu focus trước/sau](assets/m3-context-tools/editor-focus-comparison.json) giữ trạng thái UI, payload, server, nguồn và số request trên các fixture tổng hợp. Đây là tái hiện có kiểm soát cùng cơ chế lỗi và đối chiếu DB ban đầu; không tuyên bố đã ghi được event trace của chính lượt lỗi ban đầu.

Review theo luồng sử dụng local: `page.tsx` → editor/buffer → nguồn ảnh/feedback → lưu/khôi phục/đọc/chọn M4. Không phát hiện lỗi chặn còn lại sau sửa và kiểm chứng cuối. Không thêm dependency, provider hoặc đường ghi mới.

Chưa thử IME hệ điều hành/clipboard thật, screen reader, Safari/Firefox hoặc thiết bị thật. Đây là kiểm tra tập trung cho bước 3; chưa thực hiện bước 4 hồi quy/bàn giao tổng thể. Không xác nhận critic tốt hơn, người mới đã dùng dễ hơn hoặc nghiệm thu #7/#22/#26 đã đạt.

## Bằng chứng và cách chạy

- [Desktop: nguồn M3 và ảnh M2 khớp snapshot](assets/m3-context-tools/desktop.png). Ảnh trắng là PNG của provider giả, không phải ảnh model thật hoặc phác họa tác giả.
- [Mobile: ảnh khác nguồn/asset lỗi vẫn viết và lưu](assets/m3-context-tools/mobile.png).
- Cách chạy fixture/build/compiler theo [bước 1](m3-continuous-editor.md); biên dịch thêm `app/screenplaySketches.ts`, chạy `screenplay-sketch-contract.cjs` với thư mục JS đầu ra giống các contract hiện có. Browser mới: `frontend/tests/screenplay-context.browser.cjs`; dùng cùng fixture `backend/tests/ui_workspace_fixture.py` và biến `FIRSTFRAME_QA_DIRECTORY`, không dùng dữ liệu production.

Phần đóng gói chỉ gồm code/test/báo cáo và bằng chứng bước 3. Các thay đổi/tệp local có sẵn ngoài phạm vi vẫn để nguyên và không đưa vào commit/PR; plan, roadmap và prototype không thay đổi. Chưa triển khai bước 4 hoặc chạy thêm model thật.
