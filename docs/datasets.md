# Local workflow datasets

Every AI action through the HTTP API records a separate operation. The export is
automatic; no browser download or second model call is needed. Project persistence,
context selection, API response shapes, and the user's save controls are unchanged.

## Storage and recovery

The default directory is `backend/.data/datasets`, already covered by `.gitignore`.
`DATASET_DIR` can override it; use an absolute path in `backend/.env`.

- `dataset.sqlite3`: source recordings, saved before each call and after each result.
- `runs/<run_id>.json`: one UTF-8 JSON document after an operation finishes or fails.

Each JSON file is replaced atomically, so a reader never sees a partially written
document. A file-export error leaves the SQLite recording available. Storage and
export errors are logged without changing the outcome of the story operation.
If both storage destinations are unavailable, recording cannot be guaranteed.

Rebuild per-run JSON files from SQLite, optionally producing a combined JSONL file:

```bash
cd backend
python -m app.application.dataset
python -m app.application.dataset --output .data/datasets/all.jsonl
```

Re-export uses existing run IDs, creates no duplicate recordings, and makes no AI
requests. JSONL contains all stored statuses, including interrupted operations;
filter status explicitly when consuming it. Back up the directory alongside the
project database if you want to keep recordings when moving the installation.

## Operations and links

| Operation | Model steps | Completion point |
| --- | --- | --- |
| `analyze` | `reasoning` | New analysis saved with a successful revision check |
| `plan` | `planning`, `evaluation` | Story plan and critic feedback saved |
| `review` | `evaluation` | Feedback saved for the exact edited draft |
| `generate` | `reasoning`, `planning`, `evaluation` | Complete legacy generation response built |

`workflow_complete=true` identifies successful `plan` and `generate` operations.
An `analyze` or `review` can have `status=completed` without representing the whole
generation pipeline.

`project_id` groups operations for one project. `source_analysis_id` identifies
the analysis that was active when the request started. `parent_run_id` links to
the most recent completed recording using that analysis, for example:

```text
analyze -> plan -> review -> review
```

Reanalysis links from the preceding active analysis and creates a new analysis
identifier for later operations. Changing the brief clears the active analysis,
so the next analysis starts a new chain. Existing projects with no recordings
remain usable and may have a null parent link.

The provider can change between operations: inspect each step's own provenance
rather than assuming all operations in a project used the same model.

## Record schema, version 1

| Field | Meaning |
| --- | --- |
| `schema_version` | Export format version, currently `1` |
| `run_id`, `operation` | Recording UUID and action |
| `project_id`, `parent_run_id`, `source_analysis_id` | Context lineage |
| `input_revision`, `output_revision` | Revision consumed and revision successfully saved |
| `started_at`, `finished_at` | UTC timestamps |
| `status` | `running`, `completed`, `failed`, or `conflict` |
| `workflow_complete` | Successful full generation or plan-plus-evaluation |
| `review_status`, `human_feedback` | Initially `unreviewed` and `null` |
| `input`, `output` | Before/after active project snapshots, or legacy generation request/response |
| `steps` | Ordered model requests and outcomes |
| `models_used` | Distinct successful provider/actual-model pairs in this operation |
| `error_type` | Exception class only; no exception message or traceback |

Project snapshots retain the current idea, constraints, analysis, answers,
retained clarifications, draft, and feedback. Full version/archive lists are not
duplicated into every sample. The exact context actually sent to the model is
always in the step's `request.input_text`; AI interpretations are not promoted
into author choices by recording.

Each step contains:

- `stage`, `provider`, `requested_model`, and `model`. The provider comes from the
  adapter, not an environment-variable guess. `model` uses the provider response's
  identifier when supplied, otherwise the requested identifier. A failed call may
  have only `requested_model` because no successful response was received.
- `parameters`: temperature and timeout; Ollama also includes `num_ctx`. This is
  an explicit allowlist, not a dump of provider configuration or environment variables.
- `request.instructions`: original domain prompt.
- `request.effective_instructions`: exact instructions including the JSON schema.
- `request.input_text`: full workflow input, including the selected knowledge,
  examples, rubric, current draft, or author context used in that step.
- `request.response_schema` plus SHA-256 hashes of the effective prompt, schema,
  and input. These identify revisions even after source files change.
- `output`: validated structured output; `raw_output`: returned model text when
  available; `response_id`: provider response ID when available.
- `status`, `duration_ms`, `started_at`, and `error_type`. Malformed response text
  is retained when available, while the step remains failed.

