# Task 2 — Đợt đầu: baseline và thử sửa prompt

Ngày 04/11/2026. Issue #96; nhánh `fix/screenplay-quality-and-feedback`,
baseline `b929ea2` sau khi merge plan qua PR #97.

## Kết luận bàn giao

Đã thực hiện phần đo baseline, ba vòng sửa thủ công–lưu–góp ý và thử hai
prompt ứng viên theo plan. **Chưa có bản sửa chất lượng đạt điều kiện để đưa
vào runtime.** Cả prompt planner và prompt góp ý thử nghiệm đều bị loại;
source runtime cuối đợt bằng baseline. Không đổi model, schema, API hay UI.

Task 2 còn mở. Đây là bàn giao bằng chứng và ca tái hiện để tiếp tục sửa,
không phải nghiệm thu sáng tác hoặc đề nghị merge một prompt chưa đạt.

## Phạm vi và cách chạy

- [Bộ ca và ngân sách](../evaluations/task2-story-quality-2026-11-04/cases.json)
  được chốt trước khi gọi model: hai ca phát triển và một ca giữ lại; tối đa
  32 lượt gọi, 1.200 giây model, không retry model thất bại.
- Qwen `qwen2.5:7b`, temperature 0,3, context yêu cầu/thực 16384, timeout
  provider 180 giây, không seed. [Digest và cấu hình](../evaluations/task2-story-quality-2026-11-04/model-info.json).
- API thực qua FastAPI TestClient, SQLite/dataset tạm; không mở database tác
  giả. Phân tích → plan gồm một call planner và một call góp ý card sẵn có.
  Các câu hỏi chưa trả lời được để mở; không tạo đáp án tác giả giả.
- Người đọc ở đợt này là agent. Với mỗi plan, ghi lựa chọn sửa thủ công cùng
  lý do, lưu rồi gọi review. Assert bản draft trước/sau review bằng nhau.
- So sánh ứng viên dùng nguyên `input_text` và JSON schema của request đã
  lưu; chỉ thay instructions. Planner: ba lượt/ca, gồm ca giữ lại. Góp ý:
  ba lượt cho từng snapshot sửa của hai ca phát triển. Không chạy writer,
  critic v8, PDF hoặc xây runner sản xuất mới.

CLI thử nghiệm một lần được giữ ở [run.py](../evaluations/task2-story-quality-2026-11-04/run.py).
Đây là bản lưu cách đo, không phải công cụ mới trong ứng dụng. Nó lưu raw
request/response/schema, profile và ledger, từ chối thư mục output đã tồn
tại. Không chạy lại trên đợt evidence đã đóng băng; đợt mới cần thư mục và
ngân sách riêng. Instructions của các ứng viên đã loại vẫn nằm trong request
của chúng; `replay` mặc định dùng prompt hiện tại nên không tự tái tạo ứng
viên đã loại sau khi trả runtime về baseline.

## Những lỗi có bằng chứng

| Ca | Baseline và thao tác tác giả | Kết quả đọc |
| --- | --- | --- |
| Áo mưa để quên | Brief kể người quan sát nhớ cử chỉ người thợ; plan đổi thành người thợ nhớ chính khoảnh khắc đó. Phần giữa chỉ “tiếp tục làm việc”. Người đọc sửa kết bằng thao tác kéo cửa/vuốt vạt áo, cắt khi tay rời áo | Lẫn góc nhìn người kể với nội tâm nhân vật; diễn tiến chưa được phát triển. Review bản sửa đòi thêm “liên kết” nhưng không chứng minh lựa chọn tác giả nào bị vi phạm |
| Hộp bánh trống | Brief phát hiện hộp trống sau khi mở tủ; plan đã cho nhìn tủ trống từ setup. Người đọc sửa mở đầu thành ngồi → đứng lên cầm cốc, tủ còn đóng | Tiết lộ cú phát hiện sớm. Review cho rằng ngồi rồi đứng là mâu thuẫn và muốn giữ trạng thái ngồi |
| Nhặt hoa rụng — giữ lại | Baseline giữ động tác nhặt/xếp/đặt cốc, chưa thêm nhân vật hay thoại; nhãn conflict gán cho tiếng xe rác chưa chứng minh cần thiết. Người đọc viết rõ âm thanh đi cùng động tác đặt cốc và điểm cắt | Plan nền có thể dùng để đọc tiếp. Review ban đầu lại đòi từng card lặp tiếng xe rác dù tiếng đó đã hiện ở phần khác; không coi một card thiếu nhắc lại âm thanh là mâu thuẫn đã được chứng minh |

