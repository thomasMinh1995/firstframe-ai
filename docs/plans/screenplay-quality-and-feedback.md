# Task 2 — Chất lượng phát triển kịch bản và góp ý AI

- Ngày lập: 04/11/2026.
- Review phạm vi: 04/11/2026; thu gọn đợt đầu vào Story plan và vòng góp ý–sửa.
- Trạng thái: các đợt [baseline](../testing/task-2-screenplay-quality.md),
  [ngữ cảnh card](../testing/task-2-card-context.md) và
  [chọn quyết định](../testing/task-2-decision-selection.md) đã được ghi lại.
  Nền trước đợt 2.2a giữ `e71d863`: ca thời gian có tiến bộ, ràng buộc chưa đạt.
  PR #98 vẫn draft; #96 còn mở.
- Cập nhật và review 04/11: mục 2.2a đã có bản triển khai kỹ thuật trên
  nhánh draft. Full backend 894 passed, 1 skipped; năm lượt model đầu chưa
  qua gate, chưa nhận ứng viên vào dev. Xem
  [báo cáo 2.2a](../testing/task-2-decision-checks.md). Checks không đồng
  nghĩa model đã hiểu đúng các lựa chọn; #96 vẫn mở.
- Tiếp nối Task 1, đã merge qua PR #95 vào `dev` (`d8d6b60`).
- Source đã đối chiếu: bản triển khai Task 1 tại `8454167`, các module sáng tác,
  prompt, runner và bằng chứng hiện có. Khi triển khai phải ghi HEAD `dev`
  thực dùng; workspace chính hiện còn thay đổi local nên không dùng nó làm
  baseline đánh giá và không ghi đè các thay đổi đó.

## Mục tiêu

Giúp tác giả phát triển chất liệu đời sống thành diễn tiến có thể hình dung
trên màn ảnh, nhận ra một chỗ đáng sửa và tự chọn cách sửa. Chất lượng cần
thể hiện trong nội dung cụ thể: hành động, hình ảnh, âm thanh, nhịp, lời thoại
và quan hệ giữa các cảnh; không suy ra từ JSON hợp lệ hoặc điểm AI tự chấm.

AI được đề xuất chi tiết và cách kể mới phù hợp với nguồn. Tác giả được đọc,
chỉnh hoặc bỏ; phần chưa quyết định vẫn là phương án, không được gán thành
ý đồ đã chốt. Giữ đúng nguồn không có nghĩa chỉ chép lại brief hoặc cấm mọi
sáng tạo. Tương tự, yếu tố điện ảnh không đồng nghĩa phải thêm tên góc máy,
ánh sáng đẹp hoặc mô tả dài: một hành động, khoảng dừng hay âm thanh chỉ có
ích khi giúp kể điều tác giả muốn.

Giữ định hướng phim ngắn gần đời sống mà chủ sản phẩm muốn tham chiếu TPD:
một chuyện nhỏ, im lặng, chuyện vui hoặc kết mở đều có thể là lựa chọn hợp lệ.
Đây là hướng đánh giá của FirstFrame, không tuyên bố tái tạo phương pháp hay
phong cách của một cơ sở đào tạo.

Task 1 đã tổ chức cách làm việc. Task 2 cải thiện chất lượng ở các lượt AI
hiện có. Pilot với người viết thật và nghiệm thu trải nghiệm thuộc Task 3.

## Source hiện có và ý nghĩa đối với phạm vi

