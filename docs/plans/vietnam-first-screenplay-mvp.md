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
| P0.5 — Duyệt và diễn tập | Ba tình huống Việt Nam trên đúng model/config demo; đo thời gian chờ; bản ghi dự phòng được duyệt và ghi rõ nguồn | Không có lỗi nghiêm trọng về ý định trong mẫu được chọn; góp ý có ích, thời gian chờ được báo đúng; bản ghi không được trình bày như chạy trực tiếp |

P0.5 bắt đầu song song khi chuẩn bị nội dung. Ba tình huống gồm một hành động
chăm sóc thường ngày, một chuyện vui/khó xử và một khoảnh khắc lặng. Khi triển
khai, chỉ chỉnh prompt, quy tắc, rubric hoặc cấu hình liên quan đến lỗi đã
quan sát; kiểm tra lại trên đúng cấu hình và đọc kết quả thực tế. Không suy
ra chất lượng sáng tác từ JSON hợp lệ hoặc điểm rubric của AI.

Không mở rộng đợt demo sang trình viết screenplay, tự áp dụng góp ý, tạo
video/ảnh, marketplace, cộng đồng trong ứng dụng hoặc quản lý sản xuất.

## 5. Thứ tự roadmap và các kế hoạch đang có

| Mốc | Kết quả và điều kiện chuyển bước |
| --- | --- |
| M1 — Story plan đúng ý | Hoàn thành đợt P0 và pilot; người mới tự đọc/sửa/lưu được bản muốn tiếp tục |
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

Chỉ ưu tiên M2 khi có người dùng muốn viết tiếp và xác định được họ mắc ở
đâu. Đánh giá hoàn thành kịch bản khi M3/M4 khả dụng; không đo MVP story plan
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
