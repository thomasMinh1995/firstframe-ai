# Task 1 — Tổ chức lại cách người dùng làm việc với FirstFrame đang có

- Ngày: 02/11/2026.
- Trạng thái: plan triển khai; chưa thay đổi runtime.
- Phạm vi: task 1 trong ba task đã gộp theo trao đổi với chủ sản phẩm.

## Kết quả cần đạt

Tổ chức các chức năng FirstFrame hiện có thành một hành trình phát triển
kịch bản dễ hiểu. Người viết bắt đầu từ một quan sát, kỷ niệm hoặc tình
huống; làm việc cùng AI để làm rõ, phát triển câu chuyện, dàn cảnh, viết và
sửa. Ở mỗi công đoạn, họ biết FirstFrame có thể giúp gì, đang sử dụng nguồn
nào và quyết định nào cần do mình lựa chọn.

AI tiếp tục hỏi, đề xuất, viết thử và góp ý bằng các chức năng đã có. Tác giả
đọc, chỉnh và quyết định hướng phát triển trước khi chuyển công đoạn. Khả
năng tự viết vẫn được giữ, nhưng không yêu cầu người dùng tự làm mọi việc.

Hành trình chính:

```text
Chất liệu → Làm rõ → Story plan → Dàn cảnh → Viết & sửa → Đọc & xuất
```

Điều hướng chỉ mở nội dung. Các hành động làm rõ, tạo plan, tạo đề xuất cảnh,
viết thử hoặc nhận góp ý vẫn gọi AI khi người dùng chủ động yêu cầu. Task
này thay cách tiếp cận và phối hợp các chức năng đó, không xây năng lực AI mới.

## Vai trò trong từng công đoạn

| Công đoạn | FirstFrame hỗ trợ bằng chức năng hiện có | Tác giả quyết định |
| --- | --- | --- |
| Chất liệu và làm rõ | Phản chiếu cách AI hiểu nguồn, hỏi phần quan trọng còn thiếu và hiển thị đề xuất riêng | Bổ sung, sửa cách hiểu, trả lời hoặc để mở |
| Story plan | Phát triển một phương án câu chuyện; giữ bản đề xuất và góp ý theo nguồn | Đọc, chỉnh và chọn bản làm nguồn cho dàn cảnh |
| Dàn cảnh | Gợi ý danh sách/diễn tiến cảnh và cách thể hiện theo nguồn được chọn | Dùng, chỉnh, bỏ hoặc tự thêm/sắp xếp cảnh |
| Viết và sửa | Viết thử một cảnh/phần được chọn, góp ý và giữ phương án sửa riêng | Tự viết, biên tập, nhận hoặc bỏ phương án |
| Đọc và xuất | Mở bản lưu, lịch sử và xuất đúng bản được chọn | Chọn phiên bản để đọc và bàn giao |

Lưu, mở bản đã có, điều hướng và xuất PDF dùng xử lý ứng dụng hiện tại;
không cần model. Điều này không loại AI khỏi các công đoạn sáng tác ở trên.

## Cơ sở từ code hiện tại

- `Workspace.tsx` đã có `action("analyze" | "plan" | "review")`, lưu trước
  tác vụ và kiểm tra kết quả đến muộn. Nhưng CTA nhập ý tưởng gọi
  `startDraftRun()` thay vì lối làm rõ riêng.
- `WorkspaceTools.tsx` đang gộp hành trình thành ba nhóm, CTA chính dẫn tới
  draft-run hoặc đọc/xuất. Có thể dùng lại stage ID, công cụ và sự kiện mở
  panel hiện tại để làm rõ từng bước.
- `ClarificationConversation.tsx` đã xử lý không có câu hỏi, câu trả lời để
  mở, AI đề xuất và nút tạo plan riêng.
- `SceneOutlineEditor.tsx` đã cho chọn nguồn plan, tạo dàn cảnh rỗng, tự thêm,
  sửa, sắp xếp cảnh hoặc yêu cầu gợi ý riêng.
- `ScreenplayEditor.tsx` đã cho bắt đầu từ dàn cảnh được chọn, tự viết hoặc
  yêu cầu AI viết thử/góp ý/sửa, đọc và xuất. Không cần thêm API cho hành trình này.
- Draft-run đã có nguồn riêng, checkpoint, tiếp tục, hủy và nhận kết quả có
  kiểm tra phiên bản. Giữ làm lối tạo nháp tự động riêng.

## Phạm vi nhỏ nhất

