"""One offline direct-description request per saved scene; no runtime edits or retries."""
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient
from app.api.routes import projects
from app.api.schemas.projects import AuthorContext
from app.api.schemas.scenes import Scene
from app.application.project_store import ProjectStore
from app.infrastructure.scene_images import MODEL, PARAMETERS, SKETCH_PROMPT_VERSION, sketch_prompt
from app.main import create_app

PRIVATE = ROOT / "backend/.data/scene-sketch-direct-two-scenes-2026-10-27"
projects.get_project_store = lambda: ProjectStore(PRIVATE / "projects.sqlite3")
SAMPLES = ROOT / "docs/evaluations/scene-sketch-runtime-prompt-2026-10-27/samples.json"
FILES = ["backend/app/infrastructure/scene_images.py", "backend/app/api/routes/scene_sketches.py",
         "backend/app/api/schemas/projects.py", "backend/app/api/schemas/scenes.py", "backend/requirements-image.txt",
         str(Path(__file__).resolve().relative_to(ROOT))]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temporary.replace(path)


def direct_prompt(scene, context, baseline_prompt):
    # Only this two-case offline experiment: preserve supplied field text without cue sentences or quote wrappers.
    values = [scene.action, scene.characters, scene.location, scene.time,
              *scene.staging_choices.values(), scene.goal, scene.purpose, scene.viewer_intent,
              context.idea, *[d.answer for d in context.clarifications], scene.keep_or_avoid, *context.constraints]
    sentences = [v if v.rstrip().endswith((".", "!", "?")) else v+"." for v in values if v.strip()]
    return "\n\n".join([baseline_prompt.split("\n\n")[0], " ".join(sentences),
        "Do not invent an event or resolve an open ending. Only pencil strokes on white paper: "
        "no photograph, text, labels, captions, speech bubbles or panel grid."])


def prepare():
    assert not (HERE/"manifest.json").exists() and not PRIVATE.exists(), "Do not replace an earlier trial"
    previous=HERE.parent/"scene-sketch-runtime-mflux-two-scenes-2026-10-27"
    cases=json.loads((previous/"inputs.json").read_text())
    from app.api.schemas.projects import ProjectResponse
    for case in cases:
        project=ProjectResponse.model_validate(case["project"])
        projects.get_project_store().create(project.model_dump(mode="json",exclude_computed_fields=True))
        outline=project.scene_outline
        baseline=case["prompt"]
        assert sketch_prompt(outline.scenes[0],outline.source.context,"")==baseline
        case["baseline_prompt"]=baseline
        case["prompt"]=direct_prompt(outline.scenes[0],outline.source.context,baseline)
        (HERE/(case["name"]+".prompt.txt")).write_text(case["prompt"],encoding="utf-8")
    write(HERE/"inputs.json",cases)
    kept=json.loads((previous/"manifest.json").read_text())["preserved_files"]
    assert all(sha(ROOT/n)==h for n,h in kept.items())
    write(HERE/"manifest.json",{"frozen_at":datetime.now(UTC).isoformat(),"model":MODEL,"parameters":PARAMETERS,
        "prompt_version":SKETCH_PROMPT_VERSION,"experiment_prompt_id":"direct-unquoted-v1",
        "max_requests":2,"requests_per_scene":1,"retries":0,"paid_api":False,
        "private_store":str(PRIVATE.relative_to(ROOT)),"runtime_prompt_override":True,
        "samples_sha256":sha(SAMPLES),"inputs_sha256":sha(HERE/"inputs.json"),"criteria_sha256":sha(HERE/"criteria.json"),
        "hashes":{n:sha(ROOT/n) for n in FILES},"preserved_files":kept,
        "prompts":{c["name"]:sha(HERE/(c["name"]+".prompt.txt")) for c in cases},
        "baseline_hashes":{n:sha(previous/n) for n in ("inputs.json","results.json","results/repair-workshop.png","results/empty-platform.png")}})
    print("FROZEN two same source scenes, direct unquoted prompts and unchanged criteria; zero model calls",flush=True)


