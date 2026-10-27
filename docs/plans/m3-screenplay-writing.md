# Kế hoạch M3 viết và sửa kịch bản

- Ngày lập: 27/10/2026. Trạng thái: đề xuất triển khai, chưa code.
- Mục tiêu: từ bản dàn cảnh tác giả đã lưu, viết được kịch bản có hành động/lời thoại, tự sửa, lưu/mở lại và hoàn thành ít nhất một vòng đọc sửa trên đúng bản nguồn.
- Nền M2 đã merge, gần nhất là Gói 4 qua PR #51; hợp đồng bàn giao và đường ảnh có kiểm chứng kỹ thuật. Chất lượng ảnh và nghiệm thu M2 đầy đủ vẫn còn giới hạn; ảnh không bắt buộc để bắt đầu M3.
- Giữ thứ tự M3 → M4 xuất bản đã chọn → kiểm thử toàn luồng → deploy thử → trải nghiệm người dùng. Không đóng hoặc thay tiêu chí #7/#22/#26.
- Đợt này chỉ thêm plan này; không sửa roadmap, plan cũ, prototype, runtime, model hoặc cấu hình; không triển khai code.

## 1. Phạm vi và trải nghiệm

M3 biến diễn tiến và lựa chọn dàn cảnh thành văn bản để đọc, diễn và sửa. Tác giả có thể viết toàn bộ bằng tay; AI chỉ hoạt động khi được yêu cầu, luôn trình bày kết quả riêng trước khi nhận.

1. Tại M2, tác giả lưu và đối chiếu dàn cảnh, rồi chọn **Bắt đầu viết từ bản này**. Hiển thị nguồn, thứ tự cảnh và các giới hạn sẽ đi cùng. Cảnh thiếu tên/diễn tiến được quay lại hoàn thiện; không âm thầm bỏ cảnh để tạo bản bàn giao.
2. M3 có danh sách cảnh theo thứ tự và vùng soạn một cảnh. Trên desktop có thể mở nguồn M2 bên cạnh; màn hẹp dùng vùng nguồn thu gọn, không ép hai cột. Luôn phân biệt nội dung nguồn và bản tác giả đang viết.
3. Bắt đầu bằng khung cảnh trống gắn nguồn, chưa biến toàn bộ ghi chú thành văn kịch bản. Phần soạn gồm tiêu đề cảnh tự sửa và các khối **Hành động / Lời thoại**. Khối lời thoại có tên người nói và nội dung; âm thanh có thể viết trong hành động. Cho thêm, xóa, đổi thứ tự khối; cảnh không có lời thoại vẫn hợp lệ.
4. Hướng dẫn ngắn khuyến khích hành vi, hình ảnh, âm thanh có thể thể hiện. Không bắt viết thoại, lời giải thích cảm xúc, cao trào, hòa giải hoặc kết đóng. Lời thoại cần hợp xưng hô/ngữ cảnh; “show, don't tell” là định hướng góp ý, không phải luật cấm thoại.
5. **Nhờ FirstFrame viết thử cảnh này** tạo một phương án riêng. Tác giả đọc song song với bản hiện tại, tự chỉnh phương án rồi chọn **Dùng cho cảnh này** hoặc **Bỏ qua**. Nêu rõ phạm vi thay thế; dùng chỉ đưa vào buffer, chưa phải lưu. Không sinh lại cả kịch bản đang viết.
6. **Nhận góp ý cảnh này** đưa nhận xét có nguồn, tác động và gợi ý để cân nhắc. Tác giả tự sửa văn bản; không có tác vụ tự áp dụng hoặc vòng AI tự sửa. Có thể ghi nhận hữu ích, dẫn sai hoặc chưa đủ căn cứ mà không sửa kịch bản.
7. **Lưu thay đổi** giữ bản hiện tại và phiên bản trước. Đóng ô, chuyển cảnh hoặc đọc nguồn không gọi AI hay giả là đã lưu. Bản đã lưu có thể được chọn và đọc toàn kịch bản để chuẩn bị sang M4; chưa thực hiện xuất bản/PDF trong M3.

MVP giữ danh sách cảnh nguồn M2 và cho viết chi tiết từng cảnh trong M3. Nếu muốn thay cấu trúc cảnh, tác giả quay M2 rồi chủ động bắt đầu bản M3 khác; bản M3 cũ vẫn giữ. Không xây đồng bộ/ghép cấu trúc hai chiều trong đợt này. Khác biệt nội dung do tác giả tự viết được giữ, không bị ép khớp lại nguồn.

