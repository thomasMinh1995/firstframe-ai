import io
import subprocess
from copy import deepcopy
from uuid import uuid4

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from test_projects import project_client, payload  # noqa: F401
from test_scene_outline import begin, scene, update

from app.api.routes import scene_sketches as routes
from app.application.ai_provider import MissingProviderConfigurationError, ProviderTimeoutError, ProviderRequestError
from app.infrastructure.scene_images import MfluxSceneProvider, SceneImageStore, PARAMETERS, MAX_BYTES, SKETCH_PROMPT_VERSION
from app.main import create_app


def png(size=(768,432), format="PNG"):
    output=io.BytesIO(); Image.new("RGB",size,"white").save(output,format=format); return output.getvalue()


class FakeImageProvider:
    model="fake-image"
    parameters=PARAMETERS
    def __init__(self):
        self.requests=[]; self.error=None; self.data=png(); self.hook=lambda:None
    def generate(self,prompt):
        self.requests.append(prompt);self.hook()
        if self.error: raise self.error
        return self.data


@pytest.fixture
def sketches(project_client,monkeypatch):
    client,text=project_client; _,project=begin(client)
    project=client.put(f"/api/projects/{project['id']}",json=update(project,[scene("Lá thư"),scene("Cửa")])).json()
    provider=FakeImageProvider();monkeypatch.setattr(routes,"get_image_provider",lambda:provider)
    return client,provider,project,text


def generate(client,project,request_id=None):
    body={"revision":project["revision"],"request_id":request_id or str(uuid4()),
          "scene_id":project["scene_outline"]["scenes"][0]["id"],"instructions":"Giữ thư chưa mở."}
    return client.post(f"/api/projects/{project['id']}/scene-sketches",json=body),body


def decide(client,project,id,action):
    return client.post(f"/api/projects/{project['id']}/scene-sketches/{id}/{action}",json={"revision":project["revision"]})


def test_preview_keep_regenerate_discard_reload_legacy_and_scope(sketches):
    client,provider,project,text=sketches;url=f"/api/projects/{project['id']}";text_calls=len(text.requests)
    response,body=generate(client,project); assert response.status_code==200,response.text
    ready=response.json(); first=ready["scene_sketches"][-1]
    assert first["source_outline"]==project["scene_outline"] and first["source_content"]
    assert first["asset_id"] and not ready["selected_scene_sketches"]
    assert ready["scene_outline"]==project["scene_outline"] and ready["feedback_source"]==project["feedback_source"]
    assert client.post(url+"/scene-sketches",json=body).status_code==200 and len(provider.requests)==1
    assert first["prompt_version"] == SKETCH_PROMPT_VERSION
    assert first["prompt"] == provider.requests[0]
    assert project["scene_outline"]["scenes"][0]["action"] in first["prompt"]
    assert '"scene":' not in first["prompt"] and "scene_proposals" not in first["prompt"]
    assert "Quoted passages" not in first["prompt"] and "Show the visible action described here" not in first["prompt"]
    kept=decide(client,ready,first["id"],"keep").json()
    assert kept["selected_scene_sketches"]=={body["scene_id"]:first["id"]}
    second=generate(client,kept)[0].json();assert second["selected_scene_sketches"]==kept["selected_scene_sketches"]
    dropped=decide(client,second,second["scene_sketches"][-1]["id"],"discard").json()
    assert dropped["selected_scene_sketches"]==kept["selected_scene_sketches"]
    legacy=client.put(url,json={**payload(dropped),"title":"Tên tác giả"}).json()
    assert legacy["scene_sketches"]==dropped["scene_sketches"]
    assert legacy["scene_handoff"]["scenes"]==project["scene_handoff"]["scenes"]
    assert TestClient(create_app()).get(url).json()["selected_scene_sketches"]==kept["selected_scene_sketches"]
    image=client.get(f"{url}/scene-sketches/{first['id']}/image")
    assert image.status_code==200 and image.headers["content-type"]=="image/png"
    assert image.headers["x-content-type-options"]=="nosniff" and len(image.content)<MAX_BYTES
    other=client.post("/api/projects").json()
    assert client.get(f"/api/projects/{other['id']}/scene-sketches/{first['id']}/image").status_code==404
    assert client.get(url+"/scene-sketches/../../image").status_code!=200
    assert client.put(url,json={**payload(legacy),"selected_scene_sketches":kept["selected_scene_sketches"]}).status_code==422
    assert len(text.requests)==text_calls


def test_source_changed_while_waiting_cannot_keep_and_never_overwrites(sketches):
    client,provider,project,_=sketches;url=f"/api/projects/{project['id']}"
    ready=generate(client,project)[0].json();first=ready["scene_sketches"][-1]
    kept=decide(client,ready,first["id"],"keep").json()
    def edit():
        current=client.get(url).json(); scenes=deepcopy(current["scene_outline"]["scenes"])
        scenes[0]["action"]="Tác giả vừa sửa khi ảnh đang chạy."
        assert client.put(url,json=update(current,scenes)).status_code==200
    provider.hook=edit
    late=generate(client,kept)[0].json();second=late["scene_sketches"][-1]
    assert late["scene_outline"]["scenes"][0]["action"]=="Tác giả vừa sửa khi ảnh đang chạy."
    assert not late["applicable_sketch_ids"] and late["selected_scene_sketches"]==kept["selected_scene_sketches"]
    assert decide(client,late,second["id"],"keep").status_code==409
    assert client.get(url).json()["selected_scene_sketches"]==kept["selected_scene_sketches"]


