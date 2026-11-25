# Kế hoạch PR: kịch bản, thoại Việt và hình minh họa
Ngày rà soát: 25/11/2026. PR 1–6 đã squash merge vào dev qua #100, #115, #117, #119, #121 và #123. PR 7 triển khai chế độ chỉ sửa lời thoại đã chọn. PR 8–17 là kế hoạch.
Kế thừa [định hướng](../vietnam-first-screenplay-mvp.md) và [Task 2](../screenplay-quality-and-feedback.md).
BK/HA/QA là nhóm mục tiêu; bảng bên dưới mới là đơn vị PR. Không gom một nhóm vào một PR lớn.

## Những điểm đã xác minh
- Baseline PR 1: origin/dev tại b929ea268c1440b52633711a1db66f75600e583b; dùng clone sạch, không lấy workspace đang bẩn làm baseline.
- Script typecheck/lint/test/build nằm trong frontend/package.json, không ở repo root.
- frontend đang có package-lock.json; dùng pnpm chạy scripts không đồng nghĩa đã chuyển lockfile/package manager.
- Baseline chưa có cấu hình ESLint. PR 1 thêm cấu hình, guard env và CI chạy cùng gate.
- Backend và các fixture hiện dùng SQLite; chưa có adapter Postgres.
- Workspace có thay đổi local về đăng nhập và lockfile lớn hơn 1.100 dòng. Không đưa nguyên trạng vào các PR này.
- Một số tài liệu nêu PR mới hơn local dev: kiểm tra trạng thái merge thực trước khi coi chức năng là nền đã có.

## Quy tắc chung bắt buộc
1. Mỗi nhánh tạo từ dev đã cập nhật, đúng tên trong bảng. Base PR luôn là dev; không PR vào main.
2. Sau khi PR trước đã squash merge, cập nhật dev rồi mới tạo nhánh tiếp. PR song song cũng phải bắt đầu từ dev; chờ phụ thuộc merge rồi rebase, không mang commit phụ thuộc vào diff.
3. Merge bằng squash. Không bật auto-merge có kiểu merge chưa xác định; kiểm lại base/head, CI và số dòng ngay trước merge.
4. Mỗi PR có tổng additions + deletions < 500, tính cả code, test, docs, lockfile và file sinh được commit. Mục tiêu 250–450; 499 là trần, không phải mục tiêu.
5. Đếm bằng git diff --numstat dev...HEAD và đối chiếu số additions/deletions trên PR. Binary thay đổi cũng cần review, không dùng binary/nén/minify để né trần.
6. Khi vượt dự toán: cập nhật plan và thêm mẫu pr-N-body.md cho phần tách trước khi mở PR. Không loại test hoặc bỏ xử lý lỗi để vừa số dòng.
7. Mỗi PR runtime phải build được và giữ tương thích độc lập; API mới có thể chưa bật UI. Không merge một nửa migration/contract làm dev hỏng.
8. Thân PR: copy đúng pr-N-body.md, điền toàn bộ ___ và Closes #___ bằng issue thật có phạm vi tương ứng. Không mở khi còn placeholder.
9. Ghi SHA, tên test, lệnh và lỗi mong đợi khi test đỏ trên dev; chạy lại đúng test không đổi assertions trên bản sửa để chứng minh xanh.
10. Không sửa kỳ vọng test cũ để qua. Nếu contract mới xung đột kỳ vọng cũ, chốt lại phạm vi và tương thích trước; không tự nới test trong PR.
11. Test đỏ phải do hành vi thiếu/sai cần sửa, không do thiếu dependency, DB lỗi hoặc fixture hỏng. Test vốn xanh thì ghi baseline đã đạt và bỏ phần sửa không cần thiết.
12. Docs/evidence thuần túy ghi RED/GREEN N/A và kiểm nội dung/liên kết. Không dựng test đỏ giả cho việc viết tài liệu hay đánh giá nghệ thuật.
13. Prompt-only cần baseline thất bại ở content gate đã chốt và kết quả cùng input sau sửa; regression nguồn/đường gọi vẫn giữ. Nếu có logic mới, thêm test hành vi đỏ → xanh.
14. Với mỗi PR giữ raw evidence, cả lỗi và ngân sách đã dùng; không chỉ chọn lượt đẹp. Tham chiếu nơi lưu bền vững, không đẩy raw/private evidence lớn vào PR để vượt giới hạn.
15. Quy tắc này không phải lệnh mở/merge PR, deploy, nhắn quản trị viên hoặc mời người dùng trong đợt lập plan.

