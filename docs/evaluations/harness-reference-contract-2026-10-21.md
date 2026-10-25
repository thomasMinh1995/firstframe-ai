# So sánh hợp đồng tham chiếu harness trên Qwen 3B

**Quyết định: giữ nguyên mẫu khóa gắn hash trong runner, chưa đưa vào runtime.**
Trên Qwen 2.5 3B và bộ phát triển này, số lượt qua validator giảm từ 18/48 xuống
7/48. Khóa riêng phân biệt được mục trùng tên, nhưng model thường chọn khóa
`title` rồi trích nội dung từ nơi khác. Đây là kết quả của cách biểu diễn khóa
được thử, không chứng minh mọi hợp đồng dùng ID đều kém hơn tên phần.

## Kết quả so sánh

Chạy từ 22:53:06 đến 23:38:33 ngày 21/10/2026, giờ Việt Nam; 45 phút 27 giây.
Đủ 108 lời gọi sinh output: 12 planning dùng chung và 96 critic. Model và hash
23 tệp nguồn giữ nguyên; 48 cặp nhận cùng snapshot. Toàn bộ 96 request được
dựng lại và kết quả validator được replay thành công sau chạy, không gọi lại model.

| Trên 48 lượt critic mỗi biến thể | Baseline | Khóa mục tiêu |
| --- | ---: | ---: |
| Qua schema | 48/48 | 48/48 |
| Qua validator nguồn và trích dẫn | 18/48 (37,5%) | 7/48 (14,6%) |
| Có quote draft sai vị trí hoặc không tồn tại | 4/48 | 40/48 |
| Có quote nguồn tác giả không tồn tại | 28/48 | 28/48 |
| Thiếu quote tác giả cho contradiction | 1/48 | 1/48 |
| Nội dung được agent chấp nhận, chưa xét validator | 3/48 | 7/48 |
| Vừa qua validator vừa được agent chấp nhận | 0/48 | 1/48 |

Không có lượt sai tên phần/khóa trong cả hai biến thể; đây chưa phải lỗi chính
của baseline 3B trên tập này. Các nhóm lỗi có thể trùng trong một output.
38/48 output candidate có strength dùng khóa `title` nhưng quote không thuộc
title; ở 22 lượt, quote đó nằm ở một trường draft khác. Schema chọn được một
khóa hợp lệ nhưng chưa giải quyết được việc gắn bằng chứng vào đúng trường.

Chấm nội dung là đánh giá định tính không ẩn biến thể của agent, chưa có người
đọc độc lập. Một phản hồi có đoạn đúng nhưng thêm chẩn đoán sai hoặc cách sửa
trái ý đồ vẫn có thể bị loại toàn phản hồi. Các con số này là dấu hiệu để đọc
lại output, không phải thước đo hiệu quả với người dùng hay điểm chất lượng
khách quan. File chấm ghi lý do cho đủ 96 critic và 12 plan.

| Nhóm phép thử | Baseline qua validator | Khóa mục tiêu qua validator |
| --- | ---: | ---: |
| Review draft cố định | 14/36 | 7/36 |
| Critic sau planning | 4/12 | 0/12 |

Planning đạt schema 12/12; agent chấp nhận nội dung 2/12 theo tiêu chí giữ nguồn
và phạm vi. Các plan được dùng chung, không phải hai tập độc lập để so chất lượng
planner. Chưa có phép thử người dùng hoàn thành một vòng sửa.

### Thời gian quan sát

| Trung vị wall time | Baseline | Khóa mục tiêu |
| --- | ---: | ---: |
| Review draft cố định | 16,69 s | 20,99 s |
| Critic sau planning | 35,77 s | 42,11 s |
| Mọi critic | 20,06 s | 24,95 s |

Planning dùng chung có trung vị 30,30 s. Tổng thời gian critic là 1.043,426 s
cho baseline và 1.311,895 s cho candidate. Candidate nhận 148.026 token prompt
và sinh 24.308 token; baseline lần lượt là 126.855 và 19.635. Không quy thời gian
local thành chi phí API; các số này không phải SLA hoặc benchmark phần cứng.

### Những ca cần đọc

- `duplicate-section-names`, seed 73: candidate trỏ đúng Beat thứ nhất có ga tàu
  và đề nghị đưa về căn hộ. Sau đó nó vẫn bịa nhu cầu kịch tính; seed 101 còn
  trỏ đúng Beat thứ hai nhưng đề nghị thay cảnh trong nhà thành ga tàu. Khóa
  đúng và quote thật chưa chứng minh diễn giải hoặc cách sửa đúng.
- `current-letter-draft`, candidate seed 42: giữ đúng nhà, một diễn viên và
  không thêm sân bay, là lượt duy nhất qua cả hai lớp chấm. Seed 73 trích đúng
  câu “Tôi đã chọn không có cảnh sân bay.” rồi đề nghị thêm sân bay hai lần.
- `deferred-keeps-fact`, baseline seed 42: quote thật về Lan làm mẫu mũi đan và
  nguồn thật về giữ vai hướng dẫn, nhưng kết luận hành động đó là đổi Lan thành
  học viên. Validator chấp nhận trong khi diễn giải sai.
