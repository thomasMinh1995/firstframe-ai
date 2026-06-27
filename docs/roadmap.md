# Roadmap

## Sprint 1: Foundation

Status: complete.

Deliverables:

- repository structure;
- README and docs;
- Harness interfaces;
- domain plugin placeholders;
- FastAPI skeleton with health endpoint;
- Next.js App Router skeleton with landing page.

Non-goals:

- OpenAI integration;
- chatbot UX;
- prompt implementation;
- evaluation logic;
- ReAct or agent loops.

## Sprint 2: AI Kernel Design

Status: current.

Focus:

- define immutable internal artifacts;
- design provider-independent domain plugin contracts;
- implement the domain registry;
- define Reasoning, Planning, and Evaluation runtime interfaces;
- separate API transport schemas from internal artifacts;
- validate incoming request contracts before Harness entry;
- document kernel architecture and artifact flow.

Non-goals:

- OpenAI integration;
- prompt execution;
- runtime reasoning behavior;
- story generation;
- evaluation algorithms.

## Sprint 3: Short-Film Runtime Prototype

Focus:

- implement concrete runtime orchestration using Sprint 2 contracts;
- register the first domain plugin through the registry;
- map validated API input into kernel artifacts;
- keep provider calls out of the runtime until adapter boundaries are ready;
- expand test coverage around layer boundaries.

## Sprint 4: AI Provider Adapters

Focus:

- introduce provider interfaces and adapters;
- add OpenAI integration behind infrastructure boundaries;
- add safe configuration for keys and environments;
- add observability and error-handling strategy.

## Sprint 5: Product Experience

Focus:

- build the guided short-film development UI;
- connect frontend to backend APIs;
- support save/resume workflows;
- prepare a hackathon-ready demo path.
