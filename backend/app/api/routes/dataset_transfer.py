import json
import sqlite3

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import TypeAdapter, ValidationError

from app.application.dataset_branches import ConflictChoice
from app.application.dataset_bundle import (
    MAX_BUNDLE_BYTES,
    compare_conflict,
    export_bundle,
    import_bundle,
    inspect_bundle,
    validate_bundle,
)
from app.application.dataset_review import ReviewConflict

router = APIRouter(prefix="/api/datasets/bundle", tags=["dataset transfer"])


@router.get("")
def download_bundle():
    try:
        value = export_bundle()
    except ValueError as error:
        raise HTTPException(
            422,
            str(error)
            if not isinstance(error, ValidationError)
            else "Dữ liệu đang thay đổi hoặc không hợp lệ. Hãy tải lại rồi xuất lại.",
        ) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Không đọc được dataset trên máy. Hãy thử lại.") from error
    return Response(
        json.dumps(value, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="firstframe-reviewed-dataset.json"'},
    )


async def read_bundle(request: Request, *, with_resolutions: bool = False):
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_BUNDLE_BYTES + (512 * 1024 if with_resolutions else 0):
            raise HTTPException(413, "Gói vượt giới hạn 25 MiB.")
        content.extend(chunk)
    try:
        value = json.loads(content.decode("utf-8"))
        if with_resolutions and isinstance(value, dict) and "bundle" in value:
            if set(value) != {"bundle", "resolutions"}:
                raise ValueError("Yêu cầu nhập có trường không được hỗ trợ.")
            choices = TypeAdapter(dict[str, ConflictChoice]).validate_python(
                value["resolutions"], strict=True
            )
            if len(choices) > 1000:
                raise ValueError("Quá nhiều lựa chọn xung đột.")
            return validate_bundle(value["bundle"]), choices
        bundle = validate_bundle(value)
        return (bundle, {}) if with_resolutions else bundle
    except ValidationError as error:
        raise HTTPException(
            422, "Gói không đúng định dạng, schema hoặc lịch sử output. Hãy xuất lại từ FirstFrame."
        ) from error
    except (ValueError, RecursionError) as error:
        raise HTTPException(
            422,
            str(error) if isinstance(error, ValueError) else "Cấu trúc gói quá sâu, không hợp lệ.",
        ) from error


@router.post("/preview")
async def preview_bundle(request: Request):
    bundle = await read_bundle(request)
    try:
        return inspect_bundle(bundle)
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Không kiểm tra được dataset local. Hãy thử lại.") from error


@router.post("/import")
async def upload_bundle(request: Request):
    bundle, resolutions = await read_bundle(request, with_resolutions=True)
    try:
        return import_bundle(bundle, resolutions)
    except ValueError as error:
        raise HTTPException(
            422, "Không thể bảo toàn dữ liệu local hiện tại: " + str(error)
        ) from error
    except ReviewConflict as error:
        raise HTTPException(409, str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(
            503, "Không nhập được gói. Giao dịch đã được hoàn tác; hãy thử lại."
        ) from error


@router.post("/compare")
async def compare_import_conflict(request: Request, run_id: str):
    bundle = await read_bundle(request)
    try:
        return compare_conflict(bundle, run_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Không đọc được dữ liệu để so sánh.") from error
