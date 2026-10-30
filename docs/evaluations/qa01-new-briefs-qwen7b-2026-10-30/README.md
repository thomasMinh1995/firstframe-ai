# QA-01 — Brief mới, thoại tự do và diễn tiến nhiều cảnh

> Báo cáo lịch sử v24. Kết quả hiện tại nằm ở [review cuối PR #86](../qa01-new-briefs-final-review-2026-10-30/README.md); các lỗi/kết luận cũ dưới đây được giữ nguyên.

Ngày 30/10/2026. Nhánh `fix/qwen-new-brief-dialogue-continuity` từ `dev` tại `4bc8a38` (sau PR #85). **Chưa đạt nghiệm thu nội dung; PR giữ draft.** Không thay trạng thái QA-01 hay bật workflow card mặc định.

## Phạm vi và kết quả

[Cases](cases.json) được chốt trước baseline: năm brief synthetic mới, dự kiến 19 cảnh. Bốn ca yêu cầu hai lượt thoại mỗi cảnh, ca còn lại hoàn toàn im lặng. Các outline trong bộ này là fixture có kiểm soát, không phải bằng chứng planner tự tạo đúng. Mỗi cảnh dùng kết quả thực của các cảnh trước, không dùng đoạn continuity lý tưởng để che lỗi.

Ollama `qwen2.5:7b`, temperature 0.3, context 16384; [digest model](model-profile.json). Một call mỗi cảnh, không retry. Khi một cảnh thất bại, dừng các cảnh phụ thuộc của ca đó và tiếp tục ca độc lập tiếp theo.

| Brief | Số cảnh dự kiến | Kết quả nội dung cuối |
| --- | --- | --- |
| Mẹ–con / vé tàu | 3 | **Không đạt:** con nói đã cất vé ở cảnh 1, trước cảnh nhận/cất vé; lặp câu ở cảnh 2 |
| Chị–em / radio hỏng | 3 | **Không đạt:** cảnh 2 chép action vào thoại, bị từ chối; cảnh 3 chưa chạy sau lỗi |
| Mara–Owen / ô gấp / English | 3 | Đạt tiêu chí cố định: đúng ngôn ngữ, thứ tự người nói, ô chỉ đổi chủ một lần, cửa còn đóng; thoại vẫn chung chung |
| Bố–Minh / hộp kín | 4 | **Không đạt:** yêu cầu ngồi lại sau khi đã ngồi; cảnh cuối bố nói như con. Validator cuối chặn cách gọi sai đầu câu |
| An–Bình / chậu cây / không thoại | 6 | Đạt: giữ đủ sáu nhịp, An tưới đúng một lần; bình rỗng sau tưới, cây chưa xanh ngay |

[Report tại lúc chạy](final-v24/report.json): **18/19 cảnh được gửi**, 4/5 ca hoàn tất kỹ thuật/hợp đồng. Ca chị–em dừng ở cảnh 2 vì frame không hợp lệ. Không tính cảnh chưa chạy là pass.

[Revalidation mã cuối](source-verification.json): **3/5 ca** còn được chấp nhận sau bổ sung chặn vocative ở đầu câu. Câu của bố “Bố ơi, con chưa biết mở như thế nào.” ở cảnh 4 bị từ chối thay vì sửa lời và coi là đạt. [Đọc nội dung](content-review.json): chỉ **2/5 ca đạt tiêu chí nội dung**. Đây là đọc kết quả bởi agent, chưa phải người đọc độc lập/pilot.

Đối chiếu xác nhận input, instructions và schema của **26 call** (18 mới + 8 hồi quy) khớp mã cuối. Các frame được kiểm tra lại, không gọi model lần nữa. Báo cáo lúc chạy được giữ nguyên; bản đối chiếu ghi rõ hai frame bị validator cuối từ chối. Các thay đổi kiểm tra phủ định/để mở không thay input/schema của các ca dương tính này.

## Lỗi đã sửa trong hệ thống

- Yêu cầu thoại đặt trong brief/constraints từng bị bỏ qua vì writer chỉ xem `proposal.instructions`, còn auto-run gửi chuỗi rỗng. Nhận diện yêu cầu rõ **mỗi cảnh có hai lượt thoại và thứ tự hai vai** từ nguồn tác giả; schema giữ đúng vai/thứ tự, text vẫn do Qwen sinh tự do. Không lấy yêu cầu từ plan AI hoặc câu hỏi chưa được trả lời. Yêu cầu tùy chọn, phủ định, mơ hồ hoặc count/order ngoài phạm vi không bị ép thành hai câu hay âm thầm thành im lặng; dùng writer đầy đủ.
- Gửi ngôi xưng và cách gọi theo nguồn vào schema từng người nói; tách chúng khỏi nhãn tên. Giữ xưng hô riêng của tác giả. Kiểm tra một số sai lệch có căn cứ rõ: ngôi “tôi” trái ngôi gia đình đã chọn, vocative gia đình sai ở đầu/cuối câu, và câu thoại chép nguyên câu action. Sai thì giữ raw frame, trả lỗi, không thay từ hoặc gọi lại. Các guard này **không phải bộ hiểu nghĩa tổng quát**, không bắt được mọi cách nói sai vai hoặc hành động tương lai được diễn đạt lại.
- Thêm cảnh đã viết (gồm cả thoại), target và action các cảnh sau vào context để phân biệt đã xảy ra/hiện tại/chưa xảy ra. Các động tác đẩy/nghiêng không còn buộc rơi sang writer đầy đủ chỉ vì thiếu từ trong bộ nhận diện hành động. Nếu các action trước khớp chính xác phần brief đã dựng và chưa có lựa chọn tác giả, thoại AI ở cảnh trước không tự làm mất khả năng dùng nhịp tác giả ở cảnh tiếp theo. Giữ kiểm tra phiên bản, nguồn tác giả và action thay đổi.
- Không yêu cầu dịch lại các action đã được nhận diện chắc chắn là tiếng Anh. Trước đó Qwen từng dịch English sang chữ Trung Quốc/Nga; bổ sung từ chỉ hành động/liên từ phổ biến vào bộ nhận diện ngôn ngữ để không coi cảnh cuối là chưa rõ. Action Việt vẫn phải dịch khi chọn English; script-drift guard vẫn áp dụng.
- Thêm runner nhiều cảnh và kiểm tra count/order độc lập với đánh giá nội dung. Runner toàn luồng có ngân sách call chỉ định rõ cho chuỗi dài, mặc định giữ 14, tối đa 60 và vẫn chặn ở 600 giây. Không đổi runtime API, temperature, giới hạn cảnh, lưu trữ hay thêm dependency.

## Hồi quy và toàn luồng

- [Tám ca cũ](previous-eight-v24/report.json): **8/8 kỹ thuật và content gate đạt**, gồm thoại cha–con cũ, English dịch từ nguồn Việt và cảnh nối tiếp. Không dùng kết quả này thay cho bộ brief mới.
- [Toàn luồng thật](full-workflow-v24/report.json): brief → plan → outline → ba cảnh → ba review → chọn snapshot → PDF đều thành công về API; đúng ba cảnh, **14 calls**, khoảng 136 giây. Xuất PDF khi AI tắt, đúng bản đã chọn.
- [Đọc bản toàn luồng](full-workflow-v24/content-review.json): **không đạt nội dung**. Thiếu nhịp nhận/cất vé; cảnh cuối chỉ một câu của con gái. Outline AI chứa thoại có dấu nháy ở cảnh 2 và chỉ một nhân vật ở cảnh 3, khiến các cảnh rơi sang writer đầy đủ. Không coi technical pass hoặc `review_error=null` là review đã phát hiện đúng lỗi.
- Backend có hồi quy cho count/order, nguồn AI/author/legacy, phủ định/để mở/mâu thuẫn, xưng hô tùy chỉnh, action echo, raw output, không retry, nguồn không bị sửa, dịch English và checkpoint cũ. Backend local **816 passed, 1 skipped**; CI trên head PR kiểm tra lại backend và frontend typecheck/test/build.

## Điều kiện còn chặn merge / nghiệm thu

1. Thoại tự do phải giữ đúng người nói về mặt nội dung, không chỉ đúng label/schema; xử lý ca mẹ–con và bố–con ở bảng trên.
2. Không nhắc hành động tương lai như đã hoàn tất, không yêu cầu lặp động tác đã làm và không kể action trong thoại.
3. Chuỗi qua planner thật phải giữ đủ nhịp tác giả và yêu cầu thoại khi outline có quotes hoặc cast khác nhau; không chuyển profile giữa các cảnh rồi âm thầm bỏ sự kiện.
4. Chạy lại bộ brief mới sau sửa và đọc toàn bộ kết quả, giữ nguyên các ca lỗi hiện tại. Thiết bị thật, screen reader/IME và người đọc độc lập vẫn thuộc gate QA-01 riêng.

## Thử nghiệm và tái lập

[Archive](experiments.json.gz) giữ đủ **510 file của 5 lượt trước bản cuối**, gồm baseline, raw output, request/schema, proposal và lỗi. Đã giải nén đối chiếu byte trước khi gộp; [index](experiments-index.json) giữ report lịch sử. Một số guard được bổ sung trong các lượt thử; chỉ dùng capture/schema và đối chiếu mã cuối để kết luận, không coi mọi lượt thử là cùng một cấu hình runtime.

```sh
# Từ root repo, Ollama đã có qwen2.5:7b; output phải là thư mục mới.
backend/.venv/bin/python backend/scripts/check_multiscene_writing.py \
  --cases docs/evaluations/qa01-new-briefs-qwen7b-2026-10-30/cases.json \
  --output /tmp/firstframe-new-briefs

backend/.venv/bin/python backend/scripts/check_scene_writing.py \
  --all-cases --content-gate --output /tmp/firstframe-eight-regression

backend/.venv/bin/python backend/scripts/check_draft_release.py \
  --max-calls 24 \
  --brief-source docs/evaluations/qa01-new-briefs-qwen7b-2026-10-30/full-workflow-brief.json \
  --output /tmp/firstframe-three-scenes
```

## Tiếp nối review cuối PR #86

Trạng thái draft và lỗi 2/5 bên trên là bản v24 được giữ làm lịch sử. [Báo cáo cuối v25](../qa01-new-briefs-final-review-2026-10-30/README.md) ghi hai lượt 5/5, hồi quy và planner tới PDF; nêu rõ đánh đổi thoại phản hồi có cấu trúc thay cho việc coi lời tự do của Qwen là đã được kiểm chứng.