Chưa làm editor kiểu phần mềm chế bản, kéo thả, cộng tác thời gian thực, screenplay dài, chấm điểm tổng, judge mới, embedding, phân tích ảnh/OCR hoặc storyboard. Không thêm cổng đạo đức tự động vào quyền lưu/sửa; chính sách xuất bản được xử lý riêng ở M4 trước khi triển khai xuất bản.

## 2. Nguồn và mô hình dữ liệu tối thiểu

`ProjectResponse.scene_handoff` hiện là trường tính từ dàn cảnh đã lưu, gồm outline/version/source ID, thứ tự và nội dung cảnh. `project_revision` có thể tăng khi lưu metadata ảnh hoặc thao tác khác; không dùng riêng số này để kết luận nội dung M2 đã đổi.

Khi bắt đầu M3, backend đọc bản đã lưu, kiểm tra revision rồi chụp snapshot riêng, gồm bản bàn giao, nguồn story plan/ý đồ/ngôn ngữ trong `scene_outline.source` và nội dung dàn cảnh đã chọn. Không lấy buffer client, ý đồ M1 mới hơn hoặc chỉ giữ một đường dẫn tới M2 hiện tại. Bắt đầu ban đầu dùng bản M2 hiện lưu đã đối chiếu; chưa thêm bộ chọn mọi phiên bản M2 cũ.

| Đối tượng | Dữ liệu cần giữ |
| --- | --- |
| Bản kịch bản | ID, phiên bản, snapshot nguồn M2 cùng ý đồ, các cảnh kịch bản có thứ tự |
| Cảnh kịch bản | ID ổn định riêng, liên kết scene ID nguồn, tiêu đề cảnh, các khối hành động/lời thoại có ID ổn định |
| Phiên bản đã lưu | ID, thời điểm, nội dung và nguồn đủ để mở/khôi phục đúng bản; không suy từ log AI |
| Lượt viết thử | ID yêu cầu, snapshot nguồn và cảnh kịch bản, prompt/schema/model/tham số, trạng thái, output riêng hoặc lỗi; phương án tác giả chỉnh tách output gốc |
| Lượt góp ý | ID yêu cầu, snapshot kịch bản/ý đồ, ID nguồn và trích dẫn, nhận xét/phương án, kết quả kiểm tra dẫn chứng, lựa chọn tác giả nếu có |
| Bản chọn cho M4 | ID/phiên bản kịch bản đã lưu và nội dung/nguồn bất biến; không trỏ động vào buffer hoặc “bản mới nhất” |

Chốt schema cụ thể và giới hạn số cảnh/khối/độ dài/payload ở Gói 1 dựa trên phạm vi phim ngắn và giới hạn M2 hiện có. Tránh một ô văn bản khổng lồ không có định danh để dẫn chứng. ID do ứng dụng cấp; model không tự cấp nguồn hoặc quyền sửa. Không dùng `draft.sections` của story plan để chứa screenplay.

Tái sử dụng SQLite/revision, version, checkpoint/proposal, `StructuredProvider`, progress và validation đang có. Tách logic kịch bản khỏi route/UI lớn vừa đủ, không xây workflow engine hay abstraction đa model mới.

## 3. Bảo vệ dữ liệu và quyền tác giả

