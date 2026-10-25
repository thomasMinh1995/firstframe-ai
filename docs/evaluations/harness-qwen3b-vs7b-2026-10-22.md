# So sánh harness Qwen 2.5 3B và 7B

**7B dùng hợp đồng khóa mục tiêu tốt hơn rõ rệt, nhưng chưa đủ để nâng model mặc định hoặc đưa nguyên mẫu vào runtime.** Trên draft cố định, số lượt qua validator của hợp đồng khóa tăng từ 7/36 với 3B lên 28/36 với 7B. Số lượt vừa qua validator vừa được agent chấp nhận nội dung chỉ tăng từ 1/36 lên 2/36; nhiều phản hồi hợp lệ vẫn đảo nghĩa vai, báo mâu thuẫn sai hoặc sửa trái brief. Đây là kết quả trên profile request 3B và nguồn lịch sử, chưa đánh giá hợp đồng runtime mới.

Lượt chính 7B chạy từ **08:58:50 đến 10:32:29 ngày 22/10/2026**, giờ Việt Nam: 93 phút 38 giây. Đủ **108 lời gọi sinh output: 12 planner, 96 critic**, không lỗi provider, timeout, schema hoặc retry/resume. Lượt 3B trước đó mất 45 phút 27 giây. Có một lượt 7B gián đoạn được giữ riêng và loại toàn bộ khỏi so sánh chính; chi tiết ở giao thức dưới đây.

## So sánh trên cùng draft cố định

12 ca × ba seed × hai hợp đồng. Mỗi cột có 36 lượt critic; toàn bộ prompt, input và schema của nhóm này khớp giữa hai model.

| Chỉ số / 36 lượt mỗi cột | 3B baseline | 3B khóa | 7B baseline | 7B khóa |
| --- | ---: | ---: | ---: | ---: |
| Qua schema | 36 | 36 | 36 | 36 |
| Qua validator nguồn/quote | 14 (38,9%) | 7 (19,4%) | 2 (5,6%) | 28 (77,8%) |
| Có tên phần/khóa sai | 0 | 0 | 31 | 0 |
| Có quote draft sai | 3 | 29 | 5 | 1 |
| Có quote nguồn tác giả sai | 21 | 20 | 10 | 8 |
| Agent chấp nhận nội dung, chưa xét validator | 3 | 5 | 6 | 2 |
| Vừa qua validator vừa được agent chấp nhận | 0 | 1 | 0 | 2 |
| Trung vị thời gian mỗi request | 16,69 s | 20,99 s | 41,10 s | 47,87 s |

Các nhóm lỗi có thể trùng trong một output. Tỷ lệ qua validator nói về độ hợp lệ của response, không phải `passed=true` hoặc chất lượng truyện.

7B baseline thường dùng `Logline`, `Character`, tên tiêu chí rubric hoặc viết hoa `Main Conflict` thay tên phần thật. Riêng `Logline` sai hoa/thường xuất hiện ở 28/36 output cố định. Khóa enum loại nhóm lỗi này. Ngược lại, 3B vốn không sai tên phần trên tập này nhưng thường chọn khóa title rồi quote nơi khác; 7B chỉ còn một lượt quote draft sai trong biến thể khóa. **Tác dụng của hợp đồng phụ thuộc model**, chưa thể suy ra nên dùng cùng một cách biểu diễn cho mọi model.

Đối chiếu từng ca/seed: ở baseline, có 14 lượt chỉ 3B qua, hai lượt chỉ 7B qua và không lượt nào cả hai qua. Với khóa, năm lượt cả hai qua, 23 chỉ 7B qua, hai chỉ 3B qua, sáu cả hai bị chặn. Đây là số đếm ghép cặp, chưa phải kiểm định thống kê; các seed trên cùng ca không tạo thành các mẫu người dùng độc lập.

