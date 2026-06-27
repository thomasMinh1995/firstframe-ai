# Short Film Domain

Short Film Story Development is the first supported domain for FirstFrame AI.

It was chosen because short films are constrained enough for a hackathon demo but rich enough to show the value of a Creative Reasoning Harness: a vague idea must become a protagonist, conflict, emotional arc, ending, and feasible production plan.

## Domain Assets

`domains/short-film/` contains the current intelligence pack.

```text
prompts/
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

The Story Planner prompt guides the Planning Layer to return a structured `story_plan` object.

The Script Critic prompt guides the Evaluation Layer to return:

- `passed`
- `rubric_scores`
- `strengths`
- `weaknesses`
- `suggestions`

Both prompts instruct the model to preserve JSON field names in English while localizing field values to the user's language.

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