Provider API keys, HTTP authorization headers, and exception messages are never
collected by the recorder. Story content is intentionally retained locally.
Nothing is uploaded automatically.

## Evaluation, training, and demo replay

A completed request is not an approved training example. `review_status` starts
as `unreviewed`, independently of the critic's score or pass/fail judgment.
The `/datasets` page stores human labels, feedback and explicit demo/training
selections in `DATASET_DIR/reviews.sqlite3`, separate from exported files.
Labels are `unreviewed`, `approved` (good), or `needs_revision` (not suitable).
Only completed, valid samples can be approved; failed samples can retain feedback.
Selections require approval, and changing the label clears selections in the UI.
The API also rejects selections on unapproved samples.

Annotations are keyed by run ID and a SHA-256 fingerprint of the original content.
Re-exporting identical recordings preserves reviews; changing their content resets
the visible review to unreviewed. Revision checks reject stale edits with HTTP 409.
Review, output and version-restore writes also check the active branch's source
fingerprint under the same SQLite write lock. A source switch during validation
returns HTTP 409 without writing to an inactive source; reload before retrying.
Back up `reviews.sqlite3` along with the recordings to preserve human annotations.
Conflicting duplicate run IDs are excluded. This local tool has no reviewer account
or multi-user authentication; labels represent the human using this installation.

- `GET /api/datasets/samples` lists samples and annotations.
- `GET /api/datasets/samples/{run_id}` includes original context, outputs and prompts.
- `PUT /api/datasets/samples/{run_id}/review` saves status, feedback and selections,
  requiring the current fingerprint and review revision.
- `GET /api/datasets/training.jsonl` downloads completed model steps from approved
  samples explicitly selected for training. Each line contains neutral `messages`,
  response schema, project/run IDs, provider, actual model and human review.

The output editor in `/datasets` edits the structured reasoning, planning or
evaluation output of each completed step using named fields. It validates the
supported workflow schema before saving. `corrected_outputs` is stored by step
index alongside the review in `reviews.sqlite3`; source JSON/JSONL, prompts,
raw model text, artifact IDs and project snapshots are never rewritten.
History is stored as append-only full correction snapshots in the
`output_versions` table of `reviews.sqlite3`, scoped by run ID and original
fingerprint. Version 0 always resolves to the immutable original. Each changed
output save adds the next version; review-only changes and identical output saves
do not create versions. Current corrections and the history entry commit in the
same transaction, with review revision checks protecting concurrent edits.

For installations with an existing correction but no history, that correction
appears as version 1, marked “Bản sửa có trước lịch sử”. Its original save time
is unknown. It is preserved when the next version is saved or restored. Earlier
overwritten corrections from before this feature cannot be recovered. Reading
history creates no tables or annotations.

- `GET /api/datasets/samples/{run_id}/history` returns version metadata and the
  current version, without all historical output payloads.
- `GET /api/datasets/samples/{run_id}/diff?from_version=0&to_version=1` compares
  effective outputs by field, including additions/removals, nulls and array indices.
  Reordered arrays are compared by position. Unchanged fields are omitted.
- `POST /api/datasets/samples/{run_id}/restore` accepts `version`, current review
  `revision` and `fingerprint`. Restoring copies that snapshot into a new version
  marked with `restored_from`; it never rewrites older versions or original files.

The history UI compares any two versions and restores the selected “Đến phiên
bản”. Unsaved output/review changes must be saved or discarded first. Restore
revalidates supported schemas, clears approval and reuse selections, and retains
saved feedback. Demo/training continues to use only the current approved output;
old versions do not become eligible automatically. A changed original fingerprint
starts a separate history and cannot restore versions from the previous source.
Back up `reviews.sqlite3` to retain both annotations and output versions.

`PUT /api/datasets/samples/{run_id}/output` accepts the current fingerprint,
review revision and `corrected_outputs` map. An empty map restores the original.
A changed correction clears approval and both reuse selections, while retaining
saved feedback. Saving the same correction has no effect. Stale saves return 409;
invalid fields, types, scores or step indices return 422. Changes to the source
fingerprint invalidate both reviews and corrections.

Approved corrections are projected onto demo analysis, plan and evaluation
cards without changing the recorded lineage. Demo descriptions identify human
edits. Later author choices and branch inputs remain their original recordings.
When a plan changes and its evaluation has no human correction, the original AI
feedback is hidden because it did not evaluate the new plan. There is no automatic
AI re-evaluation. Original outputs can be compared in the dataset review page.

