# FirstFrame AI

**From a moment in your life to your first short-film screenplay.**

FirstFrame helps people in Vietnam write their first short film from their own experiences, understand their creative choices, and revise a screenplay to share with human collaborators. The author keeps control of the story.

The current MVP supports saved projects, clarification questions, editable story plans, version history, and feedback on the revised draft through a **Creative Reasoning Harness**. It does not yet provide a scene outline, scene-level screenplay editor, or screenplay export.

Current project workflow:

```text
Save Idea -> Analyze -> Answer/Defer Questions -> Generate Story Plan -> Edit -> Review -> Save/Reopen
```

Review gives feedback on the saved draft; it does not rewrite it. Changing the idea or constraints uses the existing clarification flow again.

## Why It Exists

A line of dialogue, an ordinary act of care, an awkward encounter, or a quiet memory can be enough to start. A beginner may need help discovering what matters in that moment and how to express it through actions, images, and sound.

FirstFrame aims to help creators start without knowing film terminology, preserve what they want to keep, and learn through a specific revision. Quiet, funny, observational, and open-ended stories are valid forms. Production limits such as cast and locations inform the writing when relevant or chosen by the author.

## First Users and Differentiation to Validate

The initial market is Vietnam. The first pilot focuses on Vietnamese film enthusiasts, especially young people who have not completed a short-film screenplay and lack a development method or someone to give useful feedback. A crew and filming schedule are not prerequisites.

The proposed differences are practical outcomes to validate:

- Start from a moment before it becomes a fully formed film idea.
- Handle Vietnamese forms of address, relationships, everyday settings, and speech in their specific context.
- Develop feelings into actions that human actors can perform, with AI additions identified as proposals.
- Help the author understand and make one useful revision.
- Respect creative intent, deliberate ambiguity, and any practical limits the author chooses.

Vietnamese support, a narrow scope, and a mentor label alone do not prove an advantage. Compare selected tasks with a familiar chatbot and a direct story-development tool during the pilot.

## Product Scope

The planned core journey is:

```text
Moment -> Story Plan -> Scene Outline -> Write and Revise Screenplay -> Export Screenplay
```

A story plan clarifies the intended story before detailed scene writing. It is a useful milestone to keep or share, but a good plan does not guarantee a good screenplay. Its detail should fit the size and form of the story.

The product goal is a complete short-film screenplay: all scenes are written, action and dialogue communicate the intended story, at least one feedback-and-revision round has taken place, and the selected draft can be exported for reading and further development. This is not a capability already delivered by the MVP.

FirstFrame's handoff ends at screenplay export. Casting, staging, shooting, editing, and post-production belong to a separate process with real people and actors. AI video, synthetic actors, generated footage, and production management are outside the product direction. Automatic scene illustrations are no longer an active roadmap milestone.

Feature-film and television **screenwriting** may be explored after the short-film journey is validated and users demonstrate a need. This is a conditional long-term direction, not an MVP commitment; the handoff would still end at screenplay export.

See the [Vietnam first-screenplay and MVP demo plan](docs/plans/vietnam-first-screenplay-mvp.md) for priorities, acceptance criteria, and pilot design. This update is documentation only; proposed demo improvements are not implemented by it.

## Current MVP

- Optional six-step onboarding tour with practice breaks, replay, and browser-local progress; tour navigation preserves unsaved text and makes no AI or project-write requests
- Local SQLite project storage, project selection, and explicit save controls
- Up to three clarification questions before story-plan generation, with an explicit option to defer a decision
- Editable story plans and feedback tied to the exact reviewed content
- Saved author-context card from the backend's effective idea, constraints and clarification answers, with unsaved-edit warnings and navigation that does not save or call AI
- Optional manual revision note: choose one current feedback item to read beside the editor, edit in your own words, then save/review/reopen through the existing controls
- Version history, story-plan restoration, and JSON backup download
- Clarification history preserves earlier questions and answers when the brief changes; answers stay in the active author context across reanalysis of the same brief, even if the new question list changes or is empty
- Revision checks that reject stale saves from another window
- FastAPI backend with `POST /api/generate`
- Project API under `/api/projects`; the original generation endpoint remains available for compatibility
- Next.js demo frontend
- Creative Reasoning Harness orchestration
- OpenAI provider adapter with local Ollama fallback when no OpenAI key is configured
- Prompt, Knowledge, Rubric, and Example loaders
- Short-film domain intelligence pack
- Pydantic structured output validation
- Vietnamese project workspace with operation-specific loading and error messages
- Localized model-output guidance
- Automatic local dataset export for analysis, planning, review, and full generation,
  including the provider and actual model used by every step
- Local demo at `/demo`: select and replay exported scenarios without calling AI