| Điểm trong source | Đã có | Việc Task 2 cần kiểm tra |
| --- | --- | --- |
| `backend/app/application/workflow.py` | Reasoning → planning → evaluation, ngữ cảnh tác giả, lựa chọn ngôn ngữ và prompt theo profile | Chọn đúng đường gọi thực tế; góp ý toàn plan và góp ý card không cùng nhiệm vụ |
| `domains/short-film/prompts/story_mentor_prompt.md` | 0–3 câu hỏi, cho để mở và tách đề xuất AI | Câu hỏi có giúp ra quyết định hay hỏi lại/thêm tiểu sử không cần thiết? |
| `story_planner_prompt.md`, `knowledge/film_rules.json`, `rubrics/story_rubric.json` trong domain | Hướng dẫn hình ảnh/hành động; vẫn có các khung mục tiêu, leo thang, chuyển biến và mặc định 5–20 phút | Đo xem hướng dẫn chung có lấn át brief ngắn, quan sát hoặc kết mở; chưa coi sự tồn tại của từ khóa là lỗi model đã được chứng minh |
| `backend/app/application/scene_suggestions.py` | Gợi ý list/append/develop theo nguồn; giữ proposal riêng | Có lặp sự kiện, nhảy điểm dừng hoặc tự thêm kết cục? |
| `backend/app/application/screenplay_writing.py`, `screenplay_composition.py` | Viết/sửa cảnh hoặc khối; profile Qwen 7B có `source-preserving-v1` và `bounded-reactions-v1` | Giữ nguồn là nền an toàn; sao chép action và chọn mẫu thoại chưa chứng minh khả năng phát triển cảnh hay thoại tự nhiên |
| `backend/app/application/screenplay_review.py` | v8: kiểm mâu thuẫn trực tiếp bằng nguồn; model phân loại độ rõ từng đoạn; diễn giải Việt/Anh cố định, `suggestion` rỗng | Đo ích lợi của nhận xét, phân biệt giới hạn kiểm tra cục bộ với đánh giá nhịp/toàn cảnh; không chỉ sửa prompt để hứa có phân tích điện ảnh toàn phim |
| `backend/app/application/screenplay_revisions.py` và editor hiện có | Nối góp ý hợp lệ với đề xuất sửa đúng cảnh/khối; tác giả nhận/chỉnh/bỏ | Một yêu cầu sửa nhỏ có tạo phương án đúng phạm vi và giúp xử lý vấn đề đã nêu? |

Các tên prompt trong bảng nằm tại `domains/short-film/prompts/` trừ khi đã ghi
đường dẫn khác. `PromptLoader` có cache; runner so sánh phải khởi tạo service
mới hoặc process mới cho mỗi phiên bản. Qwen 3B có prompt variant riêng,
không được đo variant đó rồi kết luận cho profile Qwen 7B.

## Bằng chứng cần dùng lại

- [Checklist đánh giá mentor/critic](../prompt-evaluation.md): đã có ca chất
  liệu quan sát, mâu thuẫn, để mở, đổi nguồn và ngôn ngữ; không tạo checklist
  thứ hai thay thế nó.
- [Critic v8](../evaluations/qa01-qwen-review-v8-2026-10-29/README.md): hai
  lượt 10/10 trên bộ ca phát triển. Đây là bằng chứng cho kiểm tra nguồn và
  mâu thuẫn trực tiếp, không phải đánh giá nghệ thuật tổng quát. Không dùng
  thất bại v4 làm kết luận về runtime v8.
- [Writer v25](../evaluations/qa01-new-briefs-final-review-2026-10-30/README.md):
  hai lượt 5/5 brief, 19/19 cảnh mỗi lượt và hồi quy 8/8; báo cáo đã ghi rõ
  thoại có cấu trúc và chưa có người đọc độc lập. Giữ các gate này làm hồi quy,
  không dùng nguyên văn action trùng fixture làm thước đo sáng tác mới.

## Phạm vi đợt đầu

Ưu tiên **chất liệu → làm rõ → Story plan → tác giả sửa → góp ý đúng bản sửa**.
Đây là nơi người viết tìm cách kể trước khi đi vào từng cảnh, cũng là đường
đã có mentor, planner và góp ý plan/card trong `workflow.py`.

Chỉ truy xuống dàn cảnh, writer hoặc critic v8 nếu lỗi quan sát được nằm ở
đó. Không mặc định sửa tất cả công đoạn. Vòng sửa có thể do tác giả tự làm;
không bắt buộc gọi AI viết lại hay xuất PDF để chứng minh chất lượng plan.

## Ba bước triển khai

### 2.1 — Chốt bộ ca nhỏ và đo baseline

1. Tạo worktree sạch từ `dev` mới nhất. Ghi commit, model/digest, tham số thực,
   prompt/hash và nhánh xử lý thực dùng. Không đổi model trong cùng phép so sánh.