Chấm nội dung là đọc định tính bởi agent, không ẩn biến thể, chưa có người đọc độc lập. Ba trong sáu lượt baseline 7B được chấp nhận ở nhóm cố định là các ca craft cần đối chiếu; nếu bỏ các ca đó còn 3/36. Bỏ mọi ca đánh dấu cần đối chiếu không thay số lượt 7B vừa qua validator vừa được chấp nhận: baseline 0, khóa 2. Một phản hồi có phần hữu ích nhưng thêm nhận định sai ở mục khác vẫn có thể bị loại toàn phản hồi. Không dùng các điểm này như thước đo hiệu quả với người mới.

## Planning và critic sau planning

12 planner nhận cùng request giữa hai model. Mỗi model tự sinh plan; hai critic của cùng model nhận chung plan đó. Vì draft sinh ra khác nhau, nhóm critic này không phải phép so đầu vào giống hệt giữa 3B và 7B.

| Chỉ số | 3B baseline | 3B khóa | 7B baseline | 7B khóa |
| --- | ---: | ---: | ---: | ---: |
| Critic sau planning qua validator | 4/12 | 0/12 | 3/12 | 8/12 |
| Agent chấp nhận nội dung critic | 0/12 | 2/12 | 1/12 | 1/12 |
| Qua cả hai lớp | 0/12 | 0/12 | 0/12 | 0/12 |
| Trung vị critic sau planning | 35,77 s | 42,11 s | 65,96 s | 73,46 s |

Planner đạt schema 12/12 ở cả hai model. Agent chấp nhận toàn bộ yêu cầu ở **2/12 plan 3B và 1/12 plan 7B**. Với 7B, ba plan giữ được ý đồ chính nhưng hai trong số đó có tone mới bằng tiếng Anh ở ca Vietnamese; các plan còn lại có khóa học/điều kiện chứng chỉ tự thêm, sai giới hạn phòng hoặc biến trạng thái để sau thành nội dung truyện. Trung vị planner tăng từ 30,30 s lên 58,65 s.

Gộp cả hai nhóm, chỉ để mô tả mọi đầu ra đã thu:

| Trên 48 critic mỗi cột | 3B baseline | 3B khóa | 7B baseline | 7B khóa |
| --- | ---: | ---: | ---: | ---: |
| Qua validator | 18 | 7 | 5 | 36 |
| Agent chấp nhận nội dung | 3 | 7 | 7 | 3 |
| Qua cả hai lớp | 0 | 1 | 0 | 2 |
| Lỗi tên phần/khóa | 0 | 0 | 37 | 0 |
| Lỗi quote draft | 4 | 40 | 5 | 1 |
| Lỗi quote tác giả | 28 | 28 | 15 | 12 |
| Thiếu author_quote cho contradiction | 1 | 1 | 1 | 0 |
| Trung vị mọi critic | 20,06 s | 24,95 s | 49,34 s | 53,17 s |

Tổng thời gian critic 7B: 2.281,439 s baseline, 2.622,182 s khóa; prompt token lần lượt 126.420 / 147.447, token sinh 19.966 / 22.844. Với 3B các số tương ứng là 1.043,426 / 1.311,895 s; 126.855 / 148.026 prompt token và 19.635 / 24.308 token sinh. Tổng thời gian mọi lời gọi của lượt chính 7B là 5.615,526 s. Trên nhóm draft cố định, trung vị 7B chậm khoảng 2,3–2,5 lần 3B; không quy thành SLA hoặc chi phí API.

## Lỗi nào vẫn còn, và phần harness có thể cải tiến

