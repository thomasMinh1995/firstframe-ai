# Kế hoạch cải tiến harness FirstFrame

- Cập nhật: 26/10/2026. Ưu tiên đối chiếu nghiệm thu #7 → xác nhận và sửa
  một lỗi ảnh hưởng lớn → kiểm chứng luồng người dùng. Thay lịch tám gói
  bằng phạm vi nhỏ theo lỗi thực tế; không mở thêm kiến trúc harness.
- Trạng thái: nền tảng bốn phần, phần kỹ thuật #7/tour (PR #38) và bộ thử
  offline (PR #40, issue #39) đã merge; #7 chưa được nghiệm thu chất lượng
  hoặc pilot. Không triển khai lại phần đã có, không coi test là nghiệm thu.
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
- Luồng review story plan hiện dùng CardReview, ghép nhận xét–gợi ý–mục
  tiêu qua revision_notes và snapshot nguồn sau PR #38; dữ liệu góp ý cũ
  vẫn đọc được. Hợp đồng khóa mục tiêu lịch sử hoặc FramingAssessment
  offline không phải hợp đồng cần di trú vào runtime.
- Đã có lời dẫn/bản đọc (PR #30), thẻ ý đồ đã lưu và nguồn feedback (PR #31),
  vòng sửa thủ công (PR #32), phục hồi plan khi critic lỗi (PR #33).
  Tạo lần đầu lưu draft trước critic khi nguồn hợp lệ; tạo lại giữ đề xuất
  riêng tới khi tác giả nhận, không ghi đè bản đang viết.
- PR #36 đã giao workspace và góp ý cạnh card; PR #38 hoàn thiện phần kỹ
  thuật [P0 #7](p0-author-intent-revision-flow.md): ghép nguồn/mục tiêu và
  điều hướng sửa thủ công, đồng thời cập nhật tour. Đối chiếu tiêu chí #7
  với bằng chứng hiện có trước khi mở task code mới. Merge không đóng #7.
- [UI workspace](approved-story-workspace.md) đã chốt, #35 hoàn thành.
  Giữ UI và tour đã có; chỉ chỉnh hướng dẫn nếu một sửa lỗi làm đổi luồng,
  sau khi kỹ thuật ổn định và trước nghiệm thu/pilot #7. #22 vẫn giữ các
  mục pilot, thiết bị thực và tổng kết chưa đủ bằng chứng.
- PR #40 / issue #39 bàn giao công cụ kiểm chứng offline góc nhìn và gate
  xuất bản. [Đợt 60 lượt](../evaluations/issue-7-framing-v1-guardrail-2026-10-25.md)
  không block/giữ oan nhưng bỏ sót 4/16 lượt phải block, có 28 cảnh báo thừa.
  Đây là mô phỏng gate, không phải tỷ lệ story plan sai của runtime. Giữ
  bằng chứng, hoãn tự động block; không tiếp tục mặc định một chuỗi thử
  prompt/model để biến bộ công cụ này thành điều kiện hoàn tất #7.
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

## 3. Ba việc ưu tiên để hoàn tất #7

Phần này thay lịch H1–H8 trước đây. Không có yêu cầu hoàn thành tám gói hoặc
hoàn thiện một critic tổng quát trước khi kiểm chứng MVP. Harness phục vụ
vòng đọc–sửa story plan đang có, không trở thành một sản phẩm riêng.
Thứ tự ngày 26/10/2026 thay các tham chiếu lịch tám gói trong tài liệu cũ;
không thay tiêu chí nghiệm thu của #7, tour hoặc kế hoạch sản phẩm.

| Việc | Phạm vi nhỏ nhất | Bàn giao và điểm dừng |
| --- | --- | --- |
| 1 — Đối chiếu nghiệm thu #7 | Rà từng tiêu chí với code/test/bằng chứng sau PR #38; tách phần kỹ thuật đã giao, lỗi thực tế và bằng chứng người dùng còn thiếu | Danh sách phần đã chứng minh và phần chưa đạt; không tự đóng #7 hoặc tạo lại feature đã merge |
| 2 — Xác nhận và sửa một lỗi ảnh hưởng lớn | Nhờ người đọc có kinh nghiệm đối chiếu một số ca đã lưu; chọn một lỗi tác động tới ý đồ hoặc vòng sửa, thử một thay đổi có giả thuyết rõ | So trước/sau trên ca liên quan và đối chứng; chỉ tích hợp khi có ích và qua bảo vệ dữ liệu; không có lợi thì dừng hướng đó, ghi chưa đạt |
| 3 — Kiểm chứng luồng người dùng | Khi ứng viên ổn định, kiểm chứng #7 + tour trên cùng cấu hình, rồi demo/pilot theo mục 4 | Đủ bằng chứng theo tiêu chí hiện có, ghi quyết định PO; thiếu bằng chứng/lỗi chặn vẫn là chưa đạt |

### 3.1. Đối chiếu trước khi viết thêm code

Dùng tiêu chí của [#7](p0-author-intent-revision-flow.md) và bằng chứng đã có;
không lấy toàn bộ checkbox chưa cập nhật làm danh sách phải triển khai lại.
Ghi rõ phần nào đã merge/qua test và phần nào còn thiếu model thật, đọc đối
chiếu hoặc pilot. Không suy nghiệm thu chất lượng từ test vận chuyển dữ liệu.

Đối chiếu với người đọc để phân biệt sai nguồn, vi phạm ý đồ, sửa gây hại
và khác biệt sở thích. Giữ bất đồng, không sửa nhãn hồi tố để model đạt.
Việc đọc một số ca này dùng để chọn lỗi cần xử lý, không thay pilot hoặc
tạo một bộ gold tổng quát mới làm phụ thuộc cho mọi cải thiện.

Nếu đối chiếu không còn lỗi cần sửa, chuyển thẳng sang việc 3 để bổ sung
bằng chứng người dùng còn thiếu; không tạo task code cho đủ ba bước.

### 3.2. Một lỗi, một thay đổi, một quyết định

Chọn lỗi đã xác nhận ảnh hưởng lớn nhất đến việc đọc plan đúng hướng hoặc
tự sửa. Chốt trước giả thuyết, ca tuân thủ/vi phạm, bằng chứng kỳ vọng, chi
tiết phải giữ và cách chấm. Nếu cần gọi model, đóng băng commit, prompt/schema,
model/digest, tham số và thứ tự trước lượt đầu; giữ mọi input/output/lỗi,
không retry chọn lọc hoặc bỏ các ca thất bại/abstain khỏi mẫu số. Không đổi
nhãn theo kết quả. Ca dùng chỉnh prompt không còn là ca giữ riêng.

Chỉ thay một yếu tố cần cho giả thuyết và so baseline tương đương. Đo riêng
chọn đúng nguồn, nghĩa hỗ trợ kết luận, báo sai/bỏ sót, bước sửa và thời gian
phù hợp lỗi đang xử lý; không lấy ID đúng hoặc JSON hợp lệ làm kết luận tốt.
Giữ bằng chứng ở nhiều phần khi mâu thuẫn cần nhiều phần để hiểu; không
đánh giá câu sửa riêng mà bỏ tác động lên phần còn lại của draft.

Chunk/ID, hướng dẫn sửa tối thiểu và ca mới là công cụ kiểm tra của việc này,
không còn là ba dự án nối tiếp phải hoàn thành. Dùng lại nguồn/ID của #7;
giữ toàn draft và ý đồ hiệu lực, không tự giảm context. Chỉ thử biểu diễn
nguồn khác khi lỗi đã xác nhận nằm ở chọn nguồn, không xây hệ ID song song.
Không chép schema offline vào runtime hoặc di trú dữ liệu chỉ vì benchmark
qua. Nếu có lợi, tích hợp thay đổi nhỏ vào luồng đang có và chạy test bảo
toàn, tương thích dữ liệu cũ, nguồn và UI bị ảnh hưởng.

Nếu thay đổi không có lợi hoặc kết quả chưa rõ, lưu kết luận và dừng ứng
viên đó. Không tự thêm tầng judge, đổi model liên tiếp, mở bộ thử lớn hơn
hoặc thêm schema để tiếp tục cùng hướng. Vòng thử khác cần nêu được lỗi/câu
hỏi còn lại từ đối chiếu, không tự mở rộng công việc. Lỗi chặn chưa xử lý vẫn chặn
nghiệm thu #7/demo/pilot; điểm dừng thử nghiệm không phải quyền bỏ qua lỗi.

Chỉ đo/tối ưu sâu tác vụ đã vượt ngân sách hoặc cản trở vòng viết thực tế;
không mở dự án hiệu năng riêng. Ngân sách kỹ thuật đã dùng giữ nguyên: làm
rõ ≤45 giây, tạo plan kèm critic ≤120 giây, review sau sửa ≤60 giây; toàn
bài demo ≤5 phút. Không nâng mốc hồi tố; đây chưa tự là phê duyệt PO.

### 3.3. Quay lại hành trình người dùng

Giữ UI #7 và tour đã merge. Nếu sửa lỗi làm đổi thao tác, cập nhật đúng phần
tour bị ảnh hưởng khi luồng ổn định, trước kiểm chứng/pilot; giữ sáu chặng,
tiến độ, quyền bỏ qua/mở lại. Không lên lịch làm lại tour hoặc workspace.

Kiểm chứng làm rõ → plan → tác giả tự sửa → lưu → review → mở lại trên cùng
ứng viên, đọc đúng draft/ngữ cảnh đã sửa. Ghi rõ chất lượng model và thao tác
người dùng, không lấy test mock hoặc benchmark rời rạc thay toàn luồng. Khi
đủ điều kiện, chạy đợt demo và pilot theo nguyên mục 4, không gộp cấu hình
khác nhau thành một đợt đạt. Không chạy lại benchmark lớn sau sửa tài liệu/UI
nhỏ nếu không có lỗi hoặc thay đổi liên quan cần xác nhận.

Đóng #7 chỉ khi đủ tiêu chí/bằng chứng của chính issue. Các mục #22 chưa có
bằng chứng tiếp tục mở riêng; không dùng pilot khám phá hay người đọc đối
chiếu thay pilot/nghiệm thu đã chốt của #7, #22 hoặc #26. Không bắt #7 chờ
hoàn thành mọi cải tiến harness, cũng không chờ đóng toàn bộ #22 mới xử lý
các lỗi hẹp hoặc bước tiếp phù hợp. Thiếu điều kiện demo/pilot thì ghi chưa
sẵn sàng, không ép nghiệm thu để đi tiếp milestone.

### Các bảo vệ giữ nguyên cho mọi công việc

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

### Phạm vi hoãn, chỉ mở lại khi có nhu cầu cụ thể

- Tự động block đạo đức/xuất bản, thêm tầng phân loại góc nhìn/judge hoặc
  dùng model làm cổng duyệt tác phẩm. Giữ bộ thử PR #40 làm bằng chứng giới
  hạn, không tạo phụ thuộc mới cho MVP. Người đọc vẫn ghi nhận lo ngại đạo
  đức/ngôn từ/văn hóa theo ngữ cảnh; hoãn tự động hóa không bỏ kiểm tra đó.
- Embedding/retrieval, vector database, reranker, top-k hoặc giảm context;
  chưa có căn cứ cần chúng cho một story plan ngắn đang gửi đầy đủ nguồn.
- Routing nhiều model, multi-agent, workflow engine mới và các vòng đổi
  model/chỉnh prompt không có điểm dừng. Không mặc định công cụ nào giải
  quyết được lỗi nghĩa đã thấy dù nguồn trích đúng.
- Schema lựa chọn mở rộng, tự áp dụng/tự viết lại, đồng bộ story plan–kịch
  bản và screenplay editor. Hướng sửa hai chiều ở mục 5 giữ cho giai đoạn sau.

[PDF #5](story-plan-pdf-export.md) vẫn sau demo và không chặn #7. Các nghiệm
thu #22 còn thiếu theo dõi riêng. Chỉ ưu tiên phần mở rộng khi bằng chứng từ
vòng viết cho thấy nó cần thiết; không tái khởi động tám gói như checklist.

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

Thu gọn lịch tám gói thành đối chiếu nghiệm thu #7 → xác nhận/sửa một lỗi
ảnh hưởng lớn → kiểm chứng luồng người dùng. Cập nhật trạng thái kỹ thuật
đã merge qua PR #38 và bằng chứng offline PR #40; không coi các PR này là
nghiệm thu #7 hoặc chất lượng model. Giữ nguyên bảo vệ dữ liệu ở mục 3 và
nguyên tiêu chí demo/pilot ở mục 4, hướng sửa hai chiều về sau ở mục 5.

Chỉ sửa tài liệu này và roadmap. Không sửa code, prompt/schema, runtime,
model, prototype hoặc dữ liệu; không gọi model, chạy pilot, tạo PR, cập nhật
issue hay tự ghi nhận nghiệm thu trong lần cập nhật tài liệu này.
