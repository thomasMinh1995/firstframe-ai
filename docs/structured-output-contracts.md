# Structured Output Contract Audit

This document records the canonical structured-output contracts used by the Short Film domain.

The runtime source of truth is the Pydantic response model passed to `OpenAIProvider`.
`domains/short-film/output_schema.json` mirrors the same field inventory for domain-level review.
The provider appends `model_json_schema()` to each OpenAI request as the effective response format.

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

## OpenAI Response Format

`OpenAIProvider` receives an `OpenAIStructuredRequest` with a Pydantic `response_model`.
It sends strict JSON instructions plus `response_model.model_json_schema()` to OpenAI.

Current mappings:

- Planning Layer: `_PlanningOutput`
- Evaluation Layer: `_EvaluationOutput`