2. Dùng hai brief mới để chẩn đoán: một chất liệu đời thường còn mơ hồ và một
   tình huống vui/khó xử đã rõ hướng kể. Giữ một brief thứ ba chưa dùng để
   phát triển prompt cho lượt kiểm tra cuối; chọn một khoảnh khắc quan sát,
   có thể không thoại/kết mở. Đây là độ đa dạng của bộ thử, không phải ba
   phong cách bắt buộc của FirstFrame. Số cảnh theo chất liệu và thời lượng;
   không ép mọi brief phải có một quyết định để mở.
3. Với mỗi brief, ghi ngắn điều tác giả đã chọn, điều chưa biết, hiệu quả
   mong muốn và những kiểu hiểu sai cần tránh. Chốt các tiêu chí này trước
   khi chạy, không so với một cốt truyện đáp án duy nhất. Chỉ dựng cặp bản
   tuân thủ/vi phạm nếu cần tái hiện một lỗi góp ý cụ thể.
4. Chạy một lượt mỗi brief phát triển qua làm rõ → plan → sửa một chi tiết
   theo ý đồ → lưu → góp ý. Dùng đúng đường gọi riêng của Task 1. Người đọc
   chọn thao tác sửa sau khi đọc plan, ghi lại lý do; không cố tạo lỗi để
   bắt AI phải có nhận xét. Không bắt nhận proposal hoặc chạy bước kế tiếp.
5. Đọc kết quả và lập danh sách lỗi theo công đoạn. Chọn tối đa hai nhóm lỗi
   có tác động rõ nhất để sửa trong đợt đầu; ưu tiên lỗi làm sai ý đồ hoặc
   khiến người viết không biết sửa gì. Nếu baseline đạt, không sửa để đủ việc.

Tận dụng ứng dụng/API và cách lưu evidence sẵn có. Có thể thao tác trên UI
với dự án tạm; không cần viết runner toàn luồng trước khi đọc được baseline.
Nếu một ca phải lặp nhiều lần, bổ sung đầu vào cho script phù hợp; chỉ tạo
một script tuần tự mỏng khi thao tác hiện có không đáp ứng việc tái lập.
Các runner sau chỉ dùng khi thay đổi đụng tới phạm vi của chúng:

- `check_scene_writing.py`: tám ca writer đã đóng băng.
- `check_multiscene_writing.py --cases ...`: bộ cảnh mới, có tiếp nối nguồn
  từ cảnh trước; ghi rõ outline kiểm soát không phải outline planner sinh.
- `check_review_context.py`: mười ca nguồn/critic v8. Runner đang gắn với
  fixture/Qwen cụ thể; chỉ thêm đầu vào `--cases` nếu bộ ca mới cần nó.
- `check_draft_release.py`: smoke luồng tự động đang có; không dùng nó làm
  bằng chứng đã kiểm đủ luồng từng công đoạn của Task 1.

### 2.2 — Sửa đúng điểm đã đo, giữ hợp đồng ứng dụng

Điểm xuất phát là mentor/planner/góp ý plan. Bảng dưới là bản đồ chỗ sửa khi
có lỗi, không phải danh sách tính năng phải triển khai đủ. Ưu tiên một nhóm
lỗi trước; chỉ nhận nhóm thứ hai nếu liên quan trực tiếp và vẫn kiểm chứng
được trong cùng đợt.

| Nhóm lỗi được tái hiện | Chỗ sửa ưu tiên | Giới hạn |
| --- | --- | --- |
| Mentor hỏi lại hoặc áp đặt diễn biến | Prompt mentor đúng profile | Giữ 0–3 câu hỏi, không thêm model call |
| Plan ép cao trào/hòa giải, kể cảm xúc thay vì hành động | Prompt planner hoặc guidance `film_rules`/rubric thực sự được truyền | Điều chỉnh hướng dẫn theo hình thức/thời lượng tác giả; giữ schema plan và sáu tiêu chí hiện có |
| Dàn cảnh lặp sự kiện hoặc viết vượt điểm dừng | Prompt scene suggestions; adapter nếu gửi sai ngữ cảnh | Giữ mode và cơ chế proposal/nguồn hiện có |
| Cảnh/thoại chưa đạt yêu cầu | Prompt writer hoặc logic composition đúng nhánh lỗi | Đo cả profile bảo thủ và đường viết/sửa đầy đủ; không mở rộng regex/kho mẫu theo từng fixture để tăng tỷ lệ đạt |
| Góp ý sai nguồn, báo lỗi vô căn cứ hoặc không giúp chọn bước sửa | Nguồn/đích review, prompt hoặc phần trình bày hiện có | Giữ chứng cứ và quyền tự quyết; không nới guard, không tự sinh lời sửa có vẻ cụ thể nhưng không có căn cứ |

