# Workflow

FirstFrame AI runs a complete end-to-end story development workflow.

```text
IdeaRequest
  |
  v
Transport Validation
  |
  v
IdeaArtifact
  |
  v
ReasoningLayer
  |
  v
ReasoningArtifact
  |
  v
PlanningLayer
  |
  v
PlanningArtifact
  |
  v
StoryPlanArtifact
  |
  v
EvaluationLayer
  |
  v
EvaluationArtifact
  |
  v
GenerateResponse
```

## API Flow

### Project Workflow (P0)

The current UI uses `/api/projects` and pauses for the creator's decisions:

```text
Create/Open Project -> Save Idea -> Analyze -> Answer/Defer Questions
  -> Generate Story Plan -> Edit -> Save -> Review -> Reopen/Revise
```

- `GET/POST /api/projects`: list or create projects.
- `GET/PUT /api/projects/{id}`: open or save a project.
- `POST /api/projects/{id}/analyze`: analyze the saved idea and return up to three questions, without generating a plan.
- `POST /api/projects/{id}/plan`: use the saved answers and constraints to plan and evaluate; rejects unanswered questions.
- `POST /api/projects/{id}/review`: evaluate the saved edited plan without rewriting it.

Updates and AI actions include the current `revision`. Project updates are complete replacements of the editable fields: `title`, `idea`, `constraints`, `answers`, and `draft` must all be supplied, even for empty lists or a null draft. Answers must match the current question count. Missing fields are rejected rather than silently clearing saved content. SQLite saves check the revision atomically, including after AI work, so a late response cannot overwrite newer work. The store is `backend/.data/projects.sqlite3`.

Feedback is current only when the idea, constraints, questions, answers, and draft match the reviewed content. Editing those fields marks old feedback as outdated. Changing a brief archives its previous questions and answers, including answers submitted in the same save. Reanalysis keeps answers only for unchanged questions and archives the old set before replacing it. Earlier choices remain visible for reference and are not automatically carried into a different brief.

Versions preserve drafts, their source questions/answers, and feedback before replacement and after review. Restoring a version replaces only the story plan, retaining the current brief and earlier versions. Existing database records remain readable through defaults for the added history fields; old feedback without question context is marked outdated without deleting it.

### Original Generation API

`POST /api/generate`

Request:

```json
{
  "idea": "A retired father wants to meet his daughter one last time before she leaves Vietnam."
}
```

Response:

```json
{
  "analysis": {},
  "story_plan": {},
  "evaluation": {}
}
```

The response is transport-friendly JSON, not raw internal artifacts.

## Reasoning Step

The Reasoning Layer:

- receives the user's idea;
- identifies what is present;
- identifies missing information;
- produces mentor-style notes/questions;
- returns a `ReasoningArtifact`.

Current implementation: OpenAI-backed structured response using `story_mentor_prompt.md`.
The mentor asks zero to three questions about consequential unresolved choices,
grounded in the creator's brief rather than a mandatory story template.

## Planning Step

The Planning Layer:

- loads `story_planner_prompt.md`;
- loads short-film knowledge files;
- loads a small set of local examples;
- uses the reasoning artifact as input;
- requests a structured `story_plan` object from OpenAI;
- validates the result with `_PlanningOutput`;
- maps it into a `PlanningArtifact`.

Planning fields include working title, logline, characters, conflict, beginning, middle, ending, theme, visual style, tone, and production notes.

## Evaluation Step

The Evaluation Layer:

- loads `script_critic_prompt.md`;
- loads `story_rubric.json`;
- evaluates the generated plan;
- validates scores and feedback with `_EvaluationOutput`;
- maps feedback into `EvaluationArtifact` findings.

Rubric scores are strongly typed:

- story clarity;
- character;
- conflict;
- emotional impact;
- ending;
- production feasibility.

## Frontend Experience

While the backend runs, the frontend shows a Thinking Timeline:

```text
Understanding idea -> Emotional core -> Planning -> Evaluation -> Preparing Story Plan
```

After generation completes, the UI shows:

- Story Flow visualization;
- Analysis card;
- Story Plan card;
- Evaluation card with score indicators.

## Why Harness Owns Workflow

Reasoning, planning, and evaluation are shared creative workflow concerns. They should not be duplicated inside each domain or controller.

The Harness controls order. Domains provide assets. Providers execute model calls.

## Why This Is Not A Chatbot

A chatbot responds directly to a message.

FirstFrame AI routes every request through a fixed creative reasoning pipeline with explicit artifacts, domain knowledge, structured output validation, and evaluation. This makes the system easier to test, extend, and explain during a demo.

