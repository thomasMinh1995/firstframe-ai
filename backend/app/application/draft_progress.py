"""Progress describes saved work; it never schedules model calls."""
from copy import deepcopy
from datetime import UTC, datetime

from app.api.schemas.draft_runs import WorkflowItem
from app.api.schemas.projects import ProjectResponse

BASE = ("analysis", "intent", "plan", "plan_review", "outline", "review", "draft")
TERMINAL = {"completed", "warning", "failed", "interrupted", "cancelled", "skipped"}


def timestamp():
    return datetime.now(UTC).isoformat()


def new_item(kind, scene_id=None):
    return WorkflowItem(
        id=f"{kind}:{scene_id}" if scene_id else kind, kind=kind, scene_id=scene_id,
    ).model_dump(mode="json")


def all_items(run):
    for item in run["workflow_items"]:
        yield item
        yield from item["children"]


def ensure_progress(run):
    if "workflow_items" not in run:
        run.update(progress_version=1, progress_revision=0, workflow_items=legacy_items(run))


def add_scenes(run, script):
    if script is None:
        return
    existing = {i["id"] for i in run["workflow_items"]}
    review = next(i for i in run["workflow_items"] if i["id"] == "review")
    reviews = {i["id"] for i in review["children"]}
    position = next(i for i, item in enumerate(run["workflow_items"]) if item["id"] == "review")
    for scene in script.scenes:
        item = new_item("write", scene.id)
        if item["id"] not in existing:
            run["workflow_items"].insert(position, item)
            position += 1
        item = new_item("review_scene", scene.id)
        if item["id"] not in reviews:
            review["children"].append(item)


def update_item(run, item_id, status, *, result=None, error_code=None, recorded=True):
    item = next(i for i in all_items(run) if i["id"] == item_id)
    if (item["status"], item["result"], item["error_code"]) == (status, result, error_code):
        return
    item.update(status=status, result=result, error_code=error_code)
    if recorded:
        if status == "running" and item["started_at"] is None:
            item["started_at"] = timestamp()
        item["finished_at"] = timestamp() if status in TERMINAL else None


def complete_item(run, item_id, artifact_id=None):
    item = next(i for i in all_items(run) if i["id"] == item_id)
    if item["status"] == "completed" and item["result"] and item["result"]["id"] == artifact_id:
        return
    update_item(run, item_id, "completed", result=result_ref(run, item["kind"], artifact_id))


def result_ref(run, kind, artifact_id=None):
    return {"kind": kind, "id": artifact_id, "candidate_revision": run["candidate_revision"]}


def valid_scene(scene):
    return bool(scene.heading.strip() and scene.blocks and all(
        b.text.strip() and (b.kind != "dialogue" or b.speaker.strip()) for b in scene.blocks
    ))


def legacy_items(run):
    """Read-only evidence projection: do not invent historical success or times."""
    projected = {"workflow_items": [new_item(k) for k in BASE],
                 "candidate_revision": run["candidate_revision"]}
    for item in projected["workflow_items"]:
        item["status"] = "unknown"
    p = ProjectResponse.model_validate(run["candidate"])
    add_scenes(projected, p.screenplay)
    for item in all_items(projected):
        item["status"] = "unknown"
    def known(key, kind, artifact_id=None, status="completed"):
        update_item(projected, key, status,
                    result=result_ref(run, kind, artifact_id) if status == "completed" else None,
                    recorded=False)
    if p.analysis:
        known("analysis", "analysis", p.analysis.artifact_id)
        if run["status"] == "needs_input":
            known("intent", "intent", status="needs_input")
    if p.draft:
        known("plan", "plan")
    if p.scene_outline and p.scene_outline.scenes:
        known("outline", "outline", p.scene_outline.id)
    if p.screenplay:
        for scene in p.screenplay.scenes:
            if valid_scene(scene):
                known(f"write:{scene.id}", "write", scene.id)
        for review in p.screenplay_reviews:
            if review.status == "ready" and any(s.id == review.target_scene_id for s in p.screenplay.scenes):
                known(f"review_scene:{review.target_scene_id}", "review_scene", review.id)
        if run["status"] == "ready" and all(valid_scene(s) for s in p.screenplay.scenes):
            known("draft", "draft", p.screenplay.id)
    return projected["workflow_items"]


