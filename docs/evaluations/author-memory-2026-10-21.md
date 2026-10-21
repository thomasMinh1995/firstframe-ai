# Giữ kỷ niệm, vai trò và kết quả tuyển dụng — 21/10/2026

**Chưa đạt nghiệm thu; PR cần giữ Draft.** Các thay đổi dưới đây làm rõ hợp đồng
của AI, nhưng kiểm thử thật với Ollama `qwen2.5:3b` vẫn có sai lệch nghiêm trọng.
Không coi 215 kiểm thử backend thành công là bằng chứng chất lượng sáng tác.
Không tự duyệt các output này cho demo hay huấn luyện.

## Phạm vi bản sửa

- Mentor giữ vai trò và hành động trong kỷ niệm, phân biệt sự kiện đã xảy ra với
  kết quả chưa biết; không hỏi lại điều tác giả đã quyết định.
- Planner giữ người học và người làm lab coach trên cùng nhân vật. Kỷ niệm phải
  thành hành động kể chuyện, không chỉ một từ khóa hoặc danh sách thành tích.
- Planner/critic phân biệt việc tiếp tục học, giúp người khác với kết quả do bên
  tuyển dụng quyết định. Tôn trọng trường hợp đã có lời mời và chủ động từ chối.
- Critic đọc toàn bộ bản hiện tại: Ending đã sửa không xóa lỗi còn ở Middle.
  Rubric không ép lựa chọn lớn hay kết quả tuyển dụng để đóng câu chuyện.
- Bỏ ba ví dụ truyện khỏi hai prompt critic: trong pilot, Qwen chép chuyện hộ
  chiếu và bát cơm vào góp ý cho “AI chông gai”. Các quy tắc, sáu tiêu chí và
  hợp đồng JSON vẫn giữ nguyên. Bỏ luôn ví dụ nhân quả mới thêm sau khi model
  dùng chính ví dụ đó để báo lỗi trên bản đã sửa đúng.

Chỉ thay prompt/rubric và tài liệu kiểm chứng. Không thay schema, cơ chế lưu,
UI, provider, hoặc tự sửa dữ liệu của tác giả. Thử nghiệm đặt ngữ cảnh tác giả
cuối đầu vào đã bị loại vì chưa chứng minh được lợi ích.

## Dữ liệu và phương pháp

Điểm xuất phát là bản kiểm thử “AI chông gai” trên dev `1249d67` với ý tưởng,
giới hạn nguyên văn của tác giả. Người kể đã pass đầu vào, trải qua các giai đoạn
học/thực tập và làm lab coach. Kết quả tuyển dụng cuối còn mở; học tiếp không phụ
thuộc kết quả đó. Các ca đối chứng là dữ liệu tổng hợp.

Kiểm tra thủ công các điều kiện sau, không chỉ tìm từ khóa:

1. Chính người kể hướng dẫn học viên; không chuyển vai trò sang một coach khác.
2. Hành động hướng dẫn/chia sẻ xuất hiện trong diễn biến.
3. Không cho nhân vật “quyết định pass”, không tạo lựa chọn học **hoặc** được tuyển.
4. Giữ mốc đã pass; không thay kết quả tuyển dụng còn mở bằng kỳ thi đầu vào.
5. Góp ý đúng bản: nhận ra lỗi ở Middle dù Ending đúng; không bịa lỗi ở bản đã sửa.
6. Giữ thuật ngữ Anh–Việt và ngôn ngữ diễn giải đã chọn.

Các pilot dùng cả endpoint tạo gộp cũ (`generate`) và luồng `plan` đang dùng trên
giao diện. Trong mẫu gốc không có câu hỏi/câu trả lời bổ sung, nên `plan` nhận
mảng answers rỗng. Không ghi đè dự án người dùng; các lượt gọi service lưu vào
thư mục dataset tạm. Đây không phải lần kiểm thử lại UI/lưu trữ hoặc nội dung chưa lưu.

Ứng dụng gọi Ollama thật, temperature 0.3, context 16.384. Lượt service không cố
định seed; replay planner dùng seed 42 và 73. Ca đã được dùng để điều chỉnh prompt,
không phải tập kiểm chứng độc lập. Không so sánh điểm nghệ thuật bằng rubric tự chấm.

## Bằng chứng

- `demo/evaluations/author-memory-pilots-2026-10-21.json`: các thử nghiệm bị loại,
  bao gồm input, prompt, output và metadata. Candidate 1/2 chưa có đầy đủ thay đổi
  cuối; e2e3 có thử nghiệm đổi thứ tự ngữ cảnh; memory-ui còn ba ví dụ critic cũ.
  memory-final bỏ ba ví dụ cũ nhưng còn ví dụ nhân quả mới; model tiếp tục
  bịa lỗi quyết định pass trên bản đã sửa, nên ví dụ mới cũng được bỏ ở bản cuối.
- Các fixture và kết quả cuối được liên kết bên dưới. `expected_behavior` nếu có
  là ghi chú nghiệm thu ngoài request, không đưa cho model.

