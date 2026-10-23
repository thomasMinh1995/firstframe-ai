# Kế hoạch cải tiến harness FirstFrame

- Cập nhật: 23/10/2026, tám gói sau bốn phần MVP đã merge; kết hợp chunking
  theo cấu trúc và ID nguồn, chưa triển khai embedding/retrieval.
- Trạng thái: nền tảng bốn phần đã triển khai; tám gói dưới đây là công việc
  tiếp theo, chưa được triển khai hoặc nghiệm thu bởi lần sửa tài liệu này.
- Cơ sở sản phẩm: [kế hoạch trong PR #27](vietnam-first-screenplay-mvp.md),
  theo dõi triển khai và nghiệm thu tại [issue #26](https://github.com/thomasMinh1995/firstframe-ai/issues/26).
- Bước 0–1 của đợt thử cũ đã merge trong [PR #28](https://github.com/thomasMinh1995/firstframe-ai/pull/28).
  Bốn phần MVP đã merge riêng qua PR #30–#33; chưa đồng nghĩa đạt demo/pilot.

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
- Đã có lời dẫn/bản đọc (PR #30), thẻ ý đồ đã lưu và nguồn feedback (PR #31),
  vòng sửa thủ công (PR #32), phục hồi plan khi critic lỗi (PR #33).
  Tạo lần đầu lưu draft trước critic khi nguồn hợp lệ; tạo lại giữ đề xuất
  riêng tới khi tác giả nhận, không ghi đè bản đang viết.
- Thẻ ý đồ và vòng sửa đã giao một phần của [P0 #7](p0-author-intent-revision-flow.md).
  Liên kết góp ý tới mục tiêu có cấu trúc và đã kiểm tra chưa được triển khai.
- Đợt toàn luồng trên commit `f607732` hoàn tất 9/9 hành trình và giữ nguồn,
  nhưng 7/9 lượt tạo plan vượt mốc 120 giây và còn góp ý trái ý/thiếu căn cứ.
  Chưa đủ điều kiện demo trực tiếp; chưa có nghiệm thu PO hoặc pilot.
- Đợt offline chốt 50 lượt ngày 23/10 trên Qwen 2.5 7B: đủ phát hiện,
  bằng chứng và sửa đúng ở 4/12 bản vi phạm với workflow tìm bằng chứng trước,
  so với 5/12 của prompt hẹp chạy mới cùng đợt. Bốn ca chép quote sai bị gate
  chặn; hai ca dẫn đúng chữ nhưng suy diễn sai địa điểm. Đây là bộ phát triển
  nhỏ đã dùng nhiều lần, không phải bằng chứng khái quát hoặc nghiệm thu.
- [Thử nghiệm 3B](../evaluations/harness-reference-contract-2026-10-21.md) và
  [so sánh 3B–7B](../evaluations/harness-qwen3b-vs7b-2026-10-22.md) dùng nguồn
  lịch sử `e5198db`. PR #28 bàn giao runner, test và bằng chứng; không đưa khóa
  mục tiêu vào runtime hoặc chứng minh cấu hình hiện tại đã đạt nghiệm thu.

Kết quả 7B cho thấy khóa mục tiêu có thể cải thiện kiểm tra tham chiếu nhưng
vẫn còn lỗi nghĩa và tăng thời gian chờ. Chưa đổi model mặc định hoặc di trú
hợp đồng dựa trên kết quả đó. Runner lịch sử phải chạy trên nguồn tương thích;
baseline mới cần đo đúng API/luồng và hợp đồng hiện tại.

## 3. Tám gói tiếp theo: chất lượng, tích hợp và nghiệm thu

Bốn phần MVP đã có code; không triển khai lại chúng. Tám gói là đơn vị công
việc có thể review riêng, gồm đánh giá/thử nghiệm, triển khai và nghiệm thu,
không phải tám feature hoặc tám PR cố định. Chunking và ID nguồn nằm trong
gói 2 và 5; không thêm một dự án RAG hoặc một kho bản thảo mới.

| Gói | Phạm vi nhỏ nhất | Bằng chứng bàn giao |
| --- | --- | --- |
| 1 — Đối chiếu lỗi | Chốt ca phát triển và nhờ người đọc thứ hai đối chiếu | Gold, cách chấm và bất đồng được ghi riêng; giữ output gốc |
| 2 — Bám nguồn bằng chunk/ID | Thử offline toàn văn có ID phần/câu, công cụ kiểm chứng dựng trích dẫn | So baseline, đo đúng vị trí, đúng nghĩa, báo sai/bỏ sót và thời gian |
| 3 — Sửa tối thiểu | Thử riêng cách đề xuất sửa đúng chi tiết vi phạm | Giữ nội dung hợp lệ, ý đồ và điều để mở; không tự áp dụng |
| 4 — Ca mới và nhiều ràng buộc | Kiểm chứng ứng viên trên tập giữ riêng | Không dùng bộ đã tuning để tuyên bố khái quát; có đọc đối chiếu |
| 5 — Tích hợp có điều kiện | Đưa phương án có lợi vào runtime hiện có | Hợp đồng/nguồn và dữ liệu cũ tương thích; test bảo toàn đạt |
| 6 — Thời gian chờ | Đo tách planner/critic, thử một yếu tố mỗi lần | Giảm lỗi vượt ngân sách mà không đánh đổi chất lượng/nguồn |
| 7 — Demo toàn luồng | Đợt mới 3 tình huống × 3 lượt, diễn tập và PO duyệt | Đủ bằng chứng theo mục 4; không ghép benchmark rời rạc |
| 8 — Pilot và đối chiếu giá trị | N=5–8 người mới; so với cách dùng agent/chatbot | Đạt tiêu chí hiện có, ghi mức hỗ trợ và quyết định PO |

**Làm trước:** gói 1 → 2 → 3 → 4, chỉ mở tích hợp gói 5 khi có bằng chứng
phù hợp. Đo thời gian ở gói 6 có thể song song với thử nghiệm; mọi thay đổi
ứng viên phải được chốt trước đợt nghiệm thu gói 7. Gói 8 theo điều kiện pilot
hiện hành. Nếu thử nghiệm chưa có lợi thì ghi chưa đạt/cần thêm bằng chứng,
không tự tích hợp hoặc mở rộng kiến trúc để hoàn thành đủ tám ô.

ID/chunking là ứng viên xử lý lỗi đã thấy, không là điều kiện bắt buộc mới
của pilot khám phá. Lỗi vi phạm ý đồ, sai nguồn, mất dữ liệu và các lỗi chặn
khác vẫn phải được xử lý theo mục 4 dù chọn giải pháp kỹ thuật nào.

### Các bảo vệ áp dụng cho cả tám gói

- Giữ buffer, kể cả chỉ sửa tên dự án, lịch sử, kiểm tra revision và nguồn
  feedback theo [#7](p0-author-intent-revision-flow.md). Lỗi lưu, kết quả lưu
  chưa rõ, thao tác lặp, restore, hai cửa sổ hoặc response muộn không được
  xóa/ghi đè bản sửa; không tự cập nhật revision rồi ghi lại để vượt xung đột.
- Bản đọc và editor dùng cùng buffer; đọc hoặc điều hướng không lưu, đổi
  nội dung hay gọi AI. Không dựng nội dung giả khi chưa có draft. Tác giả
  chọn hoặc từ chối góp ý rồi tự sửa; chưa thêm tự áp dụng, trạng thái đã
  giải quyết, highlight, tự viết lại hoặc vòng AI sửa nội dung.
- Thẻ ý đồ hiện tại dùng nguyên văn nguồn đã lưu từ backend/`creator_answers()`;
  buffer mới phải có nhãn chưa lưu. Không lấy summary, ví dụ hoặc đề xuất AI
  làm quyết định tác giả; không đoán `confirmed/open/proposed` từ từ khóa.
- Feedback và tham chiếu giữ đúng draft/ngữ cảnh thực gửi AI, snapshot, dự án
  và artifact nguồn; lưu cùng nhau dưới kiểm tra revision. Feedback cũ giữ
  nguồn riêng và nhãn độ mới. Dữ liệu cũ thiếu nguồn/ID ghi rõ thiếu thông
  tin, không dựng lại bằng bản hiện tại hoặc cho điều hướng chưa xác minh.
- Giữ cả hai đường phục hồi phần 4 đã merge: tạo lần đầu chỉ lưu draft khi
  chưa có draft và brief/revision còn hợp lệ; tạo lại lưu đề xuất riêng,
  giữ bản đang viết tới khi tác giả nhận có kiểm tra nguồn và lịch sử.
  Giữ ID lượt tạo, kiểm tra nhận hai lần/mất response và khả năng mở lại
  sau timeout/lỗi provider/JSON lỗi. Không dùng raw dataset làm kho khôi
  phục, thêm retry tự động hoặc gắn feedback cũ cho plan mới. Plan thiếu
  review không tự đạt demo.
- Không dùng điểm AI, JSON hợp lệ hoặc ID tồn tại thay kết luận nội dung.
  Mảng góp ý rỗng hợp lệ; thiếu bằng chứng/ý đồ phải nêu điều chưa rõ, không
  bịa quote cho thông tin còn thiếu hoặc nói đã tiến bộ khi chỉ đọc một bản.
- Dùng ca tổng hợp trong repo; trải nghiệm riêng chỉ tái sử dụng khi tác giả
  đồng ý, không đưa nội dung riêng vào repo công khai. Chưa đụng prototype,
  model mặc định, provider hoặc dữ liệu dự án thật trong thử nghiệm offline.

### 3.1. Gói 1 — Đối chiếu lỗi và khóa cách chấm

Tách lỗi chép quote, gán sai phần, suy diễn không được bằng chứng hỗ trợ,
sửa quá rộng, vi phạm lựa chọn tác giả và khác biệt thẩm mỹ. Nhờ người đọc
thứ hai đối chiếu các ca khó: địa điểm, danh tính/quan hệ, nguyên nhân vắng
và kết mở. Bất đồng hoặc thiếu bằng chứng giữ riêng, không sửa gold hồi tố
để giúp một phương án thắng.

Khóa ca tuân thủ/vi phạm, bằng chứng kỳ vọng, chi tiết hợp lệ phải giữ và
giao thức trước lượt thử mới. Dùng prompt hẹp chạy mới cùng đợt làm baseline;
không lấy tỷ lệ lịch sử thay mẫu xấu. Ghi commit, prompt/schema, model/digest,
tham số, seed nếu có, thứ tự và mọi lỗi/abstain; không sinh lại lấy mẫu đẹp.

### 3.2. Gói 2 — Chunking theo cấu trúc và ID nguồn, chỉ thử offline

Harness đang có các phần story plan. Chia nguồn theo trường/phần rồi đoạn
hoặc câu khi cần; giữ lời thoại với người nói và quy tắc với ngoại lệ.
Tên phim, logline và từng mục ý đồ/hỏi đáp cũng có thể là đơn vị nguồn.
Giữ nguyên văn, không dùng AI tóm tắt hoặc viết lại để tạo chunk.

Mỗi ID chỉ hợp lệ trong đúng dự án và snapshot/khóa nội dung nguồn, có ánh
xạ tới trường/phần và vị trí đoạn gốc. ID phần hiện dựa vào thứ tự không
được coi là danh tính ổn định xuyên revision/reorder. Khi nguồn đổi, giữ
ánh xạ cũ cùng feedback cũ, tạo ánh xạ cho nguồn mới; không trỏ ID cũ sang
đoạn cùng tên hoặc cùng số thứ tự của bản mới.

Luồng thử: **khóa snapshot → chia đoạn có ID → gửi toàn văn có ID → model
chọn ID bằng chứng → code lấy nguyên văn → góp ý/sửa thủ công**. Vẫn gửi đầy
đủ draft và ý đồ/ràng buộc/hỏi đáp hiệu lực; không chọn top-k, giảm context,
embedding, vector database hoặc retrieval. Giữ riêng nguồn tác giả, draft,
kiến thức và ví dụ; kiến thức/ví dụ không trở thành sự thật của câu chuyện.

Model chọn ID; chương trình kiểm tra snapshot, trường và phạm vi ký tự rồi
dựng quote từ nguồn gốc. Không fuzzy match, chuẩn hóa chữ để ép khớp hoặc
tìm sang phần khác khi tham chiếu sai. Nhận xét vi phạm cần dẫn ràng buộc
tác giả và đoạn draft liên quan; mâu thuẫn nhiều phần phải dẫn đủ các phần.
Điều chưa có bằng chứng được ghi chưa rõ, không kết luận bản sạch chỉ vì
không tìm thấy. ID hợp lệ chỉ chứng minh vị trí, không chứng minh vi phạm.

So A: prompt hẹp/toàn văn với B: toàn văn chia cấu trúc có ID, trên cùng dữ
liệu/model/tham số. Chỉ thay biểu diễn/tham chiếu nguồn cần cho giả thuyết;
giữ hướng dẫn sửa và các yếu tố còn lại tương đương, chưa thêm call sửa hoặc
đổi rubric cùng lúc. Ghi rõ mọi khác biệt bắt buộc của schema thực nghiệm.
Chấm riêng chọn đúng nguồn, nguyên văn, nghĩa hỗ trợ kết luận, báo sai, bỏ
sót, abstain, tokens/thời gian và kết quả đủ phát hiện–bằng chứng–sửa.

**Bàn giao:** baseline và mọi output/lỗi, bảng so sánh thành phần và kết luận
có lợi/chưa rõ. Không sửa hợp đồng runtime từ kết quả kiểm tra ID đơn thuần.

### 3.3. Gói 3 — Đề xuất sửa tối thiểu

Giữ phương án bám nguồn đã chọn, thử riêng hướng dẫn sửa. Chỉ bỏ/đổi chi tiết
vi phạm và giữ hành động hợp lệ, vai, sắc thái, nguồn lực và điều cố ý để mở.
Xóa cả phần để bỏ một câu sai không tính là sửa đầy đủ. Phân biệt lựa chọn
sáng tạo cần hỏi tác giả với dữ kiện trái lựa chọn đã rõ.

**Bàn giao:** so cả bản tuân thủ và vi phạm; đo sửa đúng, giữ nội dung tốt,
báo sai/gợi ý gây hại và toàn chuỗi. Không tự áp dụng, không đổi nguồn hoặc
chỉ chấm các output qua gate mà bỏ các ca thất bại/abstain khỏi mẫu số.

### 3.4. Gói 4 — Ca mới, nhiều ràng buộc và quyết định ứng viên

Giữ một tập ca mới chưa dùng để chỉnh prompt, có nhiều ràng buộc và bằng
chứng ở nhiều phần, kể cả Production Notes. Bao phủ chăm sóc thường ngày,
vui/khó xử, quan sát lặng, vai/xưng hô và lựa chọn để mở. Chốt kỳ vọng trước
khi chạy; người đọc đối chiếu nội dung độc lập với validator. Nếu dùng ca
giữ riêng để chỉnh tiếp thì ghi thành ca phát triển và chuẩn bị tập mới.

**Bàn giao:** kết quả đủ mẫu số, so baseline, giới hạn và quyết định ứng viên
hoặc cần thử tiếp. Chỉ mở gói 5 khi có bằng chứng cải thiện thực chất, không
bù báo sai/vi phạm ý đồ bằng tỷ lệ ID hợp lệ cao. Không thêm ngưỡng phần trăm
review mới thay điều kiện demo/pilot đã chốt ở mục 4.

### 3.5. Gói 5 — Tích hợp nhỏ vào runtime khi có bằng chứng

Dùng workflow/editor/kho dự án hiện có; chốt hợp đồng nhỏ nhất cần cho nguồn
và nhận xét, không di trú toàn bộ hệ thống theo schema thử nghiệm. Tham chiếu,
quote do backend dựng và feedback phải giữ cùng snapshot. ID sai, sai phiên
bản, phạm vi không hợp lệ hoặc một trong các tham chiếu của mục không kiểm
tra được thì mục ấy không có liên kết điều hướng được xác minh; không đoán
lại bằng tên hoặc gắn sang draft hiện tại. Góp ý tổng thể/thiếu nguồn vẫn
đọc được với nhãn phù hợp. Chưa triển khai toàn bộ UX liên kết sâu của #7.

**Bàn giao:** test hợp đồng/API/UI phù hợp cho cả review sau tạo và sau sửa,
dữ liệu cũ, stale feedback, xóa/reorder phần, restore, hai cửa sổ, lưu lỗi/kết
quả chưa rõ, response muộn và cả hai đường phục hồi critic lỗi. Xác nhận
không mất buffer/lịch sử, không tự sửa/lưu khi điều hướng, mở lại đúng bản.
Tích hợp kỹ thuật đạt chưa đồng nghĩa model đủ chất lượng hoặc đạt demo.

### 3.6. Gói 6 — Đo và xử lý thời gian chờ

Đo tách planner, critic và phần lưu/điều phối trên cấu hình ứng viên. Thử một
yếu tố mỗi lần, giữ ca kiểm tra nội dung và dữ liệu; không mặc định đổi model,
cắt ngữ cảnh hoặc tăng số call sẽ cải thiện. Dùng checklist model và giữ mọi
kết quả, không chạy lại toàn bộ benchmark sau mỗi thay đổi tài liệu/UI nhỏ.

Ngân sách kỹ thuật đã dùng: làm rõ ≤45 giây, tạo plan kèm critic ≤120 giây,
review sau sửa ≤60 giây; bài demo đầy đủ ≤5 phút. Không nâng mốc hồi tố;
ngân sách kỹ thuật này chưa tự là phê duyệt nghiệm thu của PO. Chốt commit,
prompt/model/tham số và ngân sách trước gói 7; đổi cấu hình cần đợt nghiệm
thu mới, không gộp kết quả khác cấu hình.

### 3.7. Gói 7 — Kiểm chứng demo trên cấu hình cuối

Chạy mới đủ ba tình huống × ba lượt độc lập: làm rõ → plan → tác giả tự sửa
→ lưu → review → mở lại. Hỏi tối đa ba câu có ích, có thể không hỏi nếu đã
đủ rõ. Giữ toàn bộ kết quả, input/output, thời gian và đọc đối chiếu. Thử
nghiệm offline ở gói 1–6 không thay chín lượt này. Diễn tập đủ thao tác, đọc
và chờ thực; PO/người đọc duyệt live/bản ghi/chưa sẵn sàng theo mục 4.

### 3.8. Gói 8 — Pilot và so sánh giá trị

Thực hiện N=5–8 người mới với nhiệm vụ, phiên bản và mức hỗ trợ được chốt
trước. Ghi cả bỏ dở, lý do sửa/từ chối góp ý, khả năng giải thích và mong
muốn viết tiếp. Đối chiếu agent/chatbot với cùng chất liệu và cơ hội sửa;
không lấy điểm AI hoặc số tính năng làm lợi thế. Giữ nguyên mọi ngưỡng H0,
80%, ít nhất hai người muốn tiếp tục và quyết định PO ở mục 4.

### Để sau tám gói

Chưa triển khai embedding/retrieval, vector database, reranker hoặc giảm
context. Chỉ mở đợt đánh giá riêng khi có nhu cầu tìm kiếm hoặc dữ liệu chứng
minh giá trị so với toàn văn có ID/tìm từ khóa; không thêm hai gói này vào
tám gói đã chọn. Trạng thái `confirmed/open/proposed`, review hẹp và toàn bộ
liên kết sâu của #7 không là phụ thuộc mới của pilot. Giữ tour đã có, hoàn
tất nghiệm thu và điều chỉnh lời dẫn khi luồng ổn định; [PDF #5](story-plan-pdf-export.md)
đi sau demo. Sửa hai chiều story plan–kịch bản vẫn là hướng về sau ở mục 5.

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

Cập nhật kế hoạch harness và roadmap theo tám gói, phản ánh bốn phần MVP đã
merge và đưa chunking/ID nguồn vào thử nghiệm gói 2, tích hợp có điều kiện ở
gói 5. Giữ nguyên bảo vệ dữ liệu và các ngưỡng nghiệm thu của kế hoạch sản
phẩm. Chưa sửa workflow, prompt, rubric, schema, UI, dependency, model mặc
định, prototype hoặc dữ liệu dự án; chưa triển khai embedding/retrieval.
Không coi tám gói là đã hoàn thành, không chạy model hoặc pilot để nghiệm
thu trong lần cập nhật tài liệu này.

Multi-agent, RAG, workflow engine mới, model routing, tự áp dụng góp ý và công
cụ sản xuất không phải điều kiện cho MVP story plan. Mọi mở rộng về sau phải
được quyết định từ lỗi và nhu cầu quan sát được trong hành trình viết.
