# Đổi model kiểm chứng #7: Qwen3 8B và Qwen 2.5 7B — 25/10/2026

**Qwen3 8B chưa đủ để thay model mặc định hoặc nghiệm thu #7.** Model đọc
phủ định tốt hơn ở ca hai Ending và sinh một plan giữ đúng điểm cắt. Tuy
nhiên, đề nghị sửa còn sai; nhiều kết quả không qua hợp đồng runtime và phần
lớn review vượt ngân sách chờ. Chưa đổi cấu hình runtime, prompt hay plan.

## Phép thử

- Đối chứng: [Qwen 2.5 7B](issue-7-qwen7b-2026-10-25.md), cùng code đang
  triển khai trên `codex/issue-7-feedback-targets` từ dev `60e5fa7`.
- Model thử: **qwen3:8b**, Q4_K_M, digest
  `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`.
  Ollama 0.23.0 trên localhost; không tải model mới hoặc dùng API trả phí.
- Chỉ đổi model trong process thử nghiệm. Giữ temperature **0.3**,
  `num_ctx=16384`, timeout **180 giây**; không ép seed, rút prompt hoặc
  đặt giới hạn output mới. Không truyền trường `think`; cả 23 phản hồi native
  của Qwen3 có trường thinking không rỗng, chỉ lưu số ký tự để đối chiếu.
- Sáu ca cố định × ba lượt độc lập, xen kẽ theo vòng. **18/18 lượt khớp chính
  xác instructions, input_text và JSON schema với đối chứng**, không chỉ
  cùng tên ca. Source và fixture cũng được kiểm tra hash.
- Một luồng qua API thực bằng FastAPI TestClient: analyze → plan kèm critic
  → bản sửa vi phạm → review → bản sửa trở về ý đồ → review. Dùng lại cùng
  brief/yêu cầu tác giả, nhưng câu hỏi và draft do mỗi model sinh khác nhau;
  không coi payload các bước sau trong luồng này là đối chứng byte-for-byte.
- Project SQLite và dataset tạm riêng; snapshot trước sửa của sáu ca là
  fixture, không giả làm kết quả model. Giữ toàn bộ lượt, kể cả lỗi và kết
  quả không thuận lợi. Không sửa prompt sau khi xem output.

## Kết quả kỹ thuật và độ trễ

| Chỉ số | Qwen 2.5 7B | Qwen3 8B |
| --- | ---: | ---: |
| Lượt gọi model / thao tác API | 23 / 22 | 23 / 22 |
| Output model qua JSON/schema của provider | 23/23 | 23/23 |
| Kết quả critic qua kiểm tra runtime | 21/21 | **14/21** |
| HTTP 200 | 22/22 | 16/22; gồm một plan đã giữ nháp nhưng critic lỗi |
| Review giữ nguyên dữ liệu tác giả | 20/20 | 20/20 |
| Làm rõ | 16,26 giây | 45,23 giây |
| Plan kèm critic | 73,23 giây | **230,35 giây** |
| Review: min / median / max | 13,94 / 18,44 / 21,95 giây | 45,69 / **67,99** / 121,54 giây |
| Review trong ngân sách ≤60 giây | 20/20 | **4/20** |
| Tổng API của luồng tạo/sửa | 119,72 giây | **423,86 giây** |

Không có timeout hoặc lỗi parse JSON ở Qwen3. **Cả bảy lỗi hợp đồng đều là
`aligned` nhưng `suggestion` không rỗng**, thường là lời “giữ nguyên” hoặc
thêm một thay đổi nhỏ. Backend từ chối đúng theo bảo vệ đã có; không bỏ lời
sửa hay đổi comparison âm thầm để ép kết quả qua.

Trong bảy lỗi có critic sau sinh plan và sáu review. Plan trả HTTP 200 do cơ
chế phục hồi: draft được lưu, generation ghi `critic_status=failed`, chưa có
feedback mới. Sáu review trả 502 và giữ nguyên feedback/source/revision trước
đó. **14/14 feedback mới được chấp nhận có snapshot/artifact hợp lệ khi mở
lại**. Không dùng số HTTP 200 để đồng nhất với critic thành công.

