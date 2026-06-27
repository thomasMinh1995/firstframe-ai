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

Current implementation: OpenAI-backed structured response with inline reasoning instructions.

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