Mỗi thay đổi cần có ví dụ trước/sau từ cùng input, giải thích được vì sao
sửa ở file đó và một test hồi quy khi có logic/nguồn thay đổi. Nếu đổi prompt
writer/review, cập nhật `PROMPT_VERSION` tương ứng để truy vết.

Đối với critic v8, việc không có `suggestion` là chủ ý hiện tại. Đổi câu chữ
trong mẫu hiển thị chưa làm critic hiểu quan hệ giữa các đoạn. Nếu ca lỗi cần
ngữ cảnh cảnh/lân cận, trước hết xem snapshot hiện có có đủ để sửa đầu vào
đúng phạm vi và kiểm nguồn hay không. Giữ cơ chế đề xuất sửa độc lập. Không
hứa đánh giá toàn phim bằng cách sửa prompt từng đoạn; nhu cầu đó cần quyết
định phạm vi tiếp theo. Báo cáo phải ghi rõ phần nào của Task 2 còn mở.

### 2.2a — Đợt tiếp: đối chiếu từng quyết định trong critic card

Đợt chọn quyết định đã loại năm ứng viên sau 15 call: có ID thật vẫn có thể
viện sai nguồn; dẫn đúng lệnh cấm vẫn có thể gợi ý làm điều bị cấm. Đợt này
thử làm rõ kết quả đối chiếu trong output thay vì tiếp tục đổi thứ tự hoặc
nối dài prompt. Không suy từ một nhận xét rằng mọi lựa chọn đã được kiểm.

**Điều chỉnh phạm vi đã review:** cho phép bổ sung `decision_checks` vào
schema phản hồi nội bộ của đường critic card có `review_context`. Vẫn một
call model và một nhận xét chính trong `reviews`. Không thêm field vào
public API, feedback/RevisionNote lưu trong dự án hoặc schema database.
Checks chỉ đi cùng response trong dataset/evidence hiện có; không thêm UI.
Các đường góp ý khác, planner và critic v8 theo cảnh giữ nguyên.
Cùng hợp đồng áp dụng cho plan mới và bản tác giả đã sửa khi đi qua đường
critic card này. Tiếp tục nhánh `fix/screenplay-quality-and-feedback`, ghi
HEAD thực dùng khi bắt đầu; không reset nhánh hoặc chạm workspace chính.

#### A. Phản hồi có đối chiếu từng nguồn, giữ nguyên quyền tác giả

- Dùng nguyên các `decision_id`, nội dung và câu hỏi từ context; không dùng
  AI tách thành luật mới, phân hạng ý đồ hay gán câu chưa trả lời thành lựa
  chọn. Một quyết định có nhiều mệnh đề phải được xét đầy đủ trong cùng mục.
- Mỗi quyết định có đúng một mục check. Mục đó ghi trạng thái đối chiếu
  bản sửa, căn cứ card và lý do ngắn; đồng thời ghi trạng thái/lý do đối
  chiếu suggestion nếu có. Trạng thái gồm `aligned`, `mismatch`, `uncertain`
  và `not_applicable` (không liên quan đến phần đang xét).
- Đặt checks sau `reviews` trong phản hồi để đối chiếu đúng chuỗi suggestion
  vừa sinh, không phải một phương án sửa khác chưa được trả cho người viết.
  Không thêm lượt tự sửa hoặc call kiểm tra riêng.
- `mismatch` phải có căn cứ card thuộc phạm vi review và nêu chi tiết thực
  sự xuất hiện. `not_applicable` phải giải thích vì sao không liên quan;
  không dùng thay cho thiếu thông tin. Nếu cần nguồn ngoài đoạn được gửi
  thì dùng `uncertain`, không suy thành toàn phim đã tuân thủ.