Ngân sách đã chốt là làm rõ ≤45 giây, plan kèm critic ≤120 giây, review
≤60 giây, toàn demo ≤5 phút. Qwen3 vượt nhẹ mốc làm rõ, vượt rõ mốc plan và
16/20 review. Tổng API đã là khoảng **7 phút 4 giây**, chưa tính thời gian
người dùng đọc/tự sửa, nên chưa đạt ngân sách demo. Các số liệu là lượt chạy
trên máy này; đã lưu metadata native/cache/load, chưa phải benchmark phần cứng.

## Chất lượng sáu ca

Đọc thủ công theo cùng yêu cầu #7, tách nhận xét/bước sửa khỏi việc đúng JSON.
Những phán đoán sáng tạo có thể chấp nhận được nhưng chưa chắc chắn được ghi
riêng là một phần, không ép thành nhãn đúng/sai để tạo điểm accuracy tổng.

| Ca | Qwen 2.5 7B | Qwen3 8B |
| --- | --- | --- |
| Kết mở, con gái không nhận chìa khóa | Hai mismatch sai, một aligned đúng | Hai aligned đọc đúng nhưng bị từ chối vì có suggestion; một uncertain không ép hòa giải nhưng còn suy diễn nguy cơ đã tha thứ |
| Giấu hộ chiếu trái ý đồ không kiểm soát | Phát hiện 3/3; hai đề nghị sửa phù hợp | Phát hiện 3/3; hai đề nghị phù hợp. Lượt còn lại vẫn cất hộ chiếu vào túi, đổi lý do thành tặng quà |
| Lá thư chưa mở | Hai mismatch sai, một aligned đúng | Vẫn hai mismatch sai: một đòi thư đã mở, một tự suy chỉ cha được đặt thư. Lượt aligned bị từ chối vì có suggestion |
| Quan hệ để quyết định sau | Ba mismatch không có đủ căn cứ từ lựa chọn để mở | Một uncertain/gợi ý liên kết không gian có giới hạn; hai aligned lại gán giới hạn không có trong input và bị từ chối vì suggestion |
| Hai phần cùng tên Ending, phần thứ hai chốt tha thứ | 0/3 diễn giải đúng phủ định | **3/3 chỉ đúng phần và đọc đúng phủ định**. Bước sửa vẫn có lỗi: một lượt sao lại nguyên văn card bên cạnh; một lượt đề nghị thể hiện tha thứ bằng cử chỉ, có thể vẫn chốt hòa giải |
| Lời nhân vật chứa chỉ dẫn viết screenplay tiếng Anh | Giữ JSON/tiếng Việt 3/3 nhưng góp ý không có đủ căn cứ | Cũng giữ JSON/tiếng Việt và không viết screenplay 3/3, nhưng cả ba coi lời trích như vi phạm quy tắc làm việc với AI rồi đề nghị đổi nội dung truyện |

Ở ca để sau, cụm “chỉ cử chỉ, không tranh cãi” **không có trong idea,
constraints hoặc answer của ca**, nhưng xuất hiện trong nhận xét hai lần.
Prompt có ví dụ với giới hạn tương ứng. Đây là dấu hiệu lẫn ví dụ hướng dẫn
vào nguồn tác giả; cần phép thử bỏ/đổi ví dụ để kết luận nguyên nhân, không
quy mọi lỗi cho kích thước model.

Ở ca hai Ending, ID đúng giờ đi cùng diễn giải đúng phủ định, là cải thiện
rõ trong bộ ca nhỏ này. Tuy nhiên, “phát hiện đúng” và “đề nghị sửa phù hợp”
chưa cùng đạt: giữ kết mở về mặt câu chữ vẫn có thể lặp card hoặc ngầm chốt
tha thứ bằng hành động. Nguồn do server trích đúng chữ không chứng minh mọi
suy luận và bước sửa của model đều đúng nghĩa.

## Luồng tạo plan và sửa hai vòng

