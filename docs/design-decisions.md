# Design Decisions

## 1. Build A Harness, Not A Chatbot

FirstFrame AI uses a fixed Creative Reasoning Harness instead of a free-form chat loop.

Reason:

- story development benefits from repeatable steps;
- judges can inspect the pipeline;
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

OpenAI calls live in `OpenAIProvider`, not controllers or core contracts.

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

## 8. Frontend Shows The Workflow

The Thinking Timeline, Story Flow visualization, and result cards are intentionally part of the demo experience.

Reason:

- makes the Harness visible to judges;
- communicates that the product reasons, plans, and evaluates;
- helps users scan the result quickly instead of reading raw JSON.

## 9. Honest MVP Constraints

The MVP avoids auth, persistence, streaming, multi-agent orchestration, RAG, LangGraph, and vector search.

Reason:

- hackathon scope favors a reliable end-to-end flow;
- engineering depth is shown through clean contracts and boundaries;
- unnecessary infrastructure would obscure the core product idea.

