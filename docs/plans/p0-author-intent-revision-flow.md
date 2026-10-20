# P0: Hiển thị ý đồ tác giả và nối góp ý với thao tác sửa

- Trạng thái: đề xuất, chờ PO review; chưa triển khai.
- Issue: [P0 #7](https://github.com/thomasMinh1995/firstframe-ai/issues/7).
- PR kế hoạch chỉ thay đổi tài liệu; không sửa code, prompt, schema hay dependency runtime.

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
- `page.tsx` có trường sửa ý tưởng, ràng buộc, câu trả lời, từng mục story plan,
  lưu, nhận phản hồi và lịch sử. Các lựa chọn giữ qua nhiều lượt phân tích chưa
  được thể hiện thành một thẻ ngữ cảnh đầy đủ.
- `StoryFeedback` hiển thị ba danh sách riêng. `findings` hiện chứa thông điệp
  dạng chuỗi và tên nhóm như `weakness-1`, `suggestion-1`, chưa có liên kết đáng
  tin cậy tới trường cần sửa.
- `content_key()`, `reviewed_content`, `feedback_is_current` và kiểm tra thay đổi
  chưa lưu đã có; P0 phải tiếp tục dùng cơ chế này, không coi revision bằng nhau
  hoặc tên mục giống nhau là đủ chứng minh phản hồi còn đúng.
- PDF đang là kế hoạch riêng ở [#5](https://github.com/thomasMinh1995/firstframe-ai/issues/5).
  Hai tính năng P0 này không phụ thuộc PDF và không thay phạm vi bản xuất.

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
- Khi xem phản hồi lịch sử, ngữ cảnh đi kèm lấy từ snapshot đã lưu của phản hồi/
  phiên bản đó. Không gắn thẻ ý đồ hiện tại vào một phản hồi cũ. Với dữ liệu cũ
  thiếu nguồn thì ghi chưa có đủ thông tin, không tự dựng lại từ lịch sử khác.

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

- Bổ sung dữ liệu ghép cặp, dự kiến tên `revision_notes`, thay vì frontend tự
  ghép hai mảng chuỗi hoặc tìm từ “Ending” trong thông điệp để đoán mục tiêu.
  Mỗi mục có ID trong lần phản hồi, căn cứ, tác động, bước tiếp theo và danh
  sách khóa mục tiêu. Backend gán ID mục góp ý, không dùng số thứ tự qua nhiều
  vòng như danh tính của cùng một vấn đề.
- Backend tạo khóa cho tên phim, logline và các phần của đúng snapshot gửi AI.
  Mục tiêu của phần được gắn với vị trí/nội dung nhận diện trong snapshot đó,
  không dùng tên hiển thị tiếng Việt hay tên phần làm ID duy nhất. Chuẩn hóa
  cách tạo khóa giữa đánh giá ngay sau sinh plan và đánh giá bản đã sửa.
- Model chỉ được trả khóa mục tiêu có trong đầu vào. Backend kiểm tra khóa và
  lưu ánh xạ cùng nguồn phản hồi. Tên phần được dịch ở UI không đổi khóa.
- Khóa không hợp lệ không sinh nút nhảy và không được đoán bằng tên gần giống.
  Góp ý tổng thể hoặc chưa xác định được mục tiêu vẫn đọc được, ghi rõ cần xem
  toàn bản. Nếu có trích dẫn nguyên văn, phải kiểm tra nó thuộc snapshot tương
  ứng trước khi hiển thị như một trích dẫn đã xác minh. Kiểm tra khóa/trích dẫn
  không đồng nghĩa đã xác nhận diễn giải của AI là đúng.
- Khi một góp ý liên quan nhiều phần, hiển thị lựa chọn từng phần; không âm thầm
  nhảy vào phần đầu. P0 chỉ nhảy tới trường, chưa highlight chính xác một đoạn.

### Thao tác sửa và độ mới của góp ý

1. Tác giả đọc ngữ cảnh và chọn **Sửa phần này** trong phản hồi hiện hành.
2. UI cuộn tới trường và đặt focus; hiển thị góp ý đang chọn gần chỗ sửa.
3. Tác giả tự chỉnh. Thao tác điều hướng không thay chữ, lưu, gọi AI hay khôi
   phục phiên bản. Một lần chọn chỉ là trạng thái UI tạm, không tạo task trong DB.
4. Ngay khi nội dung/ý đồ thay đổi, phản hồi được ghi rõ thuộc bản trước. Nút
   nhảy từ phản hồi cũ bị tắt; góp ý đã chọn có thể còn cạnh ô đang sửa nhưng
   phải mang nhãn cũ. Không đánh dấu tự động là đã sửa xong.
5. **Nhận phản hồi trên bản đã sửa** dùng luồng lưu rồi review hiện có. Chỉ
   cập nhật giao diện khi kết quả thuộc đúng dự án/lượt đang chạy và còn hợp lệ.

Điều kiện có nút nhảy: phản hồi đang được gắn cho bản hiện tại, khóa nội dung
khớp bản đã đọc, không có sửa nội dung/ngữ cảnh chưa lưu, và ánh xạ mục tiêu còn
hợp lệ. Nhận xét trong lịch sử chỉ đọc; không có nút nhảy vào bản đang làm việc.

Khi nhận phản hồi mới hoặc đổi dự án, bỏ lựa chọn góp ý tạm của vòng trước.
Không yêu cầu lưu trước chỉ để chọn xem hoặc điều hướng tới một trường; nếu
đang có buffer chưa lưu thì không được dùng việc chọn góp ý để gọi `persist()`
hay `accept()`. Không tự so sánh chất lượng hai bản khi chỉ gửi một bản cho AI.

## Hướng triển khai và tương thích

| Phần | Thay đổi dự kiến sau khi PO duyệt |
| --- | --- |
| Backend / ngữ cảnh | Cung cấp phép chiếu chỉ đọc của ngữ cảnh tác giả hiệu lực; dùng chung nguồn với `_creator_input` và review, không cho client tự gán summary AI vào ngữ cảnh |
| Provider, domain và core artifacts | Bổ sung mục góp ý ghép cặp và khóa mục tiêu trong đầu vào/đầu ra; truyền xuyên suốt lớp đánh giá, không làm rơi thông tin khi chuyển artifact |
| API / lưu trữ | Lưu các mục và ánh xạ với nguồn phản hồi trong dự án và `DraftVersion`; trường mới có mặc định tương thích dữ liệu cũ, không thêm kho quản lý công việc |
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

## Thứ tự thực hiện

1. **Chốt mẫu trải nghiệm và dữ liệu:** ví dụ kết mở, câu trả lời để sau, ý đồ
   xung đột với hành động, bản cũ thiếu metadata và hai mục trùng tên.
2. **Thẻ ngữ cảnh:** phép chiếu canonical, phân biệt buffer và bản lưu, đường
   dẫn tới trường gốc; chứng minh dữ liệu UI khớp đầu vào AI.
3. **Góp ý ghép cặp:** hợp đồng, khóa mục tiêu, lưu nguồn và tương thích cũ;
   kiểm tra cả đánh giá plan mới lẫn review bản sửa.
4. **Luồng sửa:** focus không ghi dữ liệu, nhãn cũ, lưu/review, xử lý lỗi và kết
   quả đến muộn. Không làm thêm màn hình quản lý task hoặc tự áp dụng đề xuất.
5. **Đánh giá thực tế:** chạy mô hình thật, pilot 5–10 người mới qua hai vòng sửa
   và nhờ 1–2 người đọc có kinh nghiệm đánh giá. Đây là quy mô thử nghiệm đề xuất,
   không phải kết quả đã có hoặc cam kết chất lượng.

## Tiêu chí nghiệm thu

| Tình huống | Kết quả bắt buộc |
| --- | --- |
| Phân tích lại cùng brief làm đổi hoặc xóa bộ câu hỏi | Thẻ vẫn thấy các hỏi đáp hiệu lực được giữ, khớp ngữ cảnh planner/critic |
| Câu hiện tại bị đổi, xóa hoặc chọn để sau | Giá trị cũ không được hồi sinh; không gọi lựa chọn để mở là đã chốt |
| Sửa ý tưởng/ràng buộc nhưng chưa lưu | Buffer giữ nguyên; thẻ nói rõ đang là bản đã lưu, chưa áp lựa chọn cũ vào brief mới |
| Lưu brief mới | Hỏi đáp cũ chuyển về lịch sử; thẻ và ngữ cảnh AI không dùng chúng cho brief mới |
| Summary AI hoặc nội dung draft chứa ý tác giả chưa từng chọn | Không đưa vào thẻ như quyết định của tác giả |
| Ba vấn đề với ba hướng sửa khác nhau | Mỗi mục ghép đúng căn cứ/tác động/bước tiếp theo, không ghép nhầm hai mảng |
| Mục trùng tên, nhãn dịch, khóa ngoài danh sách hoặc góp ý nhiều mục | Liên kết dựa trên ánh xạ đã kiểm tra; có lựa chọn mục rõ ràng hoặc không có nút nhảy, không chọn đoán |
| Chọn góp ý đủ điều kiện hoặc chỉnh ý đồ bằng nút điều hướng | Focus đúng trường; không gọi lưu/AI, không thay dữ liệu, không xóa buffer hoặc lịch sử; khi có sửa chưa lưu thì nút nhảy từ góp ý cũ bị tắt |
| Sửa sau khi chọn góp ý, có thể còn thay đổi chưa lưu khác | Toàn bộ buffer giữ nguyên; phản hồi lập tức có nhãn cũ và không còn điều hướng như phản hồi hiện hành |
| Phản hồi lịch sử hoặc thiếu metadata kiểu mới | Vẫn đọc được, không dùng ý đồ hiện tại làm ngữ cảnh của bản cũ, không nhảy vào draft hiện tại |
| Lưu và xin review mới | Đọc đúng bản đã sửa và ngữ cảnh đã lưu; lựa chọn UI cũ không bị gắn sang artifact mới |
| 409, AI lỗi hoặc kết quả đến muộn | Không ghi đè bản sửa, không thay dự án đang mở, không đánh dấu sai độ mới của phản hồi |
| Người mới sau một vòng sửa | Chỉ ra được mình muốn giữ gì, đã chọn sửa mục nào và vì sao; không bị buộc chấp nhận góp ý AI |

Kiểm thử tự động cần kiểm tra dữ liệu gửi AI, dữ liệu lưu/mở lại, và hành vi
focus/giữ buffer trong giao diện. Test fake provider chứng minh hợp đồng và
luồng dữ liệu, không chứng minh chất lượng góp ý. Dùng
[bộ tình huống đánh giá prompt](../prompt-evaluation.md) với mô hình thật để
kiểm tra dẫn chứng, sự cụ thể và mức độ tôn trọng ý đồ; bổ sung các ca khóa mục
tiêu. Theo dõi khả năng thực hiện một bước sửa và lý do từ chối góp ý, không lấy
số lần Generate hoặc điểm AI làm thước đo thành công.

## Ngoài phạm vi và điều PO cần duyệt

- Chưa có AI viết lại/tự áp dụng, tự đánh dấu đã giải quyết, task tồn tại qua
  nhiều phiên, AI so sánh hai bản, screenplay theo cảnh, ảnh/video hoặc PDF.
- P0 chưa thêm cơ chế chỉnh riêng lựa chọn giữ từ vòng cũ; chỉ hiển thị nguồn,
  điều hướng trường đang có và giải thích cách đổi brief khi đổi định hướng.
- PO duyệt: thẻ dữ liệu đã lưu kèm nhãn buffer; góp ý ghép cặp tối đa ba ưu tiên;
  nút chỉ chuyển focus; phản hồi cũ chỉ đọc; thứ tự triển khai và nghiệm thu.
- Merge PR này không hoàn thành tính năng hoặc đóng issue #7. Issue chỉ đóng
  sau khi triển khai, kiểm thử và kiểm chứng trải nghiệm thực tế.