- Mentor Qwen3 vẫn hỏi lại thời điểm cắt dù brief đã nêu rõ.
- Planner giữ cảnh dừng ở tay chạm bát cơm, không viết cả hai cùng ăn/nắm tay
  như lượt Qwen 2.5 7B. Đây mới là một lượt sinh plan, chưa đủ kết luận độ ổn định.
- Critic nhận ra điểm cắt phù hợp nhưng trả aligned kèm đề nghị sửa, bị từ
  chối. Cơ chế phục hồi giữ được nháp và trạng thái critic lỗi.
- Khi thay Ending bằng hét lên và bỏ khỏi nhà, critic chọn card Middle về
  tay chạm bát cơm rồi lại trả aligned kèm đề nghị sửa. Không phát hiện vi
  phạm rõ, review trả 502; draft tác giả vẫn được giữ.
- Khi sửa trở về đặt tay lên bát cơm và cắt trước quyết định ăn cùng mẹ,
  critic không ép ăn cùng nhau. Nó vẫn gọi câu chỉ dẫn điểm cắt là vượt
  giới hạn cử chỉ và yêu cầu lược câu đó; căn cứ chưa thuyết phục, dù đề nghị
  lần này giữ được kết mở hơn lượt Qwen 2.5 7B.

Sau critic ban đầu lỗi, `feedback_source` trống nên review trong luồng này
không có `focus_card_ids`; các card vẫn có trong input. Cần kiểm chứng riêng
việc định phạm vi review sau phục hồi bằng snapshot trước sửa đáng tin.
Không dùng khác biệt này để kết luận mọi lỗi trong luồng chỉ do model;
sáu ca cố định có focus vẫn cho thấy lỗi độc lập về hợp đồng và ngữ nghĩa.

## Bước kiểm chứng tiếp theo

1. **Chưa thay model mặc định.** Giữ cả hai model làm đối chứng; chưa có
   bằng chứng để nghiệm thu #7 hoặc chuyển sang H1–H8.
2. Với Qwen3, có thể thử riêng `think=false` trên đúng bộ ca để kiểm tra đổi
   độ trễ/tuân thủ hợp đồng có làm mất cải thiện ở ca phủ định không. Đây sẽ
   là một biến thể mới, không gộp vào lượt chỉ đổi model này. [Ollama mô tả
   trường điều khiển thinking](https://docs.ollama.com/capabilities/thinking).
   Chưa chạy biến thể đó; chưa thể nói thinking là nguyên nhân duy nhất của
   độ trễ hoặc rằng tắt thinking sẽ giữ chất lượng.
3. Kiểm chứng prompt/hợp đồng: aligned không có đề nghị sửa; tách ví dụ khỏi
   nguồn tác giả; phân biệt lời nhân vật và quy tắc phản hồi; kiểm tra từng
   bước sửa có còn giữ hành vi cấm, lặp card hoặc chốt điều cố ý để mở không.
4. Đối chiếu đường phục hồi critic lỗi và phạm vi review trước khi chạy lại
   luồng tạo/sửa. Sau khi đủ bằng chứng kỹ thuật/chất lượng mới pilot và nhờ
   người đọc độc lập theo #7.

Không sửa runtime/domain/prompt, cấu hình, plan, roadmap, prototype hay dữ
liệu thật. Hash trước/sau đều khớp; model mặc định vẫn là Qwen 2.5 7B. Chưa
commit/tạo PR; chưa chạy pilot hoặc nghiệm thu PO.

## Dấu vết để chạy lại/đối chiếu

Draft, request/output, source hash, model digest, dataset, runner và chấm đọc
thủ công giữ ngoài repo tại:

`/var/folders/5q/2y5tf10x3pg8jm8d6_mkf80h0000gn/T/firstframe-issue7-real-qwen3-8b-rqgvl9zh/`

Các tệp chính: `manifest.json`, `calls.json`, `results.json`,
`contract-comparison.json`, `manual-review.json`, `summary.json`, `checks.json`,
`run.py`, `compare.py`. Đối chứng cũ giữ nguyên thư mục đã ghi trong báo cáo
Qwen 2.5 7B; không ghi đè output hoặc chọn lại các lượt để so sánh.
