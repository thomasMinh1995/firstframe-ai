# Kiểm thử UI workspace đã chốt — 24/10/2026

## Kết quả

- Chạy lại backend trước khi commit: **307 passed, 1 skipped**, một cảnh báo deprecation của Starlette/httpx.
- Chạy lại TypeScript `tsc --noEmit` và các checks render/state cho editor/card buffer, quote anchors, progress/stream và onboarding: qua.
- Production build **QHn42rLerf4dwDFX3K1fb** đã qua. 31 file app khớp SHA-256 với source đã chạy ma trận UI; đóng gói PR không đổi runtime sau lượt kiểm chứng đó.
- Source và tài liệu qua whitespace check.

| Engine | Buffer/dữ liệu | UI/chuyển bước | Hội thoại/xác nhận/tiến trình | Tổng |
| --- | --- | --- | --- | --- |
| Chrome 155.0.8059.86 | 27/27 | 4/4 | 2/2 | 33/33 |
| Firefox 151.0 | 27/27 | 4/4 | 2/2 | 33/33 |
| WebKit 26.5 | 27/27 | 4/4 | 2/2 | 33/33 |

**99/99 ca UI qua**, profile và dữ liệu QA tạm, request mock. Các suite nằm trong `frontend/tests/story-workspace.browser.cjs`, `workspace-focus.browser.cjs`, `workspace-dialogue.browser.cjs`. Báo cáo công khai chỉ giữ [số liệu tổng hợp và hash source](assets/approved-story-workspace-matrix.json).

## Phạm vi đã kiểm tra

- Gõ/chỉnh sửa/hủy/lưu card, giữ buffer chưa lưu, lỗi lưu, rời trang, JSON, đề xuất, khôi phục lịch sử và xung đột revision hai tab.
- Hỏi tiếp giữ thứ tự/câu trả lời cũ; xem lại chưa gọi plan; sửa sau xem lại làm mất hiệu lực xác nhận; plan nhận câu trả lời mới nhất sau khi Đồng ý.
- Ba nhóm/tám bước con hiện chờ, chạy, xong theo sự kiện thực tế; giữ lỗi, checkpoint, bước chưa chạy và audit thử lại.
- Thu gọn/mở vùng, focus và thanh bước sau tạo plan, kể cả draft ngắn không cuộn tới vạch theo dõi; desktop/mobile không tràn ngang.
- Nguồn góp ý Việt/Anh khớp nguyên văn, nguồn giả bị từ chối, fallback góp ý legacy và nhãn góp ý thuộc bản trước.

Backend bổ sung kiểm tra nhiều lượt làm rõ, provider lỗi, stale revision, giới hạn 20 câu và tương thích analyze cũ. Lượt đầu thiếu import progress helper đã được sửa trước khi chạy lại toàn bộ. Assertion UI bổ sung bắt lỗi thanh bước sau tạo draft ngắn; bản cuối đã sửa và chạy lại cả 99 ca.

## Demo và giới hạn

Demo dùng API/SQLite/dataset và sự kiện xử lý thật với provider **ui-demo / fake-model**, output QA cố định: ý tưởng ngắn → sáu câu → hỏi thêm thành chín → sửa câu cũ → xem lại → Đồng ý → tám bước con → sáu card chữ S. Snapshot trước Đồng ý chưa có draft/plan; sau Đồng ý, context tạo plan dùng đúng câu trả lời mới nhất.

Ba ảnh được rà soát chỉ chứa truyện QA “Bát cơm trước cửa” và giao diện:

- [FirstFrame xin đồng ý](assets/workspace-dialogue-consent-2026-10-24.png).
- [Tiến trình đang chạy](assets/workspace-dialogue-progress-2026-10-24.png).
- [Story plan chữ S](assets/workspace-dialogue-story-plan-2026-10-24.png).

Không dùng demo QA để kết luận chất lượng model. Qwen3 trước đó còn sai ràng buộc/timeout; không chạy lại model trong lượt đóng gói PR. Chưa chạy lại bộ onboarding browser dài trong đợt UI cuối; onboarding state và tour trong suite story đã được kiểm tra. Thiết bị thật, accessibility với IME/bàn phím ảo và pilot người dùng mới vẫn cần nghiệm thu. Tiến trình thuộc lượt chạy hiện tại, không dựng lại khi reload.

Log terminal, patch thí nghiệm, output model và snapshot dự án thô được giữ local; không nằm trong PR công khai này. Dàn cảnh/Kịch bản để chốt UI riêng theo [phạm vi đã chốt](../plans/approved-story-workspace.md).
