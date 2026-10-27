"""One real runtime image request per frozen scene; no prompt override or retries."""
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

PRIVATE = ROOT / "backend/.data/scene-sketch-runtime-two-scenes-2026-10-27"
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


def prepare():
    assert not (HERE/"manifest.json").exists() and not PRIVATE.exists(), "Do not replace an earlier trial"
    samples = json.loads(SAMPLES.read_text())
    cases = []
    with TestClient(create_app()) as client:
        for name in ("repair-workshop", "empty-platform"):
            sample = next(s for s in samples if s["name"] == name)
            scene = Scene.model_validate(sample["scene"])
            context = AuthorContext.model_validate(sample["author_context"])
            prompt = sketch_prompt(scene, context, "")
            assert prompt == sample["prompt"] and sample["prompt_version"] == SKETCH_PROMPT_VERSION
            project = client.post("/api/projects").json(); url=f"/api/projects/{project['id']}"
            response = client.put(url, json={"revision":project["revision"],"title":name,
                "idea":context.idea,"constraints":context.constraints,"answers":[],"response_language":"en",
                "draft":{"title":name,"logline":context.idea,"sections":[
                    {"title":"A moment", "purpose":"Preserve the source constraints.", "content":scene.action}]}})
            assert response.status_code==200,response.text
            project=response.json()
            response=client.post(url+"/scene-outline",json={"revision":project["revision"],"source_version_id":"current"})
            assert response.status_code==200,response.text
            project=response.json()
            response=client.put(url,json={**{k:project[k] for k in ("revision","title","idea","constraints","answers","draft","response_language")},
                "scene_outline":{"id":project["scene_outline"]["id"],"version":project["scene_outline"]["version"],"scenes":[scene.model_dump()]}})
            assert response.status_code==200,response.text
            project=response.json()
            assert project["scene_outline"]["source"]["context"]==sample["author_context"]
            cases.append({"name":name,"project":project,"prompt":prompt,
                "request":{"request_id":str(uuid4()),"scene_id":scene.id,"instructions":""}})
            (HERE/(name+".prompt.txt")).write_text(prompt,encoding="utf-8")
    write(HERE/"inputs.json",cases)
    kept=["docs/plans/m2-scene-staging.md","docs/plans/harness-improvement.md",
          "docs/plans/vietnam-first-screenplay-mvp.md","docs/roadmap.md","backend/.env"]
    kept += [str(p.relative_to(ROOT)) for p in (ROOT/"frontend/app/prototype").rglob("*") if p.is_file()]
    write(HERE/"manifest.json",{"frozen_at":datetime.now(UTC).isoformat(),"model":MODEL,"parameters":PARAMETERS,
        "prompt_version":SKETCH_PROMPT_VERSION,"max_requests":2,"requests_per_scene":1,"retries":0,"paid_api":False,
        "private_store":str(PRIVATE.relative_to(ROOT)),"runtime_prompt_override":False,
        "samples_sha256":sha(SAMPLES),"inputs_sha256":sha(HERE/"inputs.json"),"criteria_sha256":sha(HERE/"criteria.json"),
        "hashes":{n:sha(ROOT/n) for n in FILES},"preserved_files":{n:sha(ROOT/n) for n in kept},
        "prompts":{c["name"]:sha(HERE/(c["name"]+".prompt.txt")) for c in cases}})
    print("FROZEN two saved scenes + actual runtime prompts + criteria; zero model calls",flush=True)


def check():
    m=json.loads((HERE/"manifest.json").read_text())
    assert m["parameters"]==PARAMETERS and m["prompt_version"]==SKETCH_PROMPT_VERSION
    assert sha(SAMPLES)==m["samples_sha256"] and sha(HERE/"inputs.json")==m["inputs_sha256"]
    assert sha(HERE/"criteria.json")==m["criteria_sha256"]
    assert all(sha(ROOT/n)==h for n,h in {**m["hashes"],**m["preserved_files"]}.items())
    assert all(sha(HERE/(n+".prompt.txt"))==h for n,h in m["prompts"].items())
    cases=json.loads((HERE/"inputs.json").read_text());assert len(cases)==2
    for case in cases:
        outline=case["project"]["scene_outline"]
        assert sketch_prompt(Scene.model_validate(outline["scenes"][0]),AuthorContext.model_validate(outline["source"]["context"]),"")==case["prompt"]
    return m


def run():
    check();destination=HERE/"results";destination.mkdir(exist_ok=False)
    os.environ["SCENE_IMAGE_PROVIDER"]="mflux"
    cases=json.loads((HERE/"inputs.json").read_text());records=[]
    with TestClient(create_app(),raise_server_exceptions=False) as client:
        for case in cases:
            check();project=case["project"];url=f"/api/projects/{project['id']}"
            current=client.get(url).json();assert current==project
            body={**case["request"],"revision":current["revision"]}
            record={"name":case["name"],"started_at":datetime.now(UTC).isoformat(),"request":body,"status":"running"}
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