def public_progress(run):
    return {
        "progress_version": run.get("progress_version", 0),
        "progress_revision": run.get("progress_revision", 0),
        "workflow_items": deepcopy(run["workflow_items"]) if "workflow_items" in run else legacy_items(run),
    }


def validate_progress(run):
    for item in run["workflow_items"]:
        WorkflowItem.model_validate(item)
    ids = [i["id"] for i in all_items(run)]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate workflow item ID")
    for item in all_items(run):
        if item["status"] == "completed" and item["result"] is None:
            raise ValueError("Completed progress requires a saved result")


def end_items(run, status, code):
    ensure_progress(run)
    for item in list(all_items(run)):
        if item["status"] in {"running", "needs_input"}:
            update_item(run, item["id"], status, error_code=code)
        elif item["status"] == "pending" and status == "cancelled":
            update_item(run, item["id"], "skipped", error_code="not_run")


def candidate_edited(run):
    """Current text may be incomplete even when generation originally succeeded."""
    ensure_progress(run)
    p = ProjectResponse.model_validate(run["candidate"])
    add_scenes(run, p.screenplay)
    if p.draft:
        update_item(run, "plan", "completed", result=result_ref(run, "plan"))
    if p.screenplay:
        for scene in p.screenplay.scenes:
            complete = valid_scene(scene)
            update_item(run, f"write:{scene.id}", "completed" if complete else "needs_input",
                        result=result_ref(run, "write", scene.id) if complete else None,
                        error_code=None if complete else "candidate_incomplete")
        complete = bool(p.screenplay.scenes) and all(valid_scene(s) for s in p.screenplay.scenes)
        update_item(run, "draft", "completed" if complete else "needs_input",
                    result=result_ref(run, "draft", p.screenplay.id) if complete else None,
                    error_code=None if complete else "candidate_incomplete")


def continuation_block(run, config):
    """Same eligibility for polling and the atomic continue claim."""
    if run["adopted_revision"] is not None:
        return "adopted"
    if run["cancel_requested"] or run["status"] == "cancelled":
        return "cancelled"
    if run["status"] not in {"needs_input", "partial", "failed", "interrupted"}:
        return "not_resumable"
    if config is None:
        return "provider_unavailable"
    if config != run["config"]:
        return "configuration_changed"
    if any("output" not in c and c["stage"] in (
        "reasoning", "planning", "scene_generation", "screenplay_generation",
    ) for c in run["calls"]):
        return "unknown_result"
    if run["original"] is not None:
        p = ProjectResponse.model_validate(run["candidate"])
        original = ProjectResponse.model_validate(run["original"])
        if (p.draft, p.screenplay) != (original.draft, original.screenplay):
            return "candidate_edited"
    return None


CONTINUE_MESSAGES = {
    "adopted": "Bản nháp đã được nhận vào không gian viết.",
    "cancelled": "Lượt tạo đã được yêu cầu kết thúc.",
    "not_resumable": "Lượt này không ở trạng thái có thể tiếp tục.",
    "provider_unavailable": "Chưa đọc được cấu hình AI. Phần đã tạo vẫn được giữ.",
    "configuration_changed": "Cấu hình model hoặc prompt đã đổi. Hãy tạo lượt mới; kết quả cũ vẫn được giữ.",
    "unknown_result": "Lần gọi AI chưa rõ kết quả; không gửi lại. Hãy giữ bản đã có hoặc hủy và tạo lượt mới.",
    "candidate_edited": "Bạn đã sửa candidate. Giữ bản này để đọc/nhận; tạo lượt mới nếu muốn AI viết lại theo nguồn khác.",
}
