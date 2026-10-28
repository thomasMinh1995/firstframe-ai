# Phiếu kiểm chứng vòng sửa #7 + tour theo HITL

Ngày chuẩn bị: 26/10/2026. **Mẫu chưa chạy, chưa có kết quả nghiệm thu.**
Dùng sau PR #43; không thay tiêu chí [#7](../plans/p0-author-intent-revision-flow.md),
[tour #22](../plans/new-user-tour.md) hoặc [pilot #26](../plans/vietnam-first-screenplay-mvp.md#61-điều-kiện-pilot-đạt-và-chuyển-sang-m2).
Chuẩn bị phiếu không cho phép tự gọi model hoặc bắt đầu pilot.

## 1. Chốt trước buổi kiểm chứng

Điền một bản cho mỗi người/phiên; dùng mã thay tên trong bản chia sẻ.

| Trường | Ghi trước khi bắt đầu |
| --- | --- |
| Mã đợt / mã người / ngày / người quan sát | … |
| Mục đích và chế độ | … / diễn tập với output đã lưu hoặc kiểm chứng luồng model thật |
| Phạm vi bằng chứng dự kiến | #7 / tour #22 / pilot #26; ghi riêng, không mặc định nghiệm thu cả ba |
| Commit/build ứng dụng | …; bản HITL đã merge: `4119366f9180870bc5604a8c37c1bd09f1ea254e` |
| Model/provider/digest/daemon/tham số | …; phát lại ghi cấu hình của output gốc, không gọi là cấu hình vừa chạy |
| Phiên bản prompt/schema và seed nếu có | …; phát lại ghi nguồn gốc, không đổi cấu hình giữa đợt rồi gộp kết quả |
| Thiết bị/trình duyệt/cách nhập/trợ năng | …; phân biệt thiết bị thật với viewport mô phỏng |
| Tài liệu và tour dùng chung | …; trạng thái mới/đã bỏ qua/đã hoàn tất, có chủ động mở lại không |
| Chất liệu, điều tác giả muốn giữ/để mở | …; phân biệt nguyên văn tác giả với đề xuất AI |
| Quyền sử dụng nội dung, log/ảnh/ghi âm nếu có | …; chưa được đồng ý thì không chia sẻ hoặc đưa chất liệu riêng vào repo công khai |
| Số người bắt đầu, nhiệm vụ chung, phiên bản và người duyệt | …; chốt theo kế hoạch tương ứng, không điều chỉnh sau khi thấy kết quả |

Diễn tập có thể dùng bốn ca đã lưu để kiểm tra cách đọc/chọn/sửa; đó là ca
phát triển đã được biết đáp án, không phải holdout hoặc pilot #26 với câu chuyện
của người tham gia. Phát lại không chứng minh làm rõ, sinh plan hoặc review mới
hoạt động. N1/N2 còn mở; buổi có người quan sát sửa nội dung hộ không tự thành
nghiệm thu H0. Đợt nghiệm thu chính thức vẫn phải đủ điều kiện, hết lỗi chặn.

## 2. Lời giao nhiệm vụ chung và cách quan sát

> Hãy dùng FirstFrame phát triển một khoảnh khắc của bạn thành story plan,
> đọc góp ý rồi tự quyết định điều muốn giữ hoặc sửa. Hãy lưu, mở lại bản của
> mình và giải thích lựa chọn. Bạn có thể dùng hướng dẫn có sẵn trong sản phẩm.

Không đưa đáp án bốn ca hoặc giảng trước thông điệp HITL để rồi coi việc nhắc
lại là người dùng tự hiểu UI. Quan sát trước, ghi thời điểm/nguyên văn mọi trợ
giúp. Câu hỏi sau nhiệm vụ dùng để tìm hiểu lý do; nếu hỏi trong lúc làm khiến
người dùng đổi quyết định thì ghi sự can thiệp, không coi là quan sát trung lập.

| Bước | Nhiệm vụ giao người dùng | Bằng chứng cần ghi |
| --- | --- | --- |
| 1 | Bắt đầu/mở đúng dự án; dùng tour nếu muốn | Tự tìm được bước tiếp theo; tour có khớp trạng thái, bỏ qua/mở lại được không; không ép xem lại hoặc xóa tiến độ |
| 2 | Nhập khoảnh khắc, điều muốn giữ; làm rõ, trả lời hoặc để mở lựa chọn rồi tạo story plan | Nguyên văn ý đồ, lựa chọn mở; điểm mắc và trợ giúp. Trong chế độ phát lại, đánh dấu bước AI chưa được kiểm chứng |
| 3 | Đọc story plan, kể lại diễn tiến và chỉ một chi tiết muốn giữ | Có hiểu câu chuyện, phân biệt story plan với kịch bản hoàn chỉnh; không chấm gu hoặc năng lực tác giả |
| 4 | Xem ý đồ và góp ý; giải thích nguồn góp ý đang đọc | Phân biệt tác giả/AI, bản đã lưu/buffer và nguồn góp ý cũ; họ hiểu điểm hoặc nhãn AI có ý nghĩa gì |
| 5 | Chọn một góp ý để cân nhắc, hoặc từ chối và giải thích | Ghi nguyên nhận xét/gợi ý, lý do hữu ích/dẫn sai; có đối chiếu nguồn không, chọn do hiểu hay chỉ vì tin điểm AI |
| 6 | Tự chọn chi tiết muốn chỉnh và tự sửa | Đến đúng card, giữ các phần khác và buffer; tác giả tự viết, không lấy việc chép ví dụ AI làm tiêu chuẩn tốt hơn |
| 7 | Lưu rồi nhận góp ý trên bản mới khi phiên được phép gọi model | Đúng bản/ý đồ, feedback cũ được phân biệt, không mất nội dung. Phát lại: chỉ ghi diễn tập/không áp dụng, không gọi là review mới |
| 8 | Rời/mở lại dự án và giải thích quyết định giữ/sửa | Mở đúng bản đã lưu, nhận ra nội dung sửa và nguồn góp ý; muốn viết tiếp không, bước tiếp cụ thể là gì |

Với đánh giá #7 theo kế hoạch, lặp bước 4–8 cho vòng sửa thứ hai, ghi riêng
hai vòng. Không tạo lỗi hoặc bắt chấp nhận AI để có đủ lượt sửa. Nếu tác giả
chọn giữ nguyên, ghi nhận lý do và phần nhiệm vụ sửa chưa được chứng minh;
không tự tính thành một vòng sửa hoàn tất. #26 giữ nguyên nhiệm vụ chung đã
chốt và yêu cầu tự sửa một chi tiết; không đổi nhiệm vụ giữa người tham gia.

## 3. Nhật ký từng bước và mức trợ giúp

| Bước / vòng | Bắt đầu–kết thúc | Hoàn thành/chưa/bỏ dở/không áp dụng | Người dùng làm/nói gì, điểm mắc | H0/H1/H2 và lời trợ giúp nguyên văn | Lỗi + tham chiếu bằng chứng |
| --- | --- | --- | --- | --- | --- |
| … | … | … | … | … | … |

- **H0:** chỉ hướng dẫn chung, tour và tài liệu có sẵn dùng chung trong sản
  phẩm. Tự dùng tour hoặc tài liệu không làm mất tính độc lập.
- **H1:** người quan sát nhắc bước hoặc chỉ chỗ thao tác, kể cả nhắc dùng
  tour sau khi người dùng đã mắc. Ghi đúng thời điểm và lời nhắc.
- **H2:** gợi ý nội dung/chi tiết nên giữ, bỏ, viết hay sửa; chỉ ra góp ý nào
  sai trong lúc họ quyết định; hoặc thao tác hộ. Không tính là H0 chỉ vì người
  dùng tự gõ câu do người quan sát gợi ý.

Mỗi bước ghi mức cao nhất đã dùng cùng các lần trợ giúp; cả nhiệm vụ chỉ tính
độc lập khi hoàn thành đầy đủ ở H0. Người bắt đầu rồi bỏ dở vẫn thuộc N của
pilot #26; giữ lý do, không thay người hoặc bỏ khỏi mẫu số. Thời gian gồm đọc,
thao tác và chờ; không tự thêm giới hạn tốc độ viết của người dùng.

## 4. Phiếu cho mỗi góp ý được cân nhắc

Sao chép phần này cho từng góp ý; không chỉ chọn lượt tốt. Người quan sát điền
ID kỹ thuật từ log/snapshot, không buộc người dùng hiểu artifact hoặc schema.

| Trường | Ghi nhận |
| --- | --- |
| Vòng / project / revision / artifact / card và thời điểm | …; xác định đúng nguồn, feedback hiện hành/cũ/thiếu nguồn |
| Ý đồ nguyên văn và phần để mở | … |
| Card nguyên văn theo thứ tự cần để hiểu | … |
| Nhận xét và gợi ý nguyên văn của AI | …; giữ cả ví dụ sửa nếu có |
| Người dùng hiểu góp ý nói gì? | …; nguyên lời, không viết lại cho hợp lý |
| Quyết định và lý do của tác giả | Giữ / sửa / từ chối / cần làm rõ / chưa quyết; … |
| Nhận xét đúng không? | Đúng / một phần / sai / chưa đủ căn cứ; câu/card đối chiếu: … |
| Có ích cho tác giả không? | Có / một phần / không / chưa biết; họ nói gì hoặc làm được gì nhờ góp ý: … |
| Có nguy cơ dẫn sai không? | Trái ý đồ / bịa hoặc dẫn sai nguồn / ép sửa thiếu căn cứ / lặp nhịp / chưa thấy / chưa rõ; bằng chứng: … |
| Tác động quan sát được | Chưa làm theo / từ chối / sửa hợp ý / sửa trái ý / mất phương hướng / chưa rõ; bản trước–sau: … |
| Trợ giúp khi quyết định và sửa | H0/H1/H2, ai gợi ý điều gì: … |
| Nhận định người đọc độc lập, nếu có | Mã người/ngày/phạm vi kinh nghiệm; đồng ý hoặc bất đồng với tác giả/AI, lý do: … |

Tách ý kiến tác giả, nhận định người quan sát/người đọc và output AI; giữ bất
đồng. Không có người đọc thì ghi thiếu, không điền Codex thay người đọc độc lập.
Đây là phiếu quan sát, không biến thành điểm chất lượng hoặc ngưỡng đạt mới.

Một nhận xét có thể hữu ích dù ví dụ sửa vụng hoặc chưa có câu thay thế. Giữ
nguyên bản hợp lệ sau khi đọc góp ý aligned cũng có giá trị. Ngược lại, tác giả
từ chối đúng một lời khuyên sai không làm output ấy đạt; họ làm theo cũng chưa
chứng minh bản thảo tốt hơn. Ghi cả phần dùng được và phần có thể dẫn sai.
Nhận định “có nguy cơ” khác với bằng chứng đã gây tác động trong bản sửa.

Ca tham chiếu cho người đọc sau quan sát: N1 là đọc ngược kết mở hoặc giữ hành
vi giấu hộ chiếu trái yêu cầu; N2 là bịa mâu thuẫn giữa im lặng–trả lời hoặc
ép thêm phản ứng sau điểm dừng. Không dùng các từ khóa này làm bộ lọc tự động
hoặc đưa đáp án cho người tham gia rồi tính quyết định đó là độc lập.

## 5. Tour, lỗi và kết luận phiên

Ghi riêng: người dùng có tìm/đóng/tiếp tục/mở lại tour được không; bước nào
không khớp UI; họ hiểu việc lưu và góp ý cũ thế nào. Quan sát thao tác bình
thường; không cố gây mất mạng, xung đột hoặc lỗi dữ liệu thật trong pilot.

Nếu có mất/ghi đè nội dung, không lưu/mở lại được, sai nguồn, vi phạm ý đồ rõ
hoặc lỗi tác vụ ngăn hoàn thành: ghi ID, thời điểm, bước, bản trước/sau và
ảnh/log được phép lưu. Ngừng thao tác có thể làm mất thêm dữ liệu; không tự
retry/restore/ghi đè để vượt lỗi. Giữ phiên thất bại; sau sửa phải xác minh
lại trên ứng viên. Việc người quan sát cứu phiên được ghi là trợ giúp, không
xóa lỗi chặn hoặc đổi kết quả gốc thành đạt.

- Hoàn thành bước nào / vòng nào; mức trợ giúp cao nhất: …
- Người dùng có hiểu AI/điểm là tham khảo không? Bằng chứng nguyên lời/hành vi: …
- Lỗi chặn, giới hạn, dữ liệu còn thiếu và bất đồng: …
- Có muốn viết tiếp chính câu chuyện này không? Bước tiếp/lý do: …
- Phạm vi kết luận: diễn tập / quan sát khám phá / bằng chứng theo tiêu chí nào: …
- Người duyệt, ngày, kết luận đạt/chưa đạt/cần thêm bằng chứng: …

## 6. Tổng hợp đợt, giữ nguyên các mốc nghiệm thu

| Phạm vi | Giữ nguyên yêu cầu và cách kết luận |
| --- | --- |
| #7 | Kế hoạch đề xuất 5–10 người mới qua hai vòng sửa và 1–2 người đọc có kinh nghiệm; đối chiếu đủ tiêu chí dữ liệu/thao tác/nội dung. Không đóng issue từ điểm AI hoặc một phiên diễn tập |
| #22 | Pilot 3–5 người cùng tổng kết; screen reader, mobile/IME/bàn phím thật và full Safari vẫn cần bằng chứng riêng. Không lấy viewport mô phỏng thay thiết bị thật |
| #26 | PO chốt N=5–8 trước; ít nhất 80% hoàn thành toàn nhiệm vụ ở H0, làm tròn lên (N=5/6/7/8 cần 4/5/6/7). Ít nhất hai người đạt muốn viết tiếp; không còn lỗi chặn; PO ghi đạt/chưa đạt/cần thêm bằng chứng trước M2 |

Có thể chuẩn bị chung một đợt nếu chốt trước nhiệm vụ/phiên bản và đủ bằng
chứng cho từng phạm vi; không tự dùng một kết quả để đóng cả ba issue. Đổi
phiên bản, nhiệm vụ hoặc ngưỡng phải tách đợt theo kế hoạch; giữ kết quả cũ,
không gộp cấu hình, hạ ngưỡng hoặc đổi nhãn hồi tố để đạt. Không biến bốn ca
đã biết đáp án thành pilot với chất liệu riêng của người mới.

Demo #26 vẫn cần ba tình huống × ba lượt toàn luồng độc lập, đủ 9/9, đúng
nguồn/dữ liệu và không lỗi chặn, trong ngân sách đã chốt; diễn tập toàn bài
không quá năm phút và PO cùng người đọc duyệt live/recorded/not ready. Ngân
sách kỹ thuật đã dùng: làm rõ ≤45 giây, plan kèm critic ≤120 giây, review ≤60
giây; không nâng hồi tố và không lấy phiên người dùng này tự chứng minh đạt
demo. Bản ghi không thay pilot hoặc nghiệm thu live.

Phiếu chỉ chuẩn bị thu bằng chứng; không tự tuyển/gửi lời mời người thử,
chạy model, sửa code/runtime/plan hoặc xác nhận #7 đã đạt. Kết quả thực tế
cần được ghi tại đúng issue #7/#22/#26 theo phạm vi đã chốt.
