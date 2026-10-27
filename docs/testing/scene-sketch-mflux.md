# Gói 4 — tích hợp ảnh MFLUX local

- Ngày: 27/10/2026. Nhánh: `feat/scene-staging-handoff`, từ dev sau PR #50.
- Phạm vi: một cảnh → một preview → chọn giữ/bỏ, cùng phần hướng dẫn/bàn giao văn bản đã làm trong nhánh này. Không sửa plan/roadmap/prototype, không đổi model văn bản hoặc tạo PR.
- **Kết luận:** luồng kỹ thuật tạo/lưu/xem/giữ/bỏ ảnh chạy được với MFLUX thật. **Ảnh thử chưa đạt nội dung để demo dàn cảnh đúng ý đồ**; Gói 4/M2 đầy đủ chưa được nghiệm thu.

## Ngân sách và lưu bền vững đã duyệt trước khi chạy

Tác giả đồng ý 2 lượt local, tối đa 180 giây/yêu cầu gồm khởi động/nạp model, 768×432, 9 bước, seed 42, 4-bit, low-RAM, MLX cache limit 2 GB, không LoRA/refiner/upscale, không API trả phí hoặc retry tự động. Sau khi cả hai lượt đầu lỗi cờ CLI trước khi sinh ảnh, tác giả duyệt riêng thêm 2 lượt cùng cảnh/prompt/tham số. Tổng cộng **4 yêu cầu: 2 lỗi adapter + 2 tạo ảnh thành công**, không xóa lỗi hay chọn lại mẫu đẹp.

Đã tạo venv riêng `backend/.data/image-runtime` (Python 3.12.13, MFLUX 0.23.0, MLX/MLX Metal 0.32.4, Pillow 12.3.0), pin package trong `backend/requirements-image.txt`. Đã sao chép cache sang `backend/.data/image-models`, kiểm tra không có symlink bị đứt. Runtime khoảng 1,1 GB, model/cache khoảng 5,5 GB; không còn phụ thuộc venv/cache trong `/private/tmp`. Không thay venv hoặc model văn bản. Chỉ thêm `SCENE_IMAGE_PROVIDER=mflux` vào cấu hình local đã bị Git bỏ qua; mẫu `.env.example` để trống, không tự bật cho máy khác.

Provider dùng đúng snapshot `b3a8f31115a11f2f9e2fa0bfbc8d78dcc3e6568b` của `filipstrand/Z-Image-Turbo-mflux-4bit`. Tiến trình gọi bằng argv, không shell; chỉ đọc model đã cài, bật `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` và tắt telemetry Hugging Face. Không có đường gọi image cloud hoặc fallback sang API trả phí.

Ảnh sản phẩm lưu ở `backend/.data/scene-images/<project UUID>/<asset UUID>.png`; metadata/snapshot/prompt/config/trạng thái nằm trong project SQLite. Thư mục ảnh lấy theo thư mục DB để DB QA riêng không đụng ảnh tác giả. Lượt thật này dùng DB tổng hợp riêng tại `backend/.data/scene-sketch-trial-adapter-v2-2026-10-27/`. Tất cả `.data/` được Git bỏ qua; không đưa weights, runtime, DB hoặc chất liệu tác giả vào repo.

## Hành vi và bảo vệ dữ liệu

