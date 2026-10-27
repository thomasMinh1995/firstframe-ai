# Cập nhật UI M3 theo prototype đã chốt

- Ngày: 27/10/2026. Trạng thái: **đã chốt hướng prototype; kế hoạch triển khai, chưa sửa code**.
- Mục tiêu: người mới chọn một cảnh, viết/sửa ngay trong một vùng soạn và đối chiếu với kịch bản đã lưu bên cạnh.
- Kế thừa [plan M3](m3-screenplay-writing.md); bốn gói chức năng đã merge qua PR #53–#56. Đây là đợt cập nhật UI, không triển khai lại bốn gói và không xác nhận chất lượng critic hoặc nghiệm thu người dùng đã đạt.
- PR tài liệu chỉ gồm plan này. Không thay tiêu chí #7/#22/#26, roadmap, model/prompt, prototype, hợp đồng lưu hiện có hoặc triển khai M4; chưa triển khai code.

## 1. Bản UI làm chuẩn

Prototype được tác giả chốt sau yêu cầu: **danh sách cảnh trên một đường thẳng có mũi tên → click cảnh mở form → kịch bản đã lưu bên cạnh**.

- Bản tham chiếu local: `firstframe-m3-entry.html` trong thư mục visualization của cuộc trao đổi ngày 21/10/2026, task `01a15f16-4982-7291-b4c7-12ba6f27c6d3`.
- SHA-256 tại lúc lập plan: `ada78013199e3b794fa9e5f7cae03e0711a523b0f316956d96beff3fa5d08c7f`.
- Prototype là mô phỏng tương tác. Không đưa nội dung mẫu, canvas minh họa, góp ý mẫu hoặc cách lưu trong prototype vào dữ liệu tác giả/runtime.

| Khu vực | Hành vi cần triển khai |
| --- | --- |
| Lần đầu chưa có M3 | Giữ thao tác bắt đầu từ M2 đã lưu, đối chiếu nguồn và bảo vệ bản đang sửa. Chỉ vào màn danh sách sau khi đã tạo hoặc mở đúng bản M3; điều hướng không tự tạo bản mới |
| Danh sách cảnh | Đúng thứ tự từ kịch bản, một đường thẳng có mũi tên; có số, tiêu đề, trạng thái và phác họa nếu có. Không còn bố cục chữ S |
| Chưa chọn cảnh | Có lời mời chọn cảnh, chưa mở form. Kịch bản đã lưu vẫn đọc được bên cạnh |
| Chọn cảnh | Mở form viết/sửa của đúng scene ID. Chuyển sang cảnh khác giữ toàn bộ sửa trong buffer; không lưu hay gọi AI |
| Vùng viết | Một trang viết liền mạch có tiêu đề và các đoạn hành động/nhân vật/lời thoại; không bắt bấm thêm một fieldset cho từng khối |
| Kịch bản đã lưu | Cột đọc riêng lấy từ `savedProject`, hiển thị toàn bộ cảnh theo thứ tự và đánh dấu cảnh đang chọn. Sửa đang gõ chỉ xuất hiện ở đây sau lưu thành công; mở dự án/đọc lại/khôi phục dùng bản server đã xác nhận. Không dùng buffer hoặc proposal làm bản đã lưu |
| Dàn cảnh, phác họa, góp ý | Mở khi cần trong khu vực hỗ trợ của form; giữ vùng viết và bản đã lưu để đối chiếu. Các tác vụ AI vẫn là lựa chọn riêng |
| Đọc toàn bộ | Giữ đường đọc bản đã lưu/lịch sử và chọn nguồn M4 hiện có. Quay lại vùng viết; không thêm màn danh sách/tiêu đề trung gian đã bị tác giả yêu cầu hoàn tác |

Desktop dùng hai cột: **form viết bên trái / kịch bản đã lưu bên phải**. Nếu nhiều cảnh, chỉ dải chọn cảnh cuộn ngang, giữ một hàng và truy cập được bằng bàn phím; không làm cả trang tràn ngang. Trên mobile, danh sách có thể thành đường thẳng dọc với mũi tên xuống; hai vùng viết/đọc xếp dọc, không ép hai cột nhỏ. Thứ tự không đổi theo breakpoint.

Không bắt có ảnh, thoại, phản hồi hoặc điểm AI để viết/lưu. Hướng dẫn dài thu gọn ở nút thông tin có tên truy cập rõ; trạng thái chưa lưu, lỗi và phạm vi thay thế phải luôn thấy.

## 2. Editor liền mạch nhưng giữ hợp đồng dữ liệu