- Các plan workshop giữ vai Mai và kết quả chứng chỉ chưa biết nhưng tự thêm
  khóa học nâng cao không có nhãn đề xuất. Nhóm quan hệ để sau biến việc tác
  giả chưa chọn quan hệ thành việc nhân vật không biết hoặc phải quyết định
  quan hệ của họ. Đây là vấn đề nguồn và trạng thái lựa chọn, không phải JSON.
- `plan-confirmed-outcome-en`, seed 42: planner bỏ chứng chỉ đã xác nhận của Eli,
  chuyển sang hành trình học viên Maria. Các seed khác thêm điều kiện duy trì
  chứng chỉ hoặc lẫn người mới với certified instructors. Critic không bảo vệ
  được dữ kiện nguồn một cách nhất quán.

Bằng chứng: [fixture](../../demo/evaluations/harness-reference-cases.json),
[raw requests và outputs](../../demo/evaluations/harness-reference-qwen3b-2026-10-21.json),
[chấm từng output và kiểm tra toàn vẹn](../../demo/evaluations/harness-reference-qwen3b-2026-10-21-review.json),
[bản ẩn tên biến thể để người đọc kiểm chứng](../../demo/evaluations/harness-reference-qwen3b-2026-10-21.blinded.json).

## Phạm vi triển khai

[Runner](../../backend/scripts/compare_harness_references.py) thực hiện bước 0
(đo baseline) và nguyên mẫu bước 1 (thử hợp đồng tham chiếu). Không
sửa workflow, prompt hay schema đang phục vụ ứng dụng, không mở kho dự án hoặc
dataset, không tự retry và không tải model mới.

Baseline lấy request từ service thực tế, gồm profile planner theo model và
critic theo ngôn ngữ. Candidate giữ trường `section` nhưng thay giá trị tên
phần tự do bằng enum khóa mục tiêu sinh từ snapshot. Khóa gồm tiền tố hash của
snapshot và vị trí nguồn; hai phần trùng tên có khóa khác nhau. Input candidate
giữ nguyên JSON draft và creator context, thêm ánh xạ khóa tới trường gốc;
chỉ dẫn tham chiếu được đổi tương ứng. Hướng dẫn sáng tác và rubric giữ nguyên.

Validator candidate dùng lại kiểm tra quote và nguồn tác giả của runtime với
các mục tiêu có tên riêng theo khóa. Không dùng fuzzy match hoặc đổi câu trích
để ép khớp. Schema và source hash riêng được lưu cho từng request và báo cáo.

## Thiết kế phép thử

- Model `qwen2.5:3b`, Q4_K_M; digest được chụp từ Ollama trước và sau chạy.
- Temperature 0,3; context 16.384; timeout 180 giây; seed 42, 73, 101.
- 12 ca review cố định, mỗi ca ba seed và hai biến thể: 72 lượt critic.
- Bốn ca plan, mỗi ca ba seed: 12 lượt planner. Mỗi plan được chia nguyên vẹn
  cho hai critic cùng seed: thêm 24 lượt critic. Tổng dự kiến 108 lời gọi.
- Thứ tự baseline/candidate đảo theo cả ca và seed. Chạy tuần tự, giữ cả output
  sai; không đổi hợp đồng hoặc prompt sau khi xem kết quả đầu tiên.
- Các ca là dữ liệu tổng hợp phát triển, gồm các ca cũ đã dùng tuning và các
  ca bổ sung trước lượt chạy. Đây không phải tập giữ riêng hoặc thử nghiệm
  người mới. Các ca plan đã cung cấp brief và hỏi đáp; không đo bước analyze.
- Payload timing ghi cả load, token prompt và token sinh nếu Ollama trả về.
  Wall time gồm overhead request; cache và tải máy chưa được kiểm soát hoàn toàn.

Digest model: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
Commit nền `e5198db2f552d316cc1debfde813128e70af224f`; hash tệp ghi cả runner
chưa commit tại thời điểm chạy. Không đổi prompt hoặc code nguồn trong lượt
chạy, không resume. Gói thay đổi gồm enum, mã có tiền tố hash, ánh xạ trong input
và chỉ dẫn tham chiếu; phép thử không tách riêng tác dụng từng thành phần.

Mỗi biến thể được chấm riêng theo schema, tham chiếu, quote draft và quote tác
giả. Một output có thể mắc nhiều lỗi; tổng các nhóm lỗi có thể lớn hơn số lượt
bị từ chối. Lỗi enum vẫn có thể giữ output để đọc nếu qua cấu trúc grounded
chung. Một lượt plan lỗi được ghi là thất bại đầu vào, không âm thầm sinh lại
hoặc tính critic chưa chạy là thành công.

Đánh giá nội dung là đọc định tính bởi agent theo `review_checks` đã ghi trong
fixture: giữ vai/kết quả/ý đồ, bắt mâu thuẫn trọng yếu khi có, tránh báo lỗi sai,
giữ giới hạn và ngôn ngữ, đề xuất tương thích. Quote hoặc khóa sai được chấm
kỹ thuật riêng; nhận xét vẫn có thể đúng ý nghĩa nhưng không dùng được. Kết quả
“dùng được” đòi cả runtime chấp nhận và nội dung chấp nhận. Đây chưa phải chấm
của người đọc độc lập; file đảo thứ tự, ẩn tên biến thể được xuất để hỗ trợ
người đọc kiểm chứng sau đó.

