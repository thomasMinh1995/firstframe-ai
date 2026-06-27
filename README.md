# FirstFrame AI

From vague ideas to structured story development.

FirstFrame AI is a production-oriented foundation for a Creative Reasoning Harness: an extensible AI workflow that will eventually guide creators from an early, ambiguous idea into a structured story plan.

Sprint 2 designs the kernel contracts for that Harness. It intentionally contains no OpenAI integration, no chatbot, no prompt execution, no evaluation logic, and no advanced AI behavior.

## Vision

Creative work often begins with a feeling, fragment, character, image, or unresolved question. FirstFrame AI exists to help creators preserve that spark while gradually shaping it into a coherent development artifact.

The long-term vision is a domain-extensible creative system. The first supported domain is short film story development, but the core Harness should also support future domains such as YouTube concepts, marketing campaigns, game design, book writing, and other structured creative workflows.

## Problem

Most AI creative tools jump too quickly from idea to generation. That can flatten taste, skip important questions, and produce output before the creative direction is clear.

Creators need a workflow that can:

- clarify vague ideas without overwriting them;
- separate reasoning, planning, and evaluation concerns;
- adapt to different creative domains;
- preserve domain-specific knowledge outside the core engine;
- evolve safely from prototype to production.

## Solution

FirstFrame AI is organized around a Creative Reasoning Harness kernel with three interface-driven runtime layers:

- **Reasoning Layer**: defines how raw creative input will be interpreted and clarified.
- **Planning Layer**: defines how clarified intent will become a structured development plan.
- **Evaluation Layer**: defines how plans will be checked against domain rubrics and quality criteria.

The Harness exchanges immutable artifacts between layers and retrieves domain knowledge through a registry-backed plugin contract. Domain-specific assets live in plugins under `domains/`, beginning with `domains/short-film/`.

## Architecture

The repository follows Clean Architecture and SOLID principles:

- Core interfaces are independent from frameworks and providers.
- Internal artifacts are immutable data objects, not API response models.
- Domain plugins hold knowledge, prompts, rubrics, and examples outside the Harness.
- The domain registry is the only entry point for retrieving domains.
- Backend delivery code depends inward on application/core boundaries.
- Frontend code is isolated from backend internals.
- Future AI providers can be added through adapters without changing core contracts.

See [docs/architecture.md](docs/architecture.md) for the full architecture notes.

## Repository Structure

```text
firstframe-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── schemas/
│   │   ├── application/
│   │   ├── core/
│   │   │   ├── artifacts.py
│   │   │   ├── domains/
│   │   │   └── harness/
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── docs/
│   ├── architecture.md
│   ├── design-decisions.md
│   ├── kernel.md
│   ├── roadmap.md
│   └── workflow.md
├── domains/
│   └── short-film/
│       ├── examples/
│       ├── glossary/
│       ├── knowledge/
│       ├── prompts/
│       └── rubrics/
├── frontend/
│   ├── app/
│   ├── package.json
│   └── tsconfig.json
└── README.md
```

### Folder Explanation

- `backend/`: FastAPI application skeleton and Python dependency configuration.
- `backend/app/api/`: HTTP delivery layer. It should expose routes and schemas only.
- `backend/app/api/schemas/`: Pydantic transport contracts for incoming requests and outgoing responses.
- `backend/app/application/`: Future use-case orchestration layer. It will coordinate core interfaces without owning domain rules.
- `backend/app/core/`: Framework-independent contracts for the Harness and domain plugin system.
- `backend/app/core/artifacts.py`: Immutable artifacts exchanged by Harness layers.
- `backend/app/core/harness/`: Reasoning, planning, and evaluation interfaces.
- `backend/app/core/domains/`: Domain plugin contracts and the domain registry.
- `backend/tests/`: Backend tests for architectural contracts and validation behavior.
- `docs/`: Product, architecture, workflow, roadmap, and decision documentation.
- `domains/`: Domain plugin assets. Each domain should be independently versionable in spirit and should not modify Harness contracts.
- `domains/short-film/`: First supported creative domain placeholder.
- `domains/short-film/knowledge/`: Future short-film development knowledge assets.
- `domains/short-film/glossary/`: Future domain vocabulary assets.
- `domains/short-film/prompts/`: Future domain prompt templates. Empty in Sprint 2 by design.
- `domains/short-film/rubrics/`: Future quality and evaluation rubrics. Empty in Sprint 2 by design.
- `domains/short-film/examples/`: Future examples and reference artifacts.
- `frontend/`: Next.js App Router skeleton with a landing page only.

## Local Development

Backend:

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements-dev.txt

uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Generate workflow:

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"idea":"A lonely astronaut hears music from an abandoned satellite."}'
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend calls `http://localhost:8000` by default. Set `NEXT_PUBLIC_API_BASE_URL` if the backend runs elsewhere.

## Roadmap

- **Sprint 1: Foundation**: repository structure, documentation, Harness interfaces, domain plugin placeholders, FastAPI skeleton, Next.js skeleton.
- **Sprint 2: AI Kernel Design**: immutable artifacts, domain plugin contract, domain registry, runtime interfaces, API schemas, request validation.
- **Sprint 3: Short-Film Runtime Prototype**: implement non-provider workflow orchestration using the existing kernel contracts.
- **Sprint 4: AI Provider Adapters**: add OpenAI integration behind infrastructure adapters.
- **Sprint 5: Product Experience**: build the first guided short-film story development UI.

See [docs/roadmap.md](docs/roadmap.md) for more detail.