Hợp đồng hiện có là `ScriptBlock {id, kind: action | dialogue, text, speaker}`. **Không thêm loại `character` vào API** chỉ vì giao diện có dòng tên nhân vật.

1. Mở vùng viết với chỗ nhập hành động sẵn sàng; placeholder không trở thành nội dung đã lưu. Không biến dàn cảnh hoặc hình phác thành văn kịch bản tự động.
2. Enter ở hành động tạo đoạn hành động tiếp. Chọn loại dòng **Nhân vật**, gõ tên rồi Enter chuyển tới lời thoại; tên và nội dung ánh xạ vào `speaker`/`text` của cùng khối dialogue. Enter sau lời thoại trở lại hành động. Shift+Enter xuống dòng trong cùng đoạn. Không xử lý phím Enter khi IME đang ghép chữ.
3. Giữ menu loại dòng cho chuột, bàn phím và cảm ứng; Tab/Shift+Tab vẫn điều hướng focus. Không tự đoán tên nhân vật, tự thêm thoại hoặc sửa câu chữ. Đổi loại đoạn đã có nội dung không được âm thầm làm mất text/người nói; cần cách giữ dữ liệu hoặc xác nhận rõ, kèm hoàn tác an toàn.
4. Sửa một khối giữ ID khối đó. Tách khối giữ ID của phần còn lại theo quy tắc cố định và chỉ cấp ID mới cho phần mới; gộp/xóa không dùng lại ID đã loại cho nội dung khác. Không cấp lại ID cả cảnh mỗi lần render/parse/save.
5. Đổi UI không đổi nguyên văn, Unicode, khoảng trắng hoặc xuống dòng có ý nghĩa. Không ghép toàn bộ cảnh thành text rồi đoán lại khối khi lưu. Dán nhiều đoạn giữ text và ranh giới rõ; nội dung HTML được xử lý như text, không thực thi.
6. Trạng thái viết dở, kể cả có người nói nhưng chưa có thoại, phải giữ trong buffer và lưu nháp theo hợp đồng đang có. Không tự bỏ đoạn rỗng đã có trong dữ liệu; phân biệt vùng placeholder tạm của UI với khối tác giả đã tạo. Giữ điều kiện chưa đủ để chọn nguồn M4.
7. Xóa, đổi thứ tự và hoàn tác khối vẫn truy cập được qua menu gọn; không mất khả năng đã có chỉ để giảm số nút thường trực. Hoàn tác không ghi đè sửa tiếp theo hoặc bản từ cửa sổ khác.

Chọn cách làm nhỏ nhất tương thích với React và các component hiện có. Không mặc định bê `contenteditable`/DOM parser trong prototype vào production, thêm thư viện editor hoặc xây trình chế bản screenplay. Trước tiên chứng minh ánh xạ và round-trip; nếu chưa giữ được dữ liệu thì chưa thay editor hiện hành.

Phạm vi kết nối cần rà: `ScreenplayEditor` quản lý chọn cảnh/buffer và anchor bằng chứng; `ScriptSceneFields` hiện dùng cho cả bản tác giả lẫn form chỉnh phương án trong `ScreenplayProposals`. Nếu tái sử dụng editor mới cho cả hai, trạng thái/ID của phương án vẫn tách riêng, chỉnh phương án không đổi bản tác giả trước khi chọn dùng. Cột đọc tái sử dụng phần render bản đã lưu của `ScreenplayReading`; `page.tsx` tiếp tục giữ nguồn `project`/`savedProject` và các callback lưu/khôi phục/chọn M4. Không tạo một đường ghi dữ liệu mới để đổi bố cục.

## 3. Phác họa và nguồn để đối chiếu

- Dùng liên kết `source_scene_id` với `screenplay.source_outline`, không ghép bằng số thứ tự/tên cảnh và không lấy M2 mới nhất thay nguồn M3 cũ.
- Tái sử dụng ảnh M2 đã chọn giữ cùng metadata nguồn và đường đọc ảnh hiện có. Chỉ coi ảnh khớp nguồn khi nội dung đã dùng tạo ảnh khớp snapshot M2 của cảnh đang viết; revision dự án hoặc tên giống nhau không đủ chứng minh.
- M3 hiện chưa chụp lựa chọn ảnh trong `Screenplay.source_outline`. Vì vậy không tuyên bố một ảnh là lựa chọn bất biến đi cùng bản M3/lịch sử. Hiển thị nguồn ảnh riêng; ảnh cũ/khác nguồn chỉ nằm trong phần đối chiếu có nhãn rõ, không tự thành thumbnail khớp nguồn. Không thêm migration/snapshot ảnh mới trong đợt UI này.
- Không có ảnh phù hợp, asset bị thiếu hoặc tải lỗi thì hiện trạng thái trung tính và vẫn viết/lưu được. Không dùng hình vẽ mẫu trong prototype làm ảnh của tác giả; không gọi tạo ảnh, OCR hoặc suy luận nội dung từ ảnh khi vào/chuyển cảnh.
- Góp ý vẫn mở đúng snapshot đã review. Giữ thông điệp AI có thể sai/bỏ sót; kiểm tra quote đúng không chứng minh nhận xét đúng. Nguồn cũ vẫn đọc được, không thành liên kết sửa bản hiện tại khi không còn khớp.

