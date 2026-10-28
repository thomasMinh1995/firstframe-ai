# M3 UI bước 4 — Hồi quy và bàn giao kỹ thuật

Kiểm chứng ngày 27/10/2026; review đóng gói ngày 28/10/2026. Nhánh `feat/m3-ui-regression-handoff`, từ `dev` tại `e4e26bf` sau PR #60. Theo bước 4 của [plan PR #57](../plans/m3-ui-simplification.md).

**Kết luận:** không phát hiện lỗi chặn do UI mới trong phạm vi Chrome/Firefox đã kiểm chứng. Đủ bằng chứng bàn giao kỹ thuật cho các đường viết/lưu/đối chiếu và thao tác M3 hiện có; các giới hạn nền tảng/thao tác thật bên dưới vẫn mở. Không coi đây là nghiệm thu người dùng, chất lượng critic hoặc toàn bộ ma trận thiết bị.

## Phạm vi thay đổi

Chỉ bổ sung test và bằng chứng, không sửa runtime. Ca tích hợp mới `frontend/tests/screenplay-handoff.browser.cjs` đi qua một hành trình liên tục, dùng editor liền mạch và bàn phím. Fixture/provider giả được bổ sung chế độ trả ba dẫn chứng **text/heading/speaker** trong cùng một nhận xét có đủ nguồn text bắt buộc; không nới validation, không đưa chế độ test vào ứng dụng thật. Thêm một test backend xác nhận các nguồn ấy hợp lệ và không sửa bản tác giả.

Không đổi plan, roadmap, prototype, schema/API, prompt/model hoặc provider runtime. Không tạo ảnh/model thật, không triển khai M4/xuất bản. Các tài liệu local đang sửa từ trước giữ ngoài phạm vi.

## Ma trận theo plan

| Nhóm | Bằng chứng đã chạy | Kết quả và giới hạn |
| --- | --- | --- |
| Round-trip/dữ liệu cũ | Ca tích hợp + `screenplay`, `screenplay-continuous`, contract và backend | Giữ tiếng Việt/NFD/emoji, khoảng trắng/xuống dòng, ID/order/kind/speaker, cảnh im lặng và nháp thiếu. Dự án chưa có M3 không tự tạo nội dung; client cũ bỏ trường M2/M3 vẫn không xóa artifact mới. Backend còn kiểm tra mở review cũ không đổi nguồn. Dùng fixture tổng hợp cùng schema cũ, không mở DB riêng của tác giả |
| Editor | Contract/editor browser + ca tích hợp bàn phím | Enter/Shift+Enter, đổi loại dòng, IME mô phỏng, Unicode/CRLF, xóa/gộp/tách/đổi thứ tự/hoàn tác và giới hạn khối. Literal HTML hiển thị như text, không thực thi. Chưa kiểm chứng IME hệ điều hành hoặc clipboard hệ thống thật |
| Hai vùng dữ liệu | `screenplay-layout`, ca tích hợp | A → B → A giữ buffer, bản lưu chỉ cập nhật khi nhận xác nhận; giữ PUT response, mất mạng/409, đổi project/script. Enter chọn cảnh chờ đúng scene ID; desktop hai cột, 390/320px xếp dọc |
| Nguồn/ảnh | `screenplay-context`, `scene-sketch` + helper contract | Hai cảnh trùng tên, M2 đổi thứ tự/nội dung, ảnh mới khác snapshot, thiếu asset/404 không ghép nhầm hoặc cản viết/lưu. Ảnh theo lựa chọn M2 đang lưu, không giả là ảnh bất biến của M3. Không tạo ảnh do điều hướng |
| AI/bằng chứng | Ca tích hợp + writing/feedback/focus browser | Chỉnh phương án riêng → dùng đúng cảnh → hoàn tác → bỏ; phương án chưa dùng không vào bản lưu. Dẫn chứng tới đúng action text, heading và dialogue speaker trong editor mới; đọc snapshot không ghi API. Sửa tay làm góp ý cũ mất liên kết vào bản hiện tại; review tiếp giữ nguồn cũ. Lỗi/timeout/mất response vẫn tự viết và lưu; không tự retry |
| Lịch sử/chọn nguồn M4 | Ca tích hợp + selection/manual browser | Chọn đúng bản đã đọc khi có buffer khác chưa lưu, không tự lưu buffer; lựa chọn bất biến sau lưu/khôi phục/client cũ. Đọc lịch sử và khôi phục giữ M1/M2/bản trước. Chỉ kiểm tra hợp đồng chọn nguồn M4 đã tồn tại, chưa xuất kịch bản |
| Truy cập/bố cục | Ca tích hợp Chrome và Firefox + layout/focus/tour | Chọn cảnh bằng focus/Enter, Tab/Shift+Tab native, summary thu gọn, focus không giành chỗ đang nhập. Ba viewport 1440/390/320px không tràn trang; thứ tự và hai vùng đúng breakpoint. Đây là viewport máy tính, không phải mobile thật/screen reader |
| Hồi quy/tour | 11 suite fixture Chrome + tour mock, backend và frontend checks | Giữ nguồn/buffer, checkpoint, lỗi và thông điệp HITL; tour sáu bước, storage/progress/bỏ qua/phát lại không đổi. Firefox chạy riêng ca tích hợp; không tuyên bố mọi suite đã chạy Firefox |

