# Kế hoạch cải tiến harness FirstFrame

- Cập nhật: 22/10/2026, chia MVP thành bốn phần nhỏ; giữ hướng sửa hai chiều về sau.
- Trạng thái: kế hoạch đề xuất; lần cập nhật này chỉ sửa tài liệu.
- Cơ sở sản phẩm: [kế hoạch trong PR #27](vietnam-first-screenplay-mvp.md),
  theo dõi triển khai và nghiệm thu tại [issue #26](https://github.com/thomasMinh1995/firstframe-ai/issues/26).
- Bước 0–1 của đợt thử cũ đã merge trong [PR #28](https://github.com/thomasMinh1995/firstframe-ai/pull/28).
  Các phần MVP và kịch bản tương lai dưới đây chưa được triển khai bởi PR đó.

## 1. Mục tiêu: story plan đúng ý trước, kịch bản hoàn chỉnh về sau

FirstFrame giúp người mới viết phim ngắn tại Việt Nam giữ lại một khoảnh khắc,
chọn điều muốn kể và phát triển thành hành động, hình ảnh hoặc âm thanh có thể
thể hiện. Harness hỗ trợ tác giả đọc, tự sửa và giữ quyền quyết định.

```text
Khoảnh khắc → Ghi lại chất liệu → Story plan → Dàn cảnh → Viết/sửa kịch bản → Xuất kịch bản
```

Story plan là bản phác thảo giúp tác giả và AI kiểm tra hướng kể trước khi
phát triển nhiều trang. Nó cần giữ dữ kiện, lựa chọn và điều cố ý để mở, đồng
thời gợi được tiến trình mà người xem có thể thấy hoặc nghe. Với một phim một
cảnh, vài dòng diễn tiến và hình ảnh cuối có thể đã đủ; không bắt mọi khoảnh
khắc đi qua một bản kế hoạch dài hoặc cấu trúc kịch tính cố định.

Một story plan phù hợp có thể giúp kịch bản nhất quán và dễ sửa hơn. Chất lượng
kịch bản còn phụ thuộc hành động, lời thoại và nhịp cảnh; story plan tốt chưa
bảo đảm kịch bản hay. Story plan được phép thay đổi khi quá trình viết làm lộ
vấn đề hoặc tìm ra hướng tốt hơn. Kịch bản hoàn chỉnh vẫn là đích đến; sản phẩm
bàn giao ở bản xuất để con người cùng làm phim.

**Kết quả MVP cần chứng minh:** tác giả bắt đầu từ một khoảnh khắc, đọc được
story plan đúng hướng, nhận ra một chỗ cần sửa, tự sửa, lưu và nhận góp ý trên
đúng bản mới. Tác giả giải thích được lựa chọn của mình; từ chối một góp ý sai
cũng là quyết định có giá trị. Điểm AI và JSON hợp lệ chỉ là chỉ số hỗ trợ.

## 2. Hiện trạng và bằng chứng cần dùng đúng phạm vi

- Đã có analyze, plan, review, lưu dự án/phiên bản, bảo vệ bản sửa chưa lưu và
  kiểm tra độ mới của feedback. Tiếp tục dùng các cơ chế này.
- Runtime critic hiện trả các mảng chuỗi góp ý. Hợp đồng bắt buộc quote/khóa
  mục tiêu trong thử nghiệm lịch sử không phải hợp đồng đang phục vụ ứng dụng.
- `CreativeReasoningHarness.plan()` vẫn chờ critic trước khi trả kết quả;
  critic lỗi có thể làm tác giả chưa nhận được plan mà planner đã tạo xong.
- Thẻ nguồn ý đồ đầy đủ và liên kết góp ý tới trường đã kiểm tra là công việc
  của [P0 #7](p0-author-intent-revision-flow.md), chưa coi là đã có.
- [Thử nghiệm 3B](../evaluations/harness-reference-contract-2026-10-21.md) và
  [so sánh 3B–7B](../evaluations/harness-qwen3b-vs7b-2026-10-22.md) dùng nguồn
  lịch sử `e5198db`. PR #28 bàn giao runner, test và bằng chứng; không đưa khóa
  mục tiêu vào runtime hoặc chứng minh cấu hình hiện tại đã đạt nghiệm thu.

Kết quả 7B cho thấy khóa mục tiêu có thể cải thiện kiểm tra tham chiếu nhưng
vẫn còn lỗi nghĩa và tăng thời gian chờ. Chưa đổi model mặc định hoặc di trú
hợp đồng dựa trên kết quả đó. Runner lịch sử phải chạy trên nguồn tương thích;
baseline mới cần đo đúng API/luồng và hợp đồng hiện tại.

## 3. Bốn phần triển khai nhỏ cho MVP

Mỗi phần dưới đây là một thay đổi có thể review và nghiệm thu riêng. Số bước
0–1 trong báo cáo cũ vẫn chỉ đợt thử lịch sử. Baseline và chuẩn bị ba tình
huống làm song song, không trở thành một feature hoặc framework mới.

| Phần | Phạm vi nhỏ nhất | Điều kiện hoàn thành |
| --- | --- | --- |
| 1 — Lời dẫn và bản đọc | P0.1–P0.2: lời mời nhập khoảnh khắc, bản đọc từ draft hiện hành | Người mới biết nhập gì và hình dung được diễn tiến; bản đọc/editor dùng cùng dữ liệu, giữ sửa chưa lưu |
| 2 — Thẻ ý đồ hiện tại | P0.3: hiển thị nguồn tác giả đã lưu từ backend | Khớp input AI, phân biệt buffer chưa lưu và nguồn của feedback cũ; không cần schema lựa chọn mới |
| 3 — Hoàn thiện vòng sửa đang có | P0.4: chọn một góp ý, tự sửa, lưu, review và mở lại | Đúng bản/ngữ cảnh, tác giả tự sửa và giải thích được; dùng editor/API hiện có |
| 4 — Phục hồi plan khi critic lỗi | Tách lần tạo đầu tiên và tạo lại khi đã có draft | Plan đã sinh được lưu bền vững khi nguồn còn hợp lệ; bảo vệ bản đang viết và review lại riêng |

Làm phần 1 trước để kiểm tra trải nghiệm đọc; phần 2–4 có thể tiến hành song
song khi đã thống nhất nguồn và phạm vi. Xử lý lỗi chặn hành trình trước khi
nghiệm thu live. Tour đã có được giữ lại, điều chỉnh sau khi luồng ổn định;
[PDF #5](story-plan-pdf-export.md) đi sau đợt demo.

### Các bảo vệ áp dụng cho cả bốn phần

Giữ buffer, lịch sử, kiểm tra revision và nguồn feedback theo [#7](p0-author-intent-revision-flow.md).
Lỗi lưu, kết quả lưu chưa rõ, thao tác lặp hoặc response đến muộn không được
xóa/ghi đè bản sửa. Điều hướng không lưu hoặc gọi AI. Feedback giữ đúng draft
và ngữ cảnh đã đọc; dữ liệu cũ thiếu nguồn ghi rõ thiếu thông tin, không dựng
lại từ dự án hiện tại. Việc chia nhỏ không làm giảm các bảo vệ này.

### 3.1. Phần 1 — Lời dẫn và bản đọc

- Đổi lời mời, nhãn và ví dụ để một khoảnh khắc nhỏ đủ bắt đầu; thu gọn thông
  tin phụ, giữ cơ chế tạo/lưu dự án hiện có.
- Dựng bản đọc tên, tóm tắt, mở đầu, diễn tiến và kết thúc từ chính draft đang
  làm việc; các mục khác có thể mở rộng. Dùng cùng dữ liệu với editor và giữ
  cả sửa chưa lưu; không thêm một lượt AI kể lại hoặc một bản thảo thứ hai.
- Giữ trạng thái đã lưu/chưa lưu; đọc hoặc chuyển tới phần chỉnh sửa không
  lưu, đổi nội dung hoặc gọi AI. Chưa cần trang đọc hay luồng điều hướng mới.

**Kiểm chứng:** sửa một mục rồi đọc lại phải thấy đúng buffer, không phát sinh
request AI/ghi dữ liệu. Không có draft thì không dựng nội dung giả. Người mới
nêu lại được diễn tiến và một chi tiết họ muốn giữ.

### 3.2. Phần 2 — Thẻ ý đồ hiện tại

- Hiển thị nguyên văn idea, constraints và hỏi đáp hiệu lực từ cùng phép
  chiếu backend gửi AI, dùng `creator_answers()`. Không gộp lại ở frontend,
  lấy summary AI làm quyết định hoặc đoán trạng thái từ từ khóa.
- Thẻ hiện tại mang nhãn ngữ cảnh đã lưu. Khi có buffer mới, báo rõ thẻ chưa
  gồm sửa chưa lưu; chỉ cập nhật sau khi lưu thành công. Dùng trường sửa sẵn
  có, không thêm bộ câu hỏi bắt buộc hoặc kho ý đồ mới.
- Hiển thị nguồn của feedback khi có snapshot được lưu và kiểm tra. Feedback
  cũ không được nhận ngữ cảnh mới; nếu thiếu nguồn thì ghi rõ thiếu thông tin
  và không cung cấp điều hướng chưa xác minh. Chưa cần migration toàn bộ dữ
  liệu lịch sử hoặc trạng thái `confirmed/open/proposed` để giao thẻ hiện tại.

**Kiểm chứng:** so thẻ với input provider, gồm hỏi đáp giữ từ vòng trước,
xóa/sửa câu trả lời và lựa chọn để sau. Đổi ý đồ A thành B phải giữ nguồn A
của feedback cũ; lỗi lưu/xung đột không xóa buffer hoặc thay nguồn bằng dữ
liệu chưa được xác nhận lưu.

### 3.3. Phần 3 — Hoàn thiện vòng sửa đang có

- Giữ danh sách góp ý hiện có, giúp tác giả chọn một chỗ để tự sửa trong
  editor. Góp ý cần chi tiết, tác động tới ý định và bước sửa khả thi; mảng
  vấn đề rỗng hợp lệ khi không có vấn đề có căn cứ.
- Dùng luồng sửa → lưu → review → mở lại đang có. Sau sửa, feedback cũ được
  đánh dấu rõ; góp ý mới chỉ gắn với đúng bản/ngữ cảnh đã lưu.
- Chưa thêm nút tự áp dụng, trạng thái “đã giải quyết”, highlight hoặc liên
  kết tự động tới trường. Liên kết mục tiêu có cấu trúc tiếp tục theo #7 khi
  nguồn và mục tiêu được kiểm tra; không phải phụ thuộc của vòng sửa thủ công.
- Phân biệt dữ kiện trái ý, lựa chọn còn mở và đề xuất sáng tạo. Không bịa
  quote cho điều còn thiếu hoặc nói “đã tiến bộ” khi chỉ đọc một bản.

**Kiểm chứng:** tác giả chọn hoặc từ chối một góp ý, tự sửa, lưu, review và
mở lại đúng bản; giải thích được lựa chọn. Thử lỗi lưu, restore, hai cửa sổ
và response muộn: giữ buffer/lịch sử và không gắn feedback sang nguồn khác.

### 3.4. Phần 4 — Phục hồi plan khi critic lỗi

Tách hai trường hợp để không bắt mọi lần tạo plan đi qua luồng nhận đề xuất:

- **Tạo lần đầu, chưa có draft:** khi planner thành công, lưu trực tiếp bản
  nháp cùng nguồn brief/revision và trạng thái chưa có góp ý, trước critic.
  Chỉ lưu nếu dự án vẫn chưa có draft và nguồn còn hợp lệ. Dùng kho dự án và
  lịch sử hiện có; tải lại vẫn đọc/sửa được, không cần thêm bước “Nhận bản”.
- **Tạo lại khi đã có draft:** lưu kết quả mới thành đề xuất riêng trong kho
  dự án hiện có, giữ bản đang viết tới khi tác giả chọn nhận. Khi nhận kiểm
  tra revision/ngữ cảnh và lưu lịch sử. Không tự thay draft vì critic lỗi,
  thao tác lặp hoặc kết quả đến muộn.

Cả hai đường giữ ID lượt tạo và nguồn để phân biệt kết quả. Nếu nguồn thay
đổi hoặc cửa sổ khác đã tạo/sửa draft thì xử lý xung đột, không tự cập nhật
revision rồi ghi lại. Khi critic lỗi, cho biết plan đã có nhưng chưa nhận
góp ý hợp lệ; có thể sửa và review lại riêng. Không dùng raw dataset làm
kho khôi phục, gắn feedback cũ cho plan mới hoặc dùng passed thay góp ý thiếu.
Phục hồi được plan không tự biến lượt thiếu review thành lượt đạt demo.

**Kiểm chứng:** planner thành công rồi critic timeout/lỗi provider/JSON lỗi,
tải lại vẫn có bản nháp hoặc đề xuất đúng trường hợp. Thử hai cửa sổ, nhận
hai lần và mất response sau khi lưu; giữ mọi bản sửa. Đo số lần phải tạo lại
plan khi chỉ critic lỗi. Có thể review hai đường riêng trong phần 4; chỉ
nghiệm thu cả phần khi cả hai đường đạt bảo toàn và phục hồi, không đánh dấu
hoàn tất chỉ vì lần tạo đầu đã qua. Chưa thêm retry tự động hoặc vòng AI tự
sửa nội dung.

### Công việc song song — baseline và sửa lỗi quan sát được

- Dùng [checklist model](../prompt-evaluation.md) và cơ chế dataset hiện có.
  Chuẩn bị ba tình huống: chăm sóc thường ngày, vui/khó xử và quan sát lặng;
  chốt brief, dữ kiện, điều giữ/để mở, thao tác sửa và kỳ vọng trước khi đọc
  kết quả. Hỏi tối đa ba câu có ích, có thể không hỏi nếu đã đủ rõ.
- Trong lúc phát triển, chạy ca liên quan tới thay đổi và giữ mọi kết quả,
  kể cả lỗi. Không chạy lại toàn bộ benchmark lịch sử sau mỗi sửa UI. Đợt
  chín lượt toàn luồng trên cấu hình cuối vẫn phải chạy đầy đủ theo mục 4;
  kết quả thử rời rạc không được ghép thành chín lượt nghiệm thu.
- Đo làm rõ → plan → sửa → lưu → review; ghi lỗi dữ kiện/vai, tự chốt lựa
  chọn, thêm biến cố trái ý, tiếng Việt/xưng hô, góp ý thiếu căn cứ, lỗi tác
  vụ và thời gian. Cố định commit, prompt, model identifier/digest và tham
  số của từng đợt, ghi seed nếu có; không sinh lại đến khi lấy được mẫu đẹp.
- Chỉ sửa input/hướng dẫn liên quan tới lỗi đã thấy, thay một yếu tố mỗi lần
  và đối chiếu cả ca đúng lẫn sai. Hỗ trợ chuyện lặng, kết mở, nhiều sắc thái
  và giới hạn tác giả đã nêu; không mặc định mọi chuyện phải buồn/hòa giải.
- Ví dụ thử nhỏ: giữ nhãn vai khi chiếu plan sang critic hoặc làm rõ trường
  do pipeline sao lặp. Đây là giả thuyết cần đo, không phải nguyên nhân đã
  được chứng minh hoặc lý do phải sửa toàn bộ prompt/schema/rubric cùng lúc.
- Dùng ca tổng hợp trong repo. Trải nghiệm riêng chỉ tái sử dụng khi tác giả
  đồng ý, không đưa nội dung riêng vào repo công khai.

### Để sau vòng MVP cơ bản

Khóa mục tiêu, trạng thái `confirmed/open/proposed` và review hẹp là ba thử
nghiệm độc lập, chỉ mở khi có lỗi/nhu cầu cụ thể. Chúng không phải điều kiện
cho bốn phần trên hoặc pilot khám phá. Khóa phải gắn snapshot; trích dẫn nếu
có phải khớp đúng mục. Câu trả lời tự do giữ nguyên nguồn, không fuzzy match
hoặc đoán lựa chọn đã chốt. Giảm ngữ cảnh phải đo cả báo sai và bỏ sót; chưa
đổi model mặc định từ kết quả thử cũ.

Chốt kỳ vọng, so biến thể có kiểm soát, chấm nội dung độc lập với validator
và nhờ người thứ hai đối chiếu ca khó. Tập đã tuning là tập phát triển, cần
ca giữ riêng khi kết luận khả năng khái quát. Mọi tích hợp sau này vẫn phải
đạt yêu cầu nguồn/snapshot và tương thích dữ liệu cũ của #7.

## 4. Nghiệm thu MVP và kiểm chứng giá trị

### Demo và pilot theo issue #26

Áp dụng đầy đủ [điều kiện demo ở mục 4.1](vietnam-first-screenplay-mvp.md#41-điều-kiện-demo-trực-tiếp-hoặc-dùng-bản-ghi)
và [điều kiện pilot ở mục 6.1](vietnam-first-screenplay-mvp.md#61-điều-kiện-pilot-đạt-và-chuyển-sang-m2).
Không thay đổi các ngưỡng đã chốt trong kế hoạch sản phẩm:

- Live: ba tình huống × ba lượt độc lập trên cấu hình cuối, đủ 9/9 lượt hoàn
  thành toàn luồng, giữ nguồn/dữ liệu và không có lỗi chặn. Chốt ngân sách
  chờ trước; cả chín lượt trong ngân sách và một buổi diễn tập đầy đủ tối đa
  năm phút. PO cùng người đọc có kinh nghiệm duyệt chế độ và lưu bằng chứng.
- Thiếu bằng chứng, có lượt trượt hoặc đổi cấu hình thì chưa đạt live; sau
  sửa chạy đợt đủ chín lượt mới và giữ kết quả cũ. Bản ghi phải được duyệt,
  ghi rõ phát lại/hiệu đính; không dùng bản ghi thay nghiệm thu live hoặc pilot.
- Pilot: chốt N=5–8 người bắt đầu, phiên bản và nhiệm vụ. Chỉ toàn nhiệm vụ
  ở H0 (hướng dẫn chung và tour/tài liệu sẵn có) tính là độc lập; H1 là nhắc
  từng bước, H2 là gợi ý sáng tác/thao tác hộ. Người bỏ dở vẫn thuộc N.
- Ít nhất 80% N hoàn thành độc lập, làm tròn lên; ít nhất hai người đạt muốn
  viết tiếp bản của họ và nêu bước tiếp. Không còn lỗi chặn chưa xử lý; PO
  ghi đạt/chưa đạt/cần thêm bằng chứng trước M2. Không hạ ngưỡng hồi tố hoặc
  gộp kết quả khác phiên bản để đạt; thay nhiệm vụ/ngưỡng cần đợt mới.

Pilot diễn ra khi vòng MVP cơ bản sẵn sàng; không chờ toàn bộ hợp đồng khóa,
trạng thái lựa chọn hoặc tối ưu review. Lưu đủ lý do sửa/từ chối và mức hỗ trợ.
Lỗi mất dữ liệu, sai nguồn, không lưu/mở lại được hoặc vi phạm lựa chọn rõ là
lỗi chặn, cần bằng chứng xác nhận lại sau sửa trên phiên bản ứng viên.

### So sánh với cách viết cùng AI agent

Giả thuyết cần kiểm chứng: người mới giữ được câu chuyện của mình và hoàn
thành một vòng sửa với ít công sức điều khiển AI hơn. Lưu phiên bản, template
hoặc một pipeline nhiều tầng tự chúng chưa chứng minh lợi thế.

So cùng chất liệu, lựa chọn, ngôn ngữ và nhiệm vụ với chatbot/agent quen thuộc
và công cụ phát triển câu chuyện trực tiếp. Cho công cụ đối chiếu mẫu prompt
hữu ích, đủ ngữ cảnh và cơ hội sửa. Chốt trước tiêu chí thắng/chưa rõ: mức hỗ
trợ, lỗi làm sai ý, khả năng tự sửa/giải thích, tổng thời gian/công sức và bản
tác giả muốn giữ hoặc viết tiếp. Đánh giá tính thể hiện bằng hành động/hình
ảnh/âm thanh với người đọc có kinh nghiệm; không lấy điểm AI làm kết luận.

Tách chỉ số kỹ thuật, chất lượng nội dung và hành vi người dùng. 80% người
hoàn thành độc lập khác với tỷ lệ output review dùng được; kế hoạch này không
đặt thêm ngưỡng 80% review làm điều kiện chặn mọi cải thiện UI hoặc pilot khám
phá. Pilot nhỏ chưa chứng minh lợi thế thị trường. Giai đoạn M1 so story plan
và vòng sửa; chỉ đánh giá hoàn thành kịch bản khi M3/M4 khả dụng.

## 5. Về sau: sửa hai chiều giữa story plan và kịch bản

Phần này là hướng M2–M4, triển khai khi có dàn cảnh và trình viết kịch bản;
không đưa screenplay editor, liên kết cảnh hoặc tự viết lại vào đợt demo MVP.

### Xác định cấp độ vấn đề trước khi sửa

“Kịch bản chưa đạt” cần được làm rõ theo trải nghiệm tác giả muốn tạo. Không
suy nguyên nhân chỉ từ điểm AI hoặc mặc định story plan là lỗi gốc.

| Tình huống | Hướng sửa đề xuất |
| --- | --- |
| Hướng kể lệch ý, diễn tiến chưa nâng đỡ cảm xúc/kết thúc mong muốn | Xem lại story plan, rồi xác định dàn cảnh/cảnh chịu ảnh hưởng |
| Hướng kể phù hợp nhưng thoại gượng, hành động thiếu sức sống hoặc nhịp cảnh chưa hợp | Sửa trực tiếp cảnh; giữ plan nếu hướng kể không đổi |
| Viết cảnh tìm ra hướng kể hoặc chi tiết cấu trúc tốt hơn | Tác giả chọn hướng mới, cập nhật story plan từ kịch bản và kiểm tra những phần liên quan |

Ví dụ: plan tự thêm cãi vã/hòa giải vào ý định kể sự chăm sóc lặng lẽ thì cần
xem lại hướng kể. Nếu plan đúng ý nhưng nhân vật nói dài để giải thích tình
thương, có thể chỉ cần sửa cách thể hiện trong cảnh.

### Ba nguyên tắc cho giai đoạn có kịch bản

1. Xác định vấn đề nằm ở hướng kể hay cách viết cảnh trước khi chọn sửa plan
   hoặc kịch bản; thoại chưa tốt không tự làm plan thành sai.
2. Chỉ đề xuất phần bị ảnh hưởng, cho tác giả xem và duyệt thay đổi. Kịch bản
   tìm được hướng tốt hơn có thể dẫn ngược về plan; không tự viết lại toàn bộ
   hoặc đồng bộ hai phía theo tên nhân vật giống nhau.
3. Giữ phiên bản plan nguồn, snapshot feedback, lịch sử, buffer và kiểm tra
   revision; khác biệt chưa được duyệt không tự thành lỗi nghệ thuật. Không
   ghi đè khi hai phía cùng sửa hoặc response đến muộn.

Thiết kế liên kết cảnh, trước/sau, duyệt từng phần, nhiều phương án và xử lý
hai phía cùng sửa được chốt khi làm M2/M3. Chưa xây schema cảnh, bộ máy đồng
bộ hoặc model tự quyết định chuỗi sửa trong MVP. Khi triển khai về sau phải
kiểm chứng sửa thoại không ép đổi plan, thay hướng kể chỉ ảnh hưởng phần liên
quan và từ chối đề xuất không làm mất nội dung.

## 6. Phạm vi lần cập nhật tài liệu

Cập nhật kế hoạch harness và tham chiếu roadmap; giữ nguyên các ngưỡng nghiệm
thu của kế hoạch sản phẩm. Chưa sửa workflow, prompt, rubric, schema, UI,
dependency, model mặc định hoặc dữ liệu dự án. Không coi các mục đề xuất là
đã triển khai, không chạy model hoặc pilot để nghiệm thu trong lần này.

Multi-agent, RAG, workflow engine mới, model routing, tự áp dụng góp ý và công
cụ sản xuất không phải điều kiện cho MVP story plan. Mọi mở rộng về sau phải
được quyết định từ lỗi và nhu cầu quan sát được trong hành trình viết.
