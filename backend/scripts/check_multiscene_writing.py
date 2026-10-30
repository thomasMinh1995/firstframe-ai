"""Write new synthetic scene sequences with real continuity; never retry a failed call.

Outlines are controlled fixtures, not evidence that the AI planner created them.
Content still requires reading against each case's review_criteria.
"""
import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api.schemas.projects import Screenplay, ScreenplayProposal, SceneOutline, ScenePlanSource, StoryDraft, AuthorContext
from app.api.schemas.scenes import Scene
from app.api.schemas.screenplays import ScriptScene
from app.api.schemas.provenance import TextProvenance
from app.application.provenance import scene_fields, ai_draft
from app.application.screenplay_writing import write_scene, PROMPT_VERSION
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def prepare(case):
    scenes = [Scene(id=str(uuid4()), **s) for s in case['scenes']]
    draft = StoryDraft(title=case['title'], logline=case['idea'], sections=[
        dict(title='Story', purpose='Author brief', content=case['idea'])])
    source = ScenePlanSource(id=str(uuid4()), project_revision=1, version_id='current', draft=draft,
        context=AuthorContext(idea=case['idea'], constraints=case['constraints'], clarifications=[], pending_questions=[]),
        response_language=case['language'], draft_provenance=ai_draft(draft))
    outline = SceneOutline(id=str(uuid4()), version=1, scenes=scenes, source=source,
        provenance={k:TextProvenance(origin=case['origin']) for k in scene_fields(scenes)})
    return Screenplay(id=str(uuid4()), version=1, source_revision=1, source_outline=outline,
        scenes=[ScriptScene(id=str(uuid4()), source_scene_id=s.id, heading=s.title) for s in scenes])


def contracts(case, scene):
    lines = [b for b in scene.blocks if b.kind=='dialogue']
    return {'requested_dialogue_count':len(lines)==case['dialogue_count'],
            'requested_speaker_order':[b.speaker for b in lines]==case['required_speakers'],
            'english_heading':case['language']!='en' or scene.heading.isascii()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',action='append',help='Run only these case IDs')
    args=parser.parse_args(); root=Path(__file__).resolve().parents[2]
    cases=json.loads(args.cases.read_text()); cases=[c for c in cases if not args.case or c['id'] in args.case]
    if not cases or args.case and set(args.case)-{c['id'] for c in cases}:parser.error('Unknown/empty case selection')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    class Capture(OllamaProvider):
        calls=0
        def request_structured(self,request):
            self.calls+=1
            save(scene_dir/f'request-{self.calls:02d}.json',dict(stage=request.stage,instructions=request.instructions,
                input_text=request.input_text,schema=request.response_model.model_json_schema()))
            result=super().request_structured(request)
            save(scene_dir/f'response-{self.calls:02d}.json',dict(output=result.output.model_dump(mode='json'),raw_output=result.raw_output))
            return result
    provider=Capture(OllamaProviderConfig('qwen2.5:7b'))
    save(out/'cases.json',cases)
    save(out/'profile.json',dict(provider=asdict(provider.metadata),prompt_version=PROMPT_VERSION,
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        fixtures_sha256=hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        expected_cases=len(cases),expected_scenes=sum(len(c['scenes']) for c in cases),
        scope='Controlled outlines; sequential writing uses all previously returned scenes. No automatic content approval.'))
    reports=[]
    for case in cases:
        case_dir=out/case['id'];case_dir.mkdir();script=prepare(case); before=script.source_outline.model_dump(mode='json');entries=[]
        for index,target in enumerate(script.scenes):
            scene_dir=case_dir/f'scene-{index+1:02d}';scene_dir.mkdir();provider.calls=0;began=time.monotonic()
            proposal=ScreenplayProposal(id=str(uuid4()),created_at='2026-10-30',source_revision=1,source_content='synthetic QA',
                source_screenplay=script.model_copy(deep=True),source_outline=script.source_outline.model_copy(deep=True),
                target_scene_id=target.id,instructions=case.get('instructions',''),prompt_version=PROMPT_VERSION)
            with gzip.open(scene_dir/'proposal.json.gz','wt',encoding='utf-8') as f:json.dump(proposal.model_dump(mode='json'),f,ensure_ascii=False)
            print(json.dumps(dict(case=case['id'],scene=index+1,event='start')),flush=True)
            try:
                result=write_scene(proposal,provider);assert result.scene.id==target.id and result.scene.source_scene_id==target.source_scene_id
                assert script.source_outline.model_dump(mode='json')==before
                save(scene_dir/'result.json',result.model_dump(mode='json'))
                script.scenes[index]=result.scene
                script.provenance.update({k:TextProvenance(origin='ai_proposal') for k in scene_fields([result.scene],True)})
                entry=dict(scene=index+1,technical_pass=True,contract_checks=contracts(case,result.scene))
            except Exception as error:
                entry=dict(scene=index+1,technical_pass=False,error=str(error),raw_output=getattr(error,'raw_output',None),cause=str(error.__cause__))
            entry.update(model_calls=provider.calls,seconds=round(time.monotonic()-began,3));entries.append(entry);save(scene_dir/'report.json',entry)
            print(json.dumps(entry,ensure_ascii=False),flush=True)
            if not entry['technical_pass']:break  # Later scenes cannot pretend a failed predecessor exists.
        save(case_dir/'screenplay.json',script.model_dump(mode='json'))
        complete=len(entries)==len(script.scenes)
        report=dict(case=case['id'],expected_scenes=len(script.scenes),scenes=entries,
            technical_pass=complete and all(e['technical_pass'] for e in entries),
            contract_pass=complete and all(e['technical_pass'] and all(e['contract_checks'].values()) for e in entries),
            content_approved=False)
        reports.append(report);save(case_dir/'report.json',report)
        save(out/'report.json',dict(cases=reports,complete=len(reports)==len(cases),
            technical_pass=len(reports)==len(cases) and all(r['technical_pass'] for r in reports),
            contract_pass=len(reports)==len(cases) and all(r['contract_pass'] for r in reports),release_approved=False))
    return 0 if all(r['technical_pass'] and r['contract_pass'] for r in reports) else 1


if __name__=='__main__':sys.exit(main())
