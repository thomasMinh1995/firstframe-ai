# Creative Reasoning Harness Kernel

The Creative Reasoning Harness kernel is the reusable framework boundary for FirstFrame AI. It defines how creative domains, artifacts, and runtime layers fit together without implementing AI behavior.

## Kernel Components

```text
Core Kernel
├── Artifacts
├── Domain Plugin Contract
├── Domain Registry
└── Runtime Layer Interfaces
```

## Artifacts

Artifacts are immutable internal data objects exchanged between Harness layers.

Current artifact models:

- `IdeaArtifact`
- `ReasoningArtifact`
- `PlanningArtifact`
- `EvaluationArtifact`
- `StoryPlanArtifact`

Artifacts are not HTTP response models and should not be returned directly from API routes.

## Domain Plugin Contract

A domain plugin exposes:

- metadata;
- knowledge resources;
- glossary resources;
- prompt resources;
- rubric resources;
- example resources.

The plugin contract is provider-independent. It describes domain assets; it does not execute prompts or call models.

## Domain Registry

`DomainRegistry` is responsible for:

- registering plugins;
- listing registered plugins;
- retrieving plugins by identifier;
- rejecting duplicate identifiers;
- rejecting empty identifiers.

Future plugin discovery should feed discovered plugins into the registry. The Harness should continue to depend on the registry rather than direct domain imports.

## Runtime Interfaces

The kernel defines three runtime layer interfaces:

- `ReasoningLayer`
- `PlanningLayer`
- `EvaluationLayer`

Each interface receives artifacts plus a domain plugin and returns the next artifact. Implementations may be deterministic, provider-backed, or hybrid in later sprints, but the contracts stay provider-independent.

## Kernel Boundary

The kernel may depend on:

- Python standard library;
- internal core contracts.

The kernel must not depend on:

- FastAPI;
- Pydantic transport schemas;
- OpenAI or other provider SDKs;
- persistence clients;
- frontend code.

## Sprint 3 Readiness

Sprint 3 can implement a concrete runtime by composing:

- a `DomainRegistry`;
- a `ReasoningLayer`;
- a `PlanningLayer`;
- an `EvaluationLayer`.

That implementation should use the current contracts rather than changing them.
