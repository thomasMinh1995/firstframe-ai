# Kế hoạch cập nhật Bản nháp và Review theo prototype đã chọn

Ngày 29/10/2026. Trạng thái: DR-01/DR-02 đã merge PR #79; DR-03/DR-04 đã merge PR #80. DR-05/DR-06 đã merge PR #81. DR-07/DR-08 đã triển khai dạng xem thử trên nhánh `fix/draft-workflow-decisions`; DR-09/DR-10 chưa triển khai. Xem [kiểm chứng quyết định và reader](../testing/draft-workflow-decisions-2026-10-30.md). Xem [kiểm chứng chuyển trạng thái và phục hồi](../testing/draft-workflow-transitions-2026-10-30.md). Xem [kiểm chứng card và bố cục](../testing/draft-workflow-cards-2026-10-29.md). Xem [hợp đồng và kiểm chứng giai đoạn 1](../testing/draft-workflow-progress-2026-10-29.md). Phạm vi là tiến độ tạo nháp và cách đọc, nhận bản nháp trong Bản nháp & Review; tiếp nối các task hệ thống và UI đã giao của workflow AI chủ động.

Áp dụng bố cục card nối theo đường chữ S, trạng thái thinking cho công việc đang chạy và skeleton được thay bằng kết quả từng bước. Người dùng phải biết hệ thống đang làm gì, phần nào đã có thể đọc và khi nào cần quyết định. Tiến độ phản ánh checkpoint backend; hiệu ứng chỉ trình bày kết quả đã có.

## Thiết kế đã chọn

Prototype: `firstframe-draft-flow.html`, bản người dùng đã chọn trong chat này. Nội dung mẫu Chiếc ô cũ và thời gian mô phỏng không phải dữ liệu vận hành.

- Desktop: ba card một hàng, thứ tự hàng đầu trái sang phải, hàng tiếp phải sang trái, rồi tiếp tục. Đường nối và số thứ tự thể hiện chiều đi. DOM và thứ tự bàn phím luôn giữ thứ tự workflow.
- Mobile: một cột, card lệch trái phải nhẹ và đường nối mềm. Nội dung, nút và thông báo lỗi vẫn vừa 320px.
- Card chờ chỉ hiện tên công đoạn và Chờ bước trước. Card đang chạy hiện nhãn công việc cùng skeleton; card có kết quả hiện tóm tắt và Đọc nội dung.
- Nhãn thinking chỉ mô tả thao tác như Đang viết cảnh 1 hoặc Đang đối chiếu nguồn. Không trình bày suy nghĩ nội bộ của model.
- Kết quả hiện bằng fade và dịch nhẹ trong khoảng 350–550ms. Blur tối đa 2px, chỉ khi chưa bật reduced motion. Skeleton có shimmer nhẹ; đường nối nhấn bước hiện tại. Không làm chữ đang đọc tiếp tục nhấp nháy.
- Nền viết đặc, card có bóng nhẹ; thanh trạng thái có nền dự phòng đặc và kính mờ khi được hỗ trợ. Dùng hệ màu, kiểu chữ và focus của FirstFrame.
- Nội dung xuất hiện ngay khi đọc được; animation không trì hoãn lưu, nhận bản hoặc xử lý lỗi. Tôn trọng reduced motion, reduced transparency và forced colors.

Các nút Chạy mô phỏng, Chạy lại và Tạm dừng trong prototype là công cụ xem thử. Bản thật dùng Tạo bản nháp, Hủy các bước tiếp theo, Tiếp tục bước chưa gửi và Dùng bản nháp này theo điều kiện hiện có. Không thêm pause/resume cho một lần model đang tính toán. Hủy không có nghĩa call đã gửi dừng tức thì.

## Phần hiện tại cần thay đổi