- **Ý nghĩa vẫn sai khi bằng chứng hợp lệ:** `deferred-keeps-fact`, seed 42, khóa: cho rằng Lan làm mẫu hoặc giúp gỡ mũi đan thì không thể là người hướng dẫn. `plan-quiet-waiting`, seed 73, khóa: đề nghị người vắng là con trai đi công tác hai tháng và thêm bóng người trở về. Cả hai qua validator.
- **Kết quả đã xác nhận vẫn bị xóa:** plan Eli seed 42 đổi chứng chỉ đã trao tháng trước thành đang chờ nhận. Cả hai critic qua validator nhưng khen premise đó và đề nghị nhận chứng chỉ trong phim. Seed 73 giữ chứng chỉ đã trao nhưng tự đặt buổi dạy đầu tiên; seed 101 thêm stakes phải duy trì chứng chỉ. Tăng kích thước model chưa bảo vệ được dữ kiện trọng yếu trên bộ này.
- **Khóa riêng có lợi ích thật:** ca `duplicate-section-names` trỏ được Beat thứ nhất có ga tàu và đề nghị đưa về căn hộ. Nhưng các output còn báo lỗi sai ở kết cha đứng lại, cho thấy đúng khóa chưa bảo đảm đúng nhận định.
- **Phép chiếu làm mất thông tin trước critic:** `_characters_text()` nối protagonist/supporting characters thành `Mai Học viên` hoặc `Eli Sarah, Tom`, không giữ nhãn. Critic vì thế có output nói chưa rõ protagonist, đề nghị xóa tên phụ, hoặc đọc Mai là học viên. Logline vẫn chứa vai đúng nên chưa thể kết luận đây là nguyên nhân duy nhất. `Core idea` cũng được pipeline sao từ logline, rồi có critic chê hai trường lặp nhau. Đây là các giả thuyết có thể kiểm chứng bằng code/input, không cần gọi lại planner.
- **Ngôn ngữ chưa ổn định:** có reason/suggestion English hoặc Chinese trong ca Vietnamese; không chỉ là giữ nguyên quote nguồn English. Schema/validator hiện thử không kiểm ý nghĩa hoặc ngôn ngữ của câu mới.

## Giao thức và phạm vi

- Cùng 16 ca nhúng trong `configuration.cases` của bằng chứng 3B, ba seed 42/73/101, temperature 0,3, context 16.384, timeout 180 giây, không tự retry output model. 12 ca review × ba seed × hai hợp đồng = 72 critic; bốn ca plan × ba seed = 12 planner, mỗi plan chia cho hai critic = 24 critic. Tổng 108 lời gọi sinh output.
- Chỉ đổi model thực thi sang `qwen2.5:7b` Q4_K_M. Giữ profile request `qwen2.5:3b`, vì ứng dụng chọn prompt/context planner khác cho 3B. So sánh này không đo profile mặc định của 7B.
- 72 request trên draft cố định phải khớp hoàn toàn request 3B: system prompt, input, schema. 12 planner request cũng phải khớp. 24 critic sau planning nhận plan do 7B tự sinh, nên chỉ so ở tầng toàn luồng; không gọi đây là đầu vào critic giống hệt giữa hai model. Trong mỗi model, hai hợp đồng nhận cùng snapshot.
- Nguồn đối chiếu là commit `e5198db2f552d316cc1debfde813128e70af224f`. Trong lúc chạy, workspace nhận commit thay prompt, schema và validator critic. Guard dừng lượt đầu sau 26 output; cả 26 request được đối chiếu khớp 3B. Các tệp lịch sử được lấy từ Git, kiểm đủ 23 hash rồi tiếp tục ở thư mục tạm riêng. Không hoàn nguyên thay đổi workspace.
- Sau 42 output, Ollama mất kết nối. Lượt đó giữ nguyên trong file `-aborted.json`: 42 output, 30 critic lỗi transport, 12 planner lỗi transport, thiếu metadata cuối. Loại **toàn bộ** lượt gián đoạn khỏi so sánh chính, không chọn lại riêng output xấu. Khởi động Ollama localhost rồi chạy mới đủ bộ trên nguồn đóng băng. Không dùng `--resume` ở lượt chính hoàn chỉnh. Tổng cả tác vụ có 192 request attempt, 150 output sinh được; bảng thời gian chính không gộp chi phí lượt bị loại, toàn bộ attempt đó vẫn có trong raw riêng.
- Giữ nguyên bộ kỳ vọng, gồm cách xử lý checklist `plan-quiet-waiting` đã công bố ở báo cáo 3B: không áp tiền đề về mốc thời gian trong draft review riêng lên plan mới. Không đổi dữ liệu gửi model.
- Chấm định tính bởi Codex agent, không ẩn biến thể, đã đọc cả lượt gián đoạn; chưa có người đọc độc lập. Nếu raw output lượt chính trùng nguyên văn lượt gián đoạn thì giữ cùng lý do chấm. Quote/key sai được chấm kỹ thuật riêng; một ý đúng không bù cho chẩn đoán sai/cách sửa trái brief ở mục khác. Đề xuất tùy chọn vô hại nhưng dư có thể được chấp nhận. Không suy ra lợi ích với người dùng từ tỷ lệ này.
- Timing local có ảnh hưởng cache, tải máy và điều kiện dịch vụ; có kiểm thử backend chạy ở đầu lượt, chưa cô lập tải máy; ghi wall time từng request và thời gian từ đầu đến cuối riêng. Không coi đây là benchmark phần cứng hoặc SLA.

