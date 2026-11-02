# Kế hoạch triển khai Streaming Interfaces cho FirstFrame

- Ngày lập: 30/10/2026.
- Cập nhật baseline: 02/11/2026, sau PR #89/#90.
- Cập nhật kế hoạch: 02/11/2026, bổ sung trải nghiệm đọc ổn định và phạm vi luồng tạo nháp chính.
- Trạng thái: SI-01/SI-02 đã triển khai trên nhánh `fix/streaming-interfaces`; SI-03 chưa nghiệm thu đầy đủ. Xem [bằng chứng kiểm tra hẹp](../testing/streaming-interfaces.md).
- Issue triển khai: [#91 — Streaming Interfaces: đọc nội dung đã lưu trước khi AI hoàn tất](https://github.com/thomasMinh1995/firstframe-ai/issues/91). Issue chứa kế hoạch đầy đủ vì tài liệu local này chưa commit/push.
- Lần chuẩn bị plan/issue chỉ sửa tài liệu. SI-01/SI-02 được triển khai và kiểm tra hẹp bằng provider giả, giữ dữ liệu, không gọi AI thật hoặc chạy QA toàn bộ. Yêu cầu tiếp theo cho phép stage/commit và push nhánh này; chưa yêu cầu tạo PR hoặc merge.
- Mục tiêu: người dùng bắt đầu đọc nội dung AI đã kiểm tra và lưu trong khi các bước tiếp theo vẫn chạy; lỗi góp ý hoặc kết nối không làm mất nội dung đã có.
- Phạm vi bản đầu: hiển thị story plan sau checkpoint, trước critic; kiểm chứng hiển thị từng cảnh trong luồng tạo bản nháp hiện có.
- Liên quan: [workflow AI chủ động](ai-first-workflow.md), [phục hồi plan](../testing/plan-recovery.md), [stream tiến độ](../testing/workflow-progress.md), [draft runs](../testing/phase3-draft-runs-2026-10-29.md).

## 1. Quyết định triển khai

Triển khai theo từng phần nội dung hoàn chỉnh đã được kiểm tra và lưu. Bản đầu không cần đổi provider sang token streaming: plan có thể đến người đọc trước khi critic xong bằng checkpoint hiện có. Đây là một cải tiến của luồng viết, không phải thay thế bộ điều phối AI.

### Lý do cần triển khai

Luồng tạo Story plan riêng đã lưu plan trước critic nhưng client còn chờ kết quả cuối, nên thời gian có nội dung để đọc muộn hơn thời điểm nội dung đã sẵn sàng. Luồng tạo nháp chính đã có checkpoint và polling; việc phát hiện phần vừa có thể đọc, giữ vị trí đọc và phân biệt phần đã lưu với toàn bộ nháp hoàn tất vẫn cần được chốt nhất quán.

Issue này giải quyết thời điểm đọc được và tính liên tục của workflow sau PR #89/#90. Không triển khai lại nền tiến trình đã có. Streaming không làm model chạy nhanh hơn hoặc xác nhận chất lượng sáng tác. “Đã kiểm tra” ở đây là cấu trúc/nguồn theo hợp đồng hiện có, không phải nội dung đã đúng ý hoặc đã được tác giả chấp nhận.

| Luồng | Hiện tại | Thay đổi trong bản đầu |
| --- | --- | --- |
| Tạo story plan riêng | Backend lưu plan trước critic nhưng UI đợi `result` cuối | Gửi checkpoint chứa snapshot đã lưu, mở bản đọc trong lúc chờ góp ý |
| Tạo lại story plan | Giữ đề xuất riêng, đợi kết quả cuối mới xem được | Cho đọc sớm đề xuất, giữ nguyên bản tác giả đang dùng |
| Tạo bản nháp tự động | Candidate checkpoint sau plan, outline và từng cảnh; UI polling 1,5–8 giây | Làm rõ phần vừa đọc được ngay trong card/vùng đọc hiện có; giữ vị trí đọc, theo dõi và cảnh đang sửa; đo độ trễ trước khi quyết định đổi polling |
| Làm rõ, review, viết thử cảnh, phác thảo ảnh | Stream tiến độ rồi trả kết quả hoàn chỉnh | Giữ giao thức/hành vi hiện tại; chạy hồi quy các luồng dùng chung parser |

Không đưa vào bản đầu: token preview, parser JSON dở dang, WebSocket/SSE mới, thay provider/model/prompt, migration SQLite, tự retry AI hoặc mở khóa sửa trong lúc critic đang chạy. Không đổi tiêu chí nghiệm thu #7/#22/#26 hoặc ngân sách chờ hiện có.

## 2. Trải nghiệm cần đạt

1. Người dùng chọn tạo plan; các chỉnh sửa đang có được lưu theo hàng đợi hiện tại trước khi gọi AI.
2. Trong lúc planner chạy, giao diện tiếp tục hiển thị tiến độ thật.
3. Khi plan hợp lệ đã được lưu, nội dung xuất hiện trong vùng đọc riêng với nhãn **“Story plan đã lưu · Đang góp ý”**. Tạo lại dùng nhãn **“Đề xuất Story plan đã lưu · Đang góp ý”**. Chưa dùng “Toàn bộ nháp sẵn sàng” cho checkpoint này.
4. Người dùng đọc được plan trong khi critic chạy. Chưa cho nhận đề xuất hoặc sửa preview trong thời gian này; các khóa hành động xung đột hiện tại tiếp tục áp dụng.
5. Critic thành công: `result` cập nhật dự án bằng cơ chế nhận kết quả hiện có; giữ cùng vùng đọc, cập nhật trạng thái và bổ sung góp ý tại chỗ. Không hủy/remount vùng đang đọc hoặc tạo hai bản trùng nhau; giữ vị trí cuộn, focus và phần đang xem.
6. Critic lỗi: nếu API trả dự án với `critic_status=failed`, vẫn nhận trạng thái đã lưu và cho dùng các đường phục hồi hiện có. Nhãn phân biệt **“Đã giữ bản nháp; chưa có góp ý hợp lệ”** với thành công toàn thao tác.
7. Stream mất kết nối hoặc trả `error` sau checkpoint: giữ bản đọc gần nhất, báo **“Đã nhận bản nháp đã lưu; chưa rõ kết quả góp ý”**. Mở lại dự án bằng GET theo đường phục hồi hiện có khi buffer đã an toàn; không tự gọi lại planner.
8. Luồng tạo nháp chính tái sử dụng reader/card hiện có. Hiển thị **“Cảnh 1 đã lưu · Đang viết cảnh 2”** khi phù hợp, và chỉ dùng **“Toàn bộ nháp sẵn sàng”** theo điều kiện run/candidate hiện hành. Nội dung mới không tự đổi phần người dùng đang đọc, nhận nháp hoặc bật lại theo dõi sau khi họ chủ động tạm dừng. Giữ bước cha cố định, tiến trình con gọn và mở đúng cảnh khi nhận nháp.

Giữ đúng hai hành vi đang có: lần đầu chưa có draft thì backend lưu bản đầu; khi đã có draft, plan mới là đề xuất và chỉ thay bản đang viết sau thao tác nhận của tác giả. Đọc preview không phải thao tác nhận.

## 3. Hợp đồng stream và tương thích

Tiếp tục dùng POST + Fetch ReadableStream và `application/x-ndjson`. Heartbeat dòng trống mỗi 15 giây và deadline im lặng 45 giây ở client giữ nguyên; deadline này không phải tổng thời gian cho phép chạy AI.

Thêm lựa chọn `POST /api/projects/{id}/plan/stream?checkpoints=true`. Mặc định không phát event mới để các client đang kiểm tra chặt ba loại event vẫn hoạt động. Chỉ client mới của thao tác `plan` bật lựa chọn này; các thao tác khác giữ URL hiện tại. Backend cũ bỏ qua query bổ sung thì client mới vẫn chờ `result` như trước, không tự gửi lại request để dò hỗ trợ.

Event bổ sung, không kết thúc stream:

```json
{
  "type": "checkpoint",
  "stage": "plan_checkpoint",
  "generation_id": "<ID plan vừa lưu>",
  "project": "<ProjectResponse dạng object, cùng cấu trúc với result.project>"
}
```

`project` trong ví dụ là ký hiệu mô tả; payload thật phải là object được serialize từ snapshot đã lưu, không phải chuỗi. Dùng lại `ProjectResponse` và validator project; không tạo một schema plan thứ hai. Revision nguồn, content nguồn và ý đồ tác giả lấy từ `plan_generations` của generation tương ứng.

- Chỉ phát sau khi validate planner output và `save_project(..., "plan_checkpoint")` thành công, trước khi critic được gọi. Planner hoặc lưu thất bại thì không có checkpoint.
- Serialize snapshot ngay lúc phát; critic sửa object ở bước sau không được làm biến đổi payload checkpoint đã xếp hàng.
- Một lượt plan chỉ phát một checkpoint nội dung. `progress` vẫn phản ánh các bước thật; chỉ `result` hoặc `error` kết thúc stream.
- Client kiểm tra project ID, generation ID có trong snapshot, revision checkpoint mới hơn revision đã gửi và `source_revision` khớp revision đã gửi. Trong bản đầu checkpoint phải có `critic_status=pending`.
- Event checkpoint sai schema/nguồn là lỗi giao thức, không dùng làm nội dung. Event trùng hợp lệ không thêm một bản đọc hoặc làm lùi revision; generation khác trong cùng lượt là lỗi giao thức.
- Không tăng revision chỉ vì phát event, không thêm lần lưu hoặc gọi model. Dữ liệu khôi phục vẫn là project SQLite; stream và dataset không phải recovery store mới.

## 4. Backend

| File | Công việc |
| --- | --- |
| `backend/app/application/progress.py` | Dùng listener theo request hiện có để phát checkpoint; helper mới nếu cần phải không phụ thuộc schema API |
| `backend/app/api/routes/projects.py:stream_project_operation` | Nhận query opt-in và chỉ bật checkpoint cho `plan` |
| `backend/app/api/routes/projects.py:project_stream` | Chuyển tiếp checkpoint khi đã opt-in, tiếp tục đọc sau event; giữ heartbeat, xử lý lỗi và hoàn tất lưu khi mất kết nối |
| `backend/app/api/routes/projects.py:plan_project/keep_plan` | Phát snapshot cùng generation ID ngay sau checkpoint bền vững; không đổi logic bản đầu/đề xuất/critic/CAS |
| `backend/tests/test_projects.py`, `test_plan_recovery.py` | Bổ sung ca opt-in, thứ tự phát, lỗi, mất kết nối và revision xung đột |

Không thay `StructuredProvider`, OpenAI/Ollama adapter hoặc `RecordingProvider`. Các bước model và dataset tiếp tục có cùng input, output, nguồn, trạng thái và số lần gọi. Luồng HTTP không stream vẫn trả `ProjectResponse` như hiện tại.

## 5. Frontend và bảo vệ bản đang viết

| File | Công việc |
| --- | --- |
| `frontend/app/projectsApi.ts` | Kiểu checkpoint, callback riêng tùy chọn; bật query khi caller yêu cầu checkpoint cho plan; validate event; Promise chỉ resolve ở `result` |
| `frontend/app/Workspace.tsx` | Giữ checkpoint trong state đọc riêng, gắn với project/lượt thao tác; hiển thị sớm, xử lý terminal và recovery |
| `frontend/app/DraftRunPanel.tsx`, `draftWorkflowState.ts` | Tái sử dụng phần đọc/card của draft run, làm rõ nội dung vừa sẵn sàng và trạng thái toàn bộ nháp; giữ theo dõi và cảnh đích khi nhận nháp |
| `frontend/app/progressState.ts`, `OperationProgress.tsx` | Nhãn phân biệt đã có bản để đọc, đang góp ý, thiếu góp ý và chưa rõ kết quả; chỉ sửa phần cần thiết |
| `frontend/app/storyWorkspace.css` | Vùng đọc responsive nếu kiểu hiện tại chưa đủ; không xây lại editor/layout |
| `frontend/tests/progress.cjs`, browser test checkpoint phù hợp | Parser, state, tương thích, bảo toàn buffer và trải nghiệm trước terminal |

Callback checkpoint không gọi `accept()`, `autosave.accept()`, `setProject()` hoặc `setSaved()`. Nó chỉ cập nhật vùng đọc. Không autosave preview, đưa vào export hoặc gắn feedback đang dùng cho plan mới. Nhãn “đã lưu” chỉ nói về snapshot backend; trạng thái buffer tác giả tiếp tục do autosave quản lý.

Mỗi thao tác frontend có token cục bộ và project ID; callback và kết quả cuối chỉ tác động khi còn thuộc thao tác/màn đang hoạt động. Đổi dự án, tạo lượt mới hoặc unmount vô hiệu hóa lượt cũ và xóa preview khỏi màn mới. Đây là token UI, không phải request ID bền vững hoặc bảo đảm idempotency cho `/plan`.

Nếu kết quả terminal gặp buffer đã thay đổi, dùng cơ chế bảo toàn buffer/recovery thay vì thay cả project. Preview sau lỗi có thể tiếp tục đọc khi tác giả sửa bản chính, nhưng phải ghi rõ nó thuộc nguồn lúc tạo, không còn mặc định là bản hiện tại. Nút nhận/mở lại vẫn kiểm tra dirty, revision và source như hiện có.

Thông báo trạng thái dùng `aria-live=polite`; không đọc lại toàn bộ plan khi trạng thái critic đổi. Không tự chuyển focus hoặc cuộn theo từng event. Kiểm tra desktop và mobile, bàn phím và nhãn đọc màn hình liên quan.

Vùng đọc sớm phải nằm ngoài vùng `fieldset inert` đang khóa khi busy, hoặc có cấu trúc khóa riêng chỉ áp dụng cho thao tác sửa. Người dùng vẫn đọc, cuộn và dùng bàn phím khi critic chạy; các hành động sửa/nhận xung đột tiếp tục bị khóa. Giữ vùng đọc ổn định từ checkpoint đến terminal; không mở thêm một reader song song cho draft run.

## 6. Thứ tự thực hiện và điểm bàn giao

| Task | Phụ thuộc | Bàn giao và điều kiện xong |
| --- | --- | --- |
| SI-00 — Xác nhận baseline — Đã hoàn tất 02/11/2026 | Không | `dev` tại `fd71196` sau PR #89/#90; conflict `workflow.py` đã xử lý, checkout cục bộ đồng bộ với `origin/dev`. CI backend/frontend đạt trên head đã review; giữ bản nháp, tiến độ và các tệp local |
| SI-01 — Backend checkpoint opt-in — Đã triển khai local | SI-00 | Event phát sau commit lưu và trước critic; mặc định giữ giao thức cũ; test thứ tự, CAS, failure và disconnect đạt |
| SI-02 — Parser và vùng đọc ổn định — Đã triển khai local | SI-01 | Đọc được plan trước terminal và khi busy; giữ cùng vùng đọc sau terminal, editor/autosave và nguồn riêng; draft run dùng lại reader/card; kiểm tra parser và HTTP/browser hẹp đạt |
| SI-03 — Hồi quy và bằng chứng | SI-02 | Kiểm chứng lỗi/mạng/hai tab, luồng tạo nháp từng cảnh, thời gian tới nội dung đầu tiên; cập nhật tài liệu theo hành vi đã giao |

Đóng gói SI-01 và SI-02 thành một thay đổi chức năng hoàn chỉnh có test đi kèm. SI-03 xác nhận khả năng bàn giao; không coi backend-only hoặc parser-only là đã triển khai xong trải nghiệm. Các mã SI là checklist trong issue tổng, không yêu cầu tạo thêm issue/chat riêng. Chưa gán người hoặc lịch cố định.

SI-00 đã hoàn tất; conflict ghi nhận ngày lập kế hoạch không còn là việc chặn SI-01. Baseline triển khai là `fd71196a915ae870b629601c2d6076f9d0b6d4fb` trên `dev`:

- [PR #89](https://github.com/thomasMinh1995/firstframe-ai/pull/89) đã merge các sửa workflow, bảo toàn tiến độ và sửa cảnh tại chỗ. Conflict cũ ở checkout `dev` đã được xử lý khi đồng bộ; giữ cả `ai_suggestions` và các bước tiến trình trong `LLMReasoningLayer.reason`.
- [PR #90](https://github.com/thomasMinh1995/firstframe-ai/pull/90) đã merge phần tiến trình còn thiếu và cập nhật tài liệu. [CI backend/frontend](https://github.com/thomasMinh1995/firstframe-ai/actions/runs/41387314151) đạt trên head `7e63f426d588a3c0dd044a085ef1c9137bc21e14`, được squash vào baseline trên; 18 kiểm tra backend hẹp dùng provider giả và bộ kiểm tra tiến trình frontend đã đạt. Test nhánh clarify từng kỳ vọng chuỗi sự kiện cũ đã được sửa trước khi merge.
- Đối chiếu sau đồng bộ xác nhận bản nháp, tiến độ đã lưu và 1.356 tệp local không đổi; 8 tệp staged gốc có bản sao lưu. Không gọi model thật hoặc chạy lại QA workflow toàn bộ cho việc xác nhận này.

Các bằng chứng trên xác nhận baseline. SI-01/SI-02 hiện là thay đổi chưa commit trên nền `fd71196`; bằng chứng kiểm tra hẹp nằm ở báo cáo liên kết đầu tài liệu. SI-03 vẫn chờ các ca bàn giao còn lại và số đo riêng; không suy nghiệm thu toàn bộ hoặc hiệu quả model thật từ các fixture đã chạy.

## 7. Ma trận kiểm thử bắt buộc

| Nhóm | Ca và kết quả cần chứng minh |
| --- | --- |
| Phát tăng dần thật | Fake critic chặn bằng barrier: client nhận checkpoint và đọc đúng plan khi critic chưa được nhả; DB đã chứa cùng generation/revision |
| Tương thích | Không opt-in chỉ có `progress/result/error`; opt-in không gây thêm model call/lần save; HTTP thường giữ response; client mới gặp stream cũ vẫn hoàn tất |
| Lỗi trước checkpoint | Planner lỗi/JSON sai hoặc save conflict không phát checkpoint và không tạo bản đọc giả |
| Lỗi sau checkpoint | Critic timeout/JSON sai vẫn đọc và mở lại được plan; terminal `failed` không báo đã có góp ý hợp lệ |
| Mất kết nối | Ngắt sau checkpoint hoặc thiếu terminal giữ preview/buffer; heartbeat reset inactivity timer; backend giữ chính sách hoàn tất lưu; không retry planner |
| Đồng thời | Tab khác lưu trong lúc critic chạy thì không bị ghi đè; source/revision đổi không nhận đề xuất như còn hiệu lực; terminal muộn không cập nhật màn khác |
| Parser | UTF-8 tiếng Việt chia chunk, heartbeat, nhiều event/chunk, dòng cuối không newline, checkpoint sai ID/revision/schema, trùng checkpoint và stream không có result |
| Quyền tác giả | Bản đầu và tạo lại đều đọc sớm; tạo lại không thay draft/feedback cũ; nhận sau terminal hoặc phục hồi vẫn qua kiểm tra source/revision; preview không vào autosave/export |
| Browser | Desktop 1280px, mobile 390px: nội dung xuất hiện trước critic, đọc/cuộn/bàn phím hoạt động khi busy; terminal giữ vùng đọc, scroll/focus và phần đang xem; failure giữ nội dung và hướng dẫn phục hồi đúng |
| Draft run hiện có | Fixture 2 và 6 cảnh: thấy checkpoint plan/outline/cảnh trước khi toàn run xong; trạng thái không báo toàn bộ sẵn sàng sớm; không tự đổi phần đọc/bật lại theo dõi; nhận nháp vẫn mở đúng cảnh; polling không gọi AI hoặc ghi đè candidate dirty; cảnh lỗi giữa chừng giữ phần đã lưu |
| Hồi quy dùng chung | Analyze/clarify/review, scene suggestions, screenplay proposal/review và sketch vẫn dùng parser bình thường; tour và trạng thái lưu không bị sai |

Test đọc `response.text` sau khi request hoàn tất chỉ chứng minh thứ tự payload, không chứng minh nội dung đã tới người đọc sớm. Cần cả test iterator có barrier và browser trên backend fixture qua HTTP thật để phát hiện buffering. Dùng SQLite/dataset tạm, không ghi vào dữ liệu ứng dụng thật.

Khi triển khai, chọn test backend liên quan, frontend contract/autosave/candidate-autosave/progress/follow/adoption, TypeScript và production build. Ưu tiên hồi quy hẹp theo helper/parser bị đổi; CI chuẩn của repository vẫn áp dụng khi có PR sau này. Không tự chạy QA workflow toàn bộ hoặc gọi model thật từ kế hoạch này. Ghi baseline failure riêng; không nới assertion hoặc sửa test không liên quan để báo xanh.

## 8. Đo hiệu quả và tiêu chí nghiệm thu

Ghi timestamp theo từng lần chạy: bắt đầu thao tác, backend hoàn tất lưu checkpoint, UI render nội dung đầu tiên và terminal. Dùng đồng hồ monotonic trong từng process; chỉ tính chênh lệch trong cùng miền đồng hồ. Đo end-to-end từ browser, không trừ trực tiếp timestamp browser với backend.

- `time_to_readable_content`: từ thao tác bắt đầu tới khi plan/cảnh đầu tiên đọc được trên UI; đây là chỉ số chính.
- `total_operation_time`: tới terminal, giữ riêng thời gian lưu trước AI và thời gian model nếu có.
- `checkpoint_to_render`: đo trên fixture hoặc bằng cách liên kết trace phù hợp; không bỏ qua ảnh hưởng buffering.
- Với draft runs, đo thêm độ trễ từ candidate revision đã lưu tới khi UI hiện checkpoint, để đánh giá polling.
- Lưu cả lỗi, thiếu checkpoint và thiếu terminal. Báo số mẫu và số lỗi; chỉ báo phân vị khi đủ mẫu có ý nghĩa, không loại ca thất bại để làm số liệu đẹp.

Fixture kiểm soát phải chứng minh plan đã hiện trong khi critic còn bị chặn. Số đo model thật là bước riêng khi được yêu cầu: đóng băng brief/cấu hình, ghi khoảng đọc sớm và ngân sách tổng; không thêm lượt model chỉ để đo baseline. Hành vi cũ lấy mốc terminal, hành vi mới lấy mốc render checkpoint trong cùng lượt. Một cấu hình chưa đo phải ghi là chưa có bằng chứng; kiểm chứng fixture không chứng minh mức cải thiện thời gian chờ thực tế.

Hoàn tất bản đầu khi SI-01–SI-03 đạt, các ca bảo vệ dữ liệu/tương thích qua, và có bằng chứng HTTP/browser về hiển thị trước terminal. Kiểm chứng chức năng bằng fixture và hiệu quả thực tế bằng model phải ghi riêng; thiếu bằng chứng model không được tuyên bố đã giảm thời gian chờ thực tế hoặc đạt nghiệm thu live.

Ngân sách hiện có vẫn là làm rõ ≤45 giây, plan kèm critic ≤120 giây, review ≤60 giây và demo ≤5 phút. Streaming không tăng các giới hạn này và không chứng nhận chất lượng sáng tác.

## 9. Bàn giao, rollback và bước tiếp theo

- Báo cáo triển khai lưu tại `docs/testing/streaming-interfaces.md`: commit/cấu hình, ca test, ảnh UI trước terminal, số lần gọi và timings/thất bại. Đây là tài liệu sẽ tạo khi triển khai, chưa phải bằng chứng đang có.
- Cập nhật README để phân biệt stream tiến độ, nội dung qua checkpoint và token streaming; sửa dòng giới hạn hiện nói chưa có streaming. Chỉ chỉnh các hướng dẫn/tour bị ảnh hưởng thực sự.
- Tắt query opt-in ở client sẽ quay về chờ `result`; giữ dữ liệu và checkpoint hiện có. Backend trước có thể chạy cùng client mới theo fallback nêu trên; backend mới mặc định phục vụ client cũ. Không có migration cần đảo ngược.
- Phần nhãn/trạng thái đọc của draft run không thay dữ liệu và có thể revert riêng; giữ polling, quyền nhận nháp và cơ chế theo dõi hiện hành.
- Xem xét giai đoạn token preview cho viết thử cảnh chỉ khi số đo cho thấy chờ planner/cảnh đầu vẫn cản luồng viết và preview giúp người dùng đọc sớm. Khi đó lập thiết kế riêng cho provider stream, parser output, scope validation, recording và phục hồi nội dung chưa hoàn chỉnh.
- Thay polling của draft run chỉ khi độ trễ đã đo gây vấn đề; không mặc định mở rộng bản đầu sang một hệ thống event bền vững mới.

Điểm dừng: giao được nội dung đã lưu trước khi góp ý hoàn tất và giữ an toàn bản tác giả. Không kéo thêm tối ưu model, framework streaming hoặc chuẩn hóa toàn bộ workflow vào thay đổi này.
