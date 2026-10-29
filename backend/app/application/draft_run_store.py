"""Durable runs share the project database so adoption is atomic."""
import json
from hashlib import sha256
from datetime import UTC, datetime
from app.application.project_store import ProjectStore, ProjectConflict, ProjectNotFound

ACTIVE = ("running", "needs_input", "partial", "failed", "interrupted")

def now():
    return datetime.now(UTC).isoformat()


def source_key(project):
    return sha256(json.dumps({"brief": project.content_key(),
        "draft_provenance": {k:v.model_dump() for k,v in project.draft_provenance.items()},
        "outline": project.scene_outline.model_dump() if project.scene_outline else None,
        "screenplay": project.screenplay.model_dump() if project.screenplay else None,
    }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class DraftRunStore(ProjectStore):
    def connect(self):
        return self._connect()

    def setup(self, c):
        c.execute("CREATE TABLE IF NOT EXISTS draft_runs (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, data TEXT NOT NULL)")

    def rows(self, project_id):
        with self.connect() as c:
            self.setup(c)
            return [json.loads(r[0]) for r in c.execute("SELECT data FROM draft_runs WHERE project_id=? ORDER BY rowid DESC", (project_id,))]

    def get_run(self, project_id, run_id):
        with self.connect() as c:
            self.setup(c)
            row = c.execute("SELECT data FROM draft_runs WHERE id=? AND project_id=?", (run_id, project_id)).fetchone()
        if row is None:
            raise ProjectNotFound
        return json.loads(row[0])

    def create_run(self, project_id, run_id, revision, config, owner):
        with self.connect() as c:
            self.setup(c)
            c.execute("BEGIN IMMEDIATE")
            old = c.execute("SELECT data FROM draft_runs WHERE id=?", (run_id,)).fetchone()
            if old:
                run = json.loads(old[0])
                if run["project_id"] != project_id or run["source_revision"] != revision:
                    raise ProjectConflict
                return run, False
            row = c.execute("SELECT data FROM projects WHERE id=?", (project_id,)).fetchone()
            if row is None:
                raise ProjectNotFound
            from app.api.schemas.projects import ProjectResponse
            project = ProjectResponse.model_validate_json(row[0])
            if project.revision != revision:
                raise ProjectConflict
            runs = [json.loads(r[0]) for r in c.execute("SELECT data FROM draft_runs WHERE project_id=?", (project_id,))]
            if any(r["status"] in ACTIVE for r in runs) or len(runs) >= 100:
                raise ProjectConflict
            # Start from the author's brief, never recycle an old generated artifact.
            candidate = project.model_copy(deep=True)
            candidate.draft = candidate.scene_outline = candidate.screenplay = None
            candidate.draft_provenance = {}
            candidate.feedback = candidate.feedback_source = candidate.reviewed_content = None
            candidate.screenplay_reviews = []
            run = dict(id=run_id, project_id=project_id, source_revision=revision,
                source_content=source_key(project), config=config, owner=owner,
                status="running", step="prepare", sending=False, cancel_requested=False,
                created_at=now(), updated_at=now(), candidate_revision=0,
                completed_scenes=0, total_scenes=0, error=None, review_error=None,
                adopted_revision=None, calls=[], candidate=candidate.model_dump(mode="json"), original=None)
            c.execute("INSERT INTO draft_runs VALUES (?,?,?)", (run_id, project_id, json.dumps(run, ensure_ascii=False)))
            return run, True

    def change(self, project_id, run_id, fn):
        with self.connect() as c:
            self.setup(c)
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT data FROM draft_runs WHERE id=? AND project_id=?", (run_id, project_id)).fetchone()
            if row is None:
                raise ProjectNotFound
            run = json.loads(row[0])
            fn(run)
            run["updated_at"] = now()
            c.execute("UPDATE draft_runs SET data=? WHERE id=?", (json.dumps(run, ensure_ascii=False), run_id))
            return run

    def recover(self, owner):
        with self.connect() as c:
            self.setup(c)
            for run_id, data in c.execute("SELECT id,data FROM draft_runs").fetchall():
                r = json.loads(data)
                if r["status"] == "running" and r["owner"] != owner:
                    r["status"] = "interrupted"
                    r["error"] = "Tiến trình đã dừng. Phần hoàn tất vẫn giữ; chỉ tiếp tục bước chưa gửi AI."
                    c.execute("UPDATE draft_runs SET data=? WHERE id=?", (json.dumps(r, ensure_ascii=False), run_id))

    def adopt(self, project_id, run_id, revision, candidate_revision):
        from app.api.schemas.projects import ProjectResponse
        from app.api.routes.projects import add_version, archive_scene_outline, archive_screenplay, archive_clarifications
        with self.connect() as c:
            self.setup(c)
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT data FROM draft_runs WHERE id=? AND project_id=?", (run_id, project_id)).fetchone()
            raw = c.execute("SELECT data FROM projects WHERE id=?", (project_id,)).fetchone()
            if row is None or raw is None:
                raise ProjectNotFound
            run, p = json.loads(row[0]), ProjectResponse.model_validate_json(raw[0])
            if run["adopted_revision"] is not None:
                return p
            if (p.revision != revision or source_key(p) != run["source_content"]
                or run["candidate_revision"] != candidate_revision or run["status"] not in ("ready", "partial")
                or run["cancel_requested"]):
                raise ProjectConflict
            draft = ProjectResponse.model_validate(run["candidate"])
            if not draft.screenplay or not any(s.blocks for s in draft.screenplay.scenes):
                raise ProjectConflict
            add_version(p)
            if (p.analysis, p.answers, p.clarifications) != (draft.analysis, draft.answers, draft.clarifications):
                archive_clarifications(p)
            archive_scene_outline(p)
            archive_screenplay(p)
            for key in ("analysis", "answers", "clarifications", "draft", "draft_provenance", "scene_outline", "screenplay"):
                setattr(p, key, getattr(draft, key))
            p.screenplay_reviews.extend(draft.screenplay_reviews)
            p.feedback = p.feedback_source = p.reviewed_content = None
            p.edit_sessions = {}
            p.revision += 1
            p.updated_at = now()
            run["adopted_revision"] = p.revision
            c.execute("UPDATE projects SET revision=?,data=? WHERE id=?", (p.revision, p.model_dump_json(exclude_computed_fields=True), project_id))
            c.execute("UPDATE draft_runs SET data=? WHERE id=?", (json.dumps(run, ensure_ascii=False), run_id))
            return p