- Endpoint riêng `POST /api/projects/{id}/scene-sketches[/stream]`, không ép ảnh vào `StructuredProvider`. Ghi request ID và snapshot trước khi chạy. Gửi lại cùng ID chỉ đọc trạng thái; khác cảnh/yêu cầu trả 409. Mất response dùng Kiểm tra ảnh đã lưu; không tự tạo lượt mới.
- Nguồn gồm đúng scene ID, snapshot dàn cảnh/story plan/ý đồ, các lựa chọn đã nhận vào cảnh và yêu cầu phác. Không dùng proposal/góp ý chưa nhận. Nguồn, provider/model/prompt/config do server gắn; client không được gửi URL/path/ảnh/source/selection map qua PUT.
- Một tiến trình ảnh local tại một thời điểm bằng khóa tệp liên tiến trình. Hết 180 giây thì dừng nhóm tiến trình và ghi lỗi. Tối đa 20 lượt lưu trong một dự án; vượt giới hạn vẫn tự viết/lưu/bàn giao text được. Không tạo hàng loạt.
- Chỉ PNG tĩnh 768×432, tối đa 8 MiB; kiểm tra decode/format/kích thước/nội dung rồi encode lại để bỏ metadata nhúng. Tệp có UUID do server cấp, ghi tệp tạm rồi đổi tên. JSON không có binary/base64. Serve ảnh kiểm tra membership trong đúng dự án, kiểm tra lại tệp, trả `image/png`, `nosniff`, `no-store`; không đọc path/URL model hoặc client đưa vào.
- Preview không thay cảnh hay ảnh đã giữ. Chọn giữ kiểm tra revision, trạng thái, toàn snapshot/khóa nguồn hiện tại và tệp còn đọc được, rồi mới đổi lựa chọn. Chọn ảnh mới không xóa tệp/lịch sử ảnh trước. Ảnh cũ được giữ để đọc và đánh dấu khi nguồn đổi; không được nhận lại như nguồn hiện tại. Đổi thứ tự/trùng tên không chuyển ảnh sang scene ID khác.
- Bỏ preview chỉ cập nhật quyết định ảnh; không tự lưu text đang sửa hoặc bỏ ảnh khác đang giữ. Bỏ ảnh đang giữ là thao tác riêng, gỡ lựa chọn đó và giữ lịch sử/tệp. Bỏ pending không hứa hủy inference ngay, nhưng kết quả muộn vẫn discarded. Không tự rebase nguồn.
- Kết quả muộn chỉ ghi mục ảnh trong transaction SQLite, không ghi đè text/nguồn/metadata lựa chọn của tác giả. Mỗi mutation có revision/CAS. Client cũ không gửi trường ảnh khi lưu vẫn giữ dữ liệu ảnh. Inspect khi có sửa chưa lưu không âm thầm ghi đè lựa chọn ảnh của cửa sổ khác.
- Tệp thiếu/lỗi, thiếu cấu hình, timeout hoặc ảnh sai vẫn cho sửa/lưu text và chuẩn bị bàn giao M3. Tải JSON chỉ chứa nội dung và tham chiếu ảnh; UI ghi rõ không backup binary. M3 viết kịch bản vẫn chưa triển khai.

## Kiểm thử kỹ thuật

| Kiểm tra | Kết quả |
| --- | --- |
| Toàn bộ backend sau sửa adapter | **419 passed, 1 skipped**; cảnh báo TestClient/httpx hiện có |
| `test_scene_sketches.py` | **16 passed**: preview/keep/discard, nguồn cũ/response muộn, pending bỏ rồi đến muộn, legacy save, request ID, khác dự án, không nhận URL/path/source/selection giả, byte/PNG/JPEG/SVG/kích thước/truncated, thiếu/lỗi tệp, disk/provider/timeout, quota, khóa tiến trình, offline args và kill timeout |
| Parser MFLUX thật | `scripts/check_scene_image_runtime.py` dùng đúng argv adapter qua parser và model-config validation; đạt, không nạp weights/sinh ảnh |
| Frontend production build/TypeScript | Đạt; có cảnh báo CSS `start` hiện có |
| Node contract/progress/onboarding | Đạt; field ảnh chỉ đọc, từ chối ID/URL giả, lựa chọn ảnh cửa sổ khác không bị coi là metadata AI để ghi đè; giữ tour sáu bước |
| Chrome `scene-sketch.browser.cjs` | Đạt với API/SQLite riêng và provider ảnh giả: tạo/giữ/bỏ, preview mới giữ ảnh cũ, chủ động thay, mất response không tăng lượt, reload, ID/order/nguồn cũ, timeout, bỏ ảnh giữ text chưa lưu, tệp thiếu không chặn bàn giao; 1280/390/320px |
| Chrome `scene-handoff.browser.cjs` | Đạt trên UI có ảnh tùy chọn: tour M1/M2, đường thủ công không AI, bàn giao G2/G3 chỉ lựa chọn đã lưu, mất mạng/409 giữ buffer, reload/order |
| Chrome M1 focus/dialogue | **4/4 và 2/2 đạt** ở desktop/mobile giả lập |
| Ảnh thật trong UI | Đã mở bằng API QA **chỉ đọc** từ DB thử, xác nhận ảnh 768×432 nạp được, thấy đúng trạng thái đang giữ/đã bỏ. Không chạy thêm model qua browser. [Ảnh chụp UI](../evaluations/scene-sketch-mflux-adapter-v2-2026-10-27/ui-real-preview.png) |
| `git diff --check` | Đạt |

