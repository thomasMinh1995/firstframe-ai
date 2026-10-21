# Đánh giá critic Qwen 2.5 3B — 21/10/2026

**Quyết định: chưa bật critic mới.** Các biến thể giảm tiếng Anh và nội dung lặp,
nhưng chưa giữ đúng ý tác giả hoặc ghép góp ý đáng tin cậy trên bộ nhiều kịch bản.
Ứng dụng vẫn dùng critic mặc định; OpenAI, các model khác, schema công khai và dữ
liệu dự án không thay đổi. Các lỗi của critic mặc định cũng còn nguyên, không được
coi là đã khắc phục bởi lượt thử nghiệm này.

## Dữ liệu và cách so sánh

- 6 kịch bản tiếng Việt tổng hợp: chờ đợi/kết mở; xin lỗi nhưng không ngăn con đi;
  giới hạn phòng trọ/một diễn viên; kết thúc chưa quyết định; hài hình ảnh không
  thoại; bản sửa chia tay trái ý định làm hòa/cùng giữ tiệm.
- Fixture ở `demo/evaluations/critic-cases-2026-10-21.jsonl` chỉ chứa request tổng
  hợp và yêu cầu mong đợi, **không phải workflow export hoặc output AI đã duyệt**.
  Trường `output: null` là có chủ ý; expected_behavior không được gửi tới model.
- Model `qwen2.5:3b`, digest quan sát `357c53fb659c…`; temperature 0.3,
  num_ctx 16.384, seed 42 và 73. Mỗi kịch bản có hai cặp trước/sau: 24 output.
- Baseline dùng prompt critic mặc định. Candidate v5 dùng prompt tập trung vào
  mâu thuẫn, tối đa một vấn đề, rubric ngắn đủ sáu tiêu chí và nhắc cú pháp mảng rỗng.
  Draft, ý tưởng, giới hạn, câu trả lời và schema được giữ đầy đủ. Prompt và cách
  trình bày rubric cùng thay đổi; kết quả không tách riêng tác dụng từng yếu tố.
- Thứ tự before/after đảo theo seed. Các pilot đã dùng các ca này để tuning;
  đây **không phải held-out benchmark**, không có đánh giá độc lập của tác giả.
- Raw output, input, effective prompt, schema, hash, seed và nhận xét từng ca nằm
  trong `demo/evaluations/qwen2.5-3b-critic-2026-10-21.json`. Báo cáo cũng giữ các
  pilot bị loại, kể cả output thất bại về nội dung. Không tự duyệt mẫu train/demo.

## Kết quả của so sánh đầy đủ

| Chỉ số trên 12 output mỗi bên | Trước | Candidate v5 |
| --- | ---: | ---: |
| JSON hợp lệ theo schema | 12/12 | 12/12 |
| Cặp đủ số lượng, cùng mục thật, có nội dung sau anchor | 6/12 | 6/12 |
| Không trúng danh sách marker tiếng Anh giới hạn | 1/12 | 12/12 |
| Tỷ lệ lặp cụm 4 từ, trung bình | 11,40% | 1,14% |
| Số từ nội dung, trung bình | 203 | 56,08 |

Kiểm tra cặp chỉ kiểm cấu trúc: hai mảng rỗng được tính hợp lệ kể cả khi model bỏ
sót lỗi. Cùng anchor chưa chứng minh gợi ý giải quyết đúng vấn đề. Chỉ số marker
không đo được tiếng Việt đúng: candidate `quiet-waiting`, seed 73 vẫn xen từ
“ambiguity” dù không trúng marker nào. Không dùng giảm độ dài/lặp làm điểm chất lượng.

| Ca | Candidate v5: kết quả cần lưu ý |
| --- | --- |
| Chờ đợi/kết mở | Seed 42 đúng hướng, hai mảng rỗng; seed 73 chê danh tính được cố ý để mở, ghép Middle với Beginning. |
| Xin lỗi/hộ chiếu | Seed 42 đề nghị giải thích hành động ngăn con thay vì hỏi sửa theo ý tác giả; seed 73 bỏ sót mâu thuẫn và có chuỗi góp ý mồ côi. |
| Giới hạn sản xuất | Cả hai seed không xử lý đúng việc quay ga tàu/đám đông trái giới hạn phòng trọ/một người. Seed 42 cho qua hoàn toàn. |
| Quyết định để sau | Cả hai có weakness chỉ chứa anchor. Seed 73 coi phương án chưa duyệt là lựa chọn đã chốt. |
| Hài không thoại | Seed 42 bịa bất khả thi khi sửa ô và đề nghị thêm người; seed 73 đòi lý do ngoài brief, không có gợi ý tương ứng. |
| Bản sửa trái ý định | Seed 42 trả anchor rỗng và lệch cặp. Seed 73 nhận ra chia tay trái ý cùng giữ tiệm, nhưng strengths vẫn khẳng định hai người đã đồng ý. |

Baseline cũng có lỗi nghiêm trọng. Ví dụ seed 73 ở ca hộ chiếu phát hiện đúng
mâu thuẫn chính, nhưng thêm góp ý quay bên ngoài trái giới hạn căn hộ; các ca khác
có strengths tiếng Anh hoặc tự ép diễn biến. Giữ baseline không phải chứng nhận
baseline đã đúng; candidate chưa vượt được ngưỡng thay thế.

## Các pilot bị loại

Ngoài v5, báo cáo giữ v1/v2 (dừng sớm sau khi thấy hồi quy), v3/v4 (hai seed trên
ca kết mở), v6 (JSON dễ đọc và prompt tiếng Việt trên ba ca), và diagnostic v7
với schema ghép lựa chọn–bằng chứng–gợi ý. Không trộn pilot vào 12 cặp chính.

V7 nhận ra một số mâu thuẫn nhưng vẫn chuyển gợi ý hộ chiếu sang Beginning trong
khi Middle có cờ mâu thuẫn và gợi ý rỗng. Ở ca phòng trọ, nó đề nghị đổi “ga tàu”
thành “sân ga”, vẫn trái giới hạn. Chỉ nhóm trường trong schema chưa giải quyết
được ý nghĩa của cặp góp ý. V7 không dùng schema công khai và không được triển khai.

## Chạy lại

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/compare_ollama_prompts.py \
  --dataset demo/evaluations/critic-cases-2026-10-21.jsonl \
  --output /tmp/critic-comparison-new.json \
  --seeds 42 73 --stages evaluation --experimental-critic
```

Chọn đường dẫn mới; báo cáo cũ không bị ghi đè. Flag experimental chỉ dùng trong
script; ứng dụng không có đường gọi candidate. Bỏ flag thì after dùng critic đang
hoạt động. Script lưu raw output cả khi JSON lỗi và ghi thêm feedback_pairs_valid
khi kiểm được output evaluation. Kiểm tra này không tự sửa/xóa output.

Thời gian chỉ để tham khảo: tải máy/cache không được kiểm soát, một số pilot có
request chồng nhau. Chưa thử lại toàn workflow hoặc benchmark model khác. Bước
kiểm chứng tiếp theo cần xác minh bằng chứng tác giả/draft và chất lượng gợi ý;
chưa có cơ sở đánh dấu các output này là dữ liệu train hoặc demo đã duyệt.