Use **Save changes / Lưu thay đổi** before closing a project. Switching projects, creating another project, and requesting AI work save pending edits first. Unsaved changes trigger a browser warning when leaving. Projects are stored in `backend/.data/projects.sqlite3`, which is ignored by Git; keep this file when restarting or moving the local installation. JSON downloads provide a readable backup; importing them is not implemented yet.

Changing the idea or constraints requires a new clarification round. Earlier answers remain readable in **Các lựa chọn trước đây** and are not silently applied to a new brief. Feedback freshness checks include the questions as well as the answers and draft. Older saved projects remain readable; feedback without this complete context is conservatively marked outdated until reviewed again.

**Ý đồ đã lưu hiện tại** shows the last confirmed saved context, including answers retained from earlier clarification rounds of the same brief. Blank answers are pending questions; deferred choices keep the author's exact wording. New evaluations save their own source context and draft with the feedback and version history. **Ý đồ đã dùng cho góp ý này** stays with that feedback when the current context changes. Older feedback without verified source metadata is labeled as missing information; opening it does not reconstruct context or migrate stored projects.

**Xem cạnh bản thảo** keeps the selected feedback text near the editor so you can decide what to change or ignore. Selection only moves focus to the note; it does not infer a target field, rewrite, save, or call AI. After a content/context edit, the note is labeled as belonging to the previous version, not as resolved. The choice is temporary and clears on new feedback, project changes, successful restoration or reload. Historical feedback and feedback without verified source metadata stay read-only. Review still saves pending edits first; a failed save prevents review, and a failed review preserves the saved draft and old feedback with its source.

Reanalyzing the same brief passes existing choices to the mentor and retains them
for planning and review. Current answers override earlier answers to the same
question, including an explicit deferral or clearing an answer. Changing the brief
clears this active context while preserving its history. Saved versions include
the effective clarification context; feedback from before this context was recorded
is conservatively marked outdated.

This is a local, single-user MVP without authentication. Keep the backend bound to localhost. AI actions use OpenAI when `OPENAI_API_KEY` is configured, otherwise a running Ollama server and an installed chat model. Project saving and reopening work without either provider.

### Output language and interface labels

FirstFrame supports Vietnamese and English AI output. The backend makes the same
language decision for clarification, planning, review and `/api/generate`; the
frontend does not guess independently. Automatic detection matches whole words
after Unicode normalization. It needs at least two distinct known words and more
than twice as many matching words as the other language, covering at least one
third of the input words. Place-name tokens `Việt` and `Nam` are not language hints.
A substring such as `con`
inside `concert`, an accent, or a proper name alone is insufficient evidence.

For uncertain, short, unaccented or balanced bilingual ideas, automatic mode asks
the creator to select **Tiếng Việt** or **English** before any model call (HTTP 422).
This is a conservative heuristic, not a general language identifier: French and
other unsupported inputs should use an explicit supported output choice. Mixed
author terminology such as `lab coach`, `build phase` and names remains allowed.

The output choice is saved per project and recorded with versions. Changing it
keeps unsaved text in the editor and does not save, call AI or translate existing
content automatically. The next AI action saves pending edits and uses the choice;
feedback for a different explicit choice is marked outdated. Existing projects
default to automatic mode without rewriting their data or invalidating compatible
automatic-mode feedback. Legacy clients that omit the field preserve a saved
explicit choice. The interface remains Vietnamese regardless of AI output language;
display labels do not rename JSON keys, rewrite author text or translate quotations.
Mentor and planner prompts also follow the explicit output choice and instruct the
model to retain author terminology and source quotations. Model compliance is not
guaranteed: the Qwen review sample still translated an author-supplied film title.

See the [language detection and UI checks](docs/evaluations/language-detection-ui-2026-10-21.md)
for regression cases and real Ollama review evidence.

## Architecture At A Glance

```text
Next.js Frontend
  |
  v
FastAPI API
  |
  v
StoryGenerationService
  |
  v
Creative Reasoning Harness
  |-- Reasoning Layer
  |-- Planning Layer
  |-- Evaluation Layer
  |
  v
Domain Assets
  |-- prompts
  |-- knowledge
  |-- rubrics
  |-- examples
  |
  v
Structured Provider (OpenAI or Ollama)
  |
  v
Validated Structured JSON
```

The Harness provides the technical foundation for story development. Product progress is measured by creators completing and improving drafts, rather than by adding workflow stages or infrastructure.

## Repository Structure