- Thêm trường M3 mặc định rỗng; dự án cũ mở/lưu được. Client cũ bỏ trường M3 không được xóa M3; thao tác M3 không xóa M1/M2, ảnh hoặc lịch sử. Khóa nội dung/góp ý M1 không thay chỉ vì có M3; M3 có kiểm tra nguồn nội dung riêng.
- Backend xác minh project, revision, scene/block ID và snapshot. Nguồn do model/client tự khai không trở thành nguồn đã xác thực. Trùng tên hoặc đổi vị trí không đổi liên kết cảnh; không tìm đích sửa bằng tên hay fuzzy match.
- Sửa M2/M1 sau khi bắt đầu M3 giữ nguyên kịch bản và nguồn cũ, báo khác biệt nội dung. Không tự ghép ý đồ hiện tại vào bản cũ. Bắt đầu bản M3 khác là thao tác riêng, lưu/checkpoint bản đang viết trước và giữ lịch sử để quay lại.
- Mọi mutation dùng revision/CAS. Mất mạng, 409, chuyển dự án, response muộn không được thay buffer bằng dữ liệu cũ. Có cảnh báo rời trang khi chưa lưu; lỗi lưu vẫn tải được bản sao nội dung theo cơ chế hiện có.
- Trước tác vụ AI phải lưu được mọi sửa đang chờ, thông báo rõ rồi cố định nguồn. Lưu thất bại không gọi AI. Kết quả về muộn lưu riêng theo snapshot, không ghi đè bản viết hoặc gắn nhãn thành góp ý hiện tại.
- Lưu ID/checkpoint trước gọi model. Gửi lại cùng yêu cầu không phát sinh lượt mới; ID cũ dùng khác nội dung bị từ chối. Khi mất phản hồi, kiểm tra kết quả đã lưu trước khi tác giả chủ động chạy mới; không tự retry.
- Bản viết thử không tự nhận. Dùng phương án chỉ thay cảnh đã thông báo trong buffer, giữ cảnh khác và nội dung mới hơn. Bất kỳ nội dung đã dùng để sinh phương án (nguồn M2, cảnh đích hoặc cảnh kịch bản liên quan) đã đổi thì giữ phương án để đọc, không cho nhận như còn hiệu lực. So khớp snapshot nội dung đã dùng, không chỉ revision dự án; thay metadata không tự làm phương án hết hiệu lực. Hoàn tác chỉ khi trạng thái đích vẫn khớp sau thao tác; không ghi đè các sửa tiếp theo.
- Góp ý phải chỉ được chi tiết trong snapshot, dẫn đúng scene/block ID và nguyên văn quote. Kiểm tra ID/quote chỉ xác nhận trích đúng; không chứng minh nhận xét đúng/hữu ích. Lý do phải giải thích liên hệ với ý đồ; phương án sáng tạo được ghi là đề xuất, không phải quyết định tác giả.
- Thiếu bằng chứng thì có thể trả “chưa đủ căn cứ” hoặc không có nhận xét. Tham chiếu sai không thành liên kết sửa đã xác thực. Chuyển tới nguồn cũ phải mở đúng snapshot; điều hướng không tự lưu, viết lại hoặc gọi AI.
- Không bắt tác giả nhận góp ý, đạt điểm AI, có ảnh hoặc có phản hồi AI để lưu/chọn phiên bản. Timeout/sai schema/lỗi critic không làm mất bản viết; lưu được output viết thử hợp lệ trước khi chạy góp ý riêng.
- Giữ nguyên tiếng Việt, khoảng trắng/xuống dòng có ý nghĩa trong text tác giả. Không thực thi HTML do model trả. Ảnh chỉ là tham khảo tùy chọn, không làm nguồn xác nhận sự kiện; thiếu ảnh không chặn M3.
- Nội dung riêng không đưa vào repo hoặc bộ thử công khai. Dataset/log chỉ ghi theo chính sách và sự đồng ý hiện có; không tự ghi tác phẩm vào bộ đánh giá. Dùng fixture tổng hợp cho test, không API trả phí khi chưa được phép.

## 4. Bốn gói triển khai

### Gói 1 — Nhận nguồn M2 và viết thủ công

1. Chốt schema/fixture và nguồn snapshot M3. Kiểm tra `scene_handoff` hợp lệ, bắt đầu đúng một bản; thao tác lặp lại không tạo bản trùng ngoài ý muốn.
2. Làm lát cắt chọn nguồn → soạn hành động/lời thoại → lưu → mở lại. Hỗ trợ thêm/xóa/đổi thứ tự khối, cảnh im lặng và cảnh chưa viết xong; không ép lưu nháp phải đủ mọi cảnh.
3. Hiển thị nguồn song song/thu gọn, buffer và trạng thái đã lưu. Thêm lịch sử/khôi phục bằng thao tác rõ, giữ bản hiện tại trước khôi phục; bắt đầu bản khác từ M2 không mất bản cũ.

**Hoàn tất khi:** đi hết đường thủ công không gọi AI; dự án/client cũ không xóa M3; reload giữ text/ID/order/nguồn. Hai cửa sổ, mất mạng, chuyển cảnh/dự án và khôi phục không mất sửa. M2 đổi chỉ báo khác biệt; đổi metadata ảnh không giả là nội dung dàn cảnh đã đổi.