def check():
    m=json.loads((HERE/"manifest.json").read_text())
    assert m["parameters"]==PARAMETERS and m["prompt_version"]==SKETCH_PROMPT_VERSION
    assert sha(SAMPLES)==m["samples_sha256"] and sha(HERE/"inputs.json")==m["inputs_sha256"]
    assert sha(HERE/"criteria.json")==m["criteria_sha256"]
    baseline=HERE.parent/"scene-sketch-runtime-mflux-two-scenes-2026-10-27"
    assert all(sha(baseline/n)==h for n,h in m["baseline_hashes"].items())
    assert all(sha(ROOT/n)==h for n,h in {**m["hashes"],**m["preserved_files"]}.items())
    assert all(sha(HERE/(n+".prompt.txt"))==h for n,h in m["prompts"].items())
    cases=json.loads((HERE/"inputs.json").read_text());assert len(cases)==2
    for case in cases:
        outline=case["project"]["scene_outline"]
        scene=Scene.model_validate(outline["scenes"][0]);context=AuthorContext.model_validate(outline["source"]["context"])
        assert sketch_prompt(scene,context,"")==case["baseline_prompt"]
        assert direct_prompt(scene,context,case["baseline_prompt"])==case["prompt"]
    return m


def run():
    check();destination=HERE/"results";destination.mkdir(exist_ok=False)
    os.environ["SCENE_IMAGE_PROVIDER"]="mflux"
    cases=json.loads((HERE/"inputs.json").read_text());records=[]
    from app.api.routes import scene_sketches
    def candidate_prompt(scene,context,instructions):
        case=next(c for c in cases if c["request"]["scene_id"]==scene.id)
        assert scene.model_dump()==case["project"]["scene_outline"]["scenes"][0]
        assert context.model_dump()==case["project"]["scene_outline"]["source"]["context"] and instructions==""
        return case["prompt"]
    scene_sketches.sketch_prompt=candidate_prompt
    with TestClient(create_app(),raise_server_exceptions=False) as client:
        for case in cases:
            check();project=case["project"];url=f"/api/projects/{project['id']}"
            current=client.get(url).json();assert current==project
            body={**case["request"],"revision":current["revision"]}
            record={"name":case["name"],"started_at":datetime.now(UTC).isoformat(),"request":body,"status":"running","experiment_prompt_id":"direct-unquoted-v1"}
            write(destination/(case["name"]+".json"),record)
            started=time.monotonic()
            try:
                response=client.post(url+"/scene-sketches",json=body)
                record.update(http_status=response.status_code,api_seconds=round(time.monotonic()-started,3))
                try:record["response"]=response.json()
                except ValueError:record["response_text"]=response.text
                current=client.get(url).json()
                item=next((s for s in current["scene_sketches"] if s["id"]==body["request_id"]),None)
                record["sketch"]=item;record["status"]=item["status"] if item else "missing_checkpoint"
                record["checks"]={"source_unchanged":current["scene_outline"]==project["scene_outline"],
                    "story_unchanged":current["draft"]==project["draft"],"no_automatic_selection":not current["selected_scene_sketches"],
                    "prompt_exact_match":bool(item and item["prompt"]==case["prompt"]),
                    "version_matches":bool(item and item["prompt_version"]==SKETCH_PROMPT_VERSION)}
                if item and item["status"]=="ready":
                    image=client.get(f"{url}/scene-sketches/{item['id']}/image")
                    assert image.status_code==200
                    image_path=destination/(case["name"]+".png");image_path.write_bytes(image.content)
                    record["image_sha256"]=sha(image_path)
                reopened=TestClient(create_app()).get(url).json()
                record["checks"]["reload_identical"]=reopened==current
            except Exception as error:
                record.update(status="runner_error",error_type=type(error).__name__,error=str(error),
                              api_seconds=round(time.monotonic()-started,3))
            records.append(record);write(destination/(case["name"]+".json"),record);write(HERE/"results.json",records)
            print(json.dumps({k:record.get(k) for k in ("name","status","http_status","api_seconds","error_type")}),flush=True)
    write(HERE/"audit.json",{"freeze_verified":bool(check()),"requests":len(records),"retries":0,
        "results_sha256":sha(HERE/"results.json"),"images":{p.name:sha(p) for p in destination.glob("*.png")}})


if __name__=="__main__":
    {"--prepare":prepare,"--run":run,"--check":check}[sys.argv[1]]()
