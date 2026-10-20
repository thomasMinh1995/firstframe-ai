# Kế hoạch: Xuất bản phát triển đã chọn ra PDF

- Trạng thái: đề xuất, chờ PO review; chưa triển khai.
- Issue: [Feature #5](https://github.com/thomasMinh1995/firstframe-ai/issues/5).
- Phạm vi PR này: tài liệu kế hoạch và liên kết roadmap, không có code hay dependency mới.

## Mục tiêu và người dùng

Người mới viết phim ngắn có thể mang bản phát triển câu chuyện (story plan) ra
ngoài FirstFrame để đọc hoặc gửi người khác góp ý. Họ chọn bản nào thì PDF chứa
đúng nội dung bản đó. Bản xuất được ghi rõ là **Bản phát triển câu chuyện**,
không được trình bày như một screenplay hoàn chỉnh.

MVP đã có `StoryDraft`, lịch sử `DraftVersion`, lưu dự án và tải bản sao JSON.
Tính năng này tận dụng dữ liệu đó, không yêu cầu viết lại story plan, nhận phản
hồi mới, đạt điểm AI hay cấu hình `OPENAI_API_KEY`.

## Phạm vi và nội dung PDF

| Đưa vào PDF | Không đưa vào PDF |
| --- | --- |
| Nhãn loại tài liệu; tên phim và logline của chính bản được chọn | Phản hồi, điểm rubric và kết luận đạt/chưa đạt của AI |
| Tiêu đề và nội dung toàn bộ các phần theo thứ tự đã lưu | Phân tích AI, câu hỏi/câu trả lời, ý tưởng gốc và ràng buộc ngoài nội dung bản thảo |
| Định danh nguồn xuất: revision hiện tại hoặc ID bản lịch sử; thời điểm của nguồn đó | Hướng dẫn mẫu `purpose` của các phần; nội dung phiên bản khác |
| Số trang và thông tin trình bày cần thiết | Storyboard, nhận xét biên tập và dữ liệu nội bộ còn lại của dự án |

Tên phim và logline lấy từ `draft`, không lấy từ tên dự án hiện tại hoặc từ
phản hồi. Không tự tạo tên tác giả vì mô hình hiện chưa có trường này. Không
tóm tắt, dịch, sửa câu, thêm thoại hoặc thay tiêu đề các phần khi xuất.
Nếu tác giả đã tự viết lời nhận xét trong nội dung bản thảo, giữ nguyên như văn
bản của họ; việc tách phản hồi dựa trên trường dữ liệu, không lọc bằng từ khóa.

Cho phép xuất bản viết dở: trường trống vẫn trống, phần rỗng vẫn giữ tiêu đề;
không thêm câu “chưa có nội dung” vào bản thảo. Chưa có `draft` thì báo chưa có
bản phát triển để xuất. Việc xuất không thay thế bản sao JSON hiện có.

## Luồng trải nghiệm

### Xuất bản đang làm việc

1. Có nút **Xuất bản phát triển PDF** gần bản đang làm việc.
2. Nếu có thay đổi chưa lưu, thông báo thao tác sẽ lưu rồi xuất; dùng luồng lưu
   hiện tại. Nếu không có thay đổi, dùng revision đã mở.
3. Chỉ gửi yêu cầu xuất sau khi lưu thành công, với revision server trả về.
4. Backend kiểm tra revision và chụp một bản dữ liệu độc lập để dựng PDF.
5. Tải tệp; giữ nguyên bản thảo, phản hồi và trạng thái đang làm việc.

Lỗi lưu hoặc xung đột revision phải dừng xuất, giữ nội dung trên màn hình và
không âm thầm lấy bản cũ. Nếu cửa sổ khác lưu sau khi backend đã chụp đúng
revision, PDF tiếp tục dùng bản đã chụp; không đọc lại rồi trộn nội dung mới.

### Xuất bản trong lịch sử

1. Mỗi bản lịch sử có nút **Xuất PDF bản này**, kèm thời điểm/nhãn để nhận biết.
2. Gửi ID ổn định của `DraftVersion`, không gửi vị trí trong danh sách phiên bản.
3. Backend tìm đúng phiên bản trong dự án và chỉ dùng `version.draft` cùng
   metadata của phiên bản đó, không lấy nội dung hay thời điểm từ bản hiện tại.
4. Tải tệp mà không khôi phục phiên bản, tự động lưu bản đang sửa, thêm lịch sử
   hoặc đánh dấu phản hồi hiện tại là mới.

Nếu bản hiện tại có thay đổi chưa lưu, xuất lịch sử vẫn giữ nguyên các thay đổi
đó. Lỗi tải PDF không làm mất nội dung và cho phép thử lại.

## Hướng triển khai đề xuất

### Backend: chọn nguồn, chụp dữ liệu, dựng tệp

- Đề xuất endpoint `POST /api/projects/{project_id}/exports/story-plan.pdf`.
- Yêu cầu chọn đúng một nguồn: `current` cùng revision dự kiến, hoặc `version`
  cùng ID phiên bản. Từ chối yêu cầu thiếu, dư hoặc trộn hai kiểu lựa chọn.
- Dùng `ProjectStore` đọc một lần và kiểm tra nguồn. Bản hiện tại cần khớp
  revision; bản lịch sử được định danh bằng ID bất biến trong đúng dự án.
- Tạo dữ liệu xuất tối thiểu từ tên phim, logline, các cặp tiêu đề/nội dung và
  metadata nguồn. Không truyền cả `ProjectResponse`, `DraftVersion` hoặc feedback
  cho bộ dựng PDF. Phản hồi AI bị loại ngay ở bước chọn dữ liệu.
- Dựng PDF phía backend bằng thư viện hỗ trợ Unicode và font nhúng. Chọn thư
  viện/font ở bước thử nghiệm kỹ thuật; ghi rõ lý do, giấy phép và cách đóng gói.
  Nội dung là văn bản thuần; không diễn giải HTML/Markdown hay tải tài nguyên
  từ đường dẫn do người dùng nhập.
- Trả tệp với `application/pdf`, tải xuống bằng tên an toàn có định danh nguồn;
  không để tên phim tạo đường dẫn hoặc header không hợp lệ. Không cache nội dung
  dự án ở proxy/trình duyệt. Chưa cần lưu tệp xuất hoặc bảng dữ liệu mới.
- Không gọi provider AI. Luồng xuất chỉ đọc dữ liệu; việc lưu bản hiện tại trước
  xuất vẫn là thao tác lưu có sẵn của ứng dụng.

| Tình huống | Hành vi đề xuất |
| --- | --- |
| Không tìm thấy dự án hoặc ID phiên bản trong dự án đó | 404; không tự chuyển sang bản mới nhất |
| Revision bản hiện tại đã thay đổi | 409; không tạo tệp từ bản khác |
| Chưa có draft hoặc lựa chọn nguồn không hợp lệ | 422 với thông báo dễ hiểu |
| Dựng/tải PDF thất bại | Báo lỗi, cho thử lại; không ghi đè dữ liệu hoặc tải tệp hỏng như thể thành công |

### Frontend: lựa chọn rõ, giữ trạng thái

- Tái sử dụng luồng `persist()` cho xuất bản hiện tại; xuất lịch sử gọi trực tiếp
  bằng ID. Không dùng nút khôi phục bản cũ để phục vụ export.
- Có trạng thái đang xuất, chặn yêu cầu lặp và giữ nguyên nguồn đã chọn trong
  suốt thao tác. Không thay dự án đang mở bằng dữ liệu trả về của bản lịch sử.
- Xử lý riêng phản hồi tệp và lỗi JSON; chỉ tải xuống khi có PDF hợp lệ. Giải
  phóng URL tạm sau tải. Hiển thị thông báo lỗi bằng tiếng Việt.

### Trình bày tài liệu

- A4, font hỗ trợ tiếng Việt được nhúng, tương phản rõ, tiêu đề có phân cấp.
- Giữ nguyên chữ, dấu câu, thứ tự đoạn và xuống dòng có ý nghĩa; cho phép xuống
  dòng mềm và ngắt trang để dàn trang, không yêu cầu giữ vị trí từng ký tự.
- Tiêu đề phần đi cùng ít nhất dòng nội dung đầu nếu có; đoạn dài, từ/URL dài
  và nội dung sát giới hạn phải được chia trang mà không mất hoặc cắt chữ.
- Tránh ép một trang bằng thu nhỏ chữ. Số trang và metadata không lẫn vào nội
  dung tác giả. Không cần mô phỏng bố cục lời thoại của screenplay ở tính năng này.

## Các bước thực hiện sau khi kế hoạch được duyệt

1. **Thử nghiệm dựng tài liệu:** dùng dữ liệu giả lập tiếng Việt ngắn, nhiều trang
   và có trường trống để chọn thư viện/font; kiểm tra bằng mắt trước khi nối UI.
2. **Chọn nguồn và API xuất:** ánh xạ dữ liệu tối thiểu, kiểm tra revision/ID,
   phản hồi tệp/lỗi, và kiểm thử không ghi dữ liệu hay gọi AI.
3. **Nối giao diện:** nút xuất hiện tại/lịch sử, lưu trước khi xuất hiện tại,
   trạng thái tải và thông báo lỗi; giữ bản sửa chưa lưu khi xuất lịch sử.
4. **Nghiệm thu:** chạy các tình huống dưới đây, render PDF thành ảnh để kiểm tra
   bố cục, ghi kết quả và cập nhật hướng dẫn sử dụng. Chỉ đóng issue khi tính
   năng thực tế hoàn thành; merge PR kế hoạch không đóng issue.

## Tiêu chí nghiệm thu và kiểm thử

| Tình huống | Kết quả bắt buộc |
| --- | --- |
| Bản A trong lịch sử khác bản B đang mở | PDF chỉ chứa nội dung A; B và bản sửa chưa lưu của B giữ nguyên |
| Chỉnh sửa hiện tại rồi xuất | Lưu thành công trước; PDF đúng revision vừa lưu, không dùng dữ liệu UI cũ |
| Cửa sổ khác lưu trước khi yêu cầu xuất được kiểm tra | Báo 409, không tải bản khác; không mất nội dung đang sửa |
| Có thay đổi sau khi đã chụp dữ liệu xuất | PDF nhất quán với nguồn đã chụp, không trộn hai revision |
| Có feedback mới/cũ trong dự án và bản lịch sử | Không có feedback, điểm rubric hoặc dữ liệu ngoài danh sách cho phép trong PDF |
| Nội dung tác giả có các từ giống tên trường feedback | Văn bản được giữ nguyên; không xóa nội dung bằng lọc từ khóa |
| Tiếng Việt, ký tự đặc biệt, dòng dài, nhiều trang, gần giới hạn hiện có | Không lỗi font, mất nội dung, tràn lề hoặc cắt trang; đối chiếu chữ và kiểm tra ảnh render |
| Có draft viết dở hoặc trường trống | Xuất phần đã có, giữ chỗ trống; không tự thêm nội dung |
| Chưa có draft; ID sai; ID của dự án khác | Báo lỗi tương ứng, không xuất nhầm bản |
| Thiếu API key; lỗi dựng hoặc tải tệp | Xuất không phụ thuộc AI; lỗi không thay đổi draft, feedback, phiên bản hoặc ngữ cảnh tác giả |
| Dự án cũ chưa có các trường metadata mới | Vẫn chọn đúng draft để xuất; thiếu metadata tùy chọn không làm mất nội dung |

Kiểm thử tự động phải chứng minh việc chọn nguồn và tách phản hồi từ dữ liệu
được chuyển tới bộ dựng, không chỉ tìm chữ trong PDF nén. Dùng dữ liệu có đánh
dấu khác nhau cho A/B và feedback để phát hiện trộn bản. Kiểm tra văn bản trích
xuất cùng với ảnh render; cả hai cần đạt trước khi nghiệm thu.

## Ngoài phạm vi và điểm PO cần duyệt

- Không viết lại nội dung, sinh kịch bản theo cảnh, xuất DOCX, xuất feedback riêng,
  thêm người dùng/tài khoản, hoặc mở rộng sang storyboard và sản xuất phim.
- PO duyệt: tên tài liệu “Bản phát triển câu chuyện”; hai cách chọn nguồn; danh
  sách nội dung xuất; cho phép bản viết dở; PDF đầu tiên dùng A4.
- Tham khảo cách phân biệt đề cương/cảnh và trình bày dễ đọc từ
  [wikiHow](https://www.wikihow.vn/Viết-kịch-bản-phim). Mẫu screenplay chỉ áp dụng
  ở bước viết theo cảnh về sau, không làm thay đổi bản phát triển hiện có.