**Làm trước để kiểm chứng:** một cảnh có tiếng Việt và nhiều khối → lưu/mở lại → hai cửa sổ → sửa M2 rồi quay lại M3. Làm trước phần trình bày đẹp hoặc prompt.

### Gói 2 — AI viết thử đúng một cảnh

1. Dùng provider văn bản đang cấu hình, prompt/schema hẹp. Đọc cảnh đích, ý đồ nguồn, vị trí trong dàn cảnh và phần kịch bản đã lưu liên quan để giữ liên tục; đánh dấu rõ phần nào là ngữ cảnh, phần nào được đề xuất thay.
2. Trả đúng một cảnh với hành động/lời thoại; không tự thêm cảnh, thay thứ tự, chốt kết mở hoặc nhận góp ý M2 chưa dùng. Chi tiết mới cần thiết cho cách thể hiện vẫn là sáng tạo đề xuất để tác giả duyệt.
3. Checkpoint trước gọi, tiến trình theo sự kiện thật, kết quả riêng có thể phục hồi. Cho đọc/chỉnh/dùng/bỏ, cảnh báo thay thế nếu cảnh đã có nội dung; không gọi critic tự động để quyết định nhận bản.

**Hoàn tất khi:** provider giả xác nhận đúng nguồn/phạm vi, không tự nhận, lỗi/sai schema/mất phản hồi không mất dữ liệu hay gọi lại. Đợt model nhỏ cho thấy có phương án đọc được và giữ các quyết định rõ; nếu chưa đạt thì ghi lỗi và để đường viết tay hoạt động, không gọi là nghiệm thu chất lượng AI.

### Gói 3 — Góp ý có bằng chứng và một vòng tác giả tự sửa

1. Review một cảnh đã lưu với ý đồ và bối cảnh liên quan, tập trung chi tiết quan sát được, khả năng thể hiện hành động và lời thoại phù hợp ngữ cảnh. Không mở bộ chấm điểm hoặc phán quyết chất lượng toàn tác phẩm.
2. Trả nhận xét ngắn kèm trích dẫn từ kịch bản; nếu nói lệch ý đồ, phải dẫn thêm quyết định/ràng buộc nguồn. Kiểm tra source/ID/quote trước khi hiện liên kết, phân biệt lỗi có căn cứ và lựa chọn sáng tạo.
3. Tác giả đọc, tự sửa rồi lưu và chủ động nhận góp ý mới. Góp ý trước giữ snapshot cũ và báo hết hiệu lực khi bất kỳ nội dung đã dùng để review thay đổi, kể cả cảnh lân cận; không tự cấp nguồn mới sau một lần sửa.

**Hoàn tất khi:** hoàn thành đọc → cân nhắc → tự sửa hoặc giữ nguyên → lưu/mở lại → review đúng bản mới. Test cả bản tuân thủ lẫn bản vi phạm một điều; người đọc đối chiếu nhận xét đúng, hữu ích và có dẫn sai tác giả hay không. “Không có góp ý” hợp lệ khi thiếu căn cứ; quote đúng hoặc bấm dùng không đủ để chấm chất lượng đạt.

### Gói 4 — Đọc toàn bản và chọn phiên bản cho M4

1. Hiển thị toàn kịch bản từ bản đã lưu, theo đúng thứ tự, giữ hành động/lời thoại và các cảnh còn trống. Không thêm lượt AI đọc/chấm toàn bản trong gói này.
2. Chọn phiên bản đã lưu làm nguồn M4 bất biến, đọc đối chiếu được trước bàn giao. Bản chưa đủ nội dung vẫn lưu nháp được; khi còn cảnh chưa viết, báo rõ và cho quay lại, không âm thầm bỏ cảnh rồi gọi là kịch bản hoàn chỉnh.
3. Cập nhật hướng dẫn M3 tại chỗ và điểm chuyển M2 → M3; giữ storage/tiến độ/bỏ qua/phát lại tour cũ. Diễn tập cả đường viết tay và đường AI có quyền chọn.

**Hoàn tất khi:** M2 nguồn đã chọn → viết/sửa → lưu/mở lại → chọn đúng phiên bản M3 để M4 dùng; không nhận buffer hoặc phương án chưa dùng. Chưa có M4 thì chỉ xác nhận hợp đồng bàn giao bằng test, không tuyên bố đã xuất bản thật hoặc hoàn thành toàn hành trình.

