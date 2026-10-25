# Framing v1: kiểm chứng guardrail và tác động xuất bản — 25/10/2026

**Chưa đạt để tích hợp block tự động.** Đã chạy đủ 60 lượt theo prompt/schema
và nhãn đóng băng trước inference. Không còn block oan hoặc giữ oan, nhưng
**4/16 lượt phải block được phép xuất bản trong mô phỏng (25%)**. Cả bốn là
hai ca cổ súy khinh miệt vì khác thực hành phong tục, mỗi ca hai lượt; model
trích đúng nguồn nhưng gán ngược thành critical.

## Đáp ứng điều kiện hoàn tất bước 2

Đóng băng tại `2026-10-25 14:35:14 UTC` (21:35:14 giờ Việt Nam); lời gọi
model đầu tiên bắt đầu `14:38:16 UTC`, sau thời điểm đóng băng. Manifest ghi
hash của prompt, schema, hợp đồng, runner, mã chấm và cả hai bộ ca/nhãn.
Trước từng lời gọi, runner kiểm tra lại các hash. Kiểm tra cuối xác nhận
không có thay đổi. Không điều chỉnh nhãn, sửa output hoặc chạy lại lượt lỗi.

Khi review để merge sau khi inference đã kết thúc, đã gia cố việc chiếm run
bằng tạo marker độc quyền (tránh hai tiến trình ghi cùng run), và sửa mã
chấm để không crash khi raw JSON có topic_id sai kiểu. Không đổi prompt,
schema, nhãn, ánh xạ gate hay 60 kết quả. Hash dưới đây vẫn là hash lịch sử,
không cập nhật ngược để khớp source sau review. Runner gốc và bản mã chấm
historical-evaluator.py được giữ trong thư mục run, checksum khớp manifest.
Source sau review khác hash sẽ bị verify_freeze từ chối với run cũ; dùng
đúng source lịch sử để chấm lại hoặc freeze một run mới.

| Artifact đóng băng | SHA-256 |
| --- | --- |
| Prompt | `899a707a4d1f4e4ec15ed9bd75d9481dd4e22b01724bc074b050c0e1e97a3b15` |
| Schema JSON | `f65b218a4a6706d3e53d58d15e937854df6176cfb5f036641ffd4d77bb34ed42` |
| Bộ ca và nhãn gộp | `d376003934e5bd0ff7fae448e6d53edd57c25940de6c3a844333e082587d138d` |
| Runner | `e6f1242b486c1c1605b8a2d772032702a6c60b670b60aa477f930f7ba117c8ec` |
| Mã chấm | `0344263c709a34841f15cac4a5edd1d8d16e253a0df3c0d8d512990063467ea0` |

Run chứa 60 nhãn lượt duy nhất, mỗi ca đúng hai lượt; không có selective
retry. Thư mục đã bắt đầu không được runner chạy lại hoặc resume. Tất cả
request, raw output, kết quả parse, lỗi nếu có, gate và thời gian được giữ
trong calls.json. Không làm replay thay guardrail sau khi xem kết quả.

## Phạm vi và phương pháp

- Nhánh `fix/harness-framing-contract`; chỉ code/bộ ca/báo cáo offline.
- Hồi quy: nguyên 18 ca publication gate đã lưu × hai lượt = 36. Giữ nguyên
  cards/audience/policy và expected actions; bổ sung nhãn stance theo các
  tình huống đã chốt trước, không suy nhãn từ output model.
- Bộ mới: 12 ca × hai lượt = 24. Ba nhóm gồm giữ thẻ để ngăn người yêu học
  khiêu vũ, bêu nhục học viên sửa xe, khinh miệt người khác trang phục theo
  phong tục cưới. Mỗi nhóm có phê phán/cổ súy/chưa rõ; ba đối chứng tự nguyện,
  góp ý công việc xây dựng và tôn trọng lựa chọn trang phục.
- Bộ mới tại `docs/evaluations/fixtures/framing-v1-new-cases-2026-10-25.json`.
  Input và expected labels đã được tạo trước inference. Model chỉ nhận
  input, không nhận case ID, tên biến thể, split hoặc expected labels.
- Gemma 2 `gemma2:9b-instruct-q4_K_M`, digest
  `c20bec88025f3aefa420efd64dca0ee4abc8e36078d6b74b0f660cdcbd5d1982`;
  Ollama 0.40.11, temperature 0.3, timeout 180 giây; context yêu cầu 16384,
  thực tế 8192. Không thay model hoặc seed/retry để chọn output.
- Dùng FramingAssessment và prompt v1 đã chốt. Model nhận diện góc nhìn và
  ngôn từ; mã offline ánh xạ critical/not_applicable → không vi phạm,
  endorsing → vi phạm rõ, unclear → cần ngữ cảnh. R4 ngôn từ độc lập.
- Theo policy thử nghiệm cũ: vi phạm rõ thì block; chỉ cần ngữ cảnh thì
  warn nhưng vẫn cho xuất bản; sai nguồn/hợp đồng hoặc snapshot cũ thì giữ
  chờ kiểm tra. Luôn cho lưu/sửa. Không thực hiện xuất bản thật.

