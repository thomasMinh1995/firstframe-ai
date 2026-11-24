# Streaming Interfaces — bằng chứng SI-01–SI-03

- Ngày cập nhật: 02/11/2026. Theo dõi [issue #91](https://github.com/thomasMinh1995/firstframe-ai/issues/91), [plan](../plans/streaming-interfaces.md).
- Runtime: `867310f65fea783e672f6263633e3417e7d762ef` trên `dev`, sau [PR #92](https://github.com/thomasMinh1995/firstframe-ai/pull/92). SI-03 ở nhánh `fix/streaming-interfaces-si03`; các kết quả dưới đây được ghi trước khi stage/commit và push theo yêu cầu tiếp theo.
- Phạm vi: fixture/provider giả, SQLite/dataset và profile Chrome tạm. Không gọi AI thật, chạy QA workflow toàn bộ, deploy hoặc tự đóng issue.
- SI-03 chỉ thêm test/fixture và tài liệu; không sửa `backend/app` hoặc `frontend/app`.

## Kết quả bàn giao

**Đã kiểm chứng SI-03 trong phạm vi fixture được yêu cầu:** 13 nhóm ca HTTP/browser đạt, 42 test backend tập trung đạt, 10 bộ frontend đạt; strict TypeScript và build production cô lập đạt. Có ảnh trước/sau, trace event và thời gian đọc được. Đây là bằng chứng chức năng có kiểm soát, không xác nhận hiệu năng model thật, chất lượng nội dung hoặc nghiệm thu live/pilot #7/#22/#26.

SI-01/SI-02 đã được merge trong PR #92. Các kiểm tra trước đó gồm 50 test backend tập trung, 7 bộ frontend và hai ca HTTP desktop/mobile; artifacts lịch sử nằm ở `artifacts/streaming-interfaces-si01-si02-2026-11-02`. Các số này không cộng vào tổng test SI-03.

## Ma trận SI-03

| Nhóm trong plan | Bằng chứng đã chạy | Kết quả |
| --- | --- | --- |
| Phát tăng dần thật | `initial-success`, `regeneration-heartbeat`; critic bị barrier chặn, checkpoint đã lưu trước khi reader xuất hiện; test iterator so snapshot SQLite trước release | Đạt |
| Tương thích/rollback | Backend opt-in/default giữ số lần save/provider; frontend gặp stream cũ; `legacy-stream` bỏ query opt-in để nhận progress/result/error qua HTTP, hoàn tất mà không gửi lại | Đạt |
| Lỗi trước checkpoint | `planner-timeout`, `planner-json`; backend save conflict | Không tạo reader giả, không thêm generation khi planner/save lỗi |
| Lỗi sau checkpoint | `critic-timeout`, `critic-json` trên desktop/mobile | Reader và phần đã lưu còn nguyên; trạng thái không báo góp ý thành công |
| Mất kết nối/heartbeat | `truncated-stream` kết thúc HTTP ngay sau checkpoint rồi backend tiếp tục lưu; reload đọc lại bằng GET; `regeneration-heartbeat` và deterministic inactivity timer test | Không gửi lại planner, giữ preview khi chưa rõ terminal, heartbeat reset deadline |
| Đồng thời/kết quả muộn | `two-tabs`: tab B tự sửa ý tưởng và autosave khi tab A đang chờ critic; `late-unmounted`: rời sang dự án khác trước terminal; backend late-save/CAS tests | Tab B và màn mới không bị ghi đè; snapshot cũ còn đọc được; không gọi AI trùng |
| Parser | `streaming-checkpoint.cjs`, `progress.cjs`: UTF-8 chia chunk, heartbeat, nhiều event/chunk, terminal không newline, sai schema/ID/revision/source, duplicate đổi nội dung, thiếu terminal, terminal cũ/pending | Đạt; Promise chỉ resolve ở terminal hợp lệ |
| Quyền tác giả/buffer | Bản đầu và tạo lại; kiểm tra draft/feedback_source và lựa chọn PDF trước/sau; autosave/candidate-autosave với dirty buffer trong lúc polling; adoption acknowledgement | Preview không tự nhận/export; buffer mới được giữ, polling không ghi hoặc gọi provider |
| Browser/bàn phím | Chrome 1280×900 và 390×900, PageDown khi busy, focus, DOM identity, vị trí dòng đọc, không tràn ngang/JS error; aria-live polite và read-only markup | Đạt trong cấu hình fixture; không thay test VoiceOver/Safari thật |
| Draft run hiện có | `draft-2`, `draft-6`: plan/outline/cảnh đọc được trước run kết thúc, giữ phần/cảnh đang xem, không báo toàn bộ sẵn sàng sớm, nhận nháp mở đúng cảnh 2; `draft-2-scene_unknown` | Đạt; 2/6 cảnh và 2/6 góp ý đã lưu. Khi cảnh thứ hai không rõ kết quả, cảnh đầu còn nguyên và không tự retry |
| Hồi quy dùng chung/tour | Parser cho clarify/review/scene suggestions/sketch/screenplay proposal/review; progress, autosave, candidate polling, parent steps, follow, adoption, tour v3 | 10 bộ frontend và các test backend được chọn đạt |

Các ca HTTP thành công: `initial-success`, `regeneration-heartbeat`, `critic-timeout`, `critic-json`, `planner-timeout`, `planner-json`, `truncated-stream`, `legacy-stream`, `two-tabs`, `late-unmounted`, `draft-2`, `draft-6`, `draft-2-scene_unknown`.

## Số đo fixture

Các timestamp browser dùng cùng `performance.now()`. `readable-frame` được đánh dấu bằng requestAnimationFrame sau khi reader được gắn vào DOM. Các số dưới đây là một mẫu cho mỗi điều kiện, không phải benchmark hoặc phân vị; thời gian critic phụ thuộc gate được test chủ động nhả.

| Ca | Request → nội dung đọc được | Event checkpoint đến → frame đọc | Request → terminal |
| --- | ---: | ---: | ---: |
| Bản đầu, có kiểm tra bàn phím | 26,8 ms | 6,9 ms | 359,4 ms |
| Tạo lại + heartbeat fixture | 27,4 ms | 4,5 ms | 899,6 ms |
| Critic timeout giả | 26,9 ms | 5,4 ms | 118,9 ms |
| Critic JSON lỗi giả | 19,5 ms | 5,2 ms | 86,4 ms |
| Stream bị cắt sau checkpoint | 28,6 ms | 7,0 ms | Không có terminal — giữ trạng thái chưa rõ |

- DB commit trước phát event được xác minh riêng trên backend; cột event→frame không được gọi là thời gian DB→frame.
- Heartbeat fixture chèn dòng trống mỗi 100 ms và chỉ trong case đó deadline 45 giây phía browser được quy đổi thành 600 ms. Chờ ít nhất 8 heartbeat để chứng minh reset inactivity. Đây là kiểm tra tăng tốc hành vi; production vẫn giữ heartbeat 15 giây/deadline 45 giây, được kiểm tra riêng bằng unit test. Không kéo ngân sách lên từ số đo này.
- Với polling, mỗi checkpoint ghi một khoảng: DB commit nằm giữa lúc browser nhả gate và lúc browser xác nhận snapshot đã lưu. Sau đó chờ UI render nút đọc đúng scene/result revision. Tất cả mốc lấy trong cùng đồng hồ browser; không trừ timestamp server/browser.
- Draft 2 cảnh: cảnh 1 **[1.804,8; 1.902,8] ms**, cảnh 2 **[1.293,9; 1.395,9] ms** từ checkpoint tới sẵn sàng đọc.
- Draft 6 cảnh: các khoảng lần lượt **[1.818,3; 1.916,2]**, **[1.296,3; 1.419,6]**, **[1.307,7; 1.415,3]**, **[1.296,8; 1.393,9]**, **[1.291,1; 1.390,7]**, **[1.804,8; 1.899,7] ms**. Nội dung đã xem không tự chuyển theo checkpoint mới.
- Số đo này xác nhận polling cập nhật được với fixture. Chưa có bằng chứng người dùng bị cản bởi độ trễ này, nên giữ polling hiện tại; không suy số đo model thật từ FakeProvider.

## Số lần gọi giả và lỗi lần thử

- Mỗi ca plan có checkpoint: đúng **1 planning + 1 evaluation**; ca planner lỗi chỉ có **1 planning**. Hai tab, reload, recovery và phản hồi muộn không gửi lại planner.
- Draft 2 cảnh: **10 request giả duy nhất**, 2 cảnh/2 góp ý đã lưu. Draft 6 cảnh: **14 request giả duy nhất**, 6 cảnh/6 góp ý đã lưu. Provider result cache tái sử dụng các request review có input/schema giống nhau, nên số logical scene reviews không bằng số request gửi; không có key gửi lặp trong mỗi run.
- Cảnh thứ hai không rõ kết quả: **6 request giả duy nhất**, chỉ 2 lần viết cảnh; cảnh đầu còn đọc được, không có lượt viết lại ngầm.
- Artifacts giữ nguyên cả ba lần chạy: lượt đầu 12 nhóm ca đạt; lượt bổ sung có một lỗi driver khi đo ngay lúc PageDown còn cuộn; lượt kiểm tra sau đã chờ bàn phím dừng cuộn trước khi đo, giữ nguyên ngưỡng 3 px và không sửa runtime. Các ca mất nội dung/terminal hoặc lỗi góp ý do fault chủ động vẫn ghi fault và kết quả phục hồi, không loại để làm đẹp số liệu.
- Các số đo polling thử đầu chỉ chờ nhãn tiến độ, chưa chứng minh candidate content đã hydrate, nên được giữ làm lịch sử và không dùng ở bảng bàn giao. Số đo cuối chờ nút đọc đúng scene/result revision trước khi ghi.

Các file `results-*.json`, ảnh trước/sau/lỗi và logs ở `artifacts/streaming-interfaces-si03-2026-11-02` (local). Có 18 lần thực thi case, trong đó 17 đạt và 1 lỗi driver đã lưu; 13 biến thể chức năng có bằng chứng đạt. Chưa có mẫu model thật; không báo trung bình/p95 hoặc tuyên bố đã giảm thời gian chờ thực tế.

## Kiểm tra tập trung và tái chạy

- Backend: chọn stream/checkpoint/late planner/changed source/accept pending trong `test_plan_content_checkpoint.py`, `test_plan_recovery.py`, `test_projects.py`, `test_scene_sketches.py`: **37 passed, 71 deselected**. Chọn source conflict/unknown scene/candidate edits/received result restart/restart scene trong `test_draft_runs.py`: **5 passed, 20 deselected**.
- Frontend: `streaming-checkpoint.cjs`, `progress.cjs`, `autosave.cjs`, `candidate-autosave.cjs`, `draft-workflow-transitions.cjs`, `draft-workflow-actions.cjs`, `draft-parent-steps.cjs`, `draft-follow-reader.cjs`, `workspace-tools.cjs`, `onboarding.cjs`: **đạt**.
- Strict TypeScript compile Workspace/draft workflow/tour và dependencies: **đạt**. Production build từ source tracked trong thư mục riêng: **đạt**. Chỉ còn cảnh báo CSS autoprefixer `start` và Starlette/httpx deprecation đã có.
- HTTP fixture: chạy `python tests/streaming_acceptance_fixture.py` từ backend bằng môi trường test. Fixture tạo store/dataset tạm mới, chỉ có fake providers và chặn outbound HTTP; mở `127.0.0.1:8055`.
- Frontend riêng build với `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8055`, start `127.0.0.1:3055`. Chạy `node tests/streaming-acceptance.browser.cjs` với Playwright có sẵn qua NODE_PATH. `SI_SCREENSHOTS` chọn thư mục bằng chứng; `SI_BASE_HEAD` ghi baseline; `SI_CASES` chọn đúng ca cần kiểm tra lại. Browser chỉ cho phép hai cổng fixture.
- Không chạy script trên server/dự án thật. Đóng cả hai server fixture sau kiểm tra. SI-03 không có migration hay thay đổi runtime cần rollback.

## Giới hạn còn giữ nguyên

Chưa chạy AI/model thật, full workflow QA, toàn bộ browser engines, thiết bị mobile/IME/VoiceOver thật, deploy hoặc pilot người dùng. Snapshot/provider/context budgets production giữ nguyên; không dùng fixture để nghiệm thu thời gian model, tiêu chí live 5 phút hoặc chất lượng sáng tác. Issue #91 chưa tự đóng; chưa tạo PR hoặc merge SI-03.
