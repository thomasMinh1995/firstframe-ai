# Kiểm chứng Gói 3 — góp ý dàn cảnh có quyền chọn

- Ngày: 27/10/2026; nhánh `feat/scene-staging-feedback`, từ `dev` sau merge PR #49 (`306a36c`).
- Theo yêu cầu: PR Gói 2 đã chuyển khỏi Draft và merge vào dev. Việc merge được thực hiện với giới hạn chất lượng đã báo cáo, không đổi thành kết quả nghiệm thu. Không sửa plan/roadmap, prototype hoặc mở Gói 4.
- Gói 3 đã có luồng kỹ thuật cho ba nhóm: hành động & diễn xuất; không gian & chi tiết; cách nhìn qua máy quay. Phạm vi đóng gói PR chỉ gồm code, test, prompt và bằng chứng kiểm chứng Gói 3.
- **Chưa kết luận đạt toàn bộ nghiệm thu Gói 3:** quote khớp nguồn không đủ chứng minh lập luận đúng/hữu ích; đợt model thật còn suy diễn và gần sát ngân sách chờ. Trải nghiệm người dùng thật chờ full workflow theo quyết định đã thống nhất.

## Phần đã triển khai

- Một yêu cầu cho cảnh được chọn, dựa trên snapshot story plan/ý đồ, nội dung/ghi chú/lựa chọn của cảnh và hành động hai cảnh liền kề khi có. Không thêm embedding, router nhiều model, critic chấm điểm hoặc vòng tự sửa.
- Nguồn có ID/label/text do server lập. Model trả tối đa sáu ý, mỗi ý có một trường đích trong allowlist, evidence source ID/quote, lý do, phương án và tác động dự kiến. Nhóm được suy ra từ trường đích, không tin nhóm do model tự khẳng định.
- Mỗi ý phải có ít nhất một quote từ chính cảnh chọn; mọi ID và quote phải tồn tại/khớp nguyên văn trong snapshot. ID sai, quote sai/trắng, trường đích lạ hoặc payload không hợp lệ làm từ chối toàn bộ kết quả, không nhặt riêng phần đẹp. Raw/lỗi vẫn được ghi.
- Quote đúng chỉ xác nhận vị trí văn bản. UI nói rõ không chứng minh cách diễn giải/phương án đúng, phân biệt trích đoạn, lý do, tác động dự kiến và phương án có thể chỉnh. Không coi đây là xác nhận chất lượng sáng tác.
- Không ép đủ ba nhóm hay bắt có ý. Kết quả rỗng/câu hỏi là hợp lệ; câu hỏi hiển thị như tham khảo, không chặn tự viết, lưu hoặc bước sau.
- Lưu các batch Gói 3 vào `staging_proposals`, riêng với `scene_proposals` Gói 2 để client cũ không phải đọc mode mới trong danh sách cũ. Client bỏ các trường Gói 3 khi lưu vẫn giữ dữ liệu. Tái dùng request ID/checkpoint, stream/progress, ghi kết quả muộn trong transaction, source/revision/409 và recorder của Gói 2.
- Preview chỉnh từng ý nằm trong buffer/dirty và có thể lưu riêng; suggestion gốc/evidence/source vẫn giữ nguyên. Dùng một ý chỉ đưa giá trị vào đúng mục staging_choices, chưa đồng nghĩa lưu; cảnh khác, diễn tiến và story plan giữ nguyên. Backend kiểm tra đúng diff một mục khi lưu có marker dùng ý.
- Mục có nội dung được cảnh báo sẽ thay; có hoàn tác an toàn trước sửa tiếp. Nếu muốn tự sửa thêm phần khác, tác giả có thể giữ nội dung như bản tự chỉnh và bỏ marker, không tự gắn lại nguồn hoặc đánh dấu proposal đã áp dụng.
- Sau khi dùng/lưu làm nguồn khác snapshot, các ý còn lại giữ để đọc, không tự rebase hoặc áp dụng theo nguồn mới. Dùng lại/ý đã bỏ/nguồn cũ bị từ chối. No-op không làm nguồn đổi thì vẫn kiểm tra trạng thái từng ý.
- Bỏ một ý chỉ lưu trạng thái của ý bằng revision/CAS; không tự lưu thay đổi cảnh đang chờ. Buffer/ghi chú/ý khác đang sửa được giữ. Nếu sửa/đã dùng/bỏ ý ở cửa sổ khác, không coi đó là metadata AI để âm thầm nhận revision rồi ghi đè.
- Có thể bỏ yêu cầu chưa rõ kết quả. Không cam kết dừng inference trên máy chủ; kết quả đến sau vẫn giữ trạng thái đã bỏ, không kích hoạt lại. Không tự retry model khi mất phản hồi.
- Tab Dàn cảnh vẫn có hai câu hỏi tác giả tùy chọn và danh sách lựa chọn tự chỉnh. Chỉnh ý đưa focus vào textarea; dùng/bỏ/chuyển tab không tự gọi AI. Không tạo ảnh hoặc sửa tour trong gói này.