- Phân biệt điều bắt buộc, điều cấm, quyền đề xuất và phần còn để mở. Một
  chi tiết chưa có trong brief vẫn hợp lệ nếu tương thích; quyền đề xuất
  không thành yêu cầu bắt buộc. Các lựa chọn tự mâu thuẫn cần hỏi tác giả,
  không tự chọn một phía hoặc ép kết luận vi phạm.
- Giữ các đoạn liên tục trước mẩu card, scope bản sửa/lân cận và ID/trích
  dẫn hiện có. Không coi các card là trạng thái đồng thời. Không ép kịch
  tính, thông điệp, hòa giải hay kết đóng để tạo một nhận xét.

#### B. Kiểm tính đầy đủ và nhất quán trước khi lưu feedback

Tận dụng `workflow.py` và `revision_review.py`; không tạo lớp điều phối mới.
Chỉ kiểm bằng code những điều xác định được từ output và context:

| Điều kiện | Cách xử lý |
| --- | --- |
| Thiếu, trùng hoặc thêm decision ID; căn cứ card ngoài scope | Từ chối output; giữ toàn bộ guard nguồn/đích hiện có |
| Có check bản sửa là `mismatch` | Nhận xét chính phải nêu vi phạm và viện một quyết định được đánh dấu vi phạm; không thay bằng lời khen/ý tưởng chung |
| Không có vi phạm nhưng có bất định liên quan chưa giải quyết | Không nhận `aligned`; output bất nhất bị từ chối, không tự đổi nhãn. Nhận xét `uncertain` nhất quán dùng đường trung tính hiện có |
| Các check quyết định đều phù hợp nhưng cặp card có lỗi tiếp nối | Vẫn cho phép `mismatch` về diễn tiến với cặp/nguồn hợp lệ; không buộc bịa một quyết định bị vi phạm |
| Có suggestion nhưng check nào đánh dấu nó vi phạm hoặc chưa đủ căn cứ | Từ chối toàn bộ output qua đường lỗi review hiện có; không xóa suggestion để cứu nhận xét |
| Suggestion rỗng | Check suggestion là không áp dụng; guard `mismatch` cần bước sửa vẫn giữ nguyên |

Một check `not_applicable` không được dùng làm căn cứ trực tiếp cho nhận
xét chính. `aligned` cần căn cứ phù hợp, không được suy từ mọi check đều
không áp dụng. `passed` tiếp tục suy từ nhận xét hợp lệ; không dùng điểm hay
cờ tự chấm của model để bỏ qua các kiểm tra này.

Checks là tự đối chiếu của cùng model, không phải bộ chấm độc lập. Code
không chứng minh được lý do có đúng ngữ nghĩa hay model đã xét hết các mệnh
đề. Các trường hợp viện sai nguồn, bịa chi tiết, bỏ sót hoặc đánh dấu sai
`not_applicable` vẫn phải được đọc trên output thật; checklist đủ mục chưa
được tính là chất lượng đã đạt.

Output không hợp lệ dùng lỗi review hiện có: giữ draft, feedback cũ cùng
nguồn và lịch sử; không công bố feedback mới, không sửa hộ hoặc retry model.
Lựa chọn chưa rõ nhưng được trình bày nhất quán bằng `uncertain` là góp ý
trung tính hợp lệ, không phải lỗi kỹ thuật. Câu hỏi làm rõ không được coi
là đã chốt hoặc thay đổi lựa chọn; check suggestion xét nó có áp đặt điều
gì trái nguồn hay không. Tác giả vẫn tự sửa/giữ/bỏ.

Trong `dataset_corrections.py`, đọc/biên tập/replay output theo schema đã
ghi: bản cũ giữ hợp đồng cũ, bản mới bắt buộc checks mới. Không thêm default
checks hoặc fallback legacy để cứu response mới bị thiếu. Tái dùng cùng
kiểm tra nhất quán cho output mới ở runtime và dataset; không migrate dữ
liệu dự án hay sửa bản ghi gốc. Cập nhật fake provider/fixture liên quan.

#### C. Kiểm thử nhỏ trước khi nhận ứng viên

