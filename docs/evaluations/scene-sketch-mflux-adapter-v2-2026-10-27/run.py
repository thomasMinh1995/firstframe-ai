"""Two pre-approved local API calls; no text AI, downloads, retries or author's DB."""
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient
from app.api.routes import projects
from app.application.project_store import ProjectStore
from app.infrastructure.scene_images import PARAMETERS, MODEL, sketch_prompt
from app.main import create_app

PRIVATE = ROOT / "backend/.data/scene-sketch-trial-adapter-v2-2026-10-27"
projects.get_project_store = lambda: ProjectStore(PRIVATE / "projects.sqlite3")
FILES = ["backend/app/infrastructure/scene_images.py", "backend/app/api/routes/scene_sketches.py",
         "backend/app/api/schemas/projects.py", "backend/app/api/schemas/scenes.py", "backend/requirements-image.txt",
         str(Path(__file__).relative_to(ROOT))]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temporary.replace(path)


def prepare():
    assert not (HERE/"manifest.json").exists() and not PRIVATE.exists(), "Never replace a previous trial"
    previous=HERE.parent/"scene-sketch-mflux-2026-10-27"
    inputs=json.loads((previous/"inputs.json").read_text())
    project=inputs["project"]
    projects.get_project_store().create({k:v for k,v in project.items() if k not in (
        "author_context","feedback_is_current","applicable_plan_ids","applicable_scene_proposal_ids",
        "applicable_sketch_ids","scene_source_is_current","scene_handoff")})
    write(HERE/"inputs.json",inputs)
    write(HERE/"manifest.json",{"frozen_at":datetime.now(UTC).isoformat(),"model":MODEL,"parameters":PARAMETERS,
         "calls":2,"retries":0,"paid_api":False,"private_store":str(PRIVATE.relative_to(ROOT)),
         "prior_batch":"scene-sketch-mflux-2026-10-27","new_budget":"User approved 2 additional calls after CLI adapter fix",
         "intent":"Same frozen source, prompt and parameters; adapter fix only. Keep original failures.",
         "hashes":{name:sha(ROOT/name) for name in FILES},"inputs_sha256":sha(HERE/"inputs.json")})
    print("FROZEN two requests, same synthetic scene/instructions/seed/config; no generation yet",flush=True)


def check():
    manifest=json.loads((HERE/"manifest.json").read_text())
    assert manifest["parameters"]==PARAMETERS
    assert all(sha(ROOT/name)==digest for name,digest in manifest["hashes"].items())
    assert sha(HERE/"inputs.json")==manifest["inputs_sha256"]
    return manifest


def run():
    check(); destination=HERE/"results";destination.mkdir(exist_ok=False)
    os.environ["SCENE_IMAGE_PROVIDER"]="mflux"
    inputs=json.loads((HERE/"inputs.json").read_text()); project=inputs["project"]; url=f"/api/projects/{project['id']}"
    records=[]; first_id=None
    with TestClient(create_app()) as client:
        for index,request in enumerate(inputs["requests"]):
            check()
            current=client.get(url).json()
            assert current["scene_outline"]==project["scene_outline"] and current["draft"]==project["draft"]
            write(destination/f"request-{index+1}.json",{**request,"revision":current["revision"]})
            response=client.post(url+"/scene-sketches",json={**request,"revision":current["revision"]})
            current=client.get(url).json(); sketch=next(s for s in current["scene_sketches"] if s["id"]==request["request_id"])
            record={"index":index+1,"http_status":response.status_code,"response":response.json(),"sketch":sketch,
                    "source_unchanged":current["scene_outline"]==project["scene_outline"],"checks":{}}
            if sketch["status"]=="ready":
                image=client.get(f"{url}/scene-sketches/{sketch['id']}/image")
                assert image.status_code==200
                (destination/f"image-{index+1}.png").write_bytes(image.content)
                record["image_sha256"]=sha(destination/f"image-{index+1}.png")
                if index==0:
                    accepted=client.post(f"{url}/scene-sketches/{sketch['id']}/keep",json={"revision":current["revision"]})
                    record["checks"]["keep_status"]=accepted.status_code
                    assert accepted.status_code==200;first_id=sketch["id"]
                else:
                    record["checks"]["new_preview_did_not_replace_first"]=(current["selected_scene_sketches"].get(request["scene_id"])==first_id)
                    discarded=client.post(f"{url}/scene-sketches/{sketch['id']}/discard",json={"revision":current["revision"]})
                    assert discarded.status_code==200
                    record["checks"]["discard_preserved_first"]=(discarded.json()["selected_scene_sketches"].get(request["scene_id"])==first_id)
                reopened=TestClient(create_app()).get(url).json()
                record["checks"]["reopen_kept_first"]=reopened["selected_scene_sketches"].get(request["scene_id"])==first_id
            records.append(record);write(destination/f"result-{index+1}.json",record);write(HERE/"results.json",records)
            print(json.dumps({"index":index+1,"http_status":response.status_code,"status":sketch["status"],"duration_seconds":sketch["duration_seconds"],"error":sketch["error"]}),flush=True)
    write(HERE/"audit.json",{"freeze_verified":bool(check()),"calls":len(records),"retries":0,
         "results_sha256":sha(HERE/"results.json"),"images":{p.name:sha(p) for p in destination.glob("*.png")}})


if __name__=="__main__":
    {"--prepare":prepare,"--run":run,"--check":check}[sys.argv[1]]()