Các thao tác sửa nằm trong `raincoat-edit.json`, `empty-fridge-edit.json`,
`held-out-edit.json`; mỗi file giữ nguyên lý do chọn sửa. Đây là ba phương
án của người đọc, không phải đáp án bắt buộc hoặc minh chứng pilot người mới.

## Hai ứng viên bị loại

**Planner:** thêm hướng dẫn tách người quan sát khỏi nhân vật, giữ thứ tự
phát hiện và diễn tiến nhìn/nghe được; bỏ yêu cầu cứng một nhân vật/một biến
đổi cảm xúc. Vẫn giữ schema hiện có. Ba lượt/ca không chứng minh sửa ổn định:

- Áo mưa: một lượt đưa người quan sát thành nhân vật thứ hai, trái giới hạn
  chỉ thấy người thợ; các lượt khác vẫn dùng ký ức hoặc lặp cử chỉ thay cho
  diễn tiến. Không đạt ba lượt xác nhận.
- Hộp bánh: một lượt ngụ ý nhân vật đã ăn bánh, một lượt thêm rời gian bếp;
  lượt còn lại giữ điểm dừng tốt hơn nhưng có câu cuối cần biên tập. Không
  thể lấy lượt này để che hai lượt còn lại.
- Ca giữ lại: hai lượt thêm người bán hoa rời quầy sau khi đặt cốc, trái
  điểm cắt; một lượt gần baseline hơn nhưng thêm ánh nhìn chưa rõ thời điểm.
  Không sửa prompt tiếp theo chính ca này rồi gọi nó là ca độc lập.

**Góp ý card:** thêm hướng dẫn phân biệt trạng thái nối tiếp với đồng thời,
đọc hành động chuyển tiếp và kiểm quyết định được viện dẫn. Cả sáu lượt vẫn
có nhận xét thiếu căn cứ. Có một lượt trả `aligned` nhưng đồng thời yêu cầu
hai người “vẫn ngồi ... khi một người đứng dậy”; các lượt khác trả mismatch
cho chính sự tiếp nối đó. Không dùng cờ `passed` hoặc nhãn aligned làm điểm
chất lượng. Prompt này cũng bị loại, không mở thêm vòng dò prompt.

Mọi before/after và lỗi vẫn được giữ trong
[thư mục evidence](../evaluations/task2-story-quality-2026-11-04/).
Profile của ứng viên chứa diff thử nghiệm; request chứa instructions thực
đã gửi. Không sửa output để biến lượt trượt thành đạt.

## Kiểm chứng và giới hạn

- **110 test backend liên quan đạt**, gồm workflow, prompt loader, reference
  isolation, revision review, plan recovery và feedback language. Test giả
  kiểm tra hợp đồng/nguồn; không phủ định lỗi chất lượng trong bảng trên.
- Đã xác nhận runtime trở lại baseline sau khi loại ứng viên. Không cần
  chạy lại frontend/browser/PDF vì không có thay đổi runtime giao tiếp.
- Một lần setup runner lỗi đường dẫn trước model; một lần sandbox chặn kết
  nối Ollama trước khi có response. Giữ cả hai dấu vết. Lần xin quyền kết
  nối local là xử lý môi trường, không chạy lại một output model xấu.
- Tổng attempt, thời gian và lỗi nằm trong
  [calls.json](../evaluations/task2-story-quality-2026-11-04/calls.json).
  Đợt này có 28 attempt, 27 response model thành công và 1 lỗi kết nối;
  tổng thời gian provider 1.102,716 giây, trong ngân sách 32/1.200.
  Đã đối chiếu 15 cặp request giữ cùng input/schema và ba vòng review không
  thay draft. [Tổng hợp](../evaluations/task2-story-quality-2026-11-04/summary.json).
  Không tự dùng phần ngân sách còn lại để tìm một output đẹp hơn.
- Chưa có PO/người đọc độc lập duyệt; chưa có pilot, model khác hoặc bằng
  chứng lợi thế thị trường. Issue #96 và các điều kiện #7/#22/#26 giữ mở.

## Việc tiếp theo trong #96

Ưu tiên lỗi critic coi các thời điểm khác nhau là mâu thuẫn: đối chiếu đầu
vào card/neighbor và cách chọn quyết định trước khi thử thêm lời nhắc. Chỉ
điều chỉnh adapter hoặc prompt khi có giả thuyết và ca đối chứng rõ; không
thêm rule theo đạo cụ/câu chữ của fixture, không bỏ guard và không tự chuyển
model. Planner vẫn cần giải quyết góc nhìn/người kể và điểm dừng. Đợt tiếp
theo cần ngân sách riêng, giữ evidence của đợt này làm kết quả không đạt.