1. Test contract cho đủ/thiếu/trùng/ID lạ, căn cứ ngoài scope, kết luận
   không khớp checks, suggestion còn vi phạm/bất định, cùng ca hợp lệ.
   Giữ hồi quy nguồn/quote, sửa–lưu–review thất bại, `uncertain`, ngôn ngữ,
   lỗi tiếp nối độc lập với quyết định và dataset cũ/mới. Test mới chỉ bảo
   đảm logic, không mô phỏng rằng model hiểu ràng buộc bằng mock.
2. Trước model, đóng băng input/kỳ vọng và ngân sách call/thời gian cho
   batch mới. Giữ model/tham số, nguồn snapshot và scope; so với baseline
   bằng đúng các input đó. Output mới dài hơn phải được đo thời gian và
   mức hoàn tất; không cắt bớt quyết định hoặc chia thêm call ngầm để vừa
   context/timeout. Nếu không chạy được trong giới hạn thì loại ứng viên,
   chưa xây hệ thống chia batch hoặc ngân sách mới.
3. Kiểm trước các cặp bánh/áo: bản vi phạm phải viện đúng lựa chọn, giải
   thích đúng chi tiết và đề nghị giữ mọi giới hạn; bản tuân thủ không bị
   bịa lỗi. Có ca ngồi → đứng, câu trả lời không liên quan, lựa chọn cho
   phép/để mở và một ràng buộc nhiều mệnh đề. Chốt thêm ca các lựa chọn tự
   mâu thuẫn và một cặp mới giữ lại. Không tính ca từng dùng để chỉnh prompt
   là ca giữ lại. Đọc căn cứ và suggestion, không chỉ đếm nhãn/ID.
4. Chỉ khi qua lượt kiểm tra đầu mới xác nhận ba lượt cho các ca bị ảnh
   hưởng; giữ mọi lượt lỗi, không chọn lượt đẹp. Tận dụng runner/evidence
   hiện có, không thêm model judge, dashboard hoặc framework. Chạy hồi quy
   module bị đổi; không chạy toàn writer/v8/PDF vì thay critic card.

Nhận ứng viên chỉ khi đối chiếu có ích hơn baseline, không tái hiện các lỗi
chặn trong ba lượt xác nhận và giữ các ca đúng. Nếu checks vẫn đủ mục nhưng
lý do sai hoặc suggestion trái giới hạn, loại ứng viên. Chưa có PO/người
đọc độc lập duyệt thì ghi đúng mức bằng chứng; không coi đó là nghiệm thu
chất lượng tổng quát hoặc tự đóng #96. Checklist nội bộ không biến FirstFrame
thành hệ thống chấm điểm tác giả hay thay thế việc phát triển kịch bản.

#### Review plan cập nhật — 04/11/2026

Đã đối chiếu với source hiện có và bằng chứng năm ứng viên bị loại. Những
điểm đã chỉnh sau review:

- Giới hạn phép kiểm vào đoạn đang xét; `not_applicable` cần lý do và thiếu
  nguồn phải để mở. Tránh một checklist giả vờ đã kiểm toàn phim.
- Tách lỗi tiếp nối khỏi vi phạm lựa chọn, giữ sáng tạo tương thích, kết
  mở và quyền đề xuất. Tránh ép một “cốt truyện đúng” hoặc bịa quyết định.
- Từ chối cả output nếu suggestion tự bị đánh dấu không an toàn với lựa
  chọn; không âm thầm cắt phần lỗi và vẫn công bố như góp ý đã đạt.
- Ghi rõ tương thích dataset và giới hạn dài/thời gian; giữ một call,
  một nhận xét hiển thị, không thêm công đoạn, migration hay hạ tầng.
- Kiểm đúng suggestion đã sinh, không đổi nhãn hộ model hoặc coi câu hỏi
  làm rõ là một quyết định mới của tác giả.

Kết luận review của agent: plan đủ rõ cho một lần triển khai thử có giới
hạn trong #96; không có điểm chặn còn mở trong phạm vi plan. Hiệu quả của
checks chưa được chứng minh, phải qua mục C trước khi nhận runtime. Lượt
review plan ban đầu chỉ thay tài liệu, chưa triển khai hoặc gọi model.