## Kiểm tra kỹ thuật

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend, chạy từ backend | **400 passed, 1 skipped**; cảnh báo TestClient/httpx hiện có |
| Gói 3 `test_scene_staging.py` | **10 passed**: quote/field sai, nguồn, ba nhóm, idempotency, edit/use/discard, đúng một trường, stale/409, rỗng/lỗi/manual/response muộn, client cũ và bỏ yêu cầu pending |
| Gói 2 `test_scene_suggestions.py` | **15 passed**, giữ các bảo vệ cũ |
| Frontend production build/TypeScript | Đạt; cảnh báo CSS nền hiện có |
| Transport `scene-contract.cjs` | Đạt: schema G3/allowlist, marker/edit chỉ gửi dữ liệu có thể sửa, preview/choice ở cửa sổ khác không bị coi là metadata AI |
| Progress `progress.cjs` | Đạt: progress thật, timeout/mất kết nối/lỗi và bảo toàn input |
| Chrome `scene-staging.browser.cjs` | Đạt trên bản cuối: pool riêng, focus khi chỉnh ý, tương tác Gói 2 và toàn bộ ca G3 |
| Chrome Gói 2 | Đạt với API/SQLite tạm/provider giả trước thay đổi pool; ca hỗn hợp G2/G3 có trong script G3 cuối |
| Chrome M1 focus/dialogue | Bản cuối: **4/4 và 2/2 đạt**, desktop và mobile |
| `git diff --check` | Đạt |

Browser dùng `ui_workspace_fixture.py`, SQLite/dataset tổng hợp tạm riêng, provider giả. Kiểm tra ba nhóm/quote, edit/save riêng, dùng đúng một mục/undo, stale các ý còn lại, bỏ ý giữ ghi chú chưa lưu, quote sai không hiển thị như ý hợp lệ, lost response không tạo thêm lượt, rỗng/câu hỏi, 1280/390/320px. Ca hỗn hợp tạo đề xuất Gói 2 sau góp ý Gói 3 phải giữ nguyên lịch sử Gói 3. Đã xem ảnh mobile; chưa kiểm tra Safari/Firefox, screen reader, thiết bị thật/IME hay tải đa người dùng.

Trong triển khai đã sửa lỗi từ kiểm tra: marker áp dụng cả batch staging phải bị từ chối thay vì rơi vào lookup proposal Gói 2; build bắt thiếu import/prop sau đổi pool và đã sửa trước bàn giao. Những lần chạy test/build lỗi thiết lập hoặc code trung gian không được tính là đạt. Không chạy model lại vì những sửa UI/lưu pool này; prompt/schema/service model đã đóng băng không đổi.

## Model thật — ba ca, dừng sau một lượt mỗi ca

Đã đóng băng ba brief/cảnh tuân thủ tổng hợp đã lưu và chạy Qwen 2.5 7B hiện tại, temperature 0.3, yêu cầu context 16384, hạn tường/provider 120 giây. Không sửa `.env`, không API trả phí, không retry, không dùng model để tự chấm và không áp dụng vào database người viết.