Thay đổi frontend, kiểm tra liên quan và tài liệu mô tả luồng. Tận dụng
`idea`, `constraints`, câu trả lời, bản lưu, API và các lượt AI hiện có.
Không thêm schema, migration, dependency, workflow engine, model hay cờ
chế độ lưu trong dự án. Chất lượng và phạm vi phản biện mới thuộc task 2.

Ô khoảnh khắc tiếp nhận chất liệu đời sống. Ô điều muốn giữ tiếp nhận chi
tiết quan trọng và điều chưa muốn quyết định. Hướng dẫn bằng ví dụ ngắn;
không thêm bảng hỏi bắt buộc hoặc một sổ tay nghiên cứu riêng.

## Thứ tự triển khai

### 1. Mở lối làm rõ riêng từ chất liệu

- CTA mặc định khi chưa có analysis hoặc brief đã đổi gọi `action("analyze")`.
- Sau khi làm rõ, dừng tại `ClarificationConversation`: tác giả trả lời,
  để mở, sửa nguồn hoặc chủ động tạo story plan.
- Không có câu hỏi vẫn hiển thị lựa chọn tạo plan; không tự chạy bước tiếp.
- Nguồn đã có được mở lại thay vì tạo lại chỉ vì người dùng quay về bước đầu.
- Tạo nháp tự động có nhãn và lối mở riêng. Nếu có lượt đang chạy/chờ, dẫn
  tới đúng lượt hiện có; không tự hủy hoặc khởi động một lượt khác.

Tệp chính: `Workspace.tsx`, `ClarificationConversation.tsx`.

### 2. Hiển thị hành trình và bước tiếp theo theo nội dung hiện có

- Đưa sáu bước ra navigation hiện có; giữ stage ID và cơ chế
  `revealWorkspaceTarget()`.
- Cho mở bước có công cụ bắt đầu khi đã đủ nguồn: có plan thì mở được dàn
  cảnh, có dàn cảnh thì mở được phần viết. Mở panel không tạo dữ liệu.
- Nút bước tiếp theo mở đúng công cụ, để tác giả chủ động chọn nguồn và bắt
  đầu bằng các nút hiện có trong editor.
- Ở mỗi bước, làm rõ hành động nhờ FirstFrame hỗ trợ và hành động tác giả
  tự chỉnh. Các nút gợi ý cảnh, viết thử và nhận góp ý phải dễ tìm trong
  bước tương ứng; không bắt người dùng biết tên API hoặc tự viết prompt kỹ thuật.
- Phân biệt chưa có nội dung, nội dung đã lưu và nguồn đã thay đổi; có nội
  dung không đồng nghĩa tác giả đã duyệt hoặc chất lượng đã đạt.
- Không tự đổi plan/outline/script theo nội dung của bước trước. Giữ cảnh
  báo khác nguồn và cơ chế chọn bản mới đang có.
- Xem lại một bước giữ buffer và vị trí đang viết. Lưu trước các tác vụ ghi
  hoặc AI tiếp tục dùng cơ chế `persist()` hiện tại.
- Giữ draft-run và lịch sử có lối mở riêng, không biến thành một bước bắt
  buộc của hành trình phát triển từng bước cùng FirstFrame.

Tệp chính: `WorkspaceTools.tsx`, `workspaceToolState.ts`, `Workspace.tsx`,
CSS navigation hiện có. Chỉ chỉnh `SceneOutlineEditor.tsx` hoặc
`ScreenplayEditor.tsx` nếu cần sửa nút mở/chuyển bước.

### 3. Cập nhật hướng dẫn, giữ tiến độ người dùng cũ

- Giữ sáu mục hướng dẫn: dự án, chất liệu, phát triển câu chuyện/dàn cảnh,
  viết và sửa, đọc/xuất, lưu/quay lại.
- Sửa nội dung và đích focus của mục phát triển để hướng dẫn làm việc cùng
  FirstFrame theo từng công đoạn. Giải thích khi nào nhờ AI hỗ trợ và khi nào
  đọc/chỉnh/chọn nguồn; không mặc định phải tạo trọn bản nháp trước.
- Tên nội bộ `draft-run` cũ có thể giữ để tương thích tiến độ; đích focus
  của hướng dẫn không bắt buộc phải mở hoặc chạy một lượt tạo tự động.
- Giữ tương thích record tour, trạng thái bỏ qua/hoàn thành và bước workspace
  đang nhớ. Không ép người cũ chạy lại onboarding.
