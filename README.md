# FirstFrame AI

**Your story. Your first short-film screenplay.**

FirstFrame AI helps beginners develop an idea into their first complete short-film screenplay through guided story development and specific, actionable feedback. The creator keeps control of the story and makes the final creative decisions.

The current MVP supports saving projects, answering clarification questions before planning, editing a story plan, and requesting feedback on the revised draft through a **Creative Reasoning Harness**. It does not yet produce a complete screenplay.

Current project workflow:

```text
Save Idea -> Analyze -> Answer Questions -> Generate Story Plan -> Edit -> Review -> Save/Reopen
```

## Why It Exists

Beginners often have a promising story idea but do not know how to shape it:

- What is the emotional core?
- Who is the protagonist?
- Where is the conflict?
- Does the ending work?
- Is the story practical for a short film?

FirstFrame guides creators through these questions, explains revision options, and helps them decide what to develop next. Practical constraints such as cast size and available locations inform the writing process.

## First Users

The first users are Vietnamese-speaking beginners who want to finish their first short-film screenplay. They have an idea or personal experience to explore but lack a development method and someone to give useful feedback.

They may be students, film-club members, or independent enthusiasts. They do not need a crew or a filming schedule to start; they need a willingness to write, review, and revise a draft.

## Product Scope

The planned core journey is:

```text
Idea -> Story Development -> Scene Outline -> Write and Revise -> Complete Screenplay
```

A completed draft contains all scenes from beginning to end, uses action and dialogue appropriate to the creator's intent, has undergone at least one feedback-and-revision round, and can be exported for reading and further development. This is the product goal, not a capability already delivered by the MVP.

After the screenplay, optional rough scene illustrations may help creators visualize characters, positions, and key actions. This is a later extension, not a requirement for completing a screenplay. It does not include animation or video generation.

Filming preparation, shooting, editing, screenings, and feature-film or television development are outside the current product roadmap.

## Current MVP

- Local SQLite project storage, project selection, and explicit save controls
- Up to three clarification questions before story-plan generation, with an explicit option to defer a decision
- Editable story plans and feedback tied to the exact reviewed content
- Version history, story-plan restoration, and JSON backup download
- Clarification history preserves earlier questions and answers when the brief changes; answers stay in the active author context across reanalysis of the same brief, even if the new question list changes or is empty
- Revision checks that reject stale saves from another window
- FastAPI backend with `POST /api/generate`
- Project API under `/api/projects`; the original generation endpoint remains available for compatibility
- Next.js demo frontend
- Creative Reasoning Harness orchestration
- OpenAI provider adapter
- Prompt, Knowledge, Rubric, and Example loaders
- Short-film domain intelligence pack
- Pydantic structured output validation
- Vietnamese project workspace with operation-specific loading and error messages
- Localized model-output guidance

Use **Save changes / Lưu thay đổi** before closing a project. Switching projects, creating another project, and requesting AI work save pending edits first. Unsaved changes trigger a browser warning when leaving. Projects are stored in `backend/.data/projects.sqlite3`, which is ignored by Git; keep this file when restarting or moving the local installation. JSON downloads provide a readable backup; importing them is not implemented yet.

Changing the idea or constraints requires a new clarification round. Earlier answers remain readable in **Các lựa chọn trước đây** and are not silently applied to a new brief. Feedback freshness checks include the questions as well as the answers and draft. Older saved projects remain readable; feedback without this complete context is conservatively marked outdated until reviewed again.

Reanalyzing the same brief passes existing choices to the mentor and retains them
for planning and review. Current answers override earlier answers to the same
question, including an explicit deferral or clearing an answer. Changing the brief
clears this active context while preserving its history. Saved versions include
the effective clarification context; feedback from before this context was recorded
is conservatively marked outdated.

This is a local, single-user MVP without authentication. Keep the backend bound to localhost. AI actions require `OPENAI_API_KEY` in `backend/.env`; project saving and reopening work without it.

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
OpenAI Provider Adapter
  |
  v
Validated Structured JSON
```

The Harness provides the technical foundation for story development. Product progress is measured by creators completing and improving drafts, rather than by adding workflow stages or infrastructure.

## Repository Structure

```text
backend/              FastAPI API, Harness runtime, core contracts, OpenAI adapter
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

Create `backend/.env` from `backend/.env.example` and set `OPENAI_API_KEY`.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

## Current Limitations

- One active domain: Short Film Story Development.
- Output is a story plan, not a scene outline or complete screenplay.
- No scene-level screenplay editing, account authentication, deployment, or streaming.
- Storage belongs to the local backend; there is no account-based cloud sync.
- Domain registration is currently static in the application service.
- OpenAI is the only implemented provider adapter.

## Next Milestones

1. Validate the project clarification and revision loop with beginners.
2. Develop an editable scene outline from the selected story plan.
3. Support scene-level writing, specific feedback, and screenplay export.
4. Consider optional rough scene illustrations after validating the core writing journey.

See [the roadmap](docs/roadmap.md) for milestone outcomes and validation. Expansion into other creative domains is deferred while FirstFrame validates the first-screenplay experience.

