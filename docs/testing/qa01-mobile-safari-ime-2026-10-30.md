# QA-01: mobile, Safari, bàn phím và khả năng tiếp cận

Ngày: 2026-10-30. Nhánh: `fix/mobile-safari-ime-accessibility`, từ `dev` tại `0301e85`.

**Kết luận:** sửa lỗi mất buffer khi đổi breakpoint, sheet mobile tự mở và nút đóng che nội dung. Bổ sung bảo vệ phím IME ở editor, review và onboarding. Đây là nghiệm thu kỹ thuật trong phạm vi dưới đây; **QA-01 toàn sản phẩm vẫn mở**.

## Môi trường và dữ liệu

- Safari native trên macOS, Responsive Design Mode tại 320×844, 390×844 và 1200×844. Menu Develop hiển thị môi trường 26.6.2. RDM là viewport desktop Safari, không phải Safari iOS hoặc thiết bị cảm ứng thật.
- Tab in-app browser riêng dùng để đọc DOM và đo kích thước tại 320×844. Các phép đo DOM bên dưới không được gán cho Safari native.
- Frontend QA cổng 3035, API cổng 8035. Tái sử dụng `backend/tests/ui_workspace_fixture.py`, bọc CORS chỉ cho origin QA. Fixture tạo SQLite/dataset trong thư mục tạm, dùng provider giả. Không sửa dữ liệu ứng dụng chính, không gọi Ollama.
- Project synthetic `QA Safari · IME · bàn phím`: hai cảnh `Lá thư chưa mở`, `Khoảng lặng`; cảnh đầu có hành động và thoại của `Con gái`. Chỉ thao tác dữ liệu fixture.
- CUA dùng cho toàn bộ thao tác UI; đối chiếu kết quả autosave bằng GET API fixture. Không chạy lại bộ brief Qwen trong đợt UI này.

## Lỗi và thay đổi

| Lỗi | Tái hiện trước sửa | Thay đổi |
| --- | --- | --- |
| Mất yêu cầu sửa chưa gửi | 390px → mở `Đề xuất sửa với AI` → nhập buffer → 1200px. Mở lại disclosure thấy textarea rỗng | Giữ một native `dialog` và cùng cây children qua breakpoint; desktop mở non-modal, mobile dùng `showModal()`. Bỏ chuyển children giữa portal và aside |
| Mobile tự bật modal | Khởi tạo ở desktop → đổi 390px → chọn cảnh. Modal bật dù chưa nhấn nút hỗ trợ | Theo dõi media query ở `ScreenplayEditor`, đóng hỗ trợ khi chuyển sang mobile; giữ children/buffer đã mount |
| Nút đóng che nội dung hoặc cuộn mất | 320px, mở disclosure rồi focus textarea phía dưới | Nút đóng nằm ngoài vùng cuộn; dùng một `div` cuộn bao quanh fieldset. Thử chỉ cho fieldset cuộn vẫn làm dialog cuộn trên WebKit, nên không dùng fieldset làm scroll host |
| Thiếu bảo vệ phím xác nhận IME | Một số handler chỉ đọc `isComposing`, không nhận fallback 229 của Safari | Dùng chung `isComposingKey` cho native/React event, cả `keyCode` ngoài và `nativeEvent`. Áp dụng cho Enter/Backspace editor, Enter người nói, Escape sửa story plan/onboarding/review và tablist dàn cảnh |

Review còn chặn Escape khi đang composition, desktop Escape đóng panel và trigger công bố `aria-expanded`/`aria-haspopup`. Onboarding chỉ coi `dialog:modal` là modal đang chặn Escape, vì panel desktop nay cũng là dialog mở non-modal.

## Kết quả đã quan sát

