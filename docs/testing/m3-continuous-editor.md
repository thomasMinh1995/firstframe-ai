# M3 UI bước 1 — Kiểm chứng editor liền mạch

Ngày 27/10/2026. Nhánh `feat/m3-continuous-editor`, từ `dev` tại `d0561b5` sau PR #57. Phạm vi là lát cắt editor một cảnh theo [plan đã merge](../plans/m3-ui-simplification.md), chưa triển khai bước 2 (danh sách cảnh thẳng và bản lưu song song).

## Thay đổi

- Editor hiện có vẫn là mặc định. Tác giả bấm **Thử editor liền mạch cho cảnh này**, có thể quay lại editor cũ mà không lưu/gọi AI hoặc mất buffer. Chỉ cảnh được chọn thử dùng editor mới; form chỉnh phương án AI vẫn dùng `ScriptSceneFields` hiện có.
- Vùng viết dùng input/textarea gọn trên một trang, không `contenteditable`, không parse lại cả cảnh và không thêm dependency. Enter tách đoạn hành động; dòng người nói và phần thoại dùng cùng một khối dialogue có ID ổn định. Enter ở người nói chuyển tới thoại, Enter ở thoại sang hành động; Shift+Enter giữ xuống dòng trong đoạn, Tab giữ điều hướng bàn phím.
- Tên người nói là `speaker`, không thêm loại `character` vào API. Không tự suy đoán người nói hoặc lấy diễn tiến M2 làm văn kịch bản. Paste-like multiline insertion giữ nguyên text, không thực thi HTML.
- Menu đoạn giữ đổi thứ tự/xóa/gộp. Chỉ gộp cùng loại và cùng người nói, giữ ID đoạn trước; khác loại/người nói bị từ chối thay vì bỏ dữ liệu. Tách giữ ID phần trước, phần mới có UUID mới. Ô nhập tạm không tạo dữ liệu chỉ vì mở editor; ID đã xóa không được dùng lại khi gõ vào ô trống mới.
- Đổi dialogue sang action khi có người nói cần xác nhận rõ việc bỏ trường người nói; giữ text và có hoàn tác ngay. Hoàn tác thao tác cấu trúc chỉ hiện khi scope bản kịch bản và nội dung cảnh còn khớp sau thao tác; sửa tiếp hoặc lưu sang phiên bản khác không bị hoàn tác cũ ghi đè.
- Bản viết dở vẫn lưu được, kể cả thoại chưa đủ hoặc khối còn trống. Giới hạn số khối/cảnh/toàn bản và độ dài tiếp tục áp dụng; backend/API/snapshot/CAS không thay đổi. Điều hướng quote dùng field/ID hiện có, không gắn lại theo vị trí hoặc tên.

## Kết quả kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| TypeScript `--noEmit --incremental false` | Đạt |
| Build production với API QA và build lại cấu hình mặc định sau QA | Đạt; không đổi `.env` |
| Node contract editor mới | Đạt: tách/gộp exact Unicode và khoảng trắng, ID ổn định, không mutate buffer, thoại/người nói, gộp không tương thích bị từ chối, khối dở và giới hạn |
| Node contract M3 hiện có | Cả ba bộ screenplay/review/selection đạt: whitelist, nguồn/quote, legacy, snapshot bản đọc và lựa chọn M4 |
| Backend M3 liên quan | **59 passed**, 7,27 giây: `test_screenplays.py`, `test_screenplay_review.py`, `test_screenplay_selection.py` |
| Chrome editor mới | Đạt trên SQLite/API tạm: opt-in không ghi, text/ID/source round-trip, Enter/Shift+Enter, tách/gộp/hoàn tác, IME mô phỏng, text nhiều dòng/HTML dạng chữ, người nói → thoại, lưu khối trống, xác nhận chuyển loại, đổi thứ tự/xóa, không dùng lại ID, sửa mới làm mất hiệu lực undo cũ, đổi cảnh giữ buffer, reload và focus bằng chứng qua provider giả |
| Chrome lỗi lưu | Mất mạng và revision 409 giữ buffer mới, bản server không bị đè; góp ý cũ không có liên kết vào bản đang sửa |
| Chrome hồi quy M3 | Bốn bộ `screenplay.browser.cjs`, `screenplay-writing.browser.cjs`, `screenplay-feedback.browser.cjs`, `screenplay-selection.browser.cjs` đều đạt trên fixture mới riêng cho từng bộ |
| Bàn phím và viewport | Tab vẫn tới control kế tiếp; 1280/390/320px không tràn trang. Đã xem ảnh editor thực tế từ QA; đây không phải kiểm tra thiết bị thật |
| Phạm vi | Hash plan M3, plan UI, prototype và bốn tài liệu local ngoài phạm vi giữ nguyên; không thay backend, provider, prompt, model hoặc schema |

Chrome editor mới có đúng một lượt review qua **provider giả** để kiểm tra liên kết nguồn; không có lượt viết thử hoặc tạo ảnh. Các bộ hồi quy AI cũng chỉ dùng provider giả. Không chạy model thật, API trả phí hoặc mở DB tác giả. Mỗi bộ browser dùng `ui_workspace_fixture.py`, DB/profile riêng và có kiểm tra request/state.

