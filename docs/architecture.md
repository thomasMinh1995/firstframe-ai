# Architecture

FirstFrame AI is built around a **Creative Reasoning Harness**: a small AI workflow engine that turns a vague creative idea into structured artifacts through Reasoning, Planning, and Evaluation.

The current MVP supports Short Film Story Development and uses OpenAI or local Ollama behind a shared provider contract. The architecture is intentionally broader than the demo domain so future creative domains can reuse the same Harness.

## System Overview

```text
Next.js Frontend
  |
  | POST /api/generate
  v
FastAPI API Layer
  |
  v
Application Workflow
  |
  v
Creative Reasoning Harness
  |-- DomainRegistry
  |-- ReasoningLayer
  |-- PlanningLayer
  |-- EvaluationLayer
  |
  v
Domain Intelligence Pack
  |-- PromptLoader
  |-- KnowledgeLoader
  |-- RubricLoader via KnowledgeLoader
  |-- ExampleLoader
  |
  v
StructuredProvider (OpenAI or Ollama)
  |
  v
Pydantic Structured Output Validation
```

## Backend Boundaries

### API Layer

`backend/app/api/` owns HTTP concerns:

- `GET /health`
- `POST /api/generate`
- Pydantic request and response transport models
- API-safe error mapping for provider failures
- CORS for local frontend development

Controllers do not call OpenAI directly. They call the application workflow and map internal artifacts to transport responses.

### Application Layer

`backend/app/application/` contains the current executable runtime:

- `workflow.py`: concrete Harness composition and layer implementations
- `ai_provider.py`: provider-independent request/result types, protocol, and errors
- `prompt_loader.py`: loads Markdown prompts from the active domain
- `knowledge_loader.py`: loads knowledge and rubric JSON
- `example_loader.py`: loads local few-shot example JSON

This layer composes core contracts with infrastructure and domain assets.

### Core Layer

`backend/app/core/` contains provider-independent contracts:

- immutable artifact dataclasses
- domain plugin protocol
- domain registry
- `ReasoningLayer`, `PlanningLayer`, `EvaluationLayer` interfaces

Core does not import FastAPI, OpenAI, frontend code, or domain JSON files.

### Infrastructure Layer

`backend/app/infrastructure/openai_provider.py` is a thin OpenAI adapter:

- loads model configuration from environment
- sends requests through `responses.create`
- appends strict JSON instructions and Pydantic JSON Schema
- parses JSON with `json.loads`
- validates with Pydantic models
- maps provider failures to provider-independent exceptions

`ollama_provider.py` sends the same context to local `/api/chat` with a JSON Schema
in `format`, then validates the completed response with Pydantic.
`provider_factory.py` selects OpenAI for a non-empty key and Ollama otherwise;
`AI_PROVIDER=openai|ollama` overrides automatic selection. Model generation failures
do not cause an automatic switch.

## Frontend

`frontend/app/` is a Next.js App Router demo UI:

- idea textarea with validation
- API client for `POST /api/generate`
- Thinking Timeline while waiting
- Story Flow visualization
- presentation-ready result cards for Analysis, Story Plan, and Evaluation
- simple English/Vietnamese loading-label heuristic

The frontend renders the existing API contract only; it does not know about internal artifacts.

## Domain Plugin Pattern

The first domain is `domains/short-film/`.

Domain assets include:

- `prompts/`
- `knowledge/`
- `rubrics/`
- `examples/`
- `output_schema.json`

The Harness owns workflow order. The domain owns creative knowledge. The provider owns model execution.

## Structured Output

Planning and evaluation responses are validated against Pydantic models in `workflow.py`.

The adapters use each response model's JSON Schema: OpenAI includes it in instructions; Ollama also enforces it through `format`. The domain-level `output_schema.json` mirrors the field inventory for documentation and tests.

This reduces prompt/schema drift and keeps the API response stable.

## Track 2 Engineering Depth

The project emphasizes:

- clear runtime boundaries;
- provider isolation;
- explicit artifact flow;
- domain-owned intelligence packs;
- loader components for prompts, knowledge, rubrics, and examples;
- structured output contracts;
- tests around registry, loaders, provider behavior, workflow, schemas, and CORS.

## Current Limitations

- OpenAI and local Ollama are implemented; other providers are not integrated.
- Domain registration is static for the MVP.
- No streaming, persistence, authentication, or deployment automation yet.
- The Reasoning Layer still uses inline instructions rather than a domain prompt file.

