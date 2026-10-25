# Kiểm chứng kỹ thuật vòng sửa #7 — 25/10/2026

Triển khai theo PR #37, từ dev `60e5fa7`. Nhánh làm việc:
`codex/issue-7-feedback-targets`. Chưa nghiệm thu/đóng #7 và chưa mở H1–H8.

## Phần bổ sung

- Dùng lại `CardReview` cho plan mới trong project và review bản sửa. Giữ
  `observation` và `suggestion` trong cùng một ưu tiên, kèm nguồn tác giả,
  trích dẫn nguyên văn và ID mục tiêu. Giữ `findings` cho luồng đọc cũ.
- Truyền dữ liệu qua core artifact, API, project, proposal và lịch sử cùng
  `FeedbackSource` hiện có. Không thêm kho task hoặc di chuyển dữ liệu khi đọc.
- Kiểm tra artifact, câu hỏi/câu trả lời và toàn bộ mục tiêu trên snapshot.
  Một tham chiếu sai khiến cả mục chỉ đọc; không tìm gần đúng hoặc nhảy tới
  tham chiếu hợp lệ còn lại. Nhãn mục trùng tên có số card/mục để phân biệt.
- “Sửa phần này” chỉ mở/focus ô sửa. Với nhiều mục tiêu, tác giả chọn rõ phần
  cần sửa. Góp ý cạnh card vẫn hiện khi mở card từ ưu tiên. Không lưu/gọi AI,
  không áp dụng gợi ý, không đánh dấu vấn đề đã giải quyết.
- Góp ý cũ vẫn đọc được, không suy cặp hoặc mục tiêu điều hướng từ chỉ số
  hai mảng hay từ chuỗi. Bản mới không có vấn đề trả về danh sách ưu tiên rỗng.
- Sau kiểm thử kỹ thuật vòng sửa, cập nhật lời dẫn tour chặng 5–6: ý đồ và
  nguồn, chọn hoặc từ chối, điều hướng, tự sửa, lưu/review. Giữ sáu bước,
  storage/tiến độ cũ và quyền bỏ qua/mở lại.

## Kết quả

- Backend: **319 passed, 1 skipped**, một cảnh báo deprecation Starlette/httpx.
  Bao gồm plan mới và review, nguồn A/B/retained answers, proposal/history,
  lỗi nguồn/khác artifact/sai phần/một phần sai, 409 và checkpoint phục hồi.
- TypeScript no-emit, production build và bốn bộ checks render/state
  (`card-feedback`, `story-editor`, `onboarding`, `progress`): qua.
- Bộ mới `revision-targets.browser.cjs`: **72/72 ca** trên Chrome
  155.0.8059.86, Firefox 151.0 và WebKit 26.5. Mỗi engine có 12 tình huống
  ở viewport 1440×1000 và 390×844. Có kiểm tra toàn bộ buffer trước/sau,
  số request, tên dự án chưa lưu, hoàn tác về nguồn, mục trùng tên, lựa chọn
  nhiều mục, title/logline/phần chi tiết, dữ liệu legacy và mất response sau
  khi server giả đã ghi thành công. Không tự retry hoặc gọi review tiếp.
- Bộ onboarding đầy đủ qua trên ba engine: luồng kết hợp, bàn phím, cũ/mới,
  nguồn thiếu, buffer, lỗi lưu/AI, hai tab, response muộn, reload và storage.
- Hồi quy workspace/focus/hội thoại hiện có trên Chrome: **33/33 ca** qua.
- Rà ảnh góp ý desktop/mobile và whitespace diff: qua.

Trình duyệt dùng production frontend tại localhost, profile và dữ liệu QA
riêng, API mock. Backend dùng provider giả và SQLite tạm. Không dùng dự án
thật, không gọi API trả phí. Bộ smoke `workspace-release.browser.cjs` yêu cầu
fixture API/SQLite riêng và không nằm trong kết quả chạy này.

## Chạy lại

```sh
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend
npx tsc --noEmit --incremental false
npm run build
npm run start -- --hostname 127.0.0.1 --port 33435
```

Cung cấp Playwright qua `NODE_PATH`, sau đó từ repo root chạy
`frontend/tests/revision-targets.browser.cjs` với
`TOUR_TEST_URL=http://localhost:33435` và `TOUR_BROWSER=chrome|firefox|webkit`.
Báo cáo/ảnh mặc định nằm trong `/tmp/firstframe-revision-<engine>/`.
Các bộ regression dùng cùng biến URL/browser. Không trỏ bộ smoke release vào
server/dữ liệu thật; nó cần fixture riêng được chuẩn bị trước.

## Giới hạn và mốc tiếp theo

Sau đợt kỹ thuật này đã có [kiểm chứng model thật Qwen 2.5 7B](../evaluations/issue-7-qwen7b-2026-10-25.md): hợp đồng dữ liệu qua, chất lượng góp ý chưa đủ nghiệm thu #7.
Tiếp tục [đối chứng Qwen3 8B trên cùng bộ ca](../evaluations/issue-7-qwen3-vs-qwen25-2026-10-25.md): đọc phủ định tốt hơn ở ca hai Ending, nhưng còn lỗi hợp đồng/bước sửa và vượt ngân sách chờ; chưa thay model mặc định.

Đúng trích dẫn và đúng mục tiêu không chứng minh nhận xét đúng nghĩa. Chưa
chạy model thật trong đợt này, chưa kiểm chứng khả năng người mới giải thích
vì sao sửa/giữ sau hai vòng. Model thật, pilot và người đọc có kinh nghiệm
vẫn cần bằng chứng theo tiêu chí #7 trước khi nghiệm thu và tiếp tục H1–H8.

Các mục #22 về pilot 3–5 người, tổng kết, screen reader, thiết bị/IME/bàn phím
ảo thật và full Safari vẫn chưa được nghiệm thu. WebKit không thay full Safari.
Plan, roadmap, cấu hình model, prototype và dữ liệu baseline offline giữ nguyên.
