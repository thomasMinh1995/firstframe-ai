# Định hướng và roadmap: phim ngắn đầu tiên cho người viết Việt Nam

- Ngày cập nhật: 22/10/2026.
- Trạng thái: kế hoạch sản phẩm; các thay đổi demo dưới đây chưa được triển khai.
- Phạm vi đợt tài liệu: lưu định hướng, thứ tự ưu tiên và tiêu chí kiểm chứng;
  không thay code, prompt, rubric, schema, dữ liệu dự án hoặc cấu hình model.
- Issue triển khai: [#26](https://github.com/thomasMinh1995/firstframe-ai/issues/26).
  Merge PR tài liệu không hoàn thành các hạng mục hoặc đóng issue triển khai.

## 1. Định hướng và người dùng đầu tiên

> FirstFrame giúp người Việt viết phim ngắn đầu tiên từ chất liệu của chính
> mình, hiểu các lựa chọn sáng tác và từng bước hoàn thiện kịch bản để chia
> sẻ với những người cùng làm phim.

Tập trung thị trường Việt Nam. Nhóm kiểm chứng đầu tiên là người Việt yêu
điện ảnh, đặc biệt là người trẻ chưa hoàn thành kịch bản phim ngắn, có một
trải nghiệm hoặc tình huống muốn kể nhưng thiếu phương pháp và người góp ý.
Người có kinh nghiệm vẫn có thể sử dụng; MVP kiểm chứng với nhóm đầu tiên.

```text
Khoảnh khắc → Story plan → Dàn cảnh → Viết và sửa kịch bản → Xuất kịch bản
```

Sản phẩm dừng ở xuất kịch bản để con người đọc, diễn, dàn dựng và quay.
Tuyển diễn viên, quản lý đoàn phim, lịch quay, quay, dựng và hậu kỳ thuộc
quy trình sản xuất tiếp theo. Video, diễn viên và cảnh quay do AI tạo nằm
ngoài định hướng. Hình minh họa tự động không còn là mốc roadmap chủ động.

Story plan giúp tác giả làm rõ câu chuyện trước khi viết chi tiết; có giá
trị để giữ và trao đổi nhưng chưa phải kịch bản hoàn chỉnh. Độ chi tiết phải
vừa với câu chuyện: một khoảnh khắc ngắn không cần một kế hoạch dài. Đích đến
của sản phẩm vẫn là kịch bản hoàn chỉnh và bản xuất có thể sử dụng.

## 2. Điểm khác biệt cần kiểm chứng

| Năng lực | Hành vi cần hướng tới | Bằng chứng từ người dùng |
| --- | --- | --- |
| Bắt đầu từ chất liệu chưa thành ý tưởng phim | Nhận một câu nói, hành động hoặc tình huống; hỏi ít câu có ích, không bắt điền đủ chủ đề, xung đột và kết thúc | Bắt đầu được mà ít cần người hướng dẫn |
| Phù hợp đời sống Việt Nam | Xưng hô, quan hệ, sinh hoạt và lời thoại hợp hoàn cảnh; chỉ hỏi vùng miền hoặc thời điểm khi chúng ảnh hưởng câu chuyện | Tác giả nhận ra và sửa được chỗ AI hiểu sai; người đọc đối chiếu hoàn cảnh |
| Cảm xúc thành hành động có thể thể hiện | Phát triển bằng hành vi, hình ảnh, âm thanh; ghi rõ chi tiết AI đề xuất | Người đọc hình dung được diễn tiến mà diễn viên thật có thể thể hiện |
| Học qua một lần sửa | Góp ý có chi tiết, tác động đến ý định và một lựa chọn sửa nhỏ | Tác giả tự sửa và giải thích được lựa chọn |
| Giữ ý định và nguồn lực | Giữ điều tác giả đã chọn hoặc để mở; giới hạn thực hiện chỉ chi phối khi có ích hoặc được tác giả yêu cầu | Không tự thêm quan hệ, biến cố, hòa giải hoặc chi tiết vượt giới hạn đã chọn |

Chuyện vui, khó xử, quan sát và khoảnh khắc lặng đều hợp lệ. Không bắt mọi
câu chuyện có cao trào, thay đổi nhân vật lớn hoặc kết thúc được giải quyết.
Phân biệt lựa chọn sáng tác với giới hạn tạm thời: hai nhân vật vì ý định
câu chuyện khác với hai nhân vật vì hiện chỉ có hai người bạn nhận đóng.

Các năng lực này là giả thuyết lợi thế, chưa phải bằng chứng FirstFrame tốt
hơn đối thủ. Công cụ phát triển câu chuyện, viết và xuất kịch bản là nhóm
cạnh tranh trực tiếp. Nền tảng tạo video AI chỉ liên quan gián tiếp. Tiếng
Việt, phạm vi hẹp hoặc nhãn “mentor” tự chúng chưa chứng minh khác biệt.

## 3. Hiện trạng và trải nghiệm demo

MVP có lưu dự án, làm rõ tối đa ba câu hỏi và để quyết định sau, tạo story
plan, sửa thủ công, lưu phiên bản và nhận góp ý. Chưa có dàn cảnh, biên tập
screenplay theo cảnh, PDF story plan hoặc xuất kịch bản hoàn chỉnh.

Tour frontend đã được triển khai trên `dev`; pilot và một số nghiệm thu
thủ công còn mở ở [#22](https://github.com/thomasMinh1995/firstframe-ai/issues/22).
Giữ tour hiện có; chỉ điều chỉnh nội dung liên quan khi luồng demo ổn định.

Demo dự kiến 3–5 phút:

1. Tác giả kể một khoảnh khắc nhỏ.
2. FirstFrame hỏi về một lựa chọn còn chưa rõ, hoặc đi tiếp nếu đã đủ rõ.
3. Tác giả đọc story plan có diễn tiến và hành động cụ thể.
4. Tác giả tự sửa một chi tiết chưa đúng ý.
5. Lưu và nhận góp ý trên đúng bản vừa sửa; giữ bản cũ trong lịch sử.

Nhận góp ý hiện không tự viết lại bản phát triển. Sửa ý tưởng hoặc ràng buộc
vẫn dùng luồng làm rõ lại đang có; không trình diễn như đã có chat viết lại.
Bản đọc và mọi đề xuất mới vẫn được gọi đúng là story plan.

## 4. Đợt P0: các thay đổi nhỏ phục vụ demo

| Thứ tự | Phạm vi nhỏ nhất | Điều kiện nghiệm thu |
| --- | --- | --- |
| P0.1 — Bắt đầu | Đổi lời giới thiệu, nhãn nhập và ví dụ; thu gọn thông tin phụ, giữ cơ chế tạo/lưu dự án | Người mới biết một chuyện nhỏ là đủ để bắt đầu; không phải giải thích thuật ngữ |
| P0.2 — Đọc câu chuyện | Bản đọc tên, tóm tắt, mở đầu, diễn tiến, kết thúc từ chính draft; các mục khác mở rộng, giữ trình sửa hiện có | Hình dung được diễn tiến và một chi tiết đáng nhớ; không thêm lượt AI để viết bản kể thứ hai; sửa chưa lưu vẫn được giữ và hiển thị đúng trạng thái |
| P0.3 — Điều muốn giữ | Phần thẻ ý đồ của #7: nguyên văn ý tưởng, ràng buộc và hỏi đáp hiệu lực từ cùng nguồn backend gửi AI | Phân biệt đã lưu/chưa lưu, lựa chọn tác giả/đề xuất AI; phản hồi cũ giữ ngữ cảnh nguồn riêng |
| P0.4 — Một lần sửa | Hướng dẫn sửa trực tiếp rồi lưu/nhận góp ý; dùng điều hướng sẵn có. Liên kết mục tiêu có cấu trúc tiếp tục theo #7 | Góp ý đọc đúng bản mới; không tự viết lại, lưu hoặc gọi AI khi chỉ điều hướng; giữ buffer, lịch sử và cảnh báo góp ý cũ |
| P0.5 — Duyệt và diễn tập | Ba tình huống Việt Nam, mỗi tình huống ba lượt toàn luồng độc lập trên đúng cấu hình demo; giữ mọi kết quả và đo thời gian | Chỉ demo trực tiếp khi đủ 9/9 lượt đạt điều kiện mục 4.1 và PO phê duyệt; nếu chưa đạt thì chỉ dùng bản ghi đã duyệt, ghi rõ là phát lại |

P0.5 bắt đầu song song khi chuẩn bị nội dung. Ba tình huống gồm một hành động
chăm sóc thường ngày, một chuyện vui/khó xử và một khoảnh khắc lặng. Khi triển
khai, chỉ chỉnh prompt, quy tắc, rubric hoặc cấu hình liên quan đến lỗi đã
quan sát; kiểm tra lại trên đúng cấu hình và đọc kết quả thực tế. Không suy
ra chất lượng sáng tác từ JSON hợp lệ hoặc điểm rubric của AI.

### 4.1. Điều kiện demo trực tiếp hoặc dùng bản ghi

- Trước khi chạy, chốt ba brief, điều muốn giữ, câu trả lời/để mở, một thao
  tác sửa thủ công và kỳ vọng cần kiểm tra cho từng ca. Áp dụng cách đọc
  kết quả trong [checklist đánh giá model](../prompt-evaluation.md).
- Mỗi ca chạy ba lần từ dự án tạm độc lập: làm rõ → plan → sửa → lưu → review.
  Cố định commit, phiên bản prompt, model identifier/digest và cấu hình;
  ghi seed nếu có. Lưu đủ input, output, lỗi, thời gian từng tác vụ và kết
  luận của cả chín lượt, kể cả lượt không tạo được output; không bỏ lượt
  xấu hoặc sinh lại đến khi chọn được mẫu đẹp.
- Một lượt đạt khi hoàn thành luồng, giữ dữ liệu/phiên bản, phản hồi đọc đúng
  draft và không có lỗi chặn. Lỗi chặn gồm: vi phạm lựa chọn/ràng buộc rõ
  ràng; bịa quyết định tác giả hoặc dẫn chứng; tự viết lại draft; góp ý sai
  nguồn; mất/ghi đè nội dung; tác vụ lỗi hoặc thiếu kết quả khiến không thể
  tiếp tục. Góp ý phải đúng chi tiết và có bước sửa khả thi; không bắt sinh
  vấn đề nếu bản không có lỗi có căn cứ. Khác biệt sở thích được ghi riêng.
- Người diễn tập chốt trước ngân sách chờ cho từng tác vụ AI và kịch bản
  trình bày tối đa năm phút, gồm cả thao tác/đọc và thời gian chờ thật.
  Chỉ chạy trực tiếp khi 9/9 lượt đạt, đều trong ngân sách đã chốt và một
  lần diễn tập đủ bài nằm trong năm phút. Không tăng ngân sách sau khi thấy
  kết quả để đổi lượt trượt thành đạt.
- PO (chủ sản phẩm) duyệt cùng người đọc có kinh nghiệm, ghi quyết định
  **trực tiếp / chỉ bản ghi / chưa sẵn sàng**, ngày, cấu hình và bằng chứng
  trong #26. Thiếu bằng chứng, có lượt trượt hoặc đổi cấu hình thì chưa đủ
  điều kiện trực tiếp; sau sửa cần một đợt đủ chín lượt mới, giữ kết quả cũ.
- Chế độ chỉ bản ghi dùng chuỗi brief–plan–bản sửa–review đã được duyệt đúng
  nguồn; ghi rõ phát lại và mọi hiệu đính của người biên tập. Đây chỉ là
  nghiệm thu nội dung phát lại, không phải nghiệm thu luồng trực tiếp hay
  chất lượng model nói chung. Nếu đang demo gặp lỗi, quá ngân sách, hoặc
  câu chuyện lệch ý rõ ràng: báo sự cố rồi chuyển sang bản ghi đã duyệt.
  Nếu bản ghi cũng chưa được duyệt, hoãn phần đó; không thay kết quả âm thầm.

Không mở rộng đợt demo sang trình viết screenplay, tự áp dụng góp ý, tạo
video/ảnh, marketplace, cộng đồng trong ứng dụng hoặc quản lý sản xuất.

## 5. Thứ tự roadmap và các kế hoạch đang có

| Mốc | Kết quả và điều kiện chuyển bước |
| --- | --- |
| M1 — Story plan đúng ý | Hoàn thành đợt P0 theo chế độ demo được duyệt và pilot đạt mục 6.1; phát lại không thay thế nghiệm thu luồng pilot |
| M1 tiếp — Sửa và chia sẻ | Hoàn thiện góp ý có mục tiêu theo #7; xuất đúng story plan đã chọn theo #5 |
| M2 — Dàn cảnh | Thêm, bỏ, sắp xếp và sửa cảnh có hành động, mục đích, liên kết; kiểm chứng tác giả dùng được để viết tiếp |
| M3 — Viết và sửa kịch bản | Viết hành động/lời thoại theo cảnh, góp ý cụ thể, giữ quyết định và phiên bản; ít nhất một vòng đọc sửa |
| M4 — Xuất kịch bản | Xuất bản đã chọn, giữ nguyên nội dung và tiếng Việt đầy đủ, định dạng dễ đọc để cộng sự sử dụng; đây là điểm bàn giao của sản phẩm |
| Về sau — Kịch bản dài | Chỉ nghiên cứu khi người đã hoàn thành phim ngắn có nhu cầu và chất liệu phát triển; vẫn dừng ở xuất kịch bản |

Giữ số hiệu các milestone cũ để tham chiếu; thứ tự ưu tiên nằm ở bảng này và
[roadmap](../roadmap.md), không suy ra từ số 1.1/1.2.

- [#7 — ý đồ và vòng sửa](p0-author-intent-revision-flow.md): giao phần thẻ ý
  đồ trước; không bỏ các yêu cầu nguồn feedback, độ mới và bảo vệ bản sửa.
  Điều hướng góp ý đến trường cần sửa chỉ triển khai khi mục tiêu được kiểm
  tra; chưa có liên kết hợp lệ thì hướng dẫn sửa thủ công.
- [#5 — PDF story plan](story-plan-pdf-export.md): sau đợt demo, giúp đọc và
  trao đổi. Đây không phải bản xuất screenplay của M4.
- [#22 — tour](new-user-tour.md): giữ chức năng đã triển khai, tiếp tục nghiệm
  thu; tránh xây lại tour trước khi biết luồng mới cần thay gì.
- Harness: ưu tiên lỗi chặn hoặc làm sai hành trình viết; thử nghiệm kỹ thuật
  không tự động trở thành điều kiện chặn mọi cải thiện giao diện.
- Hình minh họa tự động không còn là ưu tiên; không xây hạ tầng “cho phim
  dài” trong MVP. Giữ chất liệu gốc và lịch sử hiện có để viết tiếp về sau.

## 6. Pilot và kiểm chứng khác biệt

Mời 5–8 người Việt chưa hoàn thành kịch bản phim ngắn, dùng trải nghiệm của
chính họ. Đây là pilot khám phá, không đại diện toàn thị trường.

Ghi nhận chỗ cần hỗ trợ, điều bị AI tự thêm sai, số lần sửa, lý do bỏ dở và
việc tác giả có thể giải thích một lần sửa hay không. Hỏi họ có muốn giữ,
chia sẻ hoặc viết tiếp bản phát triển. Mời người có kinh nghiệm viết/làm
phim đọc một số bản để đánh giá hành động có thể thể hiện và chỗ còn mơ hồ.

So sánh một số trường hợp với chatbot tác giả quen và một công cụ trực tiếp
như Cinequill hoặc Screenwriting.ai. Dùng cùng chất liệu, ràng buộc và nhiệm
vụ; cho mỗi công cụ đủ ngữ cảnh và cơ hội sửa. Không coi quảng bá tính năng
là bằng chứng chất lượng hoặc kết quả pilot nhỏ là lợi thế thị trường đã có.

### 6.1. Điều kiện pilot đạt và chuyển sang M2

- Trước pilot, PO chốt số người bắt đầu N trong khoảng 5–8, phiên bản ứng
  dụng/model và cùng một phiếu nhiệm vụ. Nhiệm vụ gồm nhập khoảnh khắc, làm
  rõ/tạo plan, diễn đạt lại diễn tiến vừa đọc, tự sửa một chi tiết, lưu,
  nhận góp ý mới, mở lại đúng bản đã lưu và giải thích lựa chọn sửa.
- Người quan sát ghi riêng từng người và từng bước: hoàn thành/chưa hoàn
  thành, điểm mắc, lỗi, lý do bỏ dở và mức trợ giúp. H0 = chỉ dùng hướng dẫn
  chung cùng tour/tài liệu trong sản phẩm; H1 = được người quan sát nhắc
  từng bước hoặc chỉ chỗ thao tác; H2 = được gợi ý nội dung cần viết/sửa
  hoặc thao tác hộ. Chỉ hoàn thành toàn nhiệm vụ ở H0 mới tính độc lập.
  Người đã bắt đầu nhưng bỏ dở vẫn thuộc N và không tính đạt; không thay
  bằng người thành công hơn để nâng tỷ lệ.
- Ngưỡng vận hành đề xuất: ít nhất 80% của N hoàn thành độc lập, làm tròn
  lên (N=5/6/7/8 cần 4/5/6/7 người). Ít nhất hai người trong nhóm đạt muốn
  viết tiếp chính bản của họ; ghi bước tiếp họ muốn làm và điểm còn mắc.
  Đây là ngưỡng quyết định của pilot nhỏ, không phải bằng chứng thị trường.
- Không còn lỗi chặn chưa xử lý trong luồng pilot: mất/ghi đè nội dung,
  không lưu/mở lại được, phản hồi sai draft/ngữ cảnh, AI vi phạm điều tác
  giả đã chọn rõ hoặc lỗi tác vụ khiến không thể hoàn thành. Ghi ID/bằng
  chứng lỗi; sau sửa xác nhận lại tình huống lỗi trên phiên bản ứng viên.
- PO quyết định **đạt / chưa đạt / cần thêm bằng chứng** trong #26 sau khi
  xem bảng kết quả N người và nhận xét người đọc có kinh nghiệm. Chỉ ưu tiên
  M2 khi đủ ngưỡng, có nhu cầu viết tiếp, không còn lỗi chặn và PO ghi đạt.
  Thiếu điều kiện nào thì tiếp tục sửa M1; bản ghi demo không bù cho pilot
  trượt. Không hạ ngưỡng hồi tố: thay nhiệm vụ/ngưỡng phải chốt đợt mới và
  giữ báo cáo cũ. Nếu đổi phiên bản giữa pilot, tách kết quả theo phiên bản,
  không gộp các phiên bản để đạt ngưỡng; đợt mới vẫn cần đủ N=5–8.

Đánh giá hoàn thành kịch bản khi M3/M4 khả dụng; không đo MVP story plan
bằng tỷ lệ hoàn thành screenplay chưa được hỗ trợ. Lưu bằng chứng thử nghiệm
và bản ghi theo cơ chế dataset hiện có, chỉ tái sử dụng nội dung được chọn
với sự đồng ý của tác giả; không đưa trải nghiệm riêng vào repo công khai.

## 7. Hoàn tất đợt cập nhật tài liệu

- Lưu kế hoạch này; đồng bộ README, roadmap, domain và design decisions.
- Ghi rõ thị trường Việt Nam, nhóm đầu tiên và điểm bàn giao xuất kịch bản.
- Phân biệt khả năng đã có với thay đổi demo, milestone sau và hướng dài hạn.
- Tạo issue theo dõi triển khai, tham chiếu #5/#7/#22 thay vì tạo lại chúng.
- PR tài liệu liên kết issue bằng tham chiếu thông thường, không dùng từ khóa
  tự đóng. Giữ issue mở để chia nhỏ và triển khai sau.
- Chỉ commit tài liệu của đợt này; giữ nguyên các thay đổi local đang có.
