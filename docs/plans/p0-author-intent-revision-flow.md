# P0: Hiển thị ý đồ tác giả và nối góp ý với thao tác sửa

- Cập nhật: 25/10/2026. Ưu tiên hoàn thiện #7, cập nhật tour khi luồng sửa ổn
  định, kiểm chứng/nghiệm thu #7 rồi mới tiếp tục tám gói harness.
- Trạng thái: đã triển khai một phần qua PR #31–#32 và workspace PR #36;
  phần còn thiếu cần rà soát và nghiệm thu, không triển khai lại từ đầu.
- Issue: [P0 #7](https://github.com/thomasMinh1995/firstframe-ai/issues/7).
- Lần cập nhật này chỉ thay đổi tài liệu; không sửa code, prompt, schema hay dependency runtime.

## Mục tiêu và phạm vi

Người mới nhìn thấy AI đang dựa trên ý đồ nào, chọn một vấn đề đáng sửa, đến
đúng phần bản phát triển và tự sửa trước khi nhận góp ý mới. Thành công P0 là
hoàn thành một vòng sửa story plan có mục tiêu, chưa phải hoàn thành screenplay.

Hai phần cùng phục vụ một luồng: **Xem ý đồ → Đọc góp ý → Chọn phần cần sửa →
Tự sửa → Lưu và nhận phản hồi trên bản mới**. Không bắt người dùng điền thêm
bảng câu hỏi hoặc xác nhận ý đồ lại mỗi lần chỉ để được tiếp tục viết.

## Hiện trạng đã đối chiếu

- `ProjectResponse` có `idea`, `constraints`, `answers`, `clarifications` và
  `creator_answers()` để kết hợp câu trả lời hiệu lực; thay brief sẽ đưa lựa
  chọn cũ về lịch sử. Không cần thêm một kho lưu ý đồ khác.
- PR #31–#32 đã giao thẻ ý đồ đã lưu, nguồn feedback và vòng sửa thủ công.
  PR #36 bổ sung workspace card, hội thoại làm rõ, xác nhận trước khi tạo plan
  và góp ý cạnh card có đối chiếu nguồn. [UI đã chốt](approved-story-workspace.md)
  là nền triển khai; #35 đã hoàn thành, không thiết kế lại ba phần đã chốt.
- Đã có `CardReview`, `CardFeedback` và quote anchors của đúng snapshot.
  Một số dữ liệu vẫn đi qua `findings`/chuỗi hiển thị; phải đối chiếu từng
  yêu cầu ghép cặp, định danh mục tiêu, điều hướng và tương thích bên dưới
  với code/bằng chứng hiện có trước khi chọn phần cần bổ sung. Không coi có
  anchor đúng chữ là đã đạt toàn bộ #7 hoặc đúng nghĩa trên model thật.
- `content_key()`, `reviewed_content`, `feedback_is_current` và kiểm tra thay đổi
  chưa lưu đã có; P0 phải tiếp tục dùng cơ chế này, không coi revision bằng nhau
  hoặc tên mục giống nhau là đủ chứng minh phản hồi còn đúng.
- PDF đang là kế hoạch riêng ở [#5](https://github.com/thomasMinh1995/firstframe-ai/issues/5).
  Hai tính năng P0 này không phụ thuộc PDF và không thay phạm vi bản xuất.

## Ưu tiên và mốc chuyển bước

**#7 ổn định phần triển khai → cập nhật tour → kiểm chứng luồng kết hợp và
nghiệm thu #7 → tiếp tục harness H1–H8.** Không chờ đóng #7 mới sửa tour:
hướng dẫn phải khớp luồng sửa trước khi dùng nó trong pilot của #7.

“Ổn định phần triển khai” nghĩa là đã chốt hành vi/hợp đồng cần thiết và qua
kiểm thử kỹ thuật liên quan; chưa phải nghiệm thu chất lượng hoặc đóng issue.
Chỉ nghiệm thu/đóng #7 khi đủ tiêu chí hiện có và bằng chứng trải nghiệm thực
tế. Các sửa chữa/kiểm tra cần thiết để hoàn thành #7 vẫn thuộc #7, không mở
benchmark H1–H8, embedding hoặc một framework harness mới làm phụ thuộc.

Giữ các mốc riêng: cập nhật tour kỹ thuật không đóng #22. Pilot 3–5 người,
tổng kết, trình đọc màn hình, thiết bị/IME/bàn phím thật và full Safari của
#22 còn mở khi chưa có bằng chứng. Không dùng việc #22 còn mở để bắt làm lại
#7, hoặc dùng nghiệm thu #7 tự đánh dấu mọi mục #22 đạt.

## A. Thẻ ý đồ tác giả đang dùng

### Nguồn dữ liệu và cách trình bày

| Nội dung hiển thị | Nguồn và quy tắc |
| --- | --- |
| Ý tưởng của bạn | Nguyên văn `idea` đã lưu, không thay bằng summary AI |
| Điều bạn muốn giữ / giới hạn | Nguyên văn các mục `constraints`, giữ thứ tự; không tự suy diễn thành thông điệp hoặc ngân sách |
| Những lựa chọn bạn đã trả lời hoặc để mở | Hỏi đáp hiệu lực từ `creator_answers()`, gồm lựa chọn giữ lại của cùng brief; câu hiện tại ghi đè câu cũ kể cả xóa hoặc chọn để sau |
| Câu hỏi đang chờ bạn trả lời | Câu hỏi hiện tại có câu trả lời trống; không trộn với các lựa chọn đã giữ từ trước |
| Thông tin nguồn | Bản đã lưu/revision nào; phân biệt thẻ hiện tại với ngữ cảnh của phản hồi cũ |

Đây là phần hiển thị dữ liệu tác giả, không phải một tác vụ AI mới. Không lấy
`analysis.summary`, reasoning notes, nội dung AI đề xuất trong draft hoặc lịch
sử của brief khác để bổ sung quyết định tác giả.

“Câu hỏi đang chờ” là thông tin của luồng làm rõ, không phải quyết định tác giả
hoặc cam kết rằng câu hỏi trống đã được gửi cho critic. Phần ý đồ được dùng để
góp ý phải khớp chính xác payload ý tưởng/ràng buộc/hỏi đáp hiệu lực của lần đó.

Không đoán trạng thái đã chốt/chưa chốt bằng từ khóa trong văn bản tự do. Trong
P0, hiển thị nguyên văn câu trả lời, kể cả “Chưa quyết định...” từ nút để sau;
nhóm này được gọi là “đã trả lời hoặc để mở”, không gọi tất cả là quyết định đã
chốt. Chỉ trường rỗng mới được xác định chắc chắn là chưa trả lời.

### Đã lưu, chưa lưu và chỉnh lại

- Thẻ hiện tại dựa trên phép chiếu chỉ đọc do backend tạo từ cùng nguồn mà
  planner/critic nhận. Không viết một thuật toán gộp hỏi đáp độc lập ở frontend.
- Khi có sửa chưa lưu, thẻ giữ ngữ cảnh đã lưu và ghi nổi bật “Có thay đổi chưa
  lưu; thẻ này chưa bao gồm các sửa đó”. Các trường đang sửa vẫn giữ nguyên.
  Thẻ cập nhật sau khi lưu thành công; không hiển thị như thể AI đã đọc buffer.
- “Chỉnh ý tưởng / điều muốn giữ” hoặc “Chỉnh câu trả lời hiện tại” chỉ chuyển
  focus tới trường gốc có sẵn, không lưu, gọi AI hoặc xóa nội dung.
- Các câu trả lời giữ từ vòng trước nhưng không còn trường nhập hiện tại được
  ghi rõ nguồn và chỉ đọc trong P0. Đổi định hướng có thể dùng trường ý tưởng/
  điều muốn giữ; cảnh báo trước rằng lưu brief mới sẽ yêu cầu làm rõ lại và đưa
  lựa chọn cũ vào lịch sử. Chỉnh riêng các câu đã giữ là công việc về sau.
- Sau lưu brief mới, thẻ không còn dùng hỏi đáp của brief cũ. Lỗi lưu hoặc xung
  đột không xóa buffer, không thay thẻ bằng ngữ cảnh mới chưa được xác nhận lưu.
- Mọi phản hồi, kể cả phản hồi cũ còn ở màn hình chính, có ngữ cảnh riêng từ
  snapshot đã lưu của chính lần đánh giá đó. Không chỉ áp dụng quy tắc này cho
  phần lịch sử. Với dữ liệu cũ thiếu nguồn thì ghi chưa có đủ thông tin, không
  tự dựng lại từ dự án hiện tại, version gần nhất hoặc lịch sử của brief khác.

### Phân biệt ý đồ hiện tại với ý đồ đã dùng để góp ý

- Thẻ cạnh phần nhập mang nhãn **Ý đồ đã lưu hiện tại**, kèm revision được xác
  nhận. Thẻ cạnh phản hồi mang nhãn **Ý đồ đã dùng cho góp ý này**, gắn với ID
  artifact và nguồn bản thảo của phản hồi. Chúng có thể khác nhau.
- Lưu cùng một snapshot nguồn bất biến khi lưu phản hồi: ngữ cảnh thực sự gửi
  AI, bản thảo đã đọc/khóa nội dung và ánh xạ mục tiêu. ID artifact, snapshot và
  các mục góp ý phải được ghi trong cùng lần lưu có kiểm tra revision. Không
  nhận cập nhật một phần khiến góp ý mới đi với snapshot cũ.
- Ví dụ: góp ý F1 đọc ý đồ A, sau đó tác giả lưu ý đồ B nhưng chưa review lại.
  Thẻ hiện tại là B; F1 vẫn hiện ngữ cảnh A với nhãn cũ, không có nút sửa từ F1.
  Chỉ phản hồi mới đọc B mới được gắn với ngữ cảnh B.
- Nếu khôi phục hoặc sửa lại làm nội dung khớp nguồn cũ, nguồn của góp ý vẫn
  mang thông tin lần nó được tạo; không sửa revision nguồn thành revision mới
  chỉ để làm chúng giống nhau. Độ mới dựa trên nội dung/ngữ cảnh phù hợp, không
  dựa riêng vào revision hiện tại.

## B. Từ góp ý tới đúng thao tác sửa

### Một mục góp ý gắn liền vấn đề và bước tiếp theo

Mỗi ưu tiên sửa mới có cùng một mục chứa:

- chi tiết/căn cứ trong bản được đọc, hoặc mô tả rõ điều còn thiếu;
- tác động có thể có với trải nghiệm tác giả muốn tạo;
- một bước sửa nhỏ hoặc lựa chọn sáng tác cần tác giả quyết định;
- mục tiêu cần xem/sửa đã được kiểm tra;
- nút **Sửa phần này** khi phản hồi hiện hành có mục tiêu hợp lệ.

Tối đa ba ưu tiên, có thể bằng không. Điểm mạnh hiển thị riêng để biết điều cần
giữ. Không coi điểm rubric hoặc `passed` là điều kiện được sửa hay hoàn thành.

Ví dụ minh họa: tác giả muốn người cha xin lỗi, không ngăn con đi; bản Middle
có hành động giấu hộ chiếu. Góp ý nêu khả năng người xem hiểu đó là kiểm soát,
hỏi tác giả muốn giữ mâu thuẫn này hay đổi hành động, rồi dẫn tới Middle. Không
đổi cảnh, xóa hành động hoặc ép hai cha con hòa giải thay cho tác giả.

### Liên kết có cấu trúc, thuộc đúng bản phản hồi

- Rà soát dữ liệu ghép cặp/nguồn đang có, ưu tiên dùng lại `CardReview` và
  luồng chuyển artifact/API; chỉ bổ sung chỗ còn thiếu. Không thêm một hợp
  đồng song song chỉ để đổi tên, hoặc để frontend tự ghép hai mảng chuỗi hay
  tìm từ “Ending” trong thông điệp để đoán mục tiêu.
  Mỗi mục có ID trong lần phản hồi, căn cứ, tác động, bước tiếp theo và danh
  sách khóa mục tiêu. Backend gán ID mục góp ý, không dùng số thứ tự qua nhiều
  vòng như danh tính của cùng một vấn đề.
- Backend tạo khóa cho tên phim, logline và các phần của đúng snapshot gửi AI.
  Mục tiêu của phần được gắn với vị trí/nội dung nhận diện trong snapshot đó,
  không dùng tên hiển thị tiếng Việt hay tên phần làm ID duy nhất. Chuẩn hóa
  cách tạo khóa giữa đánh giá ngay sau sinh plan và đánh giá bản đã sửa.
- Model chỉ được trả khóa mục tiêu có trong đầu vào. Backend kiểm tra khóa và
  lưu ánh xạ cùng nguồn phản hồi. Tên phần được dịch ở UI không đổi khóa. Một
  tham chiếu đầy đủ thuộc bộ dự án + artifact phản hồi + khóa nội dung nguồn +
  khóa mục tiêu; không dùng lại `section-0` của một artifact khác.
- Khóa không hợp lệ không sinh nút nhảy và không được đoán bằng tên gần giống.
  Góp ý tổng thể hoặc chưa xác định được mục tiêu vẫn đọc được, ghi rõ cần xem
  toàn bản. Phân biệt góp ý không có mục tiêu với góp ý có tham chiếu sai; loại
  thứ hai mang nhãn liên kết chưa được xác minh, không trình bày như đã đối chiếu.
- Dẫn chứng nguyên văn phải gắn với từng mục tiêu và khớp đúng giá trị trường
  đó trong snapshot, không chỉ xuất hiện ở đâu đó trong toàn bộ draft. Ví dụ
  câu giấu hộ chiếu chỉ có ở Middle thì không xác minh được liên kết Ending dù
  khóa Ending có thật. Không chuẩn hóa nội dung để ép một trích dẫn sai thành khớp.
- Với góp ý nhiều mục, từng tham chiếu phải vượt kiểm tra. Nếu có khóa sai, ánh
  xạ mơ hồ hoặc trích dẫn không khớp, giữ cả mục góp ý ở trạng thái chỉ đọc;
  không âm thầm bỏ mục tiêu lỗi rồi nhảy sang mục còn lại. Không hiển thị trích
  dẫn sai như một bằng chứng đã xác minh.
- Góp ý về điều còn thiếu có thể không có trích dẫn: nêu rõ đây là nhận định,
  chỉ kiểm tra được định danh mục tiêu. Một khóa và trích dẫn đúng không chứng
  minh diễn giải của AI là đúng; ca đánh giá mô hình thật vẫn phải kiểm tra điều đó.
- Khi một góp ý liên quan nhiều phần, hiển thị lựa chọn từng phần; không âm thầm
  nhảy vào phần đầu. P0 chỉ nhảy tới trường, chưa highlight chính xác một đoạn.

### Thao tác sửa và độ mới của góp ý

1. Tác giả đọc ngữ cảnh và chọn **Sửa phần này** trong phản hồi hiện hành.
2. UI cuộn tới trường và đặt focus; hiển thị góp ý đang chọn gần chỗ sửa.
3. Tác giả tự chỉnh. Thao tác điều hướng không thay chữ, lưu, gọi AI hay khôi
   phục phiên bản. Một lần chọn chỉ là trạng thái UI tạm, không tạo task trong DB.
4. Ngay khi nội dung/ý đồ thay đổi so với nguồn phản hồi, phản hồi được ghi rõ
   thuộc bản trước. Nút nhảy từ phản hồi cũ bị tắt; góp ý đã chọn có thể còn cạnh ô đang sửa nhưng
   phải mang nhãn cũ. Không đánh dấu tự động là đã sửa xong.
5. **Nhận phản hồi trên bản đã sửa** dùng luồng lưu rồi review hiện có. Chỉ
   cập nhật giao diện khi kết quả thuộc đúng dự án/lượt đang chạy và còn hợp lệ.

Điều kiện có nút nhảy: phản hồi đang được gắn cho bản hiện tại, khóa nội dung
khớp bản đã đọc, không có sửa nội dung/ngữ cảnh chưa lưu, ánh xạ mục tiêu hợp lệ
và UI không đang bận lưu/gọi AI. Nhận xét trong lịch sử chỉ đọc; không có nút
nhảy vào bản đang làm việc ngay cả khi hai bản có chữ giống nhau.

Không dùng cờ `dirty` chung làm điều kiện độ mới: đổi tên **dự án** tạo thay đổi
chưa lưu nhưng không đổi ý đồ hoặc tên phim trong `draft`. Trường hợp đó vẫn
cho điều hướng góp ý hợp lệ mà không lưu tên dự án. Ngược lại, đổi tên phim,
logline, các phần draft, ý tưởng, ràng buộc hoặc câu trả lời thì góp ý không còn
được điều hướng. Frontend so sánh các trường ảnh hưởng phản hồi với bản đã xác
nhận lưu, không tự tính lại phép gộp ý đồ. Backend vẫn kiểm tra đầy đủ khóa nội
dung/ngữ cảnh, kể cả bộ câu hỏi và lựa chọn giữ từ trước.

Nếu tác giả hoàn tác các sửa nội dung về đúng bản đã lưu và bản đó còn khớp
nguồn phản hồi, có thể phục hồi nút nhảy mà không gọi AI. Việc hoàn tác không
thay snapshot, không chuyển nhận xét lịch sử thành góp ý hiện tại và không
tự đánh dấu một vấn đề là đã giải quyết.

Khi nhận phản hồi mới hoặc đổi dự án, bỏ lựa chọn góp ý tạm của vòng trước.
Không yêu cầu lưu trước chỉ để chọn xem hoặc điều hướng tới một trường; nếu
đang có buffer chưa lưu thì không được dùng việc chọn góp ý để gọi `persist()`
hay `accept()`. Không tự so sánh chất lượng hai bản khi chỉ gửi một bản cho AI.

## Hướng triển khai và tương thích

| Phần | Thay đổi dự kiến sau khi PO duyệt |
| --- | --- |
| Backend / ngữ cảnh | Cung cấp phép chiếu chỉ đọc của ngữ cảnh tác giả hiệu lực; dùng chung nguồn với `_creator_input` và review, không cho client tự gán summary AI vào ngữ cảnh |
| Provider, domain và core artifacts | Bổ sung mục góp ý ghép cặp và khóa mục tiêu trong đầu vào/đầu ra; truyền xuyên suốt lớp đánh giá, không làm rơi thông tin khi chuyển artifact |
| API / lưu trữ | Lưu đồng thời các mục, snapshot ý đồ/bản thảo và ánh xạ cùng artifact trong dự án và `DraftVersion`, có kiểm tra revision; trường mới có mặc định tương thích dữ liệu cũ, không thêm kho quản lý công việc |
| Frontend | Thẻ ngữ cảnh, nhãn đã lưu/chưa lưu, mục góp ý ghép cặp, focus trường và trạng thái phản hồi cũ; ánh xạ cùng khóa backend, không dựa vào regex đọc lời AI |
| Tài liệu / kiểm thử | Cập nhật hợp đồng đầu ra, prompt, fixture và tình huống đánh giá khi thực sự triển khai; không đổi các tệp runtime trong PR kế hoạch |

Giữ `findings` và điểm hiện tại cho luồng đọc cũ/API tương thích, nhưng góp ý mới
phải xuất phát từ cùng dữ liệu ghép cặp để tránh hai nguồn mâu thuẫn. Phản hồi
cũ không có trường mới tiếp tục hiển thị như hiện nay, không tạo liên kết bằng
cách đoán cặp theo số thứ tự. Không bắt gọi AI lại chỉ để mở một dự án cũ.

Giữ kiểm tra revision và lưu trước review. Trong lúc lưu/gọi AI, khóa sửa,
chuyển/tạo dự án và các thao tác ghi khác; bỏ qua phản hồi đến muộn hoặc đã bị
thay thế. Lưu bị từ chối thì giữ buffer, không gọi review. Lưu thành công nhưng
AI lỗi thì giữ bản đã lưu và phản hồi cũ với nhãn phù hợp, không hoàn tác lưu
hay gắn phản hồi cũ cho bản mới. Cơ chế conflict ở backend vẫn phải bảo vệ thao
tác từ cửa sổ khác ngay cả khi UI đang khóa.

Khi mất kết nối trong lúc lưu hoặc review, có thể server đã ghi dù client chưa
nhận kết quả. Giữ buffer và nguồn đã xác nhận cuối, báo **Chưa xác nhận được
kết quả**; không khẳng định thao tác đã thất bại hoàn toàn hoặc thẻ đang là dữ
liệu mới nhất trên server. Chưa xác nhận lưu thì không gọi bước review tiếp.
Chỉ đối chiếu lại bằng thao tác đọc và giữ buffer riêng; không tự `accept()`
bản tải lại, đổi revision rồi gửi lại buffer hoặc gắn kết quả mới tới một lượt
khác. Khi lượt kết thúc/lỗi, mở khóa; phản hồi đến muộn không được ghi đè sửa
mới hoặc xóa trạng thái bận của lượt đang chạy.

## Thứ tự thực hiện

1. **Rà phần đã có và chốt phần thiếu:** lập đối chiếu từng tiêu chí với
   PR #31–#32/#36, code và test; chốt mẫu kết mở, câu trả lời để sau, ý đồ
   xung đột với hành động, bản cũ thiếu metadata và hai mục trùng tên. Chỉ
   làm phần thiếu, giữ UI Ý tưởng/Làm rõ/Story plan đã được chốt.
2. **Hoàn thiện nguồn ngữ cảnh:** dùng phép chiếu canonical hiện có, phân
   biệt buffer/bản lưu và nguồn feedback; kiểm tra retained answers, xóa/sửa
   câu trả lời, đổi brief và dữ liệu UI khớp đầu vào AI.
3. **Hoàn thiện góp ý ghép cặp:** dùng lại hợp đồng khi phù hợp, bổ sung phần
   thiếu về khóa mục tiêu, lưu nguồn và tương thích cũ; kiểm tra cả đánh giá
   plan mới lẫn review bản sửa, không suy mục tiêu từ tên hoặc thứ tự chuỗi.
4. **Ổn định vòng sửa và test kỹ thuật:** focus không ghi dữ liệu, nhãn cũ,
   lưu/review, lỗi và response muộn; qua contract/API/UI tests phù hợp trước
   khi chốt nội dung tour. Không thêm màn hình quản lý task hay tự áp dụng.
5. **Cập nhật tour theo #7:** làm theo [phần cập nhật tour sau #7](new-user-tour.md#cập-nhật-tour-sau-khi-phần-triển-khai-7-ổn-định),
   chủ yếu chặng đọc/sửa và lưu/review; giữ sáu bước, tiến độ cũ và quyền bỏ
   qua/mở lại. Không đợi nghiệm thu/đóng #7 mới làm bước này.
6. **Kiểm chứng luồng kết hợp:** đi từ đọc ý đồ/góp ý, xem nguồn, chọn hoặc
   từ chối, tới đúng card, tự sửa, lưu, review và mở lại. Kiểm tra tour trên
   cả dữ liệu mới/cũ, feedback cũ/thiếu nguồn, buffer, xung đột và response
   muộn; tour không tự thao tác lưu/AI. Nếu #7 thay đổi lại sau bước này,
   đối chiếu tour và chạy lại ca liên quan trên cùng phiên bản ứng viên.
7. **Đánh giá thực tế:** chạy mô hình thật, pilot 5–10 người mới qua hai vòng sửa
   và nhờ 1–2 người đọc có kinh nghiệm đánh giá. Đây là quy mô thử nghiệm đề xuất,
   không phải kết quả đã có hoặc cam kết chất lượng.

Giữ riêng tiêu chí #7, pilot tour 3–5 người của #22 và pilot MVP N=5–8 của
#26. Có thể chuẩn bị cùng đợt nếu chốt trước nhiệm vụ/phiên bản và ghi đủ bằng
chứng cho từng tiêu chí; không tự dùng một kết quả để đóng cả ba issue.
Sau khi đủ bằng chứng nghiệm thu #7 và tour đã cập nhật/kiểm tra kỹ thuật,
mới tiếp tục [harness H1–H8](harness-improvement.md); dùng lại kết quả liên
quan, không chạy lại hoặc tích hợp lại phần đã đạt chỉ vì đổi thứ tự kế hoạch.

## Tiêu chí nghiệm thu

| Tình huống | Kết quả bắt buộc |
| --- | --- |
| Phân tích lại cùng brief làm đổi hoặc xóa bộ câu hỏi | Thẻ vẫn thấy các hỏi đáp hiệu lực được giữ, khớp ngữ cảnh planner/critic |
| Câu hiện tại bị đổi, xóa hoặc chọn để sau | Giá trị cũ không được hồi sinh; không gọi lựa chọn để mở là đã chốt |
| Sửa ý tưởng/ràng buộc nhưng chưa lưu | Buffer giữ nguyên; thẻ nói rõ đang là bản đã lưu, chưa áp lựa chọn cũ vào brief mới |
| Lưu brief mới | Hỏi đáp cũ chuyển về lịch sử; thẻ và ngữ cảnh AI không dùng chúng cho brief mới |
| F1 đọc ý đồ A; lưu B, chưa có F2 | Thẻ hiện tại là B; F1 trên màn hình chính vẫn có nguồn A, nhãn cũ và không có nút sửa |
| Lưu/mở lại hoặc khôi phục với góp ý mới và lịch sử | Artifact, snapshot và các mục không bị trộn; không lấy ngữ cảnh hiện tại để lấp nguồn cũ thiếu metadata |
| Summary AI hoặc nội dung draft chứa ý tác giả chưa từng chọn | Không đưa vào thẻ như quyết định của tác giả |
| Ba vấn đề với ba hướng sửa khác nhau | Mỗi mục ghép đúng căn cứ/tác động/bước tiếp theo, không ghép nhầm hai mảng |
| Mục trùng tên, nhãn dịch, khóa ngoài danh sách hoặc góp ý nhiều mục | Liên kết dựa trên ánh xạ đã kiểm tra; có lựa chọn mục rõ ràng hoặc không có nút nhảy, không chọn đoán |
| Khóa Ending hợp lệ nhưng câu trích chỉ có trong Middle | Không có nút nhảy cho mục đó, không coi câu trích là bằng chứng của Ending |
| Góp ý nhiều mục có một tham chiếu sai; hoặc khóa thuộc artifact khác | Cả mục chỉ đọc với nhãn chưa xác minh, không chuyển sang khóa tương tự hoặc mục tiêu hợp lệ còn lại |
| Chọn góp ý đủ điều kiện hoặc chỉnh ý đồ bằng nút điều hướng | Focus đúng trường; không gọi lưu/AI, không thay dữ liệu, không xóa buffer hoặc lịch sử; khi nội dung/ngữ cảnh đã khác nguồn thì nút từ góp ý đó bị tắt |
| Chỉ đổi tên dự án, chưa lưu | Góp ý còn khớp nguồn vẫn điều hướng được; tên dự án và dấu chưa lưu giữ nguyên, không tự lưu |
| Đổi tên phim/ý đồ/nội dung rồi hoàn tác đúng bản đã lưu | Nút tắt trong lúc khác nguồn và có thể bật lại khi đủ điều kiện; không sinh đánh giá mới hoặc thay snapshot |
| Sửa sau khi chọn góp ý, có thể còn thay đổi chưa lưu khác | Toàn bộ buffer giữ nguyên; phản hồi lập tức có nhãn cũ và không còn điều hướng như phản hồi hiện hành |
| Phản hồi lịch sử hoặc thiếu metadata kiểu mới | Vẫn đọc được, không dùng ý đồ hiện tại làm ngữ cảnh của bản cũ, không nhảy vào draft hiện tại |
| Lưu và xin review mới | Đọc đúng bản đã sửa và ngữ cảnh đã lưu; lựa chọn UI cũ không bị gắn sang artifact mới |
| 409, AI lỗi hoặc kết quả đến muộn | Không ghi đè bản sửa, không thay dự án đang mở, không đánh dấu sai độ mới của phản hồi |
| Mất kết nối khi lưu/review, chưa rõ server đã ghi hay chưa | Giữ buffer; thẻ chỉ là bản cuối đã xác nhận, không tự ghi lại/tải đè hoặc gọi review khi chưa xác nhận lưu; mở khóa đúng lượt |
| Người mới sau một vòng sửa | Chỉ ra được mình muốn giữ gì, đã chọn sửa mục nào và vì sao; không bị buộc chấp nhận góp ý AI |

Kiểm thử tự động cần kiểm tra dữ liệu gửi AI, dữ liệu lưu/mở lại, và hành vi
focus/giữ buffer trong giao diện. Test fake provider chứng minh hợp đồng và
luồng dữ liệu, không chứng minh chất lượng góp ý. Dùng
[bộ tình huống đánh giá prompt](../prompt-evaluation.md) với mô hình thật để
kiểm tra dẫn chứng, sự cụ thể và mức độ tôn trọng ý đồ; bổ sung các ca khóa mục
tiêu. Theo dõi khả năng thực hiện một bước sửa và lý do từ chối góp ý, không lấy
số lần Generate hoặc điểm AI làm thước đo thành công.

Mỗi ca điều hướng cần so sánh toàn bộ buffer trước/sau (gồm tên dự án, brief,
câu trả lời và mọi phần draft), đồng thời xác nhận không có lệnh lưu/AI. Dữ liệu
thử phải có A/B khác ý đồ, mục trùng tên, trích dẫn đặt ở sai phần và phản hồi
cùng khóa mục tiêu nhưng khác artifact; kiểm tra cả UI và dữ liệu snapshot đã
lưu. Mô phỏng server ghi thành công nhưng làm mất response để kiểm tra kết quả
chưa rõ, không chỉ thử lỗi trước khi server nhận request.

## Ngoài phạm vi và điều PO cần duyệt

- Chưa có AI viết lại/tự áp dụng, tự đánh dấu đã giải quyết, task tồn tại qua
  nhiều phiên, AI so sánh hai bản, screenplay theo cảnh, ảnh/video hoặc PDF.
- P0 chưa thêm cơ chế chỉnh riêng lựa chọn giữ từ vòng cũ; chỉ hiển thị nguồn,
  điều hướng trường đang có và giải thích cách đổi brief khi đổi định hướng.
- PO duyệt: thẻ dữ liệu đã lưu kèm nhãn buffer; góp ý ghép cặp tối đa ba ưu tiên;
  nút chỉ chuyển focus; phản hồi cũ chỉ đọc; thứ tự triển khai và nghiệm thu.
- Merge PR này không hoàn thành tính năng hoặc đóng issue #7. Issue chỉ đóng
  sau khi triển khai, kiểm thử và kiểm chứng trải nghiệm thực tế.