## Bằng chứng và kiểm thử

- [Raw request/output 7B](../../demo/evaluations/harness-reference-qwen7b-2026-10-22.json), [lý do chấm từng output và kiểm tra toàn vẹn](../../demo/evaluations/harness-reference-qwen7b-2026-10-22-review.json), [output ẩn tên biến thể](../../demo/evaluations/harness-reference-qwen7b-2026-10-22.blinded.json).
- [Lượt gián đoạn giữ nguyên output/lỗi transport](../../demo/evaluations/harness-reference-qwen7b-2026-10-22-aborted.json), [lý do chấm 42 output của lượt đó](../../demo/evaluations/harness-reference-qwen7b-2026-10-22-aborted-review.json).
- [Báo cáo 3B gốc](harness-reference-contract-2026-10-21.md), [fixture phát triển](../../demo/evaluations/harness-reference-cases.json), [runner](../../backend/scripts/compare_harness_references.py), [test runner](../../backend/tests/test_harness_reference_experiment.py).

Đã dựng lại 96 request critic, đối chiếu 72 request cố định và 12 request planner với 3B, replay 96 verdict validator và parse lại 12 output planner. Đủ 48 cặp cùng snapshot; 23 hash nguồn trong bản tạm không đổi; digest model đầu/cuối và digest cả hai model kiểm lại sau chạy đều giữ nguyên. Lượt chính không resume; 42 output đầu trùng nguyên văn lượt gián đoạn. Không ghi kho dự án/dataset hoặc sửa workflow/prompt đang phục vụ ứng dụng.

Trước khi workspace cập nhật, 267 test backend qua. Sau cập nhật, 235 test qua và một module test hợp đồng lịch sử được skip có lý do rõ; tám test trong module đó chạy riêng trên nguồn đóng băng đều qua. Ruff hai tệp Python qua. Guard runner trên runtime mới trả thông báo dùng nguồn lịch sử, không âm thầm chạy hợp đồng khác. Có cảnh báo deprecation Starlette sẵn có. Không có chấm người đọc độc lập, tập giữ riêng hoặc pilot trong lượt này.

Digest 7B Q4_K_M: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` (7,6B tham số). Digest 3B Q4_K_M: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` (3,1B). Template chat đọc từ Ollama trong lượt chính giống nhau; version được đọc là 0.23.0. `/api/show` không trả trường parameters cho cả hai; báo cáo 3B không có version server lịch sử, nên không khẳng định đã kiểm soát mọi mặc định provider giữa hai ngày.

## Hướng cải tiến tiếp theo