Browser phát hiện một lỗi thực: `toggle` từ `<details>` con khi thu ảnh đã bỏ làm handler popover đóng cả form. Đã sửa handler chỉ nhận `event.target === event.currentTarget`; chạy lại trọn bộ ảnh trên fixture sạch đạt. Hai lượt browser lỗi trước sửa không được tính là đạt. Lệnh pip ban đầu không dùng được vì backend venv không có pip; cài Pillow qua uv thành công, không đổi runtime văn bản.

## Hai đợt model thật, giữ nguyên cả lỗi

Trước mỗi đợt đã đóng băng input/prompt/schema, service/route/runner hashes và tham số. Đợt adapter v2 dùng **nguyên byte input của đợt cũ**, chỉ sửa cách gọi CLI và dùng DB riêng. Có 1 cảnh tổng hợp tiếng Anh, 2 yêu cầu giống nhau để kiểm tra vòng đời, **không phải hai ca nội dung độc lập**. Chọn giữ trong runner là thao tác fixture kỹ thuật, không phải tác giả nghiệm thu ảnh.

| Đợt | Lượt | Kết quả | Thời gian API, gồm subprocess/nạp model/lưu ảnh |
| --- | --- | --- | --- |
| Đầu | 1 | 502 `ProviderRequestError`: CLI không nhận `--model-path`, chưa sinh ảnh | 5,658 giây |
| Đầu | 2 | Cùng lỗi CLI, chưa sinh ảnh | 0,771 giây |
| Adapter v2, đã được duyệt ngân sách bổ sung | 1 | 200 ready; chọn giữ, mở lại giữ đúng ảnh | **35,347 giây** |
| Adapter v2 | 2 | 200 ready; preview không thay ảnh thứ nhất, bỏ preview giữ nguyên lựa chọn cũ, mở lại đúng | **31,990 giây** |

Adapter dùng `--model <snapshot local> --base-model z-image-turbo`, đã đối chiếu với parser cài thực tế trước đợt v2. Hai PNG v2 cùng SHA-256, phù hợp việc cố định cùng prompt/seed/model. Máy không cô lập tải (có kiểm tra frontend/backend cùng đợt), không coi số này là SLA hay benchmark cold/warm tổng quát. Không đo lại peak memory trong tích hợp; con số memory ở lượt thử độc lập trước không được dùng như kết quả đợt này.

Đợt lỗi: [manifest](../evaluations/scene-sketch-mflux-2026-10-27/manifest.json), [toàn bộ kết quả và stderr](../evaluations/scene-sketch-mflux-2026-10-27/results.json). Mã nguồn đúng tại lúc chạy đã được sao chép vào `source/` trước khi sửa adapter; hash khớp manifest, không xóa/ghi đè kết quả.

