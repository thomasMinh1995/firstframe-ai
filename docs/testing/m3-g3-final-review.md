# Review kỹ thuật cuối — M3 Gói 3

Ngày 27/10/2026. Nhánh `feat/screenplay-evidence-feedback`, base `dev` tại `28de3ac` sau PR #54. Review để commit/PR phần kỹ thuật Gói 3 theo yêu cầu tác giả; không triển khai Gói 4. Không chạy thêm model thật trong lượt review này.

## Kết luận và phạm vi

**Không còn lỗi kỹ thuật chặn được xác nhận trong phạm vi đã kiểm tra. Có thể đóng gói PR phần kỹ thuật. Chất lượng critic chưa đạt; nghiệm thu Gói 3 còn mở.** Đây không phải xác nhận góp ý AI đúng hoặc đủ tốt để demo/nghiệm thu.

Thay đổi cho phép review một cảnh đã lưu, giữ snapshot/nguồn riêng, kiểm ID/quote trước khi mở liên kết, nhận ghi nhận hữu ích/dẫn sai/chưa đủ căn cứ/bỏ qua, rồi để tác giả tự sửa và chủ động review lại. Không tự sửa/nhận, không chấm điểm, không tự gọi AI khi lưu hoặc điều hướng.

Review đọc cả route/schema, ProjectStore, luồng lưu dự án, writer Gói 2, provider/dataset, adapter nguồn/prompt, decoder frontend, các callback lưu/inspect/assessment, liên kết nguồn và test. Giả định sử dụng local cho phim ngắn, giới hạn dữ liệu hiện có; không đánh giá tải nhiều người dùng/dự án lớn.

## Kiểm tra kỹ thuật

- Nguồn do backend giữ, client không ghi đè review/source/history. Cùng ID tác vụ không gọi model lại; ID dùng sai yêu cầu bị từ chối. Lưu checkpoint/revision trước gọi, chặn lượt AI M3 mới khi pending, kết quả muộn chỉ cập nhật record riêng bằng transaction.
- Bỏ lượt không bị kết quả muộn kích hoạt lại. Sửa ở cửa sổ khác không bị thay bằng snapshot cũ; revision lỗi trả 409. Assessment chỉ cập nhật metadata, giữ buffer và bản server; không giả là đã lưu phần kịch bản đang sửa.
- Quote phải nằm trong đúng nguồn; note phải dẫn text cảnh đích, nghi lệch ý đồ phải có lựa chọn tác giả. Mã ngắn chỉ ở giao thức model; ID gốc dùng cho dữ liệu lưu và UI. Không tự sửa ID/quote, không tìm nguồn gần giống để cứu output.
- Frontend kiểm source/quote độc lập với snapshot, không chỉ tin cờ hợp lệ. Nguồn cũ mở snapshot cũ; chỉ focus vào nội dung hiện tại khi còn khớp, không có sửa liên quan chưa lưu. Sửa cảnh lân cận làm review cũ không còn hiện hành; không cấp lại nguồn sau sửa.
- Lỗi provider/quote/schema/ngữ cảnh/quota giữ bản tác giả và đường lưu nháp. Dataset M1 không chứa review M3; ghi log/dataset dùng chính sách local hiện có. Không thay provider/model hoặc `.env`.
- Không thêm phụ thuộc, judge, auto-fix, embedding hoặc đồng bộ sửa hai chiều. Helper giới hạn ngữ cảnh được dùng chung với writer; request/schema/prompt Gói 2 giữ nguyên.

## Kết quả kiểm thử trên code cuối

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend | **499 passed, 1 skipped**, 148,46 giây |
| Production build và typecheck | Qua; build QA dùng API fixture riêng, sau QA build lại theo cấu hình mặc định |
| Contract Node | M3 review, M3 screenplay, M2 transport, progress và onboarding qua |
| Browser Gói 3 | Qua lưu trước gọi, nguồn/focus, đọc không ghi/gọi AI, buffer assessment/inspect, tự sửa/lưu/review bản mới, cảnh lân cận cũ, mất phản hồi không retry, quote sai, timeout, notes rỗng, reload |
| Browser hồi quy | M3 viết tay và Gói 2 AI viết thử qua bằng provider giả |
| Màn hình | Chrome headless 1280/390/320 px, không tràn ngang hoặc page error |
| Phạm vi file | Chỉ runtime/test/prompt/báo cáo và fixture tổng hợp liên quan Gói 3; không stage tài liệu local cũ ngoài phạm vi |

