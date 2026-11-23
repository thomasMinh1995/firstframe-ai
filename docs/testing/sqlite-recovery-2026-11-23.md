# SQLite: tương thích và khôi phục trước phát hành

Phạm vi: projects.sqlite3 (gồm projects và draft_runs) và scene-images. SQLite tiếp tục là DB hiện tại.
Chất liệu dataset xuất riêng nếu có; JSON tải từ giao diện không chứa tệp ảnh và chưa có chức năng import.

## Bằng chứng tương thích
Fixture project-main-9db2f6f.json được tạo bằng API/ProjectStore của main 9db2f6f53bd980a43a8c9e15d6ef3c121524b581 trong thư mục tạm, không dùng DB thật.
Nó ghi schema SQL và project raw của main; API tạo/lưu thủ công Story plan, dàn cảnh và kịch bản có lời thoại/lịch sử; không gọi model. Không suy luận định dạng cũ từ model dev.
Test mở nguyên DB dạng cũ, kiểm read không viết lại nội dung, sửa tên và restart giữ nguyên ý tưởng, dàn cảnh, lời thoại và lịch sử kịch bản.
Bộ kiểm tra recovery vốn đã PASS trên baseline; PR bổ sung bằng chứng/kiểm tra, không sửa runtime hoặc dựng RED giả.

## Backup nhất quán
1. Hoàn tất hoặc dừng các lượt AI; chờ tự lưu và xác nhận không còn buffer chưa lưu. Giữ bản đang viết trước khi dừng ứng dụng.
2. Dừng toàn bộ backend/worker đang dùng DB, giữ nguyên source/DB gốc. Frontend không được tiếp tục ghi.
3. Chọn đường dẫn tuyệt đối của thư mục dữ liệu và một thư mục backup mới. Không đọc .env; không trỏ lệnh QA vào DB thật.
4. Chạy bằng Python, truyền hai đường dẫn đã kiểm tra:
```sh
python - /absolute/source-data /absolute/new-backup <<'PY'
from pathlib import Path
import shutil, sqlite3, sys
source, target = map(Path, sys.argv[1:])
assert source.is_absolute() and target.is_absolute()
assert (source / 'projects.sqlite3').is_file()
assert not target.exists()
assert source.resolve() not in target.resolve().parents
assert target.resolve() not in source.resolve().parents
# Validate the source before copying; never let sqlite3 create an empty source DB.
with sqlite3.connect(f'{source.joinpath("projects.sqlite3").as_uri()}?mode=ro', uri=True) as live:
    assert live.execute('PRAGMA integrity_check').fetchone() == ('ok',)
    target.mkdir(parents=True)
    with sqlite3.connect(target / 'projects.sqlite3') as snapshot:
        live.backup(snapshot)
        assert snapshot.execute('PRAGMA integrity_check').fetchone() == ('ok',)
if (source / 'scene-images').exists():
    shutil.copytree(source / 'scene-images', target / 'scene-images')
PY
```
Nếu lệnh thất bại, đánh dấu bản backup chưa hoàn tất và giữ source gốc; không dùng thư mục backup dở để restore.
SQLite backup API bao gồm dữ liệu đã commit trong WAL. Dừng writer vẫn cần để snapshot DB và ảnh khớp nhau.
Giữ source revision/dependency lock, thời điểm backup và checksum của DB/ảnh cùng bản sao; hạn chế quyền truy cập như dữ liệu gốc.

## Restore và rollback
1. Giữ backend/worker dừng. Chuẩn bị checkout phát hành riêng; copy toàn bộ backup đã kiểm vào backend/.data của checkout đó, thư mục này phải chưa tồn tại. Không chồng lên DB đang hoạt động hoặc giữ lại WAL/SHM cũ.
2. Kiểm integrity_check trên DB đã restore và kiểm ảnh theo asset_id. Khởi động backend từ đúng checkout mới; store mặc định ở backend/.data và ảnh ở backend/.data/scene-images.
3. Khởi động một backend duy nhất và mở dự án: đối chiếu chữ Việt, revision, history, snapshot PDF và ảnh; không chạy AI để thử restore.
4. Lượt running của process cũ chuyển interrupted; candidate/calls đã lưu được giữ, không tự gửi lại AI. Người dùng quyết định tiếp tục sau khi kiểm tra.
5. Chỉ cho phép ghi trở lại sau nghiệm thu. Nếu rollback code, dùng cả source cũ và snapshot trước nâng cấp; không giả định source main cũ hiểu mọi trường/lượt nháp mới.
Không khôi phục các buffer chưa từng được lưu; không hứa giữ lượt AI đang chạy khi backup.

## Kiểm chứng tự động
`PYTHON_DOTENV_DISABLED=1 python -m pytest -q tests/test_sqlite_recovery.py`
Dữ liệu kiểm thử nằm trong tmp_path. Test backup DB và ảnh, làm thay đổi/xóa dữ liệu gốc, restore sang thư mục mới, rồi so sánh toàn project, ảnh, PDF, pending run và integrity_check; provider/launch bị chặn.
Đây là diễn tập bằng dữ liệu giả, không phải bằng chứng đã backup/restore DB production hoặc đo độ bền nhiều người dùng.