Mỗi gói review/test riêng và chỉ commit/PR khi được yêu cầu. Không gộp thành một đợt viết code dài hoặc chờ AI hoàn hảo mới kiểm tra lưu dữ liệu.

## 5. Kiểm chứng và ngân sách model

| Lớp | Bằng chứng tối thiểu |
| --- | --- |
| Dữ liệu/API | Snapshot/ID/order, legacy/client cũ, revision/409, lịch sử/khôi phục, kết quả muộn và idempotency; M1/M2/ảnh không bị thay |
| UI | Sửa nhiều khối/cảnh, tiếng Việt/IME, bàn phím/focus, màn hẹp, chuyển cảnh và dự án, chưa lưu, lỗi mạng, preview khác bản lưu; không gọi AI do điều hướng |
| Viết thử | Ba ca tổng hợp cố định: khoảng lặng/kết mở, chuyện vui/khó xử, giới hạn nhân vật/bối cảnh; kiểm tra phạm vi một cảnh và tính liên tục với cảnh bên cạnh |
| Góp ý | Mỗi ca có bản tuân thủ và bản đổi một ràng buộc; chấm riêng đúng bằng chứng, đúng nhận xét, hữu ích, dẫn sai và bỏ sót |
| Hồi quy | Backend, build/typecheck/contract và browser các luồng bị ảnh hưởng; đường M2/M3 thủ công không cần ảnh/provider |
| Toàn luồng | Ít nhất một vòng đọc sửa trên bản đúng nguồn và chọn phiên bản; tách rõ diễn tập kỹ thuật và nghiệm thu người dùng |

Trước đợt model thật, chốt brief/snapshot, prompt/schema, model identifier/digest, tham số/seed nếu có, expected behavior và số lượt. Đề xuất ban đầu: viết một cảnh ≤120 giây, góp ý một cảnh ≤60 giây; tối đa một lượt cho mỗi input đã đóng băng, không retry chọn lọc. Đây là ngân sách đề xuất cho M3, phải được chủ sản phẩm duyệt trước chạy, không tự kế thừa ngân sách ảnh/text trước.

Lưu mọi input/output, lỗi provider/schema/tham chiếu, thời gian và kết luận người đọc. Không điều chỉnh nhãn hay kỳ vọng sau output để biến trượt thành đạt. Chỉ mở lượt sửa tiếp cho lỗi cụ thể đã xác nhận; không mở benchmark/model router hoặc chuỗi tối ưu prompt không có điểm dừng.

Các ngưỡng demo/pilot #7/#22/#26 hiện có giữ nguyên. Không tính test giả, diễn tập hoặc một lần tác giả nhận phương án là nghiệm thu người dùng; phiên trải nghiệm toàn hành trình được chuẩn bị sau M4 và deploy theo thứ tự đã chốt.

## 6. Điểm dừng và việc làm trước

Ưu tiên Gói 1: chứng minh nguồn M2 đã lưu vào đúng bản M3, tự viết/sửa và lưu/mở lại không mất dữ liệu. Chỉ sau đó mới tích hợp viết thử một cảnh, rồi góp ý có bằng chứng. Đường AI chưa đạt phải được ghi rõ; không che bằng điểm số hoặc chặn quyền viết tay.

Dừng phạm vi M3 sau khi bốn gói có bằng chứng kỹ thuật và một vòng sửa đã kiểm chứng. Lỗi nguồn, mất dữ liệu, nhận nhầm bản hoặc góp ý dẫn sai trong phạm vi đã chốt phải được xử lý và kiểm chứng lại trước khi gọi phần đó đạt. Nếu chưa xử lý, ghi rõ phần chưa đạt và giữ nghiệm thu mở; việc ghi trạng thái không thay thế khắc phục lỗi. Các cải thiện thẩm mỹ/prompt ngoài lỗi chặn được ghi lại để chuyển sang M4, không kéo dài harness thành sản phẩm riêng.

Tài liệu nền: [PR #51 tích hợp Gói 4 M2](https://github.com/thomasMinh1995/firstframe-ai/pull/51), [review Gói 4](../testing/scene-staging-g4-review.md), [định hướng phim ngắn](vietnam-first-screenplay-mvp.md), [plan harness](harness-improvement.md). M3 không tự sửa story plan/dàn cảnh theo phản hồi kịch bản; hướng hai chiều chỉ phát triển sau với tác giả chủ động duyệt.