Browser dùng SQLite/API/provider giả riêng, không mở database tác giả; không có thêm model thật/ảnh/API trả phí. TypeScript compile contract ban đầu dùng target cũ thiếu lib findLastIndex; chạy lại với ES2023 thành công, không sửa source để né lỗi. Warning Starlette/httpx và CSS `start` có sẵn còn nguyên. `git diff --check`, kiểm liên kết tài liệu và hash plan/roadmap/prototype/`.env` đều qua.

## Chất lượng và nghiệm thu còn mở

Giữ prompt v4 đang có trên nhánh, không tự rollback/chọn model khác hoặc chạy bù. [Đợt Qwen v4](m3-author-control-qwen7b-comparison.md) cho 4/6 qua hợp đồng, nhưng chỉ 1/3 bản vi phạm có nhận xét đúng/đủ nguồn đến người dùng. Các bản tuân thủ còn bị góp ý sai hoặc ép thêm quyết định/hành động. [Gemma v3](m3-gemma2-vs-qwen-v3.md) có ba timeout và chưa cung cấp đủ bằng chứng để thay model mặc định.

Các lỗi này là hạn chế chất lượng được tác giả cho phép ghi rõ khi đóng gói phần kỹ thuật; không đánh dấu đã sửa hoặc đã nghiệm thu. Quote đúng, test fake qua, tác giả bỏ qua góp ý hoặc cảnh báo AI đều không thay thế việc khắc phục lỗi dẫn sai theo plan hiện có. Guard không xác nhận lập luận hoặc sự nhất quán giữa các note; UI hiện rõ cảnh báo này và giữ quyền tác giả tự quyết.

Các đợt thử v1–v4 được giữ nguyên input/output/lỗi/manifest và source archive; chỉ fixture tổng hợp vào repo. Không sửa plan/roadmap/prototype, không đóng #7/#22/#26, không triển khai đọc toàn bản/chọn nguồn M4 của Gói 4. Nghiệm thu chất lượng AI và nghiệm thu người dùng tiếp tục mở.


## Bổ sung bằng chứng Gemma v4 và lượt lặp Qwen v4

Lần cập nhật PR #55 này chỉ thêm tài liệu và bằng chứng đã lưu, không sửa runtime hoặc chạy thêm model. Kết quả kiểm thử kỹ thuật ở trên thuộc lượt review trước, không được trình bày như đã chạy lại test trong lần bổ sung tài liệu.

- [Gemma v4 so với Qwen v4](m3-gemma2-vs-qwen-v4.md): 4/6 qua hợp đồng, bằng Qwen v4; không có timeout trong đợt v4. Không lặp cáo buộc sai ý đồ trên ba bản tuân thủ, nhưng còn góp ý ít căn cứ, 3/6 phản hồi tiếng Anh, hai lượt bị note phụ thiếu bằng chứng cảnh đích làm failed. Ca đèn pin vi phạm chưa có nhận xét trực tiếp/đủ nguồn dùng được. Context thực Gemma 8192, Qwen 16384 nên không khẳng định đối chứng cùng effective context.
- [Lượt lặp Qwen v4](m3-qwen-v4-repeat2.md): 5/6 qua hợp đồng so với 4/6 đầu, nhưng 3/6 ca đổi trạng thái ready/failed, nhận xét sai/ép thêm vẫn còn. Không chọn output tốt hơn giữa hai lượt để công bố một bộ đạt.

**Chất lượng critic chưa đạt; nghiệm thu Gói 3 vẫn mở.** Những kết quả bổ sung không thay việc sửa và kiểm chứng lỗi dẫn sai theo plan hiện có, không đóng #7/#22/#26 hoặc triển khai Gói 4. Input/output/lỗi/manifest/audit của các lượt cũ và mới giữ nguyên; chỉ diễn giải tình trạng bổ sung vào PR trong các báo cáo này.