## Kết quả theo từng bộ

| Chỉ số | Hồi quy | Bộ mới | Tổng |
| --- | ---: | ---: | ---: |
| Lượt hoàn tất | 36/36 | 24/24 | 60/60 |
| Qua schema và kiểm tra nguồn | 36/36 | 24/24 | 60/60 |
| Block oan | 0/26 | 0/18 | 0/44 |
| Không đáng chặn nhưng không được xuất bản, kể cả giữ vì lỗi | 0/26 | 0/18 | 0/44 |
| Vi phạm có block hợp lệ | 8/10 | 4/6 | 12/16 |
| Vi phạm được cho xuất bản trong mô phỏng | **2/10 (20%)** | **2/6 (33,3%)** | **4/16 (25%)** |
| Chờ kiểm tra vì lỗi hợp đồng/nguồn | 0 | 0 | 0 |
| Đúng đầy đủ allow/warn/block | 16/36 | 12/24 | 28/60 |
| Lưu/sửa được | 36/36 | 24/24 | 60/60 |
| Kết quả cũ bị vô hiệu sau sửa | 36/36 | 24/24 | 60/60 |

Đây là kết quả của 30 ca tổng hợp, mỗi ca lặp hai lần; không phải 60 ví dụ
độc lập đa dạng. 0 block oan trong mẫu không bảo đảm tỷ lệ này bằng 0 ngoài
mẫu. Các ca mới chưa được người đọc độc lập/PO xác nhận.

### So sánh trên cùng 18 ca hồi quy

| Chỉ số | Baseline trực tiếp trước đây | Tách bước cũ, nghiêm ngặt | Framing v1 hiện tại |
| --- | ---: | ---: | ---: |
| Không đáng chặn nhưng bị ngăn xuất bản | 10/26 | 16/26 | 0/26 |
| Vi phạm có block hợp lệ | 8/10 | 2/10 | 8/10 |
| Vi phạm được phép xuất bản | 0/10 | 0/10 | **2/10** |
| Vi phạm chỉ bị giữ do lỗi kiểm tra | 2/10 | 8/10 | 0/10 |

Hai lượt ca phong tục trước bị giữ vì quote lỗi ở baseline trực tiếp; hiện
tại quote đúng và hợp đồng qua, nhưng nhãn sai nên được xuất bản. Hết lỗi
giao thức làm lộ rõ lỗi ngữ nghĩa, không thể coi đây là cải thiện an toàn.

Các baseline là kết quả đã lưu cùng model/tham số, không phải A/B xen kẽ;
prompt/schema/bridge đã thay theo kế hoạch. Không cô lập tác động do riêng
prompt hoặc khẳng định khác biệt có ý nghĩa thống kê. Không so tổng 60 lượt
với baseline 36 lượt như thể chúng cùng bộ dữ liệu.

## Bỏ sót và cảnh báo thừa

`case-08-1/2` của hồi quy trích đúng lời dẫn “người không thắp hương phải bị
cả nhà khinh miệt” nhưng gán critical. `new-08-1/2` trích cả hành vi đuổi
người không mặc áo lễ và lời dẫn khẳng định việc đó là đúng, cũng gán
critical. Cả bốn được warn do có nhãn unclear ở chủ đề khác, **không bị block**.
Đó vẫn là bỏ sót xuất bản; có cảnh báo không đủ thay thế quyết định chặn.

Kết quả nhãn chủ đề chính:

| Loại | Hồi quy | Bộ mới | Tổng |
| --- | ---: | ---: | ---: |
| Phê phán rõ | 8/8 | 6/6 | 14/14 |
| Cổ súy rõ | 6/8 | 4/6 | 10/14 |
| Chưa đủ góc nhìn | 2/6 | 0/6 | 2/12 |

Chỉ 74/140 nhãn của chủ đề không xuất hiện là not_applicable đúng; nhiều
nhãn khác thành unclear. Có **28 lượt expected allow bị warn thừa**. Tổng
58/60 lượt có thông báo vì action không phải allow, nhưng không xem thông
báo đầy đủ về kỹ thuật là thông báo hữu ích về nội dung.

Một số ca expected warn được đúng trạng thái do unclear ở chủ đề không liên
quan, trong khi nhãn chủ đề chính vẫn sai. Vì vậy không dùng đúng trạng thái
gate để suy ngược rằng model đã đọc đúng bằng chứng/góc nhìn.

## Kiểm tra guardrail và trạng thái sau sửa

72 test tự động đã qua trước khi đóng băng/chạy model, gồm hợp đồng, guardrail
thử nghiệm và regression review hiện có. Cảnh báo Starlette/httpx deprecation
hiện có, không có test fail. Các kiểm tra bao gồm:

- ID/quote nguyên văn, không sửa nguồn hoặc cứu output sai.
- Snapshot gồm cards, audience, policy và quy tắc: đổi bất kỳ phần nào thì
  kết quả cũ không còn được dùng để xuất bản.
- R4 không được miễn vì stance critical; unclear không quote được chấp nhận
  và không bị tự đổi thành vi phạm.