Lượt browser đầu dừng khi test bấm nút xóa trong menu vừa được dựng lại ở trạng thái đóng sau hoàn tác. Đã sửa test mở đúng menu trước thao tác, không đổi kỳ vọng dữ liệu để lấy kết quả đạt. Review đồng thời phát hiện placeholder có thể dùng lại ID sau xóa hết; đã sửa quay vòng ID và thêm ca kiểm tra xóa rồi viết lại. Sau sửa, cả năm bộ browser đạt; bộ editor chạy thêm một lượt trên fixture mới để kiểm tra Tab và chụp ảnh editor. Log các lượt lỗi và đạt giữ local tại `/tmp/firstframe-continuous-*` và các thư mục `firstframe-workspace-*` tương ứng.

Lần biên dịch CJS đầu dùng thiếu lib cho `findLastIndex` và thiếu module render bản đọc; đã sửa lệnh build contract trước khi chạy đủ bốn bộ thành công. Đây là lỗi cấu hình lệnh kiểm chứng, không phải kết quả contract đạt của lượt lỗi. Backend còn cảnh báo Starlette/httpx deprecated hiện có, không sửa ngoài phạm vi.

## Chạy lại

1. Từ `frontend`, chạy TypeScript và production build; khi QA dùng `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8034`.
2. Biên dịch CJS tới thư mục tạm, dùng `--module commonjs --moduleResolution node --target ES2022 --lib esnext,dom --jsx react-jsx --esModuleInterop --skipLibCheck`, gồm `screenplayEditing.ts`, `projectsApi.ts`, `screenplayReviewTypes.ts`, `ScreenplayReading.tsx`. Chạy `screenplay-editing-contract.cjs` và ba contract M3 cũ với đường dẫn output; module React cần có trong `NODE_PATH` khi output nằm ngoài frontend.
3. Từ `backend`, chạy `.venv/bin/python -m pytest -q tests/test_screenplays.py tests/test_screenplay_review.py tests/test_screenplay_selection.py`.
4. Mỗi bộ browser khởi động **fixture mới** bằng `.venv/bin/python tests/ui_workspace_fixture.py`, lấy `directory` từ stdout. Chạy frontend QA tại 3034, rồi `FIRSTFRAME_QA_DIRECTORY=<directory> NODE_PATH=<Playwright packages> node frontend/tests/screenplay-continuous.browser.cjs` từ repo root. Bốn suite cũ chạy tương tự, mỗi suite có fixture mới; không dùng DB tác giả hoặc model thật.
5. Dừng các server QA đã tạo và build lại với cấu hình API mặc định.

## Review và giới hạn

Review đường gọi `ScreenplayEditor` → editor mới → callback buffer cấp dự án → API hiện có, giữ nguyên snapshot, revision/409, dữ liệu dự án khác và nguồn M4. Form phương án không chuyển sang editor mới trong bước 1; regression xác nhận chỉnh phương án riêng, dùng/bỏ/hoàn tác và lỗi provider không đổi bản tác giả ngoài lựa chọn hiện có. Không còn lỗi chặn kỹ thuật đã biết trong lát cắt kiểm chứng này.

Chưa mặc định thay editor toàn M3; chưa đổi bố cục, danh sách cảnh, cột bản lưu, ảnh hoặc tour theo bước 2–3. Editor là các trường nhập có định danh trình bày liền nhau, chưa hỗ trợ một selection xuyên qua nhiều khối độc lập như phần mềm chế bản. Dán nhiều đoạn giữ xuống dòng trong cùng khối, không tự chia/suy đoán thoại. Không tuyên bố đã có editor chuyên dụng hoặc người mới dùng dễ hơn.

IME mới kiểm tra bằng composition/keydown mô phỏng; multiline insertion dùng nhập native có kiểm soát, chưa thử IME hệ điều hành/clipboard thực, screen reader hoặc điện thoại thật. Chưa chạy Safari/Firefox. Chất lượng critic và nghiệm thu người dùng vẫn mở, không thay tiêu chí #7/#22/#26. Bước này không chạy thêm prompt/model, không triển khai M4 và không sửa plan/prototype.

## Review cuối PR #58

Phát hiện và sửa ca CRLF trước merge: textarea hiển thị `\r\n` thành `\n`, nên dùng thẳng offset con trỏ để cắt chuỗi nguồn có thể xóa sai ký tự khi chọn một đoạn sau xuống dòng. Editor nay ánh xạ offset hiển thị sang chuỗi nguồn, không chuẩn hóa text gốc; vị trí con trỏ sau gộp cũng tính theo giá trị hiển thị.

Đã thêm contract và ca Chrome nhập fixture có `A\r\nBC\r\nD`: chọn đúng `BC`, Enter tách/xóa đúng phần đã chọn, lưu giữ các CRLF còn lại; gộp giữ nguyên chuỗi và đặt con trỏ đúng ranh giới. Bốn contract và toàn bộ bộ Chrome editor chạy lại đạt trên fixture mới, bao gồm các ca bảo vệ đã có. Build QA và build lại cấu hình mặc định đạt. Bốn suite Chrome hồi quy M3 cùng 59 test backend ở trên là bằng chứng trước sửa; backend và đường editor cũ không đổi, không chạy lại các suite đó. Không còn lỗi chặn đã biết trong phạm vi bước 1; các giới hạn kiểm chứng nêu trên vẫn giữ.