Kết quả triển khai sau review: [báo cáo 2.2a](../testing/task-2-decision-checks.md).
A/B đã có code và test contract trên nhánh draft; C chưa đạt. Đã dùng
12/28 call, 394,002/1.500 giây provider, giữ nguyên nguồn/draft ở các lỗi;
không xác nhận ba lượt hoặc nhận ứng viên chỉ vì guard từ chối output.

### 2.3 — So sánh, hồi quy và bàn giao

1. So sánh baseline và bản sửa trên cùng hai brief, cùng model/tham số và
   cùng nguồn đầu vào của công đoạn được sửa. Nếu sửa tác vụ phía sau, dùng
   snapshot giống nhau thay vì sinh lại toàn bộ plan rồi so hai nguồn khác
   nhau. Trước khi gọi prompt sẵn sàng, chạy mỗi ca bị ảnh hưởng ba lần theo
   checklist hiện có; chỉ lặp tác vụ đã đổi, không nhân ba cả hành trình.
   Với brief giữ lại, đo baseline và bản sửa trước khi tinh chỉnh theo nó.
   Nếu dùng nó để sửa tiếp, ghi thành ca phát triển và cần một ca mới để
   kiểm tra khả năng áp dụng ngoài ví dụ đã thấy. Không chọn lượt đẹp.
2. Chấm riêng kỹ thuật, nội dung và ích lợi sửa. Người đọc giải thích bằng
   chi tiết trên trang; không dùng một điểm tổng hoặc model judge để thay
   việc đọc. Nếu chỉ agent đọc, ghi đúng mức bằng chứng; PO/người đọc có
   kinh nghiệm xác nhận nội dung trước khi kết luận chất lượng đã đạt.
3. Chạy test giả/contract đúng module bị đổi. Nếu đụng writer/composition,
   dùng bộ tám ca writer và ca nhiều cảnh liên quan; nếu đụng critic v8/nguồn
   của nó, dùng mười ca v8. Không chạy lại các bộ đó chỉ vì sửa prompt mentor
   hoặc góp ý plan. Lượt model thật hồi quy phải nằm trong ngân sách đã chốt;
   bằng chứng cũ không được tính thành lượt mới trên code đã sửa.
4. Xác nhận vòng sửa giữ được bản gốc, lưu và đọc lại đúng bản. Chỉ kiểm lại
   chọn snapshot/PDF nếu thay đổi có thể ảnh hưởng nguồn xuất. Dùng fixture
   để kiểm điều phối; model thật để đọc chất lượng nội dung. Frontend test/
   typecheck/build cần chạy khi thay giao diện hoặc hợp đồng ảnh hưởng nó.
5. Lưu báo cáo `docs/testing/task-2-screenplay-quality.md` với before/after,
   lỗi còn lại, thời gian và kết luận từng ca. Evidence mới ở thư mục mới
   dưới `docs/evaluations/`, không sửa các đợt cũ.

## Phiếu đọc nội dung và tiêu chí hoàn tất

| Câu hỏi cần trả lời | Bằng chứng tối thiểu |
| --- | --- |
| Có giữ đúng lựa chọn và phần để mở? | Đối chiếu brief/câu trả lời với plan và cảnh; chỉ rõ mọi chi tiết AI thêm |
| Plan có giúp tìm ra cách kể? | Chỉ ra một diễn tiến/chi tiết cụ thể phát triển được chất liệu; phân biệt phương án có ích với việc nhắc lại brief hoặc thêm biến cố trang trí |
| Có thể hình dung câu chuyện bằng hành động, hình ảnh, âm thanh? | Nêu chi tiết phục vụ hiệu quả mong muốn, khoảng trống để người xem tự hiểu và chỗ đang giải thích thay cho thể hiện; không bắt mọi phim phải dùng đủ các yếu tố hoặc chỉ dẫn máy quay |
| Cảnh có tiếp nối và dừng đúng chỗ? | Đối chiếu thứ tự, trạng thái người/vật và quan hệ giữa cảnh; không tự thêm kết cục |
| Lời thoại có đúng quan hệ và diễn được? | Đọc thành tiếng, kiểm xưng hô và sắc thái; lời mẫu đúng vai chưa tự động được coi là tự nhiên |
| Góp ý có đúng và giúp chọn một sửa đổi? | Chỉ rõ nguồn, vấn đề/tác động; bản tuân thủ không bị bịa lỗi. Nếu chưa đủ căn cứ thì để mở; tác giả có thể diễn đạt một bước sửa rồi xem phương án đúng phạm vi |

