import sqlite3

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import ValidationError

from app.application.dataset_corrections import validate_corrections
from app.application.dataset_history import output_diff
from app.application.dataset_review import (
    OutputUpdate,
    RestoreUpdate,
    ReviewConflict,
    ReviewStore,
    ReviewUpdate,
    exported_samples,
    fingerprint,
    sample_catalog,
    training_export,
)

router = APIRouter(prefix="/api/datasets", tags=["dataset review"])


@router.get("/samples")
def list_samples():
    return sample_catalog()


@router.get("/training.jsonl")
def download_training():
    return Response(
        training_export(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="approved-training.jsonl"'},
    )


@router.get("/samples/{run_id}")
def get_sample(run_id: str):
    sample = exported_samples().get(run_id)
    if sample is None:
        raise HTTPException(404, "Không tìm thấy mẫu hoặc ID bản ghi bị trùng nội dung.")
    summary = sample_catalog({run_id: sample})[0]
    review = ReviewStore().reviews().get((run_id, fingerprint(sample)))
    return {
        **summary,
        "recording": sample,
        "corrected_outputs": review.corrected_outputs if review else {},
    }


@router.put("/samples/{run_id}/review")
def update_review(run_id: str, update: ReviewUpdate):
    sample = exported_samples().get(run_id)
    if sample is None:
        raise HTTPException(404, "Mẫu không còn tồn tại. Hãy tải lại danh sách.")
    if fingerprint(sample) != update.fingerprint:
        raise HTTPException(409, "Nội dung mẫu đã thay đổi. Hãy tải lại trước khi duyệt.")
    summary = sample_catalog({run_id: sample})[0]
    if update.status == "approved" and not summary["eligible"]:
        raise HTTPException(422, "Chỉ duyệt mẫu đã hoàn tất, hợp lệ; mẫu lỗi chỉ được ghi góp ý.")
    if update.status != "approved" and (update.use_for_demo or update.use_for_training):
        raise HTTPException(422, "Chỉ chọn mẫu tốt đã duyệt cho demo hoặc train.")
    try:
        return ReviewStore().save(run_id, update).model_dump(exclude={"corrected_outputs"})
    except ReviewConflict as error:
        raise HTTPException(409, str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Không lưu được đánh giá trên máy. Hãy thử lại.") from error


@router.put("/samples/{run_id}/output")
def update_output(run_id: str, update: OutputUpdate):
    return persist_output(run_id, update)


def persist_output(run_id: str, update: OutputUpdate, restored_from: int | None = None):
    sample = exported_samples().get(run_id)
    if sample is None:
        raise HTTPException(404, "Không tìm thấy mẫu để sửa.")
    if fingerprint(sample) != update.fingerprint:
        raise HTTPException(409, "Nội dung gốc đã thay đổi. Hãy tải lại mẫu.")
    if not sample_catalog({run_id: sample})[0]["eligible"]:
        raise HTTPException(422, "Chỉ sửa output của mẫu đã hoàn tất, hợp lệ.")
    try:
        update.corrected_outputs = validate_corrections(sample, update.corrected_outputs)
        ReviewStore().save(run_id, update, restored_from=restored_from)
    except ValidationError as error:
        details = "; ".join(
            f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
            for item in error.errors(include_input=False)[:5]
        )
        raise HTTPException(422, f"Output chưa đúng cấu trúc: {details}") from error
    except ReviewConflict as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Không lưu được bản sửa. Hãy thử lại.") from error
    return get_sample(run_id)


def history_source(run_id: str):
    sample = exported_samples().get(run_id)
    if sample is None:
        raise HTTPException(404, "Không tìm thấy mẫu hoặc ID bản ghi bị trùng nội dung.")
    try:
        return sample, ReviewStore().history(run_id, fingerprint(sample))
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Không đọc được lịch sử trên máy. Hãy thử lại.") from error


@router.get("/samples/{run_id}/history")
def get_output_history(run_id: str):
    sample, versions = history_source(run_id)
    return {
        "fingerprint": fingerprint(sample),
        "current_version": versions[-1].version,
        "versions": [version.model_dump(exclude={"corrected_outputs"}) for version in versions],
    }


@router.get("/samples/{run_id}/diff")
def compare_output_versions(
    run_id: str, from_version: int = Query(ge=0), to_version: int = Query(ge=0)
):
    sample, versions = history_source(run_id)
    by_id = {version.version: version for version in versions}
    if from_version not in by_id or to_version not in by_id:
        raise HTTPException(404, "Phiên bản không thuộc lịch sử của mẫu hiện tại.")
    return {
        "fingerprint": fingerprint(sample),
        "from_version": from_version,
        "to_version": to_version,
        "changes": output_diff(sample, by_id[from_version], by_id[to_version]),
    }


@router.post("/samples/{run_id}/restore")
def restore_output_version(run_id: str, update: RestoreUpdate):
    sample, versions = history_source(run_id)
    if fingerprint(sample) != update.fingerprint:
        raise HTTPException(409, "Nội dung gốc đã thay đổi. Hãy tải lại mẫu.")
    target = next((version for version in versions if version.version == update.version), None)
    if target is None:
        raise HTTPException(404, "Không tìm thấy phiên bản cần khôi phục trong mẫu này.")
    return persist_output(
        run_id,
        OutputUpdate(
            revision=update.revision,
            fingerprint=update.fingerprint,
            corrected_outputs=target.corrected_outputs,
        ),
        restored_from=target.version,
    )