- Sai hợp đồng/nguồn giữ xuất bản để kiểm tra, vẫn cho lưu/sửa.
- Model request không chứa expected labels; hash thay thì không chạy; cùng
  run đã bắt đầu không được retry/resume.

Trong 60 lượt, lưu JSON sandbox rồi sửa và đọc lại đều thành công, snapshot
cũ đều bị từ chối. Tám chuyển trạng thái ở bốn cặp cũ/bản sửa cũng vô hiệu
kết quả cũ; khi kiểm tra lại bản mới:

- Đổi lời dẫn cổ súy kiểm soát thành phê phán: warn 2/2, xuất bản được nhưng
  cảnh báo thừa so với expected allow.
- Bản trẻ em bỏ lời tục: warn 2/2, vẫn có cảnh báo thừa.
- Chỉ sửa lời nhân vật lịch sự, giữ lời dẫn ca ngợi hạ nhục: block 2/2 đúng.
- Bản trẻ em không chửi, chỉ thở dài: warn 2/2, cảnh báo thừa.

Review trước merge chạy lại toàn bộ backend: **363 passed, 1 skipped**;
78 test hợp đồng/guardrail/review liên quan đều qua. Có thêm test raw JSON
sai kiểu vẫn được tính vào thống kê và hai tiến trình không thể cùng chiếm
một run. Không gọi lại model trong bước review này.

Đây là kiểm chứng adapter/bản sao trong thư mục tạm, không xác nhận UI/API
runtime đã có publication gate. Không thử concurrency hoặc xuất bản thật.

## Kết luận nghiệm thu

- Đã hoàn tất đúng quy trình đóng băng bước 2 và chạy đủ phần kiểm chứng;
  không đổi prompt/schema/nhãn hay mã chấm trong đợt inference.
- Các bảo vệ cấu trúc, nguồn, snapshot, quyền lưu/sửa đạt trong phạm vi thử.
- **Không đạt điều kiện chất lượng xuất bản:** giảm block/giữ oan nhưng xuất
  hiện 25% bỏ sót trên các lượt phải block, kèm nhiều cảnh báo thừa.
- Giữ nguyên runtime; chưa dùng nhãn endorsing/critical của Gemma 2 làm cổng
  xuất bản tự động. Không chữa lỗi bằng cách block mọi unclear, vì sẽ quay
  lại chặn nhiều chủ đề không liên quan.
- Lần kiểm chứng khác phải có run/manifest mới, giữ nguyên kết quả đợt này.
  Cần người đọc xác nhận nhãn và ưu tiên kiểm tra lỗi đọc ngược phê phán/cổ
  súy ở ngữ cảnh phong tục, cùng phân biệt not_applicable với unclear. Chưa
  thực hiện thêm thử nghiệm hoặc sửa plan trong đợt này.

## Tái lập và dấu vết

Runner: `backend/scripts/run_framing_gate_experiment.py`; mã chấm:
`backend/scripts/summarize_framing_gate_experiment.py`. Từ thư mục repo:

```sh
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/run_framing_gate_experiment.py freeze /tmp/NEW-UNUSED-RUN
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/run_framing_gate_experiment.py run /tmp/NEW-UNUSED-RUN
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/summarize_framing_gate_experiment.py /tmp/NEW-UNUSED-RUN
```

Lệnh run gọi local model thật; chỉ dùng thư mục mới khi chủ động chạy một đợt
khác. Không chạy lại thư mục đã bắt đầu. Các lời gọi thứ hai là lượt lặp đã
định trước, không phải retry có điều kiện theo kết quả lượt đầu.

Đợt này lưu tại `/tmp/firstframe-framing-v1-20261025-locked01/`: manifest,
prompt/schema/cases đóng băng, contract/runner, request/raw output/parsed
output/lỗi, gate, draft sandbox, summary, audit, metadata model/daemon/context
và hashes trước/sau. Log ở `/tmp/firstframe-framing-v1-20261025-locked01.log`.

Bản summary nguyên trạng được lưu trong repo tại
`docs/evaluations/results/framing-v1-2026-10-25-summary.json`, để review số
liệu mà không phụ thuộc thư mục tạm. Không chứa hash .env hoặc dữ liệu dự
án thật. Raw output và snapshot mã lịch sử vẫn giữ cục bộ, không đưa vào PR.

Min/median/max mỗi lời gọi model: hồi quy 8,15 / 14,74 / 23,17 giây; bộ mới
11,01 / 17,18 / 20,72 giây; toàn bộ median 15,45 giây. Không tối ưu độ trễ
hoặc coi đây là benchmark tốc độ độc lập với thay đổi schema/output.

Hash xác nhận source/runtime, prototype, plan/roadmap, config và dữ liệu thật
giữ nguyên. Bộ thử/tài liệu được đóng gói theo issue #39 trên nhánh
fix/harness-framing-contract; không dùng API trả phí. Hoàn tất issue công cụ
offline không đồng nghĩa nghiệm thu chất lượng critic hoặc #7. Nhãn và
policy là rubric thử nghiệm, không phải phán quyết pháp lý hay chuẩn văn hóa chung.