- Làm navigation đọc được ở màn hình 320px và sử dụng được bằng bàn phím.
- Cập nhật README và mô tả luồng trong kế hoạch MVP; giữ nguyên các điều kiện
  pilot/nghiệm thu đã chốt.

Tệp chính: `OnboardingTour.tsx`, `onboardingState.ts`, CSS hiện có,
`README.md`, `docs/plans/vietnam-first-screenplay-mvp.md`.

## Kiểm tra và tiêu chí nghiệm thu

| Tình huống | Kết quả cần đạt |
| --- | --- |
| Dự án mới từ một quan sát đời thường | Làm rõ riêng; chưa có plan, outline hoặc screenplay trước yêu cầu tương ứng |
| Không có câu hỏi / để trống một câu | Có thể tiếp tục chủ động; phần để mở không trở thành quyết định tác giả |
| Dừng ở story plan | Sửa, lưu, tải lại đúng bản; chưa tạo outline/script tự động |
| Từ plan sang dàn cảnh | Chọn nguồn đã lưu; có thể yêu cầu gợi ý bằng AI hiện có hoặc tự thêm/sửa/sắp xếp; chỉ dùng đề xuất khi tác giả chọn |
| Từ dàn cảnh sang viết | Chủ động bắt đầu từ nguồn đã lưu; có thể nhờ AI viết thử/góp ý/sửa bằng chức năng hiện có, rồi đọc và quyết định dùng |
| Yêu cầu AI ở từng công đoạn | Gửi đúng nguồn, ý đồ và câu trả lời đã lưu; dừng ở kết quả của công đoạn được yêu cầu, không tự gọi các bước tiếp theo |
| Tự viết hoặc bỏ qua đề xuất | Vẫn sửa, lưu và xuất được; không phải dùng mọi gợi ý AI để hoàn tất |
| Điều hướng, mở hướng dẫn, tải lại | Không phát sinh yêu cầu AI; giữ buffer khi chỉ chuyển panel |
| Nguồn thay đổi ở bước trước | Nội dung phía sau giữ nguyên và hiển thị trạng thái khác nguồn |
| Đang có draft-run | Mở lại đúng lượt; không chạy lượt mới hay nhận candidate vào bản tác giả ngầm |
| Lỗi lưu/AI hoặc mất xác nhận | Giữ buffer, bản đã lưu, lịch sử và cách phục hồi hiện tại |
| Dự án/tour cũ, desktop/mobile | Mở được; không mất tiến độ; focus và navigation hoạt động ở 320px |

Kiểm tra tự động cần chỉnh/bổ sung vào các suite hiện có:

- `workspace-tools.cjs`: bước khả dụng và CTA theo trạng thái dự án.
- `onboarding.cjs`: sáu mục hướng dẫn, tương thích tiến độ cũ, không gọi AI
  từ thao tác tour.
- Browser workspace/onboarding/scene-outline/screenplay: một hành trình làm
  rõ → plan → gợi ý dàn cảnh → viết thử/góp ý → tác giả chỉnh/chọn → xuất.
  Kiểm đếm request để xác nhận AI chỉ chạy theo yêu cầu, dùng đúng nguồn và
  không tự chuyển công đoạn. Thêm ca tự viết/bỏ đề xuất, lưu/mở lại, nguồn
  đổi và lượt tự động đang có.
- Chạy `npm test`, `npm run typecheck` và các browser suite bị ảnh hưởng.
  Chạy lại backend regression liên quan nếu cần đối chiếu hợp đồng API;
  không gọi model thật chỉ để kiểm tra điều hướng.

Kiểm tra luồng có thể dùng provider giả lập để xác nhận điều phối, nguồn và
các lượt gọi AI. Kết quả này không chứng minh chất lượng câu hỏi, phương án
hoặc góp ý; chất lượng đó cần đánh giá bằng model thật và người đọc ở task 2,
cùng pilot chất liệu thật ở task 3.

## Điểm dừng của task

Task hoàn thành khi người dùng làm việc được với FirstFrame qua từng công
đoạn: biết cách yêu cầu AI hỗ trợ, đọc/chỉnh/chọn kết quả, chủ động chuyển
bước, lưu/mở lại và xuất đúng bản. Tạo nháp tự động vẫn hoạt động riêng;
các cơ chế bảo toàn dữ liệu không bị suy giảm.

Đợt này không triển khai sổ tay chất liệu, nhật ký lý do sửa, reviewer mới,
thay model, thay prompt sáng tác hoặc mở rộng sản xuất phim.
