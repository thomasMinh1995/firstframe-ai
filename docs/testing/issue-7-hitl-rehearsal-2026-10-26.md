# Diễn tập vòng sửa #7 + tour bằng output đã lưu — 26/10/2026

**Kết luận: đã diễn tập thao tác trên bốn ca QA; chưa có nghiệm thu người dùng,
model hoặc toàn luồng.** Không có người tham gia thật, không gọi model mới.
Thực hiện theo [phiếu HITL](issue-7-hitl-session-sheet.md); không thay các tiêu
chí #7/#22/#26 hoặc coi N1/N2 đã được khắc phục.

## Phiên bản và phương thức

- Nền tài liệu: dev sau PR #44, `16ce7209ed20349ee92237de8677a093635bceb1`.
  Frontend không đổi từ bản HITL đã kiểm chứng của PR #43. Dùng production
  build có sẵn `0TewMJITRYRhNfQOeFsi_`, Chrome 155.0.8059.86, 1440×1000.
- Chế độ phát lại, **0 người tham gia**. Codex điều khiển browser và dùng
  quyết định tác giả đã xác nhận; tương đương thao tác hộ H2, không phải đo
  H0/H1/H2 của người thật hoặc một người dùng hoàn thành độc lập.
- Chọn trước baseline lượt 1 của mỗi ca trong đợt optional-single-card đã
  lưu; không chọn lại output tốt. Giữ nguyên nhận xét/gợi ý AI, ý đồ và draft
  đầu vào. Không phát lại ứng viên thành runtime đã tích hợp.
- Output gốc: Qwen 2.5 7B, digest
  `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`,
  Ollama 0.40.11, temperature 0.3, context 16384, timeout 180 giây; seed
  không được ép trong đợt gốc. Đây là cấu hình output cũ, không phải lượt
  suy luận mới hoặc phép đo độ trễ hiện tại.
- Browser dùng profile và project API giả riêng; save/reopen chỉ trên kho
  QA trong bộ nhớ. Draft đầy đủ lấy từ snapshot API cũ, đối chiếu card/answer
  với input model đã lưu. Artifact/project ID cho UI được dựng riêng và ghi
  rõ là replay; không coi chúng là artifact backend mới thực sự phát sinh.
- Mọi yêu cầu AI bị chặn ở lớp API giả, gồm `/review/stream`; request ngoài
  frontend/project QA cũng bị chặn. Không khởi động backend, Ollama hoặc
  dùng dữ liệu dự án thật. Script diễn tập nằm trong thư mục tạm, không sửa
  code, prompt/schema, plan, model hoặc prototype của repo.

## Nhật ký nhiệm vụ theo phiếu

| Bước | Quan sát trong diễn tập | Phạm vi và trợ giúp |
| --- | --- | --- |
| 1 — Mở dự án/tour | Mở bốn dự án QA đã chuẩn bị; ca đầu đi qua đủ sáu bước tour rồi hoàn tất. Các ca sau mở/đóng tour, mở lại được sau reload | AI thao tác hộ, không H0. Không diễn tập người mới bắt đầu từ dự án trống. Control tour không đổi buffer/kho QA hoặc tạo request API |
| 2 — Ý đồ/làm rõ/tạo plan | Hiển thị ý đồ và draft cũ đúng ca | Chỉ đọc snapshot. Làm rõ/tạo plan mới chưa được kiểm chứng |
| 3 — Đọc diễn tiến | Kiểm tra card theo draft và chụp bằng chứng | Không có lời diễn đạt lại của người thật; không suy ra mức hiểu câu chuyện |
| 4–5 — Đọc ý đồ/góp ý/nguồn | Có thông điệp AI chỉ tham khảo; mở nguồn, chọn target đúng snapshot, đọc được output cũ | Không có request ghi do đọc/chọn. Quyết định giữ/sửa lấy từ trao đổi trước, không chứng minh người mới tự phát hiện lời khuyên sai |
| 6 — Tự sửa | AI nhập theo lựa chọn tác giả ở ba ca; một ca giữ nguyên. Các phần khác được giữ | Tương đương H2. Ca giữ nguyên không tính thành vòng sửa; ví dụ thoại ca 2 chưa phải câu cuối tác giả mới xác nhận |
| 7 — Lưu/review | Ba PUT vào kho QA giả; feedback cũ mất quyền điều hướng và vẫn giữ nguồn cũ. Ba request review mới bị trả 503 có chủ ý bởi lớp replay | Không có output mới cho draft đã sửa, không gắn output cũ sang nguồn mới. Lỗi khởi chạy review hiển thị là kết quả giả lập có chủ ý, không phải lỗi provider vừa quan sát |
| 8 — Mở lại | Mở lại đúng bản QA đã lưu, kiểm tra chữ thực hiển thị và câu trả lời; tour không tự bật lại, vẫn mở/đóng thủ công được | Chỉ kiểm tra frontend + kho giả, chưa chứng minh lưu/mở lại backend thật hoặc người dùng hiểu đúng nguồn |

Mỗi thao tác có thời điểm và bằng chứng trong `results.json`. Không chấm
điểm năng lực tác giả hoặc tỷ lệ độc lập từ các bước tự động này. Có một lượt
sửa thao tác ở mỗi ca được chỉnh, **chưa hoàn tất hai vòng sửa của #7** vì
không có góp ý mới trên bản sau sửa; không tạo thêm sửa giả để đủ lượt.

## Góp ý, quyết định và tác động theo từng ca