| Thành phần | Hiện trạng | Thay đổi cần làm |
| --- | --- | --- |
| `backend/app/application/draft_run_store.py` | Run lưu JSON trong SQLite, có checkpoint và candidate revision | Bổ sung trạng thái bền vững cho từng mục workflow ngay trong JSON run; cập nhật cùng giao dịch với artifact tương ứng |
| `backend/app/application/draft_workflow.py` | Lưu `step`, số cảnh, candidate và kết quả call; review có thể lỗi riêng | Ghi bắt đầu, kết quả, lỗi và phần được giữ theo từng công đoạn/cảnh; phân biệt review story plan với review screenplay |
| `backend/app/api/routes/draft_runs.py` | GET trả run gọn; candidate đọc riêng | Bổ sung progress có phiên bản và khả năng tiếp tục cùng lý do chặn; giữ đường đọc/tiếp tục/hủy/nhận hiện có |
| `frontend/app/draftRunsApi.ts` | Kiểu và validator chỉ biết bước hiện tại, tổng cảnh | Kiểu, validator và fallback cho progress cũ/mới, trạng thái card và điều kiện hành động |
| `frontend/app/DraftRunPanel.tsx` | Poll 1,5–8 giây; đọc candidate khi revision đổi; các phần qua details | Dùng vùng card để trình bày workflow; giữ CandidateAutosave và các thao tác nguồn hiện có |
| `frontend/app/OperationProgress.tsx`, `progressState.ts` | Tiến độ request/stream cho nhiều thao tác khác | Dùng lại nhãn/primitive thích hợp; không ép timeline request tạm thời thành lịch sử run bền vững |
| `frontend/app/Workspace.tsx`, `WorkspaceStage.tsx` | Đổi công đoạn và đưa candidate đã nhận vào editor | Giữ vị trí đọc, lựa chọn card và focus; một nơi trình bày tiến độ cho cùng một lượt |
| CSS workspace | Đã có thinking, panel và card theo các công đoạn cũ | Thêm CSS riêng cho đường S, trạng thái card, skeleton, reveal và breakpoint; giới hạn phạm vi selector |

## Ánh xạ công đoạn

Chín card của prototype là ví dụ có hai cảnh. Bản thật tạo danh sách theo run và số cảnh đã xác định, không cố định chín bước hoặc hai cảnh.

| Card | Dữ liệu xác nhận | Điều kiện trình bày |
| --- | --- | --- |
| Đọc ý tưởng | `analysis` đã checkpoint | Hoàn tất khi có kết quả phân tích được lưu |
| Ý đồ và điểm còn mở | Analysis, câu hỏi, câu trả lời và `needs_input` | Cần bạn xem nếu chờ câu trả lời; đủ rõ thì hoàn tất. Đây là mốc quyết định, không thêm một call AI |
| Story plan | `candidate.draft` | Đọc được ngay sau checkpoint, kể cả critic chưa hoàn tất |
| Đối chiếu story plan | Trạng thái critic riêng | Đang chạy, đã lưu góp ý hoặc cảnh báo. Critic lỗi vẫn giữ plan |
| Dàn cảnh | Danh sách scene và ID đã lưu | Tạo card viết cảnh sau khi dàn cảnh được xác nhận hợp lệ |
| Viết từng cảnh | Scene ID, blocks và checkpoint tương ứng | Một card mỗi cảnh, stable key theo ID; chỉ hiện nội dung thực đã lưu |
| Review kịch bản | Trạng thái review từng cảnh và nguồn review | Một card tổng hợp với chi tiết theo cảnh. Không đồng nhất không có nhận xét với đạt chất lượng |
| Bản nháp để review | Candidate có nội dung, trạng thái run, quyền nhận | Phân biệt nháp đầy đủ, một phần, đã nhận và góp ý chưa hoàn tất |

Phần bản thảo đã có luôn đọc được khi review còn chạy. Điều kiện nhận candidate vẫn theo backend; không bật nút nhận sớm bằng trạng thái animation.

## Hợp đồng dữ liệu tiến độ

Bổ sung `progress_version`, `progress_revision` và `workflow_items` vào response run; các trường cũ được giữ. Mỗi item có `id`, `kind`, `scene_id` khi liên quan, `status`, `started_at`, `finished_at`, tham chiếu artifact/candidate revision và mã lỗi an toàn khi có. ID dùng định danh công đoạn và scene thực, không dùng số thứ tự hiển thị. Không lặp toàn bộ văn bản hoặc raw call trong response tiến độ.