Training exports use approved corrected outputs as the assistant target when
present, and otherwise the original model output. Each line includes
`original_output`, `corrected_output` (or null), `output_source` (`model` or
`human_corrected`), original provider/model, source fingerprint and review metadata.
Model provenance describes the original generation, not authorship of a correction.
Feedback text alone never replaces the assistant target.

After the first corrected step in a run, downstream steps are omitted from the
training export because their recorded prompts still contain the old upstream
context. Earlier unchanged steps can be included. Separate runs keep their own
original prompts and are reviewed independently. The source recording retains all
steps regardless of export eligibility.

These are preparation data, not a provider-ready fine-tuning job;
convert to the target provider format, remove sensitive material as appropriate,
and keep projects separated across training/evaluation splits. No data is uploaded.

For evaluation, compare matching operations/stages and input hashes; retain the
prompt/schema versions and actual model identifiers. Split training and test data
by project rather than by individual drafts or calls.

The `/demo` page reads completed JSON/JSONL exports through two read-only endpoints:

- `GET /api/demo/scenarios`: scenario summaries, original models, quality labels,
  and step counts, without full snapshots or prompts.
- `GET /api/demo/scenarios/{id}`: the selected sequence of recorded UI snapshots.

The catalog reads `DATASET_DIR` and the bundled `demo/datasets` folder by default.
Setting `DEMO_DATASET_DIR` replaces both with that export directory. Reading a
catalog reads existing human annotations if present; it does not create a database,
invoke a provider, save a project, or create another dataset record. After a scenario is loaded, stepping backward/forward or restarting
needs no further backend request. The local backend is still needed to load or
refresh the catalog; no external AI service or internet connection is required.

A completed `plan` creates a scenario with brief, analysis, author choices, plan,
and initial evaluation. Following `review` recordings adds edit/review pairs.
Review branches are enumerated separately by exact parent links, project and
analysis IDs, matching brief, and nondecreasing saved revisions. Recordings from
different briefs are not merged. A legacy `generate` export supplies the same
first five steps, with a note that no separate author answers were recorded.

Missing analysis exports can be represented by the saved analysis in the plan's
input snapshot. Missing model metadata remains unknown. Conflicting duplicate
record IDs are excluded; identical JSON/JSONL duplicates are deduplicated. Failed,
partial, unsupported-version, or invalid snapshots are not offered. Unknown
scenario IDs return 404; IDs are catalog keys, never filesystem paths.

The page displays recorded provider/model names and quality status separately
from the critic's scores. `unreviewed` recordings may be demonstrated but are not
presented as approved training examples. The bundled sample is a real Ollama
recording of a synthetic test brief, including its original imperfect outputs.

Replaying arbitrary user edits requires either a matching recorded branch or
live generation; these exports do not create new answers. Playback is a separate,
read-only workspace and does not silently fall back to live AI. Human ratings are managed in `/datasets`.

The demo checkbox “Chỉ dùng mẫu tốt đã chọn cho demo” or `?curated=true` on both
demo endpoints restricts playback to approved, explicitly selected recordings.
For a plan, select its original analysis and plan samples. Edited branches appear
only through a continuous selected chain. An excluded edit does not hide the
approved initial plan. Missing analysis provenance remains available in preview
but cannot appear in the curated catalog. Changing approval/selection takes effect
on the next catalog refresh; an already loaded browser replay is a snapshot.

Tests isolate all recordings in temporary directories. Model calls interrupted by
a process exit can leave `running` records in SQLite; they are not considered
completed demo or training samples. A project-save conflict preserves model traces
but has `status=conflict` and no accepted output snapshot.

## Transfer approved datasets between machines

Use **Xuất gói dataset đã duyệt** on `/datasets` to download
`firstframe-reviewed-dataset.json`. This is separate from the training JSONL.
The package contains only eligible, approved samples, including samples that are
not selected for demo/training. Each entry retains the complete original recording
(prompts, model outputs, provider/model metadata and lineage), the current review
and feedback, current corrections and all output history, including restore links.
Earlier unapproved historical corrections remain history; they do not become
training targets merely because they are in a package.

On another machine with FirstFrame's frontend and backend installed:

1. Start the local app. No API key, Ollama server, model download or external AI
   service is needed for import, quality review, history or demo playback.
2. Open `/datasets`, choose the exported `.json` file and read the preview counts.
3. Click **Nhập … mẫu và giữ nhãn đã duyệt**. Imported review labels and demo/train
   selections are retained; the original file is not modified.
