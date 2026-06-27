# Creative Reasoning Harness Kernel

The Creative Reasoning Harness is the reusable runtime boundary inside FirstFrame AI.

It is small by design: the kernel defines contracts and layer responsibilities, while the application layer composes concrete OpenAI-backed implementations for the current MVP.

## Core Contracts

`backend/app/core/` defines:

- immutable artifacts;
- domain plugin protocol;
- domain registry;
- Reasoning, Planning, and Evaluation layer interfaces.

Artifacts include:

- `IdeaArtifact`
- `ReasoningArtifact`
- `PlanningArtifact`
- `StoryPlanArtifact`
- `EvaluationArtifact`

Artifacts are internal data objects. They are not returned directly from the API.

## Runtime Layers

### ReasoningLayer

Input:

- `IdeaArtifact`
- active `DomainPlugin`

Output:

- `ReasoningArtifact`

Responsibility:

- understand the idea;
- summarize creative signals;
- identify missing information;
- produce mentor-style questions.

### PlanningLayer

Input:

- `ReasoningArtifact`
- active `DomainPlugin`

Output:

- `PlanningArtifact`

Responsibility:

- load domain prompt, knowledge, and examples;
- create a structured story plan;
- validate the planning output contract.

### EvaluationLayer

Input:

- `PlanningArtifact`
- active `DomainPlugin`

Output:

- `EvaluationArtifact`

Responsibility:

- load the domain critic prompt and rubric;
- score the plan;
- return strengths, weaknesses, and suggestions.

## Current Composition

The current application composes:

- `DomainRegistry`
- static short-film domain metadata
- `OpenAIReasoningLayer`
- `OpenAIPlanningLayer`
- `OpenAIEvaluationLayer`
- `OpenAIProvider`
- prompt, knowledge, rubric, and example loaders

This composition lives in `backend/app/application/workflow.py`.

## Domain Boundary

The kernel depends on the `DomainPlugin` contract, not on short-film files.

The short-film domain currently provides assets from `domains/short-film/`:

- prompts;
- knowledge;
- rubrics;
- examples;
- output schema documentation.

## Provider Boundary

The kernel does not import OpenAI.

OpenAI is used through `OpenAIProvider`, which receives structured requests and returns validated Pydantic objects. Provider-specific exceptions are converted into provider-independent errors.

## Why The Kernel Matters

The kernel is what makes FirstFrame AI an early AI framework rather than a single prompt demo:

- layer interfaces are explicit;
- artifacts are typed;
- domain assets are externalized;
- provider calls are isolated;
- structured output contracts are testable.

## Current Limitations

- Runtime implementations are currently OpenAI-backed only.
- Plugin discovery is static for the MVP.
- Reasoning instructions are inline rather than loaded from a domain prompt file.
- No persistence or cross-request memory exists yet.