Đọc các tiêu chí theo công đoạn: Story plan chưa cần lời thoại hoàn chỉnh;
chỉ chấm lời thoại khi đã đi vào bản cảnh. Ghi nhận khác biệt sở thích riêng
với lỗi rõ; tác giả được chọn cách kể khác người góp ý.

Hoàn tất **đợt đầu của Task 2** khi:

- Các lỗi chặn được chọn không tái hiện trong ba lượt xác nhận trên bộ ca
  đã chốt; không có regression nguồn, ngôn ngữ, quyền tác giả hay dữ liệu.
- Có đối chiếu nội dung cho thấy phần sửa hữu ích hơn baseline; nếu không
  có cải thiện hoặc chỉ đổi câu chữ, không nhận bản sửa như tiến bộ chất lượng.
- Trên ba brief có kết quả và ít nhất một vòng sửa–lưu–góp ý có lý do rõ;
  người đọc giải thích được điều gì thay đổi và vì sao giữ hoặc bỏ góp ý.
  Đây là phép đọc nội bộ, chưa chứng minh người dùng mới tự làm được.
- Nếu baseline đã đáp ứng tiêu chí, có thể kết thúc bằng evidence và kết
  luận không cần đổi code ở phạm vi đó. Phần chưa đạt ghi rõ, không kéo dài
  thử prompt/model vô hạn hoặc gọi một đợt nhỏ là hoàn tất toàn bộ Task 2.
- Báo cáo tách kết luận agent, người đọc/PO và phần chưa kiểm chứng. Việc
  triển khai và bàn giao evidence không chờ tuyển người pilot; PO/người đọc
  có kinh nghiệm duyệt nội dung, còn trải nghiệm người mới thuộc Task 3.

Không thay ngưỡng demo M1 9/9 hoặc pilot trong kế hoạch MVP; thử nghiệm Task 2
không tự đóng #7/#22/#26, không chứng minh lợi thế thị trường hay chất lượng
tổng quát từ vài fixture.

## Ngân sách và điểm dừng

Đợt chọn quyết định trước 2.2a: [review](../testing/task-2-decision-selection.md)
đã loại thêm năm ứng viên prompt/thứ tự dữ liệu sau 15 call. Runtime giữ
`e71d863`; chọn nguồn và giữ mọi giới hạn vẫn chưa đạt. PR #98 draft, #96
mở; chưa chạy ba lượt xác nhận cho ứng viên nào trong đợt này.

Mỗi batch giữ evidence/ngân sách riêng. Trước khi chạy batch mới, kiểm model
đã cấu hình và chốt
trần số call/thời gian cho batch từ số công đoạn và số đoạn đích thực tế;
một review có thể gọi nhiều lần nên không tính một lần bấm là một call.
Ghi cả tham số yêu cầu lẫn context thực nếu provider cung cấp. Dùng SQLite/
dataset tạm, fixture tổng hợp; không đưa bản thảo riêng vào evidence.

Không tự tải/đổi model, đổi `.env`, thêm API trả phí hoặc retry sinh lại để
vượt gate. Hết ngân sách thì lưu kết quả/lỗi và báo phần còn thiếu; không hạ
tiêu chí. Không gắn giới hạn toàn bộ chuỗi thử với deadline 60 giây của
critic từng review hoặc ngân sách demo M1.

Đợt đầu giao một thay đổi nhỏ cho tối đa hai nhóm lỗi đã đo và báo cáo đi
kèm. Chỉ cho phép mở rộng schema phản hồi nội bộ critic card ở mục 2.2a;
không đổi schema public API/dữ liệu dự án hoặc thêm migration, agent mới,
RAG/vector database, hệ thống chấm nghệ thuật, dashboard, nhật ký sáng tác
hoặc workflow engine. Không mở
rộng sản xuất phim/video AI; không bỏ cơ chế nguồn/lịch sử để model sáng tác
tự do hơn. Nếu cần năng lực mới vượt hợp đồng hiện tại, ghi thành quyết định
phạm vi tiếp theo cùng ví dụ lỗi, thay vì dựng hạ tầng trước.
