import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.routes.datasets import get_sample
from app.application.dataset_branches import (
    compare_states,
    digest,
    local_states,
    local_token,
    restore_branch,
    saved_branches,
    state_value,
)
from app.application.dataset_review import ReviewConflict

router = APIRouter(prefix="/api/datasets/samples", tags=["dataset branches"])


class BranchRestore(BaseModel):
    local_token: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.get("/{run_id}/branches")
def list_saved_branches(run_id: str):
    states = local_states(run_id)
    if not states:
        raise HTTPException(404, "Không tìm thấy mẫu local.")
    current_ids = {digest(state_value(state)) for state in states}
    return {
        "local_token": local_token(states),
        "branches": [
            {
                "branch_id": branch.branch_id,
                "source": branch.source,
                "created_at": branch.created_at,
                "fingerprint": branch.fingerprint,
                "history_count": len(branch.history) - 1,
                "status": branch.review.status,
                "feedback": branch.review.feedback,
                "is_current": branch.branch_id in current_ids,
            }
            for branch in saved_branches(run_id)
        ],
    }


@router.get("/{run_id}/branches/{branch_id}")
def compare_saved_branch(run_id: str, branch_id: str):
    states = local_states(run_id)
    branch = next((item for item in saved_branches(run_id) if item.branch_id == branch_id), None)
    if not states or branch is None:
        raise HTTPException(404, "Không tìm thấy nhánh lưu trữ.")
    return {"local_token": local_token(states), "changes": compare_states(states, branch)}


@router.post("/{run_id}/branches/{branch_id}/restore")
def use_saved_branch(run_id: str, branch_id: str, request: BranchRestore):
    try:
        restore_branch(run_id, branch_id, request.local_token)
    except ReviewConflict as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise HTTPException(503, "Không khôi phục được nhánh; giao dịch đã hoàn tác.") from error
    return get_sample(run_id)
