# Short Film Domain

Short Film Story Development is the first supported domain for FirstFrame AI.

The initial market is Vietnam, with a pilot focused on people who have not completed a short-film screenplay. A line, action, encounter, or memory can be enough to start. The domain supports developing that material toward scenes, action, and dialogue that real actors and filmmakers can use.

The product journey is **Moment -> Story Plan -> Scene Outline -> Write and Revise Screenplay -> Export Screenplay**. Runtime currently delivers story plans and feedback only. Casting, staging, shooting, editing, AI video, and synthetic actors are outside the product boundary.

## Planned Domain Quality Priorities

The [Vietnam first-screenplay demo plan](plans/vietnam-first-screenplay-mvp.md) defines proposed work, not prompt or rubric changes already delivered:

- Ask only consequential questions in plain language; do not require a complete premise before beginning.
- Respect Vietnamese forms of address, relationships, speech, and everyday settings in their particular context; ask about region or period only when relevant.
- Develop emotion through performable action, images, and sound. Keep AI additions recognizable as proposals rather than facts about the author's experience.
- Support funny, awkward, quiet, observational, and open-ended forms without imposing escalating conflict, reconciliation, or major transformation.
- Give grounded feedback that helps the author make and explain a small edit.
- Apply cast/location constraints when chosen or relevant; distinguish creative choices from temporary resource limits.

These are quality hypotheses to validate with beginners and experienced readers. The current rubric still includes conflict and production feasibility; its existence is not evidence that all forms are evaluated appropriately. During later implementation, adjust only guidance implicated by observed failures, including any model-specific prompt profile, and validate real outputs. No prompt, rubric, schema, or example is changed by this direction update.

## Domain Assets

`domains/short-film/` contains the current intelligence pack.

```text
prompts/
  story_mentor_prompt.md
  story_planner_prompt.md
  script_critic_prompt.md

knowledge/
  film_glossary.json
  film_rules.json
  story_patterns.json

rubrics/
  story_rubric.json

examples/
  family_drama.json
  friendship.json
  coming_of_age.json
  slice_of_life.json
  thriller.json

output_schema.json
```

## Prompts

The Story Mentor prompt guides the Reasoning Layer to reflect the supplied intent
and ask zero to three consequential, specific questions. Explicit ambiguity and
deferred decisions are respected; a clear brief may need no questions.

The Story Planner prompt guides the Planning Layer to return a structured `story_plan` object.

The Script Critic prompt guides the Evaluation Layer to return:

- `passed`
- `rubric_scores`
- `strengths`
- `weaknesses`
- `suggestions`

All three prompts preserve JSON field names in English while localizing field values.
Mentor and critic use the explicit target response language supplied by the application.

The critic receives author intent and paired questions/answers separately from the
current draft. AI analysis is not promoted to an author decision. Generic section
purpose text is excluded from the draft sent to the critic. Each priority must
identify evidence in the current draft, explain its effect relative to intent,
and offer a corresponding small revision or decision. An intentional open ending
or observational form is not inherently a weakness. No previous draft is sent,
so feedback must not claim to compare revisions.

The same authoritative creator context is also passed to the planner, including
the compatibility generation endpoint. Reanalysis passes existing decisions to
the mentor and retains them if the questions change or disappear. Changing the
idea or constraints resets that active context; history is not reused as new intent.

See [prompt evaluation](prompt-evaluation.md) for behavioral checks with a real model.

## Knowledge

The knowledge pack provides concise short-film fundamentals:

- beginner glossary;
- practical filmmaking rules;
- reusable story patterns.

The Planning Layer receives this context through `KnowledgeLoader`.

## Rubric

`story_rubric.json` defines the evaluation lens used by the Evaluation Layer:

- Story Clarity
- Character
- Conflict
- Emotional Impact
- Ending
- Production Feasibility

The rubric influences scores, strengths, weaknesses, and suggestions.

## Examples

The example library gives the Planning Layer local few-shot references without vector search or RAG.

Examples cover:

- Family Drama
- Friendship
- Coming of Age
- Slice of Life
- Thriller

The `ExampleLoader` loads and caches these JSON examples.

## Structured Output

`output_schema.json` records the domain-level field inventory for planning and evaluation.

Runtime validation still comes from Pydantic models in `backend/app/application/workflow.py`; tests ensure the domain schema document and Pydantic fields remain synchronized.

## Adding Future Domains

A future domain should follow the same pattern:

1. Create a domain folder under `domains/`.
2. Add prompts, knowledge, rubrics, examples, and output schema documentation.
3. Register domain metadata with the application registry.
4. Reuse the same Harness workflow.

The goal is that new domains change assets and registration, not the core Reasoning -> Planning -> Evaluation pipeline.

## Current Limitations

- The short-film domain is the only active domain.
- Domain registration is static in the MVP.
- There is no RAG, vector search, or database-backed domain library.
- The current UI is optimized for short-film output labels.