4. Open `/demo?curated=true`. A demo needs an approved, selected analysis/plan
   chain (and any selected review rounds). The preview reports how many selected
   chains are playable. Export does not silently approve or include missing
   unapproved dependencies.

The format marker is `firstframe-reviewed-dataset`, schema version 1 (or version 2
when conflict branches are included), with a
SHA-256 checksum over canonical JSON excluding the checksum field. Individual
recording fingerprints also validate the originals. Checksums detect corruption;
they do not authenticate the author of a file. Import verifies supported schemas,
completed snapshots, approval, unique run IDs, historical output validity,
continuous versions, restore references and the match between latest history and
current correction. Unsupported/corrupt packages are rejected. The limit is
25 MiB and 1,000 samples. History has no fixed version-count limit, so editing or
restoring a sample beyond 1,000 versions does not make it unreadable or prevent
export while the package remains within the byte limit. History is never truncated.

The preview lists new samples, exact duplicates, conflicts, corrections, history
entries and playable demos. Each conflict offers a field-by-field comparison of
original recordings, feedback/review, current corrections and history, and requires
an explicit choice: keep local or use incoming. There is no default choice.
Revision/timestamp-only review differences do not require a choice when all review
content and history are otherwise identical. Exact duplicates are skipped.

Both sides of a resolved conflict are saved as immutable branches in
`dataset_branches`, including each original, review and complete history. Keeping
local leaves the active sample unchanged and archives incoming. Using incoming
archives local and selects the incoming branch; local files and the original
`imported_samples` row are never overwritten. `dataset_active_branches` selects
which immutable original the catalog currently displays. Histories from different
originals or branches are not spliced together.

Every choice carries a token for the local state that was compared. All choices
are rechecked under a write lock before applying the package. Missing choices,
stale tokens or storage failures reject/roll back the entire import. Selecting
incoming keeps its approved review and selections; a monotonic local revision
prevents stale editor saves. A branch with incomplete/corrupt local data cannot
replace local until its history can be preserved safely.

The sample page's “Nhánh xung đột đã lưu” panel compares archived branches and
can use an old branch again. This archives the current state first, creates a new
restore round on the selected path, and clears approval and demo/train selections.
Originals and all previous paths remain available. Branches are also included in
reviewed package exports as schema version 2; new versions still import version 1
packages. Older applications that only support version 1 must be updated before
receiving packages with branches. Archived unapproved states are retained for
history and are not selected as training targets.

Mixed per-sample choices may leave fewer complete demo chains than the all-incoming
preview count. Demo checks original analysis content as well as identity before
joining a plan to its analysis; mismatched histories are not presented as approved
complete chains.

Imported originals are kept in the `imported_samples` table of
`DATASET_DIR/reviews.sqlite3`. Originals, annotations and history commit together
in one SQLite transaction; storage failures roll back the whole import. Existing
export files, automatic recording databases and projects are not rewritten.
Back up `reviews.sqlite3` or re-export a reviewed package to retain imported
originals as well as their annotations/history. The automatic recorder's JSONL
CLI remains an export of its own recording database.

Imported samples are available alongside configured JSON/JSONL sources, including
when `DEMO_DATASET_DIR` is set. Re-exporting a reviewed package preserves the
imported contents. Import does not create live projects or resume AI generation;
local demo continues to replay the recorded workflow.

- `GET /api/datasets/bundle`: download the approved package.
- `POST /api/datasets/bundle/preview`: validate package JSON and report conflicts,
  without creating storage.
- `POST /api/datasets/bundle/import`: validate and atomically import the same JSON.

Additional conflict endpoints:

- `POST /api/datasets/bundle/compare?run_id=...`: original package JSON; returns
  local-state token and changed fields for that sample.
- `POST /api/datasets/bundle/import` also accepts
  `{ "bundle": <original package>, "resolutions": { "run-id": {
  "choice": "local" | "incoming", "local_token": "..." } } }`.
  Clients must preserve original JSON number tokens rather than reserializing the
  package through JavaScript numbers. The body allows 512 KiB extra for choices.
- `GET /api/datasets/samples/{id}/branches`: saved branch summaries.
- `GET /api/datasets/samples/{id}/branches/{branch_id}`: compare current and saved.
- `POST /api/datasets/samples/{id}/branches/{branch_id}/restore`: accepts the latest
  local-state token, restores the branch and requires review again.