- 3/3 qua hợp đồng, tổng 18 ý; quote IDs/nguyên văn đều khớp snapshot.
- Thời gian: quiet **114,428**; comedy **116,929**; limits **117,001 giây**. Đạt ngân sách lượt nhỏ nhưng sát hạn; chưa phải cam kết độ trễ UI/demo. Máy không được cô lập tải và có kiểm tra browser cùng đợt, không suy rộng thành benchmark hiệu năng.
- Có phương án có thể làm nguyên liệu đọc: giữ khoảng cách/lối đi, cách thể hiện kín đáo đẩy đường, đặt đối tượng giữa khung hình. Không thấy thêm người bị cấm hoặc chốt kết mở trong ba output này.
- **Lý do/căn cứ còn yếu:** quiet trích “Cha, con gái” rồi khẳng định họ mặc quần áo hằng ngày; nguồn không nói trang phục. Trích “Căn bếp” rồi giả định cửa sổ/vị trí sáng không chứng minh bố trí thực tế. Các lựa chọn sáng tạo có thể được đề xuất nhưng không nên mô tả giả định như dữ kiện nguồn.
- **Phân loại mục còn sai:** quiet `setting` lại đề xuất ánh sáng; comedy `setting` đề xuất góc nhìn rộng. Backend chỉ đảm bảo đó là một trường cho phép, chưa chứng nhận ý phù hợp trường đó.
- **Hữu ích/diễn đạt:** comedy có “tránh chạm vào mắt An”, “ngửi một cách ngượng ngập”; cần người viết chỉnh nghĩa/cách diễn đạt. Limits lặp composition/angle gần giống nhau; lý do “có thể còn thức uống khác” làm lệch trọng tâm mời tiếp tục trò chuyện. Câu hỏi thêm hiệu ứng sáng chưa chắc cần cho cảnh, vì vậy không coi là yêu cầu bắt buộc.
- Đây là đối chiếu nội dung của Codex, chưa thay người có kinh nghiệm/PO. Quote thật không được chấm thành chứng minh toàn bộ nhận xét; không có kết luận nghiệm thu người dùng.

[Bộ đóng băng](../evaluations/scene-staging-feedback-qwen7b-2026-10-27/manifest.json), [input](../evaluations/scene-staging-feedback-qwen7b-2026-10-27/inputs.json), [prompt](../evaluations/scene-staging-feedback-qwen7b-2026-10-27/prompt.md), [schema](../evaluations/scene-staging-feedback-qwen7b-2026-10-27/schema.json), [toàn bộ output/raw/lỗi/thời gian](../evaluations/scene-staging-feedback-qwen7b-2026-10-27/results.json), [audit/hash](../evaluations/scene-staging-feedback-qwen7b-2026-10-27/audit.json). Runner cùng thư mục từ chối ghi đè kết quả cũ.

## Giới hạn còn mở

- Chưa xác nhận toàn bộ góp ý hữu ích, có lý do thực sự được nguồn hỗ trợ hoặc không dẫn sai trên chất liệu rộng hơn. Không mở thêm vòng tối ưu hoặc đổi model trong gói này.
- Thời gian gần ngân sách chờ, chưa tối ưu hoặc nới ngưỡng. Chưa nghiệm thu sáng tác/phiên người dùng; không đóng #7/#22/#26.
- Chỉ triển khai Gói 3; Gói 4, ảnh, M3 kịch bản và deploy/trải nghiệm full workflow chưa thực hiện. Không tự thay plan hoặc hạ tiêu chí để gọi gói đã đạt.

## Review trước khi mở PR — 27/10/2026

Đã rà diff và luồng liên quan: lưu project/revision, snapshot M1/M2, hai pool đề xuất, ghi kết quả muộn, dùng/bỏ/chỉnh từng ý, kiểm tra transport và các lời gọi UI. Phạm vi tải được kiểm tra là ứng dụng local với SQLite và tranh chấp revision giữa cửa sổ/yêu cầu; chưa đánh giá tải nhiều người dùng hoặc triển khai production.

Không phát hiện lỗi chặn đóng gói code Gói 3. Đã chạy lại toàn bộ backend: **400 passed, 1 skipped**; frontend production build/TypeScript, contract và progress đều đạt. Các ca Chrome G3 và hồi quy M1 ở bảng trên đã đạt trên cùng code, không chạy thêm model; hash input/prompt/schema/service/toàn bộ kết quả đóng băng được xác nhận lại.

Các hạn chế chất lượng và độ trễ model vẫn giữ nguyên như phần trên; đây không phải kết luận nghiệm thu sáng tác/người dùng. Plan, roadmap, prototype và các báo cáo thử nghiệm cũ không thuộc PR này.
