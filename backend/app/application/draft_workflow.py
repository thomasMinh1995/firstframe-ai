"""Sequential, checkpointed drafting for the local single-process application."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from app.api.schemas.projects import (ProjectResponse, StoryDraft, ScenePlanSource, SceneOutline,
    Screenplay, SceneProposal, ScreenplayProposal, ScreenplayReview)
from app.api.schemas.story import AnalysisResponse
from app.api.schemas.screenplays import ScriptScene
from app.api.schemas.provenance import TextProvenance
from app.application.ai_provider import StructuredResult
from app.application.provenance import ai_draft, scene_fields
from app.application.scene_suggestions import suggest_scenes
from app.application.screenplay_writing import write_scene
from app.application.screenplay_review import review_scene, review_sources
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

    def checkpoint(step, **updates):
        def keep(r):
            r.update(candidate=p.model_dump(mode="json"), step=step, sending=False, **updates)
            r["candidate_revision"] += 1
        return store.change(project_id, run_id, keep)

    def cancelled():
        return store.get_run(project_id, run_id)["cancel_requested"]

    try:
        service = create_story_generation_service(wrapped[0])
        if p.analysis is None:
            checkpoint("clarify")
            reasoning = service.analyze(
                p.idea, _constraints(p), answers=p.creator_answers(), response_language=p.response_language)
            p.analysis = AnalysisResponse(artifact_id=reasoning.metadata.artifact_id,
                summary=next((n.content for n in reasoning.notes if n.label == "Analysis summary"), ""),
                missing_information=list(reasoning.open_questions), ai_suggestions=list(getattr(reasoning, "ai_suggestions", ())))
            p.answers = [""] * len(p.analysis.missing_information)
            checkpoint("plan")
            if p.analysis.missing_information and not cancelled():
                store.change(project_id, run_id, lambda r: r.update(status="needs_input"))
                return
        if cancelled():
            return
        if p.draft is None:
            checkpoint("plan")
            def planned(plan):
                p.draft = StoryDraft(title=plan.title or "Phim ngắn", logline=plan.logline or "",
                    sections=[dict(title=s.title, purpose=s.purpose, content=s.content) for s in plan.sections])
                p.draft_provenance = ai_draft(p.draft)
                checkpoint("plan_review")
            try:
                service.plan(p.idea, p.creator_answers(), _constraints(p), p.response_language,
                    on_planned=planned, structured_review=True,
                    pending_questions=tuple(q for q, a in zip(p.analysis.missing_information, p.answers) if not a.strip()))
            except Exception as error:
                if p.draft is None:
                    raise
                store.change(project_id, run_id, lambda r: r.update(review_error=str(error)))
            checkpoint("outline")
        if cancelled():
            return
        if p.scene_outline is None:
            p.scene_outline = SceneOutline(id=str(uuid4()), version=1, scenes=[], source=ScenePlanSource(
                id=str(uuid4()), project_revision=run["source_revision"], version_id="current",
                draft=p.draft, draft_provenance=p.draft_provenance, context=p.author_context,
                response_language=p.response_language))
            checkpoint("outline")
        if not p.scene_outline.scenes:
            proposal = suggest_scenes(SceneProposal(id=str(uuid4()), created_at=now(),
                source_revision=p.revision, source_content=p.content_key(), source_outline=p.scene_outline,
                mode="list", instructions="Create 2 to 6 concise scenes. Automatic drafting supports at most 6 scenes."), wrapped[1])
            if len(proposal.scenes) > MAX_AUTO_SCENES:
                raise ValueError("Tạo tự động hỗ trợ tối đa 6 cảnh; không cắt bỏ cảnh. Hãy giữ story plan và tạo lượt mới ngắn hơn; bạn cũng có thể tiếp tục tự viết.")
            p.scene_outline.scenes = proposal.scenes
            p.scene_outline.provenance = {k: TextProvenance(origin="ai_proposal") for k in scene_fields(proposal.scenes)}
            checkpoint("write", total_scenes=len(proposal.scenes))
        if p.screenplay is None:
            p.screenplay = Screenplay(id=str(uuid4()), version=1, source_revision=p.revision,
                source_outline=p.scene_outline.model_copy(deep=True),
                scenes=[ScriptScene(id=str(uuid4()), source_scene_id=s.id, heading=s.title) for s in p.scene_outline.scenes])
            checkpoint("write")
        for index, scene in enumerate(p.screenplay.scenes):
            if scene.blocks:
                continue
            if cancelled():
                return
            checkpoint("write")
            result = write_scene(ScreenplayProposal(id=str(uuid4()), created_at=now(),
                source_revision=p.revision, source_content=p.content_key(), source_screenplay=p.screenplay.model_copy(deep=True),
                source_outline=p.scene_outline, target_scene_id=scene.id, prompt_version="screenplay-scene-v1"), wrapped[2])
            p.screenplay.scenes[index] = result.scene
            p.screenplay.provenance.update({k: TextProvenance(origin="ai_proposal") for k in scene_fields([result.scene], True)})
            checkpoint("write", completed_scenes=sum(bool(s.blocks) for s in p.screenplay.scenes))
        # Text is durable and readable before optional reviews begin.
        checkpoint("review")
        if not cancelled():
            for scene in p.screenplay.scenes:
                if cancelled():
                    break
                if any(r.target_scene_id == scene.id for r in p.screenplay_reviews):
                    continue
                try:
                    review = ScreenplayReview(id=str(uuid4()), created_at=now(), source_revision=p.revision,
                        source_content=p.content_key(), source_screenplay=p.screenplay.model_copy(deep=True),
                        source_outline=p.scene_outline, target_scene_id=scene.id, prompt_version="screenplay-review-v5-provenance")
                    review.sources = review_sources(review)
                    p.screenplay_reviews.append(review_scene(review, wrapped[3]))
                    checkpoint("review")
                except Exception as error:
                    store.change(project_id, run_id, lambda r: r.update(review_error=str(error)))
                    break
        def finish(r):
            r.update(status="cancelled" if r["cancel_requested"] else "ready", step="done", sending=False)
            r["original"] = r["original"] or r["candidate"]
        store.change(project_id, run_id, finish)
    except Exception as error:
        def failed(r):
            uncertain = any("output" not in c for c in r["calls"])
            r.update(status="cancelled" if r["cancel_requested"] else "interrupted" if uncertain else "partial" if p.draft else "failed",
                error=str(error), sending=uncertain)
        store.change(project_id, run_id, failed)
    finally:
        if cancelled():
            store.change(project_id, run_id, lambda r: r.update(status="cancelled"))


def _constraints(p):
    from app.core.artifacts import Constraint
    return tuple(Constraint(name=f"constraint-{i}", value=v) for i, v in enumerate(p.constraints))