## Kết quả chạy

- **100 test backend đạt**, 6,58 giây: `test_screenplays`, `test_screenplay_writing`, `test_screenplay_review`, `test_screenplay_review_priority`, `test_screenplay_selection`, `test_scene_handoff`, `test_scene_sketches`. Một cảnh báo Starlette/httpx hiện hữu, không đổi dependency.
- **8 bộ frontend checks đạt**: sáu contract M3/editor/ảnh và hai bộ onboarding/progress. TypeScript `--noEmit --incremental false`, production build QA và build mặc định sau QA đạt.
- **12 bộ Chrome 156.0.8078.48 đạt:** 11 suite dùng fixture mới gồm `screenplay-handoff`, `screenplay-focus`, `screenplay-context`, `screenplay-layout`, `screenplay-continuous`, `screenplay`, `screenplay-writing`, `screenplay-feedback`, `screenplay-selection`, `scene-handoff`, `scene-sketch` (hậu tố `.browser.cjs`); thêm `onboarding.browser.cjs` dùng API mock hoàn toàn, gồm cả hồi quy bản đọc story plan/thẻ ý đồ.
- **Firefox 151.0:** ca `screenplay-handoff.browser.cjs` đạt cùng hành trình và ba viewport. Dùng binary đã có qua `FIRSTFRAME_QA_EXECUTABLE`; không cài engine hoặc dependency mới.
- **WebKit chưa kiểm chứng:** binary cache v2311 có sẵn không tương thích với công cụ Playwright hiện tại, báo `Page.overrideSetting: Unknown setting: PushAPIEnabled` khi tạo trang. Đã dừng tiến trình kiểm tra; không tính lỗi công cụ này là lỗi ứng dụng hoặc kết quả Safari đạt.
- **Ruff:** còn 6 chẩn đoán có sẵn trong hai file test (`I001`, `F811`, `F841`). Đối chiếu code/message với nội dung `dev` tại `e4e26bf` không có chẩn đoán mới. Không gọi lượt Ruff này là đạt và không sửa lan sang style/debt cũ.

Trong **mỗi ca tích hợp** Chrome/Firefox, chỉ có một lượt viết thử giả, hai lượt review giả và không có lượt ảnh/provider story-plan. Các thao tác mở/chuyển cảnh, đọc bằng chứng, nhập yêu cầu hỗ trợ, đọc lịch sử và chọn bản không tự gọi model. Đây là kiểm chứng hợp đồng và tương tác, không phải kết quả semantic của AI thật.

Các lỗi khi soạn test mới đã sửa trước lượt cuối: dùng nhầm tham số helper `speaker`; selector trùng tiêu đề và nội dung nguồn; nhấn Enter khi nút còn busy hoặc chưa commit lựa chọn; đo hai bounding box ở hai thời điểm khác nhau khi autofocus cuộn trang; lần compile progress đầu thiếu `OperationProgress.tsx`. Lượt cuối dùng chữ ký helper đúng, so nguyên văn trường nguồn, chờ nút enabled/scene ID và đo hai vùng trong cùng một lần đọc DOM. Không nới assertion nội dung/ID/nguồn, không cần sửa runtime để làm test qua.