### Điều chỉnh checklist được ghi nhận

Ca `plan-quiet-waiting` đã kế thừa nhầm câu “Waiting already has a time cue” từ
draft review cố định, dù planning không nhận draft đó. Không áp dụng tiền đề
sai này cho ba plan hoặc critic của chúng. Fixture cho lần chạy sau đã được
sửa phần kỳ vọng; bản gốc vẫn nằm trong `configuration.cases` của raw report.
Đã xác nhận bằng assert rằng sửa checklist không đổi bất kỳ input model hoặc
snapshot của ba trial này. Không sửa prompt, schema, raw output hay verdict kỹ
thuật sau khi thấy kết quả. Việc điều chỉnh và grading bởi agent làm phần chấm
nội dung này phù hợp chẩn đoán phát triển, chưa phải benchmark giữ riêng.

## Chạy lại

**Cập nhật 22/10:** runtime đã thay hợp đồng critic sau lượt đo này. Để tái chạy
đúng nguồn lịch sử, dùng hướng dẫn tạo bản sao tạm trong
[báo cáo 3B–7B](harness-qwen3b-vs7b-2026-10-22.md#tái-chạy-trên-nguồn-lịch-sử).
Lệnh dưới đây áp dụng khi đang ở nguồn tương thích `e5198db`.

Từ thư mục `backend`:

```sh
PYTHONPATH=. .venv/bin/python scripts/compare_harness_references.py \
  --model qwen2.5:3b --seeds 42 73 101 \
  --output /tmp/harness-reference-comparison.json
```

Dùng đường dẫn mới; runner từ chối ghi đè báo cáo đã có. `--resume` chỉ chạy
các lời gọi chưa có bản ghi, giữ kết quả lỗi, kiểm tra lại cấu hình, model
metadata và source hash. Tiếp tục một lượt gián đoạn có thể thay đổi điều kiện
cache; trạng thái đó cần được ghi khi báo cáo thời gian. Đầu ra gồm report JSON
và file `.blinded.json` cùng tên gốc. Bản xuất mới dùng nhãn chung cho hai biến
thể, mã review ngẫu nhiên và file `.review-key.json` để người tổng hợp đối chiếu.
Chỉ gửi `.blinded.json` cho người chấm, giữ riêng raw report và bảng đối chiếu.
Kỳ vọng nội dung không được gửi cho model.
Nếu cần dùng `--resume` với bằng chứng lịch sử này, trích `configuration.cases`
từ raw report thành tệp riêng và truyền `--cases`; fixture hiện tại có metadata
checklist đã sửa nên runner sẽ từ chối coi nó là cùng cấu hình. Exit code 0 của
runner chỉ xác nhận hoàn thành thu thập, không xác nhận nghiệm thu chất lượng.

Hash prompt và input trong runner là SHA256 của biểu diễn JSON canonical của
giá trị chuỗi; hash source file tính trực tiếp trên bytes. Toàn bộ text prompt,
input, schema và raw output được lưu để đối chiếu độc lập với hash.

## Kiểm thử mã

266 test backend qua, gồm bảy test mới cho bảo toàn ngữ cảnh, phân biệt tên phần
trùng, quote sai vị trí, nguồn tác giả, snapshot khác, output lỗi và resume dùng
chung plan. Ruff các tệp Python mới qua. Có một cảnh báo deprecation Starlette
sẵn có. Fake provider nghiệm thu runner và validator, không chấm chất lượng model.

## Bước tiếp theo

1. Giữ nguyên mẫu trong công cụ đánh giá; chưa di trú API, dữ liệu dự án hoặc
   giao diện sang hợp đồng khóa có tiền tố hash này. Không nới kiểm tra quote
   để làm tăng số lượt được chấp nhận.
2. Nếu thử lại hợp đồng, dùng một biến thể nhỏ với mã ngắn mang nghĩa và nhãn
   nguồn rõ hơn; giữ ràng buộc snapshot ở code. Đo lại cả lỗi quote, nội dung
   và thời gian. Lỗi model ưu tiên giá trị enum đầu tiên là giả thuyết, chưa
   được chứng minh bằng phép thử tách riêng.
3. Dùng các lỗi nguồn/quan hệ đã thấy để kiểm chứng phép chiếu ngữ cảnh và
   trạng thái lựa chọn ở bước 3–4, hoặc một tác vụ đối chiếu hẹp hơn. So model
   khác trên cùng dữ liệu tổng hợp là thử nghiệm riêng; lượt này chưa đánh giá
   7B, OpenAI hoặc hiệu quả của nhiều lượt critic.
4. Nhờ người đọc độc lập kiểm chứng file ẩn tên biến thể, sau đó dùng tập giữ
   riêng và pilot trước khi kết luận về cải thiện khả năng viết của người mới.
