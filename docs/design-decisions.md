# Design Decisions

## 1. Build A Harness, Not A Chatbot

FirstFrame AI uses a fixed Creative Reasoning Harness instead of a free-form chat loop.

Reason:

- story development benefits from repeatable steps;
- the author can understand and revisit creative choices;
- future domains can reuse the same Reasoning -> Planning -> Evaluation structure;
- the system can validate structured outputs instead of trusting free-form prose.

## 2. Harness Owns Workflow

The Harness decides the runtime order:

```text
Idea -> Reasoning -> Planning -> Evaluation
```

Reason:

- workflow order is domain-agnostic;
- controllers stay thin;
- domain packs do not become mini-applications;
- future providers can plug in behind the same runtime shape.

## 3. Domain Owns Knowledge

The short-film domain owns prompts, film knowledge, rubric criteria, examples, and output schema documentation.

Reason:

- creative knowledge varies by domain;
- adding a marketing or game-design domain should not require changing the Harness;
- prompts and rubrics can evolve without touching API routes.

## 4. Load Domain Assets At Runtime

`PromptLoader`, `KnowledgeLoader`, and `ExampleLoader` read assets from the active domain and cache them in memory.

Reason:

- avoids hardcoded prompt/knowledge text in Python;
- keeps the Short Film Intelligence Pack inspectable;
- enables future domain assets to follow the same pattern.

## 5. Keep Provider Logic In Infrastructure

Provider calls live in `OpenAIProvider` and `OllamaProvider`, not controllers or core contracts. The workflow depends on `StructuredProvider`; a factory selects the adapter from configuration.

Reason:

- provider SDKs should not leak into the Harness;
- provider failures can be mapped safely;
- tests can mock the provider boundary;
- future adapters can be added without changing API routes.

## 6. Validate Structured Output With Pydantic

The provider returns JSON, then Pydantic validates the exact shape expected by each layer.

Reason:

- prevents prompt/schema drift;
- avoids markdown parsing;
- keeps the frontend response stable;
- catches malformed provider responses before API serialization.

## 7. Separate Transport Models From Artifacts

API schemas are not internal artifacts.

Reason:

- HTTP response shape is product-facing;
- artifacts are Harness-facing;
- each can evolve without forcing the other to change immediately.

## 8. Frontend Supports Reading and Revising

The current frontend exposes the workflow through progress, editable story plans, feedback, and version history. The next demo priorities are a plain-language entry, a readable view of the same working draft, visible author context, and one manual revision loop.

Reason:

- beginners need to picture their story and know the next action;
- authors need to distinguish their choices from AI proposals;
- feedback must refer to the draft and intent it actually reviewed;
- review advises the author; it does not rewrite the draft.

These additions are planned in the [Vietnam first-screenplay demo plan](plans/vietnam-first-screenplay-mvp.md). Displaying the read view must not require a second AI-authored narrative or discard unsaved edits.

## 9. Scope Follows the Writing Journey

The MVP already has local project persistence and operation progress. It does not yet deliver scene-level screenplay writing or screenplay export. Authentication, cloud sync, RAG, additional domains, and orchestration changes are not prerequisites for the next demo.

Reason:

- delivery is measured by an author starting, understanding, and revising a story;
- technical work should address demonstrated reliability or writing needs;
- implemented features and proposed work must remain distinguishable.

## 10. Vietnam First, Through Screenplay Export

FirstFrame focuses first on Vietnamese beginners writing their first short film from lived material. The journey ends at exporting the selected screenplay for human collaborators. Casting, staging, shooting, editing, and post-production are a separate human process. AI video, synthetic actors, and generated footage are outside the direction; automatic scene illustrations are no longer an active roadmap item.

The differences to validate are a low-friction beginning, contextual Vietnamese relationships and speech, emotion expressed through performable action, a useful learning-by-revision loop, and respect for intent and relevant resources. They are hypotheses, not established competitive advantages.

Story plans are the current development milestone; complete short-film screenplays remain the product goal. Feature or television screenwriting is conditional future exploration after this journey works. No production pipeline or future-format infrastructure is required now.

See the [roadmap](roadmap.md) for delivery order and the [plan](plans/vietnam-first-screenplay-mvp.md) for acceptance and pilot design.