## 4. Thứ tự triển khai nhỏ

| Bước | Phạm vi | Điều kiện hoàn tất |
| --- | --- | --- |
| **1 — Kiểm chứng editor trước** | Làm lát cắt một cảnh trên fixture/provider giả: viết liền mạch → lưu → mở lại; ánh xạ dòng nhân vật vào dialogue, giữ ID và điều hướng bằng chứng. Chưa thay UI đại trà | Text/ID/order/nguồn round-trip đúng; tiếng Việt/IME, paste, tách/gộp/xóa/hoàn tác và bản viết dở không mất dữ liệu. Nếu chưa đạt, dừng tại lỗi cụ thể thay vì mở thêm tính năng |
| **2 — Danh sách thẳng và bản lưu song song** | Đổi bố cục, trạng thái chưa chọn cảnh, click mở form và vùng đọc từ `savedProject`; tích hợp editor đã qua bước 1 | Chuyển nhiều cảnh giữ buffer; cột bản lưu không thay trong lúc gõ/lưu lỗi. Chỉ khi server xác nhận lưu thành công mới cập nhật đúng snapshot. Không phát sinh save/AI do điều hướng |
| **3 — Nguồn, ảnh và các thao tác sẵn có** | Đưa dàn cảnh/phác họa/góp ý vào phần hỗ trợ thu gọn; nối lại viết thử, dùng/bỏ/hoàn tác, đọc lịch sử, khôi phục, chọn M4 và hướng dẫn tại chỗ | Ảnh/feedback không gắn nhầm nguồn; các chức năng M3 hiện có vẫn dùng được. Không đổi prompt/model hoặc tiêu chí đủ bản M4; giữ storage/tiến độ/bỏ qua/phát lại tour |
| **4 — Hồi quy và bàn giao** | Kiểm tra tích hợp, desktop/mobile, bàn phím và dữ liệu cũ. Ghi kết quả, giới hạn và lỗi còn mở | Có báo cáo kỹ thuật theo ma trận bên dưới, không còn lỗi chặn do UI mới. Chất lượng critic và nghiệm thu người dùng tiếp tục ghi riêng |

**Làm bước 1 trước** vì editor ảnh hưởng trực tiếp nguyên văn và ID mà critic/lịch sử sử dụng. Không cần chạy model thật để biết UI có làm mất dữ liệu hay không. Mỗi bước có kiểm tra tập trung; chỉ commit/PR khi được yêu cầu riêng.

## 5. Bảo vệ dữ liệu không được thay

- Giữ snapshot M2/ý đồ và ID project/script/scene/block. M1/M2/ảnh/lịch sử không bị sửa bởi thao tác M3; client/dự án cũ vẫn mở/lưu an toàn.
- Tái sử dụng luồng buffer cấp dự án, revision/CAS, xử lý 409, lưu lỗi, tải bản sao và cảnh báo rời trang. Không tạo buffer độc lập cho cột bản lưu; response muộn hoặc đổi dự án không được đổ dữ liệu cũ vào editor đang sửa. Sau khi đổi dự án/bản kịch bản thành công, đặt lại lựa chọn cảnh và trạng thái editor theo đúng project/script ID; không giữ form/nguồn/ảnh của dự án trước.
- Không tự lưu khi click cảnh, bật phần hỗ trợ, đọc toàn bộ, đổi bản đọc hoặc chọn nguồn M4. Trước tác vụ đã yêu cầu lưu theo luồng hiện có phải giữ đủ mọi sửa của dự án; lưu thất bại thì không tiếp tục tác vụ đó.
- Giữ checkpoint/request ID và đường kiểm tra kết quả khi mất response; không tự retry/start lại/nhận proposal. Dùng phương án chỉ đổi đúng cảnh trong buffer, có xác nhận phạm vi và hoàn tác khi còn khớp.
- Phản hồi/ảnh cũ không được cấp nguồn mới. Điều hướng quote phải tới đúng field của đúng snapshot; đổi bố cục editor cần cập nhật anchor/focus, không bỏ kiểm tra này hoặc dùng fuzzy match.
- Bản đọc/lịch sử/nguồn M4 luôn tách khỏi buffer. Chọn M4 chỉ chụp đúng phiên bản đã đọc bằng hợp đồng server hiện có; bản chọn không tự đổi sau sửa/khôi phục. Bản chưa đủ vẫn lưu nháp, không âm thầm bỏ cảnh hoặc khối thiếu.
- Giữ giới hạn payload, số cảnh/khối/độ dài hiện có; không vượt giới hạn do editor mới. Không thực thi HTML từ nhập/dán/model hoặc đưa tác phẩm riêng vào log/test công khai.

