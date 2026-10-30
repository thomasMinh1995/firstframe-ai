"""Replay saved synthetic scene-writing sources once each; never retry model failures."""
import argparse
import gzip
import json
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api.schemas.projects import ProjectResponse, ScreenplayProposal
from app.application.screenplay_writing import PROMPT_VERSION, write_scene
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--model', default='qwen2.5:7b')
parser.add_argument('--variants-only', action='store_true', help='Check parent dialogue, English output and a later scene with saved continuity')
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[2]
evidence = root/'docs/evaluations'
cases = []
for name in ('quiet-open-ending', 'gentle-comedy', 'limited-resources'):
    path = evidence/'m3-scene-writing-qwen7b-2026-10-27'/name/'project-after.json'
    proposal = ScreenplayProposal.model_validate(json.loads(path.read_text())['screenplay_proposals'][-1])
    cases.append((name, path, proposal.model_copy(update={'prompt_version': PROMPT_VERSION})))
for name in ('draft-workflow-qwen7b-2026-10-30', 'draft-workflow-qwen7b-saved-brief-2026-10-30'):
    path = evidence/name/'candidate.json.gz'
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        p = ProjectResponse.model_validate(json.load(f)['project'])
    script = p.screenplay.model_copy(deep=True)
    # Reconstruct the checkpoint immediately before writing the first scene.
    for scene in script.scenes:
        scene.blocks = []
    cases.append((name, path, ScreenplayProposal(id=str(uuid4()), created_at='2026-10-30',
        source_revision=p.revision, source_content=p.content_key(), source_screenplay=script,
        source_outline=p.scene_outline, target_scene_id=script.scenes[0].id, prompt_version=PROMPT_VERSION)))

variants = {}
if args.variants_only:
    quiet = cases[0]
    dialogue = quiet[2].model_copy(deep=True)
    dialogue.instructions = 'Viết hai câu thoại ngắn, cha nói một câu và con gái đáp một câu; giữ xưng hô cha-con, thư kín và kết mở.'
    english = quiet[2].model_copy(deep=True)
    english.source_screenplay.source_outline.source.response_language = 'en'
    english.instructions = 'Write in English, preserve the unopened letter and the undecided ending.'
    later = cases[3][2].model_copy(deep=True)
    first, second = later.source_screenplay.scenes
    from app.api.schemas.screenplays import ScriptScene
    later.source_screenplay.scenes[0] = ScriptScene.model_validate({**first.model_dump(), 'blocks':[
        dict(id=str(uuid4()), kind='action', text='Bố đã đưa lá thư cho Linh. Linh đã nhận, giữ trong tay, chưa mở.', speaker='')]})
    later.target_scene_id = second.id
    variants = {'parent-dialogue':'Explicit request for two parent/child dialogue lines; source constraints unchanged.',
        'english':'Explicit English response language; Vietnamese source retained.',
        'later-scene':'Target second scene with a synthetic saved first scene: the letter has already changed hands.'}
    cases = [('parent-dialogue', quiet[1], dialogue), ('english', quiet[1], english),
             ('later-scene', cases[3][1], later)]

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

class Capture(OllamaProvider):
    def request_structured(self, request):
        self.calls += 1
        save(case_dir/f'request-{self.calls:02d}.json', dict(stage=request.stage, instructions=request.instructions,
            input_text=request.input_text, schema=request.response_model.model_json_schema()))
        result = super().request_structured(request)
        save(case_dir/f'response-{self.calls:02d}.json', dict(raw_output=result.raw_output, output=result.output.model_dump(mode='json')))
        return result

provider = Capture(OllamaProviderConfig(args.model))
save(out/'profile.json', dict(provider=asdict(provider.metadata), prompt_version=PROMPT_VERSION,
    variants=variants,
    application_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    worktree_changes=subprocess.check_output(['git', 'diff', '--stat'], cwd=root, text=True)))
reports = []
for name, path, proposal in cases:
    case_dir = out/name
    case_dir.mkdir()
    with gzip.open(case_dir/'proposal.json.gz', 'wt', encoding='utf-8') as f:
        json.dump(proposal.model_dump(mode='json'), f, ensure_ascii=False)
    began = time.monotonic()
    provider.calls = 0
    print(json.dumps({'case':name, 'event':'start'}), flush=True)
    report = dict(case=name, source=str(path.relative_to(root)))
    try:
        result = write_scene(proposal, provider)
        save(case_dir/'result.json', dict(scene=result.scene.model_dump(mode='json'),
            prompt_version=result.prompt_version, model=result.model, status=result.status))
        report.update(technical_pass=True, blocks=len(result.scene.blocks),
            target_preserved=result.scene.id == proposal.target_scene_id)
        target = next(s for s in proposal.source_screenplay.scenes if s.id == proposal.target_scene_id)
        assert report['target_preserved'] and result.scene.source_scene_id == target.source_scene_id
    except Exception as error:
        report.update(technical_pass=False, error=str(error), raw_output=getattr(error, 'raw_output', None),
            validation_error=str(error.__cause__) if error.__cause__ else None)
    report.update(seconds=round(time.monotonic()-began, 3), model_calls=provider.calls)
    reports.append(report)
    save(case_dir/'report.json', report)
    save(out/'report.json', dict(cases=reports, technical_pass=all(r['technical_pass'] for r in reports), release_approved=False))
    print(json.dumps(report, ensure_ascii=False), flush=True)
sys.exit(0 if all(r['technical_pass'] for r in reports) else 1)