```text
backend/              FastAPI API, Harness runtime, core contracts, OpenAI/Ollama adapters
frontend/             Next.js App Router demo UI
domains/short-film/   Short-film prompts, knowledge, rubric, examples, output schema
docs/                 Architecture, workflow, kernel, decisions, roadmap
```

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Create `backend/.env` from `backend/.env.example`. With `AI_PROVIDER=auto` (the default),
a non-empty `OPENAI_API_KEY` selects OpenAI; a missing or blank key selects Ollama.
`MODEL` still configures the OpenAI model; `OLLAMA_MODEL` configures the local model.

To use Ollama without an OpenAI key:

```bash
ollama serve
# In another terminal, install the chat model once:
ollama pull qwen2.5:3b
```

If the Ollama desktop app already runs the server, skip `ollama serve`. In `backend/.env`:

```dotenv
AI_PROVIDER=auto
OPENAI_API_KEY=
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_TIMEOUT_SECONDS=180
OLLAMA_CONTEXT_LENGTH=16384
```

Use `AI_PROVIDER=ollama` to force local inference even when an OpenAI key exists;
use `AI_PROVIDER=openai` to require an OpenAI key. Restart the backend after changing
configuration. Models are never downloaded automatically. Choose a chat model from
`ollama list`; embedding models such as `nomic-embed-text` cannot generate stories.

The Ollama adapter uses native `/api/chat`, a JSON Schema in `format`, and Pydantic
validation. Both providers retain the creator choices, current draft and output
contracts. `ollama / qwen2.5:3b` uses compact prompts for Vietnamese output under
`domains/short-film/prompts/ollama-qwen2.5-3b/`; its planning input retains all author
context and reasoning notes but omits the long domain knowledge and example library.
The critic keeps its full current draft, author context and rubric. Vietnamese
feedback uses the full Vietnamese critic prompt; English uses the English prompt.
Author terms such as `lab coach`, proper names, section anchors and exact quotations
may remain in their original language while explanations follow the target language.
New revision examples follow the feedback language even inside quotation marks;
the quotation exception only applies to text actually present in the current draft.
This does not require pure Vietnamese or translate the author's draft.
The critic is not compacted:
the experimental compact critic regressed on intent and feedback pairing and was
not enabled. See the recorded comparison in `docs/datasets.md`.
Other provider/model combinations keep their mentor/planner prompts and references;
critic language selection is shared across providers. Exact
effective prompts and inputs are still recorded in the dataset for comparison.
Local generation can be slower and its creative quality depends on the model.
See the [feedback-language checks](docs/evaluations/feedback-language-2026-10-21.md)
for real Qwen results and the remaining intent/feedback-quality limitations.
The context size is configurable for longer briefs; do not lower it below the input
size because Ollama may truncate older input. No provider switch is attempted after
an OpenAI request fails: an invalid key, timeout, or quota error stays an error.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

## Automatic Dataset Export

AI actions automatically record the exact prompts, input context, output schema,
raw and validated model output, provider (`openai` or `ollama`), requested and actual
model identifiers, generation settings, and before/after project snapshots.
The normal UI and API responses stay the same; recording makes no additional model calls.

Default local files (ignored by Git):

```text
backend/.data/datasets/
  dataset.sqlite3     # Durable recordings, updated after each model step
  runs/<run_id>.json  # Automatically exported after each AI action
```

Analysis, planning, and review are linked by project and analysis identifiers.
Planning includes both planner and critic calls; `/api/generate` includes all three
model steps. Failed calls and revision conflicts are recorded with explicit statuses;
they are never marked as completed workflows. A model's rubric score does not mark
the sample approved: every sample starts with `review_status=unreviewed`.

To rebuild JSON exports and also write one JSONL file without calling AI:

```bash
cd backend
python -m app.application.dataset --output .data/datasets/all.jsonl
```

Set `DATASET_DIR` in `backend/.env` to an absolute path to change the location.
Export failures are logged and do not discard a successful story edit; JSON files
can be rebuilt from SQLite. Provider credentials and exception messages are not
included in recordings. The recordings contain the creator's story content, so
choose reviewed samples before sharing or preparing training/demo datasets.

See [dataset format and recovery](docs/datasets.md). Human-review tools and curated
training exports are not implemented.

## Local Demo From Recordings

Start the backend and frontend as above, then open `http://localhost:3000/demo`,
or choose **Xem demo local từ kịch bản có sẵn** on the home page. No OpenAI key,
running Ollama server, or installed model is required for demo playback.

Choose a scenario and move through its recorded brief, analysis, author answers,
story plan, initial feedback, edited draft, and review. Previous/next, direct step
selection, and restarting playback use the loaded data in the browser. Recorded
review branches appear as separate choices. Playback is read-only: it makes no model
calls, does not create a project, and does not add recordings to the training dataset.

