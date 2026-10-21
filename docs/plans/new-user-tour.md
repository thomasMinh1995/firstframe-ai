# Kế hoạch: Tour hướng dẫn người dùng mới

- Trạng thái: đã triển khai MVP frontend trên nhánh `codex/new-user-tour`; chờ review và pilot người mới.
- Issue: [Feature #22](https://github.com/thomasMinh1995/firstframe-ai/issues/22).
- Kiểm chứng và cách chạy: [Tour người dùng mới](../testing/new-user-tour.md).

## Mục tiêu và bối cảnh

Giúp người mới biết bắt đầu ở đâu, hiểu các lựa chọn sáng tác thuộc về mình,
và đi qua một vòng phát triển câu chuyện: tạo dự án, nhập ý tưởng, làm rõ,
tạo bản phát triển, tự sửa và nhận phản hồi.

Ảnh tham khảo định hướng cách trình bày: nền tối, vùng đang hướng dẫn được
làm nổi bật, thẻ nội dung ngắn và điều hướng từng bước. Nội dung tour bám vào
FirstFrame, không sao chép workflow tổng quan nghiên cứu trong ảnh.

MVP hiện có workspace Next.js/React tại `frontend/app/page.tsx`, lưu dự án
cục bộ qua backend và chưa có tài khoản. Phần hỏi đáp chỉ xuất hiện khi có
`analysis` và brief không bị sửa; phần bản phát triển cần có `draft`.
Tour phải đi theo các điều kiện này, không yêu cầu sẵn mọi phần trên màn hình.

## Phạm vi MVP

- Một tour tiếng Việt cho workspace chính `/`, gồm sáu bước theo ba chặng.
- Lời mời bắt đầu, spotlight, thẻ hướng dẫn, chuyển bước, đóng/bỏ qua,
  tiếp tục và xem lại.
- Lưu tiến độ theo trình duyệt; thích ứng dữ liệu dự án đang mở.
- Hỗ trợ mobile, bàn phím và trình đọc màn hình.
- Giải thích đúng việc lưu, gọi AI và độ mới của phản hồi.

Không bao gồm tour riêng cho `/demo` hoặc `/datasets`, mascot/animation mới,
dịch toàn bộ giao diện, đồng bộ tài khoản, dashboard analytics, thay đổi
backend, tự điền ý tưởng hoặc tạo nội dung mẫu. Nút demo hiện có vẫn là lựa
chọn cho người muốn xem trước workflow mà chưa gọi AI.

## Nội dung sáu bước

| Bước / chặng | Vùng hướng dẫn | Nội dung dự kiến và điểm thực hành |
| --- | --- | --- |
| 1 / Bắt đầu | Nút Dự án mới | “Tạo không gian riêng cho câu chuyện của bạn. Bạn có thể lưu và quay lại viết tiếp.” Chưa có dự án thì dừng để người dùng tự tạo. |
| 2 / Bắt đầu | Ý tưởng và điều muốn giữ | “Kể một tình huống hoặc kỷ niệm, kèm điều bạn muốn giữ. Dùng Lưu thay đổi để quay lại viết tiếp, kể cả khi chưa chạy AI.” Cho nhập tại bước này; không tự điền hoặc lưu. |
| 3 / Bắt đầu | Ngôn ngữ đầu ra và Cùng làm rõ ý tưởng | “Chọn ngôn ngữ cho nội dung AI, rồi cùng làm rõ những lựa chọn sáng tác.” Giải thích chọn ngôn ngữ không tự dịch nội dung đã có. Người dùng tự bấm làm rõ; thao tác hiện có sẽ lưu trước khi gọi AI. |
| 4 / Làm rõ | Những lựa chọn của bạn và nút tạo bản phát triển | “Trả lời theo ý bạn. Nếu chưa chắc, chọn Để quyết định sau trước khi tạo bản phát triển.” Người dùng tự trả lời và tạo bản phát triển. |
| 5 / Viết và sửa | Bản phát triển đang làm việc | “Đây là bản để bạn tiếp tục viết. Bạn có thể sửa tên phim, tóm tắt và từng phần câu chuyện.” Nêu đây là bản phát triển, chưa phải kịch bản theo cảnh hoàn chỉnh. |
| 6 / Viết và sửa | Thanh lưu | “Nhận phản hồi trên bản hiện tại sẽ lưu bản này trước khi gửi AI; bạn tự quyết định cách sửa. Sau khi sửa tiếp, phản hồi cũ thuộc bản trước — hãy lưu thay đổi trước khi rời đi.” Không yêu cầu có feedback hoặc chạy review để kết thúc hướng dẫn. |

Mỗi thẻ có tiêu đề, một hoặc hai câu và đúng một vùng spotlight. Các control
được nhắc thêm chỉ là nội dung giải thích, không tạo bước con hoặc spotlight
tự chạy. Không dùng điểm AI làm điều kiện hoàn thành.

### Anchor và nơi trả focus

Các giá trị dưới đây là `data-tour` cần bổ sung, đồng thời là ID bước ổn định.
Chỉ anchor duy nhất, đã mount, còn kết nối DOM và có kích thước mới được dùng.
Điều kiện chung để mở overlay là tải workspace thành công và `busy === null`.

| Bước / ID | Phần tử làm spotlight | Điều kiện bổ sung | Focus sau khi chọn Thực hành |
| --- | --- | --- | --- |
| 1 / `new-project` | Nút Dự án mới | Luôn có trên workspace đã tải | Chính nút này; nếu đã có dự án, copy nhắc nút thật sẽ lưu dự án đang mở trước khi tạo dự án khác |
| 2 / `idea` | Ô `#idea` | Có project | `#idea`; thẻ nhắc ô điều muốn giữ ở bên dưới |
| 3 / `language` | Select `#response-language` | Có project | `#idea` nếu ý tưởng trống; nếu không, nút làm rõ khi nó hiện và enabled; nếu đã có analysis hợp lệ thì focus select |
| 4 / `choices` | Tiêu đề Những lựa chọn của bạn | Có analysis và `!briefChanged` | Câu trả lời trống đầu tiên; nếu đã đủ câu trả lời hoặc không có câu hỏi, focus nút tạo bản phát triển |
| 5 / `draft` | Tiêu đề Bản phát triển đang làm việc | Có draft | `#draft-logline`; không phụ thuộc số phần trong draft |
| 6 / `save` | `.save-toolbar` | Có draft và project | Không có nút Thực hành ở bước cuối; dùng Hoàn tất hướng dẫn |

Các tiêu đề/vùng không phải control có `tabIndex=-1` để làm focus dự phòng.
Không spotlight toàn bộ panel draft dài hơn viewport. Thanh lưu có thể được
highlight dù nút Lưu thay đổi đang disabled vì không có sửa mới; giải thích
“Đã lưu” và tuyệt đối không bật nút để phục vụ tour. Khi hoàn tất, focus nút
Lưu thay đổi nếu enabled, nếu không focus vùng trạng thái lưu.

Không tìm được anchor dù điều kiện dữ liệu cho phép: đóng overlay, chuyển
`paused`, hiện nhắc “Chưa thể mở bước này” cạnh nút hướng dẫn, cho thử lại
hoặc bỏ qua. Không poll vô hạn, không dùng tọa độ cũ hoặc tự đánh dấu hoàn tất.

## Khởi động, thực hành và tiếp tục

### Lần đầu và người đã có dự án

- Chỉ xác định điều kiện mời sau khi tải danh sách và dự án thành công.
  Lỗi kết nối không được xem là chưa có dự án.
- Nếu chưa có dự án và chưa có trạng thái tour, tự hiện lời mời ngắn với
  “Bắt đầu hướng dẫn” và “Bỏ qua”. Chỉ mở spotlight sau khi người dùng chọn bắt đầu.
- Nếu đã có dự án, không tự bật overlay. Luôn có nút “Hướng dẫn sử dụng”
  tại đầu workspace để chủ động mở.
- Lời mời và tour đều có thể đóng; đóng, Escape hoặc bỏ qua đều ngừng các
  hướng dẫn tự động còn lại cho đến khi người dùng chủ động mở lại.
- Không tự phát lại chỉ vì mở ứng dụng lần nữa hoặc thay đổi phiên bản
  nội dung tour. Giữ lựa chọn đã đóng/bỏ qua/hoàn thành khi nâng phiên bản.

### Điều hướng và điểm dừng thực hành

- Thẻ có “Trước”, “Bỏ qua”, nút đóng và nhãn “Bước N/6”. Số N là vị trí
  cố định của bước, không phải tỷ lệ công việc đã hoàn thành. Trước đi tới
  bước khả dụng gần nhất; tại bước 1 thì disabled. Không che bước chưa xem
  bằng cách tự tính nó là đã hoàn thành khi vào từ bước 4 hoặc 5.
- Bước 1–5 có “Thực hành” để đóng overlay và focus theo bảng anchor.
  Nút “Tiếp” chỉ hiện khi đích trong bảng dưới khả dụng; ở điểm chờ dữ liệu
  thì Thực hành là CTA chính. Bước 6 có “Hoàn tất hướng dẫn”.
- Khi overlay đóng để thực hành, một thanh nhỏ cạnh nút Hướng dẫn sử dụng
  cho phép “Tiếp tục hướng dẫn” và “Bỏ qua”. Không dùng `notice` hiện có:
  `useEffect` theo `dirty` đang xóa notice khi người dùng gõ. Nút/thanh tour
  đặt ngoài fieldset bị disabled khi busy để Bỏ qua vẫn hoạt động.
- Không nút tour nào gọi `persist()`, `action()`, tạo dự án hoặc khôi phục
  phiên bản. Tác giả thao tác qua nút thật; quy tắc lưu trước AI vẫn giữ nguyên.

| Bước đang xem | Tiếp khi xem | Sau Thực hành, khi nào cho tiếp tục? |
| --- | --- | --- |
| 1 | Bước 2 nếu đã có project; không có thì chỉ Thực hành | Khi tạo được project qua nút thật. Tạo thành công từ bước 1 là ngoại lệ có chủ đích cho quy tắc đổi dự án: gắn tour với ID mới rồi cho tiếp tục bước 2 |
| 2 | Bước 3, kể cả ý tưởng trống | Ngay khi đã đóng overlay: cho tiếp tục bước 3 bằng click, không cần thay chữ hoặc lưu; nút làm rõ thật vẫn kiểm tra ý tưởng như hiện tại |
| 3 | Bước 4 nếu analysis hợp lệ; nếu chưa thì chỉ Thực hành | Chờ kết quả analyze thành công được chấp nhận; sau đó cho tiếp tục bước 4. Nếu analysis đã hợp lệ, cho tiếp tục ngay, không gọi analyze lại |
| 4 | Bước 5 nếu draft đã tồn tại; nếu chưa thì chỉ Thực hành | Chờ plan thành công nếu chưa có draft. Nếu đã có draft, cho xem bước 5 ngay và ghi rõ đây là bản đã có, không xác nhận bản vừa được tạo lại |
| 5 | Bước 6 | Ngay khi đóng overlay: cho tiếp tục bước 6 bằng click, không yêu cầu sửa, lưu hay review |
| 6 | Hoàn tất hướng dẫn | Ghi completed; không chạy save/review và không chờ feedback |

Không tự mở overlay khi thao tác kết thúc. “Tiếp tục” luôn kiểm tra lại đích
và `busy` tại thời điểm click. Với mọi nút Tiếp/Tiếp tục định vào bước 4–6,
nếu analysis không còn hợp lệ thì trở về bước 2 trước, kể cả draft vẫn tồn tại.
Khi đang bận, thanh thực hành vẫn cho Bỏ qua nhưng tắt Tiếp tục; không hủy
request đang chạy. Lỗi chuyển về `paused` tại bước thực hành, không tự tiến
bước. Người dùng có thể tiếp tục xem bước đó
hoặc tự thử lại bằng nút thật; tour không giữ họ trong trạng thái chờ vô hạn.

Reload/rời trang hủy lượt chờ trong bộ nhớ. Khi quay lại chỉ mời tiếp tục
theo dữ liệu đã đọc, không phát lại tác vụ. Đổi/tạo dự án ngoài ngoại lệ bước
1 làm tour paused, bỏ lượt chờ cũ ngay từ lúc người dùng chọn thao tác;
nếu chuyển thất bại vẫn giữ buffer và chỉ mở lại khi người dùng yêu cầu.

### Dữ liệu có điều kiện và mở lại

“Analysis hợp lệ” trong tour nghĩa là đúng điều kiện UI đang dùng:
`project.analysis !== null && !briefChanged`; tour không tự đánh giá nội dung AI.
Khi chọn bắt đầu/xem lại hoặc chuyển dự án, chọn điểm vào theo thứ tự:

1. Không có project: bước 1.
2. Có project nhưng brief đang sửa hoặc thiếu analysis: bước 2, kể cả có draft cũ.
3. Analysis hợp lệ nhưng thiếu draft: bước 4.
4. Analysis hợp lệ và có draft: bước 5, kể cả chưa có feedback.

Khi đang waiting, Tiếp tục dùng bảng chuyển bước; khi paused hoặc mở lại sau
reload cùng dự án, ưu tiên bước đã lưu nếu còn khả dụng, nếu không thì dùng
thứ tự trên. Riêng briefChanged hoặc thiếu analysis ưu tiên
bước 2 trước tiến độ cũ ở bước 4–6. Ví dụ đang ở bước 5 rồi đổi ý tưởng:
mở lại phải hướng dẫn làm rõ, không dẫn thẳng tới draft cũ vẫn còn trên UI.
Sau reload không suy đoán một tác vụ thành công từ việc có draft sẵn; mở lại
chỉ để giải thích dữ liệu đang đọc, không phát thông báo “vừa tạo thành công”.

Bước 3 vẫn khả dụng với analysis hợp lệ vì anchor là select ngôn ngữ;
copy lúc này nhắc có thể tiếp tục xem lựa chọn mà không chạy lại AI.
Nếu không có câu hỏi, bước 4 nói rõ có thể tạo bản phát triển ngay.
Nếu có draft từ trước, bước 4 dùng đúng nhãn tạo lại/giữ phiên bản cũ hiện có.
Không tự bấm nút tạo lại để xem bước 5.

Chỉ bấm Hoàn tất ở bước 6 mới ghi completed. Thoát trước đó là dismissed,
kể cả người dùng đã tự làm hết workflow. Completed chỉ xác nhận đã kết thúc
lượt hướng dẫn, không chứng nhận đã xem đủ sáu bước hoặc hoàn thành câu chuyện.

## Trạng thái và lưu tiến độ

Dùng một record `localStorage` với key `firstframe:onboarding`, chứa
`version: 1`, `status`, `stepId` (sáu ID trong bảng anchor) và `projectId`
(ID hiện tại, hoặc null trước khi tạo). Trạng thái được định nghĩa như sau:

| Trạng thái | Ý nghĩa / cách vào |
| --- | --- |
| Chưa có record | Chưa tương tác lời mời; chỉ xét mời tự động sau tải workspace thành công |
| `active` | Overlay đang mở do người dùng chọn Bắt đầu/Tiếp tục/Xem lại |
| `waiting` | Đã chọn Thực hành; giữ bước xuất phát, thanh tiếp tục tra bảng chuyển bước bằng dữ liệu hiện tại |
| `paused` | Gián đoạn do reload, lỗi, đổi dự án hoặc mất anchor; giữ bước để chủ động mở lại |
| `dismissed` | Đóng, Escape, Bỏ qua từ lời mời/thẻ/thanh thực hành; không tự nhắc lại |
| `completed` | Bấm Hoàn tất ở bước 6; chỉ mở lại qua nút hướng dẫn |

Nếu đóng lời mời trước bước 1, ghi dismissed với `stepId: new-project`.
Lưu theo thay đổi bước/trạng thái/dự án, không ghi theo mỗi ký tự hoặc mỗi
lần cuộn. Lượt request đang chờ chỉ nằm trong bộ nhớ, không đưa vào storage.

Đọc storage sau khi mount để tránh lệch hydration. Kiểm tra cấu trúc và
giá trị trước khi dùng; record hỏng thì bỏ qua an toàn. Khi không đọc/ghi
được storage, tour vẫn chạy bằng state trong phiên, không chặn workspace.
Nếu đọc thất bại thì chỉ mở thủ công vì chưa biết lựa chọn trước đó.
Sau reload, `active`/`waiting` được coi là paused; không phục hồi lượt request.
MVP chỉ ghi/đọc schema version 1. Với version khác hoặc record hỏng, không
tự bật lời mời; chỉ để nút hướng dẫn hoạt động và ghi record v1 khi người dùng
chủ động mở/bỏ qua. Version nội dung tương lai phải giữ lựa chọn đã đóng hoặc
hoàn thành; chưa xây hệ thống migration cho phiên bản chưa tồn tại.

Khi tab khác ghi dismissed/completed, tab hiện tại đóng overlay/thanh nhắc và
bỏ lượt chờ qua sự kiện storage. Kết quả request cũ không được ghi đè lựa chọn
này. Xóa storage khi tab đang mở cũng không tự bật lại lời mời trong phiên đó;
không cần đồng bộ bước đang xem giữa các tab.

Không lưu ý tưởng, câu trả lời, bản thảo hoặc phản hồi trong record tour.
Tiến độ thuộc trình duyệt, không phải bằng chứng nhận diện người dùng.
Đổi trình duyệt hoặc xóa storage có thể khiến lời mời xuất hiện lại.

## Giao diện và accessibility

- Dùng màu, font, nút và bo góc hiện có. Desktop đặt thẻ cạnh mục tiêu,
  có khoảng cách và đổi hướng khi gần mép viewport.
- Mobile đặt thẻ phía dưới, có chiều cao tối đa và cuộn được; giữ vùng
  đích nhìn thấy cả khi bàn phím ảo mở.
- Dùng anchor `data-tour` ổn định; không tìm mục tiêu bằng chữ hiển thị
  hoặc thứ tự DOM. Đo lại khi cuộn, resize hoặc kích thước mục tiêu đổi;
  dọn listener/observer khi đóng.
- Spotlight ở chế độ xem chỉ để quan sát. Các tương tác thực hành diễn
  ra sau khi đóng overlay, tránh vô tình bấm xuyên nền.
- Dialog có nhãn/description, focus nằm trong thẻ khi mở; Tab/Shift+Tab
  hoạt động đúng, Escape đóng và trả focus về nút mở hoặc vùng thực hành.
  Không để nền nhận focus trong khi overlay đang mở.
- Render dialog ngoài cây nền bị inert. Đóng thông thường trả focus về nút
  mở; Thực hành/Hoàn tất dùng bảng anchor. Nếu đích focus bị tháo hoặc disabled,
  dùng tiêu đề workspace có tabIndex=-1; không focus control đã mất.
- Tôn trọng giảm chuyển động; hướng dẫn không phụ thuộc riêng vào màu.
- Không mở tour trong lúc `busy`. Nếu phát sinh lỗi, đóng overlay và ưu tiên
  thông báo hiện có; lỗi không được xóa bởi nút tour. Khi hết bận, người dùng
  vẫn có thể chủ động xem hướng dẫn để sửa đầu vào dù `error` còn tồn tại
  (ví dụ lỗi 422 cần chọn ngôn ngữ); lỗi chỉ chặn lời mời tự động, không khóa trợ giúp.
- Nếu viewport quá thấp hoặc zoom lớn khiến thẻ và spotlight không cùng vừa,
  dùng dialog cuộn được trong viewport, bỏ spotlight/mũi tên tạm thời và nêu
  tên vùng đích bằng chữ. Sau Thực hành mới cuộn/focus input; không cố giữ
  bàn phím ảo mở cùng thẻ. Dọn inert/scroll lock/listener khi đóng hoặc unmount.

### Sự kiện tích hợp với workspace

`page.tsx` cung cấp `workspaceLoadState` (loading/ready/error); chỉ ready sau cả listProjects
và mở dự án cuối thành công, hoặc sau thao tác mở/tạo dự án được xác nhận.
`busy === null` không đủ vì finally của lần tải lỗi cũng đặt busy về null.
Lời mời tự động còn cần danh sách đã tải thành công và rỗng; tạo/mở thủ công
sau lỗi tải không tự chứng minh danh sách rỗng.

Chỉ phát tín hiệu tour tại các điểm sau, không thêm event bus hoặc API mới:

- `project-created`: sau POST tạo dự án trả project hợp lệ và đã được chấp nhận.
  Không phát từ PUT lưu dự án cũ chạy trước POST.
- `analysis-succeeded` / `plan-succeeded`: sau `streamProjectOperation`
  trả result hợp lệ và được workspace chấp nhận; lấy ID từ result.
  Không phát từ event progress, `accept()` dùng chung hoặc chỉ vì `busy` vừa hết.
- Lưu/review không có tín hiệu tiến bước; bước 2 và 5 dùng thao tác Tiếp tục
  của người dùng. `run()` hiện bắt lỗi rồi resolve nên không dùng
  `await run(...)` làm bằng chứng thao tác thành công.

Trong bộ nhớ, mỗi lượt thực hành chờ create/analyze/plan giữ loại thao tác,
ID dự án lúc bắt đầu (null cho tạo lần đầu), token phiên tour và token lượt
request thật. Analyze/plan phải trả đúng ID dự án. Create phải khớp lượt POST
và ngữ cảnh bắt đầu, rồi gắn tour với ID mới trả về; không so ID mới với ID cũ.
Đóng/bỏ qua/đổi dự án/unmount hủy hiệu lực token; mở tour lại tạo phiên mới
nên kết quả phiên cũ không đánh dấu bước mới thành công. Khi nhận tín hiệu,
đợi hết busy rồi kiểm tra lại anchor để
hiện nút Tiếp tục. Đây là kiểm tra cho tour, không tự gọi accept hoặc sửa luồng
lưu/nhận kết quả của workspace.

Kết quả không có tín hiệu phù hợp vẫn có thể làm dữ liệu hiện tại thay đổi.
Tour chỉ cho chủ động mở lại theo dữ liệu đó; không ghi nhận request cũ là
thành công của lượt thực hành mới hoặc tự đánh thức một tour đã đóng.
Trong waiting, chỉ bật Tiếp tục sang chặng cần dữ liệu nếu đích đã khả dụng
ngay lúc chọn Thực hành hoặc đã nhận đúng tín hiệu của lượt chờ. Không dùng
effect theo riêng sự xuất hiện của analysis/draft để suy ra thành công.
Bước 2 và 5 không cần tín hiệu request; quy tắc này chỉ áp dụng điểm chờ 1/3/4.

## Bảo toàn dữ liệu và lỗi

Mở/đóng/đổi bước chỉ thay đổi state tour, scroll và focus. Không thay
`project`, `saved`, dirty, revision, feedback freshness hoặc lịch sử.

Lỗi lưu, validation, 409 hoặc AI không làm bước thực hành thành công.
Giữ buffer và trạng thái lỗi hiện có; không tự retry, reload hoặc gọi AI
tiếp. Với kết quả mạng chưa rõ, tour không suy đoán thao tác đã hoàn tất.
Chỉ tiếp tục sau dữ liệu thành công được workspace xác nhận cho đúng dự án.

Theo dõi tour không được thêm request ghi dữ liệu, model call, dataset
recording hoặc sửa cơ chế xử lý kết quả đến muộn của workspace.

## Hướng triển khai

| Thành phần | Thay đổi dự kiến |
| --- | --- |
| `frontend/app/page.tsx` | Nút/thanh hướng dẫn độc lập notice; anchor; trạng thái tải tường minh; tín hiệu create/analyze/plan tại đúng điểm thành công và token lượt thao tác |
| `frontend/app/OnboardingTour.tsx` — mới | Overlay, spotlight, dialog, điều hướng, scroll, focus và xử lý viewport |
| `frontend/app/onboardingState.ts` — mới | Nội dung sáu bước, chọn bước khả dụng, chuyển trạng thái, đọc/ghi tiến độ có kiểm tra |
| `frontend/app/globals.css` | Style tour theo giao diện hiện có; mobile và reduced motion |
| `frontend/tests/onboarding.cjs` — mới | Kiểm tra điều kiện, chuyển trạng thái, storage và không gây tác dụng phụ |
| Tài liệu | Liên kết roadmap và checklist kiểm thử/ghi nhận kết quả khi triển khai |

Ưu tiên React/CSS và API trình duyệt hiện có, chưa thêm dependency. Không
xây framework tour dùng chung cho nhiều trang. Logic workflow và lưu dự án
tiếp tục ở nơi hiện có; tour chỉ nhận dữ liệu cần cho hướng dẫn.

## Thứ tự thực hiện và ước lượng

1. Chốt copy, anchor, hành vi đóng/tiếp tục và mẫu desktop/mobile: 0,5 ngày.
2. Dựng overlay/dialog, spotlight, focus và responsive: 1 ngày.
3. Kết nối ba chặng, điều kiện dữ liệu và lưu tiến độ: 1 ngày.
4. Kiểm thử, sửa lỗi và thử với người mới: 0,5–1 ngày.

Ước lượng ban đầu: 3–4 ngày công triển khai, chưa tính chờ người thử hoặc thay đổi
phạm vi. Không cần thay đổi backend hay gọi model thật để kiểm tra logic tour.

## Tiêu chí nghiệm thu

- [ ] Lời mời chỉ tự xuất hiện sau tải thành công, chưa có dự án và chưa từng đóng/bỏ qua/hoàn thành.
- [ ] Người đã có dự án chỉ mở tour khi chủ động chọn; điểm bắt đầu phù hợp dữ liệu.
- [ ] Sáu bước chỉ dẫn đúng control đang tồn tại; mục tiêu biến mất thì tạm dừng an toàn.
- [ ] Tạo dự án, phân tích và tạo draft thành công cho phép tiếp tục đúng chặng; lỗi không làm tiến bước.
- [ ] Analysis không có câu hỏi vẫn có hướng dẫn đúng; brief đang sửa không dẫn vào hỏi đáp cũ.
- [ ] Đóng, Escape và bỏ qua ngừng toàn bộ hướng dẫn tự động còn lại, kể cả kết quả AI đến muộn.
- [ ] Reload cho chọn tiếp tục; đổi dự án không mang bước đang chờ của dự án trước sang.
- [ ] Có thể mở lại sau bỏ qua hoặc hoàn thành, không cần sửa dự án hoặc gọi AI lại.
- [ ] Mọi thao tác của tour giữ nguyên toàn bộ buffer, dirty, revision, feedback và lịch sử.
- [ ] Tour không tạo request ghi dữ liệu/model call; thao tác thực hành qua nút thật vẫn giữ hành vi lưu trước AI.
- [ ] Storage hỏng/bị chặn không gây crash; nâng version giữ lựa chọn đã đóng/bỏ qua/hoàn thành.
- [ ] Desktop/mobile, cuộn/resize, bàn phím ảo và nội dung dài không làm thẻ tràn hoặc che vùng thực hành.
- [ ] Dùng được với bàn phím và trình đọc màn hình; focus được giữ/trả đúng, giảm chuyển động được tôn trọng.
- [ ] Nội dung phân biệt bản phát triển với screenplay, và phản hồi cũ với phản hồi cho bản hiện tại.

Các ca chuyển bước bắt buộc khi triển khai:

| Tình huống | Kết quả cần chứng minh |
| --- | --- |
| Thực hành bước 1, POST thành công từ project=null | Gắn ID mới, cho bấm tiếp tới bước 2; không bị quy tắc đổi dự án hủy nhầm |
| Thực hành bước 2/5 rồi chỉ gõ, không lưu; hoặc không sửa chữ | Có nút tiếp tới 3/6; giữ toàn bộ buffer, không chờ API và không tự lưu |
| Có draft cũ, đổi brief; hoặc đã lưu brief mới làm analysis=null | Tiếp/mở lại từ 4–6 về bước 2; không lấy sự tồn tại của draft làm bằng chứng plan thành công |
| PUT trong persist thành công, analyze/plan sau đó lỗi; hoặc nhận progress completed nhưng chưa có result | Không phát tín hiệu thành công; ở paused tại bước thực hành, giữ lỗi/bản sửa và có thể xem lại hướng dẫn |
| Đóng tour A rồi mở tour B trước khi request A trả về | Kết quả A không tiến bước hoặc tự mở/đánh thức B; chỉ chủ động đọc trạng thái hiện tại |
| Tab khác ghi dismissed/completed trong lúc đang chờ | Đóng thẻ/thanh nhắc, bỏ token; callback cũ không ghi đè trạng thái terminal |
| Auto language gây 422, error còn trên workspace | Khi hết busy vẫn mở được trợ giúp/ngôn ngữ bằng thao tác chủ động; tour không xóa error hoặc retry |
| Không có câu hỏi, draft không có section, chưa có feedback, nút lưu disabled | Focus đúng các đích dự phòng, bước 6 hoàn tất được mà không cần gọi AI |
| Anchor mất, record hỏng/version lạ, viewport thấp/zoom lớn | Không spotlight tọa độ cũ hoặc tự bật lại; có đường mở thủ công, dialog cuộn và focus dự phòng |

## Kiểm chứng khi triển khai

- Kiểm tra tự động cho chuyển trạng thái và chọn bước theo dữ liệu; dùng
  pattern TypeScript + Node assert hiện có trong `frontend/tests/progress.cjs`.
- Kiểm thử tương tác trên trình duyệt với backend/provider giả: từ trạng
  thái trống, dự án đã có analysis/draft, không có câu hỏi, lỗi lưu/AI, đổi
  dự án, reload và kết quả đến muộn.
- So sánh toàn bộ buffer trước/sau thao tác tour và theo dõi network để
  xác nhận không gọi lưu/AI. Render tĩnh không đủ chứng minh focus,
  scroll hoặc không có tác dụng phụ.
- Chạy TypeScript, production build và các frontend regression checks
  liên quan; kiểm tra accessibility và mobile trực tiếp.
- Đề xuất thử với 3–5 người mới: họ xác định được bước tiếp theo, hiểu
  quyền tự sửa và biết cách lưu/quay lại. Ghi nhận chỗ bị kẹt hoặc phải
  hỏi trợ giúp; đây là pilot dự kiến, chưa phải kết quả đã đo.

Issue chỉ hoàn thành sau khi triển khai và đạt tiêu chí nghiệm thu.
Viết plan hoặc hoàn thành lượt xem tour không đồng nghĩa hoàn thành feature.