Lỗi focus đã sửa ở [bước 3](m3-context-tools.md) tiếp tục qua ca hồi quy: cùng nguồn/tiêu đề/text, không giành focus từ editor hoặc form hỗ trợ. Chưa thấy tái hiện hành động bị ghi sang tiêu đề trên bản đã merge.

## Bằng chứng

- [Kết quả máy đọc, phiên bản trình duyệt và giới hạn](assets/m3-ui-handoff/results.json).
- [Chrome desktop — vùng viết và bản lưu](assets/m3-ui-handoff/chrome-desktop.png).
- [Chrome viewport mobile](assets/m3-ui-handoff/chrome-mobile.png).
- [Firefox viewport mobile](assets/m3-ui-handoff/firefox-mobile.png).

Ảnh/JSON chỉ chứa fixture tổng hợp. Chuỗi HTML trong bản viết là ca an toàn hiển thị text, không phải ảnh hoặc nội dung của tác giả. Prototype và bảy file được bảo vệ khớp hash trước/sau; diff `frontend/app`, `backend/app`, `domains` rỗng.

## Chạy lại

Dùng dependency hiện có, không thêm Playwright vào runtime. Tại `frontend/`, build với `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8034`, rồi start production tại `127.0.0.1:3034`. Ở terminal khác, chạy từ `backend/`:

```sh
.venv/bin/python tests/ui_workspace_fixture.py
```

Lấy `directory` từ JSON dòng đầu, đặt `FIRSTFRAME_QA_DIRECTORY` theo giá trị đó và `NODE_PATH` tới thư mục `node_modules` cung cấp Playwright ngoài repo; từ repo chạy:

```sh
node frontend/tests/screenplay-handoff.browser.cjs
```

Mỗi suite fixture phải khởi động lại fixture để có DB mới. Ca mới hỗ trợ `FIRSTFRAME_QA_BROWSER=firefox|webkit` và tùy chọn `FIRSTFRAME_QA_EXECUTABLE` tới binary phù hợp; mặc định dùng Chrome. Không lấy một engine không tương thích rồi ghi là ứng dụng lỗi/đạt. Tour dùng `TOUR_TEST_URL=http://127.0.0.1:3034`, `TOUR_SCREENSHOTS` riêng và API mock; không cần dữ liệu backend.

Biên dịch CJS giống [bước 1](m3-continuous-editor.md), thêm `screenplaySketches.ts`, `onboardingState.ts`, `progressState.ts`, `OperationProgress.tsx` cho đủ tám script checks. Backend chạy bảy file pytest nêu trên. Kết thúc dừng server QA tạo trong phiên và build lại cấu hình API mặc định; không sửa `.env`.

## Bàn giao và phần còn mở

- Bản bàn giao là UI M3 sau PR #58/#59/#60; bước này thêm bằng chứng và test hồi quy, chưa thay chức năng ứng dụng. Phần đóng gói chỉ gồm test, fixture QA và bằng chứng liên quan bước 4. Review ngày 28/10 đối chiếu log gốc, phạm vi và đường gọi; không phát hiện lỗi chặn trong phần thay đổi. Kết quả kiểm chứng giữ ngày chạy ban đầu, không coi review này là một đợt model hoặc nghiệm thu mới.
- Chưa có kiểm chứng IME hệ điều hành, clipboard thật, thiết bị/bàn phím ảo thật, screen reader hoặc full Safari. Phải ghi/chạy riêng trước khi tuyên bố nghiệm thu các mục đó; viewport và IME mô phỏng không thay thế. WebKit cần bộ công cụ/engine tương thích trước lượt kiểm tra khác.
- Chất lượng critic M3 và N1/N2/#7 vẫn chưa được xác nhận đạt. Quote đúng, kiểm tra nguồn đúng, test xanh hay thông điệp HITL đều không chứng minh góp ý hữu ích hoặc tác giả viết tốt hơn. Giữ nguyên các kết quả/tiêu chí #7/#22/#26 và không đóng issue.
- Chưa triển khai M4 hoặc kiểm chứng xuất bản. Theo thứ tự đã chốt, sau bàn giao M3 mới sang M4, kiểm chứng luồng hoàn chỉnh, deploy thử rồi trải nghiệm người dùng. Không tự thêm vòng prompt/model, embedding/judge hoặc biến việc đóng toàn bộ #22 thành điều kiện mới để bắt đầu M4.