def test_pending_discard_late_result_stays_discarded_and_no_retry(sketches):
    client,provider,project,_=sketches;url=f"/api/projects/{project['id']}";rid=str(uuid4())
    def discard():
        pending=client.get(url).json()
        assert generate(client,pending)[0].status_code==409
        assert decide(client,pending,rid,"discard").status_code==200
    provider.hook=discard
    response,body=generate(client,project,rid);assert response.status_code==200,response.text
    latest=response.json();assert latest["scene_sketches"][-1]["status"]=="discarded"
    assert decide(client,latest,rid,"keep").status_code==409
    assert client.post(url+"/scene-sketches",json=body).status_code==200 and len(provider.requests)==1
    body["instructions"]="Khác";assert client.post(url+"/scene-sketches",json=body).status_code==409


@pytest.mark.parametrize("data",[b"<svg onload='evil()'/>",png(format="JPEG"),png((10,10)),png()[:50],b"x"*(MAX_BYTES+1)])
def test_invalid_file_rejected_no_binary_in_project_or_text_loss(sketches,data):
    client,provider,project,_=sketches;provider.data=data
    response,_=generate(client,project);assert response.status_code==502,response.text
    latest=client.get(f"/api/projects/{project['id']}").json();item=latest["scene_sketches"][-1]
    assert item["status"]=="failed" and item["asset_id"] is None and item["diagnostic"]
    assert latest["scene_outline"]==project["scene_outline"] and not latest["selected_scene_sketches"]


@pytest.mark.parametrize("error,status",[(MissingProviderConfigurationError("missing"),503),(ProviderTimeoutError("timeout"),504),(OSError("disk full"),502)])
def test_failure_keeps_previous_image_and_manual_work(sketches,error,status):
    client,provider,project,_=sketches
    ready=generate(client,project)[0].json();first=ready["scene_sketches"][-1]
    kept=decide(client,ready,first["id"],"keep").json();provider.error=error
    assert generate(client,kept)[0].status_code==status
    url=f"/api/projects/{project['id']}";latest=client.get(url).json()
    assert latest["selected_scene_sketches"]==kept["selected_scene_sketches"]
    assert latest["scene_sketches"][-1]["status"]=="failed"
    assert client.put(url,json=update(latest,[scene("Tự viết sau lỗi ảnh")])).status_code==200


def test_missing_or_corrupt_stored_file_and_conflict_preserve_selection(sketches):
    client,_,project,_=sketches;ready=generate(client,project)[0].json();s=ready["scene_sketches"][-1]
    path=routes.get_image_store().path(project["id"],s["asset_id"]);path.write_bytes(b"broken")
    assert decide(client,ready,s["id"],"keep").status_code==409
    assert client.get(f"/api/projects/{project['id']}/scene-sketches/{s['id']}/image").status_code==404
    path.unlink();assert decide(client,ready,s["id"],"keep").status_code==409
    assert decide(client,project,s["id"],"discard").status_code==409
    assert not client.get(f"/api/projects/{project['id']}").json()["selected_scene_sketches"]


def test_provider_offline_process_and_timeout(monkeypatch,tmp_path):
    (tmp_path/"image-runtime/bin").mkdir(parents=True);(tmp_path/"image-runtime/bin/python").touch()
    (tmp_path/"image-models/hub/models--filipstrand--Z-Image-Turbo-mflux-4bit/snapshots"/PARAMETERS["model_revision"]).mkdir(parents=True)
    monkeypatch.setenv("SCENE_IMAGE_PROVIDER","mflux")
    commands=[]
    class Process:
        pid=12345;returncode=0
        def __init__(self,command,**kwargs):
            commands.append((command,kwargs));
            assert kwargs["env"]["HF_HUB_OFFLINE"]=="1" and kwargs["env"]["TRANSFORMERS_OFFLINE"]=="1"
            assert command[0]==str(tmp_path/"image-runtime/bin/python")
            assert "--prompt-file" in command and "--seed" in command
            assert "--model" in command and "--base-model" in command and "--model-path" not in command
            from pathlib import Path
            Path(command[command.index("--output")+1]).write_bytes(png())
        def wait(self,timeout=None):
            if timeout is not None and fail[0]:raise subprocess.TimeoutExpired("mflux",timeout)
    fail=[False];monkeypatch.setattr("app.infrastructure.scene_images.subprocess.Popen",Process)
    killed=[];monkeypatch.setattr("app.infrastructure.scene_images.os.killpg",lambda pid,sig:killed.append(pid))
    provider=MfluxSceneProvider(tmp_path);assert provider.generate("A scene; $(no shell)").startswith(b"\x89PNG")
    fail[0]=True
    with pytest.raises(ProviderTimeoutError):provider.generate("same")
    assert killed==[12345] and len(commands)==2
    monkeypatch.setenv("SCENE_IMAGE_PROVIDER","")
    with pytest.raises(MissingProviderConfigurationError):provider.generate("same")