## Cách ly dữ liệu: đã chốt SQLite
**Quyết định ngày 23/11/2026:** trước mắt dùng SQLite theo xác nhận của chủ sản phẩm.
Mọi project/dataset/ảnh thử nằm trong thư mục tạm riêng của từng test; không dùng backend/.data hoặc DB thật.
Không chuyển sang Postgres trong kế hoạch này. Nếu sau này có nhu cầu, lập kế hoạch migration riêng.
- Luôn dùng checkout sạch không có .env/.env.local/.env.test và không copy/symlink env, DB, ảnh riêng từ workspace chính.
- Backend đặt PYTHON_DOTENV_DISABLED=1 từ đầu tiến trình; phiên bản python-dotenv sử dụng phải hỗ trợ và có test xác nhận. Không tin chỉ vào biến này nếu chưa kiểm.
- Next.js cũng tự nạp env riêng: chạy từ checkout sạch, không mang env file theo. Giá trị cần cho QA truyền tường minh bằng môi trường đã kiểm, không lấy secret production.
- Không dùng tài khoản/endpoint production, không gọi model trong test tự động; batch model thật có cấu hình/ngân sách và dữ liệu thử riêng.

Bản PR 1 đưa vào index này và pr-1-body.md; mẫu các PR tiếp theo được bổ sung cùng PR tương ứng.

## Bộ lệnh trước khi mở mỗi PR
Cài dependency bằng npm ci theo package-lock hiện tại. pnpm-workspace.yaml tắt verifyDepsBeforeRun để pnpm 11 không tự cài lại dependency khi chạy scripts. Không gom chuyển lockfile vào feature PR.
Chạy từ frontend của checkout kiểm thử cách ly:
```sh
pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check
```
PR backend phải chạy thêm, từ backend với Python environment cách ly:
```sh
PYTHON_DOTENV_DISABLED=1 python -m pytest -q
```
Chạy test mới riêng trên dev trước sửa và sau sửa. Chạy browser/renderer suite liên quan nếu PR đụng UI, ảnh hoặc PDF.
Nếu gate nền lỗi: lưu lỗi thật, sửa bằng PR nền riêng hoặc dừng mở PR; không bỏ pnpm lint hay đổi nhãn thành đã qua.
CI phải xác nhận đúng SHA head. Khi dev thay đổi/rebase, kiểm lại các gate trên SHA mới.
Trước khi mở/merge, git diff --check và trần dòng phải qua cho đúng diff PR; kết quả trên worktree bẩn không thay thế.