Pilot `memory-ui` đã đưa lại vai trò người học kiêm lab coach trong Main character
và hành động hướng dẫn trong Middle. Nhưng Ending chuyển về kỳ thi đầu vào đã qua;
critic còn đề nghị bỏ hành động hướng dẫn. Với bản chỉ sửa Ending, góp ý tiếng Anh
đã nhận ra lỗi nhân quả tại Middle trong một lượt, còn tiếng Việt tiếp tục củng cố
“quyết định pass”. Với bản đã sửa đầy đủ, critic chép ví dụ hộ chiếu/bát cơm từ prompt.
Vì vậy không chọn riêng output tốt để tuyên bố đã sửa xong.

## Kết quả planner cuối (seed 42 và 73)

Raw request/output: [planner replay](../../demo/evaluations/author-memory-planner-2026-10-21.json).
Cả sáu output hợp lệ theo schema; điều này không đồng nghĩa đúng ý đồ.

| Ca | Kết quả thủ công |
| --- | --- |
| AI chông gai, 42 | Có chính người kể hướng dẫn/chia sẻ trong final_image. Nhưng lẫn thi đầu vào với tuyển dụng, gọi thực tập là giai đoạn 2 và tự thêm “Nhà máy sản xuất AI”. Chưa đạt. |
| AI chông gai, 73 | Có hành động hướng dẫn, nhưng dựng lựa chọn giữa học/build phase và đỗ đầu vào; Ending vẫn mơ đỗ đầu vào đã pass. Chưa đạt. |
| Đã có lời mời rồi từ chối, 42/73 | Cả hai giữ hành động vá áo với mẹ và gửi email từ chối; không biến lời mời đã có thành kết quả chờ. Đạt điều kiện đối chứng hẹp. Vẫn có chi tiết tự thêm; seed 73 ghi cast_size=1 dù có mẹ. |
| Bếp im lặng, 42/73 | Giữ máy tĩnh/căn bếp, không tiết lộ danh tính hay số phận người vắng mặt, không thêm coaching/tuyển dụng. Đạt điều kiện chống nhập dữ kiện của ca AI chông gai. Chưa đánh giá chất lượng nghệ thuật toàn bản. |

## Góp ý với prompt cuối (đã bỏ các ví dụ truyện)

Input/output thực và fixture replay: [các ca kiểm chứng](../../demo/evaluations/author-memory-cases-2026-10-21.jsonl).
Ba lượt review gọi service thật, không cố định seed. Cả ba trả JSON hợp lệ nhưng
**không đạt nghiệm thu nội dung**:

| Bản được review | Kết quả |
| --- | --- |
| Chỉ sửa Ending, tiếng Việt | Nói cần phân biệt hành động với kết quả, nhưng không đề xuất sửa lỗi pass. Thay vào đó tự tạo lựa chọn giữa học chuyên sâu và thực tập, vốn là các giai đoạn liên tiếp. |
| Cùng bản đó, tiếng Anh | Gợi ý “carefully considers whether to pass or continue learning and decides to pass”; tiếp tục lỗi cần sửa và đòi thêm kết quả tuyển dụng. |
| Bản đã sửa đầy đủ, tiếng Việt | Không còn chép chuyện hộ chiếu/bát cơm hoặc bịa câu quyết định pass trong lượt này. Nhưng vẫn chê kết quả tuyển dụng chưa rõ và đòi xác định thêm, trái kết mở. |

Tất cả vẫn cần tác giả kiểm tra. Loại bỏ ví dụ làm giảm một nguồn dữ kiện lẫn
trong lượt thử, không chứng minh đã chữa toàn bộ lỗi suy diễn hoặc hồi quy.

## Chạy lại

Từ thư mục repo có môi trường backend và Ollama đang chạy:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/compare_ollama_prompts.py \
  --dataset demo/evaluations/author-memory-cases-2026-10-21.jsonl \
  --output /tmp/author-memory-new-run.json \
  --seeds 42 73 --variants before
```

Trong công cụ này, `before` nghĩa là dùng nguyên request đã ghi trong fixture
(ở đây là prompt cuối của nhánh), **không phải baseline dev**. `after` nạp prompt
hiện tại từ repo. Chọn output mới để không ghi đè bằng chứng. Fixture đối chứng
planner có `output: null` do được dựng bằng provider giả để lấy request; kết quả
Ollama thật của chúng nằm trong file planner replay, không phải output giả.
Không dùng fixture/expected_behavior làm dữ liệu train đã duyệt.

## Kiểm thử kỹ thuật và giới hạn

- Backend: `python -m pytest -q` — **215 passed**, một cảnh báo phụ thuộc Starlette/httpx.
- `git diff --check`: đạt.
- Ruff toàn backend còn ba lỗi có sẵn trong `app/api/routes/health.py`,
  `app/core/__init__.py`, `app/core/harness/__init__.py`; các file này không thay đổi.
- Chưa kiểm thử OpenAI/model khác, hiệu năng, UI hay dữ liệu chưa lưu. Không thêm
  kiểm thử chỉ dò câu chữ prompt: chúng không chứng minh AI hiểu đúng vai trò/nhân quả.

Điều kiện trước khi chuyển PR sang ready: tất cả ca “AI chông gai” và đối chứng
phải giữ đúng sự kiện/ý đồ, góp ý VI/EN không tiếp tục khuyên “quyết định pass”,
bản đã sửa không bị ép bỏ coaching hoặc tiết lộ kết quả, và không nhập ví dụ khác
vào truyện. Cần kiểm chứng thêm phương án bảo toàn dữ kiện/đối chiếu bằng chứng;
chỉ tăng số câu cấm trong prompt hiện chưa đủ.