Trạng thái item gồm `pending`, `running`, `needs_input`, `completed`, `warning`, `failed`, `interrupted`, `cancelled`, `skipped`; `unknown` dành cho phần lịch sử không xác định được. Chỉ ghi completed khi artifact hoặc kết quả tương ứng đã được lưu hợp lệ. Review lỗi riêng dùng warning khi phần tạo nội dung tiếp tục được. Mục chưa thực hiện khi hủy không được tô xanh hoặc tính thành hoàn tất.

`progress_revision` tăng khi trạng thái thay đổi, độc lập với candidate revision. Client lấy trạng thái mới dù chưa có văn bản mới; chỉ tải lại candidate khi candidate revision thay đổi. Cập nhật artifact và trạng thái completed trong cùng giao dịch để tránh card báo có nội dung nhưng candidate chưa đọc được.

Backend trả `can_continue` và lý do nếu bị chặn, theo cùng điều kiện bảo vệ của route continue hiện tại. Frontend không tự suy luận có thể retry từ tên trạng thái interrupted. Không lộ prompt, raw output hoặc stack trace qua copy công khai của card.

Run cũ thiếu timeline được chiếu từ artifact và trường hiện có. Phần không xác định rõ hiện Không có trạng thái chi tiết, không bịa timestamp, thành công hoặc thời lượng. Mở run cũ không ghi lại provenance và không gọi model để bù dữ liệu.

Tiếp tục dùng poll hiện có, không thêm SSE/WebSocket trong đợt này. Khi mất kết nối: giữ card/nội dung đã nhận, đánh dấu chưa cập nhật được; skeleton mạng không biến thành lỗi model. Response cũ của run/project trước không được cập nhật vào run đang mở.

## Các giai đoạn triển khai

Các task dưới đây là backlog tiếp nối của đợt áp dụng prototype, chưa phải issue đã tạo. DR-01–DR-08 đã có triển khai và kiểm chứng kỹ thuật; card hiện bật chủ động để xem thử. Các task còn lại chưa triển khai. Các task SYS và UI cũ giữ trạng thái đã triển khai.

| Giai đoạn | Task | Ưu tiên | Kết quả bàn giao | Phụ thuộc |
| --- | --- | --- | --- | --- |
| 1. Tiến độ thật | DR-01 Chốt trạng thái và ánh xạ workflow | P0 | Kiểu item, quy tắc hoàn tất/lỗi/hủy, mapping run cũ và số cảnh động | Không |
| 1. Tiến độ thật | DR-02 Lưu timeline và trả hợp đồng API | P0 | SQLite giữ trạng thái từng item, revision tiến độ và khả năng tiếp tục; reload/restart đúng | DR-01 |
| 2. Card và đường S | DR-03 Nối dữ liệu run vào mô hình hiển thị card | P1 | Frontend validator, stable ID, reconcile poll/candidate và fallback dữ liệu cũ | DR-02 |
| 2. Card và đường S | DR-04 Dựng card và bố cục desktop/mobile | P1 | Component card, đường S ba cột; mobile một cột; mở kết quả trong ngữ cảnh | DR-03 |
| 3. Chuyển trạng thái | DR-05 Skeleton thinking và reveal | P1 | Pending → running → kết quả/lỗi theo dữ liệu thật; hỗ trợ giảm chuyển động | DR-04 |
| 3. Chuyển trạng thái | DR-06 Kết quả về dồn và phục hồi giao diện | P1 | Không replay loading của bước đã xong; không mất nội dung/vị trí/focus khi poll hoặc reload | DR-03, DR-05 |
| 4. Quyết định của tác giả | DR-07 Làm rõ và xử lý gián đoạn ngay tại card | P0 | Câu hỏi, để mở, tiếp tục, hủy, lỗi chưa rõ kết quả; nút đúng điều kiện backend | DR-02, DR-04 |
| 4. Quyết định của tác giả | DR-08 Đọc sửa và dùng bản nháp | P1 | Nối reader/candidate/editor; flush trước nhận; review cũ đúng nguồn; không có hai editor cùng sửa một buffer | DR-06, DR-07 |
| 5. Nghiệm thu | DR-09 Hồi quy dữ liệu UI và khả năng tiếp cận | P0 trước bật luồng mới | Kiểm chứng tự động và browser cho danh sách ca bên dưới | DR-05–DR-08 |
| 5. Nghiệm thu | DR-10 Chạy luồng model thật và cập nhật hướng dẫn | P0 trước bật luồng mới | Báo cáo toàn luồng, số call/thời gian thật, ảnh/video; onboarding và QA-01 phản ánh UI mới | DR-09 |