## Danh sách PR
Dự toán dưới đây là giới hạn lập kế hoạch, chưa phải số dòng đã triển khai.
| PR | Task | Nhánh chính xác | Phụ thuộc | Dự toán tối đa |
|---|---|---|---|---|
| 1 | Nền kiểm thử | codex/ff-sb-01-isolated-checks | Không; SQLite tạm đã được chốt. | 400 |
| 2 | [BK-01 — Bộ ca kịch bản và thoại Việt](../../evaluations/bk-01-writing-cases/README.md) | codex/ff-sb-02-writing-cases | PR 1. | 350 |
| 3 | [BK-02 — Baseline trên hai ca phát triển](../../evaluations/bk-02-baseline-2026-11-24/README.md) | codex/ff-sb-03-quality-baseline | PR 2; cấu hình và ngân sách model được chốt trước chạy. | 300 |
| 4 | [BK-03 — Ngữ cảnh nhân vật khi viết cảnh](../../evaluations/bk-03-character-context-2026-11-24/README.md) | codex/ff-sb-04-character-context | PR 3. | 350 |
| 5 | [BK-04 — Diễn tiến và đạo cụ giữa hai cảnh](../../evaluations/bk-04-scene-progression-2026-11-24/README.md) | codex/ff-sb-05-scene-progression | PR 3–4. | 350 |
| 6 | [BK-05 — Thoại tự chọn trong cảnh nối tiếp](../../evaluations/bk-05-vietnamese-dialogue-2026-11-24/README.md) | codex/ff-sb-06-vietnamese-dialogue | PR 4–5; model và ngân sách giữ cố định trong phép so sánh. | 450 |
| 7 | BK-06 | feat/ff-sb-07-dialogue-revision | PR 4, 6. | 450 |
| 8 | BK-07 backend | codex/ff-sb-08-feedback-source | PR 3–6; chỉ triển khai khi đã chốt lỗi cần sửa. | 400 |
| 9 | BK-07 frontend | codex/ff-sb-09-feedback-reading | PR 8. | 350 |
| 10 | HA-01 | codex/ff-sb-10-screenplay-image-source | PR 1; nền đăng nhập/phân quyền phải đã merge vào dev. | 450 |
| 11 | HA-02 backend | codex/ff-sb-11-scene-image-generation | PR 10; provider và trần chi phí/thời gian được chốt. | 450 |
| 12 | HA-02 frontend | codex/ff-sb-12-scene-image-panel | PR 11. | 400 |
| 13 | HA-03 bản đọc | codex/ff-sb-13-illustrated-reader | PR 12; chốt cách chọn snapshot ảnh trước triển khai. | 350 |
| 14 | HA-03 bản xuất | codex/ff-sb-14-illustrated-pdf | PR 13; chốt fallback khi ảnh thiếu. | 450 |
| 15 | QA-01 | codex/ff-sb-15-independent-quality | PR 6–9; đánh giá ảnh bổ sung sau PR 12–14. | 300 |
| 16 | QA-02 kỹ thuật | codex/ff-sb-16-beta-rehearsal | PR 14–15; auth, quota, backup và quyết định DB đã hoàn tất. | 300 |
| 17 | QA-02 người dùng | codex/ff-sb-17-beta-session | PR 16 đạt; quản trị viên đồng ý đăng và có người dùng tham gia. | 250 |

## Ranh giới triển khai
- PR 2–3 không tự nghiệm thu tính năng; PR 5/8 có thể bỏ nếu baseline không có lỗi tương ứng.
- PR 4 tận dụng brief/câu trả lời; không thêm hệ thống hồ sơ nhân vật mới khi chưa chứng minh thiếu dữ liệu.
- PR 6 không mở rộng mẫu theo fixture để cải thiện số đạt; lời thoại cần người đọc đối chiếu.
- PR 10–14 kế thừa ảnh M2, không đổi nguồn ảnh cũ thành screenplay ngầm. Ảnh thiếu không chặn viết/lưu/PDF văn bản.
- PR 15 là đánh giá độc lập; nếu dùng ca giữ lại để sửa tiếp, chuyển nó thành ca phát triển và bổ sung ca giữ lại mới.
- PR 16 không gom mọi lỗi phát hiện vào một PR 500 dòng: mỗi lỗi có PR sửa/test đỏ riêng và cập nhật plan.
- Nền auth/quota/backup còn thiếu trên dev cần một kế hoạch PR riêng trước beta; không coi thay đổi local là đã merge hoặc lén nhét vào PR 16.
- M1 giữ nhiệm vụ và ngưỡng hiện có. Nhiệm vụ toàn hành trình/ảnh đo riêng, chốt trước người đầu tiên tham gia.
- Đợt đầu nên thực hiện PR 1–3, rồi chọn lỗi để làm PR 4–9. HA có thể làm song song khi nền dữ liệu đã chốt.

## Bổ sung sau PR 1: dọn lint trước khi tiếp tục
- Nhánh: `codex/ff-sb-01-lint-cleanup`, tạo từ `origin/dev` 3453fae; PR vào `dev`, squash, dưới 500 dòng cộng/xóa.
- Phạm vi: sửa 20 warning React hooks/ảnh và 2 warning CSS trong build; dùng ESLint CLI thay `next lint` deprecated; lint không cho phép warning.
- Đỏ trên dev: `pnpm lint --max-warnings=0`; test hồi quy callback theo dõi và mở góp ý với nội dung cảnh mới.
- Nghiệm thu: giữ nguyên assertion cũ, chạy đủ năm lệnh, browser suite liên quan với SQLite tạm; không đọc `.env` hay gọi model thật.
- Thân PR theo `pr-1-lint-body.md`; không gom PR 2 hoặc thay đổi workspace chính.