| Ca | Kết quả và bằng chứng |
| --- | --- |
| Desktop → 390px → chọn cảnh | Pass trên Safari: editor mở, không tự bật sheet; nút hỗ trợ vẫn mở sheet khi chủ động nhấn |
| Buffer qua breakpoint | Pass trên Safari: `BUFFER SAFARI 390 RESIZE — giữ nguyên lời thoại` giữ nguyên ở 390→1200px; sau thay đổi vùng cuộn, lặp 320→1200px với `BUFFER FINAL — giữ lời thoại`, disclosure vẫn mở và textarea giữ chữ |
| Đóng/mở lại | Pass trên Safari: Escape desktop trả focus về `Dàn cảnh & góp ý`; chuyển 320px và mở lại vẫn giữ buffer. Escape mobile cũng trả focus về trigger |
| Focus mobile | Safari AX chỉ hiện nội dung modal khi mở, focus ban đầu ở nút đóng. Thử Option+Shift+Tab/Option+Tab: focus ở dialog/nút đóng, không sang nội dung nền. Đây là kiểm tra bàn phím/AX giới hạn, chưa phải nghiệm thu toàn bộ thứ tự đọc bằng screen reader |
| Cuộn và nhập cuối sheet | Pass quan sát Safari native 320px: nút đóng vẫn hiển thị, textarea đang focus không bị nút che. DOM in-app browser: dialog `scrollTop=0`, body cuộn `31.5`; nút đóng cao 44px, bottom≈139px; textarea top≈444px, bottom≈524px |
| Tràn ngang và font nhập | DOM in-app browser 320px: `documentElement.scrollWidth=320`; dialog nằm x=19..301, content không tràn ngang. Heading, hành động, người nói, lời thoại và textarea yêu cầu sửa đều có font 16px, trường nhập có nhãn |
| Bàn phím editor | Pass trên Safari: Shift+Enter giữ xuống dòng trong hành động, Enter tạo đoạn mới và focus đoạn đó, Backspace ở đoạn rỗng gộp về đoạn trước |
| Tiếng Việt và autosave | Pass Unicode **paste** trên Safari. API lưu nguyên `Cha đặt phong thư kín lên bàn. Tiếng Việt: ngỡ ngàng, giữ lời hứa.\nCon gái kéo ghế, ngồi xuống.`, vẫn hai khối, người nói `Con gái` và thoại cũ giữ nguyên, screenplay version 5. Provider stages vẫn rỗng |
| IME logic | Unit mới kiểm tra native/React `isComposing`, Safari `isComposing=false,keyCode=229`, fallback từ `nativeEvent`, cùng Enter/Escape thường. Các suite autosave/candidate hiện có tiếp tục kiểm tra hoãn lưu khi composition và Unicode |

Để lặp thủ công: chạy API fixture với DB tạm và frontend trỏ đúng origin QA; dùng project hai cảnh đã có screenplay. Thay viewport qua thanh RDM, không reload giữa các bước buffer. Mở form hỗ trợ, nhập yêu cầu chưa gửi, đổi breakpoint rồi kiểm tra chính textarea. Sau đó đóng/mở, dùng Escape, thử Enter/Shift+Enter/Backspace trong editor và đối chiếu GET project sau autosave. Không dùng thao tác `typeText` Unicode như bằng chứng IME: công cụ native có thể bỏ dấu; paste chỉ chứng minh đường Unicode/DOM/lưu.

## Hồi quy

- `cd frontend && npm run typecheck`: pass.
- `cd frontend && npm test`: 19 suite pass, gồm `input-events.cjs`, autosave, candidate, editor split/merge, Unicode và hợp đồng review/PDF.
- `cd frontend && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8035 npm run build`: pass. Có hai cảnh báo Autoprefixer có sẵn về `align-items:start` trong `storyWorkspace.css`/`savedLibrary.css`; không có lỗi compile/type.
- `cd backend && python -m pytest -q`: 831 passed, 1 skipped; một cảnh báo deprecation Starlette/httpx có sẵn.
- Smoke bản production (`next start`): tab in-app browser 320→1200px giữ nguyên `PRODUCTION BUFFER — giữ thoại`; desktop dialog non-modal vẫn mở, Escape đóng và trả focus về trigger (`aria-expanded=false`).

## Review cuối PR #87

