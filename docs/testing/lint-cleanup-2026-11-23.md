# Dọn lint trước PR 2 — 23/11/2026

Baseline: `origin/dev` 3453fae33d0e4e6870d04deb724d066f886e00fe, sau PR #100.
Nhánh `codex/ff-sb-01-lint-cleanup`; issue #101; PR vào dev và squash.

## Đỏ → xanh
- Trên dev, `pnpm lint --max-warnings=0` exit 1: 20 warning và next lint deprecated.
- `hooks-lint-regression.cjs`: hai assertion thất bại trên source dev; cùng assertion qua sau sửa.
- Ca 1: wheel phải gọi callback mới sau rerender; ca 2: mở góp ý phải chọn cảnh hiện tại khi script giữ cùng ID.
- Dependency hooks được sửa tại nguồn; callback polling/flush ổn định, không tắt rule hay thay assertion cũ.
- ESLint CLI dùng cùng next/core-web-vitals; `--max-warnings=0` bắt warning trong CI.
- Clean build còn 2 warning autoprefixer tại flex headers: đổi align-items start thành flex-start; giữ start trong các grid.
- next/image dùng unoptimized, kích thước 768×432 và fallback lỗi; URL ảnh local tải trực tiếp.

## Kiểm chứng
- Clone sạch trong /private/tmp; không có .env và không nạp env từ workspace chính.
- `pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check`: PASS; 27 frontend suites.
- Production build riêng với NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8034 để kiểm tra browser.
- `lint-ui-regression.browser.cjs`: lưu SQLite thật trong thư mục tạm, buffer tiếng Việt, mở góp ý, ảnh/fallback, Escape của hướng dẫn, polling không khởi động lại khi rerender, preview thư viện ở 1440/390/320px.
- Dùng ui_workspace_fixture.py với PYTHON_DOTENV_DISABLED=1, provider giả; Playwright cài ngoài repo. Không gọi model thật.

## Giới hạn đã quan sát
Ba browser suite cũ timeout ở selector không còn phù hợp: onboarding chờ Bước 1/7 thay vì 6 bước; saved-library chờ nút Dự án mới đang nằm trong phần thu gọn; screenplay-context chờ scene list trước khi chuyển sang Viết & sửa.
Không đổi kỳ vọng những suite này. Ca browser mới đi qua điều hướng hiện tại và kiểm tra trực tiếp các hành vi vừa sửa; chưa chạy Safari/Firefox.
Backend không đổi trong PR này; CI vẫn chạy toàn bộ pytest.

## Chạy browser lại
Khởi động backend/tests/ui_workspace_fixture.py bằng Python environment riêng và PYTHON_DOTENV_DISABLED=1; lấy directory được in ra.
Build/start frontend tại :3034 với API base :8034; không dùng .env.
Chạy `NODE_PATH=<thư mục Playwright>/node_modules FIRSTFRAME_QA_DIRECTORY=<directory> node frontend/tests/lint-ui-regression.browser.cjs`.