1. **Chốt baseline của runtime hiện tại trước khi đổi cấu hình sử dụng.** Workspace đã đổi prompt/schema/validator trong lúc thử. Lượt này cố ý giữ nguồn lịch sử để trả lời phép so 3B–7B. Chạy bộ review cố định trên hợp đồng mới như một thí nghiệm riêng; dùng cùng kỳ vọng nội dung, không coi validator ít ràng buộc hơn là chất lượng tốt hơn.
2. **Ưu tiên bước 2 để không mất bản đề xuất khi critic lỗi.** Mã hiện tại vẫn đợi evaluation trước khi trả `HarnessRun`. Lưu bản đề xuất sau planning thành công, giữ revision và chỉ nhận vào draft khi tác giả chọn; critic lỗi vẫn cho sửa và review lại riêng. Kiểm chứng bằng timeout/lỗi provider/lỗi output và tải lại dự án, không cần thêm lượt model tự sửa.
3. **Thử nhỏ phép chiếu plan trước khi xây schema/UI lớn.** `_characters_text()` nối protagonist và supporting characters không nhãn, tạo `Mai Học viên`; `Core idea` được sao từ logline rồi critic lại chê lặp. Dùng lại 12 raw plan đã sinh, giữ model, seed, hợp đồng và kiểm tra quote; thử thêm nhãn vai từ chính trường cấu trúc gốc, không thêm dữ kiện tác giả. Không gọi lại planner. Đo riêng lỗi đảo vai, báo mâu thuẫn sai và tổng thời gian. Xử lý trường Core idea lặp là một biến thể riêng để không trộn nguyên nhân.
4. **Sau đó thử nguồn tác giả và phạm vi đối chiếu hẹp.** Trên fixture, so cùng dữ kiện ở dạng nguyên văn với trạng thái rõ `confirmed/open/proposed`, giữ nguyên quote gốc. Dữ kiện vai trong idea không bị câu “để sau” của câu hỏi AI xóa. Thử critic chỉ đối chiếu dữ kiện trước khi đổi cách góp ý craft; mỗi lần đổi một yếu tố. Có cả draft đúng để đo báo lỗi sai và draft sai để đo bỏ sót. Không thêm vòng tự xác nhận hoặc nới quote để tăng số qua.
5. **Giữ khóa mục tiêu như một ứng viên kỹ thuật, chưa di trú toàn ứng dụng.** Nếu tiếp tục phục vụ 3B, thử mã ngắn có nghĩa thay tiền tố hash nhưng vẫn ràng buộc snapshot tại code; đây là giả thuyết cần thử, chưa phải bản sửa được chứng minh. Khi có cấu hình hứa hẹn, nhờ người đọc độc lập đối chiếu output ẩn tên, rồi dùng ca giữ riêng trước pilot người mới. Tập hiện tại đã dùng để phát triển nên không dùng làm bằng chứng tổng quát.

## Tái chạy trên nguồn lịch sử

Runtime hiện tại đã thay hợp đồng grounded critic. Runner lịch sử dừng với thông báo rõ nếu chạy trực tiếp trên hợp đồng mới; bộ test tương ứng chỉ chạy trên nguồn cũ. Không khôi phục các tệp runtime trong workspace để chạy benchmark. Tạo bản sao Git cục bộ tạm, checkout commit dưới đây, chép runner hiện tại và truyền bộ ca nhúng trong raw 3B. Dùng đường dẫn output mới.

```sh
repo="$PWD"
snapshot="$(mktemp -d /tmp/firstframe-harness.XXXXXX)"
git clone --shared --no-checkout "$repo" "$snapshot"
git -C "$snapshot" checkout --detach e5198db2f552d316cc1debfde813128e70af224f
mkdir -p "$snapshot/backend/scripts"
cp backend/scripts/compare_harness_references.py "$snapshot/backend/scripts/"
python3 - "$repo" "$snapshot" <<'PYCASES'
import json, sys
from pathlib import Path
repo, snapshot = map(Path, sys.argv[1:])
report = json.loads((repo / "demo/evaluations/harness-reference-qwen3b-2026-10-21.json").read_text())
(snapshot / "cases.json").write_text(json.dumps(report["configuration"]["cases"], ensure_ascii=False))
PYCASES
cd "$snapshot/backend"
PYTHONPATH=. "$repo/backend/.venv/bin/python" scripts/compare_harness_references.py \
  --model qwen2.5:7b --request-profile-model qwen2.5:3b \
  --cases "$snapshot/cases.json" --seeds 42 73 101 --timeout 180 \
  --output /tmp/harness-reference-qwen7b-new.json
```

