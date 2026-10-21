# Kế hoạch: Tour hướng dẫn người dùng mới

- Trạng thái: đề xuất; chưa triển khai.
- Issue: [Feature #22](https://github.com/thomasMinh1995/firstframe-ai/issues/22).
- Phạm vi hiện tại: tài liệu kế hoạch và issue theo dõi; chưa thay đổi runtime hoặc dependency.

## Mục tiêu và bối cảnh

Giúp người mới biết bắt đầu ở đâu, hiểu các lựa chọn sáng tác thuộc về mình,
và đi qua một vòng phát triển câu chuyện: tạo dự án, nhập ý tưởng, làm rõ,
tạo bản phát triển, tự sửa và nhận phản hồi.

Ảnh tham khảo định hướng cách trình bày: nền tối, vùng đang hướng dẫn được
làm nổi bật, thẻ nội dung ngắn và điều hướng từng bước. Nội dung tour bám vào
FirstFrame, không sao chép workflow tổng quan nghiên cứu trong ảnh.

MVP hiện có workspace Next.js/React tại `frontend/app/page.tsx`, lưu dự án
cục bộ qua backend và chưa có tài khoản. Phần hỏi đáp chỉ xuất hiện khi có
`analysis` và brief không bị sửa; phần bản phát triển cần có `draft`.
Tour phải đi theo các điều kiện này, không yêu cầu sẵn mọi phần trên màn hình.

## Phạm vi MVP

- Một tour tiếng Việt cho workspace chính `/`, gồm sáu bước theo ba chặng.
- Lời mời bắt đầu, spotlight, thẻ hướng dẫn, chuyển bước, đóng/bỏ qua,
  tiếp tục và xem lại.
- Lưu tiến độ theo trình duyệt; thích ứng dữ liệu dự án đang mở.
- Hỗ trợ mobile, bàn phím và trình đọc màn hình.
- Giải thích đúng việc lưu, gọi AI và độ mới của phản hồi.

Không bao gồm tour riêng cho `/demo` hoặc `/datasets`, mascot/animation mới,
dịch toàn bộ giao diện, đồng bộ tài khoản, dashboard analytics, thay đổi
backend, tự điền ý tưởng hoặc tạo nội dung mẫu. Nút demo hiện có vẫn là lựa
chọn cho người muốn xem trước workflow mà chưa gọi AI.

## Nội dung sáu bước

| Bước / chặng | Vùng hướng dẫn | Nội dung dự kiến và điểm thực hành |
| --- | --- | --- |
| 1 / Bắt đầu | Nút Dự án mới | “Tạo không gian riêng cho câu chuyện của bạn. Bạn có thể lưu và quay lại viết tiếp.” Chưa có dự án thì dừng để người dùng tự tạo. |
| 2 / Bắt đầu | Ý tưởng và điều muốn giữ | “Bắt đầu bằng một tình huống hoặc kỷ niệm. Ghi thêm điều bạn muốn giữ, như kết thúc mở hoặc chỉ có hai nhân vật.” Dừng để nhập; không tự điền hoặc lưu. |
| 3 / Bắt đầu | Ngôn ngữ đầu ra và Cùng làm rõ ý tưởng | “Chọn ngôn ngữ cho nội dung AI, rồi cùng làm rõ những lựa chọn sáng tác.” Giải thích chọn ngôn ngữ không tự dịch nội dung đã có. Người dùng tự bấm làm rõ; thao tác hiện có sẽ lưu trước khi gọi AI. |
| 4 / Làm rõ | Những lựa chọn của bạn và nút tạo bản phát triển | “Trả lời theo ý bạn. Nếu chưa chắc, chọn Để quyết định sau trước khi tạo bản phát triển.” Người dùng tự trả lời và tạo bản phát triển. |
| 5 / Viết và sửa | Bản phát triển đang làm việc | “Đây là bản để bạn tiếp tục viết. Bạn có thể sửa tên phim, tóm tắt và từng phần câu chuyện.” Nêu đây là bản phát triển, chưa phải kịch bản theo cảnh hoàn chỉnh. |
| 6 / Viết và sửa | Nhận phản hồi, vùng phản hồi nếu có và thanh lưu | “Xin góp ý cho bản hiện tại rồi tự quyết định cách sửa. Lưu thay đổi trước khi rời đi.” Giải thích nhận phản hồi sẽ lưu trước khi gọi AI; sửa tiếp khiến góp ý cũ thuộc bản trước. |

Mỗi thẻ có tiêu đề, một hoặc hai câu và một thao tác tiếp theo. Khi cần giải
thích nhiều vùng cách xa nhau, spotlight lần lượt từng vùng; không mở rộng
một khung lớn che toàn bộ form. Không dùng điểm AI làm điều kiện hoàn thành.

## Khởi động, thực hành và tiếp tục

### Lần đầu và người đã có dự án

- Chỉ xác định điều kiện mời sau khi tải danh sách và dự án thành công.
  Lỗi kết nối không được xem là chưa có dự án.
- Nếu chưa có dự án và chưa có trạng thái tour, tự hiện lời mời ngắn với
  “Bắt đầu hướng dẫn” và “Bỏ qua”. Chỉ mở spotlight sau khi người dùng chọn bắt đầu.
- Nếu đã có dự án, không tự bật overlay. Luôn có nút “Hướng dẫn sử dụng”
  tại đầu workspace để chủ động mở.
- Lời mời và tour đều có thể đóng; đóng, Escape hoặc bỏ qua đều ngừng các
  hướng dẫn tự động còn lại cho đến khi người dùng chủ động mở lại.
- Không tự phát lại chỉ vì mở ứng dụng lần nữa hoặc thay đổi phiên bản
  nội dung tour. Giữ lựa chọn đã đóng/bỏ qua/hoàn thành khi nâng phiên bản.

### Điều hướng và điểm dừng thực hành

- Thẻ có “Trước”, “Tiếp”, “Bỏ qua”, nút đóng và số bước của toàn luồng.
  Ở bước cuối dùng “Hoàn tất hướng dẫn”.
- “Tiếp” và “Trước” chỉ chuyển giữa các bước có vùng đích hợp lệ.
  Không dùng nút tour để gọi `persist()`, `action()`, tạo dự án hoặc khôi phục phiên bản.
- Tại bước cần dữ liệu chưa có, dùng “Thực hành” thay cho việc nhảy tới
  phần chưa xuất hiện. Thao tác này đóng overlay, trả focus về control
  thích hợp và giữ bước tiếp theo đang chờ.
- Người dùng thao tác qua các nút thật của workspace. Việc nhập, lưu,
  phân tích, tạo bản phát triển và review giữ nguyên quy tắc hiện có.
- Trong cùng phiên tour, chỉ gợi ý tiếp tục chặng sau khi thao tác thành
  công, đúng dự án, ứng dụng hết bận và vùng đích đã render. Hiện nút
  “Tiếp tục hướng dẫn”; không tự bật thẻ che nội dung vừa trả về.
- Reload hoặc rời trang giữa chừng: khi quay lại, hiện lựa chọn tiếp tục,
  không tự mở spotlight hoặc chạy lại tác vụ AI đang chờ.
- Đổi dự án: đóng overlay, bỏ trạng thái chờ của dự án trước và yêu cầu
  chủ động tiếp tục trên dự án mới. Kết quả đến muộn không được mở lại tour.

### Dữ liệu có điều kiện và mở lại

- Chưa có dự án: bắt đầu từ bước 1.
- Có dự án, chưa có analysis hợp lệ: bắt đầu tại bước 2.
- Có analysis hợp lệ, chưa có draft: bắt đầu tại bước 4.
- Có draft: bắt đầu tại bước 5; bước 6 vẫn giải thích được khi chưa có feedback.
- Có analysis nhưng không có câu hỏi: bước 4 nói rõ có thể tạo bản phát
  triển ngay, không yêu cầu trả lời câu hỏi không tồn tại.
- Khi brief đang sửa khiến phần lựa chọn bị ẩn, không dùng analysis cũ
  để dẫn tới bước 4; đưa người dùng về bước 2–3 khi họ chọn tiếp tục.
- Nếu nút làm rõ không hiện vì analysis vẫn hợp lệ, bỏ bước 3 khi điều
  hướng lại và dẫn tới bước 4; không yêu cầu chạy AI lần nữa để xem tour.
- “Trước” chỉ đi tới phần còn khả dụng; nếu vùng đích biến mất thì tạm
  dừng, không vẽ spotlight ở tọa độ cũ hoặc âm thầm đánh dấu đã xem.
- Hoàn thành nghĩa là đã xem phần kết của hướng dẫn khả dụng, không
  chứng nhận đã tạo draft, đã review hoặc đã hoàn thành câu chuyện.

## Trạng thái và lưu tiến độ

Dùng một record `localStorage` với key `firstframe:onboarding`, chứa version,
trạng thái (`active`, `waiting`, `paused`, `dismissed`, `completed`),
ID bước ổn định và ID dự án nếu bước đang chờ gắn với dự án.

Đọc storage sau khi mount để tránh lệch hydration. Kiểm tra cấu trúc và
giá trị trước khi dùng; record hỏng thì bỏ qua an toàn. Khi không đọc/ghi
được storage, tour vẫn chạy bằng state trong phiên, không chặn workspace.
Sau reload, `active`/`waiting` chỉ tạo lời nhắc tiếp tục, không tự khởi chạy.

Không lưu ý tưởng, câu trả lời, bản thảo hoặc phản hồi trong record tour.
Tiến độ thuộc trình duyệt, không phải bằng chứng nhận diện người dùng.
Đổi trình duyệt hoặc xóa storage có thể khiến lời mời xuất hiện lại.

## Giao diện và accessibility

- Dùng màu, font, nút và bo góc hiện có. Desktop đặt thẻ cạnh mục tiêu,
  có khoảng cách và đổi hướng khi gần mép viewport.
- Mobile đặt thẻ phía dưới, có chiều cao tối đa và cuộn được; giữ vùng
  đích nhìn thấy cả khi bàn phím ảo mở.
- Dùng anchor `data-tour` ổn định; không tìm mục tiêu bằng chữ hiển thị
  hoặc thứ tự DOM. Đo lại khi cuộn, resize hoặc kích thước mục tiêu đổi;
  dọn listener/observer khi đóng.
- Spotlight ở chế độ xem chỉ để quan sát. Các tương tác thực hành diễn
  ra sau khi đóng overlay, tránh vô tình bấm xuyên nền.
- Dialog có nhãn/description, focus nằm trong thẻ khi mở; Tab/Shift+Tab
  hoạt động đúng, Escape đóng và trả focus về nút mở hoặc vùng thực hành.
  Không để nền nhận focus trong khi overlay đang mở.
- Tôn trọng giảm chuyển động; hướng dẫn không phụ thuộc riêng vào màu.
- Không mở tour trong lúc `busy`, không che lỗi hoặc tiến trình AI.
  Nếu phát sinh lỗi, ưu tiên thông báo hiện có và tạm dừng hướng dẫn.

## Bảo toàn dữ liệu và lỗi

Mở/đóng/đổi bước chỉ thay đổi state tour, scroll và focus. Không thay
`project`, `saved`, dirty, revision, feedback freshness hoặc lịch sử.

Lỗi lưu, validation, 409 hoặc AI không làm bước thực hành thành công.
Giữ buffer và trạng thái lỗi hiện có; không tự retry, reload hoặc gọi AI
tiếp. Với kết quả mạng chưa rõ, tour không suy đoán thao tác đã hoàn tất.
Chỉ tiếp tục sau dữ liệu thành công được workspace xác nhận cho đúng dự án.

Theo dõi tour không được thêm request ghi dữ liệu, model call, dataset
recording hoặc sửa cơ chế xử lý kết quả đến muộn của workspace.

## Hướng triển khai

| Thành phần | Thay đổi dự kiến |
| --- | --- |
| `frontend/app/page.tsx` | Nút hướng dẫn; anchor ổn định; truyền trạng thái đã tải/busy/dự án/briefChanged và kết quả thao tác đã được chấp nhận |
| `frontend/app/OnboardingTour.tsx` — mới | Overlay, spotlight, dialog, điều hướng, scroll, focus và xử lý viewport |
| `frontend/app/onboardingState.ts` — mới | Nội dung sáu bước, chọn bước khả dụng, chuyển trạng thái, đọc/ghi tiến độ có kiểm tra |
| `frontend/app/globals.css` | Style tour theo giao diện hiện có; mobile và reduced motion |
| `frontend/tests/onboarding.cjs` — mới | Kiểm tra điều kiện, chuyển trạng thái, storage và không gây tác dụng phụ |
| Tài liệu | Liên kết roadmap và checklist kiểm thử/ghi nhận kết quả khi triển khai |

Ưu tiên React/CSS và API trình duyệt hiện có, chưa thêm dependency. Không
xây framework tour dùng chung cho nhiều trang. Logic workflow và lưu dự án
tiếp tục ở nơi hiện có; tour chỉ nhận dữ liệu cần cho hướng dẫn.

## Thứ tự thực hiện và ước lượng

1. Chốt copy, anchor, hành vi đóng/tiếp tục và mẫu desktop/mobile: 0,5 ngày.
2. Dựng overlay/dialog, spotlight, focus và responsive: 1 ngày.
3. Kết nối ba chặng, điều kiện dữ liệu và lưu tiến độ: 1 ngày.
4. Kiểm thử, sửa lỗi và thử với người mới: 0,5–1 ngày.

Ước lượng 3–4 ngày công triển khai, chưa tính chờ người thử hoặc thay đổi
phạm vi. Không cần thay đổi backend hay gọi model thật để kiểm tra logic tour.

## Tiêu chí nghiệm thu

- [ ] Lời mời chỉ tự xuất hiện sau tải thành công, chưa có dự án và chưa từng đóng/bỏ qua/hoàn thành.
- [ ] Người đã có dự án chỉ mở tour khi chủ động chọn; điểm bắt đầu phù hợp dữ liệu.
- [ ] Sáu bước chỉ dẫn đúng control đang tồn tại; mục tiêu biến mất thì tạm dừng an toàn.
- [ ] Tạo dự án, phân tích và tạo draft thành công cho phép tiếp tục đúng chặng; lỗi không làm tiến bước.
- [ ] Analysis không có câu hỏi vẫn có hướng dẫn đúng; brief đang sửa không dẫn vào hỏi đáp cũ.
- [ ] Đóng, Escape và bỏ qua ngừng toàn bộ hướng dẫn tự động còn lại, kể cả kết quả AI đến muộn.
- [ ] Reload cho chọn tiếp tục; đổi dự án không mang bước đang chờ của dự án trước sang.
- [ ] Có thể mở lại sau bỏ qua hoặc hoàn thành, không cần sửa dự án hoặc gọi AI lại.
- [ ] Mọi thao tác của tour giữ nguyên toàn bộ buffer, dirty, revision, feedback và lịch sử.
- [ ] Tour không tạo request ghi dữ liệu/model call; thao tác thực hành qua nút thật vẫn giữ hành vi lưu trước AI.
- [ ] Storage hỏng/bị chặn không gây crash; nâng version giữ lựa chọn đã đóng/bỏ qua/hoàn thành.
- [ ] Desktop/mobile, cuộn/resize, bàn phím ảo và nội dung dài không làm thẻ tràn hoặc che vùng thực hành.
- [ ] Dùng được với bàn phím và trình đọc màn hình; focus được giữ/trả đúng, giảm chuyển động được tôn trọng.
- [ ] Nội dung phân biệt bản phát triển với screenplay, và phản hồi cũ với phản hồi cho bản hiện tại.

## Kiểm chứng khi triển khai

- Kiểm tra tự động cho chuyển trạng thái và chọn bước theo dữ liệu; dùng
  pattern TypeScript + Node assert hiện có trong `frontend/tests/progress.cjs`.
- Kiểm thử tương tác trên trình duyệt với backend/provider giả: từ trạng
  thái trống, dự án đã có analysis/draft, không có câu hỏi, lỗi lưu/AI, đổi
  dự án, reload và kết quả đến muộn.
- So sánh toàn bộ buffer trước/sau thao tác tour và theo dõi network để
  xác nhận không gọi lưu/AI. Render tĩnh không đủ chứng minh focus,
  scroll hoặc không có tác dụng phụ.
- Chạy TypeScript, production build và các frontend regression checks
  liên quan; kiểm tra accessibility và mobile trực tiếp.
- Đề xuất thử với 3–5 người mới: họ xác định được bước tiếp theo, hiểu
  quyền tự sửa và biết cách lưu/quay lại. Ghi nhận chỗ bị kẹt hoặc phải
  hỏi trợ giúp; đây là pilot dự kiến, chưa phải kết quả đã đo.

Issue chỉ hoàn thành sau khi triển khai và đạt tiêu chí nghiệm thu.
Viết plan hoặc hoàn thành lượt xem tour không đồng nghĩa hoàn thành feature.