By default the demo reads JSON exports under `DATASET_DIR` (including `runs/*.json`)
and JSONL exports, plus one bundled scenario in `demo/datasets`. The bundled scenario
was recorded from the synthetic kitchen-waiting test with `ollama / qwen2.5:3b`;
its original model output is preserved and its quality status is `unreviewed`.

To use only a chosen folder of exported scenarios, set an absolute path and restart
the backend:

```dotenv
DEMO_DATASET_DIR=/absolute/path/to/exported-datasets
```

The folder can contain individual `.json` recordings, a `runs/` subdirectory, or
`.jsonl` exports. Click **Tải lại danh sách** after adding exports. Failed,
incomplete, and inconsistent records are skipped. A standalone plan export can
show the analysis saved in its input even if the earlier analysis file is absent;
the demo does not invent missing model provenance. Arbitrary new ideas or edits
need live generation and are not part of this recorded playback.

## Current Limitations

- One active domain: Short Film Story Development.
- Output is a story plan, not a scene outline or complete screenplay.
- No scene-level screenplay editing, account authentication, deployment, or streaming.
- Storage belongs to the local backend; there is no account-based cloud sync.
- Domain registration is currently static in the application service.
- Implemented providers are OpenAI and local Ollama; Gemini and Claude are not integrated.

## Next Milestones

1. Make the story-plan demo easier to start, read, and revise; show the author's effective choices and validate three Vietnamese situations on the actual demo model.
2. Pilot with beginners, complete the focused feedback-to-edit flow, and export a selected story plan for sharing.
3. Develop an editable scene outline, then support scene-level screenplay writing and revision.
4. Export the selected complete screenplay for human collaborators; this is the product handoff.

See [the roadmap](docs/roadmap.md) and [the detailed demo plan](docs/plans/vietnam-first-screenplay-mvp.md). The onboarding tour is already implemented and awaits remaining acceptance, including beginner validation; adapt it to the settled writing flow rather than rebuilding it. Other creative domains remain deferred. Longer-form screenwriting is conditional future exploration.


### Human dataset review

Open `/datasets` from the writing or demo page to inspect original inputs, model
outputs and provider/model provenance. Mark a sample good or not suitable, record
feedback, and explicitly select approved samples for demo or future training.
Reviews are saved separately in `DATASET_DIR/reviews.sqlite3`; automatic re-export
does not erase them. Unsaved changes must be saved or discarded before switching
samples. Concurrent edits are rejected rather than silently overwritten.

Use `/demo?curated=true` for selected approved recordings. Select both analysis
and plan samples to retain complete context, plus any review rounds to replay.
Download selected training samples as JSONL from the review page. This is a neutral
preparation format with provenance, not an upload or training job. See
[dataset documentation](docs/datasets.md) for API and storage details.

The dataset review page also supports editing output fields before approval.
Expand “Chỉnh sửa output bước này”, save the editorial output, then approve and
select the sample again. Originals remain available for comparison and restore.
Saving a changed output clears approval and demo/training selections. Approved
edits are used in demo cards and training targets with human-edit provenance.
Downstream calls with stale context are omitted from training exports; demo hides
AI feedback that was generated for an earlier, uncorrected plan.

The “Lịch sử chỉnh sửa output” panel keeps every saved output revision from now
on. Compare any two versions by changed field and restore a previous correction
or the original as a new version. Restoring clears approval and reuse selections;
older versions and source recordings are preserved. Existing corrections become
a legacy history entry; edits overwritten before history was enabled are unavailable.

To move approved datasets to another machine, choose **Xuất gói dataset đã duyệt**
on `/datasets`. On the other machine, start FirstFrame locally, select the `.json`
file, review the import preview and import it. The package retains originals,
provider/model metadata, feedback, corrected outputs, all edit history and
reviewed demo/training selections. No OpenAI key or running Ollama is required.
Open `/demo?curated=true` after import. Select complete analysis/plan chains before
exporting so they are available for replay. Resolve each conflict by comparing fields and choosing local or incoming;
both complete originals and histories are kept as separate branches. Exact
duplicates are skipped, and stale choices reject the entire import. See [transfer format and storage](docs/datasets.md#transfer-approved-datasets-between-machines).

After resolving an import conflict, open “Nhánh xung đột đã lưu” on that sample to
compare or use a preserved branch again. Using a saved branch requires review
again before demo/train. Packages with branches use schema version 2 and require
this updated app on the receiving machine; version 1 packages remain supported.

The subsequent [multi-scenario Qwen critic evaluation](docs/evaluations/qwen-critic-2026-10-21.md)
records 24 primary outputs and rejected pilots. The candidate is benchmark-only;
it was not enabled because author-intent and issue/suggestion errors remained.
