# Structured Output Contract Audit

This document records the canonical structured-output contracts used by the Short Film domain.

The runtime source of truth is the Pydantic response model passed to `StructuredProvider`.
`domains/short-film/output_schema.json` mirrors the same field inventory for domain-level review.
Both adapters append `model_json_schema()` to instructions. Ollama additionally supplies the schema in the native API `format` field. The OpenAI request remains prompt-based JSON, with local Pydantic validation.

## Planning Contract

| Prompt Field | Schema Field | Status |
| --- | --- | --- |
| `story_plan` | `story_plan` | Canonical root field |
| `working_title.title` | `story_plan.working_title.title` | Synchronized |
| `logline.text` | `story_plan.logline.text` | Synchronized |
| `characters.protagonist` | `story_plan.characters.protagonist` | Synchronized |
| `characters.supporting_characters` | `story_plan.characters.supporting_characters` | Synchronized |
| `characters.antagonist_or_obstacle` | `story_plan.characters.antagonist_or_obstacle` | Synchronized |
| `conflict.external` | `story_plan.conflict.external` | Synchronized |
| `conflict.internal` | `story_plan.conflict.internal` | Synchronized |
| `conflict.stakes` | `story_plan.conflict.stakes` | Synchronized |
| `beginning.setup` | `story_plan.beginning.setup` | Synchronized |
| `beginning.key_event` | `story_plan.beginning.key_event` | Synchronized |
| `middle.escalation` | `story_plan.middle.escalation` | Synchronized |
| `middle.turning_point` | `story_plan.middle.turning_point` | Synchronized |
| `ending.resolution` | `story_plan.ending.resolution` | Synchronized |
| `ending.final_image` | `story_plan.ending.final_image` | Synchronized |
| `theme.statement` | `story_plan.theme.statement` | Synchronized |
| `visual_style.description` | `story_plan.visual_style.description` | Synchronized |
| `visual_style.visual_motifs` | `story_plan.visual_style.visual_motifs` | Synchronized |
| `tone.description` | `story_plan.tone.description` | Synchronized |
| `production_notes.notes` | `story_plan.production_notes.notes` | Synchronized |
| `production_notes.locations` | `story_plan.production_notes.locations` | Synchronized |
| `production_notes.cast_size` | `story_plan.production_notes.cast_size` | Synchronized |
| `core_idea` | None | Removed |
| `main_conflict` | None | Removed |
| `emotional_goal` | None | Removed |
| `ending_direction` | None | Removed |
| `key_scenes` | None | Removed |
| `sections[].content` object | None | Removed |

## Evaluation Contract

| Prompt Field | Schema Field | Status |
| --- | --- | --- |
| `passed` | `passed` | Synchronized |
| `rubric_scores.story_clarity` | `rubric_scores.story_clarity` | Synchronized |
| `rubric_scores.character` | `rubric_scores.character` | Synchronized |
| `rubric_scores.conflict` | `rubric_scores.conflict` | Synchronized |
| `rubric_scores.emotional_impact` | `rubric_scores.emotional_impact` | Synchronized |
| `rubric_scores.ending` | `rubric_scores.ending` | Synchronized |
| `rubric_scores.production_feasibility` | `rubric_scores.production_feasibility` | Synchronized |
| `strengths` | `strengths` | Synchronized |
| `weaknesses` | `weaknesses` | Synchronized |
| `suggestions` | `suggestions` | Synchronized |
| `overall_read` | None | Removed |
| `evaluation_summary` | None | Removed |
| `mentor_questions` | None | Removed |
| `filmability` | None | Removed |

## Provider Response Format

`OpenAIProvider` receives an `StructuredRequest` with a Pydantic `response_model`.
Both receive the same input and instructions and validate against `response_model`. Ollama uses native structured output; both expose `StructuredResult` to the workflow.

Current mappings:

- Planning Layer: `_PlanningOutput`
- Evaluation Layer: `_EvaluationOutput`

## Project revision feedback (#7)

Project plan generation and manual review both use the existing `CardReview`
provider contract (`_RevisionReviewOutput`). The server supplies card/decision
IDs from the current immutable snapshot; the model selects IDs and returns
`comparison`, `observation` (detail and its effect relative to intent), and a
specific `suggestion`. The existing focused provider prompt returns one review,
within the transport limit of three priorities. Aligned reviews produce strengths
and zero priorities. This does not establish semantic correctness or acceptance.

The core evaluation, API and saved project/history/proposal now carry optional
`revision_notes` alongside the compatible `findings` projection:

- `note_id`, `artifact_id`, `comparison`, `observation`, `suggestion` keep each
  issue and next step paired through every layer.
- `decision_id`, `decision_quote`, `decision_question` identify the actual author
  source. An equal answer to another question is not an interchangeable source.
- `targets[]` contains snapshot-local `target_id` and the exact server-extracted
  `quote`. IDs cover title, logline and section/card positions, including duplicate
  section names. They have meaning only inside the matching `FeedbackSource`
  (project, evaluation artifact, reviewed content and author/draft snapshot).

Every target and decision must match that snapshot exactly. One bad reference
makes the whole priority read-only; no fuzzy relocation or selection of the first
valid reference. Multi-target priorities expose an explicit choice. Navigation
only opens/focuses the chosen editor and preserves the complete unsaved buffer.
Changing only the project name does not invalidate feedback. Editing relevant
content does; undoing to the exact saved content can restore navigation.

Missing/malformed optional metadata falls back to readable legacy findings,
without generating pairs or links from array positions or prose. Opening a
project does not migrate stored data. Old feedback, historical views and
proposals remain read-only. Save/review still use the existing optimistic lock,
atomic source snapshot and recovery checkpoint.

The legacy `/api/generate` and default offline `StoryGenerationService.plan()`
retain `_EvaluationOutput`, including recorded baseline replays. Project routes
explicitly opt into structured initial review; no baseline files are rewritten.
