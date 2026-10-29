"""Sequential, checkpointed drafting for the local single-process application."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from pydantic import TypeAdapter
from app.core.artifacts import EvaluationArtifact
from app.application import draft_progress as progress

from app.api.schemas.projects import (ProjectResponse, StoryDraft, ScenePlanSource, SceneOutline,
    Screenplay, SceneProposal, ScreenplayProposal, ScreenplayReview)
from app.api.schemas.story import AnalysisResponse
from app.api.schemas.screenplays import ScriptScene
from app.api.schemas.provenance import TextProvenance
from app.application.ai_provider import StructuredResult
from app.application.provenance import ai_draft, scene_fields
from app.application.scene_suggestions import suggest_scenes
from app.application.screenplay_writing import write_scene
from app.application.screenplay_review import PROMPT_VERSION as REVIEW_PROMPT_VERSION, review_scene, review_sources
from app.application.workflow import create_story_generation_service
from app.application.draft_run_store import now

OWNER = str(uuid4())
POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="draft-run")
MAX_AUTO_SCENES = 6


def configuration(providers):
    prompts = Path(__file__).resolve().parents[3] / "domains/short-film/prompts"
    return {"providers": [asdict(p.metadata) for p in providers],
        "prompts": {str(p.relative_to(prompts)): sha256(p.read_bytes()).hexdigest()
                    for p in sorted(prompts.rglob("*.md"))}, "max_scenes": MAX_AUTO_SCENES}


class RecordedProvider:
    """Reuse a durable received result; never repeat an uncertain model request."""
    def __init__(self, provider, store, project_id, run_id):
        self.provider, self.store, self.project_id, self.run_id = provider, store, project_id, run_id
        self.metadata = provider.metadata

    def request_structured(self, request):
        key = sha256((request.stage + request.instructions + request.input_text
                      + json.dumps(request.response_model.model_json_schema(), sort_keys=True)).encode()).hexdigest()
        run = self.store.get_run(self.project_id, self.run_id)
        old = next((c for c in run["calls"] if c["key"] == key), None)
        if old:
            if "output" not in old:
                raise RuntimeError("Lần gọi AI chưa rõ kết quả; không gửi lại tự động.")
            return StructuredResult(output=request.response_model.model_validate(old["output"]), model=old["model"])
        if run["cancel_requested"]:
            raise InterruptedError("Đã hủy trước khi gửi AI.")
        def begin(r):
            if r["cancel_requested"]:
                raise InterruptedError("Đã hủy trước khi gửi AI.")
            r["sending"] = True
            r["calls"].append({"key": key, "stage": request.stage, "sent_at": now()})
        self.store.change(self.project_id, self.run_id, begin)
        result = self.provider.request_structured(request)
        def received(r):
            call = next(c for c in r["calls"] if c["key"] == key)
            call.update(output=result.output.model_dump(mode="json"), model=result.model)
        self.store.change(self.project_id, self.run_id, received)
        return result


def launch(store, project_id, run_id, providers):
    return POOL.submit(execute, store, project_id, run_id, providers)


def execute(store, project_id, run_id, providers):
    wrapped = [RecordedProvider(p, store, project_id, run_id) for p in providers]
    run = store.get_run(project_id, run_id)
    p = ProjectResponse.model_validate(run["candidate"])

    def checkpoint(step, *, completed=None, active=(), **updates):
        def keep(r):
            progress.ensure_progress(r)
            r.update(candidate=p.model_dump(mode="json"), step=step, sending=False, **updates)
            r["candidate_revision"] += 1
            progress.add_scenes(r, p.screenplay)
            for key, artifact_id in (completed or {}).items():
                progress.complete_item(r, key, artifact_id)
            for key in active:
                progress.update_item(r, key, "running")
        return store.change(project_id, run_id, keep)

    def mark(key, status, error_code=None):
        def keep(r):
            progress.ensure_progress(r)
            progress.update_item(r, key, status, error_code=error_code)
            if key == "plan_review" and status in {"warning", "skipped"}:
                r["review_error"] = "Góp ý story plan chưa hoàn tất sau gián đoạn."
        store.change(project_id, run_id, keep)

    def cancelled():
        return store.get_run(project_id, run_id)["cancel_requested"]

    try:
        service = create_story_generation_service(wrapped[0])
        if p.analysis is None:
            checkpoint("clarify", active=("analysis",))
            reasoning = service.analyze(
                p.idea, _constraints(p), answers=p.creator_answers(), response_language=p.response_language)
            p.analysis = AnalysisResponse(artifact_id=reasoning.metadata.artifact_id,
                summary=next((n.content for n in reasoning.notes if n.label == "Analysis summary"), ""),
                missing_information=list(reasoning.open_questions), ai_suggestions=list(getattr(reasoning, "ai_suggestions", ())))
            p.answers = [""] * len(p.analysis.missing_information)
            checkpoint("plan", completed={"analysis": p.analysis.artifact_id})
            if p.analysis.missing_information and not cancelled():
                def wait_for_author(r):
                    r["status"] = "needs_input"
                    progress.update_item(r, "intent", "needs_input")
                store.change(project_id, run_id, wait_for_author)
                return
        if cancelled():
            return
        def confirmed_intent(r):
            progress.ensure_progress(r)
            progress.complete_item(r, "analysis", p.analysis.artifact_id)
            progress.complete_item(r, "intent", p.analysis.artifact_id)
        store.change(project_id, run_id, confirmed_intent)
        if p.draft is None:
            checkpoint("plan", active=("plan",))
            def planned(plan):
                p.draft = StoryDraft(title=plan.title or "Phim ngắn", logline=plan.logline or "",
                    sections=[dict(title=s.title, purpose=s.purpose, content=s.content) for s in plan.sections])
                p.draft_provenance = ai_draft(p.draft)
                checkpoint("plan_review", completed={"plan": None}, active=("plan_review",))
            try:
                planned_run = service.plan(p.idea, p.creator_answers(), _constraints(p), p.response_language,
                    on_planned=planned, structured_review=True,
                    pending_questions=tuple(q for q, a in zip(p.analysis.missing_information, p.answers) if not a.strip()))
                def save_plan_review(r):
                    r["plan_review_result"] = TypeAdapter(EvaluationArtifact).dump_python(
                        planned_run.evaluation, mode="json")
                    progress.complete_item(r, "plan_review", planned_run.evaluation.metadata.artifact_id)
                store.change(project_id, run_id, save_plan_review)
            except Exception as error:
                if p.draft is None:
                    raise
                def failed_plan_review(r):
                    r["review_error"] = str(error)
                    progress.update_item(r, "plan_review", "cancelled" if r["cancel_requested"] else "warning",
                                         error_code="cancelled" if r["cancel_requested"] else "review_unavailable")
                store.change(project_id, run_id, failed_plan_review)
        else:
            # A restart after the plan checkpoint must not invent a successful critic.
            current = store.get_run(project_id, run_id)
            progress.ensure_progress(current)
            critic = next(i for i in current["workflow_items"] if i["id"] == "plan_review")
            if critic["status"] not in {"completed", "warning", "skipped", "unknown"}:
                calls = [c for c in current["calls"] if c["stage"] == "evaluation"]
                if calls:
                    mark("plan_review", "warning", "unknown_result" if any("output" not in c for c in calls) else "review_unavailable")
                else:
                    mark("plan_review", "skipped", "not_run")
        if cancelled():
            return
        if p.scene_outline is None:
            p.scene_outline = SceneOutline(id=str(uuid4()), version=1, scenes=[], source=ScenePlanSource(
                id=str(uuid4()), project_revision=run["source_revision"], version_id="current",
                draft=p.draft, draft_provenance=p.draft_provenance, context=p.author_context,
                response_language=p.response_language))
            checkpoint("outline")
        if not p.scene_outline.scenes:
            checkpoint("outline", active=("outline",))
            proposal = suggest_scenes(SceneProposal(id=str(uuid4()), created_at=now(),
                source_revision=p.revision, source_content=p.content_key(), source_outline=p.scene_outline,
                mode="list", instructions="Create 2 to 6 concise scenes. Automatic drafting supports at most 6 scenes."), wrapped[1])
            if len(proposal.scenes) > MAX_AUTO_SCENES:
                raise ValueError("Tạo tự động hỗ trợ tối đa 6 cảnh; không cắt bỏ cảnh. Hãy giữ story plan và tạo lượt mới ngắn hơn; bạn cũng có thể tiếp tục tự viết.")
            p.scene_outline.scenes = proposal.scenes
            p.scene_outline.provenance = {k: TextProvenance(origin="ai_proposal") for k in scene_fields(proposal.scenes)}
        if p.screenplay is None:
            p.screenplay = Screenplay(id=str(uuid4()), version=1, source_revision=p.revision,
                source_outline=p.scene_outline.model_copy(deep=True),
                scenes=[ScriptScene(id=str(uuid4()), source_scene_id=s.id, heading=s.title) for s in p.scene_outline.scenes])
            checkpoint("write", completed={"outline": p.scene_outline.id},
                       total_scenes=len(p.scene_outline.scenes))
        for index, scene in enumerate(p.screenplay.scenes):
            if scene.blocks:
                continue
            if cancelled():
                return
            checkpoint("write", active=(f"write:{scene.id}",))
            result = write_scene(ScreenplayProposal(id=str(uuid4()), created_at=now(),
                source_revision=p.revision, source_content=p.content_key(), source_screenplay=p.screenplay.model_copy(deep=True),
                source_outline=p.scene_outline, target_scene_id=scene.id, prompt_version="screenplay-scene-v1"), wrapped[2])
            p.screenplay.scenes[index] = result.scene
            p.screenplay.provenance.update({k: TextProvenance(origin="ai_proposal") for k in scene_fields([result.scene], True)})
            checkpoint("write", completed={f"write:{scene.id}": scene.id},
                       completed_scenes=sum(progress.valid_scene(s) for s in p.screenplay.scenes))
        # Text is durable and readable before optional reviews begin.
        checkpoint("review", completed={"draft": p.screenplay.id})
        if not cancelled():
            mark("review", "running")
            for scene in p.screenplay.scenes:
                if cancelled():
                    break
                saved_review = next((r for r in p.screenplay_reviews if r.target_scene_id == scene.id and r.status == "ready"), None)
                if saved_review:
                    checkpoint("review", completed={f"review_scene:{scene.id}": saved_review.id})
                    continue
                mark(f"review_scene:{scene.id}", "running")
                try:
                    review = ScreenplayReview(id=str(uuid4()), created_at=now(), source_revision=p.revision,
                        source_content=p.content_key(), source_screenplay=p.screenplay.model_copy(deep=True),
                        source_outline=p.scene_outline, target_scene_id=scene.id, prompt_version=REVIEW_PROMPT_VERSION)
                    review.sources = review_sources(review)
                    p.screenplay_reviews.append(review_scene(review, wrapped[3]))
                    checkpoint("review", completed={f"review_scene:{scene.id}": review.id})
                except Exception as error:
                    def failed_review(r):
                        r["review_error"] = str(error)
                        stopped = r["cancel_requested"]
                        status, code = ("cancelled", "cancelled") if stopped else ("warning", "review_unavailable")
                        progress.update_item(r, f"review_scene:{scene.id}", status, error_code=code)
                        progress.update_item(r, "review", status, error_code=code)
                        summary = next(i for i in r["workflow_items"] if i["id"] == "review")
                        for item in summary["children"]:
                            if item["status"] == "pending":
                                progress.update_item(r, item["id"], "skipped", error_code="not_run")
                    store.change(project_id, run_id, failed_review)
                    break
        def finish(r):
            r.update(status="cancelled" if r["cancel_requested"] else "ready", step="done", sending=False)
            r["original"] = r["original"] or r["candidate"]
            summary = next(i for i in r["workflow_items"] if i["id"] == "review")
            if all(i["status"] == "completed" for i in summary["children"]):
                progress.complete_item(r, "review", p.screenplay.id)
            if r["cancel_requested"]:
                progress.end_items(r, "cancelled", "cancelled")
        store.change(project_id, run_id, finish)
    except Exception as error:
        def failed(r):
            uncertain = any("output" not in c for c in r["calls"])
            r.update(status="cancelled" if r["cancel_requested"] else "interrupted" if uncertain else "partial" if p.draft else "failed",
                error=str(error), sending=uncertain)
            progress.end_items(r, "cancelled" if r["cancel_requested"] else "interrupted" if uncertain else "failed",
                               "cancelled" if r["cancel_requested"] else "unknown_result" if uncertain else "provider_error")
        store.change(project_id, run_id, failed)
    finally:
        if cancelled():
            def finish_cancel(r):
                r["status"] = "cancelled"
                progress.end_items(r, "cancelled", "cancelled")
            store.change(project_id, run_id, finish_cancel)


def _constraints(p):
    from app.core.artifacts import Constraint
    return tuple(Constraint(name=f"constraint-{i}", value=v) for i, v in enumerate(p.constraints))