Runner mới có thêm guard báo hợp đồng lịch sử đã bị bỏ, nên hash script của lần tái chạy sẽ khác script trong bằng chứng chính. Guard không đổi request trên commit nguồn phù hợp. Prompt, input và schema từng request được giữ nguyên đầy đủ để đối chiếu trực tiếp. `--resume` chỉ dùng với cùng source hash/cấu hình/model metadata, không tự thử lại output lỗi đã ghi.

## Sửa runner khi bàn giao bước 0–1

Runner kiểm hash nguồn trước mỗi cặp và sau mỗi output; model digest được đối
chiếu cuối lượt, response từ model khác bị từ chối. Nếu nguồn đổi/mất, model
digest đổi/mất hoặc response trả sai model, raw output đã nhận vẫn được lưu
nhưng report có trạng thái `invalid`, lệnh trả lỗi và không được resume. Không
gắn trạng thái `completed` cho lượt chạy vi phạm điều kiện cố định.

File `.blinded.json` được xuất lại từ raw report bằng nhãn hiển thị chung cho
hai biến thể; target sai dùng cùng một nhãn không khả dụng. Token khóa snapshot
trong các trường góp ý được thay bằng nhãn hiển thị, không dùng bản hiển thị
này để kiểm quote. Mã review và thứ tự được tạo ngẫu nhiên; `.review-key.json`
cùng tên gốc nối mã review với case/seed/biến thể. Chỉ gửi file blinded cho người
chấm; không gửi raw report hoặc bảng đối chiếu. Cách xuất này loại dấu vết khóa
kỹ thuật, không cam kết che mọi khác biệt văn phong giữa hai prompt.
Resume giữ nguyên cặp file review đã xuất. Cặp thiếu hoặc không khớp bị từ
chối ghi đè để không làm mất mã mà người đọc có thể đã dùng để chấm.

Hai file blinded 3B/7B đã được xuất lại; raw request/output, verdict, thời gian
và điểm chấm nội dung cũ giữ nguyên. Không gọi lại model để sửa runner; các
con số phía trên vẫn là bằng chứng của lượt chạy lịch sử. Bản sửa không đổi
workflow, prompt, rubric, schema runtime, roadmap hoặc kế hoạch sản phẩm.

Để chạy test hồi quy, dùng bản sao `e5198db` như trên rồi chép thêm test và
fixture hiện tại trước khi chạy; test không gọi model thật:

```sh
cp "$repo/backend/tests/test_harness_reference_experiment.py" "$snapshot/backend/tests/"
cp "$repo/demo/evaluations/harness-reference-cases.json" "$snapshot/demo/evaluations/"
cd "$snapshot/backend"
PYTHONPATH=. "$repo/backend/.venv/bin/python" -m pytest -q tests/test_harness_reference_experiment.py
```

Kiểm tra bản bàn giao: 26 test runner qua trên nguồn lịch sử `e5198db`; 235
test backend qua trên `dev` nền `fe07d11`, một module hợp đồng lịch sử được
skip đúng chủ đích. Ruff hai file Python qua. Đã kiểm lại 48 cặp snapshot và
hash request critic của mỗi bộ 3B/7B, cùng mapping của 96 review ID mỗi bộ.
Các file raw và chấm nội dung giữ nguyên byte; chỉ bản xuất ẩn biến thể và
bảng đối chiếu là dẫn xuất mới. Cảnh báo deprecation Starlette có sẵn.