Mỗi giai đoạn giao thành một PR vào dev. PR 1 có hợp đồng/API; PR 2 dựng card dùng được với dữ liệu thật; PR 3 hoàn thiện chuyển trạng thái; PR 4 nối đủ tương tác và recovery; PR 5 chốt kiểm chứng và hướng dẫn. Không bật giao diện thay thế mặc định cho đến khi có đủ hành động và recovery của giai đoạn 4, cùng nghiệm thu giai đoạn 5.

## File triển khai theo nhóm task

- DR-01–DR-02: `backend/app/application/draft_run_store.py`, `draft_workflow.py`, `backend/app/api/routes/draft_runs.py`; thêm schema progress nhỏ trong `backend/app/api/schemas/draft_runs.py` nếu cần cho validation; mở rộng `backend/tests/test_draft_runs.py`.
- DR-03–DR-04: `frontend/app/draftRunsApi.ts`, `DraftRunPanel.tsx`; thêm `DraftWorkflow.tsx`, `DraftWorkflowCard.tsx`, `draftWorkflowState.ts` và `draftWorkflow.css`. Chỉ tách primitive dùng lại khi có nhu cầu thực; không thêm UI library.
- DR-05–DR-06: các component/CSS trên; dùng lại nhãn và hiệu ứng phù hợp từ `OperationProgress.tsx`, `progressState.ts`, `storyWorkspace.css`. Không thay các timeline request khác ngoài phạm vi cần tích hợp.
- DR-07–DR-08: `ClarificationConversation.tsx`, `DraftRunPanel.tsx`, `candidateAutosave.ts`, `Workspace.tsx`, `WorkspaceStage.tsx` và editor/reader hiện có khi cần nối. Giữ hợp đồng nhận, nguồn và history.
- DR-09–DR-10: test frontend liên quan autosave/run, `frontend/tests/workspace-release.browser.cjs`, fixture QA, `OnboardingTour.tsx`, `onboardingState.ts`, README và báo cáo trong `docs/testing/`.

Tên file mới là phương án triển khai dự kiến, không yêu cầu tạo tất cả nếu cấu trúc nhỏ hơn đã đáp ứng đủ.

## Quy tắc skeleton và animation

1. Chỉ công đoạn đang chạy có skeleton xử lý. Công đoạn chưa tới hiện chờ; nội dung đã hoàn tất không quay lại skeleton do polling.
2. Khi đang đọc run/candidate lần đầu, skeleton tải dữ liệu là trạng thái mạng riêng. Giữ bản đã có khi refetch.
3. Không dùng timer để tự chuyển card sang completed. Không trì hoãn kết quả nhanh để bắt người dùng chờ đủ một vòng shimmer.
4. Nếu poll bỏ qua nhiều bước đã hoàn tất, nhận ngay trạng thái cuối và hiện nội dung. Có thể stagger reveal tối đa 100ms giữa tối đa ba item, tổng hiệu ứng không vượt khoảng 750ms; không diễn lại từng bước như đang gọi AI.
5. Chỉ animate lần đầu nhận kết quả hoặc khi có revision nội dung mới đã xác nhận. Đổi chế độ đọc, đóng panel, remount hoặc mở lại run không replay toàn bộ.
6. Giữ vùng skeleton gần chiều cao preview cuối. Tính lại đường nối sau resize, font hoặc card đổi kích thước; không đo liên tục theo từng frame.
7. Không tự cuộn hoặc chuyển focus khi mỗi kết quả về. Người dùng chủ động mở nội dung; trả focus về nút mở khi đóng. Lỗi và bước cần nhập phải nhận biết được cả ngoài vùng đang nhìn.
8. Progress thể hiện số mục có kết quả và số cảnh thực, không giả định các công đoạn có trọng số thời gian bằng nhau. Chưa có tổng cảnh thì hiện bước hiện tại thay vì phần trăm. Hoàn tất có cảnh báo phải nêu riêng số mục cần xem.