Đợt v2: [manifest](../evaluations/scene-sketch-mflux-adapter-v2-2026-10-27/manifest.json), [input](../evaluations/scene-sketch-mflux-adapter-v2-2026-10-27/inputs.json), [kết quả](../evaluations/scene-sketch-mflux-adapter-v2-2026-10-27/results.json), [audit/hash](../evaluations/scene-sketch-mflux-adapter-v2-2026-10-27/audit.json), [ảnh thứ nhất](../evaluations/scene-sketch-mflux-adapter-v2-2026-10-27/results/image-1.png), [ảnh thứ hai](../evaluations/scene-sketch-mflux-adapter-v2-2026-10-27/results/image-2.png). Runner từ chối ghi đè bộ kết quả; lỗi được lưu trong metadata riêng, không retry.

## Đối chiếu nội dung ảnh và phần còn chặn

Ảnh v2 có hai người và nét chì, nhưng vẽ thành trang có tiêu đề, chữ/nhãn `time`, `characters`, `Shot` và nhiều chữ méo dù yêu cầu không chữ. Bố trí trông như cả hai ngồi quanh bàn, không đúng mẹ đứng bên cửa trái/con ngồi bên phải; phong thư kín và tuổi mẹ không được thể hiện rõ. **Không đạt các ràng buộc cảnh đã đóng băng**. Việc server xác nhận PNG/nguồn hoặc runner bấm giữ không chứng minh ảnh đúng ý đồ.

Ảnh có dấu hiệu biến cấu trúc nguồn JSON/tên trường thành bố cục tài liệu; đây là giả thuyết từ đối chiếu output, chưa kiểm chứng nhân quả. Không sửa prompt, chạy thêm seed hoặc chọn ảnh khác sau kết quả để gọi đợt này đạt. Bước kiểm chứng nhỏ tiếp theo có thể là đổi cách diễn đạt prompt thành mô tả thị giác liên tục thay vì đưa JSON thô; cần được chốt/đóng băng và duyệt ngân sách riêng trước khi thử. Chưa kiểm chứng cảnh tiếng Việt, nhiều cảnh, tính nhất quán nhân vật hoặc chất liệu tác giả.

MFLUX/provider và lưu trữ đã có đường tích hợp, nên điểm thiếu hiện tại không còn đơn thuần là “chưa có provider”. **Chất lượng ảnh/phù hợp cảnh còn chặn demo phần ảnh**; text M2 vẫn dùng được. Chưa nghiệm thu M2 đầy đủ, M3 thật, người dùng, screen reader/IME thiết bị thật, Windows hoặc tải production. Không đóng #7/#22/#26 và không hạ tiêu chí.

Về quyền tái sử dụng khi triển khai tiếp: [model card gốc](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo/raw/main/README.md) khai Apache-2.0, còn [card bản lượng tử hóa đang dùng](https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit/raw/main/README.md) khai `license: other`/Tongyi Qianwen. Ghi nhận sự khác nhau này để đối chiếu điều khoản của đúng weights trước phân phối/deploy thương mại; không suy từ model gốc thành kết luận mọi artifact đều cùng giấy phép. Đợt này chỉ dùng local và không đưa weights vào repo.

## Chạy kiểm tra lại mà không thêm lượt model

- Backend: `.venv/bin/python -m pytest -q` từ `backend`.
- Kiểm tra parser: `.venv/bin/python scripts/check_scene_image_runtime.py` từ `backend`; chỉ parse/validate, không nạp weights.
- Browser giả: chạy `tests/ui_workspace_fixture.py`, frontend build trỏ API QA 8034, server 3034, rồi `FIRSTFRAME_QA_DIRECTORY=<fixture sạch> NODE_PATH=<Playwright> node frontend/tests/scene-sketch.browser.cjs`. Không dùng DB tác giả.
- Không chạy lại runner `--run` hoặc xóa thư mục kết quả để lách giới hạn. Giữ bộ đóng băng, mọi lỗi và ngân sách đã dùng.
