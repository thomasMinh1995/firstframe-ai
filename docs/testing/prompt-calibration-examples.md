# Offline prompt calibration examples

These examples are review fixtures, not runtime story context. Runtime prompts keep the general rules.


## story_mentor

## Calibration examples (illustrative; never import their details into another story)

Brief: "Một người cha gặp con gái trước khi cô đi xa. Tôi không muốn cảnh níu kéo.
Chỉ quay hai người ở bàn ăn."

Useful question: "Trong cuộc gặp ở bàn ăn, bạn muốn người cha cố nói điều gì mà
trước giờ chưa nói được, hoặc bạn muốn ông chủ động im lặng? Bạn có thể chọn
một hướng khác."

This asks about an unresolved action without deciding that he must stop her or
that they must reconcile. Do not ask how many characters or locations are available.

Brief: "Phim quan sát 3 phút, không thoại: mẹ dọn hai bát cơm nhưng ăn một mình.
Máy tĩnh trong căn bếp. Tôi muốn cảm giác chờ đợi, không tiết lộ người kia là ai
và không giải thích họ có về hay không."

Useful output: missing_information is []. Reflect the chosen waiting, silence,
and ambiguity. Do not ask who the absent person is, demand a climax, or resolve
the ending merely to complete a template.

Brief: "Chỉ quay trong một căn hộ, nhưng kết thúc cần thấy hai cha con ôm nhau
ở sân bay."

Useful question: "Bạn muốn giữ hình ảnh ôm nhau ở sân bay hay giữ giới hạn một
căn hộ và tìm cách khác thể hiện cuộc chia tay? Bạn cũng có thể đề xuất hướng khác."

Here the contradiction blocks planning; ask the creator which choice matters most.


## script_critic

## Calibration examples (illustrative, not facts about the current draft)

Intent: quiet, open ending; the daughter need not forgive her father.
Current [Ending]: "Người cha đặt chìa khóa lên bàn. Con gái nhìn, không cầm lên."

Grounded strength: "[Ending] Con gái nhìn chìa khóa mà không cầm lên giữ được
khoảng cách giữa hai người, phù hợp với kết mở bạn muốn."
Do not demand a hug, forgiveness, or an explicit explanation of her feelings.

Intent: only one apartment; the father wants to apologize, not stop her leaving.
Current [Middle]: father hides her passport. Current [Ending]: a goodbye in the apartment.

Weakness: "[Middle] Việc giấu hộ chiếu có thể khiến người xem hiểu người cha
muốn ngăn con đi, khác với ý định chỉ xin lỗi bạn đã nêu."
Matching suggestion: "[Middle] Bạn muốn giữ hành động giấu hộ chiếu để người cha
còn mâu thuẫn, hay giữ hướng chỉ xin lỗi? Nếu chọn hướng thứ hai, có thể để ông
ngập ngừng trước một lời xin lỗi ngay trong căn hộ; chưa cần thêm bối cảnh."
Do not declare that the passport action is necessarily a mistake or erase it.

Intent: observational waiting in silence; the absent person's identity stays unknown.
Current [Beginning]: mother sets two bowls. [Middle]: she folds a napkin.
[Ending]: one untouched bowl remains, but no detail indicates time passing.

Possible issue, if supported by the full draft: "[Middle, Ending] Từ gấp khăn đến
bát cơm còn nguyên chưa có dấu hiệu thời gian trôi; người xem có thể thấy một
khoảnh khắc ăn một mình thay vì cảm giác chờ đợi bạn muốn."
Small revision: "[Middle, Ending] Có thể cho bát cơm từ còn bốc hơi đến nguội đi
để cảm nhận thời gian chờ, vẫn giữ im lặng và không tiết lộ người vắng mặt."
Do not add a phone call explaining that person's identity or fate.



## script_critic_vi

## Ví dụ hiệu chỉnh, không phải sự thật của bản đang đọc

Ý đồ: kết mở lặng lẽ, con gái không cần tha thứ.
[Ending]: “Người cha đặt chìa khóa lên bàn. Con gái nhìn, không cầm lên.”

Điểm mạnh có căn cứ: “[Ending] Con gái nhìn chìa khóa mà không cầm lên giữ được
khoảng cách giữa hai người, phù hợp với kết mở bạn muốn.”
Không đòi ôm, tha thứ hoặc giải thích rõ cảm xúc của cô.

Ý đồ: chỉ một căn hộ; cha muốn xin lỗi, không ngăn con đi.
[Middle]: cha giấu hộ chiếu. [Ending]: chia tay trong căn hộ.

Điểm yếu: “[Middle] Việc giấu hộ chiếu có thể khiến người xem hiểu người cha
muốn ngăn con đi, khác với ý định chỉ xin lỗi bạn đã nêu.”
Gợi ý cùng mục: “[Middle] Bạn muốn giữ hành động giấu hộ chiếu để người cha
còn mâu thuẫn, hay giữ hướng chỉ xin lỗi? Nếu chọn hướng thứ hai, có thể để ông
ngập ngừng trước một lời xin lỗi ngay trong căn hộ; chưa cần thêm bối cảnh.”
Không mặc định giấu hộ chiếu là lỗi hoặc tự xóa hành động.

Ý đồ: quan sát chờ đợi im lặng, không tiết lộ người vắng mặt là ai.
[Beginning]: mẹ đặt hai bát. [Middle]: gấp khăn.
[Ending]: một bát còn nguyên, nhưng không có dấu thời gian trôi.

Vấn đề có thể có nếu toàn bản hỗ trợ: “[Middle, Ending] Từ gấp khăn đến bát cơm
còn nguyên chưa có dấu hiệu thời gian trôi; người xem có thể thấy một khoảnh
khắc ăn một mình thay vì cảm giác chờ đợi bạn muốn.”
Sửa nhỏ: “[Middle, Ending] Có thể cho bát cơm từ còn bốc hơi đến nguội đi để
cảm nhận thời gian chờ, vẫn giữ im lặng và không tiết lộ người vắng mặt.”
Không thêm cuộc gọi giải thích danh tính hoặc số phận người đó.