## Ca nghiệm thu bắt buộc

| Ca | Kết quả cần đạt |
| --- | --- |
| Brief đủ rõ và brief cần hỏi | Không thêm một call cho card Ý đồ; cần hỏi thì dừng đúng chỗ, để mở hoặc trả lời rồi tiếp tục |
| Một, hai và sáu cảnh | Số card theo dàn cảnh thực; không cố định chín item; ID không đổi khi cập nhật nội dung |
| Story plan có trước critic | Plan đọc được, critic vẫn running; critic lỗi không xóa hoặc giữ kín plan |
| Cảnh và review hoàn thành từng phần | Hiện nội dung đã lưu; từng review có trạng thái riêng, không gắn nhầm nguồn |
| Poll bỏ qua nhiều bước | Không hiện thinking giả hoặc chờ nhiều vòng animation; trạng thái cuối và nội dung đồng nhất |
| Mạng chậm, response sai thứ tự, đổi project/run | Không ghi đè nội dung mới, không chuyển trạng thái ngược từ response cũ |
| Reload và restart backend | Phục hồi checkpoint; lần gọi chưa rõ kết quả không tự gửi lại; lịch sử cũ tiếp tục đọc được |
| Hủy trong lúc model chạy | Không gọi bước sau; phần đã có giữ nguyên; thông báo kết quả về muộn theo trạng thái thực |
| Sửa candidate rồi nhận ngay | Flush đúng buffer, revision và provenance; 409 giữ chữ; nhận lặp không áp hai lần |
| Desktop, 320/390px, Tab và screen reader | Không tràn, thứ tự đọc đúng dù hàng đảo chiều; focus không bị animation lấy đi; thông báo theo mốc |
| Reduced motion và fallback nền | Không shimmer/blur/trượt khi giảm chuyển động; nội dung và điều khiển vẫn rõ |
| Toàn luồng tới PDF | Kể ý tưởng → tạo nháp → đọc/sửa/giữ → chọn snapshot → PDF; xuất không phát sinh call AI |

Kiểm thử backend tập trung vào giao dịch trạng thái/artifact, lỗi và phục hồi. Frontend kiểm tra mapping/reconcile bằng unit test; dùng browser cho bố cục, focus, hành vi skeleton và thao tác nhận. Không thêm test chỉ để so khớp số CSS hoặc snapshot hình thức từng card.

## Giới hạn và phần theo dõi riêng

Lần ghi workflow đã gặp model trả scene sai cấu trúc và tạo ba cảnh dù brief yêu cầu tối đa một. `draft_workflow.py` hiện có chỉ dẫn tạo 2–6 cảnh khi gọi tạo dàn cảnh. Đây là phần cần điều tra/sửa trong QA-01 về giữ đúng giới hạn tác giả; thay styling không giải quyết lỗi này. DR-10 phải giữ kết quả thật và ghi lỗi, không trình bày màn hình mô phỏng như bằng chứng model đã đạt chất lượng. Mọi sửa logic sinh nội dung được giao thành task/PR có kiểm chứng riêng.

Đợt này tái sử dụng runner, SQLite, polling và autosave. Chưa thêm pause LLM, streaming token vào card, workflow engine, thư viện animation hoặc suy luận ngữ nghĩa mới. Giữ lịch sử/provenance và cảnh báo chất lượng hiện có. Hoàn tất các task DR không tự đóng QA-01 phát hành còn chờ người đọc, pilot và thiết bị thật.

Mốc duyệt thiết kế tiếp theo là cuối giai đoạn 2: xem đường S trên dữ liệu thật. Mốc bật thay thế giao diện là sau giai đoạn 5: đủ skeleton/reveal, hành động tác giả, recovery và báo cáo toàn luồng.