Phát hiện và sửa thêm một lỗi chặn trên mobile: dialog inline mới kế thừa `disabled` từ `.project-fields` khi `busy`, nên nút đóng bên ngoài fieldset riêng của dialog vẫn bị disable. Tái hiện trên bản production bằng giữ request `/screenplay-reviews/stream`: dialog là modal nhưng nút Close khớp `:disabled`, ancestor là `.project-fields`.

Đổi khóa workspace sang `inert` + `aria-busy`. Modal native thoát inert của ancestor; fieldset riêng của review tiếp tục khóa nội dung, nút đóng dùng được. Truyền trạng thái busy cho cả inspector story plan để modal đó cũng không bật lại thao tác sửa. Cơ chế này theo [HTML Standard về modal và inert](https://html.spec.whatwg.org/multipage/interaction.html#modal-dialogs-and-inert-subtrees). Trong lúc busy, nội dung workspace tạm không nằm trong luồng tương tác/đọc; vùng tiến trình bên ngoài vẫn truy cập được. Sau khi đóng mobile sheet, nếu workspace còn inert thì chuyển focus sang tiến trình ở frame tiếp theo, sau native dialog focus restoration.

Đã kiểm tra bản sửa qua CUA:

- In-app browser 390px: `aria-busy=true`, workspace có `inert`, fieldset dialog disabled, Close không disabled; bấm Close đóng modal trong khi request vẫn giữ. Bấm editor không chuyển focus vào vùng inert, nội dung `Lá thư` giữ nguyên.
- Safari native/RDM 390px: các nút nhận/kiểm tra góp ý và đánh giá đều disabled, Close vẫn hoạt động. Bấm Close khi AI đang chờ đưa focus về `Tiến trình xử lý`; Option+Tab tiếp tục tại nút `Chuẩn bị cảnh và dẫn chứng`.
- Release request: các lượt review hoàn tất có trạng thái `ready`, văn bản `Cha đặt thư kín lên bàn.` giữ nguyên. Đóng sheet không thêm POST và không hủy request. Một lượt cố ý giữ quá 45 giây làm transport timeout; UI giữ nguồn, không retry; đối chiếu/mở lại vẫn lấy kết quả server đã lưu.
- Thêm hồi quy SSR cho inspector story plan busy/idle: fieldset khóa đúng trạng thái, Close nằm ngoài phần disabled; cập nhật các browser scenario cũ dùng trạng thái `inert` thay `.disabled`. Các file `.browser.cjs` không được chạy bằng runner ngoài CUA trong đợt này; ca UI tương ứng được thao tác qua CUA như mô tả trên.

## Gate còn mở (giữ nguyên)

Chưa nghiệm thu iPhone/iPad/Android thật, bàn phím ảo và visual viewport khi mở bàn phím, xoay thiết bị thật, bộ gõ Telex/VNI hoặc CJK có candidate thật, VoiceOver/NVDA đọc toàn luồng và các chế độ OS giảm chuyển động/transparency/forced-colors. Develop không có thiết bị inspectable và đề nghị cài Xcode cho Simulator. Thử shortcut nguồn nhập/VoiceOver không cung cấp bằng chứng composition hoặc màn đọc xác thực; không tính là pass. Không cài thêm hoặc cấp quyền input monitoring/accessibility cho bộ gõ.

Chưa chứng nhận WCAG toàn sản phẩm từ vài phép đo DOM/AX. Không đổi cờ rollout UI và không đóng QA-01 dựa trên các ca kỹ thuật này. Cần bổ sung phiên kiểm thử thiết bị, IME và assistive technology trước khi chốt gate tương ứng.

Tham khảo hành vi nền tảng: [IME-safe Enter của Chrome](https://developer.chrome.com/docs/modern-web-guidance/guides/forms/ime-safe-enter-submit) và [WebKit #165004](https://bugs.webkit.org/show_bug.cgi?id=165004) giải thích fallback 229; [W3C native dialog H102](https://w3c.github.io/wcag/techniques/html/H102.html) mô tả focus và Escape của modal native. Các nguồn này hướng dẫn cách sửa, không thay bằng chứng chạy thực tế.