def test_image_store_rejects_non_uuid_path(tmp_path):
    with pytest.raises(ValueError):SceneImageStore(tmp_path).save("../other",str(uuid4()),png())


def test_image_limit_and_untrusted_request_fields(sketches):
    client,provider,project,_=sketches;url=f"/api/projects/{project['id']}"
    _,body=generate(client,project)
    latest=client.get(url).json()
    for extra in ({"url":"https://example.com/image.png"},{"source_outline":{}},{"width":99999}):
        assert client.post(url+"/scene-sketches",json={**body,"request_id":str(uuid4()),"revision":latest["revision"],**extra}).status_code==422
    store=routes.projects.get_project_store();raw=store.get(project["id"])
    raw["scene_sketches"]=[{**raw["scene_sketches"][0],"id":str(uuid4())} for _ in range(20)]
    store.save(raw,raw["revision"])
    full=client.get(url).json();assert generate(client,full)[0].status_code==422
    assert len(provider.requests)==1
    assert client.put(url,json=update(full,[scene("Vẫn tự viết được")])).status_code==200


def test_provider_lock_blocks_second_image_process(monkeypatch,tmp_path):
    import fcntl
    (tmp_path/"image-runtime/bin").mkdir(parents=True);(tmp_path/"image-runtime/bin/python").touch()
    (tmp_path/"image-models/hub/models--filipstrand--Z-Image-Turbo-mflux-4bit/snapshots"/PARAMETERS["model_revision"]).mkdir(parents=True)
    monkeypatch.setenv("SCENE_IMAGE_PROVIDER","mflux")
    with (tmp_path/"scene-image.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(ProviderRequestError,match="still running"):
            MfluxSceneProvider(tmp_path).generate("No second process")


def test_prompt_is_bound_to_selected_saved_scene_and_keeps_legacy_history(sketches):
    client,provider,project,text=sketches;url=f"/api/projects/{project['id']}"
    # Preserve a real old record, not a migrated prompt relabeled as the new version.
    ready=generate(client,project)[0].json()
    ready=generate(client,ready)[0].json()
    store=routes.projects.get_project_store();raw=store.get(project["id"])
    raw["scene_sketches"][0]["prompt"]="Legacy JSON prompt kept verbatim."
    raw["scene_sketches"][0]["prompt_version"]="scene-sketch-v1"
    raw["scene_sketches"][1]["prompt"]="Legacy quoted visual prompt kept verbatim."
    raw["scene_sketches"][1]["prompt_version"]="scene-sketch-visual-v2"
    store.save(raw,raw["revision"])
    ready=client.get(url).json()
    scenes=deepcopy(ready["scene_outline"]["scenes"])
    scenes[0].update(action="A mechanic aged 61 watches the left wheel.",characters="One mechanic aged 61.",
                     location="A repair shed",keep_or_avoid="The toolbox stays closed.",
                     staging_choices={"performance":"Eyes stay on the wheel, away from the door."})
    scenes[1]["action"]="NEIGHBOR_ONLY_SECRET_ACTION"
    ready=client.put(url,json=update(ready,scenes)).json()
    saved_source=deepcopy(ready["scene_outline"]["source"])
    changed=payload(ready);changed["idea"]="CURRENT_M1_IDEA_MUST_NOT_REPLACE_SOURCE"
    ready=client.put(url,json=changed).json();text_calls=len(text.requests)
    result=generate(client,ready)[0];assert result.status_code==200,result.text
    latest=result.json();item=latest["scene_sketches"][-1];prompt=item["prompt"]
    assert item["prompt_version"]==SKETCH_PROMPT_VERSION and item["prompt"]==provider.requests[-1]
    assert all(value in prompt for value in (scenes[0]["action"],scenes[0]["characters"],scenes[0]["keep_or_avoid"],saved_source["context"]["idea"]))
    assert "NEIGHBOR_ONLY_SECRET_ACTION" not in prompt
    assert "CURRENT_M1_IDEA_MUST_NOT_REPLACE_SOURCE" not in prompt
    assert latest["scene_sketches"][0]["prompt"]=="Legacy JSON prompt kept verbatim."
    assert latest["scene_sketches"][0]["prompt_version"]=="scene-sketch-v1"
    assert latest["scene_sketches"][1]["prompt"]=="Legacy quoted visual prompt kept verbatim."
    assert latest["scene_sketches"][1]["prompt_version"]=="scene-sketch-visual-v2"
    assert latest["scene_outline"]==ready["scene_outline"]
    assert latest["scene_handoff"]=={**ready["scene_handoff"],"project_revision":latest["revision"]}
    assert latest["selected_scene_sketches"]==ready["selected_scene_sketches"]
    assert latest["feedback_source"]==ready["feedback_source"] and len(text.requests)==text_calls