## 6. Kiểm chứng và tiêu chí bàn giao

| Nhóm | Ca tối thiểu |
| --- | --- |
| Round-trip | Dự án M3 cũ; cảnh chỉ hành động; hội thoại nhiều người; khối rỗng; tiếng Việt, ký tự tổ hợp, nhiều khoảng trắng/xuống dòng; sửa/lưu/mở lại giữ nguyên text, speaker, ID và thứ tự |
| Editor | Enter/Shift+Enter, IME không bị chia chữ, đổi loại dòng, paste text/HTML, chọn và xóa nhiều đoạn, tách/gộp/xóa/đổi thứ tự/hoàn tác; không tự biến đoạn mô tả thành người nói |
| Hai vùng dữ liệu | Gõ ở cảnh A rồi chuyển B và quay lại; bản bên phải còn nguyên cho tới lưu thành công. Lỗi mạng/409/response muộn giữ buffer và bản lưu đúng; đổi dự án không rò nội dung |
| Nguồn và ảnh | Hai cảnh trùng tên, đổi thứ tự, M2 thay nội dung, chọn ảnh mới/ảnh khác snapshot, ảnh thiếu; nguồn và thumbnail không ghép nhầm, không phát sinh tạo ảnh |
| AI và bằng chứng | Provider giả: chỉnh phương án riêng không đổi bản tác giả, viết thử chưa dùng không vào bản lưu; dùng/bỏ/hoàn tác đúng cảnh; quote tới đúng heading/text/speaker trong editor mới, kể cả khi chưa chọn cảnh hoặc phần hỗ trợ đang đóng; feedback cũ chỉ mở nguồn cũ; lỗi AI vẫn tự viết/lưu được |
| Lịch sử và M4 | Đọc current/history khi có sửa chưa lưu; khôi phục theo luồng hiện có; chọn đúng bản đã đọc, mất response không chọn trùng; bản chọn giữ nguyên sau sửa tiếp; thiếu nội dung vẫn không đủ chọn |
| Truy cập và bố cục | Desktop hai cột; 390/320px xếp dọc không tràn trang; nhiều cảnh vẫn tới được mọi item. Nhãn, Tab/Shift+Tab, menu, trạng thái động, focus sau chuyển cảnh/đến bằng chứng; IME và paste kiểm tra trực tiếp |
| Hồi quy | Build/typecheck, frontend contract và browser M3 bị ảnh hưởng; hồi quy bàn giao M2/tour. Backend test M3/review/selection tương ứng nếu đường gọi bị ảnh hưởng; không sửa backend/prompt chỉ để thay bố cục |

Dùng fixture tổng hợp, DB/profile QA riêng và provider giả; đếm request để xác nhận click/đọc/lưu không gọi model. Không chạy thêm model văn bản/ảnh hoặc API trả phí trong đợt cập nhật UI. Nếu cần lượt thật sau này, phải có mục tiêu/ngân sách và cho phép riêng.

Điều kiện bàn giao: toàn bộ luồng thủ công và chức năng M3 hiện có hoạt động trên UI mới, không còn lỗi mất nội dung/ID, ghi đè buffer, sai nguồn hoặc nhận nhầm bản. Báo cáo ghi rõ trình duyệt/thiết bị đã thử và phần chưa thử. Kiểm tra kỹ thuật không chứng minh người mới thấy dễ dùng hơn; điểm này cần phiên người dùng sau M4/deploy theo thứ tự đã chốt. Không hạ tiêu chí nghiệm thu cũ và không đóng các lỗi critic đang mở.

Tài liệu đối chiếu: [viết thủ công M3](../testing/m3-manual-writing.md), [góp ý có bằng chứng](../testing/m3-evidence-feedback.md), [đọc và chọn nguồn M4](../testing/m3-reading-handoff.md), [review kỹ thuật Gói 3](../testing/m3-g3-final-review.md).