| Ca / output cũ | Phần dùng được hoặc có nguy cơ dẫn sai | Quyết định được phát lại và kết quả thao tác |
| --- | --- | --- |
| 1 — `forbid-reconciliation-baseline-1` | Nhận xét đọc ngược phủ định. Ví dụ sửa bỏ lời chốt nhưng lặp nhịp im lặng; không coi toàn góp ý là đúng | Giữ kết mở, bỏ nội dung lời tha thứ ở card 4; giữ card 3 chưa đáp. Lưu/mở lại giữ đúng nội dung; UI còn card trống, xem giới hạn bên dưới |
| 2 — `allow-reconciliation-baseline-1` | Gắn mismatch vào cảm giác đột ngột, đề nghị cha cầu xin tha thứ; đây không phải mâu thuẫn đã chứng minh | Giữ im lặng rồi trả lời; nhập ví dụ “Cha, mọi thứ đã qua rồi…” và làm rõ câu trả lời theo mong muốn đón nhận/thoại tự nhiên đã trao đổi. Ý đồ mới hiện đúng sau lưu; góp ý cũ vẫn giữ ý đồ gốc, không coi nó đã đọc yêu cầu mới |
| 3 — `open-ending-clean-baseline-1` | Đặt thư rồi đặt chìa khóa bị coi là mâu thuẫn và bị đề nghị bỏ một vật; chưa có căn cứ | Từ chối hướng sửa, giữ nguyên cử chỉ kết mở; không có PUT hoặc review. Đây là quyết định giữ, không tính một vòng sửa hoàn tất |
| 4 — `passport-violation-baseline-1` | Nhận ra hành vi kiểm soát trái ý đồ; hướng xin lỗi và không giấu hộ chiếu có ích dù không viết hộ cảnh | Thay bằng cha đặt thư xin lỗi lên bàn, giữ con gái nhìn thư/chưa mở. Lưu/mở lại đúng bản QA; không ép đọc, tha thứ hoặc ở lại |

Các quyết định trên là nội dung người dùng đã cho trước, do AI nhập trong
diễn tập; không phải phản hồi/đánh giá mới của người tham gia. Chưa có người
đọc độc lập chấm các phiên này; giữ kết quả chấm model/HITL cũ nguyên vẹn.

## Giới hạn thao tác phát hiện ở ca 1

Editor hiện cho xóa chữ trong card nhưng không có control xóa hẳn một card/
section. Diễn tập đã làm trống section Ending cuối; sau lưu/mở lại nó vẫn
hiện card “Chưa có nội dung.”, thay vì biến mất khỏi đường kể. Không báo là
đã xóa cấu trúc card 4. Đây là giới hạn cần trao đổi nếu việc bỏ hẳn card là
nhu cầu thực tế; chưa tự nâng thành yêu cầu mới của #7 hoặc triển khai nút xóa.

## Bằng chứng còn thiếu và việc tiếp theo

- Người mới thật: hiểu thông điệp HITL, ý đồ/nguồn, tự chọn hoặc từ chối có
  lý do, tự sửa và giải thích lựa chọn; ghi H0/H1/H2 thực tế từng bước.
- Backend và model thật trên bản đã sửa: làm rõ/tạo/review, liên kết nguồn,
  lưu/mở lại thực tế và vòng sửa thứ hai. Không dùng tốc độ replay thay ngân
  sách chờ hoặc gắn output cũ lên draft mới để hoàn tất giả một vòng.
- Người đọc có kinh nghiệm và pilot #7; các yêu cầu riêng #22/#26, thiết bị/
  trình đọc màn hình/Safari thật, demo 9/9 và quyết định PO vẫn còn thiếu.
- N1/N2 vẫn còn ở output gốc. Một quyết định sửa đúng được cấp sẵn và thao
  tác thành công không chứng minh critic hoặc một người dùng mới đã đạt.

Việc tiếp theo là chốt điều kiện/phạm vi phiên người dùng được phép thực
hiện theo phiếu và cách xử lý các lỗi còn mở; chưa tự tuyển người, gọi model
hoặc bắt đầu nghiệm thu chính thức. Không mở thêm vòng tối ưu chỉ từ diễn tập.

## Dấu vết và bảo toàn

Artifact local:
`/var/folders/5q/2y5tf10x3pg8jm8d6_mkf80h0000gn/T/firstframe-hitl-rehearsal-20261026-grle1m7w/`.
Giữ manifest, `sessions.json`, script, `results.json`, ảnh mỗi ca,
`reopen-dom-checks.json`, log và kiểm tra hash. Bốn kịch bản diễn tập cuối
hoàn tất thao tác đã nêu; đó không phải 4/4 người dùng đạt hoặc nghiệm thu.

Lượt script đầu dừng ở review do guard chưa nhận hậu tố `/stream`; API giả
cũ từ chối request, không tới model/backend. Đã sửa script tạm, giữ
`attempt-1-results.json`/`attempt-1.log`, rồi diễn tập lại đủ bốn ca. Không
sửa ứng dụng để vượt lỗi hoặc coi lượt dừng là kết quả provider/model thật.

Đối chiếu hash các file workspace có trước diễn tập, gồm source, cấu hình/
dữ liệu thật, plan/prototype và các tài liệu local cũ: khớp. Trong lượt diễn
tập chỉ thêm báo cáo này, không sửa code, cập nhật issue, commit hoặc tạo PR. Artifact tạm
cần được giữ riêng nếu muốn lưu trữ lâu dài.
